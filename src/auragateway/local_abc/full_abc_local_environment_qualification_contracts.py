"""Typed contracts for static full-run environment-qualification tooling."""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_environment_qualification_cu129_runtime import (
    CONTROLLED_BOOTSTRAP,
    DEPENDENCY_VALIDATION,
    EXPECTED_PACKAGE_COUNT,
    INSTALLATION_EXECUTOR,
    LOADER_POLICY,
    PYTHON_STARTUP_POLICY,
    RUNTIME_OUTPUT_DIRECTORY,
    TARGET_INTERPRETER_TOKEN,
    TARGET_RUNTIME_ROOT_TOKEN,
    TARGET_SITE_PACKAGES_TOKEN,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/+-]{3,240}$")
_SAFE_ARG_PATTERN = re.compile(r"^[A-Za-z0-9._/:+=-]{1,240}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "7be3361fbbfcd14cebee96b4832fe4c800702f2e"
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_review_v1.json"
)
REVIEW_GIT_BLOB_SHA: Final = "344a24f18fc32a7b945ce761f6420947a53bcc24"
REVIEW_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_review.py"
)
REVIEW_SOURCE_GIT_BLOB_SHA: Final = "fdd3022815bda785f171749a6e3a877f374aa635"
IMPLEMENTATION_PLAN_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_implementation_v1.json"
)
OUTPUT_ROOT: Final = Path("data/evals/benchmark/environment-qualification-v1")
QUALIFICATION_REQUEST_PATH: Final = OUTPUT_ROOT / "qualification_request.json"
WORKER_STARTUP_PLAN_PATH: Final = OUTPUT_ROOT / "worker_startup_plan.json"
NEXT_GATE: Final = "full_abc_local_full_run_environment_qualification_execution_review"
EXPECTED_RUFF_VERSION: Final = "0.15.21"

_REQUIRED_RUNTIME_LOCK_FIELDS: Final = (
    "attention_backend",
    "automatic_prefix_cache_configuration",
    "cuda_version",
    "dtype",
    "gpu_count",
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
    "vllm_module_version",
    "runtime_output_directory",
    "runtime_resolution_lock_sha256",
    "runtime_manifest_sha256",
    "runtime_sha256_manifest_sha256",
    "runtime_materialization_receipt_sha256",
    "runtime_package_count",
    "installation_executor",
    "dependency_validation",
    "python_startup_policy",
    "loader_policy",
    "target_python_sha256",
    "worker_startup_command_sha256",
)

_REQUIRED_METRIC_SEMANTICS: Final = (
    "cached_prefix_tokens",
    "metric_availability_state",
    "newly_computed_prefill_tokens",
    "prefill_duration_ms",
    "prompt_tokens",
    "realized_route",
    "request_latency_ms",
    "reset_state",
    "time_to_first_token_ms",
    "worker_id",
)

_REQUIRED_RESET_STEPS: Final = (
    "confirm_worker_process_exit",
    "confirm_worker_ports_closed",
    "record_reset_start",
    "restart_workers_from_bound_startup_plan",
    "revalidate_model_tokenizer_and_worker_identity",
    "verify_fresh_health_and_metric_baseline",
)

_REQUIRED_STOP_CONDITIONS: Final = (
    "cache_metric_unavailable",
    "credential_detected",
    "customer_data_detected",
    "dependency_lock_incomplete",
    "external_spend_nonzero",
    "gpu_topology_mismatch",
    "hosted_provider_fallback_detected",
    "model_identity_mismatch",
    "privacy_scan_failure",
    "reset_capability_unproven",
    "route_realization_mismatch",
    "tokenizer_identity_mismatch",
    "vllm_runtime_mismatch",
    "worker_health_failure",
    "worker_port_conflict",
)

