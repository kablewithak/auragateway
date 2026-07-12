"""Machine-enforced sufficiency decisions for cache, latency, and cost claims."""

from __future__ import annotations

from auragateway.contracts.telemetry import (
    CacheEvidenceLevel,
    ClaimDecision,
    ClaimKind,
    ClaimSufficiencyDecision,
    NormalizedTelemetry,
    PricingSchedule,
    TelemetryReasonCode,
    TelemetrySemanticFamily,
    TelemetrySufficiencyReport,
)


def _decision(
    claim_kind: ClaimKind,
    evidence_level: CacheEvidenceLevel,
    permitted: bool,
    reason_code: TelemetryReasonCode,
    required_fields: tuple[str, ...] = (),
    missing_fields: tuple[str, ...] = (),
    invalid_fields: tuple[str, ...] = (),
) -> ClaimSufficiencyDecision:
    return ClaimSufficiencyDecision(
        claim_kind=claim_kind,
        decision=ClaimDecision.PERMITTED if permitted else ClaimDecision.BLOCKED,
        reason_code=reason_code,
        evidence_level=evidence_level,
        required_fields=required_fields,
        missing_fields=missing_fields,
        invalid_fields=invalid_fields,
    )


def _cache_decision(telemetry: NormalizedTelemetry) -> ClaimSufficiencyDecision:
    if telemetry.semantic_family is TelemetrySemanticFamily.CACHED_INPUT_DETAIL:
        required = ("provider_input_tokens", "provider_cached_input_tokens")
        missing = tuple(name for name in required if getattr(telemetry, name) is None)
        if missing:
            return _decision(
                ClaimKind.CACHE_EFFICIENCY,
                telemetry.evidence_level,
                False,
                TelemetryReasonCode.CACHE_EVIDENCE_UNAVAILABLE,
                required,
                missing,
            )
        total = telemetry.provider_input_tokens
        cached = telemetry.provider_cached_input_tokens
        assert total is not None and cached is not None
        invalid: tuple[str, ...] = ()
        if total <= 0 or cached > total:
            invalid = ("provider_input_tokens", "provider_cached_input_tokens")
        if invalid:
            return _decision(
                ClaimKind.CACHE_EFFICIENCY,
                telemetry.evidence_level,
                False,
                TelemetryReasonCode.CACHE_SEMANTICS_MISMATCH,
                required,
                invalid_fields=invalid,
            )
        return _decision(
            ClaimKind.CACHE_EFFICIENCY,
            telemetry.evidence_level,
            True,
            TelemetryReasonCode.CLAIM_PERMITTED,
            required,
        )
    if telemetry.semantic_family is TelemetrySemanticFamily.CACHE_CREATION_READ:
        component_required: tuple[str, ...] = (
            "provider_uncached_input_tokens",
            "provider_cache_creation_input_tokens",
            "provider_cache_read_input_tokens",
        )
        missing = tuple(name for name in component_required if getattr(telemetry, name) is None)
        if missing:
            return _decision(
                ClaimKind.CACHE_EFFICIENCY,
                telemetry.evidence_level,
                False,
                TelemetryReasonCode.CACHE_EVIDENCE_UNAVAILABLE,
                component_required,
                missing,
            )
        if telemetry.accounting_input_tokens is None or telemetry.accounting_input_tokens <= 0:
            return _decision(
                ClaimKind.CACHE_EFFICIENCY,
                telemetry.evidence_level,
                False,
                TelemetryReasonCode.CACHE_SEMANTICS_MISMATCH,
                component_required,
                invalid_fields=("accounting_input_tokens",),
            )
        return _decision(
            ClaimKind.CACHE_EFFICIENCY,
            telemetry.evidence_level,
            True,
            TelemetryReasonCode.CLAIM_PERMITTED,
            component_required,
        )
    return _decision(
        ClaimKind.CACHE_EFFICIENCY,
        telemetry.evidence_level,
        False,
        TelemetryReasonCode.CACHE_EVIDENCE_UNAVAILABLE,
        ("provider_cache_token_evidence",),
        ("provider_cache_token_evidence",),
    )


