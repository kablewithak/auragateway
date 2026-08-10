"""Implement the exact-runtime P5/P6 single-use execution authorization V1.

This module is control-plane infrastructure. Static generation and validation
prove the issuer implementation without issuing authority. Live authorization
can only be issued after this issuer is merged to synchronized clean ``main``,
a fresh operator confirmation is supplied, the bound P5/P6 implementation is
revalidated, and the exact platform observation remains fresh.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ISSUER_BASE_MAIN_COMMIT: Final = "2877f66a112a89c313c322bd38c3f71f9caff218"
AUTHORIZATION_DESIGN_MERGE_COMMIT: Final = ISSUER_BASE_MAIN_COMMIT
P5_P6_IMPLEMENTATION_MERGE_COMMIT: Final = "9cc06c02c372fa2e7637c432759e7a1d4db56e9e"

AUTHORIZATION_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_execution_authorization_design_v1.json"
)
AUTHORIZATION_DESIGN_RECORD_SHA256: Final = (
    "18eef4f455e67ef850cb2a4ff6502360b8885d2fff7e36ddcca7dcb6f15af230"
)
AUTHORIZATION_DESIGN_RECORD_SIZE: Final = 8152

P5_P6_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_requalification_design_v1.json"
)
P5_P6_DESIGN_RECORD_SHA256: Final = (
    "4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2"
)
P5_P6_IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_implementation_record.json"
)
P5_P6_IMPLEMENTATION_RECORD_SHA256: Final = (
    "6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d"
)
P5_P6_IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_implementation_review.json"
)
P5_P6_IMPLEMENTATION_REVIEW_SHA256: Final = (
    "151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d"
)
P5_P6_IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v1.py"
)
P5_P6_IMPLEMENTATION_SOURCE_SHA256: Final = (
    "e41c0c327eab743c01dad961d07204a041e64e0579936145b79a1c23a675d126"
)
P5_P6_IMPLEMENTATION_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v1.py.tmpl"
)
P5_P6_IMPLEMENTATION_TEMPLATE_SHA256: Final = (
    "bc512e45e7ac646045dda3f598ca2aa961a0c69c86b73117d66bb457710d0dfa"
)
P5_P6_IMPLEMENTATION_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v1.py"
)
P5_P6_IMPLEMENTATION_TEST_SHA256: Final = (
    "9d6151e387cd7b972696ffe982016831271288209a8a18cd6db1335343c137eb"
)
P5_P6_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p5_p6_exact_runtime_requalification_v1.ipynb"
)
P5_P6_NOTEBOOK_SHA256: Final = "cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7"
P5_P6_RUNTIME_SCRIPT_SHA256: Final = (
    "d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67"
)
P5_P6_WRAPPER_CODE_SHA256: Final = (
    "55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c"
)
P5_P6_PROVENANCE_RECONCILIATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_provenance_identity_reconciliation_v1.py"
)
P5_P6_PROVENANCE_RECONCILIATION_SOURCE_SHA256: Final = (
    "d0e1d6b22b891bdba975107b0c56a8dd93bc295d7ea2e576d93f33d6436e5836"
)
P5_P6_PROVENANCE_RECONCILIATION_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_provenance_identity_reconciliation_v1.py"
)
P5_P6_PROVENANCE_RECONCILIATION_TEST_SHA256: Final = (
    "3f03f9c5fc17db986115e8b61403b22392a6cfefbd3bbcb6d3add76e1e67500c"
)
P5_P6_PROVENANCE_RECONCILIATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_provenance_identity_reconciliation_v1.json"
)
P5_P6_PROVENANCE_RECONCILIATION_RECORD_SHA256: Final = (
    "1a274c75bda75fa52be3095b32ade7fe00b47de69e66adaed1016cbd4ffda089"
)
P5_P6_PROVENANCE_RECONCILIATION_RECORD_SIZE: Final = 4225
V5_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_evidence_acceptance_v1_record.json"
)
V5_ACCEPTANCE_RECORD_SHA256: Final = (
    "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_execution_authorization_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_execution_authorization_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-10-local-abc-exact-runtime-p5-p6-execution-authorization-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Exact_Runtime_P5_P6_Execution_Authorization_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_exact_runtime_p5_p6_execution_authorization_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_execution_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_execution_authorization_v1_record.json"
)

AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_execution_authorization.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_authorization_consumption.json"
)
AUTHORIZATION_TRANSFER_FILENAME: Final = "execution_authorization_v1.json"
AUTHORIZATION_ID: Final = (
    "auragateway-exact-runtime-p5-p6-requalification-v1-execution-authorization"
)
AUTHORIZATION_SCOPE: Final = "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"
CONFIRMATION_PHRASE: Final = (
    "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
    "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION"
)

MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES: Final = 15
MAXIMUM_OPERATOR_CONFIRMATION_AGE_MINUTES: Final = 15
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
DEFAULT_AUTHORIZATION_WINDOW_MINUTES: Final = 180

NEXT_GATE_AFTER_STATIC_IMPLEMENTATION: Final = (
    "MERGE_EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_ISSUER_V1_WITHOUT_ISSUING"
)
NEXT_GATE_AFTER_ISSUE: Final = "EXECUTE_ONE_GOVERNED_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"
NEXT_GATE_AFTER_TERMINAL: Final = (
    "PRESERVE_AND_ACCEPT_OR_CLASSIFY_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EVIDENCE"
)

EXPECTED_RUNTIME_OUTPUTS: Final = (
    "runtime_source_identity_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_environment_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "c1_model_construction_report_v1.json",
    "c2_worker_startup_report_v1.json",
    "c3_single_request_report_v1.json",
    "c4_output_contract_report_v1.json",
    "p5_cache_behavior_report_v1.json",
    "p5_post_restart_native_origin_report_v1.json",
    "p6_stage_checkpoint_report_v1.json",
    "p6_native_origin_report_v1.json",
    "p6_worker_state_isolation_report_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "p5_p6_exact_runtime_requalification_summary_v1.json",
    "failure_report_v1.json",
    "bundle_manifest_v1.json",
    "human_report_v1.md",
)
EXPECTED_EVIDENCE_ZIP: Final = "ag-exact-runtime-p5-p6-requal-evidence-v1.zip"


class AuthorizationIssuerError(RuntimeError):
    """Metadata-safe fail-closed authorization issuer error."""

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


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationIssuerError(
            "P5_P6_AUTHORIZATION_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    """Strict immutable persisted-contract base."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ErrorEnvelope(FrozenModel):
    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class TerminalDisposition(StrEnum):
    """Terminal authorization states frozen by the merged design."""

    CONSUMED = "CONSUMED"
    EXPIRED_UNUSED = "EXPIRED_UNUSED"
    CANCELLED_UNUSED = "CANCELLED_UNUSED"
    ABANDONED_BEFORE_EXECUTION = "ABANDONED_BEFORE_EXECUTION"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class ExecutionOutcome(StrEnum):
    """Known execution outcomes after an attempt begins."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"
    INTERRUPTED = "INTERRUPTED"
    DIAGNOSTIC_INVALID = "DIAGNOSTIC_INVALID"


class ArtifactIdentity(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ExecutionLimits(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_saved_versions: Literal[1] = 1
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_workers: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class PlatformObservation(FrozenModel):
    observed_at: datetime
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"]
    accelerator: Literal["T4_X2"]
    allocated_gpu_count: Literal[2]
    internet_enabled: Literal[False]
    external_network_access_permitted: Literal[False]
    credentials_permitted: Literal[False]
    customer_data_permitted: Literal[False]

    @field_validator("observed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        return _normalize_time(value, "platform observed_at")


class IssuanceConfirmation(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    confirmation_id: Literal[
        "auragateway-exact-runtime-p5-p6-execution-authorization-confirmation-v1"
    ]
    operator_confirmed: Literal[True]
    exact_confirmation_phrase: Literal[
        "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
        "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION"
    ]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(
        ge=1,
        le=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
    )
    confirmed_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmed_authorization_design_merge_commit: Literal["2877f66a112a89c313c322bd38c3f71f9caff218"]
    confirmed_authorization_design_record_sha256: Literal[
        "18eef4f455e67ef850cb2a4ff6502360b8885d2fff7e36ddcca7dcb6f15af230"
    ]
    confirmed_scope: Literal["EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"]
    confirmed_implementation_merge_commit: Literal["9cc06c02c372fa2e7637c432759e7a1d4db56e9e"]
    confirmed_p5_p6_design_record_sha256: Literal[
        "4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2"
    ]
    confirmed_implementation_record_sha256: Literal[
        "6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d"
    ]
    confirmed_implementation_review_sha256: Literal[
        "151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d"
    ]
    confirmed_provenance_reconciliation_record_sha256: Literal[
        "1a274c75bda75fa52be3095b32ade7fe00b47de69e66adaed1016cbd4ffda089"
    ]
    confirmed_notebook_sha256: Literal[
        "cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7"
    ]
    confirmed_runtime_script_sha256: Literal[
        "d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67"
    ]
    confirmed_wrapper_code_sha256: Literal[
        "55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c"
    ]
    confirmed_v5_acceptance_sha256: Literal[
        "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
    ]
    execution_limits: ExecutionLimits
    platform: PlatformObservation

    @field_validator("confirmed_at")
    @classmethod
    def require_confirmation_timezone(cls, value: datetime) -> datetime:
        return _normalize_time(value, "operator confirmed_at")

    @model_validator(mode="after")
    def require_platform_not_after_confirmation(self) -> Self:
        if self.platform.observed_at > self.confirmed_at:
            raise ValueError("platform observation cannot follow operator confirmation")
        return self


class ExecutionAuthorization(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal[
        "auragateway-exact-runtime-p5-p6-requalification-v1-execution-authorization"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"]
    authorization_filename: Literal["execution_authorization_v1.json"]
    issued_at: datetime
    expires_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=240)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_merge_commit: Literal["2877f66a112a89c313c322bd38c3f71f9caff218"]
    authorization_design_record_sha256: Literal[
        "18eef4f455e67ef850cb2a4ff6502360b8885d2fff7e36ddcca7dcb6f15af230"
    ]
    implementation_merge_commit: Literal["9cc06c02c372fa2e7637c432759e7a1d4db56e9e"]
    implementation_record_sha256: Literal[
        "6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d"
    ]
    implementation_review_sha256: Literal[
        "151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d"
    ]
    provenance_reconciliation_record_sha256: Literal[
        "1a274c75bda75fa52be3095b32ade7fe00b47de69e66adaed1016cbd4ffda089"
    ]
    design_record_sha256: Literal[
        "4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2"
    ]
    notebook_sha256: Literal["cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7"]
    runtime_script_sha256: Literal[
        "d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67"
    ]
    wrapper_code_sha256: Literal["55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c"]
    v5_acceptance_sha256: Literal[
        "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
    ]
    operator_confirmation_recorded: Literal[True]
    operator_confirmed_at: datetime
    platform_observed_at: datetime
    platform_accelerator: Literal["T4_X2"]
    allocated_gpu_count: Literal[2]
    internet_enabled: Literal[False]
    execution_limits: ExecutionLimits
    expected_evidence_members: tuple[str, ...]
    expected_evidence_zip: Literal["ag-exact-runtime-p5-p6-requal-evidence-v1.zip"]
    runtime_execution_authorized: Literal[True]
    single_use: Literal[True]
    every_terminal_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    next_gate: Literal["EXECUTE_ONE_GOVERNED_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"]

    @field_validator(
        "issued_at",
        "expires_at",
        "operator_confirmed_at",
        "platform_observed_at",
    )
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return _normalize_time(value, "authorization timestamp")

    @model_validator(mode="after")
    def validate_window_and_contract(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        expected_expiry = self.issued_at + timedelta(minutes=self.authorization_window_minutes)
        if self.expires_at != expected_expiry:
            raise ValueError("authorization expiry does not match governed window")
        if self.expected_evidence_members != EXPECTED_RUNTIME_OUTPUTS:
            raise ValueError("expected runtime evidence contract drifted")
        return self


class AuthorizationTerminalReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    receipt_id: Literal[
        "auragateway-exact-runtime-p5-p6-requalification-v1-authorization-terminal-v1"
    ]
    authorization_id: Literal[
        "auragateway-exact-runtime-p5-p6-requalification-v1-execution-authorization"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    disposition: TerminalDisposition
    execution_attempted: bool
    execution_outcome: ExecutionOutcome | None = None
    terminalized_at: datetime
    saved_version_id: int | None = Field(default=None, ge=1)
    evidence_zip_sha256: str | None = None
    terminal_log_sha256: str | None = None
    authorization_reusable: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "PRESERVE_AND_ACCEPT_OR_CLASSIFY_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EVIDENCE"
    ] = NEXT_GATE_AFTER_TERMINAL

    @field_validator("terminalized_at")
    @classmethod
    def normalize_terminal_time(cls, value: datetime) -> datetime:
        return _normalize_time(value, "terminalized_at")

    @field_validator("evidence_zip_sha256", "terminal_log_sha256")
    @classmethod
    def validate_optional_hash(cls, value: str | None) -> str | None:
        if value is not None and not _is_sha256(value):
            raise ValueError("optional evidence hash is not a SHA-256")
        return value

    @model_validator(mode="after")
    def validate_terminal_semantics(self) -> Self:
        unused = {
            TerminalDisposition.EXPIRED_UNUSED,
            TerminalDisposition.CANCELLED_UNUSED,
            TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
        }
        if self.disposition in unused:
            if self.execution_attempted:
                raise ValueError("unused terminal disposition cannot follow an attempt")
            if self.execution_outcome is not None:
                raise ValueError("unused terminal disposition cannot have execution outcome")
        if self.disposition == TerminalDisposition.CONSUMED:
            if not self.execution_attempted or self.execution_outcome is None:
                raise ValueError("CONSUMED requires an execution attempt and known outcome")
            evidence_required = {
                ExecutionOutcome.PASSED,
                ExecutionOutcome.FAILED,
                ExecutionOutcome.AMBIGUOUS,
                ExecutionOutcome.DIAGNOSTIC_INVALID,
            }
            if self.execution_outcome in evidence_required and (
                self.saved_version_id is None or self.evidence_zip_sha256 is None
            ):
                raise ValueError("known terminal result requires saved version and evidence")
        if self.disposition == TerminalDisposition.OUTCOME_UNKNOWN:
            if not self.execution_attempted:
                raise ValueError("OUTCOME_UNKNOWN requires an execution attempt")
            if self.execution_outcome is not None:
                raise ValueError("OUTCOME_UNKNOWN cannot claim a known execution outcome")
        return self


class IssuerArchitectureReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-exact-runtime-p5-p6-execution-authorization-v1-review"]
    status: Literal["APPROVED_FOR_MERGE_NOT_ISSUANCE"]
    base_main_commit: Literal["2877f66a112a89c313c322bd38c3f71f9caff218"]
    authorization_design_record_sha256: Literal[
        "18eef4f455e67ef850cb2a4ff6502360b8885d2fff7e36ddcca7dcb6f15af230"
    ]
    p5_p6_implementation_merge_commit: Literal["9cc06c02c372fa2e7637c432759e7a1d4db56e9e"]
    lifecycle_operations: tuple[str, ...]
    terminal_dispositions: tuple[TerminalDisposition, ...]
    execution_outcomes: tuple[ExecutionOutcome, ...]
    controls: tuple[str, ...]
    non_claims: tuple[str, ...]
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False


class IssuerImplementationRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-exact-runtime-p5-p6-execution-authorization-v1-implementation"]
    status: Literal["IMPLEMENTED_NOT_ISSUED"]
    base_main_commit: Literal["2877f66a112a89c313c322bd38c3f71f9caff218"]
    authorization_design_merge_commit: Literal["2877f66a112a89c313c322bd38c3f71f9caff218"]
    authorization_design_record: ArtifactIdentity
    p5_p6_implementation_merge_commit: Literal["9cc06c02c372fa2e7637c432759e7a1d4db56e9e"]
    bound_artifacts: tuple[ArtifactIdentity, ...]
    implementation_artifacts: tuple[ArtifactIdentity, ...]
    review: ArtifactIdentity
    authorization_path: str
    terminal_receipt_path: str
    transfer_filename: Literal["execution_authorization_v1.json"]
    execution_limits: ExecutionLimits
    freshness: dict[str, int]
    terminal_dispositions: tuple[TerminalDisposition, ...]
    execution_outcomes: tuple[ExecutionOutcome, ...]
    issuer_merge_commit_bound_at_issue: Literal[True] = True
    fresh_platform_observation_required_at_issue: Literal[True] = True
    fresh_operator_confirmation_required_at_issue: Literal[True] = True
    implementation_revalidation_required_at_issue: Literal[True] = True
    semantic_boundary_revalidation_required_at_issue: Literal[True] = True
    non_overwriting_lifecycle_required: Literal[True] = True
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "MERGE_EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_ISSUER_V1_WITHOUT_ISSUING"
    ]


BOUND_ARTIFACTS: Final = (
    (
        "p5_p6_design_record",
        P5_P6_DESIGN_RECORD_PATH,
        P5_P6_DESIGN_RECORD_SHA256,
    ),
    (
        "p5_p6_implementation_record",
        P5_P6_IMPLEMENTATION_RECORD_PATH,
        P5_P6_IMPLEMENTATION_RECORD_SHA256,
    ),
    (
        "p5_p6_implementation_review",
        P5_P6_IMPLEMENTATION_REVIEW_PATH,
        P5_P6_IMPLEMENTATION_REVIEW_SHA256,
    ),
    (
        "p5_p6_implementation_source",
        P5_P6_IMPLEMENTATION_SOURCE_PATH,
        P5_P6_IMPLEMENTATION_SOURCE_SHA256,
    ),
    (
        "p5_p6_implementation_template",
        P5_P6_IMPLEMENTATION_TEMPLATE_PATH,
        P5_P6_IMPLEMENTATION_TEMPLATE_SHA256,
    ),
    (
        "p5_p6_implementation_tests",
        P5_P6_IMPLEMENTATION_TEST_PATH,
        P5_P6_IMPLEMENTATION_TEST_SHA256,
    ),
    (
        "p5_p6_notebook",
        P5_P6_NOTEBOOK_PATH,
        P5_P6_NOTEBOOK_SHA256,
    ),
    (
        "p5_p6_provenance_reconciliation_source",
        P5_P6_PROVENANCE_RECONCILIATION_SOURCE_PATH,
        P5_P6_PROVENANCE_RECONCILIATION_SOURCE_SHA256,
    ),
    (
        "p5_p6_provenance_reconciliation_tests",
        P5_P6_PROVENANCE_RECONCILIATION_TEST_PATH,
        P5_P6_PROVENANCE_RECONCILIATION_TEST_SHA256,
    ),
    (
        "p5_p6_provenance_reconciliation_record",
        P5_P6_PROVENANCE_RECONCILIATION_RECORD_PATH,
        P5_P6_PROVENANCE_RECONCILIATION_RECORD_SHA256,
    ),
    (
        "v5_acceptance_record",
        V5_ACCEPTANCE_RECORD_PATH,
        V5_ACCEPTANCE_RECORD_SHA256,
    ),
)
IMPLEMENTATION_STATIC_PATHS: Final = (
    SOURCE_PATH,
    TEST_PATH,
    ADR_PATH,
    REPORT_PATH,
    RUNBOOK_PATH,
)


def _normalize_time(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC).replace(microsecond=0)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _canonical_json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        payload: object = value.model_dump(mode="json")
    else:
        payload = value
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _raise(
    code: str,
    message: str,
    path: Path | None = None,
    details: tuple[str, ...] = (),
) -> Never:
    raise AuthorizationIssuerError(
        code,
        message,
        None if path is None else path.as_posix(),
        details,
    )


def _artifact(
    repo_root: Path,
    role: str,
    relative_path: Path,
    expected_sha256: str | None = None,
) -> ArtifactIdentity:
    target = repo_root / relative_path
    if not target.is_file() or target.is_symlink():
        _raise(
            "P5_P6_AUTHORIZATION_ARTIFACT_MISSING",
            "required authorization artifact is missing or unsafe",
            relative_path,
        )
    payload = target.read_bytes()
    observed_sha = _sha256_bytes(payload)
    if expected_sha256 is not None and observed_sha != expected_sha256:
        _raise(
            "P5_P6_AUTHORIZATION_ARTIFACT_IDENTITY_DRIFT",
            "required authorization artifact identity drifted",
            relative_path,
        )
    return ArtifactIdentity(
        role=role,
        path=relative_path.as_posix(),
        sha256=observed_sha,
        size_bytes=len(payload),
    )


def _bound_artifacts(repo_root: Path) -> tuple[ArtifactIdentity, ...]:
    return tuple(
        _artifact(repo_root, role, path, expected_sha)
        for role, path, expected_sha in BOUND_ARTIFACTS
    )


def _implementation_artifacts(repo_root: Path) -> tuple[ArtifactIdentity, ...]:
    return tuple(
        _artifact(repo_root, f"issuer_{path.stem}", path) for path in IMPLEMENTATION_STATIC_PATHS
    )


def _read_json_object(repo_root: Path, relative_path: Path) -> dict[str, object]:
    target = repo_root / relative_path
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _raise(
            "P5_P6_AUTHORIZATION_JSON_INVALID",
            "required authorization authority is invalid JSON",
            relative_path,
            (str(error),),
        )
    if not isinstance(payload, dict):
        _raise(
            "P5_P6_AUTHORIZATION_JSON_INVALID",
            "required authorization authority is not a JSON object",
            relative_path,
        )
    return cast(dict[str, object], payload)


def _validate_authorization_design(repo_root: Path) -> ArtifactIdentity:
    identity = _artifact(
        repo_root,
        "authorization_design_record",
        AUTHORIZATION_DESIGN_RECORD_PATH,
        AUTHORIZATION_DESIGN_RECORD_SHA256,
    )
    if identity.size_bytes != AUTHORIZATION_DESIGN_RECORD_SIZE:
        _raise(
            "P5_P6_AUTHORIZATION_DESIGN_SIZE_DRIFT",
            "authorization design record size drifted",
            AUTHORIZATION_DESIGN_RECORD_PATH,
        )
    record = _read_json_object(repo_root, AUTHORIZATION_DESIGN_RECORD_PATH)
    required: dict[str, object] = {
        "design_status": "DESIGN_FROZEN_NOT_IMPLEMENTED",
        "record_id": "auragateway-exact-runtime-p5-p6-execution-authorization-design-v1",
        "base_main_commit": P5_P6_IMPLEMENTATION_MERGE_COMMIT,
    }
    drift = tuple(key for key, expected in required.items() if record.get(key) != expected)
    if drift:
        _raise(
            "P5_P6_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "merged authorization design semantics drifted",
            AUTHORIZATION_DESIGN_RECORD_PATH,
            drift,
        )
    safety = record.get("safety")
    if not isinstance(safety, dict):
        _raise(
            "P5_P6_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "authorization design safety contract is missing",
            AUTHORIZATION_DESIGN_RECORD_PATH,
        )
    for key in (
        "live_authorization_issued",
        "runtime_execution_authorized",
        "p5_p6_exact_runtime_requalified",
        "pilot_execution_authorized",
        "final_measured_abc_execution_authorized",
    ):
        if safety.get(key) is not False:
            _raise(
                "P5_P6_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
                f"authorization design safety field drifted: {key}",
                AUTHORIZATION_DESIGN_RECORD_PATH,
            )
    return identity


def _validate_p5_p6_semantics(repo_root: Path) -> None:
    record = _read_json_object(repo_root, P5_P6_IMPLEMENTATION_RECORD_PATH)
    required: dict[str, object] = {
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "next_gate": (
            "DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION_AUTHORIZATION_ISSUER"
        ),
    }
    drift = tuple(key for key, expected in required.items() if record.get(key) != expected)
    if drift:
        _raise(
            "P5_P6_AUTHORIZATION_IMPLEMENTATION_SEMANTIC_DRIFT",
            "bound P5/P6 implementation semantics drifted",
            P5_P6_IMPLEMENTATION_RECORD_PATH,
            drift,
        )
    consumer = record.get("authorization_consumer")
    if not isinstance(consumer, dict):
        _raise(
            "P5_P6_AUTHORIZATION_CONSUMER_CONTRACT_MISSING",
            "P5/P6 authorization consumer contract is missing",
            P5_P6_IMPLEMENTATION_RECORD_PATH,
        )
    expected_consumer: dict[str, object] = {
        "authorization_filename": AUTHORIZATION_TRANSFER_FILENAME,
        "authorization_scope": AUTHORIZATION_SCOPE,
        "decision_required": "AUTHORIZED",
        "lifecycle_required": "ISSUED",
        "runtime_script_sha256_binding_required": True,
        "implementation_review_sha256_binding_required": True,
        "design_record_sha256_binding_required": True,
        "v5_acceptance_sha256_binding_required": True,
        "live_time_window_required": True,
        "single_use_required": True,
        "every_terminal_attempt_consumes_authorization": True,
        "unchanged_replay_authorized": False,
    }
    consumer_drift = tuple(
        key for key, expected in expected_consumer.items() if consumer.get(key) != expected
    )
    if consumer_drift:
        _raise(
            "P5_P6_AUTHORIZATION_CONSUMER_CONTRACT_DRIFT",
            "P5/P6 runtime authorization consumer contract drifted",
            P5_P6_IMPLEMENTATION_RECORD_PATH,
            consumer_drift,
        )
    semantic = record.get("semantic_boundary")
    if not isinstance(semantic, dict):
        _raise(
            "P5_P6_AUTHORIZATION_SEMANTIC_BOUNDARY_MISSING",
            "P5/P6 semantic boundary contract is missing",
            P5_P6_IMPLEMENTATION_RECORD_PATH,
        )
    required_semantic: dict[str, object] = {
        "raw_observation_type": "RawRuntimeObservation",
        "typed_observation_type": "TypedSemanticObservation",
        "decision_type": "BehaviorDecision",
        "evidence_projection_type": "EvidenceProjection",
        "public_evidence_used_as_semantic_input": False,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
    }
    semantic_drift = tuple(
        key for key, expected in required_semantic.items() if semantic.get(key) != expected
    )
    if semantic_drift:
        _raise(
            "P5_P6_AUTHORIZATION_SEMANTIC_BOUNDARY_DRIFT",
            "P5/P6 semantic boundary contract drifted",
            P5_P6_IMPLEMENTATION_RECORD_PATH,
            semantic_drift,
        )


def _validate_provenance_reconciliation_semantics(repo_root: Path) -> None:
    record = _read_json_object(
        repo_root,
        P5_P6_PROVENANCE_RECONCILIATION_RECORD_PATH,
    )
    required: dict[str, object] = {
        "status": "RECONCILED_BEFORE_EXECUTION",
        "root_cause": "PRE_COMMIT_PROVENANCE_IDENTITY_DEFECT",
        "implementation_merge_commit": P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        "authorization_must_bind_reconciliation_record": True,
        "original_review_claims_superseded_only_for_corrected_paths": True,
        "executable_runtime_identity_changed": False,
    }
    drift = tuple(key for key, expected in required.items() if record.get(key) != expected)
    if drift:
        _raise(
            "P5_P6_AUTHORIZATION_PROVENANCE_RECONCILIATION_DRIFT",
            "P5/P6 provenance reconciliation semantics drifted",
            P5_P6_PROVENANCE_RECONCILIATION_RECORD_PATH,
            drift,
        )
    safety = record.get("safety")
    if not isinstance(safety, dict):
        _raise(
            "P5_P6_AUTHORIZATION_PROVENANCE_RECONCILIATION_DRIFT",
            "P5/P6 provenance reconciliation safety state is missing",
            P5_P6_PROVENANCE_RECONCILIATION_RECORD_PATH,
        )
    for key in (
        "live_authorization_issued",
        "runtime_execution_authorized",
        "p5_p6_exact_runtime_requalified",
        "pilot_execution_authorized",
        "final_measured_abc_execution_authorized",
        "runtime_execution_performed",
    ):
        if safety.get(key) is not False:
            _raise(
                "P5_P6_AUTHORIZATION_PROVENANCE_RECONCILIATION_DRIFT",
                f"P5/P6 provenance reconciliation safety field drifted: {key}",
                P5_P6_PROVENANCE_RECONCILIATION_RECORD_PATH,
            )


def _validate_runtime_consumer_source(repo_root: Path) -> None:
    source = (repo_root / P5_P6_IMPLEMENTATION_TEMPLATE_PATH).read_text(encoding="utf-8")
    required_fragments = (
        'AUTHORIZATION_FILENAME = "execution_authorization_v1.json"',
        'AUTHORIZATION_SCOPE = "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"',
        '"maximum_model_requests": 6',
        '"maximum_worker_starts": 3',
        '"maximum_model_loads": 3',
        '"hidden_retries_permitted": 0',
        "authorization = require_execution_authorization()",
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        _raise(
            "P5_P6_AUTHORIZATION_RUNTIME_CONSUMER_DRIFT",
            "runtime authorization consumer source drifted",
            P5_P6_IMPLEMENTATION_TEMPLATE_PATH,
            missing,
        )


def _build_review() -> IssuerArchitectureReview:
    return IssuerArchitectureReview(
        review_id="auragateway-exact-runtime-p5-p6-execution-authorization-v1-review",
        status="APPROVED_FOR_MERGE_NOT_ISSUANCE",
        base_main_commit=ISSUER_BASE_MAIN_COMMIT,
        authorization_design_record_sha256=AUTHORIZATION_DESIGN_RECORD_SHA256,
        p5_p6_implementation_merge_commit=P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        lifecycle_operations=(
            "validate-static-issuer",
            "validate-external-confirmation",
            "issue-single-use-authority",
            "validate-live-authority",
            "terminalize-authority",
        ),
        terminal_dispositions=tuple(TerminalDisposition),
        execution_outcomes=tuple(ExecutionOutcome),
        controls=(
            "exact merged design and implementation identity",
            "exact provenance reconciliation authority before issuance",
            "fresh platform observation at issuance",
            "fresh exact operator confirmation at issuance",
            "synchronized clean main at issuance",
            "exact issuer merge commit bound at issuance",
            "6 request / 3 worker-start / 3 model-load ceiling",
            "zero hidden retries, replacement workers, network requests, and spend",
            "one non-overwriting live authorization",
            "one non-overwriting terminal receipt",
            "terminal authority permanently non-reusable",
            "pilot and final measured A/B/C authority remain false",
        ),
        non_claims=(
            "Static issuer implementation does not issue live authority.",
            "Static issuer implementation does not execute model or worker code.",
            "Issuer merge does not qualify current exact-runtime P5 behavior.",
            "Issuer merge does not qualify current exact-runtime P6 behavior.",
            "Issuer merge does not authorize a variance pilot.",
            "Issuer merge does not authorize final measured A/B/C execution.",
        ),
    )


def _build_record(
    repo_root: Path,
    review_bytes: bytes,
) -> IssuerImplementationRecord:
    design_identity = _validate_authorization_design(repo_root)
    _bound_artifacts(repo_root)
    _validate_p5_p6_semantics(repo_root)
    _validate_provenance_reconciliation_semantics(repo_root)
    _validate_runtime_consumer_source(repo_root)
    implementation_artifacts = _implementation_artifacts(repo_root)
    return IssuerImplementationRecord(
        record_id=("auragateway-exact-runtime-p5-p6-execution-authorization-v1-implementation"),
        status="IMPLEMENTED_NOT_ISSUED",
        base_main_commit=ISSUER_BASE_MAIN_COMMIT,
        authorization_design_merge_commit=AUTHORIZATION_DESIGN_MERGE_COMMIT,
        authorization_design_record=design_identity,
        p5_p6_implementation_merge_commit=P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        bound_artifacts=_bound_artifacts(repo_root),
        implementation_artifacts=implementation_artifacts,
        review=ArtifactIdentity(
            role="issuer_architecture_review",
            path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
            size_bytes=len(review_bytes),
        ),
        authorization_path=AUTHORIZATION_PATH.as_posix(),
        terminal_receipt_path=TERMINAL_RECEIPT_PATH.as_posix(),
        transfer_filename=AUTHORIZATION_TRANSFER_FILENAME,
        execution_limits=ExecutionLimits(),
        freshness={
            "maximum_platform_observation_age_minutes": (MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES),
            "maximum_operator_confirmation_age_minutes": (
                MAXIMUM_OPERATOR_CONFIRMATION_AGE_MINUTES
            ),
            "maximum_authorization_window_minutes": MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
            "default_authorization_window_minutes": DEFAULT_AUTHORIZATION_WINDOW_MINUTES,
        },
        terminal_dispositions=tuple(TerminalDisposition),
        execution_outcomes=tuple(ExecutionOutcome),
        next_gate=NEXT_GATE_AFTER_STATIC_IMPLEMENTATION,
    )


def _require_no_lifecycle_artifact(repo_root: Path) -> None:
    present = tuple(
        path.as_posix()
        for path in (AUTHORIZATION_PATH, TERMINAL_RECEIPT_PATH)
        if (repo_root / path).exists()
    )
    if present:
        _raise(
            "P5_P6_AUTHORIZATION_LIFECYCLE_ALREADY_STARTED",
            "live or terminal authorization artifact already exists",
            details=present,
        )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(handle)
    temporary_path = Path(temporary)
    try:
        temporary_path.write_bytes(payload)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _write_non_overwriting(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _raise(
            "P5_P6_AUTHORIZATION_NON_OVERWRITE_VIOLATION",
            "authorization lifecycle artifact already exists",
            path,
        )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def generate(repo_root: Path) -> dict[str, object]:
    """Generate static review and issuer record without issuing authority."""

    root = repo_root.resolve()
    _require_no_lifecycle_artifact(root)
    review = _build_review()
    review_bytes = _canonical_json_bytes(review)
    record = _build_record(root, review_bytes)
    record_bytes = _canonical_json_bytes(record)
    _write_atomic(root / REVIEW_PATH, review_bytes)
    _write_atomic(root / RECORD_PATH, record_bytes)
    return {
        "status": record.status,
        "review_sha256": _sha256_bytes(review_bytes),
        "record_sha256": _sha256_bytes(record_bytes),
        "authorization_issuer_implemented": True,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "p5_p6_exact_runtime_requalified": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": record.next_gate,
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate the static issuer implementation and exact generated bytes."""

    root = repo_root.resolve()
    _require_no_lifecycle_artifact(root)
    review = _build_review()
    expected_review = _canonical_json_bytes(review)
    record = _build_record(root, expected_review)
    expected_record = _canonical_json_bytes(record)

    for path, expected in (
        (REVIEW_PATH, expected_review),
        (RECORD_PATH, expected_record),
    ):
        target = root / path
        if not target.is_file() or target.is_symlink():
            _raise(
                "P5_P6_AUTHORIZATION_ISSUER_GENERATED_ARTIFACT_MISSING",
                "issuer generated artifact is missing or unsafe",
                path,
            )
        if target.read_bytes() != expected:
            _raise(
                "P5_P6_AUTHORIZATION_ISSUER_GENERATED_ARTIFACT_DRIFT",
                "issuer generated artifact differs from deterministic bytes",
                path,
            )

    return {
        "status": "EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_ISSUER_V1_VALID",
        "record_sha256": _sha256_bytes(expected_record),
        "review_sha256": _sha256_bytes(expected_review),
        "authorization_design_merge_commit": AUTHORIZATION_DESIGN_MERGE_COMMIT,
        "p5_p6_implementation_merge_commit": P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        "authorization_issuer_implemented": True,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "p5_p6_exact_runtime_requalified": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE_AFTER_STATIC_IMPLEMENTATION,
    }


