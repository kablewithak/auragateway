from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark import cache_telemetry_hardening_runner
from auragateway.benchmark.cache_telemetry_hardening_runner import (
    CacheTelemetryHardeningError,
    validate_cache_telemetry_hardening,
)

_DATA_ROOT = Path("data/evals/benchmark/cache-telemetry-hardening-v1")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_Groq_Cache_Telemetry_Capture_Hardening.md")


def _copy_assets(repo_root: Path) -> None:
    for relative_path in (
        _DATA_ROOT / "acceptance.json",
        _DATA_ROOT / "calibration_draft.json",
        _DATA_ROOT / "synthetic_cases.json",
        _DATA_ROOT / "manifest.json",
        _REPORT_PATH,
    ):
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)


def _patch_source_bindings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = {
        "data/evals/benchmark/cache-telemetry-review-v1/review.json": (
            "100dfef73584d2b985a6bbb3ff21a8af0000c120"
        ),
        "data/evals/benchmark/cache-telemetry-review-v1/manifest.json": (
            "7bccf400dad9d2987ddee9d3413ef8dff4d2883f"
        ),
    }

    def fake_git_blob_sha1(
        repo_root: Path,
        commit: str,
        path: str,
    ) -> str:
        assert commit == "e508655e33acbf544b040f2b6fdea1e2a4fe7a25"
        return expected[path]

    monkeypatch.setattr(
        cache_telemetry_hardening_runner,
        "_git_blob_sha1",
        fake_git_blob_sha1,
    )


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _refresh_manifest_hash(
    repo_root: Path,
    *,
    field_name: str,
    relative_path: Path,
) -> None:
    manifest_path = repo_root / _DATA_ROOT / "manifest.json"
    manifest = _json_object(manifest_path)
    manifest[field_name] = hashlib.sha256((repo_root / relative_path).read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def test_validator_accepts_non_live_hardening(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _patch_source_bindings(monkeypatch)

    summary = validate_cache_telemetry_hardening(tmp_path)

    assert summary.command == "validate"
    assert summary.completed_action_count == 6
    assert summary.synthetic_case_count == 7
    assert summary.synthetic_cases_passed is True
    assert summary.provider_call_performed is False
    assert summary.credential_accessed is False
    assert summary.calibration_authorized is False


def test_validator_does_not_read_groq_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _patch_source_bindings(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = validate_cache_telemetry_hardening(tmp_path)

    assert summary.credential_accessed is False
    assert summary.provider_call_performed is False


def test_validator_rejects_acceptance_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _patch_source_bindings(monkeypatch)
    acceptance_path = tmp_path / _DATA_ROOT / "acceptance.json"
    acceptance_path.write_text(
        acceptance_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        CacheTelemetryHardeningError,
        match="asset no longer matches",
    ):
        validate_cache_telemetry_hardening(tmp_path)


def test_validator_rejects_synthetic_expectation_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _patch_source_bindings(monkeypatch)
    cases_path = tmp_path / _DATA_ROOT / "synthetic_cases.json"
    payload = _json_object(cases_path)
    cases = payload["cases"]
    assert isinstance(cases, list)
    first = cases[0]
    assert isinstance(first, dict)
    first["expected_usage_decision"] = "permitted"
    first["expected_usage_reason"] = "CLAIM_PERMITTED"
    cases_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    _refresh_manifest_hash(
        tmp_path,
        field_name="synthetic_cases_sha256",
        relative_path=_DATA_ROOT / "synthetic_cases.json",
    )

    with pytest.raises(
        CacheTelemetryHardeningError,
        match="did not match expectations",
    ):
        validate_cache_telemetry_hardening(tmp_path)


def test_validator_rejects_active_calibration_draft(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _patch_source_bindings(monkeypatch)
    draft_path = tmp_path / _DATA_ROOT / "calibration_draft.json"
    payload = _json_object(draft_path)
    payload["provider_call_authorized"] = True
    draft_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    _refresh_manifest_hash(
        tmp_path,
        field_name="calibration_draft_sha256",
        relative_path=_DATA_ROOT / "calibration_draft.json",
    )

    with pytest.raises(
        CacheTelemetryHardeningError,
        match="failed typed validation",
    ):
        validate_cache_telemetry_hardening(tmp_path)


def test_validator_rejects_report_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _patch_source_bindings(monkeypatch)
    report_path = tmp_path / _REPORT_PATH
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CacheTelemetryHardeningError,
        match="asset no longer matches",
    ):
        validate_cache_telemetry_hardening(tmp_path)
