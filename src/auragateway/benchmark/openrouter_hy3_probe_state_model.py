"""Exhaustive local state model for the bounded OpenRouter Hy3 capability probe."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, replace
from enum import StrEnum


class ProbePhase(StrEnum):
    """Lifecycle phase of one authorization."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    TERMINAL = "terminal"


class ProbeEvent(StrEnum):
    """Abstract events relevant to call-budget and promotion safety."""

    ACTIVATE = "activate"
    TRANSIENT_FAILURE = "transient_failure"
    TERMINAL_FAILURE = "terminal_failure"
    SUCCESS_FIELDS_ABSENT = "success_fields_absent"
    SUCCESS_FIELDS_NULL = "success_fields_null"
    SUCCESS_ZERO = "success_zero"
    SUCCESS_POSITIVE_READ = "success_positive_read"
    SUCCESS_POSITIVE_WRITE = "success_positive_write"
    SUCCESS_ROUTE_INVALID = "success_route_invalid"
    SUCCESS_OBSERVATION_INVALID = "success_observation_invalid"
    CLOSE = "close"


class ProbeTerminalOutcome(StrEnum):
    """Terminal outcomes permitted by the bounded probe."""

    CLOSED_TRANSIENT_BUDGET_EXHAUSTED = "closed_transient_budget_exhausted"
    CLOSED_TERMINAL_PROVIDER_FAILURE = "closed_terminal_provider_failure"
    CLOSED_OBSERVATION_INVALID = "closed_observation_invalid"
    CLOSED_ROUTE_UNIDENTIFIABLE = "closed_route_unidentifiable"
    CLOSED_TELEMETRY_UNAVAILABLE = "closed_telemetry_unavailable"
    CLOSED_NO_CACHE_USE = "closed_no_cache_use"
    PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW = "promoted_to_pilot_authorization_review"


@dataclass(frozen=True, slots=True)
class ProbeState:
    """One reachable state in the capability-probe lifecycle."""

    phase: ProbePhase = ProbePhase.INACTIVE
    attempts: int = 0
    provider_successes: int = 0
    retained_successes: int = 0
    logical_call_index: int = 0
    transient_failures_current_call: int = 0
    numeric_telemetry_observed: bool = False
    positive_cache_use_observed: bool = False
    route_identity_valid: bool = True
    authorization_consumed: bool = False
    terminal_outcome: ProbeTerminalOutcome | None = None


@dataclass(frozen=True, slots=True)
class ProbeStateModelReport:
    """Deterministic summary of exhaustive state exploration."""

    reachable_state_count: int
    terminal_state_count: int
    maximum_attempts_observed: int
    maximum_provider_successes_observed: int
    maximum_retained_successes_observed: int
    terminal_outcome_counts: tuple[tuple[str, int], ...]
    invariants_checked: tuple[str, ...]
    invariant_violations: tuple[str, ...]


_INITIAL_STATE = ProbeState()
_SUCCESS_EVENTS = (
    ProbeEvent.SUCCESS_FIELDS_ABSENT,
    ProbeEvent.SUCCESS_FIELDS_NULL,
    ProbeEvent.SUCCESS_ZERO,
    ProbeEvent.SUCCESS_POSITIVE_READ,
    ProbeEvent.SUCCESS_POSITIVE_WRITE,
    ProbeEvent.SUCCESS_ROUTE_INVALID,
    ProbeEvent.SUCCESS_OBSERVATION_INVALID,
)
_INVARIANTS = (
    "attempt_budget_never_exceeds_four",
    "provider_success_budget_never_exceeds_two",
    "retained_success_budget_never_exceeds_two",
    "retained_successes_never_exceed_provider_successes",
    "logical_call_index_matches_retained_successes",
    "one_transient_replacement_per_logical_call",
    "terminal_state_consumes_authorization",
    "active_state_never_consumes_authorization",
    "promotion_requires_two_retained_successes",
    "promotion_requires_numeric_telemetry",
    "promotion_requires_positive_cache_use",
    "promotion_requires_valid_route_identity",
    "terminal_states_have_no_enabled_events",
)


def enabled_events(state: ProbeState) -> tuple[ProbeEvent, ...]:
    """Return all abstract events enabled from one state."""

    if state.phase is ProbePhase.INACTIVE:
        return (ProbeEvent.ACTIVATE,)
    if state.phase is ProbePhase.TERMINAL:
        return ()
    if state.retained_successes == 2:
        return (ProbeEvent.CLOSE,)
    if state.attempts >= 4 or state.provider_successes >= 2:
        return (ProbeEvent.CLOSE,)
    return (
        ProbeEvent.TRANSIENT_FAILURE,
        ProbeEvent.TERMINAL_FAILURE,
        *_SUCCESS_EVENTS,
    )


def _terminal(
    state: ProbeState,
    outcome: ProbeTerminalOutcome,
    *,
    attempts: int | None = None,
    provider_successes: int | None = None,
) -> ProbeState:
    return replace(
        state,
        phase=ProbePhase.TERMINAL,
        attempts=state.attempts if attempts is None else attempts,
        provider_successes=(
            state.provider_successes if provider_successes is None else provider_successes
        ),
        authorization_consumed=True,
        terminal_outcome=outcome,
    )


