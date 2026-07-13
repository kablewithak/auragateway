"""Typed contracts for one-time diagnostic provider execution."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.diagnostic_experiment import (
    DiagnosticConditionLabel,
    DiagnosticStage,
)
from auragateway.contracts.provider import ProviderErrorCode, ProviderName

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class DiagnosticExecutionAuthorizationStatus(StrEnum):
    """Lifecycle state of the one-time execution authorization."""

    ACTIVE = "active"


class DiagnosticExecutionAttemptStatus(StrEnum):
    """Terminal state for every planned attempt."""

    SUCCEEDED = "succeeded"
    PROVIDER_ERROR = "provider_error"
    SKIPPED_SEQUENCE = "skipped_sequence"
    SKIPPED_EXPERIMENT = "skipped_experiment"


class DiagnosticSequenceStatus(StrEnum):
    """Terminal state for one three-turn diagnostic sequence."""

    COMPLETED = "completed"
    REQUEST_REJECTED = "request_rejected"
    EXPERIMENT_STOPPED = "experiment_stopped"
    NOT_STARTED = "not_started"


class DiagnosticExecutionStopAction(StrEnum):
    """Runtime action after one provider result."""

    CONTINUE = "continue"
    STOP_SEQUENCE = "stop_sequence"
    STOP_EXPERIMENT = "stop_experiment"


class DiagnosticExecutionBinding(BaseModel):
    """One immutable dependency bound into active authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    sha256: str
    protected_local: bool = False

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic execution bindings require lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_local_boundary(self) -> DiagnosticExecutionBinding:
        if self.protected_local != self.path.startswith(".local/"):
            raise ValueError("protected_local must match the .local path boundary")
        return self


class DiagnosticExecutionEvidencePaths(BaseModel):
    """Public and protected evidence destinations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_path: Literal["data/evals/benchmark/diagnostic-execution-v1/authorization.json"]
    runtime_policy_path: Literal["data/evals/benchmark/diagnostic-execution-v1/runtime_policy.json"]
    journal_path: Literal["data/evals/benchmark/diagnostic-execution-v1/journal.jsonl"]
    run_records_path: Literal["data/evals/benchmark/diagnostic-execution-v1/run_records.json"]
    report_path: Literal["data/evals/benchmark/diagnostic-execution-v1/report.json"]
    manifest_path: Literal["data/evals/benchmark/diagnostic-execution-v1/manifest.json"]
    protected_raw_outputs_path: Literal[
        ".local/benchmark/diagnostic-execution-v1/provider_raw_outputs.jsonl"
    ]
    protected_failure_diagnostics_path: Literal[
        ".local/benchmark/diagnostic-execution-v1/provider_failure_diagnostics.jsonl"
    ]


class DiagnosticExecutionAuthorization(BaseModel):
    """One-time authorization that exposes execution but does not perform it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["batch-06-diagnostic-execution-auth-v1"]
    status: DiagnosticExecutionAuthorizationStatus
    review_id: Literal["batch-06-diagnostic-execution-review-v1"]
    design_id: Literal["batch-06-request-rejection-diagnostic-design-v1"]
    fixture_id: Literal["batch-06-diagnostic-prompt-fixtures-v1"]
    bindings: tuple[DiagnosticExecutionBinding, ...] = Field(
        min_length=5,
        max_length=5,
    )
    provider: Literal[ProviderName.GROQ] = ProviderName.GROQ
    provider_model_alias: Literal["groq-gpt-oss-20b"] = "groq-gpt-oss-20b"
    exact_model_identifier: Literal["openai/gpt-oss-20b"] = "openai/gpt-oss-20b"
    adapter_version: Literal["groq-chat-completions-v1"] = "groq-chat-completions-v1"
    timeout_seconds: Literal[30] = 30
    maximum_completion_tokens: Literal[256] = 256
    maximum_provider_calls: Literal[24] = 24
    maximum_total_cost_microusd: Literal[5000] = 5000
    minimum_planned_elapsed_seconds: Literal[2220] = 2220
    sequence_count: Literal[8] = 8
    planned_attempt_count: Literal[24] = 24
    confirmation_phrase: Literal["EXECUTE_BATCH_06_DIAGNOSTIC_ONCE"] = (
        "EXECUTE_BATCH_06_DIAGNOSTIC_ONCE"
    )
    evidence_paths: DiagnosticExecutionEvidencePaths
    one_time_execution: Literal[True] = True
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    held_out_execution_permitted: Literal[False] = False
    full_benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    credential_required: Literal[True] = True
    provider_calls_permitted: Literal[True] = True
    execution_command_available: Literal[True] = True
    execution_completed: Literal[False] = False
    next_gate: Literal["live_execution_preflight"] = "live_execution_preflight"

    @model_validator(mode="after")
    def validate_binding_set(self) -> DiagnosticExecutionAuthorization:
        expected_paths = {
            "data/evals/benchmark/diagnostic-authorization-review-v1/review_package.json",
            "data/evals/benchmark/diagnostic-authorization-review-v1/dry_run_report.json",
            "data/evals/benchmark/diagnostic-authorization-review-v1/manifest.json",
            "data/evals/benchmark/diagnostic-fixtures-v1/fixture_manifest.json",
            ".local/benchmark/diagnostic-fixtures-v1/prompt_cohorts.json",
        }
        observed = [item.path for item in self.bindings]
        if set(observed) != expected_paths or len(observed) != len(set(observed)):
            raise ValueError("active authorization must bind the five reviewed assets")
        if sum(item.protected_local for item in self.bindings) != 1:
            raise ValueError("active authorization requires one protected-local binding")
        return self


