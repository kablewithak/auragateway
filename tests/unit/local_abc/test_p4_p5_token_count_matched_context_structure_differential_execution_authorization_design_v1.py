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
        "p4_p5_token_count_matched_context_structure_differential_"
        "execution_authorization_design_v1"
    ),
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_design_binds_exact_merged_implementation_authorities() -> None:
    record = design.build_record(REPO_ROOT)
    observed = {authority.role: authority.sha256 for authority in record.authorities}

    assert observed == {
        "merged_successor_runtime": (
            "9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834"
        ),
        "implementation_review": (
            "fe7bd30cc8afdaa318d09a65748f2ae2d214d7c42f83416b666f1da9d8580a1a"
        ),
        "implementation_record": (
            "6815a8d3b6a7eb5e88212fd0e280cbfc686f378ab0c98f18e1a05e0de0681b27"
        ),
    }


def test_design_freezes_exact_token_matched_execution_budget() -> None:
    budget = design.build_record(REPO_ROOT).execution_budget

    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_save_and_run_all_actions == 1
    assert budget.maximum_runtime_install_attempts == 1
    assert budget.maximum_runtime_import_closure_probes == 1
    assert budget.maximum_model_requests == 9
    assert budget.maximum_worker_starts == 9
    assert budget.maximum_model_loads == 9
    assert budget.maximum_output_tokens_per_request == 32
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_observations == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_benchmark_trajectory_requests == 0
    assert budget.maximum_external_spend == 0


def test_design_freezes_exact_token_matched_differential_contract() -> None:
    experiment = design.build_record(REPO_ROOT).experiment

    assert experiment.variable_under_test == "TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE"
    assert experiment.condition_a_id == "A_ORIGINAL_24X_ANCHOR"
    assert experiment.condition_b_id == "B_NEUTRAL_REPEATED_24X"
    assert experiment.condition_c_id == "C_NEUTRAL_DIVERSE_24_SEGMENT"
    assert experiment.request_order == (
        "A_ORIGINAL_24X_ANCHOR",
        "B_NEUTRAL_REPEATED_24X",
        "C_NEUTRAL_DIVERSE_24_SEGMENT",
        "B_NEUTRAL_REPEATED_24X",
        "C_NEUTRAL_DIVERSE_24_SEGMENT",
        "A_ORIGINAL_24X_ANCHOR",
        "C_NEUTRAL_DIVERSE_24_SEGMENT",
        "A_ORIGINAL_24X_ANCHOR",
        "B_NEUTRAL_REPEATED_24X",
    )
    assert experiment.observations_per_condition == 3
    assert experiment.prompt_token_count_per_condition == 899
    assert experiment.segment_count_per_condition == 24
    assert experiment.fresh_worker_process_per_observation
    assert experiment.zero_cached_prefix_baseline_required
    assert experiment.teardown_required_between_observations
    assert experiment.pre_request_token_identity_journal_required
    assert not experiment.prior_request_cache_carryover_permitted
    assert experiment.condition_token_identity_required_before_request
    assert experiment.condition_payload_identity_required_before_request


def test_design_freezes_all_three_condition_identities() -> None:
    experiment = design.build_record(REPO_ROOT).experiment

    assert experiment.a_token_sha256 == (
        "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
    )
    assert experiment.b_token_sha256 == (
        "02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"
    )
    assert experiment.c_token_sha256 == (
        "612e1ada53aba2158536cb0d0e142e3152df7e177ff951a2565385473ec698d4"
    )
    assert experiment.a_payload_sha256 == (
        "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
    )
    assert experiment.b_payload_sha256 == (
        "1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb"
    )
    assert experiment.c_payload_sha256 == (
        "8a3d22f50f1956375cfd52f4f01e1843bfe4753da5c76359c47b8da6ecd46f72"
    )


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


def test_design_freezes_decision_matrix_and_nonclaims() -> None:
    experiment = design.build_record(REPO_ROOT).experiment

    assert experiment.a_0_b_3_c_3 == (
        "REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED"
    )
    assert experiment.a_0_b_0_c_3 == ("HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED")
    assert experiment.a_0_b_0_c_0 == "SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE"
    assert experiment.a_0_b_3_c_0 == "DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED"
    assert experiment.mixed_condition == "UNSTABLE_NO_MECHANISTIC_CLAIM"
    assert experiment.anchor_nonreproduction == (
        "ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE"
    )
    assert experiment.invariant_failure == "DIAGNOSTIC_INVALID"
    assert experiment.anchor_a_must_reproduce_zero_of_three
    assert not experiment.mixed_result_permits_mechanistic_claim
    assert experiment.b_to_c_residual_lexical_novelty_bounded
    assert not experiment.exact_repetition_sole_cause_claim_permitted
    assert not experiment.semantic_amplification_sole_cause_claim_permitted
    assert not experiment.threshold_search_authorized
    assert not experiment.runtime_remediation_authorized
    assert not experiment.p5_p6_requalification_authorized
    assert not experiment.north_star_abc_effect_claim_authorized


def test_design_requires_durable_platform_observation_receipt() -> None:
    record = design.build_record(REPO_ROOT)
    platform = record.platform
    receipt = record.platform_observation_receipt

    assert platform.accelerator == "T4_X2"
    assert platform.allocated_gpu_count == 2
    assert not platform.internet_enabled
    assert platform.fresh_post_artifact_observation_required
    assert platform.observation_precedes_save_and_run_all
    assert not platform.observation_mounted_as_runtime_input
    assert platform.machine_observable_runtime_topology_check_required

    assert receipt.control_id == "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    assert receipt.durable_receipt_required
    assert receipt.receipt_must_exist_before_save_and_run_all
    assert receipt.receipt_bound_to_transaction_id
    assert receipt.receipt_created_after_transaction_artifact
    assert not receipt.receipt_runtime_input
    assert not receipt.console_only_observation_sufficient
    assert receipt.failure_to_persist_blocks_execution


