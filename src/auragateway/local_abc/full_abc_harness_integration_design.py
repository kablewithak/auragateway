"""Typed design contract for future full AuraGateway A/B/C harness integration."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import ConditionId, LocalABCContract, PrefixPolicy

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_BLOB_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SOURCE_MERGE_COMMIT: Final = "b995794e1e1f312c23f39a685b3c118253707700"
_BENCHMARK_CONSTITUTION_BLOB_SHA: Final = "dc25906298a611b71f3482da85c6aba763c474e7"
_HARDENING_SOURCE_BLOB_SHA: Final = "d991beb28a70e90a2de6fb805dba53ca5cf16d33"
_HARDENING_PLAN_BLOB_SHA: Final = "449007bd4d0fe55596aee24c313b4ec6b1677ceb"
_HARDENING_PLAN_SHA256: Final = "aa6a02dee2ceb039e61d13048075a3a0081777538b2c08277d4a381f2b5a47e3"
_PROMPT_POLICY_SHA256: Final = "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
_RESPONSE_SCHEMA_SHA256: Final = "bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d"
_ACTION_SCHEMA_SHA256: Final = "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
_SCORE_ENTRYPOINT: Final = (
    "auragateway.local_abc.action_extraction_traceability_cleanup_hardening."
    "evaluate_reconcile_balance_extraction_v2"
)
_CLEANUP_ENTRYPOINT: Final = (
    "auragateway.local_abc.action_extraction_traceability_cleanup_hardening."
    "classify_action_extraction_worker_cleanup"
)
_EXPECTED_TRACE_FIELDS: Final = (
    "run_id",
    "trace_id",
    "comparison_pair_id",
    "episode_id",
    "replication_id",
    "condition_id",
    "cache_namespace_id",
    "session_id_hash",
    "provider_model_alias",
    "benchmark_manifest_hash",
    "execution_manifest_hash",
    "configuration_fingerprint",
    "score_prompt_policy_sha256",
    "score_rendered_prompt_sha256",
    "cleanup_status",
    "cleanup_warning_codes",
)
_EXPECTED_PUBLIC_EVIDENCE_EXCLUSIONS: Final = (
    "raw_prompts",
    "raw_user_messages",
    "raw_conversation_history",
    "raw_retrieved_document_text",
    "raw_model_outputs",
    "hidden_reasoning",
    "raw_provider_payloads",
    "credentials",
    "secrets",
    "direct_personal_identifiers",
    "unbounded_metadata",
)


class FullABCRoutePolicy(StrEnum):
    """Route behavior held fixed or changed by each A/B/C condition."""

    TURN_LOCAL = "turn_local"
    CACHE_AFFINITY_TTL = "cache_affinity_ttl"


class FullABCCausalContrastId(StrEnum):
    """The three frozen causal contrasts from the benchmark constitution."""

    A_VS_B = "A_vs_B"
    B_VS_C = "B_vs_C"
    A_VS_C = "A_vs_C"


class FullABCClaimFamily(StrEnum):
    """Claim family permitted by one controlled contrast."""

    CONTEXT_CONSTRUCTION_POLICY = "context_construction_policy"
    ROUTE_POLICY = "route_policy"
    TOTAL_SYSTEM = "total_system"


class FullABCBenchmarkSuiteId(StrEnum):
    """The functional and runtime suites governed by separate schedules."""

    FUNCTIONAL = "functional"
    RUNTIME_MICROBENCHMARK = "runtime_microbenchmark"


class FullABCTelemetryEvidenceLevel(StrEnum):
    """Evidence strength allowed for cache, latency, and cost claims."""

    OBSERVED_PROVIDER = "observed_provider"
    INFERRED_LOCAL = "inferred_local"
    UNAVAILABLE = "unavailable"


class FullABCHarnessConditionIntegration(LocalABCContract):
    """One A/B/C condition with shared hardened scoring and cleanup boundaries."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    condition_id: ConditionId
    prefix_policy: PrefixPolicy
    route_policy: FullABCRoutePolicy
    static_volatile_boundary_enforced: bool
    score_entrypoint: Literal[
        "auragateway.local_abc.action_extraction_traceability_cleanup_hardening."
        "evaluate_reconcile_balance_extraction_v2"
    ] = _SCORE_ENTRYPOINT
    cleanup_entrypoint: Literal[
        "auragateway.local_abc.action_extraction_traceability_cleanup_hardening."
        "classify_action_extraction_worker_cleanup"
    ] = _CLEANUP_ENTRYPOINT
    prompt_policy_sha256: Literal[
        "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
    ] = _PROMPT_POLICY_SHA256
    response_schema_sha256: Literal[
        "bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d"
    ] = _RESPONSE_SCHEMA_SHA256
    action_schema_sha256: Literal[
        "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
    ] = _ACTION_SCHEMA_SHA256
    explicit_executed_prompt_identity_required: Literal[True] = True
    evidence_derived_cleanup_required: Literal[True] = True
    retrieval_configuration_held_constant: Literal[True] = True
    output_schema_held_constant: Literal[True] = True
    quality_rubric_held_constant: Literal[True] = True

    @model_validator(mode="after")
    def validate_condition(self) -> Self:
        expected = {
            ConditionId.A: (
                PrefixPolicy.CACHE_HOSTILE,
                FullABCRoutePolicy.TURN_LOCAL,
                False,
            ),
            ConditionId.B: (
                PrefixPolicy.DETERMINISTIC_EXACT,
                FullABCRoutePolicy.TURN_LOCAL,
                True,
            ),
            ConditionId.C: (
                PrefixPolicy.DETERMINISTIC_EXACT,
                FullABCRoutePolicy.CACHE_AFFINITY_TTL,
                True,
            ),
        }
        expected_prefix, expected_route, expected_boundary = expected[self.condition_id]
        if self.prefix_policy is not expected_prefix:
            raise ValueError("condition prefix policy violates the frozen constitution")
        if self.route_policy is not expected_route:
            raise ValueError("condition route policy violates the frozen constitution")
        if self.static_volatile_boundary_enforced is not expected_boundary:
            raise ValueError("condition static/volatile boundary violates the frozen constitution")
        return self


