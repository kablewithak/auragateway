"""Fixed-topology worker registry for local A/B/C runtime qualification."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract, WorkerId, WorkerIdentity
from auragateway.local_abc.worker_client import (
    WorkerClient,
    WorkerClientBoundary,
    WorkerClientConfig,
    WorkerClientError,
    WorkerHealth,
)

_EXPECTED_PORTS: dict[WorkerId, int] = {
    WorkerId.WORKER_1: 8001,
    WorkerId.WORKER_2: 8002,
}
_EXPECTED_GPUS: dict[WorkerId, int] = {
    WorkerId.WORKER_1: 0,
    WorkerId.WORKER_2: 1,
}


class WorkerRegistryErrorCode(StrEnum):
    """Machine-readable worker-registry boundary failures."""

    INVALID_CLIENT_SET = "INVALID_CLIENT_SET"
    INVALID_CLIENT_BOUNDARY = "INVALID_CLIENT_BOUNDARY"
    CONFIG_TOPOLOGY_MISMATCH = "CONFIG_TOPOLOGY_MISMATCH"
    CLIENT_OPERATION_FAILED = "CLIENT_OPERATION_FAILED"
    INVALID_QUALIFICATION_TIME = "INVALID_QUALIFICATION_TIME"


class WorkerRegistryFailureCode(StrEnum):
    """Fail-closed reasons preventing environment qualification."""

    WORKER_1_NOT_READY = "WORKER_1_NOT_READY"
    WORKER_2_NOT_READY = "WORKER_2_NOT_READY"
    MODEL_IDENTITY_MISMATCH = "MODEL_IDENTITY_MISMATCH"
    TOKENIZER_IDENTITY_MISMATCH = "TOKENIZER_IDENTITY_MISMATCH"
    RUNTIME_VERSION_MISMATCH = "RUNTIME_VERSION_MISMATCH"


class WorkerRegistryError(RuntimeError):
    """Bounded registry failure without endpoint or payload disclosure."""

    def __init__(
        self,
        *,
        code: WorkerRegistryErrorCode,
        safe_detail: str,
        worker_id: WorkerId | None = None,
    ) -> None:
        self.code = code
        self.safe_detail = safe_detail
        self.worker_id = worker_id
        worker_fragment = f":{worker_id.value}" if worker_id is not None else ""
        super().__init__(f"{code.value}{worker_fragment}: {safe_detail}")


class WorkerQualification(LocalABCContract):
    """Observed health and identity evidence for one configured worker."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    worker_id: WorkerId
    config: WorkerClientConfig
    health: WorkerHealth
    identity: WorkerIdentity
    ready_for_invocation: bool

    @model_validator(mode="after")
    def validate_worker_evidence(self) -> Self:
        if self.config.worker_id is not self.worker_id:
            raise ValueError("worker qualification config identity mismatch")
        if self.health.worker_id is not self.worker_id:
            raise ValueError("worker qualification health identity mismatch")
        if self.identity.worker_id is not self.worker_id:
            raise ValueError("worker qualification runtime identity mismatch")
        if self.identity.gpu_index != _EXPECTED_GPUS[self.worker_id]:
            raise ValueError("worker qualification GPU topology mismatch")
        if self.identity.port != _EXPECTED_PORTS[self.worker_id]:
            raise ValueError("worker qualification port topology mismatch")
        if urlsplit(self.config.base_url).port != _EXPECTED_PORTS[self.worker_id]:
            raise ValueError("worker qualification endpoint port mismatch")
        if self.ready_for_invocation != self.health.ready_for_invocation:
            raise ValueError("worker readiness must exactly match observed health")
        return self


