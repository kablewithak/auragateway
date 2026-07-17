"""Reconcile the stale Gate 9 draft with the hardened full A/B/C harness lineage."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

from auragateway.local_abc.contracts import ConditionId, LocalABCContract
from auragateway.local_abc.full_abc_execution_manifest_asset_inventory import (
    FullABCExecutionManifestAssetInventory,
    load_full_abc_execution_manifest_asset_inventory,
)
from auragateway.local_abc.full_abc_execution_manifest_draft_reconciliation_contracts import (
    _ACTION_SCHEMA_SHA256,
    _ASSET_INVENTORY_SHA256,
    _BENCHMARK_CONSTITUTION_SHA256,
    _CONDITION_FINGERPRINTS_PATH,
    _DEPENDENCY_LOCK_PATH,
    _DRAFT_PATH,
    _EXPECTED_TRACE_FIELDS,
    _FUNCTIONAL_SCHEDULE,
    _INPUT_PATH,
    _INTEGRATION_DESIGN_SHA256,
    _INTEGRATION_IMPLEMENTATION_SHA256,
    _LEDGER_PATH,
    _MANIFEST_PATH,
    _OUTPUT_ROOT,
    _PROMPT_POLICY_SHA256,
    _REPORT_PATH,
    _REQUIRED_DISTRIBUTIONS,
    _RESPONSE_SCHEMA_SHA256,
    _RUNTIME_SCHEDULE,
    _SOURCE_MERGE_COMMIT,
    FullABCConditionConfigurationFingerprint,
    FullABCConditionFingerprintManifest,
    FullABCConditionFingerprintPayload,
    FullABCDependencyLock,
    FullABCDependencyPackage,
    FullABCDependencyRole,
    FullABCReconciledExecutionManifestDraft,
    FullABCReconciledManifestAssets,
    FullABCReconciledManifestControls,
    FullABCReconciledManifestIdentity,
    FullABCReconciledPlannedRun,
    FullABCReconciledPlannedRunLedger,
    FullABCReconciliationCheck,
    FullABCReconciliationCheckName,
    FullABCReconciliationCheckStatus,
    FullABCReconciliationError,
    FullABCReconciliationErrorEnvelope,
    FullABCReconciliationInput,
    FullABCReconciliationManifest,
    FullABCReconciliationReport,
    FullABCReconciliationSpec,
    FullABCReconciliationSummary,
)
from auragateway.local_abc.full_abc_harness_integration import (
    build_full_abc_condition_runtime_adapters,
    load_full_abc_harness_integration_implementation_plan,
)
from auragateway.local_abc.full_abc_harness_integration_design import (
    FullABCHarnessIntegrationDesign,
    load_full_abc_harness_integration_design,
)

VersionResolver = Callable[[str], str]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(model: LocalABCContract) -> bytes:
    return model.canonical_json().encode("utf-8")


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FullABCReconciliationError(
            "RECONCILIATION_ASSET_NOT_FOUND",
            "A required reconciliation asset was not found.",
            str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise FullABCReconciliationError(
            "RECONCILIATION_ASSET_INVALID_JSON",
            "A required reconciliation asset is not valid JSON.",
            str(path),
        ) from exc


def _load_model(path: Path, model_type: type[LocalABCContract]) -> LocalABCContract:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise FullABCReconciliationError(
            "RECONCILIATION_ASSET_INVALID_ROOT",
            "A reconciliation asset must contain one JSON object.",
            str(path),
        )
    try:
        return model_type.model_validate(cast(dict[str, object], payload))
    except ValueError as exc:
        raise FullABCReconciliationError(
            "RECONCILIATION_ASSET_VALIDATION_FAILED",
            "A reconciliation asset failed typed validation.",
            str(path),
            (str(exc),),
        ) from exc


def load_full_abc_reconciliation_spec(path: Path) -> FullABCReconciliationSpec:
    """Load the static reconciliation source constitution."""

    return cast(FullABCReconciliationSpec, _load_model(path, FullABCReconciliationSpec))


def load_full_abc_dependency_lock(path: Path) -> FullABCDependencyLock:
    """Load one generated exact dependency lock."""

    return cast(FullABCDependencyLock, _load_model(path, FullABCDependencyLock))


def load_full_abc_condition_fingerprints(path: Path) -> FullABCConditionFingerprintManifest:
    """Load the generated A/B/C configuration fingerprint manifest."""

    return cast(
        FullABCConditionFingerprintManifest,
        _load_model(path, FullABCConditionFingerprintManifest),
    )


def _require_dict(payload: object, *, path: Path, field: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise FullABCReconciliationError(
            "RECONCILIATION_SOURCE_SHAPE_INVALID",
            "A required source object has an invalid shape.",
            str(path),
            (field,),
        )
    return cast(dict[str, object], payload)


def _require_string(mapping: dict[str, object], field: str, *, path: Path) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        raise FullABCReconciliationError(
            "RECONCILIATION_SOURCE_FIELD_INVALID",
            "A required source field is missing or invalid.",
            str(path),
            (field,),
        )
    return value


def _require_int(mapping: dict[str, object], field: str, *, path: Path) -> int:
    value = mapping.get(field)
    if not isinstance(value, int):
        raise FullABCReconciliationError(
            "RECONCILIATION_SOURCE_FIELD_INVALID",
            "A required integer source field is missing or invalid.",
            str(path),
            (field,),
        )
    return value


def _require_string_list(mapping: dict[str, object], field: str, *, path: Path) -> tuple[str, ...]:
    value = mapping.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise FullABCReconciliationError(
            "RECONCILIATION_SOURCE_FIELD_INVALID",
            "A required string-list source field is missing or invalid.",
            str(path),
            (field,),
        )
    return tuple(cast(list[str], value))


def _git_head(repo_root: Path) -> str:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", _SOURCE_MERGE_COMMIT, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    value = head.stdout.strip()
    if head.returncode != 0 or ancestry.returncode != 0:
        raise FullABCReconciliationError(
            "SOURCE_MERGE_COMMIT_MISMATCH",
            "Draft reconciliation requires PR 96 to be an ancestor of the current HEAD.",
            details=(
                f"required_ancestor={_SOURCE_MERGE_COMMIT}",
                f"actual_head={value or 'unavailable'}",
            ),
        )
    return _SOURCE_MERGE_COMMIT


def build_dependency_lock(
    *,
    repo_root: Path,
    version_resolver: VersionResolver = importlib.metadata.version,
    python_version: str | None = None,
    python_implementation: str | None = None,
) -> FullABCDependencyLock:
    """Capture exact direct, development, and build package versions locally."""

    pyproject_path = repo_root / "pyproject.toml"
    try:
        pyproject_bytes = pyproject_path.read_bytes()
        pyproject = tomllib.loads(pyproject_bytes.decode("utf-8"))
    except FileNotFoundError as exc:
        raise FullABCReconciliationError(
            "PYPROJECT_NOT_FOUND",
            "The project dependency declaration was not found.",
            str(pyproject_path),
        ) from exc
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise FullABCReconciliationError(
            "PYPROJECT_INVALID",
            "The project dependency declaration could not be parsed.",
            str(pyproject_path),
        ) from exc

    project = _require_dict(pyproject.get("project"), path=pyproject_path, field="project")
    project_name = _require_string(project, "name", path=pyproject_path)
    project_version = _require_string(project, "version", path=pyproject_path)
    if project_name != "auragateway":
        raise FullABCReconciliationError(
            "PROJECT_IDENTITY_MISMATCH",
            "The reconciliation project identity is not AuraGateway.",
            str(pyproject_path),
        )

    roles = {
        "groq": FullABCDependencyRole.RUNTIME,
        "pydantic": FullABCDependencyRole.RUNTIME,
        "mypy": FullABCDependencyRole.DEVELOPMENT,
        "pytest": FullABCDependencyRole.DEVELOPMENT,
        "ruff": FullABCDependencyRole.DEVELOPMENT,
        "setuptools": FullABCDependencyRole.BUILD,
    }
    packages: list[FullABCDependencyPackage] = []
    for distribution_name in _REQUIRED_DISTRIBUTIONS:
        try:
            resolved_version = version_resolver(distribution_name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise FullABCReconciliationError(
                "DEPENDENCY_DISTRIBUTION_NOT_FOUND",
                "A required AuraGateway distribution is not installed in the active environment.",
                details=(distribution_name,),
            ) from exc
        packages.append(
            FullABCDependencyPackage(
                distribution_name=distribution_name,
                version=resolved_version,
                role=roles[distribution_name],
            )
        )

    implementation = python_implementation or platform.python_implementation()
    if implementation != "CPython":
        raise FullABCReconciliationError(
            "PYTHON_IMPLEMENTATION_UNSUPPORTED",
            "AuraGateway reconciliation requires CPython.",
            details=(implementation,),
        )
    return FullABCDependencyLock(
        lock_id="auragateway-full-abc-dependency-lock-v2",
        source_merge_commit=_SOURCE_MERGE_COMMIT,
        pyproject_path="pyproject.toml",
        pyproject_sha256=_sha256_bytes(pyproject_bytes),
        project_name="auragateway",
        project_version=project_version,
        python_implementation="CPython",
        python_version=python_version or platform.python_version(),
        packages=cast(
            tuple[
                FullABCDependencyPackage,
                FullABCDependencyPackage,
                FullABCDependencyPackage,
                FullABCDependencyPackage,
                FullABCDependencyPackage,
                FullABCDependencyPackage,
            ],
            tuple(packages),
        ),
    )


def _validate_design_and_implementation(
    *,
    repo_root: Path,
    spec: FullABCReconciliationSpec,
) -> tuple[FullABCHarnessIntegrationDesign, str, FullABCExecutionManifestAssetInventory]:
    design = load_full_abc_harness_integration_design(repo_root / spec.integration_design_path)
    if design.fingerprint() != spec.expected_integration_design_sha256:
        raise FullABCReconciliationError(
            "INTEGRATION_DESIGN_MISMATCH",
            "The merged full A/B/C integration design identity changed.",
            spec.integration_design_path,
        )
    implementation = load_full_abc_harness_integration_implementation_plan(
        repo_root / spec.integration_implementation_path
    )
    if implementation.fingerprint() != spec.expected_integration_implementation_sha256:
        raise FullABCReconciliationError(
            "INTEGRATION_IMPLEMENTATION_MISMATCH",
            "The merged full A/B/C integration implementation identity changed.",
            spec.integration_implementation_path,
        )
    inventory = load_full_abc_execution_manifest_asset_inventory(
        repo_root / spec.asset_inventory_path
    )
    if inventory.fingerprint() != spec.expected_asset_inventory_sha256:
        raise FullABCReconciliationError(
            "ASSET_INVENTORY_MISMATCH",
            "The merged execution-manifest asset inventory identity changed.",
            spec.asset_inventory_path,
        )
    return design, implementation.fingerprint(), inventory


def build_condition_fingerprints(
    *,
    repo_root: Path,
    spec: FullABCReconciliationSpec,
    dependency_lock: FullABCDependencyLock,
    legacy_input: dict[str, object],
) -> FullABCConditionFingerprintManifest:
    """Derive exact per-condition fingerprints from the merged runtime adapters."""

    design, implementation_sha256, _inventory = _validate_design_and_implementation(
        repo_root=repo_root,
        spec=spec,
    )
    adapters = build_full_abc_condition_runtime_adapters(design)
    execution_manifest = _require_dict(
        legacy_input.get("execution_manifest"),
        path=repo_root / spec.legacy_input_path,
        field="execution_manifest",
    )
    assets = _require_dict(
        execution_manifest.get("assets"),
        path=repo_root / spec.legacy_input_path,
        field="execution_manifest.assets",
    )
    pricing = _require_dict(
        _load_json(repo_root / spec.pricing_schedule_path),
        path=repo_root / spec.pricing_schedule_path,
        field="pricing_schedule",
    )
    retrieval_sha = _require_string(
        assets,
        "retrieval_configuration_sha256",
        path=repo_root / spec.legacy_input_path,
    )
    provider_model_alias = _require_string(
        assets,
        "provider_model_alias",
        path=repo_root / spec.legacy_input_path,
    )
    provider_adapter_version = _require_string(
        assets,
        "provider_adapter_version",
        path=repo_root / spec.legacy_input_path,
    )
    pricing_schedule_id = _require_string(
        pricing,
        "pricing_schedule_id",
        path=repo_root / spec.pricing_schedule_path,
    )

    records: list[FullABCConditionConfigurationFingerprint] = []
    for adapter in adapters.adapters:
        payload = FullABCConditionFingerprintPayload(
            source_merge_commit=_SOURCE_MERGE_COMMIT,
            condition_id=adapter.condition_id,
            adapter_sha256=adapter.fingerprint(),
            dependency_lock_sha256=dependency_lock.fingerprint(),
            integration_design_sha256=_INTEGRATION_DESIGN_SHA256,
            integration_implementation_sha256=implementation_sha256,
            benchmark_constitution_sha256=_BENCHMARK_CONSTITUTION_SHA256,
            retrieval_configuration_sha256=retrieval_sha,
            prompt_policy_sha256=_PROMPT_POLICY_SHA256,
            response_schema_sha256=_RESPONSE_SCHEMA_SHA256,
            action_schema_sha256=_ACTION_SCHEMA_SHA256,
            provider_model_alias=provider_model_alias,
            provider_adapter_version=provider_adapter_version,
            pricing_schedule_id=pricing_schedule_id,
            benchmark_runner_version="2.0.0-local-abc-reconciled",
        )
        records.append(
            FullABCConditionConfigurationFingerprint(
                payload=payload,
                configuration_fingerprint=payload.fingerprint(),
            )
        )
    return FullABCConditionFingerprintManifest(
        manifest_id="auragateway-full-abc-condition-fingerprints-v2",
        source_merge_commit=_SOURCE_MERGE_COMMIT,
        dependency_lock_sha256=dependency_lock.fingerprint(),
        records=cast(
            tuple[
                FullABCConditionConfigurationFingerprint,
                FullABCConditionConfigurationFingerprint,
                FullABCConditionConfigurationFingerprint,
            ],
            tuple(records),
        ),
    )


def _condition_slug(condition_id: ConditionId) -> str:
    return {
        ConditionId.A: "condition-a",
        ConditionId.B: "condition-b",
        ConditionId.C: "condition-c",
    }[condition_id]


def _benchmark_condition(
    condition_id: ConditionId,
) -> Literal["condition_a", "condition_b", "condition_c"]:
    value = {
        ConditionId.A: "condition_a",
        ConditionId.B: "condition_b",
        ConditionId.C: "condition_c",
    }[condition_id]
    return cast(Literal["condition_a", "condition_b", "condition_c"], value)


def _expand_runs(
    *,
    start_index: int,
    workload: Literal["functional", "runtime_microbenchmark"],
    episode_ids: tuple[str, ...],
    schedule: tuple[tuple[ConditionId, ConditionId, ConditionId], ...],
    fingerprints: FullABCConditionFingerprintManifest,
) -> tuple[FullABCReconciledPlannedRun, ...]:
    runs: list[FullABCReconciledPlannedRun] = []
    schedule_index = start_index
    workload_slug = workload.replace("_microbenchmark", "")
    for episode_id in episode_ids:
        for replication_number, condition_order in enumerate(schedule, start=1):
            pair_id = f"pair-{workload_slug}-{episode_id}-r{replication_number:02d}"
            for order_index, condition_id in enumerate(condition_order):
                condition_slug = _condition_slug(condition_id)
                runs.append(
                    FullABCReconciledPlannedRun(
                        schedule_index=schedule_index,
                        run_id=(
                            f"run-{workload_slug}-{episode_id}-"
                            f"r{replication_number:02d}-{condition_slug}"
                        ),
                        comparison_pair_id=pair_id,
                        workload=workload,
                        episode_id=episode_id,
                        replication_id=f"replication-{replication_number:02d}",
                        condition_id=condition_id,
                        benchmark_condition_id=_benchmark_condition(condition_id),
                        condition_order_index=order_index,
                        cache_namespace_id=(
                            f"ns-{workload_slug}-{episode_id}-"
                            f"r{replication_number:02d}-{condition_slug}"
                        ),
                        configuration_fingerprint=fingerprints.fingerprint_for(condition_id),
                    )
                )
                schedule_index += 1
    return tuple(runs)


def build_reconciled_ledger(
    *,
    legacy_input: dict[str, object],
    source_path: Path,
    condition_fingerprints: FullABCConditionFingerprintManifest,
) -> FullABCReconciledPlannedRunLedger:
    """Regenerate all 342 planned trajectories against current condition identities."""

    plan_request = _require_dict(
        legacy_input.get("plan_request"),
        path=source_path,
        field="plan_request",
    )
    functional_ids = _require_string_list(
        plan_request,
        "functional_episode_ids",
        path=source_path,
    )
    runtime_ids = _require_string_list(
        plan_request,
        "runtime_episode_ids",
        path=source_path,
    )
    turns = _require_int(plan_request, "turns_per_episode", path=source_path)
    retries = _require_int(
        plan_request,
        "maximum_retries_after_initial_attempt",
        path=source_path,
    )
    if len(functional_ids) != 18 or len(runtime_ids) != 6 or turns != 4 or retries != 1:
        raise FullABCReconciliationError(
            "LEGACY_PLAN_REQUEST_DRIFTED",
            "The Gate 9 plan request no longer matches the frozen benchmark constitution.",
            str(source_path),
        )
    if tuple(sorted(functional_ids)) != functional_ids:
        raise FullABCReconciliationError(
            "FUNCTIONAL_EPISODE_ORDER_INVALID",
            "Functional episode IDs must remain sorted.",
            str(source_path),
        )
    if tuple(sorted(runtime_ids)) != runtime_ids or not set(runtime_ids) <= set(functional_ids):
        raise FullABCReconciliationError(
            "RUNTIME_EPISODE_SET_INVALID",
            "Runtime episodes must remain a sorted subset of functional episodes.",
            str(source_path),
        )

    functional = _expand_runs(
        start_index=0,
        workload="functional",
        episode_ids=functional_ids,
        schedule=_FUNCTIONAL_SCHEDULE,
        fingerprints=condition_fingerprints,
    )
    runtime = _expand_runs(
        start_index=len(functional),
        workload="runtime_microbenchmark",
        episode_ids=runtime_ids,
        schedule=_RUNTIME_SCHEDULE,
        fingerprints=condition_fingerprints,
    )
    return FullABCReconciledPlannedRunLedger(
        plan_id="benchmark-plan-auragateway-abc-v2",
        source_merge_commit=_SOURCE_MERGE_COMMIT,
        condition_fingerprints_sha256=condition_fingerprints.fingerprint(),
        functional_run_order_schedule_id="functional-counterbalance-v1",
        runtime_run_order_schedule_id="runtime-counterbalance-v1",
        runs=functional + runtime,
    )


def _canonical_mapping_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _file_sha256(repo_root: Path, relative_path: str) -> str:
    try:
        return _sha256_bytes((repo_root / relative_path).read_bytes())
    except FileNotFoundError as exc:
        raise FullABCReconciliationError(
            "RECONCILIATION_ASSET_NOT_FOUND",
            "A required reconciliation asset was not found.",
            relative_path,
        ) from exc


def _pricing_values(repo_root: Path, spec: FullABCReconciliationSpec) -> tuple[str, str, str]:
    path = repo_root / spec.pricing_schedule_path
    payload = _require_dict(_load_json(path), path=path, field="pricing_schedule")
    pricing_id = _require_string(payload, "pricing_schedule_id", path=path)
    source_date = _require_string(payload, "source_date", path=path)
    currency = _require_string(payload, "currency", path=path)
    if currency != "USD":
        raise FullABCReconciliationError(
            "PRICING_CURRENCY_MISMATCH",
            "The full A/B/C pricing schedule must remain USD.",
            str(path),
        )
    return pricing_id, source_date, currency


def build_reconciled_draft(
    *,
    repo_root: Path,
    spec: FullABCReconciliationSpec,
    legacy_input: dict[str, object],
    dependency_lock: FullABCDependencyLock,
    condition_fingerprints: FullABCConditionFingerprintManifest,
) -> FullABCReconciledExecutionManifestDraft:
    """Build the current non-executing v2 manifest draft."""

    legacy_manifest = _require_dict(
        legacy_input.get("execution_manifest"),
        path=repo_root / spec.legacy_input_path,
        field="execution_manifest",
    )
    legacy_assets = _require_dict(
        legacy_manifest.get("assets"),
        path=repo_root / spec.legacy_input_path,
        field="execution_manifest.assets",
    )
    legacy_controls = _require_dict(
        legacy_manifest.get("controls"),
        path=repo_root / spec.legacy_input_path,
        field="execution_manifest.controls",
    )
    pricing_id, pricing_date, currency = _pricing_values(repo_root, spec)

    identity = FullABCReconciledManifestIdentity(
        execution_manifest_id="execution-manifest-auragateway-v2-draft",
        execution_manifest_version="0.2.0-draft",
        execution_manifest_status="draft",
        benchmark_constitution_version="1.0.0",
        benchmark_constitution_sha256=_BENCHMARK_CONSTITUTION_SHA256,
        benchmark_runner_version="2.0.0-local-abc-reconciled",
        comparison_eligibility_contract_version="full-abc-comparison-preflight-v1",
        evidence_bundle_schema_version="1.0.0",
        git_commit_sha=_SOURCE_MERGE_COMMIT,
        python_version=dependency_lock.python_version,
        dependency_lock_sha256=dependency_lock.fingerprint(),
        integration_design_sha256=_INTEGRATION_DESIGN_SHA256,
        integration_implementation_sha256=_INTEGRATION_IMPLEMENTATION_SHA256,
        asset_inventory_sha256=_ASSET_INVENTORY_SHA256,
        condition_fingerprints_sha256=condition_fingerprints.fingerprint(),
    )
    assets = FullABCReconciledManifestAssets(
        legacy_execution_manifest_assets_sha256=_canonical_mapping_sha256(legacy_assets),
        corpus_manifest_sha256=_require_string(
            legacy_assets,
            "corpus_manifest_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        chunking_configuration_sha256=_require_string(
            legacy_assets,
            "chunking_configuration_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        retrieval_configuration_sha256=_require_string(
            legacy_assets,
            "retrieval_configuration_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        development_retrieval_manifest_sha256=_require_string(
            legacy_assets,
            "development_retrieval_manifest_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        held_out_retrieval_manifest_sha256=_require_string(
            legacy_assets,
            "held_out_retrieval_manifest_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        retrieval_scorecard_sha256=_require_string(
            legacy_assets,
            "retrieval_scorecard_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        prompt_policy_sha256=_PROMPT_POLICY_SHA256,
        response_schema_sha256=_RESPONSE_SCHEMA_SHA256,
        action_schema_sha256=_ACTION_SCHEMA_SHA256,
        diagnostic_episode_manifest_sha256=_require_string(
            legacy_assets,
            "diagnostic_episode_manifest_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        functional_benchmark_manifest_sha256=_require_string(
            legacy_assets,
            "functional_benchmark_manifest_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        runtime_microbenchmark_manifest_sha256=_require_string(
            legacy_assets,
            "runtime_microbenchmark_manifest_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        quality_rubric_sha256=_require_string(
            legacy_assets,
            "quality_rubric_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        review_sample_schedule_sha256=_require_string(
            legacy_assets,
            "review_sample_schedule_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        feedback_manifest_sha256=_file_sha256(repo_root, spec.gate7_manifest_path),
        comparison_eligibility_manifest_sha256=_file_sha256(
            repo_root,
            spec.gate8_manifest_path,
        ),
        telemetry_fixture_manifest_sha256=_require_string(
            legacy_assets,
            "telemetry_fixture_manifest_sha256",
            path=repo_root / spec.legacy_input_path,
        ),
        provider_model_alias=_require_string(
            legacy_assets,
            "provider_model_alias",
            path=repo_root / spec.legacy_input_path,
        ),
        provider_adapter_version=_require_string(
            legacy_assets,
            "provider_adapter_version",
            path=repo_root / spec.legacy_input_path,
        ),
        pricing_schedule_id=pricing_id,
        pricing_source_date=pricing_date,
        currency=cast(Literal["USD"], currency),
        pricing_schedule_sha256=_file_sha256(repo_root, spec.pricing_schedule_path),
        negative_control_manifest_sha256=_file_sha256(
            repo_root,
            spec.negative_controls_path,
        ),
        fault_injection_fixture_sha256=_file_sha256(repo_root, spec.fault_fixtures_path),
        privacy_verification_report_sha256=_file_sha256(
            repo_root,
            spec.privacy_verification_path,
        ),
        condition_fingerprints_sha256=condition_fingerprints.fingerprint(),
    )
    controls = FullABCReconciledManifestControls(
        legacy_execution_manifest_controls_sha256=_canonical_mapping_sha256(legacy_controls),
        functional_run_order_schedule_id="functional-counterbalance-v1",
        runtime_run_order_schedule_id="runtime-counterbalance-v1",
        timeout_policy_id="provider-request-policy-v1",
        retry_policy_id="provider-request-policy-v1",
        exclusion_policy_id="exclusion-policy-v1",
        rerun_policy_id="rerun-policy-v1",
        denominator_policy_id="denominator-policy-v1",
        statistical_reporting_configuration_id="paired-bootstrap-v1",
        quality_non_inferiority_policy_id="quality-non-inferiority-v1",
        trace_fields=_EXPECTED_TRACE_FIELDS,
    )
    return FullABCReconciledExecutionManifestDraft(
        identity=identity,
        assets=assets,
        controls=controls,
        unresolved_freeze_assets=(
            "cost_budget_approval",
            "cross_condition_isolation_report",
            "final_execution_manifest",
            "freeze_report",
            "gate10_manifest",
            "provider_readiness_record",
        ),
    )


def build_reconciliation_report() -> FullABCReconciliationReport:
    """Return the fixed local-versus-external reconciliation decision."""

    checks = (
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.SOURCE_COMMIT_CURRENT,
            status=FullABCReconciliationCheckStatus.PASSED,
            details=(f"source_merge_commit={_SOURCE_MERGE_COMMIT}",),
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.DEPENDENCY_LOCK_RESOLVED,
            status=FullABCReconciliationCheckStatus.PASSED,
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.CONDITION_FINGERPRINTS_RESOLVED,
            status=FullABCReconciliationCheckStatus.PASSED,
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.INTEGRATION_LINEAGE_CURRENT,
            status=FullABCReconciliationCheckStatus.PASSED,
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.STATIC_ASSETS_BOUND,
            status=FullABCReconciliationCheckStatus.PASSED,
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.PLANNED_LEDGER_CURRENT,
            status=FullABCReconciliationCheckStatus.PASSED,
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.TRACE_FIELDS_CURRENT,
            status=FullABCReconciliationCheckStatus.PASSED,
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.EXECUTION_DISABLED,
            status=FullABCReconciliationCheckStatus.PASSED,
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.PROVIDER_READINESS_PENDING,
            status=FullABCReconciliationCheckStatus.BLOCKED_EXTERNAL,
            details=("bounded provider readiness evidence requires separate authorization",),
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.COST_APPROVAL_PENDING,
            status=FullABCReconciliationCheckStatus.BLOCKED_EXTERNAL,
            details=("approved USD ceiling remains an operator decision",),
        ),
        FullABCReconciliationCheck(
            check_name=FullABCReconciliationCheckName.FREEZE_OUTPUTS_PENDING,
            status=FullABCReconciliationCheckStatus.PENDING_FREEZE,
            details=("Gate 10 outputs are generated only after provider and budget review",),
        ),
    )
    return FullABCReconciliationReport(
        report_id="auragateway-full-abc-draft-reconciliation-report-v2",
        source_merge_commit=_SOURCE_MERGE_COMMIT,
        checks=checks,
        next_gate="full_abc_provider_readiness_and_budget_review",
    )


def _build_static_hashes(repo_root: Path, spec: FullABCReconciliationSpec) -> dict[str, str]:
    paths = {
        "benchmark_constitution": spec.benchmark_constitution_path,
        "execution_requirements": spec.execution_requirements_path,
        "gate8_manifest": spec.gate8_manifest_path,
        "gate7_manifest": spec.gate7_manifest_path,
        "pricing_schedule": spec.pricing_schedule_path,
        "negative_controls": spec.negative_controls_path,
        "fault_fixtures": spec.fault_fixtures_path,
        "privacy_verification": spec.privacy_verification_path,
        "pyproject": spec.pyproject_path,
    }
    hashes = {name: _file_sha256(repo_root, path) for name, path in paths.items()}
    if hashes["benchmark_constitution"] != spec.expected_benchmark_constitution_sha256:
        raise FullABCReconciliationError(
            "BENCHMARK_CONSTITUTION_MISMATCH",
            "The frozen Benchmark Constitution identity changed.",
            spec.benchmark_constitution_path,
        )
    return dict(sorted(hashes.items()))


def build_reconciliation_assets(
    *,
    repo_root: Path,
    spec_path: Path,
    version_resolver: VersionResolver = importlib.metadata.version,
    python_version: str | None = None,
    python_implementation: str | None = None,
    verify_git_head: bool = True,
) -> tuple[
    FullABCDependencyLock,
    FullABCConditionFingerprintManifest,
    FullABCReconciliationInput,
    FullABCReconciledExecutionManifestDraft,
    FullABCReconciledPlannedRunLedger,
    FullABCReconciliationReport,
    FullABCReconciliationManifest,
    FullABCReconciliationSummary,
]:
    """Build the complete deterministic preflight-v2 reconciliation lineage."""

    if verify_git_head:
        _git_head(repo_root)
    spec = load_full_abc_reconciliation_spec(repo_root / spec_path)
    legacy_path = repo_root / spec.legacy_input_path
    legacy_payload = _require_dict(
        _load_json(legacy_path),
        path=legacy_path,
        field="legacy_input",
    )
    dependency_lock = build_dependency_lock(
        repo_root=repo_root,
        version_resolver=version_resolver,
        python_version=python_version,
        python_implementation=python_implementation,
    )
    condition_fingerprints = build_condition_fingerprints(
        repo_root=repo_root,
        spec=spec,
        dependency_lock=dependency_lock,
        legacy_input=legacy_payload,
    )
    static_hashes = _build_static_hashes(repo_root, spec)
    input_asset = FullABCReconciliationInput(
        reconciliation_id=spec.reconciliation_id,
        source_merge_commit=_SOURCE_MERGE_COMMIT,
        spec_path=spec_path.as_posix(),
        spec_sha256=spec.fingerprint(),
        legacy_input_path=spec.legacy_input_path,
        legacy_input_sha256=_file_sha256(repo_root, spec.legacy_input_path),
        integration_design_path=spec.integration_design_path,
        integration_design_sha256=_INTEGRATION_DESIGN_SHA256,
        integration_implementation_path=spec.integration_implementation_path,
        integration_implementation_sha256=_INTEGRATION_IMPLEMENTATION_SHA256,
        asset_inventory_path=spec.asset_inventory_path,
        asset_inventory_sha256=_ASSET_INVENTORY_SHA256,
        dependency_lock_path=_DEPENDENCY_LOCK_PATH.as_posix(),
        dependency_lock_sha256=dependency_lock.fingerprint(),
        condition_fingerprints_path=_CONDITION_FINGERPRINTS_PATH.as_posix(),
        condition_fingerprints_sha256=condition_fingerprints.fingerprint(),
        static_asset_hashes=static_hashes,
        trace_fields=_EXPECTED_TRACE_FIELDS,
    )
    draft = build_reconciled_draft(
        repo_root=repo_root,
        spec=spec,
        legacy_input=legacy_payload,
        dependency_lock=dependency_lock,
        condition_fingerprints=condition_fingerprints,
    )
    ledger = build_reconciled_ledger(
        legacy_input=legacy_payload,
        source_path=legacy_path,
        condition_fingerprints=condition_fingerprints,
    )
    report = build_reconciliation_report()
    manifest = FullABCReconciliationManifest(
        manifest_id="auragateway-full-abc-draft-reconciliation-manifest-v2",
        source_merge_commit=_SOURCE_MERGE_COMMIT,
        spec_path=spec_path.as_posix(),
        spec_sha256=spec.fingerprint(),
        dependency_lock_path=_DEPENDENCY_LOCK_PATH.as_posix(),
        dependency_lock_sha256=dependency_lock.fingerprint(),
        condition_fingerprints_path=_CONDITION_FINGERPRINTS_PATH.as_posix(),
        condition_fingerprints_sha256=condition_fingerprints.fingerprint(),
        input_path=_INPUT_PATH.as_posix(),
        input_sha256=input_asset.fingerprint(),
        execution_manifest_path=_DRAFT_PATH.as_posix(),
        execution_manifest_sha256=draft.fingerprint(),
        plan_path=_LEDGER_PATH.as_posix(),
        plan_sha256=ledger.fingerprint(),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=report.fingerprint(),
        next_gate="full_abc_provider_readiness_and_budget_review",
    )
    summary = FullABCReconciliationSummary(
        source_merge_commit=_SOURCE_MERGE_COMMIT,
        dependency_lock_sha256=dependency_lock.fingerprint(),
        condition_fingerprints_sha256=condition_fingerprints.fingerprint(),
        execution_manifest_draft_sha256=draft.fingerprint(),
        planned_run_ledger_sha256=ledger.fingerprint(),
        reconciliation_manifest_sha256=manifest.fingerprint(),
        total_trajectory_count=ledger.total_trajectory_count,
        planning_ready=report.planning_ready,
        draft_current=report.draft_current,
        measured_execution_ready=report.measured_execution_ready,
        execution_enabled=report.execution_enabled,
        measured_execution_permitted=report.measured_execution_permitted,
        next_gate=report.next_gate,
    )
    return (
        dependency_lock,
        condition_fingerprints,
        input_asset,
        draft,
        ledger,
        report,
        manifest,
        summary,
    )


def write_reconciliation_assets(
    *,
    repo_root: Path,
    spec_path: Path,
    version_resolver: VersionResolver = importlib.metadata.version,
    python_version: str | None = None,
    python_implementation: str | None = None,
    verify_git_head: bool = True,
) -> FullABCReconciliationSummary:
    """Generate the complete local preflight-v2 asset set."""

    (
        dependency_lock,
        condition_fingerprints,
        input_asset,
        draft,
        ledger,
        report,
        manifest,
        summary,
    ) = build_reconciliation_assets(
        repo_root=repo_root,
        spec_path=spec_path,
        version_resolver=version_resolver,
        python_version=python_version,
        python_implementation=python_implementation,
        verify_git_head=verify_git_head,
    )
    output_root = repo_root / _OUTPUT_ROOT
    output_root.mkdir(parents=True, exist_ok=True)
    outputs = (
        (_DEPENDENCY_LOCK_PATH, dependency_lock),
        (_CONDITION_FINGERPRINTS_PATH, condition_fingerprints),
        (_INPUT_PATH, input_asset),
        (_DRAFT_PATH, draft),
        (_LEDGER_PATH, ledger),
        (_REPORT_PATH, report),
        (_MANIFEST_PATH, manifest),
    )
    for relative_path, model in outputs:
        (repo_root / relative_path).write_bytes(_canonical_json_bytes(model))
    return summary


def verify_reconciliation_assets(
    *,
    repo_root: Path,
    spec_path: Path,
    version_resolver: VersionResolver = importlib.metadata.version,
    python_version: str | None = None,
    python_implementation: str | None = None,
    verify_git_head: bool = True,
) -> FullABCReconciliationSummary:
    """Rebuild the v2 lineage and compare every persisted artifact exactly."""

    *expected_models, summary = build_reconciliation_assets(
        repo_root=repo_root,
        spec_path=spec_path,
        version_resolver=version_resolver,
        python_version=python_version,
        python_implementation=python_implementation,
        verify_git_head=verify_git_head,
    )
    paths = (
        _DEPENDENCY_LOCK_PATH,
        _CONDITION_FINGERPRINTS_PATH,
        _INPUT_PATH,
        _DRAFT_PATH,
        _LEDGER_PATH,
        _REPORT_PATH,
        _MANIFEST_PATH,
    )
    for relative_path, expected in zip(paths, expected_models, strict=True):
        observed_path = repo_root / relative_path
        try:
            observed = observed_path.read_bytes()
        except FileNotFoundError as exc:
            raise FullABCReconciliationError(
                "RECONCILIATION_OUTPUT_NOT_FOUND",
                "A generated reconciliation output was not found.",
                str(observed_path),
            ) from exc
        expected_bytes = _canonical_json_bytes(expected)
        if observed != expected_bytes:
            raise FullABCReconciliationError(
                "RECONCILIATION_OUTPUT_MISMATCH",
                "A generated reconciliation output is not reproducible.",
                str(observed_path),
            )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--spec-path",
        type=Path,
        default=Path(
            "benchmarks/local_abc/"
            "auragateway_full_abc_execution_manifest_draft_reconciliation_v2.json"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Generate or verify the local-only preflight-v2 lineage."""

    args = _parse_args(argv)
    try:
        if args.command == "generate":
            summary = write_reconciliation_assets(
                repo_root=args.repo_root,
                spec_path=args.spec_path,
            )
        else:
            summary = verify_reconciliation_assets(
                repo_root=args.repo_root,
                spec_path=args.spec_path,
            )
    except FullABCReconciliationError as exc:
        envelope = FullABCReconciliationErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
