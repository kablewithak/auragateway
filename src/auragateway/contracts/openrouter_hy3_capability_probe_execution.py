"""Typed one-time execution and terminal-closeout contracts for the Hy3 probe."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from auragateway.contracts.openrouter import (
    OpenRouterCachedInputTelemetry,
    OpenRouterCacheObservation,
    OpenRouterInvocationResult,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ATTEMPT_ID_PATTERN = re.compile(r"^openrouter-hy3-capability-probe-v1-(cold|warm)-attempt-[12]$")


class OpenRouterProbeLogicalCallRole(StrEnum):
    """The two frozen logical calls in execution order."""

    COLD_PROBE = "cold_probe"
    WARM_PROBE = "warm_probe"


class OpenRouterProbeRawResponseKind(StrEnum):
    """HTTP response surfaces retained before typed provider interpretation."""

    COMPLETION = "completion"
    GENERATION_METADATA = "generation_metadata"


class OpenRouterProbeJournalEventType(StrEnum):
    """Append-only execution events."""

    EXECUTION_STARTED = "execution_started"
    ATTEMPT_STARTED = "attempt_started"
    ATTEMPT_TRANSIENT_FAILURE = "attempt_transient_failure"
    ATTEMPT_TERMINAL_FAILURE = "attempt_terminal_failure"
    OBSERVATION_RETAINED = "observation_retained"
    EXECUTION_CLOSED = "execution_closed"


class OpenRouterProbeTerminalOutcome(StrEnum):
    """Execution-specific terminal outcomes for the one-time probe."""

    CLOSED_TRANSIENT_BUDGET_EXHAUSTED = "closed_transient_budget_exhausted"
    CLOSED_TERMINAL_PROVIDER_FAILURE = "closed_terminal_provider_failure"
    CLOSED_OBSERVATION_INVALID = "closed_observation_invalid"
    CLOSED_ROUTE_UNIDENTIFIABLE = "closed_route_unidentifiable"
    CLOSED_TELEMETRY_UNAVAILABLE = "closed_telemetry_unavailable"
    CLOSED_NO_CACHE_USE = "closed_no_cache_use"
    CLOSED_INTERRUPTED_EXECUTION = "closed_interrupted_execution"
    PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW = "promoted_to_pilot_authorization_review"


class OpenRouterProbeExecutionPaths(BaseModel):
    """Committed design files and protected runtime files for execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_policy_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-execution-v1/execution_policy.json"
    ]
    execution_report_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-execution-v1/execution_report.json"
    ]
    execution_manifest_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-execution-v1/execution_manifest.json"
    ]
    terminal_receipt_path: Literal[
        ".local/benchmark/openrouter-hy3-capability-probe-v1/terminal_receipt.json"
    ]


