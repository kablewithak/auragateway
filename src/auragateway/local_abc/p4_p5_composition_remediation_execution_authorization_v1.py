"""P4/P5 composition-remediation transaction-bound execution authorization V1.

Static generation and validation are inert. Live authority can only be issued
from synchronized clean main after this issuer has been merged and after the
operator exactly retypes a fresh dynamic SHA-256 challenge.

The issuer also persists the required post-artifact platform observation before
the operator may proceed to the single Save & Run All. This module does not
execute Kaggle itself.
"""

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
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

DESIGN_MERGE_COMMIT: Final = "788305abee1f7f4bae2d61d88009cf3f3a5f33a9"
IMPLEMENTATION_MERGE_COMMIT: Final = "f5701274037162ab9ff8f0627a544ac76d9c1b7b"
DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_execution_authorization_design_v1.json"
)
DESIGN_RECORD_SHA256: Final = "8eefe8e9d343fc20fcab4b868d623f546478787c0e57b32b836f6b879f7265b4"
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_implementation_v1_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "feecd56b5688bffb2a79369bd28f351756c8ae78f3f1c4c38dfd9365831eb76c"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_implementation_v1.json"
)
IMPLEMENTATION_RECORD_SHA256: Final = (
    "681b0463488f50d48c43b2256a0a50f0f276f10cc46c479db65c0c6e385970f8"
)
SUCCESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py"
)
SUCCESSOR_RUNTIME_SHA256: Final = "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_remediation_execution_authorization_v1.py"
)
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p4_p5_composition_remediation_transaction_bound_wrapper_v1.py.tmpl"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_p5_composition_remediation_execution_authorization_v1.py"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_P5_Composition_Remediation_Execution_Authorization_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p4_p5_composition_remediation_execution_authorization_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_execution_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_execution_authorization_v1_record.json"
)
LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_execution_authorization_v1_live.json"
)
LIVE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_execution_artifact_v1_live_manifest.json"
)
PLATFORM_OBSERVATION_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_platform_observation_v1_live.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_execution_authorization_v1_terminal.json"
)

AUTHORIZATION_SCOPE: Final = "P4_P5_COMPOSITION_REMEDIATION_CONFIRMATION_V1"
DEFAULT_WINDOW_MINUTES: Final = 180
MAX_WINDOW_MINUTES: Final = 240
MAX_CONFIRMATION_AGE_MINUTES: Final = 15
PLATFORM_CONTROL_ID: Final = "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
NEXT_GATE: Final = "MERGE_THEN_ISSUE_FRESH_P4_P5_COMPOSITION_REMEDIATION_EXECUTION_AUTHORIZATION_V1"
NEXT_GATE_AFTER_ISSUE: Final = "PERSIST_DURABLE_PLATFORM_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
NEXT_GATE_AFTER_OBSERVATION: Final = "ONE_SAVE_AND_RUN_ALL_FULL_REMEDIATED_P5_P6_CONFIRMATION"
NEXT_GATE_AFTER_TERMINAL: Final = "PRESERVE_AND_CLASSIFY_REMEDIATED_P5_P6_CONFIRMATION_EVIDENCE_V1"


class AuthorizationIssuerError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationIssuerError("P4_P5_REMEDIATION_AUTHORIZATION_ARGUMENT_ERROR", message)


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
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_save_and_run_all_actions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
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
    external_network_access_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False


class QualificationContract(FrozenModel):
    structured_request_roles: tuple[str, ...] = (
        "BASE_COLD",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    )
    structured_request_count: Literal[6] = 6
    all_structured_requests_exact_object_required: Literal[True] = True
    p5_state_required: Literal["PASS"] = "PASS"
    p6_state_required: Literal["PASS"] = "PASS"
    cache_specific_proof_required: Literal[True] = True
    p6_isolation_proof_required: Literal[True] = True
    prefix_a_token_identity_stability_required: Literal[True] = True
    negative_prefix_token_identity_divergence_required: Literal[True] = True
    base_warm_attributable_cache_reuse_required: Literal[True] = True
    post_reset_cold_state_required: Literal[True] = True
    cross_worker_no_cache_inheritance_required: Literal[True] = True
    worker1_retention_required: Literal[True] = True
    exact_action_budget_required: Literal[True] = True
    teardown_state_required: Literal["PASSED"] = "PASSED"
    scratch_cleanup_state_required: Literal["PASSED"] = "PASSED"
    pre_request_token_identity_journal_required: Literal[True] = True
    standalone_a_r_differential_required: Literal[False] = False
    case_c_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_roles(self) -> Self:
        if len(self.structured_request_roles) != self.structured_request_count:
            raise ValueError("structured request role count drifted")
        if len(set(self.structured_request_roles)) != self.structured_request_count:
            raise ValueError("structured request roles must remain unique")
        return self


