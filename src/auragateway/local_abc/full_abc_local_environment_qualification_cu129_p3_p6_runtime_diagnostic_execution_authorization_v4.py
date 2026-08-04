"""Implement, issue, verify, and consume one P3-P6 execution authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v4,
)
from auragateway.local_abc.contracts import LocalABCContract

implementation = full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v4

SOURCE_MAIN_MERGE_COMMIT: Final = "603f11bf10336222d289d56d29a18d3e9c705c68"
IMPLEMENTATION_FEATURE_COMMIT: Final = "6c3d1865f563af3dae60c0f79345ffe18e21e092"
IMPLEMENTATION_RECORD_SHA256: Final = (
    "a9cc993508178c15326f95a86a18d0009f7565df703ed7d3b66251be021a6679"
)
IMPLEMENTATION_NOTEBOOK_SHA256: Final = (
    "92984ab474d495a443ab504f400c38782df1ee0c1d1b65646e9444b311a46dd7"
)
IMPLEMENTATION_REQUEST_SHA256: Final = (
    "dbd8827d8c0a19dcd7bd6c2c4717b8bd84bde98dcefd9cfb26628f7485385632"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "06f20bbbf627c3385c530cec6928442a651e5eecf9827f328ad2f9d0362bcda2"
)
IMPLEMENTATION_TEMPLATE_SHA256: Final = (
    "076b7e69123ccab235e89e581c97cc1db56084093e76074f2e7d6db23adc9c75"
)
IMPLEMENTATION_SOURCE_SHA256: Final = (
    "cde3a0c12471b33ba7bcda43ce63c00ab03cabcdbcc122fa6ad9be5eb40ca613"
)
IMPLEMENTATION_RUNTIME_SCRIPT_SHA256: Final = (
    "72e1daad1883e4bd1456ada15e073dbb252753b166b4cc250f591f71171679a3"
)
IMPLEMENTATION_WRAPPER_CODE_SHA256: Final = (
    "cfef877ff8698f40aec1a0a4c7a6ac94e762085dfdfde88994d6da341438cd4f"
)
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"

IMPLEMENTATION_RECORD_PATH: Final = implementation.RECORD_PATH
IMPLEMENTATION_NOTEBOOK_PATH: Final = implementation.NOTEBOOK_PATH
IMPLEMENTATION_REQUEST_PATH: Final = implementation.REQUEST_PATH
IMPLEMENTATION_REVIEW_PATH: Final = implementation.REVIEW_PATH
IMPLEMENTATION_TEMPLATE_PATH: Final = implementation.TEMPLATE_PATH
IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_v4.py"
)

ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_execution_authorization_v4.py"
)
ISSUER_TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_execution_authorization_v4.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-03-local-abc-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_Execution_Authorization_V4.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_execution_authorization_v4.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_v4_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_v4_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_v4.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_consumption_v4.json"
)

AUTHORIZATION_ID: Final = "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4"
AUTHORIZATION_SCOPE: Final = "P3_P6_RUNTIME_DIAGNOSTIC_V4"
SELECTED_BACKEND: Final = "TRITON_ATTN"
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
IMPLEMENTATION_NEXT_GATE: Final = (
    "explicit_operator_confirmation_then_issue_p3_p6_execution_authorization_v4"
)
ISSUED_NEXT_GATE: Final = "execute_governed_p3_p6_runtime_diagnostic_v4"
CONSUMED_NEXT_GATE: Final = "preserve_and_accept_p3_p6_runtime_diagnostic_evidence_v4"


class AuthorizationLifecycle(StrEnum):
    """Lifecycle states for one transient single-use authority."""

    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"


class ExecutionOutcome(StrEnum):
    """Terminal outcome recorded after the single governed attempt."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class P3P6AuthorizationError(RuntimeError):
    """Metadata-safe authorization boundary failure."""

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


