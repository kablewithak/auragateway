from pathlib import Path

from auragateway.local_abc import (
    p4_p5_token_count_matched_context_structure_differential_disposition_v1 as disposition,
)


def test_build_record_accepts_governed_token_matched_result() -> None:
    root = Path(__file__).resolve().parents[3]
    record = disposition.build_record(root)

    assert record.transaction_id == disposition.TRANSACTION_ID
    assert record.saved_version_id == 342834146
    assert record.condition_a_exact_object_count == 0
    assert record.condition_b_exact_object_count == 0
    assert record.condition_c_exact_object_count == 3
    assert record.anchor_reproduced is True
    assert record.mechanistic_inference_permitted is True
    assert record.worker_identity_cardinality == 9
    assert record.model_requests_performed == 9
    assert record.model_loads_performed == 9
    assert record.worker_starts_performed == 9
    assert record.hidden_retries_performed == 0


def test_disposition_accepts_only_bounded_mechanistic_claim() -> None:
    root = Path(__file__).resolve().parents[3]
    record = disposition.build_record(root)

    assert record.high_exact_token_pattern_repetition_strongly_implicated is True
    assert record.exact_repetition_sole_cause_established is False
    assert record.semantic_amplification_sole_cause_established is False
    assert record.exact_repetition_threshold_established is False
    assert record.context_length_alone_established_causal is False
    assert record.exact_root_cause_established is False
    assert record.prefix_cache_defect_established is False
    assert record.b_to_c_residual_lexical_novelty_bounded is True


def test_disposition_preserves_terminal_and_nonclaim_boundaries() -> None:
    root = Path(__file__).resolve().parents[3]
    record = disposition.build_record(root)

    assert record.terminal_disposition == "CONSUMED"
    assert record.execution_outcome == "PASSED"
    assert record.authorization_reusable is False
    assert record.unchanged_replay_authorized is False
    assert record.new_execution_authorized is False
    assert record.p5_requalified is False
    assert record.p6_requalified is False
    assert record.measured_abc_execution_performed is False


def test_expected_outputs_are_canonical_and_review_is_bound() -> None:
    root = Path(__file__).resolve().parents[3]
    record_bytes, review_bytes = disposition.expected_outputs(root)

    assert record_bytes.endswith(b"\n")
    assert review_bytes.endswith(b"\n")
    assert (
        b'"decision_state":'
        b'"HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"' in record_bytes
    )
    assert b'"condition_a_exact_object_count":0' in record_bytes
    assert b'"condition_b_exact_object_count":0' in record_bytes
    assert b'"condition_c_exact_object_count":3' in record_bytes
    assert b'"exact_repetition_sole_cause_established":false' in record_bytes
    assert b'"new_execution_authorized":false' in review_bytes
    custody_sha = disposition.CUSTODY_MANIFEST_SHA256.encode("ascii")
    assert custody_sha in review_bytes


def test_static_validate_matches_checked_in_outputs() -> None:
    root = Path(__file__).resolve().parents[3]
    result = disposition.validate(root)

    assert result["status"] == ("P4_P5_TOKEN_MATCHED_DIFFERENTIAL_DISPOSITION_VALID")
    assert result["condition_a_exact_object_count"] == 0
    assert result["condition_b_exact_object_count"] == 0
    assert result["condition_c_exact_object_count"] == 3
    assert result["authorization_reusable"] is False
    assert result["new_execution_authorized"] is False
    assert result["next_gate"] == disposition.NEXT_GATE
