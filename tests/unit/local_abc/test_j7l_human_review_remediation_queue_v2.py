from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.j7l_human_review_remediation_v2 import (
    EXPECTED_REMEDIATION_CASE_IDS,
    EXPECTED_V1_ASSESSMENT_ACTOR_SHA256,
    AssessmentDigestV2,
    CriterionSubmissionV2,
    J7LFullHumanInventoryFreezeV2,
    J7LHumanReviewRemediationPolicyV2,
    J7LRemediationHumanAssessmentV2,
    J7LRemediationReviewerIdentityV2,
    J7LRemediationSubmissionV2,
    J7LV1ContaminationFreezeV2,
)
from auragateway.local_abc import j7l_human_review_remediation_queue_v2 as subject


def _scores(value: int) -> dict[RubricCriterion, int]:
    return {criterion: value for criterion in RubricCriterion}


def test_policy_marks_v1_non_advancing_and_requires_fresh_20() -> None:
    policy = J7LHumanReviewRemediationPolicyV2()

    assert policy.predecessor_v1_lineage_non_advancing is True
    assert policy.predecessor_v1_assessment_mutation_permitted is False
    assert policy.predecessor_v1_assessment_reuse_permitted is False
    assert policy.predecessor_v1_submitted_contaminated_count == 8
    assert policy.preserved_original_human_assessment_count == 28
    assert policy.fresh_remediation_assessment_count == 20
    assert policy.fresh_reviewer_required is True
    assert policy.fresh_reviewer_must_differ_from_v1_actor is True
    assert policy.fresh_assessment_required_for_all_20_cases is True
    assert policy.provider_requests_authorized is False
    assert policy.jev_requests_authorized is False


def test_remediation_case_inventory_is_exact_20() -> None:
    assert (
        *(f"j7l-dev-{index:03d}" for index in range(3, 13)),
        *(f"j7l-dev-{index:03d}" for index in range(15, 25)),
    ) == EXPECTED_REMEDIATION_CASE_IDS
    assert len(EXPECTED_REMEDIATION_CASE_IDS) == 20


def test_reviewer_identity_rejects_v1_actor() -> None:
    with pytest.raises(ValidationError, match="must differ from the V1"):
        J7LRemediationReviewerIdentityV2(
            reviewer_id_sha256=EXPECTED_V1_ASSESSMENT_ACTOR_SHA256,
            distinct_from_v1_assessment_actor_attested=True,
            no_prior_ai_or_v1_judgment_exposure_attested=True,
        )


def test_contamination_freeze_requires_exact_incident_inventory() -> None:
    wrong = tuple(
        AssessmentDigestV2(
            case_id=f"j7l-dev-{index:03d}",
            assessment_sha256="a" * 64,
        )
        for index in range(4, 12)
    )

    with pytest.raises(ValidationError, match="frozen incident"):
        J7LV1ContaminationFreezeV2(
            contaminated_assessments=wrong,
        )


def test_submission_requires_each_criterion_exactly_once() -> None:
    repeated = tuple(
        CriterionSubmissionV2(
            criterion=RubricCriterion.TASK_CORRECTNESS,
            score=3,
            evidence_note="Visible evidence supports this score.",
        )
        for _ in range(7)
    )

    with pytest.raises(ValidationError, match="every rubric criterion"):
        J7LRemediationSubmissionV2(
            case_id="j7l-dev-003",
            criterion_scores=repeated,
            evidence_references=("visible-evidence-1",),
            rationale="The visible evidence supports this assessment.",
        )


def test_assessment_rejects_verdict_drift() -> None:
    with pytest.raises(ValidationError, match="frozen derivation rule"):
        J7LRemediationHumanAssessmentV2(
            case_id="j7l-dev-003",
            assessment_actor_id_sha256="b" * 64,
            work_item_sha256="c" * 64,
            reviewer_safe_state_sha256="d" * 64,
            criterion_scores=_scores(3),
            failure_labels=(),
            evidence_references=("visible-evidence-1",),
            rationale="The visible evidence supports this assessment.",
            verdict=ReviewVerdict.FAIL,
        )


def test_full_human_freeze_requires_exact_ordered_20() -> None:
    wrong = tuple(
        AssessmentDigestV2(
            case_id=case_id,
            assessment_sha256="e" * 64,
        )
        for case_id in reversed(EXPECTED_REMEDIATION_CASE_IDS)
    )

    with pytest.raises(ValidationError, match="exact ordered 20-case"):
        J7LFullHumanInventoryFreezeV2(
            remediation_reviewer_id_sha256="f" * 64,
            remediation_assessments=wrong,
        )


def test_write_once_rejects_mutation(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"

    assert subject._write_once(path, b'{"value":1}\n') is True
    assert subject._write_once(path, b'{"value":1}\n') is False

    with pytest.raises(
        subject.RemediationQueueError,
        match="differs from expected bytes",
    ):
        subject._write_once(path, b'{"value":2}\n')