_RUNTIME_EVIDENCE_PATHS: Final = (
    OUTPUT_ROOT / "cache_metric_capability_report.json",
    OUTPUT_ROOT / "gpu_topology_report.json",
    OUTPUT_ROOT / "kaggle_runtime_dependency_lock.json",
    OUTPUT_ROOT / "manifest.json",
    OUTPUT_ROOT / "model_identity_report.json",
    OUTPUT_ROOT / "qualification_report.json",
    OUTPUT_ROOT / "reset_capability_report.json",
    OUTPUT_ROOT / "worker_health_report.json",
)


class FullABCLocalEnvironmentQualificationImplementationError(RuntimeError):
    """Expected metadata-safe failure for static qualification tooling."""

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


class FullABCLocalEnvironmentQualificationErrorEnvelope(LocalABCContract):
    """Machine-readable CLI failure without secrets or raw payloads."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class StaticQualificationStatus(StrEnum):
    """Lifecycle state of the implementation-only qualification package."""

    STATIC_ASSETS_GENERATED_EXECUTION_BLOCKED = "STATIC_ASSETS_GENERATED_EXECUTION_BLOCKED"
    STATIC_PLAN_NOT_EXECUTED = "STATIC_PLAN_NOT_EXECUTED"


class MetricAvailabilityState(StrEnum):
    """Explicit handling for metrics that do not exist in a runtime."""

    REQUIRED_FRESH_CAPTURE = "REQUIRED_FRESH_CAPTURE"
    UNAVAILABLE_NOT_ZERO = "UNAVAILABLE_NOT_ZERO"


class QualificationSafetyEnvelope(LocalABCContract):
    """Fail-closed static implementation boundary."""

    static_assets_generated: Literal[True] = True
    runtime_evidence_generated: Literal[False] = False
    kaggle_session_started: Literal[False] = False
    dataset_attached: Literal[False] = False
    package_installation_performed: Literal[False] = False
    notebook_created: Literal[False] = False
    notebook_execution_performed: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    worker_start_authorized: Literal[False] = False
    worker_started: Literal[False] = False
    model_execution_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    customer_data_used: Literal[False] = False
    hosted_provider_required: Literal[False] = False
    paid_fallback_permitted: Literal[False] = False
    external_spend: Literal[0] = 0
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False


class RuntimeEvidenceRequirement(LocalABCContract):
    """One runtime artifact forbidden from static generation."""

    artifact_id: str
    path: str
    generation_stage: Literal["qualification_execution"] = "qualification_execution"
    generated: Literal[False] = False
    requires_fresh_runtime_session: Literal[True] = True

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime artifact IDs must use stable lowercase characters")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("runtime artifact paths must remain bounded")
        return value


class MetricRequirement(LocalABCContract):
    """One required metric semantic with explicit missing-data behavior."""

    semantic: str
    expected_unit: str
    source_kind: Literal["runtime_metric", "runtime_metadata"]
    availability_before_execution: Literal[MetricAvailabilityState.REQUIRED_FRESH_CAPTURE] = (
        MetricAvailabilityState.REQUIRED_FRESH_CAPTURE
    )
    missing_metric_state: Literal[MetricAvailabilityState.UNAVAILABLE_NOT_ZERO] = (
        MetricAvailabilityState.UNAVAILABLE_NOT_ZERO
    )
    zero_fill_permitted: Literal[False] = False
    latency_only_cache_inference_permitted: Literal[False] = False

    @field_validator("semantic", "expected_unit")
    @classmethod
    def validate_stable_text(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("metric fields must use stable lowercase characters")
        return value


class EnvironmentBinding(LocalABCContract):
    """One non-secret environment variable required by a startup plan."""

    name: Literal[
        "CUDA_VISIBLE_DEVICES",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "PYTHONNOUSERSITE",
    ]
    value: Literal["0", "1"]


class WorkerStartupCommand(LocalABCContract):
    """Canonical non-shell argv for one isolated local vLLM worker."""

    worker_id: Literal["worker_1", "worker_2"]
    gpu_index: Literal[0, 1]
    host: Literal["127.0.0.1"] = "127.0.0.1"
    port: Literal[8001, 8002]
    health_endpoint: Literal["/health"] = "/health"
    models_endpoint: Literal["/v1/models"] = "/v1/models"
    transport_endpoint: Literal["/v1/chat/completions"] = "/v1/chat/completions"
    environment: tuple[
        EnvironmentBinding,
        EnvironmentBinding,
        EnvironmentBinding,
        EnvironmentBinding,
    ]
    command_argv: tuple[str, ...]
    command_sha256: str
    shell_execution_permitted: Literal[False] = False
    launch_authorized: Literal[False] = False

    @field_validator("command_argv")
    @classmethod
    def validate_command_argv(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) < 20:
            raise ValueError("worker startup command is incomplete")
        if any(not item or "\x00" in item or len(item) > 4096 for item in value):
            raise ValueError("worker startup command contains unsafe arguments")
        expected_prefix = (
            TARGET_INTERPRETER_TOKEN,
            "-S",
            "-c",
            CONTROLLED_BOOTSTRAP,
            TARGET_RUNTIME_ROOT_TOKEN,
            TARGET_SITE_PACKAGES_TOKEN,
            "vllm.entrypoints.openai.api_server",
        )
        if value[: len(expected_prefix)] != expected_prefix:
            raise ValueError("worker startup command must use controlled target Python")
        forbidden = {
            "--api-key",
            "--token",
            "groq",
            "openrouter",
            "curl",
            "wget",
            "pip",
        }
        lowered = {item.lower() for item in value}
        if lowered & forbidden:
            raise ValueError("worker startup command contains provider or install behavior")
        return value

    @field_validator("command_sha256")
    @classmethod
    def validate_command_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("worker startup command requires lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_topology_and_binding(self) -> Self:
        expected = {
            "worker_1": (0, 8001, "0"),
            "worker_2": (1, 8002, "1"),
        }
        expected_gpu, expected_port, expected_visible_gpu = expected[self.worker_id]
        if self.gpu_index != expected_gpu or self.port != expected_port:
            raise ValueError("worker topology drifted")
        env = {item.name: item.value for item in self.environment}
        if env != {
            "CUDA_VISIBLE_DEVICES": expected_visible_gpu,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "PYTHONNOUSERSITE": "1",
        }:
            raise ValueError("worker environment must be deterministic and offline")
        required_pairs = {
            "--host": self.host,
            "--port": str(self.port),
            "--model": "Qwen/Qwen2.5-0.5B-Instruct",
            "--revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "--tokenizer-revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "--served-model-name": "local-qwen2.5-0.5b-instruct",
        }
        argv = self.command_argv
        for flag, expected_value in required_pairs.items():
            try:
                actual_value = argv[argv.index(flag) + 1]
            except (ValueError, IndexError) as exc:
                raise ValueError(f"worker startup command is missing {flag}") from exc
            if actual_value != expected_value:
                raise ValueError(f"worker startup command drifted for {flag}")
        if "--enable-prefix-caching" not in argv:
            raise ValueError("worker startup command must enable prefix caching")
        canonical = json.dumps(
            list(self.command_argv),
            ensure_ascii=True,
            separators=(",", ":"),
        )
        expected_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if self.command_sha256 != expected_sha:
            raise ValueError("worker startup command hash does not match its canonical payload")
        return self


class WorkerStartupPlan(LocalABCContract):
    """Static two-worker startup plan that cannot launch a process."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    plan_id: Literal["auragateway-full-abc-worker-startup-plan-v1"]
    source_main_merge_commit: Literal["7be3361fbbfcd14cebee96b4832fe4c800702f2e"]
    source_review_path: Literal[
        "benchmarks/local_abc/"
        "auragateway_full_abc_local_full_run_environment_qualification_review_v1.json"
    ]
    source_review_git_blob_sha: Literal["344a24f18fc32a7b945ce761f6420947a53bcc24"]
    status: Literal[StaticQualificationStatus.STATIC_PLAN_NOT_EXECUTED]
    runtime_entrypoint: Literal["vllm.entrypoints.openai.api_server"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    runtime_integration: dict[str, object]
    workers: tuple[WorkerStartupCommand, WorkerStartupCommand]
    required_prelaunch_checks: tuple[str, ...]
    requires_fresh_runtime_dependency_lock: Literal[True] = True
    historical_runtime_versions_reusable: Literal[False] = False
    launch_authorized: Literal[False] = False
    next_gate: Literal["full_abc_local_full_run_environment_qualification_execution_review"]

    @field_validator("required_prelaunch_checks")
    @classmethod
    def validate_prelaunch_checks(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = (
            "credential_absence_verified",
            "customer_data_absence_verified",
            "gpu_topology_matches_plan",
            "model_and_tokenizer_identity_available",
            "ports_8001_and_8002_closed",
            "runtime_dependency_lock_captured",
            "runtime_resolution_lock_verified",
            "runtime_checksum_manifest_verified",
            "target_python_startup_controlled",
            "target_nvidia_loader_precedence_verified",
        )
        if value != expected:
            raise ValueError("worker prelaunch checks drifted")
        return value

    @model_validator(mode="after")
    def validate_workers(self) -> Self:
        if tuple(worker.worker_id for worker in self.workers) != ("worker_1", "worker_2"):
            raise ValueError("startup plan must preserve worker order")
        if len({worker.gpu_index for worker in self.workers}) != 2:
            raise ValueError("startup plan requires independent GPUs")
        if len({worker.port for worker in self.workers}) != 2:
            raise ValueError("startup plan requires distinct ports")
        expected_runtime = {
            "runtime_output_directory": RUNTIME_OUTPUT_DIRECTORY,
            "package_count": EXPECTED_PACKAGE_COUNT,
            "installation_executor": INSTALLATION_EXECUTOR,
            "dependency_validation": DEPENDENCY_VALIDATION,
            "python_startup_policy": PYTHON_STARTUP_POLICY,
            "loader_policy": LOADER_POLICY,
            "vllm_distribution": "0.19.1",
            "torch_distribution": "2.10.0+cu129",
            "transformers_distribution": "5.5.3",
        }
        if self.runtime_integration != expected_runtime:
            raise ValueError("worker startup runtime integration drifted")
        return self


class QualificationRequest(LocalABCContract):
    """Static request for a later, separately authorized qualification session."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-full-abc-environment-qualification-request-v1"]
    source_main_merge_commit: Literal["7be3361fbbfcd14cebee96b4832fe4c800702f2e"]
    source_review_path: Literal[
        "benchmarks/local_abc/"
        "auragateway_full_abc_local_full_run_environment_qualification_review_v1.json"
    ]
    source_review_git_blob_sha: Literal["344a24f18fc32a7b945ce761f6420947a53bcc24"]
    status: Literal[StaticQualificationStatus.STATIC_ASSETS_GENERATED_EXECUTION_BLOCKED]
    target_environment: Literal["kaggle_t4_x2"]
    execution_backend: Literal["local_vllm"]
    planned_trajectory_count: Literal[342] = 342
    fresh_runtime_session_required: Literal[True] = True
    historical_authorization_reusable: Literal[False] = False
    developer_dependency_lock_reusable_as_runtime_lock: Literal[False] = False
    required_runtime_lock_fields: tuple[str, ...]
    runtime_evidence_requirements: tuple[RuntimeEvidenceRequirement, ...]
    metric_requirements: tuple[MetricRequirement, ...]
    required_reset_steps: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    worker_startup_plan_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
    ]
    safety: QualificationSafetyEnvelope
    next_gate: Literal["full_abc_local_full_run_environment_qualification_execution_review"]

    @field_validator("required_runtime_lock_fields")
    @classmethod
    def validate_runtime_lock_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _REQUIRED_RUNTIME_LOCK_FIELDS:
            raise ValueError("runtime dependency lock fields drifted")
        return value

    @field_validator("required_reset_steps")
    @classmethod
    def validate_reset_steps(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _REQUIRED_RESET_STEPS:
            raise ValueError("reset steps drifted")
        return value

    @field_validator("stop_conditions")
    @classmethod
    def validate_stop_conditions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _REQUIRED_STOP_CONDITIONS:
            raise ValueError("qualification stop conditions drifted")
        return value

    @model_validator(mode="after")
    def validate_runtime_evidence_and_metrics(self) -> Self:
        paths = tuple(Path(item.path) for item in self.runtime_evidence_requirements)
        if paths != _RUNTIME_EVIDENCE_PATHS:
            raise ValueError("runtime evidence requirements drifted")
        semantics = tuple(item.semantic for item in self.metric_requirements)
        if semantics != _REQUIRED_METRIC_SEMANTICS:
            raise ValueError("metric requirements drifted")
        return self


class EnvironmentQualificationImplementationPlan(LocalABCContract):
    """Canonical implementation decision for the static qualification package."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    implementation_id: Literal[
        "auragateway-full-abc-local-environment-qualification-implementation-v1"
    ]
    source_main_merge_commit: Literal["7be3361fbbfcd14cebee96b4832fe4c800702f2e"]
    review_path: Literal[
        "benchmarks/local_abc/"
        "auragateway_full_abc_local_full_run_environment_qualification_review_v1.json"
    ]
    review_git_blob_sha: Literal["344a24f18fc32a7b945ce761f6420947a53bcc24"]
    review_source_git_blob_sha: Literal["fdd3022815bda785f171749a6e3a877f374aa635"]
    generated_static_assets: tuple[str, str]
    deferred_runtime_evidence: tuple[str, ...]
    execution_enabled: Literal[False] = False
    qualification_claim_permitted: Literal[False] = False
    next_gate: Literal["full_abc_local_full_run_environment_qualification_execution_review"]

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        expected_static = (
            QUALIFICATION_REQUEST_PATH.as_posix(),
            WORKER_STARTUP_PLAN_PATH.as_posix(),
        )
        if self.generated_static_assets != expected_static:
            raise ValueError("generated static asset scope drifted")
        expected_runtime = tuple(path.as_posix() for path in _RUNTIME_EVIDENCE_PATHS)
        if self.deferred_runtime_evidence != expected_runtime:
            raise ValueError("deferred runtime evidence scope drifted")
        return self


class EnvironmentQualificationStaticBundle(LocalABCContract):
    """Deterministic static bundle written by the implementation command."""

    qualification_request: QualificationRequest
    worker_startup_plan: WorkerStartupPlan

    @model_validator(mode="after")
    def validate_cross_bindings(self) -> Self:
        if (
            self.qualification_request.worker_startup_plan_path
            != WORKER_STARTUP_PLAN_PATH.as_posix()
        ):
            raise ValueError("qualification request points to the wrong startup plan")
        if self.qualification_request.source_review_git_blob_sha != (
            self.worker_startup_plan.source_review_git_blob_sha
        ):
            raise ValueError("static assets must bind the same review identity")
        return self


def canonical_command_sha256(command_argv: tuple[str, ...]) -> str:
    """Hash one canonical non-shell target-runtime worker argv."""

    encoded = json.dumps(
        list(command_argv),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_sha256(value: str) -> str:
    """Validate one lowercase SHA-256 used by tests and generators."""

    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError("value must be lowercase SHA-256")
    return value


def validate_git_object(value: str) -> str:
    """Validate one lowercase Git object identity."""

    if _GIT_OBJECT_PATTERN.fullmatch(value) is None:
        raise ValueError("value must be a lowercase Git object SHA")
    return value