class AuthorizationErrorEnvelope(LocalABCContract):
    """Machine-readable authorization error without sensitive payloads."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ARGUMENT_INVALID",
            "P3-P6 authorization arguments are invalid",
            details=(message,),
        )


class ArtifactReceipt(LocalABCContract):
    """Deterministic repository artifact identity."""

    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class WheelhouseAuthority(LocalABCContract):
    """Exact governed offline CUDA 12.9 wheelhouse controls."""

    requirements_in_sha256: Literal[
        "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"
    ]
    resolution_lock_sha256: Literal[
        "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
    ]
    materialization_lock_sha256: Literal[
        "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
    ]
    requirements_lock_sha256: Literal[
        "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"
    ]
    install_runtime_sha256: Literal[
        "68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"
    ]
    runtime_manifest_sha256: Literal[
        "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
    ]
    sha256_manifest_sha256: Literal[
        "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
    ]
    materialization_receipt_sha256: Literal[
        "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
    ]
    wheel_entry_count: Literal[176] = 176
    manifest_entry_count: Literal[182] = 182
    verified_entry_count: Literal[182] = 182


class EvidenceContractAuthority(LocalABCContract):
    """Exact V4 runtime evidence contract authorized for one attempt."""

    accepted_backend_marker: Literal["Using AttentionBackendEnum.TRITON_ATTN backend."] = (
        "Using AttentionBackendEnum.TRITON_ATTN backend."
    )
    exact_line_local_backend_marker_required: Literal[True] = True
    combined_stream_substring_matching_permitted: Literal[False] = False
    cli_echo_as_backend_evidence_permitted: Literal[False] = False
    matched_stream_line_number_and_hash_required: Literal[True] = True
    capture_threads_finalized_before_failure_serialization: Literal[True] = True
    worker_pid_parent_pid_and_start_identity_required: Literal[True] = True
    gpu_uuid_and_pci_bus_identity_required: Literal[True] = True
    structured_teardown_report_required: Literal[True] = True
    process_tree_absence_proof_required: Literal[True] = True
    gpu_process_absence_proof_required: Literal[True] = True
    closed_port_proof_required: Literal[True] = True
    gpu_memory_return_observation_required: Literal[True] = True
    maximum_gpu_memory_return_tolerance_mib: Literal[128] = 128
    executed_runtime_script_hash_required: Literal[True] = True
    notebook_wrapper_hash_verification_required: Literal[True] = True


class ImplementationAuthority(LocalABCContract):
    """Exact merged P3-P6 implementation and generated-artifact binding."""

    source_main_merge_commit: Literal["603f11bf10336222d289d56d29a18d3e9c705c68"]
    implementation_feature_commit: Literal["6c3d1865f563af3dae60c0f79345ffe18e21e092"]
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    implementation_record: ArtifactReceipt
    notebook: ArtifactReceipt
    request: ArtifactReceipt
    architecture_review: ArtifactReceipt
    template: ArtifactReceipt
    implementation_source: ArtifactReceipt
    runtime_script_sha256: Literal[
        "72e1daad1883e4bd1456ada15e073dbb252753b166b4cc250f591f71171679a3"
    ]
    wrapper_code_sha256: Literal["cfef877ff8698f40aec1a0a4c7a6ac94e762085dfdfde88994d6da341438cd4f"]
    evidence_contract: EvidenceContractAuthority
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    wheelhouse: WheelhouseAuthority
    runtime_execution_authorized_before_issuance: Literal[False]
    unchanged_v3_failure_replay_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_exact_bindings(self) -> Self:
        expected = {
            IMPLEMENTATION_RECORD_PATH.as_posix(): IMPLEMENTATION_RECORD_SHA256,
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(): IMPLEMENTATION_NOTEBOOK_SHA256,
            IMPLEMENTATION_REQUEST_PATH.as_posix(): IMPLEMENTATION_REQUEST_SHA256,
            IMPLEMENTATION_REVIEW_PATH.as_posix(): IMPLEMENTATION_REVIEW_SHA256,
            IMPLEMENTATION_TEMPLATE_PATH.as_posix(): IMPLEMENTATION_TEMPLATE_SHA256,
            IMPLEMENTATION_SOURCE_PATH.as_posix(): IMPLEMENTATION_SOURCE_SHA256,
        }
        observed = {
            self.implementation_record.repository_path: self.implementation_record.sha256,
            self.notebook.repository_path: self.notebook.sha256,
            self.request.repository_path: self.request.sha256,
            self.architecture_review.repository_path: self.architecture_review.sha256,
            self.template.repository_path: self.template.sha256,
            self.implementation_source.repository_path: self.implementation_source.sha256,
        }
        if observed != expected:
            raise ValueError("merged P3-P6 implementation bindings drifted")
        return self


class AuthorizationBudget(LocalABCContract):
    """Hard action ceiling for one sequential P3-P6 diagnostic."""

    maximum_authorization_window_minutes: Literal[240] = 240
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    maximum_model_requests: Literal[5] = 5
    maximum_output_tokens_per_request: Literal[32] = 32
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_hidden_retries: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class AuthorizationControls(LocalABCContract):
    """Fail-closed privacy, routing, and evidence controls."""

    accelerator: Literal["T4_X2"] = "T4_X2"
    internet_enabled: Literal[False] = False
    external_network_access_permitted: Literal[False] = False
    loopback_http_permitted: Literal[True] = True
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False
    explicit_backend_required: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    automatic_backend_selection_permitted: Literal[False] = False
    silent_backend_fallback_permitted: Literal[False] = False
    stop_on_first_failure: Literal[True] = True
    partial_evidence_required: Literal[True] = True
    deterministic_failure_report_required: Literal[True] = True
    runtime_install_report_required: Literal[True] = True
    bounded_install_diagnostics_required: Literal[True] = True
    runtime_import_closure_report_required: Literal[True] = True
    process_tree_import_closure_required: Literal[True] = True
    exact_target_site_pythonpath_required: Literal[True] = True
    nested_interpreter_probe_required: Literal[True] = True
    nested_interpreter_probe_before_model_copy_required: Literal[True] = True
    bounded_worker_failure_diagnostics_required: Literal[True] = True
    raw_worker_logs_in_evidence_zip_permitted: Literal[False] = False
    model_loads_on_import_probe_failure: Literal[0] = 0
    worker_starts_on_import_probe_failure: Literal[0] = 0
    deterministic_not_run_reports_required: Literal[True] = True
    scratch_cleanup_report_required: Literal[True] = True
    evidence_zip_required: Literal[True] = True
    maximum_evidence_zip_bytes: Literal[2097152] = 2097152
    wheel_find_links_relative_path: Literal["wheels"] = "wheels"
    filesystem_mutation_scope: Literal["KAGGLE_WORKING_DIRECTORY_ONLY"] = (
        "KAGGLE_WORKING_DIRECTORY_ONLY"
    )
    runtime_source_identity_report_required: Literal[True] = True
    exact_line_local_backend_marker_required: Literal[True] = True
    combined_stream_substring_matching_permitted: Literal[False] = False
    cli_echo_as_backend_evidence_permitted: Literal[False] = False
    matched_stream_line_number_and_hash_required: Literal[True] = True
    capture_threads_finalized_before_failure_serialization: Literal[True] = True
    worker_pid_parent_pid_and_start_identity_required: Literal[True] = True
    gpu_uuid_and_pci_bus_identity_required: Literal[True] = True
    worker_teardown_report_required: Literal[True] = True
    process_tree_absence_proof_required: Literal[True] = True
    gpu_process_absence_proof_required: Literal[True] = True
    closed_port_proof_required: Literal[True] = True
    gpu_memory_return_observation_required: Literal[True] = True
    maximum_gpu_memory_return_tolerance_mib: Literal[128] = 128
    executed_runtime_script_hash_required: Literal[True] = True
    notebook_wrapper_hash_verification_required: Literal[True] = True
    measured_abc_execution_authorized: Literal[False] = False


class AuthorizationArchitectureReview(LocalABCContract):
    """Deterministic decision to implement but not issue runtime authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4-review"
    ]
    status: Literal["APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION"]
    decision: Literal["SEPARATE_TRANSIENT_SINGLE_USE_P3_P6_V4_AUTHORIZATION"]
    implementation: ImplementationAuthority
    budget: AuthorizationBudget
    controls: AuthorizationControls
    operator_confirmation_required: Literal[True]
    authorization_must_remain_untracked: Literal[True]
    passed_failed_or_interrupted_attempt_consumes_authorization: Literal[True]
    runtime_loader_enforcement_mode: Literal[
        "OPERATOR_GATE_BOUND_TO_EXACT_NOTEBOOK_AND_INPUT_IDENTITIES"
    ]
    authorization_issued_in_review: Literal[False]
    runtime_execution_performed: Literal[False]
    next_gate: Literal["explicit_operator_confirmation_then_issue_p3_p6_execution_authorization_v4"]
    non_claims: tuple[str, ...] = Field(min_length=10)


