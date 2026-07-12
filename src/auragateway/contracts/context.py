"""Typed contracts for the static-anchor and volatile-append context boundary."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class ContextPartition(StrEnum):
    """Permitted context partitions."""

    STATIC = "static"
    VOLATILE = "volatile"


class StaticAnchorKind(StrEnum):
    """Stable artifact roles allowed in the prefix anchor registry."""

    BENCHMARK_POLICY = "benchmark_policy"
    RETRIEVAL_CONFIGURATION = "retrieval_configuration"
    EPISODE_MANIFEST = "episode_manifest"
    REVIEW_PROTOCOL = "review_protocol"
    TERMINAL_DECISION_CONSTITUTION = "terminal_decision_constitution"
    GATE_EVIDENCE = "gate_evidence"


class VolatileItemKind(StrEnum):
    """Append-only runtime event kinds."""

    USER_TURN = "user_turn"
    RETRIEVED_EVIDENCE = "retrieved_evidence"
    RETAINED_FEEDBACK = "retained_feedback"
    TOOL_RESULT = "tool_result"
    RUNTIME_STATE = "runtime_state"
    TERMINAL_DECISION = "terminal_decision"


class ContextDataClassification(StrEnum):
    """Data classes permitted inside the local synthetic harness."""

    SYNTHETIC_PUBLIC = "synthetic_public"
    SYNTHETIC_PROTECTED = "synthetic_protected"


class StaticAnchor(BaseModel):
    """One immutable, ordered artifact reference in the static prefix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str
    order: int = Field(ge=0)
    kind: StaticAnchorKind
    artifact_path: str
    artifact_sha256: str
    required: bool = True
    data_classification: ContextDataClassification
    content_in_public_trace: bool = False

    @field_validator("anchor_id")
    @classmethod
    def validate_anchor_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "anchor_id must use lowercase letters, digits, dots, underscores, or hyphens"
            )
        return value

    @field_validator("artifact_path")
    @classmethod
    def validate_artifact_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("artifact_path must be a safe repository-relative POSIX path")
        if not value.startswith(("data/", "docs/")):
            raise ValueError("artifact_path must live under data/ or docs/")
        return value

    @field_validator("artifact_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_trace_policy(self) -> StaticAnchor:
        if self.content_in_public_trace:
            raise ValueError("static anchor content must not be placed in public traces")
        return self


class StaticAnchorRegistry(BaseModel):
    """Frozen ordered registry defining the static context boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    registry_id: str = "auragateway-static-anchor-registry-v1"
    status: str = "candidate"
    partition: ContextPartition = ContextPartition.STATIC
    ordering_policy: str = "explicit-contiguous-order-v1"
    mutation_policy: str = "reject-after-run-start-v1"
    anchors: tuple[StaticAnchor, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_registry(self) -> StaticAnchorRegistry:
        anchor_ids = [anchor.anchor_id for anchor in self.anchors]
        paths = [anchor.artifact_path for anchor in self.anchors]
        for label, values in (("anchor IDs", anchor_ids), ("artifact paths", paths)):
            duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
            if duplicates:
                raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")
        expected_order = list(range(len(self.anchors)))
        actual_order = [anchor.order for anchor in self.anchors]
        if actual_order != expected_order:
            raise ValueError("anchor order must be contiguous, unique, and start at zero")
        required_kinds = {
            StaticAnchorKind.BENCHMARK_POLICY,
            StaticAnchorKind.RETRIEVAL_CONFIGURATION,
            StaticAnchorKind.EPISODE_MANIFEST,
            StaticAnchorKind.REVIEW_PROTOCOL,
            StaticAnchorKind.TERMINAL_DECISION_CONSTITUTION,
            StaticAnchorKind.GATE_EVIDENCE,
        }
        if {anchor.kind for anchor in self.anchors} != required_kinds:
            raise ValueError(
                "static anchor registry must contain each required anchor kind exactly once"
            )
        if self.partition is not ContextPartition.STATIC:
            raise ValueError("static anchor registry must use the static partition")
        return self


class VolatileAppendItem(BaseModel):
    """One append-only runtime context item referenced by content hash."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    sequence: int = Field(ge=0)
    kind: VolatileItemKind
    content_sha256: str
    content_bytes: int = Field(ge=1, le=1_000_000)
    data_classification: ContextDataClassification
    contains_personal_data: bool = False
    contains_secrets: bool = False
    retained: bool = True
    supersedes_item_id: str | None = None
    content_in_public_trace: bool = False

    @field_validator("item_id")
    @classmethod
    def validate_item_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "item_id must use lowercase letters, digits, dots, underscores, or hyphens"
            )
        return value

    @field_validator("content_sha256")
    @classmethod
    def validate_content_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("content_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_privacy(self) -> VolatileAppendItem:
        if self.contains_personal_data:
            raise ValueError("personal data is prohibited in the synthetic runtime context")
        if self.contains_secrets:
            raise ValueError("secrets are prohibited in the runtime context")
        if self.content_in_public_trace:
            raise ValueError("volatile content must not be placed in public traces")
        if self.supersedes_item_id == self.item_id:
            raise ValueError("an append item cannot supersede itself")
        return self


class VolatileAppendLog(BaseModel):
    """Ordered append-only runtime context log."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    run_id: str
    partition: ContextPartition = ContextPartition.VOLATILE
    append_policy: str = "append-only-no-in-place-mutation-v1"
    items: tuple[VolatileAppendItem, ...] = ()

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "run_id must use lowercase letters, digits, dots, underscores, or hyphens"
            )
        return value

    @model_validator(mode="after")
    def validate_log(self) -> VolatileAppendLog:
        if self.partition is not ContextPartition.VOLATILE:
            raise ValueError("volatile append log must use the volatile partition")
        item_ids = [item.item_id for item in self.items]
        duplicates = sorted(value for value, count in Counter(item_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate volatile item IDs: {', '.join(duplicates)}")
        if [item.sequence for item in self.items] != list(range(len(self.items))):
            raise ValueError("volatile item sequence must be contiguous and start at zero")
        available_ids: set[str] = set()
        terminal_decision_seen = False
        for item in self.items:
            if terminal_decision_seen:
                raise ValueError("no volatile items may follow a terminal decision")
            if item.supersedes_item_id is not None and item.supersedes_item_id not in available_ids:
                raise ValueError("supersedes_item_id must reference an earlier append item")
            if item.kind is VolatileItemKind.TERMINAL_DECISION:
                terminal_decision_seen = True
            available_ids.add(item.item_id)
        return self

    def append(self, item: VolatileAppendItem) -> VolatileAppendLog:
        """Return a new log after enforcing append-only identity and sequence rules."""

        if item.sequence != len(self.items):
            raise ValueError("new volatile item sequence must equal the current item count")
        if any(existing.item_id == item.item_id for existing in self.items):
            raise ValueError("new volatile item_id must be unique")
        return self.model_copy(update={"items": (*self.items, item)})


class ContextBoundaryManifest(BaseModel):
    """Hash-bound evidence for the pre-serialization context partition boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-context-boundary-manifest-v1"
    status: str = "candidate"
    static_registry_path: str
    static_registry_sha256: str
    static_anchor_count: int = Field(ge=1)
    volatile_contract_version: str = "volatile-append-v1"
    canonical_serialization_implemented: bool = False
    hmac_prefix_fingerprinting_implemented: bool = False
    gate_3_passed: bool = False
    measured_execution_permitted: bool = False

    @field_validator("static_registry_sha256")
    @classmethod
    def validate_registry_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("static_registry_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_boundary(self) -> ContextBoundaryManifest:
        if self.canonical_serialization_implemented:
            raise ValueError("this slice must not claim canonical serialization")
        if self.hmac_prefix_fingerprinting_implemented:
            raise ValueError("this slice must not claim HMAC prefix fingerprinting")
        if self.gate_3_passed or self.measured_execution_permitted:
            raise ValueError("context boundary alone cannot pass Gate 3 or permit execution")
        return self


class ContextBoundarySummary(BaseModel):
    """Safe machine-readable verification output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    registry_id: str
    static_anchor_count: int
    volatile_item_kind_count: int
    gate_3_passed: bool
    measured_execution_permitted: bool
    validation_status: str
