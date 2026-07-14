from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.groq_cache_telemetry_reauthorization import (
    GroqCacheTelemetryReauthorizationOutcome,
)
from auragateway.contracts.groq_cache_telemetry_reauthorization_execution import (
    ReauthorizationActivationManifest,
    ReauthorizationActivationReport,
    ReauthorizationAttemptRecord,
    ReauthorizationAttemptStatus,
    ReauthorizationBillingObservationState,
    ReauthorizationExecutionAuthorization,
    ReauthorizationExecutionReport,
    ReauthorizationExecutionRuntimePolicy,
    ReauthorizationExecutionStatus,
)

_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_active_authorization_is_exactly_two_call_and_non_benchmark() -> None:
    authorization = ReauthorizationExecutionAuthorization.model_validate(
        _json_object(_ROOT / "authorization.json")
    )

    assert authorization.status.value == "active"
    assert authorization.maximum_provider_calls == 2
    assert authorization.planned_attempt_count == 2
    assert authorization.planned_maximum_cost_microusd == 400
    assert authorization.maximum_total_cost_microusd == 700
    assert authorization.confirmation_phrase == (
        "EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE"
    )
    assert authorization.retry_permitted is False
    assert authorization.resume_permitted is False
    assert authorization.rerun_permitted is False
    assert authorization.provider_calls_permitted is True
    assert authorization.execution_command_available is True
    assert authorization.reauthorization_execution_authorized is True
    assert authorization.prior_calibration_rerun_authorized is False
    assert authorization.benchmark_execution_authorized is False
    assert authorization.comparison_eligible is False


def test_authorization_binds_review_and_one_protected_prompt() -> None:
    authorization = ReauthorizationExecutionAuthorization.model_validate(
        _json_object(_ROOT / "authorization.json")
    )

    assert len(authorization.bindings) == 6
    assert sum(item.protected_local for item in authorization.bindings) == 1
    assert {item.path for item in authorization.bindings if item.protected_local} == {
        ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    }


def test_authorization_rejects_third_provider_call() -> None:
    payload = _json_object(_ROOT / "authorization.json")
    payload["maximum_provider_calls"] = 3

    with pytest.raises(ValidationError):
        ReauthorizationExecutionAuthorization.model_validate(payload)


def test_runtime_policy_freezes_raw_and_parsed_same_response() -> None:
    policy = ReauthorizationExecutionRuntimePolicy.model_validate(
        _json_object(_ROOT / "runtime_policy.json")
    )

    assert policy.schedule_offsets_seconds == (0, 10)
    assert policy.request_roles == ("cold_wire_probe", "warm_wire_probe")
    assert policy.raw_and_parsed_same_response_required is True
    assert policy.retry_permitted is False
    assert policy.resume_permitted is False
    assert policy.public_raw_payload_permitted is False


def test_runtime_policy_rejects_spacing_drift() -> None:
    payload = _json_object(_ROOT / "runtime_policy.json")
    payload["schedule_offsets_seconds"] = [0, 9]

    with pytest.raises(ValidationError):
        ReauthorizationExecutionRuntimePolicy.model_validate(payload)


def test_activation_report_is_non_live_and_active() -> None:
    report = ReauthorizationActivationReport.model_validate(
        _json_object(_ROOT / "activation_report.json")
    )

    assert report.status == "active"
    assert report.provider_call_performed is False
    assert report.credential_accessed is False
    assert report.active_authorization_created is True
    assert report.execution_command_available is True
    assert report.next_gate == "live_reauthorization_preflight"


def test_activation_manifest_is_hash_only() -> None:
    manifest = ReauthorizationActivationManifest.model_validate(
        _json_object(_ROOT / "activation_manifest.json")
    )

    assert manifest.provider_call_performed is False
    assert manifest.active_authorization_created is True


