from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

design = cast(
    Any,
    importlib.import_module(
        "auragateway.local_abc."
        "b_vs_d_cumulative_length_locked_marker_diversified_differential_"
        "execution_authorization_design_v1"
    ),
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_design_binds_frozen_design_and_merged_implementation_authorities() -> None:
    record = design.build_record(REPO_ROOT)
    observed = {authority.role: authority.sha256 for authority in record.authorities}
    assert observed == {
        "frozen_experiment_design": (
            "2e07651681d98d604f0e0f6b4e8964906f39b8bfa0e48b8f8fa8e9de431e7ef9"
        ),
        "merged_successor_runtime": (
            "fe5bf3cc731d42ead44451cea4298ba1507cbcba28b65fcdbae0a31237868d39"
        ),
        "implementation_review": (
            "7278fdf91cef5fd2a19e39f4bc34421c2dce823a42e09aacc7c44ccce7fb53dc"
        ),
        "implementation_record": (
            "795a7cdf5285ba49e5dcc57a76cd46e03f07121359a5f66101692cee41bb2074"
        ),
    }


def test_design_freezes_scope_architecture_and_six_request_budget() -> None:
    record = design.build_record(REPO_ROOT)
    budget = record.execution_budget
    assert record.authorization_architecture == "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
    assert record.authorization_scope == (
        "B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"
    )
    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_save_and_run_all_actions == 1
    assert budget.maximum_runtime_install_attempts == 1
    assert budget.maximum_runtime_import_closure_probes == 1
    assert budget.maximum_model_requests == 6
    assert budget.maximum_model_loads == 6
    assert budget.maximum_worker_starts == 6
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_observations == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_benchmark_trajectory_requests == 0
    assert budget.maximum_external_spend == 0


def test_design_freezes_exact_b_vs_d_experiment_contract() -> None:
    experiment = design.build_record(REPO_ROOT).experiment
    assert experiment.condition_b_id == "B_NEUTRAL_REPEATED_24X"
    assert experiment.condition_d_id == (
        "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED"
    )
    assert experiment.request_order == (
        "B_NEUTRAL_REPEATED_24X",
        "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
        "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
        "B_NEUTRAL_REPEATED_24X",
        "B_NEUTRAL_REPEATED_24X",
        "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
    )
    assert experiment.observations_per_condition == 3
    assert experiment.prompt_token_count_per_condition == 899
    assert experiment.segment_count_per_condition == 24
    assert experiment.complete_cumulative_prompt_token_profile_locked
    assert experiment.cumulative_prompt_token_count_profile[-1] == 899
    assert experiment.cumulative_prompt_token_increment == 34
    assert experiment.fresh_worker_process_per_observation
    assert experiment.zero_cached_prefix_baseline_required
    assert experiment.teardown_required_between_observations
    assert not experiment.prior_request_cache_carryover_permitted
    assert experiment.pre_request_token_identity_journal_required
    assert experiment.pre_request_identity_persisted_before_model_request_budget
    assert experiment.invalid_json_retained_as_observation


def test_design_freezes_b_and_d_token_payload_identities_and_markers() -> None:
    experiment = design.build_record(REPO_ROOT).experiment
    assert experiment.b_token_sha256 == (
        "02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"
    )
    assert experiment.b_payload_sha256 == (
        "1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb"
    )
    assert experiment.d_token_sha256 == (
        "878ecc057fbc92764c7b8bddc3024e12720470b84a72d974ef677c16d1e37e21"
    )
    assert experiment.d_payload_sha256 == (
        "0728e8632e4694cd670e472751154d38dcacc34071d74e1caad8ece6608c8010"
    )
    assert len(experiment.d_marker_sequence) == 24
    assert experiment.d_marker_sequence[0] == "birch"
    assert experiment.d_marker_sequence[-1] == "orchid"


def test_design_freezes_generation_and_composition_controls() -> None:
    experiment = design.build_record(REPO_ROOT).experiment
    assert experiment.message_roles == ("system", "user", "assistant", "user")
    assert experiment.canonical_final_object == '{"probe":"exact-runtime-p5-p6","value":1}'
    assert experiment.maximum_output_tokens == 32
    assert experiment.temperature == 0
    assert experiment.top_p == 1
    assert experiment.repetition_penalty == 1.1
    assert experiment.seed == 7
    assert not experiment.stream
    assert not experiment.response_format_present
    assert experiment.output_mode == "UNCONSTRAINED"


def test_repetition_penalty_drift_is_rejected() -> None:
    with pytest.raises(ValidationError):
        design.DifferentialExperimentContract(repetition_penalty=1.2)


def test_design_freezes_decisions_and_nonclaims() -> None:
    experiment = design.build_record(REPO_ROOT).experiment
    assert experiment.b_0_d_3 == (
        "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"
    )
    assert experiment.b_0_d_0 == ("MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL")
    assert experiment.b_0_d_mixed == "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM"
    assert experiment.b_anchor_nonreproduction == ("B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE")
    assert experiment.invariant_failure == "DIAGNOSTIC_INVALID"
    assert experiment.b_anchor_must_reproduce_zero_of_three
    assert not experiment.mixed_result_permits_mechanistic_claim
    assert not experiment.post_hoc_two_of_three_interpretation_permitted
    assert not experiment.text_segment_boundary_must_equal_token_boundary
    assert experiment.bounded_marker_lexical_semantic_novelty_remains
    assert not experiment.exact_repetition_sole_or_root_cause_claim_permitted
    assert not experiment.aligned_block_recurrence_causal_claim_permitted
    assert not experiment.marker_lexical_novelty_eliminated
    assert not experiment.marker_semantic_novelty_eliminated
    assert not experiment.threshold_search_authorized
    assert not experiment.runtime_remediation_authorized
    assert not experiment.p5_p6_requalification_authorized
    assert not experiment.north_star_abc_effect_claim_authorized


def test_design_requires_dynamic_human_authority_and_durable_platform_receipt() -> None:
    record = design.build_record(REPO_ROOT)
    human = record.human_authorization
    receipt = record.platform_observation_receipt
    assert human.fresh_human_authority_required
    assert human.confirmation_method == "RETYPE_DYNAMIC_SHA256_CHALLENGE"
    assert human.challenge_must_be_dynamic
    assert human.exact_challenge_retype_required
    assert human.confirmation_binds_exact_authorization_intent
    assert human.challenge_synthesis_by_runtime_prohibited
    assert human.challenge_synthesis_by_model_prohibited
    assert human.challenge_synthesis_by_issuer_prohibited
    assert human.challenge_synthesis_by_assistant_prohibited
    assert receipt.control_id == "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    assert receipt.durable_receipt_required
    assert receipt.receipt_must_exist_before_save_and_run_all
    assert receipt.receipt_created_after_transaction_artifact
    assert not receipt.console_only_observation_sufficient
    assert receipt.failure_to_persist_blocks_execution


def test_design_preserves_transaction_transport_and_terminalization() -> None:
    record = design.build_record(REPO_ROOT)
    topology = record.transport_topology
    transaction = record.transaction_identity
    terminal = record.terminalization
    assert topology.authorization_specific_kaggle_inputs == 0
    assert topology.authorization_producer_notebooks == 0
    assert topology.manual_confirmation_json_files == 0
    assert not topology.runtime_authorization_filename_discovery_permitted
    assert topology.permitted_kaggle_input_roles == ("durable_runtime", "model_snapshot")
    assert transaction.transaction_id_derivation == "SHA256_CANONICAL_AUTHORIZATION_BYTES"
    assert transaction.canonical_authorization_bytes_bound
    assert transaction.runtime_payload_sha256_bound
    assert transaction.generator_contract_sha256_bound
    assert transaction.nonidentical_regeneration_requires_fresh_authority
    assert terminal.attempted_execution_terminalizes_authority
    assert not terminal.terminal_authorization_reusable
    assert not terminal.secondary_failure_may_mask_primary_failure
    assert terminal.multiple_observed_executions_invalidate_acceptance
    assert not terminal.runtime_anti_replay_established
    assert not terminal.malicious_operator_resistance_established


def test_design_is_static_and_non_authorizing() -> None:
    record = design.build_record(REPO_ROOT)
    assert record.status == "DESIGN_FROZEN_NOT_EXECUTED"
    assert not record.live_authorization_issued
    assert not record.runtime_execution_authorized
    assert record.model_requests_performed == 0
    assert record.model_loads_performed == 0
    assert record.worker_starts_performed == 0
    assert not record.kaggle_execution_performed
    assert not record.governed_executable_generated
    assert not record.platform_observation_persisted


def test_record_rendering_is_deterministic() -> None:
    assert design.render_record(REPO_ROOT) == design.render_record(REPO_ROOT)
