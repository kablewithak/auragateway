from __future__ import annotations

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
    WorkerClient,
    WorkerClientConfig,
    WorkerFinishReason,
    WorkerHealth,
    WorkerHealthState,
    WorkerInvocationRequest,
    WorkerInvocationResponse,
    WorkerMetricsFormat,
    WorkerMetricsSnapshot,
)
from auragateway.local_abc.worker_registry import (
    WorkerQualification,
    WorkerRegistry,
    WorkerRegistryError,
    WorkerRegistryErrorCode,
    WorkerRegistryFailureCode,
    WorkerRegistryReport,
)

NOW = datetime(2026, 7, 15, 16, 0, tzinfo=UTC)
TRACE_ID = UUID("33333333-3333-4333-8333-333333333333")


def model_identity(fill: str = "1") -> ModelIdentity:
    return ModelIdentity(
        repository="synthetic/model",
        revision=f"revision-{fill * 8}",
        config_sha256=fill * 64,
    )


def tokenizer_identity(fill: str = "2") -> TokenizerIdentity:
    return TokenizerIdentity(
        repository="synthetic/tokenizer",
        revision=f"revision-{fill * 8}",
        config_sha256=fill * 64,
    )


def worker_identity(
    worker_id: WorkerId,
    *,
    model: ModelIdentity | None = None,
    tokenizer: TokenizerIdentity | None = None,
    runtime_version: str = "0.10.0.synthetic1",
) -> WorkerIdentity:
    topology = {
        WorkerId.WORKER_1: (0, 8001),
        WorkerId.WORKER_2: (1, 8002),
    }
    gpu_index, port = topology[worker_id]
    return WorkerIdentity(
        worker_id=worker_id,
        gpu_index=gpu_index,
        port=port,
        runtime_version=runtime_version,
        model=model or model_identity(),
        tokenizer=tokenizer or tokenizer_identity(),
    )


class StubWorkerClient:
    def __init__(
        self,
        *,
        worker_id: WorkerId,
        host: str = "127.0.0.1",
        port: int | None = None,
        health_state: WorkerHealthState = WorkerHealthState.HEALTHY,
        identity: WorkerIdentity | None = None,
        health_error: Exception | None = None,
        identity_error: Exception | None = None,
    ) -> None:
        expected_port = 8001 if worker_id is WorkerId.WORKER_1 else 8002
        self._config = WorkerClientConfig(
            worker_id=worker_id,
            base_url=f"http://{host}:{port or expected_port}",
            connect_timeout_seconds=1.0,
            read_timeout_seconds=5.0,
        )
        self._health = WorkerHealth(
            worker_id=worker_id,
            checked_at=NOW,
            state=health_state,
            ready_for_invocation=health_state is WorkerHealthState.HEALTHY,
            latency_ms=1.5,
            safe_detail=None
            if health_state is WorkerHealthState.HEALTHY
            else "synthetic worker not ready",
        )
        self._identity = identity or worker_identity(worker_id)
        self._health_error = health_error
        self._identity_error = identity_error
        self.health_calls = 0
        self.identity_calls = 0
        self.invoke_calls = 0
        self.metrics_calls = 0
        self.reset_calls = 0

    @property
    def config(self) -> WorkerClientConfig:
        return self._config

    def health(self) -> WorkerHealth:
        self.health_calls += 1
        if self._health_error is not None:
            raise self._health_error
        return self._health

    def identity(self) -> WorkerIdentity:
        self.identity_calls += 1
        if self._identity_error is not None:
            raise self._identity_error
        return self._identity

    def invoke(self, request: WorkerInvocationRequest) -> WorkerInvocationResponse:
        self.invoke_calls += 1
        return WorkerInvocationResponse(
            request_id=request.request_id,
            worker_id=self.config.worker_id,
            completed_at=NOW,
            output_text="synthetic output",
            finish_reason=WorkerFinishReason.STOP,
            input_tokens=10,
            output_tokens=1,
            end_to_end_latency_ms=2.0,
        )

    def metrics(self) -> WorkerMetricsSnapshot:
        self.metrics_calls += 1
        return WorkerMetricsSnapshot(
            worker_id=self.config.worker_id,
            captured_at=NOW,
            source_format=WorkerMetricsFormat.JSON,
            raw_payload_sha256="a" * 64,
        )

    def reset_cache(self, request: CacheResetRequest) -> CacheResetReceipt:
        self.reset_calls += 1
        raise AssertionError("registry qualification must not reset cache")


