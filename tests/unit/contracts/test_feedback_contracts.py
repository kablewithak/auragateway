from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.feedback import (
    FeedbackEvidenceEvent,
    FeedbackFixtureSet,
    FeedbackTrajectory,
)

FIXTURE_PATH = Path("data/evals/feedback/efc-v1/fixtures.json")


def _fixture_payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


def test_fixture_set_validates() -> None:
    fixtures = FeedbackFixtureSet.model_validate(_fixture_payload())
    assert len(fixtures.cases) == 11
    assert sum(case.negative_control for case in fixtures.cases) == 9


def test_feedback_event_is_frozen() -> None:
    fixtures = FeedbackFixtureSet.model_validate(_fixture_payload())
    event = fixtures.cases[0].trajectory.events[0]
    with pytest.raises(ValidationError, match="frozen"):
        cast(Any, event).turn_index = 99


def test_retained_feedback_requires_location() -> None:
    payload = _fixture_payload()["cases"][0]["trajectory"]["events"][0]
    payload["retention_location"] = None
    with pytest.raises(ValidationError, match="retention location"):
        FeedbackEvidenceEvent.model_validate(payload)


def test_action_change_must_match_fingerprints() -> None:
    payload = _fixture_payload()["cases"][0]["trajectory"]["events"][0]
    payload["next_action_changed"] = False
    with pytest.raises(ValidationError, match="must match"):
        FeedbackEvidenceEvent.model_validate(payload)


def test_trajectory_rejects_out_of_order_events() -> None:
    payload = _fixture_payload()["cases"][0]["trajectory"]
    payload["events"] = list(reversed(payload["events"]))
    with pytest.raises(ValidationError, match="ordered by turn_index"):
        FeedbackTrajectory.model_validate(payload)


def test_extra_fields_are_forbidden() -> None:
    payload = _fixture_payload()["cases"][0]["trajectory"]["events"][0]
    payload["raw_feedback_text"] = "must not be retained"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FeedbackEvidenceEvent.model_validate(payload)