def _git(repo_root: Path, *arguments: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _require_git_success(
    repo_root: Path,
    code: str,
    message: str,
    *arguments: str,
) -> str:
    returncode, stdout, stderr = _git(repo_root, *arguments)
    if returncode != 0:
        details = () if not stderr else (stderr[-2000:],)
        _raise(code, message, details=details)
    return stdout


def _require_issue_repo_state(repo_root: Path, issuer_merge_commit: str) -> str:
    branch = _require_git_success(
        repo_root,
        "P5_P6_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect current branch",
        "branch",
        "--show-current",
    )
    if branch != "main":
        _raise(
            "P5_P6_AUTHORIZATION_NOT_ON_MAIN",
            "authorization issuance requires main",
        )
    head = _require_git_success(
        repo_root,
        "P5_P6_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect HEAD",
        "rev-parse",
        "HEAD",
    )
    origin_main = _require_git_success(
        repo_root,
        "P5_P6_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect origin/main",
        "rev-parse",
        "origin/main",
    )
    if head != issuer_merge_commit:
        _raise(
            "P5_P6_AUTHORIZATION_ISSUER_COMMIT_MISMATCH",
            "confirmed issuer merge commit does not equal HEAD",
        )
    if head != origin_main:
        _raise(
            "P5_P6_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "HEAD does not equal origin/main",
        )
    status = _require_git_success(
        repo_root,
        "P5_P6_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect repository status",
        "status",
        "--porcelain=v1",
        "-uall",
    )
    if status:
        _raise(
            "P5_P6_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
            "repository must be clean before authorization issuance",
        )
    for ancestor, code in (
        (
            AUTHORIZATION_DESIGN_MERGE_COMMIT,
            "P5_P6_AUTHORIZATION_DESIGN_NOT_ANCESTOR",
        ),
        (
            P5_P6_IMPLEMENTATION_MERGE_COMMIT,
            "P5_P6_AUTHORIZATION_IMPLEMENTATION_NOT_ANCESTOR",
        ),
    ):
        returncode, _, _ = _git(
            repo_root,
            "merge-base",
            "--is-ancestor",
            ancestor,
            head,
        )
        if returncode != 0:
            _raise(code, "required bound merge commit is not an ancestor of issuer main")
    return head


def _run_p5_validation(repo_root: Path) -> dict[str, object]:
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / P5_P6_PROVENANCE_RECONCILIATION_SOURCE_PATH),
            "validate",
            "--repo-root",
            str(repo_root),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip()
        details = () if not detail else (detail[-2000:],)
        _raise(
            "P5_P6_AUTHORIZATION_PREEXECUTION_VALIDATION_FAILED",
            "P5/P6 implementation validation failed before authorization",
            details=details,
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        _raise(
            "P5_P6_AUTHORIZATION_PREEXECUTION_VALIDATION_FAILED",
            "P5/P6 implementation validator returned invalid JSON",
            details=(str(error),),
        )
    if not isinstance(payload, dict):
        _raise(
            "P5_P6_AUTHORIZATION_PREEXECUTION_VALIDATION_FAILED",
            "P5/P6 implementation validator did not return an object",
        )
    return cast(dict[str, object], payload)


def _require_p5_preexecution_contract(repo_root: Path) -> None:
    payload = _run_p5_validation(repo_root)
    required: dict[str, object] = {
        "status": "EXACT_RUNTIME_P5_P6_PROVENANCE_IDENTITY_RECONCILIATION_V1_VALID",
        "implementation_provenance_consistent": True,
        "historical_generated_artifacts_retained": True,
        "executable_runtime_identity_changed": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": "REVALIDATE_EXACT_RUNTIME_P5_P6_EXECUTION_PRECONDITIONS_V1",
    }
    drift = tuple(key for key, expected in required.items() if payload.get(key) != expected)
    if drift:
        _raise(
            "P5_P6_AUTHORIZATION_PREEXECUTION_CONTRACT_DRIFT",
            "P5/P6 pre-execution implementation contract drifted",
            details=drift,
        )
    generated = payload.get("generated")
    if not isinstance(generated, dict):
        _raise(
            "P5_P6_AUTHORIZATION_PREEXECUTION_CONTRACT_DRIFT",
            "P5/P6 generated validation evidence is missing",
        )
    semantic = generated.get("semantic_boundary")
    if not isinstance(semantic, dict):
        _raise(
            "P5_P6_AUTHORIZATION_PREEXECUTION_CONTRACT_DRIFT",
            "P5/P6 semantic boundary validation evidence is missing",
        )
    semantic_required: dict[str, object] = {
        "public_evidence_used_as_semantic_input": False,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "authorization_precedes_runtime_installation": True,
    }
    semantic_drift = tuple(
        key for key, expected in semantic_required.items() if semantic.get(key) != expected
    )
    if semantic_drift:
        _raise(
            "P5_P6_AUTHORIZATION_SEMANTIC_BOUNDARY_REVALIDATION_FAILED",
            "P5/P6 semantic boundary revalidation drifted before authorization",
            details=semantic_drift,
        )


def _load_confirmation(path: Path) -> IssuanceConfirmation:
    if not path.is_file() or path.is_symlink():
        _raise(
            "P5_P6_AUTHORIZATION_CONFIRMATION_MISSING",
            "issuance confirmation JSON is missing or unsafe",
            path,
        )
    payload = path.read_bytes()
    try:
        parsed = json.loads(payload)
        confirmation = IssuanceConfirmation.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        _raise(
            "P5_P6_AUTHORIZATION_CONFIRMATION_INVALID",
            "issuance confirmation JSON is invalid",
            path,
            (str(error),),
        )
    canonical = _canonical_json_bytes(confirmation)
    if payload != canonical:
        _raise(
            "P5_P6_AUTHORIZATION_CONFIRMATION_NONCANONICAL",
            "issuance confirmation JSON is not canonical",
            path,
        )
    return confirmation


def _require_confirmation_fresh(
    confirmation: IssuanceConfirmation,
    now: datetime,
) -> None:
    observed_now = _normalize_time(now, "issuance time")
    if confirmation.exact_confirmation_phrase != CONFIRMATION_PHRASE:
        _raise(
            "P5_P6_AUTHORIZATION_CONFIRMATION_PHRASE_INVALID",
            "exact operator confirmation phrase is required",
        )
    if confirmation.confirmed_at > observed_now + timedelta(minutes=1):
        _raise(
            "P5_P6_AUTHORIZATION_CONFIRMATION_IN_FUTURE",
            "operator confirmation timestamp is in the future",
        )
    if confirmation.platform.observed_at > observed_now + timedelta(minutes=1):
        _raise(
            "P5_P6_AUTHORIZATION_PLATFORM_OBSERVATION_IN_FUTURE",
            "platform observation timestamp is in the future",
        )
    confirmation_age = observed_now - confirmation.confirmed_at
    platform_age = observed_now - confirmation.platform.observed_at
    if confirmation_age > timedelta(minutes=MAXIMUM_OPERATOR_CONFIRMATION_AGE_MINUTES):
        _raise(
            "P5_P6_AUTHORIZATION_CONFIRMATION_STALE",
            "operator confirmation is older than 15 minutes",
        )
    if platform_age > timedelta(minutes=MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES):
        _raise(
            "P5_P6_AUTHORIZATION_PLATFORM_OBSERVATION_STALE",
            "platform observation is older than 15 minutes",
        )


def _build_authorization(
    confirmation: IssuanceConfirmation,
    issuer_merge_commit: str,
    issued_at: datetime,
) -> ExecutionAuthorization:
    observed_issue_time = _normalize_time(issued_at, "issuance time")
    return ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle="ISSUED",
        scope=AUTHORIZATION_SCOPE,
        authorization_filename=AUTHORIZATION_TRANSFER_FILENAME,
        issued_at=observed_issue_time,
        expires_at=observed_issue_time
        + timedelta(minutes=confirmation.authorization_window_minutes),
        authorization_window_minutes=confirmation.authorization_window_minutes,
        issuer_merge_commit=issuer_merge_commit,
        authorization_design_merge_commit=AUTHORIZATION_DESIGN_MERGE_COMMIT,
        authorization_design_record_sha256=AUTHORIZATION_DESIGN_RECORD_SHA256,
        implementation_merge_commit=P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        implementation_record_sha256=P5_P6_IMPLEMENTATION_RECORD_SHA256,
        implementation_review_sha256=P5_P6_IMPLEMENTATION_REVIEW_SHA256,
        provenance_reconciliation_record_sha256=(P5_P6_PROVENANCE_RECONCILIATION_RECORD_SHA256),
        design_record_sha256=P5_P6_DESIGN_RECORD_SHA256,
        notebook_sha256=P5_P6_NOTEBOOK_SHA256,
        runtime_script_sha256=P5_P6_RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=P5_P6_WRAPPER_CODE_SHA256,
        v5_acceptance_sha256=V5_ACCEPTANCE_RECORD_SHA256,
        operator_confirmation_recorded=True,
        operator_confirmed_at=confirmation.confirmed_at,
        platform_observed_at=confirmation.platform.observed_at,
        platform_accelerator="T4_X2",
        allocated_gpu_count=2,
        internet_enabled=False,
        execution_limits=ExecutionLimits(),
        expected_evidence_members=EXPECTED_RUNTIME_OUTPUTS,
        expected_evidence_zip=EXPECTED_EVIDENCE_ZIP,
        runtime_execution_authorized=True,
        single_use=True,
        every_terminal_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        authorization_reusable=False,
        next_gate=NEXT_GATE_AFTER_ISSUE,
    )


