"""Stdlib-only output admission and atomic history mutation for variance-pilot V2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final, Never, TypeAlias, cast

JsonObject: TypeAlias = dict[str, object]
JsonHistory: TypeAlias = list[dict[str, str]]

SUPPORTED_SPEC_VERSION: Final = "1.0.0"


class RuntimeOutputAdmissionError(RuntimeError):
    """Metadata-safe standalone output-admission failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


@dataclass(frozen=True)
class AdmittedTerminalOutput:
    """Canonical admitted terminal-decision output."""

    payload: JsonObject
    canonical_json: str


def canonical_json(value: object) -> str:
    """Return deterministic JSON for admitted assistant state."""

    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _fail(code: str, message: str) -> Never:
    raise RuntimeOutputAdmissionError(code, message)


def _as_object(value: object, code: str, message: str) -> JsonObject:
    if not isinstance(value, dict):
        _fail(code, message)
    if any(not isinstance(key, str) for key in value):
        _fail(code, message)
    return cast(JsonObject, value)


def _as_string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _fail(
            "V2_OUTPUT_FIELD_TYPE_INVALID",
            f"field {field_name} must be an array of strings",
        )
    return cast(list[str], value)


def _validate_field_spec(field_spec: JsonObject) -> None:
    if set(field_spec) != {
        "schema_version",
        "kind",
        "allowed_values",
        "minimum_length",
        "minimum_items",
        "default_empty_array",
    }:
        _fail("V2_ADMISSION_SPEC_INVALID", "field specification keys drifted")
    if field_spec.get("schema_version") != SUPPORTED_SPEC_VERSION:
        _fail("V2_ADMISSION_SPEC_INVALID", "field specification version is unsupported")
    kind = field_spec.get("kind")
    allowed_values = field_spec.get("allowed_values")
    minimum_length = field_spec.get("minimum_length")
    minimum_items = field_spec.get("minimum_items")
    default_empty_array = field_spec.get("default_empty_array")

    if not isinstance(allowed_values, list) or any(
        not isinstance(item, str) for item in allowed_values
    ):
        _fail("V2_ADMISSION_SPEC_INVALID", "field allowed-values contract is invalid")
    if len(allowed_values) != len(set(cast(list[str], allowed_values))):
        _fail("V2_ADMISSION_SPEC_INVALID", "field allowed-values contract has duplicates")
    if (
        not isinstance(minimum_length, int)
        or isinstance(minimum_length, bool)
        or minimum_length < 0
    ):
        _fail("V2_ADMISSION_SPEC_INVALID", "field minimum-length contract is invalid")
    if (
        not isinstance(minimum_items, int)
        or isinstance(minimum_items, bool)
        or minimum_items < 0
    ):
        _fail("V2_ADMISSION_SPEC_INVALID", "field minimum-items contract is invalid")
    if not isinstance(default_empty_array, bool):
        _fail("V2_ADMISSION_SPEC_INVALID", "field default contract is invalid")
    if kind == "string":
        if minimum_items != 0 or default_empty_array:
            _fail("V2_ADMISSION_SPEC_INVALID", "string field contract is inconsistent")
        return
    if kind == "string_array":
        if allowed_values or minimum_length != 0:
            _fail("V2_ADMISSION_SPEC_INVALID", "string-array field contract is inconsistent")
        return
    _fail("V2_ADMISSION_SPEC_INVALID", "field kind is unsupported")


def _validate_field(field_name: str, value: object, field_spec: JsonObject) -> None:
    _validate_field_spec(field_spec)
    kind = field_spec["kind"]
    allowed_values = cast(list[str], field_spec["allowed_values"])
    minimum_length = cast(int, field_spec["minimum_length"])
    minimum_items = cast(int, field_spec["minimum_items"])

    if kind == "string":
        if not isinstance(value, str):
            _fail("V2_OUTPUT_FIELD_TYPE_INVALID", f"field {field_name} must be a string")
        if len(value) < minimum_length:
            _fail(
                "V2_OUTPUT_FIELD_LENGTH_INVALID",
                f"field {field_name} is shorter than the frozen minimum",
            )
        if allowed_values and value not in allowed_values:
            _fail(
                "V2_OUTPUT_FIELD_VALUE_INVALID",
                f"field {field_name} violates the frozen value set",
            )
        return

    if kind == "string_array":
        items = _as_string_list(value, field_name)
        if len(items) < minimum_items:
            _fail(
                "V2_OUTPUT_FIELD_ITEMS_INVALID",
                f"field {field_name} has too few items",
            )
        return

    _fail("V2_ADMISSION_SPEC_INVALID", "field kind is unsupported")


