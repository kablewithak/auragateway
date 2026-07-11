from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.chunking.runner import (
    FIXED_WINDOW_CONFIG,
    SECTION_AWARE_CONFIG,
    ChunkingError,
    build_candidate,
    main,
    verify_all_candidates,
    write_candidate,
)
from auragateway.contracts.chunking import CorpusChunk

REPO_ROOT = Path(".")


def _copy_repository_slice(tmp_path: Path) -> Path:
    for relative_path in (
        Path("data/corpus"),
        Path("data/chunking"),
    ):
        source = REPO_ROOT / relative_path
        if source.exists():
            shutil.copytree(source, tmp_path / relative_path)
    return tmp_path


def test_build_candidates_cover_all_frozen_sources() -> None:
    fixed_manifest, fixed_payload = build_candidate(REPO_ROOT, FIXED_WINDOW_CONFIG)
    section_manifest, section_payload = build_candidate(REPO_ROOT, SECTION_AWARE_CONFIG)

    assert fixed_manifest.source_document_count == 30
    assert section_manifest.source_document_count == 30
    assert fixed_manifest.chunk_count >= 30
    assert section_manifest.chunk_count >= 30
    assert fixed_manifest.chunks_sha256 != section_manifest.chunks_sha256
    assert fixed_payload != section_payload
    assert all(
        CorpusChunk.model_validate_json(line).token_count <= FIXED_WINDOW_CONFIG.target_tokens
        for line in fixed_payload.decode("utf-8").splitlines()
    )
    assert all(
        CorpusChunk.model_validate_json(line).token_count <= SECTION_AWARE_CONFIG.target_tokens
        for line in section_payload.decode("utf-8").splitlines()
    )


def test_generated_chunks_preserve_source_metadata() -> None:
    manifest, payload = build_candidate(REPO_ROOT, SECTION_AWARE_CONFIG)
    chunks = [
        CorpusChunk.model_validate_json(line) for line in payload.decode("utf-8").splitlines()
    ]

    assert len(chunks) == manifest.chunk_count
    assert {chunk.source_id for chunk in chunks} == {
        item.source_id for item in manifest.source_chunk_counts
    }
    assert any(chunk.is_stale for chunk in chunks)
    assert any(chunk.conflict_group_id is not None for chunk in chunks)
    assert any(chunk.parent_headings for chunk in chunks)


def test_verify_all_candidates_accepts_persisted_outputs() -> None:
    summaries = verify_all_candidates(REPO_ROOT)

    assert {summary.config_id for summary in summaries} == {
        "fixed-window-v1",
        "section-aware-v1",
    }
    assert all(summary.validation_status == "valid" for summary in summaries)


def test_verifier_rejects_modified_chunk_output(tmp_path: Path) -> None:
    repo_root = _copy_repository_slice(tmp_path)
    chunk_path = repo_root / "data/chunking/fixed-window-v1/chunks.jsonl"
    chunk_path.write_text(chunk_path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")

    with pytest.raises(ChunkingError, match="Persisted chunks") as error:
        from auragateway.chunking.runner import verify_candidate

        verify_candidate(repo_root, FIXED_WINDOW_CONFIG)

    assert error.value.error_code == "CHUNKING_OUTPUT_MISMATCH"


def test_verifier_rejects_modified_manifest(tmp_path: Path) -> None:
    repo_root = _copy_repository_slice(tmp_path)
    manifest_path = repo_root / "data/chunking/section-aware-v1/manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["chunk_count"] += 1
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(ChunkingError) as error:
        from auragateway.chunking.runner import verify_candidate

        verify_candidate(repo_root, SECTION_AWARE_CONFIG)

    assert error.value.error_code in {
        "CHUNKING_MANIFEST_VALIDATION_FAILED",
        "CHUNKING_MANIFEST_MISMATCH",
    }


def test_verifier_blocks_changed_frozen_corpus(tmp_path: Path) -> None:
    repo_root = _copy_repository_slice(tmp_path)
    source_path = repo_root / "data/corpus/documents/authentication/api-key-quickstart-v2.md"
    source_path.write_text(
        source_path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8"
    )

    with pytest.raises(ChunkingError) as error:
        build_candidate(repo_root, FIXED_WINDOW_CONFIG)

    assert error.value.error_code == "CHUNKING_FROZEN_CORPUS_INVALID"


def test_cli_verify_returns_typed_json(capsys: object) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert len(payload) == 2
    assert all(item["validation_status"] == "valid" for item in payload)


def test_write_candidate_is_idempotent(tmp_path: Path) -> None:
    repo_root = _copy_repository_slice(tmp_path)
    shutil.rmtree(repo_root / "data/chunking")

    first = write_candidate(repo_root, FIXED_WINDOW_CONFIG)
    first_payload = (repo_root / "data/chunking/fixed-window-v1/chunks.jsonl").read_bytes()
    second = write_candidate(repo_root, FIXED_WINDOW_CONFIG)
    second_payload = (repo_root / "data/chunking/fixed-window-v1/chunks.jsonl").read_bytes()

    assert first == second
    assert first_payload == second_payload
