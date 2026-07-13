from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.benchmark_execution import LiveDevelopmentAuthorization

_AUTHORIZATION = Path("data/evals/benchmark/live-development-v1/authorization.json")


def test_live_development_authorization_is_exact_and_no_claims() -> None:
    authorization = LiveDevelopmentAuthorization.model_validate_json(
        _AUTHORIZATION.read_text(encoding="utf-8")
    )

    assert authorization.allowed_episode_ids == ("ep-func-001",)
    assert len(authorization.allowed_run_ids) == 3
    assert authorization.live_provider_execution_permitted is True
    assert authorization.held_out_execution_permitted is False
    assert authorization.full_benchmark_execution_permitted is False
    assert authorization.benchmark_claims_permitted is False
    assert authorization.measured_execution_permitted is False


def test_authorization_rejects_attempt_budget_below_one_attempt_per_turn() -> None:
    payload = json.loads(_AUTHORIZATION.read_text(encoding="utf-8"))
    payload["maximum_total_attempt_count"] = 11

    with pytest.raises(ValidationError, match="one attempt for every authorized turn"):
        LiveDevelopmentAuthorization.model_validate(payload)


def test_authorization_rejects_missing_condition() -> None:
    payload = json.loads(_AUTHORIZATION.read_text(encoding="utf-8"))
    payload["allowed_conditions"] = ["condition_a", "condition_b", "condition_b"]

    with pytest.raises(ValidationError, match="conditions A, B, and C exactly"):
        LiveDevelopmentAuthorization.model_validate(payload)
