"""Validate v4 and linker evidence plus the governed target-first loader verifier v5."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, Self, cast

from pydantic import model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_vllm_cu129_base_pip_target_install import (
    validate_repository_package as validate_v4_package,
)

RESULT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_cu129_target_first_loader_remediation_v1.json"
)
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_target_first_loader_v1.md")
ADR_PATH: Final = Path("docs/adr/2026-07-20-local-abc-vllm-cu129-target-first-loader.md")
CERTIFICATE_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Verifier_V4_Dynamic_Linker_Reasoning_Certificate.md"
)
V4_VERIFIER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v4.ipynb"
)
INSPECTION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_dynamic_linker_inspection_v1.ipynb"
)
V5_VERIFIER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v5.ipynb"
)
V4_EVIDENCE_DIRECTORY: Final = Path("evidence_vault/local_abc/vllm-cu129-offline-compatibility-v4")
V4_EVIDENCE_MANIFEST_PATH: Final = V4_EVIDENCE_DIRECTORY / "evidence_sha256.json"
V4_SOURCE_IDENTITY_PATH: Final = V4_EVIDENCE_DIRECTORY / "source_evidence_identity.json"
INSPECTION_EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/vllm-cu129-dynlink-inspection-v1"
)
INSPECTION_EVIDENCE_MANIFEST_PATH: Final = INSPECTION_EVIDENCE_DIRECTORY / "evidence_sha256.json"
INSPECTION_SOURCE_IDENTITY_PATH: Final = (
    INSPECTION_EVIDENCE_DIRECTORY / "source_evidence_identity.json"
)

EXPECTED_BASE_COMMIT: Final = "a15cc3aa06de177c8cfe54645d67dbf8a647d11e"
EXPECTED_RESULT_SHA256: Final = "488e8c43fd66e0b2c5481ecfcdf667a3679c95fe7581c23096e650a8f735bcaa"
EXPECTED_V4_NOTEBOOK_SHA256: Final = (
    "b6a6e1ed7f33f98959fe346be173b1799a36aecb9e0245c9d2f3beaba1bd0568"
)
EXPECTED_INSPECTION_NOTEBOOK_SHA256: Final = (
    "b05046b010757a275a7570f8e45537b8efd9b568ee0275e00acaae31a5846a97"
)
EXPECTED_V5_NOTEBOOK_SHA256: Final = (
    "ad4d7a533de09965f5562db58c85cb785f2a7f8550906631142e26a34b6e59ab"
)
EXPECTED_V4_EVIDENCE_ZIP_SHA256: Final = (
    "9a4bd10a66c440ffb2628f98ce143e38a1b5cdb06a745497b7b386910816e0fe"
)
EXPECTED_V4_EVIDENCE_MANIFEST_SHA256: Final = (
    "30d87a0ff29adc7bcca431b03ef047e84acba7a2017e48a84517999415ff20d0"
)
EXPECTED_V4_EXECUTION_LOG_SHA256: Final = (
    "8b9b9894a12dee7f301482f2ec6e3aebd155d453a5e5905ad96c5607e7212f44"
)
EXPECTED_INSPECTION_EVIDENCE_ZIP_SHA256: Final = (
    "b241f49a4636c6e427299582c130f4742cf925ad5f541a65f852fa424457d2d0"
)
EXPECTED_INSPECTION_EVIDENCE_MANIFEST_SHA256: Final = (
    "d8bd838ed6cf8f521317f7f0290a0dc0eb111ed41a40515bcd2b6b6f77c99d28"
)
EXPECTED_INSPECTION_EXECUTION_LOG_SHA256: Final = (
    "ff3649a280012f33943c177268ebb45e2c2f7f498dcec290266526a9eea1c83b"
)
EXPECTED_CERTIFICATE_SHA256: Final = (
    "cc8cd04dee8017c42afb4a75e1e3103baa1f32ac4ca222687957b5ccecf2f9a7"
)
EXPECTED_NVJITLINK_SHA256: Final = (
    "02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f"
)
EXPECTED_CUSPARSE_SHA256: Final = "6d85ab1acdabfe3b5a54aa76bc948c719bcd03e07eede3eb8122b083c1a6ecf7"
EXPECTED_INHERITED_NVJITLINK_SHA256: Final = (
    "0369e6867d44b800437de4e146d72c65afc6c75adf677a15c2ecd8e6a7ac135f"
)
REQUIRED_NVJITLINK_SYMBOL: Final = "__nvJitLinkGetErrorLogSize_12_9"
V5_VERIFIER_NAME: Final = "auragateway-cu129-offline-verifier-v5"
V5_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_offline_compatibility_evidence_v5"
_LDD_PATTERN = re.compile(
    r"libnvJitLink\.so\.12\s*=>\s*(?P<path>\S+)",
    re.IGNORECASE,
)


class VerifierV4ExecutionV1(LocalABCContract):
    """Typed verifier v4 Version 1 result."""

    kaggle_title: Literal["auragateway-cu129-offline-verifier-v4"]
    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v4.ipynb"
    ]
    notebook_sha256: Literal["b6a6e1ed7f33f98959fe346be173b1799a36aecb9e0245c9d2f3beaba1bd0568"]
    captured_version: Literal[1]
    evidence_zip_sha256: Literal["9a4bd10a66c440ffb2628f98ce143e38a1b5cdb06a745497b7b386910816e0fe"]
    evidence_manifest_sha256: Literal[
        "30d87a0ff29adc7bcca431b03ef047e84acba7a2017e48a84517999415ff20d0"
    ]
    execution_log_sha256: Literal[
        "8b9b9894a12dee7f301482f2ec6e3aebd155d453a5e5905ad96c5607e7212f44"
    ]
    evidence_vault_path: Literal["evidence_vault/local_abc/vllm-cu129-offline-compatibility-v4"]
    status: Literal["FAILED"]
    input_validation_status: Literal["PASSED"]
    package_installation_status: Literal["PASSED"]
    target_distribution_inventory_status: Literal["PASSED"]
    target_dependency_check_status: Literal["PASSED"]
    gpu_topology_status: Literal["PASSED"]
    base_distribution_metadata_unchanged: Literal[True]
    target_prefix_site_isolation_status: Literal["PASSED"]
    target_process_environment_isolation_status: Literal["NOT_PROVEN"]
    first_divergence: Literal["torch_family_runtime"]
    failure_class: Literal["CUDA_DYNAMIC_LOADER_SYMBOL_RESOLUTION_FAILURE"]
    failure_code: Literal["NVJITLINK_12_9_SYMBOL_UNRESOLVED"]
    required_symbol: Literal["__nvJitLinkGetErrorLogSize_12_9"]
    observed_failed_roles: tuple[str, ...]
    causal_root_role: Literal["torch_family_runtime"]
    package_count: Literal[176]
    package_installation_started: Literal[True]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_failed_roles(self) -> Self:
        expected = (
            "torch_family_runtime",
            "vllm_module",
            "vllm_native_extension",
        )
        if self.observed_failed_roles != expected:
            raise ValueError("verifier v4 failure set drifted")
        return self


class DynamicLinkerInspectionV1(LocalABCContract):
    """Typed dynamic-linker inspection result."""

    kaggle_title: Literal["auragateway-cu129-dynlink-inspect-v1"]
    notebook_path: Literal["notebooks/auragateway_cu129_dynamic_linker_inspection_v1.ipynb"]
    notebook_sha256: Literal["b05046b010757a275a7570f8e45537b8efd9b568ee0275e00acaae31a5846a97"]
    captured_version: Literal[1]
    evidence_zip_sha256: Literal["b241f49a4636c6e427299582c130f4742cf925ad5f541a65f852fa424457d2d0"]
    evidence_manifest_sha256: Literal[
        "d8bd838ed6cf8f521317f7f0290a0dc0eb111ed41a40515bcd2b6b6f77c99d28"
    ]
    execution_log_sha256: Literal[
        "ff3649a280012f33943c177268ebb45e2c2f7f498dcec290266526a9eea1c83b"
    ]
    evidence_vault_path: Literal["evidence_vault/local_abc/vllm-cu129-dynlink-inspection-v1"]
    inspection_status: Literal["COMPLETED"]
    root_cause_assignment: Literal["LOADER_PRECEDENCE_CONFIRMED"]
    required_symbol: Literal["__nvJitLinkGetErrorLogSize_12_9"]
    required_symbol_present_in_governed_nvjitlink: Literal[True]
    governed_nvjitlink_sha256: Literal[
        "02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f"
    ]
    governed_cusparse_sha256: Literal[
        "6d85ab1acdabfe3b5a54aa76bc948c719bcd03e07eede3eb8122b083c1a6ecf7"
    ]
    inherited_nvjitlink_sha256: Literal[
        "0369e6867d44b800437de4e146d72c65afc6c75adf677a15c2ecd8e6a7ac135f"
    ]
    inherited_nvjitlink_resolution: Literal["/usr/local/cuda/lib64/libnvJitLink.so.12"]
    target_first_nvjitlink_resolution: str
    inherited_environment_load_status: Literal["FAILED"]
    target_first_environment_load_status: Literal["PASSED"]
    selected_package_versions: dict[str, str]
    package_installation_performed: Literal[False]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_packages(self) -> Self:
        expected = {
            "nvidia-cuda-runtime-cu12": "12.9.79",
            "nvidia-cusparse-cu12": "12.5.10.65",
            "nvidia-nvjitlink-cu12": "12.9.86",
        }
        if self.selected_package_versions != expected:
            raise ValueError("inspection package identities drifted")
        if "/nvidia-nvjitlink-cu12/" not in self.target_first_nvjitlink_resolution:
            raise ValueError("inspection target-first resolution drifted")
        return self


class ReasoningCertificateV1(LocalABCContract):
    """Bound combined reasoning certificate."""

    path: Literal[
        "docs/reports/AuraGateway_CU129_Verifier_V4_Dynamic_Linker_Reasoning_Certificate.md"
    ]
    sha256: Literal["cc8cd04dee8017c42afb4a75e1e3103baa1f32ac4ca222687957b5ccecf2f9a7"]
    result: Literal["REASONING_CHAIN_CONSISTENT"]
    evidence_sufficiency: Literal["SUFFICIENT_FOR_V5_REMEDIATION_DECISION"]
    root_cause_sufficiency: Literal["SUFFICIENT_FOR_LOADER_PRECEDENCE_ASSIGNMENT"]


class SelectedRemediationV1(LocalABCContract):
    """Canonical target-first process policy."""

    canonical_loader_policy: Literal["TARGET_NVIDIA_LIBRARIES_PREPENDED"]
    python_environment_policy: Literal["DROP_PYTHONPATH_AND_PYTHONHOME_SET_PYTHONNOUSERSITE"]
    inherited_loader_paths_preserved_after_target_paths: Literal[True]
    target_library_identity_verification: Literal["SHA256_AND_LDD_REALPATH"]
    target_environment_creation: Literal["VENV_WITHOUT_PIP"]
    installation_executor: Literal["BASE_PIP_PYTHON_TARGET"]
    base_environment_target: Literal[False]
    wheelhouse_rematerialization_justified: Literal[False]
    package_version_substitution_justified: Literal[False]


class ActiveVerifierV5(LocalABCContract):
    """Governed verifier v5 contract."""

    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v5.ipynb"
    ]
    notebook_sha256: Literal["ad4d7a533de09965f5562db58c85cb785f2a7f8550906631142e26a34b6e59ab"]
    kaggle_title: Literal["auragateway-cu129-offline-verifier-v5"]
    title_character_count: Literal[37]
    output_directory: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v5"]
    output_zip: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v5.zip"]
    accelerator: Literal["T4 x2"]
    internet_enabled: Literal[False]
    secrets_attached: Literal[False]
    input_policy: Literal["EXACTLY_ONE_SUCCESSFUL_MATERIALIZER_OUTPUT"]
    expected_input_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    installation_executor: Literal["BASE_PIP_PYTHON_TARGET"]
    environment_creation_mode: Literal["VENV_WITHOUT_PIP"]
    canonical_loader_policy: Literal["TARGET_NVIDIA_LIBRARIES_PREPENDED"]
    target_process_environment_isolation_required: Literal[True]
    expected_nvjitlink_sha256: Literal[
        "02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f"
    ]
    expected_cusparse_sha256: Literal[
        "6d85ab1acdabfe3b5a54aa76bc948c719bcd03e07eede3eb8122b083c1a6ecf7"
    ]
    required_nvjitlink_symbol: Literal["__nvJitLinkGetErrorLogSize_12_9"]
    downstream_failure_taxonomy: tuple[str, ...]
    model_requests_permitted: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_taxonomy(self) -> Self:
        expected = (
            "FAILED",
            "BLOCKED_BY_UPSTREAM_FAILURE",
            "NOT_EXECUTED",
        )
        if self.downstream_failure_taxonomy != expected:
            raise ValueError("verifier v5 failure taxonomy drifted")
        return self


class RemediationSafetyV1(LocalABCContract):
    """Safety state for verifier v5."""

    qualification_authorization_issued: Literal[False]
    model_loaded: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]


class TargetFirstLoaderRemediationV1(LocalABCContract):
    """Decision record consuming v4 and opening verifier v5."""

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-vllm-cu129-target-first-loader-remediation-v1"]
    repository_base_commit: Literal["a15cc3aa06de177c8cfe54645d67dbf8a647d11e"]
    decision: Literal["APPROVED_FOR_OFFLINE_CU129_TARGET_FIRST_LOADER_VERIFICATION_V5"]
    v4_execution: VerifierV4ExecutionV1
    inspection_execution: DynamicLinkerInspectionV1
    reasoning_certificate: ReasoningCertificateV1
    selected_remediation: SelectedRemediationV1
    active_verifier: ActiveVerifierV5
    safety: RemediationSafetyV1
    next_gate: Literal["run_cu129_offline_runtime_compatibility_verifier_v5"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_non_claims(self) -> Self:
        expected = (
            "target_first_torch_cuda_runtime_not_yet_verified",
            "target_first_vllm_module_import_not_yet_verified",
            "target_first_vllm_native_extension_not_yet_verified",
            "model_not_loaded",
            "tokenizer_not_loaded",
            "qualification_not_authorized",
            "measured_abc_not_authorized",
            "production_readiness_not_claimed",
        )
        if self.non_claims != expected:
            raise ValueError("target-first remediation non-claims drifted")
        return self


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected one JSON object: {path.as_posix()}")
    return cast(dict[str, Any], payload)


def _notebook_source(payload: dict[str, Any]) -> str:
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("notebook cells are missing")
    code_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]
    if len(code_cells) != 1:
        raise RuntimeError("notebook must contain exactly one code cell")
    source = code_cells[0].get("source")
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    if isinstance(source, str):
        return source
    raise RuntimeError("notebook source is invalid")


def prepend_unique_paths(
    target_paths: tuple[str, ...],
    inherited_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Return target-first, first-occurrence-wins path ordering."""

    observed: set[str] = set()
    result: list[str] = []
    for value in target_paths + inherited_paths:
        if not value or value in observed:
            continue
        observed.add(value)
        result.append(value)
    return tuple(result)


