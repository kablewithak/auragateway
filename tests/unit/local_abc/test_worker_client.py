from __future__ import annotations

import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from pydantic import ValidationError

from auragateway.local_abc.contracts import (
    ModelIdentity,
    TokenizerIdentity,
    WorkerId,
    WorkerIdentity,
)
from auragateway.local_abc.worker_client import (
    CacheResetReceipt,
    CacheResetRequest,
    CacheResetState,
    WorkerClient,
    WorkerClientBoundary,
    WorkerClientConfig,
    WorkerClientError,
    WorkerClientErrorCode,
    WorkerClientOperation,
    WorkerFinishReason,
    WorkerHealth,
    WorkerHealthState,
    WorkerInvocationRequest,
    WorkerInvocationResponse,
    WorkerInvocationSettings,
    WorkerMetricSample,
    WorkerMetricsFormat,
    WorkerMetricsSnapshot,
)

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
TRACE_ID = UUID("33333333-3333-4333-8333-333333333333")


def config(worker_id: WorkerId = WorkerId.WORKER_1) -> WorkerClientConfig:
    port = 8001 if worker_id is WorkerId.WORKER_1 else 8002
    return WorkerClientConfig(
        worker_id=worker_id,
        base_url=f"http://127.0.0.1:{port}",
        connect_timeout_seconds=2.0,
        read_timeout_seconds=30.0,
    )


def identity(worker_id: WorkerId = WorkerId.WORKER_1) -> WorkerIdentity:
    gpu_index = 0 if worker_id is WorkerId.WORKER_1 else 1
    port = 8001 if worker_id is WorkerId.WORKER_1 else 8002
    model = ModelIdentity(
        repository="Qwen/Qwen2.5-0.5B-Instruct",
        revision="1111111",
        config_sha256="1" * 64,
    )
    tokenizer = TokenizerIdentity(
        repository="Qwen/Qwen2.5-0.5B-Instruct",
        revision="1111111",
        config_sha256="2" * 64,
    )
    return WorkerIdentity(
        worker_id=worker_id,
        gpu_index=gpu_index,
        port=port,
        runtime_version="0.10.0",
        model=model,
        tokenizer=tokenizer,
    )


def invocation_request() -> WorkerInvocationRequest:
    return WorkerInvocationRequest(
        request_id="request-001",
        trace_id=TRACE_ID,
        trajectory_id="trajectory-001",
        turn_index=1,
        serialized_prefix="synthetic stable prefix",
        serialized_suffix="synthetic volatile suffix",
        settings=WorkerInvocationSettings(max_output_tokens=64, seed=7),
    )


def health(worker_id: WorkerId = WorkerId.WORKER_1) -> WorkerHealth:
    return WorkerHealth(
        worker_id=worker_id,
        checked_at=NOW,
        state=WorkerHealthState.HEALTHY,
        ready_for_invocation=True,
        latency_ms=1.25,
    )


def response(
    worker_id: WorkerId = WorkerId.WORKER_1,
    request_id: str = "request-001",
) -> WorkerInvocationResponse:
    return WorkerInvocationResponse(
        request_id=request_id,
        worker_id=worker_id,
        completed_at=NOW,
        output_text="synthetic completion",
        finish_reason=WorkerFinishReason.STOP,
        input_tokens=128,
        output_tokens=12,
        end_to_end_latency_ms=20.0,
    )


def metrics(worker_id: WorkerId = WorkerId.WORKER_1) -> WorkerMetricsSnapshot:
    return WorkerMetricsSnapshot(
        worker_id=worker_id,
        captured_at=NOW,
        source_format=WorkerMetricsFormat.PROMETHEUS_TEXT,
        raw_payload_sha256="3" * 64,
        samples=(
            WorkerMetricSample(
                name="vllm:request_success_total",
                value=1.0,
                labels=(("model_name", "synthetic-model"),),
            ),
        ),
    )


def reset_request() -> CacheResetRequest:
    return CacheResetRequest(request_id="reset-001", requested_at=NOW)


def reset_receipt(
    worker_id: WorkerId = WorkerId.WORKER_1,
    request_id: str = "reset-001",
) -> CacheResetReceipt:
    return CacheResetReceipt(
        request_id=request_id,
        worker_id=worker_id,
        completed_at=NOW,
        state=CacheResetState.VERIFIED,
        verification_method="synthetic-generation-counter",
    )


