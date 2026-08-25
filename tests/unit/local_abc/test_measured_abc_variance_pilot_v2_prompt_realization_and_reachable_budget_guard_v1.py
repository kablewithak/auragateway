from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_prompt_realization_and_reachable_budget_guard_v1 as subject,
)
from auragateway.local_abc import measured_abc_variance_pilot_v2_standalone_runtime_v2 as runtime

ROOT = Path(__file__).resolve().parents[3]
ADMISSION_SPEC_PATH = ROOT / "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json"


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _admission_spec() -> object:
    return cast(object, _load(ADMISSION_SPEC_PATH))


def _valid_response() -> dict[str, object]:
    content = json.dumps(
        {
            "decision": "answer",
            "reason_code": "evidence_sufficient",
            "response": "Supported answer.",
            "citation_ids": ["source-1"],
        }
    )
    return {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}


def test_v2_static_prompt_excludes_stale_v1_terminal_schema() -> None:
    compiler = _load(ROOT / subject.COMPILER_SPEC_PATH)
    admission = _load(ROOT / subject.STANDALONE_ADMISSION_SPEC_PATH)
    prompt = subject.build_static_system_prompt(compiler, admission)
    assert "development-live-compact-v2" in prompt
    assert '"reason_code"' in prompt
    assert '"missing_fields"' in prompt
    assert "missing_information" not in prompt
    assert '"confidence_band"' not in prompt
    assert '"few-shot-example-v1"' not in prompt


def test_prompt_placement_preserves_a_vs_b_c_semantics() -> None:
    compiler = _load(ROOT / subject.COMPILER_SPEC_PATH)
    admission = _load(ROOT / subject.STANDALONE_ADMISSION_SPEC_PATH)
    static_prompt = subject.build_static_system_prompt(compiler, admission)
    case_ids, episodes, source_map = subject._selected_material(ROOT)
    episode = episodes[case_ids[0]]
    a = subject.build_pilot_messages(
        condition_id="A",
        static_prompt=static_prompt,
        episode=episode,
        source_map=source_map,
        turn_index=1,
        history=[],
    )
    b = subject.build_pilot_messages(
        condition_id="B",
        static_prompt=static_prompt,
        episode=episode,
        source_map=source_map,
        turn_index=1,
        history=[],
    )
    c = subject.build_pilot_messages(
        condition_id="C",
        static_prompt=static_prompt,
        episode=episode,
        source_map=source_map,
        turn_index=1,
        history=[],
    )
    assert a[0]["content"].startswith(static_prompt)
    assert a[0]["content"] != static_prompt
    assert a[1]["content"] == subject.CONDITION_A_USER_PROMPT
    assert b[0]["content"] == static_prompt
    assert c == b


def test_materialization_binds_all_240_slots_without_future_prompt_claims() -> None:
    materialization = subject.build_materialization(ROOT)
    assert len(materialization.request_slots) == 240
    assert (
        materialization.prompt_contract.static_prior_assistant_256_token_allowance_relied_on
        is False
    )
    assert (
        materialization.prompt_contract.prospective_next_prompt_check_before_history_commit_required
        is True
    )
    dependent = [
        item
        for item in materialization.request_slots
        if item.history_dependency == "prior_admitted_history"
    ]
    assert len(dependent) == 162
    assert all(item.known_messages_sha256 is None for item in dependent)
    assert materialization.accepted_tokenizer_envelope_proof_complete is False
    assert materialization.new_execution_authorized is False


def test_runtime_rejects_history_before_commit_when_next_prompt_would_overflow() -> None:
    history: runtime.JsonHistory = []
    sender_calls = 0

    def render_messages(
        request: runtime.RuntimeTurnRequest,
        candidate_history: runtime.JsonHistory,
    ) -> runtime.MessageList:
        content = request.user_content + "|" + str(len(candidate_history))
        return [{"role": "user", "content": content}]

    def token_counter(messages: runtime.MessageList) -> int:
        content = messages[0]["content"]
        return 100 if content.endswith("|0") else 3841

    def sender(
        request: runtime.RuntimeTurnRequest,
        messages: runtime.MessageList,
    ) -> object:
        nonlocal sender_calls
        assert request.request_id == "turn-1"
        assert messages
        sender_calls += 1
        return _valid_response()

    requests = cast(
        tuple[
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
        ],
        tuple(
            runtime.RuntimeTurnRequest(
                request_id=f"turn-{index}",
                user_content=f"Question {index}",
                worker_id="worker_1",
            )
            for index in range(1, 5)
        ),
    )
    result = runtime.execute_trajectory(
        requests=requests,
        history=history,
        admission_spec=_admission_spec(),
        render_messages=render_messages,
        token_counter=token_counter,
        send_response=sender,
    )
    assert result.failed is True
    assert result.failure_code == "V2_RUNTIME_REACHABLE_PROMPT_BUDGET_REJECTED"
    assert result.completed_turn_count == 0
    assert result.request_attempt_count == 1
    assert sender_calls == 1
    assert history == []


def test_runtime_commits_only_after_current_and_next_budget_checks_pass() -> None:
    history: runtime.JsonHistory = []
    sender_calls = 0

    def render_messages(
        request: runtime.RuntimeTurnRequest,
        candidate_history: runtime.JsonHistory,
    ) -> runtime.MessageList:
        return [
            {
                "role": "user",
                "content": request.user_content + "|" + str(len(candidate_history)),
            }
        ]

    def token_counter(messages: runtime.MessageList) -> int:
        assert messages
        return 100

    def sender(
        request: runtime.RuntimeTurnRequest,
        messages: runtime.MessageList,
    ) -> object:
        nonlocal sender_calls
        assert request.request_id
        assert messages
        sender_calls += 1
        return _valid_response()

    requests = cast(
        tuple[
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
        ],
        tuple(
            runtime.RuntimeTurnRequest(
                request_id=f"turn-{index}",
                user_content=f"Question {index}",
                worker_id="worker_1",
            )
            for index in range(1, 5)
        ),
    )
    result = runtime.execute_trajectory(
        requests=requests,
        history=history,
        admission_spec=_admission_spec(),
        render_messages=render_messages,
        token_counter=token_counter,
        send_response=sender,
    )
    assert result.failed is False
    assert result.completed_turn_count == 4
    assert result.request_attempt_count == 4
    assert sender_calls == 4
    assert len(history) == 8
