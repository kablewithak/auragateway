from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    c4_paragraph_order_behavioral_differential_execution_authorization_design_v1 as design,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_authorization_architecture_and_scope_are_frozen() -> None:
    assert design.BASE_MAIN_COMMIT == "7e037596de1a74038583a85ed81d46ec12debbac"
    assert design.IMPLEMENTATION_MERGE_COMMIT == design.BASE_MAIN_COMMIT
    assert design.AUTHORIZATION_ARCHITECTURE == "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
    assert design.AUTHORIZATION_SCOPE == "C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"
    assert design.NEXT_GATE == (
        "IMPLEMENT_AND_MERGE_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_"
        "EXECUTION_AUTHORIZATION_ISSUER_V1"
    )


def test_exact_merged_implementation_authorities_are_bound() -> None:
    assert design.EXPERIMENT_DESIGN_SHA256 == (
        "92bd8194cea68783116bc934b57ae0b1b3a675d0a0ad7dabfa05c680a4755ce9"
    )
    assert design.SUCCESSOR_RUNTIME_SHA256 == (
        "1d055dfab9f83a2706f5335b4529df98d45e45de5210a8c6c21c2b91e6a72df0"
    )
    assert design.IMPLEMENTATION_REVIEW_SHA256 == (
        "355a6b7f7871e648d8bfaf4c7841e9e6346f9b59eba65ac98c00b55d940d2595"
    )
    assert design.IMPLEMENTATION_RECORD_SHA256 == (
        "c563bf012c7ec587089b7b28af5074207a389c5fb7381b9c1213299d3b489386"
    )
    assert design.IMPLEMENTATION_SOURCE_SHA256 == (
        "96f46fc83e34bc83884479bddf769204bba5bb49f38b927386f824ab7f103c5b"
    )
    assert design.IMPLEMENTATION_TEST_SHA256 == (
        "f9ad99abc924ec4c456eafbf9b83cf5218bee83106fb55d9fea429ddee10463a"
    )


def test_six_observation_budget_is_exact_and_non_expandable() -> None:
    budget = design.ExecutionBudget()
    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_save_and_run_all_actions == 1
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 6
    assert budget.maximum_model_loads == 6
    assert budget.maximum_worker_teardowns == 6
    assert budget.maximum_output_tokens_per_request == 32
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_observations == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_external_spend == 0


def test_human_authority_and_platform_receipt_controls_are_preserved() -> None:
    human = design.HumanAuthorizationContract()
    platform = design.PlatformContract()
    receipt = design.PlatformObservationReceiptContract()
    topology = design.TransportTopology()

    assert human.confirmation_method == "RETYPE_DYNAMIC_SHA256_CHALLENGE"
    assert human.challenge_synthesis_by_assistant_prohibited is True
    assert human.maximum_confirmation_age_minutes == 15
    assert platform.accelerator == "T4_X2"
    assert platform.allocated_gpu_count == 2
    assert platform.internet_enabled is False
    assert platform.fresh_post_artifact_observation_required is True
    assert receipt.receipt_must_exist_before_save_and_run_all is True
    assert receipt.receipt_bound_to_transaction_id is True
    assert topology.authorization_specific_kaggle_inputs == 0
    assert topology.authorization_producer_notebooks == 0
    assert topology.manual_confirmation_json_files == 0


def test_paragraph_order_experiment_contract_is_exact() -> None:
    experiment = design.DifferentialExperimentContract()
    assert experiment.request_order == (
        design.CONTROL_CONDITION,
        design.TREATMENT_CONDITION,
        design.TREATMENT_CONDITION,
        design.CONTROL_CONDITION,
        design.CONTROL_CONDITION,
        design.TREATMENT_CONDITION,
    )
    assert experiment.observations_per_condition == 3
    assert experiment.prompt_token_count_per_condition == 899
    assert experiment.final_user_boundary_per_condition == 880
    assert experiment.common_suffix_token_count == 122
    assert experiment.control_paragraph_order == tuple(range(1, 11))
    assert experiment.treatment_paragraph_order == (1, 9, 8, 7, 6, 5, 4, 3, 2, 10)
    assert experiment.paragraph_content_multiset_preserved is True
    assert experiment.token_id_multiset_identical is True
    assert experiment.control_token_sha256 == design.CONTROL_TOKEN_SHA256
    assert experiment.treatment_token_sha256 == design.TREATMENT_TOKEN_SHA256
    assert experiment.control_payload_sha256 == design.CONTROL_PAYLOAD_SHA256
    assert experiment.treatment_payload_sha256 == design.TREATMENT_PAYLOAD_SHA256


