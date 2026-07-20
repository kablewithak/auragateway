from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_vllm_cu129_offline_bootstrap_remediation import (
    EVIDENCE_DIRECTORY,
    RESULT_PATH,
    V3_VERIFIER_PATH,
    OfflineBootstrapRemediationV1,
    _load_json_object,
    _notebook_source,
    validate_repository_package,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_notebook_namespace(repo_root: Path) -> dict[str, Any]:
    payload = _load_json_object(repo_root / V3_VERIFIER_PATH)
    source = _notebook_source(payload)
    namespace: dict[str, Any] = {"__name__": "verifier_v3_test"}
    exec(compile(source, V3_VERIFIER_PATH.as_posix(), "exec"), namespace)
    return namespace


def test_repository_package_valid(repo_root: Path) -> None:
    result = validate_repository_package(repo_root)

    assert result["status"] == ("VLLM_CU129_OFFLINE_BOOTSTRAP_REMEDIATION_PACKAGE_VALID")
    assert result["decision"] == ("APPROVED_FOR_OFFLINE_CU129_BOOTSTRAP_DIAGNOSTIC_VERIFICATION_V3")
    assert result["v2_input_validation_status"] == "PASSED"
    assert result["v2_observed_failed_role"] == "offline_isolated_install"
    assert result["v2_package_installation_started"] is False
    assert result["active_verifier_title_character_count"] == 37
    assert result["qualification_authorization_issued"] is False
    assert result["model_requests_performed"] == 0
    assert result["qualification_claimed"] is False


def test_result_rejects_root_cause_overclaim(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    v2_execution = payload["v2_execution"]
    assert isinstance(v2_execution, dict)
    v2_execution["nested_ensurepip_output_captured"] = True

    with pytest.raises(ValidationError):
        OfflineBootstrapRemediationV1.model_validate(payload)


def test_v2_evidence_preserves_single_observed_failure(repo_root: Path) -> None:
    install = _load_json_object(repo_root / EVIDENCE_DIRECTORY / "10_offline_isolated_install.json")
    summary = _load_json_object(repo_root / EVIDENCE_DIRECTORY / "90_summary.json")

    assert install["command_role"] == "offline_isolated_install"
    assert install["status"] == "FAILED"
    assert install["returncode"] == 1
    assert "ensurepip" in str(install["stderr_excerpt"])
    assert summary["status"] == "FAILED"
    assert summary["model_requests_performed"] == 0
    assert summary["qualification_claimed"] is False


def test_v3_notebook_separates_venv_creation_and_ensurepip(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / V3_VERIFIER_PATH)
    source = _notebook_source(payload)

    assert '"venv_create_without_pip"' in source
    assert '"--without-pip"' in source
    assert '"venv_ensurepip_bootstrap"' in source
    assert '"ensurepip", "--upgrade", "--default-pip"' in source
    assert '"offline_hash_locked_install"' in source
    assert '"--require-hashes"' in source
    assert '"BLOCKED_BY_UPSTREAM_FAILURE"' in source
    assert '"NOT_EXECUTED"' in source


def test_v3_failure_taxonomy_marks_downstream_blocked(repo_root: Path) -> None:
    namespace = _load_notebook_namespace(repo_root)
    required_roles = namespace["REQUIRED_ROLES"]
    blocked_record = namespace["blocked_record"]
    summarize = namespace["summarize_role_states"]

    records = [
        {
            "command_role": "venv_ensurepip_bootstrap",
            "status": "FAILED",
        }
    ]
    for role in required_roles:
        if role != "venv_ensurepip_bootstrap":
            records.append(
                blocked_record(
                    role,
                    blocked_by="venv_ensurepip_bootstrap",
                    reason="captured ensurepip bootstrap failed",
                )
            )

    states = summarize(records)

    assert states["failed_required_roles"] == ["venv_ensurepip_bootstrap"]
    assert len(states["blocked_required_roles"]) == len(required_roles) - 1
    assert states["not_executed_required_roles"] == []


def test_v3_failure_taxonomy_marks_missing_role_not_executed(repo_root: Path) -> None:
    namespace = _load_notebook_namespace(repo_root)
    required_roles = namespace["REQUIRED_ROLES"]
    summarize = namespace["summarize_role_states"]

    records = [
        {"command_role": role, "status": "PASSED"}
        for role in required_roles
        if role != "vllm_native_extension"
    ]
    states = summarize(records)

    assert states["failed_required_roles"] == []
    assert states["blocked_required_roles"] == []
    assert states["not_executed_required_roles"] == ["vllm_native_extension"]
