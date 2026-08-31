from __future__ import annotations

import hashlib
from pathlib import Path

from auragateway.contracts.blinded_quality import ReviewVerdict
from auragateway.local_abc import final_342_analysis_engine_v1 as analysis
from auragateway.local_abc import final_342_execution_producer_v1 as producer
from auragateway.local_abc import final_342_measured_quality_reducers_v1 as quality
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

FINAL_MANIFEST = "f" * 64
RETRIEVAL_FINGERPRINT = "1" * 64
EPISODE_MANIFEST = "2" * 64
RUNTIME_MODEL_FINGERPRINT = "3" * 64


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _route(condition: core.ConditionId) -> core.RouteScheduleId:
    if condition is core.ConditionId.C:
        return core.RouteScheduleId.AFFINITY
    return core.RouteScheduleId.TURN_LOCAL


def _planned_runs() -> tuple[core.PlannedRun, ...]:
    rows: list[core.PlannedRun] = []
    order = 0
    for pair_index in range(54):
        for condition in core.ConditionId:
            run_id = f"functional-{pair_index:03d}-{condition.value}"
            rows.append(
                core.PlannedRun(
                    schema_version="1.0.0",
                    attempt_number=1,
                    benchmark_manifest_sha256="4" * 64,
                    cache_namespace_id=f"namespace-{run_id}",
                    comparison_pair_id=f"functional-pair-{pair_index:03d}",
                    condition_configuration_fingerprint=_sha(f"condition-{condition.value}"),
                    condition_id=condition,
                    episode_id=f"episode-{pair_index % 18:02d}",
                    execution_manifest_sha256=core.EXPECTED_PLANNING_MANIFEST_SHA256,
                    maximum_request_attempts=8,
                    planned_order_index=order,
                    replication_id=f"rep-{pair_index // 18 + 1}",
                    route_schedule_id=_route(condition),
                    run_id=run_id,
                    terminal_classification="not_started",
                    trace_id=f"trace-{run_id}",
                    turn_count=4,
                    workload=core.WorkloadId.FUNCTIONAL,
                )
            )
            order += 1
    for pair_index in range(60):
        for condition in core.ConditionId:
            run_id = f"runtime-{pair_index:03d}-{condition.value}"
            rows.append(
                core.PlannedRun(
                    schema_version="1.0.0",
                    attempt_number=1,
                    benchmark_manifest_sha256="4" * 64,
                    cache_namespace_id=f"namespace-{run_id}",
                    comparison_pair_id=f"runtime-pair-{pair_index:03d}",
                    condition_configuration_fingerprint=_sha(f"condition-{condition.value}"),
                    condition_id=condition,
                    episode_id=f"runtime-episode-{pair_index % 6:02d}",
                    execution_manifest_sha256=core.EXPECTED_PLANNING_MANIFEST_SHA256,
                    maximum_request_attempts=8,
                    planned_order_index=order,
                    replication_id=f"runtime-rep-{pair_index // 6 + 1}",
                    route_schedule_id=_route(condition),
                    run_id=run_id,
                    terminal_classification="not_started",
                    trace_id=f"trace-{run_id}",
                    turn_count=4,
                    workload=core.WorkloadId.RUNTIME_MICROBENCHMARK,
                )
            )
            order += 1
    return tuple(rows)


def _plan_bindings(planned: tuple[core.PlannedRun, ...]) -> tuple[producer.PlanBinding, ...]:
    return tuple(
        producer.PlanBinding(
            planned_order_index=item.planned_order_index,
            run_id=item.run_id,
            trace_id=item.trace_id,
            comparison_pair_id=item.comparison_pair_id,
            workload=item.workload,
            condition_id=item.condition_id,
            route_schedule_id=item.route_schedule_id,
            cache_namespace_sha256=producer.sha256_text(item.cache_namespace_id),
        )
        for item in planned
    )


def _trace_bindings(
    planned: tuple[core.PlannedRun, ...],
) -> tuple[core.RuntimeTraceIdentity, ...]:
    return tuple(
        core.RuntimeTraceIdentity(
            run_id=item.run_id,
            trace_id=item.trace_id,
            final_execution_manifest_sha256=FINAL_MANIFEST,
        )
        for item in planned
    )


