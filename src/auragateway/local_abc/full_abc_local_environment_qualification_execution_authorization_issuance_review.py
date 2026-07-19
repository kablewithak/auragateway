"""Review the final authorization-issuance implementation boundary."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_contracts as auth_contracts,
)
from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization import (
    build_portable_runtime_manifest,
)

_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/+-]{3,240}$")
_FACTORY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{2,199}:[A-Za-z_][A-Za-z0-9_]{1,79}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "58e448228abcf9b83e1a6d165094bbec61dcf02c"
HARNESS_SOURCE_COMMIT: Final = "4dfd799590195d842f2382bb882fba9b8c4e2422"
REVIEW_ID: Final = (
    "auragateway-full-abc-local-environment-qualification-execution-"
    "authorization-issuance-review-v1"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_issuance_review_v1.json"
)
NEXT_GATE: Final = (
    "full_abc_local_full_run_environment_qualification_execution_"
    "authorization_issuance_implementation"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

_AUTHORIZATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_authorization_request.json"
)
_AUTHORIZATION_CONTRACTS_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_execution_authorization_contracts.py"
)
_AUTHORIZATION_PACKAGE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_authorization.py"
)
_AUTHORIZATION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_authorization_v1.md"
)
_EXECUTION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_v1.ipynb"
)
_EXECUTION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
)
_MATERIALIZATION_RECORD_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json"
)
_RUNTIME_ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
_RUNTIME_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
_WORKER_STARTUP_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)

_RUNTIME_FACTORY_PATH: Final = (
    "auragateway.local_abc."
    "full_abc_local_environment_qualification_kaggle_runtime_adapter:"
    "create_runtime_adapter"
)
_RUNTIME_PROTOCOL_PATH: Final = (
    "auragateway.local_abc."
    "full_abc_local_environment_qualification_execution_contracts:"
    "QualificationRuntimeAdapter"
)

_MATERIALIZATION_RECORD_SHA256: Final = (
    "705881978f5a612a4bc1d131fdc96508fd8fb4a78c73e384df6968eb54bbb7a3"
)
_RUNTIME_MANIFEST_SHA256: Final = "ddc1e1fc9e5ba61212dafad8d7196eb17699b6103083b6f9678dce83ca0a74c2"
_RUNTIME_ADAPTER_SHA256: Final = "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"
_EXECUTION_REQUEST_SHA256: Final = (
    "dcef7e7243f4de16955bccdfc36dbd0194b51a602d1fc67f5c6fa375ca529e28"
)

_AUTHORITY_ROWS: Final = (
    (
        "authorization-contracts",
        "typed authorization input and provenance contracts",
        _AUTHORIZATION_CONTRACTS_PATH,
        "3dae83e83d40a4d7993d58c76ecdd219a5e1b5d0",
        "d0e64aa09de0b5ec69afb39ce9e64bd129ca2c49ad83e1026ff6d06d02ddf3d6",
    ),
    (
        "authorization-package",
        "repository-native authorization input validation package",
        _AUTHORIZATION_PACKAGE_PATH,
        "6e3983119dcb497db29e715f1ab6e31d381c7c4e",
        "5bdcf15fb5a2dc9fa92959a000eceb944a177a9184fe3d407366e29a0de904a7",
    ),
    (
        "authorization-request",
        "frozen request for bounded final authorization issuance",
        _AUTHORIZATION_REQUEST_PATH,
        "1490dbed934fd484b9ba276b61674f4ab191ae5b",
        "671b593f90af0d4a8331764f90a61b090738fb39bd7026f39236ef7eb519496e",
    ),
    (
        "authorization-runbook",
        "operator boundary and offline issuance-input procedure",
        _AUTHORIZATION_RUNBOOK_PATH,
        "117ad673ca02e1c3209e13447ae68c7556d13e21",
        "1a113cd9cdd4331d1b653eebccbf4e900b83944be2c5082b47f82a61b7d78672",
    ),
    (
        "execution-notebook",
        "deterministic unexecuted Kaggle qualification surface",
        _EXECUTION_NOTEBOOK_PATH,
        "1fd89440e46250862596f7202382e9ba5c70230a",
        "195f3e09eb36bb4d099753cd70806f158080a547d1807993396bda883c16adf6",
    ),
    (
        "execution-request",
        "canonical execution request and hard probe budget",
        _EXECUTION_REQUEST_PATH,
        "38733262351846442ee55828a136e42016a7f54e",
        _EXECUTION_REQUEST_SHA256,
    ),
    (
        "materialization-record",
        "exact Kaggle resource provenance with immutable versions",
        _MATERIALIZATION_RECORD_PATH,
        "dcde807c0d6bdcffef63a536bd318477ee1fe420",
        _MATERIALIZATION_RECORD_SHA256,
    ),
    (
        "runtime-adapter",
        "exact offline runtime adapter implementation",
        _RUNTIME_ADAPTER_PATH,
        "2f832c487e338d6233fa774dc6a4069f31cfcc30",
        _RUNTIME_ADAPTER_SHA256,
    ),
    (
        "runtime-manifest",
        "portable exact runtime projection of materialized inputs",
        _RUNTIME_MANIFEST_PATH,
        "16c52f8da5e7bdac006c2fd37292293230caf010",
        _RUNTIME_MANIFEST_SHA256,
    ),
    (
        "worker-startup-plan",
        "frozen loopback-only two-worker startup plan",
        _WORKER_STARTUP_PLAN_PATH,
        "4729f9668e3c331185fd7c4f191d2e171f5ecad8",
        "e0385a61f877be2913c4be87813e52ccff50378e65c95160d425a4abce1b3fde",
    ),
)

_EXPECTED_MATERIALIZATION_ENTRIES: Final = (
    (
        "harness_source",
        "source_tree_directory",
        "kabomolefe/auragateway-qualification-harness-4dfd799-v1",
        1,
        "/kaggle/input/datasets/kabomolefe/auragateway-qualification-harness-4dfd799-v1",
        "2ba96af01e093708b413bece444d5e440a076b4d60ac1ed9932d78c13ab3915a",
    ),
    (
        "model_artifacts",
        "hugging_face_snapshot_directory",
        "kabomolefe/auragateway-qwen2-5-0-5b-offline-v1",
        1,
        "/kaggle/input/datasets/kabomolefe/"
        "auragateway-qwen2-5-0-5b-offline-v1/"
        "auragateway-qwen2.5-0.5b-instruct-"
        "7ae557604adf67be50417f59c2c2f167def9a775/"
        "hf_home/hub/models--Qwen--Qwen2.5-0.5B-Instruct/"
        "snapshots/7ae557604adf67be50417f59c2c2f167def9a775",
        "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa",
    ),
    (
        "vllm_wheel",
        "python_wheel",
        "kabomolefe/auragateway-vllm-wheel-recovery-v1",
        1,
        "/kaggle/input/notebooks/kabomolefe/"
        "auragateway-vllm-wheel-recovery-v1/"
        "auragateway_vllm_wheels_v1/"
        "vllm-0.25.1+cu129-cp38-abi3-manylinux_2_28_x86_64.whl",
        "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431",
    ),
)

_IMPLEMENTATION_ARTIFACTS: Final = (
    (
        "authorization-issuance-runbook",
        "docs/runbooks/local_abc_full_run_environment_qualification_authorization_issuance_v1.md",
        "create",
    ),
    (
        "authorization-issuance-runner",
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_authorization_issuance.py",
        "create",
    ),
    (
        "authorization-issuance-tests",
        "tests/unit/local_abc/"
        "test_full_abc_local_environment_qualification_execution_authorization_issuance.py",
        "create",
    ),
    (
        "execution-authorization-contracts",
        "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py",
        "update",
    ),
    (
        "execution-tests",
        "tests/unit/local_abc/test_full_abc_local_environment_qualification_execution.py",
        "update",
    ),
    (
        "final-authorization-artifact",
        FINAL_AUTHORIZATION_PATH.as_posix(),
        "generate",
    ),
)


class AuthorizationIssuanceReviewError(RuntimeError):
    """Expected metadata-safe failure for the authorization-issuance review."""

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


class IssuanceAuthorityDisposition(StrEnum):
    """How one PR 109 artifact governs the issuance implementation."""

    CURRENT_AUTHORITY = "current_authority"


class IssuanceReviewAuthorityBinding(LocalABCContract):
    """One exact PR 109 authority for authorization issuance."""

    binding_id: str
    role: str = Field(min_length=12, max_length=240)
    source_locator: str
    git_blob_sha: str
    file_sha256: str
    disposition: Literal[IssuanceAuthorityDisposition.CURRENT_AUTHORITY]

    @field_validator("binding_id")
    @classmethod
    def validate_binding_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authority binding IDs must use stable lowercase characters")
        return value

    @field_validator("source_locator")
    @classmethod
    def validate_source_locator(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("authority source locators must remain bounded")
        return value

    @field_validator("git_blob_sha")
    @classmethod
    def validate_git_blob_sha(cls, value: str) -> str:
        if _GIT_OBJECT_PATTERN.fullmatch(value) is None:
            raise ValueError("authority identity must be a lowercase Git object SHA")
        return value

    @field_validator("file_sha256")
    @classmethod
    def validate_file_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("authority content identity must be lowercase SHA-256")
        return value


class MaterializationEntryReviewBinding(LocalABCContract):
    """Exact immutable identity for one required offline input."""

    role: Literal["harness_source", "model_artifacts", "vllm_wheel"]
    artifact_format: Literal[
        "source_tree_directory",
        "hugging_face_snapshot_directory",
        "python_wheel",
    ]
    kaggle_dataset_slug: str
    kaggle_dataset_version: Literal[1] = 1
    mounted_path: str
    sha256: str
    network_fallback_permitted: Literal[False] = False

    @field_validator("kaggle_dataset_slug")
    @classmethod
    def validate_kaggle_dataset_slug(cls, value: str) -> str:
        if "/" not in value or value.startswith("/") or value.endswith("/"):
            raise ValueError("Kaggle resource slugs must use owner/resource syntax")
        return value

    @field_validator("mounted_path")
    @classmethod
    def validate_mounted_path(cls, value: str) -> str:
        if not value.startswith("/kaggle/input/") or ".." in Path(value).parts:
            raise ValueError("mounted paths must remain under /kaggle/input")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("materialized input identity must be lowercase SHA-256")
        return value


class MaterializationReviewBinding(LocalABCContract):
    """Hash-linked provenance required before authorization can be implemented."""

    harness_source_commit: Literal["4dfd799590195d842f2382bb882fba9b8c4e2422"]
    materialization_record_path: str
    materialization_record_sha256: str
    runtime_manifest_path: str
    runtime_manifest_sha256: str
    entries: tuple[
        MaterializationEntryReviewBinding,
        MaterializationEntryReviewBinding,
        MaterializationEntryReviewBinding,
    ]
    network_access_permitted: Literal[False] = False
    credentials_present: Literal[False] = False
    customer_data_present: Literal[False] = False
    hosted_provider_inputs_present: Literal[False] = False

    @field_validator("materialization_record_path", "runtime_manifest_path")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("materialization authority paths must remain bounded")
        return value

    @field_validator("materialization_record_sha256", "runtime_manifest_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("materialization identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_exact_binding(self) -> Self:
        observed = tuple(
            (
                item.role,
                item.artifact_format,
                item.kaggle_dataset_slug,
                item.kaggle_dataset_version,
                item.mounted_path,
                item.sha256,
            )
            for item in self.entries
        )
        if observed != _EXPECTED_MATERIALIZATION_ENTRIES:
            raise ValueError("materialization entry bindings drifted")
        if self.materialization_record_sha256 != _MATERIALIZATION_RECORD_SHA256:
            raise ValueError("materialization record identity drifted")
        if self.runtime_manifest_sha256 != _RUNTIME_MANIFEST_SHA256:
            raise ValueError("runtime manifest identity drifted")
        return self


class RuntimeFactoryReviewBinding(LocalABCContract):
    """Exact runtime adapter identity and execution constraints."""

    artifact_path: str
    artifact_git_blob_sha: str
    artifact_sha256: str
    factory_path: str
    protocol_path: str
    startup_plan_path: str
    loopback_only: Literal[True] = True
    frozen_startup_argv_required: Literal[True] = True
    model_request_retries_permitted: Literal[False] = False
    network_fallback_permitted: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    adapter_execution_performed: Literal[False] = False

    @field_validator("artifact_path", "startup_plan_path")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("runtime binding paths must remain bounded")
        return value

    @field_validator("artifact_git_blob_sha")
    @classmethod
    def validate_git_blob_sha(cls, value: str) -> str:
        if _GIT_OBJECT_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime adapter Git identity must be lowercase")
        return value

    @field_validator("artifact_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime adapter identity must be lowercase SHA-256")
        return value

    @field_validator("factory_path", "protocol_path")
    @classmethod
    def validate_factory_paths(cls, value: str) -> str:
        if _FACTORY_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime symbols must use module:function syntax")
        return value

    @model_validator(mode="after")
    def validate_exact_binding(self) -> Self:
        if self.artifact_path != _RUNTIME_ADAPTER_PATH.as_posix():
            raise ValueError("runtime adapter path drifted")
        if self.artifact_git_blob_sha != "2f832c487e338d6233fa774dc6a4069f31cfcc30":
            raise ValueError("runtime adapter Git identity drifted")
        if self.artifact_sha256 != _RUNTIME_ADAPTER_SHA256:
            raise ValueError("runtime adapter SHA-256 drifted")
        if self.factory_path != _RUNTIME_FACTORY_PATH:
            raise ValueError("runtime factory path drifted")
        if self.protocol_path != _RUNTIME_PROTOCOL_PATH:
            raise ValueError("runtime protocol path drifted")
        if self.startup_plan_path != _WORKER_STARTUP_PLAN_PATH.as_posix():
            raise ValueError("worker startup plan path drifted")
        return self


class AuthorizationIssuanceBudget(LocalABCContract):
    """Hard operational limits that a future authorization must retain."""

    maximum_authorization_window_minutes: Literal[240] = 240
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_workers: Literal[2] = 2
    maximum_model_requests: Literal[8] = 8
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class AuthorizationIssuancePrivacyEnvelope(LocalABCContract):
    """Privacy and network boundary for the future qualification session."""

    network_access_permitted: Literal[False] = False
    network_fallback_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    hosted_provider_inputs_permitted: Literal[False] = False
    hosted_provider_calls_permitted: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False


class AuthorizationIssuanceImplementationArtifact(LocalABCContract):
    """One exact file permitted in the next implementation gate."""

    artifact_id: str
    path: str
    change_mode: Literal["create", "update", "generate"]
    created_in_this_review: Literal[False] = False
    operational_authority_created_in_this_review: Literal[False] = False

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("implementation artifact IDs must use stable lowercase characters")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("implementation artifact paths must remain bounded")
        return value


class AuthorizationIssuanceDecision(LocalABCContract):
    """Review decision that defers the actual authorization decision."""

    final_authorization_path: str
    final_authorization_generated: Literal[False] = False
    issuance_decision_deferred: Literal[True] = True
    issuance_requires_separate_implementation: Literal[True] = True
    operator_confirmation_required: Literal[True] = True
    issued_at_deferred_to_operator_confirmation: Literal[True] = True
    expires_at_limited_by_review_budget: Literal[True] = True
    execution_request_sha256: str
    materialization_record_sha256: str
    runtime_manifest_sha256: str
    runtime_adapter_sha256: str
    issuance_review_git_blob_sha_required: Literal[True] = True
    measured_execution_authorized: Literal[False] = False

    @field_validator("final_authorization_path")
    @classmethod
    def validate_final_authorization_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("final authorization path must remain bounded")
        return value

    @field_validator(
        "execution_request_sha256",
        "materialization_record_sha256",
        "runtime_manifest_sha256",
        "runtime_adapter_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization bindings must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_exact_bindings(self) -> Self:
        if self.execution_request_sha256 != _EXECUTION_REQUEST_SHA256:
            raise ValueError("execution request identity drifted")
        if self.materialization_record_sha256 != _MATERIALIZATION_RECORD_SHA256:
            raise ValueError("materialization record identity drifted")
        if self.runtime_manifest_sha256 != _RUNTIME_MANIFEST_SHA256:
            raise ValueError("runtime manifest identity drifted")
        if self.runtime_adapter_sha256 != _RUNTIME_ADAPTER_SHA256:
            raise ValueError("runtime adapter identity drifted")
        return self


class AuthorizationIssuanceReviewSafetyEnvelope(LocalABCContract):
    """Review-only state with all operational activity prohibited."""

    review_artifact_generated: Literal[True] = True
    final_authorization_generated: Literal[False] = False
    authorization_issuance_performed: Literal[False] = False
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


class FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview(LocalABCContract):
    """Review authorizing implementation, not issuance, of final authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-full-abc-local-environment-qualification-execution-"
        "authorization-issuance-review-v1"
    ]
    source_main_merge_commit: Literal["58e448228abcf9b83e1a6d165094bbec61dcf02c"]
    harness_source_commit: Literal["4dfd799590195d842f2382bb882fba9b8c4e2422"]
    lifecycle_before: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    lifecycle_after: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    decision: Literal["APPROVED_FOR_AUTHORIZATION_ISSUANCE_IMPLEMENTATION"]
    authority_bindings: tuple[IssuanceReviewAuthorityBinding, ...]
    materialization: MaterializationReviewBinding
    runtime_factory: RuntimeFactoryReviewBinding
    budget: AuthorizationIssuanceBudget
    privacy: AuthorizationIssuancePrivacyEnvelope
    implementation_artifacts: tuple[AuthorizationIssuanceImplementationArtifact, ...]
    authorization_issuance: AuthorizationIssuanceDecision
    safety: AuthorizationIssuanceReviewSafetyEnvelope
    next_gate: Literal[
        "full_abc_local_full_run_environment_qualification_execution_"
        "authorization_issuance_implementation"
    ]

    @field_validator("authority_bindings")
    @classmethod
    def validate_authority_bindings(
        cls,
        value: tuple[IssuanceReviewAuthorityBinding, ...],
    ) -> tuple[IssuanceReviewAuthorityBinding, ...]:
        identifiers = tuple(item.binding_id for item in value)
        if identifiers != tuple(sorted(identifiers)):
            raise ValueError("authority bindings must be canonically sorted")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("authority binding IDs must be unique")
        observed = tuple(
            (
                item.binding_id,
                item.role,
                Path(item.source_locator),
                item.git_blob_sha,
                item.file_sha256,
            )
            for item in value
        )
        if observed != _AUTHORITY_ROWS:
            raise ValueError("authorization-issuance authority bindings drifted")
        return value

    @field_validator("implementation_artifacts")
    @classmethod
    def validate_implementation_artifacts(
        cls,
        value: tuple[AuthorizationIssuanceImplementationArtifact, ...],
    ) -> tuple[AuthorizationIssuanceImplementationArtifact, ...]:
        identifiers = tuple(item.artifact_id for item in value)
        if identifiers != tuple(sorted(identifiers)):
            raise ValueError("implementation artifacts must be canonically sorted")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("implementation artifact IDs must be unique")
        observed = tuple((item.artifact_id, item.path, item.change_mode) for item in value)
        if observed != _IMPLEMENTATION_ARTIFACTS:
            raise ValueError("authorization-issuance implementation artifacts drifted")
        return value

    @model_validator(mode="after")
    def validate_review_boundary(self) -> Self:
        if self.authorization_issuance.final_authorization_generated:
            raise ValueError("authorization issuance must remain deferred")
        if self.safety.authorization_issuance_performed:
            raise ValueError("review cannot perform authorization issuance")
        if self.safety.gpu_execution_authorized:
            raise ValueError("review cannot authorize GPU execution")
        return self


