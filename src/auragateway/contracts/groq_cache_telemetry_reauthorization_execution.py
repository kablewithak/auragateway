"""Typed active authorization and evidence contracts for Groq raw-wire reauthorization."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.groq_cache_telemetry_reauthorization import (
    GroqCacheTelemetryReauthorizationOutcome,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ReauthorizationBillingObservationState(StrEnum):
    """Observed state of the exact billing cached-token path."""

    FIELD_ABSENT = "field_absent"
    FIELD_NULL = "field_null"
    OBSERVED_ZERO = "observed_zero"
    OBSERVED_POSITIVE = "observed_positive"


class ReauthorizationExecutionAuthorizationStatus(StrEnum):
    """Lifecycle state of the new one-time authorization."""

    ACTIVE = "active"


class ReauthorizationAttemptStatus(StrEnum):
    """Terminal state of one planned raw-wire attempt."""

    SUCCEEDED = "succeeded"
    PROVIDER_ERROR = "provider_error"
    OBSERVATION_INVALID = "observation_invalid"
    SKIPPED = "skipped"


class ReauthorizationExecutionStatus(StrEnum):
    """Terminal state of the two-call execution."""

    COMPLETED = "completed"
    FAILED = "failed"


class ReauthorizationExecutionBinding(BaseModel):
    """One immutable activation dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=260)
    sha256: str
    protected_local: bool = False

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("activation binding paths must be repository-relative")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("activation bindings require lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_local_boundary(self) -> ReauthorizationExecutionBinding:
        if self.protected_local != self.path.startswith(".local/"):
            raise ValueError("protected_local must match the .local boundary")
        return self


class ReauthorizationExecutionEvidencePaths(BaseModel):
    """Public and protected evidence destinations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/authorization.json"
    ]
    runtime_policy_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/runtime_policy.json"
    ]
    activation_report_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/activation_report.json"
    ]
    activation_manifest_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/activation_manifest.json"
    ]
    journal_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/journal.jsonl"
    ]
    run_records_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/run_records.json"
    ]
    report_path: Literal["data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/report.json"]
    manifest_path: Literal[
        "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/manifest.json"
    ]
    protected_prompt_bundle_path: Literal[
        ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    ]
    protected_raw_responses_path: Literal[
        ".local/benchmark/groq-cache-telemetry-reauthorization-v1/raw_responses.jsonl"
    ]
    protected_parsed_responses_path: Literal[
        ".local/benchmark/groq-cache-telemetry-reauthorization-v1/parsed_responses.jsonl"
    ]


class ReauthorizationExecutionAuthorization(BaseModel):
    """Active authorization for exactly two raw-wire provider calls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-reauthorization-auth-v1"]
    status: Literal[ReauthorizationExecutionAuthorizationStatus.ACTIVE] = (
        ReauthorizationExecutionAuthorizationStatus.ACTIVE
    )
    review_id: Literal["groq-cache-telemetry-reauthorization-review-v1"]
    observation_plan_id: Literal["groq-cache-telemetry-reauthorization-observation-v1"]
    execution_id: Literal["groq-cache-telemetry-reauthorization-v1"]
    source_commit: Literal["6e76bfcda488f11b6903d8aedbe04a997af35f87"]
    bindings: tuple[ReauthorizationExecutionBinding, ...] = Field(
        min_length=6,
        max_length=6,
    )
    provider: Literal["groq"] = "groq"
    model_alias: Literal["groq-gpt-oss-20b"] = "groq-gpt-oss-20b"
    exact_model_identifier: Literal["openai/gpt-oss-20b"] = "openai/gpt-oss-20b"
    adapter_version: Literal["groq-chat-completions-v1"] = "groq-chat-completions-v1"
    telemetry_capture_version: Literal["groq-cache-telemetry-capture-v1"] = (
        "groq-cache-telemetry-capture-v1"
    )
    raw_response_capture_version: Literal["groq-raw-response-capture-v1"] = (
        "groq-raw-response-capture-v1"
    )
    observation_boundary: Literal["sdk_raw_and_parsed_same_response"]
    timeout_seconds: Literal[30] = 30
    maximum_completion_tokens: Literal[32] = 32
    maximum_provider_calls: Literal[2] = 2
    maximum_total_cost_microusd: Literal[700] = 700
    planned_maximum_cost_microusd: Literal[400] = 400
    minimum_planned_elapsed_seconds: Literal[10] = 10
    planned_attempt_count: Literal[2] = 2
    confirmation_phrase: Literal["EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE"] = (
        "EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE"
    )
    evidence_paths: ReauthorizationExecutionEvidencePaths
    one_time_execution: Literal[True] = True
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    rerun_permitted: Literal[False] = False
    provider_calls_permitted: Literal[True] = True
    credential_required: Literal[True] = True
    execution_command_available: Literal[True] = True
    reauthorization_execution_authorized: Literal[True] = True
    prior_calibration_rerun_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    execution_completed: Literal[False] = False
    next_gate: Literal["live_reauthorization_preflight"] = "live_reauthorization_preflight"

    @model_validator(mode="after")
    def validate_authorization(self) -> ReauthorizationExecutionAuthorization:
        expected = {
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-review-v1/"
            "observation_plan.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-review-v1/review.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-review-v1/"
            "dry_run_report.json",
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-review-v1/manifest.json",
            "data/evals/benchmark/cache-telemetry-calibration-review-v1/prompt_recipe.json",
            ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json",
        }
        paths = [item.path for item in self.bindings]
        if set(paths) != expected or len(paths) != len(set(paths)):
            raise ValueError("authorization requires the six exact reviewed bindings")
        if sum(item.protected_local for item in self.bindings) != 1:
            raise ValueError("authorization requires exactly one protected binding")
        if self.planned_maximum_cost_microusd > self.maximum_total_cost_microusd:
            raise ValueError("planned execution cost exceeds authorization ceiling")
        return self


class ReauthorizationExecutionRuntimePolicy(BaseModel):
    """Fail-closed trajectory policy for raw-wire execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-reauthorization-auth-v1"]
    schedule_offsets_seconds: tuple[Literal[0], Literal[10]]
    request_roles: tuple[Literal["cold_wire_probe"], Literal["warm_wire_probe"]]
    planned_cost_microusd_per_call: Literal[200] = 200
    planned_maximum_cost_microusd: Literal[400] = 400
    authorization_cost_ceiling_microusd: Literal[700] = 700
    exact_provider_request_required: Literal[True] = True
    raw_and_parsed_same_response_required: Literal[True] = True
    provider_error_stops_execution: Literal[True] = True
    invalid_observation_stops_execution: Literal[True] = True
    evidence_write_failure_stops_execution: Literal[True] = True
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    absolute_schedule_enforced: Literal[True] = True
    write_through_journal_required: Literal[True] = True
    protected_raw_retention_required: Literal[True] = True
    protected_parsed_retention_required: Literal[True] = True
    public_raw_payload_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> ReauthorizationExecutionRuntimePolicy:
        if self.schedule_offsets_seconds != (0, 10):
            raise ValueError("runtime offsets must remain 0 and 10 seconds")
        if self.request_roles != ("cold_wire_probe", "warm_wire_probe"):
            raise ValueError("runtime roles must remain cold then warm")
        if self.planned_maximum_cost_microusd != (self.planned_cost_microusd_per_call * 2):
            raise ValueError("planned maximum cost must cover exactly two calls")
        if self.planned_maximum_cost_microusd > self.authorization_cost_ceiling_microusd:
            raise ValueError("runtime cost exceeds authorization ceiling")
        return self


class ReauthorizationActivationReport(BaseModel):
    """Metadata-only activation state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-reauthorization-auth-v1"]
    execution_id: Literal["groq-cache-telemetry-reauthorization-v1"]
    status: Literal["active"]
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    active_authorization_created: Literal[True] = True
    execution_command_available: Literal[True] = True
    reauthorization_execution_authorized: Literal[True] = True
    prior_calibration_rerun_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal["live_reauthorization_preflight"] = "live_reauthorization_preflight"


class ReauthorizationActivationManifest(BaseModel):
    """Integrity manifest for activation assets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-reauthorization-auth-v1"]
    authorization_sha256: str
    runtime_policy_sha256: str
    activation_report_sha256: str
    adr_sha256: str
    report_sha256: str
    provider_call_performed: Literal[False] = False
    active_authorization_created: Literal[True] = True

    @field_validator(
        "authorization_sha256",
        "runtime_policy_sha256",
        "activation_report_sha256",
        "adr_sha256",
        "report_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("activation manifest requires lowercase SHA-256")
        return value


class ReauthorizationAttemptRecord(BaseModel):
    """Public metadata-only record for one raw-wire attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_index: int = Field(ge=0, le=1)
    request_role: Literal["cold_wire_probe", "warm_wire_probe"]
    planned_offset_seconds: int = Field(ge=0, le=10)
    observed_offset_ms: int | None = Field(default=None, ge=0)
    provider_request_sha256: str
    status: ReauthorizationAttemptStatus
    provider_call_made: bool
    provider_error_code: str | None = None
    http_status_code: int | None = Field(default=None, ge=100, le=599)
    raw_body_sha256: str | None = None
    raw_body_byte_count: int | None = Field(default=None, ge=0)
    parsed_response_sha256: str | None = None
    parsed_response_byte_count: int | None = Field(default=None, ge=0)
    installed_sdk_version: str | None = None
    raw_billing_observation_state: ReauthorizationBillingObservationState | None = None
    raw_billing_field_present: bool | None = None
    raw_billing_cached_tokens: int | None = Field(default=None, ge=0)
    parsed_billing_observation_state: ReauthorizationBillingObservationState | None = None
    parsed_billing_field_present: bool | None = None
    parsed_billing_cached_tokens: int | None = Field(default=None, ge=0)
    raw_parsed_numeric_values_match: bool | None = None
    estimated_cost_microusd: int = Field(ge=0, le=200)

    @field_validator(
        "provider_request_sha256",
        "raw_body_sha256",
        "parsed_response_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("attempt identities require lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_terminal_state(self) -> ReauthorizationAttemptRecord:
        if self.status is ReauthorizationAttemptStatus.SUCCEEDED:
            required = (
                self.provider_call_made,
                self.raw_body_sha256 is not None,
                self.raw_body_byte_count is not None,
                self.parsed_response_sha256 is not None,
                self.parsed_response_byte_count is not None,
                self.installed_sdk_version is not None,
                self.raw_billing_observation_state is not None,
                self.parsed_billing_observation_state is not None,
                self.raw_billing_field_present is not None,
                self.parsed_billing_field_present is not None,
            )
            if not all(required):
                raise ValueError("successful attempts require complete dual-boundary metadata")
            if self.provider_error_code is not None:
                raise ValueError("successful attempts cannot retain a provider error")
            if self.estimated_cost_microusd != 200:
                raise ValueError("successful provider calls require planned cost")
            return self
        if self.status in {
            ReauthorizationAttemptStatus.PROVIDER_ERROR,
            ReauthorizationAttemptStatus.OBSERVATION_INVALID,
        }:
            if not self.provider_call_made or self.estimated_cost_microusd != 200:
                raise ValueError("failed live attempts require one provider-call cost")
            return self
        if self.provider_call_made or self.observed_offset_ms is not None:
            raise ValueError("skipped attempts cannot claim provider activity")
        if self.estimated_cost_microusd != 0:
            raise ValueError("skipped attempts cannot consume provider cost")
        return self


class ReauthorizationRunRecordSet(BaseModel):
    """Complete record set for both planned attempts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-reauthorization-auth-v1"]
    execution_id: Literal["groq-cache-telemetry-reauthorization-v1"]
    records: tuple[ReauthorizationAttemptRecord, ReauthorizationAttemptRecord]

    @model_validator(mode="after")
    def validate_records(self) -> ReauthorizationRunRecordSet:
        if tuple(item.attempt_index for item in self.records) != (0, 1):
            raise ValueError("run records must reconcile attempts zero and one")
        if len({item.provider_request_sha256 for item in self.records}) != 1:
            raise ValueError("both attempts must use one exact provider request")
        return self


class ReauthorizationExecutionReport(BaseModel):
    """Public terminal result and bounded claim state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-reauthorization-auth-v1"]
    execution_id: Literal["groq-cache-telemetry-reauthorization-v1"]
    status: ReauthorizationExecutionStatus
    outcome: GroqCacheTelemetryReauthorizationOutcome
    planned_attempt_count: Literal[2] = 2
    provider_call_count: int = Field(ge=0, le=2)
    successful_call_count: int = Field(ge=0, le=2)
    provider_error_count: int = Field(ge=0, le=2)
    observation_invalid_count: int = Field(ge=0, le=2)
    skipped_attempt_count: int = Field(ge=0, le=2)
    raw_numeric_sample_count: int = Field(ge=0, le=2)
    parsed_numeric_sample_count: int = Field(ge=0, le=2)
    raw_absent_sample_count: int = Field(ge=0, le=2)
    estimated_cost_microusd: int = Field(ge=0, le=400)
    live_provider_called: bool
    execution_completed: Literal[True] = True
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    exact_provider_wire_omission_claim_permitted: bool
    sdk_live_parse_defect_claim_permitted: bool
    provider_cache_usage_claim_permitted_for_execution: bool
    provider_cache_savings_claim_permitted: Literal[False] = False
    benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal["groq_cache_telemetry_reauthorization_closeout"] = (
        "groq_cache_telemetry_reauthorization_closeout"
    )

    @model_validator(mode="after")
    def validate_report(self) -> ReauthorizationExecutionReport:
        if (
            self.successful_call_count
            + self.provider_error_count
            + self.observation_invalid_count
            + self.skipped_attempt_count
            != 2
        ):
            raise ValueError("report counts must reconcile two attempts")
        if self.provider_call_count != (
            self.successful_call_count + self.provider_error_count + self.observation_invalid_count
        ):
            raise ValueError("provider-call count must reconcile live attempts")
        if self.estimated_cost_microusd != self.provider_call_count * 200:
            raise ValueError("estimated cost must reconcile provider calls")
        if self.outcome is GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_ABSENT:
            if not self.exact_provider_wire_omission_claim_permitted:
                raise ValueError("wire absence must permit the bounded omission claim")
            if self.provider_cache_usage_claim_permitted_for_execution:
                raise ValueError("wire absence cannot permit a cache-usage claim")
        if (
            self.outcome
            is GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_PRESENT_BUT_PARSED_ABSENT
            and not self.sdk_live_parse_defect_claim_permitted
        ):
            raise ValueError("wire/parser divergence must permit the bounded SDK claim")
        return self


class ReauthorizationExecutionManifest(BaseModel):
    """Integrity manifest for terminal public evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-reauthorization-auth-v1"]
    authorization_sha256: str
    runtime_policy_sha256: str
    activation_manifest_sha256: str
    journal_sha256: str
    run_records_sha256: str
    report_sha256: str
    protected_raw_responses_sha256: str
    protected_parsed_responses_sha256: str
    live_provider_called: bool
    execution_completed: Literal[True] = True

    @field_validator(
        "authorization_sha256",
        "runtime_policy_sha256",
        "activation_manifest_sha256",
        "journal_sha256",
        "run_records_sha256",
        "report_sha256",
        "protected_raw_responses_sha256",
        "protected_parsed_responses_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution manifest requires lowercase SHA-256")
        return value


class ReauthorizationExecutionSummary(BaseModel):
    """Metadata-safe CLI result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "live-preflight", "run", "verify"]
    authorization_id: str
    authorization_status: ReauthorizationExecutionAuthorizationStatus
    planned_attempt_count: Literal[2] = 2
    provider_call_count: int = Field(ge=0, le=2)
    execution_completed: bool
    live_provider_called: bool
    credential_checked: bool
    provider_calls_permitted: bool
    execution_command_available: Literal[True] = True
    resume_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False


class ReauthorizationExecutionErrorEnvelope(BaseModel):
    """Metadata-safe CLI error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()
