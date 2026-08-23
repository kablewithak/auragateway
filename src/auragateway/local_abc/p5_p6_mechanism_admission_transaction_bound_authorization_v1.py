"""Transaction-bound authorization for the P5/P6 mechanism-admission successor V1.

Static generation and validation are inert. Live authority can only be issued from
synchronized main after this implementation is merged and after the operator exactly
retypes a fresh dynamic SHA-256 challenge.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import re
import secrets
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

BASE_MAIN_COMMIT: Final = "92954e6e00cd144575a73d10f749feca24e7b735"
BEHAVIOR_IMPLEMENTATION_MERGE_COMMIT: Final = "2b1841aee4397ae0c72bad6b2c9e7069835d8399"

RECONCILIATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_"
    "reconciliation_v1.json"
)
RECONCILIATION_RECORD_SHA256: Final = (
    "06b20e84a01e41a3952399d430adf5a6923eaefe79b559f0f8412c180655fc4f"
)
RECONCILIATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_"
    "reconciliation_v1_review.json"
)
RECONCILIATION_REVIEW_SHA256: Final = (
    "e7068ee5464435b7ac593efb09a5c408000703ca252a5780e1a6b110105030bf"
)

LIFECYCLE_RECONCILIATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_344405133_reconciliation_v1.json"
)
LIFECYCLE_RECONCILIATION_GIT_BLOB: Final = "731a287dac3cc5ae947b5fd244395c6fd7339323"
PRE_REMEDIATION_RUNTIME_PAYLOAD_SHA256: Final = (
    "ecf85755c1601452a7a63be81f2d536e1106229baed0a5e58bb38e85ed4adfd4"
)

BEHAVIOR_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_v1.py"
)
BEHAVIOR_SOURCE_SHA256: Final = "90e74350782ec833865136c9efc3074d714a94148e7da5fd959483935a3488f3"
BEHAVIOR_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_mechanism_admission_successor_v1.py.tmpl"
)
BEHAVIOR_TEMPLATE_SHA256: Final = "e317ec9c06e256f21a80c3008a09a20036e5b4a8d978797013dacadd48d0b745"
BEHAVIOR_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_v1_implementation_review.json"
)
BEHAVIOR_REVIEW_SHA256: Final = "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
BEHAVIOR_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1.json"
)
BEHAVIOR_DESIGN_SHA256: Final = "6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c"
MECHANISM_CONTRACT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_contract_v2.json"
)
MECHANISM_CONTRACT_SHA256: Final = (
    "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
)
IMPLEMENTATION_ADDENDUM_PATH: Final = Path(
    "docs/adr/2026-08-22-local-abc-p5-p6-mechanism-admission-successor-"
    "runtime-outcome-contract-addendum-v1.md"
)
IMPLEMENTATION_ADDENDUM_SHA256: Final = (
    "395f9c7e9955594d7c962659dd882e0851dcc6f9833715bb53e5d37bb7439239"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_authorization_v1.py"
)
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/"
    "p5_p6_mechanism_admission_transaction_bound_wrapper_v1.py.tmpl"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_mechanism_admission_transaction_bound_authorization_v1.py"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P5_P6_Mechanism_Admission_Transaction_Bound_Authorization_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p5_p6_mechanism_admission_transaction_bound_authorization_v1.md"
)
RUNTIME_PAYLOAD_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_v1_record.json"
)

LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_transaction_bound_lifecycle_r1_authorization_live.json"
)
LIVE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_transaction_bound_lifecycle_r1_artifact_live_manifest.json"
)
PLATFORM_OBSERVATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_transaction_bound_lifecycle_r1_platform_observation_live.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_transaction_bound_lifecycle_r1_authorization_terminal.json"
)

AUTHORIZATION_SCOPE: Final = "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
NOTEBOOK_NAME: Final = "ag-p5-p6-mechanism-tx-lifecycle-r1"
EVIDENCE_ZIP_NAME: Final = "ag-p5-p6-mechanism-successor-lifecycle-r1-evidence.zip"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
DEFAULT_WINDOW_MINUTES: Final = 180
MAX_WINDOW_MINUTES: Final = 240
MAX_CONFIRMATION_AGE_MINUTES: Final = 15
PLATFORM_CONTROL_ID: Final = "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"

NEXT_GATE: Final = (
    "MERGE_THEN_ISSUE_FRESH_P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_V1"
)
NEXT_GATE_AFTER_ISSUE: Final = "PERSIST_DURABLE_PLATFORM_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
NEXT_GATE_AFTER_OBSERVATION: Final = "ONE_SAVE_AND_RUN_ALL_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
NEXT_GATE_AFTER_TERMINAL: Final = (
    "PRESERVE_AND_RECONCILE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_EVIDENCE_V1"
)

HISTORICAL_UNTRACKED_PATHS: Final = (
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_execution_artifact_"
    "v1_live_manifest.json",
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_execution_authorization_v1_live.json",
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_execution_authorization_"
    "v1_terminal.json",
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_platform_observation_v1_live.json",
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_v1_live.json",
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_artifact_v1_live_manifest.json",
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_platform_"
    "observation_v1_live.json",
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_v1_terminal.json",
)

STATIC_PATHS: Final = (SOURCE_PATH, TEMPLATE_PATH, TEST_PATH, REPORT_PATH, RUNBOOK_PATH)
GENERATED_PATHS: Final = (RUNTIME_PAYLOAD_PATH, REVIEW_PATH, RECORD_PATH)
CANDIDATE_PATHS: Final = tuple(sorted((*STATIC_PATHS, *GENERATED_PATHS)))


class AuthorizationIssuerError(RuntimeError):
    """Metadata-safe fail-closed authorization error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_ARGUMENT_ERROR",
            message,
        )


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
    attention_backend: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    gpu_topology: Literal["T4_X2"] = "T4_X2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_directory_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = MODEL_SNAPSHOT_SHA256
    prefix_caching_enabled: Literal[True] = True
    cache_block_size: Literal[16] = 16
    max_model_len: Literal[4096] = 4096


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_save_and_run_all_actions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    maximum_worker_teardowns: Literal[3] = 3
    maximum_output_tokens_per_request: Literal[32] = 32
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_workers: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class RequiredPlatform(FrozenModel):
    accelerator: Literal["T4_X2"] = "T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    external_network_access_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    preissuance_platform_observation_required: Literal[False] = False
    fresh_post_artifact_observation_required: Literal[True] = True
    observation_precedes_save_and_run_all: Literal[True] = True
    observation_mounted_as_runtime_input: Literal[False] = False
    machine_observable_runtime_topology_check_required: Literal[True] = True


