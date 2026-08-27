"""Freeze final measured A/B/C repetitions and analysis rules after accepted V2 pilot.

This producer is repository-only and non-authorizing. It binds the accepted
variance-pilot V2 evidence, the frozen Benchmark Constitution, and the existing
342-trajectory planned ledger. It establishes G10 repetition/statistical freeze
without freezing the final execution manifest or issuing execution authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

BASE_MAIN_COMMIT: Final = "c50196bdd9270d8fca38ddc6a8bd05e4ad70f6fb"

PILOT_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_v2_345461230_acceptance_v1.json"
)
PILOT_ACCEPTANCE_SHA256: Final = "f32d51db0a1570a61da22b7165b5b0c623066896449bddd32b5c637f5e5d6473"
PILOT_ACCEPTANCE_GIT_BLOB_SHA: Final = "86c2b63adead0a029620b1dd5ab5ab402e093d60"

PILOT_CLASSIFICATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_345461230_classification_v1.json"
)
PILOT_CLASSIFICATION_SHA256: Final = (
    "57470ef37d43b164fc3906c5cefae6275ba5dec065e3125ba3a41d31dd83ec95"
)

BENCHMARK_CONSTITUTION_PATH: Final = Path("docs/benchmark/AuraGateway_Benchmark_Constitution.md")
BENCHMARK_CONSTITUTION_SHA256: Final = (
    "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
)
BENCHMARK_CONSTITUTION_GIT_BLOB_SHA: Final = "dc25906298a611b71f3482da85c6aba763c474e7"

PLANNED_RUN_LEDGER_PATH: Final = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
PLANNED_RUN_LEDGER_SHA256: Final = (
    "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
)
CONDITION_FINGERPRINTS_SHA256: Final = (
    "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_repetition_statistical_freeze_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_repetition_statistical_freeze_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-27-local-abc-measured-abc-repetition-statistical-freeze-v1.md"
)
FREEZE_PATH: Final = Path(
    "data/evals/benchmark/freeze-v2/measured_abc_repetition_statistical_freeze_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_repetition_statistical_freeze_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_repetition_statistical_freeze_v1_record.json"
)

NEXT_GATE: Final = "REQUALIFY_FINAL_342_TRAJECTORY_EXECUTION_MANIFEST_AGAINST_G10_FREEZE_V1"

FUNCTIONAL_SCHEDULE: Final = ("ABC", "BCA", "CAB")
RUNTIME_SCHEDULE: Final = (
    "ABC",
    "BCA",
    "CAB",
    "ACB",
    "CBA",
    "BAC",
    "ABC",
    "BCA",
    "CAB",
    "CBA",
)


class FreezeError(RuntimeError):
    """Metadata-safe deterministic G10 failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
            "details": list(self.details),
        }


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactIdentity(StrictModel):
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_blob_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class ContrastFreeze(StrictModel):
    contrast_id: Literal["A_vs_B", "B_vs_C", "A_vs_C"]
    left_condition: Literal["A", "B"]
    right_condition: Literal["B", "C"]
    difference_definition: Literal["B-A", "C-B", "C-A"]
    claim_family: Literal[
        "context_construction_policy",
        "route_policy",
        "total_system",
    ]


class BenchmarkSuiteFreeze(StrictModel):
    suite_id: Literal["functional", "runtime_microbenchmark"]
    episode_count: int = Field(gt=0)
    conditions: Literal[3] = 3
    turns_per_trajectory: Literal[4] = 4
    repetitions_per_condition: int = Field(gt=0)
    scheduled_trajectory_count: int = Field(gt=0)
    scheduled_turn_count: int = Field(gt=0)
    schedule_id: Literal[
        "functional-counterbalance-v1",
        "runtime-counterbalance-v1",
    ]
    condition_orders: tuple[str, ...]

    @model_validator(mode="after")
    def validate_suite(self) -> Self:
        expected = {
            "functional": (
                18,
                3,
                162,
                648,
                "functional-counterbalance-v1",
                FUNCTIONAL_SCHEDULE,
            ),
            "runtime_microbenchmark": (
                6,
                10,
                180,
                720,
                "runtime-counterbalance-v1",
                RUNTIME_SCHEDULE,
            ),
        }
        (
            episodes,
            repetitions,
            trajectories,
            turns,
            schedule_id,
            orders,
        ) = expected[self.suite_id]
        if self.episode_count != episodes:
            raise ValueError("suite episode count drifted")
        if self.repetitions_per_condition != repetitions:
            raise ValueError("suite repetition count drifted")
        if self.scheduled_trajectory_count != trajectories:
            raise ValueError("suite trajectory count drifted")
        if self.scheduled_turn_count != turns:
            raise ValueError("suite turn count drifted")
        if self.schedule_id != schedule_id:
            raise ValueError("suite schedule ID drifted")
        if self.condition_orders != orders:
            raise ValueError("suite counterbalance order drifted")
        calculated = self.episode_count * self.conditions * self.repetitions_per_condition
        if calculated != self.scheduled_trajectory_count:
            raise ValueError("suite trajectory arithmetic drifted")
        if self.scheduled_trajectory_count * self.turns_per_trajectory != turns:
            raise ValueError("suite turn arithmetic drifted")
        return self


