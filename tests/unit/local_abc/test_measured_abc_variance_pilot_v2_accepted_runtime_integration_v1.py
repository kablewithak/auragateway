from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_accepted_runtime_integration_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def test_runtime_integration_reuses_only_accepted_runtime_mechanics() -> None:
    integration = subject.build_runtime_integration(ROOT)

    assert integration.accepted_runtime == subject.AcceptedRuntimeIdentity()
    assert integration.worker_bindings == subject.EXPECTED_WORKER_BINDINGS
    assert integration.reuse_boundary.reuse_runtime_installation_mechanics is True
    assert integration.reuse_boundary.reuse_runtime_identity is True
    assert integration.reuse_boundary.reuse_worker_launch_teardown_mechanics is True
    assert integration.reuse_boundary.reuse_telemetry_collection_primitives is True
    assert integration.reuse_boundary.reuse_v1_route_semantics is False
    assert integration.reuse_boundary.reuse_v1_retry_budget is False
    assert integration.reuse_boundary.reuse_v1_output_parsing is False
    assert integration.reuse_boundary.reuse_v1_output_token_budget is False
    assert integration.reuse_boundary.reuse_v1_turn_two_causal_assumptions is False


def test_runtime_integration_freezes_exact_no_retry_request_budget() -> None:
    budget = subject.build_runtime_integration(ROOT).request_budget

    assert budget.schema_canary_requests == 2
    assert budget.warmup_requests == 2
    assert budget.neutral_worker_qualification_requests == 20
    assert budget.pretreatment_requests == 24
    assert budget.pilot_requests == 216
    assert budget.maximum_total_model_requests == 240
    assert budget.maximum_attempts_per_request == 1
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_cases == 0


def test_token_budget_boundary_does_not_claim_unknown_future_prompt_counts() -> None:
    token_budget = subject.build_runtime_integration(ROOT).token_budget

    assert token_budget.max_model_len == 4096
    assert token_budget.max_output_tokens == 256
    assert token_budget.pre_authority_exact_future_prompt_counts_claimed is False
    assert token_budget.pre_authority_tokenizer_envelope_proof_required is True
    assert token_budget.pre_authority_tokenizer_envelope_proof_complete is False
    assert token_budget.runtime_exact_tokenizer_check_before_every_request is True
    assert token_budget.request_permitted_without_runtime_token_check is False
    assert token_budget.runtime_budget_expression == "prompt_tokens + 256 <= 4096"


def test_output_admission_binds_materialized_v2_contract_identities() -> None:
    admission = subject.build_runtime_integration(ROOT).output_admission

    assert (
        admission.strict_response_format_sha256
        == "a720c25951286a1f5d0c8031c25bc9be236048c7dd1258e5b4d0cc926a6bebbd"
    )
    assert (
        admission.standalone_admission_spec_sha256
        == "63568079bc50679b70467b63130aeade5a7fd63ba4c79daef2c6db33eae04a45"
    )
    assert (
        admission.generation_contract_sha256
        == "e31eeac243093d6bc0e4583fbe7568585412a146a8225fa9ff76b9b33d01c0fb"
    )
    assert admission.finish_reason_stop_required is True
    assert admission.finish_reason_length_is_hard_failure is True
    assert admission.invalid_output_retry_permitted is False
    assert admission.invalid_output_history_mutation_permitted is False
    assert admission.later_turns_after_trajectory_failure_permitted is False


def test_runtime_integration_binds_exact_materialization_artifacts() -> None:
    integration = subject.build_runtime_integration(ROOT)
    observed = {item.path: item.sha256 for item in integration.v2_materialized_artifacts}

    assert observed == {
        "data/evals/benchmark/variance-pilot-v2/pilot_schedule.json": (
            "c6b967222626196303c42e01436dd90a492758ebff2524a98acd233345f8bc2c"
        ),
        "data/evals/benchmark/variance-pilot-v2/neutral_worker_qualification_plan.json": (
            "e5d6c5810200defec86dc2f63e1e4181bacc94cc3f8f14bc96de87cc44c5d2b5"
        ),
        "data/evals/benchmark/variance-pilot-v2/strict_response_format.json": (
            "a720c25951286a1f5d0c8031c25bc9be236048c7dd1258e5b4d0cc926a6bebbd"
        ),
        "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json": (
            "63568079bc50679b70467b63130aeade5a7fd63ba4c79daef2c6db33eae04a45"
        ),
        "data/evals/benchmark/variance-pilot-v2/generation_contract.json": (
            "e31eeac243093d6bc0e4583fbe7568585412a146a8225fa9ff76b9b33d01c0fb"
        ),
    }


def test_runtime_integration_remains_non_authorizing() -> None:
    integration = subject.build_runtime_integration(ROOT)

    assert integration.runtime_executable_generated is False
    assert integration.tokenizer_budget_proof_complete is False
    assert integration.pilot_execution_authorized is False
    assert integration.final_measured_abc_execution_authorized is False
    assert integration.new_execution_authorized is False
    assert integration.next_gate == subject.NEXT_GATE
