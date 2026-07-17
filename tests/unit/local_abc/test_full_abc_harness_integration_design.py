from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.contracts import ConditionId, PrefixPolicy
from auragateway.local_abc.full_abc_harness_integration_design import (
    FullABCBenchmarkSuiteId,
    FullABCCausalContrastId,
    FullABCClaimFamily,
    FullABCHarnessIntegrationDesign,
    FullABCRoutePolicy,
    FullABCTelemetryEvidenceLevel,
    load_full_abc_harness_integration_design,
)

ROOT = Path(__file__).resolve().parents[3]
DESIGN_PATH = (
    ROOT / "benchmarks" / "local_abc" / "auragateway_full_abc_harness_integration_design_v1.json"
)
ADR_PATH = ROOT / "docs" / "adr" / "2026-07-18-local-abc-full-abc-harness-integration-design.md"
DOC_PATH = (
    ROOT / "docs" / "benchmarks" / "local_abc_auragateway_full_abc_harness_integration_design_v1.md"
)
EXPECTED_DESIGN_SHA256 = "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"


def _load_design() -> FullABCHarnessIntegrationDesign:
    return load_full_abc_harness_integration_design(DESIGN_PATH)


def _payload() -> dict[str, object]:
    value = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_design_artifact_has_frozen_identity() -> None:
    design = _load_design()
    assert design.fingerprint() == EXPECTED_DESIGN_SHA256


def test_design_binds_pr_93_and_hardening_assets() -> None:
    design = _load_design()
    assert design.source_merge_commit == "b995794e1e1f312c23f39a685b3c118253707700"
    assert design.benchmark_constitution_blob_sha == "dc25906298a611b71f3482da85c6aba763c474e7"
    assert design.hardening_source_blob_sha == "d991beb28a70e90a2de6fb805dba53ca5cf16d33"
    assert design.hardening_plan_blob_sha == "449007bd4d0fe55596aee24c313b4ec6b1677ceb"
    assert design.hardening_plan_sha256 == (
        "aa6a02dee2ceb039e61d13048075a3a0081777538b2c08277d4a381f2b5a47e3"
    )


def test_conditions_preserve_frozen_a_b_c_order() -> None:
    design = _load_design()
    assert tuple(condition.condition_id for condition in design.conditions) == (
        ConditionId.A,
        ConditionId.B,
        ConditionId.C,
    )


def test_condition_a_is_cache_hostile_and_turn_local() -> None:
    condition = _load_design().conditions[0]
    assert condition.prefix_policy is PrefixPolicy.CACHE_HOSTILE
    assert condition.route_policy is FullABCRoutePolicy.TURN_LOCAL
    assert condition.static_volatile_boundary_enforced is False


def test_condition_b_changes_context_only() -> None:
    condition = _load_design().conditions[1]
    assert condition.prefix_policy is PrefixPolicy.DETERMINISTIC_EXACT
    assert condition.route_policy is FullABCRoutePolicy.TURN_LOCAL
    assert condition.static_volatile_boundary_enforced is True


def test_condition_c_adds_cache_affinity_routing() -> None:
    condition = _load_design().conditions[2]
    assert condition.prefix_policy is PrefixPolicy.DETERMINISTIC_EXACT
    assert condition.route_policy is FullABCRoutePolicy.CACHE_AFFINITY_TTL
    assert condition.static_volatile_boundary_enforced is True


def test_all_conditions_share_hardened_scoring_and_cleanup() -> None:
    design = _load_design()
    assert len({condition.score_entrypoint for condition in design.conditions}) == 1
    assert len({condition.cleanup_entrypoint for condition in design.conditions}) == 1
    assert all(
        condition.explicit_executed_prompt_identity_required for condition in design.conditions
    )
    assert all(condition.evidence_derived_cleanup_required for condition in design.conditions)


def test_all_conditions_share_prompt_and_schema_quality_boundaries() -> None:
    design = _load_design()
    assert len({condition.prompt_policy_sha256 for condition in design.conditions}) == 1
    assert len({condition.response_schema_sha256 for condition in design.conditions}) == 1
    assert len({condition.action_schema_sha256 for condition in design.conditions}) == 1
    assert all(condition.retrieval_configuration_held_constant for condition in design.conditions)
    assert all(condition.output_schema_held_constant for condition in design.conditions)
    assert all(condition.quality_rubric_held_constant for condition in design.conditions)


def test_causal_contrasts_preserve_attribution_boundaries() -> None:
    contrasts = _load_design().contrasts
    assert tuple(contrast.contrast_id for contrast in contrasts) == tuple(FullABCCausalContrastId)
    assert tuple(contrast.permitted_claim_family for contrast in contrasts) == (
        FullABCClaimFamily.CONTEXT_CONSTRUCTION_POLICY,
        FullABCClaimFamily.ROUTE_POLICY,
        FullABCClaimFamily.TOTAL_SYSTEM,
    )


def test_functional_suite_preserves_162_trajectory_design() -> None:
    suite = _load_design().suites[0]
    assert suite.suite_id is FullABCBenchmarkSuiteId.FUNCTIONAL
    assert suite.episode_count == 18
    assert suite.turns_per_episode == 4
    assert suite.repetitions_per_condition == 3
    assert suite.scheduled_trajectory_count == 162
    assert suite.schedule_id == "functional-counterbalance-v1"