def canonicalize_environment(
    base: dict[str, str],
    target_library_paths: tuple[str, ...],
    venv_root: str,
) -> dict[str, str]:
    """Build the reviewed target process environment."""

    environment = dict(base)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    inherited = tuple(
        value for value in environment.get("LD_LIBRARY_PATH", "").split(os.pathsep) if value
    )
    environment["LD_LIBRARY_PATH"] = os.pathsep.join(
        prepend_unique_paths(target_library_paths, inherited)
    )
    environment["VIRTUAL_ENV"] = venv_root
    inherited_path = tuple(
        value for value in environment.get("PATH", "").split(os.pathsep) if value
    )
    environment["PATH"] = os.pathsep.join(
        prepend_unique_paths((str(Path(venv_root) / "bin"),), inherited_path)
    )
    return environment


def parse_ldd_nvjitlink_resolution(text: str) -> str | None:
    """Extract the nvJitLink resolution from ldd output."""

    match = _LDD_PATTERN.search(text)
    return None if match is None else match.group("path")


def classify_causal_roles(
    failed_roles: tuple[str, ...],
    torch_status: str,
) -> dict[str, tuple[str, ...]]:
    """Classify vLLM failures as blocked when Torch is the causal root."""

    if torch_status == "FAILED":
        observed = tuple(role for role in failed_roles if role == "torch_family_runtime")
        blocked = tuple(
            role for role in ("vllm_module", "vllm_native_extension") if role in failed_roles
        )
        return {"observed": observed, "blocked": blocked}
    return {"observed": failed_roles, "blocked": ()}


