"""Typed provider telemetry, normalization evidence, and Gate 4 contracts."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.provider import ProviderInvocationRequest, ProviderName

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class TelemetrySemanticFamily(StrEnum):
    """Provider-specific accounting family retained during normalization."""

    CACHED_INPUT_DETAIL = "cached_input_detail"
    CACHE_CREATION_READ = "cache_creation_read"
    LOCAL_PROMPT_EVALUATION = "local_prompt_evaluation"
    UNAVAILABLE = "unavailable"


class CacheEvidenceLevel(StrEnum):
    """Strength and provenance of cache-related evidence."""

    OBSERVED_PROVIDER = "observed_provider"
    INFERRED_LOCAL = "inferred_local"
    UNAVAILABLE = "unavailable"


class TokenDenominatorKind(StrEnum):
    """Meaning of the input-token denominator retained in normalized evidence."""

    PROVIDER_INPUT_TOTAL = "provider_input_total"
    PROVIDER_COMPONENT_SUM = "provider_component_sum"
    LOCAL_PROMPT_EVAL_COUNT = "local_prompt_eval_count"
    UNAVAILABLE = "unavailable"


class ClaimKind(StrEnum):
    """Claims independently authorized or blocked by the sufficiency gate."""

    CACHE_EFFICIENCY = "cache_efficiency"
    LATENCY = "latency"
    ESTIMATED_COST = "estimated_cost"


class ClaimDecision(StrEnum):
    """Machine-readable claim authorization."""

    PERMITTED = "permitted"
    BLOCKED = "blocked"


class TelemetryReasonCode(StrEnum):
    """Safe reasons explaining a telemetry sufficiency decision."""

    CLAIM_PERMITTED = "CLAIM_PERMITTED"
    CACHE_EVIDENCE_UNAVAILABLE = "CACHE_EVIDENCE_UNAVAILABLE"
    CACHE_SEMANTICS_MISMATCH = "CACHE_SEMANTICS_MISMATCH"
    LATENCY_EVIDENCE_UNAVAILABLE = "LATENCY_EVIDENCE_UNAVAILABLE"
    LATENCY_SEMANTICS_MISMATCH = "LATENCY_SEMANTICS_MISMATCH"
    TOKEN_EVIDENCE_UNAVAILABLE = "TOKEN_EVIDENCE_UNAVAILABLE"
    PRICING_EVIDENCE_UNAVAILABLE = "PRICING_EVIDENCE_UNAVAILABLE"
    PRICING_SEMANTICS_MISMATCH = "PRICING_SEMANTICS_MISMATCH"


class PricingEvidenceKind(StrEnum):
    """Source class for a versioned pricing schedule."""

    SYNTHETIC_FIXTURE = "synthetic_fixture"
    LIVE_PROVIDER_DOCUMENTATION = "live_provider_documentation"


class CachedInputDetailTelemetry(BaseModel):
    """Provider usage with a total-input count and a cached-input detail count."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_family: Literal[TelemetrySemanticFamily.CACHED_INPUT_DETAIL] = (
        TelemetrySemanticFamily.CACHED_INPUT_DETAIL
    )
    fixture_id: str
    provider: ProviderName
    model_alias: str
    input_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    time_to_first_output_ms: int | None = Field(default=None, ge=0)
    total_duration_ms: int | None = Field(default=None, ge=0)


