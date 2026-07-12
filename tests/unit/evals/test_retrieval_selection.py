from __future__ import annotations

from pathlib import Path

from auragateway.contracts.retrieval import RetrievalFilter, StalePolicy
from auragateway.contracts.retrieval_selection import (
    MetadataPolicy,
    RetrievalSelectionPolicy,
)
from auragateway.evals.runner import load_development_assets, load_index_context
from auragateway.evals.selection import (
    apply_metadata_policy,
    build_selection_variant,
    rank_eligible_variants,
)
from auragateway.retrieval.runner import FIXED_WINDOW_BM25_CONFIG

REPO_ROOT = Path(".")


def test_metadata_policy_negative_controls_remove_declared_fields() -> None:
    development_set, _, _ = load_development_assets(REPO_ROOT)
    case = development_set.cases[0]

    authored = apply_metadata_policy(case, MetadataPolicy.AUTHORED)
    api_area_only = apply_metadata_policy(case, MetadataPolicy.API_AREA_ONLY)
    no_metadata = apply_metadata_policy(case, MetadataPolicy.NONE)

    assert authored == case.filters
    assert api_area_only.api_areas == case.filters.api_areas
    assert api_area_only.stale_policy is StalePolicy.INCLUDE
    assert no_metadata == RetrievalFilter()


def test_authored_variant_is_recommendation_eligible() -> None:
    development_set, _, _ = load_development_assets(REPO_ROOT)
    context = load_index_context(REPO_ROOT, FIXED_WINDOW_BM25_CONFIG.config_id)
    variant = build_selection_variant(
        index=context.index,
        cases=development_set.cases,
        retriever_config_id=context.config_id,
        retriever_config_sha256=context.config_sha256,
        chunking_config_id=context.chunking_config_id,
        top_k=5,
        metadata_policy=MetadataPolicy.AUTHORED,
        policy=RetrievalSelectionPolicy(),
    )

    assert variant.eligible_for_recommendation
    assert variant.aggregate.case_count == 24
    assert variant.final_score > 0.0


def test_negative_control_variant_is_not_recommendation_eligible() -> None:
    development_set, _, _ = load_development_assets(REPO_ROOT)
    context = load_index_context(REPO_ROOT, FIXED_WINDOW_BM25_CONFIG.config_id)
    variant = build_selection_variant(
        index=context.index,
        cases=development_set.cases,
        retriever_config_id=context.config_id,
        retriever_config_sha256=context.config_sha256,
        chunking_config_id=context.chunking_config_id,
        top_k=5,
        metadata_policy=MetadataPolicy.NONE,
        policy=RetrievalSelectionPolicy(),
    )

    assert not variant.eligible_for_recommendation


def test_ranking_prioritizes_hard_gate_pass_before_score() -> None:
    development_set, _, _ = load_development_assets(REPO_ROOT)
    context = load_index_context(REPO_ROOT, FIXED_WINDOW_BM25_CONFIG.config_id)
    policy = RetrievalSelectionPolicy()
    top_three = build_selection_variant(
        index=context.index,
        cases=development_set.cases,
        retriever_config_id=context.config_id,
        retriever_config_sha256=context.config_sha256,
        chunking_config_id=context.chunking_config_id,
        top_k=3,
        metadata_policy=MetadataPolicy.AUTHORED,
        policy=policy,
    )
    top_five = build_selection_variant(
        index=context.index,
        cases=development_set.cases,
        retriever_config_id=context.config_id,
        retriever_config_sha256=context.config_sha256,
        chunking_config_id=context.chunking_config_id,
        top_k=5,
        metadata_policy=MetadataPolicy.AUTHORED,
        policy=policy,
    )

    ranked = rank_eligible_variants((top_three, top_five))

    assert ranked[0].hard_gate_passed or not ranked[1].hard_gate_passed


def test_authored_filters_outperform_api_area_only_negative_control() -> None:
    development_set, _, _ = load_development_assets(REPO_ROOT)
    context = load_index_context(REPO_ROOT, FIXED_WINDOW_BM25_CONFIG.config_id)
    policy = RetrievalSelectionPolicy()
    authored = build_selection_variant(
        index=context.index,
        cases=development_set.cases,
        retriever_config_id=context.config_id,
        retriever_config_sha256=context.config_sha256,
        chunking_config_id=context.chunking_config_id,
        top_k=5,
        metadata_policy=MetadataPolicy.AUTHORED,
        policy=policy,
    )
    api_area_only = build_selection_variant(
        index=context.index,
        cases=development_set.cases,
        retriever_config_id=context.config_id,
        retriever_config_sha256=context.config_sha256,
        chunking_config_id=context.chunking_config_id,
        top_k=5,
        metadata_policy=MetadataPolicy.API_AREA_ONLY,
        policy=policy,
    )

    assert authored.aggregate.citation_support_readiness_rate > (
        api_area_only.aggregate.citation_support_readiness_rate
    )
    assert authored.aggregate.stale_source_retrieval_rate < (
        api_area_only.aggregate.stale_source_retrieval_rate
    )
