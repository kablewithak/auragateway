"""Runtime-core contracts for the current-line measured A/B/C variance pilot V1.

This module is inert: it performs no GPU work, model loading, network access, or execution
authorization. It fixes the prompt, route, telemetry-preflight, and evidence-projection semantics
that the later transaction-bound Kaggle executable must implement exactly.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from enum import StrEnum
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import ConditionId, LocalABCContract, WorkerId

EXPECTED_TRAJECTORY_COUNT: Final = 54
EXPECTED_TURN_COUNT: Final = 216
MAXIMUM_REQUEST_ATTEMPTS: Final = 432
TURNS_PER_TRAJECTORY: Final = 4
MAXIMUM_ATTEMPTS_PER_TURN: Final = 2
PRIMARY_OPERATIONAL_TELEMETRY_TURN: Final = 2

TURN_LOCAL_ROUTE_ID: Final = "turn-local-worker1-worker2-v1"
AFFINITY_ROUTE_ID: Final = "affinity-worker1-worker1-v1"

ROUTE_REALIZATION_ID: Final = "four-turn-route-realization-v1"
TELEMETRY_PROJECTION_ID: Final = "turn-two-operational-telemetry-projection-v1"

PROMETHEUS_LINE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?:\{(?P<labels>.*)\})?\s+"
    r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$"
)
PROMETHEUS_LABEL = re.compile(r'(?:^|,)(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)="(?P<value>(?:\\.|[^"])*)"')

KNOWN_CURRENT_CACHE_METRICS: Final = (
    "vllm:prompt_tokens_by_source_total",
    "vllm:prompt_tokens_cached_total",
    "vllm:request_prefill_kv_computed_tokens_sum",
)
TIMING_METRIC_CANDIDATES: Final = {
    "prefill_duration_ms": ("vllm:request_prefill_time_seconds_sum",),
    "time_to_first_token_ms": ("vllm:time_to_first_token_seconds_sum",),
    "end_to_end_latency_ms": ("vllm:e2e_request_latency_seconds_sum",),
}

STATIC_RESPONSE_RULE: Final = (
    "Return exactly one JSON object. Do not use Markdown fences, commentary, "
    "or fields outside the frozen terminal-decision schema."
)
VOLATILE_INSTRUCTION: Final = (
    "Use only the supplied synthetic evidence. Return one terminal-decision JSON "
    "object for the current turn. Clarify rather than guess when evidence is incomplete."
)


class RuntimeContractError(RuntimeError):
    """Fail-closed metadata-safe runtime-contract error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class MetricQualificationState(StrEnum):
    """Current-runtime metric-role qualification state."""

    QUALIFIED = "QUALIFIED"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"


class PromptPlacement(StrEnum):
    """Where stable and volatile prompt material is realized."""

    CACHE_HOSTILE_MIXED_SYSTEM = "CACHE_HOSTILE_MIXED_SYSTEM"
    DETERMINISTIC_STATIC_SYSTEM_VOLATILE_USER = "DETERMINISTIC_STATIC_SYSTEM_VOLATILE_USER"


class TurnRoute(LocalABCContract):
    """One exact intended worker for one four-turn pilot trajectory."""

    turn_index: Literal[1, 2, 3, 4]
    worker_id: WorkerId


