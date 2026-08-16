from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1,
)

design = b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1


@pytest.fixture
def candidate_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    for relative in (
        design.DISPOSITION_RECORD_PATH,
        design.DISPOSITION_REVIEW_PATH,
        design.RUNTIME_PATH,
        design.PREDECESSOR_DESIGN_PATH,
        design.FEASIBILITY_PATH,
        design.SEMANTIC_REVIEW_PATH,
        design.FREEZE_CANDIDATE_PATH,
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)

    monkeypatch.setattr(
        design,
        "_base_commit_is_ancestor_of_head",
        lambda root: True,
    )
    return tmp_path


def test_descendant_lineage_and_authorities_are_accepted(
    candidate_repo: Path,
) -> None:
    authorities = design.validate_authorities(candidate_repo)

    assert len(authorities) == 7


def test_unrelated_lineage_fails_closed(
    candidate_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        design,
        "_base_commit_is_ancestor_of_head",
        lambda root: False,
    )

    with pytest.raises(design.DesignError) as captured:
        design.validate_authorities(candidate_repo)

    assert captured.value.error_code == ("B_VS_D_MARKER_DIVERSIFIED_DESIGN_BASE_MAIN_DRIFT")


def test_exact_b_and_d_token_and_payload_identities_are_bound(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)
    b, d = record.conditions

    assert b.prompt_token_count == 899
    assert d.prompt_token_count == 899
    assert b.prompt_token_sha256 == design.B_TOKEN_SHA256
    assert d.prompt_token_sha256 == design.D_TOKEN_SHA256
    assert b.request_payload_sha256 == design.B_PAYLOAD_SHA256
    assert d.request_payload_sha256 == design.D_PAYLOAD_SHA256


def test_complete_cumulative_token_profile_is_frozen(
    candidate_repo: Path,
) -> None:
    b, d = design.build_design_record(candidate_repo).conditions

    assert b.cumulative_prompt_token_count_profile == design.TOKEN_PROFILE
    assert d.cumulative_prompt_token_count_profile == design.TOKEN_PROFILE
    assert b.cumulative_prompt_token_increments == (34,) * 24
    assert d.cumulative_prompt_token_increments == (34,) * 24
    assert design.TOKEN_PROFILE[0] == 83
    assert design.TOKEN_PROFILE[-1] == 899


def test_marker_only_textual_intervention_is_frozen(
    candidate_repo: Path,
) -> None:
    b, d = design.build_design_record(candidate_repo).conditions

    assert b.unique_segment_count == 1
    assert d.unique_segment_count == 24
    assert b.marker_sequence == ("meadow",) * 24
    assert d.marker_sequence == design.D_MARKERS
    assert len(set(d.segments)) == 24
    assert all(
        segment == design.SEGMENT_TEMPLATE.format(marker=marker)
        for segment, marker in zip(
            d.segments,
            design.D_MARKERS,
            strict=True,
        )
    )


def test_representation_gradient_and_boundary_are_frozen(
    candidate_repo: Path,
) -> None:
    comparator = design.build_design_record(candidate_repo).comparator_contract

    assert (
        comparator.d_metrics.duplicate_16gram_fraction
        < comparator.b_metrics.duplicate_16gram_fraction
    )
    assert (
        comparator.d_metrics.shift_34_match_fraction < comparator.b_metrics.shift_34_match_fraction
    )
    assert (
        comparator.d_metrics.duplicate_aligned_16_token_blocks_beyond_first
        < comparator.b_metrics.duplicate_aligned_16_token_blocks_beyond_first
    )
    assert (
        comparator.d_metrics.prompt_unique_token_ids > comparator.b_metrics.prompt_unique_token_ids
    )
    assert comparator.text_segment_boundary_must_equal_token_boundary is False


