"""Typed contracts for non-live provider diagnostic experiment design."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")


class DiagnosticPlanStatus(StrEnum):
    """Lifecycle state of a provider diagnostic experiment plan."""

    DESIGN_ONLY = "design_only"
    FIXTURE_READY = "fixture_ready"
    AUTHORIZED = "authorized"


class DiagnosticHypothesisId(StrEnum):
    """Competing explanations retained before any new provider execution."""

    DETERMINISTIC_REQUEST_DEFECT = "h1_deterministic_request_defect"
    FIRST_SEQUENCE_STATE_EFFECT = "h2_first_sequence_state_effect"
    SPACING_SENSITIVE_STATE = "h3_spacing_sensitive_state"
    CONDITION_SPECIFIC_HARNESS_DIFFERENCE = "h4_condition_specific_harness_difference"
    TRANSIENT_PROVIDER_BACKEND = "h5_transient_provider_backend"


class DiagnosticStage(StrEnum):
    """Purpose of one predeclared sequence group."""

    ORDER_REVERSAL = "order_reversal"
    SPACING_MATRIX = "spacing_matrix"


class DiagnosticConditionLabel(StrEnum):
    """Local condition labels compared at an equivalent provider boundary."""

    CONDITION_B = "condition_b"
    CONDITION_C = "condition_c"


class DiagnosticCohortStatus(StrEnum):
    """Whether a privacy-safe prompt cohort has been frozen."""

    PENDING = "pending"
    MATERIALIZED = "materialized"


class DiagnosticStopDisposition(StrEnum):
    """Whether one observed failure stops a cell or the whole experiment."""

    STOP_SEQUENCE_CONTINUE_PLAN = "stop_sequence_continue_plan"
    STOP_EXPERIMENT = "stop_experiment"


class DiagnosticHypothesis(BaseModel):
    """One explicit hypothesis with diagnostic support and weakening patterns."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hypothesis_id: DiagnosticHypothesisId
    statement: str = Field(min_length=20, max_length=500)
    supporting_pattern: str = Field(min_length=20, max_length=700)
    weakening_pattern: str = Field(min_length=20, max_length=700)


class SourceFailureAnchor(BaseModel):
    """Public metadata anchoring the design to the Batch 06 observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_batch_id: Literal["auragateway-live-development-batch-06"]
    source_authorization_id: Literal["live-development-batch-06-auth-v1"]
    failed_run_id: Literal["run-functional-ep-func-001-r03-condition-c"]
    failed_condition: Literal["condition_c"]
    failed_turn_index: Literal[3]
    matched_success_run_id: Literal["run-functional-ep-func-001-r03-condition-b"]
    matched_success_condition: Literal["condition_b"]
    matched_success_turn_index: Literal[3]
    system_prompt_sha256: str
    user_prompt_sha256: str
    prompt_byte_count: Literal[8109]
    matched_success_input_tokens: Literal[1884]
    failed_public_error_code: Literal["PROVIDER_RESPONSE_INVALID"]
    failed_diagnostic_family: Literal["request_rejected"]
    failed_http_status_code: Literal[400]

    @field_validator("system_prompt_sha256", "user_prompt_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("source failure anchor hashes must be lowercase SHA-256")
        return value


class PromptCohortMaterializationContract(BaseModel):
    """Offline requirements for privacy-safe prompt cohorts created later."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    required_turn_count: Literal[3] = 3
    source_turn_prompt_byte_counts: tuple[Literal[7365], Literal[7737], Literal[8109]]
    source_input_token_estimates: tuple[Literal[1732], Literal[1809], Literal[1884]]
    exact_byte_count_match_required: Literal[True] = True
    maximum_input_token_estimate_delta: Literal[25] = 25
    unique_stable_prefix_per_cohort_required: Literal[True] = True
    provider_visible_b_c_equivalence_required: Literal[True] = True
    synthetic_content_only: Literal[True] = True
    pii_or_secret_content_permitted: Literal[False] = False
    raw_prompt_commit_permitted: Literal[False] = False


