from __future__ import annotations

import json
import shutil
from pathlib import Path

from auragateway.contracts.retrieval_selection import SelectionRecommendationStatus
from auragateway.evals.selection_runner import (
    RetrievalSelectionError,
    build_selection_evidence,
    main,
    verify_selection_evidence,
    write_selection_evidence,
)

REPO_ROOT = Path(".")


def _copy_selection_inputs(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    for relative in (
        "data/corpus",
        "data/chunking",
        "data/retrieval",
        "data/evals/retrieval/development-v1",
    ):
        source = Path(relative)
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
    selection_path = repo_root / "data/evals/retrieval/development-v1/selection-v1"
    if selection_path.exists():
        shutil.rmtree(selection_path)
    return repo_root


def test_build_selection_evidence_creates_thirty_six_variants() -> None:
    policy, variants, report = build_selection_evidence(REPO_ROOT)

    assert len(variants) == 36
    assert report.variant_count == 36
    assert report.eligible_variant_count == 12
    assert report.negative_control_variant_count == 24
    assert policy.held_out_validation_required


def test_selection_report_is_development_only() -> None:
    _, _, report = build_selection_evidence(REPO_ROOT)

    assert report.recommendation.status is SelectionRecommendationStatus.DEVELOPMENT_RECOMMENDED
    assert report.recommendation.retriever_config_id == "dense-hashed-tfidf-section-aware-v1"
    assert report.recommendation.top_k == 5
    assert report.recommendation.blocked_from_freeze
    assert report.held_out_validation_required
    assert not report.retrieval_freeze_permitted


def test_write_then_verify_selection_in_isolated_repo(tmp_path: Path) -> None:
    repo_root = _copy_selection_inputs(tmp_path)

    written = write_selection_evidence(repo_root)
    verified = verify_selection_evidence(repo_root)

    assert verified == written


def test_modified_selection_report_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_selection_inputs(tmp_path)
    write_selection_evidence(repo_root)
    report_path = repo_root / "data/evals/retrieval/selection-v1/report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["recommendation"]["blocked_from_freeze"] = False
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        verify_selection_evidence(repo_root)
    except RetrievalSelectionError as exc:
        assert exc.error_code == "RETRIEVAL_SELECTION_ARTIFACT_MISMATCH"
        return
    raise AssertionError("modified selection report was accepted")


def test_modified_variant_results_are_rejected(tmp_path: Path) -> None:
    repo_root = _copy_selection_inputs(tmp_path)
    write_selection_evidence(repo_root)
    variants_path = repo_root / "data/evals/retrieval/selection-v1/variants.jsonl"
    variants_path.write_text(
        variants_path.read_text(encoding="utf-8") + "{}\n",
        encoding="utf-8",
    )

    try:
        verify_selection_evidence(repo_root)
    except RetrievalSelectionError as exc:
        assert exc.error_code == "RETRIEVAL_SELECTION_ARTIFACT_MISMATCH"
        return
    raise AssertionError("modified selection variants were accepted")


def test_modified_upstream_scorecard_blocks_selection(tmp_path: Path) -> None:
    repo_root = _copy_selection_inputs(tmp_path)
    scorecard_path = (
        repo_root / "data/evals/retrieval/development-v1/bm25-fixed-window-v1/scorecard.json"
    )
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    payload["aggregate"]["mean_recall_at_k"] = 0.0
    scorecard_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        build_selection_evidence(repo_root)
    except RetrievalSelectionError as exc:
        assert exc.error_code == "RETRIEVAL_SELECTION_UPSTREAM_EVIDENCE_INVALID"
        return
    raise AssertionError("modified upstream scorecard was accepted")


def test_cli_verify_prints_safe_summary(capsys: object) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["variant_count"] == 36
    assert payload["held_out_validation_required"] is True
    assert "query_text" not in captured.out
