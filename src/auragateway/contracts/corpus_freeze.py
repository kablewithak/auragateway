"""Typed contracts for corpus document metadata and freeze evidence."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.contracts.corpus import (
    DocumentCompleteness,
    DocumentFormat,
    DocumentStatus,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CorpusFreezeStatus(StrEnum):
    """Lifecycle states for corpus freeze artifacts."""

    FROZEN = "frozen"


class CorpusDocumentHeader(BaseModel):
    """Metadata embedded in one authored corpus document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    version: str
    status: DocumentStatus
    updated_at: datetime
    document_format: DocumentFormat
    api_area: str
    is_stale: bool
    conflict_group_id: str | None
    completeness: DocumentCompleteness
    near_duplicate_group_id: str | None
    version_sensitive_procedure: bool


class CorpusArtifactRecord(BaseModel):
    """Hash evidence for one authored source document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    document_path: str
    document_format: DocumentFormat
    byte_count: int = Field(gt=0)
    sha256: str

    @model_validator(mode="after")
    def validate_hash(self) -> CorpusArtifactRecord:
        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError("sha256 must contain 64 lowercase hexadecimal characters")
        return self


class CorpusSourceManifest(BaseModel):
    """Versioned hash manifest for the complete corpus source set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    corpus_id: str
    corpus_version: str
    status: CorpusFreezeStatus
    inventory_path: str
    inventory_sha256: str
    artifacts: tuple[CorpusArtifactRecord, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> CorpusSourceManifest:
        if _SHA256_PATTERN.fullmatch(self.inventory_sha256) is None:
            raise ValueError("inventory_sha256 must be a valid lowercase SHA-256")

        source_ids = [artifact.source_id for artifact in self.artifacts]
        paths = [artifact.document_path for artifact in self.artifacts]
        self._require_unique(source_ids, "source_id")
        self._require_unique(paths, "document_path")
        return self

    @staticmethod
    def _require_unique(values: list[str], label: str) -> None:
        duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate artifact {label} values: {', '.join(duplicates)}")


class CorpusFreezeRecord(BaseModel):
    """Top-level immutable identity for the frozen corpus manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    corpus_id: str
    corpus_version: str
    status: CorpusFreezeStatus
    freeze_date: date
    inventory_path: str
    inventory_sha256: str
    manifest_path: str
    manifest_sha256: str
    document_count: int = Field(ge=1)
    total_document_bytes: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_hashes(self) -> CorpusFreezeRecord:
        for name, value in (
            ("inventory_sha256", self.inventory_sha256),
            ("manifest_sha256", self.manifest_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must be a valid lowercase SHA-256")
        return self


class CorpusFreezeSummary(BaseModel):
    """Safe machine-readable result from frozen corpus verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    corpus_id: str
    corpus_version: str
    status: CorpusFreezeStatus
    document_count: int
    total_document_bytes: int
    inventory_sha256: str
    manifest_sha256: str
    stale_document_count: int
    conflicting_document_count: int
    incomplete_document_count: int
    near_duplicate_document_count: int
    version_sensitive_document_count: int
    validation_status: str
