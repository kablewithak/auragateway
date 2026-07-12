from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.context.runner import ContextBoundaryError, main, verify_context_boundary


def test_verify_context_boundary_returns_safe_summary() -> None:
    summary = verify_context_boundary(Path("."))
    assert summary.static_anchor_count == 6
    assert summary.volatile_item_kind_count == 6
    assert summary.gate_3_passed is False
    assert summary.measured_execution_permitted is False


def test_cli_prints_json_summary(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["validation_status"] == "valid"


def test_verifier_rejects_changed_anchor_bytes(tmp_path: Path) -> None:
    shutil.copytree("data", tmp_path / "data")
    shutil.copytree("docs", tmp_path / "docs")
    artifact = tmp_path / "docs/benchmark/Nimbus_Relay_Gate_2_Readiness_Report.md"
    artifact.write_text(artifact.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    with pytest.raises(ContextBoundaryError, match="registered hash"):
        verify_context_boundary(tmp_path)


def test_verifier_rejects_changed_registry_hash(tmp_path: Path) -> None:
    shutil.copytree("data", tmp_path / "data")
    shutil.copytree("docs", tmp_path / "docs")
    registry = tmp_path / "data/context/static_anchor_registry.json"
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["status"] = "changed"
    registry.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ContextBoundaryError, match="registry bytes"):
        verify_context_boundary(tmp_path)