class DiagnosticPromptCohort(BaseModel):
    """One future local-only prompt cohort referenced by the design."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cohort_id: str
    status: DiagnosticCohortStatus
    stable_prefix_sha256: str | None = None
    user_prompt_sha256_by_turn: tuple[str, str, str] | None = None
    total_prompt_bytes_by_turn: tuple[int, int, int] | None = None
    input_token_estimate_by_turn: tuple[int, int, int] | None = None

    @field_validator("cohort_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("cohort_id must use a stable lowercase slug")
        return value

    @field_validator("stable_prefix_sha256")
    @classmethod
    def validate_optional_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("cohort stable prefix must be lowercase SHA-256")
        return value

    @field_validator("user_prompt_sha256_by_turn")
    @classmethod
    def validate_turn_hashes(
        cls,
        value: tuple[str, str, str] | None,
    ) -> tuple[str, str, str] | None:
        if value is not None and any(_SHA256_PATTERN.fullmatch(item) is None for item in value):
            raise ValueError("cohort turn hashes must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_materialization_state(self) -> DiagnosticPromptCohort:
        materialized_values = (
            self.stable_prefix_sha256,
            self.user_prompt_sha256_by_turn,
            self.total_prompt_bytes_by_turn,
            self.input_token_estimate_by_turn,
        )
        if self.status is DiagnosticCohortStatus.PENDING:
            if any(value is not None for value in materialized_values):
                raise ValueError("pending cohorts must not claim materialized prompt identities")
            return self
        if any(value is None for value in materialized_values):
            raise ValueError("materialized cohorts require complete prompt identities")
        return self


class DiagnosticSequence(BaseModel):
    """One predeclared three-request sequence within the experiment matrix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence_id: str
    schedule_index: int = Field(ge=0, le=31)
    stage: DiagnosticStage
    cohort_id: str
    condition_label: DiagnosticConditionLabel
    cohort_sequence_position: int = Field(ge=1, le=2)
    matched_sequence_id: str | None = None
    turn_count: Literal[3] = 3
    inter_turn_delay_seconds: Literal[0, 30]
    minimum_delay_after_previous_sequence_seconds: Literal[0, 300]
    maximum_request_attempts: Literal[3] = 3
    retry_permitted: Literal[False] = False

    @field_validator("sequence_id", "cohort_id", "matched_sequence_id")
    @classmethod
    def validate_identifier(cls, value: str | None) -> str | None:
        if value is not None and _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic sequence identifiers must use lowercase slugs")
        return value


class DiagnosticStopRule(BaseModel):
    """One machine-readable stop or continuation rule."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    trigger_codes: tuple[str, ...] = Field(min_length=1)
    disposition: DiagnosticStopDisposition
    safe_rationale: str = Field(min_length=20, max_length=500)

    @field_validator("rule_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("stop rule IDs must use lowercase slugs")
        return value

    @field_validator("trigger_codes")
    @classmethod
    def validate_trigger_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("stop rule trigger codes must be unique")
        if any(not item or len(item) > 96 for item in value):
            raise ValueError("stop rule trigger codes must be bounded")
        return value


class DiagnosticExperimentPlan(BaseModel):
    """Design-only matrix that cannot itself authorize provider execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    design_id: Literal["batch-06-request-rejection-diagnostic-design-v1"]
    status: DiagnosticPlanStatus
    source_anchor: SourceFailureAnchor
    hypotheses: tuple[DiagnosticHypothesis, ...] = Field(min_length=5, max_length=5)
    materialization_contract: PromptCohortMaterializationContract
    cohorts: tuple[DiagnosticPromptCohort, ...] = Field(min_length=6, max_length=6)
    sequences: tuple[DiagnosticSequence, ...] = Field(min_length=8, max_length=8)
    stop_rules: tuple[DiagnosticStopRule, ...] = Field(min_length=2)
    required_trace_fields: tuple[str, ...] = Field(min_length=12)
    maximum_provider_calls: Literal[24] = 24
    maximum_total_cost_microusd: Literal[5000] = 5000
    execution_authorization_required: Literal[True] = True
    execution_authorization_id: None = None
    provider_calls_permitted: Literal[False] = False
    retries_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    development_only: Literal[True] = True
    held_out_execution_permitted: Literal[False] = False
    full_benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal["fixture_materialization_review"] = "fixture_materialization_review"

    @model_validator(mode="after")
    def validate_design_matrix(self) -> DiagnosticExperimentPlan:
        if self.status is not DiagnosticPlanStatus.DESIGN_ONLY:
            raise ValueError("this artifact must remain design-only")

        hypothesis_ids = [item.hypothesis_id for item in self.hypotheses]
        if set(hypothesis_ids) != set(DiagnosticHypothesisId):
            raise ValueError("diagnostic design must cover all five competing hypotheses")
        if len(hypothesis_ids) != len(set(hypothesis_ids)):
            raise ValueError("diagnostic hypothesis IDs must be unique")

        cohort_ids = [item.cohort_id for item in self.cohorts]
        expected_cohorts = {
            "cohort-alpha",
            "cohort-beta",
            "cohort-gamma",
            "cohort-delta",
            "cohort-epsilon",
            "cohort-zeta",
        }
        if set(cohort_ids) != expected_cohorts or len(cohort_ids) != len(set(cohort_ids)):
            raise ValueError("diagnostic design requires the six frozen cohort roles exactly")
        if any(item.status is not DiagnosticCohortStatus.PENDING for item in self.cohorts):
            raise ValueError("design-only cohorts must remain pending materialization")

        sequence_ids = [item.sequence_id for item in self.sequences]
        if len(sequence_ids) != len(set(sequence_ids)):
            raise ValueError("diagnostic sequence IDs must be unique")
        if [item.schedule_index for item in self.sequences] != list(range(8)):
            raise ValueError("diagnostic sequence schedule indices must be contiguous")
        planned_request_count = sum(int(item.maximum_request_attempts) for item in self.sequences)
        if planned_request_count != self.maximum_provider_calls:
            raise ValueError("provider call budget must equal the frozen sequence request budget")
        if any(item.cohort_id not in expected_cohorts for item in self.sequences):
            raise ValueError("every diagnostic sequence must reference a declared cohort")

        order_sequences = [
            item for item in self.sequences if item.stage is DiagnosticStage.ORDER_REVERSAL
        ]
        if len(order_sequences) != 4:
            raise ValueError("order-reversal stage requires four sequences")
        for cohort_id in ("cohort-alpha", "cohort-beta"):
            pair = [item for item in order_sequences if item.cohort_id == cohort_id]
            if len(pair) != 2:
                raise ValueError("each order-reversal cohort requires two matched sequences")
            if {item.condition_label for item in pair} != set(DiagnosticConditionLabel):
                raise ValueError("order-reversal pairs require condition B and condition C")
            if {item.cohort_sequence_position for item in pair} != {1, 2}:
                raise ValueError("order-reversal pairs require first and second positions")
            if any(item.inter_turn_delay_seconds != 0 for item in pair):
                raise ValueError("order-reversal sequences use zero-second inter-turn spacing")
            pair_ids = {item.sequence_id for item in pair}
            if any(item.matched_sequence_id not in pair_ids for item in pair):
                raise ValueError("order-reversal sequences must cross-reference their pair")

        alpha_first = next(
            item
            for item in order_sequences
            if item.cohort_id == "cohort-alpha" and item.cohort_sequence_position == 1
        )
        beta_first = next(
            item
            for item in order_sequences
            if item.cohort_id == "cohort-beta" and item.cohort_sequence_position == 1
        )
        if alpha_first.condition_label is not DiagnosticConditionLabel.CONDITION_B:
            raise ValueError("cohort alpha must execute B before C")
        if beta_first.condition_label is not DiagnosticConditionLabel.CONDITION_C:
            raise ValueError("cohort beta must execute C before B")

        spacing_sequences = [
            item for item in self.sequences if item.stage is DiagnosticStage.SPACING_MATRIX
        ]
        if len(spacing_sequences) != 4:
            raise ValueError("spacing stage requires a balanced four-cell matrix")
        spacing_cells = {
            (item.condition_label, item.inter_turn_delay_seconds) for item in spacing_sequences
        }
        expected_cells = {
            (DiagnosticConditionLabel.CONDITION_B, 0),
            (DiagnosticConditionLabel.CONDITION_B, 30),
            (DiagnosticConditionLabel.CONDITION_C, 0),
            (DiagnosticConditionLabel.CONDITION_C, 30),
        }
        if spacing_cells != expected_cells:
            raise ValueError("spacing matrix must cover both labels at zero and thirty seconds")
        if any(item.cohort_sequence_position != 1 for item in spacing_sequences):
            raise ValueError("spacing cohorts must each execute one isolated sequence")
        if any(item.matched_sequence_id is not None for item in spacing_sequences):
            raise ValueError("spacing matrix sequences must use distinct independent cohorts")

        required_fields = {
            "design_id",
            "sequence_id",
            "stage",
            "cohort_id",
            "condition_label",
            "schedule_index",
            "cohort_sequence_position",
            "turn_index",
            "planned_inter_turn_delay_seconds",
            "observed_inter_turn_delay_ms",
            "system_prompt_sha256",
            "user_prompt_sha256",
            "prompt_byte_count",
            "input_token_estimate",
            "provider_status",
            "provider_error_code",
            "request_rejection_reason",
            "provider_request_id_sha256",
            "adapter_version",
            "estimated_cost_microusd",
            "protected_diagnostic_retained",
        }
        if len(self.required_trace_fields) != len(set(self.required_trace_fields)):
            raise ValueError("required trace fields must be unique")
        if not required_fields.issubset(set(self.required_trace_fields)):
            raise ValueError("required trace fields are incomplete")

        return self


