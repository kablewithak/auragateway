from __future__ import annotations

import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_vllm_cu129_target_directory_install import (
    RESULT_PATH,
    V7_NOTEBOOK_PATH,
    TargetDirectoryInstallRemediationV1,
    _load_json_object,
    _notebook_source,
    _validate_inspection_v1_evidence,
    _validate_inspection_v2_evidence,
    _validate_v6_evidence,
    validate_repository_package,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_repository_package_valid(repo_root: Path) -> None:
    result = validate_repository_package(repo_root)

    assert result["status"] == ("VLLM_CU129_TARGET_DIRECTORY_INSTALL_REMEDIATION_PACKAGE_VALID")
    assert result["decision"] == (
        "APPROVED_FOR_OFFLINE_CU129_TARGET_DIRECTORY_INSTALL_VERIFICATION_V7"
    )
    assert result["v6_first_divergence"] == "base_pip_python_target_support"
    assert result["inspection_v1_disposition"] == ("NO_SAFE_BASE_PIP_INSTALL_EXECUTOR_CONFIRMED")
    assert result["inspection_v2_disposition"] == ("BASE_PIP_TARGET_DIRECTORY_INSTALL_CONFIRMED")
    assert result["selected_installation_executor"] == ("BASE_PIP_TARGET_DIRECTORY")
    assert result["target_directory_install_confirmed"] is True
    assert result["base_distribution_metadata_unchanged"] is True
    assert result["active_verifier_title_character_count"] == 37
    assert result["model_requests_performed"] == 0
    assert result["qualification_claimed"] is False


def test_decision_record_rejects_executor_drift(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    remediation = copy.deepcopy(payload["selected_remediation"])
    assert isinstance(remediation, dict)
    remediation["installation_executor"] = "BASE_PIP_PYTHON_TARGET"
    payload["selected_remediation"] = remediation

    with pytest.raises(ValidationError):
        TargetDirectoryInstallRemediationV1.model_validate(payload)


def test_decision_record_rejects_controlled_role_omission(
    repo_root: Path,
) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    active = copy.deepcopy(payload["active_verifier"])
    assert isinstance(active, dict)
    roles = active["controlled_target_roles"]
    assert isinstance(roles, list)
    active["controlled_target_roles"] = roles[:-1]
    payload["active_verifier"] = active

    with pytest.raises(ValidationError):
        TargetDirectoryInstallRemediationV1.model_validate(payload)


def test_v6_evidence_is_diagnostic_failure(repo_root: Path) -> None:
    summary = _validate_v6_evidence(repo_root)

    assert summary["status"] == "FAILED"
    assert summary["first_divergence"] == "base_pip_python_target_support"
    assert summary["package_installation_started"] is False
    assert summary["base_distribution_metadata_unchanged"] is True


def test_inspection_v1_is_invalid_for_executor_selection(
    repo_root: Path,
) -> None:
    summary = _validate_inspection_v1_evidence(repo_root)

    assert summary["disposition"] == ("NO_SAFE_BASE_PIP_INSTALL_EXECUTOR_CONFIRMED")
    assert summary["full_closure_installation_performed"] is False


def test_inspection_v2_confirms_target_directory(
    repo_root: Path,
) -> None:
    summary = _validate_inspection_v2_evidence(repo_root)

    assert summary["disposition"] == ("BASE_PIP_TARGET_DIRECTORY_INSTALL_CONFIRMED")
    assert summary["selected_installation_executor"] == ("BASE_PIP_TARGET_DIRECTORY")
    assert summary["prefix_install_confirmed"] is False
    assert summary["target_directory_install_confirmed"] is True
    assert summary["base_distribution_metadata_unchanged"] is True


def test_v7_notebook_uses_target_directory_executor(
    repo_root: Path,
) -> None:
    source = _notebook_source(repo_root / V7_NOTEBOOK_PATH)

    assert '"--target"' in source
    assert '"--no-deps"' in source
    assert '"--ignore-installed"' in source
    assert "TARGET_DEPENDENCY_CHECK_SCRIPT" in source
    assert "CONTROLLED_TARGET_METADATA_AND_PACKAGING" in source
    assert '"--python"' not in source


def test_v7_notebook_prohibits_model_execution(
    repo_root: Path,
) -> None:
    source = _notebook_source(repo_root / V7_NOTEBOOK_PATH)

    assert "from_pretrained(" not in source
    assert "LLM(" not in source
    assert "AsyncLLM" not in source
    assert ".generate(" not in source
    assert "snapshot_download(" not in source
    assert "model_requests_performed=0" in source
    assert "qualification_claimed=false" in source
