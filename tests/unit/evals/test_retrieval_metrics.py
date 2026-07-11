from __future__ import annotations

import hashlib
from pathlib import Path

from auragateway.contracts.chunking import ChunkingStrategy, CorpusChunk
from auragateway.contracts.corpus import (
    DocumentCompleteness,
    DocumentFormat,
    DocumentStatus,
)
from auragateway.contracts.retrieval import RetrievalConfiguration, RetrievalFilter, StalePolicy
from auragateway.contracts.retrieval_eval import (
    RetrievalCaseFamily,
    RetrievalEvaluationCase,
    SourceRelevanceJudgment,
    TerminalDecision,
)
from auragateway.evals.retrieval import aggregate_metrics, evaluate_case
from auragateway.retrieval.bm25 import BM25Index
from auragateway.retrieval.runner import (
    FIXED_WINDOW_BM25_CONFIG,
    SECTION_AWARE_BM25_CONFIG,
)


def _chunk(
    source_id: str,
    content: str,
    *,
    chunk_index: int = 0,
    is_stale: bool = False,
    api_area: str = "test",
) -> CorpusChunk:
    identity = f"{source_id}:{chunk_index}:{content}".encode()
    return CorpusChunk(
        chunk_id=f"chunk-{hashlib.sha256(identity).hexdigest()[:24]}",
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


def _case(
    *,
    required_source: str = "NR-TEST-001",
    relevant_sources: tuple[SourceRelevanceJudgment, ...] | None = None,
    forbidden_sources: tuple[str, ...] = (),
    near_duplicate_sources: tuple[str, ...] = (),
    stale_policy: StalePolicy = StalePolicy.INCLUDE,
) -> RetrievalEvaluationCase:
    return RetrievalEvaluationCase(
        case_id="dev-ret-999",
        case_family=(
            RetrievalCaseFamily.NEAR_DUPLICATE_DISPLACEMENT
            if near_duplicate_sources
            else RetrievalCaseFamily.EXACT_PROCEDURE
        ),
        failure_hypothesis="The retriever may rank an unsupported source before grounded evidence.",
        query_text="alpha retrieval evidence",
        top_k=3,
        filters=RetrievalFilter(stale_policy=stale_policy),
        relevance_judgments=relevant_sources
        or (
            SourceRelevanceJudgment(
                source_id=required_source,
                grade=3,
                rationale=(
                    "This source contains the complete grounded answer for the diagnostic query."
                ),
            ),
        ),
        required_sources=(required_source,),
        forbidden_sources=forbidden_sources,
        near_duplicate_sources=near_duplicate_sources,
        expected_terminal_decision=TerminalDecision.ANSWER,
        required_information_gain=("Retrieve the grounded answer source.",),
        acceptable_variants=("Return the supported answer.",),
        failure_labels=("WRONG_SOURCE",),
        accept_reason="Accepted because the case exposes deterministic source-ranking behaviour.",
        difficulty_reason=(
            "The candidate sources share terms and can displace the preferred evidence."
        ),
    )


def _load_chunks(path: Path) -> tuple[CorpusChunk, ...]:
    return tuple(
        CorpusChunk.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def test_duplicate_chunks_do_not_inflate_source_recall() -> None:
    chunks = (
        _chunk("NR-TEST-001", "alpha retrieval evidence", chunk_index=0),
        _chunk("NR-TEST-001", "alpha retrieval evidence", chunk_index=1),
        _chunk("NR-TEST-002", "unrelated material", chunk_index=0),
    )
    index = BM25Index(
        chunks,
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
            default_top_k=3,
        ),
    )

    result = evaluate_case(index, _case())

    assert result.recall_at_k == 1.0
    assert result.precision_at_k == 0.333333333333
    assert result.ranked_hit_source_ids[:2] == ("NR-TEST-001", "NR-TEST-001")
    assert result.ranked_unique_source_ids == ("NR-TEST-001",)


def test_relevant_stale_conflict_evidence_is_not_counted_as_unwanted_stale() -> None:
    judgments = (
        SourceRelevanceJudgment(
            source_id="NR-TEST-001",
            grade=3,
            rationale=(
                "Current source resolves the diagnostic conflict with authoritative guidance."
            ),
        ),
        SourceRelevanceJudgment(
            source_id="NR-TEST-002",
            grade=2,
            rationale="Stale source is required to explain the conflicting historical guidance.",
        ),
    )
    chunks = (
        _chunk("NR-TEST-001", "alpha current evidence"),
        _chunk("NR-TEST-002", "alpha legacy evidence", is_stale=True),
    )
    index = BM25Index(
        chunks,
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
        ),
    )

    result = evaluate_case(
        index,
        _case(required_source="NR-TEST-001", relevant_sources=judgments),
    )

    assert result.stale_source_retrieval_rate == 0.0


def test_unwanted_stale_source_is_counted() -> None:
    chunks = (
        _chunk("NR-TEST-001", "alpha current evidence"),
        _chunk("NR-TEST-002", "alpha legacy evidence", is_stale=True),
    )
    index = BM25Index(
        chunks,
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
        ),
    )

    result = evaluate_case(index, _case())

    assert result.stale_source_retrieval_rate == 0.5


def test_near_duplicate_displacement_is_detected() -> None:
    chunks = (
        _chunk("NR-TEST-002", "alpha alpha retrieval evidence"),
        _chunk("NR-TEST-001", "alpha retrieval evidence"),
    )
    index = BM25Index(
        chunks,
        RetrievalConfiguration(
            config_id="bm25-test-v1",
            chunking_config_id="fixed-window-v1",
        ),
    )
    judgments = (
        SourceRelevanceJudgment(
            source_id="NR-TEST-001",
            grade=3,
            rationale="Preferred source contains the exact requested interface procedure.",
        ),
        SourceRelevanceJudgment(
            source_id="NR-TEST-002",
            grade=1,
            rationale="Near duplicate is related but targets a different interface variant.",
        ),
    )

    result = evaluate_case(
        index,
        _case(
            relevant_sources=judgments,
            near_duplicate_sources=("NR-TEST-002",),
        ),
    )

    assert result.near_duplicate_displacement is True


def test_real_bm25_candidates_produce_expected_development_metrics() -> None:
    from auragateway.evals.runner import _load_assets

    development_set, _, _ = _load_assets(Path("."))
    fixed_chunks = _load_chunks(Path("data/chunking/fixed-window-v1/chunks.jsonl"))
    section_chunks = _load_chunks(Path("data/chunking/section-aware-v1/chunks.jsonl"))
    fixed_results = tuple(
        evaluate_case(BM25Index(fixed_chunks, FIXED_WINDOW_BM25_CONFIG), case)
        for case in development_set.cases
    )
    section_results = tuple(
        evaluate_case(BM25Index(section_chunks, SECTION_AWARE_BM25_CONFIG), case)
        for case in development_set.cases
    )

    fixed = aggregate_metrics(fixed_results)
    section = aggregate_metrics(section_results)

    assert fixed.case_count == 24
    assert fixed.mean_recall_at_k == 1.0
    assert fixed.citation_support_readiness_rate == 0.916666666667
    assert section.mean_recall_at_k == 0.972222222222
    assert section.citation_support_readiness_rate == 0.875
