from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from auragateway.contracts.cache_telemetry_capture import (
    BillingCacheObservationState,
    GroqCacheTelemetryCapture,
)
from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderName,
)
from auragateway.contracts.telemetry import CachedInputDetailTelemetry
from auragateway.providers.base import (
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderPrompt,
)
from auragateway.providers.groq import GroqProviderAdapter


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


class _Client:
    def __init__(
        self,
        payload: dict[str, object] | _Response,
    ) -> None:
        self._response = payload if isinstance(payload, _Response) else _Response(payload)
        self.call_count = 0

    def create(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        model: str,
        max_completion_tokens: int,
        temperature: float,
        stream: bool,
        store: bool,
        reasoning_effort: str,
    ) -> _Response:
        self.call_count += 1
        return self._response


class _SdkValue:
    def __init__(
        self,
        *,
        model_fields_set: set[str],
        **values: object,
    ) -> None:
        self.model_fields_set = model_fields_set
        for key, value in values.items():
            setattr(self, key, value)


class _SdkLikeResponse(_Response):
    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__(payload)
        self.model_fields_set = {"model", "choices", "usage"}
        self.usage = _SdkValue(
            model_fields_set={
                "prompt_tokens",
                "completion_tokens",
                "total_time",
            },
            prompt_tokens_details=None,
        )
        self.x_groq = None


def _invocation(case_id: str) -> LiveProviderInvocation:
    return LiveProviderInvocation(
        request=ProviderInvocationRequest(
            request_id=f"{case_id}-request",
            fixture_id=case_id,
            provider=ProviderName.GROQ,
            model_alias="groq-gpt-oss-20b",
            static_prefix_fingerprint="a" * 64,
            input_token_count=1000,
            output_token_budget=256,
        ),
        prompt=ProtectedProviderPrompt(
            system_prompt="synthetic stable system prompt",
            user_prompt="synthetic user request",
        ),
        timeout_seconds=30.0,
    )


def _payload(
    *,
    prompt_tokens_details: object = None,
    include_prompt_tokens_details: bool = True,
    x_groq: object = None,
    include_x_groq: bool = False,
) -> dict[str, object]:
    usage: dict[str, object] = {
        "prompt_tokens": 1000,
        "completion_tokens": 12,
        "total_time": 0.15,
    }
    if include_prompt_tokens_details:
        usage["prompt_tokens_details"] = prompt_tokens_details

    payload: dict[str, object] = {
        "id": "provider-response-id-must-not-be-retained",
        "model": "openai/gpt-oss-20b",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": (
                        '{"decision":"answer","response":"synthetic","citation_ids":["SYN-001"]}'
                    ),
                    "reasoning": "private reasoning must not be retained",
                    "refusal": None,
                    "tool_calls": None,
                },
            }
        ],
        "usage": usage,
    }
    if include_x_groq:
        payload["x_groq"] = x_groq
    return payload


def _capture_from(
    case_id: str,
    payload: dict[str, object] | _Response,
) -> GroqCacheTelemetryCapture:
    adapter = GroqProviderAdapter(
        _Client(payload),
        installed_sdk_version="1.6.0",
    )
    call = adapter.invoke(_invocation(case_id))
    capture = call.success_telemetry_shape
    assert isinstance(capture, GroqCacheTelemetryCapture)
    return capture


def test_absent_billing_field_is_distinct_from_zero() -> None:
    capture = _capture_from(
        "groq-capture-field-absent",
        _payload(include_prompt_tokens_details=False),
    )

    assert capture.usage_present is True
    assert capture.prompt_tokens_details_present is False
    assert capture.billing_cached_tokens_field_present is False
    assert capture.billing_cached_input_tokens is None
    assert capture.billing_observation_state is BillingCacheObservationState.FIELD_ABSENT


