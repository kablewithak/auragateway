"""Stdlib-only live semantic helpers for variance-pilot successor V2.

This module is intentionally free of repository-package and third-party imports so the
transaction-bound wrapper can bind exact prompt realization and neutral qualification
semantics without relying on the notebook host environment.
"""

from __future__ import annotations

import json
import statistics
from typing import Final, TypeAlias, cast

JsonObject: TypeAlias = dict[str, object]
MessageList: TypeAlias = list[dict[str, str]]
JsonHistory: TypeAlias = list[dict[str, str]]

MAXIMUM_WORKER_MEDIAN_TTFT_RATIO: Final = 1.25
MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO: Final = 1.25
STATIC_RESPONSE_RULE: Final = (
    "Return exactly one JSON object matching the frozen TerminalDecisionOutput contract. "
    "Do not use Markdown fences, commentary, or fields outside the selected decision variant."
)
VOLATILE_INSTRUCTION: Final = (
    "Use only the supplied synthetic evidence. Return one terminal-decision JSON object for the "
    "current turn. Clarify rather than guess when evidence is incomplete."
)
CONDITION_A_USER_PROMPT: Final = "Return the JSON decision for the current embedded turn."
NEUTRAL_SOURCE_ID: Final = "neutral-v2-evidence"
NEUTRAL_SOURCE_TEXT: Final = "Synthetic neutral qualification evidence: status is ready."


