from __future__ import annotations

from pathlib import Path

import pytest

from auragateway.local_abc import final_342_analysis_engine_v1 as analysis
from auragateway.local_abc import (
    final_342_offline_orchestration_integration_rehearsal_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def synthetic_analysis_input() -> analysis.Final342AnalysisInput:
    return subject.build_synthetic_analysis_input(ROOT)


def test_subject_binds_merged_pipeline_without_creating_authority() -> None:
    result = subject.validate_subject(ROOT)

    assert result["status"] == "FINAL_342_OFFLINE_REHEARSAL_SUBJECT_VALID"
    assert result["planned_trajectory_count"] == 342
    assert result["functional_run_count"] == 162
    assert result["runtime_run_count"] == 180
    assert result["secondary_review_schedule_count"] == 41
    assert result["synthetic_evidence_only"] is True
    assert result["manifest_freeze_permitted"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False


def test_full_offline_rehearsal_composes_exact_population_and_remains_non_authorizing() -> None:
    result = subject.rehearse(ROOT)

    assert result.status == "FINAL_342_OFFLINE_ORCHESTRATION_INTEGRATION_REHEARSAL_PASS"
    assert result.planned_trajectory_count == 342
    assert result.producer_plan_binding_count == 342
    assert result.producer_trace_binding_count == 342
    assert result.secondary_review_schedule_count == 41
    assert result.protected_review_round_trip.capture_count == 4
    assert result.protected_review_round_trip.loaded_capture_count == 4
    assert result.protected_review_round_trip.reviewer_assignment_count == 2
    assert result.measured_quality_result_count == 162
    assert result.runtime_measurement_count == 720
    assert result.eligible_pairs_per_contrast == (60, 60, 60)
    assert result.synthetic_analysis_evidence_complete is True
    assert result.synthetic_quality_gate_passed is True
    assert result.synthetic_mechanics_claim_decisions == (
        "SUPPORTED",
        "SUPPORTED",
        "SUPPORTED",
    )
    assert result.synthetic_results_are_scientific_evidence is False
    assert result.synthetic_effect_claims_authoritative is False
    assert result.model_requests_performed == 0
    assert result.network_transport_performed is False
    assert result.execution_manifest_frozen is False
    assert result.final_measured_abc_execution_authorized is False
    assert result.effect_claims_permitted is False
    assert result.next_gate == "REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1"


def test_trace_manifest_drift_blocks_synthetic_pipeline_claims(
    synthetic_analysis_input: analysis.Final342AnalysisInput,
) -> None:
    first = synthetic_analysis_input.trace_bindings[0].model_copy(
        update={"final_execution_manifest_sha256": "0" * 64}
    )
    drifted = synthetic_analysis_input.model_copy(
        update={
            "trace_bindings": (
                first,
                *synthetic_analysis_input.trace_bindings[1:],
            )
        }
    )

    result = analysis.analyze_final_342(drifted)

    assert result.evidence_state is analysis.AnalysisEvidenceState.EVIDENCE_INCOMPLETE
    assert (
        analysis.AnalysisErrorCode.FINAL_EXECUTION_MANIFEST_MISMATCH
        in result.machine_readable_errors
    )
    assert all(item.decision is analysis.ClaimDecision.BLOCKED for item in result.claim_decisions)
