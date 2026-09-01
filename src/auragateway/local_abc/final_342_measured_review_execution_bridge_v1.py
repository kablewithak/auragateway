"""Protected measured-review execution bridge for the preserved Final-342 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.contracts.blinded_quality import (
    AdjudicationRecord,
    BlindedQualityRubric,
    CriterionScore,
    QualityReviewRecord,
    ReviewRole,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.evals import blinded_quality as blinded_eval
from auragateway.local_abc import final_342_measured_review_design_v1 as review_design
from auragateway.local_abc import final_342_measured_review_successor_v1 as review_successor
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

TRANSACTION_ID: Literal["16136113b163494ddd366e33a4a7553eafef9c42bd7c57e4e2f3be651fb1c8ab"] = (
    "16136113b163494ddd366e33a4a7553eafef9c42bd7c57e4e2f3be651fb1c8ab"
)
SAVED_VERSION_ID: Literal[346383612] = 346383612

PROTECTED_REVIEW_ROOT = Path(".local/auragateway/final-342-protected-review-v1")
CUSTODY_RECEIPT_PATH = Path(
    ".local/auragateway/final-342-protected-review-custody-v1/"
    "protected_review_public_receipt_v1.json"
)
RUBRIC_PATH = Path("data/evals/quality/blinded-v1/rubric.json")

EXPECTED_EXPORT_SHA256 = "4f4d34fa57420b460b11b99a43b1af9ee46d15e51d8864ad7429184b4dacabed"
EXPECTED_SCHEDULE_SHA256 = "9566edb218c2d9c6459e8428bc93676bc1e73484b2fd56a249aed2cc1db6748c"
EXPECTED_RUBRIC_SHA256 = "7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"

EXPECTED_REVIEW_ITEM_COUNT = 162
EXPECTED_PRIMARY_ASSIGNMENT_COUNT = 162
EXPECTED_SECONDARY_ASSIGNMENT_COUNT = 41
EXPECTED_ASSIGNMENT_COUNT = 203

REVIEW_RESULT_ROOT = Path(".local/auragateway/final-342-measured-review-execution-v1")


class ReviewBridgeError(RuntimeError):
    """Fail-closed measured-review bridge error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExpectedReviewAssignment(FrozenModel):
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    role: Literal["primary", "secondary"]


class BridgeInputState(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    bridge_id: Literal["auragateway-final-342-measured-review-execution-bridge-v1"] = (
        "auragateway-final-342-measured-review-execution-bridge-v1"
    )
    status: Literal["FINAL_342_MEASURED_REVIEW_INPUTS_READY"] = (
        "FINAL_342_MEASURED_REVIEW_INPUTS_READY"
    )

    transaction_id: Literal["16136113b163494ddd366e33a4a7553eafef9c42bd7c57e4e2f3be651fb1c8ab"] = (
        TRANSACTION_ID
    )
    saved_version_id: Literal[346383612] = SAVED_VERSION_ID

    review_item_count: Literal[162]
    primary_assignment_count: Literal[162]
    secondary_assignment_count: Literal[41]
    assignment_count: Literal[203]

    protected_export_sha256: Literal[
        "4f4d34fa57420b460b11b99a43b1af9ee46d15e51d8864ad7429184b4dacabed"
    ]
    protected_schedule_sha256: Literal[
        "9566edb218c2d9c6459e8428bc93676bc1e73484b2fd56a249aed2cc1db6748c"
    ]
    rubric_sha256: Literal["7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"]
    assignment_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    protected_raw_content_logged: Literal[False] = False
    review_results_produced: Literal[False] = False
    quality_review_completed: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False

    next_gate: Literal["IMPLEMENT_FINAL_342_APPEND_ONLY_REVIEW_SUBMISSION_V1"] = (
        "IMPLEMENT_FINAL_342_APPEND_ONLY_REVIEW_SUBMISSION_V1"
    )


def _require_file(path: Path) -> Path:
    if not path.is_file() or path.is_symlink():
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_FILE_MISSING",
            f"required review bridge file is missing or unsafe: {path.as_posix()}",
        )
    return path


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(_require_file(path).read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_JSON_INVALID",
            f"review bridge JSON is invalid: {path.as_posix()}",
        ) from error

    if not isinstance(value, dict):
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_JSON_SHAPE_INVALID",
            f"review bridge JSON root must be an object: {path.as_posix()}",
        )
    return value


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(_require_file(path).read_bytes()).hexdigest()


def _inventory_sha256(
    assignments: tuple[ExpectedReviewAssignment, ...],
) -> str:
    payload = [item.model_dump(mode="json") for item in assignments]
    return hashlib.sha256(review_successor.canonical_json_bytes(payload)).hexdigest()


