from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_bound_runtime_v1 as runtime,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _episode(episode_id: str) -> dict[str, Any]:
    return {
        "episode_id": episode_id,
        "evaluation_split": "development",
        "title": episode_id,
        "source_scope": {"required_source_ids": ["source-1"]},
        "turns": [{"user_message": f"{episode_id}-turn-{index}"} for index in range(1, 5)],
    }


def _schedule() -> dict[str, Any]:
    case_ids = [
        "ep-func-003",
        "ep-func-004",
        "ep-func-007",
        "ep-func-008",
        "ep-func-009",
        "ep-func-011",
    ]
    trajectories: list[dict[str, Any]] = []
    condition_orders = (
        ("A", "B", "C"),
        ("B", "C", "A"),
        ("C", "A", "B"),
    )
    index = 0
    for pair_index in range(18):
        episode_id = case_ids[pair_index % len(case_ids)]
        replication_index = pair_index // 6
        orientation_one = pair_index % 2 == 0
        alternating = (
            ["worker_1", "worker_2", "worker_1", "worker_2"]
            if orientation_one
            else ["worker_2", "worker_1", "worker_2", "worker_1"]
        )
        sticky = [alternating[0]] * 4
        for condition_index, condition_id in enumerate(condition_orders[replication_index]):
            trajectories.append(
                {
                    "schema_version": "2.0.0",
                    "schedule_index": index,
                    "comparison_pair_index": pair_index,
                    "comparison_pair_id": f"pair-{pair_index:02d}",
                    "condition_order_index": condition_index,
                    "condition_id": condition_id,
                    "episode_id": episode_id,
                    "pilot_replication_id": f"r{replication_index + 1}",
                    "worker_orientation": ("orientation_1" if orientation_one else "orientation_2"),
                    "run_id": f"run-{index:03d}",
                    "cache_namespace_id": f"namespace-{index:03d}",
                    "turn_count": 4,
                    "maximum_request_attempt_count": 4,
                    "realized_route": alternating if condition_id != "C" else sticky,
                }
            )
            index += 1
    return {
        "schema_version": "2.0.0",
        "case_count": 6,
        "cases": [{"episode_id": item, "schema_version": "2.0.0"} for item in case_ids],
        "trajectory_count": 54,
        "comparison_pair_count": 18,
        "pilot_turn_count": 216,
        "hidden_retries_permitted": False,
        "replacement_cases_permitted": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "trajectories": trajectories,
    }


def _neutral_plan() -> dict[str, Any]:
    requests: list[dict[str, Any]] = [
        {
            "sequence_index": 0,
            "request_id": "canary-w1",
            "worker_id": "worker_1",
            "phase": "schema_canary",
            "cache_namespace_id": "canary-w1",
            "max_output_tokens": 256,
            "measured_for_worker_symmetry": False,
        },
        {
            "sequence_index": 1,
            "request_id": "canary-w2",
            "worker_id": "worker_2",
            "phase": "schema_canary",
            "cache_namespace_id": "canary-w2",
            "max_output_tokens": 256,
            "measured_for_worker_symmetry": False,
        },
        {
            "sequence_index": 2,
            "request_id": "warmup-w2",
            "worker_id": "worker_2",
            "phase": "warmup",
            "cache_namespace_id": "warmup-w2",
            "max_output_tokens": 256,
            "measured_for_worker_symmetry": False,
        },
        {
            "sequence_index": 3,
            "request_id": "warmup-w1",
            "worker_id": "worker_1",
            "phase": "warmup",
            "cache_namespace_id": "warmup-w1",
            "max_output_tokens": 256,
            "measured_for_worker_symmetry": False,
        },
    ]
    sequence = 4
    for pair_index in range(1, 11):
        first = "worker_1" if pair_index % 2 else "worker_2"
        second = "worker_2" if first == "worker_1" else "worker_1"
        for order_index, worker_id in enumerate((first, second)):
            requests.append(
                {
                    "sequence_index": sequence,
                    "request_id": f"neutral-{pair_index}-{order_index}",
                    "worker_id": worker_id,
                    "phase": "neutral_worker_qualification",
                    "cache_namespace_id": f"neutral-{pair_index}-{order_index}",
                    "max_output_tokens": 256,
                    "measured_for_worker_symmetry": True,
                    "measurement_pair_index": pair_index,
                    "pair_order_index": order_index,
                }
            )
            sequence += 1
    return {
        "schema_version": "2.0.0",
        "schema_canary_request_count": 2,
        "warmup_request_count": 2,
        "measured_request_count": 20,
        "pre_treatment_request_count": 24,
        "hidden_retries_permitted": False,
        "pilot_execution_authorized": False,
        "maximum_worker_median_ttft_ratio": 1.25,
        "maximum_worker_median_prefill_ratio": 1.25,
        "requests": requests,
    }


