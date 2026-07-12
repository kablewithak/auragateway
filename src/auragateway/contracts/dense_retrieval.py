"""Typed contracts for the deterministic local dense retrieval baseline."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.corpus import DocumentCompleteness, DocumentStatus
from auragateway.contracts.retrieval import RetrievalFilter
from auragateway.contracts.retrieval_metadata import SourceRetrievalMetadata

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DenseEncoderAlgorithm(StrEnum):
    """Supported local dense-vector construction algorithms."""

    HASHED_TFIDF = "hashed_tfidf"


class DenseCandidateStatus(StrEnum):
    """Lifecycle state for generated dense retrieval candidates."""

    CANDIDATE = "candidate"


class DenseRetrievalConfiguration(BaseModel):
    """Frozen inputs for one deterministic local dense retrieval candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    config_id: str = Field(min_length=3, max_length=100)
    chunking_config_id: str = Field(min_length=3, max_length=80)
    algorithm: DenseEncoderAlgorithm = DenseEncoderAlgorithm.HASHED_TFIDF
    encoder_id: str = "hashed-tfidf-dense-v1"
    tokenizer_id: str = "unicode-alnum-casefold-v1"
    vector_dimension: int = Field(default=384, ge=64, le=4096)
    minimum_ngram: int = Field(default=1, ge=1, le=3)
    maximum_ngram: int = Field(default=2, ge=1, le=3)
    sublinear_term_frequency: bool = True
    idf_variant: str = "smooth-log-idf-v1"
    feature_hash_variant: str = "sha256-signed-bucket-v1"
    normalization: str = "l2-v1"
    similarity: str = "cosine-v1"
    default_top_k: int = Field(default=5, ge=1, le=50)
    score_precision: int = Field(default=12, ge=6, le=15)
    minimum_similarity: float = Field(default=0.0, ge=0.0, lt=1.0)
    filter_order: str = "metadata-before-similarity-global-idf-v1"
    tie_break_policy: str = "score-desc-source-id-chunk-index-chunk-id-v1"

    @model_validator(mode="after")
    def validate_ngram_range(self) -> DenseRetrievalConfiguration:
        if self.minimum_ngram > self.maximum_ngram:
            raise ValueError("minimum_ngram must not exceed maximum_ngram")
        return self


class DenseSimilarityEvidence(BaseModel):
    """Inspectable numeric evidence for one dense similarity score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_nonzero_dimensions: int = Field(ge=1)
    chunk_nonzero_dimensions: int = Field(ge=1)
    shared_nonzero_dimensions: int = Field(ge=1)
    cosine_similarity: float = Field(gt=0.0, le=1.0)


class DenseRetrievalHit(BaseModel):
    """One runtime dense retrieval hit with content for downstream context construction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rank: int = Field(ge=1)
    score: float = Field(gt=0.0, le=1.0)
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
    similarity_evidence: DenseSimilarityEvidence

    @field_validator("content_sha256")
    @classmethod
    def validate_content_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("content_sha256 must contain 64 lowercase hexadecimal characters")
        return value


class DenseRetrievalResult(BaseModel):
    """Runtime dense retrieval response with deterministic ranking evidence."""

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
    hits: tuple[DenseRetrievalHit, ...]

    @model_validator(mode="after")
    def validate_result(self) -> DenseRetrievalResult:
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


class DenseRetrievalEvidenceHit(BaseModel):
    """Content-free dense ranking evidence safe for persisted artifacts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rank: int = Field(ge=1)
    score: float = Field(gt=0.0, le=1.0)
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
    similarity_evidence: DenseSimilarityEvidence


class DenseRetrievalEvidenceResult(BaseModel):
    """Content-free dense smoke evidence persisted for reproducibility."""

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
    hits: tuple[DenseRetrievalEvidenceHit, ...]


class DenseIndexManifest(BaseModel):
    """Hash and index-statistics evidence for one dense retrieval candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    corpus_id: str
    corpus_version: str
    status: DenseCandidateStatus = DenseCandidateStatus.CANDIDATE
    config: DenseRetrievalConfiguration
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
    vocabulary_size: int = Field(ge=1)
    vector_dimension: int = Field(ge=64)
    average_nonzero_dimensions: float = Field(gt=0.0)
    smoke_query_count: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_manifest(self) -> DenseIndexManifest:
        for name, value in (
            ("config_sha256", self.config_sha256),
            ("chunking_manifest_sha256", self.chunking_manifest_sha256),
            ("chunks_sha256", self.chunks_sha256),
            ("smoke_queries_sha256", self.smoke_queries_sha256),
            ("smoke_results_sha256", self.smoke_results_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
        if self.vector_dimension != self.config.vector_dimension:
            raise ValueError("vector_dimension must match the dense configuration")
        return self


class DenseRunSummary(BaseModel):
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
    vocabulary_size: int
    vector_dimension: int
    average_nonzero_dimensions: float
    smoke_query_count: int
    smoke_results_sha256: str
    validation_status: str
