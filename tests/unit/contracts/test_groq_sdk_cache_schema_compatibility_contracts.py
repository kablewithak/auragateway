from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.cache_telemetry_capture import BillingCacheObservationState
from auragateway.contracts.groq_sdk_cache_schema_compatibility import (
    GroqSdkCacheSchemaCompatibilityManifest,
    GroqSdkCacheSchemaCompatibilityReview,
    GroqSdkCompatibilityClassification,
    GroqSdkProbeCaseId,
    GroqSdkProbeExpectation,
)

_REVIEW_PATH = Path("data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1/review.json")
_MANIFEST_PATH = Path("data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1/manifest.json")


def _review_payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(_REVIEW_PATH.read_text(encoding="utf-8")),
    )


def test_review_asset_closes_only_provider_omission_classification() -> None:
    review = GroqSdkCacheSchemaCompatibilityReview.model_validate(_review_payload())

    assert review.primary_classification is (
        GroqSdkCompatibilityClassification.PROVIDER_OMISSION_SUPPORTED
    )
    assert review.exact_provider_omission_cause_resolved is False
    assert review.sdk_upgrade_required is False
    assert review.adapter_change_required is False
    assert review.provider_call_authorized is False
    assert review.calibration_rerun_authorized is False
    assert review.benchmark_execution_authorized is False
    assert review.new_live_authorization_review_permitted is True

    supported = [item.classification for item in review.candidate_assessments if item.supported]
    assert supported == [GroqSdkCompatibilityClassification.PROVIDER_OMISSION_SUPPORTED]


def test_review_asset_contains_all_real_sdk_probe_cases() -> None:
    review = GroqSdkCacheSchemaCompatibilityReview.model_validate(_review_payload())

    assert {item.case_id for item in review.probe_expectations} == set(GroqSdkProbeCaseId)
    assert (
        review.expectation_for(
            GroqSdkProbeCaseId.DETAILS_EXPLICIT_NULL
        ).sdk_prompt_tokens_details_field_present
        is True
    )
    assert (
        review.expectation_for(
            GroqSdkProbeCaseId.DETAILS_EXPLICIT_NULL
        ).adapter_billing_observation_state
        is BillingCacheObservationState.FIELD_ABSENT
    )


def test_review_rejects_multiple_supported_candidate_causes() -> None:
    payload = _review_payload()
    assessments = payload["candidate_assessments"]
    assert isinstance(assessments, list)
    assert isinstance(assessments[1], dict)
    assessments[1]["supported"] = True

    with pytest.raises(
        ValidationError,
        match="only provider omission may be supported",
    ):
        GroqSdkCacheSchemaCompatibilityReview.model_validate(payload)


def test_review_rejects_sdk_upgrade_authorization_drift() -> None:
    payload = _review_payload()
    payload["sdk_upgrade_required"] = True

    with pytest.raises(ValidationError):
        GroqSdkCacheSchemaCompatibilityReview.model_validate(payload)


def test_probe_expectation_rejects_zero_without_field_presence() -> None:
    with pytest.raises(ValidationError, match="adapter cache values require field presence"):
        GroqSdkProbeExpectation(
            case_id=GroqSdkProbeCaseId.CACHED_TOKENS_ZERO,
            sdk_prompt_tokens_details_field_present=True,
            sdk_cached_tokens_field_present=True,
            sdk_cached_tokens_value=0,
            adapter_prompt_tokens_details_present=True,
            adapter_billing_cached_tokens_field_present=False,
            adapter_billing_cached_input_tokens=0,
            adapter_billing_observation_state=BillingCacheObservationState.OBSERVED_ZERO,
        )


def test_manifest_asset_validates_hash_contract() -> None:
    manifest = GroqSdkCacheSchemaCompatibilityManifest.model_validate_json(
        _MANIFEST_PATH.read_text(encoding="utf-8")
    )

    assert manifest.review_id == "groq-sdk-cache-schema-compatibility-v1"
    assert manifest.review_sha256 == (
        "9fbe7ef29eb7064e62f0774305c56a299eeeac47f7a6611f12cbb267f67ec807"
    )
