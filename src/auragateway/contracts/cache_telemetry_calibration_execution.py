"""Typed contracts for one-time Groq cache telemetry calibration execution."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.cache_telemetry_calibration_review import (
    CalibrationOutcome,
)
from auragateway.contracts.cache_telemetry_capture import (
    BillingCacheObservationState,
)
from auragateway.contracts.provider import ProviderErrorCode, ProviderName

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class CalibrationExecutionAuthorizationStatus(StrEnum):
    """Lifecycle state of the one-time calibration authorization."""

    ACTIVE = "active"


class CalibrationAttemptStatus(StrEnum):
    """Terminal state for one planned calibration attempt."""

    SUCCEEDED = "succeeded"
    PROVIDER_ERROR = "provider_error"
    TELEMETRY_INVALID = "telemetry_invalid"
    SKIPPED = "skipped"


class CalibrationExecutionStatus(StrEnum):
    """Terminal state of the one-time calibration."""

    COMPLETED = "completed"
    FAILED = "failed"


class CalibrationExecutionBinding(BaseModel):
    """One immutable review dependency bound into active authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    sha256: str
    protected_local: bool = False

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution bindings require lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_local_boundary(self) -> CalibrationExecutionBinding:
        if self.protected_local != self.path.startswith(".local/"):
            raise ValueError("protected_local must match the .local boundary")
        return self


class CalibrationExecutionEvidencePaths(BaseModel):
    """Public and protected calibration evidence destinations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-v1/authorization.json"
    ]
    runtime_policy_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-v1/runtime_policy.json"
    ]
    journal_path: Literal["data/evals/benchmark/cache-telemetry-calibration-v1/journal.jsonl"]
    run_records_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-v1/run_records.json"
    ]
    report_path: Literal["data/evals/benchmark/cache-telemetry-calibration-v1/report.json"]
    manifest_path: Literal["data/evals/benchmark/cache-telemetry-calibration-v1/manifest.json"]
    protected_outputs_path: Literal[
        ".local/benchmark/cache-telemetry-calibration-v1/provider_outputs.jsonl"
    ]
    protected_prompt_bundle_path: Literal[
        ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    ]


class CalibrationExecutionAuthorization(BaseModel):
    """One-time active authorization that exposes but does not perform execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-calibration-auth-v1"]
    status: Literal[CalibrationExecutionAuthorizationStatus.ACTIVE] = (
        CalibrationExecutionAuthorizationStatus.ACTIVE
    )
    review_id: Literal["groq-cache-telemetry-calibration-review-v1"]
    calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    source_commit: Literal["75a5ebae3a2fe1d40ac7cc01137744bb05c7e3ec"]
    bindings: tuple[CalibrationExecutionBinding, ...] = Field(
        min_length=5,
        max_length=5,
    )
    provider: Literal[ProviderName.GROQ] = ProviderName.GROQ
    model_alias: Literal["groq-gpt-oss-20b"] = "groq-gpt-oss-20b"
    exact_model_identifier: Literal["openai/gpt-oss-20b"] = "openai/gpt-oss-20b"
    adapter_version: Literal["groq-chat-completions-v1"] = "groq-chat-completions-v1"
    telemetry_capture_version: Literal["groq-cache-telemetry-capture-v1"] = (
        "groq-cache-telemetry-capture-v1"
    )
    timeout_seconds: Literal[30] = 30
    maximum_completion_tokens: Literal[32] = 32
    maximum_provider_calls: Literal[3] = 3
    maximum_total_cost_microusd: Literal[1000] = 1000
    planned_maximum_cost_microusd: Literal[600] = 600
    minimum_planned_elapsed_seconds: Literal[20] = 20
    planned_attempt_count: Literal[3] = 3
    confirmation_phrase: Literal["EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"] = (
        "EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"
    )
    evidence_paths: CalibrationExecutionEvidencePaths
    one_time_execution: Literal[True] = True
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    provider_calls_permitted: Literal[True] = True
    credential_required: Literal[True] = True
    execution_command_available: Literal[True] = True
    calibration_execution_authorized: Literal[True] = True
    benchmark_execution_authorized: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    execution_completed: Literal[False] = False
    next_gate: Literal["live_calibration_preflight"] = "live_calibration_preflight"

    @model_validator(mode="after")
    def validate_bindings(self) -> CalibrationExecutionAuthorization:
        expected = {
            "data/evals/benchmark/cache-telemetry-calibration-review-v1/prompt_recipe.json",
            "data/evals/benchmark/cache-telemetry-calibration-review-v1/review.json",
            "data/evals/benchmark/cache-telemetry-calibration-review-v1/dry_run_report.json",
            "data/evals/benchmark/cache-telemetry-calibration-review-v1/manifest.json",
            ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json",
        }
        paths = [item.path for item in self.bindings]
        if set(paths) != expected or len(paths) != len(set(paths)):
            raise ValueError("authorization requires the five reviewed assets")
        if sum(item.protected_local for item in self.bindings) != 1:
            raise ValueError("authorization requires one protected binding")
        if self.planned_maximum_cost_microusd > self.maximum_total_cost_microusd:
            raise ValueError("planned calibration cost exceeds authorization")
        return self