def _latency_decision(telemetry: NormalizedTelemetry) -> ClaimSufficiencyDecision:
    latency_fields = (
        "time_to_first_output_ms",
        "total_duration_ms",
        "local_prompt_eval_duration_ms",
    )
    present = tuple(name for name in latency_fields if getattr(telemetry, name) is not None)
    if not present:
        return _decision(
            ClaimKind.LATENCY,
            telemetry.evidence_level,
            False,
            TelemetryReasonCode.LATENCY_EVIDENCE_UNAVAILABLE,
            latency_fields,
            latency_fields,
        )
    invalid = tuple(name for name in present if getattr(telemetry, name) == 0)
    if invalid:
        return _decision(
            ClaimKind.LATENCY,
            telemetry.evidence_level,
            False,
            TelemetryReasonCode.LATENCY_SEMANTICS_MISMATCH,
            present,
            invalid_fields=invalid,
        )
    return _decision(
        ClaimKind.LATENCY,
        telemetry.evidence_level,
        True,
        TelemetryReasonCode.CLAIM_PERMITTED,
        present,
    )


def _cost_decision(
    telemetry: NormalizedTelemetry, pricing: PricingSchedule | None
) -> ClaimSufficiencyDecision:
    if telemetry.semantic_family not in {
        TelemetrySemanticFamily.CACHED_INPUT_DETAIL,
        TelemetrySemanticFamily.CACHE_CREATION_READ,
    }:
        return _decision(
            ClaimKind.ESTIMATED_COST,
            telemetry.evidence_level,
            False,
            TelemetryReasonCode.TOKEN_EVIDENCE_UNAVAILABLE,
            ("provider_token_accounting",),
            ("provider_token_accounting",),
        )
    cache_decision = _cache_decision(telemetry)
    if cache_decision.decision is ClaimDecision.BLOCKED:
        reason = (
            TelemetryReasonCode.CACHE_SEMANTICS_MISMATCH
            if cache_decision.reason_code is TelemetryReasonCode.CACHE_SEMANTICS_MISMATCH
            else TelemetryReasonCode.TOKEN_EVIDENCE_UNAVAILABLE
        )
        return _decision(
            ClaimKind.ESTIMATED_COST,
            telemetry.evidence_level,
            False,
            reason,
            cache_decision.required_fields,
            cache_decision.missing_fields,
            cache_decision.invalid_fields,
        )
    if telemetry.provider_output_tokens is None:
        return _decision(
            ClaimKind.ESTIMATED_COST,
            telemetry.evidence_level,
            False,
            TelemetryReasonCode.TOKEN_EVIDENCE_UNAVAILABLE,
            ("provider_output_tokens",),
            ("provider_output_tokens",),
        )
    if pricing is None:
        return _decision(
            ClaimKind.ESTIMATED_COST,
            telemetry.evidence_level,
            False,
            TelemetryReasonCode.PRICING_EVIDENCE_UNAVAILABLE,
            ("pricing_schedule",),
            ("pricing_schedule",),
        )
    if pricing.provider is not telemetry.provider or pricing.model_alias != telemetry.model_alias:
        return _decision(
            ClaimKind.ESTIMATED_COST,
            telemetry.evidence_level,
            False,
            TelemetryReasonCode.PRICING_SEMANTICS_MISMATCH,
            ("provider", "model_alias"),
            invalid_fields=("provider", "model_alias"),
        )
    if telemetry.semantic_family is TelemetrySemanticFamily.CACHED_INPUT_DETAIL:
        rate_fields: tuple[str, ...] = (
            "standard_input_per_million",
            "cached_input_per_million",
            "output_per_million",
        )
    else:
        rate_fields = (
            "standard_input_per_million",
            "cache_creation_input_per_million",
            "cache_read_input_per_million",
            "output_per_million",
        )
    missing = tuple(name for name in rate_fields if getattr(pricing, name) is None)
    if missing:
        return _decision(
            ClaimKind.ESTIMATED_COST,
            telemetry.evidence_level,
            False,
            TelemetryReasonCode.PRICING_EVIDENCE_UNAVAILABLE,
            rate_fields,
            missing,
        )
    return _decision(
        ClaimKind.ESTIMATED_COST,
        telemetry.evidence_level,
        True,
        TelemetryReasonCode.CLAIM_PERMITTED,
        rate_fields,
    )


def assess_telemetry_sufficiency(
    telemetry: NormalizedTelemetry, pricing: PricingSchedule | None = None
) -> TelemetrySufficiencyReport:
    """Authorize only claims supported by the supplied typed evidence."""

    decisions = (
        _cache_decision(telemetry),
        _latency_decision(telemetry),
        _cost_decision(telemetry, pricing),
    )
    return TelemetrySufficiencyReport(fixture_id=telemetry.fixture_id, decisions=decisions)
