"""Provider-neutral request, result, and safe prompt-summary contracts."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class ProviderName(StrEnum):
    """Provider or local-runtime identity represented by a typed adapter."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"
    UNAVAILABLE = "unavailable"


class ProviderInvocationStatus(StrEnum):
    """Terminal state of one provider invocation."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProviderErrorCode(StrEnum):
    """Safe provider-boundary failures available to retry and routing policy."""

    FIXTURE_NOT_FOUND = "PROVIDER_FIXTURE_NOT_FOUND"
    REQUEST_MISMATCH = "PROVIDER_REQUEST_MISMATCH"
    TIMEOUT = "PROVIDER_TIMEOUT"
    UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    CONNECTION_FAILED = "PROVIDER_CONNECTION_FAILED"
    AUTHENTICATION_FAILED = "PROVIDER_AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PROVIDER_PERMISSION_DENIED"
    RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    MODEL_NOT_AVAILABLE = "PROVIDER_MODEL_NOT_AVAILABLE"
    SDK_UNAVAILABLE = "PROVIDER_SDK_UNAVAILABLE"
    CONFIGURATION_MISMATCH = "PROVIDER_CONFIGURATION_MISMATCH"
    REQUEST_REJECTED = "PROVIDER_REQUEST_REJECTED"
    AMBIGUOUS_RESPONSE = "PROVIDER_RESPONSE_AMBIGUOUS"
    INVALID_RESPONSE = "PROVIDER_RESPONSE_INVALID"


class ProviderInvocationRequest(BaseModel):
    """Metadata-only provider request used by deterministic and live adapters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    request_id: str
    fixture_id: str
    provider: ProviderName
    model_alias: str
    static_prefix_fingerprint: str
    input_token_count: int = Field(ge=0)
    output_token_budget: int = Field(gt=0)

    @field_validator("request_id", "fixture_id", "model_alias")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("provider identifiers must use stable lowercase characters")
        return value

    @field_validator("static_prefix_fingerprint")
    @classmethod
    def validate_prefix_fingerprint(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("static_prefix_fingerprint must be lowercase SHA-256")
        return value


class ProtectedPromptSummary(BaseModel):
    """Safe prompt metadata that contains digests and byte counts only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    system_sha256: str
    user_sha256: str
    total_bytes: int = Field(gt=0, le=200_000)

    @field_validator("system_sha256", "user_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("prompt summaries require lowercase SHA-256 digests")
        return value


class ProviderInvocationResult(BaseModel):
    """Metadata-safe result emitted after raw provider payload handling is complete."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    request_id: str
    provider: ProviderName
    model_alias: str
    status: ProviderInvocationStatus
    output_sha256: str | None = None
    error_code: ProviderErrorCode | None = None
    retryable: bool = False

    @field_validator("request_id", "model_alias")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("provider result identifiers must use stable lowercase characters")
        return value

    @field_validator("output_sha256")
    @classmethod
    def validate_output_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("output_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_terminal_state(self) -> ProviderInvocationResult:
        if self.status is ProviderInvocationStatus.SUCCEEDED:
            if self.output_sha256 is None or self.error_code is not None or self.retryable:
                raise ValueError("successful provider results require only an output digest")
            return self
        if self.output_sha256 is not None or self.error_code is None:
            raise ValueError("failed provider results require an error code and no output digest")
        return self