class RouteRealization(LocalABCContract):
    """Explicit four-turn realization of the frozen two-worker condition route."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    realization_id: Literal["four-turn-route-realization-v1"] = ROUTE_REALIZATION_ID
    condition_id: ConditionId
    frozen_route_schedule_id: Literal[
        "turn-local-worker1-worker2-v1",
        "affinity-worker1-worker1-v1",
    ]
    turns: tuple[TurnRoute, TurnRoute, TurnRoute, TurnRoute]
    realization_rule: Literal["REPEAT_FROZEN_TWO_WORKER_ROUTE_PAIR_ACROSS_FOUR_TURNS"] = (
        "REPEAT_FROZEN_TWO_WORKER_ROUTE_PAIR_ACROSS_FOUR_TURNS"
    )

    @model_validator(mode="after")
    def validate_realization(self) -> Self:
        if tuple(item.turn_index for item in self.turns) != (1, 2, 3, 4):
            raise ValueError("route realization requires ordered turns 1 through 4")
        expected = {
            ConditionId.A: (
                TURN_LOCAL_ROUTE_ID,
                (
                    WorkerId.WORKER_1,
                    WorkerId.WORKER_2,
                    WorkerId.WORKER_1,
                    WorkerId.WORKER_2,
                ),
            ),
            ConditionId.B: (
                TURN_LOCAL_ROUTE_ID,
                (
                    WorkerId.WORKER_1,
                    WorkerId.WORKER_2,
                    WorkerId.WORKER_1,
                    WorkerId.WORKER_2,
                ),
            ),
            ConditionId.C: (
                AFFINITY_ROUTE_ID,
                (
                    WorkerId.WORKER_1,
                    WorkerId.WORKER_1,
                    WorkerId.WORKER_1,
                    WorkerId.WORKER_1,
                ),
            ),
        }
        expected_id, expected_workers = expected[self.condition_id]
        if self.frozen_route_schedule_id != expected_id:
            raise ValueError("route schedule ID violates the frozen condition")
        if tuple(item.worker_id for item in self.turns) != expected_workers:
            raise ValueError("four-turn worker realization violates the runtime contract")
        return self


class PromptRealization(LocalABCContract):
    """Exact cache-hostile versus deterministic prompt placement semantics."""

    condition_id: ConditionId
    placement: PromptPlacement

    @model_validator(mode="after")
    def validate_placement(self) -> Self:
        expected = (
            PromptPlacement.CACHE_HOSTILE_MIXED_SYSTEM
            if self.condition_id is ConditionId.A
            else PromptPlacement.DETERMINISTIC_STATIC_SYSTEM_VOLATILE_USER
        )
        if self.placement is not expected:
            raise ValueError("prompt placement violates the frozen A/B/C condition")
        return self


class RawMetricSample(LocalABCContract):
    """One relevant Prometheus sample without raw payload retention."""

    name: str
    labels: tuple[tuple[str, str], ...]
    value: float

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: float) -> float:
        if not math.isfinite(value) or value < 0:
            raise ValueError("metric values must be finite and non-negative")
        return value


class MetricRoleQualification(LocalABCContract):
    """One fail-closed timing or cache metric role."""

    role: Literal[
        "prefill_duration_ms",
        "time_to_first_token_ms",
        "end_to_end_latency_ms",
    ]
    state: MetricQualificationState
    metric_name: str | None = None
    unit: Literal["seconds"] = "seconds"

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state is MetricQualificationState.QUALIFIED:
            if self.metric_name is None:
                raise ValueError("qualified metric roles require one metric name")
        elif self.metric_name is not None:
            raise ValueError("unqualified metric roles cannot bind a metric name")
        return self


class TimingTelemetryPreflight(LocalABCContract):
    """Runtime metric discovery result that must pass before pilot requests."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    preflight_id: Literal["variance-pilot-current-timing-telemetry-preflight-v1"]
    prefill_duration: MetricRoleQualification
    time_to_first_token: MetricRoleQualification
    end_to_end_latency: MetricRoleQualification
    all_required_timing_roles_qualified: bool
    pilot_requests_permitted: bool
    missing_metric_becomes_zero: Literal[False] = False
    ambiguous_metric_permitted: Literal[False] = False
    raw_metrics_retained: Literal[False] = False

    @model_validator(mode="after")
    def validate_gate(self) -> Self:
        roles = (
            self.prefill_duration,
            self.time_to_first_token,
            self.end_to_end_latency,
        )
        qualified = all(item.state is MetricQualificationState.QUALIFIED for item in roles)
        if self.all_required_timing_roles_qualified != qualified:
            raise ValueError("timing qualification summary drifted")
        if self.pilot_requests_permitted != qualified:
            raise ValueError("pilot request admission must match timing qualification")
        return self


class TurnTelemetry(LocalABCContract):
    """Metadata-safe telemetry retained for one realized turn."""

    turn_index: Literal[1, 2, 3, 4]
    worker_id: WorkerId
    cached_prefix_tokens: int | None = Field(default=None, ge=0)
    newly_computed_prefill_tokens: int | None = Field(default=None, ge=0)
    prefill_duration_ms: float | None = Field(default=None, ge=0)
    time_to_first_token_ms: float | None = Field(default=None, ge=0)
    end_to_end_latency_ms: float | None = Field(default=None, ge=0)
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False


