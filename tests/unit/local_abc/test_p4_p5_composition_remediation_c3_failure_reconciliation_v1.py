from pathlib import Path

from auragateway.local_abc import (
    p4_p5_composition_remediation_c3_failure_reconciliation_v1 as reconciliation,
)


def test_build_record_captures_valid_governed_remediation_failure() -> None:
    root = Path(__file__).resolve().parents[3]
    record = reconciliation.build_record(root)

    assert record.transaction_id == reconciliation.TRANSACTION_ID
    assert record.saved_version_id == 341956898
    assert record.status == "RECONCILED_VALID_GOVERNED_REMEDIATION_FAILURE"
    assert record.technical_first_divergence == "C3"
    assert record.technical_failure_class == "REQUEST_EXECUTION_FAILURE"
    assert record.completed_capabilities == ("C1", "C2")
    assert record.remediated_runtime_identity_verified is True
    assert record.remediation_instruction_replacement_present is True
    assert record.historical_v5_tail_absent is True
    assert record.first_request_role == "BASE_COLD"
    assert record.first_request_prefix_variant == "A"
    assert record.first_request_token_count == 899
    assert record.pre_request_identity_persisted_before_model_request is True
    assert record.model_requests_performed == 1
    assert record.hidden_retries_performed == 0
    assert record.teardown_passed is True
    assert record.scratch_cleanup_passed is True


def test_reconciliation_refuses_to_overclaim_failed_remediation() -> None:
    root = Path(__file__).resolve().parents[3]
    record = reconciliation.build_record(root)

    assert record.full_remediation_confirmation_established is False
    assert record.v5_tail_replacement_sufficient_remediation is False
    assert record.composition_regression_family_remains_unresolved is True
    assert record.remaining_composition_subfactor_identified is False
    assert record.p5_reached is False
    assert record.p6_reached is False
    assert record.p5_failure_established is False
    assert record.p6_failure_established is False
    assert record.exact_failed_model_output_known is False
    assert record.runtime_incompatibility_established is False
    assert record.general_model_unreliability_established is False
    assert record.guided_decoding_fix_authorized is False
    assert record.new_execution_authorized is False
    assert record.authorization_reusable is False
    assert record.unchanged_replay_authorized is False


def test_expected_outputs_are_canonical_and_review_is_bound() -> None:
    root = Path(__file__).resolve().parents[3]
    record_bytes, review_bytes = reconciliation.expected_outputs(root)

    assert record_bytes.endswith(b"\n")
    assert review_bytes.endswith(b"\n")
    assert b'"causal_classification":"REMEDIATION_INTERVENTION_INSUFFICIENT"' in record_bytes
    assert b'"v5_tail_replacement_sufficient_remediation":false' in record_bytes
    assert b'"p5_failure_established":false' in record_bytes
    assert b'"p6_failure_established":false' in record_bytes
    assert b'"new_execution_authorized":false' in review_bytes
    assert reconciliation.CUSTODY_MANIFEST_SHA256.encode("ascii") in review_bytes
