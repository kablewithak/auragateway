"""Pydantic-derived output and budget contracts for measured A/B/C variance-pilot V2."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, TypeAdapter, model_validator

from auragateway.contracts.episodes import TerminalDecisionOutput
from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.measured_abc_variance_pilot_v2 import (
    MAX_OUTPUT_TOKENS,
    MAXIMUM_TOTAL_MODEL_REQUESTS,
)

MAX_MODEL_LEN: Final = 4096
RESPONSE_FORMAT_NAME: Final = "auragateway_terminal_decision_output_v2"
_TERMINAL_OUTPUT_ADAPTER: Final[TypeAdapter[TerminalDecisionOutput]] = TypeAdapter(
    TerminalDecisionOutput
)


class OutputContractCompileError(RuntimeError):
    """Fail-closed compiler error for unsupported Pydantic JSON-schema features."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class RuntimeFieldKind(StrEnum):
    """Field kinds supported by the stdlib-only V2 admission runtime."""

    STRING = "string"
    STRING_ARRAY = "string_array"


class RuntimeFieldSpec(LocalABCContract):
    """Compact generated validation rules for one terminal-output field."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    kind: RuntimeFieldKind
    allowed_values: tuple[str, ...] = ()
    minimum_length: int = Field(default=0, ge=0)
    minimum_items: int = Field(default=0, ge=0)
    default_empty_array: bool = False

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.kind is RuntimeFieldKind.STRING and (
            self.minimum_items != 0 or self.default_empty_array
        ):
            raise ValueError("string fields cannot declare array-only controls")
        if self.kind is RuntimeFieldKind.STRING_ARRAY and (
            self.allowed_values or self.minimum_length != 0
        ):
            raise ValueError("string-array fields support array controls only")
        if len(self.allowed_values) != len(set(self.allowed_values)):
            raise ValueError("field allowed values must be unique")
        return self


class RuntimeVariantSpec(LocalABCContract):
    """Generated standalone rules for one decision discriminator value."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    decision: str = Field(min_length=1)
    fields: dict[str, RuntimeFieldSpec]
    required_fields: tuple[str, ...]

    @model_validator(mode="after")
    def validate_variant(self) -> Self:
        if "decision" not in self.fields:
            raise ValueError("variant must contain decision discriminator")
        decision_rule = self.fields["decision"]
        if decision_rule.kind is not RuntimeFieldKind.STRING:
            raise ValueError("decision discriminator must be a string")
        if decision_rule.allowed_values != (self.decision,):
            raise ValueError("decision discriminator must be frozen to the variant value")
        if not set(self.required_fields).issubset(self.fields):
            raise ValueError("required fields must be defined by the variant")
        if len(self.required_fields) != len(set(self.required_fields)):
            raise ValueError("required fields must be unique")
        return self


class StandaloneAdmissionSpec(LocalABCContract):
    """Compact schema generated from TerminalDecisionOutput for the stdlib runtime."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    semantic_contract: Literal["TerminalDecisionOutput"] = "TerminalDecisionOutput"
    discriminator_field: Literal["decision"] = "decision"
    variants: tuple[
        RuntimeVariantSpec,
        RuntimeVariantSpec,
        RuntimeVariantSpec,
        RuntimeVariantSpec,
    ]

    @model_validator(mode="after")
    def validate_variants(self) -> Self:
        decisions = tuple(item.decision for item in self.variants)
        if decisions != ("answer", "clarify", "escalate", "refuse"):
            raise ValueError("terminal decision variants must remain canonical and ordered")
        return self


class GenerationContract(LocalABCContract):
    """Condition-invariant generation controls carried into the successor pilot."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    served_model_name: Literal["local-qwen2.5-0.5b-instruct"] = (
        "local-qwen2.5-0.5b-instruct"
    )
    temperature: Literal[0] = 0
    top_p: Literal[1] = 1
    seed: Literal[7] = 7
    max_tokens: Literal[256] = MAX_OUTPUT_TOKENS
    n: Literal[1] = 1
    stream: Literal[False] = False
    response_format_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hidden_retries_permitted: Literal[False] = False


