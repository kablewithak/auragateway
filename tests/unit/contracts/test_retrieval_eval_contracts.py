from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from auragateway.contracts.retrieval_eval import (
    DevelopmentRetrievalSet,
    HeldOutRejectedRetrievalSet,
    HeldOutRetrievalSet,
    RetrievalEvaluationCase,
)

DEVELOPMENT_SET_PATH = Path("data/evals/retrieval/development-v1/accepted_cases.json")
HELD_OUT_SET_PATH = Path("data/evals/retrieval/held-out-v1/accepted_cases.json")
HELD_OUT_REJECTED_PATH = Path("data/evals/retrieval/held-out-v1/rejected_cases.json")


def test_development_set_loads_exactly_twenty_four_cases() -> None:
    payload = json.loads(DEVELOPMENT_SET_PATH.read_text(encoding="utf-8"))

    development_set = DevelopmentRetrievalSet.model_validate(payload)

    assert len(development_set.cases) == 24
    assert len({case.case_family for case in development_set.cases}) >= 7
    assert all(case.accept_reason for case in development_set.cases)
    assert all(case.difficulty_reason for case in development_set.cases)


def test_held_out_set_loads_exactly_twelve_cases() -> None:
    payload = json.loads(HELD_OUT_SET_PATH.read_text(encoding="utf-8"))

    held_out_set = HeldOutRetrievalSet.model_validate(payload)

    assert len(held_out_set.cases) == 12
    assert all(case.case_id.startswith("ho-ret-") for case in held_out_set.cases)
    assert all(case.evaluation_split.value == "held_out" for case in held_out_set.cases)
    assert held_out_set.authoring_complete_before_evaluation is True


def test_held_out_rejected_set_retains_five_proposals() -> None:
    payload = json.loads(HELD_OUT_REJECTED_PATH.read_text(encoding="utf-8"))

    rejected_set = HeldOutRejectedRetrievalSet.model_validate(payload)

    assert len(rejected_set.cases) == 5
    assert all(case.reject_reason for case in rejected_set.cases)


def test_required_source_must_have_relevance_judgment() -> None:
    payload = json.loads(DEVELOPMENT_SET_PATH.read_text(encoding="utf-8"))["cases"][0]
    payload["required_sources"] = ["NR-UNKNOWN-999"]

    try:
        RetrievalEvaluationCase.model_validate(payload)
    except ValidationError as exc:
        assert "required sources must have relevance judgments" in str(exc)
        return
    raise AssertionError("case accepted a required source without a relevance judgment")


def test_forbidden_source_cannot_be_relevant() -> None:
    payload = json.loads(DEVELOPMENT_SET_PATH.read_text(encoding="utf-8"))["cases"][0]
    payload["forbidden_sources"] = ["NR-AUTH-001"]

    try:
        RetrievalEvaluationCase.model_validate(payload)
    except ValidationError as exc:
        assert "forbidden sources cannot also be relevant" in str(exc)
        return
    raise AssertionError("case accepted a source as both forbidden and relevant")


def test_case_id_must_match_evaluation_split() -> None:
    payload = json.loads(DEVELOPMENT_SET_PATH.read_text(encoding="utf-8"))["cases"][0]
    payload["evaluation_split"] = "held_out"

    try:
        RetrievalEvaluationCase.model_validate(payload)
    except ValidationError as exc:
        assert "case_id must match ho-ret-<NNN>" in str(exc)
        return
    raise AssertionError("development case ID accepted a held-out split")


def test_development_set_rejects_held_out_case() -> None:
    payload = json.loads(DEVELOPMENT_SET_PATH.read_text(encoding="utf-8"))
    held_out_case = json.loads(HELD_OUT_SET_PATH.read_text(encoding="utf-8"))["cases"][0]
    payload["cases"][0] = held_out_case

    try:
        DevelopmentRetrievalSet.model_validate(payload)
    except ValidationError as exc:
        assert "development retrieval set contains a non-development case" in str(exc)
        return
    raise AssertionError("development set accepted a held-out case")
