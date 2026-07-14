"""Typed terminal closeout for Groq raw-wire cache telemetry reauthorization."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ReauthorizationCloseoutStatus(StrEnum):
    """Terminal lifecycle state after the raw-wire evidence review."""

    CLOSED_PROVIDER_WIRE_FIELD_UNAVAILABLE = "closed_provider_wire_field_unavailable"


class ReauthorizationCloseoutClaimKind(StrEnum):
    """Claims independently permitted or blocked by terminal evidence."""

    EXECUTION_COMPLETED = "execution_completed"
    EXACT_PROVIDER_WIRE_OMISSION_FOR_OBSERVED_CALLS = (
        "exact_provider_wire_omission_for_observed_calls"
    )
    UNIVERSAL_PROVIDER_WIRE_OMISSION = "universal_provider_wire_omission"
    SDK_LIVE_PARSE_DEFECT = "sdk_live_parse_defect"
    PROVIDER_CACHE_USAGE = "provider_cache_usage"
    PROVIDER_CACHE_MISS = "provider_cache_miss"
    CACHED_TOKENS_EQUAL_ZERO = "cached_tokens_equal_zero"
    PROVIDER_CACHE_SAVINGS = "provider_cache_savings"
    BENCHMARK_EXECUTION = "benchmark_execution"
    ACCEPTED_A_B_C_COMPARISON = "accepted_a_b_c_comparison"


class ReauthorizationCloseoutClaimDecision(StrEnum):
    """Machine-readable closeout claim decision."""

    PERMITTED = "permitted"
    BLOCKED = "blocked"


class ReauthorizationCloseoutClaimReason(StrEnum):
    """Bounded evidence reasons for each claim decision."""

    TWO_SUCCESSFUL_CALLS_VERIFIED = "TWO_SUCCESSFUL_CALLS_VERIFIED"
    FIELD_ABSENT_ON_BOTH_RAW_RESPONSES = "FIELD_ABSENT_ON_BOTH_RAW_RESPONSES"
    OBSERVATION_SCOPE_LIMITED_TO_TWO_CALLS = "OBSERVATION_SCOPE_LIMITED_TO_TWO_CALLS"
    FIELD_ABSENT_BEFORE_SDK_PARSE = "FIELD_ABSENT_BEFORE_SDK_PARSE"
    BILLING_CACHE_EVIDENCE_UNAVAILABLE = "BILLING_CACHE_EVIDENCE_UNAVAILABLE"
    FIELD_ABSENCE_IS_NOT_CACHE_MISS = "FIELD_ABSENCE_IS_NOT_CACHE_MISS"
    MISSING_FIELD_IS_NOT_ZERO = "MISSING_FIELD_IS_NOT_ZERO"
    NUMERIC_CACHE_EVIDENCE_UNAVAILABLE = "NUMERIC_CACHE_EVIDENCE_UNAVAILABLE"
    GATE_4_REQUIRED_EVIDENCE_UNAVAILABLE = "GATE_4_REQUIRED_EVIDENCE_UNAVAILABLE"
    COMPARISON_NOT_ELIGIBLE = "COMPARISON_NOT_ELIGIBLE"


class ReauthorizationCloseoutNextGate(StrEnum):
    """Next non-live project gate selected from terminal evidence."""

    AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW = "auragateway_v2_terminal_evidence_review"


class ReauthorizationCloseoutBinding(BaseModel):
    """One immutable public execution dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=260)
    sha256: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("closeout bindings must be repository-relative")
        if not value.startswith("data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/"):
            raise ValueError("closeout bindings must use the frozen execution root")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("closeout bindings require lowercase SHA-256")
        return value