class CacheCreationReadTelemetry(BaseModel):
    """Provider usage that separates uncached, cache-creation, and cache-read input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_family: Literal[TelemetrySemanticFamily.CACHE_CREATION_READ] = (
        TelemetrySemanticFamily.CACHE_CREATION_READ
    )
    fixture_id: str
    provider: ProviderName
    model_alias: str
    uncached_input_tokens: int | None = Field(default=None, ge=0)
    cache_creation_input_tokens: int | None = Field(default=None, ge=0)
    cache_read_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    time_to_first_output_ms: int | None = Field(default=None, ge=0)
    total_duration_ms: int | None = Field(default=None, ge=0)


class LocalPromptEvaluationTelemetry(BaseModel):
    """Local runtime timing that must not be represented as provider cached tokens."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_family: Literal[TelemetrySemanticFamily.LOCAL_PROMPT_EVALUATION] = (
        TelemetrySemanticFamily.LOCAL_PROMPT_EVALUATION
    )
    fixture_id: str
    provider: ProviderName = ProviderName.OLLAMA
    model_alias: str
    prompt_eval_count: int | None = Field(default=None, ge=0)
    prompt_eval_duration_ms: int | None = Field(default=None, ge=0)
    output_eval_count: int | None = Field(default=None, ge=0)
    total_duration_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_local_provider(self) -> LocalPromptEvaluationTelemetry:
        if self.provider is not ProviderName.OLLAMA:
            raise ValueError("local prompt-evaluation telemetry must use the ollama provider")
        return self


class UnavailableTelemetry(BaseModel):
    """Explicit absence of trustworthy telemetry; unknown must never become zero."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_family: Literal[TelemetrySemanticFamily.UNAVAILABLE] = (
        TelemetrySemanticFamily.UNAVAILABLE
    )
    fixture_id: str
    provider: ProviderName = ProviderName.UNAVAILABLE
    model_alias: str
    unavailable_reason: str = Field(min_length=1, max_length=300)


ProviderTelemetryPayload = Annotated[
    CachedInputDetailTelemetry
    | CacheCreationReadTelemetry
    | LocalPromptEvaluationTelemetry
    | UnavailableTelemetry,
    Field(discriminator="semantic_family"),
]


class NormalizedTelemetry(BaseModel):
    """Provider-neutral envelope that preserves every provider-specific meaning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_id: str
    provider: ProviderName
    model_alias: str
    semantic_family: TelemetrySemanticFamily
    evidence_level: CacheEvidenceLevel
    denominator_kind: TokenDenominatorKind
    accounting_input_tokens: int | None = Field(default=None, ge=0)
    provider_input_tokens: int | None = Field(default=None, ge=0)
    provider_output_tokens: int | None = Field(default=None, ge=0)
    provider_cached_input_tokens: int | None = Field(default=None, ge=0)
    provider_uncached_input_tokens: int | None = Field(default=None, ge=0)
    provider_cache_creation_input_tokens: int | None = Field(default=None, ge=0)
    provider_cache_read_input_tokens: int | None = Field(default=None, ge=0)
    local_prompt_eval_count: int | None = Field(default=None, ge=0)
    local_prompt_eval_duration_ms: int | None = Field(default=None, ge=0)
    time_to_first_output_ms: int | None = Field(default=None, ge=0)
    total_duration_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_semantic_separation(self) -> NormalizedTelemetry:
        provider_cache_values = (
            self.provider_cached_input_tokens,
            self.provider_cache_creation_input_tokens,
            self.provider_cache_read_input_tokens,
        )
        local_values = (
            self.local_prompt_eval_count,
            self.local_prompt_eval_duration_ms,
        )
        if self.evidence_level is CacheEvidenceLevel.INFERRED_LOCAL:
            if any(value is not None for value in provider_cache_values):
                raise ValueError("local evidence must not contain provider cache-token fields")
            if self.semantic_family is not TelemetrySemanticFamily.LOCAL_PROMPT_EVALUATION:
                raise ValueError(
                    "inferred local evidence requires local prompt-evaluation semantics"
                )
        if self.evidence_level is CacheEvidenceLevel.OBSERVED_PROVIDER and any(
            value is not None for value in local_values
        ):
            raise ValueError("provider evidence must not contain local timing fields")
        if self.evidence_level is CacheEvidenceLevel.UNAVAILABLE:
            measurable = (
                self.accounting_input_tokens,
                self.provider_input_tokens,
                self.provider_output_tokens,
                *provider_cache_values,
                *local_values,
                self.time_to_first_output_ms,
                self.total_duration_ms,
            )
            if any(value is not None for value in measurable):
                raise ValueError("unavailable evidence must keep every metric unknown")
        return self


