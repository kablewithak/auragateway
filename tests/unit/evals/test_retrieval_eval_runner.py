from __future__ import annotations

import json
import shutil
from pathlib import Path

from auragateway.evals.runner import (
    RetrievalEvaluationError,
    build_scorecard,
    main,
    verify_all_scorecards,
    verify_scorecard,
    write_scorecard,
)
from auragateway.retrieval.dense_runner import FIXED_WINDOW_DENSE_CONFIG
from auragateway.retrieval.runner import (
    FIXED_WINDOW_BM25_CONFIG,
    SECTION_AWARE_BM25_CONFIG,
)

REPO_ROOT = Path(".")


def _copy_eval_inputs(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    for relative in (
        "data/corpus",
        "data/chunking",
        "data/retrieval",
        "data/evals/retrieval/development-v1/accepted_cases.json",
        "data/evals/retrieval/development-v1/rejected_cases.json",
    ):
        source = Path(relative)
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return repo_root


def test_build_scorecard_returns_twenty_four_case_results() -> None:
    scorecard, results = build_scorecard(REPO_ROOT, FIXED_WINDOW_BM25_CONFIG.config_id)

    assert scorecard.aggregate.case_count == 24
    assert results.count(b"\n") == 24
    assert scorecard.aggregate.correct_source_in_top_k_rate == 1.0


def test_dense_scorecard_uses_same_twenty_four_cases() -> None:
    scorecard, results = build_scorecard(REPO_ROOT, FIXED_WINDOW_DENSE_CONFIG.config_id)

    assert scorecard.aggregate.case_count == 24
    assert results.count(b"\n") == 24
    assert scorecard.retriever_config_id == FIXED_WINDOW_DENSE_CONFIG.config_id


def test_both_persisted_scorecards_verify() -> None:
    summaries = verify_all_scorecards(REPO_ROOT)

    assert [summary.case_count for summary in summaries] == [24, 24, 24, 24]
    assert all(summary.validation_status == "valid" for summary in summaries)


def test_write_then_verify_scorecard_in_isolated_repo(tmp_path: Path) -> None:
    repo_root = _copy_eval_inputs(tmp_path)

    written = write_scorecard(repo_root, SECTION_AWARE_BM25_CONFIG.config_id)
    verified = verify_scorecard(repo_root, SECTION_AWARE_BM25_CONFIG.config_id)

    assert verified == written


def test_modified_case_results_are_rejected(tmp_path: Path) -> None:
    repo_root = _copy_eval_inputs(tmp_path)
    write_scorecard(repo_root, FIXED_WINDOW_BM25_CONFIG.config_id)
    results_path = (
        repo_root / "data/evals/retrieval/development-v1/bm25-fixed-window-v1/case_results.jsonl"
    )
    results_path.write_text(results_path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")

    try:
        verify_scorecard(repo_root, FIXED_WINDOW_BM25_CONFIG.config_id)
    except RetrievalEvaluationError as exc:
        assert exc.error_code == "RETRIEVAL_EVAL_CASE_RESULTS_MISMATCH"
        return
    raise AssertionError("modified case results were accepted")


def test_modified_scorecard_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_eval_inputs(tmp_path)
    write_scorecard(repo_root, FIXED_WINDOW_BM25_CONFIG.config_id)
    scorecard_path = (
        repo_root / "data/evals/retrieval/development-v1/bm25-fixed-window-v1/scorecard.json"
    )
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    payload["aggregate"]["mean_recall_at_k"] = 0.0
    scorecard_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        verify_scorecard(repo_root, FIXED_WINDOW_BM25_CONFIG.config_id)
    except RetrievalEvaluationError as exc:
        assert exc.error_code == "RETRIEVAL_EVAL_SCORECARD_MISMATCH"
        return
    raise AssertionError("modified scorecard was accepted")


def test_unknown_source_reference_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_eval_inputs(tmp_path)
    cases_path = repo_root / "data/evals/retrieval/development-v1/accepted_cases.json"
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    payload["cases"][0]["relevance_judgments"][0]["source_id"] = "NR-FAKE-999"
    payload["cases"][0]["required_sources"] = ["NR-FAKE-999"]
    cases_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        build_scorecard(repo_root, FIXED_WINDOW_BM25_CONFIG.config_id)
    except RetrievalEvaluationError as exc:
        assert exc.error_code == "RETRIEVAL_EVAL_UNKNOWN_SOURCE"
        return
    raise AssertionError("unknown corpus source was accepted")


def test_cli_verify_prints_content_free_summary(capsys: object) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert len(payload) == 4
    assert payload[0]["case_count"] == 24
    assert "query_text" not in captured.out
