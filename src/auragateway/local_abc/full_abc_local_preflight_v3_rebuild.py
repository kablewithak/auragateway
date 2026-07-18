"""Generate the clean local-only full A/B/C preflight-v3 planning lineage."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal, cast
from uuid import UUID, uuid5

from auragateway.local_abc.contracts import ConditionId, LocalABCContract
from auragateway.local_abc.full_abc_local_preflight_v3_rebuild_contracts import (
    _ACTION_SCHEMA_SHA256,
    _BENCHMARK_CONSTITUTION_SHA256,
    _EXECUTION_REQUIREMENTS_SHA256,
    _EXPECTED_CORRECTION_SHA256,
    _EXPECTED_FUNCTIONAL_SHA256,
    _EXPECTED_INVENTORY_SHA256,
    _EXPECTED_PREFIX_MANIFEST_SHA256,
    _EXPECTED_REVIEW_SHA256,
    _EXPECTED_RUNTIME_SELECTION_SHA256,
    _EXPECTED_SUPERSESSION_SHA256,
    _FUNCTIONAL_SCHEDULE,
    _INTEGRATION_DESIGN_SHA256,
    _INTEGRATION_IMPLEMENTATION_SHA256,
    _MODEL_ALIAS,
    _MODEL_REPOSITORY,
    _MODEL_REVISION,
    _PREFIX_FINGERPRINT,
    _PROMPT_POLICY_SHA256,
    _QUALITY_RUBRIC_SHA256,
    _REQUIRED_DISTRIBUTIONS,
    _RESPONSE_SCHEMA_SHA256,
    _RETRIEVAL_CONFIGURATION_SHA256,
    _RUNTIME_SCHEDULE,
    _TOKENIZER_REVISION,
    _TORCH_CUDA_VERSION,
    _TORCH_VERSION,
    _TRACE_FIELDS,
    _VLLM_DISTRIBUTION_VERSION,
    _VLLM_WHEEL_SHA256,
    CONDITION_FINGERPRINTS_PATH,
    CORRECTION_PATH,
    DEVELOPER_LOCK_PATH,
    DRAFT_PATH,
    FUNCTIONAL_EPISODES_PATH,
    IMPLEMENTATION_ID,
    IMPLEMENTATION_PLAN_PATH,
    INPUT_PATH,
    INVENTORY_PATH,
    LEDGER_PATH,
    MANIFEST_PATH,
    NEXT_GATE,
    PREFIX_MANIFEST_PATH,
    REPORT_PATH,
    REVIEW_PATH,
    REVIEW_SHA256,
    REVIEW_SOURCE_BLOB_SHA,
    RUNTIME_SELECTION_PATH,
    SOURCE_MAIN_MERGE_COMMIT,
    SUPERSESSION_PATH,
    ConditionFingerprintManifest,
    ConditionFingerprintPayload,
    ConditionFingerprintRecord,
    DeveloperDependencyLock,
    DeveloperDependencyPackage,
    DeveloperDependencyRole,
    ExecutionManifestDraft,
    ExecutionManifestPlanningIdentity,
    FullABCLocalPreflightV3RebuildError,
    FullABCLocalPreflightV3RebuildErrorEnvelope,
    GeneratedPreflightV3Bundle,
    LocalRuntimeDirection,
    MetricMappingPlan,
    PlannedRun,
    PlannedRunLedger,
    PreflightV3ArtifactBinding,
    PreflightV3Check,
    PreflightV3CheckStatus,
    PreflightV3ImplementationPlan,
    PreflightV3Manifest,
    PreflightV3PlanningInput,
    PreflightV3Report,
    RuntimeQualificationPlaceholder,
    SharedConditionConfiguration,
    TraceCompatibilityBoundary,
)
from auragateway.local_abc.full_abc_local_preflight_v3_rebuild_review import (
    load_full_abc_local_preflight_v3_rebuild_review,
)

VersionResolver = Callable[[str], str]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _raw_file_sha256(path: Path) -> str:
    """Hash exact repository bytes for assets whose manifests bind file SHA-256."""

    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise FullABCLocalPreflightV3RebuildError(
            "REQUIRED_JSON_ASSET_UNREADABLE",
            "a required preflight-v3 JSON asset could not be read",
            path.as_posix(),
        ) from exc


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullABCLocalPreflightV3RebuildError(
            "REQUIRED_JSON_ASSET_UNREADABLE",
            "a required preflight-v3 JSON asset could not be read",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise FullABCLocalPreflightV3RebuildError(
            "REQUIRED_JSON_ASSET_INVALID_ROOT",
            "a required preflight-v3 JSON asset must contain one object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _git_merge_is_ancestor(repo_root: Path, commit_sha: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_sha, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise FullABCLocalPreflightV3RebuildError(
            "SOURCE_MAIN_MERGE_NOT_IN_ANCESTRY",
            "preflight-v3 rebuild requires PR 99 in the current HEAD ancestry",
            details=(f"required_ancestor={commit_sha}",),
        )


def _require_expected_digest(path: Path, expected: str, *, asset_id: str) -> str:
    actual = _raw_file_sha256(path)
    if actual != expected:
        raise FullABCLocalPreflightV3RebuildError(
            "SOURCE_ASSET_IDENTITY_MISMATCH",
            "a required preflight-v3 source asset drifted",
            path.as_posix(),
            (asset_id,),
        )
    return actual


def _extract_functional_episode_ids(payload: dict[str, object]) -> tuple[str, ...]:
    episodes = payload.get("episodes")
    if not isinstance(episodes, list):
        raise FullABCLocalPreflightV3RebuildError(
            "FUNCTIONAL_EPISODE_SET_INVALID",
            "functional episode set does not contain an episode list",
        )
    ids: list[str] = []
    for item in episodes:
        if not isinstance(item, dict) or not isinstance(item.get("episode_id"), str):
            raise FullABCLocalPreflightV3RebuildError(
                "FUNCTIONAL_EPISODE_SET_INVALID",
                "functional episode set contains an invalid episode identity",
            )
        ids.append(cast(str, item["episode_id"]))
    result = tuple(ids)
    if len(result) != 18 or result != tuple(sorted(result)) or len(result) != len(set(result)):
        raise FullABCLocalPreflightV3RebuildError(
            "FUNCTIONAL_EPISODE_SET_INVALID",
            "functional episode set must contain 18 unique sorted identities",
        )
    return result


def _extract_runtime_episode_ids(payload: dict[str, object]) -> tuple[str, ...]:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise FullABCLocalPreflightV3RebuildError(
            "RUNTIME_EPISODE_SET_INVALID",
            "runtime selection does not contain an entries list",
        )
    ids: list[str] = []
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("episode_id"), str):
            raise FullABCLocalPreflightV3RebuildError(
                "RUNTIME_EPISODE_SET_INVALID",
                "runtime selection contains an invalid episode identity",
            )
        ids.append(cast(str, item["episode_id"]))
    result = tuple(ids)
    if len(result) != 6 or result != tuple(sorted(result)) or len(result) != len(set(result)):
        raise FullABCLocalPreflightV3RebuildError(
            "RUNTIME_EPISODE_SET_INVALID",
            "runtime selection must contain six unique sorted identities",
        )
    return result


def load_preflight_v3_implementation_plan(path: Path) -> PreflightV3ImplementationPlan:
    """Load the static implementation plan supplied with this slice."""

    payload = _load_json_object(path)
    try:
        return PreflightV3ImplementationPlan.model_validate(payload)
    except ValueError as exc:
        raise FullABCLocalPreflightV3RebuildError(
            "IMPLEMENTATION_PLAN_INVALID",
            "the preflight-v3 implementation plan failed typed validation",
            path.as_posix(),
        ) from exc


def build_developer_dependency_lock(
    *,
    repo_root: Path,
    version_resolver: VersionResolver = importlib.metadata.version,
    python_version: str | None = None,
    python_implementation: str | None = None,
) -> DeveloperDependencyLock:
    """Capture exact local validation dependencies without promoting Groq to runtime."""

    pyproject_path = repo_root / "pyproject.toml"
    try:
        pyproject_bytes = pyproject_path.read_bytes()
        pyproject = tomllib.loads(pyproject_bytes.decode("utf-8"))
    except FileNotFoundError as exc:
        raise FullABCLocalPreflightV3RebuildError(
            "PYPROJECT_NOT_FOUND",
            "AuraGateway pyproject.toml was not found",
            pyproject_path.as_posix(),
        ) from exc
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise FullABCLocalPreflightV3RebuildError(
            "PYPROJECT_INVALID",
            "AuraGateway pyproject.toml could not be parsed",
            pyproject_path.as_posix(),
        ) from exc

    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise FullABCLocalPreflightV3RebuildError(
            "PYPROJECT_PROJECT_INVALID",
            "AuraGateway project metadata is missing",
            pyproject_path.as_posix(),
        )
    project_name = project.get("name")
    project_version_value = project.get("version")
    if project_name != "auragateway" or not isinstance(project_version_value, str):
        raise FullABCLocalPreflightV3RebuildError(
            "PROJECT_IDENTITY_MISMATCH",
            "the project metadata does not identify AuraGateway",
            pyproject_path.as_posix(),
        )

    roles = {
        "groq": DeveloperDependencyRole.HISTORICAL_HOSTED_PROVIDER,
        "pydantic": DeveloperDependencyRole.ACTIVE_RUNTIME,
        "mypy": DeveloperDependencyRole.DEVELOPMENT,
        "pytest": DeveloperDependencyRole.DEVELOPMENT,
        "ruff": DeveloperDependencyRole.DEVELOPMENT,
        "setuptools": DeveloperDependencyRole.BUILD,
    }
    packages: list[DeveloperDependencyPackage] = []
    for distribution_name in _REQUIRED_DISTRIBUTIONS:
        try:
            resolved_version = version_resolver(distribution_name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise FullABCLocalPreflightV3RebuildError(
                "DEPENDENCY_DISTRIBUTION_NOT_FOUND",
                "a required AuraGateway validation distribution is not installed",
                details=(distribution_name,),
            ) from exc
        role = roles[distribution_name]
        packages.append(
            DeveloperDependencyPackage(
                distribution_name=distribution_name,
                version=resolved_version,
                role=role,
                active_full_abc_runtime_dependency=(role is DeveloperDependencyRole.ACTIVE_RUNTIME),
            )
        )

    implementation = python_implementation or platform.python_implementation()
    if implementation != "CPython":
        raise FullABCLocalPreflightV3RebuildError(
            "PYTHON_IMPLEMENTATION_UNSUPPORTED",
            "AuraGateway preflight-v3 generation requires CPython",
            details=(implementation,),
        )

    return DeveloperDependencyLock(
        lock_id="auragateway-full-abc-developer-dependency-lock-v3",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        review_sha256=REVIEW_SHA256,
        pyproject_path="pyproject.toml",
        pyproject_sha256=_sha256_bytes(pyproject_bytes),
        project_name="auragateway",
        project_version=project_version_value,
        python_implementation="CPython",
        python_version=python_version or platform.python_version(),
        packages=cast(
            tuple[
                DeveloperDependencyPackage,
                DeveloperDependencyPackage,
                DeveloperDependencyPackage,
                DeveloperDependencyPackage,
                DeveloperDependencyPackage,
                DeveloperDependencyPackage,
            ],
            tuple(packages),
        ),
    )


def _runtime_direction() -> LocalRuntimeDirection:
    return LocalRuntimeDirection(
        execution_backend="local_vllm",
        environment="kaggle_t4_x2",
        transport_endpoint="/v1/chat/completions",
        model_alias=_MODEL_ALIAS,
        model_repository=_MODEL_REPOSITORY,
        model_revision=_MODEL_REVISION,
        tokenizer_revision=_TOKENIZER_REVISION,
        torch_version=_TORCH_VERSION,
        torch_cuda_version=_TORCH_CUDA_VERSION,
        vllm_distribution_version=_VLLM_DISTRIBUTION_VERSION,
        vllm_wheel_sha256=_VLLM_WHEEL_SHA256,
        worker_client_contract="auragateway.local_abc.worker_client.WorkerClient",
        worker_registry_contract="auragateway.local_abc.worker_registry.WorkerRegistry",
        worker_bindings=("worker_1=gpu0:8001", "worker_2=gpu1:8002"),
    )


def _runtime_placeholder() -> RuntimeQualificationPlaceholder:
    return RuntimeQualificationPlaceholder(
        status="UNRESOLVED_BEFORE_ENVIRONMENT_QUALIFICATION",
        required_fields=(
            "attention_backend",
            "automatic_prefix_cache_configuration",
            "cuda_version",
            "dtype",
            "gpu_memory_utilization",
            "gpu_model",
            "maximum_model_length",
            "model_repository",
            "model_revision",
            "output_token_budget",
            "python_version",
            "quantization",
            "tokenizer_revision",
            "torch_version",
            "transformers_version",
            "vllm_distribution_version",
            "vllm_wheel_sha256",
            "worker_startup_command_sha256",
        ),
    )


def _metric_mapping_plan() -> MetricMappingPlan:
    return MetricMappingPlan(
        mapping_id="local-vllm-cache-metric-mapping-plan-v1",
        cache_observation_states=(
            "invalid",
            "not_exposed",
            "not_observed",
            "positive",
            "zero",
        ),
        primary_metric_formula=("eligible_shared_prefix_tokens-observed_cached_prefix_tokens"),
        current_metric_names_status=("UNRESOLVED_BEFORE_CACHE_OBSERVABILITY_QUALIFICATION"),
    )


def _cache_hostile_prefix_identity() -> str:
    return _sha256_bytes(
        _canonical_json(
            {
                "base_prefix_fingerprint": _PREFIX_FINGERPRINT,
                "mutation_policy": "deterministic_per_turn_cache_hostile_v3",
                "prefix_policy": "cache_hostile",
            }
        ).encode("utf-8")
    )


def build_condition_fingerprints(
    *,
    developer_lock: DeveloperDependencyLock,
) -> tuple[
    ConditionFingerprintManifest,
    RuntimeQualificationPlaceholder,
    MetricMappingPlan,
    LocalRuntimeDirection,
]:
    """Build local-only fingerprints without provider, pricing, or budget fields."""

    runtime = _runtime_direction()
    runtime_placeholder = _runtime_placeholder()
    metric_mapping = _metric_mapping_plan()
    shared = SharedConditionConfiguration(
        action_schema_sha256=_ACTION_SCHEMA_SHA256,
        benchmark_constitution_sha256=_BENCHMARK_CONSTITUTION_SHA256,
        decoding_configuration_sha256=runtime_placeholder.fingerprint(),
        environment="kaggle_t4_x2",
        execution_backend="local_vllm",
        execution_manifest_requirements_sha256=_EXECUTION_REQUIREMENTS_SHA256,
        metric_mapping_sha256=metric_mapping.fingerprint(),
        model_alias=_MODEL_ALIAS,
        model_repository=_MODEL_REPOSITORY,
        model_revision=_MODEL_REVISION,
        prompt_policy_sha256=_PROMPT_POLICY_SHA256,
        quality_rubric_sha256=_QUALITY_RUBRIC_SHA256,
        response_schema_sha256=_RESPONSE_SCHEMA_SHA256,
        retrieval_configuration_sha256=_RETRIEVAL_CONFIGURATION_SHA256,
        runtime_configuration_sha256=runtime.fingerprint(),
        tokenizer_revision=_TOKENIZER_REVISION,
        torch_cuda_version=_TORCH_CUDA_VERSION,
        torch_version=_TORCH_VERSION,
        transport_endpoint="/v1/chat/completions",
        vllm_distribution_version=_VLLM_DISTRIBUTION_VERSION,
        worker_client_contract="auragateway.local_abc.worker_client.WorkerClient",
        worker_registry_contract="auragateway.local_abc.worker_registry.WorkerRegistry",
    )
    configurations = (
        (
            ConditionId.A,
            "condition-a-cache-namespace-v3",
            "cache_hostile",
            _cache_hostile_prefix_identity(),
            ("worker_1", "worker_2"),
        ),
        (
            ConditionId.B,
            "condition-b-cache-namespace-v3",
            "deterministic_exact",
            _PREFIX_FINGERPRINT,
            ("worker_1", "worker_2"),
        ),
        (
            ConditionId.C,
            "condition-c-cache-namespace-v3",
            "deterministic_exact",
            _PREFIX_FINGERPRINT,
            ("worker_1", "worker_1"),
        ),
    )
    records: list[ConditionFingerprintRecord] = []
    for (
        condition_id,
        namespace,
        prefix_policy,
        prefix_hash,
        route_schedule,
    ) in configurations:
        payload = ConditionFingerprintPayload(
            source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
            condition_id=condition_id,
            cache_namespace_id=namespace,
            prefix_policy=cast(Literal["cache_hostile", "deterministic_exact"], prefix_policy),
            prefix_token_hash=prefix_hash,
            prefix_token_hash_status="planning_identity_requires_runtime_confirmation",
            route_schedule=cast(
                tuple[
                    Literal["worker_1", "worker_2"],
                    Literal["worker_1", "worker_2"],
                ],
                route_schedule,
            ),
            shared=shared,
        )
        records.append(
            ConditionFingerprintRecord(
                payload=payload,
                configuration_fingerprint=payload.fingerprint(),
            )
        )

    manifest = ConditionFingerprintManifest(
        manifest_id="auragateway-full-abc-condition-fingerprints-v3",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        review_sha256=REVIEW_SHA256,
        developer_dependency_lock_sha256=developer_lock.fingerprint(),
        trace_compatibility=TraceCompatibilityBoundary(
            field_name="provider_model_alias",
            field_value=_MODEL_ALIAS,
            semantics=("legacy_name_bound_to_local_runtime_model_alias_without_provider_authority"),
        ),
        records=cast(
            tuple[
                ConditionFingerprintRecord,
                ConditionFingerprintRecord,
                ConditionFingerprintRecord,
            ],
            tuple(records),
        ),
    )
    return manifest, runtime_placeholder, metric_mapping, runtime


def _condition_slug(condition_id: ConditionId) -> str:
    return {
        ConditionId.A: "condition-a",
        ConditionId.B: "condition-b",
        ConditionId.C: "condition-c",
    }[condition_id]


def _route_schedule_id(
    condition_id: ConditionId,
) -> Literal["turn-local-worker1-worker2-v1", "affinity-worker1-worker1-v1"]:
    if condition_id is ConditionId.C:
        return "affinity-worker1-worker1-v1"
    return "turn-local-worker1-worker2-v1"


def _expand_runs(
    *,
    start_index: int,
    workload: Literal["functional", "runtime_microbenchmark"],
    episode_ids: tuple[str, ...],
    schedule: tuple[tuple[ConditionId, ConditionId, ConditionId], ...],
    fingerprints: ConditionFingerprintManifest,
    execution_identity_sha256: str,
) -> tuple[PlannedRun, ...]:
    runs: list[PlannedRun] = []
    order_index = start_index
    workload_slug = "functional" if workload == "functional" else "runtime"
    benchmark_sha = (
        _EXPECTED_FUNCTIONAL_SHA256
        if workload == "functional"
        else _EXPECTED_RUNTIME_SELECTION_SHA256
    )
    namespace = UUID("f4b71ac8-8916-5d97-8c34-15408ef86034")
    for episode_id in episode_ids:
        for replication_number, condition_order in enumerate(schedule, start=1):
            pair_id = f"pair-{workload_slug}-{episode_id}-r{replication_number:02d}"
            for condition_id in condition_order:
                condition_slug = _condition_slug(condition_id)
                run_id = (
                    f"run-{workload_slug}-{episode_id}-r{replication_number:02d}-{condition_slug}"
                )
                runs.append(
                    PlannedRun(
                        run_id=run_id,
                        trace_id=uuid5(namespace, run_id),
                        comparison_pair_id=pair_id,
                        workload=workload,
                        episode_id=episode_id,
                        replication_id=f"replication-{replication_number:02d}",
                        condition_id=condition_id,
                        condition_configuration_fingerprint=(
                            fingerprints.fingerprint_for(condition_id)
                        ),
                        cache_namespace_id=(
                            f"ns-{workload_slug}-{episode_id}-"
                            f"r{replication_number:02d}-{condition_slug}"
                        ),
                        route_schedule_id=_route_schedule_id(condition_id),
                        planned_order_index=order_index,
                        benchmark_manifest_sha256=benchmark_sha,
                        execution_manifest_sha256=execution_identity_sha256,
                    )
                )
                order_index += 1
    return tuple(runs)


def build_planned_run_ledger(
    *,
    functional_episode_ids: tuple[str, ...],
    runtime_episode_ids: tuple[str, ...],
    fingerprints: ConditionFingerprintManifest,
    planning_identity: ExecutionManifestPlanningIdentity,
) -> PlannedRunLedger:
    """Regenerate all 342 trajectories against clean local v3 fingerprints."""

    functional_runs = _expand_runs(
        start_index=0,
        workload="functional",
        episode_ids=functional_episode_ids,
        schedule=_FUNCTIONAL_SCHEDULE,
        fingerprints=fingerprints,
        execution_identity_sha256=planning_identity.fingerprint(),
    )
    runtime_runs = _expand_runs(
        start_index=len(functional_runs),
        workload="runtime_microbenchmark",
        episode_ids=runtime_episode_ids,
        schedule=_RUNTIME_SCHEDULE,
        fingerprints=fingerprints,
        execution_identity_sha256=planning_identity.fingerprint(),
    )
    return PlannedRunLedger(
        plan_id="benchmark-plan-auragateway-local-abc-v3",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        condition_fingerprints_sha256=fingerprints.fingerprint(),
        execution_manifest_planning_identity_sha256=planning_identity.fingerprint(),
        functional_run_order_schedule_id="functional-counterbalance-v1",
        runtime_run_order_schedule_id="runtime-counterbalance-v1",
        runs=functional_runs + runtime_runs,
    )


def _frozen_asset_bindings() -> dict[str, str]:
    return dict(
        sorted(
            {
                "action_schema_sha256": _ACTION_SCHEMA_SHA256,
                "asset_inventory_sha256": _EXPECTED_INVENTORY_SHA256,
                "benchmark_constitution_sha256": _BENCHMARK_CONSTITUTION_SHA256,
                "chunking_configuration_sha256": (
                    "bee67067af933b17a58b9221f8efdea10837bde1cd8b7969fe25ff92051601d2"
                ),
                "comparison_eligibility_manifest_sha256": (
                    "259f1a3646311e705d68eca10ee7ea7fa4b9d89700227b15dedb8fd118808405"
                ),
                "corpus_manifest_sha256": (
                    "c68212afd5381dec8bce49d0d5fee231a3b5589bf5460c0f72297e0c84422f55"
                ),
                "development_retrieval_manifest_sha256": (
                    "fce8d7ac8f6f11f3a48891040810b1c37a8b3c186eda85caec41f75791dc4dd5"
                ),
                "diagnostic_episode_manifest_sha256": (
                    "3a77c6fa037c62a1a548c2e5dc13e9668ebd3114cb58903df538bf7fa239ea6b"
                ),
                "execution_manifest_requirements_sha256": _EXECUTION_REQUIREMENTS_SHA256,
                "fault_injection_fixture_sha256": (
                    "257b6f8a142b103ebe22f53086e7674f13af80fa5a8e397737406cbacd3f65aa"
                ),
                "feedback_manifest_sha256": (
                    "7e856227772b38d4b66cd41936e0ad695747544f733942d4165c80dd1f71573e"
                ),
                "functional_benchmark_manifest_sha256": _EXPECTED_FUNCTIONAL_SHA256,
                "held_out_retrieval_manifest_sha256": (
                    "6d2c454a8e2b99cfef55f45c177944154aa09c76d4826cfd83035f0439a0820f"
                ),
                "integration_design_sha256": _INTEGRATION_DESIGN_SHA256,
                "integration_implementation_sha256": _INTEGRATION_IMPLEMENTATION_SHA256,
                "negative_control_manifest_sha256": (
                    "7e9da92957fdc04dfffeb423094e6a7b0868a7ffe3139509b27a7186c9b1ac86"
                ),
                "prefix_manifest_sha256": _EXPECTED_PREFIX_MANIFEST_SHA256,
                "privacy_verification_report_sha256": (
                    "de0025974cc9cbc0faaecbca13a419f7807b1870e9cd7a596460bb943736ab91"
                ),
                "prompt_policy_sha256": _PROMPT_POLICY_SHA256,
                "quality_rubric_sha256": _QUALITY_RUBRIC_SHA256,
                "response_schema_sha256": _RESPONSE_SCHEMA_SHA256,
                "retrieval_configuration_sha256": _RETRIEVAL_CONFIGURATION_SHA256,
                "retrieval_scorecard_sha256": (
                    "c10cc5025139f0118a9e07e9b1960f99c9c7ead4115e67d7ffa000c4817b9734"
                ),
                "review_sample_schedule_sha256": (
                    "da00e83fd9ad83098e1232e9b46a9d7395c6ad7dc8f82dab3966b7cca8b11de4"
                ),
                "runtime_microbenchmark_manifest_sha256": (
                    "5ff912ad317fe09d97518e5b03178ebe3bb565dcf09719182bfffc80b67034e1"
                ),
                "telemetry_fixture_manifest_sha256": (
                    "3a3bcb5296cb23f65bf4399ea2723ecb67323a8f49d1d7b2389fd334f9397e8b"
                ),
            }.items()
        )
    )


def _unresolved_assets() -> tuple[str, ...]:
    return tuple(
        sorted(
            (
                "cache-observability-qualification",
                "cache-pressure-diagnostics",
                "cache-reset-qualification",
                "current-environment-report",
                "execution-manifest-freeze",
                "fault-diagnostics",
                "kaggle-runtime-dependency-lock",
                "measured-execution-authorization",
                "repetition-count-freeze",
                "variance-pilot",
                "worker-isolation-qualification",
            )
        )
    )


def _build_preflight_report() -> PreflightV3Report:
    checks = tuple(
        sorted(
            (
                PreflightV3Check(
                    check_id="cache-diagnostics",
                    status=PreflightV3CheckStatus.BLOCKED_FOR_LATER_GATE,
                    evidence=(
                        "Fresh cache, reset, pressure, and worker-isolation evidence required."
                    ),
                ),
                PreflightV3Check(
                    check_id="condition-fingerprints",
                    status=PreflightV3CheckStatus.PASS,
                    evidence=(
                        "Three local-only A/B/C fingerprints generated without provider fields."
                    ),
                ),
                PreflightV3Check(
                    check_id="developer-dependency-lock",
                    status=PreflightV3CheckStatus.PASS,
                    evidence=(
                        "Local validation dependencies captured separately from Kaggle runtime."
                    ),
                ),
                PreflightV3Check(
                    check_id="environment-qualification",
                    status=PreflightV3CheckStatus.BLOCKED_FOR_LATER_GATE,
                    evidence="Current full-run Kaggle T4 x2 environment remains unqualified.",
                ),
                PreflightV3Check(
                    check_id="execution-freeze",
                    status=PreflightV3CheckStatus.BLOCKED_FOR_LATER_GATE,
                    evidence="Manifest freeze and measured authorization remain prohibited.",
                ),
                PreflightV3Check(
                    check_id="planned-run-ledger",
                    status=PreflightV3CheckStatus.PASS,
                    evidence="All 342 trajectories regenerated against clean v3 fingerprints.",
                ),
                PreflightV3Check(
                    check_id="preflight-v2-supersession",
                    status=PreflightV3CheckStatus.PASS,
                    evidence="Contaminated v2 hashes and provider bindings are not reused.",
                ),
                PreflightV3Check(
                    check_id="variance-pilot",
                    status=PreflightV3CheckStatus.BLOCKED_FOR_LATER_GATE,
                    evidence="Counterbalanced pilot and repetition freeze remain outstanding.",
                ),
                PreflightV3Check(
                    check_id="zero-spend-safety",
                    status=PreflightV3CheckStatus.PASS,
                    evidence=(
                        "Hosted providers, credentials, pricing, and paid fallback remain disabled."
                    ),
                ),
            ),
            key=lambda item: item.check_id,
        )
    )
    return PreflightV3Report(
        report_id="auragateway-full-abc-local-preflight-v3-report-v1",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        decision="PLANNING_ASSETS_GENERATED_EXECUTION_BLOCKED",
        checks=checks,
        next_gate=NEXT_GATE,
    )


def _build_manifest(
    artifacts: Iterable[tuple[str, Path, LocalABCContract]],
) -> PreflightV3Manifest:
    bindings = tuple(
        sorted(
            (
                PreflightV3ArtifactBinding(
                    artifact_id=artifact_id,
                    path=path.as_posix(),
                    sha256=model.fingerprint(),
                )
                for artifact_id, path, model in artifacts
            ),
            key=lambda item: item.artifact_id,
        )
    )
    return PreflightV3Manifest(
        manifest_id="auragateway-full-abc-local-preflight-v3-manifest-v1",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation_id=IMPLEMENTATION_ID,
        artifacts=cast(
            tuple[
                PreflightV3ArtifactBinding,
                PreflightV3ArtifactBinding,
                PreflightV3ArtifactBinding,
                PreflightV3ArtifactBinding,
                PreflightV3ArtifactBinding,
                PreflightV3ArtifactBinding,
            ],
            bindings,
        ),
        next_gate=NEXT_GATE,
    )


def build_preflight_v3_bundle(
    *,
    repo_root: Path,
    version_resolver: VersionResolver = importlib.metadata.version,
    python_version: str | None = None,
    python_implementation: str | None = None,
    verify_git_ancestry: bool = True,
) -> GeneratedPreflightV3Bundle:
    """Build every clean planning asset without executing a model or notebook."""

    if verify_git_ancestry:
        _git_merge_is_ancestor(repo_root, SOURCE_MAIN_MERGE_COMMIT)

    review = load_full_abc_local_preflight_v3_rebuild_review(repo_root / REVIEW_PATH)
    if review.fingerprint() != _EXPECTED_REVIEW_SHA256:
        raise FullABCLocalPreflightV3RebuildError(
            "REVIEW_IDENTITY_MISMATCH",
            "the accepted preflight-v3 review identity drifted",
            REVIEW_PATH.as_posix(),
        )
    if review.decision != "APPROVED_FOR_BOUNDED_REBUILD_IMPLEMENTATION":
        raise FullABCLocalPreflightV3RebuildError(
            "REVIEW_DECISION_NOT_APPROVED",
            "the accepted preflight-v3 review does not authorize bounded generation",
            REVIEW_PATH.as_posix(),
        )

    _require_expected_digest(
        repo_root / CORRECTION_PATH,
        _EXPECTED_CORRECTION_SHA256,
        asset_id="local-runtime-correction",
    )
    _require_expected_digest(
        repo_root / SUPERSESSION_PATH,
        _EXPECTED_SUPERSESSION_SHA256,
        asset_id="preflight-v2-supersession",
    )
    _require_expected_digest(
        repo_root / INVENTORY_PATH,
        _EXPECTED_INVENTORY_SHA256,
        asset_id="asset-inventory",
    )
    _require_expected_digest(
        repo_root / FUNCTIONAL_EPISODES_PATH,
        _EXPECTED_FUNCTIONAL_SHA256,
        asset_id="functional-episode-set",
    )
    _require_expected_digest(
        repo_root / RUNTIME_SELECTION_PATH,
        _EXPECTED_RUNTIME_SELECTION_SHA256,
        asset_id="runtime-selection",
    )
    _require_expected_digest(
        repo_root / PREFIX_MANIFEST_PATH,
        _EXPECTED_PREFIX_MANIFEST_SHA256,
        asset_id="prefix-determinism-manifest",
    )

    correction_payload = _load_json_object(repo_root / CORRECTION_PATH)
    supersession_payload = _load_json_object(repo_root / SUPERSESSION_PATH)
    blocked_flags = (
        correction_payload.get("groq_in_full_abc_scope") is False,
        correction_payload.get("openrouter_in_full_abc_scope") is False,
        correction_payload.get("pricing_schedule_required") is False,
        correction_payload.get("measured_execution_authorized") is False,
        supersession_payload.get("preflight_v2_reuse_permitted") is False,
        supersession_payload.get("execution_authorized") is False,
    )
    if not all(blocked_flags):
        raise FullABCLocalPreflightV3RebuildError(
            "SUPERSESSION_BOUNDARY_NOT_FAIL_CLOSED",
            "the hosted-provider and preflight-v2 boundaries are not fully blocked",
        )

    functional_ids = _extract_functional_episode_ids(
        _load_json_object(repo_root / FUNCTIONAL_EPISODES_PATH)
    )
    runtime_ids = _extract_runtime_episode_ids(
        _load_json_object(repo_root / RUNTIME_SELECTION_PATH)
    )

    developer_lock = build_developer_dependency_lock(
        repo_root=repo_root,
        version_resolver=version_resolver,
        python_version=python_version,
        python_implementation=python_implementation,
    )
    fingerprints, runtime_placeholder, metric_mapping, runtime_direction = (
        build_condition_fingerprints(developer_lock=developer_lock)
    )
    planning_input = PreflightV3PlanningInput(
        input_id="auragateway-full-abc-local-preflight-v3-input-v1",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        review_sha256=review.fingerprint(),
        review_source_blob_sha=REVIEW_SOURCE_BLOB_SHA,
        correction_sha256=_EXPECTED_CORRECTION_SHA256,
        supersession_sha256=_EXPECTED_SUPERSESSION_SHA256,
        asset_inventory_sha256=_EXPECTED_INVENTORY_SHA256,
        functional_episode_set_sha256=_EXPECTED_FUNCTIONAL_SHA256,
        runtime_selection_sha256=_EXPECTED_RUNTIME_SELECTION_SHA256,
        prefix_manifest_sha256=_EXPECTED_PREFIX_MANIFEST_SHA256,
        developer_dependency_lock_sha256=developer_lock.fingerprint(),
        condition_fingerprints_sha256=fingerprints.fingerprint(),
        functional_episode_ids=functional_ids,
        runtime_episode_ids=runtime_ids,
    )
    planning_identity = ExecutionManifestPlanningIdentity(
        execution_manifest_id="execution-manifest-auragateway-local-abc-v3-draft",
        execution_manifest_version="0.3.0-planning-draft",
        execution_manifest_status="planning_draft",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        review_sha256=review.fingerprint(),
        developer_dependency_lock_sha256=developer_lock.fingerprint(),
        condition_fingerprints_sha256=fingerprints.fingerprint(),
        benchmark_constitution_sha256=_BENCHMARK_CONSTITUTION_SHA256,
        execution_requirements_sha256=_EXECUTION_REQUIREMENTS_SHA256,
    )
    ledger = build_planned_run_ledger(
        functional_episode_ids=functional_ids,
        runtime_episode_ids=runtime_ids,
        fingerprints=fingerprints,
        planning_identity=planning_identity,
    )
    draft = ExecutionManifestDraft(
        identity=planning_identity,
        runtime_direction=runtime_direction,
        runtime_qualification_placeholder=runtime_placeholder,
        metric_mapping_plan_sha256=metric_mapping.fingerprint(),
        decoding_configuration_plan_sha256=runtime_placeholder.fingerprint(),
        planned_run_ledger_sha256=ledger.fingerprint(),
        frozen_asset_bindings=_frozen_asset_bindings(),
        unresolved_assets=_unresolved_assets(),
        trace_fields=_TRACE_FIELDS,
    )
    report = _build_preflight_report()
    manifest = _build_manifest(
        (
            ("condition-fingerprints", CONDITION_FINGERPRINTS_PATH, fingerprints),
            ("developer-dependency-lock", DEVELOPER_LOCK_PATH, developer_lock),
            ("execution-manifest-draft", DRAFT_PATH, draft),
            ("input", INPUT_PATH, planning_input),
            ("planned-run-ledger", LEDGER_PATH, ledger),
            ("preflight-report", REPORT_PATH, report),
        )
    )
    return GeneratedPreflightV3Bundle(
        developer_dependency_lock=developer_lock,
        condition_fingerprints=fingerprints,
        planning_input=planning_input,
        execution_manifest_draft=draft,
        planned_run_ledger=ledger,
        preflight_report=report,
        manifest=manifest,
    )


def _write_model(path: Path, model: LocalABCContract) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.canonical_json(), encoding="utf-8")


def write_preflight_v3_bundle(repo_root: Path, bundle: GeneratedPreflightV3Bundle) -> None:
    """Write seven canonical planning files; none authorize execution."""

    _write_model(repo_root / DEVELOPER_LOCK_PATH, bundle.developer_dependency_lock)
    _write_model(repo_root / CONDITION_FINGERPRINTS_PATH, bundle.condition_fingerprints)
    _write_model(repo_root / INPUT_PATH, bundle.planning_input)
    _write_model(repo_root / DRAFT_PATH, bundle.execution_manifest_draft)
    _write_model(repo_root / LEDGER_PATH, bundle.planned_run_ledger)
    _write_model(repo_root / REPORT_PATH, bundle.preflight_report)
    _write_model(repo_root / MANIFEST_PATH, bundle.manifest)


def validate_written_preflight_v3_bundle(
    repo_root: Path,
    expected: GeneratedPreflightV3Bundle,
) -> dict[str, object]:
    """Validate typed content and byte-for-byte deterministic regeneration."""

    expected_by_path: tuple[tuple[Path, LocalABCContract], ...] = (
        (DEVELOPER_LOCK_PATH, expected.developer_dependency_lock),
        (CONDITION_FINGERPRINTS_PATH, expected.condition_fingerprints),
        (INPUT_PATH, expected.planning_input),
        (DRAFT_PATH, expected.execution_manifest_draft),
        (LEDGER_PATH, expected.planned_run_ledger),
        (REPORT_PATH, expected.preflight_report),
        (MANIFEST_PATH, expected.manifest),
    )
    drift: list[str] = []
    for relative_path, model in expected_by_path:
        path = repo_root / relative_path
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError:
            drift.append(relative_path.as_posix())
            continue
        if actual != model.canonical_json():
            drift.append(relative_path.as_posix())
    if drift:
        raise FullABCLocalPreflightV3RebuildError(
            "GENERATED_PREFLIGHT_V3_DRIFT",
            "one or more generated preflight-v3 assets drifted",
            details=tuple(sorted(drift)),
        )
    return {
        "condition_fingerprints_sha256": expected.condition_fingerprints.fingerprint(),
        "developer_dependency_lock_sha256": (expected.developer_dependency_lock.fingerprint()),
        "execution_enabled": False,
        "execution_manifest_draft_sha256": expected.execution_manifest_draft.fingerprint(),
        "external_spend": 0,
        "manifest_sha256": expected.manifest.fingerprint(),
        "measured_execution_authorized": False,
        "next_gate": NEXT_GATE,
        "planned_run_ledger_sha256": expected.planned_run_ledger.fingerprint(),
        "total_trajectories": len(expected.planned_run_ledger.runs),
    }


def generate_preflight_v3(
    *,
    repo_root: Path,
    version_resolver: VersionResolver = importlib.metadata.version,
    python_version: str | None = None,
    python_implementation: str | None = None,
    verify_git_ancestry: bool = True,
) -> dict[str, object]:
    """Build, write, and verify the clean non-executable preflight-v3 lineage."""

    load_preflight_v3_implementation_plan(repo_root / IMPLEMENTATION_PLAN_PATH)
    bundle = build_preflight_v3_bundle(
        repo_root=repo_root,
        version_resolver=version_resolver,
        python_version=python_version,
        python_implementation=python_implementation,
        verify_git_ancestry=verify_git_ancestry,
    )
    write_preflight_v3_bundle(repo_root, bundle)
    return validate_written_preflight_v3_bundle(repo_root, bundle)


def verify_preflight_v3(
    *,
    repo_root: Path,
    version_resolver: VersionResolver = importlib.metadata.version,
    python_version: str | None = None,
    python_implementation: str | None = None,
    verify_git_ancestry: bool = True,
) -> dict[str, object]:
    """Regenerate in memory and compare with every committed planning artifact."""

    load_preflight_v3_implementation_plan(repo_root / IMPLEMENTATION_PLAN_PATH)
    bundle = build_preflight_v3_bundle(
        repo_root=repo_root,
        version_resolver=version_resolver,
        python_version=python_version,
        python_implementation=python_implementation,
        verify_git_ancestry=verify_git_ancestry,
    )
    return validate_written_preflight_v3_bundle(repo_root, bundle)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or verify the clean local-only preflight-v3 planning lineage."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI boundary with a metadata-safe JSON success or failure envelope."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            summary = generate_preflight_v3(repo_root=args.repo_root.resolve())
        else:
            summary = verify_preflight_v3(repo_root=args.repo_root.resolve())
    except FullABCLocalPreflightV3RebuildError as exc:
        envelope = FullABCLocalPreflightV3RebuildErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.canonical_json(), file=sys.stderr)
        return 1
    print(_canonical_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