def _material() -> dict[str, Any]:
    source_text = "synthetic source"
    schedule = _schedule()
    case_ids = [item["episode_id"] for item in schedule["cases"]]
    return {
        "pilot_schedule": schedule,
        "neutral_worker_qualification_plan": _neutral_plan(),
        "generation_contract": {
            "max_tokens": 256,
            "hidden_retries_permitted": False,
        },
        "strict_response_format": {"type": "json_schema"},
        "standalone_admission_spec": {"semantic_contract": "TerminalDecisionOutput"},
        "compiler_spec": {"segments": []},
        "episodes": [_episode(str(item)) for item in case_ids],
        "sources": {
            "source-1": {
                "text": source_text,
                "sha256": _sha(source_text),
                "byte_count": len(source_text.encode("utf-8")),
            }
        },
    }


class _Process:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode


class _Worker:
    def __init__(self, worker_id: str, gpu_index: int, port: int, pid: int) -> None:
        self.worker_id = worker_id
        self.gpu_index = gpu_index
        self.port = port
        self.generation = 1
        self.process_start_ticks = pid * 10
        self.process = _Process(pid)

    def metric_snapshot(self) -> object:
        return object()


class _Budget:
    def __init__(self) -> None:
        self.attempted_model_requests = 0


class _Adapter:
    def __init__(
        self,
        responses: list[dict[str, Any]] | None = None,
        request_counts: dict[str, int] | None = None,
    ) -> None:
        self.budget = _Budget()
        self.calls: list[dict[str, Any]] = []
        self.responses = list(responses or [])
        self.request_counts = request_counts

    def send(
        self,
        *,
        request_id: str,
        url: str,
        messages: list[dict[str, str]],
        cache_salt: str,
    ) -> tuple[dict[str, Any], object]:
        self.budget.attempted_model_requests += 1
        if self.request_counts is not None:
            self.request_counts["http_completed"] += 1
        self.calls.append(
            {
                "request_id": request_id,
                "url": url,
                "messages": messages,
                "cache_salt": cache_salt,
            }
        )
        response: dict[str, Any] = (
            self.responses.pop(0)
            if self.responses
            else {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"decision":"answer"}'},
                    }
                ]
            }
        )
        content = response["choices"][0]["message"]["content"]
        receipt = SimpleNamespace(
            attempt_sequence=self.budget.attempted_model_requests,
            messages_sha256=_sha(runtime.canonical_json(messages)),
            rendered_prompt_sha256=_sha("rendered" + request_id),
            prompt_token_count=100,
            server_usage_prompt_tokens=100,
            finish_reason=response["choices"][0]["finish_reason"],
            output_sha256=_sha(str(content)),
        )
        return response, receipt


class _Tokenizer:
    def count(self, messages: list[dict[str, str]]) -> int:
        assert messages
        return 100


class _AdmissionFailure(RuntimeError):
    pass


class _Admitted:
    def __init__(self, canonical_json: str) -> None:
        self.canonical_json = canonical_json


def _admission_namespace() -> dict[str, Any]:
    def admit_response(response: object, spec: object) -> _Admitted:
        del spec
        if not isinstance(response, dict):
            raise AssertionError("synthetic admission response must be an object")
        content = response["choices"][0]["message"]["content"]
        if content == "INVALID":
            raise _AdmissionFailure("invalid")
        return _Admitted(str(content))

    return {
        "admit_response": admit_response,
        "RuntimeOutputAdmissionError": _AdmissionFailure,
    }


