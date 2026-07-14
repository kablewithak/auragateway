from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.publication.hugging_face import (
    DATASET_ROOT,
    SPACE_ROOT,
    build_candidate_payloads,
    build_publication,
    build_publication_state,
    validate_publication,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_build_publication_state_preserves_terminal_claim_boundary() -> None:
    state = build_publication_state(_repo_root())

    assert state.comparison_eligible is False
    assert state.live_inference_included is False
    assert state.credential_required is False
    assert len(state.provider_lineages) == 2
    assert all(not item.cache_telemetry_observed for item in state.provider_lineages)


def test_candidate_contains_static_dataset_and_space() -> None:
    state = build_publication_state(_repo_root())
    payloads = build_candidate_payloads(_repo_root(), state)

    assert DATASET_ROOT / "README.md" in payloads
    assert DATASET_ROOT / "data/provider_evidence.jsonl" in payloads
    assert SPACE_ROOT / "index.html" in payloads
    assert SPACE_ROOT / "evidence.js" in payloads
    assert b"sdk: static" in payloads[SPACE_ROOT / "README.md"]
    assert b"no live inference" in payloads[SPACE_ROOT / "index.html"].lower()


def test_build_and_validate_publication_round_trip(tmp_path: Path) -> None:
    destination = tmp_path / "repo"
    _copy_source_tree(_repo_root(), destination)

    manifest = build_publication(destination)
    validated = validate_publication(destination)

    assert validated == manifest
    assert len(manifest.dataset_files) == 9
    assert len(manifest.space_files) == 8
    assert manifest.remote_publication_authorized is False


def test_builder_rejects_terminal_review_drift(tmp_path: Path) -> None:
    destination = tmp_path / "repo"
    _copy_source_tree(_repo_root(), destination)
    review_path = (
        destination / "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/review.json"
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["comparison_eligible"] = True
    review_path.write_text(json.dumps(review), encoding="utf-8")

    with pytest.raises(ValueError, match="terminal review drifted"):
        build_publication_state(destination)


def _copy_source_tree(source: Path, destination: Path) -> None:
    import shutil

    paths = (
        "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1",
        "data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1",
        "data/publication/hugging-face-v1/publication_policy.json",
        "docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md",
        "src/auragateway/contracts/hugging_face_publication.py",
        "src/auragateway/publication/__init__.py",
        "src/auragateway/publication/hugging_face.py",
        "src/auragateway/publication/hugging_face_runner.py",
    )
    for relative in paths:
        source_path = source / relative
        destination_path = destination / relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_dir():
            shutil.copytree(source_path, destination_path)
        else:
            shutil.copy2(source_path, destination_path)
