from __future__ import annotations

import json
from pathlib import Path

from auragateway.contracts.telemetry import (
    CacheEvidenceLevel,
    TelemetryFixtureCase,
    TelemetryFixtureSet,
    TelemetrySemanticFamily,
    TokenDenominatorKind,
)
from auragateway.telemetry.normalize import normalize_telemetry


def _cases() -> dict[str, TelemetryFixtureCase]:
    payload = json.loads(
        Path("data/provider_fixtures/telemetry/fixtures.json").read_text(encoding="utf-8")
    )
    fixtures = TelemetryFixtureSet.model_validate(payload)
    return {case.case_id: case for case in fixtures.cases}


def test_cached_detail_normalization_preserves_total_and_cached_meaning() -> None:
    case = _cases()["cached-detail-valid"]
    normalized = normalize_telemetry(case.telemetry)
    assert normalized.denominator_kind is TokenDenominatorKind.PROVIDER_INPUT_TOTAL
    assert normalized.provider_input_tokens == 1000
    assert normalized.provider_cached_input_tokens == 700
    assert normalized.provider_uncached_input_tokens == 300
    assert normalized.provider_cache_read_input_tokens is None


def test_creation_read_normalization_preserves_distinct_components() -> None:
    case = _cases()["creation-read-valid"]
    normalized = normalize_telemetry(case.telemetry)
    assert normalized.denominator_kind is TokenDenominatorKind.PROVIDER_COMPONENT_SUM
    assert normalized.accounting_input_tokens == 1500
    assert normalized.provider_uncached_input_tokens == 300
    assert normalized.provider_cache_creation_input_tokens == 500
    assert normalized.provider_cache_read_input_tokens == 700
    assert normalized.provider_cached_input_tokens is None


def test_local_timing_does_not_create_provider_cache_fields() -> None:
    case = _cases()["local-timing-only"]
    normalized = normalize_telemetry(case.telemetry)
    assert normalized.semantic_family is TelemetrySemanticFamily.LOCAL_PROMPT_EVALUATION
    assert normalized.evidence_level is CacheEvidenceLevel.INFERRED_LOCAL
    assert normalized.local_prompt_eval_count == 900
    assert normalized.provider_cached_input_tokens is None
    assert normalized.provider_cache_creation_input_tokens is None
    assert normalized.provider_cache_read_input_tokens is None


def test_invalid_cached_denominator_is_preserved_for_sufficiency_detection() -> None:
    case = _cases()["invalid-cache-denominator"]
    normalized = normalize_telemetry(case.telemetry)
    assert normalized.provider_input_tokens == 500
    assert normalized.provider_cached_input_tokens == 700
    assert normalized.provider_uncached_input_tokens is None


def test_unavailable_telemetry_keeps_metrics_unknown() -> None:
    case = _cases()["telemetry-unavailable"]
    normalized = normalize_telemetry(case.telemetry)
    assert normalized.evidence_level is CacheEvidenceLevel.UNAVAILABLE
    assert normalized.accounting_input_tokens is None
    assert normalized.total_duration_ms is None
