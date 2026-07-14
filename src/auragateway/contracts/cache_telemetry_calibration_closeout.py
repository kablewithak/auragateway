"""Typed contracts for immutable Groq cache telemetry calibration closeout."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CalibrationCloseoutStatus(StrEnum):
    """Lifecycle state after one-time calibration reconciliation."""

    CLOSED_BILLING_FIELD_UNAVAILABLE = "closed_billing_field_unavailable"


class CalibrationCloseoutClaimKind(StrEnum):
    """Claims independently permitted or blocked by closeout evidence."""

    EXECUTION_COMPLETED = "execution_completed"
    BILLING_FIELD_UNAVAILABLE = "billing_field_unavailable"
    EXACT_UNAVAILABILITY_CAUSE = "exact_unavailability_cause"
    PROVIDER_CACHE_USAGE = "provider_cache_usage"
    PROVIDER_CACHE_SAVINGS = "provider_cache_savings"
    HARDWARE_CACHE_USAGE = "hardware_cache_usage"
    LATENCY_IMPROVEMENT = "latency_improvement"
    ACCEPTED_A_B_C_COMPARISON = "accepted_a_b_c_comparison"


class CalibrationCloseoutClaimDecision(StrEnum):
    """Machine-readable claim decision."""

    PERMITTED = "permitted"
    BLOCKED = "blocked"


class CalibrationCloseoutClaimReason(StrEnum):
    """Bounded reason taxonomy for closeout claim decisions."""

    THREE_SUCCESSFUL_CALLS_VERIFIED = "THREE_SUCCESSFUL_CALLS_VERIFIED"
    FIELD_ABSENT_ON_ALL_SUCCESSFUL_CALLS = "FIELD_ABSENT_ON_ALL_SUCCESSFUL_CALLS"
    CAUSE_NOT_IDENTIFIED_BY_CALIBRATION = "CAUSE_NOT_IDENTIFIED_BY_CALIBRATION"
    BILLING_CACHE_EVIDENCE_UNAVAILABLE = "BILLING_CACHE_EVIDENCE_UNAVAILABLE"
    HARDWARE_CACHE_USAGE_UNAVAILABLE = "HARDWARE_CACHE_USAGE_UNAVAILABLE"
    CALIBRATION_NOT_POWERED_FOR_LATENCY = "CALIBRATION_NOT_POWERED_FOR_LATENCY"
    CALIBRATION_NOT_COMPARISON_ELIGIBLE = "CALIBRATION_NOT_COMPARISON_ELIGIBLE"


class CalibrationCloseoutNextGate(StrEnum):
    """Next project gate selected from the calibration evidence."""

    GROQ_SDK_CACHE_SCHEMA_COMPATIBILITY_REVIEW = "groq_sdk_cache_schema_compatibility_review"


class CalibrationCloseoutBinding(BaseModel):
    """One immutable public execution evidence dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("closeout bindings require lowercase SHA-256")
        return value


class CalibrationCloseoutClaimRecord(BaseModel):
    """One explicit calibration claim boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: CalibrationCloseoutClaimKind
    decision: CalibrationCloseoutClaimDecision
    reason: CalibrationCloseoutClaimReason

    @model_validator(mode="after")
    def validate_decision(self) -> CalibrationCloseoutClaimRecord:
        permitted_reasons = {
            CalibrationCloseoutClaimReason.THREE_SUCCESSFUL_CALLS_VERIFIED,
            CalibrationCloseoutClaimReason.FIELD_ABSENT_ON_ALL_SUCCESSFUL_CALLS,
        }
        if (
            self.decision is CalibrationCloseoutClaimDecision.PERMITTED
            and self.reason not in permitted_reasons
        ):
            raise ValueError("permitted claims require permitted evidence")
        if (
            self.decision is CalibrationCloseoutClaimDecision.BLOCKED
            and self.reason in permitted_reasons
        ):
            raise ValueError("blocked claims require a blocking reason")
        return self


class CalibrationCloseoutExecutionOutcome(BaseModel):
    """Reconciled terminal execution counts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planned_attempt_count: Literal[3] = 3
    provider_call_count: Literal[3] = 3
    successful_call_count: Literal[3] = 3
    provider_error_count: Literal[0] = 0
    telemetry_invalid_count: Literal[0] = 0
    skipped_attempt_count: Literal[0] = 0
    estimated_cost_microusd: Literal[600] = 600
    cost_semantics: Literal["planned_bounded_estimate_not_provider_invoice"] = (
        "planned_bounded_estimate_not_provider_invoice"
    )