class OpenRouterProbeExecutionPolicy(BaseModel):
    """Additive execution policy that refines the historical abstract model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["openrouter-hy3-capability-probe-execution-policy-v1"]
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    confirmation_phrase: Literal["EXECUTE_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE"]
    logical_call_roles: tuple[
        Literal["cold_probe"],
        Literal["warm_probe"],
    ]
    expected_outputs: tuple[
        Literal["COLD-PROBE-ACK"],
        Literal["WARM-PROBE-ACK"],
    ]
    maximum_total_inference_attempts: Literal[4] = 4
    maximum_attempts_per_logical_call: Literal[2] = 2
    maximum_transient_replacements_per_logical_call: Literal[1] = 1
    transient_http_statuses: tuple[Literal[429], Literal[502], Literal[524], Literal[529]]
    exact_trimmed_output_required: Literal[True] = True
    one_raw_record_per_http_response: Literal[True] = True
    completion_must_be_retained_before_generation_lookup: Literal[True] = True
    successful_completion_retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    rerun_permitted: Literal[False] = False
    incomplete_journal_closes_without_network: Literal[True] = True
    interruption_terminal_outcome: Literal["closed_interrupted_execution"]
    numeric_measurement_channel_fields: tuple[
        Literal["cached_tokens"],
        Literal["cache_write_tokens"],
        Literal["native_tokens_cached"],
    ]
    cold_positive_read_classification: Literal["cold_state_contamination"]
    cold_positive_read_alone_permits_promotion: Literal[False] = False
    controlled_positive_cache_use_requires: tuple[
        Literal["cold_cache_write_positive"],
        Literal["warm_cache_read_positive"],
    ]
    committed_authorization_mutation_permitted: Literal[False] = False
    authorization_consumption_location: Literal["protected_local_terminal_receipt"]
    public_raw_payload_permitted: Literal[False] = False
    paths: OpenRouterProbeExecutionPaths

    @model_validator(mode="after")
    def validate_policy(self) -> OpenRouterProbeExecutionPolicy:
        if self.logical_call_roles != ("cold_probe", "warm_probe"):
            raise ValueError("execution roles must remain cold then warm")
        if self.expected_outputs != ("COLD-PROBE-ACK", "WARM-PROBE-ACK"):
            raise ValueError("execution outputs must remain exact")
        if self.transient_http_statuses != (429, 502, 524, 529):
            raise ValueError("execution transient statuses must remain exact")
        if self.controlled_positive_cache_use_requires != (
            "cold_cache_write_positive",
            "warm_cache_read_positive",
        ):
            raise ValueError("execution promotion evidence must remain exact")
        return self


class OpenRouterProbeExecutionReport(BaseModel):
    """Public inactive-at-rest report for the execution implementation slice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["openrouter-hy3-capability-probe-execution-policy-v1"]
    execution_command_available: Literal[True] = True
    live_provider_call_performed: Literal[False] = False
    historical_hash_bound_files_modified: Literal[False] = False
    recording_transport_added: Literal[True] = True
    interruption_closeout_added: Literal[True] = True
    exact_output_validation_added: Literal[True] = True
    stricter_promotion_rule_added: Literal[True] = True
    committed_authorization_remains_immutable: Literal[True] = True
    protected_terminal_receipt_required: Literal[True] = True
    sanitized_closeout_requires_separate_review: Literal[True] = True
    next_gate: Literal["merge_execution_runner_then_execute_once"]


class OpenRouterProbeExecutionManifest(BaseModel):
    """Integrity manifest for the additive execution implementation package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["openrouter-hy3-capability-probe-execution-policy-v1"]
    execution_policy_sha256: str
    execution_report_sha256: str
    contract_sha256: str
    recording_transport_sha256: str
    execution_runner_sha256: str
    adr_sha256: str
    benchmark_report_sha256: str
    live_provider_call_performed: Literal[False] = False

    @field_validator(
        "execution_policy_sha256",
        "execution_report_sha256",
        "contract_sha256",
        "recording_transport_sha256",
        "execution_runner_sha256",
        "adr_sha256",
        "benchmark_report_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution manifest requires lowercase SHA-256")
        return value


class OpenRouterProbeAttemptContext(BaseModel):
    """Immutable identity supplied to one transport attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    attempt_id: str
    logical_call_role: OpenRouterProbeLogicalCallRole
    logical_call_index: int = Field(ge=0, le=1)
    attempt_number: int = Field(ge=1, le=2)

    @field_validator("attempt_id")
    @classmethod
    def validate_attempt_id(cls, value: str) -> str:
        if _ATTEMPT_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("attempt ID does not match the frozen execution format")
        return value

    @model_validator(mode="after")
    def validate_role_index(self) -> OpenRouterProbeAttemptContext:
        expected_index = (
            0 if self.logical_call_role is OpenRouterProbeLogicalCallRole.COLD_PROBE else 1
        )
        expected_fragment = "cold" if expected_index == 0 else "warm"
        if self.logical_call_index != expected_index:
            raise ValueError("logical call role and index do not reconcile")
        if f"-{expected_fragment}-" not in self.attempt_id:
            raise ValueError("attempt ID and logical call role do not reconcile")
        return self


