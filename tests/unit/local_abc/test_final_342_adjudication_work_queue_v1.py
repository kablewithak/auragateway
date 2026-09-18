from __future__ import annotations

import json

from auragateway.contracts.blinded_quality import (
    CriterionScore,
    DisagreementReason,
    MaterialDisagreement,
    QualityReviewRecord,
    ReviewRole,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.local_abc import final_342_adjudication_work_queue_v1 as subject
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)


def _scores(value: int) -> tuple[CriterionScore, ...]:
    return tuple(
        CriterionScore(
            criterion=criterion,
            score=value,
            evidence_note_sha256="a" * 64,
        )
        for criterion in RubricCriterion
    )


def _review(
    *,
    review_id: str,
    role: ReviewRole,
    label: EpisodeFailureLabel,
) -> QualityReviewRecord:
    return QualityReviewRecord(
        review_id=review_id,
        episode_id="ep-func-001",
        reviewer_id_sha256=("b" * 64 if role is ReviewRole.PRIMARY else "c" * 64),
        role=role,
        criterion_scores=_scores(2),
        failure_labels=(label,),
        verdict=ReviewVerdict.FAIL,
        rationale_sha256="d" * 64,
    )


def _payload() -> review_successor.ReviewerPayload:
    turns = tuple(
        review_successor.ReviewerTurn(
            turn_index=index,
            user_message=f"user-{index}",
            assistant_output={"answer": f"assistant-{index}"},
            citation_source_ids=(),
        )
        for index in range(1, 5)
    )
    return review_successor.ReviewerPayload(
        assignment_id="review-" + ("1" * 24),
        review_item_id="2" * 64,
        episode_id="ep-func-001",
        turns=turns,
        terminal_structured_result={"decision": "answer"},
        frozen_source_evidence=({"source_id": "source-1"},),
        deterministic_validation_summary={"valid": True},
    )


def _case() -> subject.MaterialCase:
    primary = _review(
        review_id="review-" + ("1" * 24),
        role=ReviewRole.PRIMARY,
        label=EpisodeFailureLabel.STALE_SOURCE_SELECTED,
    )
    secondary = _review(
        review_id="review-" + ("3" * 24),
        role=ReviewRole.SECONDARY,
        label=EpisodeFailureLabel.UNSUPPORTED_CLAIM,
    )
    return subject.MaterialCase(
        payload=_payload(),
        primary=primary,
        secondary=secondary,
        disagreement=MaterialDisagreement(
            episode_id="ep-func-001",
            primary_review_id=primary.review_id,
            secondary_review_id=secondary.review_id,
            reasons=(DisagreementReason.FAILURE_LABEL_MISMATCH,),
            criterion_score_deltas={criterion: 0 for criterion in RubricCriterion},
        ),
    )


def test_submission_template_scores_all_seven_criteria() -> None:
    template = subject._submission_template("2" * 64)
    assert template.adjudicator_key is None
    assert len(template.criterion_scores) == 7
    assert {item.criterion for item in template.criterion_scores} == set(RubricCriterion)
    assert all(item.score is None for item in template.criterion_scores)
    assert template.failure_labels == ()
    assert template.rationale is None


def test_anonymized_review_pair_is_deterministic() -> None:
    case = _case()
    first = subject._anonymized_review_pair(
        case.payload.review_item_id,
        case.primary,
        case.secondary,
    )
    second = subject._anonymized_review_pair(
        case.payload.review_item_id,
        case.primary,
        case.secondary,
    )
    assert first == second
    assert {first[0].failure_labels, first[1].failure_labels} == {
        case.primary.failure_labels,
        case.secondary.failure_labels,
    }


def test_visible_evidence_strips_assignment_and_reviewer_identity() -> None:
    evidence = subject._visible_evidence(_payload())
    serialized = json.dumps(evidence.model_dump(mode="json"), sort_keys=True)
    assert "assignment_id" not in serialized
    assert "reviewer_id_sha256" not in serialized


def test_material_case_is_human_disagreement_shape() -> None:
    case = _case()
    assert DisagreementReason.FAILURE_LABEL_MISMATCH in case.disagreement.reasons
    assert case.primary.role is ReviewRole.PRIMARY
    assert case.secondary.role is ReviewRole.SECONDARY
