from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import TypeAdapter, ValidationError

from auragateway.contracts.episodes import TerminalDecisionOutput
from auragateway.local_abc import measured_abc_variance_pilot_v2_output_admission_runtime as runtime
from auragateway.local_abc import measured_abc_variance_pilot_v2_output_contract as subject

ROOT = Path(__file__).resolve().parents[3]
TERMINAL_ADAPTER: TypeAdapter[TerminalDecisionOutput] = TypeAdapter(TerminalDecisionOutput)


def _valid_payloads() -> tuple[dict[str, object], ...]:
    return (
        {
            "decision": "answer",
            "reason_code": "evidence_sufficient",
            "response": "Use the supported Nimbus Relay procedure.",
            "citation_ids": ["NR-API-001"],
            "unresolved_items": [],
        },
        {
            "decision": "clarify",
            "reason_code": "missing_required_parameter",
            "question": "Which environment is affected?",
            "missing_fields": ["environment"],
            "citation_ids": [],
        },
        {
            "decision": "escalate",
            "reason_code": "incomplete_documentation",
            "escalation_reason_code": "documentation_gap",
            "explanation": "The frozen evidence does not define this procedure.",
            "evidence_source_ids": ["NR-API-002"],
        },
        {
            "decision": "refuse",
            "reason_code": "unsupported_capability",
            "refusal_reason_code": "unsupported_product_behaviour",
            "explanation": "The requested behavior is not supported by the frozen evidence.",
            "safe_alternative": "Use the documented Nimbus Relay capability instead.",
        },
    )


def _response(payload: dict[str, object], finish_reason: str = "stop") -> dict[str, object]:
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": json.dumps(payload)},
            }
        ]
    }


def test_compiler_derives_four_variant_standalone_contract() -> None:
    schema = subject.terminal_output_json_schema()
    spec = subject.compile_standalone_admission_spec(schema)
    assert tuple(item.decision for item in spec.variants) == (
        "answer",
        "clarify",
        "escalate",
        "refuse",
    )
    assert spec.discriminator_field == "decision"
    assert spec.semantic_contract == "TerminalDecisionOutput"


def test_compiler_ignores_semantically_irrelevant_pydantic_schema_ordering() -> None:
    original = subject.terminal_output_json_schema()
    reordered = copy.deepcopy(original)
    discriminator = cast(dict[str, object], reordered["discriminator"])
    mapping = cast(dict[str, object], discriminator["mapping"])
    discriminator["mapping"] = dict(reversed(tuple(mapping.items())))
    one_of = cast(list[object], reordered["oneOf"])
    reordered["oneOf"] = list(reversed(one_of))
    assert (
        subject.compile_standalone_admission_spec(original)
        == subject.compile_standalone_admission_spec(reordered)
    )


def test_compiler_accepts_pydantic_enum_descriptions_as_annotations() -> None:
    schema = subject.terminal_output_json_schema()
    definitions = cast(dict[str, object], schema["$defs"])
    escalation = cast(dict[str, object], definitions["EscalationReasonCode"])
    refusal = cast(dict[str, object], definitions["RefusalReasonCode"])
    assert escalation["description"] == "Typed reasons that permit escalation."
    assert refusal["description"] == "Typed reasons that permit refusal."
    subject.compile_standalone_admission_spec(schema)


def test_response_format_matches_strict_vllm_boundary() -> None:
    schema = subject.terminal_output_json_schema()
    response_format = subject.strict_response_format(schema)
    assert response_format["type"] == "json_schema"
    nested = cast(dict[str, object], response_format["json_schema"])
    assert nested["name"] == subject.RESPONSE_FORMAT_NAME
    assert nested["strict"] is True
    assert nested["schema"] == schema
    generation = subject.build_generation_contract()
    assert generation.max_tokens == 256
    assert generation.hidden_retries_permitted is False
    assert generation.response_format_sha256 == subject.sha256_json(response_format)


def test_valid_terminal_variants_match_pydantic_and_standalone_runtime() -> None:
    spec = subject.compile_standalone_admission_spec().model_dump(mode="json")
    for payload in _valid_payloads():
        canonical = subject.canonical_json(payload)
        TERMINAL_ADAPTER.validate_json(canonical)
        admitted = runtime.admit_terminal_output(canonical, spec)
        assert admitted.canonical_json == canonical
        assert admitted.payload == payload


def _invalid_answer_payloads() -> tuple[dict[str, object], ...]:
    payloads: list[dict[str, object]] = []

    missing = copy.deepcopy(_valid_payloads()[0])
    missing.pop("reason_code")
    payloads.append(missing)

    for field_name, value in (
        ("extra_field", "forbidden"),
        ("decision", "unknown"),
        ("reason_code", "wrong_reason"),
        ("response", 7),
        ("citation_ids", []),
        ("response", ""),
        ("question", "mixed variant field"),
    ):
        payload = copy.deepcopy(_valid_payloads()[0])
        payload[field_name] = value
        payloads.append(payload)
    return tuple(payloads)


