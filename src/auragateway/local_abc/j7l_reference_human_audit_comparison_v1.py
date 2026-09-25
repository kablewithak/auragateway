"""Deterministic J7L V3 human-audit versus model-reference comparison gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceAuditScheduleV1,
    J7LReferenceJudgmentV1,
)
from auragateway.local_abc import j7l_reference_execution_v3 as reference_execution
from auragateway.local_abc import j7l_reference_human_audit_queue_v1 as audit_queue

AUDIT_SCHEDULE_PATH = audit_queue.AUDIT_SCHEDULE_PATH
HUMAN_ASSESSMENT_ROOT = audit_queue.ASSESSMENT_ROOT
REFERENCE_JUDGMENT_ROOT = reference_execution.JUDGMENTS_DIR
COMPARISON_ROOT = Path(".local/auragateway/j7l-reference-human-audit-comparison-v1")
HUMAN_FREEZE_PATH = COMPARISON_ROOT / "human_audit_freeze.json"
CASE_COMPARISON_ROOT = COMPARISON_ROOT / "comparisons"
AUDIT_RESULT_PATH = COMPARISON_ROOT / "audit_result.json"

EXPECTED_AUDIT_SCHEDULE_SHA256: Literal[
    "02a71acbe5ff1461ff91cdc874ae35453d21f156bcaf10928f8922cbedd60109"
] = "02a71acbe5ff1461ff91cdc874ae35453d21f156bcaf10928f8922cbedd60109"
EXPECTED_OPERATOR_SHA256 = audit_queue.OPERATOR_SHA256
EXPECTED_BINDING_SHA256 = reference_execution.EXPECTED_BINDING_SHA256
EXPECTED_AUDIT_CASE_COUNT: Literal[28] = 28
EXPECTED_REFERENCE_CASE_COUNT: Literal[48] = 48
MATERIAL_SCORE_DELTA: Literal[2] = 2


class ReferenceAuditComparisonError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_COMPARISON_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FrozenHumanAssessmentEntry(FrozenModel):
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class HumanAuditFreeze(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_REFERENCE_HUMAN_AUDIT_FROZEN"] = "J7L_REFERENCE_HUMAN_AUDIT_FROZEN"
    audit_case_count: Literal[28] = EXPECTED_AUDIT_CASE_COUNT
    reference_audit_schedule_sha256: Literal[
        "02a71acbe5ff1461ff91cdc874ae35453d21f156bcaf10928f8922cbedd60109"
    ] = EXPECTED_AUDIT_SCHEDULE_SHA256
    audit_actor_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolution_owner_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessments: tuple[FrozenHumanAssessmentEntry, ...] = Field(
        min_length=28,
        max_length=28,
    )
    assessment_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_before_reference_comparison: Literal[True] = True
    model_reference_content_read_before_freeze: Literal[False] = False
    jev_requests_performed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_freeze(self) -> Self:
        ids = tuple(item.case_id for item in self.assessments)
        if len(ids) != len(set(ids)):
            raise ValueError("human-audit freeze case IDs must be unique")
        if self.assessment_inventory_sha256 != _assessment_inventory_sha256(self.assessments):
            raise ValueError("human-audit assessment inventory digest drifted")
        if self.audit_actor_id_sha256 != EXPECTED_OPERATOR_SHA256:
            raise ValueError("human-audit freeze actor identity drifted")
        if self.resolution_owner_id_sha256 != EXPECTED_OPERATOR_SHA256:
            raise ValueError("human-audit freeze resolution-owner identity drifted")
        return self


DisagreementReason = Literal[
    "VERDICT_MISMATCH",
    "CRITERION_SCORE_DELTA",
    "FAILURE_LABEL_SET_MISMATCH",
]


class AuditCaseComparison(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    human_assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_judgment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    human_verdict: ReviewVerdict
    reference_verdict: ReviewVerdict
    criterion_score_deltas: dict[RubricCriterion, int]
    human_failure_labels: tuple[EpisodeFailureLabel, ...]
    reference_failure_labels: tuple[EpisodeFailureLabel, ...]
    verdict_mismatch: bool
    material_score_delta: bool
    failure_label_set_mismatch: bool
    disagreement_reasons: tuple[DisagreementReason, ...]
    material_disagreement: bool
    audit_may_rewrite_reference: Literal[False] = False

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
        if set(self.criterion_score_deltas) != set(RubricCriterion):
            raise ValueError("audit comparison must cover every rubric criterion")
        verdict = self.human_verdict is not self.reference_verdict
        score = any(delta >= MATERIAL_SCORE_DELTA for delta in self.criterion_score_deltas.values())
        labels = set(self.human_failure_labels) != set(self.reference_failure_labels)
        reasons: list[DisagreementReason] = []
        if verdict:
            reasons.append("VERDICT_MISMATCH")
        if score:
            reasons.append("CRITERION_SCORE_DELTA")
        if labels:
            reasons.append("FAILURE_LABEL_SET_MISMATCH")
        if self.verdict_mismatch != verdict:
            raise ValueError("verdict-mismatch flag drifted")
        if self.material_score_delta != score:
            raise ValueError("material-score-delta flag drifted")
        if self.failure_label_set_mismatch != labels:
            raise ValueError("failure-label-set-mismatch flag drifted")
        if self.disagreement_reasons != tuple(reasons):
            raise ValueError("audit disagreement reasons drifted")
        if self.material_disagreement != bool(reasons):
            raise ValueError("material-disagreement flag drifted")
        return self


class ReferenceAuditResult(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal[
        "J7L_REFERENCE_HUMAN_AUDIT_PASS",
        "J7L_REFERENCE_HUMAN_AUDIT_FAIL",
    ]
    audit_case_count: Literal[28] = EXPECTED_AUDIT_CASE_COUNT
    agreement_count: int = Field(ge=0, le=28)
    material_disagreement_count: int = Field(ge=0, le=28)
    material_disagreement_case_ids: tuple[str, ...]
    verdict_mismatch_count: int = Field(ge=0, le=28)
    material_score_delta_case_count: int = Field(ge=0, le=28)
    failure_label_set_mismatch_count: int = Field(ge=0, le=28)
    human_audit_freeze_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_audit_schedule_sha256: Literal[
        "02a71acbe5ff1461ff91cdc874ae35453d21f156bcaf10928f8922cbedd60109"
    ] = EXPECTED_AUDIT_SCHEDULE_SHA256
    audit_actor_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolution_owner_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    audit_complete: Literal[True] = True
    audit_may_rewrite_reference: Literal[False] = False
    model_reference_content_read: Literal[True] = True
    jev_requests_performed: Literal[0] = 0
    reference_set_valid_for_advancement: bool
    coverage_evaluated: Literal[False] = False
    next_gate: Literal[
        "EVALUATE_J7L_REFERENCE_COVERAGE_V1",
        "STOP_REFERENCE_QUALITY_FAILURE",
    ]

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if self.agreement_count != self.audit_case_count - self.material_disagreement_count:
            raise ValueError("audit agreement accounting drifted")
        if len(self.material_disagreement_case_ids) != self.material_disagreement_count:
            raise ValueError("material-disagreement case accounting drifted")
        if len(set(self.material_disagreement_case_ids)) != len(
            self.material_disagreement_case_ids
        ):
            raise ValueError("material-disagreement case IDs must be unique")
        passed = self.material_disagreement_count == 0
        expected_status = (
            "J7L_REFERENCE_HUMAN_AUDIT_PASS" if passed else "J7L_REFERENCE_HUMAN_AUDIT_FAIL"
        )
        expected_gate = (
            "EVALUATE_J7L_REFERENCE_COVERAGE_V1" if passed else "STOP_REFERENCE_QUALITY_FAILURE"
        )
        if self.status != expected_status:
            raise ValueError("reference-audit status drifted")
        if self.reference_set_valid_for_advancement is not passed:
            raise ValueError("reference advancement disposition drifted")
        if self.next_gate != expected_gate:
            raise ValueError("reference-audit next gate drifted")
        if self.audit_actor_id_sha256 != EXPECTED_OPERATOR_SHA256:
            raise ValueError("audit-result actor identity drifted")
        if self.resolution_owner_id_sha256 != EXPECTED_OPERATOR_SHA256:
            raise ValueError("audit-result resolution-owner identity drifted")
        return self


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_FILE_MISSING",
            f"required protected audit file is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_JSON_INVALID",
            f"protected audit file is not valid UTF-8 JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_JSON_SHAPE_INVALID",
            f"protected audit file root must be an object: {path.as_posix()}",
        )
    return value


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise ReferenceAuditComparisonError(
                "J7L_REFERENCE_AUDIT_OUTPUT_PATH_UNSAFE",
                "protected audit output path is unsafe",
            )
        if path.read_bytes() != payload:
            raise ReferenceAuditComparisonError(
                "J7L_REFERENCE_AUDIT_APPEND_ONLY_CONFLICT",
                "existing protected audit output differs from expected bytes",
            )
        return False
    with path.open("xb") as handle:
        handle.write(payload)
    return True


def _load_schedule(root: Path) -> J7LReferenceAuditScheduleV1:
    path = root / AUDIT_SCHEDULE_PATH
    if not path.is_file() or path.is_symlink():
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_SCHEDULE_MISSING",
            "frozen reference-audit schedule is missing or unsafe",
        )
    if _sha256_file(path) != EXPECTED_AUDIT_SCHEDULE_SHA256:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_SCHEDULE_HASH_DRIFT",
            "frozen reference-audit schedule SHA-256 drifted",
        )
    try:
        schedule = J7LReferenceAuditScheduleV1.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_SCHEDULE_INVALID",
            "frozen reference-audit schedule failed typed validation",
        ) from error
    if schedule.audit_actor_id_sha256 != EXPECTED_OPERATOR_SHA256:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_ACTOR_DRIFT",
            "frozen audit actor identity drifted",
        )
    if schedule.resolution_owner_id_sha256 != EXPECTED_OPERATOR_SHA256:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_OWNER_DRIFT",
            "frozen resolution-owner identity drifted",
        )
    return schedule


def _audit_case_ids(schedule: J7LReferenceAuditScheduleV1) -> tuple[str, ...]:
    case_ids = schedule.protected_secondary_case_ids + schedule.additional_spot_check_case_ids
    if len(case_ids) != EXPECTED_AUDIT_CASE_COUNT:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_CASE_COUNT_INVALID",
            "frozen human audit must contain exactly 28 cases",
        )
    if len(set(case_ids)) != len(case_ids):
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_CASE_IDS_NOT_UNIQUE",
            "frozen human-audit case IDs must be unique",
        )
    return case_ids


def _load_human_assessment(
    root: Path,
    case_id: str,
) -> tuple[audit_queue.Assessment, str]:
    path = root / HUMAN_ASSESSMENT_ROOT / f"{case_id}.json"
    try:
        assessment = audit_queue.Assessment.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_ASSESSMENT_INVALID",
            f"{case_id} human assessment failed typed validation",
        ) from error
    if assessment.case_id != case_id:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_ASSESSMENT_CASE_DRIFT",
            f"{case_id} human assessment identity drifted",
        )
    return assessment, _sha256_file(path)


def _load_all_human_assessments(
    root: Path,
    case_ids: tuple[str, ...],
) -> dict[str, tuple[audit_queue.Assessment, str]]:
    directory = root / HUMAN_ASSESSMENT_ROOT
    observed = tuple(sorted(path.stem for path in directory.glob("j7l-dev-*.json")))
    if observed != tuple(sorted(case_ids)):
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_ASSESSMENT_INVENTORY_DRIFT",
            "protected human-assessment inventory differs from frozen 28-case audit",
        )
    return {case_id: _load_human_assessment(root, case_id) for case_id in case_ids}


def _assessment_inventory_sha256(
    entries: tuple[FrozenHumanAssessmentEntry, ...],
) -> str:
    inventory = tuple(
        {
            "case_id": entry.case_id,
            "assessment_sha256": entry.assessment_sha256,
        }
        for entry in entries
    )
    return _sha256_bytes(_canonical_json_bytes(inventory))


def _expected_human_freeze(root: Path) -> HumanAuditFreeze:
    schedule = _load_schedule(root)
    case_ids = _audit_case_ids(schedule)
    assessments = _load_all_human_assessments(root, case_ids)
    entries = tuple(
        FrozenHumanAssessmentEntry(
            case_id=case_id,
            assessment_sha256=assessments[case_id][1],
        )
        for case_id in case_ids
    )
    return HumanAuditFreeze(
        audit_actor_id_sha256=schedule.audit_actor_id_sha256,
        resolution_owner_id_sha256=schedule.resolution_owner_id_sha256,
        assessments=entries,
        assessment_inventory_sha256=_assessment_inventory_sha256(entries),
    )


def freeze_human_audit(repo_root: Path) -> HumanAuditFreeze:
    root = repo_root.resolve()
    freeze = _expected_human_freeze(root)
    _write_once(
        root / HUMAN_FREEZE_PATH,
        _canonical_json_bytes(freeze.model_dump(mode="json")),
    )
    return freeze


def _load_and_validate_freeze(root: Path) -> tuple[HumanAuditFreeze, str]:
    path = root / HUMAN_FREEZE_PATH
    if not path.is_file() or path.is_symlink():
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_FREEZE_REQUIRED",
            "human audit must be frozen before model-reference comparison",
        )
    try:
        freeze = HumanAuditFreeze.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_FREEZE_INVALID",
            "human-audit freeze failed typed validation",
        ) from error
    expected = _expected_human_freeze(root)
    if path.read_bytes() != _canonical_json_bytes(expected.model_dump(mode="json")):
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_FREEZE_DRIFT",
            "human assessments changed after the protected freeze",
        )
    return freeze, _sha256_file(path)


def _load_reference_population(
    root: Path,
) -> dict[str, tuple[J7LReferenceJudgmentV1, str]]:
    directory = root / REFERENCE_JUDGMENT_ROOT
    expected_ids = tuple(f"j7l-dev-{index:03d}" for index in range(1, 49))
    observed_ids = tuple(sorted(path.stem for path in directory.glob("j7l-dev-*.json")))
    if observed_ids != expected_ids:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_REFERENCE_INVENTORY_DRIFT",
            "model-reference judgment inventory must be exactly j7l-dev-001..048",
        )
    judgments: dict[str, tuple[J7LReferenceJudgmentV1, str]] = {}
    for case_id in expected_ids:
        path = directory / f"{case_id}.json"
        try:
            judgment = J7LReferenceJudgmentV1.model_validate(_read_json_object(path))
        except ValidationError as error:
            raise ReferenceAuditComparisonError(
                "J7L_REFERENCE_AUDIT_REFERENCE_INVALID",
                f"{case_id} model-reference judgment failed typed validation",
            ) from error
        if judgment.case_id != case_id:
            raise ReferenceAuditComparisonError(
                "J7L_REFERENCE_AUDIT_REFERENCE_CASE_DRIFT",
                f"{case_id} model-reference judgment identity drifted",
            )
        if judgment.judge_binding_sha256 != EXPECTED_BINDING_SHA256:
            raise ReferenceAuditComparisonError(
                "J7L_REFERENCE_AUDIT_BINDING_DRIFT",
                f"{case_id} model-reference judge binding drifted",
            )
        judgments[case_id] = (judgment, _sha256_file(path))
    if len(judgments) != EXPECTED_REFERENCE_CASE_COUNT:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_REFERENCE_COUNT_INVALID",
            "model-reference population must contain exactly 48 valid judgments",
        )
    return judgments


def compare_case(
    *,
    human: audit_queue.Assessment,
    human_sha256: str,
    reference: J7LReferenceJudgmentV1,
    reference_sha256: str,
) -> AuditCaseComparison:
    if human.case_id != reference.case_id:
        raise ReferenceAuditComparisonError(
            "J7L_REFERENCE_AUDIT_CASE_ID_MISMATCH",
            "human and model-reference case identities differ",
        )
    deltas = {
        criterion: abs(human.criterion_scores[criterion] - reference.criterion_scores[criterion])
        for criterion in RubricCriterion
    }
    verdict = human.verdict is not reference.verdict
    score = any(delta >= MATERIAL_SCORE_DELTA for delta in deltas.values())
    labels = set(human.failure_labels) != set(reference.failure_labels)
    reasons: list[DisagreementReason] = []
    if verdict:
        reasons.append("VERDICT_MISMATCH")
    if score:
        reasons.append("CRITERION_SCORE_DELTA")
    if labels:
        reasons.append("FAILURE_LABEL_SET_MISMATCH")
    return AuditCaseComparison(
        case_id=human.case_id,
        human_assessment_sha256=human_sha256,
        reference_judgment_sha256=reference_sha256,
        human_verdict=human.verdict,
        reference_verdict=reference.verdict,
        criterion_score_deltas=deltas,
        human_failure_labels=human.failure_labels,
        reference_failure_labels=reference.failure_labels,
        verdict_mismatch=verdict,
        material_score_delta=score,
        failure_label_set_mismatch=labels,
        disagreement_reasons=tuple(reasons),
        material_disagreement=bool(reasons),
    )


def evaluate(repo_root: Path) -> ReferenceAuditResult:
    root = repo_root.resolve()
    freeze, freeze_sha256 = _load_and_validate_freeze(root)
    schedule = _load_schedule(root)
    case_ids = _audit_case_ids(schedule)
    human = _load_all_human_assessments(root, case_ids)

    # Model-reference content is read only after the human freeze is verified.
    references = _load_reference_population(root)

    comparisons: list[AuditCaseComparison] = []
    for case_id in case_ids:
        human_assessment, human_sha256 = human[case_id]
        reference, reference_sha256 = references[case_id]
        comparison = compare_case(
            human=human_assessment,
            human_sha256=human_sha256,
            reference=reference,
            reference_sha256=reference_sha256,
        )
        _write_once(
            root / CASE_COMPARISON_ROOT / f"{case_id}.json",
            _canonical_json_bytes(comparison.model_dump(mode="json")),
        )
        comparisons.append(comparison)

    material = tuple(item for item in comparisons if item.material_disagreement)
    passed = not material
    result = ReferenceAuditResult(
        status=("J7L_REFERENCE_HUMAN_AUDIT_PASS" if passed else "J7L_REFERENCE_HUMAN_AUDIT_FAIL"),
        agreement_count=EXPECTED_AUDIT_CASE_COUNT - len(material),
        material_disagreement_count=len(material),
        material_disagreement_case_ids=tuple(item.case_id for item in material),
        verdict_mismatch_count=sum(item.verdict_mismatch for item in comparisons),
        material_score_delta_case_count=sum(item.material_score_delta for item in comparisons),
        failure_label_set_mismatch_count=sum(
            item.failure_label_set_mismatch for item in comparisons
        ),
        human_audit_freeze_sha256=freeze_sha256,
        audit_actor_id_sha256=freeze.audit_actor_id_sha256,
        resolution_owner_id_sha256=freeze.resolution_owner_id_sha256,
        reference_set_valid_for_advancement=passed,
        next_gate=(
            "EVALUATE_J7L_REFERENCE_COVERAGE_V1" if passed else "STOP_REFERENCE_QUALITY_FAILURE"
        ),
    )
    _write_once(
        root / AUDIT_RESULT_PATH,
        _canonical_json_bytes(result.model_dump(mode="json")),
    )
    return result


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("freeze", "evaluate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "freeze":
            result: FrozenModel = freeze_human_audit(args.repo_root)
        else:
            result = evaluate(args.repo_root)
    except (ReferenceAuditComparisonError, ValidationError, OSError) as error:
        if isinstance(error, ReferenceAuditComparisonError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, ValidationError):
            code = "J7L_REFERENCE_AUDIT_COMPARISON_TYPED_VALIDATION_FAILED"
            message = "J7L reference-audit comparison typed validation failed"
        else:
            code = "J7L_REFERENCE_AUDIT_COMPARISON_IO_FAILED"
            message = "J7L reference-audit comparison local I/O failed"
        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(result.model_dump_json(exclude_none=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
