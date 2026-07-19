from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_control_output_discovery_remediation as remediation,
)

ROOT = Path(__file__).resolve().parents[3]


def test_repository_remediation_package_validates() -> None:
    summary = remediation.validate_repository_package(ROOT)

    assert summary == {
        "status": "CONTROL_OUTPUT_DISCOVERY_REMEDIATION_PACKAGE_VALID",
        "record_sha256": remediation._file_sha256(ROOT / remediation.RECORD_PATH),
        "failure_class": "INPUT_DISCOVERY_FAILURE",
        "failure_code": "CONTROL_OUTPUT_NAMESPACE_COLLISION",
        "failure_stage": "control_output_discovery",
        "evidence_zip_sha256": ("55910873d6282ce8b98efd2726d2630bfed4f1c706eb4ec6484adb8a66885926"),
        "evidence_files_verified": 3,
        "launcher_sha256": ("33e85b6982d9a07328854e922d1a4a0dadc15a92bebf6805e9c2dfa21c18624e"),
        "discovery_scope": "governed_control_output_root",
        "authorization_issued": False,
        "kaggle_gpu_session_started": True,
        "model_runtime_started": False,
        "model_requests_performed": 0,
        "next_gate": ("merge_control_root_scoped_launcher_then_issue_fresh_authorization"),
    }


def test_record_rejects_launcher_identity_drift(tmp_path: Path) -> None:
    payload = json.loads((ROOT / remediation.RECORD_PATH).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    remediation_payload = cast(dict[str, object], payload["remediation"])
    remediation_payload["launcher_notebook_sha256"] = "0" * 64

    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        RuntimeError,
        match="remediation record is invalid",
    ):
        remediation.load_record(record_path)


def test_record_rejects_control_file_contract_drift(tmp_path: Path) -> None:
    payload = json.loads((ROOT / remediation.RECORD_PATH).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    remediation_payload = cast(dict[str, object], payload["remediation"])
    remediation_payload["exact_flat_file_set"] = ["offline_dataset_manifest.json"]

    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        RuntimeError,
        match="remediation record is invalid",
    ):
        remediation.load_record(record_path)


def test_repository_validator_rejects_evidence_drift(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"

    for relative_path in (
        remediation.RECORD_PATH,
        remediation.LAUNCHER_FAILURE_PATH,
        remediation.LAUNCHER_FAILURE_TRACE_PATH,
        remediation.EVIDENCE_SHA256_PATH,
        remediation.LAUNCHER_PATH,
    ):
        source = ROOT / relative_path
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    (repo_root / remediation.LAUNCHER_FAILURE_TRACE_PATH).write_text(
        "drifted trace",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="remediation package drifted",
    ):
        remediation.validate_repository_package(repo_root)
