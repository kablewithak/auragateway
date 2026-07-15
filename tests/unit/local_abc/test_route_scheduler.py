from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.local_abc.contracts import (
    ConditionDefinition,
    ConditionId,
    PrefixIdentity,
    PrefixPolicy,
    RouteSchedule,
    WorkerId,
)
from auragateway.local_abc.route_scheduler import (
    DeterministicRouteScheduler,
    ExperimentRoutePlan,
    RouteDecision,
    RouteReason,
    RouteSchedulingError,
    RouteSchedulingErrorCode,
    ScheduledRoute,
)


def prefix_identity(fill: str = "1") -> PrefixIdentity:
    return PrefixIdentity(
        serializer_version="1.0.0",
        token_hash=fill * 64,
        token_count=128,
        tokenizer_fingerprint="2" * 64,
    )


def condition_definition(
    condition_id: ConditionId,
    *,
    identity: PrefixIdentity | None = None,
) -> ConditionDefinition:
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
        prefix_identity=identity or prefix_identity(),
    )


def definitions() -> tuple[ConditionDefinition, ConditionDefinition, ConditionDefinition]:
    shared_identity = prefix_identity()
    return (
        condition_definition(ConditionId.A, identity=prefix_identity("3")),
        condition_definition(ConditionId.B, identity=shared_identity),
        condition_definition(ConditionId.C, identity=shared_identity),
    )


@pytest.mark.parametrize(
    ("condition_id", "expected_workers", "expected_reasons"),
    [
        (
            ConditionId.A,
            (WorkerId.WORKER_1, WorkerId.WORKER_2),
            (RouteReason.INITIAL_DESTINATION, RouteReason.CONTROLLED_CROSS_WORKER),
        ),
        (
            ConditionId.B,
            (WorkerId.WORKER_1, WorkerId.WORKER_2),
            (RouteReason.INITIAL_DESTINATION, RouteReason.CONTROLLED_CROSS_WORKER),
        ),
        (
            ConditionId.C,
            (WorkerId.WORKER_1, WorkerId.WORKER_1),
            (RouteReason.INITIAL_DESTINATION, RouteReason.AFFINITY_PRESERVED),
        ),
    ],
)
def test_schedule_condition_emits_exact_destinations_and_reasons(
    condition_id: ConditionId,
    expected_workers: tuple[WorkerId, WorkerId],
    expected_reasons: tuple[RouteReason, RouteReason],
) -> None:
    route = DeterministicRouteScheduler().schedule_condition(condition_definition(condition_id))

    assert route.schedule.workers == expected_workers
    assert tuple(decision.worker_id for decision in route.decisions) == expected_workers
    assert tuple(decision.reason for decision in route.decisions) == expected_reasons


def test_schedule_experiment_preserves_required_causal_contrasts() -> None:
    plan = DeterministicRouteScheduler().schedule_experiment(definitions())

    route_a = plan.route_for(ConditionId.A)
    route_b = plan.route_for(ConditionId.B)
    route_c = plan.route_for(ConditionId.C)
    assert route_a.schedule == route_b.schedule
    assert route_b.schedule != route_c.schedule


def test_schedule_experiment_canonicalizes_definition_order() -> None:
    condition_a, condition_b, condition_c = definitions()

    plan = DeterministicRouteScheduler().schedule_experiment(
        (condition_c, condition_a, condition_b)
    )

    assert tuple(route.condition_id for route in plan.routes) == (
        ConditionId.A,
        ConditionId.B,
        ConditionId.C,
    )


def test_scheduling_is_deterministic_and_hash_ready() -> None:
    scheduler = DeterministicRouteScheduler()

    first = scheduler.schedule_experiment(definitions())
    second = scheduler.schedule_experiment(definitions())

    assert first == second
    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()


