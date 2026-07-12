from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from auragateway.contracts.provider import ProviderName
from auragateway.contracts.route import (
    CacheAffinityStatus,
    RouteReason,
    RouteTransitionKind,
    SessionRouteInitialization,
    SessionRouteTransitionRequest,
)
from auragateway.routing.state import apply_session_route_transition, initialize_session_route

_SESSION_HASH = "7d973d0fbe4c55f1401f480b498b6cc67b271f3fd4f92f43e9f149b0520d47ec"
_EVIDENCE_AT = datetime(2026, 7, 12, 16, 0, tzinfo=UTC)


def test_initialize_session_route_creates_cold_metadata_only_state() -> None:
    result = initialize_session_route(
        SessionRouteInitialization(
            session_id_hash=_SESSION_HASH,
            active_provider=ProviderName.GROQ,
            active_model="groq-gpt-oss-20b",
        )
    )
    assert result.previous_state is None
    assert result.transition_kind is RouteTransitionKind.INITIALIZED
    assert result.route_changed is False
    assert result.current_state.cache_affinity_status is CacheAffinityStatus.COLD
    assert result.current_state.last_cache_evidence_at is None
    assert result.current_state.route_change_count == 0
    assert result.current_state.last_route_reason is RouteReason.SESSION_START


def test_warm_affinity_preserves_binding_without_incrementing_count() -> None:
    initial = initialize_session_route(
        SessionRouteInitialization(
            session_id_hash=_SESSION_HASH,
            active_provider=ProviderName.GROQ,
            active_model="groq-gpt-oss-20b",
        )
    )
    result = apply_session_route_transition(
        SessionRouteTransitionRequest(
            previous_state=initial.current_state,
            target_provider=ProviderName.GROQ,
            target_model="groq-gpt-oss-20b",
            target_cache_affinity_status=CacheAffinityStatus.PLAUSIBLY_WARM,
            reason=RouteReason.WARM_CACHE_AFFINITY,
            cache_evidence_at=_EVIDENCE_AT,
        )
    )
    assert result.transition_kind is RouteTransitionKind.PRESERVED
    assert result.route_changed is False
    assert result.current_state.route_change_count == 0
    assert result.current_state.last_cache_evidence_at == _EVIDENCE_AT


def test_explicit_route_change_increments_count_once() -> None:
    initial = initialize_session_route(
        SessionRouteInitialization(
            session_id_hash=_SESSION_HASH,
            active_provider=ProviderName.GROQ,
            active_model="groq-gpt-oss-20b",
        )
    )
    result = apply_session_route_transition(
        SessionRouteTransitionRequest(
            previous_state=initial.current_state,
            target_provider=ProviderName.OLLAMA,
            target_model="ollama-llama3.2-3b",
            target_cache_affinity_status=CacheAffinityStatus.UNKNOWN,
            reason=RouteReason.PROVIDER_FAILURE,
        )
    )
    assert result.transition_kind is RouteTransitionKind.CHANGED
    assert result.route_changed is True
    assert result.current_state.route_change_count == 1
    assert result.current_state.active_provider is ProviderName.OLLAMA


def test_session_reset_clears_route_and_counts_binding_change() -> None:
    initial = initialize_session_route(
        SessionRouteInitialization(
            session_id_hash=_SESSION_HASH,
            active_provider=ProviderName.GROQ,
            active_model="groq-gpt-oss-20b",
        )
    )
    result = apply_session_route_transition(
        SessionRouteTransitionRequest(
            previous_state=initial.current_state,
            target_provider=None,
            target_model=None,
            target_cache_affinity_status=CacheAffinityStatus.COLD,
            reason=RouteReason.SESSION_RESET,
        )
    )
    assert result.transition_kind is RouteTransitionKind.RESET
    assert result.route_changed is True
    assert result.current_state.active_provider is None
    assert result.current_state.active_model is None
    assert result.current_state.route_change_count == 1


def test_warm_affinity_cannot_switch_provider_or_model() -> None:
    initial = initialize_session_route(
        SessionRouteInitialization(
            session_id_hash=_SESSION_HASH,
            active_provider=ProviderName.GROQ,
            active_model="groq-gpt-oss-20b",
        )
    )
    with pytest.raises(ValidationError, match="cannot change the active route"):
        SessionRouteTransitionRequest(
            previous_state=initial.current_state,
            target_provider=ProviderName.OLLAMA,
            target_model="ollama-llama3.2-3b",
            target_cache_affinity_status=CacheAffinityStatus.PLAUSIBLY_WARM,
            reason=RouteReason.WARM_CACHE_AFFINITY,
            cache_evidence_at=_EVIDENCE_AT,
        )


def test_ttl_expiry_requires_expired_state_and_evidence_time() -> None:
    initial = initialize_session_route(
        SessionRouteInitialization(
            session_id_hash=_SESSION_HASH,
            active_provider=ProviderName.GROQ,
            active_model="groq-gpt-oss-20b",
        )
    )
    with pytest.raises(ValidationError, match="expired target state"):
        SessionRouteTransitionRequest(
            previous_state=initial.current_state,
            target_provider=ProviderName.GROQ,
            target_model="groq-gpt-oss-20b",
            target_cache_affinity_status=CacheAffinityStatus.UNKNOWN,
            reason=RouteReason.TTL_EXPIRED,
            cache_evidence_at=_EVIDENCE_AT,
        )


def test_session_start_is_reserved_for_initialization() -> None:
    initial = initialize_session_route(
        SessionRouteInitialization(
            session_id_hash=_SESSION_HASH,
            active_provider=ProviderName.GROQ,
            active_model="groq-gpt-oss-20b",
        )
    )
    with pytest.raises(ValidationError, match="reserved for route initialization"):
        SessionRouteTransitionRequest(
            previous_state=initial.current_state,
            target_provider=ProviderName.GROQ,
            target_model="groq-gpt-oss-20b",
            target_cache_affinity_status=CacheAffinityStatus.COLD,
            reason=RouteReason.SESSION_START,
        )
