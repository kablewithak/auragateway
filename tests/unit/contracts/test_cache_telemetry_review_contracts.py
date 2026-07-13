from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.cache_telemetry_review import (
    CacheTelemetryClaimKind,
    CacheTelemetrySignalKind,
    CacheTelemetrySufficiencyReview,
)

_REVIEW_ROOT = Path("data/evals/benchmark/cache-telemetry-review-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_review_blocks_all_cache_and_benchmark_claims() -> None:
    review = CacheTelemetrySufficiencyReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert review.current_provider_cache_claim_sufficient is False
    assert review.provider_call_authorized is False
    assert review.calibration_authorized is False
    assert review.full_benchmark_authorized is False
    assert {item.claim_kind for item in review.claims} == set(CacheTelemetryClaimKind)


def test_review_preserves_missing_cache_telemetry_as_unknown() -> None:
    review = CacheTelemetrySufficiencyReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert review.observed_cached_input_token_sample_count == 0
    assert review.observed_total_cached_input_tokens is None
    assert review.unknown_interpreted_as_zero is False


def test_review_requires_all_three_signal_assessments() -> None:
    review = CacheTelemetrySufficiencyReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert {item.signal_kind for item in review.signals} == set(CacheTelemetrySignalKind)


def test_hardware_cache_signals_cannot_become_billing_equivalent() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    signals = deepcopy(payload["signals"])
    assert isinstance(signals, list)
    assert isinstance(signals[1], dict)
    signals[1]["semantically_equivalent_to_billing_cache_tokens"] = True
    payload["signals"] = signals

    with pytest.raises(
        ValidationError,
        match="hardware cache signals cannot be promoted",
    ):
        CacheTelemetrySufficiencyReview.model_validate(payload)


def test_review_rejects_positive_historical_cache_sample_count() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    signals = deepcopy(payload["signals"])
    assert isinstance(signals, list)
    assert isinstance(signals[0], dict)
    signals[0]["observed_sample_count"] = 1
    payload["signals"] = signals

    with pytest.raises(
        ValidationError,
        match="observed no billing cache samples",
    ):
        CacheTelemetrySufficiencyReview.model_validate(payload)


def test_review_requires_exact_six_actions() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    actions = deepcopy(payload["required_actions"])
    assert isinstance(actions, list)
    actions.pop()
    payload["required_actions"] = actions

    with pytest.raises(ValidationError):
        CacheTelemetrySufficiencyReview.model_validate(payload)


def test_review_rejects_provider_call_authorization() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    payload["provider_call_authorized"] = True

    with pytest.raises(ValidationError):
        CacheTelemetrySufficiencyReview.model_validate(payload)


def test_public_review_assets_exclude_sensitive_fields() -> None:
    text = "\n".join(
        (
            (_REVIEW_ROOT / "review.json").read_text(encoding="utf-8"),
            (_REVIEW_ROOT / "manifest.json").read_text(encoding="utf-8"),
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