def clients(
    *,
    worker_1: StubWorkerClient | None = None,
    worker_2: StubWorkerClient | None = None,
) -> tuple[StubWorkerClient, StubWorkerClient]:
    return (
        worker_1 or StubWorkerClient(worker_id=WorkerId.WORKER_1),
        worker_2 or StubWorkerClient(worker_id=WorkerId.WORKER_2),
    )


def test_registry_requires_exactly_two_clients() -> None:
    worker_1, worker_2 = clients()

    for candidate in ((), (worker_1,), (worker_1, worker_2, worker_1)):
        with pytest.raises(WorkerRegistryError) as exc_info:
            WorkerRegistry(cast("tuple[WorkerClient, ...]", candidate))
        assert exc_info.value.code is WorkerRegistryErrorCode.INVALID_CLIENT_SET


def test_registry_requires_unique_worker_1_and_worker_2() -> None:
    duplicate = (
        StubWorkerClient(worker_id=WorkerId.WORKER_1),
        StubWorkerClient(worker_id=WorkerId.WORKER_1),
    )

    with pytest.raises(WorkerRegistryError) as exc_info:
        WorkerRegistry(duplicate)

    assert exc_info.value.code is WorkerRegistryErrorCode.INVALID_CLIENT_SET


@pytest.mark.parametrize(
    ("worker_id", "wrong_port"),
    [(WorkerId.WORKER_1, 8101), (WorkerId.WORKER_2, 8102)],
)
def test_registry_enforces_fixed_endpoint_ports(
    worker_id: WorkerId,
    wrong_port: int,
) -> None:
    worker_1, worker_2 = clients()
    replacement = StubWorkerClient(worker_id=worker_id, port=wrong_port)
    candidate = (
        (replacement, worker_2) if worker_id is WorkerId.WORKER_1 else (worker_1, replacement)
    )

    with pytest.raises(WorkerRegistryError) as exc_info:
        WorkerRegistry(candidate)

    assert exc_info.value.code is WorkerRegistryErrorCode.CONFIG_TOPOLOGY_MISMATCH
    assert exc_info.value.worker_id is worker_id


def test_registry_requires_one_local_scheme_and_hostname() -> None:
    candidate = (
        StubWorkerClient(worker_id=WorkerId.WORKER_1, host="127.0.0.1"),
        StubWorkerClient(worker_id=WorkerId.WORKER_2, host="localhost"),
    )

    with pytest.raises(WorkerRegistryError) as exc_info:
        WorkerRegistry(candidate)

    assert exc_info.value.code is WorkerRegistryErrorCode.CONFIG_TOPOLOGY_MISMATCH


def test_registry_accepts_input_in_any_order_but_qualifies_canonically() -> None:
    worker_1, worker_2 = clients()
    registry = WorkerRegistry((worker_2, worker_1))

    report = registry.qualify(qualified_at=NOW)

    assert tuple(item.worker_id for item in report.workers) == tuple(WorkerId)
    assert registry.boundary_for(WorkerId.WORKER_1).config.worker_id is WorkerId.WORKER_1
    assert registry.boundary_for(WorkerId.WORKER_2).config.worker_id is WorkerId.WORKER_2


def test_healthy_parity_report_is_ready_for_environment_qualification() -> None:
    report = WorkerRegistry(clients()).qualify(qualified_at=NOW)

    assert report.ready_for_environment_qualification
    assert report.model_identity_match
    assert report.tokenizer_identity_match
    assert report.runtime_version_match
    assert report.failure_codes == ()
    assert report.worker_for(WorkerId.WORKER_1).identity.gpu_index == 0
    assert report.worker_for(WorkerId.WORKER_2).identity.gpu_index == 1