class CalibrationCloseoutTokenAssessment(BaseModel):
    """Observed provider token counts and planning-estimate calibration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_token_sample_count: Literal[3] = 3
    observed_input_tokens_each_call: Literal[1401] = 1401
    observed_input_tokens_total: Literal[4203] = 4203
    planned_input_token_estimate_each_call: Literal[2112] = 2112
    planned_input_token_estimate_total: Literal[6336] = 6336
    estimate_minus_observed_tokens: Literal[2133] = 2133
    estimate_over_observed_parts_per_million: Literal[507495] = 507495
    output_token_sample_count: Literal[3] = 3
    observed_output_tokens_each_call: Literal[27] = 27
    observed_output_tokens_total: Literal[81] = 81
    estimator_direction: Literal["conservative_overestimate"] = "conservative_overestimate"


class CalibrationCloseoutDurationAssessment(BaseModel):
    """Descriptive duration evidence without a latency claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    duration_sample_count: Literal[3] = 3
    duration_total_ms: Literal[341] = 341
    mean_duration_milli_ms: Literal[113667] = 113667
    median_duration_milli_ms: Literal[113000] = 113000
    minimum_duration_ms: Literal[98] = 98
    maximum_duration_ms: Literal[130] = 130
    latency_claim_permitted: Literal[False] = False
    semantics: Literal["descriptive_only"] = "descriptive_only"


class CalibrationCloseoutTelemetryAssessment(BaseModel):
    """Successful-response cache telemetry coverage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    installed_sdk_version: Literal["1.5.0"] = "1.5.0"
    installed_sdk_version_sample_count: Literal[3] = 3
    usage_present_count: Literal[3] = 3
    prompt_tokens_details_present_count: Literal[0] = 0
    billing_cached_tokens_field_present_count: Literal[0] = 0
    billing_cache_numeric_sample_count: Literal[0] = 0
    billing_observation_state: Literal["field_absent"] = "field_absent"
    x_groq_present_count: Literal[3] = 3
    x_groq_usage_present_count: Literal[0] = 0
    dram_cached_tokens_field_present_count: Literal[0] = 0
    sram_cached_tokens_field_present_count: Literal[0] = 0
    hardware_cache_numeric_sample_count: Literal[0] = 0
    billing_cache_evidence_available: Literal[False] = False
    hardware_cache_evidence_available: Literal[False] = False
    unknown_interpreted_as_zero: Literal[False] = False


class CalibrationCloseoutImplementationResolution(BaseModel):
    """Engineering decision selected from the closed calibration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    retain_success_telemetry_capture: Literal[True] = True
    request_construction_change_selected: Literal[False] = False
    routing_change_selected: Literal[False] = False
    cache_affinity_change_selected: Literal[False] = False
    benchmark_restart_permitted: Literal[False] = False
    sdk_schema_compatibility_review_required: Literal[True] = True
    provider_response_omission_established: Literal[False] = False
    sdk_schema_incompatibility_established: Literal[False] = False
    exact_cause_established: Literal[False] = False
    reason: Literal["billing_cache_field_absent_across_all_successful_calls"] = (
        "billing_cache_field_absent_across_all_successful_calls"
    )


