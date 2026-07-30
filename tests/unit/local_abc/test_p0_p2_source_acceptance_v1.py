"""Tests for corrected P0-P2 source acceptance integration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

import auragateway.local_abc.p0_p2_source_acceptance_v1 as subject


def _copy_evidence_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    for relative in subject.BOUND_EVIDENCE_PATHS:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def test_saved_version_bindings_are_exact() -> None:
    assert subject.MATERIALIZER_SAVED_VERSION_ID == 339075357
    assert subject.INSPECTION_SAVED_VERSION_ID == 339077364
    assert subject.MATERIALIZER_SAVED_VERSION_URL == (
        "https://www.kaggle.com/code/kabomolefe/"
        "ag-cu129-p0-p2-source-materializer-v2?scriptVersionId=339075357"
    )
    assert subject.INSPECTION_SAVED_VERSION_URL == (
        "https://www.kaggle.com/code/kabomolefe/"
        "ag-cu129-p0-p2-source-inspection-v2/log?scriptVersionId=339077364"
    )


def test_acceptance_record_build_is_deterministic(tmp_path: Path) -> None:
    repo_root = _copy_evidence_repo(tmp_path)
    first = subject.build_acceptance_record(repo_root)
    second = subject.build_acceptance_record(repo_root)
    assert first == second
    assert first.canonical_json() == second.canonical_json()


def test_generation_and_validation_end_to_end(tmp_path: Path) -> None:
    repo_root = _copy_evidence_repo(tmp_path)
    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)
    assert validated == generated


def test_tampered_materializer_log_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_evidence_repo(tmp_path)
    (repo_root / subject.MATERIALIZER_LOG_PATH).write_bytes(b"tampered")
    with pytest.raises(
        subject.P0P2SourceAcceptanceError,
        match="identity",
    ):
        subject.build_acceptance_record(repo_root)


def test_tampered_inspection_archive_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_evidence_repo(tmp_path)
    (repo_root / subject.INSPECTION_EVIDENCE_ZIP_PATH).write_bytes(b"tampered")
    with pytest.raises(
        subject.P0P2SourceAcceptanceError,
        match="identity",
    ):
        subject.build_acceptance_record(repo_root)


def test_acceptance_contract_rejects_wrong_saved_version(tmp_path: Path) -> None:
    repo_root = _copy_evidence_repo(tmp_path)
    payload = json.loads(subject.build_acceptance_record(repo_root).canonical_json())
    assert isinstance(payload, dict)
    materializer = payload["materializer"]
    assert isinstance(materializer, dict)
    materializer["saved_version_id"] = 1
    with pytest.raises(ValidationError):
        subject.P0P2SourceAcceptanceRecord.model_validate(payload)
