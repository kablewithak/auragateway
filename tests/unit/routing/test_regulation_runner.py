from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.routing.regulation_runner import (
    RouteRegulationEvidenceError,
    build_route_regulation,
    verify_route_regulation,
)


def test_frozen_gate_five_regulation_evidence_verifies() -> None:
    repo_root = Path(__file__).parents[3]
    summary = verify_route_regulation(repo_root)
    assert summary.fixture_count == 13
    assert summary.negative_control_count == 9
    assert summary.gate_5_regulation_passed is True
    assert summary.measured_execution_permitted is False


def test_gate_five_builder_reproduces_report_in_isolated_copy(tmp_path: Path) -> None:
    repo_root = Path(__file__).parents[3]
    source = repo_root / "data" / "provider_fixtures" / "routing" / "regulation_cases.json"
    target = tmp_path / "data" / "provider_fixtures" / "routing" / "regulation_cases.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())

    built = build_route_regulation(tmp_path)
    verified = verify_route_regulation(tmp_path)
    assert built == verified
    report_path = target.with_name("regulation_report.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["gate_5_regulation_passed"] is True


def test_fixture_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    repo_root = Path(__file__).parents[3]
    source_dir = repo_root / "data" / "provider_fixtures" / "routing"
    target_dir = tmp_path / "data" / "provider_fixtures" / "routing"
    target_dir.mkdir(parents=True)
    for name in ("regulation_cases.json", "regulation_report.json", "regulation_manifest.json"):
        (target_dir / name).write_bytes((source_dir / name).read_bytes())

    fixture_path = target_dir / "regulation_cases.json"
    fixture_path.write_text(fixture_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RouteRegulationEvidenceError, match="fixture hash"):
        verify_route_regulation(tmp_path)
