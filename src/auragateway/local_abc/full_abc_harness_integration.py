"""Local implementation of the hardened full A/B/C harness integration boundary."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, cast
from uuid import UUID

from pydantic import field_validator, model_validator

from auragateway.local_abc.action_extraction_eval import (
    ActionExtractionCaseScore,
    ReconcileBalanceExtractionCase,
)
from auragateway.local_abc.action_extraction_traceability_cleanup_hardening import (
    ActionExtractionCleanupStatus,
    ActionExtractionCleanupWarningCode,
    ActionExtractionWorkerCleanupDecision,
    ActionExtractionWorkerCleanupObservation,
    classify_action_extraction_worker_cleanup,
    evaluate_reconcile_balance_extraction_v2,
)
from auragateway.local_abc.contracts import ConditionId, LocalABCContract, PrefixPolicy
from auragateway.local_abc.full_abc_harness_integration_design import (
    FullABCCausalContrastId,
    FullABCHarnessIntegrationDesign,
    FullABCRoutePolicy,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_BLOB_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{2,159}$")
_SOURCE_MERGE_COMMIT: Final = "430fe12445dce4563274b880f203da175acb567d"
_DESIGN_BLOB_SHA: Final = "5d1bcb3a4fd26096d2e0d5f8c51e38ef927de0d3"
_DESIGN_SHA256: Final = "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
_HARDENING_SOURCE_BLOB_SHA: Final = "d991beb28a70e90a2de6fb805dba53ca5cf16d33"
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


class FullABCIntegrationPreflightFailureCode(StrEnum):
    """Machine-readable reasons a future pair cannot enter comparative reporting."""

    DESIGN_FINGERPRINT_MISMATCH = "DESIGN_FINGERPRINT_MISMATCH"
    EXECUTION_MANIFEST_UNFROZEN = "EXECUTION_MANIFEST_UNFROZEN"
    MEASURED_EXECUTION_UNAUTHORIZED = "MEASURED_EXECUTION_UNAUTHORIZED"
    PROVIDER_EXECUTION_UNAUTHORIZED = "PROVIDER_EXECUTION_UNAUTHORIZED"
    GPU_EXECUTION_UNAUTHORIZED = "GPU_EXECUTION_UNAUTHORIZED"
    CONDITION_PAIR_MISMATCH = "CONDITION_PAIR_MISMATCH"
    COMPARISON_PAIR_ID_MISMATCH = "COMPARISON_PAIR_ID_MISMATCH"
    EPISODE_ID_MISMATCH = "EPISODE_ID_MISMATCH"
    REPLICATION_ID_MISMATCH = "REPLICATION_ID_MISMATCH"
    PROVIDER_MODEL_ALIAS_MISMATCH = "PROVIDER_MODEL_ALIAS_MISMATCH"
    BENCHMARK_MANIFEST_MISMATCH = "BENCHMARK_MANIFEST_MISMATCH"
    EXECUTION_MANIFEST_MISMATCH = "EXECUTION_MANIFEST_MISMATCH"
    CONFIGURATION_FINGERPRINT_MISMATCH = "CONFIGURATION_FINGERPRINT_MISMATCH"
    CACHE_NAMESPACE_COLLISION = "CACHE_NAMESPACE_COLLISION"
    PROMPT_POLICY_MISMATCH = "PROMPT_POLICY_MISMATCH"
    CLEANUP_FAILED = "CLEANUP_FAILED"
    CLEANUP_WARNING_BLOCKS_RUNTIME = "CLEANUP_WARNING_BLOCKS_RUNTIME"


class FullABCConditionRuntimeAdapter(LocalABCContract):
    """Executable local adapter for one frozen condition without provider authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    condition_id: ConditionId
    prefix_policy: PrefixPolicy
    route_policy: FullABCRoutePolicy
    static_volatile_boundary_enforced: bool
    integration_design_sha256: Literal[
        "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
    ] = _DESIGN_SHA256
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
    model_request_performed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False

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
            raise ValueError("runtime adapter prefix policy violates the frozen design")
        if self.route_policy is not expected_route:
            raise ValueError("runtime adapter route policy violates the frozen design")
        if self.static_volatile_boundary_enforced is not expected_boundary:
            raise ValueError("runtime adapter context boundary violates the frozen design")
        return self


