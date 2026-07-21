"""Typed contracts for the current CUDA 12.9 harness rematerialization toolchain."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class HarnessSourceInventoryEntry(LocalABCContract):
    """One regular Git blob included in the deterministic source package."""

    path: str
    git_blob_sha: str
    sha256: str
    size_bytes: int = Field(ge=0)
    executable: bool = False

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or not path.parts
            or ".." in path.parts
            or "\\" in value
            or value.startswith("./")
            or path.as_posix() != value
        ):
            raise ValueError("inventory path must be a normalized relative POSIX path")
        return value

    @field_validator("git_blob_sha")
    @classmethod
    def validate_git_blob_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("git_blob_sha must be a lowercase 40-character Git object id")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("inventory sha256 must be lowercase SHA-256")
        return value


class HarnessBuildSpec(LocalABCContract):
    """Deterministic source-authority and output contract for one harness package."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    package_id: str
    source_commit: str
    archive_name: str
    input_dataset_name: str
    output_directory: str
    materialization_receipt_name: str
    required_paths: tuple[str, ...]
    expected_file_sha256: dict[str, str] = Field(default_factory=dict)
    maximum_files: int = Field(ge=1, le=20_000)
    maximum_total_bytes: int = Field(ge=1, le=2 * 1024 * 1024 * 1024)

    @field_validator(
        "package_id",
        "input_dataset_name",
        "output_directory",
        "materialization_receipt_name",
    )
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.removesuffix(".json")
        if _NAME_PATTERN.fullmatch(normalized) is None:
            raise ValueError("toolchain names must use stable lowercase characters")
        return value

    @field_validator("archive_name")
    @classmethod
    def validate_archive_name(cls, value: str) -> str:
        if not value.endswith(".zip") or "/" in value or "\\" in value:
            raise ValueError("archive_name must be one ZIP filename")
        return value

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("source_commit must be one lowercase 40-character Git commit id")
        return value

    @field_validator("required_paths")
    @classmethod
    def validate_required_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(set(value)) != len(value):
            raise ValueError("required_paths must be non-empty and unique")
        for item in value:
            HarnessSourceInventoryEntry(
                path=item,
                git_blob_sha="0" * 40,
                sha256="0" * 64,
                size_bytes=0,
            )
        return value

    @field_validator("expected_file_sha256")
    @classmethod
    def validate_expected_file_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        for path, digest in value.items():
            HarnessSourceInventoryEntry(
                path=path,
                git_blob_sha="0" * 40,
                sha256=digest,
                size_bytes=0,
            )
        return value

    @model_validator(mode="after")
    def validate_expected_paths_are_required(self) -> Self:
        missing = sorted(set(self.expected_file_sha256) - set(self.required_paths))
        if missing:
            raise ValueError("expected_file_sha256 keys must also be required paths")
        return self


class HarnessToolchainSafety(LocalABCContract):
    """Fail-closed non-execution boundary for packaging and metadata inspection."""

    network_access_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    tokenizer_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    benchmark_trajectory_requests_performed: Literal[0] = 0
    authorization_issued: Literal[False] = False
    credentials_present: Literal[False] = False
    customer_data_present: Literal[False] = False
    external_spend: Literal[0] = 0


