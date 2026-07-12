"""Normalize typed provider telemetry without flattening provider semantics."""

from __future__ import annotations

from typing import assert_never

from auragateway.contracts.telemetry import (
    CacheCreationReadTelemetry,
    CachedInputDetailTelemetry,
    CacheEvidenceLevel,
    LocalPromptEvaluationTelemetry,
    NormalizedTelemetry,
    ProviderTelemetryPayload,
    TelemetrySemanticFamily,
    TokenDenominatorKind,
    UnavailableTelemetry,
)


def normalize_telemetry(payload: ProviderTelemetryPayload) -> NormalizedTelemetry:
    """Map one typed payload into a provenance-preserving normalized envelope."""

    if isinstance(payload, CachedInputDetailTelemetry):
        uncached_input_tokens: int | None = None
        if (
            payload.input_tokens is not None
            and payload.cached_input_tokens is not None
            and payload.cached_input_tokens <= payload.input_tokens
        ):
            uncached_input_tokens = payload.input_tokens - payload.cached_input_tokens
        return NormalizedTelemetry(
            fixture_id=payload.fixture_id,
            provider=payload.provider,
            model_alias=payload.model_alias,
            semantic_family=TelemetrySemanticFamily.CACHED_INPUT_DETAIL,
            evidence_level=CacheEvidenceLevel.OBSERVED_PROVIDER,
            denominator_kind=TokenDenominatorKind.PROVIDER_INPUT_TOTAL,
            accounting_input_tokens=payload.input_tokens,
            provider_input_tokens=payload.input_tokens,
            provider_output_tokens=payload.output_tokens,
            provider_cached_input_tokens=payload.cached_input_tokens,
            provider_uncached_input_tokens=uncached_input_tokens,
            time_to_first_output_ms=payload.time_to_first_output_ms,
            total_duration_ms=payload.total_duration_ms,
        )
    if isinstance(payload, CacheCreationReadTelemetry):
        components = (
            payload.uncached_input_tokens,
            payload.cache_creation_input_tokens,
            payload.cache_read_input_tokens,
        )
        component_values = tuple(value for value in components if value is not None)
        accounting_input_tokens = sum(component_values) if len(component_values) == 3 else None
        return NormalizedTelemetry(
            fixture_id=payload.fixture_id,
            provider=payload.provider,
            model_alias=payload.model_alias,
            semantic_family=TelemetrySemanticFamily.CACHE_CREATION_READ,
            evidence_level=CacheEvidenceLevel.OBSERVED_PROVIDER,
            denominator_kind=TokenDenominatorKind.PROVIDER_COMPONENT_SUM,
            accounting_input_tokens=accounting_input_tokens,
            provider_output_tokens=payload.output_tokens,
            provider_uncached_input_tokens=payload.uncached_input_tokens,
            provider_cache_creation_input_tokens=payload.cache_creation_input_tokens,
            provider_cache_read_input_tokens=payload.cache_read_input_tokens,
            time_to_first_output_ms=payload.time_to_first_output_ms,
            total_duration_ms=payload.total_duration_ms,
        )
    if isinstance(payload, LocalPromptEvaluationTelemetry):
        return NormalizedTelemetry(
            fixture_id=payload.fixture_id,
            provider=payload.provider,
            model_alias=payload.model_alias,
            semantic_family=TelemetrySemanticFamily.LOCAL_PROMPT_EVALUATION,
            evidence_level=CacheEvidenceLevel.INFERRED_LOCAL,
            denominator_kind=TokenDenominatorKind.LOCAL_PROMPT_EVAL_COUNT,
            accounting_input_tokens=payload.prompt_eval_count,
            provider_output_tokens=payload.output_eval_count,
            local_prompt_eval_count=payload.prompt_eval_count,
            local_prompt_eval_duration_ms=payload.prompt_eval_duration_ms,
            total_duration_ms=payload.total_duration_ms,
        )
    if isinstance(payload, UnavailableTelemetry):
        return NormalizedTelemetry(
            fixture_id=payload.fixture_id,
            provider=payload.provider,
            model_alias=payload.model_alias,
            semantic_family=TelemetrySemanticFamily.UNAVAILABLE,
            evidence_level=CacheEvidenceLevel.UNAVAILABLE,
            denominator_kind=TokenDenominatorKind.UNAVAILABLE,
        )
    assert_never(payload)
