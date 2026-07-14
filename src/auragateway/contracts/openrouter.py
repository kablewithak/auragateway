"""Typed OpenRouter invocation, route, and cache-observation contracts."""

from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class OpenRouterInvocationStatus(StrEnum):
    """Terminal adapter result state."""

    SUCCEEDED = "succeeded"


class OpenRouterCacheObservationState(StrEnum):
    """Presence-aware state for one normalized numeric cache field."""

    FIELD_ABSENT = "field_absent"
    FIELD_NULL = "field_null"
    OBSERVED_ZERO = "observed_zero"
    OBSERVED_POSITIVE = "observed_positive"


class OpenRouterGenerationReconciliationState(StrEnum):
    """Relationship between completion usage and generation metadata."""

    MATCHED = "matched"
    NATIVE_CACHE_VALUE_UNAVAILABLE = "native_cache_value_unavailable"


class OpenRouterInvocationRequest(BaseModel):
    """Metadata-only request for the extensible OpenRouter adapter seam."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: str
    fixture_id: str
    provider_id: Literal["openrouter"] = "openrouter"
    model_alias: Literal["openrouter-hy3-free"] = "openrouter-hy3-free"
    static_prefix_fingerprint: str
    input_token_count: int = Field(gt=0)
    output_token_budget: int = Field(gt=0, le=256)

    @field_validator("request_id", "fixture_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("OpenRouter identifiers require stable lowercase characters")
        return value

    @field_validator("static_prefix_fingerprint")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("static prefix fingerprint must be lowercase SHA-256")
        return value


class OpenRouterInvocationResult(BaseModel):
    """Metadata-safe OpenRouter result independent of the legacy provider enum."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: str
    provider_id: Literal["openrouter"] = "openrouter"
    model_alias: Literal["openrouter-hy3-free"] = "openrouter-hy3-free"
    status: Literal[OpenRouterInvocationStatus.SUCCEEDED] = OpenRouterInvocationStatus.SUCCEEDED
    output_sha256: str

    @field_validator("request_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("OpenRouter result IDs require stable lowercase characters")
        return value

    @field_validator("output_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("OpenRouter result requires lowercase SHA-256")
        return value


class OpenRouterCachedInputTelemetry(BaseModel):
    """OpenRouter normalized usage without pretending it is Tencent-direct telemetry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    fixture_id: str
    provider_id: Literal["openrouter"] = "openrouter"
    model_alias: Literal["openrouter-hy3-free"] = "openrouter-hy3-free"
    input_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    cache_write_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    telemetry_authority: Literal["openrouter_normalized_usage"] = "openrouter_normalized_usage"


class OpenRouterCacheFieldObservation(BaseModel):
    """One presence-aware normalized cache field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: Literal["cached_tokens", "cache_write_tokens"]
    field_present: bool
    state: OpenRouterCacheObservationState
    value: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_state(self) -> OpenRouterCacheFieldObservation:
        expected: tuple[bool, int | None]
        if self.state is OpenRouterCacheObservationState.FIELD_ABSENT:
            expected = (False, None)
        elif self.state is OpenRouterCacheObservationState.FIELD_NULL:
            expected = (True, None)
        elif self.state is OpenRouterCacheObservationState.OBSERVED_ZERO:
            expected = (True, 0)
        else:
            if self.value is None or self.value <= 0:
                raise ValueError("positive cache observations require a value greater than zero")
            expected = (True, self.value)
        if (self.field_present, self.value) != expected:
            raise ValueError("cache observation state does not match presence and value")
        return self


class OpenRouterRouteMetadata(BaseModel):
    """Public-safe route identity reconciled across two OpenRouter surfaces."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_model: Literal["tencent/hy3:free"] = "tencent/hy3:free"
    resolved_model: str = Field(min_length=3, max_length=200)
    upstream_provider: str = Field(min_length=1, max_length=120)
    generation_id_sha256: str
    session_id_sha256: str
    completion_payload_sha256: str
    generation_payload_sha256: str
    native_tokens_cached: int | None = Field(default=None, ge=0)
    cache_discount: Decimal | None = None
    reconciliation_state: OpenRouterGenerationReconciliationState
    telemetry_authority: Literal["openrouter_normalized_usage"] = "openrouter_normalized_usage"

    @field_validator(
        "generation_id_sha256",
        "session_id_sha256",
        "completion_payload_sha256",
        "generation_payload_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("OpenRouter route metadata requires lowercase SHA-256")
        return value


class OpenRouterCacheObservation(BaseModel):
    """Cache-read, cache-write, and route metadata for one adapter call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    read: OpenRouterCacheFieldObservation
    write: OpenRouterCacheFieldObservation
    route: OpenRouterRouteMetadata
    missing_interpreted_as_zero: Literal[False] = False
    direct_tencent_telemetry_claim_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_field_names(self) -> OpenRouterCacheObservation:
        if self.read.field_name != "cached_tokens":
            raise ValueError("read observation must bind cached_tokens")
        if self.write.field_name != "cache_write_tokens":
            raise ValueError("write observation must bind cache_write_tokens")
        return self
