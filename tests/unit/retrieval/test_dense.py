from __future__ import annotations

import hashlib
from pathlib import Path

from auragateway.contracts.chunking import ChunkingStrategy, CorpusChunk
from auragateway.contracts.corpus import (
    DocumentCompleteness,
    DocumentFormat,
    DocumentStatus,
)
from auragateway.contracts.dense_retrieval import DenseRetrievalConfiguration
from auragateway.contracts.retrieval import RetrievalFilter, RetrievalQuery, StalePolicy
from auragateway.retrieval.dense import DenseIndex, to_dense_evidence_result
from auragateway.retrieval.dense_runner import FIXED_WINDOW_DENSE_CONFIG


def _chunk(
    source_id: str,
    content: str,
    *,
    chunk_index: int = 0,
    api_area: str = "authentication",
    is_stale: bool = False,
) -> CorpusChunk:
    identity = f"{source_id}:{chunk_index}:{content}".encode()
    chunk_id = f"chunk-{hashlib.sha256(identity).hexdigest()[:24]}"
    return CorpusChunk(
        chunk_id=chunk_id,
        source_id=source_id,
        document_path=f"data/corpus/documents/{source_id.lower()}.md",
        source_version="1.0",
        document_format=DocumentFormat.MARKDOWN,
        api_area=api_area,
        source_status=(DocumentStatus.DEPRECATED if is_stale else DocumentStatus.CURRENT),
        is_stale=is_stale,
        conflict_group_id=None,
        completeness=DocumentCompleteness.COMPLETE,
        near_duplicate_group_id=None,
        version_sensitive_procedure=False,
        strategy=ChunkingStrategy.FIXED_WINDOW,
        config_id="fixed-window-v1",
        config_sha256="a" * 64,
        chunk_index=chunk_index,
        parent_headings=(),
        content=content,
        token_count=len(content.split()),
        character_count=len(content),
        content_sha256="b" * 64,
    )


def _config() -> DenseRetrievalConfiguration:
    return DenseRetrievalConfiguration(
        config_id="dense-test-v1",
        chunking_config_id="fixed-window-v1",
        vector_dimension=128,
    )


def _load_chunks(path: Path) -> tuple[CorpusChunk, ...]:
    return tuple(
        CorpusChunk.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def test_dense_index_returns_no_hits_for_out_of_vocabulary_query() -> None:
    index = DenseIndex((_chunk("NR-TEST-001", "alpha beta gamma"),), _config())

    result = index.search(RetrievalQuery(query_id="no-match", query_text="delta epsilon"))

    assert result.hits == ()
    assert result.positive_score_count == 0


def test_dense_ties_use_stable_source_id_order() -> None:
    index = DenseIndex(
        (
            _chunk("NR-TEST-002", "same retrieval terms"),
            _chunk("NR-TEST-001", "same retrieval terms"),
        ),
        _config(),
    )

    result = index.search(RetrievalQuery(query_id="tie-test", query_text="retrieval"))

    assert [hit.source_id for hit in result.hits] == ["NR-TEST-001", "NR-TEST-002"]


def test_dense_metadata_filter_excludes_stale_chunks() -> None:
    index = DenseIndex(
        (
            _chunk("NR-TEST-001", "API key lifetime 24 hours"),
            _chunk("NR-TEST-002", "API key lifetime seven days", is_stale=True),
        ),
        _config(),
    )
    query = RetrievalQuery(
        query_id="current-only",
        query_text="API key lifetime",
        filters=RetrievalFilter(stale_policy=StalePolicy.EXCLUDE),
    )

    result = index.search(query)

    assert result.candidate_count == 1
    assert [hit.source_id for hit in result.hits] == ["NR-TEST-001"]


def test_dense_repeated_search_is_deterministic() -> None:
    chunks = _load_chunks(Path("data/chunking/fixed-window-v1/chunks.jsonl"))
    index = DenseIndex(chunks, FIXED_WINDOW_DENSE_CONFIG)
    query = RetrievalQuery(
        query_id="dense-determinism-test",
        query_text="webhook retry window 72 hours",
        filters=RetrievalFilter(api_areas=("webhooks",)),
    )

    assert index.search(query) == index.search(query)


def test_dense_fixed_window_ranks_current_auth_source_first() -> None:
    chunks = _load_chunks(Path("data/chunking/fixed-window-v1/chunks.jsonl"))
    index = DenseIndex(chunks, FIXED_WINDOW_DENSE_CONFIG)
    query = RetrievalQuery(
        query_id="dense-auth-current",
        query_text="current API v2 key lifetime 24 hours rotation",
        filters=RetrievalFilter(
            api_areas=("authentication",),
            stale_policy=StalePolicy.EXCLUDE,
            version_sensitive_only=True,
        ),
    )

    result = index.search(query)

    assert result.hits
    assert result.hits[0].source_id == "NR-AUTH-001"
    assert result.hits[0].similarity_evidence.shared_nonzero_dimensions > 0


def test_dense_evidence_projection_removes_content() -> None:
    index = DenseIndex((_chunk("NR-TEST-001", "alpha beta gamma"),), _config())
    result = index.search(RetrievalQuery(query_id="dense-evidence", query_text="alpha"))

    evidence = to_dense_evidence_result(result)

    assert "content" not in evidence.model_dump(mode="json")["hits"][0]
