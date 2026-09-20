from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LDevelopmentConstitutionV2,
    J7LReferenceAuditScheduleV1,
    J7LReferenceJudgmentV1,
    ReferenceAuthorityClass,
)


def _scores(value: int = 3) -> dict[RubricCriterion, int]:
    return {criterion: value for criterion in RubricCriterion}


def test_successor_is_model_reference_non_authorizing_and_r0() -> None:
    constitution = J7LDevelopmentConstitutionV2()

    assert constitution.reference_authority.authority_class == (
        ReferenceAuthorityClass.MODEL_DERIVED_REFERENCE.value
    )
    assert constitution.reference_authority.audit_may_rewrite_reference is False
    assert constitution.reference_authority.hybrid_adjudication_permitted is False
    assert constitution.reference_execution.planned_primary_reference_request_count == 48
    assert constitution.reference_execution.automatic_retry_permitted is False
    assert constitution.reference_execution.external_spend_ceiling == 0
    assert constitution.jev_experiment.planned_provider_request_count == 96
    assert constitution.jev_experiment.model_pin == "jev-1.13.0"
    assert constitution.jev_experiment.reference_visible_to_jev is False
    assert constitution.provider_binding_present_in_constitution is False
    assert constitution.next_gate == "FREEZE_J7L_REFERENCE_JUDGE_BINDING_V1"


def test_valid_reference_verdict_is_deterministic() -> None:
    reference = J7LReferenceJudgmentV1(
        case_id="j7l-dev-001",
        request_id_sha256="a" * 64,
        judge_binding_sha256="b" * 64,
        criterion_scores=_scores(3),
        evidence_references=("visible-evidence-1",),
        rationale="The visible evidence supports the declared scores and terminal outcome.",
        verdict=ReviewVerdict.PASS,
    )

    assert reference.verdict is ReviewVerdict.PASS


def test_reference_rejects_verdict_inconsistent_with_labels() -> None:
    with pytest.raises(ValidationError, match="frozen derivation rule"):
        J7LReferenceJudgmentV1(
            case_id="j7l-dev-001",
            request_id_sha256="a" * 64,
            judge_binding_sha256="b" * 64,
            criterion_scores=_scores(3),
            failure_labels=(EpisodeFailureLabel.UNSUPPORTED_CLAIM,),
            evidence_references=("visible-evidence-1",),
            rationale="A material unsupported claim is visible in the candidate response.",
            verdict=ReviewVerdict.PASS,
        )


def test_reference_requires_all_seven_criteria() -> None:
    payload: dict[str, Any] = J7LReferenceJudgmentV1(
        case_id="j7l-dev-001",
        request_id_sha256="a" * 64,
        judge_binding_sha256="b" * 64,
        criterion_scores=_scores(3),
        evidence_references=("visible-evidence-1",),
        rationale="The visible evidence supports the declared scores and terminal outcome.",
        verdict=ReviewVerdict.PASS,
    ).model_dump(mode="json")
    del payload["criterion_scores"][RubricCriterion.CLARITY.value]

    with pytest.raises(ValidationError, match="every rubric criterion"):
        J7LReferenceJudgmentV1.model_validate(payload)


def test_audit_schedule_requires_disjoint_samples() -> None:
    secondary = tuple(f"j7l-dev-{index:03d}" for index in range(25, 49))

    with pytest.raises(ValidationError, match="must be disjoint"):
        J7LReferenceAuditScheduleV1(
            schedule_id="auragateway-reference-audit-schedule-v1",
            audit_actor_id_sha256="c" * 64,
            resolution_owner_id_sha256="d" * 64,
            protected_secondary_case_ids=secondary,
            additional_spot_check_case_ids=("j7l-dev-025", "j7l-dev-001"),
        )
