from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from auragateway.contracts.retrieval_eval import (
    DevelopmentRetrievalSet,
    RetrievalEvaluationCase,
)

DEVELOPMENT_SET_PATH = Path("data/evals/retrieval/development-v1/accepted_cases.json")


def test_development_set_loads_exactly_twenty_four_cases() -> None:
    payload = json.loads(DEVELOPMENT_SET_PATH.read_text(encoding="utf-8"))

    development_set = DevelopmentRetrievalSet.model_validate(payload)

    assert len(development_set.cases) == 24
    assert len({case.case_family for case in development_set.cases}) >= 7
    assert all(case.accept_reason for case in development_set.cases)
    assert all(case.difficulty_reason for case in development_set.cases)


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


def test_development_case_cannot_use_held_out_split() -> None:
    payload = json.loads(DEVELOPMENT_SET_PATH.read_text(encoding="utf-8"))["cases"][0]
    payload["evaluation_split"] = "held_out"

    try:
        RetrievalEvaluationCase.model_validate(payload)
    except ValidationError as exc:
        assert "development retrieval cases must use the development split" in str(exc)
        return
    raise AssertionError("development case accepted a held-out split")
