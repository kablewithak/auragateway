"""Deterministic benchmark planning and measured-execution preflight controls."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from pydantic import BaseModel

from auragateway.contracts.benchmark_preflight import (
    BenchmarkBudgetEnvelope,
    BenchmarkExecutionManifest,
    BenchmarkPlanRequest,
    BenchmarkPreflightReport,
    BenchmarkWorkload,
    EvidenceVaultContract,
    ExecutionManifestStatus,
    PlannedBenchmarkRun,
    PlannedRunLedger,
    PreflightCheckName,
    PreflightCheckResult,
    PreflightCheckStatus,
    PreflightFailureCode,
    ProviderReadinessSnapshot,
    ProviderReadinessState,
)
from auragateway.contracts.evidence_bundle import BenchmarkCondition

_FUNCTIONAL_SCHEDULE: tuple[tuple[BenchmarkCondition, ...], ...] = (
    (BenchmarkCondition.A, BenchmarkCondition.B, BenchmarkCondition.C),
    (BenchmarkCondition.B, BenchmarkCondition.C, BenchmarkCondition.A),
    (BenchmarkCondition.C, BenchmarkCondition.A, BenchmarkCondition.B),
)
_RUNTIME_SCHEDULE: tuple[tuple[BenchmarkCondition, ...], ...] = (
    (BenchmarkCondition.A, BenchmarkCondition.B, BenchmarkCondition.C),
    (BenchmarkCondition.B, BenchmarkCondition.C, BenchmarkCondition.A),
    (BenchmarkCondition.C, BenchmarkCondition.A, BenchmarkCondition.B),
    (BenchmarkCondition.A, BenchmarkCondition.C, BenchmarkCondition.B),
    (BenchmarkCondition.C, BenchmarkCondition.B, BenchmarkCondition.A),
    (BenchmarkCondition.B, BenchmarkCondition.A, BenchmarkCondition.C),
    (BenchmarkCondition.A, BenchmarkCondition.B, BenchmarkCondition.C),
    (BenchmarkCondition.B, BenchmarkCondition.C, BenchmarkCondition.A),
    (BenchmarkCondition.C, BenchmarkCondition.A, BenchmarkCondition.B),
    (BenchmarkCondition.C, BenchmarkCondition.B, BenchmarkCondition.A),
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_model_sha256(model: BaseModel, *, exclude: set[str] | None = None) -> str:
    """Hash a Pydantic model using stable JSON ordering."""

    payload = model.model_dump(mode="json", exclude=exclude or set(), exclude_none=True)
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(normalized.encode("utf-8"))


def execution_manifest_sha256(manifest: BenchmarkExecutionManifest) -> str:
    """Calculate the canonical manifest digest without the self-hash field."""

    payload = manifest.model_dump(mode="json", exclude_none=True)
    identity = dict(payload["identity"])
    identity.pop("execution_manifest_sha256", None)
    payload["identity"] = identity
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(normalized.encode("utf-8"))


def _run_id(
    workload: BenchmarkWorkload,
    episode_id: str,
    replication_number: int,
    condition: BenchmarkCondition,
) -> str:
    episode_slug = episode_id.replace("_", "-")
    return (
        f"run-{workload.value.replace('_', '-')}-{episode_slug}-"
        f"r{replication_number:02d}-{condition.value.replace('_', '-')}"
    )


def _pair_id(
    workload: BenchmarkWorkload,
    episode_id: str,
    replication_number: int,
) -> str:
    return f"pair-{workload.value.replace('_', '-')}-{episode_id}-r{replication_number:02d}"


def _namespace_id(
    workload: BenchmarkWorkload,
    episode_id: str,
    replication_number: int,
    condition: BenchmarkCondition,
) -> str:
    return (
        f"ns-{workload.value.replace('_', '-')}-{episode_id}-"
        f"r{replication_number:02d}-{condition.value.replace('_', '-')}"
    )


def _expand_workload(
    *,
    start_index: int,
    workload: BenchmarkWorkload,
    episode_ids: tuple[str, ...],
    schedule: tuple[tuple[BenchmarkCondition, ...], ...],
    turns_per_episode: int,
    maximum_retries_after_initial_attempt: int,
) -> tuple[PlannedBenchmarkRun, ...]:
    runs: list[PlannedBenchmarkRun] = []
    schedule_index = start_index
    attempts_per_turn = 1 + maximum_retries_after_initial_attempt
    for episode_id in episode_ids:
        for replication_number, condition_order in enumerate(schedule, start=1):
            pair_id = _pair_id(workload, episode_id, replication_number)
            for order_index, condition in enumerate(condition_order):
                runs.append(
                    PlannedBenchmarkRun(
                        schedule_index=schedule_index,
                        run_id=_run_id(
                            workload,
                            episode_id,
                            replication_number,
                            condition,
                        ),
                        comparison_pair_id=pair_id,
                        workload=workload,
                        episode_id=episode_id,
                        replication_id=f"replication-{replication_number:02d}",
                        condition_id=condition,
                        condition_order_index=order_index,
                        cache_namespace_id=_namespace_id(
                            workload,
                            episode_id,
                            replication_number,
                            condition,
                        ),
                        turn_count=turns_per_episode,
                        maximum_request_attempt_count=(turns_per_episode * attempts_per_turn),
                    )
                )
                schedule_index += 1
    return tuple(runs)


def build_run_ledger(request: BenchmarkPlanRequest) -> PlannedRunLedger:
    """Expand the frozen functional and runtime counterbalanced matrices."""

    functional = _expand_workload(
        start_index=0,
        workload=BenchmarkWorkload.FUNCTIONAL,
        episode_ids=request.functional_episode_ids,
        schedule=_FUNCTIONAL_SCHEDULE,
        turns_per_episode=request.turns_per_episode,
        maximum_retries_after_initial_attempt=request.maximum_retries_after_initial_attempt,
    )
    runtime = _expand_workload(
        start_index=len(functional),
        workload=BenchmarkWorkload.RUNTIME,
        episode_ids=request.runtime_episode_ids,
        schedule=_RUNTIME_SCHEDULE,
        turns_per_episode=request.turns_per_episode,
        maximum_retries_after_initial_attempt=request.maximum_retries_after_initial_attempt,
    )
    runs = functional + runtime
    return PlannedRunLedger(
        plan_id=request.plan_id,
        functional_run_order_schedule_id="functional-counterbalance-v1",
        runtime_run_order_schedule_id="runtime-counterbalance-v1",
        runs=runs,
        functional_trajectory_count=len(functional),
        runtime_trajectory_count=len(runtime),
        total_trajectory_count=len(runs),
        total_turn_count=sum(item.turn_count for item in runs),
        maximum_request_attempt_count=sum(item.maximum_request_attempt_count for item in runs),
    )


def _check(
    check_name: PreflightCheckName,
    passed: bool,
    failure_code: PreflightFailureCode,
    *details: str,
) -> PreflightCheckResult:
    return PreflightCheckResult(
        check_name=check_name,
        status=PreflightCheckStatus.PASSED if passed else PreflightCheckStatus.FAILED,
        failure_code=None if passed else failure_code,
        details=tuple(details),
    )


def _manifest_hash_check(manifest: BenchmarkExecutionManifest) -> PreflightCheckResult:
    identity = manifest.identity
    if identity.execution_manifest_status is ExecutionManifestStatus.DRAFT:
        return PreflightCheckResult(
            check_name=PreflightCheckName.EXECUTION_MANIFEST_HASH_VALID,
            status=PreflightCheckStatus.NOT_APPLICABLE,
            details=("draft manifests do not carry a frozen self-hash",),
        )
    expected = execution_manifest_sha256(manifest)
    return _check(
        PreflightCheckName.EXECUTION_MANIFEST_HASH_VALID,
        identity.execution_manifest_sha256 == expected,
        PreflightFailureCode.EXECUTION_MANIFEST_HASH_MISMATCH,
        "frozen execution-manifest digest must match canonical serialization",
    )


def _functional_complete(ledger: PlannedRunLedger) -> bool:
    runs = tuple(item for item in ledger.runs if item.workload is BenchmarkWorkload.FUNCTIONAL)
    pair_conditions: dict[str, set[BenchmarkCondition]] = {}
    for item in runs:
        pair_conditions.setdefault(item.comparison_pair_id, set()).add(item.condition_id)
    return (
        len(runs) == 162
        and len(pair_conditions) == 54
        and all(values == set(BenchmarkCondition) for values in pair_conditions.values())
    )


def _runtime_complete(ledger: PlannedRunLedger) -> bool:
    runs = tuple(item for item in ledger.runs if item.workload is BenchmarkWorkload.RUNTIME)
    pair_conditions: dict[str, set[BenchmarkCondition]] = {}
    for item in runs:
        pair_conditions.setdefault(item.comparison_pair_id, set()).add(item.condition_id)
    return (
        len(runs) == 180
        and len(pair_conditions) == 60
        and all(values == set(BenchmarkCondition) for values in pair_conditions.values())
    )


def evaluate_preflight(
    *,
    manifest: BenchmarkExecutionManifest,
    provider: ProviderReadinessSnapshot,
    budget: BenchmarkBudgetEnvelope,
    vault: EvidenceVaultContract,
    ledger: PlannedRunLedger,
) -> BenchmarkPreflightReport:
    """Evaluate planning readiness and measured-execution blockers."""

    manifest_valid = all(
        (
            bool(manifest.identity.execution_manifest_version),
            bool(manifest.assets.provider_model_alias),
            bool(manifest.assets.functional_benchmark_manifest_sha256),
            bool(manifest.assets.runtime_microbenchmark_manifest_sha256),
        )
    )
    unresolved_assets = tuple(
        name
        for name in (
            "pricing_schedule_version",
            "pricing_source_date",
            "currency",
            "negative_control_manifest_sha256",
            "fault_injection_fixture_sha256",
            "privacy_verification_report_sha256",
            "cross_condition_isolation_test_sha256",
        )
        if getattr(manifest.assets, name) is None
    )
    manifest_assets_resolved = not unresolved_assets
    manifest_frozen = manifest.identity.execution_manifest_status is ExecutionManifestStatus.FROZEN
    provider_config_ready = all(
        (
            provider.readiness_state is ProviderReadinessState.CONFIGURATION_READY,
            provider.credentials_configured,
            provider.adapter_calibration_passed,
            provider.telemetry_mapping_passed,
            provider.provider_error_taxonomy_passed,
        )
    )
    live_probe_passed = provider.live_probe_performed and provider.live_probe_passed
    request_budget_sufficient = all(
        (
            budget.maximum_trajectory_count >= ledger.total_trajectory_count,
            budget.maximum_turn_count >= ledger.total_turn_count,
            budget.maximum_request_attempt_count >= ledger.maximum_request_attempt_count,
        )
    )
    cost_budget_declared = (
        budget.approved_cost_budget_minor_units is not None
        and budget.estimated_upper_bound_minor_units is not None
        and budget.estimated_upper_bound_minor_units <= budget.approved_cost_budget_minor_units
    )
    functional_complete = _functional_complete(ledger)
    runtime_complete = _runtime_complete(ledger)
    vault_valid = all(
        (
            vault.append_only_finalized_bundles,
            not vault.protected_review_exports_public,
            not vault.raw_provider_payloads_public,
            not vault.raw_prompts_public,
            not vault.secrets_public,
        )
    )
    execution_disabled = not manifest.identity.execution_enabled and not ledger.execution_enabled

    checks = (
        _check(
            PreflightCheckName.EXECUTION_MANIFEST_VALID,
            manifest_valid,
            PreflightFailureCode.EXECUTION_MANIFEST_INVALID,
            "execution manifest must contain all typed identity and asset fields",
        ),
        _check(
            PreflightCheckName.EXECUTION_MANIFEST_ASSETS_RESOLVED,
            manifest_assets_resolved,
            PreflightFailureCode.EXECUTION_MANIFEST_ASSETS_UNRESOLVED,
            *(unresolved_assets or ("all freeze-required assets are resolved",)),
        ),
        _check(
            PreflightCheckName.EXECUTION_MANIFEST_FROZEN,
            manifest_frozen,
            PreflightFailureCode.EXECUTION_MANIFEST_NOT_FROZEN,
            "measured execution requires the canonical manifest to be frozen",
        ),
        _manifest_hash_check(manifest),
        _check(
            PreflightCheckName.PROVIDER_CONFIGURATION_READY,
            provider_config_ready,
            PreflightFailureCode.PROVIDER_CONFIGURATION_NOT_READY,
            "provider credentials are represented only as a configured boolean",
        ),
        _check(
            PreflightCheckName.PROVIDER_LIVE_PROBE_PASSED,
            live_probe_passed,
            PreflightFailureCode.PROVIDER_LIVE_PROBE_NOT_PASSED,
            "a bounded live dry-run probe is required before measured execution",
        ),
        _check(
            PreflightCheckName.REQUEST_BUDGET_SUFFICIENT,
            request_budget_sufficient,
            PreflightFailureCode.REQUEST_BUDGET_INSUFFICIENT,
            "request budget must cover 342 trajectories, 1368 turns, and 2736 attempts",
        ),
        _check(
            PreflightCheckName.COST_BUDGET_DECLARED,
            cost_budget_declared,
            PreflightFailureCode.COST_BUDGET_NOT_DECLARED,
            "a versioned approved cost ceiling is required before provider execution",
        ),
        _check(
            PreflightCheckName.FUNCTIONAL_MATRIX_COMPLETE,
            functional_complete,
            PreflightFailureCode.FUNCTIONAL_PLAN_INCOMPLETE,
            "functional plan requires 18 episodes, 3 replications, and A/B/C",
        ),
        _check(
            PreflightCheckName.RUNTIME_MATRIX_COMPLETE,
            runtime_complete,
            PreflightFailureCode.RUNTIME_PLAN_INCOMPLETE,
            "runtime plan requires 6 episodes, 10 replications, and A/B/C",
        ),
        _check(
            PreflightCheckName.EVIDENCE_VAULT_CONTRACT_VALID,
            vault_valid,
            PreflightFailureCode.EVIDENCE_VAULT_CONTRACT_INVALID,
            "public and protected evidence roots must remain separated",
        ),
        _check(
            PreflightCheckName.EXECUTION_DISABLED_BY_DEFAULT,
            execution_disabled,
            PreflightFailureCode.EXECUTION_ENABLEMENT_UNSAFE,
            "planning commands must not execute provider calls",
        ),
    )
    failure_codes = tuple(
        dict.fromkeys(item.failure_code for item in checks if item.failure_code is not None)
    )
    planning_checks = {
        PreflightCheckName.EXECUTION_MANIFEST_VALID,
        PreflightCheckName.REQUEST_BUDGET_SUFFICIENT,
        PreflightCheckName.FUNCTIONAL_MATRIX_COMPLETE,
        PreflightCheckName.RUNTIME_MATRIX_COMPLETE,
        PreflightCheckName.EVIDENCE_VAULT_CONTRACT_VALID,
        PreflightCheckName.EXECUTION_DISABLED_BY_DEFAULT,
    }
    planning_ready = all(
        item.status is PreflightCheckStatus.PASSED
        for item in checks
        if item.check_name in planning_checks
    )
    measured_execution_ready = (
        all(
            item.status in {PreflightCheckStatus.PASSED, PreflightCheckStatus.NOT_APPLICABLE}
            for item in checks
        )
        and manifest.identity.execution_enabled
    )
    return BenchmarkPreflightReport(
        plan_id=ledger.plan_id,
        execution_manifest_id=manifest.identity.execution_manifest_id,
        checks=checks,
        failure_codes=failure_codes,
        functional_trajectory_count=ledger.functional_trajectory_count,
        runtime_trajectory_count=ledger.runtime_trajectory_count,
        total_trajectory_count=ledger.total_trajectory_count,
        total_turn_count=ledger.total_turn_count,
        maximum_request_attempt_count=ledger.maximum_request_attempt_count,
        planning_ready=planning_ready,
        measured_execution_ready=measured_execution_ready,
        execution_enabled=manifest.identity.execution_enabled,
    )


def shuffled_runs(
    ledger: PlannedRunLedger,
    indexes: Iterable[int],
) -> tuple[PlannedBenchmarkRun, ...]:
    """Test helper exposing a controlled run-order projection."""

    return tuple(ledger.runs[index] for index in indexes)
