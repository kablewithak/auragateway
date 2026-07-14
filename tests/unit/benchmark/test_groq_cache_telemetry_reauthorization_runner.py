from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark import (
    groq_cache_telemetry_reauthorization_runner as runner,
)
from auragateway.benchmark.groq_cache_telemetry_reauthorization_runner import (
    GroqCacheTelemetryReauthorizationError,
    dry_run_groq_cache_telemetry_reauthorization,
    validate_groq_cache_telemetry_reauthorization,
)

_REVIEW_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-review-v1")
_ADR_PATH = Path("docs/adr/groq-cache-telemetry-reauthorization-review.md")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_Groq_Cache_Telemetry_Reauthorization_Review.md")


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _copy_review_assets(repo_root: Path) -> None:
    review = _json_object(_REVIEW_ROOT / "review.json")
    bindings = review["source_bindings"]
    assert isinstance(bindings, list)

    relative_paths = [
        _REVIEW_ROOT / "observation_plan.json",
        _REVIEW_ROOT / "review.json",
        _REVIEW_ROOT / "dry_run_report.json",
        _REVIEW_ROOT / "manifest.json",
        _ADR_PATH,
        _REPORT_PATH,
    ]
    for binding in bindings:
        assert isinstance(binding, dict)
        path = binding["path"]
        assert isinstance(path, str)
        relative_paths.append(Path(path))

    for relative_path in relative_paths:
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)


def _refresh_manifest_hash(
    repo_root: Path,
    *,
    field_name: str,
    relative_path: Path,
) -> None:
    manifest_path = repo_root / _REVIEW_ROOT / "manifest.json"
    manifest = _json_object(manifest_path)
    manifest[field_name] = hashlib.sha256((repo_root / relative_path).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_validate_accepts_review_ready_inactive(tmp_path: Path) -> None:
    _copy_review_assets(tmp_path)

    summary = validate_groq_cache_telemetry_reauthorization(tmp_path)

    assert summary.command == "validate"
    assert summary.planned_attempt_count == 2
    assert summary.maximum_provider_calls == 2
    assert summary.observation_boundary_materially_different is True
    assert summary.raw_response_api_available is True
    assert summary.provider_call_performed is False
    assert summary.credential_accessed is False
    assert summary.provider_call_authorized is False
    assert summary.active_authorization_created is False
    assert summary.execution_command_available is False
    assert summary.reauthorization_execution_authorized is False
    assert summary.benchmark_execution_authorized is False
    assert summary.comparison_eligible is False


def test_dry_run_reproduces_two_attempt_schedule(tmp_path: Path) -> None:
    _copy_review_assets(tmp_path)

    summary = dry_run_groq_cache_telemetry_reauthorization(tmp_path)

    assert summary.command == "dry-run"
    assert summary.planned_attempt_count == 2
    assert summary.provider_call_performed is False
    assert summary.credential_accessed is False
    assert summary.execution_command_available is False


def test_validate_does_not_read_environment_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_review_assets(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = validate_groq_cache_telemetry_reauthorization(tmp_path)

    assert summary.credential_accessed is False
    assert summary.provider_call_performed is False


def test_validate_rejects_manifest_hash_drift(tmp_path: Path) -> None:
    _copy_review_assets(tmp_path)
    review_path = tmp_path / _REVIEW_ROOT / "review.json"
    review_path.write_text(
        review_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        GroqCacheTelemetryReauthorizationError,
        match="no longer matches its manifest",
    ):
        validate_groq_cache_telemetry_reauthorization(tmp_path)


def test_validate_rejects_historical_source_drift(tmp_path: Path) -> None:
    _copy_review_assets(tmp_path)
    source_path = tmp_path / "data/evals/benchmark/cache-telemetry-calibration-v1/report.json"
    source_path.write_text(
        source_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        GroqCacheTelemetryReauthorizationError,
        match="historical evidence file no longer matches",
    ):
        validate_groq_cache_telemetry_reauthorization(tmp_path)


def test_validate_rejects_dry_run_drift(tmp_path: Path) -> None:
    _copy_review_assets(tmp_path)
    dry_run_path = tmp_path / _REVIEW_ROOT / "dry_run_report.json"
    dry_run = _json_object(dry_run_path)
    attempts = dry_run["attempts"]
    assert isinstance(attempts, list)
    assert isinstance(attempts[1], dict)
    attempts[1]["planned_offset_seconds"] = 9
    dry_run_path.write_text(json.dumps(dry_run, indent=2) + "\n", encoding="utf-8")
    _refresh_manifest_hash(
        tmp_path,
        field_name="dry_run_report_sha256",
        relative_path=_REVIEW_ROOT / "dry_run_report.json",
    )

    with pytest.raises(
        GroqCacheTelemetryReauthorizationError,
        match="typed contract",
    ):
        validate_groq_cache_telemetry_reauthorization(tmp_path)


def test_validate_rejects_observation_plan_hash_drift(tmp_path: Path) -> None:
    _copy_review_assets(tmp_path)
    plan_path = tmp_path / _REVIEW_ROOT / "observation_plan.json"
    plan = _json_object(plan_path)
    plan["protected_raw_responses_path"] = (
        ".local/benchmark/groq-cache-telemetry-reauthorization-v1/raw_responses-v2.jsonl"
    )
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    _refresh_manifest_hash(
        tmp_path,
        field_name="observation_plan_sha256",
        relative_path=_REVIEW_ROOT / "observation_plan.json",
    )

    with pytest.raises(
        GroqCacheTelemetryReauthorizationError,
        match="does not bind the exact observation plan bytes",
    ):
        validate_groq_cache_telemetry_reauthorization(tmp_path)


def test_validate_rejects_missing_raw_response_sdk_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_review_assets(tmp_path)

    class _FakeClient:
        def __init__(self, *, api_key: str) -> None:
            self.api_key = api_key
            self.chat = object()

        def close(self) -> None:
            return None

    monkeypatch.setattr(runner, "Groq", _FakeClient)

    with pytest.raises(
        GroqCacheTelemetryReauthorizationError,
        match="raw-response surface",
    ):
        validate_groq_cache_telemetry_reauthorization(tmp_path)


def test_runner_exposes_no_execution_function() -> None:
    assert not hasattr(runner, "execute_groq_cache_telemetry_reauthorization")
