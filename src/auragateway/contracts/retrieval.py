"""Typed contracts for deterministic sparse retrieval."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.corpus import DocumentCompleteness, DocumentStatus
from auragateway.contracts.retrieval_metadata import (
    RetrievalMetadataFilter,
    SourceRetrievalMetadata,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_QUERY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


class RetrievalAlgorithm(StrEnum):
    """Supported sparse retrieval algorithms."""

    BM25 = "bm25"


class RetrievalCandidateStatus(StrEnum):
    """Lifecycle state for retrieval candidates."""

    CANDIDATE = "candidate"


class StalePolicy(StrEnum):
    """How source staleness affects candidate eligibility."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
    ONLY = "only"


class RetrievalFilter(BaseModel):
    """Typed metadata filters applied before BM25 scoring."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_areas: tuple[str, ...] = ()
    source_statuses: tuple[DocumentStatus, ...] = ()
    completeness: tuple[DocumentCompleteness, ...] = ()
    source_ids: tuple[str, ...] = ()
    stale_policy: StalePolicy = StalePolicy.INCLUDE
    version_sensitive_only: bool = False
    metadata: RetrievalMetadataFilter | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @field_validator("api_areas", "source_ids")
    @classmethod
    def normalize_string_filters(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("string filter values must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("string filter values must be unique")
        return normalized

    @field_validator("source_statuses", "completeness")
    @classmethod
    def require_unique_enum_filters(cls, value: tuple[object, ...]) -> tuple[object, ...]:
        if len(value) != len(set(value)):
            raise ValueError("enum filter values must be unique")
        return value


class RetrievalConfiguration(BaseModel):
    """Frozen inputs for one BM25 candidate over one chunking strategy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    config_id: str = Field(min_length=3, max_length=80)
    algorithm: RetrievalAlgorithm = RetrievalAlgorithm.BM25
    chunking_config_id: str = Field(min_length=3, max_length=80)
    tokenizer_id: str = "unicode-alnum-casefold-v1"
    k1: float = Field(default=1.2, gt=0.0, le=5.0)
    b: float = Field(default=0.75, ge=0.0, le=1.0)
    default_top_k: int = Field(default=5, ge=1, le=50)
    score_precision: int = Field(default=12, ge=6, le=15)
    minimum_score: float = Field(default=0.0, ge=0.0)
    idf_variant: str = "bm25-positive-idf-v1"
    filter_order: str = "metadata-before-scoring-global-idf-v1"
    tie_break_policy: str = "score-desc-source-id-chunk-index-chunk-id-v1"


class RetrievalQuery(BaseModel):
    """One retrieval request at the deterministic sparse boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_id: str
    query_text: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    filters: RetrievalFilter = RetrievalFilter()

    @field_validator("query_id")
    @classmethod
    def validate_query_id(cls, value: str) -> str:
        if _QUERY_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("query_id must use lowercase letters, digits, hyphens, or underscores")
        return value

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query_text must not be blank")
        return normalized


class BM25TermContribution(BaseModel):
    """Inspectable term-level contribution to one BM25 hit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    term: str = Field(min_length=1)
    query_term_frequency: int = Field(ge=1)
    document_frequency: int = Field(ge=1)
    chunk_term_frequency: int = Field(ge=1)
    idf: float = Field(ge=0.0)
    score: float = Field(gt=0.0)