def transition(state: ProbeState, event: ProbeEvent) -> ProbeState:
    """Apply one enabled abstract event."""

    if event not in enabled_events(state):
        raise ValueError(f"event {event.value} is not enabled from {state.phase.value}")
    if event is ProbeEvent.ACTIVATE:
        return replace(state, phase=ProbePhase.ACTIVE)
    if event is ProbeEvent.TRANSIENT_FAILURE:
        next_attempts = state.attempts + 1
        if state.transient_failures_current_call == 0 and next_attempts < 4:
            return replace(
                state,
                attempts=next_attempts,
                transient_failures_current_call=1,
            )
        return _terminal(
            state,
            ProbeTerminalOutcome.CLOSED_TRANSIENT_BUDGET_EXHAUSTED,
            attempts=next_attempts,
        )
    if event is ProbeEvent.TERMINAL_FAILURE:
        return _terminal(
            state,
            ProbeTerminalOutcome.CLOSED_TERMINAL_PROVIDER_FAILURE,
            attempts=state.attempts + 1,
        )
    if event is ProbeEvent.SUCCESS_OBSERVATION_INVALID:
        return _terminal(
            state,
            ProbeTerminalOutcome.CLOSED_OBSERVATION_INVALID,
            attempts=state.attempts + 1,
            provider_successes=state.provider_successes + 1,
        )
    if event in _SUCCESS_EVENTS:
        numeric = event in {
            ProbeEvent.SUCCESS_ZERO,
            ProbeEvent.SUCCESS_POSITIVE_READ,
            ProbeEvent.SUCCESS_POSITIVE_WRITE,
            ProbeEvent.SUCCESS_ROUTE_INVALID,
        }
        positive = event in {
            ProbeEvent.SUCCESS_POSITIVE_READ,
            ProbeEvent.SUCCESS_POSITIVE_WRITE,
            ProbeEvent.SUCCESS_ROUTE_INVALID,
        }
        return replace(
            state,
            attempts=state.attempts + 1,
            provider_successes=state.provider_successes + 1,
            retained_successes=state.retained_successes + 1,
            logical_call_index=state.logical_call_index + 1,
            transient_failures_current_call=0,
            numeric_telemetry_observed=state.numeric_telemetry_observed or numeric,
            positive_cache_use_observed=state.positive_cache_use_observed or positive,
            route_identity_valid=(
                state.route_identity_valid and event is not ProbeEvent.SUCCESS_ROUTE_INVALID
            ),
        )
    if not state.route_identity_valid:
        outcome = ProbeTerminalOutcome.CLOSED_ROUTE_UNIDENTIFIABLE
    elif not state.numeric_telemetry_observed:
        outcome = ProbeTerminalOutcome.CLOSED_TELEMETRY_UNAVAILABLE
    elif not state.positive_cache_use_observed:
        outcome = ProbeTerminalOutcome.CLOSED_NO_CACHE_USE
    else:
        outcome = ProbeTerminalOutcome.PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW
    return _terminal(state, outcome)


def _invariant_violations(state: ProbeState) -> tuple[str, ...]:
    violations: list[str] = []
    if not 0 <= state.attempts <= 4:
        violations.append("attempt_budget_never_exceeds_four")
    if not 0 <= state.provider_successes <= 2:
        violations.append("provider_success_budget_never_exceeds_two")
    if not 0 <= state.retained_successes <= 2:
        violations.append("retained_success_budget_never_exceeds_two")
    if state.retained_successes > state.provider_successes:
        violations.append("retained_successes_never_exceed_provider_successes")
    if state.logical_call_index != state.retained_successes:
        violations.append("logical_call_index_matches_retained_successes")
    if state.transient_failures_current_call not in (0, 1):
        violations.append("one_transient_replacement_per_logical_call")
    if state.phase is ProbePhase.TERMINAL:
        if not state.authorization_consumed or state.terminal_outcome is None:
            violations.append("terminal_state_consumes_authorization")
        if enabled_events(state):
            violations.append("terminal_states_have_no_enabled_events")
    else:
        if state.authorization_consumed or state.terminal_outcome is not None:
            violations.append("active_state_never_consumes_authorization")
    if state.terminal_outcome is ProbeTerminalOutcome.PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW:
        if state.retained_successes != 2:
            violations.append("promotion_requires_two_retained_successes")
        if not state.numeric_telemetry_observed:
            violations.append("promotion_requires_numeric_telemetry")
        if not state.positive_cache_use_observed:
            violations.append("promotion_requires_positive_cache_use")
        if not state.route_identity_valid:
            violations.append("promotion_requires_valid_route_identity")
    return tuple(violations)


def explore_state_space() -> ProbeStateModelReport:
    """Explore every reachable state and return invariant results."""

    queue: deque[ProbeState] = deque([_INITIAL_STATE])
    visited: set[ProbeState] = {_INITIAL_STATE}
    violations: list[str] = []
    while queue:
        state = queue.popleft()
        violations.extend(_invariant_violations(state))
        for event in enabled_events(state):
            next_state = transition(state, event)
            if next_state not in visited:
                visited.add(next_state)
                queue.append(next_state)
    terminal_states = tuple(state for state in visited if state.phase is ProbePhase.TERMINAL)
    outcome_counts = Counter(
        state.terminal_outcome.value
        for state in terminal_states
        if state.terminal_outcome is not None
    )
    return ProbeStateModelReport(
        reachable_state_count=len(visited),
        terminal_state_count=len(terminal_states),
        maximum_attempts_observed=max(state.attempts for state in visited),
        maximum_provider_successes_observed=max(state.provider_successes for state in visited),
        maximum_retained_successes_observed=max(state.retained_successes for state in visited),
        terminal_outcome_counts=tuple(sorted(outcome_counts.items())),
        invariants_checked=_INVARIANTS,
        invariant_violations=tuple(sorted(set(violations))),
    )


__all__ = [
    "ProbeEvent",
    "ProbePhase",
    "ProbeState",
    "ProbeStateModelReport",
    "ProbeTerminalOutcome",
    "enabled_events",
    "explore_state_space",
    "transition",
]
