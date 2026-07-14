"""Typed non-live identifiability review for OpenRouter-hosted Hy3."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class OpenRouterHy3ReviewStatus(StrEnum):
    """Lifecycle state of the bounded non-live review."""

    REVIEW_READY_INACTIVE = "review_ready_inactive"


class OpenRouterHy3TelemetryAuthority(StrEnum):
    """Authority represented by cache and route metadata."""

    OPENROUTER_NORMALIZED_USAGE = "openrouter_normalized_usage"


class OpenRouterHy3ConditionId(StrEnum):
    """Frozen experimental conditions."""

    CONDITION_A = "condition_a"
    CONDITION_B = "condition_b"
    CONDITION_C = "condition_c"


class OpenRouterHy3ClaimKind(StrEnum):
    """Claims explicitly permitted or blocked by the review."""

    FREE_ROUTE_AVAILABLE_TIME_LIMITED = "free_route_available_time_limited"
    NORMALIZED_CACHE_SCHEMA_DOCUMENTED = "normalized_cache_schema_documented"
    EXPLICIT_SESSION_STICKINESS_DOCUMENTED = "explicit_session_stickiness_documented"
    GENERATION_ROUTE_METADATA_DOCUMENTED = "generation_route_metadata_documented"
    CONDITION_A_B_DESIGN_IDENTIFIABLE = "condition_a_b_design_identifiable"
    CONDITION_B_C_DESIGN_IDENTIFIABLE = "condition_b_c_design_identifiable"
    HY3_FREE_NUMERIC_CACHE_TELEMETRY = "hy3_free_numeric_cache_telemetry"
    HY3_FREE_CACHE_USE = "hy3_free_cache_use"
    CONDITION_C_EFFECT = "condition_c_effect"
    MULTIPLE_ELIGIBLE_ENDPOINTS = "multiple_eligible_endpoints"
    PRIVACY_COMPATIBLE_ENDPOINT_AVAILABLE = "privacy_compatible_endpoint_available"
    BENCHMARK_ELIGIBILITY = "benchmark_eligibility"


class OpenRouterHy3ClaimDecision(StrEnum):
    """Machine-readable claim decision."""

    PERMITTED = "permitted"
    BLOCKED = "blocked"


class OpenRouterHy3ClaimReason(StrEnum):
    """Evidence reasons for claim decisions."""

    OFFICIAL_ROUTE_PAGE_OBSERVED = "OFFICIAL_ROUTE_PAGE_OBSERVED"
    OFFICIAL_CACHE_SCHEMA_DOCUMENTED = "OFFICIAL_CACHE_SCHEMA_DOCUMENTED"
    OFFICIAL_SESSION_ROUTING_DOCUMENTED = "OFFICIAL_SESSION_ROUTING_DOCUMENTED"
    OFFICIAL_GENERATION_METADATA_DOCUMENTED = "OFFICIAL_GENERATION_METADATA_DOCUMENTED"
    EXPERIMENTAL_CONTROL_FROZEN = "EXPERIMENTAL_CONTROL_FROZEN"
    LIVE_RESPONSE_NOT_OBSERVED = "LIVE_RESPONSE_NOT_OBSERVED"
    LIVE_CACHE_USE_NOT_OBSERVED = "LIVE_CACHE_USE_NOT_OBSERVED"
    COMPARISON_NOT_EXECUTED = "COMPARISON_NOT_EXECUTED"
    ENDPOINT_COUNT_NOT_VERIFIED = "ENDPOINT_COUNT_NOT_VERIFIED"
    PRIVACY_ROUTE_NOT_PREFLIGHTED = "PRIVACY_ROUTE_NOT_PREFLIGHTED"
    CAPABILITY_GATE_NOT_PASSED = "CAPABILITY_GATE_NOT_PASSED"


class OpenRouterHy3NextGate(StrEnum):
    """Next gate selected by the non-live review."""

    OPENROUTER_PROVIDER_ADAPTER_DRY_RUN = "openrouter_provider_adapter_dry_run"


class OpenRouterHy3SourceBinding(BaseModel):
    """One immutable local source dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=280)
    sha256: str
    purpose: str = Field(min_length=3, max_length=220)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("source paths must be repository-relative")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("source bindings require lowercase SHA-256")
        return value


