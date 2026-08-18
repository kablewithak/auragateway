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
        "canonical_synthetic_prefix_c4_single_use_execution_authorization_design_v1"
    ),
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_design_binds_exact_c4_authorities() -> None:
    record = design.build_record(REPO_ROOT)
    observed = {authority.role: authority.sha256 for authority in record.authorities}
    assert observed == {
        "frozen_qualification_request": (
            "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884"
        ),
        "frozen_qualification_review": (
            "ff1ecb531db85cfacab26db9f546fdc981292dd3feb2da6934a3e74c712286bc"
        ),
        "reusable_prefix_identity_receipt": (
            "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835"
        ),
        "merged_successor_runtime": (
            "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
        ),
        "implementation_review": (
            "d5bbb90fbf171ad3c38e713b9aa71e2fd6dbc39254236933dcdf446e824d9452"
        ),
        "implementation_record": (
            "7e5d102ed485279f0d8efd344529ec92b96e97a858b68652518a0472aeb9665a"
        ),
    }


def test_design_freezes_single_use_scope_and_three_request_budget() -> None:
    record = design.build_record(REPO_ROOT)
    budget = record.execution_budget
    assert record.authorization_architecture == "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
    assert record.authorization_scope == (
        "CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
    )
    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_save_and_run_all_actions == 1
    assert budget.maximum_runtime_install_attempts == 1
    assert budget.maximum_runtime_import_closure_probes == 1
    assert budget.maximum_model_requests == 3
    assert budget.maximum_model_loads == 3
    assert budget.maximum_worker_starts == 3
    assert budget.maximum_worker_teardowns == 3
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_requests == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_benchmark_trajectory_requests == 0
    assert budget.maximum_external_spend == 0


def test_design_freezes_c4_request_and_reusable_prefix_identities() -> None:
    qualification = design.build_record(REPO_ROOT).qualification
    assert qualification.canonical_corpus_version == "CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1"
    assert qualification.full_prompt_token_count == 899
    assert qualification.full_prompt_token_sha256 == (
        "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
    )
    assert qualification.reusable_prefix_token_count == 880
    assert qualification.reusable_prefix_token_sha256 == (
        "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
    )
    assert qualification.canonical_request_payload_sha256 == (
        "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
    )
    assert qualification.canonical_final_object == ('{"probe":"exact-runtime-p5-p6","value":1}')


def test_design_freezes_behavioral_qualification_contract() -> None:
    qualification = design.build_record(REPO_ROOT).qualification
    assert qualification.observation_count == 3
    assert qualification.exact_pass_count_required == 3
    assert qualification.one_request_per_worker
    assert qualification.fresh_worker_per_observation
    assert qualification.zero_cached_prefix_baseline_required
    assert qualification.teardown_after_each_observation
    assert qualification.healthy_behavioral_failure_completes_all_observations
    assert qualification.execution_invalidating_failure_stops_without_replacement
    assert qualification.strict_duplicate_key_rejection
    assert qualification.strict_integer_value_validation
    assert qualification.finish_reason_stop_required
    assert not qualification.threshold_relaxation_permitted
    assert qualification.hidden_retries_permitted == 0
    assert qualification.replacement_requests_permitted == 0
    assert qualification.terminal_states == (
        "QUALIFIED",
        "NOT_QUALIFIED",
        "INVALID_EXECUTION",
    )


def test_design_freezes_generation_contract_and_rejects_drift() -> None:
    qualification = design.build_record(REPO_ROOT).qualification
    assert qualification.message_roles == ("system", "user", "assistant", "user")
    assert qualification.maximum_output_tokens == 32
    assert qualification.temperature == 0
    assert qualification.top_p == 1
    assert qualification.repetition_penalty == 1.1
    assert qualification.seed == 7
    assert not qualification.stream
    assert not qualification.response_format_present
    assert not qualification.guided_decoding_present
    assert not qualification.schema_enforcement_present
    with pytest.raises(ValidationError):
        design.QualificationContract(repetition_penalty=1.2)


def test_design_requires_fresh_human_authority_and_platform_receipt() -> None:
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


def test_design_preserves_transaction_transport_and_single_use_terminalization() -> None:
    record = design.build_record(REPO_ROOT)
    topology = record.transport_topology
    identity = record.transaction_identity
    terminal = record.terminalization
    assert topology.authorization_specific_kaggle_inputs == 0
    assert topology.authorization_producer_notebooks == 0
    assert topology.manual_confirmation_json_files == 0
    assert not topology.runtime_authorization_filename_discovery_permitted
    assert topology.permitted_kaggle_input_roles == ("durable_runtime", "model_snapshot")
    assert identity.transaction_id_derivation == "SHA256_CANONICAL_AUTHORIZATION_BYTES"
    assert identity.canonical_authorization_bytes_bound
    assert identity.runtime_payload_sha256_bound
    assert identity.canonical_request_payload_sha256_bound
    assert identity.reusable_prefix_token_sha256_bound
    assert identity.nonidentical_regeneration_requires_fresh_authority
    assert terminal.attempted_execution_terminalizes_authority
    assert not terminal.terminal_authorization_reusable
    assert terminal.multiple_observed_executions_invalidate_acceptance
    assert not terminal.runtime_anti_replay_established
    assert not terminal.malicious_operator_resistance_established


def test_design_separates_runtime_observation_from_repository_acceptance() -> None:
    acceptance = design.build_record(REPO_ROOT).repository_acceptance
    assert not acceptance.runtime_decision_is_repository_acceptance
    assert acceptance.separate_acceptance_reconciliation_required
    assert acceptance.authorization_lifecycle_must_be_verified
    assert acceptance.evidence_identity_must_be_verified
    assert acceptance.saved_version_identity_must_be_verified
    assert acceptance.platform_budget_must_be_verified
    assert acceptance.runtime_identity_must_be_verified
    assert acceptance.c4_acceptance_required_before_p5_p6_successor
    assert acceptance.p5_p6_successor_must_derive_from_this_runtime


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
    assert not record.c4_qualified
    assert not record.p5_requalified
    assert not record.p6_requalified


def test_record_rendering_is_deterministic() -> None:
    assert design.render_record(REPO_ROOT) == design.render_record(REPO_ROOT)
