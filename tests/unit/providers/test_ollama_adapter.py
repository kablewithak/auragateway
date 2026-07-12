from __future__ import annotations

from collections.abc import Mapping
from urllib.error import URLError

import pytest

from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderName,
)
from auragateway.contracts.telemetry import LocalPromptEvaluationTelemetry
from auragateway.providers.base import (
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderPrompt,
)
from auragateway.providers.ollama import (
    OLLAMA_DEFAULT_ENDPOINT,
    OLLAMA_MODEL_ALIAS,
    OLLAMA_MODEL_ID,
    OllamaProviderAdapter,
)

_PREFIX_FINGERPRINT = "6b7c72729eca9480ef7a0cf734b957dd6c10fa9ff88adc33e322af54d50f4d63"


class _Transport:
    def __init__(self, payload: Mapping[str, object] | Exception) -> None:
        self._payload = payload
        self.request_payload: Mapping[str, object] | None = None

    def generate(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        assert endpoint == OLLAMA_DEFAULT_ENDPOINT
        assert timeout_seconds == 300
        self.request_payload = payload
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _invocation(provider: ProviderName = ProviderName.OLLAMA) -> LiveProviderInvocation:
    request = ProviderInvocationRequest(
        request_id="ollama-calibration-request-1",
        fixture_id="ollama-live-turn-1",
        provider=provider,
        model_alias=OLLAMA_MODEL_ALIAS,
        static_prefix_fingerprint=_PREFIX_FINGERPRINT,
        input_token_count=2300,
        output_token_budget=32,
    )
    return LiveProviderInvocation(
        request=request,
        prompt=ProtectedProviderPrompt(system_prompt="stable-prefix", user_prompt="dynamic-turn"),
        timeout_seconds=300 if provider is ProviderName.OLLAMA else 60,
    )


def _payload() -> dict[str, object]:
    return {
        "model": OLLAMA_MODEL_ID,
        "response": "READY-1",
        "done": True,
        "done_reason": "stop",
        "total_duration": 4_100_000_000,
        "prompt_eval_count": 2294,
        "prompt_eval_duration": 2_900_000_000,
        "eval_count": 5,
    }


def test_ollama_adapter_maps_local_timing_without_cache_claim() -> None:
    transport = _Transport(_payload())
    call = OllamaProviderAdapter(transport).invoke(_invocation())
    assert isinstance(call.telemetry, LocalPromptEvaluationTelemetry)
    assert call.telemetry.prompt_eval_count == 2294
    assert call.telemetry.prompt_eval_duration_ms == 2900
    assert call.telemetry.total_duration_ms == 4100
    assert call.telemetry.output_eval_count == 5
    assert transport.request_payload is not None


def test_ollama_adapter_rejects_provider_identity_drift() -> None:
    with pytest.raises(LiveProviderError) as caught:
        OllamaProviderAdapter(_Transport(_payload())).invoke(_invocation(ProviderName.GROQ))
    assert caught.value.error_code is ProviderErrorCode.CONFIGURATION_MISMATCH


def test_ollama_adapter_maps_local_connection_failure() -> None:
    with pytest.raises(LiveProviderError) as caught:
        OllamaProviderAdapter(_Transport(URLError("raw local detail"))).invoke(_invocation())
    assert caught.value.error_code is ProviderErrorCode.CONNECTION_FAILED
    assert caught.value.retryable is True
    assert "raw local detail" not in caught.value.safe_message