class DiagnosticDesignManifest(BaseModel):
    """Integrity binding for the design and its Batch 06 evidence anchor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    design_id: Literal["batch-06-request-rejection-diagnostic-design-v1"]
    plan_path: Literal["data/evals/benchmark/diagnostic-design-v1/experiment_plan.json"]
    plan_sha256: str
    source_batch_manifest_path: Literal["data/evals/benchmark/live-development-v6/manifest.json"]
    source_batch_id: Literal["auragateway-live-development-batch-06"]
    source_authorization_id: Literal["live-development-batch-06-auth-v1"]
    source_journal_sha256: str
    source_run_records_sha256: str
    source_report_sha256: str
    source_batch_verification_required: Literal[True] = True
    execution_authorized: Literal[False] = False

    @field_validator(
        "plan_sha256",
        "source_journal_sha256",
        "source_run_records_sha256",
        "source_report_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic design manifest hashes must be lowercase SHA-256")
        return value


class DiagnosticDesignValidationSummary(BaseModel):
    """Metadata-only validation result for the design artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate-diagnostic-design"] = "validate-diagnostic-design"
    design_id: str
    status: DiagnosticPlanStatus
    hypothesis_count: int = Field(ge=0)
    cohort_count: int = Field(ge=0)
    sequence_count: int = Field(ge=0)
    maximum_provider_calls: int = Field(ge=0)
    plan_sha256: str
    source_batch_verified: Literal[True] = True
    provider_calls_permitted: Literal[False] = False
    authorization_created: Literal[False] = False
    execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
