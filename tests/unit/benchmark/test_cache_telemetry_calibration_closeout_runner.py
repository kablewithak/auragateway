from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.cache_telemetry_calibration_closeout_runner import (
    CalibrationCloseoutError,
    validate_calibration_closeout,
)

_CLOSEOUT_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-closeout-v1")
_EXECUTION_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-v1")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_Cache_Telemetry_Calibration_Closeout.md")


def _copy_assets(repo_root: Path) -> None:
    for relative_path in (
        _CLOSEOUT_ROOT / "closeout.json",
        _CLOSEOUT_ROOT / "manifest.json",
        _EXECUTION_ROOT / "authorization.json",
        _EXECUTION_ROOT / "runtime_policy.json",
        _EXECUTION_ROOT / "journal.jsonl",
        _EXECUTION_ROOT / "run_records.json",
        _EXECUTION_ROOT / "report.json",
        _EXECUTION_ROOT / "manifest.json",
        _REPORT_PATH,
    ):
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_validator_accepts_closed_calibration(tmp_path: Path) -> None:
    _copy_assets(tmp_path)

    summary = validate_calibration_closeout(tmp_path)

    assert summary.provider_call_count == 3
    assert summary.successful_call_count == 3
    assert summary.billing_cache_numeric_sample_count == 0
    assert summary.installed_sdk_version == "1.5.0"
    assert summary.authorization_consumed is True
    assert summary.rerun_permitted is False


def test_validator_reads_no_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = validate_calibration_closeout(tmp_path)

    assert summary.provider_call_count == 3


def test_validator_rejects_execution_report_hash_drift(
    tmp_path: Path,
) -> None:
    _copy_assets(tmp_path)
    report_path = tmp_path / _EXECUTION_ROOT / "report.json"
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationCloseoutError,
        match="bound execution asset no longer matches",
    ):
        validate_calibration_closeout(tmp_path)


def test_validator_rejects_closeout_hash_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    closeout_path = tmp_path / _CLOSEOUT_ROOT / "closeout.json"
    closeout_path.write_text(
        closeout_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationCloseoutError,
        match="closeout JSON no longer matches",
    ):
        validate_calibration_closeout(tmp_path)


def test_validator_rejects_report_content_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    report_path = tmp_path / _REPORT_PATH
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationCloseoutError,
        match="closeout report no longer matches",
    ):
        validate_calibration_closeout(tmp_path)


def test_validator_rejects_sdk_version_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    records_path = tmp_path / _EXECUTION_ROOT / "run_records.json"
    payload = _json_object(records_path)
    records = payload["records"]
    assert isinstance(records, list)
    first = records[0]
    assert isinstance(first, dict)
    first["installed_sdk_version"] = "1.5.1"
    records_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationCloseoutError,
        match="bound execution asset no longer matches",
    ):
        validate_calibration_closeout(tmp_path)


def test_validator_rejects_billing_state_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    records_path = tmp_path / _EXECUTION_ROOT / "run_records.json"
    payload = _json_object(records_path)
    records = payload["records"]
    assert isinstance(records, list)
    first = records[0]
    assert isinstance(first, dict)
    first["billing_cached_tokens_field_present"] = True
    first["billing_observation_state"] = "observed_zero"
    first["billing_cached_input_tokens"] = 0
    records_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationCloseoutError,
        match="bound execution asset no longer matches",
    ):
        validate_calibration_closeout(tmp_path)


def test_validator_rejects_execution_manifest_drift(
    tmp_path: Path,
) -> None:
    _copy_assets(tmp_path)
    manifest_path = tmp_path / _EXECUTION_ROOT / "manifest.json"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationCloseoutError,
        match="bound execution asset no longer matches",
    ):
        validate_calibration_closeout(tmp_path)
