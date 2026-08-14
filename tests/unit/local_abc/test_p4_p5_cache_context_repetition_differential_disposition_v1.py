from pathlib import Path

from auragateway.local_abc import (
    p4_p5_cache_context_repetition_differential_disposition_v1 as disposition,
)


def test_build_record_accepts_governed_positive_repetition_differential() -> None:
    root = Path(__file__).resolve().parents[3]
    record = disposition.build_record(root)

    assert record.transaction_id == disposition.TRANSACTION_ID
    assert record.saved_version_id == 342415694
    assert record.status == "DISPOSITIONED_VALID_GOVERNED_REPETITION_DIFFERENTIAL"
    assert record.decision_state == "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"
    assert record.variable_under_test == "CACHE_CONTEXT_REPETITION_COUNT"
    assert record.control_repetition_count == 1
    assert record.treatment_repetition_count == 24
    assert record.control_exact_object_count == 3
    assert record.treatment_exact_object_count == 0
    assert record.treatment_historical_identity_matched is True
    assert record.fresh_worker_process_per_observation is True
    assert record.worker_identity_cardinality == 6
    assert record.model_requests_performed == 6
    assert record.model_loads_performed == 6
    assert record.worker_starts_performed == 6
    assert record.hidden_retries_performed == 0
    assert record.teardown_passed is True
    assert record.scratch_cleanup_passed is True


def test_disposition_preserves_claim_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    record = disposition.build_record(root)

    assert record.long_repeated_24x_condition_necessary_relative_to_1x_established is True
    assert record.exact_repetition_threshold_established is False
    assert record.repetition_alone_established_causal is False
    assert record.context_length_alone_established_causal is False
    assert record.exact_root_cause_established is False
    assert record.prefix_cache_defect_established is False
    assert record.p5_requalified is False
    assert record.p6_requalified is False
    assert record.measured_abc_execution_performed is False
    assert record.new_execution_authorized is False
    assert record.authorization_reusable is False
    assert record.unchanged_replay_authorized is False


def test_expected_outputs_are_canonical_and_review_is_bound() -> None:
    root = Path(__file__).resolve().parents[3]
    record_bytes, review_bytes = disposition.expected_outputs(root)

    assert record_bytes.endswith(b"\n")
    assert review_bytes.endswith(b"\n")
    assert b'"decision_state":"LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"' in record_bytes
    assert b'"control_exact_object_count":3' in record_bytes
    assert b'"treatment_exact_object_count":0' in record_bytes
    assert b'"exact_repetition_threshold_established":false' in record_bytes
    assert b'"exact_root_cause_established":false' in record_bytes
    assert b'"new_execution_authorized":false' in review_bytes
    assert disposition.CUSTODY_MANIFEST_SHA256.encode("ascii") in review_bytes


def test_static_validate_matches_checked_in_generated_outputs() -> None:
    root = Path(__file__).resolve().parents[3]
    result = disposition.validate(root)

    assert result["status"] == "P4_P5_REPETITION_DIFFERENTIAL_DISPOSITION_VALID"
    assert result["decision_state"] == "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"
    assert result["exact_repetition_threshold_established"] is False
    assert result["exact_root_cause_established"] is False
    assert result["p5_requalified"] is False
    assert result["p6_requalified"] is False
    assert result["new_execution_authorized"] is False
    assert result["next_gate"] == disposition.NEXT_GATE
