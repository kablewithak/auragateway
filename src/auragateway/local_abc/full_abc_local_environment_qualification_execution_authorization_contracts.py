"""Typed contracts for the qualification-execution authorization input package."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/+-]{3,240}$")
_KAGGLE_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}/[a-z0-9][a-z0-9_-]{1,79}$")
_FACTORY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{2,199}:[A-Za-z_][A-Za-z0-9_]{1,79}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "2d6e20a952a14df806d7166c7de276405fa4c7e7"
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_review_v1.json"
)
REVIEW_GIT_BLOB_SHA: Final = "d41ae54d31c9a36ca5e942b6a57bbdfd9858a6ec"
REVIEW_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_execution_authorization_review.py"
)
REVIEW_SOURCE_GIT_BLOB_SHA: Final = "593757e84bb69342f29806e62c8d250a40fb950f"
EXECUTION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
)
EXECUTION_REQUEST_GIT_BLOB_SHA: Final = "325de0033a647caa4e5f6b311619e7ea29ede89e"
EXECUTION_REQUEST_SHA256: Final = "7b0080429246f6def3c1ac28b8a677a2ed7e29ccf318690d9309ed98ff179ba0"
EXECUTION_RUNNER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution.py"
)
EXECUTION_RUNNER_GIT_BLOB_SHA: Final = "ea4fa2df31ad326be2d294581286faaa7bd9b9a6"
ARTIFACT_IDENTITY_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_artifact_identity.py"
)
ARTIFACT_IDENTITY_GIT_BLOB_SHA: Final = "60189de0e17c52db52610dd4b32a1babc59033ab"
EXECUTION_CONTRACTS_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py"
)
EXECUTION_CONTRACTS_GIT_BLOB_SHA: Final = "eb526e33d529f03c23b542b2a7058971ffc23d76"
EXECUTION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_v1.ipynb"
)
EXECUTION_NOTEBOOK_GIT_BLOB_SHA: Final = "58ea94e02e5333a07f614e7e00fbbb201e287ece"
EXECUTION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_v1.md"
)
EXECUTION_RUNBOOK_GIT_BLOB_SHA: Final = "fde4ba09f3eab4fd119ee181755f4e05d42d9620"
WORKER_STARTUP_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
WORKER_STARTUP_PLAN_GIT_BLOB_SHA: Final = "25392d5ec7cce9740688457a7aa91358039554eb"
RUNTIME_INTEGRATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_qualification_runtime_integration_review_v1.json"
)
RUNTIME_INTEGRATION_REVIEW_GIT_BLOB_SHA: Final = "a1fba29e34934b96f516c3cd966c3c6dfe31c1e1"

AUTHORIZATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_authorization_request.json"
)
DATASET_MANIFEST_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest_request.json"
)
MATERIALIZATION_RECORD_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json"
)
MATERIALIZED_DATASET_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
RUNTIME_ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
RUNTIME_ADAPTER_GIT_BLOB_SHA: Final = "46c82e83d05bb80b48c05dd33fd9c4c8c771721d"
RUNTIME_MODULE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_cu129_runtime.py"
)
RUNTIME_MODULE_GIT_BLOB_SHA: Final = "0ed94ef12de8d5bd1d40e39e05fed49238e76544"
RUNTIME_FACTORY_PATH: Final = (
    "auragateway.local_abc."
    "full_abc_local_environment_qualification_kaggle_runtime_adapter:"
    "create_runtime_adapter"
)
NEXT_GATE: Final = (
    "full_abc_local_full_run_environment_qualification_execution_authorization_issuance_review"
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


class AuthorizationPackageError(RuntimeError):
    """Metadata-safe failure while building authorization inputs."""

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


class AuthorizationPackageErrorEnvelope(LocalABCContract):
    """Machine-readable safe error response."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class AuthorizationPackageStatus(StrEnum):
    """Static package lifecycle state."""

    INPUT_PACKAGE_GENERATED_ISSUANCE_BLOCKED = "INPUT_PACKAGE_GENERATED_ISSUANCE_BLOCKED"


class DatasetMaterializationState(StrEnum):
    """Dataset preparation state before exact Kaggle identities exist."""

    REQUESTED_NOT_MATERIALIZED = "REQUESTED_NOT_MATERIALIZED"


class DatasetRole(StrEnum):
    """Exact offline input roles required for qualification."""

    HARNESS_SOURCE = "harness_source"
    MODEL_ARTIFACTS = "model_artifacts"
    VLLM_RUNTIME = "vllm_runtime"


class DatasetArtifactFormat(StrEnum):
    """Supported offline artifact representations."""

    SOURCE_TREE_DIRECTORY = "source_tree_directory"
    ZIP_ARCHIVE = "zip_archive"
    HUGGING_FACE_SNAPSHOT_DIRECTORY = "hugging_face_snapshot_directory"
    PYTHON_WHEELHOUSE_DIRECTORY = "python_wheelhouse_directory"


