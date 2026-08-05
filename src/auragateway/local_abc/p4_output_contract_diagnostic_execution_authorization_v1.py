"""Implement, issue, verify, and consume one P4 diagnostic authorization."""

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

from auragateway.local_abc.contracts import LocalABCContract

ORIGINAL_IMPLEMENTATION_MERGE_COMMIT: Final = "3ab50e7a1e2661c5967ba91501c51afe96b58864"
EVIDENCE_CONTRACT_FEATURE_COMMIT: Final = "e60b59e40fc756e51a58617d4d47cbb85d37dc7b"
EVIDENCE_CONTRACT_MERGE_COMMIT: Final = "e13882628559ec0f8f3364cc27ce574cbdd92806"
TERMINAL_CLOSURE_FEATURE_COMMIT: Final = "d85cc387344164034e30fe57752e4f04f4d10cdd"
TERMINAL_CLOSURE_MERGE_COMMIT: Final = "5c1654c78ce398591043960fb28e5e1f03f3cc34"
SOURCE_MAIN_MERGE_COMMIT: Final = TERMINAL_CLOSURE_MERGE_COMMIT
IMPLEMENTATION_SOURCE_MAIN_COMMIT: Final = "e13882628559ec0f8f3364cc27ce574cbdd92806"

IMPLEMENTATION_RECORD_SHA256: Final = (
    "3f7adc15e26acf16861b1095ab6a1f4d8dd22f0a6332cc3585b14df75d6c9d60"
)
IMPLEMENTATION_NOTEBOOK_SHA256: Final = (
    "70a8c1e535b9372b86573ab9680d9a56d21fc3daecf6699dceae13dab4f102b4"
)
IMPLEMENTATION_RUNTIME_SCRIPT_SHA256: Final = (
    "3c099830ea27da4c37e7a5a8afeb088b58184dbacda8d866be65d86115bdfbd1"
)
IMPLEMENTATION_WRAPPER_CODE_SHA256: Final = (
    "0268570106cf5fa06da6304a9236fa4f32850f8ddb78b54c67f93faf440620dc"
)
IMPLEMENTATION_REQUEST_SHA256: Final = (
    "b5e87cf55241a710111668f4fa06b08bd6fa36975c24efa59f79601aa4bd1632"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "7886cce4f9aea0be34094a3c746bc3c8eb2ae6c33f8deeea3db262c4f39ea309"
)
IMPLEMENTATION_SOURCE_SHA256: Final = (
    "ed205f8f0bfb6eff68e6dcb8f4ec616cbd2af6fb1cca78a8faa4cd19b86a0452"
)
IMPLEMENTATION_TEMPLATE_SHA256: Final = (
    "ff689398ea41954520ef3f7441362e2f04f352207bc0d4c8f72f21e98bcbbb0b"
)
IMPLEMENTATION_TESTS_SHA256: Final = (
    "30acdc42e0bba49eb04fa7518292c5cc9af8b48957a8b6a31ef0a7f2e14665aa"
)
IMPLEMENTATION_ADR_SHA256: Final = (
    "8f018022c80111b2c0505d0b9405c833a7fc2b1f331048726706e1bbb92468e8"
)
IMPLEMENTATION_REPORT_SHA256: Final = (
    "70f3763b77ee4fbe27e467c36f46119426fc5c2280f513e5b30b280cec644485"
)
IMPLEMENTATION_RUNBOOK_SHA256: Final = (
    "a49608c4b8c7666087fb93c64532b6a54317ba1f19b37838f0018015d9af1066"
)
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"

IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v1_record.json"
)
IMPLEMENTATION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p4_output_contract_diagnostic_v1.ipynb"
)
IMPLEMENTATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p4_output_contract_diagnostic_v1_request.json"
)
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v1_review.json"
)
IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_output_contract_diagnostic_v1.py"
)
IMPLEMENTATION_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v1.py.tmpl"
)
IMPLEMENTATION_TESTS_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_output_contract_diagnostic_v1.py"
)
IMPLEMENTATION_ADR_PATH: Final = Path(
    "docs/adr/2026-08-05-local-abc-p4-output-contract-diagnostic-v1.md"
)
IMPLEMENTATION_REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_Output_Contract_Diagnostic_V1.md"
)
IMPLEMENTATION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p4_output_contract_diagnostic_v1.md"
)

ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_output_contract_diagnostic_execution_authorization_v1.py"
)
ISSUER_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_output_contract_diagnostic_execution_authorization_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-05-local-abc-p4-output-contract-diagnostic-execution-authorization-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_Output_Contract_Diagnostic_Execution_Authorization_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p4_output_contract_diagnostic_execution_authorization_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_authorization_v1_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_execution_authorization_v1.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_authorization_consumption_v1.json"
)

AUTHORIZATION_ID: Final = "auragateway-p4-output-contract-diagnostic-execution-authorization-v1"
AUTHORIZATION_SCOPE: Final = "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1"
SELECTED_BACKEND: Final = "TRITON_ATTN"
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
IMPLEMENTATION_NEXT_GATE: Final = (
    "explicit_operator_confirmation_then_issue_p4_output_contract_"
    "diagnostic_execution_authorization_v1"
)
ISSUED_NEXT_GATE: Final = "execute_governed_p4_output_contract_diagnostic_v1"
CONSUMED_NEXT_GATE: Final = "preserve_and_classify_p4_output_contract_diagnostic_v1"

EXPECTED_RUNTIME_OUTPUTS: Final = (
    "runtime_source_identity_report_v1.json",
    "model_snapshot_report_v1.json",
    "wheelhouse_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "worker_startup_report_v1.json",
    "request_results_v1.json",
    "case_metrics_v1.json",
    "selection_report_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "p4_output_contract_diagnostic_summary_v1.json",
    "failure_report_v1.json",
    "bundle_manifest_v1.json",
    "human_report_v1.md",
    "ag-p4-output-contract-evidence-v1.zip",
)


class AuthorizationLifecycle(StrEnum):
    """Lifecycle states for one transient single-use authority."""

    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"