class MechanismContract(FrozenModel):
    semantic_states: tuple[
        Literal["EXACT_MATCH"],
        Literal["VALID_JSON_MISMATCH"],
        Literal["NON_OBJECT_JSON"],
        Literal["INVALID_JSON"],
    ] = (
        "EXACT_MATCH",
        "VALID_JSON_MISMATCH",
        "NON_OBJECT_JSON",
        "INVALID_JSON",
    )
    semantic_mismatch_blocks_mechanism: Literal[False] = False
    invalid_json_blocks_mechanism: Literal[False] = False
    finish_reason_stop_required: Literal[True] = True
    response_content_digest_required: Literal[True] = True
    raw_output_logging_permitted: Literal[False] = False
    p5_uses_semantic_state: Literal[False] = False
    p6_uses_semantic_state: Literal[False] = False
    p5_acceptance_relaxed: Literal[False] = False
    p6_acceptance_relaxed: Literal[False] = False


class AuthorizationIntent(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    intent_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"] = AUTHORIZATION_SCOPE
    prepared_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=MAX_WINDOW_MINUTES)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    reconciliation_record_sha256: Literal[
        "06b20e84a01e41a3952399d430adf5a6923eaefe79b559f0f8412c180655fc4f"
    ] = RECONCILIATION_RECORD_SHA256
    behavior_implementation_merge_commit: Literal["2b1841aee4397ae0c72bad6b2c9e7069835d8399"] = (
        BEHAVIOR_IMPLEMENTATION_MERGE_COMMIT
    )
    behavior_implementation_review_sha256: Literal[
        "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
    ] = BEHAVIOR_REVIEW_SHA256
    mechanism_admission_contract_sha256: Literal[
        "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
    ] = MECHANISM_CONTRACT_SHA256
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    mechanism: MechanismContract
    required_platform: RequiredPlatform

    @field_validator("prepared_at")
    @classmethod
    def normalize_prepared_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "prepared_at")


class AuthorizationBody(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str = Field(pattern=r"^p5p6mech-[0-9a-f]{32}$")
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle: Literal["ISSUED"] = "ISSUED"
    scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"] = AUTHORIZATION_SCOPE
    authorization_challenge_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_confirmation_method: Literal["RETYPE_DYNAMIC_SHA256_CHALLENGE"] = (
        "RETYPE_DYNAMIC_SHA256_CHALLENGE"
    )
    operator_confirmation_recorded: Literal[True] = True
    operator_confirmed_at: datetime
    issued_at: datetime
    expires_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=MAX_WINDOW_MINUTES)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    reconciliation_record_sha256: Literal[
        "06b20e84a01e41a3952399d430adf5a6923eaefe79b559f0f8412c180655fc4f"
    ] = RECONCILIATION_RECORD_SHA256
    behavior_implementation_merge_commit: Literal["2b1841aee4397ae0c72bad6b2c9e7069835d8399"] = (
        BEHAVIOR_IMPLEMENTATION_MERGE_COMMIT
    )
    behavior_implementation_review_sha256: Literal[
        "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
    ] = BEHAVIOR_REVIEW_SHA256
    mechanism_admission_contract_sha256: Literal[
        "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
    ] = MECHANISM_CONTRACT_SHA256
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    mechanism: MechanismContract
    required_platform: RequiredPlatform
    platform_observation_control_id: Literal[
        "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    ] = PLATFORM_CONTROL_ID
    durable_platform_observation_required: Literal[True] = True
    runtime_execution_authorized: Literal[True] = True
    mechanism_admission_execution_authorized: Literal[True] = True
    single_use: Literal[True] = True
    every_terminal_attempt_consumes_authorization: Literal[True] = True
    unchanged_replay_authorized: Literal[False] = False
    authorization_reusable: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False
    repository_acceptance_established: Literal[False] = False
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
        expected_expiry = self.issued_at + timedelta(minutes=self.authorization_window_minutes)
        if self.expires_at != expected_expiry:
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
    status: Literal["TRANSACTION_BOUND_EXECUTABLE_GENERATED"] = (
        "TRANSACTION_BOUND_EXECUTABLE_GENERATED"
    )
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    executable_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_container_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_container_is_semantic_payload_identity: Literal[False] = False
    authorization_specific_kaggle_inputs: Literal[0] = 0
    authorization_producer_notebooks: Literal[0] = 0
    manual_confirmation_json_files: Literal[0] = 0
    permitted_kaggle_input_roles: tuple[
        Literal["durable_runtime"],
        Literal["model_snapshot"],
    ] = ("durable_runtime", "model_snapshot")
    platform_observation_required_before_save_and_run_all: Literal[True] = True
    platform_observation_persisted: Literal[False] = False
    runtime_execution_authorized: Literal[True] = True
    single_use_governance: Literal[True] = True
    runtime_anti_replay_established: Literal[False] = False


class PlatformObservationReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    control_id: Literal["PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"] = PLATFORM_CONTROL_ID
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_observed_at: datetime
    accelerator: Literal["T4_X2"] = "T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"] = "KAGGLE_NOTEBOOK_SETTINGS_UI"
    persisted_before_save_and_run_all: Literal[True] = True
    receipt_runtime_input: Literal[False] = False

    @field_validator("platform_observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "platform_observed_at")


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
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    disposition: TerminalDisposition
    execution_attempted: bool
    execution_outcome: ExecutionOutcome | None = None
    terminalized_at: datetime
    saved_version_id: int | None = Field(default=None, ge=1)
    platform_observation_receipt_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    evidence_zip_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False] = False
    repository_acceptance_established: Literal[False] = False
    p5_requalified: Literal[False] = False
    p6_requalified: Literal[False] = False

    @field_validator("terminalized_at")
    @classmethod
    def normalize_terminalized_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "terminalized_at")

    @model_validator(mode="after")
    def validate_terminal_semantics(self) -> Self:
        unused = self.disposition in {
            TerminalDisposition.EXPIRED_UNUSED,
            TerminalDisposition.CANCELLED_UNUSED,
            TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
        }
        if unused and self.execution_attempted:
            raise ValueError("unused disposition cannot report execution attempted")
        if unused and self.execution_outcome is not None:
            raise ValueError("unused disposition cannot carry an execution outcome")
        if self.disposition is TerminalDisposition.CONSUMED:
            if not self.execution_attempted:
                raise ValueError("CONSUMED requires execution attempted")
            if self.execution_outcome is None:
                raise ValueError("CONSUMED requires execution outcome")
        return self


