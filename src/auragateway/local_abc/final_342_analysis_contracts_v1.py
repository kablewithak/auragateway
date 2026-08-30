"""Validate the final-342 post-run analysis contract design."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RECORD_PATH = Path("benchmarks/local_abc/auragateway_final_342_analysis_contracts_v1.json")
EXPECTED_BASE_MAIN = "9888f05a8c1c3b36fa9728b2bd2790f5704f4109"

BOUND_SOURCE_BLOBS: dict[str, str] = {
    "benchmark_constitution": "dc25906298a611b71f3482da85c6aba763c474e7",
    "g10_repetition_statistical_freeze": "9999eb0350a3d3e01a9f5f3451f54d7deaa35aef",
    "planned_run_ledger": "553b23e24629bdca81d9fb9fdcbd90cc2081caf0",
    "final_execution_producer": "9bedae7c7815e80d7c03ccc37b1e5261310056cf",
    "measured_review_design": "e667cf734e6fdeec1acf4a5b254beebb78754fb7",
    "quality_gate_contracts": "31c18f9735b26ff194a65bb824f7810db3a208f5",
    "deterministic_quality_contracts": "f25d94de7ad0f5ed2bc4c961a6aaa16e32dd9a09",
    "blinded_quality_contracts": "14a3cdf2463ed980913e7c3c8a37ad037ea84a4d",
    "feedback_contracts": "4375eff8e45ed2cc7bf6ff788200b67e39a07ae1",
    "feedback_manifest": "7c56abed309031e0d9f8d371d2fc1124ff4c8640",
}


class AnalysisContractsError(RuntimeError):
    """Fail-closed analysis-contract validation error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AnalysisContractsError("FINAL_342_ANALYSIS_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceBinding(FrozenModel):
    role: str = Field(min_length=3)
    path: str = Field(min_length=3)
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class DenominatorAuthority(FrozenModel):
    scientific_scheduled_trajectory_source: Literal["planned_run_ledger.runs"]
    total_scheduled_trajectory_count: Literal[342]
    functional_scheduled_trajectory_count: Literal[162]
    runtime_scheduled_trajectory_count: Literal[180]
    total_scheduled_logical_turn_count: Literal[1368]
    maximum_physical_attempt_count: Literal[2736]
    request_reconciliation_scheduled_request_count_role: Literal[
        "operational_attempt_reservation_counter"
    ]
    request_reconciliation_scheduled_request_count_is_scientific_denominator: Literal[False]
    physical_attempt_source: Literal["attempt_action_ledger_v1.json.reservations"]
    transport_completion_source: Literal[
        "attempt_action_ledger_v1.json.transport_outcomes.http_completed"
    ]
    admitted_turn_source: Literal[
        "attempt_action_ledger_v1.json.admissions.evidence.schema_admitted"
    ]
    committed_turn_source: Literal["attempt_action_ledger_v1.json.state_mutations.decision.commit"]
    trajectory_terminal_source: Literal["trajectory_terminal_ledger_v1.json.trajectories"]
    completed_run_runtime_view_required: Literal[True]
    failure_accounted_all_scheduled_view_required: Literal[True]


class ExecutionAccountability(FrozenModel):
    all_planned_run_ids_must_be_reconciled: Literal[True]
    unknown_run_ids_permitted: Literal[False]
    missing_terminal_record_is_evidence_incomplete: Literal[True]
    logical_turn_and_physical_attempt_counts_must_remain_distinct: Literal[True]
    every_attempt_retained: Literal[True]
    hidden_retry_permitted: Literal[False]
    replacement_case_permitted: Literal[False]
    first_causal_failure_preserved: Literal[True]
    secondary_failure_may_mask_primary: Literal[False]
    metric_specific_exclusions_must_use_predeclared_rules: Literal[True]
    excluded_runs_remain_failure_accounted: Literal[True]
    poor_quality_latency_or_unfavorable_result_is_exclusion_reason: Literal[False]
    rerun_original_record_deleted: Literal[False]


class ComparisonEligibility(FrozenModel):
    final_execution_manifest_hash_match_required: Literal[True]
    configuration_fingerprint_match_required: Literal[True]
    mixed_execution_manifest_hashes_eligible_by_default: Literal[False]
    route_realization_required_for_route_dependent_metrics: Literal[True]
    telemetry_sufficiency_required_per_metric_family: Literal[True]
    warm_eligibility_required_for_primary_runtime_endpoint_turns: Literal[True]
    partially_eligible_metric_families_require_explicit_support: Literal[True]
    human_authored_report_may_override_ineligible_decision: Literal[False]
    comparison_gate_records_compared_run_ids: Literal[True]
    comparison_gate_records_mismatched_fields: Literal[True]
    comparison_gate_records_invalidated_metrics: Literal[True]
    comparison_gate_records_invalidated_claims: Literal[True]
    comparison_gate_records_required_reruns: Literal[True]


class QualityAnalysis(FrozenModel):
    functional_population_count: Literal[162]
    runtime_microbenchmark_human_review_required: Literal[False]
    deterministic_scoring_required_for_each_produced_candidate: Literal[True]
    execution_failure_without_candidate_counts_as_task_non_success: Literal[True]
    capture_gap_state: Literal["EVIDENCE_INCOMPLETE"]
    capture_gap_permits_quality_noninferiority: Literal[False]
    capture_gap_permits_runtime_improvement_claim: Literal[False]
    primary_review_required_for_every_reviewable_candidate: Literal[True]
    secondary_review_target_count: Literal[41]
    secondary_schedule_materialized_before_manifest_freeze: Literal[True]
    selected_nonreviewable_case_replacement_permitted: Literal[False]
    material_disagreement_requires_independent_adjudication: Literal[True]
    structured_output_validity_minimum: Literal["0.95"]
    task_success_max_regression_percentage_points: Literal["5"]
    citation_support_regression_permitted: Literal[False]
    unsupported_answer_rate_increase_permitted: Literal[False]
    retrieval_configuration_change_permitted: Literal[False]
    unsafe_route_retry_escalation_refusal_regression_permitted: Literal[False]
    measured_task_success_reducer_required_before_manifest_freeze: Literal[True]
    task_success_may_be_inferred_from_runtime_completion_only: Literal[False]
    task_success_may_be_inferred_from_structured_validity_only: Literal[False]
    historical_synthetic_quality_gate_direct_measured_reuse_permitted: Literal[False]
    historical_quality_threshold_logic_reusable: Literal[True]
    quality_gate_precedes_runtime_improvement_claim: Literal[True]


class RuntimeAnalysis(FrozenModel):
    runtime_population_count: Literal[180]
    runtime_comparison_pair_count: Literal[60]
    primary_endpoint_id: Literal["warm-eligible-newly-computed-prefill-tokens-v1"]
    primary_telemetry_field: Literal["newly_computed_prefill_tokens"]
    turn_1_classification: Literal["cold"]
    primary_candidate_turn_indices: tuple[Literal[2, 3, 4], ...]
    include_turn_only_when_warm_eligible: Literal[True]
    trajectory_aggregation: Literal["sum_warm_eligible_turns_within_runtime_trajectory"]
    direction: Literal["lower_is_better"]
    contrasts: tuple[Literal["B-A", "C-B", "C-A"], ...]
    cold_and_warm_views_reported_separately: Literal[True]
    completed_run_and_failure_accounted_views_required: Literal[True]
    warm_ineligible_or_missing_telemetry_remains_visible_in_coverage: Literal[True]
    monetary_cost_comparison_in_scope: Literal[False]


class StatisticalAndClaimAnalysis(FrozenModel):
    configuration_id: Literal["paired-bootstrap-v1"]
    method: Literal["percentile_bootstrap"]
    resampling_unit: Literal["comparison_pair_at_episode_level"]
    bootstrap_samples: Literal[10000]
    confidence_level: Literal["0.95"]
    random_seed: Literal[20260712]
    primary_point_estimator: Literal["median_paired_difference"]
    runtime_improvement_requires_negative_point_estimate: Literal[True]
    runtime_improvement_requires_ci_upper_bound_below_zero: Literal[True]
    academic_statistical_significance_claim_permitted: Literal[False]
    universal_generalization_claim_permitted: Literal[False]
    decision_precedence: tuple[str, ...]
    earlier_gate_failure_blocks_dependent_claims: Literal[True]
    quality_failure_with_faster_runtime_classification: Literal[
        "quality_regression_not_improvement"
    ]
    monetary_cost_effect_claims_permitted: Literal[False]


class FeedbackAnalysis(FrozenModel):
    trace_level_feedback_evidence_required_for_feedback_claims: Literal[True]
    required_dimensions: tuple[
        Literal[
            "validity",
            "novelty",
            "retention",
            "later_action_change",
            "task_sufficiency",
        ],
        ...,
    ]
    universal_efc_score_permitted: Literal[False]
    historical_synthetic_feedback_direct_measured_reuse_permitted: Literal[False]
    measured_feedback_successor_required_before_manifest_freeze: Literal[True]


class ImplementationBoundary(FrozenModel):
    exact_secondary_review_schedule_implementation_still_required: Literal[True]
    measured_protected_review_exporter_implementation_still_required: Literal[True]
    measured_task_success_reducer_implementation_still_required: Literal[True]
    unsafe_behavior_regression_reducer_implementation_still_required: Literal[True]
    measured_feedback_successor_implementation_still_required: Literal[True]
    producer_modification_authorized_by_this_decision: Literal[False]
    analysis_engine_implementation_authorized_by_this_decision: Literal[False]
    complete_offline_integration_rehearsal_authorized_by_this_decision: Literal[False]
    producer_review_analysis_seam_audit_required_next: Literal[True]


class SafetyState(FrozenModel):
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    execution_manifest_frozen: Literal[False]
    manifest_freeze_permitted: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class AnalysisContractsRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    analysis_contract_id: Literal["auragateway-final-342-analysis-contracts-v1"]
    status: Literal["PROPOSED_FOR_FINAL_342_ANALYSIS_CONTRACT_ACCEPTANCE"]
    base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    decision: Literal["FINAL_342_POST_RUN_ANALYSIS_CONTRACTS_V1"]
    source_bindings: tuple[SourceBinding, ...]
    denominator_authority: DenominatorAuthority
    execution_accountability: ExecutionAccountability
    comparison_eligibility: ComparisonEligibility
    quality_analysis: QualityAnalysis
    runtime_analysis: RuntimeAnalysis
    statistical_and_claim_analysis: StatisticalAndClaimAnalysis
    feedback_analysis: FeedbackAnalysis
    implementation_boundary: ImplementationBoundary
    safety_state: SafetyState
    next_gate: Literal["AUDIT_FINAL_342_PRODUCER_REVIEW_ANALYSIS_SEAMS_V1"]

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if self.base_main_commit != EXPECTED_BASE_MAIN:
            raise ValueError("analysis-contract base main drifted")
        roles = tuple(item.role for item in self.source_bindings)
        if len(roles) != len(set(roles)):
            raise ValueError("analysis-contract source binding roles must be unique")
        if set(roles) != set(BOUND_SOURCE_BLOBS):
            raise ValueError("analysis-contract source binding roles drifted")
        expected_precedence = (
            "bundle_schema_and_hash_verification",
            "run_accountability_verification",
            "execution_manifest_and_configuration_fingerprint_eligibility",
            "telemetry_sufficiency_decision",
            "quality_noninferiority_decision",
            "metric_calculation",
            "claim_generation",
        )
        if self.statistical_and_claim_analysis.decision_precedence != expected_precedence:
            raise ValueError("analysis decision precedence drifted")
        if self.runtime_analysis.primary_candidate_turn_indices != (2, 3, 4):
            raise ValueError("primary runtime candidate turns drifted")
        if self.runtime_analysis.contrasts != ("B-A", "C-B", "C-A"):
            raise ValueError("runtime contrast orientation drifted")
        expected_feedback = (
            "validity",
            "novelty",
            "retention",
            "later_action_change",
            "task_sufficiency",
        )
        if self.feedback_analysis.required_dimensions != expected_feedback:
            raise ValueError("feedback analysis dimensions drifted")
        return self


def _read_json(repo_root: Path, relative: str) -> object:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_SOURCE_MISSING",
            f"required analysis source is missing or symlinked: {relative}",
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_INVALID_JSON",
            f"required analysis source is not valid JSON: {relative}",
        ) from error


