"""Regression tests for the bounded vLLM CLI contract hardening."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_vllm_cli_contract_hardening as hardening,
)

ROOT = Path(__file__).resolve().parents[3]


def test_repository_hardening_package_blocks_retry_until_rematerialization() -> None:
    summary = hardening.validate_repository_package(ROOT)

    assert summary["status"] == "VLLM_CLI_CONTRACT_HARDENING_IMPLEMENTED"
    assert summary["decision"] == ("IMPLEMENTED_AWAITING_POST_MERGE_HARNESS_REMATERIALIZATION")
    assert summary["pinned_vllm_version"] == "0.19.1"
    assert summary["rejected_option"] == "--disable-log-requests"
    assert summary["replacement_option"] == "--no-enable-log-requests"
    assert summary["pre_worker_cli_capability_gate"] is True
    assert summary["capability_failure_mode"] == "fail_before_worker_spawn"
    assert summary["active_harness_unchanged"] is True
    assert summary["active_harness_reusable_for_retry"] is False
    assert summary["fresh_issuer_usable"] is False
    assert summary["consumed_authorization_reusable"] is False
    assert summary["evidence_artifact_count"] == 4
    assert summary["authorization_issued"] is False
    assert summary["kaggle_execution_performed"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["next_gate"] == ("merge_then_prepare_vllm_cli_hardened_harness_source_package")


def test_worker_plan_guard_rejects_rejected_logging_option(tmp_path: Path) -> None:
    source = json.loads((ROOT / hardening.WORKER_PLAN_PATH).read_text(encoding="utf-8"))
    source["workers"][0]["command_argv"][-1] = "--disable-log-requests"
    path = tmp_path / "worker_startup_plan.json"
    path.write_text(
        json.dumps(source, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(hardening, "WORKER_PLAN_PATH", path.relative_to(tmp_path))
        with pytest.raises(
            hardening.VllmCliContractHardeningError,
            match="canonical builder",
        ):
            hardening._require_worker_plan(tmp_path)


def test_record_loader_rejects_noncanonical_json(tmp_path: Path) -> None:
    payload = json.loads((ROOT / hardening.RECORD_PATH).read_text(encoding="utf-8"))
    path = tmp_path / "record.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(
        hardening.VllmCliContractHardeningError,
        match="not canonical",
    ):
        hardening._load_record(path)
