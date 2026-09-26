from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.j7l_audited_adjudicated_development_reference_v1 import (
    CriterionSubmission,
    J7LAuditedAdjudicatedDevelopmentReferencePolicyV1,
    J7LSuccessorHumanAssessmentV1,
    J7LSuccessorSubmissionV1,
    derived_verdict,
)
from auragateway.local_abc import (
    j7l_audited_adjudicated_development_reference_queue_v1 as subject,
)


def _scores(value: int) -> dict[RubricCriterion, int]:
    return {criterion: value for criterion in RubricCriterion}


def test_policy_preserves_failed_v3_and_requires_full_human_population() -> None:
    policy = J7LAuditedAdjudicatedDevelopmentReferencePolicyV1()

    assert policy.failed_v3_lineage_remains_failed is True
    assert policy.failed_v3_reference_mutation_permitted is False
    assert policy.failed_v3_human_rescoring_permitted is False
    assert policy.preserved_human_assessment_count == 28
    assert policy.remaining_human_assessment_count == 20
    assert policy.required_full_human_assessment_count == 48
    assert policy.model_judgment_direct_authority_permitted is False
    assert policy.material_disagreement_resolution_source == "INDEPENDENT_ADJUDICATION"
    assert policy.development_only is True
    assert policy.j7m_qualification_claim_permitted is False


def test_remaining_case_ids_preserves_frozen_case_order() -> None:
    all_ids = tuple(f"j7l-dev-{index:03d}" for index in range(1, 49))
    preserved = (
        *(f"j7l-dev-{index:03d}" for index in range(25, 49)),
        "j7l-dev-001",
        "j7l-dev-002",
        "j7l-dev-013",
        "j7l-dev-014",
    )

    remaining = subject._remaining_case_ids(all_ids, preserved)

    assert remaining == (
        *(f"j7l-dev-{index:03d}" for index in range(3, 13)),
        *(f"j7l-dev-{index:03d}" for index in range(15, 25)),
    )
    assert len(remaining) == 20


def test_remaining_case_ids_rejects_wrong_preserved_count() -> None:
    all_ids = tuple(f"j7l-dev-{index:03d}" for index in range(1, 49))
    preserved = tuple(f"j7l-dev-{index:03d}" for index in range(1, 28))

    with pytest.raises(subject.SuccessorQueueError, match="28 unique cases"):
        subject._remaining_case_ids(all_ids, preserved)


def test_derived_verdict_matches_frozen_rule() -> None:
    passing_scores = _scores(3)
    failing_scores = _scores(1)

    assert derived_verdict(passing_scores, ()) is ReviewVerdict.PASS
    assert (
        derived_verdict(
            passing_scores,
            (EpisodeFailureLabel.UNSUPPORTED_CLAIM,),
        )
        is ReviewVerdict.FAIL
    )
    assert derived_verdict(failing_scores, ()) is ReviewVerdict.FAIL


def test_submission_requires_each_criterion_exactly_once() -> None:
    repeated = tuple(
        CriterionSubmission(
            criterion=RubricCriterion.TASK_CORRECTNESS,
            score=3,
            evidence_note="Visible evidence supports this score.",
        )
        for _ in range(7)
    )

    with pytest.raises(ValidationError, match="every rubric criterion"):
        J7LSuccessorSubmissionV1(
            case_id="j7l-dev-003",
            criterion_scores=repeated,
            evidence_references=("visible-evidence-1",),
            rationale="The visible evidence supports this assessment.",
        )


def test_assessment_rejects_verdict_that_differs_from_frozen_derivation() -> None:
    with pytest.raises(ValidationError, match="frozen derivation rule"):
        J7LSuccessorHumanAssessmentV1(
            case_id="j7l-dev-003",
            assessment_actor_id_sha256="a" * 64,
            work_item_sha256="b" * 64,
            reviewer_safe_state_sha256="c" * 64,
            criterion_scores=_scores(3),
            failure_labels=(),
            evidence_references=("visible-evidence-1",),
            rationale="The visible evidence supports this assessment.",
            verdict=ReviewVerdict.FAIL,
        )


def test_write_once_rejects_mutation(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"

    assert subject._write_once(path, b'{"value":1}\n') is True
    assert subject._write_once(path, b'{"value":1}\n') is False

    with pytest.raises(subject.SuccessorQueueError, match="differs from expected bytes"):
        subject._write_once(path, b'{"value":2}\n')


def test_submission_json_shape_is_deterministic() -> None:
    criteria = tuple(
        CriterionSubmission(
            criterion=criterion,
            score=3,
            evidence_note=f"Visible evidence supports {criterion.value}.",
        )
        for criterion in RubricCriterion
    )
    submission = J7LSuccessorSubmissionV1(
        case_id="j7l-dev-003",
        criterion_scores=criteria,
        evidence_references=("visible-evidence-1",),
        rationale="The visible evidence supports this assessment.",
    )

    encoded = subject._canonical_bytes(submission.model_dump(mode="json"))
    decoded = json.loads(encoded.decode("utf-8"))

    assert decoded["case_id"] == "j7l-dev-003"
    assert len(decoded["criterion_scores"]) == 7
    assert decoded["failure_labels"] == []