class AuthorizationIntent(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    intent_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    scope: Literal["P4_P5_COMPOSITION_REMEDIATION_CONFIRMATION_V1"]
    prepared_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=MAX_WINDOW_MINUTES)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_record_sha256: Literal[
        "8eefe8e9d343fc20fcab4b868d623f546478787c0e57b32b836f6b879f7265b4"
    ]
    implementation_merge_commit: Literal["f5701274037162ab9ff8f0627a544ac76d9c1b7b"]
    implementation_review_sha256: Literal[
        "feecd56b5688bffb2a79369bd28f351756c8ae78f3f1c4c38dfd9365831eb76c"
    ]
    implementation_record_sha256: Literal[
        "681b0463488f50d48c43b2256a0a50f0f276f10cc46c479db65c0c6e385970f8"
    ]
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
    ]
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    qualification: QualificationContract
    required_platform: RequiredPlatform
    platform_observation_control_id: Literal[
        "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    ] = PLATFORM_CONTROL_ID

    @field_validator("prepared_at")
    @classmethod
    def normalize_prepared_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "prepared_at")


class AuthorizationBody(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str = Field(pattern=r"^p4p5r-[0-9a-f]{32}$")
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle: Literal["ISSUED"] = "ISSUED"
    scope: Literal["P4_P5_COMPOSITION_REMEDIATION_CONFIRMATION_V1"]
    authorization_challenge_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_confirmation_method: Literal["RETYPE_DYNAMIC_SHA256_CHALLENGE"]
    operator_confirmation_recorded: Literal[True]
    operator_confirmed_at: datetime
    issued_at: datetime
    expires_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=MAX_WINDOW_MINUTES)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_record_sha256: Literal[
        "8eefe8e9d343fc20fcab4b868d623f546478787c0e57b32b836f6b879f7265b4"
    ]
    implementation_merge_commit: Literal["f5701274037162ab9ff8f0627a544ac76d9c1b7b"]
    implementation_review_sha256: Literal[
        "feecd56b5688bffb2a79369bd28f351756c8ae78f3f1c4c38dfd9365831eb76c"
    ]
    implementation_record_sha256: Literal[
        "681b0463488f50d48c43b2256a0a50f0f276f10cc46c479db65c0c6e385970f8"
    ]
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
    ]
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    qualification: QualificationContract
    required_platform: RequiredPlatform
    platform_observation_control_id: Literal[
        "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    ] = PLATFORM_CONTROL_ID
    durable_platform_observation_required: Literal[True] = True
    runtime_execution_authorized: Literal[True] = True
    single_use: Literal[True] = True
    every_terminal_attempt_consumes_authorization: Literal[True] = True
    unchanged_replay_authorized: Literal[False] = False
    authorization_reusable: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False
    case_c_authorized: Literal[False] = False

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
    status: Literal["TRANSACTION_BOUND_EXECUTABLE_GENERATED"]
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_record_sha256: Literal[
        "8eefe8e9d343fc20fcab4b868d623f546478787c0e57b32b836f6b879f7265b4"
    ]
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
    ]
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    executable_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_container_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_container_is_semantic_payload_identity: Literal[False] = False
    authorization_specific_kaggle_inputs: Literal[0] = 0
    authorization_producer_notebooks: Literal[0] = 0
    manual_confirmation_json_files: Literal[0] = 0
    permitted_kaggle_input_roles: tuple[Literal["durable_runtime"], Literal["model_snapshot"]]
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
    platform_observation_receipt_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
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
        if self.disposition in unused:
            if (
                self.execution_attempted
                or self.execution_outcome is not None
                or self.saved_version_id is not None
            ):
                raise ValueError("unused disposition contains execution evidence")
            return self
        if not self.execution_attempted:
            raise ValueError("attempted disposition requires execution_attempted")
        if self.saved_version_id is None:
            raise ValueError("attempted disposition requires saved version identity")
        if self.disposition == TerminalDisposition.CONSUMED and self.execution_outcome is None:
            raise ValueError("CONSUMED disposition requires execution outcome")
        if (
            self.disposition == TerminalDisposition.OUTCOME_UNKNOWN
            and self.execution_outcome is not None
        ):
            raise ValueError("OUTCOME_UNKNOWN must not fabricate execution outcome")
        if (
            self.execution_outcome == ExecutionOutcome.PASSED
            and self.platform_observation_receipt_sha256 is None
        ):
            raise ValueError("PASSED outcome requires durable platform observation receipt")
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
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_ARTIFACT_MISSING",
            "required artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _read_json_object(root: Path, relative: Path) -> dict[str, object]:
    parsed: object = json.loads(_read_required(root, relative))
    if not isinstance(parsed, dict):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_JSON_INVALID",
            "required JSON artifact must contain one object",
            relative.as_posix(),
        )
    return cast(dict[str, object], parsed)