class AuthorizationImplementationRecord(LocalABCContract):
    """Repository receipt for the issuer implementation only."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4-record"
    ]
    status: Literal["P3_P6_RUNTIME_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V4_VALID"]
    source_main_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation: ImplementationAuthority
    review: ArtifactReceipt
    issuer_source: ArtifactReceipt
    issuer_tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    authorization_path: str
    consumption_path: str
    authorization_issuer_implemented: Literal[True]
    authorization_issued: Literal[False]
    consumption_record_created: Literal[False]
    runtime_execution_performed: Literal[False]
    budget: AuthorizationBudget
    controls: AuthorizationControls
    next_gate: Literal["explicit_operator_confirmation_then_issue_p3_p6_execution_authorization_v4"]


class AuthorizationIssuanceConfirmation(LocalABCContract):
    """Explicit operator confirmation required before transient issuance."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    confirmation_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-confirmation-v4"
    ]
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=240)
    confirmed_scope: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V4"]
    confirmed_notebook_sha256: Literal[
        "92984ab474d495a443ab504f400c38782df1ee0c1d1b65646e9444b311a46dd7"
    ]
    confirmed_runtime_script_sha256: Literal[
        "72e1daad1883e4bd1456ada15e073dbb252753b166b4cc250f591f71171679a3"
    ]
    confirmed_wrapper_code_sha256: Literal[
        "cfef877ff8698f40aec1a0a4c7a6ac94e762085dfdfde88994d6da341438cd4f"
    ]
    confirmed_model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    confirmed_backend: Literal["TRITON_ATTN"]

    @field_validator("confirmed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("confirmed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


class P3P6ExecutionAuthorization(LocalABCContract):
    """Transient single-use runtime authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal[AuthorizationLifecycle.ISSUED]
    scope: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V4"]
    source_main_merge_commit: Literal["603f11bf10336222d289d56d29a18d3e9c705c68"]
    implementation_feature_commit: Literal["6c3d1865f563af3dae60c0f79345ffe18e21e092"]
    implementation_record_sha256: Literal[
        "a9cc993508178c15326f95a86a18d0009f7565df703ed7d3b66251be021a6679"
    ]
    request_sha256: Literal["dbd8827d8c0a19dcd7bd6c2c4717b8bd84bde98dcefd9cfb26628f7485385632"]
    notebook_sha256: Literal["92984ab474d495a443ab504f400c38782df1ee0c1d1b65646e9444b311a46dd7"]
    runtime_script_sha256: Literal[
        "72e1daad1883e4bd1456ada15e073dbb252753b166b4cc250f591f71171679a3"
    ]
    wrapper_code_sha256: Literal["cfef877ff8698f40aec1a0a4c7a6ac94e762085dfdfde88994d6da341438cd4f"]
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    wheelhouse: WheelhouseAuthority
    evidence_contract: EvidenceContractAuthority
    issued_from_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issued_at: datetime
    expires_at: datetime
    operator_confirmation_recorded: Literal[True]
    single_use: Literal[True]
    passed_failed_or_interrupted_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    budget: AuthorizationBudget
    controls: AuthorizationControls

    @field_validator("issued_at", "expires_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        maximum = timedelta(minutes=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES)
        if self.expires_at - self.issued_at > maximum:
            raise ValueError("authorization window exceeds reviewed budget")
        return self


class P3P6AuthorizationConsumption(LocalABCContract):
    """Non-overwriting terminal receipt for the single attempt."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    consumption_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-consumption-v4"
    ]
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.CONSUMED]
    consumed_at: datetime
    outcome: ExecutionOutcome
    saved_version_id: int = Field(gt=0)
    notebook_sha256: Literal["92984ab474d495a443ab504f400c38782df1ee0c1d1b65646e9444b311a46dd7"]
    runtime_script_sha256: Literal[
        "72e1daad1883e4bd1456ada15e073dbb252753b166b4cc250f591f71171679a3"
    ]
    wrapper_code_sha256: Literal["cfef877ff8698f40aec1a0a4c7a6ac94e762085dfdfde88994d6da341438cd4f"]
    authorization_reusable: Literal[False]
    next_gate: Literal["preserve_and_accept_p3_p6_runtime_diagnostic_evidence_v4"]

    @field_validator("consumed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _artifact(repo_root: Path, relative_path: Path) -> ArtifactReceipt:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ARTIFACT_UNSAFE",
            "a required authorization artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if relative_path == IMPLEMENTATION_SOURCE_PATH:
        payload = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return ArtifactReceipt(
        repository_path=relative_path.as_posix(),
        sha256=_sha256_bytes(payload),
    )


def _require_artifact(
    repo_root: Path,
    relative_path: Path,
    expected_sha256: str,
) -> ArtifactReceipt:
    receipt = _artifact(repo_root, relative_path)
    if receipt.sha256 != expected_sha256:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_IMPLEMENTATION_DRIFT",
            "a merged P3-P6 implementation artifact drifted",
            relative_path.as_posix(),
        )
    return receipt