def test_prefix_identity_does_not_change_condition_destination() -> None:
    first = DeterministicRouteScheduler().schedule_condition(
        condition_definition(ConditionId.B, identity=prefix_identity("4"))
    )
    second = DeterministicRouteScheduler().schedule_condition(
        condition_definition(ConditionId.B, identity=prefix_identity("5"))
    )

    assert first == second


def test_decision_for_returns_exact_turn_destination() -> None:
    route = DeterministicRouteScheduler().schedule_condition(condition_definition(ConditionId.C))

    assert route.decision_for(1) is route.decisions[0]
    assert route.decision_for(2) is route.decisions[1]


def test_decision_for_rejects_unsupported_turn_with_machine_readable_code() -> None:
    route = DeterministicRouteScheduler().schedule_condition(condition_definition(ConditionId.C))

    with pytest.raises(RouteSchedulingError) as exc_info:
        route.decision_for(3)

    assert exc_info.value.code is RouteSchedulingErrorCode.INVALID_TURN_INDEX


@pytest.mark.parametrize(
    "invalid_definitions",
    [
        definitions()[:2],
        (definitions()[0], definitions()[0], definitions()[2]),
        (*definitions(), definitions()[0]),
    ],
)
def test_schedule_experiment_rejects_missing_duplicate_or_extra_conditions(
    invalid_definitions: tuple[ConditionDefinition, ...],
) -> None:
    with pytest.raises(RouteSchedulingError) as exc_info:
        DeterministicRouteScheduler().schedule_experiment(invalid_definitions)

    assert exc_info.value.code is RouteSchedulingErrorCode.INVALID_EXPERIMENT_CONSTITUTION


def test_scheduler_revalidates_model_copy_that_bypassed_contract_validation() -> None:
    valid = condition_definition(ConditionId.C)
    tampered = valid.model_copy(
        update={"route_schedule": RouteSchedule(workers=(WorkerId.WORKER_1, WorkerId.WORKER_2))}
    )

    with pytest.raises(RouteSchedulingError) as exc_info:
        DeterministicRouteScheduler().schedule_condition(tampered)

    assert exc_info.value.code is RouteSchedulingErrorCode.INVALID_CONDITION_DEFINITION


def test_route_decision_rejects_worker_substitution() -> None:
    with pytest.raises(ValidationError, match="destination violates"):
        RouteDecision(
            condition_id=ConditionId.C,
            turn_index=2,
            worker_id=WorkerId.WORKER_2,
            reason=RouteReason.AFFINITY_PRESERVED,
        )


def test_route_decision_rejects_false_reason() -> None:
    with pytest.raises(ValidationError, match="reason violates"):
        RouteDecision(
            condition_id=ConditionId.B,
            turn_index=2,
            worker_id=WorkerId.WORKER_2,
            reason=RouteReason.AFFINITY_PRESERVED,
        )


def test_scheduled_route_rejects_decisions_that_do_not_match_schedule() -> None:
    valid = DeterministicRouteScheduler().schedule_condition(condition_definition(ConditionId.C))
    tampered_decision = valid.decisions[1].model_copy(update={"worker_id": WorkerId.WORKER_2})

    with pytest.raises(ValidationError, match="destination violates"):
        ScheduledRoute(
            condition_id=ConditionId.C,
            schedule=valid.schedule,
            decisions=(valid.decisions[0], tampered_decision),
        )


def test_route_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RouteDecision.model_validate(
            {
                "condition_id": "A",
                "turn_index": 1,
                "worker_id": "worker_1",
                "reason": "initial_destination",
                "fallback_worker": "worker_2",
            }
        )


def test_experiment_route_plan_rejects_noncanonical_order() -> None:
    scheduler = DeterministicRouteScheduler()
    route_a = scheduler.schedule_condition(definitions()[0])
    route_b = scheduler.schedule_condition(definitions()[1])
    route_c = scheduler.schedule_condition(definitions()[2])

    with pytest.raises(ValidationError, match="canonical A, B, C order"):
        ExperimentRoutePlan(routes=(route_c, route_a, route_b))
