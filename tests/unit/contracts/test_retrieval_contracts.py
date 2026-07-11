from __future__ import annotations

from pydantic import ValidationError

from auragateway.contracts.corpus import DocumentCompleteness, DocumentStatus
from auragateway.contracts.retrieval import (
    RetrievalConfiguration,
    RetrievalEvidenceHit,
    RetrievalEvidenceResult,
    RetrievalFilter,
    RetrievalHit,
    RetrievalQuery,
    RetrievalResult,
    RetrievalSmokeQuerySet,
    StalePolicy,
)


def test_retrieval_configuration_rejects_invalid_b() -> None:
    try:
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
            b=1.1,
        )
    except ValidationError:
        return
    raise AssertionError("invalid BM25 b value was accepted")


def test_filter_rejects_duplicate_values() -> None:
    try:
        RetrievalFilter(api_areas=("authentication", "authentication"))
    except ValidationError:
        return
    raise AssertionError("duplicate metadata filter values were accepted")


def test_query_rejects_blank_text() -> None:
    try:
        RetrievalQuery(query_id="blank-query", query_text="   ")
    except ValidationError:
        return
    raise AssertionError("blank retrieval query was accepted")


def test_smoke_query_set_rejects_duplicate_ids() -> None:
    query = RetrievalQuery(query_id="duplicate-query", query_text="key lifetime")
    try:
        RetrievalSmokeQuerySet(query_set_id="test-v1", queries=(query, query))
    except ValidationError:
        return
    raise AssertionError("duplicate smoke-query IDs were accepted")


def _hit(rank: int, score: float, chunk_id: str) -> RetrievalHit:
    return RetrievalHit(
        rank=rank,
        score=score,
        chunk_id=chunk_id,
        source_id="NR-AUTH-001",
        document_path="data/corpus/documents/authentication/api-key-quickstart-v2.md",
        source_version="2.0",
        source_status=DocumentStatus.CURRENT,
        api_area="authentication",
        is_stale=False,
        completeness=DocumentCompleteness.COMPLETE,
        version_sensitive_procedure=True,
        chunk_index=rank - 1,
        parent_headings=(),
        content="API key lifetime is 24 hours.",
        content_sha256="a" * 64,
        matched_terms=("key",),
        term_contributions=(
            {
                "term": "key",
                "query_term_frequency": 1,
                "document_frequency": 1,
                "chunk_term_frequency": 1,
                "idf": 0.5,
                "score": score,
            },
        ),
    )


def test_result_rejects_non_contiguous_ranks() -> None:
    try:
        RetrievalResult(
            query_id="rank-test",
            query_sha256="b" * 64,
            retriever_config_id="bm25-test-v1",
            retriever_config_sha256="c" * 64,
            chunking_config_id="fixed-window-v1",
            top_k=5,
            filters=RetrievalFilter(stale_policy=StalePolicy.EXCLUDE),
            candidate_count=2,
            positive_score_count=2,
            hits=(_hit(2, 1.0, "chunk-aaaaaaaaaaaaaaaaaaaaaaaa"),),
        )
    except ValidationError:
        return
    raise AssertionError("non-contiguous retrieval ranks were accepted")


def test_content_free_evidence_contract_contains_no_content_field() -> None:
    evidence = RetrievalEvidenceResult(
        query_id="evidence-test",
        query_sha256="d" * 64,
        retriever_config_id="bm25-test-v1",
        retriever_config_sha256="e" * 64,
        chunking_config_id="fixed-window-v1",
        top_k=5,
        filters=RetrievalFilter(),
        candidate_count=1,
        positive_score_count=1,
        hits=(
            RetrievalEvidenceHit(
                rank=1,
                score=1.0,
                chunk_id="chunk-aaaaaaaaaaaaaaaaaaaaaaaa",
                source_id="NR-AUTH-001",
                document_path=("data/corpus/documents/authentication/api-key-quickstart-v2.md"),
                source_version="2.0",
                source_status=DocumentStatus.CURRENT,
                api_area="authentication",
                is_stale=False,
                chunk_index=0,
                parent_headings=(),
                matched_terms=("key",),
            ),
        ),
    )

    payload = evidence.model_dump(mode="json")

    assert "content" not in payload["hits"][0]