def _read_json_object(repo_root: Path, relative_path: Path) -> dict[str, object]:
    path = repo_root / relative_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_IMPLEMENTATION_JSON_INVALID",
            "a merged P3-P6 implementation artifact is invalid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_IMPLEMENTATION_ROOT_INVALID",
            "a merged P3-P6 implementation artifact must be one object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _implementation_authority(repo_root: Path) -> ImplementationAuthority:
    record = _read_json_object(repo_root, IMPLEMENTATION_RECORD_PATH)
    request = _read_json_object(repo_root, IMPLEMENTATION_REQUEST_PATH)
    review = _read_json_object(repo_root, IMPLEMENTATION_REVIEW_PATH)
    if record.get("status") != "IMPLEMENTED_NOT_EXECUTED":
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_IMPLEMENTATION_STATE_INVALID",
            "the P3-P6 implementation is not in the reviewed pre-execution state",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    safety = record.get("safety")
    if not isinstance(safety, dict) or safety.get("runtime_execution_authorized") is not False:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_PREEXISTING_AUTHORITY",
            "the P3-P6 implementation unexpectedly reports runtime authority",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if request.get("runtime_execution_authorized") is not False:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_REQUEST_STATE_INVALID",
            "the P3-P6 request unexpectedly reports runtime authority",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    if review.get("runtime_execution_authorized") is not False:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_REVIEW_STATE_INVALID",
            "the P3-P6 architecture review unexpectedly reports runtime authority",
            IMPLEMENTATION_REVIEW_PATH.as_posix(),
        )
    if request.get("model_snapshot_sha256") != MODEL_SNAPSHOT_SHA256:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_MODEL_IDENTITY_DRIFT",
            "the P3-P6 model snapshot identity drifted",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    if record.get("authorization_issuer_included") is not False:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_IMPLEMENTATION_STATE_INVALID",
            "the V4 implementation unexpectedly includes an authorization issuer",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if request.get("authorization_issuer_included") is not False:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_REQUEST_STATE_INVALID",
            "the V4 request unexpectedly includes an authorization issuer",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    if record.get("next_gate") != ("merge_then_design_separate_p3_p6_execution_authorization_v4"):
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_IMPLEMENTATION_GATE_DRIFT",
            "the merged V4 implementation next gate drifted",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    known_failure = request.get("known_v3_failure")
    expected_failure = {
        "saved_version_id": 339943910,
        "lifecycle_outcome": "FAILED",
        "reported_failure_code": "P3_P6_EXPLICIT_BACKEND_NOT_REALIZED",
        "failed_probe": "P3",
        "runtime_install_status": "PASSED",
        "process_tree_import_closure_status": "PASSED",
        "worker_readiness_established": True,
        "served_model_inventory_established": True,
        "triton_attn_startup_selection_established": True,
        "formal_p3_acceptance_established": False,
        "evidence_disposition": "QUARANTINED_INVALID_DIAGNOSTIC",
        "first_divergence": (
            "BACKEND_MARKER_PREDICATE_INCOMPATIBLE_WITH_PINNED_VLLM_0_19_1_RUNTIME_MARKER"
        ),
        "unchanged_replay_authorized": False,
    }
    if known_failure != expected_failure:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_V3_FAILURE_CONTEXT_DRIFT",
            "the accepted V3 failure context drifted",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    evidence_contract = request.get("evidence_contract")
    expected_evidence_contract = EvidenceContractAuthority().model_dump(mode="json")
    if evidence_contract != expected_evidence_contract:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_EVIDENCE_CONTRACT_DRIFT",
            "the V4 evidence contract drifted",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    record_notebook = record.get("notebook")
    if not isinstance(record_notebook, dict):
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_NOTEBOOK_RECEIPT_INVALID",
            "the V4 notebook receipt is unavailable",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if (
        record_notebook.get("runtime_script_sha256") != IMPLEMENTATION_RUNTIME_SCRIPT_SHA256
        or record_notebook.get("wrapper_code_sha256") != IMPLEMENTATION_WRAPPER_CODE_SHA256
    ):
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_RUNTIME_SOURCE_BINDING_DRIFT",
            "the V4 runtime-script or wrapper identity drifted",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    outputs = review.get("output_contract")
    required_outputs = {
        "runtime_source_identity_report_v4.json",
        "runtime_import_closure_report_v4.json",
        "worker_teardown_report_v4.json",
        "bundle_manifest_v4.json",
    }
    if not isinstance(outputs, list) or not required_outputs.issubset(set(outputs)):
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_OUTPUT_CONTRACT_DRIFT",
            "the V4 evidence output contract is incomplete",
            IMPLEMENTATION_REVIEW_PATH.as_posix(),
        )
    return ImplementationAuthority(
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        implementation_record=_require_artifact(
            repo_root,
            IMPLEMENTATION_RECORD_PATH,
            IMPLEMENTATION_RECORD_SHA256,
        ),
        notebook=_require_artifact(
            repo_root,
            IMPLEMENTATION_NOTEBOOK_PATH,
            IMPLEMENTATION_NOTEBOOK_SHA256,
        ),
        request=_require_artifact(
            repo_root,
            IMPLEMENTATION_REQUEST_PATH,
            IMPLEMENTATION_REQUEST_SHA256,
        ),
        architecture_review=_require_artifact(
            repo_root,
            IMPLEMENTATION_REVIEW_PATH,
            IMPLEMENTATION_REVIEW_SHA256,
        ),
        template=_require_artifact(
            repo_root,
            IMPLEMENTATION_TEMPLATE_PATH,
            IMPLEMENTATION_TEMPLATE_SHA256,
        ),
        implementation_source=_require_artifact(
            repo_root,
            IMPLEMENTATION_SOURCE_PATH,
            IMPLEMENTATION_SOURCE_SHA256,
        ),
        runtime_script_sha256=IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=IMPLEMENTATION_WRAPPER_CODE_SHA256,
        evidence_contract=EvidenceContractAuthority(),
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        wheelhouse=WheelhouseAuthority(
            requirements_in_sha256=(
                "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"
            ),
            resolution_lock_sha256=(
                "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
            ),
            materialization_lock_sha256=(
                "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
            ),
            requirements_lock_sha256=(
                "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"
            ),
            install_runtime_sha256=(
                "68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"
            ),
            runtime_manifest_sha256=(
                "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
            ),
            sha256_manifest_sha256=(
                "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
            ),
            materialization_receipt_sha256=(
                "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
            ),
        ),
        runtime_execution_authorized_before_issuance=False,
        unchanged_v3_failure_replay_authorized=False,
    )


