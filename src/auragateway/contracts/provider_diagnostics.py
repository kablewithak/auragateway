"""Metadata-safe provider failure diagnostics for protected local evidence."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class ProviderFailureDiagnostic(BaseModel):
    """Content-free local record for one provider-boundary failure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
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

    @field_validator("request_id_sha256", "provider_request_id_sha256")
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