class ExecutionOutcome(StrEnum):
    """Terminal outcome recorded after the governed attempt."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class P4AuthorizationError(RuntimeError):
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ARGUMENT_INVALID",
            "P4 authorization arguments are invalid",
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


class ExecutionBudget(LocalABCContract):
    """Hard action ceiling for one P4 diagnostic execution."""

    maximum_authorization_window_minutes: Literal[240] = 240
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[1] = 1
    maximum_worker_starts: Literal[1] = 1
    maximum_model_requests: Literal[18] = 18
    maximum_output_tokens_per_request: Literal[32] = 32
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_hidden_retries: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class AuthorizationControls(LocalABCContract):
    """Fail-closed execution, evidence, and privacy controls."""

    accelerator: Literal["T4_X1"] = "T4_X1"
    internet_enabled: Literal[False] = False
    external_network_access_permitted: Literal[False] = False
    loopback_http_permitted: Literal[True] = True
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False
    raw_worker_logs_in_evidence_zip_permitted: Literal[False] = False
    explicit_backend_required: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    automatic_backend_selection_permitted: Literal[False] = False
    silent_backend_fallback_permitted: Literal[False] = False
    exact_backend_marker_required: Literal[True] = True
    one_runtime_install_required: Literal[True] = True
    one_import_closure_probe_required: Literal[True] = True
    one_model_load_required: Literal[True] = True
    one_worker_start_required: Literal[True] = True
    exact_request_schedule_required: Literal[True] = True
    balanced_six_case_matrix_required: Literal[True] = True
    three_repetitions_per_case_required: Literal[True] = True
    content_invalid_request_is_fatal: Literal[False] = False
    schema_rejected_request_is_fatal: Literal[False] = False
    infrastructure_or_transport_failure_is_fatal: Literal[True] = True
    deterministic_failure_report_required: Literal[True] = True
    success_failure_report_status: Literal["NOT_APPLICABLE"] = "NOT_APPLICABLE"
    failed_failure_report_status: Literal["FAILED"] = "FAILED"
    expected_runtime_output_count: Literal[16] = 16
    expected_pre_manifest_output_count: Literal[14] = 14
    expected_pre_archive_output_count: Literal[15] = 15
    output_contract_parity_required: Literal[True] = True
    worker_teardown_report_required: Literal[True] = True
    capture_threads_finalized_required: Literal[True] = True
    scratch_cleanup_report_required: Literal[True] = True
    evidence_zip_required: Literal[True] = True
    runtime_source_identity_report_required: Literal[True] = True
    model_snapshot_report_required: Literal[True] = True
    wheelhouse_report_required: Literal[True] = True
    runtime_install_report_required: Literal[True] = True
    runtime_import_closure_report_required: Literal[True] = True
    request_results_report_required: Literal[True] = True
    case_metrics_report_required: Literal[True] = True
    selection_report_required: Literal[True] = True
    terminal_path_output_contract_required: Literal[True] = True
    not_run_stage_reports_required: Literal[True] = True
    partial_request_evidence_required: Literal[True] = True
    partial_evidence_selection_ineligible_required: Literal[True] = True
    startup_failure_teardown_required: Literal[True] = True
    surviving_capture_threads_are_fatal: Literal[True] = True
    residual_worker_process_is_fatal: Literal[True] = True
    scratch_cleanup_failure_is_fatal: Literal[True] = True
    pre_manifest_output_completeness_gate_required: Literal[True] = True
    pre_archive_output_completeness_gate_required: Literal[True] = True
    measured_abc_execution_authorized: Literal[False] = False


class TerminalEvidenceAuthority(LocalABCContract):
    """Executable proof that ordinary terminal paths realize the contract."""

    canonical_output_contract: Literal[True] = True
    initialize_not_run_reports: Literal[True] = True
    partial_request_evidence: Literal[True] = True
    partial_selection_ineligible: Literal[True] = True
    startup_failure_teardown: Literal[True] = True
    teardown_failure_terminalized: Literal[True] = True
    cleanup_failure_terminalized: Literal[True] = True
    pre_manifest_output_completeness_gate: Literal[True] = True
    pre_archive_output_completeness_gate: Literal[True] = True
    synthetic_failure_regression: Literal[True] = True


class ImplementationAuthority(LocalABCContract):
    """Exact merged P4 implementation and remediation binding."""

    original_implementation_merge_commit: Literal["3ab50e7a1e2661c5967ba91501c51afe96b58864"]
    evidence_contract_feature_commit: Literal["e60b59e40fc756e51a58617d4d47cbb85d37dc7b"]
    evidence_contract_merge_commit: Literal["e13882628559ec0f8f3364cc27ce574cbdd92806"]
    terminal_closure_feature_commit: Literal["d85cc387344164034e30fe57752e4f04f4d10cdd"]
    terminal_closure_merge_commit: Literal["5c1654c78ce398591043960fb28e5e1f03f3cc34"]
    source_main_merge_commit: Literal["5c1654c78ce398591043960fb28e5e1f03f3cc34"]
    implementation_source_main_commit: Literal["e13882628559ec0f8f3364cc27ce574cbdd92806"]
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    implementation_record: ArtifactReceipt
    notebook: ArtifactReceipt
    request: ArtifactReceipt
    architecture_review: ArtifactReceipt
    implementation_source: ArtifactReceipt
    template: ArtifactReceipt
    implementation_tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    runtime_script_sha256: Literal[
        "3c099830ea27da4c37e7a5a8afeb088b58184dbacda8d866be65d86115bdfbd1"
    ]
    wrapper_code_sha256: Literal["0268570106cf5fa06da6304a9236fa4f32850f8ddb78b54c67f93faf440620dc"]
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    wheelhouse: WheelhouseAuthority
    expected_runtime_outputs: tuple[str, ...]
    terminal_evidence: TerminalEvidenceAuthority
    execution_budget: ExecutionBudget
    controls: AuthorizationControls
    runtime_execution_authorized_before_issuance: Literal[False]
    authorization_issuer_included_before_issuance: Literal[False]
    measured_abc_execution_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_exact_bindings(self) -> Self:
        expected = {
            IMPLEMENTATION_RECORD_PATH.as_posix(): IMPLEMENTATION_RECORD_SHA256,
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(): IMPLEMENTATION_NOTEBOOK_SHA256,
            IMPLEMENTATION_REQUEST_PATH.as_posix(): IMPLEMENTATION_REQUEST_SHA256,
            IMPLEMENTATION_REVIEW_PATH.as_posix(): IMPLEMENTATION_REVIEW_SHA256,
            IMPLEMENTATION_SOURCE_PATH.as_posix(): IMPLEMENTATION_SOURCE_SHA256,
            IMPLEMENTATION_TEMPLATE_PATH.as_posix(): IMPLEMENTATION_TEMPLATE_SHA256,
            IMPLEMENTATION_TESTS_PATH.as_posix(): IMPLEMENTATION_TESTS_SHA256,
            IMPLEMENTATION_ADR_PATH.as_posix(): IMPLEMENTATION_ADR_SHA256,
            IMPLEMENTATION_REPORT_PATH.as_posix(): IMPLEMENTATION_REPORT_SHA256,
            IMPLEMENTATION_RUNBOOK_PATH.as_posix(): IMPLEMENTATION_RUNBOOK_SHA256,
        }
        observed = {
            self.implementation_record.repository_path: self.implementation_record.sha256,
            self.notebook.repository_path: self.notebook.sha256,
            self.request.repository_path: self.request.sha256,
            self.architecture_review.repository_path: self.architecture_review.sha256,
            self.implementation_source.repository_path: self.implementation_source.sha256,
            self.template.repository_path: self.template.sha256,
            self.implementation_tests.repository_path: self.implementation_tests.sha256,
            self.adr.repository_path: self.adr.sha256,
            self.report.repository_path: self.report.sha256,
            self.runbook.repository_path: self.runbook.sha256,
        }
        if observed != expected:
            raise ValueError("merged P4 implementation bindings drifted")
        if self.expected_runtime_outputs != EXPECTED_RUNTIME_OUTPUTS:
            raise ValueError("P4 expected runtime output contract drifted")
        if self.terminal_evidence != TerminalEvidenceAuthority():
            raise ValueError("P4 terminal-evidence authority drifted")
        if self.terminal_closure_merge_commit != self.source_main_merge_commit:
            raise ValueError("P4 terminal-closure source authority drifted")
        return self


class AuthorizationArchitectureReview(LocalABCContract):
    """Deterministic decision to implement but not issue runtime authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v1-review"
    ]
    status: Literal["APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION"]
    decision: Literal["SEPARATE_TRANSIENT_SINGLE_USE_P4_DIAGNOSTIC_AUTHORIZATION"]
    implementation: ImplementationAuthority
    budget: ExecutionBudget
    controls: AuthorizationControls
    operator_confirmation_required: Literal[True]
    authorization_must_remain_untracked: Literal[True]
    passed_failed_or_interrupted_attempt_consumes_authorization: Literal[True]
    runtime_loader_enforcement_mode: Literal[
        "OPERATOR_GATE_BOUND_TO_EXACT_NOTEBOOK_AND_INPUT_IDENTITIES"
    ]
    authorization_issued_in_review: Literal[False]
    runtime_execution_performed: Literal[False]
    next_gate: Literal[
        "explicit_operator_confirmation_then_issue_p4_output_contract_"
        "diagnostic_execution_authorization_v1"
    ]
    non_claims: tuple[str, ...] = Field(min_length=10)


