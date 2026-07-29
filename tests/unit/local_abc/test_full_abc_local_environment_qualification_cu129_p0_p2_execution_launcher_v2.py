"""Tests for the governed CUDA 12.9 P0-P2 execution launcher V2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_p0_p2_execution_launcher_v2 as subject,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )


def _write_fixture_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    template_source = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "auragateway"
        / "local_abc"
        / "templates"
        / subject.LAUNCHER_TEMPLATE_PATH.name
    )
    template_target = repo_root / subject.LAUNCHER_TEMPLATE_PATH
    template_target.parent.mkdir(parents=True, exist_ok=True)
    template_target.write_bytes(template_source.read_bytes())

    source_root = Path(__file__).resolve().parents[3]
    bindings = (
        (subject.DIAGNOSTIC_NOTEBOOK_PATH, subject.EXPECTED_DIAGNOSTIC_NOTEBOOK_SHA256),
        (subject.DIAGNOSTIC_REQUEST_PATH, subject.EXPECTED_DIAGNOSTIC_REQUEST_SHA256),
        (
            subject.DIAGNOSTIC_IMPLEMENTATION_PATH,
            subject.EXPECTED_IMPLEMENTATION_RECORD_SHA256,
        ),
    )
    for relative, expected_sha in bindings:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        assert _sha256(target) == expected_sha

    _write_json(
        repo_root / subject.SOURCE_MATERIALIZATION_RECORD_PATH,
        {
            "status": "P0_P2_SOURCE_MATERIALIZATION_TOOLCHAIN_V2_VALID",
            "source_bundle_sha256": subject.EXPECTED_SOURCE_BUNDLE_SHA256,
            "source_inventory_sha256": subject.EXPECTED_SOURCE_INVENTORY_SHA256,
            "output_directory_name": "ag_cu129_p0_p2_source_materializer_v2_output",
            "output_dataset_name": "ag-cu129-p0-p2-source-v2",
        },
    )
    _write_json(repo_root / subject.SOURCE_MATERIALIZATION_REVIEW_PATH, {"ok": True})
    review_target = repo_root / subject.REVIEW_RECORD_PATH
    review_target.parent.mkdir(parents=True, exist_ok=True)
    review_target.write_bytes((source_root / subject.REVIEW_RECORD_PATH).read_bytes())
    return repo_root


def _code_source(notebook_bytes: bytes) -> str:
    raw = json.loads(notebook_bytes.decode("utf-8"))
    assert isinstance(raw, dict)
    cells = raw["cells"]
    assert isinstance(cells, list)
    code_cell = cells[1]
    assert isinstance(code_cell, dict)
    source = code_cell["source"]
    assert isinstance(source, list)
    return "".join(str(line) for line in source)


def test_kaggle_names_fit_limit() -> None:
    names = (
        subject.LAUNCHER_NOTEBOOK_NAME,
        subject.FAILED_LAUNCHER_NOTEBOOK_NAME,
    )
    assert all(len(name) <= subject.MAXIMUM_KAGGLE_NAME_CHARACTERS for name in names)


def test_generated_launcher_is_deterministic(tmp_path: Path) -> None:
    repo_root = _write_fixture_repo(tmp_path)
    first = subject.build_generated_launcher(repo_root)
    second = subject.build_generated_launcher(repo_root)
    assert first.notebook_bytes == second.notebook_bytes
    assert first.record == second.record


def test_generated_launcher_compiles_and_respects_line_policy(tmp_path: Path) -> None:
    generated = subject.build_generated_launcher(_write_fixture_repo(tmp_path))
    source = _code_source(generated.notebook_bytes)
    compile(source, "launcher", "exec")
    assert max(len(line) for line in source.splitlines()) <= 100
    assert "lines.extend([" not in source


def test_generated_launcher_is_unexecuted(tmp_path: Path) -> None:
    generated = subject.build_generated_launcher(_write_fixture_repo(tmp_path))
    raw = json.loads(generated.notebook_bytes.decode("utf-8"))
    assert isinstance(raw, dict)
    cells = raw["cells"]
    assert isinstance(cells, list)
    assert len(cells) == 2
    code_cell = cells[1]
    assert isinstance(code_cell, dict)
    assert code_cell["outputs"] == []
    assert code_cell["execution_count"] is None


def test_launcher_supports_direct_notebook_output_lineage(tmp_path: Path) -> None:
    generated = subject.build_generated_launcher(_write_fixture_repo(tmp_path))
    source = _code_source(generated.notebook_bytes)
    assert "INPUT_ROOT.rglob(SOURCE_RECEIPT_NAME)" in source
    assert generated.record.direct_notebook_output_attachment is True
    assert generated.record.standalone_kaggle_dataset_required is False


def test_launcher_has_one_execution_attempt_and_zero_model_budget(tmp_path: Path) -> None:
    generated = subject.build_generated_launcher(_write_fixture_repo(tmp_path))
    source = _code_source(generated.notebook_bytes)
    assert source.count("diagnostic_execution_attempts += 1") == 1
    assert generated.record.execution_budget.maximum_diagnostic_executions == 1
    assert generated.record.execution_budget.maximum_model_loads == 0
    assert generated.record.execution_budget.maximum_worker_starts == 0
    assert generated.record.execution_budget.maximum_model_requests == 0
    assert generated.record.execution_budget.maximum_benchmark_trajectory_requests == 0


def test_source_identity_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _write_fixture_repo(tmp_path)
    (repo_root / subject.DIAGNOSTIC_NOTEBOOK_PATH).write_bytes(b"tampered")
    with pytest.raises(
        subject.P0P2ExecutionLauncherV2Error,
        match="identity",
    ):
        subject.build_generated_launcher(repo_root)


def test_review_rejects_standalone_dataset_requirement() -> None:
    payload = json.loads(
        (Path(__file__).resolve().parents[3] / subject.REVIEW_RECORD_PATH).read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(payload, dict)
    payload["standalone_kaggle_dataset_required"] = True
    with pytest.raises(ValidationError):
        subject.ExecutionLauncherReviewRecord.model_validate(payload)


def test_generation_and_validation_end_to_end(tmp_path: Path) -> None:
    repo_root = _write_fixture_repo(tmp_path)
    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)
    assert validated == generated


def test_validation_rejects_generated_notebook_drift(tmp_path: Path) -> None:
    repo_root = _write_fixture_repo(tmp_path)
    subject.generate(repo_root)
    (repo_root / subject.LAUNCHER_NOTEBOOK_PATH).write_bytes(b"drift")
    with pytest.raises(subject.P0P2ExecutionLauncherV2Error, match="differs"):
        subject.validate(repo_root)
