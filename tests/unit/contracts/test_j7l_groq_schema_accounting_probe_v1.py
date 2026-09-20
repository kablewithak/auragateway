from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.j7l_groq_schema_accounting_probe_v1 import (
    PreActivationMeasurementsV1,
    SchemaAccountingProbePlanV1,
    SchemaAccountingProbeReviewV1,
)

_REVIEW_ROOT = Path("data/evals/quality/j7l-groq-schema-accounting-review-v1")


def _load(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_plan_freezes_two_call_single_variable_experiment() -> None:
    plan = SchemaAccountingProbePlanV1.model_validate(_load(_REVIEW_ROOT / "probe_plan.json"))

    assert plan.planned_attempt_count == 2
    assert plan.maximum_provider_calls == 2
    assert plan.messages_identical_across_attempts is True
    assert plan.only_response_format_may_differ is True
    assert plan.control_response_format_present is False
    assert plan.strict_response_format_present is True
    assert plan.provider_call_authorized is False
    assert plan.execution_command_available is False
    assert plan.j7l_reference_request_permitted is False
    assert plan.jev_request_permitted is False
    assert plan.external_spend_ceiling_zar == 0


def test_measurements_preserve_token_conflict() -> None:
    measurements = PreActivationMeasurementsV1.model_validate(
        _load(_REVIEW_ROOT / "preactivation_measurements.json")
    )

    assert measurements.maximum_exact_message_tokens == 7448
    assert measurements.organization_tpm_observed == 8000
    assert measurements.maximum_conservative_plus_output_budget_tokens == 8300


def test_measurements_reject_non_conflicting_envelope() -> None:
    payload = _load(_REVIEW_ROOT / "preactivation_measurements.json")
    payload["maximum_conservative_plus_output_budget_tokens"] = 7900

    with pytest.raises(ValidationError):
        PreActivationMeasurementsV1.model_validate(payload)


def test_review_cannot_authorize_reference_execution() -> None:
    review = SchemaAccountingProbeReviewV1.model_validate(_load(_REVIEW_ROOT / "review.json"))

    assert review.provider_call_performed is False
    assert review.provider_call_authorized is False
    assert review.execution_command_available is False
    assert review.j7l_reference_request_permitted is False
    assert review.jev_request_permitted is False
    assert review.claim_boundary["groq_reference_judge_binding_frozen"] is False
