"""Typed contracts for deterministic corpus chunking candidates."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.contracts.corpus import (
    DocumentCompleteness,
    DocumentFormat,
    DocumentStatus,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CHUNK_ID_PATTERN = re.compile(r"^chunk-[0-9a-f]{24}$")


class ChunkingStrategy(StrEnum):
    """Supported deterministic chunking candidates."""

    FIXED_WINDOW = "fixed_window"
    SECTION_AWARE = "section_aware"


class ChunkingCandidateStatus(StrEnum):
    """Lifecycle state for generated chunking candidates."""

    CANDIDATE = "candidate"


class ChunkingConfiguration(BaseModel):
    """Frozen inputs for one deterministic chunking candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    config_id: str = Field(min_length=3, max_length=80)
    strategy: ChunkingStrategy
    target_tokens: int = Field(ge=16, le=2048)
    overlap_tokens: int = Field(ge=0, le=512)
    minimum_fallback_tokens: int = Field(ge=1, le=512)
    tokenizer_id: str = "lexical-whitespace-v1"
    preserve_parent_headings: bool

    @model_validator(mode="after")
    def validate_window(self) -> ChunkingConfiguration:
        if self.overlap_tokens >= self.target_tokens:
            raise ValueError("overlap_tokens must be smaller than target_tokens")
        if self.minimum_fallback_tokens > self.target_tokens:
            raise ValueError("minimum_fallback_tokens must not exceed target_tokens")
        if self.strategy is ChunkingStrategy.FIXED_WINDOW and self.preserve_parent_headings:
            raise ValueError("fixed-window chunking does not preserve parent headings")
        if self.strategy is ChunkingStrategy.SECTION_AWARE and not self.preserve_parent_headings:
            raise ValueError("section-aware chunking must preserve parent headings")
        return self


class CorpusChunk(BaseModel):
    """One deterministic chunk derived from a frozen corpus source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    chunk_id: str
    source_id: str
    document_path: str
    source_version: str
    document_format: DocumentFormat
    api_area: str
    source_status: DocumentStatus
    is_stale: bool
    conflict_group_id: str | None
    completeness: DocumentCompleteness
    near_duplicate_group_id: str | None
    version_sensitive_procedure: bool
    strategy: ChunkingStrategy
    config_id: str
    config_sha256: str
    chunk_index: int = Field(ge=0)
    parent_headings: tuple[str, ...] = ()
    content: str = Field(min_length=1)
    token_count: int = Field(ge=1)
    character_count: int = Field(ge=1)
    content_sha256: str

    @model_validator(mode="after")
    def validate_chunk(self) -> CorpusChunk:
        if _CHUNK_ID_PATTERN.fullmatch(self.chunk_id) is None:
            raise ValueError("chunk_id must match chunk-<24 lowercase hex characters>")
        for name, value in (
            ("config_sha256", self.config_sha256),
            ("content_sha256", self.content_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
        if len(self.content) != self.character_count:
            raise ValueError("character_count must match content length")
        if self.strategy is ChunkingStrategy.FIXED_WINDOW and self.parent_headings:
            raise ValueError("fixed-window chunks must not contain parent headings")
        return self


class SourceChunkCount(BaseModel):
    """Chunk-count evidence for one frozen source document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    chunk_count: int = Field(ge=1)


class ChunkingManifest(BaseModel):
    """Hash and count evidence for one generated chunking candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    corpus_id: str
    corpus_version: str
    status: ChunkingCandidateStatus = ChunkingCandidateStatus.CANDIDATE
    strategy: ChunkingStrategy
    config: ChunkingConfiguration
    config_sha256: str
    corpus_manifest_path: str
    corpus_manifest_sha256: str
    chunks_path: str
    chunks_sha256: str
    source_document_count: int = Field(ge=1)
    chunk_count: int = Field(ge=1)
    total_chunk_tokens: int = Field(ge=1)
    source_chunk_counts: tuple[SourceChunkCount, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> ChunkingManifest:
        for name, value in (
            ("config_sha256", self.config_sha256),
            ("corpus_manifest_sha256", self.corpus_manifest_sha256),
            ("chunks_sha256", self.chunks_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
        if self.config.strategy is not self.strategy:
            raise ValueError("manifest strategy must match configuration strategy")
        source_ids = [item.source_id for item in self.source_chunk_counts]
        duplicates = sorted(value for value, count in Counter(source_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate source chunk counts: {', '.join(duplicates)}")
        if len(self.source_chunk_counts) != self.source_document_count:
            raise ValueError("source_document_count must match source_chunk_counts")
        if sum(item.chunk_count for item in self.source_chunk_counts) != self.chunk_count:
            raise ValueError("chunk_count must match the per-source chunk counts")
        return self


class ChunkingRunSummary(BaseModel):
    """Safe machine-readable output from candidate build or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    corpus_id: str
    corpus_version: str
    strategy: ChunkingStrategy
    config_id: str
    config_sha256: str
    source_document_count: int
    chunk_count: int
    total_chunk_tokens: int
    chunks_sha256: str
    validation_status: str
