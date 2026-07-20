"""Validate verifier v5/startup evidence and the controlled-startup verifier v6."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, Self, cast

from pydantic import model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_vllm_cu129_target_first_loader import (
    validate_repository_package as validate_v5_package,
)

RESULT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_cu129_controlled_python_startup_remediation_v1.json"
)
ADR_PATH: Final = Path("docs/adr/2026-07-21-local-abc-vllm-cu129-controlled-python-startup.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_controlled_python_startup_v1.md")
CERTIFICATE_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Verifier_V5_Python_Startup_Reasoning_Certificate.md"
)
STARTUP_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_python_startup_inspection_v1.ipynb"
)
V6_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v6.ipynb"
)
V5_EVIDENCE_DIRECTORY: Final = Path("evidence_vault/local_abc/vllm-cu129-offline-compatibility-v5")
STARTUP_EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/vllm-cu129-python-startup-inspection-v1"
)

EXPECTED_BASE_COMMIT: Final = "eb81a61a99f6839794a0ea4c4f90b2cb8dc7e4f3"
EXPECTED_RESULT_SHA256: Final = "4d8e439e652916892777272219784c7197c849dbf26717f2e7403d1acfd9813a"
EXPECTED_CERTIFICATE_SHA256: Final = (
    "d9b228d6ee891e72146794fd0a171ad22354ae8e5195d8b14ae6b2f6bb221bfd"
)
EXPECTED_STARTUP_NOTEBOOK_SHA256: Final = (
    "17395499ea760f021b05f252492e9b7fd3b2be48cd07650caa14e07263ef3e85"
)
EXPECTED_V6_NOTEBOOK_SHA256: Final = (
    "48d4ee3a9dfce1eb4634a37e9e75fc5042d11d30cb0860c8455e8815c3b4e4f0"
)
EXPECTED_V5_EVIDENCE_ZIP_SHA256: Final = (
    "303879f21a0245f566a6df39e950afe90e8f15799a819e889a3a75b20fc97ae6"
)
EXPECTED_V5_EVIDENCE_MANIFEST_SHA256: Final = (
    "798b12fcf2c4bafc1f7bcc2eb26992e24284187d968449e1cdb8869a2e6ace38"
)
EXPECTED_V5_EXECUTION_LOG_SHA256: Final = (
    "1ff315f4438fa62bc3f2ad92a369b1f5fa3d4d836f27f2e4e209fd47b4cb2056"
)
EXPECTED_STARTUP_EVIDENCE_ZIP_SHA256: Final = (
    "f44aa81e4596cf19fac9a28743662b1b53531052e4e3a9dd78f666ab75030ee8"
)
EXPECTED_STARTUP_EVIDENCE_MANIFEST_SHA256: Final = (
    "963f4c5f0a837ed0851bca291cee118abe1309441af1f8d3f77868ba4429b5d8"
)
EXPECTED_STARTUP_EXECUTION_LOG_SHA256: Final = (
    "ea49d9732e208ecb0447a777204ef9871f12e26b12a6cb15b563c3a27ec55a64"
)
V6_VERIFIER_NAME: Final = "auragateway-cu129-offline-verifier-v6"
V6_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_offline_compatibility_evidence_v6"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class VerifierV5ExecutionV1(LocalABCContract):
    """Typed verifier v5 Version 1 diagnostic result."""

    kaggle_title: Literal["auragateway-cu129-offline-verifier-v5"]
    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v5.ipynb"
    ]
    notebook_sha256: Literal["ad4d7a533de09965f5562db58c85cb785f2a7f8550906631142e26a34b6e59ab"]
    captured_version: Literal[1]
    evidence_zip_sha256: Literal["303879f21a0245f566a6df39e950afe90e8f15799a819e889a3a75b20fc97ae6"]
    evidence_manifest_sha256: Literal[
        "798b12fcf2c4bafc1f7bcc2eb26992e24284187d968449e1cdb8869a2e6ace38"
    ]
    execution_log_sha256: Literal[
        "1ff315f4438fa62bc3f2ad92a369b1f5fa3d4d836f27f2e4e209fd47b4cb2056"
    ]
    evidence_vault_path: Literal["evidence_vault/local_abc/vllm-cu129-offline-compatibility-v5"]
    status: Literal["FAILED"]
    input_validation_status: Literal["PASSED"]
    venv_creation_status: Literal["PASSED"]
    target_identity_returncode: Literal[0]
    target_identity_semantic_status: Literal["FAILED"]
    first_divergence: Literal["target_runtime_identity_before_install"]
    failure_class: Literal["TARGET_PYTHON_STARTUP_CUSTOMIZATION_LEAK"]
    failure_code: Literal["BASE_SITECUSTOMIZE_IMPORT_FAILED"]
    observed_stderr: Literal["ModuleNotFoundError: No module named 'wrapt'"]
    package_installation_started: Literal[False]
    loader_remediation_tested: Literal[False]
    base_distribution_metadata_unchanged: Literal[True]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]


class StartupInspectionV1(LocalABCContract):
    """Typed controlled-startup inspection result."""

    kaggle_title: Literal["auragateway-cu129-python-startup-inspect-v1"]
    notebook_path: Literal["notebooks/auragateway_cu129_python_startup_inspection_v1.ipynb"]
    notebook_sha256: Literal["17395499ea760f021b05f252492e9b7fd3b2be48cd07650caa14e07263ef3e85"]
    captured_version: Literal[1]
    evidence_zip_sha256: Literal["f44aa81e4596cf19fac9a28743662b1b53531052e4e3a9dd78f666ab75030ee8"]
    evidence_manifest_sha256: Literal[
        "963f4c5f0a837ed0851bca291cee118abe1309441af1f8d3f77868ba4429b5d8"
    ]
    execution_log_sha256: Literal[
        "ea49d9732e208ecb0447a777204ef9871f12e26b12a6cb15b563c3a27ec55a64"
    ]
    evidence_vault_path: Literal["evidence_vault/local_abc/vllm-cu129-python-startup-inspection-v1"]
    inspection_status: Literal["COMPLETED"]
    disposition: Literal["CONTROLLED_SITE_BOOTSTRAP_CONFIRMED"]
    sanitized_default_startup_status: Literal["WARNING"]
    isolated_mode_startup_status: Literal["WARNING"]
    no_site_startup_status: Literal["PREFIX_NOT_INITIALIZED"]
    controlled_site_bootstrap_status: Literal["PASSED"]
    controlled_site_bootstrap_confirmed: Literal[True]
    external_package_paths: tuple[str, ...]
    package_installation_performed: Literal[False]
    wheelhouse_attached: Literal[False]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_paths(self) -> Self:
        if self.external_package_paths:
            raise ValueError("startup inspection external package paths drifted")
        return self


class ReasoningCertificateV1(LocalABCContract):
    """Bound verifier v5 startup reasoning certificate."""

    path: Literal[
        "docs/reports/AuraGateway_CU129_Verifier_V5_Python_Startup_Reasoning_Certificate.md"
    ]
    sha256: Literal["d9b228d6ee891e72146794fd0a171ad22354ae8e5195d8b14ae6b2f6bb221bfd"]
    result: Literal["REASONING_CHAIN_CONSISTENT"]
    evidence_sufficiency: Literal["SUFFICIENT_FOR_V6_REMEDIATION_DECISION"]
    root_cause_sufficiency: Literal["SUFFICIENT_FOR_TARGET_PYTHON_STARTUP_CUSTOMIZATION_ASSIGNMENT"]


class SelectedRemediationV1(LocalABCContract):
    """Controlled Python startup and target-first loader policy."""

    python_startup_policy: Literal["NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"]
    sitecustomize_policy: Literal["CONTROLLED_SENTINEL_BEFORE_SITE_MAIN"]
    usercustomize_policy: Literal["CONTROLLED_SENTINEL_BEFORE_SITE_MAIN"]
    external_package_path_policy: Literal["REMOVE_NON_TARGET_SITE_AND_DIST_PACKAGES"]
    canonical_loader_policy: Literal["TARGET_NVIDIA_LIBRARIES_PREPENDED"]
    target_environment_creation: Literal["VENV_WITHOUT_PIP"]
    installation_executor: Literal["BASE_PIP_PYTHON_TARGET"]
    base_environment_target: Literal[False]
    wheelhouse_rematerialization_justified: Literal[False]
    package_version_substitution_justified: Literal[False]


class ActiveVerifierV6(LocalABCContract):
    """Governed verifier v6 contract."""

    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v6.ipynb"
    ]
    notebook_sha256: Literal["48d4ee3a9dfce1eb4634a37e9e75fc5042d11d30cb0860c8455e8815c3b4e4f0"]
    kaggle_title: Literal["auragateway-cu129-offline-verifier-v6"]
    title_character_count: Literal[37]
    output_directory: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v6"]
    output_zip: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v6.zip"]
    accelerator: Literal["T4 x2"]
    internet_enabled: Literal[False]
    secrets_attached: Literal[False]
    input_policy: Literal["EXACTLY_ONE_SUCCESSFUL_MATERIALIZER_OUTPUT"]
    expected_input_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    python_startup_policy: Literal["NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"]
    canonical_loader_policy: Literal["TARGET_NVIDIA_LIBRARIES_PREPENDED"]
    controlled_target_roles: tuple[str, ...]
    model_requests_permitted: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_roles(self) -> Self:
        expected = (
            "target_runtime_identity_before_install",
            "target_distribution_inventory",
            "canonical_cusparse_direct_load",
            "target_process_environment",
            "python_runtime",
            "torch_family_runtime",
            "transformers_runtime",
            "vllm_distribution",
            "vllm_module",
            "vllm_native_extension",
        )
        if self.controlled_target_roles != expected:
            raise ValueError("controlled target role set drifted")
        return self


class RemediationSafetyV1(LocalABCContract):
    """Safety boundary for verifier v6."""

    qualification_authorization_issued: Literal[False]
    model_loaded: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]


class ControlledPythonStartupRemediationV1(LocalABCContract):
    """Decision record consuming v5 and startup-inspection evidence."""

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-vllm-cu129-controlled-python-startup-remediation-v1"]
    repository_base_commit: Literal["eb81a61a99f6839794a0ea4c4f90b2cb8dc7e4f3"]
    decision: Literal["APPROVED_FOR_OFFLINE_CU129_CONTROLLED_PYTHON_STARTUP_VERIFICATION_V6"]
    verifier_v5_execution: VerifierV5ExecutionV1
    startup_inspection: StartupInspectionV1
    reasoning_certificate: ReasoningCertificateV1
    selected_remediation: SelectedRemediationV1
    active_verifier: ActiveVerifierV6
    safety: RemediationSafetyV1
    next_gate: Literal["run_cu129_offline_runtime_compatibility_verifier_v6"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_non_claims(self) -> Self:
        expected = (
            "verifier_v6_offline_install_not_yet_verified",
            "verifier_v6_target_first_nvjitlink_resolution_not_yet_verified",
            "verifier_v6_torch_cuda_runtime_not_yet_verified",
            "verifier_v6_vllm_module_not_yet_verified",
            "verifier_v6_vllm_native_extension_not_yet_verified",
            "model_not_loaded",
            "qualification_not_authorized",
            "measured_abc_not_authorized",
            "production_readiness_not_claimed",
        )
        if self.non_claims != expected:
            raise ValueError("controlled-startup non-claims drifted")
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


def _validate_vault(
    root: Path,
    directory: Path,
    *,
    expected_manifest_sha256: str,
) -> int:
    manifest_path = root / directory / "evidence_sha256.json"
    if _file_sha256(manifest_path) != expected_manifest_sha256:
        raise RuntimeError(f"evidence manifest identity drifted: {directory}")
    manifest = _load_json_object(manifest_path)
    files = manifest.get("files")
    if manifest.get("schema_version") != "1.0.0" or not isinstance(files, list):
        raise RuntimeError(f"evidence manifest contract drifted: {directory}")

    expected_paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise RuntimeError("evidence manifest entry is invalid")
        relative_raw = entry.get("path")
        digest = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if (
            not isinstance(relative_raw, str)
            or not isinstance(digest, str)
            or _SHA256_PATTERN.fullmatch(digest) is None
            or not isinstance(size_bytes, int)
            or size_bytes < 0
        ):
            raise RuntimeError("evidence manifest entry fields are invalid")
        relative = PurePosixPath(relative_raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("evidence manifest path is unsafe")
        if relative_raw in expected_paths:
            raise RuntimeError("evidence manifest paths are not unique")
        expected_paths.add(relative_raw)
        path = root / directory / Path(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"evidence file is missing or unsafe: {relative_raw}")
        if _file_sha256(path) != digest or path.stat().st_size != size_bytes:
            raise RuntimeError(f"evidence file identity drifted: {relative_raw}")

    observed_paths = {
        path.name for path in (root / directory).iterdir() if path.name != "evidence_sha256.json"
    }
    if observed_paths != expected_paths:
        raise RuntimeError(f"evidence vault topology drifted: {directory}")
    return len(files)


def _validate_v5_evidence(root: Path) -> dict[str, object]:
    count = _validate_vault(
        root,
        V5_EVIDENCE_DIRECTORY,
        expected_manifest_sha256=EXPECTED_V5_EVIDENCE_MANIFEST_SHA256,
    )
    source = _load_json_object(root / V5_EVIDENCE_DIRECTORY / "source_evidence_identity.json")
    expected_source = {
        "source_artifact_sha256": EXPECTED_V5_EVIDENCE_ZIP_SHA256,
        "source_artifact_size_bytes": 13573,
        "execution_log_sha256": EXPECTED_V5_EXECUTION_LOG_SHA256,
        "execution_log_size_bytes": 2960,
        "kaggle_title": "auragateway-cu129-offline-verifier-v5",
        "notebook_sha256": ("ad4d7a533de09965f5562db58c85cb785f2a7f8550906631142e26a34b6e59ab"),
        "captured_version": 1,
        "complete_execution_log_provided": True,
        "evidence_file_count": 28,
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
        raise RuntimeError("verifier v5 source identity drifted: " + ", ".join(drift))

    input_validation = _load_json_object(root / V5_EVIDENCE_DIRECTORY / "00_input_validation.json")
    identity = _load_json_object(
        root / V5_EVIDENCE_DIRECTORY / "10_07_target_runtime_identity_before_install.json"
    )
    summary = _load_json_object(root / V5_EVIDENCE_DIRECTORY / "90_summary.json")
    stderr = str(identity.get("stderr_excerpt", ""))
    if (
        input_validation.get("status") != "PASSED"
        or input_validation.get("package_count") != 176
        or input_validation.get("manifest_entry_count") != 182
    ):
        raise RuntimeError("verifier v5 input validation evidence drifted")
    if (
        identity.get("command_role") != "target_runtime_identity_before_install"
        or identity.get("returncode") != 0
        or identity.get("status") != "FAILED"
        or identity.get("semantic_error") != "base sitecustomize leaked into target process"
        or "No module named 'wrapt'" not in stderr
    ):
        raise RuntimeError("verifier v5 startup failure evidence drifted")
    if (
        summary.get("status") != "FAILED"
        or summary.get("first_divergence") != "target_runtime_identity_before_install"
        or summary.get("failed_required_roles") != ["target_runtime_identity_before_install"]
        or summary.get("package_installation_started") is not False
        or summary.get("base_distribution_metadata_unchanged") is not True
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("verifier v5 summary evidence drifted")
    return {
        "files_verified": count,
        "first_divergence": summary["first_divergence"],
        "package_installation_started": False,
    }


def _parse_stdout(record: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(str(record.get("stdout_excerpt", "")).strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError("startup probe stdout is not JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("startup probe stdout is not one JSON object")
    return cast(dict[str, Any], payload)


def _validate_startup_evidence(root: Path) -> dict[str, object]:
    count = _validate_vault(
        root,
        STARTUP_EVIDENCE_DIRECTORY,
        expected_manifest_sha256=EXPECTED_STARTUP_EVIDENCE_MANIFEST_SHA256,
    )
    source = _load_json_object(root / STARTUP_EVIDENCE_DIRECTORY / "source_evidence_identity.json")
    expected_source = {
        "source_artifact_sha256": EXPECTED_STARTUP_EVIDENCE_ZIP_SHA256,
        "source_artifact_size_bytes": 8755,
        "execution_log_sha256": EXPECTED_STARTUP_EXECUTION_LOG_SHA256,
        "execution_log_size_bytes": 2302,
        "kaggle_title": "auragateway-cu129-python-startup-inspect-v1",
        "notebook_sha256": EXPECTED_STARTUP_NOTEBOOK_SHA256,
        "captured_version": 1,
        "complete_execution_log_provided": True,
        "evidence_file_count": 10,
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
        raise RuntimeError("startup source identity drifted: " + ", ".join(drift))

    default = _load_json_object(
        root / STARTUP_EVIDENCE_DIRECTORY / "10_05_sanitized_default_startup.json"
    )
    isolated = _load_json_object(
        root / STARTUP_EVIDENCE_DIRECTORY / "10_06_isolated_mode_startup.json"
    )
    no_site = _load_json_object(root / STARTUP_EVIDENCE_DIRECTORY / "10_07_no_site_startup.json")
    controlled = _load_json_object(
        root / STARTUP_EVIDENCE_DIRECTORY / "10_08_controlled_site_bootstrap.json"
    )
    summary = _load_json_object(root / STARTUP_EVIDENCE_DIRECTORY / "90_summary.json")

    for record in (default, isolated):
        stderr = str(record.get("stderr_excerpt", ""))
        if (
            record.get("status") != "PASSED"
            or record.get("returncode") != 0
            or "sitecustomize" not in stderr
            or "No module named 'wrapt'" not in stderr
        ):
            raise RuntimeError("startup warning reproduction evidence drifted")

    no_site_payload = _parse_stdout(no_site)
    if (
        no_site.get("status") != "PASSED"
        or no_site_payload.get("no_site_flag") != 1
        or no_site_payload.get("prefix_matches_expected") is not False
        or no_site_payload.get("target_site_packages_present") is not False
    ):
        raise RuntimeError("no-site startup evidence drifted")

    controlled_payload = _parse_stdout(controlled)
    expected_controlled = {
        "prefix_matches_expected": True,
        "base_prefix_differs": True,
        "pythonpath_present": False,
        "pythonhome_present": False,
        "python_no_user_site": "1",
        "user_site_enabled": False,
        "pip_present": False,
        "target_site_packages_present": True,
        "external_package_paths": [],
        "sitecustomize_loaded": True,
        "sitecustomize_origin": "<auragateway-suppressed-sitecustomize>",
        "usercustomize_loaded": True,
        "usercustomize_origin": "<auragateway-suppressed-usercustomize>",
        "no_site_flag": 1,
    }
    if (
        controlled.get("status") != "PASSED"
        or controlled.get("returncode") != 0
        or str(controlled.get("stderr_excerpt", "")) != ""
        or any(
            controlled_payload.get(key) != expected_value
            for key, expected_value in expected_controlled.items()
        )
    ):
        raise RuntimeError("controlled site bootstrap evidence drifted")

    if (
        summary.get("inspection_status") != "COMPLETED"
        or summary.get("disposition") != "CONTROLLED_SITE_BOOTSTRAP_CONFIRMED"
        or summary.get("controlled_site_bootstrap_confirmed") is not True
        or summary.get("next_gate") != "build_cu129_offline_runtime_compatibility_verifier_v6"
        or summary.get("package_installation_performed") is not False
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("startup inspection summary drifted")
    return {
        "files_verified": count,
        "disposition": summary["disposition"],
        "controlled_site_bootstrap_confirmed": True,
    }


def _validate_notebook(
    root: Path,
    path: Path,
    *,
    expected_sha256: str,
    expected_metadata: dict[str, object],
    required_fragments: tuple[str, ...],
) -> dict[str, object]:
    payload = _load_json_object(root / path)
    metadata = payload.get("metadata")
    if payload.get("nbformat") != 4 or not isinstance(metadata, dict):
        raise RuntimeError(f"notebook structure drifted: {path}")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise RuntimeError(f"notebook metadata is missing: {path}")
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_metadata.items()
            if auragateway.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError(f"notebook metadata drifted: {path}: " + ", ".join(drift))

    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError(f"notebook cells drifted: {path}")
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None or cell.get("outputs") != []:
            raise RuntimeError(f"notebook contains execution state: {path}")

    source = _notebook_source(payload)
    compile(source, path.as_posix(), "exec")
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        raise RuntimeError(
            f"notebook source lacks reviewed fragments: {path}: " + ", ".join(missing)
        )
    observed_sha256 = _file_sha256(root / path)
    if observed_sha256 != expected_sha256:
        raise RuntimeError(f"notebook raw identity drifted: {path}")
    return {
        "notebook_sha256": observed_sha256,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "execution_state_present": False,
    }


def _validate_startup_notebook(root: Path) -> dict[str, object]:
    return _validate_notebook(
        root,
        STARTUP_NOTEBOOK_PATH,
        expected_sha256=EXPECTED_STARTUP_NOTEBOOK_SHA256,
        expected_metadata={
            "schema_version": "1.0.0",
            "notebook_name": "auragateway-cu129-python-startup-inspect-v1",
            "diagnostic_only": True,
            "accelerator": "T4 x2",
            "internet_required": False,
            "inputs_required": 0,
            "package_installation_permitted": False,
            "model_requests_permitted": 0,
            "qualification_claimed": False,
        },
        required_fragments=(
            'NOTEBOOK_NAME = "auragateway-cu129-python-startup-inspect-v1"',
            '"sanitized_default_startup"',
            '"isolated_mode_startup"',
            '"no_site_startup"',
            '"controlled_site_bootstrap"',
            'sys.modules["sitecustomize"] = sentinel("sitecustomize")',
            'sys.modules["usercustomize"] = sentinel("usercustomize")',
            "site.main()",
            '"CONTROLLED_SITE_BOOTSTRAP_CONFIRMED"',
            '"package_installation_performed": False',
            '"model_requests_performed": 0',
        ),
    )


def _validate_v6_notebook(root: Path) -> dict[str, object]:
    result = _validate_notebook(
        root,
        V6_NOTEBOOK_PATH,
        expected_sha256=EXPECTED_V6_NOTEBOOK_SHA256,
        expected_metadata={
            "schema_version": "6.0.0",
            "notebook_name": V6_VERIFIER_NAME,
            "diagnostic_only": True,
            "internet_required": False,
            "accelerator": "T4 x2",
            "credentials_permitted": False,
            "customer_data_permitted": False,
            "model_requests_permitted": 0,
            "qualification_claimed": False,
            "input_directory_name": "auragateway_vllm_cu129_wheelhouse_v1",
            "python_startup_policy": "NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP",
            "supersedes_notebook": (
                "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v5.ipynb"
            ),
            "supersession_reason": "TARGET_PYTHON_STARTUP_CUSTOMIZATION_LEAK",
        },
        required_fragments=(
            'NOTEBOOK_NAME = "auragateway-cu129-offline-verifier-v6"',
            'OUTPUT_DIRECTORY_NAME = "auragateway_vllm_cu129_offline_compatibility_evidence_v6"',
            'VENV_ROOT = Path("/kaggle/working/auragateway_vllm_runtime_cu129_v6")',
            'CONTROLLED_SITE_BOOTSTRAP_SCRIPT = """',
            "def controlled_target_argv(",
            '"-S"',
            'sys.modules["sitecustomize"] = sentinel("sitecustomize")',
            'sys.modules["usercustomize"] = sentinel("usercustomize")',
            "site.main()",
            '"NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"',
            '"TARGET_NVIDIA_LIBRARIES_PREPENDED"',
            '"target_runtime_identity_before_install"',
            '"offline_hash_locked_install_via_base_pip"',
            '"canonical_nvjitlink_resolution"',
            '"torch_family_runtime"',
            '"vllm_native_extension"',
            '"model_requests_performed": 0',
            '"qualification_claimed": False',
        ),
    )
    source = _notebook_source(_load_json_object(root / V6_NOTEBOOK_PATH))
    direct_target_pattern = re.compile(
        r"\[\s*str\(python\),\s*\"-c\"",
        re.MULTILINE,
    )
    if direct_target_pattern.search(source) is not None:
        raise RuntimeError("verifier v6 retains a direct target-Python -c invocation")
    if source.count("controlled_target_argv(") < 11:
        raise RuntimeError("verifier v6 controlled target invocation coverage drifted")
    return result


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate the v5 failure, startup proof, and verifier v6 package."""

    root = repo_root.resolve()
    baseline = validate_v5_package(root)
    if baseline.get("status") != ("VLLM_CU129_TARGET_FIRST_LOADER_REMEDIATION_PACKAGE_VALID"):
        raise RuntimeError("verifier v5 baseline package is not valid")

    result = ControlledPythonStartupRemediationV1.model_validate(
        _load_json_object(root / RESULT_PATH)
    )
    if _file_sha256(root / RESULT_PATH) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("controlled-startup decision record identity drifted")
    if result.repository_base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError("controlled-startup repository base commit drifted")

    v5_evidence = _validate_v5_evidence(root)
    startup_evidence = _validate_startup_evidence(root)
    startup_notebook = _validate_startup_notebook(root)
    verifier = _validate_v6_notebook(root)

    if _file_sha256(root / CERTIFICATE_PATH) != EXPECTED_CERTIFICATE_SHA256:
        raise RuntimeError("startup reasoning certificate identity drifted")
    certificate = (root / CERTIFICATE_PATH).read_text(encoding="utf-8")
    required_certificate_fragments = (
        "REASONING_CHAIN_CONSISTENT",
        "SUFFICIENT_FOR_V6_REMEDIATION_DECISION",
        "SUFFICIENT_FOR_TARGET_PYTHON_STARTUP_CUSTOMIZATION_ASSIGNMENT",
        "NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP",
        "Verifier v6 must use the controlled bootstrap for every target-Python probe",
    )
    if any(fragment not in certificate for fragment in required_certificate_fragments):
        raise RuntimeError("startup reasoning certificate drifted")

    adr = (root / ADR_PATH).read_text(encoding="utf-8")
    required_adr_fragments = (
        "Status: Accepted",
        "TARGET_PYTHON_STARTUP_CUSTOMIZATION_LEAK",
        "NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP",
        "CONTROLLED_SENTINEL_BEFORE_SITE_MAIN",
        "REMOVE_NON_TARGET_SITE_AND_DIST_PACKAGES",
        "TARGET_NVIDIA_LIBRARIES_PREPENDED",
        EXPECTED_V6_NOTEBOOK_SHA256,
        EXPECTED_RESULT_SHA256,
    )
    if any(fragment not in adr for fragment in required_adr_fragments):
        raise RuntimeError("controlled-startup ADR drifted")

    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    required_runbook_fragments = (
        "APPROVED_FOR_OFFLINE_CU129_CONTROLLED_PYTHON_STARTUP_VERIFICATION_V6",
        "run_cu129_offline_runtime_compatibility_verifier_v6",
        V6_VERIFIER_NAME,
        V6_OUTPUT_DIRECTORY,
        EXPECTED_V6_NOTEBOOK_SHA256,
        EXPECTED_RESULT_SHA256,
        "python_startup_policy=NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP",
        "canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED",
        "Accelerator: T4 x2",
        "Internet: Off",
        "Inputs: exactly the successful Version 1 materializer output",
        "Run exactly once",
        "No model or tokenizer loading",
    )
    if any(fragment not in runbook for fragment in required_runbook_fragments):
        raise RuntimeError("controlled-startup runbook drifted")

    return {
        "status": "VLLM_CU129_CONTROLLED_PYTHON_STARTUP_REMEDIATION_PACKAGE_VALID",
        "decision": result.decision,
        "record_sha256": EXPECTED_RESULT_SHA256,
        "repository_base_commit": result.repository_base_commit,
        "v5_evidence_zip_sha256": EXPECTED_V5_EVIDENCE_ZIP_SHA256,
        "v5_evidence_manifest_sha256": EXPECTED_V5_EVIDENCE_MANIFEST_SHA256,
        "v5_evidence_files_verified": v5_evidence["files_verified"],
        "v5_first_divergence": v5_evidence["first_divergence"],
        "v5_package_installation_started": (v5_evidence["package_installation_started"]),
        "startup_evidence_zip_sha256": EXPECTED_STARTUP_EVIDENCE_ZIP_SHA256,
        "startup_evidence_manifest_sha256": (EXPECTED_STARTUP_EVIDENCE_MANIFEST_SHA256),
        "startup_evidence_files_verified": startup_evidence["files_verified"],
        "startup_disposition": startup_evidence["disposition"],
        "controlled_site_bootstrap_confirmed": (
            startup_evidence["controlled_site_bootstrap_confirmed"]
        ),
        "startup_notebook_sha256": startup_notebook["notebook_sha256"],
        "reasoning_certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
        "active_verifier_notebook_sha256": verifier["notebook_sha256"],
        "active_verifier_kaggle_title": V6_VERIFIER_NAME,
        "active_verifier_title_character_count": len(V6_VERIFIER_NAME),
        "python_startup_policy": result.selected_remediation.python_startup_policy,
        "canonical_loader_policy": result.selected_remediation.canonical_loader_policy,
        "wheelhouse_rematerialization_justified": (
            result.selected_remediation.wheelhouse_rematerialization_justified
        ),
        "package_version_substitution_justified": (
            result.selected_remediation.package_version_substitution_justified
        ),
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