def test_control_anchor_and_decision_state_contract_is_exact() -> None:
    experiment = design.DifferentialExperimentContract()
    assert experiment.decision_states == design.DECISION_STATES
    assert experiment.control_anchor_must_reproduce_zero_of_three_exact is True
    assert experiment.control_anchor_valid_json_three_of_three_required is True
    assert experiment.control_anchor_historical_parsed_identity_required is True
    assert experiment.treatment_three_of_three_exact_means_restoration is True
    assert experiment.post_hoc_two_of_three_interpretation_permitted is False
    assert experiment.mixed_result_permits_paragraph_order_claim is False
    assert experiment.paragraph_order_root_cause_claim_permitted is False
    assert experiment.threshold_search_authorized is False
    assert experiment.runtime_remediation_authorized is False
    assert experiment.p5_p6_requalification_authorized is False
    assert experiment.north_star_abc_effect_claim_authorized is False


def test_build_record_binds_exact_merged_authority_roles() -> None:
    record = design.build_record(REPO_ROOT)
    assert record.status == "DESIGN_FROZEN_NOT_EXECUTED"
    assert record.base_main_commit == design.BASE_MAIN_COMMIT
    assert record.implementation_merge_commit == design.IMPLEMENTATION_MERGE_COMMIT
    assert tuple(authority.role for authority in record.authorities) == (
        "frozen_experiment_design",
        "merged_successor_runtime",
        "implementation_review",
        "implementation_record",
    )
    assert tuple(authority.sha256 for authority in record.authorities) == (
        design.EXPERIMENT_DESIGN_SHA256,
        design.SUCCESSOR_RUNTIME_SHA256,
        design.IMPLEMENTATION_REVIEW_SHA256,
        design.IMPLEMENTATION_RECORD_SHA256,
    )
    assert record.live_authorization_issued is False
    assert record.runtime_execution_authorized is False
    assert record.model_requests_performed == 0
    assert record.governed_executable_generated is False


def test_render_record_is_deterministic_and_canonical() -> None:
    first = design.render_record(REPO_ROOT)
    second = design.render_record(REPO_ROOT)
    assert first == second
    assert first.endswith(b"\n")
    assert b'"status": "DESIGN_FROZEN_NOT_EXECUTED"' in first
    assert b'"live_authorization_issued": false' in first
    assert b'"runtime_execution_authorized": false' in first


def test_models_fail_closed_on_extra_fields() -> None:
    with pytest.raises(ValidationError):
        design.ExecutionBudget.model_validate(
            {
                **design.ExecutionBudget().model_dump(),
                "unexpected_budget_expansion": 1,
            }
        )


def test_transaction_identity_binds_both_conditions_and_order() -> None:
    identity = design.TransactionIdentityContract()
    assert identity.canonical_authorization_bytes_bound is True
    assert identity.runtime_payload_sha256_bound is True
    assert identity.control_request_payload_sha256_bound is True
    assert identity.treatment_request_payload_sha256_bound is True
    assert identity.control_token_sha256_bound is True
    assert identity.treatment_token_sha256_bound is True
    assert identity.request_order_bound is True
    assert identity.nonidentical_regeneration_requires_fresh_authority is True


def test_terminalization_remains_single_use_governance() -> None:
    terminalization = design.TerminalizationContract()
    assert terminalization.attempted_execution_terminalizes_authority is True
    assert terminalization.terminal_authorization_reusable is False
    assert terminalization.multiple_observed_executions_invalidate_acceptance is True
    assert terminalization.runtime_anti_replay_established is False
    assert terminalization.malicious_operator_resistance_established is False