class OpenRouterProbeRawResponseRecord(BaseModel):
    """Protected complete HTTP response retained before provider parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    attempt_id: str
    logical_call_role: OpenRouterProbeLogicalCallRole
    attempt_number: int = Field(ge=1, le=2)
    response_sequence: int = Field(ge=1, le=2)
    response_kind: OpenRouterProbeRawResponseKind
    received_at: datetime
    http_status: int = Field(ge=100, le=599)
    content_type: str | None = Field(default=None, max_length=200)
    body_sha256: str
    body_bytes: int = Field(ge=0, le=2_000_000)
    body_representation: Literal["json", "utf8", "base64"]
    json_payload: JsonValue | None = None
    body_utf8: str | None = None
    body_base64: str | None = None
    protected_local_only: Literal[True] = True
    public_release_permitted: Literal[False] = False

    @field_validator("attempt_id")
    @classmethod
    def validate_attempt_id(cls, value: str) -> str:
        if _ATTEMPT_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("raw response attempt ID is invalid")
        return value

    @field_validator("body_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("raw response requires lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_body_representation(self) -> OpenRouterProbeRawResponseRecord:
        if self.body_representation == "json":
            if self.body_utf8 is not None or self.body_base64 is not None:
                raise ValueError("JSON response cannot include alternate body representations")
        elif self.body_representation == "utf8":
            if (
                self.body_utf8 is None
                or self.json_payload is not None
                or self.body_base64 is not None
            ):
                raise ValueError("UTF-8 response body representation is inconsistent")
        elif (
            self.body_base64 is None or self.json_payload is not None or self.body_utf8 is not None
        ):
            raise ValueError("base64 response body representation is inconsistent")
        return self


class OpenRouterProbeParsedObservationRecord(BaseModel):
    """Protected typed observation retained after adapter and output validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    attempt_id: str
    logical_call_role: OpenRouterProbeLogicalCallRole
    attempt_number: int = Field(ge=1, le=2)
    retained_at: datetime
    result: OpenRouterInvocationResult
    telemetry: OpenRouterCachedInputTelemetry
    observation: OpenRouterCacheObservation
    expected_output: Literal["COLD-PROBE-ACK", "WARM-PROBE-ACK"]
    exact_trimmed_output_valid: bool
    numeric_measurement_channel_observed: bool
    cold_positive_cache_read_contamination: bool
    controlled_positive_cache_use_observed: bool
    protected_local_only: Literal[True] = True
    public_release_permitted: Literal[False] = False

    @field_validator("attempt_id")
    @classmethod
    def validate_attempt_id(cls, value: str) -> str:
        if _ATTEMPT_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("parsed observation attempt ID is invalid")
        return value

    @model_validator(mode="after")
    def validate_output_binding(self) -> OpenRouterProbeParsedObservationRecord:
        expected_role = (
            OpenRouterProbeLogicalCallRole.COLD_PROBE
            if self.expected_output == "COLD-PROBE-ACK"
            else OpenRouterProbeLogicalCallRole.WARM_PROBE
        )
        if self.logical_call_role is not expected_role:
            raise ValueError("expected output does not match logical call role")
        return self


