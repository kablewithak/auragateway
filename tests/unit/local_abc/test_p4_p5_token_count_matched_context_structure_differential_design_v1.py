from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import p4_p5_token_count_matched_context_structure_differential_design_v1

design = p4_p5_token_count_matched_context_structure_differential_design_v1


@pytest.fixture
def candidate_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    for relative in (
        design.DISPOSITION_RECORD_PATH,
        design.DISPOSITION_REVIEW_PATH,
        design.RUNTIME_PATH,
        design.TOKENIZER_RECEIPT_PATH,
        design.COMPARATOR_FEASIBILITY_PATH,
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


def test_descendant_lineage_is_accepted(candidate_repo: Path) -> None:
    authorities = design.validate_authorities(candidate_repo)

    assert len(authorities) == 6


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

    assert captured.value.error_code == "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_BASE_MAIN_DRIFT"


def test_exact_condition_token_identities_are_bound(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)
    a, b, c = record.conditions

    assert a.prompt_token_count == 899
    assert b.prompt_token_count == 899
    assert c.prompt_token_count == 899

    assert a.prompt_token_sha256 == (
        "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
    )
    assert b.prompt_token_sha256 == (
        "02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"
    )
    assert c.prompt_token_sha256 == (
        "612e1ada53aba2158536cb0d0e142e3152df7e177ff951a2565385473ec698d4"
    )


def test_condition_structure_is_frozen(candidate_repo: Path) -> None:
    a, b, c = design.build_design_record(candidate_repo).conditions

    assert a.segment_count == 24
    assert b.segment_count == 24
    assert c.segment_count == 24

    assert a.unique_segment_count == 1
    assert b.unique_segment_count == 1
    assert c.unique_segment_count == 24

    assert a.instruction_like_repetition_present is True
    assert b.instruction_like_repetition_present is False
    assert c.instruction_like_repetition_present is False


def test_comparator_separation_and_human_review_are_bound(candidate_repo: Path) -> None:
    comparator = design.build_design_record(candidate_repo).comparator_contract

    assert comparator.human_review.neutrality == "PASS"
    assert comparator.human_review.naturalness == "PASS"
    assert comparator.human_review.semantic_comparability == "PASS"
    assert comparator.human_review.structural_isolation == "PASS_WITH_BOUNDED_LEXICAL_NOVELTY"

    assert comparator.c_duplicate_8gram_fraction < comparator.b_duplicate_8gram_fraction
    assert comparator.c_duplicate_16gram_fraction <= comparator.b_duplicate_16gram_fraction * 0.5


def test_request_plan_is_position_balanced(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(item.condition_id.value for item in record.request_plan) == design.ORDER

    for condition_id in design.ConditionId:
        positions = tuple(
            item.ordinal for item in record.request_plan if item.condition_id == condition_id
        )
        assert len(positions) == 3
        assert sum(positions) == 15


def test_runtime_and_generation_controls_are_frozen(candidate_repo: Path) -> None:
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
    assert record.generation_controls.response_format_present is False


def test_primary_endpoint_and_budget_are_frozen(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.primary_endpoint.field == "exact_object"
    assert record.primary_endpoint.per_condition_observations == 3
    assert record.primary_endpoint.condition_pass == "3_OF_3_EXACT_OBJECT_TRUE"
    assert record.primary_endpoint.condition_fail == "0_OF_3_EXACT_OBJECT_TRUE"
    assert record.primary_endpoint.condition_mixed == "1_OR_2_OF_3_EXACT_OBJECT_TRUE"

    assert record.execution_budget.maximum_model_requests == 9
    assert record.execution_budget.maximum_model_loads == 9
    assert record.execution_budget.maximum_worker_starts == 9
    assert record.execution_budget.hidden_retries_permitted == 0
    assert record.execution_budget.replacement_observations_permitted == 0


def test_interpretation_contract_is_complete(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(rule.state for rule in record.decision_rules) == tuple(design.DecisionState)
    assert len(record.decision_rules) == 7


def test_anchor_validity_rule_precedes_mechanistic_inference(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    anchor_rule = next(
        rule
        for rule in record.decision_rules
        if rule.state
        == design.DecisionState.ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE
    )

    assert "Condition A is not 0/3" in anchor_rule.condition
    assert "B and C are not used" in anchor_rule.implication


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
    assert parsed["frozen_composition"]["prompt_token_count_per_condition"] == 899
    assert len(parsed["request_plan"]) == 9


def test_authority_drift_fails_closed(candidate_repo: Path) -> None:
    path = candidate_repo / design.RUNTIME_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(design.DesignError) as captured:
        design.validate_authorities(candidate_repo)

    assert captured.value.error_code == "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_AUTHORITY_DRIFT"


def test_generated_record_drift_fails_closed(candidate_repo: Path) -> None:
    design.generate(candidate_repo)
    path = candidate_repo / design.RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["design_status"] = "TAMPERED"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(design.DesignError) as captured:
        design.validate_generated(candidate_repo)

    assert captured.value.error_code == "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_RECORD_DRIFT"
