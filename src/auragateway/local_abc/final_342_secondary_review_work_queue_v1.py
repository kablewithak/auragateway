"""Local blinded secondary human-review work queue for Final-342 measured evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as bridge,
)
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)

QUEUE_ROOT = Path(".local/auragateway/final-342-secondary-review-work-queue-v1")


class SecondaryWorkQueueError(RuntimeError):
    """Fail-closed secondary human-review work-queue error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class CriterionDraft(FrozenModel):
    criterion: RubricCriterion
    score: int | None = Field(
        default=None,
        ge=1,
        le=4,
    )
    evidence_note: str | None = Field(
        default=None,
        min_length=1,
        max_length=4000,
    )


class ReviewSubmissionTemplate(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    reviewer_key: str | None = None
    criterion_scores: tuple[CriterionDraft, ...] = Field(
        min_length=7,
        max_length=7,
    )
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    rationale: str | None = None


class SecondaryWorkItem(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    work_item_id: Literal["auragateway-final-342-secondary-review-work-item-v1"] = (
        "auragateway-final-342-secondary-review-work-item-v1"
    )
    role: Literal["secondary"] = "secondary"
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    reviewer_payload: review_successor.ReviewerPayload
    rubric: BlindedQualityRubric


class QueueStatus(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal[
        "SECONDARY_REVIEW_PENDING",
        "SECONDARY_REVIEW_COMPLETE",
    ]

    valid_primary_review_count: int = Field(ge=0, le=162)
    missing_primary_review_count: int = Field(ge=0, le=162)
    valid_secondary_review_count: int = Field(ge=0, le=41)
    missing_secondary_review_count: int = Field(ge=0, le=41)

    next_secondary_assignment_id: str | None = Field(
        default=None,
        pattern=r"^review-[0-9a-f]{24}$",
    )

    raw_protected_content_logged: Literal[False] = False
    primary_review_content_exposed: Literal[False] = False
    human_review_result_created: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    new_execution_authorized: Literal[False] = False


class MaterializationReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal[
        "SECONDARY_WORK_ITEM_READY",
        "SECONDARY_REVIEW_COMPLETE",
    ]

    assignment_id: str | None = Field(
        default=None,
        pattern=r"^review-[0-9a-f]{24}$",
    )
    work_item_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    work_item_path: str | None = None
    submission_path: str | None = None
    work_item_created: bool
    submission_template_created: bool

    raw_protected_content_logged: Literal[False] = False
    primary_review_content_exposed: Literal[False] = False
    human_review_result_created: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    new_execution_authorized: Literal[False] = False

    next_gate: Literal[
        "COMPLETE_CURRENT_SECONDARY_HUMAN_REVIEW",
        "EVALUATE_FINAL_342_MATERIAL_DISAGREEMENTS_V1",
    ]


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_FILE_MISSING",
            f"required queue input is missing or unsafe: {path.as_posix()}",
        )

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_JSON_INVALID",
            f"queue input JSON is invalid: {path.as_posix()}",
        ) from error

    if not isinstance(value, dict):
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_JSON_SHAPE_INVALID",
            f"queue input must be a JSON object: {path.as_posix()}",
        )

    return value


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_PATH_UNSAFE",
                "queue output path is not a regular file",
            )

        if path.read_bytes() != payload:
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_APPEND_ONLY_CONFLICT",
                "existing immutable queue work item differs from expected bytes",
            )

        return False

    temporary = path.with_name(f".{path.name}.tmp")

    if temporary.exists():
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_TEMP_RESIDUE",
            "queue temporary file already exists",
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


def _validate_existing_submission_identity(
    path: Path,
    *,
    assignment_id: str,
) -> None:
    payload = _read_json_object(path)
    observed = payload.get("assignment_id")

    if observed != assignment_id:
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_SUBMISSION_IDENTITY_MISMATCH",
            "existing secondary submission draft belongs to a different assignment",
        )


def _write_submission_template_if_absent(
    path: Path,
    payload: bytes,
    *,
    assignment_id: str,
) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_SUBMISSION_PATH_UNSAFE",
                "submission draft path is not a regular file",
            )

        _validate_existing_submission_identity(
            path,
            assignment_id=assignment_id,
        )
        return False

    temporary = path.with_name(f".{path.name}.tmp")

    if temporary.exists():
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_TEMP_RESIDUE",
            "submission draft temporary file already exists",
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


def _load_queue_inputs(
    root: Path,
) -> tuple[
    review_successor.ProtectedExport,
    review_successor.ProtectedSchedule,
    BlindedQualityRubric,
    tuple[bridge.ExpectedReviewAssignment, ...],
]:
    bridge.validate_inputs(root)

    protected_root = root / bridge.PROTECTED_REVIEW_ROOT

    export = review_successor.ProtectedExport.model_validate(
        _read_json_object(protected_root / review_successor.PROTECTED_EXPORT_PATH.name)
    )

    schedule = review_successor.ProtectedSchedule.model_validate(
        _read_json_object(protected_root / review_successor.PROTECTED_SCHEDULE_PATH.name)
    )

    rubric = BlindedQualityRubric.model_validate(_read_json_object(root / bridge.RUBRIC_PATH))

    assignments = bridge.project_expected_assignments(export, schedule)

    return export, schedule, rubric, assignments


