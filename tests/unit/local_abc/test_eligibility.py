from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from auragateway.local_abc.contracts import (
    CacheObservation,
    CacheObservationState,
    ConditionDefinition,
    ConditionId,
    PrefixIdentity,
    PrefixPolicy,
    RouteSchedule,
    RunTerminalClassification,
    TelemetryObservation,
    TrajectoryRecord,
    TrajectoryTerminalState,
    WorkerId,
)
from auragateway.local_abc.eligibility import (
    EligibilityEvaluationError,
    EligibilityEvaluationErrorCode,
    EligibilityEvaluator,
)
from auragateway.local_abc.errors import LocalABCFailureCode
from auragateway.local_abc.route_scheduler import DeterministicRouteScheduler
from auragateway.local_abc.worker import (
    FakeTrajectoryRequest,
    FakeTurnRequest,
    FakeWorker,
    FakeWorkerMode,
    FakeWorkerRegistry,
)

NOW = datetime(2026, 7, 15, 8, 0, tzinfo=UTC)
TRACE_ID = UUID("22222222-2222-4222-8222-222222222222")


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


def fake_trajectory(
    condition_id: ConditionId,
    *,
    worker_1_mode: FakeWorkerMode = FakeWorkerMode.ZERO_REUSE,
    worker_2_mode: FakeWorkerMode = FakeWorkerMode.ZERO_REUSE,
    realized_route_override: tuple[WorkerId, WorkerId] | None = None,
    trajectory_id: str = "trajectory-001",
) -> TrajectoryRecord:
    workers = FakeWorkerRegistry(
        (
            FakeWorker(worker_id=WorkerId.WORKER_1, mode=worker_1_mode),
            FakeWorker(worker_id=WorkerId.WORKER_2, mode=worker_2_mode),
        )
    )
    route = DeterministicRouteScheduler().schedule_condition(condition_definition(condition_id))
    request = FakeTrajectoryRequest(
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
    workers.reset_all()
    return workers.run_trajectory(request)


def test_positive_reuse_completed_route_is_comparison_and_affinity_eligible() -> None:
    trajectory = fake_trajectory(
        ConditionId.C,
        worker_1_mode=FakeWorkerMode.POSITIVE_REUSE,
    )

    decision = EligibilityEvaluator().evaluate(trajectory)

    assert decision.terminal_classification is RunTerminalClassification.COMPLETED_ELIGIBLE
    assert decision.comparison_eligible
    assert decision.affinity_comparison_eligible
    assert decision.telemetry_sufficient
    assert decision.route_realized
    assert decision.failure_codes == ()


def test_observed_zero_reuse_remains_comparison_eligible() -> None:
    decision = EligibilityEvaluator().evaluate(fake_trajectory(ConditionId.B))

    assert decision.comparison_eligible
    assert decision.affinity_comparison_eligible
    assert decision.telemetry_sufficient


def test_condition_a_can_be_comparison_eligible_but_not_affinity_eligible() -> None:
    decision = EligibilityEvaluator().evaluate(fake_trajectory(ConditionId.A))

    assert decision.comparison_eligible
    assert not decision.affinity_comparison_eligible


def test_absent_telemetry_is_task_complete_but_comparison_ineligible() -> None:
    trajectory = fake_trajectory(
        ConditionId.B,
        worker_1_mode=FakeWorkerMode.TELEMETRY_NOT_EXPOSED,
        worker_2_mode=FakeWorkerMode.TELEMETRY_NOT_EXPOSED,
    )

    decision = EligibilityEvaluator().evaluate(trajectory)

    assert decision.task_completed
    assert not decision.comparison_eligible
    assert not decision.telemetry_sufficient
    assert decision.terminal_classification is RunTerminalClassification.COMPLETED_INELIGIBLE
    assert decision.failure_codes == (LocalABCFailureCode.TELEMETRY_NOT_EXPOSED,)


def test_route_mismatch_retains_task_completion_but_blocks_comparison() -> None:
    trajectory = fake_trajectory(
        ConditionId.B,
        realized_route_override=(WorkerId.WORKER_1, WorkerId.WORKER_1),
    )

    decision = EligibilityEvaluator().evaluate(trajectory)

    assert decision.task_completed
    assert decision.fallback_used
    assert not decision.route_realized
    assert not decision.comparison_eligible
    assert not decision.affinity_comparison_eligible
    assert (
        decision.terminal_classification
        is RunTerminalClassification.TASK_COMPLETED_BUT_COMPARISON_INELIGIBLE
    )
    assert LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH in decision.failure_codes


def test_interruption_is_retained_and_never_comparison_eligible() -> None:
    trajectory = fake_trajectory(
        ConditionId.C,
        worker_1_mode=FakeWorkerMode.INTERRUPT_ON_TURN_2,
    )

    decision = EligibilityEvaluator().evaluate(trajectory)

    assert decision.terminal_classification is RunTerminalClassification.INTERRUPTED_RETAINED
    assert not decision.task_completed
    assert not decision.comparison_eligible
    assert not decision.telemetry_sufficient
    assert LocalABCFailureCode.SESSION_INTERRUPTED in decision.failure_codes


def test_observed_cache_without_complete_numeric_metrics_fails_closed() -> None:
    trajectory = fake_trajectory(ConditionId.B)
    incomplete = trajectory.telemetry[0].model_copy(update={"prefill_duration_ms": None})
    tampered = trajectory.model_copy(update={"telemetry": (incomplete, trajectory.telemetry[1])})

    decision = EligibilityEvaluator().evaluate(tampered)

    assert not decision.telemetry_sufficient
    assert not decision.comparison_eligible
    assert LocalABCFailureCode.TELEMETRY_INVALID in decision.failure_codes


def test_cached_and_newly_computed_tokens_must_reconcile_to_eligible_prefix() -> None:
    trajectory = fake_trajectory(ConditionId.B)
    inconsistent = trajectory.telemetry[0].model_copy(update={"newly_computed_prefill_tokens": 127})
    tampered = trajectory.model_copy(update={"telemetry": (inconsistent, trajectory.telemetry[1])})

    decision = EligibilityEvaluator().evaluate(tampered)

    assert not decision.telemetry_sufficient
    assert LocalABCFailureCode.TELEMETRY_INVALID in decision.failure_codes


def test_failed_attempt_is_retained_with_explicit_ineligibility() -> None:
    trajectory = TrajectoryRecord(
        trajectory_id="trajectory-failed",
        trace_id=TRACE_ID,
        case_id="case-001",
        replication_id="replication-001",
        condition_id=ConditionId.B,
        intended_route=RouteSchedule(workers=(WorkerId.WORKER_1, WorkerId.WORKER_2)),
        realized_route=(WorkerId.WORKER_1,),
        terminal_state=TrajectoryTerminalState.FAILED,
        task_completed=False,
        telemetry=(),
        failure_codes=(LocalABCFailureCode.WORKER_START_FAILED,),
    )

    decision = EligibilityEvaluator().evaluate(trajectory)

    assert decision.terminal_classification is RunTerminalClassification.FAILED_RETAINED
    assert not decision.comparison_eligible
    assert decision.failure_codes == (LocalABCFailureCode.WORKER_START_FAILED,)


def test_evaluate_many_preserves_every_attempt_and_input_order() -> None:
    trajectories = (
        fake_trajectory(ConditionId.A, trajectory_id="trajectory-001"),
        fake_trajectory(
            ConditionId.B,
            trajectory_id="trajectory-002",
            worker_1_mode=FakeWorkerMode.TELEMETRY_NOT_EXPOSED,
            worker_2_mode=FakeWorkerMode.TELEMETRY_NOT_EXPOSED,
        ),
        fake_trajectory(
            ConditionId.C,
            trajectory_id="trajectory-003",
            worker_1_mode=FakeWorkerMode.INTERRUPT_ON_TURN_2,
        ),
    )

    decisions = EligibilityEvaluator().evaluate_many(trajectories)

    assert tuple(item.trajectory_id for item in decisions) == (
        "trajectory-001",
        "trajectory-002",
        "trajectory-003",
    )
    assert len(decisions) == len(trajectories)


def test_existing_failure_code_blocks_otherwise_valid_comparison() -> None:
    trajectory = fake_trajectory(ConditionId.B)
    marked = trajectory.model_copy(update={"failure_codes": (LocalABCFailureCode.RUN_INELIGIBLE,)})

    decision = EligibilityEvaluator().evaluate(marked)

    assert not decision.comparison_eligible
    assert decision.terminal_classification is RunTerminalClassification.COMPLETED_INELIGIBLE
    assert decision.failure_codes == (LocalABCFailureCode.RUN_INELIGIBLE,)


def test_failure_codes_are_deterministically_sorted() -> None:
    trajectory = fake_trajectory(
        ConditionId.B,
        realized_route_override=(WorkerId.WORKER_1, WorkerId.WORKER_1),
    )
    marked = trajectory.model_copy(
        update={
            "failure_codes": (
                LocalABCFailureCode.RUN_INELIGIBLE,
                LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH,
            )
        }
    )

    decision = EligibilityEvaluator().evaluate(marked)

    assert decision.failure_codes == tuple(
        sorted(decision.failure_codes, key=lambda code: code.value)
    )


def test_strict_revalidation_rejects_invalid_model_copy() -> None:
    valid = fake_trajectory(ConditionId.B)
    tampered = valid.model_copy(update={"task_completed": False})

    with pytest.raises(EligibilityEvaluationError) as exc_info:
        EligibilityEvaluator().evaluate(tampered)

    assert exc_info.value.code is EligibilityEvaluationErrorCode.INVALID_TRAJECTORY


def test_not_observed_telemetry_is_not_treated_as_zero() -> None:
    base = fake_trajectory(ConditionId.B)
    not_observed = TelemetryObservation(
        observation_id="obs-not-observed",
        worker_id=WorkerId.WORKER_1,
        collected_at=NOW,
        metric_mapping_version="fake-local-abc-v1",
        cache=CacheObservation(
            state=CacheObservationState.NOT_OBSERVED,
            raw_metric_name="fake.cached_prefix_tokens",
            reason_code=LocalABCFailureCode.TELEMETRY_NOT_OBSERVED,
        ),
        eligible_shared_prefix_tokens=128,
    )
    trajectory = base.model_copy(update={"telemetry": (not_observed, base.telemetry[1])})

    decision = EligibilityEvaluator().evaluate(trajectory)

    assert not decision.telemetry_sufficient
    assert LocalABCFailureCode.TELEMETRY_NOT_OBSERVED in decision.failure_codes
    assert not decision.comparison_eligible
