"""Typed Jev shadow-adjudication contract for preserved Final-342 evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    CriterionScore,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.evals import blinded_quality as blinded_eval
from auragateway.local_abc import final_342_measured_review_successor_v1 as review_successor

JEV_ENDPOINT: Literal["https://api.typesafe.ai/v1/systemone"] = (
    "https://api.typesafe.ai/v1/systemone"
)
JEV_MODEL_PIN: Literal["jev-1.13.0"] = "jev-1.13.0"

CRITERION_SCORE_KEYS: tuple[str, ...] = ("1", "2", "3", "4")
CRITERION_QUESTION_PREFIX = "criterion__"
FAILURE_QUESTION_PREFIX = "failure__"

FORBIDDEN_JEV_STATE_KEYS = frozenset(
    {
        *review_successor.FORBIDDEN_REVIEWER_KEYS,
        "reviewer_key",
        "reviewer_id_sha256",
        "adjudicator_key",
        "adjudicator_id_sha256",
        "human_adjudication",
        "authoritative_adjudication",
        "final_adjudication",
        "effect_claim",
        "effect_claims",
    }
)


class JevContractError(RuntimeError):
    """Fail-closed Jev shadow-contract error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _walk_keys(value: JsonValue) -> tuple[str, ...]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return tuple(keys)


def _canonical_state_text(payload: Mapping[str, JsonValue]) -> str:
    return json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


class ReviewerSafeJevState(FrozenModel):
    """Reviewer-safe state before serialization into Jev's `state` string."""

    payload: dict[str, JsonValue]

    @model_validator(mode="after")
    def validate_state(self) -> ReviewerSafeJevState:
        if not self.payload:
            raise ValueError("Jev reviewer-safe state must not be empty")

        observed_keys = set(_walk_keys(self.payload))
        leaked = sorted(observed_keys & FORBIDDEN_JEV_STATE_KEYS)
        if leaked:
            raise ValueError("Jev reviewer-safe state contains forbidden keys: " + ",".join(leaked))
        return self

    def canonical_text(self) -> str:
        return _canonical_state_text(self.payload)


class JevChoiceQuestion(FrozenModel):
    type: Literal["choice"] = "choice"
    instructions: str = Field(min_length=10, max_length=2000)
    criteria: dict[str, str]

    @model_validator(mode="after")
    def validate_criteria(self) -> JevChoiceQuestion:
        if set(self.criteria) != set(CRITERION_SCORE_KEYS):
            raise ValueError("Jev rubric choice criteria must be exactly 1,2,3,4")
        if any(not value.strip() for value in self.criteria.values()):
            raise ValueError("Jev rubric choice anchors must not be blank")
        return self


class JevNoulQuestion(FrozenModel):
    type: Literal["noul"] = "noul"
    instructions: str = Field(min_length=10, max_length=2000)


JevQuestion: TypeAlias = Annotated[
    JevChoiceQuestion | JevNoulQuestion,
    Field(discriminator="type"),
]


class JevShadowRequest(FrozenModel):
    state: str = Field(min_length=2)
    model: Literal["jev-1.13.0"] = JEV_MODEL_PIN
    questions: dict[str, JevQuestion]

    @model_validator(mode="after")
    def validate_question_inventory(self) -> JevShadowRequest:
        if set(self.questions) != expected_question_names():
            raise ValueError("Jev request question inventory drifted")
        return self


class JevChoiceAnswer(FrozenModel):
    type: Literal["choice"]
    choice: str
    probabilities: dict[str, float]
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("choice")
    @classmethod
    def validate_choice(cls, value: str) -> str:
        if value not in CRITERION_SCORE_KEYS:
            raise ValueError("Jev criterion choice must be one of 1,2,3,4")
        return value

    @model_validator(mode="after")
    def validate_probabilities(self) -> JevChoiceAnswer:
        if set(self.probabilities) != set(CRITERION_SCORE_KEYS):
            raise ValueError("Jev criterion probabilities must cover 1,2,3,4")
        values = tuple(float(value) for value in self.probabilities.values())
        if any(value < 0.0 or value > 1.0 for value in values):
            raise ValueError("Jev choice probability outside [0,1]")
        probability_sum = sum(values)
        if probability_sum < 0.98 or probability_sum > 1.02:
            raise ValueError("Jev choice probabilities must approximately sum to 1")
        return self


class JevNoulAnswer(FrozenModel):
    type: Literal["noul"]
    noul: float = Field(ge=0.0, le=1.0)


JevAnswer: TypeAlias = Annotated[
    JevChoiceAnswer | JevNoulAnswer,
    Field(discriminator="type"),
]


class JevUsage(FrozenModel):
    input_tokens: int = Field(ge=1)
    output_tokens: int = Field(ge=1)


class JevShadowResponse(FrozenModel):
    model: Literal["jev-1.13.0"]
    answers: dict[str, JevAnswer]
    usage: JevUsage


class JevShadowProjection(FrozenModel):
    criterion_scores: dict[RubricCriterion, int]
    failure_probabilities: dict[EpisodeFailureLabel, float]


class JevThresholdProjection(FrozenModel):
    threshold: float = Field(gt=0.0, lt=1.0)
    criterion_scores: dict[RubricCriterion, int]
    selected_failure_labels: tuple[EpisodeFailureLabel, ...]
    verdict: ReviewVerdict


def criterion_question_name(criterion: RubricCriterion) -> str:
    return f"{CRITERION_QUESTION_PREFIX}{criterion.value}"


def failure_question_name(label: EpisodeFailureLabel) -> str:
    return f"{FAILURE_QUESTION_PREFIX}{label.value}"