class AuthorizationImplementationRecord(LocalABCContract):
    """Repository receipt for the issuer implementation only."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v1-record"
    ]
    status: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V1_VALID"]
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
    budget: ExecutionBudget
    controls: AuthorizationControls
    next_gate: Literal[
        "explicit_operator_confirmation_then_issue_p4_output_contract_"
        "diagnostic_execution_authorization_v1"
    ]


class AuthorizationIssuanceConfirmation(LocalABCContract):
    """Explicit operator confirmation required before transient issuance."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    confirmation_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-confirmation-v1"
    ]
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=240)
    confirmed_scope: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1"]
    confirmed_source_main_merge_commit: Literal["5c1654c78ce398591043960fb28e5e1f03f3cc34"]
    confirmed_terminal_closure_feature_commit: Literal["d85cc387344164034e30fe57752e4f04f4d10cdd"]
    confirmed_notebook_sha256: Literal[
        "70a8c1e535b9372b86573ab9680d9a56d21fc3daecf6699dceae13dab4f102b4"
    ]
    confirmed_runtime_script_sha256: Literal[
        "3c099830ea27da4c37e7a5a8afeb088b58184dbacda8d866be65d86115bdfbd1"
    ]
    confirmed_wrapper_code_sha256: Literal[
        "0268570106cf5fa06da6304a9236fa4f32850f8ddb78b54c67f93faf440620dc"
    ]
    confirmed_request_sha256: Literal[
        "b5e87cf55241a710111668f4fa06b08bd6fa36975c24efa59f79601aa4bd1632"
    ]
    confirmed_implementation_record_sha256: Literal[
        "3f7adc15e26acf16861b1095ab6a1f4d8dd22f0a6332cc3585b14df75d6c9d60"
    ]
    confirmed_model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    confirmed_backend: Literal["TRITON_ATTN"]
    confirmed_model_request_budget: Literal[18]
    confirmed_runtime_output_count: Literal[16]
    confirmed_terminal_path_output_contract_complete: Literal[True]

    @field_validator("confirmed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("confirmed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


class P4ExecutionAuthorization(LocalABCContract):
    """Transient single-use runtime authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v1"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal[AuthorizationLifecycle.ISSUED]
    scope: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1"]
    original_implementation_merge_commit: Literal["3ab50e7a1e2661c5967ba91501c51afe96b58864"]
    evidence_contract_feature_commit: Literal["e60b59e40fc756e51a58617d4d47cbb85d37dc7b"]
    evidence_contract_merge_commit: Literal["e13882628559ec0f8f3364cc27ce574cbdd92806"]
    terminal_closure_feature_commit: Literal["d85cc387344164034e30fe57752e4f04f4d10cdd"]
    terminal_closure_merge_commit: Literal["5c1654c78ce398591043960fb28e5e1f03f3cc34"]
    source_main_merge_commit: Literal["5c1654c78ce398591043960fb28e5e1f03f3cc34"]
    implementation_record_sha256: Literal[
        "3f7adc15e26acf16861b1095ab6a1f4d8dd22f0a6332cc3585b14df75d6c9d60"
    ]
    request_sha256: Literal["b5e87cf55241a710111668f4fa06b08bd6fa36975c24efa59f79601aa4bd1632"]
    notebook_sha256: Literal["70a8c1e535b9372b86573ab9680d9a56d21fc3daecf6699dceae13dab4f102b4"]
    runtime_script_sha256: Literal[
        "3c099830ea27da4c37e7a5a8afeb088b58184dbacda8d866be65d86115bdfbd1"
    ]
    wrapper_code_sha256: Literal["0268570106cf5fa06da6304a9236fa4f32850f8ddb78b54c67f93faf440620dc"]
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    wheelhouse: WheelhouseAuthority
    expected_runtime_outputs: tuple[str, ...]
    terminal_evidence: TerminalEvidenceAuthority
    issued_from_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issued_at: datetime
    expires_at: datetime
    operator_confirmation_recorded: Literal[True]
    single_use: Literal[True]
    passed_failed_or_interrupted_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    budget: ExecutionBudget
    controls: AuthorizationControls

    @field_validator("issued_at", "expires_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def validate_window_and_outputs(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        maximum = timedelta(minutes=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES)
        if self.expires_at - self.issued_at > maximum:
            raise ValueError("authorization window exceeds reviewed budget")
        if self.expected_runtime_outputs != EXPECTED_RUNTIME_OUTPUTS:
            raise ValueError("authorization output contract drifted")
        if self.terminal_evidence != TerminalEvidenceAuthority():
            raise ValueError("authorization terminal-evidence contract drifted")
        return self


class P4AuthorizationConsumption(LocalABCContract):
    """Non-overwriting terminal receipt for the single attempt."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    consumption_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-consumption-v1"
    ]
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v1"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.CONSUMED]
    consumed_at: datetime
    outcome: ExecutionOutcome
    saved_version_id: int = Field(gt=0)
    notebook_sha256: Literal["70a8c1e535b9372b86573ab9680d9a56d21fc3daecf6699dceae13dab4f102b4"]
    runtime_script_sha256: Literal[
        "3c099830ea27da4c37e7a5a8afeb088b58184dbacda8d866be65d86115bdfbd1"
    ]
    wrapper_code_sha256: Literal["0268570106cf5fa06da6304a9236fa4f32850f8ddb78b54c67f93faf440620dc"]
    authorization_reusable: Literal[False]
    next_gate: Literal["preserve_and_classify_p4_output_contract_diagnostic_v1"]

    @field_validator("consumed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_lf(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _git_blob(repo_root: Path, commit: str, relative_path: Path) -> bytes:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "show",
                f"{commit}:{relative_path.as_posix()}",
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_GIT_BLOB_UNREADABLE",
            "a required implementation artifact could not be read from Git",
            relative_path.as_posix(),
        ) from error
    if result.returncode != 0:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_GIT_BLOB_MISSING",
            "a required implementation artifact is absent from source authority",
            relative_path.as_posix(),
        )
    return result.stdout


