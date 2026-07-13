"""Typed contracts for immutable Batch 06 diagnostic closeout evidence."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DiagnosticCloseoutStatus(StrEnum):
    """Lifecycle state after the one-time diagnostic execution is reconciled."""

    CLOSED_NONREPRODUCED = "closed_nonreproduced"


class DiagnosticHypothesisId(StrEnum):
    """Predeclared hypotheses from the diagnostic design."""

    DETERMINISTIC_REQUEST_DEFECT = "deterministic_request_defect"
    FIRST_SEQUENCE_STATE_EFFECT = "first_sequence_state_effect"
    SPACING_SENSITIVE_PROVIDER_STATE = "spacing_sensitive_provider_state"
    HIDDEN_CONDITION_SPECIFIC_HARNESS_DIFFERENCE = "hidden_condition_specific_harness_difference"
    TRANSIENT_OR_HIDDEN_PROVIDER_BACKEND_EVENT = "transient_or_hidden_provider_backend_event"


class DiagnosticHypothesisVerdict(StrEnum):
    """Bounded verdicts supported by the controlled execution."""

    STRONGLY_CONTRADICTED = "strongly_contradicted"
    NOT_OBSERVED = "not_observed"
    NOT_OBSERVED_FOR_REQUEST_ACCEPTANCE = "not_observed_for_request_acceptance"
    STRONGLY_CONTRADICTED_AT_PROVIDER_BOUNDARY = "strongly_contradicted_at_provider_boundary"
    BEST_SUPPORTED_INFERENCE = "best_supported_inference"


class DiagnosticEvidenceCode(StrEnum):
    """Evidence codes retained without raw prompt or provider output content."""

    ALL_24_CALLS_SUCCEEDED = "ALL_24_CALLS_SUCCEEDED"
    ALL_8_SEQUENCES_COMPLETED = "ALL_8_SEQUENCES_COMPLETED"
    ZERO_REQUEST_REJECTIONS = "ZERO_REQUEST_REJECTIONS"
    ORDER_REVERSALS_SUCCEEDED = "ORDER_REVERSALS_SUCCEEDED"
    ZERO_AND_THIRTY_SECOND_CELLS_SUCCEEDED = "ZERO_AND_THIRTY_SECOND_CELLS_SUCCEEDED"
    MATCHED_B_C_REQUEST_IDENTITIES_SUCCEEDED = "MATCHED_B_C_REQUEST_IDENTITIES_SUCCEEDED"
    CACHE_TELEMETRY_UNAVAILABLE = "CACHE_TELEMETRY_UNAVAILABLE"
    DURATION_OBSERVATIONS_DESCRIPTIVE_ONLY = "DURATION_OBSERVATIONS_DESCRIPTIVE_ONLY"


class DiagnosticClaimKind(StrEnum):
    """Claims independently permitted or blocked by closeout evidence."""

    REQUEST_REJECTION_NONREPRODUCTION = "request_rejection_nonreproduction"
    DETERMINISTIC_REQUEST_DEFECT_CONTRADICTED = "deterministic_request_defect_contradicted"
    EXACT_PROVIDER_ROOT_CAUSE = "exact_provider_root_cause"
    CACHE_USAGE = "cache_usage"
    CACHE_SAVINGS = "cache_savings"
    LATENCY_IMPROVEMENT = "latency_improvement"
    ACCEPTED_A_B_C_COMPARISON = "accepted_a_b_c_comparison"


class DiagnosticClaimDecision(StrEnum):
    """Machine-readable claim decision."""

    PERMITTED = "permitted"
    BLOCKED = "blocked"


class DiagnosticClaimReason(StrEnum):
    """Reason for one claim decision."""

    CONTROLLED_NONREPRODUCTION_OBSERVED = "CONTROLLED_NONREPRODUCTION_OBSERVED"
    DETERMINISTIC_DEFECT_CONTRADICTED = "DETERMINISTIC_DEFECT_CONTRADICTED"
    PROVIDER_INTERNAL_STATE_UNOBSERVED = "PROVIDER_INTERNAL_STATE_UNOBSERVED"
    CACHE_EVIDENCE_UNAVAILABLE = "CACHE_EVIDENCE_UNAVAILABLE"
    DIAGNOSTIC_NOT_POWERED_FOR_LATENCY = "DIAGNOSTIC_NOT_POWERED_FOR_LATENCY"
    COMPARISON_INELIGIBLE_DIAGNOSTIC = "COMPARISON_INELIGIBLE_DIAGNOSTIC"


class DiagnosticImplementationDecision(StrEnum):
    """Engineering action selected from the diagnostic evidence."""

    NO_REQUEST_CONSTRUCTION_OR_ROUTING_FIX = "no_request_construction_or_routing_fix"


class DiagnosticNextGate(StrEnum):
    """Next project gate after immutable closeout."""

    CACHE_TELEMETRY_SUFFICIENCY_REVIEW = "cache_telemetry_sufficiency_review"


class DiagnosticCloseoutBinding(BaseModel):
    """One immutable public evidence dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic closeout bindings require lowercase SHA-256")
        return value