def _review_result_path(root: Path, assignment_id: str) -> Path:
    return root / bridge.REVIEW_RESULT_ROOT / "reviews" / f"{assignment_id}.json"


def _primary_assignment_for_item(
    assignments: tuple[bridge.ExpectedReviewAssignment, ...],
    review_item_id: str,
) -> bridge.ExpectedReviewAssignment:
    candidates = tuple(
        item
        for item in assignments
        if item.review_item_id == review_item_id and item.role == "primary"
    )

    if len(candidates) != 1:
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_PRIMARY_IDENTITY_INVALID",
            "scheduled secondary review item does not map to exactly one primary assignment",
        )

    return candidates[0]


def select_next_secondary(
    *,
    root: Path,
    export: review_successor.ProtectedExport,
    schedule: review_successor.ProtectedSchedule,
    assignments: tuple[bridge.ExpectedReviewAssignment, ...],
) -> (
    tuple[
        bridge.ExpectedReviewAssignment,
        review_successor.ReviewerPayload,
    ]
    | None
):
    assignment_by_id = {item.assignment_id: item for item in assignments}
    payload_by_id = {item.assignment_id: item for item in export.assignments}

    if len(payload_by_id) != len(export.assignments):
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_EXPORT_DUPLICATE",
            "reviewer export contains duplicate assignment IDs",
        )

    for entry in schedule.entries:
        assignment = assignment_by_id.get(entry.secondary_assignment_id)

        if assignment is None:
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_ASSIGNMENT_UNKNOWN",
                "frozen secondary schedule contains an unknown assignment",
            )

        if assignment.role != "secondary":
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_ROLE_INVALID",
                "frozen secondary schedule resolved to a non-secondary assignment",
            )

        if assignment.review_item_id != entry.review_item_id:
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_REVIEW_ITEM_MISMATCH",
                "secondary schedule review-item identity drifted",
            )

        primary = _primary_assignment_for_item(
            assignments,
            assignment.review_item_id,
        )

        primary_result = _review_result_path(root, primary.assignment_id)

        if not primary_result.is_file() or primary_result.is_symlink():
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_PRIMARY_REQUIRED",
                "secondary review requires the corresponding persisted primary review",
            )

        secondary_result = _review_result_path(root, assignment.assignment_id)

        if secondary_result.exists():
            if secondary_result.is_symlink() or not secondary_result.is_file():
                raise SecondaryWorkQueueError(
                    "FINAL_342_SECONDARY_REVIEW_QUEUE_RESULT_PATH_UNSAFE",
                    "secondary review result path is not a regular file",
                )
            continue

        payload = payload_by_id.get(assignment.assignment_id)

        if payload is None:
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_PAYLOAD_MISSING",
                "secondary assignment is missing from the protected reviewer export",
            )

        if payload.review_item_id != assignment.review_item_id:
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_PAYLOAD_REVIEW_ITEM_MISMATCH",
                "secondary reviewer payload review-item identity drifted",
            )

        if payload.episode_id != assignment.episode_id:
            raise SecondaryWorkQueueError(
                "FINAL_342_SECONDARY_REVIEW_QUEUE_PAYLOAD_EPISODE_MISMATCH",
                "secondary reviewer payload episode identity drifted",
            )

        return assignment, payload

    return None


def _submission_template(assignment_id: str) -> ReviewSubmissionTemplate:
    return ReviewSubmissionTemplate(
        assignment_id=assignment_id,
        criterion_scores=tuple(
            CriterionDraft(criterion=criterion) for criterion in RubricCriterion
        ),
    )


def materialize_secondary_work_item(
    *,
    root: Path,
    queue_root: Path,
    assignment: bridge.ExpectedReviewAssignment,
    payload: review_successor.ReviewerPayload,
    rubric: BlindedQualityRubric,
) -> MaterializationReceipt:
    if assignment.role != "secondary":
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_SECONDARY_ROLE_REQUIRED",
            "secondary work-item materialization requires a secondary assignment",
        )

    if payload.assignment_id != assignment.assignment_id:
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_PAYLOAD_ASSIGNMENT_MISMATCH",
            "secondary reviewer payload assignment identity drifted",
        )

    if payload.review_item_id != assignment.review_item_id:
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_PAYLOAD_REVIEW_ITEM_MISMATCH",
            "secondary reviewer payload review-item identity drifted",
        )

    if payload.episode_id != assignment.episode_id:
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_PAYLOAD_EPISODE_MISMATCH",
            "secondary reviewer payload episode identity drifted",
        )

    work_item = SecondaryWorkItem(
        assignment_id=assignment.assignment_id,
        review_item_id=assignment.review_item_id,
        episode_id=assignment.episode_id,
        reviewer_payload=payload,
        rubric=rubric,
    )

    review_successor.assert_reviewer_safe(work_item.model_dump(mode="python"))

    package_root = queue_root / assignment.assignment_id
    work_item_path = package_root / "work_item.json"
    submission_path = package_root / "submission.json"

    work_item_bytes = _canonical_json_bytes(work_item.model_dump(mode="json"))

    work_item_created = _write_once(
        work_item_path,
        work_item_bytes,
    )

    template = _submission_template(assignment.assignment_id)
    template_bytes = _canonical_json_bytes(template.model_dump(mode="json"))

    submission_created = _write_submission_template_if_absent(
        submission_path,
        template_bytes,
        assignment_id=assignment.assignment_id,
    )

    return MaterializationReceipt(
        status="SECONDARY_WORK_ITEM_READY",
        assignment_id=assignment.assignment_id,
        work_item_sha256=_sha256_bytes(work_item_bytes),
        work_item_path=work_item_path.relative_to(root).as_posix(),
        submission_path=submission_path.relative_to(root).as_posix(),
        work_item_created=work_item_created,
        submission_template_created=submission_created,
        next_gate="COMPLETE_CURRENT_SECONDARY_HUMAN_REVIEW",
    )


