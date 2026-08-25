"""Transaction-bound runtime orchestrator for measured A/B/C variance-pilot successor V2.

The authorization wrapper injects exact committed namespaces for the accepted R2 runtime
mechanics and the already-qualified V2 deterministic components. This module composes those
pieces without reconstructing prompt, routing, admission, tokenizer, or request semantics.

No model work occurs on import. Live execution requires an injected transaction context.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final, TypeAlias, cast

JsonObject: TypeAlias = dict[str, object]
JsonHistory: TypeAlias = list[dict[str, str]]
MessageList: TypeAlias = list[dict[str, str]]
Namespace: TypeAlias = dict[str, Any]

WORK_ROOT: Final = Path("/kaggle/working").resolve()
OUTPUT_ROOT: Final = WORK_ROOT / "variance_pilot_v2_transaction_bound_v1"
SCRATCH_ROOT: Final = WORK_ROOT / "variance_pilot_v2_transaction_bound_v1_scratch"
TARGET_ROOT: Final = SCRATCH_ROOT / "target_runtime"
TARGET_SITE: Final = TARGET_ROOT / "lib" / "python3.12" / "site-packages"
TARGET_PYTHON: Final = TARGET_ROOT / "bin" / "python"
LOG_ROOT: Final = OUTPUT_ROOT / "worker_logs"
CHECKPOINT_ROOT: Final = OUTPUT_ROOT / "checkpoints"
EVIDENCE_ZIP: Final = WORK_ROOT / "ag-variance-pilot-v2-tx-v1-evidence.zip"

EXPECTED_TRAJECTORY_COUNT: Final = 54
EXPECTED_COMPARISON_PAIR_COUNT: Final = 18
EXPECTED_PILOT_TURN_COUNT: Final = 216
EXPECTED_SCHEMA_CANARY_REQUEST_COUNT: Final = 2
EXPECTED_WARMUP_REQUEST_COUNT: Final = 2
EXPECTED_NEUTRAL_REQUEST_COUNT: Final = 20
EXPECTED_PRETREATMENT_REQUEST_COUNT: Final = 24
EXPECTED_TOTAL_SCHEDULED_REQUESTS: Final = 240
MAX_MODEL_LEN: Final = 4096
MAX_OUTPUT_TOKENS: Final = 256
MAX_EVIDENCE_ZIP_BYTES: Final = 2 * 1024**2

TIMING_CANDIDATES: Final = {
    "prefill_duration_ms": ("vllm:request_prefill_time_seconds_sum",),
    "time_to_first_token_ms": ("vllm:time_to_first_token_seconds_sum",),
    "end_to_end_latency_ms": ("vllm:e2e_request_latency_seconds_sum",),
}
PROM_LINE: Final = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?:\{.*\})?\s+"
    r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$"
)
_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")

PUBLIC_OUTPUT_NAMES: Final = (
    "runtime_binding_report_v1.json",
    "pretreatment_ledger_v1.json",
    "neutral_worker_qualification_v1.json",
    "pilot_trajectory_ledger_v1.json",
    "request_reconciliation_v1.json",
    "runtime_summary_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "failure_report_v1.json",
    "checkpoint_manifest_v1.json",
    "bundle_manifest_v1.json",
)


class V2TransactionRuntimeError(RuntimeError):
    """Metadata-safe transaction-bound V2 runtime failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise V2TransactionRuntimeError(code, message)


def _as_object(value: object, code: str, message: str) -> JsonObject:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise V2TransactionRuntimeError(code, message)
    return cast(JsonObject, value)


def _as_object_list(value: object, code: str, message: str) -> list[JsonObject]:
    if not isinstance(value, list):
        raise V2TransactionRuntimeError(code, message)
    result: list[JsonObject] = []
    for raw in value:
        result.append(_as_object(raw, code, message))
    return result


def _as_message_list(value: object, code: str, message: str) -> MessageList:
    if not isinstance(value, list):
        raise V2TransactionRuntimeError(code, message)
    for raw in value:
        if not isinstance(raw, dict):
            raise V2TransactionRuntimeError(code, message)
        if set(raw) != {"role", "content"}:
            raise V2TransactionRuntimeError(code, message)
        if not isinstance(raw.get("role"), str) or not isinstance(raw.get("content"), str):
            raise V2TransactionRuntimeError(code, message)
    return cast(MessageList, value)


def _request_count(row: JsonObject, field_name: str) -> int:
    value = row.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise V2TransactionRuntimeError(
            "V2_REQUEST_RECONCILIATION_FAILED",
            f"V2 request reconciliation field is invalid: {field_name}",
        )
    return value


def _safe_message(error: BaseException) -> str:
    value = getattr(error, "safe_message", None)
    if isinstance(value, str) and value:
        return value[:1000]
    return "transaction-bound runtime failed; inspect the recorded exception type"


def _atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(value).encode("utf-8")
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise V2TransactionRuntimeError(
            "V2_EVIDENCE_TEMPORARY_PATH_EXISTS",
            "temporary evidence path already exists",
        )
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _injected_namespace(name: str) -> Namespace:
    value = globals().get(name)
    if not isinstance(value, dict):
        raise V2TransactionRuntimeError(
            "V2_TRANSACTION_INJECTION_MISSING",
            f"required injected namespace is missing: {name}",
        )
    return cast(Namespace, value)


def _transaction_context() -> tuple[str, str]:
    transaction_id = globals().get("AURAGATEWAY_TRANSACTION_ID")
    runtime_sha256 = globals().get("EXECUTED_RUNTIME_SCRIPT_SHA256")
    if not isinstance(transaction_id, str) or _SHA256_PATTERN.fullmatch(transaction_id) is None:
        raise V2TransactionRuntimeError(
            "V2_TRANSACTION_ID_INVALID",
            "transaction-bound transaction identity is missing or invalid",
        )
    if not isinstance(runtime_sha256, str) or _SHA256_PATTERN.fullmatch(runtime_sha256) is None:
        raise V2TransactionRuntimeError(
            "V2_RUNTIME_SOURCE_IDENTITY_INVALID",
            "transaction-bound runtime source identity is missing or invalid",
        )
    return transaction_id, runtime_sha256


def _material() -> JsonObject:
    value = globals().get("AURAGATEWAY_V2_MATERIAL")
    return _as_object(
        value,
        "V2_TRANSACTION_MATERIAL_MISSING",
        "transaction-bound V2 material is missing or invalid",
    )


def _configure_reused_runtime(r2: Namespace) -> None:
    r2["OUTPUT_ROOT"] = OUTPUT_ROOT
    r2["SCRATCH_ROOT"] = SCRATCH_ROOT
    r2["TARGET_ROOT"] = TARGET_ROOT
    r2["TARGET_SITE"] = TARGET_SITE
    r2["TARGET_PYTHON"] = TARGET_PYTHON
    r2["EXPECTED_CHILD_PYTHON"] = TARGET_PYTHON
    r2["LOG_ROOT"] = LOG_ROOT
    r2["EVIDENCE_ZIP"] = EVIDENCE_ZIP


