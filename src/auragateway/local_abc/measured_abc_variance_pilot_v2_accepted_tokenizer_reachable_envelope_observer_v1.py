"""Observe the history-independent V2 prompt frontier with the accepted tokenizer."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import subprocess
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

prompt_guard = importlib.import_module(
    "auragateway.local_abc."
    "measured_abc_variance_pilot_v2_prompt_realization_and_reachable_budget_guard_v1"
)

PROMPT_GUARD_ARTIFACT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/prompt_realization_and_reachable_budget_guard_v1.json"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "measured_abc_variance_pilot_v2_accepted_tokenizer_reachable_envelope_observer_v1.py"
)
DRIVER_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "measured_abc_variance_pilot_v2_accepted_tokenizer_reachable_envelope_driver_v1.py"
)
OUTPUT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/"
    "accepted_tokenizer_reachable_envelope_observation_v1.json"
)

EXPECTED_REQUEST_COUNT: Final = 240
EXPECTED_OBSERVED_COUNT: Final = 78
EXPECTED_DEFERRED_COUNT: Final = 162
MAX_MODEL_LEN: Final = 4096
MAX_OUTPUT_TOKENS: Final = 256
MAX_PROMPT_TOKENS: Final = MAX_MODEL_LEN - MAX_OUTPUT_TOKENS
NEXT_GATE: Final = "REVIEW_VARIANCE_PILOT_SUCCESSOR_V2_EXECUTION_AUTHORIZATION_V1"


class AcceptedTokenizerReachableEnvelopeError(RuntimeError):
    """Metadata-safe accepted-tokenizer observation failure."""

    def __init__(self, error_code: str, safe_message: str, path: Path | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class ArtifactReceipt(LocalABCContract):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class ObservationRequestRow(LocalABCContract):
    sequence_index: int = Field(ge=0, lt=EXPECTED_REQUEST_COUNT)
    request_id: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    messages_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    messages: tuple[dict[str, str], dict[str, str]]


class ObservationRow(LocalABCContract):
    sequence_index: int = Field(ge=0, lt=EXPECTED_REQUEST_COUNT)
    request_id: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    messages_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rendered_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_token_count: int = Field(ge=1, le=MAX_PROMPT_TOKENS)
    token_id_parity: Literal[True] = True


class TokenizerSurfaceIdentity(LocalABCContract):
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    transformers_version: Literal["5.14.1"] = "5.14.1"
    tokenizer_class: Literal["Qwen2Tokenizer"] = "Qwen2Tokenizer"
    chat_template_sha256: Literal[
        "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"
    ] = "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"
    tokenizer_json_sha256: Literal[
        "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
    ] = "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
    tokenizer_config_sha256: Literal[
        "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"
    ] = "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"
    vocab_sha256: Literal["ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"] = (
        "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"
    )
    merges_sha256: Literal["599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3"] = (
        "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3"
    )
    local_files_only: Literal[True] = True


class ReachableEnvelopeObservationV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    observation_id: Literal[
        "auragateway-variance-pilot-v2-accepted-tokenizer-reachable-envelope-observation-v1"
    ] = "auragateway-variance-pilot-v2-accepted-tokenizer-reachable-envelope-observation-v1"
    tokenizer: TokenizerSurfaceIdentity
    request_slot_count: Literal[240] = EXPECTED_REQUEST_COUNT
    observed_history_independent_request_count: Literal[78] = EXPECTED_OBSERVED_COUNT
    deferred_history_dependent_request_count: Literal[162] = EXPECTED_DEFERRED_COUNT
    rows: tuple[ObservationRow, ...] = Field(
        min_length=EXPECTED_OBSERVED_COUNT,
        max_length=EXPECTED_OBSERVED_COUNT,
    )
    maximum_observed_prompt_tokens: int = Field(ge=1, le=MAX_PROMPT_TOKENS)
    minimum_observed_prompt_budget_headroom_tokens: int = Field(ge=0, le=MAX_PROMPT_TOKENS)
    accepted_tokenizer_surface_qualified: Literal[True] = True
    history_independent_prompt_observation_complete: Literal[True] = True
    history_dependent_prompt_counts_preobserved: Literal[False] = False
    all_240_future_prompt_counts_claimed: Literal[False] = False
    accepted_tokenizer_full_future_envelope_proof_complete: Literal[False] = False
    static_prior_assistant_256_token_allowance_relied_on: Literal[False] = False
    runtime_prospective_next_prompt_guard_required: Literal[True] = True
    model_loaded: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    external_network_requests_performed: Literal[0] = 0
    prompt_guard_artifact: ArtifactReceipt
    observer_source: ArtifactReceipt
    tokenizer_driver_source: ArtifactReceipt
    pilot_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal["REVIEW_VARIANCE_PILOT_SUCCESSOR_V2_EXECUTION_AUTHORIZATION_V1"] = NEXT_GATE

    @model_validator(mode="after")
    def validate_rows(self) -> Self:
        if len({row.sequence_index for row in self.rows}) != EXPECTED_OBSERVED_COUNT:
            raise ValueError("observed tokenizer sequence indexes must be unique")
        if len({row.request_id for row in self.rows}) != EXPECTED_OBSERVED_COUNT:
            raise ValueError("observed tokenizer request IDs must be unique")
        maximum = max(row.prompt_token_count for row in self.rows)
        if self.maximum_observed_prompt_tokens != maximum:
            raise ValueError("maximum observed prompt token count drifted")
        expected_headroom = MAX_PROMPT_TOKENS - maximum
        if self.minimum_observed_prompt_budget_headroom_tokens != expected_headroom:
            raise ValueError("observed prompt-budget headroom drifted")
        return self


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_REQUIRED_FILE_MISSING",
            "required tokenizer-observation file is missing or unsafe",
            relative,
        )
    raw = path.read_bytes()
    return ArtifactReceipt(path=relative.as_posix(), sha256=_sha256_bytes(raw), size_bytes=len(raw))


def _messages_sha256(messages: list[dict[str, str]]) -> str:
    return _sha256_text(prompt_guard.canonical_json(messages))


def build_observation_request(repo_root: Path) -> tuple[ObservationRequestRow, ...]:
    root = repo_root.resolve()
    frozen = prompt_guard.build_materialization(root)
    compiler_spec = prompt_guard._load_object(root, prompt_guard.COMPILER_SPEC_PATH)
    admission_spec = prompt_guard._load_object(root, prompt_guard.STANDALONE_ADMISSION_SPEC_PATH)
    static_prompt = prompt_guard.build_static_system_prompt(compiler_spec, admission_spec)
    if frozen.static_system_prompt_sha256 != _sha256_text(static_prompt):
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_STATIC_PROMPT_DRIFT",
            "static prompt identity drifted from the prompt guard",
            PROMPT_GUARD_ARTIFACT_PATH,
        )

    _, episodes, source_map = prompt_guard._selected_material(root)
    schedule = prompt_guard._load_object(root, prompt_guard.PILOT_SCHEDULE_PATH)
    trajectories = schedule.get("trajectories")
    if not isinstance(trajectories, list) or len(trajectories) != 54:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_SCHEDULE_INVALID",
            "pilot schedule must contain 54 trajectories",
            prompt_guard.PILOT_SCHEDULE_PATH,
        )
    by_run = {
        cast(str, raw["run_id"]): cast(dict[str, object], raw)
        for raw in trajectories
        if isinstance(raw, dict) and isinstance(raw.get("run_id"), str)
    }
    if len(by_run) != 54:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_SCHEDULE_INVALID",
            "pilot trajectory identities are invalid",
            prompt_guard.PILOT_SCHEDULE_PATH,
        )

    token_material = prompt_guard._load_object(root, prompt_guard.TOKENIZER_RUNTIME_PATH)
    plan = token_material.get("tokenizer_budget_plan")
    if not isinstance(plan, dict):
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
            "tokenizer budget plan is missing",
            prompt_guard.TOKENIZER_RUNTIME_PATH,
        )
    raw_requests = plan.get("requests")
    if not isinstance(raw_requests, list) or len(raw_requests) != EXPECTED_REQUEST_COUNT:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
            "tokenizer budget plan must contain exactly 240 requests",
            prompt_guard.TOKENIZER_RUNTIME_PATH,
        )

    rows: list[ObservationRequestRow] = []
    deferred = 0
    for slot, raw_request in zip(frozen.request_slots, raw_requests, strict=True):
        if not isinstance(raw_request, dict):
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
                "tokenizer request row is invalid",
                prompt_guard.TOKENIZER_RUNTIME_PATH,
            )
        if slot.history_dependency == "prior_admitted_history":
            deferred += 1
            continue
        request_id = raw_request.get("request_id")
        phase = raw_request.get("phase")
        if request_id != slot.request_id or phase != slot.phase:
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_REQUEST_IDENTITY_DRIFT",
                "tokenizer request identity drifted across frozen artifacts",
            )
        if not isinstance(request_id, str) or not isinstance(phase, str):
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
                "tokenizer request identity is invalid",
                prompt_guard.TOKENIZER_RUNTIME_PATH,
            )

        if phase != "pilot":
            messages = prompt_guard.build_neutral_messages(phase, static_prompt)
        else:
            run_id = raw_request.get("pilot_run_id")
            turn_index = raw_request.get("pilot_turn_index")
            if not isinstance(run_id, str) or turn_index != 1:
                raise AcceptedTokenizerReachableEnvelopeError(
                    "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
                    "history-independent pilot request must be turn one",
                    prompt_guard.TOKENIZER_RUNTIME_PATH,
                )
            trajectory = by_run.get(run_id)
            if trajectory is None:
                raise AcceptedTokenizerReachableEnvelopeError(
                    "V2_ACCEPTED_TOKENIZER_SCHEDULE_INVALID",
                    "pilot trajectory is missing",
                    prompt_guard.PILOT_SCHEDULE_PATH,
                )
            episode_id = trajectory.get("episode_id")
            condition_id = trajectory.get("condition_id")
            if not isinstance(episode_id, str) or not isinstance(condition_id, str):
                raise AcceptedTokenizerReachableEnvelopeError(
                    "V2_ACCEPTED_TOKENIZER_SCHEDULE_INVALID",
                    "pilot trajectory prompt identity is invalid",
                    prompt_guard.PILOT_SCHEDULE_PATH,
                )
            episode = episodes.get(episode_id)
            if episode is None:
                raise AcceptedTokenizerReachableEnvelopeError(
                    "V2_ACCEPTED_TOKENIZER_EPISODES_INVALID",
                    "pilot episode is missing",
                    prompt_guard.ACCEPTED_EPISODES_PATH,
                )
            messages = prompt_guard.build_pilot_messages(
                condition_id=condition_id,
                static_prompt=static_prompt,
                episode=episode,
                source_map=source_map,
                turn_index=1,
                history=[],
            )

        messages_sha = _messages_sha256(messages)
        if slot.known_messages_sha256 != messages_sha:
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_MESSAGES_IDENTITY_DRIFT",
                "history-independent prompt identity drifted",
                PROMPT_GUARD_ARTIFACT_PATH,
            )
        if len(messages) != 2:
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_MESSAGES_SHAPE_INVALID",
                "history-independent prompt must contain exactly two messages",
            )
        rows.append(
            ObservationRequestRow(
                sequence_index=slot.sequence_index,
                request_id=request_id,
                phase=phase,
                messages_sha256=messages_sha,
                messages=cast(tuple[dict[str, str], dict[str, str]], tuple(messages)),
            )
        )

    if len(rows) != EXPECTED_OBSERVED_COUNT or deferred != EXPECTED_DEFERRED_COUNT:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_FRONTIER_COUNT_DRIFT",
            "reachable tokenizer observation frontier count drifted",
        )
    return tuple(rows)


def _run_driver(
    repo_root: Path,
    tokenizer_python: Path,
    snapshot: Path,
    rows: tuple[ObservationRequestRow, ...],
) -> dict[str, object]:
    if not tokenizer_python.is_file():
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_PYTHON_MISSING",
            "preserved tokenizer Python executable is missing",
        )
    if not snapshot.is_dir():
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_SNAPSHOT_MISSING",
            "accepted tokenizer snapshot directory is missing",
        )
    driver = repo_root / DRIVER_PATH
    if not driver.is_file() or driver.is_symlink():
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_DRIVER_MISSING",
            "accepted tokenizer driver is missing or unsafe",
            DRIVER_PATH,
        )
    payload = {
        "schema_version": "1.0.0",
        "rows": [row.model_dump(mode="json") for row in rows],
    }
    environment = os.environ.copy()
    environment["HF_HUB_OFFLINE"] = "1"
    environment["TRANSFORMERS_OFFLINE"] = "1"
    completed = subprocess.run(
        [str(tokenizer_python), str(driver), "--snapshot", str(snapshot)],
        input=prompt_guard.canonical_json(payload) + "\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        env=environment,
        check=False,
    )
    if completed.returncode != 0:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_DRIVER_FAILED",
            "accepted tokenizer driver failed closed",
            DRIVER_PATH,
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_DRIVER_OUTPUT_INVALID",
            "accepted tokenizer driver output is invalid",
            DRIVER_PATH,
        ) from exc
    if not isinstance(result, dict):
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_DRIVER_OUTPUT_INVALID",
            "accepted tokenizer driver output root is invalid",
            DRIVER_PATH,
        )
    return cast(dict[str, object], result)


def _validate_driver_result(
    repo_root: Path,
    request_rows: tuple[ObservationRequestRow, ...],
    raw_result: dict[str, object],
) -> ReachableEnvelopeObservationV1:
    file_hashes = raw_result.get("tokenizer_file_sha256")
    if not isinstance(file_hashes, dict):
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_IDENTITY_INVALID",
            "accepted tokenizer file identities are missing",
        )
    try:
        identity = TokenizerSurfaceIdentity(
            transformers_version=raw_result.get("transformers_version"),
            tokenizer_class=raw_result.get("tokenizer_class"),
            chat_template_sha256=raw_result.get("chat_template_sha256"),
            tokenizer_json_sha256=file_hashes.get("tokenizer.json"),
            tokenizer_config_sha256=file_hashes.get("tokenizer_config.json"),
            vocab_sha256=file_hashes.get("vocab.json"),
            merges_sha256=file_hashes.get("merges.txt"),
            local_files_only=raw_result.get("local_files_only"),
        )
    except ValidationError as exc:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_IDENTITY_DRIFT",
            "accepted tokenizer identity drifted",
        ) from exc
    if (
        raw_result.get("model_loaded") is not False
        or raw_result.get("model_requests_performed") != 0
        or raw_result.get("gpu_execution_performed") is not False
        or raw_result.get("external_network_requests_performed") != 0
    ):
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_EXECUTION_BOUNDARY_VIOLATION",
            "tokenizer observation crossed its execution boundary",
        )

    raw_rows = raw_result.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != EXPECTED_OBSERVED_COUNT:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_OBSERVATION_COUNT_INVALID",
            "accepted tokenizer observation row count drifted",
        )
    observed: list[ObservationRow] = []
    for request_row, raw_row in zip(request_rows, raw_rows, strict=True):
        if not isinstance(raw_row, dict):
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_OBSERVATION_ROW_INVALID",
                "accepted tokenizer observation row is invalid",
            )
        payload = dict(cast(dict[str, object], raw_row))
        payload["phase"] = request_row.phase
        try:
            row = ObservationRow.model_validate(payload)
        except ValidationError as exc:
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_OBSERVATION_ROW_INVALID",
                "accepted tokenizer observation row violated its contract",
            ) from exc
        if (
            row.sequence_index != request_row.sequence_index
            or row.request_id != request_row.request_id
            or row.messages_sha256 != request_row.messages_sha256
        ):
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_OBSERVATION_IDENTITY_DRIFT",
                "accepted tokenizer observation row identity drifted",
            )
        observed.append(row)

    maximum = max(row.prompt_token_count for row in observed)
    return ReachableEnvelopeObservationV1(
        tokenizer=identity,
        rows=tuple(observed),
        maximum_observed_prompt_tokens=maximum,
        minimum_observed_prompt_budget_headroom_tokens=MAX_PROMPT_TOKENS - maximum,
        prompt_guard_artifact=_receipt(repo_root, PROMPT_GUARD_ARTIFACT_PATH),
        observer_source=_receipt(repo_root, SOURCE_PATH),
        tokenizer_driver_source=_receipt(repo_root, DRIVER_PATH),
    )


def observe(repo_root: Path, tokenizer_python: Path, snapshot: Path) -> dict[str, object]:
    root = repo_root.resolve()
    rows = build_observation_request(root)
    raw_result = _run_driver(root, tokenizer_python.resolve(), snapshot.resolve(), rows)
    observation = _validate_driver_result(root, rows, raw_result)
    output = root / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((observation.canonical_json() + "\n").encode("utf-8"))
    return _summary(
        observation,
        "VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_TOKENIZER_REACHABLE_ENVELOPE_PASS",
    )


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    path = root / OUTPUT_PATH
    try:
        observation = ReachableEnvelopeObservationV1.model_validate_json(path.read_bytes())
    except (FileNotFoundError, ValidationError) as exc:
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_OBSERVATION_ARTIFACT_INVALID",
            "accepted tokenizer observation artifact is missing or invalid",
            OUTPUT_PATH,
        ) from exc
    if observation.prompt_guard_artifact != _receipt(root, PROMPT_GUARD_ARTIFACT_PATH):
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_PROMPT_GUARD_RECEIPT_DRIFT",
            "prompt guard receipt drifted after tokenizer observation",
            PROMPT_GUARD_ARTIFACT_PATH,
        )
    if observation.observer_source != _receipt(root, SOURCE_PATH):
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_OBSERVER_RECEIPT_DRIFT",
            "tokenizer observer source receipt drifted",
            SOURCE_PATH,
        )
    if observation.tokenizer_driver_source != _receipt(root, DRIVER_PATH):
        raise AcceptedTokenizerReachableEnvelopeError(
            "V2_ACCEPTED_TOKENIZER_DRIVER_RECEIPT_DRIFT",
            "tokenizer driver source receipt drifted",
            DRIVER_PATH,
        )
    request_rows = build_observation_request(root)
    by_index = {row.sequence_index: row for row in request_rows}
    for row in observation.rows:
        expected = by_index.get(row.sequence_index)
        if expected is None or expected.request_id != row.request_id:
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_OBSERVATION_IDENTITY_DRIFT",
                "persisted tokenizer observation no longer matches frozen prompts",
            )
        if expected.messages_sha256 != row.messages_sha256:
            raise AcceptedTokenizerReachableEnvelopeError(
                "V2_ACCEPTED_TOKENIZER_MESSAGES_IDENTITY_DRIFT",
                "persisted tokenizer message identity drifted",
            )
    return _summary(
        observation,
        "VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_TOKENIZER_REACHABLE_ENVELOPE_VALID",
    )


def _summary(observation: ReachableEnvelopeObservationV1, status: str) -> dict[str, object]:
    return {
        "status": status,
        "observed_history_independent_request_count": EXPECTED_OBSERVED_COUNT,
        "deferred_history_dependent_request_count": EXPECTED_DEFERRED_COUNT,
        "maximum_observed_prompt_tokens": observation.maximum_observed_prompt_tokens,
        "minimum_observed_prompt_budget_headroom_tokens": (
            observation.minimum_observed_prompt_budget_headroom_tokens
        ),
        "accepted_tokenizer_surface_qualified": True,
        "history_dependent_prompt_counts_preobserved": False,
        "accepted_tokenizer_full_future_envelope_proof_complete": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "external_network_requests_performed": 0,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("observe", "validate"))
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--tokenizer-python", type=Path)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "observe":
            if args.tokenizer_python is None or args.snapshot is None:
                raise AcceptedTokenizerReachableEnvelopeError(
                    "V2_ACCEPTED_TOKENIZER_OBSERVATION_ARGUMENT_MISSING",
                    "observe requires tokenizer Python and snapshot paths",
                )
            result = observe(args.repo_root, args.tokenizer_python, args.snapshot)
        else:
            result = validate(args.repo_root)
    except AcceptedTokenizerReachableEnvelopeError as exc:
        print(
            prompt_guard.canonical_json(
                {
                    "status": "ERROR",
                    "error_code": exc.error_code,
                    "safe_message": exc.safe_message,
                    "path": exc.path.as_posix() if exc.path is not None else None,
                }
            )
        )
        return 1
    print(prompt_guard.canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