def test_runtime_suite_preserves_180_trajectory_design() -> None:
    suite = _load_design().suites[1]
    assert suite.suite_id is FullABCBenchmarkSuiteId.RUNTIME_MICROBENCHMARK
    assert suite.episode_count == 6
    assert suite.turns_per_episode == 4
    assert suite.repetitions_per_condition == 10
    assert suite.scheduled_trajectory_count == 180
    assert suite.schedule_id == "runtime-counterbalance-v1"


def test_quality_gate_blocks_speed_or_cost_wins_with_quality_regression() -> None:
    gate = _load_design().quality_gate
    assert str(gate.max_task_success_regression_percentage_points) == "5"
    assert str(gate.minimum_structured_output_validity) == "0.95"
    assert gate.citation_support_regression_permitted is False
    assert gate.unsupported_answer_rate_increase_permitted is False
    assert gate.comparison_eligibility_required is True


def test_telemetry_gate_keeps_unknown_values_unknown() -> None:
    gate = _load_design().telemetry_claim_gate
    assert gate.permitted_evidence_levels == tuple(FullABCTelemetryEvidenceLevel)
    assert gate.unknown_values_remain_unknown is True
    assert gate.missing_cache_value_coerced_to_zero is False
    assert gate.warm_eligibility_proves_provider_cache_hit is False
    assert gate.provider_cache_claim_requires_observed_provider_evidence is True


def test_trace_contract_includes_score_and_cleanup_hardening_fields() -> None:
    fields = _load_design().trace_fields
    assert "score_prompt_policy_sha256" in fields
    assert "score_rendered_prompt_sha256" in fields
    assert "cleanup_status" in fields
    assert "cleanup_warning_codes" in fields


def test_privacy_boundary_excludes_raw_sensitive_evidence() -> None:
    exclusions = _load_design().public_evidence_exclusions
    assert "raw_prompts" in exclusions
    assert "raw_retrieved_document_text" in exclusions
    assert "raw_model_outputs" in exclusions
    assert "raw_provider_payloads" in exclusions
    assert "credentials" in exclusions
    assert "direct_personal_identifiers" in exclusions


def test_design_creates_no_execution_authority() -> None:
    design = _load_design()
    assert design.execution_manifest_frozen is False
    assert design.measured_execution_authorized is False
    assert design.gpu_execution_authorized is False
    assert design.provider_execution_authorized is False
    assert design.new_authorization_issued is False
    assert design.consumed_authorization_reused is False
    assert design.full_abc_results_claimed is False
    assert design.next_gate == "full_abc_harness_integration_implementation"


def test_condition_a_cannot_be_relabelled_deterministic() -> None:
    payload = _payload()
    conditions = payload["conditions"]
    assert isinstance(conditions, list)
    conditions[0]["prefix_policy"] = "deterministic_exact"
    with pytest.raises(ValidationError, match="prefix policy"):
        FullABCHarnessIntegrationDesign.model_validate(payload)


def test_condition_b_cannot_gain_cache_affinity() -> None:
    payload = _payload()
    conditions = payload["conditions"]
    assert isinstance(conditions, list)
    conditions[1]["route_policy"] = "cache_affinity_ttl"
    with pytest.raises(ValidationError, match="route policy"):
        FullABCHarnessIntegrationDesign.model_validate(payload)


def test_condition_c_cannot_revert_to_turn_local_routing() -> None:
    payload = _payload()
    conditions = payload["conditions"]
    assert isinstance(conditions, list)
    conditions[2]["route_policy"] = "turn_local"
    with pytest.raises(ValidationError, match="route policy"):
        FullABCHarnessIntegrationDesign.model_validate(payload)


def test_contrast_cannot_overclaim_wrong_mechanism() -> None:
    payload = _payload()
    contrasts = payload["contrasts"]
    assert isinstance(contrasts, list)
    contrasts[0]["permitted_claim_family"] = "route_policy"
    with pytest.raises(ValidationError, match="claim family"):
        FullABCHarnessIntegrationDesign.model_validate(payload)


def test_suite_trajectory_count_cannot_drift() -> None:
    payload = _payload()
    suites = payload["suites"]
    assert isinstance(suites, list)
    suites[1]["scheduled_trajectory_count"] = 179
    with pytest.raises(ValidationError, match="trajectory count"):
        FullABCHarnessIntegrationDesign.model_validate(payload)


def test_trace_contract_cannot_drop_cleanup_warnings() -> None:
    payload = _payload()
    trace_fields = payload["trace_fields"]
    assert isinstance(trace_fields, list)
    trace_fields.remove("cleanup_warning_codes")
    with pytest.raises(ValidationError, match="trace fields"):
        FullABCHarnessIntegrationDesign.model_validate(payload)


def test_design_artifact_is_canonical_single_line_json() -> None:
    design = _load_design()
    text = DESIGN_PATH.read_text(encoding="utf-8")
    assert "\n" not in text
    assert text == design.canonical_json()


def test_docs_preserve_execution_block_and_next_gate() -> None:
    for path in (ADR_PATH, DOC_PATH):
        text = path.read_text(encoding="utf-8")
        assert "measured_execution_authorized=false" in text
        assert "provider_execution_authorized=false" in text
        assert "full_abc_harness_integration_implementation" in text
        assert "No model request" in text
