"""Tests for final-342 per-run measured-quality reducers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from auragateway.contracts.blinded_quality import (
    AdjudicationRecord,
    BlindedQualityRubric,
    CriterionScore,
    QualityReviewRecord,
    ReviewRole,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality import (
    DeterministicQualityResult,
    QualityCheckName,
    QualityCheckResult,
    QualityCheckStatus,
)
from auragateway.contracts.retrieval_eval import TerminalDecision
from auragateway.evals import blinded_quality as blinded_eval
from auragateway.local_abc import final_342_execution_producer_v1 as producer
from auragateway.local_abc import final_342_measured_quality_reducers_v1 as reducer
from auragateway.local_abc import final_342_measured_review_design_v1 as review_design
from auragateway.local_abc import final_342_measured_review_successor_v1 as review_successor
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

ROOT = Path(__file__).resolve().parents[3]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _rubric() -> BlindedQualityRubric:
    raw = json.loads((ROOT / reducer.RUBRIC_PATH).read_text(encoding="utf-8"))
    return BlindedQualityRubric.model_validate(raw)


def _schedule() -> review_successor.ProtectedSchedule:
    return review_successor.derive_protected_schedule(ROOT)


def _plan(
    *,
    run_id: str = "run-functional-test-primary-only",
    condition_id: core.ConditionId = core.ConditionId.A,
) -> producer.PlanBinding:
    return producer.PlanBinding(
        planned_order_index=0,
        run_id=run_id,
        trace_id=f"trace-{_sha(run_id)[:16]}",
        comparison_pair_id="pair-test-001",
        workload=core.WorkloadId.FUNCTIONAL,
        condition_id=condition_id,
        route_schedule_id=core.RouteScheduleId.TURN_LOCAL,
        cache_namespace_sha256=_sha(f"namespace|{run_id}"),
    )


def _route_identity(
    plan: producer.PlanBinding,
    turn_index: int,
    *,
    unsafe: bool = False,
) -> core.CacheResidencyIdentity:
    worker_id = core.realize_route(plan.route_schedule_id)[turn_index - 1]
    if unsafe:
        worker_id = (
            core.WorkerId.WORKER_2
            if worker_id is core.WorkerId.WORKER_1
            else core.WorkerId.WORKER_1
        )
    return core.CacheResidencyIdentity(
        worker_id=worker_id,
        worker_generation=1,
        runtime_model_fingerprint=_sha("runtime-model"),
    )


def _execution_evidence(
    plan: producer.PlanBinding,
    *,
    retry_turn_one: bool = False,
    unsafe_retry: bool = False,
    unsafe_route: bool = False,
) -> tuple[
    tuple[producer.AttemptReservation, ...],
    tuple[producer.TransportOutcomeRecord, ...],
]:
    reservations: list[producer.AttemptReservation] = []
    outcomes: list[producer.TransportOutcomeRecord] = []
    sequence = 1

    for turn_index in range(1, 5):
        first = producer.AttemptReservation(
            global_attempt_sequence=sequence,
            run_id=plan.run_id,
            trace_id=plan.trace_id,
            turn_index=turn_index,
            attempt_index=1,
            logical_request_fingerprint=_sha(f"{plan.run_id}|turn|{turn_index}"),
            route_identity=_route_identity(
                plan,
                turn_index,
                unsafe=unsafe_route and turn_index == 1,
            ),
            retry_backoff_seconds=0,
        )
        reservations.append(first)

        if retry_turn_one and turn_index == 1:
            outcomes.append(
                producer.TransportOutcomeRecord(
                    global_attempt_sequence=sequence,
                    outcome=(
                        core.AttemptOutcome.AMBIGUOUS
                        if unsafe_retry
                        else core.AttemptOutcome.NO_RESPONSE
                    ),
                    retryable=not unsafe_retry,
                    http_completed=False,
                    error_code="TEST_FIRST_ATTEMPT_FAILED",
                    safe_message="Synthetic first-attempt failure.",
                )
            )
            sequence += 1
            reservations.append(
                producer.AttemptReservation(
                    global_attempt_sequence=sequence,
                    run_id=plan.run_id,
                    trace_id=plan.trace_id,
                    turn_index=turn_index,
                    attempt_index=2,
                    logical_request_fingerprint=first.logical_request_fingerprint,
                    route_identity=first.route_identity,
                    retry_backoff_seconds=producer.RETRY_BACKOFF_SECONDS,
                )
            )
            outcomes.append(
                producer.TransportOutcomeRecord(
                    global_attempt_sequence=sequence,
                    outcome=core.AttemptOutcome.SUCCEEDED,
                    retryable=False,
                    http_completed=True,
                    http_status=200,
                    response_sha256=_sha(f"response|{sequence}"),
                )
            )
        else:
            outcomes.append(
                producer.TransportOutcomeRecord(
                    global_attempt_sequence=sequence,
                    outcome=core.AttemptOutcome.SUCCEEDED,
                    retryable=False,
                    http_completed=True,
                    http_status=200,
                    response_sha256=_sha(f"response|{sequence}"),
                )
            )
        sequence += 1

    return tuple(reservations), tuple(outcomes)


def _captures(
    run_id: str,
    episode_id: str,
) -> tuple[review_successor.ProtectedTurnCapture, ...]:
    captures: list[review_successor.ProtectedTurnCapture] = []
    review_item_id = core.protected_review_id(run_id)
    for turn_index in range(1, 5):
        output = {"turn": turn_index, "decision": "answer"}
        captures.append(
            review_successor.ProtectedTurnCapture(
                run_id=run_id,
                review_item_id=review_item_id,
                episode_id=episode_id,
                turn_index=turn_index,
                user_message=f"user-{turn_index}",
                assistant_output=output,
                response_sha256=review_successor.sha256_bytes(
                    review_successor.canonical_json_bytes(output)
                ),
            )
        )
    return tuple(captures)


def _deterministic_result(
    episode_id: str,
    *,
    failed_check: QualityCheckName | None = None,
    failure_label: EpisodeFailureLabel = EpisodeFailureLabel.TASK_INSUFFICIENT,
) -> DeterministicQualityResult:
    checks: list[QualityCheckResult] = []
    failures: list[EpisodeFailureLabel] = []
    for check_name in QualityCheckName:
        if check_name is failed_check:
            checks.append(
                QualityCheckResult(
                    check_name=check_name,
                    status=QualityCheckStatus.FAILED,
                    failure_label=failure_label,
                )
            )
            failures.append(failure_label)
        else:
            checks.append(
                QualityCheckResult(
                    check_name=check_name,
                    status=QualityCheckStatus.PASSED,
                )
            )

    return DeterministicQualityResult(
        trace_id="quality-trace-final-342-test",
        episode_id=episode_id,
        output_sha256=_sha(f"candidate|{episode_id}"),
        retrieval_configuration_fingerprint=_sha("retrieval-config"),
        structured_output_valid=True,
        terminal_decision=TerminalDecision.ANSWER,
        checks=tuple(checks),
        failure_labels=tuple(failures),
        deterministic_quality_passed=failed_check is None,
    )


def _scores(
    *,
    safety_score: int = 3,
    task_score: int = 3,
) -> tuple[CriterionScore, ...]:
    values = {
        criterion: (
            safety_score
            if criterion is RubricCriterion.SAFETY
            else task_score
            if criterion is RubricCriterion.TASK_CORRECTNESS
            else 3
        )
        for criterion in RubricCriterion
    }
    return tuple(
        CriterionScore(
            criterion=criterion,
            score=values[criterion],
            evidence_note_sha256=_sha(f"note|{criterion.value}|{values[criterion]}"),
        )
        for criterion in RubricCriterion
    )


def _review(
    run_id: str,
    episode_id: str,
    role: ReviewRole,
    *,
    scores: tuple[CriterionScore, ...] | None = None,
    failure_labels: tuple[EpisodeFailureLabel, ...] = (),
    forced_verdict: ReviewVerdict | None = None,
    reviewer_seed: str | None = None,
) -> QualityReviewRecord:
    role_name: Literal["primary", "secondary"]
    if role is ReviewRole.PRIMARY:
        role_name = "primary"
    elif role is ReviewRole.SECONDARY:
        role_name = "secondary"
    else:
        raise AssertionError("test helper does not build adjudicator review records")
    selected_scores = scores if scores is not None else _scores()
    rubric = _rubric()
    verdict = (
        forced_verdict
        if forced_verdict is not None
        else blinded_eval.expected_verdict(
            selected_scores,
            len(failure_labels),
            rubric,
        )
    )
    review_item_id = core.protected_review_id(run_id)
    return QualityReviewRecord(
        review_id=review_design.role_assignment_id(review_item_id, role_name),
        episode_id=episode_id,
        reviewer_id_sha256=_sha(reviewer_seed or f"reviewer|{role_name}"),
        role=role,
        criterion_scores=selected_scores,
        failure_labels=failure_labels,
        verdict=verdict,
        rationale_sha256=_sha(f"rationale|{role_name}"),
    )


def _adjudication(
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
    *,
    scores: tuple[CriterionScore, ...] | None = None,
    failure_labels: tuple[EpisodeFailureLabel, ...] = (),
) -> AdjudicationRecord:
    selected_scores = scores if scores is not None else _scores()
    rubric = _rubric()
    verdict = blinded_eval.expected_verdict(
        selected_scores,
        len(failure_labels),
        rubric,
    )
    return AdjudicationRecord(
        episode_id=primary.episode_id,
        primary_review_id=primary.review_id,
        secondary_review_id=secondary.review_id,
        adjudicator_id_sha256=_sha("adjudicator"),
        final_criterion_scores=selected_scores,
        final_failure_labels=failure_labels,
        final_verdict=verdict,
        rationale_sha256=_sha("adjudication-rationale"),
    )


def _input(
    *,
    plan: producer.PlanBinding | None = None,
    episode_id: str = "ep-func-001",
    failed_execution: bool = False,
    captures: tuple[review_successor.ProtectedTurnCapture, ...] | None = None,
    deterministic: DeterministicQualityResult | None = None,
    primary: QualityReviewRecord | None = None,
    secondary: QualityReviewRecord | None = None,
    adjudication: AdjudicationRecord | None = None,
    retry_turn_one: bool = False,
    unsafe_retry: bool = False,
    unsafe_route: bool = False,
) -> reducer.MeasuredQualityRunInput:
    selected_plan = plan if plan is not None else _plan()
    attempts, outcomes = _execution_evidence(
        selected_plan,
        retry_turn_one=retry_turn_one,
        unsafe_retry=unsafe_retry,
        unsafe_route=unsafe_route,
    )
    selected_captures: tuple[review_successor.ProtectedTurnCapture, ...]
    selected_deterministic: DeterministicQualityResult | None
    selected_primary: QualityReviewRecord | None

    if failed_execution:
        attempts = attempts[:1]
        outcomes = outcomes[:1]
        terminal = producer.TrajectoryTerminalRecord(
            run_id=selected_plan.run_id,
            trace_id=selected_plan.trace_id,
            terminal_state=producer.TrajectoryTerminalState.FAILED,
            attempted_request_count=1,
            committed_turn_count=0,
            failure_code="TEST_EXECUTION_FAILED",
        )
        selected_captures = ()
        selected_deterministic = None
        selected_primary = None
    else:
        terminal = producer.TrajectoryTerminalRecord(
            run_id=selected_plan.run_id,
            trace_id=selected_plan.trace_id,
            terminal_state=producer.TrajectoryTerminalState.COMPLETED,
            attempted_request_count=len(attempts),
            committed_turn_count=4,
        )
        selected_captures = (
            captures if captures is not None else _captures(selected_plan.run_id, episode_id)
        )
        selected_deterministic = (
            deterministic if deterministic is not None else _deterministic_result(episode_id)
        )
        selected_primary = (
            primary
            if primary is not None
            else _review(
                selected_plan.run_id,
                episode_id,
                ReviewRole.PRIMARY,
            )
        )

    return reducer.MeasuredQualityRunInput(
        run_id=selected_plan.run_id,
        episode_id=episode_id,
        plan=selected_plan,
        terminal=terminal,
        attempt_reservations=attempts,
        transport_outcomes=outcomes,
        protected_captures=selected_captures,
        deterministic_quality=selected_deterministic,
        primary_review=selected_primary,
        secondary_review=secondary,
        adjudication=adjudication,
        rubric=_rubric(),
        review_schedule=_schedule(),
    )


def _selected_secondary_case() -> tuple[producer.PlanBinding, str]:
    selected = _schedule().entries[0]
    plan = _plan(
        run_id=selected.run_id,
        condition_id=core.ConditionId(selected.condition_id),
    )
    return plan, selected.episode_id


def test_current_reducer_contract_validates_without_execution() -> None:
    result = reducer.validate(ROOT)

    assert result["status"] == "FINAL_342_MEASURED_QUALITY_REDUCERS_V1_VALID"
    assert result["per_run_measured_quality_reducers_implemented"] is True
    assert result["producer_modified"] is False
    assert result["historical_gate6_modified"] is False
    assert result["aggregate_noninferiority_implemented"] is False
    assert result["manifest_freeze_permitted"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
    assert result["next_gate"] == "AUTHOR_FINAL_342_MEASURED_FEEDBACK_SUCCESSOR_V1"


def test_completed_captured_primary_pass_is_task_success() -> None:
    result = reducer.reduce_measured_quality_run(_input())

    assert result.evidence_state is reducer.EvidenceState.COMPLETE
    assert result.task_success is True
    assert result.review_resolution_state is reducer.ReviewResolutionState.PRIMARY_RESOLVED
    assert result.resolved_review_source is reducer.ResolvedReviewSource.PRIMARY
    assert result.resolved_review_verdict is ReviewVerdict.PASS


def test_completed_captured_primary_fail_is_task_non_success() -> None:
    plan = _plan()
    primary = _review(
        plan.run_id,
        "ep-func-001",
        ReviewRole.PRIMARY,
        failure_labels=(EpisodeFailureLabel.TASK_INSUFFICIENT,),
    )

    result = reducer.reduce_measured_quality_run(_input(plan=plan, primary=primary))

    assert result.evidence_state is reducer.EvidenceState.COMPLETE
    assert result.task_success is False
    assert result.resolved_review_verdict is ReviewVerdict.FAIL


def test_explicit_execution_failure_without_candidate_is_task_non_success() -> None:
    result = reducer.reduce_measured_quality_run(_input(failed_execution=True))

    assert result.evidence_state is reducer.EvidenceState.COMPLETE
    assert result.task_success is False
    assert result.review_resolution_state is reducer.ReviewResolutionState.NOT_REQUIRED
    assert result.resolved_review_verdict is None


def test_candidate_capture_gap_is_evidence_incomplete_not_task_failure() -> None:
    plan = _plan()
    captures = _captures(plan.run_id, "ep-func-001")[:3]
    value = _input(plan=plan, captures=captures)
    payload = value.model_dump(mode="python")
    payload["primary_review"] = None

    result = reducer.reduce_measured_quality_run(
        reducer.MeasuredQualityRunInput.model_validate(payload)
    )

    assert result.evidence_state is reducer.EvidenceState.EVIDENCE_INCOMPLETE
    assert result.task_success is None
    assert reducer.ReducerErrorCode.MISSING_PROTECTED_CAPTURE in result.machine_readable_errors
    assert reducer.ReducerErrorCode.MISSING_PRIMARY_REVIEW not in result.machine_readable_errors


def test_secondary_agreement_keeps_primary_authoritative() -> None:
    plan, episode_id = _selected_secondary_case()
    primary = _review(plan.run_id, episode_id, ReviewRole.PRIMARY)
    secondary = _review(
        plan.run_id,
        episode_id,
        ReviewRole.SECONDARY,
        reviewer_seed="secondary-independent",
    )

    result = reducer.reduce_measured_quality_run(
        _input(
            plan=plan,
            episode_id=episode_id,
            primary=primary,
            secondary=secondary,
        )
    )

    assert result.evidence_state is reducer.EvidenceState.COMPLETE
    assert result.task_success is True
    assert (
        result.review_resolution_state
        is reducer.ReviewResolutionState.PRIMARY_RESOLVED_AFTER_SECONDARY_AGREEMENT
    )
    assert result.resolved_review_source is reducer.ResolvedReviewSource.PRIMARY


def test_non_material_secondary_score_difference_does_not_require_adjudication() -> None:
    plan, episode_id = _selected_secondary_case()
    primary = _review(plan.run_id, episode_id, ReviewRole.PRIMARY)
    secondary = _review(
        plan.run_id,
        episode_id,
        ReviewRole.SECONDARY,
        scores=_scores(task_score=4),
        reviewer_seed="secondary-score-difference",
    )

    result = reducer.reduce_measured_quality_run(
        _input(
            plan=plan,
            episode_id=episode_id,
            primary=primary,
            secondary=secondary,
        )
    )

    assert result.evidence_state is reducer.EvidenceState.COMPLETE
    assert result.resolved_review_source is reducer.ResolvedReviewSource.PRIMARY
    assert result.resolved_review_verdict is ReviewVerdict.PASS


def test_material_disagreement_without_adjudication_is_incomplete() -> None:
    plan, episode_id = _selected_secondary_case()
    primary = _review(plan.run_id, episode_id, ReviewRole.PRIMARY)
    secondary = _review(
        plan.run_id,
        episode_id,
        ReviewRole.SECONDARY,
        failure_labels=(EpisodeFailureLabel.TASK_INSUFFICIENT,),
        reviewer_seed="secondary-disagreement",
    )

    result = reducer.reduce_measured_quality_run(
        _input(
            plan=plan,
            episode_id=episode_id,
            primary=primary,
            secondary=secondary,
        )
    )

    assert result.evidence_state is reducer.EvidenceState.EVIDENCE_INCOMPLETE
    assert result.task_success is None
    assert reducer.ReducerErrorCode.MISSING_REQUIRED_ADJUDICATION in result.machine_readable_errors


def test_material_disagreement_uses_valid_adjudication_as_authority() -> None:
    plan, episode_id = _selected_secondary_case()
    primary = _review(plan.run_id, episode_id, ReviewRole.PRIMARY)
    secondary = _review(
        plan.run_id,
        episode_id,
        ReviewRole.SECONDARY,
        failure_labels=(EpisodeFailureLabel.TASK_INSUFFICIENT,),
        reviewer_seed="secondary-disagreement",
    )
    adjudication = _adjudication(primary, secondary)

    result = reducer.reduce_measured_quality_run(
        _input(
            plan=plan,
            episode_id=episode_id,
            primary=primary,
            secondary=secondary,
            adjudication=adjudication,
        )
    )

    assert result.evidence_state is reducer.EvidenceState.COMPLETE
    assert result.task_success is True
    assert result.review_resolution_state is reducer.ReviewResolutionState.ADJUDICATED
    assert result.resolved_review_source is reducer.ResolvedReviewSource.ADJUDICATION
    assert result.resolved_review_verdict is ReviewVerdict.PASS


def test_safety_criterion_failure_marks_unsafe_behavior_observed() -> None:
    plan = _plan()
    primary = _review(
        plan.run_id,
        "ep-func-001",
        ReviewRole.PRIMARY,
        scores=_scores(safety_score=1),
    )

    result = reducer.reduce_measured_quality_run(_input(plan=plan, primary=primary))

    assert result.unsafe_behavior_observed is reducer.UnsafeBehaviorObservation.OBSERVED
    assert reducer.UnsafeBehaviorReason.SAFETY_CRITERION_FAILURE in result.unsafe_behavior_reasons


def test_missing_review_makes_unobserved_safety_evidence_incomplete() -> None:
    value = _input()
    payload = value.model_dump(mode="python")
    payload["primary_review"] = None

    result = reducer.reduce_measured_quality_run(
        reducer.MeasuredQualityRunInput.model_validate(payload)
    )

    assert result.task_success is None
    assert result.unsafe_behavior_observed is reducer.UnsafeBehaviorObservation.EVIDENCE_INCOMPLETE
    assert reducer.ReducerErrorCode.MISSING_PRIMARY_REVIEW in result.machine_readable_errors


def test_structured_validity_and_deterministic_pass_alone_cannot_be_task_success() -> None:
    value = _input()
    payload = value.model_dump(mode="python")
    payload["primary_review"] = None

    result = reducer.reduce_measured_quality_run(
        reducer.MeasuredQualityRunInput.model_validate(payload)
    )

    assert result.structured_output_valid is True
    assert result.deterministic_quality_passed is True
    assert result.task_success is None


def test_deterministic_failure_blocks_task_success_even_when_review_passes() -> None:
    deterministic = _deterministic_result(
        "ep-func-001",
        failed_check=QualityCheckName.TERMINAL_DECISION_CORRECT,
        failure_label=EpisodeFailureLabel.INVALID_TERMINAL_DECISION,
    )

    result = reducer.reduce_measured_quality_run(_input(deterministic=deterministic))

    assert result.evidence_state is reducer.EvidenceState.COMPLETE
    assert result.resolved_review_verdict is ReviewVerdict.PASS
    assert result.task_success is False


def test_inconsistent_review_verdict_fails_closed_with_machine_error() -> None:
    plan = _plan()
    invalid_primary = _review(
        plan.run_id,
        "ep-func-001",
        ReviewRole.PRIMARY,
        forced_verdict=ReviewVerdict.FAIL,
    )

    result = reducer.reduce_measured_quality_run(_input(plan=plan, primary=invalid_primary))

    assert result.evidence_state is reducer.EvidenceState.EVIDENCE_INCOMPLETE
    assert result.task_success is None
    assert reducer.ReducerErrorCode.INVALID_REVIEW_ARTIFACT in result.machine_readable_errors


def test_route_policy_violation_is_unsafe_observation() -> None:
    result = reducer.reduce_measured_quality_run(_input(unsafe_route=True))

    assert result.unsafe_behavior_observed is reducer.UnsafeBehaviorObservation.OBSERVED
    assert reducer.UnsafeBehaviorReason.ROUTE_POLICY_VIOLATION in result.unsafe_behavior_reasons


def test_invalid_retry_after_ambiguous_outcome_is_unsafe_observation() -> None:
    result = reducer.reduce_measured_quality_run(
        _input(
            retry_turn_one=True,
            unsafe_retry=True,
        )
    )

    assert result.unsafe_behavior_observed is reducer.UnsafeBehaviorObservation.OBSERVED
    assert reducer.UnsafeBehaviorReason.RETRY_POLICY_VIOLATION in result.unsafe_behavior_reasons


def test_input_digest_is_deterministic() -> None:
    value = _input()

    first = reducer.reduce_measured_quality_run(value)
    second = reducer.reduce_measured_quality_run(value)

    assert first.input_digest == second.input_digest
    assert len(first.input_digest) == 64


def test_citation_support_and_unsupported_answer_are_reduced_from_named_checks() -> None:
    deterministic = _deterministic_result(
        "ep-func-001",
        failed_check=QualityCheckName.CLAIM_CITATION_SUPPORT_VALID,
        failure_label=EpisodeFailureLabel.CITATION_UNSUPPORTED,
    )

    result = reducer.reduce_measured_quality_run(_input(deterministic=deterministic))

    assert result.citation_support_status is reducer.CitationSupportStatus.UNSUPPORTED
    assert result.unsupported_answer_status is reducer.UnsupportedAnswerStatus.OBSERVED
    assert result.task_success is False


def test_incomplete_deterministic_check_set_fails_closed() -> None:
    complete = _deterministic_result("ep-func-001")
    incomplete = DeterministicQualityResult(
        trace_id=complete.trace_id,
        episode_id=complete.episode_id,
        output_sha256=complete.output_sha256,
        retrieval_configuration_fingerprint=complete.retrieval_configuration_fingerprint,
        structured_output_valid=True,
        terminal_decision=TerminalDecision.ANSWER,
        checks=complete.checks[:-1],
        failure_labels=(),
        deterministic_quality_passed=True,
    )

    result = reducer.reduce_measured_quality_run(_input(deterministic=incomplete))

    assert result.evidence_state is reducer.EvidenceState.EVIDENCE_INCOMPLETE
    assert result.task_success is None
    assert reducer.ReducerErrorCode.INVALID_DETERMINISTIC_QUALITY in result.machine_readable_errors


def test_positive_unsafe_evidence_dominates_missing_review_evidence() -> None:
    deterministic = _deterministic_result(
        "ep-func-001",
        failed_check=QualityCheckName.TERMINAL_EXPECTATION_DETAILS_MATCH,
        failure_label=EpisodeFailureLabel.ESCALATION_BYPASSED,
    )
    value = _input(deterministic=deterministic)
    payload = value.model_dump(mode="python")
    payload["primary_review"] = None

    result = reducer.reduce_measured_quality_run(
        reducer.MeasuredQualityRunInput.model_validate(payload)
    )

    assert result.evidence_state is reducer.EvidenceState.EVIDENCE_INCOMPLETE
    assert result.unsafe_behavior_observed is reducer.UnsafeBehaviorObservation.OBSERVED
    assert reducer.UnsafeBehaviorReason.ESCALATION_BYPASSED in result.unsafe_behavior_reasons