def _git(root: Path, *arguments: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", *arguments], cwd=root, check=False, capture_output=True, text=True, encoding="utf-8"
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _require_git(root: Path, *arguments: str) -> str:
    code, stdout, _ = _git(root, *arguments)
    if code != 0:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_GIT_STATE_FAILED", "unable to inspect repository state"
        )
    return stdout


def _require_design_ancestor(root: Path) -> None:
    code, _, _ = _git(root, "merge-base", "--is-ancestor", DESIGN_MERGE_COMMIT, "HEAD")
    if code != 0:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_DESIGN_NOT_ANCESTOR",
            "merged authorization design is not an ancestor of HEAD",
        )


def _require_merged_clean_main(root: Path) -> str:
    branch = _require_git(root, "branch", "--show-current")
    if branch != "main":
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_NOT_ON_MAIN",
            "live authorization requires synchronized main",
        )
    head = _require_git(root, "rev-parse", "HEAD")
    origin_main = _require_git(root, "rev-parse", "origin/main")
    if head != origin_main:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "HEAD must equal origin/main before live authorization",
        )
    status = _require_git(root, "status", "--porcelain=v1", "-uall")
    if status:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
            "repository must be clean before live authorization",
        )
    code, _, _ = _git(root, "merge-base", "--is-ancestor", DESIGN_MERGE_COMMIT, head)
    if code != 0:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_DESIGN_NOT_MERGED",
            "authorization design is not contained in current main",
        )
    return head


def _verify_hash(root: Path, relative: Path, expected_sha256: str) -> bytes:
    payload = _read_required(root, relative)
    if _sha256(payload) != expected_sha256:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_IDENTITY_DRIFT",
            "bound authority identity drifted",
            relative.as_posix(),
        )
    return payload


def _validate_design(root: Path) -> None:
    payload = _verify_hash(root, DESIGN_RECORD_PATH, DESIGN_RECORD_SHA256)
    parsed: object = json.loads(payload)
    if not isinstance(parsed, dict):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_DESIGN_INVALID",
            "authorization design record must contain one object",
            DESIGN_RECORD_PATH.as_posix(),
        )
    record = cast(dict[str, object], parsed)
    required = {
        "status": "DESIGN_FROZEN_NOT_EXECUTED",
        "authorization_architecture": "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "authorization_scope": AUTHORIZATION_SCOPE,
        "implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
        "platform_observation_persisted": False,
    }
    drift = tuple(key for key, expected in required.items() if record.get(key) != expected)
    if drift:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_DESIGN_CONTRACT_DRIFT",
            "authorization design contract drifted: " + ",".join(drift),
            DESIGN_RECORD_PATH.as_posix(),
        )
    if record.get("execution_budget") != ExecutionBudget().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_BUDGET_DRIFT",
            "authorization design execution budget drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if record.get("runtime_model") != RuntimeModelContract().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_RUNTIME_CONTRACT_DRIFT",
            "authorization design runtime/model contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if record.get("qualification") != QualificationContract().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_QUALIFICATION_DRIFT",
            "authorization design qualification contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    observation = record.get("platform_observation_receipt")
    if not isinstance(observation, dict) or observation.get("control_id") != PLATFORM_CONTROL_ID:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_PLATFORM_CONTROL_DRIFT",
            "durable platform observation control drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if observation.get("durable_receipt_required") is not True:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_PLATFORM_CONTROL_DRIFT",
            "durable platform observation receipt requirement drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if observation.get("receipt_must_exist_before_save_and_run_all") is not True:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_PLATFORM_CONTROL_DRIFT",
            "platform observation ordering drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )


