"""Deterministic, non-authorizing core for the final 342-trajectory runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CORE_ID = "auragateway-final-342-non-authorizing-runtime-core-v1"
PLANNED_RUN_LEDGER_PATH = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
EXPECTED_LEDGER_SHA256 = "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
EXPECTED_CONDITION_FINGERPRINTS_SHA256 = (
    "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
)
EXPECTED_PLANNING_MANIFEST_SHA256 = (
    "4bd822375390cf413718553313903679e78b650dfa798955e2f7c61ebd8b8678"
)
EXPECTED_TRAJECTORY_COUNT = 342
EXPECTED_TURN_COUNT = 1368
EXPECTED_MAXIMUM_REQUEST_ATTEMPTS = 2736
EXPECTED_FUNCTIONAL_TRAJECTORIES = 162
EXPECTED_RUNTIME_TRAJECTORIES = 180
MAXIMUM_RETRIES_AFTER_INITIAL_ATTEMPT = 1
RETRY_BACKOFF_SECONDS = 2
WARM_TTL_SECONDS = 300
PROTECTED_REVIEW_ROOT: Literal[".local/auragateway/final-342-protected-review-v1"] = (
    ".local/auragateway/final-342-protected-review-v1"
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class RuntimeCoreError(RuntimeError):
    """Fail-closed deterministic runtime-core error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise RuntimeCoreError("FINAL_342_CORE_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConditionId(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class WorkloadId(StrEnum):
    FUNCTIONAL = "functional"
    RUNTIME_MICROBENCHMARK = "runtime_microbenchmark"


class RouteScheduleId(StrEnum):
    TURN_LOCAL = "turn-local-worker1-worker2-v1"
    AFFINITY = "affinity-worker1-worker1-v1"


class WorkerId(StrEnum):
    WORKER_1 = "worker_1"
    WORKER_2 = "worker_2"


class WarmClassification(StrEnum):
    COLD = "cold"
    WARM_ELIGIBLE = "warm_eligible"
    UNAVAILABLE_OR_AMBIGUOUS = "unavailable_or_ambiguous"


class WarmDecisionCode(StrEnum):
    FIRST_TURN_COLD = "FIRST_TURN_COLD"
    PRIOR_ELIGIBLE_REQUEST_MATCHED = "PRIOR_ELIGIBLE_REQUEST_MATCHED"
    NO_ELIGIBLE_PRIOR_REQUEST = "NO_ELIGIBLE_PRIOR_REQUEST"
    CRITICAL_EVIDENCE_UNAVAILABLE = "CRITICAL_EVIDENCE_UNAVAILABLE"
    TEMPORAL_EVIDENCE_INVALID = "TEMPORAL_EVIDENCE_INVALID"


class AttemptOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    NO_RESPONSE = "no_response"
    DEFINITE_FAILURE = "definite_failure"
    AMBIGUOUS = "ambiguous"


class RetryDecisionCode(StrEnum):
    AUTHORIZED_BOUNDED_RETRY = "AUTHORIZED_BOUNDED_RETRY"
    BLOCKED_NO_RETRYABLE_FAILURE = "BLOCKED_NO_RETRYABLE_FAILURE"
    BLOCKED_AMBIGUOUS_DUPLICATE_RISK = "BLOCKED_AMBIGUOUS_DUPLICATE_RISK"
    BLOCKED_NON_RETRYABLE_FAILURE = "BLOCKED_NON_RETRYABLE_FAILURE"
    BLOCKED_RETRY_BUDGET_EXHAUSTED = "BLOCKED_RETRY_BUDGET_EXHAUSTED"
    BLOCKED_REQUEST_MISMATCH = "BLOCKED_REQUEST_MISMATCH"
    BLOCKED_ROUTE_CHANGE = "BLOCKED_ROUTE_CHANGE"


class CommitDecisionCode(StrEnum):
    COMMIT_AUTHORIZED = "COMMIT_AUTHORIZED"
    BLOCKED_CURRENT_PROMPT_BUDGET = "BLOCKED_CURRENT_PROMPT_BUDGET"
    BLOCKED_FINISH_REASON = "BLOCKED_FINISH_REASON"
    BLOCKED_SCHEMA_ADMISSION = "BLOCKED_SCHEMA_ADMISSION"
    BLOCKED_NEXT_PROMPT_REACHABILITY = "BLOCKED_NEXT_PROMPT_REACHABILITY"


class FailurePhase(StrEnum):
    TRANSPORT = "transport"
    ADMISSION = "admission"
    STATE = "state"
    TELEMETRY = "telemetry"
    TEARDOWN = "teardown"
    CLEANUP = "cleanup"
    EVIDENCE_PACKAGING = "evidence_packaging"
    AUTHORIZATION_TERMINALIZATION = "authorization_terminalization"


_SECONDARY_ONLY_FAILURE_PHASES = {
    FailurePhase.TEARDOWN,
    FailurePhase.CLEANUP,
    FailurePhase.EVIDENCE_PACKAGING,
    FailurePhase.AUTHORIZATION_TERMINALIZATION,
}


class PlannedRun(FrozenModel):
    schema_version: Literal["1.0.0"]
    attempt_number: Literal[1]
    benchmark_manifest_sha256: str
    cache_namespace_id: str = Field(min_length=1)
    comparison_pair_id: str = Field(min_length=1)
    condition_configuration_fingerprint: str
    condition_id: ConditionId
    episode_id: str = Field(min_length=1)
    execution_manifest_sha256: str
    maximum_request_attempts: Literal[8]
    planned_order_index: int = Field(ge=0, lt=EXPECTED_TRAJECTORY_COUNT)
    replication_id: str = Field(min_length=1)
    route_schedule_id: RouteScheduleId
    run_id: str = Field(min_length=1)
    terminal_classification: Literal["not_started"]
    trace_id: str = Field(min_length=1)
    turn_count: Literal[4]
    workload: WorkloadId

    @field_validator(
        "benchmark_manifest_sha256",
        "condition_configuration_fingerprint",
        "execution_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("planned-run digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_planning_manifest(self) -> Self:
        if self.execution_manifest_sha256 != EXPECTED_PLANNING_MANIFEST_SHA256:
            raise ValueError("planned run execution-manifest planning identity drifted")
        return self


class PlannedRunLedger(FrozenModel):
    schema_version: Literal["1.0.0"]
    plan_id: Literal["benchmark-plan-auragateway-local-abc-v3"]
    source_main_merge_commit: str = Field(min_length=40, max_length=40)
    condition_fingerprints_sha256: str
    execution_manifest_planning_identity_sha256: str
    functional_run_order_schedule_id: Literal["functional-counterbalance-v1"]
    runtime_run_order_schedule_id: Literal["runtime-counterbalance-v1"]
    functional_trajectory_count: Literal[162]
    runtime_trajectory_count: Literal[180]
    total_trajectory_count: Literal[342]
    total_turn_count: Literal[1368]
    maximum_request_attempt_count: Literal[2736]
    every_attempt_retained: Literal[True]
    hidden_retry_permitted: Literal[False]
    replacement_case_permitted: Literal[False]
    reuse_preflight_v2_hash_bindings: Literal[False]
    execution_enabled: Literal[False]
    runs: tuple[PlannedRun, ...]

    @field_validator(
        "condition_fingerprints_sha256",
        "execution_manifest_planning_identity_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("ledger digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_frozen_plan(self) -> Self:
        if self.condition_fingerprints_sha256 != EXPECTED_CONDITION_FINGERPRINTS_SHA256:
            raise ValueError("condition fingerprint identity drifted")
        if self.execution_manifest_planning_identity_sha256 != EXPECTED_PLANNING_MANIFEST_SHA256:
            raise ValueError("ledger planning-manifest identity drifted")
        if len(self.runs) != EXPECTED_TRAJECTORY_COUNT:
            raise ValueError("planned run ledger must contain exactly 342 runs")

        functional_count = 0
        runtime_count = 0
        run_ids: set[str] = set()
        trace_ids: set[str] = set()

        for expected_index, run in enumerate(self.runs):
            if run.planned_order_index != expected_index:
                raise ValueError("planned run order must remain exact")
            if run.run_id in run_ids or run.trace_id in trace_ids:
                raise ValueError("planned run and trace identities must be unique")
            run_ids.add(run.run_id)
            trace_ids.add(run.trace_id)
            if run.workload is WorkloadId.FUNCTIONAL:
                functional_count += 1
            if run.workload is WorkloadId.RUNTIME_MICROBENCHMARK:
                runtime_count += 1

        if functional_count != EXPECTED_FUNCTIONAL_TRAJECTORIES:
            raise ValueError("functional trajectory count drifted")
        if runtime_count != EXPECTED_RUNTIME_TRAJECTORIES:
            raise ValueError("runtime trajectory count drifted")
        return self


class RuntimeTurnPlan(FrozenModel):
    run_id: str
    trace_id: str
    comparison_pair_id: str
    workload: WorkloadId
    condition_id: ConditionId
    route_schedule_id: RouteScheduleId
    turn_index: int = Field(ge=1, le=4)
    worker_id: WorkerId
    session_id_hash: str
    cache_namespace_sha256: str

    @field_validator("session_id_hash", "cache_namespace_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime turn identities must be lowercase SHA-256")
        return value


class RuntimeTraceIdentity(FrozenModel):
    run_id: str
    trace_id: str
    planning_execution_manifest_sha256: str = EXPECTED_PLANNING_MANIFEST_SHA256
    final_execution_manifest_sha256: str

    @field_validator(
        "planning_execution_manifest_sha256",
        "final_execution_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("trace manifest identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest_bridge(self) -> Self:
        if self.planning_execution_manifest_sha256 != EXPECTED_PLANNING_MANIFEST_SHA256:
            raise ValueError("planning manifest identity drifted")
        if self.final_execution_manifest_sha256 == EXPECTED_PLANNING_MANIFEST_SHA256:
            raise ValueError("final execution manifest cannot reuse the planning identity")
        return self


class CacheResidencyIdentity(FrozenModel):
    worker_id: WorkerId
    worker_generation: int = Field(ge=1)
    runtime_model_fingerprint: str

    @field_validator("runtime_model_fingerprint")
    @classmethod
    def validate_fingerprint(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime model fingerprint must be lowercase SHA-256")
        return value


class WarmTurnEvidence(FrozenModel):
    turn_index: int = Field(ge=1, le=4)
    session_id_hash: str
    cache_namespace_sha256: str
    static_prefix_fingerprint: str | None
    residency_identity: CacheResidencyIdentity | None
    affinity_epoch: int = Field(ge=0)
    request_started_monotonic_ns: int = Field(ge=0)
    request_completed_monotonic_ns: int | None = Field(default=None, ge=0)
    request_completed: bool
    provider_failure: bool = False
    session_reset: bool = False
    benchmark_transition: bool = False

    @field_validator(
        "session_id_hash",
        "cache_namespace_sha256",
        "static_prefix_fingerprint",
    )
    @classmethod
    def validate_optional_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("warm evidence fingerprints must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_timing(self) -> Self:
        if self.request_completed:
            if self.request_completed_monotonic_ns is None:
                raise ValueError("completed request requires completion monotonic time")
            if self.request_completed_monotonic_ns < self.request_started_monotonic_ns:
                raise ValueError("request completion cannot precede request start")
        if not self.request_completed and self.request_completed_monotonic_ns is not None:
            raise ValueError("incomplete request cannot contain completion monotonic time")
        return self

    @property
    def eligible_as_prior_request(self) -> bool:
        return self.request_completed and not any(
            (
                self.provider_failure,
                self.session_reset,
                self.benchmark_transition,
            )
        )


class WarmEligibilityDecision(FrozenModel):
    classification: WarmClassification
    decision_code: WarmDecisionCode
    matched_prior_turn_index: int | None = Field(default=None, ge=1, le=4)

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if (
            self.classification is WarmClassification.WARM_ELIGIBLE
            and self.matched_prior_turn_index is None
        ):
            raise ValueError("warm-eligible decision requires a matched prior turn")
        if (
            self.classification is not WarmClassification.WARM_ELIGIBLE
            and self.matched_prior_turn_index is not None
        ):
            raise ValueError("non-warm decisions cannot expose a matched prior turn")
        return self


class RetryAttemptEvidence(FrozenModel):
    attempt_index: int = Field(ge=1, le=2)
    logical_request_fingerprint: str
    route_identity: CacheResidencyIdentity
    outcome: AttemptOutcome
    retryable: bool = False

    @field_validator("logical_request_fingerprint")
    @classmethod
    def validate_fingerprint(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("logical request fingerprint must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.outcome is AttemptOutcome.SUCCEEDED and self.retryable:
            raise ValueError("successful attempt cannot be retryable")
        if self.outcome is AttemptOutcome.AMBIGUOUS and self.retryable:
            raise ValueError("ambiguous attempt cannot be retryable")
        return self


class RetryDecision(FrozenModel):
    authorized: bool
    decision_code: RetryDecisionCode
    authorized_attempt_index: int | None = Field(default=None, ge=2, le=2)
    retry_backoff_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if self.authorized and (
            self.decision_code is not RetryDecisionCode.AUTHORIZED_BOUNDED_RETRY
            or self.authorized_attempt_index != 2
            or self.retry_backoff_seconds != RETRY_BACKOFF_SECONDS
        ):
            raise ValueError("authorized retry decision is inconsistent")
        if not self.authorized and (
            self.authorized_attempt_index is not None or self.retry_backoff_seconds is not None
        ):
            raise ValueError("blocked retry decision cannot authorize work")
        return self


class TurnAdmissionEvidence(FrozenModel):
    turn_index: int = Field(ge=1, le=4)
    current_prompt_budget_valid: bool
    finish_reason: str | None
    schema_admitted: bool
    has_next_turn: bool
    next_prompt_reachable: bool | None

    @model_validator(mode="after")
    def validate_reachability_shape(self) -> Self:
        if self.has_next_turn and self.next_prompt_reachable is None:
            raise ValueError("non-terminal turn requires next-prompt reachability evidence")
        if not self.has_next_turn and self.next_prompt_reachable is not None:
            raise ValueError("terminal turn must not contain next-prompt reachability evidence")
        return self


class TurnCommitDecision(FrozenModel):
    decision_code: CommitDecisionCode
    history_mutation_permitted: bool

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        expected = self.decision_code is CommitDecisionCode.COMMIT_AUTHORIZED
        if self.history_mutation_permitted != expected:
            raise ValueError("history mutation permission must match commit decision")
        return self


class RequestCounters(FrozenModel):
    scheduled_request_count: int = Field(ge=0, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)
    attempted_request_count: int = Field(ge=0, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)
    http_completed_request_count: int = Field(
        ge=0,
        le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
    )
    admitted_request_count: int = Field(ge=0, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)
    committed_request_count: int = Field(ge=0, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)

    @model_validator(mode="after")
    def validate_monotonic_counters(self) -> Self:
        if not (
            self.scheduled_request_count
            >= self.attempted_request_count
            >= self.http_completed_request_count
            >= self.admitted_request_count
            >= self.committed_request_count
            >= 0
        ):
            raise ValueError("request counters violate the monotonic accountability invariant")
        return self


class ProtectedReviewPublicReceipt(FrozenModel):
    protected_export_root: Literal[".local/auragateway/final-342-protected-review-v1"] = (
        PROTECTED_REVIEW_ROOT
    )
    export_sha256: str
    item_count: int = Field(ge=1)
    opaque_review_ids_only: Literal[True] = True
    raw_prompts_in_public_evidence: Literal[False] = False
    raw_outputs_in_public_evidence: Literal[False] = False
    raw_provider_payloads_in_public_evidence: Literal[False] = False
    public_binding_is_metadata_or_digest_only: Literal[True] = True
    retention_and_deletion_rule_bound: Literal[True]

    @field_validator("export_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("protected export digest must be lowercase SHA-256")
        return value


class FailureRecord(FrozenModel):
    phase: FailurePhase
    error_code: str = Field(min_length=3, max_length=120)
    safe_message: str = Field(min_length=1, max_length=240)


class FailureState(FrozenModel):
    primary_failure: FailureRecord | None = None
    secondary_failures: tuple[FailureRecord, ...] = ()

    @model_validator(mode="after")
    def validate_primary_failure(self) -> Self:
        if (
            self.primary_failure is not None
            and self.primary_failure.phase in _SECONDARY_ONLY_FAILURE_PHASES
        ):
            raise ValueError("secondary-only failure phase cannot become primary")
        return self


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def session_id_hash(run_id: str) -> str:
    """Derive the frozen privacy-safe final-run session identity."""
    return _sha256_text(f"auragateway-final-342-session-v1|{run_id}")


def protected_review_id(run_id: str) -> str:
    """Derive an opaque review ID without exposing condition or route metadata."""
    return _sha256_text(f"auragateway-final-342-protected-review-v1|{run_id}")


def realize_route(route_schedule_id: RouteScheduleId) -> tuple[WorkerId, ...]:
    """Realize the exact four-turn worker route from the ledger schedule ID."""
    if route_schedule_id is RouteScheduleId.TURN_LOCAL:
        return (
            WorkerId.WORKER_1,
            WorkerId.WORKER_2,
            WorkerId.WORKER_1,
            WorkerId.WORKER_2,
        )
    if route_schedule_id is RouteScheduleId.AFFINITY:
        return (
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
        )
    raise RuntimeCoreError(
        "FINAL_342_ROUTE_SCHEDULE_UNSUPPORTED",
        "planned run route schedule is unsupported",
    )


def realize_run(run: PlannedRun) -> tuple[RuntimeTurnPlan, ...]:
    """Convert one frozen planned run into four deterministic turn plans."""
    route = realize_route(run.route_schedule_id)
    session_hash = session_id_hash(run.run_id)
    namespace_hash = _sha256_text(run.cache_namespace_id)
    return tuple(
        RuntimeTurnPlan(
            run_id=run.run_id,
            trace_id=run.trace_id,
            comparison_pair_id=run.comparison_pair_id,
            workload=run.workload,
            condition_id=run.condition_id,
            route_schedule_id=run.route_schedule_id,
            turn_index=index,
            worker_id=worker_id,
            session_id_hash=session_hash,
            cache_namespace_sha256=namespace_hash,
        )
        for index, worker_id in enumerate(route, start=1)
    )


def classify_warm_eligibility(
    current: WarmTurnEvidence,
    prior_turns: Sequence[WarmTurnEvidence],
) -> WarmEligibilityDecision:
    """Classify benchmark warm eligibility without treating it as a cache-hit claim."""
    if current.turn_index == 1:
        return WarmEligibilityDecision(
            classification=WarmClassification.COLD,
            decision_code=WarmDecisionCode.FIRST_TURN_COLD,
        )
    if current.static_prefix_fingerprint is None or current.residency_identity is None:
        return WarmEligibilityDecision(
            classification=WarmClassification.UNAVAILABLE_OR_AMBIGUOUS,
            decision_code=WarmDecisionCode.CRITICAL_EVIDENCE_UNAVAILABLE,
        )

    ambiguous_candidate = False
    for prior in sorted(prior_turns, key=lambda item: item.turn_index, reverse=True):
        if prior.turn_index >= current.turn_index:
            continue
        if prior.session_id_hash != current.session_id_hash:
            continue
        if prior.cache_namespace_sha256 != current.cache_namespace_sha256:
            continue
        if prior.affinity_epoch != current.affinity_epoch:
            continue
        if not prior.eligible_as_prior_request:
            continue
        if (
            prior.static_prefix_fingerprint is None
            or prior.residency_identity is None
            or prior.request_completed_monotonic_ns is None
        ):
            ambiguous_candidate = True
            continue
        if prior.static_prefix_fingerprint != current.static_prefix_fingerprint:
            continue
        if prior.residency_identity != current.residency_identity:
            continue

        elapsed_ns = current.request_started_monotonic_ns - prior.request_completed_monotonic_ns
        if elapsed_ns < 0:
            return WarmEligibilityDecision(
                classification=WarmClassification.UNAVAILABLE_OR_AMBIGUOUS,
                decision_code=WarmDecisionCode.TEMPORAL_EVIDENCE_INVALID,
            )
        if elapsed_ns <= WARM_TTL_SECONDS * 1_000_000_000:
            return WarmEligibilityDecision(
                classification=WarmClassification.WARM_ELIGIBLE,
                decision_code=WarmDecisionCode.PRIOR_ELIGIBLE_REQUEST_MATCHED,
                matched_prior_turn_index=prior.turn_index,
            )

    if ambiguous_candidate:
        return WarmEligibilityDecision(
            classification=WarmClassification.UNAVAILABLE_OR_AMBIGUOUS,
            decision_code=WarmDecisionCode.CRITICAL_EVIDENCE_UNAVAILABLE,
        )
    return WarmEligibilityDecision(
        classification=WarmClassification.COLD,
        decision_code=WarmDecisionCode.NO_ELIGIBLE_PRIOR_REQUEST,
    )


def authorize_retry(
    attempts: Sequence[RetryAttemptEvidence],
    *,
    proposed_logical_request_fingerprint: str,
    proposed_route_identity: CacheResidencyIdentity,
) -> RetryDecision:
    """Authorize at most one exact-route retry after typed non-ambiguous failure."""
    if not attempts:
        raise RuntimeCoreError(
            "FINAL_342_RETRY_HISTORY_EMPTY",
            "retry authorization requires retained attempt evidence",
        )

    first = attempts[0]
    for expected_index, attempt in enumerate(attempts, start=1):
        if attempt.attempt_index != expected_index:
            raise RuntimeCoreError(
                "FINAL_342_RETRY_HISTORY_INVALID",
                "retry attempt indexes must be contiguous",
            )
        if attempt.logical_request_fingerprint != first.logical_request_fingerprint:
            raise RuntimeCoreError(
                "FINAL_342_RETRY_HISTORY_INVALID",
                "retry history must retain one logical request fingerprint",
            )
        if attempt.route_identity != first.route_identity:
            raise RuntimeCoreError(
                "FINAL_342_RETRY_HISTORY_INVALID",
                "retry history must retain one cache-residency route",
            )

    last = attempts[-1]
    if last.outcome is AttemptOutcome.AMBIGUOUS:
        code = RetryDecisionCode.BLOCKED_AMBIGUOUS_DUPLICATE_RISK
    elif last.outcome not in {
        AttemptOutcome.NO_RESPONSE,
        AttemptOutcome.DEFINITE_FAILURE,
    }:
        code = RetryDecisionCode.BLOCKED_NO_RETRYABLE_FAILURE
    elif not last.retryable:
        code = RetryDecisionCode.BLOCKED_NON_RETRYABLE_FAILURE
    elif len(attempts) - 1 >= MAXIMUM_RETRIES_AFTER_INITIAL_ATTEMPT:
        code = RetryDecisionCode.BLOCKED_RETRY_BUDGET_EXHAUSTED
    elif proposed_logical_request_fingerprint != last.logical_request_fingerprint:
        code = RetryDecisionCode.BLOCKED_REQUEST_MISMATCH
    elif proposed_route_identity != last.route_identity:
        code = RetryDecisionCode.BLOCKED_ROUTE_CHANGE
    else:
        return RetryDecision(
            authorized=True,
            decision_code=RetryDecisionCode.AUTHORIZED_BOUNDED_RETRY,
            authorized_attempt_index=2,
            retry_backoff_seconds=RETRY_BACKOFF_SECONDS,
        )

    return RetryDecision(
        authorized=False,
        decision_code=code,
    )


def evaluate_turn_commit(evidence: TurnAdmissionEvidence) -> TurnCommitDecision:
    """Authorize history mutation only after all frozen admission gates pass."""
    if not evidence.current_prompt_budget_valid:
        code = CommitDecisionCode.BLOCKED_CURRENT_PROMPT_BUDGET
    elif evidence.finish_reason != "stop":
        code = CommitDecisionCode.BLOCKED_FINISH_REASON
    elif not evidence.schema_admitted:
        code = CommitDecisionCode.BLOCKED_SCHEMA_ADMISSION
    elif evidence.has_next_turn and evidence.next_prompt_reachable is not True:
        code = CommitDecisionCode.BLOCKED_NEXT_PROMPT_REACHABILITY
    else:
        return TurnCommitDecision(
            decision_code=CommitDecisionCode.COMMIT_AUTHORIZED,
            history_mutation_permitted=True,
        )

    return TurnCommitDecision(
        decision_code=code,
        history_mutation_permitted=False,
    )


def record_failure(state: FailureState, failure: FailureRecord) -> FailureState:
    """Preserve the first causal failure and retain later failures separately."""
    if state.primary_failure is None and failure.phase not in _SECONDARY_ONLY_FAILURE_PHASES:
        return FailureState(
            primary_failure=failure,
            secondary_failures=state.secondary_failures,
        )
    return FailureState(
        primary_failure=state.primary_failure,
        secondary_failures=(*state.secondary_failures, failure),
    )


def load_runtime_plan(repo_root: Path) -> PlannedRunLedger:
    """Load and validate the exact frozen 342-run planning subject."""
    path = repo_root.resolve() / PLANNED_RUN_LEDGER_PATH
    if not path.is_file() or path.is_symlink():
        raise RuntimeCoreError(
            "FINAL_342_LEDGER_MISSING",
            "frozen planned-run ledger is missing or symlinked",
        )
    if _sha256_path(path) != EXPECTED_LEDGER_SHA256:
        raise RuntimeCoreError(
            "FINAL_342_LEDGER_IDENTITY_DRIFT",
            "frozen planned-run ledger identity drifted",
        )
    try:
        return PlannedRunLedger.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise RuntimeCoreError(
            "FINAL_342_LEDGER_VALIDATION_FAILED",
            "frozen planned-run ledger failed runtime-core validation",
        ) from error


def validate(repo_root: Path) -> dict[str, object]:
    """Validate the non-authorizing core against the exact frozen plan."""
    ledger = load_runtime_plan(repo_root)
    turn_count = 0
    review_ids: set[str] = set()
    for run in ledger.runs:
        turns = realize_run(run)
        if len(turns) != 4:
            raise RuntimeCoreError(
                "FINAL_342_ROUTE_REALIZATION_INVALID",
                "planned run did not realize exactly four turns",
            )
        turn_count += len(turns)
        review_id = protected_review_id(run.run_id)
        if review_id in review_ids:
            raise RuntimeCoreError(
                "FINAL_342_PROTECTED_REVIEW_ID_COLLISION",
                "protected review identity collision detected",
            )
        review_ids.add(review_id)

    if turn_count != EXPECTED_TURN_COUNT:
        raise RuntimeCoreError(
            "FINAL_342_REALIZED_TURN_COUNT_DRIFT",
            "realized final-run turn count drifted",
        )

    return {
        "status": "FINAL_342_NON_AUTHORIZING_RUNTIME_CORE_V1_VALID",
        "core_id": CORE_ID,
        "planned_trajectories": len(ledger.runs),
        "realized_turns": turn_count,
        "maximum_request_attempts": ledger.maximum_request_attempt_count,
        "functional_trajectories": ledger.functional_trajectory_count,
        "runtime_trajectories": ledger.runtime_trajectory_count,
        "protected_review_id_count": len(review_ids),
        "warm_ttl_seconds": WARM_TTL_SECONDS,
        "maximum_retries_after_initial_attempt": (MAXIMUM_RETRIES_AFTER_INITIAL_ATTEMPT),
        "retry_backoff_seconds": RETRY_BACKOFF_SECONDS,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "execution_manifest_frozen": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": "REHEARSE_FINAL_342_TRANSACTION_WRAPPER_V1",
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = cast(str, args.command)
    repo_root = Path(cast(str, args.repo_root))
    if command != "validate":
        raise RuntimeCoreError(
            "FINAL_342_CORE_ARGUMENT_ERROR",
            "unsupported runtime-core command",
        )

    try:
        result = validate(repo_root)
    except (RuntimeCoreError, OSError) as error:
        if isinstance(error, RuntimeCoreError):
            code = error.error_code
            message = error.safe_message
        else:
            code = "FINAL_342_CORE_VALIDATION_FAILED"
            message = str(error)
        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
