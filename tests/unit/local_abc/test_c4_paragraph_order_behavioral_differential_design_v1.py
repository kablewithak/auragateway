from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    c4_paragraph_order_behavioral_differential_design_v1,
)

design = c4_paragraph_order_behavioral_differential_design_v1


@pytest.fixture
def candidate_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    source_root = Path(__file__).resolve().parents[3]

    for _, relative, _ in design.AUTHORITY_SPECS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)

    monkeypatch.setattr(
        design,
        "_base_commit_is_ancestor_of_head",
        lambda root: True,
    )

    return tmp_path


def test_governed_c4_authorities_are_accepted(
    candidate_repo: Path,
) -> None:
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

    assert captured.value.error_code == ("C4_PARAGRAPH_ORDER_DESIGN_BASE_MAIN_DRIFT")


def test_static_isolation_contract_is_frozen(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)
    evidence = record.static_isolation_evidence
    control, treatment = record.conditions

    assert control.prompt_token_count == 899
    assert treatment.prompt_token_count == 899
    assert control.prompt_token_sha256 == design.CONTROL_TOKEN_SHA256
    assert treatment.prompt_token_sha256 == design.TREATMENT_TOKEN_SHA256

    assert evidence.token_id_multiset_identical is True
    assert evidence.prompt_token_count_equal is True
    assert evidence.final_user_boundary_equal is True
    assert evidence.message_boundary_profile_equal is True
    assert evidence.common_suffix_token_count == 122

    assert control.final_user_boundary == 880
    assert treatment.final_user_boundary == 880
    assert control.message_boundary_profile == (3, 28, 869, 880)
    assert treatment.message_boundary_profile == (3, 28, 869, 880)


def test_exact_paragraph_order_intervention_is_frozen(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)
    control, treatment = record.conditions
    evidence = record.static_isolation_evidence

    assert control.paragraph_order == tuple(range(1, 11))
    assert treatment.paragraph_order == (1, 9, 8, 7, 6, 5, 4, 3, 2, 10)

    assert evidence.first_paragraph_preserved is True
    assert evidence.last_paragraph_preserved is True
    assert evidence.paragraph_content_multiset_preserved is True
    assert evidence.character_count_preserved is True
    assert evidence.producer_reexecutes_tokenizer is False


def test_historical_control_failure_anchor_is_bound(
    candidate_repo: Path,
) -> None:
    control, treatment = design.build_design_record(candidate_repo).conditions

    assert control.historical_exact_object_result == "0_OF_3"
    assert control.historical_canonical_parsed_object_sha256 == (
        design.HISTORICAL_CONTROL_PARSED_OBJECT_SHA256
    )

    assert treatment.historical_exact_object_result == "NOT_EXECUTED"
    assert treatment.historical_canonical_parsed_object_sha256 is None


def test_request_plan_and_budget_are_frozen(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert (
        tuple(item.condition_id.value for item in record.request_plan) == design.OBSERVATION_ORDER
    )

    assert record.execution_budget.maximum_model_requests == 6
    assert record.execution_budget.maximum_model_loads == 6
    assert record.execution_budget.maximum_worker_starts == 6
    assert record.execution_budget.maximum_worker_teardowns == 6
    assert record.execution_budget.hidden_retries_permitted == 0
    assert record.execution_budget.replacement_observations_permitted == 0


def test_control_anchor_rule_precedes_treatment_inference(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    first_rule = record.decision_rules[0]

    assert first_rule.state == (
        design.DecisionState.CONTROL_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE
    )
    assert "treatment is not used" in first_rule.implication


def test_interpretation_contract_is_complete(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(rule.state for rule in record.decision_rules) == tuple(design.DecisionState)

    assert len(record.decision_rules) == 6


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


def test_design_is_execution_inert(
    candidate_repo: Path,
) -> None:
    safety = design.build_design_record(candidate_repo).safety

    assert safety.runtime_execution_authorized is False
    assert safety.new_execution_authorized is False
    assert safety.execution_authorization_issued is False
    assert safety.kaggle_execution_performed is False
    assert safety.gpu_execution_performed is False
    assert safety.model_loaded is False
    assert safety.worker_started is False
    assert safety.model_requests_performed == 0
    assert safety.p5_p6_requalification_authorized is False
    assert safety.measured_abc_execution_authorized is False


def test_generation_is_byte_deterministic(
    candidate_repo: Path,
) -> None:
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


def test_authority_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    path = candidate_repo / design.C4_DISPOSITION_RECORD_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(design.DesignError) as captured:
        design.validate_authorities(candidate_repo)

    assert captured.value.error_code == ("C4_PARAGRAPH_ORDER_DESIGN_AUTHORITY_DRIFT")


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

    assert captured.value.error_code == ("C4_PARAGRAPH_ORDER_DESIGN_RECORD_DRIFT")
