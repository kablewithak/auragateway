"""Reconcile verifier v7 raw runtime success with its false-negative summary."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, Self, cast

from pydantic import model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_vllm_cu129_target_directory_install import (
    V7_NOTEBOOK_PATH,
    _load_json_object,
    _notebook_source,
)
from auragateway.local_abc.full_abc_local_vllm_cu129_target_directory_install import (
    validate_repository_package as validate_v7_package,
)

RESULT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_cu129_v7_false_negative_reconciliation_v1.json"
)
CERTIFICATE_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Verifier_V7_False_Negative_Reasoning_Certificate.md"
)
V7_EVIDENCE_DIRECTORY: Final = Path("evidence_vault/local_abc/vllm-cu129-offline-compatibility-v7")

EXPECTED_BASE_COMMIT: Final = "0ba5d809e712cf5af6b4d99ceedc1b457850a94f"
EXPECTED_RESULT_SHA256: Final = "ad865f2d61d1b0939601e4dae1f1a7767574240f1efe9b00c85a14a425e780a4"
EXPECTED_CERTIFICATE_SHA256: Final = (
    "f4b4a6473fbbc9707001b6ea2f78dbd7b46ed1c0e5aa26a783262b38736c2a55"
)
EXPECTED_V7_NOTEBOOK_SHA256: Final = (
    "66fe0df31e49c035d858865749eca1755d5d09ce863b378a9f01fb55ac8bf7fd"
)
EXPECTED_V7_EVIDENCE_ZIP_SHA256: Final = (
    "8db01f1dd47a01ce2a1cd180c177af8c12826acdba8694d16893b2119e8633e7"
)
EXPECTED_V7_INTERNAL_MANIFEST_SHA256: Final = (
    "51588c414216e65fa3db8edf3afa388349c5bbcde1d05277fdafb534a170f997"
)
EXPECTED_V7_EXECUTION_LOG_SHA256: Final = (
    "0e82fca90fbc68688c1a8fbc41dbf42d8cb8bc868786dfa5952f47f7f5107261"
)
EXPECTED_V7_REPOSITORY_MANIFEST_SHA256: Final = (
    "f59e11d1e12f582e404a89a2f26b94910ed1dac90f48c07eaf2614c6b9038a0b"
)
EXPECTED_NVJITLINK_SHA256: Final = (
    "02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f"
)
EXPECTED_CUSPARSE_SHA256: Final = "6d85ab1acdabfe3b5a54aa76bc948c719bcd03e07eede3eb8122b083c1a6ecf7"
EXPECTED_BASE_DISTRIBUTION_SNAPSHOT_SHA256: Final = (
    "031e9ecfcfb5cad68578ae8bbab5d8bcd60676fd233465a7badfe705bdc65db9"
)
REQUIRED_NVJITLINK_SYMBOL: Final = "__nvJitLinkGetErrorLogSize_12_9"

_REQUIRED_PASSED_ROLES: Final = (
    "base_python_runtime",
    "base_venv_import",
    "base_pip_import",
    "base_distribution_snapshot_before",
    "gpu_topology",
    "venv_create_without_pip",
    "target_runtime_identity_before_install",
    "offline_hash_locked_install_via_base_pip_target_directory",
    "target_distribution_inventory",
    "target_dependency_check_via_controlled_python",
    "canonical_process_environment",
    "target_cuda_library_inventory",
    "inherited_nvjitlink_resolution",
    "canonical_nvjitlink_symbol",
    "canonical_cusparse_direct_load",
    "target_process_environment",
    "python_runtime",
    "torch_family_runtime",
    "transformers_runtime",
    "vllm_distribution",
    "vllm_module",
    "vllm_native_extension",
    "base_distribution_snapshot_after",
)

_ROLE_FILENAMES: Final = {
    "base_python_runtime": "10_01_base_python_runtime.json",
    "base_venv_import": "10_02_base_venv_import.json",
    "base_pip_import": "10_03_base_pip_import.json",
    "base_distribution_snapshot_before": ("10_04_base_distribution_snapshot_before.json"),
    "gpu_topology": "10_05_gpu_topology.json",
    "venv_create_without_pip": "10_06_venv_create_without_pip.json",
    "target_runtime_identity_before_install": ("10_07_target_runtime_identity_before_install.json"),
    "offline_hash_locked_install_via_base_pip_target_directory": (
        "10_08_offline_hash_locked_install_via_base_pip_target_directory.json"
    ),
    "target_distribution_inventory": "10_09_target_distribution_inventory.json",
    "target_dependency_check_via_controlled_python": (
        "10_10_target_dependency_check_via_controlled_python.json"
    ),
    "canonical_process_environment": "10_11_canonical_process_environment.json",
    "target_cuda_library_inventory": "10_12_target_cuda_library_inventory.json",
    "inherited_nvjitlink_resolution": "10_13_inherited_nvjitlink_resolution.json",
    "canonical_nvjitlink_symbol": "10_15_canonical_nvjitlink_symbol.json",
    "canonical_cusparse_direct_load": "10_16_canonical_cusparse_direct_load.json",
    "target_process_environment": "10_17_target_process_environment.json",
    "python_runtime": "10_18_python_runtime.json",
    "torch_family_runtime": "10_19_torch_family_runtime.json",
    "transformers_runtime": "10_20_transformers_runtime.json",
    "vllm_distribution": "10_21_vllm_distribution.json",
    "vllm_module": "10_22_vllm_module.json",
    "vllm_native_extension": "10_23_vllm_native_extension.json",
    "base_distribution_snapshot_after": "10_24_base_distribution_snapshot_after.json",
}

_LDD_PATH_PATTERN: Final = re.compile(r"libnvJitLink\.so\.12\s+=>\s+(\S+)")
_PYTHON_DIRECTORY_PATTERN: Final = re.compile(r"python\d+\.\d+")


class SourceEvidenceV1(LocalABCContract):
    """Immutable verifier v7 evidence identities."""

    captured_version: Literal[1]
    evidence_directory: Literal["evidence_vault/local_abc/vllm-cu129-offline-compatibility-v7"]
    evidence_zip_sha256: Literal["8db01f1dd47a01ce2a1cd180c177af8c12826acdba8694d16893b2119e8633e7"]
    execution_log_sha256: Literal[
        "0e82fca90fbc68688c1a8fbc41dbf42d8cb8bc868786dfa5952f47f7f5107261"
    ]
    internal_manifest_sha256: Literal[
        "51588c414216e65fa3db8edf3afa388349c5bbcde1d05277fdafb534a170f997"
    ]
    notebook_sha256: Literal["66fe0df31e49c035d858865749eca1755d5d09ce863b378a9f01fb55ac8bf7fd"]
    repository_manifest_sha256: Literal[
        "f59e11d1e12f582e404a89a2f26b94910ed1dac90f48c07eaf2614c6b9038a0b"
    ]


class ReportedResultV1(LocalABCContract):
    """Original verifier summary retained without reinterpretation."""

    status: Literal["FAILED"]
    first_divergence: Literal["canonical_nvjitlink_resolution"]
    failed_required_roles: tuple[Literal["canonical_nvjitlink_resolution"], ...]
    blocked_required_roles: tuple[str, ...]
    not_executed_required_roles: tuple[str, ...]
    canonical_nvjitlink_resolved_to_target: Literal[False]

    @model_validator(mode="after")
    def validate_role_sets(self) -> Self:
        if self.failed_required_roles != ("canonical_nvjitlink_resolution",):
            raise ValueError("reported failed role set drifted")
        if self.blocked_required_roles or self.not_executed_required_roles:
            raise ValueError("reported downstream role state drifted")
        return self


class StructuralTargetResolutionV1(LocalABCContract):
    """Version-neutral target path result."""

    validation_policy: Literal["VENV_ROOT_AND_TARGET_LIBRARY_INVENTORY"]
    venv_root_source: Literal["target_runtime_identity_before_install.argv[0]"]
    venv_root: str
    resolved_path: str
    inventory_path: str
    expected_library_sha256: Literal[
        "02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f"
    ]
    exact_inventory_path_match: Literal[True]
    resolved_path_within_venv_root: Literal[True]
    active_logic_contains_version_specific_runtime_token: Literal[False]


class EvidenceBackedResultV1(LocalABCContract):
    """Runtime result derived from raw records."""

    runtime_prerequisite_status: Literal["TECHNICALLY_PASSED"]
    aggregate_summary_disposition: Literal["FALSE_NEGATIVE"]
    failure_class: Literal["HARNESS_SEMANTIC_FALSE_NEGATIVE"]
    failure_code: Literal["STALE_RUNTIME_VERSION_PATH_LITERAL"]
    target_first_nvjitlink_resolution: Literal["PASSED"]
    required_nvjitlink_symbol_present: Literal[True]
    torch_cuda_runtime: Literal["PASSED"]
    vllm_module_import: Literal["PASSED"]
    vllm_native_extension_import: Literal["PASSED"]
    base_distribution_metadata_unchanged: Literal[True]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]


class ReasoningCertificateV1(LocalABCContract):
    """Bound causal decision artifact."""

    path: Literal[
        "docs/reports/AuraGateway_CU129_Verifier_V7_False_Negative_Reasoning_Certificate.md"
    ]
    sha256: Literal["f4b4a6473fbbc9707001b6ea2f78dbd7b46ed1c0e5aa26a783262b38736c2a55"]
    result: Literal["REASONING_CHAIN_CONSISTENT"]
    evidence_sufficiency: Literal["SUFFICIENT_FOR_REPOSITORY_RECONCILIATION"]
    rerun_decision: Literal["NOT_JUSTIFIED"]


class ReconciliationSafetyV1(LocalABCContract):
    """Hard stop boundary after repository reconciliation."""

    verifier_v7_rerun_permitted: Literal[False]
    wheelhouse_rematerialization_permitted: Literal[False]
    fresh_authorization_issued: Literal[False]
    model_loading_permitted: Literal[False]
    worker_start_permitted: Literal[False]
    model_requests_performed: Literal[0]
    customer_data_used: Literal[False]
    credentials_used: Literal[False]
    external_spend: Literal[0]
    qualification_claimed: Literal[False]


class VerifierV7FalseNegativeReconciliationV1(LocalABCContract):
    """Typed repository reconciliation decision."""

    schema_version: Literal["1.0.0"]
    repository_base_commit: Literal["0ba5d809e712cf5af6b4d99ceedc1b457850a94f"]
    source_evidence: SourceEvidenceV1
    reported_result: ReportedResultV1
    structural_target_resolution: StructuralTargetResolutionV1
    evidence_backed_result: EvidenceBackedResultV1
    reasoning_certificate: ReasoningCertificateV1
    decision: Literal["VERIFIER_V7_RUNTIME_PREREQUISITE_TECHNICALLY_PASSED_RECONCILED"]
    next_gate: Literal["review_cu129_runtime_integration_for_environment_qualification"]
    safety: ReconciliationSafetyV1
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_non_claims(self) -> Self:
        required = {
            "model load was not performed",
            "workers were not started",
            "cache observability was not qualified",
            "measured A/B/C execution remains unauthorized",
            "no latency, quality, cache, or cost improvement is claimed",
            "production readiness is not claimed",
        }
        if set(self.non_claims) != required:
            raise ValueError("reconciliation non-claims drifted")
        return self


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_stdout(record: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(str(record.get("stdout_excerpt", "")).strip())
    if not isinstance(payload, dict):
        raise RuntimeError("expected JSON object in command stdout")
    return cast(dict[str, Any], payload)


def _validate_repository_manifest(directory: Path) -> int:
    manifest_path = directory / "evidence_sha256.json"
    if _sha256(manifest_path) != EXPECTED_V7_REPOSITORY_MANIFEST_SHA256:
        raise RuntimeError("verifier v7 repository evidence manifest drifted")
    manifest = _load_json_object(manifest_path)
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise RuntimeError("verifier v7 repository evidence manifest is invalid")
    observed: set[str] = set()
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise RuntimeError("verifier v7 repository evidence entry is invalid")
        entry = cast(dict[str, Any], raw_entry)
        relative = entry.get("path")
        if not isinstance(relative, str) or "/" in relative or "\\" in relative:
            raise RuntimeError("verifier v7 repository evidence path is invalid")
        path = directory / relative
        if (
            not path.is_file()
            or path.stat().st_size != entry.get("size_bytes")
            or _sha256(path) != entry.get("sha256")
        ):
            raise RuntimeError(f"verifier v7 evidence identity drifted: {relative}")
        observed.add(relative)
    expected = {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.name != "evidence_sha256.json"
    }
    if observed != expected:
        raise RuntimeError("verifier v7 repository evidence topology drifted")
    return len(entries)


def _validate_internal_manifest(directory: Path) -> int:
    manifest_path = directory / "99_evidence_sha256.json"
    if _sha256(manifest_path) != EXPECTED_V7_INTERNAL_MANIFEST_SHA256:
        raise RuntimeError("verifier v7 internal manifest identity drifted")
    manifest = _load_json_object(manifest_path)
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("verifier v7 internal manifest is invalid")
    observed: set[str] = set()
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise RuntimeError("verifier v7 internal evidence entry is invalid")
        entry = cast(dict[str, Any], raw_entry)
        relative = entry.get("path")
        if not isinstance(relative, str):
            raise RuntimeError("verifier v7 internal evidence path is invalid")
        path = directory / relative
        if (
            not path.is_file()
            or path.stat().st_size != entry.get("size_bytes")
            or _sha256(path) != entry.get("sha256")
        ):
            raise RuntimeError(f"verifier v7 internal evidence drifted: {relative}")
        observed.add(relative)
    expected = {
        path.name
        for path in directory.iterdir()
        if path.is_file()
        and path.name
        not in {
            "99_evidence_sha256.json",
            "execution.log",
            "source_evidence_identity.json",
            "evidence_sha256.json",
        }
    }
    if observed != expected:
        raise RuntimeError("verifier v7 internal evidence topology drifted")
    return len(entries)


def _validate_source_identity(directory: Path) -> None:
    identity = _load_json_object(directory / "source_evidence_identity.json")
    expected = {
        "schema_version": "1.0.0",
        "kaggle_title": "auragateway-cu129-offline-verifier-v7",
        "notebook_path": V7_NOTEBOOK_PATH.as_posix(),
        "notebook_sha256": EXPECTED_V7_NOTEBOOK_SHA256,
        "captured_version": 1,
        "source_artifact": ("auragateway_vllm_cu129_offline_compatibility_evidence_v7.zip"),
        "source_artifact_sha256": EXPECTED_V7_EVIDENCE_ZIP_SHA256,
        "source_artifact_size_bytes": 28203,
        "evidence_file_count": 27,
        "execution_log_sha256": EXPECTED_V7_EXECUTION_LOG_SHA256,
        "execution_log_size_bytes": 2556,
        "complete_execution_log_provided": True,
        "model_requests_performed": 0,
        "qualification_claimed": False,
    }
    drift = sorted(key for key, value in expected.items() if identity.get(key) != value)
    if drift:
        raise RuntimeError("verifier v7 source evidence identity drifted: " + ", ".join(drift))
    if _sha256(directory / "execution.log") != EXPECTED_V7_EXECUTION_LOG_SHA256:
        raise RuntimeError("verifier v7 execution log identity drifted")


def _parse_ldd_resolved_path(stdout: str) -> PurePosixPath:
    match = _LDD_PATH_PATTERN.search(stdout)
    if match is None:
        raise RuntimeError("canonical ldd output lacks nvJitLink resolution")
    return PurePosixPath(match.group(1))


def _derive_venv_root(target_identity: dict[str, Any]) -> PurePosixPath:
    argv = target_identity.get("argv")
    if not isinstance(argv, list) or not argv or not isinstance(argv[0], str):
        raise RuntimeError("target identity argv is invalid")
    python_path = PurePosixPath(argv[0])
    if python_path.name != "python" or python_path.parent.name != "bin":
        raise RuntimeError("target identity Python path is not rooted in VENV_ROOT")
    return python_path.parent.parent


def _is_target_nvjitlink_resolution(
    *,
    venv_root: PurePosixPath,
    resolved_path: PurePosixPath,
    inventory_path: PurePosixPath,
) -> bool:
    if resolved_path != inventory_path:
        return False
    try:
        relative = resolved_path.relative_to(venv_root)
    except ValueError:
        return False
    parts = relative.parts
    if len(parts) != 7:
        return False
    if parts[0] != "lib" or _PYTHON_DIRECTORY_PATTERN.fullmatch(parts[1]) is None:
        return False
    return parts[2:] == (
        "site-packages",
        "nvidia",
        "nvjitlink",
        "lib",
        "libnvJitLink.so.12",
    )


def _validate_structural_target_resolution(directory: Path) -> dict[str, object]:
    target_identity = _load_json_object(
        directory / "10_07_target_runtime_identity_before_install.json"
    )
    inventory = _load_json_object(directory / "10_12_target_cuda_library_inventory.json")
    canonical = _load_json_object(directory / "10_14_canonical_nvjitlink_resolution.json")

    if (
        canonical.get("returncode") != 0
        or canonical.get("timed_out") is not False
        or canonical.get("stderr_excerpt") != ""
    ):
        raise RuntimeError("canonical nvJitLink raw command did not pass")

    nvjitlink = inventory.get("libnvJitLink")
    cusparse = inventory.get("libcusparse")
    if not isinstance(nvjitlink, dict) or not isinstance(cusparse, dict):
        raise RuntimeError("target CUDA library inventory is invalid")
    if (
        nvjitlink.get("sha256") != EXPECTED_NVJITLINK_SHA256
        or cusparse.get("sha256") != EXPECTED_CUSPARSE_SHA256
    ):
        raise RuntimeError("target CUDA library identity drifted")

    resolved_path = _parse_ldd_resolved_path(str(canonical.get("stdout_excerpt", "")))
    inventory_path = PurePosixPath(str(nvjitlink.get("realpath")))
    venv_root = _derive_venv_root(target_identity)
    if not _is_target_nvjitlink_resolution(
        venv_root=venv_root,
        resolved_path=resolved_path,
        inventory_path=inventory_path,
    ):
        raise RuntimeError("canonical loader did not structurally select target nvJitLink")

    argv = canonical.get("argv")
    if not isinstance(argv, list) or len(argv) != 2 or argv[0] != "ldd":
        raise RuntimeError("canonical nvJitLink command shape drifted")
    if PurePosixPath(str(argv[1])) != PurePosixPath(str(cusparse.get("realpath"))):
        raise RuntimeError("canonical ldd target does not match target cuSPARSE inventory")

    return {
        "venv_root": venv_root.as_posix(),
        "resolved_path": resolved_path.as_posix(),
        "inventory_path": inventory_path.as_posix(),
        "exact_inventory_path_match": True,
        "resolved_path_within_venv_root": True,
        "expected_library_sha256": EXPECTED_NVJITLINK_SHA256,
    }


def _validate_v7_notebook_defect(root: Path) -> None:
    path = root / V7_NOTEBOOK_PATH
    if _sha256(path) != EXPECTED_V7_NOTEBOOK_SHA256:
        raise RuntimeError("verifier v7 notebook identity drifted")
    source = _notebook_source(path)
    required = (
        'VENV_ROOT = Path("/kaggle/working/auragateway_vllm_runtime_cu129_v7")',
        '"<working>/auragateway_vllm_runtime_cu129_v6/"',
        '"canonical_nvjitlink_resolution"',
        '"TARGET_NVIDIA_LIBRARIES_PREPENDED"',
    )
    if any(fragment not in source for fragment in required):
        raise RuntimeError("verifier v7 historical defect binding drifted")


def _validate_passed_role(directory: Path, role: str) -> dict[str, Any]:
    record = _load_json_object(directory / _ROLE_FILENAMES[role])
    if (
        record.get("command_role") != role
        or record.get("status") != "PASSED"
        or record.get("returncode") != 0
        or record.get("timed_out") is not False
    ):
        raise RuntimeError(f"verifier v7 passed role drifted: {role}")
    return record


def _validate_v7_evidence(root: Path) -> dict[str, object]:
    directory = root / V7_EVIDENCE_DIRECTORY
    repository_files = _validate_repository_manifest(directory)
    internal_files = _validate_internal_manifest(directory)
    _validate_source_identity(directory)

    input_validation = _load_json_object(directory / "00_input_validation.json")
    if (
        input_validation.get("status") != "PASSED"
        or input_validation.get("package_count") != 176
        or input_validation.get("model_requests_performed") != 0
        or input_validation.get("qualification_claimed") is not False
    ):
        raise RuntimeError("verifier v7 input validation drifted")

    records = {role: _validate_passed_role(directory, role) for role in _REQUIRED_PASSED_ROLES}
    structural = _validate_structural_target_resolution(directory)

    canonical = _load_json_object(directory / "10_14_canonical_nvjitlink_resolution.json")
    if (
        canonical.get("command_role") != "canonical_nvjitlink_resolution"
        or canonical.get("status") != "FAILED"
        or canonical.get("semantic_error") != "canonical loader did not select target nvJitLink"
    ):
        raise RuntimeError("original verifier v7 failed role was not preserved")

    summary = _load_json_object(directory / "90_summary.json")
    if (
        summary.get("status") != "FAILED"
        or summary.get("first_divergence") != "canonical_nvjitlink_resolution"
        or summary.get("failed_required_roles") != ["canonical_nvjitlink_resolution"]
        or summary.get("blocked_required_roles") != []
        or summary.get("not_executed_required_roles") != []
        or summary.get("canonical_nvjitlink_resolved_to_target") is not False
        or summary.get("required_nvjitlink_symbol_present") is not True
        or summary.get("base_distribution_metadata_unchanged") is not True
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("original verifier v7 summary was not preserved")

    symbol = records["canonical_nvjitlink_symbol"]
    if REQUIRED_NVJITLINK_SYMBOL not in str(symbol.get("stdout_excerpt", "")):
        raise RuntimeError("required CUDA 12.9 nvJitLink symbol is absent")

    direct_load = records["canonical_cusparse_direct_load"]
    if str(direct_load.get("stdout_excerpt", "")).strip() != "loaded":
        raise RuntimeError("target cuSPARSE direct load drifted")

    dependency = _load_json_stdout(records["target_dependency_check_via_controlled_python"])
    if (
        dependency.get("distribution_count") != 176
        or dependency.get("evaluated_requirement_count") != 345
        or dependency.get("missing") != []
        or dependency.get("incompatible") != []
        or dependency.get("invalid") != []
    ):
        raise RuntimeError("controlled target dependency proof drifted")

    torch = _load_json_stdout(records["torch_family_runtime"])
    expected_torch = {
        "torch": "2.10.0+cu129",
        "torchaudio": "2.10.0+cu129",
        "torchvision": "0.25.0+cu129",
        "cuda": "12.9",
        "available": True,
        "device_count": 2,
    }
    if torch != expected_torch:
        raise RuntimeError("Torch CUDA runtime proof drifted")

    if str(records["transformers_runtime"].get("stdout_excerpt", "")).strip() != "5.5.3":
        raise RuntimeError("Transformers runtime proof drifted")
    if str(records["vllm_distribution"].get("stdout_excerpt", "")).strip() != "0.19.1":
        raise RuntimeError("vLLM distribution proof drifted")
    if str(records["vllm_module"].get("stdout_excerpt", "")).strip() != "0.19.1":
        raise RuntimeError("vLLM module proof drifted")
    if str(records["vllm_native_extension"].get("stdout_excerpt", "")).strip() != "ok":
        raise RuntimeError("vLLM native extension proof drifted")

    before = _load_json_stdout(records["base_distribution_snapshot_before"])
    after = _load_json_stdout(records["base_distribution_snapshot_after"])
    if before != after:
        raise RuntimeError("base distribution metadata changed")
    if (
        before.get("count") != 952
        or before.get("sha256") != EXPECTED_BASE_DISTRIBUTION_SNAPSHOT_SHA256
    ):
        raise RuntimeError("base distribution snapshot identity drifted")

    log = (directory / "execution.log").read_text(encoding="utf-8")
    required_log = (
        "offline_compatibility_status=FAILED",
        "first_divergence=canonical_nvjitlink_resolution",
        'failed_required_roles=["canonical_nvjitlink_resolution"]',
        "canonical_nvjitlink_resolved_to_target=false",
        "dependency_validation=CONTROLLED_TARGET_METADATA_AND_PACKAGING",
        "base_distribution_metadata_unchanged=true",
        "model_requests_performed=0",
        "qualification_claimed=false",
    )
    if any(fragment not in log for fragment in required_log):
        raise RuntimeError("verifier v7 canonical execution log drifted")

    return {
        "repository_files_verified": repository_files,
        "internal_files_verified": internal_files,
        "reported_status": summary["status"],
        "reported_first_divergence": summary["first_divergence"],
        "structural_resolution": structural,
        "runtime_prerequisite_status": "TECHNICALLY_PASSED",
        "aggregate_summary_disposition": "FALSE_NEGATIVE",
        "model_requests_performed": 0,
        "qualification_claimed": False,
    }


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    baseline = validate_v7_package(root)
    if baseline.get("status") != ("VLLM_CU129_TARGET_DIRECTORY_INSTALL_REMEDIATION_PACKAGE_VALID"):
        raise RuntimeError("verifier v7 repository baseline is not valid")

    result_path = root / RESULT_PATH
    if _sha256(result_path) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("verifier v7 reconciliation record identity drifted")
    decision = VerifierV7FalseNegativeReconciliationV1.model_validate(
        _load_json_object(result_path)
    )
    if decision.repository_base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError("verifier v7 reconciliation base commit drifted")

    _validate_v7_notebook_defect(root)
    evidence = _validate_v7_evidence(root)

    certificate_path = root / CERTIFICATE_PATH
    if _sha256(certificate_path) != EXPECTED_CERTIFICATE_SHA256:
        raise RuntimeError("verifier v7 reasoning certificate identity drifted")
    certificate = certificate_path.read_text(encoding="utf-8")
    required_certificate = (
        "REASONING_CHAIN_CONSISTENT",
        "SUFFICIENT_FOR_REPOSITORY_RECONCILIATION",
        "NOT_JUSTIFIED",
        "HARNESS_SEMANTIC_FALSE_NEGATIVE",
        "VENV_ROOT",
        "RUNTIME_PREREQUISITE_TECHNICALLY_PASSED",
    )
    if any(fragment not in certificate for fragment in required_certificate):
        raise RuntimeError("verifier v7 reasoning certificate drifted")

    observed = cast(dict[str, object], evidence["structural_resolution"])
    recorded = decision.structural_target_resolution
    if (
        recorded.venv_root != observed["venv_root"]
        or recorded.resolved_path != observed["resolved_path"]
        or recorded.inventory_path != observed["inventory_path"]
    ):
        raise RuntimeError("recorded structural target resolution drifted")

    structural_source = inspect.getsource(_is_target_nvjitlink_resolution)
    prohibited_active_tokens = (
        "auragateway_vllm_runtime_cu129_v5",
        "auragateway_vllm_runtime_cu129_v6",
        "auragateway_vllm_runtime_cu129_v7",
    )
    if any(token in structural_source for token in prohibited_active_tokens):
        raise RuntimeError("active reconciliation logic contains a version-specific root")

    return {
        "status": "VLLM_CU129_VERIFIER_V7_FALSE_NEGATIVE_RECONCILIATION_VALID",
        "baseline_status": baseline.get("status"),
        "decision": decision.decision,
        "reported_status": evidence["reported_status"],
        "reported_first_divergence": evidence["reported_first_divergence"],
        "runtime_prerequisite_status": evidence["runtime_prerequisite_status"],
        "aggregate_summary_disposition": evidence["aggregate_summary_disposition"],
        "structural_target_resolution": "PASSED",
        "repository_files_verified": evidence["repository_files_verified"],
        "internal_files_verified": evidence["internal_files_verified"],
        "reasoning_certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
        "verifier_v7_rerun_permitted": False,
        "model_requests_performed": evidence["model_requests_performed"],
        "qualification_claimed": evidence["qualification_claimed"],
        "next_gate": decision.next_gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    print(json.dumps(validate_repository_package(args.repo_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
