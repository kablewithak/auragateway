"""Typed contracts for inactive diagnostic execution authorization review."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.diagnostic_experiment import (
    DiagnosticConditionLabel,
    DiagnosticStage,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")


class DiagnosticAuthorizationReviewStatus(StrEnum):
    """Lifecycle state before any live authorization is activated."""

    REVIEW_READY = "review_ready"


class DiagnosticActivationState(StrEnum):
    """Provider execution activation state."""

    INACTIVE = "inactive"


class DiagnosticReviewBinding(BaseModel):
    """One immutable repository or protected-local dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    sha256: str
    protected_local: bool = False

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic review bindings require lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_protected_path(self) -> DiagnosticReviewBinding:
        is_local = self.path.startswith(".local/")
        if self.protected_local != is_local:
            raise ValueError("protected_local must match the .local path boundary")
        return self


class DiagnosticProviderReviewProfile(BaseModel):
    """Exact provider request profile reviewed before activation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["groq"] = "groq"
    provider_model_alias: Literal["groq-gpt-oss-20b"] = "groq-gpt-oss-20b"
    exact_model_identifier: Literal["openai/gpt-oss-20b"] = "openai/gpt-oss-20b"
    adapter_version: Literal["groq-chat-completions-v1"] = "groq-chat-completions-v1"
    maximum_completion_tokens: Literal[256] = 256
    temperature_milli: Literal[0] = 0
    streaming: Literal[False] = False
    store_enabled: Literal[False] = False
    reasoning_effort: Literal["low"] = "low"
    timeout_seconds: Literal[30] = 30


class DiagnosticEvidenceReviewPolicy(BaseModel):
    """Public and protected evidence destinations for later execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    public_journal_path: Literal["data/evals/benchmark/diagnostic-execution-v1/journal.jsonl"]
    public_run_records_path: Literal[
        "data/evals/benchmark/diagnostic-execution-v1/run_records.json"
    ]
    public_report_path: Literal["data/evals/benchmark/diagnostic-execution-v1/report.json"]
    protected_raw_outputs_path: Literal[
        ".local/benchmark/diagnostic-execution-v1/provider_raw_outputs.jsonl"
    ]
    protected_failure_diagnostics_path: Literal[
        ".local/benchmark/diagnostic-execution-v1/provider_failure_diagnostics.jsonl"
    ]
    raw_prompts_in_public_evidence_permitted: Literal[False] = False
    raw_outputs_in_public_evidence_permitted: Literal[False] = False
    provider_error_messages_in_public_evidence_permitted: Literal[False] = False
    credentials_in_logs_permitted: Literal[False] = False


class DiagnosticAuthorizationReviewPackage(BaseModel):
    """Inactive review package that cannot itself permit provider execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["batch-06-diagnostic-execution-review-v1"]
    status: DiagnosticAuthorizationReviewStatus
    activation_state: DiagnosticActivationState
    design_id: Literal["batch-06-request-rejection-diagnostic-design-v1"]
    fixture_id: Literal["batch-06-diagnostic-prompt-fixtures-v1"]
    bindings: tuple[DiagnosticReviewBinding, ...] = Field(
        min_length=5,
        max_length=5,
    )
    provider_profile: DiagnosticProviderReviewProfile
    evidence_policy: DiagnosticEvidenceReviewPolicy
    sequence_ids_in_order: tuple[
        Literal["order-alpha-b-first"],
        Literal["order-alpha-c-second"],
        Literal["order-beta-c-first"],
        Literal["order-beta-b-second"],
        Literal["spacing-gamma-b-zero"],
        Literal["spacing-delta-b-thirty"],
        Literal["spacing-epsilon-c-zero"],
        Literal["spacing-zeta-c-thirty"],
    ]
    maximum_provider_calls: Literal[24] = 24
    maximum_total_cost_microusd: Literal[5000] = 5000
    minimum_planned_elapsed_seconds: Literal[2220] = 2220
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    held_out_execution_permitted: Literal[False] = False
    full_benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    dry_run_only: Literal[True] = True
    credential_required: Literal[False] = False
    provider_calls_permitted: Literal[False] = False
    execution_command_available: Literal[False] = False
    active_authorization_id: None = None
    activation_review_required: Literal[True] = True
    next_gate: Literal["active_authorization_review"] = "active_authorization_review"

    @model_validator(mode="after")
    def validate_inactive_review(self) -> DiagnosticAuthorizationReviewPackage:
        if self.status is not DiagnosticAuthorizationReviewStatus.REVIEW_READY:
            raise ValueError("diagnostic authorization review must be review-ready")
        if self.activation_state is not DiagnosticActivationState.INACTIVE:
            raise ValueError("diagnostic authorization review must remain inactive")

        expected_paths = {
            "data/evals/benchmark/diagnostic-design-v1/experiment_plan.json",
            "data/evals/benchmark/diagnostic-design-v1/manifest.json",
            "data/evals/benchmark/diagnostic-fixtures-v1/fixture_recipe.json",
            "data/evals/benchmark/diagnostic-fixtures-v1/fixture_manifest.json",
            ".local/benchmark/diagnostic-fixtures-v1/prompt_cohorts.json",
        }
        observed_paths = [item.path for item in self.bindings]
        if set(observed_paths) != expected_paths or len(observed_paths) != len(set(observed_paths)):
            raise ValueError("diagnostic review must bind the five frozen assets exactly")
        protected = [item for item in self.bindings if item.protected_local]
        if len(protected) != 1:
            raise ValueError("diagnostic review requires one protected-local binding")
        if len(self.sequence_ids_in_order) != len(set(self.sequence_ids_in_order)):
            raise ValueError("diagnostic review sequence IDs must be unique")
        return self


class DiagnosticDryRunAttempt(BaseModel):
    """One metadata-only attempt projected without provider execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_index: int = Field(ge=0, le=23)
    sequence_id: str
    sequence_schedule_index: int = Field(ge=0, le=7)
    stage: DiagnosticStage
    cohort_id: str
    condition_label: DiagnosticConditionLabel
    turn_index: int = Field(ge=1, le=3)
    planned_offset_seconds: int = Field(ge=0, le=2220)
    planned_delay_from_previous_attempt_seconds: int = Field(ge=0, le=300)
    system_prompt_sha256: str
    user_prompt_sha256: str
    provider_request_sha256: str
    prompt_byte_count: int = Field(gt=0)
    input_token_estimate: int = Field(gt=0)
    provider_call_permitted: Literal[False] = False
    retry_permitted: Literal[False] = False

    @field_validator(
        "sequence_id",
        "cohort_id",
    )
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run identifiers must use lowercase stable slugs")
        return value

    @field_validator(
        "system_prompt_sha256",
        "user_prompt_sha256",
        "provider_request_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run attempt identities must be lowercase SHA-256")
        return value