def project_expected_assignments(
    export: review_successor.ProtectedExport,
    schedule: review_successor.ProtectedSchedule,
) -> tuple[ExpectedReviewAssignment, ...]:
    secondary_by_item = {
        item.review_item_id: item.secondary_assignment_id for item in schedule.entries
    }

    projected: list[ExpectedReviewAssignment] = []

    for payload in export.assignments:
        primary_assignment_id = review_design.role_assignment_id(
            payload.review_item_id,
            "primary",
        )
        secondary_assignment_id = secondary_by_item.get(payload.review_item_id)

        role: Literal["primary", "secondary"]

        if payload.assignment_id == primary_assignment_id:
            role = "primary"
        elif (
            secondary_assignment_id is not None and payload.assignment_id == secondary_assignment_id
        ):
            role = "secondary"
        else:
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_ASSIGNMENT_IDENTITY_INVALID",
                "protected reviewer export contains an assignment that does not "
                "match the frozen primary or secondary identity",
            )

        projected.append(
            ExpectedReviewAssignment(
                assignment_id=payload.assignment_id,
                review_item_id=payload.review_item_id,
                episode_id=payload.episode_id,
                role=role,
            )
        )

    assignments = tuple(projected)

    assignment_ids = tuple(item.assignment_id for item in assignments)
    review_item_ids = {item.review_item_id for item in assignments}
    primary = tuple(item for item in assignments if item.role == "primary")
    secondary = tuple(item for item in assignments if item.role == "secondary")

    if len(assignment_ids) != len(set(assignment_ids)):
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ASSIGNMENT_DUPLICATE",
            "protected reviewer assignment IDs must be unique",
        )

    if export.assignment_count != len(assignments):
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ASSIGNMENT_COUNT_DRIFT",
            "protected reviewer export assignment count drifted",
        )

    if export.review_item_count != len(review_item_ids):
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_REVIEW_ITEM_COUNT_DRIFT",
            "protected reviewer export review-item count drifted",
        )

    if len(review_item_ids) != EXPECTED_REVIEW_ITEM_COUNT:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_REVIEW_POPULATION_INVALID",
            "Final-342 protected review population must contain exactly 162 items",
        )

    if len(primary) != EXPECTED_PRIMARY_ASSIGNMENT_COUNT:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_PRIMARY_COUNT_INVALID",
            "Final-342 requires exactly 162 primary review assignments",
        )

    if len(secondary) != EXPECTED_SECONDARY_ASSIGNMENT_COUNT:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_SECONDARY_COUNT_INVALID",
            "Final-342 requires exactly 41 secondary review assignments",
        )

    if len(assignments) != EXPECTED_ASSIGNMENT_COUNT:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_TOTAL_ASSIGNMENT_COUNT_INVALID",
            "Final-342 requires exactly 203 blinded review assignments",
        )

    primary_items = {item.review_item_id for item in primary}
    if primary_items != review_item_ids:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_PRIMARY_COVERAGE_INCOMPLETE",
            "every protected review item requires exactly one primary assignment",
        )

    projected_secondary = {item.review_item_id: item.assignment_id for item in secondary}
    if projected_secondary != secondary_by_item:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_SECONDARY_SCHEDULE_DRIFT",
            "secondary assignments differ from the frozen review schedule",
        )

    return assignments


def validate_inputs(
    repo_root: Path,
    *,
    protected_root: Path | None = None,
    custody_receipt_path: Path | None = None,
) -> BridgeInputState:
    root = repo_root.resolve()

    selected_protected_root = (
        protected_root if protected_root is not None else root / PROTECTED_REVIEW_ROOT
    )
    selected_receipt_path = (
        custody_receipt_path if custody_receipt_path is not None else root / CUSTODY_RECEIPT_PATH
    )

    export_path = selected_protected_root / review_successor.PROTECTED_EXPORT_PATH.name
    schedule_path = selected_protected_root / review_successor.PROTECTED_SCHEDULE_PATH.name
    rubric_path = root / RUBRIC_PATH

    export_sha256 = _sha256_file(export_path)
    schedule_sha256 = _sha256_file(schedule_path)
    rubric_sha256 = _sha256_file(rubric_path)

    if export_sha256 != EXPECTED_EXPORT_SHA256:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_EXPORT_IDENTITY_DRIFT",
            "protected reviewer export identity drifted",
        )

    if schedule_sha256 != EXPECTED_SCHEDULE_SHA256:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_SCHEDULE_IDENTITY_DRIFT",
            "protected review schedule identity drifted",
        )

    if rubric_sha256 != EXPECTED_RUBRIC_SHA256:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_RUBRIC_IDENTITY_DRIFT",
            "frozen review rubric identity drifted",
        )

    export = review_successor.ProtectedExport.model_validate(_read_json_object(export_path))
    schedule = review_successor.ProtectedSchedule.model_validate(_read_json_object(schedule_path))
    BlindedQualityRubric.model_validate(_read_json_object(rubric_path))

    receipt = core.ProtectedReviewPublicReceipt.model_validate(
        _read_json_object(selected_receipt_path)
    )

    if receipt.export_sha256 != export_sha256:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_RECEIPT_EXPORT_MISMATCH",
            "protected public receipt does not bind the accepted reviewer export",
        )

    if receipt.item_count != EXPECTED_REVIEW_ITEM_COUNT:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_RECEIPT_POPULATION_DRIFT",
            "protected public receipt review-item count drifted",
        )

    assignments = project_expected_assignments(
        export,
        schedule,
    )

    return BridgeInputState(
        review_item_count=EXPECTED_REVIEW_ITEM_COUNT,
        primary_assignment_count=EXPECTED_PRIMARY_ASSIGNMENT_COUNT,
        secondary_assignment_count=EXPECTED_SECONDARY_ASSIGNMENT_COUNT,
        assignment_count=EXPECTED_ASSIGNMENT_COUNT,
        protected_export_sha256=EXPECTED_EXPORT_SHA256,
        protected_schedule_sha256=EXPECTED_SCHEDULE_SHA256,
        rubric_sha256=EXPECTED_RUBRIC_SHA256,
        assignment_inventory_sha256=_inventory_sha256(assignments),
    )


class CriterionSubmission(FrozenModel):
    criterion: RubricCriterion
    score: int = Field(ge=1, le=4)
    evidence_note: str = Field(min_length=1, max_length=4000)


