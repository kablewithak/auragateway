from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from auragateway.local_abc.contracts import (
    CacheObservationState,
    ModelIdentity,
    TokenizerIdentity,
    WorkerId,
    WorkerIdentity,
)
from auragateway.local_abc.errors import LocalABCFailureCode
from auragateway.local_abc.telemetry import (
    TelemetryAdaptationRequest,
    TelemetryAdapterError,
    TelemetryAdapterErrorCode,
    TelemetryMappingProfile,
    TelemetryMetricSelector,
    TelemetryMetricSemantic,
    TelemetryMetricValueKind,
    VersionedTelemetryAdapter,
)
from auragateway.local_abc.worker_client import (
    WorkerFinishReason,
    WorkerInvocationResponse,
    WorkerMetricSample,
    WorkerMetricsFormat,
    WorkerMetricsSnapshot,
)

BEFORE = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)
COMPLETED = BEFORE + timedelta(seconds=1)
AFTER = COMPLETED + timedelta(milliseconds=100)
RUNTIME_VERSION = "synthetic-vllm-fixture-1.0.0"
CACHE_NAME = "vllm_fixture:cached_prefix_tokens_total"
NEW_PREFILL_NAME = "vllm_fixture:new_prefill_tokens_total"
PREFILL_SECONDS_NAME = "vllm_fixture:prefill_seconds_total"
TTFT_SECONDS_NAME = "vllm_fixture:ttft_seconds"
LABELS = (("model", "synthetic-model"),)


def worker_identity(worker_id: WorkerId = WorkerId.WORKER_1) -> WorkerIdentity:
    gpu_index, port = {
        WorkerId.WORKER_1: (0, 8001),
        WorkerId.WORKER_2: (1, 8002),
    }[worker_id]
    model = ModelIdentity(
        repository="synthetic/model",
        revision="revision-001",
        config_sha256="1" * 64,
    )
    tokenizer = TokenizerIdentity(
        repository="synthetic/tokenizer",
        revision="revision-001",
        config_sha256="2" * 64,
    )
    return WorkerIdentity(
        worker_id=worker_id,
        gpu_index=gpu_index,
        port=port,
        runtime_version=RUNTIME_VERSION,
        model=model,
        tokenizer=tokenizer,
    )


def selector(
    semantic: TelemetryMetricSemantic,
    name: str,
    *,
    value_kind: TelemetryMetricValueKind = TelemetryMetricValueKind.COUNTER_DELTA,
) -> TelemetryMetricSelector:
    return TelemetryMetricSelector(
        semantic=semantic,
        metric_name=name,
        labels=LABELS,
        value_kind=value_kind,
    )


def profile(
    selectors: tuple[TelemetryMetricSelector, ...] | None = None,
    *,
    runtime_version: str = RUNTIME_VERSION,
    source_format: WorkerMetricsFormat = WorkerMetricsFormat.PROMETHEUS_TEXT,
) -> TelemetryMappingProfile:
    return TelemetryMappingProfile(
        profile_id="synthetic-vllm-metrics-v1",
        mapping_version="synthetic-vllm-mapping-v1",
        runtime_version=runtime_version,
        source_format=source_format,
        selectors=selectors
        if selectors is not None
        else (
            selector(TelemetryMetricSemantic.CACHED_PREFIX_TOKENS, CACHE_NAME),
            selector(
                TelemetryMetricSemantic.NEWLY_COMPUTED_PREFILL_TOKENS,
                NEW_PREFILL_NAME,
            ),
            selector(TelemetryMetricSemantic.PREFILL_DURATION_SECONDS, PREFILL_SECONDS_NAME),
            selector(
                TelemetryMetricSemantic.TIME_TO_FIRST_TOKEN_SECONDS,
                TTFT_SECONDS_NAME,
                value_kind=TelemetryMetricValueKind.GAUGE,
            ),
        ),
    )


def sample(name: str, value: float) -> WorkerMetricSample:
    return WorkerMetricSample(name=name, value=value, labels=LABELS)


