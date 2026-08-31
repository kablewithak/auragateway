"""Deterministic post-run analysis engine for the final-342 Local ABC experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import subprocess
import sys
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc import final_342_execution_producer_v1 as producer
from auragateway.local_abc import final_342_measured_quality_reducers_v1 as quality
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

RECORD_PATH = Path("benchmarks/local_abc/auragateway_final_342_analysis_engine_v1.json")
FREEZE_PATH = Path(
    "data/evals/benchmark/freeze-v2/measured_abc_repetition_statistical_freeze_v1.json"
)
PLANNED_LEDGER_PATH = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
EXPECTED_BASE_MAIN = "c5bac2c3d2903418c60ad59a190c0dc7e5adfdd3"
ENGINE_VERSION: Literal["final-342-analysis-engine-v1"] = "final-342-analysis-engine-v1"

EXPECTED_SOURCE_BLOBS: dict[str, str] = {
    "src/auragateway/local_abc/final_342_execution_producer_v1.py": (
        "9bedae7c7815e80d7c03ccc37b1e5261310056cf"
    ),
    "src/auragateway/local_abc/final_342_non_authorizing_runtime_core_v1.py": (
        "7edeb7cb3f6c2213868d23863c33a9a94669468c"
    ),
    "src/auragateway/local_abc/final_342_measured_quality_reducers_v1.py": (
        "e84f47010f16f0340d38de71a22e1cc7c03b6252"
    ),
    "benchmarks/local_abc/auragateway_final_342_measured_quality_reducers_v1.json": (
        "dd2a9be5dca8eccbf1c70c9d6645866736dff57e"
    ),
    "src/auragateway/local_abc/final_342_analysis_contracts_v1.py": (
        "e5ff63b8a1f148dee42bbf1e39504b26657a6d75"
    ),
    "benchmarks/local_abc/auragateway_final_342_analysis_contracts_v1.json": (
        "0e7f654a5e8562f93ada988bba51f4e3ed5b5b1f"
    ),
    "src/auragateway/local_abc/measured_abc_repetition_statistical_freeze_v1.py": (
        "404aac33c8ca7d35d3997f348ea88b975b3b7d12"
    ),
    FREEZE_PATH.as_posix(): "9999eb0350a3d3e01a9f5f3451f54d7deaa35aef",
    PLANNED_LEDGER_PATH.as_posix(): "553b23e24629bdca81d9fb9fdcbd90cc2081caf0",
}

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260712
CONFIDENCE_LEVEL = 0.95
TASK_SUCCESS_MARGIN = Decimal("0.05")
STRUCTURED_VALIDITY_MINIMUM = Decimal("0.95")
RUN_COUNT = 342
FUNCTIONAL_RUN_COUNT = 162
RUNTIME_RUN_COUNT = 180
FUNCTIONAL_PAIR_COUNT = 54
RUNTIME_PAIR_COUNT = 60
RUNS_PER_FUNCTIONAL_CONDITION = 54
RUNS_PER_RUNTIME_CONDITION = 60


class Final342AnalysisError(RuntimeError):
    """Fail-closed deterministic analysis error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise Final342AnalysisError("FINAL_342_ANALYSIS_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceBinding(FrozenModel):
    role: str = Field(min_length=3)
    path: str = Field(min_length=3)
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class AnalysisEvidenceState(StrEnum):
    COMPLETE = "COMPLETE"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"


class QualityGateState(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class CheckState(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class RuntimeEndpointState(StrEnum):
    AVAILABLE = "AVAILABLE"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    INELIGIBLE = "INELIGIBLE"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"


class RuntimeContrastState(StrEnum):
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class ClaimDecision(StrEnum):
    SUPPORTED = "SUPPORTED"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    BLOCKED = "BLOCKED"


class ClaimFamily(StrEnum):
    CONTEXT_CONSTRUCTION_POLICY = "context_construction_policy"
    ROUTE_POLICY = "route_policy"
    TOTAL_SYSTEM = "total_system"


class AnalysisErrorCode(StrEnum):
    BUNDLE_VERIFICATION_FAILED = "BUNDLE_VERIFICATION_FAILED"
    PLANNED_LEDGER_INVALID = "PLANNED_LEDGER_INVALID"
    PLAN_BINDING_INVALID = "PLAN_BINDING_INVALID"
    TRACE_BINDING_INVALID = "TRACE_BINDING_INVALID"
    FINAL_EXECUTION_MANIFEST_MISMATCH = "FINAL_EXECUTION_MANIFEST_MISMATCH"
    TERMINAL_LEDGER_INCOMPLETE = "TERMINAL_LEDGER_INCOMPLETE"
    TERMINAL_LEDGER_INVALID = "TERMINAL_LEDGER_INVALID"
    FUNCTIONAL_QUALITY_LEDGER_INCOMPLETE = "FUNCTIONAL_QUALITY_LEDGER_INCOMPLETE"
    FUNCTIONAL_QUALITY_LEDGER_INVALID = "FUNCTIONAL_QUALITY_LEDGER_INVALID"
    FUNCTIONAL_QUALITY_EVIDENCE_INCOMPLETE = "FUNCTIONAL_QUALITY_EVIDENCE_INCOMPLETE"
    RUNTIME_MEASUREMENT_INVALID = "RUNTIME_MEASUREMENT_INVALID"
    RUNTIME_PRIMARY_TELEMETRY_INCOMPLETE = "RUNTIME_PRIMARY_TELEMETRY_INCOMPLETE"


class QualityCheckName(StrEnum):
    RETRIEVAL_CONFIGURATION_MATCH = "RETRIEVAL_CONFIGURATION_MATCH"
    EPISODE_MANIFEST_MATCH = "EPISODE_MANIFEST_MATCH"
    STRUCTURED_OUTPUT_VALIDITY = "STRUCTURED_OUTPUT_VALIDITY"
    CITATION_SUPPORT_NON_REGRESSION = "CITATION_SUPPORT_NON_REGRESSION"
    UNSUPPORTED_ANSWER_NON_REGRESSION = "UNSUPPORTED_ANSWER_NON_REGRESSION"
    TASK_SUCCESS_NON_INFERIORITY = "TASK_SUCCESS_NON_INFERIORITY"
    UNSAFE_BEHAVIOR_NON_REGRESSION = "UNSAFE_BEHAVIOR_NON_REGRESSION"


class ConditionIdentity(FrozenModel):
    condition_id: core.ConditionId
    retrieval_configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BundleVerification(FrozenModel):
    receipt: producer.EvidenceBundleReceipt
    schema_and_hash_verified: bool


class Final342AnalysisInput(FrozenModel):
    final_execution_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bundle_verification: BundleVerification
    condition_identities: tuple[ConditionIdentity, ...] = Field(min_length=3, max_length=3)
    planned_runs: tuple[core.PlannedRun, ...]
    plan_bindings: tuple[producer.PlanBinding, ...]
    trace_bindings: tuple[core.RuntimeTraceIdentity, ...]
    trajectory_terminals: tuple[producer.TrajectoryTerminalRecord, ...]
    measurements: tuple[producer.TurnMeasurementRecord, ...]
    measured_quality_results: tuple[quality.MeasuredQualityRunResult, ...]

    @model_validator(mode="after")
    def validate_condition_identities(self) -> Self:
        condition_ids = tuple(item.condition_id for item in self.condition_identities)
        if set(condition_ids) != set(core.ConditionId):
            raise ValueError("condition identities must contain A, B, and C")
        if len(condition_ids) != len(set(condition_ids)):
            raise ValueError("condition identities must be unique")
        return self


class RunAccountability(FrozenModel):
    planned_run_count: int = Field(ge=0)
    plan_binding_count: int = Field(ge=0)
    trace_binding_count: int = Field(ge=0)
    terminal_record_count: int = Field(ge=0)
    completed_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    missing_terminal_count: int = Field(ge=0)
    functional_quality_result_count: int = Field(ge=0)
    accountability_complete: bool


class ConditionQualityAggregate(FrozenModel):
    condition_id: core.ConditionId
    sample_count: int = Field(ge=0)
    task_success_count: int = Field(ge=0)
    structured_output_valid_count: int = Field(ge=0)
    citation_evaluable_count: int = Field(ge=0)
    citation_supported_count: int = Field(ge=0)
    answer_evaluable_count: int = Field(ge=0)
    unsupported_answer_count: int = Field(ge=0)
    unsafe_evaluable_count: int = Field(ge=0)
    unsafe_behavior_count: int = Field(ge=0)
    task_success_rate: Decimal | None
    structured_output_validity_rate: Decimal | None
    citation_support_rate: Decimal | None
    unsupported_answer_rate: Decimal | None
    unsafe_behavior_rate: Decimal | None


class QualityCheckResult(FrozenModel):
    check_name: QualityCheckName
    state: CheckState
    condition_id: core.ConditionId | None = None
    observed: Decimal | None = None
    reference: Decimal | None = None
    threshold: Decimal | None = None
    reason: str | None = None


class QualityNonInferiorityResult(FrozenModel):
    state: QualityGateState
    conditions: tuple[ConditionQualityAggregate, ...] = Field(min_length=3, max_length=3)
    checks: tuple[QualityCheckResult, ...]
    quality_gate_passed: bool

    @model_validator(mode="after")
    def validate_gate(self) -> Self:
        if self.quality_gate_passed != (self.state is QualityGateState.PASSED):
            raise ValueError("quality gate pass flag must match quality gate state")
        return self


class RuntimeTrajectoryEndpoint(FrozenModel):
    run_id: str
    comparison_pair_id: str
    condition_id: core.ConditionId
    state: RuntimeEndpointState
    primary_endpoint_tokens: int | None = Field(default=None, ge=0)
    warm_eligible_turn_count: int = Field(ge=0, le=3)
    warm_ineligible_turn_count: int = Field(ge=0, le=3)
    missing_candidate_measurement_count: int = Field(ge=0, le=3)
    missing_primary_telemetry_count: int = Field(ge=0, le=3)
    cold_turn_observed: bool
    cold_turn_telemetry_complete: bool
    route_realization_valid: bool

    @model_validator(mode="after")
    def validate_endpoint(self) -> Self:
        available = self.state is RuntimeEndpointState.AVAILABLE
        if available != (self.primary_endpoint_tokens is not None):
            raise ValueError("runtime endpoint availability and value must reconcile")
        return self


class BootstrapInterval(FrozenModel):
    sample_count: Literal[10000] = 10000
    seed: Literal[20260712] = 20260712
    confidence_level: Literal["0.95"] = "0.95"
    point_estimate: float
    lower_bound: float
    upper_bound: float


class RuntimeContrastResult(FrozenModel):
    contrast_id: Literal["B-A", "C-B", "C-A"]
    claim_family: ClaimFamily
    left_condition: core.ConditionId
    right_condition: core.ConditionId
    planned_pair_count: Literal[60] = 60
    eligible_pair_count: int = Field(ge=0, le=RUNTIME_PAIR_COUNT)
    excluded_pair_count: int = Field(ge=0, le=RUNTIME_PAIR_COUNT)
    paired_differences: tuple[int, ...]
    state: RuntimeContrastState
    interval: BootstrapInterval | None
    improvement_direction_established: bool

    @model_validator(mode="after")
    def validate_contrast(self) -> Self:
        if self.eligible_pair_count + self.excluded_pair_count != self.planned_pair_count:
            raise ValueError("runtime pair counts must reconcile")
        if self.eligible_pair_count != len(self.paired_differences):
            raise ValueError("eligible pair count must match paired differences")
        if self.state is RuntimeContrastState.COMPLETE and self.eligible_pair_count != 60:
            raise ValueError("complete runtime contrast requires all planned pairs")
        if self.state is RuntimeContrastState.COMPLETE and self.interval is None:
            raise ValueError("complete runtime contrast requires a bootstrap interval")
        if self.state is RuntimeContrastState.BLOCKED and self.improvement_direction_established:
            raise ValueError("blocked runtime contrast cannot establish improvement")
        return self


class ClaimDecisionResult(FrozenModel):
    claim_family: ClaimFamily
    contrast_id: Literal["B-A", "C-B", "C-A"]
    decision: ClaimDecision
    reason: str


class FeedbackClaimPolicy(FrozenModel):
    measured_feedback_required_for_north_star_claims: Literal[False] = False
    measured_feedback_required_for_feedback_specific_claims: Literal[True] = True
    feedback_specific_claims_without_measured_feedback_permitted: Literal[False] = False


class Final342AnalysisResult(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    engine_version: Literal["final-342-analysis-engine-v1"] = ENGINE_VERSION
    evidence_state: AnalysisEvidenceState
    run_accountability: RunAccountability
    quality_noninferiority: QualityNonInferiorityResult
    runtime_endpoints: tuple[RuntimeTrajectoryEndpoint, ...]
    runtime_contrasts: tuple[RuntimeContrastResult, ...] = Field(min_length=3, max_length=3)
    claim_decisions: tuple[ClaimDecisionResult, ...] = Field(min_length=3, max_length=3)
    feedback_claim_policy: FeedbackClaimPolicy = FeedbackClaimPolicy()
    machine_readable_errors: tuple[AnalysisErrorCode, ...]
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence_state(self) -> Self:
        has_errors = bool(self.machine_readable_errors)
        is_incomplete = self.evidence_state is AnalysisEvidenceState.EVIDENCE_INCOMPLETE
        if has_errors != is_incomplete:
            raise ValueError("analysis evidence state must reconcile with analysis errors")
        return self


class DenominatorPolicy(FrozenModel):
    scheduled_trajectory_source: Literal["planned_run_ledger.runs"]
    total_scheduled_trajectories: Literal[342]
    functional_scheduled_trajectories: Literal[162]
    runtime_scheduled_trajectories: Literal[180]
    functional_runs_per_condition: Literal[54]
    runtime_runs_per_condition: Literal[60]
    runtime_comparison_pairs: Literal[60]
    failures_remain_in_accountability: Literal[True]
    replacement_cases_permitted: Literal[False]


class QualityPolicy(FrozenModel):
    task_success_regression_margin: Literal["0.05"]
    structured_output_validity_minimum: Literal["0.95"]
    citation_support_regression_permitted: Literal[False]
    unsupported_answer_rate_increase_permitted: Literal[False]
    unsafe_behavior_rate_increase_permitted: Literal[False]
    retrieval_configuration_change_permitted: Literal[False]
    evidence_incomplete_permits_quality_decision: Literal[False]
    quality_gate_precedes_runtime_improvement_claim: Literal[True]


class RuntimePolicy(FrozenModel):
    primary_endpoint_id: Literal["warm-eligible-newly-computed-prefill-tokens-v1"]
    telemetry_field: Literal["newly_computed_prefill_tokens"]
    candidate_turn_indices: tuple[Literal[2, 3, 4], ...]
    aggregation: Literal["sum_warm_eligible_turns_within_runtime_trajectory"]
    non_warm_candidate_turn_is_error: Literal[False]
    missing_candidate_measurement_blocks_endpoint: Literal[True]
    missing_warm_primary_telemetry_blocks_endpoint: Literal[True]
    missing_cold_telemetry_blocks_primary_endpoint: Literal[False]
    complete_pair_set_required_for_effect_claim: Literal[True]
    contrasts: tuple[Literal["B-A", "C-B", "C-A"], ...]


class StatisticalPolicy(FrozenModel):
    method: Literal["percentile_bootstrap"]
    resampling_unit: Literal["comparison_pair_at_episode_level"]
    bootstrap_samples: Literal[10000]
    confidence_level: Literal["0.95"]
    random_seed: Literal[20260712]
    point_estimator: Literal["median_paired_difference"]
    percentile_interpolation: Literal["linear_empirical_p_times_n_minus_1"]
    improvement_requires_negative_point_estimate: Literal[True]
    improvement_requires_ci_upper_bound_below_zero: Literal[True]
    practical_effect_threshold_defined: Literal[False]


class FeedbackReconciliation(FrozenModel):
    historical_pre_run_feedback_blocker_superseded: Literal[True]
    measured_feedback_required_for_north_star_claims: Literal[False]
    measured_feedback_required_for_feedback_specific_claims: Literal[True]
    feedback_specific_claims_without_measured_feedback_permitted: Literal[False]
    historical_gate7_modified: Literal[False]


class ImplementationBoundary(FrozenModel):
    analysis_engine_implemented: Literal[True]
    producer_modified: Literal[False]
    measured_quality_reducer_modified: Literal[False]
    measured_feedback_successor_implemented: Literal[False]
    offline_integration_rehearsal_implemented: Literal[False]
    execution_manifest_frozen: Literal[False]
    next_missing_boundary: Literal["FINAL_342_OFFLINE_ORCHESTRATION_AND_INTEGRATION_REHEARSAL_V1"]


class SafetyState(FrozenModel):
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    manifest_freeze_permitted: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class AnalysisBoundaryRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    analysis_engine_id: Literal["auragateway-final-342-analysis-engine-v1"]
    status: Literal["PROPOSED_FOR_FINAL_342_ANALYSIS_ENGINE_ACCEPTANCE"]
    base_main_commit: Literal["c5bac2c3d2903418c60ad59a190c0dc7e5adfdd3"]
    decision: Literal["FINAL_342_ANALYSIS_ENGINE_V1"]
    source_bindings: tuple[SourceBinding, ...]
    denominator_policy: DenominatorPolicy
    quality_policy: QualityPolicy
    runtime_policy: RuntimePolicy
    statistical_policy: StatisticalPolicy
    feedback_reconciliation: FeedbackReconciliation
    implementation_boundary: ImplementationBoundary
    safety_state: SafetyState
    next_gate: Literal["AUTHOR_FINAL_342_OFFLINE_ORCHESTRATION_AND_INTEGRATION_REHEARSAL_V1"]

    @model_validator(mode="after")
    def validate_source_set(self) -> Self:
        observed = {item.path: item.git_blob_sha for item in self.source_bindings}
        if observed != EXPECTED_SOURCE_BLOBS:
            raise ValueError("analysis engine source binding set drifted")
        return self


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def analysis_input_digest(value: Final342AnalysisInput) -> str:
    return sha256_bytes(canonical_json_bytes(value.model_dump(mode="json")))


def _rate(numerator: int, denominator: int) -> Decimal | None:
    if denominator <= 0:
        return None
    return Decimal(numerator) / Decimal(denominator)


def _dedupe_errors(values: list[AnalysisErrorCode]) -> tuple[AnalysisErrorCode, ...]:
    return tuple(dict.fromkeys(values))


def _planned_run_shape_valid(planned_runs: tuple[core.PlannedRun, ...]) -> bool:
    if len(planned_runs) != RUN_COUNT:
        return False
    if tuple(item.planned_order_index for item in planned_runs) != tuple(range(RUN_COUNT)):
        return False
    run_ids = tuple(item.run_id for item in planned_runs)
    trace_ids = tuple(item.trace_id for item in planned_runs)
    if len(run_ids) != len(set(run_ids)) or len(trace_ids) != len(set(trace_ids)):
        return False

    for workload, expected_pairs, expected_per_condition in (
        (core.WorkloadId.FUNCTIONAL, FUNCTIONAL_PAIR_COUNT, RUNS_PER_FUNCTIONAL_CONDITION),
        (core.WorkloadId.RUNTIME_MICROBENCHMARK, RUNTIME_PAIR_COUNT, RUNS_PER_RUNTIME_CONDITION),
    ):
        rows = tuple(item for item in planned_runs if item.workload is workload)
        condition_counts = {
            condition: sum(item.condition_id is condition for item in rows)
            for condition in core.ConditionId
        }
        if any(count != expected_per_condition for count in condition_counts.values()):
            return False
        pair_ids = {item.comparison_pair_id for item in rows}
        if len(pair_ids) != expected_pairs:
            return False
        invalid_pair = any(
            {item.condition_id for item in rows if item.comparison_pair_id == pair_id}
            != set(core.ConditionId)
            for pair_id in pair_ids
        )
        if invalid_pair:
            return False
    return True


def _index_planned_runs(
    planned_runs: tuple[core.PlannedRun, ...],
) -> tuple[dict[str, core.PlannedRun], bool]:
    result: dict[str, core.PlannedRun] = {}
    duplicate = False
    for item in planned_runs:
        duplicate = duplicate or item.run_id in result
        result[item.run_id] = item
    return result, duplicate


def _index_plan_bindings(
    bindings: tuple[producer.PlanBinding, ...],
) -> tuple[dict[str, producer.PlanBinding], bool]:
    result: dict[str, producer.PlanBinding] = {}
    duplicate = False
    for item in bindings:
        duplicate = duplicate or item.run_id in result
        result[item.run_id] = item
    return result, duplicate


def _index_trace_bindings(
    bindings: tuple[core.RuntimeTraceIdentity, ...],
) -> tuple[dict[str, core.RuntimeTraceIdentity], bool]:
    result: dict[str, core.RuntimeTraceIdentity] = {}
    duplicate = False
    for item in bindings:
        duplicate = duplicate or item.run_id in result
        result[item.run_id] = item
    return result, duplicate


def _index_terminals(
    terminals: tuple[producer.TrajectoryTerminalRecord, ...],
) -> tuple[dict[str, producer.TrajectoryTerminalRecord], bool]:
    result: dict[str, producer.TrajectoryTerminalRecord] = {}
    duplicate = False
    for item in terminals:
        duplicate = duplicate or item.run_id in result
        result[item.run_id] = item
    return result, duplicate


def _index_quality_results(
    results: tuple[quality.MeasuredQualityRunResult, ...],
) -> tuple[dict[str, quality.MeasuredQualityRunResult], bool]:
    indexed: dict[str, quality.MeasuredQualityRunResult] = {}
    duplicate = False
    for item in results:
        duplicate = duplicate or item.run_id in indexed
        indexed[item.run_id] = item
    return indexed, duplicate


def _plan_binding_matches(
    planned: core.PlannedRun,
    binding: producer.PlanBinding,
) -> bool:
    return all(
        (
            planned.planned_order_index == binding.planned_order_index,
            planned.run_id == binding.run_id,
            planned.trace_id == binding.trace_id,
            planned.comparison_pair_id == binding.comparison_pair_id,
            planned.workload is binding.workload,
            planned.condition_id is binding.condition_id,
            planned.route_schedule_id is binding.route_schedule_id,
            producer.sha256_text(planned.cache_namespace_id) == binding.cache_namespace_sha256,
        )
    )


def _reconcile_identity_and_accountability(
    value: Final342AnalysisInput,
    errors: list[AnalysisErrorCode],
) -> tuple[
    dict[str, core.PlannedRun],
    dict[str, producer.TrajectoryTerminalRecord],
    dict[str, quality.MeasuredQualityRunResult],
    RunAccountability,
]:
    planned_by_id, planned_duplicate = _index_planned_runs(value.planned_runs)
    if planned_duplicate or not _planned_run_shape_valid(value.planned_runs):
        errors.append(AnalysisErrorCode.PLANNED_LEDGER_INVALID)

    plan_by_id, plan_duplicate = _index_plan_bindings(value.plan_bindings)
    plan_invalid = (
        plan_duplicate or len(plan_by_id) != RUN_COUNT or set(plan_by_id) != set(planned_by_id)
    )
    if not plan_invalid:
        plan_invalid = any(
            not _plan_binding_matches(planned, plan_by_id[run_id])
            for run_id, planned in planned_by_id.items()
        )
    if plan_invalid:
        errors.append(AnalysisErrorCode.PLAN_BINDING_INVALID)

    trace_by_id, trace_duplicate = _index_trace_bindings(value.trace_bindings)
    trace_invalid = (
        trace_duplicate or len(trace_by_id) != RUN_COUNT or set(trace_by_id) != set(planned_by_id)
    )
    manifest_mismatch = False
    if not trace_invalid:
        for run_id, planned in planned_by_id.items():
            trace = trace_by_id[run_id]
            if trace.trace_id != planned.trace_id:
                trace_invalid = True
            if trace.final_execution_manifest_sha256 != value.final_execution_manifest_sha256:
                manifest_mismatch = True
    if trace_invalid:
        errors.append(AnalysisErrorCode.TRACE_BINDING_INVALID)
    if manifest_mismatch:
        errors.append(AnalysisErrorCode.FINAL_EXECUTION_MANIFEST_MISMATCH)

    terminals_by_id, terminal_duplicate = _index_terminals(value.trajectory_terminals)
    unknown_terminal = bool(set(terminals_by_id) - set(planned_by_id))
    terminal_identity_invalid = terminal_duplicate or unknown_terminal
    for run_id, terminal in terminals_by_id.items():
        matched_planned = planned_by_id.get(run_id)
        if matched_planned is not None and terminal.trace_id != matched_planned.trace_id:
            terminal_identity_invalid = True
    if terminal_identity_invalid:
        errors.append(AnalysisErrorCode.TERMINAL_LEDGER_INVALID)
    missing_terminal_ids = set(planned_by_id) - set(terminals_by_id)
    missing_terminal_count = len(missing_terminal_ids)
    if missing_terminal_count:
        errors.append(AnalysisErrorCode.TERMINAL_LEDGER_INCOMPLETE)

    quality_by_id, quality_duplicate = _index_quality_results(value.measured_quality_results)
    functional_ids = {
        item.run_id for item in value.planned_runs if item.workload is core.WorkloadId.FUNCTIONAL
    }
    unknown_quality = bool(set(quality_by_id) - functional_ids)
    if quality_duplicate or unknown_quality:
        errors.append(AnalysisErrorCode.FUNCTIONAL_QUALITY_LEDGER_INVALID)
    missing_quality = functional_ids - set(quality_by_id)
    if missing_quality or len(quality_by_id) != FUNCTIONAL_RUN_COUNT:
        errors.append(AnalysisErrorCode.FUNCTIONAL_QUALITY_LEDGER_INCOMPLETE)
    if missing_terminal_ids & functional_ids:
        errors.append(AnalysisErrorCode.FUNCTIONAL_QUALITY_EVIDENCE_INCOMPLETE)

    quality_identity_invalid = False
    quality_evidence_incomplete = False
    for run_id, result in quality_by_id.items():
        matched_planned = planned_by_id.get(run_id)
        matched_terminal = terminals_by_id.get(run_id)
        if matched_planned is None or matched_planned.workload is not core.WorkloadId.FUNCTIONAL:
            quality_identity_invalid = True
            continue
        if result.episode_id != matched_planned.episode_id:
            quality_identity_invalid = True
        if (
            matched_terminal is not None
            and result.execution_state is not matched_terminal.terminal_state
        ):
            quality_identity_invalid = True
        if result.evidence_state is quality.EvidenceState.EVIDENCE_INCOMPLETE:
            quality_evidence_incomplete = True
        if (
            result.citation_support_status is quality.CitationSupportStatus.EVIDENCE_INCOMPLETE
            or result.unsupported_answer_status
            is quality.UnsupportedAnswerStatus.EVIDENCE_INCOMPLETE
            or result.unsafe_behavior_observed
            is quality.UnsafeBehaviorObservation.EVIDENCE_INCOMPLETE
        ):
            quality_evidence_incomplete = True
        if (
            matched_terminal is not None
            and matched_terminal.terminal_state is producer.TrajectoryTerminalState.COMPLETED
            and result.structured_output_valid is None
        ):
            quality_evidence_incomplete = True
        if (
            result.evidence_state is quality.EvidenceState.COMPLETE
            and result.machine_readable_errors
        ):
            quality_identity_invalid = True
        if (
            matched_terminal is not None
            and matched_terminal.terminal_state is producer.TrajectoryTerminalState.FAILED
            and result.task_success is not False
        ):
            quality_identity_invalid = True
        if (
            matched_terminal is not None
            and matched_terminal.terminal_state is producer.TrajectoryTerminalState.COMPLETED
            and result.task_success is None
        ):
            quality_evidence_incomplete = True
    if quality_identity_invalid:
        errors.append(AnalysisErrorCode.FUNCTIONAL_QUALITY_LEDGER_INVALID)
    if quality_evidence_incomplete:
        errors.append(AnalysisErrorCode.FUNCTIONAL_QUALITY_EVIDENCE_INCOMPLETE)

    completed = sum(
        item.terminal_state is producer.TrajectoryTerminalState.COMPLETED
        for item in terminals_by_id.values()
    )
    failed = sum(
        item.terminal_state is producer.TrajectoryTerminalState.FAILED
        for item in terminals_by_id.values()
    )
    accountability_complete = not any(
        code
        in {
            AnalysisErrorCode.PLANNED_LEDGER_INVALID,
            AnalysisErrorCode.PLAN_BINDING_INVALID,
            AnalysisErrorCode.TRACE_BINDING_INVALID,
            AnalysisErrorCode.FINAL_EXECUTION_MANIFEST_MISMATCH,
            AnalysisErrorCode.TERMINAL_LEDGER_INCOMPLETE,
            AnalysisErrorCode.TERMINAL_LEDGER_INVALID,
        }
        for code in errors
    )
    accountability = RunAccountability(
        planned_run_count=len(value.planned_runs),
        plan_binding_count=len(value.plan_bindings),
        trace_binding_count=len(value.trace_bindings),
        terminal_record_count=len(value.trajectory_terminals),
        completed_run_count=completed,
        failed_run_count=failed,
        missing_terminal_count=missing_terminal_count,
        functional_quality_result_count=len(value.measured_quality_results),
        accountability_complete=accountability_complete,
    )
    return planned_by_id, terminals_by_id, quality_by_id, accountability


def _condition_quality_aggregate(
    condition: core.ConditionId,
    planned_by_id: dict[str, core.PlannedRun],
    quality_by_id: dict[str, quality.MeasuredQualityRunResult],
) -> ConditionQualityAggregate:
    run_ids = tuple(
        run_id
        for run_id, planned in planned_by_id.items()
        if planned.workload is core.WorkloadId.FUNCTIONAL and planned.condition_id is condition
    )
    results = tuple(quality_by_id[run_id] for run_id in run_ids if run_id in quality_by_id)

    task_success_count = sum(item.task_success is True for item in results)
    structured_valid_count = sum(item.structured_output_valid is True for item in results)
    citation_evaluable = tuple(
        item
        for item in results
        if item.citation_support_status
        in {quality.CitationSupportStatus.SUPPORTED, quality.CitationSupportStatus.UNSUPPORTED}
    )
    citation_supported_count = sum(
        item.citation_support_status is quality.CitationSupportStatus.SUPPORTED
        for item in citation_evaluable
    )
    answer_evaluable = tuple(
        item
        for item in results
        if item.unsupported_answer_status
        in {quality.UnsupportedAnswerStatus.OBSERVED, quality.UnsupportedAnswerStatus.NOT_OBSERVED}
    )
    unsupported_answer_count = sum(
        item.unsupported_answer_status is quality.UnsupportedAnswerStatus.OBSERVED
        for item in answer_evaluable
    )
    unsafe_evaluable = tuple(
        item
        for item in results
        if item.unsafe_behavior_observed
        in {
            quality.UnsafeBehaviorObservation.OBSERVED,
            quality.UnsafeBehaviorObservation.NOT_OBSERVED,
        }
    )
    unsafe_behavior_count = sum(
        item.unsafe_behavior_observed is quality.UnsafeBehaviorObservation.OBSERVED
        for item in unsafe_evaluable
    )

    sample_count = len(run_ids)
    return ConditionQualityAggregate(
        condition_id=condition,
        sample_count=sample_count,
        task_success_count=task_success_count,
        structured_output_valid_count=structured_valid_count,
        citation_evaluable_count=len(citation_evaluable),
        citation_supported_count=citation_supported_count,
        answer_evaluable_count=len(answer_evaluable),
        unsupported_answer_count=unsupported_answer_count,
        unsafe_evaluable_count=len(unsafe_evaluable),
        unsafe_behavior_count=unsafe_behavior_count,
        task_success_rate=_rate(task_success_count, sample_count),
        structured_output_validity_rate=_rate(structured_valid_count, sample_count),
        citation_support_rate=_rate(citation_supported_count, len(citation_evaluable)),
        unsupported_answer_rate=_rate(unsupported_answer_count, len(answer_evaluable)),
        unsafe_behavior_rate=_rate(unsafe_behavior_count, len(unsafe_evaluable)),
    )


def _compare_non_regression(
    *,
    check_name: QualityCheckName,
    condition: core.ConditionId,
    candidate: Decimal | None,
    baseline: Decimal | None,
    candidate_must_be_at_least_baseline: bool,
) -> QualityCheckResult:
    if candidate is None or baseline is None:
        return QualityCheckResult(
            check_name=check_name,
            state=CheckState.BLOCKED,
            condition_id=condition,
            observed=candidate,
            reference=baseline,
            reason="RATE_DENOMINATOR_UNAVAILABLE",
        )
    passed = candidate >= baseline if candidate_must_be_at_least_baseline else candidate <= baseline
    return QualityCheckResult(
        check_name=check_name,
        state=CheckState.PASSED if passed else CheckState.FAILED,
        condition_id=condition,
        observed=candidate,
        reference=baseline,
        threshold=baseline,
    )


def _evaluate_quality(
    value: Final342AnalysisInput,
    planned_by_id: dict[str, core.PlannedRun],
    quality_by_id: dict[str, quality.MeasuredQualityRunResult],
    errors: list[AnalysisErrorCode],
) -> QualityNonInferiorityResult:
    aggregates = tuple(
        _condition_quality_aggregate(condition, planned_by_id, quality_by_id)
        for condition in core.ConditionId
    )
    aggregate_by_condition = {item.condition_id: item for item in aggregates}
    identity_by_condition = {item.condition_id: item for item in value.condition_identities}
    checks: list[QualityCheckResult] = []

    retrieval_fingerprints = {
        item.retrieval_configuration_fingerprint for item in value.condition_identities
    }
    retrieval_match = len(retrieval_fingerprints) == 1
    checks.append(
        QualityCheckResult(
            check_name=QualityCheckName.RETRIEVAL_CONFIGURATION_MATCH,
            state=CheckState.PASSED if retrieval_match else CheckState.BLOCKED,
            reason=None if retrieval_match else "RETRIEVAL_CONFIGURATION_DRIFT",
        )
    )

    episode_manifests = {item.episode_manifest_sha256 for item in value.condition_identities}
    episode_match = len(episode_manifests) == 1
    checks.append(
        QualityCheckResult(
            check_name=QualityCheckName.EPISODE_MANIFEST_MATCH,
            state=CheckState.PASSED if episode_match else CheckState.BLOCKED,
            reason=None if episode_match else "EPISODE_MANIFEST_DRIFT",
        )
    )

    functional_evidence_incomplete = any(
        code
        in {
            AnalysisErrorCode.FUNCTIONAL_QUALITY_LEDGER_INCOMPLETE,
            AnalysisErrorCode.FUNCTIONAL_QUALITY_LEDGER_INVALID,
            AnalysisErrorCode.FUNCTIONAL_QUALITY_EVIDENCE_INCOMPLETE,
        }
        for code in errors
    )

    for condition in core.ConditionId:
        rate = aggregate_by_condition[condition].structured_output_validity_rate
        if functional_evidence_incomplete or rate is None:
            checks.append(
                QualityCheckResult(
                    check_name=QualityCheckName.STRUCTURED_OUTPUT_VALIDITY,
                    state=CheckState.BLOCKED,
                    condition_id=condition,
                    observed=rate,
                    threshold=STRUCTURED_VALIDITY_MINIMUM,
                    reason="FUNCTIONAL_EVIDENCE_INCOMPLETE",
                )
            )
        else:
            checks.append(
                QualityCheckResult(
                    check_name=QualityCheckName.STRUCTURED_OUTPUT_VALIDITY,
                    state=(
                        CheckState.PASSED
                        if rate >= STRUCTURED_VALIDITY_MINIMUM
                        else CheckState.FAILED
                    ),
                    condition_id=condition,
                    observed=rate,
                    threshold=STRUCTURED_VALIDITY_MINIMUM,
                )
            )

    baseline = aggregate_by_condition[core.ConditionId.A]
    for condition in (core.ConditionId.B, core.ConditionId.C):
        candidate = aggregate_by_condition[condition]
        if functional_evidence_incomplete:
            for check_name in (
                QualityCheckName.CITATION_SUPPORT_NON_REGRESSION,
                QualityCheckName.UNSUPPORTED_ANSWER_NON_REGRESSION,
                QualityCheckName.TASK_SUCCESS_NON_INFERIORITY,
                QualityCheckName.UNSAFE_BEHAVIOR_NON_REGRESSION,
            ):
                checks.append(
                    QualityCheckResult(
                        check_name=check_name,
                        state=CheckState.BLOCKED,
                        condition_id=condition,
                        reason="FUNCTIONAL_EVIDENCE_INCOMPLETE",
                    )
                )
            continue

        checks.append(
            _compare_non_regression(
                check_name=QualityCheckName.CITATION_SUPPORT_NON_REGRESSION,
                condition=condition,
                candidate=candidate.citation_support_rate,
                baseline=baseline.citation_support_rate,
                candidate_must_be_at_least_baseline=True,
            )
        )
        checks.append(
            _compare_non_regression(
                check_name=QualityCheckName.UNSUPPORTED_ANSWER_NON_REGRESSION,
                condition=condition,
                candidate=candidate.unsupported_answer_rate,
                baseline=baseline.unsupported_answer_rate,
                candidate_must_be_at_least_baseline=False,
            )
        )

        candidate_task = candidate.task_success_rate
        baseline_task = baseline.task_success_rate
        if candidate_task is None or baseline_task is None:
            checks.append(
                QualityCheckResult(
                    check_name=QualityCheckName.TASK_SUCCESS_NON_INFERIORITY,
                    state=CheckState.BLOCKED,
                    condition_id=condition,
                    observed=candidate_task,
                    reference=baseline_task,
                    reason="TASK_SUCCESS_RATE_UNAVAILABLE",
                )
            )
        else:
            minimum = baseline_task - TASK_SUCCESS_MARGIN
            checks.append(
                QualityCheckResult(
                    check_name=QualityCheckName.TASK_SUCCESS_NON_INFERIORITY,
                    state=(CheckState.PASSED if candidate_task >= minimum else CheckState.FAILED),
                    condition_id=condition,
                    observed=candidate_task,
                    reference=baseline_task,
                    threshold=minimum,
                )
            )

        checks.append(
            _compare_non_regression(
                check_name=QualityCheckName.UNSAFE_BEHAVIOR_NON_REGRESSION,
                condition=condition,
                candidate=candidate.unsafe_behavior_rate,
                baseline=baseline.unsafe_behavior_rate,
                candidate_must_be_at_least_baseline=False,
            )
        )

    identity_complete = set(identity_by_condition) == set(core.ConditionId)
    if not identity_complete or any(item.state is CheckState.BLOCKED for item in checks):
        state = QualityGateState.BLOCKED
    elif any(item.state is CheckState.FAILED for item in checks):
        state = QualityGateState.FAILED
    else:
        state = QualityGateState.PASSED
    return QualityNonInferiorityResult(
        state=state,
        conditions=aggregates,
        checks=tuple(checks),
        quality_gate_passed=state is QualityGateState.PASSED,
    )


def _index_measurements(
    value: Final342AnalysisInput,
    planned_by_id: dict[str, core.PlannedRun],
    errors: list[AnalysisErrorCode],
) -> dict[tuple[str, int], producer.TurnMeasurementRecord]:
    indexed: dict[tuple[str, int], producer.TurnMeasurementRecord] = {}
    invalid = False
    for item in value.measurements:
        planned = planned_by_id.get(item.run_id)
        key = (item.run_id, item.turn_index)
        if planned is None or key in indexed:
            invalid = True
        else:
            if item.trace_id != planned.trace_id:
                invalid = True
            if (
                item.trace_identity.final_execution_manifest_sha256
                != value.final_execution_manifest_sha256
            ):
                invalid = True
            if item.trace_identity.trace_id != planned.trace_id:
                invalid = True
        indexed[key] = item
    if invalid:
        errors.append(AnalysisErrorCode.RUNTIME_MEASUREMENT_INVALID)
    return indexed


def _build_runtime_endpoints(
    value: Final342AnalysisInput,
    planned_by_id: dict[str, core.PlannedRun],
    terminals_by_id: dict[str, producer.TrajectoryTerminalRecord],
    errors: list[AnalysisErrorCode],
) -> tuple[RuntimeTrajectoryEndpoint, ...]:
    measurements = _index_measurements(value, planned_by_id, errors)
    endpoints: list[RuntimeTrajectoryEndpoint] = []
    primary_telemetry_incomplete = False

    runtime_runs = tuple(
        item
        for item in value.planned_runs
        if item.workload is core.WorkloadId.RUNTIME_MICROBENCHMARK
    )
    for planned in runtime_runs:
        terminal = terminals_by_id.get(planned.run_id)
        expected_route = core.realize_route(planned.route_schedule_id)
        cold = measurements.get((planned.run_id, 1))
        cold_observed = cold is not None
        cold_complete = cold is not None and cold.newly_computed_prefill_tokens is not None

        if terminal is None:
            endpoints.append(
                RuntimeTrajectoryEndpoint(
                    run_id=planned.run_id,
                    comparison_pair_id=planned.comparison_pair_id,
                    condition_id=planned.condition_id,
                    state=RuntimeEndpointState.EVIDENCE_INCOMPLETE,
                    warm_eligible_turn_count=0,
                    warm_ineligible_turn_count=0,
                    missing_candidate_measurement_count=3,
                    missing_primary_telemetry_count=0,
                    cold_turn_observed=cold_observed,
                    cold_turn_telemetry_complete=cold_complete,
                    route_realization_valid=False,
                )
            )
            continue

        if terminal.terminal_state is producer.TrajectoryTerminalState.FAILED:
            endpoints.append(
                RuntimeTrajectoryEndpoint(
                    run_id=planned.run_id,
                    comparison_pair_id=planned.comparison_pair_id,
                    condition_id=planned.condition_id,
                    state=RuntimeEndpointState.EXECUTION_FAILED,
                    warm_eligible_turn_count=0,
                    warm_ineligible_turn_count=0,
                    missing_candidate_measurement_count=sum(
                        (planned.run_id, turn_index) not in measurements for turn_index in (2, 3, 4)
                    ),
                    missing_primary_telemetry_count=0,
                    cold_turn_observed=cold_observed,
                    cold_turn_telemetry_complete=cold_complete,
                    route_realization_valid=True,
                )
            )
            continue

        warm_eligible_count = 0
        warm_ineligible_count = 0
        missing_measurement_count = 0
        missing_primary_count = 0
        route_valid = True
        endpoint_tokens = 0

        for turn_index in (2, 3, 4):
            measurement = measurements.get((planned.run_id, turn_index))
            if measurement is None:
                missing_measurement_count += 1
                continue
            if measurement.route_identity.worker_id is not expected_route[turn_index - 1]:
                route_valid = False
            if (
                measurement.warm_decision.classification
                is not core.WarmClassification.WARM_ELIGIBLE
            ):
                warm_ineligible_count += 1
                continue
            warm_eligible_count += 1
            if measurement.newly_computed_prefill_tokens is None:
                missing_primary_count += 1
            else:
                endpoint_tokens += measurement.newly_computed_prefill_tokens

        if missing_measurement_count or missing_primary_count:
            state = RuntimeEndpointState.EVIDENCE_INCOMPLETE
            primary_value: int | None = None
            primary_telemetry_incomplete = True
        elif not route_valid:
            state = RuntimeEndpointState.INELIGIBLE
            primary_value = None
        else:
            state = RuntimeEndpointState.AVAILABLE
            primary_value = endpoint_tokens

        endpoints.append(
            RuntimeTrajectoryEndpoint(
                run_id=planned.run_id,
                comparison_pair_id=planned.comparison_pair_id,
                condition_id=planned.condition_id,
                state=state,
                primary_endpoint_tokens=primary_value,
                warm_eligible_turn_count=warm_eligible_count,
                warm_ineligible_turn_count=warm_ineligible_count,
                missing_candidate_measurement_count=missing_measurement_count,
                missing_primary_telemetry_count=missing_primary_count,
                cold_turn_observed=cold_observed,
                cold_turn_telemetry_complete=cold_complete,
                route_realization_valid=route_valid,
            )
        )

    if primary_telemetry_incomplete:
        errors.append(AnalysisErrorCode.RUNTIME_PRIMARY_TELEMETRY_INCOMPLETE)
    return tuple(endpoints)


def _linear_quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_EMPTY_QUANTILE",
            "cannot calculate a quantile from an empty sample",
        )
    position = probability * (len(sorted_values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = position - lower_index
    lower = sorted_values[lower_index]
    upper = sorted_values[upper_index]
    return lower + (upper - lower) * weight


def paired_bootstrap_interval(differences: tuple[int, ...]) -> BootstrapInterval:
    if not differences:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_EMPTY_PAIRED_DIFFERENCES",
            "paired bootstrap requires at least one paired difference",
        )
    point_estimate = float(statistics.median(differences))
    rng = random.Random(BOOTSTRAP_SEED)
    sample_size = len(differences)
    bootstrap_medians: list[float] = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = tuple(differences[rng.randrange(sample_size)] for _ in range(sample_size))
        bootstrap_medians.append(float(statistics.median(sample)))
    bootstrap_medians.sort()
    alpha = 1.0 - CONFIDENCE_LEVEL
    lower = _linear_quantile(bootstrap_medians, alpha / 2.0)
    upper = _linear_quantile(bootstrap_medians, 1.0 - alpha / 2.0)
    return BootstrapInterval(
        point_estimate=point_estimate,
        lower_bound=lower,
        upper_bound=upper,
    )


def _contrast_specifications() -> tuple[
    tuple[
        Literal["B-A", "C-B", "C-A"],
        ClaimFamily,
        core.ConditionId,
        core.ConditionId,
    ],
    ...,
]:
    return (
        (
            "B-A",
            ClaimFamily.CONTEXT_CONSTRUCTION_POLICY,
            core.ConditionId.A,
            core.ConditionId.B,
        ),
        ("C-B", ClaimFamily.ROUTE_POLICY, core.ConditionId.B, core.ConditionId.C),
        ("C-A", ClaimFamily.TOTAL_SYSTEM, core.ConditionId.A, core.ConditionId.C),
    )


def _runtime_contrast(
    *,
    contrast_id: Literal["B-A", "C-B", "C-A"],
    claim_family: ClaimFamily,
    left_condition: core.ConditionId,
    right_condition: core.ConditionId,
    runtime_pair_ids: tuple[str, ...],
    endpoint_by_pair_condition: dict[tuple[str, core.ConditionId], RuntimeTrajectoryEndpoint],
) -> RuntimeContrastResult:
    differences: list[int] = []
    for pair_id in runtime_pair_ids:
        left = endpoint_by_pair_condition.get((pair_id, left_condition))
        right = endpoint_by_pair_condition.get((pair_id, right_condition))
        if (
            left is None
            or right is None
            or left.state is not RuntimeEndpointState.AVAILABLE
            or right.state is not RuntimeEndpointState.AVAILABLE
            or left.primary_endpoint_tokens is None
            or right.primary_endpoint_tokens is None
        ):
            continue
        differences.append(right.primary_endpoint_tokens - left.primary_endpoint_tokens)

    eligible = len(differences)
    excluded = RUNTIME_PAIR_COUNT - eligible
    interval = paired_bootstrap_interval(tuple(differences)) if differences else None
    complete = eligible == RUNTIME_PAIR_COUNT
    improvement = bool(
        complete
        and interval is not None
        and interval.point_estimate < 0
        and interval.upper_bound < 0
    )
    return RuntimeContrastResult(
        contrast_id=contrast_id,
        claim_family=claim_family,
        left_condition=left_condition,
        right_condition=right_condition,
        eligible_pair_count=eligible,
        excluded_pair_count=excluded,
        paired_differences=tuple(differences),
        state=RuntimeContrastState.COMPLETE if complete else RuntimeContrastState.BLOCKED,
        interval=interval,
        improvement_direction_established=improvement,
    )


def _blocked_runtime_contrasts() -> tuple[RuntimeContrastResult, ...]:
    return tuple(
        RuntimeContrastResult(
            contrast_id=contrast_id,
            claim_family=claim_family,
            left_condition=left,
            right_condition=right,
            eligible_pair_count=0,
            excluded_pair_count=60,
            paired_differences=(),
            state=RuntimeContrastState.BLOCKED,
            interval=None,
            improvement_direction_established=False,
        )
        for contrast_id, claim_family, left, right in _contrast_specifications()
    )


def _analyze_runtime_contrasts(
    value: Final342AnalysisInput,
    endpoints: tuple[RuntimeTrajectoryEndpoint, ...],
) -> tuple[RuntimeContrastResult, ...]:
    runtime_pair_ids = tuple(
        dict.fromkeys(
            item.comparison_pair_id
            for item in value.planned_runs
            if item.workload is core.WorkloadId.RUNTIME_MICROBENCHMARK
        )
    )
    endpoint_by_pair_condition = {
        (item.comparison_pair_id, item.condition_id): item for item in endpoints
    }
    if len(runtime_pair_ids) != RUNTIME_PAIR_COUNT or len(endpoint_by_pair_condition) != 180:
        return _blocked_runtime_contrasts()
    return tuple(
        _runtime_contrast(
            contrast_id=contrast_id,
            claim_family=claim_family,
            left_condition=left,
            right_condition=right,
            runtime_pair_ids=runtime_pair_ids,
            endpoint_by_pair_condition=endpoint_by_pair_condition,
        )
        for contrast_id, claim_family, left, right in _contrast_specifications()
    )


def _claim_decisions(
    quality_result: QualityNonInferiorityResult,
    contrasts: tuple[RuntimeContrastResult, ...],
    errors: tuple[AnalysisErrorCode, ...],
) -> tuple[ClaimDecisionResult, ...]:
    decisions: list[ClaimDecisionResult] = []
    for contrast in contrasts:
        if errors:
            decision = ClaimDecision.BLOCKED
            reason = "ANALYSIS_EVIDENCE_INCOMPLETE"
        elif quality_result.state is QualityGateState.BLOCKED:
            decision = ClaimDecision.BLOCKED
            reason = "QUALITY_GATE_BLOCKED"
        elif quality_result.state is QualityGateState.FAILED:
            decision = ClaimDecision.BLOCKED
            reason = "QUALITY_REGRESSION_NOT_IMPROVEMENT"
        elif contrast.state is RuntimeContrastState.BLOCKED:
            decision = ClaimDecision.BLOCKED
            reason = "RUNTIME_CONTRAST_INCOMPLETE"
        elif contrast.improvement_direction_established:
            decision = ClaimDecision.SUPPORTED
            reason = "FROZEN_DIRECTION_AND_INTERVAL_RULE_SATISFIED"
        else:
            decision = ClaimDecision.NOT_ESTABLISHED
            reason = "FROZEN_DIRECTION_AND_INTERVAL_RULE_NOT_SATISFIED"
        decisions.append(
            ClaimDecisionResult(
                claim_family=contrast.claim_family,
                contrast_id=contrast.contrast_id,
                decision=decision,
                reason=reason,
            )
        )
    return tuple(decisions)


def analyze_final_342(value: Final342AnalysisInput) -> Final342AnalysisResult:
    errors: list[AnalysisErrorCode] = []
    if not value.bundle_verification.schema_and_hash_verified:
        errors.append(AnalysisErrorCode.BUNDLE_VERIFICATION_FAILED)

    planned_by_id, terminals_by_id, quality_by_id, accountability = (
        _reconcile_identity_and_accountability(value, errors)
    )
    quality_result = _evaluate_quality(value, planned_by_id, quality_by_id, errors)
    runtime_endpoints = _build_runtime_endpoints(value, planned_by_id, terminals_by_id, errors)
    runtime_contrasts = _analyze_runtime_contrasts(value, runtime_endpoints)
    final_errors = _dedupe_errors(errors)
    claims = _claim_decisions(quality_result, runtime_contrasts, final_errors)
    evidence_state = (
        AnalysisEvidenceState.EVIDENCE_INCOMPLETE
        if final_errors
        else AnalysisEvidenceState.COMPLETE
    )
    return Final342AnalysisResult(
        evidence_state=evidence_state,
        run_accountability=accountability,
        quality_noninferiority=quality_result,
        runtime_endpoints=runtime_endpoints,
        runtime_contrasts=runtime_contrasts,
        claim_decisions=claims,
        machine_readable_errors=final_errors,
        input_digest=analysis_input_digest(value),
    )


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_JSON_READ_FAILED",
            f"unable to read JSON object: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_JSON_SHAPE_INVALID",
            f"JSON value must be a string-keyed object: {path.as_posix()}",
        )
    return cast(dict[str, object], value)


def _git_blob_sha(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_SOURCE_MISSING",
            f"required source is missing or symlinked: {relative}",
        )
    result = subprocess.run(
        ["git", "hash-object", "--", relative],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_GIT_HASH_FAILED",
            f"unable to hash required source: {relative}",
        )
    return result.stdout.strip()


def _require_base_main_ancestor(root: Path) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_BASE_MAIN, "HEAD"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_BASE_MAIN_INVALID",
            "accepted G11.9 merge must be an ancestor of current HEAD",
        )


def _validate_source_bindings(root: Path, record: AnalysisBoundaryRecord) -> None:
    observed = {item.path: item.git_blob_sha for item in record.source_bindings}
    if observed != EXPECTED_SOURCE_BLOBS:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_SOURCE_SET_DRIFT",
            "analysis engine source binding set drifted",
        )
    for relative, expected in EXPECTED_SOURCE_BLOBS.items():
        if _git_blob_sha(root, relative) != expected:
            raise Final342AnalysisError(
                "FINAL_342_ANALYSIS_SOURCE_IDENTITY_DRIFT",
                f"analysis predecessor identity drifted: {relative}",
            )


def _validate_freeze(root: Path) -> None:
    freeze = _read_json_object(root / FREEZE_PATH)
    if freeze.get("total_scheduled_trajectory_count") != 342:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_FREEZE_DRIFT",
            "scheduled trajectory count drifted",
        )
    endpoint = freeze.get("primary_runtime_endpoint")
    statistics_record = freeze.get("statistics")
    quality_record = freeze.get("quality_non_inferiority")
    if not all(isinstance(item, dict) for item in (endpoint, statistics_record, quality_record)):
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_FREEZE_SHAPE_INVALID",
            "frozen analysis sections are incomplete",
        )
    assert isinstance(endpoint, dict)
    assert isinstance(statistics_record, dict)
    assert isinstance(quality_record, dict)

    expected_endpoint: dict[str, object] = {
        "metric_id": "warm-eligible-newly-computed-prefill-tokens-v1",
        "telemetry_field": "newly_computed_prefill_tokens",
        "aggregation": "sum_warm_eligible_turns_within_runtime_trajectory",
        "warm_eligible_turn_indices": [2, 3, 4],
        "paired_difference_orientation": "right_condition_minus_left_condition",
        "primary_point_estimator": "median_paired_difference",
    }
    for key, expected in expected_endpoint.items():
        if endpoint.get(key) != expected:
            raise Final342AnalysisError(
                "FINAL_342_ANALYSIS_ENDPOINT_FREEZE_DRIFT",
                f"primary runtime endpoint drifted: {key}",
            )

    expected_statistics: dict[str, object] = {
        "configuration_id": "paired-bootstrap-v1",
        "method": "percentile_bootstrap",
        "resampling_unit": "comparison_pair_at_episode_level",
        "bootstrap_samples": 10000,
        "confidence_level": "0.95",
        "random_seed": 20260712,
        "runtime_improvement_direction_requires_point_estimate_below_zero": True,
        "runtime_improvement_direction_requires_ci_upper_bound_below_zero": True,
    }
    for key, expected in expected_statistics.items():
        if statistics_record.get(key) != expected:
            raise Final342AnalysisError(
                "FINAL_342_ANALYSIS_STATISTICAL_FREEZE_DRIFT",
                f"statistical freeze drifted: {key}",
            )

    expected_quality: dict[str, object] = {
        "max_task_success_regression_percentage_points": "5",
        "minimum_structured_output_validity": "0.95",
        "citation_support_regression_permitted": False,
        "unsupported_answer_rate_increase_permitted": False,
        "retrieval_configuration_change_permitted": False,
        "unsafe_behavior_regression_permitted": False,
        "quality_gate_required_before_runtime_improvement_claim": True,
    }
    for key, expected in expected_quality.items():
        if quality_record.get(key) != expected:
            raise Final342AnalysisError(
                "FINAL_342_ANALYSIS_QUALITY_FREEZE_DRIFT",
                f"quality freeze drifted: {key}",
            )


