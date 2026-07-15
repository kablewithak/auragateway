"""Deterministic route scheduling for the controlled local A/B/C experiment."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Literal, Self

from pydantic import ValidationError, model_validator

from auragateway.local_abc.contracts import (
    ConditionDefinition,
    ConditionId,
    LocalABCContract,
    RouteSchedule,
    WorkerId,
)

TurnIndex = Literal[1, 2]

_EXPECTED_WORKERS: dict[ConditionId, tuple[WorkerId, WorkerId]] = {
    ConditionId.A: (WorkerId.WORKER_1, WorkerId.WORKER_2),
    ConditionId.B: (WorkerId.WORKER_1, WorkerId.WORKER_2),
    ConditionId.C: (WorkerId.WORKER_1, WorkerId.WORKER_1),
}


class RouteReason(StrEnum):
    """Why a deterministic destination was selected for one turn."""

    INITIAL_DESTINATION = "initial_destination"
    CONTROLLED_CROSS_WORKER = "controlled_cross_worker"
    AFFINITY_PRESERVED = "affinity_preserved"


class RouteSchedulingErrorCode(StrEnum):
    """Machine-readable failures at the route-scheduler boundary."""

    INVALID_CONDITION_DEFINITION = "INVALID_CONDITION_DEFINITION"
    INVALID_EXPERIMENT_CONSTITUTION = "INVALID_EXPERIMENT_CONSTITUTION"
    INVALID_TURN_INDEX = "INVALID_TURN_INDEX"


class RouteSchedulingError(ValueError):
    """Bounded route-scheduling failure without raw payload disclosure."""

    def __init__(self, code: RouteSchedulingErrorCode, safe_detail: str) -> None:
        self.code = code
        self.safe_detail = safe_detail
        super().__init__(f"{code.value}: {safe_detail}")


def _expected_reason(condition_id: ConditionId, turn_index: TurnIndex) -> RouteReason:
    if turn_index == 1:
        return RouteReason.INITIAL_DESTINATION
    if condition_id in {ConditionId.A, ConditionId.B}:
        return RouteReason.CONTROLLED_CROSS_WORKER
    return RouteReason.AFFINITY_PRESERVED


class RouteDecision(LocalABCContract):
    """One immutable intended destination with an explicit causal reason."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    condition_id: ConditionId
    turn_index: TurnIndex
    worker_id: WorkerId
    reason: RouteReason

    @model_validator(mode="after")
    def validate_constitution(self) -> Self:
        expected_worker = _EXPECTED_WORKERS[self.condition_id][self.turn_index - 1]
        expected_reason = _expected_reason(self.condition_id, self.turn_index)
        if self.worker_id is not expected_worker:
            raise ValueError("route decision destination violates the frozen A/B/C constitution")
        if self.reason is not expected_reason:
            raise ValueError("route decision reason violates the frozen A/B/C constitution")
        return self