def _validate_schedule(schedule: JsonObject) -> list[JsonObject]:
    required = {
        "case_count": 6,
        "trajectory_count": EXPECTED_TRAJECTORY_COUNT,
        "comparison_pair_count": EXPECTED_COMPARISON_PAIR_COUNT,
        "pilot_turn_count": EXPECTED_PILOT_TURN_COUNT,
        "hidden_retries_permitted": False,
        "replacement_cases_permitted": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, expected in required.items():
        _require(
            schedule.get(key) == expected,
            "V2_PILOT_SCHEDULE_DRIFT",
            "V2 pilot schedule contract drifted",
        )
    trajectories = _as_object_list(
        schedule.get("trajectories"),
        "V2_PILOT_SCHEDULE_DRIFT",
        "V2 pilot trajectory set is invalid",
    )
    _require(
        len(trajectories) == EXPECTED_TRAJECTORY_COUNT,
        "V2_PILOT_SCHEDULE_DRIFT",
        "V2 pilot schedule must contain exactly 54 trajectories",
    )
    for index, trajectory in enumerate(trajectories):
        _require(
            trajectory.get("schedule_index") == index,
            "V2_PILOT_SCHEDULE_ORDER_DRIFT",
            "V2 pilot schedule order drifted",
        )
        _require(
            trajectory.get("turn_count") == 4
            and trajectory.get("maximum_request_attempt_count") == 4,
            "V2_PILOT_TRAJECTORY_INVALID",
            "V2 pilot trajectory turn contract drifted",
        )
        route = trajectory.get("realized_route")
        _require(
            isinstance(route, list)
            and len(route) == 4
            and all(item in {"worker_1", "worker_2"} for item in route),
            "V2_PILOT_REALIZED_ROUTE_INVALID",
            "V2 pilot realized route is invalid",
        )
        _require(
            trajectory.get("condition_id") in {"A", "B", "C"},
            "V2_PILOT_TRAJECTORY_INVALID",
            "V2 pilot condition identity is invalid",
        )
    for pair_index in range(EXPECTED_COMPARISON_PAIR_COUNT):
        trio = trajectories[pair_index * 3 : pair_index * 3 + 3]
        pair_ids = {item.get("comparison_pair_id") for item in trio}
        condition_ids = [item.get("condition_id") for item in trio]
        condition_order = [item.get("condition_order_index") for item in trio]
        _require(
            len(pair_ids) == 1
            and None not in pair_ids
            and condition_ids == ["A", "B", "C"]
            and condition_order == [0, 1, 2],
            "V2_PILOT_COMPARISON_TRIO_INVALID",
            "V2 pilot comparison trio contract drifted",
        )
    return trajectories


def _validate_neutral_plan(plan: JsonObject) -> list[JsonObject]:
    required = {
        "schema_canary_request_count": EXPECTED_SCHEMA_CANARY_REQUEST_COUNT,
        "warmup_request_count": EXPECTED_WARMUP_REQUEST_COUNT,
        "measured_request_count": EXPECTED_NEUTRAL_REQUEST_COUNT,
        "pre_treatment_request_count": EXPECTED_PRETREATMENT_REQUEST_COUNT,
        "hidden_retries_permitted": False,
        "pilot_execution_authorized": False,
    }
    for key, expected in required.items():
        _require(
            plan.get(key) == expected,
            "V2_PRETREATMENT_PLAN_DRIFT",
            "V2 pre-treatment plan contract drifted",
        )
    requests = _as_object_list(
        plan.get("requests"),
        "V2_PRETREATMENT_PLAN_DRIFT",
        "V2 pre-treatment request set is invalid",
    )
    _require(
        len(requests) == EXPECTED_PRETREATMENT_REQUEST_COUNT,
        "V2_PRETREATMENT_PLAN_DRIFT",
        "V2 pre-treatment plan must contain exactly 24 requests",
    )
    expected_prefix = (
        ("schema_canary", "worker_1", False),
        ("schema_canary", "worker_2", False),
        ("warmup", "worker_2", False),
        ("warmup", "worker_1", False),
    )
    for index, request in enumerate(requests):
        _require(
            request.get("sequence_index") == index,
            "V2_PRETREATMENT_ORDER_DRIFT",
            "V2 pre-treatment request order drifted",
        )
        _require(
            request.get("worker_id") in {"worker_1", "worker_2"}
            and request.get("max_output_tokens") == MAX_OUTPUT_TOKENS,
            "V2_PRETREATMENT_REQUEST_INVALID",
            "V2 pre-treatment request contract drifted",
        )
        if index < 4:
            phase, worker_id, measured = expected_prefix[index]
            _require(
                request.get("phase") == phase
                and request.get("worker_id") == worker_id
                and request.get("measured_for_worker_symmetry") is measured,
                "V2_PRETREATMENT_ORDER_DRIFT",
                "V2 pre-treatment canary/warmup order drifted",
            )
        if index >= 4:
            _require(
                request.get("phase") == "neutral_worker_qualification"
                and request.get("measured_for_worker_symmetry") is True,
                "V2_PRETREATMENT_MEASURED_SET_INVALID",
                "V2 measured neutral qualification set drifted",
            )
    return requests


def _episode_map(
    schedule: JsonObject,
    episodes_raw: object,
) -> dict[str, JsonObject]:
    cases = _as_object_list(
        schedule.get("cases"),
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 pilot case set is invalid",
    )
    case_ids: set[str] = set()
    for item in cases:
        episode_id = item.get("episode_id")
        if isinstance(episode_id, str):
            case_ids.add(episode_id)
    _require(
        len(case_ids) == 6,
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 pilot case identities are invalid",
    )
    episodes = _as_object_list(
        episodes_raw,
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 pilot episode material is invalid",
    )
    result: dict[str, JsonObject] = {}
    for episode in episodes:
        episode_id = episode.get("episode_id")
        if not isinstance(episode_id, str):
            raise V2TransactionRuntimeError(
                "V2_TRANSACTION_MATERIAL_INVALID",
                "V2 pilot episode identity is invalid",
            )
        if episode_id not in case_ids:
            continue
        _require(
            episode.get("evaluation_split") == "development",
            "V2_TRANSACTION_MATERIAL_SPLIT_INVALID",
            "V2 pilot material may contain development episodes only",
        )
        if episode_id in result:
            raise V2TransactionRuntimeError(
                "V2_TRANSACTION_MATERIAL_INVALID",
                "V2 pilot episode identity is duplicated",
            )
        result[episode_id] = episode
    _require(
        set(result) == case_ids,
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 pilot episode material does not match the frozen case set",
    )
    return result


def _source_map(episodes: dict[str, JsonObject], sources_raw: object) -> dict[str, str]:
    sources = _as_object(
        sources_raw,
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 source material is invalid",
    )
    required_ids: set[str] = set()
    for episode in episodes.values():
        scope = _as_object(
            episode.get("source_scope"),
            "V2_TRANSACTION_MATERIAL_INVALID",
            "V2 pilot episode source scope is invalid",
        )
        ids = scope.get("required_source_ids")
        _require(
            isinstance(ids, list) and all(isinstance(item, str) for item in ids),
            "V2_TRANSACTION_MATERIAL_INVALID",
            "V2 required source IDs are invalid",
        )
        required_ids.update(cast(list[str], ids))
    result: dict[str, str] = {}
    for source_id in required_ids:
        row = _as_object(
            sources.get(source_id),
            "V2_TRANSACTION_MATERIAL_INVALID",
            "V2 required source material is missing",
        )
        text = row.get("text")
        expected_sha = row.get("sha256")
        expected_bytes = row.get("byte_count")
        if (
            not isinstance(text, str)
            or not isinstance(expected_sha, str)
            or not isinstance(expected_bytes, int)
            or isinstance(expected_bytes, bool)
            or sha256_text(text) != expected_sha
            or len(text.encode("utf-8")) != expected_bytes
        ):
            raise V2TransactionRuntimeError(
                "V2_TRANSACTION_SOURCE_IDENTITY_DRIFT",
                "V2 required source identity drifted",
            )
        result[source_id] = text
    _require(
        set(result) == required_ids,
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 required source set is incomplete",
    )
    return result


def validate_material(material: JsonObject) -> JsonObject:
    """Validate the exact transaction material shape without granting execution authority."""

    schedule = _as_object(
        material.get("pilot_schedule"),
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 pilot schedule material is missing",
    )
    neutral_plan = _as_object(
        material.get("neutral_worker_qualification_plan"),
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 neutral qualification material is missing",
    )
    generation_contract = _as_object(
        material.get("generation_contract"),
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 generation contract material is missing",
    )
    response_format = _as_object(
        material.get("strict_response_format"),
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 strict response format material is missing",
    )
    admission_spec = _as_object(
        material.get("standalone_admission_spec"),
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 standalone admission material is missing",
    )
    compiler_spec = _as_object(
        material.get("compiler_spec"),
        "V2_TRANSACTION_MATERIAL_INVALID",
        "V2 compiler specification material is missing",
    )
    trajectories = _validate_schedule(schedule)
    pretreatment_requests = _validate_neutral_plan(neutral_plan)
    episodes = _episode_map(schedule, material.get("episodes"))
    sources = _source_map(episodes, material.get("sources"))
    _require(
        generation_contract.get("max_tokens") == MAX_OUTPUT_TOKENS
        and generation_contract.get("hidden_retries_permitted") is False,
        "V2_GENERATION_CONTRACT_DRIFT",
        "V2 generation contract drifted",
    )
    _require(
        admission_spec.get("semantic_contract") == "TerminalDecisionOutput",
        "V2_ADMISSION_SPEC_DRIFT",
        "V2 standalone admission semantic contract drifted",
    )
    return {
        "schedule": schedule,
        "neutral_plan": neutral_plan,
        "generation_contract": generation_contract,
        "response_format": response_format,
        "admission_spec": admission_spec,
        "compiler_spec": compiler_spec,
        "trajectories": trajectories,
        "pretreatment_requests": pretreatment_requests,
        "episodes": episodes,
        "sources": sources,
    }


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
            raise V2TransactionRuntimeError(
                "V2_TIMING_METRIC_INVALID",
                "V2 timing metric contains an invalid numeric value",
            )
        totals[name] += value
        seen.add(name)
    return {name: totals[name] for name in seen}


def _timing_delta(before: str, after: str) -> dict[str, float | None]:
    before_values = _prometheus_totals(before)
    after_values = _prometheus_totals(after)
    result: dict[str, float | None] = {}
    for role, candidates in TIMING_CANDIDATES.items():
        observed: list[float] = []
        for name in candidates:
            if name not in before_values or name not in after_values:
                continue
            delta = after_values[name] - before_values[name]
            if delta < 0:
                raise V2TransactionRuntimeError(
                    "V2_TIMING_METRIC_COUNTER_REGRESSION",
                    "V2 timing metric counter regressed",
                )
            if delta > 0:
                observed.append(delta * 1000.0)
        result[role] = observed[0] if len(observed) == 1 else None
    return result


def _worker_identity(worker: Any) -> JsonObject:
    process = getattr(worker, "process", None)
    if process is None or process.poll() is not None:
        raise V2TransactionRuntimeError(
            "V2_WORKER_GENERATION_DRIFT",
            "V2 worker is not live at the frozen generation",
        )
    return {
        "worker_id": getattr(worker, "worker_id", None),
        "generation": getattr(worker, "generation", None),
        "gpu_index": getattr(worker, "gpu_index", None),
        "port": getattr(worker, "port", None),
        "pid": getattr(process, "pid", None),
        "process_start_ticks": getattr(worker, "process_start_ticks", None),
    }


def _freeze_worker_identities(workers: dict[str, Any]) -> dict[str, JsonObject]:
    _require(
        set(workers) == {"worker_1", "worker_2"},
        "V2_WORKER_SET_INVALID",
        "V2 worker set is invalid",
    )
    observed = {worker_id: _worker_identity(worker) for worker_id, worker in workers.items()}
    _require(
        observed["worker_1"].get("gpu_index") == 0
        and observed["worker_1"].get("port") == 8001
        and observed["worker_2"].get("gpu_index") == 1
        and observed["worker_2"].get("port") == 8002
        and observed["worker_1"].get("generation") == 1
        and observed["worker_2"].get("generation") == 1,
        "V2_WORKER_BINDING_DRIFT",
        "V2 worker GPU/port/generation binding drifted",
    )
    return observed


def _assert_workers_frozen(
    workers: dict[str, Any],
    frozen: dict[str, JsonObject],
) -> None:
    current = _freeze_worker_identities(workers)
    if current != frozen:
        raise V2TransactionRuntimeError(
            "V2_WORKER_GENERATION_DRIFT",
            "V2 worker identity changed after qualification",
        )


def _count_and_check(tokenizer: Any, messages: MessageList) -> int:
    count = tokenizer.count(messages)
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
        or count + MAX_OUTPUT_TOKENS > MAX_MODEL_LEN
    ):
        raise V2TransactionRuntimeError(
            "V2_RUNTIME_TOKEN_BUDGET_EXCEEDED",
            "V2 request exceeds the frozen model-length budget",
        )
    return count


