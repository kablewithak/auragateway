from __future__ import annotations

import pytest
from groq.types.chat.chat_completion import ChatCompletion
from pydantic import ValidationError

from auragateway.benchmark.groq_sdk_cache_schema_compatibility_runner import (
    _payload,
    _probe_real_sdk_case,
)
from auragateway.contracts.cache_telemetry_capture import BillingCacheObservationState
from auragateway.contracts.groq_sdk_cache_schema_compatibility import GroqSdkProbeCaseId


@pytest.mark.parametrize(
    ("case_id", "details_present", "cached_field_present", "cached_value", "state"),
    [
        (
            GroqSdkProbeCaseId.DETAILS_ABSENT,
            False,
            False,
            None,
            BillingCacheObservationState.FIELD_ABSENT,
        ),
        (
            GroqSdkProbeCaseId.DETAILS_EXPLICIT_NULL,
            True,
            False,
            None,
            BillingCacheObservationState.FIELD_ABSENT,
        ),
        (
            GroqSdkProbeCaseId.CACHED_TOKENS_ZERO,
            True,
            True,
            0,
            BillingCacheObservationState.OBSERVED_ZERO,
        ),
        (
            GroqSdkProbeCaseId.CACHED_TOKENS_POSITIVE,
            True,
            True,
            600,
            BillingCacheObservationState.OBSERVED_POSITIVE,
        ),
    ],
)
def test_real_groq_sdk_objects_preserve_adapter_presence_semantics(
    case_id: GroqSdkProbeCaseId,
    details_present: bool,
    cached_field_present: bool,
    cached_value: int | None,
    state: BillingCacheObservationState,
) -> None:
    observed, synthetic_calls = _probe_real_sdk_case(case_id, "1.5.0")

    assert observed.sdk_prompt_tokens_details_field_present is details_present
    assert observed.sdk_cached_tokens_field_present is cached_field_present
    assert observed.sdk_cached_tokens_value == cached_value
    assert observed.adapter_prompt_tokens_details_present is details_present
    assert observed.adapter_billing_cached_tokens_field_present is cached_field_present
    assert observed.adapter_billing_cached_input_tokens == cached_value
    assert observed.adapter_billing_observation_state is state
    assert synthetic_calls == 1


def test_real_groq_sdk_rejects_nested_null_cached_tokens() -> None:
    payload = _payload(GroqSdkProbeCaseId.CACHED_TOKENS_ZERO)
    usage = payload["usage"]
    assert isinstance(usage, dict)
    usage["prompt_tokens_details"] = {"cached_tokens": None}

    with pytest.raises(ValidationError):
        ChatCompletion.model_validate(payload)


def test_real_groq_sdk_requires_x_groq_request_id() -> None:
    payload = _payload(GroqSdkProbeCaseId.CACHED_TOKENS_POSITIVE)
    x_groq = payload["x_groq"]
    assert isinstance(x_groq, dict)
    x_groq.pop("id")

    with pytest.raises(ValidationError, match=r"x_groq\.id"):
        ChatCompletion.model_validate(payload)
