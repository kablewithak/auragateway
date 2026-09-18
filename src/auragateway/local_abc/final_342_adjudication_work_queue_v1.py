"""Independent third-human adjudication work queue for Final-342.

The queue verifies that the frozen Jev shadow batch is complete but never
places Jev outputs in authoritative human work items.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    DisagreementReason,
    MaterialDisagreement,
    QualityReviewRecord,
    ReviewRole,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.evals import blinded_quality as blinded_eval
from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)
from auragateway.local_abc import (
    final_342_jev_shadow_batch_freeze_v1 as batch_freeze,
)
from auragateway.local_abc import (
    final_342_jev_shadow_batch_runner_v1 as batch_runner,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_runner_v1 as canary_runner,
)
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as bridge,
)
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)

QUEUE_ROOT = Path(".local/auragateway/final-342-adjudication-work-queue-v1")
EXPECTED_MATERIAL_DISAGREEMENTS: Literal[35] = 35
EXPECTED_VERDICT_MISMATCHES: Literal[0] = 0
EXPECTED_MATERIAL_SCORE_DELTAS: Literal[4] = 4
EXPECTED_FAILURE_LABEL_MISMATCHES: Literal[35] = 35
EXPECTED_JEV_REQUEST_INVENTORY_SHA256: Literal[
    "d009646abff567e35c94da8a61edf57f2cf8ac948bfe915e7941861abd359627"
] = "d009646abff567e35c94da8a61edf57f2cf8ac948bfe915e7941861abd359627"


class AdjudicationQueueError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CriterionDraft(FrozenModel):
    criterion: RubricCriterion
    score: int | None = Field(default=None, ge=1, le=4)
    evidence_note: str | None = Field(default=None, min_length=1, max_length=4000)


class AdjudicationSubmissionTemplate(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    adjudicator_key: str | None = None
    criterion_scores: tuple[CriterionDraft, ...] = Field(min_length=7, max_length=7)
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    rationale: str | None = None


class VisibleCaseEvidence(FrozenModel):
    rubric_id: Literal["auragateway-quality-rubric-v1"]
    rubric_sha256: Literal["7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"]
    turns: tuple[review_successor.ReviewerTurn, ...] = Field(min_length=4, max_length=4)
    terminal_structured_result: dict[str, object] | None = None
    frozen_source_evidence: tuple[dict[str, object], ...] = ()
    deterministic_validation_summary: dict[str, object] = Field(default_factory=dict)


class InitialReviewView(FrozenModel):
    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...]
    verdict: ReviewVerdict

    @model_validator(mode="after")
    def validate_view(self) -> InitialReviewView:
        if set(self.criterion_scores) != set(RubricCriterion):
            raise ValueError("initial review must score all rubric criteria")
        if any(score < 1 or score > 4 for score in self.criterion_scores.values()):
            raise ValueError("initial review score must remain in [1,4]")
        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("initial review failure labels must be unique")
        return self


class AdjudicationWorkItem(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    work_item_id: Literal["auragateway-final-342-independent-adjudication-work-item-v1"] = (
        "auragateway-final-342-independent-adjudication-work-item-v1"
    )
    role: Literal["adjudicator"] = "adjudicator"
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    adjudication_instruction: str = Field(min_length=50, max_length=1600)
    visible_case_evidence: VisibleCaseEvidence
    rubric: BlindedQualityRubric
    review_a: InitialReviewView
    review_b: InitialReviewView
    disagreement_reasons: tuple[DisagreementReason, ...] = Field(min_length=1)
    criterion_score_deltas: dict[RubricCriterion, int]
    failure_label_inventory: tuple[EpisodeFailureLabel, ...]

    @model_validator(mode="after")
    def validate_work_item(self) -> AdjudicationWorkItem:
        if set(self.criterion_score_deltas) != set(RubricCriterion):
            raise ValueError("adjudication score deltas must cover all rubric criteria")
        if set(self.failure_label_inventory) != set(EpisodeFailureLabel):
            raise ValueError("failure-label inventory drifted")
        return self


class QueueStatus(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["ADJUDICATION_PENDING", "ADJUDICATION_COMPLETE"]
    detected_material_disagreement_count: Literal[35]
    valid_adjudication_count: int = Field(ge=0, le=35)
    missing_required_adjudication_count: int = Field(ge=0, le=35)
    next_review_item_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    jev_shadow_batch_complete: Literal[True] = True
    jev_shadow_output_exposed_to_human: Literal[False] = False
    reviewer_identity_exposed_to_adjudicator: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    effect_claims_permitted: Literal[False] = False


class MaterializationReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["ADJUDICATION_WORK_ITEM_READY", "ADJUDICATION_COMPLETE"]
    review_item_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    work_item_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    work_item_path: str | None = None
    submission_path: str | None = None
    work_item_created: bool
    submission_template_created: bool
    jev_shadow_batch_complete: Literal[True] = True
    jev_shadow_output_exposed_to_human: Literal[False] = False
    reviewer_identity_exposed_to_adjudicator: Literal[False] = False
    human_adjudication_created: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal[
        "COMPLETE_CURRENT_INDEPENDENT_HUMAN_ADJUDICATION",
        "J7_JEV_VS_HUMAN_CALIBRATION",
    ]


class MaterialCase(FrozenModel):
    payload: review_successor.ReviewerPayload
    primary: QualityReviewRecord
    secondary: QualityReviewRecord
    disagreement: MaterialDisagreement


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _canonical_provider_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_FILE_MISSING",
            f"required adjudication input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_JSON_INVALID",
            f"adjudication input is invalid JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_JSON_SHAPE_INVALID",
            f"adjudication JSON root must be an object: {path.as_posix()}",
        )
    return value


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_PATH_UNSAFE",
                "adjudication queue output path is unsafe",
            )
        if path.read_bytes() != payload:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_APPEND_ONLY_CONFLICT",
                "existing immutable adjudication work item differs",
            )
        return False

    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_TEMP_RESIDUE",
            "adjudication queue temporary file already exists",
        )
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.rename(temporary, path)
    except OSError:
        if temporary.exists():
            temporary.unlink()
        if path.is_file() and not path.is_symlink() and path.read_bytes() == payload:
            return False
        raise
    return True


def _write_submission_template_if_absent(
    path: Path,
    payload: bytes,
    *,
    review_item_id: str,
) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_SUBMISSION_PATH_UNSAFE",
                "adjudication submission path is unsafe",
            )
        existing = _read_json_object(path)
        if existing.get("review_item_id") != review_item_id:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_SUBMISSION_IDENTITY_MISMATCH",
                "existing adjudication draft belongs to a different review item",
            )
        return False

    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_TEMP_RESIDUE",
            "adjudication submission temporary file already exists",
        )
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.rename(temporary, path)
    except OSError:
        if temporary.exists():
            temporary.unlink()
        raise
    return True


def _review_result_path(root: Path, assignment_id: str) -> Path:
    return root / bridge.REVIEW_RESULT_ROOT / "reviews" / f"{assignment_id}.json"


def _adjudication_result_path(root: Path, review_item_id: str) -> Path:
    return root / bridge.REVIEW_RESULT_ROOT / "adjudications" / f"{review_item_id}.json"


def _find_assignment(
    assignments: tuple[bridge.ExpectedReviewAssignment, ...],
    *,
    review_item_id: str,
    role: Literal["primary", "secondary"],
) -> bridge.ExpectedReviewAssignment:
    matches = tuple(
        item for item in assignments if item.review_item_id == review_item_id and item.role == role
    )
    if len(matches) != 1:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_ASSIGNMENT_INVALID",
            f"expected exactly one {role} assignment for review item",
        )
    return matches[0]


def _load_review(
    root: Path,
    assignment: bridge.ExpectedReviewAssignment,
    rubric: BlindedQualityRubric,
) -> QualityReviewRecord:
    try:
        review = QualityReviewRecord.model_validate(
            _read_json_object(_review_result_path(root, assignment.assignment_id))
        )
    except ValidationError as error:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_REVIEW_INVALID",
            "persisted human review failed typed validation",
        ) from error
    expected_role = ReviewRole.PRIMARY if assignment.role == "primary" else ReviewRole.SECONDARY
    if (
        review.review_id != assignment.assignment_id
        or review.episode_id != assignment.episode_id
        or review.role is not expected_role
    ):
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_REVIEW_IDENTITY_DRIFT",
            "persisted human review differs from its frozen assignment",
        )
    expected_verdict = blinded_eval.expected_verdict(
        review.criterion_scores,
        len(review.failure_labels),
        rubric,
    )
    if review.verdict is not expected_verdict:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_REVIEW_VERDICT_INVALID",
            "persisted human review verdict differs from frozen rubric",
        )
    return review


def _validate_jev_shadow_complete(root: Path) -> None:
    try:
        manifest = batch_freeze.FrozenBatchManifest.model_validate(
            _read_json_object(root / batch_freeze.BATCH_MANIFEST_PATH)
        )
        canary_receipt = canary_runner.LiveCanaryReceipt.model_validate(
            _read_json_object(root / canary_runner.CANARY_RECEIPT_PATH)
        )
    except ValidationError as error:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_JEV_EVIDENCE_INVALID",
            "Jev shadow completion evidence failed typed validation",
        ) from error

    if manifest.request_inventory_sha256 != EXPECTED_JEV_REQUEST_INVENTORY_SHA256:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_JEV_INVENTORY_DRIFT",
            "Jev shadow request inventory differs from accepted J5 evidence",
        )
    if (
        canary_receipt.request_sha256 != manifest.canary_request_sha256
        or canary_receipt.response_sha256 != manifest.canary_response_sha256
    ):
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_JEV_CANARY_DRIFT",
            "Jev canary evidence differs from the frozen 35-case manifest",
        )

    for entry in manifest.entries[1:]:
        request_path = root / entry.request_relative_path
        if not request_path.is_file() or request_path.is_symlink():
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_JEV_REQUEST_MISSING",
                "frozen Jev request is missing or unsafe",
            )
        request_bytes = request_path.read_bytes()
        if _sha256_bytes(request_bytes) != entry.request_sha256:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_JEV_REQUEST_DRIFT",
                "frozen Jev request digest drifted",
            )
        try:
            request = jev_contract.JevShadowRequest.model_validate(
                json.loads(request_bytes.decode("utf-8"))
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_JEV_REQUEST_INVALID",
                "frozen Jev request failed typed validation",
            ) from error

        execution_path = (
            root
            / batch_runner.EXECUTION_ROOT
            / f"{entry.batch_index:02d}-{entry.review_item_id}.json"
        )
        try:
            execution = batch_runner.BatchCaseExecutionRecord.model_validate(
                _read_json_object(execution_path)
            )
        except ValidationError as error:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_JEV_EXECUTION_INVALID",
                "Jev shadow execution record failed typed validation",
            ) from error
        if (
            execution.batch_index != entry.batch_index
            or execution.review_item_id != entry.review_item_id
            or execution.request_sha256 != entry.request_sha256
        ):
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_JEV_EXECUTION_DRIFT",
                "Jev execution identity differs from frozen batch entry",
            )
        try:
            jev_contract.validate_response_against_request(request, execution.response)
        except jev_contract.JevContractError as error:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_JEV_RESPONSE_INVALID",
                "Jev shadow response differs from its frozen request",
            ) from error
        response_bytes = _canonical_provider_bytes(execution.response.model_dump(mode="json"))
        if _sha256_bytes(response_bytes) != execution.response_sha256:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_JEV_RESPONSE_DRIFT",
                "persisted Jev response digest drifted",
            )


def _load_inputs(
    root: Path,
) -> tuple[
    review_successor.ProtectedExport,
    review_successor.ProtectedSchedule,
    BlindedQualityRubric,
    tuple[bridge.ExpectedReviewAssignment, ...],
]:
    bridge.validate_inputs(root)
    protected_root = root / bridge.PROTECTED_REVIEW_ROOT
    try:
        export = review_successor.ProtectedExport.model_validate(
            _read_json_object(protected_root / review_successor.PROTECTED_EXPORT_PATH.name)
        )
        schedule = review_successor.ProtectedSchedule.model_validate(
            _read_json_object(protected_root / review_successor.PROTECTED_SCHEDULE_PATH.name)
        )
        rubric = BlindedQualityRubric.model_validate(_read_json_object(root / bridge.RUBRIC_PATH))
    except ValidationError as error:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_INPUT_INVALID",
            "human adjudication queue input failed typed validation",
        ) from error
    assignments = bridge.project_expected_assignments(export, schedule)
    return export, schedule, rubric, assignments


def _material_cases(
    root: Path,
    export: review_successor.ProtectedExport,
    schedule: review_successor.ProtectedSchedule,
    rubric: BlindedQualityRubric,
    assignments: tuple[bridge.ExpectedReviewAssignment, ...],
) -> tuple[MaterialCase, ...]:
    payload_by_assignment = {payload.assignment_id: payload for payload in export.assignments}
    cases: list[MaterialCase] = []
    for schedule_entry in schedule.entries:
        primary_assignment = _find_assignment(
            assignments,
            review_item_id=schedule_entry.review_item_id,
            role="primary",
        )
        secondary_assignment = _find_assignment(
            assignments,
            review_item_id=schedule_entry.review_item_id,
            role="secondary",
        )
        primary = _load_review(root, primary_assignment, rubric)
        secondary = _load_review(root, secondary_assignment, rubric)
        try:
            disagreement = blinded_eval.detect_material_disagreement(primary, secondary, rubric)
        except blinded_eval.BlindedQualityError as error:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_DISAGREEMENT_INVALID",
                error.safe_message,
            ) from error
        if disagreement is None:
            continue
        payload = payload_by_assignment.get(primary_assignment.assignment_id)
        if payload is None:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_PAYLOAD_MISSING",
                "primary reviewer payload is missing from protected export",
            )
        cases.append(
            MaterialCase(
                payload=payload,
                primary=primary,
                secondary=secondary,
                disagreement=disagreement,
            )
        )
    frozen = tuple(cases)
    _validate_material_shape(frozen)
    return frozen


def _validate_material_shape(cases: tuple[MaterialCase, ...]) -> None:
    if len(cases) != EXPECTED_MATERIAL_DISAGREEMENTS:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_MATERIAL_COUNT_DRIFT",
            f"expected 35 material disagreements; observed={len(cases)}",
        )
    verdict_mismatch_count = sum(
        DisagreementReason.VERDICT_MISMATCH in case.disagreement.reasons for case in cases
    )
    score_delta_count = sum(
        DisagreementReason.MATERIAL_SCORE_DELTA in case.disagreement.reasons for case in cases
    )
    label_mismatch_count = sum(
        DisagreementReason.FAILURE_LABEL_MISMATCH in case.disagreement.reasons for case in cases
    )
    if verdict_mismatch_count != EXPECTED_VERDICT_MISMATCHES:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_VERDICT_SHAPE_DRIFT",
            "material-disagreement verdict-mismatch count drifted",
        )
    if score_delta_count != EXPECTED_MATERIAL_SCORE_DELTAS:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_SCORE_SHAPE_DRIFT",
            "material score-delta count drifted",
        )
    if label_mismatch_count != EXPECTED_FAILURE_LABEL_MISMATCHES:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_LABEL_SHAPE_DRIFT",
            "failure-label mismatch count drifted",
        )


def _score_map(review: QualityReviewRecord) -> dict[RubricCriterion, int]:
    return {score.criterion: score.score for score in review.criterion_scores}


def _review_view(review: QualityReviewRecord) -> InitialReviewView:
    return InitialReviewView(
        criterion_scores=_score_map(review),
        failure_labels=review.failure_labels,
        verdict=review.verdict,
    )


def _anonymized_review_pair(
    review_item_id: str,
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
) -> tuple[InitialReviewView, InitialReviewView]:
    candidates = (
        (
            hashlib.sha256(f"{review_item_id}|{primary.review_id}".encode()).hexdigest(),
            _review_view(primary),
        ),
        (
            hashlib.sha256(f"{review_item_id}|{secondary.review_id}".encode()).hexdigest(),
            _review_view(secondary),
        ),
    )
    ordered = tuple(sorted(candidates, key=lambda item: item[0]))
    return ordered[0][1], ordered[1][1]


def _visible_evidence(payload: review_successor.ReviewerPayload) -> VisibleCaseEvidence:
    return VisibleCaseEvidence(
        rubric_id=payload.rubric_id,
        rubric_sha256=payload.rubric_sha256,
        turns=payload.turns,
        terminal_structured_result=payload.terminal_structured_result,
        frozen_source_evidence=payload.frozen_source_evidence,
        deterministic_validation_summary=payload.deterministic_validation_summary,
    )


def build_work_item(case: MaterialCase, rubric: BlindedQualityRubric) -> AdjudicationWorkItem:
    review_a, review_b = _anonymized_review_pair(
        case.payload.review_item_id,
        case.primary,
        case.secondary,
    )
    item = AdjudicationWorkItem(
        review_item_id=case.payload.review_item_id,
        episode_id=case.payload.episode_id,
        adjudication_instruction=(
            "Act as the independent third human adjudicator. Using only the visible "
            "blinded case evidence, frozen rubric, and two anonymous initial human "
            "review views, determine the final score for every criterion and exact "
            "failure-label set. Resolve the disagreement independently: do not "
            "average mechanically and do not assume either initial reviewer is "
            "correct. Do not use or request any Jev shadow result, model output, "
            "probability, or later calibration result. Your adjudicator identity "
            "must be different from both initial human reviewers."
        ),
        visible_case_evidence=_visible_evidence(case.payload),
        rubric=rubric,
        review_a=review_a,
        review_b=review_b,
        disagreement_reasons=case.disagreement.reasons,
        criterion_score_deltas=case.disagreement.criterion_score_deltas,
        failure_label_inventory=tuple(EpisodeFailureLabel),
    )
    review_successor.assert_reviewer_safe(item.model_dump(mode="python"))
    return item


def _submission_template(review_item_id: str) -> AdjudicationSubmissionTemplate:
    return AdjudicationSubmissionTemplate(
        review_item_id=review_item_id,
        criterion_scores=tuple(
            CriterionDraft(criterion=criterion) for criterion in RubricCriterion
        ),
    )


def _select_next_case(root: Path, cases: tuple[MaterialCase, ...]) -> MaterialCase | None:
    for case in cases:
        path = _adjudication_result_path(root, case.payload.review_item_id)
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise AdjudicationQueueError(
                    "FINAL_342_ADJUDICATION_QUEUE_RESULT_PATH_UNSAFE",
                    "adjudication result path is unsafe",
                )
            continue
        return case
    return None


def queue_status(repo_root: Path) -> QueueStatus:
    root = repo_root.resolve()
    _validate_jev_shadow_complete(root)
    accountability = bridge.review_accountability(root)
    if (
        accountability.valid_primary_review_count != 162
        or accountability.missing_primary_review_count != 0
        or accountability.valid_secondary_review_count != 41
        or accountability.missing_secondary_review_count != 0
        or accountability.detected_material_disagreement_count != 35
        or accountability.currently_required_adjudication_count != 35
        or accountability.unexpected_review_file_count != 0
        or accountability.invalid_review_record_count != 0
        or accountability.unexpected_adjudication_file_count != 0
        or accountability.invalid_adjudication_record_count != 0
        or accountability.reviewer_independence_violation_count != 0
    ):
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_ACCOUNTABILITY_INVALID",
            "review accountability is not valid for J6 adjudication",
        )
    export, schedule, rubric, assignments = _load_inputs(root)
    cases = _material_cases(root, export, schedule, rubric, assignments)
    next_case = _select_next_case(root, cases)
    if next_case is None:
        if accountability.missing_required_adjudication_count != 0:
            raise AdjudicationQueueError(
                "FINAL_342_ADJUDICATION_QUEUE_COMPLETION_DRIFT",
                "queue is empty but required adjudications remain",
            )
        return QueueStatus(
            status="ADJUDICATION_COMPLETE",
            detected_material_disagreement_count=35,
            valid_adjudication_count=accountability.valid_adjudication_count,
            missing_required_adjudication_count=0,
        )
    if accountability.missing_required_adjudication_count <= 0:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_PENDING_DRIFT",
            "queue found pending work after accountability completed",
        )
    return QueueStatus(
        status="ADJUDICATION_PENDING",
        detected_material_disagreement_count=35,
        valid_adjudication_count=accountability.valid_adjudication_count,
        missing_required_adjudication_count=accountability.missing_required_adjudication_count,
        next_review_item_id=next_case.payload.review_item_id,
    )


def materialize_next(repo_root: Path) -> MaterializationReceipt:
    root = repo_root.resolve()
    status = queue_status(root)
    if status.status == "ADJUDICATION_COMPLETE":
        return MaterializationReceipt(
            status="ADJUDICATION_COMPLETE",
            work_item_created=False,
            submission_template_created=False,
            next_gate="J7_JEV_VS_HUMAN_CALIBRATION",
        )
    export, schedule, rubric, assignments = _load_inputs(root)
    cases = _material_cases(root, export, schedule, rubric, assignments)
    next_case = _select_next_case(root, cases)
    if next_case is None:
        raise AdjudicationQueueError(
            "FINAL_342_ADJUDICATION_QUEUE_NEXT_CASE_MISSING",
            "status reported pending adjudication but no case was selected",
        )
    work_item = build_work_item(next_case, rubric)
    review_item_id = next_case.payload.review_item_id
    package_root = root / QUEUE_ROOT / review_item_id
    work_item_path = package_root / "work_item.json"
    submission_path = package_root / "submission.json"
    work_item_bytes = _canonical_json_bytes(work_item.model_dump(mode="json"))
    submission_bytes = _canonical_json_bytes(
        _submission_template(review_item_id).model_dump(mode="json")
    )
    work_item_created = _write_once(work_item_path, work_item_bytes)
    submission_created = _write_submission_template_if_absent(
        submission_path,
        submission_bytes,
        review_item_id=review_item_id,
    )
    return MaterializationReceipt(
        status="ADJUDICATION_WORK_ITEM_READY",
        review_item_id=review_item_id,
        work_item_sha256=_sha256_bytes(work_item_bytes),
        work_item_path=work_item_path.relative_to(root).as_posix(),
        submission_path=submission_path.relative_to(root).as_posix(),
        work_item_created=work_item_created,
        submission_template_created=submission_created,
        next_gate="COMPLETE_CURRENT_INDEPENDENT_HUMAN_ADJUDICATION",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="final_342_adjudication_work_queue_v1")
    parser.add_argument("command", choices=("status", "materialize-next"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result: FrozenModel
    if args.command == "status":
        result = queue_status(args.repo_root)
    else:
        result = materialize_next(args.repo_root)
    print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
