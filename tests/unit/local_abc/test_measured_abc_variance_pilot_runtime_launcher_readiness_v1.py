from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    measured_abc_variance_pilot_runtime_launcher_readiness_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def test_runtime_request_is_current_line_and_non_authorizing() -> None:
    request = subject.build_request()
    assert request.runtime.vllm_distribution == "0.25.1+cu129"
    assert request.runtime.torch == "2.11.0+cu129"
    assert request.runtime.gpu_topology == "T4_X2"
    assert request.budget.pilot_trajectory_count == 54
    assert request.budget.pilot_turn_count == 216
    assert request.budget.maximum_request_attempt_count == 432
    assert request.telemetry_admission.preflight_required_before_pilot_requests
    assert request.telemetry_admission.current_timing_metric_names_prequalified is False
    assert request.transaction_bound_authorization_required is True
    assert request.pilot_execution_authorized is False
    assert request.final_measured_abc_execution_authorized is False


def test_runtime_realization_binds_current_reconciliation() -> None:
    request = subject.build_request()
    realization = subject.build_realization(ROOT, request)
    assert realization.timing_telemetry_preflight_required is True
    assert realization.current_timing_telemetry_qualification_established is False
    assert realization.pilot_execution_authorized is False
    assert realization.final_measured_abc_execution_authorized is False
    assert realization.next_gate == subject.NEXT_GATE


def test_readiness_v2_does_not_satisfy_old_authorization_seam() -> None:
    request = subject.build_request()
    realization = subject.build_realization(ROOT, request)
    readiness = subject.build_readiness(ROOT, realization)
    assert readiness.old_runtime_launcher_readiness_v1_superseded is True
    assert readiness.old_variance_pilot_authorization_v1_superseded is True
    assert readiness.transaction_bound_successor_required is True
    assert readiness.transaction_bound_executable_generated is False
    assert readiness.platform_observation_persisted is False
    assert readiness.pilot_execution_authorized is False
    assert readiness.final_measured_abc_execution_authorized is False
    assert readiness.new_execution_authorized is False


def test_generated_outputs_validate() -> None:
    result = subject.validate_implementation(ROOT)
    assert result["status"] == "VARIANCE_PILOT_RUNTIME_CONTRACT_READINESS_V2_VALID"
    assert result["candidate_introduced_execution_authority"] is False
