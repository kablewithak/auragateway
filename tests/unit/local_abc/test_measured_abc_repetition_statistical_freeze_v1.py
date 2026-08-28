from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from auragateway.local_abc import measured_abc_repetition_statistical_freeze_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def test_g10_binds_accepted_v2_pilot_without_authorizing_execution() -> None:
    freeze = subject.build_freeze(ROOT)
    assert freeze.source_pilot_saved_version_id == 345461230
    assert freeze.repetition_freeze_established is True
    assert freeze.statistical_freeze_established is True
    assert freeze.execution_manifest_frozen is False
    assert freeze.final_measured_abc_execution_authorized is False
    assert freeze.new_execution_authorized is False
    assert freeze.effect_claims_permitted is False


def test_final_repetition_counts_match_existing_342_run_ledger() -> None:
    freeze = subject.build_freeze(ROOT)
    functional, runtime = freeze.suites
    assert functional.episode_count == 18
    assert functional.repetitions_per_condition == 3
    assert functional.scheduled_trajectory_count == 162
    assert functional.scheduled_turn_count == 648
    assert runtime.episode_count == 6
    assert runtime.repetitions_per_condition == 10
    assert runtime.scheduled_trajectory_count == 180
    assert runtime.scheduled_turn_count == 720
    assert freeze.total_scheduled_trajectory_count == 342
    assert freeze.total_scheduled_turn_count == 1368


def test_counterbalance_orders_are_exact() -> None:
    freeze = subject.build_freeze(ROOT)
    functional, runtime = freeze.suites
    assert functional.condition_orders == ("ABC", "BCA", "CAB")
    assert runtime.condition_orders == (
        "ABC",
        "BCA",
        "CAB",
        "ACB",
        "CBA",
        "BAC",
        "ABC",
        "BCA",
        "CAB",
        "CBA",
    )


def test_primary_runtime_endpoint_is_frozen_but_requires_runner_requalification() -> None:
    endpoint = subject.build_freeze(ROOT).primary_runtime_endpoint
    assert endpoint.metric_id == "warm-eligible-newly-computed-prefill-tokens-v1"
    assert endpoint.telemetry_field == "newly_computed_prefill_tokens"
    assert endpoint.warm_eligible_turn_indices == (2, 3, 4)
    assert endpoint.direction == "lower_is_better"
    assert endpoint.primary_point_estimator == "median_paired_difference"
    assert endpoint.final_runner_emission_requalification_required is True


def test_statistical_contract_matches_frozen_constitution() -> None:
    stats = subject.build_freeze(ROOT).statistics
    assert stats.configuration_id == "paired-bootstrap-v1"
    assert stats.method == "percentile_bootstrap"
    assert stats.resampling_unit == "comparison_pair_at_episode_level"
    assert stats.bootstrap_samples == 10000
    assert stats.confidence_level == Decimal("0.95")
    assert stats.random_seed == 20260712
    assert stats.runtime_improvement_direction_requires_point_estimate_below_zero is True
    assert stats.runtime_improvement_direction_requires_ci_upper_bound_below_zero is True
    assert stats.academic_statistical_significance_claim_permitted is False
    assert stats.universal_generalization_claim_permitted is False


def test_quality_noninferiority_contract_is_exact() -> None:
    quality = subject.build_freeze(ROOT).quality_non_inferiority
    assert quality.policy_id == "quality-non-inferiority-v1"
    assert quality.max_task_success_regression_percentage_points == Decimal("5")
    assert quality.minimum_structured_output_validity == Decimal("0.95")
    assert quality.citation_support_regression_permitted is False
    assert quality.unsupported_answer_rate_increase_permitted is False
    assert quality.retrieval_configuration_change_permitted is False
    assert quality.unsafe_behavior_regression_permitted is False
    assert quality.comparison_eligibility_required is True
    assert quality.independent_double_review_fraction == Decimal("0.25")
    assert quality.double_review_seed == 20260712


def test_warm_reset_contract_separates_cold_and_warm_views() -> None:
    warm = subject.build_freeze(ROOT).warm_reset
    assert warm.first_turn_classification == "cold"
    assert warm.synthetic_pre_warm_requests_permitted is False
    assert warm.primary_runtime_endpoint_uses_warm_eligible_turns_only is True
    assert warm.distinct_cache_namespace_per_condition_pair_replication is True
    assert warm.cross_condition_namespace_reuse_permitted is False
    assert warm.namespace_identity_is_reset_boundary is True
    assert warm.cold_and_warm_results_reported_separately is True


def test_existing_planned_run_ledger_satisfies_g10_schedule() -> None:
    subject._validate_planned_ledger(ROOT)


def test_generated_outputs_validate_without_opening_execution_authority() -> None:
    result = subject.validate(ROOT)
    assert result["status"] == "MEASURED_ABC_REPETITION_STATISTICAL_FREEZE_V1_VALID"
    assert result["pilot_repository_acceptance_established"] is True
    assert result["repetition_freeze_established"] is True
    assert result["statistical_freeze_established"] is True
    assert result["execution_manifest_frozen"] is False
    assert result["final_runner_requalification_required"] is True
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["new_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
