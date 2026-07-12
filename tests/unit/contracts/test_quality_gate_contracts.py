from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.quality_gate import (
    ConditionQualityMetrics,
    QualityComparisonInput,
    QualityGateFixtureSet,
)

_FIXTURE_PATH = Path("data/evals/quality/noninferiority-v1/fixtures.json")


def _fixtures() -> QualityGateFixtureSet:
    return QualityGateFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_contract_loads_every_fixed_case() -> None:
    fixtures = _fixtures()

    assert len(fixtures.cases) == 10
    assert sum(case.negative_control for case in fixtures.cases) == 9


def test_condition_metrics_reject_impossible_counts() -> None:
    payload = _fixtures().cases[0].comparison.conditions[0].model_dump()
    payload["task_success_count"] = payload["sample_count"] + 1

    with pytest.raises(ValidationError, match="task_success_count cannot exceed"):
        ConditionQualityMetrics.model_validate(payload)


def test_comparison_requires_conditions_a_b_and_c_exactly_once() -> None:
    payload = _fixtures().cases[0].comparison.model_dump(mode="json")
    payload["conditions"][2]["condition_id"] = "condition_b"

    with pytest.raises(ValidationError, match="conditions must be unique"):
        QualityComparisonInput.model_validate(payload)


def test_comparison_contract_is_frozen_and_extra_forbid() -> None:
    comparison = _fixtures().cases[0].comparison

    with pytest.raises(ValidationError, match="frozen"):
        cast(Any, comparison).comparison_id = "quality-compare-other"

    payload = json.loads(comparison.model_dump_json())
    payload["raw_candidate_output"] = "prohibited"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        QualityComparisonInput.model_validate(payload)
