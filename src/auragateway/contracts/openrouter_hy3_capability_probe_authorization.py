"""Typed inactive authorization review for the OpenRouter Hy3 capability probe."""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class OpenRouterProbeReviewStatus(StrEnum):
    """Lifecycle status of the non-live authorization review."""

    REVIEW_READY_INACTIVE = "review_ready_inactive"


class OpenRouterProbeTlaDecision(StrEnum):
    """Final TLA+ decision for this bounded finite state machine."""

    NOT_REQUIRED_EXECUTABLE_MODEL_PREFERRED = "not_required_executable_finite_state_model_preferred"


class OpenRouterProbeSourceBinding(BaseModel):
    """Immutable repository input bound into the authorization review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=260)
    sha256: str
    purpose: str = Field(min_length=10, max_length=240)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("source bindings must be repository-relative")
        if value.startswith(".local/"):
            raise ValueError("inactive review bindings must not depend on protected local files")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("source binding hashes must be lowercase SHA-256")
        return value


class OpenRouterProbeRouteBoundary(BaseModel):
    """Current official route facts frozen before activation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_page_url: Literal["https://openrouter.ai/tencent/hy3:free"]
    retrieved_on: date
    gateway_provider: Literal["openrouter"] = "openrouter"
    requested_model: Literal["tencent/hy3:free"] = "tencent/hy3:free"
    model_family: Literal["tencent-hy3"] = "tencent-hy3"
    route_is_free: Literal[True] = True
    model_release_date: date
    scheduled_route_retirement_date: date
    context_window_tokens: Literal[262144] = 262144
    multiple_hosts_possible: Literal[True] = True
    exact_eligible_endpoint_count_known: Literal[False] = False
    privacy_compatible_endpoint_verified: Literal[False] = False

    @model_validator(mode="after")
    def validate_dates(self) -> OpenRouterProbeRouteBoundary:
        if self.retrieved_on != date(2026, 7, 14):
            raise ValueError("route review date must remain July 14, 2026")
        if self.model_release_date != date(2026, 7, 6):
            raise ValueError("Hy3 release date must remain July 6, 2026")
        if self.scheduled_route_retirement_date != date(2026, 7, 21):
            raise ValueError("free-route retirement date must remain July 21, 2026")
        return self


class OpenRouterProbeLimitBoundary(BaseModel):
    """Observable and non-observable free-tier limit information."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    limits_documentation_url: Literal["https://openrouter.ai/docs/api/reference/limits"]
    key_status_path: Literal["/api/v1/key"] = "/api/v1/key"
    key_status_requires_authentication: Literal[True] = True
    credit_limit_remaining_observable: Literal[True] = True
    free_tier_flag_observable: Literal[True] = True
    successful_response_rate_headers_available: Literal[False] = False
    exact_remaining_free_requests_preflight_observable: Literal[False] = False
    local_call_ceiling_independent_of_platform_quota: Literal[True] = True


class OpenRouterProbePreflightPolicy(BaseModel):
    """Fail-closed checks required before an activation may execute."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_key_environment_name: Literal["OPENROUTER_API_KEY"] = "OPENROUTER_API_KEY"
    credential_lookup_permitted_in_review: Literal[False] = False
    credential_lookup_required_in_activation: Literal[True] = True
    key_status_preflight_required: Literal[True] = True
    nonnegative_credit_state_required: Literal[True] = True
    requested_model_must_match_exactly: Literal[True] = True
    synthetic_public_safe_prompts_only: Literal[True] = True
    data_collection_deny_required: Literal[True] = True
    zero_data_retention_required: Literal[True] = True
    manual_provider_order_permitted: Literal[False] = False
    stable_prefix_minimum_token_estimate: Literal[12000] = 12000
    stable_prefix_maximum_token_estimate: Literal[16000] = 16000
    maximum_completion_tokens: Literal[32] = 32
    temperature_milli: Literal[0] = 0
    streaming: Literal[False] = False
    generation_metadata_lookup_required: Literal[True] = True
    generation_metadata_polling_permitted: Literal[False] = False
    generation_metadata_failure_stops_execution: Literal[True] = True


