from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auragateway.evals.quality_runner import (
    QualityEvidenceError,
    build_quality_evidence,
    verify_quality_evidence,
)

_SOURCE_ROOT = Path(__file__).parents[3]


def _copy_repo_assets(target: Path) -> None:
    paths = (
        "data/evals/quality/deterministic-v1/fixtures.json",
        "data/evals/episodes/functional-v1/accepted_episodes.json",
        "data/evals/episodes/manifest.json",
        "data/corpus/source_inventory.json",
    )
    for relative in paths:
        source = _SOURCE_ROOT / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def test_build_and_verify_quality_evidence(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    built = build_quality_evidence(tmp_path)
    verified = verify_quality_evidence(tmp_path)

    assert built == verified
    assert built.fixture_count == 14
    assert built.negative_control_count == 10
    assert built.deterministic_scorers_passed is True
    assert built.measured_execution_permitted is False


def test_verify_rejects_fixture_hash_drift(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    build_quality_evidence(tmp_path)
    fixture_path = tmp_path / "data/evals/quality/deterministic-v1/fixtures.json"
    fixture_path.write_text(fixture_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(QualityEvidenceError, match="fixture hash"):
        verify_quality_evidence(tmp_path)
