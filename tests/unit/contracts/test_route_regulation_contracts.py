from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.provider import ProviderErrorCode, ProviderName
from auragateway.contracts.route import (
    CacheAffinityStatus,
    RouteReason,
    SessionRouteState,
    SessionRouteTransitionRequest,
)
from auragateway.contracts.route_policy import (
    RoutePolicyDecision,
    RoutePolicyDecisionCode,
    RoutePolicyDecisionStatus,
)
from auragateway.contracts.route_regulation import (
    AttemptOutcome,
    ProposedRetryAttempt,
    RegulationDecisionStatus,
    RetryAttemptRecord,
    RetryAuthorizationDecision,
    RetryAuthorizationRequest,
    RetryDecisionCode,
    RouteDecisionHistory,
    RouteDecisionHistoryEntry,
    RoutePolicyRegulationDecision,
    RouteRegulationCode,
)
from auragateway.routing.state import apply_session_route_transition

_SESSION_HASH = "7d973d0fbe4c55f1401f480b498b6cc67b271f3fd4f92f43e9f149b0520d47ec"
_REQUEST_HASH = "1f" * 32
_RECOVERY_HASH = "2f" * 32
_EVIDENCE_AT = datetime(2026, 7, 12, 16, 0, tzinfo=UTC)
_EVALUATED_AT = datetime(2026, 7, 12, 16, 1, tzinfo=UTC)


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


def _transition() -> SessionRouteTransitionRequest:
    return SessionRouteTransitionRequest(
        previous_state=_state(),
        target_provider=ProviderName.OLLAMA,
        target_model="ollama-llama3.2-3b",
        target_cache_affinity_status=CacheAffinityStatus.UNKNOWN,
        reason=RouteReason.PROVIDER_FAILURE,
    )


def _authorized_policy() -> RoutePolicyDecision:
    return RoutePolicyDecision(
        policy_id="gate5-route-policy-v1",
        policy_version="1.1.0",
        evaluated_at=_EVALUATED_AT,
        status=RoutePolicyDecisionStatus.AUTHORIZED,
        decision_code=RoutePolicyDecisionCode.AUTHORIZED_PROVIDER_FAILURE_REROUTE,
        proposed_reason=RouteReason.PROVIDER_FAILURE,
        authorized_transition=_transition(),
    )


def test_route_history_requires_authorized_policy_decision() -> None:
    blocked = RoutePolicyDecision(
        policy_id="gate5-route-policy-v1",
        policy_version="1.1.0",
        evaluated_at=_EVALUATED_AT,
        status=RoutePolicyDecisionStatus.BLOCKED,
        decision_code=RoutePolicyDecisionCode.BLOCKED_AMBIGUOUS_RESPONSE,
        proposed_reason=RouteReason.PROVIDER_FAILURE,
        authorized_transition=None,
    )
    with pytest.raises(ValidationError, match="authorized policy decision"):
        RouteDecisionHistoryEntry(
            sequence_index=1,
            policy_decision=blocked,
            transition_result=apply_session_route_transition(_transition()),
            applied_at=_EVALUATED_AT,
        )


def test_route_history_requires_contiguous_indexes() -> None:
    entry = RouteDecisionHistoryEntry(
        sequence_index=2,
        policy_decision=_authorized_policy(),
        transition_result=apply_session_route_transition(_transition()),
        applied_at=_EVALUATED_AT,
    )
    with pytest.raises(ValidationError, match="sequence indexes must be contiguous"):
        RouteDecisionHistory(session_id_hash=_SESSION_HASH, entries=(entry,))


def test_ambiguous_attempt_cannot_be_marked_retryable() -> None:
    with pytest.raises(ValidationError, match="cannot be marked retryable"):
        RetryAttemptRecord(
            attempt_index=1,
            logical_request_fingerprint=_REQUEST_HASH,
            provider=ProviderName.GROQ,
            model_alias="groq-gpt-oss-20b",
            outcome=AttemptOutcome.AMBIGUOUS,
            error_code=ProviderErrorCode.AMBIGUOUS_RESPONSE,
            retryable=True,
        )


def test_retry_attempt_after_first_requires_recovery_fingerprint() -> None:
    with pytest.raises(ValidationError, match="require a recovery action"):
        RetryAttemptRecord(
            attempt_index=2,
            logical_request_fingerprint=_REQUEST_HASH,
            provider=ProviderName.GROQ,
            model_alias="groq-gpt-oss-20b",
            outcome=AttemptOutcome.DEFINITE_FAILURE,
            error_code=ProviderErrorCode.TIMEOUT,
            retryable=True,
        )


def test_retry_request_requires_next_contiguous_attempt_index() -> None:
    first = RetryAttemptRecord(
        attempt_index=1,
        logical_request_fingerprint=_REQUEST_HASH,
        provider=ProviderName.GROQ,
        model_alias="groq-gpt-oss-20b",
        outcome=AttemptOutcome.DEFINITE_FAILURE,
        error_code=ProviderErrorCode.TIMEOUT,
        retryable=True,
    )
    with pytest.raises(ValidationError, match="must follow the retained history"):
        RetryAuthorizationRequest(
            policy_id="gate5-retry-policy-v1",
            policy_version="1.0.0",
            attempts=(first,),
            proposed_attempt=ProposedRetryAttempt(
                attempt_index=3,
                logical_request_fingerprint=_REQUEST_HASH,
                provider=ProviderName.GROQ,
                model_alias="groq-gpt-oss-20b",
                recovery_action_fingerprint=_RECOVERY_HASH,
            ),
        )


def test_regulation_contracts_are_frozen_and_reject_extra_fields() -> None:
    attempt = RetryAttemptRecord(
        attempt_index=1,
        logical_request_fingerprint=_REQUEST_HASH,
        provider=ProviderName.GROQ,
        model_alias="groq-gpt-oss-20b",
        outcome=AttemptOutcome.DEFINITE_FAILURE,
        error_code=ProviderErrorCode.TIMEOUT,
        retryable=True,
    )
    with pytest.raises(ValidationError, match="frozen"):
        cast(Any, attempt).retryable = False

    payload = attempt.model_dump()
    payload["raw_provider_payload"] = "forbidden"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RetryAttemptRecord.model_validate(payload)


def test_blocked_regulation_decisions_cannot_expose_executable_actions() -> None:
    with pytest.raises(ValidationError, match="must not expose"):
        RoutePolicyRegulationDecision(
            status=RegulationDecisionStatus.BLOCKED,
            decision_code=RouteRegulationCode.BLOCKED_ROUTE_THRASH,
            route_change_count_before=1,
            regulated_policy_decision=_authorized_policy(),
        )

    proposed = ProposedRetryAttempt(
        attempt_index=2,
        logical_request_fingerprint=_REQUEST_HASH,
        provider=ProviderName.GROQ,
        model_alias="groq-gpt-oss-20b",
        recovery_action_fingerprint=_RECOVERY_HASH,
    )
    with pytest.raises(ValidationError, match="must not expose"):
        RetryAuthorizationDecision(
            status=RegulationDecisionStatus.BLOCKED,
            decision_code=RetryDecisionCode.BLOCKED_RETRY_BUDGET_EXHAUSTED,
            retries_used=1,
            authorized_retry=proposed,
        )