class TrajectoryOperationalProjection(LocalABCContract):
    """One old-pilot-compatible trajectory projection from turn-two telemetry."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    projection_id: Literal["turn-two-operational-telemetry-projection-v1"] = TELEMETRY_PROJECTION_ID
    run_id: str
    worker_id: WorkerId
    source_turn_index: Literal[2] = PRIMARY_OPERATIONAL_TELEMETRY_TURN
    cached_prefix_tokens: int | None = Field(default=None, ge=0)
    newly_computed_prefill_tokens: int | None = Field(default=None, ge=0)
    prefill_duration_ms: float | None = Field(default=None, ge=0)
    time_to_first_token_ms: float | None = Field(default=None, ge=0)
    end_to_end_latency_ms: float | None = Field(default=None, ge=0)
    cache_consistent: bool | None = None


def canonical_json(payload: object) -> str:
    """Stable JSON used for embedded prompt material and evidence identities."""

    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def route_realization(condition_id: ConditionId) -> RouteRealization:
    """Return the explicit four-turn worker realization for one condition."""

    workers = {
        ConditionId.A: (
            WorkerId.WORKER_1,
            WorkerId.WORKER_2,
            WorkerId.WORKER_1,
            WorkerId.WORKER_2,
        ),
        ConditionId.B: (
            WorkerId.WORKER_1,
            WorkerId.WORKER_2,
            WorkerId.WORKER_1,
            WorkerId.WORKER_2,
        ),
        ConditionId.C: (
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
        ),
    }[condition_id]
    schedule_id = AFFINITY_ROUTE_ID if condition_id is ConditionId.C else TURN_LOCAL_ROUTE_ID
    return RouteRealization(
        condition_id=condition_id,
        frozen_route_schedule_id=schedule_id,
        turns=tuple(
            TurnRoute(turn_index=index, worker_id=worker)
            for index, worker in enumerate(workers, start=1)
        ),
    )


def prompt_realization(condition_id: ConditionId) -> PromptRealization:
    placement = (
        PromptPlacement.CACHE_HOSTILE_MIXED_SYSTEM
        if condition_id is ConditionId.A
        else PromptPlacement.DETERMINISTIC_STATIC_SYSTEM_VOLATILE_USER
    )
    return PromptRealization(condition_id=condition_id, placement=placement)


def build_static_system_prompt(compiler_spec: dict[str, object]) -> str:
    """Reproduce the compact static prompt profile used by prior live execution."""

    required = (
        "serialization_version",
        "template_id",
        "template_version",
        "segments",
        "tools",
        "output_schema",
        "context_pack",
    )
    if any(key not in compiler_spec for key in required):
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_COMPILER_SPEC_INVALID",
            "compiler specification is missing required static prompt fields",
        )
    payload = {
        "runtime_prompt_profile": "development-live-compact-v1",
        "serialization_version": compiler_spec["serialization_version"],
        "template_id": compiler_spec["template_id"],
        "template_version": compiler_spec["template_version"],
        "segments": compiler_spec["segments"],
        "tools": compiler_spec["tools"],
        "output_schema": compiler_spec["output_schema"],
        "context_pack": compiler_spec["context_pack"],
        "response_rule": STATIC_RESPONSE_RULE,
    }
    return canonical_json(payload)


def build_volatile_prompt(
    *,
    episode: dict[str, object],
    turn_index: int,
    source_evidence: tuple[dict[str, str], ...],
    prior_user_messages: tuple[str, ...],
    prior_assistant_outputs: tuple[str, ...],
) -> str:
    """Reproduce the four-turn volatile prompt without leaking it to public evidence."""

    if turn_index not in {1, 2, 3, 4}:
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_TURN_INDEX_INVALID",
            "pilot turn index must be between one and four",
        )
    turns = episode.get("turns")
    if not isinstance(turns, list) or len(turns) != 4:
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_EPISODE_INVALID",
            "pilot episode must contain exactly four turns",
        )
    if len(prior_user_messages) != len(prior_assistant_outputs):
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_HISTORY_INVALID",
            "pilot conversation history is not pairwise aligned",
        )
    raw_turn = turns[turn_index - 1]
    if not isinstance(raw_turn, dict):
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_EPISODE_INVALID",
            "pilot episode turn is invalid",
        )
    user_message = raw_turn.get("user_message")
    if not isinstance(user_message, str) or not user_message.strip():
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_EPISODE_INVALID",
            "pilot episode turn user message is invalid",
        )
    source_scope = episode.get("source_scope")
    if not isinstance(source_scope, dict):
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_EPISODE_INVALID",
            "pilot episode source scope is invalid",
        )
    required_ids = source_scope.get("required_source_ids")
    if not isinstance(required_ids, list) or not all(
        isinstance(item, str) for item in required_ids
    ):
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_EPISODE_INVALID",
            "pilot episode required source IDs are invalid",
        )
    history: list[dict[str, str]] = []
    for prior_user, prior_assistant in zip(
        prior_user_messages,
        prior_assistant_outputs,
        strict=True,
    ):
        history.extend(
            (
                {"role": "user", "content": prior_user},
                {"role": "assistant", "content": prior_assistant},
            )
        )
    payload = {
        "episode_id": episode.get("episode_id"),
        "episode_title": episode.get("title"),
        "turn_index": turn_index,
        "conversation_history": history,
        "current_user_message": user_message,
        "permitted_source_ids": required_ids,
        "retrieval_evidence": list(source_evidence),
        "instruction": VOLATILE_INSTRUCTION,
    }
    return canonical_json(payload)


def realize_prompts(
    *,
    condition_id: ConditionId,
    static_prompt: str,
    volatile_prompt: str,
) -> tuple[str, str]:
    """Return exact system/user placement for one condition."""

    if condition_id is ConditionId.A:
        return (
            static_prompt + volatile_prompt,
            "Return the JSON decision for the current embedded turn.",
        )
    return static_prompt, volatile_prompt


def _parse_labels(payload: str) -> tuple[tuple[str, str], ...]:
    if not payload:
        return ()
    position = 0
    labels: list[tuple[str, str]] = []
    while position < len(payload):
        match = PROMETHEUS_LABEL.match(payload, position)
        if match is None:
            raise RuntimeContractError(
                "VARIANCE_PILOT_RUNTIME_METRIC_LABEL_INVALID",
                "relevant Prometheus labels cannot be parsed losslessly",
            )
        value = match.group("value").replace(r"\\", "\\").replace(r"\"", '"').replace(r"\n", "\n")
        labels.append((match.group("key"), value))
        position = match.end()
    return tuple(sorted(labels))


def parse_relevant_metrics(payload: str) -> tuple[RawMetricSample, ...]:
    """Parse only cache and candidate timing metrics from one metrics payload."""

    names = set(KNOWN_CURRENT_CACHE_METRICS)
    for candidates in TIMING_METRIC_CANDIDATES.values():
        names.update(candidates)
    samples: list[RawMetricSample] = []
    for raw_line in payload.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = PROMETHEUS_LINE.fullmatch(stripped)
        if match is None or match.group("name") not in names:
            continue
        try:
            value = float(match.group("value"))
        except ValueError as error:
            raise RuntimeContractError(
                "VARIANCE_PILOT_RUNTIME_METRIC_VALUE_INVALID",
                "relevant Prometheus metric value is invalid",
            ) from error
        samples.append(
            RawMetricSample(
                name=match.group("name"),
                labels=_parse_labels(match.group("labels") or ""),
                value=value,
            )
        )
    return tuple(samples)


def _qualify_role(
    role: Literal[
        "prefill_duration_ms",
        "time_to_first_token_ms",
        "end_to_end_latency_ms",
    ],
    samples: tuple[RawMetricSample, ...],
) -> MetricRoleQualification:
    candidates = TIMING_METRIC_CANDIDATES[role]
    observed = tuple(name for name in candidates if any(item.name == name for item in samples))
    if len(observed) == 1:
        return MetricRoleQualification(
            role=role,
            state=MetricQualificationState.QUALIFIED,
            metric_name=observed[0],
        )
    state = MetricQualificationState.MISSING if not observed else MetricQualificationState.AMBIGUOUS
    return MetricRoleQualification(role=role, state=state)


def timing_telemetry_preflight(metrics_payload: str) -> TimingTelemetryPreflight:
    """Fail closed when the current runtime cannot expose each timing role uniquely."""

    samples = parse_relevant_metrics(metrics_payload)
    prefill = _qualify_role("prefill_duration_ms", samples)
    ttft = _qualify_role("time_to_first_token_ms", samples)
    e2e = _qualify_role("end_to_end_latency_ms", samples)
    qualified = all(
        item.state is MetricQualificationState.QUALIFIED for item in (prefill, ttft, e2e)
    )
    return TimingTelemetryPreflight(
        preflight_id="variance-pilot-current-timing-telemetry-preflight-v1",
        prefill_duration=prefill,
        time_to_first_token=ttft,
        end_to_end_latency=e2e,
        all_required_timing_roles_qualified=qualified,
        pilot_requests_permitted=qualified,
    )


def project_turn_two_operational_telemetry(
    *,
    run_id: str,
    turns: tuple[TurnTelemetry, TurnTelemetry, TurnTelemetry, TurnTelemetry],
    cache_consistent: bool | None,
) -> TrajectoryOperationalProjection:
    """Project one four-turn trajectory onto the pilot's turn-two operational row."""

    if tuple(item.turn_index for item in turns) != (1, 2, 3, 4):
        raise RuntimeContractError(
            "VARIANCE_PILOT_RUNTIME_TELEMETRY_ORDER_INVALID",
            "trajectory telemetry must contain ordered turns one through four",
        )
    turn = turns[PRIMARY_OPERATIONAL_TELEMETRY_TURN - 1]
    return TrajectoryOperationalProjection(
        run_id=run_id,
        worker_id=turn.worker_id,
        cached_prefix_tokens=turn.cached_prefix_tokens,
        newly_computed_prefill_tokens=turn.newly_computed_prefill_tokens,
        prefill_duration_ms=turn.prefill_duration_ms,
        time_to_first_token_ms=turn.time_to_first_token_ms,
        end_to_end_latency_ms=turn.end_to_end_latency_ms,
        cache_consistent=cache_consistent,
    )