def _validate_git_revision(revision: str) -> str:
    if _GIT_OBJECT_PATTERN.fullmatch(revision) is None:
        raise AuthorizationIssuanceReviewError(
            "REQUIRED_GIT_REVISION_INVALID",
            "required authorization-issuance review revision is invalid",
            details=(revision,),
        )
    return revision


def _git_blob_sha(
    repo_root: Path,
    relative_path: Path,
    *,
    revision: str = SOURCE_MAIN_MERGE_COMMIT,
) -> str:
    validated_revision = _validate_git_revision(revision)
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                f"{validated_revision}:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationIssuanceReviewError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required authorization-issuance authority could not be resolved",
            relative_path.as_posix(),
            details=(validated_revision,),
        ) from exc
    identity = result.stdout.strip()
    if _GIT_OBJECT_PATTERN.fullmatch(identity) is None:
        raise AuthorizationIssuanceReviewError(
            "REQUIRED_GIT_AUTHORITY_INVALID",
            "required authorization-issuance authority returned an invalid identity",
            relative_path.as_posix(),
            details=(validated_revision,),
        )
    return identity


def _git_file_sha256(
    repo_root: Path,
    relative_path: Path,
    *,
    revision: str = SOURCE_MAIN_MERGE_COMMIT,
) -> str:
    validated_revision = _validate_git_revision(revision)
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "show",
                f"{validated_revision}:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationIssuanceReviewError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required authorization-issuance authority could not be read",
            relative_path.as_posix(),
            details=(validated_revision,),
        ) from exc
    return hashlib.sha256(result.stdout).hexdigest()