def _counted_post_json(
    r2: Namespace,
    request_counts: dict[str, int],
) -> Callable[[str, JsonObject], JsonObject]:
    def post_json(url: str, payload: JsonObject) -> JsonObject:
        response = r2["post_json"](url, payload)
        request_counts["http_completed"] += 1
        return _as_object(
            response,
            "V2_RESPONSE_ENVELOPE_INVALID",
            "V2 loopback transport returned a non-object response",
        )

    return post_json


def _send_with_telemetry(
    *,
    r2: Namespace,
    adapter: Any,
    worker: Any,
    worker_id: str,
    request_id: str,
    messages: MessageList,
    cache_salt: str,
) -> tuple[JsonObject, JsonObject]:
    before_cache = worker.metric_snapshot()
    before_timing = r2["get_text"](f"http://127.0.0.1:{worker.port}/metrics")
    started = time.perf_counter()
    response_raw, receipt = adapter.send(
        request_id=request_id,
        url=f"http://127.0.0.1:{worker.port}/v1/chat/completions",
        messages=messages,
        cache_salt=cache_salt,
    )
    wall_ms = (time.perf_counter() - started) * 1000.0
    after_timing = r2["get_text"](f"http://127.0.0.1:{worker.port}/metrics")
    after_cache = worker.metric_snapshot()
    cache_delta = r2["metric_delta"](before_cache, after_cache)
    timing = _timing_delta(before_timing, after_timing)
    response = _as_object(
        response_raw,
        "V2_RESPONSE_ENVELOPE_INVALID",
        "V2 request adapter returned a non-object response",
    )
    evidence = {
        "request_id": request_id,
        "worker_id": worker_id,
        "worker_generation": getattr(worker, "generation", None),
        "attempt_sequence": getattr(receipt, "attempt_sequence", None),
        "messages_sha256": getattr(receipt, "messages_sha256", None),
        "rendered_prompt_sha256": getattr(receipt, "rendered_prompt_sha256", None),
        "prompt_token_count": getattr(receipt, "prompt_token_count", None),
        "server_usage_prompt_tokens": getattr(receipt, "server_usage_prompt_tokens", None),
        "finish_reason": getattr(receipt, "finish_reason", None),
        "output_sha256": getattr(receipt, "output_sha256", None),
        "cached_prefix_tokens": round(float(cache_delta.local_cache_hit)),
        "newly_computed_prefill_tokens": round(float(cache_delta.newly_computed_prefill_tokens)),
        "external_kv_transfer_tokens": round(float(cache_delta.external_kv_transfer)),
        "prefill_duration_ms": timing["prefill_duration_ms"],
        "time_to_first_token_ms": timing["time_to_first_token_ms"],
        "end_to_end_latency_ms": timing["end_to_end_latency_ms"],
        "wall_clock_end_to_end_ms": wall_ms,
        "http_completed": True,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }
    return response, evidence


