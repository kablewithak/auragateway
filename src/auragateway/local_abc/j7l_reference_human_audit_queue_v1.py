"""Protected J7L V3 reference human-audit queue.

This module intentionally never reads model-derived J7L judgments. It materializes
the frozen 28-case reviewer-safe audit packet and persists human assessments under
.local. Model-reference comparison is a separate later boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v2 import J7LReferenceAuditScheduleV1
from auragateway.contracts.quality_semantic_projection_v1 import HumanSemanticProjectionV1
from auragateway.local_abc import quality_development_case_freeze_v1 as case_freeze

AUDIT_SCHEDULE_PATH = Path(
    ".local/auragateway/j7l-reference-execution-v3/reference_audit_schedule.json"
)
REVIEW_SCHEDULE_PATH = Path(".local/auragateway/j7l-development-v1/review/review-schedule-v1.json")
PRIMARY_EXPORT_PATH = Path(
    ".local/auragateway/j7l-development-v1/review/primary-reviewer-export-v1.json"
)
SECONDARY_EXPORT_PATH = Path(
    ".local/auragateway/j7l-development-v1/review/secondary-reviewer-export-v1.json"
)
QUEUE_ROOT = Path(".local/auragateway/j7l-reference-human-audit-v1")
WORK_ROOT = QUEUE_ROOT / "work-items"
SUBMISSION_ROOT = QUEUE_ROOT / "submissions"
ASSESSMENT_ROOT = QUEUE_ROOT / "assessments"

EXPECTED_AUDIT_SCHEDULE_SHA256 = "02a71acbe5ff1461ff91cdc874ae35453d21f156bcaf10928f8922cbedd60109"
EXPECTED_REVIEW_SCHEDULE_SHA256 = "0a526cc4ad983e0e0fe040c13703c6d09e86ebcdb9aaa839e2e14f9c6a201cf3"
EXPECTED_PRIMARY_EXPORT_SHA256 = "226eb0ceb89e6f173b2a500e1ce009b09abeb373d4086bd08cbe3c94277441fd"
EXPECTED_SECONDARY_EXPORT_SHA256 = (
    "96f636c2dc1e47746e2360d18d3f28fb80cc5832792c0214154fa7e10f188aa1"
)
OPERATOR_SHA256: Literal["a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"] = (
    "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"
)


class HumanAuditQueueError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise HumanAuditQueueError("J7L_HUMAN_AUDIT_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CriterionDraft(FrozenModel):
    criterion: RubricCriterion
    score: int | None = Field(default=None, ge=1, le=4)
    evidence_note: str | None = Field(default=None, min_length=1, max_length=4000)


class CriterionSubmission(FrozenModel):
    criterion: RubricCriterion
    score: int = Field(ge=1, le=4)
    evidence_note: str = Field(min_length=1, max_length=4000)


class SubmissionTemplate(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    criterion_scores: tuple[CriterionDraft, ...] = Field(min_length=7, max_length=7)
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = ()
    rationale: str | None = Field(default=None, min_length=20, max_length=8000)


class Submission(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    criterion_scores: tuple[CriterionSubmission, ...] = Field(min_length=7, max_length=7)
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=20, max_length=8000)

    @model_validator(mode="after")
    def validate_submission(self) -> Self:
        criteria = tuple(item.criterion for item in self.criterion_scores)
        if len(criteria) != len(set(criteria)) or set(criteria) != set(RubricCriterion):
            raise ValueError("submission must score every rubric criterion exactly once")
        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("submission failure labels must be unique")
        if len(self.evidence_references) != len(set(self.evidence_references)):
            raise ValueError("submission evidence references must be unique")
        return self


class WorkItem(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    audit_index: int = Field(ge=0, le=27)
    audit_stratum: Literal["protected_secondary", "additional_spot_check"]
    source_review_stream: Literal["primary", "secondary"]
    source_assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state: dict[str, JsonValue]
    semantic_projection: HumanSemanticProjectionV1
    reviewer_instruction: str = Field(min_length=100, max_length=1200)
    audit_actor_id_sha256: Literal[
        "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"
    ] = "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"
    model_reference_included: Literal[False] = False
    jev_output_included: Literal[False] = False
    authoring_targets_included: Literal[False] = False


class Assessment(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_REFERENCE_HUMAN_AUDIT_ASSESSMENT_COMPLETE"] = (
        "J7L_REFERENCE_HUMAN_AUDIT_ASSESSMENT_COMPLETE"
    )
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    audit_actor_id_sha256: Literal[
        "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"
    ] = "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"
    work_item_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=20, max_length=8000)
    verdict: ReviewVerdict
    model_reference_included_in_work_item: Literal[False] = False
    jev_output_included_in_work_item: Literal[False] = False

    @model_validator(mode="after")
    def validate_assessment(self) -> Self:
        if set(self.criterion_scores) != set(RubricCriterion):
            raise ValueError("assessment must score every rubric criterion")
        if any(score < 1 or score > 4 for score in self.criterion_scores.values()):
            raise ValueError("assessment scores must remain in [1,4]")
        if self.verdict is not _derived_verdict(self.criterion_scores, self.failure_labels):
            raise ValueError("assessment verdict differs from the frozen derivation rule")
        return self


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_FILE_MISSING",
            f"required protected input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_JSON_INVALID",
            f"protected input is not valid UTF-8 JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_JSON_SHAPE_INVALID",
            f"protected input root must be an object: {path.as_posix()}",
        )
    return value


def _assert_hash(path: Path, expected: str, role: str) -> None:
    if not path.is_file() or path.is_symlink() or _sha256_file(path) != expected:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_IDENTITY_DRIFT",
            f"{role} is missing, unsafe, or has drifted",
        )


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise HumanAuditQueueError(
                "J7L_HUMAN_AUDIT_OUTPUT_PATH_UNSAFE",
                "protected audit output path is unsafe",
            )
        if path.read_bytes() != payload:
            raise HumanAuditQueueError(
                "J7L_HUMAN_AUDIT_APPEND_ONLY_CONFLICT",
                "existing protected audit output differs from expected bytes",
            )
        return False
    with path.open("xb") as handle:
        handle.write(payload)
    return True


def _write_template_if_absent(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise HumanAuditQueueError(
                "J7L_HUMAN_AUDIT_SUBMISSION_PATH_UNSAFE",
                "submission path is unsafe",
            )
        return False
    with path.open("xb") as handle:
        handle.write(payload)
    return True


def _derived_verdict(
    scores: dict[RubricCriterion, int],
    labels: tuple[EpisodeFailureLabel, ...],
) -> ReviewVerdict:
    values = tuple(scores[criterion] for criterion in RubricCriterion)
    passed = sum(values) >= 21 and min(values) >= 2 and not labels
    return ReviewVerdict.PASS if passed else ReviewVerdict.FAIL


def _load_inputs(
    root: Path,
) -> tuple[
    J7LReferenceAuditScheduleV1,
    case_freeze.J7LReviewScheduleV1,
    case_freeze.J7LReviewerExportV1,
    case_freeze.J7LReviewerExportV1,
]:
    paths = (
        (root / AUDIT_SCHEDULE_PATH, EXPECTED_AUDIT_SCHEDULE_SHA256, "audit schedule"),
        (root / REVIEW_SCHEDULE_PATH, EXPECTED_REVIEW_SCHEDULE_SHA256, "review schedule"),
        (root / PRIMARY_EXPORT_PATH, EXPECTED_PRIMARY_EXPORT_SHA256, "primary export"),
        (root / SECONDARY_EXPORT_PATH, EXPECTED_SECONDARY_EXPORT_SHA256, "secondary export"),
    )
    for path, expected, role in paths:
        _assert_hash(path, expected, role)

    try:
        audit = J7LReferenceAuditScheduleV1.model_validate(_read_json(root / AUDIT_SCHEDULE_PATH))
        schedule = case_freeze.J7LReviewScheduleV1.model_validate(
            _read_json(root / REVIEW_SCHEDULE_PATH)
        )
        primary = case_freeze.J7LReviewerExportV1.model_validate(
            _read_json(root / PRIMARY_EXPORT_PATH)
        )
        secondary = case_freeze.J7LReviewerExportV1.model_validate(
            _read_json(root / SECONDARY_EXPORT_PATH)
        )
    except ValidationError as error:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_TYPED_INPUT_INVALID",
            "protected audit input failed typed validation",
        ) from error

    if audit.audit_actor_id_sha256 != OPERATOR_SHA256:
        raise HumanAuditQueueError("J7L_HUMAN_AUDIT_ACTOR_DRIFT", "audit actor drifted")
    if audit.resolution_owner_id_sha256 != OPERATOR_SHA256:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_OWNER_DRIFT",
            "resolution owner drifted",
        )
    if primary.review_stream != "primary" or primary.item_count != 48:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_PRIMARY_EXPORT_DRIFT",
            "primary export shape drifted",
        )
    if secondary.review_stream != "secondary" or secondary.item_count != 24:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_SECONDARY_EXPORT_DRIFT",
            "secondary export shape drifted",
        )
    return audit, schedule, primary, secondary


def _case_ids(
    audit: J7LReferenceAuditScheduleV1,
    schedule: case_freeze.J7LReviewScheduleV1,
) -> tuple[str, ...]:
    expected_protected = tuple(
        item.case_id
        for item in schedule.entries
        if item.family.value in {"terminal_non_substantive", "ontology_near_miss"}
    )
    ordinary = tuple(
        item.case_id for item in schedule.entries if item.family.value == "ordinary_clean"
    )
    clear_failure = tuple(
        item.case_id for item in schedule.entries if item.family.value == "clear_failure"
    )
    if audit.protected_secondary_case_ids != expected_protected:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_PROTECTED_SAMPLE_DRIFT",
            "protected 24-case sample drifted",
        )
    if audit.additional_spot_check_case_ids != ordinary[:2] + clear_failure[:2]:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_SPOT_CHECK_SAMPLE_DRIFT",
            "additional four-case sample drifted",
        )
    combined = audit.protected_secondary_case_ids + audit.additional_spot_check_case_ids
    if len(combined) != 28 or len(set(combined)) != 28:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_CASE_INVENTORY_INVALID",
            "audit inventory must contain exactly 28 unique cases",
        )
    return combined


def _work_item(
    case_id: str,
    audit_index: int,
    audit: J7LReferenceAuditScheduleV1,
    schedule: case_freeze.J7LReviewScheduleV1,
    primary: case_freeze.J7LReviewerExportV1,
    secondary: case_freeze.J7LReviewerExportV1,
) -> WorkItem:
    entry = next(item for item in schedule.entries if item.case_id == case_id)
    protected = case_id in set(audit.protected_secondary_case_ids)

    if protected:
        if entry.secondary_assignment_id is None:
            raise HumanAuditQueueError(
                "J7L_HUMAN_AUDIT_SECONDARY_ASSIGNMENT_MISSING",
                f"{case_id} has no protected secondary assignment",
            )
        assignment_id = entry.secondary_assignment_id
        item = next(
            (
                candidate
                for candidate in secondary.items
                if candidate.assignment_id == assignment_id
            ),
            None,
        )
        if item is None:
            raise HumanAuditQueueError(
                "J7L_HUMAN_AUDIT_SECONDARY_ITEM_MISSING",
                f"{case_id} secondary reviewer item is missing",
            )
        projection = secondary.semantic_projection
        instruction = secondary.reviewer_instruction
        stratum: Literal["protected_secondary", "additional_spot_check"] = "protected_secondary"
        stream: Literal["primary", "secondary"] = "secondary"
    else:
        assignment_id = entry.primary_assignment_id
        item = next(
            (candidate for candidate in primary.items if candidate.assignment_id == assignment_id),
            None,
        )
        if item is None:
            raise HumanAuditQueueError(
                "J7L_HUMAN_AUDIT_PRIMARY_ITEM_MISSING",
                f"{case_id} primary reviewer item is missing",
            )
        projection = primary.semantic_projection
        instruction = primary.reviewer_instruction
        stratum = "additional_spot_check"
        stream = "primary"

    if item.review_item_id != entry.review_item_id:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_REVIEW_ITEM_DRIFT",
            f"{case_id} review-item identity drifted",
        )
    if item.reviewer_safe_state_sha256 != entry.reviewer_safe_state_sha256:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_SAFE_STATE_DRIFT",
            f"{case_id} reviewer-safe state identity drifted",
        )
    case_freeze.assert_reviewer_export_safe(item.model_dump(mode="json"))

    return WorkItem(
        case_id=case_id,
        audit_index=audit_index,
        audit_stratum=stratum,
        source_review_stream=stream,
        source_assignment_id=assignment_id,
        review_item_id=item.review_item_id,
        reviewer_safe_state_sha256=item.reviewer_safe_state_sha256,
        reviewer_safe_state=item.reviewer_safe_state,
        semantic_projection=projection,
        reviewer_instruction=instruction,
    )


def validate_inputs(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    audit, schedule, primary, secondary = _load_inputs(root)
    case_ids = _case_ids(audit, schedule)
    for index, case_id in enumerate(case_ids):
        _work_item(case_id, index, audit, schedule, primary, secondary)
    return {
        "schema_version": "1.0.0",
        "status": "J7L_REFERENCE_HUMAN_AUDIT_INPUTS_VALID",
        "audit_case_count": 28,
        "protected_secondary_case_count": 24,
        "additional_spot_check_case_count": 4,
        "audit_actor_id_sha256": OPERATOR_SHA256,
        "resolution_owner_id_sha256": OPERATOR_SHA256,
        "model_reference_content_read": False,
        "jev_requests_performed": 0,
        "network_access_performed": False,
    }


def prepare(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    validate_inputs(root)
    audit, schedule, primary, secondary = _load_inputs(root)
    case_ids = _case_ids(audit, schedule)
    created_work_items = 0
    created_templates = 0

    for index, case_id in enumerate(case_ids):
        work = _work_item(case_id, index, audit, schedule, primary, secondary)
        work_bytes = _canonical_bytes(work.model_dump(mode="json"))
        created_work_items += int(_write_once(root / WORK_ROOT / f"{case_id}.json", work_bytes))
        template = SubmissionTemplate(
            case_id=case_id,
            criterion_scores=tuple(
                CriterionDraft(criterion=criterion) for criterion in RubricCriterion
            ),
        )
        created_templates += int(
            _write_template_if_absent(
                root / SUBMISSION_ROOT / f"{case_id}.json",
                _canonical_bytes(template.model_dump(mode="json")),
            )
        )

    return {
        "schema_version": "1.0.0",
        "status": "J7L_REFERENCE_HUMAN_AUDIT_PACKET_READY",
        "audit_case_count": 28,
        "created_work_item_count": created_work_items,
        "created_submission_template_count": created_templates,
        "work_item_root": WORK_ROOT.as_posix(),
        "submission_root": SUBMISSION_ROOT.as_posix(),
        "model_reference_content_read": False,
        "jev_requests_performed": 0,
    }


def status(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    audit, schedule, _primary, _secondary = _load_inputs(root)
    case_ids = _case_ids(audit, schedule)
    completed = []
    for case_id in case_ids:
        path = root / ASSESSMENT_ROOT / f"{case_id}.json"
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise HumanAuditQueueError(
                    "J7L_HUMAN_AUDIT_ASSESSMENT_PATH_UNSAFE",
                    f"{case_id} assessment path is unsafe",
                )
            try:
                assessment = Assessment.model_validate(_read_json(path))
            except ValidationError as error:
                raise HumanAuditQueueError(
                    "J7L_HUMAN_AUDIT_ASSESSMENT_INVALID",
                    f"{case_id} assessment failed typed validation",
                ) from error
            if assessment.case_id != case_id:
                raise HumanAuditQueueError(
                    "J7L_HUMAN_AUDIT_ASSESSMENT_CASE_DRIFT",
                    f"{case_id} assessment identity drifted",
                )
            completed.append(case_id)

    pending = tuple(case_id for case_id in case_ids if case_id not in set(completed))
    return {
        "schema_version": "1.0.0",
        "status": ("HUMAN_AUDIT_ASSESSMENTS_COMPLETE" if not pending else "HUMAN_AUDIT_PENDING"),
        "audit_case_count": 28,
        "completed_assessment_count": len(completed),
        "pending_assessment_count": len(pending),
        "next_case_id": pending[0] if pending else None,
        "next_work_item_path": ((WORK_ROOT / f"{pending[0]}.json").as_posix() if pending else None),
        "next_submission_path": (
            (SUBMISSION_ROOT / f"{pending[0]}.json").as_posix() if pending else None
        ),
        "material_disagreement_evaluated": False,
        "model_reference_content_read": False,
        "jev_requests_performed": 0,
    }


def submit(repo_root: Path, submission_file: Path) -> dict[str, object]:
    root = repo_root.resolve()
    validate_inputs(root)
    selected = submission_file if submission_file.is_absolute() else root / submission_file
    if not selected.is_file() or selected.is_symlink():
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_SUBMISSION_MISSING",
            "human-audit submission file is missing or unsafe",
        )
    try:
        selected.resolve().relative_to((root / ".local").resolve())
    except ValueError as error:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_SUBMISSION_OUTSIDE_LOCAL",
            "human-audit submission must remain under the repository .local root",
        ) from error

    try:
        submission = Submission.model_validate(_read_json(selected))
    except ValidationError as error:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_SUBMISSION_INVALID",
            "human-audit submission failed typed validation",
        ) from error

    audit, schedule, primary, secondary = _load_inputs(root)
    case_ids = _case_ids(audit, schedule)
    if submission.case_id not in set(case_ids):
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_CASE_NOT_AUTHORIZED",
            "submission case is outside the frozen audit inventory",
        )

    expected_work = _work_item(
        submission.case_id,
        case_ids.index(submission.case_id),
        audit,
        schedule,
        primary,
        secondary,
    )
    expected_work_bytes = _canonical_bytes(expected_work.model_dump(mode="json"))
    work_path = root / WORK_ROOT / f"{submission.case_id}.json"
    if not work_path.is_file() or work_path.is_symlink():
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_WORK_ITEM_MISSING",
            "submission requires its prepared protected work item",
        )
    if work_path.read_bytes() != expected_work_bytes:
        raise HumanAuditQueueError(
            "J7L_HUMAN_AUDIT_WORK_ITEM_DRIFT",
            "prepared work item differs from the frozen reviewer-safe input",
        )

    by_criterion = {item.criterion: item for item in submission.criterion_scores}
    scores = {criterion: by_criterion[criterion].score for criterion in RubricCriterion}
    assessment = Assessment(
        case_id=submission.case_id,
        work_item_sha256=hashlib.sha256(expected_work_bytes).hexdigest(),
        reviewer_safe_state_sha256=expected_work.reviewer_safe_state_sha256,
        criterion_scores=scores,
        failure_labels=submission.failure_labels,
        evidence_references=submission.evidence_references,
        rationale=submission.rationale,
        verdict=_derived_verdict(scores, submission.failure_labels),
    )
    assessment_bytes = _canonical_bytes(assessment.model_dump(mode="json"))
    created = _write_once(
        root / ASSESSMENT_ROOT / f"{submission.case_id}.json",
        assessment_bytes,
    )
    queue = status(root)
    return {
        "schema_version": "1.0.0",
        "status": "J7L_REFERENCE_HUMAN_AUDIT_ASSESSMENT_PERSISTED",
        "case_id": submission.case_id,
        "assessment_sha256": hashlib.sha256(assessment_bytes).hexdigest(),
        "created": created,
        "completed_assessment_count": queue["completed_assessment_count"],
        "pending_assessment_count": queue["pending_assessment_count"],
        "next_case_id": queue["next_case_id"],
        "model_reference_content_read": False,
        "material_disagreement_evaluated": False,
        "jev_requests_performed": 0,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=("validate-inputs", "prepare", "status", "submit"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--submission-file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-inputs":
            result = validate_inputs(args.repo_root)
        elif args.command == "prepare":
            result = prepare(args.repo_root)
        elif args.command == "status":
            result = status(args.repo_root)
        else:
            if args.submission_file is None:
                raise HumanAuditQueueError(
                    "J7L_HUMAN_AUDIT_SUBMISSION_REQUIRED",
                    "submit requires --submission-file",
                )
            result = submit(args.repo_root, args.submission_file)
    except (HumanAuditQueueError, ValidationError, OSError) as error:
        if isinstance(error, HumanAuditQueueError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, ValidationError):
            code = "J7L_HUMAN_AUDIT_TYPED_VALIDATION_FAILED"
            message = "J7L human-audit typed validation failed"
        else:
            code = "J7L_HUMAN_AUDIT_IO_FAILED"
            message = "J7L human-audit local I/O failed"
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

    print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
