from __future__ import annotations

from pathlib import Path

import pytest

from auragateway.local_abc import c4_mechanism_admission_assessment_v1 as assessment

REPO_ROOT = Path(__file__).resolve().parents[3]


def qualified_observation() -> assessment.MechanismObservation:
    return assessment.MechanismObservation(
        execution_valid=True,
        observation_count=3,
        http_200_count=3,
        finish_reason_stop_count=3,
        zero_cache_baseline_count=3,
        worker_identity_cardinality=3,
        full_prompt_token_count=899,
        reusable_prefix_token_count=880,
        hidden_retries=0,
        teardown_passed=True,
        scratch_cleanup_passed=True,
        failure_report_not_applicable=True,
        runtime_identity_bound=True,
        request_identity_bound=True,
        evidence_identity_bound=True,
        output_provenance_present=True,
    )


def test_build_all_preserves_semantic_failure_and_assesses_mechanism() -> None:
    contract_payload, record_payload, review_payload = assessment.build_all(REPO_ROOT)

    contract = assessment.QualificationContract.model_validate_json(contract_payload)
    record = assessment.AssessmentRecord.model_validate_json(record_payload)
    review = assessment.AssessmentReview.model_validate_json(review_payload)

    assert contract.semantic_exact_object_blocking is False
    assert contract.valid_json_blocking is False
    assert contract.model_semantics_permitted_as_p6_route_proof is False

    assert record.semantic_observation.state == "NOT_QUALIFIED"
    assert record.semantic_c4_relabelled is False
    assert (
        record.mechanism_decision.state
        == assessment.MechanismAdmissionState.QUALIFIED
    )
    assert record.p5_requalified is False
    assert record.p6_requalified is False
    assert record.model_requests_performed == 0
    assert record.new_execution_authorized is False

    assert review.semantic_c4_state == "NOT_QUALIFIED"
    assert (
        review.mechanism_admission_state
        == assessment.MechanismAdmissionState.QUALIFIED
    )
    assert review.p5_requalified_claimed is False
    assert review.p6_requalified_claimed is False


def test_semantic_fields_are_not_inputs_to_mechanism_classifier() -> None:
    observation = qualified_observation()

    decision = assessment.assess_mechanism(observation)

    assert decision.state == assessment.MechanismAdmissionState.QUALIFIED
    assert not hasattr(observation, "exact_object_count")
    assert not hasattr(observation, "valid_json_count")


def test_hidden_retry_blocks_mechanism_admission() -> None:
    observation = qualified_observation().model_copy(update={"hidden_retries": 1})

    decision = assessment.assess_mechanism(observation)

    assert decision.state == assessment.MechanismAdmissionState.NOT_QUALIFIED
    assert "hidden_retries_nonzero" in decision.blocking_failures


def test_transport_failure_blocks_mechanism_admission() -> None:
    observation = qualified_observation().model_copy(update={"http_200_count": 2})

    decision = assessment.assess_mechanism(observation)

    assert decision.state == assessment.MechanismAdmissionState.NOT_QUALIFIED
    assert "http_200_count_mismatch" in decision.blocking_failures


def test_token_geometry_drift_blocks_mechanism_admission() -> None:
    observation = qualified_observation().model_copy(
        update={"reusable_prefix_token_count": 879}
    )

    decision = assessment.assess_mechanism(observation)

    assert decision.state == assessment.MechanismAdmissionState.NOT_QUALIFIED
    assert "reusable_prefix_token_count_mismatch" in decision.blocking_failures


def test_missing_worker_identity_is_ambiguous() -> None:
    observation = qualified_observation().model_copy(
        update={"worker_identity_cardinality": None}
    )

    decision = assessment.assess_mechanism(observation)

    assert decision.state == assessment.MechanismAdmissionState.AMBIGUOUS
    assert "worker_identity_cardinality=NOT_OBSERVED" in decision.ambiguous_reasons


def test_explicit_failure_beats_other_ambiguity() -> None:
    observation = qualified_observation().model_copy(
        update={
            "worker_identity_cardinality": None,
            "execution_valid": False,
        }
    )

    decision = assessment.assess_mechanism(observation)

    assert decision.state == assessment.MechanismAdmissionState.NOT_QUALIFIED
    assert "execution_valid=false" in decision.blocking_failures
    assert "worker_identity_cardinality=NOT_OBSERVED" in decision.ambiguous_reasons


def test_contract_does_not_preprove_p5_or_p6() -> None:
    frozen = assessment.contract(REPO_ROOT)
    by_id = {item.requirement_id: item for item in frozen.requirements}

    assert by_id["P5-OBS"].blocking_for_mechanism_admission is False
    assert by_id["P6-OBS"].blocking_for_mechanism_admission is False
    assert (
        by_id["P5-OBS"].requirement_class
        == assessment.RequirementClass.DOWNSTREAM_P5_MEASUREMENT
    )
    assert (
        by_id["P6-OBS"].requirement_class
        == assessment.RequirementClass.DOWNSTREAM_P6_MEASUREMENT
    )


def test_proof_basis_keeps_model_semantics_out_of_p6_route_proof() -> None:
    basis = assessment.proof_basis(REPO_ROOT)

    assert basis.p5_latency_as_primary_proof_permitted is False
    assert basis.p6_model_semantics_as_route_proof_permitted is False


def test_require_sha_rejects_byte_drift(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(assessment.AssessmentError):
        assessment.require_sha(tmp_path, Path("authority.json"), "0" * 64)
