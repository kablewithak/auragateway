from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import p4_p5_composition_differential_design_v1

design = p4_p5_composition_differential_design_v1


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]

    paths = (
        design.P4_ACCEPTANCE_PATH,
        design.P4_IMPLEMENTATION_RECORD_PATH,
        design.P4_REQUEST_PATH,
        design.P4_TEMPLATE_PATH,
        design.P5_RUNTIME_PATH,
        design.C3_RECONCILIATION_PATH,
    )

    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)

    return tmp_path


def test_authority_scopes_are_explicit(
    candidate_repo: Path,
) -> None:
    authorities = design.validate_authorities(candidate_repo)

    current = {item.role for item in authorities if item.scope == design.AuthorityScope.CURRENT}
    historical = {
        item.role
        for item in authorities
        if item.scope == design.AuthorityScope.HISTORICAL_PRECEDENT
    }

    assert current == {
        "current_p5_runtime_composition",
        "current_c3_reconciliation",
    }
    assert historical == {
        "historical_p4_execution_acceptance",
        "historical_p4_implementation_record",
        "historical_p4_case_matrix",
        "historical_p4_message_shape",
    }


def test_case_shapes_isolate_message_composition(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)
    case_a, case_b = record.cases

    assert case_a.name == "SIMPLE_CONTROL"
    assert case_a.message_roles == ("system", "user")
    assert case_a.synthetic_cache_context_present is False
    assert case_a.synthetic_assistant_ack_present is False

    assert case_b.name == "COMPOSED_P5"
    assert case_b.message_roles == (
        "system",
        "user",
        "assistant",
        "user",
    )
    assert case_b.synthetic_cache_context_present is True
    assert case_b.synthetic_assistant_ack_present is True

    assert case_a.final_object_canonical == case_b.final_object_canonical
    assert case_a.system_prompt_source == case_b.system_prompt_source
    assert case_a.variable_under_test == "MESSAGE_COMPOSITION_ONLY"
    assert case_b.variable_under_test == "MESSAGE_COMPOSITION_ONLY"


def test_generation_controls_and_runtime_are_fixed(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.generation_controls.temperature == 0
    assert record.generation_controls.top_p == 1
    assert record.generation_controls.repetition_penalty == 1.1
    assert record.generation_controls.seed == 7
    assert record.generation_controls.max_tokens == 32
    assert record.generation_controls.response_format_present is False

    assert record.runtime.vllm_distribution == "0.25.1+cu129"
    assert record.runtime.torch == "2.11.0+cu129"
    assert record.runtime.backend == "TRITON_ATTN"
    assert record.runtime.platform_topology == "T4_x2"
    assert record.runtime.worker_gpu_index == 0


def test_request_plan_is_balanced_six_request_differential(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(item.case_id.value for item in record.request_plan) == (
        "A",
        "B",
        "B",
        "A",
        "A",
        "B",
    )

    assert record.execution_budget.maximum_model_requests == 6
    assert record.execution_budget.maximum_model_loads == 1
    assert record.execution_budget.maximum_worker_starts == 1
    assert record.execution_budget.hidden_retries_permitted == 0
    assert record.execution_budget.external_network_requests_permitted == 0


def test_decision_contract_is_complete(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(rule.state for rule in record.decision_rules) == tuple(design.DecisionState)

    assert record.decision_rules[0].state == (design.DecisionState.COMPOSITION_REGRESSION_SUPPORTED)
    assert record.decision_rules[1].state == (
        design.DecisionState.COMPOSITION_HYPOTHESIS_NOT_REPRODUCED
    )
    assert record.decision_rules[2].state == (design.DecisionState.SIMPLE_CONTROL_NOT_RELIABLE)
    assert record.decision_rules[3].state == (design.DecisionState.NON_DETERMINISTIC_OR_AMBIGUOUS)


def test_design_is_execution_inert(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.safety.runtime_execution_authorized is False
    assert record.safety.new_execution_authorized is False
    assert record.safety.kaggle_execution_performed is False
    assert record.safety.gpu_execution_performed is False
    assert record.safety.model_loaded is False
    assert record.safety.worker_started is False
    assert record.safety.model_requests_performed == 0
    assert record.safety.runtime_fix_authorized is False
    assert record.safety.measured_abc_execution_authorized is False


def test_generate_and_validate_are_byte_deterministic(
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
    assert parsed["next_gate"] == design.NEXT_GATE
    assert parsed["safety"]["runtime_execution_authorized"] is False
    assert parsed["safety"]["new_execution_authorized"] is False


def test_authority_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    path = candidate_repo / design.P5_RUNTIME_PATH

    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(design.DesignError) as captured:
        design.validate_authorities(candidate_repo)

    assert captured.value.error_code == "P4_P5_DIFF_AUTHORITY_DRIFT"


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

    assert captured.value.error_code == "P4_P5_DIFF_RECORD_DRIFT"
