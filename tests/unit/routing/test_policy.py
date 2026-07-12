from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

import pytest

from auragateway.contracts.provider import ProviderName
from auragateway.contracts.route import (
    CacheAffinityStatus,
    RouteReason,
    SessionRouteState,
    SessionRouteTransitionRequest,
)
from auragateway.contracts.route_policy import (
    RouteEligibilitySnapshot,
    RoutePolicyDecisionCode,
    RoutePolicyDecisionStatus,
    RoutePolicyEvaluationRequest,
)
from auragateway.routing.policy import evaluate_route_policy
from auragateway.routing.state import apply_session_route_transition

_FIXTURE_PATH = (
    Path(__file__).parents[3] / "data" / "provider_fixtures" / "routing" / "route_policy_cases.json"
)
_SESSION_HASH = "7d973d0fbe4c55f1401f480b498b6cc67b271f3fd4f92f43e9f149b0520d47ec"
_EVIDENCE_AT = datetime(2026, 7, 12, 16, 0, tzinfo=UTC)
_EVALUATED_AT = datetime(2026, 7, 12, 16, 2, tzinfo=UTC)


class PolicyFixtureCase(TypedDict):
    case_id: str
    request: dict[str, object]
    expected_status: str
    expected_code: str


class PolicyFixtureSet(TypedDict):
    schema_version: str
    fixture_set_id: str
    cases: list[PolicyFixtureCase]


def _fixture_set() -> PolicyFixtureSet:
    return cast(PolicyFixtureSet, json.loads(_FIXTURE_PATH.read_text(encoding="utf-8")))


def _warm_state() -> SessionRouteState:
    return SessionRouteState(
        session_id_hash=_SESSION_HASH,
        active_provider=ProviderName.GROQ,
        active_model="groq-gpt-oss-20b",
        last_cache_evidence_at=_EVIDENCE_AT,
        cache_affinity_status=CacheAffinityStatus.PLAUSIBLY_WARM,
        route_change_count=0,
        last_route_reason=RouteReason.WARM_CACHE_AFFINITY,
    )


def _eligibility(
    provider: ProviderName,
    model_alias: str,
    *,
    capability: bool = True,
    safety: bool = True,
    quality: bool = True,
) -> RouteEligibilitySnapshot:
    return RouteEligibilitySnapshot(
        provider=provider,
        model_alias=model_alias,
        capability_eligible=capability,
        safety_eligible=safety,
        quality_eligible=quality,
    )


@pytest.mark.parametrize("case", _fixture_set()["cases"], ids=lambda case: case["case_id"])
def test_route_policy_fixtures(case: PolicyFixtureCase) -> None:
    request = RoutePolicyEvaluationRequest.model_validate(case["request"])
    decision = evaluate_route_policy(request)
    assert decision.status.value == case["expected_status"]
    assert decision.decision_code.value == case["expected_code"]


def test_authorized_provider_failure_decision_applies_existing_state_transition() -> None:
    case = next(
        item
        for item in _fixture_set()["cases"]
        if item["case_id"] == "provider-definite-failure-reroute-authorized"
    )
    request = RoutePolicyEvaluationRequest.model_validate(case["request"])
    decision = evaluate_route_policy(request)
    assert decision.authorized_transition is not None

    result = apply_session_route_transition(decision.authorized_transition)
    assert result.route_changed is True
    assert result.current_state.active_provider is ProviderName.OLLAMA
    assert result.current_state.route_change_count == 1
    assert result.current_state.cache_affinity_status is CacheAffinityStatus.UNKNOWN


@pytest.mark.parametrize(
    ("reason", "active", "authorized_code"),
    [
        (
            RouteReason.SAFETY_REQUIREMENT,
            _eligibility(
                ProviderName.GROQ,
                "groq-gpt-oss-20b",
                safety=False,
            ),
            RoutePolicyDecisionCode.AUTHORIZED_SAFETY_REROUTE,
        ),
        (
            RouteReason.QUALITY_GUARDRAIL,
            _eligibility(
                ProviderName.GROQ,
                "groq-gpt-oss-20b",
                quality=False,
            ),
            RoutePolicyDecisionCode.AUTHORIZED_QUALITY_REROUTE,
        ),
    ],
)
def test_hard_guardrail_failure_authorizes_eligible_reroute(
    reason: RouteReason,
    active: RouteEligibilitySnapshot,
    authorized_code: RoutePolicyDecisionCode,
) -> None:
    transition = SessionRouteTransitionRequest(
        previous_state=_warm_state(),
        target_provider=ProviderName.OLLAMA,
        target_model="ollama-llama3.2-3b",
        target_cache_affinity_status=CacheAffinityStatus.UNKNOWN,
        reason=reason,
    )
    request = RoutePolicyEvaluationRequest(
        policy_id="gate5-route-policy-v1",
        policy_version="1.0.0",
        warm_ttl_seconds=300,
        evaluated_at=_EVALUATED_AT,
        proposed_transition=transition,
        active_route_eligibility=active,
        target_route_eligibility=_eligibility(
            ProviderName.OLLAMA,
            "ollama-llama3.2-3b",
        ),
    )
    decision = evaluate_route_policy(request)
    assert decision.status is RoutePolicyDecisionStatus.AUTHORIZED
    assert decision.decision_code is authorized_code


def test_ineligible_target_blocks_guardrail_reroute() -> None:
    transition = SessionRouteTransitionRequest(
        previous_state=_warm_state(),
        target_provider=ProviderName.OLLAMA,
        target_model="ollama-llama3.2-3b",
        target_cache_affinity_status=CacheAffinityStatus.UNKNOWN,
        reason=RouteReason.SAFETY_REQUIREMENT,
    )
    request = RoutePolicyEvaluationRequest(
        policy_id="gate5-route-policy-v1",
        policy_version="1.0.0",
        warm_ttl_seconds=300,
        evaluated_at=_EVALUATED_AT,
        proposed_transition=transition,
        active_route_eligibility=_eligibility(
            ProviderName.GROQ,
            "groq-gpt-oss-20b",
            safety=False,
        ),
        target_route_eligibility=_eligibility(
            ProviderName.OLLAMA,
            "ollama-llama3.2-3b",
            quality=False,
        ),
    )
    decision = evaluate_route_policy(request)
    assert decision.status is RoutePolicyDecisionStatus.BLOCKED
    assert decision.decision_code is RoutePolicyDecisionCode.BLOCKED_TARGET_ROUTE_INELIGIBLE


def test_session_reset_is_authorized_without_target_eligibility() -> None:
    transition = SessionRouteTransitionRequest(
        previous_state=_warm_state(),
        target_provider=None,
        target_model=None,
        target_cache_affinity_status=CacheAffinityStatus.COLD,
        reason=RouteReason.SESSION_RESET,
    )
    request = RoutePolicyEvaluationRequest(
        policy_id="gate5-route-policy-v1",
        policy_version="1.0.0",
        warm_ttl_seconds=300,
        evaluated_at=_EVALUATED_AT,
        proposed_transition=transition,
        active_route_eligibility=_eligibility(
            ProviderName.GROQ,
            "groq-gpt-oss-20b",
        ),
        target_route_eligibility=None,
    )
    decision = evaluate_route_policy(request)
    assert decision.decision_code is RoutePolicyDecisionCode.AUTHORIZED_SESSION_RESET
