from __future__ import annotations

import json
from pathlib import Path

from auragateway.contracts.feedback import (
    EFCFailureCode,
    FeedbackFixtureCase,
    FeedbackFixtureSet,
)
from auragateway.evals.feedback import evaluate_feedback_trajectory

FIXTURE_PATH = Path("data/evals/feedback/efc-v1/fixtures.json")


def _fixtures() -> FeedbackFixtureSet:
    return FeedbackFixtureSet.model_validate_json(FIXTURE_PATH.read_text(encoding="utf-8"))


def _case(case_id: str) -> FeedbackFixtureCase:
    return next(case for case in _fixtures().cases if case.case_id == case_id)


def test_passing_retained_feedback_has_no_composite_score() -> None:
    summary = evaluate_feedback_trajectory(_case("efc-pass-retained-action-change").trajectory)
    assert summary.efc_evidence_passed is True
    assert summary.task_sufficiency_passed is True
    assert summary.universal_efc_score is None
    assert summary.feedback_linked_action_change_count == 1


def test_redundant_feedback_is_not_rewarded() -> None:
    summary = evaluate_feedback_trajectory(_case("efc-redundant-feedback").trajectory)
    assert summary.efc_evidence_passed is False
    assert summary.task_sufficiency_passed is True
    assert summary.redundant_event_count == 1
    assert summary.failure_codes == (EFCFailureCode.REDUNDANT_FEEDBACK,)


def test_unretained_valid_feedback_fails_sufficiency() -> None:
    summary = evaluate_feedback_trajectory(_case("efc-unretained-valid").trajectory)
    assert summary.unretained_valid_event_count == 1
    assert summary.task_sufficiency_passed is False
    assert summary.failure_codes == (
        EFCFailureCode.UNRETAINED_VALID_FEEDBACK,
        EFCFailureCode.MISSING_REQUIRED_SUBGOAL_EVIDENCE,
        EFCFailureCode.TASK_INSUFFICIENT,
    )


def test_all_fixture_expectations_match() -> None:
    for case in _fixtures().cases:
        summary = evaluate_feedback_trajectory(case.trajectory)
        assert summary.efc_evidence_passed is case.expected_pass
        assert summary.failure_codes == case.expected_failure_codes


def test_summary_contains_no_raw_feedback_content() -> None:
    summary = evaluate_feedback_trajectory(_case("efc-invalid-feedback").trajectory)
    serialized = json.dumps(summary.model_dump(mode="json"), sort_keys=True)
    prohibited = ("raw_feedback", "user_message", "candidate_output", "document_text")
    assert all(marker not in serialized for marker in prohibited)
