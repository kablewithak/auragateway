"""Validate verifier v2 failure evidence and the governed verifier v3 remediation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, Self, cast

from pydantic import model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_vllm_cu129_wheelhouse_materialization import (
    validate_repository_package as validate_materialization_package,
)

RESULT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_cu129_offline_bootstrap_remediation_v1.json"
)
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_wheelhouse_materialization_v1.md")
ADR_PATH: Final = Path("docs/adr/2026-07-20-local-abc-vllm-cu129-offline-bootstrap-remediation.md")
CERTIFICATE_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Offline_Verifier_V2_Semi_Formal_Reasoning_Certificate.md"
)
V2_VERIFIER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v2.ipynb"
)
V3_VERIFIER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v3.ipynb"
)
EVIDENCE_DIRECTORY: Final = Path("evidence_vault/local_abc/vllm-cu129-offline-compatibility-v2")
EVIDENCE_MANIFEST_PATH: Final = EVIDENCE_DIRECTORY / "evidence_sha256.json"
SOURCE_IDENTITY_PATH: Final = EVIDENCE_DIRECTORY / "source_evidence_identity.json"

EXPECTED_BASE_COMMIT: Final = "2d7dd8e8298109c09ba675a929ddd462e7d9a696"
EXPECTED_RESULT_SHA256: Final = "988b95cf8f7ea4128fcc48a831b34746f4c884208b9d38494d071b2393a315bf"
EXPECTED_V2_NOTEBOOK_SHA256: Final = (
    "86db695b463a97d021c7d45a3cd31284d404d618c968ffd18837631f7221d5f2"
)
EXPECTED_V3_NOTEBOOK_SHA256: Final = (
    "d9cd2218fb7fc995ecd205127d979154c9700d26e7432abfefc6a0a7af1af36f"
)
EXPECTED_EVIDENCE_ZIP_SHA256: Final = (
    "01019ce577f2bc7bfaaa8810d19161157f1dbc15b3c8817c2ba7836c4b0158d4"
)
EXPECTED_EVIDENCE_MANIFEST_SHA256: Final = (
    "bcda0b716981a31fa205682485598f7b4d0460133f8430fce3c656663421ff42"
)
EXPECTED_CERTIFICATE_SHA256: Final = (
    "b1ffc2009ee100ffb990b88f09e08827e0301cecc233b6259ba0c5177a64b492"
)
V3_VERIFIER_NAME: Final = "auragateway-cu129-offline-verifier-v3"
V3_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_offline_compatibility_evidence_v3"


class VerifierV2FailureV1(LocalABCContract):
    """Typed interpretation of verifier v2 Version 1."""

    kaggle_title: Literal["auragateway-cu129-offline-verifier-v2"]
    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v2.ipynb"
    ]
    notebook_sha256: Literal["86db695b463a97d021c7d45a3cd31284d404d618c968ffd18837631f7221d5f2"]
    captured_version: Literal[1]
    evidence_zip_sha256: Literal["01019ce577f2bc7bfaaa8810d19161157f1dbc15b3c8817c2ba7836c4b0158d4"]
    evidence_vault_path: Literal["evidence_vault/local_abc/vllm-cu129-offline-compatibility-v2"]
    evidence_manifest_sha256: Literal[
        "bcda0b716981a31fa205682485598f7b4d0460133f8430fce3c656663421ff42"
    ]
    status: Literal["FAILED"]
    input_validation_status: Literal["PASSED"]
    first_divergence: Literal["offline_isolated_install"]
    failure_class: Literal["ISOLATED_ENVIRONMENT_BOOTSTRAP_FAILURE"]
    failure_code: Literal["ENSUREPIP_BOOTSTRAP_FAILED"]
    observed_failed_roles: tuple[Literal["offline_isolated_install"], ...]
    downstream_not_executed_roles: tuple[str, ...]
    package_installation_started: Literal[False]
    nested_ensurepip_output_captured: Literal[False]
    wheelhouse_rematerialization_justified: Literal[False]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_role_interpretation(self) -> Self:
        expected = (
            "pip_check",
            "gpu_topology",
            "python_runtime",
            "torch_family_runtime",
            "transformers_runtime",
            "vllm_distribution",
            "vllm_module",
            "vllm_native_extension",
        )
        if self.observed_failed_roles != ("offline_isolated_install",):
            raise ValueError("v2 observed failure set drifted")
        if self.downstream_not_executed_roles != expected:
            raise ValueError("v2 downstream blocked set drifted")
        return self


class ReasoningCertificateV1(LocalABCContract):
    """Bound semi-formal reasoning artifact."""

    path: Literal[
        "docs/reports/AuraGateway_CU129_Offline_Verifier_V2_Semi_Formal_Reasoning_Certificate.md"
    ]
    sha256: Literal["b1ffc2009ee100ffb990b88f09e08827e0301cecc233b6259ba0c5177a64b492"]
    result: Literal["REASONING_CHAIN_CONSISTENT"]
    evidence_sufficiency: Literal["SUFFICIENT_FOR_V3_REMEDIATION_DECISION"]
    root_cause_sufficiency: Literal["INSUFFICIENT_FOR_ENSUREPIP_CAUSE_ASSIGNMENT"]


class ActiveVerifierV3(LocalABCContract):
    """Governed verifier v3 execution contract."""

    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v3.ipynb"
    ]
    notebook_sha256: Literal["d9cd2218fb7fc995ecd205127d979154c9700d26e7432abfefc6a0a7af1af36f"]
    kaggle_title: Literal["auragateway-cu129-offline-verifier-v3"]
    title_character_count: Literal[37]
    output_directory: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v3"]
    output_zip: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v3.zip"]
    accelerator: Literal["T4 x2"]
    internet_enabled: Literal[False]
    secrets_attached: Literal[False]
    input_policy: Literal["EXACTLY_ONE_SUCCESSFUL_MATERIALIZER_OUTPUT"]
    expected_input_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    environment_creation_mode: Literal["VENV_WITHOUT_PIP_THEN_CAPTURED_ENSUREPIP"]
    downstream_failure_taxonomy: tuple[str, ...]
    model_requests_permitted: Literal[0]
    qualification_claimed: Literal[False]

    @model_validator(mode="after")
    def validate_failure_taxonomy(self) -> Self:
        if self.downstream_failure_taxonomy != (
            "FAILED",
            "BLOCKED_BY_UPSTREAM_FAILURE",
            "NOT_EXECUTED",
        ):
            raise ValueError("verifier v3 failure taxonomy drifted")
        return self


class RemediationSafetyV1(LocalABCContract):
    """Safety state for the verifier v3 diagnostic run."""

    qualification_authorization_issued: Literal[False]
    model_loaded: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]


class OfflineBootstrapRemediationV1(LocalABCContract):
    """Decision record that consumes v2 and opens verifier v3."""

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-vllm-cu129-offline-bootstrap-remediation-v1"]
    repository_base_commit: Literal["2d7dd8e8298109c09ba675a929ddd462e7d9a696"]
    decision: Literal["APPROVED_FOR_OFFLINE_CU129_BOOTSTRAP_DIAGNOSTIC_VERIFICATION_V3"]
    v2_execution: VerifierV2FailureV1
    reasoning_certificate: ReasoningCertificateV1
    active_verifier: ActiveVerifierV3
    safety: RemediationSafetyV1
    next_gate: Literal["run_cu129_offline_runtime_compatibility_verifier_v3"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_non_claims(self) -> Self:
        expected = (
            "ensurepip_root_cause_not_yet_assigned",
            "offline_install_not_yet_verified",
            "pip_check_not_yet_verified",
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
            raise ValueError("bootstrap remediation non-claims drifted")
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


def _validate_v2_evidence(root: Path) -> dict[str, object]:
    manifest = _load_json_object(root / EVIDENCE_MANIFEST_PATH)
    files = manifest.get("files")
    if manifest.get("schema_version") != "1.0.0" or not isinstance(files, list):
        raise RuntimeError("v2 evidence manifest is invalid")
    if len(files) != 5:
        raise RuntimeError("v2 evidence manifest must contain five source files")

    observed_paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise RuntimeError("v2 evidence entry is invalid")
        relative_raw = entry.get("path")
        digest = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if (
            not isinstance(relative_raw, str)
            or not isinstance(digest, str)
            or not isinstance(size_bytes, int)
        ):
            raise RuntimeError("v2 evidence entry fields are invalid")
        relative = PurePosixPath(relative_raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("v2 evidence path is unsafe")
        if relative_raw in observed_paths:
            raise RuntimeError("v2 evidence paths are not unique")
        observed_paths.add(relative_raw)
        path = root / EVIDENCE_DIRECTORY / Path(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("v2 evidence file is missing or unsafe")
        if _file_sha256(path) != digest or path.stat().st_size != size_bytes:
            raise RuntimeError("v2 evidence identity drifted")

    if _file_sha256(root / EVIDENCE_MANIFEST_PATH) != EXPECTED_EVIDENCE_MANIFEST_SHA256:
        raise RuntimeError("v2 evidence manifest raw identity drifted")

    source_identity = _load_json_object(root / SOURCE_IDENTITY_PATH)
    expected_source = {
        "source_artifact_sha256": EXPECTED_EVIDENCE_ZIP_SHA256,
        "kaggle_title": "auragateway-cu129-offline-verifier-v2",
        "notebook_sha256": EXPECTED_V2_NOTEBOOK_SHA256,
        "captured_version": 1,
        "complete_execution_log_provided": False,
        "evidence_file_count": 4,
        "model_requests_performed": 0,
        "qualification_claimed": False,
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_source.items()
            if source_identity.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("v2 source identity drifted: " + ", ".join(drift))

    input_validation = _load_json_object(root / EVIDENCE_DIRECTORY / "00_input_validation.json")
    if (
        input_validation.get("status") != "PASSED"
        or input_validation.get("package_count") != 176
        or input_validation.get("manifest_entry_count") != 182
        or input_validation.get("total_wheel_bytes") != 5727339111
    ):
        raise RuntimeError("v2 input validation evidence drifted")

    install = _load_json_object(root / EVIDENCE_DIRECTORY / "10_offline_isolated_install.json")
    stderr = install.get("stderr_excerpt")
    if (
        install.get("command_role") != "offline_isolated_install"
        or install.get("status") != "FAILED"
        or install.get("returncode") != 1
        or install.get("timed_out") is not False
        or not isinstance(stderr, str)
        or "-m', 'ensurepip', '--upgrade', '--default-pip'" not in stderr
        or "returned non-zero exit status 1" not in stderr
    ):
        raise RuntimeError("v2 ensurepip failure evidence drifted")

    summary = _load_json_object(root / EVIDENCE_DIRECTORY / "90_summary.json")
    expected_roles = {
        "offline_isolated_install",
        "pip_check",
        "gpu_topology",
        "python_runtime",
        "torch_family_runtime",
        "transformers_runtime",
        "vllm_distribution",
        "vllm_module",
        "vllm_native_extension",
    }
    failed_roles = summary.get("failed_required_roles")
    if (
        summary.get("status") != "FAILED"
        or not isinstance(failed_roles, list)
        or set(failed_roles) != expected_roles
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("v2 summary evidence drifted")

    return {
        "evidence_files_verified": len(files) + 1,
        "input_validation_status": input_validation["status"],
        "observed_failed_role": install["command_role"],
        "nested_ensurepip_output_captured": False,
        "package_installation_started": False,
    }


def _validate_v3_notebook(root: Path) -> dict[str, object]:
    path = root / V3_VERIFIER_PATH
    payload = _load_json_object(path)
    metadata = payload.get("metadata")
    if payload.get("nbformat") != 4 or not isinstance(metadata, dict):
        raise RuntimeError("verifier v3 notebook structure drifted")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise RuntimeError("verifier v3 metadata is missing")
    expected_metadata = {
        "schema_version": "3.0.0",
        "notebook_name": V3_VERIFIER_NAME,
        "diagnostic_only": True,
        "internet_required": False,
        "accelerator": "T4 x2",
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "model_requests_permitted": 0,
        "qualification_claimed": False,
        "input_directory_name": "auragateway_vllm_cu129_wheelhouse_v1",
        "supersedes_notebook": V2_VERIFIER_PATH.as_posix(),
        "supersession_reason": "ENSUREPIP_FAILURE_OUTPUT_NOT_CAPTURED",
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_metadata.items()
            if auragateway.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("verifier v3 metadata drifted: " + ", ".join(drift))

    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("verifier v3 cells are invalid")
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None or cell.get("outputs") != []:
            raise RuntimeError("verifier v3 contains execution state")

    source = _notebook_source(payload)
    compile(source, path.as_posix(), "exec")
    required_fragments = (
        'NOTEBOOK_NAME = "auragateway-cu129-offline-verifier-v3"',
        '"base_ensurepip_import"',
        '"base_ensurepip_cli"',
        '"venv_create_without_pip"',
        '"--without-pip"',
        '"venv_ensurepip_bootstrap"',
        '"ensurepip", "--upgrade", "--default-pip"',
        '"BLOCKED_BY_UPSTREAM_FAILURE"',
        '"NOT_EXECUTED"',
        '"offline_hash_locked_install"',
        '"--require-hashes"',
        '"model_requests_performed=0"',
        '"qualification_claimed=false"',
        '"upload_only_this_file=true"',
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        raise RuntimeError("verifier v3 source lacks reviewed fragments: " + ", ".join(missing))
    observed_sha256 = _file_sha256(path)
    if observed_sha256 != EXPECTED_V3_NOTEBOOK_SHA256:
        raise RuntimeError("verifier v3 raw identity drifted")
    return {
        "notebook_sha256": observed_sha256,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "execution_state_present": False,
    }


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate v2 failure evidence and the verifier v3 remediation package."""

    root = repo_root.resolve()
    baseline = validate_materialization_package(root)
    if baseline.get("status") != "VLLM_CU129_WHEELHOUSE_MATERIALIZATION_PACKAGE_VALID":
        raise RuntimeError("materialization baseline is not valid")

    result = OfflineBootstrapRemediationV1.model_validate(_load_json_object(root / RESULT_PATH))
    if _file_sha256(root / RESULT_PATH) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("bootstrap remediation result raw identity drifted")
    if result.repository_base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError("bootstrap remediation base commit drifted")

    if _file_sha256(root / V2_VERIFIER_PATH) != EXPECTED_V2_NOTEBOOK_SHA256:
        raise RuntimeError("verifier v2 historical identity drifted")
    evidence = _validate_v2_evidence(root)
    verifier = _validate_v3_notebook(root)

    if _file_sha256(root / CERTIFICATE_PATH) != EXPECTED_CERTIFICATE_SHA256:
        raise RuntimeError("semi-formal reasoning certificate identity drifted")
    certificate = (root / CERTIFICATE_PATH).read_text(encoding="utf-8")
    required_certificate_fragments = (
        "REASONING_CHAIN_CONSISTENT",
        "SUFFICIENT_FOR_V3_REMEDIATION_DECISION",
        "INSUFFICIENT_FOR_ENSUREPIP_CAUSE_ASSIGNMENT",
        "No wheelhouse rematerialization is justified",
    )
    if any(fragment not in certificate for fragment in required_certificate_fragments):
        raise RuntimeError("semi-formal reasoning certificate drifted")

    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    required_runbook_fragments = (
        "APPROVED_FOR_OFFLINE_CU129_BOOTSTRAP_DIAGNOSTIC_VERIFICATION_V3",
        "run_cu129_offline_runtime_compatibility_verifier_v3",
        "auragateway-cu129-offline-verifier-v2",
        "ENSUREPIP_BOOTSTRAP_FAILED",
        V3_VERIFIER_NAME,
        V3_OUTPUT_DIRECTORY,
        EXPECTED_V3_NOTEBOOK_SHA256,
        EXPECTED_EVIDENCE_ZIP_SHA256,
        "Accelerator: T4 x2",
        "Internet: Off",
        "Inputs: exactly the successful Version 1 materializer output",
        "Do not rerun verifier v2",
    )
    if any(fragment not in runbook for fragment in required_runbook_fragments):
        raise RuntimeError("CUDA 12.9 bootstrap runbook drifted")

    adr = (root / ADR_PATH).read_text(encoding="utf-8")
    required_adr_fragments = (
        "Status: Accepted",
        "ENSUREPIP_BOOTSTRAP_FAILED",
        EXPECTED_EVIDENCE_ZIP_SHA256,
        EXPECTED_EVIDENCE_MANIFEST_SHA256,
        EXPECTED_CERTIFICATE_SHA256,
        EXPECTED_V3_NOTEBOOK_SHA256,
        V3_VERIFIER_NAME,
    )
    if any(fragment not in adr for fragment in required_adr_fragments):
        raise RuntimeError("CUDA 12.9 bootstrap ADR drifted")

    return {
        "status": "VLLM_CU129_OFFLINE_BOOTSTRAP_REMEDIATION_PACKAGE_VALID",
        "decision": result.decision,
        "record_sha256": EXPECTED_RESULT_SHA256,
        "repository_base_commit": result.repository_base_commit,
        "v2_evidence_zip_sha256": EXPECTED_EVIDENCE_ZIP_SHA256,
        "v2_evidence_manifest_sha256": EXPECTED_EVIDENCE_MANIFEST_SHA256,
        "v2_evidence_files_verified": evidence["evidence_files_verified"],
        "v2_input_validation_status": evidence["input_validation_status"],
        "v2_observed_failed_role": evidence["observed_failed_role"],
        "v2_package_installation_started": evidence["package_installation_started"],
        "reasoning_certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
        "active_verifier_notebook_sha256": verifier["notebook_sha256"],
        "active_verifier_kaggle_title": V3_VERIFIER_NAME,
        "active_verifier_title_character_count": len(V3_VERIFIER_NAME),
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
