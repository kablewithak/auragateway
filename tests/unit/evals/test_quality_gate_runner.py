from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.evals.quality_gate_runner import (
    QualityGateAssetError,
    verify_assets,
    write_assets,
)

_FIXTURE_SOURCE = Path("data/evals/quality/noninferiority-v1/fixtures.json")


def _prepare_repo(tmp_path: Path) -> Path:
    fixture_target = tmp_path / "data/evals/quality/noninferiority-v1/fixtures.json"
    fixture_target.parent.mkdir(parents=True, exist_ok=True)
    fixture_target.write_bytes(_FIXTURE_SOURCE.read_bytes())

    deterministic_target = tmp_path / "data/evals/quality/deterministic-v1/manifest.json"
    deterministic_target.parent.mkdir(parents=True, exist_ok=True)
    deterministic_target.write_text(
        json.dumps(
            {
                "deterministic_scorers_passed": True,
                "measured_execution_permitted": False,
                "retrieval_configuration_fingerprint": (
                    "220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490"
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    protected_target = tmp_path / "data/evals/quality/execution-v1/manifest.json"
    protected_target.parent.mkdir(parents=True, exist_ok=True)
    protected_target.write_text(
        json.dumps(
            {
                "execution_controls_passed": True,
                "synthetic_fixture_execution": True,
                "human_review_completed": False,
                "measured_execution_permitted": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_build_and_verify_quality_gate_assets(tmp_path: Path) -> None:
    repo_root = _prepare_repo(tmp_path)

    summary = write_assets(repo_root)
    verified = verify_assets(repo_root)

    assert summary == verified
    assert summary.fixture_count == 10
    assert summary.negative_control_count == 9
    assert summary.quality_gate_dry_run_passed
    assert not summary.measured_execution_permitted


def test_verify_rejects_tampered_report(tmp_path: Path) -> None:
    repo_root = _prepare_repo(tmp_path)
    write_assets(repo_root)
    report_path = repo_root / "data/evals/quality/noninferiority-v1/report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["fixture_set_id"] = "auragateway-gate-6-quality-noninferiority-tampered"
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(QualityGateAssetError, match="does not match deterministic output"):
        verify_assets(repo_root)