def _require_primary_phase_complete(
    accountability: bridge.ReviewCompletionAccountability,
) -> None:
    if (
        accountability.valid_primary_review_count != 162
        or accountability.missing_primary_review_count != 0
    ):
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_PRIMARY_PHASE_INCOMPLETE",
            "secondary review cannot begin until all 162 primary reviews are valid",
        )


def _require_accountability_safe(
    accountability: bridge.ReviewCompletionAccountability,
) -> None:
    if (
        accountability.unexpected_review_file_count != 0
        or accountability.invalid_review_record_count != 0
        or accountability.unexpected_adjudication_file_count != 0
        or accountability.invalid_adjudication_record_count != 0
        or accountability.reviewer_independence_violation_count != 0
    ):
        raise SecondaryWorkQueueError(
            "FINAL_342_SECONDARY_REVIEW_QUEUE_ACCOUNTABILITY_INVALID",
            "review accountability contains invalid or unexpected evidence",
        )


def queue_status(repo_root: Path) -> QueueStatus:
    root = repo_root.resolve()
    accountability = bridge.review_accountability(root)

    _require_accountability_safe(accountability)
    _require_primary_phase_complete(accountability)

    export, schedule, _rubric, assignments = _load_queue_inputs(root)

    next_secondary = select_next_secondary(
        root=root,
        export=export,
        schedule=schedule,
        assignments=assignments,
    )

    if next_secondary is None:
        return QueueStatus(
            status="SECONDARY_REVIEW_COMPLETE",
            valid_primary_review_count=accountability.valid_primary_review_count,
            missing_primary_review_count=accountability.missing_primary_review_count,
            valid_secondary_review_count=accountability.valid_secondary_review_count,
            missing_secondary_review_count=accountability.missing_secondary_review_count,
        )

    assignment, _payload = next_secondary

    return QueueStatus(
        status="SECONDARY_REVIEW_PENDING",
        valid_primary_review_count=accountability.valid_primary_review_count,
        missing_primary_review_count=accountability.missing_primary_review_count,
        valid_secondary_review_count=accountability.valid_secondary_review_count,
        missing_secondary_review_count=accountability.missing_secondary_review_count,
        next_secondary_assignment_id=assignment.assignment_id,
    )


def materialize_next_secondary(repo_root: Path) -> MaterializationReceipt:
    root = repo_root.resolve()
    accountability = bridge.review_accountability(root)

    _require_accountability_safe(accountability)
    _require_primary_phase_complete(accountability)

    export, schedule, rubric, assignments = _load_queue_inputs(root)

    selected = select_next_secondary(
        root=root,
        export=export,
        schedule=schedule,
        assignments=assignments,
    )

    if selected is None:
        return MaterializationReceipt(
            status="SECONDARY_REVIEW_COMPLETE",
            work_item_created=False,
            submission_template_created=False,
            next_gate="EVALUATE_FINAL_342_MATERIAL_DISAGREEMENTS_V1",
        )

    assignment, payload = selected

    return materialize_secondary_work_item(
        root=root,
        queue_root=root / QUEUE_ROOT,
        assignment=assignment,
        payload=payload,
        rubric=rubric,
    )


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "status",
            "materialize-next-secondary",
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        result: FrozenModel

        if args.command == "status":
            result = queue_status(args.repo_root)
        else:
            result = materialize_next_secondary(args.repo_root)

    except (
        SecondaryWorkQueueError,
        ValidationError,
        OSError,
    ) as error:
        if isinstance(error, SecondaryWorkQueueError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, ValidationError):
            code = "FINAL_342_SECONDARY_REVIEW_QUEUE_TYPED_VALIDATION_FAILED"
            message = "secondary human-review work queue typed validation failed"
        else:
            code = "FINAL_342_SECONDARY_REVIEW_QUEUE_IO_ERROR"
            message = "secondary human-review work queue I/O failed"

        print(
            json.dumps(
                {
                    "error_code": code,
                    "safe_message": message,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            result.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