def _as_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_SOURCE_SHAPE_INVALID",
            f"{label} must be a JSON object",
        )
    return value


def _git_blob_sha(repo_root: Path, relative: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "hash-object", "--", relative],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_GIT_BLOB_UNREADABLE",
            "unable to inspect analysis source Git blob identity",
        ) from error
    if completed.returncode != 0:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_GIT_BLOB_UNREADABLE",
            f"unable to hash analysis source: {relative}",
        )
    value = completed.stdout.strip()
    if len(value) != 40:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_GIT_BLOB_INVALID",
            f"analysis source Git blob identity is invalid: {relative}",
        )
    return value


def _require_base_main_ancestor(repo_root: Path) -> None:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                EXPECTED_BASE_MAIN,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_GIT_STATE_UNREADABLE",
            "unable to inspect analysis-contract base-main ancestry",
        ) from error
    if completed.returncode != 0:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_BASE_MAIN_MISSING",
            "accepted measured-review merge is not an ancestor",
        )


def _validate_source_bindings(repo_root: Path, record: AnalysisContractsRecord) -> None:
    for binding in record.source_bindings:
        expected = BOUND_SOURCE_BLOBS[binding.role]
        if binding.git_blob_sha != expected:
            raise AnalysisContractsError(
                "FINAL_342_ANALYSIS_RECORD_BINDING_DRIFT",
                f"recorded source binding drifted: {binding.role}",
            )
        observed = _git_blob_sha(repo_root, binding.path)
        if observed != expected:
            raise AnalysisContractsError(
                "FINAL_342_ANALYSIS_SOURCE_IDENTITY_DRIFT",
                f"analysis source identity drifted: {binding.path}",
            )


