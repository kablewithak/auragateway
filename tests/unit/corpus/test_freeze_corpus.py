from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.corpus.freeze import (
    CorpusFreezeError,
    build_source_manifest,
    main,
    verify_frozen_corpus,
    write_freeze_assets,
)

REPO_ROOT = Path(".")
INVENTORY_PATH = Path("data/corpus/source_inventory.json")
MANIFEST_PATH = Path("data/corpus/source_manifest.json")
FREEZE_RECORD_PATH = Path("data/corpus/corpus_freeze_record.json")


def _copy_corpus_fixture(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "data" / "corpus", repo_root / "data" / "corpus")
    return repo_root


def test_verify_frozen_corpus_returns_complete_summary() -> None:
    summary = verify_frozen_corpus(REPO_ROOT)

    assert summary.status.value == "frozen"
    assert summary.document_count == 30
    assert summary.total_document_bytes > 20_000
    assert summary.stale_document_count == 5
    assert summary.conflicting_document_count == 6
    assert summary.incomplete_document_count == 4
    assert summary.near_duplicate_document_count == 4
    assert summary.version_sensitive_document_count == 9
    assert summary.validation_status == "valid"


def test_build_source_manifest_is_deterministic() -> None:
    first = build_source_manifest(REPO_ROOT, INVENTORY_PATH)
    second = build_source_manifest(REPO_ROOT, INVENTORY_PATH)

    assert first == second
    assert len(first.artifacts) == 30
    assert tuple(item.document_path for item in first.artifacts) == tuple(
        sorted(item.document_path for item in first.artifacts)
    )


def test_verify_rejects_tampered_document(tmp_path: Path) -> None:
    repo_root = _copy_corpus_fixture(tmp_path)
    document_path = repo_root / "data/corpus/documents/authentication/api-key-quickstart-v2.md"
    document_path.write_text(
        document_path.read_text(encoding="utf-8") + "\nTampered.\n",
        encoding="utf-8",
    )

    with pytest.raises(CorpusFreezeError) as exc_info:
        verify_frozen_corpus(repo_root)

    assert exc_info.value.error_code == "CORPUS_SOURCE_MANIFEST_MISMATCH"


def test_verify_rejects_missing_document(tmp_path: Path) -> None:
    repo_root = _copy_corpus_fixture(tmp_path)
    missing_path = repo_root / "data/corpus/documents/events/event-types.md"
    missing_path.unlink()

    with pytest.raises(CorpusFreezeError) as exc_info:
        verify_frozen_corpus(repo_root)

    assert exc_info.value.error_code == "CORPUS_DOCUMENT_SET_MISMATCH"
    assert any(detail.startswith("missing:") for detail in exc_info.value.details)


def test_verify_rejects_extra_document(tmp_path: Path) -> None:
    repo_root = _copy_corpus_fixture(tmp_path)
    extra_path = repo_root / "data/corpus/documents/events/unplanned.md"
    extra_path.write_text("# Unplanned\n", encoding="utf-8")

    with pytest.raises(CorpusFreezeError) as exc_info:
        verify_frozen_corpus(repo_root)

    assert exc_info.value.error_code == "CORPUS_DOCUMENT_SET_MISMATCH"
    assert any(detail.startswith("extra:") for detail in exc_info.value.details)


def test_build_rejects_document_metadata_mismatch(tmp_path: Path) -> None:
    repo_root = _copy_corpus_fixture(tmp_path)
    document_path = repo_root / "data/corpus/documents/webhooks/delivery-and-retries-v3.md"
    content = document_path.read_text(encoding="utf-8")
    document_path.write_text(content.replace("version: 3.0", "version: 9.9", 1), encoding="utf-8")

    with pytest.raises(CorpusFreezeError) as exc_info:
        build_source_manifest(repo_root, INVENTORY_PATH)

    assert exc_info.value.error_code == "CORPUS_DOCUMENT_METADATA_MISMATCH"


def test_write_freeze_assets_rebuilds_same_evidence(tmp_path: Path) -> None:
    repo_root = _copy_corpus_fixture(tmp_path)
    (repo_root / MANIFEST_PATH).unlink()
    (repo_root / FREEZE_RECORD_PATH).unlink()

    summary = write_freeze_assets(repo_root)
    persisted_manifest = json.loads((repo_root / MANIFEST_PATH).read_text(encoding="utf-8"))

    assert summary.document_count == 30
    assert len(persisted_manifest["artifacts"]) == 30
    assert verify_frozen_corpus(repo_root) == summary


def test_cli_verify_prints_typed_summary(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "frozen"
    assert payload["document_count"] == 30
    assert payload["validation_status"] == "valid"