@pytest.mark.parametrize("payload", _invalid_answer_payloads())
def test_invalid_answer_variants_fail_pydantic_and_standalone_runtime(
    payload: dict[str, object],
) -> None:
    serialized = json.dumps(payload)
    with pytest.raises(ValidationError):
        TERMINAL_ADAPTER.validate_json(serialized)
    spec = subject.compile_standalone_admission_spec().model_dump(mode="json")
    with pytest.raises(runtime.RuntimeOutputAdmissionError):
        runtime.admit_terminal_output(serialized, spec)



def test_optional_empty_array_defaults_match_pydantic_canonicalization() -> None:
    payload = copy.deepcopy(_valid_payloads()[0])
    payload.pop("unresolved_items")
    serialized = subject.canonical_json(payload)
    validated = TERMINAL_ADAPTER.validate_json(serialized)
    spec = subject.compile_standalone_admission_spec().model_dump(mode="json")
    admitted = runtime.admit_terminal_output(serialized, spec)
    assert admitted.payload == validated.model_dump(mode="json")
    assert admitted.payload["unresolved_items"] == []


def test_malformed_json_fails_both_boundaries() -> None:
    malformed = '{"decision":"answer"'
    with pytest.raises(ValidationError):
        TERMINAL_ADAPTER.validate_json(malformed)
    spec = subject.compile_standalone_admission_spec().model_dump(mode="json")
    with pytest.raises(runtime.RuntimeOutputAdmissionError) as observed:
        runtime.admit_terminal_output(malformed, spec)
    assert observed.value.error_code == "V2_OUTPUT_JSON_INVALID"


def test_compiler_rejects_unsupported_json_schema_feature() -> None:
    schema = copy.deepcopy(subject.terminal_output_json_schema())
    defs = cast(dict[str, object], schema["$defs"])
    answer = cast(dict[str, object], defs["AnswerDecisionOutput"])
    properties = cast(dict[str, object], answer["properties"])
    response = cast(dict[str, object], properties["response"])
    response["maxLength"] = 500
    with pytest.raises(subject.OutputContractCompileError) as observed:
        subject.compile_standalone_admission_spec(schema)
    assert observed.value.error_code == "V2_OUTPUT_SCHEMA_UNSUPPORTED"


def test_finish_reason_length_rejects_without_state_mutation() -> None:
    spec = subject.compile_standalone_admission_spec().model_dump(mode="json")
    history = [{"role": "system", "content": "frozen"}]
    before = copy.deepcopy(history)
    with pytest.raises(runtime.RuntimeOutputAdmissionError) as observed:
        runtime.admit_and_commit_turn(
            history,
            "current user turn",
            _response(_valid_payloads()[0], finish_reason="length"),
            spec,
        )
    assert observed.value.error_code == "V2_OUTPUT_TRUNCATED"
    assert history == before


def test_schema_invalid_output_rejects_without_state_mutation() -> None:
    spec = subject.compile_standalone_admission_spec().model_dump(mode="json")
    history = [{"role": "system", "content": "frozen"}]
    before = copy.deepcopy(history)
    invalid = copy.deepcopy(_valid_payloads()[0])
    invalid["citation_ids"] = []
    with pytest.raises(runtime.RuntimeOutputAdmissionError):
        runtime.admit_and_commit_turn(history, "current user turn", _response(invalid), spec)
    assert history == before


def test_valid_output_is_canonicalized_before_atomic_history_commit() -> None:
    spec = subject.compile_standalone_admission_spec().model_dump(mode="json")
    history: runtime.JsonHistory = [{"role": "system", "content": "frozen"}]
    payload = _valid_payloads()[0]
    admitted = runtime.admit_and_commit_turn(
        history,
        "current user turn",
        _response(payload),
        spec,
    )
    assert len(history) == 3
    assert history[-2] == {"role": "user", "content": "current user turn"}
    assert history[-1] == {"role": "assistant", "content": admitted.canonical_json}
    assert admitted.canonical_json == subject.canonical_json(payload)


def test_prompt_budget_proof_requires_exact_240_unique_fitting_requests() -> None:
    observations = tuple(
        subject.PromptBudgetObservation(
            request_id=f"request-{index:03d}",
            rendered_prompt_sha256=f"{index:064x}",
            prompt_token_count=3840,
        )
        for index in range(240)
    )
    proof = subject.PromptBudgetProof(
        tokenizer_identity_sha256="f" * 64,
        observations=observations,
    )
    assert len(proof.observations) == 240
    assert proof.pilot_execution_authorized is False
    assert proof.final_measured_abc_execution_authorized is False


def test_prompt_budget_rejects_one_token_over_frozen_context_limit() -> None:
    with pytest.raises(ValidationError):
        subject.PromptBudgetObservation(
            request_id="too-large",
            rendered_prompt_sha256="a" * 64,
            prompt_token_count=3841,
        )


def test_standalone_runtime_has_no_pydantic_dependency() -> None:
    source = (
        ROOT
        / "src"
        / "auragateway"
        / "local_abc"
        / "measured_abc_variance_pilot_v2_output_admission_runtime.py"
    ).read_text(encoding="utf-8")
    assert "pydantic" not in source.casefold()