def _checkpoint_payload(
    *,
    transaction_id: str,
    phase: str,
    scheduled: int,
    attempted: int,
    http_completed: int,
    admitted: int,
    committed: int,
    detail: JsonObject | None = None,
) -> JsonObject:
    _require(
        scheduled >= attempted >= http_completed >= admitted >= committed >= 0,
        "V2_REQUEST_RECONCILIATION_INVALID",
        "V2 checkpoint request counters violate the monotonic invariant",
    )
    return {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "phase": phase,
        "scheduled_request_count": scheduled,
        "attempted_request_count": attempted,
        "http_completed_request_count": http_completed,
        "admitted_request_count": admitted,
        "committed_request_count": committed,
        "detail": {} if detail is None else detail,
        "raw_prompts_retained": False,
        "raw_outputs_retained": False,
    }


def _write_checkpoint(name: str, payload: JsonObject) -> JsonObject:
    _require(
        re.fullmatch(r"[a-z0-9_]+", name) is not None,
        "V2_CHECKPOINT_NAME_INVALID",
        "V2 checkpoint name is invalid",
    )
    path = CHECKPOINT_ROOT / f"{name}.json"
    _atomic_write_json(path, payload)
    raw = path.read_bytes()
    return {
        "name": name,
        "path": path.relative_to(OUTPUT_ROOT).as_posix(),
        "sha256": sha256_bytes(raw),
        "size_bytes": len(raw),
    }


def _episode_user_message(episode: JsonObject, turn_index: int) -> str:
    turns = episode.get("turns")
    if not isinstance(turns, list) or len(turns) != 4 or turn_index not in {1, 2, 3, 4}:
        raise V2TransactionRuntimeError(
            "V2_PILOT_EPISODE_INVALID",
            "V2 pilot episode turn set is invalid",
        )
    raw = turns[turn_index - 1]
    turn = _as_object(
        raw,
        "V2_PILOT_EPISODE_INVALID",
        "V2 pilot turn is invalid",
    )
    user_message = turn.get("user_message")
    if not isinstance(user_message, str) or not user_message.strip():
        raise V2TransactionRuntimeError(
            "V2_PILOT_EPISODE_INVALID",
            "V2 pilot user message is invalid",
        )
    return user_message


def _run_pretreatment(
    *,
    transaction_id: str,
    r2: Namespace,
    live: Namespace,
    admission: Namespace,
    neutral_plan: JsonObject,
    requests: list[JsonObject],
    static_prompt: str,
    admission_spec: JsonObject,
    workers: dict[str, Any],
    frozen_workers: dict[str, JsonObject],
    tokenizer: Any,
    adapter: Any,
    checkpoint_receipts: list[JsonObject],
    request_counts: dict[str, int],
    ledger: list[JsonObject],
) -> JsonObject:
    samples: list[JsonObject] = []
    for index, request in enumerate(requests):
        _assert_workers_frozen(workers, frozen_workers)
        request_id = request.get("request_id")
        worker_id = request.get("worker_id")
        phase = request.get("phase")
        namespace = request.get("cache_namespace_id")
        if not isinstance(request_id, str):
            raise V2TransactionRuntimeError(
                "V2_PRETREATMENT_REQUEST_INVALID",
                "V2 pre-treatment request ID is invalid",
            )
        if not isinstance(worker_id, str) or worker_id not in workers:
            raise V2TransactionRuntimeError(
                "V2_PRETREATMENT_REQUEST_INVALID",
                "V2 pre-treatment worker identity is invalid",
            )
        if not isinstance(phase, str) or not isinstance(namespace, str):
            raise V2TransactionRuntimeError(
                "V2_PRETREATMENT_REQUEST_INVALID",
                "V2 pre-treatment phase or cache namespace is invalid",
            )
        messages = _as_message_list(
            live["build_neutral_messages"](phase, static_prompt),
            "V2_PRETREATMENT_MESSAGE_INVALID",
            "V2 live neutral-message renderer returned an invalid message list",
        )
        _count_and_check(tokenizer, messages)
        response, evidence = _send_with_telemetry(
            r2=r2,
            adapter=adapter,
            worker=workers[worker_id],
            worker_id=worker_id,
            request_id=request_id,
            messages=messages,
            cache_salt=sha256_text(namespace),
        )
        evidence.update(
            {
                "sequence_index": index,
                "phase": phase,
                "admitted": False,
                "committed": False,
                "admitted_output_sha256": None,
            }
        )
        ledger.append(evidence)
        admitted = admission["admit_response"](response, admission_spec)
        request_counts["admitted"] += 1
        request_counts["committed"] += 1
        evidence.update(
            {
                "admitted": True,
                "committed": True,
                "admitted_output_sha256": sha256_text(admitted.canonical_json),
            }
        )
        if request.get("measured_for_worker_symmetry") is True:
            telemetry_valid = (
                evidence.get("time_to_first_token_ms") is not None
                and evidence.get("prefill_duration_ms") is not None
                and evidence.get("external_kv_transfer_tokens") == 0
            )
            samples.append(
                {
                    "measurement_pair_index": request.get("measurement_pair_index"),
                    "pair_order_index": request.get("pair_order_index"),
                    "worker_id": worker_id,
                    "admitted": True,
                    "telemetry_valid": telemetry_valid,
                    "time_to_first_token_ms": evidence.get("time_to_first_token_ms"),
                    "prefill_duration_ms": evidence.get("prefill_duration_ms"),
                }
            )
        if index == 1:
            checkpoint_receipts.append(
                _write_checkpoint(
                    "schema_canary",
                    _checkpoint_payload(
                        transaction_id=transaction_id,
                        phase="SCHEMA_CANARY_COMPLETE",
                        scheduled=EXPECTED_TOTAL_SCHEDULED_REQUESTS,
                        attempted=adapter.budget.attempted_model_requests,
                        http_completed=request_counts["http_completed"],
                        admitted=request_counts["admitted"],
                        committed=request_counts["committed"],
                        detail={"schema_canary_request_count": 2},
                    ),
                )
            )

    qualification = _as_object(
        live["assess_neutral_worker_qualification"](neutral_plan, samples),
        "V2_NEUTRAL_WORKER_QUALIFICATION_INVALID",
        "V2 neutral worker qualification result is invalid",
    )
    _atomic_write_json(OUTPUT_ROOT / "neutral_worker_qualification_v1.json", qualification)
    checkpoint_receipts.append(
        _write_checkpoint(
            "neutral_qualification",
            _checkpoint_payload(
                transaction_id=transaction_id,
                phase="NEUTRAL_QUALIFICATION_COMPLETE",
                scheduled=EXPECTED_TOTAL_SCHEDULED_REQUESTS,
                attempted=adapter.budget.attempted_model_requests,
                http_completed=request_counts["http_completed"],
                admitted=request_counts["admitted"],
                committed=request_counts["committed"],
                detail={
                    "pretreatment_request_count": len(ledger),
                    "qualification_decision": qualification.get("decision"),
                },
            ),
        )
    )
    _require(
        qualification.get("decision") == "PASS",
        "V2_NEUTRAL_WORKER_QUALIFICATION_FAILED",
        "V2 neutral worker qualification did not pass",
    )
    _assert_workers_frozen(workers, frozen_workers)
    return qualification