class ReviewSubmissionDraft(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    reviewer_key: str = Field(min_length=3, max_length=200)
    criterion_scores: tuple[CriterionSubmission, ...] = Field(
        min_length=7,
        max_length=7,
    )
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    rationale: str = Field(min_length=1, max_length=8000)

    @model_validator(mode="after")
    def validate_submission(self) -> ReviewSubmissionDraft:
        criteria = tuple(item.criterion for item in self.criterion_scores)

        if len(criteria) != len(set(criteria)):
            raise ValueError("review submission criterion scores must be unique")

        if set(criteria) != set(RubricCriterion):
            raise ValueError("review submission must score every rubric criterion")

        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("review submission failure labels must be unique")

        return self


class ReviewSubmissionReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    role: Literal["primary", "secondary"]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created: bool

    raw_submission_persisted_by_bridge: Literal[False] = False
    raw_reviewer_key_persisted: Literal[False] = False
    raw_evidence_notes_persisted: Literal[False] = False
    raw_rationale_persisted: Literal[False] = False
    raw_protected_content_logged: Literal[False] = False

    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_review_bytes(
    value: QualityReviewRecord,
) -> bytes:
    return review_successor.canonical_json_bytes(value.model_dump(mode="json"))


def _find_expected_assignment(
    assignments: tuple[ExpectedReviewAssignment, ...],
    assignment_id: str,
) -> ExpectedReviewAssignment:
    matches = tuple(item for item in assignments if item.assignment_id == assignment_id)

    if len(matches) != 1:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ASSIGNMENT_NOT_FOUND",
            "review submission does not match exactly one frozen assignment",
        )

    return matches[0]


def _find_primary_assignment(
    assignments: tuple[ExpectedReviewAssignment, ...],
    review_item_id: str,
) -> ExpectedReviewAssignment:
    matches = tuple(
        item
        for item in assignments
        if (item.review_item_id == review_item_id and item.role == "primary")
    )

    if len(matches) != 1:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_PRIMARY_ASSIGNMENT_INVALID",
            "review item does not have exactly one frozen primary assignment",
        )

    return matches[0]


def _review_result_path(
    result_root: Path,
    assignment_id: str,
) -> Path:
    return result_root / "reviews" / f"{assignment_id}.json"


def _write_once_review(
    path: Path,
    payload: bytes,
) -> bool:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_RESULT_PATH_UNSAFE",
                "review result path is not a regular file",
            )

        if path.read_bytes() != payload:
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_APPEND_ONLY_CONFLICT",
                "existing review result differs from submitted review",
            )

        return False

    temporary = path.with_name(f".{path.name}.tmp")

    if temporary.exists():
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_TEMP_RESIDUE",
            "review result temporary path already exists",
        )

    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    try:
        os.rename(
            temporary,
            path,
        )
    except OSError:
        if temporary.exists():
            temporary.unlink()

        if path.is_file() and not path.is_symlink() and path.read_bytes() == payload:
            return False

        raise

    return True


def persist_review_record(
    review: QualityReviewRecord,
    result_root: Path,
) -> tuple[Path, str, bool]:
    payload = _canonical_review_bytes(review)
    digest = hashlib.sha256(payload).hexdigest()

    target = _review_result_path(
        result_root,
        review.review_id,
    )

    created = _write_once_review(
        target,
        payload,
    )

    return target, digest, created


def _load_persisted_review(
    path: Path,
    rubric: BlindedQualityRubric,
) -> QualityReviewRecord:
    try:
        review = QualityReviewRecord.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_PERSISTED_REVIEW_INVALID",
            "persisted review result failed typed validation",
        ) from error

    expected = blinded_eval.expected_verdict(
        review.criterion_scores,
        len(review.failure_labels),
        rubric,
    )

    if review.verdict is not expected:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_PERSISTED_VERDICT_INVALID",
            "persisted review verdict differs from frozen rubric",
        )

    return review


def build_review_record(
    assignment: ExpectedReviewAssignment,
    submission: ReviewSubmissionDraft,
    rubric: BlindedQualityRubric,
    *,
    primary_review: QualityReviewRecord | None = None,
) -> QualityReviewRecord:
    if submission.assignment_id != assignment.assignment_id:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_SUBMISSION_ASSIGNMENT_MISMATCH",
            "review submission assignment identity drifted",
        )

    reviewer_id_sha256 = _sha256_text(submission.reviewer_key)

    role = ReviewRole.PRIMARY if assignment.role == "primary" else ReviewRole.SECONDARY

    if role is ReviewRole.PRIMARY and primary_review is not None:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_PRIMARY_DEPENDENCY_INVALID",
            "primary review submission cannot depend on another primary review",
        )

    if role is ReviewRole.SECONDARY:
        if primary_review is None:
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_PRIMARY_REVIEW_REQUIRED",
                "secondary review requires the completed primary review",
            )

        if (
            primary_review.episode_id != assignment.episode_id
            or primary_review.role is not ReviewRole.PRIMARY
        ):
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_PRIMARY_REVIEW_IDENTITY_INVALID",
                "secondary review primary dependency identity drifted",
            )

        if primary_review.reviewer_id_sha256 == reviewer_id_sha256:
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_REVIEWER_INDEPENDENCE_VIOLATION",
                "primary and secondary reviews require independent reviewers",
            )

    submitted_by_criterion = {item.criterion: item for item in submission.criterion_scores}

    criterion_scores = tuple(
        CriterionScore(
            criterion=criterion,
            score=submitted_by_criterion[criterion].score,
            evidence_note_sha256=_sha256_text(submitted_by_criterion[criterion].evidence_note),
        )
        for criterion in RubricCriterion
    )

    verdict = blinded_eval.expected_verdict(
        criterion_scores,
        len(submission.failure_labels),
        rubric,
    )

    return QualityReviewRecord(
        review_id=assignment.assignment_id,
        episode_id=assignment.episode_id,
        reviewer_id_sha256=reviewer_id_sha256,
        role=role,
        criterion_scores=criterion_scores,
        failure_labels=submission.failure_labels,
        verdict=verdict,
        rationale_sha256=_sha256_text(submission.rationale),
    )


