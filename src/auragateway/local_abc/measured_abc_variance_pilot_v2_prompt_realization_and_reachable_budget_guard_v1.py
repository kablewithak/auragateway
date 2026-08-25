"""Freeze V2 prompt realization and reachable-state token-budget admission."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

PILOT_SCHEDULE_PATH: Final = Path("data/evals/benchmark/variance-pilot-v2/pilot_schedule.json")
NEUTRAL_PLAN_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/neutral_worker_qualification_plan.json"
)
TOKENIZER_RUNTIME_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/tokenizer_budget_and_standalone_runtime_v1.json"
)
ACCEPTED_EPISODES_PATH: Final = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
RUNTIME_SELECTION_PATH: Final = Path("data/evals/episodes/runtime-v1/selection.json")
SOURCE_MANIFEST_PATH: Final = Path("data/corpus/source_manifest.json")
COMPILER_SPEC_PATH: Final = Path("data/context/compiler_spec.json")
STANDALONE_ADMISSION_SPEC_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "measured_abc_variance_pilot_v2_prompt_realization_and_reachable_budget_guard_v1.py"
)
RUNTIME_V2_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_standalone_runtime_v2.py"
)
OUTPUT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/prompt_realization_and_reachable_budget_guard_v1.json"
)

EXPECTED_REQUEST_COUNT: Final = 240
MAX_MODEL_LEN: Final = 4096
MAX_OUTPUT_TOKENS: Final = 256
MAX_PROMPT_TOKENS: Final = MAX_MODEL_LEN - MAX_OUTPUT_TOKENS
NEXT_GATE: Final = "OBSERVE_VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_TOKENIZER_REACHABLE_ENVELOPE_V1"

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


class PromptBudgetGuardError(RuntimeError):
    """Metadata-safe prompt-realization or budget-guard contract failure."""

    def __init__(self, error_code: str, safe_message: str, path: Path | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class ArtifactReceipt(LocalABCContract):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class PromptSlotBinding(LocalABCContract):
    sequence_index: int = Field(ge=0, lt=EXPECTED_REQUEST_COUNT)
    request_id: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    history_dependency: Literal["none", "prior_admitted_history"]
    known_messages_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_known_messages(self) -> Self:
        if self.history_dependency == "none" and self.known_messages_sha256 is None:
            raise ValueError("history-independent slots require an exact message identity")
        if (
            self.history_dependency == "prior_admitted_history"
            and self.known_messages_sha256 is not None
        ):
            raise ValueError("history-dependent slots cannot claim a future exact message identity")
        return self


class PromptRealizationGuardContract(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    contract_id: Literal[
        "auragateway-variance-pilot-v2-prompt-realization-reachable-budget-guard-v1"
    ] = "auragateway-variance-pilot-v2-prompt-realization-reachable-budget-guard-v1"
    static_prompt_profile: Literal["development-live-compact-v2"] = "development-live-compact-v2"
    pilot_history_transport: Literal["CANONICAL_JSON_EMBEDDED_IN_VOLATILE_PROMPT"] = (
        "CANONICAL_JSON_EMBEDDED_IN_VOLATILE_PROMPT"
    )
    condition_a_placement: Literal["STATIC_PLUS_VOLATILE_SYSTEM_CONSTANT_USER"] = (
        "STATIC_PLUS_VOLATILE_SYSTEM_CONSTANT_USER"
    )
    condition_b_c_placement: Literal["STATIC_SYSTEM_VOLATILE_USER"] = "STATIC_SYSTEM_VOLATILE_USER"
    v1_prompt_placement_semantics_reused: Literal[True] = True
    v1_terminal_output_schema_reused: Literal[False] = False
    v1_terminal_few_shot_reused: Literal[False] = False
    v1_terminal_tool_schema_reused: Literal[False] = False
    v2_standalone_admission_spec_required: Literal[True] = True
    exact_current_prompt_check_before_send_required: Literal[True] = True
    prospective_next_prompt_check_before_history_commit_required: Literal[True] = True
    static_prior_assistant_256_token_allowance_relied_on: Literal[False] = False
    history_commit_permitted_after_prospective_budget_failure: Literal[False] = False
    maximum_prompt_tokens: Literal[3840] = MAX_PROMPT_TOKENS
    max_output_tokens: Literal[256] = MAX_OUTPUT_TOKENS
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    accepted_tokenizer_observation_performed: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False


class MaterializationV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    prompt_contract: PromptRealizationGuardContract = PromptRealizationGuardContract()
    static_system_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_episode_ids: tuple[str, str, str, str, str, str]
    required_source_ids: tuple[str, ...]
    request_slots: tuple[PromptSlotBinding, ...] = Field(
        min_length=EXPECTED_REQUEST_COUNT,
        max_length=EXPECTED_REQUEST_COUNT,
    )
    source: ArtifactReceipt
    standalone_runtime_v2: ArtifactReceipt
    pilot_schedule: ArtifactReceipt
    neutral_plan: ArtifactReceipt
    tokenizer_runtime: ArtifactReceipt
    accepted_episodes: ArtifactReceipt
    runtime_selection: ArtifactReceipt
    source_manifest: ArtifactReceipt
    compiler_spec: ArtifactReceipt
    standalone_admission_spec: ArtifactReceipt
    accepted_tokenizer_envelope_proof_complete: Literal[False] = False
    runtime_executable_generated: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "OBSERVE_VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_TOKENIZER_REACHABLE_ENVELOPE_V1"
    ] = NEXT_GATE

    @model_validator(mode="after")
    def validate_slots(self) -> Self:
        if tuple(item.sequence_index for item in self.request_slots) != tuple(
            range(EXPECTED_REQUEST_COUNT)
        ):
            raise ValueError("prompt slot indexes must be contiguous")
        if len({item.request_id for item in self.request_slots}) != EXPECTED_REQUEST_COUNT:
            raise ValueError("prompt slot request IDs must be unique")
        return self


MessageList = list[dict[str, str]]
JsonHistory = list[dict[str, str]]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_messages(messages: MessageList) -> str:
    return _sha256_text(canonical_json(messages))


def _load_object(repo_root: Path, relative: Path) -> dict[str, object]:
    path = repo_root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_REQUIRED_FILE_MISSING",
            "required prompt-realization file is missing",
            relative,
        ) from exc
    except json.JSONDecodeError as exc:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_JSON_INVALID",
            "required prompt-realization JSON is invalid",
            relative,
        ) from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_JSON_ROOT_INVALID",
            "required prompt-realization JSON root must be an object",
            relative,
        )
    return cast(dict[str, object], value)


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_REQUIRED_FILE_MISSING",
            "required prompt-realization file is missing or unsafe",
            relative,
        )
    raw = path.read_bytes()
    return ArtifactReceipt(path=relative.as_posix(), sha256=_sha256_bytes(raw), size_bytes=len(raw))


def _stable_segments(compiler_spec: dict[str, object]) -> list[dict[str, object]]:
    raw = compiler_spec.get("segments")
    if not isinstance(raw, list):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_COMPILER_SPEC_INVALID",
            "compiler segments are invalid",
            COMPILER_SPEC_PATH,
        )
    expected = ("system-policy-v1", "task-procedure-v1", "citation-rules-v1")
    selected: list[dict[str, object]] = []
    for segment_id in expected:
        matches = [
            cast(dict[str, object], item)
            for item in raw
            if isinstance(item, dict) and item.get("segment_id") == segment_id
        ]
        if len(matches) != 1:
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_COMPILER_SPEC_INVALID",
                "required stable compiler segment is missing or duplicated",
                COMPILER_SPEC_PATH,
            )
        selected.append(matches[0])
    return selected


def build_static_system_prompt(
    compiler_spec: dict[str, object],
    admission_spec: dict[str, object],
) -> str:
    """Build the V2 static prompt without reintroducing the stale V1 terminal schema."""

    required = ("serialization_version", "template_id", "context_pack")
    if any(key not in compiler_spec for key in required):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_COMPILER_SPEC_INVALID",
            "compiler specification is missing stable prompt inputs",
            COMPILER_SPEC_PATH,
        )
    if admission_spec.get("semantic_contract") != "TerminalDecisionOutput":
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_ADMISSION_SPEC_INVALID",
            "V2 standalone admission contract is invalid",
            STANDALONE_ADMISSION_SPEC_PATH,
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
    if phase not in {"schema_canary", "warmup", "neutral_worker_qualification"}:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_PRETREATMENT_PHASE_INVALID",
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
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_HISTORY_INVALID",
            "pilot history length does not match turn index",
        )
    for index, item in enumerate(history):
        expected_role = "user" if index % 2 == 0 else "assistant"
        if set(item) != {"role", "content"} or item.get("role") != expected_role:
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_HISTORY_INVALID",
                "pilot history role ordering is invalid",
            )
        if not isinstance(item.get("content"), str):
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_HISTORY_INVALID",
                "pilot history content is invalid",
            )


def build_pilot_messages(
    *,
    condition_id: str,
    static_prompt: str,
    episode: dict[str, object],
    source_map: dict[str, str],
    turn_index: int,
    history: JsonHistory,
) -> MessageList:
    """Render the exact two-message V2 pilot prompt, including admitted history in volatile JSON."""

    if condition_id not in {"A", "B", "C"}:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_CONDITION_INVALID",
            "pilot condition is invalid",
        )
    if turn_index not in {1, 2, 3, 4}:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_TURN_INVALID",
            "pilot turn index is invalid",
        )
    _validate_history(history, turn_index)
    turns = episode.get("turns")
    scope = episode.get("source_scope")
    if not isinstance(turns, list) or len(turns) != 4 or not isinstance(scope, dict):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_EPISODE_INVALID",
            "pilot episode shape is invalid",
            ACCEPTED_EPISODES_PATH,
        )
    raw_turn = turns[turn_index - 1]
    if not isinstance(raw_turn, dict):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_EPISODE_INVALID",
            "pilot turn shape is invalid",
            ACCEPTED_EPISODES_PATH,
        )
    user_message = raw_turn.get("user_message")
    raw_ids = scope.get("required_source_ids")
    if not isinstance(user_message, str) or not user_message.strip():
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_EPISODE_INVALID",
            "pilot user message is invalid",
            ACCEPTED_EPISODES_PATH,
        )
    if not isinstance(raw_ids, list) or any(not isinstance(item, str) for item in raw_ids):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_EPISODE_INVALID",
            "pilot required source IDs are invalid",
            ACCEPTED_EPISODES_PATH,
        )
    source_ids = cast(list[str], raw_ids)
    evidence: list[dict[str, str]] = []
    for source_id in source_ids:
        document = source_map.get(source_id)
        if document is None:
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_SOURCE_MISSING",
                "pilot required source is missing",
                SOURCE_MANIFEST_PATH,
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


def _selected_material(
    repo_root: Path,
) -> tuple[tuple[str, ...], dict[str, dict[str, object]], dict[str, str]]:
    schedule = _load_object(repo_root, PILOT_SCHEDULE_PATH)
    case_rows = schedule.get("cases")
    if not isinstance(case_rows, list) or len(case_rows) != 6:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_SCHEDULE_INVALID",
            "V2 schedule must contain six cases",
            PILOT_SCHEDULE_PATH,
        )
    case_ids: list[str] = []
    for raw in case_rows:
        if not isinstance(raw, dict) or not isinstance(raw.get("episode_id"), str):
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_SCHEDULE_INVALID",
                "V2 schedule case identity is invalid",
                PILOT_SCHEDULE_PATH,
            )
        case_ids.append(cast(str, raw["episode_id"]))

    runtime_selection = _load_object(repo_root, RUNTIME_SELECTION_PATH)
    runtime_entries = runtime_selection.get("entries")
    if not isinstance(runtime_entries, list):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_RUNTIME_SELECTION_INVALID",
            "runtime selection is invalid",
            RUNTIME_SELECTION_PATH,
        )
    final_ids = {
        item.get("episode_id")
        for item in runtime_entries
        if isinstance(item, dict) and isinstance(item.get("episode_id"), str)
    }
    if set(case_ids) & final_ids:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_FINAL_RUNTIME_LEAKAGE",
            "V2 pilot cases overlap final runtime-selected episodes",
            RUNTIME_SELECTION_PATH,
        )

    accepted = _load_object(repo_root, ACCEPTED_EPISODES_PATH)
    raw_episodes = accepted.get("episodes")
    if not isinstance(raw_episodes, list):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_EPISODES_INVALID",
            "accepted episode set is invalid",
            ACCEPTED_EPISODES_PATH,
        )
    episodes: dict[str, dict[str, object]] = {}
    required_source_ids: set[str] = set()
    for raw in raw_episodes:
        if not isinstance(raw, dict) or raw.get("episode_id") not in case_ids:
            continue
        if raw.get("evaluation_split") != "development":
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_EPISODES_INVALID",
                "V2 pilot may use development episodes only",
                ACCEPTED_EPISODES_PATH,
            )
        episode = cast(dict[str, object], raw)
        episode_id = cast(str, episode["episode_id"])
        scope = episode.get("source_scope")
        if not isinstance(scope, dict):
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_EPISODES_INVALID",
                "pilot episode source scope is invalid",
                ACCEPTED_EPISODES_PATH,
            )
        ids = scope.get("required_source_ids")
        if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_EPISODES_INVALID",
                "pilot episode source IDs are invalid",
                ACCEPTED_EPISODES_PATH,
            )
        required_source_ids.update(cast(list[str], ids))
        episodes[episode_id] = episode
    if set(episodes) != set(case_ids):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_EPISODES_INVALID",
            "selected V2 episode set is incomplete",
            ACCEPTED_EPISODES_PATH,
        )

    manifest = _load_object(repo_root, SOURCE_MANIFEST_PATH)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_SOURCE_MANIFEST_INVALID",
            "source manifest artifacts are invalid",
            SOURCE_MANIFEST_PATH,
        )
    source_map: dict[str, str] = {}
    for raw in artifacts:
        if not isinstance(raw, dict) or raw.get("source_id") not in required_source_ids:
            continue
        source_id = raw.get("source_id")
        document_path = raw.get("document_path")
        expected_sha = raw.get("sha256")
        expected_bytes = raw.get("byte_count")
        if not (
            isinstance(source_id, str)
            and isinstance(document_path, str)
            and isinstance(expected_sha, str)
            and isinstance(expected_bytes, int)
        ):
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_SOURCE_MANIFEST_INVALID",
                "required source manifest row is invalid",
                SOURCE_MANIFEST_PATH,
            )
        source_path = repo_root / document_path
        raw_bytes = source_path.read_bytes()
        if _sha256_bytes(raw_bytes) != expected_sha or len(raw_bytes) != expected_bytes:
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_SOURCE_IDENTITY_DRIFT",
                "required source identity drifted",
                Path(document_path),
            )
        source_map[source_id] = raw_bytes.decode("utf-8")
    if set(source_map) != required_source_ids:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_SOURCE_SET_INCOMPLETE",
            "V2 prompt source set is incomplete",
            SOURCE_MANIFEST_PATH,
        )
    return tuple(case_ids), episodes, source_map


def _request_slot_bindings(
    repo_root: Path,
    static_prompt: str,
    episodes: dict[str, dict[str, object]],
    source_map: dict[str, str],
) -> tuple[PromptSlotBinding, ...]:
    token_material = _load_object(repo_root, TOKENIZER_RUNTIME_PATH)
    plan = token_material.get("tokenizer_budget_plan")
    if not isinstance(plan, dict):
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_TOKEN_PLAN_INVALID",
            "tokenizer budget plan is missing",
            TOKENIZER_RUNTIME_PATH,
        )
    requests = plan.get("requests")
    if not isinstance(requests, list) or len(requests) != EXPECTED_REQUEST_COUNT:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_TOKEN_PLAN_INVALID",
            "tokenizer budget plan must contain 240 requests",
            TOKENIZER_RUNTIME_PATH,
        )
    schedule = _load_object(repo_root, PILOT_SCHEDULE_PATH)
    trajectories = schedule.get("trajectories")
    if not isinstance(trajectories, list) or len(trajectories) != 54:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_SCHEDULE_INVALID",
            "V2 schedule must contain 54 trajectories",
            PILOT_SCHEDULE_PATH,
        )
    by_run: dict[str, dict[str, object]] = {}
    for raw in trajectories:
        if not isinstance(raw, dict) or not isinstance(raw.get("run_id"), str):
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_SCHEDULE_INVALID",
                "V2 trajectory identity is invalid",
                PILOT_SCHEDULE_PATH,
            )
        by_run[cast(str, raw["run_id"])] = cast(dict[str, object], raw)

    bindings: list[PromptSlotBinding] = []
    for expected_index, raw in enumerate(requests):
        if not isinstance(raw, dict):
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_TOKEN_PLAN_INVALID",
                "tokenizer request row is invalid",
                TOKENIZER_RUNTIME_PATH,
            )
        row = cast(dict[str, object], raw)
        request_id = row.get("request_id")
        phase = row.get("phase")
        dependency = row.get("prompt_state_dependency")
        if row.get("sequence_index") != expected_index:
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_TOKEN_PLAN_INVALID",
                "tokenizer request sequence drifted",
                TOKENIZER_RUNTIME_PATH,
            )
        if not isinstance(request_id, str) or not isinstance(phase, str):
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_TOKEN_PLAN_INVALID",
                "tokenizer request identity is invalid",
                TOKENIZER_RUNTIME_PATH,
            )
        if dependency not in {"none", "prior_admitted_history"}:
            raise PromptBudgetGuardError(
                "V2_PROMPT_GUARD_TOKEN_PLAN_INVALID",
                "tokenizer request history dependency is invalid",
                TOKENIZER_RUNTIME_PATH,
            )
        known_sha: str | None = None
        if dependency == "none":
            if phase != "pilot":
                known_sha = _sha256_messages(build_neutral_messages(phase, static_prompt))
            else:
                run_id = row.get("pilot_run_id")
                turn_index = row.get("pilot_turn_index")
                if not isinstance(run_id, str) or turn_index != 1:
                    raise PromptBudgetGuardError(
                        "V2_PROMPT_GUARD_TOKEN_PLAN_INVALID",
                        "history-independent pilot request must be turn one",
                        TOKENIZER_RUNTIME_PATH,
                    )
                trajectory = by_run.get(run_id)
                if trajectory is None:
                    raise PromptBudgetGuardError(
                        "V2_PROMPT_GUARD_SCHEDULE_INVALID",
                        "pilot run identity is missing from schedule",
                        PILOT_SCHEDULE_PATH,
                    )
                episode_id = trajectory.get("episode_id")
                condition_id = trajectory.get("condition_id")
                if not isinstance(episode_id, str) or not isinstance(condition_id, str):
                    raise PromptBudgetGuardError(
                        "V2_PROMPT_GUARD_SCHEDULE_INVALID",
                        "pilot trajectory prompt identity is invalid",
                        PILOT_SCHEDULE_PATH,
                    )
                episode = episodes.get(episode_id)
                if episode is None:
                    raise PromptBudgetGuardError(
                        "V2_PROMPT_GUARD_EPISODES_INVALID",
                        "pilot episode is missing",
                        ACCEPTED_EPISODES_PATH,
                    )
                known_sha = _sha256_messages(
                    build_pilot_messages(
                        condition_id=condition_id,
                        static_prompt=static_prompt,
                        episode=episode,
                        source_map=source_map,
                        turn_index=1,
                        history=[],
                    )
                )
        bindings.append(
            PromptSlotBinding(
                sequence_index=expected_index,
                request_id=request_id,
                phase=phase,
                history_dependency=cast(Literal["none", "prior_admitted_history"], dependency),
                known_messages_sha256=known_sha,
            )
        )
    return tuple(bindings)


def build_materialization(repo_root: Path) -> MaterializationV1:
    compiler_spec = _load_object(repo_root, COMPILER_SPEC_PATH)
    admission_spec = _load_object(repo_root, STANDALONE_ADMISSION_SPEC_PATH)
    static_prompt = build_static_system_prompt(compiler_spec, admission_spec)
    case_ids, episodes, source_map = _selected_material(repo_root)
    bindings = _request_slot_bindings(repo_root, static_prompt, episodes, source_map)
    return MaterializationV1(
        static_system_prompt_sha256=_sha256_text(static_prompt),
        selected_episode_ids=cast(tuple[str, str, str, str, str, str], case_ids),
        required_source_ids=tuple(sorted(source_map)),
        request_slots=bindings,
        source=_receipt(repo_root, SOURCE_PATH),
        standalone_runtime_v2=_receipt(repo_root, RUNTIME_V2_PATH),
        pilot_schedule=_receipt(repo_root, PILOT_SCHEDULE_PATH),
        neutral_plan=_receipt(repo_root, NEUTRAL_PLAN_PATH),
        tokenizer_runtime=_receipt(repo_root, TOKENIZER_RUNTIME_PATH),
        accepted_episodes=_receipt(repo_root, ACCEPTED_EPISODES_PATH),
        runtime_selection=_receipt(repo_root, RUNTIME_SELECTION_PATH),
        source_manifest=_receipt(repo_root, SOURCE_MANIFEST_PATH),
        compiler_spec=_receipt(repo_root, COMPILER_SPEC_PATH),
        standalone_admission_spec=_receipt(repo_root, STANDALONE_ADMISSION_SPEC_PATH),
    )


def _artifact_bytes(value: LocalABCContract) -> bytes:
    return (value.canonical_json() + "\n").encode("utf-8")


def materialize(repo_root: Path) -> dict[str, object]:
    materialization = build_materialization(repo_root.resolve())
    output = repo_root.resolve() / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_artifact_bytes(materialization))
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_PROMPT_REALIZATION_GUARD_PASS",
        "request_slot_count": len(materialization.request_slots),
        "accepted_tokenizer_envelope_proof_complete": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected = build_materialization(root)
    try:
        observed = MaterializationV1.model_validate_json((root / OUTPUT_PATH).read_bytes())
    except (FileNotFoundError, ValidationError) as exc:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_OUTPUT_INVALID",
            "prompt-realization guard output is missing or invalid",
            OUTPUT_PATH,
        ) from exc
    if observed != expected:
        raise PromptBudgetGuardError(
            "V2_PROMPT_GUARD_OUTPUT_DRIFT",
            "prompt-realization guard output is not deterministic",
            OUTPUT_PATH,
        )
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_PROMPT_REALIZATION_GUARD_VALID",
        "request_slot_count": len(observed.request_slots),
        "accepted_tokenizer_envelope_proof_complete": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("materialize", "validate"))
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    result = (
        materialize(args.repo_root) if args.command == "materialize" else validate(args.repo_root)
    )
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
