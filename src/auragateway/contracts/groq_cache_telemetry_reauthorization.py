"""Typed non-live review for a bounded Groq cache-telemetry reauthorization."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class GroqCacheTelemetryReauthorizationStatus(StrEnum):
    """Terminal state of the non-live reauthorization review."""

    REVIEW_READY_INACTIVE = "review_ready_inactive"


class GroqCacheTelemetryReauthorizationDecision(StrEnum):
    """Bounded decision produced by the review."""

    REVIEW_READY_INACTIVE = "reauthorization_review_ready_inactive"
    DENIED_NO_NEW_INFORMATION = "reauthorization_denied_no_new_information"
    BLOCKED_PROVIDER_CLARIFICATION_REQUIRED = (
        "reauthorization_blocked_provider_clarification_required"
    )


class GroqCacheTelemetryObservationBoundary(StrEnum):
    """Observation surfaces used before and after the proposed intervention."""

    PARSED_SDK_OBJECT = "parsed_sdk_object"
    SDK_RAW_AND_PARSED_SAME_RESPONSE = "sdk_raw_and_parsed_same_response"


class GroqCacheTelemetryReauthorizationOutcome(StrEnum):
    """Possible future execution outcomes frozen before activation."""

    WIRE_FIELD_PRESENT_AND_PARSED = "wire_field_present_and_parsed"
    WIRE_FIELD_PRESENT_BUT_PARSED_ABSENT = "wire_field_present_but_parsed_absent"
    WIRE_FIELD_ABSENT = "wire_field_absent"
    EXECUTION_FAILED = "reauthorization_execution_failed"


class ReauthorizationSourceBinding(BaseModel):
    """Immutable repository evidence used by the review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    purpose: str = Field(min_length=3, max_length=200)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("source binding paths must be repository-relative")
        if not value.startswith("data/evals/benchmark/"):
            raise ValueError("source bindings must remain under benchmark evidence")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("source binding SHA-256 must be lowercase hexadecimal")
        return value


class ReauthorizationExternalProviderBoundary(BaseModel):
    """Current official provider facts used by the non-live decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    documentation_url: str
    retrieved_on: date
    supported_model: Literal["openai/gpt-oss-20b"]
    automatic_caching: Literal[True]
    exact_prefix_required: Literal[True]
    cache_hit_guaranteed: Literal[False]
    cache_expiry_without_use_hours: Literal[2]
    minimum_cacheable_token_lower_bound: Literal[128]
    minimum_cacheable_token_upper_bound: Literal[1024]
    billing_cached_tokens_path: Literal["usage.prompt_tokens_details.cached_tokens"]
    cached_input_discount_percent: Literal[50]

    @field_validator("documentation_url")
    @classmethod
    def validate_documentation_url(cls, value: str) -> str:
        if value != "https://console.groq.com/docs/prompt-caching":
            raise ValueError("provider evidence must use the official prompt-caching page")
        return value


class ReauthorizationSdkBoundary(BaseModel):
    """Installed SDK surface required for dual raw/parsed observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    installed_sdk_version: Literal["1.5.0"]
    resource_path: Literal["client.chat.completions.with_raw_response.create"]
    raw_and_parsed_same_http_response: Literal[True]
    raw_body_public_persistence_permitted: Literal[False]
    raw_body_protected_local_required: Literal[True]
    parsed_object_public_persistence_permitted: Literal[False]
    parsed_object_protected_local_required: Literal[True]