def _validate_evidence_directory(
    root: Path,
    *,
    directory: Path,
    manifest_path: Path,
    expected_manifest_sha256: str,
    expected_file_count: int,
) -> int:
    manifest = _load_json_object(root / manifest_path)
    files = manifest.get("files")
    if manifest.get("schema_version") != "1.0.0" or not isinstance(files, list):
        raise RuntimeError("evidence manifest is invalid")
    if len(files) != expected_file_count:
        raise RuntimeError("evidence manifest file count drifted")
    observed_paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise RuntimeError("evidence manifest entry is invalid")
        relative_raw = entry.get("path")
        digest = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if (
            not isinstance(relative_raw, str)
            or not isinstance(digest, str)
            or not isinstance(size_bytes, int)
        ):
            raise RuntimeError("evidence manifest fields are invalid")
        relative = PurePosixPath(relative_raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("evidence path is unsafe")
        if relative_raw in observed_paths:
            raise RuntimeError("evidence paths are not unique")
        observed_paths.add(relative_raw)
        path = root / directory / Path(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("evidence file is missing or unsafe")
        if _file_sha256(path) != digest or path.stat().st_size != size_bytes:
            raise RuntimeError("evidence identity drifted")
    if _file_sha256(root / manifest_path) != expected_manifest_sha256:
        raise RuntimeError("evidence manifest raw identity drifted")
    return len(files) + 1


def _validate_v4_evidence(root: Path) -> dict[str, object]:
    verified = _validate_evidence_directory(
        root,
        directory=V4_EVIDENCE_DIRECTORY,
        manifest_path=V4_EVIDENCE_MANIFEST_PATH,
        expected_manifest_sha256=EXPECTED_V4_EVIDENCE_MANIFEST_SHA256,
        expected_file_count=23,
    )
    source = _load_json_object(root / V4_SOURCE_IDENTITY_PATH)
    expected_source = {
        "source_artifact_sha256": EXPECTED_V4_EVIDENCE_ZIP_SHA256,
        "source_artifact_size_bytes": 15130,
        "execution_log_sha256": EXPECTED_V4_EXECUTION_LOG_SHA256,
        "execution_log_size_bytes": 2437,
        "kaggle_title": "auragateway-cu129-offline-verifier-v4",
        "notebook_sha256": EXPECTED_V4_NOTEBOOK_SHA256,
        "captured_version": 1,
        "complete_execution_log_provided": True,
        "evidence_file_count": 21,
        "model_requests_performed": 0,
        "qualification_claimed": False,
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_source.items()
            if source.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("v4 source identity drifted: " + ", ".join(drift))

    input_validation = _load_json_object(root / V4_EVIDENCE_DIRECTORY / "00_input_validation.json")
    install = _load_json_object(
        root / V4_EVIDENCE_DIRECTORY / "10_09_offline_hash_locked_install_via_base_pip.json"
    )
    inventory = _load_json_object(
        root / V4_EVIDENCE_DIRECTORY / "10_10_target_distribution_inventory.json"
    )
    dependency = _load_json_object(
        root / V4_EVIDENCE_DIRECTORY / "10_11_target_dependency_check_via_base_pip.json"
    )
    torch = _load_json_object(root / V4_EVIDENCE_DIRECTORY / "10_13_torch_family_runtime.json")
    summary = _load_json_object(root / V4_EVIDENCE_DIRECTORY / "90_summary.json")
    stderr = torch.get("stderr_excerpt")
    if (
        input_validation.get("status") != "PASSED"
        or input_validation.get("package_count") != 176
        or input_validation.get("manifest_entry_count") != 182
        or input_validation.get("total_wheel_bytes") != 5727339111
    ):
        raise RuntimeError("v4 input validation evidence drifted")
    if install.get("status") != "PASSED" or install.get("returncode") != 0:
        raise RuntimeError("v4 offline installation evidence drifted")
    if inventory.get("status") != "PASSED":
        raise RuntimeError("v4 target inventory evidence drifted")
    if dependency.get("status") != "PASSED" or "No broken requirements found." not in str(
        dependency.get("stdout_excerpt")
    ):
        raise RuntimeError("v4 dependency evidence drifted")
    if (
        torch.get("command_role") != "torch_family_runtime"
        or torch.get("status") != "FAILED"
        or torch.get("returncode") != 1
        or not isinstance(stderr, str)
        or REQUIRED_NVJITLINK_SYMBOL not in stderr
    ):
        raise RuntimeError("v4 Torch failure evidence drifted")
    if (
        summary.get("status") != "FAILED"
        or summary.get("first_divergence") != "torch_family_runtime"
        or summary.get("failed_required_roles")
        != ["torch_family_runtime", "vllm_module", "vllm_native_extension"]
        or summary.get("package_installation_started") is not True
        or summary.get("base_distribution_metadata_unchanged") is not True
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("v4 summary evidence drifted")
    return {
        "evidence_files_verified": verified,
        "input_validation_status": input_validation["status"],
        "installation_status": install["status"],
        "first_divergence": summary["first_divergence"],
        "failure_code": "NVJITLINK_12_9_SYMBOL_UNRESOLVED",
    }


def _validate_inspection_evidence(root: Path) -> dict[str, object]:
    verified = _validate_evidence_directory(
        root,
        directory=INSPECTION_EVIDENCE_DIRECTORY,
        manifest_path=INSPECTION_EVIDENCE_MANIFEST_PATH,
        expected_manifest_sha256=EXPECTED_INSPECTION_EVIDENCE_MANIFEST_SHA256,
        expected_file_count=14,
    )
    source = _load_json_object(root / INSPECTION_SOURCE_IDENTITY_PATH)
    expected_source = {
        "source_artifact_sha256": EXPECTED_INSPECTION_EVIDENCE_ZIP_SHA256,
        "source_artifact_size_bytes": 11410,
        "execution_log_sha256": EXPECTED_INSPECTION_EXECUTION_LOG_SHA256,
        "execution_log_size_bytes": 2294,
        "kaggle_title": "auragateway-cu129-dynlink-inspect-v1",
        "notebook_path": INSPECTION_NOTEBOOK_PATH.as_posix(),
        "notebook_sha256": EXPECTED_INSPECTION_NOTEBOOK_SHA256,
        "captured_version": 1,
        "complete_execution_log_provided": True,
        "evidence_file_count": 12,
        "model_requests_performed": 0,
        "qualification_claimed": False,
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_source.items()
            if source.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("inspection source identity drifted: " + ", ".join(drift))

    candidates = _load_json_object(
        root / INSPECTION_EVIDENCE_DIRECTORY / "50_nvjitlink_candidates.json"
    )
    inherited = _load_json_object(
        root / INSPECTION_EVIDENCE_DIRECTORY / "60_inherited_environment_ldd.json"
    )
    target = _load_json_object(
        root / INSPECTION_EVIDENCE_DIRECTORY / "61_target_first_environment_ldd.json"
    )
    inherited_load = _load_json_object(
        root / INSPECTION_EVIDENCE_DIRECTORY / "70_inherited_environment_cusparse_load.json"
    )
    target_load = _load_json_object(
        root / INSPECTION_EVIDENCE_DIRECTORY / "71_target_first_environment_cusparse_load.json"
    )
    summary = _load_json_object(root / INSPECTION_EVIDENCE_DIRECTORY / "90_summary.json")
    candidate_records = candidates.get("candidates")
    if not isinstance(candidate_records, list) or len(candidate_records) != 3:
        raise RuntimeError("inspection nvJitLink candidates drifted")
    target_candidate = next(
        (
            entry
            for entry in candidate_records
            if isinstance(entry, dict) and entry.get("sha256") == EXPECTED_NVJITLINK_SHA256
        ),
        None,
    )
    inherited_candidate = next(
        (
            entry
            for entry in candidate_records
            if isinstance(entry, dict)
            and entry.get("sha256") == EXPECTED_INHERITED_NVJITLINK_SHA256
        ),
        None,
    )
    if (
        not isinstance(target_candidate, dict)
        or target_candidate.get("required_symbol_present") is not True
        or not isinstance(inherited_candidate, dict)
        or inherited_candidate.get("required_symbol_present") is not False
    ):
        raise RuntimeError("inspection symbol evidence drifted")
    if "/usr/local/cuda/lib64/libnvJitLink.so.12" not in str(
        inherited.get("stdout_excerpt")
    ) or "/nvidia-nvjitlink-cu12/" not in str(target.get("stdout_excerpt")):
        raise RuntimeError("inspection ldd evidence drifted")
    if inherited_load.get("status") != "FAILED" or target_load.get("status") != "PASSED":
        raise RuntimeError("inspection direct-load evidence drifted")
    if (
        summary.get("inspection_status") != "COMPLETED"
        or summary.get("root_cause_assignment") != "LOADER_PRECEDENCE_CONFIRMED"
        or summary.get("required_symbol_present_in_extracted_nvjitlink") is not True
        or summary.get("inherited_environment_load_status") != "FAILED"
        or summary.get("target_first_environment_load_status") != "PASSED"
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("inspection summary evidence drifted")
    return {
        "evidence_files_verified": verified,
        "inspection_status": summary["inspection_status"],
        "root_cause_assignment": summary["root_cause_assignment"],
        "inherited_load_status": summary["inherited_environment_load_status"],
        "target_first_load_status": summary["target_first_environment_load_status"],
    }


def _validate_v5_notebook(root: Path) -> dict[str, object]:
    path = root / V5_VERIFIER_PATH
    payload = _load_json_object(path)
    metadata = payload.get("metadata")
    if payload.get("nbformat") != 4 or not isinstance(metadata, dict):
        raise RuntimeError("verifier v5 notebook structure drifted")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise RuntimeError("verifier v5 metadata is missing")
    expected_metadata = {
        "schema_version": "5.0.0",
        "notebook_name": V5_VERIFIER_NAME,
        "diagnostic_only": True,
        "internet_required": False,
        "accelerator": "T4 x2",
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "model_requests_permitted": 0,
        "qualification_claimed": False,
        "input_directory_name": "auragateway_vllm_cu129_wheelhouse_v1",
        "installation_executor": "BASE_PIP_PYTHON_TARGET",
        "minimum_base_pip_version": "22.3",
        "canonical_loader_policy": "TARGET_NVIDIA_LIBRARIES_PREPENDED",
        "supersedes_notebook": V4_VERIFIER_PATH.as_posix(),
        "supersession_reason": "CUDA_12_9_TARGET_LIBRARY_PRECEDENCE_REQUIRED",
        "source_inspection_evidence_zip_sha256": (EXPECTED_INSPECTION_EVIDENCE_ZIP_SHA256),
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_metadata.items()
            if auragateway.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("verifier v5 metadata drifted: " + ", ".join(drift))

    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("verifier v5 cells are invalid")
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None or cell.get("outputs") != []:
            raise RuntimeError("verifier v5 contains execution state")

    source = _notebook_source(payload)
    compile(source, path.as_posix(), "exec")
    required_fragments = (
        'NOTEBOOK_NAME = "auragateway-cu129-offline-verifier-v5"',
        '"TARGET_NVIDIA_LIBRARIES_PREPENDED"',
        'environment.pop("PYTHONPATH", None)',
        'environment.pop("PYTHONHOME", None)',
        'environment["PYTHONNOUSERSITE"] = "1"',
        '"LD_LIBRARY_PATH"',
        '"target_cuda_library_inventory"',
        EXPECTED_NVJITLINK_SHA256,
        EXPECTED_CUSPARSE_SHA256,
        REQUIRED_NVJITLINK_SYMBOL,
        '"canonical_nvjitlink_resolution"',
        '"canonical_nvjitlink_symbol"',
        '"canonical_cusparse_direct_load"',
        '"target_process_environment"',
        '"torch_family_runtime"',
        '"vllm_module"',
        '"vllm_native_extension"',
        '"BLOCKED_BY_UPSTREAM_FAILURE"',
        '"model_requests_performed=0"',
        '"qualification_claimed=false"',
        '"upload_only_this_file=true"',
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        raise RuntimeError("verifier v5 source lacks reviewed fragments: " + ", ".join(missing))
    prohibited = (
        "from_pretrained(",
        "AutoModel",
        "AutoTokenizer",
        "LLM(",
        ".generate(",
        "requests.get(",
        "urllib.request",
    )
    if any(fragment in source for fragment in prohibited):
        raise RuntimeError("verifier v5 contains prohibited execution behavior")
    torch_index = source.index('"torch_family_runtime"')
    vllm_index = source.rindex('"vllm_module"')
    dependency_index = source.rfind('"torch_family_runtime"', 0, vllm_index)
    if dependency_index < torch_index:
        raise RuntimeError("vLLM module is not causally dependent on Torch")
    observed_sha256 = _file_sha256(path)
    if observed_sha256 != EXPECTED_V5_NOTEBOOK_SHA256:
        raise RuntimeError("verifier v5 raw identity drifted")
    return {
        "notebook_sha256": observed_sha256,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "execution_state_present": False,
    }


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate v4, inspection, and target-first verifier v5 package."""

    root = repo_root.resolve()
    baseline = validate_v4_package(root)
    if baseline.get("status") != ("VLLM_CU129_BASE_PIP_TARGET_INSTALL_REMEDIATION_PACKAGE_VALID"):
        raise RuntimeError("verifier v4 baseline is not valid")

    result = TargetFirstLoaderRemediationV1.model_validate(_load_json_object(root / RESULT_PATH))
    if _file_sha256(root / RESULT_PATH) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("target-first result raw identity drifted")
    if result.repository_base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError("target-first result base commit drifted")

    if _file_sha256(root / V4_VERIFIER_PATH) != EXPECTED_V4_NOTEBOOK_SHA256:
        raise RuntimeError("verifier v4 historical identity drifted")
    if _file_sha256(root / INSPECTION_NOTEBOOK_PATH) != EXPECTED_INSPECTION_NOTEBOOK_SHA256:
        raise RuntimeError("inspection notebook identity drifted")

    v4_evidence = _validate_v4_evidence(root)
    inspection = _validate_inspection_evidence(root)
    verifier = _validate_v5_notebook(root)

    if _file_sha256(root / CERTIFICATE_PATH) != EXPECTED_CERTIFICATE_SHA256:
        raise RuntimeError("combined reasoning certificate identity drifted")
    certificate = (root / CERTIFICATE_PATH).read_text(encoding="utf-8")
    required_certificate_fragments = (
        "REASONING_CHAIN_CONSISTENT",
        "SUFFICIENT_FOR_V5_REMEDIATION_DECISION",
        "SUFFICIENT_FOR_LOADER_PRECEDENCE_ASSIGNMENT",
        "LOADER_PRECEDENCE_CONFIRMED",
        "No wheelhouse rematerialization or package-version substitution is justified",
    )
    if any(fragment not in certificate for fragment in required_certificate_fragments):
        raise RuntimeError("combined reasoning certificate drifted")

    adr = (root / ADR_PATH).read_text(encoding="utf-8")
    required_adr_fragments = (
        "Status: Accepted",
        "LOADER_PRECEDENCE_CONFIRMED",
        EXPECTED_V4_EVIDENCE_ZIP_SHA256,
        EXPECTED_INSPECTION_EVIDENCE_ZIP_SHA256,
        EXPECTED_CERTIFICATE_SHA256,
        EXPECTED_V5_NOTEBOOK_SHA256,
        EXPECTED_NVJITLINK_SHA256,
        EXPECTED_CUSPARSE_SHA256,
        "TARGET_NVIDIA_LIBRARIES_PREPENDED",
        "PYTHONNOUSERSITE=1",
    )
    if any(fragment not in adr for fragment in required_adr_fragments):
        raise RuntimeError("target-first ADR drifted")

    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    required_runbook_fragments = (
        "APPROVED_FOR_OFFLINE_CU129_BASE_PIP_TARGET_INSTALL_VERIFICATION_V4",
        "run_cu129_offline_runtime_compatibility_verifier_v4",
        "APPROVED_FOR_OFFLINE_CU129_TARGET_FIRST_LOADER_VERIFICATION_V5",
        "run_cu129_offline_runtime_compatibility_verifier_v5",
        "LOADER_PRECEDENCE_CONFIRMED",
        V5_VERIFIER_NAME,
        V5_OUTPUT_DIRECTORY,
        EXPECTED_V5_NOTEBOOK_SHA256,
        EXPECTED_V4_EVIDENCE_ZIP_SHA256,
        EXPECTED_INSPECTION_EVIDENCE_ZIP_SHA256,
        "canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED",
        "Accelerator: T4 x2",
        "Internet: Off",
        "Inputs: exactly the successful Version 1 materializer output",
        "Do not rerun verifier v4",
        "Do not rerun the dynamic-linker inspection",
        "package_count=176",
        "zero downloads",
    )
    if any(fragment not in runbook for fragment in required_runbook_fragments):
        raise RuntimeError("CUDA 12.9 target-first runbook drifted")

    return {
        "status": "VLLM_CU129_TARGET_FIRST_LOADER_REMEDIATION_PACKAGE_VALID",
        "decision": result.decision,
        "record_sha256": EXPECTED_RESULT_SHA256,
        "repository_base_commit": result.repository_base_commit,
        "v4_evidence_zip_sha256": EXPECTED_V4_EVIDENCE_ZIP_SHA256,
        "v4_evidence_manifest_sha256": EXPECTED_V4_EVIDENCE_MANIFEST_SHA256,
        "v4_evidence_files_verified": v4_evidence["evidence_files_verified"],
        "v4_input_validation_status": v4_evidence["input_validation_status"],
        "v4_installation_status": v4_evidence["installation_status"],
        "v4_first_divergence": v4_evidence["first_divergence"],
        "v4_failure_code": v4_evidence["failure_code"],
        "inspection_evidence_zip_sha256": EXPECTED_INSPECTION_EVIDENCE_ZIP_SHA256,
        "inspection_evidence_manifest_sha256": (EXPECTED_INSPECTION_EVIDENCE_MANIFEST_SHA256),
        "inspection_evidence_files_verified": inspection["evidence_files_verified"],
        "inspection_status": inspection["inspection_status"],
        "root_cause_assignment": inspection["root_cause_assignment"],
        "inherited_load_status": inspection["inherited_load_status"],
        "target_first_load_status": inspection["target_first_load_status"],
        "reasoning_certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
        "active_verifier_notebook_sha256": verifier["notebook_sha256"],
        "active_verifier_kaggle_title": V5_VERIFIER_NAME,
        "active_verifier_title_character_count": len(V5_VERIFIER_NAME),
        "canonical_loader_policy": result.active_verifier.canonical_loader_policy,
        "qualification_authorization_issued": (result.safety.qualification_authorization_issued),
        "model_requests_performed": result.safety.model_requests_performed,
        "qualification_claimed": result.active_verifier.qualification_claimed,
        "next_gate": result.next_gate,
    }


def main() -> int:
    """Validate the repository package and print canonical JSON."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(validate_repository_package(args.repo_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
