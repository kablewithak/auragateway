from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

import pytest

from auragateway.contracts.route_regulation import (
    Gate5RegulationFixtureSet,
    RegulationDecisionStatus,
    RetryDecisionCode,
    RetryRegulationFixtureCase,
    RouteRegulationCode,
    RouteRegulationFixtureCase,
)
from auragateway.routing.regulation import authorize_retry, regulate_route_policy

_FIXTURE_PATH = (
    Path(__file__).parents[3] / "data" / "provider_fixtures" / "routing" / "regulation_cases.json"
)


class ExpectedFixtureResult(TypedDict):
    case_id: str
    expected_status: str
    expected_code: str


def _fixture_set() -> Gate5RegulationFixtureSet:
    return Gate5RegulationFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "case",
    _fixture_set().route_cases,
    ids=lambda case: case.case_id,
)
def test_route_regulation_fixtures(case: RouteRegulationFixtureCase) -> None:
    decision = regulate_route_policy(case.request)
    assert decision.status is case.expected_status
    assert decision.decision_code is case.expected_code


@pytest.mark.parametrize(
    "case",
    _fixture_set().retry_cases,
    ids=lambda case: case.case_id,
)
def test_retry_regulation_fixtures(case: RetryRegulationFixtureCase) -> None:
    decision = authorize_retry(case.request)
    assert decision.status is case.expected_status
    assert decision.decision_code is case.expected_code


def test_fixture_json_is_canonical_typed_evidence() -> None:
    raw = cast(dict[str, object], json.loads(_FIXTURE_PATH.read_text(encoding="utf-8")))
    assert raw["fixture_set_id"] == "auragateway-gate5-route-regulation-v1"
    fixtures = _fixture_set()
    assert len(fixtures.route_cases) == 5
    assert len(fixtures.retry_cases) == 8


def test_second_route_change_is_blocked_as_thrash() -> None:
    case = next(
        case for case in _fixture_set().route_cases if case.case_id == "second-route-change-blocked"
    )
    decision = regulate_route_policy(case.request)
    assert decision.status is RegulationDecisionStatus.BLOCKED
    assert decision.decision_code is RouteRegulationCode.BLOCKED_ROUTE_THRASH
    assert decision.route_change_count_before == 1


def test_ambiguous_response_never_authorizes_duplicate_retry() -> None:
    case = next(
        case
        for case in _fixture_set().retry_cases
        if case.case_id == "ambiguous-response-retry-blocked"
    )
    decision = authorize_retry(case.request)
    assert decision.status is RegulationDecisionStatus.BLOCKED
    assert decision.decision_code is RetryDecisionCode.BLOCKED_AMBIGUOUS_DUPLICATE_RISK
    assert decision.authorized_retry is None


def test_valid_bounded_retry_exposes_only_metadata_safe_attempt() -> None:
    case = next(
        case for case in _fixture_set().retry_cases if case.case_id == "bounded-retry-authorized"
    )
    decision = authorize_retry(case.request)
    assert decision.status is RegulationDecisionStatus.AUTHORIZED
    assert decision.decision_code is RetryDecisionCode.AUTHORIZED_BOUNDED_RETRY
    assert decision.authorized_retry is not None
    serialized = decision.model_dump_json()
    assert "prompt" not in serialized
    assert "output" not in serialized
