"""Groq live adapter with typed cached-token telemetry and protected output handling."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from typing import Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationResult,
    ProviderInvocationStatus,
    ProviderName,
)
from auragateway.contracts.telemetry import CachedInputDetailTelemetry
from auragateway.providers.base import (
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderOutput,
    ProviderCall,
)

GROQ_MODEL_ID = "openai/gpt-oss-20b"
GROQ_MODEL_ALIAS = "groq-gpt-oss-20b"
GROQ_ADAPTER_VERSION = "groq-chat-completions-v1"


class _ModelDumpable(Protocol):
    def model_dump(self) -> dict[str, object]:
        """Return the SDK response as a temporary in-memory mapping."""


class _GroqCompletionClient(Protocol):
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
    ) -> _ModelDumpable:
        """Create one non-streaming chat completion."""


class _GroqPromptTokenDetails(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    cached_tokens: int | None = Field(default=None, ge=0)


class _GroqUsage(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_time: float | None = Field(default=None, ge=0)
    prompt_tokens_details: _GroqPromptTokenDetails | None = None


class _GroqMessage(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    content: str | None = None


class _GroqChoice(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    message: _GroqMessage


class _GroqResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    model: str
    choices: tuple[_GroqChoice, ...] = Field(min_length=1)
    usage: _GroqUsage | None = None


def _build_completion_client(timeout_seconds: float) -> _GroqCompletionClient:
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key is None or not api_key.strip():
        raise LiveProviderError(
            ProviderErrorCode.AUTHENTICATION_FAILED,
            "GROQ_API_KEY is not available in the current process environment.",
            retryable=False,
        )
    try:
        from groq import Groq
    except ImportError as exc:
        raise LiveProviderError(
            ProviderErrorCode.SDK_UNAVAILABLE,
            "The pinned Groq SDK is not installed in the active environment.",
            retryable=False,
        ) from exc
    client = Groq(api_key=api_key, max_retries=0, timeout=timeout_seconds)
    return cast(_GroqCompletionClient, client.chat.completions)


def _map_groq_exception(exc: Exception) -> LiveProviderError:
    name = type(exc).__name__
    status_code = getattr(exc, "status_code", None)
    if name == "APITimeoutError":
        return LiveProviderError(
            ProviderErrorCode.TIMEOUT,
            "The Groq request exceeded the configured timeout.",
            retryable=True,
        )
    if name == "RateLimitError" or status_code == 429:
        return LiveProviderError(
            ProviderErrorCode.RATE_LIMITED,
            "Groq rejected the request because a rate or quota limit was reached.",
            retryable=True,
        )
    if name == "AuthenticationError" or status_code == 401:
        return LiveProviderError(
            ProviderErrorCode.AUTHENTICATION_FAILED,
            "Groq rejected the supplied process credential.",
            retryable=False,
        )
    if name == "PermissionDeniedError" or status_code == 403:
        return LiveProviderError(
            ProviderErrorCode.PERMISSION_DENIED,
            "Groq denied access to the requested model or operation.",
            retryable=False,
        )
    if name == "NotFoundError" or status_code == 404:
        return LiveProviderError(
            ProviderErrorCode.MODEL_NOT_AVAILABLE,
            "The configured Groq model was not available.",
            retryable=False,
        )
    if name == "APIConnectionError":
        return LiveProviderError(
            ProviderErrorCode.CONNECTION_FAILED,
            "The Groq API could not be reached.",
            retryable=True,
        )
    if isinstance(status_code, int) and status_code >= 500:
        return LiveProviderError(
            ProviderErrorCode.UNAVAILABLE,
            "Groq returned a provider-side availability failure.",
            retryable=True,
        )
    return LiveProviderError(
        ProviderErrorCode.INVALID_RESPONSE,
        "The Groq request failed with an unsupported provider response.",
        retryable=False,
    )


def _duration_ms(total_time_seconds: float | None) -> int | None:
    if total_time_seconds is None:
        return None
    return round(total_time_seconds * 1_000)


class GroqProviderAdapter:
    """Map Groq chat completions into frozen cached-input telemetry semantics."""

    def __init__(self, completion_client: _GroqCompletionClient | None = None) -> None:
        self._completion_client = completion_client

    def invoke(self, invocation: LiveProviderInvocation) -> ProviderCall:
        """Execute one bounded Groq request without exposing raw content publicly."""

        request = invocation.request
        if request.provider is not ProviderName.GROQ or request.model_alias != GROQ_MODEL_ALIAS:
            raise LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "The invocation does not match the configured Groq adapter identity.",
                retryable=False,
            )
        client = self._completion_client or _build_completion_client(invocation.timeout_seconds)
        try:
            raw_response = client.create(
                messages=(
                    {"role": "system", "content": invocation.prompt.system_prompt},
                    {"role": "user", "content": invocation.prompt.user_prompt},
                ),
                model=GROQ_MODEL_ID,
                max_completion_tokens=request.output_token_budget,
                temperature=0.0,
                stream=False,
                store=False,
                reasoning_effort="low",
            )
        except LiveProviderError:
            raise
        except Exception as exc:
            raise _map_groq_exception(exc) from exc

        try:
            response = _GroqResponse.model_validate(raw_response.model_dump())
        except (AttributeError, ValidationError) as exc:
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "Groq returned a response that failed typed adapter validation.",
                retryable=False,
            ) from exc
        if response.model != GROQ_MODEL_ID:
            raise LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "Groq returned a model identity that differs from the configured model.",
                retryable=False,
            )
        output_text = response.choices[0].message.content
        if output_text is None or not output_text.strip():
            raise LiveProviderError(
                ProviderErrorCode.AMBIGUOUS_RESPONSE,
                "Groq returned no usable assistant content.",
                retryable=False,
            )

        usage = response.usage
        details = usage.prompt_tokens_details if usage is not None else None
        telemetry = CachedInputDetailTelemetry(
            fixture_id=request.fixture_id,
            provider=ProviderName.GROQ,
            model_alias=request.model_alias,
            input_tokens=usage.prompt_tokens if usage is not None else None,
            cached_input_tokens=details.cached_tokens if details is not None else None,
            output_tokens=usage.completion_tokens if usage is not None else None,
            total_duration_ms=_duration_ms(usage.total_time) if usage is not None else None,
        )
        protected_output = ProtectedProviderOutput(output_text)
        result = ProviderInvocationResult(
            request_id=request.request_id,
            provider=ProviderName.GROQ,
            model_alias=request.model_alias,
            status=ProviderInvocationStatus.SUCCEEDED,
            output_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        )
        return ProviderCall(
            result=result,
            telemetry=telemetry,
            protected_output=protected_output,
        )