def snapshot(
    *,
    captured_at: datetime,
    cache: float | None = 10.0,
    new_prefill: float | None = 100.0,
    prefill_seconds: float | None = 1.0,
    ttft_seconds: float | None = 0.2,
    worker_id: WorkerId = WorkerId.WORKER_1,
    source_format: WorkerMetricsFormat = WorkerMetricsFormat.PROMETHEUS_TEXT,
    digest_fill: str = "a",
) -> WorkerMetricsSnapshot:
    values = (
        (CACHE_NAME, cache),
        (NEW_PREFILL_NAME, new_prefill),
        (PREFILL_SECONDS_NAME, prefill_seconds),
        (TTFT_SECONDS_NAME, ttft_seconds),
    )
    samples = tuple(sample(name, value) for name, value in values if value is not None)
    return WorkerMetricsSnapshot(
        worker_id=worker_id,
        captured_at=captured_at,
        source_format=source_format,
        raw_payload_sha256=digest_fill * 64,
        samples=samples,
    )


def response(worker_id: WorkerId = WorkerId.WORKER_1) -> WorkerInvocationResponse:
    return WorkerInvocationResponse(
        request_id="request-001",
        worker_id=worker_id,
        completed_at=COMPLETED,
        output_text="synthetic fixture output",
        finish_reason=WorkerFinishReason.STOP,
        input_tokens=256,
        output_tokens=16,
        end_to_end_latency_ms=480.0,
    )


def adaptation_request(
    *,
    before: WorkerMetricsSnapshot | None = None,
    after: WorkerMetricsSnapshot | None = None,
    identity: WorkerIdentity | None = None,
    invocation_response: WorkerInvocationResponse | None = None,
    eligible_shared_prefix_tokens: int = 128,
) -> TelemetryAdaptationRequest:
    return TelemetryAdaptationRequest(
        observation_id="observation-001",
        worker_identity=identity or worker_identity(),
        before_snapshot=before or snapshot(captured_at=BEFORE),
        after_snapshot=after
        or snapshot(
            captured_at=AFTER,
            cache=42.0,
            new_prefill=196.0,
            prefill_seconds=1.04,
            ttft_seconds=0.18,
            digest_fill="b",
        ),
        invocation_response=invocation_response or response(),
        eligible_shared_prefix_tokens=eligible_shared_prefix_tokens,
    )


def test_positive_counter_deltas_normalize_to_observed_cache_evidence() -> None:
    record = VersionedTelemetryAdapter(profile()).adapt(adaptation_request())

    observation = record.observation
    assert observation.cache.state is CacheObservationState.POSITIVE
    assert observation.cache.observed_cached_prefix_tokens == 32
    assert observation.newly_computed_prefill_tokens == 96
    assert observation.prefill_duration_ms == pytest.approx(40.0)
    assert observation.time_to_first_token_ms == pytest.approx(180.0)
    assert observation.end_to_end_latency_ms == 480.0
    assert observation.cache.raw_metric_name == CACHE_NAME


def test_zero_delta_remains_observed_zero() -> None:
    request = adaptation_request(
        after=snapshot(
            captured_at=AFTER,
            cache=10.0,
            new_prefill=228.0,
            prefill_seconds=1.05,
            ttft_seconds=0.2,
            digest_fill="b",
        )
    )

    observation = VersionedTelemetryAdapter(profile()).adapt(request).observation

    assert observation.cache.state is CacheObservationState.ZERO
    assert observation.cache.observed_cached_prefix_tokens == 0
    assert observation.newly_computed_prefill_tokens == 128


def test_unmapped_cache_semantic_remains_not_exposed() -> None:
    mapping = profile(
        selectors=(
            selector(
                TelemetryMetricSemantic.NEWLY_COMPUTED_PREFILL_TOKENS,
                NEW_PREFILL_NAME,
            ),
        )
    )

    observation = VersionedTelemetryAdapter(mapping).adapt(adaptation_request()).observation

    assert observation.cache.state is CacheObservationState.NOT_EXPOSED
    assert observation.cache.observed_cached_prefix_tokens is None
    assert observation.cache.reason_code is LocalABCFailureCode.TELEMETRY_NOT_EXPOSED