def validate_admission_spec(spec: object) -> JsonObject:
    """Validate the compact generated admission contract before using it."""

    root = _as_object(spec, "V2_ADMISSION_SPEC_INVALID", "admission spec root must be an object")
    if set(root) != {
        "schema_version",
        "semantic_contract",
        "discriminator_field",
        "variants",
    }:
        _fail("V2_ADMISSION_SPEC_INVALID", "admission spec root keys drifted")
    if root.get("schema_version") != SUPPORTED_SPEC_VERSION:
        _fail("V2_ADMISSION_SPEC_INVALID", "admission spec version is unsupported")
    if root.get("semantic_contract") != "TerminalDecisionOutput":
        _fail("V2_ADMISSION_SPEC_INVALID", "admission semantic contract is invalid")
    if root.get("discriminator_field") != "decision":
        _fail("V2_ADMISSION_SPEC_INVALID", "admission discriminator must be decision")
    variants = root.get("variants")
    if not isinstance(variants, list) or len(variants) != 4:
        _fail("V2_ADMISSION_SPEC_INVALID", "admission spec must contain four variants")

    decisions: set[str] = set()
    decision_order: list[str] = []
    for raw_variant in variants:
        variant = _as_object(
            raw_variant,
            "V2_ADMISSION_SPEC_INVALID",
            "admission variant must be an object",
        )
        if set(variant) != {"schema_version", "decision", "fields", "required_fields"}:
            _fail("V2_ADMISSION_SPEC_INVALID", "admission variant keys drifted")
        if variant.get("schema_version") != SUPPORTED_SPEC_VERSION:
            _fail("V2_ADMISSION_SPEC_INVALID", "admission variant version is unsupported")
        decision = variant.get("decision")
        fields = variant.get("fields")
        required_fields = variant.get("required_fields")
        if not isinstance(decision, str) or not decision:
            _fail("V2_ADMISSION_SPEC_INVALID", "admission variant decision is invalid")
        if decision in decisions:
            _fail("V2_ADMISSION_SPEC_INVALID", "admission decisions must be unique")
        decisions.add(decision)
        decision_order.append(decision)
        if not isinstance(fields, dict) or not fields:
            _fail("V2_ADMISSION_SPEC_INVALID", "admission variant fields are invalid")
        if any(not isinstance(key, str) for key in fields):
            _fail("V2_ADMISSION_SPEC_INVALID", "admission field names must be strings")
        if not isinstance(required_fields, list) or any(
            not isinstance(item, str) for item in required_fields
        ):
            _fail("V2_ADMISSION_SPEC_INVALID", "required fields contract is invalid")
        typed_required = cast(list[str], required_fields)
        typed_fields = cast(dict[str, object], fields)
        if len(typed_required) != len(set(typed_required)):
            _fail("V2_ADMISSION_SPEC_INVALID", "required fields contain duplicates")
        if not set(typed_required).issubset(set(typed_fields)):
            _fail("V2_ADMISSION_SPEC_INVALID", "required fields are not defined")
        decision_field = _as_object(
            typed_fields.get("decision"),
            "V2_ADMISSION_SPEC_INVALID",
            "decision field specification must be an object",
        )
        if decision_field.get("allowed_values") != [decision]:
            _fail("V2_ADMISSION_SPEC_INVALID", "decision field does not match its variant")
        for field_name, raw_field_spec in typed_fields.items():
            field_spec = _as_object(
                raw_field_spec,
                "V2_ADMISSION_SPEC_INVALID",
                "field specification must be an object",
            )
            _validate_field_spec(field_spec)
            if (
                field_spec.get("default_empty_array") is True
                and field_name in typed_required
            ):
                _fail("V2_ADMISSION_SPEC_INVALID", "required fields cannot use runtime defaults")
    if decisions != {"answer", "clarify", "escalate", "refuse"}:
        _fail("V2_ADMISSION_SPEC_INVALID", "admission decision set drifted")
    if decision_order != ["answer", "clarify", "escalate", "refuse"]:
        _fail("V2_ADMISSION_SPEC_INVALID", "admission decision order drifted")
    return root


