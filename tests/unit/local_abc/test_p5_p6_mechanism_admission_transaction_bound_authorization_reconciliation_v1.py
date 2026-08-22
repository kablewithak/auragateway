from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    p5_p6_mechanism_admission_transaction_bound_authorization_reconciliation_v1 as subject,
)


def test_reconciliation_separates_behavioral_and_authorization_predecessors() -> None:
    record = subject.build_record()
    assert record.behavioral_predecessor == "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"
    assert record.authorization_predecessor == "TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1"


def test_transaction_bound_topology_restored_without_weakening_authority() -> None:
    record = subject.build_record()
    architecture = record.authorization_architecture
    assert architecture.decision == "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
    assert architecture.authorization_specific_kaggle_inputs == 0
    assert architecture.authorization_producer_notebooks == 0
    assert architecture.manual_confirmation_json_files == 0
    assert architecture.runtime_authorization_filename_discovery_permitted is False
    assert architecture.operator_confirmation_method == "RETYPE_DYNAMIC_SHA256_CHALLENGE"
    assert architecture.durable_platform_observation_required is True
    assert architecture.observation_mounted_as_runtime_input is False


def test_mechanism_admission_semantics_are_preserved() -> None:
    record = subject.build_record()
    boundary = record.preserved_mechanism_boundary
    assert boundary.semantic_states == (
        "EXACT_MATCH",
        "VALID_JSON_MISMATCH",
        "NON_OBJECT_JSON",
        "INVALID_JSON",
    )
    assert boundary.semantic_mismatch_blocks_mechanism is False
    assert boundary.invalid_json_blocks_mechanism is False
    assert boundary.finish_reason_stop_required is True
    assert boundary.p5_uses_semantic_state is False
    assert boundary.p6_uses_semantic_state is False
    assert boundary.p5_acceptance_relaxed is False
    assert boundary.p6_acceptance_relaxed is False


def test_pr291_transport_is_preserved_but_not_current_authority() -> None:
    record = subject.build_record()
    topology = record.superseded_topology
    assert topology.disposition == "IMPLEMENTED_BUT_SUPERSEDED_BEFORE_LIVE_ISSUANCE"
    assert topology.historical_files_preserved is True
    assert topology.live_authorization_issued is False
    assert topology.reuse_as_current_authority_permitted is False


def test_execution_budget_stays_bounded() -> None:
    budget = subject.build_record().execution_budget
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 3
    assert budget.maximum_model_loads == 3
    assert budget.maximum_hidden_retries == 0


def test_static_reconciliation_does_not_authorize_execution() -> None:
    record = subject.build_record()
    assert record.live_authorization_issued is False
    assert record.runtime_execution_authorized is False
    assert record.kaggle_execution_performed is False
    assert record.gpu_execution_performed is False
    assert record.model_requests_performed == 0


def test_review_binds_canonical_record() -> None:
    record = subject.build_record()
    review = subject.build_review(record)
    expected = subject._sha256(subject._canonical_json_bytes(record.model_dump(mode="json")))
    assert review.design_record_sha256 == expected
    assert review.transaction_bound_architecture_valid is True
    assert review.mechanism_semantics_preserved is True


def test_next_gate_is_implementation_only() -> None:
    assert (
        subject.build_record().next_gate
        == "IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_V1"
    )
    assert (
        Path(
            "benchmarks/local_abc/"
            "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_"
            "reconciliation_v1.json"
        )
        == subject.RECORD_PATH
    )
