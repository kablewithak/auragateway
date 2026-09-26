"""Blinded completion queue for the J7L audited/adjudicated development successor.

The queue extends the already-frozen 28-case human audit to all 48 frozen J7L
development cases. It never reads model-reference judgments while human scoring
is in progress. The failed V3 audit remains immutable and terminal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import NamedTuple, Never

from pydantic import BaseModel, ValidationError

from auragateway.contracts.blinded_quality import RubricCriterion
from auragateway.contracts.j7l_audited_adjudicated_development_reference_v1 import (
    EXPECTED_CASE_COUNT,
    EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256,
    EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256,
    EXPECTED_FAILED_V3_MATERIAL_DISAGREEMENT_COUNT,
    EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT,
    EXPECTED_REMAINING_HUMAN_ASSESSMENT_COUNT,
    CriterionDraft,
    J7LAuditedAdjudicatedDevelopmentReferencePolicyV1,
    J7LSuccessorHumanAssessmentV1,
    J7LSuccessorHumanWorkItemV1,
    J7LSuccessorPreflightReceiptV1,
    J7LSuccessorPrepareReceiptV1,
    J7LSuccessorQueueStatusV1,
    J7LSuccessorSubmissionReceiptV1,
    J7LSuccessorSubmissionTemplateV1,
    J7LSuccessorSubmissionV1,
    derived_verdict,
)
from auragateway.local_abc import j7l_reference_human_audit_comparison_v1 as predecessor
from auragateway.local_abc import j7l_reference_human_audit_queue_v1 as audit_queue
from auragateway.local_abc import quality_development_case_freeze_v1 as case_freeze

QUEUE_ROOT = Path(".local/auragateway/j7l-audited-adjudicated-development-reference-v1")
WORK_ROOT = QUEUE_ROOT / "work-items"
SUBMISSION_ROOT = QUEUE_ROOT / "submissions"
ASSESSMENT_ROOT = QUEUE_ROOT / "assessments"

POLICY = J7LAuditedAdjudicatedDevelopmentReferencePolicyV1()


class SuccessorQueueError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SuccessorQueueError("J7L_SUCCESSOR_ARGUMENT_ERROR", message)


class _Context(NamedTuple):
    schedule: case_freeze.J7LReviewScheduleV1
    primary_export: case_freeze.J7LReviewerExportV1
    preserved_case_ids: tuple[str, ...]
    remaining_case_ids: tuple[str, ...]


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_FILE_MISSING",
            f"required successor input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_JSON_INVALID",
            f"successor input is not valid UTF-8 JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_JSON_SHAPE_INVALID",
            f"successor input root must be an object: {path.as_posix()}",
        )
    return value


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise SuccessorQueueError(
                "J7L_SUCCESSOR_OUTPUT_PATH_UNSAFE",
                "successor output path is unsafe",
            )
        if path.read_bytes() != payload:
            raise SuccessorQueueError(
                "J7L_SUCCESSOR_APPEND_ONLY_CONFLICT",
                "existing successor output differs from expected bytes",
            )
        return False
    with path.open("xb") as handle:
        handle.write(payload)
    return True


def _write_template_if_absent(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise SuccessorQueueError(
                "J7L_SUCCESSOR_SUBMISSION_PATH_UNSAFE",
                "successor submission path is unsafe",
            )
        return False
    with path.open("xb") as handle:
        handle.write(payload)
    return True


def _remaining_case_ids(
    all_case_ids: tuple[str, ...],
    preserved_case_ids: tuple[str, ...],
) -> tuple[str, ...]:
    if len(all_case_ids) != EXPECTED_CASE_COUNT or len(set(all_case_ids)) != EXPECTED_CASE_COUNT:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_CASE_INVENTORY_INVALID",
            "successor subject must contain exactly 48 unique frozen case IDs",
        )
    if (
        len(preserved_case_ids) != EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
        or len(set(preserved_case_ids)) != EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
    ):
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_PRESERVED_HUMAN_INVENTORY_INVALID",
            "predecessor human freeze must contain exactly 28 unique cases",
        )
    unknown = sorted(set(preserved_case_ids) - set(all_case_ids))
    if unknown:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_PRESERVED_CASE_ID_DRIFT",
            "predecessor human freeze contains cases outside the frozen 48-case subject",
        )
    remaining = tuple(case_id for case_id in all_case_ids if case_id not in set(preserved_case_ids))
    if len(remaining) != EXPECTED_REMAINING_HUMAN_ASSESSMENT_COUNT:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_REMAINING_HUMAN_COUNT_INVALID",
            "successor must require exactly 20 additional blinded human assessments",
        )
    return remaining


def _load_context(root: Path) -> _Context:
    audit_queue.validate_inputs(root)

    audit_result_path = root / predecessor.AUDIT_RESULT_PATH
    if _sha256_file(audit_result_path) != EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_FAILED_AUDIT_IDENTITY_DRIFT",
            "failed V3 audit-result identity drifted",
        )
    try:
        audit_result = predecessor.ReferenceAuditResult.model_validate(
            _read_json(audit_result_path)
        )
    except ValidationError as error:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_FAILED_AUDIT_INVALID",
            "failed V3 audit result failed typed validation",
        ) from error

    if (
        audit_result.status != "J7L_REFERENCE_HUMAN_AUDIT_FAIL"
        or audit_result.material_disagreement_count
        != EXPECTED_FAILED_V3_MATERIAL_DISAGREEMENT_COUNT
        or audit_result.reference_set_valid_for_advancement
        or audit_result.coverage_evaluated
        or audit_result.jev_requests_performed != 0
        or audit_result.next_gate != "STOP_REFERENCE_QUALITY_FAILURE"
    ):
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_FAILED_AUDIT_DISPOSITION_DRIFT",
            "V3 predecessor is not the exact terminal failed reference-quality lineage",
        )

    try:
        freeze, freeze_sha256 = predecessor._load_and_validate_freeze(root)
    except predecessor.ReferenceAuditComparisonError as error:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_HUMAN_FREEZE_INVALID",
            "predecessor human freeze no longer validates against its 28 assessments",
        ) from error
    if freeze_sha256 != EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_HUMAN_FREEZE_IDENTITY_DRIFT",
            "failed V3 human-freeze identity drifted",
        )

    schedule_path = root / audit_queue.REVIEW_SCHEDULE_PATH
    primary_path = root / audit_queue.PRIMARY_EXPORT_PATH
    if _sha256_file(schedule_path) != audit_queue.EXPECTED_REVIEW_SCHEDULE_SHA256:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_REVIEW_SCHEDULE_DRIFT",
            "frozen 48-case human-review schedule drifted",
        )
    if _sha256_file(primary_path) != audit_queue.EXPECTED_PRIMARY_EXPORT_SHA256:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_PRIMARY_EXPORT_DRIFT",
            "frozen primary reviewer export drifted",
        )

    try:
        schedule = case_freeze.J7LReviewScheduleV1.model_validate(_read_json(schedule_path))
        primary = case_freeze.J7LReviewerExportV1.model_validate(_read_json(primary_path))
    except ValidationError as error:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_REVIEW_INPUT_INVALID",
            "successor reviewer-safe input failed typed validation",
        ) from error

    if primary.review_stream != "primary" or primary.item_count != EXPECTED_CASE_COUNT:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_PRIMARY_EXPORT_SHAPE_DRIFT",
            "successor requires the exact 48-case primary reviewer export",
        )

    all_case_ids = tuple(entry.case_id for entry in schedule.entries)
    preserved_case_ids = tuple(item.case_id for item in freeze.assessments)
    remaining = _remaining_case_ids(all_case_ids, preserved_case_ids)

    return _Context(
        schedule=schedule,
        primary_export=primary,
        preserved_case_ids=preserved_case_ids,
        remaining_case_ids=remaining,
    )


def _work_item(context: _Context, case_id: str, queue_index: int) -> J7LSuccessorHumanWorkItemV1:
    entry = next(
        (candidate for candidate in context.schedule.entries if candidate.case_id == case_id),
        None,
    )
    if entry is None:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_SCHEDULE_CASE_MISSING",
            f"{case_id} is missing from the frozen review schedule",
        )
    item = next(
        (
            candidate
            for candidate in context.primary_export.items
            if candidate.assignment_id == entry.primary_assignment_id
        ),
        None,
    )
    if item is None:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_PRIMARY_ITEM_MISSING",
            f"{case_id} primary reviewer item is missing",
        )
    if item.review_item_id != entry.review_item_id:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_REVIEW_ITEM_DRIFT",
            f"{case_id} review-item identity drifted",
        )
    if item.reviewer_safe_state_sha256 != entry.reviewer_safe_state_sha256:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_SAFE_STATE_DRIFT",
            f"{case_id} reviewer-safe state identity drifted",
        )
    case_freeze.assert_reviewer_export_safe(item.model_dump(mode="json"))

    return J7LSuccessorHumanWorkItemV1(
        case_id=case_id,
        queue_index=queue_index,
        source_assignment_id=entry.primary_assignment_id,
        review_item_id=item.review_item_id,
        reviewer_safe_state_sha256=item.reviewer_safe_state_sha256,
        reviewer_safe_state=item.reviewer_safe_state,
        semantic_projection=context.primary_export.semantic_projection,
        reviewer_instruction=context.primary_export.reviewer_instruction,
        assessment_actor_id_sha256=audit_queue.OPERATOR_SHA256,
    )


def validate_inputs(repo_root: Path) -> J7LSuccessorPreflightReceiptV1:
    root = repo_root.resolve()
    context = _load_context(root)
    for index, case_id in enumerate(context.remaining_case_ids):
        _work_item(context, case_id, index)
    return J7LSuccessorPreflightReceiptV1()


def prepare(repo_root: Path) -> J7LSuccessorPrepareReceiptV1:
    root = repo_root.resolve()
    context = _load_context(root)
    created_work_items = 0
    created_templates = 0

    for index, case_id in enumerate(context.remaining_case_ids):
        work = _work_item(context, case_id, index)
        work_bytes = _canonical_bytes(work.model_dump(mode="json"))
        created_work_items += int(_write_once(root / WORK_ROOT / f"{case_id}.json", work_bytes))

        template = J7LSuccessorSubmissionTemplateV1(
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

    return J7LSuccessorPrepareReceiptV1(
        created_work_item_count=created_work_items,
        created_submission_template_count=created_templates,
        work_item_root=WORK_ROOT.as_posix(),
        submission_root=SUBMISSION_ROOT.as_posix(),
    )


def status(repo_root: Path) -> J7LSuccessorQueueStatusV1:
    root = repo_root.resolve()
    context = _load_context(root)
    remaining_set = set(context.remaining_case_ids)

    if (root / ASSESSMENT_ROOT).exists():
        observed_ids = tuple(
            sorted(path.stem for path in (root / ASSESSMENT_ROOT).glob("j7l-dev-*.json"))
        )
        unexpected = tuple(case_id for case_id in observed_ids if case_id not in remaining_set)
        if unexpected:
            raise SuccessorQueueError(
                "J7L_SUCCESSOR_UNAUTHORIZED_ASSESSMENT_PRESENT",
                (
                    "successor assessment root contains a case outside "
                    "the authorized 20-case remainder"
                ),
            )

    completed: list[str] = []
    for case_id in context.remaining_case_ids:
        path = root / ASSESSMENT_ROOT / f"{case_id}.json"
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file():
            raise SuccessorQueueError(
                "J7L_SUCCESSOR_ASSESSMENT_PATH_UNSAFE",
                f"{case_id} successor assessment path is unsafe",
            )
        try:
            assessment = J7LSuccessorHumanAssessmentV1.model_validate(_read_json(path))
        except ValidationError as error:
            raise SuccessorQueueError(
                "J7L_SUCCESSOR_ASSESSMENT_INVALID",
                f"{case_id} successor assessment failed typed validation",
            ) from error
        if assessment.case_id != case_id:
            raise SuccessorQueueError(
                "J7L_SUCCESSOR_ASSESSMENT_CASE_DRIFT",
                f"{case_id} successor assessment identity drifted",
            )
        if assessment.assessment_actor_id_sha256 != audit_queue.OPERATOR_SHA256:
            raise SuccessorQueueError(
                "J7L_SUCCESSOR_ASSESSMENT_ACTOR_DRIFT",
                f"{case_id} successor assessment actor drifted",
            )
        completed.append(case_id)

    pending = tuple(
        case_id for case_id in context.remaining_case_ids if case_id not in set(completed)
    )
    next_case_id = pending[0] if pending else None

    return J7LSuccessorQueueStatusV1(
        status=(
            "SUCCESSOR_HUMAN_REVIEW_COMPLETE" if not pending else "SUCCESSOR_HUMAN_REVIEW_PENDING"
        ),
        successor_completed_assessment_count=len(completed),
        total_completed_human_assessment_count=(
            EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT + len(completed)
        ),
        pending_successor_assessment_count=len(pending),
        next_case_id=next_case_id,
        next_work_item_path=(
            (WORK_ROOT / f"{next_case_id}.json").as_posix() if next_case_id is not None else None
        ),
        next_submission_path=(
            (SUBMISSION_ROOT / f"{next_case_id}.json").as_posix()
            if next_case_id is not None
            else None
        ),
    )


def submit(repo_root: Path, submission_file: Path) -> J7LSuccessorSubmissionReceiptV1:
    root = repo_root.resolve()
    context = _load_context(root)

    selected = submission_file if submission_file.is_absolute() else root / submission_file
    if not selected.is_file() or selected.is_symlink():
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_SUBMISSION_MISSING",
            "successor human-review submission file is missing or unsafe",
        )
    try:
        selected.resolve().relative_to((root / ".local").resolve())
    except ValueError as error:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_SUBMISSION_OUTSIDE_LOCAL",
            "successor human-review submission must remain under repository .local",
        ) from error

    try:
        submission = J7LSuccessorSubmissionV1.model_validate(_read_json(selected))
    except ValidationError as error:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_SUBMISSION_INVALID",
            "successor human-review submission failed typed validation",
        ) from error

    if submission.case_id in set(context.preserved_case_ids):
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_PRESERVED_CASE_RESCORING_FORBIDDEN",
            "the frozen 28 predecessor human assessments may not be rescored",
        )
    if submission.case_id not in set(context.remaining_case_ids):
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_CASE_NOT_AUTHORIZED",
            "submission case is outside the authorized 20-case successor remainder",
        )

    queue_index = context.remaining_case_ids.index(submission.case_id)
    expected_work = _work_item(context, submission.case_id, queue_index)
    expected_work_bytes = _canonical_bytes(expected_work.model_dump(mode="json"))
    work_path = root / WORK_ROOT / f"{submission.case_id}.json"
    if not work_path.is_file() or work_path.is_symlink():
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_WORK_ITEM_MISSING",
            "submission requires its prepared blinded work item",
        )
    if work_path.read_bytes() != expected_work_bytes:
        raise SuccessorQueueError(
            "J7L_SUCCESSOR_WORK_ITEM_DRIFT",
            "prepared successor work item differs from frozen reviewer-safe input",
        )

    by_criterion = {item.criterion: item for item in submission.criterion_scores}
    scores = {criterion: by_criterion[criterion].score for criterion in RubricCriterion}
    assessment = J7LSuccessorHumanAssessmentV1(
        case_id=submission.case_id,
        assessment_actor_id_sha256=audit_queue.OPERATOR_SHA256,
        work_item_sha256=hashlib.sha256(expected_work_bytes).hexdigest(),
        reviewer_safe_state_sha256=expected_work.reviewer_safe_state_sha256,
        criterion_scores=scores,
        failure_labels=submission.failure_labels,
        evidence_references=submission.evidence_references,
        rationale=submission.rationale,
        verdict=derived_verdict(scores, submission.failure_labels),
    )
    assessment_bytes = _canonical_bytes(assessment.model_dump(mode="json"))
    created = _write_once(
        root / ASSESSMENT_ROOT / f"{submission.case_id}.json",
        assessment_bytes,
    )

    queue = status(root)
    return J7LSuccessorSubmissionReceiptV1(
        case_id=submission.case_id,
        assessment_sha256=hashlib.sha256(assessment_bytes).hexdigest(),
        created=created,
        total_completed_human_assessment_count=queue.total_completed_human_assessment_count,
        pending_successor_assessment_count=queue.pending_successor_assessment_count,
        next_case_id=queue.next_case_id,
    )


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
    result: BaseModel
    try:
        if args.command == "validate-inputs":
            result = validate_inputs(args.repo_root)
        elif args.command == "prepare":
            result = prepare(args.repo_root)
        elif args.command == "status":
            result = status(args.repo_root)
        else:
            if args.submission_file is None:
                raise SuccessorQueueError(
                    "J7L_SUCCESSOR_SUBMISSION_REQUIRED",
                    "submit requires --submission-file",
                )
            result = submit(args.repo_root, args.submission_file)
    except (
        SuccessorQueueError,
        predecessor.ReferenceAuditComparisonError,
        audit_queue.HumanAuditQueueError,
        case_freeze.J7LCaseFreezeError,
        ValidationError,
        OSError,
    ) as error:
        if isinstance(error, SuccessorQueueError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, predecessor.ReferenceAuditComparisonError):
            code = "J7L_SUCCESSOR_PREDECESSOR_AUDIT_INVALID"
            message = "failed V3 predecessor audit evidence is invalid"
        elif isinstance(error, audit_queue.HumanAuditQueueError):
            code = "J7L_SUCCESSOR_PREDECESSOR_HUMAN_INPUT_INVALID"
            message = "predecessor human-review input is invalid"
        elif isinstance(error, case_freeze.J7LCaseFreezeError):
            code = "J7L_SUCCESSOR_REVIEWER_SAFE_INPUT_INVALID"
            message = "frozen reviewer-safe input is invalid"
        elif isinstance(error, ValidationError):
            code = "J7L_SUCCESSOR_TYPED_VALIDATION_FAILED"
            message = "J7L successor typed validation failed"
        else:
            code = "J7L_SUCCESSOR_LOCAL_IO_FAILED"
            message = "J7L successor local I/O failed"

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

    print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
