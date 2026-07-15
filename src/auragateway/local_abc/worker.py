"""Deterministic fake-worker harness for the controlled local A/B/C experiment."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import (
    CacheObservation,
    CacheObservationState,
    LocalABCContract,
    TelemetryObservation,
    TrajectoryRecord,
    TrajectoryTerminalState,
    WorkerId,
)
from auragateway.local_abc.errors import LocalABCFailureCode
from auragateway.local_abc.route_scheduler import ScheduledRoute, TurnIndex

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_FAKE_METRIC_NAME = "fake.cached_prefix_tokens"
_FAKE_METRIC_MAPPING_VERSION = "fake-local-abc-v1"


class FakeWorkerMode(StrEnum):
    """Deterministic behavior selected for one local fake worker."""

    POSITIVE_REUSE = "positive_reuse"
    ZERO_REUSE = "zero_reuse"
    TELEMETRY_NOT_EXPOSED = "telemetry_not_exposed"
    INTERRUPT_ON_TURN_2 = "interrupt_on_turn_2"
    RESET_FAILURE = "reset_failure"


class FakeWorkerError(RuntimeError):
    """Bounded fake-worker failure carrying the project error taxonomy."""

    def __init__(self, code: LocalABCFailureCode, safe_detail: str) -> None:
        self.code = code
        self.safe_detail = safe_detail
        super().__init__(f"{code.value}: {safe_detail}")


class FakeTurnRequest(LocalABCContract):
    """Metadata-only request used by the deterministic fake worker."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    trajectory_id: str
    turn_index: TurnIndex
    eligible_shared_prefix_tokens: int = Field(gt=0)
    collected_at: datetime

    @field_validator("trajectory_id")
    @classmethod
    def validate_trajectory_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trajectory_id must use stable lowercase characters")
        return value

    @field_validator("collected_at")
    @classmethod
    def validate_collected_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("collected_at must be timezone-aware")
        return value


