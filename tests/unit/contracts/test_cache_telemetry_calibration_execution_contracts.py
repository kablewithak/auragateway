from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Literal, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.cache_telemetry_calibration_execution import (
    CalibrationAttemptRecord,
    CalibrationAttemptStatus,
    CalibrationExecutionAuthorization,
    CalibrationExecutionReport,
    CalibrationExecutionRuntimePolicy,
    CalibrationExecutionStatus,
)
from auragateway.contracts.cache_telemetry_calibration_review import (
    CalibrationOutcome,
)
from auragateway.contracts.cache_telemetry_capture import (
    BillingCacheObservationState,
)

_EXECUTION_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _successful_record(index: int) -> CalibrationAttemptRecord:
    roles: tuple[
        Literal["cold"],
        Literal["warm_repeat_one"],
        Literal["warm_repeat_two"],
    ] = ("cold", "warm_repeat_one", "warm_repeat_two")
    offsets = (0, 10, 20)
    return CalibrationAttemptRecord(
        attempt_index=index,
        request_role=roles[index],
        planned_offset_seconds=offsets[index],
        observed_offset_ms=offsets[index] * 1000,
        provider_request_sha256="a" * 64,
        system_prompt_sha256="b" * 64,
        user_prompt_sha256="c" * 64,
        status=CalibrationAttemptStatus.SUCCEEDED,
        provider_call_made=True,
        output_sha256="d" * 64,
        output_byte_count=12,
        input_tokens=2112,
        cached_input_tokens=0,
        output_tokens=4,
        total_duration_ms=150,
        installed_sdk_version="1.6.0",
        usage_present=True,
        prompt_tokens_details_present=True,
        billing_cached_tokens_field_present=True,
        billing_observation_state=(BillingCacheObservationState.OBSERVED_ZERO),
        billing_cached_input_tokens=0,
        x_groq_present=False,
        x_groq_usage_present=False,
        dram_cached_tokens_field_present=False,
        sram_cached_tokens_field_present=False,
        estimated_cost_microusd=200,
    )


def test_authorization_is_active_one_time_and_benchmark_blocked() -> None:
    authorization = CalibrationExecutionAuthorization.model_validate(
        _json_object(_EXECUTION_ROOT / "authorization.json")
    )

    assert authorization.maximum_provider_calls == 3
    assert authorization.one_time_execution is True
    assert authorization.retry_permitted is False
    assert authorization.resume_permitted is False
    assert authorization.calibration_execution_authorized is True
    assert authorization.benchmark_execution_authorized is False
    assert authorization.benchmark_claims_permitted is False


def test_authorization_requires_exact_five_bindings() -> None:
    payload = _json_object(_EXECUTION_ROOT / "authorization.json")
    bindings = deepcopy(payload["bindings"])
    assert isinstance(bindings, list)
    bindings.pop()
    payload["bindings"] = bindings

    with pytest.raises(ValidationError):
        CalibrationExecutionAuthorization.model_validate(payload)


def test_authorization_rejects_cost_above_ceiling() -> None:
    payload = _json_object(_EXECUTION_ROOT / "authorization.json")
    payload["planned_maximum_cost_microusd"] = 1200

    with pytest.raises(ValidationError):
        CalibrationExecutionAuthorization.model_validate(payload)


def test_runtime_policy_freezes_offsets_and_roles() -> None:
    policy = CalibrationExecutionRuntimePolicy.model_validate(
        _json_object(_EXECUTION_ROOT / "runtime_policy.json")
    )

    assert policy.schedule_offsets_seconds == (0, 10, 20)
    assert policy.request_roles == (
        "cold",
        "warm_repeat_one",
        "warm_repeat_two",
    )
    assert policy.retry_permitted is False
    assert policy.resume_permitted is False


def test_runtime_policy_rejects_offset_drift() -> None:
    payload = _json_object(_EXECUTION_ROOT / "runtime_policy.json")
    payload["schedule_offsets_seconds"] = [0, 5, 20]

    with pytest.raises(ValidationError):
        CalibrationExecutionRuntimePolicy.model_validate(payload)


def test_successful_attempt_requires_sdk_and_cache_state() -> None:
    payload = _successful_record(0).model_dump(mode="json")
    payload["installed_sdk_version"] = None

    with pytest.raises(
        ValidationError,
        match="successful attempts require SDK provenance",
    ):
        CalibrationAttemptRecord.model_validate(payload)


def test_skipped_attempt_cannot_claim_provider_cost() -> None:
    payload = _successful_record(2).model_dump(mode="json")
    payload.update(
        {
            "status": "skipped",
            "provider_call_made": False,
            "observed_offset_ms": None,
            "output_sha256": None,
            "output_byte_count": None,
            "installed_sdk_version": None,
            "billing_observation_state": None,
            "estimated_cost_microusd": 200,
        }
    )

    with pytest.raises(
        ValidationError,
        match="skipped attempts cannot consume provider cost",
    ):
        CalibrationAttemptRecord.model_validate(payload)


def test_report_reconciles_three_attempts_and_cost() -> None:
    report = CalibrationExecutionReport(
        authorization_id="groq-cache-telemetry-calibration-auth-v1",
        calibration_id="groq-cache-telemetry-calibration-v1",
        status=CalibrationExecutionStatus.COMPLETED,
        outcome=CalibrationOutcome.TELEMETRY_OBSERVED_WITHOUT_CACHE_HIT,
        provider_call_count=3,
        successful_call_count=3,
        provider_error_count=0,
        telemetry_invalid_count=0,
        skipped_attempt_count=0,
        billing_cache_numeric_sample_count=3,
        warm_positive_cache_sample_count=0,
        estimated_cost_microusd=600,
        live_provider_called=True,
        provider_cache_usage_claim_permitted_for_calibration=True,
    )

    assert report.authorization_consumed is True
    assert report.rerun_permitted is False
    assert report.resume_permitted is False
    assert report.benchmark_claims_permitted is False


def test_report_rejects_non_reconciling_counts() -> None:
    with pytest.raises(
        ValidationError,
        match="report counts must reconcile three attempts",
    ):
        CalibrationExecutionReport(
            authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
            calibration_id="groq-cache-telemetry-calibration-v1",
            status=CalibrationExecutionStatus.FAILED,
            outcome=CalibrationOutcome.CALIBRATION_EXECUTION_FAILED,
            provider_call_count=1,
            successful_call_count=0,
            provider_error_count=1,
            telemetry_invalid_count=0,
            skipped_attempt_count=1,
            billing_cache_numeric_sample_count=0,
            warm_positive_cache_sample_count=0,
            estimated_cost_microusd=200,
            live_provider_called=True,
            provider_cache_usage_claim_permitted_for_calibration=False,
        )


def test_public_activation_assets_exclude_sensitive_fields() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            _EXECUTION_ROOT / "authorization.json",
            _EXECUTION_ROOT / "runtime_policy.json",
        )
    )

    for forbidden in (
        '"system_prompt":',
        '"user_prompt":',
        '"messages":',
        '"raw_response":',
        '"raw_output":',
        '"output_text":',
        '"api_key":',
        '"authorization_header":',
    ):
        assert forbidden not in text