def _build_review(repo_root: Path) -> AuthorizationArchitectureReview:
    return AuthorizationArchitectureReview(
        review_id=("auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4-review"),
        status="APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION",
        decision="SEPARATE_TRANSIENT_SINGLE_USE_P3_P6_V4_AUTHORIZATION",
        implementation=_implementation_authority(repo_root),
        budget=AuthorizationBudget(),
        controls=AuthorizationControls(),
        operator_confirmation_required=True,
        authorization_must_remain_untracked=True,
        passed_failed_or_interrupted_attempt_consumes_authorization=True,
        runtime_loader_enforcement_mode=(
            "OPERATOR_GATE_BOUND_TO_EXACT_NOTEBOOK_AND_INPUT_IDENTITIES"
        ),
        authorization_issued_in_review=False,
        runtime_execution_performed=False,
        next_gate=IMPLEMENTATION_NEXT_GATE,
        non_claims=(
            "This review does not issue runtime authorization.",
            "The V4 P3-P6 notebook has not been executed.",
            "No Kaggle session or GPU action has been started.",
            "No target runtime has been installed by this authorization tranche.",
            "The accepted V3 failed lifecycle remains consumed and non-replayable.",
            "The V4 evidence-contract implementation is locally validated only.",
            "No model has been loaded.",
            "No worker has been started.",
            "No model request has been issued.",
            "No cache behavior or reset has been observed.",
            "No dual-worker isolation has been observed.",
            "No A/B/C benchmark trajectory is authorized.",
            "The notebook does not parse the transient authorization artifact.",
            "Execution remains an operator gate bound to exact identities.",
            "Deployment and production readiness are not claimed.",
        ),
    )


def _build_record(
    repo_root: Path,
    review_bytes: bytes,
) -> AuthorizationImplementationRecord:
    return AuthorizationImplementationRecord(
        record_id=("auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4-record"),
        status="P3_P6_RUNTIME_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V4_VALID",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation=_implementation_authority(repo_root),
        review=ArtifactReceipt(
            repository_path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
        ),
        issuer_source=_artifact(repo_root, ISSUER_SOURCE_PATH),
        issuer_tests=_artifact(repo_root, ISSUER_TEST_PATH),
        adr=_artifact(repo_root, ADR_PATH),
        report=_artifact(repo_root, REPORT_PATH),
        runbook=_artifact(repo_root, RUNBOOK_PATH),
        authorization_path=AUTHORIZATION_PATH.as_posix(),
        consumption_path=CONSUMPTION_PATH.as_posix(),
        authorization_issuer_implemented=True,
        authorization_issued=False,
        consumption_record_created=False,
        runtime_execution_performed=False,
        budget=AuthorizationBudget(),
        controls=AuthorizationControls(),
        next_gate=IMPLEMENTATION_NEXT_GATE,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    except OSError as error:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ATOMIC_WRITE_FAILED",
            "an authorization artifact could not be written atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _write_non_overwriting(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ALREADY_EXISTS",
            "the transient authorization artifact already exists",
            path.as_posix(),
        )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.link(temporary_path, path)
    except FileExistsError as error:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ALREADY_EXISTS",
            "the transient authorization appeared during issuance",
            path.as_posix(),
        ) from error
    except OSError as error:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ATOMIC_CREATE_FAILED",
            "the transient authorization could not be created atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def generate(repo_root: Path) -> AuthorizationImplementationRecord:
    """Generate deterministic review and implementation record only."""

    root = repo_root.resolve()
    if (root / AUTHORIZATION_PATH).exists() or (root / CONSUMPTION_PATH).exists():
        raise P3P6AuthorizationError(
            "P3_P6_TRANSIENT_AUTHORITY_PRESENT",
            "transient authorization artifacts must be absent during generation",
        )
    review = _build_review(root)
    review_bytes = review.canonical_json().encode("utf-8")
    _write_atomic(root / REVIEW_PATH, review_bytes)
    record = _build_record(root, review_bytes)
    _write_atomic(root / RECORD_PATH, record.canonical_json().encode("utf-8"))
    return record


def _validate_static_package(repo_root: Path) -> AuthorizationImplementationRecord:
    review = _build_review(repo_root)
    review_bytes = review.canonical_json().encode("utf-8")
    record = _build_record(repo_root, review_bytes)
    expected = (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record.canonical_json().encode("utf-8")),
    )
    for path, payload in expected:
        target = repo_root / path
        if not target.is_file() or target.is_symlink():
            raise P3P6AuthorizationError(
                "P3_P6_AUTHORIZATION_STATIC_ARTIFACT_UNSAFE",
                "a static authorization artifact is missing or unsafe",
                path.as_posix(),
            )
        if target.read_bytes() != payload:
            raise P3P6AuthorizationError(
                "P3_P6_AUTHORIZATION_STATIC_ARTIFACT_DRIFT",
                "a static authorization artifact differs from fresh generation",
                path.as_posix(),
            )
    return record