class OpenRouterHy3ExternalSource(BaseModel):
    """One official external source with bounded assertions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    url: str = Field(min_length=8, max_length=500)
    retrieved_on: Literal["2026-07-14"] = "2026-07-14"
    assertions: tuple[str, ...] = Field(min_length=1, max_length=8)

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("external source IDs require stable lowercase slugs")
        return value


class OpenRouterHy3RouteBoundary(BaseModel):
    """Frozen model and gateway facts for the time-limited route."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gateway_provider: Literal["openrouter"] = "openrouter"
    requested_model: Literal["tencent/hy3:free"] = "tencent/hy3:free"
    model_family: Literal["tencent-hy3"] = "tencent-hy3"
    route_available_as_of_review: Literal[True] = True
    route_is_free: Literal[True] = True
    model_release_date: Literal["2026-07-06"] = "2026-07-06"
    scheduled_route_retirement_date: Literal["2026-07-21"] = "2026-07-21"
    context_window_tokens: Literal[262144] = 262144
    endpoint_count_known: Literal[False] = False
    direct_tencent_telemetry_claim_permitted: Literal[False] = False


class OpenRouterHy3TelemetryBoundary(BaseModel):
    """Normalized usage and route metadata available at the gateway boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authority: Literal[OpenRouterHy3TelemetryAuthority.OPENROUTER_NORMALIZED_USAGE] = (
        OpenRouterHy3TelemetryAuthority.OPENROUTER_NORMALIZED_USAGE
    )
    cached_tokens_path: Literal["usage.prompt_tokens_details.cached_tokens"] = (
        "usage.prompt_tokens_details.cached_tokens"
    )
    cache_write_tokens_path: Literal["usage.prompt_tokens_details.cache_write_tokens"] = (
        "usage.prompt_tokens_details.cache_write_tokens"
    )
    cache_discount_path: Literal["generation.cache_discount"] = "generation.cache_discount"
    generation_provider_path: Literal["generation.provider_name"] = "generation.provider_name"
    generation_model_path: Literal["generation.model"] = "generation.model"
    generation_session_path: Literal["generation.session_id"] = "generation.session_id"
    generation_native_cached_tokens_path: Literal["generation.native_tokens_cached"] = (
        "generation.native_tokens_cached"
    )
    normalized_schema_documented: Literal[True] = True
    hy3_free_numeric_telemetry_observed: Literal[False] = False
    hy3_free_cache_use_observed: Literal[False] = False
    missing_interpreted_as_zero: Literal[False] = False


class OpenRouterHy3Condition(BaseModel):
    """One frozen condition and its controlled variables."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_id: OpenRouterHy3ConditionId
    prefix_mode: Literal["unstable", "deterministic_stable"]
    session_mode: Literal["unique_per_request", "stable_affinity_key"]
    intended_hypothesis: Literal[
        "control",
        "context_determinism",
        "affinity_retention",
    ]


class OpenRouterHy3IdentifiabilityResolution(BaseModel):
    """Causal-identifiability boundary before adapter or live execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    explicit_session_id_replaces_message_hash_key: Literal[True] = True
    explicit_session_id_activates_stickiness_on_success: Literal[True] = True
    manual_provider_order_permitted: Literal[False] = False
    manual_provider_order_disables_sticky_routing: Literal[True] = True
    unique_session_ids_required_for_a_and_b: Literal[True] = True
    stable_session_id_required_for_c: Literal[True] = True
    generation_metadata_required: Literal[True] = True
    provider_route_stability_requires_live_verification: Literal[True] = True
    condition_a_b_design_identifiable: Literal[True] = True
    condition_b_c_design_identifiable: Literal[True] = True
    condition_c_effect_claim_permitted: Literal[False] = False


class OpenRouterHy3PrivacyBoundary(BaseModel):
    """Privacy controls required for any future live request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    synthetic_public_safe_prompts_only: Literal[True] = True
    data_collection_deny_required: Literal[True] = True
    zero_data_retention_required: Literal[True] = True
    customer_data_permitted: Literal[False] = False
    private_repository_content_permitted: Literal[False] = False
    historical_local_prompt_bundle_permitted: Literal[False] = False
    public_raw_provider_body_permitted: Literal[False] = False
    credential_logging_permitted: Literal[False] = False
    privacy_compatible_route_verified: Literal[False] = False


