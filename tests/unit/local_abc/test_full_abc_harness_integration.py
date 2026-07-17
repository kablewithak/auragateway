"""Regression tests for the local full A/B/C harness integration implementation."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_eval import ReconcileBalanceExtractionCase
from auragateway.local_abc.action_extraction_remediation import (
    load_action_extraction_remediation_manifest,
)
from auragateway.local_abc.action_extraction_traceability_cleanup_hardening import (
    ActionExtractionCleanupStatus,
    ActionExtractionCleanupWarningCode,
    ActionExtractionWorkerCleanupObservation,
)
from auragateway.local_abc.contracts import ConditionId
from auragateway.local_abc.full_abc_harness_integration import (
    FullABCCleanupBridgeResult,
    FullABCComparisonPreflightContext,
    FullABCConditionRuntimeAdapter,
    FullABCConditionRuntimeAdapterSet,
    FullABCHarnessIntegrationImplementationPlan,
    FullABCIntegrationPreflightFailureCode,
    FullABCScoredActionExtraction,
    FullABCTraceEnvelope,
    build_full_abc_condition_runtime_adapters,
    build_full_abc_trace_envelope,
    classify_full_abc_worker_cleanup,
    evaluate_full_abc_comparison_preflight,
    load_full_abc_harness_integration_implementation_plan,
    score_full_abc_action_extraction,
)
from auragateway.local_abc.full_abc_harness_integration_design import (
    FullABCCausalContrastId,
    FullABCHarnessIntegrationDesign,
    FullABCRoutePolicy,
    load_full_abc_harness_integration_design,
)

ROOT = Path(__file__).resolve().parents[3]
DESIGN_PATH = ROOT / "benchmarks/local_abc/auragateway_full_abc_harness_integration_design_v1.json"
IMPLEMENTATION_PATH = (
    ROOT / "benchmarks/local_abc/auragateway_full_abc_harness_integration_implementation_v1.json"
)
REMEDIATION_MANIFEST_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_remediation_cases_v2.json"
)
ADR_PATH = ROOT / "docs/adr/2026-07-18-local-abc-full-abc-harness-integration-implementation.md"
DOC_PATH = (
    ROOT / "docs/benchmarks/local_abc_auragateway_full_abc_harness_integration_implementation_v1.md"
)
DESIGN_SHA256 = "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
IMPLEMENTATION_SHA256 = "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
PROMPT_POLICY_SHA256 = "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
BENCHMARK_HASH = "a" * 64
EXECUTION_HASH = "b" * 64
CONFIGURATION_HASHES = {
    ConditionId.A: "c" * 64,
    ConditionId.B: "d" * 64,
    ConditionId.C: "e" * 64,
}


def _design() -> FullABCHarnessIntegrationDesign:
    return load_full_abc_harness_integration_design(DESIGN_PATH)


def _plan() -> FullABCHarnessIntegrationImplementationPlan:
    return load_full_abc_harness_integration_implementation_plan(IMPLEMENTATION_PATH)


def _adapters() -> FullABCConditionRuntimeAdapterSet:
    return build_full_abc_condition_runtime_adapters(_design())


def _case() -> ReconcileBalanceExtractionCase:
    manifest = load_action_extraction_remediation_manifest(REMEDIATION_MANIFEST_PATH)
    cases = (*manifest.historical_cases, *manifest.added_diagnostic_cases)
    return next(case for case in cases if case.eval_case_id == "formatted-currency-values")


def _scored(condition_id: ConditionId) -> FullABCScoredActionExtraction:
    adapter = _adapters().for_condition(condition_id)
    case = _case()
    return score_full_abc_action_extraction(
        adapter=adapter,
        case=case,
        output_text=case.expected_action.model_dump_json(),
        finish_reason="stop",
        completion_tokens=32,
    )


def _cleanup(
    condition_id: ConditionId,
    status: ActionExtractionCleanupStatus = ActionExtractionCleanupStatus.CLEAN,
) -> FullABCCleanupBridgeResult:
    adapter = _adapters().for_condition(condition_id)
    if status is ActionExtractionCleanupStatus.CLEAN:
        observation = ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGINT",),
        )
    elif status is ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS:
        observation = ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGINT",),
            leaked_semaphore_count=1,
        )
    else:
        observation = ActionExtractionWorkerCleanupObservation(
            return_code=-9,
            port_closed=True,
            application_shutdown_completed=False,
            signal_path=("SIGINT", "SIGTERM", "SIGKILL"),
        )
    return classify_full_abc_worker_cleanup(adapter=adapter, observation=observation)


def _trace(
    condition_id: ConditionId,
    *,
    cleanup_status: ActionExtractionCleanupStatus = ActionExtractionCleanupStatus.CLEAN,
    comparison_pair_id: str = "pair-episode-001-replication-01",
    episode_id: str = "episode-001",
    replication_id: str = "replication-01",
    benchmark_hash: str = BENCHMARK_HASH,
    execution_hash: str = EXECUTION_HASH,
    provider_model_alias: str = "local/qwen2.5-0.5b-instruct",
    configuration_fingerprint: str | None = None,
    cache_namespace_id: str | None = None,
) -> FullABCTraceEnvelope:
    suffix = condition_id.value.lower()
    return build_full_abc_trace_envelope(
        scored=_scored(condition_id),
        cleanup=_cleanup(condition_id, cleanup_status),
        run_id=f"run-{suffix}-001",
        trace_id=UUID(
            f"00000000-0000-0000-0000-00000000000{1 + list(ConditionId).index(condition_id)}"
        ),
        comparison_pair_id=comparison_pair_id,
        episode_id=episode_id,
        replication_id=replication_id,
        cache_namespace_id=cache_namespace_id or f"namespace-{suffix}-001",
        session_id_hash={ConditionId.A: "1" * 64, ConditionId.B: "2" * 64, ConditionId.C: "3" * 64}[
            condition_id
        ],
        provider_model_alias=provider_model_alias,
        benchmark_manifest_hash=benchmark_hash,
        execution_manifest_hash=execution_hash,
        configuration_fingerprint=(configuration_fingerprint or CONFIGURATION_HASHES[condition_id]),
    )


def _context(
    *,
    execution_manifest_frozen: bool = True,
    measured_execution_authorized: bool = True,
    provider_execution_authorized: bool = True,
    gpu_execution_authorized: bool = True,
) -> FullABCComparisonPreflightContext:
    return FullABCComparisonPreflightContext(
        integration_design_sha256=DESIGN_SHA256,
        benchmark_manifest_hash=BENCHMARK_HASH,
        execution_manifest_hash=EXECUTION_HASH,
        expected_configuration_fingerprints=CONFIGURATION_HASHES,
        execution_manifest_frozen=execution_manifest_frozen,
        measured_execution_authorized=measured_execution_authorized,
        provider_execution_authorized=provider_execution_authorized,
        gpu_execution_authorized=gpu_execution_authorized,
    )


def test_implementation_plan_binds_merged_design_and_source() -> None:
    plan = _plan()

    assert plan.source_merge_commit == "430fe12445dce4563274b880f203da175acb567d"
    assert plan.design_blob_sha == "5d1bcb3a4fd26096d2e0d5f8c51e38ef927de0d3"
    assert plan.integration_design_sha256 == DESIGN_SHA256
    assert plan.hardening_source_blob_sha == "d991beb28a70e90a2de6fb805dba53ca5cf16d33"
    assert plan.fingerprint() == IMPLEMENTATION_SHA256


def test_implementation_plan_grants_no_execution_authority() -> None:
    plan = _plan()

    assert plan.execution_manifest_frozen is False
    assert plan.measured_execution_authorized is False
    assert plan.provider_execution_authorized is False
    assert plan.gpu_execution_authorized is False
    assert plan.new_authorization_issued is False
    assert plan.consumed_authorization_reused is False
    assert plan.model_request_performed is False
    assert plan.provider_call_performed is False
    assert plan.gpu_execution_performed is False
    assert plan.next_gate == "full_abc_execution_manifest_asset_inventory"


def test_runtime_adapters_materialize_exact_a_b_c_design() -> None:
    adapters = _adapters()

    assert tuple(adapter.condition_id for adapter in adapters.adapters) == tuple(ConditionId)
    assert adapters.for_condition(ConditionId.A).static_volatile_boundary_enforced is False
    assert adapters.for_condition(ConditionId.B).route_policy is FullABCRoutePolicy.TURN_LOCAL
    assert (
        adapters.for_condition(ConditionId.C).route_policy is FullABCRoutePolicy.CACHE_AFFINITY_TTL
    )
    assert len({adapter.score_entrypoint for adapter in adapters.adapters}) == 1
    assert len({adapter.cleanup_entrypoint for adapter in adapters.adapters}) == 1


def test_runtime_adapter_rejects_condition_specific_route_drift() -> None:
    payload = _adapters().for_condition(ConditionId.B).model_dump(mode="python")
    payload["route_policy"] = FullABCRoutePolicy.CACHE_AFFINITY_TTL

    with pytest.raises(ValidationError, match="route policy"):
        FullABCConditionRuntimeAdapter.model_validate(payload)


def test_shared_scoring_bridge_binds_executed_v2_prompt_identity() -> None:
    scored = _scored(ConditionId.A)

    assert scored.score.first_attempt_task_success is True
    assert scored.score_prompt_policy_sha256 == PROMPT_POLICY_SHA256
    assert scored.score_prompt_policy_sha256 == scored.score.prompt_identity.policy_sha256
    assert (
        scored.score_rendered_prompt_sha256 == scored.score.prompt_identity.rendered_prompt_sha256
    )
    assert scored.raw_output_retained is False
    assert scored.model_request_performed is False


def test_shared_scoring_bridge_retains_failed_quality_outcome() -> None:
    adapter = _adapters().for_condition(ConditionId.B)
    case = _case()
    scored = score_full_abc_action_extraction(
        adapter=adapter,
        case=case,
        output_text="{}",
        finish_reason="stop",
        completion_tokens=2,
    )

    assert scored.score.first_attempt_task_success is False
    assert scored.score.evaluation_failure_codes
    assert scored.score_prompt_policy_sha256 == PROMPT_POLICY_SHA256


def test_cleanup_bridge_returns_clean_only_for_clean_observations() -> None:
    cleanup = _cleanup(ConditionId.A)

    assert cleanup.cleanup_status is ActionExtractionCleanupStatus.CLEAN
    assert cleanup.cleanup_warning_codes == ()
    assert cleanup.decision.cleanup_perfect is True


def test_cleanup_bridge_preserves_warning_qualified_state() -> None:
    cleanup = _cleanup(
        ConditionId.B,
        ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS,
    )

    assert cleanup.cleanup_status is ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS
    assert cleanup.cleanup_warning_codes == (ActionExtractionCleanupWarningCode.LEAKED_SEMAPHORE,)
    assert cleanup.decision.terminally_safe is True


def test_cleanup_bridge_preserves_failed_state() -> None:
    cleanup = _cleanup(ConditionId.C, ActionExtractionCleanupStatus.FAILED)

    assert cleanup.cleanup_status is ActionExtractionCleanupStatus.FAILED
    assert cleanup.decision.infrastructure_failure is True


def test_trace_envelope_contains_exact_frozen_integration_fields() -> None:
    trace = _trace(ConditionId.A)

    assert trace.integration_field_names() == _plan().trace_fields
    assert trace.score_prompt_policy_sha256 == PROMPT_POLICY_SHA256
    assert trace.cleanup_status is ActionExtractionCleanupStatus.CLEAN
    assert trace.raw_prompt_retained is False
    assert trace.raw_model_output_retained is False
    assert trace.raw_provider_payload_retained is False
    assert trace.credentials_retained is False
    assert trace.direct_personal_identifiers_retained is False


def test_trace_builder_rejects_cross_condition_score_and_cleanup() -> None:
    with pytest.raises(ValueError, match="share condition identity"):
        build_full_abc_trace_envelope(
            scored=_scored(ConditionId.A),
            cleanup=_cleanup(ConditionId.B),
            run_id="run-a-001",
            trace_id=UUID("00000000-0000-0000-0000-000000000001"),
            comparison_pair_id="pair-episode-001-replication-01",
            episode_id="episode-001",
            replication_id="replication-01",
            cache_namespace_id="namespace-a-001",
            session_id_hash="1" * 64,
            provider_model_alias="local/qwen2.5-0.5b-instruct",
            benchmark_manifest_hash=BENCHMARK_HASH,
            execution_manifest_hash=EXECUTION_HASH,
            configuration_fingerprint=CONFIGURATION_HASHES[ConditionId.A],
        )


def test_trace_contract_rejects_raw_prompt_retention() -> None:
    payload = _trace(ConditionId.A).model_dump(mode="python")
    payload["raw_prompt_retained"] = True

    with pytest.raises(ValidationError):
        FullABCTraceEnvelope.model_validate(payload)


def test_clean_authorized_pair_passes_quality_and_runtime_preflight() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.A),
        right=_trace(ConditionId.B),
    )

    assert decision.record_shape_valid is True
    assert decision.quality_metric_eligible is True
    assert decision.runtime_metric_eligible is True
    assert decision.failure_codes == ()
    assert decision.warning_codes == ()
    assert decision.provider_cache_claim_eligible is False
    assert decision.claim_generation_permitted is False
    assert decision.rerun_authorized is False


def test_cleanup_warning_preserves_quality_but_blocks_runtime_metrics() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.A),
        right=_trace(
            ConditionId.B,
            cleanup_status=ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS,
        ),
    )

    assert decision.record_shape_valid is True
    assert decision.quality_metric_eligible is True
    assert decision.runtime_metric_eligible is False
    assert decision.failure_codes == ()
    assert decision.warning_codes == (
        FullABCIntegrationPreflightFailureCode.CLEANUP_WARNING_BLOCKS_RUNTIME,
    )


def test_failed_cleanup_blocks_all_comparative_metric_families() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.B_VS_C,
        left=_trace(ConditionId.B),
        right=_trace(ConditionId.C, cleanup_status=ActionExtractionCleanupStatus.FAILED),
    )

    assert decision.record_shape_valid is False
    assert decision.quality_metric_eligible is False
    assert decision.runtime_metric_eligible is False
    assert FullABCIntegrationPreflightFailureCode.CLEANUP_FAILED in decision.failure_codes


def test_current_unfrozen_unauthorized_state_is_explicitly_blocked() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(
            execution_manifest_frozen=False,
            measured_execution_authorized=False,
            provider_execution_authorized=False,
            gpu_execution_authorized=False,
        ),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.A),
        right=_trace(ConditionId.B),
    )

    assert decision.record_shape_valid is True
    assert decision.quality_metric_eligible is False
    assert decision.runtime_metric_eligible is False
    assert FullABCIntegrationPreflightFailureCode.EXECUTION_MANIFEST_UNFROZEN in (
        decision.failure_codes
    )
    assert FullABCIntegrationPreflightFailureCode.MEASURED_EXECUTION_UNAUTHORIZED in (
        decision.failure_codes
    )
    assert FullABCIntegrationPreflightFailureCode.PROVIDER_EXECUTION_UNAUTHORIZED in (
        decision.failure_codes
    )
    assert FullABCIntegrationPreflightFailureCode.GPU_EXECUTION_UNAUTHORIZED in (
        decision.failure_codes
    )


def test_contrast_condition_order_is_fail_closed() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.B),
        right=_trace(ConditionId.A),
    )

    assert FullABCIntegrationPreflightFailureCode.CONDITION_PAIR_MISMATCH in (
        decision.failure_codes
    )
    assert decision.quality_metric_eligible is False


def test_pair_identity_and_episode_mismatch_are_retained() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.A),
        right=_trace(
            ConditionId.B,
            comparison_pair_id="pair-other-001",
            episode_id="episode-002",
        ),
    )

    assert FullABCIntegrationPreflightFailureCode.COMPARISON_PAIR_ID_MISMATCH in (
        decision.failure_codes
    )
    assert FullABCIntegrationPreflightFailureCode.EPISODE_ID_MISMATCH in decision.failure_codes


def test_cross_condition_cache_namespace_reuse_is_blocked() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.A, cache_namespace_id="namespace-shared-001"),
        right=_trace(ConditionId.B, cache_namespace_id="namespace-shared-001"),
    )

    assert FullABCIntegrationPreflightFailureCode.CACHE_NAMESPACE_COLLISION in (
        decision.failure_codes
    )


def test_configuration_fingerprint_drift_is_blocked() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.A),
        right=_trace(ConditionId.B, configuration_fingerprint="f" * 64),
    )

    assert FullABCIntegrationPreflightFailureCode.CONFIGURATION_FINGERPRINT_MISMATCH in (
        decision.failure_codes
    )


def test_manifest_mismatch_is_blocked() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.A),
        right=_trace(
            ConditionId.B,
            benchmark_hash="9" * 64,
            execution_hash="8" * 64,
        ),
    )

    assert FullABCIntegrationPreflightFailureCode.BENCHMARK_MANIFEST_MISMATCH in (
        decision.failure_codes
    )
    assert FullABCIntegrationPreflightFailureCode.EXECUTION_MANIFEST_MISMATCH in (
        decision.failure_codes
    )


def test_provider_model_alias_mismatch_is_blocked() -> None:
    decision = evaluate_full_abc_comparison_preflight(
        context=_context(),
        contrast_id=FullABCCausalContrastId.A_VS_B,
        left=_trace(ConditionId.A),
        right=_trace(ConditionId.B, provider_model_alias="local/other-model"),
    )

    assert FullABCIntegrationPreflightFailureCode.PROVIDER_MODEL_ALIAS_MISMATCH in (
        decision.failure_codes
    )


def test_preflight_context_requires_all_three_condition_fingerprints() -> None:
    with pytest.raises(ValidationError, match="A, B, and C"):
        FullABCComparisonPreflightContext(
            integration_design_sha256=DESIGN_SHA256,
            benchmark_manifest_hash=BENCHMARK_HASH,
            execution_manifest_hash=EXECUTION_HASH,
            expected_configuration_fingerprints={ConditionId.A: "c" * 64},
            execution_manifest_frozen=False,
            measured_execution_authorized=False,
            provider_execution_authorized=False,
            gpu_execution_authorized=False,
        )


def test_json_artifact_is_canonical_single_line() -> None:
    text = IMPLEMENTATION_PATH.read_text(encoding="utf-8")
    payload = json.loads(text)
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    assert text == canonical
    assert "\n" not in text


def test_documentation_preserves_execution_boundary_and_non_claims() -> None:
    adr = ADR_PATH.read_text(encoding="utf-8")
    documentation = DOC_PATH.read_text(encoding="utf-8")

    for text in (adr, documentation):
        assert "full_abc_execution_manifest_asset_inventory" in text
        assert "measured_execution_authorized=false" in text
        assert "provider_execution_authorized=false" in text
        assert "gpu_execution_authorized=false" in text
        assert "does not authorize" in text.lower()
