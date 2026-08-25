"""Injected stdlib-only executable rehearsal payload for variance-pilot successor V2."""

from __future__ import annotations

import json
import sys

_runtime_candidate = globals().get("AURAGATEWAY_V2_STANDALONE_RUNTIME")
_admission_spec_candidate = globals().get("AURAGATEWAY_V2_ADMISSION_SPEC")
_runtime_module_name_candidate = globals().get("AURAGATEWAY_V2_RUNTIME_MODULE_NAME")

if not isinstance(_runtime_candidate, dict):
    raise RuntimeError("standalone runtime injection is missing")
if not isinstance(_admission_spec_candidate, dict):
    raise RuntimeError("admission-spec injection is missing")
if not isinstance(_runtime_module_name_candidate, str) or not _runtime_module_name_candidate:
    raise RuntimeError("runtime module identity injection is missing")

_RUNTIME: dict[str, object] = _runtime_candidate
_ADMISSION_SPEC: dict[str, object] = _admission_spec_candidate
_RUNTIME_MODULE_NAME: str = _runtime_module_name_candidate


def _valid_response() -> dict[str, object]:
    content = json.dumps(
        {
            "decision": "answer",
            "reason_code": "evidence_sufficient",
            "response": "Rehearsal-supported answer.",
            "citation_ids": ["source-1"],
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": content},
            }
        ]
    }


def main() -> int:
    runtime_turn_request = _RUNTIME.get("RuntimeTurnRequest")
    execute_trajectory = _RUNTIME.get("execute_trajectory")
    if not callable(runtime_turn_request) or not callable(execute_trajectory):
        raise RuntimeError("standalone runtime injection is incomplete")

    history: list[dict[str, str]] = []
    token_counter_calls = 0
    fake_worker_calls = 0

    def render_messages(
        request: object,
        current_history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        user_content = getattr(request, "user_content", None)
        if not isinstance(user_content, str) or not user_content:
            raise RuntimeError("rehearsal request user content is invalid")
        messages = [{"role": "system", "content": "rehearsal-system"}]
        messages.extend(dict(item) for item in current_history)
        messages.append({"role": "user", "content": user_content})
        return messages

    def token_counter(messages: list[dict[str, str]]) -> int:
        nonlocal token_counter_calls
        if not messages:
            raise RuntimeError("rehearsal tokenizer received no messages")
        token_counter_calls += 1
        return 100

    def fake_worker(request: object, messages: list[dict[str, str]]) -> object:
        nonlocal fake_worker_calls
        worker_id = getattr(request, "worker_id", None)
        if worker_id != "worker_1" or not messages:
            raise RuntimeError("rehearsal fake-worker request is invalid")
        fake_worker_calls += 1
        return _valid_response()

    requests = tuple(
        runtime_turn_request(
            request_id=f"rehearsal-turn-{turn_index}",
            user_content=f"Rehearsal question {turn_index}",
            worker_id="worker_1",
        )
        for turn_index in range(1, 5)
    )
    if len(requests) != 4:
        raise RuntimeError("rehearsal request construction drifted")

    result = execute_trajectory(
        requests=requests,
        history=history,
        admission_spec=_ADMISSION_SPEC,
        render_messages=render_messages,
        token_counter=token_counter,
        send_response=fake_worker,
    )
    if getattr(result, "failed", True):
        raise RuntimeError("standalone runtime rehearsal unexpectedly failed")
    if getattr(result, "completed_turn_count", None) != 4:
        raise RuntimeError("standalone runtime rehearsal turn count drifted")
    if getattr(result, "request_attempt_count", None) != 4:
        raise RuntimeError("standalone runtime rehearsal attempt count drifted")
    if len(history) != 8:
        raise RuntimeError("standalone runtime rehearsal history mutation drifted")
    if token_counter_calls != 4 or fake_worker_calls != 4:
        raise RuntimeError("standalone runtime rehearsal call counts drifted")

    globals()["AURAGATEWAY_V2_REHEARSAL_RESULT"] = {
        "runtime_module_registered_during_execution": _RUNTIME_MODULE_NAME in sys.modules,
        "runtime_injection_used": True,
        "fake_worker_request_count": fake_worker_calls,
        "token_budget_check_count": token_counter_calls,
        "completed_turn_count": 4,
        "request_attempt_count": 4,
        "history_entry_count": len(history),
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
    }
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
