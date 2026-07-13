from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.cache_telemetry_calibration_review import (
    CacheTelemetryCalibrationReview,
    CalibrationDryRunReport,
    CalibrationOutcome,
    CalibrationPromptRecipe,
    CalibrationReviewManifest,
)

_REVIEW_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-review-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_review_is_inactive_and_non_live() -> None:
    review = CacheTelemetryCalibrationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert review.provider_call_authorized is False
    assert review.active_authorization_created is False
    assert review.execution_command_available is False
    assert review.credential_accessed is False
    assert review.calibration_execution_authorized is False
    assert review.benchmark_execution_authorized is False


def test_review_requires_all_four_outcomes() -> None:
    review = CacheTelemetryCalibrationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert {item.outcome for item in review.outcome_taxonomy} == set(CalibrationOutcome)


def test_review_requires_eight_unique_source_bindings() -> None:
    review = CacheTelemetryCalibrationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )
    paths = [item.path for item in review.source_bindings]

    assert len(paths) == 8
    assert len(paths) == len(set(paths))


def test_review_rejects_duplicate_source_binding() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    bindings = deepcopy(payload["source_bindings"])
    assert isinstance(bindings, list)
    bindings[-1] = deepcopy(bindings[0])
    payload["source_bindings"] = bindings

    with pytest.raises(
        ValidationError,
        match="source binding paths must be unique",
    ):
        CacheTelemetryCalibrationReview.model_validate(payload)


def test_schedule_is_three_call_no_retry_no_resume() -> None:
    review = CacheTelemetryCalibrationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert review.schedule.maximum_provider_calls == 3
    assert review.schedule.attempt_offsets_seconds == (0, 10, 20)
    assert review.schedule.retry_permitted is False
    assert review.schedule.resume_permitted is False


def test_review_rejects_schedule_reordering() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    schedule = deepcopy(payload["schedule"])
    assert isinstance(schedule, dict)
    schedule["attempt_offsets_seconds"] = [0, 20, 10]
    payload["schedule"] = schedule

    with pytest.raises(
        ValidationError,
        match="offsets must remain 0, 10, and 20",
    ):
        CacheTelemetryCalibrationReview.model_validate(payload)


def test_prompt_recipe_exceeds_documented_upper_minimum() -> None:
    recipe = CalibrationPromptRecipe.model_validate(
        _json_object(_REVIEW_ROOT / "prompt_recipe.json")
    )

    assert recipe.conservative_input_token_estimate == 2112
    assert recipe.minimum_cacheable_token_upper_bound == 1024
    assert recipe.minimum_length_margin_tokens == 1088
    assert recipe.raw_prompt_committed is False


def test_dry_run_repeats_one_exact_provider_request() -> None:
    report = CalibrationDryRunReport.model_validate(
        _json_object(_REVIEW_ROOT / "dry_run_report.json")
    )
    hashes = {item.provider_request_sha256 for item in report.attempts}

    assert report.planned_attempt_count == 3
    assert report.unique_provider_request_count == 1
    assert report.repeated_provider_request_count == 2
    assert len(hashes) == 1


def test_dry_run_rejects_provider_request_drift() -> None:
    payload = _json_object(_REVIEW_ROOT / "dry_run_report.json")
    attempts = deepcopy(payload["attempts"])
    assert isinstance(attempts, list)
    assert isinstance(attempts[1], dict)
    attempts[1]["provider_request_sha256"] = "0" * 64
    payload["attempts"] = attempts

    with pytest.raises(
        ValidationError,
        match="all calibration requests must be identical",
    ):
        CalibrationDryRunReport.model_validate(payload)


def test_manifest_keeps_execution_inactive() -> None:
    manifest = CalibrationReviewManifest.model_validate(
        _json_object(_REVIEW_ROOT / "manifest.json")
    )

    assert manifest.provider_call_authorized is False
    assert manifest.execution_command_available is False
    assert manifest.calibration_execution_authorized is False
    assert manifest.benchmark_execution_authorized is False


def test_public_review_assets_exclude_sensitive_fields() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            _REVIEW_ROOT / "prompt_recipe.json",
            _REVIEW_ROOT / "review.json",
            _REVIEW_ROOT / "dry_run_report.json",
            _REVIEW_ROOT / "manifest.json",
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
