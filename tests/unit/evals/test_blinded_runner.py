"""Runner tests for frozen Gate 6 blinded quality evidence."""

from __future__ import annotations

import shutil
from pathlib import Path

from auragateway.evals.blinded_runner import build_assets, verify_assets, write_assets

ROOT = Path(__file__).parents[3]


def _copy_required_assets(destination: Path) -> None:
    paths = (
        "data/evals/quality/blinded-v1/rubric.json",
        "data/evals/quality/blinded-v1/fixtures.json",
        "data/evals/episodes/functional-v1/accepted_episodes.json",
        "data/evals/episodes/blinded_review_protocol.json",
        "data/evals/episodes/manifest.json",
        "data/evals/quality/deterministic-v1/manifest.json",
    )
    for relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def test_build_assets_has_expected_counts() -> None:
    assignments, report, manifest, summary = build_assets(ROOT)
    assert assignments.primary_assignment_count == 18
    assert assignments.secondary_assignment_count == 5
    assert report.fixture_count == 10
    assert report.negative_control_count == 5
    assert manifest.blinded_workflow_passed
    assert summary.material_disagreement_fixture_count == 4


def test_write_then_verify_round_trip(tmp_path: Path) -> None:
    _copy_required_assets(tmp_path)
    written = write_assets(tmp_path)
    verified = verify_assets(tmp_path)
    assert written == verified
    assert verified.blinded_workflow_passed


def test_repository_frozen_assets_verify() -> None:
    summary = verify_assets(ROOT)
    assert summary.primary_assignment_count == 18
    assert summary.secondary_assignment_count == 5
    assert not summary.measured_execution_permitted
