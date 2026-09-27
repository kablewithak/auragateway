from __future__ import annotations

from collections import defaultdict

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.j7l_human_first_development_v2 import (
    J7LHumanFirstDevelopmentCaseSetV2,
    J7LHumanFirstDevelopmentCaseV2,
)
from auragateway.contracts.j7l_human_first_review_v2 import (
    CriterionSubmissionV2,
    J7LHumanAssessmentV2,
    J7LHumanFirstReviewPolicyV2,
    J7LHumanReviewSubmissionV2,
    J7LHumanReviewWorkItemV2,
)
from auragateway.contracts.quality_development_evaluation_v1 import J7LCaseFamily
from auragateway.local_abc import j7l_human_first_review_queue_v2 as subject


def _near_miss_map() -> dict[int, tuple[EpisodeFailureLabel, ...]]:
    labels = tuple(EpisodeFailureLabel)
    indices = tuple(range(36, 48))
    assigned: dict[int, list[EpisodeFailureLabel]] = defaultdict(list)

    for _ in range(2):
        for label_index, label in enumerate(labels):
            start = label_index % len(indices)
            for offset in range(len(indices)):
                case_index = indices[(start + offset) % len(indices)]
                if label in assigned[case_index]:
                    continue
                assigned[case_index].append(label)
                break
            else:
                raise AssertionError("unable to place near-miss label target")

    return {case_index: tuple(case_labels) for case_index, case_labels in assigned.items()}


def _positive_labels(case_index: int) -> tuple[EpisodeFailureLabel, ...]:
    labels = tuple(EpisodeFailureLabel)
    first = labels[(case_index * 2) % len(labels)]
    second = labels[(case_index * 2 + 1) % len(labels)]
    return (first, second)


