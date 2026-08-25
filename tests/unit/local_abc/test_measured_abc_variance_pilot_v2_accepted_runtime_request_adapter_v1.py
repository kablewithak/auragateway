from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_accepted_runtime_request_adapter_v1 as adapter,
)


def _messages() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]


def _response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "probe",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"decision": {"const": "answer"}},
                "required": ["decision"],
            },
        },
    }


def _generation(response_format: dict[str, object]) -> dict[str, object]:
    encoded = adapter.canonical_json(response_format).encode("utf-8")
    return {
        "schema_version": "1.0.0",
        "served_model_name": "local-qwen2.5-0.5b-instruct",
        "temperature": 0,
        "top_p": 1,
        "seed": 7,
        "max_tokens": 256,
        "n": 1,
        "stream": False,
        "hidden_retries_permitted": False,
        "response_format_sha256": hashlib.sha256(encoded).hexdigest(),
    }


class _ReadStream:
    def __init__(self, lines: list[str]) -> None:
        self.lines = list(lines)

    def readline(self) -> str:
        return self.lines.pop(0) if self.lines else ""


class _WriteStream:
    def __init__(self) -> None:
        self.values: list[str] = []
        self.closed = False

    def write(self, value: str) -> int:
        self.values.append(value)
        return len(value)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class _FakeProcess:
    def __init__(self, stdout_lines: list[str]) -> None:
        self.stdin = _WriteStream()
        self.stdout = _ReadStream(stdout_lines)
        self.stderr = _ReadStream([])
        self.return_code: int | None = None

    def poll(self) -> int | None:
        return self.return_code

    def wait(self, timeout: float | None = None) -> int:
        _ = timeout
        self.return_code = 0
        return 0

    def terminate(self) -> None:
        self.return_code = 0

    def kill(self) -> None:
        self.return_code = -9


class _FakeTokenizer:
    def __init__(self, observation: adapter.TokenizerObservation) -> None:
        self.observation = observation

    def count(self, messages: list[dict[str, str]]) -> int:
        assert adapter.message_identity(messages) == self.observation.messages_sha256
        return self.observation.prompt_token_count

    def observation_for(
        self,
        messages: list[dict[str, str]],
    ) -> adapter.TokenizerObservation:
        assert adapter.message_identity(messages) == self.observation.messages_sha256
        return self.observation


def test_request_payload_uses_exact_v2_generation_and_response_format() -> None:
    response_format = _response_format()
    generation = _generation(response_format)
    payload = adapter.build_request_payload(
        messages=_messages(),
        cache_salt="a" * 64,
        generation_contract=generation,
        response_format=response_format,
    )

    assert payload == {
        "model": "local-qwen2.5-0.5b-instruct",
        "messages": _messages(),
        "temperature": 0,
        "top_p": 1,
        "seed": 7,
        "max_tokens": 256,
        "n": 1,
        "stream": False,
        "cache_salt": "a" * 64,
        "response_format": response_format,
    }


def test_request_payload_rejects_v1_output_budget() -> None:
    response_format = _response_format()
    generation = _generation(response_format)
    generation["max_tokens"] = 64

    with pytest.raises(adapter.AcceptedRuntimeRequestAdapterError) as exc_info:
        adapter.build_request_payload(
            messages=_messages(),
            cache_salt="a" * 64,
            generation_contract=generation,
            response_format=response_format,
        )

    assert exc_info.value.error_code == "V2_GENERATION_CONTRACT_DRIFT"


def test_request_payload_rejects_response_format_identity_drift() -> None:
    response_format = _response_format()
    generation = _generation(response_format)
    response_format["type"] = "json_object"

    with pytest.raises(adapter.AcceptedRuntimeRequestAdapterError) as exc_info:
        adapter.build_request_payload(
            messages=_messages(),
            cache_salt="a" * 64,
            generation_contract=generation,
            response_format=response_format,
        )

    assert exc_info.value.error_code == "V2_RESPONSE_FORMAT_IDENTITY_DRIFT"


def test_budget_is_consumed_before_failed_transport_and_no_retry_occurs() -> None:
    messages = _messages()
    observation = adapter.TokenizerObservation(
        messages_sha256=adapter.message_identity(messages),
        rendered_prompt_sha256="b" * 64,
        prompt_token_count=25,
    )
    tokenizer = _FakeTokenizer(observation)
    budget = adapter.RequestBudget()
    calls: list[dict[str, object]] = []

    def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append({"url": url, "payload": payload})
        raise RuntimeError("transport failed")

    request_adapter = adapter.OneShotVllmRequestAdapter(
        tokenizer=tokenizer,
        post_json=post_json,
        generation_contract=_generation(_response_format()),
        response_format=_response_format(),
        budget=budget,
    )

    with pytest.raises(RuntimeError, match="transport failed"):
        request_adapter.send(
            request_id="request-1",
            url="http://127.0.0.1:8001/v1/chat/completions",
            messages=messages,
            cache_salt="c" * 64,
        )

    assert budget.attempted_model_requests == 1
    assert len(calls) == 1