def _validate_implementation_authorities(root: Path) -> bytes:
    _verify_hash(root, IMPLEMENTATION_REVIEW_PATH, IMPLEMENTATION_REVIEW_SHA256)
    _verify_hash(root, IMPLEMENTATION_RECORD_PATH, IMPLEMENTATION_RECORD_SHA256)
    return _verify_hash(root, SUCCESSOR_RUNTIME_PATH, SUCCESSOR_RUNTIME_SHA256)


def _static_review(root: Path) -> dict[str, object]:
    _validate_design(root)
    _validate_implementation_authorities(root)
    source = _read_required(root, SOURCE_PATH)
    template = _read_required(root, TEMPLATE_PATH)
    test = _read_required(root, TEST_PATH)
    report = _read_required(root, REPORT_PATH)
    runbook = _read_required(root, RUNBOOK_PATH)
    return {
        "schema_version": "1.0.0",
        "review_id": "auragateway-p4-p5-composition-remediation-execution-authorization-v1-review",
        "status": "APPROVED_STATIC_ISSUER_IMPLEMENTATION",
        "design_merge_commit": DESIGN_MERGE_COMMIT,
        "design_record_sha256": DESIGN_RECORD_SHA256,
        "implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "implementation_review_sha256": IMPLEMENTATION_REVIEW_SHA256,
        "implementation_record_sha256": IMPLEMENTATION_RECORD_SHA256,
        "successor_runtime_sha256": SUCCESSOR_RUNTIME_SHA256,
        "source_sha256": _sha256(source),
        "generator_contract_sha256": _sha256(template),
        "test_sha256": _sha256(test),
        "report_sha256": _sha256(report),
        "runbook_sha256": _sha256(runbook),
        "authorization_scope": AUTHORIZATION_SCOPE,
        "authorization_architecture": "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "operator_confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "transaction_id_derivation": "SHA256_CANONICAL_AUTHORIZATION_BYTES",
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "maximum_hidden_retries": 0,
        "structured_request_count": 6,
        "p5_state_required": "PASS",
        "p6_state_required": "PASS",
        "durable_platform_observation_required": True,
        "platform_observation_control_id": PLATFORM_CONTROL_ID,
        "platform_observation_receipt_runtime_input": False,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_anti_replay_established": False,
        "case_c_authorized": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _static_record(root: Path, review_bytes: bytes) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_id": "auragateway-p4-p5-composition-remediation-execution-authorization-v1",
        "status": "IMPLEMENTED_NOT_ISSUED",
        "design_merge_commit": DESIGN_MERGE_COMMIT,
        "design_record_sha256": DESIGN_RECORD_SHA256,
        "implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "successor_runtime_sha256": SUCCESSOR_RUNTIME_SHA256,
        "review_sha256": _sha256(review_bytes),
        "source_path": SOURCE_PATH.as_posix(),
        "template_path": TEMPLATE_PATH.as_posix(),
        "authorization_scope": AUTHORIZATION_SCOPE,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "maximum_hidden_retries": 0,
        "structured_request_count": 6,
        "durable_platform_observation_required": True,
        "platform_observation_control_id": PLATFORM_CONTROL_ID,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_anti_replay_established": False,
        "case_c_authorized": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "platform_observation_persisted": False,
        "kaggle_execution_performed": False,
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
        "status": "P4_P5_REMEDIATION_AUTHORIZATION_STATIC_ARTIFACTS_GENERATED",
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "platform_observation_persisted": False,
        "next_gate": NEXT_GATE,
    }


