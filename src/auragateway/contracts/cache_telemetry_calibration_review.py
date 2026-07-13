"""Typed contracts for the inactive Groq cache calibration review."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class CalibrationReviewStatus(StrEnum):
    """Lifecycle state of the non-live authorization review."""

    REVIEW_READY_INACTIVE = "review_ready_inactive"


class CalibrationOutcome(StrEnum):
    """Predeclared future calibration outcome taxonomy."""

    TELEMETRY_OBSERVED_WITH_CACHE_HIT = "telemetry_observed_with_cache_hit"
    TELEMETRY_OBSERVED_WITHOUT_CACHE_HIT = "telemetry_observed_without_cache_hit"
    BILLING_CACHE_FIELD_UNAVAILABLE = "billing_cache_field_unavailable"
    CALIBRATION_EXECUTION_FAILED = "calibration_execution_failed"


class CalibrationDryRunStatus(StrEnum):
    """Deterministic review dry-run status."""

    PASSED_INACTIVE = "passed_inactive"


class CalibrationSourceBinding(BaseModel):
    """One immutable repository source bound by Git blob identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    git_blob_sha1: str

    @field_validator("git_blob_sha1")
    @classmethod
    def validate_git_blob_sha1(cls, value: str) -> str:
        if _GIT_SHA1_PATTERN.fullmatch(value) is None:
            raise ValueError("source bindings require lowercase Git SHA-1")
        return value


class ExternalProviderBoundary(BaseModel):
    """Provider documentation assumptions frozen for the review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    documentation_url: Literal["https://console.groq.com/docs/prompt-caching"]
    retrieved_on: Literal["2026-07-14"]
    supported_model: Literal["openai/gpt-oss-20b"]
    automatic_caching: Literal[True] = True
    exact_prefix_required: Literal[True] = True
    minimum_cacheable_token_range: tuple[int, int]
    cache_hit_guaranteed: Literal[False] = False
    cache_expiry_without_use_hours: Literal[2] = 2
    billing_cached_tokens_path: Literal["usage.prompt_tokens_details.cached_tokens"]
    cached_input_discount_percent: Literal[50] = 50

    @model_validator(mode="after")
    def validate_token_range(self) -> ExternalProviderBoundary:
        if self.minimum_cacheable_token_range != (128, 1024):
            raise ValueError("provider minimum token range must remain frozen")
        return self


class CalibrationProviderProfile(BaseModel):
    """Exact future provider request parameters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["groq"]
    model_alias: Literal["groq-gpt-oss-20b"]
    exact_model_identifier: Literal["openai/gpt-oss-20b"]
    adapter_version: Literal["groq-chat-completions-v1"]
    telemetry_capture_version: Literal["groq-cache-telemetry-capture-v1"]
    max_completion_tokens: Literal[32] = 32
    temperature: float = 0.0
    stream: Literal[False] = False
    store: Literal[False] = False
    reasoning_effort: Literal["low"] = "low"
    timeout_seconds: float = 30.0

    @model_validator(mode="after")
    def validate_exact_floats(self) -> CalibrationProviderProfile:
        if self.temperature != 0.0:
            raise ValueError("calibration temperature must remain zero")
        if self.timeout_seconds != 30.0:
            raise ValueError("calibration timeout must remain 30 seconds")
        return self


class CalibrationPromptBinding(BaseModel):
    """Public identity of the protected synthetic prompt bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    recipe_id: Literal["groq-cache-telemetry-calibration-prompt-v1"]
    system_prompt_byte_count: Literal[8192] = 8192
    user_prompt_byte_count: Literal[256] = 256
    total_prompt_byte_count: Literal[8448] = 8448
    conservative_input_token_estimate: Literal[2112] = 2112
    minimum_cacheable_token_upper_bound: Literal[1024] = 1024
    minimum_length_margin_tokens: Literal[1088] = 1088
    system_prompt_sha256: str
    user_prompt_sha256: str
    provider_request_sha256: str
    protected_bundle_path: Literal[
        ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    ]
    protected_bundle_sha256: str
    exact_provider_request_required: Literal[True] = True

    @field_validator(
        "system_prompt_sha256",
        "user_prompt_sha256",
        "provider_request_sha256",
        "protected_bundle_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("prompt bindings require lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_length_margin(self) -> CalibrationPromptBinding:
        if (
            self.conservative_input_token_estimate - self.minimum_cacheable_token_upper_bound
            != self.minimum_length_margin_tokens
        ):
            raise ValueError("minimum prompt-length margin is inconsistent")
        return self


class CalibrationSchedule(BaseModel):
    """Bounded three-call cold/warm/repeat schedule."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planned_attempt_count: Literal[3] = 3
    maximum_provider_calls: Literal[3] = 3
    attempt_offsets_seconds: tuple[int, int, int]
    minimum_planned_elapsed_seconds: Literal[20] = 20
    request_roles: tuple[
        Literal["cold"],
        Literal["warm_repeat_one"],
        Literal["warm_repeat_two"],
    ]
    all_provider_request_hashes_identical: Literal[True] = True
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    estimated_max_cost_microusd: Literal[600] = 600
    authorization_cost_ceiling_microusd: Literal[1000] = 1000

    @model_validator(mode="after")
    def validate_schedule(self) -> CalibrationSchedule:
        if self.attempt_offsets_seconds != (0, 10, 20):
            raise ValueError("calibration offsets must remain 0, 10, and 20")
        if self.request_roles != (
            "cold",
            "warm_repeat_one",
            "warm_repeat_two",
        ):
            raise ValueError("calibration request roles are out of order")
        if self.estimated_max_cost_microusd > self.authorization_cost_ceiling_microusd:
            raise ValueError("planned cost exceeds the review ceiling")
        return self


