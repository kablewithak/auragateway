from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import final_342_execution_producer_closure_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def test_closure_covers_exactly_ten_g11_3a_obligations() -> None:
    record = subject.build_record(ROOT)

    assert tuple(item.obligation_id for item in record.obligation_decisions) == (
        subject.OBLIGATION_IDS
    )
    assert len(record.obligation_decisions) == 10


def test_closure_has_nine_successors_and_one_explicit_exclusion() -> None:
    record = subject.build_record(ROOT)
    bounded = [
        item
        for item in record.obligation_decisions
        if item.disposition is subject.ClosureDisposition.BOUNDED_SUCCESSOR_REQUIRED
    ]
    excluded = [
        item
        for item in record.obligation_decisions
        if item.disposition is subject.ClosureDisposition.EXPLICITLY_OUT_OF_SCOPE
    ]

    assert len(bounded) == 9
    assert len(excluded) == 1
    assert excluded[0].obligation_id == "pricing_scope_and_cost_claim_mapping"
    assert excluded[0].successor_boundary is None


def test_cost_scope_excludes_monetary_claim_without_relaxing_spend_ceiling() -> None:
    cost = subject.build_record(ROOT).cost_scope

    assert cost.monetary_cost_comparison_in_scope is False
    assert cost.monetary_cost_effect_claims_permitted is False
    assert cost.external_spend_ceiling == 0
    assert cost.accepted_local_monetary_pricing_schedule_bound is False
    assert cost.mechanism_and_latency_reporting_unchanged is True


def test_three_boundaries_own_every_bounded_obligation_once() -> None:
    record = subject.build_record(ROOT)
    boundaries = record.implementation_boundaries

    assert tuple(item.boundary_id for item in boundaries) == (
        subject.BoundaryId.EXECUTION_PRODUCER,
        subject.BoundaryId.PROTECTED_REVIEW,
        subject.BoundaryId.ANALYSIS_CONTRACTS,
    )

    owned = [obligation for boundary in boundaries for obligation in boundary.owns_obligations]
    bounded = [
        item.obligation_id
        for item in record.obligation_decisions
        if item.disposition is subject.ClosureDisposition.BOUNDED_SUCCESSOR_REQUIRED
    ]

    assert len(owned) == len(set(owned))
    assert set(owned) == set(bounded)


def test_execution_boundary_rejects_direct_v2_copy_and_full_rewrite() -> None:
    record = subject.build_record(ROOT)
    forest = record.forest_constraint

    assert forest.general_benchmark_platform_build_permitted is False
    assert forest.full_runtime_rewrite_required is False
    assert forest.direct_v2_runtime_copy_permitted is False
    assert forest.accepted_mechanics_reused_when_semantics_match is True

    v2_transport = next(
        item
        for item in record.obligation_decisions
        if item.obligation_id == "final_request_transport_and_worker_startup"
    )
    assert v2_transport.successor_boundary is subject.BoundaryId.EXECUTION_PRODUCER
    assert subject.V2_REQUEST_ADAPTER_PATH.as_posix() in v2_transport.reuse_sources


def test_persistence_contract_is_monotonic_and_failure_preserving() -> None:
    contract = subject.build_record(ROOT).persistence_contract

    assert contract.phases == (
        "transaction_admission",
        "request_attempt_reservation",
        "transport_outcome",
        "telemetry_and_output_admission",
        "state_mutation_decision",
        "trajectory_terminal_state",
        "worker_teardown",
        "scratch_cleanup",
        "evidence_packaging",
        "authorization_terminalization",
    )
    assert contract.persist_phase_truth_before_next_fallible_phase is True
    assert contract.first_causal_failure_preserved is True
    assert contract.secondary_failure_may_mask_primary is False
    assert contract.later_enrichment_may_erase_prior_truth is False


def test_source_contracts_capture_retry_and_pricing_boundary() -> None:
    subject._validate_source_contracts(ROOT)

    request_adapter = subject._read_bytes(ROOT, subject.V2_REQUEST_ADAPTER_PATH).decode("utf-8")
    fingerprints = subject._read_object(ROOT, subject.PREFLIGHT_FINGERPRINTS_PATH)

    assert "with no retry path" in request_adapter
    assert fingerprints["pricing_fields_present"] is False
    assert fingerprints["provider_fields_present"] is False


def test_closure_remains_non_authorizing_and_non_freezing() -> None:
    state = subject.build_record(ROOT).safety_state

    assert state.producer_obligation_classification_complete is True
    assert state.final_producer_implementation_complete is False
    assert state.complete_offline_producer_rehearsal_established is False
    assert state.manifest_freeze_permitted is False
    assert state.execution_manifest_frozen is False
    assert state.final_measured_abc_execution_authorized is False
    assert state.new_execution_authorized is False
    assert state.effect_claims_permitted is False
    assert state.model_requests_performed == 0
    assert state.gpu_execution_performed is False
    assert state.kaggle_execution_performed is False


def test_repository_record_regenerates_exactly() -> None:
    result = subject.validate_repository(ROOT)

    assert result["status"] == "FINAL_342_EXECUTION_PRODUCER_CLOSURE_V1_VALID"
    assert result["producer_obligation_count"] == 10
    assert result["bounded_successor_obligation_count"] == 9
    assert result["out_of_scope_obligation_count"] == 1
    assert result["implementation_boundary_count"] == 3
    assert result["monetary_cost_comparison_in_scope"] is False
    assert result["external_spend_ceiling"] == 0
    assert result["manifest_freeze_permitted"] is False
    assert result["next_gate"] == "IMPLEMENT_FINAL_342_EXECUTION_PRODUCER_V1"
