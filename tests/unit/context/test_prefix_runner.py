from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.context.prefix_runner import (
    PrefixDeterminismError,
    build_prefix_determinism,
    main,
    verify_prefix_determinism,
)

KEY = "auragateway-synthetic-prefix-fixture-key-v1-20260712"
KEY_ID = "synthetic-prefix-fixture-key-v1"


def _set_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AURAGATEWAY_PREFIX_HMAC_KEY", KEY)
    monkeypatch.setenv("AURAGATEWAY_PREFIX_HMAC_KEY_ID", KEY_ID)


def _copy_repo_assets(tmp_path: Path) -> None:
    shutil.copytree("data", tmp_path / "data")
    shutil.copytree("docs", tmp_path / "docs")


def test_verify_prefix_determinism_returns_gate_three_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_key(monkeypatch)
    summary = verify_prefix_determinism(Path("."))
    assert summary.stable_turn_count == 5
    assert summary.negative_control_pass_count == 7
    assert summary.gate_3_passed is True
    assert summary.measured_execution_permitted is False


def test_cli_prints_safe_json_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _set_key(monkeypatch)
    exit_code = main(["verify", "--repo-root", "."])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["validation_status"] == "valid"
    assert "raw" not in json.dumps(payload).lower()


def test_missing_hmac_settings_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AURAGATEWAY_PREFIX_HMAC_KEY", raising=False)
    monkeypatch.delenv("AURAGATEWAY_PREFIX_HMAC_KEY_ID", raising=False)
    with pytest.raises(PrefixDeterminismError, match="environment settings"):
        verify_prefix_determinism(Path("."))


def test_verifier_rejects_changed_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_key(monkeypatch)
    _copy_repo_assets(tmp_path)
    report_path = tmp_path / "data/context/prefix-determinism-v1/report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["status"] = "changed"
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(PrefixDeterminismError, match="does not match the frozen report"):
        verify_prefix_determinism(tmp_path)


def test_verifier_rejects_changed_turn_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_key(monkeypatch)
    _copy_repo_assets(tmp_path)
    turns_path = tmp_path / "data/context/prefix-determinism-v1/turns.json"
    payload = json.loads(turns_path.read_text(encoding="utf-8"))
    payload["turns"][0]["volatile_log"]["items"][0]["content_bytes"] += 1
    turns_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(PrefixDeterminismError, match="does not match the frozen report"):
        verify_prefix_determinism(tmp_path)


def test_verifier_rejects_timestamp_in_static_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_key(monkeypatch)
    _copy_repo_assets(tmp_path)
    spec_path = tmp_path / "data/context/compiler_spec.json"
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    payload["timestamp"] = "2026-07-12T00:00:00+02:00"
    spec_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(PrefixDeterminismError, match="Volatile or secret-bearing"):
        verify_prefix_determinism(tmp_path)


def test_build_recreates_identical_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_key(monkeypatch)
    _copy_repo_assets(tmp_path)
    report_path = tmp_path / "data/context/prefix-determinism-v1/report.json"
    manifest_path = tmp_path / "data/context/prefix-determinism-v1/manifest.json"
    report_path.unlink()
    manifest_path.unlink()
    summary = build_prefix_determinism(tmp_path)
    assert summary.gate_3_passed is True
    assert verify_prefix_determinism(tmp_path) == summary
