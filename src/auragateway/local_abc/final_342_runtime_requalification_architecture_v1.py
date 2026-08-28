"""Validate the G11.0 final-342 runtime requalification architecture."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_runtime_requalification_architecture_v1.json"
)

EXPECTED_BASE_MAIN = "c05af5260df3cae71ca8d66154b60432b0af46f0"
EXPECTED_LEDGER_SHA256 = "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
EXPECTED_CONDITION_FINGERPRINTS_SHA256 = (
    "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
)
EXPECTED_CONSTITUTION_SHA256 = "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
EXPECTED_REQUIREMENTS_SHA256 = "30799246e6fa8d91246a5277e613ed97f840a164331f1f04a3f17fd84aad20cf"
EXPECTED_PLANNING_MANIFEST_SHA256 = (
    "4bd822375390cf413718553313903679e78b650dfa798955e2f7c61ebd8b8678"
)


class ArchitectureError(RuntimeError):
    """Fail-closed architecture validation error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ArchitectureError("FINAL_342_ARCH_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NorthStar(FrozenModel):
    planned_trajectories: Literal[342]
    planned_turns: Literal[1368]
    maximum_request_attempts: Literal[2736]
    one_governed_final_execution_required: Literal[True]
    effect_claims_permitted_by_this_architecture: Literal[False]


class FrozenSubject(FrozenModel):
    planned_run_ledger_path: str
    planned_run_ledger_sha256: Literal[
        "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
    ]
    condition_fingerprints_path: str
    condition_fingerprints_sha256: Literal[
        "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
    ]
    benchmark_constitution_path: str
    benchmark_constitution_sha256: Literal[
        "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
    ]
    execution_requirements_path: str
    execution_requirements_sha256: Literal[
        "30799246e6fa8d91246a5277e613ed97f840a164331f1f04a3f17fd84aad20cf"
    ]
    g10_freeze_path: str
    functional_trajectory_count: Literal[162]
    runtime_trajectory_count: Literal[180]
    primary_runtime_endpoint: Literal["warm-eligible-newly-computed-prefill-tokens-v1"]
    primary_runtime_telemetry_field: Literal["newly_computed_prefill_tokens"]
    ledger_regeneration_permitted: Literal[False]


class ExecutionIdentityBridge(FrozenModel):
    planning_execution_manifest_sha256: Literal[
        "4bd822375390cf413718553313903679e78b650dfa798955e2f7c61ebd8b8678"
    ]
    ledger_planning_manifest_identity_rewritten: Literal[False]
    planning_manifest_hash_is_final_execution_manifest_hash: Literal[False]
    final_execution_manifest_hash_required_in_every_runtime_trace: Literal[True]
    final_comparison_eligibility_uses_final_execution_manifest_hash: Literal[True]
    versioned_planning_to_execution_compatibility_rule_required: Literal[True]


class RouteRealization(FrozenModel):
    route_source: Literal["planned_run.route_schedule_id"]
    derive_route_from_condition_permitted: Literal[False]
    turn_local_route_schedule_id: Literal["turn-local-worker1-worker2-v1"]
    turn_local_four_turn_realization: tuple[
        Literal["worker_1"],
        Literal["worker_2"],
        Literal["worker_1"],
        Literal["worker_2"],
    ]
    affinity_route_schedule_id: Literal["affinity-worker1-worker1-v1"]
    affinity_four_turn_realization: tuple[
        Literal["worker_1"],
        Literal["worker_1"],
        Literal["worker_1"],
        Literal["worker_1"],
    ]
    cache_residency_identity_fields: tuple[
        Literal["worker_id"],
        Literal["worker_generation"],
        Literal["runtime_model_fingerprint"],
    ]
    worker_generation_drift_invalidates_warm_eligibility: Literal[True]


class SessionIdentity(FrozenModel):
    derivation_id: Literal["sha256-domain-separated-run-id-v1"]
    canonical_input_template: Literal["auragateway-final-342-session-v1|{run_id}"]
    same_session_hash_required_across_four_turns: Literal[True]
    raw_session_identifier_retained: Literal[False]


class WarmEligibility(FrozenModel):
    ttl_assumption_seconds: Literal[300]
    ttl_source: Literal["benchmark-assumption-v1"]
    ttl_source_evidence_path: str
    ttl_is_provider_or_vllm_residency_guarantee: Literal[False]
    first_turn_classification: Literal["cold"]
    same_session_required: Literal[True]
    same_cache_residency_route_required: Literal[True]
    static_prefix_match_required: Literal[True]
    same_cache_namespace_required: Literal[True]
    inside_ttl_required: Literal[True]
    provider_failure_invalidates: Literal[True]
    session_reset_invalidates: Literal[True]
    benchmark_transition_invalidates: Literal[True]
    observed_cached_tokens_required_for_warm_eligibility: Literal[False]
    ambiguous_state_treatment: Literal["unavailable_or_ambiguous"]
    synthetic_pre_warm_requests_permitted: Literal[False]
    planning_prefix_hash_is_runtime_confirmation: Literal[False]
    runtime_prefix_confirmation_required: Literal[True]


class RetryAndAccountability(FrozenModel):
    policy_id: Literal["provider-request-policy-v1"]
    connection_timeout_seconds: Literal[10]
    first_output_timeout_seconds: Literal[45]
    total_request_timeout_seconds: Literal[120]
    maximum_retries_after_initial_attempt: Literal[1]
    retry_backoff_seconds: Literal[2]
    retry_jitter_permitted: Literal[False]
    retry_requires_no_response_or_definite_failure: Literal[True]
    blind_retry_after_ambiguous_response_permitted: Literal[False]
    every_attempt_retained: Literal[True]
    maximum_request_attempt_count: Literal[2736]
    extra_final_authority_canary_requests_permitted: Literal[False]
    extra_final_authority_worker_qualification_requests_permitted: Literal[False]
    v2_pretreatment_requests_carried_into_final_execution: Literal[False]


class OutputAndState(FrozenModel):
    finish_reason_stop_required: Literal[True]
    schema_admission_required_before_state_mutation: Literal[True]
    exact_accepted_tokenizer_check_required_before_request: Literal[True]
    prospective_next_prompt_budget_check_required_before_state_mutation: Literal[True]
    failed_or_unadmitted_output_mutates_history: Literal[False]
    http_completion_accounted_before_later_admission_or_telemetry_failure: Literal[True]


class EvidenceChannels(FrozenModel):
    public_raw_prompts_permitted: Literal[False]
    public_raw_outputs_permitted: Literal[False]
    public_raw_provider_payloads_permitted: Literal[False]
    protected_measured_review_export_required: Literal[True]
    protected_export_root: Literal[".local/auragateway/final-342-protected-review-v1"]
    protected_export_must_remain_git_ignored: Literal[True]
    protected_export_uses_opaque_review_ids: Literal[True]
    public_evidence_binds_protected_export_by_metadata_or_digest_only: Literal[True]
    retention_and_deletion_rule_required_before_execution_manifest_freeze: Literal[True]
    primary_rubric_review_fraction: Literal["1"]
    independent_double_review_fraction: Literal["0.25"]
    double_review_seed: Literal[20260712]
    reviewers_blinded_to_condition_route_cost_latency_and_cache: Literal[True]


class FailureAndTerminalization(FrozenModel):
    first_causal_failure_preserved_separately: Literal[True]
    secondary_failure_may_mask_primary: Literal[False]
    teardown_failure_recorded_separately: Literal[True]
    cleanup_failure_recorded_separately: Literal[True]
    evidence_packaging_failure_recorded_separately: Literal[True]
    authorization_terminalization_failure_recorded_separately: Literal[True]
    authority_terminalizable_without_governed_evidence_zip: Literal[True]


class TransactionWrapper(FrozenModel):
    transaction_bound_execution_artifact_required: Literal[True]
    authorization_specific_kaggle_inputs_permitted: Literal[False]
    authorization_producer_notebooks_permitted: Literal[False]
    manual_confirmation_json_permitted: Literal[False]
    whole_notebook_sha256_is_semantic_execution_identity: Literal[False]
    runtime_payload_identity_bound: Literal[True]
    real_module_graph_structural_rehearsal_required: Literal[True]
    repository_pythonpath_dependency_permitted_in_rehearsal: Literal[False]
    production_module_graph_clobber_guard_may_be_weakened_for_tests: Literal[False]


class AuthorizationBoundary(FrozenModel):
    runner_implementation_is_authority: Literal[False]
    execution_manifest_freeze_is_authority: Literal[False]
    issuer_capability_is_live_issuance: Literal[False]
    single_use_is_governance_invariant: Literal[True]
    runtime_anti_replay_established: Literal[False]
    multiple_observed_executions_for_one_transaction_invalidate_acceptance: Literal[True]
    old_authorization_reusable_true_semantics_permitted_in_successor: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]