@pytest.mark.parametrize(
    ("worker_id", "expected_code"),
    [
        (WorkerId.WORKER_1, WorkerRegistryFailureCode.WORKER_1_NOT_READY),
        (WorkerId.WORKER_2, WorkerRegistryFailureCode.WORKER_2_NOT_READY),
    ],
)
def test_non_ready_health_fails_closed(
    worker_id: WorkerId,
    expected_code: WorkerRegistryFailureCode,
) -> None:
    unhealthy = StubWorkerClient(
        worker_id=worker_id,
        health_state=WorkerHealthState.UNHEALTHY,
    )
    worker_1, worker_2 = clients()
    candidate = (unhealthy, worker_2) if worker_id is WorkerId.WORKER_1 else (worker_1, unhealthy)

    report = WorkerRegistry(candidate).qualify(qualified_at=NOW)

    assert not report.ready_for_environment_qualification
    assert expected_code in report.failure_codes


def test_unknown_health_is_not_treated_as_ready() -> None:
    worker_1 = StubWorkerClient(
        worker_id=WorkerId.WORKER_1,
        health_state=WorkerHealthState.UNKNOWN,
    )

    report = WorkerRegistry(clients(worker_1=worker_1)).qualify(qualified_at=NOW)

    assert not report.worker_for(WorkerId.WORKER_1).ready_for_invocation
    assert WorkerRegistryFailureCode.WORKER_1_NOT_READY in report.failure_codes


def test_model_identity_mismatch_is_explicit() -> None:
    worker_2 = StubWorkerClient(
        worker_id=WorkerId.WORKER_2,
        identity=worker_identity(WorkerId.WORKER_2, model=model_identity("3")),
    )

    report = WorkerRegistry(clients(worker_2=worker_2)).qualify(qualified_at=NOW)

    assert not report.model_identity_match
    assert not report.ready_for_environment_qualification
    assert WorkerRegistryFailureCode.MODEL_IDENTITY_MISMATCH in report.failure_codes


def test_tokenizer_identity_mismatch_is_explicit() -> None:
    worker_2 = StubWorkerClient(
        worker_id=WorkerId.WORKER_2,
        identity=worker_identity(
            WorkerId.WORKER_2,
            tokenizer=tokenizer_identity("4"),
        ),
    )

    report = WorkerRegistry(clients(worker_2=worker_2)).qualify(qualified_at=NOW)

    assert not report.tokenizer_identity_match
    assert WorkerRegistryFailureCode.TOKENIZER_IDENTITY_MISMATCH in report.failure_codes


def test_runtime_version_mismatch_is_explicit() -> None:
    worker_2 = StubWorkerClient(
        worker_id=WorkerId.WORKER_2,
        identity=worker_identity(
            WorkerId.WORKER_2,
            runtime_version="0.10.1.synthetic1",
        ),
    )

    report = WorkerRegistry(clients(worker_2=worker_2)).qualify(qualified_at=NOW)

    assert not report.runtime_version_match
    assert WorkerRegistryFailureCode.RUNTIME_VERSION_MISMATCH in report.failure_codes


def test_multiple_failures_are_unique_and_canonically_sorted() -> None:
    worker_1 = StubWorkerClient(
        worker_id=WorkerId.WORKER_1,
        health_state=WorkerHealthState.UNHEALTHY,
    )
    worker_2 = StubWorkerClient(
        worker_id=WorkerId.WORKER_2,
        health_state=WorkerHealthState.UNKNOWN,
        identity=worker_identity(
            WorkerId.WORKER_2,
            model=model_identity("5"),
            tokenizer=tokenizer_identity("6"),
            runtime_version="0.10.2.synthetic1",
        ),
    )

    report = WorkerRegistry(clients(worker_1=worker_1, worker_2=worker_2)).qualify(qualified_at=NOW)

    assert report.failure_codes == tuple(
        sorted(set(report.failure_codes), key=lambda code: code.value)
    )
    assert len(report.failure_codes) == 5


def test_qualification_calls_only_health_and_identity_once() -> None:
    worker_1, worker_2 = clients()

    WorkerRegistry((worker_1, worker_2)).qualify(qualified_at=NOW)

    for worker in (worker_1, worker_2):
        assert worker.health_calls == 1
        assert worker.identity_calls == 1
        assert worker.invoke_calls == 0
        assert worker.metrics_calls == 0
        assert worker.reset_calls == 0


