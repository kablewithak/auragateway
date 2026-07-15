"""Fail-closed trajectory eligibility for the controlled local A/B/C experiment."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import ValidationError

from auragateway.local_abc.contracts import (
    CacheObservationState,
    ConditionId,
    RunEligibility,
    RunTerminalClassification,
    TelemetryObservation,
    TrajectoryRecord,
    TrajectoryTerminalState,
)
from auragateway.local_abc.errors import LocalABCFailureCode

_OBSERVED_CACHE_STATES = {
    CacheObservationState.ZERO,
    CacheObservationState.POSITIVE,
}
_AFFINITY_CONDITIONS = {ConditionId.B, ConditionId.C}


class EligibilityEvaluationErrorCode(StrEnum):
    """Machine-readable evaluator boundary failures."""

    INVALID_TRAJECTORY = "INVALID_TRAJECTORY"


class EligibilityEvaluationError(ValueError):
    """Bounded evaluator failure without unsafe trajectory disclosure."""

    def __init__(self, code: EligibilityEvaluationErrorCode, safe_detail: str) -> None:
        self.code = code
        self.safe_detail = safe_detail
        super().__init__(f"{code.value}: {safe_detail}")


class EligibilityEvaluator:
    """Convert retained trajectories into explicit run and comparison decisions."""

    def evaluate(self, trajectory: TrajectoryRecord) -> RunEligibility:
        """Evaluate one trajectory without dropping failures or repairing evidence."""

        validated = self._revalidate_trajectory(trajectory)
        telemetry_sufficient = self._telemetry_sufficient(validated.telemetry)
        route_realized = (
            len(validated.realized_route) == 2
            and validated.realized_route == validated.intended_route.workers
            and not validated.fallback_used
        )
        failure_codes = self._effective_failure_codes(
            validated,
            telemetry_sufficient=telemetry_sufficient,
            route_realized=route_realized,
        )
        comparison_eligible = (
            validated.terminal_state is TrajectoryTerminalState.COMPLETED
            and validated.task_completed
            and telemetry_sufficient
            and route_realized
            and not validated.fallback_used
            and not failure_codes
        )
        classification = self._classification(
            validated,
            comparison_eligible=comparison_eligible,
        )
        affinity_eligible = comparison_eligible and validated.condition_id in _AFFINITY_CONDITIONS

        return RunEligibility(
            trajectory_id=validated.trajectory_id,
            condition_id=validated.condition_id,
            terminal_classification=classification,
            task_completed=validated.task_completed,
            comparison_eligible=comparison_eligible,
            affinity_comparison_eligible=affinity_eligible,
            telemetry_sufficient=telemetry_sufficient,
            route_realized=route_realized,
            fallback_used=validated.fallback_used,
            failure_codes=failure_codes,
        )

    def evaluate_many(
        self,
        trajectories: Sequence[TrajectoryRecord],
    ) -> tuple[RunEligibility, ...]:
        """Evaluate every retained attempt in input order without filtering."""

        return tuple(self.evaluate(trajectory) for trajectory in trajectories)

    @staticmethod
    def _revalidate_trajectory(trajectory: TrajectoryRecord) -> TrajectoryRecord:
        try:
            return TrajectoryRecord.model_validate(trajectory.model_dump(mode="python"))
        except ValidationError as exc:
            raise EligibilityEvaluationError(
                EligibilityEvaluationErrorCode.INVALID_TRAJECTORY,
                "trajectory failed strict eligibility-boundary revalidation",
            ) from exc

    @staticmethod
    def _telemetry_sufficient(
        telemetry: tuple[TelemetryObservation, ...],
    ) -> bool:
        if len(telemetry) != 2:
            return False

        for observation in telemetry:
            cache = observation.cache
            cached_tokens = cache.observed_cached_prefix_tokens
            newly_computed = observation.newly_computed_prefill_tokens
            if cache.state not in _OBSERVED_CACHE_STATES:
                return False
            if cache.reason_code is not None or cached_tokens is None or newly_computed is None:
                return False
            if cached_tokens + newly_computed != observation.eligible_shared_prefix_tokens:
                return False
            if observation.prefill_duration_ms is None:
                return False
            if observation.time_to_first_token_ms is None:
                return False
            if observation.end_to_end_latency_ms is None:
                return False
        return True

    @staticmethod
    def _effective_failure_codes(
        trajectory: TrajectoryRecord,
        *,
        telemetry_sufficient: bool,
        route_realized: bool,
    ) -> tuple[LocalABCFailureCode, ...]:
        failure_codes = set(trajectory.failure_codes)

        for observation in trajectory.telemetry:
            if observation.cache.reason_code is not None:
                failure_codes.add(observation.cache.reason_code)

        if trajectory.terminal_state is TrajectoryTerminalState.INTERRUPTED:
            failure_codes.add(LocalABCFailureCode.SESSION_INTERRUPTED)
        if not route_realized and trajectory.fallback_used:
            failure_codes.add(LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH)
        observed_cache_only = all(
            observation.cache.state in _OBSERVED_CACHE_STATES
            for observation in trajectory.telemetry
        )
        if trajectory.task_completed and not telemetry_sufficient and observed_cache_only:
            failure_codes.add(LocalABCFailureCode.TELEMETRY_INVALID)
        if trajectory.terminal_state is TrajectoryTerminalState.FAILED and not failure_codes:
            failure_codes.add(LocalABCFailureCode.RUN_INELIGIBLE)
        if not failure_codes and trajectory.terminal_state is not TrajectoryTerminalState.COMPLETED:
            failure_codes.add(LocalABCFailureCode.RUN_INELIGIBLE)

        return tuple(sorted(failure_codes, key=lambda code: code.value))

    @staticmethod
    def _classification(
        trajectory: TrajectoryRecord,
        *,
        comparison_eligible: bool,
    ) -> RunTerminalClassification:
        if trajectory.terminal_state is TrajectoryTerminalState.FAILED:
            return RunTerminalClassification.FAILED_RETAINED
        if trajectory.terminal_state is TrajectoryTerminalState.INTERRUPTED:
            return RunTerminalClassification.INTERRUPTED_RETAINED
        if comparison_eligible:
            return RunTerminalClassification.COMPLETED_ELIGIBLE
        if trajectory.fallback_used:
            return RunTerminalClassification.TASK_COMPLETED_BUT_COMPARISON_INELIGIBLE
        return RunTerminalClassification.COMPLETED_INELIGIBLE