class PrimaryRuntimeEndpointFreeze(StrictModel):
    metric_id: Literal["warm-eligible-newly-computed-prefill-tokens-v1"] = (
        "warm-eligible-newly-computed-prefill-tokens-v1"
    )
    telemetry_field: Literal["newly_computed_prefill_tokens"] = "newly_computed_prefill_tokens"
    unit: Literal["tokens_per_trajectory"] = "tokens_per_trajectory"
    aggregation: Literal["sum_warm_eligible_turns_within_runtime_trajectory"] = (
        "sum_warm_eligible_turns_within_runtime_trajectory"
    )
    warm_eligible_turn_indices: tuple[Literal[2, 3, 4], ...] = (2, 3, 4)
    direction: Literal["lower_is_better"] = "lower_is_better"
    paired_difference_orientation: Literal["right_condition_minus_left_condition"] = (
        "right_condition_minus_left_condition"
    )
    primary_point_estimator: Literal["median_paired_difference"] = "median_paired_difference"
    final_runner_emission_requalification_required: Literal[True] = True
    cold_turn_retained_and_reported_separately: Literal[True] = True


class StatisticalFreeze(StrictModel):
    configuration_id: Literal["paired-bootstrap-v1"] = "paired-bootstrap-v1"
    method: Literal["percentile_bootstrap"] = "percentile_bootstrap"
    resampling_unit: Literal["comparison_pair_at_episode_level"] = (
        "comparison_pair_at_episode_level"
    )
    bootstrap_samples: Literal[10000] = 10000
    confidence_level: Decimal = Decimal("0.95")
    random_seed: Literal[20260712] = 20260712
    report_run_count: Literal[True] = True
    report_successful_run_count: Literal[True] = True
    report_failure_count: Literal[True] = True
    report_median: Literal[True] = True
    report_p25: Literal[True] = True
    report_p75: Literal[True] = True
    report_minimum: Literal[True] = True
    report_maximum: Literal[True] = True
    report_p90_where_useful: Literal[True] = True
    report_paired_per_episode_differences: Literal[True] = True
    report_cold_and_warm_views: Literal[True] = True
    report_completed_and_failure_accounted_views: Literal[True] = True
    runtime_improvement_direction_requires_point_estimate_below_zero: Literal[True] = True
    runtime_improvement_direction_requires_ci_upper_bound_below_zero: Literal[True] = True
    academic_statistical_significance_claim_permitted: Literal[False] = False
    universal_generalization_claim_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_statistics(self) -> Self:
        if self.confidence_level != Decimal("0.95"):
            raise ValueError("confidence level drifted")
        return self


class QualityNonInferiorityFreeze(StrictModel):
    policy_id: Literal["quality-non-inferiority-v1"] = "quality-non-inferiority-v1"
    max_task_success_regression_percentage_points: Decimal = Decimal("5")
    minimum_structured_output_validity: Decimal = Decimal("0.95")
    citation_support_regression_permitted: Literal[False] = False
    unsupported_answer_rate_increase_permitted: Literal[False] = False
    retrieval_configuration_change_permitted: Literal[False] = False
    unsafe_behavior_regression_permitted: Literal[False] = False
    comparison_eligibility_required: Literal[True] = True
    quality_gate_required_before_runtime_improvement_claim: Literal[True] = True
    deterministic_checks_fraction: Decimal = Decimal("1")
    primary_rubric_review_fraction: Decimal = Decimal("1")
    independent_double_review_fraction: Decimal = Decimal("0.25")
    double_review_seed: Literal[20260712] = 20260712
    double_review_stratified_by_condition_and_terminal_decision: Literal[True] = True
    reviewers_blinded_to_condition_route_cost_latency_and_cache: Literal[True] = True

    @model_validator(mode="after")
    def validate_quality(self) -> Self:
        if self.max_task_success_regression_percentage_points != Decimal("5"):
            raise ValueError("task-success margin drifted")
        if self.minimum_structured_output_validity != Decimal("0.95"):
            raise ValueError("structured-output floor drifted")
        if self.independent_double_review_fraction != Decimal("0.25"):
            raise ValueError("double-review fraction drifted")
        return self


