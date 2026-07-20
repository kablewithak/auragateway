from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_vllm_cu129_base_pip_target_install import (
    RESULT_PATH,
    V4_VERIFIER_PATH,
    BasePipTargetInstallRemediationV1,
    _load_json_object,
    _notebook_source,
    _validate_v3_evidence,
    classify_role_states,
    pip_version_supported,
    validate_repository_package,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_repository_package_valid(repo_root: Path) -> None:
    result = validate_repository_package(repo_root)

    assert result["status"] == ("VLLM_CU129_BASE_PIP_TARGET_INSTALL_REMEDIATION_PACKAGE_VALID")
    assert result["decision"] == (
        "APPROVED_FOR_OFFLINE_CU129_BASE_PIP_TARGET_INSTALL_VERIFICATION_V4"
    )
    assert result["v3_input_validation_status"] == "PASSED"
    assert result["v3_first_divergence"] == "base_ensurepip_import"
    assert result["v3_failure_code"] == "ENSUREPIP_MODULE_ABSENT"
    assert result["v3_package_installation_started"] is False
    assert result["installation_executor"] == "BASE_PIP_PYTHON_TARGET"
    assert result["minimum_base_pip_version"] == "22.3"
    assert result["active_verifier_title_character_count"] == 37
    assert result["qualification_authorization_issued"] is False
    assert result["model_requests_performed"] == 0
    assert result["qualification_claimed"] is False


def test_decision_record_rejects_drift(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    payload["decision"] = "QUALIFIED"

    with pytest.raises(ValidationError):
        BasePipTargetInstallRemediationV1.model_validate(payload)


def test_v3_evidence_assigns_ensurepip_absence(repo_root: Path) -> None:
    evidence = _validate_v3_evidence(repo_root)

    assert evidence["input_validation_status"] == "PASSED"
    assert evidence["first_divergence"] == "base_ensurepip_import"
    assert evidence["failure_code"] == "ENSUREPIP_MODULE_ABSENT"
    assert evidence["package_installation_started"] is False


def test_pip_version_gate() -> None:
    assert pip_version_supported("22.3") is True
    assert pip_version_supported("25.1.1") is True
    assert pip_version_supported("22.2.2") is False
    assert pip_version_supported("unknown") is False


def test_failure_taxonomy_distinguishes_observed_and_blocked() -> None:
    roles = ("base_pip", "install", "runtime")
    records: list[dict[str, object]] = [
        {"command_role": "base_pip", "status": "FAILED"},
        {
            "command_role": "install",
            "status": "BLOCKED_BY_UPSTREAM_FAILURE",
        },
    ]

    result = classify_role_states(records, roles)

    assert result == {
        "failed": ("base_pip",),
        "blocked": ("install",),
        "not_executed": ("runtime",),
    }


def test_v4_uses_supported_base_pip_target_contract(repo_root: Path) -> None:
    notebook = _load_json_object(repo_root / V4_VERIFIER_PATH)
    source = _notebook_source(notebook)

    assert '"--without-pip"' in source
    assert '"base_pip_python_target_support"' in source
    assert '"offline_hash_locked_install_via_base_pip"' in source
    assert '"--no-index"' in source
    assert '"--no-cache-dir"' in source
    assert '"--require-hashes"' in source
    assert '"base_ensurepip_import"' not in source
    assert '"venv_ensurepip_bootstrap"' not in source

    python_option = source.index('"--python"')
    install_subcommand = source.index('"install",', python_option)
    assert python_option < install_subcommand


def test_v4_preserves_independent_gpu_and_isolation_evidence(repo_root: Path) -> None:
    notebook = _load_json_object(repo_root / V4_VERIFIER_PATH)
    source = _notebook_source(notebook)

    gpu_index = source.index('"gpu_topology"')
    install_index = source.index('"offline_hash_locked_install_via_base_pip"')
    assert gpu_index < install_index
    assert '"target_runtime_identity_before_install"' in source
    assert '"prefix_matches_expected"' in source
    assert '"system_site_packages_enabled"' in source
    assert '"pip_present": False' in source


def test_v4_proves_target_closure_and_base_metadata_stability(repo_root: Path) -> None:
    notebook = _load_json_object(repo_root / V4_VERIFIER_PATH)
    source = _notebook_source(notebook)

    assert '"target_distribution_inventory"' in source
    assert '"target_dependency_check_via_base_pip"' in source
    assert '"base_distribution_snapshot_before"' in source
    assert '"base_distribution_snapshot_after"' in source
    assert '"base_distribution_metadata_unchanged"' in source