class FullABCCausalContrast(LocalABCContract):
    """Permitted attribution for one pairwise A/B/C comparison."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    contrast_id: FullABCCausalContrastId
    left_condition: ConditionId
    right_condition: ConditionId
    permitted_claim_family: FullABCClaimFamily
    prohibited_attribution: str = Field(min_length=20, max_length=240)

    @model_validator(mode="after")
    def validate_contrast(self) -> Self:
        expected = {
            FullABCCausalContrastId.A_VS_B: (
                ConditionId.A,
                ConditionId.B,
                FullABCClaimFamily.CONTEXT_CONSTRUCTION_POLICY,
            ),
            FullABCCausalContrastId.B_VS_C: (
                ConditionId.B,
                ConditionId.C,
                FullABCClaimFamily.ROUTE_POLICY,
            ),
            FullABCCausalContrastId.A_VS_C: (
                ConditionId.A,
                ConditionId.C,
                FullABCClaimFamily.TOTAL_SYSTEM,
            ),
        }
        left, right, claim_family = expected[self.contrast_id]
        if self.left_condition is not left or self.right_condition is not right:
            raise ValueError("contrast condition order violates the frozen constitution")
        if self.permitted_claim_family is not claim_family:
            raise ValueError("contrast claim family violates the frozen constitution")
        return self


class FullABCBenchmarkSuite(LocalABCContract):
    """Frozen trajectory counts and run-order schedule for one benchmark suite."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    suite_id: FullABCBenchmarkSuiteId
    episode_count: int = Field(gt=0)
    turns_per_episode: Literal[4] = 4
    condition_count: Literal[3] = 3
    repetitions_per_condition: int = Field(gt=0)
    scheduled_trajectory_count: int = Field(gt=0)
    schedule_id: str

    @model_validator(mode="after")
    def validate_suite(self) -> Self:
        expected = {
            FullABCBenchmarkSuiteId.FUNCTIONAL: (
                18,
                3,
                162,
                "functional-counterbalance-v1",
            ),
            FullABCBenchmarkSuiteId.RUNTIME_MICROBENCHMARK: (
                6,
                10,
                180,
                "runtime-counterbalance-v1",
            ),
        }
        episodes, repetitions, trajectories, schedule_id = expected[self.suite_id]
        if self.episode_count != episodes:
            raise ValueError("benchmark suite episode count drifted")
        if self.repetitions_per_condition != repetitions:
            raise ValueError("benchmark suite repetition count drifted")
        if self.scheduled_trajectory_count != trajectories:
            raise ValueError("benchmark suite trajectory count drifted")
        if self.schedule_id != schedule_id:
            raise ValueError("benchmark suite schedule ID drifted")
        calculated = self.episode_count * self.condition_count * self.repetitions_per_condition
        if calculated != self.scheduled_trajectory_count:
            raise ValueError("benchmark suite trajectory arithmetic does not reconcile")
        return self


