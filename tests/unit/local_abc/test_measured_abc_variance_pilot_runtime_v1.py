from __future__ import annotations

from auragateway.local_abc import measured_abc_variance_pilot_runtime_v1 as subject
from auragateway.local_abc.contracts import ConditionId, WorkerId


def test_four_turn_route_realization_is_explicit() -> None:
    a = subject.route_realization(ConditionId.A)
    b = subject.route_realization(ConditionId.B)
    c = subject.route_realization(ConditionId.C)

    assert tuple(item.worker_id for item in a.turns) == (
        WorkerId.WORKER_1,
        WorkerId.WORKER_2,
        WorkerId.WORKER_1,
        WorkerId.WORKER_2,
    )
    assert a.turns == b.turns
    assert tuple(item.worker_id for item in c.turns) == (
        WorkerId.WORKER_1,
        WorkerId.WORKER_1,
        WorkerId.WORKER_1,
        WorkerId.WORKER_1,
    )


def test_prompt_placement_preserves_a_vs_b_and_b_vs_c() -> None:
    a = subject.realize_prompts(
        condition_id=ConditionId.A,
        static_prompt="STATIC",
        volatile_prompt="VOLATILE",
    )
    b = subject.realize_prompts(
        condition_id=ConditionId.B,
        static_prompt="STATIC",
        volatile_prompt="VOLATILE",
    )
    c = subject.realize_prompts(
        condition_id=ConditionId.C,
        static_prompt="STATIC",
        volatile_prompt="VOLATILE",
    )

    assert a == (
        "STATICVOLATILE",
        "Return the JSON decision for the current embedded turn.",
    )
    assert b == ("STATIC", "VOLATILE")
    assert c == b


def test_compact_prompt_serializer_does_not_add_newlines() -> None:
    spec: dict[str, object] = {
        "serialization_version": "v1",
        "template_id": "template",
        "template_version": "1",
        "segments": [],
        "tools": [],
        "output_schema": {},
        "context_pack": {},
    }
    rendered = subject.build_static_system_prompt(spec)
    assert not rendered.endswith("\n")


def test_timing_preflight_fails_closed_when_metrics_are_missing() -> None:
    preflight = subject.timing_telemetry_preflight("vllm:prompt_tokens_cached_total 10\n")
    assert preflight.all_required_timing_roles_qualified is False
    assert preflight.pilot_requests_permitted is False


def test_timing_preflight_qualifies_exact_current_candidates() -> None:
    payload = "\n".join(
        (
            "vllm:request_prefill_time_seconds_sum 1.0",
            "vllm:time_to_first_token_seconds_sum 2.0",
            "vllm:e2e_request_latency_seconds_sum 3.0",
        )
    )
    preflight = subject.timing_telemetry_preflight(payload)
    assert preflight.all_required_timing_roles_qualified is True
    assert preflight.pilot_requests_permitted is True


def test_turn_two_projection_uses_realized_turn_two_worker() -> None:
    turns = (
        subject.TurnTelemetry(turn_index=1, worker_id=WorkerId.WORKER_1),
        subject.TurnTelemetry(
            turn_index=2,
            worker_id=WorkerId.WORKER_2,
            cached_prefix_tokens=16,
            newly_computed_prefill_tokens=32,
            prefill_duration_ms=12.0,
            time_to_first_token_ms=20.0,
            end_to_end_latency_ms=50.0,
        ),
        subject.TurnTelemetry(turn_index=3, worker_id=WorkerId.WORKER_1),
        subject.TurnTelemetry(turn_index=4, worker_id=WorkerId.WORKER_2),
    )
    projection = subject.project_turn_two_operational_telemetry(
        run_id="pilot-run-example",
        turns=turns,
        cache_consistent=True,
    )
    assert projection.source_turn_index == 2
    assert projection.worker_id is WorkerId.WORKER_2
    assert projection.cached_prefix_tokens == 16
    assert projection.cache_consistent is True
