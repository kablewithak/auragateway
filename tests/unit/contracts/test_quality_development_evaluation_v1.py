from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v1 import (
    J7LCaseFamily,
    J7LDevelopmentCaseSetV1,
    J7LDevelopmentCaseV1,
    J7LDevelopmentConstitutionV1,
)


def _case(index: int, family: J7LCaseFamily) -> J7LDevelopmentCaseV1:
    near_miss_targets = (
        (EpisodeFailureLabel.UNSUPPORTED_CLAIM,)
        if family is J7LCaseFamily.ONTOLOGY_NEAR_MISS
        else ()
    )
    terminal_material = family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE and index < 32
    return J7LDevelopmentCaseV1(
        case_id=f"j7l-dev-{index + 1:03d}",
        case_index=index,
        family=family,
        reviewer_safe_state={
            "visible_case": {
                "prompt": f"synthetic development case {index}",
                "response": "synthetic candidate response",
            }
        },
        near_miss_label_targets=near_miss_targets,
        terminal_action_evidence_material=terminal_material,
    )


def _case_set() -> J7LDevelopmentCaseSetV1:
    cases: list[J7LDevelopmentCaseV1] = []
    families = tuple(J7LCaseFamily)
    for family_index, family in enumerate(families):
        for offset in range(12):
            cases.append(_case(family_index * 12 + offset, family))
    return J7LDevelopmentCaseSetV1(cases=tuple(cases))


def test_constitution_is_exact_and_non_authorizing() -> None:
    constitution = J7LDevelopmentConstitutionV1()

    assert constitution.development_policy.case_count == 48
    assert constitution.development_policy.primary_review_count == 48
    assert constitution.development_policy.secondary_review_count == 24
    assert constitution.development_policy.planned_provider_request_count == 96
    assert constitution.development_policy.automatic_retry_permitted is False
    assert constitution.development_policy.deployment_claim_permitted is False
    assert constitution.next_gate_on_pass == "J7M_HELD_OUT_QUALIFICATION_V1"


def test_case_set_requires_exact_family_balance() -> None:
    case_set = _case_set()
    assert len(case_set.cases) == 48

    payload = case_set.model_dump(mode="json")
    payload["cases"][12]["family"] = J7LCaseFamily.ORDINARY_CLEAN.value

    with pytest.raises(ValidationError, match="exactly 12 per family"):
        J7LDevelopmentCaseSetV1.model_validate(payload)


def test_case_id_must_match_case_index() -> None:
    payload: dict[str, Any] = _case(
        0,
        J7LCaseFamily.ORDINARY_CLEAN,
    ).model_dump(mode="json")
    payload["case_id"] = "j7l-dev-048"

    with pytest.raises(ValidationError, match="match case_index"):
        J7LDevelopmentCaseV1.model_validate(payload)


def test_reviewer_safe_state_rejects_authoring_metadata_leak() -> None:
    payload = _case(
        0,
        J7LCaseFamily.ORDINARY_CLEAN,
    ).model_dump(mode="json")
    payload["reviewer_safe_state"]["case_family"] = "hidden-authoring-metadata"

    with pytest.raises(ValidationError, match="forbidden keys"):
        J7LDevelopmentCaseV1.model_validate(payload)


def test_ontology_near_miss_case_requires_target() -> None:
    payload = _case(
        36,
        J7LCaseFamily.ONTOLOGY_NEAR_MISS,
    ).model_dump(mode="json")
    payload["near_miss_label_targets"] = []

    with pytest.raises(ValidationError, match="require near-miss label targets"):
        J7LDevelopmentCaseV1.model_validate(payload)


def test_positive_and_near_miss_targets_must_be_disjoint() -> None:
    payload = _case(
        36,
        J7LCaseFamily.ONTOLOGY_NEAR_MISS,
    ).model_dump(mode="json")
    payload["positive_label_targets"] = [EpisodeFailureLabel.UNSUPPORTED_CLAIM.value]

    with pytest.raises(ValidationError, match="must be disjoint"):
        J7LDevelopmentCaseV1.model_validate(payload)