class FullABCQualityNonInferiorityGate(LocalABCContract):
    """Quality floor that must pass before runtime improvements may be claimed."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["quality-non-inferiority-v1"] = "quality-non-inferiority-v1"
    max_task_success_regression_percentage_points: Decimal = Decimal("5")
    minimum_structured_output_validity: Decimal = Decimal("0.95")
    citation_support_regression_permitted: Literal[False] = False
    unsupported_answer_rate_increase_permitted: Literal[False] = False
    retrieval_configuration_change_permitted: Literal[False] = False
    unsafe_behavior_regression_permitted: Literal[False] = False
    comparison_eligibility_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_gate(self) -> Self:
        if self.max_task_success_regression_percentage_points != Decimal("5"):
            raise ValueError("task-success non-inferiority margin must remain five points")
        if self.minimum_structured_output_validity != Decimal("0.95"):
            raise ValueError("structured-output validity floor must remain 0.95")
        return self


class FullABCTelemetryClaimGate(LocalABCContract):
    """Fail-closed claim policy for unavailable or ambiguous provider cache evidence."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    permitted_evidence_levels: tuple[FullABCTelemetryEvidenceLevel, ...] = (
        FullABCTelemetryEvidenceLevel.OBSERVED_PROVIDER,
        FullABCTelemetryEvidenceLevel.INFERRED_LOCAL,
        FullABCTelemetryEvidenceLevel.UNAVAILABLE,
    )
    unknown_values_remain_unknown: Literal[True] = True
    missing_cache_value_coerced_to_zero: Literal[False] = False
    warm_eligibility_proves_provider_cache_hit: Literal[False] = False
    provider_cache_claim_requires_observed_provider_evidence: Literal[True] = True
    cache_latency_cost_claim_requires_sufficiency_decision: Literal[True] = True

    @field_validator("permitted_evidence_levels")
    @classmethod
    def validate_levels(
        cls,
        value: tuple[FullABCTelemetryEvidenceLevel, ...],
    ) -> tuple[FullABCTelemetryEvidenceLevel, ...]:
        expected = tuple(FullABCTelemetryEvidenceLevel)
        if value != expected:
            raise ValueError("telemetry evidence levels must remain complete and ordered")
        return value