class DiagnosticHypothesisConclusion(BaseModel):
    """One hypothesis verdict with bounded evidence codes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hypothesis_id: DiagnosticHypothesisId
    verdict: DiagnosticHypothesisVerdict
    evidence_codes: tuple[DiagnosticEvidenceCode, ...] = Field(
        min_length=1,
        max_length=5,
    )


class DiagnosticClaimDecisionRecord(BaseModel):
    """One explicit claim boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: DiagnosticClaimKind
    decision: DiagnosticClaimDecision
    reason: DiagnosticClaimReason

    @model_validator(mode="after")
    def validate_reason(self) -> DiagnosticClaimDecisionRecord:
        permitted_reasons = {
            DiagnosticClaimReason.CONTROLLED_NONREPRODUCTION_OBSERVED,
            DiagnosticClaimReason.DETERMINISTIC_DEFECT_CONTRADICTED,
        }
        if (
            self.decision is DiagnosticClaimDecision.PERMITTED
            and self.reason not in permitted_reasons
        ):
            raise ValueError("permitted claims require a permitted evidence reason")
        if self.decision is DiagnosticClaimDecision.BLOCKED and self.reason in permitted_reasons:
            raise ValueError("blocked claims require a blocking evidence reason")
        return self


class DiagnosticExecutionOutcome(BaseModel):
    """Reconciled terminal execution counts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planned_attempt_count: Literal[24] = 24
    provider_call_count: Literal[24] = 24
    successful_call_count: Literal[24] = 24
    provider_error_count: Literal[0] = 0
    skipped_attempt_count: Literal[0] = 0
    planned_sequence_count: Literal[8] = 8
    completed_sequence_count: Literal[8] = 8
    request_rejected_sequence_count: Literal[0] = 0
    experiment_stopped_sequence_count: Literal[0] = 0
    not_started_sequence_count: Literal[0] = 0
    estimated_cost_microusd: Literal[4992] = 4992
    cost_semantics: Literal["planned_bounded_estimate_not_provider_invoice"] = (
        "planned_bounded_estimate_not_provider_invoice"
    )


class DiagnosticTokenCalibration(BaseModel):
    """Observed provider token counts compared with frozen preflight estimates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    estimate_sample_count: Literal[24] = 24
    observed_input_token_sample_count: Literal[24] = 24
    estimated_input_tokens_total: Literal[43400] = 43400
    observed_input_tokens_total: Literal[40151] = 40151
    estimate_minus_observed_tokens: Literal[3249] = 3249
    estimate_over_observed_parts_per_million: Literal[80920] = 80920
    estimator_direction: Literal["conservative_overestimate"] = "conservative_overestimate"


class DiagnosticCacheTelemetryAssessment(BaseModel):
    """Cache telemetry coverage with unknown preserved as unknown."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cached_input_token_sample_count: Literal[0] = 0
    nonzero_cached_input_token_sample_count: Literal[0] = 0
    total_cached_input_tokens: None = None
    cached_share_parts_per_million: None = None
    cache_evidence_available: Literal[False] = False
    unknown_interpreted_as_zero: Literal[False] = False
    reason: Literal[DiagnosticClaimReason.CACHE_EVIDENCE_UNAVAILABLE] = (
        DiagnosticClaimReason.CACHE_EVIDENCE_UNAVAILABLE
    )


class DiagnosticDurationAssessment(BaseModel):
    """Descriptive duration observations that are not promoted to a latency claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    duration_sample_count: Literal[24] = 24
    duration_total_ms: Literal[4595] = 4595
    mean_duration_milli_ms: Literal[191458] = 191458
    median_duration_milli_ms: Literal[172500] = 172500
    minimum_duration_ms: Literal[135] = 135
    maximum_duration_ms: Literal[373] = 373
    repeated_request_pair_count: Literal[6] = 6
    second_occurrence_faster_pair_count: Literal[5] = 5
    mean_second_minus_first_duration_milli_ms: Literal[-49333] = -49333
    median_second_minus_first_duration_milli_ms: Literal[-26500] = -26500
    latency_claim_permitted: Literal[False] = False
    semantics: Literal["descriptive_only"] = "descriptive_only"


