from __future__ import annotations

import hashlib
from collections.abc import Mapping

import pytest

from auragateway.contracts.openrouter import (
    OpenRouterCachedInputTelemetry,
    OpenRouterCacheObservationState,
    OpenRouterInvocationRequest,
)
from auragateway.contracts.provider import ProviderErrorCode
from auragateway.providers.base import LiveProviderError, ProtectedProviderPrompt
from auragateway.providers.openrouter import (
    OpenRouterLiveInvocation,
    OpenRouterProviderAdapter,
)


class _Transport:
    def __init__(
        self,
        completion: Mapping[str, object],
        generation: Mapping[str, object],
    ) -> None:
        self.completion = completion
        self.generation = generation
        self.request_payload: Mapping[str, object] | None = None

    def create_chat(
        self,
        *,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        assert timeout_seconds == 30
        self.request_payload = payload
        return self.completion

    def get_generation(
        self,
        *,
        generation_id: str,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        assert generation_id == "gen-test"
        assert timeout_seconds == 30
        return self.generation


def _invocation() -> OpenRouterLiveInvocation:
    return OpenRouterLiveInvocation(
        request=OpenRouterInvocationRequest(
            request_id="openrouter-test-request",
            fixture_id="openrouter-test",
            static_prefix_fingerprint="a" * 64,
            input_token_count=12000,
            output_token_budget=32,
        ),
        prompt=ProtectedProviderPrompt(
            system_prompt="stable synthetic prefix",
            user_prompt="synthetic suffix",
        ),
        session_id="auragateway-session-test",
        timeout_seconds=30,
    )


def _completion(details: object) -> dict[str, object]:
    usage: dict[str, object] = {
        "prompt_tokens": 12000,
        "completion_tokens": 4,
    }
    if details != "missing":
        usage["prompt_tokens_details"] = details
    return {
        "id": "gen-test",
        "model": "tencent/hy3",
        "choices": [{"message": {"content": "READY"}}],
        "usage": usage,
    }


def _generation(native: object = 10000) -> dict[str, object]:
    return {
        "data": {
            "id": "gen-test",
            "model": "tencent/hy3",
            "provider_name": "synthetic-provider",
            "session_id": "auragateway-session-test",
            "native_tokens_cached": native,
            "cache_discount": "0",
        }
    }


def test_adapter_maps_read_and_write_telemetry_without_losing_presence() -> None:
    transport = _Transport(
        _completion({"cached_tokens": 10000, "cache_write_tokens": 0}),
        _generation(),
    )
    observed = OpenRouterProviderAdapter(transport).invoke(_invocation())

    assert isinstance(observed.telemetry, OpenRouterCachedInputTelemetry)
    assert observed.telemetry.cached_input_tokens == 10000
    assert observed.observation.read.state is OpenRouterCacheObservationState.OBSERVED_POSITIVE
    assert observed.observation.write.state is OpenRouterCacheObservationState.OBSERVED_ZERO
    assert observed.observation.route.upstream_provider == "synthetic-provider"
    assert observed.observation.missing_interpreted_as_zero is False


def test_adapter_preserves_absent_cache_fields_as_unknown() -> None:
    observed = OpenRouterProviderAdapter(
        _Transport(_completion("missing"), _generation(None))
    ).invoke(_invocation())

    assert observed.observation.read.state is OpenRouterCacheObservationState.FIELD_ABSENT
    assert observed.observation.write.state is OpenRouterCacheObservationState.FIELD_ABSENT
    assert isinstance(observed.telemetry, OpenRouterCachedInputTelemetry)
    assert observed.telemetry.cached_input_tokens is None


def test_adapter_enforces_privacy_and_omits_manual_provider_order() -> None:
    transport = _Transport(
        _completion({"cached_tokens": 0, "cache_write_tokens": 0}),
        _generation(0),
    )
    OpenRouterProviderAdapter(transport).invoke(_invocation())

    assert transport.request_payload is not None
    assert transport.request_payload["provider"] == {
        "data_collection": "deny",
        "zdr": True,
    }
    assert "order" not in transport.request_payload["provider"]
    assert transport.request_payload["session_id"] == "auragateway-session-test"


def test_adapter_rejects_invalid_numeric_cache_type() -> None:
    with pytest.raises(LiveProviderError) as caught:
        OpenRouterProviderAdapter(
            _Transport(
                _completion({"cached_tokens": "10000", "cache_write_tokens": 0}),
                _generation(),
            )
        ).invoke(_invocation())
    assert caught.value.error_code is ProviderErrorCode.INVALID_RESPONSE
    assert caught.value.retryable is False


def test_adapter_rejects_generation_identity_mismatch() -> None:
    generation = _generation()
    data = generation["data"]
    assert isinstance(data, dict)
    data["model"] = "different/model"

    with pytest.raises(LiveProviderError) as caught:
        OpenRouterProviderAdapter(
            _Transport(
                _completion({"cached_tokens": 10000, "cache_write_tokens": 0}),
                generation,
            )
        ).invoke(_invocation())
    assert caught.value.error_code is ProviderErrorCode.CONFIGURATION_MISMATCH


def test_session_hash_does_not_expose_session_value() -> None:
    invocation = _invocation()
    expected = hashlib.sha256(b"auragateway-session-test").hexdigest()
    assert invocation.session_id_sha256 == expected
    assert "auragateway-session-test" not in repr(invocation)