def _terminals(
    planned: tuple[core.PlannedRun, ...],
) -> tuple[producer.TrajectoryTerminalRecord, ...]:
    return tuple(
        producer.TrajectoryTerminalRecord(
            run_id=item.run_id,
            trace_id=item.trace_id,
            terminal_state=producer.TrajectoryTerminalState.COMPLETED,
            attempted_request_count=4,
            committed_turn_count=4,
        )
        for item in planned
    )


def _quality_result(item: core.PlannedRun) -> quality.MeasuredQualityRunResult:
    return quality.MeasuredQualityRunResult(
        run_id=item.run_id,
        episode_id=item.episode_id,
        evidence_state=quality.EvidenceState.COMPLETE,
        execution_state=producer.TrajectoryTerminalState.COMPLETED,
        review_resolution_state=quality.ReviewResolutionState.PRIMARY_RESOLVED,
        task_success=True,
        unsafe_behavior_observed=quality.UnsafeBehaviorObservation.NOT_OBSERVED,
        unsafe_behavior_reasons=(),
        structured_output_valid=True,
        citation_support_status=quality.CitationSupportStatus.SUPPORTED,
        unsupported_answer_status=quality.UnsupportedAnswerStatus.NOT_OBSERVED,
        deterministic_quality_passed=True,
        resolved_review_verdict=ReviewVerdict.PASS,
        resolved_failure_labels=(),
        resolved_review_source=quality.ResolvedReviewSource.PRIMARY,
        input_digest=_sha(f"quality-{item.run_id}"),
        machine_readable_errors=(),
    )


def _quality_results(
    planned: tuple[core.PlannedRun, ...],
) -> tuple[quality.MeasuredQualityRunResult, ...]:
    return tuple(
        _quality_result(item) for item in planned if item.workload is core.WorkloadId.FUNCTIONAL
    )


def _token_value(condition: core.ConditionId) -> int:
    return {
        core.ConditionId.A: 100,
        core.ConditionId.B: 80,
        core.ConditionId.C: 60,
    }[condition]


def _measurements(
    planned: tuple[core.PlannedRun, ...],
) -> tuple[producer.TurnMeasurementRecord, ...]:
    records: list[producer.TurnMeasurementRecord] = []
    sequence = 1
    for item in planned:
        if item.workload is not core.WorkloadId.RUNTIME_MICROBENCHMARK:
            continue
        route = core.realize_route(item.route_schedule_id)
        namespace_sha = producer.sha256_text(item.cache_namespace_id)
        for turn_index in (1, 2, 3, 4):
            route_identity = core.CacheResidencyIdentity(
                worker_id=route[turn_index - 1],
                worker_generation=1,
                runtime_model_fingerprint=RUNTIME_MODEL_FINGERPRINT,
            )
            warm_evidence = core.WarmTurnEvidence(
                turn_index=turn_index,
                session_id_hash=_sha(f"session-{item.run_id}"),
                cache_namespace_sha256=namespace_sha,
                static_prefix_fingerprint=_sha(f"prefix-{item.run_id}"),
                residency_identity=route_identity,
                affinity_epoch=0,
                request_started_monotonic_ns=sequence * 10,
                request_completed_monotonic_ns=sequence * 10 + 1,
                request_completed=True,
            )
            if turn_index == 1:
                warm_decision = core.WarmEligibilityDecision(
                    classification=core.WarmClassification.COLD,
                    decision_code=core.WarmDecisionCode.FIRST_TURN_COLD,
                )
            else:
                warm_decision = core.WarmEligibilityDecision(
                    classification=core.WarmClassification.WARM_ELIGIBLE,
                    decision_code=core.WarmDecisionCode.PRIOR_ELIGIBLE_REQUEST_MATCHED,
                    matched_prior_turn_index=max(1, turn_index - 2),
                )
            records.append(
                producer.TurnMeasurementRecord(
                    global_attempt_sequence=sequence,
                    run_id=item.run_id,
                    trace_id=item.trace_id,
                    turn_index=turn_index,
                    trace_identity=core.RuntimeTraceIdentity(
                        run_id=item.run_id,
                        trace_id=item.trace_id,
                        final_execution_manifest_sha256=FINAL_MANIFEST,
                    ),
                    route_identity=route_identity,
                    warm_evidence=warm_evidence,
                    warm_decision=warm_decision,
                    prompt_token_count=1000,
                    server_usage_prompt_tokens=1000,
                    cached_prefix_tokens=900 if turn_index > 1 else 0,
                    newly_computed_prefill_tokens=_token_value(item.condition_id),
                    prefill_duration_ms=10.0,
                    time_to_first_token_ms=20.0,
                    end_to_end_latency_ms=30.0,
                    finish_reason="stop",
                    output_sha256=_sha(f"output-{item.run_id}-{turn_index}"),
                )
            )
            sequence += 1
    return tuple(records)