def _case_set() -> J7LHumanFirstDevelopmentCaseSetV2:
    criteria = tuple(RubricCriterion)
    near_miss = _near_miss_map()
    cases: list[J7LHumanFirstDevelopmentCaseV2] = []

    for case_index in range(48):
        family = tuple(J7LCaseFamily)[case_index // 12]
        labels: tuple[EpisodeFailureLabel, ...] = ()
        if 12 <= case_index < 36:
            labels = _positive_labels(case_index - 12)

        scores = {
            criterion: 2 + ((case_index + criterion_index) % 3)
            for criterion_index, criterion in enumerate(criteria)
        }
        if labels:
            scores[RubricCriterion.TASK_CORRECTNESS] = 1
        if not labels:
            while sum(scores.values()) < 21:
                for criterion in criteria:
                    if scores[criterion] < 4:
                        scores[criterion] += 1
                        break

        cases.append(
            J7LHumanFirstDevelopmentCaseV2(
                case_id=f"j7l-v2-dev-{case_index + 1:03d}",
                case_index=case_index,
                family=family,
                reviewer_safe_state={
                    "user_request": f"request {case_index}",
                    "candidate_response": f"response {case_index}",
                },
                intended_criterion_scores=scores,
                intended_failure_labels=labels,
                near_miss_label_targets=near_miss.get(case_index, ()),
                intended_verdict=(ReviewVerdict.FAIL if labels else ReviewVerdict.PASS),
                terminal_action_evidence_material=(
                    family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE and case_index < 32
                ),
                authoring_notes=("Synthetic authoring note used only for review-queue tests."),
            )
        )

    return J7LHumanFirstDevelopmentCaseSetV2(cases=tuple(cases))


def _assessments(
    case_set: J7LHumanFirstDevelopmentCaseSetV2,
) -> tuple[J7LHumanAssessmentV2, ...]:
    assessments: list[J7LHumanAssessmentV2] = []

    for case in case_set.cases:
        assignment_id = f"review-{case.case_index:024x}"
        labels = case.intended_failure_labels
        scores = case.intended_criterion_scores

        assessments.append(
            J7LHumanAssessmentV2(
                case_id=case.case_id,
                assignment_id=assignment_id,
                reviewer_id_sha256="a" * 64,
                work_item_sha256="b" * 64,
                reviewer_safe_state_sha256="c" * 64,
                criterion_scores=scores,
                failure_labels=labels,
                evidence_references=("visible_case",),
                rationale=("Independent human rationale preserved for deterministic tests."),
                verdict=(ReviewVerdict.FAIL if labels else ReviewVerdict.PASS),
            )
        )

    return tuple(assessments)


def test_policy_is_single_human_development_only() -> None:
    policy = J7LHumanFirstReviewPolicyV2()

    assert policy.case_count == 48
    assert policy.single_human_development_reference is True
    assert policy.sequential_submission_required is True
    assert policy.case_id_hidden_from_human_work_item is True
    assert policy.family_hidden_from_human_work_item is True
    assert policy.provider_requests_authorized is False
    assert policy.jev_requests_authorized is False
    assert policy.j7m_execution_authorized is False


def test_queue_order_is_deterministic_and_complete() -> None:
    assignments = tuple(f"review-{index:024x}" for index in range(48))

    first = subject._queue_order(assignments)
    second = subject._queue_order(assignments)

    assert first == second
    assert set(first) == set(assignments)
    assert first != assignments


def test_work_item_schema_rejects_case_id() -> None:
    payload = {
        "queue_index": 0,
        "assignment_id": "review-" + "a" * 24,
        "review_item_id": "b" * 64,
        "reviewer_safe_state_sha256": "c" * 64,
        "reviewer_safe_state": {"visible": "state"},
        "semantic_projection": {
            "schema_version": "1.0.0",
        },
        "reviewer_instruction": "x" * 120,
        "case_id": "j7l-v2-dev-001",
    }

    with pytest.raises(ValidationError):
        J7LHumanReviewWorkItemV2.model_validate(payload)


def test_submission_requires_every_criterion_exactly_once() -> None:
    criteria = tuple(RubricCriterion)
    submission = J7LHumanReviewSubmissionV2(
        assignment_id="review-" + "a" * 24,
        criterion_scores=tuple(
            CriterionSubmissionV2(criterion=criterion, score=3) for criterion in criteria
        ),
        evidence_references=("visible_case",),
        rationale="Independent human rationale for the visible evidence.",
    )

    assert len(submission.criterion_scores) == 7

    payload = submission.model_dump(mode="json")
    payload["criterion_scores"][0]["criterion"] = payload["criterion_scores"][1]["criterion"]

    with pytest.raises(ValidationError, match="every rubric criterion"):
        J7LHumanReviewSubmissionV2.model_validate(payload)


def test_assessment_rejects_inconsistent_verdict() -> None:
    scores = {criterion: 4 for criterion in RubricCriterion}
    with pytest.raises(ValidationError, match="deterministic derivation"):
        J7LHumanAssessmentV2(
            case_id="j7l-v2-dev-001",
            assignment_id="review-" + "a" * 24,
            reviewer_id_sha256="b" * 64,
            work_item_sha256="c" * 64,
            reviewer_safe_state_sha256="d" * 64,
            criterion_scores=scores,
            evidence_references=("visible_case",),
            rationale="Independent human rationale for the visible evidence.",
            verdict=ReviewVerdict.FAIL,
        )


def test_human_reference_coverage_passes_without_treating_targets_as_truth() -> None:
    case_set = _case_set()
    assessments = _assessments(case_set)

    report = subject.build_coverage_report(case_set, assessments)

    assert report.status == "J7L_V2_HUMAN_REFERENCE_COVERAGE_PASS"
    assert report.pass_count >= 16
    assert report.fail_count >= 16
    assert report.minimum_positive_support_observed >= 2
    assert report.minimum_near_miss_negative_support_observed >= 2
    assert report.minimum_distinct_scores_observed >= 3
    assert report.minimum_low_scores_observed >= 4
    assert report.minimum_high_scores_observed >= 4
    assert report.terminal_material_evidence_case_count >= 8
    assert report.authoring_targets_treated_as_human_truth is False


def test_human_reference_coverage_fails_when_label_support_collapses() -> None:
    case_set = _case_set()
    assessments = _assessments(case_set)

    rewritten: list[J7LHumanAssessmentV2] = []
    for assessment in assessments:
        scores = {criterion: 4 for criterion in RubricCriterion}
        rewritten.append(
            J7LHumanAssessmentV2(
                case_id=assessment.case_id,
                assignment_id=assessment.assignment_id,
                reviewer_id_sha256=assessment.reviewer_id_sha256,
                work_item_sha256=assessment.work_item_sha256,
                reviewer_safe_state_sha256=assessment.reviewer_safe_state_sha256,
                criterion_scores=scores,
                failure_labels=(),
                evidence_references=assessment.evidence_references,
                rationale=assessment.rationale,
                verdict=ReviewVerdict.PASS,
            )
        )

    report = subject.build_coverage_report(case_set, tuple(rewritten))

    assert report.status == "J7L_V2_HUMAN_REFERENCE_COVERAGE_FAIL"
    assert report.positive_label_coverage_pass is False
    assert report.next_gate == "STOP_VERSIONED_SUCCESSOR_REQUIRED"