class CacheTelemetryCalibrationCloseout(BaseModel):
    """Immutable final result of the one-time Groq cache calibration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    closeout_id: Literal["groq-cache-telemetry-calibration-closeout-v1"]
    status: Literal[CalibrationCloseoutStatus.CLOSED_BILLING_FIELD_UNAVAILABLE] = (
        CalibrationCloseoutStatus.CLOSED_BILLING_FIELD_UNAVAILABLE
    )
    authorization_id: Literal["groq-cache-telemetry-calibration-auth-v1"]
    calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    execution_bindings: tuple[CalibrationCloseoutBinding, ...] = Field(
        min_length=6,
        max_length=6,
    )
    execution_outcome: CalibrationCloseoutExecutionOutcome
    token_assessment: CalibrationCloseoutTokenAssessment
    duration_assessment: CalibrationCloseoutDurationAssessment
    telemetry_assessment: CalibrationCloseoutTelemetryAssessment
    claims: tuple[CalibrationCloseoutClaimRecord, ...] = Field(
        min_length=8,
        max_length=8,
    )
    implementation_resolution: CalibrationCloseoutImplementationResolution
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    execution_evidence_mutation_permitted: Literal[False] = False
    provider_cache_usage_claim_permitted: Literal[False] = False
    provider_cache_savings_claim_permitted: Literal[False] = False
    benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    exact_unavailability_cause_established: Literal[False] = False
    next_gate: Literal[CalibrationCloseoutNextGate.GROQ_SDK_CACHE_SCHEMA_COMPATIBILITY_REVIEW] = (
        CalibrationCloseoutNextGate.GROQ_SDK_CACHE_SCHEMA_COMPATIBILITY_REVIEW
    )

    @model_validator(mode="after")
    def validate_closeout(self) -> CacheTelemetryCalibrationCloseout:
        expected_paths = {
            "data/evals/benchmark/cache-telemetry-calibration-v1/authorization.json",
            "data/evals/benchmark/cache-telemetry-calibration-v1/runtime_policy.json",
            "data/evals/benchmark/cache-telemetry-calibration-v1/journal.jsonl",
            "data/evals/benchmark/cache-telemetry-calibration-v1/run_records.json",
            "data/evals/benchmark/cache-telemetry-calibration-v1/report.json",
            "data/evals/benchmark/cache-telemetry-calibration-v1/manifest.json",
        }
        observed_paths = [item.path for item in self.execution_bindings]
        if set(observed_paths) != expected_paths or len(observed_paths) != len(set(observed_paths)):
            raise ValueError("closeout requires all six execution assets")

        expected_claims = set(CalibrationCloseoutClaimKind)
        observed_claims = [item.claim_kind for item in self.claims]
        if set(observed_claims) != expected_claims or len(observed_claims) != len(
            set(observed_claims)
        ):
            raise ValueError("closeout requires all eight claim decisions")
        return self


class CacheTelemetryCalibrationCloseoutManifest(BaseModel):
    """Integrity manifest for closeout JSON and report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    closeout_id: Literal["groq-cache-telemetry-calibration-closeout-v1"]
    closeout_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-closeout-v1/closeout.json"
    ]
    closeout_sha256: str
    report_path: Literal["docs/benchmark/AuraGateway_Cache_Telemetry_Calibration_Closeout.md"]
    report_sha256: str
    execution_manifest_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-v1/manifest.json"
    ]
    execution_manifest_sha256: str
    source_evidence_locked: Literal[True] = True
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    next_gate: Literal[CalibrationCloseoutNextGate.GROQ_SDK_CACHE_SCHEMA_COMPATIBILITY_REVIEW] = (
        CalibrationCloseoutNextGate.GROQ_SDK_CACHE_SCHEMA_COMPATIBILITY_REVIEW
    )

    @field_validator(
        "closeout_sha256",
        "report_sha256",
        "execution_manifest_sha256",
    )
    @classmethod
    def validate_manifest_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("closeout manifest requires lowercase SHA-256")
        return value


class CacheTelemetryCalibrationCloseoutSummary(BaseModel):
    """Metadata-safe closeout validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    closeout_id: Literal["groq-cache-telemetry-calibration-closeout-v1"]
    status: Literal[CalibrationCloseoutStatus.CLOSED_BILLING_FIELD_UNAVAILABLE]
    provider_call_count: Literal[3] = 3
    successful_call_count: Literal[3] = 3
    billing_cache_numeric_sample_count: Literal[0] = 0
    billing_cached_tokens_field_present_count: Literal[0] = 0
    installed_sdk_version: Literal["1.5.0"] = "1.5.0"
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    execution_evidence_mutation_permitted: Literal[False] = False
    benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal[CalibrationCloseoutNextGate.GROQ_SDK_CACHE_SCHEMA_COMPATIBILITY_REVIEW]
