from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark import (
    cache_telemetry_calibration_review_runner as runner,
)
from auragateway.benchmark.cache_telemetry_calibration_review_runner import (
    CalibrationReviewError,
    dry_run_calibration_review,
    materialize_protected_prompt_bundle,
    validate_calibration_review,
    verify_calibration_review,
)

_REVIEW_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-review-v1")
_REPORT_PATH = Path(
    "docs/benchmark/AuraGateway_Cache_Telemetry_Calibration_Authorization_Review.md"
)


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _copy_review_assets(repo_root: Path) -> None:
    for relative_path in (
        _REVIEW_ROOT / "prompt_recipe.json",
        _REVIEW_ROOT / "review.json",
        _REVIEW_ROOT / "dry_run_report.json",
        _REVIEW_ROOT / "manifest.json",
        _REPORT_PATH,
    ):
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
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def _repo_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    _copy_review_assets(tmp_path)
    monkeypatch.setattr(
        runner,
        "_validate_source_bindings",
        lambda repo_root, review: None,
    )
    monkeypatch.setattr(
        runner,
        "_validate_hardening_state",
        lambda repo_root: None,
    )
    return tmp_path


def test_validate_accepts_inactive_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)

    summary = validate_calibration_review(repo_root)

    assert summary.command == "validate"
    assert summary.planned_attempt_count == 3
    assert summary.unique_provider_request_count == 1
    assert summary.protected_bundle_verified is False
    assert summary.provider_call_performed is False
    assert summary.credential_accessed is False
    assert summary.execution_command_available is False


def test_dry_run_reproduces_three_attempt_schedule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)

    summary = dry_run_calibration_review(repo_root)

    assert summary.command == "dry-run"
    assert summary.planned_attempt_count == 3
    assert summary.calibration_execution_authorized is False


def test_materialize_and_verify_protected_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)

    materialized = materialize_protected_prompt_bundle(repo_root)
    verified = verify_calibration_review(repo_root)

    protected_path = (
        repo_root / ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    )
    assert protected_path.is_file()
    assert materialized.protected_bundle_verified is True
    assert verified.command == "verify"
    assert verified.protected_bundle_verified is True


def test_materialize_does_not_read_groq_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = materialize_protected_prompt_bundle(repo_root)

    assert summary.credential_accessed is False
    assert summary.provider_call_performed is False


def test_materialize_rejects_conflicting_protected_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    protected_path = (
        repo_root / ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    )
    protected_path.parent.mkdir(parents=True)
    protected_path.write_text("different bytes\n", encoding="utf-8")

    with pytest.raises(
        CalibrationReviewError,
        match="different bytes",
    ):
        materialize_protected_prompt_bundle(repo_root)


def test_validate_rejects_review_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    review_path = repo_root / _REVIEW_ROOT / "review.json"
    review_path.write_text(
        review_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationReviewError,
        match="asset no longer matches",
    ):
        validate_calibration_review(repo_root)


def test_validate_rejects_prompt_reproduction_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    recipe_path = repo_root / _REVIEW_ROOT / "prompt_recipe.json"
    recipe = _json_object(recipe_path)
    recipe["system_prompt_sha256"] = "0" * 64
    recipe_path.write_text(
        json.dumps(recipe, indent=2) + "\n",
        encoding="utf-8",
    )
    _refresh_manifest_hash(
        repo_root,
        field_name="prompt_recipe_sha256",
        relative_path=_REVIEW_ROOT / "prompt_recipe.json",
    )

    with pytest.raises(
        CalibrationReviewError,
        match="did not reproduce",
    ):
        validate_calibration_review(repo_root)


def test_validate_rejects_source_binding_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_review_assets(tmp_path)
    monkeypatch.setattr(
        runner,
        "_validate_hardening_state",
        lambda repo_root: None,
    )
    monkeypatch.setattr(
        runner,
        "_git_blob_sha1",
        lambda repo_root, commit, path: "0" * 40,
    )

    with pytest.raises(
        CalibrationReviewError,
        match="source no longer matches",
    ):
        validate_calibration_review(tmp_path)


def test_verify_rejects_protected_bundle_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    materialize_protected_prompt_bundle(repo_root)
    protected_path = (
        repo_root / ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    )
    protected_path.write_text(
        protected_path.read_text(encoding="utf-8") + "tamper\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationReviewError,
        match="no longer matches the review",
    ):
        verify_calibration_review(repo_root)