class ScriptedWorkerClient:
    def __init__(
        self,
        *,
        worker_id: WorkerId = WorkerId.WORKER_1,
    ) -> None:
        self._config = config(worker_id)
        self.health_result: object = health(worker_id)
        self.invoke_result: object = response(worker_id)
        self.metrics_result: object = metrics(worker_id)
        self.reset_result: object = reset_receipt(worker_id)
        self.identity_result: object = identity(worker_id)
        self.failures: dict[WorkerClientOperation, BaseException] = {}
        self.calls: list[WorkerClientOperation] = []
        self.last_invocation: WorkerInvocationRequest | None = None
        self.last_reset: CacheResetRequest | None = None

    @property
    def config(self) -> WorkerClientConfig:
        return self._config

    def _result(self, operation: WorkerClientOperation, value: object) -> object:
        self.calls.append(operation)
        failure = self.failures.get(operation)
        if failure is not None:
            raise failure
        return value

    def health(self) -> WorkerHealth:
        return cast(WorkerHealth, self._result(WorkerClientOperation.HEALTH, self.health_result))

    def invoke(self, request: WorkerInvocationRequest) -> WorkerInvocationResponse:
        self.last_invocation = request
        return cast(
            WorkerInvocationResponse,
            self._result(WorkerClientOperation.INVOKE, self.invoke_result),
        )

    def metrics(self) -> WorkerMetricsSnapshot:
        return cast(
            WorkerMetricsSnapshot,
            self._result(WorkerClientOperation.METRICS, self.metrics_result),
        )

    def reset_cache(self, request: CacheResetRequest) -> CacheResetReceipt:
        self.last_reset = request
        return cast(
            CacheResetReceipt,
            self._result(WorkerClientOperation.RESET_CACHE, self.reset_result),
        )

    def identity(self) -> WorkerIdentity:
        return cast(
            WorkerIdentity,
            self._result(WorkerClientOperation.IDENTITY, self.identity_result),
        )


def test_config_normalizes_trailing_slash_and_preserves_no_retry_policy() -> None:
    value = WorkerClientConfig(
        worker_id=WorkerId.WORKER_1,
        base_url="http://127.0.0.1:8001/",
        connect_timeout_seconds=1.0,
        read_timeout_seconds=2.0,
    )

    assert value.base_url == "http://127.0.0.1:8001"
    assert value.max_attempts == 1


@pytest.mark.parametrize(
    "base_url",
    [
        "ftp://127.0.0.1:8001",
        "http://user:secret@127.0.0.1:8001",
        "http://127.0.0.1",
        "http://127.0.0.1:8001/health",
        "http://127.0.0.1:8001?token=secret",
        "http://127.0.0.1:8001#fragment",
    ],
)
def test_config_rejects_unsafe_or_ambiguous_base_urls(base_url: str) -> None:
    with pytest.raises(ValidationError):
        WorkerClientConfig(
            worker_id=WorkerId.WORKER_1,
            base_url=base_url,
            connect_timeout_seconds=1.0,
            read_timeout_seconds=2.0,
        )


def test_health_requires_readiness_to_match_healthy_state() -> None:
    with pytest.raises(ValidationError, match="exactly match"):
        WorkerHealth(
            worker_id=WorkerId.WORKER_1,
            checked_at=NOW,
            state=WorkerHealthState.UNKNOWN,
            ready_for_invocation=True,
            latency_ms=1.0,
            safe_detail="no response",
        )


def test_non_healthy_health_requires_safe_detail() -> None:
    with pytest.raises(ValidationError, match="safe_detail"):
        WorkerHealth(
            worker_id=WorkerId.WORKER_1,
            checked_at=NOW,
            state=WorkerHealthState.UNHEALTHY,
            ready_for_invocation=False,
            latency_ms=1.0,
        )


def test_invocation_request_and_response_hide_raw_content_from_repr() -> None:
    request = invocation_request()
    result = response()

    assert "synthetic stable prefix" not in repr(request)
    assert "synthetic volatile suffix" not in repr(request)
    assert "synthetic completion" not in repr(result)