class CalibrationExecutionRuntimePolicy(BaseModel):
    """Fail-closed runtime trajectory policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-calibration-auth-v1"]
    schedule_offsets_seconds: tuple[
        Literal[0],
        Literal[10],
        Literal[20],
    ]
    request_roles: tuple[
        Literal["cold"],
        Literal["warm_repeat_one"],
        Literal["warm_repeat_two"],
    ]
    planned_cost_microusd_per_call: Literal[200] = 200
    planned_maximum_cost_microusd: Literal[600] = 600
    authorization_cost_ceiling_microusd: Literal[1000] = 1000
    exact_provider_request_required: Literal[True] = True
    provider_error_stops_calibration: Literal[True] = True
    telemetry_shape_missing_stops_calibration: Literal[True] = True
    evidence_write_failure_stops_calibration: Literal[True] = True
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    absolute_schedule_enforced: Literal[True] = True
    write_through_journal_required: Literal[True] = True
    protected_output_retention_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_policy(self) -> CalibrationExecutionRuntimePolicy:
        if self.schedule_offsets_seconds != (0, 10, 20):
            raise ValueError("runtime offsets must remain 0, 10, and 20")
        if self.request_roles != (
            "cold",
            "warm_repeat_one",
            "warm_repeat_two",
        ):
            raise ValueError("runtime roles must remain cold, warm one, warm two")
        if self.planned_maximum_cost_microusd != (self.planned_cost_microusd_per_call * 3):
            raise ValueError("planned maximum cost must cover three calls")
        if self.planned_maximum_cost_microusd > (self.authorization_cost_ceiling_microusd):
            raise ValueError("runtime cost exceeds authorization ceiling")
        return self


class CalibrationAttemptRecord(BaseModel):
    """Public metadata-only record for one planned attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_index: int = Field(ge=0, le=2)
    request_role: Literal[
        "cold",
        "warm_repeat_one",
        "warm_repeat_two",
    ]
    planned_offset_seconds: int = Field(ge=0, le=20)
    observed_offset_ms: int | None = Field(default=None, ge=0)
    provider_request_sha256: str
    system_prompt_sha256: str
    user_prompt_sha256: str
    status: CalibrationAttemptStatus
    provider_call_made: bool
    provider_error_code: ProviderErrorCode | None = None
    output_sha256: str | None = None
    output_byte_count: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_duration_ms: int | None = Field(default=None, ge=0)
    installed_sdk_version: str | None = None
    usage_present: bool | None = None
    prompt_tokens_details_present: bool | None = None
    billing_cached_tokens_field_present: bool | None = None
    billing_observation_state: BillingCacheObservationState | None = None
    billing_cached_input_tokens: int | None = Field(default=None, ge=0)
    x_groq_present: bool | None = None
    x_groq_usage_present: bool | None = None
    dram_cached_tokens_field_present: bool | None = None
    dram_cached_tokens: int | None = Field(default=None, ge=0)
    sram_cached_tokens_field_present: bool | None = None
    sram_cached_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_microusd: int = Field(ge=0, le=200)

    @field_validator(
        "provider_request_sha256",
        "system_prompt_sha256",
        "user_prompt_sha256",
        "output_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("attempt identities require lowercase SHA-256")
        return value

    @field_validator("installed_sdk_version")
    @classmethod
    def validate_version(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("installed SDK version cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_terminal_state(self) -> CalibrationAttemptRecord:
        if self.status is CalibrationAttemptStatus.SUCCEEDED:
            if not self.provider_call_made:
                raise ValueError("successful attempts require a provider call")
            if self.provider_error_code is not None:
                raise ValueError("successful attempts cannot retain an error")
            if self.output_sha256 is None or self.output_byte_count is None:
                raise ValueError("successful attempts require output identity")
            if self.installed_sdk_version is None:
                raise ValueError("successful attempts require SDK provenance")
            if self.billing_observation_state is None:
                raise ValueError("successful attempts require cache field state")
            if self.estimated_cost_microusd != 200:
                raise ValueError("successful calls require planned cost")
            return self

        if self.status in {
            CalibrationAttemptStatus.PROVIDER_ERROR,
            CalibrationAttemptStatus.TELEMETRY_INVALID,
        }:
            if not self.provider_call_made:
                raise ValueError("failed live attempts require a provider call")
            if self.estimated_cost_microusd != 200:
                raise ValueError("failed live calls require planned cost")
            return self

        if self.provider_call_made or self.observed_offset_ms is not None:
            raise ValueError("skipped attempts cannot claim provider activity")
        if self.estimated_cost_microusd != 0:
            raise ValueError("skipped attempts cannot consume provider cost")
        return self


class CalibrationRunRecordSet(BaseModel):
    """Complete record set for all three planned attempts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-calibration-auth-v1"]
    calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    records: tuple[CalibrationAttemptRecord, ...] = Field(
        min_length=3,
        max_length=3,
    )

    @model_validator(mode="after")
    def validate_records(self) -> CalibrationRunRecordSet:
        if [item.attempt_index for item in self.records] != [0, 1, 2]:
            raise ValueError("calibration records must reconcile all attempts")
        hashes = {item.provider_request_sha256 for item in self.records}
        if len(hashes) != 1:
            raise ValueError("all calibration request identities must match")
        return self


class CalibrationExecutionReport(BaseModel):
    """Public calibration result and claim boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-calibration-auth-v1"]
    calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    status: CalibrationExecutionStatus
    outcome: CalibrationOutcome
    planned_attempt_count: Literal[3] = 3
    provider_call_count: int = Field(ge=0, le=3)
    successful_call_count: int = Field(ge=0, le=3)
    provider_error_count: int = Field(ge=0, le=3)
    telemetry_invalid_count: int = Field(ge=0, le=3)
    skipped_attempt_count: int = Field(ge=0, le=3)
    billing_cache_numeric_sample_count: int = Field(ge=0, le=3)
    warm_positive_cache_sample_count: int = Field(ge=0, le=2)
    estimated_cost_microusd: int = Field(ge=0, le=600)
    live_provider_called: bool
    execution_completed: Literal[True] = True
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    provider_cache_usage_claim_permitted_for_calibration: bool
    provider_cache_savings_claim_permitted: Literal[False] = False
    benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal["cache_telemetry_calibration_closeout"] = (
        "cache_telemetry_calibration_closeout"
    )

    @model_validator(mode="after")
    def validate_reconciliation(self) -> CalibrationExecutionReport:
        if (
            self.successful_call_count
            + self.provider_error_count
            + self.telemetry_invalid_count
            + self.skipped_attempt_count
            != 3
        ):
            raise ValueError("report counts must reconcile three attempts")
        if self.provider_call_count != (
            self.successful_call_count + self.provider_error_count + self.telemetry_invalid_count
        ):
            raise ValueError("provider call count must reconcile live attempts")
        if self.estimated_cost_microusd != self.provider_call_count * 200:
            raise ValueError("estimated cost must reconcile provider calls")
        return self


class CalibrationExecutionManifest(BaseModel):
    """Integrity manifest for one-time calibration evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["groq-cache-telemetry-calibration-auth-v1"]
    authorization_sha256: str
    runtime_policy_sha256: str
    journal_sha256: str
    run_records_sha256: str
    report_sha256: str
    live_provider_called: bool
    execution_completed: Literal[True] = True

    @field_validator(
        "authorization_sha256",
        "runtime_policy_sha256",
        "journal_sha256",
        "run_records_sha256",
        "report_sha256",
    )
    @classmethod
    def validate_manifest_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution manifest requires lowercase SHA-256")
        return value


class CalibrationExecutionSummary(BaseModel):
    """Metadata-safe CLI result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "live-preflight", "run", "verify"]
    authorization_id: str
    authorization_status: CalibrationExecutionAuthorizationStatus
    planned_attempt_count: Literal[3] = 3
    provider_call_count: int = Field(ge=0, le=3)
    execution_completed: bool
    live_provider_called: bool
    credential_checked: bool
    provider_calls_permitted: bool
    execution_command_available: Literal[True] = True
    resume_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