class PreflightReconciliation(FrozenModel):
    blind_unresolved_asset_removal_permitted: Literal[False]
    reconcile_each_old_blocker_to_current_evidence_or_keep_unresolved: Literal[True]
    required_reconciliation_families: tuple[str, ...]


class SafetyState(FrozenModel):
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    execution_manifest_frozen: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class ArchitectureRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    architecture_id: Literal["auragateway-final-342-runtime-requalification-architecture-v1"]
    status: Literal["PROPOSED_FOR_G11_0_ARCHITECTURE_ACCEPTANCE"]
    base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    decision: Literal["FINAL_342_TRANSACTION_BOUND_RUNTIME_REQUALIFICATION_V1"]
    north_star: NorthStar
    frozen_subject: FrozenSubject
    execution_identity_bridge: ExecutionIdentityBridge
    route_realization: RouteRealization
    session_identity: SessionIdentity
    warm_eligibility: WarmEligibility
    retry_and_accountability: RetryAndAccountability
    output_and_state: OutputAndState
    evidence_channels: EvidenceChannels
    failure_and_terminalization: FailureAndTerminalization
    transaction_wrapper: TransactionWrapper
    authorization_boundary: AuthorizationBoundary
    preflight_reconciliation: PreflightReconciliation
    implementation_sequence: tuple[str, ...]
    safety_state: SafetyState
    next_gate: Literal["IMPLEMENT_FINAL_342_NON_AUTHORIZING_RUNTIME_CORE_V1"]

    @model_validator(mode="after")
    def validate_architecture_boundary(self) -> Self:
        if self.base_main_commit != EXPECTED_BASE_MAIN:
            raise ValueError("G11.0 architecture base main drifted")
        if len(set(self.preflight_reconciliation.required_reconciliation_families)) != len(
            self.preflight_reconciliation.required_reconciliation_families
        ):
            raise ValueError("preflight reconciliation families must be unique")
        if len(self.implementation_sequence) != 7:
            raise ValueError("G11.0 implementation sequence must contain seven gates")
        return self