def _base_input() -> analysis.Final342AnalysisInput:
    planned = _planned_runs()
    return analysis.Final342AnalysisInput(
        final_execution_manifest_sha256=FINAL_MANIFEST,
        bundle_verification=analysis.BundleVerification(
            receipt=producer.EvidenceBundleReceipt(
                bundle_manifest_sha256="5" * 64,
                evidence_archive_sha256="6" * 64,
                member_count=8,
            ),
            schema_and_hash_verified=True,
        ),
        condition_identities=tuple(
            analysis.ConditionIdentity(
                condition_id=condition,
                retrieval_configuration_fingerprint=RETRIEVAL_FINGERPRINT,
                episode_manifest_sha256=EPISODE_MANIFEST,
            )
            for condition in core.ConditionId
        ),
        planned_runs=planned,
        plan_bindings=_plan_bindings(planned),
        trace_bindings=_trace_bindings(planned),
        trajectory_terminals=_terminals(planned),
        measurements=_measurements(planned),
        measured_quality_results=_quality_results(planned),
    )


def _functional_run_ids(
    value: analysis.Final342AnalysisInput,
    condition: core.ConditionId,
) -> tuple[str, ...]:
    return tuple(
        item.run_id
        for item in value.planned_runs
        if item.workload is core.WorkloadId.FUNCTIONAL and item.condition_id is condition
    )


def _replace_quality(
    value: analysis.Final342AnalysisInput,
    updates: dict[str, dict[str, object]],
) -> analysis.Final342AnalysisInput:
    results = tuple(
        item.model_copy(update=updates.get(item.run_id, {}))
        for item in value.measured_quality_results
    )
    return value.model_copy(update={"measured_quality_results": results})


def test_complete_analysis_supports_three_frozen_claim_families() -> None:
    result = analysis.analyze_final_342(_base_input())

    assert result.evidence_state is analysis.AnalysisEvidenceState.COMPLETE
    assert result.run_accountability.accountability_complete is True
    assert result.run_accountability.planned_run_count == 342
    assert result.quality_noninferiority.state is analysis.QualityGateState.PASSED
    assert tuple(item.sample_count for item in result.quality_noninferiority.conditions) == (
        54,
        54,
        54,
    )
    assert tuple(item.eligible_pair_count for item in result.runtime_contrasts) == (60, 60, 60)
    assert tuple(item.decision for item in result.claim_decisions) == (
        analysis.ClaimDecision.SUPPORTED,
        analysis.ClaimDecision.SUPPORTED,
        analysis.ClaimDecision.SUPPORTED,
    )
    assert result.feedback_claim_policy.measured_feedback_required_for_north_star_claims is False


def test_paired_bootstrap_is_deterministic_and_uses_frozen_seed() -> None:
    differences = tuple([-20] * 60)
    first = analysis.paired_bootstrap_interval(differences)
    second = analysis.paired_bootstrap_interval(differences)

    assert first == second
    assert first.sample_count == 10000
    assert first.seed == 20260712
    assert first.point_estimate == -20.0
    assert first.lower_bound == -20.0
    assert first.upper_bound == -20.0


