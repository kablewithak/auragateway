from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.evidence.runner import (
    EvidenceBundleAssetError,
    build_assets,
    verify_assets,
    write_assets,
)

_REQUIRED_PATHS = (
    Path("data/evals/evidence/gate8-v1/fixtures.json"),
    Path("data/evals/episodes/manifest.json"),
    Path("data/evals/quality/noninferiority-v1/manifest.json"),
    Path("data/evals/feedback/efc-v1/manifest.json"),
    Path("docs/adr/ADR-0010-immutable-evidence-bundles-and-comparison-eligibility.md"),
)


def _copy_inputs(destination: Path) -> None:
    for relative_path in _REQUIRED_PATHS:
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative_path, target)


def test_build_assets_reconciles_fixed_counts() -> None:
    report, manifest, summary = build_assets(Path("."))

    assert report.fixture_count == 11
    assert report.negative_control_count == 8
    assert report.valid_bundle_count == 5
    assert report.gate_8_controls_passed is True
    assert manifest.gate_8_controls_passed is True
    assert summary.universal_claim_override_permitted is False


def test_verify_assets_matches_persisted_evidence() -> None:
    summary = verify_assets(Path("."))

    assert summary.gate_8_controls_passed is True
    assert summary.measured_execution_permitted is False


def test_verify_assets_detects_report_mutation(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)
    write_assets(tmp_path)
    report_path = tmp_path / "data/evals/evidence/gate8-v1/report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["results"][0]["case_id"] = "bundle-mutated-persisted-report"
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(EvidenceBundleAssetError) as exc_info:
        verify_assets(tmp_path)

    assert exc_info.value.error_code == "GATE8_REPORT_MISMATCH"
