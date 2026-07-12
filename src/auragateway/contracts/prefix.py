"""Typed contracts for canonical static-prefix compilation and Gate 3 evidence."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.context import (
    ContextDataClassification,
    StaticAnchorKind,
    VolatileAppendLog,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class StaticSegmentKind(StrEnum):
    """Stable text segment roles permitted in the provider prefix."""

    SYSTEM_POLICY = "system_policy"
    TASK_PROCEDURE = "task_procedure"
    CITATION_RULES = "citation_rules"
    FEW_SHOT_EXAMPLE = "few_shot_example"


class SchemaValueType(StrEnum):
    """Provider-neutral scalar and collection types for static contracts."""

    STRING = "string"
    STRING_LIST = "string_list"
    ENUM = "enum"
    BOOLEAN = "boolean"


class PrefixMutationReason(StrEnum):
    """Allowed reasons for a detected static-prefix mutation."""

    TEMPLATE_VERSION_CHANGED = "template_version_changed"
    TOOL_CONTRACT_CHANGED = "tool_contract_changed"
    OUTPUT_SCHEMA_CHANGED = "output_schema_changed"
    CONTEXT_PACK_CHANGED = "context_pack_changed"
    SERIALIZATION_ORDER_CHANGED = "serialization_order_changed"
    FORBIDDEN_VOLATILE_FIELD_DETECTED = "forbidden_volatile_field_detected"
    PROVIDER_SERIALIZATION_CHANGED = "provider_serialization_changed"
    UNKNOWN = "unknown"


class PrefixMutationKind(StrEnum):
    """Required Gate 3 negative-control mutations and metamorphic controls."""

    TIMESTAMP_INSERTION = "timestamp_insertion"
    TOOL_ORDER_CHANGE = "tool_order_change"
    OUTPUT_SCHEMA_VERSION_CHANGE = "output_schema_version_change"
    JSON_KEY_ORDER_CHANGE = "json_key_order_change"
    ONE_BYTE_EXAMPLE_CHANGE = "one_byte_example_change"
    VOLATILE_USER_CONTENT_CHANGE = "volatile_user_content_change"
    RETRIEVAL_ORDER_CHANGE = "retrieval_order_change"


class PrefixMutationOutcome(StrEnum):
    """Observed and expected negative-control outcomes."""

    BLOCKED = "blocked"
    FINGERPRINT_CHANGED = "fingerprint_changed"
    STATIC_FINGERPRINT_UNCHANGED = "static_fingerprint_unchanged"
    CANONICALLY_EQUIVALENT = "canonically_equivalent"


class StaticTextSegment(BaseModel):
    """One stable textual segment in the provider prefix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_id: str
    order: int = Field(ge=0)
    kind: StaticSegmentKind
    content: str = Field(min_length=1, max_length=20_000)
    data_classification: ContextDataClassification = ContextDataClassification.SYNTHETIC_PROTECTED
    content_in_public_trace: bool = False

    @field_validator("segment_id")
    @classmethod
    def validate_segment_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("segment_id must use lowercase stable identifier characters")
        return value

    @model_validator(mode="after")
    def validate_trace_policy(self) -> StaticTextSegment:
        if self.content_in_public_trace:
            raise ValueError("static segment content must not be placed in public traces")
        return self