def _submission_file(
    root: Path,
    path: Path,
) -> Path:
    selected = path if path.is_absolute() else root / path

    if not selected.is_file() or selected.is_symlink():
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_SUBMISSION_FILE_MISSING",
            "review submission file is missing or unsafe",
        )

    local_root = (root / ".local").resolve()
    resolved = selected.resolve()

    try:
        resolved.relative_to(local_root)
    except ValueError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_SUBMISSION_OUTSIDE_PROTECTED_LOCAL_ROOT",
            "raw review submission must remain under the repository .local root",
        ) from error

    return resolved


def _load_submission(
    path: Path,
) -> ReviewSubmissionDraft:
    try:
        return ReviewSubmissionDraft.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_SUBMISSION_INVALID",
            "raw review submission failed typed validation",
        ) from error


def _load_review_inputs(
    root: Path,
    protected_root: Path,
) -> tuple[
    review_successor.ProtectedExport,
    review_successor.ProtectedSchedule,
    BlindedQualityRubric,
    tuple[ExpectedReviewAssignment, ...],
]:
    export_path = protected_root / review_successor.PROTECTED_EXPORT_PATH.name
    schedule_path = protected_root / review_successor.PROTECTED_SCHEDULE_PATH.name
    rubric_path = root / RUBRIC_PATH

    try:
        export = review_successor.ProtectedExport.model_validate(_read_json_object(export_path))
        schedule = review_successor.ProtectedSchedule.model_validate(
            _read_json_object(schedule_path)
        )
        rubric = BlindedQualityRubric.model_validate(_read_json_object(rubric_path))
    except ValidationError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_INPUT_MODEL_INVALID",
            "measured-review bridge input failed typed validation",
        ) from error

    assignments = project_expected_assignments(
        export,
        schedule,
    )

    return (
        export,
        schedule,
        rubric,
        assignments,
    )


def submit_review(
    repo_root: Path,
    submission_path: Path,
    *,
    result_root: Path | None = None,
    protected_root: Path | None = None,
    custody_receipt_path: Path | None = None,
) -> ReviewSubmissionReceipt:
    root = repo_root.resolve()

    selected_protected_root = (
        protected_root if protected_root is not None else root / PROTECTED_REVIEW_ROOT
    )

    selected_result_root = result_root if result_root is not None else root / REVIEW_RESULT_ROOT

    validate_inputs(
        root,
        protected_root=selected_protected_root,
        custody_receipt_path=custody_receipt_path,
    )

    (
        _export,
        _schedule,
        rubric,
        assignments,
    ) = _load_review_inputs(
        root,
        selected_protected_root,
    )

    raw_submission_path = _submission_file(
        root,
        submission_path,
    )

    submission = _load_submission(raw_submission_path)

    assignment = _find_expected_assignment(
        assignments,
        submission.assignment_id,
    )

    primary_review: QualityReviewRecord | None = None

    if assignment.role == "secondary":
        primary_assignment = _find_primary_assignment(
            assignments,
            assignment.review_item_id,
        )

        primary_path = _review_result_path(
            selected_result_root,
            primary_assignment.assignment_id,
        )

        if not primary_path.is_file() or primary_path.is_symlink():
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_PRIMARY_REVIEW_REQUIRED",
                "secondary review requires a persisted primary review",
            )

        primary_review = _load_persisted_review(
            primary_path,
            rubric,
        )

        if primary_review.review_id != primary_assignment.assignment_id:
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_PRIMARY_REVIEW_IDENTITY_INVALID",
                "persisted primary review assignment identity drifted",
            )

    review = build_review_record(
        assignment,
        submission,
        rubric,
        primary_review=primary_review,
    )

    _target, digest, created = persist_review_record(
        review,
        selected_result_root,
    )

    return ReviewSubmissionReceipt(
        assignment_id=assignment.assignment_id,
        episode_id=assignment.episode_id,
        role=assignment.role,
        review_sha256=digest,
        created=created,
    )


class AdjudicationSubmissionDraft(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    adjudicator_key: str = Field(min_length=3, max_length=200)
    criterion_scores: tuple[CriterionSubmission, ...] = Field(
        min_length=7,
        max_length=7,
    )
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    rationale: str = Field(min_length=1, max_length=8000)

    @model_validator(mode="after")
    def validate_submission(self) -> AdjudicationSubmissionDraft:
        criteria = tuple(item.criterion for item in self.criterion_scores)

        if len(criteria) != len(set(criteria)):
            raise ValueError("adjudication criterion scores must be unique")

        if set(criteria) != set(RubricCriterion):
            raise ValueError("adjudication must score every rubric criterion")

        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("adjudication failure labels must be unique")

        return self


class AdjudicationSubmissionReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    primary_review_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    secondary_review_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    adjudication_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created: bool

    raw_submission_persisted_by_bridge: Literal[False] = False
    raw_adjudicator_key_persisted: Literal[False] = False
    raw_evidence_notes_persisted: Literal[False] = False
    raw_rationale_persisted: Literal[False] = False
    raw_protected_content_logged: Literal[False] = False

    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False


def _find_secondary_assignment(
    assignments: tuple[ExpectedReviewAssignment, ...],
    review_item_id: str,
) -> ExpectedReviewAssignment:
    matches = tuple(
        item
        for item in assignments
        if (item.review_item_id == review_item_id and item.role == "secondary")
    )

    if len(matches) != 1:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_SECONDARY_ASSIGNMENT_INVALID",
            "review item does not have exactly one frozen secondary assignment",
        )

    return matches[0]