def _read_bytes(repo_root: Path, relative: str) -> bytes:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise ArchitectureError(
            "FINAL_342_ARCH_SOURCE_MISSING",
            f"required source is missing or symlinked: {relative}",
        )
    return path.read_bytes()


def _read_json(repo_root: Path, relative: str) -> object:
    try:
        return json.loads(_read_bytes(repo_root, relative).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ArchitectureError(
            "FINAL_342_ARCH_INVALID_JSON",
            f"required source is not valid JSON: {relative}",
        ) from exc


def _sha256_path(repo_root: Path, relative: str) -> str:
    return hashlib.sha256(_read_bytes(repo_root, relative)).hexdigest()


def _require_sha(repo_root: Path, relative: str, expected: str) -> None:
    if _sha256_path(repo_root, relative) != expected:
        raise ArchitectureError(
            "FINAL_342_ARCH_IDENTITY_DRIFT",
            f"architecture-bound source identity drifted: {relative}",
        )


def _as_mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ArchitectureError(
            "FINAL_342_ARCH_SOURCE_SHAPE_INVALID",
            f"{name} must be a JSON object",
        )
    return value


def _validate_ledger(repo_root: Path, record: ArchitectureRecord) -> None:
    path = record.frozen_subject.planned_run_ledger_path
    _require_sha(repo_root, path, EXPECTED_LEDGER_SHA256)
    ledger = _as_mapping(_read_json(repo_root, path), "planned run ledger")

    expected_scalars = {
        "functional_trajectory_count": 162,
        "runtime_trajectory_count": 180,
        "total_trajectory_count": 342,
        "total_turn_count": 1368,
        "maximum_request_attempt_count": 2736,
        "every_attempt_retained": True,
        "hidden_retry_permitted": False,
        "replacement_case_permitted": False,
        "execution_enabled": False,
        "execution_manifest_planning_identity_sha256": EXPECTED_PLANNING_MANIFEST_SHA256,
    }
    for key, expected in expected_scalars.items():
        if ledger.get(key) != expected:
            raise ArchitectureError(
                "FINAL_342_ARCH_LEDGER_DRIFT",
                f"planned ledger field drifted: {key}",
            )

    runs = ledger.get("runs")
    if not isinstance(runs, list) or len(runs) != 342:
        raise ArchitectureError(
            "FINAL_342_ARCH_LEDGER_RUNS_INVALID",
            "planned ledger must contain exactly 342 runs",
        )

    permitted_routes = {
        record.route_realization.turn_local_route_schedule_id,
        record.route_realization.affinity_route_schedule_id,
    }
    for expected_index, raw in enumerate(runs):
        run = _as_mapping(raw, "planned run")
        if run.get("planned_order_index") != expected_index:
            raise ArchitectureError(
                "FINAL_342_ARCH_LEDGER_ORDER_DRIFT",
                "planned ledger order indexes must remain exact",
            )
        if run.get("execution_manifest_sha256") != EXPECTED_PLANNING_MANIFEST_SHA256:
            raise ArchitectureError(
                "FINAL_342_ARCH_PLANNING_MANIFEST_DRIFT",
                "planned-run planning-manifest identity drifted",
            )
        if run.get("turn_count") != 4 or run.get("maximum_request_attempts") != 8:
            raise ArchitectureError(
                "FINAL_342_ARCH_LEDGER_BUDGET_DRIFT",
                "planned-run turn or attempt budget drifted",
            )
        if run.get("route_schedule_id") not in permitted_routes:
            raise ArchitectureError(
                "FINAL_342_ARCH_ROUTE_SCHEDULE_DRIFT",
                "planned-run route schedule is outside the frozen set",
            )


def _validate_g10(repo_root: Path, record: ArchitectureRecord) -> None:
    payload = _as_mapping(
        _read_json(repo_root, record.frozen_subject.g10_freeze_path),
        "G10 freeze",
    )
    expected = {
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
        "total_scheduled_trajectory_count": 342,
        "total_scheduled_turn_count": 1368,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ArchitectureError(
                "FINAL_342_ARCH_G10_DRIFT",
                f"G10 field drifted: {key}",
            )

    endpoint = _as_mapping(payload.get("primary_runtime_endpoint"), "G10 endpoint")
    if endpoint.get("metric_id") != record.frozen_subject.primary_runtime_endpoint:
        raise ArchitectureError(
            "FINAL_342_ARCH_G10_ENDPOINT_DRIFT",
            "G10 primary endpoint ID drifted",
        )
    if endpoint.get("telemetry_field") != record.frozen_subject.primary_runtime_telemetry_field:
        raise ArchitectureError(
            "FINAL_342_ARCH_G10_TELEMETRY_DRIFT",
            "G10 telemetry field drifted",
        )
    if endpoint.get("warm_eligible_turn_indices") != [2, 3, 4]:
        raise ArchitectureError(
            "FINAL_342_ARCH_G10_WARM_TURNS_DRIFT",
            "G10 warm-eligible turn indexes drifted",
        )


def _validate_condition_fingerprints(repo_root: Path, record: ArchitectureRecord) -> None:
    path = record.frozen_subject.condition_fingerprints_path
    _require_sha(repo_root, path, EXPECTED_CONDITION_FINGERPRINTS_SHA256)
    payload = _as_mapping(_read_json(repo_root, path), "condition fingerprints")
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 3:
        raise ArchitectureError(
            "FINAL_342_ARCH_CONDITION_FINGERPRINTS_INVALID",
            "condition fingerprints must contain exactly three records",
        )
    for raw in records:
        item = _as_mapping(raw, "condition fingerprint")
        condition_payload = _as_mapping(item.get("payload"), "condition payload")
        if condition_payload.get("prefix_token_hash_status") != (
            "planning_identity_requires_runtime_confirmation"
        ):
            raise ArchitectureError(
                "FINAL_342_ARCH_PREFIX_CONFIRMATION_DRIFT",
                "planning prefix identity must require runtime confirmation",
            )


def _validate_ttl_lineage(repo_root: Path, record: ArchitectureRecord) -> None:
    payload = _as_mapping(
        _read_json(repo_root, record.warm_eligibility.ttl_source_evidence_path),
        "historical TTL source manifest",
    )
    assets = _as_mapping(payload.get("assets"), "historical TTL source assets")
    if assets.get("cache_ttl_assumption_seconds") != record.warm_eligibility.ttl_assumption_seconds:
        raise ArchitectureError(
            "FINAL_342_ARCH_TTL_SOURCE_DRIFT",
            "historical benchmark TTL assumption drifted",
        )
    if assets.get("cache_ttl_source") != record.warm_eligibility.ttl_source:
        raise ArchitectureError(
            "FINAL_342_ARCH_TTL_SOURCE_DRIFT",
            "historical benchmark TTL source label drifted",
        )


def _validate_lineage(repo_root: Path) -> None:
    transaction_adr = _read_bytes(
        repo_root,
        "docs/adr/2026-08-11-local-abc-transaction-bound-execution-authorization-architecture-v1.md",
    ).decode("utf-8")
    if "TRANSACTION_BOUND_EXECUTION_ARTIFACT" not in transaction_adr:
        raise ArchitectureError(
            "FINAL_342_ARCH_TRANSACTION_LINEAGE_DRIFT",
            "transaction-bound architecture marker was not found",
        )

    old_issuer = _read_bytes(
        repo_root,
        "src/auragateway/local_abc/measured_abc_execution_authorization_v1.py",
    ).decode("utf-8")
    if "authorization_reusable: Literal[True] = True" not in old_issuer:
        raise ArchitectureError(
            "FINAL_342_ARCH_OLD_ISSUER_PREMISE_DRIFT",
            "historical reusable-authority premise was not found",
        )

    v2_runtime = _read_bytes(
        repo_root,
        "src/auragateway/local_abc/measured_abc_variance_pilot_transaction_bound_runtime_v1.py",
    ).decode("utf-8")
    if "newly_computed_prefill_tokens" not in v2_runtime:
        raise ArchitectureError(
            "FINAL_342_ARCH_TELEMETRY_LINEAGE_DRIFT",
            "V2 newly-computed-prefill telemetry lineage was not found",
        )

    gitignore = _read_bytes(repo_root, ".gitignore").decode("utf-8")
    if ".local/" not in gitignore:
        raise ArchitectureError(
            "FINAL_342_ARCH_PROTECTED_EXPORT_NOT_IGNORED",
            "protected review export is not covered by .gitignore",
        )


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record = ArchitectureRecord.model_validate(_read_json(root, RECORD_PATH.as_posix()))

    _require_sha(
        root,
        record.frozen_subject.benchmark_constitution_path,
        EXPECTED_CONSTITUTION_SHA256,
    )
    _require_sha(
        root,
        record.frozen_subject.execution_requirements_path,
        EXPECTED_REQUIREMENTS_SHA256,
    )
    _validate_ledger(root, record)
    _validate_g10(root, record)
    _validate_condition_fingerprints(root, record)
    _validate_ttl_lineage(root, record)
    _validate_lineage(root)

    return {
        "status": "FINAL_342_RUNTIME_REQUALIFICATION_ARCHITECTURE_V1_VALID",
        "decision": record.decision,
        "planned_trajectories": record.north_star.planned_trajectories,
        "planned_turns": record.north_star.planned_turns,
        "maximum_request_attempts": record.north_star.maximum_request_attempts,
        "planning_manifest_identity_preserved": (
            not record.execution_identity_bridge.ledger_planning_manifest_identity_rewritten
        ),
        "runtime_prefix_confirmation_required": (
            record.warm_eligibility.runtime_prefix_confirmation_required
        ),
        "ttl_assumption_seconds": record.warm_eligibility.ttl_assumption_seconds,
        "protected_measured_review_export_required": (
            record.evidence_channels.protected_measured_review_export_required
        ),
        "execution_manifest_frozen": record.safety_state.execution_manifest_frozen,
        "final_measured_abc_execution_authorized": (
            record.safety_state.final_measured_abc_execution_authorized
        ),
        "new_execution_authorized": record.safety_state.new_execution_authorized,
        "effect_claims_permitted": record.safety_state.effect_claims_permitted,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate(Path(args.repo_root))
    except (
        ArchitectureError,
        UnicodeDecodeError,
        ValidationError,
        OSError,
    ) as error:
        if isinstance(error, ArchitectureError):
            code = error.error_code
            message = error.safe_message
        else:
            code = "FINAL_342_ARCH_VALIDATION_FAILED"
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
