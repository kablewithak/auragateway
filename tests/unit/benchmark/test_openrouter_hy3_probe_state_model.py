from __future__ import annotations

from auragateway.benchmark.openrouter_hy3_probe_state_model import (
    ProbeEvent,
    ProbePhase,
    ProbeState,
    ProbeTerminalOutcome,
    enabled_events,
    explore_state_space,
    transition,
)


def _activate() -> ProbeState:
    return transition(ProbeState(), ProbeEvent.ACTIVATE)


def test_exhaustive_state_model_has_no_invariant_violations() -> None:
    report = explore_state_space()
    assert report.reachable_state_count == 88
    assert report.terminal_state_count == 57
    assert report.maximum_attempts_observed == 4
    assert report.maximum_provider_successes_observed == 2
    assert report.maximum_retained_successes_observed == 2
    assert report.invariant_violations == ()


def test_one_transient_replacement_is_allowed_per_logical_call() -> None:
    state = transition(_activate(), ProbeEvent.TRANSIENT_FAILURE)
    assert state.attempts == 1
    assert state.transient_failures_current_call == 1

    state = transition(state, ProbeEvent.SUCCESS_ZERO)
    assert state.attempts == 2
    assert state.retained_successes == 1
    assert state.transient_failures_current_call == 0


def test_second_transient_failure_closes_and_consumes_authorization() -> None:
    state = transition(_activate(), ProbeEvent.TRANSIENT_FAILURE)
    state = transition(state, ProbeEvent.TRANSIENT_FAILURE)
    assert state.phase is ProbePhase.TERMINAL
    assert state.authorization_consumed is True
    assert state.terminal_outcome is ProbeTerminalOutcome.CLOSED_TRANSIENT_BUDGET_EXHAUSTED
    assert enabled_events(state) == ()


def test_absent_telemetry_closes_without_promotion() -> None:
    state = transition(_activate(), ProbeEvent.SUCCESS_FIELDS_ABSENT)
    state = transition(state, ProbeEvent.SUCCESS_FIELDS_ABSENT)
    state = transition(state, ProbeEvent.CLOSE)
    assert state.terminal_outcome is ProbeTerminalOutcome.CLOSED_TELEMETRY_UNAVAILABLE


def test_numeric_zero_closes_without_cache_use_claim() -> None:
    state = transition(_activate(), ProbeEvent.SUCCESS_ZERO)
    state = transition(state, ProbeEvent.SUCCESS_ZERO)
    state = transition(state, ProbeEvent.CLOSE)
    assert state.terminal_outcome is ProbeTerminalOutcome.CLOSED_NO_CACHE_USE


def test_positive_cache_use_promotes_only_after_two_retained_successes() -> None:
    state = transition(_activate(), ProbeEvent.SUCCESS_POSITIVE_WRITE)
    state = transition(state, ProbeEvent.SUCCESS_POSITIVE_READ)
    state = transition(state, ProbeEvent.CLOSE)
    assert state.terminal_outcome is ProbeTerminalOutcome.PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW
    assert state.retained_successes == 2
    assert state.route_identity_valid is True


def test_route_failure_blocks_promotion_even_with_positive_cache_use() -> None:
    state = transition(_activate(), ProbeEvent.SUCCESS_POSITIVE_WRITE)
    state = transition(state, ProbeEvent.SUCCESS_ROUTE_INVALID)
    state = transition(state, ProbeEvent.CLOSE)
    assert state.terminal_outcome is ProbeTerminalOutcome.CLOSED_ROUTE_UNIDENTIFIABLE


def test_post_success_observation_failure_is_never_retried() -> None:
    state = transition(_activate(), ProbeEvent.SUCCESS_OBSERVATION_INVALID)
    assert state.phase is ProbePhase.TERMINAL
    assert state.provider_successes == 1
    assert state.retained_successes == 0
    assert state.terminal_outcome is ProbeTerminalOutcome.CLOSED_OBSERVATION_INVALID
    assert enabled_events(state) == ()
