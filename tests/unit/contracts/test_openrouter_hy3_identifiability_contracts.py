from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.openrouter_hy3_identifiability import (
    OpenRouterHy3ClaimDecision,
    OpenRouterHy3ClaimKind,
    OpenRouterHy3ConditionId,
    OpenRouterHy3IdentifiabilityManifest,
    OpenRouterHy3IdentifiabilityReview,
)

_REVIEW_ROOT = Path("data/evals/benchmark/openrouter-hy3-identifiability-review-v1")


def _payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((_REVIEW_ROOT / "review.json").read_text(encoding="utf-8")),
    )


def test_review_loads_with_inactive_non_live_state() -> None:
    review = OpenRouterHy3IdentifiabilityReview.model_validate(_payload())

    assert review.adapter_implementation_permitted is True
    assert review.live_provider_call_authorized is False
    assert review.call_budget.live_calls_performed_by_review == 0
    assert review.telemetry_boundary.hy3_free_numeric_telemetry_observed is False
    assert review.identifiability.condition_c_effect_claim_permitted is False


def test_review_freezes_conditions_a_b_c_in_order() -> None:
    review = OpenRouterHy3IdentifiabilityReview.model_validate(_payload())

    assert tuple(item.condition_id for item in review.conditions) == (
        OpenRouterHy3ConditionId.CONDITION_A,
        OpenRouterHy3ConditionId.CONDITION_B,
        OpenRouterHy3ConditionId.CONDITION_C,
    )
    assert review.conditions[0].session_mode == "unique_per_request"
    assert review.conditions[1].prefix_mode == "deterministic_stable"
    assert review.conditions[2].session_mode == "stable_affinity_key"


def test_review_contains_all_claim_decisions() -> None:
    review = OpenRouterHy3IdentifiabilityReview.model_validate(_payload())
    decisions = {item.claim_kind: item.decision for item in review.claims}

    assert set(decisions) == set(OpenRouterHy3ClaimKind)
    assert (
        decisions[OpenRouterHy3ClaimKind.NORMALIZED_CACHE_SCHEMA_DOCUMENTED]
        is OpenRouterHy3ClaimDecision.PERMITTED
    )
    assert (
        decisions[OpenRouterHy3ClaimKind.HY3_FREE_NUMERIC_CACHE_TELEMETRY]
        is OpenRouterHy3ClaimDecision.BLOCKED
    )
    assert (
        decisions[OpenRouterHy3ClaimKind.BENCHMARK_ELIGIBILITY]
        is OpenRouterHy3ClaimDecision.BLOCKED
    )


def test_review_rejects_condition_c_without_stable_affinity() -> None:
    payload = _payload()
    conditions = payload["conditions"]
    assert isinstance(conditions, list)
    condition_c = conditions[2]
    assert isinstance(condition_c, dict)
    condition_c["session_mode"] = "unique_per_request"

    with pytest.raises(ValidationError, match="condition definition drifted"):
        OpenRouterHy3IdentifiabilityReview.model_validate(payload)


def test_review_rejects_live_authorization_promotion() -> None:
    payload = _payload()
    payload["live_provider_call_authorized"] = True

    with pytest.raises(ValidationError):
        OpenRouterHy3IdentifiabilityReview.model_validate(payload)


def test_review_rejects_unobserved_cache_claim_promotion() -> None:
    payload = _payload()
    claims = payload["claims"]
    assert isinstance(claims, list)
    for claim in claims:
        assert isinstance(claim, dict)
        if claim["claim_kind"] == "hy3_free_cache_use":
            claim["decision"] = "permitted"
            break

    with pytest.raises(ValidationError, match="claim decision exceeds"):
        OpenRouterHy3IdentifiabilityReview.model_validate(payload)


def test_review_preserves_missing_not_zero() -> None:
    review = OpenRouterHy3IdentifiabilityReview.model_validate(_payload())

    assert review.telemetry_boundary.hy3_free_numeric_telemetry_observed is False
    assert review.telemetry_boundary.hy3_free_cache_use_observed is False
    assert review.telemetry_boundary.missing_interpreted_as_zero is False


def test_review_requires_privacy_controls_before_live_use() -> None:
    review = OpenRouterHy3IdentifiabilityReview.model_validate(_payload())

    assert review.privacy_boundary.data_collection_deny_required is True
    assert review.privacy_boundary.zero_data_retention_required is True
    assert review.privacy_boundary.privacy_compatible_route_verified is False


def test_manifest_loads_and_blocks_provider_execution() -> None:
    manifest = OpenRouterHy3IdentifiabilityManifest.model_validate_json(
        (_REVIEW_ROOT / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest.provider_call_performed is False
    assert manifest.credential_accessed is False
    assert manifest.source_evidence_locked is True