def _r2_namespace() -> dict[str, Any]:
    timing_values = iter(
        [
            "\n".join(
                (
                    "vllm:request_prefill_time_seconds_sum 0",
                    "vllm:time_to_first_token_seconds_sum 0",
                    "vllm:e2e_request_latency_seconds_sum 0",
                )
            ),
            "\n".join(
                (
                    "vllm:request_prefill_time_seconds_sum 0.01",
                    "vllm:time_to_first_token_seconds_sum 0.02",
                    "vllm:e2e_request_latency_seconds_sum 0.03",
                )
            ),
        ]
        * 16
    )

    def get_text(url: str) -> str:
        assert url.endswith("/metrics")
        return next(timing_values)

    def metric_delta(before: object, after: object) -> object:
        del before, after
        return SimpleNamespace(
            local_cache_hit=0.0,
            newly_computed_prefill_tokens=100.0,
            external_kv_transfer=0.0,
        )

    return {"get_text": get_text, "metric_delta": metric_delta}


def _live_namespace() -> dict[str, Any]:
    def build_pilot_messages(**kwargs: object) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": str(kwargs["condition_id"])},
            {"role": "user", "content": str(kwargs["turn_index"])},
        ]

    return {"build_pilot_messages": build_pilot_messages}


@dataclass(frozen=True)
class _RuntimeTurnRequest:
    request_id: str
    user_content: str
    worker_id: str


def _workers() -> dict[str, _Worker]:
    return {
        "worker_1": _Worker("worker_1", 0, 8001, 101),
        "worker_2": _Worker("worker_2", 1, 8002, 202),
    }


def test_validate_material_accepts_frozen_v2_shape_and_rejects_bad_realized_route() -> None:
    material = _material()
    validated = runtime.validate_material(material)
    validated_trajectories = validated.get("trajectories")
    assert isinstance(validated_trajectories, list)
    assert len(validated_trajectories) == 54
    material["pilot_schedule"]["trajectories"][0]["realized_route"] = ["worker_1"]
    with pytest.raises(runtime.V2TransactionRuntimeError) as exc:
        runtime.validate_material(material)
    assert exc.value.error_code == "V2_PILOT_REALIZED_ROUTE_INVALID"


def test_validate_material_accepts_frozen_replication_condition_rotation() -> None:
    schedule = _schedule()
    trajectories = schedule["trajectories"]
    assert [item["condition_id"] for item in trajectories[0:3]] == ["A", "B", "C"]
    assert [item["condition_id"] for item in trajectories[18:21]] == ["B", "C", "A"]
    assert [item["condition_id"] for item in trajectories[36:39]] == ["C", "A", "B"]
    runtime.validate_material(_material())


def test_neutral_plan_requires_frozen_canary_and_warmup_order() -> None:
    material = _material()
    plan = material["neutral_worker_qualification_plan"]
    plan["requests"][2]["worker_id"] = "worker_1"
    with pytest.raises(runtime.V2TransactionRuntimeError) as exc:
        runtime.validate_material(material)
    assert exc.value.error_code == "V2_PRETREATMENT_ORDER_DRIFT"


def test_run_trajectory_uses_realized_route_without_condition_reconstruction() -> None:
    workers = _workers()
    frozen = runtime._freeze_worker_identities(workers)
    request_counts = {"http_completed": 0, "admitted": 0, "committed": 0}
    adapter = _Adapter(request_counts=request_counts)

    def execute_trajectory(**kwargs: Any) -> object:
        requests = kwargs["requests"]
        history = kwargs["history"]
        for request in requests:
            messages = kwargs["render_messages"](request, history)
            kwargs["token_counter"](messages)
            response = kwargs["send_response"](request, messages)
            content = response["choices"][0]["message"]["content"]
            history.extend(
                [
                    {"role": "user", "content": request.user_content},
                    {"role": "assistant", "content": content},
                ]
            )
        return SimpleNamespace(
            request_attempt_count=4,
            completed_turn_count=4,
            failed=False,
            failure_code=None,
        )

    trajectory = _schedule()["trajectories"][3]
    assert trajectory["condition_id"] == "A"
    assert trajectory["realized_route"][0] == "worker_2"
    result = runtime._run_trajectory(
        r2=_r2_namespace(),
        live=_live_namespace(),
        standalone={
            "RuntimeTurnRequest": _RuntimeTurnRequest,
            "execute_trajectory": execute_trajectory,
        },
        admission=_admission_namespace(),
        trajectory=trajectory,
        episode=_episode(str(trajectory["episode_id"])),
        source_map={"source-1": "synthetic source"},
        static_prompt="static",
        admission_spec={"semantic_contract": "TerminalDecisionOutput"},
        workers=workers,
        frozen_workers=frozen,
        tokenizer=_Tokenizer(),
        adapter=adapter,
        request_counts=request_counts,
    )
    assert [call["url"] for call in adapter.calls] == [
        "http://127.0.0.1:8002/v1/chat/completions",
        "http://127.0.0.1:8001/v1/chat/completions",
        "http://127.0.0.1:8002/v1/chat/completions",
        "http://127.0.0.1:8001/v1/chat/completions",
    ]
    assert len({str(call["cache_salt"]) for call in adapter.calls}) == 1
    assert result["realized_route"] == trajectory["realized_route"]


