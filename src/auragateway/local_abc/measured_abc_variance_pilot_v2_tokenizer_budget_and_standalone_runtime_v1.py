"""Tokenizer-budget plan and standalone-runtime contract for variance-pilot successor V2."""

from __future__ import annotations

import argparse
import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract, WorkerId
from auragateway.local_abc.measured_abc_variance_pilot_v2_output_contract import canonical_json

ACCEPTED_RUNTIME_INTEGRATION_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/accepted_runtime_integration_v1.json"
)
PILOT_SCHEDULE_PATH: Final = Path("data/evals/benchmark/variance-pilot-v2/pilot_schedule.json")
NEUTRAL_PLAN_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/neutral_worker_qualification_plan.json"
)
STANDALONE_ADMISSION_SPEC_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json"
)
GENERATION_CONTRACT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/generation_contract.json"
)
OUTPUT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/tokenizer_budget_and_standalone_runtime_v1.json"
)
CONTRACT_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "measured_abc_variance_pilot_v2_tokenizer_budget_and_standalone_runtime_v1.py"
)
STANDALONE_RUNTIME_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_standalone_runtime_v1.py"
)

PRETREATMENT_REQUEST_COUNT: Final = 24
PILOT_REQUEST_COUNT: Final = 216
MAXIMUM_TOTAL_MODEL_REQUESTS: Final = 240
MAX_MODEL_LEN: Final = 4096
MAX_OUTPUT_TOKENS: Final = 256
NEXT_GATE: Final = (
    "IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_TOKENIZER_ENVELOPE_AND_EXECUTABLE_REHEARSAL_V1"
)


class TokenizerRuntimeContractError(RuntimeError):
    """Metadata-safe deterministic tokenizer/runtime contract failure."""

    def __init__(self, error_code: str, safe_message: str, path: Path | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class RequestPhase(StrEnum):
    """One request phase in the exact 240-request successor plan."""

    SCHEMA_CANARY = "schema_canary"
    WARMUP = "warmup"
    NEUTRAL_WORKER_QUALIFICATION = "neutral_worker_qualification"
    PILOT = "pilot"


class PromptStateDependency(StrEnum):
    """Whether exact prompt size depends on prior admitted assistant state."""

    NONE = "none"
    PRIOR_ADMITTED_HISTORY = "prior_admitted_history"


class TokenizerBudgetRequestSlot(LocalABCContract):
    """One request position requiring exact runtime token admission."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    sequence_index: int = Field(ge=0, lt=MAXIMUM_TOTAL_MODEL_REQUESTS)
    request_id: str = Field(min_length=1)
    phase: RequestPhase
    worker_id: WorkerId
    pilot_run_id: str | None = None
    pilot_turn_index: int | None = Field(default=None, ge=1, le=4)
    prompt_state_dependency: PromptStateDependency
    maximum_attempts: Literal[1] = 1

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        is_pilot = self.phase is RequestPhase.PILOT
        if is_pilot and (self.pilot_run_id is None or self.pilot_turn_index is None):
            raise ValueError("pilot request slots require run and turn identity")
        if not is_pilot and (self.pilot_run_id is not None or self.pilot_turn_index is not None):
            raise ValueError("pre-treatment request slots cannot carry pilot identity")
        if is_pilot:
            expected_dependency = (
                PromptStateDependency.NONE
                if self.pilot_turn_index == 1
                else PromptStateDependency.PRIOR_ADMITTED_HISTORY
            )
            if self.prompt_state_dependency is not expected_dependency:
                raise ValueError("pilot prompt-state dependency drifted")
        elif self.prompt_state_dependency is not PromptStateDependency.NONE:
            raise ValueError("pre-treatment requests cannot depend on pilot history")
        return self


class TokenizerBudgetPlanV1(LocalABCContract):
    """Exact request inventory without claiming unknowable future token counts."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    plan_id: Literal["auragateway-variance-pilot-v2-tokenizer-budget-plan-v1"] = (
        "auragateway-variance-pilot-v2-tokenizer-budget-plan-v1"
    )
    requests: tuple[TokenizerBudgetRequestSlot, ...] = Field(
        min_length=MAXIMUM_TOTAL_MODEL_REQUESTS,
        max_length=MAXIMUM_TOTAL_MODEL_REQUESTS,
    )
    pretreatment_request_count: Literal[24] = PRETREATMENT_REQUEST_COUNT
    pilot_request_count: Literal[216] = PILOT_REQUEST_COUNT
    maximum_total_model_requests: Literal[240] = MAXIMUM_TOTAL_MODEL_REQUESTS
    max_model_len: Literal[4096] = MAX_MODEL_LEN
    max_output_tokens: Literal[256] = MAX_OUTPUT_TOKENS
    pre_authority_exact_future_prompt_counts_claimed: Literal[False] = False
    accepted_tokenizer_observation_required_for_completion: Literal[True] = True
    pre_authority_tokenizer_envelope_proof_complete: Literal[False] = False
    runtime_exact_tokenizer_check_before_every_request: Literal[True] = True
    request_permitted_without_runtime_token_check: Literal[False] = False
    runtime_budget_expression: Literal["prompt_tokens + 256 <= 4096"] = (
        "prompt_tokens + 256 <= 4096"
    )
    pilot_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        indexes = tuple(item.sequence_index for item in self.requests)
        if indexes != tuple(range(MAXIMUM_TOTAL_MODEL_REQUESTS)):
            raise ValueError("tokenizer-budget request indexes must be contiguous")
        request_ids = tuple(item.request_id for item in self.requests)
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("tokenizer-budget request IDs must be unique")
        phase_counts = {
            phase: sum(item.phase is phase for item in self.requests) for phase in RequestPhase
        }
        if phase_counts != {
            RequestPhase.SCHEMA_CANARY: 2,
            RequestPhase.WARMUP: 2,
            RequestPhase.NEUTRAL_WORKER_QUALIFICATION: 20,
            RequestPhase.PILOT: 216,
        }:
            raise ValueError("tokenizer-budget phase counts drifted")
        return self