def _adjudication_result_path(
    result_root: Path,
    review_item_id: str,
) -> Path:
    return result_root / "adjudications" / f"{review_item_id}.json"


def _canonical_adjudication_bytes(
    value: AdjudicationRecord,
) -> bytes:
    return review_successor.canonical_json_bytes(value.model_dump(mode="json"))


def persist_adjudication_record(
    adjudication: AdjudicationRecord,
    review_item_id: str,
    result_root: Path,
) -> tuple[Path, str, bool]:
    payload = _canonical_adjudication_bytes(adjudication)

    digest = hashlib.sha256(payload).hexdigest()

    target = _adjudication_result_path(
        result_root,
        review_item_id,
    )

    created = _write_once_review(
        target,
        payload,
    )

    return target, digest, created


def build_adjudication_record(
    primary_assignment: ExpectedReviewAssignment,
    secondary_assignment: ExpectedReviewAssignment,
    submission: AdjudicationSubmissionDraft,
    primary_review: QualityReviewRecord,
    secondary_review: QualityReviewRecord,
    rubric: BlindedQualityRubric,
) -> AdjudicationRecord:
    if primary_assignment.role != "primary":
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_PRIMARY_ROLE_INVALID",
            "adjudication requires a frozen primary assignment",
        )

    if secondary_assignment.role != "secondary":
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_SECONDARY_ROLE_INVALID",
            "adjudication requires a frozen secondary assignment",
        )

    if primary_assignment.review_item_id != secondary_assignment.review_item_id:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_REVIEW_ITEM_MISMATCH",
            "primary and secondary assignments refer to different review items",
        )

    if submission.review_item_id != primary_assignment.review_item_id:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_SUBMISSION_IDENTITY_DRIFT",
            "adjudication submission review-item identity drifted",
        )

    if (
        primary_review.review_id != primary_assignment.assignment_id
        or primary_review.role is not ReviewRole.PRIMARY
    ):
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_PRIMARY_REVIEW_INVALID",
            "persisted primary review does not match its frozen assignment",
        )

    if (
        secondary_review.review_id != secondary_assignment.assignment_id
        or secondary_review.role is not ReviewRole.SECONDARY
    ):
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_SECONDARY_REVIEW_INVALID",
            "persisted secondary review does not match its frozen assignment",
        )

    try:
        disagreement = blinded_eval.detect_material_disagreement(
            primary_review,
            secondary_review,
            rubric,
        )
    except blinded_eval.BlindedQualityError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_DISAGREEMENT_INPUT_INVALID",
            error.safe_message,
        ) from error

    if disagreement is None:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_NOT_REQUIRED",
            "adjudication is prohibited without material disagreement",
        )

    submitted_by_criterion = {item.criterion: item for item in submission.criterion_scores}

    final_scores = tuple(
        CriterionScore(
            criterion=criterion,
            score=submitted_by_criterion[criterion].score,
            evidence_note_sha256=_sha256_text(submitted_by_criterion[criterion].evidence_note),
        )
        for criterion in RubricCriterion
    )

    final_verdict = blinded_eval.expected_verdict(
        final_scores,
        len(submission.failure_labels),
        rubric,
    )

    adjudication = AdjudicationRecord(
        episode_id=primary_review.episode_id,
        primary_review_id=primary_review.review_id,
        secondary_review_id=secondary_review.review_id,
        adjudicator_id_sha256=_sha256_text(submission.adjudicator_key),
        final_criterion_scores=final_scores,
        final_failure_labels=submission.failure_labels,
        final_verdict=final_verdict,
        rationale_sha256=_sha256_text(submission.rationale),
    )

    try:
        blinded_eval.validate_adjudication(
            adjudication,
            primary_review,
            secondary_review,
            disagreement,
            rubric,
        )
    except blinded_eval.BlindedQualityError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_INVALID",
            error.safe_message,
        ) from error

    return adjudication


def _load_adjudication_submission(
    path: Path,
) -> AdjudicationSubmissionDraft:
    try:
        return AdjudicationSubmissionDraft.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_SUBMISSION_INVALID",
            "raw adjudication submission failed typed validation",
        ) from error