def test_invocation_settings_are_deterministic_and_non_streaming() -> None:
    settings = WorkerInvocationSettings(max_output_tokens=128, seed=11)

    assert settings.temperature == 0.0
    assert settings.top_p == 1.0
    assert not settings.stream


def test_successful_response_requires_generated_tokens() -> None:
    with pytest.raises(ValidationError, match="at least one output token"):
        WorkerInvocationResponse(
            request_id="request-001",
            worker_id=WorkerId.WORKER_1,
            completed_at=NOW,
            output_text="synthetic completion",
            finish_reason=WorkerFinishReason.STOP,
            input_tokens=128,
            output_tokens=0,
            end_to_end_latency_ms=20.0,
        )


def test_metric_labels_are_canonicalized() -> None:
    sample = WorkerMetricSample(
        name="vllm:metric_total",
        value=1.0,
        labels=(("worker", "worker_1"), ("model", "synthetic")),
    )

    assert sample.labels == (("model", "synthetic"), ("worker", "worker_1"))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_metric_samples_reject_non_finite_values(value: float) -> None:
    with pytest.raises(ValidationError, match="finite"):
        WorkerMetricSample(name="vllm:metric_total", value=value)


def test_metrics_snapshot_rejects_duplicate_series() -> None:
    first = WorkerMetricSample(name="vllm:metric_total", value=1.0)
    second = WorkerMetricSample(name="vllm:metric_total", value=2.0)

    with pytest.raises(ValidationError, match="duplicate"):
        WorkerMetricsSnapshot(
            worker_id=WorkerId.WORKER_1,
            captured_at=NOW,
            source_format=WorkerMetricsFormat.PROMETHEUS_TEXT,
            raw_payload_sha256="3" * 64,
            samples=(first, second),
        )


def test_empty_metrics_snapshot_remains_explicitly_empty() -> None:
    snapshot = WorkerMetricsSnapshot(
        worker_id=WorkerId.WORKER_1,
        captured_at=NOW,
        source_format=WorkerMetricsFormat.PROMETHEUS_TEXT,
        raw_payload_sha256="3" * 64,
    )

    assert snapshot.samples == ()


def test_reset_receipt_distinguishes_verified_from_not_supported() -> None:
    unsupported = CacheResetReceipt(
        request_id="reset-001",
        worker_id=WorkerId.WORKER_1,
        completed_at=NOW,
        state=CacheResetState.NOT_SUPPORTED,
        safe_detail="worker runtime does not expose a reset operation",
    )

    assert unsupported.state is CacheResetState.NOT_SUPPORTED
    assert unsupported.verification_method is None


def test_verified_reset_requires_verification_method() -> None:
    with pytest.raises(ValidationError, match="verification_method"):
        CacheResetReceipt(
            request_id="reset-001",
            worker_id=WorkerId.WORKER_1,
            completed_at=NOW,
            state=CacheResetState.VERIFIED,
        )


def test_scripted_client_satisfies_runtime_protocol() -> None:
    client = ScriptedWorkerClient()

    assert isinstance(client, WorkerClient)


def test_boundary_returns_strictly_validated_results_and_exact_requests() -> None:
    client = ScriptedWorkerClient()
    boundary = WorkerClientBoundary(client)
    request = invocation_request()
    cache_reset = reset_request()

    assert boundary.health() == health()
    assert boundary.invoke(request) == response()
    assert boundary.metrics() == metrics()
    assert boundary.reset_cache(cache_reset) == reset_receipt()
    assert boundary.identity() == identity()
    assert client.last_invocation == request
    assert client.last_reset == cache_reset


def test_boundary_revalidates_tampered_model_instances() -> None:
    client = ScriptedWorkerClient()
    client.health_result = health().model_copy(update={"ready_for_invocation": False})

    with pytest.raises(WorkerClientError) as exc_info:
        WorkerClientBoundary(client).health()

    error = exc_info.value
    assert error.code is WorkerClientErrorCode.INVALID_RESPONSE
    assert error.operation is WorkerClientOperation.HEALTH
    assert error.__cause__ is None
    assert error.__context__ is None


