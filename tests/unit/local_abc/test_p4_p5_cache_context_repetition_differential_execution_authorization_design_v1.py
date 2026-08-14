from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    p4_p5_cache_context_repetition_differential_execution_authorization_design_v1 as design,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_design_binds_exact_merged_authorities() -> None:
    record = design.build_record(REPO_ROOT)
    observed = {authority.role: authority.sha256 for authority in record.authorities}

    assert observed == {
        "merged_successor_runtime": (
            "dfa0e7ea48eaf21dd6d3faf97b0440dda19817dec18de7c17d720c9185569a4b"
        ),
        "implementation_review": (
            "6bf7595e9dda3793f94bf866e0feff8db31cfe2c4c9cd7e3f4941c973a4ea2a4"
        ),
        "implementation_record": (
            "31628aef52b292236bbaf9a787fd1f47ca3751a1416cf916b51fc354258e4a6c"
        ),
    }


def test_design_freezes_repetition_execution_budget() -> None:
    budget = design.build_record(REPO_ROOT).execution_budget

    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_save_and_run_all_actions == 1
    assert budget.maximum_runtime_install_attempts == 1
    assert budget.maximum_runtime_import_closure_probes == 1
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 6
    assert budget.maximum_model_loads == 6
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_workers == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_benchmark_trajectory_requests == 0
    assert budget.maximum_external_spend == 0


def test_design_freezes_exact_repetition_differential_contract() -> None:
    experiment = design.build_record(REPO_ROOT).experiment

    assert experiment.variable_under_test == "CACHE_CONTEXT_REPETITION_COUNT"
    assert experiment.control_condition_id == "CONTROL_1X"
    assert experiment.treatment_condition_id == "TREATMENT_24X"
    assert experiment.request_order == (
        "CONTROL_1X",
        "TREATMENT_24X",
        "TREATMENT_24X",
        "CONTROL_1X",
        "CONTROL_1X",
        "TREATMENT_24X",
    )
    assert experiment.control_repetition_count == 1
    assert experiment.treatment_repetition_count == 24
    assert experiment.observations_per_condition == 3
    assert experiment.fresh_worker_process_per_observation
    assert experiment.zero_cached_prefix_baseline_required
    assert experiment.teardown_required_between_observations
    assert experiment.pre_request_token_identity_journal_required
    assert experiment.control_intra_condition_identity_required
    assert experiment.treatment_intra_condition_identity_required
    assert experiment.control_must_differ_from_treatment_token_identity
    assert experiment.treatment_must_match_historical_failed_24x_identity
    assert experiment.treatment_expected_token_count == 899
    assert experiment.treatment_expected_token_sha256 == (
        "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
    )
    assert experiment.treatment_expected_payload_sha256 == (
        "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
    )


def test_design_freezes_exact_decision_states_and_non_claims() -> None:
    experiment = design.build_record(REPO_ROOT).experiment

    assert experiment.control_3_of_3_treatment_0_of_3 == "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"
    assert experiment.control_0_of_3_treatment_0_of_3 == "REPETITION_NOT_NECESSARY"
    assert experiment.control_3_of_3_treatment_3_of_3 == "REGRESSION_NOT_REPRODUCED"
    assert experiment.unstable_control == "CONTROL_NOT_RELIABLE"
    assert experiment.stable_control_mixed_treatment == "NON_DETERMINISTIC_OR_AMBIGUOUS"
    assert experiment.invariant_failure == "DIAGNOSTIC_INVALID"
    assert not experiment.threshold_search_authorized
    assert not experiment.assistant_topology_discriminator_authorized
    assert not experiment.runtime_remediation_authorized
    assert not experiment.measured_abc_execution_authorized


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
    assert receipt.required_fields == (
        "transaction_id",
        "platform_observed_at",
        "accelerator",
        "allocated_gpu_count",
        "internet_enabled",
        "capability_source",
    )


def test_design_preserves_transaction_bound_topology() -> None:
    record = design.build_record(REPO_ROOT)
    topology = record.transport_topology
    transaction = record.transaction_identity

    assert record.authorization_architecture == "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
    assert topology.authorization_specific_kaggle_inputs == 0
    assert topology.authorization_producer_notebooks == 0
    assert topology.manual_confirmation_json_files == 0
    assert not topology.runtime_authorization_filename_discovery_permitted
    assert topology.permitted_kaggle_input_roles == (
        "durable_runtime",
        "model_snapshot",
    )
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
        "ag-p4-p5-cache-context-repetition-differential-evidence-v1.zip"
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
    first = design.render_record(REPO_ROOT)
    second = design.render_record(REPO_ROOT)

    assert first == second


def test_checked_in_record_matches_deterministic_contract() -> None:
    expected = design.render_record(REPO_ROOT)
    observed = (REPO_ROOT / design.DESIGN_RECORD_PATH).read_bytes()

    assert observed == expected


def test_complete_design_validation() -> None:
    result = design.validate(REPO_ROOT)

    assert result["status"] == "P4_P5_REPETITION_AUTHORIZATION_DESIGN_VALID"
    assert result["authorization_scope"] == "P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"
    assert result["maximum_model_requests"] == 6
    assert result["maximum_worker_starts"] == 6
    assert result["maximum_model_loads"] == 6
    assert result["maximum_hidden_retries"] == 0
    assert result["durable_platform_observation_required"] is True
    assert result["observation_precedes_save_and_run_all"] is True
    assert result["control_repetition_count"] == 1
    assert result["treatment_repetition_count"] == 24
    assert result["observations_per_condition"] == 3
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
