"""Typed contract for the bounded J7L Groq schema-accounting probe V2 repair."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import field_validator, model_validator

from auragateway.contracts.j7l_groq_schema_accounting_probe_v1 import FrozenModel

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SchemaAccountingProbePlanV2(FrozenModel):
    schema_version: Literal["2.0.0"]
    plan_id: Literal["j7l-groq-schema-accounting-observation-v2"]
    review_id: Literal["j7l-groq-schema-accounting-review-v1"]
    provider: Literal["groq"]
    exact_model_identifier: Literal["openai/gpt-oss-20b"]
    installed_sdk_version_required: Literal["1.5.0"]
    resource_path: Literal["client.chat.completions.with_raw_response.create"]
    prompt_recipe_path: str
    prompt_recipe_sha256: str
    strict_response_schema_path: str
    strict_response_schema_sha256: str
    maximum_completion_tokens: Literal[384]
    temperature_milli: Literal[0]
    streaming: Literal[False]
    storage: Literal[False]
    reasoning_effort: Literal["low"]
    timeout_seconds: Literal[30]
    planned_attempt_count: Literal[2]
    maximum_provider_calls: Literal[2]
    attempt_offsets_seconds: tuple[Literal[0], Literal[10]]
    request_roles: tuple[
        Literal["control_no_response_format"],
        Literal["strict_json_schema"],
    ]
    messages_identical_across_attempts: Literal[True]
    only_response_format_may_differ: Literal[True]
    control_response_format_present: Literal[False]
    strict_response_format_present: Literal[True]
    strict_mode: Literal[True]
    usage_prompt_tokens_required: Literal[True]
    usage_completion_tokens_required: Literal[True]
    usage_total_tokens_observed_if_present: Literal[True]
    rate_limit_headers_observed_if_present: Literal[True]
    raw_response_protected_local_required: Literal[True]
    public_raw_payload_permitted: Literal[False]
    protected_raw_responses_path: str
    protected_parsed_responses_path: str
    retry_permitted: Literal[False]
    resume_permitted: Literal[False]
    rerun_permitted: Literal[False]
    free_tier_required: Literal[True]
    paid_fallback_permitted: Literal[False]
    external_spend_ceiling_zar: Literal[0]
    j7l_reference_request_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    provider_call_authorized: Literal[False]
    execution_command_available: Literal[False]
    activation_required: Literal[True]

    @field_validator(
        "prompt_recipe_sha256",
        "strict_response_schema_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("probe hashes must be lowercase SHA-256")
        return value

    @field_validator(
        "prompt_recipe_path",
        "strict_response_schema_path",
        "protected_raw_responses_path",
        "protected_parsed_responses_path",
    )
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("probe paths must be repository-relative")
        return value

    @model_validator(mode="after")
    def validate_experiment(self) -> Self:
        if self.maximum_provider_calls != self.planned_attempt_count:
            raise ValueError("provider-call ceiling must equal the frozen attempt count")
        if self.protected_raw_responses_path == self.protected_parsed_responses_path:
            raise ValueError("raw and parsed protected evidence paths must differ")
        return self
