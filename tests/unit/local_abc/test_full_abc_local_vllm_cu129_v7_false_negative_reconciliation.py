from __future__ import annotations

import copy
import json
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_vllm_cu129_v7_false_negative_reconciliation import (
    RESULT_PATH,
    V7_EVIDENCE_DIRECTORY,
    VerifierV7FalseNegativeReconciliationV1,
    _is_target_nvjitlink_resolution,
    _validate_structural_target_resolution,
    _validate_v7_evidence,
    validate_repository_package,
)


def _load_json_object(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_repository_package_valid(repo_root: Path) -> None:
    result = validate_repository_package(repo_root)

    assert result["status"] == ("VLLM_CU129_VERIFIER_V7_FALSE_NEGATIVE_RECONCILIATION_VALID")
    assert result["reported_status"] == "FAILED"
    assert result["reported_first_divergence"] == "canonical_nvjitlink_resolution"
    assert result["runtime_prerequisite_status"] == "TECHNICALLY_PASSED"
    assert result["aggregate_summary_disposition"] == "FALSE_NEGATIVE"
    assert result["structural_target_resolution"] == "PASSED"
    assert result["verifier_v7_rerun_permitted"] is False
    assert result["model_requests_performed"] == 0
    assert result["qualification_claimed"] is False


def test_reconciliation_record_rejects_reported_status_rewrite(
    repo_root: Path,
) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    reported = copy.deepcopy(payload["reported_result"])
    assert isinstance(reported, dict)
    reported["status"] = "PASSED"
    payload["reported_result"] = reported

    with pytest.raises(ValidationError):
        VerifierV7FalseNegativeReconciliationV1.model_validate(payload)


def test_original_failed_summary_is_preserved(repo_root: Path) -> None:
    directory = repo_root / V7_EVIDENCE_DIRECTORY
    summary = _load_json_object(directory / "90_summary.json")
    canonical = _load_json_object(directory / "10_14_canonical_nvjitlink_resolution.json")

    assert summary["status"] == "FAILED"
    assert summary["failed_required_roles"] == ["canonical_nvjitlink_resolution"]
    assert summary["canonical_nvjitlink_resolved_to_target"] is False
    assert canonical["status"] == "FAILED"
    assert canonical["returncode"] == 0
    assert canonical["semantic_error"] == ("canonical loader did not select target nvJitLink")


def test_v7_target_path_passes_structural_resolution(repo_root: Path) -> None:
    result = _validate_structural_target_resolution(repo_root / V7_EVIDENCE_DIRECTORY)

    assert result["exact_inventory_path_match"] is True
    assert result["resolved_path_within_venv_root"] is True
    assert result["resolved_path"] == result["inventory_path"]


def test_inherited_cuda_path_fails_structural_resolution() -> None:
    venv_root = PurePosixPath("<working>/runtime")
    inventory = PurePosixPath(
        "<working>/runtime/lib/python3.12/site-packages/nvidia/nvjitlink/lib/libnvJitLink.so.12"
    )
    inherited = PurePosixPath("/usr/local/cuda/lib64/libnvJitLink.so.12")

    assert (
        _is_target_nvjitlink_resolution(
            venv_root=venv_root,
            resolved_path=inherited,
            inventory_path=inventory,
        )
        is False
    )


def test_sibling_runtime_path_fails_structural_resolution() -> None:
    venv_root = PurePosixPath("<working>/runtime-a")
    sibling = PurePosixPath(
        "<working>/runtime-b/lib/python3.12/site-packages/nvidia/nvjitlink/lib/libnvJitLink.so.12"
    )

    assert (
        _is_target_nvjitlink_resolution(
            venv_root=venv_root,
            resolved_path=sibling,
            inventory_path=sibling,
        )
        is False
    )


def test_all_runtime_roles_support_evidence_backed_pass(repo_root: Path) -> None:
    result = _validate_v7_evidence(repo_root)

    assert result["reported_status"] == "FAILED"
    assert result["runtime_prerequisite_status"] == "TECHNICALLY_PASSED"
    assert result["aggregate_summary_disposition"] == "FALSE_NEGATIVE"
    assert result["model_requests_performed"] == 0
    assert result["qualification_claimed"] is False