def _implementation_artifact(
    repo_root: Path,
    relative_path: Path,
    expected_sha256: str,
) -> ArtifactReceipt:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_IMPLEMENTATION_ARTIFACT_UNSAFE",
            "a required P4 implementation artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    authority_payload = _canonical_lf(_git_blob(repo_root, SOURCE_MAIN_MERGE_COMMIT, relative_path))
    working_payload = _canonical_lf(path.read_bytes())
    if working_payload != authority_payload:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_IMPLEMENTATION_WORKTREE_DRIFT",
            "a P4 implementation artifact differs from merged authority",
            relative_path.as_posix(),
        )
    observed_sha256 = _sha256_bytes(authority_payload)
    if observed_sha256 != expected_sha256:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_IMPLEMENTATION_IDENTITY_DRIFT",
            "a merged P4 implementation identity drifted",
            relative_path.as_posix(),
        )
    return ArtifactReceipt(
        repository_path=relative_path.as_posix(),
        sha256=observed_sha256,
    )


def _issuer_artifact(repo_root: Path, relative_path: Path) -> ArtifactReceipt:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ISSUER_ARTIFACT_UNSAFE",
            "a required issuer artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    return ArtifactReceipt(
        repository_path=relative_path.as_posix(),
        sha256=_sha256_bytes(_canonical_lf(path.read_bytes())),
    )


def _read_json_object(repo_root: Path, relative_path: Path) -> dict[str, object]:
    path = repo_root / relative_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_IMPLEMENTATION_JSON_INVALID",
            "a merged P4 implementation artifact is invalid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_IMPLEMENTATION_ROOT_INVALID",
            "a merged P4 implementation artifact must be one object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _wheelhouse_authority() -> WheelhouseAuthority:
    return WheelhouseAuthority(
        requirements_in_sha256=("a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"),
        resolution_lock_sha256=("1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"),
        materialization_lock_sha256=(
            "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
        ),
        requirements_lock_sha256=(
            "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"
        ),
        install_runtime_sha256=("68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"),
        runtime_manifest_sha256=(
            "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
        ),
        sha256_manifest_sha256=("789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"),
        materialization_receipt_sha256=(
            "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
        ),
    )


def _terminal_evidence_authority(repo_root: Path) -> TerminalEvidenceAuthority:
    source_text = (repo_root / IMPLEMENTATION_SOURCE_PATH).read_text(encoding="utf-8")
    template_text = (repo_root / IMPLEMENTATION_TEMPLATE_PATH).read_text(encoding="utf-8")
    tests_text = (repo_root / IMPLEMENTATION_TESTS_PATH).read_text(encoding="utf-8")
    adr_text = (repo_root / IMPLEMENTATION_ADR_PATH).read_text(encoding="utf-8")
    report_text = (repo_root / IMPLEMENTATION_REPORT_PATH).read_text(encoding="utf-8")
    runbook_text = (repo_root / IMPLEMENTATION_RUNBOOK_PATH).read_text(encoding="utf-8")

    required = {
        "canonical_output_contract": ("EXPECTED_RUNTIME_OUTPUTS: Final = (" in source_text),
        "initialize_not_run_reports": ("initialize_not_run_reports" in template_text),
        "partial_request_evidence": "write_request_evidence" in template_text,
        "partial_selection_ineligible": ("INELIGIBLE_PARTIAL_EVIDENCE" in template_text),
        "startup_failure_teardown": "startup_teardown" in template_text,
        "teardown_failure_terminalized": ("P4_OUTPUT_CONTRACT_TEARDOWN_FAILED" in template_text),
        "cleanup_failure_terminalized": (
            "P4_OUTPUT_CONTRACT_SCRATCH_CLEANUP_FAILED" in template_text
        ),
        "pre_manifest_output_completeness_gate": (
            "runtime output set is incomplete before manifest creation" in template_text
        ),
        "pre_archive_output_completeness_gate": (
            "runtime output set is incomplete before archive creation" in template_text
        ),
        "synthetic_failure_regression": (
            "test_runtime_failure_path_emits_complete_output_contract" in tests_text
        ),
        "adr_terminal_closure": ("## Terminal-path evidence closure amendment" in adr_text),
        "report_terminal_closure": "## Terminal-path closure" in report_text,
        "runbook_terminal_closure": ("## Terminal-path completeness gate" in runbook_text),
    }
    missing = tuple(sorted(name for name, present in required.items() if not present))
    if missing:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_TERMINAL_EVIDENCE_DRIFT",
            "the merged P4 terminal-evidence contract drifted",
            details=missing,
        )
    return TerminalEvidenceAuthority()


