"""Failure-weighted development selection across retrieval candidates."""

from __future__ import annotations

from collections.abc import Iterable

from auragateway.contracts.retrieval import RetrievalFilter
from auragateway.contracts.retrieval_eval import (
    RetrievalAggregateMetrics,
    RetrievalCaseMetrics,
    RetrievalEvaluationCase,
)
from auragateway.contracts.retrieval_selection import (
    MetadataPolicy,
    PromotionGateResult,
    RetrievalSelectionPolicy,
    RetrievalSelectionVariant,
)
from auragateway.evals.retrieval import aggregate_metrics, evaluate_case
from auragateway.retrieval.bm25 import BM25Index
from auragateway.retrieval.dense import DenseIndex

_SCORE_PRECISION = 12


def _round_score(value: float) -> float:
    return round(value, _SCORE_PRECISION)


def apply_metadata_policy(
    case: RetrievalEvaluationCase,
    policy: MetadataPolicy,
) -> RetrievalFilter:
    """Apply one declared or negative-control metadata policy."""

    if policy is MetadataPolicy.AUTHORED:
        return case.filters
    if policy is MetadataPolicy.API_AREA_ONLY:
        return RetrievalFilter(api_areas=case.filters.api_areas)
    if policy is MetadataPolicy.NONE:
        return RetrievalFilter()
    raise ValueError(f"unsupported metadata policy: {policy}")


def evaluate_variant_cases(
    index: BM25Index | DenseIndex,
    cases: tuple[RetrievalEvaluationCase, ...],
    top_k: int,
    metadata_policy: MetadataPolicy,
) -> tuple[RetrievalCaseMetrics, ...]:
    """Evaluate one candidate under one top-k and metadata-policy variant."""

    transformed = tuple(
        case.model_copy(
            update={
                "top_k": top_k,
                "filters": apply_metadata_policy(case, metadata_policy),
            }
        )
        for case in cases
    )
    return tuple(evaluate_case(index, case) for case in transformed)


def weighted_case_rates(
    results: tuple[RetrievalCaseMetrics, ...],
    cases: tuple[RetrievalEvaluationCase, ...],
    policy: RetrievalSelectionPolicy,
) -> tuple[float, float, tuple[str, ...]]:
    """Return failure-weighted case pass and failure rates."""

    if len(results) != len(cases):
        raise ValueError("case results and evaluation cases must have equal length")
    cases_by_id = {case.case_id: case for case in cases}
    total_weight = 0.0
    passed_weight = 0.0
    failed_case_ids: list[str] = []
    for result in results:
        case = cases_by_id.get(result.case_id)
        if case is None:
            raise ValueError(f"result references unknown case: {result.case_id}")
        weight = policy.case_family_weights.for_family(case.case_family)
        total_weight += weight
        if result.citation_support_ready:
            passed_weight += weight
        else:
            failed_case_ids.append(result.case_id)
    if total_weight <= 0.0:
        raise ValueError("case-family weights must produce a positive total")
    pass_rate = _round_score(passed_weight / total_weight)
    failure_rate = _round_score(1.0 - pass_rate)
    return pass_rate, failure_rate, tuple(failed_case_ids)


def _minimum_gate(gate_id: str, observed: float, threshold: float) -> PromotionGateResult:
    return PromotionGateResult(
        gate_id=gate_id,
        passed=observed >= threshold,
        observed=observed,
        threshold=threshold,
        comparator=">=",
    )


def _maximum_gate(gate_id: str, observed: float, threshold: float) -> PromotionGateResult:
    return PromotionGateResult(
        gate_id=gate_id,
        passed=observed <= threshold,
        observed=observed,
        threshold=threshold,
        comparator="<=",
    )


def promotion_gate_results(
    aggregate: RetrievalAggregateMetrics,
    weighted_case_pass_rate: float,
    policy: RetrievalSelectionPolicy,
) -> tuple[PromotionGateResult, ...]:
    """Evaluate the predeclared development promotion gates."""

    thresholds = policy.thresholds
    return (
        _minimum_gate(
            "minimum_mean_recall_at_k",
            aggregate.mean_recall_at_k,
            thresholds.minimum_mean_recall_at_k,
        ),
        _minimum_gate(
            "minimum_correct_source_in_top_k_rate",
            aggregate.correct_source_in_top_k_rate,
            thresholds.minimum_correct_source_in_top_k_rate,
        ),
        _minimum_gate(
            "minimum_all_required_sources_in_top_k_rate",
            aggregate.all_required_sources_in_top_k_rate,
            thresholds.minimum_all_required_sources_in_top_k_rate,
        ),
        _minimum_gate(
            "minimum_citation_support_readiness_rate",
            aggregate.citation_support_readiness_rate,
            thresholds.minimum_citation_support_readiness_rate,
        ),
        _minimum_gate(
            "minimum_mean_reciprocal_rank",
            aggregate.mean_reciprocal_rank,
            thresholds.minimum_mean_reciprocal_rank,
        ),
        _minimum_gate(
            "minimum_weighted_case_pass_rate",
            weighted_case_pass_rate,
            thresholds.minimum_weighted_case_pass_rate,
        ),
        _maximum_gate(
            "maximum_unsupported_source_retrieval_rate",
            aggregate.unsupported_source_retrieval_rate,
            thresholds.maximum_unsupported_source_retrieval_rate,
        ),
        _maximum_gate(
            "maximum_stale_source_retrieval_rate",
            aggregate.stale_source_retrieval_rate,
            thresholds.maximum_stale_source_retrieval_rate,
        ),
        _maximum_gate(
            "maximum_metadata_filter_violation_rate",
            aggregate.metadata_filter_violation_rate,
            thresholds.maximum_metadata_filter_violation_rate,
        ),
        _maximum_gate(
            "maximum_near_duplicate_displacement_rate",
            aggregate.near_duplicate_displacement_rate,
            thresholds.maximum_near_duplicate_displacement_rate,
        ),
    )