def submit_adjudication(
    repo_root: Path,
    submission_path: Path,
    *,
    result_root: Path | None = None,
    protected_root: Path | None = None,
    custody_receipt_path: Path | None = None,
) -> AdjudicationSubmissionReceipt:
    root = repo_root.resolve()

    selected_protected_root = (
        protected_root if protected_root is not None else root / PROTECTED_REVIEW_ROOT
    )

    selected_result_root = result_root if result_root is not None else root / REVIEW_RESULT_ROOT

    validate_inputs(
        root,
        protected_root=selected_protected_root,
        custody_receipt_path=custody_receipt_path,
    )

    (
        _export,
        _schedule,
        rubric,
        assignments,
    ) = _load_review_inputs(
        root,
        selected_protected_root,
    )

    raw_submission_path = _submission_file(
        root,
        submission_path,
    )

    submission = _load_adjudication_submission(raw_submission_path)

    primary_assignment = _find_primary_assignment(
        assignments,
        submission.review_item_id,
    )

    secondary_assignment = _find_secondary_assignment(
        assignments,
        submission.review_item_id,
    )

    primary_path = _review_result_path(
        selected_result_root,
        primary_assignment.assignment_id,
    )

    secondary_path = _review_result_path(
        selected_result_root,
        secondary_assignment.assignment_id,
    )

    if not primary_path.is_file() or primary_path.is_symlink():
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_PRIMARY_REQUIRED",
            "adjudication requires a persisted primary review",
        )

    if not secondary_path.is_file() or secondary_path.is_symlink():
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_SECONDARY_REQUIRED",
            "adjudication requires a persisted secondary review",
        )

    primary_review = _load_persisted_review(
        primary_path,
        rubric,
    )

    secondary_review = _load_persisted_review(
        secondary_path,
        rubric,
    )

    adjudication = build_adjudication_record(
        primary_assignment,
        secondary_assignment,
        submission,
        primary_review,
        secondary_review,
        rubric,
    )

    _target, digest, created = persist_adjudication_record(
        adjudication,
        submission.review_item_id,
        selected_result_root,
    )

    return AdjudicationSubmissionReceipt(
        review_item_id=submission.review_item_id,
        primary_review_id=primary_review.review_id,
        secondary_review_id=secondary_review.review_id,
        adjudication_sha256=digest,
        created=created,
    )


class ReviewCompletionAccountability(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["INCOMPLETE", "COMPLETE"]

    expected_primary_review_count: Literal[162] = 162
    valid_primary_review_count: int = Field(ge=0, le=162)
    missing_primary_review_count: int = Field(ge=0, le=162)

    expected_secondary_review_count: Literal[41] = 41
    valid_secondary_review_count: int = Field(ge=0, le=41)
    missing_secondary_review_count: int = Field(ge=0, le=41)

    review_file_count: int = Field(ge=0)
    unexpected_review_file_count: int = Field(ge=0)
    invalid_review_record_count: int = Field(ge=0)

    complete_secondary_pair_count: int = Field(ge=0, le=41)
    pending_secondary_pair_count: int = Field(ge=0, le=41)
    reviewer_independence_violation_count: int = Field(ge=0)

    detected_material_disagreement_count: int = Field(ge=0, le=41)
    currently_required_adjudication_count: int = Field(ge=0, le=41)
    adjudication_requirement_fully_determined: bool

    adjudication_file_count: int = Field(ge=0)
    valid_adjudication_count: int = Field(ge=0, le=41)
    missing_required_adjudication_count: int = Field(ge=0, le=41)
    unexpected_adjudication_file_count: int = Field(ge=0)
    invalid_adjudication_record_count: int = Field(ge=0)

    unresolved_material_disagreement_count: int = Field(
        ge=0,
        le=41,
    )

    review_complete: bool
    adjudication_complete: bool
    overall_review_evidence_complete: bool

    raw_protected_content_logged: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False

    next_gate: Literal[
        "COMPLETE_FINAL_342_HUMAN_REVIEW_V1",
        "MATERIALIZE_FINAL_342_MEASURED_QUALITY_INPUTS_V1",
    ]

    @model_validator(mode="after")
    def validate_accountability(
        self,
    ) -> ReviewCompletionAccountability:
        if (
            self.valid_primary_review_count + self.missing_primary_review_count
            != self.expected_primary_review_count
        ):
            raise ValueError("primary review counts must reconcile")

        if (
            self.valid_secondary_review_count + self.missing_secondary_review_count
            != self.expected_secondary_review_count
        ):
            raise ValueError("secondary review counts must reconcile")

        if (
            self.complete_secondary_pair_count + self.pending_secondary_pair_count
            != self.expected_secondary_review_count
        ):
            raise ValueError("secondary pair counts must reconcile")

        if self.currently_required_adjudication_count != self.detected_material_disagreement_count:
            raise ValueError(
                "required adjudication count must match detected material disagreements"
            )

        if (
            self.valid_adjudication_count + self.missing_required_adjudication_count
            != self.currently_required_adjudication_count
        ):
            raise ValueError("required adjudication counts must reconcile")

        if self.unresolved_material_disagreement_count != self.missing_required_adjudication_count:
            raise ValueError("unresolved disagreements must match missing valid adjudications")

        complete_status = self.status == "COMPLETE"

        if complete_status != self.overall_review_evidence_complete:
            raise ValueError("completion status must match overall evidence state")

        if self.overall_review_evidence_complete != self.adjudication_complete:
            raise ValueError("overall completion requires completed adjudication")

        return self


def _direct_result_files(
    directory: Path,
) -> tuple[Path, ...]:
    if not directory.exists():
        return ()

    if directory.is_symlink() or not directory.is_dir():
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_RESULT_DIRECTORY_UNSAFE",
            "review result directory is not a real directory",
        )

    files: list[Path] = []

    for child in directory.iterdir():
        if child.is_symlink() or not child.is_file():
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_RESULT_TREE_UNSAFE",
                "review result directory contains an unsafe entry",
            )

        files.append(child)

    return tuple(
        sorted(
            files,
            key=lambda item: item.name,
        )
    )


def _load_review_for_assignment(
    path: Path,
    assignment: ExpectedReviewAssignment,
    rubric: BlindedQualityRubric,
) -> QualityReviewRecord:
    review = _load_persisted_review(
        path,
        rubric,
    )

    expected_role = ReviewRole.PRIMARY if assignment.role == "primary" else ReviewRole.SECONDARY

    if review.review_id != assignment.assignment_id:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_REVIEW_ID_INVALID",
            "persisted review does not match its frozen assignment",
        )

    if review.episode_id != assignment.episode_id:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_EPISODE_INVALID",
            "persisted review episode identity drifted",
        )

    if review.role is not expected_role:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_ROLE_INVALID",
            "persisted review role differs from frozen assignment",
        )

    return review


