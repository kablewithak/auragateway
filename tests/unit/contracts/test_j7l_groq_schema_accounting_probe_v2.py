from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.j7l_groq_schema_accounting_probe_v2 import (
    SchemaAccountingProbePlanV2,
)

_REVIEW_ROOT = Path("data/evals/quality/j7l-groq-schema-accounting-review-v1")
_V1_PLAN = _REVIEW_ROOT / "probe_plan.json"
_V2_PLAN = _REVIEW_ROOT / "probe_plan_v2.json"


def _load(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_v2_is_bounded_completion_budget_repair() -> None:
    v1 = _load(_V1_PLAN)
    v2 = _load(_V2_PLAN)

    expected = dict(v1)
    expected.update(
        {
            "schema_version": "2.0.0",
            "plan_id": "j7l-groq-schema-accounting-observation-v2",
            "maximum_completion_tokens": 384,
            "protected_raw_responses_path": (
                ".local/auragateway/j7l-groq-schema-accounting-probe-v2/raw_responses.jsonl"
            ),
            "protected_parsed_responses_path": (
                ".local/auragateway/j7l-groq-schema-accounting-probe-v2/parsed_responses.jsonl"
            ),
        }
    )

    assert v2 == expected

    plan = SchemaAccountingProbePlanV2.model_validate(v2)

    assert plan.maximum_completion_tokens == 384
    assert plan.planned_attempt_count == 2
    assert plan.maximum_provider_calls == 2
    assert plan.messages_identical_across_attempts is True
    assert plan.only_response_format_may_differ is True
    assert plan.provider_call_authorized is False
    assert plan.execution_command_available is False
    assert plan.j7l_reference_request_permitted is False
    assert plan.jev_request_permitted is False


def test_v2_rejects_underbudgeted_32_token_ceiling() -> None:
    payload = _load(_V2_PLAN)
    payload["maximum_completion_tokens"] = 32

    with pytest.raises(ValidationError):
        SchemaAccountingProbePlanV2.model_validate(payload)