class HarnessSourcePackageReceipt(LocalABCContract):
    """Canonical receipt for one deterministic source archive."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["CURRENT_CU129_HARNESS_SOURCE_PACKAGED"]
    package_id: str
    source_commit: str
    archive_name: str
    archive_sha256: str
    inventory_name: Literal["source_inventory.json"] = "source_inventory.json"
    inventory_sha256: str
    source_receipt_name: Literal["source_packaging_receipt.json"] = "source_packaging_receipt.json"
    sha256_manifest_name: Literal["sha256_manifest.json"] = "sha256_manifest.json"
    output_directory: str
    input_dataset_name: str
    materialization_receipt_name: str
    directory_sha256: str
    file_count: int = Field(ge=1)
    total_bytes: int = Field(ge=1)
    required_paths: tuple[str, ...]
    expected_file_sha256: dict[str, str]
    safety: HarnessToolchainSafety = Field(default_factory=HarnessToolchainSafety)

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("receipt source_commit must be one lowercase Git commit id")
        return value

    @field_validator("archive_sha256", "inventory_sha256", "directory_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("receipt digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_counts_and_required_paths(self) -> Self:
        if self.file_count < len(self.required_paths):
            raise ValueError("file_count cannot be smaller than the required path set")
        if set(self.expected_file_sha256) - set(self.required_paths):
            raise ValueError("receipt expected identities must belong to required paths")
        return self


class GeneratedNotebookReceipt(LocalABCContract):
    """Identity and safety contract for one generated unexecuted notebook."""

    notebook_name: str
    filename: str
    sha256: str
    cell_count: int = Field(ge=2, le=4)
    execution_counts_present: Literal[False] = False
    outputs_present: Literal[False] = False
    network_access_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_requests_performed: Literal[0] = 0

    @field_validator("notebook_name")
    @classmethod
    def validate_notebook_name(cls, value: str) -> str:
        if len(value) > 50 or _NAME_PATTERN.fullmatch(value) is None:
            raise ValueError("notebook_name must be a valid Kaggle name of at most 50 characters")
        return value

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        if not value.endswith(".ipynb") or "/" in value or "\\" in value:
            raise ValueError("filename must be one notebook filename")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("notebook sha256 must be lowercase SHA-256")
        return value


class PreparedHarnessToolchainReceipt(LocalABCContract):
    """Top-level identity binding the package and generated notebook outputs."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["CURRENT_CU129_HARNESS_TOOLCHAIN_PREPARED"]
    source_package: HarnessSourcePackageReceipt
    source_receipt_sha256: str
    source_sha256_manifest_sha256: str
    materializer_notebook: GeneratedNotebookReceipt
    inspection_notebook: GeneratedNotebookReceipt
    output_filenames: tuple[str, ...]
    next_gate: Literal["publish_materialize_and_metadata_inspect_current_cu129_harness"]
    safety: HarnessToolchainSafety = Field(default_factory=HarnessToolchainSafety)

    @field_validator("source_receipt_sha256", "source_sha256_manifest_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("prepared-toolchain digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_output_filename_set(self) -> Self:
        expected = {
            self.source_package.archive_name,
            self.source_package.inventory_name,
            self.source_package.source_receipt_name,
            self.source_package.sha256_manifest_name,
            self.materializer_notebook.filename,
            self.inspection_notebook.filename,
            "toolchain_receipt.json",
        }
        if set(self.output_filenames) != expected or len(self.output_filenames) != len(expected):
            raise ValueError("prepared toolchain output filename set drifted")
        return self


class HarnessToolchainDecisionRecord(LocalABCContract):
    """Repository decision authorizing the complete rematerialization toolchain."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-current-harness-toolchain-v1"]
    review_minimum_ancestor: Literal["defe184d338b525e2f48104ef76e5d0d9a1329a8"]
    decision: Literal["APPROVED_FOR_COMPLETE_CURRENT_CU129_HARNESS_TOOLCHAIN"]
    capabilities: tuple[str, ...]
    safety: HarnessToolchainSafety = Field(default_factory=HarnessToolchainSafety)
    next_gate: Literal["merge_then_prepare_current_cu129_harness_toolchain"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_capabilities_and_non_claims(self) -> Self:
        expected_capabilities = {
            "deterministic_git_object_source_packaging",
            "reproducible_zip_byte_verification",
            "typed_source_inventory_and_receipt",
            "current_runtime_boundary_validation",
            "kaggle_materializer_notebook_generation",
            "metadata_only_input_inspection_notebook_generation",
            "archive_and_filesystem_safety_guards",
            "post_merge_clean_main_source_binding",
            "tooling_authority_separation",
            "repeated_failure_reasoning_certificate",
        }
        if set(self.capabilities) != expected_capabilities or len(self.capabilities) != len(
            expected_capabilities
        ):
            raise ValueError("toolchain capability set drifted")
        required_non_claims = {
            "final post-merge source commit not yet known",
            "current harness archive not yet generated",
            "Kaggle materialization not yet performed",
            "metadata-only input inspection not yet performed",
            "authorization not issued",
            "environment qualification not performed",
            "measured A/B/C execution not authorized",
            "production readiness not claimed",
        }
        if not required_non_claims.issubset(set(self.non_claims)):
            raise ValueError("toolchain non-claim set is incomplete")
        return self
