from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from auragateway.contracts.prefix import (
    PrefixMutationCaseSet,
    PrefixTurnFixtureSet,
    StaticCompilerSpec,
)


def test_static_compiler_spec_loads_frozen_contract() -> None:
    payload = json.loads(Path("data/context/compiler_spec.json").read_text(encoding="utf-8"))
    spec = StaticCompilerSpec.model_validate(payload)
    assert spec.status == "frozen"
    assert len(spec.tools) == 2
    assert len(spec.segments) == 4


def test_prefix_turn_fixture_set_requires_five_growing_turns() -> None:
    payload = json.loads(
        Path("data/context/prefix-determinism-v1/turns.json").read_text(encoding="utf-8")
    )
    fixtures = PrefixTurnFixtureSet.model_validate(payload)
    assert [len(turn.volatile_log.items) for turn in fixtures.turns] == [1, 3, 5, 7, 9]


def test_prefix_mutation_case_set_covers_every_required_control() -> None:
    payload = json.loads(
        Path("data/context/prefix-determinism-v1/mutation_cases.json").read_text(encoding="utf-8")
    )
    cases = PrefixMutationCaseSet.model_validate(payload)
    assert len(cases.cases) == 7


def test_static_compiler_spec_rejects_tool_order_gap() -> None:
    payload = json.loads(Path("data/context/compiler_spec.json").read_text(encoding="utf-8"))
    payload["tools"][1]["order"] = 3
    try:
        StaticCompilerSpec.model_validate(payload)
    except ValidationError as exc:
        assert "tool order must be contiguous" in str(exc)
    else:
        raise AssertionError("invalid tool order was accepted")


def test_prefix_turn_fixture_set_rejects_non_growing_logs() -> None:
    payload = json.loads(
        Path("data/context/prefix-determinism-v1/turns.json").read_text(encoding="utf-8")
    )
    payload["turns"][4]["volatile_log"]["items"] = payload["turns"][3]["volatile_log"]["items"]
    try:
        PrefixTurnFixtureSet.model_validate(payload)
    except ValidationError as exc:
        assert "each controlled turn must append volatile context" in str(exc)
    else:
        raise AssertionError("non-growing turn log was accepted")