def benefit_score(
    aggregate: RetrievalAggregateMetrics,
    weighted_case_pass_rate: float,
    policy: RetrievalSelectionPolicy,
) -> float:
    """Calculate the positive metric component of selection score."""

    weights = policy.benefit_weights
    value = (
        aggregate.mean_recall_at_k * weights.mean_recall_at_k
        + aggregate.all_required_sources_in_top_k_rate * weights.all_required_sources_in_top_k_rate
        + aggregate.citation_support_readiness_rate * weights.citation_support_readiness_rate
        + aggregate.mean_reciprocal_rank * weights.mean_reciprocal_rank
        + aggregate.mean_ndcg_at_k * weights.mean_ndcg_at_k
        + aggregate.mean_precision_at_k * weights.mean_precision_at_k
        + weighted_case_pass_rate * weights.weighted_case_pass_rate
    )
    return _round_score(value)


def penalty_score(
    aggregate: RetrievalAggregateMetrics,
    policy: RetrievalSelectionPolicy,
) -> float:
    """Calculate the evidence-noise and safety penalty component."""

    weights = policy.penalty_weights
    value = (
        aggregate.unsupported_source_retrieval_rate * weights.unsupported_source_retrieval_rate
        + aggregate.stale_source_retrieval_rate * weights.stale_source_retrieval_rate
        + aggregate.metadata_filter_violation_rate * weights.metadata_filter_violation_rate
        + aggregate.near_duplicate_displacement_rate * weights.near_duplicate_displacement_rate
    )
    return _round_score(value)


def build_selection_variant(
    *,
    index: BM25Index | DenseIndex,
    cases: tuple[RetrievalEvaluationCase, ...],
    retriever_config_id: str,
    retriever_config_sha256: str,
    chunking_config_id: str,
    top_k: int,
    metadata_policy: MetadataPolicy,
    policy: RetrievalSelectionPolicy,
) -> RetrievalSelectionVariant:
    """Build one deterministic candidate selection variant."""

    results = evaluate_variant_cases(index, cases, top_k, metadata_policy)
    aggregate = aggregate_metrics(results)
    weighted_pass, weighted_failure, failed_case_ids = weighted_case_rates(results, cases, policy)
    gates = promotion_gate_results(aggregate, weighted_pass, policy)
    positive_score = benefit_score(aggregate, weighted_pass, policy)
    negative_score = penalty_score(aggregate, policy)
    top_k_penalty = _round_score(
        max(0, top_k - policy.minimum_top_k) * policy.top_k_penalty_per_extra_hit
    )
    final_score = _round_score(100.0 * max(0.0, positive_score - negative_score - top_k_penalty))
    variant_id = f"{retriever_config_id}--top-{top_k}--{metadata_policy.value}"
    return RetrievalSelectionVariant(
        variant_id=variant_id,
        retriever_config_id=retriever_config_id,
        retriever_config_sha256=retriever_config_sha256,
        chunking_config_id=chunking_config_id,
        top_k=top_k,
        metadata_policy=metadata_policy,
        eligible_for_recommendation=metadata_policy is policy.eligible_metadata_policy,
        aggregate=aggregate,
        weighted_case_pass_rate=weighted_pass,
        weighted_case_failure_rate=weighted_failure,
        failed_case_ids=failed_case_ids,
        gate_results=gates,
        hard_gate_passed=all(gate.passed for gate in gates),
        benefit_score=positive_score,
        penalty_score=negative_score,
        top_k_penalty=top_k_penalty,
        final_score=final_score,
    )


def rank_eligible_variants(
    variants: Iterable[RetrievalSelectionVariant],
) -> tuple[RetrievalSelectionVariant, ...]:
    """Rank authored-policy variants conservatively and deterministically."""

    eligible = tuple(variant for variant in variants if variant.eligible_for_recommendation)
    return tuple(
        sorted(
            eligible,
            key=lambda variant: (
                not variant.hard_gate_passed,
                -variant.final_score,
                variant.top_k,
                variant.retriever_config_id,
            ),
        )
    )