@pytest.mark.parametrize(
    ("operation", "configure", "call"),
    [
        (
            WorkerClientOperation.HEALTH,
            lambda client: setattr(client, "health_result", health(WorkerId.WORKER_2)),
            lambda boundary: boundary.health(),
        ),
        (
            WorkerClientOperation.INVOKE,
            lambda client: setattr(client, "invoke_result", response(WorkerId.WORKER_2)),
            lambda boundary: boundary.invoke(invocation_request()),
        ),
        (
            WorkerClientOperation.METRICS,
            lambda client: setattr(client, "metrics_result", metrics(WorkerId.WORKER_2)),
            lambda boundary: boundary.metrics(),
        ),
        (
            WorkerClientOperation.RESET_CACHE,
            lambda client: setattr(client, "reset_result", reset_receipt(WorkerId.WORKER_2)),
            lambda boundary: boundary.reset_cache(reset_request()),
        ),
        (
            WorkerClientOperation.IDENTITY,
            lambda client: setattr(client, "identity_result", identity(WorkerId.WORKER_2)),
            lambda boundary: boundary.identity(),
        ),
    ],
)
def test_boundary_rejects_worker_identity_mismatch(
    operation: WorkerClientOperation,
    configure: Callable[[ScriptedWorkerClient], None],
    call: Callable[[WorkerClientBoundary], object],
) -> None:
    client = ScriptedWorkerClient()
    configure(client)

    with pytest.raises(WorkerClientError) as exc_info:
        call(WorkerClientBoundary(client))

    assert exc_info.value.operation is operation
    assert exc_info.value.code is WorkerClientErrorCode.WORKER_ID_MISMATCH


@pytest.mark.parametrize(
    ("operation", "configure", "call"),
    [
        (
            WorkerClientOperation.INVOKE,
            lambda client: setattr(client, "invoke_result", response(request_id="request-999")),
            lambda boundary: boundary.invoke(invocation_request()),
        ),
        (
            WorkerClientOperation.RESET_CACHE,
            lambda client: setattr(client, "reset_result", reset_receipt(request_id="reset-999")),
            lambda boundary: boundary.reset_cache(reset_request()),
        ),
    ],
)
def test_boundary_rejects_request_id_mismatch(
    operation: WorkerClientOperation,
    configure: Callable[[ScriptedWorkerClient], None],
    call: Callable[[WorkerClientBoundary], object],
) -> None:
    client = ScriptedWorkerClient()
    configure(client)

    with pytest.raises(WorkerClientError) as exc_info:
        call(WorkerClientBoundary(client))

    assert exc_info.value.operation is operation
    assert exc_info.value.code is WorkerClientErrorCode.REQUEST_ID_MISMATCH


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (
            TimeoutError("sensitive endpoint and payload detail"),
            WorkerClientErrorCode.TIMEOUT,
        ),
        (
            ConnectionError("sensitive endpoint and payload detail"),
            WorkerClientErrorCode.CONNECTION_FAILED,
        ),
    ],
)
def test_boundary_maps_transport_failures_without_raw_payloads(
    failure: BaseException,
    expected_code: WorkerClientErrorCode,
) -> None:
    client = ScriptedWorkerClient()
    client.failures[WorkerClientOperation.HEALTH] = failure

    with pytest.raises(WorkerClientError) as exc_info:
        WorkerClientBoundary(client).health()

    error = exc_info.value
    formatted = "".join(traceback.format_exception(error))
    assert error.code is expected_code
    assert error.operation is WorkerClientOperation.HEALTH
    assert error.__cause__ is None
    assert error.__context__ is None
    assert "sensitive endpoint and payload detail" not in str(error)
    assert "sensitive endpoint and payload detail" not in repr(error)
    assert "sensitive endpoint and payload detail" not in formatted
    assert "synthetic stable prefix" not in formatted


def test_boundary_does_not_retry_failed_operations() -> None:
    client = ScriptedWorkerClient()
    client.failures[WorkerClientOperation.HEALTH] = TimeoutError()

    with pytest.raises(WorkerClientError):
        WorkerClientBoundary(client).health()

    assert client.calls == [WorkerClientOperation.HEALTH]


def test_contract_fingerprints_are_deterministic() -> None:
    first = invocation_request()
    second = invocation_request()

    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()