class ScheduledRoute(LocalABCContract):
    """Canonical two-turn intended route for one condition."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    condition_id: ConditionId
    schedule: RouteSchedule
    decisions: tuple[RouteDecision, RouteDecision]

    @model_validator(mode="after")
    def validate_route(self) -> Self:
        expected_workers = _EXPECTED_WORKERS[self.condition_id]
        if self.schedule.workers != expected_workers:
            raise ValueError("scheduled route violates the frozen A/B/C constitution")
        if tuple(decision.turn_index for decision in self.decisions) != (1, 2):
            raise ValueError("scheduled route requires ordered turn decisions 1 and 2")
        if any(decision.condition_id is not self.condition_id for decision in self.decisions):
            raise ValueError("route decisions must match the scheduled condition")
        decision_workers = tuple(decision.worker_id for decision in self.decisions)
        if decision_workers != self.schedule.workers:
            raise ValueError("route decisions must exactly match the intended route schedule")
        return self

    def decision_for(self, turn_index: int) -> RouteDecision:
        """Return one intended destination or fail closed for an unsupported turn."""

        if turn_index == 1:
            return self.decisions[0]
        if turn_index == 2:
            return self.decisions[1]
        raise RouteSchedulingError(
            RouteSchedulingErrorCode.INVALID_TURN_INDEX,
            "route decisions exist only for turns 1 and 2",
        )


class ExperimentRoutePlan(LocalABCContract):
    """Canonical A/B/C route plan before any worker invocation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    routes: tuple[ScheduledRoute, ScheduledRoute, ScheduledRoute]

    @model_validator(mode="after")
    def validate_experiment_routes(self) -> Self:
        condition_order = tuple(route.condition_id for route in self.routes)
        if condition_order != (ConditionId.A, ConditionId.B, ConditionId.C):
            raise ValueError("experiment route plan requires canonical A, B, C order")

        route_a, route_b, route_c = self.routes
        if route_a.schedule != route_b.schedule:
            raise ValueError("A and B must use identical intended route schedules")
        if route_b.schedule == route_c.schedule:
            raise ValueError("B and C must differ by worker-affinity schedule")
        return self

    def route_for(self, condition_id: ConditionId) -> ScheduledRoute:
        """Return the required route for one condition."""

        return self.routes[{ConditionId.A: 0, ConditionId.B: 1, ConditionId.C: 2}[condition_id]]


class DeterministicRouteScheduler:
    """Produce intended routes only; worker execution and fallback are separate boundaries."""

    def schedule_condition(self, definition: ConditionDefinition) -> ScheduledRoute:
        """Strictly revalidate and schedule one frozen condition definition."""

        validated = self._revalidate_definition(definition)
        first_worker, second_worker = validated.route_schedule.workers
        decisions = (
            RouteDecision(
                condition_id=validated.condition_id,
                turn_index=1,
                worker_id=first_worker,
                reason=RouteReason.INITIAL_DESTINATION,
            ),
            RouteDecision(
                condition_id=validated.condition_id,
                turn_index=2,
                worker_id=second_worker,
                reason=_expected_reason(validated.condition_id, 2),
            ),
        )
        return ScheduledRoute(
            condition_id=validated.condition_id,
            schedule=validated.route_schedule,
            decisions=decisions,
        )

    def schedule_experiment(
        self,
        definitions: Sequence[ConditionDefinition],
    ) -> ExperimentRoutePlan:
        """Schedule exactly one definition for A, B, and C in canonical order."""

        definitions_tuple = tuple(definitions)
        condition_ids = tuple(definition.condition_id for definition in definitions_tuple)
        if len(definitions_tuple) != 3 or set(condition_ids) != set(ConditionId):
            raise RouteSchedulingError(
                RouteSchedulingErrorCode.INVALID_EXPERIMENT_CONSTITUTION,
                "exactly one condition definition for A, B, and C is required",
            )
        if len(condition_ids) != len(set(condition_ids)):
            raise RouteSchedulingError(
                RouteSchedulingErrorCode.INVALID_EXPERIMENT_CONSTITUTION,
                "duplicate condition definitions are not permitted",
            )

        by_id = {definition.condition_id: definition for definition in definitions_tuple}
        route_a = self.schedule_condition(by_id[ConditionId.A])
        route_b = self.schedule_condition(by_id[ConditionId.B])
        route_c = self.schedule_condition(by_id[ConditionId.C])
        return ExperimentRoutePlan(routes=(route_a, route_b, route_c))

    @staticmethod
    def _revalidate_definition(definition: ConditionDefinition) -> ConditionDefinition:
        try:
            return ConditionDefinition.model_validate(definition.model_dump(mode="python"))
        except ValidationError as exc:
            raise RouteSchedulingError(
                RouteSchedulingErrorCode.INVALID_CONDITION_DEFINITION,
                "condition definition failed strict route-scheduler revalidation",
            ) from exc