class ToolInputField(BaseModel):
    """One ordered field in a provider-neutral tool input contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    order: int = Field(ge=0)
    name: str
    value_type: SchemaValueType
    required: bool
    description: str = Field(min_length=1, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("tool field name must be a stable identifier")
        return value


class ToolContractSpec(BaseModel):
    """One ordered stable tool contract included in the provider prefix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    order: int = Field(ge=0)
    tool_id: str
    version: str
    description: str = Field(min_length=1, max_length=1_000)
    input_fields: tuple[ToolInputField, ...] = Field(min_length=1)

    @field_validator("tool_id")
    @classmethod
    def validate_tool_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("tool_id must be a stable identifier")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("tool version must be a stable version identifier")
        return value

    @model_validator(mode="after")
    def validate_fields(self) -> ToolContractSpec:
        field_names = [field.name for field in self.input_fields]
        duplicates = sorted(value for value, count in Counter(field_names).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate tool field names: {', '.join(duplicates)}")
        if [field.order for field in self.input_fields] != list(range(len(self.input_fields))):
            raise ValueError("tool input field order must be contiguous and start at zero")
        return self


class OutputSchemaField(BaseModel):
    """One ordered field in the structured terminal-decision output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    order: int = Field(ge=0)
    name: str
    value_type: SchemaValueType
    required: bool
    enum_values: tuple[str, ...] = ()

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("output schema field name must be a stable identifier")
        return value

    @model_validator(mode="after")
    def validate_enum_values(self) -> OutputSchemaField:
        if self.value_type is SchemaValueType.ENUM and not self.enum_values:
            raise ValueError("enum output fields must declare enum_values")
        if self.value_type is not SchemaValueType.ENUM and self.enum_values:
            raise ValueError("non-enum output fields must not declare enum_values")
        if len(self.enum_values) != len(set(self.enum_values)):
            raise ValueError("enum_values must be unique")
        return self


class OutputSchemaSpec(BaseModel):
    """Versioned structured-output schema included in the static prefix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_id: str
    version: str
    fields: tuple[OutputSchemaField, ...] = Field(min_length=1)

    @field_validator("schema_id")
    @classmethod
    def validate_schema_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("schema_id must be a stable identifier")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("output schema version must be a stable version identifier")
        return value

    @model_validator(mode="after")
    def validate_fields(self) -> OutputSchemaSpec:
        names = [field.name for field in self.fields]
        duplicates = sorted(value for value, count in Counter(names).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate output schema field names: {', '.join(duplicates)}")
        if [field.order for field in self.fields] != list(range(len(self.fields))):
            raise ValueError("output schema field order must be contiguous and start at zero")
        return self


class ContextPackSpec(BaseModel):
    """Approved reusable stable context pack."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_pack_id: str
    version: str
    content: str = Field(min_length=1, max_length=20_000)
    data_classification: ContextDataClassification = ContextDataClassification.SYNTHETIC_PROTECTED
    content_in_public_trace: bool = False

    @field_validator("context_pack_id")
    @classmethod
    def validate_context_pack_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("context_pack_id must be a stable identifier")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("context pack version must be a stable version identifier")
        return value

    @model_validator(mode="after")
    def validate_trace_policy(self) -> ContextPackSpec:
        if self.content_in_public_trace:
            raise ValueError("context pack content must not be placed in public traces")
        return self


class StaticCompilerSpec(BaseModel):
    """Complete versioned input to canonical provider-prefix serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    spec_id: str = "auragateway-static-compiler-spec-v1"
    status: str = "frozen"
    serialization_version: str = "canonical-static-provider-v1"
    template_id: str
    template_version: str
    tool_contract_version: str
    static_registry_path: str
    static_registry_sha256: str
    segments: tuple[StaticTextSegment, ...] = Field(min_length=4)
    tools: tuple[ToolContractSpec, ...] = Field(min_length=1)
    output_schema: OutputSchemaSpec
    context_pack: ContextPackSpec
    raw_content_in_public_trace: bool = False

    @field_validator(
        "spec_id",
        "template_id",
        "serialization_version",
        "tool_contract_version",
    )
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("compiler identifiers must use stable identifier characters")
        return value

    @field_validator("template_version")
    @classmethod
    def validate_template_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("template_version must be a stable version identifier")
        return value

    @field_validator("static_registry_path")
    @classmethod
    def validate_registry_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("static_registry_path must be repository-relative")
        if not value.startswith("data/context/"):
            raise ValueError("static_registry_path must live under data/context/")
        return value

    @field_validator("static_registry_sha256")
    @classmethod
    def validate_registry_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("static_registry_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_compiler_spec(self) -> StaticCompilerSpec:
        if self.raw_content_in_public_trace:
            raise ValueError("raw static content must not be placed in public traces")
        segment_ids = [segment.segment_id for segment in self.segments]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("static segment IDs must be unique")
        if [segment.order for segment in self.segments] != list(range(len(self.segments))):
            raise ValueError("static segment order must be contiguous and start at zero")
        required_segment_kinds = {
            StaticSegmentKind.SYSTEM_POLICY,
            StaticSegmentKind.TASK_PROCEDURE,
            StaticSegmentKind.CITATION_RULES,
            StaticSegmentKind.FEW_SHOT_EXAMPLE,
        }
        if {segment.kind for segment in self.segments} != required_segment_kinds:
            raise ValueError("compiler spec must contain every required static segment kind")
        tool_ids = [tool.tool_id for tool in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("tool IDs must be unique")
        if [tool.order for tool in self.tools] != list(range(len(self.tools))):
            raise ValueError("tool order must be contiguous and start at zero")
        return self


class CanonicalAnchorContent(BaseModel):
    """Canonicalized registered artifact content embedded in the static payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str
    order: int
    kind: StaticAnchorKind
    artifact_sha256: str
    normalized_content: str


class CanonicalStaticPayload(BaseModel):
    """Provider-neutral canonical static payload before UTF-8 serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    serialization_version: str
    template_id: str
    template_version: str
    tool_contract_version: str
    segments: tuple[StaticTextSegment, ...]
    tools: tuple[ToolContractSpec, ...]
    output_schema: OutputSchemaSpec
    context_pack: ContextPackSpec
    anchors: tuple[CanonicalAnchorContent, ...]


class PrefixFingerprintRecord(BaseModel):
    """Safe fingerprint evidence without raw static content or HMAC key material."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fingerprint_id: str = "auragateway-static-prefix-fingerprint-v1"
    algorithm: str = "hmac-sha256"
    key_id: str
    prefix_fingerprint: str
    canonical_sha256: str
    canonical_bytes: int = Field(ge=1)
    serialization_version: str
    template_id: str
    template_version: str
    tool_contract_fingerprint: str
    output_schema_fingerprint: str
    context_pack_fingerprint: str
    static_registry_sha256: str
    raw_content_retained: bool = False

    @field_validator(
        "prefix_fingerprint",
        "canonical_sha256",
        "tool_contract_fingerprint",
        "output_schema_fingerprint",
        "context_pack_fingerprint",
        "static_registry_sha256",
    )
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("fingerprint fields must be lowercase SHA-256")
        return value

    @field_validator("key_id")
    @classmethod
    def validate_key_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("key_id must be a stable non-secret identifier")
        return value

    @model_validator(mode="after")
    def validate_privacy(self) -> PrefixFingerprintRecord:
        if self.raw_content_retained:
            raise ValueError("prefix fingerprint evidence must not retain raw content")
        return self


class PrefixTurnFixture(BaseModel):
    """One controlled turn with a complete append-only volatile log."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_index: int = Field(ge=0)
    volatile_log: VolatileAppendLog


class PrefixTurnFixtureSet(BaseModel):
    """Five controlled turns used for the Gate 3 stability audit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str = "auragateway-prefix-stability-turns-v1"
    turns: tuple[PrefixTurnFixture, ...] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_turns(self) -> PrefixTurnFixtureSet:
        if [turn.turn_index for turn in self.turns] != list(range(5)):
            raise ValueError("prefix stability turns must be exactly zero through four")
        run_ids = {turn.volatile_log.run_id for turn in self.turns}
        if len(run_ids) != 1:
            raise ValueError("all prefix stability turns must share one run_id")
        previous_items = 0
        for turn in self.turns:
            current_items = len(turn.volatile_log.items)
            if current_items <= previous_items:
                raise ValueError("each controlled turn must append volatile context")
            previous_items = current_items
        return self


class PrefixMutationCase(BaseModel):
    """One declared mutation calibration case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    mutation_kind: PrefixMutationKind
    expected_outcome: PrefixMutationOutcome
    expected_reason: PrefixMutationReason | None = None

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("mutation case_id must be a stable identifier")
        return value


class PrefixMutationCaseSet(BaseModel):
    """Frozen set of required prefix negative controls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    case_set_id: str = "auragateway-prefix-mutation-cases-v1"
    cases: tuple[PrefixMutationCase, ...] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def validate_cases(self) -> PrefixMutationCaseSet:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("mutation case IDs must be unique")
        if {case.mutation_kind for case in self.cases} != set(PrefixMutationKind):
            raise ValueError("mutation case set must contain every required mutation kind")
        return self


class PrefixMutationResult(BaseModel):
    """Observed result for one mutation calibration case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    mutation_kind: PrefixMutationKind
    expected_outcome: PrefixMutationOutcome
    observed_outcome: PrefixMutationOutcome
    expected_reason: PrefixMutationReason | None = None
    observed_reason: PrefixMutationReason | None = None
    baseline_fingerprint: str
    mutated_fingerprint: str | None = None
    passed: bool

    @field_validator("baseline_fingerprint", "mutated_fingerprint")
    @classmethod
    def validate_hashes(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("mutation fingerprints must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_result(self) -> PrefixMutationResult:
        if self.observed_outcome is PrefixMutationOutcome.BLOCKED:
            if self.observed_reason is None or self.mutated_fingerprint is not None:
                raise ValueError("blocked mutations require a reason and no mutated fingerprint")
        elif self.mutated_fingerprint is None:
            raise ValueError("non-blocked mutations require a mutated fingerprint")
        if self.passed != (
            self.expected_outcome is self.observed_outcome
            and self.expected_reason is self.observed_reason
        ):
            raise ValueError("passed must match expected and observed mutation outcomes")
        return self


class PrefixTurnAudit(BaseModel):
    """Safe five-turn fingerprint evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_index: int = Field(ge=0, le=4)
    volatile_log_sha256: str
    volatile_item_count: int = Field(ge=1)
    static_prefix_fingerprint: str
    matches_baseline: bool

    @field_validator("volatile_log_sha256", "static_prefix_fingerprint")
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("turn audit hashes must be lowercase SHA-256")
        return value


class PrefixStabilityReport(BaseModel):
    """Hash-bound Gate 3 prefix-stability and mutation-calibration report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str = "auragateway-prefix-stability-report-v1"
    status: str = "passed"
    compiler_spec_path: str
    compiler_spec_sha256: str
    static_registry_path: str
    static_registry_sha256: str
    turn_fixtures_path: str
    turn_fixtures_sha256: str
    mutation_cases_path: str
    mutation_cases_sha256: str
    fingerprint: PrefixFingerprintRecord
    turn_audits: tuple[PrefixTurnAudit, ...] = Field(min_length=5, max_length=5)
    mutation_results: tuple[PrefixMutationResult, ...] = Field(min_length=7, max_length=7)
    stable_turn_count: int = Field(ge=5, le=5)
    negative_control_count: int = Field(ge=7, le=7)
    negative_control_pass_count: int = Field(ge=7, le=7)
    canonical_serialization_implemented: bool = True
    hmac_prefix_fingerprinting_implemented: bool = True
    gate_3_passed: bool = True
    measured_execution_permitted: bool = False
    required_next_gate: str = "telemetry_integrity"

    @field_validator(
        "compiler_spec_sha256",
        "static_registry_sha256",
        "turn_fixtures_sha256",
        "mutation_cases_sha256",
    )
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("report references must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_report(self) -> PrefixStabilityReport:
        if [audit.turn_index for audit in self.turn_audits] != list(range(5)):
            raise ValueError("turn audits must be ordered zero through four")
        if not all(audit.matches_baseline for audit in self.turn_audits):
            raise ValueError("all controlled turns must match the baseline fingerprint")
        if not all(result.passed for result in self.mutation_results):
            raise ValueError("every mutation calibration case must pass")
        if self.negative_control_count != len(self.mutation_results):
            raise ValueError("negative_control_count must match mutation_results")
        if self.negative_control_pass_count != sum(
            result.passed for result in self.mutation_results
        ):
            raise ValueError("negative_control_pass_count must match passing results")
        if not self.canonical_serialization_implemented:
            raise ValueError("Gate 3 requires canonical serialization")
        if not self.hmac_prefix_fingerprinting_implemented:
            raise ValueError("Gate 3 requires HMAC prefix fingerprinting")
        if not self.gate_3_passed or self.measured_execution_permitted:
            raise ValueError("Gate 3 report must pass without permitting measured execution")
        return self


class PrefixDeterminismManifest(BaseModel):
    """Frozen Gate 3 manifest binding all prefix-determinism evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-prefix-determinism-manifest-v1"
    status: str = "frozen"
    context_boundary_manifest_path: str
    context_boundary_manifest_sha256: str
    compiler_spec_path: str
    compiler_spec_sha256: str
    turn_fixtures_path: str
    turn_fixtures_sha256: str
    mutation_cases_path: str
    mutation_cases_sha256: str
    report_path: str
    report_sha256: str
    prefix_fingerprint: str
    serialization_version: str
    hmac_key_id: str
    stable_turn_count: int = 5
    negative_control_count: int = 7
    gate_3_passed: bool = True
    measured_execution_permitted: bool = False
    required_next_gate: str = "telemetry_integrity"

    @field_validator(
        "context_boundary_manifest_sha256",
        "compiler_spec_sha256",
        "turn_fixtures_sha256",
        "mutation_cases_sha256",
        "report_sha256",
        "prefix_fingerprint",
    )
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest references must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> PrefixDeterminismManifest:
        if not self.gate_3_passed:
            raise ValueError("prefix determinism manifest must record a passed Gate 3")
        if self.measured_execution_permitted:
            raise ValueError("Gate 3 must not permit measured execution")
        return self


class PrefixDeterminismSummary(BaseModel):
    """Safe CLI output for Gate 3 verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str
    serialization_version: str
    static_anchor_count: int
    stable_turn_count: int
    negative_control_count: int
    negative_control_pass_count: int
    prefix_fingerprint: str
    gate_3_passed: bool
    measured_execution_permitted: bool
    validation_status: str
