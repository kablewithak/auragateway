"""Deterministic practical EFC trace evaluation for Gate 7."""

from __future__ import annotations

from collections import defaultdict

from auragateway.contracts.feedback import (
    EFCFailureCode,
    FeedbackEventAssessment,
    FeedbackInformativenessStatus,
    FeedbackNoveltyStatus,
    FeedbackTrajectory,
    FeedbackTrajectorySummary,
    FeedbackValidityStatus,
    TaskSufficiencyStatus,
)


def _event_failure_codes(
    *,
    validity_status: FeedbackValidityStatus,
    informativeness_status: FeedbackInformativenessStatus,
    novelty_status: FeedbackNoveltyStatus,
    fingerprint_seen: bool,
    retained_in_state: bool | None,
) -> tuple[EFCFailureCode, ...]:
    failures: list[EFCFailureCode] = []
    if validity_status is FeedbackValidityStatus.INVALID:
        failures.append(EFCFailureCode.INVALID_FEEDBACK)
    elif validity_status is FeedbackValidityStatus.UNKNOWN:
        failures.append(EFCFailureCode.UNKNOWN_VALIDITY)

    if informativeness_status is FeedbackInformativenessStatus.IRRELEVANT:
        failures.append(EFCFailureCode.UNINFORMATIVE_FEEDBACK)
    elif informativeness_status is FeedbackInformativenessStatus.UNKNOWN:
        failures.append(EFCFailureCode.UNKNOWN_INFORMATIVENESS)

    if novelty_status is FeedbackNoveltyStatus.UNKNOWN:
        failures.append(EFCFailureCode.UNKNOWN_NOVELTY)
    elif (novelty_status is FeedbackNoveltyStatus.NEW and fingerprint_seen) or (
        novelty_status is FeedbackNoveltyStatus.REDUNDANT and not fingerprint_seen
    ):
        failures.append(EFCFailureCode.NOVELTY_STATUS_INCONSISTENT)
    elif novelty_status is FeedbackNoveltyStatus.REDUNDANT:
        failures.append(EFCFailureCode.REDUNDANT_FEEDBACK)

    if validity_status is FeedbackValidityStatus.VALID:
        if retained_in_state is False:
            failures.append(EFCFailureCode.UNRETAINED_VALID_FEEDBACK)
        elif retained_in_state is None:
            failures.append(EFCFailureCode.UNKNOWN_RETENTION)
    return tuple(failures)


def evaluate_feedback_trajectory(
    trajectory: FeedbackTrajectory,
) -> FeedbackTrajectorySummary:
    """Evaluate feedback validity, novelty, retention, action change, and sufficiency."""

    seen_fingerprints: set[str] = set()
    useful_retained_by_subgoal: dict[str, int] = defaultdict(int)
    assessments: list[FeedbackEventAssessment] = []

    for event in trajectory.events:
        fingerprint_seen = event.evidence_fingerprint in seen_fingerprints
        failures = _event_failure_codes(
            validity_status=event.validity_status,
            informativeness_status=event.informativeness_status,
            novelty_status=event.novelty_status,
            fingerprint_seen=fingerprint_seen,
            retained_in_state=event.retained_in_state,
        )
        valid = event.validity_status is FeedbackValidityStatus.VALID
        informative = event.informativeness_status is FeedbackInformativenessStatus.INFORMATIVE
        non_redundant = event.novelty_status is FeedbackNoveltyStatus.NEW and not fingerprint_seen
        retained = event.retained_in_state is True
        next_action_changed = event.next_action_changed is True

        assessment = FeedbackEventAssessment(
            event_id=event.event_id,
            valid=valid,
            informative=informative,
            non_redundant=non_redundant,
            retained=retained,
            next_action_changed=next_action_changed,
            failure_codes=failures,
        )
        assessments.append(assessment)
        if valid and informative and non_redundant and retained:
            useful_retained_by_subgoal[event.subgoal_id] += 1
        seen_fingerprints.add(event.evidence_fingerprint)

    assessment_tuple = tuple(assessments)
    valid_count = sum(item.valid for item in assessment_tuple)
    redundant_count = sum(
        EFCFailureCode.REDUNDANT_FEEDBACK in item.failure_codes
        or EFCFailureCode.NOVELTY_STATUS_INCONSISTENT in item.failure_codes
        for item in assessment_tuple
    )
    retained_valid_count = sum(item.valid and item.retained for item in assessment_tuple)
    unretained_valid_count = valid_count - retained_valid_count
    actionable = tuple(
        item for item in assessment_tuple if item.valid and item.informative and item.retained
    )
    action_change_count = sum(item.next_action_changed for item in actionable)

    missing_subgoals = tuple(
        subgoal_id
        for subgoal_id in trajectory.required_subgoal_ids
        if useful_retained_by_subgoal[subgoal_id] == 0
    )
    explicitly_sufficient = any(
        event.task_sufficiency_status is TaskSufficiencyStatus.SUFFICIENT
        for event in trajectory.events
    )
    task_sufficient = all(
        (
            trajectory.task_completed,
            trajectory.expected_terminal_decision_reached,
            set(trajectory.completed_subgoal_ids) == set(trajectory.required_subgoal_ids),
            not missing_subgoals,
            explicitly_sufficient,
        )
    )

    failure_codes = list(
        dict.fromkeys(code for assessment in assessment_tuple for code in assessment.failure_codes)
    )
    if missing_subgoals:
        failure_codes.append(EFCFailureCode.MISSING_REQUIRED_SUBGOAL_EVIDENCE)
    if not task_sufficient:
        failure_codes.append(EFCFailureCode.TASK_INSUFFICIENT)

    event_count = len(assessment_tuple)
    valid_denominator = valid_count or 1
    actionable_denominator = len(actionable) or 1
    return FeedbackTrajectorySummary(
        trajectory_id=trajectory.trajectory_id,
        trace_id=trajectory.trace_id,
        event_count=event_count,
        valid_event_count=valid_count,
        redundant_event_count=redundant_count,
        retained_valid_event_count=retained_valid_count,
        unretained_valid_event_count=unretained_valid_count,
        feedback_linked_action_change_count=action_change_count,
        valid_feedback_event_rate=valid_count / event_count,
        redundant_feedback_event_rate=redundant_count / event_count,
        retained_feedback_event_rate=retained_valid_count / valid_denominator,
        unretained_valid_feedback_event_rate=unretained_valid_count / valid_denominator,
        feedback_linked_action_change_rate=action_change_count / actionable_denominator,
        task_sufficiency_passed=task_sufficient,
        event_assessments=assessment_tuple,
        failure_codes=tuple(dict.fromkeys(failure_codes)),
        efc_evidence_passed=not failure_codes and task_sufficient,
    )
