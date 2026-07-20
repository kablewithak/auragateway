"""Validate verifier v3 evidence and the governed base-pip target verifier v4."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, Self, cast

from pydantic import model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_vllm_cu129_offline_bootstrap_remediation import (
    validate_repository_package as validate_bootstrap_package,
)

RESULT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_cu129_base_pip_target_install_remediation_v1.json"
)
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_wheelhouse_materialization_v1.md")
ADR_PATH: Final = Path("docs/adr/2026-07-20-local-abc-vllm-cu129-base-pip-target-install.md")
CERTIFICATE_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Offline_Verifier_V3_Semi_Formal_Reasoning_Certificate.md"
)
V3_VERIFIER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v3.ipynb"
)
V4_VERIFIER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v4.ipynb"
)
EVIDENCE_DIRECTORY: Final = Path("evidence_vault/local_abc/vllm-cu129-offline-compatibility-v3")
EVIDENCE_MANIFEST_PATH: Final = EVIDENCE_DIRECTORY / "evidence_sha256.json"
SOURCE_IDENTITY_PATH: Final = EVIDENCE_DIRECTORY / "source_evidence_identity.json"

EXPECTED_BASE_COMMIT: Final = "ae90184a337cdea584bff59e3e74289544efa496"
EXPECTED_RESULT_SHA256: Final = "906e79e70de6e3fe9af5ba4d0ca3a2fd2e1904c27f172bfee6e825ec92e7ad5e"
EXPECTED_V3_NOTEBOOK_SHA256: Final = (
    "d9cd2218fb7fc995ecd205127d979154c9700d26e7432abfefc6a0a7af1af36f"
)
EXPECTED_V4_NOTEBOOK_SHA256: Final = (
    "b6a6e1ed7f33f98959fe346be173b1799a36aecb9e0245c9d2f3beaba1bd0568"
)
EXPECTED_EVIDENCE_ZIP_SHA256: Final = (
    "721fb2dc1fcbb57f2cda2e5772d5bac9fdf6f2f10798595fc4dd6f3cdf55d671"
)
EXPECTED_EVIDENCE_MANIFEST_SHA256: Final = (
    "399549e894f3d5afecffac1244d2bf32f32fb34c0f5ef815fba443b75f8613e8"
)
EXPECTED_CERTIFICATE_SHA256: Final = (
    "25449c1f1ce7e70c88ed4cdbbeb0a3875a05a15b4386846a22c1b70a9d6027d7"
)
V4_VERIFIER_NAME: Final = "auragateway-cu129-offline-verifier-v4"
V4_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_offline_compatibility_evidence_v4"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class VerifierV3FailureV1(LocalABCContract):
    """Typed interpretation of verifier v3 Version 1."""

    kaggle_title: Literal["auragateway-cu129-offline-verifier-v3"]
    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v3.ipynb"
    ]
    notebook_sha256: Literal["d9cd2218fb7fc995ecd205127d979154c9700d26e7432abfefc6a0a7af1af36f"]
    captured_version: Literal[1]
    evidence_zip_sha256: Literal["721fb2dc1fcbb57f2cda2e5772d5bac9fdf6f2f10798595fc4dd6f3cdf55d671"]
    evidence_vault_path: Literal["evidence_vault/local_abc/vllm-cu129-offline-compatibility-v3"]
    evidence_manifest_sha256: Literal[
        "399549e894f3d5afecffac1244d2bf32f32fb34c0f5ef815fba443b75f8613e8"
    ]
    status: Literal["FAILED"]
    input_validation_status: Literal["PASSED"]
    base_python_runtime: Literal["3.12.13"]
    base_venv_import_status: Literal["PASSED"]
    base_ensurepip_import_status: Literal["FAILED"]
    first_divergence: Literal["base_ensurepip_import"]
    failure_class: Literal["BASE_INTERPRETER_BOOTSTRAP_CAPABILITY_FAILURE"]
    failure_code: Literal["ENSUREPIP_MODULE_ABSENT"]
    observed_failed_roles: tuple[Literal["base_ensurepip_import"], ...]
    blocked_required_roles: tuple[str, ...]
    package_installation_started: Literal[False]
    wheelhouse_rematerialization_justified: Literal[False]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_roles(self) -> Self:
        if self.observed_failed_roles != ("base_ensurepip_import",):
            raise ValueError("v3 observed failure set drifted")
        expected = (
            "base_ensurepip_cli",
            "gpu_topology",
            "offline_hash_locked_install",
            "pip_check",
            "python_runtime",
            "torch_family_runtime",
            "transformers_runtime",
            "venv_create_without_pip",
            "venv_ensurepip_bootstrap",
            "venv_pip_version",
            "venv_python_runtime",
            "vllm_distribution",
            "vllm_module",
            "vllm_native_extension",
        )
        if self.blocked_required_roles != expected:
            raise ValueError("v3 blocked role set drifted")
        return self


class ReasoningCertificateV1(LocalABCContract):
    """Bound verifier v3 reasoning certificate."""

    path: Literal[
        "docs/reports/AuraGateway_CU129_Offline_Verifier_V3_Semi_Formal_Reasoning_Certificate.md"
    ]
    sha256: Literal["25449c1f1ce7e70c88ed4cdbbeb0a3875a05a15b4386846a22c1b70a9d6027d7"]
    result: Literal["REASONING_CHAIN_CONSISTENT"]
    evidence_sufficiency: Literal["SUFFICIENT_FOR_V4_REMEDIATION_DECISION"]
    root_cause_sufficiency: Literal["SUFFICIENT_FOR_ENSUREPIP_ABSENCE_ASSIGNMENT"]


class SelectedRemediationV1(LocalABCContract):
    """Supported base-pip target-install contract."""

    official_interface: Literal["PIP_GLOBAL_PYTHON_OPTION"]
    minimum_base_pip_version: Literal["22.3"]
    target_environment_creation: Literal["VENV_WITHOUT_PIP"]
    target_environment_contains_pip_before_install: Literal[False]
    base_pip_role: Literal["INSTALLATION_EXECUTOR_ONLY"]
    base_environment_target: Literal[False]
    wheelhouse_rematerialization_justified: Literal[False]
    install_command_contract: tuple[str, ...]

    @model_validator(mode="after")
    def validate_command(self) -> Self:
        expected = (
            "python",
            "-m",
            "pip",
            "--isolated",
            "--disable-pip-version-check",
            "--python",
            "<target-venv>",
            "install",
            "--no-index",
            "--no-cache-dir",
            "--find-links",
            "<wheelhouse>",
            "--require-hashes",
            "-r",
            "<requirements-lock>",
        )
        if self.install_command_contract != expected:
            raise ValueError("base-pip target install command drifted")
        return self


class ActiveVerifierV4(LocalABCContract):
    """Governed verifier v4 execution contract."""

    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v4.ipynb"
    ]
    notebook_sha256: Literal["b6a6e1ed7f33f98959fe346be173b1799a36aecb9e0245c9d2f3beaba1bd0568"]
    kaggle_title: Literal["auragateway-cu129-offline-verifier-v4"]
    title_character_count: Literal[37]
    output_directory: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v4"]
    output_zip: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v4.zip"]
    accelerator: Literal["T4 x2"]
    internet_enabled: Literal[False]
    secrets_attached: Literal[False]
    input_policy: Literal["EXACTLY_ONE_SUCCESSFUL_MATERIALIZER_OUTPUT"]
    expected_input_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    installation_executor: Literal["BASE_PIP_PYTHON_TARGET"]
    minimum_base_pip_version: Literal["22.3"]
    environment_creation_mode: Literal["VENV_WITHOUT_PIP"]
    target_isolation_required: Literal[True]
    base_distribution_snapshot_required: Literal[True]
    host_independent_roles: tuple[str, ...]
    downstream_failure_taxonomy: tuple[str, ...]
    model_requests_permitted: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_harness_contract(self) -> Self:
        if self.host_independent_roles != (
            "base_python_runtime",
            "base_venv_import",
            "base_pip_import",
            "base_distribution_snapshot_before",
            "gpu_topology",
        ):
            raise ValueError("verifier v4 independent role set drifted")
        if self.downstream_failure_taxonomy != (
            "FAILED",
            "BLOCKED_BY_UPSTREAM_FAILURE",
            "NOT_EXECUTED",
        ):
            raise ValueError("verifier v4 failure taxonomy drifted")
        return self


class RemediationSafetyV1(LocalABCContract):
    """Safety state for verifier v4."""

    qualification_authorization_issued: Literal[False]
    model_loaded: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]


class BasePipTargetInstallRemediationV1(LocalABCContract):
    """Decision record that consumes verifier v3 and opens verifier v4."""

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-vllm-cu129-base-pip-target-install-remediation-v1"]
    repository_base_commit: Literal["ae90184a337cdea584bff59e3e74289544efa496"]
    decision: Literal["APPROVED_FOR_OFFLINE_CU129_BASE_PIP_TARGET_INSTALL_VERIFICATION_V4"]
    v3_execution: VerifierV3FailureV1
    reasoning_certificate: ReasoningCertificateV1
    selected_remediation: SelectedRemediationV1
    active_verifier: ActiveVerifierV4
    safety: RemediationSafetyV1
    next_gate: Literal["run_cu129_offline_runtime_compatibility_verifier_v4"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_non_claims(self) -> Self:
        expected = (
            "base_pip_availability_not_yet_verified_in_next_session",
            "offline_install_not_yet_verified",
            "target_dependency_check_not_yet_verified",
            "base_filesystem_immutability_not_proven",
            "torch_cuda_runtime_not_yet_verified",
            "two_t4_topology_not_yet_verified",
            "vllm_module_import_not_yet_verified",
            "vllm_native_extension_not_yet_verified",
            "model_not_loaded",
            "qualification_not_authorized",
            "measured_abc_not_authorized",
            "production_readiness_not_claimed",
        )
        if self.non_claims != expected:
            raise ValueError("base-pip remediation non-claims drifted")
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
        raise RuntimeError("verifier notebook cells are missing")
    code_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]
    if len(code_cells) != 1:
        raise RuntimeError("verifier notebook must contain exactly one code cell")
    source = code_cells[0].get("source")
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    if isinstance(source, str):
        return source
    raise RuntimeError("verifier notebook source is invalid")


def classify_role_states(
    records: list[dict[str, object]],
    required_roles: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    observed = {str(record["command_role"]): record for record in records}
    return {
        "failed": tuple(
            role
            for role in required_roles
            if role in observed and observed[role].get("status") == "FAILED"
        ),
        "blocked": tuple(
            role
            for role in required_roles
            if role in observed and observed[role].get("status") == "BLOCKED_BY_UPSTREAM_FAILURE"
        ),
        "not_executed": tuple(
            role
            for role in required_roles
            if role not in observed or observed[role].get("status") == "NOT_EXECUTED"
        ),
    }


def pip_version_supported(value: str) -> bool:
    match = re.match(r"^(\d+)\.(\d+)", value)
    if match is None:
        return False
    return (int(match.group(1)), int(match.group(2))) >= (22, 3)


def _validate_v3_evidence(root: Path) -> dict[str, object]:
    manifest = _load_json_object(root / EVIDENCE_MANIFEST_PATH)
    files = manifest.get("files")
    if manifest.get("schema_version") != "1.0.0" or not isinstance(files, list):
        raise RuntimeError("v3 evidence manifest is invalid")
    if len(files) != 21:
        raise RuntimeError("v3 evidence manifest must contain 21 source files")

    observed_paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise RuntimeError("v3 evidence entry is invalid")
        relative_raw = entry.get("path")
        digest = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if (
            not isinstance(relative_raw, str)
            or not isinstance(digest, str)
            or not isinstance(size_bytes, int)
        ):
            raise RuntimeError("v3 evidence fields are invalid")
        relative = PurePosixPath(relative_raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("v3 evidence path is unsafe")
        if relative_raw in observed_paths:
            raise RuntimeError("v3 evidence paths are not unique")
        observed_paths.add(relative_raw)
        path = root / EVIDENCE_DIRECTORY / Path(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("v3 evidence file is missing or unsafe")
        if _file_sha256(path) != digest or path.stat().st_size != size_bytes:
            raise RuntimeError("v3 evidence identity drifted")

    if _file_sha256(root / EVIDENCE_MANIFEST_PATH) != EXPECTED_EVIDENCE_MANIFEST_SHA256:
        raise RuntimeError("v3 evidence manifest raw identity drifted")

    source = _load_json_object(root / SOURCE_IDENTITY_PATH)
    expected_source = {
        "source_artifact_sha256": EXPECTED_EVIDENCE_ZIP_SHA256,
        "source_artifact_size_bytes": 8386,
        "kaggle_title": "auragateway-cu129-offline-verifier-v3",
        "notebook_sha256": EXPECTED_V3_NOTEBOOK_SHA256,
        "captured_version": 1,
        "complete_execution_log_provided": False,
        "evidence_file_count": 20,
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
        raise RuntimeError("v3 source identity drifted: " + ", ".join(drift))

    input_validation = _load_json_object(root / EVIDENCE_DIRECTORY / "00_input_validation.json")
    ensurepip = _load_json_object(root / EVIDENCE_DIRECTORY / "10_03_base_ensurepip_import.json")
    summary = _load_json_object(root / EVIDENCE_DIRECTORY / "90_summary.json")
    stderr = ensurepip.get("stderr_excerpt")
    if (
        input_validation.get("status") != "PASSED"
        or input_validation.get("package_count") != 176
        or input_validation.get("manifest_entry_count") != 182
        or input_validation.get("total_wheel_bytes") != 5727339111
    ):
        raise RuntimeError("v3 input validation evidence drifted")
    if (
        ensurepip.get("command_role") != "base_ensurepip_import"
        or ensurepip.get("status") != "FAILED"
        or ensurepip.get("returncode") != 1
        or not isinstance(stderr, str)
        or "No module named 'ensurepip'" not in stderr
    ):
        raise RuntimeError("v3 ensurepip absence evidence drifted")
    if (
        summary.get("status") != "FAILED"
        or summary.get("first_divergence") != "base_ensurepip_import"
        or summary.get("failed_required_roles") != ["base_ensurepip_import"]
        or summary.get("package_installation_started") is not False
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("v3 summary evidence drifted")

    return {
        "evidence_files_verified": len(files) + 1,
        "input_validation_status": input_validation["status"],
        "first_divergence": summary["first_divergence"],
        "failure_code": "ENSUREPIP_MODULE_ABSENT",
        "package_installation_started": False,
    }


def _validate_v4_notebook(root: Path) -> dict[str, object]:
    path = root / V4_VERIFIER_PATH
    payload = _load_json_object(path)
    metadata = payload.get("metadata")
    if payload.get("nbformat") != 4 or not isinstance(metadata, dict):
        raise RuntimeError("verifier v4 notebook structure drifted")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise RuntimeError("verifier v4 metadata is missing")
    expected_metadata = {
        "schema_version": "4.0.0",
        "notebook_name": V4_VERIFIER_NAME,
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
        "supersedes_notebook": V3_VERIFIER_PATH.as_posix(),
        "supersession_reason": "BASE_INTERPRETER_ENSUREPIP_MODULE_ABSENT",
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_metadata.items()
            if auragateway.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("verifier v4 metadata drifted: " + ", ".join(drift))

    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("verifier v4 cells are invalid")
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None or cell.get("outputs") != []:
            raise RuntimeError("verifier v4 contains execution state")

    source = _notebook_source(payload)
    compile(source, path.as_posix(), "exec")
    required_fragments = (
        'NOTEBOOK_NAME = "auragateway-cu129-offline-verifier-v4"',
        '"base_pip_import"',
        '"base_distribution_snapshot_before"',
        '"gpu_topology"',
        '"--without-pip"',
        '"target_runtime_identity_before_install"',
        '"base_pip_python_target_support"',
        '"--python"',
        '"offline_hash_locked_install_via_base_pip"',
        '"--no-index"',
        '"--no-cache-dir"',
        '"--require-hashes"',
        '"target_distribution_inventory"',
        '"target_dependency_check_via_base_pip"',
        '"base_distribution_snapshot_after"',
        '"base_distribution_metadata_unchanged"',
        '"target_environment_isolated"',
        '"model_requests_performed=0"',
        '"qualification_claimed=false"',
        '"upload_only_this_file=true"',
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        raise RuntimeError("verifier v4 source lacks reviewed fragments: " + ", ".join(missing))
    prohibited = (
        '"base_ensurepip_import"',
        '"venv_ensurepip_bootstrap"',
        '"ensurepip", "--upgrade"',
    )
    if any(fragment in source for fragment in prohibited):
        raise RuntimeError("verifier v4 retains an ensurepip execution dependency")
    command_fragment = (
        '"--isolated",\n                "--disable-pip-version-check",\n'
        '                "--python",\n                str(VENV_ROOT),\n'
        '                "install",'
    )
    if command_fragment not in source:
        raise RuntimeError("verifier v4 pip --python ordering drifted")
    observed_sha256 = _file_sha256(path)
    if observed_sha256 != EXPECTED_V4_NOTEBOOK_SHA256:
        raise RuntimeError("verifier v4 raw identity drifted")
    return {
        "notebook_sha256": observed_sha256,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "execution_state_present": False,
    }


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate verifier v3 evidence and the verifier v4 remediation package."""

    root = repo_root.resolve()
    baseline = validate_bootstrap_package(root)
    if baseline.get("status") != "VLLM_CU129_OFFLINE_BOOTSTRAP_REMEDIATION_PACKAGE_VALID":
        raise RuntimeError("verifier v3 bootstrap baseline is not valid")

    result = BasePipTargetInstallRemediationV1.model_validate(_load_json_object(root / RESULT_PATH))
    if _file_sha256(root / RESULT_PATH) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("base-pip remediation result raw identity drifted")
    if result.repository_base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError("base-pip remediation base commit drifted")

    if _file_sha256(root / V3_VERIFIER_PATH) != EXPECTED_V3_NOTEBOOK_SHA256:
        raise RuntimeError("verifier v3 historical identity drifted")
    evidence = _validate_v3_evidence(root)
    verifier = _validate_v4_notebook(root)

    if _file_sha256(root / CERTIFICATE_PATH) != EXPECTED_CERTIFICATE_SHA256:
        raise RuntimeError("verifier v3 reasoning certificate identity drifted")
    certificate = (root / CERTIFICATE_PATH).read_text(encoding="utf-8")
    required_certificate_fragments = (
        "REASONING_CHAIN_CONSISTENT",
        "SUFFICIENT_FOR_V4_REMEDIATION_DECISION",
        "SUFFICIENT_FOR_ENSUREPIP_ABSENCE_ASSIGNMENT",
        "No wheelhouse rematerialization is justified",
    )
    if any(fragment not in certificate for fragment in required_certificate_fragments):
        raise RuntimeError("verifier v3 reasoning certificate drifted")

    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    required_runbook_fragments = (
        "APPROVED_FOR_OFFLINE_CU129_BASE_PIP_TARGET_INSTALL_VERIFICATION_V4",
        "run_cu129_offline_runtime_compatibility_verifier_v4",
        "ENSUREPIP_MODULE_ABSENT",
        V4_VERIFIER_NAME,
        V4_OUTPUT_DIRECTORY,
        EXPECTED_V4_NOTEBOOK_SHA256,
        EXPECTED_EVIDENCE_ZIP_SHA256,
        "minimum_base_pip_version=22.3",
        "installation_executor=BASE_PIP_PYTHON_TARGET",
        "Accelerator: T4 x2",
        "Internet: Off",
        "Inputs: exactly the successful Version 1 materializer output",
        "Do not rerun verifier v3",
        "package_count=176",
        "zero downloads",
    )
    if any(fragment not in runbook for fragment in required_runbook_fragments):
        raise RuntimeError("CUDA 12.9 base-pip runbook drifted")

    adr = (root / ADR_PATH).read_text(encoding="utf-8")
    required_adr_fragments = (
        "Status: Accepted",
        "ENSUREPIP_MODULE_ABSENT",
        EXPECTED_EVIDENCE_ZIP_SHA256,
        EXPECTED_EVIDENCE_MANIFEST_SHA256,
        EXPECTED_CERTIFICATE_SHA256,
        EXPECTED_V4_NOTEBOOK_SHA256,
        V4_VERIFIER_NAME,
        "--python",
        "--without-pip",
    )
    if any(fragment not in adr for fragment in required_adr_fragments):
        raise RuntimeError("CUDA 12.9 base-pip ADR drifted")

    return {
        "status": "VLLM_CU129_BASE_PIP_TARGET_INSTALL_REMEDIATION_PACKAGE_VALID",
        "decision": result.decision,
        "record_sha256": EXPECTED_RESULT_SHA256,
        "repository_base_commit": result.repository_base_commit,
        "v3_evidence_zip_sha256": EXPECTED_EVIDENCE_ZIP_SHA256,
        "v3_evidence_manifest_sha256": EXPECTED_EVIDENCE_MANIFEST_SHA256,
        "v3_evidence_files_verified": evidence["evidence_files_verified"],
        "v3_input_validation_status": evidence["input_validation_status"],
        "v3_first_divergence": evidence["first_divergence"],
        "v3_failure_code": evidence["failure_code"],
        "v3_package_installation_started": evidence["package_installation_started"],
        "reasoning_certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
        "active_verifier_notebook_sha256": verifier["notebook_sha256"],
        "active_verifier_kaggle_title": V4_VERIFIER_NAME,
        "active_verifier_title_character_count": len(V4_VERIFIER_NAME),
        "installation_executor": result.active_verifier.installation_executor,
        "minimum_base_pip_version": result.active_verifier.minimum_base_pip_version,
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