class WorkerRegistryReport(LocalABCContract):
    """Canonical two-worker readiness and parity qualification report."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    qualified_at: datetime
    workers: tuple[WorkerQualification, WorkerQualification]
    model_identity_match: bool
    tokenizer_identity_match: bool
    runtime_version_match: bool
    ready_for_environment_qualification: bool
    failure_codes: tuple[WorkerRegistryFailureCode, ...] = ()

    @field_validator("qualified_at")
    @classmethod
    def validate_qualified_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("qualified_at must be timezone-aware")
        return value

    @field_validator("failure_codes")
    @classmethod
    def validate_failure_codes(
        cls,
        value: tuple[WorkerRegistryFailureCode, ...],
    ) -> tuple[WorkerRegistryFailureCode, ...]:
        if len(value) != len(set(value)):
            raise ValueError("worker registry failure codes must be unique")
        if value != tuple(sorted(value, key=lambda code: code.value)):
            raise ValueError("worker registry failure codes must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_report(self) -> Self:
        if tuple(item.worker_id for item in self.workers) != tuple(WorkerId):
            raise ValueError("worker registry report requires canonical worker_1, worker_2 order")

        first, second = self.workers
        expected_model_match = first.identity.model == second.identity.model
        expected_tokenizer_match = first.identity.tokenizer == second.identity.tokenizer
        expected_runtime_match = first.identity.runtime_version == second.identity.runtime_version
        if self.model_identity_match != expected_model_match:
            raise ValueError("model_identity_match does not match observed worker identities")
        if self.tokenizer_identity_match != expected_tokenizer_match:
            raise ValueError("tokenizer_identity_match does not match observed worker identities")
        if self.runtime_version_match != expected_runtime_match:
            raise ValueError("runtime_version_match does not match observed worker identities")

        expected_failures = _failure_codes_for(
            self.workers,
            model_identity_match=expected_model_match,
            tokenizer_identity_match=expected_tokenizer_match,
            runtime_version_match=expected_runtime_match,
        )
        if self.failure_codes != expected_failures:
            raise ValueError("worker registry failure codes do not match observed evidence")
        if self.ready_for_environment_qualification != (not expected_failures):
            raise ValueError("environment qualification readiness must fail closed")
        return self

    def worker_for(self, worker_id: WorkerId) -> WorkerQualification:
        """Return one required worker qualification."""

        return self.workers[0 if worker_id is WorkerId.WORKER_1 else 1]


def _failure_codes_for(
    workers: tuple[WorkerQualification, WorkerQualification],
    *,
    model_identity_match: bool,
    tokenizer_identity_match: bool,
    runtime_version_match: bool,
) -> tuple[WorkerRegistryFailureCode, ...]:
    failure_codes: set[WorkerRegistryFailureCode] = set()
    first, second = workers
    if not first.ready_for_invocation:
        failure_codes.add(WorkerRegistryFailureCode.WORKER_1_NOT_READY)
    if not second.ready_for_invocation:
        failure_codes.add(WorkerRegistryFailureCode.WORKER_2_NOT_READY)
    if not model_identity_match:
        failure_codes.add(WorkerRegistryFailureCode.MODEL_IDENTITY_MISMATCH)
    if not tokenizer_identity_match:
        failure_codes.add(WorkerRegistryFailureCode.TOKENIZER_IDENTITY_MISMATCH)
    if not runtime_version_match:
        failure_codes.add(WorkerRegistryFailureCode.RUNTIME_VERSION_MISMATCH)
    return tuple(sorted(failure_codes, key=lambda code: code.value))


class WorkerRegistry:
    """Own exactly two validated clients behind the frozen local topology."""

    def __init__(self, clients: Sequence[WorkerClient]) -> None:
        clients_tuple = tuple(clients)
        if len(clients_tuple) != 2:
            raise WorkerRegistryError(
                code=WorkerRegistryErrorCode.INVALID_CLIENT_SET,
                safe_detail="worker registry requires exactly two clients",
            )

        try:
            boundaries = tuple(WorkerClientBoundary(client) for client in clients_tuple)
        except WorkerClientError as exc:
            raise WorkerRegistryError(
                code=WorkerRegistryErrorCode.INVALID_CLIENT_BOUNDARY,
                safe_detail="worker client failed registry-boundary validation",
            ) from exc

        by_id = {boundary.config.worker_id: boundary for boundary in boundaries}
        if len(by_id) != 2 or set(by_id) != set(WorkerId):
            raise WorkerRegistryError(
                code=WorkerRegistryErrorCode.INVALID_CLIENT_SET,
                safe_detail="worker registry requires unique worker_1 and worker_2 clients",
            )
        self._validate_config_topology(by_id)
        self._boundaries = by_id

    def boundary_for(self, worker_id: WorkerId) -> WorkerClientBoundary:
        """Return the validated boundary for one fixed worker identity."""

        return self._boundaries[worker_id]

    def qualify(self, *, qualified_at: datetime) -> WorkerRegistryReport:
        """Observe health and identity once per worker and produce a fail-closed report."""

        if qualified_at.tzinfo is None or qualified_at.utcoffset() is None:
            raise WorkerRegistryError(
                code=WorkerRegistryErrorCode.INVALID_QUALIFICATION_TIME,
                safe_detail="qualified_at must be timezone-aware",
            )

        qualifications: list[WorkerQualification] = []
        for worker_id in WorkerId:
            boundary = self._boundaries[worker_id]
            try:
                health = boundary.health()
                identity = boundary.identity()
            except WorkerClientError as exc:
                raise WorkerRegistryError(
                    code=WorkerRegistryErrorCode.CLIENT_OPERATION_FAILED,
                    safe_detail="worker health or identity qualification failed",
                    worker_id=worker_id,
                ) from exc
            qualifications.append(
                WorkerQualification(
                    worker_id=worker_id,
                    config=boundary.config,
                    health=health,
                    identity=identity,
                    ready_for_invocation=health.ready_for_invocation,
                )
            )

        first, second = qualifications
        workers = (first, second)
        model_identity_match = first.identity.model == second.identity.model
        tokenizer_identity_match = first.identity.tokenizer == second.identity.tokenizer
        runtime_version_match = first.identity.runtime_version == second.identity.runtime_version
        failure_codes = _failure_codes_for(
            workers,
            model_identity_match=model_identity_match,
            tokenizer_identity_match=tokenizer_identity_match,
            runtime_version_match=runtime_version_match,
        )
        return WorkerRegistryReport(
            qualified_at=qualified_at,
            workers=workers,
            model_identity_match=model_identity_match,
            tokenizer_identity_match=tokenizer_identity_match,
            runtime_version_match=runtime_version_match,
            ready_for_environment_qualification=not failure_codes,
            failure_codes=failure_codes,
        )

    @staticmethod
    def _validate_config_topology(
        boundaries: dict[WorkerId, WorkerClientBoundary],
    ) -> None:
        parsed = {
            worker_id: urlsplit(boundary.config.base_url)
            for worker_id, boundary in boundaries.items()
        }
        for worker_id, endpoint in parsed.items():
            if endpoint.port != _EXPECTED_PORTS[worker_id]:
                raise WorkerRegistryError(
                    code=WorkerRegistryErrorCode.CONFIG_TOPOLOGY_MISMATCH,
                    safe_detail="worker endpoint port violates the fixed topology",
                    worker_id=worker_id,
                )
        first = parsed[WorkerId.WORKER_1]
        second = parsed[WorkerId.WORKER_2]
        if (first.scheme, first.hostname) != (second.scheme, second.hostname):
            raise WorkerRegistryError(
                code=WorkerRegistryErrorCode.CONFIG_TOPOLOGY_MISMATCH,
                safe_detail="both workers must share one local scheme and hostname",
            )