class WarmResetFreeze(StrictModel):
    first_turn_classification: Literal["cold"] = "cold"
    synthetic_pre_warm_requests_permitted: Literal[False] = False
    primary_runtime_endpoint_uses_warm_eligible_turns_only: Literal[True] = True
    distinct_cache_namespace_per_condition_pair_replication: Literal[True] = True
    cross_condition_namespace_reuse_permitted: Literal[False] = False
    namespace_identity_is_reset_boundary: Literal[True] = True
    prior_same_route_required_for_warm_eligibility: Literal[True] = True
    static_prefix_match_required_for_warm_eligibility: Literal[True] = True
    same_namespace_required_for_warm_eligibility: Literal[True] = True
    ttl_eligibility_required_for_warm_eligibility: Literal[True] = True
    provider_failure_invalidates_warm_eligibility: Literal[True] = True
    session_reset_invalidates_warm_eligibility: Literal[True] = True
    benchmark_transition_invalidates_warm_eligibility: Literal[True] = True
    ambiguous_cache_state_treatment: Literal["unavailable_or_ambiguous"] = (
        "unavailable_or_ambiguous"
    )
    cold_and_warm_results_reported_separately: Literal[True] = True


class RunAccountabilityFreeze(StrictModel):
    policy_id: Literal["provider-request-policy-v1"] = "provider-request-policy-v1"
    maximum_retries_after_initial_attempt: Literal[1] = 1
    retry_jitter_during_measured_execution: Literal[False] = False
    hidden_retries_permitted: Literal[False] = False
    replacement_cases_permitted: Literal[False] = False
    all_attempts_retained: Literal[True] = True
    poor_quality_latency_cost_or_unfavorable_result_is_exclusion_reason: Literal[False] = False
    reruns_require_predeclared_reason_and_preserve_original: Literal[True] = True
    rerun_requires_fresh_execution_authority_when_prior_authority_is_spent: Literal[True] = True


