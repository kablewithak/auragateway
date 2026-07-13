"""Bounded live development-only A/B/C execution with append-only evidence."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
from collections import Counter
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from auragateway.benchmark.smoke import execution_manifest_canonical_sha256, sha256_file
from auragateway.context.compiler import canonical_json_bytes
from auragateway.contracts.benchmark_execution import (
    LiveAttemptRecord,
    LiveDevelopmentAuthorization,
    LiveDevelopmentReport,
    LiveExecutionFailureCode,
    LiveJournalAttemptEvent,
    LiveJournalEvent,
    LiveJournalTerminalEvent,
    LiveResponseCertainty,
    LiveRunRecordSet,
    LiveTerminalRecord,
)
from auragateway.contracts.benchmark_smoke import (
    Gate9ManifestProjection,
    Gate10ManifestProjection,
    SmokePlanLedgerProjection,
    SmokePlanRunProjection,
)
from auragateway.contracts.episodes import (
    AnswerDecisionOutput,
    BenchmarkEpisode,
    EscalateDecisionOutput,
    FunctionalEpisodeSet,
    TerminalDecisionOutput,
)
from auragateway.contracts.evidence_bundle import BenchmarkCondition, RunTerminalStatus
from auragateway.contracts.prefix import StaticCompilerSpec
from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderInvocationStatus,
    ProviderName,
)
from auragateway.providers.base import (
    LiveProviderAdapter,
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderPrompt,
)
from auragateway.telemetry.normalize import normalize_telemetry

_GATE10_MANIFEST_PATH = Path("data/evals/benchmark/freeze-v1/manifest.json")
_EXECUTION_MANIFEST_PATH = Path("data/evals/benchmark/freeze-v1/execution_manifest.json")
_GATE9_MANIFEST_PATH = Path("data/evals/benchmark/preflight-v1/manifest.json")
_PLAN_PATH = Path("data/evals/benchmark/preflight-v1/planned_run_ledger.json")
_EPISODE_SET_PATH = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
_COMPILER_SPEC_PATH = Path("data/context/compiler_spec.json")
_SOURCE_MANIFEST_PATH = Path("data/corpus/source_manifest.json")
_PRICING_SCHEDULE_PATH = Path("data/evals/benchmark/freeze-v1/pricing_schedule.json")
_HMAC_KEY_ENV = "AURAGATEWAY_PREFIX_HMAC_KEY"
_HMAC_KEY_ID_ENV = "AURAGATEWAY_PREFIX_HMAC_KEY_ID"
_TERMINAL_OUTPUT_ADAPTER: TypeAdapter[TerminalDecisionOutput] = TypeAdapter(TerminalDecisionOutput)
_SYSTEMIC_ERROR_CODES = {
    ProviderErrorCode.AUTHENTICATION_FAILED,
    ProviderErrorCode.PERMISSION_DENIED,
    ProviderErrorCode.MODEL_NOT_AVAILABLE,
    ProviderErrorCode.SDK_UNAVAILABLE,
    ProviderErrorCode.CONFIGURATION_MISMATCH,
}
_DEFINITE_RETRYABLE_CODES = {
    ProviderErrorCode.RATE_LIMITED,
    ProviderErrorCode.UNAVAILABLE,
    ProviderErrorCode.CONNECTION_FAILED,
}


class LiveExecutionError(Exception):
    """Expected live-development failure with metadata-safe details."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class _SourceArtifact(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    source_id: str
    document_path: str
    byte_count: int = Field(gt=0)
    sha256: str