class FakeTurnResult(LocalABCContract):
    """One deterministic fake-worker result with normalized telemetry."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    worker_id: WorkerId
    turn_index: TurnIndex
    telemetry: TelemetryObservation

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if self.telemetry.worker_id is not self.worker_id:
            raise ValueError("fake result worker must match telemetry worker")
        return self


class FakeTrajectoryRequest(LocalABCContract):
    """Complete synthetic trajectory request for the local fake-worker registry."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    trajectory_id: str
    trace_id: UUID
    case_id: str
    replication_id: str
    route: ScheduledRoute
    turns: tuple[FakeTurnRequest, FakeTurnRequest]
    realized_route_override: tuple[WorkerId, WorkerId] | None = None

    @field_validator("trajectory_id", "case_id", "replication_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("fake trajectory identifiers must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_turns(self) -> Self:
        if tuple(turn.turn_index for turn in self.turns) != (1, 2):
            raise ValueError("fake trajectories require ordered turns 1 and 2")
        if any(turn.trajectory_id != self.trajectory_id for turn in self.turns):
            raise ValueError("fake turn trajectory IDs must match the trajectory request")
        return self


class FakeWorker:
    """Stateful local fake with explicit reset and deterministic telemetry behavior."""

    def __init__(self, *, worker_id: WorkerId, mode: FakeWorkerMode) -> None:
        self.worker_id = worker_id
        self.mode = mode
        self._invocation_count = 0
        self._invocations_since_reset = 0
        self._reset_count = 0
        self._reset_verified = False

    @property
    def invocation_count(self) -> int:
        """Return attempted fake invocations, including interrupted attempts."""

        return self._invocation_count

    @property
    def reset_count(self) -> int:
        """Return successful reset count."""

        return self._reset_count

    @property
    def reset_verified(self) -> bool:
        """Return whether this worker belongs to the current verified reset window."""

        return self._reset_verified

    def reset_cache(self) -> None:
        """Verify a synthetic clean baseline or fail before any trajectory starts."""

        self._reset_verified = False
        if self.mode is FakeWorkerMode.RESET_FAILURE:
            raise FakeWorkerError(
                LocalABCFailureCode.CACHE_RESET_FAILED,
                f"synthetic cache reset failed for {self.worker_id.value}",
            )
        self._reset_count += 1
        self._invocations_since_reset = 0
        self._reset_verified = True

    def invalidate_reset(self) -> None:
        """Close the current one-trajectory reset authorization window."""

        self._reset_verified = False

    def invoke(self, request: FakeTurnRequest) -> FakeTurnResult:
        """Return deterministic normalized telemetry or an explicit interruption."""

        if not self._reset_verified:
            raise FakeWorkerError(
                LocalABCFailureCode.CACHE_RESET_FAILED,
                "fake worker invocation requires a verified reset",
            )

        self._invocation_count += 1
        self._invocations_since_reset += 1
        if self.mode is FakeWorkerMode.INTERRUPT_ON_TURN_2 and request.turn_index == 2:
            raise FakeWorkerError(
                LocalABCFailureCode.SESSION_INTERRUPTED,
                "synthetic interruption occurred during turn 2",
            )
        if self.mode is FakeWorkerMode.RESET_FAILURE:
            raise FakeWorkerError(
                LocalABCFailureCode.CACHE_RESET_FAILED,
                "reset-failure workers cannot be invoked",
            )

        return FakeTurnResult(
            worker_id=self.worker_id,
            turn_index=request.turn_index,
            telemetry=self._build_telemetry(request),
        )

    def _build_telemetry(self, request: FakeTurnRequest) -> TelemetryObservation:
        eligible = request.eligible_shared_prefix_tokens
        observation_id = self._observation_id(request)

        if self.mode is FakeWorkerMode.TELEMETRY_NOT_EXPOSED:
            return TelemetryObservation(
                observation_id=observation_id,
                worker_id=self.worker_id,
                collected_at=request.collected_at,
                metric_mapping_version=_FAKE_METRIC_MAPPING_VERSION,
                cache=CacheObservation(
                    state=CacheObservationState.NOT_EXPOSED,
                    reason_code=LocalABCFailureCode.TELEMETRY_NOT_EXPOSED,
                ),
                eligible_shared_prefix_tokens=eligible,
            )

        cached_tokens = 0
        if self.mode is FakeWorkerMode.POSITIVE_REUSE and self._invocations_since_reset > 1:
            cached_tokens = max(1, eligible // 2)
        newly_computed = eligible - cached_tokens
        cache_state = (
            CacheObservationState.POSITIVE if cached_tokens > 0 else CacheObservationState.ZERO
        )
        prefill_duration_ms = float(newly_computed) + 0.25
        time_to_first_token_ms = prefill_duration_ms + 1.0

        return TelemetryObservation(
            observation_id=observation_id,
            worker_id=self.worker_id,
            collected_at=request.collected_at,
            metric_mapping_version=_FAKE_METRIC_MAPPING_VERSION,
            cache=CacheObservation(
                state=cache_state,
                raw_metric_name=_FAKE_METRIC_NAME,
                observed_cached_prefix_tokens=cached_tokens,
            ),
            eligible_shared_prefix_tokens=eligible,
            newly_computed_prefill_tokens=newly_computed,
            prefill_duration_ms=prefill_duration_ms,
            time_to_first_token_ms=time_to_first_token_ms,
            end_to_end_latency_ms=time_to_first_token_ms + 2.0,
        )

    def _observation_id(self, request: FakeTurnRequest) -> str:
        material = (f"{request.trajectory_id}:{self.worker_id.value}:{request.turn_index}").encode()
        digest = hashlib.sha256(material).hexdigest()[:24]
        return f"obs-{digest}"


class FakeWorkerRegistry:
    """Two-worker registry executing one reset-gated synthetic trajectory at a time."""

    def __init__(self, workers: Sequence[FakeWorker]) -> None:
        workers_tuple = tuple(workers)
        workers_by_id = {worker.worker_id: worker for worker in workers_tuple}
        if len(workers_tuple) != 2 or set(workers_by_id) != set(WorkerId):
            raise ValueError("fake registry requires exactly worker_1 and worker_2")
        if len(workers_by_id) != len(workers_tuple):
            raise ValueError("fake registry worker identities must be unique")
        self._workers = workers_by_id
        self._reset_verified = False

    def reset_all(self) -> None:
        """Reset both workers and open one trajectory execution window."""

        self._reset_verified = False
        for worker in self._workers.values():
            worker.invalidate_reset()

        try:
            for worker_id in WorkerId:
                self._workers[worker_id].reset_cache()
        except FakeWorkerError:
            for worker in self._workers.values():
                worker.invalidate_reset()
            raise

        self._reset_verified = True

    def run_trajectory(self, request: FakeTrajectoryRequest) -> TrajectoryRecord:
        """Execute one deterministic synthetic trajectory and retain partial outcomes."""

        if not self._reset_verified:
            raise FakeWorkerError(
                LocalABCFailureCode.CACHE_RESET_FAILED,
                "registry reset_all must pass before trajectory execution",
            )
        validated = self._revalidate_request(request)
        intended_route = validated.route.schedule.workers
        realized_route = validated.realized_route_override or intended_route
        fallback_used = realized_route != intended_route
        failure_codes: set[LocalABCFailureCode] = set()
        if fallback_used:
            failure_codes.add(LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH)

        telemetry: list[TelemetryObservation] = []
        attempted_workers: list[WorkerId] = []
        try:
            for turn, worker_id in zip(validated.turns, realized_route, strict=True):
                attempted_workers.append(worker_id)
                try:
                    result = self._workers[worker_id].invoke(turn)
                except FakeWorkerError as exc:
                    if exc.code is not LocalABCFailureCode.SESSION_INTERRUPTED:
                        raise
                    failure_codes.add(exc.code)
                    return TrajectoryRecord(
                        trajectory_id=validated.trajectory_id,
                        trace_id=validated.trace_id,
                        case_id=validated.case_id,
                        replication_id=validated.replication_id,
                        condition_id=validated.route.condition_id,
                        intended_route=validated.route.schedule,
                        realized_route=tuple(attempted_workers),
                        terminal_state=TrajectoryTerminalState.INTERRUPTED,
                        task_completed=False,
                        fallback_used=fallback_used,
                        telemetry=tuple(telemetry),
                        failure_codes=self._ordered_failure_codes(failure_codes),
                    )
                telemetry.append(result.telemetry)

            return TrajectoryRecord(
                trajectory_id=validated.trajectory_id,
                trace_id=validated.trace_id,
                case_id=validated.case_id,
                replication_id=validated.replication_id,
                condition_id=validated.route.condition_id,
                intended_route=validated.route.schedule,
                realized_route=tuple(attempted_workers),
                terminal_state=TrajectoryTerminalState.COMPLETED,
                task_completed=True,
                fallback_used=fallback_used,
                telemetry=tuple(telemetry),
                failure_codes=self._ordered_failure_codes(failure_codes),
            )
        finally:
            self._reset_verified = False
            for worker in self._workers.values():
                worker.invalidate_reset()

    @staticmethod
    def _revalidate_request(request: FakeTrajectoryRequest) -> FakeTrajectoryRequest:
        try:
            return FakeTrajectoryRequest.model_validate(request.model_dump(mode="python"))
        except ValidationError as exc:
            raise FakeWorkerError(
                LocalABCFailureCode.RUN_INELIGIBLE,
                "fake trajectory request failed strict revalidation",
            ) from exc

    @staticmethod
    def _ordered_failure_codes(
        failure_codes: set[LocalABCFailureCode],
    ) -> tuple[LocalABCFailureCode, ...]:
        return tuple(sorted(failure_codes, key=lambda code: code.value))
