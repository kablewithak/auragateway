"""Typed contracts for the development-only controlled benchmark smoke."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.evidence_bundle import BenchmarkCondition, RunTerminalStatus

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_PATTERN = re.compile(r"^run-[a-z0-9-]{3,160}$")
_PAIR_ID_PATTERN = re.compile(r"^pair-[a-z0-9-]{3,160}$")
_NAMESPACE_ID_PATTERN = re.compile(r"^ns-[a-z0-9-]{3,160}$")
_EPISODE_ID_PATTERN = re.compile(r"^ep-func-[0-9]{3}$")
_TRACE_ID_PATTERN = re.compile(r"^trace-[0-9a-f]{24}$")
_ATTEMPT_ID_PATTERN = re.compile(r"^attempt-[0-9a-f]{24}$")
_TERMINAL_ID_PATTERN = re.compile(r"^terminal-[0-9a-f]{24}$")


class SmokeAttemptOutcome(StrEnum):
    """Scripted provider outcomes used to exercise runner regulation."""

    COMPLETED = "completed"
    DEFINITE_RETRYABLE_FAILURE = "definite_retryable_failure"
    AMBIGUOUS_RESPONSE = "ambiguous_response"
    NONRETRYABLE_FAILURE = "nonretryable_failure"


class SmokeResponseCertainty(StrEnum):
    """Provider response certainty retained by the smoke runner."""

    SUCCESS = "success"
    DEFINITE_FAILURE = "definite_failure"
    AMBIGUOUS = "ambiguous"


class SmokeFailureCode(StrEnum):
    """Bounded terminal reasons emitted by the controlled smoke."""

    AMBIGUOUS_PROVIDER_RESPONSE = "AMBIGUOUS_PROVIDER_RESPONSE"
    NONRETRYABLE_PROVIDER_FAILURE = "NONRETRYABLE_PROVIDER_FAILURE"
    RETRY_BUDGET_EXHAUSTED = "RETRY_BUDGET_EXHAUSTED"
    ATTEMPT_BUDGET_EXHAUSTED = "ATTEMPT_BUDGET_EXHAUSTED"
    COST_BUDGET_EXHAUSTED = "COST_BUDGET_EXHAUSTED"
    SCRIPT_INCOMPLETE = "SCRIPT_INCOMPLETE"


class ControlledSmokeAuthorization(BaseModel):
    """Explicit authorization for one synthetic development-only A/B/C smoke."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    smoke_id: str
    authorization_id: str
    execution_manifest_sha256: str
    gate10_manifest_sha256: str
    gate9_manifest_sha256: str
    planned_run_ledger_sha256: str
    functional_episode_set_sha256: str
    allowed_episode_ids: tuple[str, ...] = Field(min_length=1, max_length=1)
    allowed_run_ids: tuple[str, ...] = Field(min_length=3, max_length=3)
    allowed_conditions: tuple[BenchmarkCondition, ...] = Field(min_length=3, max_length=3)
    maximum_run_count: Literal[3] = 3
    maximum_total_attempt_count: int = Field(ge=3, le=24)
    maximum_total_cost_microusd: int = Field(ge=1)
    turns_per_run: Literal[4] = 4
    development_only: Literal[True] = True
    scripted_execution_only: Literal[True] = True
    live_provider_execution_permitted: Literal[False] = False
    held_out_execution_permitted: Literal[False] = False
    full_benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False

    @field_validator(
        "execution_manifest_sha256",
        "gate10_manifest_sha256",
        "gate9_manifest_sha256",
        "planned_run_ledger_sha256",
        "functional_episode_set_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("controlled-smoke identities must be lowercase SHA-256")
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
    def validate_scope(self) -> ControlledSmokeAuthorization:
        if set(self.allowed_conditions) != set(BenchmarkCondition):
            raise ValueError("controlled smoke must authorize conditions A, B, and C exactly")
        if self.maximum_run_count != len(self.allowed_run_ids):
            raise ValueError("maximum_run_count must match the authorized run set")
        return self


class ScriptedAttemptFixture(BaseModel):
    """One metadata-only scripted provider attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_index: int = Field(ge=1, le=4)
    attempt_index: int = Field(ge=1, le=2)
    outcome: SmokeAttemptOutcome
    response_certainty: SmokeResponseCertainty
    retryable: bool
    logical_request_sha256: str
    provider_request_id_sha256: str
    output_sha256: str | None = None
    provider_error_code: str | None = None
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    estimated_cost_microusd: int = Field(ge=0)

    @field_validator(
        "logical_request_sha256",
        "provider_request_id_sha256",
        "output_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("attempt digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_outcome(self) -> ScriptedAttemptFixture:
        if self.outcome is SmokeAttemptOutcome.COMPLETED:
            if self.response_certainty is not SmokeResponseCertainty.SUCCESS:
                raise ValueError("completed attempts require success certainty")
            if self.retryable or self.provider_error_code is not None:
                raise ValueError("completed attempts cannot be retryable or carry an error")
            if self.output_sha256 is None or self.output_tokens == 0:
                raise ValueError("completed attempts require output evidence")
        elif self.outcome is SmokeAttemptOutcome.DEFINITE_RETRYABLE_FAILURE:
            if self.response_certainty is not SmokeResponseCertainty.DEFINITE_FAILURE:
                raise ValueError("retryable failure requires definite-failure certainty")
            if not self.retryable or self.provider_error_code is None:
                raise ValueError("retryable failure requires an error code and retryable=true")
            if self.output_sha256 is not None or self.output_tokens != 0:
                raise ValueError("failed attempts cannot claim output evidence")
        elif self.outcome is SmokeAttemptOutcome.AMBIGUOUS_RESPONSE:
            if self.response_certainty is not SmokeResponseCertainty.AMBIGUOUS:
                raise ValueError("ambiguous outcome requires ambiguous certainty")
            if self.retryable or self.provider_error_code is None:
                raise ValueError("ambiguous responses must block retry and retain an error code")
            if self.output_sha256 is not None:
                raise ValueError("ambiguous responses cannot claim output evidence")
        else:
            if self.response_certainty is not SmokeResponseCertainty.DEFINITE_FAILURE:
                raise ValueError("nonretryable failure requires definite-failure certainty")
            if self.retryable or self.provider_error_code is None:
                raise ValueError("nonretryable failure requires retryable=false and an error code")
            if self.output_sha256 is not None:
                raise ValueError("failed attempts cannot claim output evidence")
        return self


class ScriptedRunScenario(BaseModel):
    """Ordered scripted attempts for one authorized trajectory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    expected_terminal_status: RunTerminalStatus
    attempts: tuple[ScriptedAttemptFixture, ...] = Field(min_length=1, max_length=8)

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if _RUN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("scenario run_id must use run-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_attempt_order(self) -> ScriptedRunScenario:
        previous_turn = 0
        expected_attempt_by_turn: dict[int, int] = {}
        logical_requests: dict[int, str] = {}
        for attempt in self.attempts:
            if attempt.turn_index < previous_turn:
                raise ValueError("scripted attempts must be ordered by turn")
            expected = expected_attempt_by_turn.get(attempt.turn_index, 1)
            if attempt.attempt_index != expected:
                raise ValueError("attempt indexes must be contiguous within each turn")
            expected_attempt_by_turn[attempt.turn_index] = expected + 1
            previous = logical_requests.setdefault(
                attempt.turn_index, attempt.logical_request_sha256
            )
            if previous != attempt.logical_request_sha256:
                raise ValueError("retries must preserve the logical-request fingerprint")
            logical_requests[attempt.turn_index] = previous
            previous_turn = attempt.turn_index
        return self


class ScriptedSmokeFixtureSet(BaseModel):
    """Complete scripted fixture set for the three-condition smoke."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    scenarios: tuple[ScriptedRunScenario, ...] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_scenarios(self) -> ScriptedSmokeFixtureSet:
        run_ids = [item.run_id for item in self.scenarios]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("scripted scenario run IDs must be unique")
        return self


class SmokePlanRunProjection(BaseModel):
    """Fields used from the already-validated Gate 9 plan ledger."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    schedule_index: int = Field(ge=0)
    run_id: str
    comparison_pair_id: str
    workload: str
    episode_id: str
    replication_id: str
    condition_id: BenchmarkCondition
    cache_namespace_id: str
    turn_count: int = Field(ge=1)
    maximum_request_attempt_count: int = Field(ge=1)

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if _RUN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("planned run ID must use run-<slug> form")
        return value

    @field_validator("comparison_pair_id")
    @classmethod
    def validate_pair_id(cls, value: str) -> str:
        if _PAIR_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("comparison pair ID must use pair-<slug> form")
        return value

    @field_validator("cache_namespace_id")
    @classmethod
    def validate_namespace_id(cls, value: str) -> str:
        if _NAMESPACE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("cache namespace ID must use ns-<slug> form")
        return value


class SmokePlanLedgerProjection(BaseModel):
    """Projection of the frozen Gate 9 ledger after its file hash is verified."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    plan_id: str
    runs: tuple[SmokePlanRunProjection, ...] = Field(min_length=3)


class EpisodeSplitProjection(BaseModel):
    """Only the episode identity and protected split used by the smoke gate."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    episode_id: str
    evaluation_split: Literal["development", "held_out"]


class EpisodeSetProjection(BaseModel):
    """Projection of the frozen functional episode set."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    episodes: tuple[EpisodeSplitProjection, ...] = Field(min_length=1)


class Gate9ManifestProjection(BaseModel):
    """Fields required to bind the smoke to the planned-run ledger."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    plan_path: str
    plan_sha256: str
    planning_ready: bool
    measured_execution_ready: bool
    execution_enabled: bool
    measured_execution_permitted: bool

    @field_validator("plan_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("Gate 9 plan digest must be lowercase SHA-256")
        return value


class Gate10ManifestProjection(BaseModel):
    """Fields required to bind the smoke to the frozen execution manifest."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    gate9_manifest_path: str
    gate9_manifest_sha256: str
    execution_manifest_path: str
    execution_manifest_file_sha256: str
    execution_manifest_canonical_sha256: str
    gate_10_passed: bool
    execution_enabled: bool
    measured_execution_permitted: bool

    @field_validator(
        "gate9_manifest_sha256",
        "execution_manifest_file_sha256",
        "execution_manifest_canonical_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("Gate 10 digests must be lowercase SHA-256")
        return value


class SmokeAttemptRecord(BaseModel):
    """Immutable metadata-only attempt evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str
    trace_id: str
    run_id: str
    turn_index: int = Field(ge=1, le=4)
    attempt_index: int = Field(ge=1, le=2)
    outcome: SmokeAttemptOutcome
    response_certainty: SmokeResponseCertainty
    retry_authorized: bool
    logical_request_sha256: str
    provider_request_id_sha256: str
    output_sha256: str | None = None
    provider_error_code: str | None = None
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    estimated_cost_microusd: int = Field(ge=0)

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


class SmokeTerminalRecord(BaseModel):
    """One terminal trajectory record retained by the smoke ledger."""

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
    failure_code: SmokeFailureCode | None = None

    @field_validator("terminal_record_id")
    @classmethod
    def validate_terminal_id(cls, value: str) -> str:
        if _TERMINAL_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal_record_id must use terminal-<24 hex> form")
        return value

    @model_validator(mode="after")
    def validate_terminal(self) -> SmokeTerminalRecord:
        if self.attempt_count != len(self.attempt_ids):
            raise ValueError("terminal attempt_count must match attempt_ids")
        if self.terminal_status is RunTerminalStatus.COMPLETED:
            if self.completed_turn_count != 4 or self.failure_code is not None:
                raise ValueError("completed smoke runs require four turns and no failure code")
        elif self.failure_code is None:
            raise ValueError("non-completed smoke runs require a bounded failure code")
        return self


class SmokeRunRecordSet(BaseModel):
    """Complete append-preserving evidence for the three-run controlled smoke."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    smoke_id: str
    authorization_id: str
    execution_manifest_sha256: str
    terminal_records: tuple[SmokeTerminalRecord, ...] = Field(min_length=1, max_length=3)
    attempt_records: tuple[SmokeAttemptRecord, ...] = Field(min_length=1, max_length=24)
    total_attempt_count: int
    total_estimated_cost_microusd: int
    live_provider_called: Literal[False] = False
    held_out_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_reconciliation(self) -> SmokeRunRecordSet:
        terminal_ids = [item.terminal_record_id for item in self.terminal_records]
        if len(terminal_ids) != len(set(terminal_ids)):
            raise ValueError("terminal record IDs must be unique")
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
            raise ValueError("total smoke cost must reconcile with retained attempts")
        retained = set(attempt_ids)
        for terminal in self.terminal_records:
            if not set(terminal.attempt_ids) <= retained:
                raise ValueError("terminal records may reference only retained attempts")
        return self


class TerminalStatusCount(BaseModel):
    """Stable terminal-status aggregate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    terminal_status: RunTerminalStatus
    count: int = Field(ge=0)


class ControlledSmokeReport(BaseModel):
    """Metadata-only Gate 11 controlled-smoke report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    smoke_id: str
    authorization_id: str
    execution_manifest_sha256: str
    selected_episode_ids: tuple[str, ...]
    selected_run_count: int
    terminal_record_count: int
    attempt_record_count: int
    retry_authorized_count: int
    ambiguous_retry_blocked_count: int
    terminal_status_counts: tuple[TerminalStatusCount, ...]
    expected_terminal_statuses_matched: bool
    attempt_budget_respected: bool
    cost_budget_respected: bool
    resume_preserved_terminal_records: bool
    development_only: bool
    live_provider_called: bool
    held_out_executed: bool
    full_benchmark_executed: bool
    benchmark_claims_permitted: bool
    smoke_passed: bool
    measured_execution_permitted: Literal[False] = False


class Gate11SmokeManifest(BaseModel):
    """Hash-bound inventory for controlled-smoke evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-11-controlled-smoke-manifest-v1"
    authorization_path: str
    authorization_sha256: str
    fixture_path: str
    fixture_sha256: str
    run_records_path: str
    run_records_sha256: str
    report_path: str
    report_sha256: str
    gate10_manifest_sha256: str
    execution_manifest_sha256: str
    planned_run_ledger_sha256: str
    functional_episode_set_sha256: str
    smoke_passed: bool
    live_provider_called: Literal[False] = False
    held_out_executed: Literal[False] = False
    full_benchmark_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @field_validator(
        "authorization_sha256",
        "fixture_sha256",
        "run_records_sha256",
        "report_sha256",
        "gate10_manifest_sha256",
        "execution_manifest_sha256",
        "planned_run_ledger_sha256",
        "functional_episode_set_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("Gate 11 manifest digests must be lowercase SHA-256")
        return value


class ControlledSmokeSummary(BaseModel):
    """Safe CLI summary for controlled-smoke actions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "run", "resume", "verify"]
    authorization_id: str
    smoke_passed: bool
    terminal_record_count: int
    attempt_record_count: int
    reused_terminal_record_count: int
    live_provider_called: Literal[False] = False
    held_out_executed: Literal[False] = False
    full_benchmark_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