def _normalize_time(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(UTC)


def _canonical_json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _artifact_json_bytes(value: object) -> bytes:
    return _canonical_json_bytes(value) + b"\n"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_REQUIRED_ARTIFACT_MISSING",
            "required authorization artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _verify_hash(root: Path, relative: Path, expected: str) -> bytes:
    payload = _read_required(root, relative)
    if _sha256(payload) != expected:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_AUTHORITY_IDENTITY_DRIFT",
            "required authorization authority identity drifted",
            relative.as_posix(),
        )
    return payload


def _git(root: Path, *arguments: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _require_git(root: Path, *arguments: str) -> str:
    code, stdout, stderr = _git(root, *arguments)
    if code != 0:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_GIT_COMMAND_FAILED",
            stderr or "required git command failed",
        )
    return stdout


def _require_base_ancestor(root: Path) -> None:
    code, _, _ = _git(root, "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, "HEAD")
    if code != 0:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_BASE_MAIN_MISSING",
            "merged reconciliation design is not an ancestor of HEAD",
        )


def _validate_reconciliation(root: Path) -> None:
    record_bytes = _verify_hash(
        root,
        RECONCILIATION_RECORD_PATH,
        RECONCILIATION_RECORD_SHA256,
    )
    _verify_hash(
        root,
        RECONCILIATION_REVIEW_PATH,
        RECONCILIATION_REVIEW_SHA256,
    )
    record = json.loads(record_bytes)
    if not isinstance(record, dict):
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_RECONCILIATION_INVALID",
            "reconciliation record must be one JSON object",
        )
    required = {
        "status": "DESIGN_RECONCILED_NOT_IMPLEMENTED",
        "decision": "RESTORE_TRANSACTION_BOUND_AUTHORIZATION_FOR_MECHANISM_ADMISSION_SUCCESSOR",
        "authorization_predecessor": "TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1",
        "behavioral_predecessor": "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2",
        "runtime_execution_authorized": False,
        "live_authorization_issued": False,
        "next_gate": (
            "IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_V1"
        ),
    }
    drift = tuple(key for key, expected in required.items() if record.get(key) != expected)
    if drift:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_RECONCILIATION_SEMANTIC_DRIFT",
            "reconciliation semantics drifted: " + ",".join(drift),
        )
    architecture = record.get("authorization_architecture")
    if not isinstance(architecture, dict):
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_RECONCILIATION_SEMANTIC_DRIFT",
            "authorization architecture is missing",
        )
    architecture_required = {
        "decision": "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "operator_confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "preissuance_platform_observation_required": False,
        "fresh_post_artifact_observation_required": True,
        "observation_mounted_as_runtime_input": False,
    }
    architecture_drift = tuple(
        key for key, expected in architecture_required.items() if architecture.get(key) != expected
    )
    if architecture_drift:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_RECONCILIATION_SEMANTIC_DRIFT",
            "authorization architecture drifted: " + ",".join(architecture_drift),
        )


def _validate_lifecycle_reconciliation(root: Path) -> None:
    blob = _require_git(
        root,
        "rev-parse",
        "HEAD:" + LIFECYCLE_RECONCILIATION_PATH.as_posix(),
    )
    if blob != LIFECYCLE_RECONCILIATION_GIT_BLOB:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_LIFECYCLE_RECONCILIATION_IDENTITY_DRIFT",
            "target-runtime lifecycle reconciliation identity drifted",
            LIFECYCLE_RECONCILIATION_PATH.as_posix(),
        )
    payload = _read_required(root, LIFECYCLE_RECONCILIATION_PATH)
    record = json.loads(payload)
    if not isinstance(record, dict):
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_LIFECYCLE_RECONCILIATION_INVALID",
            "target-runtime lifecycle reconciliation must be one JSON object",
        )
    required = {
        "status": "ACCEPTED_DIAGNOSTIC_OUTCOME_UNKNOWN",
        "saved_version_id": 344405133,
        "runtime_payload_sha256": PRE_REMEDIATION_RUNTIME_PAYLOAD_SHA256,
        "runtime_install_subprocess": "PASSED",
        "first_supported_divergence": ("POST_INSTALL_TARGET_RUNTIME_SNAPSHOT_SYMLINK_REJECTION"),
        "diagnostic_masking_established": True,
        "baseline_venv_copies_enforced": False,
        "cleanup_snapshot_protected_from_masking": False,
        "worker_starts": 0,
        "model_requests": 0,
        "p5_executed": False,
        "p6_executed": False,
        "new_execution_authorized": False,
        "next_gate": (
            "IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TARGET_RUNTIME_LIFECYCLE_REMEDIATION_V1"
        ),
    }
    drift = tuple(key for key, expected in required.items() if record.get(key) != expected)
    if drift:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_LIFECYCLE_RECONCILIATION_SEMANTIC_DRIFT",
            "target-runtime lifecycle reconciliation drifted: " + ",".join(drift),
        )


def _validate_behavior_authorities(root: Path) -> None:
    for relative, expected in (
        (BEHAVIOR_SOURCE_PATH, BEHAVIOR_SOURCE_SHA256),
        (BEHAVIOR_TEMPLATE_PATH, BEHAVIOR_TEMPLATE_SHA256),
        (BEHAVIOR_REVIEW_PATH, BEHAVIOR_REVIEW_SHA256),
        (BEHAVIOR_DESIGN_PATH, BEHAVIOR_DESIGN_SHA256),
        (MECHANISM_CONTRACT_PATH, MECHANISM_CONTRACT_SHA256),
        (IMPLEMENTATION_ADDENDUM_PATH, IMPLEMENTATION_ADDENDUM_SHA256),
    ):
        _verify_hash(root, relative, expected)


TRANSACTION_CONTEXT_FUNCTION: Final = r"""def require_transaction_bound_context(
) -> dict[str, object]:
    transaction_id = globals().get("AURAGATEWAY_TRANSACTION_ID")
    if (
        not isinstance(transaction_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", transaction_id) is None
    ):
        raise DiagnosticFailure(
            "AUTHORITY_FAILURE",
            "transaction-bound wrapper admission context is missing or invalid",
        )
    return {
        "transaction_id": transaction_id,
        "authorization_transport": "EMBEDDED_WRAPPER_ADMISSION",
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_execution_authorized": True,
    }
"""


def _replace_between(
    source: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start_count = source.count(start_marker)
    end_count = source.count(end_marker)
    if start_count != 1 or end_count != 1:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_RUNTIME_TRANSFORM_DRIFT",
            f"{label} marker cardinality drifted: start={start_count}, end={end_count}",
            BEHAVIOR_TEMPLATE_PATH.as_posix(),
        )
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[:start] + replacement + source[end:]


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_RUNTIME_TRANSFORM_DRIFT",
            f"{label} expected one transform target; observed {count}",
            BEHAVIOR_TEMPLATE_PATH.as_posix(),
        )
    return source.replace(old, new, 1)