class CalibrationEvidencePaths(BaseModel):
    """Future public and protected evidence destinations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    public_journal_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-v1/journal.jsonl"
    ]
    public_run_records_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-v1/run_records.json"
    ]
    public_report_path: Literal["data/evals/benchmark/cache-telemetry-calibration-v1/report.json"]
    public_manifest_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-v1/manifest.json"
    ]
    protected_output_path: Literal[
        ".local/benchmark/cache-telemetry-calibration-v1/provider_outputs.jsonl"
    ]
    protected_prompt_bundle_path: Literal[
        ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    ]


class CalibrationStopPolicy(BaseModel):
    """Fail-closed future calibration trajectory regulation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_error_stops_calibration: Literal[True] = True
    request_identity_mismatch_stops_before_call: Literal[True] = True
    telemetry_shape_missing_stops_calibration: Literal[True] = True
    public_evidence_write_failure_stops_calibration: Literal[True] = True
    protected_output_write_failure_stops_calibration: Literal[True] = True
    budget_exhaustion_stops_calibration: Literal[True] = True
    privacy_violation_stops_calibration: Literal[True] = True
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False


class CalibrationOutcomeRule(BaseModel):
    """One future outcome rule with explicit claim limits."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: CalibrationOutcome
    requirements: tuple[str, ...] = Field(min_length=1)
    provider_cache_usage_claim_permitted_for_calibration: bool
    benchmark_claims_permitted: Literal[False] = False


class CacheTelemetryCalibrationReview(BaseModel):
    """Frozen inactive authorization review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["groq-cache-telemetry-calibration-review-v1"]
    status: Literal[CalibrationReviewStatus.REVIEW_READY_INACTIVE] = (
        CalibrationReviewStatus.REVIEW_READY_INACTIVE
    )
    source_commit: Literal["2de6767d02fa309849f5583d7dd67963618a00a1"]
    source_hardening_id: Literal["groq-cache-telemetry-hardening-v1"]
    calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    source_bindings: tuple[CalibrationSourceBinding, ...] = Field(
        min_length=8,
        max_length=8,
    )
    external_provider_boundary: ExternalProviderBoundary
    provider_profile: CalibrationProviderProfile
    prompt_binding: CalibrationPromptBinding
    schedule: CalibrationSchedule
    evidence_paths: CalibrationEvidencePaths
    stop_policy: CalibrationStopPolicy
    outcome_taxonomy: tuple[CalibrationOutcomeRule, ...] = Field(
        min_length=4,
        max_length=4,
    )
    provider_call_authorized: Literal[False] = False
    active_authorization_created: Literal[False] = False
    execution_command_available: Literal[False] = False
    credential_required_for_review: Literal[False] = False
    credential_accessed: Literal[False] = False
    calibration_execution_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal["cache_telemetry_calibration_activation"] = (
        "cache_telemetry_calibration_activation"
    )

    @model_validator(mode="after")
    def validate_review(self) -> CacheTelemetryCalibrationReview:
        paths = [item.path for item in self.source_bindings]
        if len(paths) != len(set(paths)):
            raise ValueError("source binding paths must be unique")
        outcomes = [item.outcome for item in self.outcome_taxonomy]
        if set(outcomes) != set(CalibrationOutcome):
            raise ValueError("review requires all calibration outcomes")
        if len(outcomes) != len(set(outcomes)):
            raise ValueError("calibration outcomes must be unique")
        if (
            self.prompt_binding.protected_bundle_path
            != self.evidence_paths.protected_prompt_bundle_path
        ):
            raise ValueError("protected prompt paths must match")
        return self