class ReauthorizationCloseoutClaimRecord(BaseModel):
    """One explicit closeout claim boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: ReauthorizationCloseoutClaimKind
    decision: ReauthorizationCloseoutClaimDecision
    reason: ReauthorizationCloseoutClaimReason

    @model_validator(mode="after")
    def validate_decision(self) -> ReauthorizationCloseoutClaimRecord:
        permitted_reasons = {
            ReauthorizationCloseoutClaimReason.TWO_SUCCESSFUL_CALLS_VERIFIED,
            ReauthorizationCloseoutClaimReason.FIELD_ABSENT_ON_BOTH_RAW_RESPONSES,
        }
        if (
            self.decision is ReauthorizationCloseoutClaimDecision.PERMITTED
            and self.reason not in permitted_reasons
        ):
            raise ValueError("permitted claims require permitted evidence")
        if (
            self.decision is ReauthorizationCloseoutClaimDecision.BLOCKED
            and self.reason in permitted_reasons
        ):
            raise ValueError("blocked claims require blocking evidence")
        return self


class ReauthorizationCloseoutExecutionOutcome(BaseModel):
    """Reconciled terminal execution counts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planned_attempt_count: Literal[2] = 2
    provider_call_count: Literal[2] = 2
    successful_call_count: Literal[2] = 2
    provider_error_count: Literal[0] = 0
    observation_invalid_count: Literal[0] = 0
    skipped_attempt_count: Literal[0] = 0
    estimated_cost_microusd: Literal[400] = 400
    cost_semantics: Literal["planned_bounded_estimate_not_provider_invoice"] = (
        "planned_bounded_estimate_not_provider_invoice"
    )


