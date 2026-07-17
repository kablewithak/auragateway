"""Static qualification and lineage binding for the v2 requalification notebook."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.action_extraction_authorization_activation import (
    ActionExtractionAuthorizationActivationPackageV2,
    load_action_extraction_authorization_activation_package_v2,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")

_PR88_MERGE_COMMIT: Final = "639e21a63eb8a37d0221c2630b756203d1270f62"
_ACTIVATION_SOURCE_BLOB_SHA: Final = "aa1afdf0acc52bd5bf2a3e0d7fb9c6b71f5fd342"
_AUTHORIZATION_JSON_BLOB_SHA: Final = "3f84ebc86450dc8e2e70c2d457593bf9b10136bf"
_ACTIVATION_MANIFEST_BLOB_SHA: Final = "142133a745dcc69d64ecae81811c8d2cb377b909"
_AUTHORIZATION_SHA256: Final = "a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899"
_ACTIVATION_MANIFEST_SHA256: Final = (
    "42ce858a657afe0fd6d4eb7a5e0846fedf1b9c41ab883826acf08712a94b0526"
)
_EXPECTED_CODE_CELL_COUNT: Final = 12
_EXPECTED_CASE_COUNT: Final = 16
_EXPECTED_IMPORT_MODULES: Final = (
    "auragateway",
    "auragateway.local_abc.action_extraction_authorization_activation",
    "auragateway.local_abc.action_extraction_remediation",
    "auragateway.local_abc.action_extraction_eval",
    "auragateway.local_abc.arithmetic_action",
)


class ActionExtractionNotebookSourceBinding(LocalABCContract):
    """Exact merged activation source or artifact binding."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    path: str
    git_blob_sha: str
    canonical_sha256: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("notebook source binding path must be repository-relative")
        return value

    @field_validator("git_blob_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("notebook source blob must be a full lowercase Git SHA")
        return value

    @field_validator("canonical_sha256")
    @classmethod
    def validate_optional_digest(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("notebook source digest must be lowercase SHA-256")
        return value


class ActionExtractionNotebookArtifactFacts(LocalABCContract):
    """Static facts derived from the notebook bytes."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    notebook_sha256: str
    notebook_code_source_sha256: str
    notebook_code_cell_count: Literal[12] = 12
    notebook_has_saved_execution_state: Literal[False] = False
    notebook_cells_compile: Literal[True] = True

    @field_validator("notebook_sha256", "notebook_code_source_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("notebook artifact digests must be lowercase SHA-256")
        return value


class ActionExtractionRequalificationNotebookBindingV2(LocalABCContract):
    """Frozen notebook identity and bounded execution constitution."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    binding_id: Literal[
        "reconcile-balance-action-extraction-requalification-notebook-binding-v2"
    ] = "reconcile-balance-action-extraction-requalification-notebook-binding-v2"
    generated_at: datetime
    repository: Literal["kablewithak/auragateway"] = "kablewithak/auragateway"
    activation_merge_commit: Literal["639e21a63eb8a37d0221c2630b756203d1270f62"] = (
        _PR88_MERGE_COMMIT
    )
    source_bindings: tuple[ActionExtractionNotebookSourceBinding, ...] = Field(
        min_length=3,
        max_length=3,
    )
    authorization_id: Literal[
        "reconcile-balance-action-extraction-requalification-authorization-v2"
    ] = "reconcile-balance-action-extraction-requalification-authorization-v2"
    authorization_sha256: str
    activation_manifest_sha256: str
    authorization_consumed: Literal[False] = False
    prior_authorization_consumed: Literal[True] = True
    notebook_filename: Literal[
        "auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb"
    ] = "auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb"
    notebook_repository_path: Literal[
        "notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb"
    ] = (
        "notebooks/kaggle/"
        "auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb"
    )
    package_filename: Literal[
        "auragateway-local-abc-action-extraction-requalification-notebook-v2.zip"
    ] = "auragateway-local-abc-action-extraction-requalification-notebook-v2.zip"
    notebook_sha256: str
    notebook_code_source_sha256: str
    notebook_code_cell_count: Literal[12] = 12
    notebook_has_saved_execution_state: Literal[False] = False
    notebook_cells_compile: Literal[True] = True
    notebook_qualified_for_bounded_execution: Literal[True] = True
    case_count: Literal[16] = 16
    request_count: Literal[16] = 16
    request_attempts_per_case: Literal[1] = 1
    complete_suite_required: Literal[True] = True
    failed_case_only_execution_permitted: Literal[False] = False
    hidden_retry_count: Literal[0] = 0
    repair_attempt_count: Literal[0] = 0
    replacement_request_count: Literal[0] = 0
    worker_id: Literal["worker_1"] = "worker_1"
    required_import_modules: tuple[str, ...] = _EXPECTED_IMPORT_MODULES
    repository_import_qualification_required: Literal[True] = True
    repository_source_path_policy: Literal["exact_checkout_src_prepend_v1"] = (
        "exact_checkout_src_prepend_v1"
    )
    editable_install_required: Literal[False] = False
    runtime_environment_isolation_required: Literal[True] = True
    runtime_environment_policy: Literal["isolated_venv_exact_torch_cu129_v2"] = (
        "isolated_venv_exact_torch_cu129_v2"
    )
    runtime_venv_bootstrap_policy: Literal["without_pip_host_pip_python_v1"] = (
        "without_pip_host_pip_python_v1"
    )
    runtime_default_ensurepip_used: Literal[False] = False
    runtime_host_pip_targeting_required: Literal[True] = True
    runtime_system_site_packages_inherited: Literal[False] = False
    vllm_binary_import_probe_required: Literal[True] = True
    vllm_worker_python_policy: Literal["qualified_isolated_runtime_python_v1"] = (
        "qualified_isolated_runtime_python_v1"
    )
    normalization_policy_sha256: str
    prompt_policy_sha256: str
    response_schema_sha256: str
    action_schema_sha256: str
    evidence_archive_filename: Literal[
        "auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip"
    ] = "auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip"
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
    execution_command_available: Literal[False] = False
    next_gate: Literal["bounded_action_extraction_v2_kaggle_execution_package"] = (
        "bounded_action_extraction_v2_kaggle_execution_package"
    )

    @field_validator("binding_id")
    @classmethod
    def validate_binding_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("binding ID must use stable lowercase characters")
        return value

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value

    @field_validator("activation_merge_commit")
    @classmethod
    def validate_activation_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("activation merge commit must be a full lowercase Git SHA")
        return value

    @field_validator(
        "authorization_sha256",
        "activation_manifest_sha256",
        "notebook_sha256",
        "notebook_code_source_sha256",
        "normalization_policy_sha256",
        "prompt_policy_sha256",
        "response_schema_sha256",
        "action_schema_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("notebook binding digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        paths = tuple(binding.path for binding in self.source_bindings)
        if any(count > 1 for count in Counter(paths).values()):
            raise ValueError("notebook source binding paths must be unique")
        expected = (
            (
                "src/auragateway/local_abc/action_extraction_authorization_activation.py",
                _ACTIVATION_SOURCE_BLOB_SHA,
                None,
            ),
            (
                "benchmarks/local_abc/"
                "reconcile_balance_extraction_requalification_authorization_v2.json",
                _AUTHORIZATION_JSON_BLOB_SHA,
                _AUTHORIZATION_SHA256,
            ),
            (
                "benchmarks/local_abc/"
                "reconcile_balance_extraction_authorization_activation_manifest_v2.json",
                _ACTIVATION_MANIFEST_BLOB_SHA,
                _ACTIVATION_MANIFEST_SHA256,
            ),
        )
        observed = tuple(
            (binding.path, binding.git_blob_sha, binding.canonical_sha256)
            for binding in self.source_bindings
        )
        if observed != expected:
            raise ValueError("notebook source bindings drifted from merged PR #88")
        if self.authorization_sha256 != _AUTHORIZATION_SHA256:
            raise ValueError("notebook must bind the exact fresh authorization")
        if self.activation_manifest_sha256 != _ACTIVATION_MANIFEST_SHA256:
            raise ValueError("notebook must bind the activation manifest")
        if self.required_import_modules != _EXPECTED_IMPORT_MODULES:
            raise ValueError("notebook import qualification set drifted")
        return self


class ActionExtractionNotebookQualificationPackageV2(LocalABCContract):
    """Cross-file package proving notebook identity and authorization lineage."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    activation_package: ActionExtractionAuthorizationActivationPackageV2
    binding: ActionExtractionRequalificationNotebookBindingV2
    notebook: ActionExtractionNotebookArtifactFacts

    @model_validator(mode="after")
    def validate_package(self) -> Self:
        authorization = self.activation_package.authorization
        if authorization.fingerprint() != self.binding.authorization_sha256:
            raise ValueError("notebook binding must match the active authorization")
        if self.activation_package.manifest.fingerprint() != (
            self.binding.activation_manifest_sha256
        ):
            raise ValueError("notebook binding must match the activation manifest")
        if authorization.source_merge_commit != "6038f7055e34c6c559b3c41cb919d0cb421b3e55":
            raise ValueError("authorization source lineage drifted")
        if authorization.authorization_consumed:
            raise ValueError("notebook qualification requires an unused authorization")
        if authorization.case_count != self.binding.case_count:
            raise ValueError("notebook case count drifted from authorization")
        hash_fields = (
            "normalization_policy_sha256",
            "prompt_policy_sha256",
            "response_schema_sha256",
            "action_schema_sha256",
        )
        for field_name in hash_fields:
            if getattr(authorization, field_name) != getattr(self.binding, field_name):
                raise ValueError(f"notebook {field_name} drifted from authorization")
        if self.notebook.notebook_sha256 != self.binding.notebook_sha256:
            raise ValueError("binding must match exact notebook bytes")
        if self.notebook.notebook_code_source_sha256 != (self.binding.notebook_code_source_sha256):
            raise ValueError("binding must match exact notebook code source")
        if self.notebook.notebook_code_cell_count != self.binding.notebook_code_cell_count:
            raise ValueError("notebook code-cell count drifted")
        return self


def _notebook_code_sources(notebook: dict[str, Any]) -> tuple[str, ...]:
    sources: list[str] = []
    for cell in cast(list[dict[str, Any]], notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            if not all(isinstance(line, str) for line in source):
                raise ValueError("notebook code source list contains a non-string")
            sources.append("".join(source))
        elif isinstance(source, str):
            sources.append(source)
        else:
            raise ValueError("notebook code source has unsupported type")
    return tuple(sources)


def inspect_action_extraction_notebook_v2(path: Path) -> ActionExtractionNotebookArtifactFacts:
    """Inspect notebook bytes without executing model, GPU, or provider code."""

    notebook = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    code_sources = _notebook_code_sources(notebook)
    if len(code_sources) != _EXPECTED_CODE_CELL_COUNT:
        raise ValueError("notebook must retain exactly 12 code cells")
    has_saved_state = False
    for cell in cast(list[dict[str, Any]], notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None or cell.get("outputs") != []:
            has_saved_state = True
    for index, code in enumerate(code_sources):
        compile(code, f"notebook-cell-{index:02d}", "exec")
    joined = "\n\n# --- CELL BOUNDARY ---\n\n".join(code_sources)
    return ActionExtractionNotebookArtifactFacts(
        notebook_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        notebook_code_source_sha256=hashlib.sha256(joined.encode("utf-8")).hexdigest(),
        notebook_code_cell_count=len(code_sources),
        notebook_has_saved_execution_state=has_saved_state,
        notebook_cells_compile=True,
    )


def load_action_extraction_notebook_binding_v2(
    path: Path,
) -> ActionExtractionRequalificationNotebookBindingV2:
    """Load and validate the canonical notebook binding."""

    return ActionExtractionRequalificationNotebookBindingV2.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_action_extraction_notebook_qualification_package_v2(
    *,
    parent_manifest_path: Path,
    parent_plan_path: Path,
    remediation_manifest_path: Path,
    remediation_plan_path: Path,
    review_path: Path,
    dry_run_path: Path,
    review_manifest_path: Path,
    authorization_path: Path,
    activation_manifest_path: Path,
    notebook_path: Path,
    notebook_binding_path: Path,
) -> ActionExtractionNotebookQualificationPackageV2:
    """Load all assets and validate the complete notebook lineage."""

    activation_package = load_action_extraction_authorization_activation_package_v2(
        parent_manifest_path=parent_manifest_path,
        parent_plan_path=parent_plan_path,
        remediation_manifest_path=remediation_manifest_path,
        remediation_plan_path=remediation_plan_path,
        review_path=review_path,
        dry_run_path=dry_run_path,
        review_manifest_path=review_manifest_path,
        authorization_path=authorization_path,
        activation_manifest_path=activation_manifest_path,
    )
    return ActionExtractionNotebookQualificationPackageV2(
        activation_package=activation_package,
        binding=load_action_extraction_notebook_binding_v2(notebook_binding_path),
        notebook=inspect_action_extraction_notebook_v2(notebook_path),
    )


def canonical_notebook_binding_file_sha256(path: Path) -> str:
    """Validate canonical one-line JSON and return its contract fingerprint."""

    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    if text != f"{canonical}\n":
        raise ValueError(f"JSON artifact is not canonical one-line JSON: {path}")
    return ActionExtractionRequalificationNotebookBindingV2.model_validate(payload).fingerprint()
