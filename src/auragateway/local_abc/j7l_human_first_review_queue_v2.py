"""Sequential single-human review queue for J7L human-first development V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple, Never

from pydantic import BaseModel, ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.j7l_human_first_development_v2 import (
    J7LCaseSetFreezeReceiptV2,
    J7LHumanFirstDevelopmentCaseSetV2,
    J7LNoveltyPolicyV2,
    J7LReviewerExportV2,
    J7LReviewScheduleV2,
)
from auragateway.contracts.j7l_human_first_review_v2 import (
    EXPECTED_CASE_COUNT,
    EXPECTED_NOVELTY_THRESHOLD,
    AssessmentDigestV2,
    CriterionDraftV2,
    J7LHumanAssessmentV2,
    J7LHumanFirstReviewPolicyV2,
    J7LHumanReferenceCoverageReportV2,
    J7LHumanReferenceFreezeV2,
    J7LHumanReferencePublicReceiptV2,
    J7LHumanReviewerIdentityV2,
    J7LHumanReviewPreflightReceiptV2,
    J7LHumanReviewPrepareReceiptV2,
    J7LHumanReviewQueueStatusV2,
    J7LHumanReviewSubmissionReceiptV2,
    J7LHumanReviewSubmissionTemplateV2,
    J7LHumanReviewSubmissionV2,
    J7LHumanReviewWorkItemV2,
    derived_verdict,
)
from auragateway.contracts.quality_development_evaluation_v1 import J7LCaseFamily
from auragateway.local_abc import j7l_human_first_development_v2 as foundation

QUEUE_ROOT = Path(".local/auragateway/j7l-human-first-review-v2")
REVIEWER_IDENTITY_PATH = QUEUE_ROOT / "reviewer_identity.json"
WORK_ROOT = QUEUE_ROOT / "work-items"
SUBMISSION_ROOT = QUEUE_ROOT / "submissions"
ASSESSMENT_ROOT = QUEUE_ROOT / "assessments"
COVERAGE_REPORT_PATH = QUEUE_ROOT / "human_reference_coverage_report.json"
HUMAN_REFERENCE_FREEZE_PATH = QUEUE_ROOT / "human_reference_freeze.json"

PUBLIC_HUMAN_REFERENCE_RECEIPT_PATH = Path(
    "data/evals/quality/j7l-human-first-development-v2/human-reference-freeze-v1.json"
)

POLICY = J7LHumanFirstReviewPolicyV2()
_QUEUE_ORDER_SALT = "auragateway-j7l-v2-human-review-order-v1"


class HumanReviewQueueError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise HumanReviewQueueError("J7L_V2_REVIEW_ARGUMENT_ERROR", message)


class _Context(NamedTuple):
    freeze_receipt: J7LCaseSetFreezeReceiptV2
    schedule: J7LReviewScheduleV2
    export: J7LReviewerExportV2
    ordered_assignment_ids: tuple[str, ...]
    assignment_to_case_id: dict[str, str]


def _canonical_bytes(value: object) -> bytes:
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


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_FILE_MISSING",
            f"required human-review input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_JSON_INVALID",
            f"human-review input is not valid UTF-8 JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_JSON_SHAPE_INVALID",
            f"human-review input root must be an object: {path.as_posix()}",
        )
    return value


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise HumanReviewQueueError(
                "J7L_V2_REVIEW_OUTPUT_PATH_UNSAFE",
                "human-review output path is unsafe",
            )
        if path.read_bytes() != payload:
            raise HumanReviewQueueError(
                "J7L_V2_REVIEW_APPEND_ONLY_CONFLICT",
                "existing human-review output differs from expected bytes",
            )
        return False

    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_TEMP_RESIDUE",
            "human-review temporary output already exists",
        )
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return True


def _write_template_if_absent(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise HumanReviewQueueError(
                "J7L_V2_REVIEW_SUBMISSION_PATH_UNSAFE",
                "human-review submission template path is unsafe",
            )
        return False
    with path.open("xb") as handle:
        handle.write(payload)
    return True


def _verify_file_sha(path: Path, expected_sha256: str, error_code: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise HumanReviewQueueError(
            error_code,
            f"required protected artifact is missing or unsafe: {path.as_posix()}",
        )
    if _sha256_file(path) != expected_sha256:
        raise HumanReviewQueueError(
            error_code,
            f"protected artifact identity drifted: {path.as_posix()}",
        )


def _queue_order(assignment_ids: tuple[str, ...]) -> tuple[str, ...]:
    if len(assignment_ids) != EXPECTED_CASE_COUNT:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_ASSIGNMENT_COUNT_INVALID",
            "review queue requires exactly 48 assignment IDs",
        )
    if len(set(assignment_ids)) != EXPECTED_CASE_COUNT:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_ASSIGNMENT_DUPLICATE",
            "review queue assignment IDs must be unique",
        )

    def key(assignment_id: str) -> str:
        return _sha256_bytes(f"{_QUEUE_ORDER_SALT}|{assignment_id}".encode())

    return tuple(sorted(assignment_ids, key=key))


def _load_context(repo_root: Path) -> _Context:
    root = repo_root.resolve()
    freeze_path = root / foundation.PUBLIC_FREEZE_PATH

    try:
        freeze_receipt = J7LCaseSetFreezeReceiptV2.model_validate(_read_json(freeze_path))
    except ValidationError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_FOUNDATION_FREEZE_INVALID",
            "foundation case-freeze receipt failed typed validation",
        ) from error

    if (
        freeze_receipt.status != "J7L_V2_CASE_SET_FROZEN_FOR_HUMAN_REVIEW"
        or not freeze_receipt.authoring_coverage_valid
        or not freeze_receipt.novelty_valid
        or freeze_receipt.human_reference_frozen
        or freeze_receipt.model_reveal_performed
        or freeze_receipt.provider_requests_performed != 0
        or freeze_receipt.jev_requests_performed != 0
    ):
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_FOUNDATION_DISPOSITION_INVALID",
            "foundation case-freeze receipt is not at the clean pre-human boundary",
        )

    _verify_file_sha(
        root / foundation.AUTHORING_CASE_SET_PATH,
        freeze_receipt.authoring_case_set_sha256,
        "J7L_V2_REVIEW_AUTHORING_IDENTITY_DRIFT",
    )
    _verify_file_sha(
        root / foundation.HISTORICAL_SIMILARITY_PROFILE_PATH,
        freeze_receipt.historical_similarity_profile_sha256,
        "J7L_V2_REVIEW_SIMILARITY_PROFILE_IDENTITY_DRIFT",
    )

    novelty_path = root / foundation.NOVELTY_POLICY_PATH
    _verify_file_sha(
        novelty_path,
        freeze_receipt.novelty_policy_sha256,
        "J7L_V2_REVIEW_NOVELTY_POLICY_IDENTITY_DRIFT",
    )
    try:
        novelty = J7LNoveltyPolicyV2.model_validate(_read_json(novelty_path))
    except ValidationError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_NOVELTY_POLICY_INVALID",
            "frozen novelty policy failed typed validation",
        ) from error
    if novelty.maximum_pair_similarity_allowed != EXPECTED_NOVELTY_THRESHOLD:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_NOVELTY_THRESHOLD_DRIFT",
            "frozen novelty threshold is not exactly 0.80",
        )

    schedule_path = root / foundation.REVIEW_SCHEDULE_PATH
    export_path = root / foundation.PRIMARY_EXPORT_PATH
    _verify_file_sha(
        schedule_path,
        freeze_receipt.protected_schedule_sha256,
        "J7L_V2_REVIEW_SCHEDULE_IDENTITY_DRIFT",
    )
    _verify_file_sha(
        export_path,
        freeze_receipt.protected_primary_export_sha256,
        "J7L_V2_REVIEW_EXPORT_IDENTITY_DRIFT",
    )

    try:
        schedule = J7LReviewScheduleV2.model_validate(_read_json(schedule_path))
        export = J7LReviewerExportV2.model_validate(_read_json(export_path))
    except ValidationError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_INPUT_TYPED_INVALID",
            "frozen reviewer-safe inputs failed typed validation",
        ) from error

    foundation._assert_reviewer_safe(export.model_dump(mode="json"))

    schedule_by_assignment = {entry.primary_assignment_id: entry for entry in schedule.entries}
    export_by_assignment = {item.assignment_id: item for item in export.items}

    if set(schedule_by_assignment) != set(export_by_assignment):
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_ASSIGNMENT_INVENTORY_DRIFT",
            "review schedule and reviewer-safe export assignment inventories differ",
        )

    assignment_to_case_id: dict[str, str] = {}
    for assignment_id, entry in schedule_by_assignment.items():
        item = export_by_assignment[assignment_id]
        if (
            item.review_item_id != entry.review_item_id
            or item.reviewer_safe_state_sha256 != entry.reviewer_safe_state_sha256
        ):
            raise HumanReviewQueueError(
                "J7L_V2_REVIEW_ITEM_IDENTITY_DRIFT",
                "review schedule and reviewer-safe item identities differ",
            )
        assignment_to_case_id[assignment_id] = entry.case_id

    return _Context(
        freeze_receipt=freeze_receipt,
        schedule=schedule,
        export=export,
        ordered_assignment_ids=_queue_order(tuple(export_by_assignment)),
        assignment_to_case_id=assignment_to_case_id,
    )


def validate_inputs(repo_root: Path) -> J7LHumanReviewPreflightReceiptV2:
    _load_context(repo_root)
    return J7LHumanReviewPreflightReceiptV2()


def initialize(
    repo_root: Path,
    *,
    reviewer_id_sha256: str,
    hidden_authoring_unread_attested: bool,
    human_judgments_before_ai_proposals_attested: bool,
) -> J7LHumanReviewerIdentityV2:
    root = repo_root.resolve()
    _load_context(root)

    if not hidden_authoring_unread_attested:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_HIDDEN_AUTHORING_ATTESTATION_REQUIRED",
            "initialization requires attestation that hidden authoring content remains unread",
        )
    if not human_judgments_before_ai_proposals_attested:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_HUMAN_FIRST_ATTESTATION_REQUIRED",
            "initialization requires human-first judgment attestation",
        )

    try:
        identity = J7LHumanReviewerIdentityV2(
            reviewer_id_sha256=reviewer_id_sha256,
        )
    except ValidationError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_REVIEWER_ID_INVALID",
            "reviewer identity SHA-256 failed typed validation",
        ) from error

    _write_once(
        root / REVIEWER_IDENTITY_PATH,
        _canonical_bytes(identity.model_dump(mode="json")),
    )
    return identity


def _load_identity(root: Path) -> J7LHumanReviewerIdentityV2:
    try:
        return J7LHumanReviewerIdentityV2.model_validate(_read_json(root / REVIEWER_IDENTITY_PATH))
    except ValidationError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_REVIEWER_IDENTITY_INVALID",
            "human reviewer identity failed typed validation",
        ) from error


def _work_item(
    context: _Context,
    *,
    assignment_id: str,
    queue_index: int,
) -> J7LHumanReviewWorkItemV2:
    item = next(
        candidate for candidate in context.export.items if candidate.assignment_id == assignment_id
    )
    instruction = (
        context.export.reviewer_instruction
        + " Make the human judgment yourself before consulting any AI assistant. "
        "After you have independently chosen the scores, failure labels, evidence "
        "references, and rationale, deterministic tooling may validate and serialize it."
    )
    work = J7LHumanReviewWorkItemV2(
        queue_index=queue_index,
        assignment_id=item.assignment_id,
        review_item_id=item.review_item_id,
        reviewer_safe_state_sha256=item.reviewer_safe_state_sha256,
        reviewer_safe_state=item.reviewer_safe_state,
        semantic_projection=context.export.semantic_projection,
        reviewer_instruction=instruction,
    )
    foundation._assert_reviewer_safe(work.model_dump(mode="json"))
    return work


def prepare(repo_root: Path) -> J7LHumanReviewPrepareReceiptV2:
    root = repo_root.resolve()
    context = _load_context(root)
    _load_identity(root)

    created_work = 0
    created_templates = 0

    for queue_index, assignment_id in enumerate(context.ordered_assignment_ids):
        work = _work_item(
            context,
            assignment_id=assignment_id,
            queue_index=queue_index,
        )
        created_work += int(
            _write_once(
                root / WORK_ROOT / f"{assignment_id}.json",
                _canonical_bytes(work.model_dump(mode="json")),
            )
        )
        template = J7LHumanReviewSubmissionTemplateV2(
            assignment_id=assignment_id,
            criterion_scores=tuple(
                CriterionDraftV2(criterion=criterion) for criterion in RubricCriterion
            ),
        )
        created_templates += int(
            _write_template_if_absent(
                root / SUBMISSION_ROOT / f"{assignment_id}.json",
                _canonical_bytes(template.model_dump(mode="json")),
            )
        )

    return J7LHumanReviewPrepareReceiptV2(
        created_work_item_count=created_work,
        created_submission_template_count=created_templates,
        work_item_root=WORK_ROOT.as_posix(),
        submission_root=SUBMISSION_ROOT.as_posix(),
    )


def _assessment_path(root: Path, assignment_id: str) -> Path:
    return root / ASSESSMENT_ROOT / f"{assignment_id}.json"


def _load_assessment(
    root: Path,
    context: _Context,
    identity: J7LHumanReviewerIdentityV2,
    assignment_id: str,
) -> J7LHumanAssessmentV2:
    try:
        assessment = J7LHumanAssessmentV2.model_validate(
            _read_json(_assessment_path(root, assignment_id))
        )
    except ValidationError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_ASSESSMENT_INVALID",
            "stored human assessment failed typed validation",
        ) from error

    if assessment.assignment_id != assignment_id:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_ASSESSMENT_ASSIGNMENT_DRIFT",
            "stored human assessment assignment identity drifted",
        )
    if assessment.case_id != context.assignment_to_case_id[assignment_id]:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_ASSESSMENT_CASE_DRIFT",
            "stored human assessment case identity drifted",
        )
    if assessment.reviewer_id_sha256 != identity.reviewer_id_sha256:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_ASSESSMENT_REVIEWER_DRIFT",
            "stored human assessment reviewer identity drifted",
        )
    return assessment


def status(repo_root: Path) -> J7LHumanReviewQueueStatusV2:
    root = repo_root.resolve()
    context = _load_context(root)
    identity = _load_identity(root)

    if (root / ASSESSMENT_ROOT).exists():
        observed = {
            path.stem
            for path in (root / ASSESSMENT_ROOT).glob("review-*.json")
            if path.is_file() and not path.is_symlink()
        }
        unexpected = sorted(observed - set(context.ordered_assignment_ids))
        if unexpected:
            raise HumanReviewQueueError(
                "J7L_V2_REVIEW_UNAUTHORIZED_ASSESSMENT_PRESENT",
                "assessment root contains an assignment outside the frozen queue",
            )

    completed: list[str] = []
    gap_seen = False
    for assignment_id in context.ordered_assignment_ids:
        path = _assessment_path(root, assignment_id)
        if not path.exists():
            gap_seen = True
            continue
        if path.is_symlink() or not path.is_file():
            raise HumanReviewQueueError(
                "J7L_V2_REVIEW_ASSESSMENT_PATH_UNSAFE",
                "human assessment path is unsafe",
            )
        if gap_seen:
            raise HumanReviewQueueError(
                "J7L_V2_REVIEW_OUT_OF_ORDER_ASSESSMENT",
                "stored assessments must form a strict prefix of the frozen review order",
            )
        _load_assessment(root, context, identity, assignment_id)
        completed.append(assignment_id)

    completed_count = len(completed)
    pending_count = EXPECTED_CASE_COUNT - completed_count
    next_assignment = context.ordered_assignment_ids[completed_count] if pending_count else None

    return J7LHumanReviewQueueStatusV2(
        status=(
            "J7L_V2_HUMAN_REVIEW_COMPLETE" if pending_count == 0 else "J7L_V2_HUMAN_REVIEW_PENDING"
        ),
        completed_assessment_count=completed_count,
        pending_assessment_count=pending_count,
        next_assignment_id=next_assignment,
        next_work_item_path=(
            (WORK_ROOT / f"{next_assignment}.json").as_posix()
            if next_assignment is not None
            else None
        ),
        next_submission_path=(
            (SUBMISSION_ROOT / f"{next_assignment}.json").as_posix()
            if next_assignment is not None
            else None
        ),
    )


def submit(
    repo_root: Path,
    submission_file: Path,
) -> J7LHumanReviewSubmissionReceiptV2:
    root = repo_root.resolve()
    context = _load_context(root)
    identity = _load_identity(root)
    queue = status(root)

    if queue.next_assignment_id is None:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_ALREADY_COMPLETE",
            "all 48 human assessments are already complete",
        )

    selected = submission_file if submission_file.is_absolute() else root / submission_file
    if not selected.is_file() or selected.is_symlink():
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_SUBMISSION_MISSING",
            "human-review submission file is missing or unsafe",
        )
    try:
        selected.resolve().relative_to((root / ".local").resolve())
    except ValueError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_SUBMISSION_OUTSIDE_LOCAL",
            "human-review submission must remain under repository .local",
        ) from error

    try:
        submission = J7LHumanReviewSubmissionV2.model_validate(_read_json(selected))
    except ValidationError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_SUBMISSION_INVALID",
            "human-review submission failed typed validation",
        ) from error

    if submission.assignment_id != queue.next_assignment_id:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_SUBMISSION_OUT_OF_ORDER",
            "submission must target the next frozen review assignment",
        )

    queue_index = context.ordered_assignment_ids.index(submission.assignment_id)
    expected_work = _work_item(
        context,
        assignment_id=submission.assignment_id,
        queue_index=queue_index,
    )
    expected_work_bytes = _canonical_bytes(expected_work.model_dump(mode="json"))
    work_path = root / WORK_ROOT / f"{submission.assignment_id}.json"

    if not work_path.is_file() or work_path.is_symlink():
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_WORK_ITEM_MISSING",
            "submission requires its prepared reviewer-safe work item",
        )
    if work_path.read_bytes() != expected_work_bytes:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_WORK_ITEM_DRIFT",
            "prepared reviewer-safe work item differs from the frozen input",
        )

    by_criterion = {item.criterion: item.score for item in submission.criterion_scores}
    scores = {criterion: by_criterion[criterion] for criterion in RubricCriterion}

    assessment = J7LHumanAssessmentV2(
        case_id=context.assignment_to_case_id[submission.assignment_id],
        assignment_id=submission.assignment_id,
        reviewer_id_sha256=identity.reviewer_id_sha256,
        work_item_sha256=_sha256_bytes(expected_work_bytes),
        reviewer_safe_state_sha256=expected_work.reviewer_safe_state_sha256,
        criterion_scores=scores,
        failure_labels=submission.failure_labels,
        evidence_references=submission.evidence_references,
        rationale=submission.rationale,
        verdict=derived_verdict(scores, submission.failure_labels),
    )
    assessment_bytes = _canonical_bytes(assessment.model_dump(mode="json"))
    created = _write_once(
        _assessment_path(root, submission.assignment_id),
        assessment_bytes,
    )

    updated = status(root)
    return J7LHumanReviewSubmissionReceiptV2(
        assignment_id=submission.assignment_id,
        assessment_sha256=_sha256_bytes(assessment_bytes),
        created=created,
        completed_assessment_count=updated.completed_assessment_count,
        pending_assessment_count=updated.pending_assessment_count,
        next_assignment_id=updated.next_assignment_id,
    )


def _all_assessments(
    root: Path,
    context: _Context,
    identity: J7LHumanReviewerIdentityV2,
) -> tuple[J7LHumanAssessmentV2, ...]:
    queue = status(root)
    if queue.pending_assessment_count != 0:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_INCOMPLETE",
            "all 48 human assessments must complete before coverage evaluation",
        )
    return tuple(
        _load_assessment(root, context, identity, assignment_id)
        for assignment_id in context.ordered_assignment_ids
    )


def _load_authoring_after_review(
    root: Path,
    context: _Context,
) -> J7LHumanFirstDevelopmentCaseSetV2:
    path = root / foundation.AUTHORING_CASE_SET_PATH
    _verify_file_sha(
        path,
        context.freeze_receipt.authoring_case_set_sha256,
        "J7L_V2_REVIEW_AUTHORING_IDENTITY_DRIFT",
    )
    try:
        return J7LHumanFirstDevelopmentCaseSetV2.model_validate(_read_json(path))
    except ValidationError as error:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_AUTHORING_TYPED_INVALID",
            "sealed authoring population failed typed validation after human review",
        ) from error


def build_coverage_report(
    case_set: J7LHumanFirstDevelopmentCaseSetV2,
    assessments: tuple[J7LHumanAssessmentV2, ...],
) -> J7LHumanReferenceCoverageReportV2:
    if len(assessments) != EXPECTED_CASE_COUNT:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_COVERAGE_ASSESSMENT_COUNT_INVALID",
            "coverage evaluation requires exactly 48 human assessments",
        )

    by_case = {assessment.case_id: assessment for assessment in assessments}
    if len(by_case) != EXPECTED_CASE_COUNT:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_COVERAGE_CASE_DUPLICATE",
            "coverage evaluation requires 48 unique human-assessed cases",
        )

    expected_case_ids = {case.case_id for case in case_set.cases}
    if set(by_case) != expected_case_ids:
        raise HumanReviewQueueError(
            "J7L_V2_REVIEW_COVERAGE_CASE_INVENTORY_DRIFT",
            "human assessment inventory differs from the sealed 48-case population",
        )

    verdict_counts = Counter(assessment.verdict for assessment in assessments)
    positive_counts = Counter(
        label for assessment in assessments for label in assessment.failure_labels
    )

    near_miss_negative: Counter[EpisodeFailureLabel] = Counter()
    for case in case_set.cases:
        observed_labels = set(by_case[case.case_id].failure_labels)
        for label in case.near_miss_label_targets:
            if label not in observed_labels:
                near_miss_negative[label] += 1

    distinct_counts: list[int] = []
    low_counts: list[int] = []
    high_counts: list[int] = []
    for criterion in RubricCriterion:
        scores = tuple(assessment.criterion_scores[criterion] for assessment in assessments)
        distinct_counts.append(len(set(scores)))
        low_counts.append(sum(score in {1, 2} for score in scores))
        high_counts.append(sum(score in {3, 4} for score in scores))

    terminal_material = sum(
        case.family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE
        and case.terminal_action_evidence_material
        for case in case_set.cases
    )

    pass_count = verdict_counts[ReviewVerdict.PASS]
    fail_count = verdict_counts[ReviewVerdict.FAIL]
    minimum_positive = min(positive_counts[label] for label in EpisodeFailureLabel)
    minimum_near_miss = min(near_miss_negative[label] for label in EpisodeFailureLabel)
    minimum_distinct = min(distinct_counts)
    minimum_low = min(low_counts)
    minimum_high = min(high_counts)

    checks = {
        "pass_fail_coverage_pass": pass_count >= 16 and fail_count >= 16,
        "positive_label_coverage_pass": minimum_positive >= 2,
        "near_miss_negative_coverage_pass": minimum_near_miss >= 2,
        "criterion_diversity_coverage_pass": minimum_distinct >= 3,
        "criterion_low_coverage_pass": minimum_low >= 4,
        "criterion_high_coverage_pass": minimum_high >= 4,
        "terminal_material_coverage_pass": terminal_material >= 8,
    }
    passed = all(checks.values())

    return J7LHumanReferenceCoverageReportV2(
        status=(
            "J7L_V2_HUMAN_REFERENCE_COVERAGE_PASS"
            if passed
            else "J7L_V2_HUMAN_REFERENCE_COVERAGE_FAIL"
        ),
        pass_count=pass_count,
        fail_count=fail_count,
        minimum_positive_support_observed=minimum_positive,
        minimum_near_miss_negative_support_observed=minimum_near_miss,
        minimum_distinct_scores_observed=minimum_distinct,
        minimum_low_scores_observed=minimum_low,
        minimum_high_scores_observed=minimum_high,
        terminal_material_evidence_case_count=terminal_material,
        pass_fail_coverage_pass=checks["pass_fail_coverage_pass"],
        positive_label_coverage_pass=checks["positive_label_coverage_pass"],
        near_miss_negative_coverage_pass=checks["near_miss_negative_coverage_pass"],
        criterion_diversity_coverage_pass=checks["criterion_diversity_coverage_pass"],
        criterion_low_coverage_pass=checks["criterion_low_coverage_pass"],
        criterion_high_coverage_pass=checks["criterion_high_coverage_pass"],
        terminal_material_coverage_pass=checks["terminal_material_coverage_pass"],
        next_gate=(
            "FREEZE_SINGLE_HUMAN_DEVELOPMENT_REFERENCE"
            if passed
            else "STOP_VERSIONED_SUCCESSOR_REQUIRED"
        ),
    )


def freeze_reference(repo_root: Path) -> J7LHumanReferencePublicReceiptV2:
    root = repo_root.resolve()
    context = _load_context(root)
    identity = _load_identity(root)
    assessments = _all_assessments(root, context, identity)

    case_set = _load_authoring_after_review(root, context)
    coverage = build_coverage_report(case_set, assessments)
    coverage_bytes = _canonical_bytes(coverage.model_dump(mode="json"))
    _write_once(root / COVERAGE_REPORT_PATH, coverage_bytes)

    if coverage.status != "J7L_V2_HUMAN_REFERENCE_COVERAGE_PASS":
        raise HumanReviewQueueError(
            "J7L_V2_HUMAN_REFERENCE_COVERAGE_FAILED",
            "human reference coverage failed; preserve evidence and use a versioned successor",
        )

    digests = tuple(
        AssessmentDigestV2(
            case_id=assessment.case_id,
            assignment_id=assessment.assignment_id,
            assessment_sha256=_sha256_file(_assessment_path(root, assessment.assignment_id)),
        )
        for assessment in assessments
    )

    foundation_freeze_sha256 = _sha256_file(root / foundation.PUBLIC_FREEZE_PATH)
    protected = J7LHumanReferenceFreezeV2(
        reviewer_id_sha256=identity.reviewer_id_sha256,
        foundation_case_freeze_sha256=foundation_freeze_sha256,
        coverage_report_sha256=_sha256_bytes(coverage_bytes),
        assessments=digests,
    )
    protected_bytes = _canonical_bytes(protected.model_dump(mode="json"))
    _write_once(root / HUMAN_REFERENCE_FREEZE_PATH, protected_bytes)

    public = J7LHumanReferencePublicReceiptV2(
        pass_count=coverage.pass_count,
        fail_count=coverage.fail_count,
        foundation_case_freeze_sha256=foundation_freeze_sha256,
        coverage_report_sha256=_sha256_bytes(coverage_bytes),
        protected_human_reference_freeze_sha256=_sha256_bytes(protected_bytes),
    )
    _write_once(
        root / PUBLIC_HUMAN_REFERENCE_RECEIPT_PATH,
        _canonical_bytes(public.model_dump(mode="json")),
    )
    return public


def verify_freeze(repo_root: Path) -> J7LHumanReferencePublicReceiptV2:
    root = repo_root.resolve()
    expected = freeze_reference(root)
    public_path = root / PUBLIC_HUMAN_REFERENCE_RECEIPT_PATH
    if public_path.read_bytes() != _canonical_bytes(expected.model_dump(mode="json")):
        raise HumanReviewQueueError(
            "J7L_V2_HUMAN_REFERENCE_PUBLIC_RECEIPT_DRIFT",
            "public human-reference freeze receipt bytes drifted",
        )
    return expected


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "validate-inputs",
            "initialize",
            "prepare",
            "status",
            "submit",
            "freeze-reference",
            "verify-freeze",
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--reviewer-id-sha256")
    parser.add_argument("--attest-hidden-authoring-unread", action="store_true")
    parser.add_argument(
        "--attest-human-judgments-before-ai-proposals",
        action="store_true",
    )
    parser.add_argument("--submission-file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result: BaseModel

    try:
        if args.command == "validate-inputs":
            result = validate_inputs(args.repo_root)
        elif args.command == "initialize":
            if args.reviewer_id_sha256 is None:
                raise HumanReviewQueueError(
                    "J7L_V2_REVIEW_REVIEWER_ID_REQUIRED",
                    "initialize requires --reviewer-id-sha256",
                )
            result = initialize(
                args.repo_root,
                reviewer_id_sha256=args.reviewer_id_sha256,
                hidden_authoring_unread_attested=args.attest_hidden_authoring_unread,
                human_judgments_before_ai_proposals_attested=(
                    args.attest_human_judgments_before_ai_proposals
                ),
            )
        elif args.command == "prepare":
            result = prepare(args.repo_root)
        elif args.command == "status":
            result = status(args.repo_root)
        elif args.command == "submit":
            if args.submission_file is None:
                raise HumanReviewQueueError(
                    "J7L_V2_REVIEW_SUBMISSION_REQUIRED",
                    "submit requires --submission-file",
                )
            result = submit(args.repo_root, args.submission_file)
        elif args.command == "freeze-reference":
            result = freeze_reference(args.repo_root)
        else:
            result = verify_freeze(args.repo_root)
    except (
        HumanReviewQueueError,
        ValidationError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, HumanReviewQueueError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, ValidationError):
            code = "J7L_V2_REVIEW_TYPED_VALIDATION_FAILED"
            message = "J7L V2 human-review typed validation failed"
        elif isinstance(error, json.JSONDecodeError):
            code = "J7L_V2_REVIEW_JSON_DECODE_FAILED"
            message = "J7L V2 human-review JSON decoding failed"
        else:
            code = "J7L_V2_REVIEW_LOCAL_IO_FAILED"
            message = "J7L V2 human-review local I/O failed"

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

    print(
        json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