def _git_text_at_revision(
    repo_root: Path,
    relative_path: Path,
    *,
    revision: str = SOURCE_MAIN_MERGE_COMMIT,
) -> str:
    validated_revision = _validate_git_revision(revision)
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "show",
                f"{validated_revision}:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationIssuanceReviewError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required authorization-issuance authority could not be read",
            relative_path.as_posix(),
            details=(validated_revision,),
        ) from exc
    return result.stdout


def _load_json_object_at_revision(
    repo_root: Path,
    relative_path: Path,
    *,
    revision: str = SOURCE_MAIN_MERGE_COMMIT,
) -> dict[str, object]:
    try:
        payload = json.loads(
            _git_text_at_revision(
                repo_root,
                relative_path,
                revision=revision,
            )
        )
    except json.JSONDecodeError as exc:
        raise AuthorizationIssuanceReviewError(
            "REQUIRED_JSON_AUTHORITY_INVALID",
            "required authorization-issuance authority must be valid JSON",
            relative_path.as_posix(),
            details=(revision,),
        ) from exc
    if not isinstance(payload, dict):
        raise AuthorizationIssuanceReviewError(
            "REQUIRED_JSON_AUTHORITY_INVALID",
            "required authorization-issuance authority must be one JSON object",
            relative_path.as_posix(),
            details=(revision,),
        )
    return payload