def issue_authorization(
    repo_root: Path,
    *,
    confirmation: IssuanceConfirmation,
    now: datetime | None = None,
) -> dict[str, object]:
    """Issue one non-overwriting short-lived authorization after all gates pass."""

    root = repo_root.resolve()
    validate_implementation(root)
    _require_p5_preexecution_contract(root)
    _require_no_lifecycle_artifact(root)
    observed_now = _normalize_time(now or datetime.now(UTC), "issuance time")
    _require_confirmation_fresh(confirmation, observed_now)
    issuer_head = _require_issue_repo_state(
        root,
        confirmation.confirmed_issuer_merge_commit,
    )
    authorization = _build_authorization(confirmation, issuer_head, observed_now)
    payload = _canonical_json_bytes(authorization)
    _write_non_overwriting(root / AUTHORIZATION_PATH, payload)
    return {
        "status": "EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_V1_ISSUED",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "transfer_filename": AUTHORIZATION_TRANSFER_FILENAME,
        "authorization_sha256": _sha256_bytes(payload),
        "issuer_merge_commit": issuer_head,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "maximum_model_requests": authorization.execution_limits.maximum_model_requests,
        "maximum_worker_starts": authorization.execution_limits.maximum_worker_starts,
        "maximum_model_loads": authorization.execution_limits.maximum_model_loads,
        "live_authorization_issued": True,
        "runtime_execution_authorized": True,
        "p5_p6_exact_runtime_requalified": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "authorization_reusable": False,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }


