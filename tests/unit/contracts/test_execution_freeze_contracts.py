from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.execution_freeze import (
    CostBudgetDecision,
    NegativeControlManifest,
    PricingSchedule,
    PrivacyVerificationReport,
    ProviderReadinessRecord,
)

_REPO_ROOT = Path(__file__).parents[3]
_ASSET_ROOT = _REPO_ROOT / "data/evals/benchmark/freeze-v1"


def _load(name: str) -> object:
    return json.loads((_ASSET_ROOT / name).read_text(encoding="utf-8"))


def test_static_freeze_contracts_validate() -> None:
    pricing = PricingSchedule.model_validate(_load("pricing_schedule.json"))
    controls = NegativeControlManifest.model_validate(_load("negative_control_manifest.json"))
    privacy = PrivacyVerificationReport.model_validate(_load("privacy_verification.json"))

    assert pricing.provider_model_alias == "groq-gpt-oss-20b"
    assert len(controls.controls) == 10
    assert privacy.privacy_verification_passed is True


def test_duplicate_negative_control_id_is_rejected() -> None:
    payload = _load("negative_control_manifest.json")
    assert isinstance(payload, dict)
    controls = payload["controls"]
    assert isinstance(controls, list)
    controls[1]["control_id"] = controls[0]["control_id"]

    with pytest.raises(ValidationError, match="negative-control IDs must be unique"):
        NegativeControlManifest.model_validate(payload)


def test_privacy_summary_must_match_check_results() -> None:
    payload = _load("privacy_verification.json")
    assert isinstance(payload, dict)
    checks = payload["checks"]
    assert isinstance(checks, list)
    checks[0]["passed"] = False

    with pytest.raises(ValidationError, match="must match all check outcomes"):
        PrivacyVerificationReport.model_validate(payload)


def test_provider_readiness_requires_protected_path() -> None:
    with pytest.raises(ValidationError, match="must remain under"):
        ProviderReadinessRecord(
            record_id="provider-readiness-v1",
            provider_name="groq",
            provider_model_alias="groq-gpt-oss-20b",
            provider_adapter_version="groq-chat-completions-v1",
            probe_mode="groq_live",
            credentials_configured=True,
            probe_performed=True,
            probe_passed=True,
            call_count=2,
            protected_report_path="evidence_vault/raw-provider-report.json",
            protected_report_sha256="a" * 64,
            raw_payload_persisted=False,
            measured_execution_permitted=False,
            observed_at=datetime.now(UTC),
        )


def test_cost_budget_decision_rejects_inconsistent_status() -> None:
    with pytest.raises(ValidationError, match="budget_sufficient must match"):
        CostBudgetDecision(
            decision_id="budget-v1",
            pricing_schedule_id="pricing-v1",
            maximum_request_attempt_count=2736,
            maximum_input_tokens_per_attempt=3000,
            maximum_output_tokens_per_attempt=256,
            estimated_upper_bound_minor_units=83,
            approved_cost_budget_minor_units=50,
            currency="USD",
            estimate_uses_uncached_input_price=True,
            budget_sufficient=True,
            estimate_status="versioned_estimate_not_invoice",
        )


def test_pricing_rejects_non_discounted_cached_input() -> None:
    payload = _load("pricing_schedule.json")
    assert isinstance(payload, dict)
    payload["cached_input_usd_per_million_tokens"] = "0.075"

    with pytest.raises(ValidationError, match="cached input price must be lower"):
        PricingSchedule.model_validate(payload)