def _implementation_authority(repo_root: Path) -> ImplementationAuthority:
    record = _read_json_object(repo_root, IMPLEMENTATION_RECORD_PATH)
    request = _read_json_object(repo_root, IMPLEMENTATION_REQUEST_PATH)
    review = _read_json_object(repo_root, IMPLEMENTATION_REVIEW_PATH)

    if record.get("status") != "IMPLEMENTED_NOT_EXECUTED":
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_IMPLEMENTATION_STATE_INVALID",
            "the P4 implementation is not in the reviewed pre-execution state",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if record.get("source_main_commit") != IMPLEMENTATION_SOURCE_MAIN_COMMIT:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_SOURCE_MAIN_BINDING_DRIFT",
            "the P4 implementation source-main binding drifted",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if request.get("source_main_commit") != IMPLEMENTATION_SOURCE_MAIN_COMMIT:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_REQUEST_SOURCE_BINDING_DRIFT",
            "the P4 request source-main binding drifted",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    if review.get("source_main_commit") != IMPLEMENTATION_SOURCE_MAIN_COMMIT:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_REVIEW_SOURCE_BINDING_DRIFT",
            "the P4 review source-main binding drifted",
            IMPLEMENTATION_REVIEW_PATH.as_posix(),
        )

    safety = record.get("safety")
    if not isinstance(safety, dict):
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_IMPLEMENTATION_SAFETY_INVALID",
            "the P4 implementation safety contract is invalid",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if safety.get("runtime_execution_authorized") is not False:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_PREEXISTING_AUTHORITY",
            "the P4 implementation unexpectedly reports runtime authority",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if safety.get("model_requests_performed") != 0:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_PREEXISTING_EXECUTION",
            "the P4 implementation unexpectedly reports model requests",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if record.get("authorization_issuer_included") is not False:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_IMPLEMENTATION_STATE_INVALID",
            "the P4 implementation unexpectedly includes an issuer",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if request.get("runtime_execution_authorized") is not False:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_REQUEST_STATE_INVALID",
            "the P4 request unexpectedly reports runtime authority",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    if request.get("authorization_issuer_included") is not False:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_REQUEST_STATE_INVALID",
            "the P4 request unexpectedly includes an issuer",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    if request.get("measured_abc_execution_authorized") is not False:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_MEASURED_ABC_STATE_INVALID",
            "the P4 request unexpectedly authorizes measured A/B/C",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    if request.get("model_snapshot_sha256") != MODEL_SNAPSHOT_SHA256:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_MODEL_IDENTITY_DRIFT",
            "the P4 model snapshot identity drifted",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )

    expected_budget = {
        "benchmark_trajectory_requests_permitted": 0,
        "external_network_requests_permitted": 0,
        "external_spend": 0,
        "hidden_retries_permitted": 0,
        "maximum_kaggle_sessions": 1,
        "maximum_model_loads": 1,
        "maximum_model_requests": 18,
        "maximum_output_tokens_per_request": 32,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_worker_starts": 1,
    }
    if request.get("execution_budget") != expected_budget:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_BUDGET_DRIFT",
            "the merged P4 execution budget drifted",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )

    request_order = request.get("request_order")
    if not isinstance(request_order, list) or len(request_order) != 18:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_REQUEST_ORDER_DRIFT",
            "the merged P4 request order drifted",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )
    for case_id in ("A", "B", "C", "D", "E", "F"):
        if request_order.count(case_id) != 3:
            raise P4AuthorizationError(
                "P4_AUTHORIZATION_REQUEST_ORDER_DRIFT",
                "the merged P4 case repetition count drifted",
                IMPLEMENTATION_REQUEST_PATH.as_posix(),
                details=(case_id,),
            )

    record_outputs = record.get("expected_runtime_outputs")
    review_outputs = review.get("output_contract")
    if (
        not isinstance(record_outputs, list)
        or tuple(record_outputs) != EXPECTED_RUNTIME_OUTPUTS
        or not isinstance(review_outputs, list)
        or tuple(review_outputs) != EXPECTED_RUNTIME_OUTPUTS
    ):
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_OUTPUT_CONTRACT_DRIFT",
            "the merged P4 output contract drifted",
        )

    notebook_receipt = record.get("notebook")
    if not isinstance(notebook_receipt, dict):
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_NOTEBOOK_RECEIPT_INVALID",
            "the P4 notebook receipt is unavailable",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if (
        notebook_receipt.get("runtime_script_sha256") != IMPLEMENTATION_RUNTIME_SCRIPT_SHA256
        or notebook_receipt.get("wrapper_code_sha256") != IMPLEMENTATION_WRAPPER_CODE_SHA256
    ):
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_RUNTIME_SOURCE_BINDING_DRIFT",
            "the P4 runtime-script or wrapper identity drifted",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    return ImplementationAuthority(
        original_implementation_merge_commit=ORIGINAL_IMPLEMENTATION_MERGE_COMMIT,
        evidence_contract_feature_commit=EVIDENCE_CONTRACT_FEATURE_COMMIT,
        evidence_contract_merge_commit=EVIDENCE_CONTRACT_MERGE_COMMIT,
        terminal_closure_feature_commit=TERMINAL_CLOSURE_FEATURE_COMMIT,
        terminal_closure_merge_commit=TERMINAL_CLOSURE_MERGE_COMMIT,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation_source_main_commit=IMPLEMENTATION_SOURCE_MAIN_COMMIT,
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        implementation_record=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_RECORD_PATH,
            IMPLEMENTATION_RECORD_SHA256,
        ),
        notebook=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_NOTEBOOK_PATH,
            IMPLEMENTATION_NOTEBOOK_SHA256,
        ),
        request=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_REQUEST_PATH,
            IMPLEMENTATION_REQUEST_SHA256,
        ),
        architecture_review=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_REVIEW_PATH,
            IMPLEMENTATION_REVIEW_SHA256,
        ),
        implementation_source=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_SOURCE_PATH,
            IMPLEMENTATION_SOURCE_SHA256,
        ),
        template=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_TEMPLATE_PATH,
            IMPLEMENTATION_TEMPLATE_SHA256,
        ),
        implementation_tests=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_TESTS_PATH,
            IMPLEMENTATION_TESTS_SHA256,
        ),
        adr=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_ADR_PATH,
            IMPLEMENTATION_ADR_SHA256,
        ),
        report=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_REPORT_PATH,
            IMPLEMENTATION_REPORT_SHA256,
        ),
        runbook=_implementation_artifact(
            repo_root,
            IMPLEMENTATION_RUNBOOK_PATH,
            IMPLEMENTATION_RUNBOOK_SHA256,
        ),
        runtime_script_sha256=IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=IMPLEMENTATION_WRAPPER_CODE_SHA256,
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        wheelhouse=_wheelhouse_authority(),
        expected_runtime_outputs=EXPECTED_RUNTIME_OUTPUTS,
        terminal_evidence=_terminal_evidence_authority(repo_root),
        execution_budget=ExecutionBudget(),
        controls=AuthorizationControls(),
        runtime_execution_authorized_before_issuance=False,
        authorization_issuer_included_before_issuance=False,
        measured_abc_execution_authorized=False,
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "This issuer implementation does not issue live runtime authorization.",
        "The P4 diagnostic has not been executed by this tranche.",
        "No Kaggle session or GPU action has been started.",
        "No target runtime has been installed by this tranche.",
        "No model has been loaded.",
        "No worker has been started.",
        "No model request has been issued.",
        "JSON-schema compatibility with the pinned runtime is not established.",
        "No A-F diagnostic case has been selected.",
        "P4 structured-output reliability is not established.",
        "P5 prefix-cache qualification is not established.",
        "P6 route and metric isolation is not established.",
        "Measured A/B/C is not authorized.",
        "Terminal-path completeness is statically validated but not runtime-proven on Kaggle.",
        "The transient authorization is an operator gate, not notebook-parsed authority.",
        "Deployment and production readiness are not claimed.",
    )


