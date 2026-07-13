from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.diagnostic_experiment import DiagnosticExperimentPlan

_PLAN_PATH = Path("data/evals/benchmark/diagnostic-design-v1/experiment_plan.json")


def _payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(_PLAN_PATH.read_text(encoding="utf-8")),
    )


def test_diagnostic_experiment_plan_validates_frozen_matrix() -> None:
    plan = DiagnosticExperimentPlan.model_validate(_payload())

    assert plan.status.value == "design_only"
    assert len(plan.hypotheses) == 5
    assert len(plan.cohorts) == 6
    assert len(plan.sequences) == 8
    assert plan.maximum_provider_calls == 24
    assert plan.provider_calls_permitted is False
    assert plan.execution_authorization_id is None


def test_design_cannot_authorize_provider_execution() -> None:
    payload = _payload()
    payload["provider_calls_permitted"] = True

    with pytest.raises(ValidationError):
        DiagnosticExperimentPlan.model_validate(payload)


def test_design_requires_balanced_spacing_matrix() -> None:
    payload = _payload()
    sequences = deepcopy(payload["sequences"])
    assert isinstance(sequences, list)
    assert isinstance(sequences[-1], dict)
    sequences[-1]["inter_turn_delay_seconds"] = 0
    payload["sequences"] = sequences

    with pytest.raises(ValidationError, match="spacing matrix"):
        DiagnosticExperimentPlan.model_validate(payload)


def test_design_requires_reversed_first_condition() -> None:
    payload = _payload()
    sequences = deepcopy(payload["sequences"])
    assert isinstance(sequences, list)
    assert isinstance(sequences[2], dict)
    sequences[2]["condition_label"] = "condition_b"
    payload["sequences"] = sequences

    with pytest.raises(ValidationError, match="condition B and condition C"):
        DiagnosticExperimentPlan.model_validate(payload)


def test_design_requires_complete_trace_fields() -> None:
    payload = _payload()
    raw_fields = payload["required_trace_fields"]
    assert isinstance(raw_fields, list)
    fields = cast(list[str], raw_fields.copy())
    fields.remove("provider_request_id_sha256")
    payload["required_trace_fields"] = fields

    with pytest.raises(ValidationError, match="trace fields"):
        DiagnosticExperimentPlan.model_validate(payload)


def test_pending_cohorts_cannot_claim_materialized_hashes() -> None:
    payload = _payload()
    cohorts = deepcopy(payload["cohorts"])
    assert isinstance(cohorts, list)
    assert isinstance(cohorts[0], dict)
    cohorts[0]["stable_prefix_sha256"] = "a" * 64
    payload["cohorts"] = cohorts

    with pytest.raises(ValidationError, match="pending cohorts"):
        DiagnosticExperimentPlan.model_validate(payload)