class PricingSchedule(BaseModel):
    """Versioned pricing inputs used only for explicitly estimated cost."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schedule_id: str
    provider: ProviderName
    model_alias: str
    source_date: date
    evidence_kind: PricingEvidenceKind
    currency: Literal["USD"] = "USD"
    standard_input_per_million: Decimal | None = Field(default=None, ge=0)
    cached_input_per_million: Decimal | None = Field(default=None, ge=0)
    cache_creation_input_per_million: Decimal | None = Field(default=None, ge=0)
    cache_read_input_per_million: Decimal | None = Field(default=None, ge=0)
    output_per_million: Decimal | None = Field(default=None, ge=0)


class ClaimSufficiencyDecision(BaseModel):
    """One explicit claim decision with bounded evidence diagnostics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: ClaimKind
    decision: ClaimDecision
    reason_code: TelemetryReasonCode
    evidence_level: CacheEvidenceLevel
    required_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_decision(self) -> ClaimSufficiencyDecision:
        if self.decision is ClaimDecision.PERMITTED:
            if self.reason_code is not TelemetryReasonCode.CLAIM_PERMITTED:
                raise ValueError("permitted claims require CLAIM_PERMITTED")
            if self.missing_fields or self.invalid_fields:
                raise ValueError("permitted claims must not contain evidence defects")
        elif self.reason_code is TelemetryReasonCode.CLAIM_PERMITTED:
            raise ValueError("blocked claims require a blocking reason")
        return self


class TelemetrySufficiencyReport(BaseModel):
    """Independent cache, latency, and estimated-cost decisions for one call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_id: str
    decisions: tuple[ClaimSufficiencyDecision, ...] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_complete_decision_set(self) -> TelemetrySufficiencyReport:
        kinds = [decision.claim_kind for decision in self.decisions]
        if set(kinds) != set(ClaimKind) or len(kinds) != len(set(kinds)):
            raise ValueError("sufficiency report must contain one decision per claim kind")
        return self

    def decision_for(self, claim_kind: ClaimKind) -> ClaimSufficiencyDecision:
        """Return the required claim decision without exposing raw telemetry."""

        return next(item for item in self.decisions if item.claim_kind is claim_kind)


class FixtureClaimExpectation(BaseModel):
    """Expected result for one deterministic sufficiency decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: ClaimKind
    decision: ClaimDecision
    reason_code: TelemetryReasonCode


