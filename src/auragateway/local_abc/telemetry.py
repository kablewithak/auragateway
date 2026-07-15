"""Versioned raw-metric normalization for the controlled local A/B/C runtime."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import (
    CacheObservation,
    CacheObservationState,
    LocalABCContract,
    TelemetryObservation,
    WorkerIdentity,
)
from auragateway.local_abc.errors import LocalABCFailureCode
from auragateway.local_abc.worker_client import (
    WorkerInvocationResponse,
    WorkerMetricSample,
    WorkerMetricsFormat,
    WorkerMetricsSnapshot,
)

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$")
_LABEL_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")
_METRIC_NAME_PATTERN = re.compile(r"^[A-Za-z_:][A-Za-z0-9_:.-]{0,199}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class TelemetryMetricSemantic(StrEnum):
    """Normalized meanings supported by the local A/B/C telemetry boundary."""

    CACHED_PREFIX_TOKENS = "cached_prefix_tokens"
    NEWLY_COMPUTED_PREFILL_TOKENS = "newly_computed_prefill_tokens"
    PREFILL_DURATION_SECONDS = "prefill_duration_seconds"
    TIME_TO_FIRST_TOKEN_SECONDS = "time_to_first_token_seconds"


class TelemetryMetricValueKind(StrEnum):
    """How a raw metric sample becomes one per-request value."""

    COUNTER_DELTA = "counter_delta"
    GAUGE = "gauge"


class TelemetryAdapterErrorCode(StrEnum):
    """Machine-readable failures at the telemetry adapter boundary."""

    INVALID_PROFILE = "INVALID_PROFILE"
    INVALID_REQUEST = "INVALID_REQUEST"
    RUNTIME_VERSION_MISMATCH = "RUNTIME_VERSION_MISMATCH"
    WORKER_ID_MISMATCH = "WORKER_ID_MISMATCH"
    SNAPSHOT_ORDER_INVALID = "SNAPSHOT_ORDER_INVALID"
    SOURCE_FORMAT_MISMATCH = "SOURCE_FORMAT_MISMATCH"


class TelemetryAdapterError(ValueError):
    """Bounded telemetry-normalization failure without raw metric disclosure."""

    def __init__(self, code: TelemetryAdapterErrorCode, safe_detail: str) -> None:
        self.code = code
        self.safe_detail = safe_detail
        super().__init__(f"{code.value}: {safe_detail}")


class TelemetryMetricSelector(LocalABCContract):
    """Exact versioned binding from one raw series to one normalized semantic."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    semantic: TelemetryMetricSemantic
    metric_name: str = Field(min_length=1, max_length=200)
    labels: tuple[tuple[str, str], ...] = ()
    value_kind: TelemetryMetricValueKind

    @field_validator("metric_name")
    @classmethod
    def validate_metric_name(cls, value: str) -> str:
        if _METRIC_NAME_PATTERN.fullmatch(value) is None:
            raise ValueError("telemetry selector metric name contains unsupported characters")
        return value

    @field_validator("labels")
    @classmethod
    def validate_labels(
        cls,
        value: tuple[tuple[str, str], ...],
    ) -> tuple[tuple[str, str], ...]:
        names = [name for name, _ in value]
        if any(_LABEL_NAME_PATTERN.fullmatch(name) is None for name in names):
            raise ValueError("telemetry selector label name contains unsupported characters")
        if len(names) != len(set(names)):
            raise ValueError("telemetry selector label names must be unique")
        if any(not label_value for _, label_value in value):
            raise ValueError("telemetry selector label values must not be empty")
        return tuple(sorted(value))