def _validate_g10(repo_root: Path) -> None:
    relative = "data/evals/benchmark/freeze-v2/measured_abc_repetition_statistical_freeze_v1.json"
    g10 = _as_mapping(_read_json(repo_root, relative), "G10 freeze")
    expected = {
        "total_scheduled_trajectory_count": 342,
        "total_scheduled_turn_count": 1368,
        "primary_runtime_endpoint_frozen": True,
        "quality_contract_frozen": True,
        "warm_reset_policy_frozen": True,
        "final_measured_abc_execution_authorized": False,
        "effect_claims_permitted": False,
    }
    for key, value in expected.items():
        if g10.get(key) != value:
            raise AnalysisContractsError(
                "FINAL_342_ANALYSIS_G10_DRIFT",
                f"G10 analysis field drifted: {key}",
            )

    endpoint = _as_mapping(g10.get("primary_runtime_endpoint"), "G10 runtime endpoint")
    if endpoint.get("metric_id") != "warm-eligible-newly-computed-prefill-tokens-v1":
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_ENDPOINT_DRIFT",
            "G10 primary runtime endpoint drifted",
        )
    if endpoint.get("warm_eligible_turn_indices") != [2, 3, 4]:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_WARM_TURN_DRIFT",
            "G10 warm-eligible turn set drifted",
        )
    if endpoint.get("primary_point_estimator") != "median_paired_difference":
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_POINT_ESTIMATOR_DRIFT",
            "G10 primary runtime point estimator drifted",
        )

    statistics = _as_mapping(g10.get("statistics"), "G10 statistics")
    statistical_expected = {
        "configuration_id": "paired-bootstrap-v1",
        "bootstrap_samples": 10000,
        "confidence_level": "0.95",
        "random_seed": 20260712,
    }
    for statistical_key, statistical_value in statistical_expected.items():
        if statistics.get(statistical_key) != statistical_value:
            raise AnalysisContractsError(
                "FINAL_342_ANALYSIS_STATISTICAL_DRIFT",
                f"G10 statistical field drifted: {statistical_key}",
            )

    quality = _as_mapping(g10.get("quality_non_inferiority"), "G10 quality contract")
    quality_expected = {
        "minimum_structured_output_validity": "0.95",
        "max_task_success_regression_percentage_points": "5",
        "citation_support_regression_permitted": False,
        "unsupported_answer_rate_increase_permitted": False,
        "retrieval_configuration_change_permitted": False,
        "unsafe_behavior_regression_permitted": False,
    }
    for quality_key, quality_value in quality_expected.items():
        if quality.get(quality_key) != quality_value:
            raise AnalysisContractsError(
                "FINAL_342_ANALYSIS_QUALITY_DRIFT",
                f"G10 quality field drifted: {quality_key}",
            )


