from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from auragateway.contracts.retrieval_gate import (
    GateOneDecisionStatus,
    HeldOutFreezeRecord,
    HeldOutValidationPolicy,
    HeldOutValidationReport,
)

ROOT = Path("data/evals/retrieval/held-out-v1")


def test_held_out_freeze_record_precedes_candidate_results() -> None:
    record = HeldOutFreezeRecord.model_validate_json(
        (ROOT / "freeze_record.json").read_text(encoding="utf-8")
    )

    assert record.status == "frozen_before_candidate_evaluation"
    assert record.authoring_complete is True
    assert record.candidate_results_present_at_freeze is False


def test_held_out_policy_locks_two_development_finalists() -> None:
    policy = HeldOutValidationPolicy.model_validate_json(
        (ROOT / "policy.json").read_text(encoding="utf-8")
    )

    assert [item.development_rank for item in policy.finalists] == [1, 2]
    assert {item.top_k for item in policy.finalists} == {5}
    assert policy.development_recommendation_is_not_auto_confirmed is True


def test_current_gate_one_decision_is_blocked_without_selected_candidate() -> None:
    report = HeldOutValidationReport.model_validate_json(
        (ROOT / "decision.json").read_text(encoding="utf-8")
    )

    assert report.decision.status is GateOneDecisionStatus.BLOCKED
    assert report.decision.selected_retriever_config_id is None
    assert report.decision.gate_1_passed is False
    assert report.decision.retrieval_freeze_permitted is False


def test_policy_rejects_duplicate_finalist_ranks() -> None:
    payload = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))
    payload["finalists"][1]["development_rank"] = 1

    try:
        HeldOutValidationPolicy.model_validate(payload)
    except ValidationError as exc:
        assert "duplicate development ranks" in str(exc)
        return
    raise AssertionError("held-out policy accepted duplicate finalist ranks")


def test_blocked_decision_rejects_selected_candidate_fields() -> None:
    payload = json.loads((ROOT / "decision.json").read_text(encoding="utf-8"))
    payload["decision"]["selected_retriever_config_id"] = "bm25-fixed-window-v1"

    try:
        HeldOutValidationReport.model_validate(payload)
    except ValidationError as exc:
        assert "blocked decision must not include selected candidate fields" in str(exc)
        return
    raise AssertionError("blocked decision accepted selected candidate fields")
