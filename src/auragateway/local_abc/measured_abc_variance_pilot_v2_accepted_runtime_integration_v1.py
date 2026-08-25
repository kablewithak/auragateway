"""Accepted-runtime integration contracts for measured A/B/C variance-pilot successor V2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Final, Literal, cast

from pydantic import Field, ValidationError

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.measured_abc_variance_pilot_v2_local_materialization_v1 import (
    GENERATION_CONTRACT_PATH,
    MATERIALIZATION_MANIFEST_PATH,
    NEUTRAL_PLAN_PATH,
    PILOT_SCHEDULE_PATH,
    STANDALONE_ADMISSION_SPEC_PATH,
    STRICT_RESPONSE_FORMAT_PATH,
    LocalMaterializationManifest,
)
from auragateway.local_abc.measured_abc_variance_pilot_v2_output_contract import (
    MAX_MODEL_LEN,
    canonical_json,
)

V1_RUNTIME_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v1/runtime_request_v1.json"
)
V1_RUNTIME_READINESS_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_runtime_launcher_readiness_v2.json"
)
OUTPUT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/accepted_runtime_integration_v1.json"
)

EXPECTED_WORKER_BINDINGS: Final[
    tuple[
        Literal["worker_1=gpu0:8001"],
        Literal["worker_2=gpu1:8002"],
    ]
] = (
    "worker_1=gpu0:8001",
    "worker_2=gpu1:8002",
)
NEXT_GATE: Final = (
    "IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_V2_TOKENIZER_BUDGET_AND_STANDALONE_RUNTIME_V1"
)


class RuntimeIntegrationError(RuntimeError):
    """Metadata-safe deterministic runtime-integration failure."""

    def __init__(self, error_code: str, safe_message: str, path: Path | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class ArtifactReceipt(LocalABCContract):
    """Content identity for one accepted upstream artifact."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class AcceptedRuntimeIdentity(LocalABCContract):
    """Exact accepted runtime identity reused by V2."""

    python: Literal["3.12"] = "3.12"
    cuda_variant: Literal["cu129"] = "cu129"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public_semantic_version: Literal["0.25.1"] = "0.25.1"
    required_native_module: Literal["vllm._C_stable_libtorch"] = "vllm._C_stable_libtorch"
    attention_backend: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    gpu_topology: Literal["T4_X2"] = "T4_X2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = (
        "Qwen/Qwen2.5-0.5B-Instruct"
    )
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"


class RuntimeReuseBoundary(LocalABCContract):
    """Explicitly separate reusable mechanics from superseded V1 semantics."""

    reuse_runtime_installation_mechanics: Literal[True] = True
    reuse_runtime_identity: Literal[True] = True
    reuse_worker_launch_teardown_mechanics: Literal[True] = True
    reuse_telemetry_collection_primitives: Literal[True] = True
    reuse_v1_route_semantics: Literal[False] = False
    reuse_v1_retry_budget: Literal[False] = False
    reuse_v1_output_parsing: Literal[False] = False
    reuse_v1_output_token_budget: Literal[False] = False
    reuse_v1_turn_two_causal_assumptions: Literal[False] = False


class RequestBudgetV2(LocalABCContract):
    """Exact no-retry successor request budget."""

    schema_canary_requests: Literal[2] = 2
    warmup_requests: Literal[2] = 2
    neutral_worker_qualification_requests: Literal[20] = 20
    pretreatment_requests: Literal[24] = 24
    pilot_requests: Literal[216] = 216
    maximum_total_model_requests: Literal[240] = 240
    maximum_attempts_per_request: Literal[1] = 1
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_cases: Literal[0] = 0


class TokenBudgetBoundary(LocalABCContract):
    """Pre-authority and live-runtime token-budget responsibilities."""

    max_model_len: Literal[4096] = MAX_MODEL_LEN
    max_output_tokens: Literal[256] = 256
    pre_authority_exact_future_prompt_counts_claimed: Literal[False] = False
    pre_authority_tokenizer_envelope_proof_required: Literal[True] = True
    pre_authority_tokenizer_envelope_proof_complete: Literal[False] = False
    runtime_exact_tokenizer_check_before_every_request: Literal[True] = True
    request_permitted_without_runtime_token_check: Literal[False] = False
    runtime_budget_expression: Literal["prompt_tokens + 256 <= 4096"] = (
        "prompt_tokens + 256 <= 4096"
    )


