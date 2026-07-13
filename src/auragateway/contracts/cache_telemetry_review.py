"""Typed contracts for cache telemetry sufficiency review."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class CacheTelemetryReviewStatus(StrEnum):
    """Lifecycle state for the cache telemetry evidence review."""

    BLOCKED_PROVIDER_OBSERVATION_GAP = "blocked_provider_observation_gap"


class CacheTelemetryEvidenceKind(StrEnum):
    """Source class for one frozen review assertion."""

    LIVE_EXECUTION = "live_execution"
    OFFICIAL_PROVIDER_DOCUMENTATION = "official_provider_documentation"
    OFFICIAL_PROVIDER_SDK_SCHEMA = "official_provider_sdk_schema"
    REPOSITORY_SOURCE = "repository_source"


class CacheTelemetrySignalKind(StrEnum):
    """Cache-related signal with explicit semantics."""

    BILLING_PROMPT_CACHE_TOKENS = "billing_prompt_cache_tokens"
    HARDWARE_DRAM_CACHE_TOKENS = "hardware_dram_cache_tokens"
    HARDWARE_SRAM_CACHE_TOKENS = "hardware_sram_cache_tokens"


class CacheTelemetryClaimKind(StrEnum):
    """Claims controlled by this review."""

    PROVIDER_CACHE_USAGE = "provider_cache_usage"
    PROVIDER_CACHE_SAVINGS = "provider_cache_savings"
    LATENCY_IMPROVEMENT = "latency_improvement"
    ACCEPTED_A_B_C_COMPARISON = "accepted_a_b_c_comparison"


class CacheTelemetryClaimDecision(StrEnum):
    """Machine-readable decision for one claim."""

    BLOCKED = "blocked"


class CacheTelemetryReasonCode(StrEnum):
    """Bounded reason taxonomy for blocked claims."""

    BILLING_CACHE_FIELD_UNOBSERVED = "BILLING_CACHE_FIELD_UNOBSERVED"
    HARDWARE_SIGNAL_NOT_BILLING_EQUIVALENT = "HARDWARE_SIGNAL_NOT_BILLING_EQUIVALENT"
    DIAGNOSTIC_NOT_POWERED_FOR_LATENCY = "DIAGNOSTIC_NOT_POWERED_FOR_LATENCY"
    COMPARISON_NOT_AUTHORIZED = "COMPARISON_NOT_AUTHORIZED"


class CacheTelemetryNextGate(StrEnum):
    """Next engineering gate after the review."""

    GROQ_CACHE_TELEMETRY_CAPTURE_HARDENING = "groq_cache_telemetry_capture_hardening"


class CacheTelemetrySourceBinding(BaseModel):
    """One immutable local source bound by Git blob identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    git_blob_sha1: str

    @field_validator("git_blob_sha1")
    @classmethod
    def validate_sha1(cls, value: str) -> str:
        if _SHA1_PATTERN.fullmatch(value) is None:
            raise ValueError("source bindings require lowercase Git blob SHA-1")
        return value


class CacheTelemetryExternalSource(BaseModel):
    """One external source represented by narrow review assertions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    kind: CacheTelemetryEvidenceKind
    url: str = Field(min_length=8, max_length=500)
    retrieved_on: Literal["2026-07-13"] = "2026-07-13"
    assertions: tuple[str, ...] = Field(min_length=1, max_length=8)

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("external source IDs require stable lowercase slugs")
        return value


class CacheTelemetrySignalAssessment(BaseModel):
    """One cache signal and whether it can support billing-cache claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    signal_kind: CacheTelemetrySignalKind
    current_adapter_parses_signal: bool
    observed_sample_count: int = Field(ge=0, le=24)
    semantically_equivalent_to_billing_cache_tokens: bool
    claim_use_permitted: Literal[False] = False
    reason: str = Field(min_length=3, max_length=300)


class CacheTelemetryClaimAssessment(BaseModel):
    """One blocked claim with a bounded reason."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: CacheTelemetryClaimKind
    decision: Literal[CacheTelemetryClaimDecision.BLOCKED] = CacheTelemetryClaimDecision.BLOCKED
    reason_code: CacheTelemetryReasonCode


class CacheTelemetryRequiredAction(BaseModel):
    """One mandatory action before a provider calibration can be reviewed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str
    description: str = Field(min_length=8, max_length=400)
    provider_call_required: Literal[False] = False
    acceptance_evidence: tuple[str, ...] = Field(min_length=1, max_length=6)

    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("action IDs require stable lowercase slugs")
        return value


