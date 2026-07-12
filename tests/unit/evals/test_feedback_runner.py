from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.evals.feedback_runner import (
    EFCEvidenceAssetError,
    build_assets,
    verify_assets,
)


def _copy_assets(tmp_path: Path) -> None:
    paths = (
        "data/evals/feedback/efc-v1/fixtures.json",
        "data/evals/feedback/efc-v1/report.json",
        "data/evals/feedback/efc-v1/manifest.json",
        "data/evals/episodes/manifest.json",
        "data/evals/quality/noninferiority-v1/manifest.json",
    )
    for relative in paths:
        source = Path(relative)
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def test_verify_assets_reproduces_frozen_evidence(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    summary = verify_assets(tmp_path)
    assert summary.fixture_count == 11
    assert summary.negative_control_count == 9
    assert summary.efc_evidence_controls_passed is True
    assert summary.measured_execution_permitted is False
    assert summary.universal_efc_score_reported is False


def test_report_is_metadata_only() -> None:
    report, _, _ = build_assets(Path("."))
    payload = report.model_dump(mode="json")
    serialized = json.dumps(payload, sort_keys=True)
    prohibited = (
        "raw_feedback",
        "user_message",
        "prompt",
        "document_text",
        "model_output",
    )
    assert all(marker not in serialized for marker in prohibited)


def test_verify_rejects_report_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    report_path = tmp_path / "data/evals/feedback/efc-v1/report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["schema_version"] = "1.0.1"
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(EFCEvidenceAssetError, match="does not match"):
        verify_assets(tmp_path)
