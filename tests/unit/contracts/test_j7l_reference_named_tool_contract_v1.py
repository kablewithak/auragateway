from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceJudgmentV1,
    J7LReferenceStructuredOutputContractV1,
    J7LReferenceToolArgumentsV1,
    ReferenceDecodingSettingsV1,
)

TOOL_CONTRACT_PATH = Path(
    "data/evals/quality/j7l-reference-judge-binding-v1/named_tool_contract.json"
)
BINDING_PLAN_PATH = Path("data/evals/quality/j7l-reference-judge-binding-v1/binding_plan.json")
EXPECTED_TOOL_CONTRACT_SHA256 = "2279c972598100c5bb52c77b97c6134f86e8cf77d479167358b1d52a5fd9e695"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _scores(value: int = 3) -> dict[RubricCriterion, int]:
    return {criterion: value for criterion in RubricCriterion}


def _tool_arguments() -> J7LReferenceToolArgumentsV1:
    return J7LReferenceToolArgumentsV1(
        criterion_scores=_scores(),
        failure_labels=(),
        evidence_references=("visible-evidence-1",),
        rationale="The visible evidence supports the declared scores and terminal outcome.",
        verdict=ReviewVerdict.PASS,
        uncertainty_statement=None,
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("expected JSON object")
    return payload


def test_decoding_contract_uses_forced_named_tool_not_response_format() -> None:
    decoding = ReferenceDecodingSettingsV1(reasoning_mode="DISABLED_PENDING_QUALIFICATION")

    assert decoding.structured_output_mode == "FORCED_NAMED_TOOL"
    assert "response_format" not in decoding.model_dump(mode="json")


def test_tool_arguments_are_host_bound_into_reference_judgment() -> None:
    arguments = _tool_arguments()

    judgment = J7LReferenceJudgmentV1(
        case_id="j7l-dev-001",
        request_id_sha256="a" * 64,
        judge_binding_sha256="b" * 64,
        **arguments.model_dump(),
    )

    assert judgment.case_id == "j7l-dev-001"
    assert judgment.verdict is ReviewVerdict.PASS


def test_tool_arguments_reject_inconsistent_declared_verdict() -> None:
    with pytest.raises(ValidationError, match="frozen derivation rule"):
        J7LReferenceToolArgumentsV1(
            criterion_scores=_scores(),
            failure_labels=(),
            evidence_references=("visible-evidence-1",),
            rationale="The visible evidence supports the declared scores and terminal outcome.",
            verdict=ReviewVerdict.FAIL,
            uncertainty_statement=None,
        )


def test_named_tool_artifact_freezes_one_forced_output_tool() -> None:
    root = _repo_root()
    path = root / TOOL_CONTRACT_PATH
    payload = _load_json(path)

    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_TOOL_CONTRACT_SHA256
    assert payload["structured_output_mode"] == "FORCED_NAMED_TOOL"
    assert payload["response_format_present"] is False
    assert payload["additional_model_tools_permitted"] is False
    assert payload["model_may_supply_identity_fields"] is False
    assert payload["hidden_reasoning_persisted"] is False

    wire = payload["wire"]
    assert len(wire["tools"]) == 1
    assert wire["tools"][0]["function"]["name"] == "submit_reference_judgment"
    assert wire["tool_choice"] == {
        "type": "function",
        "function": {"name": "submit_reference_judgment"},
    }

    parameters = wire["tools"][0]["function"]["parameters"]
    assert set(parameters["properties"]["criterion_scores"]["properties"]) == {
        criterion.value for criterion in RubricCriterion
    }


def test_structured_output_binding_contract_accepts_frozen_artifact_hash() -> None:
    contract = J7LReferenceStructuredOutputContractV1(
        tool_contract_id="j7l-glm52-reference-named-tool-v1",
        tool_contract_sha256=EXPECTED_TOOL_CONTRACT_SHA256,
    )

    assert contract.mode == "FORCED_NAMED_TOOL"
    assert contract.tool_name == "submit_reference_judgment"
    assert contract.tool_choice_required is True
    assert contract.response_format_present is False
    assert contract.additional_model_tools_permitted is False
    assert contract.hidden_reasoning_persisted is False


def test_binding_plan_is_non_executable_and_bounded() -> None:
    plan = _load_json(_repo_root() / BINDING_PLAN_PATH)

    assert plan["status"] == "PLANNED_NON_EXECUTABLE"
    assert plan["selected_candidate"]["provider_id"] == "huawei_modelarts_maas"
    assert plan["selected_candidate"]["model_id"] == "glm-5.2"
    assert plan["selected_candidate"]["model_version_or_revision"] is None
    assert (
        plan["selected_candidate"]["configuration_lineage"]["authority_for_auragateway_execution"]
        is False
    )
    assert plan["structured_output"]["tool_contract_sha256"] == (EXPECTED_TOOL_CONTRACT_SHA256)
    assert plan["token_budget"]["planned_primary_reference_request_count"] == 48
    assert plan["token_budget"]["planned_primary_output_token_ceiling"] == 36_864
    assert plan["token_budget"]["planned_primary_total_token_ceiling"] == 444_864
    assert plan["token_budget"]["hard_reference_phase_total_token_ceiling"] == 500_000
    assert plan["execution_policy"]["automatic_retry_permitted"] is False
    assert plan["execution_policy"]["external_spend_ceiling_zar"] == 0
    assert plan["provider_requests_performed"] == 0
    assert plan["jev_requests_performed"] == 0
    assert plan["network_access_authorized"] is False
    assert plan["reference_execution_authorized"] is False
    assert plan["binding_frozen"] is False
