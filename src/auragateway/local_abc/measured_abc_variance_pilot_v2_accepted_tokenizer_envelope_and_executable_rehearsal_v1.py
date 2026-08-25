"""Accepted-tokenizer envelope contract and executable rehearsal for variance-pilot V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import types
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

TOKENIZER_RUNTIME_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/tokenizer_budget_and_standalone_runtime_v1.json"
)
ACCEPTED_RUNTIME_INTEGRATION_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/accepted_runtime_integration_v1.json"
)
STANDALONE_RUNTIME_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_standalone_runtime_v1.py"
)
REHEARSAL_PAYLOAD_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_executable_rehearsal_payload_v1.py"
)
ADMISSION_SPEC_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json"
)
OUTPUT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/"
    "accepted_tokenizer_envelope_and_executable_rehearsal_v1.json"
)

MAX_MODEL_LEN: Final = 4096
MAX_OUTPUT_TOKENS: Final = 256
MAX_PROMPT_ENVELOPE_TOKENS: Final = MAX_MODEL_LEN - MAX_OUTPUT_TOKENS
EXPECTED_REQUEST_COUNT: Final = 240
RUNTIME_MODULE_NAME: Final = "auragateway.local_abc._variance_pilot_v2_rehearsal_runtime"
PAYLOAD_MODULE_NAME: Final = "auragateway.local_abc._variance_pilot_v2_rehearsal_payload"
NEXT_GATE: Final = "OBSERVE_VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_TOKENIZER_ENVELOPE_V1"


class TokenizerEnvelopeRehearsalError(RuntimeError):
    """Metadata-safe tokenizer-envelope or rehearsal failure."""

    def __init__(self, error_code: str, safe_message: str, path: Path | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class ArtifactReceipt(LocalABCContract):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class AcceptedTokenizerIdentity(LocalABCContract):
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    transformers: Literal["5.14.1"] = "5.14.1"
    max_model_len: Literal[4096] = MAX_MODEL_LEN
    max_output_tokens: Literal[256] = MAX_OUTPUT_TOKENS


class TokenizerEnvelopeSlot(LocalABCContract):
    sequence_index: int = Field(ge=0, lt=EXPECTED_REQUEST_COUNT)
    request_id: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    prior_assistant_message_count: int = Field(ge=0, le=3)
    prior_assistant_token_allowance: int = Field(ge=0, le=3 * MAX_OUTPUT_TOKENS)
    maximum_prompt_envelope_tokens: Literal[3840] = MAX_PROMPT_ENVELOPE_TOKENS

    @model_validator(mode="after")
    def validate_allowance(self) -> Self:
        expected = self.prior_assistant_message_count * MAX_OUTPUT_TOKENS
        if self.prior_assistant_token_allowance != expected:
            raise ValueError("prior assistant token allowance drifted")
        return self


class AcceptedTokenizerEnvelopeRequestV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-variance-pilot-v2-accepted-tokenizer-envelope-v1"] = (
        "auragateway-variance-pilot-v2-accepted-tokenizer-envelope-v1"
    )
    tokenizer: AcceptedTokenizerIdentity = AcceptedTokenizerIdentity()
    slots: tuple[TokenizerEnvelopeSlot, ...] = Field(
        min_length=EXPECTED_REQUEST_COUNT,
        max_length=EXPECTED_REQUEST_COUNT,
    )
    proof_method: Literal["ACCEPTED_CHAT_TEMPLATE_SEGMENT_SUM_PLUS_PRIOR_OUTPUT_TOKEN_CAP_V1"] = (
        "ACCEPTED_CHAT_TEMPLATE_SEGMENT_SUM_PLUS_PRIOR_OUTPUT_TOKEN_CAP_V1"
    )
    exact_future_assistant_outputs_claimed: Literal[False] = False
    accepted_runtime_observation_required: Literal[True] = True
    accepted_tokenizer_envelope_proof_complete: Literal[False] = False
    model_requests_required: Literal[False] = False
    gpu_required: Literal[False] = False
    external_network_requests_permitted: Literal[0] = 0
    pilot_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_slots(self) -> Self:
        indexes = tuple(item.sequence_index for item in self.slots)
        if indexes != tuple(range(EXPECTED_REQUEST_COUNT)):
            raise ValueError("accepted-tokenizer envelope indexes must be contiguous")
        request_ids = tuple(item.request_id for item in self.slots)
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("accepted-tokenizer envelope request IDs must be unique")
        return self


class AcceptedTokenizerObservationRow(LocalABCContract):
    sequence_index: int = Field(ge=0, lt=EXPECTED_REQUEST_COUNT)
    request_id: str = Field(min_length=1)
    known_segment_token_count: int = Field(ge=0)
    prior_assistant_token_allowance: int = Field(ge=0, le=3 * MAX_OUTPUT_TOKENS)
    envelope_prompt_token_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_envelope(self) -> Self:
        expected = self.known_segment_token_count + self.prior_assistant_token_allowance
        if self.envelope_prompt_token_count != expected:
            raise ValueError("accepted-tokenizer envelope arithmetic drifted")
        return self


class AcceptedTokenizerEnvelopeObservationV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    observation_id: Literal[
        "auragateway-variance-pilot-v2-accepted-tokenizer-envelope-observation-v1"
    ] = "auragateway-variance-pilot-v2-accepted-tokenizer-envelope-observation-v1"
    tokenizer: AcceptedTokenizerIdentity = AcceptedTokenizerIdentity()
    proof_method: Literal["ACCEPTED_CHAT_TEMPLATE_SEGMENT_SUM_PLUS_PRIOR_OUTPUT_TOKEN_CAP_V1"] = (
        "ACCEPTED_CHAT_TEMPLATE_SEGMENT_SUM_PLUS_PRIOR_OUTPUT_TOKEN_CAP_V1"
    )
    rows: tuple[AcceptedTokenizerObservationRow, ...] = Field(
        min_length=EXPECTED_REQUEST_COUNT,
        max_length=EXPECTED_REQUEST_COUNT,
    )
    model_loaded: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    external_network_requests_performed: Literal[0] = 0


class AcceptedTokenizerEnvelopeProofV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["ACCEPTED_TOKENIZER_ENVELOPE_PASS"] = "ACCEPTED_TOKENIZER_ENVELOPE_PASS"
    observed_request_count: Literal[240] = EXPECTED_REQUEST_COUNT
    maximum_observed_envelope_prompt_tokens: int = Field(ge=0, le=MAX_PROMPT_ENVELOPE_TOKENS)
    minimum_headroom_tokens: int = Field(ge=MAX_OUTPUT_TOKENS, le=MAX_MODEL_LEN)
    accepted_tokenizer_envelope_proof_complete: Literal[True] = True
    pilot_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False


class ExecutableRehearsalResultV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["EXECUTABLE_REHEARSAL_PASS"] = "EXECUTABLE_REHEARSAL_PASS"
    module_type_loader_used: Literal[True] = True
    sys_modules_registration_used: Literal[True] = True
    runtime_module_registered_during_execution: Literal[True] = True
    runtime_injection_used: Literal[True] = True
    fake_worker_request_count: Literal[4] = 4
    token_budget_check_count: Literal[4] = 4
    completed_turn_count: Literal[4] = 4
    request_attempt_count: Literal[4] = 4
    history_entry_count: Literal[8] = 8
    system_exit_zero_handled: Literal[True] = True
    module_registry_cleanup_complete: Literal[True] = True
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False


class MaterializationV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    envelope_request: AcceptedTokenizerEnvelopeRequestV1
    executable_rehearsal: ExecutableRehearsalResultV1
    tokenizer_runtime_contract: ArtifactReceipt
    accepted_runtime_integration: ArtifactReceipt
    standalone_runtime_source: ArtifactReceipt
    rehearsal_payload_source: ArtifactReceipt
    standalone_admission_spec: ArtifactReceipt
    accepted_tokenizer_envelope_proof_complete: Literal[False] = False
    executable_rehearsal_complete: Literal[True] = True
    live_runtime_executable_generated: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal["OBSERVE_VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_TOKENIZER_ENVELOPE_V1"] = (
        NEXT_GATE
    )


def _canonical_bytes(value: object) -> bytes:
    if isinstance(value, LocalABCContract):
        value = value.model_dump(mode="json")
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise TokenizerEnvelopeRehearsalError(
            "V2_TOKENIZER_REHEARSAL_REQUIRED_FILE_MISSING",
            "required tokenizer-envelope or rehearsal file is missing or unsafe",
            relative,
        )
    raw = path.read_bytes()
    return ArtifactReceipt(path=relative.as_posix(), sha256=_sha256(raw), size_bytes=len(raw))


def _load_object(repo_root: Path, relative: Path) -> dict[str, object]:
    path = repo_root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TokenizerEnvelopeRehearsalError(
            "V2_TOKENIZER_REHEARSAL_REQUIRED_FILE_MISSING",
            "required tokenizer-envelope or rehearsal JSON is missing",
            relative,
        ) from exc
    except json.JSONDecodeError as exc:
        raise TokenizerEnvelopeRehearsalError(
            "V2_TOKENIZER_REHEARSAL_JSON_INVALID",
            "required tokenizer-envelope or rehearsal JSON is invalid",
            relative,
        ) from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise TokenizerEnvelopeRehearsalError(
            "V2_TOKENIZER_REHEARSAL_JSON_ROOT_INVALID",
            "required tokenizer-envelope or rehearsal JSON root must be an object",
            relative,
        )
    return cast(dict[str, object], value)


def _accepted_tokenizer_identity(repo_root: Path) -> AcceptedTokenizerIdentity:
    integration = _load_object(repo_root, ACCEPTED_RUNTIME_INTEGRATION_PATH)
    accepted_runtime = integration.get("accepted_runtime")
    if not isinstance(accepted_runtime, dict):
        raise TokenizerEnvelopeRehearsalError(
            "V2_ACCEPTED_TOKENIZER_RUNTIME_IDENTITY_INVALID",
            "accepted runtime identity is missing",
            ACCEPTED_RUNTIME_INTEGRATION_PATH,
        )
    payload = cast(dict[str, object], accepted_runtime)
    try:
        return AcceptedTokenizerIdentity.model_validate(
            {
                "model_repository": payload.get("model_repository"),
                "model_revision": payload.get("model_revision"),
                "transformers": payload.get("transformers"),
            }
        )
    except ValidationError as exc:
        raise TokenizerEnvelopeRehearsalError(
            "V2_ACCEPTED_TOKENIZER_RUNTIME_IDENTITY_DRIFT",
            "accepted runtime tokenizer identity drifted",
            ACCEPTED_RUNTIME_INTEGRATION_PATH,
        ) from exc


def build_envelope_request(repo_root: Path) -> AcceptedTokenizerEnvelopeRequestV1:
    """Bind all 240 request slots without claiming future assistant output text."""

    materialization = _load_object(repo_root, TOKENIZER_RUNTIME_PATH)
    plan = materialization.get("tokenizer_budget_plan")
    if not isinstance(plan, dict):
        raise TokenizerEnvelopeRehearsalError(
            "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
            "tokenizer budget plan is missing",
            TOKENIZER_RUNTIME_PATH,
        )
    raw_requests = plan.get("requests")
    if not isinstance(raw_requests, list) or len(raw_requests) != EXPECTED_REQUEST_COUNT:
        raise TokenizerEnvelopeRehearsalError(
            "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
            "tokenizer budget plan must contain exactly 240 requests",
            TOKENIZER_RUNTIME_PATH,
        )

    slots: list[TokenizerEnvelopeSlot] = []
    for expected_index, raw_request in enumerate(raw_requests):
        if not isinstance(raw_request, dict):
            raise TokenizerEnvelopeRehearsalError(
                "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
                "tokenizer budget request row is invalid",
                TOKENIZER_RUNTIME_PATH,
            )
        request = cast(dict[str, object], raw_request)
        request_id = request.get("request_id")
        phase = request.get("phase")
        turn_index = request.get("pilot_turn_index")
        if request.get("sequence_index") != expected_index:
            raise TokenizerEnvelopeRehearsalError(
                "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
                "tokenizer budget request sequence drifted",
                TOKENIZER_RUNTIME_PATH,
            )
        if not isinstance(request_id, str) or not isinstance(phase, str):
            raise TokenizerEnvelopeRehearsalError(
                "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
                "tokenizer budget request identity is invalid",
                TOKENIZER_RUNTIME_PATH,
            )
        prior_count = 0
        if turn_index is not None:
            if (
                not isinstance(turn_index, int)
                or isinstance(turn_index, bool)
                or turn_index not in range(1, 5)
            ):
                raise TokenizerEnvelopeRehearsalError(
                    "V2_ACCEPTED_TOKENIZER_PLAN_INVALID",
                    "pilot turn index is invalid",
                    TOKENIZER_RUNTIME_PATH,
                )
            prior_count = turn_index - 1
        slots.append(
            TokenizerEnvelopeSlot(
                sequence_index=expected_index,
                request_id=request_id,
                phase=phase,
                prior_assistant_message_count=prior_count,
                prior_assistant_token_allowance=prior_count * MAX_OUTPUT_TOKENS,
            )
        )

    return AcceptedTokenizerEnvelopeRequestV1(
        tokenizer=_accepted_tokenizer_identity(repo_root),
        slots=tuple(slots),
    )


def validate_accepted_tokenizer_observation(
    repo_root: Path,
    raw_observation: object,
) -> AcceptedTokenizerEnvelopeProofV1:
    """Validate a future accepted-runtime envelope observation without granting authority."""

    try:
        observation = AcceptedTokenizerEnvelopeObservationV1.model_validate(raw_observation)
    except ValidationError as exc:
        raise TokenizerEnvelopeRehearsalError(
            "V2_ACCEPTED_TOKENIZER_OBSERVATION_INVALID",
            "accepted-tokenizer envelope observation is invalid",
        ) from exc
    request = build_envelope_request(repo_root)
    if observation.tokenizer != request.tokenizer:
        raise TokenizerEnvelopeRehearsalError(
            "V2_ACCEPTED_TOKENIZER_IDENTITY_DRIFT",
            "accepted-tokenizer envelope observation used a different tokenizer identity",
        )
    if len(observation.rows) != len(request.slots):
        raise TokenizerEnvelopeRehearsalError(
            "V2_ACCEPTED_TOKENIZER_OBSERVATION_COUNT_INVALID",
            "accepted-tokenizer envelope observation count drifted",
        )

    maximum = 0
    for slot, row in zip(request.slots, observation.rows, strict=True):
        if row.sequence_index != slot.sequence_index or row.request_id != slot.request_id:
            raise TokenizerEnvelopeRehearsalError(
                "V2_ACCEPTED_TOKENIZER_OBSERVATION_IDENTITY_DRIFT",
                "accepted-tokenizer envelope row identity drifted",
            )
        if row.prior_assistant_token_allowance != slot.prior_assistant_token_allowance:
            raise TokenizerEnvelopeRehearsalError(
                "V2_ACCEPTED_TOKENIZER_OBSERVATION_ALLOWANCE_DRIFT",
                "accepted-tokenizer history allowance drifted",
            )
        if row.envelope_prompt_token_count > MAX_PROMPT_ENVELOPE_TOKENS:
            raise TokenizerEnvelopeRehearsalError(
                "V2_ACCEPTED_TOKENIZER_ENVELOPE_EXCEEDED",
                "accepted-tokenizer envelope exceeds the frozen prompt budget",
            )
        maximum = max(maximum, row.envelope_prompt_token_count)

    return AcceptedTokenizerEnvelopeProofV1(
        maximum_observed_envelope_prompt_tokens=maximum,
        minimum_headroom_tokens=MAX_MODEL_LEN - maximum,
    )


def _load_runtime_module(repo_root: Path) -> tuple[types.ModuleType, str]:
    source_path = repo_root / STANDALONE_RUNTIME_SOURCE_PATH
    source = source_path.read_text(encoding="utf-8")
    if RUNTIME_MODULE_NAME in sys.modules:
        raise TokenizerEnvelopeRehearsalError(
            "V2_EXECUTABLE_REHEARSAL_MODULE_ALREADY_REGISTERED",
            "rehearsal runtime module is already registered",
        )
    module = types.ModuleType(RUNTIME_MODULE_NAME)
    filename = f"<{RUNTIME_MODULE_NAME}>"
    module.__file__ = filename
    module.__package__ = "auragateway.local_abc"
    sys.modules[RUNTIME_MODULE_NAME] = module
    try:
        exec(
            compile(source, filename, "exec"),
            module.__dict__,
            module.__dict__,
        )
    except BaseException:
        sys.modules.pop(RUNTIME_MODULE_NAME, None)
        raise
    return module, source


def run_executable_rehearsal(repo_root: Path) -> ExecutableRehearsalResultV1:
    """Exercise loader, runtime injection, fake worker, state mutation, and SystemExit handling."""

    runtime_module: types.ModuleType | None = None
    payload_module: types.ModuleType | None = None
    handled_exit = False
    raw_result: object = None
    try:
        runtime_module, _ = _load_runtime_module(repo_root)
        if PAYLOAD_MODULE_NAME in sys.modules:
            raise TokenizerEnvelopeRehearsalError(
                "V2_EXECUTABLE_REHEARSAL_MODULE_ALREADY_REGISTERED",
                "rehearsal payload module is already registered",
            )
        payload_source = (repo_root / REHEARSAL_PAYLOAD_SOURCE_PATH).read_text(encoding="utf-8")
        admission_spec = _load_object(repo_root, ADMISSION_SPEC_PATH)
        payload_module = types.ModuleType(PAYLOAD_MODULE_NAME)
        payload_filename = f"<{PAYLOAD_MODULE_NAME}>"
        payload_module.__file__ = payload_filename
        payload_module.__package__ = "auragateway.local_abc"
        payload_module.__dict__.update(
            {
                "__name__": "__main__",
                "AURAGATEWAY_V2_STANDALONE_RUNTIME": runtime_module.__dict__,
                "AURAGATEWAY_V2_ADMISSION_SPEC": admission_spec,
                "AURAGATEWAY_V2_RUNTIME_MODULE_NAME": RUNTIME_MODULE_NAME,
            }
        )
        sys.modules[PAYLOAD_MODULE_NAME] = payload_module
        try:
            exec(
                compile(payload_source, payload_filename, "exec"),
                payload_module.__dict__,
                payload_module.__dict__,
            )
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise TokenizerEnvelopeRehearsalError(
                    "V2_EXECUTABLE_REHEARSAL_NONZERO_EXIT",
                    "rehearsal payload exited non-zero",
                ) from exc
            handled_exit = True
        raw_result = payload_module.__dict__.get("AURAGATEWAY_V2_REHEARSAL_RESULT")
    except (OSError, SyntaxError) as exc:
        raise TokenizerEnvelopeRehearsalError(
            "V2_EXECUTABLE_REHEARSAL_LOAD_FAILED",
            "rehearsal source could not be loaded",
        ) from exc
    finally:
        sys.modules.pop(PAYLOAD_MODULE_NAME, None)
        sys.modules.pop(RUNTIME_MODULE_NAME, None)

    if not handled_exit:
        raise TokenizerEnvelopeRehearsalError(
            "V2_EXECUTABLE_REHEARSAL_EXIT_NOT_OBSERVED",
            "rehearsal payload did not exercise SystemExit handling",
        )
    if not isinstance(raw_result, dict):
        raise TokenizerEnvelopeRehearsalError(
            "V2_EXECUTABLE_REHEARSAL_RESULT_INVALID",
            "rehearsal payload did not produce a result object",
        )
    result_payload = dict(cast(dict[str, object], raw_result))
    result_payload.update(
        {
            "schema_version": "1.0.0",
            "status": "EXECUTABLE_REHEARSAL_PASS",
            "module_type_loader_used": True,
            "sys_modules_registration_used": True,
            "system_exit_zero_handled": True,
            "module_registry_cleanup_complete": (
                RUNTIME_MODULE_NAME not in sys.modules and PAYLOAD_MODULE_NAME not in sys.modules
            ),
        }
    )
    try:
        return ExecutableRehearsalResultV1.model_validate(result_payload)
    except ValidationError as exc:
        raise TokenizerEnvelopeRehearsalError(
            "V2_EXECUTABLE_REHEARSAL_RESULT_INVALID",
            "rehearsal result violated the frozen executable-rehearsal contract",
        ) from exc


def build_materialization(repo_root: Path) -> MaterializationV1:
    return MaterializationV1(
        envelope_request=build_envelope_request(repo_root),
        executable_rehearsal=run_executable_rehearsal(repo_root),
        tokenizer_runtime_contract=_receipt(repo_root, TOKENIZER_RUNTIME_PATH),
        accepted_runtime_integration=_receipt(repo_root, ACCEPTED_RUNTIME_INTEGRATION_PATH),
        standalone_runtime_source=_receipt(repo_root, STANDALONE_RUNTIME_SOURCE_PATH),
        rehearsal_payload_source=_receipt(repo_root, REHEARSAL_PAYLOAD_SOURCE_PATH),
        standalone_admission_spec=_receipt(repo_root, ADMISSION_SPEC_PATH),
    )


def materialize(repo_root: Path) -> dict[str, object]:
    payload = build_materialization(repo_root)
    path = repo_root / OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TOKENIZER_ENVELOPE_REHEARSAL_PASS",
        "accepted_tokenizer_envelope_proof_complete": False,
        "executable_rehearsal_complete": True,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_materialization(repo_root: Path) -> dict[str, object]:
    path = repo_root / OUTPUT_PATH
    if not path.is_file():
        raise TokenizerEnvelopeRehearsalError(
            "V2_TOKENIZER_REHEARSAL_MATERIALIZATION_MISSING",
            "tokenizer-envelope rehearsal materialization is missing",
            OUTPUT_PATH,
        )
    expected = _canonical_bytes(build_materialization(repo_root))
    if path.read_bytes() != expected:
        raise TokenizerEnvelopeRehearsalError(
            "V2_TOKENIZER_REHEARSAL_MATERIALIZATION_DRIFT",
            "tokenizer-envelope rehearsal materialization drifted",
            OUTPUT_PATH,
        )
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TOKENIZER_ENVELOPE_REHEARSAL_VALID",
        "accepted_tokenizer_envelope_proof_complete": False,
        "executable_rehearsal_complete": True,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measured-abc-variance-pilot-v2-tokenizer-envelope-rehearsal-v1"
    )
    parser.add_argument("command", choices=("materialize", "validate", "rehearse"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "materialize":
            result = materialize(repo_root)
        elif args.command == "validate":
            result = validate_materialization(repo_root)
        else:
            rehearsal = run_executable_rehearsal(repo_root)
            result = rehearsal.model_dump(mode="json")
    except TokenizerEnvelopeRehearsalError as exc:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "error_code": exc.error_code,
                    "safe_message": exc.safe_message,
                    "path": exc.path.as_posix() if exc.path is not None else None,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