class ReauthorizationCloseoutTelemetryAssessment(BaseModel):
    """Raw-wire and parsed-object cache telemetry coverage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    installed_sdk_version: Literal["1.5.0"] = "1.5.0"
    installed_sdk_version_sample_count: Literal[2] = 2
    raw_response_sample_count: Literal[2] = 2
    parsed_response_sample_count: Literal[2] = 2
    raw_billing_field_absent_count: Literal[2] = 2
    parsed_billing_field_absent_count: Literal[2] = 2
    raw_billing_numeric_sample_count: Literal[0] = 0
    parsed_billing_numeric_sample_count: Literal[0] = 0
    exact_provider_request_sha256: Literal[
        "23cac23a165812ae8e9908e9d0609fb533359a30ed4386d76bcfb82e6a9d17c9"
    ]
    provider_wire_omission_established_for_observed_calls: Literal[True] = True
    universal_provider_wire_omission_established: Literal[False] = False
    sdk_live_parse_defect_established: Literal[False] = False
    provider_cache_usage_evidence_available: Literal[False] = False
    unknown_interpreted_as_zero: Literal[False] = False


class ReauthorizationCloseoutProtectedEvidence(BaseModel):
    """Hash-only lineage for protected response evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_responses_path: Literal[
        ".local/benchmark/groq-cache-telemetry-reauthorization-v1/raw_responses.jsonl"
    ]
    raw_responses_sha256: str
    parsed_responses_path: Literal[
        ".local/benchmark/groq-cache-telemetry-reauthorization-v1/parsed_responses.jsonl"
    ]
    parsed_responses_sha256: str
    protected_content_committed: Literal[False] = False
    protected_content_read_by_closeout: Literal[False] = False
    hash_lineage_preserved: Literal[True] = True

    @field_validator("raw_responses_sha256", "parsed_responses_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("protected evidence requires lowercase SHA-256")
        return value


class ReauthorizationCloseoutImplementationResolution(BaseModel):
    """Engineering action selected from terminal raw-wire evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    retain_current_adapter: Literal[True] = True
    sdk_upgrade_selected: Literal[False] = False
    request_construction_change_selected: Literal[False] = False
    routing_change_selected: Literal[False] = False
    cache_affinity_change_selected: Literal[False] = False
    identical_provider_rerun_permitted: Literal[False] = False
    additional_provider_execution_permitted: Literal[False] = False
    evidence_path_terminal: Literal[True] = True
    reason: Literal["billing_cache_field_absent_on_both_raw_responses"] = (
        "billing_cache_field_absent_on_both_raw_responses"
    )


class ReauthorizationCloseoutGate4Resolution(BaseModel):
    """Final Gate 4 posture for the current provider evidence path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["closed_required_provider_cache_evidence_unavailable"]
    gate_4_passed: Literal[False] = False
    required_provider_cache_evidence_available: Literal[False] = False
    negative_result_accepted: Literal[True] = True
    benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal[ReauthorizationCloseoutNextGate.AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW] = (
        ReauthorizationCloseoutNextGate.AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW
    )


class GroqCacheTelemetryReauthorizationCloseout(BaseModel):
    """Immutable terminal result of the Groq raw-wire reauthorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    closeout_id: Literal["groq-cache-telemetry-reauthorization-closeout-v1"]
    status: Literal[ReauthorizationCloseoutStatus.CLOSED_PROVIDER_WIRE_FIELD_UNAVAILABLE] = (
        ReauthorizationCloseoutStatus.CLOSED_PROVIDER_WIRE_FIELD_UNAVAILABLE
    )
    source_commit: str
    authorization_id: Literal["groq-cache-telemetry-reauthorization-auth-v1"]
    execution_id: Literal["groq-cache-telemetry-reauthorization-v1"]
    execution_bindings: tuple[ReauthorizationCloseoutBinding, ...] = Field(
        min_length=8,
        max_length=8,
    )
    execution_outcome: ReauthorizationCloseoutExecutionOutcome
    telemetry_assessment: ReauthorizationCloseoutTelemetryAssessment
    protected_evidence: ReauthorizationCloseoutProtectedEvidence
    claims: tuple[ReauthorizationCloseoutClaimRecord, ...] = Field(
        min_length=10,
        max_length=10,
    )
    implementation_resolution: ReauthorizationCloseoutImplementationResolution
    gate_4_resolution: ReauthorizationCloseoutGate4Resolution
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    execution_evidence_mutation_permitted: Literal[False] = False
    provider_calls_permitted: Literal[False] = False
    credential_access_required: Literal[False] = False
    provider_cache_usage_claim_permitted: Literal[False] = False
    provider_cache_savings_claim_permitted: Literal[False] = False
    benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal[ReauthorizationCloseoutNextGate.AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW] = (
        ReauthorizationCloseoutNextGate.AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW
    )

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("source_commit must be a lowercase 40-character SHA")
        return value

    @model_validator(mode="after")
    def validate_closeout(self) -> GroqCacheTelemetryReauthorizationCloseout:
        expected_paths = {
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/authorization.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/runtime_policy.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/activation_report.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/activation_manifest.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/journal.jsonl",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/run_records.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/report.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/manifest.json",
        }
        observed_paths = [item.path for item in self.execution_bindings]
        if set(observed_paths) != expected_paths or len(observed_paths) != len(set(observed_paths)):
            raise ValueError("closeout requires all eight execution assets")

        observed_claims = [item.claim_kind for item in self.claims]
        if set(observed_claims) != set(ReauthorizationCloseoutClaimKind) or len(
            observed_claims
        ) != len(set(observed_claims)):
            raise ValueError("closeout requires all ten claim decisions")

        if (
            self.gate_4_resolution.next_gate is not self.next_gate
            or self.implementation_resolution.additional_provider_execution_permitted
        ):
            raise ValueError("closeout gate and execution posture must remain terminal")
        return self


class GroqCacheTelemetryReauthorizationCloseoutManifest(BaseModel):
    """Integrity manifest for closeout JSON and report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    closeout_id: Literal["groq-cache-telemetry-reauthorization-closeout-v1"]
    source_commit: str
    closeout_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-closeout-v1/closeout.json"
    ]
    closeout_sha256: str
    report_path: Literal[
        "docs/benchmark/AuraGateway_Groq_Cache_Telemetry_Reauthorization_Closeout.md"
    ]
    report_sha256: str
    execution_report_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/report.json"
    ]
    execution_report_sha256: str
    execution_manifest_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/manifest.json"
    ]
    execution_manifest_sha256: str
    source_evidence_locked: Literal[True] = True
    protected_evidence_read: Literal[False] = False
    authorization_consumed: Literal[True] = True
    provider_calls_permitted: Literal[False] = False
    rerun_permitted: Literal[False] = False
    next_gate: Literal[ReauthorizationCloseoutNextGate.AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW] = (
        ReauthorizationCloseoutNextGate.AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW
    )

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("source_commit must be a lowercase 40-character SHA")
        return value

    @field_validator(
        "closeout_sha256",
        "report_sha256",
        "execution_report_sha256",
        "execution_manifest_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("closeout manifest requires lowercase SHA-256")
        return value


class GroqCacheTelemetryReauthorizationCloseoutSummary(BaseModel):
    """Metadata-safe closeout validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    closeout_id: Literal["groq-cache-telemetry-reauthorization-closeout-v1"]
    status: Literal[ReauthorizationCloseoutStatus.CLOSED_PROVIDER_WIRE_FIELD_UNAVAILABLE]
    provider_call_count: Literal[2] = 2
    successful_call_count: Literal[2] = 2
    raw_billing_field_absent_count: Literal[2] = 2
    raw_billing_numeric_sample_count: Literal[0] = 0
    authorization_consumed: Literal[True] = True
    provider_calls_permitted: Literal[False] = False
    rerun_permitted: Literal[False] = False
    benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal[ReauthorizationCloseoutNextGate.AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW]