class RepetitionStatisticalFreeze(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    freeze_id: Literal["auragateway-measured-abc-repetition-statistical-freeze-v1"] = (
        "auragateway-measured-abc-repetition-statistical-freeze-v1"
    )
    source_main_commit: Literal["c50196bdd9270d8fca38ddc6a8bd05e4ad70f6fb"] = BASE_MAIN_COMMIT
    source_pilot_saved_version_id: Literal[345461230] = 345461230
    source_pilot_transaction_id: Literal[
        "4341cafac81245d433a680db0bc9c62ecabdbf1d279c0ddc0a19741eb44c7d8b"
    ] = "4341cafac81245d433a680db0bc9c62ecabdbf1d279c0ddc0a19741eb44c7d8b"
    pilot_acceptance: ArtifactIdentity
    pilot_classification: ArtifactIdentity
    benchmark_constitution: ArtifactIdentity
    planned_run_ledger: ArtifactIdentity
    condition_fingerprints_sha256: Literal[
        "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
    ] = CONDITION_FINGERPRINTS_SHA256
    suites: tuple[BenchmarkSuiteFreeze, BenchmarkSuiteFreeze]
    contrasts: tuple[ContrastFreeze, ContrastFreeze, ContrastFreeze]
    primary_runtime_endpoint: PrimaryRuntimeEndpointFreeze
    statistics: StatisticalFreeze
    quality_non_inferiority: QualityNonInferiorityFreeze
    warm_reset: WarmResetFreeze
    run_accountability: RunAccountabilityFreeze
    total_scheduled_trajectory_count: Literal[342] = 342
    total_scheduled_turn_count: Literal[1368] = 1368
    repetition_freeze_established: Literal[True] = True
    statistical_freeze_established: Literal[True] = True
    primary_runtime_endpoint_frozen: Literal[True] = True
    quality_contract_frozen: Literal[True] = True
    warm_reset_policy_frozen: Literal[True] = True
    execution_manifest_frozen: Literal[False] = False
    final_runner_requalification_required: Literal[True] = True
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal[
        "REQUALIFY_FINAL_342_TRAJECTORY_EXECUTION_MANIFEST_AGAINST_G10_FREEZE_V1"
    ] = NEXT_GATE

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if tuple(item.suite_id for item in self.suites) != (
            "functional",
            "runtime_microbenchmark",
        ):
            raise ValueError("suite order drifted")
        if tuple(item.contrast_id for item in self.contrasts) != (
            "A_vs_B",
            "B_vs_C",
            "A_vs_C",
        ):
            raise ValueError("contrast order drifted")
        if sum(item.scheduled_trajectory_count for item in self.suites) != 342:
            raise ValueError("total trajectory count drifted")
        if sum(item.scheduled_turn_count for item in self.suites) != 1368:
            raise ValueError("total turn count drifted")
        return self


class ImplementationReview(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-measured-abc-repetition-statistical-freeze-v1-review"] = (
        "auragateway-measured-abc-repetition-statistical-freeze-v1-review"
    )
    source_main_commit: Literal["c50196bdd9270d8fca38ddc6a8bd05e4ad70f6fb"] = BASE_MAIN_COMMIT
    pilot_repository_acceptance_established: Literal[True] = True
    repetition_freeze_permitted_by_pilot_acceptance: Literal[True] = True
    planned_ledger_identity_valid: Literal[True] = True
    functional_schedule_valid: Literal[True] = True
    runtime_schedule_valid: Literal[True] = True
    statistical_contract_matches_constitution: Literal[True] = True
    quality_contract_matches_constitution: Literal[True] = True
    warm_reset_contract_matches_constitution: Literal[True] = True
    primary_runtime_endpoint_is_new_g10_decision: Literal[True] = True
    primary_runtime_endpoint_runner_requalification_required: Literal[True] = True
    repetition_freeze_established: Literal[True] = True
    statistical_freeze_established: Literal[True] = True
    execution_manifest_frozen: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal[
        "REQUALIFY_FINAL_342_TRAJECTORY_EXECUTION_MANIFEST_AGAINST_G10_FREEZE_V1"
    ] = NEXT_GATE


class ImplementationRecord(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-measured-abc-repetition-statistical-freeze-v1-record"] = (
        "auragateway-measured-abc-repetition-statistical-freeze-v1-record"
    )
    source_main_commit: Literal["c50196bdd9270d8fca38ddc6a8bd05e4ad70f6fb"] = BASE_MAIN_COMMIT
    freeze_path: str
    freeze_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_path: str
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_path: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    test_path: str
    test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    adr_path: str
    adr_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    total_scheduled_trajectory_count: Literal[342] = 342
    total_scheduled_turn_count: Literal[1368] = 1368
    repetition_freeze_established: Literal[True] = True
    statistical_freeze_established: Literal[True] = True
    execution_manifest_frozen: Literal[False] = False
    final_runner_requalification_required: Literal[True] = True
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal[
        "REQUALIFY_FINAL_342_TRAJECTORY_EXECUTION_MANIFEST_AGAINST_G10_FREEZE_V1"
    ] = NEXT_GATE


def _canonical_bytes(model: BaseModel) -> bytes:
    return (
        json.dumps(
            model.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except FileNotFoundError as error:
        raise FreezeError(
            "G10_REQUIRED_ARTIFACT_MISSING",
            "A required G10 source artifact is missing.",
            path.as_posix(),
        ) from error


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise FreezeError(
            "G10_REQUIRED_JSON_INVALID",
            "A required G10 JSON artifact is missing or invalid.",
            path.as_posix(),
            (type(error).__name__,),
        ) from error
    if not isinstance(value, dict):
        raise FreezeError(
            "G10_REQUIRED_JSON_INVALID",
            "A required G10 JSON artifact must contain one object.",
            path.as_posix(),
        )
    return cast(dict[str, object], value)


def _git_blob_sha(repo_root: Path, path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", path.as_posix()],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    value = result.stdout.strip()
    if result.returncode != 0 or len(value) != 40:
        raise FreezeError(
            "G10_GIT_BLOB_IDENTITY_UNAVAILABLE",
            "Unable to establish a required Git blob identity.",
            path.as_posix(),
        )
    return value


def _require_base_lineage(repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise FreezeError(
            "G10_BASE_MAIN_LINEAGE_MISMATCH",
            "G10 requires the merged V2 pilot-acceptance main commit as an ancestor.",
            details=(f"required_ancestor={BASE_MAIN_COMMIT}",),
        )


def _validate_source_identities(repo_root: Path) -> None:
    acceptance_path = repo_root / PILOT_ACCEPTANCE_PATH
    classification_path = repo_root / PILOT_CLASSIFICATION_PATH
    constitution_path = repo_root / BENCHMARK_CONSTITUTION_PATH
    ledger_path = repo_root / PLANNED_RUN_LEDGER_PATH

    identities = (
        (acceptance_path, PILOT_ACCEPTANCE_SHA256),
        (classification_path, PILOT_CLASSIFICATION_SHA256),
        (constitution_path, BENCHMARK_CONSTITUTION_SHA256),
        (ledger_path, PLANNED_RUN_LEDGER_SHA256),
    )
    for path, expected in identities:
        observed = _sha256_file(path)
        if observed != expected:
            raise FreezeError(
                "G10_SOURCE_IDENTITY_DRIFT",
                "A G10 source artifact identity drifted.",
                path.relative_to(repo_root).as_posix(),
                (f"expected={expected}", f"observed={observed}"),
            )

    acceptance_blob = _git_blob_sha(repo_root, PILOT_ACCEPTANCE_PATH)
    if acceptance_blob != PILOT_ACCEPTANCE_GIT_BLOB_SHA:
        raise FreezeError(
            "G10_PILOT_ACCEPTANCE_GIT_BLOB_DRIFT",
            "The merged pilot-acceptance Git blob identity drifted.",
            PILOT_ACCEPTANCE_PATH.as_posix(),
        )

    constitution_blob = _git_blob_sha(repo_root, BENCHMARK_CONSTITUTION_PATH)
    if constitution_blob != BENCHMARK_CONSTITUTION_GIT_BLOB_SHA:
        raise FreezeError(
            "G10_CONSTITUTION_GIT_BLOB_DRIFT",
            "The frozen Benchmark Constitution Git blob identity drifted.",
            BENCHMARK_CONSTITUTION_PATH.as_posix(),
        )


def _validate_pilot_acceptance(repo_root: Path) -> None:
    acceptance = _read_json(repo_root / PILOT_ACCEPTANCE_PATH)
    expected = {
        "source_saved_version_id": 345461230,
        "source_transaction_id": (
            "4341cafac81245d433a680db0bc9c62ecabdbf1d279c0ddc0a19741eb44c7d8b"
        ),
        "source_classification_sha256": PILOT_CLASSIFICATION_SHA256,
        "governed_execution_evidence_accepted": True,
        "task_output_contract_satisfied": True,
        "worker_nuisance_control_qualified": True,
        "estimator_and_nuisance_controls_interpretable": True,
        "pilot_repository_acceptance_established": True,
        "repetition_freeze_permitted": True,
        "repetition_freeze_established": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
    }
    for key, expected_value in expected.items():
        if acceptance.get(key) != expected_value:
            raise FreezeError(
                "G10_PILOT_ACCEPTANCE_BOUNDARY_INVALID",
                "The merged V2 pilot acceptance does not permit G10.",
                PILOT_ACCEPTANCE_PATH.as_posix(),
                (f"field={key}",),
            )


def _pair_condition_order(rows: list[dict[str, object]]) -> str:
    ordered = sorted(rows, key=lambda row: cast(int, row["planned_order_index"]))
    return "".join(cast(str, row["condition_id"]) for row in ordered)


def _validate_planned_ledger(repo_root: Path) -> None:
    ledger = _read_json(repo_root / PLANNED_RUN_LEDGER_PATH)

    exact = {
        "functional_run_order_schedule_id": "functional-counterbalance-v1",
        "runtime_run_order_schedule_id": "runtime-counterbalance-v1",
        "functional_trajectory_count": 162,
        "runtime_trajectory_count": 180,
        "total_trajectory_count": 342,
        "total_turn_count": 1368,
        "maximum_request_attempt_count": 2736,
        "hidden_retry_permitted": False,
        "replacement_case_permitted": False,
        "every_attempt_retained": True,
        "execution_enabled": False,
        "condition_fingerprints_sha256": CONDITION_FINGERPRINTS_SHA256,
    }
    for key, expected in exact.items():
        if ledger.get(key) != expected:
            raise FreezeError(
                "G10_PLANNED_LEDGER_CONTRACT_DRIFT",
                "The existing final planned-run ledger drifted from G10 requirements.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
                (f"field={key}",),
            )

    runs_raw = ledger.get("runs")
    if not isinstance(runs_raw, list) or len(runs_raw) != 342:
        raise FreezeError(
            "G10_PLANNED_LEDGER_RUN_SET_INVALID",
            "The planned-run ledger must contain exactly 342 runs.",
            PLANNED_RUN_LEDGER_PATH.as_posix(),
        )
    runs = cast(list[dict[str, object]], runs_raw)

    order = [row.get("planned_order_index") for row in runs]
    if order != list(range(342)):
        raise FreezeError(
            "G10_PLANNED_LEDGER_ORDER_INVALID",
            "Planned run indexes must remain contiguous and ordered.",
            PLANNED_RUN_LEDGER_PATH.as_posix(),
        )

    for field in ("run_id", "trace_id", "cache_namespace_id"):
        values = [row.get(field) for row in runs]
        if any(not isinstance(value, str) for value in values):
            raise FreezeError(
                "G10_PLANNED_LEDGER_IDENTITY_INVALID",
                "A planned-run identity field is invalid.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
                (f"field={field}",),
            )
        if len(set(cast(list[str], values))) != 342:
            raise FreezeError(
                "G10_PLANNED_LEDGER_IDENTITY_DUPLICATE",
                "A planned-run identity field contains duplicates.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
                (f"field={field}",),
            )

    for row in runs:
        if row.get("turn_count") != 4:
            raise FreezeError(
                "G10_PLANNED_LEDGER_TURN_COUNT_INVALID",
                "Every final planned trajectory must contain four turns.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            )
        if row.get("attempt_number") != 1:
            raise FreezeError(
                "G10_PLANNED_LEDGER_ATTEMPT_INVALID",
                "Every planned ledger row must begin at attempt one.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            )
        if row.get("maximum_request_attempts") != 8:
            raise FreezeError(
                "G10_PLANNED_LEDGER_REQUEST_BUDGET_INVALID",
                "Each four-turn trajectory must preserve the bounded retry budget.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            )
        if row.get("terminal_classification") != "not_started":
            raise FreezeError(
                "G10_PLANNED_LEDGER_EXECUTION_STATE_INVALID",
                "The frozen final planned ledger must remain unexecuted.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            )

    functional = [row for row in runs if row.get("workload") == "functional"]
    runtime = [row for row in runs if row.get("workload") == "runtime_microbenchmark"]
    if len(functional) != 162 or len(runtime) != 180:
        raise FreezeError(
            "G10_PLANNED_LEDGER_SUITE_COUNT_INVALID",
            "Functional/runtime suite counts drifted.",
            PLANNED_RUN_LEDGER_PATH.as_posix(),
        )

    functional_episodes = {cast(str, row["episode_id"]) for row in functional}
    runtime_episodes = {cast(str, row["episode_id"]) for row in runtime}
    if len(functional_episodes) != 18 or len(runtime_episodes) != 6:
        raise FreezeError(
            "G10_PLANNED_LEDGER_EPISODE_COUNT_INVALID",
            "Functional/runtime episode counts drifted.",
            PLANNED_RUN_LEDGER_PATH.as_posix(),
        )

    pair_rows: dict[str, list[dict[str, object]]] = {}
    for row in runs:
        pair_id = row.get("comparison_pair_id")
        if not isinstance(pair_id, str):
            raise FreezeError(
                "G10_PLANNED_LEDGER_PAIR_ID_INVALID",
                "A planned comparison pair identity is invalid.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            )
        pair_rows.setdefault(pair_id, []).append(row)

    if len(pair_rows) != 114:
        raise FreezeError(
            "G10_PLANNED_LEDGER_PAIR_COUNT_INVALID",
            "The final plan must contain exactly 114 A/B/C comparison pairs.",
            PLANNED_RUN_LEDGER_PATH.as_posix(),
        )

    for rows in pair_rows.values():
        if len(rows) != 3 or {row.get("condition_id") for row in rows} != {
            "A",
            "B",
            "C",
        }:
            raise FreezeError(
                "G10_PLANNED_LEDGER_PAIR_SHAPE_INVALID",
                "Each final comparison pair must contain exactly A, B, and C.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            )
        workload = rows[0].get("workload")
        if any(row.get("workload") != workload for row in rows):
            raise FreezeError(
                "G10_PLANNED_LEDGER_PAIR_WORKLOAD_DRIFT",
                "A comparison pair crosses benchmark suites.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            )

        replication = cast(str, rows[0]["replication_id"])
        if any(row.get("replication_id") != replication for row in rows):
            raise FreezeError(
                "G10_PLANNED_LEDGER_PAIR_REPLICATION_DRIFT",
                "A comparison pair crosses replications.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            )

        try:
            replication_number = int(replication.removeprefix("replication-"))
        except ValueError as error:
            raise FreezeError(
                "G10_PLANNED_LEDGER_REPLICATION_ID_INVALID",
                "A replication identity is invalid.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
            ) from error

        observed_order = _pair_condition_order(rows)
        expected_order: str | None = None
        if workload == "functional" and 1 <= replication_number <= 3:
            expected_order = FUNCTIONAL_SCHEDULE[replication_number - 1]
        if workload == "runtime_microbenchmark" and 1 <= replication_number <= 10:
            expected_order = RUNTIME_SCHEDULE[replication_number - 1]
        if observed_order != expected_order:
            raise FreezeError(
                "G10_PLANNED_LEDGER_COUNTERBALANCE_DRIFT",
                "A planned A/B/C condition order drifted from the frozen schedule.",
                PLANNED_RUN_LEDGER_PATH.as_posix(),
                (
                    f"replication={replication}",
                    f"observed={observed_order}",
                    f"expected={expected_order}",
                ),
            )


def _artifact_identity(
    path: Path,
    sha256: str,
    git_blob_sha: str | None = None,
) -> ArtifactIdentity:
    return ArtifactIdentity(
        repository_path=path.as_posix(),
        sha256=sha256,
        git_blob_sha=git_blob_sha,
    )


def build_freeze(repo_root: Path) -> RepetitionStatisticalFreeze:
    root = repo_root.resolve()
    _require_base_lineage(root)
    _validate_source_identities(root)
    _validate_pilot_acceptance(root)
    _validate_planned_ledger(root)

    functional = BenchmarkSuiteFreeze(
        suite_id="functional",
        episode_count=18,
        repetitions_per_condition=3,
        scheduled_trajectory_count=162,
        scheduled_turn_count=648,
        schedule_id="functional-counterbalance-v1",
        condition_orders=FUNCTIONAL_SCHEDULE,
    )
    runtime = BenchmarkSuiteFreeze(
        suite_id="runtime_microbenchmark",
        episode_count=6,
        repetitions_per_condition=10,
        scheduled_trajectory_count=180,
        scheduled_turn_count=720,
        schedule_id="runtime-counterbalance-v1",
        condition_orders=RUNTIME_SCHEDULE,
    )

    contrasts = (
        ContrastFreeze(
            contrast_id="A_vs_B",
            left_condition="A",
            right_condition="B",
            difference_definition="B-A",
            claim_family="context_construction_policy",
        ),
        ContrastFreeze(
            contrast_id="B_vs_C",
            left_condition="B",
            right_condition="C",
            difference_definition="C-B",
            claim_family="route_policy",
        ),
        ContrastFreeze(
            contrast_id="A_vs_C",
            left_condition="A",
            right_condition="C",
            difference_definition="C-A",
            claim_family="total_system",
        ),
    )

    return RepetitionStatisticalFreeze(
        pilot_acceptance=_artifact_identity(
            PILOT_ACCEPTANCE_PATH,
            PILOT_ACCEPTANCE_SHA256,
            PILOT_ACCEPTANCE_GIT_BLOB_SHA,
        ),
        pilot_classification=_artifact_identity(
            PILOT_CLASSIFICATION_PATH,
            PILOT_CLASSIFICATION_SHA256,
        ),
        benchmark_constitution=_artifact_identity(
            BENCHMARK_CONSTITUTION_PATH,
            BENCHMARK_CONSTITUTION_SHA256,
            BENCHMARK_CONSTITUTION_GIT_BLOB_SHA,
        ),
        planned_run_ledger=_artifact_identity(
            PLANNED_RUN_LEDGER_PATH,
            PLANNED_RUN_LEDGER_SHA256,
        ),
        suites=(functional, runtime),
        contrasts=contrasts,
        primary_runtime_endpoint=PrimaryRuntimeEndpointFreeze(),
        statistics=StatisticalFreeze(),
        quality_non_inferiority=QualityNonInferiorityFreeze(),
        warm_reset=WarmResetFreeze(),
        run_accountability=RunAccountabilityFreeze(),
    )


def build_review(repo_root: Path) -> ImplementationReview:
    build_freeze(repo_root)
    return ImplementationReview()


def _write(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(model))


def _load_model(path: Path, model_type: type[BaseModel]) -> BaseModel:
    try:
        return model_type.model_validate_json(path.read_bytes())
    except (FileNotFoundError, ValidationError) as error:
        raise FreezeError(
            "G10_GENERATED_ARTIFACT_INVALID",
            "A generated G10 artifact is missing or invalid.",
            path.as_posix(),
            (type(error).__name__,),
        ) from error


def build_record(repo_root: Path) -> ImplementationRecord:
    root = repo_root.resolve()
    return ImplementationRecord(
        freeze_path=FREEZE_PATH.as_posix(),
        freeze_sha256=_sha256_file(root / FREEZE_PATH),
        review_path=REVIEW_PATH.as_posix(),
        review_sha256=_sha256_file(root / REVIEW_PATH),
        source_path=SOURCE_PATH.as_posix(),
        source_sha256=_sha256_file(root / SOURCE_PATH),
        test_path=TEST_PATH.as_posix(),
        test_sha256=_sha256_file(root / TEST_PATH),
        adr_path=ADR_PATH.as_posix(),
        adr_sha256=_sha256_file(root / ADR_PATH),
    )


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    freeze = build_freeze(root)
    review = build_review(root)
    _write(root / FREEZE_PATH, freeze)
    _write(root / REVIEW_PATH, review)
    record = build_record(root)
    _write(root / RECORD_PATH, record)
    return {
        "status": "MEASURED_ABC_REPETITION_STATISTICAL_FREEZE_V1_GENERATED",
        "total_scheduled_trajectory_count": 342,
        "total_scheduled_turn_count": 1368,
        "repetition_freeze_established": True,
        "statistical_freeze_established": True,
        "primary_runtime_endpoint_frozen": True,
        "quality_contract_frozen": True,
        "warm_reset_policy_frozen": True,
        "execution_manifest_frozen": False,
        "final_runner_requalification_required": True,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_freeze = build_freeze(root)
    expected_review = build_review(root)

    observed_freeze = cast(
        RepetitionStatisticalFreeze,
        _load_model(root / FREEZE_PATH, RepetitionStatisticalFreeze),
    )
    observed_review = cast(
        ImplementationReview,
        _load_model(root / REVIEW_PATH, ImplementationReview),
    )
    observed_record = cast(
        ImplementationRecord,
        _load_model(root / RECORD_PATH, ImplementationRecord),
    )

    if observed_freeze != expected_freeze:
        raise FreezeError(
            "G10_FREEZE_OUTPUT_DRIFT",
            "The committed G10 freeze artifact is not deterministic.",
            FREEZE_PATH.as_posix(),
        )
    if observed_review != expected_review:
        raise FreezeError(
            "G10_REVIEW_OUTPUT_DRIFT",
            "The committed G10 review artifact is not deterministic.",
            REVIEW_PATH.as_posix(),
        )

    expected_record = build_record(root)
    if observed_record != expected_record:
        raise FreezeError(
            "G10_RECORD_OUTPUT_DRIFT",
            "The committed G10 record artifact is not deterministic.",
            RECORD_PATH.as_posix(),
        )

    return {
        "status": "MEASURED_ABC_REPETITION_STATISTICAL_FREEZE_V1_VALID",
        "pilot_repository_acceptance_established": True,
        "repetition_freeze_established": True,
        "statistical_freeze_established": True,
        "primary_runtime_endpoint_frozen": True,
        "quality_contract_frozen": True,
        "warm_reset_policy_frozen": True,
        "execution_manifest_frozen": False,
        "final_runner_requalification_required": True,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": NEXT_GATE,
    }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise FreezeError(
            "G10_ARGUMENT_INVALID",
            "G10 repetition/statistical-freeze arguments are invalid.",
            details=(message,),
        )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="measured-abc-repetition-statistical-freeze-v1")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        item = commands.add_parser(command)
        item.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        result = (
            generate(args.repo_root) if args.command == "generate" else validate(args.repo_root)
        )
        print(
            json.dumps(
                result,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except FreezeError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