def _validate_ledger(repo_root: Path) -> None:
    relative = "data/evals/benchmark/preflight-v3/planned_run_ledger.json"
    ledger = _as_mapping(_read_json(repo_root, relative), "planned run ledger")
    expected = {
        "functional_trajectory_count": 162,
        "runtime_trajectory_count": 180,
        "total_trajectory_count": 342,
        "total_turn_count": 1368,
        "maximum_request_attempt_count": 2736,
        "every_attempt_retained": True,
        "hidden_retry_permitted": False,
        "replacement_case_permitted": False,
    }
    for key, value in expected.items():
        if ledger.get(key) != value:
            raise AnalysisContractsError(
                "FINAL_342_ANALYSIS_LEDGER_DRIFT",
                f"planned-run ledger field drifted: {key}",
            )

    runs = ledger.get("runs")
    if not isinstance(runs, list) or len(runs) != 342:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_LEDGER_RUNS_INVALID",
            "planned-run ledger must contain exactly 342 runs",
        )

    runtime_pairs: dict[str, set[str]] = {}
    for raw in runs:
        row = _as_mapping(raw, "planned run")
        if row.get("turn_count") != 4 or row.get("maximum_request_attempts") != 8:
            raise AnalysisContractsError(
                "FINAL_342_ANALYSIS_LEDGER_BUDGET_DRIFT",
                "planned-run turn or attempt budget drifted",
            )
        if row.get("workload") == "runtime_microbenchmark":
            pair_id = row.get("comparison_pair_id")
            condition = row.get("condition_id")
            if not isinstance(pair_id, str) or not isinstance(condition, str):
                raise AnalysisContractsError(
                    "FINAL_342_ANALYSIS_RUNTIME_PAIR_INVALID",
                    "runtime comparison-pair identity is invalid",
                )
            runtime_pairs.setdefault(pair_id, set()).add(condition)

    if len(runtime_pairs) != 60:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_RUNTIME_PAIR_COUNT_DRIFT",
            "runtime analysis must contain exactly 60 comparison pairs",
        )
    if any(conditions != {"A", "B", "C"} for conditions in runtime_pairs.values()):
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_RUNTIME_PAIR_SHAPE_DRIFT",
            "every runtime comparison pair must contain A, B, and C",
        )


