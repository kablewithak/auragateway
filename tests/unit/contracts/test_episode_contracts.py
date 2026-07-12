from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from auragateway.contracts.episodes import (
    REQUIRED_DIAGNOSTIC_FAMILIES,
    BlindedReviewProtocol,
    FunctionalEpisodeSet,
    RuntimeEpisodeSelection,
    TerminalDecisionOutput,
)

EPISODE_ROOT = Path("data/evals/episodes")


def test_functional_set_is_frozen_and_covers_required_families() -> None:
    episode_set = FunctionalEpisodeSet.model_validate_json(
        (EPISODE_ROOT / "functional-v1/accepted_episodes.json").read_text(encoding="utf-8")
    )

    families = {episode.case_family for episode in episode_set.episodes}

    assert episode_set.episode_count == 18
    assert episode_set.development_episode_count == 12
    assert episode_set.held_out_episode_count == 6
    assert REQUIRED_DIAGNOSTIC_FAMILIES.issubset(families)
    assert all(len(episode.turns) == 4 for episode in episode_set.episodes)


def test_runtime_selection_represents_all_terminal_decisions() -> None:
    selection = RuntimeEpisodeSelection.model_validate_json(
        (EPISODE_ROOT / "runtime-v1/selection.json").read_text(encoding="utf-8")
    )

    assert selection.episode_count == 6
    assert {entry.expected_terminal_decision.value for entry in selection.entries} == {
        "answer",
        "clarify",
        "escalate",
        "refuse",
    }


def test_blinded_review_protocol_hides_experimental_fields() -> None:
    protocol = BlindedReviewProtocol.model_validate_json(
        (EPISODE_ROOT / "blinded_review_protocol.json").read_text(encoding="utf-8")
    )

    assert protocol.primary_review_fraction == 1.0
    assert protocol.double_review_fraction == 0.25
    assert protocol.double_review_episode_count == 5
    assert protocol.public_trace_contains_raw_content is False
    assert "condition_id" in protocol.reviewer_hidden_fields
    assert "cache_telemetry" in protocol.reviewer_hidden_fields


def test_terminal_output_union_accepts_typed_answer() -> None:
    adapter: TypeAdapter[TerminalDecisionOutput] = TypeAdapter(TerminalDecisionOutput)
    output = adapter.validate_python(
        {
            "decision": "answer",
            "reason_code": "evidence_sufficient",
            "response": "Use the current 24-hour token lifetime.",
            "citation_ids": ["NR-AUTH-001"],
            "unresolved_items": [],
        }
    )

    assert output.decision.value == "answer"


def test_terminal_output_union_rejects_mixed_decision_fields() -> None:
    adapter: TypeAdapter[TerminalDecisionOutput] = TypeAdapter(TerminalDecisionOutput)

    try:
        adapter.validate_python(
            {
                "decision": "clarify",
                "reason_code": "missing_required_parameter",
                "question": "Which grant type is present?",
                "missing_fields": ["grant_type"],
                "citation_ids": [],
                "response": "Use refresh_token.",
            }
        )
    except ValidationError as exc:
        assert "Extra inputs are not permitted" in str(exc)
        return
    raise AssertionError("mixed terminal-decision fields were accepted")


def test_functional_set_rejects_final_decision_mismatch() -> None:
    payload = json.loads(
        (EPISODE_ROOT / "functional-v1/accepted_episodes.json").read_text(encoding="utf-8")
    )
    payload["episodes"][0]["turns"][3]["expected_decision"] = "clarify"

    try:
        FunctionalEpisodeSet.model_validate(payload)
    except ValidationError as exc:
        assert "final turn decision must match expected terminal decision" in str(exc)
        return
    raise AssertionError("episode accepted a final terminal-decision mismatch")
