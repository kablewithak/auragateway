"""Typed contract for the bounded GLM-5.2 named-tool qualification."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import Field, JsonValue, field_validator, model_validator

from auragateway.contracts.quality_development_evaluation_v2 import FrozenModel

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class J7LGLM52SyntheticPromptRecipeV1(FrozenModel):
    schema_version: Literal["1.0.0"]
    recipe_id: Literal["j7l-glm52-named-tool-synthetic-prompt-v1"]
    synthetic_only: Literal[True]
    contains_frozen_j7l_case_content: Literal[False]
    contains_jev_content: Literal[False]
    contains_frozen_reference_answers: Literal[False]
    system_instruction: str = Field(min_length=40, max_length=1000)
    synthetic_case: dict[str, JsonValue]
    deterministic_padding: dict[str, JsonValue]
    expected_tool_arguments: dict[str, JsonValue]

    @model_validator(mode="after")
    def validate_synthetic_case(self) -> Self:
        case_id = self.synthetic_case.get("case_id")
        if not isinstance(case_id, str) or not case_id.startswith("synthetic-"):
            raise ValueError("qualification case must use a synthetic case ID")
        if case_id.startswith("j7l-dev-"):
            raise ValueError("frozen J7L case IDs are prohibited in qualification")
        line = self.deterministic_padding.get("line")
        repeat_count = self.deterministic_padding.get("repeat_count")
        if not isinstance(line, str) or not line:
            raise ValueError("synthetic padding line is required")
        if isinstance(repeat_count, bool) or not isinstance(repeat_count, int):
            raise ValueError("synthetic padding repeat_count must be an integer")
        if repeat_count < 1 or repeat_count > 500:
            raise ValueError("synthetic padding repeat_count is outside the frozen bound")
        return self


class J7LGLM52NamedToolQualificationPlanV1(FrozenModel):
    schema_version: Literal["1.0.0"]
    plan_id: Literal["j7l-glm52-named-tool-boundary-qualification-v1"]
    status: Literal["REVIEW_READY_INACTIVE"]
    binding_plan_id: Literal["j7l-glm52-reference-judge-binding-plan-v1"]
    binding_plan_source_merge_commit: Literal["0ba2b7b22e7f79d50ba45c2220da7faa0735433c"]
    provider: Literal["huawei_modelarts_maas"]
    exact_model_identifier: Literal["glm-5.2"]
    provider_version_or_revision_required_for_final_binding: Literal[True]
    catalog_endpoint_url: Literal[
        "https://api-ap-southeast-1.modelarts-maas.com/v2/models"
    ]
    chat_endpoint_url: Literal[
        "https://api-ap-southeast-1.modelarts-maas.com/openai/v1/chat/completions"
    ]
    region_label: Literal["ap-southeast-1"]
    credential_env_name: Literal["HUAWEI_MAAS_API_KEY"]
    http_backend: Literal["urllib.request"]
    named_tool_contract_path: str
    named_tool_contract_sha256: Literal["2279c972598100c5bb52c77b97c6134f86e8cf77d479167358b1d52a5fd9e695"]
    synthetic_prompt_recipe_path: str
    synthetic_prompt_recipe_sha256: Literal["1096b01fcffa5b42c79b77dce2840ddb9ebf8ce837c7ed304e1c6f092c40167b"]
    model_projection_path: str
    model_projection_sha256: Literal["b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"]
    request_contract: dict[str, JsonValue]
    execution_budget: dict[str, JsonValue]
    acceptance_requirements: dict[str, JsonValue]
    claim_boundary: dict[str, bool]
    protected_raw_response_path: str
    protected_parsed_response_path: str
    public_result_path: str
    provider_documentation_observed_on: Literal["2026-09-21"]
    provider_documentation: dict[str, JsonValue]
    provider_call_authorized: Literal[False]
    credential_access_authorized: Literal[False]
    network_access_authorized: Literal[False]
    execution_command_available: Literal[False]
    activation_required: Literal[True]
    j7l_reference_request_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    binding_freeze_permitted: Literal[False]
    next_gate: Literal["AUTHORIZE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_V1"]

    @field_validator(
        "named_tool_contract_sha256",
        "synthetic_prompt_recipe_sha256",
        "model_projection_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("qualification hashes must be lowercase SHA-256")
        return value

    @field_validator(
        "named_tool_contract_path",
        "synthetic_prompt_recipe_path",
        "model_projection_path",
        "protected_raw_response_path",
        "protected_parsed_response_path",
        "public_result_path",
    )
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("qualification paths must be repository-relative")
        return value

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        budget = self.execution_budget
        if budget.get("maximum_provider_http_requests") != 2:
            raise ValueError("qualification HTTP request ceiling must remain two")
        if budget.get("maximum_model_inference_requests") != 1:
            raise ValueError("qualification inference request ceiling must remain one")
        if budget.get("maximum_catalog_requests") != 1:
            raise ValueError("qualification catalog request ceiling must remain one")
        if budget.get("qualification_token_allowance") != 20000:
            raise ValueError("qualification token allowance must remain 20000")
        if budget.get("automatic_retry_permitted") is not False:
            raise ValueError("automatic retries must remain forbidden")
        if budget.get("resume_permitted") is not False:
            raise ValueError("resume must remain forbidden")
        if budget.get("rerun_permitted") is not False:
            raise ValueError("rerun must remain forbidden")
        if budget.get("external_spend_ceiling_zar") != 0:
            raise ValueError("qualification external spend ceiling must remain zero")

        request = self.request_contract
        if request.get("stream") is not False:
            raise ValueError("qualification must remain non-streaming")
        if request.get("max_completion_tokens") != 768:
            raise ValueError("qualification output ceiling must remain 768")
        if request.get("structured_output_mode") != "FORCED_NAMED_TOOL":
            raise ValueError("qualification structured output mode drifted")
        if request.get("tool_name") != "submit_reference_judgment":
            raise ValueError("qualification tool name drifted")
        if request.get("response_format_present") is not False:
            raise ValueError("response_format must remain absent")
        return self