class DiagnosticImplementationResolution(BaseModel):
    """Engineering decision after the hypothesis review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[DiagnosticImplementationDecision.NO_REQUEST_CONSTRUCTION_OR_ROUTING_FIX] = (
        DiagnosticImplementationDecision.NO_REQUEST_CONSTRUCTION_OR_ROUTING_FIX
    )
    request_construction_change_selected: Literal[False] = False
    routing_change_selected: Literal[False] = False
    cache_affinity_change_selected: Literal[False] = False
    provider_error_taxonomy_hardening_retained: Literal[True] = True
    reason: Literal["controlled_execution_did_not_reproduce_a_deterministic_harness_defect"] = (
        "controlled_execution_did_not_reproduce_a_deterministic_harness_defect"
    )


class DiagnosticCloseout(BaseModel):
    """Immutable final diagnostic result for the Batch 06 rejection investigation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    closeout_id: Literal["batch-06-diagnostic-closeout-v1"]
    status: Literal[DiagnosticCloseoutStatus.CLOSED_NONREPRODUCED] = (
        DiagnosticCloseoutStatus.CLOSED_NONREPRODUCED
    )
    source_batch_id: Literal["auragateway-live-development-batch-06"]
    source_batch_status: Literal["failed_verified"] = "failed_verified"
    authorization_id: Literal["batch-06-diagnostic-execution-auth-v1"]
    execution_bindings: tuple[DiagnosticCloseoutBinding, ...] = Field(
        min_length=6,
        max_length=6,
    )
    execution_outcome: DiagnosticExecutionOutcome
    token_calibration: DiagnosticTokenCalibration
    cache_telemetry: DiagnosticCacheTelemetryAssessment
    duration_assessment: DiagnosticDurationAssessment
    hypotheses: tuple[DiagnosticHypothesisConclusion, ...] = Field(
        min_length=5,
        max_length=5,
    )
    claims: tuple[DiagnosticClaimDecisionRecord, ...] = Field(
        min_length=7,
        max_length=7,
    )
    implementation_resolution: DiagnosticImplementationResolution
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    execution_evidence_mutation_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    exact_provider_root_cause_established: Literal[False] = False
    best_supported_explanation: Literal["transient_or_hidden_provider_backend_event"] = (
        "transient_or_hidden_provider_backend_event"
    )
    next_gate: Literal[DiagnosticNextGate.CACHE_TELEMETRY_SUFFICIENCY_REVIEW] = (
        DiagnosticNextGate.CACHE_TELEMETRY_SUFFICIENCY_REVIEW
    )

    @model_validator(mode="after")
    def validate_closeout(self) -> DiagnosticCloseout:
        expected_paths = {
            "data/evals/benchmark/diagnostic-execution-v1/authorization.json",
            "data/evals/benchmark/diagnostic-execution-v1/runtime_policy.json",
            "data/evals/benchmark/diagnostic-execution-v1/journal.jsonl",
            "data/evals/benchmark/diagnostic-execution-v1/run_records.json",
            "data/evals/benchmark/diagnostic-execution-v1/report.json",
            "data/evals/benchmark/diagnostic-execution-v1/manifest.json",
        }
        observed_paths = [item.path for item in self.execution_bindings]
        if set(observed_paths) != expected_paths or len(observed_paths) != len(set(observed_paths)):
            raise ValueError("diagnostic closeout requires the six execution assets")

        expected_hypotheses = set(DiagnosticHypothesisId)
        observed_hypotheses = [item.hypothesis_id for item in self.hypotheses]
        if set(observed_hypotheses) != expected_hypotheses or len(observed_hypotheses) != len(
            set(observed_hypotheses)
        ):
            raise ValueError("diagnostic closeout requires all five hypotheses exactly")

        expected_claims = set(DiagnosticClaimKind)
        observed_claims = [item.claim_kind for item in self.claims]
        if set(observed_claims) != expected_claims or len(observed_claims) != len(
            set(observed_claims)
        ):
            raise ValueError("diagnostic closeout requires all seven claim decisions")
        return self


class DiagnosticCloseoutManifest(BaseModel):
    """Integrity manifest for the closeout JSON and human-readable report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    closeout_id: Literal["batch-06-diagnostic-closeout-v1"]
    closeout_path: Literal["data/evals/benchmark/diagnostic-closeout-v1/closeout.json"]
    closeout_sha256: str
    report_path: Literal["docs/benchmark/AuraGateway_Batch_06_Diagnostic_Closeout.md"]
    report_sha256: str
    execution_manifest_path: Literal["data/evals/benchmark/diagnostic-execution-v1/manifest.json"]
    execution_manifest_sha256: str
    source_evidence_locked: Literal[True] = True
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    next_gate: Literal[DiagnosticNextGate.CACHE_TELEMETRY_SUFFICIENCY_REVIEW] = (
        DiagnosticNextGate.CACHE_TELEMETRY_SUFFICIENCY_REVIEW
    )

    @field_validator(
        "closeout_sha256",
        "report_sha256",
        "execution_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic closeout manifest requires lowercase SHA-256")
        return value


class DiagnosticCloseoutValidationSummary(BaseModel):
    """Metadata-safe CLI result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    closeout_id: Literal["batch-06-diagnostic-closeout-v1"]
    status: Literal[DiagnosticCloseoutStatus.CLOSED_NONREPRODUCED]
    provider_call_count: Literal[24] = 24
    successful_call_count: Literal[24] = 24
    provider_error_count: Literal[0] = 0
    cached_input_token_sample_count: Literal[0] = 0
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    execution_evidence_mutation_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal[DiagnosticNextGate.CACHE_TELEMETRY_SUFFICIENCY_REVIEW] = (
        DiagnosticNextGate.CACHE_TELEMETRY_SUFFICIENCY_REVIEW
    )