class _SourceManifest(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    status: str
    artifacts: tuple[_SourceArtifact, ...] = Field(min_length=1)


class _PricingSchedule(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    pricing_schedule_id: str
    provider_name: str
    provider_model_alias: str
    exact_model_identifier: str
    currency: str
    uncached_input_usd_per_million_tokens: Decimal
    cached_input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal
    maximum_input_tokens_per_attempt: int
    maximum_output_tokens_per_attempt: int


class _ProtectedOutputRecord(BaseModel):
    """Protected local record. This model must never be written below data/."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    attempt_id: str
    run_id: str
    turn_index: int
    output_sha256: str
    raw_output: str


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_REQUIRED_ASSET_MISSING",
            "A required live-development asset was not found.",
            str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_INVALID_JSON",
            "A live-development asset is not valid JSON.",
            str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_ASSET_VALIDATION_FAILED",
            "A live-development asset failed typed validation.",
            str(path),
            details,
        ) from exc


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _opaque_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:24]}"


def _load_hmac_settings() -> tuple[bytes, str]:
    key_value = os.environ.get(_HMAC_KEY_ENV)
    key_id = os.environ.get(_HMAC_KEY_ID_ENV)
    if key_value is None or key_id is None:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PREFIX_HMAC_SETTINGS_MISSING",
            "Prefix HMAC key and non-secret key ID must be supplied through environment settings.",
        )
    key = key_value.encode("utf-8")
    if len(key) < 32:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PREFIX_HMAC_KEY_TOO_SHORT",
            "Prefix HMAC key must contain at least 32 UTF-8 bytes.",
        )
    if not key_id.strip():
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PREFIX_HMAC_KEY_ID_INVALID",
            "Prefix HMAC key ID must not be blank.",
        )
    return key, key_id


def _verify_file_hash(repo_root: Path, relative_path: Path, expected: str, code: str) -> None:
    path = repo_root / relative_path
    if sha256_file(path) != expected:
        raise LiveExecutionError(
            code,
            "A frozen live-development dependency no longer matches its authorized bytes.",
            str(path),
        )


def validate_live_upstream(
    repo_root: Path,
    authorization: LiveDevelopmentAuthorization,
) -> tuple[
    tuple[SmokePlanRunProjection, ...],
    dict[str, BenchmarkEpisode],
    StaticCompilerSpec,
    _SourceManifest,
    _PricingSchedule,
]:
    """Verify every frozen dependency and return only the authorized development scope."""

    _verify_file_hash(
        repo_root,
        _GATE10_MANIFEST_PATH,
        authorization.gate10_manifest_sha256,
        "LIVE_DEVELOPMENT_GATE10_MANIFEST_MISMATCH",
    )
    gate10 = _load_model(repo_root / _GATE10_MANIFEST_PATH, Gate10ManifestProjection)
    if not gate10.gate_10_passed or gate10.execution_enabled:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_GATE10_STATE_INVALID",
            "Gate 10 must pass while full measured execution remains disabled.",
            str(repo_root / _GATE10_MANIFEST_PATH),
        )
    if gate10.measured_execution_permitted:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_GATE10_MEASURED_EXECUTION_UNSAFE",
            "The frozen Gate 10 state may not authorize measured execution for this pilot.",
        )

    execution_path = repo_root / gate10.execution_manifest_path
    if sha256_file(execution_path) != gate10.execution_manifest_file_sha256:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_EXECUTION_MANIFEST_FILE_MISMATCH",
            "Frozen execution-manifest file bytes do not match Gate 10.",
            str(execution_path),
        )
    execution_payload = _load_json(execution_path)
    if not isinstance(execution_payload, dict):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_EXECUTION_MANIFEST_INVALID",
            "Frozen execution manifest must be a JSON object.",
            str(execution_path),
        )
    canonical = execution_manifest_canonical_sha256(execution_payload)
    if canonical != gate10.execution_manifest_canonical_sha256:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_EXECUTION_MANIFEST_CANONICAL_MISMATCH",
            "Frozen execution-manifest canonical digest does not reproduce.",
            str(execution_path),
        )
    if canonical != authorization.execution_manifest_sha256:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_AUTHORIZATION_MANIFEST_MISMATCH",
            "Live authorization targets a different execution manifest.",
            str(execution_path),
        )
    identity = execution_payload.get("identity")
    assets = execution_payload.get("assets")
    if not isinstance(identity, dict) or not isinstance(assets, dict):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_EXECUTION_MANIFEST_INVALID",
            "Frozen execution manifest identity or assets are missing.",
            str(execution_path),
        )
    if identity.get("execution_manifest_status") != "frozen":
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_EXECUTION_MANIFEST_NOT_FROZEN",
            "Live development requires a frozen execution manifest.",
        )
    if identity.get("execution_enabled") is not False:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_FULL_EXECUTION_ENABLEMENT_UNSAFE",
            "Full benchmark execution must remain disabled during the development pilot.",
        )
    expected_provider = (
        assets.get("primary_provider"),
        assets.get("provider_model_alias"),
        assets.get("provider_adapter_version"),
    )
    authorized_provider = (
        authorization.provider.value,
        authorization.provider_model_alias,
        authorization.provider_adapter_version,
    )
    if expected_provider != authorized_provider:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PROVIDER_IDENTITY_MISMATCH",
            "Authorization provider identity differs from the frozen execution manifest.",
        )

    _verify_file_hash(
        repo_root,
        _GATE9_MANIFEST_PATH,
        authorization.gate9_manifest_sha256,
        "LIVE_DEVELOPMENT_GATE9_MANIFEST_MISMATCH",
    )
    gate9 = _load_model(repo_root / _GATE9_MANIFEST_PATH, Gate9ManifestProjection)
    if not gate9.planning_ready or gate9.execution_enabled or gate9.measured_execution_permitted:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_GATE9_STATE_INVALID",
            "Gate 9 must remain planning-ready and non-executing for the development pilot.",
        )
    if gate9.plan_sha256 != authorization.planned_run_ledger_sha256:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PLAN_AUTHORIZATION_MISMATCH",
            "Gate 9 plan identity differs from the live authorization.",
        )
    _verify_file_hash(
        repo_root,
        _PLAN_PATH,
        authorization.planned_run_ledger_sha256,
        "LIVE_DEVELOPMENT_PLAN_FILE_MISMATCH",
    )
    plan = _load_model(repo_root / _PLAN_PATH, SmokePlanLedgerProjection)

    _verify_file_hash(
        repo_root,
        _EPISODE_SET_PATH,
        authorization.functional_episode_set_sha256,
        "LIVE_DEVELOPMENT_EPISODE_SET_MISMATCH",
    )
    episode_set = _load_model(repo_root / _EPISODE_SET_PATH, FunctionalEpisodeSet)
    episodes = {item.episode_id: item for item in episode_set.episodes}
    for episode_id in authorization.allowed_episode_ids:
        episode = episodes.get(episode_id)
        if episode is None or episode.evaluation_split.value != "development":
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_HELD_OUT_EPISODE_BLOCKED",
                "The live pilot may use authorized development episodes only.",
                details=(episode_id,),
            )

    selected = tuple(item for item in plan.runs if item.run_id in authorization.allowed_run_ids)
    if tuple(item.run_id for item in selected) != authorization.allowed_run_ids:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_RUN_ORDER_MISMATCH",
            "Authorized runs must exist exactly once and preserve frozen plan order.",
        )
    if len(selected) != authorization.maximum_run_count:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_AUTHORIZED_RUN_SET_INCOMPLETE",
            "Every authorized run must exist in the frozen plan exactly once.",
        )
    if any(item.workload != "functional" for item in selected):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_NONFUNCTIONAL_RUN_BLOCKED",
            "The bounded live pilot permits functional development runs only.",
        )
    if any(item.episode_id not in authorization.allowed_episode_ids for item in selected):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_EPISODE_SCOPE_VIOLATION",
            "Selected runs must belong to authorized development episodes.",
        )
    if any(item.turn_count != authorization.turns_per_run for item in selected):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_TURN_COUNT_MISMATCH",
            "Selected runs must preserve the frozen four-turn workload.",
        )
    if len({item.cache_namespace_id for item in selected}) != len(selected):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_CACHE_NAMESPACE_REUSE",
            "Every live-development condition requires a distinct cache namespace.",
        )
    grouped: dict[str, list[SmokePlanRunProjection]] = {}
    for run in selected:
        grouped.setdefault(run.episode_id, []).append(run)
    for episode_id, runs in grouped.items():
        if {item.condition_id for item in runs} != set(BenchmarkCondition):
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_CONDITION_COVERAGE_INVALID",
                "Every authorized episode must cover A, B, and C exactly.",
                details=(episode_id,),
            )
        if len({item.comparison_pair_id for item in runs}) != 1:
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_PAIR_SCOPE_INVALID",
                "Each authorized episode must use one frozen comparison pair.",
                details=(episode_id,),
            )
        if {item.replication_id for item in runs} != {"replication-01"}:
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_REPLICATION_SCOPE_INVALID",
                "The first live development batch is restricted to replication-01.",
                details=(episode_id,),
            )

    _verify_file_hash(
        repo_root,
        _COMPILER_SPEC_PATH,
        authorization.compiler_spec_sha256,
        "LIVE_DEVELOPMENT_COMPILER_SPEC_MISMATCH",
    )
    spec = _load_model(repo_root / _COMPILER_SPEC_PATH, StaticCompilerSpec)
    if (
        spec.template_id != assets.get("prompt_template_id")
        or spec.template_version != assets.get("prompt_template_version")
        or spec.serialization_version != assets.get("serialization_version")
    ):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PROMPT_IDENTITY_MISMATCH",
            "Compact prompt inputs differ from the frozen execution-manifest identity.",
        )

    _verify_file_hash(
        repo_root,
        _SOURCE_MANIFEST_PATH,
        authorization.source_manifest_sha256,
        "LIVE_DEVELOPMENT_SOURCE_MANIFEST_MISMATCH",
    )
    source_manifest = _load_model(repo_root / _SOURCE_MANIFEST_PATH, _SourceManifest)
    if source_manifest.status != "frozen":
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_SOURCE_MANIFEST_NOT_FROZEN",
            "Live development requires the frozen synthetic corpus manifest.",
        )

    _verify_file_hash(
        repo_root,
        _PRICING_SCHEDULE_PATH,
        authorization.pricing_schedule_sha256,
        "LIVE_DEVELOPMENT_PRICING_SCHEDULE_MISMATCH",
    )
    pricing = _load_model(repo_root / _PRICING_SCHEDULE_PATH, _PricingSchedule)
    if (
        pricing.pricing_schedule_id != assets.get("pricing_schedule_version")
        or pricing.provider_name != authorization.provider.value
        or pricing.provider_model_alias != authorization.provider_model_alias
    ):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PRICING_IDENTITY_MISMATCH",
            "Pricing schedule identity differs from the frozen execution manifest.",
        )
    if authorization.maximum_input_tokens_per_attempt > pricing.maximum_input_tokens_per_attempt:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_INPUT_CEILING_EXCEEDS_FREEZE",
            "Authorization input ceiling exceeds the frozen pricing ceiling.",
        )
    if authorization.output_token_budget > pricing.maximum_output_tokens_per_attempt:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_OUTPUT_CEILING_EXCEEDS_FREEZE",
            "Authorization output ceiling exceeds the frozen pricing ceiling.",
        )
    return selected, episodes, spec, source_manifest, pricing


def _static_system_prompt(spec: StaticCompilerSpec) -> str:
    payload = {
        "runtime_prompt_profile": "development-live-compact-v1",
        "serialization_version": spec.serialization_version,
        "template_id": spec.template_id,
        "template_version": spec.template_version,
        "segments": [item.model_dump(mode="json") for item in spec.segments],
        "tools": [item.model_dump(mode="json") for item in spec.tools],
        "output_schema": spec.output_schema.model_dump(mode="json"),
        "context_pack": spec.context_pack.model_dump(mode="json"),
        "response_rule": (
            "Return exactly one JSON object. Do not use Markdown fences, commentary, "
            "or fields outside the frozen terminal-decision schema."
        ),
    }
    return bytes(canonical_json_bytes(payload)).decode("utf-8")


def _load_episode_sources(
    repo_root: Path,
    episode: BenchmarkEpisode,
    source_manifest: _SourceManifest,
) -> tuple[dict[str, str], ...]:
    by_id = {item.source_id: item for item in source_manifest.artifacts}
    evidence: list[dict[str, str]] = []
    for source_id in episode.source_scope.required_source_ids:
        artifact = by_id.get(source_id)
        if artifact is None:
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_REQUIRED_SOURCE_MISSING",
                "An episode-required source is absent from the frozen source manifest.",
                details=(source_id,),
            )
        path = repo_root / artifact.document_path
        if sha256_file(path) != artifact.sha256:
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_SOURCE_ARTIFACT_MISMATCH",
                "A required source no longer matches its frozen corpus hash.",
                str(path),
                (source_id,),
            )
        text = path.read_text(encoding="utf-8")
        if len(text.encode("utf-8")) != artifact.byte_count:
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_SOURCE_BYTE_COUNT_MISMATCH",
                "A required source no longer matches its frozen byte count.",
                str(path),
                (source_id,),
            )
        evidence.append({"source_id": source_id, "document": text})
    return tuple(evidence)


def _volatile_prompt(
    episode: BenchmarkEpisode,
    turn_index: int,
    source_evidence: tuple[dict[str, str], ...],
    prior_user_messages: list[str],
    prior_assistant_outputs: list[str],
) -> str:
    history: list[dict[str, str]] = []
    for user_message, assistant_output in zip(
        prior_user_messages,
        prior_assistant_outputs,
        strict=True,
    ):
        history.extend(
            (
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_output},
            )
        )
    turn = episode.turns[turn_index - 1]
    payload = {
        "episode_id": episode.episode_id,
        "episode_title": episode.title,
        "turn_index": turn_index,
        "conversation_history": history,
        "current_user_message": turn.user_message,
        "permitted_source_ids": list(episode.source_scope.required_source_ids),
        "retrieval_evidence": list(source_evidence),
        "instruction": (
            "Use only the supplied synthetic evidence. Return one terminal-decision JSON "
            "object for the current turn. Clarify rather than guess when evidence is incomplete."
        ),
    }
    return bytes(canonical_json_bytes(payload)).decode("utf-8")


def _prompts_for_condition(
    condition: BenchmarkCondition,
    static_prompt: str,
    volatile_prompt: str,
) -> ProtectedProviderPrompt:
    if condition is BenchmarkCondition.A:
        mixed_system = static_prompt + volatile_prompt
        return ProtectedProviderPrompt(
            system_prompt=mixed_system,
            user_prompt="Return the JSON decision for the current embedded turn.",
        )
    return ProtectedProviderPrompt(system_prompt=static_prompt, user_prompt=volatile_prompt)


def _prefix_fingerprint(system_prompt: str, hmac_key: bytes) -> str:
    return hmac.new(hmac_key, system_prompt.encode("utf-8"), hashlib.sha256).hexdigest()


def _estimated_input_tokens(prompt: ProtectedProviderPrompt) -> int:
    return max(1, math.ceil(int(prompt.total_bytes) / 4))


def _cost_microusd(
    input_tokens: int,
    cached_input_tokens: int | None,
    output_tokens: int,
    pricing: _PricingSchedule,
) -> int:
    cached = cached_input_tokens or 0
    if cached > input_tokens:
        cached = 0
    uncached = input_tokens - cached
    cost = (
        Decimal(uncached) * pricing.uncached_input_usd_per_million_tokens
        + Decimal(cached) * pricing.cached_input_usd_per_million_tokens
        + Decimal(output_tokens) * pricing.output_usd_per_million_tokens
    )
    return int(cost.to_integral_value(rounding=ROUND_CEILING))


def _projected_attempt_cost(
    estimated_input_tokens: int,
    authorization: LiveDevelopmentAuthorization,
    pricing: _PricingSchedule,
) -> int:
    return _cost_microusd(
        estimated_input_tokens,
        None,
        authorization.output_token_budget,
        pricing,
    )


def _response_certainty(error_code: ProviderErrorCode) -> LiveResponseCertainty:
    if error_code in {ProviderErrorCode.TIMEOUT, ProviderErrorCode.AMBIGUOUS_RESPONSE}:
        return LiveResponseCertainty.AMBIGUOUS
    return LiveResponseCertainty.DEFINITE_FAILURE


def _citation_ids(output: TerminalDecisionOutput) -> tuple[str, ...]:
    if isinstance(output, AnswerDecisionOutput):
        return tuple(str(item) for item in output.citation_ids)
    if isinstance(output, EscalateDecisionOutput):
        return tuple(str(item) for item in output.evidence_source_ids)
    citation_ids = getattr(output, "citation_ids", ())
    return tuple(citation_ids)


def _parse_structured_output(
    raw_output: str,
    allowed_source_ids: set[str],
) -> tuple[bool, bool | None, str | None, tuple[str, ...]]:
    try:
        payload = json.loads(raw_output)
        output = _TERMINAL_OUTPUT_ADAPTER.validate_python(payload)
    except (json.JSONDecodeError, ValidationError):
        return False, None, None, ()
    citations = _citation_ids(output)
    citation_scope_valid = set(citations).issubset(allowed_source_ids)
    return True, citation_scope_valid, str(output.decision), citations


def _append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line.rstrip("\n") + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def append_journal_event(path: Path, event: LiveJournalEvent) -> None:
    """Append one metadata-only event and force it to disk before continuing."""

    _append_line(path, event.model_dump_json())


def append_protected_output(
    path: Path,
    attempt_id: str,
    run_id: str,
    turn_index: int,
    output_sha256: str,
    raw_output: str,
) -> None:
    """Append raw provider output beneath ignored local storage only."""

    record = _ProtectedOutputRecord(
        attempt_id=attempt_id,
        run_id=run_id,
        turn_index=turn_index,
        output_sha256=output_sha256,
        raw_output=raw_output,
    )
    _append_line(path, record.model_dump_json())


def load_journal(path: Path) -> tuple[LiveJournalEvent, ...]:
    """Load and validate contiguous append-only public journal evidence."""

    if not path.exists():
        return ()
    adapter: TypeAdapter[LiveJournalEvent] = TypeAdapter(LiveJournalEvent)
    events: list[LiveJournalEvent] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_JOURNAL_BLANK_LINE",
                "The append-only live journal contains a blank event line.",
                str(path),
            )
        try:
            event = adapter.validate_json(line)
        except ValidationError as exc:
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_JOURNAL_VALIDATION_FAILED",
                "The append-only live journal contains an invalid event.",
                str(path),
                (f"line={index + 1}",),
            ) from exc
        if event.sequence_index != index:
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_JOURNAL_SEQUENCE_INVALID",
                "The append-only live journal sequence is not contiguous.",
                str(path),
                (f"expected={index}", f"observed={event.sequence_index}"),
            )
        events.append(event)
    attempt_ids = [
        item.attempt.attempt_id for item in events if isinstance(item, LiveJournalAttemptEvent)
    ]
    terminal_runs = [
        item.terminal.run_id for item in events if isinstance(item, LiveJournalTerminalEvent)
    ]
    if len(attempt_ids) != len(set(attempt_ids)):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_JOURNAL_DUPLICATE_ATTEMPT",
            "The append-only live journal contains duplicate attempt IDs.",
            str(path),
        )
    if len(terminal_runs) != len(set(terminal_runs)):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_JOURNAL_DUPLICATE_TERMINAL",
            "The append-only live journal contains duplicate terminal run records.",
            str(path),
        )
    return tuple(events)


def _events_by_run(
    events: tuple[LiveJournalEvent, ...],
) -> tuple[dict[str, list[LiveAttemptRecord]], dict[str, LiveTerminalRecord]]:
    attempts: dict[str, list[LiveAttemptRecord]] = {}
    terminals: dict[str, LiveTerminalRecord] = {}
    for event in events:
        if isinstance(event, LiveJournalAttemptEvent):
            attempts.setdefault(event.attempt.run_id, []).append(event.attempt)
        else:
            terminals[event.terminal.run_id] = event.terminal
    return attempts, terminals


def _terminal_record(
    run: SmokePlanRunProjection,
    trace_id: str,
    attempts: list[LiveAttemptRecord],
    status: RunTerminalStatus,
    completed_turn_count: int,
    failure_code: LiveExecutionFailureCode | None,
) -> LiveTerminalRecord:
    structured_failures = sum(
        item.provider_status is ProviderInvocationStatus.SUCCEEDED
        and not item.structured_output_valid
        for item in attempts
    )
    citation_failures = sum(item.citation_scope_valid is False for item in attempts)
    return LiveTerminalRecord(
        terminal_record_id=_opaque_id(
            "terminal",
            run.run_id,
            status.value,
            len(attempts),
            failure_code.value if failure_code is not None else "none",
        ),
        trace_id=trace_id,
        run_id=run.run_id,
        comparison_pair_id=run.comparison_pair_id,
        episode_id=run.episode_id,
        condition_id=run.condition_id,
        cache_namespace_id=run.cache_namespace_id,
        terminal_status=status,
        completed_turn_count=completed_turn_count,
        attempt_count=len(attempts),
        attempt_ids=tuple(item.attempt_id for item in attempts),
        structured_output_failure_count=structured_failures,
        citation_scope_failure_count=citation_failures,
        failure_code=failure_code,
    )


def _append_terminal(
    journal_path: Path,
    events: list[LiveJournalEvent],
    terminal: LiveTerminalRecord,
) -> None:
    event = LiveJournalTerminalEvent(sequence_index=len(events), terminal=terminal)
    append_journal_event(journal_path, event)
    events.append(event)


def _attempt_record_from_error(
    *,
    run: SmokePlanRunProjection,
    trace_id: str,
    turn_index: int,
    attempt_index: int,
    prompt: ProtectedProviderPrompt,
    static_prefix_fingerprint: str,
    prefix_hmac_key_id: str,
    logical_request_sha256: str,
    request_id: str,
    error: LiveProviderError,
    retry_authorized: bool,
) -> LiveAttemptRecord:
    summary = prompt.summary()
    return LiveAttemptRecord(
        attempt_id=_opaque_id(
            "attempt",
            run.run_id,
            turn_index,
            attempt_index,
            logical_request_sha256,
        ),
        trace_id=trace_id,
        run_id=run.run_id,
        condition_id=run.condition_id,
        turn_index=turn_index,
        attempt_index=attempt_index,
        provider=ProviderName.GROQ,
        model_alias="groq-gpt-oss-20b",
        route_reason=(
            "session_start"
            if run.condition_id is BenchmarkCondition.C and turn_index == 1
            else "warm_cache_affinity"
            if run.condition_id is BenchmarkCondition.C
            else "benchmark_control"
        ),
        provider_status=ProviderInvocationStatus.FAILED,
        response_certainty=_response_certainty(error.error_code),
        retry_authorized=retry_authorized,
        logical_request_sha256=logical_request_sha256,
        provider_request_id_sha256=_sha256_bytes(request_id.encode("utf-8")),
        static_prefix_fingerprint=static_prefix_fingerprint,
        prefix_hmac_key_id=prefix_hmac_key_id,
        system_prompt_sha256=summary.system_sha256,
        user_prompt_sha256=summary.user_sha256,
        prompt_byte_count=summary.total_bytes,
        provider_error_code=error.error_code.value,
        estimated_cost_microusd=0,
    )


def _build_record_set(
    authorization: LiveDevelopmentAuthorization,
    events: tuple[LiveJournalEvent, ...],
) -> LiveRunRecordSet:
    attempts = tuple(
        event.attempt for event in events if isinstance(event, LiveJournalAttemptEvent)
    )
    terminals = tuple(
        event.terminal for event in events if isinstance(event, LiveJournalTerminalEvent)
    )
    order = {run_id: index for index, run_id in enumerate(authorization.allowed_run_ids)}
    ordered_attempts = tuple(
        sorted(attempts, key=lambda item: (order[item.run_id], item.turn_index, item.attempt_index))
    )
    ordered_terminals = tuple(sorted(terminals, key=lambda item: order[item.run_id]))
    return LiveRunRecordSet(
        batch_id=authorization.batch_id,
        authorization_id=authorization.authorization_id,
        execution_manifest_sha256=authorization.execution_manifest_sha256,
        terminal_records=ordered_terminals,
        attempt_records=ordered_attempts,
        total_attempt_count=len(ordered_attempts),
        total_estimated_cost_microusd=sum(
            item.estimated_cost_microusd for item in ordered_attempts
        ),
        live_provider_called=bool(ordered_attempts),
    )


def build_live_report(
    authorization: LiveDevelopmentAuthorization,
    records: LiveRunRecordSet,
    reused_terminal_count: int,
    protected_outputs_retained: bool,
) -> LiveDevelopmentReport:
    """Build a no-claims public report from reconciled terminal evidence."""

    status_counts = Counter(item.terminal_status for item in records.terminal_records)
    retry_count = sum(item.retry_authorized for item in records.attempt_records)
    ambiguous_blocked = sum(
        item.response_certainty is LiveResponseCertainty.AMBIGUOUS and not item.retry_authorized
        for item in records.attempt_records
    )
    return LiveDevelopmentReport(
        batch_id=authorization.batch_id,
        authorization_id=authorization.authorization_id,
        execution_manifest_sha256=authorization.execution_manifest_sha256,
        selected_episode_ids=authorization.allowed_episode_ids,
        selected_run_count=authorization.maximum_run_count,
        terminal_record_count=len(records.terminal_records),
        attempt_record_count=len(records.attempt_records),
        provider_call_count=len(records.attempt_records),
        retry_authorized_count=retry_count,
        ambiguous_retry_blocked_count=ambiguous_blocked,
        completed_run_count=status_counts[RunTerminalStatus.COMPLETED],
        completed_validation_failure_count=status_counts[
            RunTerminalStatus.COMPLETED_VALIDATION_FAILURE
        ],
        provider_error_count=status_counts[RunTerminalStatus.PROVIDER_ERROR],
        safety_abort_count=status_counts[RunTerminalStatus.ABORTED_SAFETY_CONTROL],
        budget_exhausted_count=status_counts[RunTerminalStatus.BUDGET_EXHAUSTED],
        structured_output_failure_count=sum(
            item.structured_output_failure_count for item in records.terminal_records
        ),
        citation_scope_failure_count=sum(
            item.citation_scope_failure_count for item in records.terminal_records
        ),
        total_estimated_cost_microusd=records.total_estimated_cost_microusd,
        attempt_budget_respected=(
            records.total_attempt_count <= authorization.maximum_total_attempt_count
        ),
        cost_budget_respected=(
            records.total_estimated_cost_microusd <= authorization.maximum_total_cost_microusd
        ),
        resume_reused_terminal_record_count=reused_terminal_count,
        live_provider_called=records.live_provider_called,
        retrieval_execution_mode=authorization.retrieval_execution_mode,
        runtime_prompt_profile=authorization.runtime_prompt_profile,
        protected_outputs_retained_locally=protected_outputs_retained,
        batch_completed=(len(records.terminal_records) == authorization.maximum_run_count),
    )


def execute_live_development(
    *,
    repo_root: Path,
    authorization: LiveDevelopmentAuthorization,
    adapter: LiveProviderAdapter,
    journal_path: Path,
    protected_output_path: Path,
    resume: bool,
) -> tuple[LiveRunRecordSet, LiveDevelopmentReport, int]:
    """Execute authorized live runs while preserving terminal and attempt evidence."""

    selected, episodes, spec, source_manifest, pricing = validate_live_upstream(
        repo_root,
        authorization,
    )
    hmac_key, hmac_key_id = _load_hmac_settings()
    static_prompt = _static_system_prompt(spec)
    existing_events = load_journal(journal_path)
    if existing_events and not resume:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_JOURNAL_ALREADY_EXISTS",
            "Existing journal evidence requires the resume command.",
            str(journal_path),
        )
    events = list(existing_events)
    existing_attempts, existing_terminals = _events_by_run(existing_events)
    existing_key_ids = {
        attempt.prefix_hmac_key_id
        for attempts in existing_attempts.values()
        for attempt in attempts
    }
    if existing_key_ids and existing_key_ids != {hmac_key_id}:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PREFIX_HMAC_KEY_ID_MISMATCH",
            "Resume requires the same non-secret prefix HMAC key ID as existing attempts.",
            details=tuple(sorted(existing_key_ids)),
        )
    reused_terminal_count = len(existing_terminals)
    total_attempt_count = sum(isinstance(item, LiveJournalAttemptEvent) for item in existing_events)
    total_cost = sum(
        item.attempt.estimated_cost_microusd
        for item in existing_events
        if isinstance(item, LiveJournalAttemptEvent)
    )
    halt_remaining = False

    for run in selected:
        if run.run_id in existing_terminals:
            continue
        trace_id = _opaque_id("trace", authorization.execution_manifest_sha256, run.run_id)
        prior_attempts = list(existing_attempts.get(run.run_id, []))
        if prior_attempts:
            completed_turns = len(
                {
                    item.turn_index
                    for item in prior_attempts
                    if item.provider_status is ProviderInvocationStatus.SUCCEEDED
                }
            )
            resume_terminal = _terminal_record(
                run,
                trace_id,
                prior_attempts,
                RunTerminalStatus.ABORTED_SAFETY_CONTROL,
                completed_turns,
                LiveExecutionFailureCode.RESUME_UNCERTAIN_PROVIDER_STATE,
            )
            _append_terminal(journal_path, events, resume_terminal)
            continue
        if halt_remaining:
            halt_terminal = _terminal_record(
                run,
                trace_id,
                [],
                RunTerminalStatus.ABORTED_SAFETY_CONTROL,
                0,
                LiveExecutionFailureCode.BATCH_HALTED_PROVIDER_FAILURE,
            )
            _append_terminal(journal_path, events, halt_terminal)
            continue

        episode = episodes[run.episode_id]
        source_evidence = _load_episode_sources(repo_root, episode, source_manifest)
        prior_user_messages: list[str] = []
        prior_assistant_outputs: list[str] = []
        run_attempts: list[LiveAttemptRecord] = []
        completed_turns = 0
        terminal: LiveTerminalRecord | None = None

        for turn_index in range(1, authorization.turns_per_run + 1):
            volatile_prompt = _volatile_prompt(
                episode,
                turn_index,
                source_evidence,
                prior_user_messages,
                prior_assistant_outputs,
            )
            prompt = _prompts_for_condition(run.condition_id, static_prompt, volatile_prompt)
            estimated_input = _estimated_input_tokens(prompt)
            if estimated_input > authorization.maximum_input_tokens_per_attempt:
                terminal = _terminal_record(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.BUDGET_EXHAUSTED,
                    completed_turns,
                    LiveExecutionFailureCode.INPUT_BUDGET_EXHAUSTED,
                )
                break
            projected_cost = _projected_attempt_cost(
                estimated_input,
                authorization,
                pricing,
            )
            if total_cost + projected_cost > authorization.maximum_total_cost_microusd:
                terminal = _terminal_record(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.BUDGET_EXHAUSTED,
                    completed_turns,
                    LiveExecutionFailureCode.COST_BUDGET_EXHAUSTED,
                )
                break

            for attempt_index in (1, 2):
                if total_attempt_count >= authorization.maximum_total_attempt_count:
                    terminal = _terminal_record(
                        run,
                        trace_id,
                        run_attempts,
                        RunTerminalStatus.BUDGET_EXHAUSTED,
                        completed_turns,
                        LiveExecutionFailureCode.ATTEMPT_BUDGET_EXHAUSTED,
                    )
                    break
                logical_request_sha256 = _sha256_bytes(
                    canonical_json_bytes(
                        {
                            "run_id": run.run_id,
                            "turn_index": turn_index,
                            "condition_id": run.condition_id.value,
                            "system_prompt_sha256": prompt.summary().system_sha256,
                            "user_prompt_sha256": prompt.summary().user_sha256,
                        }
                    )
                )
                request_id = (
                    "live-"
                    + _sha256_bytes(f"{run.run_id}|{turn_index}|{attempt_index}".encode())[:24]
                )
                fixture_id = "live-" + logical_request_sha256[:24]
                static_prefix_fingerprint = _prefix_fingerprint(
                    prompt.system_prompt,
                    hmac_key,
                )
                invocation = LiveProviderInvocation(
                    request=ProviderInvocationRequest(
                        request_id=request_id,
                        fixture_id=fixture_id,
                        provider=authorization.provider,
                        model_alias=authorization.provider_model_alias,
                        static_prefix_fingerprint=static_prefix_fingerprint,
                        input_token_count=estimated_input,
                        output_token_budget=authorization.output_token_budget,
                    ),
                    prompt=prompt,
                    timeout_seconds=authorization.timeout_seconds,
                )
                try:
                    provider_call = adapter.invoke(invocation)
                except LiveProviderError as exc:
                    certainty = _response_certainty(exc.error_code)
                    retry_authorized = (
                        attempt_index == 1
                        and exc.retryable
                        and certainty is LiveResponseCertainty.DEFINITE_FAILURE
                        and exc.error_code in _DEFINITE_RETRYABLE_CODES
                    )
                    attempt = _attempt_record_from_error(
                        run=run,
                        trace_id=trace_id,
                        turn_index=turn_index,
                        attempt_index=attempt_index,
                        prompt=prompt,
                        static_prefix_fingerprint=static_prefix_fingerprint,
                        prefix_hmac_key_id=hmac_key_id,
                        logical_request_sha256=logical_request_sha256,
                        request_id=request_id,
                        error=exc,
                        retry_authorized=retry_authorized,
                    )
                    event = LiveJournalAttemptEvent(
                        sequence_index=len(events),
                        attempt=attempt,
                    )
                    append_journal_event(journal_path, event)
                    events.append(event)
                    run_attempts.append(attempt)
                    total_attempt_count += 1
                    if retry_authorized:
                        continue
                    if certainty is LiveResponseCertainty.AMBIGUOUS:
                        terminal = _terminal_record(
                            run,
                            trace_id,
                            run_attempts,
                            RunTerminalStatus.ABORTED_SAFETY_CONTROL,
                            completed_turns,
                            LiveExecutionFailureCode.AMBIGUOUS_PROVIDER_RESPONSE,
                        )
                    else:
                        failure = (
                            LiveExecutionFailureCode.RETRY_BUDGET_EXHAUSTED
                            if attempt_index == 2 and exc.retryable
                            else LiveExecutionFailureCode.NONRETRYABLE_PROVIDER_FAILURE
                        )
                        terminal = _terminal_record(
                            run,
                            trace_id,
                            run_attempts,
                            RunTerminalStatus.PROVIDER_ERROR,
                            completed_turns,
                            failure,
                        )
                    if exc.error_code in _SYSTEMIC_ERROR_CODES:
                        halt_remaining = True
                    break

                if provider_call.result.status is not ProviderInvocationStatus.SUCCEEDED:
                    error_code = (
                        provider_call.result.error_code or ProviderErrorCode.INVALID_RESPONSE
                    )
                    typed_error = LiveProviderError(
                        error_code,
                        "Provider adapter returned a typed failed result.",
                        retryable=provider_call.result.retryable,
                    )
                    certainty = _response_certainty(error_code)
                    retry_authorized = (
                        attempt_index == 1
                        and typed_error.retryable
                        and certainty is LiveResponseCertainty.DEFINITE_FAILURE
                        and error_code in _DEFINITE_RETRYABLE_CODES
                    )
                    attempt = _attempt_record_from_error(
                        run=run,
                        trace_id=trace_id,
                        turn_index=turn_index,
                        attempt_index=attempt_index,
                        prompt=prompt,
                        static_prefix_fingerprint=static_prefix_fingerprint,
                        prefix_hmac_key_id=hmac_key_id,
                        logical_request_sha256=logical_request_sha256,
                        request_id=request_id,
                        error=typed_error,
                        retry_authorized=retry_authorized,
                    )
                    event = LiveJournalAttemptEvent(
                        sequence_index=len(events),
                        attempt=attempt,
                    )
                    append_journal_event(journal_path, event)
                    events.append(event)
                    run_attempts.append(attempt)
                    total_attempt_count += 1
                    if retry_authorized:
                        continue
                    terminal = _terminal_record(
                        run,
                        trace_id,
                        run_attempts,
                        RunTerminalStatus.PROVIDER_ERROR,
                        completed_turns,
                        LiveExecutionFailureCode.NONRETRYABLE_PROVIDER_FAILURE,
                    )
                    break

                protected_output = provider_call.protected_output
                if protected_output is None:
                    missing_output_error = LiveProviderError(
                        ProviderErrorCode.AMBIGUOUS_RESPONSE,
                        "Provider adapter returned no protected output for a successful call.",
                        retryable=False,
                    )
                    attempt = _attempt_record_from_error(
                        run=run,
                        trace_id=trace_id,
                        turn_index=turn_index,
                        attempt_index=attempt_index,
                        prompt=prompt,
                        static_prefix_fingerprint=static_prefix_fingerprint,
                        prefix_hmac_key_id=hmac_key_id,
                        logical_request_sha256=logical_request_sha256,
                        request_id=request_id,
                        error=missing_output_error,
                        retry_authorized=False,
                    )
                    event = LiveJournalAttemptEvent(
                        sequence_index=len(events),
                        attempt=attempt,
                    )
                    append_journal_event(journal_path, event)
                    events.append(event)
                    run_attempts.append(attempt)
                    total_attempt_count += 1
                    terminal = _terminal_record(
                        run,
                        trace_id,
                        run_attempts,
                        RunTerminalStatus.ABORTED_SAFETY_CONTROL,
                        completed_turns,
                        LiveExecutionFailureCode.AMBIGUOUS_PROVIDER_RESPONSE,
                    )
                    break

                attempt_id = _opaque_id(
                    "attempt",
                    run.run_id,
                    turn_index,
                    attempt_index,
                    logical_request_sha256,
                )
                protected_retained = True
                try:
                    append_protected_output(
                        protected_output_path,
                        attempt_id,
                        run.run_id,
                        turn_index,
                        protected_output.sha256,
                        protected_output.text,
                    )
                except OSError:
                    protected_retained = False

                structured_valid = False
                citation_scope_valid: bool | None = None
                decision: str | None = None
                citations: tuple[str, ...] = ()
                if protected_retained:
                    (
                        structured_valid,
                        citation_scope_valid,
                        decision,
                        citations,
                    ) = _parse_structured_output(
                        protected_output.text,
                        set(episode.source_scope.required_source_ids),
                    )
                normalized = normalize_telemetry(provider_call.telemetry)
                input_tokens = normalized.provider_input_tokens or estimated_input
                cached_tokens = normalized.provider_cached_input_tokens
                uncached_tokens = normalized.provider_uncached_input_tokens
                output_tokens = normalized.provider_output_tokens or 0
                cost = _cost_microusd(
                    input_tokens,
                    cached_tokens,
                    output_tokens,
                    pricing,
                )
                summary = prompt.summary()
                attempt = LiveAttemptRecord(
                    attempt_id=attempt_id,
                    trace_id=trace_id,
                    run_id=run.run_id,
                    condition_id=run.condition_id,
                    turn_index=turn_index,
                    attempt_index=attempt_index,
                    provider=authorization.provider,
                    model_alias=authorization.provider_model_alias,
                    route_reason=(
                        "session_start"
                        if run.condition_id is BenchmarkCondition.C and turn_index == 1
                        else "warm_cache_affinity"
                        if run.condition_id is BenchmarkCondition.C
                        else "benchmark_control"
                    ),
                    provider_status=ProviderInvocationStatus.SUCCEEDED,
                    response_certainty=LiveResponseCertainty.SUCCESS,
                    retry_authorized=False,
                    logical_request_sha256=logical_request_sha256,
                    provider_request_id_sha256=_sha256_bytes(request_id.encode("utf-8")),
                    static_prefix_fingerprint=static_prefix_fingerprint,
                    prefix_hmac_key_id=hmac_key_id,
                    system_prompt_sha256=summary.system_sha256,
                    user_prompt_sha256=summary.user_sha256,
                    prompt_byte_count=summary.total_bytes,
                    output_sha256=protected_output.sha256,
                    input_tokens=input_tokens,
                    cached_input_tokens=cached_tokens,
                    uncached_input_tokens=uncached_tokens,
                    output_tokens=output_tokens,
                    total_duration_ms=normalized.total_duration_ms,
                    estimated_cost_microusd=cost,
                    protected_output_retained=protected_retained,
                    structured_output_valid=structured_valid,
                    citation_scope_valid=citation_scope_valid,
                    decision=decision,
                    citation_ids=citations,
                )
                event = LiveJournalAttemptEvent(
                    sequence_index=len(events),
                    attempt=attempt,
                )
                append_journal_event(journal_path, event)
                events.append(event)
                run_attempts.append(attempt)
                total_attempt_count += 1
                total_cost += cost
                if not protected_retained:
                    terminal = _terminal_record(
                        run,
                        trace_id,
                        run_attempts,
                        RunTerminalStatus.ABORTED_SAFETY_CONTROL,
                        completed_turns,
                        LiveExecutionFailureCode.PROTECTED_OUTPUT_RETENTION_FAILED,
                    )
                    break
                prior_user_messages.append(episode.turns[turn_index - 1].user_message)
                prior_assistant_outputs.append(protected_output.text)
                completed_turns += 1
                break

            if terminal is not None:
                break

        if terminal is None:
            structured_failures = sum(not item.structured_output_valid for item in run_attempts)
            citation_failures = sum(item.citation_scope_valid is False for item in run_attempts)
            if structured_failures:
                terminal = _terminal_record(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.COMPLETED_VALIDATION_FAILURE,
                    completed_turns,
                    LiveExecutionFailureCode.STRUCTURED_OUTPUT_INVALID,
                )
            elif citation_failures:
                terminal = _terminal_record(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.COMPLETED_VALIDATION_FAILURE,
                    completed_turns,
                    LiveExecutionFailureCode.CITATION_SCOPE_INVALID,
                )
            else:
                terminal = _terminal_record(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.COMPLETED,
                    completed_turns,
                    None,
                )
        _append_terminal(journal_path, events, terminal)

    final_events = tuple(events)
    records = _build_record_set(authorization, final_events)
    report = build_live_report(
        authorization,
        records,
        reused_terminal_count,
        protected_output_path.exists(),
    )
    return records, report, reused_terminal_count
