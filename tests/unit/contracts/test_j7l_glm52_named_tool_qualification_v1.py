from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.j7l_glm52_named_tool_qualification_v1 import (
    J7LGLM52NamedToolQualificationPlanV1,
    J7LGLM52SyntheticPromptRecipeV1,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN_PATH = ROOT / (
    "data/evals/quality/j7l-glm52-named-tool-qualification-v1/"
    "qualification_plan.json"
)
RECIPE_PATH = ROOT / (
    "data/evals/quality/j7l-glm52-named-tool-qualification-v1/"
    "synthetic_prompt_recipe.json"
)


def _load(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_qualification_plan_is_inactive_bounded_and_non_reference() -> None:
    plan = J7LGLM52NamedToolQualificationPlanV1.model_validate(_load(PLAN_PATH))

    assert plan.provider == "huawei_modelarts_maas"
    assert plan.exact_model_identifier == "glm-5.2"
    assert plan.http_backend == "urllib.request"
    assert plan.execution_budget["maximum_provider_http_requests"] == 2
    assert plan.execution_budget["maximum_model_inference_requests"] == 1
    assert plan.execution_budget["maximum_catalog_requests"] == 1
    assert plan.execution_budget["qualification_token_allowance"] == 20_000
    assert plan.execution_budget["automatic_retry_permitted"] is False
    assert plan.execution_budget["external_spend_ceiling_zar"] == 0
    assert plan.provider_call_authorized is False
    assert plan.credential_access_authorized is False
    assert plan.network_access_authorized is False
    assert plan.execution_command_available is False
    assert plan.j7l_reference_request_permitted is False
    assert plan.jev_request_permitted is False
    assert plan.binding_freeze_permitted is False


def test_synthetic_recipe_contains_no_frozen_case_content() -> None:
    recipe = J7LGLM52SyntheticPromptRecipeV1.model_validate(_load(RECIPE_PATH))

    assert recipe.synthetic_only is True
    assert recipe.contains_frozen_j7l_case_content is False
    assert recipe.contains_jev_content is False
    assert recipe.contains_frozen_reference_answers is False
    assert recipe.synthetic_case["case_id"] == "synthetic-glm52-tool-boundary-001"


def test_plan_rejects_execution_authority_mutation() -> None:
    payload = _load(PLAN_PATH)
    payload["provider_call_authorized"] = True

    with pytest.raises(ValidationError):
        J7LGLM52NamedToolQualificationPlanV1.model_validate(payload)