def test_trajectory_failure_on_turn_two_records_no_later_requests() -> None:
    workers = _workers()
    frozen = runtime._freeze_worker_identities(workers)
    request_counts = {"http_completed": 0, "admitted": 0, "committed": 0}
    adapter = _Adapter(
        responses=[
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"decision":"answer"}'},
                    }
                ]
            },
            {"choices": [{"finish_reason": "stop", "message": {"content": "INVALID"}}]},
        ],
        request_counts=request_counts,
    )

    def execute_trajectory(**kwargs: Any) -> object:
        requests = kwargs["requests"]
        history = kwargs["history"]
        first = requests[0]
        first_messages = kwargs["render_messages"](first, history)
        kwargs["token_counter"](first_messages)
        first_response = kwargs["send_response"](first, first_messages)
        history.extend(
            [
                {"role": "user", "content": first.user_content},
                {
                    "role": "assistant",
                    "content": first_response["choices"][0]["message"]["content"],
                },
            ]
        )
        second = requests[1]
        second_messages = kwargs["render_messages"](second, history)
        kwargs["token_counter"](second_messages)
        kwargs["send_response"](second, second_messages)
        return SimpleNamespace(
            request_attempt_count=2,
            completed_turn_count=1,
            failed=True,
            failure_code="V2_OUTPUT_JSON_INVALID",
        )

    trajectory = _schedule()["trajectories"][0]
    result = runtime._run_trajectory(
        r2=_r2_namespace(),
        live=_live_namespace(),
        standalone={
            "RuntimeTurnRequest": _RuntimeTurnRequest,
            "execute_trajectory": execute_trajectory,
        },
        admission=_admission_namespace(),
        trajectory=trajectory,
        episode=_episode(str(trajectory["episode_id"])),
        source_map={"source-1": "synthetic source"},
        static_prompt="static",
        admission_spec={"semantic_contract": "TerminalDecisionOutput"},
        workers=workers,
        frozen_workers=frozen,
        tokenizer=_Tokenizer(),
        adapter=adapter,
        request_counts=request_counts,
    )
    assert len(adapter.calls) == 2
    assert result["attempted_request_count"] == 2
    assert result["admitted_request_count"] == 1
    assert result["committed_turn_count"] == 1
    assert result["failure_code"] == "V2_OUTPUT_JSON_INVALID"


def test_fatal_after_one_committed_turn_preserves_partial_counters() -> None:
    workers = _workers()
    frozen = runtime._freeze_worker_identities(workers)
    request_counts = {"http_completed": 0, "admitted": 0, "committed": 0}
    adapter = _Adapter(request_counts=request_counts)

    def execute_trajectory(**kwargs: Any) -> object:
        requests = kwargs["requests"]
        history = kwargs["history"]
        first = requests[0]
        messages = kwargs["render_messages"](first, history)
        kwargs["token_counter"](messages)
        response = kwargs["send_response"](first, messages)
        history.extend(
            [
                {"role": "user", "content": first.user_content},
                {
                    "role": "assistant",
                    "content": response["choices"][0]["message"]["content"],
                },
            ]
        )
        raise RuntimeError("synthetic fatal infrastructure failure")

    trajectory = _schedule()["trajectories"][0]
    with pytest.raises(RuntimeError, match="synthetic fatal infrastructure failure"):
        runtime._run_trajectory(
            r2=_r2_namespace(),
            live=_live_namespace(),
            standalone={
                "RuntimeTurnRequest": _RuntimeTurnRequest,
                "execute_trajectory": execute_trajectory,
            },
            admission=_admission_namespace(),
            trajectory=trajectory,
            episode=_episode(str(trajectory["episode_id"])),
            source_map={"source-1": "synthetic source"},
            static_prompt="static",
            admission_spec={"semantic_contract": "TerminalDecisionOutput"},
            workers=workers,
            frozen_workers=frozen,
            tokenizer=_Tokenizer(),
            adapter=adapter,
            request_counts=request_counts,
        )

    assert len(adapter.calls) == 1
    assert request_counts == {"http_completed": 1, "admitted": 1, "committed": 1}


