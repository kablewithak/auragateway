"""Deterministic route-history and retry regulation for Gate 5."""

from __future__ import annotations

from auragateway.contracts.route import RouteReason
from auragateway.contracts.route_policy import RoutePolicyDecisionStatus
from auragateway.contracts.route_regulation import (
    AttemptOutcome,
    RegulationDecisionStatus,
    RetryAuthorizationDecision,
    RetryAuthorizationRequest,
    RetryDecisionCode,
    RoutePolicyRegulationDecision,
    RoutePolicyRegulationRequest,
    RouteRegulationCode,
)

_THRASH_EXEMPT_REASONS = {
    RouteReason.SESSION_RESET,
    RouteReason.BENCHMARK_CONTROL,
}


def regulate_route_policy(
    request: RoutePolicyRegulationRequest,
) -> RoutePolicyRegulationDecision:
    """Block route thrash after the single-decision policy has authorized a transition."""

    policy_decision = request.policy_decision
    route_changes = request.history.applied_route_change_count
    if policy_decision.status is RoutePolicyDecisionStatus.BLOCKED:
        return RoutePolicyRegulationDecision(
            status=RegulationDecisionStatus.BLOCKED,
            decision_code=RouteRegulationCode.BLOCKED_POLICY_DECISION,
            route_change_count_before=route_changes,
            regulated_policy_decision=None,
        )

    transition = policy_decision.authorized_transition
    if transition is None:
        raise ValueError("authorized policy decision is missing its transition")
    previous_binding = (
        transition.previous_state.active_provider,
        transition.previous_state.active_model,
    )
    target_binding = (transition.target_provider, transition.target_model)
    route_changes_now = previous_binding != target_binding
    if (
        route_changes_now
        and transition.reason not in _THRASH_EXEMPT_REASONS
        and route_changes >= request.max_route_changes_per_session
    ):
        return RoutePolicyRegulationDecision(
            status=RegulationDecisionStatus.BLOCKED,
            decision_code=RouteRegulationCode.BLOCKED_ROUTE_THRASH,
            route_change_count_before=route_changes,
            regulated_policy_decision=None,
        )

    return RoutePolicyRegulationDecision(
        status=RegulationDecisionStatus.AUTHORIZED,
        decision_code=RouteRegulationCode.AUTHORIZED_POLICY_DECISION,
        route_change_count_before=route_changes,
        regulated_policy_decision=policy_decision,
    )


def authorize_retry(request: RetryAuthorizationRequest) -> RetryAuthorizationDecision:
    """Authorize one bounded retry only after a definite, retryable provider failure."""

    last_attempt = request.attempts[-1]
    retries_used = len(request.attempts) - 1
    if last_attempt.outcome is AttemptOutcome.AMBIGUOUS:
        code = RetryDecisionCode.BLOCKED_AMBIGUOUS_DUPLICATE_RISK
    elif last_attempt.outcome is not AttemptOutcome.DEFINITE_FAILURE:
        code = RetryDecisionCode.BLOCKED_NO_DEFINITE_FAILURE
    elif not last_attempt.retryable:
        code = RetryDecisionCode.BLOCKED_NON_RETRYABLE_FAILURE
    elif retries_used >= request.max_retries:
        code = RetryDecisionCode.BLOCKED_RETRY_BUDGET_EXHAUSTED
    elif (
        request.proposed_attempt.logical_request_fingerprint
        != last_attempt.logical_request_fingerprint
    ):
        code = RetryDecisionCode.BLOCKED_RETRY_REQUEST_MISMATCH
    elif (
        request.proposed_attempt.provider,
        request.proposed_attempt.model_alias,
    ) != (last_attempt.provider, last_attempt.model_alias):
        code = RetryDecisionCode.BLOCKED_ROUTE_CHANGE_REQUIRES_POLICY
    else:
        used_recovery_actions = {
            attempt.recovery_action_fingerprint
            for attempt in request.attempts
            if attempt.recovery_action_fingerprint is not None
        }
        if request.proposed_attempt.recovery_action_fingerprint in used_recovery_actions:
            code = RetryDecisionCode.BLOCKED_INVALID_RETRY
        else:
            return RetryAuthorizationDecision(
                status=RegulationDecisionStatus.AUTHORIZED,
                decision_code=RetryDecisionCode.AUTHORIZED_BOUNDED_RETRY,
                retries_used=retries_used,
                authorized_retry=request.proposed_attempt,
            )

    return RetryAuthorizationDecision(
        status=RegulationDecisionStatus.BLOCKED,
        decision_code=code,
        retries_used=retries_used,
        authorized_retry=None,
    )