def validate_implementation_package(repo_root: Path) -> dict[str, object]:
    """Validate the issuer implementation without creating runtime authority."""

    root = repo_root.resolve()
    if (root / AUTHORIZATION_PATH).exists() or (root / CONSUMPTION_PATH).exists():
        raise P3P6AuthorizationError(
            "P3_P6_TRANSIENT_AUTHORITY_PRESENT",
            "transient authorization artifacts must be absent during review",
        )
    record = _validate_static_package(root)
    return {
        "status": record.status,
        "source_main_merge_commit": record.source_main_merge_commit,
        "implementation_feature_commit": (record.implementation.implementation_feature_commit),
        "notebook_sha256": record.implementation.notebook.sha256,
        "runtime_script_sha256": record.implementation.runtime_script_sha256,
        "wrapper_code_sha256": record.implementation.wrapper_code_sha256,
        "model_snapshot_sha256": record.implementation.model_snapshot_sha256,
        "authorization_issuer_implemented": True,
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "maximum_kaggle_sessions": record.budget.maximum_kaggle_sessions,
        "maximum_runtime_install_attempts": (record.budget.maximum_runtime_install_attempts),
        "maximum_runtime_import_closure_probes": (
            record.budget.maximum_runtime_import_closure_probes
        ),
        "maximum_model_loads": record.budget.maximum_model_loads,
        "maximum_worker_starts": record.budget.maximum_worker_starts,
        "maximum_model_requests": record.budget.maximum_model_requests,
        "maximum_output_tokens_per_request": (record.budget.maximum_output_tokens_per_request),
        "maximum_benchmark_trajectory_requests": 0,
        "next_gate": record.next_gate,
    }


def _run_git(repo_root: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_GIT_FAILED",
            "a required Git inspection could not be completed",
            details=tuple(arguments),
        ) from error
    if result.returncode != 0:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_GIT_FAILED",
            "a required Git inspection failed",
            details=tuple(arguments),
        )
    return result.stdout.strip()


def _require_ancestor(repo_root: Path, commit: str) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ANCESTRY_UNREADABLE",
            "authorization source ancestry could not be inspected",
            details=(commit,),
        ) from error
    if result.returncode != 0:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_SOURCE_AUTHORITY_MISSING",
            "a required merged source authority is not an ancestor of HEAD",
            details=(commit,),
        )


def _allowed_transient_status(allow_transient: bool) -> tuple[str, ...]:
    if not allow_transient:
        return ()
    return (
        f"?? {AUTHORIZATION_PATH.as_posix()}",
        f"?? {CONSUMPTION_PATH.as_posix()}",
    )


def _require_synchronized_main(repo_root: Path, *, allow_transient: bool) -> str:
    branch = _run_git(repo_root, ["branch", "--show-current"])
    if branch != "main":
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_MAIN_REQUIRED",
            "authorization lifecycle operations require branch main",
            details=(branch,),
        )
    head = _run_git(repo_root, ["rev-parse", "HEAD"])
    origin_main = _run_git(repo_root, ["rev-parse", "origin/main"])
    if head != origin_main:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "local main and origin/main are not synchronized",
        )
    status = tuple(
        line
        for line in _run_git(
            repo_root,
            ["status", "--porcelain=v1", "--untracked-files=all"],
        ).splitlines()
        if line
    )
    allowed = set(_allowed_transient_status(allow_transient))
    unexpected = tuple(sorted(line for line in status if line not in allowed))
    if unexpected:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
            "the repository contains changes outside transient authorization files",
            details=unexpected,
        )
    return head


def _require_transient_paths_untracked(repo_root: Path) -> None:
    tracked = _run_git(
        repo_root,
        [
            "ls-files",
            "--",
            AUTHORIZATION_PATH.as_posix(),
            CONSUMPTION_PATH.as_posix(),
        ],
    )
    if tracked:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_MUST_REMAIN_UNTRACKED",
            "transient authorization artifacts must never be tracked",
            details=tuple(tracked.splitlines()),
        )


def _require_source_authority(repo_root: Path) -> None:
    _require_ancestor(repo_root, SOURCE_MAIN_MERGE_COMMIT)
    _require_ancestor(repo_root, IMPLEMENTATION_FEATURE_COMMIT)


def _build_authorization(
    *,
    repo_root: Path,
    issuer_head: str,
    confirmation: AuthorizationIssuanceConfirmation,
) -> P3P6ExecutionAuthorization:
    _validate_static_package(repo_root)
    confirmation_checks = (
        confirmation.confirmed_scope == AUTHORIZATION_SCOPE,
        confirmation.confirmed_notebook_sha256 == IMPLEMENTATION_NOTEBOOK_SHA256,
        confirmation.confirmed_runtime_script_sha256 == IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        confirmation.confirmed_wrapper_code_sha256 == IMPLEMENTATION_WRAPPER_CODE_SHA256,
        confirmation.confirmed_model_snapshot_sha256 == MODEL_SNAPSHOT_SHA256,
        confirmation.confirmed_backend == SELECTED_BACKEND,
    )
    if not all(confirmation_checks):
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_CONFIRMATION_BINDING_DRIFT",
            "operator confirmation does not bind the reviewed V4 identities",
        )
    issued_at = confirmation.confirmed_at
    return P3P6ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=AuthorizationLifecycle.ISSUED,
        scope=AUTHORIZATION_SCOPE,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        implementation_record_sha256=IMPLEMENTATION_RECORD_SHA256,
        request_sha256=IMPLEMENTATION_REQUEST_SHA256,
        notebook_sha256=IMPLEMENTATION_NOTEBOOK_SHA256,
        runtime_script_sha256=IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=IMPLEMENTATION_WRAPPER_CODE_SHA256,
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        wheelhouse=WheelhouseAuthority(
            requirements_in_sha256=(
                "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"
            ),
            resolution_lock_sha256=(
                "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
            ),
            materialization_lock_sha256=(
                "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
            ),
            requirements_lock_sha256=(
                "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"
            ),
            install_runtime_sha256=(
                "68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"
            ),
            runtime_manifest_sha256=(
                "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
            ),
            sha256_manifest_sha256=(
                "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
            ),
            materialization_receipt_sha256=(
                "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
            ),
        ),
        evidence_contract=EvidenceContractAuthority(),
        issued_from_main_commit=issuer_head,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(minutes=confirmation.authorization_window_minutes),
        operator_confirmation_recorded=True,
        single_use=True,
        passed_failed_or_interrupted_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        budget=AuthorizationBudget(),
        controls=AuthorizationControls(),
    )


