from pathlib import Path

from auragateway.local_abc import (
    p4_p5_composition_differential_terminalization_reconciliation_v1 as reconciliation,
)


def test_build_record_preserves_result_and_provenance_gap() -> None:
    root = Path(__file__).resolve().parents[3]
    record = reconciliation.build_record(root)

    assert record.transaction_id == reconciliation.TRANSACTION_ID
    assert record.saved_version_id == 341807938
    assert record.diagnostic_execution_status == "DIAGNOSTIC_COMPLETE"
    assert record.diagnostic_decision == "COMPOSITION_REGRESSION_SUPPORTED"
    assert record.variable_under_test == "MESSAGE_COMPOSITION_ONLY"
    assert record.case_a_exact_successes == 3
    assert record.case_b_exact_successes == 0
    assert record.case_a_valid_json_count == 3
    assert record.case_b_valid_json_count == 0
    assert record.controlled_differential_evidence_established is True
    assert record.scientific_result_valid is True
    assert record.diagnostic_result_invalidated is False
    assert record.platform_observed_at is None
    assert record.platform_observation_timestamp_recoverable is False
    assert record.terminalization_timestamp_fabricated is False
    assert record.original_issuer_terminalization_completed is False
    assert record.original_issuer_lifecycle_closed is False
    assert record.operational_authority_closed_by_reconciliation is True
    assert record.authorization_reuse_permitted is False
    assert record.rerun_permitted is False
    assert record.case_c_authorized is False
    assert record.runtime_remediation_authorized is False
    assert record.new_execution_authorized is False
    assert record.next_gate == "DESIGN_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1"


def test_expected_outputs_are_canonical_and_review_is_bound() -> None:
    root = Path(__file__).resolve().parents[3]
    record_bytes, review_bytes = reconciliation.expected_outputs(root)

    assert record_bytes.endswith(b"\n")
    assert review_bytes.endswith(b"\n")
    assert b"COMPOSITION_REGRESSION_SUPPORTED" in record_bytes
    assert b"APPROVED_RECONCILIATION_WITH_EXPLICIT_PROVENANCE_GAP" in review_bytes
    assert reconciliation.EXPECTED_EVIDENCE_SHA256.encode("ascii") in record_bytes
    assert b'"new_execution_authorized":false' in record_bytes
