from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import measured_abc_execution_authorization_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def test_execution_budget_is_exact() -> None:
    budget = subject.ExecutionBudget()
    assert budget.planned_trajectories == 342
    assert budget.planned_turns == 1368
    assert budget.maximum_model_request_attempts == 2736
    assert budget.maximum_retries_after_initial_attempt == 1
    assert budget.maximum_hidden_retries == 0
    assert budget.replacement_cases_permitted is False
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_external_spend == 0


def test_runtime_binding_is_current_local_vllm_line() -> None:
    runtime = subject.RuntimeBinding()
    assert runtime.accelerator == "GPU_T4_X2"
    assert runtime.internet_enabled is False
    assert runtime.execution_backend == "local_vllm"
    assert runtime.model_repository == "Qwen/Qwen2.5-0.5B-Instruct"
    assert runtime.worker_1_gpu_index == 0
    assert runtime.worker_1_port == 8001
    assert runtime.worker_2_gpu_index == 1
    assert runtime.worker_2_port == 8002


def test_platform_observation_rejects_internet_enabled() -> None:
    payload = {
        "observed_at": datetime.now(UTC).isoformat(),
        "capability_source": "KAGGLE_NOTEBOOK_SETTINGS_UI",
        "accelerator": "GPU_T4_X2",
        "allocated_gpu_count": 2,
        "internet_enabled": True,
        "wheelhouse_input_count": 1,
        "model_snapshot_input_count": 1,
        "worker_1_cuda_visible_devices": "0",
        "worker_1_gpu_index": 0,
        "worker_1_port": 8001,
        "worker_2_cuda_visible_devices": "1",
        "worker_2_gpu_index": 1,
        "worker_2_port": 8002,
    }
    with pytest.raises(ValidationError):
        subject.PlatformCapabilityObservation.model_validate(payload)


def test_readiness_rejects_wrong_trajectory_count() -> None:
    receipt = {
        "repository_path": "benchmarks/local_abc/example.json",
        "sha256": "a" * 64,
        "size_bytes": 1,
    }
    payload = {
        "status": "READY_FOR_MEASURED_ABC_AUTHORIZATION",
        "source_main_commit": "a" * 40,
        "current_line_p5_pass_accepted": True,
        "current_line_p6_pass_accepted": True,
        "variance_pilot_accepted": True,
        "repetition_count_frozen": True,
        "execution_manifest_frozen": True,
        "execution_manifest_execution_enabled": False,
        "planned_trajectories": 72,
        "planned_turns": 1368,
        "maximum_model_request_attempts": 2736,
        "maximum_hidden_retries": 0,
        "planned_run_ledger_sha256": subject.PLANNED_LEDGER_SHA256,
        "condition_fingerprints_sha256": subject.CONDITION_FINGERPRINTS_SHA256,
        "execution_manifest": receipt,
        "variance_pilot_acceptance": {**receipt, "repository_path": "a.json"},
        "repetition_count_freeze": {**receipt, "repository_path": "b.json"},
        "governed_p5_p6_acceptance": {**receipt, "repository_path": "c.json"},
        "runtime": subject.RuntimeBinding().model_dump(mode="json"),
        "measured_abc_execution_authorized": False,
        "runtime_execution_authorized": False,
        "next_gate": "observe_platform_and_issue_measured_abc_execution_authorization_v1",
    }
    with pytest.raises(ValidationError):
        subject.MeasuredABCExecutionReadiness.model_validate(payload)


def test_passed_consumption_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        subject.AuthorizationConsumption(
            authorization_sha256="a" * 64,
            outcome=subject.ExecutionOutcome.PASSED,
            consumed_at=datetime.now(UTC),
        )


def test_non_passed_consumption_can_preserve_partial_evidence() -> None:
    item = subject.AuthorizationConsumption(
        authorization_sha256="a" * 64,
        outcome=subject.ExecutionOutcome.INTERRUPTED,
        consumed_at=datetime.now(UTC),
    )
    assert item.authorization_reusable is False
    assert item.measured_abc_execution_authorized is False


def test_issued_authorization_is_single_use_and_binds_confirmation() -> None:
    now = datetime.now(UTC)
    item = subject.MeasuredABCExecutionAuthorization(
        issued_at=now,
        expires_at=now + timedelta(seconds=1),
        issued_from_main_commit="a" * 40,
        confirmation_sha256="d" * 64,
        readiness_sha256="b" * 64,
        execution_manifest_sha256="c" * 64,
        platform_observation=subject.PlatformCapabilityObservation(
            observed_at=now,
            capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
            accelerator="GPU_T4_X2",
            allocated_gpu_count=2,
            internet_enabled=False,
            wheelhouse_input_count=1,
            model_snapshot_input_count=1,
            worker_1_cuda_visible_devices="0",
            worker_1_gpu_index=0,
            worker_1_port=8001,
            worker_2_cuda_visible_devices="1",
            worker_2_gpu_index=1,
            worker_2_port=8002,
        ),
        runtime=subject.RuntimeBinding(),
        budget=subject.ExecutionBudget(),
    )
    assert item.single_use is True
    assert item.authorization_reusable is True
    assert item.confirmation_sha256 == "d" * 64
    assert item.measured_abc_execution_authorized is True


def test_historical_authorities_are_context_only_in_policy() -> None:
    payload = json.loads((ROOT / subject.POLICY_PATH).read_text(encoding="utf-8"))
    historical = payload["historical_context_only"]
    assert historical["measured_execution_authorization_v1"]["git_blob_sha"] == (
        "9a712372cee83c4af4a026081ec01ddbc809effa"
    )
    assert historical["hosted_provider_execution_manifest"]["git_blob_sha"] == (
        "791299bb0df45441f25ed8c1e030d84ca1a31ec3"
    )


def test_review_is_deterministic() -> None:
    first = subject.build_review(ROOT)
    second = subject.build_review(ROOT)
    assert first == second
    assert first.authorization_issued is False
    assert first.measured_abc_execution_authorized is False


def test_generated_record_does_not_authorize_execution() -> None:
    record = subject._load_model(
        subject.ImplementationRecord,
        ROOT / subject.RECORD_PATH,
    )
    assert record.authorization_issued is False
    assert record.measured_abc_execution_authorized is False
    assert record.runtime_execution_authorized is False


def test_validate_implementation_reports_dynamic_readiness_without_issuing() -> None:
    result = subject.validate_implementation(ROOT)
    assert result["status"] == "MEASURED_ABC_EXECUTION_AUTHORIZATION_V1_VALID"
    assert isinstance(result["issuance_ready"], bool)
    assert result["authorization_issued"] is False
    assert result["measured_abc_execution_authorized"] is False
    assert result["runtime_execution_authorized"] is False
