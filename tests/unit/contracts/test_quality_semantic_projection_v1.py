from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_semantic_projection_v1 import (
    HumanCriterionSemanticProjectionV1,
    HumanFailureLabelSemanticProjectionV1,
    HumanSemanticProjectionV1,
    ModelCriterionSemanticQuestionV1,
    ModelFailureLabelSemanticQuestionV1,
    ModelSemanticProjectionV1,
    SemanticProjectionParityReceiptV1,
)


def _human_projection_payload() -> dict[str, Any]:
    projection = HumanSemanticProjectionV1(
        criteria=tuple(
            HumanCriterionSemanticProjectionV1(
                criterion=criterion,
                guidance=f"semantic guidance for criterion {criterion.value}",
            )
            for criterion in RubricCriterion
        ),
        failure_labels=tuple(
            HumanFailureLabelSemanticProjectionV1(
                label=label,
                guidance=f"semantic guidance for failure label {label.value}",
            )
            for label in EpisodeFailureLabel
        ),
    )
    return projection.model_dump(mode="json")


def _model_projection_payload() -> dict[str, Any]:
    projection = ModelSemanticProjectionV1(
        criterion_questions=tuple(
            ModelCriterionSemanticQuestionV1(
                question_name=f"criterion__{criterion.value}",
                criterion=criterion,
                instructions=f"semantic instructions for criterion {criterion.value}",
                criteria={
                    "1": "score one anchor",
                    "2": "score two anchor",
                    "3": "score three anchor",
                    "4": "score four anchor",
                },
            )
            for criterion in RubricCriterion
        ),
        failure_questions=tuple(
            ModelFailureLabelSemanticQuestionV1(
                question_name=f"failure__{label.value}",
                label=label,
                instructions=f"semantic instructions for failure label {label.value}",
            )
            for label in EpisodeFailureLabel
        ),
    )
    return projection.model_dump(mode="json")


def test_human_projection_requires_complete_unique_inventory() -> None:
    payload = _human_projection_payload()
    payload["criteria"][-1] = payload["criteria"][0]

    with pytest.raises(ValidationError, match="every rubric criterion exactly once"):
        HumanSemanticProjectionV1.model_validate(payload)


def test_model_projection_requires_complete_unique_inventory() -> None:
    payload = _model_projection_payload()
    payload["failure_questions"][-1] = payload["failure_questions"][0]

    with pytest.raises(ValidationError, match="every failure label exactly once"):
        ModelSemanticProjectionV1.model_validate(payload)


def test_model_criterion_question_requires_exact_score_inventory() -> None:
    with pytest.raises(ValidationError, match="score inventory"):
        ModelCriterionSemanticQuestionV1(
            question_name="criterion__task_correctness",
            criterion=RubricCriterion.TASK_CORRECTNESS,
            instructions="semantic instructions for task correctness",
            criteria={
                "1": "score one anchor",
                "2": "score two anchor",
                "3": "score three anchor",
            },
        )


def test_model_question_name_must_match_semantic_identity() -> None:
    with pytest.raises(ValidationError, match="does not match criterion"):
        ModelCriterionSemanticQuestionV1(
            question_name="criterion__clarity",
            criterion=RubricCriterion.TASK_CORRECTNESS,
            instructions="semantic instructions for task correctness",
            criteria={
                "1": "score one anchor",
                "2": "score two anchor",
                "3": "score three anchor",
                "4": "score four anchor",
            },
        )


def test_parity_receipt_cannot_claim_execution_or_threshold_activity() -> None:
    receipt = SemanticProjectionParityReceiptV1(
        human_projection_sha256="a" * 64,
        model_projection_sha256="b" * 64,
    )

    assert receipt.network_access_performed is False
    assert receipt.jev_request_performed is False
    assert receipt.deployment_threshold_selected is False
    assert receipt.deployment_threshold_validated is False
    assert receipt.final_342_mutated is False
    assert receipt.rubric_v1_mutated is False
