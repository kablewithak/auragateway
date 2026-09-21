from __future__ import annotations

import json
from pathlib import Path

from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceToolArgumentsV1,
)
from auragateway.local_abc import j7l_glm52_named_tool_qualification_v1 as subject

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_TOOL_CONTRACT_SHA256 = "2279c972598100c5bb52c77b97c6134f86e8cf77d479167358b1d52a5fd9e695"
EXPECTED_RECIPE_SHA256 = "1096b01fcffa5b42c79b77dce2840ddb9ebf8ce837c7ed304e1c6f092c40167b"


def test_dry_run_builds_exact_non_live_named_tool_request() -> None:
    result = subject.dry_run(ROOT)
    body = subject.build_chat_request_body(ROOT)

    assert result["status"] == "J7L_GLM52_NAMED_TOOL_QUALIFICATION_DESIGN_PASS"
    assert result["provider_call_performed"] is False
    assert result["credential_accessed"] is False
    assert result["network_access_performed"] is False
    assert result["j7l_reference_request_performed"] is False
    assert result["jev_request_performed"] is False
    assert result["execution_command_available"] is False

    assert set(body) == {
        "model",
        "messages",
        "tools",
        "tool_choice",
        "stream",
        "max_completion_tokens",
        "chat_template_kwargs",
    }
    assert body["model"] == "glm-5.2"
    assert body["stream"] is False
    assert body["max_completion_tokens"] == 768
    assert body["chat_template_kwargs"] == {"thinking": False}
    assert "response_format" not in body
    assert "temperature" not in body
    assert "top_p" not in body
    assert "seed" not in body

    tools = body["tools"]
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "submit_reference_judgment"
    assert body["tool_choice"] == {
        "type": "function",
        "function": {"name": "submit_reference_judgment"},
    }


def test_plan_binds_existing_tool_contract_and_synthetic_recipe() -> None:
    plan = subject.load_plan(ROOT)

    assert plan.named_tool_contract_sha256 == EXPECTED_TOOL_CONTRACT_SHA256
    assert plan.synthetic_prompt_recipe_sha256 == EXPECTED_RECIPE_SHA256


def test_synthetic_expected_arguments_validate_against_reference_boundary() -> None:
    _, recipe, _, _ = subject.load_assets(ROOT)

    arguments = J7LReferenceToolArgumentsV1.model_validate(
        recipe.expected_tool_arguments
    )

    assert arguments.verdict.value == "pass"
    assert arguments.failure_labels == ()


def test_request_contains_no_frozen_j7l_case_id() -> None:
    body = subject.build_chat_request_body(ROOT)
    encoded = json.dumps(body, sort_keys=True)

    assert "j7l-dev-" not in encoded
    assert "synthetic-glm52-tool-boundary-001" in encoded
