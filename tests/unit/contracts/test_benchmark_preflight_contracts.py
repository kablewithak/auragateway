from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.benchmark_preflight import (
    BenchmarkBudgetEnvelope,
    BenchmarkPreflightInput,
    ExecutionManifestIdentity,
    ProviderReadinessSnapshot,
    ProviderReadinessState,
)

ROOT = Path(__file__).resolve().parents[3]
INPUT_PATH = ROOT / "data/evals/benchmark/preflight-v1/input.json"


def load_input() -> BenchmarkPreflightInput:
    return BenchmarkPreflightInput.model_validate_json(INPUT_PATH.read_text(encoding="utf-8"))


def test_draft_execution_manifest_keeps_execution_disabled() -> None:
    input_asset = load_input()

    with pytest.raises(
        ValidationError,
        match="draft execution manifests must keep execution disabled",
    ):
        ExecutionManifestIdentity.model_validate(
            {
                **input_asset.execution_manifest.identity.model_dump(mode="json"),
                "execution_enabled": True,
            }
        )


def test_frozen_execution_manifest_requires_digest() -> None:
    input_asset = load_input()

    with pytest.raises(ValidationError, match="frozen execution manifests require"):
        ExecutionManifestIdentity.model_validate(
            {
                **input_asset.execution_manifest.identity.model_dump(mode="json"),
                "execution_manifest_status": "frozen",
            }
        )


def test_provider_live_probe_cannot_pass_without_being_performed() -> None:
    input_asset = load_input()
    payload = input_asset.provider_readiness.model_dump(mode="json")
    payload["live_probe_passed"] = True

    with pytest.raises(ValidationError, match="live_probe_passed requires"):
        ProviderReadinessSnapshot.model_validate(payload)


def test_configuration_ready_requires_all_provider_controls() -> None:
    input_asset = load_input()
    payload = input_asset.provider_readiness.model_dump(mode="json")
    payload["readiness_state"] = ProviderReadinessState.CONFIGURATION_READY.value

    with pytest.raises(ValidationError, match="configuration_ready requires"):
        ProviderReadinessSnapshot.model_validate(payload)


def test_cost_budget_fields_resolve_together() -> None:
    with pytest.raises(ValidationError, match="approved and estimated cost budgets"):
        BenchmarkBudgetEnvelope(
            maximum_trajectory_count=342,
            maximum_turn_count=1368,
            maximum_request_attempt_count=2736,
            approved_cost_budget_minor_units=5000,
            estimated_upper_bound_minor_units=None,
            currency="USD",
        )


def test_input_json_has_no_secret_value_fields() -> None:
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    provider = payload["provider_readiness"]

    assert provider["credentials_configured"] is False
    assert "api_key" not in provider
    assert "token" not in provider
    assert "credential" not in provider