def validate_static(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_design_ancestor(root)
    review_bytes = _artifact_json_bytes(_static_review(root))
    record_bytes = _artifact_json_bytes(_static_record(root, review_bytes))
    for relative, expected in ((REVIEW_PATH, review_bytes), (RECORD_PATH, record_bytes)):
        if _read_required(root, relative) != expected:
            raise AuthorizationIssuerError(
                "P4_P5_REMEDIATION_AUTHORIZATION_STATIC_ARTIFACT_DRIFT",
                "generated static issuer artifact drifted",
                relative.as_posix(),
            )
    for relative in (
        LIVE_AUTHORIZATION_PATH,
        LIVE_MANIFEST_PATH,
        PLATFORM_OBSERVATION_RECEIPT_PATH,
        TERMINAL_RECEIPT_PATH,
    ):
        if (root / relative).exists():
            raise AuthorizationIssuerError(
                "P4_P5_REMEDIATION_AUTHORIZATION_LIVE_LIFECYCLE_PRESENT",
                "static validation requires no live lifecycle artifact",
                relative.as_posix(),
            )
    return {
        "status": "P4_P5_REMEDIATION_EXECUTION_AUTHORIZATION_V1_VALID",
        "authorization_scope": AUTHORIZATION_SCOPE,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "maximum_hidden_retries": 0,
        "structured_request_count": 6,
        "durable_platform_observation_required": True,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "platform_observation_persisted": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def build_intent(
    root: Path,
    issuer_merge_commit: str,
    *,
    prepared_at: datetime,
    window_minutes: int,
    intent_id: str,
) -> AuthorizationIntent:
    root = root.resolve()
    _validate_design(root)
    runtime_payload = _validate_implementation_authorities(root)
    return AuthorizationIntent(
        intent_id=intent_id,
        scope=AUTHORIZATION_SCOPE,
        prepared_at=prepared_at,
        authorization_window_minutes=window_minutes,
        issuer_merge_commit=issuer_merge_commit,
        authorization_design_record_sha256=DESIGN_RECORD_SHA256,
        implementation_merge_commit=IMPLEMENTATION_MERGE_COMMIT,
        implementation_review_sha256=IMPLEMENTATION_REVIEW_SHA256,
        implementation_record_sha256=IMPLEMENTATION_RECORD_SHA256,
        issuer_source_sha256=_sha256(_read_required(root, SOURCE_PATH)),
        generator_contract_sha256=_sha256(_read_required(root, TEMPLATE_PATH)),
        runtime_payload_sha256=_sha256(runtime_payload),
        runtime=RuntimeModelContract(),
        budget=ExecutionBudget(),
        qualification=QualificationContract(),
        required_platform=RequiredPlatform(),
    )


def authorization_challenge(intent: AuthorizationIntent) -> str:
    return _sha256(_canonical_json_bytes(intent))


def build_authorization(
    intent: AuthorizationIntent, *, challenge: str, confirmed_at: datetime
) -> tuple[ExecutionAuthorization, bytes]:
    expected_challenge = authorization_challenge(intent)
    if challenge != expected_challenge:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_CHALLENGE_DRIFT",
            "authorization challenge does not bind exact intent",
        )
    confirmed = _normalize_time(confirmed_at, "confirmed_at")
    if confirmed < intent.prepared_at:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_CONFIRMATION_TIME_INVALID",
            "operator confirmation precedes authorization intent",
        )
    if confirmed - intent.prepared_at > timedelta(minutes=MAX_CONFIRMATION_AGE_MINUTES):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_CONFIRMATION_STALE",
            "operator confirmation exceeded freshness window",
        )
    body = AuthorizationBody(
        authorization_id="p4p5r-" + intent.intent_id,
        scope=AUTHORIZATION_SCOPE,
        authorization_challenge_sha256=challenge,
        operator_confirmation_method="RETYPE_DYNAMIC_SHA256_CHALLENGE",
        operator_confirmation_recorded=True,
        operator_confirmed_at=confirmed,
        issued_at=confirmed,
        expires_at=confirmed + timedelta(minutes=intent.authorization_window_minutes),
        authorization_window_minutes=intent.authorization_window_minutes,
        issuer_merge_commit=intent.issuer_merge_commit,
        authorization_design_record_sha256=intent.authorization_design_record_sha256,
        implementation_merge_commit=intent.implementation_merge_commit,
        implementation_review_sha256=intent.implementation_review_sha256,
        implementation_record_sha256=intent.implementation_record_sha256,
        issuer_source_sha256=intent.issuer_source_sha256,
        generator_contract_sha256=intent.generator_contract_sha256,
        runtime_payload_sha256=intent.runtime_payload_sha256,
        runtime=intent.runtime,
        budget=intent.budget,
        qualification=intent.qualification,
        required_platform=intent.required_platform,
    )
    transaction_id = _sha256(_canonical_json_bytes(body))
    authorization = ExecutionAuthorization(transaction_id=transaction_id, authorization=body)
    return authorization, _canonical_json_bytes(authorization)