def issue_authorization(
    *,
    repo_root: Path,
    confirmation: AuthorizationIssuanceConfirmation,
) -> dict[str, object]:
    """Issue one transient, non-overwriting authority after explicit confirmation."""

    root = repo_root.resolve()
    issuer_head = _require_synchronized_main(root, allow_transient=False)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    if (root / CONSUMPTION_PATH).exists():
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ALREADY_CONSUMED",
            "a prior P3-P6 authorization consumption receipt already exists",
            CONSUMPTION_PATH.as_posix(),
        )
    authorization = _build_authorization(
        repo_root=root,
        issuer_head=issuer_head,
        confirmation=confirmation,
    )
    payload = authorization.canonical_json().encode("utf-8")
    _write_non_overwriting(root / AUTHORIZATION_PATH, payload)
    return {
        "status": "P3_P6_RUNTIME_DIAGNOSTIC_EXECUTION_AUTHORIZATION_ISSUED",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": _sha256_bytes(payload),
        "issued_from_main_commit": authorization.issued_from_main_commit,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "notebook_sha256": authorization.notebook_sha256,
        "runtime_script_sha256": authorization.runtime_script_sha256,
        "wrapper_code_sha256": authorization.wrapper_code_sha256,
        "model_snapshot_sha256": authorization.model_snapshot_sha256,
        "single_use": True,
        "maximum_kaggle_sessions": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_model_loads": 3,
        "maximum_worker_starts": 3,
        "maximum_model_requests": 5,
        "maximum_output_tokens_per_request": 32,
        "maximum_benchmark_trajectory_requests": 0,
        "next_gate": ISSUED_NEXT_GATE,
    }


def _load_canonical(
    path: Path,
    model: type[LocalABCContract],
) -> LocalABCContract:
    try:
        observed = path.read_text(encoding="utf-8")
        contract = model.model_validate_json(observed)
    except (OSError, ValidationError) as error:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_PAYLOAD_INVALID",
            "an authorization payload failed strict validation",
            path.as_posix(),
        ) from error
    if observed != contract.canonical_json():
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_PAYLOAD_NOT_CANONICAL",
            "an authorization payload is not canonical JSON",
            path.as_posix(),
        )
    return contract


def _validate_authorization_bindings(
    authorization: P3P6ExecutionAuthorization,
) -> None:
    checks = (
        authorization.authorization_id == AUTHORIZATION_ID,
        authorization.scope == AUTHORIZATION_SCOPE,
        authorization.source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT,
        authorization.implementation_feature_commit == IMPLEMENTATION_FEATURE_COMMIT,
        authorization.implementation_record_sha256 == IMPLEMENTATION_RECORD_SHA256,
        authorization.request_sha256 == IMPLEMENTATION_REQUEST_SHA256,
        authorization.notebook_sha256 == IMPLEMENTATION_NOTEBOOK_SHA256,
        authorization.runtime_script_sha256 == IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        authorization.wrapper_code_sha256 == IMPLEMENTATION_WRAPPER_CODE_SHA256,
        authorization.model_snapshot_sha256 == MODEL_SNAPSHOT_SHA256,
        authorization.evidence_contract == EvidenceContractAuthority(),
        authorization.operator_confirmation_recorded is True,
        authorization.single_use is True,
        authorization.passed_failed_or_interrupted_attempt_consumes_authorization is True,
        authorization.unchanged_replay_authorized is False,
        authorization.wheelhouse
        == WheelhouseAuthority(
            requirements_in_sha256=(
                "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"
            ),
            resolution_lock_sha256=(
                "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
            ),
            materialization_lock_sha256=(
                "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
            ),
            requirements_lock_sha256=(
                "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"
            ),
            install_runtime_sha256=(
                "68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"
            ),
            runtime_manifest_sha256=(
                "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
            ),
            sha256_manifest_sha256=(
                "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
            ),
            materialization_receipt_sha256=(
                "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
            ),
        ),
        authorization.budget == AuthorizationBudget(),
        authorization.controls == AuthorizationControls(),
    )
    if not all(checks):
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_BINDING_DRIFT",
            "the transient authorization no longer binds the reviewed inputs",
            AUTHORIZATION_PATH.as_posix(),
        )