def _load_adjudication_for_pair(
    path: Path,
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
    rubric: BlindedQualityRubric,
) -> AdjudicationRecord:
    try:
        adjudication = AdjudicationRecord.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_ADJUDICATION_INVALID",
            "persisted adjudication failed typed validation",
        ) from error

    try:
        disagreement = blinded_eval.detect_material_disagreement(
            primary,
            secondary,
            rubric,
        )
    except blinded_eval.BlindedQualityError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_PAIR_INVALID",
            error.safe_message,
        ) from error

    if disagreement is None:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_ADJUDICATION_UNEXPECTED",
            "persisted adjudication has no material disagreement",
        )

    try:
        blinded_eval.validate_adjudication(
            adjudication,
            primary,
            secondary,
            disagreement,
            rubric,
        )
    except blinded_eval.BlindedQualityError as error:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_ADJUDICATION_INVALID",
            error.safe_message,
        ) from error

    return adjudication


def build_review_accountability(
    assignments: tuple[ExpectedReviewAssignment, ...],
    rubric: BlindedQualityRubric,
    result_root: Path,
) -> ReviewCompletionAccountability:
    if result_root.exists() and (result_root.is_symlink() or not result_root.is_dir()):
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_RESULT_ROOT_UNSAFE",
            "review result root is not a real directory",
        )

    primary_assignments = {
        item.review_item_id: item for item in assignments if item.role == "primary"
    }

    secondary_assignments = {
        item.review_item_id: item for item in assignments if item.role == "secondary"
    }

    if len(primary_assignments) != 162:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_PRIMARY_SET_INVALID",
            "accountability requires exactly 162 primary assignments",
        )

    if len(secondary_assignments) != 41:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_SECONDARY_SET_INVALID",
            "accountability requires exactly 41 secondary assignments",
        )

    reviews_root = result_root / "reviews"

    review_files = _direct_result_files(reviews_root)

    expected_review_names = {f"{item.assignment_id}.json": item for item in assignments}

    unexpected_review_files = tuple(
        path for path in review_files if path.name not in expected_review_names
    )

    files_by_name = {path.name: path for path in review_files}

    valid_reviews: dict[
        str,
        QualityReviewRecord,
    ] = {}

    invalid_review_record_count = 0

    for assignment in assignments:
        file_name = f"{assignment.assignment_id}.json"

        path = files_by_name.get(file_name)

        if path is None:
            continue

        try:
            review = _load_review_for_assignment(
                path,
                assignment,
                rubric,
            )
        except ReviewBridgeError:
            invalid_review_record_count += 1
            continue

        valid_reviews[assignment.assignment_id] = review

    valid_primary_review_count = sum(
        1
        for assignment in primary_assignments.values()
        if assignment.assignment_id in valid_reviews
    )

    valid_secondary_review_count = sum(
        1
        for assignment in secondary_assignments.values()
        if assignment.assignment_id in valid_reviews
    )

    complete_secondary_pair_count = 0
    reviewer_independence_violation_count = 0

    required_adjudications: dict[
        str,
        tuple[
            QualityReviewRecord,
            QualityReviewRecord,
        ],
    ] = {}

    for review_item_id, secondary_assignment in secondary_assignments.items():
        primary_assignment = primary_assignments[review_item_id]

        primary_review = valid_reviews.get(primary_assignment.assignment_id)

        secondary_review = valid_reviews.get(secondary_assignment.assignment_id)

        if primary_review is None or secondary_review is None:
            continue

        complete_secondary_pair_count += 1

        if primary_review.reviewer_id_sha256 == secondary_review.reviewer_id_sha256:
            reviewer_independence_violation_count += 1
            continue

        try:
            disagreement = blinded_eval.detect_material_disagreement(
                primary_review,
                secondary_review,
                rubric,
            )
        except blinded_eval.BlindedQualityError as error:
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_ACCOUNTABILITY_PAIR_INVALID",
                error.safe_message,
            ) from error

        if disagreement is not None:
            required_adjudications[review_item_id] = (
                primary_review,
                secondary_review,
            )

    pending_secondary_pair_count = 41 - complete_secondary_pair_count

    adjudication_requirement_fully_determined = (
        complete_secondary_pair_count == 41 and reviewer_independence_violation_count == 0
    )

    adjudications_root = result_root / "adjudications"

    adjudication_files = _direct_result_files(adjudications_root)

    required_adjudication_names = {
        f"{review_item_id}.json": review_item_id for review_item_id in required_adjudications
    }

    unexpected_adjudication_files = tuple(
        path for path in adjudication_files if path.name not in required_adjudication_names
    )

    adjudications_by_name = {path.name: path for path in adjudication_files}

    valid_adjudication_count = 0
    invalid_adjudication_record_count = 0

    for (
        review_item_id,
        reviews,
    ) in required_adjudications.items():
        file_name = f"{review_item_id}.json"

        path = adjudications_by_name.get(file_name)

        if path is None:
            continue

        primary_review, secondary_review = reviews

        try:
            _load_adjudication_for_pair(
                path,
                primary_review,
                secondary_review,
                rubric,
            )
        except ReviewBridgeError:
            invalid_adjudication_record_count += 1
            continue

        valid_adjudication_count += 1

    currently_required_adjudication_count = len(required_adjudications)

    missing_required_adjudication_count = (
        currently_required_adjudication_count - valid_adjudication_count
    )

    missing_primary_review_count = 162 - valid_primary_review_count

    missing_secondary_review_count = 41 - valid_secondary_review_count

    review_complete = (
        valid_primary_review_count == 162
        and valid_secondary_review_count == 41
        and len(unexpected_review_files) == 0
        and invalid_review_record_count == 0
        and reviewer_independence_violation_count == 0
    )

    adjudication_complete = (
        review_complete
        and adjudication_requirement_fully_determined
        and missing_required_adjudication_count == 0
        and len(unexpected_adjudication_files) == 0
        and invalid_adjudication_record_count == 0
    )

    overall_complete = adjudication_complete

    status: Literal[
        "INCOMPLETE",
        "COMPLETE",
    ] = "COMPLETE" if overall_complete else "INCOMPLETE"

    next_gate: Literal[
        "COMPLETE_FINAL_342_HUMAN_REVIEW_V1",
        "MATERIALIZE_FINAL_342_MEASURED_QUALITY_INPUTS_V1",
    ] = (
        "MATERIALIZE_FINAL_342_MEASURED_QUALITY_INPUTS_V1"
        if overall_complete
        else "COMPLETE_FINAL_342_HUMAN_REVIEW_V1"
    )

    return ReviewCompletionAccountability(
        status=status,
        valid_primary_review_count=valid_primary_review_count,
        missing_primary_review_count=missing_primary_review_count,
        valid_secondary_review_count=valid_secondary_review_count,
        missing_secondary_review_count=missing_secondary_review_count,
        review_file_count=len(review_files),
        unexpected_review_file_count=len(unexpected_review_files),
        invalid_review_record_count=invalid_review_record_count,
        complete_secondary_pair_count=complete_secondary_pair_count,
        pending_secondary_pair_count=pending_secondary_pair_count,
        reviewer_independence_violation_count=(reviewer_independence_violation_count),
        detected_material_disagreement_count=(currently_required_adjudication_count),
        currently_required_adjudication_count=(currently_required_adjudication_count),
        adjudication_requirement_fully_determined=(adjudication_requirement_fully_determined),
        adjudication_file_count=len(adjudication_files),
        valid_adjudication_count=valid_adjudication_count,
        missing_required_adjudication_count=(missing_required_adjudication_count),
        unexpected_adjudication_file_count=len(unexpected_adjudication_files),
        invalid_adjudication_record_count=(invalid_adjudication_record_count),
        unresolved_material_disagreement_count=(missing_required_adjudication_count),
        review_complete=review_complete,
        adjudication_complete=adjudication_complete,
        overall_review_evidence_complete=overall_complete,
        next_gate=next_gate,
    )


