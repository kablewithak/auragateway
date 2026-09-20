from __future__ import annotations

import hashlib
import json
import shutil
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import j7l_groq_schema_accounting_probe_v1 as subject

_REVIEW_ROOT = Path("data/evals/quality/j7l-groq-schema-accounting-review-v1")
_SUCCESSOR = Path(
    "docs/benchmark/AuraGateway_J7L_Model_Derived_Reference_Successor_Constitution_v1.md"
)


def _json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _string(payload: dict[str, object], key: str) -> str:
    value = payload[key]
    assert isinstance(value, str)
    return value


def _copy_assets(repo_root: Path) -> None:
    manifest = _json(_REVIEW_ROOT / "manifest.json")
    paths = [
        Path(_string(manifest, "probe_plan_path")),
        Path(_string(manifest, "review_path")),
        Path(_string(manifest, "dry_run_report_path")),
        Path(_string(manifest, "strict_response_schema_path")),
        Path(_string(manifest, "synthetic_prompt_recipe_path")),
        Path(_string(manifest, "preactivation_measurements_path")),
        Path(_string(manifest, "adr_path")),
        Path(_string(manifest, "report_path")),
        _REVIEW_ROOT / "manifest.json",
        _SUCCESSOR,
    ]
    for relative in paths:
        destination = repo_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative, destination)


def _refresh_manifest_hash(
    repo_root: Path,
    field: str,
    relative_path: Path,
) -> None:
    manifest_path = repo_root / _REVIEW_ROOT / "manifest.json"
    manifest = _json(manifest_path)
    manifest[field] = hashlib.sha256((repo_root / relative_path).read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_validate_review_is_non_live(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setattr(importlib_metadata, "version", lambda name: "1.5.0")
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    result = subject.validate_review(tmp_path)

    assert result["status"] == "J7L_GROQ_SCHEMA_ACCOUNTING_REVIEW_PASS"
    assert result["planned_attempt_count"] == 2
    assert result["provider_call_performed"] is False
    assert result["credential_accessed"] is False
    assert result["execution_command_available"] is False
    assert result["j7l_reference_request_permitted"] is False


def test_dry_run_preserves_attempt_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    result = subject.dry_run(tmp_path)

    assert result["attempt_roles"] == (
        "control_no_response_format",
        "strict_json_schema",
    )
    assert result["attempt_offsets_seconds"] == (0, 10)
    assert result["provider_call_performed"] is False


def test_validate_rejects_manifest_bound_asset_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setattr(importlib_metadata, "version", lambda name: "1.5.0")
    plan_path = tmp_path / _REVIEW_ROOT / "probe_plan.json"
    plan_path.write_text(
        plan_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        subject.SchemaAccountingReviewError,
        match="no longer matches its manifest",
    ):
        subject.validate_review(tmp_path)


def test_validate_rejects_sdk_version_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setattr(importlib_metadata, "version", lambda name: "1.6.0")

    with pytest.raises(
        subject.SchemaAccountingReviewError,
        match="installed Groq SDK",
    ):
        subject.validate_review(tmp_path)


def test_runner_exposes_no_execution_function() -> None:
    assert not hasattr(subject, "execute")
    assert not hasattr(subject, "execute_probe")
    assert not hasattr(subject, "execute_schema_accounting_probe")