def test_reconciliation_explains_skipped_and_admission_gaps() -> None:
    pretreatment: list[dict[str, object]] = [{"committed": True} for _ in range(24)]
    trajectories: list[dict[str, Any]] = []
    for index in range(54):
        if index == 0:
            trajectories.append(
                {
                    "scheduled_turn_count": 4,
                    "attempted_request_count": 2,
                    "http_completed_request_count": 2,
                    "admitted_request_count": 1,
                    "committed_turn_count": 1,
                    "failure_code": "V2_OUTPUT_JSON_INVALID",
                }
            )
            continue
        trajectories.append(
            {
                "scheduled_turn_count": 4,
                "attempted_request_count": 4,
                "http_completed_request_count": 4,
                "admitted_request_count": 4,
                "committed_turn_count": 4,
                "failure_code": None,
            }
        )
    reconciliation = runtime.reconcile_requests(
        adapter_attempted=238,
        pretreatment_ledger=pretreatment,
        trajectories=trajectories,
    )
    assert reconciliation["scheduled_request_count"] == 240
    assert reconciliation["attempted_request_count"] == 238
    assert reconciliation["http_completed_minus_admitted"] == 1
    assert reconciliation["admitted_minus_committed"] == 0
    assert reconciliation["skipped_later_turns_by_failure_code"] == {"V2_OUTPUT_JSON_INVALID": 2}


def test_counted_transport_records_http_completion_before_response_validation() -> None:
    request_counts = {"http_completed": 0, "admitted": 0, "committed": 0}

    def post_json(url: str, payload: dict[str, object]) -> object:
        del url, payload
        return []

    counted = runtime._counted_post_json(
        {"post_json": post_json},
        request_counts,
    )
    with pytest.raises(runtime.V2TransactionRuntimeError) as exc:
        counted("http://127.0.0.1:8001/v1/chat/completions", {})
    assert exc.value.error_code == "V2_RESPONSE_ENVELOPE_INVALID"
    assert request_counts["http_completed"] == 1


def test_checkpoint_counter_invariant_fails_closed() -> None:
    with pytest.raises(runtime.V2TransactionRuntimeError) as exc:
        runtime._checkpoint_payload(
            transaction_id="a" * 64,
            phase="INVALID",
            scheduled=10,
            attempted=9,
            http_completed=8,
            admitted=7,
            committed=8,
        )
    assert exc.value.error_code == "V2_REQUEST_RECONCILIATION_INVALID"


def test_worker_identity_drift_is_fatal() -> None:
    workers = _workers()
    frozen = runtime._freeze_worker_identities(workers)
    workers["worker_2"].generation = 2
    with pytest.raises(runtime.V2TransactionRuntimeError) as exc:
        runtime._assert_workers_frozen(workers, frozen)
    assert exc.value.error_code in {
        "V2_WORKER_BINDING_DRIFT",
        "V2_WORKER_GENERATION_DRIFT",
    }


def test_source_keeps_v1_semantics_prohibited_and_v2_budget_frozen() -> None:
    source_path = Path(runtime.__file__)
    source = source_path.read_text(encoding="utf-8")
    assert "def _route(" not in source
    assert "MAXIMUM_TOTAL_MODEL_REQUESTS: Final = 437" not in source
    assert "MAX_OUTPUT_TOKENS: Final = 64" not in source
    assert "_cache_salt_isolation_preflight" not in source
    assert "_preflight_probe" not in source
    assert "EXPECTED_TOTAL_SCHEDULED_REQUESTS: Final = 240" in source
    assert "MAX_OUTPUT_TOKENS: Final = 256" in source
    assert 'trajectory.get("realized_route")' in source


def test_required_checkpoint_families_are_present() -> None:
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    for marker in (
        '"schema_canary"',
        '"neutral_qualification"',
        'f"comparison_pair_{pair_index + 1:02d}"',
        '"primary_failure"',
        '"teardown"',
    ):
        assert marker in source
