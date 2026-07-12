"""Deterministic Gate 5 route-policy authorization engine."""

from __future__ import annotations

from auragateway.contracts.route import CacheAffinityStatus, RouteReason
from auragateway.contracts.route_policy import (
    ProviderResponseState,
    RoutePolicyDecision,
    RoutePolicyDecisionCode,
    RoutePolicyDecisionStatus,
    RoutePolicyEvaluationRequest,
)


def _authorized(
    request: RoutePolicyEvaluationRequest,
    code: RoutePolicyDecisionCode,
) -> RoutePolicyDecision:
    return RoutePolicyDecision(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
        evaluated_at=request.evaluated_at,
        status=RoutePolicyDecisionStatus.AUTHORIZED,
        decision_code=code,
        proposed_reason=request.proposed_transition.reason,
        authorized_transition=request.proposed_transition,
    )


def _blocked(
    request: RoutePolicyEvaluationRequest,
    code: RoutePolicyDecisionCode,
) -> RoutePolicyDecision:
    return RoutePolicyDecision(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
        evaluated_at=request.evaluated_at,
        status=RoutePolicyDecisionStatus.BLOCKED,
        decision_code=code,
        proposed_reason=request.proposed_transition.reason,
        authorized_transition=None,
    )


def _target_is_eligible(request: RoutePolicyEvaluationRequest) -> bool:
    target = request.target_route_eligibility
    return target is not None and target.fully_eligible


def _route_binding_changes(request: RoutePolicyEvaluationRequest) -> bool:
    previous = request.proposed_transition.previous_state
    return (previous.active_provider, previous.active_model) != (
        request.proposed_transition.target_provider,
        request.proposed_transition.target_model,
    )


def _cache_age_seconds(request: RoutePolicyEvaluationRequest) -> float | None:
    evidence_at = request.proposed_transition.cache_evidence_at
    if evidence_at is None:
        return None
    return (request.evaluated_at - evidence_at).total_seconds()


def _authorize_reroute(
    request: RoutePolicyEvaluationRequest,
    authorized_code: RoutePolicyDecisionCode,
) -> RoutePolicyDecision:
    transition = request.proposed_transition
    if not _route_binding_changes(request):
        return _blocked(request, RoutePolicyDecisionCode.BLOCKED_REASON_STATE_MISMATCH)
    if transition.target_cache_affinity_status is not CacheAffinityStatus.UNKNOWN:
        return _blocked(request, RoutePolicyDecisionCode.BLOCKED_REASON_STATE_MISMATCH)
    if transition.cache_evidence_at is not None:
        return _blocked(request, RoutePolicyDecisionCode.BLOCKED_REASON_STATE_MISMATCH)
    if not _target_is_eligible(request):
        return _blocked(request, RoutePolicyDecisionCode.BLOCKED_TARGET_ROUTE_INELIGIBLE)
    return _authorized(request, authorized_code)


def evaluate_route_policy(request: RoutePolicyEvaluationRequest) -> RoutePolicyDecision:
    """Authorize or block one explicit transition without choosing a route autonomously."""

    reason = request.proposed_transition.reason

    if reason is RouteReason.WARM_CACHE_AFFINITY:
        cache_age_seconds = _cache_age_seconds(request)
        if cache_age_seconds is None:
            return _blocked(request, RoutePolicyDecisionCode.BLOCKED_REASON_STATE_MISMATCH)
        if cache_age_seconds > request.warm_ttl_seconds:
            return _blocked(request, RoutePolicyDecisionCode.BLOCKED_TTL_EXPIRED)
        if not request.active_route_eligibility.fully_eligible:
            return _blocked(request, RoutePolicyDecisionCode.BLOCKED_REASON_STATE_MISMATCH)
        return _authorized(request, RoutePolicyDecisionCode.AUTHORIZED_WARM_PRESERVATION)

    if reason is RouteReason.TTL_EXPIRED:
        cache_age_seconds = _cache_age_seconds(request)
        if cache_age_seconds is None:
            return _blocked(request, RoutePolicyDecisionCode.BLOCKED_REASON_STATE_MISMATCH)
        if cache_age_seconds <= request.warm_ttl_seconds:
            return _blocked(request, RoutePolicyDecisionCode.BLOCKED_TTL_NOT_EXPIRED)
        if _route_binding_changes(request):
            return _blocked(request, RoutePolicyDecisionCode.BLOCKED_REASON_STATE_MISMATCH)
        return _authorized(request, RoutePolicyDecisionCode.AUTHORIZED_TTL_EXPIRY)

    if reason is RouteReason.PROVIDER_FAILURE:
        if request.provider_response_state is ProviderResponseState.AMBIGUOUS:
            return _blocked(request, RoutePolicyDecisionCode.BLOCKED_AMBIGUOUS_RESPONSE)
        if request.provider_response_state is not ProviderResponseState.DEFINITE_FAILURE:
            return _blocked(
                request,
                RoutePolicyDecisionCode.BLOCKED_PROVIDER_FAILURE_UNCONFIRMED,
            )
        return _authorize_reroute(
            request,
            RoutePolicyDecisionCode.AUTHORIZED_PROVIDER_FAILURE_REROUTE,
        )

    if reason is RouteReason.CAPABILITY_REQUIREMENT:
        if request.active_route_eligibility.capability_eligible:
            return _blocked(
                request,
                RoutePolicyDecisionCode.BLOCKED_ACTIVE_CAPABILITY_ELIGIBLE,
            )
        return _authorize_reroute(
            request,
            RoutePolicyDecisionCode.AUTHORIZED_CAPABILITY_REROUTE,
        )

    if reason is RouteReason.SAFETY_REQUIREMENT:
        if request.active_route_eligibility.safety_eligible:
            return _blocked(
                request,
                RoutePolicyDecisionCode.BLOCKED_ACTIVE_SAFETY_ELIGIBLE,
            )
        return _authorize_reroute(
            request,
            RoutePolicyDecisionCode.AUTHORIZED_SAFETY_REROUTE,
        )

    if reason is RouteReason.QUALITY_GUARDRAIL:
        if request.active_route_eligibility.quality_eligible:
            return _blocked(
                request,
                RoutePolicyDecisionCode.BLOCKED_ACTIVE_QUALITY_ELIGIBLE,
            )
        return _authorize_reroute(
            request,
            RoutePolicyDecisionCode.AUTHORIZED_QUALITY_REROUTE,
        )

    if reason is RouteReason.SESSION_RESET:
        return _authorized(request, RoutePolicyDecisionCode.AUTHORIZED_SESSION_RESET)

    if reason is RouteReason.BENCHMARK_CONTROL:
        return _authorize_reroute(
            request,
            RoutePolicyDecisionCode.AUTHORIZED_BENCHMARK_CONTROL,
        )

    return _blocked(request, RoutePolicyDecisionCode.BLOCKED_REASON_STATE_MISMATCH)
