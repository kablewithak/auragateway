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
from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_v1 as canary,
)
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)


def _scores(value: int) -> tuple[CriterionScore, ...]:
    return tuple(
        CriterionScore(
            criterion=criterion,
            score=value,
            evidence_note_sha256="1" * 64,
        )
        for criterion in RubricCriterion
    )


def _review(
    *,
    review_id: str,
    role: ReviewRole,
    reviewer_sha: str,
    labels: tuple[EpisodeFailureLabel, ...],
) -> QualityReviewRecord:
    return QualityReviewRecord(
        review_id=review_id,
        episode_id="ep-func-001",
        reviewer_id_sha256=reviewer_sha,
        role=role,
        criterion_scores=_scores(3),
        failure_labels=labels,
        verdict=ReviewVerdict.FAIL,
        rationale_sha256="2" * 64,
    )


def _payload() -> review_successor.ReviewerPayload:
    return review_successor.ReviewerPayload(
        assignment_id="review-" + ("a" * 24),
        review_item_id="b" * 64,
        episode_id="ep-func-001",
        turns=(
            review_successor.ReviewerTurn(
                turn_index=1,
                user_message="Synthetic visible turn one.",
                assistant_output={"decision": "answer"},
                citation_source_ids=("source-current",),
            ),
            review_successor.ReviewerTurn(
                turn_index=2,
                user_message="Synthetic visible turn two.",
                assistant_output={"decision": "answer"},
                citation_source_ids=("source-current",),
            ),
            review_successor.ReviewerTurn(
                turn_index=3,
                user_message="Synthetic visible turn three.",
                assistant_output={"decision": "answer"},
                citation_source_ids=("source-current",),
            ),
            review_successor.ReviewerTurn(
                turn_index=4,
                user_message="Synthetic visible turn four.",
                assistant_output={"decision": "answer"},
                citation_source_ids=("source-current",),
            ),
        ),
        terminal_structured_result={"decision": "answer"},
        frozen_source_evidence=(
            {
                "source_id": "source-current",
                "text": "Visible frozen source evidence.",
            },
        ),
        deterministic_validation_summary={"structured_output_valid": True},
    )


def _disagreement(
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
) -> MaterialDisagreement:
    return MaterialDisagreement(
        episode_id="ep-func-001",
        primary_review_id=primary.review_id,
        secondary_review_id=secondary.review_id,
        reasons=(DisagreementReason.FAILURE_LABEL_MISMATCH,),
        criterion_score_deltas={criterion: 0 for criterion in RubricCriterion},
    )


def test_canary_packet_is_identity_free_and_provider_safe() -> None:
    primary = _review(
        review_id="review-" + ("a" * 24),
        role=ReviewRole.PRIMARY,
        reviewer_sha="3" * 64,
        labels=(EpisodeFailureLabel.STALE_SOURCE_SELECTED,),
    )
    secondary = _review(
        review_id="review-" + ("c" * 24),
        role=ReviewRole.SECONDARY,
        reviewer_sha="4" * 64,
        labels=(EpisodeFailureLabel.UNSUPPORTED_CLAIM,),
    )

    packet = canary.build_canary_packet(
        _payload(),
        primary,
        secondary,
        _disagreement(primary, secondary),
    )

    payload = packet.model_dump(mode="json")
    serialized = json.dumps(payload, sort_keys=True)

    assert "reviewer_id_sha256" not in serialized
    assert primary.review_id not in serialized
    assert secondary.review_id not in serialized
    assert "rationale_sha256" not in serialized
    assert packet.review_a.verdict is ReviewVerdict.FAIL
    assert packet.review_b.verdict is ReviewVerdict.FAIL

    safe = jev_contract.ReviewerSafeJevState(payload=payload)
    assert safe.payload["review_item_id"] == "b" * 64


def test_anonymized_review_order_is_deterministic() -> None:
    primary = _review(
        review_id="review-" + ("a" * 24),
        role=ReviewRole.PRIMARY,
        reviewer_sha="3" * 64,
        labels=(EpisodeFailureLabel.STALE_SOURCE_SELECTED,),
    )
    secondary = _review(
        review_id="review-" + ("c" * 24),
        role=ReviewRole.SECONDARY,
        reviewer_sha="4" * 64,
        labels=(EpisodeFailureLabel.UNSUPPORTED_CLAIM,),
    )

    first = canary._anonymized_review_pair(
        "b" * 64,
        primary,
        secondary,
    )
    second = canary._anonymized_review_pair(
        "b" * 64,
        primary,
        secondary,
    )

    assert first == second
    assert {
        first[0].failure_labels,
        first[1].failure_labels,
    } == {
        (EpisodeFailureLabel.STALE_SOURCE_SELECTED,),
        (EpisodeFailureLabel.UNSUPPORTED_CLAIM,),
    }


def test_canary_packet_preserves_disagreement_reason() -> None:
    primary = _review(
        review_id="review-" + ("a" * 24),
        role=ReviewRole.PRIMARY,
        reviewer_sha="3" * 64,
        labels=(EpisodeFailureLabel.STALE_SOURCE_SELECTED,),
    )
    secondary = _review(
        review_id="review-" + ("c" * 24),
        role=ReviewRole.SECONDARY,
        reviewer_sha="4" * 64,
        labels=(EpisodeFailureLabel.UNSUPPORTED_CLAIM,),
    )

    packet = canary.build_canary_packet(
        _payload(),
        primary,
        secondary,
        _disagreement(primary, secondary),
    )

    assert packet.disagreement_reasons == (DisagreementReason.FAILURE_LABEL_MISMATCH,)
    assert set(packet.criterion_score_deltas) == set(RubricCriterion)
