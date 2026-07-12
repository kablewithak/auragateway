"""Deterministic source-level retrieval metrics for development cases."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import cast

from auragateway.contracts.chunking import CorpusChunk
from auragateway.contracts.dense_retrieval import (
    DenseRetrievalHit,
    DenseRetrievalResult,
)
from auragateway.contracts.retrieval import (
    RetrievalFilter,
    RetrievalHit,
    RetrievalQuery,
    RetrievalResult,
)
from auragateway.contracts.retrieval_eval import (
    RetrievalAggregateMetrics,
    RetrievalCaseMetrics,
    RetrievalEvaluationCase,
)
from auragateway.retrieval.bm25 import BM25Index
from auragateway.retrieval.dense import DenseIndex

_METRIC_PRECISION = 12


def _round_metric(value: float) -> float:
    return round(value, _METRIC_PRECISION)


def _deduplicate(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def _dcg(grades: Iterable[int]) -> float:
    total = 0.0
    for rank, grade in enumerate(grades, start=1):
        total += float(2**grade - 1) / math.log2(rank + 1)
    return total


def _metadata_filter_matches(
    hit: RetrievalHit | DenseRetrievalHit,
    filters: RetrievalFilter,
) -> bool:
    if filters.api_areas and hit.api_area not in filters.api_areas:
        return False
    if filters.source_statuses and hit.source_status not in filters.source_statuses:
        return False
    if filters.completeness and hit.completeness not in filters.completeness:
        return False
    if filters.source_ids and hit.source_id not in filters.source_ids:
        return False
    if filters.stale_policy.value == "exclude" and hit.is_stale:
        return False
    if filters.stale_policy.value == "only" and not hit.is_stale:
        return False
    if filters.version_sensitive_only and not hit.version_sensitive_procedure:
        return False
    constraints = filters.metadata
    if constraints is None:
        return True
    metadata = hit.retrieval_metadata
    if metadata is None:
        return False
    if constraints.languages and metadata.language not in constraints.languages:
        return False
    if constraints.interface_kinds and metadata.interface_kind not in constraints.interface_kinds:
        return False
    if constraints.oauth_grants and metadata.oauth_grant not in constraints.oauth_grants:
        return False
    return not (
        constraints.representations and metadata.representation not in constraints.representations
    )


def evaluate_case(
    index: BM25Index | DenseIndex,
    case: RetrievalEvaluationCase,
) -> RetrievalCaseMetrics:
    """Run one accepted development case and compute deterministic source metrics."""

    result = index.search(
        RetrievalQuery(
            query_id=case.case_id,
            query_text=case.query_text,
            top_k=case.top_k,
            filters=case.filters,
        )
    )
    if not isinstance(result, (RetrievalResult, DenseRetrievalResult)):
        raise TypeError("unsupported retrieval result type")
    hits = cast(tuple[RetrievalHit | DenseRetrievalHit, ...], result.hits)
    ranked_hit_sources = tuple(hit.source_id for hit in hits)
    ranked_unique_sources = _deduplicate(ranked_hit_sources)
    relevance_by_source = {
        judgment.source_id: judgment.grade for judgment in case.relevance_judgments
    }
    relevant_sources = tuple(relevance_by_source)
    relevant_found = tuple(source for source in relevant_sources if source in ranked_unique_sources)
    required_found = tuple(
        source for source in case.required_sources if source in ranked_unique_sources
    )
    missing_required = tuple(
        source for source in case.required_sources if source not in ranked_unique_sources
    )
    forbidden_found = tuple(
        source for source in ranked_unique_sources if source in case.forbidden_sources
    )

    recall = len(relevant_found) / len(relevant_sources)
    precision = len(relevant_found) / case.top_k
    first_relevant_rank = next(
        (rank for rank, hit in enumerate(hits, start=1) if hit.source_id in relevance_by_source),
        None,
    )
    reciprocal_rank = 0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank

    seen_sources: set[str] = set()
    observed_grades: list[int] = []
    for hit in hits:
        if hit.source_id in seen_sources:
            observed_grades.append(0)
            continue
        seen_sources.add(hit.source_id)
        observed_grades.append(relevance_by_source.get(hit.source_id, 0))
    ideal_grades = sorted(relevance_by_source.values(), reverse=True)[: case.top_k]
    ideal_dcg = _dcg(ideal_grades)
    ndcg = 0.0 if ideal_dcg == 0.0 else _dcg(observed_grades) / ideal_dcg

    returned_count = len(hits)
    unsupported_count = sum(hit.source_id not in relevance_by_source for hit in hits)
    stale_count = sum(hit.is_stale and hit.source_id not in relevance_by_source for hit in hits)
    metadata_violations = tuple(
        hit.chunk_id for hit in hits if not _metadata_filter_matches(hit, case.filters)
    )
    rate_denominator = returned_count or 1

    required_positions = [
        rank
        for rank, source_id in enumerate(ranked_hit_sources, start=1)
        if source_id in case.required_sources
    ]
    near_duplicate_positions = [
        rank
        for rank, source_id in enumerate(ranked_hit_sources, start=1)
        if source_id in case.near_duplicate_sources
    ]
    near_duplicate_displacement = bool(
        case.near_duplicate_sources
        and near_duplicate_positions
        and (not required_positions or min(near_duplicate_positions) < min(required_positions))
    )

    all_required = not missing_required
    citation_ready = all_required and not forbidden_found and not metadata_violations
    return RetrievalCaseMetrics(
        case_id=case.case_id,
        case_family=case.case_family,
        query_sha256=result.query_sha256,
        retriever_config_id=result.retriever_config_id,
        retriever_config_sha256=result.retriever_config_sha256,
        chunking_config_id=result.chunking_config_id,
        top_k=case.top_k,
        returned_hit_count=returned_count,
        ranked_hit_source_ids=ranked_hit_sources,
        ranked_unique_source_ids=ranked_unique_sources,
        required_sources_found=required_found,
        missing_required_sources=missing_required,
        forbidden_sources_found=forbidden_found,
        relevant_sources_found=relevant_found,
        metadata_filter_violation_chunk_ids=metadata_violations,
        recall_at_k=_round_metric(recall),
        precision_at_k=_round_metric(precision),
        reciprocal_rank=_round_metric(reciprocal_rank),
        ndcg_at_k=_round_metric(ndcg),
        correct_source_in_top_k=bool(required_found),
        all_required_sources_in_top_k=all_required,
        citation_support_ready=citation_ready,
        unsupported_source_retrieval_rate=_round_metric(unsupported_count / rate_denominator),
        stale_source_retrieval_rate=_round_metric(stale_count / rate_denominator),
        metadata_filter_violation_rate=_round_metric(len(metadata_violations) / rate_denominator),
        near_duplicate_displacement=near_duplicate_displacement,
    )


def evaluate_cases(
    chunks: tuple[CorpusChunk, ...],
    index: BM25Index | DenseIndex,
    cases: tuple[RetrievalEvaluationCase, ...],
) -> tuple[RetrievalCaseMetrics, ...]:
    """Evaluate all cases after confirming the supplied index covers the chunks."""

    if index.chunk_count != len(chunks):
        raise ValueError("retrieval index and supplied chunks must contain the same chunk count")
    return tuple(evaluate_case(index, case) for case in cases)


def aggregate_metrics(
    results: tuple[RetrievalCaseMetrics, ...],
) -> RetrievalAggregateMetrics:
    """Aggregate case-level metrics without hiding per-case evidence."""

    if not results:
        raise ValueError("at least one retrieval case result is required")

    case_count = len(results)

    def mean(values: Iterable[float]) -> float:
        values_tuple = tuple(values)
        return _round_metric(sum(values_tuple) / len(values_tuple))

    near_duplicate_results = tuple(
        result for result in results if result.case_family.value == "near_duplicate_displacement"
    )
    displacement_rate = (
        mean(float(result.near_duplicate_displacement) for result in near_duplicate_results)
        if near_duplicate_results
        else 0.0
    )
    return RetrievalAggregateMetrics(
        case_count=case_count,
        mean_recall_at_k=mean(result.recall_at_k for result in results),
        mean_precision_at_k=mean(result.precision_at_k for result in results),
        mean_reciprocal_rank=mean(result.reciprocal_rank for result in results),
        mean_ndcg_at_k=mean(result.ndcg_at_k for result in results),
        correct_source_in_top_k_rate=mean(
            float(result.correct_source_in_top_k) for result in results
        ),
        all_required_sources_in_top_k_rate=mean(
            float(result.all_required_sources_in_top_k) for result in results
        ),
        citation_support_readiness_rate=mean(
            float(result.citation_support_ready) for result in results
        ),
        unsupported_source_retrieval_rate=mean(
            result.unsupported_source_retrieval_rate for result in results
        ),
        stale_source_retrieval_rate=mean(result.stale_source_retrieval_rate for result in results),
        metadata_filter_violation_rate=mean(
            result.metadata_filter_violation_rate for result in results
        ),
        near_duplicate_case_count=len(near_duplicate_results),
        near_duplicate_displacement_rate=displacement_rate,
    )