def render_executable_payload(
    root: Path,
    authorization: ExecutionAuthorization,
    authorization_bytes: bytes,
    runtime_payload: bytes,
) -> bytes:
    template = _read_required(root, TEMPLATE_PATH)
    generator_sha = _sha256(template)
    issuer_source_sha = _sha256(_read_required(root, SOURCE_PATH))
    if authorization.authorization.generator_contract_sha256 != generator_sha:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_GENERATOR_DRIFT",
            "authorization does not bind current generator contract",
        )
    if authorization.authorization.issuer_source_sha256 != issuer_source_sha:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_ISSUER_SOURCE_DRIFT",
            "authorization does not bind current issuer source",
        )
    if authorization.authorization.runtime_payload_sha256 != _sha256(runtime_payload):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_RUNTIME_PAYLOAD_DRIFT",
            "authorization does not bind supplied runtime payload",
        )
    source = template.decode("utf-8")
    replacements = {
        "__AUTHORIZATION_B64__": base64.b64encode(authorization_bytes).decode("ascii"),
        "__RUNTIME_PAYLOAD_B64__": base64.b64encode(runtime_payload).decode("ascii"),
        "__TRANSACTION_ID__": authorization.transaction_id,
        "__ISSUER_MERGE_COMMIT__": authorization.authorization.issuer_merge_commit,
        "__ISSUER_SOURCE_SHA256__": issuer_source_sha,
        "__RUNTIME_PAYLOAD_SHA256__": authorization.authorization.runtime_payload_sha256,
        "__GENERATOR_CONTRACT_SHA256__": generator_sha,
    }
    for marker, value in replacements.items():
        if source.count(marker) != 1:
            raise AuthorizationIssuerError(
                "P4_P5_REMEDIATION_AUTHORIZATION_TEMPLATE_MARKER_DRIFT",
                "generator template marker cardinality drifted",
            )
        source = source.replace(marker, value)
    return source.encode("utf-8")


def build_notebook(executable_payload: bytes) -> bytes:
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": executable_payload.decode("utf-8").splitlines(keepends=True),
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
        issuer_merge_commit=authorization.authorization.issuer_merge_commit,
        authorization_design_record_sha256=authorization.authorization.authorization_design_record_sha256,
        issuer_source_sha256=authorization.authorization.issuer_source_sha256,
        runtime_payload_sha256=authorization.authorization.runtime_payload_sha256,
        generator_contract_sha256=authorization.authorization.generator_contract_sha256,
        executable_payload_sha256=_sha256(executable_payload),
        notebook_container_sha256=_sha256(notebook_bytes),
        permitted_kaggle_input_roles=("durable_runtime", "model_snapshot"),
    )