class CacheTelemetrySufficiencyReview(BaseModel):
    """Frozen review of whether current evidence supports cache claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["cache-telemetry-sufficiency-review-v1"]
    status: CacheTelemetryReviewStatus
    source_closeout_id: Literal["batch-06-diagnostic-closeout-v1"]
    source_commit: Literal["247d611657bed874bcefdc58dbc7db1f3a014f7b"]
    source_bindings: tuple[CacheTelemetrySourceBinding, ...] = Field(
        min_length=5,
        max_length=5,
    )
    external_sources: tuple[CacheTelemetryExternalSource, ...] = Field(
        min_length=2,
        max_length=2,
    )
    observed_provider_call_count: Literal[24] = 24
    observed_successful_call_count: Literal[24] = 24
    observed_input_token_sample_count: Literal[24] = 24
    observed_duration_sample_count: Literal[24] = 24
    observed_cached_input_token_sample_count: Literal[0] = 0
    observed_total_cached_input_tokens: None = None
    unknown_interpreted_as_zero: Literal[False] = False
    exact_installed_groq_sdk_version_observed: Literal[False] = False
    raw_success_response_retained: Literal[False] = False
    billing_cache_field_path: Literal["usage.prompt_tokens_details.cached_tokens"] = (
        "usage.prompt_tokens_details.cached_tokens"
    )
    hardware_cache_field_paths: tuple[
        Literal["x_groq.usage.dram_cached_tokens"],
        Literal["x_groq.usage.sram_cached_tokens"],
    ]
    signals: tuple[CacheTelemetrySignalAssessment, ...] = Field(
        min_length=3,
        max_length=3,
    )
    claims: tuple[CacheTelemetryClaimAssessment, ...] = Field(
        min_length=4,
        max_length=4,
    )
    required_actions: tuple[CacheTelemetryRequiredAction, ...] = Field(
        min_length=6,
        max_length=6,
    )
    current_provider_cache_claim_sufficient: Literal[False] = False
    provider_call_authorized: Literal[False] = False
    calibration_authorized: Literal[False] = False
    full_benchmark_authorized: Literal[False] = False
    next_gate: Literal[CacheTelemetryNextGate.GROQ_CACHE_TELEMETRY_CAPTURE_HARDENING] = (
        CacheTelemetryNextGate.GROQ_CACHE_TELEMETRY_CAPTURE_HARDENING
    )

    @model_validator(mode="after")
    def validate_review_completeness(self) -> CacheTelemetrySufficiencyReview:
        expected_binding_paths = {
            "data/evals/benchmark/diagnostic-closeout-v1/closeout.json",
            "data/evals/benchmark/diagnostic-closeout-v1/manifest.json",
            "src/auragateway/providers/groq.py",
            "src/auragateway/contracts/telemetry.py",
            "pyproject.toml",
        }
        observed_binding_paths = [item.path for item in self.source_bindings]
        if set(observed_binding_paths) != expected_binding_paths:
            raise ValueError("review requires the five frozen local sources")
        if len(observed_binding_paths) != len(set(observed_binding_paths)):
            raise ValueError("review source bindings must be unique")

        expected_signals = set(CacheTelemetrySignalKind)
        observed_signals = [item.signal_kind for item in self.signals]
        if set(observed_signals) != expected_signals:
            raise ValueError("review requires all three cache signal assessments")
        if len(observed_signals) != len(set(observed_signals)):
            raise ValueError("cache signal assessments must be unique")

        expected_claims = set(CacheTelemetryClaimKind)
        observed_claims = [item.claim_kind for item in self.claims]
        if set(observed_claims) != expected_claims:
            raise ValueError("review requires all four claim assessments")
        if len(observed_claims) != len(set(observed_claims)):
            raise ValueError("claim assessments must be unique")

        action_ids = [item.action_id for item in self.required_actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("required action IDs must be unique")

        billing_signal = next(
            item
            for item in self.signals
            if item.signal_kind is CacheTelemetrySignalKind.BILLING_PROMPT_CACHE_TOKENS
        )
        if not billing_signal.current_adapter_parses_signal:
            raise ValueError("current adapter must parse the documented billing field")
        if billing_signal.observed_sample_count != 0:
            raise ValueError("Batch 06 diagnostic observed no billing cache samples")

        hardware_signals = tuple(
            item
            for item in self.signals
            if item.signal_kind is not CacheTelemetrySignalKind.BILLING_PROMPT_CACHE_TOKENS
        )
        if any(item.semantically_equivalent_to_billing_cache_tokens for item in hardware_signals):
            raise ValueError("hardware cache signals cannot be promoted to billing semantics")
        return self


class CacheTelemetryReviewManifest(BaseModel):
    """Integrity manifest for the cache telemetry sufficiency review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["cache-telemetry-sufficiency-review-v1"]
    review_path: Literal["data/evals/benchmark/cache-telemetry-review-v1/review.json"]
    review_sha256: str
    report_path: Literal["docs/benchmark/AuraGateway_Cache_Telemetry_Sufficiency_Review.md"]
    report_sha256: str
    provider_call_authorized: Literal[False] = False
    next_gate: Literal[CacheTelemetryNextGate.GROQ_CACHE_TELEMETRY_CAPTURE_HARDENING] = (
        CacheTelemetryNextGate.GROQ_CACHE_TELEMETRY_CAPTURE_HARDENING
    )

    @field_validator("review_sha256", "report_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("review manifest requires lowercase SHA-256")
        return value


class CacheTelemetryReviewSummary(BaseModel):
    """Metadata-safe validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    review_id: str
    status: CacheTelemetryReviewStatus
    provider_call_count: Literal[24] = 24
    successful_call_count: Literal[24] = 24
    cached_input_token_sample_count: Literal[0] = 0
    cache_claim_sufficient: Literal[False] = False
    provider_call_authorized: Literal[False] = False
    calibration_authorized: Literal[False] = False
    full_benchmark_authorized: Literal[False] = False
    credential_accessed: Literal[False] = False
    next_gate: CacheTelemetryNextGate
