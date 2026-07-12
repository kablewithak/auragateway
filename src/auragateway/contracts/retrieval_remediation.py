"""Typed contracts for retrieval metadata remediation evidence."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.dense_retrieval import DenseRetrievalConfiguration
from auragateway.contracts.retrieval import RetrievalConfiguration
from auragateway.contracts.retrieval_eval import RetrievalAggregateMetrics

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class RemediationAlgorithm(StrEnum):
    """Retriever families included in the remediation comparison."""

    BM25 = "bm25"
    DENSE_HASHED_TFIDF = "dense_hashed_tfidf"


class RetrievalRemediationManifest(BaseModel):
    """Hash-bound inputs for one remediated development candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str
    status: str = "development_remediation_candidate"
    algorithm: RemediationAlgorithm
    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    bm25_config: RetrievalConfiguration | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    dense_config: DenseRetrievalConfiguration | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    chunks_path: str
    chunks_sha256: str
    source_metadata_path: str
    source_metadata_sha256: str
    development_set_path: str
    development_set_sha256: str
    rejected_set_path: str
    rejected_set_sha256: str
    source_document_count: int = Field(ge=1)
    chunk_count: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_manifest(self) -> RetrievalRemediationManifest:
        for name, value in (
            ("retriever_config_sha256", self.retriever_config_sha256),
            ("chunks_sha256", self.chunks_sha256),
            ("source_metadata_sha256", self.source_metadata_sha256),
            ("development_set_sha256", self.development_set_sha256),
            ("rejected_set_sha256", self.rejected_set_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain lowercase SHA-256")
        if self.algorithm is RemediationAlgorithm.BM25:
            if self.bm25_config is None or self.dense_config is not None:
                raise ValueError("BM25 remediation manifest requires only bm25_config")
            if self.bm25_config.config_id != self.retriever_config_id:
                raise ValueError("BM25 config ID must match retriever_config_id")
        else:
            if self.dense_config is None or self.bm25_config is not None:
                raise ValueError("dense remediation manifest requires only dense_config")
            if self.dense_config.config_id != self.retriever_config_id:
                raise ValueError("dense config ID must match retriever_config_id")
        return self


class RemediationScorecardReference(BaseModel):
    """Hash reference and aggregate metrics for one before or after scorecard."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: str
    retriever_config_id: str
    scorecard_path: str
    scorecard_sha256: str
    aggregate: RetrievalAggregateMetrics

    @field_validator("scorecard_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("scorecard_sha256 must contain lowercase SHA-256")
        return value


class RetrievalRemediationReport(BaseModel):
    """Before/after development evidence without reopening held-out v1."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str = "nimbus-relay-retrieval-remediation-v1"
    status: str = "development_remediation_complete"
    metadata_registry_path: str
    metadata_registry_sha256: str
    development_v1_path: str
    development_v1_sha256: str
    development_v2_path: str
    development_v2_sha256: str
    held_out_v1_path: str
    held_out_v1_sha256: str
    before_scorecards: tuple[RemediationScorecardReference, ...] = Field(min_length=2, max_length=2)
    after_scorecards: tuple[RemediationScorecardReference, ...] = Field(min_length=2, max_length=2)
    remediated_case_ids: tuple[str, ...] = Field(min_length=1)
    resolved_development_case_ids: tuple[str, ...]
    remaining_development_failure_ids: tuple[str, ...]
    gate_1_status: str = "blocked_pending_held_out_v2"
    held_out_v1_modified: bool = False
    held_out_v2_required: bool = True
    retrieval_freeze_permitted: bool = False
    measured_execution_permitted: bool = False

    @model_validator(mode="after")
    def validate_report(self) -> RetrievalRemediationReport:
        for name, value in (
            ("metadata_registry_sha256", self.metadata_registry_sha256),
            ("development_v1_sha256", self.development_v1_sha256),
            ("development_v2_sha256", self.development_v2_sha256),
            ("held_out_v1_sha256", self.held_out_v1_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain lowercase SHA-256")
        if self.held_out_v1_modified:
            raise ValueError("held-out v1 must remain unchanged")
        if not self.held_out_v2_required:
            raise ValueError("held-out v2 must remain required after remediation")
        if self.retrieval_freeze_permitted or self.measured_execution_permitted:
            raise ValueError("development remediation cannot permit freeze or execution")
        return self


class RetrievalRemediationSummary(BaseModel):
    """Safe CLI build or verification output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str
    remediated_candidate_count: int
    development_case_count: int
    remediated_case_count: int
    resolved_case_count: int
    remaining_failure_count: int
    gate_1_status: str
    held_out_v2_required: bool
    retrieval_freeze_permitted: bool
    validation_status: str
