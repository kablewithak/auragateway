"""Non-live design verification for the GLM-5.2 named-tool qualification."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from auragateway.contracts.j7l_glm52_named_tool_qualification_v1 import (
    J7LGLM52NamedToolQualificationPlanV1,
    J7LGLM52SyntheticPromptRecipeV1,
)
from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceToolArgumentsV1,
)
from auragateway.local_abc import quality_semantic_projection_v1 as semantic_projection

PLAN_PATH = Path(
    "data/evals/quality/j7l-glm52-named-tool-qualification-v1/qualification_plan.json"
)


class QualificationDesignError(RuntimeError):
    """Fail-closed non-live qualification design error."""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_mapping(path: Path) -> Mapping[str, object]:
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        raise QualificationDesignError(
            "QUALIFICATION_JSON_SHAPE_INVALID",
            f"{path.as_posix()} must contain one JSON object",
        )
    return cast(Mapping[str, object], payload)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def load_plan(repo_root: Path) -> J7LGLM52NamedToolQualificationPlanV1:
    root = repo_root.resolve()
    return J7LGLM52NamedToolQualificationPlanV1.model_validate(
        _load_json(root / PLAN_PATH)
    )


def load_assets(
    repo_root: Path,
) -> tuple[
    J7LGLM52NamedToolQualificationPlanV1,
    J7LGLM52SyntheticPromptRecipeV1,
    Mapping[str, object],
    Mapping[str, object],
]:
    root = repo_root.resolve()
    plan = load_plan(root)

    tool_path = root / plan.named_tool_contract_path
    if _sha256_file(tool_path) != plan.named_tool_contract_sha256:
        raise QualificationDesignError(
            "QUALIFICATION_TOOL_CONTRACT_DRIFT",
            "named-tool contract bytes drifted",
        )

    recipe_path = root / plan.synthetic_prompt_recipe_path
    if _sha256_file(recipe_path) != plan.synthetic_prompt_recipe_sha256:
        raise QualificationDesignError(
            "QUALIFICATION_SYNTHETIC_RECIPE_DRIFT",
            "synthetic prompt recipe bytes drifted",
        )

    parity = semantic_projection.verify_materialized_projections(root)
    if parity.model_projection_sha256 != plan.model_projection_sha256:
        raise QualificationDesignError(
            "QUALIFICATION_MODEL_PROJECTION_DRIFT",
            "model semantic projection identity drifted",
        )

    recipe = J7LGLM52SyntheticPromptRecipeV1.model_validate(_load_json(recipe_path))
    tool_contract = _load_mapping(tool_path)
    model_projection = _load_mapping(root / plan.model_projection_path)
    J7LReferenceToolArgumentsV1.model_validate(recipe.expected_tool_arguments)
    return plan, recipe, tool_contract, model_projection


def build_catalog_request_descriptor(
    plan: J7LGLM52NamedToolQualificationPlanV1,
) -> dict[str, object]:
    return {
        "method": "GET",
        "url": plan.catalog_endpoint_url,
        "authorization_header_required": True,
        "credential_env_name": plan.credential_env_name,
        "body_present": False,
    }


def _synthetic_payload(
    recipe: J7LGLM52SyntheticPromptRecipeV1,
    model_projection: Mapping[str, object],
) -> dict[str, object]:
    line = cast(str, recipe.deterministic_padding["line"])
    repeat_count = cast(int, recipe.deterministic_padding["repeat_count"])
    return {
        "semantic_projection": dict(model_projection),
        "synthetic_case": recipe.synthetic_case,
        "synthetic_envelope_padding": [line for _ in range(repeat_count)],
        "transport_instruction": (
            "Return exactly one submit_reference_judgment tool call. "
            "Use the expected synthetic outcome encoded in the visible case evidence."
        ),
    }


def build_chat_request_body(repo_root: Path) -> dict[str, object]:
    plan, recipe, tool_contract, model_projection = load_assets(repo_root)

    wire_value = tool_contract.get("wire")
    if not isinstance(wire_value, Mapping):
        raise QualificationDesignError(
            "QUALIFICATION_TOOL_WIRE_INVALID",
            "named-tool contract wire is invalid",
        )
    wire = cast(Mapping[str, object], wire_value)
    tools = wire.get("tools")
    tool_choice = wire.get("tool_choice")
    if not isinstance(tools, list) or len(tools) != 1:
        raise QualificationDesignError(
            "QUALIFICATION_TOOL_INVENTORY_INVALID",
            "qualification requires exactly one output tool",
        )
    if not isinstance(tool_choice, Mapping):
        raise QualificationDesignError(
            "QUALIFICATION_TOOL_CHOICE_INVALID",
            "qualification requires a named tool choice",
        )

    payload: dict[str, object] = {
        "model": plan.exact_model_identifier,
        "messages": [
            {"role": "system", "content": recipe.system_instruction},
            {
                "role": "user",
                "content": canonical_json(
                    _synthetic_payload(recipe, model_projection)
                ),
            },
        ],
        "tools": tools,
        "tool_choice": dict(tool_choice),
        "stream": False,
        "max_completion_tokens": 768,
        "chat_template_kwargs": {"thinking": False},
    }

    forbidden = {"response_format", "temperature", "top_p", "seed"}
    if forbidden & set(payload):
        raise QualificationDesignError(
            "QUALIFICATION_REQUEST_CONTROL_DRIFT",
            "forbidden request controls are present",
        )
    return payload


def dry_run(repo_root: Path) -> dict[str, object]:
    plan, recipe, _, _ = load_assets(repo_root)
    body = build_chat_request_body(repo_root)
    encoded = canonical_json(body).encode("utf-8")
    catalog = build_catalog_request_descriptor(plan)

    return {
        "schema_version": "1.0.0",
        "status": "J7L_GLM52_NAMED_TOOL_QUALIFICATION_DESIGN_PASS",
        "plan_id": plan.plan_id,
        "provider": plan.provider,
        "model": plan.exact_model_identifier,
        "catalog_endpoint_url": plan.catalog_endpoint_url,
        "chat_endpoint_url": plan.chat_endpoint_url,
        "http_backend": plan.http_backend,
        "catalog_request_descriptor": catalog,
        "chat_request_body_sha256": hashlib.sha256(encoded).hexdigest(),
        "chat_request_body_bytes": len(encoded),
        "synthetic_case_id": recipe.synthetic_case["case_id"],
        "tool_name": "submit_reference_judgment",
        "max_completion_tokens": 768,
        "qualification_token_allowance": plan.execution_budget[
            "qualification_token_allowance"
        ],
        "maximum_provider_http_requests": plan.execution_budget[
            "maximum_provider_http_requests"
        ],
        "maximum_model_inference_requests": plan.execution_budget[
            "maximum_model_inference_requests"
        ],
        "provider_call_performed": False,
        "credential_accessed": False,
        "network_access_performed": False,
        "j7l_reference_request_performed": False,
        "jev_request_performed": False,
        "execution_command_available": False,
        "next_gate": plan.next_gate,
    }