def _build_review(repo_root: Path) -> AuthorizationArchitectureReview:
    return AuthorizationArchitectureReview(
        review_id=("auragateway-p4-output-contract-diagnostic-execution-authorization-v1-review"),
        status="APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION",
        decision="SEPARATE_TRANSIENT_SINGLE_USE_P4_DIAGNOSTIC_AUTHORIZATION",
        implementation=_implementation_authority(repo_root),
        budget=ExecutionBudget(),
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
        non_claims=_non_claims(),
    )


def _build_record(
    repo_root: Path,
    review_bytes: bytes,
) -> AuthorizationImplementationRecord:
    return AuthorizationImplementationRecord(
        record_id=("auragateway-p4-output-contract-diagnostic-execution-authorization-v1-record"),
        status="P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V1_VALID",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation=_implementation_authority(repo_root),
        review=ArtifactReceipt(
            repository_path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
        ),
        issuer_source=_issuer_artifact(repo_root, ISSUER_SOURCE_PATH),
        issuer_tests=_issuer_artifact(repo_root, ISSUER_TEST_PATH),
        adr=_issuer_artifact(repo_root, ADR_PATH),
        report=_issuer_artifact(repo_root, REPORT_PATH),
        runbook=_issuer_artifact(repo_root, RUNBOOK_PATH),
        authorization_path=AUTHORIZATION_PATH.as_posix(),
        consumption_path=CONSUMPTION_PATH.as_posix(),
        authorization_issuer_implemented=True,
        authorization_issued=False,
        consumption_record_created=False,
        runtime_execution_performed=False,
        budget=ExecutionBudget(),
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ATOMIC_WRITE_FAILED",
            "an authorization artifact could not be written atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _write_non_overwriting(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ALREADY_EXISTS",
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ALREADY_EXISTS",
            "the transient authorization appeared during issuance",
            path.as_posix(),
        ) from error
    except OSError as error:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ATOMIC_CREATE_FAILED",
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
        raise P4AuthorizationError(
            "P4_TRANSIENT_AUTHORITY_PRESENT",
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
            raise P4AuthorizationError(
                "P4_AUTHORIZATION_STATIC_ARTIFACT_UNSAFE",
                "a static authorization artifact is missing or unsafe",
                path.as_posix(),
            )
        if target.read_bytes() != payload:
            raise P4AuthorizationError(
                "P4_AUTHORIZATION_STATIC_ARTIFACT_DRIFT",
                "a static authorization artifact differs from fresh generation",
                path.as_posix(),
            )
    return record


def validate_implementation_package(repo_root: Path) -> dict[str, object]:
    """Validate the issuer implementation without creating runtime authority."""

    root = repo_root.resolve()
    if (root / AUTHORIZATION_PATH).exists() or (root / CONSUMPTION_PATH).exists():
        raise P4AuthorizationError(
            "P4_TRANSIENT_AUTHORITY_PRESENT",
            "transient authorization artifacts must be absent during review",
        )
    record = _validate_static_package(root)
    return {
        "status": record.status,
        "source_main_merge_commit": record.source_main_merge_commit,
        "evidence_contract_feature_commit": (
            record.implementation.evidence_contract_feature_commit
        ),
        "evidence_contract_merge_commit": (record.implementation.evidence_contract_merge_commit),
        "terminal_closure_feature_commit": (record.implementation.terminal_closure_feature_commit),
        "terminal_closure_merge_commit": (record.implementation.terminal_closure_merge_commit),
        "notebook_sha256": record.implementation.notebook.sha256,
        "runtime_script_sha256": record.implementation.runtime_script_sha256,
        "wrapper_code_sha256": record.implementation.wrapper_code_sha256,
        "request_sha256": record.implementation.request.sha256,
        "implementation_record_sha256": record.implementation.implementation_record.sha256,
        "model_snapshot_sha256": record.implementation.model_snapshot_sha256,
        "authorization_issuer_implemented": True,
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "maximum_kaggle_sessions": record.budget.maximum_kaggle_sessions,
        "maximum_model_loads": record.budget.maximum_model_loads,
        "maximum_worker_starts": record.budget.maximum_worker_starts,
        "maximum_model_requests": record.budget.maximum_model_requests,
        "maximum_output_tokens_per_request": (record.budget.maximum_output_tokens_per_request),
        "expected_runtime_output_count": record.controls.expected_runtime_output_count,
        "terminal_path_output_contract_complete": (
            record.implementation.terminal_evidence == TerminalEvidenceAuthority()
        ),
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_GIT_FAILED",
            "a required Git inspection could not be completed",
            details=tuple(arguments),
        ) from error
    if result.returncode != 0:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_GIT_FAILED",
            "a required Git inspection failed",
            details=tuple(arguments),
        )
    return result.stdout.strip()


def _require_ancestor(repo_root: Path, commit: str) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                commit,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ANCESTRY_UNREADABLE",
            "authorization source ancestry could not be inspected",
            details=(commit,),
        ) from error
    if result.returncode != 0:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_SOURCE_AUTHORITY_MISSING",
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_MAIN_REQUIRED",
            "authorization lifecycle operations require branch main",
            details=(branch,),
        )
    head = _run_git(repo_root, ["rev-parse", "HEAD"])
    origin_main = _run_git(repo_root, ["rev-parse", "origin/main"])
    if head != origin_main:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_MUST_REMAIN_UNTRACKED",
            "transient authorization artifacts must never be tracked",
            details=tuple(tracked.splitlines()),
        )