class PromptBudgetObservation(LocalABCContract):
    """Exact-tokenizer observation consumed by the later runtime-integration proof."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: str = Field(min_length=1)
    rendered_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_token_count: int = Field(ge=0)
    max_output_tokens: Literal[256] = MAX_OUTPUT_TOKENS
    max_model_len: Literal[4096] = MAX_MODEL_LEN

    @model_validator(mode="after")
    def validate_budget(self) -> Self:
        if self.prompt_token_count + self.max_output_tokens > self.max_model_len:
            raise ValueError("prompt plus output budget exceeds frozen max_model_len")
        return self


class PromptBudgetProof(LocalABCContract):
    """Complete 240-request token-budget proof required before live authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    tokenizer_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observations: tuple[PromptBudgetObservation, ...] = Field(
        min_length=MAXIMUM_TOTAL_MODEL_REQUESTS,
        max_length=MAXIMUM_TOTAL_MODEL_REQUESTS,
    )
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_observations(self) -> Self:
        request_ids = tuple(item.request_id for item in self.observations)
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("prompt-budget request IDs must be unique")
        return self


def canonical_json(value: object) -> str:
    """Return deterministic JSON for hashing generated contract material."""

    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_json(value: object) -> str:
    """Return lowercase SHA-256 over deterministic JSON."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def terminal_output_json_schema() -> dict[str, object]:
    """Return the canonical Pydantic JSON schema for TerminalDecisionOutput."""

    return cast(dict[str, object], _TERMINAL_OUTPUT_ADAPTER.json_schema())


def strict_response_format(schema: dict[str, object] | None = None) -> dict[str, object]:
    """Build the exact vLLM/OpenAI-compatible strict response-format object."""

    selected_schema = terminal_output_json_schema() if schema is None else schema
    return {
        "type": "json_schema",
        "json_schema": {
            "name": RESPONSE_FORMAT_NAME,
            "strict": True,
            "schema": selected_schema,
        },
    }


def _compile_error(message: str) -> Never:
    raise OutputContractCompileError("V2_OUTPUT_SCHEMA_UNSUPPORTED", message)


def _object(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        _compile_error(f"{context} must be an object")
    return cast(dict[str, object], value)


def _string_list(value: object, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _compile_error(f"{context} must be a string list")
    return tuple(cast(list[str], value))


def _resolve_string_enum(
    root_defs: dict[str, object],
    field_schema: dict[str, object],
) -> tuple[str, ...] | None:
    ref = field_schema.get("$ref")
    if ref is None:
        return None
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        _compile_error("only local $defs references are supported")
    name = ref.removeprefix("#/$defs/")
    target = _object(root_defs.get(name), "referenced definition")
    allowed_keys = {"description", "enum", "title", "type"}
    if set(target) - allowed_keys:
        _compile_error("referenced enum definition contains unsupported keywords")
    if target.get("type") != "string":
        _compile_error("referenced definition must be a string enum")
    return _string_list(target.get("enum"), "referenced enum values")


def _compile_field(
    root_defs: dict[str, object],
    raw_field_schema: object,
) -> RuntimeFieldSpec:
    schema = _object(raw_field_schema, "field schema")
    ref_values = _resolve_string_enum(root_defs, schema)
    if ref_values is not None:
        if set(schema) != {"$ref"}:
            _compile_error("$ref fields cannot combine local sibling keywords")
        return RuntimeFieldSpec(kind=RuntimeFieldKind.STRING, allowed_values=ref_values)

    field_type = schema.get("type")
    if field_type == "string":
        allowed_keys = {"const", "description", "enum", "minLength", "title", "type"}
        if set(schema) - allowed_keys:
            _compile_error("string field contains unsupported JSON-schema keywords")
        const = schema.get("const")
        enum_values = schema.get("enum")
        if const is not None and enum_values is not None:
            _compile_error("string field cannot define both const and enum")
        allowed_values: tuple[str, ...] = ()
        if const is not None:
            if not isinstance(const, str):
                _compile_error("string const must be a string")
            allowed_values = (const,)
        elif enum_values is not None:
            allowed_values = tuple(sorted(_string_list(enum_values, "string enum values")))
        minimum_length = schema.get("minLength", 0)
        if (
            not isinstance(minimum_length, int)
            or isinstance(minimum_length, bool)
            or minimum_length < 0
        ):
            _compile_error("minLength must be a non-negative integer")
        return RuntimeFieldSpec(
            kind=RuntimeFieldKind.STRING,
            allowed_values=allowed_values,
            minimum_length=minimum_length,
        )

    if field_type == "array":
        allowed_keys = {"default", "description", "items", "minItems", "title", "type"}
        if set(schema) - allowed_keys:
            _compile_error("array field contains unsupported JSON-schema keywords")
        items = _object(schema.get("items"), "array items")
        if items != {"type": "string"}:
            _compile_error("only arrays of strings are supported")
        minimum_items = schema.get("minItems", 0)
        if (
            not isinstance(minimum_items, int)
            or isinstance(minimum_items, bool)
            or minimum_items < 0
        ):
            _compile_error("minItems must be a non-negative integer")
        has_default = "default" in schema
        default = schema.get("default")
        if has_default and default != []:
            _compile_error("only the frozen empty-array default is supported")
        return RuntimeFieldSpec(
            kind=RuntimeFieldKind.STRING_ARRAY,
            minimum_items=minimum_items,
            default_empty_array=has_default,
        )

    _compile_error("field type is unsupported")


def compile_standalone_admission_spec(
    schema: dict[str, object] | None = None,
) -> StandaloneAdmissionSpec:
    """Compile the supported TerminalDecisionOutput schema subset into runtime rules."""

    root = terminal_output_json_schema() if schema is None else schema
    required_root_keys = {"$defs", "discriminator", "oneOf"}
    annotation_root_keys = {"$schema", "description", "title"}
    if not required_root_keys.issubset(root):
        _compile_error("terminal schema root is missing required keywords")
    if set(root) - required_root_keys - annotation_root_keys:
        _compile_error("terminal schema root contains unsupported keywords")
    defs = _object(root.get("$defs"), "$defs")
    discriminator = _object(root.get("discriminator"), "discriminator")
    if discriminator.get("propertyName") != "decision":
        _compile_error("terminal schema discriminator must be decision")
    mapping = _object(discriminator.get("mapping"), "discriminator mapping")
    canonical_decisions = ("answer", "clarify", "escalate", "refuse")
    if set(mapping) != set(canonical_decisions):
        _compile_error("terminal discriminator mapping drifted")
    one_of = root.get("oneOf")
    if not isinstance(one_of, list) or len(one_of) != 4:
        _compile_error("terminal schema must contain four oneOf variants")

    expected_refs: set[str] = set()
    for decision in canonical_decisions:
        ref = mapping[decision]
        if not isinstance(ref, str):
            _compile_error("variant mapping references must be strings")
        expected_refs.add(ref)
    observed_refs: set[str] = set()
    for raw_ref in one_of:
        ref_object = _object(raw_ref, "oneOf member")
        if set(ref_object) != {"$ref"} or not isinstance(ref_object.get("$ref"), str):
            _compile_error("oneOf members must contain exactly one local $ref")
        observed_refs.add(cast(str, ref_object["$ref"]))
    if len(observed_refs) != 4 or observed_refs != expected_refs:
        _compile_error("oneOf references must match the discriminator mapping")

    variants: list[RuntimeVariantSpec] = []
    for decision in canonical_decisions:
        ref = mapping[decision]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
            _compile_error("variant mapping must reference local definitions")
        definition_name = ref.removeprefix("#/$defs/")
        definition = _object(defs.get(definition_name), "variant definition")
        allowed_definition_keys = {
            "additionalProperties",
            "description",
            "properties",
            "required",
            "title",
            "type",
        }
        if set(definition) - allowed_definition_keys:
            _compile_error("variant definition contains unsupported keywords")
        if (
            definition.get("type") != "object"
            or definition.get("additionalProperties") is not False
        ):
            _compile_error("variant must be a closed JSON object")
        properties = _object(definition.get("properties"), "variant properties")
        required_fields = tuple(
            sorted(_string_list(definition.get("required"), "required fields"))
        )
        compiled_fields = {
            field_name: _compile_field(defs, field_schema)
            for field_name, field_schema in properties.items()
        }
        variants.append(
            RuntimeVariantSpec(
                decision=decision,
                fields=compiled_fields,
                required_fields=required_fields,
            )
        )

    variant_tuple = cast(
        tuple[
            RuntimeVariantSpec,
            RuntimeVariantSpec,
            RuntimeVariantSpec,
            RuntimeVariantSpec,
        ],
        tuple(variants),
    )
    return StandaloneAdmissionSpec(variants=variant_tuple)


def build_generation_contract() -> GenerationContract:
    """Build the single generation contract shared by canary, neutral and A/B/C requests."""

    return GenerationContract(response_format_sha256=sha256_json(strict_response_format()))
