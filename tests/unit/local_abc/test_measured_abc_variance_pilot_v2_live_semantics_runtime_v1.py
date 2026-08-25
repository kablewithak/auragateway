from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_prompt_realization_and_reachable_budget_guard_v1 as prompt_guard,
)
from auragateway.local_abc.contracts import WorkerId
from auragateway.local_abc.measured_abc_variance_pilot_v2 import (
    NeutralWorkerSample,
    build_neutral_worker_plan,
)
from auragateway.local_abc.measured_abc_variance_pilot_v2 import (
    assess_neutral_worker_qualification as assess_typed,
)
from auragateway.local_abc.measured_abc_variance_pilot_v2_live_semantics_runtime_v1 import (
    LiveSemanticsRuntimeError,
    assess_neutral_worker_qualification,
    build_neutral_messages,
    build_pilot_messages,
    build_static_system_prompt,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPILER_SPEC_PATH = REPO_ROOT / "data/context/compiler_spec.json"
ADMISSION_SPEC_PATH = (
    REPO_ROOT / "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json"
)
SOURCE_PATH = (
    REPO_ROOT
    / "src/auragateway/local_abc/measured_abc_variance_pilot_v2_live_semantics_runtime_v1.py"
)


def _load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _pass_samples() -> tuple[NeutralWorkerSample, ...]:
    samples: list[NeutralWorkerSample] = []
    for pair_index in range(1, 11):
        first = WorkerId.WORKER_1 if pair_index % 2 == 1 else WorkerId.WORKER_2
        second = WorkerId.WORKER_2 if first is WorkerId.WORKER_1 else WorkerId.WORKER_1
        for pair_order_index, worker in enumerate((first, second)):
            base = 10.0 if worker is WorkerId.WORKER_1 else 10.5
            samples.append(
                NeutralWorkerSample(
                    measurement_pair_index=pair_index,
                    pair_order_index=pair_order_index,
                    worker_id=worker,
                    admitted=True,
                    telemetry_valid=True,
                    time_to_first_token_ms=base,
                    prefill_duration_ms=base * 2,
                )
            )
    return tuple(samples)


def test_live_module_is_stdlib_only() -> None:
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots <= {"__future__", "json", "statistics", "typing"}


def test_static_prompt_matches_frozen_reference() -> None:
    compiler_spec = _load_object(COMPILER_SPEC_PATH)
    admission_spec = _load_object(ADMISSION_SPEC_PATH)
    observed = build_static_system_prompt(compiler_spec, admission_spec)
    expected = prompt_guard.build_static_system_prompt(compiler_spec, admission_spec)
    assert observed == expected


@pytest.mark.parametrize(
    "phase",
    ["schema_canary", "warmup", "neutral_worker_qualification"],
)
def test_neutral_messages_match_frozen_reference(phase: str) -> None:
    compiler_spec = _load_object(COMPILER_SPEC_PATH)
    admission_spec = _load_object(ADMISSION_SPEC_PATH)
    static_prompt = build_static_system_prompt(compiler_spec, admission_spec)
    observed = build_neutral_messages(phase, static_prompt)
    expected = prompt_guard.build_neutral_messages(phase, static_prompt)
    assert observed == expected


@pytest.mark.parametrize("condition_id", ["A", "B", "C"])
def test_pilot_messages_match_frozen_reference(condition_id: str) -> None:
    compiler_spec = _load_object(COMPILER_SPEC_PATH)
    admission_spec = _load_object(ADMISSION_SPEC_PATH)
    static_prompt = build_static_system_prompt(compiler_spec, admission_spec)
    episode: dict[str, object] = {
        "episode_id": "synthetic-parity-case",
        "title": "Synthetic parity case",
        "turns": [
            {"user_message": "turn one"},
            {"user_message": "turn two"},
            {"user_message": "turn three"},
            {"user_message": "turn four"},
        ],
        "source_scope": {"required_source_ids": ["S1"]},
    }
    source_map = {"S1": "Synthetic source evidence."}
    history = [
        {"role": "user", "content": "synthetic prior user"},
        {
            "role": "assistant",
            "content": '{"citation_ids":["S1"],"decision":"answer",'
            '"reason_code":"evidence_sufficient","response":"ok",'
            '"unresolved_items":[]}',
        },
    ]
    observed = build_pilot_messages(
        condition_id=condition_id,
        static_prompt=static_prompt,
        episode=episode,
        source_map=source_map,
        turn_index=2,
        history=history,
    )
    expected = prompt_guard.build_pilot_messages(
        condition_id=condition_id,
        static_prompt=static_prompt,
        episode=episode,
        source_map=source_map,
        turn_index=2,
        history=history,
    )
    assert observed == expected


def test_neutral_assessment_matches_typed_reference_for_pass() -> None:
    plan = build_neutral_worker_plan()
    samples = _pass_samples()
    expected = assess_typed(plan, samples).model_dump(mode="json")
    observed = assess_neutral_worker_qualification(
        plan.model_dump(mode="json"),
        [sample.model_dump(mode="json") for sample in samples],
    )
    assert observed == expected


def test_neutral_assessment_matches_typed_reference_for_failure() -> None:
    plan = build_neutral_worker_plan()
    samples = list(_pass_samples())
    first = samples[0]
    samples[0] = first.model_copy(update={"telemetry_valid": False})
    expected = assess_typed(plan, tuple(samples)).model_dump(mode="json")
    observed = assess_neutral_worker_qualification(
        plan.model_dump(mode="json"),
        [sample.model_dump(mode="json") for sample in samples],
    )
    assert observed == expected


def test_neutral_assessment_rejects_duplicate_sample_identity() -> None:
    plan = build_neutral_worker_plan().model_dump(mode="json")
    samples = [sample.model_dump(mode="json") for sample in _pass_samples()]
    samples[-1] = dict(samples[0])
    with pytest.raises(LiveSemanticsRuntimeError) as exc_info:
        assess_neutral_worker_qualification(plan, samples)
    assert exc_info.value.error_code == "V2_LIVE_NEUTRAL_SAMPLE_DUPLICATE"
