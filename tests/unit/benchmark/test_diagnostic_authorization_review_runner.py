from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.diagnostic_authorization_review_runner import (
    DiagnosticAuthorizationReviewError,
    validate_authorization_review,
)
from auragateway.benchmark.diagnostic_fixture_runner import (
    DiagnosticFixtureError,
    materialize_diagnostic_fixtures,
)

_DESIGN_ROOT = Path("data/evals/benchmark/diagnostic-design-v1")
_FIXTURE_ROOT = Path("data/evals/benchmark/diagnostic-fixtures-v1")
_REVIEW_ROOT = Path("data/evals/benchmark/diagnostic-authorization-review-v1")
_BATCH06_ROOT = Path("data/evals/benchmark/live-development-v6")


def _copy_file(repo_root: Path, relative_path: Path) -> None:
    destination = repo_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(relative_path, destination)


def _repo_fixture(tmp_path: Path) -> Path:
    for relative_path in (
        _DESIGN_ROOT / "experiment_plan.json",
        _DESIGN_ROOT / "manifest.json",
        _FIXTURE_ROOT / "fixture_recipe.json",
        _FIXTURE_ROOT / "fixture_manifest.json",
        _REVIEW_ROOT / "review_package.json",
        _REVIEW_ROOT / "dry_run_report.json",
        _REVIEW_ROOT / "manifest.json",
        _BATCH06_ROOT / "manifest.json",
        _BATCH06_ROOT / "report.json",
    ):
        _copy_file(tmp_path, relative_path)

    materialize_diagnostic_fixtures(tmp_path)
    return tmp_path


def test_validator_accepts_inactive_review(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)

    summary = validate_authorization_review(repo_root)

    assert summary.command == "validate"
    assert summary.status.value == "review_ready"
    assert summary.activation_state.value == "inactive"
    assert summary.sequence_count == 8
    assert summary.attempt_count == 24
    assert summary.minimum_planned_elapsed_seconds == 2220
    assert summary.provider_calls_made is False
    assert summary.authorization_created is False


def test_dry_run_command_remains_non_live(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = validate_authorization_review(
        repo_root,
        command="dry-run",
    )

    assert summary.command == "dry-run"
    assert summary.credential_accessed is False
    assert summary.provider_calls_permitted is False
    assert summary.execution_permitted is False


def test_validator_rejects_active_authorization_file(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    authorization_path = repo_root / _REVIEW_ROOT / "authorization.json"
    authorization_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        DiagnosticAuthorizationReviewError,
        match="active authorization file is forbidden",
    ):
        validate_authorization_review(repo_root)


def test_validator_rejects_batch07_assets(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    (repo_root / "data/evals/benchmark/live-development-v7").mkdir(parents=True)

    with pytest.raises(
        DiagnosticAuthorizationReviewError,
        match="Batch 07 assets are forbidden",
    ):
        validate_authorization_review(repo_root)


def test_validator_rejects_review_package_hash_drift(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    review_path = repo_root / _REVIEW_ROOT / "review_package.json"
    payload = cast(
        dict[str, object],
        json.loads(review_path.read_text(encoding="utf-8")),
    )
    bindings = payload["bindings"]
    assert isinstance(bindings, list)
    assert isinstance(bindings[0], dict)
    bindings[0]["sha256"] = "0" * 64
    review_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        DiagnosticAuthorizationReviewError,
        match="no longer matches its manifest",
    ):
        validate_authorization_review(repo_root)


def test_validator_rejects_dry_run_report_drift(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    report_path = repo_root / _REVIEW_ROOT / "dry_run_report.json"
    payload = cast(
        dict[str, object],
        json.loads(report_path.read_text(encoding="utf-8")),
    )
    attempts = payload["attempts"]
    assert isinstance(attempts, list)
    assert isinstance(attempts[0], dict)
    attempts[0]["prompt_byte_count"] = 7366
    report_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        DiagnosticAuthorizationReviewError,
        match="no longer matches its manifest",
    ):
        validate_authorization_review(repo_root)


def test_validator_rejects_protected_bundle_tamper(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    protected_path = repo_root / ".local/benchmark/diagnostic-fixtures-v1/prompt_cohorts.json"
    protected_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        DiagnosticFixtureError,
        match="failed typed validation",
    ):
        validate_authorization_review(repo_root)


def test_committed_schedule_has_expected_offsets() -> None:
    payload = cast(
        dict[str, object],
        json.loads((_REVIEW_ROOT / "dry_run_report.json").read_text(encoding="utf-8")),
    )
    attempts = payload["attempts"]
    assert isinstance(attempts, list)
    offsets = [
        cast(int, item["planned_offset_seconds"]) for item in attempts if isinstance(item, dict)
    ]

    assert offsets == [
        0,
        0,
        0,
        300,
        300,
        300,
        600,
        600,
        600,
        900,
        900,
        900,
        1200,
        1200,
        1200,
        1500,
        1530,
        1560,
        1860,
        1860,
        1860,
        2160,
        2190,
        2220,
    ]
