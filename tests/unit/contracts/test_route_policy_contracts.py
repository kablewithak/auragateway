from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.provider import ProviderName
from auragateway.contracts.route import (
    CacheAffinityStatus,
    RouteReason,
    SessionRouteState,
    SessionRouteTransitionRequest,
)
from auragateway.contracts.route_policy import (
    ProviderResponseState,
    RouteEligibilitySnapshot,
    RoutePolicyDecision,
    RoutePolicyDecisionCode,
    RoutePolicyDecisionStatus,
    RoutePolicyEvaluationRequest,
)

_SESSION_HASH = "7d973d0fbe4c55f1401f480b498b6cc67b271f3fd4f92f43e9f149b0520d47ec"
_EVIDENCE_AT = datetime(2026, 7, 12, 16, 0, tzinfo=UTC)
_EVALUATED_AT = datetime(2026, 7, 12, 16, 2, tzinfo=UTC)


def _state() -> SessionRouteState:
    return SessionRouteState(
        session_id_hash=_SESSION_HASH,
        active_provider=ProviderName.GROQ,
        active_model="groq-gpt-oss-20b",
        last_cache_evidence_at=_EVIDENCE_AT,
        cache_affinity_status=CacheAffinityStatus.PLAUSIBLY_WARM,
        route_change_count=0,
        last_route_reason=RouteReason.WARM_CACHE_AFFINITY,
    )


def _eligibility(
    provider: ProviderName = ProviderName.GROQ,
    model_alias: str = "groq-gpt-oss-20b",
) -> RouteEligibilitySnapshot:
    return RouteEligibilitySnapshot(
        provider=provider,
        model_alias=model_alias,
        capability_eligible=True,
        safety_eligible=True,
        quality_eligible=True,
    )


def _transition() -> SessionRouteTransitionRequest:
    return SessionRouteTransitionRequest(
        previous_state=_state(),
        target_provider=ProviderName.OLLAMA,
        target_model="ollama-llama3.2-3b",
        target_cache_affinity_status=CacheAffinityStatus.UNKNOWN,
        reason=RouteReason.PROVIDER_FAILURE,
    )


def test_policy_request_rejects_mismatched_active_eligibility() -> None:
    with pytest.raises(ValidationError, match="active eligibility must match"):
        RoutePolicyEvaluationRequest(
            policy_id="gate5-route-policy-v1",
            policy_version="1.0.0",
            warm_ttl_seconds=300,
            evaluated_at=_EVALUATED_AT,
            proposed_transition=_transition(),
            active_route_eligibility=_eligibility(
                ProviderName.OLLAMA,
                "ollama-llama3.2-3b",
            ),
            target_route_eligibility=_eligibility(
                ProviderName.OLLAMA,
                "ollama-llama3.2-3b",
            ),
            provider_response_state=ProviderResponseState.DEFINITE_FAILURE,
            provider_error_code="PROVIDER_UNAVAILABLE",
        )


def test_policy_request_rejects_failure_state_without_error_code() -> None:
    with pytest.raises(ValidationError, match="require provider_error_code"):
        RoutePolicyEvaluationRequest(
            policy_id="gate5-route-policy-v1",
            policy_version="1.0.0",
            warm_ttl_seconds=300,
            evaluated_at=_EVALUATED_AT,
            proposed_transition=_transition(),
            active_route_eligibility=_eligibility(),
            target_route_eligibility=_eligibility(
                ProviderName.OLLAMA,
                "ollama-llama3.2-3b",
            ),
            provider_response_state=ProviderResponseState.DEFINITE_FAILURE,
        )


def test_policy_request_rejects_future_cache_evidence() -> None:
    transition = SessionRouteTransitionRequest(
        previous_state=_state(),
        target_provider=ProviderName.GROQ,
        target_model="groq-gpt-oss-20b",
        target_cache_affinity_status=CacheAffinityStatus.PLAUSIBLY_WARM,
        reason=RouteReason.WARM_CACHE_AFFINITY,
        cache_evidence_at=datetime(2026, 7, 12, 16, 3, tzinfo=UTC),
    )
    with pytest.raises(ValidationError, match="cannot be later"):
        RoutePolicyEvaluationRequest(
            policy_id="gate5-route-policy-v1",
            policy_version="1.0.0",
            warm_ttl_seconds=300,
            evaluated_at=_EVALUATED_AT,
            proposed_transition=transition,
            active_route_eligibility=_eligibility(),
            target_route_eligibility=_eligibility(),
        )


def test_policy_contracts_are_frozen_and_reject_extra_fields() -> None:
    eligibility = _eligibility()
    with pytest.raises(ValidationError, match="frozen"):
        cast(Any, eligibility).quality_eligible = False

    payload = eligibility.model_dump()
    payload["raw_provider_payload"] = "forbidden"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RouteEligibilitySnapshot.model_validate(payload)


def test_blocked_decision_cannot_contain_authorized_transition() -> None:
    with pytest.raises(ValidationError, match="must not authorize"):
        RoutePolicyDecision(
            policy_id="gate5-route-policy-v1",
            policy_version="1.0.0",
            evaluated_at=_EVALUATED_AT,
            status=RoutePolicyDecisionStatus.BLOCKED,
            decision_code=RoutePolicyDecisionCode.BLOCKED_AMBIGUOUS_RESPONSE,
            proposed_reason=RouteReason.PROVIDER_FAILURE,
            authorized_transition=_transition(),
        )
