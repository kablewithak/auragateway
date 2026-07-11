from __future__ import annotations

import json
import shutil
from pathlib import Path

from auragateway.retrieval.runner import (
    FIXED_WINDOW_BM25_CONFIG,
    SECTION_AWARE_BM25_CONFIG,
    RetrievalError,
    build_candidate,
    main,
    verify_all_candidates,
    verify_candidate,
    write_candidate,
)

REPO_ROOT = Path(".")


def _copy_retrieval_inputs(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    shutil.copytree("data/corpus", repo_root / "data/corpus")
    shutil.copytree("data/chunking", repo_root / "data/chunking")
    smoke_source = Path("data/retrieval/bm25-v1/smoke_queries.json")
    smoke_target = repo_root / smoke_source
    smoke_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(smoke_source, smoke_target)
    return repo_root


def test_build_candidate_returns_typed_index_statistics() -> None:
    manifest, results = build_candidate(REPO_ROOT, FIXED_WINDOW_BM25_CONFIG)

    assert manifest.source_document_count == 30
    assert manifest.chunk_count == 54
    assert manifest.smoke_query_count == 10
    assert manifest.total_index_tokens > 0
    assert manifest.vocabulary_size > 0
    assert results.count(b"\n") == 10


def test_both_persisted_candidates_verify() -> None:
    summaries = verify_all_candidates(REPO_ROOT)

    assert [summary.chunk_count for summary in summaries] == [54, 112]
    assert all(summary.validation_status == "valid" for summary in summaries)


def test_write_then_verify_candidate_in_isolated_repo(tmp_path: Path) -> None:
    repo_root = _copy_retrieval_inputs(tmp_path)

    written = write_candidate(repo_root, SECTION_AWARE_BM25_CONFIG)
    verified = verify_candidate(repo_root, SECTION_AWARE_BM25_CONFIG)

    assert verified == written


def test_modified_smoke_results_are_rejected(tmp_path: Path) -> None:
    repo_root = _copy_retrieval_inputs(tmp_path)
    write_candidate(repo_root, FIXED_WINDOW_BM25_CONFIG)
    results_path = repo_root / "data/retrieval/bm25-v1/fixed-window-v1/smoke_results.jsonl"
    results_path.write_text(results_path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")

    try:
        verify_candidate(repo_root, FIXED_WINDOW_BM25_CONFIG)
    except RetrievalError as exc:
        assert exc.error_code == "RETRIEVAL_SMOKE_RESULTS_MISMATCH"
        return
    raise AssertionError("modified smoke results were accepted")


def test_modified_retrieval_manifest_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_retrieval_inputs(tmp_path)
    write_candidate(repo_root, FIXED_WINDOW_BM25_CONFIG)
    manifest_path = repo_root / "data/retrieval/bm25-v1/fixed-window-v1/manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["vocabulary_size"] += 1
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        verify_candidate(repo_root, FIXED_WINDOW_BM25_CONFIG)
    except RetrievalError as exc:
        assert exc.error_code == "RETRIEVAL_MANIFEST_MISMATCH"
        return
    raise AssertionError("modified retrieval manifest was accepted")


def test_cli_verify_prints_safe_json(capsys: object) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert len(payload) == 2
    assert payload[0]["validation_status"] == "valid"
    assert "query_text" not in captured.out
