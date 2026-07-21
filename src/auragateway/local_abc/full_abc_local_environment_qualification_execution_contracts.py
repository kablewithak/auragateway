"""Typed contracts for the bounded environment-qualification execution package."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Final, Literal, Protocol, Self, runtime_checkable

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/+-]{3,240}$")
_FACTORY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{2,199}:[A-Za-z_][A-Za-z0-9_]{1,79}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "cab13a26fac319c9aac92a5b721b0206dc1791e8"
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_execution_review_v1.json"
)
REVIEW_GIT_BLOB_SHA: Final = "0b5fe5dc497080974b27e0720d0fab51baa77851"
AUTHORIZATION_ISSUANCE_REVIEW_GIT_BLOB_SHA: Final = "61590be7fe1d10e8e9b38405cf634f4a0cae3e31"
REVIEW_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_review.py"
)
REVIEW_SOURCE_GIT_BLOB_SHA: Final = "ebc1a28e97333f6f0a55d42f9c37b42701c75fa8"
STATIC_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_request.json"
)
STATIC_REQUEST_GIT_BLOB_SHA: Final = "ac2dc5a9082b9befb55c8ced8a7d58f926808987"
WORKER_STARTUP_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
WORKER_STARTUP_PLAN_GIT_BLOB_SHA: Final = "25392d5ec7cce9740688457a7aa91358039554eb"

RUNTIME_INTEGRATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_qualification_runtime_integration_review_v1.json"
)
RUNTIME_INTEGRATION_REVIEW_GIT_BLOB_SHA: Final = "a1fba29e34934b96f516c3cd966c3c6dfe31c1e1"

EXECUTION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_full_abc_environment_qualification_v1.ipynb")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_full_run_environment_qualification_v1.md")
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_execution_authorization_v1.json"
)
NEXT_GATE: Final = (
    "full_abc_local_full_run_environment_qualification_execution_authorization_review"
)
EXPECTED_RUFF_VERSION: Final = "0.15.21"

RUNTIME_EVIDENCE_PATHS: Final = (
    Path("data/evals/benchmark/environment-qualification-v1/cache_metric_capability_report.json"),
    Path("data/evals/benchmark/environment-qualification-v1/gpu_topology_report.json"),
    Path("data/evals/benchmark/environment-qualification-v1/kaggle_runtime_dependency_lock.json"),
    Path("data/evals/benchmark/environment-qualification-v1/manifest.json"),
    Path("data/evals/benchmark/environment-qualification-v1/model_identity_report.json"),
    Path("data/evals/benchmark/environment-qualification-v1/qualification_report.json"),
    Path("data/evals/benchmark/environment-qualification-v1/reset_capability_report.json"),
    Path("data/evals/benchmark/environment-qualification-v1/worker_health_report.json"),
)

SYNTHETIC_PROBE_IDS: Final = (
    "worker-1-cold-prefix",
    "worker-1-warm-prefix",
    "worker-2-cold-prefix",
    "worker-2-warm-prefix",
    "worker-1-post-reset-baseline",
    "worker-2-post-reset-baseline",
)

REQUIRED_RUNTIME_LOCK_FIELDS: Final = (
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

REQUIRED_METRIC_SEMANTICS: Final = (
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

REQUIRED_RESET_STEPS: Final = (
    "confirm_worker_process_exit",
    "confirm_worker_ports_closed",
    "record_reset_start",
    "restart_workers_from_bound_startup_plan",
    "revalidate_model_tokenizer_and_worker_identity",
    "verify_fresh_health_and_metric_baseline",
)

REQUIRED_STOP_CONDITIONS: Final = (
    "authorization_invalid",
    "cache_metric_unavailable",
    "credential_detected",
    "customer_data_detected",
    "dataset_manifest_drift",
    "dependency_lock_incomplete",
    "external_spend_nonzero",
    "gpu_topology_mismatch",
    "hidden_retry_detected",
    "hosted_provider_fallback_detected",
    "model_identity_mismatch",
    "model_request_budget_exhausted",
    "network_access_detected",
    "privacy_scan_failure",
    "reset_capability_unproven",
    "route_realization_mismatch",
    "runtime_adapter_drift",
    "tokenizer_identity_mismatch",
    "vllm_runtime_mismatch",
    "worker_health_failure",
    "worker_port_conflict",
)


class FullABCLocalEnvironmentQualificationExecutionError(RuntimeError):
    """Metadata-safe execution-package failure."""

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


class FullABCLocalEnvironmentQualificationExecutionErrorEnvelope(LocalABCContract):
    """Machine-readable error response without sensitive runtime payloads."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class ExecutionPackageStatus(StrEnum):
    """Lifecycle state of the static execution package."""

    STATIC_PACKAGE_GENERATED_AUTHORIZATION_BLOCKED = (
        "STATIC_PACKAGE_GENERATED_AUTHORIZATION_BLOCKED"
    )


