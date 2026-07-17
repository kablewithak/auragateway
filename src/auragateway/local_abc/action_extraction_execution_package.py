"""Deterministic Kaggle execution packaging for action-extraction requalification v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.action_extraction_notebook_qualification import (
    ActionExtractionNotebookQualificationPackageV2,
    load_action_extraction_notebook_qualification_package_v2,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")

_PR89_MERGE_COMMIT: Final = "1cbb01e72fc624b71be1faef9da199a1556d2f0c"
_QUALIFICATION_SOURCE_BLOB_SHA: Final = "97a5756d3a95defccdff90811ff1318f863456b7"
_NOTEBOOK_BLOB_SHA: Final = "237c344330d63b803f94265dbdc24c20ae379dcd"
_BINDING_BLOB_SHA: Final = "9e88e7ac87b0452839b25c540f4e50f3282e72a1"
_QUALIFICATION_SOURCE_FILE_SHA256: Final = (
    "70f80b2a01c5d13dea3c775a911ad810d13ec5d09bf0d3806dfd5fc64a6e1d04"
)
_NOTEBOOK_SHA256: Final = "e1e38afa6f269c9aa529bdafa1ce4ca8c4bba4a53d7b69e93bfaf0e3549a97e9"
_NOTEBOOK_CODE_SOURCE_SHA256: Final = (
    "26f7f46475e2746e6e099210475b18b08a1abb90994759394cc2c11d39f1c499"
)
_NOTEBOOK_BINDING_SHA256: Final = "476d3be54fc34cafacba4bcdef07eaa1213a426df0496e4908bc8078b7edac88"
_NOTEBOOK_BINDING_FILE_SHA256: Final = (
    "f1ed0f27d8073f806b59317aca22424335df4d71c37068ee5efa1493779f77c6"
)
_PACKAGE_SHA256: Final = "deb7d803819ec489218f78ecc4466ae1402eef30a63ba7b93d293ea872677451"
_PACKAGE_SIZE_BYTES: Final = 76893
_FIXED_ZIP_TIMESTAMP: Final = (1980, 1, 1, 0, 0, 0)
_FIXED_ZIP_MODE: Final = 0o100644

_NOTEBOOK_PATH: Final = (
    "notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb"
)
_BINDING_PATH: Final = (
    "benchmarks/local_abc/reconcile_balance_extraction_requalification_notebook_binding_v2.json"
)
_PACKAGE_FILENAME: Final = "auragateway-local-abc-action-extraction-requalification-notebook-v2.zip"
_EXPECTED_MEMBER_PATHS: Final = (_BINDING_PATH, _NOTEBOOK_PATH)


class ActionExtractionExecutionPackageSourceBinding(LocalABCContract):
    """Exact merged PR #89 source binding."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    path: str
    git_blob_sha: str
    file_sha256: str
    canonical_sha256: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("execution-package source path must be repository-relative")
        return value

    @field_validator("git_blob_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("execution-package source blob must be a full lowercase Git SHA")
        return value

    @field_validator("file_sha256", "canonical_sha256")
    @classmethod
    def validate_digest(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution-package source digest must be lowercase SHA-256")
        return value


class ActionExtractionExecutionPackageMember(LocalABCContract):
    """One exact deterministic ZIP member."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    path: str
    sha256: str
    size_bytes: int = Field(ge=1)
    compression: Literal["stored"] = "stored"
    timestamp: Literal["1980-01-01T00:00:00"] = "1980-01-01T00:00:00"
    unix_mode: Literal["100644"] = "100644"

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("execution-package member path must be repository-relative")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution-package member digest must be lowercase SHA-256")
        return value


class ActionExtractionKaggleExecutionPackageV2(LocalABCContract):
    """Frozen package identity and single-execution operator contract."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    package_id: Literal["reconcile-balance-action-extraction-kaggle-execution-package-v2"] = (
        "reconcile-balance-action-extraction-kaggle-execution-package-v2"
    )
    created_at: datetime
    repository: Literal["kablewithak/auragateway"] = "kablewithak/auragateway"
    source_merge_commit: Literal["1cbb01e72fc624b71be1faef9da199a1556d2f0c"] = _PR89_MERGE_COMMIT
    source_bindings: tuple[ActionExtractionExecutionPackageSourceBinding, ...] = Field(
        min_length=3,
        max_length=3,
    )
    authorization_id: Literal[
        "reconcile-balance-action-extraction-requalification-authorization-v2"
    ] = "reconcile-balance-action-extraction-requalification-authorization-v2"
    authorization_sha256: str
    authorization_consumed: Literal[False] = False
    notebook_binding_sha256: str
    notebook_sha256: str
    notebook_code_source_sha256: str
    notebook_qualified_for_bounded_execution: Literal[True] = True
    package_filename: Literal[
        "auragateway-local-abc-action-extraction-requalification-notebook-v2.zip"
    ] = _PACKAGE_FILENAME
    package_sha256: str
    package_size_bytes: Literal[76893] = _PACKAGE_SIZE_BYTES
    archive_policy: Literal["zip_stored_fixed_metadata_v1"] = "zip_stored_fixed_metadata_v1"
    member_count: Literal[2] = 2
    members: tuple[ActionExtractionExecutionPackageMember, ...] = Field(
        min_length=2,
        max_length=2,
    )
    zip_integrity_verified: Literal[True] = True
    package_member_bytes_verified: Literal[True] = True
    status: Literal["ready_for_single_kaggle_execution"] = "ready_for_single_kaggle_execution"
    execution_permitted_after_package_pr_merge: Literal[True] = True
    operator_merge_verification_required: Literal[True] = True
    execution_attempt_limit: Literal[1] = 1
    request_count: Literal[16] = 16
    request_attempts_per_case: Literal[1] = 1
    complete_suite_required: Literal[True] = True
    failed_case_only_execution_permitted: Literal[False] = False
    hidden_retry_count: Literal[0] = 0
    repair_attempt_count: Literal[0] = 0
    replacement_request_count: Literal[0] = 0
    required_exact_operand_matches: Literal[16] = 16
    required_exact_final_answer_matches: Literal[16] = 16
    kaggle_accelerator: Literal["GPU T4 x2"] = "GPU T4 x2"
    kaggle_internet_required: Literal[True] = True
    kaggle_secrets_required: Literal[False] = False
    package_attachment_required: Literal[True] = True
    restart_and_rerun_permitted: Literal[False] = False
    failed_cell_only_rerun_permitted: Literal[False] = False
    expected_evidence_archive_filename: Literal[
        "auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip"
    ] = "auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip"
    evidence_archive_download_required: Literal[True] = True
    raw_prompt_retention_permitted: Literal[False] = False
    raw_output_retention_permitted: Literal[False] = False
    raw_action_retention_permitted: Literal[False] = False
    token_id_retention_permitted: Literal[False] = False
    cache_measurement_in_scope: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    provider_call_performed: Literal[False] = False
    model_request_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    external_spend: Literal[0] = 0
    customer_data_used: Literal[False] = False
    synthetic_data_only: Literal[True] = True
    next_gate: Literal["immutable_action_extraction_v2_execution_evidence_audit"] = (
        "immutable_action_extraction_v2_execution_evidence_audit"
    )

    @field_validator("package_id")
    @classmethod
    def validate_package_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("execution-package ID must use stable lowercase characters")
        return value

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value

    @field_validator("source_merge_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("source merge commit must be a full lowercase Git SHA")
        return value

    @field_validator(
        "authorization_sha256",
        "notebook_binding_sha256",
        "notebook_sha256",
        "notebook_code_source_sha256",
        "package_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution-package digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_package(self) -> Self:
        expected_bindings = (
            (
                "src/auragateway/local_abc/action_extraction_notebook_qualification.py",
                _QUALIFICATION_SOURCE_BLOB_SHA,
                _QUALIFICATION_SOURCE_FILE_SHA256,
                None,
            ),
            (
                _NOTEBOOK_PATH,
                _NOTEBOOK_BLOB_SHA,
                _NOTEBOOK_SHA256,
                _NOTEBOOK_SHA256,
            ),
            (
                _BINDING_PATH,
                _BINDING_BLOB_SHA,
                _NOTEBOOK_BINDING_FILE_SHA256,
                _NOTEBOOK_BINDING_SHA256,
            ),
        )
        observed_bindings = tuple(
            (
                binding.path,
                binding.git_blob_sha,
                binding.file_sha256,
                binding.canonical_sha256,
            )
            for binding in self.source_bindings
        )
        if observed_bindings != expected_bindings:
            raise ValueError("execution-package source bindings drifted from merged PR #89")
        if self.notebook_binding_sha256 != _NOTEBOOK_BINDING_SHA256:
            raise ValueError("execution package must bind the qualified notebook contract")
        if self.notebook_sha256 != _NOTEBOOK_SHA256:
            raise ValueError("execution package must bind the exact notebook bytes")
        if self.notebook_code_source_sha256 != _NOTEBOOK_CODE_SOURCE_SHA256:
            raise ValueError("execution package must bind the exact notebook code source")
        if self.package_sha256 != _PACKAGE_SHA256:
            raise ValueError("execution-package archive digest drifted")
        expected_members = (
            (_BINDING_PATH, _NOTEBOOK_BINDING_FILE_SHA256, 4097),
            (_NOTEBOOK_PATH, _NOTEBOOK_SHA256, 72258),
        )
        observed_members = tuple(
            (member.path, member.sha256, member.size_bytes) for member in self.members
        )
        if observed_members != expected_members:
            raise ValueError("execution-package member constitution drifted")
        return self


class ActionExtractionExecutionPackageFacts(LocalABCContract):
    """Facts inspected from one generated execution package."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    package_sha256: str
    package_size_bytes: int = Field(ge=1)
    member_paths: tuple[str, str]
    member_sha256: tuple[str, str]
    member_size_bytes: tuple[int, int]
    zip_integrity_verified: Literal[True] = True
    deterministic_metadata_verified: Literal[True] = True

    @field_validator("package_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("package facts digest must be lowercase SHA-256")
        return value


class ActionExtractionExecutionPackageBundleV2(LocalABCContract):
    """Cross-file proof that the generated package matches the qualification lineage."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    qualification_package: ActionExtractionNotebookQualificationPackageV2
    execution_package: ActionExtractionKaggleExecutionPackageV2
    facts: ActionExtractionExecutionPackageFacts

    @model_validator(mode="after")
    def validate_bundle(self) -> Self:
        binding = self.qualification_package.binding
        if binding.fingerprint() != self.execution_package.notebook_binding_sha256:
            raise ValueError("execution package must bind the qualified notebook binding")
        if binding.notebook_sha256 != self.execution_package.notebook_sha256:
            raise ValueError("execution package notebook SHA drifted from qualification")
        if binding.notebook_code_source_sha256 != (
            self.execution_package.notebook_code_source_sha256
        ):
            raise ValueError("execution package code-source SHA drifted from qualification")
        if binding.authorization_consumed:
            raise ValueError("execution package requires the fresh unused authorization")
        if self.facts.package_sha256 != self.execution_package.package_sha256:
            raise ValueError("generated package SHA does not match execution package contract")
        if self.facts.package_size_bytes != self.execution_package.package_size_bytes:
            raise ValueError("generated package size does not match execution package contract")
        expected_paths = tuple(member.path for member in self.execution_package.members)
        if self.facts.member_paths != expected_paths:
            raise ValueError("generated package paths do not match execution package contract")
        if self.facts.member_sha256 != tuple(
            member.sha256 for member in self.execution_package.members
        ):
            raise ValueError("generated package member digests drifted")
        return self


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_fixed_member(archive: zipfile.ZipFile, *, path: str, data: bytes) -> None:
    info = zipfile.ZipInfo(path, date_time=_FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = _FIXED_ZIP_MODE << 16
    info.internal_attr = 0
    info.flag_bits = 0
    archive.writestr(info, data)


def build_action_extraction_kaggle_package_v2(
    *,
    repository_root: Path,
    destination: Path,
) -> ActionExtractionExecutionPackageFacts:
    """Build the exact deterministic two-member Kaggle package without executing it."""

    source_bytes = {path: (repository_root / path).read_bytes() for path in _EXPECTED_MEMBER_PATHS}
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in _EXPECTED_MEMBER_PATHS:
            _write_fixed_member(archive, path=path, data=source_bytes[path])
    return inspect_action_extraction_kaggle_package_v2(destination)


def inspect_action_extraction_kaggle_package_v2(
    path: Path,
) -> ActionExtractionExecutionPackageFacts:
    """Inspect exact package bytes, members, and deterministic ZIP metadata."""

    package_bytes = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("execution-package ZIP integrity failed")
        infos = archive.infolist()
        member_paths = tuple(info.filename for info in infos)
        if member_paths != _EXPECTED_MEMBER_PATHS:
            raise ValueError("execution-package member paths or order drifted")
        member_sha256: list[str] = []
        member_size_bytes: list[int] = []
        for info in infos:
            if info.compress_type != zipfile.ZIP_STORED:
                raise ValueError("execution-package members must use stored compression")
            if info.date_time != _FIXED_ZIP_TIMESTAMP:
                raise ValueError("execution-package member timestamp drifted")
            if info.create_system != 3 or (info.external_attr >> 16) != _FIXED_ZIP_MODE:
                raise ValueError("execution-package member mode drifted")
            data = archive.read(info.filename)
            member_sha256.append(_sha256_bytes(data))
            member_size_bytes.append(len(data))
    return ActionExtractionExecutionPackageFacts(
        package_sha256=_sha256_bytes(package_bytes),
        package_size_bytes=len(package_bytes),
        member_paths=(member_paths[0], member_paths[1]),
        member_sha256=(member_sha256[0], member_sha256[1]),
        member_size_bytes=(member_size_bytes[0], member_size_bytes[1]),
        zip_integrity_verified=True,
        deterministic_metadata_verified=True,
    )


def load_action_extraction_execution_package_v2(
    path: Path,
) -> ActionExtractionKaggleExecutionPackageV2:
    """Load and validate the canonical execution-package contract."""

    return ActionExtractionKaggleExecutionPackageV2.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_action_extraction_execution_package_bundle_v2(
    *,
    repository_root: Path,
    execution_package_path: Path,
    generated_package_path: Path,
) -> ActionExtractionExecutionPackageBundleV2:
    """Load qualification lineage and validate the generated Kaggle package."""

    benchmark_root = repository_root / "benchmarks" / "local_abc"
    qualification_package = load_action_extraction_notebook_qualification_package_v2(
        parent_manifest_path=benchmark_root / "reconcile_balance_extraction_eval_cases_v1.json",
        parent_plan_path=benchmark_root / "reconcile_balance_extraction_eval_plan_v1.json",
        remediation_manifest_path=(
            benchmark_root / "reconcile_balance_extraction_remediation_cases_v2.json"
        ),
        remediation_plan_path=(
            benchmark_root / "reconcile_balance_extraction_remediation_plan_v2.json"
        ),
        review_path=(benchmark_root / "reconcile_balance_extraction_authorization_review_v2.json"),
        dry_run_path=(
            benchmark_root / "reconcile_balance_extraction_authorization_dry_run_v2.json"
        ),
        review_manifest_path=(
            benchmark_root / "reconcile_balance_extraction_authorization_review_manifest_v2.json"
        ),
        authorization_path=(
            benchmark_root / "reconcile_balance_extraction_requalification_authorization_v2.json"
        ),
        activation_manifest_path=(
            benchmark_root
            / "reconcile_balance_extraction_authorization_activation_manifest_v2.json"
        ),
        notebook_path=repository_root / _NOTEBOOK_PATH,
        notebook_binding_path=repository_root / _BINDING_PATH,
    )
    return ActionExtractionExecutionPackageBundleV2(
        qualification_package=qualification_package,
        execution_package=load_action_extraction_execution_package_v2(execution_package_path),
        facts=inspect_action_extraction_kaggle_package_v2(generated_package_path),
    )


def canonical_execution_package_file_sha256(path: Path) -> str:
    """Validate canonical one-line JSON and return its contract fingerprint."""

    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    if text != f"{canonical}\n":
        raise ValueError(f"JSON artifact is not canonical one-line JSON: {path}")
    return ActionExtractionKaggleExecutionPackageV2.model_validate(payload).fingerprint()


def main() -> int:
    """Build and verify the exact Kaggle upload package."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository_root = args.repository_root.resolve()
    output = args.output.resolve()
    facts = build_action_extraction_kaggle_package_v2(
        repository_root=repository_root,
        destination=output,
    )
    manifest_path = (
        repository_root / "benchmarks/local_abc/"
        "reconcile_balance_extraction_requalification_execution_package_v2.json"
    )
    bundle = load_action_extraction_execution_package_bundle_v2(
        repository_root=repository_root,
        execution_package_path=manifest_path,
        generated_package_path=output,
    )
    print(
        json.dumps(
            {
                "status": bundle.execution_package.status,
                "output": str(output),
                "package_sha256": facts.package_sha256,
                "package_size_bytes": facts.package_size_bytes,
                "member_count": len(facts.member_paths),
                "authorization_consumed": False,
                "model_request_performed": False,
                "gpu_execution_performed": False,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
