from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.cache_telemetry_capture import (
    BillingCacheObservationState,
    CacheTelemetryCalibrationDraft,
    CacheTelemetryHardeningAcceptance,
    CacheTelemetrySyntheticCaseSet,
    GroqCacheTelemetryCapture,
)

_DATA_ROOT = Path("data/evals/benchmark/cache-telemetry-hardening-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _capture_payload(case_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "fixture_id": case_id,
        "provider": "groq",
        "model_alias": "groq-gpt-oss-20b",
        "adapter_version": "groq-chat-completions-v1",
        "capture_version": "groq-cache-telemetry-capture-v1",
        "installed_sdk_version": "1.6.0",
        "usage_present": True,
        "prompt_tokens_details_present": True,
        "billing_cached_tokens_field_present": True,
        "billing_cached_input_tokens": 0,
        "x_groq_present": False,
        "x_groq_usage_present": False,
        "dram_cached_tokens_field_present": False,
        "dram_cached_tokens": None,
        "sram_cached_tokens_field_present": False,
        "sram_cached_tokens": None,
    }


def test_capture_distinguishes_absent_null_zero_and_positive() -> None:
    absent_payload = _capture_payload("capture-state-absent")
    absent_payload.update(
        {
            "prompt_tokens_details_present": False,
            "billing_cached_tokens_field_present": False,
            "billing_cached_input_tokens": None,
        }
    )
    null_payload = _capture_payload("capture-state-null")
    null_payload["billing_cached_input_tokens"] = None
    zero_payload = _capture_payload("capture-state-zero")
    positive_payload = _capture_payload("capture-state-positive")
    positive_payload["billing_cached_input_tokens"] = 512

    assert (
        GroqCacheTelemetryCapture.model_validate(absent_payload).billing_observation_state
        is BillingCacheObservationState.FIELD_ABSENT
    )
    assert (
        GroqCacheTelemetryCapture.model_validate(null_payload).billing_observation_state
        is BillingCacheObservationState.FIELD_NULL
    )
    assert (
        GroqCacheTelemetryCapture.model_validate(zero_payload).billing_observation_state
        is BillingCacheObservationState.OBSERVED_ZERO
    )
    assert (
        GroqCacheTelemetryCapture.model_validate(positive_payload).billing_observation_state
        is BillingCacheObservationState.OBSERVED_POSITIVE
    )


def test_capture_rejects_value_without_field_presence() -> None:
    payload = _capture_payload("capture-value-without-field")
    payload["billing_cached_tokens_field_present"] = False

    with pytest.raises(
        ValidationError,
        match="billing cache value requires field presence",
    ):
        GroqCacheTelemetryCapture.model_validate(payload)


def test_capture_rejects_prompt_details_without_usage() -> None:
    payload = _capture_payload("capture-details-without-usage")
    payload["usage_present"] = False

    with pytest.raises(
        ValidationError,
        match="prompt token details require usage presence",
    ):
        GroqCacheTelemetryCapture.model_validate(payload)


def test_capture_rejects_hardware_field_without_x_groq_usage() -> None:
    payload = _capture_payload("capture-hardware-without-parent")
    payload["dram_cached_tokens_field_present"] = True
    payload["dram_cached_tokens"] = 100

    with pytest.raises(
        ValidationError,
        match="hardware cache fields require x_groq usage",
    ):
        GroqCacheTelemetryCapture.model_validate(payload)


def test_capture_rejects_unsafe_sdk_version() -> None:
    payload = _capture_payload("capture-unsafe-sdk-version")
    payload["installed_sdk_version"] = "1.6.0 customer@example.com"

    with pytest.raises(
        ValidationError,
        match="installed SDK version contains unsafe characters",
    ):
        GroqCacheTelemetryCapture.model_validate(payload)


def test_calibration_draft_is_inactive_and_three_call() -> None:
    draft = CacheTelemetryCalibrationDraft.model_validate(
        _json_object(_DATA_ROOT / "calibration_draft.json")
    )

    assert draft.maximum_provider_calls == 3
    assert draft.provider_call_authorized is False
    assert draft.calibration_authorized is False
    assert draft.retry_permitted is False
    assert draft.resume_permitted is False


def test_calibration_draft_rejects_reordered_steps() -> None:
    payload = _json_object(_DATA_ROOT / "calibration_draft.json")
    steps = deepcopy(payload["steps"])
    assert isinstance(steps, list)
    steps.reverse()
    payload["steps"] = steps

    with pytest.raises(
        ValidationError,
        match="sequence indexes must be contiguous",
    ):
        CacheTelemetryCalibrationDraft.model_validate(payload)


def test_hardening_acceptance_requires_all_six_actions() -> None:
    acceptance = CacheTelemetryHardeningAcceptance.model_validate(
        _json_object(_DATA_ROOT / "acceptance.json")
    )

    assert len(acceptance.actions) == 6
    assert acceptance.provider_call_performed is False
    assert acceptance.credential_accessed is False


def test_hardening_acceptance_rejects_missing_action() -> None:
    payload = _json_object(_DATA_ROOT / "acceptance.json")
    actions = deepcopy(payload["actions"])
    assert isinstance(actions, list)
    actions.pop()
    payload["actions"] = actions

    with pytest.raises(ValidationError):
        CacheTelemetryHardeningAcceptance.model_validate(payload)


def test_synthetic_case_set_contains_required_negative_controls() -> None:
    case_set = CacheTelemetrySyntheticCaseSet.model_validate(
        _json_object(_DATA_ROOT / "synthetic_cases.json")
    )
    case_ids = {item.case_id for item in case_set.cases}

    assert "cache-field-absent" in case_ids
    assert "cache-field-null" in case_ids
    assert "cache-observed-zero" in case_ids
    assert "cache-observed-positive" in case_ids
    assert "cache-exceeds-input" in case_ids
    assert "hardware-only-signal" in case_ids


def test_public_assets_exclude_sensitive_fields() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            _DATA_ROOT / "acceptance.json",
            _DATA_ROOT / "calibration_draft.json",
            _DATA_ROOT / "synthetic_cases.json",
        )
    )

    for forbidden in (
        '"system_prompt":',
        '"user_prompt":',
        '"messages":',
        '"raw_output":',
        '"output_text":',
        '"provider_error_message":',
        '"api_key":',
        '"authorization_header":',
    ):
        assert forbidden not in text