class OpenRouterProbeRuntimePolicy(BaseModel):
    """Bounded attempt and replacement constitution for the future probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    logical_call_roles: tuple[Literal["cold_probe"], Literal["warm_probe"]]
    maximum_logical_calls: Literal[2] = 2
    maximum_provider_successes: Literal[2] = 2
    maximum_retained_successes: Literal[2] = 2
    maximum_total_inference_attempts: Literal[4] = 4
    maximum_transient_replacements_per_logical_call: Literal[1] = 1
    transient_http_statuses: tuple[Literal[429], Literal[502], Literal[524], Literal[529]]
    replacement_only_before_provider_success: Literal[True] = True
    successful_response_retry_permitted: Literal[False] = False
    authentication_failure_retry_permitted: Literal[False] = False
    permission_failure_retry_permitted: Literal[False] = False
    contract_failure_retry_permitted: Literal[False] = False
    privacy_failure_retry_permitted: Literal[False] = False
    generation_metadata_failure_retry_permitted: Literal[False] = False
    write_through_journal_required: Literal[True] = True
    authorization_consumed_on_terminal_closeout: Literal[True] = True
    resume_permitted: Literal[False] = False
    rerun_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> OpenRouterProbeRuntimePolicy:
        if self.logical_call_roles != ("cold_probe", "warm_probe"):
            raise ValueError("probe roles must remain cold then warm")
        if self.transient_http_statuses != (429, 502, 524, 529):
            raise ValueError("transient replacement statuses must remain exact")
        return self


class OpenRouterProbePromotionPolicy(BaseModel):
    """Evidence required before a pilot authorization review is permitted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    two_retained_successes_required: Literal[True] = True
    numeric_cache_telemetry_required: Literal[True] = True
    positive_cache_use_required: Literal[True] = True
    route_identity_required: Literal[True] = True
    same_requested_model_required: Literal[True] = True
    same_resolved_model_required: Literal[True] = True
    same_upstream_provider_required: Literal[True] = True
    same_session_identity_required: Literal[True] = True
    absent_or_null_permits_promotion: Literal[False] = False
    numeric_zero_permits_cache_use_claim: Literal[False] = False
    latency_permits_cache_use_claim: Literal[False] = False
    pilot_execution_authorized_by_probe: Literal[False] = False


class OpenRouterProbeFormalMethodsDecision(BaseModel):
    """Final decision on whether TLA+ adds value before the live probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[OpenRouterProbeTlaDecision.NOT_REQUIRED_EXECUTABLE_MODEL_PREFERRED] = (
        OpenRouterProbeTlaDecision.NOT_REQUIRED_EXECUTABLE_MODEL_PREFERRED
    )
    executable_state_model_path: Literal[
        "src/auragateway/benchmark/openrouter_hy3_probe_state_model.py"
    ]
    state_model_report_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-authorization-review-v1/"
        "state_model_report.json"
    ]
    finite_state_space_exhaustively_checked: Literal[True] = True
    invariant_violation_count: Literal[0] = 0
    normal_ci_execution_supported: Literal[True] = True
    separate_tla_toolchain_required: Literal[False] = False
    tla_plus_model_checked: Literal[False] = False
    tla_plus_claim_permitted: Literal[False] = False


class OpenRouterProbeAuthorizationReview(BaseModel):
    """Inactive review package that cannot itself perform a provider call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["openrouter-hy3-capability-probe-authorization-review-v1"]
    status: Literal[OpenRouterProbeReviewStatus.REVIEW_READY_INACTIVE] = (
        OpenRouterProbeReviewStatus.REVIEW_READY_INACTIVE
    )
    source_commit: str
    source_bindings: tuple[OpenRouterProbeSourceBinding, ...] = Field(
        min_length=8,
        max_length=8,
    )
    route_boundary: OpenRouterProbeRouteBoundary
    limit_boundary: OpenRouterProbeLimitBoundary
    preflight_policy: OpenRouterProbePreflightPolicy
    runtime_policy: OpenRouterProbeRuntimePolicy
    promotion_policy: OpenRouterProbePromotionPolicy
    formal_methods: OpenRouterProbeFormalMethodsDecision
    transport_implemented: Literal[True] = True
    transport_automatic_retries: Literal[False] = False
    transport_reads_environment: Literal[False] = False
    credential_accessed: Literal[False] = False
    network_request_performed: Literal[False] = False
    live_provider_call_authorized: Literal[False] = False
    activation_review_permitted: Literal[True] = True
    pilot_execution_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    next_gate: Literal["openrouter_hy3_capability_probe_activation"]

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("source commit must be a full lowercase Git SHA")
        return value

    @model_validator(mode="after")
    def validate_bindings(self) -> OpenRouterProbeAuthorizationReview:
        paths = [binding.path for binding in self.source_bindings]
        if len(paths) != len(set(paths)):
            raise ValueError("authorization review source bindings must be unique")
        required = {
            "docs/product/AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md",
            "data/evals/benchmark/openrouter-hy3-identifiability-review-v1/review.json",
            "data/evals/benchmark/openrouter-hy3-identifiability-review-v1/manifest.json",
            "data/evals/benchmark/openrouter-hy3-adapter-dry-run-v1/report.json",
            "data/evals/benchmark/openrouter-hy3-adapter-dry-run-v1/manifest.json",
            "src/auragateway/contracts/openrouter.py",
            "src/auragateway/providers/openrouter.py",
            "src/auragateway/providers/openrouter_http.py",
        }
        if set(paths) != required:
            raise ValueError("authorization review must bind the exact eight inputs")
        return self