def _validate_predecessor_boundaries(root: Path) -> None:
    reducer_record = _read_json_object(
        root / "benchmarks/local_abc/auragateway_final_342_measured_quality_reducers_v1.json"
    )
    reducer_boundary = reducer_record.get("implementation_boundary")
    if not isinstance(reducer_boundary, dict):
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_REDUCER_RECORD_INVALID",
            "G11.9 implementation boundary is missing",
        )
    if reducer_boundary.get("per_run_measured_quality_reducers_implemented") is not True:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_REDUCER_NOT_READY",
            "G11.9 per-run quality reducers are not established",
        )
    if reducer_boundary.get("producer_modified") is not False:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_PRODUCER_BOUNDARY_DRIFT",
            "G11.9 unexpectedly modified producer ownership",
        )

    analysis_record = _read_json_object(
        root / "benchmarks/local_abc/auragateway_final_342_analysis_contracts_v1.json"
    )
    feedback = analysis_record.get("feedback_analysis")
    if not isinstance(feedback, dict):
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_FEEDBACK_LINEAGE_INVALID",
            "historical feedback analysis boundary is missing",
        )
    if feedback.get("trace_level_feedback_evidence_required_for_feedback_claims") is not True:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_FEEDBACK_CLAIM_BOUNDARY_DRIFT",
            "feedback-specific claim evidence requirement drifted",
        )


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _require_base_main_ancestor(root)
    try:
        record = AnalysisBoundaryRecord.model_validate(_read_json_object(root / RECORD_PATH))
    except ValidationError as error:
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_RECORD_INVALID",
            "analysis engine record failed validation",
        ) from error

    _validate_source_bindings(root, record)
    _validate_freeze(root)
    _validate_predecessor_boundaries(root)
    ledger = core.load_runtime_plan(root)
    if not _planned_run_shape_valid(ledger.runs):
        raise Final342AnalysisError(
            "FINAL_342_ANALYSIS_PLANNED_LEDGER_INVALID",
            "frozen planned-run ledger no longer satisfies final analysis shape",
        )

    return {
        "status": "FINAL_342_ANALYSIS_ENGINE_V1_VALID",
        "analysis_engine_id": record.analysis_engine_id,
        "planned_trajectory_count": len(ledger.runs),
        "functional_trajectory_count": FUNCTIONAL_RUN_COUNT,
        "runtime_trajectory_count": RUNTIME_RUN_COUNT,
        "runtime_comparison_pair_count": RUNTIME_PAIR_COUNT,
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "measured_feedback_required_for_north_star_claims": False,
        "feedback_specific_claims_without_measured_feedback_permitted": False,
        "producer_modified": False,
        "manifest_freeze_permitted": False,
        "final_measured_abc_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        if args.command != "validate":
            raise Final342AnalysisError(
                "FINAL_342_ANALYSIS_COMMAND_INVALID",
                "unsupported analysis engine command",
            )
        summary = validate(args.repo_root)
    except Final342AnalysisError as error:
        print(
            json.dumps(
                {"error_code": error.error_code, "safe_message": error.safe_message},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