def _classify_private_responses(
    responses: list[JsonObject],
    admission: Namespace,
    admission_spec: JsonObject,
) -> list[bool]:
    result: list[bool] = []
    error_type = admission.get("RuntimeOutputAdmissionError")
    for response in responses:
        try:
            admission["admit_response"](response, admission_spec)
        except BaseException as error:
            if isinstance(error_type, type) and isinstance(error, error_type):
                result.append(False)
                continue
            raise
        result.append(True)
    return result


def _update_partial_trajectory_counts(
    *,
    private_responses: list[JsonObject],
    history: JsonHistory,
    admission: Namespace,
    admission_spec: JsonObject,
    request_counts: dict[str, int],
) -> tuple[list[bool], int]:
    _require(
        len(history) % 2 == 0,
        "V2_PILOT_TRAJECTORY_RECONCILIATION_FAILED",
        "V2 pilot history must contain complete user/assistant pairs",
    )
    admitted_flags = _classify_private_responses(private_responses, admission, admission_spec)
    committed = len(history) // 2
    admitted = sum(admitted_flags)
    _require(
        0 <= committed <= admitted <= len(private_responses) <= 4,
        "V2_PILOT_TRAJECTORY_RECONCILIATION_FAILED",
        "V2 pilot partial trajectory counters diverged",
    )
    request_counts["admitted"] += admitted
    request_counts["committed"] += committed
    return admitted_flags, committed


def _run_trajectory(
    *,
    r2: Namespace,
    live: Namespace,
    standalone: Namespace,
    admission: Namespace,
    trajectory: JsonObject,
    episode: JsonObject,
    source_map: dict[str, str],
    static_prompt: str,
    admission_spec: JsonObject,
    workers: dict[str, Any],
    frozen_workers: dict[str, JsonObject],
    tokenizer: Any,
    adapter: Any,
    request_counts: dict[str, int],
) -> JsonObject:
    run_id = trajectory.get("run_id")
    condition_id = trajectory.get("condition_id")
    namespace = trajectory.get("cache_namespace_id")
    realized_route = trajectory.get("realized_route")
    if not isinstance(run_id, str):
        raise V2TransactionRuntimeError(
            "V2_PILOT_TRAJECTORY_INVALID",
            "V2 pilot run identity is invalid",
        )
    if not isinstance(condition_id, str) or condition_id not in {"A", "B", "C"}:
        raise V2TransactionRuntimeError(
            "V2_PILOT_TRAJECTORY_INVALID",
            "V2 pilot condition identity is invalid",
        )
    if not isinstance(namespace, str):
        raise V2TransactionRuntimeError(
            "V2_PILOT_TRAJECTORY_INVALID",
            "V2 pilot cache namespace is invalid",
        )
    if (
        not isinstance(realized_route, list)
        or len(realized_route) != 4
        or any(
            not isinstance(item, str) or item not in {"worker_1", "worker_2"}
            for item in realized_route
        )
    ):
        raise V2TransactionRuntimeError(
            "V2_PILOT_TRAJECTORY_INVALID",
            "V2 pilot realized route is invalid",
        )
    route = cast(list[str], realized_route)
    runtime_request_type = standalone["RuntimeTurnRequest"]
    requests = tuple(
        runtime_request_type(
            request_id=f"{run_id}-turn-{turn_index}",
            user_content=_episode_user_message(episode, turn_index),
            worker_id=route[turn_index - 1],
        )
        for turn_index in range(1, 5)
    )
    request_index = {request.request_id: index for index, request in enumerate(requests, start=1)}
    history: JsonHistory = []
    transport_records: list[JsonObject] = []
    private_responses: list[JsonObject] = []
    cache_salt = sha256_text(namespace)

    def render_messages(request: Any, current_history: JsonHistory) -> MessageList:
        turn_index = request_index.get(request.request_id)
        _require(
            turn_index is not None and request.worker_id == route[turn_index - 1],
            "V2_PILOT_REALIZED_ROUTE_DRIFT",
            "V2 pilot runtime request diverged from the committed realized route",
        )
        return _as_message_list(
            live["build_pilot_messages"](
                condition_id=condition_id,
                static_prompt=static_prompt,
                episode=episode,
                source_map=source_map,
                turn_index=turn_index,
                history=current_history,
            ),
            "V2_PILOT_MESSAGE_INVALID",
            "V2 live pilot-message renderer returned an invalid message list",
        )

    def send_response(request: Any, messages: MessageList) -> JsonObject:
        _assert_workers_frozen(workers, frozen_workers)
        worker_id = request.worker_id
        _require(
            worker_id in workers,
            "V2_PILOT_REALIZED_ROUTE_DRIFT",
            "V2 pilot request references an unknown realized worker",
        )
        response, evidence = _send_with_telemetry(
            r2=r2,
            adapter=adapter,
            worker=workers[worker_id],
            worker_id=worker_id,
            request_id=request.request_id,
            messages=messages,
            cache_salt=cache_salt,
        )
        transport_records.append(evidence)
        private_responses.append(response)
        return response

    try:
        result = standalone["execute_trajectory"](
            requests=requests,
            history=history,
            admission_spec=admission_spec,
            render_messages=render_messages,
            token_counter=tokenizer.count,
            send_response=send_response,
        )
    except BaseException:
        _update_partial_trajectory_counts(
            private_responses=private_responses,
            history=history,
            admission=admission,
            admission_spec=admission_spec,
            request_counts=request_counts,
        )
        raise
    attempted = int(result.request_attempt_count)
    admitted_flags, committed = _update_partial_trajectory_counts(
        private_responses=private_responses,
        history=history,
        admission=admission,
        admission_spec=admission_spec,
        request_counts=request_counts,
    )
    _require(
        attempted == len(transport_records) == len(private_responses)
        and committed == int(result.completed_turn_count)
        and 0 <= committed <= attempted <= 4,
        "V2_PILOT_TRAJECTORY_RECONCILIATION_FAILED",
        "V2 pilot trajectory request/history counters diverged",
    )
    admitted = sum(admitted_flags)
    turn_records: list[JsonObject] = []
    for index, evidence in enumerate(transport_records):
        turn_index = index + 1
        is_admitted = admitted_flags[index]
        is_committed = turn_index <= committed
        row = dict(evidence)
        row.update(
            {
                "turn_index": turn_index,
                "scheduled_worker_id": route[index],
                "admitted": is_admitted,
                "committed": is_committed,
                "failure_code": (
                    result.failure_code
                    if result.failed and index == attempted - 1 and not is_committed
                    else None
                ),
            }
        )
        turn_records.append(row)
    return {
        "schema_version": "1.0.0",
        "schedule_index": trajectory.get("schedule_index"),
        "comparison_pair_id": trajectory.get("comparison_pair_id"),
        "comparison_pair_index": trajectory.get("comparison_pair_index"),
        "run_id": run_id,
        "episode_id": trajectory.get("episode_id"),
        "pilot_replication_id": trajectory.get("pilot_replication_id"),
        "worker_orientation": trajectory.get("worker_orientation"),
        "condition_id": condition_id,
        "realized_route": route,
        "cache_namespace_sha256": sha256_text(namespace),
        "scheduled_turn_count": 4,
        "attempted_request_count": attempted,
        "http_completed_request_count": len(transport_records),
        "admitted_request_count": admitted,
        "committed_turn_count": committed,
        "trajectory_failed": bool(result.failed),
        "failure_code": result.failure_code,
        "turns": turn_records,
        "raw_prompts_retained": False,
        "raw_outputs_retained": False,
    }


