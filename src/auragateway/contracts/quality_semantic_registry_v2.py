"""Typed semantic registry for quality-evaluator contract v2."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.blinded_quality import RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SemanticSourceReferenceV2(FrozenModel):
    """One auditable source supporting a semantic definition."""

    source_kind: Literal["executable", "benchmark", "normative"]
    repository_path: str = Field(min_length=1, max_length=500)
    locator: str = Field(min_length=1, max_length=500)

    @field_validator("repository_path")
    @classmethod
    def validate_repository_path(cls, value: str) -> str:
        path = value.strip()
        if not path:
            raise ValueError("semantic source repository path must not be blank")
        if path.startswith("/") or "\\" in path:
            raise ValueError("semantic source repository path must be repo-relative POSIX")
        if ".." in path.split("/"):
            raise ValueError("semantic source repository path must not traverse parents")
        return path

    @field_validator("locator")
    @classmethod
    def validate_locator(cls, value: str) -> str:
        locator = value.strip()
        if not locator:
            raise ValueError("semantic source locator must not be blank")
        return locator


class CriterionSemanticDefinitionV2(FrozenModel):
    """One criterion's complete evaluator-facing semantic contract."""

    criterion: RubricCriterion
    description: str = Field(min_length=20, max_length=1000)
    applicability_rule: str = Field(min_length=20, max_length=2000)
    non_substantive_response_rule: str = Field(min_length=20, max_length=2000)
    score_1_anchor: str = Field(min_length=10, max_length=1000)
    score_2_anchor: str = Field(min_length=10, max_length=1000)
    score_3_anchor: str = Field(min_length=10, max_length=1000)
    score_4_anchor: str = Field(min_length=10, max_length=1000)
    boundary_notes: tuple[str, ...] = Field(min_length=1)
    semantic_sources: tuple[SemanticSourceReferenceV2, ...] = Field(min_length=1)

    @field_validator("boundary_notes")
    @classmethod
    def validate_boundary_notes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("criterion boundary notes must not contain blanks")
        if len(normalized) != len(set(normalized)):
            raise ValueError("criterion boundary notes must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_semantic_sources(self) -> CriterionSemanticDefinitionV2:
        identities = tuple(
            (source.source_kind, source.repository_path, source.locator)
            for source in self.semantic_sources
        )
        if len(identities) != len(set(identities)):
            raise ValueError("criterion semantic sources must be unique")
        return self


class FailureLabelSemanticDefinitionV2(FrozenModel):
    """One failure label's complete operational semantic contract."""

    label: EpisodeFailureLabel
    operational_definition: str = Field(min_length=20, max_length=2000)
    applies_when: tuple[str, ...] = Field(min_length=1)
    does_not_apply_when: tuple[str, ...] = Field(min_length=1)
    related_labels: tuple[EpisodeFailureLabel, ...] = ()
    semantic_sources: tuple[SemanticSourceReferenceV2, ...] = Field(min_length=1)
    positive_example: str = Field(min_length=20, max_length=3000)
    near_miss_example: str = Field(min_length=20, max_length=3000)

    @field_validator("applies_when", "does_not_apply_when")
    @classmethod
    def validate_rules(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("failure-label rules must not contain blanks")
        if len(normalized) != len(set(normalized)):
            raise ValueError("failure-label rules must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_label_contract(self) -> FailureLabelSemanticDefinitionV2:
        if self.label in self.related_labels:
            raise ValueError("failure label must not relate to itself")

        if len(self.related_labels) != len(set(self.related_labels)):
            raise ValueError("related failure labels must be unique")

        source_identities = tuple(
            (source.source_kind, source.repository_path, source.locator)
            for source in self.semantic_sources
        )
        if len(source_identities) != len(set(source_identities)):
            raise ValueError("failure-label semantic sources must be unique")

        return self


class QualitySemanticRegistryV2(FrozenModel):
    """Canonical semantic contract shared by human and model evaluators."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    registry_id: Literal["auragateway-quality-semantic-registry-v2"] = (
        "auragateway-quality-semantic-registry-v2"
    )
    criteria: tuple[CriterionSemanticDefinitionV2, ...] = Field(
        min_length=len(RubricCriterion),
        max_length=len(RubricCriterion),
    )
    failure_labels: tuple[FailureLabelSemanticDefinitionV2, ...] = Field(
        min_length=len(EpisodeFailureLabel),
        max_length=len(EpisodeFailureLabel),
    )

    @model_validator(mode="after")
    def validate_inventory(self) -> QualitySemanticRegistryV2:
        criterion_inventory = tuple(item.criterion for item in self.criteria)
        if len(criterion_inventory) != len(set(criterion_inventory)):
            raise ValueError("semantic registry criteria must be unique")
        if set(criterion_inventory) != set(RubricCriterion):
            raise ValueError("semantic registry must define every rubric criterion exactly once")

        failure_inventory = tuple(item.label for item in self.failure_labels)
        if len(failure_inventory) != len(set(failure_inventory)):
            raise ValueError("semantic registry failure labels must be unique")
        if set(failure_inventory) != set(EpisodeFailureLabel):
            raise ValueError("semantic registry must define every failure label exactly once")

        return self

    def canonical_bytes(self) -> bytes:
        """Return stable bytes used to bind all semantic-registry consumers."""
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    def sha256(self) -> str:
        """Return the canonical registry digest."""
        return hashlib.sha256(self.canonical_bytes()).hexdigest()
