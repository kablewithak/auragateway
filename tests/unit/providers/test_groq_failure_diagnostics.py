from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, ClassVar, cast

import pytest

from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderName,
)
from auragateway.contracts.provider_diagnostics import (
    AssistantContentState,
    ProviderFailureFamily,
    ProviderFinishReason,
)
from auragateway.providers.base import (
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderPrompt,
)
from auragateway.providers.groq import GROQ_MODEL_ID, GroqProviderAdapter


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


class _Client:
    def __init__(
        self,
        *,
        response: _Response | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error

    def create(self, **_: Any) -> _Response:
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise AssertionError("fake client requires a response or error")
        return self._response


class BadRequestError(Exception):
    status_code = 400
    request_id = "provider-request-sensitive-id"
    body: ClassVar[dict[str, object]] = {
        "error": {
            "message": "raw provider message must never be retained",
            "type": "invalid_request_error",
            "code": "context_length_exceeded",
            "param": "messages",
        }
    }


class RateLimitError(Exception):
    status_code = 429
    body: ClassVar[dict[str, object]] = {
        "error": {
            "message": "quota details must never be retained",
            "type": "rate_limit_error",
            "code": "tokens_per_minute",
            "param": None,
        }
    }


class UnsafeMetadataBadRequestError(Exception):
    status_code = 400
    body: ClassVar[dict[str, object]] = {
        "error": {
            "message": "raw provider message",
            "type": "customer_specific_type",
            "code": "gsk_secret_shaped_value_1234567890",
            "param": "messages[0]",
        }
    }


class StrangeProviderExplosion(Exception):
    pass


def _invocation(request_id: str = "request-diagnostic-001") -> LiveProviderInvocation:
    return LiveProviderInvocation(
        request=ProviderInvocationRequest(
            request_id=request_id,
            fixture_id="fixture-diagnostic-001",
            provider=ProviderName.GROQ,
            model_alias="groq-gpt-oss-20b",
            static_prefix_fingerprint="a" * 64,
            input_token_count=100,
            output_token_budget=64,
        ),
        prompt=ProtectedProviderPrompt(
            system_prompt="synthetic system prompt",
            user_prompt="synthetic user prompt",
        ),
        timeout_seconds=30.0,
    )


def _read_one(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    return cast(dict[str, object], json.loads(lines[0]))


def _valid_response(
    content: str | None,
    *,
    response_id: str = "completion-sensitive-id",
    finish_reason: str = "stop",
    reasoning: str | None = None,
    refusal: str | None = None,
    tool_calls: list[dict[str, object]] | None = None,
    completion_tokens: int | None = 20,
) -> _Response:
    return _Response(
        {
            "id": response_id,
            "model": GROQ_MODEL_ID,
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {
                        "content": content,
                        "reasoning": reasoning,
                        "refusal": refusal,
                        "tool_calls": tool_calls or [],
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": completion_tokens,
                "total_time": 0.25,
                "prompt_tokens_details": {"cached_tokens": 40},
            },
        }
    )


def test_http_400_is_retained_as_request_rejected_without_raw_message(
    tmp_path: Path,
) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    adapter = GroqProviderAdapter(
        _Client(error=BadRequestError("secret exception message")),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation())

    assert exc_info.value.error_code is ProviderErrorCode.INVALID_RESPONSE
    record = _read_one(diagnostic_path)
    assert record["family"] == ProviderFailureFamily.REQUEST_REJECTED
    assert record["exception_class_allowlisted"] == "BadRequestError"
    assert record["http_status_code"] == 400
    assert record["provider_error_type_allowlisted"] == "invalid_request_error"
    assert record["provider_error_code_allowlisted"] == "context_length_exceeded"
    assert record["provider_error_param_allowlisted"] == "messages"
    assert (
        record["provider_request_id_sha256"]
        == hashlib.sha256(BadRequestError.request_id.encode("utf-8")).hexdigest()
    )
    retained = diagnostic_path.read_text(encoding="utf-8")
    assert "secret exception message" not in retained
    assert "raw provider message" not in retained
    assert BadRequestError.request_id not in retained


def test_rate_limit_retains_family_and_retryability(tmp_path: Path) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    adapter = GroqProviderAdapter(
        _Client(error=RateLimitError("secret quota message")),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation())

    assert exc_info.value.error_code is ProviderErrorCode.RATE_LIMITED
    assert exc_info.value.retryable is True
    record = _read_one(diagnostic_path)
    assert record["family"] == ProviderFailureFamily.RATE_LIMITED
    assert record["retryable"] is True
    assert record["mapped_provider_error_code"] == ProviderErrorCode.RATE_LIMITED
    assert record["response_choice_count"] is None


def test_unapproved_provider_metadata_values_are_dropped(tmp_path: Path) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    adapter = GroqProviderAdapter(
        _Client(error=UnsafeMetadataBadRequestError("secret")),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError):
        adapter.invoke(_invocation())

    record = _read_one(diagnostic_path)
    assert record["provider_error_type_allowlisted"] is None
    assert record["provider_error_code_allowlisted"] is None
    assert record["provider_error_param_allowlisted"] is None
    retained = diagnostic_path.read_text(encoding="utf-8")
    assert "gsk_secret_shaped_value" not in retained
    assert "messages[0]" not in retained


def test_unknown_exception_does_not_retain_unapproved_class_or_message(
    tmp_path: Path,
) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    adapter = GroqProviderAdapter(
        _Client(error=StrangeProviderExplosion("credential-shaped secret")),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation())

    assert exc_info.value.error_code is ProviderErrorCode.INVALID_RESPONSE
    record = _read_one(diagnostic_path)
    assert record["family"] == ProviderFailureFamily.UNKNOWN_PROVIDER_EXCEPTION
    assert record["exception_class_allowlisted"] is None
    retained = diagnostic_path.read_text(encoding="utf-8")
    assert "StrangeProviderExplosion" not in retained
    assert "credential-shaped secret" not in retained


def test_malformed_sdk_response_is_separate_from_request_rejection(
    tmp_path: Path,
) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    adapter = GroqProviderAdapter(
        _Client(response=_Response({"model": GROQ_MODEL_ID, "choices": []})),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation())

    assert exc_info.value.error_code is ProviderErrorCode.INVALID_RESPONSE
    record = _read_one(diagnostic_path)
    assert record["family"] == ProviderFailureFamily.RESPONSE_SCHEMA_INVALID
    assert record["exception_class_allowlisted"] == "ValidationError"
    assert record["http_status_code"] is None
    assert record["response_choice_count"] is None


@pytest.mark.parametrize(
    ("content", "expected_state"),
    [
        (None, AssistantContentState.NULL),
        ("", AssistantContentState.EMPTY),
        ("   \n\t", AssistantContentState.WHITESPACE),
    ],
)
def test_missing_assistant_content_retains_bounded_response_shape(
    tmp_path: Path,
    content: str | None,
    expected_state: AssistantContentState,
) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    reasoning = "private reasoning must not be retained"
    adapter = GroqProviderAdapter(
        _Client(response=_valid_response(content, reasoning=reasoning)),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation())

    assert exc_info.value.error_code is ProviderErrorCode.AMBIGUOUS_RESPONSE
    record = _read_one(diagnostic_path)
    assert record["family"] == ProviderFailureFamily.ASSISTANT_CONTENT_MISSING
    assert record["exception_class_allowlisted"] is None
    assert record["response_choice_count"] == 1
    assert record["response_finish_reason_allowlisted"] == ProviderFinishReason.STOP
    assert record["assistant_content_state"] == expected_state
    assert record["response_usage_present"] is True
    assert record["response_completion_tokens"] == 20
    assert record["reasoning_present"] is True
    assert record["reasoning_byte_count"] == len(reasoning.encode("utf-8"))
    assert record["tool_call_count"] == 0
    assert record["refusal_present"] is False
    assert record["refusal_byte_count"] == 0
    assert record["response_id_sha256"] == hashlib.sha256(b"completion-sensitive-id").hexdigest()
    retained = diagnostic_path.read_text(encoding="utf-8")
    assert reasoning not in retained
    assert "completion-sensitive-id" not in retained


def test_missing_content_retains_finish_reason_and_non_text_shapes(
    tmp_path: Path,
) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    refusal = "private refusal must not be retained"
    tool_calls: list[dict[str, object]] = [
        {
            "id": "tool-call-sensitive-id",
            "function": {"name": "lookup", "arguments": '{"secret":true}'},
        }
    ]
    adapter = GroqProviderAdapter(
        _Client(
            response=_valid_response(
                None,
                finish_reason="tool_calls",
                refusal=refusal,
                tool_calls=tool_calls,
                completion_tokens=64,
            )
        ),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError):
        adapter.invoke(_invocation())

    record = _read_one(diagnostic_path)
    assert record["response_finish_reason_allowlisted"] == ProviderFinishReason.TOOL_CALLS
    assert record["response_completion_tokens"] == 64
    assert record["reasoning_present"] is False
    assert record["reasoning_byte_count"] == 0
    assert record["tool_call_count"] == 1
    assert record["refusal_present"] is True
    assert record["refusal_byte_count"] == len(refusal.encode("utf-8"))
    retained = diagnostic_path.read_text(encoding="utf-8")
    assert refusal not in retained
    assert "tool-call-sensitive-id" not in retained
    assert "secret" not in retained


def test_unknown_finish_reason_is_not_retained(tmp_path: Path) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    adapter = GroqProviderAdapter(
        _Client(response=_valid_response(None, finish_reason="provider_private_reason")),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError):
        adapter.invoke(_invocation())

    record = _read_one(diagnostic_path)
    assert record["response_finish_reason_allowlisted"] is None
    assert "provider_private_reason" not in diagnostic_path.read_text(encoding="utf-8")


def test_missing_usage_retains_unknown_completion_tokens(tmp_path: Path) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    response = _Response(
        {
            "id": "completion-sensitive-id",
            "model": GROQ_MODEL_ID,
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {
                        "content": None,
                        "reasoning": None,
                        "refusal": None,
                        "tool_calls": [],
                    },
                }
            ],
            "usage": None,
        }
    )
    adapter = GroqProviderAdapter(
        _Client(response=response),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError):
        adapter.invoke(_invocation())

    record = _read_one(diagnostic_path)
    assert record["response_finish_reason_allowlisted"] == ProviderFinishReason.LENGTH
    assert record["response_usage_present"] is False
    assert record["response_completion_tokens"] is None


def test_diagnostic_write_failure_blocks_original_failure_as_ambiguous(
    tmp_path: Path,
) -> None:
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")
    diagnostic_path = blocked_parent / "provider_failure_diagnostics.jsonl"
    adapter = GroqProviderAdapter(
        _Client(error=BadRequestError("secret exception message")),
        failure_diagnostic_path=diagnostic_path,
    )

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation())

    assert exc_info.value.error_code is ProviderErrorCode.AMBIGUOUS_RESPONSE
    assert exc_info.value.retryable is False
    assert exc_info.value.safe_message == (
        "Provider failure diagnostic evidence could not be retained safely."
    )


def test_successful_call_writes_no_failure_diagnostic(tmp_path: Path) -> None:
    diagnostic_path = tmp_path / "provider_failure_diagnostics.jsonl"
    adapter = GroqProviderAdapter(
        _Client(response=_valid_response('{"decision":"answer"}')),
        failure_diagnostic_path=diagnostic_path,
    )

    call = adapter.invoke(_invocation())

    assert call.result.status.value == "succeeded"
    assert call.protected_output is not None
    assert not diagnostic_path.exists()
