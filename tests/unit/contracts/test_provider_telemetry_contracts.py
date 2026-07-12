from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.telemetry import (
    CachedInputDetailTelemetry,
    CacheEvidenceLevel,
    NormalizedTelemetry,
    TelemetryFixtureSet,
    TelemetrySemanticFamily,
    TokenDenominatorKind,
)


def _fixtures() -> TelemetryFixtureSet:
    payload = json.loads(
        Path("data/provider_fixtures/telemetry/fixtures.json").read_text(encoding="utf-8")
    )
    return TelemetryFixtureSet.model_validate(payload)


def test_fixture_set_covers_provider_local_and_unavailable_semantics() -> None:
    fixtures = _fixtures()
    assert {case.telemetry.semantic_family for case in fixtures.cases} == set(
        TelemetrySemanticFamily
    )
    assert len(fixtures.cases) == 8
    assert sum(case.negative_control for case in fixtures.cases) == 6


def test_unknown_cached_input_value_remains_none() -> None:
    fixtures = _fixtures()
    case = next(item for item in fixtures.cases if item.case_id == "missing-cache-field")
    assert isinstance(case.telemetry, CachedInputDetailTelemetry)
    assert case.telemetry.cached_input_tokens is None


def test_normalized_local_evidence_rejects_provider_cache_tokens() -> None:
    with pytest.raises(ValidationError, match="local evidence must not contain"):
        NormalizedTelemetry(
            fixture_id="local-invalid",
            provider="ollama",
            model_alias="synthetic-ollama-local-model",
            semantic_family=TelemetrySemanticFamily.LOCAL_PROMPT_EVALUATION,
            evidence_level=CacheEvidenceLevel.INFERRED_LOCAL,
            denominator_kind=TokenDenominatorKind.LOCAL_PROMPT_EVAL_COUNT,
            provider_cached_input_tokens=10,
            local_prompt_eval_count=100,
            local_prompt_eval_duration_ms=10,
        )


def test_fixture_contract_rejects_unbounded_extra_fields() -> None:
    payload = json.loads(
        Path("data/provider_fixtures/telemetry/fixtures.json").read_text(encoding="utf-8")
    )
    payload["cases"][0]["telemetry"]["raw_provider_payload"] = {"unsafe": True}
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TelemetryFixtureSet.model_validate(payload)
