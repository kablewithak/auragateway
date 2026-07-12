from __future__ import annotations

import json
from pathlib import Path

from auragateway.contracts.feedback import FeedbackFixtureSet, FeedbackTrajectory
from auragateway.evals.feedback import evaluate_feedback_trajectory

FIXTURE_PATH = Path("data/evals/feedback/efc-v1/fixtures.json")


def _fixtures() -> FeedbackFixtureSet:
    return FeedbackFixtureSet.model_validate_json(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_duplicate_evidence_cannot_improve_trajectory() -> None:
    source_case = next(
        case for case in _fixtures().cases if case.case_id == "efc-pass-retained-no-action-change"
    )
    original = source_case.trajectory
    first = original.events[0]
    duplicate_payload = first.model_dump(mode="json")
    duplicate_payload.update(
        {
            "event_id": "efc-event-metamorphic-duplicate",
            "turn_index": first.turn_index + 1,
            "novelty_status": "redundant",
        }
    )
    trajectory_payload = original.model_dump(mode="json")
    trajectory_payload["events"].append(duplicate_payload)
    duplicated = FeedbackTrajectory.model_validate(trajectory_payload)

    baseline = evaluate_feedback_trajectory(original)
    changed = evaluate_feedback_trajectory(duplicated)
    assert baseline.efc_evidence_passed is True
    assert changed.efc_evidence_passed is False
    assert changed.redundant_feedback_event_rate > baseline.redundant_feedback_event_rate


def test_distinct_event_order_with_same_turn_is_metric_invariant() -> None:
    source_case = next(
        case for case in _fixtures().cases if case.case_id == "efc-pass-retained-action-change"
    )
    payload = source_case.trajectory.model_dump(mode="json")
    for event in payload["events"]:
        event["turn_index"] = 1
    forward = FeedbackTrajectory.model_validate(payload)
    payload["events"] = list(reversed(payload["events"]))
    reversed_trajectory = FeedbackTrajectory.model_validate(payload)

    forward_summary = evaluate_feedback_trajectory(forward)
    reversed_summary = evaluate_feedback_trajectory(reversed_trajectory)
    assert forward_summary.valid_feedback_event_rate == reversed_summary.valid_feedback_event_rate
    assert (
        forward_summary.retained_feedback_event_rate
        == reversed_summary.retained_feedback_event_rate
    )
    assert forward_summary.task_sufficiency_passed == reversed_summary.task_sufficiency_passed


def test_manifest_report_never_contains_universal_score_value() -> None:
    report = json.loads(Path("data/evals/feedback/efc-v1/report.json").read_text(encoding="utf-8"))
    assert report["universal_efc_score_reported"] is False
    for result in report["results"]:
        assert result["summary"]["universal_efc_score"] is None