class FullABCHarnessIntegrationDesign(LocalABCContract):
    """Immutable integration design; it grants no measured execution authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    design_id: Literal["auragateway-full-abc-harness-integration-design-v1"] = (
        "auragateway-full-abc-harness-integration-design-v1"
    )
    source_merge_commit: Literal["b995794e1e1f312c23f39a685b3c118253707700"] = _SOURCE_MERGE_COMMIT
    benchmark_constitution_blob_sha: Literal["dc25906298a611b71f3482da85c6aba763c474e7"] = (
        _BENCHMARK_CONSTITUTION_BLOB_SHA
    )
    hardening_source_blob_sha: Literal["d991beb28a70e90a2de6fb805dba53ca5cf16d33"] = (
        _HARDENING_SOURCE_BLOB_SHA
    )
    hardening_plan_blob_sha: Literal["449007bd4d0fe55596aee24c313b4ec6b1677ceb"] = (
        _HARDENING_PLAN_BLOB_SHA
    )
    hardening_plan_sha256: Literal[
        "aa6a02dee2ceb039e61d13048075a3a0081777538b2c08277d4a381f2b5a47e3"
    ] = _HARDENING_PLAN_SHA256
    conditions: tuple[
        FullABCHarnessConditionIntegration,
        FullABCHarnessConditionIntegration,
        FullABCHarnessConditionIntegration,
    ]
    contrasts: tuple[FullABCCausalContrast, FullABCCausalContrast, FullABCCausalContrast]
    suites: tuple[FullABCBenchmarkSuite, FullABCBenchmarkSuite]
    quality_gate: FullABCQualityNonInferiorityGate
    telemetry_claim_gate: FullABCTelemetryClaimGate
    trace_fields: tuple[str, ...]
    public_evidence_exclusions: tuple[str, ...]
    score_identity_must_match_executed_prompt: Literal[True] = True
    cleanup_classification_must_follow_observed_evidence: Literal[True] = True
    condition_specific_scorer_permitted: Literal[False] = False
    condition_specific_cleanup_semantics_permitted: Literal[False] = False
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    provider_execution_authorized: Literal[False] = False
    new_authorization_issued: Literal[False] = False
    consumed_authorization_reused: Literal[False] = False
    full_abc_results_claimed: Literal[False] = False
    next_gate: Literal["full_abc_harness_integration_implementation"] = (
        "full_abc_harness_integration_implementation"
    )

    @field_validator(
        "benchmark_constitution_blob_sha",
        "hardening_source_blob_sha",
        "hardening_plan_blob_sha",
    )
    @classmethod
    def validate_git_blob_sha(cls, value: str) -> str:
        if _GIT_BLOB_PATTERN.fullmatch(value) is None:
            raise ValueError("integration design blob identities must be lowercase Git SHA-1")
        return value

    @field_validator("hardening_plan_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("integration design digest must be lowercase SHA-256")
        return value

    @field_validator("trace_fields")
    @classmethod
    def validate_trace_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _EXPECTED_TRACE_FIELDS:
            raise ValueError("integration trace fields drifted from the frozen design")
        return value

    @field_validator("public_evidence_exclusions")
    @classmethod
    def validate_public_exclusions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _EXPECTED_PUBLIC_EVIDENCE_EXCLUSIONS:
            raise ValueError("public evidence exclusions drifted from the privacy boundary")
        return value

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        if tuple(condition.condition_id for condition in self.conditions) != tuple(ConditionId):
            raise ValueError("conditions must preserve A, B, C order")
        if tuple(contrast.contrast_id for contrast in self.contrasts) != tuple(
            FullABCCausalContrastId
        ):
            raise ValueError("contrasts must preserve A/B, B/C, A/C order")
        if tuple(suite.suite_id for suite in self.suites) != tuple(FullABCBenchmarkSuiteId):
            raise ValueError("benchmark suites must preserve functional then runtime order")

        score_entrypoints = {condition.score_entrypoint for condition in self.conditions}
        cleanup_entrypoints = {condition.cleanup_entrypoint for condition in self.conditions}
        prompt_policies = {condition.prompt_policy_sha256 for condition in self.conditions}
        response_schemas = {condition.response_schema_sha256 for condition in self.conditions}
        action_schemas = {condition.action_schema_sha256 for condition in self.conditions}
        if len(score_entrypoints) != 1 or len(cleanup_entrypoints) != 1:
            raise ValueError("all conditions must share hardened scoring and cleanup entrypoints")
        if len(prompt_policies) != 1 or len(response_schemas) != 1 or len(action_schemas) != 1:
            raise ValueError("all conditions must share prompt and schema quality boundaries")
        return self


def load_full_abc_harness_integration_design(
    path: Path,
) -> FullABCHarnessIntegrationDesign:
    """Load the immutable design artifact without granting execution authority."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("full A/B/C integration design must contain one JSON object")
    return FullABCHarnessIntegrationDesign.model_validate(cast(dict[str, object], payload))