class DiagnosticExecutionRuntimePolicy(BaseModel):
    """Fail-closed runtime policy bound to the active authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["batch-06-diagnostic-execution-auth-v1"]
    review_id: Literal["batch-06-diagnostic-execution-review-v1"]
    schedule_offsets_seconds: tuple[
        Literal[0],
        Literal[0],
        Literal[0],
        Literal[300],
        Literal[300],
        Literal[300],
        Literal[600],
        Literal[600],
        Literal[600],
        Literal[900],
        Literal[900],
        Literal[900],
        Literal[1200],
        Literal[1200],
        Literal[1200],
        Literal[1500],
        Literal[1530],
        Literal[1560],
        Literal[1860],
        Literal[1860],
        Literal[1860],
        Literal[2160],
        Literal[2190],
        Literal[2220],
    ]
    planned_cost_microusd_per_provider_call: Literal[208] = 208
    planned_maximum_cost_microusd: Literal[4992] = 4992
    authorization_cost_ceiling_microusd: Literal[5000] = 5000
    request_rejection_error_code: Literal[ProviderErrorCode.REQUEST_REJECTED] = (
        ProviderErrorCode.REQUEST_REJECTED
    )
    request_rejection_action: Literal[DiagnosticExecutionStopAction.STOP_SEQUENCE] = (
        DiagnosticExecutionStopAction.STOP_SEQUENCE
    )
    other_provider_error_action: Literal[DiagnosticExecutionStopAction.STOP_EXPERIMENT] = (
        DiagnosticExecutionStopAction.STOP_EXPERIMENT
    )
    successful_call_action: Literal[DiagnosticExecutionStopAction.CONTINUE] = (
        DiagnosticExecutionStopAction.CONTINUE
    )
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    absolute_schedule_enforced: Literal[True] = True
    write_through_journal_required: Literal[True] = True
    protected_output_retention_required: Literal[True] = True
    protected_failure_diagnostics_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_budget(self) -> DiagnosticExecutionRuntimePolicy:
        if len(self.schedule_offsets_seconds) != 24:
            raise ValueError("diagnostic execution schedule requires 24 offsets")
        if self.schedule_offsets_seconds[-1] != 2220:
            raise ValueError("diagnostic execution schedule must end at 2220 seconds")
        if self.planned_maximum_cost_microusd != (
            self.planned_cost_microusd_per_provider_call * 24
        ):
            raise ValueError("planned diagnostic cost must cover all provider calls")
        if self.planned_maximum_cost_microusd > self.authorization_cost_ceiling_microusd:
            raise ValueError("planned diagnostic cost exceeds authorization ceiling")
        return self


class DiagnosticExecutionAttemptRecord(BaseModel):
    """Public metadata-only terminal record for one planned attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_index: int = Field(ge=0, le=23)
    sequence_id: str
    sequence_schedule_index: int = Field(ge=0, le=7)
    stage: DiagnosticStage
    cohort_id: str
    condition_label: DiagnosticConditionLabel
    turn_index: int = Field(ge=1, le=3)
    planned_offset_seconds: int = Field(ge=0, le=2220)
    observed_offset_ms: int | None = Field(default=None, ge=0)
    system_prompt_sha256: str
    user_prompt_sha256: str
    provider_request_sha256: str
    prompt_byte_count: int = Field(gt=0)
    input_token_estimate: int = Field(gt=0)
    status: DiagnosticExecutionAttemptStatus
    provider_call_made: bool
    provider_error_code: ProviderErrorCode | None = None
    output_sha256: str | None = None
    output_byte_count: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_duration_ms: int | None = Field(default=None, ge=0)
    estimated_cost_microusd: int = Field(ge=0, le=208)

    @field_validator(
        "sequence_id",
        "cohort_id",
    )
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic execution IDs must use stable lowercase characters")
        return value

    @field_validator(
        "system_prompt_sha256",
        "user_prompt_sha256",
        "provider_request_sha256",
        "output_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic execution identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_terminal_state(self) -> DiagnosticExecutionAttemptRecord:
        if self.status is DiagnosticExecutionAttemptStatus.SUCCEEDED:
            if not self.provider_call_made:
                raise ValueError("successful attempts require one provider call")
            if self.provider_error_code is not None or self.output_sha256 is None:
                raise ValueError("successful attempts require output identity only")
            if self.output_byte_count is None:
                raise ValueError("successful attempts require protected output byte count")
            if self.estimated_cost_microusd != 208:
                raise ValueError("successful provider calls require planned cost")
            return self
        if self.status is DiagnosticExecutionAttemptStatus.PROVIDER_ERROR:
            if not self.provider_call_made or self.provider_error_code is None:
                raise ValueError("provider errors require one call and an error code")
            if self.output_sha256 is not None or self.output_byte_count is not None:
                raise ValueError("provider errors cannot claim protected output")
            if self.estimated_cost_microusd != 208:
                raise ValueError("provider-error calls require planned cost")
            return self
        if self.provider_call_made:
            raise ValueError("skipped attempts cannot claim provider calls")
        if self.provider_error_code is not None or self.output_sha256 is not None:
            raise ValueError("skipped attempts cannot claim provider results")
        if self.observed_offset_ms is not None:
            raise ValueError("skipped attempts cannot claim observed call timing")
        if self.estimated_cost_microusd != 0:
            raise ValueError("skipped attempts cannot consume planned provider cost")
        return self


class DiagnosticSequenceRecord(BaseModel):
    """Terminal accountability for one planned sequence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence_id: str
    status: DiagnosticSequenceStatus
    planned_attempt_count: Literal[3] = 3
    provider_call_count: int = Field(ge=0, le=3)
    successful_call_count: int = Field(ge=0, le=3)
    provider_error_count: int = Field(ge=0, le=1)
    skipped_attempt_count: int = Field(ge=0, le=3)
    terminal_error_code: ProviderErrorCode | None = None

    @field_validator("sequence_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("sequence IDs must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> DiagnosticSequenceRecord:
        if self.successful_call_count + self.provider_error_count + self.skipped_attempt_count != 3:
            raise ValueError("sequence records must account for all three attempts")
        if self.provider_call_count != (self.successful_call_count + self.provider_error_count):
            raise ValueError("sequence provider call count is inconsistent")
        if self.status is DiagnosticSequenceStatus.COMPLETED and (
            self.successful_call_count != 3 or self.terminal_error_code is not None
        ):
            raise ValueError("completed sequences require three successful calls")
        if (
            self.status is DiagnosticSequenceStatus.REQUEST_REJECTED
            and self.terminal_error_code is not ProviderErrorCode.REQUEST_REJECTED
        ):
            raise ValueError("request-rejected sequences require the matching error")
        return self


class DiagnosticExecutionRecordSet(BaseModel):
    """Public reconciled records for one one-time diagnostic execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["batch-06-diagnostic-execution-auth-v1"]
    attempts: tuple[DiagnosticExecutionAttemptRecord, ...] = Field(
        min_length=24,
        max_length=24,
    )
    sequences: tuple[DiagnosticSequenceRecord, ...] = Field(
        min_length=8,
        max_length=8,
    )
    planned_attempt_count: Literal[24] = 24
    provider_call_count: int = Field(ge=0, le=24)
    successful_call_count: int = Field(ge=0, le=24)
    provider_error_count: int = Field(ge=0, le=8)
    skipped_sequence_attempt_count: int = Field(ge=0, le=16)
    skipped_experiment_attempt_count: int = Field(ge=0, le=23)
    estimated_cost_microusd: int = Field(ge=0, le=4992)
    live_provider_called: bool
    execution_completed: Literal[True] = True

    @model_validator(mode="after")
    def validate_accountability(self) -> DiagnosticExecutionRecordSet:
        if [item.attempt_index for item in self.attempts] != list(range(24)):
            raise ValueError("diagnostic attempt indices must be contiguous")
        if len({item.sequence_id for item in self.sequences}) != 8:
            raise ValueError("diagnostic records require eight unique sequences")
        observed_provider_calls = sum(item.provider_call_made for item in self.attempts)
        observed_successes = sum(
            item.status is DiagnosticExecutionAttemptStatus.SUCCEEDED for item in self.attempts
        )
        observed_errors = sum(
            item.status is DiagnosticExecutionAttemptStatus.PROVIDER_ERROR for item in self.attempts
        )
        observed_sequence_skips = sum(
            item.status is DiagnosticExecutionAttemptStatus.SKIPPED_SEQUENCE
            for item in self.attempts
        )
        observed_experiment_skips = sum(
            item.status is DiagnosticExecutionAttemptStatus.SKIPPED_EXPERIMENT
            for item in self.attempts
        )
        observed_cost = sum(item.estimated_cost_microusd for item in self.attempts)
        expected = (
            observed_provider_calls,
            observed_successes,
            observed_errors,
            observed_sequence_skips,
            observed_experiment_skips,
            observed_cost,
            observed_provider_calls > 0,
        )
        actual = (
            self.provider_call_count,
            self.successful_call_count,
            self.provider_error_count,
            self.skipped_sequence_attempt_count,
            self.skipped_experiment_attempt_count,
            self.estimated_cost_microusd,
            self.live_provider_called,
        )
        if actual != expected:
            raise ValueError("diagnostic execution aggregate counts are inconsistent")
        return self


class DiagnosticExecutionReport(BaseModel):
    """Public bounded outcome for the diagnostic experiment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["batch-06-diagnostic-execution-auth-v1"]
    status: Literal["completed"] = "completed"
    planned_sequence_count: Literal[8] = 8
    planned_attempt_count: Literal[24] = 24
    provider_call_count: int = Field(ge=0, le=24)
    completed_sequence_count: int = Field(ge=0, le=8)
    request_rejected_sequence_count: int = Field(ge=0, le=8)
    experiment_stopped_sequence_count: int = Field(ge=0, le=1)
    not_started_sequence_count: int = Field(ge=0, le=7)
    successful_call_count: int = Field(ge=0, le=24)
    provider_error_count: int = Field(ge=0, le=8)
    skipped_attempt_count: int = Field(ge=0, le=23)
    estimated_cost_microusd: int = Field(ge=0, le=4992)
    attempt_budget_respected: Literal[True] = True
    cost_budget_respected: Literal[True] = True
    protected_outputs_retained_locally: bool
    protected_failure_diagnostics_boundary_configured: Literal[True] = True
    live_provider_called: bool
    execution_completed: Literal[True] = True
    held_out_executed: Literal[False] = False
    full_benchmark_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False


class DiagnosticExecutionManifest(BaseModel):
    """Hash manifest for persisted diagnostic execution evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["batch-06-diagnostic-execution-auth-v1"]
    authorization_sha256: str
    runtime_policy_sha256: str
    review_manifest_sha256: str
    dry_run_report_sha256: str
    journal_sha256: str
    run_records_sha256: str
    report_sha256: str
    protected_raw_outputs_path: str
    protected_failure_diagnostics_path: str
    live_provider_called: bool
    execution_completed: Literal[True] = True

    @field_validator(
        "authorization_sha256",
        "runtime_policy_sha256",
        "review_manifest_sha256",
        "dry_run_report_sha256",
        "journal_sha256",
        "run_records_sha256",
        "report_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic execution manifest requires lowercase SHA-256")
        return value


class DiagnosticExecutionSummary(BaseModel):
    """Metadata-safe CLI summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "live-preflight", "run", "verify"]
    authorization_id: str
    authorization_status: DiagnosticExecutionAuthorizationStatus
    planned_attempt_count: Literal[24] = 24
    provider_call_count: int = Field(ge=0, le=24)
    execution_completed: bool
    live_provider_called: bool
    credential_checked: bool
    provider_calls_permitted: bool
    execution_command_available: Literal[True] = True
    resume_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
