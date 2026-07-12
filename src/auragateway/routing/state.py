"""Pure route-state initialization and transition functions."""

from __future__ import annotations

from auragateway.contracts.route import (
    CacheAffinityStatus,
    RouteReason,
    RouteTransitionKind,
    SessionRouteInitialization,
    SessionRouteState,
    SessionRouteTransitionRequest,
    SessionRouteTransitionResult,
)


def initialize_session_route(
    initialization: SessionRouteInitialization,
) -> SessionRouteTransitionResult:
    """Create a cold, metadata-only session route without fabricating cache evidence."""

    current_state = SessionRouteState(
        session_id_hash=initialization.session_id_hash,
        active_provider=initialization.active_provider,
        active_model=initialization.active_model,
        last_cache_evidence_at=None,
        cache_affinity_status=CacheAffinityStatus.COLD,
        route_change_count=0,
        last_route_reason=RouteReason.SESSION_START,
    )
    return SessionRouteTransitionResult(
        previous_state=None,
        current_state=current_state,
        transition_kind=RouteTransitionKind.INITIALIZED,
        route_changed=False,
        reason=RouteReason.SESSION_START,
    )


def apply_session_route_transition(
    request: SessionRouteTransitionRequest,
) -> SessionRouteTransitionResult:
    """Apply an already-authorized target state without deciding route policy."""

    previous_state = request.previous_state
    previous_binding = (previous_state.active_provider, previous_state.active_model)
    target_binding = (request.target_provider, request.target_model)
    route_changed = previous_binding != target_binding

    current_state = SessionRouteState(
        session_id_hash=previous_state.session_id_hash,
        active_provider=request.target_provider,
        active_model=request.target_model,
        last_cache_evidence_at=request.cache_evidence_at,
        cache_affinity_status=request.target_cache_affinity_status,
        route_change_count=previous_state.route_change_count + int(route_changed),
        last_route_reason=request.reason,
    )

    if request.reason is RouteReason.SESSION_RESET:
        transition_kind = RouteTransitionKind.RESET
    elif route_changed:
        transition_kind = RouteTransitionKind.CHANGED
    else:
        transition_kind = RouteTransitionKind.PRESERVED

    return SessionRouteTransitionResult(
        previous_state=previous_state,
        current_state=current_state,
        transition_kind=transition_kind,
        route_changed=route_changed,
        reason=request.reason,
    )
