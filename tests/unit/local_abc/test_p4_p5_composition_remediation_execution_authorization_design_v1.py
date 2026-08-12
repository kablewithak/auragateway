from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    p4_p5_composition_remediation_execution_authorization_design_v1 as design,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_design_binds_exact_merged_authorities() -> None:
    record = design.build_record(REPO_ROOT)
    observed = {authority.role: authority.sha256 for authority in record.authorities}

    assert observed == {
        "merged_remediated_runtime": (
            "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
        ),
        "implementation_review": (
            "feecd56b5688bffb2a79369bd28f351756c8ae78f3f1c4c38dfd9365831eb76c"
        ),
        "implementation_record": (
            "681b0463488f50d48c43b2256a0a50f0f276f10cc46c479db65c0c6e385970f8"
        ),
    }


def test_design_freezes_full_runtime_execution_budget() -> None:
    budget = design.build_record(REPO_ROOT).execution_budget

    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_save_and_run_all_actions == 1
    assert budget.maximum_runtime_install_attempts == 1
    assert budget.maximum_runtime_import_closure_probes == 1
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 3
    assert budget.maximum_model_loads == 3
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_workers == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_benchmark_trajectory_requests == 0
    assert budget.maximum_external_spend == 0


def test_design_freezes_full_p5_p6_acceptance_contract() -> None:
    qualification = design.build_record(REPO_ROOT).qualification

    assert qualification.structured_request_roles == (
        "BASE_COLD",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    )
    assert qualification.structured_request_count == 6
    assert qualification.all_structured_requests_exact_object_required
    assert qualification.p5_state_required == "PASS"
    assert qualification.p6_state_required == "PASS"
    assert qualification.cache_specific_proof_required
    assert qualification.p6_isolation_proof_required
    assert qualification.pre_request_token_identity_journal_required
    assert qualification.exact_action_budget_required
    assert qualification.teardown_state_required == "PASSED"
    assert qualification.scratch_cleanup_state_required == "PASSED"
    assert not qualification.standalone_a_r_differential_required
    assert not qualification.case_c_authorized


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

    assert evidence.expected_evidence_zip == "ag-p5-p6-transaction-bound-evidence-v1.zip"
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
    assert not record.case_c_authorized


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

    assert result["status"] == "P4_P5_REMEDIATION_AUTHORIZATION_DESIGN_VALID"
    assert result["authorization_scope"] == "P4_P5_COMPOSITION_REMEDIATION_CONFIRMATION_V1"
    assert result["maximum_model_requests"] == 6
    assert result["maximum_worker_starts"] == 3
    assert result["maximum_model_loads"] == 3
    assert result["maximum_hidden_retries"] == 0
    assert result["durable_platform_observation_required"] is True
    assert result["observation_precedes_save_and_run_all"] is True
    assert result["structured_request_count"] == 6
    assert result["p5_state_required"] == "PASS"
    assert result["p6_state_required"] == "PASS"
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
    assert binding.qualification_contract_bound
    assert binding.required_platform_policy_bound
    assert binding.authorization_window_bound
