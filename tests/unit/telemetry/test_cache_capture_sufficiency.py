from __future__ import annotations

from auragateway.contracts.cache_telemetry_capture import (
    CacheMeasurementClaimKind,
    CacheMeasurementDecision,
    CacheMeasurementReasonCode,
    GroqCacheTelemetryCapture,
)
from auragateway.contracts.provider import ProviderName
from auragateway.contracts.telemetry import CachedInputDetailTelemetry
from auragateway.telemetry.cache_capture_sufficiency import (
    assess_groq_cache_telemetry_sufficiency,
)


def _capture(
    case_id: str,
    *,
    field_present: bool = True,
    cached_tokens: int | None = 0,
    hardware_present: bool = False,
) -> GroqCacheTelemetryCapture:
    return GroqCacheTelemetryCapture(
        fixture_id=case_id,
        model_alias="groq-gpt-oss-20b",
        installed_sdk_version="1.6.0",
        usage_present=True,
        prompt_tokens_details_present=field_present,
        billing_cached_tokens_field_present=field_present,
        billing_cached_input_tokens=cached_tokens,
        x_groq_present=hardware_present,
        x_groq_usage_present=hardware_present,
        dram_cached_tokens_field_present=hardware_present,
        dram_cached_tokens=900 if hardware_present else None,
        sram_cached_tokens_field_present=hardware_present,
        sram_cached_tokens=100 if hardware_present else None,
    )


def _telemetry(
    case_id: str,
    *,
    input_tokens: int | None = 1000,
    cached_tokens: int | None = 0,
    provider: ProviderName = ProviderName.GROQ,
    model_alias: str = "groq-gpt-oss-20b",
) -> CachedInputDetailTelemetry:
    return CachedInputDetailTelemetry(
        fixture_id=case_id,
        provider=provider,
        model_alias=model_alias,
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        output_tokens=10,
        total_duration_ms=150,
    )


def test_absent_billing_field_blocks_usage_and_savings() -> None:
    case_id = "sufficiency-field-absent"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(case_id, field_present=False, cached_tokens=None),
        _telemetry(case_id, cached_tokens=None),
        pricing_evidence_available=True,
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    savings = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_SAVINGS)
    assert usage.decision is CacheMeasurementDecision.BLOCKED
    assert usage.reason_code is CacheMeasurementReasonCode.BILLING_CACHE_FIELD_ABSENT
    assert savings.decision is CacheMeasurementDecision.BLOCKED
    assert savings.reason_code is usage.reason_code


def test_null_billing_field_blocks_usage() -> None:
    case_id = "sufficiency-field-null"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(case_id, cached_tokens=None),
        _telemetry(case_id, cached_tokens=None),
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    assert usage.decision is CacheMeasurementDecision.BLOCKED
    assert usage.reason_code is CacheMeasurementReasonCode.BILLING_CACHE_FIELD_NULL


def test_measured_zero_permits_usage_claim() -> None:
    case_id = "sufficiency-observed-zero"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(case_id, cached_tokens=0),
        _telemetry(case_id, cached_tokens=0),
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    assert usage.decision is CacheMeasurementDecision.PERMITTED
    assert usage.reason_code is CacheMeasurementReasonCode.CLAIM_PERMITTED
    assert report.valid_input_denominator is True


def test_measured_positive_with_pricing_permits_savings() -> None:
    case_id = "sufficiency-observed-positive"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(case_id, cached_tokens=600),
        _telemetry(case_id, cached_tokens=600),
        pricing_evidence_available=True,
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    savings = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_SAVINGS)
    assert usage.decision is CacheMeasurementDecision.PERMITTED
    assert savings.decision is CacheMeasurementDecision.PERMITTED


def test_usage_without_pricing_blocks_savings_only() -> None:
    case_id = "sufficiency-pricing-missing"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(case_id, cached_tokens=600),
        _telemetry(case_id, cached_tokens=600),
        pricing_evidence_available=False,
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    savings = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_SAVINGS)
    assert usage.decision is CacheMeasurementDecision.PERMITTED
    assert savings.decision is CacheMeasurementDecision.BLOCKED
    assert savings.reason_code is CacheMeasurementReasonCode.PRICING_EVIDENCE_UNAVAILABLE


def test_cached_tokens_exceeding_input_are_rejected() -> None:
    case_id = "sufficiency-cache-exceeds-input"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(case_id, cached_tokens=1200),
        _telemetry(case_id, input_tokens=1000, cached_tokens=1200),
        pricing_evidence_available=True,
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    assert usage.decision is CacheMeasurementDecision.BLOCKED
    assert usage.reason_code is CacheMeasurementReasonCode.CACHE_TOKENS_EXCEED_INPUT


def test_missing_input_denominator_blocks_usage() -> None:
    case_id = "sufficiency-input-missing"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(case_id, cached_tokens=100),
        _telemetry(case_id, input_tokens=None, cached_tokens=100),
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    assert usage.decision is CacheMeasurementDecision.BLOCKED
    assert usage.reason_code is CacheMeasurementReasonCode.INPUT_DENOMINATOR_UNAVAILABLE


def test_hardware_only_signal_does_not_satisfy_billing_gate() -> None:
    case_id = "sufficiency-hardware-only"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(
            case_id,
            field_present=False,
            cached_tokens=None,
            hardware_present=True,
        ),
        _telemetry(case_id, cached_tokens=None),
        pricing_evidence_available=True,
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    assert report.hardware_cache_signal_present is True
    assert usage.decision is CacheMeasurementDecision.BLOCKED
    assert usage.reason_code is CacheMeasurementReasonCode.BILLING_CACHE_FIELD_ABSENT


def test_provider_identity_mismatch_blocks_usage() -> None:
    case_id = "sufficiency-identity-mismatch"
    report = assess_groq_cache_telemetry_sufficiency(
        _capture(case_id, cached_tokens=100),
        _telemetry(
            case_id,
            cached_tokens=100,
            model_alias="different-model",
        ),
    )

    usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
    assert usage.decision is CacheMeasurementDecision.BLOCKED
    assert usage.reason_code is CacheMeasurementReasonCode.PROVIDER_IDENTITY_MISMATCH
