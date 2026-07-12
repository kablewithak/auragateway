"""Typed source metadata used for deterministic retrieval pre-filtering."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SOURCE_ID_PATTERN = re.compile(r"^NR-[A-Z][A-Z0-9-]*-[0-9]{3}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SourceLanguage(StrEnum):
    """Language or runtime identity required to apply a source correctly."""

    LANGUAGE_AGNOSTIC = "language_agnostic"
    PYTHON = "python"
    JAVASCRIPT = "javascript"


class InterfaceKind(StrEnum):
    """Primary interface described by a source."""

    GENERAL = "general"
    RAW_HTTP = "raw_http"
    SDK = "sdk"


class OAuthGrantKind(StrEnum):
    """OAuth grant semantics described by a source."""

    NOT_APPLICABLE = "not_applicable"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"


class RepresentationKind(StrEnum):
    """How the source is intended to be consumed."""

    HUMAN_GUIDE = "human_guide"
    MACHINE_REFERENCE = "machine_reference"


class SourceRetrievalMetadata(BaseModel):
    """Typed retrieval discriminators for one frozen source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    language: SourceLanguage = SourceLanguage.LANGUAGE_AGNOSTIC
    interface_kind: InterfaceKind = InterfaceKind.GENERAL
    oauth_grant: OAuthGrantKind = OAuthGrantKind.NOT_APPLICABLE
    representation: RepresentationKind

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        if _SOURCE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("source_id must match NR-<AREA>-<NNN>")
        return value

    @model_validator(mode="after")
    def validate_semantics(self) -> SourceRetrievalMetadata:
        if (
            self.language is not SourceLanguage.LANGUAGE_AGNOSTIC
            and self.interface_kind is not InterfaceKind.SDK
        ):
            raise ValueError("language-specific sources must use the SDK interface kind")
        if (
            self.oauth_grant is not OAuthGrantKind.NOT_APPLICABLE
            and self.interface_kind is not InterfaceKind.RAW_HTTP
        ):
            raise ValueError("OAuth-grant sources must use the raw_http interface kind")
        return self


class SourceRetrievalMetadataRegistry(BaseModel):
    """Hash-bound metadata overlay for the frozen corpus."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    registry_id: str = "nimbus-relay-retrieval-metadata-v1"
    status: str = "development_remediation"
    corpus_id: str = "nimbus-relay"
    corpus_version: str = "1.0.0"
    corpus_manifest_path: str = "data/corpus/source_manifest.json"
    corpus_manifest_sha256: str
    entries: tuple[SourceRetrievalMetadata, ...] = Field(min_length=30, max_length=30)

    @field_validator("corpus_manifest_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("corpus_manifest_sha256 must contain lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_entries(self) -> SourceRetrievalMetadataRegistry:
        source_ids = [entry.source_id for entry in self.entries]
        duplicates = sorted(
            source_id for source_id, count in Counter(source_ids).items() if count > 1
        )
        if duplicates:
            raise ValueError(f"duplicate metadata source IDs: {', '.join(duplicates)}")
        return self

    def by_source_id(self) -> dict[str, SourceRetrievalMetadata]:
        """Return an immutable-model lookup for retrieval indexes."""

        return {entry.source_id: entry for entry in self.entries}


class RetrievalMetadataFilter(BaseModel):
    """Optional exact-match source discriminators applied before ranking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    languages: tuple[SourceLanguage, ...] = ()
    interface_kinds: tuple[InterfaceKind, ...] = ()
    oauth_grants: tuple[OAuthGrantKind, ...] = ()
    representations: tuple[RepresentationKind, ...] = ()

    @field_validator("languages", "interface_kinds", "oauth_grants", "representations")
    @classmethod
    def require_unique_values(cls, value: tuple[object, ...]) -> tuple[object, ...]:
        if len(value) != len(set(value)):
            raise ValueError("retrieval metadata filter values must be unique")
        return value