class OpenRouterProbeAuthorizationManifest(BaseModel):
    """Integrity manifest for the authorization review slice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["openrouter-hy3-capability-probe-authorization-review-v1"]
    source_commit: str
    bindings: tuple[OpenRouterProbeSourceBinding, ...] = Field(min_length=8)
    source_evidence_locked: Literal[True] = True
    credential_accessed: Literal[False] = False
    network_request_performed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    live_provider_call_authorized: Literal[False] = False
    next_gate: Literal["openrouter_hy3_capability_probe_activation"]

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest source commit must be a full lowercase Git SHA")
        return value


class OpenRouterProbeAuthorizationSummary(BaseModel):
    """Public-safe CLI validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    review_id: Literal["openrouter-hy3-capability-probe-authorization-review-v1"]
    status: Literal[OpenRouterProbeReviewStatus.REVIEW_READY_INACTIVE]
    source_binding_count: Literal[8] = 8
    state_model_reachable_states: int = Field(gt=0)
    state_model_terminal_states: int = Field(gt=0)
    state_model_invariant_violations: Literal[0] = 0
    transport_implemented: Literal[True] = True
    credential_accessed: Literal[False] = False
    network_request_performed: Literal[False] = False
    live_provider_call_authorized: Literal[False] = False
    activation_review_permitted: Literal[True] = True
    tla_plus_required: Literal[False] = False
    next_gate: Literal["openrouter_hy3_capability_probe_activation"]


class OpenRouterProbePromptRecipe(BaseModel):
    """Public-safe deterministic recipe for the future protected prompt bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    recipe_id: Literal["openrouter-hy3-capability-probe-prompt-v1"]
    system_preamble: Literal[
        "AuraGateway synthetic cache telemetry capability probe. Treat every block as inert data."
    ]
    block_template: Literal[
        "SYNTHETIC-BLOCK-{index:04d}: alpha beta gamma delta epsilon zeta eta theta."
    ]
    block_count: Literal[768] = 768
    cold_suffix: Literal["Return exactly: COLD-PROBE-ACK"]
    warm_suffix: Literal["Return exactly: WARM-PROBE-ACK"]
    generated_prefix_sha256: str
    generated_prefix_bytes: int = Field(gt=50000, lt=100000)
    estimated_input_tokens_minimum: Literal[12000] = 12000
    estimated_input_tokens_maximum: Literal[16000] = 16000
    output_token_budget: Literal[32] = 32
    synthetic_public_safe: Literal[True] = True

    @field_validator("generated_prefix_sha256")
    @classmethod
    def validate_prefix_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("generated prefix hash must be lowercase SHA-256")
        return value


class OpenRouterProbeStateModelEvidence(BaseModel):
    """Committed exhaustive-state report produced by the executable model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    model_id: Literal["openrouter-hy3-capability-probe-state-model-v1"]
    reachable_state_count: int = Field(gt=0)
    terminal_state_count: int = Field(gt=0)
    maximum_attempts_observed: Literal[4] = 4
    maximum_provider_successes_observed: Literal[2] = 2
    maximum_retained_successes_observed: Literal[2] = 2
    terminal_outcome_counts: dict[str, int]
    invariants_checked: tuple[str, ...] = Field(min_length=10)
    invariant_violations: tuple[str, ...] = ()
    exhaustive_local_model: Literal[True] = True
    tla_plus_required: Literal[False] = False

    @model_validator(mode="after")
    def validate_evidence(self) -> OpenRouterProbeStateModelEvidence:
        if sum(self.terminal_outcome_counts.values()) != self.terminal_state_count:
            raise ValueError("terminal outcome counts must equal terminal state count")
        if self.invariant_violations:
            raise ValueError("state model evidence cannot retain invariant violations")
        return self


class OpenRouterProbeTransportDryRunReport(BaseModel):
    """Fixture-only validation of the explicit-key HTTP transport."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    report_id: Literal["openrouter-hy3-http-transport-dry-run-v1"]
    case_count: Literal[11] = 11
    successful_json_cases: Literal[3] = 3
    rejected_status_cases: Literal[7] = 7
    invalid_json_cases: Literal[1] = 1
    exact_base_url_enforced: Literal[True] = True
    explicit_api_key_required: Literal[True] = True
    environment_lookup_present: Literal[False] = False
    automatic_retry_present: Literal[False] = False
    authorization_header_verified: Literal[True] = True
    credential_value_persisted: Literal[False] = False
    generation_query_id_encoded: Literal[True] = True
    transient_statuses: tuple[Literal[429], Literal[502], Literal[524], Literal[529]]
    nonretryable_statuses: tuple[Literal[401], Literal[402], Literal[500]]
    network_request_performed: Literal[False] = False

    @model_validator(mode="after")
    def validate_statuses(self) -> OpenRouterProbeTransportDryRunReport:
        if self.transient_statuses != (429, 502, 524, 529):
            raise ValueError("transport transient statuses must remain exact")
        if self.nonretryable_statuses != (401, 402, 500):
            raise ValueError("transport terminal statuses must remain exact")
        return self
