from __future__ import annotations

import hashlib
from pathlib import Path

from auragateway.contracts.chunking import ChunkingStrategy, CorpusChunk
from auragateway.contracts.corpus import (
    DocumentCompleteness,
    DocumentFormat,
    DocumentStatus,
)
from auragateway.contracts.retrieval import (
    RetrievalConfiguration,
    RetrievalFilter,
    RetrievalQuery,
    StalePolicy,
)
from auragateway.retrieval.bm25 import BM25Index, to_evidence_result, tokenize
from auragateway.retrieval.runner import FIXED_WINDOW_BM25_CONFIG


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


def _load_chunks(path: Path) -> tuple[CorpusChunk, ...]:
    return tuple(
        CorpusChunk.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def test_tokenize_is_casefolded_and_punctuation_independent() -> None:
    assert tokenize("API-Key: 24 HOURS") == ("api", "key", "24", "hours")


def test_index_returns_no_zero_score_hits() -> None:
    index = BM25Index(
        (_chunk("NR-TEST-001", "alpha beta gamma"),),
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
        ),
    )

    result = index.search(RetrievalQuery(query_id="no-match", query_text="delta epsilon"))

    assert result.hits == ()
    assert result.positive_score_count == 0


def test_ties_use_stable_source_id_order() -> None:
    index = BM25Index(
        (
            _chunk("NR-TEST-002", "same retrieval terms"),
            _chunk("NR-TEST-001", "same retrieval terms"),
        ),
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
        ),
    )

    result = index.search(RetrievalQuery(query_id="tie-test", query_text="retrieval"))

    assert [hit.source_id for hit in result.hits] == ["NR-TEST-001", "NR-TEST-002"]


def test_metadata_filter_excludes_stale_chunks_before_scoring() -> None:
    index = BM25Index(
        (
            _chunk("NR-TEST-001", "API key lifetime 24 hours"),
            _chunk("NR-TEST-002", "API key lifetime seven days", is_stale=True),
        ),
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
        ),
    )
    query = RetrievalQuery(
        query_id="current-only",
        query_text="API key lifetime",
        filters=RetrievalFilter(stale_policy=StalePolicy.EXCLUDE),
    )

    result = index.search(query)

    assert result.candidate_count == 1
    assert [hit.source_id for hit in result.hits] == ["NR-TEST-001"]


def test_fixed_window_corpus_ranks_current_auth_source_first() -> None:
    chunks = _load_chunks(Path("data/chunking/fixed-window-v1/chunks.jsonl"))
    index = BM25Index(chunks, FIXED_WINDOW_BM25_CONFIG)
    query = RetrievalQuery(
        query_id="auth-current-test",
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
    assert result.hits[0].is_stale is False


def test_repeated_search_is_deterministic() -> None:
    chunks = _load_chunks(Path("data/chunking/fixed-window-v1/chunks.jsonl"))
    index = BM25Index(chunks, FIXED_WINDOW_BM25_CONFIG)
    query = RetrievalQuery(
        query_id="determinism-test",
        query_text="webhook retry window 72 hours",
        filters=RetrievalFilter(api_areas=("webhooks",)),
    )

    first = index.search(query)
    second = index.search(query)

    assert first == second


def test_evidence_projection_removes_chunk_content() -> None:
    index = BM25Index(
        (_chunk("NR-TEST-001", "alpha beta gamma"),),
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
        ),
    )
    result = index.search(RetrievalQuery(query_id="evidence-test", query_text="alpha"))

    evidence = to_evidence_result(result)

    assert "content" not in evidence.model_dump(mode="json")["hits"][0]
