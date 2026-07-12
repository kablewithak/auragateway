from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.provider import ProviderName
from auragateway.contracts.route import (
    CacheAffinityStatus,
    RouteReason,
    SessionRouteInitialization,
    SessionRouteState,
)

_FIXTURE_PATH = (
    Path(__file__).parents[3]
    / "data"
    / "provider_fixtures"
    / "routing"
    / "session_state_cases.json"
)


class ValidFixtureCase(TypedDict):
    case_id: str
    payload: dict[str, object]


class InvalidFixtureCase(ValidFixtureCase):
    expected_error_fragment: str


class RouteFixtureSet(TypedDict):
    schema_version: str
    fixture_set_id: str
    valid_cases: list[ValidFixtureCase]
    invalid_cases: list[InvalidFixtureCase]


def _fixture_set() -> RouteFixtureSet:
    return cast(RouteFixtureSet, json.loads(_FIXTURE_PATH.read_text(encoding="utf-8")))


@pytest.mark.parametrize("case", _fixture_set()["valid_cases"], ids=lambda case: case["case_id"])
def test_valid_session_route_state_fixtures(case: ValidFixtureCase) -> None:
    state = SessionRouteState.model_validate(case["payload"])
    assert state.session_id_hash == case["payload"]["session_id_hash"]


@pytest.mark.parametrize("case", _fixture_set()["invalid_cases"], ids=lambda case: case["case_id"])
def test_invalid_session_route_state_fixtures(case: InvalidFixtureCase) -> None:
    with pytest.raises(ValidationError, match=case["expected_error_fragment"]):
        SessionRouteState.model_validate(case["payload"])


def test_route_contracts_are_frozen_and_reject_extra_fields() -> None:
    initialization = SessionRouteInitialization(
        session_id_hash="7d973d0fbe4c55f1401f480b498b6cc67b271f3fd4f92f43e9f149b0520d47ec",
        active_provider=ProviderName.GROQ,
        active_model="groq-gpt-oss-20b",
    )
    with pytest.raises(ValidationError, match="frozen"):
        cast(Any, initialization).active_model = "other-model"

    payload = initialization.model_dump()
    payload["raw_session_id"] = "forbidden"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SessionRouteInitialization.model_validate(payload)


def test_route_reason_set_matches_gate_five_contract() -> None:
    assert set(RouteReason) == {
        RouteReason.SESSION_START,
        RouteReason.WARM_CACHE_AFFINITY,
        RouteReason.TTL_EXPIRED,
        RouteReason.PROVIDER_FAILURE,
        RouteReason.CAPABILITY_REQUIREMENT,
        RouteReason.SAFETY_REQUIREMENT,
        RouteReason.QUALITY_GUARDRAIL,
        RouteReason.SESSION_RESET,
        RouteReason.BENCHMARK_CONTROL,
    }
    assert set(CacheAffinityStatus) == {
        CacheAffinityStatus.COLD,
        CacheAffinityStatus.PLAUSIBLY_WARM,
        CacheAffinityStatus.EXPIRED,
        CacheAffinityStatus.UNKNOWN,
    }
