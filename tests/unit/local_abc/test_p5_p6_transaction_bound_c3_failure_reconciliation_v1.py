from __future__ import annotations

from pathlib import Path

from auragateway.local_abc.p5_p6_transaction_bound_c3_failure_reconciliation_v1 import (
    CUSTODY_MANIFEST_SHA256,
    NEXT_GATE,
    build_record,
    validate,
)

ROOT = Path(__file__).resolve().parents[3]


def test_reconciliation_classifies_composition_seam() -> None:
    record = build_record(ROOT)

    assert record.primary_classification == ("P4_P5_COMPOSITION_OUTPUT_CONTRACT_REGRESSION")
    assert record.specific_classification == (
        "QUALIFIED_CASE_A_REUSED_AFTER_MATERIAL_MESSAGE_CONTEXT_CHANGE"
    )
    assert record.historical_failure_family_match is True
    assert record.historical_p4_case_a_selected is True
    assert record.historical_p4_case_a_qualified is True
    assert record.current_composition_uses_v4_system_prompt is True
    assert record.current_composition_uses_v5_derived_cache_context is True
    assert record.material_message_context_change_established is True


def test_reconciliation_preserves_governance_boundary() -> None:
    record = build_record(ROOT)

    assert record.governance_disposition == ("ACCEPTED_INVALID_SINGLE_USE_TRANSACTION")
    assert record.technical_evidence_disposition == (
        "ACCEPTED_TECHNICAL_DIAGNOSTIC_FAILURE_EVIDENCE"
    )
    assert record.technical_first_divergence == "C3"
    assert record.duplicate_saved_execution_observed is True
    assert record.single_use_acceptance_valid is False
    assert record.authorization_reusable is False
    assert record.unchanged_replay_authorized is False
    assert record.runtime_fix_authorized is False
    assert record.new_execution_authorized is False


def test_reconciliation_does_not_promote_downstream_failures() -> None:
    record = build_record(ROOT)

    assert record.runtime_incompatibility_established is False
    assert record.model_construction_failure_established is False
    assert record.worker_startup_failure_established is False
    assert record.p5_failure_established is False
    assert record.p6_failure_established is False
    assert record.exact_failed_model_output_known is False


def test_reconciliation_custody_and_next_gate_are_frozen() -> None:
    record = build_record(ROOT)

    assert CUSTODY_MANIFEST_SHA256 == (
        "3ca422790bdb6ff2a57c922e33f3fd7df01226d71e122f77234400a088c82103"
    )
    assert record.next_gate == NEXT_GATE
    assert NEXT_GATE == "DESIGN_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1"


def test_generated_reconciliation_package_validates() -> None:
    result = validate(ROOT)

    assert result["status"] == "P5_P6_C3_FAILURE_RECONCILIATION_VALID"
    assert result["runtime_fix_authorized"] is False
    assert result["new_execution_authorized"] is False
    assert result["next_gate"] == NEXT_GATE