def _materialize_behavior_template(root: Path) -> str:
    template = _read_required(root, BEHAVIOR_TEMPLATE_PATH).decode("utf-8")
    replacements = {
        "__NOTEBOOK_NAME__": NOTEBOOK_NAME,
        "__SOURCE_MAIN_COMMIT__": BASE_MAIN_COMMIT,
        "__IMPLEMENTATION_REVIEW_SHA256__": BEHAVIOR_REVIEW_SHA256,
        "__DESIGN_RECORD_SHA256__": BEHAVIOR_DESIGN_SHA256,
        "__MECHANISM_ADMISSION_CONTRACT_SHA256__": MECHANISM_CONTRACT_SHA256,
        "__IMPLEMENTATION_ADDENDUM_SHA256__": IMPLEMENTATION_ADDENDUM_SHA256,
        "__MODEL_SNAPSHOT_SHA256__": MODEL_SNAPSHOT_SHA256,
        "__EVIDENCE_ZIP_NAME__": EVIDENCE_ZIP_NAME,
    }
    for marker, value in replacements.items():
        if template.count(marker) != 1:
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_RUNTIME_TEMPLATE_MARKER_DRIFT",
                f"behavior runtime marker cardinality drifted: {marker}",
                BEHAVIOR_TEMPLATE_PATH.as_posix(),
            )
        template = template.replace(marker, value, 1)
    if re.search(r"__[A-Z0-9_]+__", template) is not None:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_RUNTIME_TEMPLATE_MARKER_DRIFT",
            "unresolved behavior runtime marker remains",
            BEHAVIOR_TEMPLATE_PATH.as_posix(),
        )
    return template


def _function_ast(source: str, name: str) -> str:
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.dump(node, annotate_fields=True, include_attributes=False)
    raise AuthorizationIssuerError(
        "P5_P6_TX_AUTH_REQUIRED_FUNCTION_MISSING",
        f"required runtime function is missing: {name}",
    )


def build_runtime_payload(root: Path) -> bytes:
    predecessor = _materialize_behavior_template(root)
    source = _replace_between(
        predecessor,
        "\nAUTHORIZATION_FILENAME = ",
        "\n\ndef consume_actions(",
        "\n" + TRANSACTION_CONTEXT_FUNCTION.rstrip(),
        "authorization transport removal",
    )
    source = _replace_once(
        source,
        (
            '        active_failure_code = "AUTHORITY_FAILURE"\n'
            "        authorization = require_execution_authorization()"
        ),
        (
            '        active_failure_code = "AUTHORITY_FAILURE"\n'
            "        authorization = require_transaction_bound_context()"
        ),
        "transaction-bound runtime context",
    )

    source = _replace_once(
        source,
        ('IMPLEMENTATION_REVIEW_SHA256: Final = "' + BEHAVIOR_REVIEW_SHA256 + '"'),
        (f'IMPLEMENTATION_REVIEW_SHA256: Final = (\n    "{BEHAVIOR_REVIEW_SHA256}"\n)'),
        "materialized implementation review identity formatting",
    )
    source = _replace_once(
        source,
        ('MECHANISM_ADMISSION_CONTRACT_SHA256: Final = "' + MECHANISM_CONTRACT_SHA256 + '"'),
        (f'MECHANISM_ADMISSION_CONTRACT_SHA256: Final = (\n    "{MECHANISM_CONTRACT_SHA256}"\n)'),
        "materialized mechanism contract identity formatting",
    )
    source = _replace_once(
        source,
        ('IMPLEMENTATION_ADDENDUM_SHA256: Final = "' + IMPLEMENTATION_ADDENDUM_SHA256 + '"'),
        (f'IMPLEMENTATION_ADDENDUM_SHA256: Final = (\n    "{IMPLEMENTATION_ADDENDUM_SHA256}"\n)'),
        "materialized implementation addendum identity formatting",
    )
    source = _replace_once(
        source,
        '    worker: "Worker",',
        "    worker: Worker,",
        "Worker forward annotation",
    )
    source = _replace_once(
        source,
        "zip(left.token_ids, right.token_ids)",
        "zip(left.token_ids, right.token_ids, strict=False)",
        "explicit zip truncation semantics",
    )

    source = _replace_once(
        source,
        '        return response.read().decode("utf-8")',
        '        return response.read().decode("utf-8")  # type: ignore[no-any-return]',
        "inherited get_text typing",
    )
    source = _replace_once(
        source,
        '        name = raw.get("path")',
        '        name = raw.get("path")  # type: ignore[assignment]',
        "inherited wheelhouse manifest typing",
    )
    source = _replace_once(
        source,
        "                chunk = source.read(8192)",
        "                chunk = source.read(8192)  # type: ignore[attr-defined]",
        "inherited capture read protocol typing",
    )
    source = _replace_once(
        source,
        "            source.close()",
        "            source.close()  # type: ignore[attr-defined]",
        "inherited capture close protocol typing",
    )
    source = _replace_once(
        source,
        "    return payload\n\n\ndef _path_within_target",
        "    return payload  # type: ignore[no-any-return]\n\n\ndef _path_within_target",
        "inherited target-runtime JSON typing",
    )
    source = _replace_once(
        source,
        '        self.memory_before_start_mib = int(identity["memory_used_mib"])',
        (
            "        self.memory_before_start_mib = int(  "
            "# type: ignore[call-overload]\n"
            '            identity["memory_used_mib"]\n'
            "        )"
        ),
        "inherited worker GPU-memory typing",
    )
    source = _replace_once(
        source,
        '            return int(identity["memory_used_mib"])',
        (
            '            return int(identity["memory_used_mib"])'
            "  # type: ignore[no-any-return, call-overload]"
        ),
        "inherited GPU-memory helper typing",
    )
    source = _replace_once(
        source,
        "        p5_observations = {",
        "        p5_observations: dict[str, object] = {",
        "P5 observation dictionary typing",
    )
    source = _replace_once(
        source,
        '            "--without-pip",\n            str(TARGET_ROOT),',
        '            "--without-pip",\n            "--copies",\n            str(TARGET_ROOT),',
        "target-runtime venv copies",
    )
    source = _replace_once(
        source,
        (
            "def cleanup_scratch() -> dict[str, object]:\n"
            "    before = directory_snapshot(SCRATCH_ROOT)\n"
            '    status = "PASSED"\n'
            "    error_type = None\n"
            "    safe_message = None\n"
            "    try:"
        ),
        (
            "def cleanup_scratch() -> dict[str, object]:\n"
            "    before: dict[str, object]\n"
            '    status = "PASSED"\n'
            "    error_type: str | None = None\n"
            "    safe_message: str | None = None\n"
            "    try:\n"
            "        before = directory_snapshot(SCRATCH_ROOT)\n"
            "    except (OSError, RuntimeError) as error:\n"
            "        before = {\n"
            '            "exists": True,\n'
            '            "file_count": 0,\n'
            '            "size_bytes": 0,\n'
            '            "snapshot_failed": True,\n'
            "        }\n"
            '        status = "FAILED"\n'
            "        error_type = type(error).__name__\n"
            "        safe_message = sanitize_excerpt(str(error))\n"
            "    try:"
        ),
        "cleanup snapshot failure containment",
    )
    source = _replace_once(
        source,
        (
            "    except OSError as error:\n"
            '        status = "FAILED"\n'
            "        error_type = type(error).__name__\n"
            "        safe_message = sanitize_excerpt(str(error))\n"
            "    report = {"
        ),
        (
            "    except OSError as error:\n"
            '        status = "FAILED"\n'
            "        if error_type is None:\n"
            "            error_type = type(error).__name__\n"
            "            safe_message = sanitize_excerpt(str(error))\n"
            "    report = {"
        ),
        "cleanup first-failure preservation",
    )

    for token in (
        "AUTHORIZATION_CONTROL_NOTEBOOK_NAME",
        "AUTHORIZATION_CONTROL_OUTPUT_DIRECTORY",
        "AUTHORIZATION_TRANSPORT_CONTRACT",
        "resolve_authorization_control_output",
        "require_execution_authorization",
        "GOVERNED_ROOT_EXACT_FLAT_V1",
    ):
        if token in source:
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_STALE_TRANSPORT_RETAINED",
                f"transaction-bound runtime retained stale transport token: {token}",
            )

    for name in (
        "observe_structured_response",
        "run_structured_request",
        "decide_p5",
        "decide_p6",
    ):
        if _function_ast(predecessor, name) != _function_ast(source, name):
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_MECHANISM_SEMANTIC_DRIFT",
                f"transaction-bound transform changed frozen mechanism function: {name}",
            )

    required_tokens = (
        '"model_requests": 6',
        '"model_loads": 3',
        '"worker_starts": 3',
        "SemanticState.EXACT_MATCH",
        'if finish_reason != "stop":',
        '"raw_output_logged": False',
        '"authorization_specific_kaggle_inputs": 0',
        '"--copies"',
        'failure["secondary_scratch_cleanup_failure"] = True',
    )
    for token in required_tokens:
        if token not in source:
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_MECHANISM_CONTRACT_DRIFT",
                f"transaction-bound runtime contract token missing: {token}",
            )

    compile(source, RUNTIME_PAYLOAD_PATH.as_posix(), "exec")
    return source.encode("utf-8")


