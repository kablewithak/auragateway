"""Metadata-safe provider failure diagnostics for protected local evidence."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.provider import ProviderErrorCode, ProviderName

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SAFE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,96}$")


class ProviderFailureFamily(StrEnum):
    """Bounded provider failure families used for local diagnosis."""

    REQUEST_REJECTED = "request_rejected"
    RESPONSE_SCHEMA_INVALID = "response_schema_invalid"
    ASSISTANT_CONTENT_MISSING = "assistant_content_missing"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    MODEL_UNAVAILABLE = "model_unavailable"
    CONNECTION_FAILED = "connection_failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    UNKNOWN_PROVIDER_EXCEPTION = "unknown_provider_exception"


class AssistantContentState(StrEnum):
    """Observed visible assistant-content state without retaining the content."""

    NULL = "null"
    EMPTY = "empty"
    WHITESPACE = "whitespace"


class ProviderFinishReason(StrEnum):
    """Allowlisted provider finish reasons safe for protected diagnostics."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    FUNCTION_CALL = "function_call"


class ProviderFailureDiagnostic(BaseModel):
    """Content-free local record for one provider-boundary failure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.1.0"] = "1.1.0"
    provider: Literal[ProviderName.GROQ] = ProviderName.GROQ
    model_alias: str = Field(min_length=3, max_length=96)
    request_id_sha256: str
    family: ProviderFailureFamily
    exception_class_allowlisted: str | None = None
    http_status_code: int | None = Field(default=None, ge=100, le=599)
    provider_error_type_allowlisted: str | None = None
    provider_error_code_allowlisted: str | None = None
    provider_error_param_allowlisted: str | None = None
    provider_request_id_sha256: str | None = None
    retryable: bool
    mapped_provider_error_code: ProviderErrorCode
    response_id_sha256: str | None = None
    response_choice_count: int | None = Field(default=None, ge=0, le=16)
    response_finish_reason_allowlisted: ProviderFinishReason | None = None
    assistant_content_state: AssistantContentState | None = None
    response_usage_present: bool | None = None
    response_completion_tokens: int | None = Field(default=None, ge=0)
    reasoning_present: bool | None = None
    reasoning_byte_count: int | None = Field(default=None, ge=0, le=200_000)
    tool_call_count: int | None = Field(default=None, ge=0, le=128)
    refusal_present: bool | None = None
    refusal_byte_count: int | None = Field(default=None, ge=0, le=200_000)

    @field_validator("request_id_sha256", "provider_request_id_sha256", "response_id_sha256")
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("provider failure digests must be lowercase SHA-256")
        return value

    @field_validator(
        "exception_class_allowlisted",
        "provider_error_type_allowlisted",
        "provider_error_code_allowlisted",
        "provider_error_param_allowlisted",
    )
    @classmethod
    def validate_allowlisted_token(cls, value: str | None) -> str | None:
        if value is not None and _SAFE_TOKEN_PATTERN.fullmatch(value) is None:
            raise ValueError("provider failure metadata must use bounded safe tokens")
        return value

    @model_validator(mode="after")
    def validate_response_shape(self) -> ProviderFailureDiagnostic:
        response_shape_values = (
            self.response_id_sha256,
            self.response_choice_count,
            self.response_finish_reason_allowlisted,
            self.assistant_content_state,
            self.response_usage_present,
            self.response_completion_tokens,
            self.reasoning_present,
            self.reasoning_byte_count,
            self.tool_call_count,
            self.refusal_present,
            self.refusal_byte_count,
        )
        has_response_shape = any(value is not None for value in response_shape_values)
        if self.family is not ProviderFailureFamily.ASSISTANT_CONTENT_MISSING:
            if has_response_shape:
                raise ValueError(
                    "response-shape metadata is reserved for assistant-content-missing failures"
                )
            return self

        required_values = (
            self.response_choice_count,
            self.assistant_content_state,
            self.response_usage_present,
            self.reasoning_present,
            self.reasoning_byte_count,
            self.tool_call_count,
            self.refusal_present,
            self.refusal_byte_count,
        )
        if any(value is None for value in required_values):
            raise ValueError(
                "assistant-content-missing failures require complete response-shape metadata"
            )
        if self.response_choice_count is not None and self.response_choice_count < 1:
            raise ValueError("assistant-content-missing failures require at least one choice")
        if self.response_usage_present is False and self.response_completion_tokens is not None:
            raise ValueError("completion tokens require provider usage metadata")
        if self.reasoning_present is True and self.reasoning_byte_count == 0:
            raise ValueError("present reasoning requires a positive byte count")
        if self.refusal_present is True and self.refusal_byte_count == 0:
            raise ValueError("present refusal metadata requires a positive byte count")
        return self
