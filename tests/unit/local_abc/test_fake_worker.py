from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from auragateway.local_abc.contracts import (
    CacheObservationState,
    ConditionDefinition,
    ConditionId,
    PrefixIdentity,
    PrefixPolicy,
    RouteSchedule,
    TrajectoryTerminalState,
    WorkerId,
)
from auragateway.local_abc.errors import LocalABCFailureCode
from auragateway.local_abc.route_scheduler import DeterministicRouteScheduler
from auragateway.local_abc.worker import (
    FakeTrajectoryRequest,
    FakeTurnRequest,
    FakeWorker,
    FakeWorkerError,
    FakeWorkerMode,
    FakeWorkerRegistry,
)

NOW = datetime(2026, 7, 15, 8, 0, tzinfo=UTC)
TRACE_ID = UUID("11111111-1111-4111-8111-111111111111")


def prefix_identity() -> PrefixIdentity:
    return PrefixIdentity(
        serializer_version="1.0.0",
        token_hash="1" * 64,
        token_count=128,
        tokenizer_fingerprint="2" * 64,
    )


def condition_definition(condition_id: ConditionId) -> ConditionDefinition:
    schedules = {
        ConditionId.A: (WorkerId.WORKER_1, WorkerId.WORKER_2),
        ConditionId.B: (WorkerId.WORKER_1, WorkerId.WORKER_2),
        ConditionId.C: (WorkerId.WORKER_1, WorkerId.WORKER_1),
    }
    policy = (
        PrefixPolicy.CACHE_HOSTILE
        if condition_id is ConditionId.A
        else PrefixPolicy.DETERMINISTIC_EXACT
    )
    return ConditionDefinition(
        condition_id=condition_id,
        prefix_policy=policy,
        route_schedule=RouteSchedule(workers=schedules[condition_id]),
        prefix_identity=prefix_identity(),
    )


def trajectory_request(
    condition_id: ConditionId,
    *,
    realized_route_override: tuple[WorkerId, WorkerId] | None = None,
    trajectory_id: str = "trajectory-001",
) -> FakeTrajectoryRequest:
    route = DeterministicRouteScheduler().schedule_condition(condition_definition(condition_id))
    return FakeTrajectoryRequest(
        trajectory_id=trajectory_id,
        trace_id=TRACE_ID,
        case_id="case-001",
        replication_id="replication-001",
        route=route,
        turns=(
            FakeTurnRequest(
                trajectory_id=trajectory_id,
                turn_index=1,
                eligible_shared_prefix_tokens=128,
                collected_at=NOW,
            ),
            FakeTurnRequest(
                trajectory_id=trajectory_id,
                turn_index=2,
                eligible_shared_prefix_tokens=128,
                collected_at=NOW,
            ),
        ),
        realized_route_override=realized_route_override,
    )


def registry(
    *,
    worker_1_mode: FakeWorkerMode = FakeWorkerMode.ZERO_REUSE,
    worker_2_mode: FakeWorkerMode = FakeWorkerMode.ZERO_REUSE,
) -> tuple[FakeWorkerRegistry, FakeWorker, FakeWorker]:
    worker_1 = FakeWorker(worker_id=WorkerId.WORKER_1, mode=worker_1_mode)
    worker_2 = FakeWorker(worker_id=WorkerId.WORKER_2, mode=worker_2_mode)
    return FakeWorkerRegistry((worker_1, worker_2)), worker_1, worker_2


def test_positive_reuse_is_explicit_on_second_same_worker_turn() -> None:
    workers, _, _ = registry(worker_1_mode=FakeWorkerMode.POSITIVE_REUSE)
    workers.reset_all()

    trajectory = workers.run_trajectory(trajectory_request(ConditionId.C))

    assert trajectory.terminal_state is TrajectoryTerminalState.COMPLETED
    assert trajectory.realized_route == (WorkerId.WORKER_1, WorkerId.WORKER_1)
    assert tuple(item.cache.state for item in trajectory.telemetry) == (
        CacheObservationState.ZERO,
        CacheObservationState.POSITIVE,
    )
    assert trajectory.telemetry[1].cache.observed_cached_prefix_tokens == 64


def test_positive_mode_does_not_invent_cross_worker_reuse() -> None:
    workers, _, _ = registry(
        worker_1_mode=FakeWorkerMode.POSITIVE_REUSE,
        worker_2_mode=FakeWorkerMode.POSITIVE_REUSE,
    )
    workers.reset_all()

    trajectory = workers.run_trajectory(trajectory_request(ConditionId.B))

    assert tuple(item.cache.state for item in trajectory.telemetry) == (
        CacheObservationState.ZERO,
        CacheObservationState.ZERO,
    )


def test_zero_reuse_remains_observed_zero_not_missing() -> None:
    workers, _, _ = registry()
    workers.reset_all()

    trajectory = workers.run_trajectory(trajectory_request(ConditionId.B))

    assert all(item.cache.state is CacheObservationState.ZERO for item in trajectory.telemetry)
    assert all(item.cache.observed_cached_prefix_tokens == 0 for item in trajectory.telemetry)
    assert all(item.cache.raw_metric_name is not None for item in trajectory.telemetry)


