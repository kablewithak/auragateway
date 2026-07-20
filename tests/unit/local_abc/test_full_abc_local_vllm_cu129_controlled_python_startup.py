from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_vllm_cu129_controlled_python_startup import (
    RESULT_PATH,
    V6_NOTEBOOK_PATH,
    ControlledPythonStartupRemediationV1,
    _load_json_object,
    _notebook_source,
    _validate_startup_evidence,
    _validate_v5_evidence,
    validate_repository_package,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_repository_package_valid(repo_root: Path) -> None:
    result = validate_repository_package(repo_root)

    assert result["status"] == ("VLLM_CU129_CONTROLLED_PYTHON_STARTUP_REMEDIATION_PACKAGE_VALID")
    assert result["decision"] == (
        "APPROVED_FOR_OFFLINE_CU129_CONTROLLED_PYTHON_STARTUP_VERIFICATION_V6"
    )
    assert result["v5_first_divergence"] == ("target_runtime_identity_before_install")
    assert result["v5_package_installation_started"] is False
    assert result["startup_disposition"] == ("CONTROLLED_SITE_BOOTSTRAP_CONFIRMED")
    assert result["controlled_site_bootstrap_confirmed"] is True
    assert result["active_verifier_title_character_count"] == 37
    assert result["model_requests_performed"] == 0
    assert result["qualification_claimed"] is False


def test_decision_record_rejects_drift(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    payload["decision"] = "QUALIFIED"

    with pytest.raises(ValidationError):
        ControlledPythonStartupRemediationV1.model_validate(payload)


def test_controlled_role_set_rejects_omission(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    active = copy.deepcopy(payload["active_verifier"])
    assert isinstance(active, dict)
    roles = active["controlled_target_roles"]
    assert isinstance(roles, list)
    active["controlled_target_roles"] = roles[:-1]
    payload["active_verifier"] = active

    with pytest.raises(ValidationError):
        ControlledPythonStartupRemediationV1.model_validate(payload)


def test_v5_evidence_assigns_startup_customization_leak(
    repo_root: Path,
) -> None:
    result = _validate_v5_evidence(repo_root)

    assert result["first_divergence"] == ("target_runtime_identity_before_install")
    assert result["package_installation_started"] is False


def test_startup_evidence_confirms_controlled_bootstrap(
    repo_root: Path,
) -> None:
    result = _validate_startup_evidence(repo_root)

    assert result["disposition"] == "CONTROLLED_SITE_BOOTSTRAP_CONFIRMED"
    assert result["controlled_site_bootstrap_confirmed"] is True


def test_v6_uses_controlled_target_wrapper_for_all_target_python_roles(
    repo_root: Path,
) -> None:
    notebook = _load_json_object(repo_root / V6_NOTEBOOK_PATH)
    source = _notebook_source(notebook)

    assert "def controlled_target_argv(" in source
    assert source.count("controlled_target_argv(") >= 11
    assert 'sys.modules["sitecustomize"] = sentinel("sitecustomize")' in source
    assert 'sys.modules["usercustomize"] = sentinel("usercustomize")' in source
    assert "site.main()" in source
    assert (
        re.search(
            r"\[\s*str\(python\),\s*\"-c\"",
            source,
            re.MULTILINE,
        )
        is None
    )


def test_v6_preserves_target_first_loader_and_offline_install(
    repo_root: Path,
) -> None:
    notebook = _load_json_object(repo_root / V6_NOTEBOOK_PATH)
    source = _notebook_source(notebook)

    assert '"TARGET_NVIDIA_LIBRARIES_PREPENDED"' in source
    assert '"--without-pip"' in source
    assert '"--python"' in source
    assert '"--no-index"' in source
    assert '"--no-cache-dir"' in source
    assert '"--require-hashes"' in source
    assert '"canonical_nvjitlink_resolution"' in source
    assert '"canonical_cusparse_direct_load"' in source


def test_v6_preserves_safety_nonclaims(repo_root: Path) -> None:
    notebook = _load_json_object(repo_root / V6_NOTEBOOK_PATH)
    source = _notebook_source(notebook)

    assert '"model_requests_performed": 0' in source
    assert '"benchmark_trajectory_requests_performed": 0' in source
    assert '"qualification_claimed": False' in source
    assert "AutoModel" not in source
    assert "from_pretrained" not in source
    assert "LLM(" not in source
