from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.benchmark.openrouter_hy3_probe_prompt import (
    derive_session_id,
    validate_stable_prefix,
)
from auragateway.contracts.openrouter_hy3_capability_probe_authorization import (
    OpenRouterProbeAuthorizationReview,
    OpenRouterProbePromptRecipe,
)

_ROOT = Path("data/evals/benchmark/openrouter-hy3-capability-probe-authorization-review-v1")


def _payload(name: str) -> object:
    return json.loads((_ROOT / name).read_text(encoding="utf-8"))


def test_review_remains_inactive_and_cannot_authorize_live_execution() -> None:
    review = OpenRouterProbeAuthorizationReview.model_validate(_payload("review.json"))
    assert review.live_provider_call_authorized is False
    assert review.credential_accessed is False
    assert review.network_request_performed is False
    assert review.activation_review_permitted is True
    assert review.runtime_policy.maximum_total_inference_attempts == 4
    assert review.runtime_policy.successful_response_retry_permitted is False
    assert review.promotion_policy.positive_cache_use_required is True
    assert review.formal_methods.tla_plus_model_checked is False


def test_prompt_recipe_reconciles_to_frozen_hash_and_byte_count() -> None:
    recipe = OpenRouterProbePromptRecipe.model_validate(_payload("prompt_recipe.json"))
    prefix = validate_stable_prefix(recipe)
    assert len(prefix.encode("utf-8")) == 53080
    assert derive_session_id(recipe).startswith("auragateway-hy3-probe-")
    assert prefix.count("SYNTHETIC-BLOCK-") == 768


def test_prompt_recipe_rejects_hash_drift() -> None:
    payload = _payload("prompt_recipe.json")
    assert isinstance(payload, dict)
    payload["generated_prefix_sha256"] = "0" * 64
    recipe = OpenRouterProbePromptRecipe.model_validate(payload)
    with pytest.raises(ValueError, match="frozen SHA-256"):
        validate_stable_prefix(recipe)


def test_review_rejects_duplicate_source_binding() -> None:
    payload = _payload("review.json")
    assert isinstance(payload, dict)
    bindings = payload["source_bindings"]
    assert isinstance(bindings, list)
    bindings[-1] = bindings[0]
    with pytest.raises(ValidationError, match="must be unique"):
        OpenRouterProbeAuthorizationReview.model_validate(payload)


def test_review_rejects_route_date_drift() -> None:
    payload = _payload("review.json")
    assert isinstance(payload, dict)
    route = payload["route_boundary"]
    assert isinstance(route, dict)
    route["scheduled_route_retirement_date"] = "2026-07-22"
    with pytest.raises(ValidationError, match="retirement date"):
        OpenRouterProbeAuthorizationReview.model_validate(payload)


def test_review_rejects_expanded_transient_statuses() -> None:
    payload = _payload("review.json")
    assert isinstance(payload, dict)
    policy = payload["runtime_policy"]
    assert isinstance(policy, dict)
    policy["transient_http_statuses"] = [429, 500, 502, 524, 529]
    with pytest.raises(ValidationError):
        OpenRouterProbeAuthorizationReview.model_validate(payload)