class ReauthorizationMaterialDifference(BaseModel):
    """Evidence that a future run is not a duplicate of the closed calibration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prior_observation_boundary: Literal[GroqCacheTelemetryObservationBoundary.PARSED_SDK_OBJECT]
    proposed_observation_boundary: Literal[
        GroqCacheTelemetryObservationBoundary.SDK_RAW_AND_PARSED_SAME_RESPONSE
    ]
    provider_unchanged: Literal[True]
    model_unchanged: Literal[True]
    prompt_unchanged: Literal[True]
    request_parameters_unchanged: Literal[True]
    only_observation_boundary_changes: Literal[True]
    materially_different: Literal[True]
    information_gain_questions: tuple[str, ...] = Field(min_length=3, max_length=3)

    @field_validator("information_gain_questions")
    @classmethod
    def validate_information_questions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("information-gain questions must be unique")
        if any(len(item.strip()) < 10 for item in value):
            raise ValueError("information-gain questions must be substantive")
        return value


class ReauthorizationObservationPlan(BaseModel):
    """Exact inactive plan for a potential two-call wire-versus-SDK calibration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    plan_id: str
    review_id: str
    provider: Literal["groq"]
    model_alias: Literal["groq-gpt-oss-20b"]
    exact_model_identifier: Literal["openai/gpt-oss-20b"]
    adapter_version: Literal["groq-chat-completions-v1"]
    telemetry_capture_version: Literal["groq-cache-telemetry-capture-v1"]
    raw_response_capture_version: Literal["groq-raw-response-capture-v1"]
    prompt_recipe_path: str
    prompt_recipe_sha256: str
    protected_prompt_bundle_path: str
    protected_prompt_bundle_sha256: str
    protected_raw_responses_path: str
    protected_parsed_responses_path: str
    maximum_completion_tokens: Literal[32]
    temperature_milli: Literal[0]
    streaming: Literal[False]
    storage: Literal[False]
    reasoning_effort: Literal["low"]
    timeout_seconds: Literal[30]
    planned_attempt_count: Literal[2]
    maximum_provider_calls: Literal[2]
    attempt_offsets_seconds: tuple[int, int]
    request_roles: tuple[Literal["cold_wire_probe"], Literal["warm_wire_probe"]]
    exact_provider_request_required: Literal[True]
    planned_cost_microusd_per_call: Literal[200]
    planned_maximum_cost_microusd: Literal[400]
    authorization_cost_ceiling_microusd: Literal[700]
    retry_permitted: Literal[False]
    resume_permitted: Literal[False]
    public_raw_payload_permitted: Literal[False]
    provider_call_authorized: Literal[False]
    execution_command_available: Literal[False]
    activation_required: Literal[True]
    benchmark_execution_authorized: Literal[False]
    comparison_eligible: Literal[False]

    @field_validator("plan_id", "review_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("review and plan IDs must use stable lowercase identifiers")
        return value

    @field_validator("prompt_recipe_path")
    @classmethod
    def validate_prompt_recipe_path(cls, value: str) -> str:
        if value != "data/evals/benchmark/cache-telemetry-calibration-review-v1/prompt_recipe.json":
            raise ValueError("the reauthorization must reuse the frozen prompt recipe")
        return value

    @field_validator("protected_prompt_bundle_path")
    @classmethod
    def validate_protected_prompt_path(cls, value: str) -> str:
        if value != ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json":
            raise ValueError("the reauthorization must reuse the frozen protected prompt bundle")
        return value

    @field_validator("protected_raw_responses_path", "protected_parsed_responses_path")
    @classmethod
    def validate_protected_output_paths(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("protected output paths must be repository-relative")
        if not value.startswith(".local/benchmark/groq-cache-telemetry-reauthorization-v1/"):
            raise ValueError("future raw and parsed outputs must remain in the new local namespace")
        return value

    @field_validator("prompt_recipe_sha256", "protected_prompt_bundle_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("plan hashes must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_schedule(self) -> ReauthorizationObservationPlan:
        if self.attempt_offsets_seconds != (0, 10):
            raise ValueError("reauthorization offsets must remain 0 and 10 seconds")
        if self.maximum_provider_calls != self.planned_attempt_count:
            raise ValueError("provider-call ceiling must equal the two planned attempts")
        if self.planned_maximum_cost_microusd != (
            self.planned_cost_microusd_per_call * self.planned_attempt_count
        ):
            raise ValueError("planned cost must equal per-call cost times planned attempts")
        if self.authorization_cost_ceiling_microusd < self.planned_maximum_cost_microusd:
            raise ValueError("authorization cost ceiling must cover planned maximum cost")
        if self.protected_raw_responses_path == self.protected_parsed_responses_path:
            raise ValueError("raw and parsed protected outputs require distinct paths")
        return self


class ReauthorizationOutcomeRule(BaseModel):
    """Predeclared interpretation for one possible future execution result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: GroqCacheTelemetryReauthorizationOutcome
    requirements: tuple[str, ...] = Field(min_length=1)
    exact_provider_wire_omission_claim_permitted: bool
    sdk_live_parse_defect_claim_permitted: bool
    provider_cache_usage_claim_permitted: bool
    benchmark_claims_permitted: Literal[False] = False


class GroqCacheTelemetryReauthorizationReview(BaseModel):
    """Inactive review proving whether a future run would add new information."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    review_id: str
    status: Literal[GroqCacheTelemetryReauthorizationStatus.REVIEW_READY_INACTIVE]
    decision: Literal[GroqCacheTelemetryReauthorizationDecision.REVIEW_READY_INACTIVE]
    source_commit: str
    prior_authorization_id: Literal["groq-cache-telemetry-calibration-auth-v1"]
    prior_calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    prior_closeout_id: Literal["groq-cache-telemetry-calibration-closeout-v1"]
    compatibility_review_id: Literal["groq-sdk-cache-schema-compatibility-v1"]
    source_bindings: tuple[ReauthorizationSourceBinding, ...] = Field(min_length=11)
    external_provider_boundary: ReauthorizationExternalProviderBoundary
    sdk_boundary: ReauthorizationSdkBoundary
    material_difference: ReauthorizationMaterialDifference
    observation_plan_id: str
    observation_plan_sha256: str
    outcome_taxonomy: tuple[ReauthorizationOutcomeRule, ...] = Field(min_length=4, max_length=4)
    prior_authorization_consumed: Literal[True]
    prior_rerun_permitted: Literal[False]
    prior_resume_permitted: Literal[False]
    provider_call_performed: Literal[False]
    credential_required_for_review: Literal[False]
    credential_accessed: Literal[False]
    provider_call_authorized: Literal[False]
    active_authorization_created: Literal[False]
    execution_command_available: Literal[False]
    reauthorization_execution_authorized: Literal[False]
    benchmark_execution_authorized: Literal[False]
    benchmark_claims_permitted: Literal[False]
    comparison_eligible: Literal[False]
    next_gate: Literal["groq_cache_telemetry_reauthorization_activation"]

    @field_validator("review_id", "observation_plan_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("review identifiers must use stable lowercase identifiers")
        return value

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("source_commit must be a full lowercase Git commit SHA")
        return value

    @field_validator("observation_plan_sha256")
    @classmethod
    def validate_plan_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("observation plan hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_review(self) -> GroqCacheTelemetryReauthorizationReview:
        paths = [binding.path for binding in self.source_bindings]
        duplicates = sorted(value for value, count in Counter(paths).items() if count > 1)
        if duplicates:
            raise ValueError(f"source binding paths must be unique: {', '.join(duplicates)}")
        if len(paths) != 11:
            raise ValueError("reauthorization review requires exactly eleven lineage bindings")
        outcomes = [rule.outcome for rule in self.outcome_taxonomy]
        if set(outcomes) != set(GroqCacheTelemetryReauthorizationOutcome):
            raise ValueError("outcome taxonomy must cover every reauthorization outcome")
        if len(outcomes) != len(set(outcomes)):
            raise ValueError("reauthorization outcomes must be unique")
        if self.observation_plan_id == self.prior_calibration_id:
            raise ValueError("new review and prior calibration identities must remain distinct")
        return self


class ReauthorizationDryRunAttempt(BaseModel):
    """One metadata-only planned attempt; never a provider call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_index: int = Field(ge=0, le=1)
    request_role: Literal["cold_wire_probe", "warm_wire_probe"]
    planned_offset_seconds: int = Field(ge=0, le=10)
    provider_request_sha256: str
    prompt_recipe_sha256: str
    observation_boundary: Literal[
        GroqCacheTelemetryObservationBoundary.SDK_RAW_AND_PARSED_SAME_RESPONSE
    ]
    raw_response_capture_required: Literal[True]
    parsed_response_capture_required: Literal[True]
    provider_call_permitted: Literal[False]

    @field_validator("provider_request_sha256", "prompt_recipe_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run hashes must be lowercase SHA-256")
        return value


class ReauthorizationDryRunReport(BaseModel):
    """Deterministic inactive schedule derived from the observation plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    review_id: str
    plan_id: str
    status: Literal["passed_inactive"]
    attempts: tuple[ReauthorizationDryRunAttempt, ReauthorizationDryRunAttempt]
    planned_attempt_count: Literal[2]
    unique_provider_request_count: Literal[1]
    repeated_provider_request_count: Literal[1]
    raw_and_parsed_same_response_required: Literal[True]
    provider_call_performed: Literal[False]
    credential_accessed: Literal[False]
    execution_command_available: Literal[False]
    reauthorization_execution_authorized: Literal[False]
    benchmark_execution_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_dry_run(self) -> ReauthorizationDryRunReport:
        if tuple(item.attempt_index for item in self.attempts) != (0, 1):
            raise ValueError("dry-run attempts must remain ordered 0 then 1")
        if tuple(item.request_role for item in self.attempts) != (
            "cold_wire_probe",
            "warm_wire_probe",
        ):
            raise ValueError("dry-run request roles must remain cold then warm")
        if tuple(item.planned_offset_seconds for item in self.attempts) != (0, 10):
            raise ValueError("dry-run offsets must remain 0 and 10 seconds")
        if len({item.provider_request_sha256 for item in self.attempts}) != 1:
            raise ValueError("all reauthorization requests must be byte-identical")
        if len({item.prompt_recipe_sha256 for item in self.attempts}) != 1:
            raise ValueError("all attempts must bind the same prompt recipe")
        return self


class GroqCacheTelemetryReauthorizationManifest(BaseModel):
    """Hash manifest for the frozen inactive review assets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str
    status: Literal["frozen_inactive"]
    source_commit: str
    observation_plan_path: str
    observation_plan_sha256: str
    review_path: str
    review_sha256: str
    dry_run_report_path: str
    dry_run_report_sha256: str
    adr_path: str
    adr_sha256: str
    report_path: str
    report_sha256: str
    provider_call_authorized: Literal[False]
    active_authorization_created: Literal[False]
    execution_command_available: Literal[False]
    reauthorization_execution_authorized: Literal[False]
    benchmark_execution_authorized: Literal[False]
    next_gate: Literal["groq_cache_telemetry_reauthorization_activation"]

    @field_validator(
        "observation_plan_path",
        "review_path",
        "dry_run_report_path",
        "adr_path",
        "report_path",
    )
    @classmethod
    def validate_repo_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("manifest paths must be repository-relative")
        allowed = (
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-review-v1/",
            "docs/adr/",
            "docs/benchmark/",
        )
        if not value.startswith(allowed):
            raise ValueError("manifest paths must remain in approved review locations")
        return value

    @field_validator(
        "observation_plan_sha256",
        "review_sha256",
        "dry_run_report_sha256",
        "adr_sha256",
        "report_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest hashes must be lowercase SHA-256")
        return value

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest source_commit must be a full Git SHA")
        return value


class GroqCacheTelemetryReauthorizationSummary(BaseModel):
    """Safe CLI summary for validation or metadata-only dry run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "dry-run"]
    review_id: str
    status: GroqCacheTelemetryReauthorizationStatus
    decision: GroqCacheTelemetryReauthorizationDecision
    source_commit: str
    planned_attempt_count: int
    maximum_provider_calls: int
    observation_boundary_materially_different: bool
    raw_response_api_available: bool
    provider_call_performed: bool
    credential_accessed: bool
    provider_call_authorized: bool
    active_authorization_created: bool
    execution_command_available: bool
    reauthorization_execution_authorized: bool
    benchmark_execution_authorized: bool
    comparison_eligible: bool
    next_gate: str


class GroqCacheTelemetryReauthorizationErrorEnvelope(BaseModel):
    """Machine-readable safe failure emitted by the validator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()