class RetrievalHit(BaseModel):
    """One runtime retrieval hit with content for downstream context construction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rank: int = Field(ge=1)
    score: float = Field(gt=0.0)
    chunk_id: str
    source_id: str
    document_path: str
    source_version: str
    source_status: DocumentStatus
    api_area: str
    is_stale: bool
    completeness: DocumentCompleteness
    version_sensitive_procedure: bool
    retrieval_metadata: SourceRetrievalMetadata | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    chunk_index: int = Field(ge=0)
    parent_headings: tuple[str, ...]
    content: str = Field(min_length=1)
    content_sha256: str
    matched_terms: tuple[str, ...] = Field(min_length=1)
    term_contributions: tuple[BM25TermContribution, ...] = Field(min_length=1)

    @field_validator("content_sha256")
    @classmethod
    def validate_content_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("content_sha256 must contain 64 lowercase hexadecimal characters")
        return value


class RetrievalResult(BaseModel):
    """Runtime retrieval response with deterministic ranking evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    query_id: str
    query_sha256: str
    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    top_k: int = Field(ge=1)
    filters: RetrievalFilter
    candidate_count: int = Field(ge=0)
    positive_score_count: int = Field(ge=0)
    hits: tuple[RetrievalHit, ...]

    @model_validator(mode="after")
    def validate_result(self) -> RetrievalResult:
        for name, value in (
            ("query_sha256", self.query_sha256),
            ("retriever_config_sha256", self.retriever_config_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
        if len(self.hits) > self.top_k:
            raise ValueError("hit count must not exceed top_k")
        expected_ranks = list(range(1, len(self.hits) + 1))
        if [hit.rank for hit in self.hits] != expected_ranks:
            raise ValueError("hit ranks must be contiguous and start at one")
        chunk_ids = [hit.chunk_id for hit in self.hits]
        duplicates = sorted(value for value, count in Counter(chunk_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate hit chunk IDs: {', '.join(duplicates)}")
        scores = [hit.score for hit in self.hits]
        if scores != sorted(scores, reverse=True):
            raise ValueError("hit scores must be non-increasing")
        if self.positive_score_count < len(self.hits):
            raise ValueError("positive_score_count must be at least the returned hit count")
        if self.candidate_count < self.positive_score_count:
            raise ValueError("candidate_count must be at least positive_score_count")
        return self


class RetrievalEvidenceHit(BaseModel):
    """Content-free ranking evidence safe for persisted candidate artifacts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rank: int = Field(ge=1)
    score: float = Field(gt=0.0)
    chunk_id: str
    source_id: str
    document_path: str
    source_version: str
    source_status: DocumentStatus
    api_area: str
    is_stale: bool
    retrieval_metadata: SourceRetrievalMetadata | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    chunk_index: int = Field(ge=0)
    parent_headings: tuple[str, ...]
    matched_terms: tuple[str, ...] = Field(min_length=1)


class RetrievalEvidenceResult(BaseModel):
    """Content-free smoke-query evidence persisted for reproducibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    query_id: str
    query_sha256: str
    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    top_k: int
    filters: RetrievalFilter
    candidate_count: int
    positive_score_count: int
    hits: tuple[RetrievalEvidenceHit, ...]


class RetrievalSmokeQuerySet(BaseModel):
    """Versioned development-only smoke queries for deterministic checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    query_set_id: str = Field(min_length=3, max_length=80)
    status: str = "development_smoke_only"
    queries: tuple[RetrievalQuery, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_query_set(self) -> RetrievalSmokeQuerySet:
        query_ids = [query.query_id for query in self.queries]
        duplicates = sorted(value for value, count in Counter(query_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate query IDs: {', '.join(duplicates)}")
        return self


class RetrievalIndexManifest(BaseModel):
    """Hash and index-statistics evidence for one sparse retrieval candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    corpus_id: str
    corpus_version: str
    status: RetrievalCandidateStatus = RetrievalCandidateStatus.CANDIDATE
    config: RetrievalConfiguration
    config_sha256: str
    chunking_manifest_path: str
    chunking_manifest_sha256: str
    chunks_path: str
    chunks_sha256: str
    smoke_queries_path: str
    smoke_queries_sha256: str
    smoke_results_path: str
    smoke_results_sha256: str
    source_document_count: int = Field(ge=1)
    chunk_count: int = Field(ge=1)
    total_index_tokens: int = Field(ge=1)
    vocabulary_size: int = Field(ge=1)
    average_chunk_length: float = Field(gt=0.0)
    smoke_query_count: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_manifest(self) -> RetrievalIndexManifest:
        for name, value in (
            ("config_sha256", self.config_sha256),
            ("chunking_manifest_sha256", self.chunking_manifest_sha256),
            ("chunks_sha256", self.chunks_sha256),
            ("smoke_queries_sha256", self.smoke_queries_sha256),
            ("smoke_results_sha256", self.smoke_results_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
        return self


class RetrievalRunSummary(BaseModel):
    """Safe machine-readable build or verification output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    corpus_id: str
    corpus_version: str
    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    source_document_count: int
    chunk_count: int
    total_index_tokens: int
    vocabulary_size: int
    average_chunk_length: float
    smoke_query_count: int
    smoke_results_sha256: str
    validation_status: str
