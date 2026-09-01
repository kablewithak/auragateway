from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    final_342_g1114d_terminal_reconciliation_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def test_reconciliation_preserves_historical_receipt_and_corrects_acceptance() -> None:
    record = subject.build_record(ROOT)

    assert record.historical_terminal_disposition == "CONSUMED"
    assert record.historical_terminal_execution_outcome == "PASSED"
    assert record.historical_terminal_receipt_preserved is True

    assert record.functional_execution_outcome == "PASSED"
    assert record.governed_teardown_outcome == "FAILED"
    assert record.overall_governed_execution_outcome == "FAILED"

    assert record.terminal_receipt_classification_conflict is True
    assert record.historical_terminal_outcome_superseded_for_governed_acceptance is True


def test_reconciliation_binds_complete_functional_workload_evidence() -> None:
    record = subject.build_record(ROOT)

    assert record.request_reconciliation_passed is True
    assert record.trajectory_terminal_count == 342
    assert record.completed_trajectory_count == 342

    assert record.primary_failure_present is False
    assert record.secondary_failure_count == 1
    assert record.secondary_failure_phase == "teardown"
    assert record.secondary_failure_code == "FINAL_342_TEARDOWN_FAILURE"
    assert record.secondary_failure_safe_message == "ValidationError"

    assert record.worker_teardown_record_count == 0
    assert record.scratch_cleanup_status == "PASSED"
    assert record.scratch_absent is True


def test_reconciliation_classifies_latent_schema_adapter_defect() -> None:
    record = subject.build_record(ROOT)

    assert record.remediation_effect_class == "LATENT_DOWNSTREAM_DEFECT_REVEALED"
    assert record.root_cause_classification == (
        "P5_P6_TEARDOWN_REPORT_TO_PRODUCER_FIELD_MAPPING_MISMATCH"
    )
    assert record.root_cause_confidence == (
        "HIGH_ARCHITECTURAL_INFERENCE_NOT_RUNTIME_TEARDOWN_PROOF"
    )
    assert record.repair_implemented is True
    assert record.scientific_contract_changed is False


def test_reconciliation_does_not_promote_unobserved_teardown_or_effect_claims() -> None:
    record = subject.build_record(ROOT)

    assert record.actual_worker_teardown_pass_established is False
    assert record.effect_claims_permitted is False
    assert record.authorization_reusable is False
    assert record.unchanged_replay_authorized is False
    assert record.new_execution_authorized is False


def test_generated_reconciliation_package_validates() -> None:
    result = subject.validate(ROOT)

    assert result["status"] == ("FINAL_342_G1114D_TERMINAL_RECONCILIATION_VALID")
    assert result["historical_terminal_receipt_preserved"] is True
    assert result["corrected_governed_execution_outcome"] == "FAILED"
    assert result["effect_claims_permitted"] is False
    assert result["authorization_reusable"] is False
    assert result["new_execution_authorized"] is False
    assert result["next_gate"] == subject.NEXT_GATE