def test_mapped_but_absent_cache_series_remains_not_observed() -> None:
    request = adaptation_request(
        after=snapshot(
            captured_at=AFTER,
            cache=None,
            new_prefill=196.0,
            prefill_seconds=1.04,
            ttft_seconds=0.18,
            digest_fill="b",
        )
    )

    observation = VersionedTelemetryAdapter(profile()).adapt(request).observation

    assert observation.cache.state is CacheObservationState.NOT_OBSERVED
    assert observation.cache.observed_cached_prefix_tokens is None
    assert observation.cache.raw_metric_name == CACHE_NAME
    assert observation.cache.reason_code is LocalABCFailureCode.TELEMETRY_NOT_OBSERVED


def test_counter_reset_becomes_invalid_not_negative_evidence() -> None:
    request = adaptation_request(
        after=snapshot(
            captured_at=AFTER,
            cache=5.0,
            new_prefill=196.0,
            prefill_seconds=1.04,
            ttft_seconds=0.18,
            digest_fill="b",
        )
    )

    observation = VersionedTelemetryAdapter(profile()).adapt(request).observation

    assert observation.cache.state is CacheObservationState.INVALID
    assert observation.cache.observed_cached_prefix_tokens is None
    assert observation.cache.reason_code is LocalABCFailureCode.TELEMETRY_INVALID


def test_non_integral_token_delta_becomes_invalid_evidence() -> None:
    request = adaptation_request(
        after=snapshot(
            captured_at=AFTER,
            cache=42.5,
            new_prefill=195.5,
            prefill_seconds=1.04,
            ttft_seconds=0.18,
            digest_fill="b",
        )
    )

    observation = VersionedTelemetryAdapter(profile()).adapt(request).observation

    assert observation.cache.state is CacheObservationState.INVALID
    assert observation.cache.observed_cached_prefix_tokens is None
    assert observation.cache.reason_code is LocalABCFailureCode.TELEMETRY_INVALID


def test_token_reconciliation_failure_marks_cache_evidence_invalid() -> None:
    request = adaptation_request(
        after=snapshot(
            captured_at=AFTER,
            cache=42.0,
            new_prefill=195.0,
            prefill_seconds=1.04,
            ttft_seconds=0.18,
            digest_fill="b",
        )
    )

    observation = VersionedTelemetryAdapter(profile()).adapt(request).observation

    assert observation.cache.state is CacheObservationState.INVALID
    assert observation.newly_computed_prefill_tokens is None
    assert observation.cache.reason_code is LocalABCFailureCode.TELEMETRY_INVALID


def test_cached_tokens_cannot_exceed_eligible_prefix() -> None:
    request = adaptation_request(
        after=snapshot(
            captured_at=AFTER,
            cache=210.0,
            new_prefill=100.0,
            prefill_seconds=1.04,
            ttft_seconds=0.18,
            digest_fill="b",
        )
    )

    observation = VersionedTelemetryAdapter(profile()).adapt(request).observation

    assert observation.cache.state is CacheObservationState.INVALID
    assert observation.cache.observed_cached_prefix_tokens is None


def test_absent_optional_duration_metrics_remain_none() -> None:
    request = adaptation_request(
        after=snapshot(
            captured_at=AFTER,
            cache=42.0,
            new_prefill=196.0,
            prefill_seconds=None,
            ttft_seconds=None,
            digest_fill="b",
        )
    )

    observation = VersionedTelemetryAdapter(profile()).adapt(request).observation

    assert observation.prefill_duration_ms is None
    assert observation.time_to_first_token_ms is None
    assert observation.end_to_end_latency_ms == 480.0


def test_mapping_profile_requires_unique_semantics() -> None:
    duplicate = selector(TelemetryMetricSemantic.CACHED_PREFIX_TOKENS, "other_cache")

    with pytest.raises(ValidationError, match="one semantic"):
        profile(
            selectors=(
                selector(TelemetryMetricSemantic.CACHED_PREFIX_TOKENS, CACHE_NAME),
                duplicate,
            )
        )


def test_mapping_profile_canonicalizes_selector_labels() -> None:
    mapped = TelemetryMetricSelector(
        semantic=TelemetryMetricSemantic.CACHED_PREFIX_TOKENS,
        metric_name=CACHE_NAME,
        labels=(("worker", "worker_1"), ("model", "synthetic-model")),
        value_kind=TelemetryMetricValueKind.COUNTER_DELTA,
    )

    assert mapped.labels == (("model", "synthetic-model"), ("worker", "worker_1"))


