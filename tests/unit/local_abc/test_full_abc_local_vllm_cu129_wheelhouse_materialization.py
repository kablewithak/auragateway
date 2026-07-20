from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_vllm_cu129_wheelhouse_materialization import (
    EVIDENCE_DIRECTORY,
    EVIDENCE_MANIFEST_PATH,
    RESULT_PATH,
    V2_VERIFIER_PATH,
    WheelhouseMaterializationResultV1,
    _load_json_object,
    _notebook_source,
    _validate_materialization_metadata,
    validate_repository_package,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_repository_package_valid(repo_root: Path) -> None:
    result = validate_repository_package(repo_root)

    assert result["status"] == "VLLM_CU129_WHEELHOUSE_MATERIALIZATION_PACKAGE_VALID"
    assert result["decision"] == "APPROVED_FOR_OFFLINE_CU129_RUNTIME_COMPATIBILITY_VERIFICATION_V2"
    assert result["package_count"] == 176
    assert result["manifest_entry_count"] == 182
    assert result["total_wheel_bytes"] == 5_727_339_111
    assert result["active_verifier_title_character_count"] == 37
    assert result["authorization_issued"] is False
    assert result["model_requests_performed"] == 0
    assert result["qualification_claimed"] is False


def test_materialization_result_rejects_decision_drift(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    payload["decision"] = "QUALIFIED"

    with pytest.raises(ValidationError):
        WheelhouseMaterializationResultV1.model_validate(payload)


def test_active_verifier_binds_exact_materialization_topology(repo_root: Path) -> None:
    notebook = _load_json_object(repo_root / V2_VERIFIER_PATH)
    source = _notebook_source(notebook)

    assert '"resolution_lock.json"' in source
    assert "EXPECTED_PACKAGE_COUNT = 176" in source
    assert "EXPECTED_MANIFEST_ENTRY_COUNT = 182" in source
    assert "EXPECTED_TOTAL_WHEEL_BYTES = 5727339111" in source
    assert "def streaming_sha256" in source
    assert '"PIP_NO_INDEX": "1"' in source
    assert '"torch_family_runtime"' in source
    assert '"model_requests_performed=0"' in source
    assert '"qualification_claimed=false"' in source


def test_evidence_vault_contains_only_small_control_plane_files(
    repo_root: Path,
) -> None:
    payload = _load_json_object(repo_root / EVIDENCE_MANIFEST_PATH)
    files = payload["files"]
    assert isinstance(files, list)
    assert len(files) == 9

    paths = {cast(dict[str, Any], entry)["path"] for entry in files if isinstance(entry, dict)}
    assert paths == {
        "execution.log",
        "install_runtime.py",
        "materialization.lock.txt",
        "materialization_receipt.json",
        "requirements.in",
        "requirements.lock.txt",
        "runtime_manifest.json",
        "sha256_manifest.json",
        "source_evidence_identity.json",
    }
    assert not tuple((repo_root / EVIDENCE_DIRECTORY).glob("*.whl"))


def test_materialization_metadata_matches_resolution_lock(repo_root: Path) -> None:
    result = _validate_materialization_metadata(repo_root)

    assert result == {
        "manifest_entry_count": 182,
        "wheel_entry_count": 176,
        "non_wheel_entry_count": 6,
        "total_wheel_bytes": 5_727_339_111,
    }


def test_verifier_v1_is_superseded_before_execution(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    result = WheelhouseMaterializationResultV1.model_validate(payload)

    assert result.superseded_verifier.execution_authority == ("SUPERSEDED_BEFORE_EXECUTION")
    assert result.superseded_verifier.defect_code == (
        "OFFLINE_VERIFIER_TOPOLOGY_CONTRACT_OMITS_RESOLUTION_LOCK"
    )
    assert result.active_verifier.kaggle_title == ("auragateway-cu129-offline-verifier-v2")
