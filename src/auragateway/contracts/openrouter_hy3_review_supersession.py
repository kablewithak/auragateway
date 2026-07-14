"""Typed supersession overlay for historical OpenRouter Hy3 reviews."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.auragateway_v2_terminal_evidence_review import (
    OpenRouterHy3TerminalEvidenceReviewManifest,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class OpenRouterHy3SupersessionScope(StrEnum):
    """One historical hash-binding site delegated to a later manifest."""

    IDENTIFIABILITY_REVIEW_SOURCE = "identifiability_review_source"
    IDENTIFIABILITY_MANIFEST_ASSET = "identifiability_manifest_asset"
    AUTHORIZATION_REVIEW_SOURCE = "authorization_review_source"


class OpenRouterHy3SupersededPath(StrEnum):
    """Mutable governing documents superseded after the historical reviews."""

    MINI_PRD = (
        "docs/product/AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md"
    )
    CORE_PRD = "docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md"


class OpenRouterHy3SupersedingHashField(StrEnum):
    """Hash fields exposed by the later terminal-continuity manifest."""

    HY3_MINI_PRD_SHA256 = "hy3_mini_prd_sha256"
    CORE_PRD_SHA256 = "core_prd_sha256"


class OpenRouterHy3SupersessionBinding(BaseModel):
    """One exact historical binding delegated to the later manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: OpenRouterHy3SupersessionScope
    path: OpenRouterHy3SupersededPath
    historical_sha256: str
    superseding_hash_field: OpenRouterHy3SupersedingHashField

    @field_validator("historical_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("historical bindings require lowercase SHA-256")
        return value


class OpenRouterHy3HistoricalReviewSupersession(BaseModel):
    """Immutable overlay preserving history while validating current documents."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    supersession_id: Literal["openrouter-hy3-historical-review-supersession-v1"]
    identifiability_review_path: Literal[
        "data/evals/benchmark/openrouter-hy3-identifiability-review-v1/review.json"
    ]
    identifiability_review_sha256: str
    identifiability_manifest_path: Literal[
        "data/evals/benchmark/openrouter-hy3-identifiability-review-v1/manifest.json"
    ]
    identifiability_manifest_sha256: str
    authorization_review_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-authorization-review-v1/review.json"
    ]
    authorization_review_sha256: str
    authorization_manifest_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-authorization-review-v1/manifest.json"
    ]
    authorization_manifest_sha256: str
    superseding_manifest_path: Literal[
        "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/manifest.json"
    ]
    superseding_manifest_sha256: str
    authorization_runner_path: Literal[
        "src/auragateway/benchmark/openrouter_hy3_capability_probe_authorization_runner.py"
    ]
    authorization_runner_historical_sha256: str
    authorization_runner_superseding_sha256: str
    bindings: tuple[OpenRouterHy3SupersessionBinding, ...] = Field(
        min_length=4,
        max_length=4,
    )
    historical_evidence_mutation_permitted: Literal[False] = False
    provider_execution_reopened: Literal[False] = False

    @field_validator(
        "identifiability_review_sha256",
        "identifiability_manifest_sha256",
        "authorization_review_sha256",
        "authorization_manifest_sha256",
        "superseding_manifest_sha256",
        "authorization_runner_historical_sha256",
        "authorization_runner_superseding_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("supersession assets require lowercase SHA-256")
        return value

    @field_validator(
        "identifiability_review_path",
        "identifiability_manifest_path",
        "authorization_review_path",
        "authorization_manifest_path",
        "superseding_manifest_path",
    )
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("supersession paths must be repository-relative")
        return value

    @model_validator(mode="after")
    def validate_bindings(self) -> OpenRouterHy3HistoricalReviewSupersession:
        observed = {
            (binding.scope, binding.path, binding.superseding_hash_field)
            for binding in self.bindings
        }
        expected = {
            (
                OpenRouterHy3SupersessionScope.IDENTIFIABILITY_REVIEW_SOURCE,
                OpenRouterHy3SupersededPath.MINI_PRD,
                OpenRouterHy3SupersedingHashField.HY3_MINI_PRD_SHA256,
            ),
            (
                OpenRouterHy3SupersessionScope.IDENTIFIABILITY_REVIEW_SOURCE,
                OpenRouterHy3SupersededPath.CORE_PRD,
                OpenRouterHy3SupersedingHashField.CORE_PRD_SHA256,
            ),
            (
                OpenRouterHy3SupersessionScope.IDENTIFIABILITY_MANIFEST_ASSET,
                OpenRouterHy3SupersededPath.MINI_PRD,
                OpenRouterHy3SupersedingHashField.HY3_MINI_PRD_SHA256,
            ),
            (
                OpenRouterHy3SupersessionScope.AUTHORIZATION_REVIEW_SOURCE,
                OpenRouterHy3SupersededPath.MINI_PRD,
                OpenRouterHy3SupersedingHashField.HY3_MINI_PRD_SHA256,
            ),
        }
        if observed != expected:
            raise ValueError(
                "supersession requires the four exact historical binding sites"
            )
        if len(self.bindings) != len(observed):
            raise ValueError("supersession bindings must be unique")

        if self.authorization_runner_historical_sha256 != (
            "a409c28bb13ad70e51831007486995781b0708c191dc7dc5df582fe9c138d9a6"
        ):
            raise ValueError("authorization runner historical hash must remain frozen")

        expected_historical_hashes = {
            OpenRouterHy3SupersededPath.MINI_PRD: (
                "8d3604a65a94c50098e8e7d853e16b1ab21a5f9fdf8aaedf6e3d5ee7a793be0a"
            ),
            OpenRouterHy3SupersededPath.CORE_PRD: (
                "86acfc9bed13767a2869090d64fcabbfdf3da3b4bd156708afbd8f3919586409"
            ),
        }
        for binding in self.bindings:
            if binding.historical_sha256 != expected_historical_hashes[binding.path]:
                raise ValueError(
                    "supersession historical hash does not match frozen lineage"
                )
        return self


def superseding_hash(
    manifest: OpenRouterHy3TerminalEvidenceReviewManifest,
    field: OpenRouterHy3SupersedingHashField,
) -> str:
    """Resolve one allow-listed current-document hash from the later manifest."""

    if field is OpenRouterHy3SupersedingHashField.HY3_MINI_PRD_SHA256:
        return manifest.hy3_mini_prd_sha256
    if field is OpenRouterHy3SupersedingHashField.CORE_PRD_SHA256:
        return manifest.core_prd_sha256
    raise AssertionError(f"Unhandled superseding hash field: {field}")