def _static_review(root: Path, runtime_payload: bytes) -> dict[str, object]:
    _validate_reconciliation(root)
    _validate_lifecycle_reconciliation(root)
    _validate_behavior_authorities(root)
    return {
        "schema_version": "1.0.0",
        "review_id": (
            "auragateway-p5-p6-mechanism-admission-transaction-bound-authorization-v1-review"
        ),
        "status": "APPROVED_STATIC_TRANSACTION_BOUND_IMPLEMENTATION",
        "base_main_commit": BASE_MAIN_COMMIT,
        "reconciliation_record_sha256": RECONCILIATION_RECORD_SHA256,
        "reconciliation_review_sha256": RECONCILIATION_REVIEW_SHA256,
        "behavior_implementation_merge_commit": BEHAVIOR_IMPLEMENTATION_MERGE_COMMIT,
        "behavior_source_sha256": BEHAVIOR_SOURCE_SHA256,
        "behavior_template_sha256": BEHAVIOR_TEMPLATE_SHA256,
        "behavior_implementation_review_sha256": BEHAVIOR_REVIEW_SHA256,
        "runtime_payload_sha256": _sha256(runtime_payload),
        "source_sha256": _sha256(_read_required(root, SOURCE_PATH)),
        "generator_contract_sha256": _sha256(_read_required(root, TEMPLATE_PATH)),
        "test_sha256": _sha256(_read_required(root, TEST_PATH)),
        "report_sha256": _sha256(_read_required(root, REPORT_PATH)),
        "runbook_sha256": _sha256(_read_required(root, RUNBOOK_PATH)),
        "authorization_scope": AUTHORIZATION_SCOPE,
        "authorization_architecture": "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "operator_confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "transaction_id_derivation": "SHA256_CANONICAL_AUTHORIZATION_BYTES",
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_authorization_filename_discovery_permitted": False,
        "fresh_post_artifact_observation_required": True,
        "platform_observation_receipt_runtime_input": False,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "maximum_hidden_retries": 0,
        "mechanism_semantics_preserved": True,
        "target_runtime_venv_copies_enforced": True,
        "cleanup_primary_failure_preserved": True,
        "pre_remediation_runtime_payload_sha256": PRE_REMEDIATION_RUNTIME_PAYLOAD_SHA256,
        "lifecycle_reconciliation_git_blob": LIFECYCLE_RECONCILIATION_GIT_BLOB,
        "p5_acceptance_relaxed": False,
        "p6_acceptance_relaxed": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _static_record(
    runtime_payload: bytes,
    review_bytes: bytes,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_id": ("auragateway-p5-p6-mechanism-admission-transaction-bound-authorization-v1"),
        "status": "IMPLEMENTED_NOT_ISSUED",
        "base_main_commit": BASE_MAIN_COMMIT,
        "review_sha256": _sha256(review_bytes),
        "source_path": SOURCE_PATH.as_posix(),
        "template_path": TEMPLATE_PATH.as_posix(),
        "runtime_payload_path": RUNTIME_PAYLOAD_PATH.as_posix(),
        "runtime_payload_sha256": _sha256(runtime_payload),
        "authorization_scope": AUTHORIZATION_SCOPE,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_authorization_filename_discovery_permitted": False,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "maximum_hidden_retries": 0,
        "mechanism_semantics_preserved": True,
        "target_runtime_venv_copies_enforced": True,
        "cleanup_primary_failure_preserved": True,
        "pre_remediation_runtime_payload_sha256": PRE_REMEDIATION_RUNTIME_PAYLOAD_SHA256,
        "lifecycle_reconciliation_git_blob": LIFECYCLE_RECONCILIATION_GIT_BLOB,
        "p5_requalified": False,
        "p6_requalified": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
        "platform_observation_persisted": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "runtime_anti_replay_established": False,
        "next_gate": NEXT_GATE,
    }


def generated_payloads(root: Path) -> dict[Path, bytes]:
    runtime_payload = build_runtime_payload(root)
    review_bytes = _artifact_json_bytes(_static_review(root, runtime_payload))
    record_bytes = _artifact_json_bytes(_static_record(runtime_payload, review_bytes))
    return {
        RUNTIME_PAYLOAD_PATH: runtime_payload,
        REVIEW_PATH: review_bytes,
        RECORD_PATH: record_bytes,
    }


def generate_static(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_base_ancestor(root)
    outputs = generated_payloads(root)
    for relative, payload in outputs.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_GENERATED",
        "candidate_path_count": len(CANDIDATE_PATHS),
        "generated_path_count": len(outputs),
        "runtime_payload_sha256": _sha256(outputs[RUNTIME_PAYLOAD_PATH]),
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def validate_static(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_base_ancestor(root)
    outputs = generated_payloads(root)
    for relative, expected in outputs.items():
        if _read_required(root, relative) != expected:
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_GENERATED_ARTIFACT_DRIFT",
                "generated transaction-bound artifact is non-canonical",
                relative.as_posix(),
            )
    for relative in (
        LIVE_AUTHORIZATION_PATH,
        LIVE_MANIFEST_PATH,
        PLATFORM_OBSERVATION_PATH,
        TERMINAL_RECEIPT_PATH,
    ):
        if (root / relative).exists():
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_LIVE_LIFECYCLE_PRESENT",
                "static validation requires no current live lifecycle artifact",
                relative.as_posix(),
            )
    if len(CANDIDATE_PATHS) != 8:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_CANDIDATE_BOUNDARY_DRIFT",
            "transaction-bound implementation candidate must contain eight paths",
        )
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_VALID",
        "candidate_path_count": len(CANDIDATE_PATHS),
        "generated_path_count": len(GENERATED_PATHS),
        "runtime_payload_sha256": _sha256(outputs[RUNTIME_PAYLOAD_PATH]),
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "mechanism_semantics_preserved": True,
        "target_runtime_venv_copies_enforced": True,
        "cleanup_primary_failure_preserved": True,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _require_merged_clean_main(root: Path) -> tuple[str, str]:
    branch = _require_git(root, "branch", "--show-current")
    if branch != "main":
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_NOT_ON_MAIN",
            "live authorization requires synchronized main",
        )
    head = _require_git(root, "rev-parse", "HEAD")
    origin_main = _require_git(root, "rev-parse", "origin/main")
    if head != origin_main:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_MAIN_NOT_SYNCHRONIZED",
            "HEAD must equal origin/main before live authorization",
        )
    tracked = _require_git(root, "status", "--porcelain=v1", "--untracked-files=no")
    if tracked:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_TRACKED_REPOSITORY_NOT_CLEAN",
            "tracked repository state must be clean before live authorization",
        )
    untracked_raw = _require_git(root, "ls-files", "--others", "--exclude-standard")
    observed_untracked = tuple(sorted(line for line in untracked_raw.splitlines() if line))
    expected_untracked = tuple(sorted(HISTORICAL_UNTRACKED_PATHS))
    if observed_untracked != expected_untracked:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_UNTRACKED_CUSTODY_DRIFT",
            "preissuance untracked inventory must equal historical evidence allowlist",
        )

    code, _, _ = _git(root, "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, head)
    if code != 0:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_RECONCILIATION_NOT_MERGED",
            "authorization reconciliation is not contained in current main",
        )

    issuer_merge_commit = _require_git(
        root,
        "log",
        "--first-parent",
        "--format=%H",
        "--max-count=1",
        "--",
        SOURCE_PATH.as_posix(),
    )
    if re.fullmatch(r"[0-9a-f]{40}", issuer_merge_commit) is None:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_ISSUER_NOT_MERGED",
            "unable to resolve issuer merge commit on main",
        )
    governed_paths = (SOURCE_PATH, TEMPLATE_PATH, RUNTIME_PAYLOAD_PATH, REVIEW_PATH, RECORD_PATH)
    code, _, _ = _git(
        root,
        "diff",
        "--quiet",
        issuer_merge_commit,
        "HEAD",
        "--",
        *(path.as_posix() for path in governed_paths),
    )
    if code != 0:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_ISSUER_POSTMERGE_DRIFT",
            "issuer identities changed after issuer merge",
        )
    return head, issuer_merge_commit