def test_absent_telemetry_uses_not_exposed_without_numeric_substitution() -> None:
    workers, _, _ = registry(
        worker_1_mode=FakeWorkerMode.TELEMETRY_NOT_EXPOSED,
        worker_2_mode=FakeWorkerMode.TELEMETRY_NOT_EXPOSED,
    )
    workers.reset_all()

    trajectory = workers.run_trajectory(trajectory_request(ConditionId.B))

    for observation in trajectory.telemetry:
        assert observation.cache.state is CacheObservationState.NOT_EXPOSED
        assert observation.cache.observed_cached_prefix_tokens is None
        assert observation.cache.reason_code is LocalABCFailureCode.TELEMETRY_NOT_EXPOSED
        assert observation.newly_computed_prefill_tokens is None
        assert observation.prefill_duration_ms is None


def test_reset_failure_blocks_execution_before_any_invocation() -> None:
    workers, worker_1, worker_2 = registry(worker_2_mode=FakeWorkerMode.RESET_FAILURE)

    with pytest.raises(FakeWorkerError) as exc_info:
        workers.reset_all()

    assert exc_info.value.code is LocalABCFailureCode.CACHE_RESET_FAILED
    assert worker_1.invocation_count == 0
    assert worker_2.invocation_count == 0
    assert not worker_1.reset_verified
    assert not worker_2.reset_verified

    with pytest.raises(FakeWorkerError) as run_exc:
        workers.run_trajectory(trajectory_request(ConditionId.B))
    assert run_exc.value.code is LocalABCFailureCode.CACHE_RESET_FAILED


def test_trajectory_requires_a_verified_reset() -> None:
    workers, _, _ = registry()

    with pytest.raises(FakeWorkerError) as exc_info:
        workers.run_trajectory(trajectory_request(ConditionId.A))

    assert exc_info.value.code is LocalABCFailureCode.CACHE_RESET_FAILED


def test_explicit_route_mismatch_is_retained_as_fallback() -> None:
    workers, _, _ = registry()
    workers.reset_all()

    trajectory = workers.run_trajectory(
        trajectory_request(
            ConditionId.B,
            realized_route_override=(WorkerId.WORKER_1, WorkerId.WORKER_1),
        )
    )

    assert trajectory.task_completed
    assert trajectory.fallback_used
    assert trajectory.realized_route == (WorkerId.WORKER_1, WorkerId.WORKER_1)
    assert LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH in trajectory.failure_codes


def test_interruption_retains_partial_telemetry_and_attempted_route() -> None:
    workers, _, _ = registry(worker_1_mode=FakeWorkerMode.INTERRUPT_ON_TURN_2)
    workers.reset_all()

    trajectory = workers.run_trajectory(trajectory_request(ConditionId.C))

    assert trajectory.terminal_state is TrajectoryTerminalState.INTERRUPTED
    assert not trajectory.task_completed
    assert trajectory.realized_route == (WorkerId.WORKER_1, WorkerId.WORKER_1)
    assert len(trajectory.telemetry) == 1
    assert LocalABCFailureCode.SESSION_INTERRUPTED in trajectory.failure_codes


def test_one_reset_authorizes_exactly_one_trajectory() -> None:
    workers, _, _ = registry()
    request = trajectory_request(ConditionId.B)
    workers.reset_all()

    workers.run_trajectory(request)

    with pytest.raises(FakeWorkerError) as exc_info:
        workers.run_trajectory(request)
    assert exc_info.value.code is LocalABCFailureCode.CACHE_RESET_FAILED


def test_fresh_registries_produce_identical_evidence() -> None:
    first_registry, _, _ = registry(worker_1_mode=FakeWorkerMode.POSITIVE_REUSE)
    second_registry, _, _ = registry(worker_1_mode=FakeWorkerMode.POSITIVE_REUSE)
    request = trajectory_request(ConditionId.C)
    first_registry.reset_all()
    second_registry.reset_all()

    first = first_registry.run_trajectory(request)
    second = second_registry.run_trajectory(request)

    assert first == second
    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()


@pytest.mark.parametrize(
    "workers",
    [
        (),
        (FakeWorker(worker_id=WorkerId.WORKER_1, mode=FakeWorkerMode.ZERO_REUSE),),
        (
            FakeWorker(worker_id=WorkerId.WORKER_1, mode=FakeWorkerMode.ZERO_REUSE),
            FakeWorker(worker_id=WorkerId.WORKER_1, mode=FakeWorkerMode.POSITIVE_REUSE),
        ),
    ],
)
def test_registry_requires_exactly_two_unique_worker_identities(
    workers: tuple[FakeWorker, ...],
) -> None:
    with pytest.raises(ValueError, match=r"exactly worker_1 and worker_2|identities"):
        FakeWorkerRegistry(workers)


def test_request_rejects_mismatched_turn_trajectory_ids() -> None:
    valid = trajectory_request(ConditionId.B)
    invalid_turn = valid.turns[1].model_copy(update={"trajectory_id": "trajectory-999"})

    with pytest.raises(ValidationError, match="trajectory IDs"):
        FakeTrajectoryRequest(
            trajectory_id=valid.trajectory_id,
            trace_id=valid.trace_id,
            case_id=valid.case_id,
            replication_id=valid.replication_id,
            route=valid.route,
            turns=(valid.turns[0], invalid_turn),
        )


def test_strict_revalidation_rejects_tampered_request() -> None:
    workers, _, _ = registry()
    valid = trajectory_request(ConditionId.B)
    tampered = valid.model_copy(update={"turns": (valid.turns[0], valid.turns[0])})
    workers.reset_all()

    with pytest.raises(FakeWorkerError) as exc_info:
        workers.run_trajectory(tampered)

    assert exc_info.value.code is LocalABCFailureCode.RUN_INELIGIBLE
