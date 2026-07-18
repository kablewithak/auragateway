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
EXECUTION_REQUEST_GIT_BLOB_SHA: Final = "38733262351846442ee55828a136e42016a7f54e"
EXECUTION_REQUEST_SHA256: Final = "dcef7e7243f4de16955bccdfc36dbd0194b51a602d1fc67f5c6fa375ca529e28"
EXECUTION_RUNNER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution.py"
)
EXECUTION_RUNNER_GIT_BLOB_SHA: Final = "921b5dcff84880f1c0e02bbc1164a7c73567d1fb"
EXECUTION_CONTRACTS_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py"
)
EXECUTION_CONTRACTS_GIT_BLOB_SHA: Final = "a82423c9cd5739d0d47e128bb5ce74493952ceb7"
EXECUTION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_v1.ipynb"
)
EXECUTION_NOTEBOOK_GIT_BLOB_SHA: Final = "b154168dcc300243b80cdf2fb4104d311195176e"
EXECUTION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_v1.md"
)
EXECUTION_RUNBOOK_GIT_BLOB_SHA: Final = "181a9bfb9a8984716f734389881477f8bee58e69"
WORKER_STARTUP_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
WORKER_STARTUP_PLAN_GIT_BLOB_SHA: Final = "4729f9668e3c331185fd7c4f191d2e171f5ecad8"

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
    VLLM_WHEEL = "vllm_wheel"


class DatasetArtifactFormat(StrEnum):
    """Supported offline artifact containers."""

    ZIP_ARCHIVE = "zip_archive"
    TAR_GZ_ARCHIVE = "tar_gz_archive"
    PYTHON_WHEEL = "python_wheel"


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
    mounted_path_required: Literal[True] = True
    sha256_required: Literal[True] = True
    network_fallback_permitted: Literal[False] = False
    materialized: Literal[False] = False


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
            DatasetRole.VLLM_WHEEL,
        )
        if roles != expected:
            raise ValueError("offline dataset roles drifted")
        if any(item.materialized for item in self.roles):
            raise ValueError("static dataset request cannot claim materialization")
        return self


class MaterializedDatasetEntry(LocalABCContract):
    """Exact Kaggle identity and runtime projection for one offline input."""

    role: DatasetRole
    kaggle_dataset_slug: str
    kaggle_dataset_version: int = Field(ge=1)
    mounted_path: str
    sha256: str
    network_fallback_permitted: Literal[False] = False

    @field_validator("kaggle_dataset_slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if _KAGGLE_SLUG_PATTERN.fullmatch(value) is None:
            raise ValueError("Kaggle dataset slugs must use owner/dataset syntax")
        return value

    @field_validator("mounted_path")
    @classmethod
    def validate_mounted_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or path.parts[:3] != ("/", "kaggle", "input"):
            raise ValueError("mounted paths must remain under /kaggle/input")
        if ".." in path.parts:
            raise ValueError("mounted paths must not traverse parent directories")
        return value

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
            DatasetRole.VLLM_WHEEL,
        )
        if roles != expected:
            raise ValueError("materialized dataset roles drifted")
        slugs = tuple(item.kaggle_dataset_slug for item in self.entries)
        if len(slugs) != len(set(slugs)):
            raise ValueError("materialized dataset slugs must be unique")
        paths = tuple(item.mounted_path for item in self.entries)
        if len(paths) != len(set(paths)):
            raise ValueError("materialized mounted paths must be unique")
        return self


class PortableDatasetManifestEntry(LocalABCContract):
    """Runtime-compatible manifest entry validated with POSIX path semantics."""

    role: Literal["harness_source", "model_artifacts", "vllm_wheel"]
    mounted_path: str
    sha256: str

    @field_validator("mounted_path")
    @classmethod
    def validate_mounted_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or path.parts[:3] != ("/", "kaggle", "input"):
            raise ValueError("runtime mounted paths must remain under /kaggle/input")
        if ".." in path.parts:
            raise ValueError("runtime mounted paths must not traverse parent directories")
        return value

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
        if roles != ("harness_source", "model_artifacts", "vllm_wheel"):
            raise ValueError("runtime dataset roles drifted")
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
        "dcef7e7243f4de16955bccdfc36dbd0194b51a602d1fc67f5c6fa375ca529e28"
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
