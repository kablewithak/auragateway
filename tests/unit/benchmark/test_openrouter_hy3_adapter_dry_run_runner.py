from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.benchmark.openrouter_hy3_adapter_dry_run_runner import (
    OpenRouterDryRunError,
    validate_openrouter_dry_run,
)

_FIXTURE = Path("data/provider_fixtures/openrouter-hy3-adapter-v1/fixtures.json")
_REPORT = Path("data/evals/benchmark/openrouter-hy3-adapter-dry-run-v1/report.json")
_MANIFEST = Path("data/evals/benchmark/openrouter-hy3-adapter-dry-run-v1/manifest.json")


def _copy_assets(repo_root: Path) -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    paths = {_FIXTURE, _REPORT, _MANIFEST}
    paths.update(Path(item["path"]) for item in manifest["bindings"])
    for path in paths:
        destination = repo_root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)


def test_validator_accepts_fixture_only_adapter_boundary() -> None:
    summary = validate_openrouter_dry_run(Path("."))
    assert summary.case_count == 7
    assert summary.successful_case_count == 5
    assert summary.rejected_case_count == 2
    assert summary.live_provider_call_performed is False
    assert summary.live_provider_call_authorized is False
    assert summary.adapter_ready_for_authorization_review is True
    assert summary.tla_plus_reassessment_required is True


def test_validator_reads_no_openrouter_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-be-read")
    summary = validate_openrouter_dry_run(tmp_path)
    assert summary.credential_accessed is False


def test_validator_rejects_fixture_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = tmp_path / _FIXTURE
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(OpenRouterDryRunError, match="bound dry-run asset"):
        validate_openrouter_dry_run(tmp_path)


def test_validator_rejects_adapter_source_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = tmp_path / "src/auragateway/providers/openrouter.py"
    path.write_text(
        path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(OpenRouterDryRunError, match="bound dry-run asset"):
        validate_openrouter_dry_run(tmp_path)