def test_task_success_noninferiority_passes_two_failures_and_fails_three() -> None:
    base = _base_input()
    b_runs = _functional_run_ids(base, core.ConditionId.B)

    two_failures = _replace_quality(
        base,
        {
            run_id: {"task_success": False, "deterministic_quality_passed": False}
            for run_id in b_runs[:2]
        },
    )
    two_result = analysis.analyze_final_342(two_failures)
    assert two_result.quality_noninferiority.state is analysis.QualityGateState.PASSED

    three_failures = _replace_quality(
        base,
        {
            run_id: {"task_success": False, "deterministic_quality_passed": False}
            for run_id in b_runs[:3]
        },
    )
    three_result = analysis.analyze_final_342(three_failures)
    assert three_result.quality_noninferiority.state is analysis.QualityGateState.FAILED
    assert all(
        item.decision is analysis.ClaimDecision.BLOCKED for item in three_result.claim_decisions
    )


def test_citation_unsupported_and_unsafe_regressions_each_fail_quality() -> None:
    base = _base_input()
    run_id = _functional_run_ids(base, core.ConditionId.B)[0]

    citation = _replace_quality(
        base,
        {run_id: {"citation_support_status": quality.CitationSupportStatus.UNSUPPORTED}},
    )
    assert (
        analysis.analyze_final_342(citation).quality_noninferiority.state
        is analysis.QualityGateState.FAILED
    )

    unsupported = _replace_quality(
        base,
        {run_id: {"unsupported_answer_status": quality.UnsupportedAnswerStatus.OBSERVED}},
    )
    assert (
        analysis.analyze_final_342(unsupported).quality_noninferiority.state
        is analysis.QualityGateState.FAILED
    )

    unsafe = _replace_quality(
        base,
        {
            run_id: {
                "unsafe_behavior_observed": quality.UnsafeBehaviorObservation.OBSERVED,
                "unsafe_behavior_reasons": (quality.UnsafeBehaviorReason.RETRY_POLICY_VIOLATION,),
            }
        },
    )
    assert (
        analysis.analyze_final_342(unsafe).quality_noninferiority.state
        is analysis.QualityGateState.FAILED
    )


def test_missing_functional_quality_is_evidence_incomplete_not_inferred_failure() -> None:
    base = _base_input()
    incomplete = base.model_copy(
        update={"measured_quality_results": base.measured_quality_results[:-1]}
    )
    result = analysis.analyze_final_342(incomplete)

    assert result.evidence_state is analysis.AnalysisEvidenceState.EVIDENCE_INCOMPLETE
    assert (
        analysis.AnalysisErrorCode.FUNCTIONAL_QUALITY_LEDGER_INCOMPLETE
        in result.machine_readable_errors
    )
    assert result.quality_noninferiority.state is analysis.QualityGateState.BLOCKED


def test_explicit_failed_functional_trajectory_is_complete_task_non_success() -> None:
    base = _base_input()
    run_id = _functional_run_ids(base, core.ConditionId.A)[0]
    planned = next(item for item in base.planned_runs if item.run_id == run_id)
    terminals = tuple(
        producer.TrajectoryTerminalRecord(
            run_id=item.run_id,
            trace_id=item.trace_id,
            terminal_state=producer.TrajectoryTerminalState.FAILED,
            attempted_request_count=1,
            committed_turn_count=0,
            failure_code="provider_failure",
        )
        if item.run_id == run_id
        else item
        for item in base.trajectory_terminals
    )
    failed_quality = quality.MeasuredQualityRunResult(
        run_id=run_id,
        episode_id=planned.episode_id,
        evidence_state=quality.EvidenceState.COMPLETE,
        execution_state=producer.TrajectoryTerminalState.FAILED,
        review_resolution_state=quality.ReviewResolutionState.NOT_REQUIRED,
        task_success=False,
        unsafe_behavior_observed=quality.UnsafeBehaviorObservation.NOT_OBSERVED,
        unsafe_behavior_reasons=(),
        structured_output_valid=None,
        citation_support_status=quality.CitationSupportStatus.NOT_EVALUABLE,
        unsupported_answer_status=quality.UnsupportedAnswerStatus.NOT_EVALUABLE,
        deterministic_quality_passed=None,
        resolved_review_verdict=None,
        resolved_failure_labels=(),
        resolved_review_source=quality.ResolvedReviewSource.NONE,
        input_digest=_sha(f"failed-{run_id}"),
        machine_readable_errors=(),
    )
    results = tuple(
        failed_quality if item.run_id == run_id else item for item in base.measured_quality_results
    )
    value = base.model_copy(
        update={"trajectory_terminals": terminals, "measured_quality_results": results}
    )
    result = analysis.analyze_final_342(value)

    assert result.evidence_state is analysis.AnalysisEvidenceState.COMPLETE
    condition_a = result.quality_noninferiority.conditions[0]
    assert condition_a.task_success_count == 53
    assert condition_a.sample_count == 54


