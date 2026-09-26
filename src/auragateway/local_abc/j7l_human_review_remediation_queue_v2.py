"""Clean V2 human-review remediation queue for the J7L successor lineage.

V1 remains preserved and non-advancing because eight submitted successor
assessments were authored by an AI assistant and pasted as human judgments.
This V2 lineage requires a distinct human reviewer to assess all twenty cases
that were outside the original frozen 28-case human audit.

The human work-item path never includes V1 assessment content, model-reference
judgments, predecessor comparison content, Jev output, authoring targets, or
case-family metadata.
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
    J7LSuccessorHumanAssessmentV1,
    derived_verdict,
)
from auragateway.contracts.j7l_human_review_remediation_v2 import (
    EXPECTED_KNOWN_EXPOSED_UNSUBMITTED_CASE_IDS,
    EXPECTED_REMEDIATION_CASE_IDS,
    EXPECTED_V1_ASSESSMENT_ACTOR_SHA256,
    EXPECTED_V1_CONTAMINATED_CASE_IDS,
    AssessmentDigestV2,
    CriterionDraftV2,
    J7LFullHumanInventoryFreezeV2,
    J7LHumanReviewRemediationPolicyV2,
    J7LRemediationHumanAssessmentV2,
    J7LRemediationHumanWorkItemV2,
    J7LRemediationInitializeReceiptV2,
    J7LRemediationPreflightReceiptV2,
    J7LRemediationPrepareReceiptV2,
    J7LRemediationQueueStatusV2,
    J7LRemediationReviewerIdentityV2,
    J7LRemediationSubmissionReceiptV2,
    J7LRemediationSubmissionTemplateV2,
    J7LRemediationSubmissionV2,
    J7LV1ContaminationFreezeV2,
)
from auragateway.local_abc import (
    j7l_audited_adjudicated_development_reference_queue_v1 as v1_queue,
)
from auragateway.local_abc import j7l_reference_human_audit_comparison_v1 as predecessor
from auragateway.local_abc import j7l_reference_human_audit_queue_v1 as audit_queue
from auragateway.local_abc import quality_development_case_freeze_v1 as case_freeze

QUEUE_ROOT = Path(".local/auragateway/j7l-human-review-remediation-v2")
CONTAMINATION_FREEZE_PATH = QUEUE_ROOT / "v1_contamination_freeze.json"
REVIEWER_IDENTITY_PATH = QUEUE_ROOT / "reviewer_identity.json"
WORK_ROOT = QUEUE_ROOT / "work-items"
SUBMISSION_ROOT = QUEUE_ROOT / "submissions"
ASSESSMENT_ROOT = QUEUE_ROOT / "assessments"
FULL_HUMAN_FREEZE_PATH = QUEUE_ROOT / "full_human_inventory_freeze.json"

POLICY = J7LHumanReviewRemediationPolicyV2()

_REMEDIATION_REVIEWER_INSTRUCTION = (
    " Complete this assessment independently. Do not use scores, failure labels, "
    "verdicts, evidence notes, or rationale proposed by any AI assistant or prior "
    "reviewer. Use only this reviewer-safe work item and its included human semantic "
    "projection."
)


class RemediationQueueError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise RemediationQueueError("J7L_REMEDIATION_ARGUMENT_ERROR", message)


class _Context(NamedTuple):
    base: v1_queue._Context
    contamination_freeze: J7LV1ContaminationFreezeV2
    reviewer_identity: J7LRemediationReviewerIdentityV2


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


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise RemediationQueueError(
            "J7L_REMEDIATION_FILE_MISSING",
            f"required remediation input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RemediationQueueError(
            "J7L_REMEDIATION_JSON_INVALID",
            f"remediation input is not valid UTF-8 JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise RemediationQueueError(
            "J7L_REMEDIATION_JSON_SHAPE_INVALID",
            f"remediation input root must be an object: {path.as_posix()}",
        )
    return value


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise RemediationQueueError(
                "J7L_REMEDIATION_OUTPUT_PATH_UNSAFE",
                "remediation output path is unsafe",
            )
        if path.read_bytes() != payload:
            raise RemediationQueueError(
                "J7L_REMEDIATION_APPEND_ONLY_CONFLICT",
                "existing remediation output differs from expected bytes",
            )
        return False
    with path.open("xb") as handle:
        handle.write(payload)
    return True


def _write_template_if_absent(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise RemediationQueueError(
                "J7L_REMEDIATION_SUBMISSION_PATH_UNSAFE",
                "remediation submission path is unsafe",
            )
        return False
    with path.open("xb") as handle:
        handle.write(payload)
    return True


def _base_context(root: Path) -> v1_queue._Context:
    try:
        context = v1_queue._load_context(root)
    except v1_queue.SuccessorQueueError as error:
        raise RemediationQueueError(
            "J7L_REMEDIATION_PREDECESSOR_CONTEXT_INVALID",
            "V1 successor predecessor context is invalid",
        ) from error
    if context.remaining_case_ids != EXPECTED_REMEDIATION_CASE_IDS:
        raise RemediationQueueError(
            "J7L_REMEDIATION_CASE_INVENTORY_DRIFT",
            "V2 remediation subject differs from the exact frozen 20-case remainder",
        )
    return context


def _observe_v1_contamination(root: Path) -> J7LV1ContaminationFreezeV2:
    context = _base_context(root)
    try:
        v1_status = v1_queue.status(root)
    except v1_queue.SuccessorQueueError as error:
        raise RemediationQueueError(
            "J7L_REMEDIATION_V1_STATUS_INVALID",
            "V1 successor queue cannot be validated for contamination freeze",
        ) from error

    if (
        v1_status.successor_completed_assessment_count != 8
        or v1_status.total_completed_human_assessment_count != 36
        or v1_status.pending_successor_assessment_count != 12
        or v1_status.next_case_id != "j7l-dev-011"
    ):
        raise RemediationQueueError(
            "J7L_REMEDIATION_V1_CONTAMINATION_STATE_DRIFT",
            "V1 successor queue is not at the frozen 8-submission contamination state",
        )

    observed_ids = tuple(
        case_id
        for case_id in context.remaining_case_ids
        if (root / v1_queue.ASSESSMENT_ROOT / f"{case_id}.json").is_file()
    )
    if observed_ids != EXPECTED_V1_CONTAMINATED_CASE_IDS:
        raise RemediationQueueError(
            "J7L_REMEDIATION_V1_CONTAMINATED_CASE_INVENTORY_DRIFT",
            "V1 contaminated assessment IDs differ from the frozen incident",
        )

    digests: list[AssessmentDigestV2] = []
    for case_id in EXPECTED_V1_CONTAMINATED_CASE_IDS:
        path = root / v1_queue.ASSESSMENT_ROOT / f"{case_id}.json"
        if path.is_symlink() or not path.is_file():
            raise RemediationQueueError(
                "J7L_REMEDIATION_V1_ASSESSMENT_PATH_UNSAFE",
                f"{case_id} V1 contaminated assessment path is unsafe",
            )
        try:
            assessment = J7LSuccessorHumanAssessmentV1.model_validate(_read_json(path))
        except ValidationError as error:
            raise RemediationQueueError(
                "J7L_REMEDIATION_V1_ASSESSMENT_INVALID",
                f"{case_id} V1 contaminated assessment failed typed validation",
            ) from error
        if assessment.case_id != case_id:
            raise RemediationQueueError(
                "J7L_REMEDIATION_V1_ASSESSMENT_CASE_DRIFT",
                f"{case_id} V1 contaminated assessment identity drifted",
            )
        if assessment.assessment_actor_id_sha256 != EXPECTED_V1_ASSESSMENT_ACTOR_SHA256:
            raise RemediationQueueError(
                "J7L_REMEDIATION_V1_ASSESSMENT_ACTOR_DRIFT",
                f"{case_id} V1 contaminated assessment actor drifted",
            )
        digests.append(
            AssessmentDigestV2(
                case_id=case_id,
                assessment_sha256=_sha256_file(path),
            )
        )

    return J7LV1ContaminationFreezeV2(
        contaminated_assessments=tuple(digests),
        known_exposed_unsubmitted_case_ids=(EXPECTED_KNOWN_EXPOSED_UNSUBMITTED_CASE_IDS),
    )


def observe_v1(repo_root: Path) -> J7LV1ContaminationFreezeV2:
    return _observe_v1_contamination(repo_root.resolve())


def initialize(
    repo_root: Path,
    reviewer_id_sha256: str,
    *,
    reviewer_independence_attested: bool,
    reviewer_no_prior_exposure_attested: bool,
) -> J7LRemediationInitializeReceiptV2:
    root = repo_root.resolve()

    if not reviewer_independence_attested:
        raise RemediationQueueError(
            "J7L_REMEDIATION_REVIEWER_INDEPENDENCE_ATTESTATION_REQUIRED",
            "initialize requires explicit distinct-human reviewer attestation",
        )
    if not reviewer_no_prior_exposure_attested:
        raise RemediationQueueError(
            "J7L_REMEDIATION_REVIEWER_EXPOSURE_ATTESTATION_REQUIRED",
            ("initialize requires attestation that the reviewer has not seen prior judgments"),
        )

    freeze = _observe_v1_contamination(root)
    try:
        reviewer = J7LRemediationReviewerIdentityV2(
            reviewer_id_sha256=reviewer_id_sha256,
            distinct_from_v1_assessment_actor_attested=True,
            no_prior_ai_or_v1_judgment_exposure_attested=True,
        )
    except ValidationError as error:
        raise RemediationQueueError(
            "J7L_REMEDIATION_REVIEWER_IDENTITY_INVALID",
            "remediation reviewer identity failed typed validation",
        ) from error

    _write_once(
        root / CONTAMINATION_FREEZE_PATH,
        _canonical_bytes(freeze.model_dump(mode="json")),
    )
    _write_once(
        root / REVIEWER_IDENTITY_PATH,
        _canonical_bytes(reviewer.model_dump(mode="json")),
    )

    return J7LRemediationInitializeReceiptV2(
        reviewer_id_sha256=reviewer.reviewer_id_sha256,
    )


def _load_governed_context(root: Path) -> _Context:
    base = _base_context(root)
    current_contamination = _observe_v1_contamination(root)

    try:
        frozen_contamination = J7LV1ContaminationFreezeV2.model_validate(
            _read_json(root / CONTAMINATION_FREEZE_PATH)
        )
        reviewer_identity = J7LRemediationReviewerIdentityV2.model_validate(
            _read_json(root / REVIEWER_IDENTITY_PATH)
        )
    except ValidationError as error:
        raise RemediationQueueError(
            "J7L_REMEDIATION_GOVERNANCE_INPUT_INVALID",
            "V2 remediation governance input failed typed validation",
        ) from error

    if current_contamination != frozen_contamination:
        raise RemediationQueueError(
            "J7L_REMEDIATION_V1_CONTAMINATION_FREEZE_DRIFT",
            ("current V1 contamination state differs from the frozen remediation binding"),
        )

    return _Context(
        base=base,
        contamination_freeze=frozen_contamination,
        reviewer_identity=reviewer_identity,
    )


def _work_item(
    context: _Context,
    case_id: str,
    queue_index: int,
) -> J7LRemediationHumanWorkItemV2:
    entry = next(
        (candidate for candidate in context.base.schedule.entries if candidate.case_id == case_id),
        None,
    )
    if entry is None:
        raise RemediationQueueError(
            "J7L_REMEDIATION_SCHEDULE_CASE_MISSING",
            f"{case_id} is missing from the frozen review schedule",
        )
    item = next(
        (
            candidate
            for candidate in context.base.primary_export.items
            if candidate.assignment_id == entry.primary_assignment_id
        ),
        None,
    )
    if item is None:
        raise RemediationQueueError(
            "J7L_REMEDIATION_PRIMARY_ITEM_MISSING",
            f"{case_id} primary reviewer item is missing",
        )
    if item.review_item_id != entry.review_item_id:
        raise RemediationQueueError(
            "J7L_REMEDIATION_REVIEW_ITEM_DRIFT",
            f"{case_id} review-item identity drifted",
        )
    if item.reviewer_safe_state_sha256 != entry.reviewer_safe_state_sha256:
        raise RemediationQueueError(
            "J7L_REMEDIATION_SAFE_STATE_DRIFT",
            f"{case_id} reviewer-safe state identity drifted",
        )
    case_freeze.assert_reviewer_export_safe(item.model_dump(mode="json"))

    reviewer_instruction = (
        context.base.primary_export.reviewer_instruction + _REMEDIATION_REVIEWER_INSTRUCTION
    )

    return J7LRemediationHumanWorkItemV2(
        case_id=case_id,
        queue_index=queue_index,
        source_assignment_id=entry.primary_assignment_id,
        review_item_id=item.review_item_id,
        reviewer_safe_state_sha256=item.reviewer_safe_state_sha256,
        reviewer_safe_state=item.reviewer_safe_state,
        semantic_projection=context.base.primary_export.semantic_projection,
        reviewer_instruction=reviewer_instruction,
        assessment_actor_id_sha256=context.reviewer_identity.reviewer_id_sha256,
    )


def validate_inputs(repo_root: Path) -> J7LRemediationPreflightReceiptV2:
    root = repo_root.resolve()
    context = _load_governed_context(root)
    for index, case_id in enumerate(EXPECTED_REMEDIATION_CASE_IDS):
        _work_item(context, case_id, index)
    return J7LRemediationPreflightReceiptV2()


def prepare(repo_root: Path) -> J7LRemediationPrepareReceiptV2:
    root = repo_root.resolve()
    context = _load_governed_context(root)
    created_work_items = 0
    created_templates = 0

    for index, case_id in enumerate(EXPECTED_REMEDIATION_CASE_IDS):
        work = _work_item(context, case_id, index)
        work_bytes = _canonical_bytes(work.model_dump(mode="json"))
        created_work_items += int(_write_once(root / WORK_ROOT / f"{case_id}.json", work_bytes))

        template = J7LRemediationSubmissionTemplateV2(
            case_id=case_id,
            criterion_scores=tuple(
                CriterionDraftV2(criterion=criterion) for criterion in RubricCriterion
            ),
        )
        created_templates += int(
            _write_template_if_absent(
                root / SUBMISSION_ROOT / f"{case_id}.json",
                _canonical_bytes(template.model_dump(mode="json")),
            )
        )

    return J7LRemediationPrepareReceiptV2(
        created_work_item_count=created_work_items,
        created_submission_template_count=created_templates,
        work_item_root=WORK_ROOT.as_posix(),
        submission_root=SUBMISSION_ROOT.as_posix(),
    )


def status(repo_root: Path) -> J7LRemediationQueueStatusV2:
    root = repo_root.resolve()
    context = _load_governed_context(root)
    allowed = set(EXPECTED_REMEDIATION_CASE_IDS)

    if (root / ASSESSMENT_ROOT).exists():
        observed_ids = tuple(
            sorted(path.stem for path in (root / ASSESSMENT_ROOT).glob("j7l-dev-*.json"))
        )
        unexpected = tuple(case_id for case_id in observed_ids if case_id not in allowed)
        if unexpected:
            raise RemediationQueueError(
                "J7L_REMEDIATION_UNAUTHORIZED_ASSESSMENT_PRESENT",
                "remediation assessment root contains an unauthorized case",
            )

    completed: list[str] = []
    for case_id in EXPECTED_REMEDIATION_CASE_IDS:
        path = root / ASSESSMENT_ROOT / f"{case_id}.json"
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file():
            raise RemediationQueueError(
                "J7L_REMEDIATION_ASSESSMENT_PATH_UNSAFE",
                f"{case_id} remediation assessment path is unsafe",
            )
        try:
            assessment = J7LRemediationHumanAssessmentV2.model_validate(_read_json(path))
        except ValidationError as error:
            raise RemediationQueueError(
                "J7L_REMEDIATION_ASSESSMENT_INVALID",
                f"{case_id} remediation assessment failed typed validation",
            ) from error
        if assessment.case_id != case_id:
            raise RemediationQueueError(
                "J7L_REMEDIATION_ASSESSMENT_CASE_DRIFT",
                f"{case_id} remediation assessment identity drifted",
            )
        if assessment.assessment_actor_id_sha256 != context.reviewer_identity.reviewer_id_sha256:
            raise RemediationQueueError(
                "J7L_REMEDIATION_ASSESSMENT_ACTOR_DRIFT",
                f"{case_id} remediation assessment actor drifted",
            )
        completed.append(case_id)

    pending = tuple(
        case_id for case_id in EXPECTED_REMEDIATION_CASE_IDS if case_id not in set(completed)
    )
    next_case_id = pending[0] if pending else None

    return J7LRemediationQueueStatusV2(
        status=(
            "REMEDIATION_HUMAN_REVIEW_COMPLETE"
            if not pending
            else "REMEDIATION_HUMAN_REVIEW_PENDING"
        ),
        remediation_completed_assessment_count=len(completed),
        total_clean_human_assessment_count=28 + len(completed),
        pending_remediation_assessment_count=len(pending),
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


def submit(
    repo_root: Path,
    submission_file: Path,
) -> J7LRemediationSubmissionReceiptV2:
    root = repo_root.resolve()
    context = _load_governed_context(root)
    queue_before = status(root)

    selected = submission_file if submission_file.is_absolute() else root / submission_file
    if not selected.is_file() or selected.is_symlink():
        raise RemediationQueueError(
            "J7L_REMEDIATION_SUBMISSION_MISSING",
            "remediation human-review submission file is missing or unsafe",
        )
    try:
        selected.resolve().relative_to((root / ".local").resolve())
    except ValueError as error:
        raise RemediationQueueError(
            "J7L_REMEDIATION_SUBMISSION_OUTSIDE_LOCAL",
            "remediation human-review submission must remain under repository .local",
        ) from error

    try:
        submission = J7LRemediationSubmissionV2.model_validate(_read_json(selected))
    except ValidationError as error:
        raise RemediationQueueError(
            "J7L_REMEDIATION_SUBMISSION_INVALID",
            "remediation human-review submission failed typed validation",
        ) from error

    if submission.case_id not in set(EXPECTED_REMEDIATION_CASE_IDS):
        raise RemediationQueueError(
            "J7L_REMEDIATION_CASE_NOT_AUTHORIZED",
            "submission case is outside the exact 20-case remediation population",
        )
    if submission.case_id != queue_before.next_case_id:
        raise RemediationQueueError(
            "J7L_REMEDIATION_OUT_OF_ORDER_SUBMISSION",
            "remediation submissions must follow frozen case order",
        )

    queue_index = EXPECTED_REMEDIATION_CASE_IDS.index(submission.case_id)
    expected_work = _work_item(context, submission.case_id, queue_index)
    expected_work_bytes = _canonical_bytes(expected_work.model_dump(mode="json"))
    work_path = root / WORK_ROOT / f"{submission.case_id}.json"
    if not work_path.is_file() or work_path.is_symlink():
        raise RemediationQueueError(
            "J7L_REMEDIATION_WORK_ITEM_MISSING",
            "submission requires its prepared blinded work item",
        )
    if work_path.read_bytes() != expected_work_bytes:
        raise RemediationQueueError(
            "J7L_REMEDIATION_WORK_ITEM_DRIFT",
            "prepared remediation work item differs from frozen reviewer-safe input",
        )

    by_criterion = {item.criterion: item for item in submission.criterion_scores}
    scores = {criterion: by_criterion[criterion].score for criterion in RubricCriterion}
    assessment = J7LRemediationHumanAssessmentV2(
        case_id=submission.case_id,
        assessment_actor_id_sha256=context.reviewer_identity.reviewer_id_sha256,
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

    queue_after = status(root)
    return J7LRemediationSubmissionReceiptV2(
        case_id=submission.case_id,
        assessment_sha256=hashlib.sha256(assessment_bytes).hexdigest(),
        created=created,
        total_clean_human_assessment_count=(queue_after.total_clean_human_assessment_count),
        pending_remediation_assessment_count=(queue_after.pending_remediation_assessment_count),
        next_case_id=queue_after.next_case_id,
    )


def freeze(repo_root: Path) -> J7LFullHumanInventoryFreezeV2:
    root = repo_root.resolve()
    context = _load_governed_context(root)
    queue = status(root)
    if queue.pending_remediation_assessment_count != 0:
        raise RemediationQueueError(
            "J7L_REMEDIATION_FREEZE_BEFORE_COMPLETION_FORBIDDEN",
            "full human inventory may be frozen only after all 20 fresh assessments",
        )

    try:
        _, predecessor_freeze_sha256 = predecessor._load_and_validate_freeze(root)
    except predecessor.ReferenceAuditComparisonError as error:
        raise RemediationQueueError(
            "J7L_REMEDIATION_PREDECESSOR_HUMAN_FREEZE_INVALID",
            "original 28-case human freeze no longer validates",
        ) from error

    digests: list[AssessmentDigestV2] = []
    for case_id in EXPECTED_REMEDIATION_CASE_IDS:
        path = root / ASSESSMENT_ROOT / f"{case_id}.json"
        assessment = J7LRemediationHumanAssessmentV2.model_validate(_read_json(path))
        if assessment.assessment_actor_id_sha256 != context.reviewer_identity.reviewer_id_sha256:
            raise RemediationQueueError(
                "J7L_REMEDIATION_FREEZE_ACTOR_DRIFT",
                f"{case_id} remediation assessment actor drifted before freeze",
            )
        digests.append(
            AssessmentDigestV2(
                case_id=case_id,
                assessment_sha256=_sha256_file(path),
            )
        )

    human_freeze = J7LFullHumanInventoryFreezeV2(
        predecessor_human_freeze_sha256=predecessor_freeze_sha256,
        remediation_reviewer_id_sha256=(context.reviewer_identity.reviewer_id_sha256),
        remediation_assessments=tuple(digests),
    )
    _write_once(
        root / FULL_HUMAN_FREEZE_PATH,
        _canonical_bytes(human_freeze.model_dump(mode="json")),
    )
    return human_freeze


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "observe-v1",
            "initialize",
            "validate-inputs",
            "prepare",
            "status",
            "submit",
            "freeze",
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--submission-file", type=Path)
    parser.add_argument("--reviewer-id-sha256")
    parser.add_argument(
        "--reviewer-independence-attested",
        action="store_true",
    )
    parser.add_argument(
        "--reviewer-no-prior-exposure-attested",
        action="store_true",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result: BaseModel
    try:
        if args.command == "observe-v1":
            result = observe_v1(args.repo_root)
        elif args.command == "initialize":
            if args.reviewer_id_sha256 is None:
                raise RemediationQueueError(
                    "J7L_REMEDIATION_REVIEWER_ID_REQUIRED",
                    "initialize requires --reviewer-id-sha256",
                )
            result = initialize(
                args.repo_root,
                args.reviewer_id_sha256,
                reviewer_independence_attested=(args.reviewer_independence_attested),
                reviewer_no_prior_exposure_attested=(args.reviewer_no_prior_exposure_attested),
            )
        elif args.command == "validate-inputs":
            result = validate_inputs(args.repo_root)
        elif args.command == "prepare":
            result = prepare(args.repo_root)
        elif args.command == "status":
            result = status(args.repo_root)
        elif args.command == "submit":
            if args.submission_file is None:
                raise RemediationQueueError(
                    "J7L_REMEDIATION_SUBMISSION_REQUIRED",
                    "submit requires --submission-file",
                )
            result = submit(args.repo_root, args.submission_file)
        else:
            result = freeze(args.repo_root)
    except (
        RemediationQueueError,
        predecessor.ReferenceAuditComparisonError,
        audit_queue.HumanAuditQueueError,
        case_freeze.J7LCaseFreezeError,
        ValidationError,
        OSError,
    ) as error:
        if isinstance(error, RemediationQueueError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, predecessor.ReferenceAuditComparisonError):
            code = "J7L_REMEDIATION_PREDECESSOR_AUDIT_INVALID"
            message = "failed V3 predecessor audit evidence is invalid"
        elif isinstance(error, audit_queue.HumanAuditQueueError):
            code = "J7L_REMEDIATION_PREDECESSOR_HUMAN_INPUT_INVALID"
            message = "predecessor human-review input is invalid"
        elif isinstance(error, case_freeze.J7LCaseFreezeError):
            code = "J7L_REMEDIATION_REVIEWER_SAFE_INPUT_INVALID"
            message = "frozen reviewer-safe input is invalid"
        elif isinstance(error, ValidationError):
            code = "J7L_REMEDIATION_TYPED_VALIDATION_FAILED"
            message = "J7L remediation typed validation failed"
        else:
            code = "J7L_REMEDIATION_LOCAL_IO_FAILED"
            message = "J7L remediation local I/O failed"

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
