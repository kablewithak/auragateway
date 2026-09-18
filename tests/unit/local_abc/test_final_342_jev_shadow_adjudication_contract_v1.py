from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _rubric(repo_root: Path) -> BlindedQualityRubric:
    path = repo_root / "data/evals/quality/blinded-v1/rubric.json"
    return BlindedQualityRubric.model_validate_json(path.read_text(encoding="utf-8"))


def _state() -> jev.ReviewerSafeJevState:
    return jev.ReviewerSafeJevState(
        payload={
            "review_item": {
                "episode_id": "ep-func-001",
                "visible_evidence": ["synthetic-visible-evidence"],
            },
            "disagreement_reasons": ["failure_label_mismatch"],
        }
    )


def _valid_response(
    *,
    choice: str = "3",
    failure_probability: float = 0.1,
) -> jev.JevShadowResponse:
    answers: dict[str, object] = {}

    for criterion in RubricCriterion:
        answers[jev.criterion_question_name(criterion)] = {
            "type": "choice",
            "choice": choice,
            "probabilities": {
                "1": 0.05,
                "2": 0.15,
                "3": 0.70,
                "4": 0.10,
            },
            "confidence": 0.8,
        }

    for label in EpisodeFailureLabel:
        answers[jev.failure_question_name(label)] = {
            "type": "noul",
            "noul": failure_probability,
        }

    return jev.JevShadowResponse.model_validate(
        {
            "model": "jev-1.13.0",
            "answers": answers,
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }
    )


def test_build_request_has_exact_frozen_inventory(repo_root: Path) -> None:
    rubric = _rubric(repo_root)
    request = jev.build_request(_state(), rubric)

    assert request.model == "jev-1.13.0"
    assert len(request.questions) == len(RubricCriterion) + len(EpisodeFailureLabel)
    assert set(request.questions) == jev.expected_question_names()

    decoded_state = json.loads(request.state)
    assert decoded_state["review_item"]["episode_id"] == "ep-func-001"

    for criterion in RubricCriterion:
        question = request.questions[jev.criterion_question_name(criterion)]
        assert isinstance(question, jev.JevChoiceQuestion)
        assert set(question.criteria) == {"1", "2", "3", "4"}

    for label in EpisodeFailureLabel:
        question = request.questions[jev.failure_question_name(label)]
        assert isinstance(question, jev.JevNoulQuestion)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "condition_id",
        "route",
        "latency",
        "cost",
        "expected_answer",
        "reviewer_key",
        "human_adjudication",
    ],
)
def test_reviewer_safe_state_rejects_forbidden_keys(forbidden_key: str) -> None:
    with pytest.raises(ValidationError):
        jev.ReviewerSafeJevState(
            payload={
                "safe": {
                    forbidden_key: "must-not-cross-provider-boundary",
                }
            }
        )


def test_response_requires_exact_model_pin_and_answer_inventory(
    repo_root: Path,
) -> None:
    rubric = _rubric(repo_root)
    request = jev.build_request(_state(), rubric)
    response = _valid_response()

    jev.validate_response_against_request(request, response)

    drifted_payload = response.model_dump(mode="json")
    drifted_payload["model"] = "jev-1.14.0"
    with pytest.raises(ValidationError):
        jev.JevShadowResponse.model_validate(drifted_payload)

    missing_payload = response.model_dump(mode="json")
    missing_payload["answers"].pop(next(iter(missing_payload["answers"])))
    missing = jev.JevShadowResponse.model_validate(missing_payload)
    with pytest.raises(jev.JevContractError, match="answer inventory"):
        jev.validate_response_against_request(request, missing)


def test_choice_probability_contract_is_bounded() -> None:
    with pytest.raises(ValidationError):
        jev.JevChoiceAnswer.model_validate(
            {
                "type": "choice",
                "choice": "3",
                "probabilities": {
                    "1": 0.10,
                    "2": 0.10,
                    "3": 0.10,
                    "4": 0.10,
                },
                "confidence": 0.8,
            }
        )


def test_project_response_preserves_scores_and_raw_failure_probabilities(
    repo_root: Path,
) -> None:
    rubric = _rubric(repo_root)
    request = jev.build_request(_state(), rubric)
    response = _valid_response(
        choice="3",
        failure_probability=0.21,
    )

    projection = jev.project_response(request, response)

    assert set(projection.criterion_scores) == set(RubricCriterion)
    assert set(projection.failure_probabilities) == set(EpisodeFailureLabel)
    assert set(projection.criterion_scores.values()) == {3}
    assert set(projection.failure_probabilities.values()) == {0.21}


def test_threshold_projection_has_no_implicit_default(repo_root: Path) -> None:
    rubric = _rubric(repo_root)
    request = jev.build_request(_state(), rubric)
    response = _valid_response(
        choice="3",
        failure_probability=0.49,
    )

    projection = jev.project_with_threshold(
        request,
        response,
        rubric,
        threshold=0.5,
    )

    assert projection.selected_failure_labels == ()
    assert projection.verdict is ReviewVerdict.PASS

    with pytest.raises(jev.JevContractError, match="strictly between"):
        jev.project_with_threshold(
            request,
            response,
            rubric,
            threshold=1.0,
        )


def test_any_selected_failure_label_forces_frozen_fail_verdict(
    repo_root: Path,
) -> None:
    rubric = _rubric(repo_root)
    request = jev.build_request(_state(), rubric)
    response = _valid_response(
        choice="4",
        failure_probability=0.91,
    )

    projection = jev.project_with_threshold(
        request,
        response,
        rubric,
        threshold=0.9,
    )

    assert len(projection.selected_failure_labels) == len(EpisodeFailureLabel)
    assert projection.verdict is ReviewVerdict.FAIL
