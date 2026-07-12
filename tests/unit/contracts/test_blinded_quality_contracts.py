"""Contract tests for Gate 6 blinded quality assets."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import (
    BlindedQualityFixtureSet,
    BlindedQualityRubric,
    ReviewAssignmentManifest,
    ReviewRole,
    RubricCriterion,
)

ROOT = Path(__file__).parents[3]
ASSET_ROOT = ROOT / "data/evals/quality/blinded-v1"


def test_rubric_loads_every_required_criterion() -> None:
    rubric = BlindedQualityRubric.model_validate_json(
        (ASSET_ROOT / "rubric.json").read_text(encoding="utf-8")
    )
    assert {item.criterion for item in rubric.criteria} == set(RubricCriterion)
    assert rubric.passing_total_score == 21
    assert rubric.material_score_delta == 2


def test_rubric_rejects_extra_fields() -> None:
    payload = {
        "criteria": [],
        "unexpected": True,
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        BlindedQualityRubric.model_validate(payload)


def test_fixture_set_loads_positive_and_negative_controls() -> None:
    fixtures = BlindedQualityFixtureSet.model_validate_json(
        (ASSET_ROOT / "fixtures.json").read_text(encoding="utf-8")
    )
    assert len(fixtures.cases) == 10
    assert sum(case.negative_control for case in fixtures.cases) == 5
    assert any(not case.negative_control for case in fixtures.cases)


def test_frozen_fixture_cannot_be_mutated() -> None:
    fixtures = BlindedQualityFixtureSet.model_validate_json(
        (ASSET_ROOT / "fixtures.json").read_text(encoding="utf-8")
    )
    with pytest.raises(ValidationError, match="frozen"):
        cast(Any, fixtures).schema_version = "2.0.0"


def test_assignment_manifest_rejects_duplicate_review_ids() -> None:
    payload = {
        "protocol_id": "blinded-adjudication-v1",
        "sampling_seed": 20260712,
        "episode_count": 1,
        "primary_assignment_count": 1,
        "secondary_assignment_count": 0,
        "double_review_episode_ids": [],
        "assignments": [
            {
                "review_id": "review-0123456789abcdef01234567",
                "episode_id": "ep-func-001",
                "role": "primary",
                "assignment_key_sha256": hashlib.sha256(b"one").hexdigest(),
            },
            {
                "review_id": "review-0123456789abcdef01234567",
                "episode_id": "ep-func-002",
                "role": "primary",
                "assignment_key_sha256": hashlib.sha256(b"two").hexdigest(),
            },
        ],
    }
    with pytest.raises(ValidationError, match="review assignment IDs must be unique"):
        ReviewAssignmentManifest.model_validate(payload)


def test_assignment_role_does_not_preassign_adjudicator() -> None:
    assert ReviewRole.ADJUDICATOR.value == "adjudicator"