def build_intent(
    root: Path,
    issuer_merge_commit: str,
    *,
    prepared_at: datetime,
    window_minutes: int,
    intent_id: str,
) -> AuthorizationIntent:
    runtime_payload = _read_required(root, RUNTIME_PAYLOAD_PATH)
    return AuthorizationIntent(
        intent_id=intent_id,
        prepared_at=prepared_at,
        authorization_window_minutes=window_minutes,
        issuer_merge_commit=issuer_merge_commit,
        issuer_source_sha256=_sha256(_read_required(root, SOURCE_PATH)),
        generator_contract_sha256=_sha256(_read_required(root, TEMPLATE_PATH)),
        runtime_payload_sha256=_sha256(runtime_payload),
        runtime=RuntimeModelContract(),
        budget=ExecutionBudget(),
        mechanism=MechanismContract(),
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
    expected_challenge = authorization_challenge(intent)
    if challenge != expected_challenge:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_CHALLENGE_DRIFT",
            "authorization challenge does not bind exact intent",
        )
    confirmed = _normalize_time(confirmed_at, "confirmed_at")
    if confirmed < intent.prepared_at:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_CONFIRMATION_TIME_INVALID",
            "operator confirmation precedes authorization intent",
        )
    maximum_confirmation_age = timedelta(minutes=MAX_CONFIRMATION_AGE_MINUTES)
    if confirmed - intent.prepared_at > maximum_confirmation_age:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_CONFIRMATION_STALE",
            "operator confirmation exceeded freshness window",
        )
    body = AuthorizationBody(
        authorization_id="p5p6mech-" + intent.intent_id,
        authorization_challenge_sha256=challenge,
        operator_confirmed_at=confirmed,
        issued_at=confirmed,
        expires_at=confirmed + timedelta(minutes=intent.authorization_window_minutes),
        authorization_window_minutes=intent.authorization_window_minutes,
        issuer_merge_commit=intent.issuer_merge_commit,
        issuer_source_sha256=intent.issuer_source_sha256,
        generator_contract_sha256=intent.generator_contract_sha256,
        runtime_payload_sha256=intent.runtime_payload_sha256,
        runtime=RuntimeModelContract(),
        budget=ExecutionBudget(),
        mechanism=MechanismContract(),
        required_platform=RequiredPlatform(),
    )
    transaction_id = _sha256(_canonical_json_bytes(body))
    authorization = ExecutionAuthorization(
        transaction_id=transaction_id,
        authorization=body,
    )
    return authorization, _canonical_json_bytes(authorization)


