from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    p4_p5_composition_differential_execution_authorization_design_v1 as design,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_design_binds_exact_merged_authorities() -> None:
    record = design.build_record(REPO_ROOT)

    observed = {authority.role: authority.sha256 for authority in record.authorities}

    assert observed == {
        "merged_successor_runtime": (
            "4711f94031bc65ae159dab14412d99cfbd9ecee01b5a2d7d2fd7a2c2b09d7db7"
        ),
        "implementation_review": (
            "523f42b32d76ae357313f009b548703ea2da8fd9f6496cf6adb7cc50ad4ec655"
        ),
        "implementation_record": (
            "8b2b11f367b60272323cb9e6269cbb09e597063d03467207798c96b25e79b1b1"
        ),
    }


def test_design_freezes_exact_execution_budget() -> None:
    budget = design.build_record(REPO_ROOT).execution_budget

    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_save_and_run_all_actions == 1
    assert budget.maximum_runtime_install_attempts == 1
    assert budget.maximum_runtime_import_closure_probes == 1
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 1
    assert budget.maximum_model_loads == 1
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_workers == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_benchmark_trajectory_requests == 0
    assert budget.maximum_external_spend == 0


def test_design_freezes_differential_and_case_c_boundary() -> None:
    experiment = design.build_record(REPO_ROOT).experiment

    assert experiment.variable_under_test == "MESSAGE_COMPOSITION_ONLY"
    assert experiment.case_a_roles == ("system", "user")
    assert experiment.case_b_roles == (
        "system",
        "user",
        "assistant",
        "user",
    )
    assert experiment.request_order == ("A", "B", "B", "A", "A", "B")
    assert experiment.repetitions_per_case == 3

    assert experiment.a_3_of_3_b_0_of_3 == "COMPOSITION_REGRESSION_SUPPORTED"
    assert experiment.a_3_of_3_b_3_of_3 == "COMPOSITION_HYPOTHESIS_NOT_REPRODUCED"
    assert experiment.a_not_3_of_3 == "SIMPLE_CONTROL_NOT_RELIABLE"
    assert experiment.otherwise == "NON_DETERMINISTIC_OR_AMBIGUOUS"

    assert experiment.mixed_result_requires_separate_case_c_design
    assert not experiment.case_c_authorized_by_this_design
    assert not experiment.runtime_remediation_authorized


def test_design_preserves_transaction_bound_topology() -> None:
    record = design.build_record(REPO_ROOT)
    topology = record.transport_topology
    transaction = record.transaction_identity

    assert record.authorization_architecture == ("TRANSACTION_BOUND_EXECUTION_ARTIFACT")
    assert topology.authorization_specific_kaggle_inputs == 0
    assert topology.authorization_producer_notebooks == 0
    assert topology.manual_confirmation_json_files == 0
    assert not topology.runtime_authorization_filename_discovery_permitted
    assert topology.permitted_kaggle_input_roles == (
        "durable_runtime",
        "model_snapshot",
    )

    assert transaction.transaction_id_derivation == ("SHA256_CANONICAL_AUTHORIZATION_BYTES")
    assert transaction.canonical_authorization_bytes_bound
    assert transaction.runtime_payload_sha256_bound
    assert transaction.generator_contract_sha256_bound
    assert transaction.deterministic_artifact_generation_required
    assert not transaction.whole_notebook_sha256_is_semantic_payload_identity


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


def test_platform_observation_sequence_matches_transaction_architecture() -> None:
    platform = design.build_record(REPO_ROOT).platform

    assert platform.accelerator == "T4_X2"
    assert platform.allocated_gpu_count == 2
    assert not platform.internet_enabled
    assert not platform.preissuance_platform_observation_required
    assert platform.fresh_post_artifact_observation_required
    assert platform.observation_precedes_save_and_run_all
    assert not platform.observation_mounted_as_runtime_input
    assert platform.machine_observable_runtime_topology_check_required


def test_design_preserves_single_use_terminalization() -> None:
    terminal = design.build_record(REPO_ROOT).terminalization

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
    assert not record.differential_notebook_generated


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

    assert result["status"] == "P4_P5_DIFF_AUTHORIZATION_DESIGN_VALID"
    assert result["authorization_scope"] == "P4_P5_COMPOSITION_DIFFERENTIAL_V1"
    assert result["issuer_merge_commit_binding_required"] is True
    assert result["runtime_model_contract_bound"] is True
    assert result["maximum_model_requests"] == 6
    assert result["maximum_worker_starts"] == 1
    assert result["maximum_model_loads"] == 1
    assert result["maximum_hidden_retries"] == 0
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
    assert runtime.model_revision == ("7ae557604adf67be50417f59c2c2f167def9a775")
    assert runtime.tokenizer_revision == runtime.model_revision
    assert runtime.model_directory_sha256 == (
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    )


def test_future_authorization_payload_is_fully_lineage_bound() -> None:
    record = design.build_record(REPO_ROOT)
    binding = record.authorization_payload_binding

    assert record.authorization_scope == "P4_P5_COMPOSITION_DIFFERENTIAL_V1"
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