def test_server_prompt_usage_must_match_presend_accepted_tokenizer_count() -> None:
    messages = _messages()
    observation = adapter.TokenizerObservation(
        messages_sha256=adapter.message_identity(messages),
        rendered_prompt_sha256="b" * 64,
        prompt_token_count=25,
    )

    def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        _ = (url, payload)
        return {
            "usage": {"prompt_tokens": 26},
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": '{"decision":"answer"}'},
                }
            ],
        }

    request_adapter = adapter.OneShotVllmRequestAdapter(
        tokenizer=_FakeTokenizer(observation),
        post_json=post_json,
        generation_contract=_generation(_response_format()),
        response_format=_response_format(),
        budget=adapter.RequestBudget(),
    )

    with pytest.raises(adapter.AcceptedRuntimeRequestAdapterError) as exc_info:
        request_adapter.send(
            request_id="request-1",
            url="http://127.0.0.1:8001/v1/chat/completions",
            messages=messages,
            cache_salt="c" * 64,
        )

    assert exc_info.value.error_code == "V2_SERVER_TOKEN_COUNT_MISMATCH"


def test_success_receipt_binds_exact_message_and_server_token_counts() -> None:
    messages = _messages()
    observation = adapter.TokenizerObservation(
        messages_sha256=adapter.message_identity(messages),
        rendered_prompt_sha256="b" * 64,
        prompt_token_count=25,
    )
    content = '{"decision":"answer"}'

    def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        _ = (url, payload)
        return {
            "usage": {"prompt_tokens": 25},
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": content},
                }
            ],
        }

    budget = adapter.RequestBudget()
    request_adapter = adapter.OneShotVllmRequestAdapter(
        tokenizer=_FakeTokenizer(observation),
        post_json=post_json,
        generation_contract=_generation(_response_format()),
        response_format=_response_format(),
        budget=budget,
    )
    response, receipt = request_adapter.send(
        request_id="request-1",
        url="http://127.0.0.1:8002/v1/chat/completions",
        messages=messages,
        cache_salt="c" * 64,
    )

    assert response["usage"] == {"prompt_tokens": 25}
    assert receipt.attempt_sequence == 1
    assert receipt.prompt_token_count == 25
    assert receipt.server_usage_prompt_tokens == 25
    assert receipt.messages_sha256 == observation.messages_sha256
    assert receipt.rendered_prompt_sha256 == observation.rendered_prompt_sha256
    assert receipt.output_sha256 == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert receipt.raw_prompt_retained is False
    assert receipt.raw_output_retained is False


def test_external_or_unfrozen_request_destination_is_rejected_before_transport() -> None:
    messages = _messages()
    observation = adapter.TokenizerObservation(
        messages_sha256=adapter.message_identity(messages),
        rendered_prompt_sha256="b" * 64,
        prompt_token_count=25,
    )
    calls = 0

    def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"url": url, "payload": payload}

    request_adapter = adapter.OneShotVllmRequestAdapter(
        tokenizer=_FakeTokenizer(observation),
        post_json=post_json,
        generation_contract=_generation(_response_format()),
        response_format=_response_format(),
        budget=adapter.RequestBudget(),
    )

    with pytest.raises(adapter.AcceptedRuntimeRequestAdapterError) as exc_info:
        request_adapter.send(
            request_id="request-1",
            url="https://example.com/v1/chat/completions",
            messages=messages,
            cache_salt="c" * 64,
        )

    assert exc_info.value.error_code == "V2_REQUEST_DESTINATION_INVALID"
    assert request_adapter.budget.attempted_model_requests == 0
    assert calls == 0


def test_sidecar_protocol_binds_exact_identity_and_message_count(
    tmp_path: Path,
) -> None:
    target_python = tmp_path / "python"
    target_python.write_text("fake", encoding="utf-8")
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    messages = _messages()
    messages_sha = adapter.message_identity(messages)
    ready = (
        adapter.canonical_json(
            {
                "status": "READY",
                "transformers": "5.14.1",
                "tokenizer_class": "Qwen2Tokenizer",
                "chat_template_sha256": adapter.EXPECTED_CHAT_TEMPLATE_SHA256,
            }
        )
        + "\n"
    )
    counted = (
        adapter.canonical_json(
            {
                "status": "COUNTED",
                "prompt_token_count": 25,
                "messages_sha256": messages_sha,
                "rendered_prompt_sha256": "d" * 64,
                "token_id_parity": True,
            }
        )
        + "\n"
    )
    process = _FakeProcess([ready, counted])
    factory_calls: list[dict[str, Any]] = []

    def process_factory(*args: Any, **kwargs: Any) -> subprocess.Popen[str]:
        factory_calls.append({"args": args, "kwargs": kwargs})
        return process  # type: ignore[return-value]

    sidecar = adapter.AcceptedTokenizerSidecar(
        target_python,
        snapshot,
        process_factory=process_factory,
    )

    assert sidecar.count(messages) == 25
    observation = sidecar.observation_for(messages)
    assert observation.prompt_token_count == 25
    assert observation.messages_sha256 == messages_sha
    assert observation.rendered_prompt_sha256 == "d" * 64
    assert process.stdin.values == [adapter.canonical_json({"messages": messages}) + "\n"]
    assert sidecar.close() == 0
    assert len(factory_calls) == 1
    env = factory_calls[0]["kwargs"]["env"]
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["PYTHONNOUSERSITE"] == "1"


def test_sidecar_source_retains_batch_encoding_and_rendered_token_parity_guards() -> None:
    assert adapter.tokenizer_sidecar_contains_required_guards() is True
    assert len(adapter.tokenizer_sidecar_source_sha256()) == 64