def test_missing_terminal_record_is_evidence_incomplete() -> None:
    base = _base_input()
    value = base.model_copy(update={"trajectory_terminals": base.trajectory_terminals[:-1]})
    result = analysis.analyze_final_342(value)

    assert result.evidence_state is analysis.AnalysisEvidenceState.EVIDENCE_INCOMPLETE
    assert analysis.AnalysisErrorCode.TERMINAL_LEDGER_INCOMPLETE in result.machine_readable_errors


def test_missing_cold_measurements_do_not_block_primary_warm_endpoint() -> None:
    base = _base_input()
    measurements = tuple(item for item in base.measurements if item.turn_index != 1)
    result = analysis.analyze_final_342(base.model_copy(update={"measurements": measurements}))

    assert result.evidence_state is analysis.AnalysisEvidenceState.COMPLETE
    assert all(
        item.state is analysis.RuntimeEndpointState.AVAILABLE for item in result.runtime_endpoints
    )
    assert all(item.cold_turn_observed is False for item in result.runtime_endpoints)
    assert all(item.decision is analysis.ClaimDecision.SUPPORTED for item in result.claim_decisions)


def test_missing_candidate_measurement_blocks_affected_runtime_claim() -> None:
    base = _base_input()
    target = next(
        item
        for item in base.measurements
        if item.run_id == "runtime-000-B" and item.turn_index == 2
    )
    measurements = tuple(item for item in base.measurements if item is not target)
    result = analysis.analyze_final_342(base.model_copy(update={"measurements": measurements}))

    endpoint = next(item for item in result.runtime_endpoints if item.run_id == "runtime-000-B")
    assert endpoint.state is analysis.RuntimeEndpointState.EVIDENCE_INCOMPLETE
    assert result.evidence_state is analysis.AnalysisEvidenceState.EVIDENCE_INCOMPLETE
    assert result.runtime_contrasts[0].state is analysis.RuntimeContrastState.BLOCKED


def test_non_warm_candidate_turn_is_excluded_without_becoming_error() -> None:
    base = _base_input()
    measurements = tuple(
        item.model_copy(
            update={
                "warm_decision": core.WarmEligibilityDecision(
                    classification=core.WarmClassification.COLD,
                    decision_code=core.WarmDecisionCode.NO_ELIGIBLE_PRIOR_REQUEST,
                )
            }
        )
        if item.run_id == "runtime-000-A" and item.turn_index == 2
        else item
        for item in base.measurements
    )
    result = analysis.analyze_final_342(base.model_copy(update={"measurements": measurements}))
    endpoint = next(item for item in result.runtime_endpoints if item.run_id == "runtime-000-A")

    assert result.evidence_state is analysis.AnalysisEvidenceState.COMPLETE
    assert endpoint.state is analysis.RuntimeEndpointState.AVAILABLE
    assert endpoint.warm_eligible_turn_count == 2
    assert endpoint.warm_ineligible_turn_count == 1


