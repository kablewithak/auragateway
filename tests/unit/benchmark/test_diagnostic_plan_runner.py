from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.benchmark.diagnostic_plan_runner import (
    DiagnosticDesignError,
    validate_diagnostic_design,
)

_SOURCE_DESIGN_ROOT = Path("data/evals/benchmark/diagnostic-design-v1")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _repo_fixture(tmp_path: Path) -> Path:
    design_root = tmp_path / _SOURCE_DESIGN_ROOT
    design_root.mkdir(parents=True)
    shutil.copyfile(
        _SOURCE_DESIGN_ROOT / "experiment_plan.json",
        design_root / "experiment_plan.json",
    )
    shutil.copyfile(
        _SOURCE_DESIGN_ROOT / "manifest.json",
        design_root / "manifest.json",
    )

    source_root = tmp_path / "data/evals/benchmark/live-development-v6"
    _write_json(
        source_root / "manifest.json",
        {
            "journal_sha256": ("73e5414a98fd075fe0a58f4db2d0f739d93ed748a7545411cbb492aea1067a76"),
            "run_records_sha256": (
                "fbd1e64d10b317a18475d6dccb922bf4e7c41ce40c491c7654bac664c7347f84"
            ),
            "report_sha256": ("670d233cb53c78523d036ec4ea2dc8f16f787b988d033e0a811105a63a503edd"),
            "live_provider_called": True,
            "held_out_executed": False,
            "full_benchmark_executed": False,
            "benchmark_claims_permitted": False,
            "measured_execution_permitted": False,
            "comparison_eligible": False,
        },
    )
    _write_json(
        source_root / "report.json",
        {
            "batch_id": "auragateway-live-development-batch-06",
            "authorization_id": "live-development-batch-06-auth-v1",
            "terminal_record_count": 3,
            "attempt_record_count": 11,
            "completed_run_count": 2,
            "provider_error_count": 1,
            "development_only": True,
            "live_provider_called": True,
            "held_out_executed": False,
            "full_benchmark_executed": False,
            "benchmark_claims_permitted": False,
            "measured_execution_permitted": False,
            "comparison_eligible": False,
            "batch_completed": True,
        },
    )
    return tmp_path


def test_validator_accepts_design_without_authorization(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)

    summary = validate_diagnostic_design(repo_root)

    assert summary.design_id == ("batch-06-request-rejection-diagnostic-design-v1")
    assert summary.status.value == "design_only"
    assert summary.hypothesis_count == 5
    assert summary.cohort_count == 6
    assert summary.sequence_count == 8
    assert summary.maximum_provider_calls == 24
    assert summary.provider_calls_permitted is False
    assert summary.authorization_created is False
    assert summary.execution_permitted is False


def test_validator_rejects_authorization_file(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    authorization = repo_root / "data/evals/benchmark/diagnostic-design-v1/authorization.json"
    _write_json(authorization, {"unsafe": True})

    with pytest.raises(
        DiagnosticDesignError,
        match="must not contain an execution authorization",
    ):
        validate_diagnostic_design(repo_root)


def test_validator_rejects_plan_hash_drift(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    plan_path = repo_root / "data/evals/benchmark/diagnostic-design-v1/experiment_plan.json"
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    hypotheses = plan_payload["hypotheses"]
    assert isinstance(hypotheses, list)
    assert isinstance(hypotheses[0], dict)
    hypotheses[0]["statement"] = (
        str(hypotheses[0]["statement"]) + " This sentence creates valid hash drift."
    )
    _write_json(plan_path, plan_payload)

    with pytest.raises(
        DiagnosticDesignError,
        match="no longer matches its manifest",
    ):
        validate_diagnostic_design(repo_root)


def test_validator_rejects_source_evidence_identity_drift(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    manifest_path = repo_root / "data/evals/benchmark/live-development-v6/manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["report_sha256"] = "0" * 64
    _write_json(manifest_path, payload)

    with pytest.raises(
        DiagnosticDesignError,
        match="public evidence identities differ",
    ):
        validate_diagnostic_design(repo_root)


def test_validator_rejects_source_report_outcome_drift(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    report_path = repo_root / "data/evals/benchmark/live-development-v6/report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["provider_error_count"] = 0
    _write_json(report_path, payload)

    with pytest.raises(
        DiagnosticDesignError,
        match="recorded Batch 06 outcome",
    ):
        validate_diagnostic_design(repo_root)