def test_exact_runtime_version_match_is_required() -> None:
    adapter = VersionedTelemetryAdapter(profile(runtime_version="synthetic-vllm-fixture-2.0.0"))

    with pytest.raises(TelemetryAdapterError) as exc_info:
        adapter.adapt(adaptation_request())

    assert exc_info.value.code is TelemetryAdapterErrorCode.RUNTIME_VERSION_MISMATCH


def test_source_format_must_match_profile() -> None:
    request = adaptation_request(
        before=snapshot(
            captured_at=BEFORE,
            source_format=WorkerMetricsFormat.JSON,
        ),
        after=snapshot(
            captured_at=AFTER,
            cache=42.0,
            new_prefill=196.0,
            prefill_seconds=1.04,
            ttft_seconds=0.18,
            source_format=WorkerMetricsFormat.JSON,
            digest_fill="b",
        ),
    )

    with pytest.raises(TelemetryAdapterError) as exc_info:
        VersionedTelemetryAdapter(profile()).adapt(request)

    assert exc_info.value.code is TelemetryAdapterErrorCode.SOURCE_FORMAT_MISMATCH


def test_worker_mismatch_fails_strict_request_revalidation() -> None:
    valid = adaptation_request()
    request = valid.model_copy(update={"invocation_response": response(WorkerId.WORKER_2)})

    with pytest.raises(TelemetryAdapterError) as exc_info:
        VersionedTelemetryAdapter(profile()).adapt(request)

    assert exc_info.value.code is TelemetryAdapterErrorCode.WORKER_ID_MISMATCH


def test_snapshot_order_fails_strict_request_revalidation() -> None:
    valid = adaptation_request()
    invalid_after = snapshot(
        captured_at=COMPLETED - timedelta(milliseconds=1),
        cache=42.0,
        new_prefill=196.0,
        prefill_seconds=1.04,
        ttft_seconds=0.18,
        digest_fill="b",
    )
    request = valid.model_copy(update={"after_snapshot": invalid_after})

    with pytest.raises(TelemetryAdapterError) as exc_info:
        VersionedTelemetryAdapter(profile()).adapt(request)

    assert exc_info.value.code is TelemetryAdapterErrorCode.SNAPSHOT_ORDER_INVALID


def test_tampered_profile_fails_adapter_construction() -> None:
    valid = profile()
    tampered = valid.model_copy(update={"mapping_version": "bad version"})

    with pytest.raises(TelemetryAdapterError) as exc_info:
        VersionedTelemetryAdapter(tampered)

    assert exc_info.value.code is TelemetryAdapterErrorCode.INVALID_PROFILE


def test_tampered_request_fails_adapter_boundary() -> None:
    valid = adaptation_request()
    tampered = valid.model_copy(update={"eligible_shared_prefix_tokens": 0})

    with pytest.raises(TelemetryAdapterError) as exc_info:
        VersionedTelemetryAdapter(profile()).adapt(tampered)

    assert exc_info.value.code is TelemetryAdapterErrorCode.INVALID_REQUEST


def test_record_preserves_mapping_and_snapshot_lineage() -> None:
    adapter = VersionedTelemetryAdapter(profile())

    record = adapter.adapt(adaptation_request())

    assert record.profile_id == adapter.profile.profile_id
    assert record.mapping_version == adapter.profile.mapping_version
    assert record.profile_fingerprint == adapter.profile.fingerprint()
    assert record.before_snapshot_sha256 == "a" * 64
    assert record.after_snapshot_sha256 == "b" * 64


def test_adaptation_is_deterministic_and_hash_ready() -> None:
    adapter = VersionedTelemetryAdapter(profile())
    request = adaptation_request()

    first = adapter.adapt(request)
    second = adapter.adapt(request)

    assert first == second
    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()


def test_raw_metric_names_do_not_escape_as_normalized_field_names() -> None:
    record = VersionedTelemetryAdapter(profile()).adapt(adaptation_request())
    payload = record.observation.model_dump(mode="json")

    assert CACHE_NAME not in payload
    assert payload["cache"]["raw_metric_name"] == CACHE_NAME
