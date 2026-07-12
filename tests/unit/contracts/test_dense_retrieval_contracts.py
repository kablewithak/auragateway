from __future__ import annotations

from pydantic import ValidationError

from auragateway.contracts.corpus import DocumentCompleteness, DocumentStatus
from auragateway.contracts.dense_retrieval import (
    DenseIndexManifest,
    DenseRetrievalConfiguration,
    DenseRetrievalEvidenceHit,
    DenseRetrievalEvidenceResult,
    DenseRetrievalHit,
    DenseRetrievalResult,
    DenseSimilarityEvidence,
)
from auragateway.contracts.retrieval import RetrievalFilter


def _evidence() -> DenseSimilarityEvidence:
    return DenseSimilarityEvidence(
        query_nonzero_dimensions=4,
        chunk_nonzero_dimensions=8,
        shared_nonzero_dimensions=2,
        cosine_similarity=0.5,
    )


def _hit(rank: int, score: float, chunk_id: str) -> DenseRetrievalHit:
    return DenseRetrievalHit(
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
        similarity_evidence=_evidence().model_copy(update={"cosine_similarity": score}),
    )


def test_dense_configuration_rejects_inverted_ngram_range() -> None:
    try:
        DenseRetrievalConfiguration(
            config_id="dense-test-v1",
            chunking_config_id="fixed-window-v1",
            minimum_ngram=2,
            maximum_ngram=1,
        )
    except ValidationError:
        return
    raise AssertionError("inverted dense n-gram range was accepted")


def test_dense_result_rejects_non_contiguous_ranks() -> None:
    try:
        DenseRetrievalResult(
            query_id="rank-test",
            query_sha256="b" * 64,
            retriever_config_id="dense-test-v1",
            retriever_config_sha256="c" * 64,
            chunking_config_id="fixed-window-v1",
            top_k=5,
            filters=RetrievalFilter(),
            candidate_count=2,
            positive_score_count=2,
            hits=(_hit(2, 0.5, "chunk-aaaaaaaaaaaaaaaaaaaaaaaa"),),
        )
    except ValidationError:
        return
    raise AssertionError("non-contiguous dense ranks were accepted")


def test_dense_manifest_requires_matching_vector_dimension() -> None:
    config = DenseRetrievalConfiguration(
        config_id="dense-test-v1",
        chunking_config_id="fixed-window-v1",
        vector_dimension=384,
    )
    try:
        DenseIndexManifest(
            corpus_id="nimbus-relay",
            corpus_version="1.0.0",
            config=config,
            config_sha256="a" * 64,
            chunking_manifest_path="data/chunking/fixed-window-v1/manifest.json",
            chunking_manifest_sha256="b" * 64,
            chunks_path="data/chunking/fixed-window-v1/chunks.jsonl",
            chunks_sha256="c" * 64,
            smoke_queries_path="data/retrieval/bm25-v1/smoke_queries.json",
            smoke_queries_sha256="d" * 64,
            smoke_results_path="data/retrieval/dense/smoke.jsonl",
            smoke_results_sha256="e" * 64,
            source_document_count=30,
            chunk_count=54,
            vocabulary_size=100,
            vector_dimension=256,
            average_nonzero_dimensions=20.0,
            smoke_query_count=10,
        )
    except ValidationError:
        return
    raise AssertionError("mismatched dense vector dimension was accepted")


def test_dense_evidence_contract_contains_no_content_field() -> None:
    evidence = DenseRetrievalEvidenceResult(
        query_id="evidence-test",
        query_sha256="d" * 64,
        retriever_config_id="dense-test-v1",
        retriever_config_sha256="e" * 64,
        chunking_config_id="fixed-window-v1",
        top_k=5,
        filters=RetrievalFilter(),
        candidate_count=1,
        positive_score_count=1,
        hits=(
            DenseRetrievalEvidenceHit(
                rank=1,
                score=0.5,
                chunk_id="chunk-aaaaaaaaaaaaaaaaaaaaaaaa",
                source_id="NR-AUTH-001",
                document_path=("data/corpus/documents/authentication/api-key-quickstart-v2.md"),
                source_version="2.0",
                source_status=DocumentStatus.CURRENT,
                api_area="authentication",
                is_stale=False,
                chunk_index=0,
                parent_headings=(),
                similarity_evidence=_evidence(),
            ),
        ),
    )

    payload = evidence.model_dump(mode="json")

    assert "content" not in payload["hits"][0]
