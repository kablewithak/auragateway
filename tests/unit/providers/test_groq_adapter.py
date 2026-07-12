from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

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
from auragateway.providers.groq import GROQ_MODEL_ALIAS, GROQ_MODEL_ID, GroqProviderAdapter

_PREFIX_FINGERPRINT = "6b7c72729eca9480ef7a0cf734b957dd6c10fa9ff88adc33e322af54d50f4d63"


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


class _Client:
    def __init__(self, payload: dict[str, object] | Exception) -> None:
        self._payload = payload
        self.messages: Sequence[Mapping[str, str]] | None = None

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
        self.messages = messages
        assert model == GROQ_MODEL_ID
        assert max_completion_tokens == 64
        assert temperature == 0
        assert stream is False
        assert store is False
        assert reasoning_effort == "low"
        if isinstance(self._payload, Exception):
            raise self._payload
        return _Response(self._payload)


class RateLimitError(Exception):
    status_code = 429


def _invocation(provider: ProviderName = ProviderName.GROQ) -> LiveProviderInvocation:
    request = ProviderInvocationRequest(
        request_id="groq-calibration-request-1",
        fixture_id="groq-live-turn-1",
        provider=provider,
        model_alias=GROQ_MODEL_ALIAS,
        static_prefix_fingerprint=_PREFIX_FINGERPRINT,
        input_token_count=2300,
        output_token_budget=64,
    )
    return LiveProviderInvocation(
        request=request,
        prompt=ProtectedProviderPrompt(system_prompt="stable-prefix", user_prompt="dynamic-turn"),
        timeout_seconds=60,
    )


def _payload(cached_tokens: int | None = 2048) -> dict[str, object]:
    details: dict[str, object] | None = (
        {"cached_tokens": cached_tokens} if cached_tokens is not None else None
    )
    return {
        "model": GROQ_MODEL_ID,
        "choices": [{"message": {"content": "READY-1"}}],
        "usage": {
            "prompt_tokens": 2310,
            "completion_tokens": 5,
            "total_time": 0.42,
            "prompt_tokens_details": details,
        },
    }


def test_groq_adapter_maps_cached_token_usage_without_raw_persistence() -> None:
    client = _Client(_payload())
    call = GroqProviderAdapter(client).invoke(_invocation())
    assert isinstance(call.telemetry, CachedInputDetailTelemetry)
    assert call.telemetry.input_tokens == 2310
    assert call.telemetry.cached_input_tokens == 2048
    assert call.telemetry.output_tokens == 5
    assert call.telemetry.total_duration_ms == 420
    assert call.result.output_sha256 is not None
    assert client.messages is not None


def test_groq_adapter_preserves_missing_cache_detail_as_none() -> None:
    call = GroqProviderAdapter(_Client(_payload(None))).invoke(_invocation())
    assert isinstance(call.telemetry, CachedInputDetailTelemetry)
    assert call.telemetry.cached_input_tokens is None


def test_groq_adapter_rejects_provider_identity_drift() -> None:
    with pytest.raises(LiveProviderError) as caught:
        GroqProviderAdapter(_Client(_payload())).invoke(_invocation(ProviderName.OPENAI))
    assert caught.value.error_code is ProviderErrorCode.CONFIGURATION_MISMATCH


def test_groq_adapter_maps_rate_limit_without_raw_error_text() -> None:
    with pytest.raises(LiveProviderError) as caught:
        GroqProviderAdapter(_Client(RateLimitError("raw provider body"))).invoke(_invocation())
    assert caught.value.error_code is ProviderErrorCode.RATE_LIMITED
    assert caught.value.retryable is True
    assert "raw provider body" not in caught.value.safe_message
