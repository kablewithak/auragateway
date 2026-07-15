"""Provider-neutral worker client contracts for local A/B/C runtime integration."""

from __future__ import annotations

import math
import re
from contextlib import suppress
from datetime import datetime
from enum import StrEnum
from typing import Literal, Protocol, TypeVar, runtime_checkable
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import (
    LocalABCContract,
    WorkerId,
    WorkerIdentity,
)
from auragateway.local_abc.route_scheduler import TurnIndex

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_METRIC_NAME_PATTERN = re.compile(r"^[A-Za-z_:][A-Za-z0-9_:.-]{0,199}$")
_LABEL_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class WorkerClientOperation(StrEnum):
    """Operations exposed by every worker client implementation."""

    HEALTH = "health"
    INVOKE = "invoke"
    METRICS = "metrics"
    RESET_CACHE = "reset_cache"
    IDENTITY = "identity"


class WorkerClientErrorCode(StrEnum):
    """Machine-readable failures at the worker-client boundary."""

    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    INVALID_CONFIG = "INVALID_CONFIG"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    WORKER_ID_MISMATCH = "WORKER_ID_MISMATCH"
    REQUEST_ID_MISMATCH = "REQUEST_ID_MISMATCH"


class WorkerClientError(RuntimeError):
    """Bounded worker-client failure without raw request or response disclosure."""

    def __init__(
        self,
        *,
        operation: WorkerClientOperation,
        code: WorkerClientErrorCode,
        safe_detail: str,
    ) -> None:
        self.operation = operation
        self.code = code
        self.safe_detail = safe_detail
        super().__init__(f"{operation.value}:{code.value}: {safe_detail}")


class WorkerClientConfig(LocalABCContract):
    """Immutable transport configuration with explicit no-retry policy."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    worker_id: WorkerId
    base_url: str
    connect_timeout_seconds: float = Field(gt=0, le=60)
    read_timeout_seconds: float = Field(gt=0, le=300)
    max_attempts: Literal[1] = 1
    verify_tls: bool = True

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("worker base_url must use http or https")
        if parsed.hostname is None or parsed.port is None:
            raise ValueError("worker base_url must include a hostname and explicit port")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("worker base_url must not contain credentials")
        if parsed.query or parsed.fragment:
            raise ValueError("worker base_url must not contain query or fragment components")
        normalized_path = parsed.path.rstrip("/")
        if normalized_path:
            raise ValueError("worker base_url must not contain an endpoint path")
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"


class WorkerHealthState(StrEnum):
    """Observed worker readiness without inventing health from missing evidence."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class WorkerHealth(LocalABCContract):
    """One worker health observation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    worker_id: WorkerId
    checked_at: datetime
    state: WorkerHealthState
    ready_for_invocation: bool
    latency_ms: float = Field(ge=0)
    safe_detail: str | None = Field(default=None, min_length=1, max_length=300)

    @field_validator("checked_at")
    @classmethod
    def validate_checked_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checked_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_health_semantics(self) -> WorkerHealth:
        healthy = self.state is WorkerHealthState.HEALTHY
        if self.ready_for_invocation != healthy:
            raise ValueError("ready_for_invocation must exactly match healthy state")
        if self.state is not WorkerHealthState.HEALTHY and self.safe_detail is None:
            raise ValueError("non-healthy observations require safe_detail")
        return self


class WorkerInvocationSettings(LocalABCContract):
    """Frozen deterministic decoding settings for controlled execution."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    max_output_tokens: int = Field(gt=0, le=4096)
    temperature: float = Field(default=0.0, ge=0.0, le=0.0)
    top_p: float = Field(default=1.0, ge=1.0, le=1.0)
    stream: Literal[False] = False
    seed: int = Field(ge=0, le=2_147_483_647)


class WorkerInvocationRequest(LocalABCContract):
    """Typed model invocation request; raw content must never be logged."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: str
    trace_id: UUID
    trajectory_id: str
    turn_index: TurnIndex
    serialized_prefix: str = Field(min_length=1, repr=False)
    serialized_suffix: str = Field(min_length=1, repr=False)
    settings: WorkerInvocationSettings
    customer_data_used: Literal[False] = False
    paid_fallback_permitted: Literal[False] = False

    @field_validator("request_id", "trajectory_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("worker invocation identifiers must use stable lowercase characters")
        return value

    @field_validator("serialized_prefix", "serialized_suffix")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("worker invocation content must not be blank")
        return value


class WorkerFinishReason(StrEnum):
    """Normalized completion reason returned by a worker."""

    STOP = "stop"
    LENGTH = "length"
    ERROR = "error"


class WorkerInvocationResponse(LocalABCContract):
    """Typed worker completion with privacy-aware representation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: str
    worker_id: WorkerId
    completed_at: datetime
    output_text: str = Field(min_length=1, repr=False)
    finish_reason: WorkerFinishReason
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    end_to_end_latency_ms: float = Field(ge=0)

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("request_id must use stable lowercase characters")
        return value

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("completed_at must be timezone-aware")
        return value

    @field_validator("output_text")
    @classmethod
    def validate_output_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("output_text must not be blank")
        return value

    @model_validator(mode="after")
    def validate_usage(self) -> WorkerInvocationResponse:
        if self.finish_reason is WorkerFinishReason.ERROR and self.output_tokens != 0:
            raise ValueError("error responses cannot claim generated output tokens")
        if self.finish_reason is not WorkerFinishReason.ERROR and self.output_tokens == 0:
            raise ValueError("successful responses require at least one output token")
        return self


