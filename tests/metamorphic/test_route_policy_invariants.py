from __future__ import annotations

from datetime import UTC, datetime, timedelta

from auragateway.contracts.provider import ProviderName
from auragateway.contracts.route import (
    CacheAffinityStatus,
    RouteReason,
    SessionRouteState,
    SessionRouteTransitionRequest,
)
from auragateway.contracts.route_policy import (
    RouteEligibilitySnapshot,
    RoutePolicyDecisionCode,
    RoutePolicyEvaluationRequest,
)
from auragateway.routing.policy import evaluate_route_policy

_SESSION_HASH = "7d973d0fbe4c55f1401f480b498b6cc67b271f3fd4f92f43e9f149b0520d47ec"
_EVIDENCE_AT = datetime(2026, 7, 12, 16, 0, tzinfo=UTC)


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


def _eligibility(*, capability: bool = True) -> RouteEligibilitySnapshot:
    return RouteEligibilitySnapshot(
        provider=ProviderName.GROQ,
        model_alias="groq-gpt-oss-20b",
        capability_eligible=capability,
        safety_eligible=True,
        quality_eligible=True,
    )


def test_crossing_only_ttl_boundary_changes_warm_authorization() -> None:
    transition = SessionRouteTransitionRequest(
        previous_state=_state(),
        target_provider=ProviderName.GROQ,
        target_model="groq-gpt-oss-20b",
        target_cache_affinity_status=CacheAffinityStatus.PLAUSIBLY_WARM,
        reason=RouteReason.WARM_CACHE_AFFINITY,
        cache_evidence_at=_EVIDENCE_AT,
    )
    within_ttl = RoutePolicyEvaluationRequest(
        policy_id="gate5-route-policy-v1",
        policy_version="1.0.0",
        warm_ttl_seconds=300,
        evaluated_at=_EVIDENCE_AT + timedelta(seconds=300),
        proposed_transition=transition,
        active_route_eligibility=_eligibility(),
        target_route_eligibility=_eligibility(),
    )
    beyond_ttl = within_ttl.model_copy(
        update={"evaluated_at": _EVIDENCE_AT + timedelta(seconds=301)}
    )

    assert (
        evaluate_route_policy(within_ttl).decision_code
        is RoutePolicyDecisionCode.AUTHORIZED_WARM_PRESERVATION
    )
    assert (
        evaluate_route_policy(beyond_ttl).decision_code
        is RoutePolicyDecisionCode.BLOCKED_TTL_EXPIRED
    )


def test_changing_only_active_capability_changes_reroute_authorization() -> None:
    transition = SessionRouteTransitionRequest(
        previous_state=_state(),
        target_provider=ProviderName.OLLAMA,
        target_model="ollama-llama3.2-3b",
        target_cache_affinity_status=CacheAffinityStatus.UNKNOWN,
        reason=RouteReason.CAPABILITY_REQUIREMENT,
    )
    target = RouteEligibilitySnapshot(
        provider=ProviderName.OLLAMA,
        model_alias="ollama-llama3.2-3b",
        capability_eligible=True,
        safety_eligible=True,
        quality_eligible=True,
    )
    eligible_active = RoutePolicyEvaluationRequest(
        policy_id="gate5-route-policy-v1",
        policy_version="1.0.0",
        warm_ttl_seconds=300,
        evaluated_at=_EVIDENCE_AT + timedelta(seconds=60),
        proposed_transition=transition,
        active_route_eligibility=_eligibility(capability=True),
        target_route_eligibility=target,
    )
    ineligible_active = eligible_active.model_copy(
        update={"active_route_eligibility": _eligibility(capability=False)}
    )

    assert (
        evaluate_route_policy(eligible_active).decision_code
        is RoutePolicyDecisionCode.BLOCKED_ACTIVE_CAPABILITY_ELIGIBLE
    )
    assert (
        evaluate_route_policy(ineligible_active).decision_code
        is RoutePolicyDecisionCode.AUTHORIZED_CAPABILITY_REROUTE
    )