class SourceAuthorityBinding(LocalABCContract):
    """One exact merged authority consumed by this package."""

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


class DatasetRoleMaterializationRequest(LocalABCContract):
    """One requested Kaggle input whose exact identity is still unresolved."""

    role: DatasetRole
    artifact_format: DatasetArtifactFormat
    required_content: str = Field(min_length=12, max_length=360)
    dataset_slug_required: Literal[True] = True
    dataset_version_required: Literal[True] = True
    mounted_path_required: bool = True
    sha256_required: Literal[True] = True
    network_fallback_permitted: Literal[False] = False
    materialized: Literal[False] = False

    @model_validator(mode="after")
    def validate_materialization_boundary(self) -> Self:
        if self.role is DatasetRole.VLLM_RUNTIME:
            if self.mounted_path_required:
                raise ValueError("vLLM runtime must use output-directory discovery")
            return self
        if not self.mounted_path_required:
            raise ValueError("non-runtime dataset roles require exact mounted paths")
        return self


class OfflineDatasetManifestRequest(LocalABCContract):
    """Static request to materialize exact offline Kaggle inputs after merge."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal[
        "auragateway-full-abc-local-environment-qualification-offline-dataset-request-v1"
    ]
    source_main_merge_commit: Literal["2d6e20a952a14df806d7166c7de276405fa4c7e7"]
    status: Literal[DatasetMaterializationState.REQUESTED_NOT_MATERIALIZED]
    source_authorities: tuple[SourceAuthorityBinding, ...]
    roles: tuple[
        DatasetRoleMaterializationRequest,
        DatasetRoleMaterializationRequest,
        DatasetRoleMaterializationRequest,
    ]
    source_main_commit_must_follow_implementation_merge: Literal[True] = True
    exact_dataset_slug_required: Literal[True] = True
    exact_dataset_version_required: Literal[True] = True
    exact_mounted_path_required: Literal[True] = True
    exact_sha256_required: Literal[True] = True
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    hosted_provider_inputs_permitted: Literal[False] = False
    network_fallback_permitted: Literal[False] = False
    materialized_manifest_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
    ]
    materialized_manifest_generated: Literal[False] = False
    next_gate: Literal[
        "full_abc_local_full_run_environment_qualification_execution_authorization_issuance_review"
    ]

    @field_validator("source_authorities")
    @classmethod
    def validate_source_authorities(
        cls,
        value: tuple[SourceAuthorityBinding, ...],
    ) -> tuple[SourceAuthorityBinding, ...]:
        identifiers = tuple(item.authority_id for item in value)
        if identifiers != tuple(sorted(identifiers)):
            raise ValueError("source authorities must be canonically sorted")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("source authority IDs must be unique")
        return value

    @model_validator(mode="after")
    def validate_roles(self) -> Self:
        roles = tuple(item.role for item in self.roles)
        expected = (
            DatasetRole.HARNESS_SOURCE,
            DatasetRole.MODEL_ARTIFACTS,
            DatasetRole.VLLM_RUNTIME,
        )
        if roles != expected:
            raise ValueError("offline dataset roles drifted")
        if any(item.materialized for item in self.roles):
            raise ValueError("static dataset request cannot claim materialization")
        return self


class MaterializedDatasetEntry(LocalABCContract):
    """Exact Kaggle identity and runtime projection for one offline input."""

    role: DatasetRole
    artifact_format: DatasetArtifactFormat
    kaggle_dataset_slug: str
    kaggle_dataset_version: int = Field(ge=1)
    mounted_path: str | None = None
    sha256: str
    runtime_output_directory: str | None = None
    resolution_lock_sha256: str | None = None
    runtime_manifest_sha256: str | None = None
    sha256_manifest_sha256: str | None = None
    materialization_receipt_sha256: str | None = None
    package_count: int | None = Field(default=None, ge=1)
    network_fallback_permitted: Literal[False] = False

    @field_validator("kaggle_dataset_slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if _KAGGLE_SLUG_PATTERN.fullmatch(value) is None:
            raise ValueError("Kaggle dataset slugs must use owner/dataset syntax")
        return value

    @field_validator("mounted_path")
    @classmethod
    def validate_mounted_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        path = PurePosixPath(value)
        if not path.is_absolute() or path.parts[:3] != ("/", "kaggle", "input"):
            raise ValueError("mounted paths must remain under /kaggle/input")
        if ".." in path.parts:
            raise ValueError("mounted paths must not traverse parent directories")
        return value

    @model_validator(mode="after")
    def validate_runtime_binding(self) -> Self:
        runtime_values = (
            self.runtime_output_directory,
            self.resolution_lock_sha256,
            self.runtime_manifest_sha256,
            self.sha256_manifest_sha256,
            self.materialization_receipt_sha256,
            self.package_count,
        )
        if self.role is DatasetRole.VLLM_RUNTIME:
            if self.mounted_path is not None:
                raise ValueError("vLLM runtime uses bounded output-directory discovery")
            if any(value is None for value in runtime_values):
                raise ValueError("vLLM runtime materialization authority is incomplete")
            if self.sha256 != self.sha256_manifest_sha256:
                raise ValueError("vLLM runtime digest must bind its checksum manifest")
            return self
        if self.mounted_path is None:
            raise ValueError("non-runtime materialized inputs require a mounted path")
        if any(value is not None for value in runtime_values):
            raise ValueError("runtime authority fields belong only to vllm_runtime")
        return self

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("materialized dataset digests must be lowercase SHA-256")
        return value


class MaterializedOfflineDatasetRecord(LocalABCContract):
    """Canonical provenance record retaining Kaggle slug and version identity."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: str
    harness_source_commit: str
    entries: tuple[
        MaterializedDatasetEntry,
        MaterializedDatasetEntry,
        MaterializedDatasetEntry,
    ]
    runtime_manifest_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
    ]
    runtime_manifest_sha256: str
    network_access_permitted: Literal[False] = False
    credentials_present: Literal[False] = False
    customer_data_present: Literal[False] = False
    hosted_provider_inputs_present: Literal[False] = False

    @field_validator("record_id")
    @classmethod
    def validate_record_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("materialization record IDs must use stable lowercase characters")
        return value

    @field_validator("harness_source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _GIT_OBJECT_PATTERN.fullmatch(value) is None:
            raise ValueError("harness source commit must be a lowercase Git object SHA")
        return value

    @field_validator("runtime_manifest_sha256")
    @classmethod
    def validate_manifest_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime manifest digest must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_roles(self) -> Self:
        roles = tuple(item.role for item in self.entries)
        expected = (
            DatasetRole.HARNESS_SOURCE,
            DatasetRole.MODEL_ARTIFACTS,
            DatasetRole.VLLM_RUNTIME,
        )
        if roles != expected:
            raise ValueError("materialized dataset roles drifted")
        formats = tuple(item.artifact_format for item in self.entries)
        expected_formats = (
            DatasetArtifactFormat.SOURCE_TREE_DIRECTORY,
            DatasetArtifactFormat.HUGGING_FACE_SNAPSHOT_DIRECTORY,
            DatasetArtifactFormat.PYTHON_WHEELHOUSE_DIRECTORY,
        )
        if formats != expected_formats:
            raise ValueError("materialized dataset artifact formats drifted")
        slugs = tuple(item.kaggle_dataset_slug for item in self.entries)
        if len(slugs) != len(set(slugs)):
            raise ValueError("materialized dataset slugs must be unique")
        paths = tuple(item.mounted_path for item in self.entries if item.mounted_path is not None)
        if len(paths) != len(set(paths)):
            raise ValueError("materialized mounted paths must be unique")
        return self


class PortableDatasetManifestEntry(LocalABCContract):
    """Runtime-compatible manifest entry validated with POSIX path semantics."""

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
        path = PurePosixPath(value)
        if not path.is_absolute() or path.parts[:3] != ("/", "kaggle", "input"):
            raise ValueError("runtime mounted paths must remain under /kaggle/input")
        if ".." in path.parts:
            raise ValueError("runtime mounted paths must not traverse parent directories")
        return value

    @model_validator(mode="after")
    def validate_runtime_binding(self) -> Self:
        runtime_values = (
            self.runtime_output_directory,
            self.resolution_lock_sha256,
            self.runtime_manifest_sha256,
            self.sha256_manifest_sha256,
            self.materialization_receipt_sha256,
            self.package_count,
        )
        if self.role == "vllm_runtime":
            if self.mounted_path is not None:
                raise ValueError("vLLM runtime uses bounded output-directory discovery")
            if any(value is None for value in runtime_values):
                raise ValueError("portable vLLM runtime authority is incomplete")
            if self.sha256 != self.sha256_manifest_sha256:
                raise ValueError("vLLM runtime digest must bind its checksum manifest")
            return self
        if self.mounted_path is None:
            raise ValueError("non-runtime manifest entries require a mounted path")
        if any(value is not None for value in runtime_values):
            raise ValueError("runtime authority fields belong only to vllm_runtime")
        return self

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime dataset digests must be lowercase SHA-256")
        return value


class PortableQualificationDatasetManifest(LocalABCContract):
    """Cross-platform projection consumed by the existing Kaggle execution harness."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: str
    entries: tuple[
        PortableDatasetManifestEntry,
        PortableDatasetManifestEntry,
        PortableDatasetManifestEntry,
    ]
    network_access_permitted: Literal[False] = False
    credentials_present: Literal[False] = False
    customer_data_present: Literal[False] = False
    hosted_provider_inputs_present: Literal[False] = False

    @field_validator("manifest_id")
    @classmethod
    def validate_manifest_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime manifest IDs must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_roles(self) -> Self:
        roles = tuple(item.role for item in self.entries)
        if roles != ("harness_source", "model_artifacts", "vllm_runtime"):
            raise ValueError("runtime dataset roles drifted")
        formats = tuple(item.artifact_format for item in self.entries)
        if formats != (
            "source_tree_directory",
            "hugging_face_snapshot_directory",
            "python_wheelhouse_directory",
        ):
            raise ValueError("runtime dataset artifact formats drifted")
        return self


class RuntimeAdapterImplementationBinding(LocalABCContract):
    """Static identity and constraints for the concrete Kaggle runtime adapter."""

    artifact_path: Literal[
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
    ]
    factory_path: Literal[
        "auragateway.local_abc."
        "full_abc_local_environment_qualification_kaggle_runtime_adapter:"
        "create_runtime_adapter"
    ]
    protocol_path: Literal[
        "auragateway.local_abc."
        "full_abc_local_environment_qualification_execution_contracts:"
        "QualificationRuntimeAdapter"
    ]
    startup_plan_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
    ]
    loopback_only: Literal[True] = True
    frozen_startup_argv_required: Literal[True] = True
    model_request_retries_permitted: Literal[False] = False
    network_fallback_permitted: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    transactional_evidence_commit_owned_by_harness: Literal[True] = True
    adapter_generated: Literal[True] = True
    adapter_executed: Literal[False] = False
    artifact_sha256_deferred_to_issuance_review: Literal[True] = True


class AuthorizationPackageSafetyEnvelope(LocalABCContract):
    """Implementation-only safety state with operational authority disabled."""

    authorization_package_generated: Literal[True] = True
    final_authorization_generated: Literal[False] = False
    materialized_dataset_manifest_generated: Literal[False] = False
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
    measured_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False


class QualificationAuthorizationRequest(LocalABCContract):
    """Static request for a later exact authorization-issuance review."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal[
        "auragateway-full-abc-local-environment-qualification-authorization-request-v1"
    ]
    source_main_merge_commit: Literal["2d6e20a952a14df806d7166c7de276405fa4c7e7"]
    status: Literal[AuthorizationPackageStatus.INPUT_PACKAGE_GENERATED_ISSUANCE_BLOCKED]
    source_authorities: tuple[SourceAuthorityBinding, ...]
    execution_request_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
    ]
    execution_request_sha256: Literal[
        "7b0080429246f6def3c1ac28b8a677a2ed7e29ccf318690d9309ed98ff179ba0"
    ]
    dataset_manifest_request_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest_request.json"
    ]
    dataset_manifest_request_sha256: str
    materialization_record_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/"
        "offline_dataset_materialization_record.json"
    ]
    materialization_record_sha256_required: Literal[True] = True
    runtime_dataset_manifest_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
    ]
    runtime_dataset_manifest_sha256_required: Literal[True] = True
    exact_kaggle_slug_and_version_binding_required: Literal[True] = True
    issuance_review_git_blob_sha_required: Literal[True] = True
    runtime_adapter: RuntimeAdapterImplementationBinding
    final_authorization_path: Literal[
        "benchmarks/local_abc/"
        "auragateway_full_abc_local_full_run_environment_qualification_"
        "execution_authorization_v1.json"
    ]
    operator_confirmation_required: Literal[True] = True
    maximum_authorization_window_minutes: Literal[240] = 240
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_workers: Literal[2] = 2
    maximum_model_requests: Literal[8] = 8
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    customer_data_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    network_access_permitted: Literal[False] = False
    external_spend: Literal[0] = 0
    final_authorization_generated: Literal[False] = False
    safety: AuthorizationPackageSafetyEnvelope
    next_gate: Literal[
        "full_abc_local_full_run_environment_qualification_execution_authorization_issuance_review"
    ]

    @field_validator("source_authorities")
    @classmethod
    def validate_source_authorities(
        cls,
        value: tuple[SourceAuthorityBinding, ...],
    ) -> tuple[SourceAuthorityBinding, ...]:
        identifiers = tuple(item.authority_id for item in value)
        if identifiers != tuple(sorted(identifiers)):
            raise ValueError("source authorities must be canonically sorted")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("source authority IDs must be unique")
        return value

    @field_validator("dataset_manifest_request_sha256")
    @classmethod
    def validate_dataset_request_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("dataset request identity must be lowercase SHA-256")
        return value
