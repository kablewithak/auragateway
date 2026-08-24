"""Standalone transaction-bound runtime for the AuraGateway variance pilot V1.

The generated wrapper injects:
- AURAGATEWAY_R2_RUNTIME: the exact accepted current-runtime P5/P6 runtime library namespace;
- AURAGATEWAY_PILOT_MATERIAL: six development episodes plus frozen synthetic source material;
- AURAGATEWAY_TRANSACTION_ID: the single-use transaction identity;
- EXECUTED_RUNTIME_SCRIPT_SHA256: this runtime payload identity.

No external network access, credentials, customer data, raw prompt logging, or raw output
publication is permitted.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import zipfile
from pathlib import Path
from typing import Any, Final, cast

_RAW_R2_RUNTIME = globals().get("AURAGATEWAY_R2_RUNTIME")
_RAW_PILOT_MATERIAL = globals().get("AURAGATEWAY_PILOT_MATERIAL")
_RAW_TRANSACTION_ID = globals().get("AURAGATEWAY_TRANSACTION_ID")
_RAW_RUNTIME_SHA256 = globals().get("EXECUTED_RUNTIME_SCRIPT_SHA256")

if not isinstance(_RAW_R2_RUNTIME, dict):
    raise RuntimeError("transaction-bound R2 runtime injection is missing")
if not isinstance(_RAW_PILOT_MATERIAL, dict):
    raise RuntimeError("transaction-bound pilot material injection is missing")
if not isinstance(_RAW_TRANSACTION_ID, str):
    raise RuntimeError("transaction-bound transaction identity is missing")
if not isinstance(_RAW_RUNTIME_SHA256, str):
    raise RuntimeError("transaction-bound runtime identity is missing")

R2: dict[str, Any] = cast(dict[str, Any], _RAW_R2_RUNTIME)
MATERIAL: dict[str, Any] = cast(dict[str, Any], _RAW_PILOT_MATERIAL)
TRANSACTION_ID: str = _RAW_TRANSACTION_ID
RUNTIME_SHA256: str = _RAW_RUNTIME_SHA256

WORK_ROOT: Final = Path("/kaggle/working").resolve()
OUTPUT_ROOT: Final = WORK_ROOT / "variance_pilot_transaction_bound_v1"
SCRATCH_ROOT: Final = WORK_ROOT / "variance_pilot_transaction_bound_v1_scratch"
TARGET_ROOT: Final = SCRATCH_ROOT / "target_runtime"
TARGET_SITE: Final = TARGET_ROOT / "lib" / "python3.12" / "site-packages"
TARGET_PYTHON: Final = TARGET_ROOT / "bin" / "python"
LOG_ROOT: Final = OUTPUT_ROOT / "worker_logs"
EVIDENCE_ZIP: Final = WORK_ROOT / "ag-variance-pilot-tx-v1-evidence.zip"

SERVED_MODEL_NAME: Final = "local-qwen2.5-0.5b-instruct"
MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"

EXPECTED_TRAJECTORIES: Final = 54
EXPECTED_TURNS: Final = 216
MAXIMUM_PILOT_REQUEST_ATTEMPTS: Final = 432
MAXIMUM_PREFLIGHT_REQUESTS: Final = 5
MAXIMUM_TOTAL_MODEL_REQUESTS: Final = 437
MAX_OUTPUT_TOKENS: Final = 64
SEED: Final = 7

TIMING_CANDIDATES: Final = {
    "prefill_duration_ms": ("vllm:request_prefill_time_seconds_sum",),
    "time_to_first_token_ms": ("vllm:time_to_first_token_seconds_sum",),
    "end_to_end_latency_ms": ("vllm:e2e_request_latency_seconds_sum",),
}

PROM_LINE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?:\{.*\})?\s+"
    r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$"
)

STATIC_RESPONSE_RULE: Final = (
    "Return exactly one JSON object. Do not use Markdown fences, commentary, "
    "or fields outside the frozen terminal-decision schema."
)
VOLATILE_INSTRUCTION: Final = (
    "Use only the supplied synthetic evidence. Return one terminal-decision JSON "
    "object for the current turn. Clarify rather than guess when evidence is incomplete."
)

PUBLIC_OUTPUTS: Final = (
    "timing_telemetry_preflight_v1.json",
    "pilot_trajectory_ledger_v1.json",
    "pilot_operational_evidence_v1.json",
    "pilot_runtime_summary_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "failure_report_v1.json",
    "bundle_manifest_v1.json",
)


class PilotRuntimeFailure(RuntimeError):
    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8", newline="\n")


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise PilotRuntimeFailure(code, message)


def _configure_reused_runtime() -> None:
    R2["OUTPUT_ROOT"] = OUTPUT_ROOT
    R2["SCRATCH_ROOT"] = SCRATCH_ROOT
    R2["TARGET_ROOT"] = TARGET_ROOT
    R2["TARGET_SITE"] = TARGET_SITE
    R2["TARGET_PYTHON"] = TARGET_PYTHON
    R2["EXPECTED_CHILD_PYTHON"] = TARGET_PYTHON
    R2["LOG_ROOT"] = LOG_ROOT
    R2["EVIDENCE_ZIP"] = EVIDENCE_ZIP


def _validate_material() -> tuple[
    dict[str, object],
    dict[str, dict[str, object]],
    dict[str, str],
    dict[str, object],
]:
    _require(isinstance(MATERIAL, dict), "PILOT_MATERIAL_INVALID", "material root invalid")
    schedule_raw = MATERIAL.get("pilot_schedule")
    episodes_raw = MATERIAL.get("episodes")
    sources_raw = MATERIAL.get("sources")
    compiler_spec_raw = MATERIAL.get("compiler_spec")
    if not isinstance(schedule_raw, dict):
        raise PilotRuntimeFailure(
            "PILOT_MATERIAL_INVALID",
            "pilot schedule missing from material",
        )
    if not isinstance(episodes_raw, list) or len(episodes_raw) != 6:
        raise PilotRuntimeFailure(
            "PILOT_MATERIAL_INVALID",
            "pilot material must contain six development episodes",
        )
    if not isinstance(sources_raw, dict) or not sources_raw:
        raise PilotRuntimeFailure(
            "PILOT_MATERIAL_INVALID",
            "pilot source material is missing",
        )
    if not isinstance(compiler_spec_raw, dict):
        raise PilotRuntimeFailure(
            "PILOT_MATERIAL_INVALID",
            "compiler specification is missing",
        )
    schedule = cast(dict[str, object], schedule_raw)
    episodes = cast(list[object], episodes_raw)
    sources = cast(dict[object, object], sources_raw)
    compiler_spec = cast(dict[str, object], compiler_spec_raw)
    required_schedule = {
        "case_count": 6,
        "trajectory_count": 54,
        "turn_count": 216,
        "maximum_request_attempt_count": 432,
        "hidden_retries_permitted": False,
        "replacement_cases_permitted": False,
        "final_benchmark_effect_claims_permitted": False,
    }
    for key, expected in required_schedule.items():
        _require(
            schedule.get(key) == expected,
            "PILOT_SCHEDULE_DRIFT",
            "pilot schedule contract drifted",
        )
    trajectories = schedule.get("trajectories")
    _require(
        isinstance(trajectories, list) and len(trajectories) == EXPECTED_TRAJECTORIES,
        "PILOT_SCHEDULE_DRIFT",
        "pilot schedule must contain 54 trajectories",
    )
    episode_map: dict[str, dict[str, object]] = {}
    for raw in episodes:
        if not isinstance(raw, dict):
            raise PilotRuntimeFailure(
                "PILOT_MATERIAL_INVALID",
                "pilot episode row invalid",
            )
        episode = cast(dict[str, object], raw)
        episode_id = episode.get("episode_id")
        split = episode.get("evaluation_split")
        if not isinstance(episode_id, str) or split != "development":
            raise PilotRuntimeFailure(
                "PILOT_MATERIAL_INVALID",
                "pilot episode identity or split invalid",
            )
        episode_map[episode_id] = episode
    _require(
        len(episode_map) == 6,
        "PILOT_MATERIAL_INVALID",
        "pilot episode identities must be unique",
    )
    source_map: dict[str, str] = {}
    for source_id, raw in sources.items():
        if not isinstance(source_id, str) or not isinstance(raw, dict):
            raise PilotRuntimeFailure(
                "PILOT_MATERIAL_INVALID",
                "pilot source row invalid",
            )
        source = cast(dict[str, object], raw)
        text = source.get("text")
        expected_sha = source.get("sha256")
        if not (
            isinstance(text, str)
            and isinstance(expected_sha, str)
            and sha256_text(text) == expected_sha
        ):
            raise PilotRuntimeFailure(
                "PILOT_MATERIAL_INVALID",
                "pilot source identity drifted",
            )
        source_map[source_id] = text
    return schedule, episode_map, source_map, compiler_spec


def _credential_preflight() -> None:
    for name in R2["CREDENTIAL_ENV_NAMES"]:
        value = os.environ.get(name)
        if value is not None and value.strip():
            raise PilotRuntimeFailure(
                "PILOT_CREDENTIAL_BOUNDARY_VIOLATION",
                "credential-bearing environment variable is present",
            )


def _static_prompt(spec: dict[str, object]) -> str:
    required = (
        "serialization_version",
        "template_id",
        "template_version",
        "segments",
        "tools",
        "output_schema",
        "context_pack",
    )
    _require(
        all(key in spec for key in required),
        "PILOT_COMPILER_SPEC_INVALID",
        "compiler specification is incomplete",
    )
    return canonical_json(
        {
            "runtime_prompt_profile": "development-live-compact-v1",
            "serialization_version": spec["serialization_version"],
            "template_id": spec["template_id"],
            "template_version": spec["template_version"],
            "segments": spec["segments"],
            "tools": spec["tools"],
            "output_schema": spec["output_schema"],
            "context_pack": spec["context_pack"],
            "response_rule": STATIC_RESPONSE_RULE,
        }
    )


def _volatile_prompt(
    episode: dict[str, object],
    turn_index: int,
    source_map: dict[str, str],
    prior_users: list[str],
    prior_assistants: list[str],
) -> tuple[str, str]:
    turns_raw = episode.get("turns")
    scope_raw = episode.get("source_scope")
    if not isinstance(turns_raw, list) or len(turns_raw) != 4:
        raise PilotRuntimeFailure(
            "PILOT_EPISODE_INVALID",
            "pilot episode must have four turns",
        )
    if not isinstance(scope_raw, dict):
        raise PilotRuntimeFailure(
            "PILOT_EPISODE_INVALID",
            "pilot episode source scope missing",
        )
    turns = cast(list[object], turns_raw)
    scope = cast(dict[str, object], scope_raw)
    raw_ids_value = scope.get("required_source_ids")
    if not isinstance(raw_ids_value, list) or not all(
        isinstance(item, str) for item in raw_ids_value
    ):
        raise PilotRuntimeFailure(
            "PILOT_EPISODE_INVALID",
            "pilot episode source IDs invalid",
        )
    raw_ids = cast(list[str], raw_ids_value)
    raw_turn_value = turns[turn_index - 1]
    if not isinstance(raw_turn_value, dict):
        raise PilotRuntimeFailure(
            "PILOT_EPISODE_INVALID",
            "pilot turn invalid",
        )
    raw_turn = cast(dict[str, object], raw_turn_value)
    user_message = raw_turn.get("user_message")
    if not isinstance(user_message, str) or not user_message.strip():
        raise PilotRuntimeFailure(
            "PILOT_EPISODE_INVALID",
            "pilot turn user message invalid",
        )
    history: list[dict[str, str]] = []
    for user_text, assistant_text in zip(
        prior_users,
        prior_assistants,
        strict=True,
    ):
        history.extend(
            (
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_text},
            )
        )
    evidence = []
    for source_id in raw_ids:
        source_text = source_map.get(source_id)
        if source_text is None:
            raise PilotRuntimeFailure(
                "PILOT_SOURCE_MISSING",
                "episode-required synthetic source is missing",
            )
        evidence.append({"source_id": source_id, "document": source_text})
    payload = {
        "episode_id": episode.get("episode_id"),
        "episode_title": episode.get("title"),
        "turn_index": turn_index,
        "conversation_history": history,
        "current_user_message": user_message,
        "permitted_source_ids": raw_ids,
        "retrieval_evidence": evidence,
        "instruction": VOLATILE_INSTRUCTION,
    }
    return canonical_json(payload), user_message


def _route(condition_id: str) -> tuple[str, str, str, str]:
    if condition_id in {"A", "B"}:
        return ("worker_1", "worker_2", "worker_1", "worker_2")
    if condition_id == "C":
        return ("worker_1", "worker_1", "worker_1", "worker_1")
    raise PilotRuntimeFailure("PILOT_CONDITION_INVALID", "pilot condition ID invalid")


def _prometheus_totals(payload: str) -> dict[str, float]:
    names = {name for candidates in TIMING_CANDIDATES.values() for name in candidates}
    totals = {name: 0.0 for name in names}
    seen: set[str] = set()
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = PROM_LINE.fullmatch(line)
        if match is None:
            continue
        name = match.group("name")
        if name not in names:
            continue
        value = float(match.group("value"))
        if not math.isfinite(value) or value < 0:
            raise PilotRuntimeFailure(
                "PILOT_TIMING_METRIC_INVALID",
                "timing metric contains invalid numeric value",
            )
        totals[name] += value
        seen.add(name)
    return {name: totals[name] for name in seen}


def _timing_delta(
    before: str,
    after: str,
) -> dict[str, tuple[str, float] | None]:
    before_values = _prometheus_totals(before)
    after_values = _prometheus_totals(after)
    result: dict[str, tuple[str, float] | None] = {}
    for role, candidates in TIMING_CANDIDATES.items():
        observed: list[tuple[str, float]] = []
        for name in candidates:
            if name not in before_values or name not in after_values:
                continue
            delta = after_values[name] - before_values[name]
            if delta < 0:
                raise PilotRuntimeFailure(
                    "PILOT_TIMING_METRIC_COUNTER_REGRESSION",
                    "timing metric counter regressed",
                )
            if delta > 0:
                observed.append((name, delta))
        result[role] = observed[0] if len(observed) == 1 else None
    return result


def _response_content(response: dict[str, object]) -> tuple[str, str]:
    choices_raw = response.get("choices")
    if not isinstance(choices_raw, list) or len(choices_raw) != 1:
        raise PilotRuntimeFailure(
            "PILOT_RESPONSE_ENVELOPE_INVALID",
            "chat completion must contain exactly one choice",
        )
    choice_raw = cast(list[object], choices_raw)[0]
    if not isinstance(choice_raw, dict):
        raise PilotRuntimeFailure(
            "PILOT_RESPONSE_ENVELOPE_INVALID",
            "chat completion choice invalid",
        )
    choice = cast(dict[str, object], choice_raw)
    message_raw = choice.get("message")
    finish_reason = choice.get("finish_reason")
    if not isinstance(message_raw, dict):
        raise PilotRuntimeFailure(
            "PILOT_RESPONSE_ENVELOPE_INVALID",
            "chat completion message invalid",
        )
    message = cast(dict[str, object], message_raw)
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise PilotRuntimeFailure(
            "PILOT_RESPONSE_ENVELOPE_INVALID",
            "chat completion content missing",
        )
    if not isinstance(finish_reason, str):
        raise PilotRuntimeFailure(
            "PILOT_RESPONSE_ENVELOPE_INVALID",
            "chat completion finish reason invalid",
        )
    return content, finish_reason


def _json_object_valid(content: str) -> bool:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, dict)


def _request(
    worker: Any,
    *,
    system_prompt: str,
    user_prompt: str,
    cache_salt: str,
    counters: dict[str, int],
) -> dict[str, object]:
    if counters["model_requests"] >= MAXIMUM_TOTAL_MODEL_REQUESTS:
        raise PilotRuntimeFailure(
            "PILOT_REQUEST_BUDGET_EXCEEDED",
            "maximum transaction-bound model request budget exceeded",
        )
    before_cache = worker.metric_snapshot()
    before_timing = R2["get_text"](f"http://127.0.0.1:{worker.port}/metrics")
    started = time.perf_counter()
    response = R2["post_json"](
        f"http://127.0.0.1:{worker.port}/v1/chat/completions",
        {
            "model": SERVED_MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "top_p": 1,
            "seed": SEED,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "n": 1,
            "stream": False,
            "cache_salt": cache_salt,
        },
    )
    wall_ms = (time.perf_counter() - started) * 1000
    after_timing = R2["get_text"](f"http://127.0.0.1:{worker.port}/metrics")
    after_cache = worker.metric_snapshot()
    counters["model_requests"] += 1
    cache_delta = R2["metric_delta"](before_cache, after_cache)
    timing = _timing_delta(before_timing, after_timing)
    content, finish_reason = _response_content(response)
    return {
        "content": content,
        "output_sha256": sha256_text(content),
        "finish_reason": finish_reason,
        "json_object_valid": _json_object_valid(content),
        "cached_prefix_tokens": round(cache_delta.local_cache_hit),
        "newly_computed_prefill_tokens": round(cache_delta.newly_computed_prefill_tokens),
        "external_kv_transfer_tokens": round(cache_delta.external_kv_transfer),
        "timing": timing,
        "wall_clock_end_to_end_ms": wall_ms,
    }


def _preflight_probe(
    worker: Any,
    worker_id: str,
    counters: dict[str, int],
) -> dict[str, object]:
    salt = sha256_text("variance-pilot-timing-preflight|" + worker_id)
    long_prefix = (
        "AuraGateway synthetic timing and prefix-cache isolation preflight. "
        "This deterministic content is deliberately long enough to span "
        "multiple cache blocks and contains no customer data. "
    ) * 32
    result = _request(
        worker,
        system_prompt=long_prefix,
        user_prompt='{"status":"timing-preflight"}',
        cache_salt=salt,
        counters=counters,
    )
    timing_raw = result["timing"]
    if not isinstance(timing_raw, dict):
        raise PilotRuntimeFailure(
            "PILOT_TIMING_PREFLIGHT_FAILED",
            "timing preflight result invalid",
        )
    timing = cast(dict[str, object], timing_raw)
    roles: dict[str, dict[str, object]] = {}
    for role in TIMING_CANDIDATES:
        observed = timing.get(role)
        if not (
            isinstance(observed, tuple)
            and len(observed) == 2
            and isinstance(observed[0], str)
            and isinstance(observed[1], (int, float))
        ):
            raise PilotRuntimeFailure(
                "PILOT_TIMING_TELEMETRY_UNAVAILABLE",
                "required current-runtime timing metric role unavailable",
            )
        name = observed[0]
        delta = float(observed[1])
        roles[role] = {
            "metric_name": name,
            "observed_positive_delta": delta > 0,
        }
    return {
        "worker_id": worker_id,
        "roles": roles,
        "raw_metrics_retained": False,
        "raw_output_retained": False,
        "output_sha256": result["output_sha256"],
    }


def _cache_salt_isolation_preflight(
    worker: Any,
    counters: dict[str, int],
) -> dict[str, object]:
    long_prefix = (
        "AuraGateway synthetic timing and prefix-cache isolation preflight. "
        "This deterministic content is deliberately long enough to span "
        "multiple cache blocks and contains no customer data. "
    ) * 32
    salt_a = sha256_text("variance-pilot-cache-salt-preflight|A")
    salt_b = sha256_text("variance-pilot-cache-salt-preflight|B")
    cold = _request(
        worker,
        system_prompt=long_prefix,
        user_prompt='{"status":"cache-salt-preflight"}',
        cache_salt=salt_a,
        counters=counters,
    )
    warm = _request(
        worker,
        system_prompt=long_prefix,
        user_prompt='{"status":"cache-salt-preflight"}',
        cache_salt=salt_a,
        counters=counters,
    )
    isolated = _request(
        worker,
        system_prompt=long_prefix,
        user_prompt='{"status":"cache-salt-preflight"}',
        cache_salt=salt_b,
        counters=counters,
    )
    cold_hits = cold.get("cached_prefix_tokens")
    warm_hits = warm.get("cached_prefix_tokens")
    isolated_hits = isolated.get("cached_prefix_tokens")
    if not (
        isinstance(cold_hits, int) and isinstance(warm_hits, int) and isinstance(isolated_hits, int)
    ):
        raise PilotRuntimeFailure(
            "PILOT_CACHE_SALT_PREFLIGHT_INVALID",
            "cache-salt preflight did not produce integer cache metrics",
        )
    _require(
        warm_hits > cold_hits,
        "PILOT_CACHE_SALT_REUSE_NOT_OBSERVED",
        "same-salt warm request did not increase prefix-cache reuse",
    )
    _require(
        isolated_hits <= cold_hits,
        "PILOT_CACHE_SALT_ISOLATION_NOT_OBSERVED",
        "different-salt request inherited warm prefix-cache state",
    )
    return {
        "status": "QUALIFIED",
        "mechanism": "VLLM_CACHE_SALT",
        "same_salt_warm_cached_prefix_tokens": warm_hits,
        "same_salt_cold_cached_prefix_tokens": cold_hits,
        "different_salt_cached_prefix_tokens": isolated_hits,
        "cross_salt_reuse_observed": False,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }


def _validate_preflight_pair(
    worker_1: dict[str, object],
    worker_2: dict[str, object],
) -> dict[str, object]:
    roles_1_raw = worker_1["roles"]
    roles_2_raw = worker_2["roles"]
    if not isinstance(roles_1_raw, dict) or not isinstance(roles_2_raw, dict):
        raise PilotRuntimeFailure(
            "PILOT_TIMING_PREFLIGHT_FAILED",
            "timing preflight role map invalid",
        )
    roles_1 = cast(dict[str, object], roles_1_raw)
    roles_2 = cast(dict[str, object], roles_2_raw)
    selected: dict[str, str] = {}
    for role in TIMING_CANDIDATES:
        item_1_raw = roles_1.get(role)
        item_2_raw = roles_2.get(role)
        if not isinstance(item_1_raw, dict) or not isinstance(item_2_raw, dict):
            raise PilotRuntimeFailure(
                "PILOT_TIMING_PREFLIGHT_FAILED",
                "timing preflight role missing",
            )
        item_1 = cast(dict[str, object], item_1_raw)
        item_2 = cast(dict[str, object], item_2_raw)
        name_1 = item_1.get("metric_name")
        name_2 = item_2.get("metric_name")
        if not isinstance(name_1, str) or name_1 != name_2:
            raise PilotRuntimeFailure(
                "PILOT_TIMING_METRIC_ASYMMETRY",
                "workers do not expose the same timing metric mapping",
            )
        selected[role] = name_1
    return {
        "schema_version": "1.0.0",
        "status": "QUALIFIED",
        "transaction_id": TRANSACTION_ID,
        "timing_preflight_request_count": 2,
        "worker_1": worker_1,
        "worker_2": worker_2,
        "selected_metric_names": selected,
        "pilot_requests_permitted": True,
        "missing_metric_becomes_zero": False,
        "ambiguous_metric_permitted": False,
        "raw_metrics_retained": False,
    }


def _source_evidence(
    episode: dict[str, object],
    source_map: dict[str, str],
) -> tuple[dict[str, str], ...]:
    scope_raw = episode.get("source_scope")
    if not isinstance(scope_raw, dict):
        raise PilotRuntimeFailure(
            "PILOT_EPISODE_INVALID",
            "episode source scope missing",
        )
    scope = cast(dict[str, object], scope_raw)
    raw_ids_value = scope.get("required_source_ids")
    if not isinstance(raw_ids_value, list):
        raise PilotRuntimeFailure(
            "PILOT_EPISODE_INVALID",
            "episode required source IDs missing",
        )
    raw_ids = cast(list[object], raw_ids_value)
    result: list[dict[str, str]] = []
    for source_id in raw_ids:
        if not isinstance(source_id, str) or source_id not in source_map:
            raise PilotRuntimeFailure(
                "PILOT_SOURCE_MISSING",
                "episode-required source missing",
            )
        result.append({"source_id": source_id, "document": source_map[source_id]})
    return tuple(result)


def _trajectory(
    raw: dict[str, object],
    episode: dict[str, object],
    source_map: dict[str, str],
    static_prompt: str,
    workers: dict[str, Any],
    counters: dict[str, int],
) -> tuple[dict[str, object], dict[str, object]]:
    run_id = raw.get("run_id")
    condition_id = raw.get("condition_id")
    namespace = raw.get("cache_namespace_id")
    episode_id = raw.get("episode_id")
    if not (
        isinstance(run_id, str)
        and isinstance(condition_id, str)
        and isinstance(namespace, str)
        and isinstance(episode_id, str)
    ):
        raise PilotRuntimeFailure(
            "PILOT_TRAJECTORY_INVALID",
            "pilot trajectory identity invalid",
        )
    worker_ids = _route(condition_id)
    cache_salt = sha256_text(namespace)
    prior_users: list[str] = []
    prior_assistants: list[str] = []
    turn_records: list[dict[str, object]] = []
    started = time.perf_counter()
    task_status = "completed"
    comparison_status = "eligible"
    interrupted = False

    for turn_index, worker_id in enumerate(worker_ids, start=1):
        volatile, user_message = _volatile_prompt(
            episode,
            turn_index,
            source_map,
            prior_users,
            prior_assistants,
        )
        if condition_id == "A":
            system_prompt = static_prompt + volatile
            user_prompt = "Return the JSON decision for the current embedded turn."
        else:
            system_prompt = static_prompt
            user_prompt = volatile
        worker = workers[worker_id]
        try:
            result = _request(
                worker,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                cache_salt=cache_salt,
                counters=counters,
            )
        except Exception as error:
            task_status = "interrupted"
            comparison_status = "ineligible"
            interrupted = True
            turn_records.append(
                {
                    "turn_index": turn_index,
                    "worker_id": worker_id,
                    "request_completed": False,
                    "error_type": type(error).__name__,
                    "raw_prompt_retained": False,
                    "raw_output_retained": False,
                }
            )
            break
        timing_raw = result["timing"]
        if not isinstance(timing_raw, dict):
            raise PilotRuntimeFailure(
                "PILOT_TELEMETRY_INVALID",
                "request timing evidence invalid",
            )
        timing = cast(dict[str, object], timing_raw)
        timing_values: dict[str, float | None] = {}
        for role in TIMING_CANDIDATES:
            observed = timing.get(role)
            if isinstance(observed, tuple) and len(observed) == 2:
                timing_values[role] = float(observed[1]) * 1000
            else:
                timing_values[role] = None
                comparison_status = "ineligible"
        if result["external_kv_transfer_tokens"] != 0:
            comparison_status = "ineligible"
        if result["finish_reason"] != "stop" or result["json_object_valid"] is not True:
            task_status = "failed"
        prior_users.append(user_message)
        prior_assistants.append(str(result["content"]))
        turn_records.append(
            {
                "turn_index": turn_index,
                "worker_id": worker_id,
                "request_completed": True,
                "finish_reason": result["finish_reason"],
                "json_object_valid": result["json_object_valid"],
                "output_sha256": result["output_sha256"],
                "cached_prefix_tokens": result["cached_prefix_tokens"],
                "newly_computed_prefill_tokens": (result["newly_computed_prefill_tokens"]),
                "external_kv_transfer_tokens": (result["external_kv_transfer_tokens"]),
                "prefill_duration_ms": timing_values["prefill_duration_ms"],
                "time_to_first_token_ms": (timing_values["time_to_first_token_ms"]),
                "end_to_end_latency_ms": (timing_values["end_to_end_latency_ms"]),
                "wall_clock_end_to_end_ms": result["wall_clock_end_to_end_ms"],
                "cache_salt_sha256": sha256_text(cache_salt),
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            }
        )

    session_ms = (time.perf_counter() - started) * 1000
    turn_2 = turn_records[1] if len(turn_records) >= 2 else None
    cache_consistent: bool | None = None
    if isinstance(turn_2, dict) and turn_2.get("request_completed") is True:
        cached = turn_2.get("cached_prefix_tokens")
        if isinstance(cached, int):
            cache_consistent = cached > 0 if condition_id == "C" else cached == 0
            if not cache_consistent:
                comparison_status = "ineligible"
    if len(turn_records) != 4:
        comparison_status = "ineligible"
    ledger_row = {
        "schedule_index": raw.get("schedule_index"),
        "run_id": run_id,
        "comparison_pair_id": raw.get("comparison_pair_id"),
        "episode_id": episode_id,
        "pilot_replication_id": raw.get("pilot_replication_id"),
        "condition_id": condition_id,
        "cache_namespace_sha256": sha256_text(namespace),
        "cache_isolation_mechanism": "VLLM_CACHE_SALT",
        "task_status": task_status,
        "comparison_status": comparison_status,
        "interrupted": interrupted,
        "session_duration_ms": session_ms,
        "turns": turn_records,
        "raw_prompt_retained": False,
        "raw_user_message_retained": False,
        "raw_retrieved_document_text_retained": False,
        "raw_model_output_retained": False,
        "credentials_retained": False,
        "customer_data_used": False,
    }
    projection: dict[str, object] = {
        "run_id": run_id,
        "episode_id": episode_id,
        "pilot_replication_id": raw.get("pilot_replication_id"),
        "condition_id": condition_id,
        "worker_id": None,
        "task_status": task_status,
        "comparison_status": comparison_status,
        "interrupted": interrupted,
        "cached_prefix_tokens": None,
        "newly_computed_prefill_tokens": None,
        "prefill_duration_ms": None,
        "time_to_first_token_ms": None,
        "end_to_end_latency_ms": None,
        "session_duration_ms": session_ms,
        "cache_consistent": cache_consistent,
        "raw_prompt_retained": False,
        "raw_user_message_retained": False,
        "raw_retrieved_document_text_retained": False,
        "raw_model_output_retained": False,
        "credentials_retained": False,
        "customer_data_used": False,
    }
    if isinstance(turn_2, dict):
        projection.update(
            {
                "worker_id": turn_2.get("worker_id"),
                "cached_prefix_tokens": turn_2.get("cached_prefix_tokens"),
                "newly_computed_prefill_tokens": (turn_2.get("newly_computed_prefill_tokens")),
                "prefill_duration_ms": turn_2.get("prefill_duration_ms"),
                "time_to_first_token_ms": (turn_2.get("time_to_first_token_ms")),
                "end_to_end_latency_ms": turn_2.get("end_to_end_latency_ms"),
            }
        )
    return ledger_row, projection


def _bundle() -> dict[str, object]:
    members: list[dict[str, object]] = []
    for name in PUBLIC_OUTPUTS:
        path = OUTPUT_ROOT / name
        if name == "bundle_manifest_v1.json":
            continue
        if not path.is_file():
            continue
        payload = path.read_bytes()
        members.append(
            {
                "name": name,
                "sha256": sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "transaction_id": TRANSACTION_ID,
        "runtime_payload_sha256": RUNTIME_SHA256,
        "member_count": len(members),
        "members": members,
        "raw_prompts_included": False,
        "raw_outputs_included": False,
        "raw_source_documents_included": False,
        "credentials_included": False,
    }
    write_json(OUTPUT_ROOT / "bundle_manifest_v1.json", manifest)
    with zipfile.ZipFile(
        EVIDENCE_ZIP,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for name in PUBLIC_OUTPUTS:
            path = OUTPUT_ROOT / name
            if path.is_file():
                archive.write(path, arcname=name)
    return {
        "evidence_zip": EVIDENCE_ZIP.name,
        "evidence_zip_sha256": sha256_bytes(EVIDENCE_ZIP.read_bytes()),
        "evidence_zip_size_bytes": EVIDENCE_ZIP.stat().st_size,
        "bundle_manifest_sha256": sha256_bytes(
            (OUTPUT_ROOT / "bundle_manifest_v1.json").read_bytes()
        ),
    }


def main() -> int:
    if OUTPUT_ROOT.exists() or SCRATCH_ROOT.exists() or EVIDENCE_ZIP.exists():
        raise PilotRuntimeFailure(
            "PILOT_WORKSPACE_NOT_FRESH",
            "variance-pilot output or scratch path already exists",
        )
    OUTPUT_ROOT.mkdir(parents=True)
    _configure_reused_runtime()
    schedule, episodes, source_map, compiler_spec = _validate_material()
    _credential_preflight()

    counters = {
        "runtime_install_attempts": 0,
        "runtime_import_closure_probes": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
    }
    worker_1 = None
    worker_2 = None
    primary_error: BaseException | None = None

    try:
        wheelhouse = R2["discover_one_directory"](R2["RUNTIME_OUTPUT_DIRECTORY"])
        R2["validate_wheelhouse"](wheelhouse)
        source_snapshot = R2["discover_model_snapshot"]()
        R2["install_runtime"](wheelhouse, counters)
        R2["validate_target_runtime"]()
        model_home, snapshot = R2["prepare_model_home"](source_snapshot)

        worker_1 = R2["Worker"](
            "worker_1",
            0,
            8001,
            model_home,
            snapshot,
            generation=1,
        )
        worker_2 = R2["Worker"](
            "worker_2",
            1,
            8002,
            model_home,
            snapshot,
            generation=1,
        )
        worker_1.start(counters)
        worker_1.wait_ready()
        worker_1.validate_model()
        worker_2.start(counters)
        worker_2.wait_ready()
        worker_2.validate_model()

        preflight_1 = _preflight_probe(worker_1, "worker_1", counters)
        preflight_2 = _preflight_probe(worker_2, "worker_2", counters)
        timing_preflight = _validate_preflight_pair(preflight_1, preflight_2)
        cache_salt_preflight = _cache_salt_isolation_preflight(
            worker_1,
            counters,
        )
        preflight = {
            **timing_preflight,
            "timing_preflight_request_count": 2,
            "cache_salt_preflight_request_count": 3,
            "total_preflight_request_count": 5,
            "cache_salt_isolation": cache_salt_preflight,
            "cache_salt_isolation_qualified": True,
        }
        write_json(
            OUTPUT_ROOT / "timing_telemetry_preflight_v1.json",
            preflight,
        )

        trajectories_raw = schedule.get("trajectories")
        if not isinstance(trajectories_raw, list):
            raise PilotRuntimeFailure(
                "PILOT_SCHEDULE_DRIFT",
                "pilot trajectories missing",
            )
        trajectories = cast(list[object], trajectories_raw)
        static_prompt = _static_prompt(compiler_spec)
        workers = {"worker_1": worker_1, "worker_2": worker_2}
        ledger: list[dict[str, object]] = []
        projections: list[dict[str, object]] = []

        for expected_index, raw in enumerate(trajectories):
            if not isinstance(raw, dict):
                raise PilotRuntimeFailure(
                    "PILOT_TRAJECTORY_INVALID",
                    "pilot trajectory row invalid",
                )
            trajectory = cast(dict[str, object], raw)
            _require(
                trajectory.get("schedule_index") == expected_index,
                "PILOT_SCHEDULE_ORDER_DRIFT",
                "pilot trajectory order drifted",
            )
            episode_id = trajectory.get("episode_id")
            if not isinstance(episode_id, str) or episode_id not in episodes:
                raise PilotRuntimeFailure(
                    "PILOT_EPISODE_INVALID",
                    "pilot trajectory references unknown episode",
                )
            row, projection = _trajectory(
                trajectory,
                episodes[episode_id],
                source_map,
                static_prompt,
                workers,
                counters,
            )
            ledger.append(row)
            projections.append(projection)

        write_json(
            OUTPUT_ROOT / "pilot_trajectory_ledger_v1.json",
            {
                "schema_version": "1.0.0",
                "transaction_id": TRANSACTION_ID,
                "scheduled_trajectory_count": 54,
                "scheduled_turn_count": 216,
                "timing_preflight_request_count": 5,
                "model_request_count": counters["model_requests"],
                "hidden_retry_count": 0,
                "replacement_case_count": 0,
                "trajectories": ledger,
            },
        )
        write_json(
            OUTPUT_ROOT / "pilot_operational_evidence_v1.json",
            {
                "schema_version": "1.0.0",
                "bundle_id": ("auragateway-measured-abc-variance-pilot-v1-evidence"),
                "transaction_id": TRANSACTION_ID,
                "trajectory_count": len(projections),
                "trajectories": projections,
                "external_spend": 0,
                "external_network_requests": 0,
                "hidden_retries": 0,
                "replacement_cases_used": False,
            },
        )
        completed = sum(item["task_status"] == "completed" for item in projections)
        interrupted = sum(bool(item["interrupted"]) for item in projections)
        eligible = sum(item["comparison_status"] == "eligible" for item in projections)
        write_json(
            OUTPUT_ROOT / "pilot_runtime_summary_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "PASSED_PENDING_REPOSITORY_ACCEPTANCE",
                "transaction_id": TRANSACTION_ID,
                "scheduled_trajectory_count": 54,
                "completed_trajectory_count": completed,
                "interrupted_trajectory_count": interrupted,
                "comparison_eligible_trajectory_count": eligible,
                "model_request_count": counters["model_requests"],
                "timing_preflight_request_count": 5,
                "pilot_execution_authorized_at_runtime": True,
                "pilot_repository_acceptance_established": False,
                "final_measured_abc_execution_authorized": False,
                "effect_claims_permitted": False,
                "raw_prompts_retained": False,
                "raw_outputs_retained": False,
                "customer_data_used": False,
                "external_spend": 0,
            },
        )
        write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "NO_FATAL_RUNTIME_FAILURE",
                "transaction_id": TRANSACTION_ID,
                "fatal_failure": False,
            },
        )
    except BaseException as error:
        primary_error = error
        write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "FATAL_RUNTIME_FAILURE",
                "transaction_id": TRANSACTION_ID,
                "fatal_failure": True,
                "exception_type": type(error).__name__,
                "safe_message": str(error)[:1000],
            },
        )
    finally:
        reports: list[dict[str, object]] = []
        for worker, reason in (
            (worker_2, "variance_pilot_complete"),
            (worker_1, "variance_pilot_complete"),
        ):
            if worker is None:
                continue
            try:
                reports.append(worker.stop_and_report(reason))
            except BaseException as error:
                reports.append(
                    {
                        "status": "FAILED",
                        "worker_id": getattr(worker, "worker_id", "unknown"),
                        "error_type": type(error).__name__,
                    }
                )
                if primary_error is None:
                    primary_error = error
        write_json(
            OUTPUT_ROOT / "worker_teardown_report_v1.json",
            {
                "schema_version": "1.0.0",
                "transaction_id": TRANSACTION_ID,
                "worker_report_count": len(reports),
                "reports": reports,
            },
        )
        try:
            cleanup = R2["cleanup_scratch"]()
        except BaseException as error:
            cleanup = {
                "schema_version": "1.0.0",
                "status": "FAILED",
                "error_type": type(error).__name__,
            }
            if primary_error is None:
                primary_error = error
        write_json(OUTPUT_ROOT / "scratch_cleanup_report_v1.json", cleanup)
        bundle = _bundle()
        print("EVIDENCE_ZIP_SHA256=" + str(bundle["evidence_zip_sha256"]))
        print("TRANSACTION_ID=" + TRANSACTION_ID)
        print("EXECUTION_OUTCOME=" + ("PASSED" if primary_error is None else "FAILED"))

    if primary_error is not None:
        raise primary_error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