def _validate_producer_counter_semantics(repo_root: Path) -> None:
    relative = "src/auragateway/local_abc/final_342_execution_producer_v1.py"
    text = (repo_root / relative).read_text(encoding="utf-8")
    required = (
        "scheduled_request_count=len(self.attempt_reservations)",
        "attempted_request_count=len(self.attempt_reservations)",
        '"attempt_action_ledger_v1.json"',
        '"trajectory_terminal_ledger_v1.json"',
        '"scheduled_trajectory_count": EXPECTED_TRAJECTORY_COUNT',
    )
    if any(marker not in text for marker in required):
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_PRODUCER_SEMANTICS_DRIFT",
            "producer evidence or counter semantics drifted",
        )


def _validate_review_design(repo_root: Path) -> None:
    relative = "benchmarks/local_abc/auragateway_final_342_measured_review_design_v1.json"
    review = _as_mapping(_read_json(repo_root, relative), "measured review design")
    population = _as_mapping(review.get("review_population"), "review population")
    capture = _as_mapping(review.get("capture_policy"), "review capture policy")
    if population.get("planned_functional_trajectory_count") != 162:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_REVIEW_POPULATION_DRIFT",
            "measured-review functional population drifted",
        )
    if population.get("secondary_review_target_count") != 41:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_REVIEW_SAMPLE_DRIFT",
            "measured-review secondary target drifted",
        )
    if capture.get("candidate_exists_capture_failed_quality_state") != "EVIDENCE_INCOMPLETE":
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_CAPTURE_STATE_DRIFT",
            "measured-review capture-gap state drifted",
        )
    if capture.get("quality_non_inferiority_permitted_with_capture_gap") is not False:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_CAPTURE_GATE_DRIFT",
            "capture gap must block quality non-inferiority",
        )


