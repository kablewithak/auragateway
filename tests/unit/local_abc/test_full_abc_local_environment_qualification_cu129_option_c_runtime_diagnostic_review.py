"""Regression tests for the approved Option C runtime diagnostic decision."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_option_c_runtime_diagnostic_review as subject,
)


def _record_path() -> Path:
    return Path(
        "benchmarks/local_abc/auragateway_cu129_option_c_runtime_diagnostic_decision_v1.json"
    )


def _load_record_payload() -> dict[str, object]:
    payload = json.loads(_record_path().read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_record_is_canonical_and_selects_option_c() -> None:
    raw = _record_path().read_text(encoding="utf-8")
    record = subject.OptionCRuntimeDiagnosticDecisionRecord.model_validate_json(raw)

    assert raw == record.canonical_json()
    assert record.decision == "APPROVED_FOR_OPTION_C_TWO_STAGE_RUNTIME_DIAGNOSTIC"
    assert record.selected_strategy.selected_backend == "TRITON_ATTN"
    assert record.selected_strategy.backend_decision_changed is False
    assert record.next_gate == "implement_p0_p2_platform_diagnostic_assets"


def test_p0_p2_are_platform_only_and_do_not_consume_full_attempt() -> None:
    record = subject.OptionCRuntimeDiagnosticDecisionRecord.model_validate(_load_record_payload())

    assert tuple(probe.probe_id for probe in record.platform_diagnostic.probes) == (
        "P0",
        "P1",
        "P2",
    )
    assert record.platform_diagnostic.model_load_permitted is False
    assert record.platform_diagnostic.worker_start_permitted is False
    assert record.platform_diagnostic.model_requests_permitted == 0
    assert record.platform_diagnostic.benchmark_trajectory_requests_permitted == 0
    assert record.platform_diagnostic.maximum_sessions == 1
    assert record.selected_strategy.full_qualification_attempt_consumed_by_p0_p2 is False


def test_p3_p6_remain_deferred_and_separately_authorized() -> None:
    record = subject.OptionCRuntimeDiagnosticDecisionRecord.model_validate(_load_record_payload())

    assert tuple(probe.probe_id for probe in record.runtime_diagnostic.probes) == (
        "P3",
        "P4",
        "P5",
        "P6",
    )
    assert record.runtime_diagnostic.prerequisite == "EXPLICIT_TRITON_IMPLEMENTATION_MERGED"
    assert record.runtime_diagnostic.separate_future_authorization_required is True
    assert record.runtime_diagnostic.measured_execution_permitted is False
    assert record.runtime_diagnostic.hidden_retries_permitted is False
    assert record.runtime_diagnostic.replacement_workers_permitted is False
    assert record.runtime_diagnostic.silent_backend_fallback_permitted is False


def test_failure_budget_blocks_a_fourth_blind_vllm_cycle() -> None:
    record = subject.OptionCRuntimeDiagnosticDecisionRecord.model_validate(_load_record_payload())

    assert record.failure_budget.platform_diagnostic_sessions == 1
    assert record.failure_budget.explicit_triton_full_qualification_attempts == 1
    assert record.failure_budget.compatibility_spike_candidates_maximum == 3
    assert record.failure_budget.fourth_blind_vllm_repair_cycle_permitted is False


def test_platform_probe_order_drift_is_rejected() -> None:
    payload = _load_record_payload()
    platform = payload["platform_diagnostic"]
    assert isinstance(platform, dict)
    probes = platform["probes"]
    assert isinstance(probes, list)
    probes[0], probes[1] = probes[1], probes[0]

    with pytest.raises(ValidationError, match="P0-P2 probe order"):
        subject.OptionCRuntimeDiagnosticDecisionRecord.model_validate(payload)


def _write_temp_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    triton_already_implemented: bool = False,
) -> None:
    for relative_path in (
        subject.RECORD_PATH,
        subject.ADR_PATH,
        subject.REPORT_PATH,
        subject.RUNBOOK_PATH,
    ):
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)

    previous_payload = {
        "decision": "APPROVED_FOR_DETERMINISTIC_T4_ATTENTION_BACKEND_IMPLEMENTATION",
        "implementation_boundary": {"selected_backend": "TRITON_ATTN"},
    }
    previous_raw = json.dumps(previous_payload, separators=(",", ":"), sort_keys=True)
    previous_path = tmp_path / subject.PREVIOUS_REVIEW_PATH
    previous_path.parent.mkdir(parents=True, exist_ok=True)
    previous_path.write_text(previous_raw, encoding="utf-8")
    monkeypatch.setattr(
        subject,
        "PREVIOUS_REVIEW_SHA256",
        hashlib.sha256(previous_raw.encode("utf-8")).hexdigest(),
    )

    command = ["python", "--dtype", "auto", "--enable-prefix-caching"]
    if triton_already_implemented:
        command.extend(("--attention-backend", "TRITON_ATTN"))
    worker_plan = {
        "workers": [
            {"command_argv": [*command, "--port", "8001"]},
            {"command_argv": [*command, "--port", "8002"]},
        ]
    }
    worker_plan_path = tmp_path / subject.WORKER_PLAN_PATH
    worker_plan_path.parent.mkdir(parents=True, exist_ok=True)
    worker_plan_path.write_text(json.dumps(worker_plan), encoding="utf-8")
    monkeypatch.setattr(subject, "_require_base_ancestor", lambda _: None)


def test_repository_package_validates_decision_only_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_temp_package(tmp_path, monkeypatch)

    summary = subject.validate_repository_package(tmp_path)

    assert summary["status"] == "OPTION_C_RUNTIME_DIAGNOSTIC_DECISION_VALID"
    assert summary["platform_probe_count"] == 3
    assert summary["runtime_probe_count"] == 4
    assert summary["runtime_source_changed"] is False
    assert summary["authorization_issued"] is False
    assert summary["kaggle_execution_performed"] is False


def test_repository_package_rejects_runtime_implementation_in_decision_tranche(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_temp_package(tmp_path, monkeypatch, triton_already_implemented=True)

    with pytest.raises(
        subject.OptionCRuntimeDiagnosticDecisionError,
        match="runtime implementation was mixed",
    ):
        subject.validate_repository_package(tmp_path)