def _read_authorization(repo_root: Path) -> tuple[ExecutionAuthorization, bytes]:
    target = repo_root / AUTHORIZATION_PATH
    if not target.is_file() or target.is_symlink():
        _raise(
            "P5_P6_AUTHORIZATION_MISSING",
            "live P5/P6 authorization file is missing or unsafe",
            AUTHORIZATION_PATH,
        )
    payload = target.read_bytes()
    try:
        parsed = json.loads(payload)
        authorization = ExecutionAuthorization.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        _raise(
            "P5_P6_AUTHORIZATION_INVALID",
            "live P5/P6 authorization is invalid",
            AUTHORIZATION_PATH,
            (str(error),),
        )
    if payload != _canonical_json_bytes(authorization):
        _raise(
            "P5_P6_AUTHORIZATION_NONCANONICAL",
            "live P5/P6 authorization bytes are not canonical",
            AUTHORIZATION_PATH,
        )
    return authorization, payload


def validate_live_authorization(
    repo_root: Path,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    """Validate one live authorization without mutating lifecycle state."""

    root = repo_root.resolve()
    authorization, payload = _read_authorization(root)
    if (root / TERMINAL_RECEIPT_PATH).exists():
        _raise(
            "P5_P6_AUTHORIZATION_ALREADY_TERMINAL",
            "authorization already has a terminal receipt",
            TERMINAL_RECEIPT_PATH,
        )
    observed_now = _normalize_time(now or datetime.now(UTC), "validation time")
    if observed_now < authorization.issued_at or observed_now >= authorization.expires_at:
        _raise(
            "P5_P6_AUTHORIZATION_OUTSIDE_VALID_WINDOW",
            "live authorization is outside its valid time window",
        )
    return {
        "status": "EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_V1_LIVE_VALID",
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": _sha256_bytes(payload),
        "issuer_merge_commit": authorization.issuer_merge_commit,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "runtime_execution_authorized": True,
        "p5_p6_exact_runtime_requalified": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "authorization_reusable": False,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }


def terminalize_authorization(
    repo_root: Path,
    *,
    disposition: TerminalDisposition,
    execution_outcome: ExecutionOutcome | None,
    saved_version_id: int | None,
    evidence_zip_sha256: str | None,
    terminal_log_sha256: str | None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Write the single non-overwriting terminal receipt for one authorization."""

    root = repo_root.resolve()
    authorization, payload = _read_authorization(root)
    if (root / TERMINAL_RECEIPT_PATH).exists():
        _raise(
            "P5_P6_AUTHORIZATION_ALREADY_TERMINAL",
            "authorization already has a terminal receipt",
            TERMINAL_RECEIPT_PATH,
        )
    observed_now = _normalize_time(now or datetime.now(UTC), "terminal time")
    unused = {
        TerminalDisposition.EXPIRED_UNUSED,
        TerminalDisposition.CANCELLED_UNUSED,
        TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
    }
    if (
        disposition == TerminalDisposition.EXPIRED_UNUSED
        and observed_now < authorization.expires_at
    ):
        _raise(
            "P5_P6_AUTHORIZATION_NOT_YET_EXPIRED",
            "EXPIRED_UNUSED requires the authorization window to have elapsed",
        )
    if (
        disposition
        in {
            TerminalDisposition.CANCELLED_UNUSED,
            TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
        }
        and observed_now >= authorization.expires_at
    ):
        _raise(
            "P5_P6_AUTHORIZATION_UNUSED_DISPOSITION_AFTER_EXPIRY",
            "use EXPIRED_UNUSED after authorization expiry",
        )
    execution_attempted = disposition not in unused
    receipt = AuthorizationTerminalReceipt(
        receipt_id=("auragateway-exact-runtime-p5-p6-requalification-v1-authorization-terminal-v1"),
        authorization_id=authorization.authorization_id,
        authorization_sha256=_sha256_bytes(payload),
        issuer_merge_commit=authorization.issuer_merge_commit,
        disposition=disposition,
        execution_attempted=execution_attempted,
        execution_outcome=execution_outcome,
        terminalized_at=observed_now,
        saved_version_id=saved_version_id,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
    )
    receipt_bytes = _canonical_json_bytes(receipt)
    _write_non_overwriting(root / TERMINAL_RECEIPT_PATH, receipt_bytes)
    return {
        "status": "EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_V1_TERMINAL",
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": _sha256_bytes(payload),
        "terminal_receipt_path": TERMINAL_RECEIPT_PATH.as_posix(),
        "terminal_receipt_sha256": _sha256_bytes(receipt_bytes),
        "disposition": disposition.value,
        "execution_attempted": execution_attempted,
        "execution_outcome": None if execution_outcome is None else execution_outcome.value,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "p5_p6_exact_runtime_requalified": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "authorization_reusable": False,
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }


def validate_confirmation_file(path: Path) -> dict[str, object]:
    confirmation = _load_confirmation(path)
    return {
        "status": "EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_CONFIRMATION_VALID",
        "confirmation_id": confirmation.confirmation_id,
        "confirmed_at": confirmation.confirmed_at.isoformat(),
        "platform_observed_at": confirmation.platform.observed_at.isoformat(),
        "authorization_window_minutes": confirmation.authorization_window_minutes,
        "runtime_execution_authorized": False,
        "live_authorization_issued": False,
    }


def _print_error(error: AuthorizationIssuerError) -> None:
    envelope = ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    )
    print(_canonical_json_bytes(envelope).decode("utf-8"), file=sys.stderr, end="")


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "generate",
            "validate-implementation",
            "validate-confirmation",
            "issue",
            "validate-live",
            "terminalize",
        ),
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--confirmation-json")
    parser.add_argument(
        "--disposition",
        choices=tuple(item.value for item in TerminalDisposition),
    )
    parser.add_argument(
        "--outcome",
        choices=tuple(item.value for item in ExecutionOutcome),
    )
    parser.add_argument("--saved-version-id", type=int)
    parser.add_argument("--evidence-zip-sha256")
    parser.add_argument("--terminal-log-sha256")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        result: object
        if args.command == "generate":
            result = generate(root)
        elif args.command == "validate-implementation":
            result = validate_implementation(root)
        elif args.command == "validate-confirmation":
            if args.confirmation_json is None:
                _raise(
                    "P5_P6_AUTHORIZATION_ARGUMENT_MISSING",
                    "--confirmation-json is required",
                )
            result = validate_confirmation_file(Path(args.confirmation_json))
        elif args.command == "issue":
            if args.confirmation_json is None:
                _raise(
                    "P5_P6_AUTHORIZATION_ARGUMENT_MISSING",
                    "--confirmation-json is required",
                )
            confirmation = _load_confirmation(Path(args.confirmation_json))
            result = issue_authorization(root, confirmation=confirmation)
        elif args.command == "validate-live":
            result = validate_live_authorization(root)
        else:
            if args.disposition is None:
                _raise(
                    "P5_P6_AUTHORIZATION_ARGUMENT_MISSING",
                    "--disposition is required",
                )
            outcome = None
            if args.outcome is not None:
                outcome = ExecutionOutcome(args.outcome)
            result = terminalize_authorization(
                root,
                disposition=TerminalDisposition(args.disposition),
                execution_outcome=outcome,
                saved_version_id=args.saved_version_id,
                evidence_zip_sha256=args.evidence_zip_sha256,
                terminal_log_sha256=args.terminal_log_sha256,
            )
    except AuthorizationIssuerError as error:
        _print_error(error)
        return 2
    except ValidationError as error:
        _print_error(
            AuthorizationIssuerError(
                "P5_P6_AUTHORIZATION_VALIDATION_ERROR",
                "authorization contract validation failed",
                details=(str(error),),
            )
        )
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