def _validate_historical_successor_boundaries(repo_root: Path) -> None:
    quality_path = repo_root / "src/auragateway/contracts/quality_gate.py"
    quality_text = quality_path.read_text(encoding="utf-8")
    if "synthetic_dry_run: Literal[True] = True" not in quality_text:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_QUALITY_LINEAGE_DRIFT",
            "historical quality gate synthetic boundary drifted",
        )
    if "measured_execution_permitted: Literal[False] = False" not in quality_text:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_QUALITY_LINEAGE_DRIFT",
            "historical quality gate measured boundary drifted",
        )

    feedback_path = repo_root / "src/auragateway/contracts/feedback.py"
    feedback_text = feedback_path.read_text(encoding="utf-8")
    if "synthetic_fixture_execution: Literal[True] = True" not in feedback_text:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_FEEDBACK_LINEAGE_DRIFT",
            "historical feedback synthetic boundary drifted",
        )
    if "universal_efc_score_reported: Literal[False] = False" not in feedback_text:
        raise AnalysisContractsError(
            "FINAL_342_ANALYSIS_FEEDBACK_LINEAGE_DRIFT",
            "historical feedback claim boundary drifted",
        )


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record = AnalysisContractsRecord.model_validate(_read_json(root, RECORD_PATH.as_posix()))
    _require_base_main_ancestor(root)
    _validate_source_bindings(root, record)
    _validate_g10(root)
    _validate_ledger(root)
    _validate_producer_counter_semantics(root)
    _validate_review_design(root)
    _validate_historical_successor_boundaries(root)

    return {
        "status": "FINAL_342_ANALYSIS_CONTRACTS_V1_VALID",
        "scientific_scheduled_trajectory_count": 342,
        "scientific_scheduled_logical_turn_count": 1368,
        "maximum_physical_attempt_count": 2736,
        "functional_quality_population": 162,
        "secondary_review_target_count": 41,
        "runtime_population": 180,
        "runtime_comparison_pair_count": 60,
        "primary_runtime_endpoint": record.runtime_analysis.primary_endpoint_id,
        "request_counter_is_scientific_denominator": False,
        "measured_task_success_reducer_required": True,
        "measured_feedback_successor_required": True,
        "manifest_freeze_permitted": record.safety_state.manifest_freeze_permitted,
        "final_measured_abc_execution_authorized": (
            record.safety_state.final_measured_abc_execution_authorized
        ),
        "effect_claims_permitted": record.safety_state.effect_claims_permitted,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate(Path(args.repo_root))
    except (
        AnalysisContractsError,
        UnicodeDecodeError,
        ValidationError,
        OSError,
    ) as error:
        if isinstance(error, AnalysisContractsError):
            code = error.error_code
            message = error.safe_message
        else:
            code = "FINAL_342_ANALYSIS_VALIDATION_FAILED"
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