class OpenRouterHy3CallBudget(BaseModel):
    """Future capability-probe constitution frozen before implementation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    maximum_successful_calls: Literal[2] = 2
    maximum_total_attempts: Literal[4] = 4
    transient_replacement_http_statuses: tuple[
        Literal[429],
        Literal[502],
        Literal[524],
        Literal[529],
    ] = (429, 502, 524, 529)
    replacement_only_before_usable_evidence: Literal[True] = True
    successful_response_retry_permitted: Literal[False] = False
    authentication_failure_retry_permitted: Literal[False] = False
    contract_failure_retry_permitted: Literal[False] = False
    privacy_failure_retry_permitted: Literal[False] = False
    live_calls_performed_by_review: Literal[0] = 0


class OpenRouterHy3ClaimRecord(BaseModel):
    """One explicit claim boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: OpenRouterHy3ClaimKind
    decision: OpenRouterHy3ClaimDecision
    reason: OpenRouterHy3ClaimReason


class OpenRouterHy3IdentifiabilityReview(BaseModel):
    """Immutable conclusion of the non-live route and experiment review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["openrouter-hy3-identifiability-review-v1"]
    status: Literal[OpenRouterHy3ReviewStatus.REVIEW_READY_INACTIVE] = (
        OpenRouterHy3ReviewStatus.REVIEW_READY_INACTIVE
    )
    source_commit: str
    mini_prd_version: Literal["1.0.0"] = "1.0.0"
    source_bindings: tuple[OpenRouterHy3SourceBinding, ...] = Field(
        min_length=6,
        max_length=6,
    )
    external_sources: tuple[OpenRouterHy3ExternalSource, ...] = Field(
        min_length=4,
        max_length=4,
    )
    route_boundary: OpenRouterHy3RouteBoundary
    telemetry_boundary: OpenRouterHy3TelemetryBoundary
    conditions: tuple[
        OpenRouterHy3Condition,
        OpenRouterHy3Condition,
        OpenRouterHy3Condition,
    ]
    identifiability: OpenRouterHy3IdentifiabilityResolution
    privacy_boundary: OpenRouterHy3PrivacyBoundary
    call_budget: OpenRouterHy3CallBudget
    claims: tuple[OpenRouterHy3ClaimRecord, ...] = Field(
        min_length=12,
        max_length=12,
    )
    adapter_implementation_permitted: Literal[True] = True
    dry_run_harness_permitted: Literal[True] = True
    live_provider_call_authorized: Literal[False] = False
    credential_access_permitted: Literal[False] = False
    capability_probe_authorization_review_permitted: Literal[True] = True
    pilot_execution_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    tla_plus_required_before_adapter: Literal[False] = False
    tla_plus_reassessment_required_before_live_authorization: Literal[True] = True
    next_gate: Literal[OpenRouterHy3NextGate.OPENROUTER_PROVIDER_ADAPTER_DRY_RUN] = (
        OpenRouterHy3NextGate.OPENROUTER_PROVIDER_ADAPTER_DRY_RUN
    )

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("review requires a full lowercase source commit")
        return value

    @model_validator(mode="after")
    def validate_review(self) -> OpenRouterHy3IdentifiabilityReview:
        expected_paths = {
            "docs/product/AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md",
            "data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1/review.json",
            "data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1/manifest.json",
            "docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md",
            "src/auragateway/contracts/provider.py",
            "src/auragateway/providers/base.py",
        }
        observed_paths = [item.path for item in self.source_bindings]
        if set(observed_paths) != expected_paths or len(observed_paths) != len(set(observed_paths)):
            raise ValueError("review requires the six exact local source bindings")

        expected_conditions = tuple(OpenRouterHy3ConditionId)
        observed_conditions = tuple(item.condition_id for item in self.conditions)
        if observed_conditions != expected_conditions:
            raise ValueError("conditions must remain ordered A, B, then C")
        expected_specs = {
            OpenRouterHy3ConditionId.CONDITION_A: (
                "unstable",
                "unique_per_request",
                "control",
            ),
            OpenRouterHy3ConditionId.CONDITION_B: (
                "deterministic_stable",
                "unique_per_request",
                "context_determinism",
            ),
            OpenRouterHy3ConditionId.CONDITION_C: (
                "deterministic_stable",
                "stable_affinity_key",
                "affinity_retention",
            ),
        }
        for item in self.conditions:
            expected = expected_specs[item.condition_id]
            observed = (item.prefix_mode, item.session_mode, item.intended_hypothesis)
            if observed != expected:
                raise ValueError("condition definition drifted from the frozen experiment")

        expected_claims = set(OpenRouterHy3ClaimKind)
        observed_claims = [item.claim_kind for item in self.claims]
        if set(observed_claims) != expected_claims or len(observed_claims) != len(
            set(observed_claims)
        ):
            raise ValueError("review requires all twelve claim decisions")

        permitted = {
            OpenRouterHy3ClaimKind.FREE_ROUTE_AVAILABLE_TIME_LIMITED,
            OpenRouterHy3ClaimKind.NORMALIZED_CACHE_SCHEMA_DOCUMENTED,
            OpenRouterHy3ClaimKind.EXPLICIT_SESSION_STICKINESS_DOCUMENTED,
            OpenRouterHy3ClaimKind.GENERATION_ROUTE_METADATA_DOCUMENTED,
            OpenRouterHy3ClaimKind.CONDITION_A_B_DESIGN_IDENTIFIABLE,
            OpenRouterHy3ClaimKind.CONDITION_B_C_DESIGN_IDENTIFIABLE,
        }
        for claim in self.claims:
            expected_decision = (
                OpenRouterHy3ClaimDecision.PERMITTED
                if claim.claim_kind in permitted
                else OpenRouterHy3ClaimDecision.BLOCKED
            )
            if claim.decision is not expected_decision:
                raise ValueError("claim decision exceeds the non-live evidence boundary")
        return self


class OpenRouterHy3IdentifiabilityManifest(BaseModel):
    """Integrity manifest for the review and human-readable records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["openrouter-hy3-identifiability-review-v1"]
    source_commit: str
    review_path: Literal[
        "data/evals/benchmark/openrouter-hy3-identifiability-review-v1/review.json"
    ]
    review_sha256: str
    adr_path: Literal["docs/adr/openrouter-hy3-identifiability-review.md"]
    adr_sha256: str
    report_path: Literal["docs/benchmark/AuraGateway_OpenRouter_Hy3_Identifiability_Review.md"]
    report_sha256: str
    mini_prd_path: Literal[
        "docs/product/AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md"
    ]
    mini_prd_sha256: str
    source_evidence_locked: Literal[True] = True
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    next_gate: Literal[OpenRouterHy3NextGate.OPENROUTER_PROVIDER_ADAPTER_DRY_RUN] = (
        OpenRouterHy3NextGate.OPENROUTER_PROVIDER_ADAPTER_DRY_RUN
    )

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest requires a full lowercase source commit")
        return value

    @field_validator(
        "review_sha256",
        "adr_sha256",
        "report_sha256",
        "mini_prd_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest requires lowercase SHA-256")
        return value


class OpenRouterHy3IdentifiabilitySummary(BaseModel):
    """Metadata-safe CLI result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    review_id: Literal["openrouter-hy3-identifiability-review-v1"]
    status: OpenRouterHy3ReviewStatus
    source_binding_count: Literal[6] = 6
    external_source_count: Literal[4] = 4
    route_available_as_of_review: Literal[True] = True
    condition_a_b_design_identifiable: Literal[True] = True
    condition_b_c_design_identifiable: Literal[True] = True
    condition_c_effect_claim_permitted: Literal[False] = False
    adapter_implementation_permitted: Literal[True] = True
    live_provider_call_authorized: Literal[False] = False
    credential_accessed: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    next_gate: OpenRouterHy3NextGate