class OpenRouterProbeJournalRecord(BaseModel):
    """One metadata-safe append-only execution journal event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    event_index: int = Field(ge=1)
    event_type: OpenRouterProbeJournalEventType
    recorded_at: datetime
    attempt_id: str | None = None
    logical_call_role: OpenRouterProbeLogicalCallRole | None = None
    attempt_number: int | None = Field(default=None, ge=1, le=2)
    total_attempt_count: int = Field(ge=0, le=4)
    provider_success_count: int = Field(ge=0, le=2)
    retained_success_count: int = Field(ge=0, le=2)
    replacement_count: int = Field(ge=0, le=2)
    safe_error_code: str | None = Field(default=None, max_length=120)
    retry_permitted: bool | None = None
    terminal_outcome: OpenRouterProbeTerminalOutcome | None = None

    @field_validator("attempt_id")
    @classmethod
    def validate_attempt_id(cls, value: str | None) -> str | None:
        if value is not None and _ATTEMPT_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("journal attempt ID is invalid")
        return value

    @model_validator(mode="after")
    def validate_event_shape(self) -> OpenRouterProbeJournalRecord:
        attempt_event = self.event_type in {
            OpenRouterProbeJournalEventType.ATTEMPT_STARTED,
            OpenRouterProbeJournalEventType.ATTEMPT_TRANSIENT_FAILURE,
            OpenRouterProbeJournalEventType.ATTEMPT_TERMINAL_FAILURE,
            OpenRouterProbeJournalEventType.OBSERVATION_RETAINED,
        }
        if attempt_event and (
            self.attempt_id is None or self.logical_call_role is None or self.attempt_number is None
        ):
            raise ValueError("attempt journal events require attempt identity")
        if self.event_type is OpenRouterProbeJournalEventType.EXECUTION_CLOSED:
            if self.terminal_outcome is None:
                raise ValueError("execution close event requires terminal outcome")
        elif self.terminal_outcome is not None:
            raise ValueError("terminal outcome is allowed only on execution close")
        return self


class OpenRouterProbeTerminalReceipt(BaseModel):
    """Protected local overlay proving one-time authorization consumption."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    terminal_outcome: OpenRouterProbeTerminalOutcome
    authorization_consumed: Literal[True] = True
    source_commit: str
    execution_started_at: datetime | None = None
    closed_at: datetime
    attempt_count: int = Field(ge=0, le=4)
    provider_success_count: int = Field(ge=0, le=2)
    retained_success_count: int = Field(ge=0, le=2)
    replacement_count: int = Field(ge=0, le=2)
    numeric_measurement_channel_observed: bool
    controlled_positive_cache_use_observed: bool
    cold_positive_cache_read_contamination: bool
    route_identity_valid: bool
    prompt_bundle_sha256: str
    preflight_receipt_sha256: str
    journal_sha256_before_close: str
    journal_bytes_before_close: int = Field(ge=0)
    raw_responses_sha256: str
    parsed_responses_sha256: str
    committed_authorization_mutated: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal[
        "sanitized_capability_closeout",
        "pilot_authorization_review",
    ]

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal receipt requires a full lowercase commit SHA")
        return value

    @field_validator(
        "prompt_bundle_sha256",
        "preflight_receipt_sha256",
        "journal_sha256_before_close",
        "raw_responses_sha256",
        "parsed_responses_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal receipt requires lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_terminal_state(self) -> OpenRouterProbeTerminalReceipt:
        promoted = (
            self.terminal_outcome
            is OpenRouterProbeTerminalOutcome.PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW
        )
        if promoted:
            if self.retained_success_count != 2:
                raise ValueError("promotion requires two retained successes")
            if not self.numeric_measurement_channel_observed:
                raise ValueError("promotion requires numeric measurement-channel evidence")
            if not self.controlled_positive_cache_use_observed:
                raise ValueError("promotion requires controlled positive cache-use evidence")
            if not self.route_identity_valid:
                raise ValueError("promotion requires valid route identity")
            if self.next_gate != "pilot_authorization_review":
                raise ValueError("promoted receipt requires pilot authorization review next")
        elif self.next_gate != "sanitized_capability_closeout":
            raise ValueError("closed receipt requires sanitized closeout next")
        if (
            self.terminal_outcome is OpenRouterProbeTerminalOutcome.CLOSED_INTERRUPTED_EXECUTION
            and self.execution_started_at is None
        ):
            raise ValueError("interrupted closeout requires an execution start timestamp")
        return self


class OpenRouterProbeExecutionSummary(BaseModel):
    """Metadata-safe command summary for execution and local verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "execute", "verify-local", "close-interrupted"]
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    execution_ready: bool
    terminal_receipt_present: bool
    authorization_consumed: bool
    terminal_outcome: OpenRouterProbeTerminalOutcome | None = None
    attempt_count: int = Field(ge=0, le=4)
    provider_success_count: int = Field(ge=0, le=2)
    retained_success_count: int = Field(ge=0, le=2)
    replacement_count: int = Field(ge=0, le=2)
    credential_accessed: bool
    network_request_count: int = Field(ge=0, le=6)
    next_gate: str


class OpenRouterProbeExecutionErrorEnvelope(BaseModel):
    """Metadata-safe execution CLI error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()