def verify_authorization(
    *,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify one live authority immediately before governed execution."""

    root = repo_root.resolve()
    issuer_head = _require_synchronized_main(root, allow_transient=True)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    _validate_static_package(root)
    if (root / CONSUMPTION_PATH).exists():
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ALREADY_CONSUMED",
            "the authorization has a consumption receipt and is not reusable",
            CONSUMPTION_PATH.as_posix(),
        )
    loaded = _load_canonical(root / AUTHORIZATION_PATH, P3P6ExecutionAuthorization)
    authorization = cast(P3P6ExecutionAuthorization, loaded)
    _validate_authorization_bindings(authorization)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if not authorization.issued_at <= observed_now < authorization.expires_at:
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_EXPIRED",
            "the transient authorization is outside its validity window",
            AUTHORIZATION_PATH.as_posix(),
        )
    return {
        "status": "P3_P6_RUNTIME_DIAGNOSTIC_EXECUTION_AUTHORIZATION_VALID",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": authorization.fingerprint(),
        "issuer_head_commit": issuer_head,
        "issued_from_main_commit": authorization.issued_from_main_commit,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "notebook_sha256": authorization.notebook_sha256,
        "runtime_script_sha256": authorization.runtime_script_sha256,
        "wrapper_code_sha256": authorization.wrapper_code_sha256,
        "model_snapshot_sha256": authorization.model_snapshot_sha256,
        "single_use": True,
        "consumed": False,
        "maximum_kaggle_sessions": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_model_loads": 3,
        "maximum_worker_starts": 3,
        "maximum_model_requests": 5,
        "maximum_output_tokens_per_request": 32,
        "maximum_benchmark_trajectory_requests": 0,
        "next_gate": ISSUED_NEXT_GATE,
    }


def consume_authorization(
    *,
    repo_root: Path,
    outcome: ExecutionOutcome,
    saved_version_id: int,
    consumed_at: datetime | None = None,
) -> dict[str, object]:
    """Create one non-overwriting receipt after the single execution attempt."""

    root = repo_root.resolve()
    _require_synchronized_main(root, allow_transient=True)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    if (root / CONSUMPTION_PATH).exists():
        raise P3P6AuthorizationError(
            "P3_P6_AUTHORIZATION_ALREADY_CONSUMED",
            "the authorization consumption receipt already exists",
            CONSUMPTION_PATH.as_posix(),
        )
    loaded = _load_canonical(root / AUTHORIZATION_PATH, P3P6ExecutionAuthorization)
    authorization = cast(P3P6ExecutionAuthorization, loaded)
    _validate_authorization_bindings(authorization)
    authorization_payload = authorization.canonical_json().encode("utf-8")
    receipt = P3P6AuthorizationConsumption(
        consumption_id=(
            "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-consumption-v4"
        ),
        authorization_id=AUTHORIZATION_ID,
        authorization_sha256=_sha256_bytes(authorization_payload),
        lifecycle=AuthorizationLifecycle.CONSUMED,
        consumed_at=(consumed_at or datetime.now(UTC)).astimezone(UTC),
        outcome=outcome,
        saved_version_id=saved_version_id,
        notebook_sha256=IMPLEMENTATION_NOTEBOOK_SHA256,
        runtime_script_sha256=IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=IMPLEMENTATION_WRAPPER_CODE_SHA256,
        authorization_reusable=False,
        next_gate=CONSUMED_NEXT_GATE,
    )
    payload = receipt.canonical_json().encode("utf-8")
    _write_non_overwriting(root / CONSUMPTION_PATH, payload)
    return {
        "status": "P3_P6_RUNTIME_DIAGNOSTIC_EXECUTION_AUTHORIZATION_CONSUMED",
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": receipt.authorization_sha256,
        "consumption_path": CONSUMPTION_PATH.as_posix(),
        "consumption_sha256": _sha256_bytes(payload),
        "outcome": receipt.outcome.value,
        "saved_version_id": receipt.saved_version_id,
        "authorization_reusable": False,
        "next_gate": receipt.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-p3-p6-authorization-v4")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("generate", "validate-implementation", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)

    issue_parser = subparsers.add_parser("issue")
    issue_parser.add_argument("--repo-root", type=Path, required=True)
    issue_parser.add_argument("--operator-confirm", action="store_true")
    issue_parser.add_argument("--window-minutes", type=int, default=240)
    issue_parser.add_argument("--confirm-scope", required=True)
    issue_parser.add_argument("--confirm-notebook-sha256", required=True)
    issue_parser.add_argument("--confirm-runtime-script-sha256", required=True)
    issue_parser.add_argument("--confirm-wrapper-code-sha256", required=True)
    issue_parser.add_argument("--confirm-model-snapshot-sha256", required=True)
    issue_parser.add_argument("--confirm-backend", required=True)

    consume_parser = subparsers.add_parser("consume")
    consume_parser.add_argument("--repo-root", type=Path, required=True)
    consume_parser.add_argument("--operator-confirm", action="store_true")
    consume_parser.add_argument(
        "--outcome",
        choices=tuple(item.value for item in ExecutionOutcome),
        required=True,
    )
    consume_parser.add_argument("--saved-version-id", type=int, required=True)
    return parser


def _error_json(error: P3P6AuthorizationError) -> str:
    return AuthorizationErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).canonical_json()


def main(argv: list[str] | None = None) -> int:
    """Run one repository-only authorization lifecycle command."""

    try:
        arguments = _build_parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            record = generate(repo_root)
            summary: dict[str, object] = {
                "status": record.status,
                "authorization_issued": False,
                "runtime_execution_performed": False,
                "next_gate": record.next_gate,
            }
        elif arguments.command == "validate-implementation":
            summary = validate_implementation_package(repo_root)
        elif arguments.command == "issue":
            if arguments.operator_confirm is not True:
                raise P3P6AuthorizationError(
                    "P3_P6_OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required for issuance",
                )
            confirmation = AuthorizationIssuanceConfirmation(
                confirmation_id=(
                    "auragateway-cu129-p3-p6-runtime-diagnostic-"
                    "execution-authorization-confirmation-v4"
                ),
                operator_confirmed=True,
                confirmed_at=datetime.now(UTC),
                authorization_window_minutes=cast(int, arguments.window_minutes),
                confirmed_scope=cast(str, arguments.confirm_scope),
                confirmed_notebook_sha256=cast(
                    str,
                    arguments.confirm_notebook_sha256,
                ),
                confirmed_runtime_script_sha256=cast(
                    str,
                    arguments.confirm_runtime_script_sha256,
                ),
                confirmed_wrapper_code_sha256=cast(
                    str,
                    arguments.confirm_wrapper_code_sha256,
                ),
                confirmed_model_snapshot_sha256=cast(
                    str,
                    arguments.confirm_model_snapshot_sha256,
                ),
                confirmed_backend=cast(str, arguments.confirm_backend),
            )
            summary = issue_authorization(
                repo_root=repo_root,
                confirmation=confirmation,
            )
        elif arguments.command == "verify":
            summary = verify_authorization(repo_root=repo_root)
        elif arguments.command == "consume":
            if arguments.operator_confirm is not True:
                raise P3P6AuthorizationError(
                    "P3_P6_OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required for consumption",
                )
            summary = consume_authorization(
                repo_root=repo_root,
                outcome=ExecutionOutcome(cast(str, arguments.outcome)),
                saved_version_id=cast(int, arguments.saved_version_id),
            )
        else:
            raise P3P6AuthorizationError(
                "P3_P6_AUTHORIZATION_COMMAND_UNSUPPORTED",
                "the authorization command is unsupported",
            )
        print(json.dumps(summary, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
        return 0
    except (P3P6AuthorizationError, ValidationError, ValueError, OSError) as error:
        if isinstance(error, P3P6AuthorizationError):
            output = _error_json(error)
        else:
            output = AuthorizationErrorEnvelope(
                error_code="P3_P6_AUTHORIZATION_UNEXPECTED",
                safe_message=str(error),
            ).canonical_json()
        print(output, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
