from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.groq_cache_telemetry_reauthorization import (
    GroqCacheTelemetryReauthorizationDecision,
    GroqCacheTelemetryReauthorizationManifest,
    GroqCacheTelemetryReauthorizationOutcome,
    GroqCacheTelemetryReauthorizationReview,
    ReauthorizationDryRunReport,
    ReauthorizationObservationPlan,
)

_REVIEW_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-review-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_review_is_inactive_and_requires_separate_activation() -> None:
    review = GroqCacheTelemetryReauthorizationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert review.decision is GroqCacheTelemetryReauthorizationDecision.REVIEW_READY_INACTIVE
    assert review.prior_authorization_consumed is True
    assert review.prior_rerun_permitted is False
    assert review.prior_resume_permitted is False
    assert review.provider_call_performed is False
    assert review.credential_accessed is False
    assert review.provider_call_authorized is False
    assert review.active_authorization_created is False
    assert review.execution_command_available is False
    assert review.reauthorization_execution_authorized is False
    assert review.benchmark_execution_authorized is False
    assert review.comparison_eligible is False


def test_review_binds_complete_historical_lineage() -> None:
    review = GroqCacheTelemetryReauthorizationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )
    paths = [binding.path for binding in review.source_bindings]

    assert len(paths) == 11
    assert len(paths) == len(set(paths))
    assert "data/evals/benchmark/cache-telemetry-calibration-v1/journal.jsonl" in paths
    assert "data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1/review.json" in paths


def test_review_rejects_duplicate_lineage_binding() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    bindings = deepcopy(payload["source_bindings"])
    assert isinstance(bindings, list)
    bindings[-1] = deepcopy(bindings[0])
    payload["source_bindings"] = bindings

    with pytest.raises(ValidationError, match="source binding paths must be unique"):
        GroqCacheTelemetryReauthorizationReview.model_validate(payload)


def test_material_difference_changes_only_observation_boundary() -> None:
    review = GroqCacheTelemetryReauthorizationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )
    difference = review.material_difference

    assert difference.materially_different is True
    assert difference.provider_unchanged is True
    assert difference.model_unchanged is True
    assert difference.prompt_unchanged is True
    assert difference.request_parameters_unchanged is True
    assert difference.only_observation_boundary_changes is True
    assert len(difference.information_gain_questions) == 3


def test_review_rejects_model_change_disguised_as_single_intervention() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    difference = deepcopy(payload["material_difference"])
    assert isinstance(difference, dict)
    difference["model_unchanged"] = False
    payload["material_difference"] = difference

    with pytest.raises(ValidationError):
        GroqCacheTelemetryReauthorizationReview.model_validate(payload)


def test_observation_plan_is_two_call_no_retry_no_resume() -> None:
    plan = ReauthorizationObservationPlan.model_validate(
        _json_object(_REVIEW_ROOT / "observation_plan.json")
    )

    assert plan.planned_attempt_count == 2
    assert plan.maximum_provider_calls == 2
    assert plan.attempt_offsets_seconds == (0, 10)
    assert plan.request_roles == ("cold_wire_probe", "warm_wire_probe")
    assert plan.retry_permitted is False
    assert plan.resume_permitted is False
    assert plan.provider_call_authorized is False
    assert plan.execution_command_available is False
    assert plan.activation_required is True


def test_observation_plan_uses_distinct_protected_raw_and_parsed_paths() -> None:
    plan = ReauthorizationObservationPlan.model_validate(
        _json_object(_REVIEW_ROOT / "observation_plan.json")
    )

    assert plan.protected_raw_responses_path != plan.protected_parsed_responses_path
    assert plan.protected_raw_responses_path.startswith(".local/")
    assert plan.protected_parsed_responses_path.startswith(".local/")
    assert plan.public_raw_payload_permitted is False


def test_observation_plan_rejects_third_call() -> None:
    payload = _json_object(_REVIEW_ROOT / "observation_plan.json")
    payload["planned_attempt_count"] = 3
    payload["maximum_provider_calls"] = 3

    with pytest.raises(ValidationError):
        ReauthorizationObservationPlan.model_validate(payload)


def test_outcome_taxonomy_is_complete_and_unique() -> None:
    review = GroqCacheTelemetryReauthorizationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert {item.outcome for item in review.outcome_taxonomy} == set(
        GroqCacheTelemetryReauthorizationOutcome
    )


def test_wire_absence_does_not_permit_cache_usage_claim() -> None:
    review = GroqCacheTelemetryReauthorizationReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )
    rule = next(
        item
        for item in review.outcome_taxonomy
        if item.outcome is GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_ABSENT
    )

    assert rule.exact_provider_wire_omission_claim_permitted is True
    assert rule.sdk_live_parse_defect_claim_permitted is False
    assert rule.provider_cache_usage_claim_permitted is False
    assert rule.benchmark_claims_permitted is False


def test_dry_run_reproduces_one_exact_request_twice() -> None:
    report = ReauthorizationDryRunReport.model_validate(
        _json_object(_REVIEW_ROOT / "dry_run_report.json")
    )

    assert report.planned_attempt_count == 2
    assert report.unique_provider_request_count == 1
    assert report.repeated_provider_request_count == 1
    assert len({item.provider_request_sha256 for item in report.attempts}) == 1
    assert report.provider_call_performed is False
    assert report.credential_accessed is False


def test_dry_run_rejects_request_identity_drift() -> None:
    payload = _json_object(_REVIEW_ROOT / "dry_run_report.json")
    attempts = deepcopy(payload["attempts"])
    assert isinstance(attempts, list)
    assert isinstance(attempts[1], dict)
    attempts[1]["provider_request_sha256"] = "0" * 64
    payload["attempts"] = attempts

    with pytest.raises(ValidationError, match="byte-identical"):
        ReauthorizationDryRunReport.model_validate(payload)


def test_manifest_keeps_review_inactive() -> None:
    manifest = GroqCacheTelemetryReauthorizationManifest.model_validate(
        _json_object(_REVIEW_ROOT / "manifest.json")
    )

    assert manifest.provider_call_authorized is False
    assert manifest.active_authorization_created is False
    assert manifest.execution_command_available is False
    assert manifest.reauthorization_execution_authorized is False
    assert manifest.benchmark_execution_authorized is False


def test_public_review_assets_exclude_sensitive_payload_fields() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            _REVIEW_ROOT / "observation_plan.json",
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
        '"raw_body":',
        '"output_text":',
        '"api_key":',
        '"authorization_header":',
    ):
        assert forbidden not in text