class DiagnosticDryRunReport(BaseModel):
    """Committed metadata-only projection of the inactive execution review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    report_id: Literal["batch-06-diagnostic-execution-dry-run-v1"]
    review_id: Literal["batch-06-diagnostic-execution-review-v1"]
    status: Literal["dry_run_validated"] = "dry_run_validated"
    attempts: tuple[DiagnosticDryRunAttempt, ...] = Field(
        min_length=24,
        max_length=24,
    )
    sequence_count: Literal[8] = 8
    attempt_count: Literal[24] = 24
    unique_provider_request_count: Literal[18] = 18
    repeated_provider_request_count: Literal[6] = 6
    minimum_planned_elapsed_seconds: Literal[2220] = 2220
    maximum_provider_calls: Literal[24] = 24
    maximum_total_cost_microusd: Literal[5000] = 5000
    unique_stable_prefixes_verified: Literal[True] = True
    exact_prompt_byte_counts_verified: Literal[True] = True
    provider_visible_b_c_equivalence_verified: Literal[True] = True
    protected_prompt_bundle_verified: Literal[True] = True
    stop_rules_bound: Literal[True] = True
    credential_accessed: Literal[False] = False
    provider_calls_permitted: Literal[False] = False
    provider_calls_made: Literal[False] = False
    authorization_created: Literal[False] = False
    execution_permitted: Literal[False] = False
    next_gate: Literal["active_authorization_review"] = "active_authorization_review"

    @model_validator(mode="after")
    def validate_dry_run_schedule(self) -> DiagnosticDryRunReport:
        if [item.attempt_index for item in self.attempts] != list(range(24)):
            raise ValueError("dry-run attempt indices must be contiguous")
        if self.attempts[-1].planned_offset_seconds != 2220:
            raise ValueError("dry-run schedule must end at the frozen minimum elapsed time")
        if len({item.sequence_id for item in self.attempts}) != 8:
            raise ValueError("dry-run report must contain all eight sequences")
        sequence_counts: dict[str, int] = {}
        for attempt in self.attempts:
            sequence_counts[attempt.sequence_id] = sequence_counts.get(attempt.sequence_id, 0) + 1
        if set(sequence_counts.values()) != {3}:
            raise ValueError("every dry-run sequence must contain exactly three attempts")
        request_hashes = [item.provider_request_sha256 for item in self.attempts]
        unique_count = len(set(request_hashes))
        repeated_count = len(request_hashes) - unique_count
        if unique_count != self.unique_provider_request_count:
            raise ValueError("dry-run unique provider request count is inconsistent")
        if repeated_count != self.repeated_provider_request_count:
            raise ValueError("dry-run repeated provider request count is inconsistent")
        return self


class DiagnosticAuthorizationReviewManifest(BaseModel):
    """Integrity binding for the inactive review package and dry-run report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["batch-06-diagnostic-execution-review-v1"]
    review_package_path: Literal[
        "data/evals/benchmark/diagnostic-authorization-review-v1/review_package.json"
    ]
    review_package_sha256: str
    dry_run_report_path: Literal[
        "data/evals/benchmark/diagnostic-authorization-review-v1/dry_run_report.json"
    ]
    dry_run_report_sha256: str
    activation_state: Literal["inactive"] = "inactive"
    active_authorization_present: Literal[False] = False
    provider_calls_permitted: Literal[False] = False
    execution_command_available: Literal[False] = False

    @field_validator("review_package_sha256", "dry_run_report_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic review manifest requires lowercase SHA-256")
        return value


class DiagnosticAuthorizationReviewSummary(BaseModel):
    """Metadata-only validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "dry-run"]
    review_id: str
    status: DiagnosticAuthorizationReviewStatus
    activation_state: DiagnosticActivationState
    sequence_count: Literal[8] = 8
    attempt_count: Literal[24] = 24
    minimum_planned_elapsed_seconds: Literal[2220] = 2220
    maximum_provider_calls: Literal[24] = 24
    maximum_total_cost_microusd: Literal[5000] = 5000
    protected_prompt_bundle_verified: Literal[True] = True
    provider_calls_permitted: Literal[False] = False
    provider_calls_made: Literal[False] = False
    credential_accessed: Literal[False] = False
    authorization_created: Literal[False] = False
    execution_permitted: Literal[False] = False
    next_gate: Literal["active_authorization_review"] = "active_authorization_review"
