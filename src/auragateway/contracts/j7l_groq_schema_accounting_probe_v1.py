"""Typed contracts for the inactive J7L Groq schema-accounting probe review."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SchemaAccountingProbePlanV1(FrozenModel):
    schema_version: Literal["1.0.0"]
    plan_id: Literal["j7l-groq-schema-accounting-observation-v1"]
    review_id: Literal["j7l-groq-schema-accounting-review-v1"]
    provider: Literal["groq"]
    exact_model_identifier: Literal["openai/gpt-oss-20b"]
    installed_sdk_version_required: Literal["1.5.0"]
    resource_path: Literal["client.chat.completions.with_raw_response.create"]
    prompt_recipe_path: str
    prompt_recipe_sha256: str
    strict_response_schema_path: str
    strict_response_schema_sha256: str
    maximum_completion_tokens: Literal[32]
    temperature_milli: Literal[0]
    streaming: Literal[False]
    storage: Literal[False]
    reasoning_effort: Literal["low"]
    timeout_seconds: Literal[30]
    planned_attempt_count: Literal[2]
    maximum_provider_calls: Literal[2]
    attempt_offsets_seconds: tuple[Literal[0], Literal[10]]
    request_roles: tuple[
        Literal["control_no_response_format"],
        Literal["strict_json_schema"],
    ]
    messages_identical_across_attempts: Literal[True]
    only_response_format_may_differ: Literal[True]
    control_response_format_present: Literal[False]
    strict_response_format_present: Literal[True]
    strict_mode: Literal[True]
    usage_prompt_tokens_required: Literal[True]
    usage_completion_tokens_required: Literal[True]
    usage_total_tokens_observed_if_present: Literal[True]
    rate_limit_headers_observed_if_present: Literal[True]
    raw_response_protected_local_required: Literal[True]
    public_raw_payload_permitted: Literal[False]
    protected_raw_responses_path: str
    protected_parsed_responses_path: str
    retry_permitted: Literal[False]
    resume_permitted: Literal[False]
    rerun_permitted: Literal[False]
    free_tier_required: Literal[True]
    paid_fallback_permitted: Literal[False]
    external_spend_ceiling_zar: Literal[0]
    j7l_reference_request_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    provider_call_authorized: Literal[False]
    execution_command_available: Literal[False]
    activation_required: Literal[True]

    @field_validator(
        "prompt_recipe_sha256",
        "strict_response_schema_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("probe hashes must be lowercase SHA-256")
        return value

    @field_validator(
        "prompt_recipe_path",
        "strict_response_schema_path",
        "protected_raw_responses_path",
        "protected_parsed_responses_path",
    )
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("probe paths must be repository-relative")
        return value

    @model_validator(mode="after")
    def validate_experiment(self) -> Self:
        if self.maximum_provider_calls != self.planned_attempt_count:
            raise ValueError("provider-call ceiling must equal the frozen attempt count")
        if self.protected_raw_responses_path == self.protected_parsed_responses_path:
            raise ValueError("raw and parsed protected evidence paths must differ")
        return self


class PreActivationMeasurementsV1(FrozenModel):
    schema_version: Literal["1.0.0"]
    measurement_id: Literal["j7l-groq-preactivation-measurements-v1"]
    evidence_origin: Literal["operator_observed_local_and_provider_preflight"]
    measured_on: Literal["2026-09-20"]
    openai_harmony_version: Literal["0.0.8"]
    groq_sdk_version: Literal["1.5.0"]
    model_projection_only_tokens: Literal[9452]
    canonical_registry_only_tokens: Literal[7027]
    case_count: Literal[48]
    minimum_registry_plus_case_tokens: Literal[7184]
    minimum_token_case_id: Literal["j7l-dev-040"]
    maximum_registry_plus_case_tokens: Literal[7310]
    maximum_token_case_id: Literal["j7l-dev-014"]
    cases_registry_plus_case_at_or_above_8000: Literal[0]
    minimum_exact_message_tokens: Literal[7322]
    maximum_exact_message_tokens: Literal[7448]
    maximum_exact_message_case_id: Literal["j7l-dev-014"]
    maximum_conservative_with_schema_tokens: Literal[7916]
    maximum_conservative_case_id: Literal["j7l-dev-014"]
    planned_reference_output_budget_tokens: Literal[384]
    maximum_conservative_plus_output_budget_tokens: Literal[8300]
    cases_conservative_plus_output_at_or_above_8000: Literal[48]
    models_preflight_http_status: Literal[200]
    target_model_present: Literal[True]
    target_model_active: Literal[True]
    target_model_context_window: Literal[131072]
    models_endpoint_token_limit_header_present: Literal[False]
    organization_rpm_observed: Literal[30]
    organization_rpd_observed: Literal[1000]
    organization_tpm_observed: Literal[8000]
    organization_tpd_observed: Literal[200000]
    project_limit_can_exceed_organization_limit: Literal[False]
    accounting_question_unresolved: Literal[True]

    @model_validator(mode="after")
    def validate_measurements(self) -> Self:
        total = (
            self.maximum_conservative_with_schema_tokens
            + self.planned_reference_output_budget_tokens
        )
        if total != self.maximum_conservative_plus_output_budget_tokens:
            raise ValueError("conservative token envelope arithmetic drifted")
        if self.maximum_exact_message_tokens >= self.organization_tpm_observed:
            raise ValueError("exact message unexpectedly exceeds observed organization TPM")
        if self.maximum_conservative_plus_output_budget_tokens <= (self.organization_tpm_observed):
            raise ValueError("probe is not justified by the frozen token-limit conflict")
        return self


class SchemaAccountingProbeReviewV1(FrozenModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal["j7l-groq-schema-accounting-review-v1"]
    status: Literal["review_ready_inactive"]
    decision: Literal["schema_accounting_probe_review_ready_inactive"]
    source_commit: str
    successor_constitution_sha256: str
    semantic_registry_sha256: str
    model_projection_sha256: str
    probe_plan_sha256: str
    preactivation_measurements_sha256: str
    strict_response_schema_sha256: str
    synthetic_prompt_recipe_sha256: str
    provider_facts: dict[str, JsonValue]
    information_gain_question: str = Field(min_length=40, max_length=500)
    primary_decision_rule: dict[str, str]
    claim_boundary: dict[str, bool]
    provider_call_performed: Literal[False]
    credential_required_for_review: Literal[False]
    credential_accessed: Literal[False]
    provider_call_authorized: Literal[False]
    active_authorization_created: Literal[False]
    execution_command_available: Literal[False]
    j7l_reference_request_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    external_spend_ceiling_zar: Literal[0]
    next_gate: Literal["J7L_GROQ_SCHEMA_ACCOUNTING_PROBE_ACTIVATION_V1"]

    @field_validator(
        "successor_constitution_sha256",
        "semantic_registry_sha256",
        "model_projection_sha256",
        "probe_plan_sha256",
        "preactivation_measurements_sha256",
        "strict_response_schema_sha256",
        "synthetic_prompt_recipe_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("review hashes must be lowercase SHA-256")
        return value

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("source_commit must be a full lowercase Git commit SHA")
        return value

    @model_validator(mode="after")
    def validate_claim_boundary(self) -> Self:
        expected = {
            "positive_prompt_delta_closes_current_groq_j7l_shape": True,
            "zero_prompt_delta_proves_schema_free_rate_accounting": False,
            "zero_prompt_delta_requires_full_size_synthetic_qualification": True,
            "j7l_reference_execution_authorized": False,
            "groq_reference_judge_binding_frozen": False,
        }
        if self.claim_boundary != expected:
            raise ValueError("schema-accounting claim boundary drifted")
        return self


class SchemaAccountingDryRunAttemptV1(FrozenModel):
    attempt_index: int = Field(ge=0, le=1)
    role: Literal["control_no_response_format", "strict_json_schema"]
    planned_offset_seconds: int = Field(ge=0, le=10)
    prompt_recipe_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_format_present: bool
    strict_response_schema_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )


class SchemaAccountingDryRunReportV1(FrozenModel):
    schema_version: Literal["1.0.0"]
    dry_run_id: Literal["j7l-groq-schema-accounting-dry-run-v1"]
    status: Literal["dry_run_pass"]
    attempts: tuple[
        SchemaAccountingDryRunAttemptV1,
        SchemaAccountingDryRunAttemptV1,
    ]
    messages_identical_across_attempts: Literal[True]
    provider_call_performed: Literal[False]
    credential_accessed: Literal[False]
    execution_command_available: Literal[False]

    @model_validator(mode="after")
    def validate_attempts(self) -> Self:
        control, strict = self.attempts
        if (control.attempt_index, strict.attempt_index) != (0, 1):
            raise ValueError("dry-run attempts must remain in frozen order")
        if control.role != "control_no_response_format":
            raise ValueError("first dry-run attempt must be the control")
        if strict.role != "strict_json_schema":
            raise ValueError("second dry-run attempt must use strict schema")
        if control.response_format_present:
            raise ValueError("control must omit response_format")
        if control.strict_response_schema_sha256 is not None:
            raise ValueError("control must not bind the strict response schema")
        if not strict.response_format_present:
            raise ValueError("strict attempt must include response_format")
        if strict.strict_response_schema_sha256 is None:
            raise ValueError("strict attempt must bind the response schema")
        if control.prompt_recipe_sha256 != strict.prompt_recipe_sha256:
            raise ValueError("both attempts must bind byte-identical messages")
        return self


class SchemaAccountingReviewManifestV1(FrozenModel):
    schema_version: Literal["1.0.0"]
    manifest_id: Literal["j7l-groq-schema-accounting-review-manifest-v1"]
    status: Literal["frozen_inactive"]
    source_commit: str
    probe_plan_path: str
    probe_plan_sha256: str
    review_path: str
    review_sha256: str
    dry_run_report_path: str
    dry_run_report_sha256: str
    strict_response_schema_path: str
    strict_response_schema_sha256: str
    synthetic_prompt_recipe_path: str
    synthetic_prompt_recipe_sha256: str
    preactivation_measurements_path: str
    preactivation_measurements_sha256: str
    adr_path: str
    adr_sha256: str
    report_path: str
    report_sha256: str
    provider_call_authorized: Literal[False]
    execution_command_available: Literal[False]
    j7l_reference_request_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    next_gate: Literal["J7L_GROQ_SCHEMA_ACCOUNTING_PROBE_ACTIVATION_V1"]

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest source commit must be a full SHA")
        return value

    @field_validator(
        "probe_plan_sha256",
        "review_sha256",
        "dry_run_report_sha256",
        "strict_response_schema_sha256",
        "synthetic_prompt_recipe_sha256",
        "preactivation_measurements_sha256",
        "adr_sha256",
        "report_sha256",
    )
    @classmethod
    def validate_manifest_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest hashes must be lowercase SHA-256")
        return value

    @field_validator(
        "probe_plan_path",
        "review_path",
        "dry_run_report_path",
        "strict_response_schema_path",
        "synthetic_prompt_recipe_path",
        "preactivation_measurements_path",
        "adr_path",
        "report_path",
    )
    @classmethod
    def validate_manifest_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("manifest paths must be repository-relative")
        return value
