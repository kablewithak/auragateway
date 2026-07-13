from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest

from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderName,
)
from auragateway.contracts.provider_diagnostics import (
    ProviderFailureFamily,
    ProviderReasoningEffort,
    RequestRejectionReason,
)
from auragateway.providers.base import (
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderPrompt,
)
from auragateway.providers.groq import GroqProviderAdapter


class _Response:
    def model_dump(self) -> dict[str, object]:
        raise AssertionError("error-only fake client must never return a response")


class _Client:
    def __init__(self, error: Exception) -> None:
        self._error = error

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
        raise self._error


class BadRequestError(Exception):
    status_code = 400
    request_id = "provider-request-id-must-not-be-retained"

    def __init__(self, body: dict[str, object]) -> None:
        super().__init__("exception message must not be retained")
        self.body = body


def _invocation() -> LiveProviderInvocation:
    return LiveProviderInvocation(
        request=ProviderInvocationRequest(
            request_id="request-rejection-hardening-001",
            fixture_id="fixture-rejection-hardening-001",
            provider=ProviderName.GROQ,
            model_alias="groq-gpt-oss-20b",
            static_prefix_fingerprint="a" * 64,
            input_token_count=1884,
            output_token_budget=256,
        ),
        prompt=ProtectedProviderPrompt(
            system_prompt="stable synthetic prefix π",
            user_prompt="volatile synthetic turn λ",
        ),
        timeout_seconds=30.0,
    )


def _read_one(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    return cast(dict[str, object], json.loads(lines[0]))


def test_top_level_request_error_shape_maps_to_distinct_public_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "provider_failure_diagnostics.jsonl"
    error = BadRequestError(
        {
            "message": "unsupported parameter value",
            "type": "invalid_request_error",
            "code": "unsupported_value",
            "param": "reasoning_effort",
        }
    )
    adapter = GroqProviderAdapter(_Client(error), failure_diagnostic_path=path)

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation())

    assert exc_info.value.error_code is ProviderErrorCode.REQUEST_REJECTED
    assert exc_info.value.retryable is False
    record = _read_one(path)
    assert record["schema_version"] == "1.3.0"
    assert record["family"] == ProviderFailureFamily.REQUEST_REJECTED
    assert record["mapped_provider_error_code"] == ProviderErrorCode.REQUEST_REJECTED
    assert record["request_rejection_reason"] == RequestRejectionReason.UNSUPPORTED_PARAMETER
    assert record["provider_error_code_allowlisted"] == "unsupported_value"
    assert record["provider_error_param_allowlisted"] == "reasoning_effort"


def test_request_rejection_retains_complete_content_free_request_shape(
    tmp_path: Path,
) -> None:
    path = tmp_path / "provider_failure_diagnostics.jsonl"
    error = BadRequestError(
        {
            "error": {
                "message": "context length exceeded",
                "type": "invalid_request_error",
            }
        }
    )
    invocation = _invocation()
    adapter = GroqProviderAdapter(_Client(error), failure_diagnostic_path=path)

    with pytest.raises(LiveProviderError):
        adapter.invoke(invocation)

    record = _read_one(path)
    system_bytes = len(invocation.prompt.system_prompt.encode("utf-8"))
    user_bytes = len(invocation.prompt.user_prompt.encode("utf-8"))
    assert record["adapter_version"] == "groq-chat-completions-v1"
    assert record["request_rejection_reason"] == RequestRejectionReason.CONTEXT_LENGTH
    assert record["request_message_count"] == 2
    assert record["request_system_prompt_byte_count"] == system_bytes
    assert record["request_user_prompt_byte_count"] == user_bytes
    assert record["request_total_prompt_byte_count"] == system_bytes + user_bytes
    assert record["request_input_token_estimate"] == 1884
    assert record["request_output_token_budget"] == 256
    assert record["request_temperature_milli"] == 0
    assert record["request_streaming"] is False
    assert record["request_store_enabled"] is False
    assert record["request_reasoning_effort_allowlisted"] == ProviderReasoningEffort.LOW


def test_unknown_400_discards_secret_message_and_emits_unknown_reason(
    tmp_path: Path,
) -> None:
    path = tmp_path / "provider_failure_diagnostics.jsonl"
    secret = "customer@example.com gsk_secret_value_123"
    error = BadRequestError(
        {
            "error": {
                "message": secret,
                "type": "invalid_request_error",
                "code": "customer_specific_secret_code",
                "param": "messages[0]",
            }
        }
    )
    adapter = GroqProviderAdapter(_Client(error), failure_diagnostic_path=path)

    with pytest.raises(LiveProviderError):
        adapter.invoke(_invocation())

    record = _read_one(path)
    assert record["request_rejection_reason"] == RequestRejectionReason.UNKNOWN
    assert record["provider_error_code_allowlisted"] is None
    assert record["provider_error_param_allowlisted"] is None
    retained = path.read_text(encoding="utf-8")
    assert secret not in retained
    assert "customer@example.com" not in retained
    assert "gsk_secret_value" not in retained
    assert BadRequestError.request_id not in retained