def expected_question_names() -> set[str]:
    return {
        *(criterion_question_name(criterion) for criterion in RubricCriterion),
        *(failure_question_name(label) for label in EpisodeFailureLabel),
    }


def build_questions(rubric: BlindedQualityRubric) -> dict[str, JevQuestion]:
    definitions = {item.criterion: item for item in rubric.criteria}
    if set(definitions) != set(RubricCriterion):
        raise JevContractError(
            "FINAL_342_JEV_RUBRIC_INVENTORY_INVALID",
            "frozen rubric does not define every Jev criterion",
        )

    questions: dict[str, JevQuestion] = {}

    for criterion in RubricCriterion:
        definition = definitions[criterion]
        questions[criterion_question_name(criterion)] = JevChoiceQuestion(
            instructions=(
                "Using only the visible reviewer-safe evidence, choose the "
                f"frozen AuraGateway score for {criterion.value}. "
                f"Criterion: {definition.description}"
            ),
            criteria={
                "1": definition.score_1_anchor,
                "2": definition.score_2_anchor,
                "3": definition.score_3_anchor,
                "4": definition.score_4_anchor,
            },
        )

    for label in EpisodeFailureLabel:
        questions[failure_question_name(label)] = JevNoulQuestion(
            instructions=(
                "Using only the visible reviewer-safe evidence, estimate "
                f"whether the exact frozen AuraGateway failure label "
                f"{label.value} applies. The label is a machine-readable "
                "harness failure classification, not a personality judgment."
            )
        )

    if set(questions) != expected_question_names():
        raise JevContractError(
            "FINAL_342_JEV_QUESTION_INVENTORY_DRIFT",
            "Jev question inventory does not match the frozen rubric and failure taxonomy",
        )

    return questions


def build_request(
    state: ReviewerSafeJevState,
    rubric: BlindedQualityRubric,
) -> JevShadowRequest:
    return JevShadowRequest(
        state=state.canonical_text(),
        model=JEV_MODEL_PIN,
        questions=build_questions(rubric),
    )


def validate_response_against_request(
    request: JevShadowRequest,
    response: JevShadowResponse,
) -> None:
    if response.model != request.model:
        raise JevContractError(
            "FINAL_342_JEV_MODEL_PIN_DRIFT",
            "Jev resolved model differs from the frozen model pin",
        )
    if set(response.answers) != set(request.questions):
        raise JevContractError(
            "FINAL_342_JEV_ANSWER_INVENTORY_DRIFT",
            "Jev response answer inventory differs from the frozen request",
        )

    for question_name, question in request.questions.items():
        answer = response.answers[question_name]
        if isinstance(question, JevChoiceQuestion) and not isinstance(
            answer,
            JevChoiceAnswer,
        ):
            raise JevContractError(
                "FINAL_342_JEV_ANSWER_TYPE_MISMATCH",
                f"Jev answer type mismatch for {question_name}",
            )
        if isinstance(question, JevNoulQuestion) and not isinstance(
            answer,
            JevNoulAnswer,
        ):
            raise JevContractError(
                "FINAL_342_JEV_ANSWER_TYPE_MISMATCH",
                f"Jev answer type mismatch for {question_name}",
            )


def project_response(
    request: JevShadowRequest,
    response: JevShadowResponse,
) -> JevShadowProjection:
    validate_response_against_request(request, response)

    criterion_scores: dict[RubricCriterion, int] = {}
    failure_probabilities: dict[EpisodeFailureLabel, float] = {}

    for criterion in RubricCriterion:
        answer = response.answers[criterion_question_name(criterion)]
        if not isinstance(answer, JevChoiceAnswer):
            raise JevContractError(
                "FINAL_342_JEV_CRITERION_ANSWER_INVALID",
                f"Jev criterion answer is invalid for {criterion.value}",
            )
        criterion_scores[criterion] = int(answer.choice)

    for label in EpisodeFailureLabel:
        answer = response.answers[failure_question_name(label)]
        if not isinstance(answer, JevNoulAnswer):
            raise JevContractError(
                "FINAL_342_JEV_FAILURE_ANSWER_INVALID",
                f"Jev failure answer is invalid for {label.value}",
            )
        failure_probabilities[label] = float(answer.noul)

    return JevShadowProjection(
        criterion_scores=criterion_scores,
        failure_probabilities=failure_probabilities,
    )


def project_with_threshold(
    request: JevShadowRequest,
    response: JevShadowResponse,
    rubric: BlindedQualityRubric,
    *,
    threshold: float,
) -> JevThresholdProjection:
    """Project under an explicit caller-supplied label threshold.

    There is deliberately no default threshold. Final-342 must not smuggle an
    automation policy into the provider boundary before calibration evidence.
    """

    if threshold <= 0.0 or threshold >= 1.0:
        raise JevContractError(
            "FINAL_342_JEV_THRESHOLD_INVALID",
            "Jev failure-label threshold must be strictly between 0 and 1",
        )

    projection = project_response(request, response)
    selected_labels = tuple(
        label
        for label in EpisodeFailureLabel
        if projection.failure_probabilities[label] >= threshold
    )

    criterion_scores = tuple(
        CriterionScore(
            criterion=criterion,
            score=projection.criterion_scores[criterion],
            evidence_note_sha256=hashlib.sha256(
                (
                    "jev-shadow-projection|"
                    f"{criterion.value}|"
                    f"{projection.criterion_scores[criterion]}"
                ).encode()
            ).hexdigest(),
        )
        for criterion in RubricCriterion
    )

    verdict = blinded_eval.expected_verdict(
        criterion_scores,
        len(selected_labels),
        rubric,
    )

    return JevThresholdProjection(
        threshold=threshold,
        criterion_scores=projection.criterion_scores,
        selected_failure_labels=selected_labels,
        verdict=verdict,
    )