class ArtifactReceipt(LocalABCContract):
    """Content identity for one upstream artifact."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class StandaloneRuntimeContractV1(LocalABCContract):
    """Non-authorizing runtime behavior required before executable materialization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    runtime_contract_id: Literal["auragateway-variance-pilot-v2-standalone-runtime-v1"] = (
        "auragateway-variance-pilot-v2-standalone-runtime-v1"
    )
    accepted_runtime_integration: ArtifactReceipt
    contract_source: ArtifactReceipt
    standalone_runtime_source: ArtifactReceipt
    tokenizer_budget_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    standalone_admission_spec_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tokenizer_interface: Literal["EXACT_ACCEPTED_CHAT_TEMPLATE_TOKEN_COUNT"] = (
        "EXACT_ACCEPTED_CHAT_TEMPLATE_TOKEN_COUNT"
    )
    max_model_len: Literal[4096] = MAX_MODEL_LEN
    max_output_tokens: Literal[256] = MAX_OUTPUT_TOKENS
    maximum_total_model_requests: Literal[240] = MAXIMUM_TOTAL_MODEL_REQUESTS
    maximum_attempts_per_request: Literal[1] = 1
    hidden_retries_permitted: Literal[False] = False
    replacement_requests_permitted: Literal[False] = False
    token_check_precedes_request_send: Literal[True] = True
    over_budget_request_send_permitted: Literal[False] = False
    standalone_output_admission_required: Literal[True] = True
    atomic_history_mutation_required: Literal[True] = True
    failed_turn_history_mutation_permitted: Literal[False] = False
    later_turns_after_trajectory_failure_permitted: Literal[False] = False
    runtime_executable_generated: Literal[False] = False
    accepted_tokenizer_envelope_proof_complete: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_TOKENIZER_ENVELOPE_"
        "AND_EXECUTABLE_REHEARSAL_V1"
    ] = NEXT_GATE


