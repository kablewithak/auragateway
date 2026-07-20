"""Validate v6 and installation-executor evidence plus verifier v7."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Final, Literal, Self, cast

from pydantic import model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_vllm_cu129_controlled_python_startup import (
    validate_repository_package as validate_v6_package,
)

RESULT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_cu129_target_directory_install_remediation_v1.json"
)
ADR_PATH: Final = Path("docs/adr/2026-07-21-local-abc-vllm-cu129-target-directory-install.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_target_directory_install_v1.md")
CERTIFICATE_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Verifier_V6_Installation_Executor_Reasoning_Certificate.md"
)
INSPECTION_V1_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_pip_prefix_inspection_v1.ipynb"
)
INSPECTION_V2_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_pip_prefix_inspection_v2.ipynb"
)
V7_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v7.ipynb"
)
V6_EVIDENCE_DIRECTORY: Final = Path("evidence_vault/local_abc/vllm-cu129-offline-compatibility-v6")
INSPECTION_V1_EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/vllm-cu129-pip-prefix-inspection-v1"
)
INSPECTION_V2_EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/vllm-cu129-pip-prefix-inspection-v2"
)

EXPECTED_BASE_COMMIT: Final = "cafddfb46c1e2b8eecd830dc21aad0fc0b982200"
EXPECTED_RESULT_SHA256: Final = "69e057564f0f215095f1fde4244fc526905f79646c1dfe79d3e670f63b74cd22"
EXPECTED_CERTIFICATE_SHA256: Final = (
    "e803966fdaa11714c68a2d6d4ebb4f42da80b686251821d88da658758e798a0d"
)
EXPECTED_V7_NOTEBOOK_SHA256: Final = (
    "66fe0df31e49c035d858865749eca1755d5d09ce863b378a9f01fb55ac8bf7fd"
)
EXPECTED_INSPECTION_V1_NOTEBOOK_SHA256: Final = (
    "3c073d7bf2385c9aab0972c05abcc2e410e606143f2ab505cc80cc59c803a545"
)
EXPECTED_INSPECTION_V2_NOTEBOOK_SHA256: Final = (
    "6d426dc3b98f64033563384a24049950c46252b433d64c73d37f1032610963b6"
)
EXPECTED_V6_REPOSITORY_MANIFEST_SHA256: Final = (
    "1438bc8531dd961f0d57c64c9453099b4a84548a8e2848631de929900baa1656"
)
EXPECTED_INSPECTION_V1_REPOSITORY_MANIFEST_SHA256: Final = (
    "e204f778bc137ac89c9e433d0a197266ca34962284f754d2fd983152535b3422"
)
EXPECTED_INSPECTION_V2_REPOSITORY_MANIFEST_SHA256: Final = (
    "8499d4298793bc628b3c6b218496cac45232031c8177b4f34b67901da94cc483"
)

EXPECTED_CONTROLLED_ROLES: Final = (
    "target_runtime_identity_before_install",
    "target_distribution_inventory",
    "target_dependency_check_via_controlled_python",
    "canonical_cusparse_direct_load",
    "target_process_environment",
    "python_runtime",
    "torch_family_runtime",
    "transformers_runtime",
    "vllm_distribution",
    "vllm_module",
    "vllm_native_extension",
)
EXPECTED_INSTALL_FLAGS: Final = (
    "--no-index",
    "--no-cache-dir",
    "--no-deps",
    "--ignore-installed",
    "--require-hashes",
    "--target",
)


class TargetDirectoryInstallRemediationV1(LocalABCContract):
    """Governed target-directory installation decision."""

    schema_version: Literal["1.0.0"]
    repository_base_commit: Literal["cafddfb46c1e2b8eecd830dc21aad0fc0b982200"]
    evidence: dict[str, Any]
    reasoning_certificate: dict[str, Any]
    selected_remediation: dict[str, Any]
    active_verifier: dict[str, Any]
    decision: Literal["APPROVED_FOR_OFFLINE_CU129_TARGET_DIRECTORY_INSTALL_VERIFICATION_V7"]
    next_gate: Literal["run_cu129_offline_runtime_compatibility_verifier_v7"]
    safety: dict[str, Any]
    non_claims: list[str]

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        verifier_v6 = cast(dict[str, Any], self.evidence.get("verifier_v6"))
        inspection_v1 = cast(
            dict[str, Any],
            self.evidence.get("inspection_v1"),
        )
        inspection_v2 = cast(
            dict[str, Any],
            self.evidence.get("inspection_v2"),
        )
        if (
            verifier_v6.get("status") != "FAILED"
            or verifier_v6.get("first_divergence") != "base_pip_python_target_support"
            or verifier_v6.get("package_installation_started") is not False
        ):
            raise ValueError("verifier v6 evidence contract drifted")
        if (
            inspection_v1.get("disposition") != "INVALID_FOR_INSTALLER_SELECTION"
            or inspection_v1.get("failure_code") != "HARDCODED_PROBE_DISTRIBUTION_ABSENT"
        ):
            raise ValueError("inspection v1 evidence contract drifted")
        if (
            inspection_v2.get("disposition") != "BASE_PIP_TARGET_DIRECTORY_INSTALL_CONFIRMED"
            or inspection_v2.get("selected_installation_executor") != "BASE_PIP_TARGET_DIRECTORY"
            or inspection_v2.get("prefix_install_confirmed") is not False
            or inspection_v2.get("target_directory_install_confirmed") is not True
            or inspection_v2.get("base_distribution_metadata_unchanged") is not True
            or inspection_v2.get("full_closure_installation_performed") is not False
        ):
            raise ValueError("inspection v2 evidence contract drifted")

        certificate = self.reasoning_certificate
        if (
            certificate.get("sha256") != EXPECTED_CERTIFICATE_SHA256
            or certificate.get("result") != "REASONING_CHAIN_CONSISTENT"
            or certificate.get("evidence_sufficiency") != "SUFFICIENT_FOR_V7_REMEDIATION_DECISION"
        ):
            raise ValueError("reasoning certificate contract drifted")

        remediation = self.selected_remediation
        if (
            remediation.get("installation_executor") != "BASE_PIP_TARGET_DIRECTORY"
            or remediation.get("target_directory") != "VENV_PURELIB_SITE_PACKAGES"
            or tuple(remediation.get("full_closure_install_flags", ())) != EXPECTED_INSTALL_FLAGS
            or remediation.get("dependency_validation")
            != "CONTROLLED_TARGET_METADATA_AND_PACKAGING"
            or remediation.get("wheelhouse_rematerialization_justified") is not False
            or remediation.get("package_version_substitution_justified") is not False
        ):
            raise ValueError("selected remediation contract drifted")

        active = self.active_verifier
        if (
            active.get("notebook_sha256") != EXPECTED_V7_NOTEBOOK_SHA256
            or active.get("kaggle_title") != "auragateway-cu129-offline-verifier-v7"
            or active.get("title_character_count") != 37
            or active.get("installation_executor") != "BASE_PIP_TARGET_DIRECTORY"
            or active.get("dependency_validation") != "CONTROLLED_TARGET_METADATA_AND_PACKAGING"
            or active.get("python_startup_policy") != "NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"
            or active.get("canonical_loader_policy") != "TARGET_NVIDIA_LIBRARIES_PREPENDED"
            or tuple(active.get("controlled_target_roles", ())) != EXPECTED_CONTROLLED_ROLES
            or active.get("internet_enabled") is not False
            or active.get("model_requests_permitted") != 0
            or active.get("qualification_claimed") is not False
        ):
            raise ValueError("active verifier v7 contract drifted")

        safety = self.safety
        required_false = (
            "verifier_v6_rerun_permitted",
            "inspection_v1_rerun_permitted",
            "inspection_v2_rerun_permitted",
            "wheelhouse_rematerialization_permitted",
            "network_fallback_permitted",
            "model_loading_permitted",
            "worker_start_permitted",
            "qualification_authorization_issued",
            "customer_data_permitted",
            "credentials_permitted",
        )
        if any(safety.get(key) is not False for key in required_false):
            raise ValueError("safety contract drifted")
        if (
            safety.get("model_requests_permitted") != 0
            or safety.get("benchmark_trajectory_requests_permitted") != 0
        ):
            raise ValueError("request safety contract drifted")
        return self


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return cast(dict[str, Any], payload)


def _notebook_source(path: Path) -> str:
    payload = _load_json_object(path)
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError(f"notebook cells are invalid: {path}")
    sources: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = cell.get("source")
        if isinstance(source, list) and all(isinstance(item, str) for item in source):
            sources.append("".join(cast(list[str], source)))
        elif isinstance(source, str):
            sources.append(source)
        else:
            raise RuntimeError(f"notebook source is invalid: {path}")
    if len(sources) != 1:
        raise RuntimeError(f"expected one code cell: {path}")
    compile(sources[0], path.as_posix(), "exec")
    return sources[0]


def _validate_repository_manifest(
    directory: Path,
    expected_sha256: str,
) -> int:
    manifest_path = directory / "evidence_sha256.json"
    if _sha256(manifest_path) != expected_sha256:
        raise RuntimeError(f"repository evidence manifest drifted: {directory}")
    manifest = _load_json_object(manifest_path)
    files = manifest.get("files")
    if not isinstance(files, list):
        raise RuntimeError(f"repository evidence files are invalid: {directory}")
    observed_paths: set[str] = set()
    for raw_entry in files:
        if not isinstance(raw_entry, dict):
            raise RuntimeError("repository evidence entry is invalid")
        entry = cast(dict[str, Any], raw_entry)
        relative = entry.get("path")
        if not isinstance(relative, str) or "/" in relative or "\\" in relative:
            raise RuntimeError("repository evidence path is invalid")
        path = directory / relative
        if (
            not path.is_file()
            or path.stat().st_size != entry.get("size_bytes")
            or _sha256(path) != entry.get("sha256")
        ):
            raise RuntimeError(f"repository evidence identity drifted: {relative}")
        observed_paths.add(relative)
    expected_paths = {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.name != "evidence_sha256.json"
    }
    if observed_paths != expected_paths:
        raise RuntimeError(f"repository evidence topology drifted: {directory}")
    return len(files)


def _validate_internal_manifest(directory: Path) -> int:
    manifest = _load_json_object(directory / "99_evidence_sha256.json")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("internal evidence manifest is invalid")
    observed: set[str] = set()
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise RuntimeError("internal evidence entry is invalid")
        entry = cast(dict[str, Any], raw_entry)
        relative = entry.get("path")
        if not isinstance(relative, str):
            raise RuntimeError("internal evidence path is invalid")
        path = directory / relative
        if (
            not path.is_file()
            or path.stat().st_size != entry.get("size_bytes")
            or _sha256(path) != entry.get("sha256")
        ):
            raise RuntimeError(f"internal evidence identity drifted: {relative}")
        observed.add(relative)
    excluded = {
        "99_evidence_sha256.json",
        "execution.log",
        "source_evidence_identity.json",
        "evidence_sha256.json",
    }
    expected = {
        path.name for path in directory.iterdir() if path.is_file() and path.name not in excluded
    }
    if observed != expected:
        raise RuntimeError(f"internal evidence topology drifted: {directory}")
    return len(entries)


def _validate_source_identity(
    directory: Path,
    *,
    title: str,
    notebook_sha256: str,
    source_artifact_sha256: str,
    execution_log_sha256: str,
) -> None:
    identity = _load_json_object(directory / "source_evidence_identity.json")
    expected = {
        "schema_version": "1.0.0",
        "kaggle_title": title,
        "notebook_sha256": notebook_sha256,
        "captured_version": 1,
        "source_artifact_sha256": source_artifact_sha256,
        "execution_log_sha256": execution_log_sha256,
        "complete_execution_log_provided": True,
        "model_requests_performed": 0,
        "qualification_claimed": False,
    }
    drift = sorted(key for key, value in expected.items() if identity.get(key) != value)
    if drift:
        raise RuntimeError("source evidence identity drifted: " + ", ".join(drift))


def _validate_v6_evidence(root: Path) -> dict[str, Any]:
    directory = root / V6_EVIDENCE_DIRECTORY
    _validate_repository_manifest(
        directory,
        EXPECTED_V6_REPOSITORY_MANIFEST_SHA256,
    )
    _validate_internal_manifest(directory)
    _validate_source_identity(
        directory,
        title="auragateway-cu129-offline-verifier-v6",
        notebook_sha256=("48d4ee3a9dfce1eb4634a37e9e75fc5042d11d30cb0860c8455e8815c3b4e4f0"),
        source_artifact_sha256=("852b6d497adf620eca90c3719fe6dee1e607528ace6ac76cdf24907c009ada1f"),
        execution_log_sha256=("96d8ebb496e180124f945b6c3fe9a7cd16fabec9811625e5e569f39269ede3b7"),
    )
    summary = _load_json_object(directory / "90_summary.json")
    if (
        summary.get("status") != "FAILED"
        or summary.get("first_divergence") != "base_pip_python_target_support"
        or summary.get("package_installation_started") is not False
        or summary.get("base_distribution_metadata_unchanged") is not True
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("verifier v6 summary drifted")
    return summary


def _validate_inspection_v1_evidence(root: Path) -> dict[str, Any]:
    directory = root / INSPECTION_V1_EVIDENCE_DIRECTORY
    _validate_repository_manifest(
        directory,
        EXPECTED_INSPECTION_V1_REPOSITORY_MANIFEST_SHA256,
    )
    _validate_internal_manifest(directory)
    _validate_source_identity(
        directory,
        title="auragateway-cu129-pip-prefix-inspect-v1",
        notebook_sha256=EXPECTED_INSPECTION_V1_NOTEBOOK_SHA256,
        source_artifact_sha256=("b5f169d039544dcf304076b98613ff4b35525e1962daf9ff41f9ab275566c9e1"),
        execution_log_sha256=("622c4728573b20b450553bedb43e20bd5b8558f285e676bf54226056204b57c4"),
    )
    input_validation = _load_json_object(directory / "00_input_validation.json")
    summary = _load_json_object(directory / "90_summary.json")
    if (
        input_validation.get("status") != "FAILED"
        or input_validation.get("error_message") != "expected one wrapt record; observed 0"
        or summary.get("disposition") != "NO_SAFE_BASE_PIP_INSTALL_EXECUTOR_CONFIRMED"
        or summary.get("full_closure_installation_performed") is not False
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("inspection v1 evidence drifted")
    return summary


def _validate_inspection_v2_evidence(root: Path) -> dict[str, Any]:
    directory = root / INSPECTION_V2_EVIDENCE_DIRECTORY
    _validate_repository_manifest(
        directory,
        EXPECTED_INSPECTION_V2_REPOSITORY_MANIFEST_SHA256,
    )
    _validate_internal_manifest(directory)
    _validate_source_identity(
        directory,
        title="auragateway-cu129-pip-prefix-inspect-v2",
        notebook_sha256=EXPECTED_INSPECTION_V2_NOTEBOOK_SHA256,
        source_artifact_sha256=("3a13daccd9f796562436844aa33f3019bab7ad2b634bab5e7a0905511bc40b22"),
        execution_log_sha256=("ab55fdc1785f3ed77852c3d569bd6ec9bee7e94d1caeb492ffe0bcd742c95efc"),
    )
    input_validation = _load_json_object(directory / "00_input_validation.json")
    prefix_install = _load_json_object(directory / "10_04_base_pip_prefix_install_probe.json")
    prefix_probe = _load_json_object(directory / "10_05_controlled_prefix_distribution_probe.json")
    target_install = _load_json_object(
        directory / "10_06_base_pip_target_directory_install_probe.json"
    )
    target_probe = _load_json_object(
        directory / "10_07_controlled_target_directory_distribution_probe.json"
    )
    summary = _load_json_object(directory / "90_summary.json")
    if (
        input_validation.get("status") != "PASSED"
        or input_validation.get("selected_distribution") != "detect-installer"
        or input_validation.get("selected_version") != "0.1.0"
        or input_validation.get("selected_wheel_sha256")
        != "034fb20fd665c36e6ba52b8821525ea07fb4f7f938cac459df889fb33801528a"
        or prefix_install.get("status") != "PASSED"
        or prefix_probe.get("status") != "FAILED"
        or target_install.get("status") != "PASSED"
        or target_probe.get("status") != "PASSED"
        or summary.get("disposition") != "BASE_PIP_TARGET_DIRECTORY_INSTALL_CONFIRMED"
        or summary.get("selected_installation_executor") != "BASE_PIP_TARGET_DIRECTORY"
        or summary.get("prefix_install_confirmed") is not False
        or summary.get("target_directory_install_confirmed") is not True
        or summary.get("base_distribution_metadata_unchanged") is not True
        or summary.get("full_closure_installation_performed") is not False
        or summary.get("model_requests_performed") != 0
        or summary.get("qualification_claimed") is not False
    ):
        raise RuntimeError("inspection v2 evidence drifted")
    return summary


def _validate_v7_notebook(root: Path) -> None:
    path = root / V7_NOTEBOOK_PATH
    if _sha256(path) != EXPECTED_V7_NOTEBOOK_SHA256:
        raise RuntimeError("verifier v7 notebook identity drifted")
    source = _notebook_source(path)
    required = (
        'NOTEBOOK_NAME = "auragateway-cu129-offline-verifier-v7"',
        '"offline_hash_locked_install_via_base_pip_target_directory"',
        '"target_dependency_check_via_controlled_python"',
        '"--target"',
        '"--no-deps"',
        '"--ignore-installed"',
        "TARGET_DEPENDENCY_CHECK_SCRIPT",
        "CONTROLLED_TARGET_METADATA_AND_PACKAGING",
        '"BASE_PIP_TARGET_DIRECTORY"',
        "TARGET_NVIDIA_LIBRARIES_PREPENDED",
        "NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP",
        "model_requests_performed=0",
        "qualification_claimed=false",
    )
    if any(fragment not in source for fragment in required):
        raise RuntimeError("verifier v7 notebook semantic contract drifted")
    forbidden = (
        '"--python"',
        "from_pretrained(",
        "LLM(",
        "AsyncLLM",
        ".generate(",
        "snapshot_download(",
    )
    if any(fragment in source for fragment in forbidden):
        raise RuntimeError("verifier v7 notebook contains prohibited behavior")


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    baseline = validate_v6_package(root)

    result_path = root / RESULT_PATH
    if _sha256(result_path) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("target-directory decision record drifted")
    decision = TargetDirectoryInstallRemediationV1.model_validate(_load_json_object(result_path))
    if decision.repository_base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError("target-directory repository base commit drifted")

    if (
        _sha256(root / INSPECTION_V1_NOTEBOOK_PATH) != EXPECTED_INSPECTION_V1_NOTEBOOK_SHA256
        or _sha256(root / INSPECTION_V2_NOTEBOOK_PATH) != EXPECTED_INSPECTION_V2_NOTEBOOK_SHA256
    ):
        raise RuntimeError("installation inspection notebook drifted")
    _validate_v7_notebook(root)

    v6 = _validate_v6_evidence(root)
    inspection_v1 = _validate_inspection_v1_evidence(root)
    inspection_v2 = _validate_inspection_v2_evidence(root)

    if _sha256(root / CERTIFICATE_PATH) != EXPECTED_CERTIFICATE_SHA256:
        raise RuntimeError("installation executor certificate drifted")

    adr = (root / ADR_PATH).read_text(encoding="utf-8")
    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    required_adr = (
        "Status: Accepted",
        "BASE_PIP_TARGET_DIRECTORY",
        "CONTROLLED_TARGET_METADATA_AND_PACKAGING",
        "BASE_PIP_TARGET_DIRECTORY_INSTALL_CONFIRMED",
        EXPECTED_CERTIFICATE_SHA256,
    )
    required_runbook = (
        "APPROVED_FOR_OFFLINE_CU129_TARGET_DIRECTORY_INSTALL_VERIFICATION_V7",
        "run_cu129_offline_runtime_compatibility_verifier_v7",
        EXPECTED_BASE_COMMIT,
        EXPECTED_V7_NOTEBOOK_SHA256,
        EXPECTED_RESULT_SHA256,
        "Title: auragateway-cu129-offline-verifier-v7",
        "Accelerator: T4 x2",
        "Internet: Off",
        "model_requests_permitted=0",
        "qualification_claimed=false",
    )
    if any(fragment not in adr for fragment in required_adr):
        raise RuntimeError("target-directory ADR drifted")
    if any(fragment not in runbook for fragment in required_runbook):
        raise RuntimeError("target-directory runbook drifted")

    return {
        "status": ("VLLM_CU129_TARGET_DIRECTORY_INSTALL_REMEDIATION_PACKAGE_VALID"),
        "baseline_status": baseline.get("status"),
        "decision": decision.decision,
        "next_gate": decision.next_gate,
        "v6_first_divergence": v6["first_divergence"],
        "inspection_v1_disposition": inspection_v1["disposition"],
        "inspection_v2_disposition": inspection_v2["disposition"],
        "selected_installation_executor": (inspection_v2["selected_installation_executor"]),
        "target_directory_install_confirmed": (inspection_v2["target_directory_install_confirmed"]),
        "base_distribution_metadata_unchanged": (
            inspection_v2["base_distribution_metadata_unchanged"]
        ),
        "active_verifier_kaggle_title": (decision.active_verifier["kaggle_title"]),
        "active_verifier_title_character_count": (
            decision.active_verifier["title_character_count"]
        ),
        "active_verifier_notebook_sha256": EXPECTED_V7_NOTEBOOK_SHA256,
        "model_requests_performed": 0,
        "qualification_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    print(
        json.dumps(
            validate_repository_package(args.repo_root),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