def reconcile_requests(
    *,
    adapter_attempted: int,
    pretreatment_ledger: list[JsonObject],
    trajectories: list[JsonObject],
) -> JsonObject:
    attempted = adapter_attempted
    http_completed = len(pretreatment_ledger) + sum(
        _request_count(item, "http_completed_request_count") for item in trajectories
    )
    admitted = len(pretreatment_ledger) + sum(
        _request_count(item, "admitted_request_count") for item in trajectories
    )
    committed = len(pretreatment_ledger) + sum(
        _request_count(item, "committed_turn_count") for item in trajectories
    )
    _require(
        EXPECTED_TOTAL_SCHEDULED_REQUESTS
        >= attempted
        >= http_completed
        >= admitted
        >= committed
        >= 0,
        "V2_REQUEST_RECONCILIATION_FAILED",
        "V2 terminal request counters violate the monotonic invariant",
    )
    skipped_by_failure: dict[str, int] = {}
    admission_failures = 0
    admitted_not_committed = 0
    prospective_rejections = 0
    for trajectory in trajectories:
        scheduled = _request_count(trajectory, "scheduled_turn_count")
        observed_attempts = _request_count(trajectory, "attempted_request_count")
        failure_code = trajectory.get("failure_code")
        skipped = scheduled - observed_attempts
        if skipped > 0:
            key = str(failure_code or "UNKNOWN_TRAJECTORY_FAILURE")
            skipped_by_failure[key] = skipped_by_failure.get(key, 0) + skipped
        admission_failures += _request_count(
            trajectory, "http_completed_request_count"
        ) - _request_count(trajectory, "admitted_request_count")
        gap = _request_count(trajectory, "admitted_request_count") - _request_count(
            trajectory, "committed_turn_count"
        )
        admitted_not_committed += gap
        if trajectory.get("failure_code") == "V2_RUNTIME_REACHABLE_PROMPT_BUDGET_REJECTED":
            prospective_rejections += gap
    _require(
        attempted - http_completed == 0,
        "V2_REQUEST_RECONCILIATION_FAILED",
        "completed runtime reached terminal reconciliation with an unaccounted transport attempt",
    )
    return {
        "schema_version": "1.0.0",
        "scheduled_request_count": EXPECTED_TOTAL_SCHEDULED_REQUESTS,
        "attempted_request_count": attempted,
        "http_completed_request_count": http_completed,
        "admitted_request_count": admitted,
        "committed_request_count": committed,
        "scheduled_minus_attempted": EXPECTED_TOTAL_SCHEDULED_REQUESTS - attempted,
        "attempted_minus_http_completed": attempted - http_completed,
        "http_completed_minus_admitted": http_completed - admitted,
        "admitted_minus_committed": admitted - committed,
        "skipped_later_turns_by_failure_code": skipped_by_failure,
        "output_admission_failure_count": admission_failures,
        "admitted_not_committed_count": admitted_not_committed,
        "prospective_reachable_budget_rejection_count": prospective_rejections,
        "hidden_retry_count": 0,
        "replacement_case_count": 0,
        "monotonic_invariant_satisfied": True,
    }


