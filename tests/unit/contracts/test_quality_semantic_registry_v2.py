from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_semantic_registry_v2 import (
    CriterionSemanticDefinitionV2,
    FailureLabelSemanticDefinitionV2,
    QualitySemanticRegistryV2,
    SemanticSourceReferenceV2,
)


def _source() -> SemanticSourceReferenceV2:
    return SemanticSourceReferenceV2(
        source_kind="normative",
        repository_path="docs/adr/2026-09-18-quality-semantic-registry-v2.md",
        locator="Quality semantic registry v2 normative decision",
    )


def _criterion(
    criterion: RubricCriterion,
) -> CriterionSemanticDefinitionV2:
    return CriterionSemanticDefinitionV2(
        criterion=criterion,
        description=f"Semantic description for the {criterion.value} quality criterion.",
        applicability_rule=(
            f"Apply {criterion.value} whenever the evaluated response contains "
            "behaviour material to this criterion."
        ),
        non_substantive_response_rule=(
            "A non-substantive response must still be evaluated when its terminal "
            "action or omission materially exercises this criterion."
        ),
        score_1_anchor="Material failure under the criterion contract.",
        score_2_anchor="Material weakness remains under the criterion contract.",
        score_3_anchor="Criterion is satisfied with only minor weaknesses.",
        score_4_anchor="Criterion is fully satisfied without material weakness.",
        boundary_notes=("Boundary decisions must use the visible evidence only.",),
        semantic_sources=(_source(),),
    )


def _failure(
    label: EpisodeFailureLabel,
) -> FailureLabelSemanticDefinitionV2:
    related = (
        (EpisodeFailureLabel.UNSUPPORTED_CLAIM,)
        if label is not EpisodeFailureLabel.UNSUPPORTED_CLAIM
        else (EpisodeFailureLabel.TASK_INSUFFICIENT,)
    )
    return FailureLabelSemanticDefinitionV2(
        label=label,
        operational_definition=(
            f"Operational definition for the exact {label.value} failure label."
        ),
        applies_when=(f"Apply {label.value} when its explicit operational condition is met.",),
        does_not_apply_when=(
            f"Do not apply {label.value} when only a related near-miss is present.",
        ),
        related_labels=related,
        semantic_sources=(_source(),),
        positive_example=(f"A concrete positive example satisfying the {label.value} definition."),
        near_miss_example=(f"A concrete near-miss that must not receive the {label.value} label."),
    )


def _registry_payload() -> dict[str, Any]:
    registry = QualitySemanticRegistryV2(
        criteria=tuple(_criterion(item) for item in RubricCriterion),
        failure_labels=tuple(_failure(item) for item in EpisodeFailureLabel),
    )
    return registry.model_dump(mode="json")


def test_complete_registry_validates_and_hash_is_stable() -> None:
    first = QualitySemanticRegistryV2.model_validate(_registry_payload())
    second = QualitySemanticRegistryV2.model_validate(_registry_payload())

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.sha256() == second.sha256()
    assert len(first.sha256()) == 64


def test_missing_criterion_is_rejected() -> None:
    payload = _registry_payload()
    payload["criteria"] = payload["criteria"][:-1]

    with pytest.raises(ValidationError):
        QualitySemanticRegistryV2.model_validate(payload)


def test_duplicate_criterion_is_rejected() -> None:
    payload = _registry_payload()
    payload["criteria"][-1] = payload["criteria"][0]

    with pytest.raises(ValidationError, match="criteria must be unique"):
        QualitySemanticRegistryV2.model_validate(payload)


def test_missing_failure_label_is_rejected() -> None:
    payload = _registry_payload()
    payload["failure_labels"] = payload["failure_labels"][:-1]

    with pytest.raises(ValidationError):
        QualitySemanticRegistryV2.model_validate(payload)


def test_duplicate_failure_label_is_rejected() -> None:
    payload = _registry_payload()
    payload["failure_labels"][-1] = payload["failure_labels"][0]

    with pytest.raises(ValidationError, match="failure labels must be unique"):
        QualitySemanticRegistryV2.model_validate(payload)


def test_self_referential_related_label_is_rejected() -> None:
    payload = _registry_payload()
    definition = payload["failure_labels"][0]
    definition["related_labels"] = [definition["label"]]

    with pytest.raises(ValidationError, match="must not relate to itself"):
        QualitySemanticRegistryV2.model_validate(payload)


def test_unknown_semantic_source_kind_is_rejected() -> None:
    payload = _registry_payload()
    payload["criteria"][0]["semantic_sources"][0]["source_kind"] = "unknown"

    with pytest.raises(ValidationError):
        QualitySemanticRegistryV2.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    [
        "applies_when",
        "does_not_apply_when",
    ],
)
def test_empty_failure_label_rule_inventory_is_rejected(
    field_name: str,
) -> None:
    payload = _registry_payload()
    payload["failure_labels"][0][field_name] = []

    with pytest.raises(ValidationError):
        QualitySemanticRegistryV2.model_validate(payload)


def test_unknown_semantic_source_shape_is_rejected() -> None:
    payload = _registry_payload()
    payload["criteria"][0]["semantic_sources"][0]["unexpected"] = "drift"

    with pytest.raises(ValidationError):
        QualitySemanticRegistryV2.model_validate(payload)


def test_criterion_inventory_drift_is_rejected() -> None:
    payload = _registry_payload()
    payload["criteria"][0]["criterion"] = payload["criteria"][1]["criterion"]

    with pytest.raises(ValidationError):
        QualitySemanticRegistryV2.model_validate(payload)


def test_failure_label_inventory_drift_is_rejected() -> None:
    payload = _registry_payload()
    payload["failure_labels"][0]["label"] = payload["failure_labels"][1]["label"]

    with pytest.raises(ValidationError):
        QualitySemanticRegistryV2.model_validate(payload)


def test_repository_source_path_must_be_safe_and_relative() -> None:
    with pytest.raises(ValidationError):
        SemanticSourceReferenceV2(
            source_kind="normative",
            repository_path="../outside.md",
            locator="Unsafe path example",
        )