class TelemetryFixtureCase(BaseModel):
    """One deterministic provider request, telemetry payload, and expected decisions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    request: ProviderInvocationRequest
    telemetry: ProviderTelemetryPayload
    pricing_schedule_id: str | None = None
    expectations: tuple[FixtureClaimExpectation, ...] = Field(min_length=3, max_length=3)
    negative_control: bool = False

    @model_validator(mode="after")
    def validate_case_identity(self) -> TelemetryFixtureCase:
        if self.case_id != self.request.fixture_id or self.case_id != self.telemetry.fixture_id:
            raise ValueError("case, request, and telemetry fixture IDs must match")
        if self.request.provider is not self.telemetry.provider:
            raise ValueError("request and telemetry providers must match")
        if self.request.model_alias != self.telemetry.model_alias:
            raise ValueError("request and telemetry model aliases must match")
        kinds = [expectation.claim_kind for expectation in self.expectations]
        if set(kinds) != set(ClaimKind) or len(kinds) != len(set(kinds)):
            raise ValueError("fixture expectations must cover each claim exactly once")
        return self


class TelemetryFixtureSet(BaseModel):
    """Frozen deterministic Gate 4 telemetry fixtures and synthetic pricing schedules."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    cases: tuple[TelemetryFixtureCase, ...] = Field(min_length=1)
    pricing_schedules: tuple[PricingSchedule, ...] = ()

    @model_validator(mode="after")
    def validate_unique_assets(self) -> TelemetryFixtureSet:
        case_ids = [case.case_id for case in self.cases]
        duplicates = sorted(value for value, count in Counter(case_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate telemetry fixture IDs: {', '.join(duplicates)}")
        schedule_ids = [schedule.schedule_id for schedule in self.pricing_schedules]
        duplicates = sorted(value for value, count in Counter(schedule_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate pricing schedule IDs: {', '.join(duplicates)}")
        known_schedules = set(schedule_ids)
        unknown = sorted(
            case.pricing_schedule_id
            for case in self.cases
            if case.pricing_schedule_id is not None
            and case.pricing_schedule_id not in known_schedules
        )
        if unknown:
            raise ValueError(f"unknown pricing schedule IDs: {', '.join(unknown)}")
        return self


class Gate4FixtureResult(BaseModel):
    """Sanitized result for one deterministic telemetry fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    semantic_family: TelemetrySemanticFamily
    evidence_level: CacheEvidenceLevel
    invocation_output_sha256: str
    normalized_telemetry: NormalizedTelemetry
    sufficiency: TelemetrySufficiencyReport
    expectations_matched: bool
    negative_control: bool

    @field_validator("invocation_output_sha256")
    @classmethod
    def validate_output_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("invocation_output_sha256 must be lowercase SHA-256")
        return value


class Gate4TelemetryReport(BaseModel):
    """Deterministic Gate 4 report derived from typed fixtures."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str = "auragateway-gate-4-telemetry-report-v1"
    status: Literal["passed", "failed"]
    fixture_set_id: str
    results: tuple[Gate4FixtureResult, ...] = Field(min_length=1)
    fixture_count: int = Field(gt=0)
    negative_control_count: int = Field(ge=0)
    all_expectations_matched: bool
    provider_semantics_preserved: bool
    unknown_values_remained_none: bool
    local_timing_separated_from_provider_cache: bool
    raw_provider_payloads_persisted: bool = False
    gate_4_passed: bool
    measured_execution_permitted: bool = False
    required_next_work: str = "primary_live_provider_adapter"

    @model_validator(mode="after")
    def validate_gate_state(self) -> Gate4TelemetryReport:
        if self.fixture_count != len(self.results):
            raise ValueError("fixture_count must equal the number of fixture results")
        if self.negative_control_count != sum(result.negative_control for result in self.results):
            raise ValueError("negative_control_count does not match fixture results")
        expected_pass = (
            self.all_expectations_matched
            and self.provider_semantics_preserved
            and self.unknown_values_remained_none
            and self.local_timing_separated_from_provider_cache
            and not self.raw_provider_payloads_persisted
        )
        if self.gate_4_passed != expected_pass:
            raise ValueError("gate_4_passed does not match required telemetry controls")
        if (self.status == "passed") != self.gate_4_passed:
            raise ValueError("report status must match Gate 4 decision")
        if self.measured_execution_permitted:
            raise ValueError("Gate 4 must not permit measured benchmark execution")
        return self


class Gate4TelemetryManifest(BaseModel):
    """Frozen identity for Gate 4 fixture and report evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-4-telemetry-manifest-v1"
    status: Literal["frozen"] = "frozen"
    fixture_path: str
    fixture_sha256: str
    report_path: str
    report_sha256: str
    fixture_count: int = Field(gt=0)
    negative_control_count: int = Field(ge=0)
    gate_4_passed: bool
    measured_execution_permitted: bool = False
    required_next_work: str = "primary_live_provider_adapter"

    @field_validator("fixture_path", "report_path")
    @classmethod
    def validate_repo_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Gate 4 artifact paths must be repository-relative")
        if not value.startswith("data/provider_fixtures/telemetry/"):
            raise ValueError("Gate 4 artifacts must live under telemetry fixtures")
        return value

    @field_validator("fixture_sha256", "report_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("Gate 4 artifact hashes must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_execution_state(self) -> Gate4TelemetryManifest:
        if not self.gate_4_passed or self.measured_execution_permitted:
            raise ValueError("frozen Gate 4 evidence must pass without permitting execution")
        return self


class Gate4TelemetrySummary(BaseModel):
    """Safe CLI summary for Gate 4 build and verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_count: int
    negative_control_count: int
    gate_4_passed: bool
    measured_execution_permitted: bool
    fixture_sha256: str
    report_sha256: str