def admit_terminal_output(content: str, spec: object) -> AdmittedTerminalOutput:
    """Parse and validate one model output against the generated standalone contract."""

    root = validate_admission_spec(spec)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeOutputAdmissionError(
            "V2_OUTPUT_JSON_INVALID",
            "model output is not valid JSON",
        ) from exc
    payload = _as_object(
        parsed,
        "V2_OUTPUT_ROOT_INVALID",
        "model output root must be a JSON object",
    )
    decision = payload.get("decision")
    if not isinstance(decision, str):
        _fail("V2_OUTPUT_DISCRIMINATOR_INVALID", "decision discriminator is missing or invalid")

    variants = cast(list[object], root["variants"])
    selected: JsonObject | None = None
    for raw_variant in variants:
        variant = _as_object(
            raw_variant,
            "V2_ADMISSION_SPEC_INVALID",
            "admission variant must be an object",
        )
        if variant.get("decision") == decision:
            selected = variant
            break
    if selected is None:
        _fail("V2_OUTPUT_DISCRIMINATOR_INVALID", "decision discriminator is unsupported")

    fields = cast(dict[str, object], selected["fields"])
    required = cast(list[str], selected["required_fields"])
    unknown = sorted(set(payload) - set(fields))
    if unknown:
        _fail("V2_OUTPUT_EXTRA_FIELDS", "model output contains fields outside the frozen variant")
    missing = sorted(set(required) - set(payload))
    if missing:
        _fail("V2_OUTPUT_REQUIRED_FIELD_MISSING", "model output is missing required fields")

    normalized = dict(payload)
    for field_name, raw_field_spec in fields.items():
        field_spec = _as_object(
            raw_field_spec,
            "V2_ADMISSION_SPEC_INVALID",
            "field specification must be an object",
        )
        if field_name not in normalized and field_spec.get("default_empty_array") is True:
            normalized[field_name] = []

    for field_name, value in normalized.items():
        field_spec = _as_object(
            fields[field_name],
            "V2_ADMISSION_SPEC_INVALID",
            "field specification must be an object",
        )
        _validate_field(field_name, value, field_spec)

    canonical = canonical_json(normalized)
    canonical_payload = cast(JsonObject, json.loads(canonical))
    return AdmittedTerminalOutput(payload=canonical_payload, canonical_json=canonical)


def _extract_response_content(response: object) -> str:
    envelope = _as_object(
        response,
        "V2_RESPONSE_ENVELOPE_INVALID",
        "response envelope must be an object",
    )
    choices = envelope.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        _fail("V2_RESPONSE_ENVELOPE_INVALID", "response must contain exactly one choice")
    choice = _as_object(
        choices[0],
        "V2_RESPONSE_ENVELOPE_INVALID",
        "response choice must be an object",
    )
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        _fail("V2_OUTPUT_TRUNCATED", "finish_reason length is a hard output-contract failure")
    if finish_reason != "stop":
        _fail("V2_FINISH_REASON_INVALID", "finish_reason must be stop")
    message = _as_object(
        choice.get("message"),
        "V2_RESPONSE_ENVELOPE_INVALID",
        "response message must be an object",
    )
    content = message.get("content")
    if not isinstance(content, str):
        _fail("V2_RESPONSE_ENVELOPE_INVALID", "response content must be a string")
    return content


def admit_response(response: object, spec: object) -> AdmittedTerminalOutput:
    """Admit an OpenAI-compatible response only after envelope and finish-reason checks."""

    return admit_terminal_output(_extract_response_content(response), spec)


def admit_and_commit_turn(
    history: JsonHistory,
    user_content: str,
    response: object,
    spec: object,
) -> AdmittedTerminalOutput:
    """Mutate history atomically only after terminal output has been fully admitted."""

    if not isinstance(user_content, str) or not user_content:
        _fail("V2_USER_CONTENT_INVALID", "current user content must be a non-empty string")
    admitted = admit_response(response, spec)
    history.extend(
        (
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": admitted.canonical_json},
        )
    )
    return admitted