def _require_source_ancestor(repo_root: Path) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                SOURCE_MAIN_MERGE_COMMIT,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationIssuanceReviewError(
            "SOURCE_MAIN_ANCESTRY_UNREADABLE",
            "source main ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise AuthorizationIssuanceReviewError(
            "SOURCE_MAIN_MERGE_MISSING",
            "PR 109 merge must be an ancestor of the current HEAD",
            details=(SOURCE_MAIN_MERGE_COMMIT,),
        )


def build_default_review() -> FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview:
    """Build the review without generating operational authorization."""

    authorities = tuple(
        IssuanceReviewAuthorityBinding(
            binding_id=binding_id,
            role=role,
            source_locator=path.as_posix(),
            git_blob_sha=git_blob_sha,
            file_sha256=file_sha256,
            disposition=IssuanceAuthorityDisposition.CURRENT_AUTHORITY,
        )
        for binding_id, role, path, git_blob_sha, file_sha256 in _AUTHORITY_ROWS
    )
    generated_entries = tuple(
        MaterializationEntryReviewBinding(
            role=cast(
                Literal["harness_source", "model_artifacts", "vllm_wheel"],
                role,
            ),
            artifact_format=cast(
                Literal[
                    "source_tree_directory",
                    "hugging_face_snapshot_directory",
                    "python_wheel",
                ],
                artifact_format,
            ),
            kaggle_dataset_slug=kaggle_dataset_slug,
            kaggle_dataset_version=cast(Literal[1], kaggle_dataset_version),
            mounted_path=mounted_path,
            sha256=sha256,
        )
        for (
            role,
            artifact_format,
            kaggle_dataset_slug,
            kaggle_dataset_version,
            mounted_path,
            sha256,
        ) in _EXPECTED_MATERIALIZATION_ENTRIES
    )
    entries = cast(
        tuple[
            MaterializationEntryReviewBinding,
            MaterializationEntryReviewBinding,
            MaterializationEntryReviewBinding,
        ],
        generated_entries,
    )
    implementation_artifacts = tuple(
        AuthorizationIssuanceImplementationArtifact(
            artifact_id=artifact_id,
            path=path,
            change_mode=cast(Literal["create", "update", "generate"], change_mode),
        )
        for artifact_id, path, change_mode in _IMPLEMENTATION_ARTIFACTS
    )
    return FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview(
        review_id=REVIEW_ID,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        harness_source_commit=HARNESS_SOURCE_COMMIT,
        decision="APPROVED_FOR_AUTHORIZATION_ISSUANCE_IMPLEMENTATION",
        authority_bindings=authorities,
        materialization=MaterializationReviewBinding(
            harness_source_commit=HARNESS_SOURCE_COMMIT,
            materialization_record_path=_MATERIALIZATION_RECORD_PATH.as_posix(),
            materialization_record_sha256=_MATERIALIZATION_RECORD_SHA256,
            runtime_manifest_path=_RUNTIME_MANIFEST_PATH.as_posix(),
            runtime_manifest_sha256=_RUNTIME_MANIFEST_SHA256,
            entries=entries,
        ),
        runtime_factory=RuntimeFactoryReviewBinding(
            artifact_path=_RUNTIME_ADAPTER_PATH.as_posix(),
            artifact_git_blob_sha="2f832c487e338d6233fa774dc6a4069f31cfcc30",
            artifact_sha256=_RUNTIME_ADAPTER_SHA256,
            factory_path=_RUNTIME_FACTORY_PATH,
            protocol_path=_RUNTIME_PROTOCOL_PATH,
            startup_plan_path=_WORKER_STARTUP_PLAN_PATH.as_posix(),
        ),
        budget=AuthorizationIssuanceBudget(),
        privacy=AuthorizationIssuancePrivacyEnvelope(),
        implementation_artifacts=implementation_artifacts,
        authorization_issuance=AuthorizationIssuanceDecision(
            final_authorization_path=FINAL_AUTHORIZATION_PATH.as_posix(),
            execution_request_sha256=_EXECUTION_REQUEST_SHA256,
            materialization_record_sha256=_MATERIALIZATION_RECORD_SHA256,
            runtime_manifest_sha256=_RUNTIME_MANIFEST_SHA256,
            runtime_adapter_sha256=_RUNTIME_ADAPTER_SHA256,
        ),
        safety=AuthorizationIssuanceReviewSafetyEnvelope(),
        next_gate=NEXT_GATE,
    )


