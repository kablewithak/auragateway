"""OpenRouter adapter with fixture-first route and cache telemetry reconciliation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from auragateway.contracts.openrouter import (
    OpenRouterCachedInputTelemetry,
    OpenRouterCacheFieldObservation,
    OpenRouterCacheObservation,
    OpenRouterCacheObservationState,
    OpenRouterGenerationReconciliationState,
    OpenRouterInvocationRequest,
    OpenRouterInvocationResult,
    OpenRouterRouteMetadata,
)
from auragateway.contracts.provider import ProviderErrorCode
from auragateway.providers.base import (
    LiveProviderError,
    ProtectedProviderOutput,
    ProtectedProviderPrompt,
)

OPENROUTER_MODEL_ID = "tencent/hy3:free"
OPENROUTER_MODEL_ALIAS = "openrouter-hy3-free"
OPENROUTER_ADAPTER_VERSION = "openrouter-chat-completions-v1"
OPENROUTER_TELEMETRY_AUTHORITY = "openrouter-normalized-usage-v1"


class _OpenRouterTransport(Protocol):
    def create_chat(
        self,
        *,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        """Return one decoded OpenRouter chat-completion response."""

    def get_generation(
        self,
        *,
        generation_id: str,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        """Return decoded generation metadata for the supplied completion ID."""


@dataclass(frozen=True, slots=True, repr=False)
class OpenRouterLiveInvocation:
    """One OpenRouter call with protected prompt and sticky-session content."""

    request: OpenRouterInvocationRequest
    prompt: ProtectedProviderPrompt = field(repr=False)
    session_id: str = field(repr=False)
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.session_id.strip() or len(self.session_id) > 256:
            raise ValueError("OpenRouter session IDs must contain 1 to 256 characters")
        if not 0 < self.timeout_seconds <= 120:
            raise ValueError("OpenRouter timeout must be greater than zero and at most 120 seconds")

    @property
    def session_id_sha256(self) -> str:
        return hashlib.sha256(self.session_id.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class OpenRouterProviderCall:
    """Extensible adapter result that does not mutate the legacy provider enum."""

    result: OpenRouterInvocationResult
    telemetry: OpenRouterCachedInputTelemetry
    observation: OpenRouterCacheObservation
    protected_output: ProtectedProviderOutput = field(repr=False)


class _PromptTokenDetails(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    cached_tokens: int | None = Field(default=None, ge=0)
    cache_write_tokens: int | None = Field(default=None, ge=0)


class _Usage(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    prompt_tokens_details: _PromptTokenDetails | None = None


class _Message(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    content: str | None = None


class _Choice(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    message: _Message


class _CompletionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    choices: tuple[_Choice, ...] = Field(min_length=1)
    usage: _Usage | None = None


class _GenerationData(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    provider_name: str = Field(min_length=1)
    session_id: str | None = None
    native_tokens_cached: int | None = Field(default=None, ge=0)
    cache_discount: Decimal | None = None


class _GenerationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    data: _GenerationData


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _observe_numeric_field(
    payload: Mapping[str, object] | None,
    field_name: str,
) -> OpenRouterCacheFieldObservation:
    if payload is None or field_name not in payload:
        return OpenRouterCacheFieldObservation(
            field_name=field_name,
            field_present=False,
            state=OpenRouterCacheObservationState.FIELD_ABSENT,
            value=None,
        )
    value = payload[field_name]
    if value is None:
        return OpenRouterCacheFieldObservation(
            field_name=field_name,
            field_present=True,
            state=OpenRouterCacheObservationState.FIELD_NULL,
            value=None,
        )
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LiveProviderError(
            ProviderErrorCode.INVALID_RESPONSE,
            "OpenRouter returned a cache field with an invalid numeric type.",
            retryable=False,
        )
    return OpenRouterCacheFieldObservation(
        field_name=field_name,
        field_present=True,
        state=(
            OpenRouterCacheObservationState.OBSERVED_ZERO
            if value == 0
            else OpenRouterCacheObservationState.OBSERVED_POSITIVE
        ),
        value=value,
    )


def _build_payload(invocation: OpenRouterLiveInvocation) -> Mapping[str, object]:
    return {
        "model": OPENROUTER_MODEL_ID,
        "messages": [
            {"role": "system", "content": invocation.prompt.system_prompt},
            {"role": "user", "content": invocation.prompt.user_prompt},
        ],
        "session_id": invocation.session_id,
        "max_completion_tokens": invocation.request.output_token_budget,
        "temperature": 0.0,
        "stream": False,
        "provider": {
            "data_collection": "deny",
            "zdr": True,
        },
    }


class OpenRouterProviderAdapter:
    """Map OpenRouter calls into an extensible typed provider envelope."""

    def __init__(self, transport: _OpenRouterTransport) -> None:
        self._transport = transport

    def invoke(self, invocation: OpenRouterLiveInvocation) -> OpenRouterProviderCall:
        """Replay one bounded transport call without credential or network ownership."""

        payload = _build_payload(invocation)
        provider_policy = _mapping(payload.get("provider"))
        if provider_policy != {"data_collection": "deny", "zdr": True}:
            raise LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "OpenRouter privacy controls are not fail-closed.",
                retryable=False,
            )
        if "order" in provider_policy:
            raise LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "Manual provider order is prohibited for the affinity experiment.",
                retryable=False,
            )

        completion_payload = self._transport.create_chat(
            payload=payload,
            timeout_seconds=invocation.timeout_seconds,
        )
        try:
            completion = _CompletionResponse.model_validate(completion_payload)
        except ValidationError as exc:
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouter returned a completion that failed typed validation.",
                retryable=False,
            ) from exc
        output_text = completion.choices[0].message.content
        if output_text is None or not output_text.strip():
            raise LiveProviderError(
                ProviderErrorCode.AMBIGUOUS_RESPONSE,
                "OpenRouter returned no usable assistant content.",
                retryable=False,
            )

        usage_payload = _mapping(completion_payload.get("usage"))
        details_payload = (
            _mapping(usage_payload.get("prompt_tokens_details"))
            if usage_payload is not None
            else None
        )
        read = _observe_numeric_field(details_payload, "cached_tokens")
        write = _observe_numeric_field(details_payload, "cache_write_tokens")

        generation_payload = self._transport.get_generation(
            generation_id=completion.id,
            timeout_seconds=invocation.timeout_seconds,
        )
        try:
            generation = _GenerationResponse.model_validate(generation_payload).data
        except ValidationError as exc:
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouter generation metadata failed typed validation.",
                retryable=False,
            ) from exc
        if generation.id != completion.id or generation.model != completion.model:
            raise LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "OpenRouter completion and generation identities do not reconcile.",
                retryable=False,
            )
        if generation.session_id != invocation.session_id:
            raise LiveProviderError(
                ProviderErrorCode.CONFIGURATION_MISMATCH,
                "OpenRouter generation metadata does not preserve the requested session.",
                retryable=False,
            )
        if (
            read.value is not None
            and generation.native_tokens_cached is not None
            and read.value != generation.native_tokens_cached
        ):
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouter completion and generation cache values do not reconcile.",
                retryable=False,
            )
        reconciliation = (
            OpenRouterGenerationReconciliationState.MATCHED
            if generation.native_tokens_cached is not None
            else OpenRouterGenerationReconciliationState.NATIVE_CACHE_VALUE_UNAVAILABLE
        )

        usage = completion.usage
        protected_output = ProtectedProviderOutput(text=output_text)
        result = OpenRouterInvocationResult(
            request_id=invocation.request.request_id,
            output_sha256=protected_output.sha256,
        )
        telemetry = OpenRouterCachedInputTelemetry(
            fixture_id=invocation.request.fixture_id,
            input_tokens=usage.prompt_tokens if usage is not None else None,
            cached_input_tokens=read.value,
            cache_write_input_tokens=write.value,
            output_tokens=usage.completion_tokens if usage is not None else None,
        )
        route = OpenRouterRouteMetadata(
            resolved_model=completion.model,
            upstream_provider=generation.provider_name,
            generation_id_sha256=hashlib.sha256(completion.id.encode("utf-8")).hexdigest(),
            session_id_sha256=invocation.session_id_sha256,
            completion_payload_sha256=_canonical_sha256(completion_payload),
            generation_payload_sha256=_canonical_sha256(generation_payload),
            native_tokens_cached=generation.native_tokens_cached,
            cache_discount=generation.cache_discount,
            reconciliation_state=reconciliation,
        )
        return OpenRouterProviderCall(
            result=result,
            telemetry=telemetry,
            observation=OpenRouterCacheObservation(read=read, write=write, route=route),
            protected_output=protected_output,
        )


__all__ = [
    "OPENROUTER_ADAPTER_VERSION",
    "OPENROUTER_MODEL_ALIAS",
    "OPENROUTER_MODEL_ID",
    "OPENROUTER_TELEMETRY_AUTHORITY",
    "OpenRouterLiveInvocation",
    "OpenRouterProviderAdapter",
    "OpenRouterProviderCall",
]