def test_sdk_defaults_do_not_fabricate_field_presence() -> None:
    payload = _payload(prompt_tokens_details=None)
    capture = _capture_from(
        "groq-capture-sdk-default-absent",
        _SdkLikeResponse(payload),
    )

    assert capture.usage_present is True
    assert capture.prompt_tokens_details_present is False
    assert capture.billing_cached_tokens_field_present is False
    assert capture.billing_cached_input_tokens is None


def test_null_billing_field_is_retained_as_null() -> None:
    capture = _capture_from(
        "groq-capture-field-null",
        _payload(prompt_tokens_details={"cached_tokens": None}),
    )

    assert capture.prompt_tokens_details_present is True
    assert capture.billing_cached_tokens_field_present is True
    assert capture.billing_cached_input_tokens is None
    assert capture.billing_observation_state is BillingCacheObservationState.FIELD_NULL


def test_measured_zero_is_retained_as_observed_zero() -> None:
    capture = _capture_from(
        "groq-capture-zero",
        _payload(prompt_tokens_details={"cached_tokens": 0}),
    )

    assert capture.billing_cached_tokens_field_present is True
    assert capture.billing_cached_input_tokens == 0
    assert capture.billing_observation_state is BillingCacheObservationState.OBSERVED_ZERO


def test_positive_billing_and_hardware_values_remain_separate() -> None:
    capture = _capture_from(
        "groq-capture-positive",
        _payload(
            prompt_tokens_details={"cached_tokens": 600},
            include_x_groq=True,
            x_groq={
                "usage": {
                    "dram_cached_tokens": 800,
                    "sram_cached_tokens": 200,
                }
            },
        ),
    )

    assert capture.billing_cached_input_tokens == 600
    assert capture.dram_cached_tokens == 800
    assert capture.sram_cached_tokens == 200
    assert capture.billing_cached_input_tokens != (
        capture.dram_cached_tokens + capture.sram_cached_tokens
    )


def test_exact_installed_sdk_version_is_retained() -> None:
    capture = _capture_from(
        "groq-capture-sdk-version",
        _payload(prompt_tokens_details={"cached_tokens": 0}),
    )

    assert capture.installed_sdk_version == "1.6.0"
    assert capture.capture_version == "groq-cache-telemetry-capture-v1"


def test_success_shape_contains_no_raw_provider_content() -> None:
    capture = _capture_from(
        "groq-capture-privacy",
        _payload(
            prompt_tokens_details={"cached_tokens": 0},
            include_x_groq=True,
            x_groq={
                "usage": {
                    "dram_cached_tokens": 0,
                    "sram_cached_tokens": 0,
                }
            },
        ),
    )
    serialized = capture.model_dump_json()

    for forbidden in (
        "provider-response-id-must-not-be-retained",
        "private reasoning must not be retained",
        "synthetic user request",
        "synthetic stable system prompt",
        "citation_ids",
        "api_key",
        "authorization",
    ):
        assert forbidden not in serialized


def test_negative_hardware_cache_value_fails_typed_response_validation() -> None:
    adapter = GroqProviderAdapter(
        _Client(
            _payload(
                prompt_tokens_details={"cached_tokens": 0},
                include_x_groq=True,
                x_groq={
                    "usage": {
                        "dram_cached_tokens": -1,
                        "sram_cached_tokens": 0,
                    }
                },
            )
        ),
        installed_sdk_version="1.6.0",
    )

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation("groq-capture-negative-hardware"))

    assert exc_info.value.error_code is ProviderErrorCode.INVALID_RESPONSE


def test_success_call_retains_standard_usage_telemetry() -> None:
    adapter = GroqProviderAdapter(
        _Client(_payload(prompt_tokens_details={"cached_tokens": 600})),
        installed_sdk_version="1.6.0",
    )
    call = adapter.invoke(_invocation("groq-capture-standard-usage"))

    assert isinstance(call.telemetry, CachedInputDetailTelemetry)
    assert call.telemetry.input_tokens == 1000
    assert call.telemetry.cached_input_tokens == 600
    assert call.telemetry.output_tokens == 12
    assert call.telemetry.total_duration_ms == 150