def authorize_generate(root: Path, output_path: Path, *, window_minutes: int) -> dict[str, object]:
    root = root.resolve()
    validate_static(root)
    issuer_commit = _require_merged_clean_main(root)
    for relative in (
        LIVE_AUTHORIZATION_PATH,
        LIVE_MANIFEST_PATH,
        PLATFORM_OBSERVATION_RECEIPT_PATH,
        TERMINAL_RECEIPT_PATH,
    ):
        if (root / relative).exists():
            raise AuthorizationIssuerError(
                "P4_P5_REMEDIATION_AUTHORIZATION_LIFECYCLE_EXISTS",
                "live transaction lifecycle already exists",
                relative.as_posix(),
            )
    runtime_payload = _validate_implementation_authorities(root)
    if output_path.exists():
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_OUTPUT_EXISTS",
            "generated notebook output already exists",
            str(output_path),
        )
    prepared = datetime.now(UTC)
    intent = build_intent(
        root,
        issuer_commit,
        prepared_at=prepared,
        window_minutes=window_minutes,
        intent_id=secrets.token_hex(16),
    )
    challenge = authorization_challenge(intent)
    print("authorization_challenge=" + challenge)
    print("scope=" + AUTHORIZATION_SCOPE)
    print("issuer_merge_commit=" + issuer_commit)
    print("authorization_design_record_sha256=" + DESIGN_RECORD_SHA256)
    print("runtime_payload_sha256=" + intent.runtime_payload_sha256)
    print("maximum_model_requests=6")
    print("maximum_worker_starts=3")
    print("maximum_model_loads=3")
    print("maximum_hidden_retries=0")
    print("structured_request_count=6")
    print("required_p5_state=PASS")
    print("required_p6_state=PASS")
    print("required_platform=T4_X2 / 2 GPUs / Internet Off")
    print("platform_observation_control=" + PLATFORM_CONTROL_ID)
    observed = input(
        "Retype the authorization challenge to authorize exactly one "
        "full remediated P5/P6 confirmation: "
    ).strip()
    if observed != challenge:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_CONFIRMATION_MISMATCH",
            "interactive authorization challenge did not match",
        )
    authorization, authorization_bytes = build_authorization(
        intent, challenge=challenge, confirmed_at=datetime.now(UTC)
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
        "status": "P4_P5_REMEDIATION_EXECUTION_ARTIFACT_AUTHORIZED_AND_GENERATED",
        "transaction_id": authorization.transaction_id,
        "authorization_sha256": _sha256(authorization_bytes),
        "issuer_merge_commit": issuer_commit,
        "runtime_payload_sha256": authorization.authorization.runtime_payload_sha256,
        "executable_payload_sha256": manifest.executable_payload_sha256,
        "notebook_container_sha256": manifest.notebook_container_sha256,
        "output_path": str(output_path),
        "platform_observation_persisted": False,
        "save_and_run_all_authorized_yet": False,
        "runtime_anti_replay_established": False,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }


