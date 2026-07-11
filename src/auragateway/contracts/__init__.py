"""Typed boundary contracts for AuraGateway."""

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
    "CorpusArtifactRecord",
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
]
