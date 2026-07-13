"""Assess whether captured Groq cache telemetry supports bounded claims."""

from __future__ import annotations

from auragateway.contracts.cache_telemetry_capture import (
    CacheMeasurementClaimKind,
    CacheMeasurementDecision,
    CacheMeasurementDecisionRecord,
    CacheMeasurementReasonCode,
    GroqCacheTelemetryCapture,
    GroqCacheTelemetrySufficiencyReport,
)
from auragateway.contracts.provider import ProviderName
from auragateway.contracts.telemetry import CachedInputDetailTelemetry


def _decision(
    claim_kind: CacheMeasurementClaimKind,
    permitted: bool,
    reason_code: CacheMeasurementReasonCode,
    *,
    required_fields: tuple[str, ...] = (),
    missing_fields: tuple[str, ...] = (),
    invalid_fields: tuple[str, ...] = (),
) -> CacheMeasurementDecisionRecord:
    return CacheMeasurementDecisionRecord(
        claim_kind=claim_kind,
        decision=(
            CacheMeasurementDecision.PERMITTED if permitted else CacheMeasurementDecision.BLOCKED
        ),
        reason_code=reason_code,
        required_fields=required_fields,
        missing_fields=missing_fields,
        invalid_fields=invalid_fields,
    )


def _usage_decision(
    capture: GroqCacheTelemetryCapture,
    telemetry: CachedInputDetailTelemetry,
) -> CacheMeasurementDecisionRecord:
    required = (
        "billing_cached_tokens_field_present",
        "billing_cached_input_tokens",
        "input_tokens",
    )
    cached_tokens = capture.billing_cached_input_tokens
    input_tokens = telemetry.input_tokens
    if telemetry.provider is not ProviderName.GROQ or (
        telemetry.model_alias != capture.model_alias or telemetry.fixture_id != capture.fixture_id
    ):
        return _decision(
            CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE,
            False,
            CacheMeasurementReasonCode.PROVIDER_IDENTITY_MISMATCH,
            required_fields=required,
            invalid_fields=("provider", "model_alias", "fixture_id"),
        )
    if not capture.billing_cached_tokens_field_present:
        return _decision(
            CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE,
            False,
            CacheMeasurementReasonCode.BILLING_CACHE_FIELD_ABSENT,
            required_fields=required,
            missing_fields=("billing_cached_tokens_field_present",),
        )
    if cached_tokens is None:
        return _decision(
            CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE,
            False,
            CacheMeasurementReasonCode.BILLING_CACHE_FIELD_NULL,
            required_fields=required,
            missing_fields=("billing_cached_input_tokens",),
        )
    if input_tokens is None or input_tokens <= 0:
        return _decision(
            CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE,
            False,
            CacheMeasurementReasonCode.INPUT_DENOMINATOR_UNAVAILABLE,
            required_fields=required,
            missing_fields=("input_tokens",),
        )
    if cached_tokens > input_tokens:
        return _decision(
            CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE,
            False,
            CacheMeasurementReasonCode.CACHE_TOKENS_EXCEED_INPUT,
            required_fields=required,
            invalid_fields=(
                "billing_cached_input_tokens",
                "input_tokens",
            ),
        )
    return _decision(
        CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE,
        True,
        CacheMeasurementReasonCode.CLAIM_PERMITTED,
        required_fields=required,
    )


def assess_groq_cache_telemetry_sufficiency(
    capture: GroqCacheTelemetryCapture,
    telemetry: CachedInputDetailTelemetry,
    *,
    pricing_evidence_available: bool = False,
) -> GroqCacheTelemetrySufficiencyReport:
    """Permit cache claims only when billing telemetry is explicit and valid."""

    usage = _usage_decision(capture, telemetry)
    if usage.decision is CacheMeasurementDecision.BLOCKED:
        savings = _decision(
            CacheMeasurementClaimKind.PROVIDER_CACHE_SAVINGS,
            False,
            usage.reason_code,
            required_fields=usage.required_fields,
            missing_fields=usage.missing_fields,
            invalid_fields=usage.invalid_fields,
        )
    elif not pricing_evidence_available:
        savings = _decision(
            CacheMeasurementClaimKind.PROVIDER_CACHE_SAVINGS,
            False,
            CacheMeasurementReasonCode.PRICING_EVIDENCE_UNAVAILABLE,
            required_fields=("versioned_pricing_schedule",),
            missing_fields=("versioned_pricing_schedule",),
        )
    else:
        savings = _decision(
            CacheMeasurementClaimKind.PROVIDER_CACHE_SAVINGS,
            True,
            CacheMeasurementReasonCode.CLAIM_PERMITTED,
            required_fields=(
                "billing_cached_input_tokens",
                "input_tokens",
                "versioned_pricing_schedule",
            ),
        )

    hardware_signal_present = any(
        (
            capture.dram_cached_tokens_field_present,
            capture.sram_cached_tokens_field_present,
        )
    )
    input_tokens = telemetry.input_tokens
    cached_tokens = capture.billing_cached_input_tokens
    valid_input_denominator = (
        input_tokens is not None
        and input_tokens > 0
        and cached_tokens is not None
        and cached_tokens <= input_tokens
    )
    return GroqCacheTelemetrySufficiencyReport(
        fixture_id=capture.fixture_id,
        billing_observation_state=capture.billing_observation_state,
        valid_input_denominator=valid_input_denominator,
        hardware_cache_signal_present=hardware_signal_present,
        decisions=(usage, savings),
    )