def record_platform_observation(root: Path, *, observed_at: datetime) -> dict[str, object]:
    root = root.resolve()
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_ALREADY_TERMINAL",
            "transaction already has a terminal receipt",
        )
    if (root / PLATFORM_OBSERVATION_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_PLATFORM_OBSERVATION_ALREADY_PERSISTED",
            "durable platform observation receipt already exists",
            PLATFORM_OBSERVATION_RECEIPT_PATH.as_posix(),
        )
    authorization_bytes = _read_required(root, LIVE_AUTHORIZATION_PATH)
    manifest_bytes = _read_required(root, LIVE_MANIFEST_PATH)
    authorization = ExecutionAuthorization.model_validate_json(authorization_bytes)
    manifest = ExecutionArtifactManifest.model_validate_json(manifest_bytes)
    canonical_authorization = _canonical_json_bytes(authorization)
    if manifest.authorization_sha256 != _sha256(canonical_authorization):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_LIFECYCLE_IDENTITY_DRIFT",
            "live manifest no longer binds live authorization",
        )
    if manifest.transaction_id != authorization.transaction_id:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_TRANSACTION_DRIFT",
            "live manifest transaction identity drifted",
        )
    observed = _normalize_time(observed_at, "platform_observed_at")
    if observed < authorization.authorization.issued_at:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_PLATFORM_TIME_INVALID",
            "platform observation precedes authorization",
        )
    if observed >= authorization.authorization.expires_at:
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_PLATFORM_TIME_EXPIRED",
            "platform observation occurred outside authorization window",
        )
    receipt = PlatformObservationReceipt(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(canonical_authorization),
        manifest_sha256=_sha256(manifest_bytes),
        platform_observed_at=observed,
    )
    receipt_bytes = _artifact_json_bytes(receipt)
    (root / PLATFORM_OBSERVATION_RECEIPT_PATH).write_bytes(receipt_bytes)
    return {
        "status": "P4_P5_REMEDIATION_PLATFORM_OBSERVATION_PERSISTED",
        "transaction_id": receipt.transaction_id,
        "platform_observation_receipt_sha256": _sha256(receipt_bytes),
        "platform_observed_at": receipt.platform_observed_at.isoformat(),
        "accelerator": receipt.accelerator,
        "allocated_gpu_count": receipt.allocated_gpu_count,
        "internet_enabled": receipt.internet_enabled,
        "capability_source": receipt.capability_source,
        "persisted_before_save_and_run_all": True,
        "receipt_runtime_input": False,
        "save_and_run_all_authorized_yet": True,
        "next_gate": NEXT_GATE_AFTER_OBSERVATION,
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
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_AUTHORIZATION_ALREADY_TERMINAL",
            "transaction already has a terminal receipt",
        )
    authorization_bytes = _read_required(root, LIVE_AUTHORIZATION_PATH)
    manifest_bytes = _read_required(root, LIVE_MANIFEST_PATH)
    authorization = ExecutionAuthorization.model_validate_json(authorization_bytes)
    manifest = ExecutionArtifactManifest.model_validate_json(manifest_bytes)
    canonical_authorization = _canonical_json_bytes(authorization)
    if manifest.authorization_sha256 != _sha256(canonical_authorization):
        raise AuthorizationIssuerError(
            "P4_P5_REMEDIATION_LIFECYCLE_IDENTITY_DRIFT",
            "live manifest no longer binds live authorization",
        )
    platform_sha: str | None = None
    if (root / PLATFORM_OBSERVATION_RECEIPT_PATH).is_file():
        platform_bytes = _read_required(root, PLATFORM_OBSERVATION_RECEIPT_PATH)
        platform = PlatformObservationReceipt.model_validate_json(platform_bytes)
        if platform.transaction_id != authorization.transaction_id:
            raise AuthorizationIssuerError(
                "P4_P5_REMEDIATION_PLATFORM_TRANSACTION_DRIFT",
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
        execution_outcome=outcome,
        terminalized_at=datetime.now(UTC),
        saved_version_id=saved_version_id,
        platform_observation_receipt_sha256=platform_sha,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
    )
    (root / TERMINAL_RECEIPT_PATH).write_bytes(_artifact_json_bytes(receipt))
    return {
        "status": "P4_P5_REMEDIATION_EXECUTION_AUTHORIZATION_TERMINAL",
        "transaction_id": receipt.transaction_id,
        "disposition": receipt.disposition.value,
        "execution_attempted": receipt.execution_attempted,
        "platform_observation_receipt_bound": platform_sha is not None,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }


def _default_output() -> Path:
    return Path.home() / "Desktop" / "ag-p4-p5-remediation-p5-p6-confirmation-v1.ipynb"


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
    parser.add_argument("--disposition", choices=tuple(item.value for item in TerminalDisposition))
    parser.add_argument("--outcome", choices=tuple(item.value for item in ExecutionOutcome))
    parser.add_argument("--saved-version-id", type=int)
    parser.add_argument("--evidence-zip-sha256")
    parser.add_argument("--terminal-log-sha256")
    return parser


def _print_error(error: AuthorizationIssuerError) -> None:
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
        if args.command == "validate":
            result = validate_static(root)
        if args.command == "authorize-generate":
            output = Path(args.output).resolve() if args.output else _default_output()
            result = authorize_generate(root, output, window_minutes=args.window_minutes)
        if args.command == "record-platform-observation":
            if args.platform_observed_at is None:
                raise AuthorizationIssuerError(
                    "P4_P5_REMEDIATION_AUTHORIZATION_ARGUMENT_MISSING",
                    "--platform-observed-at is required",
                )
            result = record_platform_observation(
                root, observed_at=datetime.fromisoformat(args.platform_observed_at)
            )
        if args.command == "terminalize":
            if args.disposition is None:
                raise AuthorizationIssuerError(
                    "P4_P5_REMEDIATION_AUTHORIZATION_ARGUMENT_MISSING", "--disposition is required"
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
        AuthorizationIssuerError,
        ValidationError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, AuthorizationIssuerError):
            _print_error(error)
        if not isinstance(error, AuthorizationIssuerError):
            _print_error(
                AuthorizationIssuerError(
                    "P4_P5_REMEDIATION_AUTHORIZATION_VALIDATION_FAILED", str(error)
                )
            )
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