class CalibrationDryRunAttempt(BaseModel):
    """One metadata-only planned calibration attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_index: int = Field(ge=0, le=2)
    request_role: Literal[
        "cold",
        "warm_repeat_one",
        "warm_repeat_two",
    ]
    planned_offset_seconds: int = Field(ge=0, le=20)
    provider_request_sha256: str
    system_prompt_sha256: str
    user_prompt_sha256: str
    total_prompt_byte_count: Literal[8448] = 8448
    conservative_input_token_estimate: Literal[2112] = 2112
    max_completion_tokens: Literal[32] = 32
    provider_call_permitted: Literal[False] = False

    @field_validator(
        "provider_request_sha256",
        "system_prompt_sha256",
        "user_prompt_sha256",
    )
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run attempts require lowercase SHA-256")
        return value


class CalibrationDryRunReport(BaseModel):
    """Deterministic non-live schedule proof."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["groq-cache-telemetry-calibration-review-v1"]
    calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    status: Literal[CalibrationDryRunStatus.PASSED_INACTIVE] = (
        CalibrationDryRunStatus.PASSED_INACTIVE
    )
    planned_attempt_count: Literal[3] = 3
    unique_provider_request_count: Literal[1] = 1
    repeated_provider_request_count: Literal[2] = 2
    minimum_planned_elapsed_seconds: Literal[20] = 20
    estimated_max_cost_microusd: Literal[600] = 600
    authorization_cost_ceiling_microusd: Literal[1000] = 1000
    attempts: tuple[CalibrationDryRunAttempt, ...] = Field(
        min_length=3,
        max_length=3,
    )
    all_provider_request_hashes_identical: Literal[True] = True
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    execution_command_available: Literal[False] = False
    calibration_execution_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_attempts(self) -> CalibrationDryRunReport:
        if [item.attempt_index for item in self.attempts] != [0, 1, 2]:
            raise ValueError("dry-run attempt indexes must be contiguous")
        if [item.planned_offset_seconds for item in self.attempts] != [
            0,
            10,
            20,
        ]:
            raise ValueError("dry-run attempt offsets are inconsistent")
        request_hashes = {item.provider_request_sha256 for item in self.attempts}
        if len(request_hashes) != 1:
            raise ValueError("all calibration requests must be identical")
        return self


class CalibrationPromptRecipe(BaseModel):
    """Public deterministic recipe for the protected prompt bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    recipe_id: Literal["groq-cache-telemetry-calibration-prompt-v1"]
    calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    content_class: Literal["synthetic_ascii_only"]
    system_prompt_byte_count: Literal[8192] = 8192
    user_prompt_byte_count: Literal[256] = 256
    total_prompt_byte_count: Literal[8448] = 8448
    conservative_input_token_estimate: Literal[2112] = 2112
    minimum_cacheable_token_upper_bound: Literal[1024] = 1024
    minimum_length_margin_tokens: Literal[1088] = 1088
    system_prompt_sha256: str
    user_prompt_sha256: str
    provider_request_sha256: str
    protected_bundle_path: Literal[
        ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    ]
    protected_bundle_sha256: str
    provider_request_repetition_count: Literal[3] = 3
    exact_provider_request_required: Literal[True] = True
    raw_prompt_committed: Literal[False] = False
    provider_call_authorized: Literal[False] = False

    @field_validator(
        "system_prompt_sha256",
        "user_prompt_sha256",
        "provider_request_sha256",
        "protected_bundle_sha256",
    )
    @classmethod
    def validate_recipe_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("prompt recipe requires lowercase SHA-256")
        return value


class CalibrationReviewManifest(BaseModel):
    """Integrity manifest for the inactive calibration review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["groq-cache-telemetry-calibration-review-v1"]
    prompt_recipe_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-review-v1/prompt_recipe.json"
    ]
    prompt_recipe_sha256: str
    review_path: Literal["data/evals/benchmark/cache-telemetry-calibration-review-v1/review.json"]
    review_sha256: str
    dry_run_report_path: Literal[
        "data/evals/benchmark/cache-telemetry-calibration-review-v1/dry_run_report.json"
    ]
    dry_run_report_sha256: str
    report_path: Literal[
        "docs/benchmark/AuraGateway_Cache_Telemetry_Calibration_Authorization_Review.md"
    ]
    report_sha256: str
    protected_bundle_sha256: str
    provider_call_authorized: Literal[False] = False
    execution_command_available: Literal[False] = False
    calibration_execution_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    next_gate: Literal["cache_telemetry_calibration_activation"] = (
        "cache_telemetry_calibration_activation"
    )

    @field_validator(
        "prompt_recipe_sha256",
        "review_sha256",
        "dry_run_report_sha256",
        "report_sha256",
        "protected_bundle_sha256",
    )
    @classmethod
    def validate_manifest_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("review manifest requires lowercase SHA-256")
        return value


class CalibrationReviewSummary(BaseModel):
    """Metadata-safe CLI summary for review commands."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["materialize", "validate", "dry-run", "verify"]
    review_id: str
    status: CalibrationReviewStatus
    planned_attempt_count: Literal[3] = 3
    unique_provider_request_count: Literal[1] = 1
    protected_bundle_verified: bool
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    execution_command_available: Literal[False] = False
    calibration_execution_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    next_gate: Literal["cache_telemetry_calibration_activation"] = (
        "cache_telemetry_calibration_activation"
    )
