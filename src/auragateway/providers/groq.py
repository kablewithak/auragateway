"""Groq live adapter with typed telemetry and metadata-safe failure diagnostics."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationResult,
    ProviderInvocationStatus,
    ProviderName,
)
from auragateway.contracts.provider_diagnostics import (
    ProviderFailureDiagnostic,
    ProviderFailureFamily,
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

_ALLOWED_EXCEPTION_CLASSES = frozenset(
    {
        "APIConnectionError",
        "APIStatusError",
        "APITimeoutError",
        "AuthenticationError",
        "BadRequestError",
        "ConflictError",
        "InternalServerError",
        "NotFoundError",
        "PermissionDeniedError",
        "RateLimitError",
        "UnprocessableEntityError",
        "AttributeError",
        "ValidationError",
    }
)

_ALLOWED_PROVIDER_ERROR_TYPES = frozenset(
    {
        "api_error",
        "authentication_error",
        "invalid_request_error",
        "not_found_error",
        "permission_error",
        "rate_limit_error",
        "server_error",
    }
)
_ALLOWED_PROVIDER_ERROR_CODES = frozenset(
    {
        "context_length_exceeded",
        "invalid_api_key",
        "invalid_value",
        "json_validate_failed",
        "model_not_found",
        "quota_exceeded",
        "rate_limit_exceeded",
        "requests_per_minute",
        "tokens_per_minute",
        "tool_use_failed",
        "unsupported_value",
    }
)
_ALLOWED_PROVIDER_ERROR_PARAMS = frozenset(
    {
        "max_completion_tokens",
        "messages",
        "model",
        "reasoning_effort",
        "response_format",
        "store",
        "stream",
        "temperature",
        "tool_choice",
        "tools",
    }
)


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


def _safe_status_code(exc: Exception) -> int | None:
    value = getattr(exc, "status_code", None)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if not 100 <= value <= 599:
        return None
    return value


def _classify_groq_exception(
    exc: Exception,
) -> tuple[ProviderFailureFamily, LiveProviderError]:
    name = type(exc).__name__
    status_code = _safe_status_code(exc)
    if name == "APITimeoutError":
        return (
            ProviderFailureFamily.TIMEOUT,
            LiveProviderError(
                ProviderErrorCode.TIMEOUT,
                "The Groq request exceeded the configured timeout.",
                retryable=True,
            ),
        )
    if name == "RateLimitError" or status_code == 429:
        return (
            ProviderFailureFamily.RATE_LIMITED,
            LiveProviderError(
                ProviderErrorCode.RATE_LIMITED,
                "Groq rejected the request because a rate or quota limit was reached.",
                retryable=True,
            ),
        )
    if name == "AuthenticationError" or status_code == 401:
        return (
            ProviderFailureFamily.AUTHENTICATION_FAILED,
            LiveProviderError(
                ProviderErrorCode.AUTHENTICATION_FAILED,
                "Groq rejected the supplied process credential.",
                retryable=False,
            ),
        )
    if name == "PermissionDeniedError" or status_code == 403:
        return (
            ProviderFailureFamily.PERMISSION_DENIED,
            LiveProviderError(
                ProviderErrorCode.PERMISSION_DENIED,
                "Groq denied access to the requested model or operation.",
                retryable=False,
            ),
        )
    if name == "NotFoundError" or status_code == 404:
        return (
            ProviderFailureFamily.MODEL_UNAVAILABLE,
            LiveProviderError(
                ProviderErrorCode.MODEL_NOT_AVAILABLE,
                "The configured Groq model was not available.",
                retryable=False,
            ),
        )
    if name == "APIConnectionError":
        return (
            ProviderFailureFamily.CONNECTION_FAILED,
            LiveProviderError(
                ProviderErrorCode.CONNECTION_FAILED,
                "The Groq API could not be reached.",
                retryable=True,
            ),
        )
    if name == "InternalServerError" or (isinstance(status_code, int) and status_code >= 500):
        return (
            ProviderFailureFamily.PROVIDER_UNAVAILABLE,
            LiveProviderError(
                ProviderErrorCode.UNAVAILABLE,
                "Groq returned a provider-side availability failure.",
                retryable=True,
            ),
        )
    if name in {"BadRequestError", "ConflictError", "UnprocessableEntityError"} or (
        isinstance(status_code, int) and 400 <= status_code < 500
    ):
        return (
            ProviderFailureFamily.REQUEST_REJECTED,
            LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "Groq rejected the request before returning usable assistant content.",
                retryable=False,
            ),
        )
    return (
        ProviderFailureFamily.UNKNOWN_PROVIDER_EXCEPTION,
        LiveProviderError(
            ProviderErrorCode.INVALID_RESPONSE,
            "The Groq request failed with an unsupported provider response.",
            retryable=False,
        ),
    )


def _map_groq_exception(exc: Exception) -> LiveProviderError:
    """Preserve the existing bounded public error mapping."""

    return _classify_groq_exception(exc)[1]


def _safe_token(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (str, int)):
        return None
    candidate = str(value)
    if not candidate or len(candidate) > 96:
        return None
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:/-")
    if any(character not in allowed for character in candidate):
        return None
    return candidate


def _allowlisted_provider_value(
    value: object,
    allowed_values: frozenset[str],
) -> str | None:
    token = _safe_token(value)
    if token not in allowed_values:
        return None
    return token


def _provider_error_fields(exc: Exception) -> tuple[str | None, str | None, str | None]:
    body = getattr(exc, "body", None)
    if not isinstance(body, Mapping):
        return None, None, None
    payload: Mapping[object, object] = body
    nested = body.get("error")
    if isinstance(nested, Mapping):
        payload = nested
    return (
        _allowlisted_provider_value(payload.get("type"), _ALLOWED_PROVIDER_ERROR_TYPES),
        _allowlisted_provider_value(payload.get("code"), _ALLOWED_PROVIDER_ERROR_CODES),
        _allowlisted_provider_value(payload.get("param"), _ALLOWED_PROVIDER_ERROR_PARAMS),
    )


def _provider_request_id_sha256(exc: Exception) -> str | None:
    request_id = getattr(exc, "request_id", None)
    if not isinstance(request_id, str) or not request_id:
        return None
    return hashlib.sha256(request_id.encode("utf-8")).hexdigest()


def _allowlisted_exception_class(exc: Exception | None) -> str | None:
    if exc is None:
        return None
    name = type(exc).__name__
    if name not in _ALLOWED_EXCEPTION_CLASSES:
        return None
    return name


def _duration_ms(total_time_seconds: float | None) -> int | None:
    if total_time_seconds is None:
        return None
    return round(total_time_seconds * 1_000)


class GroqProviderAdapter:
    """Map Groq calls into typed telemetry and protected local failure evidence."""

    def __init__(
        self,
        completion_client: _GroqCompletionClient | None = None,
        *,
        failure_diagnostic_path: Path | None = None,
    ) -> None:
        self._completion_client = completion_client
        self._failure_diagnostic_path = failure_diagnostic_path

    def _append_failure_diagnostic(self, diagnostic: ProviderFailureDiagnostic) -> None:
        path = self._failure_diagnostic_path
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(diagnostic.model_dump_json() + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise LiveProviderError(
                ProviderErrorCode.AMBIGUOUS_RESPONSE,
                "Provider failure diagnostic evidence could not be retained safely.",
                retryable=False,
            ) from exc

    def _retain_failure(
        self,
        invocation: LiveProviderInvocation,
        family: ProviderFailureFamily,
        error: LiveProviderError,
        exc: Exception | None = None,
    ) -> None:
        error_type, error_code, error_param = (
            _provider_error_fields(exc) if exc is not None else (None, None, None)
        )
        diagnostic = ProviderFailureDiagnostic(
            model_alias=invocation.request.model_alias,
            request_id_sha256=hashlib.sha256(
                invocation.request.request_id.encode("utf-8")
            ).hexdigest(),
            family=family,
            exception_class_allowlisted=_allowlisted_exception_class(exc),
            http_status_code=_safe_status_code(exc) if exc is not None else None,
            provider_error_type_allowlisted=error_type,
            provider_error_code_allowlisted=error_code,
            provider_error_param_allowlisted=error_param,
            provider_request_id_sha256=(
                _provider_request_id_sha256(exc) if exc is not None else None
            ),
            retryable=error.retryable,
            mapped_provider_error_code=error.error_code,
        )
        self._append_failure_diagnostic(diagnostic)

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
            family, error = _classify_groq_exception(exc)
            self._retain_failure(invocation, family, error, exc)
            raise error from exc

        try:
            response = _GroqResponse.model_validate(raw_response.model_dump())
        except (AttributeError, ValidationError) as exc:
            error = LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "Groq returned a response that failed typed adapter validation.",
                retryable=False,
            )
            self._retain_failure(
                invocation,
                ProviderFailureFamily.RESPONSE_SCHEMA_INVALID,
                error,
                exc,
            )
            raise error from exc
        if response.model != GROQ_MODEL_ID:
            error = LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "Groq returned a model identity that differs from the configured model.",
                retryable=False,
            )
            self._retain_failure(
                invocation,
                ProviderFailureFamily.RESPONSE_SCHEMA_INVALID,
                error,
            )
            raise error
        output_text = response.choices[0].message.content
        if output_text is None or not output_text.strip():
            error = LiveProviderError(
                ProviderErrorCode.AMBIGUOUS_RESPONSE,
                "Groq returned no usable assistant content.",
                retryable=False,
            )
            self._retain_failure(
                invocation,
                ProviderFailureFamily.ASSISTANT_CONTENT_MISSING,
                error,
            )
            raise error

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