def test_design_preserves_transaction_bound_topology() -> None:
    record = design.build_record(REPO_ROOT)
    topology = record.transport_topology
    transaction = record.transaction_identity

    assert record.authorization_architecture == "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
    assert record.authorization_scope == (
        "P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"
    )
    assert topology.authorization_specific_kaggle_inputs == 0
    assert topology.authorization_producer_notebooks == 0
    assert topology.manual_confirmation_json_files == 0
    assert not topology.runtime_authorization_filename_discovery_permitted
    assert topology.permitted_kaggle_input_roles == ("durable_runtime", "model_snapshot")
    assert transaction.transaction_id_derivation == "SHA256_CANONICAL_AUTHORIZATION_BYTES"
    assert transaction.canonical_authorization_bytes_bound
    assert transaction.runtime_payload_sha256_bound
    assert transaction.generator_contract_sha256_bound
    assert transaction.deterministic_artifact_generation_required
    assert not transaction.whole_notebook_sha256_is_semantic_payload_identity
    assert transaction.nonidentical_regeneration_requires_fresh_authority


def test_design_requires_fresh_dynamic_human_authority() -> None:
    human = design.build_record(REPO_ROOT).human_authorization

    assert human.fresh_human_authority_required
    assert human.confirmation_method == "RETYPE_DYNAMIC_SHA256_CHALLENGE"
    assert human.challenge_must_be_dynamic
    assert human.exact_challenge_retype_required
    assert human.confirmation_binds_exact_authorization_intent
    assert human.challenge_synthesis_by_runtime_prohibited
    assert human.maximum_confirmation_age_minutes == 15
    assert human.default_authorization_window_minutes == 180
    assert human.maximum_authorization_window_minutes == 240


def test_design_preserves_evidence_privacy_and_terminalization() -> None:
    record = design.build_record(REPO_ROOT)
    evidence = record.evidence
    terminal = record.terminalization

    assert evidence.expected_evidence_zip == (
        "ag-p4-p5-token-count-matched-context-structure-differential-evidence-v1.zip"
    )
    assert evidence.pre_request_token_identity_journal == (
        "pre_request_token_identity_journal_v1.json"
    )
    assert not evidence.raw_prompt_retained
    assert not evidence.raw_output_retained
    assert not evidence.credentials_permitted
    assert not evidence.customer_data_permitted
    assert evidence.platform_observation_bound_to_transaction
    assert evidence.saved_version_bound_to_transaction
    assert evidence.evidence_identity_bound_to_terminal_receipt
    assert evidence.terminalizable_without_expected_evidence_zip

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


def test_checked_in_record_matches_deterministic_contract() -> None:
    assert (REPO_ROOT / design.DESIGN_RECORD_PATH).read_bytes() == design.render_record(REPO_ROOT)


def test_complete_design_validation() -> None:
    result = design.validate(REPO_ROOT)

    assert result["status"] == "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORIZATION_DESIGN_VALID"
    assert result["authorization_scope"] == (
        "P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"
    )
    assert result["maximum_model_requests"] == 9
    assert result["maximum_worker_starts"] == 9
    assert result["maximum_model_loads"] == 9
    assert result["maximum_hidden_retries"] == 0
    assert result["durable_platform_observation_required"] is True
    assert result["observation_precedes_save_and_run_all"] is True
    assert result["observations_per_condition"] == 3
    assert result["prompt_token_count_per_condition"] == 899
    assert result["condition_count"] == 3
    assert result["fresh_worker_process_per_observation"] is True
    assert result["authorization_specific_kaggle_inputs"] == 0
    assert result["authorization_producer_notebooks"] == 0
    assert result["live_authorization_issued"] is False
    assert result["runtime_execution_authorized"] is False


def test_design_freezes_exact_runtime_model_contract() -> None:
    runtime = design.build_record(REPO_ROOT).runtime_model

    assert runtime.python == "3.12"
    assert runtime.cuda_variant == "cu129"
    assert runtime.torch == "2.11.0+cu129"
    assert runtime.torch_cuda_version == "12.9"
    assert runtime.transformers == "5.14.1"
    assert runtime.triton == "3.6.0"
    assert runtime.vllm_distribution == "0.25.1+cu129"
    assert runtime.vllm_public_semantic_version == "0.25.1"
    assert runtime.required_native_module == "vllm._C_stable_libtorch"
    assert runtime.attention_backend == "TRITON_ATTN"
    assert runtime.gpu_topology == "T4_x2"
    assert runtime.model_repository == "Qwen/Qwen2.5-0.5B-Instruct"
    assert runtime.model_revision == "7ae557604adf67be50417f59c2c2f167def9a775"
    assert runtime.tokenizer_revision == runtime.model_revision
    assert runtime.model_directory_sha256 == (
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    )


def test_future_authorization_payload_is_fully_lineage_bound() -> None:
    binding = design.build_record(REPO_ROOT).authorization_payload_binding

    assert binding.authorization_scope_bound
    assert binding.authorization_design_record_sha256_bound
    assert binding.issuer_merge_commit_bound
    assert binding.implementation_merge_commit_bound
    assert binding.implementation_authority_hashes_bound
    assert binding.runtime_model_contract_bound
    assert binding.execution_budget_bound
    assert binding.differential_experiment_contract_bound
    assert binding.required_platform_policy_bound
    assert binding.authorization_window_bound
