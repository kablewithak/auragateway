"""Transaction-bound execution authorization and artifact generation V1."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ARCHITECTURE_MERGE_COMMIT: Final = "32b737a64133dbd8361ac3db871e4c02ff80ccf3"
ARCHITECTURE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_authorization_architecture_v1.json"
)
ARCHITECTURE_RECORD_SHA256: Final = (
    "4fff25e4a6160dfcdd23294285689d0290b9ecf32930a90c737454878d2a3779"
)
DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_authorization_implementation_design_v1.json"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/transaction_bound_execution_authorization_v1.py"
)
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/transaction_bound_execution_wrapper_v1.py.tmpl"
)
TEST_PATH: Final = Path("tests/unit/local_abc/test_transaction_bound_execution_authorization_v1.py")
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Transaction_Bound_Execution_Authorization_Implementation_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_transaction_bound_execution_authorization_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_authorization_v1_record.json"
)
LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_authorization_v1_live.json"
)
LIVE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_artifact_v1_live_manifest.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_authorization_v1_terminal.json"
)
RUNTIME_INTEGRATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_p5_p6_runtime_integration_v1.json"
)

AUTHORIZATION_SCOPE: Final = "EXACT_RUNTIME_P5_P6_TRANSACTION_BOUND_V1"
DEFAULT_WINDOW_MINUTES: Final = 180
MAX_WINDOW_MINUTES: Final = 240
NEXT_GATE: Final = "INTEGRATE_EXACT_RUNTIME_P5_P6_SUCCESSOR_PAYLOAD_AND_SYMLINK_REGRESSION_V1"


class TransactionBoundError(RuntimeError):
    """Metadata-safe transaction-bound control error."""

    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise TransactionBoundError("TRANSACTION_BOUND_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeModelContract(FrozenModel):
    python: Literal["3.12"] = "3.12"
    cuda_variant: Literal["cu129"] = "cu129"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public_semantic_version: Literal["0.25.1"] = "0.25.1"
    required_native_module: Literal["vllm._C_stable_libtorch"] = "vllm._C_stable_libtorch"
    gpu_topology: Literal["T4_x2"] = "T4_x2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_directory_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"


class ExecutionBudget(FrozenModel):
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_workers: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class RequiredPlatform(FrozenModel):
    accelerator: Literal["T4_X2"] = "T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False


class AuthorizationIntent(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    intent_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    scope: Literal["EXACT_RUNTIME_P5_P6_TRANSACTION_BOUND_V1"]
    prepared_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=MAX_WINDOW_MINUTES)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    architecture_record_sha256: Literal[
        "4fff25e4a6160dfcdd23294285689d0290b9ecf32930a90c737454878d2a3779"
    ]
    implementation_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    required_platform: RequiredPlatform

    @field_validator("prepared_at")
    @classmethod
    def normalize_prepared_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "prepared_at")


class AuthorizationBody(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str = Field(pattern=r"^tb-[0-9a-f]{32}$")
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle: Literal["ISSUED"] = "ISSUED"
    scope: Literal["EXACT_RUNTIME_P5_P6_TRANSACTION_BOUND_V1"]
    authorization_challenge_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_confirmation_method: Literal["RETYPE_DYNAMIC_SHA256_CHALLENGE"]
    operator_confirmation_recorded: Literal[True]
    operator_confirmed_at: datetime
    issued_at: datetime
    expires_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=MAX_WINDOW_MINUTES)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    architecture_record_sha256: Literal[
        "4fff25e4a6160dfcdd23294285689d0290b9ecf32930a90c737454878d2a3779"
    ]
    implementation_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime: RuntimeModelContract
    required_platform: RequiredPlatform
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_workers: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0
    runtime_execution_authorized: Literal[True] = True
    single_use: Literal[True] = True
    every_terminal_attempt_consumes_authorization: Literal[True] = True
    unchanged_replay_authorized: Literal[False] = False
    authorization_reusable: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False

    @field_validator("operator_confirmed_at", "issued_at", "expires_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _normalize_time(value, "authorization timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.issued_at != self.operator_confirmed_at:
            raise ValueError("issuance must coincide with interactive confirmation")
        if self.expires_at != self.issued_at + timedelta(minutes=self.authorization_window_minutes):
            raise ValueError("authorization expiry does not match governed window")
        return self


class ExecutionAuthorization(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization: AuthorizationBody

    @model_validator(mode="after")
    def validate_transaction_identity(self) -> Self:
        expected = _sha256(_canonical_json_bytes(self.authorization))
        if self.transaction_id != expected:
            raise ValueError("transaction ID does not match canonical authorization bytes")
        return self


class ExecutionArtifactManifest(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["TRANSACTION_BOUND_EXECUTABLE_GENERATED"]
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    executable_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_container_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_container_is_semantic_payload_identity: Literal[False] = False
    authorization_specific_kaggle_inputs: Literal[0] = 0
    authorization_producer_notebooks: Literal[0] = 0
    manual_confirmation_json_files: Literal[0] = 0
    permitted_kaggle_input_roles: tuple[Literal["durable_runtime"], Literal["model_snapshot"]]
    runtime_execution_authorized: Literal[True] = True
    single_use_governance: Literal[True] = True
    runtime_anti_replay_established: Literal[False] = False


class TerminalDisposition(StrEnum):
    CONSUMED = "CONSUMED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    EXPIRED_UNUSED = "EXPIRED_UNUSED"
    CANCELLED_UNUSED = "CANCELLED_UNUSED"
    ABANDONED_BEFORE_EXECUTION = "ABANDONED_BEFORE_EXECUTION"


class ExecutionOutcome(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"
    INTERRUPTED = "INTERRUPTED"
    DIAGNOSTIC_INVALID = "DIAGNOSTIC_INVALID"


class TerminalReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    disposition: TerminalDisposition
    execution_attempted: bool
    execution_outcome: ExecutionOutcome | None = None
    terminalized_at: datetime
    saved_version_id: int | None = Field(default=None, ge=1)
    evidence_zip_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False

    @field_validator("terminalized_at")
    @classmethod
    def normalize_terminalized_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "terminalized_at")

    @model_validator(mode="after")
    def validate_terminal_semantics(self) -> Self:
        unused = {
            TerminalDisposition.EXPIRED_UNUSED,
            TerminalDisposition.CANCELLED_UNUSED,
            TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
        }
        if self.disposition in unused and (
            self.execution_attempted
            or self.execution_outcome is not None
            or self.saved_version_id is not None
        ):
            raise ValueError("unused disposition contains execution evidence")
        if self.disposition in {
            TerminalDisposition.CONSUMED,
            TerminalDisposition.OUTCOME_UNKNOWN,
        } and (not self.execution_attempted or self.saved_version_id is None):
            raise ValueError("attempted disposition requires saved version identity")
        return self


def _normalize_time(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(UTC)


def _canonical_json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _artifact_json_bytes(value: object) -> bytes:
    return _canonical_json_bytes(value) + b"\n"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise TransactionBoundError(
            "TRANSACTION_BOUND_REQUIRED_ARTIFACT_MISSING",
            "required artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _git(root: Path, *arguments: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", *arguments], cwd=root, check=False, capture_output=True, text=True
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _require_git(root: Path, *arguments: str) -> str:
    code, stdout, _ = _git(root, *arguments)
    if code != 0:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_GIT_STATE_FAILED", "unable to inspect repository state"
        )
    return stdout


def _require_merged_clean_main(root: Path) -> str:
    branch = _require_git(root, "branch", "--show-current")
    if branch != "main":
        raise TransactionBoundError(
            "TRANSACTION_BOUND_NOT_ON_MAIN", "live authorization requires main"
        )
    head = _require_git(root, "rev-parse", "HEAD")
    origin_main = _require_git(root, "rev-parse", "origin/main")
    if head != origin_main:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_MAIN_NOT_SYNCHRONIZED", "HEAD must equal origin/main"
        )
    status = _require_git(root, "status", "--porcelain=v1", "-uall")
    if status:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_REPOSITORY_NOT_CLEAN",
            "repository must be clean before live authorization",
        )
    code, _, _ = _git(root, "merge-base", "--is-ancestor", ARCHITECTURE_MERGE_COMMIT, head)
    if code != 0:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_ARCHITECTURE_NOT_ANCESTOR",
            "merged architecture is not an ancestor of HEAD",
        )
    return head


def _require_runtime_integration(root: Path, runtime_payload_path: Path) -> bytes:
    record_bytes = _read_required(root, RUNTIME_INTEGRATION_RECORD_PATH)
    try:
        record = json.loads(record_bytes)
    except json.JSONDecodeError as error:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_INVALID",
            "runtime integration record is invalid JSON",
            RUNTIME_INTEGRATION_RECORD_PATH.as_posix(),
        ) from error
    if not isinstance(record, dict):
        raise TransactionBoundError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_INVALID",
            "runtime integration record must be one object",
            RUNTIME_INTEGRATION_RECORD_PATH.as_posix(),
        )
    required = {
        "status": "TRANSACTION_BOUND_P5_P6_RUNTIME_INTEGRATION_VALID",
        "live_authorization_boundary_ready": True,
        "symlink_regression_covered": True,
        "authorization_specific_kaggle_inputs": 0,
    }
    drift = tuple(key for key, expected in required.items() if record.get(key) != expected)
    if drift:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_CONTRACT_DRIFT",
            "runtime integration contract drifted",
            RUNTIME_INTEGRATION_RECORD_PATH.as_posix(),
        )
    relative = record.get("runtime_payload_path")
    expected_sha = record.get("runtime_payload_sha256")
    if not isinstance(relative, str) or not isinstance(expected_sha, str):
        raise TransactionBoundError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_IDENTITY_MISSING",
            "runtime integration identity is missing",
            RUNTIME_INTEGRATION_RECORD_PATH.as_posix(),
        )
    expected_path = (root / relative).resolve()
    observed_path = runtime_payload_path.resolve()
    if observed_path != expected_path:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_RUNTIME_PAYLOAD_PATH_MISMATCH",
            "runtime payload path does not match merged integration record",
        )
    payload = _read_required(root, Path(relative))
    if _sha256(payload) != expected_sha:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_RUNTIME_PAYLOAD_IDENTITY_DRIFT",
            "runtime payload identity drifted from merged integration record",
            relative,
        )
    return payload


def _validate_architecture(root: Path) -> None:
    payload = _read_required(root, ARCHITECTURE_RECORD_PATH)
    if _sha256(payload) != ARCHITECTURE_RECORD_SHA256:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_ARCHITECTURE_IDENTITY_DRIFT",
            "architecture record identity drifted",
            ARCHITECTURE_RECORD_PATH.as_posix(),
        )
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise TransactionBoundError(
            "TRANSACTION_BOUND_ARCHITECTURE_INVALID", "architecture record must be one object"
        )
    required = {
        "decision": "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "next_gate": "IMPLEMENT_TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1",
    }
    if any(parsed.get(key) != value for key, value in required.items()):
        raise TransactionBoundError(
            "TRANSACTION_BOUND_ARCHITECTURE_CONTRACT_DRIFT", "architecture contract drifted"
        )


def _static_review(root: Path) -> dict[str, object]:
    _validate_architecture(root)
    source = _read_required(root, SOURCE_PATH)
    template = _read_required(root, TEMPLATE_PATH)
    design = _read_required(root, DESIGN_PATH)
    return {
        "schema_version": "1.0.0",
        "review_id": "auragateway-transaction-bound-execution-authorization-v1-review",
        "status": "APPROVED_FOR_STATIC_IMPLEMENTATION",
        "architecture_merge_commit": ARCHITECTURE_MERGE_COMMIT,
        "architecture_record_sha256": ARCHITECTURE_RECORD_SHA256,
        "source_sha256": _sha256(source),
        "generator_contract_sha256": _sha256(template),
        "design_sha256": _sha256(design),
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "operator_confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "transaction_id_derivation": "SHA256_CANONICAL_AUTHORIZATION_BYTES",
        "deterministic_generation_required": True,
        "runtime_anti_replay_established": False,
        "gpu_execution_authorized": False,
        "runtime_payload_integrated": False,
        "symlink_regression_remediated": False,
        "next_gate": NEXT_GATE,
    }


def _static_record(root: Path, review_bytes: bytes) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_id": "auragateway-transaction-bound-execution-authorization-v1",
        "status": "IMPLEMENTED_NOT_ISSUED",
        "architecture_merge_commit": ARCHITECTURE_MERGE_COMMIT,
        "review_sha256": _sha256(review_bytes),
        "source_path": SOURCE_PATH.as_posix(),
        "template_path": TEMPLATE_PATH.as_posix(),
        "runtime_execution_authorized": False,
        "live_authorization_issued": False,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "maximum_local_control_commands": 2,
        "maximum_kaggle_save_and_run_all_actions": 1,
        "runtime_anti_replay_established": False,
        "gpu_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def generate_static(root: Path) -> dict[str, object]:
    root = root.resolve()
    review_bytes = _artifact_json_bytes(_static_review(root))
    record_bytes = _artifact_json_bytes(_static_record(root, review_bytes))
    for relative, payload in ((REVIEW_PATH, review_bytes), (RECORD_PATH, record_bytes)):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return {
        "status": "TRANSACTION_BOUND_STATIC_ARTIFACTS_GENERATED",
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "next_gate": NEXT_GATE,
    }


def validate_static(root: Path) -> dict[str, object]:
    root = root.resolve()
    review_bytes = _artifact_json_bytes(_static_review(root))
    record_bytes = _artifact_json_bytes(_static_record(root, review_bytes))
    for relative, expected in ((REVIEW_PATH, review_bytes), (RECORD_PATH, record_bytes)):
        observed = _read_required(root, relative)
        if observed != expected:
            raise TransactionBoundError(
                "TRANSACTION_BOUND_STATIC_ARTIFACT_DRIFT",
                "generated static artifact drifted",
                relative.as_posix(),
            )
    for relative in (LIVE_AUTHORIZATION_PATH, LIVE_MANIFEST_PATH, TERMINAL_RECEIPT_PATH):
        if (root / relative).exists():
            raise TransactionBoundError(
                "TRANSACTION_BOUND_LIVE_LIFECYCLE_PRESENT",
                "static validation requires no live lifecycle artifact",
                relative.as_posix(),
            )
    return {
        "status": "TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1_VALID",
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_anti_replay_established": False,
        "live_authorization_issued": False,
        "gpu_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def build_intent(
    root: Path,
    runtime_payload: bytes,
    issuer_merge_commit: str,
    *,
    prepared_at: datetime,
    window_minutes: int,
    intent_id: str,
) -> AuthorizationIntent:
    return AuthorizationIntent(
        intent_id=intent_id,
        scope=AUTHORIZATION_SCOPE,
        prepared_at=prepared_at,
        authorization_window_minutes=window_minutes,
        issuer_merge_commit=issuer_merge_commit,
        architecture_record_sha256=ARCHITECTURE_RECORD_SHA256,
        implementation_source_sha256=_sha256(_read_required(root, SOURCE_PATH)),
        generator_contract_sha256=_sha256(_read_required(root, TEMPLATE_PATH)),
        runtime_payload_sha256=_sha256(runtime_payload),
        runtime=RuntimeModelContract(),
        budget=ExecutionBudget(),
        required_platform=RequiredPlatform(),
    )


def authorization_challenge(intent: AuthorizationIntent) -> str:
    return _sha256(_canonical_json_bytes(intent))


def build_authorization(
    intent: AuthorizationIntent,
    *,
    challenge: str,
    confirmed_at: datetime,
) -> tuple[ExecutionAuthorization, bytes]:
    confirmed = _normalize_time(confirmed_at, "confirmed_at")
    body = AuthorizationBody(
        authorization_id="tb-" + intent.intent_id,
        scope=AUTHORIZATION_SCOPE,
        authorization_challenge_sha256=challenge,
        operator_confirmation_method="RETYPE_DYNAMIC_SHA256_CHALLENGE",
        operator_confirmation_recorded=True,
        operator_confirmed_at=confirmed,
        issued_at=confirmed,
        expires_at=confirmed + timedelta(minutes=intent.authorization_window_minutes),
        authorization_window_minutes=intent.authorization_window_minutes,
        issuer_merge_commit=intent.issuer_merge_commit,
        architecture_record_sha256=intent.architecture_record_sha256,
        implementation_source_sha256=intent.implementation_source_sha256,
        generator_contract_sha256=intent.generator_contract_sha256,
        runtime_payload_sha256=intent.runtime_payload_sha256,
        runtime=intent.runtime,
        required_platform=intent.required_platform,
    )
    transaction_id = _sha256(_canonical_json_bytes(body))
    authorization = ExecutionAuthorization(
        transaction_id=transaction_id,
        authorization=body,
    )
    payload = _canonical_json_bytes(authorization)
    return authorization, payload


def render_executable_payload(
    root: Path,
    authorization: ExecutionAuthorization,
    authorization_bytes: bytes,
    runtime_payload: bytes,
) -> bytes:
    template = _read_required(root, TEMPLATE_PATH)
    generator_sha = _sha256(template)
    if authorization.authorization.generator_contract_sha256 != generator_sha:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_GENERATOR_IDENTITY_DRIFT",
            "authorization does not bind current generator contract",
        )
    if authorization.authorization.runtime_payload_sha256 != _sha256(runtime_payload):
        raise TransactionBoundError(
            "TRANSACTION_BOUND_RUNTIME_PAYLOAD_DRIFT",
            "authorization does not bind supplied runtime payload",
        )
    source = template.decode("utf-8")
    replacements = {
        "__AUTHORIZATION_B64__": base64.b64encode(authorization_bytes).decode("ascii"),
        "__RUNTIME_PAYLOAD_B64__": base64.b64encode(runtime_payload).decode("ascii"),
        "__TRANSACTION_ID__": authorization.transaction_id,
        "__RUNTIME_PAYLOAD_SHA256__": authorization.authorization.runtime_payload_sha256,
        "__GENERATOR_CONTRACT_SHA256__": generator_sha,
    }
    for marker, value in replacements.items():
        if source.count(marker) != 1:
            raise TransactionBoundError(
                "TRANSACTION_BOUND_TEMPLATE_MARKER_DRIFT",
                "generator template marker cardinality drifted",
            )
        source = source.replace(marker, value)
    return source.encode("utf-8")


def build_notebook(executable_payload: bytes) -> bytes:
    source = executable_payload.decode("utf-8").splitlines(keepends=True)
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source,
            }
        ],
        "metadata": {"language_info": {"name": "python", "version": "3.12"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return (
        json.dumps(notebook, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        + b"\n"
    )


def build_manifest(
    authorization: ExecutionAuthorization,
    authorization_bytes: bytes,
    executable_payload: bytes,
    notebook_bytes: bytes,
) -> ExecutionArtifactManifest:
    return ExecutionArtifactManifest(
        status="TRANSACTION_BOUND_EXECUTABLE_GENERATED",
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(authorization_bytes),
        runtime_payload_sha256=authorization.authorization.runtime_payload_sha256,
        generator_contract_sha256=authorization.authorization.generator_contract_sha256,
        executable_payload_sha256=_sha256(executable_payload),
        notebook_container_sha256=_sha256(notebook_bytes),
        permitted_kaggle_input_roles=("durable_runtime", "model_snapshot"),
    )


def authorize_generate(
    root: Path, runtime_payload_path: Path, output_path: Path, *, window_minutes: int
) -> dict[str, object]:
    root = root.resolve()
    validate_static(root)
    issuer_commit = _require_merged_clean_main(root)
    for relative in (LIVE_AUTHORIZATION_PATH, LIVE_MANIFEST_PATH, TERMINAL_RECEIPT_PATH):
        if (root / relative).exists():
            raise TransactionBoundError(
                "TRANSACTION_BOUND_LIFECYCLE_ALREADY_EXISTS",
                "live transaction lifecycle already exists",
                relative.as_posix(),
            )
    runtime_payload = _require_runtime_integration(root, runtime_payload_path)
    if output_path.exists():
        raise TransactionBoundError(
            "TRANSACTION_BOUND_OUTPUT_EXISTS",
            "generated notebook output already exists",
            str(output_path),
        )
    prepared = datetime.now(UTC)
    intent = build_intent(
        root,
        runtime_payload,
        issuer_commit,
        prepared_at=prepared,
        window_minutes=window_minutes,
        intent_id=secrets.token_hex(16),
    )
    challenge = authorization_challenge(intent)
    print("authorization_challenge=" + challenge)
    print("scope=" + AUTHORIZATION_SCOPE)
    print("issuer_merge_commit=" + issuer_commit)
    print("runtime_payload_sha256=" + intent.runtime_payload_sha256)
    print("maximum_model_requests=6")
    print("required_platform=T4_X2 / 2 GPUs / Internet Off")
    observed = input(
        "Retype the authorization challenge to authorize exactly one governed execution: "
    ).strip()
    if observed != challenge:
        raise TransactionBoundError(
            "TRANSACTION_BOUND_OPERATOR_CONFIRMATION_MISMATCH",
            "interactive authorization challenge did not match",
        )
    confirmed = datetime.now(UTC)
    authorization, authorization_bytes = build_authorization(
        intent, challenge=challenge, confirmed_at=confirmed
    )
    executable_payload = render_executable_payload(
        root, authorization, authorization_bytes, runtime_payload
    )
    notebook_bytes = build_notebook(executable_payload)
    manifest = build_manifest(
        authorization, authorization_bytes, executable_payload, notebook_bytes
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(notebook_bytes)
    (root / LIVE_AUTHORIZATION_PATH).write_bytes(_artifact_json_bytes(authorization))
    (root / LIVE_MANIFEST_PATH).write_bytes(_artifact_json_bytes(manifest))
    return {
        "status": "TRANSACTION_BOUND_EXECUTION_ARTIFACT_AUTHORIZED_AND_GENERATED",
        "transaction_id": authorization.transaction_id,
        "authorization_sha256": _sha256(authorization_bytes),
        "runtime_payload_sha256": authorization.authorization.runtime_payload_sha256,
        "executable_payload_sha256": manifest.executable_payload_sha256,
        "notebook_container_sha256": manifest.notebook_container_sha256,
        "output_path": str(output_path),
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_anti_replay_established": False,
        "next_gate": "FRESH_PLATFORM_OBSERVATION_THEN_ONE_SAVE_AND_RUN_ALL",
    }


def terminalize(
    root: Path,
    *,
    disposition: TerminalDisposition,
    outcome: ExecutionOutcome | None,
    saved_version_id: int | None,
    evidence_zip_sha256: str | None,
    terminal_log_sha256: str | None,
) -> dict[str, object]:
    root = root.resolve()
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise TransactionBoundError(
            "TRANSACTION_BOUND_ALREADY_TERMINAL", "transaction already has a terminal receipt"
        )
    authorization_bytes_artifact = _read_required(root, LIVE_AUTHORIZATION_PATH)
    manifest_payload = json.loads(_read_required(root, LIVE_MANIFEST_PATH))
    authorization_payload = json.loads(authorization_bytes_artifact)
    authorization = ExecutionAuthorization.model_validate(authorization_payload)
    manifest = ExecutionArtifactManifest.model_validate(manifest_payload)
    canonical_authorization = _canonical_json_bytes(authorization)
    if manifest.authorization_sha256 != _sha256(canonical_authorization):
        raise TransactionBoundError(
            "TRANSACTION_BOUND_LIFECYCLE_IDENTITY_DRIFT",
            "live manifest no longer binds live authorization",
        )
    unused = disposition in {
        TerminalDisposition.EXPIRED_UNUSED,
        TerminalDisposition.CANCELLED_UNUSED,
        TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
    }
    receipt = TerminalReceipt(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(canonical_authorization),
        disposition=disposition,
        execution_attempted=not unused,
        execution_outcome=outcome,
        terminalized_at=datetime.now(UTC),
        saved_version_id=saved_version_id,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
    )
    (root / TERMINAL_RECEIPT_PATH).write_bytes(_artifact_json_bytes(receipt))
    return {
        "status": "TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_TERMINAL",
        "transaction_id": receipt.transaction_id,
        "disposition": receipt.disposition.value,
        "execution_attempted": receipt.execution_attempted,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "next_gate": "PRESERVE_AND_ACCEPT_OR_RECONCILE_TRANSACTION_BOUND_EXECUTION_EVIDENCE",
    }


def _default_output() -> Path:
    return Path.home() / "Desktop" / "ag-p5-p6-transaction-bound-v1.ipynb"


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command", choices=("generate", "validate", "authorize-generate", "terminalize")
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--runtime-payload")
    parser.add_argument("--output")
    parser.add_argument("--window-minutes", type=int, default=DEFAULT_WINDOW_MINUTES)
    parser.add_argument("--disposition", choices=tuple(item.value for item in TerminalDisposition))
    parser.add_argument("--outcome", choices=tuple(item.value for item in ExecutionOutcome))
    parser.add_argument("--saved-version-id", type=int)
    parser.add_argument("--evidence-zip-sha256")
    parser.add_argument("--terminal-log-sha256")
    return parser


def _print_error(error: TransactionBoundError) -> None:
    print(
        _canonical_json_bytes(
            {"error_code": error.error_code, "safe_message": error.safe_message, "path": error.path}
        ).decode("utf-8"),
        file=sys.stderr,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        if args.command == "generate":
            result = generate_static(root)
        elif args.command == "validate":
            result = validate_static(root)
        elif args.command == "authorize-generate":
            if args.runtime_payload is None:
                raise TransactionBoundError(
                    "TRANSACTION_BOUND_ARGUMENT_MISSING", "--runtime-payload is required"
                )
            result = authorize_generate(
                root,
                Path(args.runtime_payload).resolve(),
                Path(args.output).resolve() if args.output else _default_output(),
                window_minutes=args.window_minutes,
            )
        else:
            if args.disposition is None:
                raise TransactionBoundError(
                    "TRANSACTION_BOUND_ARGUMENT_MISSING", "--disposition is required"
                )
            result = terminalize(
                root,
                disposition=TerminalDisposition(args.disposition),
                outcome=None if args.outcome is None else ExecutionOutcome(args.outcome),
                saved_version_id=args.saved_version_id,
                evidence_zip_sha256=args.evidence_zip_sha256,
                terminal_log_sha256=args.terminal_log_sha256,
            )
    except (
        TransactionBoundError,
        ValidationError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, TransactionBoundError):
            _print_error(error)
        else:
            _print_error(TransactionBoundError("TRANSACTION_BOUND_VALIDATION_FAILED", str(error)))
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