def test_success_record_preserves_absent_as_unknown() -> None:
    record = ReauthorizationAttemptRecord(
        attempt_index=0,
        request_role="cold_wire_probe",
        planned_offset_seconds=0,
        observed_offset_ms=0,
        provider_request_sha256="a" * 64,
        status=ReauthorizationAttemptStatus.SUCCEEDED,
        provider_call_made=True,
        http_status_code=200,
        raw_body_sha256="b" * 64,
        raw_body_byte_count=10,
        parsed_response_sha256="c" * 64,
        parsed_response_byte_count=10,
        installed_sdk_version="1.5.0",
        raw_billing_observation_state=ReauthorizationBillingObservationState.FIELD_ABSENT,
        raw_billing_field_present=False,
        parsed_billing_observation_state=ReauthorizationBillingObservationState.FIELD_ABSENT,
        parsed_billing_field_present=False,
        estimated_cost_microusd=200,
    )

    assert record.raw_billing_cached_tokens is None
    assert record.parsed_billing_cached_tokens is None


def test_skipped_record_cannot_claim_provider_activity() -> None:
    with pytest.raises(ValidationError):
        ReauthorizationAttemptRecord(
            attempt_index=1,
            request_role="warm_wire_probe",
            planned_offset_seconds=10,
            observed_offset_ms=10_000,
            provider_request_sha256="a" * 64,
            status=ReauthorizationAttemptStatus.SKIPPED,
            provider_call_made=False,
            estimated_cost_microusd=0,
        )


def test_wire_absence_report_blocks_cache_usage() -> None:
    report = ReauthorizationExecutionReport(
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        execution_id="groq-cache-telemetry-reauthorization-v1",
        status=ReauthorizationExecutionStatus.COMPLETED,
        outcome=GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_ABSENT,
        provider_call_count=2,
        successful_call_count=2,
        provider_error_count=0,
        observation_invalid_count=0,
        skipped_attempt_count=0,
        raw_numeric_sample_count=0,
        parsed_numeric_sample_count=0,
        raw_absent_sample_count=2,
        estimated_cost_microusd=400,
        live_provider_called=True,
        exact_provider_wire_omission_claim_permitted=True,
        sdk_live_parse_defect_claim_permitted=False,
        provider_cache_usage_claim_permitted_for_execution=False,
    )

    assert report.exact_provider_wire_omission_claim_permitted is True
    assert report.provider_cache_usage_claim_permitted_for_execution is False
    assert report.benchmark_claims_permitted is False


def test_wire_absence_report_rejects_cache_usage_claim() -> None:
    payload = {
        "authorization_id": "groq-cache-telemetry-reauthorization-auth-v1",
        "execution_id": "groq-cache-telemetry-reauthorization-v1",
        "status": "completed",
        "outcome": "wire_field_absent",
        "provider_call_count": 2,
        "successful_call_count": 2,
        "provider_error_count": 0,
        "observation_invalid_count": 0,
        "skipped_attempt_count": 0,
        "raw_numeric_sample_count": 0,
        "parsed_numeric_sample_count": 0,
        "raw_absent_sample_count": 2,
        "estimated_cost_microusd": 400,
        "live_provider_called": True,
        "exact_provider_wire_omission_claim_permitted": True,
        "sdk_live_parse_defect_claim_permitted": False,
        "provider_cache_usage_claim_permitted_for_execution": True,
    }

    with pytest.raises(ValidationError):
        ReauthorizationExecutionReport.model_validate(payload)


def test_public_activation_assets_exclude_sensitive_payloads() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            _ROOT / "authorization.json",
            _ROOT / "runtime_policy.json",
            _ROOT / "activation_report.json",
            _ROOT / "activation_manifest.json",
        )
    )

    for forbidden in (
        '"system_prompt":',
        '"user_prompt":',
        '"messages":',
        '"raw_response":',
        '"raw_body_base64":',
        '"parsed_response":',
        '"api_key":',
        '"authorization_header":',
    ):
        assert forbidden not in text


def test_future_execution_evidence_is_byte_preserved_by_git() -> None:
    attributes = Path(".gitattributes").read_text(encoding="utf-8")
    for path in (
        "journal.jsonl",
        "run_records.json",
        "report.json",
        "manifest.json",
    ):
        rule = f"data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/{path} -text"
        assert rule in attributes
