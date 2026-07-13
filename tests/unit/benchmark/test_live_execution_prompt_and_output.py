from __future__ import annotations

from pathlib import Path

from auragateway.benchmark.execution import (
    _parse_structured_output,
    _prompts_for_condition,
    _static_system_prompt,
)
from auragateway.contracts.evidence_bundle import BenchmarkCondition
from auragateway.contracts.prefix import StaticCompilerSpec


def _spec() -> StaticCompilerSpec:
    return StaticCompilerSpec.model_validate_json(
        Path("data/context/compiler_spec.json").read_text(encoding="utf-8")
    )


def test_condition_a_mutates_system_while_b_and_c_preserve_it() -> None:
    static = _static_system_prompt(_spec())
    first = '{"current_user_message":"first"}\n'
    second = '{"current_user_message":"second"}\n'

    a_first = _prompts_for_condition(BenchmarkCondition.A, static, first)
    a_second = _prompts_for_condition(BenchmarkCondition.A, static, second)
    b_first = _prompts_for_condition(BenchmarkCondition.B, static, first)
    b_second = _prompts_for_condition(BenchmarkCondition.B, static, second)
    c_first = _prompts_for_condition(BenchmarkCondition.C, static, first)

    assert a_first.summary().system_sha256 != a_second.summary().system_sha256
    assert b_first.summary().system_sha256 == b_second.summary().system_sha256
    assert b_first.summary().system_sha256 == c_first.summary().system_sha256
    assert b_first.summary().user_sha256 != b_second.summary().user_sha256


def test_structured_output_validation_is_strict_and_source_scoped() -> None:
    valid = (
        '{"decision":"answer","reason_code":"evidence_sufficient",'
        '"response":"Use the current API-key guidance.",'
        '"citation_ids":["NR-AUTH-001"],"unresolved_items":[]}'
    )
    out_of_scope = valid.replace("NR-AUTH-001", "NR-AUTH-999")
    fenced = "```json\n" + valid + "\n```"

    assert _parse_structured_output(valid, {"NR-AUTH-001"}) == (
        True,
        True,
        "answer",
        ("NR-AUTH-001",),
    )
    assert _parse_structured_output(out_of_scope, {"NR-AUTH-001"})[1] is False
    assert _parse_structured_output(fenced, {"NR-AUTH-001"})[0] is False