def _render_wrapper(
    root: Path,
    authorization: ExecutionAuthorization,
    authorization_bytes: bytes,
) -> tuple[bytes, str]:
    template = _read_required(root, TEMPLATE_PATH).decode("utf-8")
    runtime_payload = _read_required(root, RUNTIME_PAYLOAD_PATH)
    replacements = {
        "__AUTHORIZATION_B64__": base64.b64encode(authorization_bytes).decode("ascii"),
        "__RUNTIME_PAYLOAD_B64__": base64.b64encode(runtime_payload).decode("ascii"),
        "__TRANSACTION_ID__": authorization.transaction_id,
        "__ISSUER_MERGE_COMMIT__": authorization.authorization.issuer_merge_commit,
        "__ISSUER_SOURCE_SHA256__": authorization.authorization.issuer_source_sha256,
        "__RUNTIME_PAYLOAD_SHA256__": authorization.authorization.runtime_payload_sha256,
        "__GENERATOR_CONTRACT_SHA256__": (authorization.authorization.generator_contract_sha256),
    }
    rendered = template
    for marker, value in replacements.items():
        if rendered.count(marker) != 1:
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_WRAPPER_MARKER_DRIFT",
                f"wrapper marker cardinality drifted: {marker}",
                TEMPLATE_PATH.as_posix(),
            )
        rendered = rendered.replace(marker, value, 1)
    if re.search(r"__[A-Z0-9_]+__", rendered) is not None:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_WRAPPER_RENDER_INCOMPLETE",
            "wrapper rendering left unresolved markers",
        )
    payload = rendered.encode("utf-8")
    compile(payload, "<p5-p6-mechanism-transaction-bound-wrapper>", "exec")
    return payload, _sha256(payload)


def _notebook_bytes(wrapper_payload: bytes) -> bytes:
    source = wrapper_payload.decode("utf-8").splitlines(keepends=True)
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
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
            "auragateway": {
                "notebook_name": NOTEBOOK_NAME,
                "authorization_specific_kaggle_inputs": 0,
                "authorization_producer_notebooks": 0,
                "manual_confirmation_json_files": 0,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return _artifact_json_bytes(notebook)


def authorize_generate(
    root: Path,
    output: Path,
    *,
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    if not 1 <= window_minutes <= MAX_WINDOW_MINUTES:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_WINDOW_INVALID",
            "authorization window is outside governed bounds",
        )
    _, issuer_merge_commit = _require_merged_clean_main(root)
    validate_static(root)
    for relative in (
        LIVE_AUTHORIZATION_PATH,
        LIVE_MANIFEST_PATH,
        PLATFORM_OBSERVATION_PATH,
        TERMINAL_RECEIPT_PATH,
    ):
        if (root / relative).exists():
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_LIVE_LIFECYCLE_PRESENT",
                "fresh issuance requires no current live lifecycle artifact",
                relative.as_posix(),
            )
    if output.exists():
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_OUTPUT_ALREADY_EXISTS",
            "governed notebook output already exists",
            str(output),
        )

    prepared_at = datetime.now(UTC)
    intent = build_intent(
        root,
        issuer_merge_commit,
        prepared_at=prepared_at,
        window_minutes=window_minutes,
        intent_id=secrets.token_hex(16),
    )
    challenge = authorization_challenge(intent)
    print("")
    print("=== FRESH HUMAN AUTHORIZATION REQUIRED ===")
    print("Retype this exact dynamic SHA-256 challenge:")
    print(challenge)
    confirmation = input("CONFIRMATION> ").strip()
    if confirmation != challenge:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_HUMAN_CONFIRMATION_MISMATCH",
            "operator confirmation did not exactly match dynamic challenge",
        )

    authorization, authorization_bytes = build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=datetime.now(UTC),
    )
    wrapper_payload, wrapper_sha = _render_wrapper(root, authorization, authorization_bytes)
    notebook_bytes = _notebook_bytes(wrapper_payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(notebook_bytes)

    live_authorization_path = root / LIVE_AUTHORIZATION_PATH
    live_authorization_path.parent.mkdir(parents=True, exist_ok=True)
    live_authorization_path.write_bytes(_artifact_json_bytes(authorization))
    manifest = ExecutionArtifactManifest(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(authorization_bytes),
        issuer_merge_commit=issuer_merge_commit,
        issuer_source_sha256=authorization.authorization.issuer_source_sha256,
        runtime_payload_sha256=authorization.authorization.runtime_payload_sha256,
        generator_contract_sha256=authorization.authorization.generator_contract_sha256,
        executable_payload_sha256=wrapper_sha,
        notebook_container_sha256=_sha256(notebook_bytes),
    )
    (root / LIVE_MANIFEST_PATH).write_bytes(_artifact_json_bytes(manifest))
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_EXECUTABLE_GENERATED",
        "transaction_id": authorization.transaction_id,
        "authorization_sha256": _sha256(authorization_bytes),
        "issuer_merge_commit": issuer_merge_commit,
        "runtime_payload_sha256": authorization.authorization.runtime_payload_sha256,
        "executable_payload_sha256": wrapper_sha,
        "notebook_container_sha256": _sha256(notebook_bytes),
        "notebook_path": str(output),
        "notebook_name": NOTEBOOK_NAME,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "platform_observation_persisted": False,
        "runtime_execution_authorized": True,
        "authorization_reusable": False,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }


