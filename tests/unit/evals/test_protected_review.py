from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    ReviewAssignmentManifest,
)
from auragateway.contracts.episodes import EpisodeEvaluationSplit
from auragateway.contracts.protected_review import ProtectedReviewSubmissionSet
from auragateway.evals.protected_review import (
    ProtectedReviewExecutionError,
    evaluate_protected_review_execution,
)


def _load(path: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(Path(path).read_text(encoding="utf-8")),
    )


def _splits() -> dict[str, EpisodeEvaluationSplit]:
    return {
        f"ep-func-{index:03d}": (
            EpisodeEvaluationSplit.DEVELOPMENT if index <= 12 else EpisodeEvaluationSplit.HELD_OUT
        )
        for index in range(1, 19)
    }


def _inputs() -> tuple[
    ReviewAssignmentManifest,
    BlindedQualityRubric,
    dict[str, Any],
]:
    return (
        ReviewAssignmentManifest.model_validate(
            _load("data/evals/quality/blinded-v1/assignment_manifest.json")
        ),
        BlindedQualityRubric.model_validate(_load("data/evals/quality/blinded-v1/rubric.json")),
        _load("data/evals/quality/execution-v1/submissions.json"),
    )


def test_complete_execution_builds_agreement_and_held_out_aggregate() -> None:
    assignments, rubric, payload = _inputs()
    report = evaluate_protected_review_execution(
        assignments,
        rubric,
        _splits(),
        ProtectedReviewSubmissionSet.model_validate(payload),
    )

    assert report.assignment_count == 23
    assert report.review_count == 23
    assert report.primary_review_count == 18
    assert report.secondary_review_count == 5
    assert report.adjudication_count == 2
    assert report.agreement.material_disagreement_count == 2
    assert report.held_out.held_out_episode_count == 6
    assert report.held_out.pass_count == 5
    assert report.held_out.fail_count == 1
    assert report.execution_controls_passed is True
    assert report.human_review_completed is False


def test_missing_review_is_blocked() -> None:
    assignments, rubric, payload = _inputs()
    payload["reviews"] = payload["reviews"][:-1]

    with pytest.raises(ProtectedReviewExecutionError) as exc_info:
        evaluate_protected_review_execution(
            assignments,
            rubric,
            _splits(),
            ProtectedReviewSubmissionSet.model_validate(payload),
        )

    assert exc_info.value.error_code == "REVIEW_COVERAGE_INCOMPLETE"


def test_unassigned_review_is_blocked() -> None:
    assignments, rubric, payload = _inputs()
    extra_review = deepcopy(payload["reviews"][0])
    extra_review["review_id"] = "review-aaaaaaaaaaaaaaaaaaaaaaaa"
    payload["reviews"].append(extra_review)

    with pytest.raises(ProtectedReviewExecutionError) as exc_info:
        evaluate_protected_review_execution(
            assignments,
            rubric,
            _splits(),
            ProtectedReviewSubmissionSet.model_validate(payload),
        )

    assert exc_info.value.error_code == "UNASSIGNED_REVIEW_SUBMISSION"


def test_missing_adjudication_is_blocked() -> None:
    assignments, rubric, payload = _inputs()
    payload["adjudications"] = payload["adjudications"][1:]

    with pytest.raises(ProtectedReviewExecutionError) as exc_info:
        evaluate_protected_review_execution(
            assignments,
            rubric,
            _splits(),
            ProtectedReviewSubmissionSet.model_validate(payload),
        )

    assert exc_info.value.error_code == "MATERIAL_DISAGREEMENT_UNADJUDICATED"


def test_review_input_order_does_not_change_report() -> None:
    assignments, rubric, payload = _inputs()
    forward = ProtectedReviewSubmissionSet.model_validate(payload)
    reversed_payload = deepcopy(payload)
    reversed_payload["reviews"] = list(reversed(reversed_payload["reviews"]))
    reversed_payload["adjudications"] = list(reversed(reversed_payload["adjudications"]))
    reverse = ProtectedReviewSubmissionSet.model_validate(reversed_payload)

    assert evaluate_protected_review_execution(assignments, rubric, _splits(), forward) == (
        evaluate_protected_review_execution(assignments, rubric, _splits(), reverse)
    )