def load_review(
    path: Path,
) -> FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview:
    """Load the canonical review artifact with metadata-safe failures."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview.model_validate(
            payload
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_REVIEW_INVALID",
            "the authorization-issuance review artifact is missing or invalid",
            path.as_posix(),
        ) from exc


def write_default_review(
    path: Path,
) -> FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview:
    """Write only the review artifact; do not generate final authorization."""

    review = build_default_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(review.canonical_json(), encoding="utf-8", newline="\n")
    return review


def _validate_typed_authorities(
    repo_root: Path,
) -> tuple[
    auth_contracts.QualificationAuthorizationRequest,
    auth_contracts.MaterializedOfflineDatasetRecord,
    auth_contracts.PortableQualificationDatasetManifest,
]:
    try:
        request = auth_contracts.QualificationAuthorizationRequest.model_validate(
            _load_json_object_at_revision(repo_root, _AUTHORIZATION_REQUEST_PATH)
        )
        record = auth_contracts.MaterializedOfflineDatasetRecord.model_validate(
            _load_json_object_at_revision(repo_root, _MATERIALIZATION_RECORD_PATH)
        )
        manifest = auth_contracts.PortableQualificationDatasetManifest.model_validate(
            _load_json_object_at_revision(repo_root, _RUNTIME_MANIFEST_PATH)
        )
    except ValidationError as exc:
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_AUTHORITY_INVALID",
            "one or more issuance-review authorities failed contract validation",
        ) from exc
    return request, record, manifest


def _validate_notebook_boundary(repo_root: Path) -> None:
    notebook = _load_json_object_at_revision(repo_root, _EXECUTION_NOTEBOOK_PATH)
    metadata = notebook.get("metadata")
    cells = notebook.get("cells")
    if not isinstance(metadata, dict) or not isinstance(cells, list):
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_NOTEBOOK_INVALID",
            "qualification notebook structure is invalid",
            _EXECUTION_NOTEBOOK_PATH.as_posix(),
        )
    aura_metadata = metadata.get("auragateway")
    code_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]
    checks = [
        isinstance(aura_metadata, dict),
        all(cell.get("execution_count") is None for cell in code_cells),
        all(cell.get("outputs", []) == [] for cell in code_cells),
    ]
    if isinstance(aura_metadata, dict):
        checks.extend(
            (
                aura_metadata.get("execution_authorized") is False,
                aura_metadata.get("benchmark_trajectory_requests_permitted") == 0,
            )
        )
    if not all(checks):
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_NOTEBOOK_BOUNDARY_INVALID",
            "qualification notebook no longer preserves the unexecuted boundary",
            _EXECUTION_NOTEBOOK_PATH.as_posix(),
        )


def validate_repository_review_package(repo_root: Path) -> dict[str, object]:
    """Validate exact PR 109 issuance inputs and return a safe review summary."""

    _require_source_ancestor(repo_root)
    review = load_review(repo_root / REVIEW_PATH)

    git_drift = tuple(
        binding.source_locator
        for binding in review.authority_bindings
        if _git_blob_sha(
            repo_root,
            Path(binding.source_locator),
            revision=SOURCE_MAIN_MERGE_COMMIT,
        )
        != binding.git_blob_sha
    )
    if git_drift:
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_GIT_AUTHORITY_DRIFT",
            "one or more PR 109 authorization authorities drifted",
            details=tuple(sorted(git_drift)),
        )

    content_drift = tuple(
        binding.source_locator
        for binding in review.authority_bindings
        if _git_file_sha256(
            repo_root,
            Path(binding.source_locator),
            revision=SOURCE_MAIN_MERGE_COMMIT,
        )
        != binding.file_sha256
    )
    if content_drift:
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_CONTENT_DRIFT",
            "one or more PR 109 authorization authority contents drifted",
            details=tuple(sorted(content_drift)),
        )

    request, record, manifest = _validate_typed_authorities(repo_root)
    expected_manifest = build_portable_runtime_manifest(record)
    if manifest.canonical_json() != expected_manifest.canonical_json():
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_MANIFEST_PROJECTION_DRIFT",
            "runtime manifest does not match the exact materialization record",
            _RUNTIME_MANIFEST_PATH.as_posix(),
        )

    request_checks = (
        request.next_gate == "full_abc_local_full_run_environment_qualification_execution_"
        "authorization_issuance_review",
        request.final_authorization_generated is False,
        request.operator_confirmation_required is True,
        request.maximum_authorization_window_minutes == 240,
        request.maximum_kaggle_sessions == 1,
        request.maximum_workers == 2,
        request.maximum_model_requests == 8,
        request.maximum_output_tokens_per_request == 32,
        request.benchmark_trajectory_requests_permitted == 0,
        request.customer_data_permitted is False,
        request.credentials_permitted is False,
        request.network_access_permitted is False,
        request.external_spend == 0,
        request.runtime_adapter.factory_path == _RUNTIME_FACTORY_PATH,
        request.runtime_adapter.protocol_path == _RUNTIME_PROTOCOL_PATH,
        request.runtime_adapter.adapter_executed is False,
    )
    record_checks = (
        record.harness_source_commit == HARNESS_SOURCE_COMMIT,
        record.fingerprint() == _MATERIALIZATION_RECORD_SHA256,
        record.runtime_manifest_sha256 == _RUNTIME_MANIFEST_SHA256,
        record.network_access_permitted is False,
        record.credentials_present is False,
        record.customer_data_present is False,
        record.hosted_provider_inputs_present is False,
    )
    manifest_checks = (
        manifest.fingerprint() == _RUNTIME_MANIFEST_SHA256,
        manifest.network_access_permitted is False,
        manifest.credentials_present is False,
        manifest.customer_data_present is False,
        manifest.hosted_provider_inputs_present is False,
    )
    if not all((*request_checks, *record_checks, *manifest_checks)):
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_BOUNDARY_INVALID",
            "merged inputs no longer support bounded authorization issuance",
        )

    observed_entries = tuple(
        (
            item.role.value,
            item.artifact_format.value,
            item.kaggle_dataset_slug,
            item.kaggle_dataset_version,
            item.mounted_path,
            item.sha256,
        )
        for item in record.entries
    )
    if observed_entries != _EXPECTED_MATERIALIZATION_ENTRIES:
        raise AuthorizationIssuanceReviewError(
            "AUTHORIZATION_ISSUANCE_MATERIALIZATION_DRIFT",
            "exact materialized input identities drifted",
        )

    _validate_notebook_boundary(repo_root)
    if (repo_root / FINAL_AUTHORIZATION_PATH).exists():
        raise AuthorizationIssuanceReviewError(
            "PREMATURE_FINAL_AUTHORIZATION_PRESENT",
            "final operational authorization appeared before implementation",
            FINAL_AUTHORIZATION_PATH.as_posix(),
        )

    historical_issuance_summary = {
        "materialization_record_sha256": record.fingerprint(),
        "runtime_dataset_manifest_sha256": manifest.fingerprint(),
        "runtime_adapter_sha256": _git_file_sha256(
            repo_root,
            _RUNTIME_ADAPTER_PATH,
            revision=SOURCE_MAIN_MERGE_COMMIT,
        ),
        "harness_source_commit": record.harness_source_commit,
        "exact_kaggle_dataset_count": len(record.entries),
        "final_authorization_generated": False,
        "kaggle_session_started": False,
        "next_gate": (
            "full_abc_local_full_run_environment_qualification_execution_"
            "authorization_issuance_review"
        ),
    }
    expected_issuance_summary = {
        "materialization_record_sha256": _MATERIALIZATION_RECORD_SHA256,
        "runtime_dataset_manifest_sha256": _RUNTIME_MANIFEST_SHA256,
        "runtime_adapter_sha256": _RUNTIME_ADAPTER_SHA256,
        "harness_source_commit": HARNESS_SOURCE_COMMIT,
        "exact_kaggle_dataset_count": 3,
        "final_authorization_generated": False,
        "kaggle_session_started": False,
        "next_gate": (
            "full_abc_local_full_run_environment_qualification_execution_"
            "authorization_issuance_review"
        ),
    }
    if any(
        historical_issuance_summary.get(key) != value
        for key, value in expected_issuance_summary.items()
    ):
        raise AuthorizationIssuanceReviewError(
            "HISTORICAL_ISSUANCE_INPUT_SUMMARY_DRIFT",
            "historical PR 109 issuance-input summary drifted",
        )

    return {
        "review_sha256": review.fingerprint(),
        "decision": review.decision,
        "source_main_merge_commit": review.source_main_merge_commit,
        "harness_source_commit": review.harness_source_commit,
        "materialization_record_sha256": review.materialization.materialization_record_sha256,
        "runtime_manifest_sha256": review.materialization.runtime_manifest_sha256,
        "runtime_adapter_sha256": review.runtime_factory.artifact_sha256,
        "runtime_factory": review.runtime_factory.factory_path,
        "maximum_authorization_window_minutes": (
            review.budget.maximum_authorization_window_minutes
        ),
        "maximum_kaggle_sessions": review.budget.maximum_kaggle_sessions,
        "maximum_workers": review.budget.maximum_workers,
        "maximum_model_requests": review.budget.maximum_model_requests,
        "maximum_output_tokens_per_request": (review.budget.maximum_output_tokens_per_request),
        "benchmark_trajectory_requests_permitted": (
            review.budget.benchmark_trajectory_requests_permitted
        ),
        "network_access_permitted": review.privacy.network_access_permitted,
        "customer_data_permitted": review.privacy.customer_data_permitted,
        "credentials_permitted": review.privacy.credentials_permitted,
        "external_spend": review.budget.external_spend,
        "final_authorization_generated": False,
        "authorization_issuance_performed": False,
        "kaggle_session_started": False,
        "lifecycle_after": review.lifecycle_after,
        "next_gate": review.next_gate,
    }