class OutputAdmissionBoundary(LocalABCContract):
    """Hashes and fail-closed response-state requirements reused by live execution."""

    strict_response_format_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    standalone_admission_spec_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    finish_reason_stop_required: Literal[True] = True
    finish_reason_length_is_hard_failure: Literal[True] = True
    json_decode_required_before_state_mutation: Literal[True] = True
    standalone_admission_required_before_state_mutation: Literal[True] = True
    canonicalization_required_before_state_mutation: Literal[True] = True
    invalid_output_retry_permitted: Literal[False] = False
    invalid_output_history_mutation_permitted: Literal[False] = False
    later_turns_after_trajectory_failure_permitted: Literal[False] = False


class AcceptedRuntimeIntegrationV1(LocalABCContract):
    """Non-authorizing accepted-runtime integration contract for V2."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    integration_id: Literal["auragateway-variance-pilot-successor-v2-runtime-integration-v1"] = (
        "auragateway-variance-pilot-successor-v2-runtime-integration-v1"
    )
    accepted_runtime: AcceptedRuntimeIdentity
    worker_bindings: tuple[
        Literal["worker_1=gpu0:8001"],
        Literal["worker_2=gpu1:8002"],
    ]
    reuse_boundary: RuntimeReuseBoundary = RuntimeReuseBoundary()
    request_budget: RequestBudgetV2 = RequestBudgetV2()
    token_budget: TokenBudgetBoundary = TokenBudgetBoundary()
    output_admission: OutputAdmissionBoundary
    accepted_runtime_request: ArtifactReceipt
    accepted_runtime_readiness: ArtifactReceipt
    v2_local_materialization_manifest: ArtifactReceipt
    v2_materialized_artifacts: tuple[ArtifactReceipt, ...]
    runtime_executable_generated: Literal[False] = False
    tokenizer_budget_proof_complete: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_V2_TOKENIZER_BUDGET_AND_STANDALONE_RUNTIME_V1"
    ] = NEXT_GATE


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_REQUIRED_FILE_MISSING",
            "required runtime-integration artifact is missing or unsafe",
            relative,
        )
    raw = path.read_bytes()
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha256_bytes(raw),
        size_bytes=len(raw),
    )


def _load_object(repo_root: Path, relative: Path) -> dict[str, object]:
    path = repo_root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_REQUIRED_FILE_MISSING",
            "required runtime-integration JSON is missing",
            relative,
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_JSON_INVALID",
            "required runtime-integration JSON is invalid",
            relative,
        ) from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_JSON_ROOT_INVALID",
            "required runtime-integration JSON root must be an object",
            relative,
        )
    return cast(dict[str, object], value)


def _accepted_runtime(repo_root: Path) -> tuple[AcceptedRuntimeIdentity, ArtifactReceipt]:
    request = _load_object(repo_root, V1_RUNTIME_REQUEST_PATH)
    try:
        runtime = AcceptedRuntimeIdentity.model_validate(request.get("runtime"))
    except ValidationError as exc:
        raise RuntimeIntegrationError(
            "V2_ACCEPTED_RUNTIME_IDENTITY_DRIFT",
            "accepted runtime identity differs from the qualified runtime",
            V1_RUNTIME_REQUEST_PATH,
        ) from exc
    if request.get("worker_bindings") != list(EXPECTED_WORKER_BINDINGS):
        raise RuntimeIntegrationError(
            "V2_ACCEPTED_RUNTIME_WORKER_BINDING_DRIFT",
            "accepted runtime worker bindings drifted",
            V1_RUNTIME_REQUEST_PATH,
        )
    if (
        request.get("pilot_execution_authorized") is not False
        or request.get("final_measured_abc_execution_authorized") is not False
    ):
        raise RuntimeIntegrationError(
            "V2_ACCEPTED_RUNTIME_UPSTREAM_AUTHORITY_INVALID",
            "accepted runtime request unexpectedly carries execution authority",
            V1_RUNTIME_REQUEST_PATH,
        )
    return runtime, _receipt(repo_root, V1_RUNTIME_REQUEST_PATH)


def _validate_readiness(
    repo_root: Path,
    runtime_request_receipt: ArtifactReceipt,
) -> ArtifactReceipt:
    readiness = _load_object(repo_root, V1_RUNTIME_READINESS_PATH)
    if readiness.get("status") != "READY_FOR_TRANSACTION_BOUND_EXECUTABLE_IMPLEMENTATION":
        raise RuntimeIntegrationError(
            "V2_ACCEPTED_RUNTIME_READINESS_INVALID",
            "accepted runtime readiness status is not reusable",
            V1_RUNTIME_READINESS_PATH,
        )
    if (
        readiness.get("pilot_execution_authorized") is not False
        or readiness.get("final_measured_abc_execution_authorized") is not False
        or readiness.get("new_execution_authorized") is not False
    ):
        raise RuntimeIntegrationError(
            "V2_ACCEPTED_RUNTIME_READINESS_AUTHORITY_INVALID",
            "accepted runtime readiness unexpectedly carries execution authority",
            V1_RUNTIME_READINESS_PATH,
        )
    raw_request_receipt = readiness.get("runtime_request")
    if not isinstance(raw_request_receipt, dict):
        raise RuntimeIntegrationError(
            "V2_ACCEPTED_RUNTIME_READINESS_INVALID",
            "accepted readiness is missing its runtime-request receipt",
            V1_RUNTIME_READINESS_PATH,
        )
    typed_request_receipt = cast(dict[str, object], raw_request_receipt)
    if typed_request_receipt.get("sha256") != runtime_request_receipt.sha256:
        raise RuntimeIntegrationError(
            "V2_ACCEPTED_RUNTIME_READINESS_DRIFT",
            "accepted readiness no longer binds the runtime request",
            V1_RUNTIME_READINESS_PATH,
        )
    return _receipt(repo_root, V1_RUNTIME_READINESS_PATH)


def _load_materialization_manifest(repo_root: Path) -> LocalMaterializationManifest:
    path = repo_root / MATERIALIZATION_MANIFEST_PATH
    try:
        return LocalMaterializationManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise RuntimeIntegrationError(
            "V2_LOCAL_MATERIALIZATION_MANIFEST_INVALID",
            "V2 local materialization manifest is invalid",
            MATERIALIZATION_MANIFEST_PATH,
        ) from exc


def _materialization_receipts(
    repo_root: Path,
    manifest: LocalMaterializationManifest,
) -> tuple[ArtifactReceipt, ...]:
    expected = (
        (PILOT_SCHEDULE_PATH, manifest.pilot_schedule_sha256),
        (NEUTRAL_PLAN_PATH, manifest.neutral_worker_qualification_plan_sha256),
        (STRICT_RESPONSE_FORMAT_PATH, manifest.strict_response_format_sha256),
        (STANDALONE_ADMISSION_SPEC_PATH, manifest.standalone_admission_spec_sha256),
        (GENERATION_CONTRACT_PATH, manifest.generation_contract_sha256),
    )
    receipts: list[ArtifactReceipt] = []
    for relative, expected_sha in expected:
        receipt = _receipt(repo_root, relative)
        if receipt.sha256 != expected_sha:
            raise RuntimeIntegrationError(
                "V2_LOCAL_MATERIALIZATION_ARTIFACT_DRIFT",
                "V2 materialized artifact differs from its manifest identity",
                relative,
            )
        receipts.append(receipt)
    return tuple(receipts)


def _validate_v2_semantic_inputs(repo_root: Path) -> None:
    schedule = _load_object(repo_root, PILOT_SCHEDULE_PATH)
    neutral = _load_object(repo_root, NEUTRAL_PLAN_PATH)
    generation = _load_object(repo_root, GENERATION_CONTRACT_PATH)
    admission = _load_object(repo_root, STANDALONE_ADMISSION_SPEC_PATH)

    if (
        schedule.get("pilot_turn_count") != 216
        or schedule.get("trajectory_count") != 54
        or schedule.get("pilot_execution_authorized") is not False
        or schedule.get("hidden_retries_permitted") is not False
    ):
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_SCHEDULE_INVALID",
            "V2 schedule does not satisfy the accepted runtime-integration boundary",
            PILOT_SCHEDULE_PATH,
        )
    if (
        neutral.get("pre_treatment_request_count") != 24
        or neutral.get("measured_request_count") != 20
        or neutral.get("pilot_execution_authorized") is not False
        or neutral.get("hidden_retries_permitted") is not False
    ):
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_PRETREATMENT_INVALID",
            "V2 pre-treatment plan does not satisfy the accepted runtime-integration boundary",
            NEUTRAL_PLAN_PATH,
        )
    required_generation: dict[str, object] = {
        "temperature": 0,
        "top_p": 1,
        "seed": 7,
        "max_tokens": 256,
        "n": 1,
        "stream": False,
        "hidden_retries_permitted": False,
    }
    if any(generation.get(key) != expected for key, expected in required_generation.items()):
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_GENERATION_INVALID",
            "V2 generation contract drifted",
            GENERATION_CONTRACT_PATH,
        )
    if admission.get("semantic_contract") != "TerminalDecisionOutput":
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_ADMISSION_INVALID",
            "V2 standalone admission semantic contract drifted",
            STANDALONE_ADMISSION_SPEC_PATH,
        )


def build_runtime_integration(repo_root: Path) -> AcceptedRuntimeIntegrationV1:
    """Build the non-authorizing accepted-runtime integration contract."""

    runtime, runtime_request_receipt = _accepted_runtime(repo_root)
    readiness_receipt = _validate_readiness(repo_root, runtime_request_receipt)
    manifest = _load_materialization_manifest(repo_root)
    if (
        manifest.pretreatment_request_count != 24
        or manifest.pilot_request_count != 216
        or manifest.maximum_total_model_requests != 240
        or manifest.tokenizer_budget_proof_complete is not False
        or manifest.pilot_execution_authorized is not False
        or manifest.final_measured_abc_execution_authorized is not False
    ):
        raise RuntimeIntegrationError(
            "V2_LOCAL_MATERIALIZATION_BOUNDARY_INVALID",
            "V2 local materialization does not satisfy the integration boundary",
            MATERIALIZATION_MANIFEST_PATH,
        )

    _validate_v2_semantic_inputs(repo_root)
    materialized_receipts = _materialization_receipts(repo_root, manifest)

    return AcceptedRuntimeIntegrationV1(
        accepted_runtime=runtime,
        worker_bindings=EXPECTED_WORKER_BINDINGS,
        output_admission=OutputAdmissionBoundary(
            strict_response_format_sha256=manifest.strict_response_format_sha256,
            standalone_admission_spec_sha256=manifest.standalone_admission_spec_sha256,
            generation_contract_sha256=manifest.generation_contract_sha256,
        ),
        accepted_runtime_request=runtime_request_receipt,
        accepted_runtime_readiness=readiness_receipt,
        v2_local_materialization_manifest=_receipt(repo_root, MATERIALIZATION_MANIFEST_PATH),
        v2_materialized_artifacts=materialized_receipts,
    )


def _expected_bytes(repo_root: Path) -> bytes:
    contract = build_runtime_integration(repo_root)
    return canonical_json(contract.model_dump(mode="json")).encode("utf-8")


def materialize(repo_root: Path) -> dict[str, object]:
    """Write the deterministic integration artifact without authorizing execution."""

    path = repo_root / OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_expected_bytes(repo_root))
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_RUNTIME_INTEGRATION_PASS",
        "materialized_path": OUTPUT_PATH.as_posix(),
        "runtime_executable_generated": False,
        "tokenizer_budget_proof_complete": False,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_materialization(repo_root: Path) -> dict[str, object]:
    """Require the integration artifact to equal deterministic regenerated bytes."""

    path = repo_root / OUTPUT_PATH
    if not path.is_file() or path.is_symlink():
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_MATERIALIZATION_MISSING",
            "accepted-runtime integration artifact is missing or unsafe",
            OUTPUT_PATH,
        )
    if path.read_bytes() != _expected_bytes(repo_root):
        raise RuntimeIntegrationError(
            "V2_RUNTIME_INTEGRATION_MATERIALIZATION_DRIFT",
            "accepted-runtime integration artifact differs from deterministic source",
            OUTPUT_PATH,
        )
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_ACCEPTED_RUNTIME_INTEGRATION_VALID",
        "runtime_executable_generated": False,
        "tokenizer_budget_proof_complete": False,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measured-abc-variance-pilot-v2-accepted-runtime-integration-v1"
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
    except RuntimeIntegrationError as exc:
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
