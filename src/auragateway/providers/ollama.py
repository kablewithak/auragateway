"""Ollama local-runtime adapter with typed prompt-evaluation timing evidence."""

from __future__ import annotations

import hashlib
import json
import math
import socket
from collections.abc import Mapping
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationResult,
    ProviderInvocationStatus,
    ProviderName,
)
from auragateway.contracts.telemetry import LocalPromptEvaluationTelemetry
from auragateway.providers.base import LiveProviderError, LiveProviderInvocation, ProviderCall

OLLAMA_MODEL_ID = "llama3.2:3b"
OLLAMA_MODEL_ALIAS = "ollama-llama3.2-3b"
OLLAMA_ADAPTER_VERSION = "ollama-generate-v1"
OLLAMA_DEFAULT_ENDPOINT = "http://localhost:11434/api/generate"


class _OllamaTransport(Protocol):
    def generate(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        """Send one bounded local generation request."""


class _UrllibOllamaTransport:
    def generate(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        body = json.dumps(dict(payload), separators=(",", ":")).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            parsed = json.loads(response.read().decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Ollama response must be a JSON object")
        return cast(dict[str, object], parsed)


class _OllamaResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    model: str
    response: str
    done: bool
    done_reason: str | None = None
    total_duration: int | None = Field(default=None, ge=0)
    prompt_eval_count: int | None = Field(default=None, ge=0)
    prompt_eval_duration: int | None = Field(default=None, ge=0)
    eval_count: int | None = Field(default=None, ge=0)


def _nanoseconds_to_ms(value: int | None) -> int | None:
    if value is None:
        return None
    if value == 0:
        return 0
    return math.ceil(value / 1_000_000)


def _map_ollama_exception(exc: Exception) -> LiveProviderError:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return LiveProviderError(
            ProviderErrorCode.TIMEOUT,
            "The Ollama request exceeded the configured timeout.",
            retryable=True,
        )
    if isinstance(exc, HTTPError):
        if exc.code == 404:
            return LiveProviderError(
                ProviderErrorCode.MODEL_NOT_AVAILABLE,
                "The configured Ollama model was not available locally.",
                retryable=False,
            )
        return LiveProviderError(
            ProviderErrorCode.UNAVAILABLE,
            "Ollama returned a local runtime HTTP failure.",
            retryable=exc.code >= 500,
        )
    if isinstance(exc, URLError):
        return LiveProviderError(
            ProviderErrorCode.CONNECTION_FAILED,
            "The local Ollama API could not be reached.",
            retryable=True,
        )
    if isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError, ValueError)):
        return LiveProviderError(
            ProviderErrorCode.INVALID_RESPONSE,
            "Ollama returned a response that could not be validated safely.",
            retryable=False,
        )
    return LiveProviderError(
        ProviderErrorCode.UNAVAILABLE,
        "The Ollama invocation failed before typed telemetry was produced.",
        retryable=False,
    )


class OllamaProviderAdapter:
    """Map the local Ollama generate API into local timing semantics only."""

    def __init__(
        self,
        transport: _OllamaTransport | None = None,
        endpoint: str = OLLAMA_DEFAULT_ENDPOINT,
    ) -> None:
        self._transport = transport or _UrllibOllamaTransport()
        self._endpoint = endpoint

    def invoke(self, invocation: LiveProviderInvocation) -> ProviderCall:
        """Execute one local request without representing timing as cached-token evidence."""

        request = invocation.request
        if request.provider is not ProviderName.OLLAMA or request.model_alias != OLLAMA_MODEL_ALIAS:
            raise LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "The invocation does not match the configured Ollama adapter identity.",
                retryable=False,
            )
        payload: dict[str, object] = {
            "model": OLLAMA_MODEL_ID,
            "system": invocation.prompt.system_prompt,
            "prompt": invocation.prompt.user_prompt,
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": 0,
                "num_predict": request.output_token_budget,
            },
        }
        try:
            raw_response = self._transport.generate(
                endpoint=self._endpoint,
                payload=payload,
                timeout_seconds=invocation.timeout_seconds,
            )
            response = _OllamaResponse.model_validate(raw_response)
        except LiveProviderError:
            raise
        except Exception as exc:
            raise _map_ollama_exception(exc) from exc

        if response.model != OLLAMA_MODEL_ID:
            raise LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "Ollama returned a model identity that differs from the configured model.",
                retryable=False,
            )
        if not response.done or not response.response.strip():
            raise LiveProviderError(
                ProviderErrorCode.AMBIGUOUS_RESPONSE,
                "Ollama did not return one completed assistant response.",
                retryable=False,
            )

        telemetry = LocalPromptEvaluationTelemetry(
            fixture_id=request.fixture_id,
            provider=ProviderName.OLLAMA,
            model_alias=request.model_alias,
            prompt_eval_count=response.prompt_eval_count,
            prompt_eval_duration_ms=_nanoseconds_to_ms(response.prompt_eval_duration),
            output_eval_count=response.eval_count,
            total_duration_ms=_nanoseconds_to_ms(response.total_duration),
        )
        result = ProviderInvocationResult(
            request_id=request.request_id,
            provider=ProviderName.OLLAMA,
            model_alias=request.model_alias,
            status=ProviderInvocationStatus.SUCCEEDED,
            output_sha256=hashlib.sha256(response.response.encode("utf-8")).hexdigest(),
        )
        return ProviderCall(result=result, telemetry=telemetry)