def review_accountability(
    repo_root: Path,
    *,
    result_root: Path | None = None,
    protected_root: Path | None = None,
    custody_receipt_path: Path | None = None,
) -> ReviewCompletionAccountability:
    root = repo_root.resolve()

    selected_protected_root = (
        protected_root if protected_root is not None else root / PROTECTED_REVIEW_ROOT
    )

    selected_result_root = result_root if result_root is not None else root / REVIEW_RESULT_ROOT

    validate_inputs(
        root,
        protected_root=selected_protected_root,
        custody_receipt_path=custody_receipt_path,
    )

    (
        _export,
        _schedule,
        rubric,
        assignments,
    ) = _load_review_inputs(
        root,
        selected_protected_root,
    )

    return build_review_accountability(
        assignments,
        rubric,
        selected_result_root,
    )


def validate_review_completion(
    repo_root: Path,
) -> ReviewCompletionAccountability:
    result = review_accountability(repo_root)

    if not result.overall_review_evidence_complete:
        raise ReviewBridgeError(
            "FINAL_342_REVIEW_BRIDGE_COMPLETION_INCOMPLETE",
            "Final-342 human-review evidence is not complete",
        )

    return result


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "validate-inputs",
            "submit-review",
            "submit-adjudication",
            "review-status",
            "validate-completion",
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--submission-file",
        type=Path,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        if args.command == "validate-inputs":
            result: FrozenModel = validate_inputs(args.repo_root)
        elif args.command == "submit-review":
            if args.submission_file is None:
                raise ReviewBridgeError(
                    "FINAL_342_REVIEW_BRIDGE_SUBMISSION_FILE_REQUIRED",
                    "submit-review requires --submission-file",
                )

            result = submit_review(
                args.repo_root,
                args.submission_file,
            )
        elif args.command == "submit-adjudication":
            if args.submission_file is None:
                raise ReviewBridgeError(
                    "FINAL_342_REVIEW_BRIDGE_ADJUDICATION_FILE_REQUIRED",
                    "submit-adjudication requires --submission-file",
                )

            result = submit_adjudication(
                args.repo_root,
                args.submission_file,
            )
        elif args.command == "review-status":
            result = review_accountability(args.repo_root)
        elif args.command == "validate-completion":
            result = validate_review_completion(args.repo_root)
        else:
            raise ReviewBridgeError(
                "FINAL_342_REVIEW_BRIDGE_COMMAND_INVALID",
                "unsupported measured-review bridge command",
            )

    except (
        ReviewBridgeError,
        ValidationError,
        OSError,
    ) as error:
        if isinstance(error, ReviewBridgeError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, ValidationError):
            code = "FINAL_342_REVIEW_BRIDGE_TYPED_VALIDATION_FAILED"
            message = "measured-review bridge typed validation failed"
        else:
            code = "FINAL_342_REVIEW_BRIDGE_IO_FAILED"
            message = "measured-review bridge local I/O failed"

        print(
            json.dumps(
                {
                    "error_code": code,
                    "safe_message": message,
                },
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