def record_platform_observation(
    root: Path,
    *,
    observed_at: datetime,
) -> dict[str, object]:
    root = root.resolve()
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_ALREADY_TERMINAL",
            "terminal authority cannot accept a platform observation",
        )
    if (root / PLATFORM_OBSERVATION_PATH).exists():
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_PLATFORM_OBSERVATION_ALREADY_EXISTS",
            "platform observation is single-write",
        )
    authorization_bytes = _read_required(root, LIVE_AUTHORIZATION_PATH)
    manifest_bytes = _read_required(root, LIVE_MANIFEST_PATH)
    authorization = ExecutionAuthorization.model_validate_json(authorization_bytes)
    manifest = ExecutionArtifactManifest.model_validate_json(manifest_bytes)
    canonical_authorization = _canonical_json_bytes(authorization)
    if manifest.transaction_id != authorization.transaction_id:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_PLATFORM_TRANSACTION_DRIFT",
            "live manifest transaction identity drifted",
        )
    if _sha256(canonical_authorization) != manifest.authorization_sha256:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_PLATFORM_AUTHORIZATION_DRIFT",
            "live manifest no longer binds live authorization",
        )
    observed = _normalize_time(observed_at, "platform_observed_at")
    if observed < authorization.authorization.issued_at:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_PLATFORM_OBSERVATION_TIME_INVALID",
            "platform observation predates authorization issuance",
        )
    receipt = PlatformObservationReceipt(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(canonical_authorization),
        manifest_sha256=_sha256(manifest_bytes),
        platform_observed_at=observed,
    )
    receipt_bytes = _artifact_json_bytes(receipt)
    (root / PLATFORM_OBSERVATION_PATH).write_bytes(receipt_bytes)
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_DURABLE_PLATFORM_OBSERVATION_PERSISTED",
        "transaction_id": receipt.transaction_id,
        "receipt_sha256": _sha256(receipt_bytes),
        "accelerator": receipt.accelerator,
        "allocated_gpu_count": receipt.allocated_gpu_count,
        "internet_enabled": receipt.internet_enabled,
        "persisted_before_save_and_run_all": True,
        "runtime_execution_authorized": True,
        "authorization_reusable": False,
        "next_gate": NEXT_GATE_AFTER_OBSERVATION,
    }


def terminalize(
    root: Path,
    *,
    disposition: TerminalDisposition,
    execution_outcome: ExecutionOutcome | None,
    saved_version_id: int | None,
    evidence_zip_sha256: str | None,
    terminal_log_sha256: str | None,
) -> dict[str, object]:
    root = root.resolve()
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_ALREADY_TERMINAL",
            "authorization terminal receipt already exists",
        )
    authorization_bytes = _read_required(root, LIVE_AUTHORIZATION_PATH)
    manifest_bytes = _read_required(root, LIVE_MANIFEST_PATH)
    authorization = ExecutionAuthorization.model_validate_json(authorization_bytes)
    manifest = ExecutionArtifactManifest.model_validate_json(manifest_bytes)
    canonical_authorization = _canonical_json_bytes(authorization)
    if _sha256(canonical_authorization) != manifest.authorization_sha256:
        raise AuthorizationIssuerError(
            "P5_P6_TX_AUTH_LIFECYCLE_IDENTITY_DRIFT",
            "live manifest no longer binds live authorization",
        )

    platform_sha: str | None = None
    if (root / PLATFORM_OBSERVATION_PATH).is_file():
        platform_bytes = _read_required(root, PLATFORM_OBSERVATION_PATH)
        platform = PlatformObservationReceipt.model_validate_json(platform_bytes)
        if platform.transaction_id != authorization.transaction_id:
            raise AuthorizationIssuerError(
                "P5_P6_TX_AUTH_PLATFORM_TRANSACTION_DRIFT",
                "platform observation transaction identity drifted",
            )
        platform_sha = _sha256(platform_bytes)

    unused = disposition in {
        TerminalDisposition.EXPIRED_UNUSED,
        TerminalDisposition.CANCELLED_UNUSED,
        TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
    }
    receipt = TerminalReceipt(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(canonical_authorization),
        manifest_sha256=_sha256(manifest_bytes),
        disposition=disposition,
        execution_attempted=not unused,
        execution_outcome=execution_outcome,
        terminalized_at=datetime.now(UTC),
        saved_version_id=saved_version_id,
        platform_observation_receipt_sha256=platform_sha,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
    )
    (root / TERMINAL_RECEIPT_PATH).write_bytes(_artifact_json_bytes(receipt))
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_EXECUTION_AUTHORIZATION_TERMINAL",
        "transaction_id": receipt.transaction_id,
        "disposition": receipt.disposition.value,
        "execution_attempted": receipt.execution_attempted,
        "execution_outcome": (
            None if receipt.execution_outcome is None else receipt.execution_outcome.value
        ),
        "platform_observation_receipt_bound": platform_sha is not None,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "repository_acceptance_established": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }


def _default_output() -> Path:
    return Path.home() / "Desktop" / f"{NOTEBOOK_NAME}.ipynb"


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "generate",
            "validate",
            "authorize-generate",
            "record-platform-observation",
            "terminalize",
        ),
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--window-minutes", type=int, default=DEFAULT_WINDOW_MINUTES)
    parser.add_argument("--platform-observed-at")
    parser.add_argument(
        "--disposition",
        choices=tuple(item.value for item in TerminalDisposition),
    )
    parser.add_argument(
        "--execution-outcome",
        choices=tuple(item.value for item in ExecutionOutcome),
    )
    parser.add_argument("--saved-version-id", type=int)
    parser.add_argument("--evidence-zip-sha256")
    parser.add_argument("--terminal-log-sha256")
    return parser


def _print_error(error: AuthorizationIssuerError) -> None:
    print(
        _canonical_json_bytes(
            {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path,
            }
        ).decode("utf-8"),
        file=sys.stderr,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        result: dict[str, object]
        if args.command == "generate":
            result = generate_static(root)
        elif args.command == "validate":
            result = validate_static(root)
        elif args.command == "authorize-generate":
            output = Path(args.output).resolve() if args.output else _default_output()
            result = authorize_generate(root, output, window_minutes=args.window_minutes)
        elif args.command == "record-platform-observation":
            if args.platform_observed_at is None:
                raise AuthorizationIssuerError(
                    "P5_P6_TX_AUTH_ARGUMENT_MISSING",
                    "--platform-observed-at is required",
                )
            result = record_platform_observation(
                root,
                observed_at=datetime.fromisoformat(args.platform_observed_at),
            )
        else:
            if args.disposition is None:
                raise AuthorizationIssuerError(
                    "P5_P6_TX_AUTH_ARGUMENT_MISSING",
                    "--disposition is required",
                )
            result = terminalize(
                root,
                disposition=TerminalDisposition(args.disposition),
                execution_outcome=(
                    None
                    if args.execution_outcome is None
                    else ExecutionOutcome(args.execution_outcome)
                ),
                saved_version_id=args.saved_version_id,
                evidence_zip_sha256=args.evidence_zip_sha256,
                terminal_log_sha256=args.terminal_log_sha256,
            )
    except (
        AuthorizationIssuerError,
        ValidationError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, AuthorizationIssuerError):
            _print_error(error)
        else:
            _print_error(
                AuthorizationIssuerError(
                    "P5_P6_TX_AUTH_VALIDATION_FAILED",
                    str(error),
                )
            )
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
