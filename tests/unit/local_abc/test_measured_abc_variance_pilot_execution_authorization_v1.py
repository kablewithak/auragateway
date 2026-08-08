from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    measured_abc_variance_pilot_execution_authorization_v1 as subject,
)


def test_pilot_budget_is_exact_and_separate() -> None:
    budget = subject.PilotBudget()
    assert budget.pilot_trajectory_count == 54
    assert budget.pilot_turn_count == 216
    assert budget.maximum_request_attempts == 432
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_external_spend == 0


def test_platform_observation_rejects_internet_enabled() -> None:
    with pytest.raises(ValidationError):
        subject.PlatformCapabilityObservation(
            observed_at=datetime.now(UTC),
            capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
            accelerator="GPU_T4_X2",
            allocated_gpu_count=2,
            internet_enabled=True,
            wheelhouse_input_count=1,
            model_snapshot_input_count=1,
        )


def test_authorization_never_enables_final_measured_abc() -> None:
    now = datetime.now(UTC)
    item = subject.PilotExecutionAuthorization(
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        issued_from_main_commit="a" * 40,
        confirmation_sha256="b" * 64,
        runtime_launcher_readiness_sha256="e" * 64,
        pilot_manifest_sha256="c" * 64,
        pilot_schedule_sha256="d" * 64,
        runtime=subject.RuntimeBinding(),
        budget=subject.PilotBudget(),
    )
    assert item.pilot_execution_authorized is True
    assert item.final_measured_abc_execution_authorized is False
    assert item.single_use is True


def test_runtime_launcher_readiness_remains_non_authorizing() -> None:
    readiness = subject.RuntimeLauncherReadiness(
        status="READY_FOR_VARIANCE_PILOT_AUTHORIZATION",
        source_main_commit="b" * 40,
        pilot_manifest_sha256="c" * 64,
        pilot_schedule_sha256="d" * 64,
        launcher_source=subject.CommittedArtifact(
            repository_path="src/example.py",
            git_blob_sha="e" * 40,
        ),
        launcher_notebook=subject.CommittedArtifact(
            repository_path="notebooks/example.ipynb",
            git_blob_sha="a" * 40,
        ),
        runtime_request=subject.CommittedArtifact(
            repository_path="data/example.json",
            git_blob_sha="f" * 40,
        ),
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_gate="observe_platform_and_issue_variance_pilot_authorization_v1",
    )
    assert readiness.pilot_execution_authorized is False
    assert readiness.final_measured_abc_execution_authorized is False


def test_passed_consumption_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        subject.AuthorizationConsumption(
            authorization_sha256="a" * 64,
            outcome=subject.ExecutionOutcome.PASSED,
            consumed_at=datetime.now(UTC),
        )


def test_interrupted_consumption_is_terminal_without_pass_evidence() -> None:
    item = subject.AuthorizationConsumption(
        authorization_sha256="a" * 64,
        outcome=subject.ExecutionOutcome.INTERRUPTED,
        consumed_at=datetime.now(UTC),
    )
    assert item.authorization_reusable is False
    assert item.pilot_execution_authorized is False
    assert item.final_measured_abc_execution_authorized is False
