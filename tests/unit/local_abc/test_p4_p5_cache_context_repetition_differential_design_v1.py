from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import p4_p5_cache_context_repetition_differential_design_v1

design = p4_p5_cache_context_repetition_differential_design_v1


@pytest.fixture
def candidate_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    for relative in (
        design.STATIC_RECORD_PATH,
        design.STATIC_REVIEW_PATH,
        design.RUNTIME_PATH,
        design.C3_PATH,
        design.DIFF_PATH,
        design.P5_ACCEPT_PATH,
        design.P5_RESET_PATH,
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

    assert captured.value.error_code == "P4_P5_REPETITION_DIFF_BASE_MAIN_DRIFT"
    assert captured.value.safe_message == ("frozen design base is not an ancestor of current HEAD")


def test_variable_is_repetition_count_only(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)
    control, treatment = record.conditions

    assert record.frozen_composition.variable_under_test == "CACHE_CONTEXT_REPETITION_COUNT"
    assert record.frozen_composition.prefix_variant == "A"
    assert record.frozen_composition.message_roles == ("system", "user", "assistant", "user")
    assert control.repetition_count == 1
    assert treatment.repetition_count == 24


def test_fresh_worker_cold_state_contract(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.starting_state.strategy == "FRESH_WORKER_PROCESS_PER_OBSERVATION"
    assert record.starting_state.prior_request_cache_carryover_permitted is False
    assert record.starting_state.namespace_only_reset_permitted is False
    assert record.starting_state.require_fresh_worker_identity is True
    assert record.starting_state.require_zero_cached_prefix_baseline is True
    assert record.starting_state.teardown_required_between_observations is True

    assert record.execution_budget.maximum_model_requests == 6
    assert record.execution_budget.maximum_model_loads == 6
    assert record.execution_budget.maximum_worker_starts == 6
    assert record.execution_budget.hidden_retries_permitted == 0
    assert record.execution_budget.replacement_workers_permitted == 0


def test_request_plan_is_counterbalanced(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(item.condition_id.value for item in record.request_plan) == (
        "CONTROL_1X",
        "TREATMENT_24X",
        "TREATMENT_24X",
        "CONTROL_1X",
        "CONTROL_1X",
        "TREATMENT_24X",
    )


def test_exact_failed_24x_identity_is_bound(candidate_repo: Path) -> None:
    token = design.build_design_record(candidate_repo).token_identity

    assert token.treatment_expected_token_count == 899
    assert token.treatment_expected_token_sha256 == (
        "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
    )
    assert token.treatment_expected_payload_sha256 == (
        "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
    )
    assert token.treatment_must_match_historical_failed_24x_identity is True
    assert token.control_must_differ_from_treatment_token_identity is True


def test_runtime_and_generation_controls_are_frozen(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.runtime.backend == "TRITON_ATTN"
    assert record.runtime.vllm_distribution == "0.25.1+cu129"
    assert record.runtime.prefix_caching_enabled is True
    assert record.runtime.cache_block_size == 16
    assert record.runtime.max_model_len == 4096

    assert record.generation_controls.temperature == 0
    assert record.generation_controls.top_p == 1
    assert record.generation_controls.repetition_penalty == 1.1
    assert record.generation_controls.seed == 7
    assert record.generation_controls.max_tokens == 32
    assert record.generation_controls.response_format_present is False


def test_decision_contract_is_complete(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(rule.state for rule in record.decision_rules) == tuple(design.DecisionState)
    assert len(record.decision_rules) == 6


def test_design_is_execution_inert(candidate_repo: Path) -> None:
    safety = design.build_design_record(candidate_repo).safety

    assert safety.runtime_execution_authorized is False
    assert safety.new_execution_authorized is False
    assert safety.kaggle_execution_performed is False
    assert safety.gpu_execution_performed is False
    assert safety.model_loaded is False
    assert safety.worker_started is False
    assert safety.model_requests_performed == 0
    assert safety.runtime_fix_authorized is False
    assert safety.threshold_search_authorized is False
    assert safety.assistant_topology_discriminator_authorized is False
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
    assert parsed["starting_state"]["strategy"] == "FRESH_WORKER_PROCESS_PER_OBSERVATION"


def test_authority_drift_fails_closed(candidate_repo: Path) -> None:
    path = candidate_repo / design.RUNTIME_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(design.DesignError) as captured:
        design.validate_authorities(candidate_repo)

    assert captured.value.error_code == "P4_P5_REPETITION_DIFF_AUTHORITY_DRIFT"


def test_generated_record_drift_fails_closed(candidate_repo: Path) -> None:
    design.generate(candidate_repo)
    path = candidate_repo / design.RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["design_status"] = "TAMPERED"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(design.DesignError) as captured:
        design.validate_generated(candidate_repo)

    assert captured.value.error_code == "P4_P5_REPETITION_DIFF_RECORD_DRIFT"
