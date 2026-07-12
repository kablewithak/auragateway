from __future__ import annotations

from pathlib import Path

import pytest

from auragateway.benchmark.smoke import ControlledSmokeError
from auragateway.benchmark.smoke_runner import (
    resume_assets,
    verify_assets,
    write_assets,
)


def test_runner_writes_and_verifies_deterministic_evidence(
    temp_smoke_repo: tuple[Path, str],
) -> None:
    repo, authorization_id = temp_smoke_repo
    summary = write_assets(repo, authorization_id)
    assert summary.smoke_passed is True
    assert summary.terminal_record_count == 3
    verified = verify_assets(repo, authorization_id)
    assert verified.smoke_passed is True


def test_resume_reuses_all_terminal_records_without_byte_change(
    temp_smoke_repo: tuple[Path, str],
) -> None:
    repo, authorization_id = temp_smoke_repo
    write_assets(repo, authorization_id)
    records_path = repo / "data/evals/benchmark/smoke-v1/run_records.json"
    before = records_path.read_bytes()
    summary = resume_assets(repo, authorization_id)
    assert summary.reused_terminal_record_count == 3
    assert records_path.read_bytes() == before


def test_verify_rejects_mutated_report(
    temp_smoke_repo: tuple[Path, str],
) -> None:
    repo, authorization_id = temp_smoke_repo
    write_assets(repo, authorization_id)
    report_path = repo / "data/evals/benchmark/smoke-v1/smoke_report.json"
    mutated = report_path.read_text().replace(
        '"smoke_passed": true',
        '"smoke_passed": false',
    )
    report_path.write_text(mutated)
    with pytest.raises(ControlledSmokeError, match="not reproducible"):
        verify_assets(repo, authorization_id)


def test_runner_rejects_wrong_authorization_id(
    temp_smoke_repo: tuple[Path, str],
) -> None:
    repo, _ = temp_smoke_repo
    with pytest.raises(ControlledSmokeError, match="does not match"):
        write_assets(repo, "wrong-authorization")


def test_runner_rejects_mutated_gate10_manifest(
    temp_smoke_repo: tuple[Path, str],
) -> None:
    repo, authorization_id = temp_smoke_repo
    gate10_path = repo / "data/evals/benchmark/freeze-v1/manifest.json"
    mutated = gate10_path.read_text().replace(
        '"gate_10_passed": true',
        '"gate_10_passed": false',
    )
    gate10_path.write_text(mutated)
    with pytest.raises(ControlledSmokeError, match="Gate 10 manifest bytes"):
        write_assets(repo, authorization_id)


def test_runner_rejects_mutated_plan_bytes(
    temp_smoke_repo: tuple[Path, str],
) -> None:
    repo, authorization_id = temp_smoke_repo
    plan_path = repo / "data/evals/benchmark/preflight-v1/planned_run_ledger.json"
    plan_path.write_text(plan_path.read_text().replace('"turn_count": 4', '"turn_count": 3', 1))
    with pytest.raises(ControlledSmokeError, match="Planned-run ledger bytes"):
        write_assets(repo, authorization_id)