class WorkerMetricsFormat(StrEnum):
    """Transport-neutral raw metrics representation."""

    PROMETHEUS_TEXT = "prometheus_text"
    JSON = "json"


class WorkerMetricSample(LocalABCContract):
    """One raw metric series before semantic telemetry mapping."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    name: str
    value: float
    labels: tuple[tuple[str, str], ...] = ()

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if _METRIC_NAME_PATTERN.fullmatch(value) is None:
            raise ValueError("metric name contains unsupported characters")
        return value

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric value must be finite")
        return value

    @field_validator("labels")
    @classmethod
    def validate_labels(
        cls,
        value: tuple[tuple[str, str], ...],
    ) -> tuple[tuple[str, str], ...]:
        label_names = [name for name, _ in value]
        if any(_LABEL_NAME_PATTERN.fullmatch(name) is None for name in label_names):
            raise ValueError("metric label name contains unsupported characters")
        if len(label_names) != len(set(label_names)):
            raise ValueError("metric label names must be unique within one sample")
        if any(not label_value for _, label_value in value):
            raise ValueError("metric label values must not be empty")
        return tuple(sorted(value))


class WorkerMetricsSnapshot(LocalABCContract):
    """Raw worker metrics inventory without semantic cache conclusions."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    worker_id: WorkerId
    captured_at: datetime
    source_format: WorkerMetricsFormat
    raw_payload_sha256: str
    samples: tuple[WorkerMetricSample, ...] = ()

    @field_validator("captured_at")
    @classmethod
    def validate_captured_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        return value

    @field_validator("raw_payload_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("raw metrics payload digest must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_unique_series(self) -> WorkerMetricsSnapshot:
        identities = tuple((sample.name, sample.labels) for sample in self.samples)
        if len(identities) != len(set(identities)):
            raise ValueError("metrics snapshot cannot contain duplicate metric series")
        return self


class CacheResetState(StrEnum):
    """Explicit cache reset outcome; unsupported and unverified stay distinct."""

    VERIFIED = "verified"
    NOT_SUPPORTED = "not_supported"
    FAILED = "failed"
    NOT_VERIFIED = "not_verified"


class CacheResetRequest(LocalABCContract):
    """Idempotency-ready request for one worker-local cache reset."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: str
    requested_at: datetime
    scope: Literal["worker_prefix_cache"] = "worker_prefix_cache"
    require_verified: Literal[True] = True

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("cache reset request_id must use stable lowercase characters")
        return value

    @field_validator("requested_at")
    @classmethod
    def validate_requested_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("requested_at must be timezone-aware")
        return value


class CacheResetReceipt(LocalABCContract):
    """One explicit worker-local cache reset result."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: str
    worker_id: WorkerId
    completed_at: datetime
    state: CacheResetState
    verification_method: str | None = Field(default=None, min_length=1, max_length=120)
    safe_detail: str | None = Field(default=None, min_length=1, max_length=300)

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("cache reset receipt request_id must use stable lowercase characters")
        return value

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("completed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_reset_semantics(self) -> CacheResetReceipt:
        if self.state is CacheResetState.VERIFIED:
            if self.verification_method is None:
                raise ValueError("verified reset requires verification_method")
            if self.safe_detail is not None:
                raise ValueError("verified reset cannot contain failure detail")
            return self
        if self.safe_detail is None:
            raise ValueError("non-verified reset outcomes require safe_detail")
        if self.verification_method is not None:
            raise ValueError("non-verified reset outcomes cannot claim verification_method")
        return self


@runtime_checkable
class WorkerClient(Protocol):
    """Provider-neutral synchronous worker client interface."""

    @property
    def config(self) -> WorkerClientConfig:
        """Return immutable client configuration."""

    def health(self) -> WorkerHealth:
        """Return current health without inferring readiness from silence."""

    def invoke(self, request: WorkerInvocationRequest) -> WorkerInvocationResponse:
        """Invoke one deterministic model turn."""

    def metrics(self) -> WorkerMetricsSnapshot:
        """Return raw metric samples without semantic cache mapping."""

    def reset_cache(self, request: CacheResetRequest) -> CacheResetReceipt:
        """Attempt one explicit worker-local cache reset."""

    def identity(self) -> WorkerIdentity:
        """Return observed runtime, model, tokenizer, GPU, and port identity."""


ContractT = TypeVar("ContractT", bound=BaseModel)


class WorkerClientBoundary:
    """Strictly revalidate one client implementation without hidden retries."""

    def __init__(self, client: WorkerClient) -> None:
        self._client = client
        self._config = self._revalidate(
            WorkerClientConfig,
            client.config,
            operation=WorkerClientOperation.IDENTITY,
        )

    @property
    def config(self) -> WorkerClientConfig:
        """Return the strictly validated client configuration."""

        return self._config

    def health(self) -> WorkerHealth:
        value = self._call(WorkerClientOperation.HEALTH, self._client.health)
        validated = self._revalidate(
            WorkerHealth,
            value,
            operation=WorkerClientOperation.HEALTH,
        )
        self._require_worker(validated.worker_id, WorkerClientOperation.HEALTH)
        return validated

    def invoke(self, request: WorkerInvocationRequest) -> WorkerInvocationResponse:
        validated_request = self._revalidate(
            WorkerInvocationRequest,
            request,
            operation=WorkerClientOperation.INVOKE,
        )
        value = self._call(
            WorkerClientOperation.INVOKE,
            lambda: self._client.invoke(validated_request),
        )
        validated = self._revalidate(
            WorkerInvocationResponse,
            value,
            operation=WorkerClientOperation.INVOKE,
        )
        self._require_worker(validated.worker_id, WorkerClientOperation.INVOKE)
        if validated.request_id != validated_request.request_id:
            raise WorkerClientError(
                operation=WorkerClientOperation.INVOKE,
                code=WorkerClientErrorCode.REQUEST_ID_MISMATCH,
                safe_detail="worker response request_id does not match invocation request",
            )
        return validated

    def metrics(self) -> WorkerMetricsSnapshot:
        value = self._call(WorkerClientOperation.METRICS, self._client.metrics)
        validated = self._revalidate(
            WorkerMetricsSnapshot,
            value,
            operation=WorkerClientOperation.METRICS,
        )
        self._require_worker(validated.worker_id, WorkerClientOperation.METRICS)
        return validated

    def reset_cache(self, request: CacheResetRequest) -> CacheResetReceipt:
        validated_request = self._revalidate(
            CacheResetRequest,
            request,
            operation=WorkerClientOperation.RESET_CACHE,
        )
        value = self._call(
            WorkerClientOperation.RESET_CACHE,
            lambda: self._client.reset_cache(validated_request),
        )
        validated = self._revalidate(
            CacheResetReceipt,
            value,
            operation=WorkerClientOperation.RESET_CACHE,
        )
        self._require_worker(validated.worker_id, WorkerClientOperation.RESET_CACHE)
        if validated.request_id != validated_request.request_id:
            raise WorkerClientError(
                operation=WorkerClientOperation.RESET_CACHE,
                code=WorkerClientErrorCode.REQUEST_ID_MISMATCH,
                safe_detail="cache reset receipt request_id does not match reset request",
            )
        return validated

    def identity(self) -> WorkerIdentity:
        value = self._call(WorkerClientOperation.IDENTITY, self._client.identity)
        validated = self._revalidate(
            WorkerIdentity,
            value,
            operation=WorkerClientOperation.IDENTITY,
        )
        self._require_worker(validated.worker_id, WorkerClientOperation.IDENTITY)
        return validated

    def _require_worker(
        self,
        observed: WorkerId,
        operation: WorkerClientOperation,
    ) -> None:
        if observed is not self._config.worker_id:
            raise WorkerClientError(
                operation=operation,
                code=WorkerClientErrorCode.WORKER_ID_MISMATCH,
                safe_detail="worker response identity does not match client configuration",
            )

    @staticmethod
    def _call(operation: WorkerClientOperation, function: object) -> object:
        if not callable(function):
            raise WorkerClientError(
                operation=operation,
                code=WorkerClientErrorCode.INVALID_CONFIG,
                safe_detail="worker client operation is not callable",
            )

        failure: tuple[WorkerClientErrorCode, str] | None = None
        try:
            return function()
        except WorkerClientError:
            raise
        except TimeoutError:
            failure = (
                WorkerClientErrorCode.TIMEOUT,
                "worker operation exceeded its configured timeout",
            )
        except ConnectionError:
            failure = (
                WorkerClientErrorCode.CONNECTION_FAILED,
                "worker operation could not reach the configured endpoint",
            )

        code, safe_detail = failure
        raise WorkerClientError(
            operation=operation,
            code=code,
            safe_detail=safe_detail,
        )

    @staticmethod
    def _revalidate(
        model_type: type[ContractT],
        value: object,
        *,
        operation: WorkerClientOperation,
    ) -> ContractT:
        payload = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        validated: ContractT | None = None
        with suppress(ValidationError):
            validated = model_type.model_validate(payload)

        if validated is None:
            raise WorkerClientError(
                operation=operation,
                code=WorkerClientErrorCode.INVALID_RESPONSE,
                safe_detail="worker client contract failed strict boundary revalidation",
            )
        return validated
