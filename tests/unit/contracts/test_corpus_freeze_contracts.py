from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from auragateway.contracts.corpus import DocumentFormat
from auragateway.contracts.corpus_freeze import (
    CorpusArtifactRecord,
    CorpusFreezeRecord,
    CorpusFreezeStatus,
    CorpusSourceManifest,
)

VALID_HASH = "a" * 64


def test_artifact_record_rejects_invalid_hash() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        CorpusArtifactRecord(
            source_id="NR-AUTH-001",
            document_path="data/corpus/documents/authentication/api-key-quickstart-v2.md",
            document_format=DocumentFormat.MARKDOWN,
            byte_count=100,
            sha256="not-a-hash",
        )


def test_manifest_rejects_duplicate_document_paths() -> None:
    artifact = CorpusArtifactRecord(
        source_id="NR-AUTH-001",
        document_path="data/corpus/documents/authentication/api-key-quickstart-v2.md",
        document_format=DocumentFormat.MARKDOWN,
        byte_count=100,
        sha256=VALID_HASH,
    )
    duplicate_path = artifact.model_copy(update={"source_id": "NR-AUTH-002"})

    with pytest.raises(ValidationError, match="duplicate artifact document_path"):
        CorpusSourceManifest(
            schema_version="1.0.0",
            corpus_id="nimbus-relay",
            corpus_version="1.0.0",
            status=CorpusFreezeStatus.FROZEN,
            inventory_path="data/corpus/source_inventory.json",
            inventory_sha256=VALID_HASH,
            artifacts=(artifact, duplicate_path),
        )


def test_freeze_record_rejects_invalid_manifest_hash() -> None:
    with pytest.raises(ValidationError, match="manifest_sha256"):
        CorpusFreezeRecord(
            schema_version="1.0.0",
            corpus_id="nimbus-relay",
            corpus_version="1.0.0",
            status=CorpusFreezeStatus.FROZEN,
            freeze_date=date(2026, 7, 12),
            inventory_path="data/corpus/source_inventory.json",
            inventory_sha256=VALID_HASH,
            manifest_path="data/corpus/source_manifest.json",
            manifest_sha256="bad",
            document_count=30,
            total_document_bytes=1000,
        )