def test_route_realization_violation_blocks_route_dependent_contrast_without_guessing() -> None:
    base = _base_input()
    target = next(
        item
        for item in base.measurements
        if item.run_id == "runtime-000-B" and item.turn_index == 3
    )
    wrong_worker = (
        core.WorkerId.WORKER_2
        if target.route_identity.worker_id is core.WorkerId.WORKER_1
        else core.WorkerId.WORKER_1
    )
    wrong_route = target.route_identity.model_copy(update={"worker_id": wrong_worker})
    wrong_evidence = target.warm_evidence.model_copy(update={"residency_identity": wrong_route})
    altered = target.model_copy(
        update={"route_identity": wrong_route, "warm_evidence": wrong_evidence}
    )
    measurements = tuple(altered if item is target else item for item in base.measurements)
    result = analysis.analyze_final_342(base.model_copy(update={"measurements": measurements}))
    endpoint = next(item for item in result.runtime_endpoints if item.run_id == "runtime-000-B")

    assert result.evidence_state is analysis.AnalysisEvidenceState.COMPLETE
    assert endpoint.state is analysis.RuntimeEndpointState.INELIGIBLE
    assert endpoint.route_realization_valid is False
    assert result.runtime_contrasts[0].state is analysis.RuntimeContrastState.BLOCKED
    assert result.claim_decisions[0].decision is analysis.ClaimDecision.BLOCKED


def test_final_manifest_trace_binding_mismatch_is_evidence_incomplete() -> None:
    base = _base_input()
    first = base.trace_bindings[0].model_copy(update={"final_execution_manifest_sha256": "e" * 64})
    value = base.model_copy(update={"trace_bindings": (first, *base.trace_bindings[1:])})
    result = analysis.analyze_final_342(value)

    assert result.evidence_state is analysis.AnalysisEvidenceState.EVIDENCE_INCOMPLETE
    assert (
        analysis.AnalysisErrorCode.FINAL_EXECUTION_MANIFEST_MISMATCH
        in result.machine_readable_errors
    )


def test_repository_validator_preserves_non_authorizing_boundary() -> None:
    summary = analysis.validate(Path("."))

    assert summary["status"] == "FINAL_342_ANALYSIS_ENGINE_V1_VALID"
    assert summary["planned_trajectory_count"] == 342
    assert summary["measured_feedback_required_for_north_star_claims"] is False
    assert summary["producer_modified"] is False
    assert summary["manifest_freeze_permitted"] is False
    assert summary["final_measured_abc_execution_authorized"] is False


def test_retrieval_configuration_drift_blocks_quality_without_becoming_missing_evidence() -> None:
    base = _base_input()
    identities = tuple(
        item.model_copy(update={"retrieval_configuration_fingerprint": "9" * 64})
        if item.condition_id is core.ConditionId.C
        else item
        for item in base.condition_identities
    )
    value = base.model_copy(update={"condition_identities": identities})
    result = analysis.analyze_final_342(value)

    assert result.evidence_state is analysis.AnalysisEvidenceState.COMPLETE
    assert result.quality_noninferiority.state is analysis.QualityGateState.BLOCKED
    assert all(item.decision is analysis.ClaimDecision.BLOCKED for item in result.claim_decisions)


def test_bundle_verification_failure_blocks_all_claims() -> None:
    base = _base_input()
    bundle = base.bundle_verification.model_copy(update={"schema_and_hash_verified": False})
    result = analysis.analyze_final_342(base.model_copy(update={"bundle_verification": bundle}))

    assert result.evidence_state is analysis.AnalysisEvidenceState.EVIDENCE_INCOMPLETE
    assert analysis.AnalysisErrorCode.BUNDLE_VERIFICATION_FAILED in result.machine_readable_errors
    assert all(item.decision is analysis.ClaimDecision.BLOCKED for item in result.claim_decisions)


def test_complete_zero_runtime_difference_is_not_established_not_blocked() -> None:
    base = _base_input()
    measurements = tuple(
        item.model_copy(update={"newly_computed_prefill_tokens": 100})
        if item.turn_index in (2, 3, 4)
        else item
        for item in base.measurements
    )
    result = analysis.analyze_final_342(base.model_copy(update={"measurements": measurements}))

    assert result.evidence_state is analysis.AnalysisEvidenceState.COMPLETE
    assert result.quality_noninferiority.state is analysis.QualityGateState.PASSED
    assert all(
        item.state is analysis.RuntimeContrastState.COMPLETE for item in result.runtime_contrasts
    )
    assert all(
        item.decision is analysis.ClaimDecision.NOT_ESTABLISHED for item in result.claim_decisions
    )
