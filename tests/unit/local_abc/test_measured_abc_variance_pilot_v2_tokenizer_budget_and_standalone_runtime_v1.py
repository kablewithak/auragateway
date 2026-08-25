from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_standalone_runtime_v1 as runtime,
)
from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_tokenizer_budget_and_standalone_runtime_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]
ADMISSION_SPEC_PATH = ROOT / "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json"


def _admission_spec() -> object:
    return cast(object, json.loads(ADMISSION_SPEC_PATH.read_text(encoding="utf-8")))


def _valid_response() -> dict[str, object]:
    content = json.dumps(
        {
            "decision": "answer",
            "reason_code": "evidence_sufficient",
            "response": "Supported answer.",
            "citation_ids": ["source-1"],
        }
    )
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": content},
            }
        ]
    }


def _length_response() -> dict[str, object]:
    return {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": "{}"},
            }
        ]
    }


def _render_messages(
    request: runtime.RuntimeTurnRequest,
    history: runtime.JsonHistory,
) -> runtime.MessageList:
    messages: runtime.MessageList = [{"role": "system", "content": "system"}]
    messages.extend(dict(item) for item in history)
    messages.append({"role": "user", "content": request.user_content})
    return messages


def test_tokenizer_budget_plan_contains_exact_240_request_positions() -> None:
    plan = subject.build_tokenizer_budget_plan(ROOT)
    assert len(plan.requests) == 240
    assert tuple(item.sequence_index for item in plan.requests) == tuple(range(240))
    assert len({item.request_id for item in plan.requests}) == 240
    assert sum(item.phase is subject.RequestPhase.SCHEMA_CANARY for item in plan.requests) == 2
    assert sum(item.phase is subject.RequestPhase.WARMUP for item in plan.requests) == 2
    assert (
        sum(
            item.phase is subject.RequestPhase.NEUTRAL_WORKER_QUALIFICATION
            for item in plan.requests
        )
        == 20
    )
    assert sum(item.phase is subject.RequestPhase.PILOT for item in plan.requests) == 216
    assert plan.pre_authority_exact_future_prompt_counts_claimed is False
    assert plan.pre_authority_tokenizer_envelope_proof_complete is False
    assert plan.runtime_exact_tokenizer_check_before_every_request is True


def test_pilot_turns_two_through_four_depend_on_admitted_history() -> None:
    plan = subject.build_tokenizer_budget_plan(ROOT)
    pilot = [item for item in plan.requests if item.phase is subject.RequestPhase.PILOT]
    assert len(pilot) == 216
    for item in pilot:
        expected = (
            subject.PromptStateDependency.NONE
            if item.pilot_turn_index == 1
            else subject.PromptStateDependency.PRIOR_ADMITTED_HISTORY
        )
        assert item.prompt_state_dependency is expected


def test_runtime_materialization_remains_non_authorizing() -> None:
    materialization = subject.build_materialization(ROOT)
    contract = materialization.standalone_runtime_contract
    assert contract.maximum_total_model_requests == 240
    assert contract.max_output_tokens == 256
    assert contract.max_model_len == 4096
    assert contract.token_check_precedes_request_send is True
    assert contract.over_budget_request_send_permitted is False
    assert contract.accepted_tokenizer_envelope_proof_complete is False
    assert contract.runtime_executable_generated is False
    assert contract.pilot_execution_authorized is False
    assert contract.new_execution_authorized is False


def test_exact_token_budget_is_checked_before_request_send() -> None:
    history: runtime.JsonHistory = []
    sender_calls = 0

    def token_counter(messages: runtime.MessageList) -> int:
        assert messages
        return 100

    def sender(
        request: runtime.RuntimeTurnRequest,
        messages: runtime.MessageList,
    ) -> object:
        nonlocal sender_calls
        assert request.worker_id == "worker_1"
        assert messages
        sender_calls += 1
        return _valid_response()

    observation = runtime.execute_turn(
        request=runtime.RuntimeTurnRequest(
            request_id="request-1",
            user_content="Question one",
            worker_id="worker_1",
        ),
        history=history,
        admission_spec=_admission_spec(),
        render_messages=_render_messages,
        token_counter=token_counter,
        send_response=sender,
    )
    assert observation.prompt_token_count == 100
    assert sender_calls == 1
    assert len(history) == 2


def test_over_budget_request_is_never_sent_and_history_is_unchanged() -> None:
    history: runtime.JsonHistory = []
    sender_calls = 0

    def token_counter(messages: runtime.MessageList) -> int:
        assert messages
        return 3841

    def sender(
        request: runtime.RuntimeTurnRequest,
        messages: runtime.MessageList,
    ) -> object:
        nonlocal sender_calls
        sender_calls += 1
        return _valid_response()

    with pytest.raises(runtime.StandaloneRuntimeError) as observed:
        runtime.execute_turn(
            request=runtime.RuntimeTurnRequest(
                request_id="request-over-budget",
                user_content="Question",
                worker_id="worker_1",
            ),
            history=history,
            admission_spec=_admission_spec(),
            render_messages=_render_messages,
            token_counter=token_counter,
            send_response=sender,
        )
    assert observed.value.error_code == "V2_RUNTIME_TOKEN_BUDGET_EXCEEDED"
    assert sender_calls == 0
    assert history == []


def test_second_turn_length_failure_stops_trajectory_without_retry() -> None:
    history: runtime.JsonHistory = []
    sender_calls = 0

    def token_counter(messages: runtime.MessageList) -> int:
        assert messages
        return 100

    def sender(
        request: runtime.RuntimeTurnRequest,
        messages: runtime.MessageList,
    ) -> object:
        nonlocal sender_calls
        assert messages
        sender_calls += 1
        if sender_calls == 2:
            return _length_response()
        return _valid_response()

    requests = tuple(
        runtime.RuntimeTurnRequest(
            request_id=f"trajectory-turn-{turn_index}",
            user_content=f"Question {turn_index}",
            worker_id="worker_1",
        )
        for turn_index in range(1, 5)
    )
    typed_requests = cast(
        tuple[
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
            runtime.RuntimeTurnRequest,
        ],
        requests,
    )
    result = runtime.execute_trajectory(
        requests=typed_requests,
        history=history,
        admission_spec=_admission_spec(),
        render_messages=_render_messages,
        token_counter=token_counter,
        send_response=sender,
    )
    assert result.failed is True
    assert result.failure_code == "V2_OUTPUT_TRUNCATED"
    assert result.completed_turn_count == 1
    assert result.request_attempt_count == 2
    assert sender_calls == 2
    assert len(history) == 2