class TelemetryMappingProfile(LocalABCContract):
    """Exact runtime-version metric mapping; no fuzzy version fallback is permitted."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    profile_id: str
    mapping_version: str
    runtime_name: Literal["vllm"] = "vllm"
    runtime_version: str
    source_format: WorkerMetricsFormat
    selectors: tuple[TelemetryMetricSelector, ...] = ()

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("telemetry profile_id must use stable lowercase characters")
        return value

    @field_validator("mapping_version", "runtime_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("telemetry mapping versions must use stable characters")
        return value

    @model_validator(mode="after")
    def validate_selectors(self) -> Self:
        semantics = [selector.semantic for selector in self.selectors]
        if len(semantics) != len(set(semantics)):
            raise ValueError("telemetry profile cannot map one semantic more than once")
        identities = [
            (selector.metric_name, selector.labels, selector.value_kind)
            for selector in self.selectors
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("telemetry profile cannot contain duplicate raw selectors")
        return self

    def selector_for(
        self,
        semantic: TelemetryMetricSemantic,
    ) -> TelemetryMetricSelector | None:
        """Return the exact selector for one semantic, if the version exposes it."""

        return next(
            (selector for selector in self.selectors if selector.semantic is semantic),
            None,
        )


class TelemetryAdaptationRequest(LocalABCContract):
    """Evidence required to normalize one completed worker invocation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    observation_id: str
    worker_identity: WorkerIdentity
    before_snapshot: WorkerMetricsSnapshot
    after_snapshot: WorkerMetricsSnapshot
    invocation_response: WorkerInvocationResponse
    eligible_shared_prefix_tokens: int = Field(gt=0)

    @field_validator("observation_id")
    @classmethod
    def validate_observation_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("observation_id must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_worker_and_time_order(self) -> Self:
        worker_ids = {
            self.worker_identity.worker_id,
            self.before_snapshot.worker_id,
            self.after_snapshot.worker_id,
            self.invocation_response.worker_id,
        }
        if len(worker_ids) != 1:
            raise ValueError("telemetry request worker identities must match")
        if self.before_snapshot.captured_at > self.invocation_response.completed_at:
            raise ValueError("before metrics snapshot must precede invocation completion")
        if self.invocation_response.completed_at > self.after_snapshot.captured_at:
            raise ValueError("after metrics snapshot must follow invocation completion")
        return self


class TelemetryAdaptationRecord(LocalABCContract):
    """Normalized observation with mapping and raw-snapshot lineage."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    profile_id: str
    mapping_version: str
    profile_fingerprint: str
    before_snapshot_sha256: str
    after_snapshot_sha256: str
    observation: TelemetryObservation

    @field_validator(
        "profile_fingerprint",
        "before_snapshot_sha256",
        "after_snapshot_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("telemetry lineage digests must be lowercase SHA-256")
        return value


class _MetricReadState(StrEnum):
    NOT_EXPOSED = "not_exposed"
    NOT_OBSERVED = "not_observed"
    VALID = "valid"
    INVALID = "invalid"


class _MetricRead(LocalABCContract):
    state: _MetricReadState
    metric_name: str | None = None
    value: float | None = None


class VersionedTelemetryAdapter:
    """Normalize raw snapshots through one exact runtime-version mapping profile."""

    def __init__(self, profile: TelemetryMappingProfile) -> None:
        self._profile = self._revalidate_profile(profile)

    @property
    def profile(self) -> TelemetryMappingProfile:
        """Return the immutable mapping profile used by this adapter."""

        return self._profile

    def adapt(self, request: TelemetryAdaptationRequest) -> TelemetryAdaptationRecord:
        """Map one before/after metric pair without repairing absent evidence."""

        validated = self._revalidate_request(request)
        self._validate_compatibility(validated)

        cache_read = self._read_metric(
            TelemetryMetricSemantic.CACHED_PREFIX_TOKENS,
            validated.before_snapshot,
            validated.after_snapshot,
        )
        new_prefill_read = self._read_metric(
            TelemetryMetricSemantic.NEWLY_COMPUTED_PREFILL_TOKENS,
            validated.before_snapshot,
            validated.after_snapshot,
        )
        prefill_duration_read = self._read_metric(
            TelemetryMetricSemantic.PREFILL_DURATION_SECONDS,
            validated.before_snapshot,
            validated.after_snapshot,
        )
        ttft_read = self._read_metric(
            TelemetryMetricSemantic.TIME_TO_FIRST_TOKEN_SECONDS,
            validated.before_snapshot,
            validated.after_snapshot,
        )

        cache, newly_computed = self._normalize_token_evidence(
            cache_read=cache_read,
            new_prefill_read=new_prefill_read,
            eligible_shared_prefix_tokens=validated.eligible_shared_prefix_tokens,
        )
        observation = TelemetryObservation(
            observation_id=validated.observation_id,
            worker_id=validated.worker_identity.worker_id,
            collected_at=validated.after_snapshot.captured_at,
            metric_mapping_version=self._profile.mapping_version,
            cache=cache,
            eligible_shared_prefix_tokens=validated.eligible_shared_prefix_tokens,
            newly_computed_prefill_tokens=newly_computed,
            prefill_duration_ms=self._seconds_to_ms(prefill_duration_read),
            time_to_first_token_ms=self._seconds_to_ms(ttft_read),
            end_to_end_latency_ms=validated.invocation_response.end_to_end_latency_ms,
        )
        return TelemetryAdaptationRecord(
            profile_id=self._profile.profile_id,
            mapping_version=self._profile.mapping_version,
            profile_fingerprint=self._profile.fingerprint(),
            before_snapshot_sha256=validated.before_snapshot.raw_payload_sha256,
            after_snapshot_sha256=validated.after_snapshot.raw_payload_sha256,
            observation=observation,
        )

    def _validate_compatibility(self, request: TelemetryAdaptationRequest) -> None:
        identity = request.worker_identity
        if identity.runtime_name != self._profile.runtime_name:
            raise TelemetryAdapterError(
                TelemetryAdapterErrorCode.RUNTIME_VERSION_MISMATCH,
                "worker runtime name does not match telemetry profile",
            )
        if identity.runtime_version != self._profile.runtime_version:
            raise TelemetryAdapterError(
                TelemetryAdapterErrorCode.RUNTIME_VERSION_MISMATCH,
                "worker runtime version does not exactly match telemetry profile",
            )
        if request.before_snapshot.source_format is not self._profile.source_format:
            raise TelemetryAdapterError(
                TelemetryAdapterErrorCode.SOURCE_FORMAT_MISMATCH,
                "before snapshot format does not match telemetry profile",
            )
        if request.after_snapshot.source_format is not self._profile.source_format:
            raise TelemetryAdapterError(
                TelemetryAdapterErrorCode.SOURCE_FORMAT_MISMATCH,
                "after snapshot format does not match telemetry profile",
            )

    def _read_metric(
        self,
        semantic: TelemetryMetricSemantic,
        before: WorkerMetricsSnapshot,
        after: WorkerMetricsSnapshot,
    ) -> _MetricRead:
        selector = self._profile.selector_for(semantic)
        if selector is None:
            return _MetricRead(state=_MetricReadState.NOT_EXPOSED)

        after_sample = self._sample_for(after, selector)
        if after_sample is None:
            return _MetricRead(
                state=_MetricReadState.NOT_OBSERVED,
                metric_name=selector.metric_name,
            )
        if selector.value_kind is TelemetryMetricValueKind.GAUGE:
            if after_sample.value < 0:
                return _MetricRead(
                    state=_MetricReadState.INVALID,
                    metric_name=selector.metric_name,
                )
            return _MetricRead(
                state=_MetricReadState.VALID,
                metric_name=selector.metric_name,
                value=after_sample.value,
            )

        before_sample = self._sample_for(before, selector)
        if before_sample is None:
            return _MetricRead(
                state=_MetricReadState.INVALID,
                metric_name=selector.metric_name,
            )
        delta = after_sample.value - before_sample.value
        if delta < 0:
            return _MetricRead(
                state=_MetricReadState.INVALID,
                metric_name=selector.metric_name,
            )
        return _MetricRead(
            state=_MetricReadState.VALID,
            metric_name=selector.metric_name,
            value=delta,
        )

    @staticmethod
    def _sample_for(
        snapshot: WorkerMetricsSnapshot,
        selector: TelemetryMetricSelector,
    ) -> WorkerMetricSample | None:
        return next(
            (
                sample
                for sample in snapshot.samples
                if sample.name == selector.metric_name and sample.labels == selector.labels
            ),
            None,
        )

    @staticmethod
    def _normalize_token_evidence(
        *,
        cache_read: _MetricRead,
        new_prefill_read: _MetricRead,
        eligible_shared_prefix_tokens: int,
    ) -> tuple[CacheObservation, int | None]:
        metric_name = cache_read.metric_name
        if cache_read.state is _MetricReadState.NOT_EXPOSED:
            return (
                CacheObservation(
                    state=CacheObservationState.NOT_EXPOSED,
                    reason_code=LocalABCFailureCode.TELEMETRY_NOT_EXPOSED,
                ),
                VersionedTelemetryAdapter._optional_token_count(new_prefill_read),
            )
        if cache_read.state is _MetricReadState.NOT_OBSERVED:
            return (
                CacheObservation(
                    state=CacheObservationState.NOT_OBSERVED,
                    raw_metric_name=metric_name,
                    reason_code=LocalABCFailureCode.TELEMETRY_NOT_OBSERVED,
                ),
                VersionedTelemetryAdapter._optional_token_count(new_prefill_read),
            )
        if cache_read.state is _MetricReadState.INVALID:
            return (
                CacheObservation(
                    state=CacheObservationState.INVALID,
                    raw_metric_name=metric_name,
                    reason_code=LocalABCFailureCode.TELEMETRY_INVALID,
                ),
                None,
            )

        cached_tokens = VersionedTelemetryAdapter._token_count(cache_read)
        newly_computed = VersionedTelemetryAdapter._token_count(new_prefill_read)
        cache_value_invalid = cache_read.state is _MetricReadState.VALID and cached_tokens is None
        new_prefill_invalid = (
            new_prefill_read.state in {_MetricReadState.INVALID, _MetricReadState.VALID}
            and newly_computed is None
        )
        if cache_value_invalid or new_prefill_invalid or cached_tokens is None:
            return (
                CacheObservation(
                    state=CacheObservationState.INVALID,
                    raw_metric_name=metric_name,
                    reason_code=LocalABCFailureCode.TELEMETRY_INVALID,
                ),
                None,
            )
        if cached_tokens > eligible_shared_prefix_tokens:
            return (
                CacheObservation(
                    state=CacheObservationState.INVALID,
                    raw_metric_name=metric_name,
                    reason_code=LocalABCFailureCode.TELEMETRY_INVALID,
                ),
                None,
            )
        if newly_computed is not None and (
            cached_tokens + newly_computed != eligible_shared_prefix_tokens
        ):
            return (
                CacheObservation(
                    state=CacheObservationState.INVALID,
                    raw_metric_name=metric_name,
                    reason_code=LocalABCFailureCode.TELEMETRY_INVALID,
                ),
                None,
            )
        cache_state = (
            CacheObservationState.ZERO if cached_tokens == 0 else CacheObservationState.POSITIVE
        )
        return (
            CacheObservation(
                state=cache_state,
                raw_metric_name=metric_name,
                observed_cached_prefix_tokens=cached_tokens,
            ),
            newly_computed,
        )

    @staticmethod
    def _token_count(read: _MetricRead) -> int | None:
        if read.state is not _MetricReadState.VALID:
            return None
        value = read.value
        if value is None or value < 0 or not value.is_integer():
            return None
        return int(value)

    @staticmethod
    def _optional_token_count(read: _MetricRead) -> int | None:
        return VersionedTelemetryAdapter._token_count(read)

    @staticmethod
    def _seconds_to_ms(read: _MetricRead) -> float | None:
        if read.state is not _MetricReadState.VALID or read.value is None:
            return None
        return read.value * 1000.0

    @staticmethod
    def _revalidate_profile(
        profile: TelemetryMappingProfile,
    ) -> TelemetryMappingProfile:
        try:
            return TelemetryMappingProfile.model_validate(profile.model_dump(mode="python"))
        except ValidationError as exc:
            raise TelemetryAdapterError(
                TelemetryAdapterErrorCode.INVALID_PROFILE,
                "telemetry profile failed strict boundary revalidation",
            ) from exc

    @staticmethod
    def _revalidate_request(
        request: TelemetryAdaptationRequest,
    ) -> TelemetryAdaptationRequest:
        try:
            return TelemetryAdaptationRequest.model_validate(request.model_dump(mode="python"))
        except ValidationError as exc:
            safe_detail = "telemetry request failed strict boundary revalidation"
            error_text = str(exc)
            if "worker identities must match" in error_text:
                code = TelemetryAdapterErrorCode.WORKER_ID_MISMATCH
            elif "snapshot must" in error_text:
                code = TelemetryAdapterErrorCode.SNAPSHOT_ORDER_INVALID
            else:
                code = TelemetryAdapterErrorCode.INVALID_REQUEST
            raise TelemetryAdapterError(code, safe_detail) from exc