class FullABCConditionRuntimeAdapterSet(LocalABCContract):
    """Canonical A/B/C adapter set with one scorer and one cleanup classifier."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    adapters: tuple[
        FullABCConditionRuntimeAdapter,
        FullABCConditionRuntimeAdapter,
        FullABCConditionRuntimeAdapter,
    ]

    @model_validator(mode="after")
    def validate_adapters(self) -> Self:
        if tuple(adapter.condition_id for adapter in self.adapters) != tuple(ConditionId):
            raise ValueError("runtime adapters must preserve A, B, C order")
        if len({adapter.score_entrypoint for adapter in self.adapters}) != 1:
            raise ValueError("all runtime adapters must share one score entrypoint")
        if len({adapter.cleanup_entrypoint for adapter in self.adapters}) != 1:
            raise ValueError("all runtime adapters must share one cleanup entrypoint")
        return self

    def for_condition(self, condition_id: ConditionId) -> FullABCConditionRuntimeAdapter:
        """Return the adapter for one condition."""

        return self.adapters[{ConditionId.A: 0, ConditionId.B: 1, ConditionId.C: 2}[condition_id]]


class FullABCScoredActionExtraction(LocalABCContract):
    """Condition-scoped action score produced by the shared hardened scorer."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    condition_id: ConditionId
    score: ActionExtractionCaseScore
    score_prompt_policy_sha256: str
    score_rendered_prompt_sha256: str
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    model_request_performed: Literal[False] = False

    @field_validator("score_prompt_policy_sha256", "score_rendered_prompt_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("scored action identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_score_binding(self) -> Self:
        if self.score_prompt_policy_sha256 != self.score.prompt_identity.policy_sha256:
            raise ValueError("score policy trace must match the retained score identity")
        if self.score_rendered_prompt_sha256 != self.score.prompt_identity.rendered_prompt_sha256:
            raise ValueError("rendered prompt trace must match the retained score identity")
        if self.score_prompt_policy_sha256 != _PROMPT_POLICY_SHA256:
            raise ValueError("full A/B/C scoring must bind the active v2 prompt policy")
        return self


class FullABCCleanupBridgeResult(LocalABCContract):
    """Condition-scoped cleanup decision from the shared evidence-derived classifier."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    condition_id: ConditionId
    decision: ActionExtractionWorkerCleanupDecision
    cleanup_status: ActionExtractionCleanupStatus
    cleanup_warning_codes: tuple[ActionExtractionCleanupWarningCode, ...]

    @model_validator(mode="after")
    def validate_cleanup_binding(self) -> Self:
        if self.cleanup_status is not self.decision.status:
            raise ValueError("cleanup bridge status must match the classifier decision")
        if self.cleanup_warning_codes != self.decision.warning_codes:
            raise ValueError("cleanup bridge warnings must match the classifier decision")
        return self


class FullABCTraceEnvelope(LocalABCContract):
    """Privacy-safe trajectory trace carrying every frozen integration field."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    run_id: str
    trace_id: UUID
    comparison_pair_id: str
    episode_id: str
    replication_id: str
    condition_id: ConditionId
    cache_namespace_id: str
    session_id_hash: str
    provider_model_alias: str
    benchmark_manifest_hash: str
    execution_manifest_hash: str
    configuration_fingerprint: str
    score_prompt_policy_sha256: str
    score_rendered_prompt_sha256: str
    cleanup_status: ActionExtractionCleanupStatus
    cleanup_warning_codes: tuple[ActionExtractionCleanupWarningCode, ...]
    raw_prompt_retained: Literal[False] = False
    raw_user_message_retained: Literal[False] = False
    raw_conversation_history_retained: Literal[False] = False
    raw_retrieved_document_text_retained: Literal[False] = False
    raw_model_output_retained: Literal[False] = False
    raw_provider_payload_retained: Literal[False] = False
    credentials_retained: Literal[False] = False
    secrets_retained: Literal[False] = False
    direct_personal_identifiers_retained: Literal[False] = False

    @field_validator(
        "run_id",
        "comparison_pair_id",
        "episode_id",
        "replication_id",
        "cache_namespace_id",
    )
    @classmethod
    def validate_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trace identifiers must use stable lowercase characters")
        return value

    @field_validator("provider_model_alias")
    @classmethod
    def validate_alias(cls, value: str) -> str:
        if _ALIAS_PATTERN.fullmatch(value) is None:
            raise ValueError("provider model alias contains unsupported characters")
        return value

    @field_validator(
        "session_id_hash",
        "benchmark_manifest_hash",
        "execution_manifest_hash",
        "configuration_fingerprint",
        "score_prompt_policy_sha256",
        "score_rendered_prompt_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("trace fingerprints must be lowercase SHA-256")
        return value

    @field_validator("cleanup_warning_codes")
    @classmethod
    def validate_warning_order(
        cls,
        value: tuple[ActionExtractionCleanupWarningCode, ...],
    ) -> tuple[ActionExtractionCleanupWarningCode, ...]:
        if len(value) != len(set(value)):
            raise ValueError("cleanup warning codes must be unique")
        expected = tuple(sorted(value, key=lambda item: item.value))
        if value != expected:
            raise ValueError("cleanup warning codes must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_trace(self) -> Self:
        if self.score_prompt_policy_sha256 != _PROMPT_POLICY_SHA256:
            raise ValueError("trace score policy must bind the active v2 prompt policy")
        if self.cleanup_status is ActionExtractionCleanupStatus.CLEAN:
            if self.cleanup_warning_codes:
                raise ValueError("clean traces cannot retain cleanup warnings")
        elif (
            self.cleanup_status is ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS
            and not self.cleanup_warning_codes
        ):
            raise ValueError("warning-qualified cleanup requires warning codes")
        return self

    def integration_field_names(self) -> tuple[str, ...]:
        """Return the exact trace fields frozen by the integration design."""

        return _EXPECTED_TRACE_FIELDS


class FullABCComparisonPreflightContext(LocalABCContract):
    """Future execution authority and expected fingerprints supplied to local preflight."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    integration_design_sha256: str
    benchmark_manifest_hash: str
    execution_manifest_hash: str
    expected_configuration_fingerprints: dict[ConditionId, str]
    execution_manifest_frozen: bool
    measured_execution_authorized: bool
    provider_execution_authorized: bool
    gpu_execution_authorized: bool
    issues_authority: Literal[False] = False

    @field_validator(
        "integration_design_sha256",
        "benchmark_manifest_hash",
        "execution_manifest_hash",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("preflight fingerprints must be lowercase SHA-256")
        return value

    @field_validator("expected_configuration_fingerprints")
    @classmethod
    def validate_configuration_fingerprints(
        cls,
        value: dict[ConditionId, str],
    ) -> dict[ConditionId, str]:
        if set(value) != set(ConditionId):
            raise ValueError("preflight requires one expected fingerprint for A, B, and C")
        if any(_SHA256_PATTERN.fullmatch(item) is None for item in value.values()):
            raise ValueError("condition configuration fingerprints must be lowercase SHA-256")
        return value


class FullABCComparisonPreflightDecision(LocalABCContract):
    """Fail-closed metric-family eligibility decision for one future comparison pair."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    contrast_id: FullABCCausalContrastId
    left_condition: ConditionId
    right_condition: ConditionId
    record_shape_valid: bool
    quality_metric_eligible: bool
    runtime_metric_eligible: bool
    provider_cache_claim_eligible: Literal[False] = False
    claim_generation_permitted: Literal[False] = False
    failure_codes: tuple[FullABCIntegrationPreflightFailureCode, ...]
    warning_codes: tuple[FullABCIntegrationPreflightFailureCode, ...]
    original_records_retained: Literal[True] = True
    rerun_authorized: Literal[False] = False

    @field_validator("failure_codes", "warning_codes")
    @classmethod
    def validate_codes(
        cls,
        value: tuple[FullABCIntegrationPreflightFailureCode, ...],
    ) -> tuple[FullABCIntegrationPreflightFailureCode, ...]:
        if len(value) != len(set(value)):
            raise ValueError("preflight codes must be unique")
        expected = tuple(sorted(value, key=lambda item: item.value))
        if value != expected:
            raise ValueError("preflight codes must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if self.quality_metric_eligible and self.failure_codes:
            raise ValueError("quality eligibility cannot coexist with preflight failures")
        if self.runtime_metric_eligible and (
            self.failure_codes
            or FullABCIntegrationPreflightFailureCode.CLEANUP_WARNING_BLOCKS_RUNTIME
            in self.warning_codes
        ):
            raise ValueError("runtime eligibility requires no failures or cleanup warning block")
        if self.runtime_metric_eligible and not self.quality_metric_eligible:
            raise ValueError("runtime eligibility requires quality eligibility")
        return self


class FullABCHarnessIntegrationImplementationPlan(LocalABCContract):
    """Immutable local implementation record that grants no execution authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    implementation_id: Literal["auragateway-full-abc-harness-integration-implementation-v1"]
    source_merge_commit: Literal["430fe12445dce4563274b880f203da175acb567d"]
    design_blob_sha: Literal["5d1bcb3a4fd26096d2e0d5f8c51e38ef927de0d3"]
    integration_design_sha256: Literal[
        "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
    ]
    hardening_source_blob_sha: Literal["d991beb28a70e90a2de6fb805dba53ca5cf16d33"]
    condition_adapter_builder: Literal[
        "auragateway.local_abc.full_abc_harness_integration."
        "build_full_abc_condition_runtime_adapters"
    ]
    scoring_bridge: Literal[
        "auragateway.local_abc.full_abc_harness_integration.score_full_abc_action_extraction"
    ]
    cleanup_bridge: Literal[
        "auragateway.local_abc.full_abc_harness_integration.classify_full_abc_worker_cleanup"
    ]
    trace_builder: Literal[
        "auragateway.local_abc.full_abc_harness_integration.build_full_abc_trace_envelope"
    ]
    comparison_preflight: Literal[
        "auragateway.local_abc.full_abc_harness_integration.evaluate_full_abc_comparison_preflight"
    ]
    trace_fields: tuple[str, ...]
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    provider_execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    new_authorization_issued: Literal[False] = False
    consumed_authorization_reused: Literal[False] = False
    model_request_performed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0
    next_gate: Literal["full_abc_execution_manifest_asset_inventory"] = (
        "full_abc_execution_manifest_asset_inventory"
    )

    @field_validator("design_blob_sha", "hardening_source_blob_sha")
    @classmethod
    def validate_blob_sha(cls, value: str) -> str:
        if _GIT_BLOB_PATTERN.fullmatch(value) is None:
            raise ValueError("implementation source blobs must be lowercase Git SHA-1")
        return value

    @field_validator("integration_design_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("implementation design binding must be lowercase SHA-256")
        return value

    @field_validator("trace_fields")
    @classmethod
    def validate_trace_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _EXPECTED_TRACE_FIELDS:
            raise ValueError("implementation trace fields drifted from the frozen design")
        return value


def build_full_abc_condition_runtime_adapters(
    design: FullABCHarnessIntegrationDesign,
) -> FullABCConditionRuntimeAdapterSet:
    """Materialize local condition adapters from the exact frozen design."""

    validated = FullABCHarnessIntegrationDesign.model_validate(design.model_dump(mode="python"))
    if validated.fingerprint() != _DESIGN_SHA256:
        raise ValueError("integration design fingerprint does not match the merged design")

    adapters = tuple(
        FullABCConditionRuntimeAdapter(
            condition_id=condition.condition_id,
            prefix_policy=condition.prefix_policy,
            route_policy=condition.route_policy,
            static_volatile_boundary_enforced=condition.static_volatile_boundary_enforced,
        )
        for condition in validated.conditions
    )
    return FullABCConditionRuntimeAdapterSet(
        adapters=cast(
            tuple[
                FullABCConditionRuntimeAdapter,
                FullABCConditionRuntimeAdapter,
                FullABCConditionRuntimeAdapter,
            ],
            adapters,
        )
    )


def score_full_abc_action_extraction(
    *,
    adapter: FullABCConditionRuntimeAdapter,
    case: ReconcileBalanceExtractionCase,
    output_text: str,
    finish_reason: str | None,
    completion_tokens: int,
) -> FullABCScoredActionExtraction:
    """Score retained output locally through the shared hardened v2 scorer."""

    score = evaluate_reconcile_balance_extraction_v2(
        case=case,
        output_text=output_text,
        finish_reason=finish_reason,
        completion_tokens=completion_tokens,
    )
    return FullABCScoredActionExtraction(
        condition_id=adapter.condition_id,
        score=score,
        score_prompt_policy_sha256=score.prompt_identity.policy_sha256,
        score_rendered_prompt_sha256=score.prompt_identity.rendered_prompt_sha256,
    )


def classify_full_abc_worker_cleanup(
    *,
    adapter: FullABCConditionRuntimeAdapter,
    observation: ActionExtractionWorkerCleanupObservation,
) -> FullABCCleanupBridgeResult:
    """Classify one worker shutdown through the shared evidence-derived classifier."""

    decision = classify_action_extraction_worker_cleanup(observation)
    return FullABCCleanupBridgeResult(
        condition_id=adapter.condition_id,
        decision=decision,
        cleanup_status=decision.status,
        cleanup_warning_codes=decision.warning_codes,
    )


def build_full_abc_trace_envelope(
    *,
    scored: FullABCScoredActionExtraction,
    cleanup: FullABCCleanupBridgeResult,
    run_id: str,
    trace_id: UUID,
    comparison_pair_id: str,
    episode_id: str,
    replication_id: str,
    cache_namespace_id: str,
    session_id_hash: str,
    provider_model_alias: str,
    benchmark_manifest_hash: str,
    execution_manifest_hash: str,
    configuration_fingerprint: str,
) -> FullABCTraceEnvelope:
    """Build one privacy-safe trace from scorer and cleanup outputs."""

    if scored.condition_id is not cleanup.condition_id:
        raise ValueError("score and cleanup evidence must share condition identity")
    return FullABCTraceEnvelope(
        run_id=run_id,
        trace_id=trace_id,
        comparison_pair_id=comparison_pair_id,
        episode_id=episode_id,
        replication_id=replication_id,
        condition_id=scored.condition_id,
        cache_namespace_id=cache_namespace_id,
        session_id_hash=session_id_hash,
        provider_model_alias=provider_model_alias,
        benchmark_manifest_hash=benchmark_manifest_hash,
        execution_manifest_hash=execution_manifest_hash,
        configuration_fingerprint=configuration_fingerprint,
        score_prompt_policy_sha256=scored.score_prompt_policy_sha256,
        score_rendered_prompt_sha256=scored.score_rendered_prompt_sha256,
        cleanup_status=cleanup.cleanup_status,
        cleanup_warning_codes=tuple(
            sorted(cleanup.cleanup_warning_codes, key=lambda item: item.value)
        ),
    )


def _expected_conditions_for_contrast(
    contrast_id: FullABCCausalContrastId,
) -> tuple[ConditionId, ConditionId]:
    return {
        FullABCCausalContrastId.A_VS_B: (ConditionId.A, ConditionId.B),
        FullABCCausalContrastId.B_VS_C: (ConditionId.B, ConditionId.C),
        FullABCCausalContrastId.A_VS_C: (ConditionId.A, ConditionId.C),
    }[contrast_id]


def evaluate_full_abc_comparison_preflight(
    *,
    context: FullABCComparisonPreflightContext,
    contrast_id: FullABCCausalContrastId,
    left: FullABCTraceEnvelope,
    right: FullABCTraceEnvelope,
) -> FullABCComparisonPreflightDecision:
    """Evaluate pair eligibility without issuing execution or claim authority."""

    failures: set[FullABCIntegrationPreflightFailureCode] = set()
    warnings: set[FullABCIntegrationPreflightFailureCode] = set()
    expected_left, expected_right = _expected_conditions_for_contrast(contrast_id)

    if context.integration_design_sha256 != _DESIGN_SHA256:
        failures.add(FullABCIntegrationPreflightFailureCode.DESIGN_FINGERPRINT_MISMATCH)
    if not context.execution_manifest_frozen:
        failures.add(FullABCIntegrationPreflightFailureCode.EXECUTION_MANIFEST_UNFROZEN)
    if not context.measured_execution_authorized:
        failures.add(FullABCIntegrationPreflightFailureCode.MEASURED_EXECUTION_UNAUTHORIZED)
    if not context.provider_execution_authorized:
        failures.add(FullABCIntegrationPreflightFailureCode.PROVIDER_EXECUTION_UNAUTHORIZED)
    if not context.gpu_execution_authorized:
        failures.add(FullABCIntegrationPreflightFailureCode.GPU_EXECUTION_UNAUTHORIZED)
    if (left.condition_id, right.condition_id) != (expected_left, expected_right):
        failures.add(FullABCIntegrationPreflightFailureCode.CONDITION_PAIR_MISMATCH)
    if left.comparison_pair_id != right.comparison_pair_id:
        failures.add(FullABCIntegrationPreflightFailureCode.COMPARISON_PAIR_ID_MISMATCH)
    if left.episode_id != right.episode_id:
        failures.add(FullABCIntegrationPreflightFailureCode.EPISODE_ID_MISMATCH)
    if left.replication_id != right.replication_id:
        failures.add(FullABCIntegrationPreflightFailureCode.REPLICATION_ID_MISMATCH)
    if left.provider_model_alias != right.provider_model_alias:
        failures.add(FullABCIntegrationPreflightFailureCode.PROVIDER_MODEL_ALIAS_MISMATCH)
    if (
        left.benchmark_manifest_hash != right.benchmark_manifest_hash
        or left.benchmark_manifest_hash != context.benchmark_manifest_hash
    ):
        failures.add(FullABCIntegrationPreflightFailureCode.BENCHMARK_MANIFEST_MISMATCH)
    if (
        left.execution_manifest_hash != right.execution_manifest_hash
        or left.execution_manifest_hash != context.execution_manifest_hash
    ):
        failures.add(FullABCIntegrationPreflightFailureCode.EXECUTION_MANIFEST_MISMATCH)
    if (
        left.configuration_fingerprint
        != context.expected_configuration_fingerprints[left.condition_id]
    ):
        failures.add(FullABCIntegrationPreflightFailureCode.CONFIGURATION_FINGERPRINT_MISMATCH)
    if (
        right.configuration_fingerprint
        != context.expected_configuration_fingerprints[right.condition_id]
    ):
        failures.add(FullABCIntegrationPreflightFailureCode.CONFIGURATION_FINGERPRINT_MISMATCH)
    if left.cache_namespace_id == right.cache_namespace_id:
        failures.add(FullABCIntegrationPreflightFailureCode.CACHE_NAMESPACE_COLLISION)
    if (
        left.score_prompt_policy_sha256 != _PROMPT_POLICY_SHA256
        or right.score_prompt_policy_sha256 != _PROMPT_POLICY_SHA256
    ):
        failures.add(FullABCIntegrationPreflightFailureCode.PROMPT_POLICY_MISMATCH)
    if (
        left.cleanup_status is ActionExtractionCleanupStatus.FAILED
        or right.cleanup_status is ActionExtractionCleanupStatus.FAILED
    ):
        failures.add(FullABCIntegrationPreflightFailureCode.CLEANUP_FAILED)
    if (
        left.cleanup_status is ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS
        or right.cleanup_status is ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS
    ):
        warnings.add(FullABCIntegrationPreflightFailureCode.CLEANUP_WARNING_BLOCKS_RUNTIME)

    ordered_failures = tuple(sorted(failures, key=lambda item: item.value))
    ordered_warnings = tuple(sorted(warnings, key=lambda item: item.value))
    record_shape_valid = not {
        FullABCIntegrationPreflightFailureCode.CONDITION_PAIR_MISMATCH,
        FullABCIntegrationPreflightFailureCode.COMPARISON_PAIR_ID_MISMATCH,
        FullABCIntegrationPreflightFailureCode.EPISODE_ID_MISMATCH,
        FullABCIntegrationPreflightFailureCode.REPLICATION_ID_MISMATCH,
        FullABCIntegrationPreflightFailureCode.PROVIDER_MODEL_ALIAS_MISMATCH,
        FullABCIntegrationPreflightFailureCode.BENCHMARK_MANIFEST_MISMATCH,
        FullABCIntegrationPreflightFailureCode.EXECUTION_MANIFEST_MISMATCH,
        FullABCIntegrationPreflightFailureCode.CONFIGURATION_FINGERPRINT_MISMATCH,
        FullABCIntegrationPreflightFailureCode.CACHE_NAMESPACE_COLLISION,
        FullABCIntegrationPreflightFailureCode.PROMPT_POLICY_MISMATCH,
        FullABCIntegrationPreflightFailureCode.CLEANUP_FAILED,
    }.intersection(failures)
    quality_eligible = not ordered_failures
    runtime_eligible = quality_eligible and not ordered_warnings

    return FullABCComparisonPreflightDecision(
        contrast_id=contrast_id,
        left_condition=left.condition_id,
        right_condition=right.condition_id,
        record_shape_valid=record_shape_valid,
        quality_metric_eligible=quality_eligible,
        runtime_metric_eligible=runtime_eligible,
        failure_codes=ordered_failures,
        warning_codes=ordered_warnings,
    )


def load_full_abc_harness_integration_implementation_plan(
    path: Path,
) -> FullABCHarnessIntegrationImplementationPlan:
    """Load the immutable local implementation plan without granting execution authority."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("full A/B/C implementation plan must contain one JSON object")
    return FullABCHarnessIntegrationImplementationPlan.model_validate(
        cast(dict[str, object], payload)
    )
