from __future__ import annotations

from pathlib import Path

from auragateway.contracts.route_regulation import (
    Gate5RegulationFixtureSet,
    RegulationDecisionStatus,
    RetryDecisionCode,
    RoutePolicyRegulationRequest,
    RouteRegulationCode,
)
from auragateway.routing.regulation import authorize_retry, regulate_route_policy

_FIXTURE_PATH = (
    Path(__file__).parents[2] / "data" / "provider_fixtures" / "routing" / "regulation_cases.json"
)


def _fixtures() -> Gate5RegulationFixtureSet:
    return Gate5RegulationFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_increasing_route_change_budget_changes_only_thrash_authorization() -> None:
    case = next(
        case for case in _fixtures().route_cases if case.case_id == "second-route-change-blocked"
    )
    blocked = regulate_route_policy(case.request)
    relaxed_request = RoutePolicyRegulationRequest(
        policy_decision=case.request.policy_decision,
        history=case.request.history,
        max_route_changes_per_session=2,
    )
    authorized = regulate_route_policy(relaxed_request)
    assert blocked.decision_code is RouteRegulationCode.BLOCKED_ROUTE_THRASH
    assert authorized.status is RegulationDecisionStatus.AUTHORIZED
    assert authorized.decision_code is RouteRegulationCode.AUTHORIZED_POLICY_DECISION


def test_new_recovery_action_changes_invalid_retry_to_authorized() -> None:
    case = next(
        case
        for case in _fixtures().retry_cases
        if case.case_id == "repeated-recovery-action-blocked"
    )
    blocked = authorize_retry(case.request)
    proposed = case.request.proposed_attempt.model_copy(
        update={"recovery_action_fingerprint": "9f" * 32}
    )
    authorized = authorize_retry(case.request.model_copy(update={"proposed_attempt": proposed}))
    assert blocked.decision_code is RetryDecisionCode.BLOCKED_INVALID_RETRY
    assert authorized.status is RegulationDecisionStatus.AUTHORIZED
    assert authorized.decision_code is RetryDecisionCode.AUTHORIZED_BOUNDED_RETRY


def test_ambiguous_response_remains_blocked_when_retry_budget_increases() -> None:
    case = next(
        case
        for case in _fixtures().retry_cases
        if case.case_id == "ambiguous-response-retry-blocked"
    )
    original = authorize_retry(case.request)
    expanded = authorize_retry(case.request.model_copy(update={"max_retries": 3}))
    assert original.decision_code is RetryDecisionCode.BLOCKED_AMBIGUOUS_DUPLICATE_RISK
    assert expanded.decision_code is RetryDecisionCode.BLOCKED_AMBIGUOUS_DUPLICATE_RISK