def test_client_timeout_is_wrapped_with_worker_context() -> None:
    worker_1 = StubWorkerClient(
        worker_id=WorkerId.WORKER_1,
        health_error=TimeoutError("sensitive transport detail"),
    )

    with pytest.raises(WorkerRegistryError) as exc_info:
        WorkerRegistry(clients(worker_1=worker_1)).qualify(qualified_at=NOW)

    assert exc_info.value.code is WorkerRegistryErrorCode.CLIENT_OPERATION_FAILED
    assert exc_info.value.worker_id is WorkerId.WORKER_1
    assert "sensitive transport detail" not in str(exc_info.value)


def test_identity_worker_mismatch_is_wrapped_as_operation_failure() -> None:
    worker_1 = StubWorkerClient(
        worker_id=WorkerId.WORKER_1,
        identity=worker_identity(WorkerId.WORKER_2),
    )

    with pytest.raises(WorkerRegistryError) as exc_info:
        WorkerRegistry(clients(worker_1=worker_1)).qualify(qualified_at=NOW)

    assert exc_info.value.code is WorkerRegistryErrorCode.CLIENT_OPERATION_FAILED
    assert exc_info.value.worker_id is WorkerId.WORKER_1


def test_qualification_rejects_naive_timestamp() -> None:
    naive = datetime(2026, 7, 15, 16, 0)

    with pytest.raises(WorkerRegistryError) as exc_info:
        WorkerRegistry(clients()).qualify(qualified_at=naive)

    assert exc_info.value.code is WorkerRegistryErrorCode.INVALID_QUALIFICATION_TIME


def test_fresh_registries_produce_identical_reports() -> None:
    first = WorkerRegistry(clients()).qualify(qualified_at=NOW)
    second = WorkerRegistry(clients()).qualify(qualified_at=NOW)

    assert first == second
    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()


def test_worker_qualification_rejects_endpoint_identity_mismatch() -> None:
    valid = WorkerRegistry(clients()).qualify(qualified_at=NOW).workers[0]
    invalid_config = valid.config.model_copy(update={"base_url": "http://127.0.0.1:8002"})

    with pytest.raises(ValidationError, match="endpoint port"):
        WorkerQualification(
            worker_id=valid.worker_id,
            config=invalid_config,
            health=valid.health,
            identity=valid.identity,
            ready_for_invocation=valid.ready_for_invocation,
        )


def test_report_rejects_false_readiness_claim() -> None:
    valid = WorkerRegistry(clients()).qualify(qualified_at=NOW)

    with pytest.raises(ValidationError, match="readiness"):
        WorkerRegistryReport(
            qualified_at=valid.qualified_at,
            workers=valid.workers,
            model_identity_match=True,
            tokenizer_identity_match=True,
            runtime_version_match=True,
            ready_for_environment_qualification=False,
            failure_codes=(),
        )


def test_report_rejects_unsorted_failure_codes() -> None:
    valid = WorkerRegistry(clients()).qualify(qualified_at=NOW)
    first = valid.workers[0].model_copy(update={"ready_for_invocation": False})
    second = valid.workers[1].model_copy(update={"ready_for_invocation": False})

    with pytest.raises(ValidationError, match="canonically sorted"):
        WorkerRegistryReport(
            qualified_at=NOW,
            workers=(first, second),
            model_identity_match=True,
            tokenizer_identity_match=True,
            runtime_version_match=True,
            ready_for_environment_qualification=False,
            failure_codes=(
                WorkerRegistryFailureCode.WORKER_2_NOT_READY,
                WorkerRegistryFailureCode.WORKER_1_NOT_READY,
            ),
        )


def test_report_contains_only_metadata_evidence() -> None:
    report_text = repr(WorkerRegistry(clients()).qualify(qualified_at=NOW))

    assert "serialized_prefix" not in report_text
    assert "serialized_suffix" not in report_text
    assert "output_text" not in report_text
    assert str(TRACE_ID) not in report_text
