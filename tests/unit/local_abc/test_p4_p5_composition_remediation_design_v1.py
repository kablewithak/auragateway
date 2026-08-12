from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import p4_p5_composition_remediation_design_v1

design = p4_p5_composition_remediation_design_v1


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]

    paths = (
        design.P4_ACCEPTANCE_PATH,
        design.P4_IMPLEMENTATION_RECORD_PATH,
        design.P4_TEMPLATE_PATH,
        design.P5_RUNTIME_PATH,
        design.C3_RECONCILIATION_PATH,
        design.DIFFERENTIAL_DESIGN_PATH,
        design.DIFFERENTIAL_IMPLEMENTATION_PATH,
        design.DIFFERENTIAL_RECONCILIATION_PATH,
    )

    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)

    return tmp_path


def test_authorities_bind_historical_current_and_experimental_evidence(
    candidate_repo: Path,
) -> None:
    authorities = design.validate_authorities(candidate_repo)

    by_scope = {
        scope: {item.role for item in authorities if item.scope == scope}
        for scope in design.AuthorityScope
    }

    assert by_scope[design.AuthorityScope.HISTORICAL_PRECEDENT] == {
        "historical_p4_execution_acceptance",
        "historical_p4_implementation_record",
        "historical_p4_v4_v5_message_matrix",
    }
    assert by_scope[design.AuthorityScope.CURRENT] == {
        "current_p5_p6_predecessor_runtime",
        "current_c3_failure_reconciliation",
    }
    assert by_scope[design.AuthorityScope.CONTROLLED_EXPERIMENT] == {
        "controlled_composition_differential_design",
        "controlled_composition_differential_implementation",
        "accepted_composition_differential_result",
    }


def test_intervention_changes_only_cache_context_instruction_tail(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.intervention.intervention_id == (
        design.InterventionId.REPLACE_V5_CACHE_CONTEXT_INSTRUCTION_WITH_ACCEPTED_V4_INSTRUCTION
    )
    assert record.intervention.target_constants == (
        "SYNTHETIC_CACHE_CONTEXT_A",
        "SYNTHETIC_CACHE_CONTEXT_B",
    )
    assert record.intervention.before_instruction == design.V5_INSTRUCTION
    assert record.intervention.after_instruction == design.V4_INSTRUCTION
    assert record.intervention.expected_predecessor_occurrences == 2
    assert record.intervention.expected_successor_occurrences_of_before == 0
    assert record.intervention.expected_successor_occurrences_of_after_in_cache_contexts == 2


def test_composition_and_generation_invariants_are_frozen(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.composition_invariants.message_roles == (
        "system",
        "user",
        "assistant",
        "user",
    )
    assert record.composition_invariants.synthetic_assistant_ack == design.ASSISTANT_ACK
    assert record.composition_invariants.synthetic_assistant_ack_preserved is True
    assert record.composition_invariants.cache_context_repetition_count == 24
    assert record.composition_invariants.prefix_variants_preserved == ("A", "B")
    assert record.composition_invariants.final_object_canonical == (
        '{"probe":"exact-runtime-p5-p6","value":1}'
    )
    assert record.composition_invariants.p5_decision_semantics_preserved is True
    assert record.composition_invariants.p6_decision_semantics_preserved is True

    assert record.generation_controls.temperature == 0
    assert record.generation_controls.top_p == 1
    assert record.generation_controls.repetition_penalty == 1.1
    assert record.generation_controls.seed == 7
    assert record.generation_controls.max_tokens == 32
    assert record.generation_controls.response_format_present is False
    assert record.generation_controls.output_mode == "UNCONSTRAINED"


def test_pre_request_token_identity_evidence_is_failure_safe(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)
    control = record.pre_request_evidence_control

    assert control.artifact_name == "pre_request_token_identity_journal_v1.json"
    assert control.retained_fields == design.PRE_REQUEST_EVIDENCE_FIELDS
    assert control.persist_after_tokenization is True
    assert control.persist_before_metric_snapshot is True
    assert control.persist_before_model_request_budget_consumption is True
    assert control.persist_before_chat_completion_request is True
    assert control.atomic_write_required is True
    assert control.raw_prompt_retained is False
    assert control.raw_model_output_retained is False
    assert control.payload_hash_only is True


def test_full_runtime_acceptance_preserves_p5_and_p6_semantics(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)
    acceptance = record.full_runtime_acceptance

    assert acceptance.request_roles == (
        "BASE_COLD",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    )
    assert acceptance.maximum_model_requests == 6
    assert acceptance.maximum_model_loads == 3
    assert acceptance.maximum_worker_starts == 3
    assert acceptance.hidden_retries_permitted == 0
    assert acceptance.exact_structured_output_required_for_all_requests is True
    assert acceptance.p5_required_state == "PASS"
    assert acceptance.p6_required_state == "PASS"
    assert acceptance.prefix_a_token_identity_stable_across_controls is True
    assert acceptance.negative_prefix_token_identity_must_diverge is True
    assert acceptance.warm_cache_reuse_required is True
    assert acceptance.reset_cold_state_required is True
    assert acceptance.cross_worker_cold_state_required is True
    assert acceptance.worker_1_retention_required is True


def test_future_platform_observation_control_is_frozen_but_deferred(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)
    control = record.future_authorization_control

    assert control.control_id == "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    assert control.deferred_to_authorization_tranche is True
    assert control.required_fields == design.FUTURE_PLATFORM_FIELDS
    assert control.must_bind_transaction_id is True
    assert control.must_be_persisted_before_save_and_run_all is True
    assert control.console_only_observation_permitted is False


def test_design_is_execution_inert(
    candidate_repo: Path,
) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.safety.runtime_execution_authorized is False
    assert record.safety.new_execution_authorized is False
    assert record.safety.remediation_implemented is False
    assert record.safety.successor_runtime_generated is False
    assert record.safety.kaggle_execution_performed is False
    assert record.safety.gpu_execution_performed is False
    assert record.safety.model_loaded is False
    assert record.safety.worker_started is False
    assert record.safety.model_requests_performed == 0
    assert record.safety.case_c_authorized is False


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

    assert parsed["design_status"] == "DESIGN_FROZEN_NOT_IMPLEMENTED"
    assert parsed["next_gate"] == design.NEXT_GATE
    assert parsed["safety"]["runtime_execution_authorized"] is False
    assert parsed["safety"]["remediation_implemented"] is False


def test_predecessor_authority_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    path = candidate_repo / design.P5_RUNTIME_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(design.DesignError) as captured:
        design.validate_authorities(candidate_repo)

    assert captured.value.error_code == "P4_P5_REMEDIATION_AUTHORITY_DRIFT"


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

    assert captured.value.error_code == "P4_P5_REMEDIATION_RECORD_DRIFT"
