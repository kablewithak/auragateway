"""Typed contracts for the bounded live development benchmark batch."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.evidence_bundle import BenchmarkCondition, RunTerminalStatus
from auragateway.contracts.provider import ProviderInvocationStatus, ProviderName

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_PATTERN = re.compile(r"^run-[a-z0-9-]{3,160}$")
_PAIR_ID_PATTERN = re.compile(r"^pair-[a-z0-9-]{3,160}$")
_NAMESPACE_ID_PATTERN = re.compile(r"^ns-[a-z0-9-]{3,160}$")
_EPISODE_ID_PATTERN = re.compile(r"^ep-func-[0-9]{3}$")
_TRACE_ID_PATTERN = re.compile(r"^trace-[0-9a-f]{24}$")
_ATTEMPT_ID_PATTERN = re.compile(r"^attempt-[0-9a-f]{24}$")
_TERMINAL_ID_PATTERN = re.compile(r"^terminal-[0-9a-f]{24}$")


class LiveResponseCertainty(StrEnum):
    """Whether one provider attempt has a safe retry interpretation."""

    SUCCESS = "success"
    DEFINITE_FAILURE = "definite_failure"
    AMBIGUOUS = "ambiguous"


class LiveExecutionFailureCode(StrEnum):
    """Bounded failure reasons retained by the live development runner."""

    AMBIGUOUS_PROVIDER_RESPONSE = "AMBIGUOUS_PROVIDER_RESPONSE"
    NONRETRYABLE_PROVIDER_FAILURE = "NONRETRYABLE_PROVIDER_FAILURE"
    RETRY_BUDGET_EXHAUSTED = "RETRY_BUDGET_EXHAUSTED"
    ATTEMPT_BUDGET_EXHAUSTED = "ATTEMPT_BUDGET_EXHAUSTED"
    INPUT_BUDGET_EXHAUSTED = "INPUT_BUDGET_EXHAUSTED"
    COST_BUDGET_EXHAUSTED = "COST_BUDGET_EXHAUSTED"
    STRUCTURED_OUTPUT_INVALID = "STRUCTURED_OUTPUT_INVALID"
    CITATION_SCOPE_INVALID = "CITATION_SCOPE_INVALID"
    PROTECTED_OUTPUT_RETENTION_FAILED = "PROTECTED_OUTPUT_RETENTION_FAILED"
    RESUME_UNCERTAIN_PROVIDER_STATE = "RESUME_UNCERTAIN_PROVIDER_STATE"
    BATCH_HALTED_PROVIDER_FAILURE = "BATCH_HALTED_PROVIDER_FAILURE"


class LiveDevelopmentAuthorization(BaseModel):
    """Explicit authorization for one bounded live development-only A/B/C batch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    batch_id: str
    authorization_id: str
    execution_manifest_sha256: str
    gate10_manifest_sha256: str
    gate9_manifest_sha256: str
    planned_run_ledger_sha256: str
    functional_episode_set_sha256: str
    compiler_spec_sha256: str
    source_manifest_sha256: str
    pricing_schedule_sha256: str
    allowed_episode_ids: tuple[str, ...] = Field(min_length=1, max_length=2)
    allowed_run_ids: tuple[str, ...] = Field(min_length=3, max_length=6)
    allowed_conditions: tuple[BenchmarkCondition, ...] = Field(min_length=3, max_length=3)
    maximum_run_count: int = Field(ge=3, le=6)
    maximum_total_attempt_count: int = Field(ge=3, le=24)
    maximum_total_cost_microusd: int = Field(ge=1)
    maximum_input_tokens_per_attempt: int = Field(ge=1, le=3000)
    output_token_budget: int = Field(ge=1, le=256)
    timeout_seconds: float = Field(gt=0, le=120)
    turns_per_run: Literal[4] = 4
    provider: ProviderName = ProviderName.GROQ
    provider_model_alias: Literal["groq-gpt-oss-20b"] = "groq-gpt-oss-20b"
    provider_adapter_version: Literal["groq-chat-completions-v1"] = "groq-chat-completions-v1"
    runtime_prompt_profile: Literal["development-live-compact-v1"] = "development-live-compact-v1"
    retrieval_execution_mode: Literal["frozen-required-source-injection-v1"] = (
        "frozen-required-source-injection-v1"
    )
    development_only: Literal[True] = True
    live_provider_execution_permitted: Literal[True] = True
    held_out_execution_permitted: Literal[False] = False
    full_benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: ProviderName) -> ProviderName:
        if value is not ProviderName.GROQ:
            raise ValueError("live development currently authorizes Groq only")
        return value

    @field_validator(
        "execution_manifest_sha256",
        "gate10_manifest_sha256",
        "gate9_manifest_sha256",
        "planned_run_ledger_sha256",
        "functional_episode_set_sha256",
        "compiler_spec_sha256",
        "source_manifest_sha256",
        "pricing_schedule_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("live-development identities must be lowercase SHA-256")
        return value

    @field_validator("allowed_episode_ids")
    @classmethod
    def validate_episode_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("allowed episode IDs must be unique")
        if any(_EPISODE_ID_PATTERN.fullmatch(item) is None for item in value):
            raise ValueError("allowed episode IDs must match ep-func-<NNN>")
        return value

    @field_validator("allowed_run_ids")
    @classmethod
    def validate_run_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("allowed run IDs must be unique")
        if any(_RUN_ID_PATTERN.fullmatch(item) is None for item in value):
            raise ValueError("allowed run IDs must use run-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_scope(self) -> LiveDevelopmentAuthorization:
        if set(self.allowed_conditions) != set(BenchmarkCondition):
            raise ValueError("live development must authorize conditions A, B, and C exactly")
        if self.maximum_run_count != len(self.allowed_run_ids):
            raise ValueError("maximum_run_count must match the authorized run set")
        if len(self.allowed_run_ids) != len(self.allowed_episode_ids) * 3:
            raise ValueError("every authorized episode requires one A/B/C run triplet")
        if self.maximum_total_attempt_count < self.maximum_run_count * self.turns_per_run:
            raise ValueError("attempt budget must permit one attempt for every authorized turn")
        return self


class LiveAttemptRecord(BaseModel):
    """One public metadata-only provider attempt record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str
    trace_id: str
    run_id: str
    condition_id: BenchmarkCondition
    turn_index: int = Field(ge=1, le=4)
    attempt_index: int = Field(ge=1, le=2)
    provider: ProviderName
    model_alias: str
    route_reason: Literal["benchmark_control", "session_start", "warm_cache_affinity"]
    provider_status: ProviderInvocationStatus
    response_certainty: LiveResponseCertainty
    retry_authorized: bool
    logical_request_sha256: str
    provider_request_id_sha256: str
    static_prefix_fingerprint: str
    prefix_hmac_key_id: str = Field(min_length=1, max_length=100)
    system_prompt_sha256: str
    user_prompt_sha256: str
    prompt_byte_count: int = Field(gt=0)
    output_sha256: str | None = None
    provider_error_code: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    uncached_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_duration_ms: int | None = Field(default=None, ge=0)
    estimated_cost_microusd: int = Field(ge=0)
    protected_output_retained: bool = False
    structured_output_valid: bool = False
    citation_scope_valid: bool | None = None
    decision: str | None = None
    citation_ids: tuple[str, ...] = ()

    @field_validator("attempt_id")
    @classmethod
    def validate_attempt_id(cls, value: str) -> str:
        if _ATTEMPT_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("attempt_id must use attempt-<24 hex> form")
        return value

    @field_validator("trace_id")
    @classmethod
    def validate_trace_id(cls, value: str) -> str:
        if _TRACE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trace_id must use trace-<24 hex> form")
        return value

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if _RUN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("run_id must use run-<slug> form")
        return value

    @field_validator(
        "logical_request_sha256",
        "provider_request_id_sha256",
        "static_prefix_fingerprint",
        "system_prompt_sha256",
        "user_prompt_sha256",
        "output_sha256",
    )
    @classmethod
    def validate_hashes(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("attempt digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_attempt(self) -> LiveAttemptRecord:
        if self.provider_status is ProviderInvocationStatus.SUCCEEDED:
            if self.response_certainty is not LiveResponseCertainty.SUCCESS:
                raise ValueError("successful attempts require success certainty")
            if self.output_sha256 is None or self.provider_error_code is not None:
                raise ValueError("successful attempts require output evidence and no error code")
            if self.retry_authorized:
                raise ValueError("successful attempts cannot authorize retry")
        else:
            if self.output_sha256 is not None or self.provider_error_code is None:
                raise ValueError("failed attempts require an error code and no output digest")
            if self.structured_output_valid or self.protected_output_retained:
                raise ValueError("failed attempts cannot claim retained or validated output")
        if (
            self.cached_input_tokens is not None
            and self.input_tokens is not None
            and self.cached_input_tokens > self.input_tokens
        ):
            raise ValueError("cached input tokens cannot exceed total input tokens")
        if (
            self.uncached_input_tokens is not None
            and self.input_tokens is not None
            and self.uncached_input_tokens > self.input_tokens
        ):
            raise ValueError("uncached input tokens cannot exceed total input tokens")
        if self.structured_output_valid and not self.protected_output_retained:
            raise ValueError("validated structured output must be retained in protected storage")
        if self.citation_scope_valid is not None and not self.structured_output_valid:
            raise ValueError("citation scope is evaluated only for valid structured output")
        return self


class LiveTerminalRecord(BaseModel):
    """One terminal record for an authorized live development trajectory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    terminal_record_id: str
    trace_id: str
    run_id: str
    comparison_pair_id: str
    episode_id: str
    condition_id: BenchmarkCondition
    cache_namespace_id: str
    terminal_status: RunTerminalStatus
    completed_turn_count: int = Field(ge=0, le=4)
    attempt_count: int = Field(ge=0, le=8)
    attempt_ids: tuple[str, ...]
    structured_output_failure_count: int = Field(ge=0, le=4)
    citation_scope_failure_count: int = Field(ge=0, le=4)
    failure_code: LiveExecutionFailureCode | None = None

    @field_validator("terminal_record_id")
    @classmethod
    def validate_terminal_id(cls, value: str) -> str:
        if _TERMINAL_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal_record_id must use terminal-<24 hex> form")
        return value

    @field_validator("trace_id")
    @classmethod
    def validate_trace_id(cls, value: str) -> str:
        if _TRACE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trace_id must use trace-<24 hex> form")
        return value

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if _RUN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("run_id must use run-<slug> form")
        return value

    @field_validator("comparison_pair_id")
    @classmethod
    def validate_pair_id(cls, value: str) -> str:
        if _PAIR_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("comparison_pair_id must use pair-<slug> form")
        return value

    @field_validator("cache_namespace_id")
    @classmethod
    def validate_namespace_id(cls, value: str) -> str:
        if _NAMESPACE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("cache_namespace_id must use ns-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_terminal(self) -> LiveTerminalRecord:
        if self.attempt_count != len(self.attempt_ids):
            raise ValueError("terminal attempt_count must match attempt_ids")
        if self.terminal_status is RunTerminalStatus.COMPLETED:
            if self.completed_turn_count != 4 or self.failure_code is not None:
                raise ValueError("completed runs require four turns and no failure code")
            if self.structured_output_failure_count or self.citation_scope_failure_count:
                raise ValueError("completed runs cannot contain validation failures")
        elif self.terminal_status is RunTerminalStatus.COMPLETED_VALIDATION_FAILURE:
            if self.completed_turn_count != 4:
                raise ValueError("validation-failure completion still requires four turns")
            if self.failure_code not in {
                LiveExecutionFailureCode.STRUCTURED_OUTPUT_INVALID,
                LiveExecutionFailureCode.CITATION_SCOPE_INVALID,
            }:
                raise ValueError("validation-failure completion requires a validation failure code")
        elif self.failure_code is None:
            raise ValueError("non-completed runs require a bounded failure code")
        return self


class LiveJournalAttemptEvent(BaseModel):
    """Append-only journal event containing one public attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: Literal["attempt"] = "attempt"
    sequence_index: int = Field(ge=0)
    attempt: LiveAttemptRecord


class LiveJournalTerminalEvent(BaseModel):
    """Append-only journal event containing one terminal record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: Literal["terminal"] = "terminal"
    sequence_index: int = Field(ge=0)
    terminal: LiveTerminalRecord


LiveJournalEvent = Annotated[
    LiveJournalAttemptEvent | LiveJournalTerminalEvent,
    Field(discriminator="event_type"),
]


class LiveRunRecordSet(BaseModel):
    """Reconciled public evidence derived from the append-only journal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    batch_id: str
    authorization_id: str
    execution_manifest_sha256: str
    terminal_records: tuple[LiveTerminalRecord, ...] = Field(min_length=1, max_length=6)
    attempt_records: tuple[LiveAttemptRecord, ...] = Field(max_length=24)
    total_attempt_count: int = Field(ge=0)
    total_estimated_cost_microusd: int = Field(ge=0)
    live_provider_called: bool
    held_out_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_reconciliation(self) -> LiveRunRecordSet:
        run_ids = [item.run_id for item in self.terminal_records]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("terminal run IDs must be unique")
        attempt_ids = [item.attempt_id for item in self.attempt_records]
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("attempt IDs must be unique")
        if self.total_attempt_count != len(self.attempt_records):
            raise ValueError("total_attempt_count must match retained attempts")
        observed_cost = sum(item.estimated_cost_microusd for item in self.attempt_records)
        if self.total_estimated_cost_microusd != observed_cost:
            raise ValueError("total live-development cost must reconcile")
        retained = set(attempt_ids)
        for terminal in self.terminal_records:
            if not set(terminal.attempt_ids) <= retained:
                raise ValueError("terminal records may reference only retained attempts")
        return self


class LiveDevelopmentReport(BaseModel):
    """Public metadata-only report for the bounded live development batch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    batch_id: str
    authorization_id: str
    execution_manifest_sha256: str
    selected_episode_ids: tuple[str, ...]
    selected_run_count: int
    terminal_record_count: int
    attempt_record_count: int
    provider_call_count: int
    retry_authorized_count: int
    ambiguous_retry_blocked_count: int
    completed_run_count: int
    completed_validation_failure_count: int
    provider_error_count: int
    safety_abort_count: int
    budget_exhausted_count: int
    structured_output_failure_count: int
    citation_scope_failure_count: int
    total_estimated_cost_microusd: int
    attempt_budget_respected: bool
    cost_budget_respected: bool
    resume_reused_terminal_record_count: int
    development_only: Literal[True] = True
    live_provider_called: bool
    held_out_executed: Literal[False] = False
    full_benchmark_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    retrieval_execution_mode: Literal["frozen-required-source-injection-v1"]
    runtime_prompt_profile: Literal["development-live-compact-v1"]
    protected_outputs_retained_locally: bool
    batch_completed: bool


class LiveDevelopmentManifest(BaseModel):
    """Hash-bound public inventory for the bounded live development evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-live-development-batch-01-manifest-v1"
    authorization_path: str
    authorization_sha256: str
    journal_path: str
    journal_sha256: str
    run_records_path: str
    run_records_sha256: str
    report_path: str
    report_sha256: str
    execution_manifest_sha256: str
    planned_run_ledger_sha256: str
    functional_episode_set_sha256: str
    live_provider_called: bool
    held_out_executed: Literal[False] = False
    full_benchmark_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False

    @field_validator(
        "authorization_sha256",
        "journal_sha256",
        "run_records_sha256",
        "report_sha256",
        "execution_manifest_sha256",
        "planned_run_ledger_sha256",
        "functional_episode_set_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("live-development manifest digests must be lowercase SHA-256")
        return value


class LiveDevelopmentSummary(BaseModel):
    """Safe CLI summary for live-development actions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "run", "resume", "verify"]
    authorization_id: str
    terminal_record_count: int = Field(ge=0)
    attempt_record_count: int = Field(ge=0)
    reused_terminal_record_count: int = Field(ge=0)
    live_provider_called: bool
    held_out_executed: Literal[False] = False
    full_benchmark_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    batch_completed: bool
