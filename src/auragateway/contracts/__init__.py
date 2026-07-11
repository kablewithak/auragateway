"""Typed boundary contracts for AuraGateway."""

from auragateway.contracts.chunking import (
    ChunkingCandidateStatus,
    ChunkingConfiguration,
    ChunkingManifest,
    ChunkingRunSummary,
    ChunkingStrategy,
    CorpusChunk,
    SourceChunkCount,
)
from auragateway.contracts.corpus import (
    CorpusInventory,
    CorpusMinimumRequirements,
    CorpusSource,
    CorpusValidationSummary,
    DataClassification,
    DocumentCompleteness,
    DocumentFormat,
    DocumentStatus,
)
from auragateway.contracts.corpus_freeze import (
    CorpusArtifactRecord,
    CorpusDocumentHeader,
    CorpusFreezeRecord,
    CorpusFreezeStatus,
    CorpusFreezeSummary,
    CorpusSourceManifest,
)

__all__ = [
    "ChunkingCandidateStatus",
    "ChunkingConfiguration",
    "ChunkingManifest",
    "ChunkingRunSummary",
    "ChunkingStrategy",
    "CorpusArtifactRecord",
    "CorpusChunk",
    "CorpusDocumentHeader",
    "CorpusFreezeRecord",
    "CorpusFreezeStatus",
    "CorpusFreezeSummary",
    "CorpusInventory",
    "CorpusMinimumRequirements",
    "CorpusSource",
    "CorpusSourceManifest",
    "CorpusValidationSummary",
    "DataClassification",
    "DocumentCompleteness",
    "DocumentFormat",
    "DocumentStatus",
    "SourceChunkCount",
]