def _require_source_authority(repo_root: Path) -> None:
    _require_ancestor(repo_root, ORIGINAL_IMPLEMENTATION_MERGE_COMMIT)
    _require_ancestor(repo_root, EVIDENCE_CONTRACT_FEATURE_COMMIT)
    _require_ancestor(repo_root, EVIDENCE_CONTRACT_MERGE_COMMIT)
    _require_ancestor(repo_root, TERMINAL_CLOSURE_FEATURE_COMMIT)
    _require_ancestor(repo_root, TERMINAL_CLOSURE_MERGE_COMMIT)


def _build_authorization(
    *,
    repo_root: Path,
    issuer_head: str,
    confirmation: AuthorizationIssuanceConfirmation,
) -> P4ExecutionAuthorization:
    _validate_static_package(repo_root)
    checks = (
        confirmation.confirmed_scope == AUTHORIZATION_SCOPE,
        confirmation.confirmed_source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT,
        confirmation.confirmed_terminal_closure_feature_commit == TERMINAL_CLOSURE_FEATURE_COMMIT,
        confirmation.confirmed_notebook_sha256 == IMPLEMENTATION_NOTEBOOK_SHA256,
        confirmation.confirmed_runtime_script_sha256 == IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        confirmation.confirmed_wrapper_code_sha256 == IMPLEMENTATION_WRAPPER_CODE_SHA256,
        confirmation.confirmed_request_sha256 == IMPLEMENTATION_REQUEST_SHA256,
        confirmation.confirmed_implementation_record_sha256 == IMPLEMENTATION_RECORD_SHA256,
        confirmation.confirmed_model_snapshot_sha256 == MODEL_SNAPSHOT_SHA256,
        confirmation.confirmed_backend == SELECTED_BACKEND,
        confirmation.confirmed_model_request_budget == 18,
        confirmation.confirmed_runtime_output_count == 16,
        confirmation.confirmed_terminal_path_output_contract_complete is True,
    )
    if not all(checks):
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_CONFIRMATION_BINDING_DRIFT",
            "operator confirmation does not bind the reviewed P4 identities",
        )
    issued_at = confirmation.confirmed_at
    return P4ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=AuthorizationLifecycle.ISSUED,
        scope=AUTHORIZATION_SCOPE,
        original_implementation_merge_commit=ORIGINAL_IMPLEMENTATION_MERGE_COMMIT,
        evidence_contract_feature_commit=EVIDENCE_CONTRACT_FEATURE_COMMIT,
        evidence_contract_merge_commit=EVIDENCE_CONTRACT_MERGE_COMMIT,
        terminal_closure_feature_commit=TERMINAL_CLOSURE_FEATURE_COMMIT,
        terminal_closure_merge_commit=TERMINAL_CLOSURE_MERGE_COMMIT,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation_record_sha256=IMPLEMENTATION_RECORD_SHA256,
        request_sha256=IMPLEMENTATION_REQUEST_SHA256,
        notebook_sha256=IMPLEMENTATION_NOTEBOOK_SHA256,
        runtime_script_sha256=IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=IMPLEMENTATION_WRAPPER_CODE_SHA256,
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        wheelhouse=_wheelhouse_authority(),
        expected_runtime_outputs=EXPECTED_RUNTIME_OUTPUTS,
        terminal_evidence=_terminal_evidence_authority(repo_root),
        issued_from_main_commit=issuer_head,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(minutes=confirmation.authorization_window_minutes),
        operator_confirmation_recorded=True,
        single_use=True,
        passed_failed_or_interrupted_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        budget=ExecutionBudget(),
        controls=AuthorizationControls(),
    )


def issue_authorization(
    *,
    repo_root: Path,
    confirmation: AuthorizationIssuanceConfirmation,
) -> dict[str, object]:
    """Issue one transient, non-overwriting authority after confirmation."""

    root = repo_root.resolve()
    issuer_head = _require_synchronized_main(root, allow_transient=False)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    if (root / CONSUMPTION_PATH).exists():
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ALREADY_CONSUMED",
            "a prior P4 authorization consumption receipt already exists",
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
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_ISSUED",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": _sha256_bytes(payload),
        "issued_from_main_commit": authorization.issued_from_main_commit,
        "terminal_closure_feature_commit": (authorization.terminal_closure_feature_commit),
        "terminal_closure_merge_commit": (authorization.terminal_closure_merge_commit),
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "notebook_sha256": authorization.notebook_sha256,
        "runtime_script_sha256": authorization.runtime_script_sha256,
        "wrapper_code_sha256": authorization.wrapper_code_sha256,
        "model_snapshot_sha256": authorization.model_snapshot_sha256,
        "single_use": True,
        "maximum_kaggle_sessions": 1,
        "maximum_model_loads": 1,
        "maximum_worker_starts": 1,
        "maximum_model_requests": 18,
        "maximum_output_tokens_per_request": 32,
        "expected_runtime_output_count": 16,
        "terminal_path_output_contract_complete": True,
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_PAYLOAD_INVALID",
            "an authorization payload failed strict validation",
            path.as_posix(),
        ) from error
    if observed != contract.canonical_json():
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_PAYLOAD_NOT_CANONICAL",
            "an authorization payload is not canonical JSON",
            path.as_posix(),
        )
    return contract