class ProbePhase(StrEnum):
    """Synthetic qualification phase."""

    COLD_PREFIX = "cold_prefix"
    WARM_PREFIX = "warm_prefix"
    POST_RESET_BASELINE = "post_reset_baseline"


class MetricAvailabilityState(StrEnum):
    """Explicit availability state; unavailable never means zero."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE_NOT_ZERO = "UNAVAILABLE_NOT_ZERO"


class QualificationDecision(StrEnum):
    """Outcome of a completed qualification capture."""

    QUALIFIED = "QUALIFIED"
    FAILED = "FAILED"


class AuthorizationDecision(StrEnum):
    """Operational authority state."""

    AUTHORIZED = "AUTHORIZED"


class SourceAuthorityBinding(LocalABCContract):
    """Exact merged authority consumed by the static package."""

    authority_id: str
    path: str
    git_blob_sha: str

    @field_validator("authority_id")
    @classmethod
    def validate_authority_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authority IDs must use stable lowercase characters")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("authority paths must remain bounded")
        return value

    @field_validator("git_blob_sha")
    @classmethod
    def validate_git_blob_sha(cls, value: str) -> str:
        if _GIT_OBJECT_PATTERN.fullmatch(value) is None:
            raise ValueError("authority identity must be a lowercase Git object SHA")
        return value


class SyntheticProbeDefinition(LocalABCContract):
    """One fixed public-safe synthetic qualification probe."""

    probe_id: str
    worker_id: Literal["worker_1", "worker_2"]
    phase: ProbePhase
    sequence_index: int = Field(ge=1, le=6)
    prefix_template_id: Literal["synthetic-cache-prefix-v1"]
    suffix_template_id: str
    prior_probe_id: str | None = None
    max_output_tokens: Literal[32] = 32
    benchmark_payload_used: Literal[False] = False
    customer_data_used: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False

    @field_validator("probe_id", "suffix_template_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("probe identifiers must use stable lowercase characters")
        return value

    @field_validator("prior_probe_id")
    @classmethod
    def validate_prior_probe_id(cls, value: str | None) -> str | None:
        if value is not None and _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("prior probe IDs must use stable lowercase characters")
        return value


class QualificationProbeBudget(LocalABCContract):
    """Finite synthetic request budget for one qualification session."""

    maximum_kaggle_sessions: Literal[1] = 1
    maximum_workers: Literal[2] = 2
    maximum_model_requests: Literal[8] = 8
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    benchmark_episode_payloads_permitted: Literal[False] = False
    customer_payloads_permitted: Literal[False] = False
    hidden_retries_permitted: Literal[False] = False


class DatasetRoleRequirement(LocalABCContract):
    """One exact offline dataset role required before authorization."""

    role: Literal["harness_source", "model_artifacts", "vllm_runtime"]
    exact_manifest_entry_required: Literal[True] = True
    sha256_required: Literal[True] = True
    network_fallback_permitted: Literal[False] = False


class RuntimeEvidenceRequirement(LocalABCContract):
    """One deferred runtime evidence artifact and its schema identity."""

    evidence_id: str
    path: str
    schema_id: str
    generated: Literal[False] = False
    same_runtime_session_required: Literal[True] = True

    @field_validator("evidence_id", "schema_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence identifiers must use stable lowercase characters")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("runtime evidence paths must remain bounded")
        return value


class ExecutionPackageSafetyEnvelope(LocalABCContract):
    """Static package state with all operational authority disabled."""

    execution_package_generated: Literal[True] = True
    notebook_created: Literal[True] = True
    notebook_execution_performed: Literal[False] = False
    kaggle_session_started: Literal[False] = False
    dataset_attached: Literal[False] = False
    package_installation_performed: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    worker_start_authorized: Literal[False] = False
    worker_started: Literal[False] = False
    model_execution_performed: Literal[False] = False
    runtime_evidence_generated: Literal[False] = False
    environment_qualified: Literal[False] = False
    credential_accessed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False


class QualificationExecutionRequest(LocalABCContract):
    """Static request for a future separately authorized qualification run."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-full-abc-local-environment-qualification-execution-request-v1"]
    source_main_merge_commit: Literal["cab13a26fac319c9aac92a5b721b0206dc1791e8"]
    status: Literal[ExecutionPackageStatus.STATIC_PACKAGE_GENERATED_AUTHORIZATION_BLOCKED]
    source_authorities: tuple[SourceAuthorityBinding, ...]
    planned_trajectory_count: Literal[342] = 342
    probe_budget: QualificationProbeBudget
    synthetic_probes: tuple[SyntheticProbeDefinition, ...]
    dataset_roles: tuple[DatasetRoleRequirement, ...]
    required_runtime_lock_fields: tuple[str, ...]
    required_metric_semantics: tuple[str, ...]
    required_reset_steps: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    runtime_evidence: tuple[RuntimeEvidenceRequirement, ...]
    authorization_path: Literal[
        "benchmarks/local_abc/"
        "auragateway_full_abc_local_full_run_environment_qualification_"
        "execution_authorization_v1.json"
    ]
    runtime_factory_binding_required: Literal[True] = True
    evidence_written_only_after_validation: Literal[True] = True
    safety: ExecutionPackageSafetyEnvelope
    next_gate: Literal[
        "full_abc_local_full_run_environment_qualification_execution_authorization_review"
    ]

    @field_validator("source_authorities")
    @classmethod
    def validate_source_authorities(
        cls,
        value: tuple[SourceAuthorityBinding, ...],
    ) -> tuple[SourceAuthorityBinding, ...]:
        identities = tuple(item.authority_id for item in value)
        if len(identities) != len(set(identities)):
            raise ValueError("source authority IDs must be unique")
        if identities != tuple(sorted(identities)):
            raise ValueError("source authorities must be canonically sorted")
        return value

    @field_validator("synthetic_probes")
    @classmethod
    def validate_synthetic_probes(
        cls,
        value: tuple[SyntheticProbeDefinition, ...],
    ) -> tuple[SyntheticProbeDefinition, ...]:
        probe_ids = tuple(item.probe_id for item in value)
        indexes = tuple(item.sequence_index for item in value)
        if probe_ids != SYNTHETIC_PROBE_IDS:
            raise ValueError("synthetic qualification probe IDs drifted")
        if indexes != tuple(range(1, 7)):
            raise ValueError("synthetic qualification probe order drifted")
        return value

    @field_validator("dataset_roles")
    @classmethod
    def validate_dataset_roles(
        cls,
        value: tuple[DatasetRoleRequirement, ...],
    ) -> tuple[DatasetRoleRequirement, ...]:
        roles = tuple(item.role for item in value)
        if roles != ("harness_source", "model_artifacts", "vllm_runtime"):
            raise ValueError("offline dataset roles drifted")
        return value

    @field_validator("required_runtime_lock_fields")
    @classmethod
    def validate_runtime_lock_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != REQUIRED_RUNTIME_LOCK_FIELDS:
            raise ValueError("runtime dependency-lock field set drifted")
        return value

    @field_validator("required_metric_semantics")
    @classmethod
    def validate_metric_semantics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != REQUIRED_METRIC_SEMANTICS:
            raise ValueError("required metric semantic set drifted")
        return value

    @field_validator("required_reset_steps")
    @classmethod
    def validate_reset_steps(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != REQUIRED_RESET_STEPS:
            raise ValueError("required reset sequence drifted")
        return value

    @field_validator("stop_conditions")
    @classmethod
    def validate_stop_conditions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != REQUIRED_STOP_CONDITIONS:
            raise ValueError("qualification stop conditions drifted")
        return value

    @field_validator("runtime_evidence")
    @classmethod
    def validate_runtime_evidence(
        cls,
        value: tuple[RuntimeEvidenceRequirement, ...],
    ) -> tuple[RuntimeEvidenceRequirement, ...]:
        paths = tuple(item.path for item in value)
        expected = tuple(path.as_posix() for path in RUNTIME_EVIDENCE_PATHS)
        if paths != expected:
            raise ValueError("runtime evidence path set drifted")
        if any(item.generated for item in value):
            raise ValueError("static execution package cannot contain runtime evidence")
        return value


class DatasetManifestEntry(LocalABCContract):
    """One exact mounted input artifact for an authorized offline run."""

    role: Literal["harness_source", "model_artifacts", "vllm_runtime"]
    artifact_format: Literal[
        "source_tree_directory",
        "hugging_face_snapshot_directory",
        "python_wheelhouse_directory",
    ]
    mounted_path: str | None = None
    sha256: str
    runtime_output_directory: str | None = None
    resolution_lock_sha256: str | None = None
    runtime_manifest_sha256: str | None = None
    sha256_manifest_sha256: str | None = None
    materialization_receipt_sha256: str | None = None
    package_count: int | None = Field(default=None, ge=1)

    @field_validator("mounted_path")
    @classmethod
    def validate_mounted_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        posix_path = PurePosixPath(value)
        windows_path = PureWindowsPath(value)
        if ".." in posix_path.parts or ".." in windows_path.parts:
            raise ValueError("dataset entries must not traverse parent directories")
        if not (posix_path.is_absolute() or windows_path.is_absolute()):
            raise ValueError("dataset entries require absolute bounded mounted paths")
        return value

    @model_validator(mode="after")
    def validate_runtime_binding(self) -> Self:
        runtime_fields = (
            self.runtime_output_directory,
            self.resolution_lock_sha256,
            self.runtime_manifest_sha256,
            self.sha256_manifest_sha256,
            self.materialization_receipt_sha256,
            self.package_count,
        )
        if self.role == "vllm_runtime":
            if self.mounted_path is not None:
                raise ValueError("vLLM runtime must use bounded output-directory discovery")
            if any(value is None for value in runtime_fields):
                raise ValueError("vLLM runtime requires complete wheelhouse authority")
            if self.sha256 != self.sha256_manifest_sha256:
                raise ValueError("vLLM runtime digest must bind the checksum manifest")
            return self
        if self.mounted_path is None:
            raise ValueError("non-runtime dataset entries require a mounted path")
        if any(value is not None for value in runtime_fields):
            raise ValueError("runtime authority fields belong only to vllm_runtime")
        return self

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("dataset entry digest must be lowercase SHA-256")
        return value


class QualificationDatasetManifest(LocalABCContract):
    """Exact offline dataset manifest supplied by a future authorization gate."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: str
    entries: tuple[DatasetManifestEntry, DatasetManifestEntry, DatasetManifestEntry]
    network_access_permitted: Literal[False] = False
    credentials_present: Literal[False] = False
    customer_data_present: Literal[False] = False
    hosted_provider_inputs_present: Literal[False] = False

    @field_validator("manifest_id")
    @classmethod
    def validate_manifest_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("dataset manifest IDs must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_roles(self) -> Self:
        roles = tuple(item.role for item in self.entries)
        if roles != ("harness_source", "model_artifacts", "vllm_runtime"):
            raise ValueError("dataset manifest must preserve the exact role order")
        formats = tuple(item.artifact_format for item in self.entries)
        if formats != (
            "source_tree_directory",
            "hugging_face_snapshot_directory",
            "python_wheelhouse_directory",
        ):
            raise ValueError("dataset manifest artifact formats drifted")
        mounted_paths = tuple(
            item.mounted_path for item in self.entries if item.mounted_path is not None
        )
        if len(mounted_paths) != len(set(mounted_paths)):
            raise ValueError("dataset manifest mounted paths must be unique")
        return self


class QualificationRuntimeFactoryBinding(LocalABCContract):
    """Exact runtime adapter code identity supplied by authorization."""

    factory_path: str
    artifact_path: str
    artifact_sha256: str

    @field_validator("factory_path")
    @classmethod
    def validate_factory_path(cls, value: str) -> str:
        if _FACTORY_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime factory path must use module:function syntax")
        return value

    @field_validator("artifact_path")
    @classmethod
    def validate_artifact_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if _PATH_PATTERN.fullmatch(value) is None or path.is_absolute() or ".." in path.parts:
            raise ValueError(
                "runtime factory artifact path must be repository-relative and bounded"
            )
        return value

    @field_validator("artifact_sha256")
    @classmethod
    def validate_artifact_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime adapter digest must be lowercase SHA-256")
        return value


class QualificationExecutionAuthorization(LocalABCContract):
    """Time-bounded operational authority for one qualification session."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str
    decision: Literal[AuthorizationDecision.AUTHORIZED]
    source_main_merge_commit: Literal["211a10757999b1b110cb1d9df172938cf6ed7969"]
    request_sha256: str
    review_git_blob_sha: Literal["61590be7fe1d10e8e9b38405cf634f4a0cae3e31"]
    authorization_issuance_review_sha256: str
    materialization_record_sha256: str
    dataset_manifest_sha256: str
    runtime_factory: QualificationRuntimeFactoryBinding
    issued_at: datetime
    expires_at: datetime
    maximum_workers: Literal[2] = 2
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_model_requests: Literal[8] = 8
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    customer_data_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    network_access_permitted: Literal[False] = False
    external_spend: Literal[0] = 0
    operator_confirmation_recorded: Literal[True]
    measured_execution_authorized: Literal[False] = False

    @field_validator("authorization_id")
    @classmethod
    def validate_authorization_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization IDs must use stable lowercase characters")
        return value

    @field_validator(
        "request_sha256",
        "authorization_issuance_review_sha256",
        "materialization_record_sha256",
        "dataset_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization digests must be lowercase SHA-256")
        return value

    @field_validator("issued_at", "expires_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        if self.expires_at - self.issued_at > timedelta(minutes=240):
            raise ValueError("authorization window cannot exceed 240 minutes")
        return self


class RuntimeEvidenceBase(LocalABCContract):
    """Shared lineage and safety fields for one runtime evidence artifact."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    evidence_id: str
    runtime_session_id: str
    captured_at: datetime
    source_request_sha256: str
    dataset_manifest_sha256: str
    customer_data_used: Literal[False] = False
    credential_accessed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    external_spend: Literal[0] = 0

    @field_validator("evidence_id", "runtime_session_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime evidence IDs must use stable lowercase characters")
        return value

    @field_validator("captured_at")
    @classmethod
    def validate_captured_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("runtime evidence timestamps must be timezone-aware")
        return value

    @field_validator("source_request_sha256", "dataset_manifest_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime evidence digests must be lowercase SHA-256")
        return value


class KaggleRuntimeDependencyLock(RuntimeEvidenceBase):
    """Fresh runtime dependency and execution configuration lock."""

    evidence_id: Literal["kaggle-runtime-dependency-lock"]
    python_version: str
    torch_version: str
    cuda_version: str
    transformers_version: str
    vllm_module_version: str
    vllm_distribution_version: str
    runtime_output_directory: str
    runtime_resolution_lock_sha256: str
    runtime_manifest_sha256: str
    runtime_sha256_manifest_sha256: str
    runtime_materialization_receipt_sha256: str
    runtime_package_count: Literal[176]
    installation_executor: Literal["BASE_PIP_TARGET_DIRECTORY"]
    dependency_validation: Literal["CONTROLLED_TARGET_METADATA_AND_PACKAGING"]
    python_startup_policy: Literal["NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"]
    loader_policy: Literal["TARGET_NVIDIA_LIBRARIES_PREPENDED"]
    target_python_sha256: str
    attention_backend: str
    automatic_prefix_cache_configuration: Literal["enabled"]
    dtype: str
    quantization: str
    maximum_model_length: Literal[4096]
    output_token_budget: Literal[32]
    gpu_memory_utilization: Literal["0.85"]
    gpu_model: Literal["Tesla T4"]
    gpu_count: Literal[2]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    worker_startup_command_sha256: tuple[str, str]

    @field_validator(
        "python_version",
        "torch_version",
        "cuda_version",
        "transformers_version",
        "vllm_module_version",
        "vllm_distribution_version",
        "attention_backend",
        "dtype",
        "quantization",
    )
    @classmethod
    def validate_version_like(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime lock values must use stable version characters")
        return value

    @field_validator(
        "runtime_resolution_lock_sha256",
        "runtime_manifest_sha256",
        "runtime_sha256_manifest_sha256",
        "runtime_materialization_receipt_sha256",
        "target_python_sha256",
    )
    @classmethod
    def validate_runtime_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime identities must be lowercase SHA-256")
        return value

    @field_validator("worker_startup_command_sha256")
    @classmethod
    def validate_command_sha256(cls, value: tuple[str, str]) -> tuple[str, str]:
        if any(_SHA256_PATTERN.fullmatch(item) is None for item in value):
            raise ValueError("worker command identities must be lowercase SHA-256")
        return value


class GpuDeviceObservation(LocalABCContract):
    """One visible GPU identity."""

    gpu_index: Literal[0, 1]
    name: Literal["Tesla T4"]
    compute_capability: Literal["7.5"]
    memory_total_mib: int = Field(gt=0)


class GpuTopologyReport(RuntimeEvidenceBase):
    """Fresh two-GPU topology report."""

    evidence_id: Literal["gpu-topology-report"]
    devices: tuple[GpuDeviceObservation, GpuDeviceObservation]
    topology_matches_plan: Literal[True] = True

    @model_validator(mode="after")
    def validate_devices(self) -> Self:
        if tuple(item.gpu_index for item in self.devices) != (0, 1):
            raise ValueError("GPU topology must preserve indexes 0 and 1")
        return self


class ModelIdentityReport(RuntimeEvidenceBase):
    """Fresh model and tokenizer identity report."""

    evidence_id: Literal["model-identity-report"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_manifest_sha256: str
    config_sha256: str
    tokenizer_config_sha256: str
    tokenizer_json_sha256: str
    identity_matches_plan: Literal[True] = True

    @field_validator(
        "model_manifest_sha256",
        "config_sha256",
        "tokenizer_config_sha256",
        "tokenizer_json_sha256",
    )
    @classmethod
    def validate_identity_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("model identity digests must be lowercase SHA-256")
        return value


class WorkerHealthObservation(LocalABCContract):
    """One worker health and identity observation."""

    worker_id: Literal["worker_1", "worker_2"]
    gpu_index: Literal[0, 1]
    port: Literal[8001, 8002]
    health_status: Literal["healthy"]
    model_identity_matches: Literal[True] = True
    tokenizer_identity_matches: Literal[True] = True
    route_identity_matches: Literal[True] = True

    @model_validator(mode="after")
    def validate_topology(self) -> Self:
        expected = {"worker_1": (0, 8001), "worker_2": (1, 8002)}
        if (self.gpu_index, self.port) != expected[self.worker_id]:
            raise ValueError("worker health observation topology drifted")
        return self


class WorkerHealthReport(RuntimeEvidenceBase):
    """Fresh two-worker health report."""

    evidence_id: Literal["worker-health-report"]
    workers: tuple[WorkerHealthObservation, WorkerHealthObservation]
    all_workers_healthy: Literal[True] = True

    @model_validator(mode="after")
    def validate_workers(self) -> Self:
        if tuple(item.worker_id for item in self.workers) != ("worker_1", "worker_2"):
            raise ValueError("worker health report must preserve canonical worker order")
        return self


class MetricCapabilityObservation(LocalABCContract):
    """Mapped runtime metric capability for one required semantic."""

    semantic: str
    availability_state: MetricAvailabilityState
    raw_metric_name: str | None = None
    source_unit: str | None = None
    zero_fill_permitted: Literal[False] = False
    latency_only_inference_permitted: Literal[False] = False

    @field_validator("semantic")
    @classmethod
    def validate_semantic(cls, value: str) -> str:
        if value not in REQUIRED_METRIC_SEMANTICS:
            raise ValueError("metric semantic is not required by this qualification")
        return value

    @model_validator(mode="after")
    def validate_availability(self) -> Self:
        available = self.availability_state is MetricAvailabilityState.AVAILABLE
        if available and (self.raw_metric_name is None or self.source_unit is None):
            raise ValueError("available metric semantics require raw source and unit mappings")
        if not available and (self.raw_metric_name is not None or self.source_unit is not None):
            raise ValueError("unavailable metrics cannot claim source mappings")
        return self


class CacheMetricCapabilityReport(RuntimeEvidenceBase):
    """Fresh explicit metric capability report."""

    evidence_id: Literal["cache-metric-capability-report"]
    semantics: tuple[MetricCapabilityObservation, ...]
    all_required_metrics_available: Literal[True] = True
    cache_success_claim_permitted: Literal[False] = False

    @field_validator("semantics")
    @classmethod
    def validate_semantics(
        cls,
        value: tuple[MetricCapabilityObservation, ...],
    ) -> tuple[MetricCapabilityObservation, ...]:
        names = tuple(item.semantic for item in value)
        if names != REQUIRED_METRIC_SEMANTICS:
            raise ValueError("metric capability report semantic order drifted")
        if any(item.availability_state is not MetricAvailabilityState.AVAILABLE for item in value):
            raise ValueError("qualification requires all metric semantics to be available")
        return value


class ResetStepObservation(LocalABCContract):
    """One verified reset step."""

    step_id: str
    passed: Literal[True] = True
    evidence_sha256: str

    @field_validator("step_id")
    @classmethod
    def validate_step_id(cls, value: str) -> str:
        if value not in REQUIRED_RESET_STEPS:
            raise ValueError("reset step is not part of the required sequence")
        return value

    @field_validator("evidence_sha256")
    @classmethod
    def validate_evidence_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("reset evidence digest must be lowercase SHA-256")
        return value


class ResetCapabilityReport(RuntimeEvidenceBase):
    """Fresh full-restart reset capability report."""

    evidence_id: Literal["reset-capability-report"]
    steps: tuple[ResetStepObservation, ...]
    namespace_only_reset_used: Literal[False] = False
    reset_capability_verified: Literal[True] = True

    @field_validator("steps")
    @classmethod
    def validate_steps(
        cls,
        value: tuple[ResetStepObservation, ...],
    ) -> tuple[ResetStepObservation, ...]:
        if tuple(item.step_id for item in value) != REQUIRED_RESET_STEPS:
            raise ValueError("reset capability step order drifted")
        return value


class ProbeObservation(LocalABCContract):
    """Metadata-only outcome for one synthetic model request."""

    probe_id: str
    worker_id: Literal["worker_1", "worker_2"]
    request_index: int = Field(ge=1, le=8)
    output_tokens: int = Field(ge=1, le=32)
    route_realized: Literal[True] = True
    raw_prompt_logged: Literal[False] = False
    raw_output_logged: Literal[False] = False

    @field_validator("probe_id")
    @classmethod
    def validate_probe_id(cls, value: str) -> str:
        if value not in SYNTHETIC_PROBE_IDS:
            raise ValueError("probe observation ID is not in the fixed synthetic set")
        return value


class QualificationReport(RuntimeEvidenceBase):
    """Final validated decision for one qualification session."""

    evidence_id: Literal["qualification-report"]
    decision: QualificationDecision
    model_request_count: int = Field(ge=0, le=8)
    probes: tuple[ProbeObservation, ...]
    stop_conditions_triggered: tuple[str, ...] = ()
    environment_qualified: bool
    measured_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if self.decision is QualificationDecision.QUALIFIED:
            if self.environment_qualified is not True:
                raise ValueError("qualified decisions must set environment_qualified")
            if self.stop_conditions_triggered:
                raise ValueError("qualified decisions cannot contain stop conditions")
            if self.model_request_count != 6 or len(self.probes) != 6:
                raise ValueError("qualified decisions require all six synthetic probes")
        elif self.environment_qualified:
            raise ValueError("failed decisions cannot qualify the environment")
        return self


class QualificationManifestEntry(LocalABCContract):
    """One canonical runtime evidence file identity."""

    evidence_id: str
    path: str
    sha256: str

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest evidence IDs must use stable lowercase characters")
        return value

    @field_validator("path")
    @classmethod
    def validate_manifest_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("manifest evidence paths must remain bounded")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_manifest_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest evidence digest must be lowercase SHA-256")
        return value


class QualificationManifest(RuntimeEvidenceBase):
    """Canonical inventory of one complete runtime evidence bundle."""

    evidence_id: Literal["qualification-manifest"]
    entries: tuple[QualificationManifestEntry, ...]
    evidence_bundle_complete: Literal[True] = True
    environment_qualified: Literal[True] = True
    measured_execution_authorized: Literal[False] = False

    @field_validator("entries")
    @classmethod
    def validate_entries(
        cls,
        value: tuple[QualificationManifestEntry, ...],
    ) -> tuple[QualificationManifestEntry, ...]:
        expected_paths = tuple(
            path.as_posix() for path in RUNTIME_EVIDENCE_PATHS if path.name != "manifest.json"
        )
        paths = tuple(item.path for item in value)
        if paths != expected_paths:
            raise ValueError("qualification manifest entry order drifted")
        return value


class QualificationRuntimeCapture(LocalABCContract):
    """In-memory all-or-nothing runtime capture returned by an adapter."""

    dependency_lock: KaggleRuntimeDependencyLock
    gpu_topology: GpuTopologyReport
    model_identity: ModelIdentityReport
    worker_health: WorkerHealthReport
    metric_capability: CacheMetricCapabilityReport
    reset_capability: ResetCapabilityReport
    qualification_report: QualificationReport

    @model_validator(mode="after")
    def validate_shared_lineage(self) -> Self:
        items: tuple[RuntimeEvidenceBase, ...] = (
            self.dependency_lock,
            self.gpu_topology,
            self.model_identity,
            self.worker_health,
            self.metric_capability,
            self.reset_capability,
            self.qualification_report,
        )
        session_ids = {item.runtime_session_id for item in items}
        request_digests = {item.source_request_sha256 for item in items}
        dataset_digests = {item.dataset_manifest_sha256 for item in items}
        if len(session_ids) != 1:
            raise ValueError("runtime evidence must come from one fresh runtime session")
        if len(request_digests) != 1 or len(dataset_digests) != 1:
            raise ValueError("runtime evidence lineage digests must match")
        if self.qualification_report.decision is not QualificationDecision.QUALIFIED:
            raise ValueError("only a fully qualified capture may be committed")
        return self


@runtime_checkable
class QualificationRuntimeAdapter(Protocol):
    """Injected runtime boundary used only after external authorization."""

    def capture(
        self,
        request: QualificationExecutionRequest,
        dataset_manifest: QualificationDatasetManifest,
    ) -> QualificationRuntimeCapture:
        """Perform one bounded capture and return validated in-memory evidence."""
