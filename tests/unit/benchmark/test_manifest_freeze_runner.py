from __future__ import annotations

from pathlib import Path

import pytest

from auragateway.benchmark.manifest_freeze_runner import _minor_units, main

_REPO_ROOT = Path(__file__).parents[3]


def test_minor_units_accepts_two_decimal_usd() -> None:
    assert _minor_units("5.00") == 500
    assert _minor_units("0.83") == 83


def test_minor_units_rejects_fractional_cents() -> None:
    with pytest.raises(Exception, match="at most two decimals"):
        _minor_units("5.001")


def test_validate_command_accepts_static_assets(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["validate", "--repo-root", str(_REPO_ROOT)])

    assert result == 0
    assert '"command": "validate"' in capsys.readouterr().out


def test_probe_requires_environment_credential(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    result = main(["probe-provider", "--repo-root", str(_REPO_ROOT)])

    assert result == 1
    error = capsys.readouterr().err
    assert "PROVIDER_CONFIGURATION_NOT_READY" in error
    assert "GROQ_API_KEY" in error


def test_freeze_requires_git_sha_and_budget(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["freeze", "--repo-root", str(_REPO_ROOT)])

    assert result == 1
    assert "IMPLEMENTATION_GIT_SHA_INVALID" in capsys.readouterr().err


def test_verify_fails_before_generated_freeze_assets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(["verify", "--repo-root", str(tmp_path)])

    assert result == 1
    assert "EXECUTION_FREEZE_ASSET_NOT_FOUND" in capsys.readouterr().err


def test_freeze_and_verify_with_synthetic_probe_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib
    import json
    import shutil

    from auragateway.benchmark import manifest_freeze
    from auragateway.contracts.execution_freeze import ProviderReadinessRecord

    relative_paths = (
        "data/evals/benchmark/preflight-v1/input.json",
        "data/evals/benchmark/preflight-v1/planned_run_ledger.json",
        "data/evals/benchmark/preflight-v1/manifest.json",
        "data/evals/benchmark/freeze-v1/pricing_schedule.json",
        "data/evals/benchmark/freeze-v1/negative_control_manifest.json",
        "data/evals/benchmark/freeze-v1/fault_injection_fixtures.json",
        "data/evals/benchmark/freeze-v1/privacy_verification.json",
    )
    for relative_path in relative_paths:
        source = _REPO_ROOT / relative_path
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    protected_path = Path(".local/provider-calibration/20260713T000000Z/groq_live-report.json")
    protected_full_path = tmp_path / protected_path
    protected_full_path.parent.mkdir(parents=True, exist_ok=True)
    protected_payload = {
        "mode": "groq_live",
        "status": "passed",
        "calls": [{"provider": "groq"}, {"provider": "groq"}],
        "raw_payload_persisted": False,
        "measured_execution_permitted": False,
    }
    protected_full_path.write_text(
        json.dumps(protected_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    readiness = ProviderReadinessRecord(
        record_id="groq-gpt-oss-20b-readiness-v1",
        provider_name="groq",
        provider_model_alias="groq-gpt-oss-20b",
        provider_adapter_version="groq-chat-completions-v1",
        probe_mode="groq_live",
        credentials_configured=True,
        probe_performed=True,
        probe_passed=True,
        call_count=2,
        protected_report_path=protected_path.as_posix(),
        protected_report_sha256=hashlib.sha256(protected_full_path.read_bytes()).hexdigest(),
        raw_payload_persisted=False,
        measured_execution_permitted=False,
        observed_at="2026-07-13T00:00:00Z",
    )
    readiness_path = tmp_path / "data/evals/benchmark/freeze-v1/provider_readiness.json"
    readiness_path.write_bytes(manifest_freeze.model_json_bytes(readiness))
    monkeypatch.setattr(manifest_freeze, "verify_gate9_preflight", lambda _root: None)

    frozen = manifest_freeze.freeze_execution_manifest(
        repo_root=tmp_path,
        implementation_git_sha="a" * 40,
        approved_cost_budget_minor_units=500,
    )
    verified = manifest_freeze.verify_frozen_assets(tmp_path)

    assert frozen.gate_10_passed is True
    assert frozen.estimated_upper_bound_minor_units == 83
    assert verified.execution_manifest_sha256 == frozen.execution_manifest_sha256
    assert verified.measured_execution_permitted is False