def _validate_authorization_bindings(
    authorization: P4ExecutionAuthorization,
) -> None:
    checks = (
        authorization.authorization_id == AUTHORIZATION_ID,
        authorization.scope == AUTHORIZATION_SCOPE,
        authorization.original_implementation_merge_commit == ORIGINAL_IMPLEMENTATION_MERGE_COMMIT,
        authorization.evidence_contract_feature_commit == EVIDENCE_CONTRACT_FEATURE_COMMIT,
        authorization.evidence_contract_merge_commit == EVIDENCE_CONTRACT_MERGE_COMMIT,
        authorization.terminal_closure_feature_commit == TERMINAL_CLOSURE_FEATURE_COMMIT,
        authorization.terminal_closure_merge_commit == TERMINAL_CLOSURE_MERGE_COMMIT,
        authorization.source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT,
        authorization.implementation_record_sha256 == IMPLEMENTATION_RECORD_SHA256,
        authorization.request_sha256 == IMPLEMENTATION_REQUEST_SHA256,
        authorization.notebook_sha256 == IMPLEMENTATION_NOTEBOOK_SHA256,
        authorization.runtime_script_sha256 == IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        authorization.wrapper_code_sha256 == IMPLEMENTATION_WRAPPER_CODE_SHA256,
        authorization.model_snapshot_sha256 == MODEL_SNAPSHOT_SHA256,
        authorization.wheelhouse == _wheelhouse_authority(),
        authorization.expected_runtime_outputs == EXPECTED_RUNTIME_OUTPUTS,
        authorization.terminal_evidence == TerminalEvidenceAuthority(),
        authorization.operator_confirmation_recorded is True,
        authorization.single_use is True,
        authorization.passed_failed_or_interrupted_attempt_consumes_authorization is True,
        authorization.unchanged_replay_authorized is False,
        authorization.budget == ExecutionBudget(),
        authorization.controls == AuthorizationControls(),
    )
    if not all(checks):
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_BINDING_DRIFT",
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ALREADY_CONSUMED",
            "the authorization has a consumption receipt and is not reusable",
            CONSUMPTION_PATH.as_posix(),
        )
    loaded = _load_canonical(root / AUTHORIZATION_PATH, P4ExecutionAuthorization)
    authorization = cast(P4ExecutionAuthorization, loaded)
    _validate_authorization_bindings(authorization)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if not authorization.issued_at <= observed_now < authorization.expires_at:
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_EXPIRED",
            "the transient authorization is outside its validity window",
            AUTHORIZATION_PATH.as_posix(),
        )
    return {
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_VALID",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": authorization.fingerprint(),
        "issuer_head_commit": issuer_head,
        "issued_from_main_commit": authorization.issued_from_main_commit,
        "terminal_closure_feature_commit": (authorization.terminal_closure_feature_commit),
        "terminal_closure_merge_commit": (authorization.terminal_closure_merge_commit),
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "notebook_sha256": authorization.notebook_sha256,
        "runtime_script_sha256": authorization.runtime_script_sha256,
        "wrapper_code_sha256": authorization.wrapper_code_sha256,
        "single_use": True,
        "consumed": False,
        "maximum_kaggle_sessions": 1,
        "maximum_model_loads": 1,
        "maximum_worker_starts": 1,
        "maximum_model_requests": 18,
        "maximum_output_tokens_per_request": 32,
        "expected_runtime_output_count": 16,
        "terminal_path_output_contract_complete": True,
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
        raise P4AuthorizationError(
            "P4_AUTHORIZATION_ALREADY_CONSUMED",
            "the authorization consumption receipt already exists",
            CONSUMPTION_PATH.as_posix(),
        )
    loaded = _load_canonical(root / AUTHORIZATION_PATH, P4ExecutionAuthorization)
    authorization = cast(P4ExecutionAuthorization, loaded)
    _validate_authorization_bindings(authorization)
    authorization_payload = authorization.canonical_json().encode("utf-8")
    receipt = P4AuthorizationConsumption(
        consumption_id=(
            "auragateway-p4-output-contract-diagnostic-execution-authorization-consumption-v1"
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
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_CONSUMED",
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
    parser = _ArgumentParser(prog="auragateway-p4-authorization-v1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("generate", "validate-implementation", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)

    issue_parser = subparsers.add_parser("issue")
    issue_parser.add_argument("--repo-root", type=Path, required=True)
    issue_parser.add_argument("--operator-confirm", action="store_true")
    issue_parser.add_argument("--window-minutes", type=int, default=240)
    issue_parser.add_argument("--confirm-scope", required=True)
    issue_parser.add_argument("--confirm-source-main-merge-commit", required=True)
    issue_parser.add_argument(
        "--confirm-terminal-closure-feature-commit",
        required=True,
    )
    issue_parser.add_argument("--confirm-notebook-sha256", required=True)
    issue_parser.add_argument("--confirm-runtime-script-sha256", required=True)
    issue_parser.add_argument("--confirm-wrapper-code-sha256", required=True)
    issue_parser.add_argument("--confirm-request-sha256", required=True)
    issue_parser.add_argument("--confirm-implementation-record-sha256", required=True)
    issue_parser.add_argument("--confirm-model-snapshot-sha256", required=True)
    issue_parser.add_argument("--confirm-backend", required=True)
    issue_parser.add_argument("--confirm-model-request-budget", type=int, required=True)
    issue_parser.add_argument("--confirm-runtime-output-count", type=int, required=True)
    issue_parser.add_argument(
        "--confirm-terminal-path-output-contract-complete",
        action="store_true",
        required=True,
    )

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


def _error_json(error: P4AuthorizationError) -> str:
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
                raise P4AuthorizationError(
                    "P4_OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required for issuance",
                )
            confirmation = AuthorizationIssuanceConfirmation(
                confirmation_id=(
                    "auragateway-p4-output-contract-diagnostic-execution-"
                    "authorization-confirmation-v1"
                ),
                operator_confirmed=True,
                confirmed_at=datetime.now(UTC),
                authorization_window_minutes=cast(int, arguments.window_minutes),
                confirmed_scope=cast(str, arguments.confirm_scope),
                confirmed_source_main_merge_commit=cast(
                    str,
                    arguments.confirm_source_main_merge_commit,
                ),
                confirmed_terminal_closure_feature_commit=cast(
                    str,
                    arguments.confirm_terminal_closure_feature_commit,
                ),
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
                confirmed_request_sha256=cast(
                    str,
                    arguments.confirm_request_sha256,
                ),
                confirmed_implementation_record_sha256=cast(
                    str,
                    arguments.confirm_implementation_record_sha256,
                ),
                confirmed_model_snapshot_sha256=cast(
                    str,
                    arguments.confirm_model_snapshot_sha256,
                ),
                confirmed_backend=cast(str, arguments.confirm_backend),
                confirmed_model_request_budget=cast(
                    int,
                    arguments.confirm_model_request_budget,
                ),
                confirmed_runtime_output_count=cast(
                    int,
                    arguments.confirm_runtime_output_count,
                ),
                confirmed_terminal_path_output_contract_complete=cast(
                    bool,
                    arguments.confirm_terminal_path_output_contract_complete,
                ),
            )
            summary = issue_authorization(
                repo_root=repo_root,
                confirmation=confirmation,
            )
        elif arguments.command == "verify":
            summary = verify_authorization(repo_root=repo_root)
        elif arguments.command == "consume":
            if arguments.operator_confirm is not True:
                raise P4AuthorizationError(
                    "P4_OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required for consumption",
                )
            summary = consume_authorization(
                repo_root=repo_root,
                outcome=ExecutionOutcome(cast(str, arguments.outcome)),
                saved_version_id=cast(int, arguments.saved_version_id),
            )
        else:
            raise P4AuthorizationError(
                "P4_AUTHORIZATION_COMMAND_UNSUPPORTED",
                "the authorization command is unsupported",
            )
        print(
            json.dumps(
                summary,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except (P4AuthorizationError, ValidationError, ValueError, OSError) as error:
        if isinstance(error, P4AuthorizationError):
            output = _error_json(error)
        else:
            output = AuthorizationErrorEnvelope(
                error_code="P4_AUTHORIZATION_UNEXPECTED",
                safe_message=type(error).__name__,
            ).canonical_json()
        print(output, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