def _bundle(transaction_id: str, runtime_sha256: str) -> JsonObject:
    members: list[JsonObject] = []
    paths: list[Path] = []
    for name in PUBLIC_OUTPUT_NAMES:
        if name == "bundle_manifest_v1.json":
            continue
        path = OUTPUT_ROOT / name
        if path.is_file():
            paths.append(path)
    if CHECKPOINT_ROOT.is_dir():
        paths.extend(sorted(CHECKPOINT_ROOT.glob("*.json")))
    for path in sorted(set(paths), key=lambda item: item.as_posix()):
        payload = path.read_bytes()
        members.append(
            {
                "path": path.relative_to(OUTPUT_ROOT).as_posix(),
                "sha256": sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "runtime_payload_sha256": runtime_sha256,
        "member_count": len(members),
        "members": members,
        "raw_prompts_included": False,
        "raw_outputs_included": False,
        "raw_source_documents_included": False,
        "credentials_included": False,
    }
    _atomic_write_json(OUTPUT_ROOT / "bundle_manifest_v1.json", manifest)
    with zipfile.ZipFile(EVIDENCE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [*paths, OUTPUT_ROOT / "bundle_manifest_v1.json"]:
            if path.is_file():
                archive.write(path, arcname=path.relative_to(OUTPUT_ROOT).as_posix())
    zip_size = EVIDENCE_ZIP.stat().st_size
    _require(
        zip_size <= MAX_EVIDENCE_ZIP_BYTES,
        "V2_EVIDENCE_BUNDLE_TOO_LARGE",
        "V2 evidence bundle exceeds the bounded size limit",
    )
    return {
        "evidence_zip": EVIDENCE_ZIP.name,
        "evidence_zip_sha256": sha256_bytes(EVIDENCE_ZIP.read_bytes()),
        "evidence_zip_size_bytes": zip_size,
        "bundle_manifest_sha256": sha256_bytes(
            (OUTPUT_ROOT / "bundle_manifest_v1.json").read_bytes()
        ),
    }


def main() -> int:
    transaction_id, runtime_sha256 = _transaction_context()
    r2 = _injected_namespace("AURAGATEWAY_R2_RUNTIME")
    live = _injected_namespace("AURAGATEWAY_V2_LIVE_SEMANTICS")
    adapter_ns = _injected_namespace("AURAGATEWAY_V2_REQUEST_ADAPTER")
    standalone = _injected_namespace("AURAGATEWAY_V2_STANDALONE_RUNTIME")
    admission = _injected_namespace("AURAGATEWAY_V2_OUTPUT_ADMISSION_RUNTIME")
    material = validate_material(_material())

    if OUTPUT_ROOT.exists() or SCRATCH_ROOT.exists() or EVIDENCE_ZIP.exists():
        raise V2TransactionRuntimeError(
            "V2_TRANSACTION_WORKSPACE_NOT_FRESH",
            "V2 transaction output, scratch, or evidence path already exists",
        )
    OUTPUT_ROOT.mkdir(parents=True)
    _configure_reused_runtime(r2)

    counters = {
        "runtime_install_attempts": 0,
        "runtime_import_closure_probes": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
    }
    workers: dict[str, Any] = {}
    tokenizer: Any | None = None
    checkpoint_receipts: list[JsonObject] = []
    primary_error: BaseException | None = None
    teardown_errors: list[JsonObject] = []
    cleanup_error: BaseException | None = None
    pretreatment_ledger: list[JsonObject] = []
    pilot_ledger: list[JsonObject] = []
    budget: Any | None = None
    request_counts = {"http_completed": 0, "admitted": 0, "committed": 0}

    try:
        r2["require_private_environment"]()
        wheelhouse = r2["discover_one_directory"](r2["RUNTIME_OUTPUT_DIRECTORY"])
        r2["validate_wheelhouse"](wheelhouse)
        source_snapshot = r2["discover_model_snapshot"]()
        r2["install_runtime"](wheelhouse, counters)
        r2["validate_target_runtime"]()
        r2["validate_process_tree_import_closure"](counters)
        model_home, snapshot = r2["prepare_model_home"](source_snapshot)

        workers = {
            "worker_1": r2["Worker"]("worker_1", 0, 8001, model_home, snapshot, generation=1),
            "worker_2": r2["Worker"]("worker_2", 1, 8002, model_home, snapshot, generation=1),
        }
        for worker_id in ("worker_1", "worker_2"):
            worker = workers[worker_id]
            worker.start(counters)
            worker.wait_ready()
            worker.validate_model()
            worker.wait_backend_marker()
        frozen_workers = _freeze_worker_identities(workers)

        tokenizer = adapter_ns["AcceptedTokenizerSidecar"](TARGET_PYTHON, snapshot)
        budget = adapter_ns["RequestBudget"](
            maximum_total_model_requests=EXPECTED_TOTAL_SCHEDULED_REQUESTS
        )
        adapter = adapter_ns["OneShotVllmRequestAdapter"](
            tokenizer=tokenizer,
            post_json=_counted_post_json(r2, request_counts),
            generation_contract=material["generation_contract"],
            response_format=material["response_format"],
            budget=budget,
        )
        static_prompt = live["build_static_system_prompt"](
            material["compiler_spec"], material["admission_spec"]
        )
        _atomic_write_json(
            OUTPUT_ROOT / "runtime_binding_report_v1.json",
            {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "runtime_payload_sha256": runtime_sha256,
                "worker_identities": frozen_workers,
                "request_budget": EXPECTED_TOTAL_SCHEDULED_REQUESTS,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "max_model_len": MAX_MODEL_LEN,
                "realized_route_is_schedule_authority": True,
                "route_reconstruction_permitted": False,
                "hidden_retry_count": 0,
                "replacement_case_count": 0,
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            },
        )

        qualification = _run_pretreatment(
            transaction_id=transaction_id,
            r2=r2,
            live=live,
            admission=admission,
            neutral_plan=cast(JsonObject, material["neutral_plan"]),
            requests=cast(list[JsonObject], material["pretreatment_requests"]),
            static_prompt=static_prompt,
            admission_spec=cast(JsonObject, material["admission_spec"]),
            workers=workers,
            frozen_workers=frozen_workers,
            tokenizer=tokenizer,
            adapter=adapter,
            checkpoint_receipts=checkpoint_receipts,
            request_counts=request_counts,
            ledger=pretreatment_ledger,
        )
        _atomic_write_json(
            OUTPUT_ROOT / "pretreatment_ledger_v1.json",
            {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "scheduled_request_count": EXPECTED_PRETREATMENT_REQUEST_COUNT,
                "attempted_request_count": len(pretreatment_ledger),
                "admitted_request_count": len(pretreatment_ledger),
                "qualification_decision": qualification.get("decision"),
                "requests": pretreatment_ledger,
            },
        )

        trajectories = cast(list[JsonObject], material["trajectories"])
        episodes = cast(dict[str, JsonObject], material["episodes"])
        sources = cast(dict[str, str], material["sources"])
        for index, trajectory in enumerate(trajectories):
            _assert_workers_frozen(workers, frozen_workers)
            episode_id = trajectory.get("episode_id")
            if not isinstance(episode_id, str) or episode_id not in episodes:
                raise V2TransactionRuntimeError(
                    "V2_PILOT_EPISODE_INVALID",
                    "V2 pilot trajectory references an unknown episode",
                )
            row = _run_trajectory(
                r2=r2,
                live=live,
                standalone=standalone,
                admission=admission,
                trajectory=trajectory,
                episode=episodes[episode_id],
                source_map=sources,
                static_prompt=static_prompt,
                admission_spec=cast(JsonObject, material["admission_spec"]),
                workers=workers,
                frozen_workers=frozen_workers,
                tokenizer=tokenizer,
                adapter=adapter,
                request_counts=request_counts,
            )
            pilot_ledger.append(row)
            if (index + 1) % 3 == 0:
                pair_index = index // 3
                cumulative_http = request_counts["http_completed"]
                cumulative_admitted = request_counts["admitted"]
                cumulative_committed = request_counts["committed"]
                checkpoint_receipts.append(
                    _write_checkpoint(
                        f"comparison_pair_{pair_index + 1:02d}",
                        _checkpoint_payload(
                            transaction_id=transaction_id,
                            phase="COMPARISON_TRIO_COMPLETE",
                            scheduled=EXPECTED_TOTAL_SCHEDULED_REQUESTS,
                            attempted=budget.attempted_model_requests,
                            http_completed=cumulative_http,
                            admitted=cumulative_admitted,
                            committed=cumulative_committed,
                            detail={
                                "comparison_pair_index": pair_index,
                                "comparison_pair_id": trajectory.get("comparison_pair_id"),
                                "trajectory_count_completed": len(pilot_ledger),
                            },
                        ),
                    )
                )

        _atomic_write_json(
            OUTPUT_ROOT / "pilot_trajectory_ledger_v1.json",
            {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "scheduled_trajectory_count": EXPECTED_TRAJECTORY_COUNT,
                "scheduled_turn_count": EXPECTED_PILOT_TURN_COUNT,
                "trajectories": pilot_ledger,
                "hidden_retry_count": 0,
                "replacement_case_count": 0,
            },
        )
        reconciliation = reconcile_requests(
            adapter_attempted=budget.attempted_model_requests,
            pretreatment_ledger=pretreatment_ledger,
            trajectories=pilot_ledger,
        )
        _require(
            reconciliation["http_completed_request_count"] == request_counts["http_completed"]
            and reconciliation["admitted_request_count"] == request_counts["admitted"]
            and reconciliation["committed_request_count"] == request_counts["committed"],
            "V2_REQUEST_RECONCILIATION_FAILED",
            "V2 shared request counters diverged from the terminal ledgers",
        )
        _atomic_write_json(OUTPUT_ROOT / "request_reconciliation_v1.json", reconciliation)
        _atomic_write_json(
            OUTPUT_ROOT / "runtime_summary_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "PASSED_PENDING_REPOSITORY_ACCEPTANCE",
                "transaction_id": transaction_id,
                "pretreatment_qualification": qualification.get("decision"),
                "scheduled_trajectory_count": EXPECTED_TRAJECTORY_COUNT,
                "observed_trajectory_count": len(pilot_ledger),
                "failed_trajectory_count": sum(
                    bool(item.get("trajectory_failed")) for item in pilot_ledger
                ),
                "request_reconciliation": reconciliation,
                "pilot_execution_authorized_at_runtime": True,
                "pilot_repository_acceptance_established": False,
                "final_measured_abc_execution_authorized": False,
                "effect_claims_permitted": False,
                "raw_prompts_retained": False,
                "raw_outputs_retained": False,
                "customer_data_used": False,
                "external_network_requests": 0,
                "external_spend": 0,
            },
        )
        _atomic_write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "NO_PRIMARY_RUNTIME_FAILURE",
                "transaction_id": transaction_id,
                "primary_failure": False,
                "cleanup_failure": False,
            },
        )
    except BaseException as error:
        primary_error = error
        attempted = 0 if budget is None else int(budget.attempted_model_requests)
        http_completed = request_counts["http_completed"]
        admitted_count = request_counts["admitted"]
        committed_count = request_counts["committed"]
        try:
            checkpoint_receipts.append(
                _write_checkpoint(
                    "primary_failure",
                    _checkpoint_payload(
                        transaction_id=transaction_id,
                        phase="PRIMARY_FATAL_FAILURE",
                        scheduled=EXPECTED_TOTAL_SCHEDULED_REQUESTS,
                        attempted=attempted,
                        http_completed=http_completed,
                        admitted=admitted_count,
                        committed=committed_count,
                        detail={
                            "exception_type": type(error).__name__,
                            "error_code": getattr(
                                error, "error_code", getattr(error, "code", None)
                            ),
                            "safe_message": _safe_message(error),
                        },
                    ),
                )
            )
        except BaseException as checkpoint_error:
            teardown_errors.append(
                {
                    "phase": "primary_failure_checkpoint",
                    "exception_type": type(checkpoint_error).__name__,
                    "safe_message": _safe_message(checkpoint_error),
                }
            )
        if pretreatment_ledger and not (OUTPUT_ROOT / "pretreatment_ledger_v1.json").is_file():
            _atomic_write_json(
                OUTPUT_ROOT / "pretreatment_ledger_v1.json",
                {
                    "schema_version": "1.0.0",
                    "transaction_id": transaction_id,
                    "status": "PARTIAL_PRIMARY_FAILURE",
                    "requests": pretreatment_ledger,
                },
            )
        if pilot_ledger and not (OUTPUT_ROOT / "pilot_trajectory_ledger_v1.json").is_file():
            _atomic_write_json(
                OUTPUT_ROOT / "pilot_trajectory_ledger_v1.json",
                {
                    "schema_version": "1.0.0",
                    "transaction_id": transaction_id,
                    "status": "PARTIAL_PRIMARY_FAILURE",
                    "trajectories": pilot_ledger,
                },
            )
        _atomic_write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "PRIMARY_RUNTIME_FAILURE",
                "transaction_id": transaction_id,
                "primary_failure": True,
                "primary_exception_type": type(error).__name__,
                "primary_error_code": getattr(error, "error_code", getattr(error, "code", None)),
                "primary_safe_message": _safe_message(error),
                "cleanup_failure": False,
            },
        )
    finally:
        if tokenizer is not None:
            try:
                tokenizer_exit = tokenizer.close()
                if tokenizer_exit not in {0, None}:
                    raise V2TransactionRuntimeError(
                        "V2_TOKENIZER_SIDECAR_TEARDOWN_FAILED",
                        "V2 tokenizer sidecar returned nonzero during teardown",
                    )
            except BaseException as error:
                teardown_errors.append(
                    {
                        "phase": "tokenizer_sidecar",
                        "exception_type": type(error).__name__,
                        "safe_message": _safe_message(error),
                    }
                )
        worker_reports: list[JsonObject] = []
        for worker_id in ("worker_2", "worker_1"):
            worker = workers.get(worker_id)
            if worker is None:
                continue
            try:
                report = _as_object(
                    worker.stop_and_report("variance_pilot_v2_complete"),
                    "V2_WORKER_TEARDOWN_FAILED",
                    "V2 worker teardown report is invalid",
                )
                worker_reports.append(report)
                if report.get("status") not in {"PASSED", "NOT_STARTED"}:
                    teardown_errors.append(
                        {
                            "phase": "worker_teardown",
                            "worker_id": worker_id,
                            "exception_type": "WorkerTeardownStatus",
                            "safe_message": "V2 worker teardown did not pass",
                        }
                    )
            except BaseException as error:
                teardown_errors.append(
                    {
                        "phase": "worker_teardown",
                        "worker_id": worker_id,
                        "exception_type": type(error).__name__,
                        "safe_message": _safe_message(error),
                    }
                )
        _atomic_write_json(
            OUTPUT_ROOT / "worker_teardown_report_v1.json",
            {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "worker_report_count": len(worker_reports),
                "reports": worker_reports,
                "teardown_errors": teardown_errors,
            },
        )
        try:
            cleanup = _as_object(
                r2["cleanup_scratch"](),
                "V2_SCRATCH_CLEANUP_FAILED",
                "V2 scratch cleanup report is invalid",
            )
        except BaseException as error:
            cleanup_error = error
            cleanup = {
                "schema_version": "1.0.0",
                "status": "FAILED",
                "exception_type": type(error).__name__,
                "safe_message": _safe_message(error),
            }
        _atomic_write_json(OUTPUT_ROOT / "scratch_cleanup_report_v1.json", cleanup)
        cleanup_failed = bool(teardown_errors) or cleanup.get("status") == "FAILED"
        attempted = 0 if budget is None else int(budget.attempted_model_requests)
        http_completed = request_counts["http_completed"]
        admitted_count = request_counts["admitted"]
        committed_count = request_counts["committed"]
        try:
            checkpoint_receipts.append(
                _write_checkpoint(
                    "teardown",
                    _checkpoint_payload(
                        transaction_id=transaction_id,
                        phase="TEARDOWN_COMPLETE",
                        scheduled=EXPECTED_TOTAL_SCHEDULED_REQUESTS,
                        attempted=attempted,
                        http_completed=http_completed,
                        admitted=admitted_count,
                        committed=committed_count,
                        detail={
                            "worker_report_count": len(worker_reports),
                            "teardown_error_count": len(teardown_errors),
                            "scratch_cleanup_status": cleanup.get("status"),
                        },
                    ),
                )
            )
        except BaseException as error:
            teardown_errors.append(
                {
                    "phase": "teardown_checkpoint",
                    "exception_type": type(error).__name__,
                    "safe_message": _safe_message(error),
                }
            )
            cleanup_failed = True
        _atomic_write_json(
            OUTPUT_ROOT / "checkpoint_manifest_v1.json",
            {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "checkpoint_count": len(checkpoint_receipts),
                "checkpoints": checkpoint_receipts,
            },
        )
        if primary_error is not None or cleanup_failed:
            _atomic_write_json(
                OUTPUT_ROOT / "failure_report_v1.json",
                {
                    "schema_version": "1.0.0",
                    "status": (
                        "PRIMARY_AND_CLEANUP_FAILURE"
                        if primary_error is not None and cleanup_failed
                        else "PRIMARY_RUNTIME_FAILURE"
                        if primary_error is not None
                        else "CLEANUP_FAILURE"
                    ),
                    "transaction_id": transaction_id,
                    "primary_failure": primary_error is not None,
                    "primary_exception_type": (
                        None if primary_error is None else type(primary_error).__name__
                    ),
                    "primary_error_code": (
                        None
                        if primary_error is None
                        else getattr(
                            primary_error,
                            "error_code",
                            getattr(primary_error, "code", None),
                        )
                    ),
                    "primary_safe_message": (
                        None if primary_error is None else _safe_message(primary_error)
                    ),
                    "cleanup_failure": cleanup_failed,
                    "cleanup_error_count": len(teardown_errors)
                    + (1 if cleanup_error is not None else 0),
                    "cleanup_errors": teardown_errors,
                },
            )
        bundle = _bundle(transaction_id, runtime_sha256)
        print("EVIDENCE_ZIP_SHA256=" + str(bundle["evidence_zip_sha256"]))
        print("TRANSACTION_ID=" + transaction_id)
        print(
            "EXECUTION_OUTCOME="
            + ("PASSED" if primary_error is None and not cleanup_failed else "FAILED")
        )

    if primary_error is not None:
        raise primary_error
    if teardown_errors:
        raise V2TransactionRuntimeError(
            "V2_TEARDOWN_FAILED",
            "V2 transaction teardown failed after primary execution completed",
        )
    if cleanup_error is not None:
        raise cleanup_error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