class LiveSemanticsRuntimeError(RuntimeError):
    """Metadata-safe live-semantics failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _as_object(value: object, code: str, message: str) -> JsonObject:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise LiveSemanticsRuntimeError(code, message)
    return cast(JsonObject, value)


def _stable_segments(compiler_spec: JsonObject) -> list[JsonObject]:
    raw = compiler_spec.get("segments")
    if not isinstance(raw, list):
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_COMPILER_SPEC_INVALID",
            "compiler segments are invalid",
        )
    expected = ("system-policy-v1", "task-procedure-v1", "citation-rules-v1")
    selected: list[JsonObject] = []
    for segment_id in expected:
        matches = [
            cast(JsonObject, item)
            for item in raw
            if isinstance(item, dict) and item.get("segment_id") == segment_id
        ]
        if len(matches) != 1:
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_PROMPT_COMPILER_SPEC_INVALID",
                "required stable compiler segment is missing or duplicated",
            )
        selected.append(matches[0])
    return selected


def build_static_system_prompt(
    compiler_spec: JsonObject,
    admission_spec: JsonObject,
) -> str:
    """Build the exact V2 static prompt without stale V1 terminal material."""

    required = ("serialization_version", "template_id", "context_pack")
    if any(key not in compiler_spec for key in required):
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_COMPILER_SPEC_INVALID",
            "compiler specification is missing stable prompt inputs",
        )
    if admission_spec.get("semantic_contract") != "TerminalDecisionOutput":
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_ADMISSION_SPEC_INVALID",
            "V2 standalone admission contract is invalid",
        )
    payload = {
        "runtime_prompt_profile": "development-live-compact-v2",
        "serialization_version": compiler_spec["serialization_version"],
        "template_id": compiler_spec["template_id"],
        "template_version": "2.0.0",
        "segments": _stable_segments(compiler_spec),
        "context_pack": compiler_spec["context_pack"],
        "terminal_output_contract": admission_spec,
        "response_rule": STATIC_RESPONSE_RULE,
    }
    return canonical_json(payload)


def build_neutral_messages(phase: str, static_prompt: str) -> MessageList:
    """Render the exact schema-canary, warm-up, or neutral qualification request."""

    if phase not in {"schema_canary", "warmup", "neutral_worker_qualification"}:
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PRETREATMENT_PHASE_INVALID",
            "pre-treatment phase is invalid",
        )
    user_payload = {
        "request_contract_id": "neutral-worker-qualification-request-v1",
        "phase": phase,
        "synthetic_evidence": [{"source_id": NEUTRAL_SOURCE_ID, "document": NEUTRAL_SOURCE_TEXT}],
        "instruction": (
            "Return an answer decision stating the synthetic status, citing neutral-v2-evidence."
        ),
    }
    return [
        {"role": "system", "content": static_prompt},
        {"role": "user", "content": canonical_json(user_payload)},
    ]


def _validate_history(history: JsonHistory, turn_index: int) -> None:
    expected_entries = (turn_index - 1) * 2
    if len(history) != expected_entries:
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_HISTORY_INVALID",
            "pilot history length does not match turn index",
        )
    for index, item in enumerate(history):
        expected_role = "user" if index % 2 == 0 else "assistant"
        if set(item) != {"role", "content"} or item.get("role") != expected_role:
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_PROMPT_HISTORY_INVALID",
                "pilot history role ordering is invalid",
            )
        if not isinstance(item.get("content"), str):
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_PROMPT_HISTORY_INVALID",
                "pilot history content is invalid",
            )


def build_pilot_messages(
    *,
    condition_id: str,
    static_prompt: str,
    episode: JsonObject,
    source_map: dict[str, str],
    turn_index: int,
    history: JsonHistory,
) -> MessageList:
    """Render the exact two-message V2 pilot prompt from admitted semantic history."""

    if condition_id not in {"A", "B", "C"}:
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_CONDITION_INVALID",
            "pilot condition is invalid",
        )
    if turn_index not in {1, 2, 3, 4}:
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_TURN_INVALID",
            "pilot turn index is invalid",
        )
    _validate_history(history, turn_index)
    turns = episode.get("turns")
    scope = episode.get("source_scope")
    if not isinstance(turns, list) or len(turns) != 4 or not isinstance(scope, dict):
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_EPISODE_INVALID",
            "pilot episode shape is invalid",
        )
    raw_turn = turns[turn_index - 1]
    if not isinstance(raw_turn, dict):
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_EPISODE_INVALID",
            "pilot turn shape is invalid",
        )
    user_message = raw_turn.get("user_message")
    raw_ids = scope.get("required_source_ids")
    if not isinstance(user_message, str) or not user_message.strip():
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_EPISODE_INVALID",
            "pilot user message is invalid",
        )
    if not isinstance(raw_ids, list) or any(not isinstance(item, str) for item in raw_ids):
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_PROMPT_EPISODE_INVALID",
            "pilot required source IDs are invalid",
        )
    source_ids = cast(list[str], raw_ids)
    evidence: list[dict[str, str]] = []
    for source_id in source_ids:
        document = source_map.get(source_id)
        if document is None:
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_PROMPT_SOURCE_MISSING",
                "pilot required source is missing",
            )
        evidence.append({"source_id": source_id, "document": document})
    volatile = canonical_json(
        {
            "episode_id": episode.get("episode_id"),
            "episode_title": episode.get("title"),
            "turn_index": turn_index,
            "conversation_history": history,
            "current_user_message": user_message,
            "permitted_source_ids": source_ids,
            "retrieval_evidence": evidence,
            "instruction": VOLATILE_INSTRUCTION,
        }
    )
    if condition_id == "A":
        return [
            {"role": "system", "content": static_prompt + volatile},
            {"role": "user", "content": CONDITION_A_USER_PROMPT},
        ]
    return [
        {"role": "system", "content": static_prompt},
        {"role": "user", "content": volatile},
    ]


def _median_ratio(left: list[float], right: list[float]) -> float | None:
    if not left or not right:
        return None
    left_median = statistics.median(left)
    right_median = statistics.median(right)
    low = min(left_median, right_median)
    high = max(left_median, right_median)
    if low == 0:
        return 1.0 if high == 0 else None
    return high / low


def _measured_plan_identities(plan: JsonObject) -> set[tuple[int, int, str]]:
    if (
        plan.get("pre_treatment_request_count") != 24
        or plan.get("measured_request_count") != 20
        or plan.get("maximum_worker_median_ttft_ratio") != MAXIMUM_WORKER_MEDIAN_TTFT_RATIO
        or plan.get("maximum_worker_median_prefill_ratio") != MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO
        or plan.get("hidden_retries_permitted") is not False
    ):
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_NEUTRAL_PLAN_INVALID",
            "neutral worker qualification plan drifted",
        )
    requests = plan.get("requests")
    if not isinstance(requests, list) or len(requests) != 24:
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_NEUTRAL_PLAN_INVALID",
            "neutral worker qualification request set is invalid",
        )
    identities: set[tuple[int, int, str]] = set()
    for raw in requests:
        row = _as_object(
            raw,
            "V2_LIVE_NEUTRAL_PLAN_INVALID",
            "neutral worker qualification row is invalid",
        )
        if row.get("measured_for_worker_symmetry") is not True:
            continue
        pair_index = row.get("measurement_pair_index")
        pair_order_index = row.get("pair_order_index")
        worker_id = row.get("worker_id")
        if (
            not isinstance(pair_index, int)
            or isinstance(pair_index, bool)
            or not isinstance(pair_order_index, int)
            or isinstance(pair_order_index, bool)
            or worker_id not in {"worker_1", "worker_2"}
        ):
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_NEUTRAL_PLAN_INVALID",
                "measured neutral request identity is invalid",
            )
        identities.add((pair_index, pair_order_index, worker_id))
    if len(identities) != 20:
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_NEUTRAL_PLAN_INVALID",
            "neutral worker qualification requires twenty unique measured identities",
        )
    return identities


def assess_neutral_worker_qualification(
    plan: JsonObject,
    samples: list[JsonObject],
) -> JsonObject:
    """Evaluate the frozen gross worker-asymmetry qualification using safe samples only."""

    expected = _measured_plan_identities(plan)
    observed: set[tuple[int, int, str]] = set()
    normalized: list[JsonObject] = []
    for sample in samples:
        pair_index = sample.get("measurement_pair_index")
        pair_order_index = sample.get("pair_order_index")
        worker_id = sample.get("worker_id")
        admitted = sample.get("admitted")
        telemetry_valid = sample.get("telemetry_valid")
        ttft = sample.get("time_to_first_token_ms")
        prefill = sample.get("prefill_duration_ms")
        if (
            not isinstance(pair_index, int)
            or isinstance(pair_index, bool)
            or not isinstance(pair_order_index, int)
            or isinstance(pair_order_index, bool)
            or worker_id not in {"worker_1", "worker_2"}
            or not isinstance(admitted, bool)
            or not isinstance(telemetry_valid, bool)
        ):
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_NEUTRAL_SAMPLE_INVALID",
                "neutral worker sample identity or state is invalid",
            )
        if ttft is not None and (
            not isinstance(ttft, (int, float)) or isinstance(ttft, bool) or ttft < 0
        ):
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_NEUTRAL_SAMPLE_INVALID",
                "neutral TTFT sample is invalid",
            )
        if prefill is not None and (
            not isinstance(prefill, (int, float)) or isinstance(prefill, bool) or prefill < 0
        ):
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_NEUTRAL_SAMPLE_INVALID",
                "neutral prefill sample is invalid",
            )
        identity = (pair_index, pair_order_index, worker_id)
        if identity in observed:
            raise LiveSemanticsRuntimeError(
                "V2_LIVE_NEUTRAL_SAMPLE_DUPLICATE",
                "neutral worker evidence contains duplicate sample identities",
            )
        observed.add(identity)
        normalized.append(sample)
    if observed - expected:
        raise LiveSemanticsRuntimeError(
            "V2_LIVE_NEUTRAL_SAMPLE_UNEXPECTED",
            "neutral worker evidence contains unexpected sample identities",
        )

    blocking: list[str] = []
    if observed != expected:
        blocking.append("NEUTRAL_SAMPLE_SET_INCOMPLETE")
    if any(item.get("admitted") is not True for item in normalized):
        blocking.append("NEUTRAL_OUTPUT_ADMISSION_FAILED")
    if any(item.get("telemetry_valid") is not True for item in normalized):
        blocking.append("NEUTRAL_TELEMETRY_INVALID")

    usable = [
        item
        for item in normalized
        if item.get("admitted") is True
        and item.get("telemetry_valid") is True
        and item.get("time_to_first_token_ms") is not None
        and item.get("prefill_duration_ms") is not None
    ]
    worker_1 = [item for item in usable if item.get("worker_id") == "worker_1"]
    worker_2 = [item for item in usable if item.get("worker_id") == "worker_2"]
    ttft_ratio = _median_ratio(
        [float(cast(float, item["time_to_first_token_ms"])) for item in worker_1],
        [float(cast(float, item["time_to_first_token_ms"])) for item in worker_2],
    )
    prefill_ratio = _median_ratio(
        [float(cast(float, item["prefill_duration_ms"])) for item in worker_1],
        [float(cast(float, item["prefill_duration_ms"])) for item in worker_2],
    )
    if ttft_ratio is None:
        blocking.append("NEUTRAL_TTFT_RATIO_UNAVAILABLE")
    elif ttft_ratio > MAXIMUM_WORKER_MEDIAN_TTFT_RATIO:
        blocking.append("NEUTRAL_TTFT_ASYMMETRY_EXCEEDED")
    if prefill_ratio is None:
        blocking.append("NEUTRAL_PREFILL_RATIO_UNAVAILABLE")
    elif prefill_ratio > MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO:
        blocking.append("NEUTRAL_PREFILL_ASYMMETRY_EXCEEDED")

    blocking = sorted(set(blocking))
    return {
        "schema_version": "1.0.0",
        "decision": "PASS" if not blocking else "FAIL",
        "observed_sample_count": len(samples),
        "worker_1_sample_count": sum(item.get("worker_id") == "worker_1" for item in samples),
        "worker_2_sample_count": sum(item.get("worker_id") == "worker_2" for item in samples),
        "worker_median_ttft_ratio": ttft_ratio,
        "worker_median_prefill_ratio": prefill_ratio,
        "blocking_reasons": blocking,
    }
