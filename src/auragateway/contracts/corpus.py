"""Typed contracts for the synthetic Nimbus Relay corpus inventory."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SOURCE_ID_PATTERN = re.compile(r"^NR-[A-Z][A-Z0-9-]*-[0-9]{3}$")


class DocumentFormat(StrEnum):
    """Permitted source-document formats."""

    MARKDOWN = "markdown"
    JSON = "json"


class DocumentStatus(StrEnum):
    """Lifecycle status for a corpus source."""

    CURRENT = "current"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    DRAFT = "draft"


class DocumentCompleteness(StrEnum):
    """Whether a source intentionally contains complete guidance."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class DataClassification(StrEnum):
    """Allowed data classification for the Phase 1 corpus."""

    SYNTHETIC_PUBLIC = "synthetic_public"


class CorpusMinimumRequirements(BaseModel):
    """Frozen minimum diagnostic requirements from the PRD."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_count: int = Field(default=30, ge=30)
    distinct_intent_categories: int = Field(default=10, ge=10)
    stale_document_count: int = Field(default=5, ge=5)
    conflicting_document_count: int = Field(default=5, ge=5)
    incomplete_document_count: int = Field(default=4, ge=4)
    near_duplicate_document_count: int = Field(default=4, ge=4)
    version_sensitive_document_count: int = Field(default=6, ge=6)


class CorpusSource(BaseModel):
    """One planned or authored Nimbus Relay corpus source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    document_path: str
    title: str = Field(min_length=5, max_length=160)
    version: str = Field(min_length=1, max_length=32)
    topic: str = Field(min_length=2, max_length=80)
    api_area: str = Field(min_length=2, max_length=80)
    status: DocumentStatus
    updated_at: datetime
    document_format: DocumentFormat
    intent_categories: tuple[str, ...] = Field(min_length=1)
    data_classification: DataClassification = DataClassification.SYNTHETIC_PUBLIC
    is_stale: bool = False
    conflict_group_id: str | None = None
    completeness: DocumentCompleteness = DocumentCompleteness.COMPLETE
    near_duplicate_group_id: str | None = None
    version_sensitive_procedure: bool = False
    supersedes_source_id: str | None = None
    contains_personal_data: bool = False
    contains_secrets: bool = False

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        if _SOURCE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("source_id must match NR-<AREA>-<NNN>")
        return value

    @field_validator("document_path")
    @classmethod
    def validate_document_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("document_path must be a safe repository-relative POSIX path")
        if not value.startswith("data/corpus/documents/"):
            raise ValueError("document_path must live under data/corpus/documents/")
        if path.suffix not in {".md", ".json"}:
            raise ValueError("document_path must end in .md or .json")
        return value

    @field_validator("intent_categories")
    @classmethod
    def validate_intent_categories(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(category.strip().lower() for category in value)
        if any(not category for category in normalized):
            raise ValueError("intent categories must not be empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("intent categories must be unique per source")
        return normalized

    @model_validator(mode="after")
    def validate_source_consistency(self) -> CorpusSource:
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("updated_at must include a timezone offset")
        if self.document_format is DocumentFormat.MARKDOWN and not self.document_path.endswith(
            ".md"
        ):
            raise ValueError("markdown sources must use a .md document path")
        if self.document_format is DocumentFormat.JSON and not self.document_path.endswith(".json"):
            raise ValueError("json sources must use a .json document path")
        stale_statuses = {DocumentStatus.DEPRECATED, DocumentStatus.SUPERSEDED}
        if self.is_stale and self.status not in stale_statuses:
            raise ValueError("stale sources must be deprecated or superseded")
        if not self.is_stale and self.status in stale_statuses:
            raise ValueError("deprecated or superseded sources must be marked stale")
        if self.contains_personal_data:
            raise ValueError("personal data is prohibited in the synthetic corpus")
        if self.contains_secrets:
            raise ValueError("secrets are prohibited in the synthetic corpus")
        if self.supersedes_source_id == self.source_id:
            raise ValueError("a source cannot supersede itself")
        return self


class CorpusInventory(BaseModel):
    """Versioned inventory and diagnostic constitution for the corpus."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    corpus_id: str
    corpus_version: str
    status: str
    minimum_requirements: CorpusMinimumRequirements
    sources: tuple[CorpusSource, ...]

    @model_validator(mode="after")
    def validate_inventory(self) -> CorpusInventory:
        source_ids = [source.source_id for source in self.sources]
        document_paths = [source.document_path for source in self.sources]

        self._require_unique(source_ids, "source_id")
        self._require_unique(document_paths, "document_path")

        requirements = self.minimum_requirements
        if len(self.sources) < requirements.document_count:
            raise ValueError("inventory does not meet the minimum document count")

        categories = {category for source in self.sources for category in source.intent_categories}
        if len(categories) < requirements.distinct_intent_categories:
            raise ValueError("inventory does not meet the minimum distinct intent-category count")

        stale_count = sum(source.is_stale for source in self.sources)
        conflict_count = sum(source.conflict_group_id is not None for source in self.sources)
        incomplete_count = sum(
            source.completeness is DocumentCompleteness.INCOMPLETE for source in self.sources
        )
        near_duplicate_count = sum(
            source.near_duplicate_group_id is not None for source in self.sources
        )
        version_sensitive_count = sum(source.version_sensitive_procedure for source in self.sources)

        thresholds = {
            "stale": (stale_count, requirements.stale_document_count),
            "conflicting": (conflict_count, requirements.conflicting_document_count),
            "incomplete": (incomplete_count, requirements.incomplete_document_count),
            "near-duplicate": (
                near_duplicate_count,
                requirements.near_duplicate_document_count,
            ),
            "version-sensitive": (
                version_sensitive_count,
                requirements.version_sensitive_document_count,
            ),
        }
        for label, (actual, required) in thresholds.items():
            if actual < required:
                raise ValueError(f"inventory requires at least {required} {label} documents")

        self._require_group_size(self.sources, "conflict_group_id")
        self._require_group_size(self.sources, "near_duplicate_group_id")

        available_ids = set(source_ids)
        for source in self.sources:
            if (
                source.supersedes_source_id is not None
                and source.supersedes_source_id not in available_ids
            ):
                raise ValueError(
                    f"{source.source_id} supersedes unknown source {source.supersedes_source_id}"
                )

        formats = {source.document_format for source in self.sources}
        if formats != {DocumentFormat.MARKDOWN, DocumentFormat.JSON}:
            raise ValueError("inventory must include both Markdown and JSON sources")

        return self

    @staticmethod
    def _require_unique(values: list[str], field_name: str) -> None:
        duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate {field_name} values: {', '.join(duplicates)}")

    @staticmethod
    def _require_group_size(sources: tuple[CorpusSource, ...], field_name: str) -> None:
        values = [getattr(source, field_name) for source in sources]
        counts = Counter(value for value in values if value is not None)
        singleton_groups = sorted(group for group, count in counts.items() if count < 2)
        if singleton_groups:
            raise ValueError(
                f"{field_name} groups must contain at least two sources: "
                f"{', '.join(singleton_groups)}"
            )

    def validation_summary(self) -> CorpusValidationSummary:
        """Return the safe machine-readable validation summary."""

        categories = {category for source in self.sources for category in source.intent_categories}
        return CorpusValidationSummary(
            schema_version=self.schema_version,
            corpus_id=self.corpus_id,
            corpus_version=self.corpus_version,
            status=self.status,
            document_count=len(self.sources),
            distinct_intent_categories=len(categories),
            stale_document_count=sum(source.is_stale for source in self.sources),
            conflicting_document_count=sum(
                source.conflict_group_id is not None for source in self.sources
            ),
            incomplete_document_count=sum(
                source.completeness is DocumentCompleteness.INCOMPLETE for source in self.sources
            ),
            near_duplicate_document_count=sum(
                source.near_duplicate_group_id is not None for source in self.sources
            ),
            version_sensitive_document_count=sum(
                source.version_sensitive_procedure for source in self.sources
            ),
            validation_status="valid",
        )


class CorpusValidationSummary(BaseModel):
    """Safe CLI output after successful inventory validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    corpus_id: str
    corpus_version: str
    status: str
    document_count: int
    distinct_intent_categories: int
    stale_document_count: int
    conflicting_document_count: int
    incomplete_document_count: int
    near_duplicate_document_count: int
    version_sensitive_document_count: int
    validation_status: str