class TokenizerBudgetRuntimeMaterializationV1(LocalABCContract):
    """Deterministic materialization of request-plan and runtime contracts."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    tokenizer_budget_plan: TokenizerBudgetPlanV1
    standalone_runtime_contract: StandaloneRuntimeContractV1


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: object) -> str:
    return _sha256_bytes(canonical_json(value).encode("utf-8"))


def _load_object(repo_root: Path, relative: Path) -> dict[str, object]:
    path = repo_root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_REQUIRED_FILE_MISSING",
            "required tokenizer/runtime artifact is missing",
            relative,
        ) from exc
    except json.JSONDecodeError as exc:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_JSON_INVALID",
            "required tokenizer/runtime artifact is invalid JSON",
            relative,
        ) from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_JSON_ROOT_INVALID",
            "required tokenizer/runtime JSON root must be an object",
            relative,
        )
    return cast(dict[str, object], value)


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_REQUIRED_FILE_MISSING",
            "required tokenizer/runtime artifact is missing or unsafe",
            relative,
        )
    raw = path.read_bytes()
    return ArtifactReceipt(path=relative.as_posix(), sha256=_sha256_bytes(raw), size_bytes=len(raw))


def _worker_id(value: object, path: Path) -> WorkerId:
    if not isinstance(value, str):
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_WORKER_INVALID",
            "request plan contains an invalid worker identity",
            path,
        )
    try:
        return WorkerId(value)
    except ValueError as exc:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_WORKER_INVALID",
            "request plan contains an invalid worker identity",
            path,
        ) from exc


def build_tokenizer_budget_plan(repo_root: Path) -> TokenizerBudgetPlanV1:
    """Build the exact 240 request positions from frozen V2 materialization."""

    neutral = _load_object(repo_root, NEUTRAL_PLAN_PATH)
    schedule = _load_object(repo_root, PILOT_SCHEDULE_PATH)
    neutral_requests = neutral.get("requests")
    trajectories = schedule.get("trajectories")
    if (
        not isinstance(neutral_requests, list)
        or len(neutral_requests) != PRETREATMENT_REQUEST_COUNT
    ):
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_PRETREATMENT_INVALID",
            "pre-treatment plan must contain exactly 24 requests",
            NEUTRAL_PLAN_PATH,
        )
    if not isinstance(trajectories, list) or len(trajectories) != 54:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_SCHEDULE_INVALID",
            "pilot schedule must contain exactly 54 trajectories",
            PILOT_SCHEDULE_PATH,
        )

    slots: list[TokenizerBudgetRequestSlot] = []
    for expected_index, raw_request in enumerate(neutral_requests):
        if not isinstance(raw_request, dict):
            raise TokenizerRuntimeContractError(
                "V2_TOKENIZER_RUNTIME_PRETREATMENT_INVALID",
                "pre-treatment request row is invalid",
                NEUTRAL_PLAN_PATH,
            )
        request = cast(dict[str, object], raw_request)
        if request.get("sequence_index") != expected_index:
            raise TokenizerRuntimeContractError(
                "V2_TOKENIZER_RUNTIME_PRETREATMENT_INVALID",
                "pre-treatment request sequence drifted",
                NEUTRAL_PLAN_PATH,
            )
        request_id = request.get("request_id")
        phase = request.get("phase")
        if not isinstance(request_id, str) or not isinstance(phase, str):
            raise TokenizerRuntimeContractError(
                "V2_TOKENIZER_RUNTIME_PRETREATMENT_INVALID",
                "pre-treatment request identity is invalid",
                NEUTRAL_PLAN_PATH,
            )
        try:
            typed_phase = RequestPhase(phase)
        except ValueError as exc:
            raise TokenizerRuntimeContractError(
                "V2_TOKENIZER_RUNTIME_PRETREATMENT_INVALID",
                "pre-treatment phase is invalid",
                NEUTRAL_PLAN_PATH,
            ) from exc
        slots.append(
            TokenizerBudgetRequestSlot(
                sequence_index=expected_index,
                request_id=request_id,
                phase=typed_phase,
                worker_id=_worker_id(request.get("worker_id"), NEUTRAL_PLAN_PATH),
                prompt_state_dependency=PromptStateDependency.NONE,
            )
        )

    for raw_trajectory in trajectories:
        if not isinstance(raw_trajectory, dict):
            raise TokenizerRuntimeContractError(
                "V2_TOKENIZER_RUNTIME_SCHEDULE_INVALID",
                "pilot trajectory row is invalid",
                PILOT_SCHEDULE_PATH,
            )
        trajectory = cast(dict[str, object], raw_trajectory)
        schedule_index = trajectory.get("schedule_index")
        run_id = trajectory.get("run_id")
        realized_route = trajectory.get("realized_route")
        if (
            not isinstance(schedule_index, int)
            or isinstance(schedule_index, bool)
            or not isinstance(run_id, str)
            or not isinstance(realized_route, list)
            or len(realized_route) != 4
        ):
            raise TokenizerRuntimeContractError(
                "V2_TOKENIZER_RUNTIME_SCHEDULE_INVALID",
                "pilot trajectory identity or route is invalid",
                PILOT_SCHEDULE_PATH,
            )
        for turn_offset, raw_worker in enumerate(realized_route):
            turn_index = turn_offset + 1
            sequence_index = PRETREATMENT_REQUEST_COUNT + schedule_index * 4 + turn_offset
            slots.append(
                TokenizerBudgetRequestSlot(
                    sequence_index=sequence_index,
                    request_id=f"{run_id}-turn-{turn_index}",
                    phase=RequestPhase.PILOT,
                    worker_id=_worker_id(raw_worker, PILOT_SCHEDULE_PATH),
                    pilot_run_id=run_id,
                    pilot_turn_index=turn_index,
                    prompt_state_dependency=(
                        PromptStateDependency.NONE
                        if turn_index == 1
                        else PromptStateDependency.PRIOR_ADMITTED_HISTORY
                    ),
                )
            )
    return TokenizerBudgetPlanV1(requests=tuple(slots))


def _validate_integration(repo_root: Path) -> tuple[dict[str, object], ArtifactReceipt]:
    integration = _load_object(repo_root, ACCEPTED_RUNTIME_INTEGRATION_PATH)
    request_budget = integration.get("request_budget")
    token_budget = integration.get("token_budget")
    output_admission = integration.get("output_admission")
    if not isinstance(request_budget, dict) or not isinstance(token_budget, dict):
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_INTEGRATION_INVALID",
            "accepted runtime integration is missing budget contracts",
            ACCEPTED_RUNTIME_INTEGRATION_PATH,
        )
    if not isinstance(output_admission, dict):
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_INTEGRATION_INVALID",
            "accepted runtime integration is missing output admission",
            ACCEPTED_RUNTIME_INTEGRATION_PATH,
        )
    if (
        request_budget.get("maximum_total_model_requests") != 240
        or request_budget.get("maximum_attempts_per_request") != 1
        or request_budget.get("maximum_hidden_retries") != 0
        or token_budget.get("max_model_len") != 4096
        or token_budget.get("max_output_tokens") != 256
        or token_budget.get("runtime_exact_tokenizer_check_before_every_request") is not True
        or token_budget.get("request_permitted_without_runtime_token_check") is not False
    ):
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_INTEGRATION_INVALID",
            "accepted runtime integration budget semantics drifted",
            ACCEPTED_RUNTIME_INTEGRATION_PATH,
        )
    if (
        integration.get("pilot_execution_authorized") is not False
        or integration.get("new_execution_authorized") is not False
    ):
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_AUTHORITY_INVALID",
            "accepted runtime integration unexpectedly carries execution authority",
            ACCEPTED_RUNTIME_INTEGRATION_PATH,
        )
    return integration, _receipt(repo_root, ACCEPTED_RUNTIME_INTEGRATION_PATH)


def build_materialization(repo_root: Path) -> TokenizerBudgetRuntimeMaterializationV1:
    """Build deterministic, non-authorizing tokenizer/runtime contracts."""

    integration, integration_receipt = _validate_integration(repo_root)
    plan = build_tokenizer_budget_plan(repo_root)
    output_admission = cast(dict[str, object], integration["output_admission"])
    admission_receipt = _receipt(repo_root, STANDALONE_ADMISSION_SPEC_PATH)
    generation_receipt = _receipt(repo_root, GENERATION_CONTRACT_PATH)
    expected_admission_sha = output_admission.get("standalone_admission_spec_sha256")
    expected_generation_sha = output_admission.get("generation_contract_sha256")
    if admission_receipt.sha256 != expected_admission_sha:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_ADMISSION_DRIFT",
            "standalone admission spec identity drifted",
            STANDALONE_ADMISSION_SPEC_PATH,
        )
    if generation_receipt.sha256 != expected_generation_sha:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_GENERATION_DRIFT",
            "generation contract identity drifted",
            GENERATION_CONTRACT_PATH,
        )
    runtime_contract = StandaloneRuntimeContractV1(
        accepted_runtime_integration=integration_receipt,
        contract_source=_receipt(repo_root, CONTRACT_SOURCE_PATH),
        standalone_runtime_source=_receipt(repo_root, STANDALONE_RUNTIME_SOURCE_PATH),
        tokenizer_budget_plan_sha256=_sha256_json(plan.model_dump(mode="json")),
        standalone_admission_spec_sha256=admission_receipt.sha256,
        generation_contract_sha256=generation_receipt.sha256,
    )
    return TokenizerBudgetRuntimeMaterializationV1(
        tokenizer_budget_plan=plan,
        standalone_runtime_contract=runtime_contract,
    )


def _canonical_bytes(value: object) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize(repo_root: Path) -> dict[str, object]:
    """Write the deterministic tokenizer/runtime contract artifact."""

    materialization = build_materialization(repo_root)
    path = repo_root / OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(materialization.model_dump(mode="json")))
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TOKENIZER_RUNTIME_MATERIALIZATION_PASS",
        "request_slot_count": MAXIMUM_TOTAL_MODEL_REQUESTS,
        "accepted_tokenizer_envelope_proof_complete": False,
        "runtime_executable_generated": False,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_materialization(repo_root: Path) -> dict[str, object]:
    """Require byte-identical regeneration of the materialized contract."""

    expected = build_materialization(repo_root)
    path = repo_root / OUTPUT_PATH
    if not path.is_file() or path.is_symlink():
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_MATERIALIZATION_MISSING",
            "tokenizer/runtime materialization artifact is missing or unsafe",
            OUTPUT_PATH,
        )
    expected_bytes = _canonical_bytes(expected.model_dump(mode="json"))
    if path.read_bytes() != expected_bytes:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_MATERIALIZATION_DRIFT",
            "tokenizer/runtime materialization differs from deterministic source",
            OUTPUT_PATH,
        )
    try:
        observed = TokenizerBudgetRuntimeMaterializationV1.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as exc:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_MATERIALIZATION_INVALID",
            "tokenizer/runtime materialization artifact is invalid",
            OUTPUT_PATH,
        ) from exc
    if observed != expected:
        raise TokenizerRuntimeContractError(
            "V2_TOKENIZER_RUNTIME_MATERIALIZATION_DRIFT",
            "tokenizer/runtime materialization model identity drifted",
            OUTPUT_PATH,
        )
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TOKENIZER_RUNTIME_VALID",
        "request_slot_count": MAXIMUM_TOTAL_MODEL_REQUESTS,
        "accepted_tokenizer_envelope_proof_complete": False,
        "runtime_executable_generated": False,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measured-abc-variance-pilot-v2-tokenizer-budget-and-standalone-runtime-v1"
    )
    parser.add_argument("command", choices=("materialize", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        result = (
            materialize(repo_root)
            if args.command == "materialize"
            else validate_materialization(repo_root)
        )
    except TokenizerRuntimeContractError as exc:
        print(
            canonical_json(
                {
                    "status": "ERROR",
                    "error_code": exc.error_code,
                    "safe_message": exc.safe_message,
                    "path": exc.path.as_posix() if exc.path is not None else None,
                }
            )
        )
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
