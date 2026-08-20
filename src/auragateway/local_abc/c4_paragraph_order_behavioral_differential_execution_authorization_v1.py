"""C4 paragraph-order differential transaction-bound execution authorization issuer V1.

Static generation and validation are inert. Live authority can only be issued from
synchronized clean main after this issuer has been merged and after the operator
exactly retypes a fresh dynamic SHA-256 challenge.

The issuer persists the required post-artifact platform observation before the
operator may proceed to the single Save & Run All. This module never executes
Kaggle itself.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

DESIGN_MERGE_COMMIT: Final = "2e0e09b65023397f30d73a406f3f60e7090c85b1"
IMPLEMENTATION_MERGE_COMMIT: Final = "7e037596de1a74038583a85ed81d46ec12debbac"

DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "execution_authorization_design_v1.json"
)
DESIGN_RECORD_SHA256: Final = "8305ebb153f962015c28de98bd6fcf6feeb202482163c6cce3f0caf08cc3d143"
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_implementation_v1_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "355a6b7f7871e648d8bfaf4c7841e9e6346f9b59eba65ac98c00b55d940d2595"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_implementation_v1.json"
)
IMPLEMENTATION_RECORD_SHA256: Final = (
    "c563bf012c7ec587089b7b28af5074207a389c5fb7381b9c1213299d3b489386"
)
SUCCESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/c4_paragraph_order_behavioral_differential_runtime_v1.py"
)
SUCCESSOR_RUNTIME_SHA256: Final = "1d055dfab9f83a2706f5335b4529df98d45e45de5210a8c6c21c2b91e6a72df0"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "c4_paragraph_order_behavioral_differential_execution_authorization_v1.py"
)
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/"
    "c4_paragraph_order_behavioral_differential_transaction_bound_wrapper_v1.py.tmpl"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_c4_paragraph_order_behavioral_differential_execution_authorization_v1.py"
)
REPORT_PATH: Final = Path(
    "docs/reports/"
    "AuraGateway_C4_Paragraph_Order_Behavioral_Differential_Execution_Authorization_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/"
    "local_abc_c4_paragraph_order_behavioral_differential_execution_authorization_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "execution_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "execution_authorization_v1_record.json"
)
LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "execution_authorization_v1_live.json"
)
LIVE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "execution_artifact_v1_live_manifest.json"
)
PLATFORM_OBSERVATION_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "platform_observation_v1_live.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "execution_authorization_v1_terminal.json"
)

AUTHORIZATION_SCOPE: Final = "C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"
DEFAULT_WINDOW_MINUTES: Final = 180
MAX_WINDOW_MINUTES: Final = 240
MAX_CONFIRMATION_AGE_MINUTES: Final = 15
PLATFORM_CONTROL_ID: Final = "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"

NEXT_GATE: Final = (
    "MERGE_THEN_ISSUE_FRESH_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"
)
NEXT_GATE_AFTER_ISSUE: Final = "PERSIST_DURABLE_PLATFORM_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
NEXT_GATE_AFTER_OBSERVATION: Final = (
    "ONE_SAVE_AND_RUN_ALL_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"
)
NEXT_GATE_AFTER_TERMINAL: Final = (
    "PRESERVE_AND_CLASSIFY_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_EVIDENCE_V1"
)

CONTROL_CONDITION: Final = "CONTROL_ORIGINAL_C4"
TREATMENT_CONDITION: Final = "TREATMENT_REVERSED_MIDDLE_EIGHT"
REQUEST_ORDER: Final = (
    CONTROL_CONDITION,
    TREATMENT_CONDITION,
    TREATMENT_CONDITION,
    CONTROL_CONDITION,
    CONTROL_CONDITION,
    TREATMENT_CONDITION,
)
DECISION_STATES: Final = (
    "CONTROL_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE",
    "ORDER_INTERVENTION_RESTORES_BEHAVIOR",
    "ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE",
    "ORDER_INTERVENTION_CHANGES_FAILURE_PHENOTYPE",
    "ORDER_INTERVENTION_EFFECT_AMBIGUOUS",
    "DIAGNOSTIC_INVALID",
)


class AuthorizationIssuerError(RuntimeError):
    """Metadata-safe issuer failure."""

    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_ARGUMENT_ERROR",
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
    ] = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    prefix_caching_enabled: Literal[True] = True
    cache_block_size: Literal[16] = 16
    max_model_len: Literal[4096] = 4096
    worker_gpu_index: Literal[0] = 0


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_save_and_run_all_actions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[6] = 6
    maximum_model_loads: Literal[6] = 6
    maximum_worker_teardowns: Literal[6] = 6
    maximum_output_tokens_per_request: Literal[32] = 32
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_observations: Literal[0] = 0
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


class AuthorizationIntent(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    intent_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    scope: Literal["C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"]
    prepared_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=MAX_WINDOW_MINUTES)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_merge_commit: Literal["2e0e09b65023397f30d73a406f3f60e7090c85b1"] = (
        DESIGN_MERGE_COMMIT
    )
    authorization_design_record_sha256: Literal[
        "8305ebb153f962015c28de98bd6fcf6feeb202482163c6cce3f0caf08cc3d143"
    ] = DESIGN_RECORD_SHA256
    implementation_merge_commit: Literal["7e037596de1a74038583a85ed81d46ec12debbac"] = (
        IMPLEMENTATION_MERGE_COMMIT
    )
    implementation_review_sha256: Literal[
        "355a6b7f7871e648d8bfaf4c7841e9e6346f9b59eba65ac98c00b55d940d2595"
    ] = IMPLEMENTATION_REVIEW_SHA256
    implementation_record_sha256: Literal[
        "c563bf012c7ec587089b7b28af5074207a389c5fb7381b9c1213299d3b489386"
    ] = IMPLEMENTATION_RECORD_SHA256
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "1d055dfab9f83a2706f5335b4529df98d45e45de5210a8c6c21c2b91e6a72df0"
    ] = SUCCESSOR_RUNTIME_SHA256
    runtime_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    budget_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    experiment_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    experiment: dict[str, object]
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
    authorization_id: str = Field(pattern=r"^c4po-[0-9a-f]{32}$")
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle: Literal["ISSUED"] = "ISSUED"
    scope: Literal["C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"]
    authorization_challenge_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_confirmation_method: Literal["RETYPE_DYNAMIC_SHA256_CHALLENGE"]
    operator_confirmation_recorded: Literal[True]
    operator_confirmed_at: datetime
    issued_at: datetime
    expires_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=MAX_WINDOW_MINUTES)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_merge_commit: Literal["2e0e09b65023397f30d73a406f3f60e7090c85b1"] = (
        DESIGN_MERGE_COMMIT
    )
    authorization_design_record_sha256: Literal[
        "8305ebb153f962015c28de98bd6fcf6feeb202482163c6cce3f0caf08cc3d143"
    ] = DESIGN_RECORD_SHA256
    implementation_merge_commit: Literal["7e037596de1a74038583a85ed81d46ec12debbac"] = (
        IMPLEMENTATION_MERGE_COMMIT
    )
    implementation_review_sha256: Literal[
        "355a6b7f7871e648d8bfaf4c7841e9e6346f9b59eba65ac98c00b55d940d2595"
    ] = IMPLEMENTATION_REVIEW_SHA256
    implementation_record_sha256: Literal[
        "c563bf012c7ec587089b7b28af5074207a389c5fb7381b9c1213299d3b489386"
    ] = IMPLEMENTATION_RECORD_SHA256
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "1d055dfab9f83a2706f5335b4529df98d45e45de5210a8c6c21c2b91e6a72df0"
    ] = SUCCESSOR_RUNTIME_SHA256
    runtime_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    budget_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    experiment_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    experiment: dict[str, object]
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
    threshold_search_authorized: Literal[False] = False
    runtime_remediation_authorized: Literal[False] = False
    p5_p6_requalification_authorized: Literal[False] = False
    north_star_abc_effect_claim_authorized: Literal[False] = False
    paragraph_order_root_cause_claim_authorized: Literal[False] = False

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
        "8305ebb153f962015c28de98bd6fcf6feeb202482163c6cce3f0caf08cc3d143"
    ] = DESIGN_RECORD_SHA256
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "1d055dfab9f83a2706f5335b4529df98d45e45de5210a8c6c21c2b91e6a72df0"
    ] = SUCCESSOR_RUNTIME_SHA256
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    budget_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    experiment_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
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
    platform_observation_receipt_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
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
            invalid_unused = (
                self.execution_attempted
                or self.execution_outcome is not None
                or self.saved_version_id is not None
            )
            if invalid_unused:
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
        passed_without_platform = (
            self.execution_outcome == ExecutionOutcome.PASSED
            and self.platform_observation_receipt_sha256 is None
        )
        if passed_without_platform:
            raise ValueError("PASSED outcome requires durable platform observation receipt")
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
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_ARTIFACT_MISSING",
            "required artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _read_json_object(root: Path, relative: Path) -> dict[str, object]:
    parsed: object = json.loads(_read_required(root, relative))
    if not isinstance(parsed, dict):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_JSON_INVALID",
            "required JSON artifact must contain one object",
            relative.as_posix(),
        )
    return cast(dict[str, object], parsed)


def _git(root: Path, *arguments: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _require_git(root: Path, *arguments: str) -> str:
    code, stdout, _ = _git(root, *arguments)
    if code != 0:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_GIT_STATE_FAILED",
            "unable to inspect repository state",
        )
    return stdout


def _require_design_ancestor(root: Path) -> None:
    code, _, _ = _git(
        root,
        "merge-base",
        "--is-ancestor",
        DESIGN_MERGE_COMMIT,
        "HEAD",
    )
    if code != 0:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_DESIGN_NOT_ANCESTOR",
            "merged authorization design is not an ancestor of HEAD",
        )


def _require_merged_clean_main(root: Path) -> str:
    branch = _require_git(root, "branch", "--show-current")
    if branch != "main":
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_NOT_ON_MAIN",
            "live authorization requires synchronized main",
        )
    head = _require_git(root, "rev-parse", "HEAD")
    origin_main = _require_git(root, "rev-parse", "origin/main")
    if head != origin_main:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "HEAD must equal origin/main before live authorization",
        )
    status = _require_git(root, "status", "--porcelain=v1", "-uall")
    if status:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
            "repository must be clean before live authorization",
        )
    code, _, _ = _git(
        root,
        "merge-base",
        "--is-ancestor",
        DESIGN_MERGE_COMMIT,
        head,
    )
    if code != 0:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_DESIGN_NOT_MERGED",
            "authorization design is not contained in current main",
        )
    return head


def _verify_hash(root: Path, relative: Path, expected_sha256: str) -> bytes:
    payload = _read_required(root, relative)
    if _sha256(payload) != expected_sha256:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_IDENTITY_DRIFT",
            "bound authority identity drifted",
            relative.as_posix(),
        )
    return payload


def _component(record: dict[str, object], key: str) -> dict[str, object]:
    value = record.get(key)
    if not isinstance(value, dict):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_DESIGN_CONTRACT_DRIFT",
            f"authorization design component is missing or invalid: {key}",
            DESIGN_RECORD_PATH.as_posix(),
        )
    return cast(dict[str, object], value)


def _contract_sha256(value: object) -> str:
    return _sha256(_canonical_json_bytes(value))


def _require_field(
    mapping: dict[str, object],
    field: str,
    expected: object,
    *,
    error_code: str,
) -> None:
    if mapping.get(field) != expected:
        raise AuthorizationIssuerError(
            error_code,
            f"authorization design field drifted: {field}",
            DESIGN_RECORD_PATH.as_posix(),
        )


def _validate_experiment(experiment: dict[str, object]) -> None:
    required: dict[str, object] = {
        "experiment_id": AUTHORIZATION_SCOPE,
        "variable_under_test": (
            "GLOBAL_PARAGRAPH_ORDER_WITH_TOKEN_INVENTORY_AND_LOCAL_TAIL_LOCKED"
        ),
        "control_condition_id": CONTROL_CONDITION,
        "treatment_condition_id": TREATMENT_CONDITION,
        "observations_per_condition": 3,
        "request_order": list(REQUEST_ORDER),
        "prompt_token_count_per_condition": 899,
        "control_token_sha256": (
            "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
        ),
        "treatment_token_sha256": (
            "14d6a6856ffb5c4caa4a4ed229fa0c94ac06b86fbef473be001dd6d8e3698cce"
        ),
        "control_payload_sha256": (
            "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
        ),
        "treatment_payload_sha256": (
            "47c519c24efd40e3bab4bfa2eaec1cf3d62c91a648870e631721625567f20b5e"
        ),
        "historical_control_parsed_object_sha256": (
            "fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba"
        ),
        "control_anchor_historical_parsed_identity_required": True,
        "control_anchor_must_reproduce_zero_of_three_exact": True,
        "control_anchor_valid_json_three_of_three_required": True,
        "fresh_worker_process_per_observation": True,
        "zero_cached_prefix_baseline_required": True,
        "teardown_required_between_observations": True,
        "prior_request_cache_carryover_permitted": False,
        "pre_request_token_identity_journal_required": True,
        "pre_request_identity_persisted_before_model_request_budget": True,
        "threshold_search_authorized": False,
        "runtime_remediation_authorized": False,
        "p5_p6_requalification_authorized": False,
        "north_star_abc_effect_claim_authorized": False,
        "paragraph_order_root_cause_claim_permitted": False,
        "mixed_result_permits_paragraph_order_claim": False,
        "post_hoc_two_of_three_interpretation_permitted": False,
    }
    for field, expected in required.items():
        _require_field(
            experiment,
            field,
            expected,
            error_code="C4_PARAGRAPH_ORDER_AUTHORIZATION_EXPERIMENT_DRIFT",
        )
    _require_field(
        experiment,
        "decision_states",
        list(DECISION_STATES),
        error_code="C4_PARAGRAPH_ORDER_AUTHORIZATION_EXPERIMENT_DRIFT",
    )


def _validate_design(root: Path) -> dict[str, object]:
    payload = _verify_hash(root, DESIGN_RECORD_PATH, DESIGN_RECORD_SHA256)
    parsed: object = json.loads(payload)
    if not isinstance(parsed, dict):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_DESIGN_INVALID",
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
    for field, expected in required.items():
        _require_field(
            record,
            field,
            expected,
            error_code="C4_PARAGRAPH_ORDER_AUTHORIZATION_DESIGN_CONTRACT_DRIFT",
        )

    runtime = _component(record, "runtime_model")
    budget = _component(record, "execution_budget")
    experiment = _component(record, "experiment")
    platform = _component(record, "platform")

    if runtime != RuntimeModelContract().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_RUNTIME_CONTRACT_DRIFT",
            "authorization design runtime/model contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if budget != ExecutionBudget().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_BUDGET_DRIFT",
            "authorization design execution budget drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if platform != RequiredPlatform().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_PLATFORM_DRIFT",
            "authorization design required platform contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    _validate_experiment(experiment)

    human = _component(record, "human_authorization")
    required_human = {
        "fresh_human_authority_required": True,
        "confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "challenge_must_be_dynamic": True,
        "exact_challenge_retype_required": True,
        "confirmation_binds_exact_authorization_intent": True,
        "challenge_synthesis_by_runtime_prohibited": True,
        "challenge_synthesis_by_assistant_prohibited": True,
        "challenge_synthesis_by_model_prohibited": True,
        "challenge_synthesis_by_issuer_prohibited": True,
        "maximum_confirmation_age_minutes": MAX_CONFIRMATION_AGE_MINUTES,
        "default_authorization_window_minutes": DEFAULT_WINDOW_MINUTES,
        "maximum_authorization_window_minutes": MAX_WINDOW_MINUTES,
    }
    for field, expected in required_human.items():
        _require_field(
            human,
            field,
            expected,
            error_code="C4_PARAGRAPH_ORDER_AUTHORIZATION_HUMAN_CONTROL_DRIFT",
        )

    observation = _component(record, "platform_observation_receipt")
    required_observation = {
        "control_id": PLATFORM_CONTROL_ID,
        "durable_receipt_required": True,
        "receipt_must_exist_before_save_and_run_all": True,
        "receipt_bound_to_transaction_id": True,
        "receipt_created_after_transaction_artifact": True,
        "receipt_runtime_input": False,
        "console_only_observation_sufficient": False,
        "failure_to_persist_blocks_execution": True,
    }
    for field, expected in required_observation.items():
        _require_field(
            observation,
            field,
            expected,
            error_code="C4_PARAGRAPH_ORDER_AUTHORIZATION_PLATFORM_CONTROL_DRIFT",
        )

    transport = _component(record, "transport_topology")
    required_transport = {
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_authorization_filename_discovery_permitted": False,
        "permitted_kaggle_input_roles": ["durable_runtime", "model_snapshot"],
    }
    for field, expected in required_transport.items():
        _require_field(
            transport,
            field,
            expected,
            error_code="C4_PARAGRAPH_ORDER_AUTHORIZATION_TRANSPORT_DRIFT",
        )

    admission = _component(record, "runtime_admission")
    required_admission = {
        "static_repository_runtime_execution_permitted": False,
        "transaction_bound_executable_required": True,
        "authorization_admission_precedes_runtime_installation": True,
        "authorization_must_be_live_at_admission": True,
        "admitted_execution_may_finish_after_expiry": True,
        "unchanged_replay_authorized": False,
    }
    for field, expected in required_admission.items():
        _require_field(
            admission,
            field,
            expected,
            error_code="C4_PARAGRAPH_ORDER_AUTHORIZATION_ADMISSION_DRIFT",
        )
    return record


def _validate_implementation_authorities(root: Path) -> bytes:
    _verify_hash(root, IMPLEMENTATION_REVIEW_PATH, IMPLEMENTATION_REVIEW_SHA256)
    _verify_hash(root, IMPLEMENTATION_RECORD_PATH, IMPLEMENTATION_RECORD_SHA256)
    return _verify_hash(root, SUCCESSOR_RUNTIME_PATH, SUCCESSOR_RUNTIME_SHA256)


def _static_review(root: Path) -> dict[str, object]:
    design = _validate_design(root)
    _validate_implementation_authorities(root)
    source = _read_required(root, SOURCE_PATH)
    template = _read_required(root, TEMPLATE_PATH)
    test = _read_required(root, TEST_PATH)
    report = _read_required(root, REPORT_PATH)
    runbook = _read_required(root, RUNBOOK_PATH)
    runtime = _component(design, "runtime_model")
    budget = _component(design, "execution_budget")
    experiment = _component(design, "experiment")
    platform = _component(design, "platform")

    return {
        "schema_version": "1.0.0",
        "review_id": (
            "auragateway-c4-paragraph-order-behavioral-differential-"
            "execution-authorization-v1-review"
        ),
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
        "runtime_contract_sha256": _contract_sha256(runtime),
        "budget_contract_sha256": _contract_sha256(budget),
        "experiment_contract_sha256": _contract_sha256(experiment),
        "platform_contract_sha256": _contract_sha256(platform),
        "authorization_scope": AUTHORIZATION_SCOPE,
        "authorization_architecture": "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "operator_confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "transaction_id_derivation": "SHA256_CANONICAL_AUTHORIZATION_BYTES",
        "maximum_model_requests": 6,
        "maximum_worker_starts": 6,
        "maximum_model_loads": 6,
        "maximum_worker_teardowns": 6,
        "maximum_hidden_retries": 0,
        "maximum_replacement_observations": 0,
        "maximum_output_tokens_per_request": 32,
        "condition_count": 2,
        "observations_per_condition": 3,
        "prompt_token_count_per_condition": 899,
        "request_order": list(REQUEST_ORDER),
        "control_anchor_historical_parsed_identity_required": True,
        "paragraph_order_root_cause_claim_authorized": False,
        "threshold_search_authorized": False,
        "runtime_remediation_authorized": False,
        "p5_p6_requalification_authorized": False,
        "north_star_abc_effect_claim_authorized": False,
        "durable_platform_observation_required": True,
        "platform_observation_control_id": PLATFORM_CONTROL_ID,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_anti_replay_established": False,
        "systemexit_zero_is_success": True,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
        "platform_observation_persisted": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _static_record(root: Path, review_bytes: bytes) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_id": (
            "auragateway-c4-paragraph-order-behavioral-differential-execution-authorization-v1"
        ),
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
        "maximum_worker_starts": 6,
        "maximum_model_loads": 6,
        "maximum_worker_teardowns": 6,
        "maximum_hidden_retries": 0,
        "maximum_replacement_observations": 0,
        "maximum_output_tokens_per_request": 32,
        "condition_count": 2,
        "observations_per_condition": 3,
        "prompt_token_count_per_condition": 899,
        "request_order": list(REQUEST_ORDER),
        "control_anchor_historical_parsed_identity_required": True,
        "paragraph_order_root_cause_claim_authorized": False,
        "threshold_search_authorized": False,
        "runtime_remediation_authorized": False,
        "p5_p6_requalification_authorized": False,
        "north_star_abc_effect_claim_authorized": False,
        "durable_platform_observation_required": True,
        "platform_observation_control_id": PLATFORM_CONTROL_ID,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_anti_replay_established": False,
        "systemexit_zero_is_success": True,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
        "platform_observation_persisted": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "model_loads_performed": 0,
        "worker_starts_performed": 0,
        "next_gate": NEXT_GATE,
    }


def generate_static(root: Path) -> dict[str, object]:
    root = root.resolve()
    review_bytes = _artifact_json_bytes(_static_review(root))
    record_bytes = _artifact_json_bytes(_static_record(root, review_bytes))
    for relative, payload in (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return {
        "status": "C4_PARAGRAPH_ORDER_AUTHORIZATION_STATIC_ARTIFACTS_GENERATED",
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
    for relative, expected in (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        if _read_required(root, relative) != expected:
            raise AuthorizationIssuerError(
                "C4_PARAGRAPH_ORDER_AUTHORIZATION_STATIC_ARTIFACT_DRIFT",
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
                "C4_PARAGRAPH_ORDER_AUTHORIZATION_LIVE_LIFECYCLE_PRESENT",
                "static validation requires no live lifecycle artifact",
                relative.as_posix(),
            )
    return {
        "status": "C4_PARAGRAPH_ORDER_EXECUTION_AUTHORIZATION_V1_VALID",
        "authorization_scope": AUTHORIZATION_SCOPE,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 6,
        "maximum_model_loads": 6,
        "maximum_worker_teardowns": 6,
        "maximum_hidden_retries": 0,
        "maximum_replacement_observations": 0,
        "condition_count": 2,
        "observations_per_condition": 3,
        "prompt_token_count_per_condition": 899,
        "request_order": list(REQUEST_ORDER),
        "control_anchor_historical_parsed_identity_required": True,
        "paragraph_order_root_cause_claim_authorized": False,
        "durable_platform_observation_required": True,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "systemexit_zero_is_success": True,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
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
    design = _validate_design(root)
    runtime_payload = _validate_implementation_authorities(root)
    runtime = RuntimeModelContract.model_validate(_component(design, "runtime_model"))
    budget = ExecutionBudget.model_validate(_component(design, "execution_budget"))
    experiment = _component(design, "experiment")
    platform = RequiredPlatform.model_validate(_component(design, "platform"))
    return AuthorizationIntent(
        intent_id=intent_id,
        scope=AUTHORIZATION_SCOPE,
        prepared_at=prepared_at,
        authorization_window_minutes=window_minutes,
        issuer_merge_commit=issuer_merge_commit,
        issuer_source_sha256=_sha256(_read_required(root, SOURCE_PATH)),
        generator_contract_sha256=_sha256(_read_required(root, TEMPLATE_PATH)),
        runtime_contract_sha256=_contract_sha256(runtime),
        budget_contract_sha256=_contract_sha256(budget),
        experiment_contract_sha256=_contract_sha256(experiment),
        platform_contract_sha256=_contract_sha256(platform),
        runtime=runtime,
        budget=budget,
        experiment=experiment,
        required_platform=platform,
        runtime_payload_sha256=_sha256(runtime_payload),
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
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_CHALLENGE_DRIFT",
            "authorization challenge does not bind exact intent",
        )
    confirmed = _normalize_time(confirmed_at, "confirmed_at")
    if confirmed < intent.prepared_at:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_CONFIRMATION_TIME_INVALID",
            "operator confirmation precedes authorization intent",
        )
    if confirmed - intent.prepared_at > timedelta(minutes=MAX_CONFIRMATION_AGE_MINUTES):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_CONFIRMATION_STALE",
            "operator confirmation exceeded freshness window",
        )
    body = AuthorizationBody(
        authorization_id="c4po-" + intent.intent_id,
        scope=AUTHORIZATION_SCOPE,
        authorization_challenge_sha256=challenge,
        operator_confirmation_method="RETYPE_DYNAMIC_SHA256_CHALLENGE",
        operator_confirmation_recorded=True,
        operator_confirmed_at=confirmed,
        issued_at=confirmed,
        expires_at=confirmed + timedelta(minutes=intent.authorization_window_minutes),
        authorization_window_minutes=intent.authorization_window_minutes,
        issuer_merge_commit=intent.issuer_merge_commit,
        issuer_source_sha256=intent.issuer_source_sha256,
        generator_contract_sha256=intent.generator_contract_sha256,
        runtime_contract_sha256=intent.runtime_contract_sha256,
        budget_contract_sha256=intent.budget_contract_sha256,
        experiment_contract_sha256=intent.experiment_contract_sha256,
        platform_contract_sha256=intent.platform_contract_sha256,
        runtime=intent.runtime,
        budget=intent.budget,
        experiment=intent.experiment,
        required_platform=intent.required_platform,
    )
    transaction_id = _sha256(_canonical_json_bytes(body))
    authorization = ExecutionAuthorization(
        transaction_id=transaction_id,
        authorization=body,
    )
    return authorization, _canonical_json_bytes(authorization)


def _python_adjacent_string_literals(value: str, *, chunk_size: int = 72) -> str:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    chunks = tuple(
        value[offset : offset + chunk_size] for offset in range(0, len(value), chunk_size)
    )
    if not chunks:
        return '""'
    return "\n    ".join(json.dumps(chunk) for chunk in chunks)


def render_executable_payload(
    root: Path,
    authorization: ExecutionAuthorization,
    authorization_bytes: bytes,
    runtime_payload: bytes,
) -> bytes:
    template = _read_required(root, TEMPLATE_PATH)
    generator_sha = _sha256(template)
    issuer_source_sha = _sha256(_read_required(root, SOURCE_PATH))
    body = authorization.authorization
    if body.generator_contract_sha256 != generator_sha:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_GENERATOR_DRIFT",
            "authorization does not bind current generator contract",
        )
    if body.issuer_source_sha256 != issuer_source_sha:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_ISSUER_SOURCE_DRIFT",
            "authorization does not bind current issuer source",
        )
    if body.runtime_payload_sha256 != _sha256(runtime_payload):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_RUNTIME_PAYLOAD_DRIFT",
            "authorization does not bind supplied runtime payload",
        )

    replacements = {
        "__AUTHORIZATION_B64__": _python_adjacent_string_literals(
            base64.b64encode(authorization_bytes).decode("ascii")
        ),
        "__RUNTIME_PAYLOAD_B64__": _python_adjacent_string_literals(
            base64.b64encode(runtime_payload).decode("ascii")
        ),
        "__TRANSACTION_ID__": authorization.transaction_id,
        "__ISSUER_MERGE_COMMIT__": body.issuer_merge_commit,
        "__ISSUER_SOURCE_SHA256__": issuer_source_sha,
        "__RUNTIME_PAYLOAD_SHA256__": body.runtime_payload_sha256,
        "__GENERATOR_CONTRACT_SHA256__": generator_sha,
        "__RUNTIME_CONTRACT_SHA256__": body.runtime_contract_sha256,
        "__BUDGET_CONTRACT_SHA256__": body.budget_contract_sha256,
        "__EXPERIMENT_CONTRACT_SHA256__": body.experiment_contract_sha256,
        "__PLATFORM_CONTRACT_SHA256__": body.platform_contract_sha256,
    }
    rendered = template.decode("utf-8")
    for marker, value in replacements.items():
        if rendered.count(marker) != 1:
            raise AuthorizationIssuerError(
                "C4_PARAGRAPH_ORDER_AUTHORIZATION_TEMPLATE_MARKER_DRIFT",
                f"generator template marker cardinality drifted: {marker}",
            )
        rendered = rendered.replace(marker, value)
    return rendered.encode("utf-8")


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
    return _artifact_json_bytes(notebook)


def build_manifest(
    authorization: ExecutionAuthorization,
    authorization_bytes: bytes,
    executable_payload: bytes,
    notebook_bytes: bytes,
) -> ExecutionArtifactManifest:
    body = authorization.authorization
    return ExecutionArtifactManifest(
        status="TRANSACTION_BOUND_EXECUTABLE_GENERATED",
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(authorization_bytes),
        issuer_merge_commit=body.issuer_merge_commit,
        issuer_source_sha256=body.issuer_source_sha256,
        generator_contract_sha256=body.generator_contract_sha256,
        runtime_contract_sha256=body.runtime_contract_sha256,
        budget_contract_sha256=body.budget_contract_sha256,
        experiment_contract_sha256=body.experiment_contract_sha256,
        platform_contract_sha256=body.platform_contract_sha256,
        executable_payload_sha256=_sha256(executable_payload),
        notebook_container_sha256=_sha256(notebook_bytes),
        permitted_kaggle_input_roles=("durable_runtime", "model_snapshot"),
    )


def authorize_generate(
    root: Path,
    output_path: Path,
    *,
    window_minutes: int,
) -> dict[str, object]:
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
                "C4_PARAGRAPH_ORDER_AUTHORIZATION_LIFECYCLE_EXISTS",
                "live transaction lifecycle already exists",
                relative.as_posix(),
            )
    if output_path.exists():
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_OUTPUT_EXISTS",
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
    print("maximum_worker_starts=6")
    print("maximum_model_loads=6")
    print("maximum_worker_teardowns=6")
    print("maximum_hidden_retries=0")
    print("request_order=CONTROL,TREATMENT,TREATMENT,CONTROL,CONTROL,TREATMENT")
    print("control_anchor_historical_parsed_identity_required=true")
    print("paragraph_order_root_cause_claim_authorized=false")
    print("required_platform=T4_X2 / 2 GPUs / Internet Off")
    print("platform_observation_control=" + PLATFORM_CONTROL_ID)
    observed = input(
        "Retype the authorization challenge to authorize exactly one "
        "C4 paragraph-order behavioral differential execution: "
    ).strip()
    if observed != challenge:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_CONFIRMATION_MISMATCH",
            "interactive authorization challenge did not match",
        )

    authorization, authorization_bytes = build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=datetime.now(UTC),
    )
    runtime_payload = _validate_implementation_authorities(root)
    executable_payload = render_executable_payload(
        root,
        authorization,
        authorization_bytes,
        runtime_payload,
    )
    notebook_bytes = build_notebook(executable_payload)
    manifest = build_manifest(
        authorization,
        authorization_bytes,
        executable_payload,
        notebook_bytes,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(notebook_bytes)
    (root / LIVE_AUTHORIZATION_PATH).write_bytes(_artifact_json_bytes(authorization))
    (root / LIVE_MANIFEST_PATH).write_bytes(_artifact_json_bytes(manifest))
    return {
        "status": "C4_PARAGRAPH_ORDER_EXECUTION_ARTIFACT_AUTHORIZED_AND_GENERATED",
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


def record_platform_observation(
    root: Path,
    *,
    observed_at: datetime,
) -> dict[str, object]:
    root = root.resolve()
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_ALREADY_TERMINAL",
            "transaction already has a terminal receipt",
        )
    if (root / PLATFORM_OBSERVATION_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_PLATFORM_OBSERVATION_ALREADY_PERSISTED",
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
            "C4_PARAGRAPH_ORDER_LIFECYCLE_IDENTITY_DRIFT",
            "live manifest no longer binds live authorization",
        )
    if manifest.transaction_id != authorization.transaction_id:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_TRANSACTION_DRIFT",
            "live manifest transaction identity drifted",
        )

    observed = _normalize_time(observed_at, "platform_observed_at")
    if observed < authorization.authorization.issued_at:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_PLATFORM_TIME_INVALID",
            "platform observation precedes authorization",
        )
    if observed >= authorization.authorization.expires_at:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_PLATFORM_TIME_EXPIRED",
            "platform observation occurred after authorization expiry",
        )

    receipt = PlatformObservationReceipt(
        transaction_id=authorization.transaction_id,
        authorization_sha256=manifest.authorization_sha256,
        manifest_sha256=_sha256(_canonical_json_bytes(manifest)),
        platform_observed_at=observed,
    )
    receipt_bytes = _artifact_json_bytes(receipt)
    (root / PLATFORM_OBSERVATION_RECEIPT_PATH).write_bytes(receipt_bytes)
    return {
        "status": "C4_PARAGRAPH_ORDER_PLATFORM_OBSERVATION_PERSISTED",
        "transaction_id": authorization.transaction_id,
        "platform_observation_receipt_sha256": _sha256(_canonical_json_bytes(receipt)),
        "platform_observation_persisted": True,
        "save_and_run_all_authorized_yet": True,
        "next_gate": NEXT_GATE_AFTER_OBSERVATION,
    }


def _optional_file_sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.is_file() or path.is_symlink():
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_TERMINAL_EVIDENCE_MISSING",
            "terminal evidence path is missing or unsafe",
            str(path),
        )
    return _sha256(path.read_bytes())


def terminalize(
    root: Path,
    *,
    disposition: TerminalDisposition,
    execution_attempted: bool,
    execution_outcome: ExecutionOutcome | None,
    saved_version_id: int | None,
    evidence_zip: Path | None,
    terminal_log: Path | None,
    terminalized_at: datetime,
) -> dict[str, object]:
    root = root.resolve()
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_ALREADY_TERMINAL",
            "transaction already has a terminal receipt",
        )

    authorization_bytes = _read_required(root, LIVE_AUTHORIZATION_PATH)
    manifest_bytes = _read_required(root, LIVE_MANIFEST_PATH)
    authorization = ExecutionAuthorization.model_validate_json(authorization_bytes)
    manifest = ExecutionArtifactManifest.model_validate_json(manifest_bytes)
    canonical_authorization = _canonical_json_bytes(authorization)
    canonical_manifest = _canonical_json_bytes(manifest)

    if manifest.authorization_sha256 != _sha256(canonical_authorization):
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_LIFECYCLE_IDENTITY_DRIFT",
            "live manifest no longer binds live authorization",
        )
    if manifest.transaction_id != authorization.transaction_id:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_TRANSACTION_DRIFT",
            "live manifest transaction identity drifted",
        )

    platform_sha256: str | None = None
    platform_path = root / PLATFORM_OBSERVATION_RECEIPT_PATH
    if platform_path.exists():
        platform_payload = _read_required(root, PLATFORM_OBSERVATION_RECEIPT_PATH)
        platform_receipt = PlatformObservationReceipt.model_validate_json(platform_payload)
        if platform_receipt.transaction_id != authorization.transaction_id:
            raise AuthorizationIssuerError(
                "C4_PARAGRAPH_ORDER_PLATFORM_TRANSACTION_DRIFT",
                "platform receipt transaction identity drifted",
            )
        platform_sha256 = _sha256(_canonical_json_bytes(platform_receipt))

    receipt = TerminalReceipt(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(canonical_authorization),
        manifest_sha256=_sha256(canonical_manifest),
        disposition=disposition,
        execution_attempted=execution_attempted,
        execution_outcome=execution_outcome,
        terminalized_at=terminalized_at,
        saved_version_id=saved_version_id,
        platform_observation_receipt_sha256=platform_sha256,
        evidence_zip_sha256=_optional_file_sha256(evidence_zip),
        terminal_log_sha256=_optional_file_sha256(terminal_log),
    )
    receipt_bytes = _artifact_json_bytes(receipt)
    (root / TERMINAL_RECEIPT_PATH).write_bytes(receipt_bytes)
    return {
        "status": "C4_PARAGRAPH_ORDER_EXECUTION_AUTHORIZATION_TERMINALIZED",
        "transaction_id": authorization.transaction_id,
        "disposition": receipt.disposition.value,
        "execution_attempted": receipt.execution_attempted,
        "execution_outcome": (
            receipt.execution_outcome.value if receipt.execution_outcome is not None else None
        ),
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "terminal_receipt_sha256": _sha256(_canonical_json_bytes(receipt)),
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }


def _default_output() -> Path:
    return Path.home() / "Desktop" / "ag-c4-paragraph-order-behavioral-differential-v1.ipynb"


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
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=DEFAULT_WINDOW_MINUTES,
    )
    parser.add_argument("--platform-observed-at")
    parser.add_argument(
        "--disposition",
        choices=tuple(item.value for item in TerminalDisposition),
    )
    parser.add_argument("--execution-attempted", action="store_true")
    parser.add_argument(
        "--execution-outcome",
        choices=tuple(item.value for item in ExecutionOutcome),
    )
    parser.add_argument("--saved-version-id", type=int)
    parser.add_argument("--evidence-zip")
    parser.add_argument("--terminal-log")
    parser.add_argument("--terminalized-at")
    return parser


def _parse_datetime(value: str, field: str) -> datetime:
    try:
        observed = datetime.fromisoformat(value)
    except ValueError as error:
        raise AuthorizationIssuerError(
            "C4_PARAGRAPH_ORDER_AUTHORIZATION_TIME_INVALID",
            f"{field} must be an ISO-8601 datetime",
        ) from error
    return _normalize_time(observed, field)


def main() -> int:
    args = _parser().parse_args()
    root = Path(args.repo_root)
    try:
        result: dict[str, object]
        if args.command == "generate":
            result = generate_static(root)
        if args.command == "validate":
            result = validate_static(root)
        if args.command == "authorize-generate":
            output = Path(args.output).resolve() if args.output else _default_output()
            result = authorize_generate(
                root,
                output,
                window_minutes=args.window_minutes,
            )
        if args.command == "record-platform-observation":
            if args.platform_observed_at is None:
                raise AuthorizationIssuerError(
                    "C4_PARAGRAPH_ORDER_PLATFORM_TIME_REQUIRED",
                    "--platform-observed-at is required",
                )
            result = record_platform_observation(
                root,
                observed_at=_parse_datetime(
                    args.platform_observed_at,
                    "platform_observed_at",
                ),
            )
        if args.command == "terminalize":
            if args.disposition is None or args.terminalized_at is None:
                raise AuthorizationIssuerError(
                    "C4_PARAGRAPH_ORDER_TERMINAL_ARGUMENT_REQUIRED",
                    "--disposition and --terminalized-at are required",
                )
            outcome = (
                ExecutionOutcome(args.execution_outcome)
                if args.execution_outcome is not None
                else None
            )
            evidence_zip = Path(args.evidence_zip).resolve() if args.evidence_zip else None
            terminal_log = Path(args.terminal_log).resolve() if args.terminal_log else None
            result = terminalize(
                root,
                disposition=TerminalDisposition(args.disposition),
                execution_attempted=args.execution_attempted,
                execution_outcome=outcome,
                saved_version_id=args.saved_version_id,
                evidence_zip=evidence_zip,
                terminal_log=terminal_log,
                terminalized_at=_parse_datetime(
                    args.terminalized_at,
                    "terminalized_at",
                ),
            )
    except (
        AuthorizationIssuerError,
        ValidationError,
        json.JSONDecodeError,
        OSError,
        UnicodeDecodeError,
    ) as error:
        if isinstance(error, AuthorizationIssuerError):
            code = error.error_code
            message = error.safe_message
            path = error.path
        if not isinstance(error, AuthorizationIssuerError):
            code = "C4_PARAGRAPH_ORDER_AUTHORIZATION_VALIDATION_FAILED"
            message = str(error)
            path = None
        print(
            json.dumps(
                {
                    "error_code": code,
                    "safe_message": message,
                    "path": path,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

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