def test_human_review_and_user_acceptance_are_bound(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)
    review = record.comparator_contract.human_review

    assert review.neutrality == "PASS"
    assert review.naturalness == "PASS"
    assert review.semantic_comparability_to_b == "PASS"
    assert review.marker_only_textual_change == "PASS"
    assert review.instruction_like_semantics_absent == "PASS"
    assert review.forbidden_terms_absent == "PASS"
    assert review.cumulative_prompt_token_profile_equal_to_b == "PASS"
    assert review.text_boundary_token_boundary_assumption == "NOT_USED"
    assert review.structural_isolation == ("PASS_WITH_BOUNDED_MARKER_LEXICAL_AND_SEMANTIC_NOVELTY")


def test_request_plan_and_budget_are_frozen(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(item.condition_id.value for item in record.request_plan) == design.ORDER
    assert record.execution_budget.maximum_model_requests == 6
    assert record.execution_budget.maximum_model_loads == 6
    assert record.execution_budget.maximum_worker_starts == 6
    assert record.execution_budget.hidden_retries_permitted == 0
    assert record.execution_budget.replacement_observations_permitted == 0


def test_b_anchor_validity_rule_precedes_d_inference(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    rule = next(
        item
        for item in record.decision_rules
        if item.state == design.DecisionState.B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE
    )

    assert "Condition B is not 0/3" in rule.condition
    assert "D is not used" in rule.implication


def test_interpretation_contract_is_complete(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(rule.state for rule in record.decision_rules) == tuple(design.DecisionState)
    assert len(record.decision_rules) == 5


def test_runtime_generation_and_starting_state_are_preserved(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.runtime.backend == "TRITON_ATTN"
    assert record.runtime.vllm_distribution == "0.25.1+cu129"
    assert record.runtime.transformers == "5.14.1"
    assert record.runtime.prefix_caching_enabled is True
    assert record.runtime.cache_block_size == 16
    assert record.runtime.max_model_len == 4096

    assert record.generation_controls.temperature == 0
    assert record.generation_controls.top_p == 1
    assert record.generation_controls.repetition_penalty == 1.1
    assert record.generation_controls.seed == 7
    assert record.generation_controls.max_tokens == 32

    assert record.starting_state.strategy == ("FRESH_WORKER_PROCESS_PER_OBSERVATION")
    assert record.starting_state.prior_request_cache_carryover_permitted is False
    assert record.starting_state.require_zero_cached_prefix_baseline is True


def test_design_is_execution_inert(candidate_repo: Path) -> None:
    safety = design.build_design_record(candidate_repo).safety

    assert safety.runtime_execution_authorized is False
    assert safety.new_execution_authorized is False
    assert safety.kaggle_execution_performed is False
    assert safety.gpu_execution_performed is False
    assert safety.model_loaded is False
    assert safety.worker_started is False
    assert safety.model_requests_performed == 0
    assert safety.execution_authorization_issued is False
    assert safety.threshold_search_authorized is False
    assert safety.p5_p6_requalification_authorized is False
    assert safety.measured_abc_execution_authorized is False


def test_generation_is_byte_deterministic(candidate_repo: Path) -> None:
    generated = design.generate(candidate_repo)
    first = (candidate_repo / design.RECORD_PATH).read_bytes()

    validated = design.validate_generated(candidate_repo)
    second = (candidate_repo / design.RECORD_PATH).read_bytes()

    assert generated == validated
    assert first == second

    parsed = json.loads(first)
    assert parsed["design_status"] == "DESIGN_FROZEN_NOT_EXECUTED"
    assert len(parsed["conditions"]) == 2
    assert len(parsed["request_plan"]) == 6
    assert parsed["execution_budget"]["maximum_model_requests"] == 6
    assert parsed["safety"]["new_execution_authorized"] is False


def test_authority_drift_fails_closed(candidate_repo: Path) -> None:
    path = candidate_repo / design.FEASIBILITY_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(design.DesignError) as captured:
        design.validate_authorities(candidate_repo)

    assert captured.value.error_code == ("B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_DRIFT")


def test_generated_record_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    design.generate(candidate_repo)
    path = candidate_repo / design.RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["design_status"] = "TAMPERED"
    path.write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(design.DesignError) as captured:
        design.validate_generated(candidate_repo)

    assert captured.value.error_code == ("B_VS_D_MARKER_DIVERSIFIED_DESIGN_RECORD_DRIFT")
