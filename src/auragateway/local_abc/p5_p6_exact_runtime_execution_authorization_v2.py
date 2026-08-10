"""Govern one fresh Exact-Runtime P5/P6 Requalification V2 execution authority.

Static generation and validation are inert. Live authority can only be written
from synchronized clean ``main`` after this issuer is merged, after a fresh
operator confirmation and platform observation, after the merged V2
implementation revalidates, and after the candidate authorization round-trips
through the current governed authorization transport contract.
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

from auragateway.local_abc.p5_p6_exact_runtime_authorization_transport_v1 import (
    CONTROL_NOTEBOOK_NAME,
    CONTROL_OUTPUT_DIRECTORY_NAME,
    AuthorizationTransportError,
    materialize_control_package,
    validate_authorization_bytes,
    validate_control_package,
)

ISSUER_BASE_MAIN_COMMIT: Final = "f81fa4209efbd4ea7fbffc130705c6b1189c61d5"
P5_P6_IMPLEMENTATION_MERGE_COMMIT: Final = ISSUER_BASE_MAIN_COMMIT

AUTHORIZATION_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_execution_authorization_design_v2.json"
)
AUTHORIZATION_DESIGN_RECORD_SHA256: Final = (
    "1b1ef41610e298aac33b57e7deb2b96f8d69c73cd0cccbc9dc4c7e11be4b0fc2"
)
AUTHORIZATION_DESIGN_RECORD_SIZE: Final = 5420

P5_P6_IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_implementation_review.json"
)
P5_P6_IMPLEMENTATION_REVIEW_SHA256: Final = (
    "550dc3dbf78e12e951cb68774321731702f1e22734588508b246a7c18c5d39b2"
)
P5_P6_IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_implementation_record.json"
)
P5_P6_IMPLEMENTATION_RECORD_SHA256: Final = (
    "f814ad36d81eef259abd9374be4bf9100cac4579bfd3004d906ce69fc86cc635"
)
P5_P6_IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v2.py"
)
P5_P6_IMPLEMENTATION_SOURCE_SHA256: Final = (
    "5a91268ff616bf925bba5e0eafc80be4353f40e97ed5d5b01ea5c0a8feed50d6"
)
P5_P6_IMPLEMENTATION_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v2.py.tmpl"
)
P5_P6_IMPLEMENTATION_TEMPLATE_SHA256: Final = (
    "5af0c62de986c332a95ed5a97be14e35418448d9ad1427bc6321749765a2d48c"
)
P5_P6_IMPLEMENTATION_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v2.py"
)
P5_P6_IMPLEMENTATION_TEST_SHA256: Final = (
    "71091e28c2a3130f06e561625cb422e239f91fb0d4213c26908d3b4e1f9be827"
)
P5_P6_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p5_p6_exact_runtime_requalification_v2.ipynb"
)
P5_P6_NOTEBOOK_SHA256: Final = "ecf8adf4c5b2bcf557c2e10caa319f0d4b707fd7a24bd36c31525ee60b9d548a"
P5_P6_RUNTIME_SCRIPT_SHA256: Final = (
    "599b0395952abb0666e48890d4f25ad9050260837134a4c53716943a3d391df0"
)
P5_P6_WRAPPER_CODE_SHA256: Final = (
    "feba17d2caaba8169495943d58cbd68036515747507db239e0911aa2cca90721"
)
TRANSPORT_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_authorization_transport_remediation_design_v1.json"
)
TRANSPORT_DESIGN_RECORD_SHA256: Final = (
    "679c11a020e7381417f9f2fe0087f72ee10e9a454703609a1ab48c70da57d3bb"
)
TRANSPORT_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_authorization_transport_v1.py"
)
TRANSPORT_SOURCE_SHA256: Final = "7399da65bddc6ed84b7f8bcf49aa41c9bf8a3d5f8a857405d16061b0d25e7d7d"
TRANSPORT_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_authorization_transport_v1.py"
)
TRANSPORT_TEST_SHA256: Final = "0144e5392224a828d8f02d9ab11e5316325a15e7f2b6a955c1b90cab670d558a"
V5_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_evidence_acceptance_v1_record.json"
)
V5_ACCEPTANCE_RECORD_SHA256: Final = (
    "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_execution_authorization_v2.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_execution_authorization_v2.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-10-local-abc-exact-runtime-p5-p6-execution-authorization-v2.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Exact_Runtime_P5_P6_Execution_Authorization_V2.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_exact_runtime_p5_p6_execution_authorization_v2.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_execution_authorization_v2_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_execution_authorization_v2_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_execution_authorization.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_authorization_consumption.json"
)
AUTHORIZATION_TRANSFER_FILENAME: Final = "execution_authorization_v1.json"
AUTHORIZATION_ID: Final = (
    "auragateway-exact-runtime-p5-p6-requalification-v2-execution-authorization"
)
AUTHORIZATION_SCOPE: Final = "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"
CONFIRMATION_PHRASE: Final = (
    "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
    "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EXECUTION"
)

MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES: Final = 15
MAXIMUM_OPERATOR_CONFIRMATION_AGE_MINUTES: Final = 15
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
DEFAULT_AUTHORIZATION_WINDOW_MINUTES: Final = 180

NEXT_GATE_AFTER_STATIC_IMPLEMENTATION: Final = (
    "MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EXECUTION_AUTHORIZATION_ISSUER_WITHOUT_ISSUING"
)
NEXT_GATE_AFTER_ISSUE: Final = "MATERIALIZE_AND_ATTACH_GOVERNED_V2_AUTHORIZATION_CONTROL_OUTPUT"
NEXT_GATE_AFTER_TERMINAL: Final = (
    "PRESERVE_AND_ACCEPT_OR_CLASSIFY_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EVIDENCE"
)
EXPECTED_EVIDENCE_ZIP: Final = "ag-exact-runtime-p5-p6-requal-evidence-v2.zip"


class AuthorizationIssuerError(RuntimeError):
    """Metadata-safe fail-closed issuer error."""

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
        raise AuthorizationIssuerError("P5_P6_V2_AUTHORIZATION_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ErrorEnvelope(FrozenModel):
    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class TerminalDisposition(StrEnum):
    CONSUMED = "CONSUMED"
    EXPIRED_UNUSED = "EXPIRED_UNUSED"
    CANCELLED_UNUSED = "CANCELLED_UNUSED"
    ABANDONED_BEFORE_EXECUTION = "ABANDONED_BEFORE_EXECUTION"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class ExecutionOutcome(StrEnum):
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
        "auragateway-exact-runtime-p5-p6-execution-authorization-confirmation-v2"
    ]
    operator_confirmed: Literal[True]
    exact_confirmation_phrase: Literal[
        "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
        "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EXECUTION"
    ]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(
        ge=1,
        le=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
    )
    confirmed_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmed_authorization_design_record_sha256: Literal[
        "1b1ef41610e298aac33b57e7deb2b96f8d69c73cd0cccbc9dc4c7e11be4b0fc2"
    ]
    confirmed_scope: Literal["EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"]
    confirmed_implementation_merge_commit: Literal["f81fa4209efbd4ea7fbffc130705c6b1189c61d5"]
    confirmed_implementation_record_sha256: Literal[
        "f814ad36d81eef259abd9374be4bf9100cac4579bfd3004d906ce69fc86cc635"
    ]
    confirmed_implementation_review_sha256: Literal[
        "550dc3dbf78e12e951cb68774321731702f1e22734588508b246a7c18c5d39b2"
    ]
    confirmed_transport_design_sha256: Literal[
        "679c11a020e7381417f9f2fe0087f72ee10e9a454703609a1ab48c70da57d3bb"
    ]
    confirmed_notebook_sha256: Literal[
        "ecf8adf4c5b2bcf557c2e10caa319f0d4b707fd7a24bd36c31525ee60b9d548a"
    ]
    confirmed_runtime_script_sha256: Literal[
        "599b0395952abb0666e48890d4f25ad9050260837134a4c53716943a3d391df0"
    ]
    confirmed_wrapper_code_sha256: Literal[
        "feba17d2caaba8169495943d58cbd68036515747507db239e0911aa2cca90721"
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
        "auragateway-exact-runtime-p5-p6-requalification-v2-execution-authorization"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"]
    authorization_filename: Literal["execution_authorization_v1.json"]
    issued_at: datetime
    expires_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=240)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_record_sha256: Literal[
        "1b1ef41610e298aac33b57e7deb2b96f8d69c73cd0cccbc9dc4c7e11be4b0fc2"
    ]
    implementation_merge_commit: Literal["f81fa4209efbd4ea7fbffc130705c6b1189c61d5"]
    implementation_record_sha256: Literal[
        "f814ad36d81eef259abd9374be4bf9100cac4579bfd3004d906ce69fc86cc635"
    ]
    implementation_review_sha256: Literal[
        "550dc3dbf78e12e951cb68774321731702f1e22734588508b246a7c18c5d39b2"
    ]
    design_record_sha256: Literal[
        "679c11a020e7381417f9f2fe0087f72ee10e9a454703609a1ab48c70da57d3bb"
    ]
    notebook_sha256: Literal["ecf8adf4c5b2bcf557c2e10caa319f0d4b707fd7a24bd36c31525ee60b9d548a"]
    runtime_script_sha256: Literal[
        "599b0395952abb0666e48890d4f25ad9050260837134a4c53716943a3d391df0"
    ]
    wrapper_code_sha256: Literal["feba17d2caaba8169495943d58cbd68036515747507db239e0911aa2cca90721"]
    v5_acceptance_sha256: Literal[
        "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
    ]
    operator_confirmation_recorded: Literal[True]
    operator_confirmed_at: datetime
    platform_observed_at: datetime
    platform_accelerator: Literal["T4_X2"]
    allocated_gpu_count: Literal[2]
    internet_enabled: Literal[False]
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    hidden_retries_permitted: Literal[0] = 0
    replacement_workers_permitted: Literal[0] = 0
    network_requests_permitted: Literal[0] = 0
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0
    runtime_execution_authorized: Literal[True]
    single_use: Literal[True]
    every_terminal_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    expected_evidence_zip: Literal["ag-exact-runtime-p5-p6-requal-evidence-v2.zip"]
    next_gate: Literal["MATERIALIZE_AND_ATTACH_GOVERNED_V2_AUTHORIZATION_CONTROL_OUTPUT"]

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
    def validate_window(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        expected = self.issued_at + timedelta(minutes=self.authorization_window_minutes)
        if self.expires_at != expected:
            raise ValueError("authorization expiry does not match governed window")
        return self


class AuthorizationTerminalReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    receipt_id: Literal[
        "auragateway-exact-runtime-p5-p6-requalification-v2-authorization-terminal-v1"
    ]
    authorization_id: Literal[
        "auragateway-exact-runtime-p5-p6-requalification-v2-execution-authorization"
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
        "PRESERVE_AND_ACCEPT_OR_CLASSIFY_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EVIDENCE"
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
                raise ValueError("unused disposition cannot follow execution")
            if self.execution_outcome is not None:
                raise ValueError("unused disposition cannot have an outcome")
        if self.disposition == TerminalDisposition.CONSUMED:
            if not self.execution_attempted or self.execution_outcome is None:
                raise ValueError("CONSUMED requires a known execution attempt")
            evidence_required = {
                ExecutionOutcome.PASSED,
                ExecutionOutcome.FAILED,
                ExecutionOutcome.AMBIGUOUS,
                ExecutionOutcome.DIAGNOSTIC_INVALID,
            }
            if self.execution_outcome in evidence_required and (
                self.saved_version_id is None or self.evidence_zip_sha256 is None
            ):
                raise ValueError("known terminal result requires saved evidence")
        if self.disposition == TerminalDisposition.OUTCOME_UNKNOWN and (
            not self.execution_attempted or self.execution_outcome is not None
        ):
            raise ValueError("OUTCOME_UNKNOWN requires an uncertain attempt")
        return self


class IssuerArchitectureReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-exact-runtime-p5-p6-execution-authorization-v2-review"]
    status: Literal["APPROVED_FOR_MERGE_NOT_ISSUANCE"]
    base_main_commit: Literal["f81fa4209efbd4ea7fbffc130705c6b1189c61d5"]
    authorization_design_record_sha256: Literal[
        "1b1ef41610e298aac33b57e7deb2b96f8d69c73cd0cccbc9dc4c7e11be4b0fc2"
    ]
    p5_p6_implementation_merge_commit: Literal["f81fa4209efbd4ea7fbffc130705c6b1189c61d5"]
    transport_round_trip_required_at_issue: Literal[True] = True
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
    record_id: Literal["auragateway-exact-runtime-p5-p6-execution-authorization-v2-implementation"]
    status: Literal["IMPLEMENTED_NOT_ISSUED"]
    base_main_commit: Literal["f81fa4209efbd4ea7fbffc130705c6b1189c61d5"]
    authorization_design_record: ArtifactIdentity
    p5_p6_implementation_merge_commit: Literal["f81fa4209efbd4ea7fbffc130705c6b1189c61d5"]
    bound_artifacts: tuple[ArtifactIdentity, ...]
    implementation_artifacts: tuple[ArtifactIdentity, ...]
    review: ArtifactIdentity
    authorization_path: str
    terminal_receipt_path: str
    transfer_filename: Literal["execution_authorization_v1.json"]
    transport_contract: Literal["GOVERNED_ROOT_EXACT_FLAT_V1"]
    control_producer_notebook: Literal["ag-p5-p6-auth-control-v1"]
    control_output_directory: Literal["ag_p5_p6_auth_control_v1"]
    execution_limits: ExecutionLimits
    freshness: dict[str, int]
    terminal_dispositions: tuple[TerminalDisposition, ...]
    execution_outcomes: tuple[ExecutionOutcome, ...]
    transport_round_trip_required_at_issue: Literal[True] = True
    issuer_merge_commit_bound_at_issue: Literal[True] = True
    fresh_platform_observation_required_at_issue: Literal[True] = True
    fresh_operator_confirmation_required_at_issue: Literal[True] = True
    implementation_revalidation_required_at_issue: Literal[True] = True
    non_overwriting_lifecycle_required: Literal[True] = True
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_"
        "EXECUTION_AUTHORIZATION_ISSUER_WITHOUT_ISSUING"
    ]


BOUND_ARTIFACTS: Final = (
    (
        "v2_implementation_review",
        P5_P6_IMPLEMENTATION_REVIEW_PATH,
        P5_P6_IMPLEMENTATION_REVIEW_SHA256,
    ),
    (
        "v2_implementation_record",
        P5_P6_IMPLEMENTATION_RECORD_PATH,
        P5_P6_IMPLEMENTATION_RECORD_SHA256,
    ),
    (
        "v2_implementation_source",
        P5_P6_IMPLEMENTATION_SOURCE_PATH,
        P5_P6_IMPLEMENTATION_SOURCE_SHA256,
    ),
    (
        "v2_implementation_template",
        P5_P6_IMPLEMENTATION_TEMPLATE_PATH,
        P5_P6_IMPLEMENTATION_TEMPLATE_SHA256,
    ),
    ("v2_implementation_tests", P5_P6_IMPLEMENTATION_TEST_PATH, P5_P6_IMPLEMENTATION_TEST_SHA256),
    ("v2_notebook", P5_P6_NOTEBOOK_PATH, P5_P6_NOTEBOOK_SHA256),
    ("transport_design", TRANSPORT_DESIGN_RECORD_PATH, TRANSPORT_DESIGN_RECORD_SHA256),
    ("transport_source", TRANSPORT_SOURCE_PATH, TRANSPORT_SOURCE_SHA256),
    ("transport_tests", TRANSPORT_TEST_PATH, TRANSPORT_TEST_SHA256),
    ("v5_acceptance", V5_ACCEPTANCE_RECORD_PATH, V5_ACCEPTANCE_RECORD_SHA256),
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
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _artifact_json_bytes(value: object) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return (json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _transport_json_bytes(value: object) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
            "P5_P6_V2_AUTHORIZATION_ARTIFACT_MISSING",
            "required authorization artifact is missing or unsafe",
            relative_path,
        )
    payload = target.read_bytes()
    observed = _sha256_bytes(payload)
    if expected_sha256 is not None and observed != expected_sha256:
        _raise(
            "P5_P6_V2_AUTHORIZATION_ARTIFACT_IDENTITY_DRIFT",
            "required authorization artifact identity drifted",
            relative_path,
        )
    return ArtifactIdentity(
        role=role,
        path=relative_path.as_posix(),
        sha256=observed,
        size_bytes=len(payload),
    )


def _bound_artifacts(repo_root: Path) -> tuple[ArtifactIdentity, ...]:
    return tuple(
        _artifact(repo_root, role, path, expected) for role, path, expected in BOUND_ARTIFACTS
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
            "P5_P6_V2_AUTHORIZATION_JSON_INVALID",
            "required authority is invalid JSON",
            relative_path,
            (str(error),),
        )
    if not isinstance(payload, dict):
        _raise(
            "P5_P6_V2_AUTHORIZATION_JSON_INVALID",
            "required authority is not a JSON object",
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
            "P5_P6_V2_AUTHORIZATION_DESIGN_SIZE_DRIFT",
            "authorization design record size drifted",
            AUTHORIZATION_DESIGN_RECORD_PATH,
        )
    record = _read_json_object(repo_root, AUTHORIZATION_DESIGN_RECORD_PATH)
    required: dict[str, object] = {
        "design_status": "DESIGN_FROZEN_NOT_IMPLEMENTED",
        "record_id": "auragateway-exact-runtime-p5-p6-execution-authorization-design-v2",
        "base_main_commit": P5_P6_IMPLEMENTATION_MERGE_COMMIT,
    }
    drift = tuple(k for k, expected in required.items() if record.get(k) != expected)
    if drift:
        _raise(
            "P5_P6_V2_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "merged authorization design semantics drifted",
            AUTHORIZATION_DESIGN_RECORD_PATH,
            drift,
        )
    safety = record.get("safety")
    if not isinstance(safety, dict):
        _raise(
            "P5_P6_V2_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "authorization design safety contract is missing",
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
                "P5_P6_V2_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
                f"authorization design safety field drifted: {key}",
            )
    return identity


def _validate_v2_semantics(repo_root: Path) -> None:
    record = _read_json_object(repo_root, P5_P6_IMPLEMENTATION_RECORD_PATH)
    required: dict[str, object] = {
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "authorization_transport_remediated": True,
        "behavioral_core_preserved": True,
        "next_gate": (
            "DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EXECUTION_AUTHORIZATION_ISSUER"
        ),
    }
    drift = tuple(k for k, expected in required.items() if record.get(k) != expected)
    if drift:
        _raise(
            "P5_P6_V2_AUTHORIZATION_IMPLEMENTATION_SEMANTIC_DRIFT",
            "bound V2 implementation semantics drifted",
            P5_P6_IMPLEMENTATION_RECORD_PATH,
            drift,
        )
    consumer = record.get("authorization_consumer")
    if not isinstance(consumer, dict):
        _raise(
            "P5_P6_V2_AUTHORIZATION_CONSUMER_MISSING",
            "V2 authorization consumer contract is missing",
        )
    expected_consumer: dict[str, object] = {
        "authorization_filename": AUTHORIZATION_TRANSFER_FILENAME,
        "authorization_scope": AUTHORIZATION_SCOPE,
        "decision_required": "AUTHORIZED",
        "lifecycle_required": "ISSUED",
        "governed_root_resolved_before_filename": True,
        "exact_flat_control_file_count": 3,
        "global_filename_uniqueness_required": False,
        "unscoped_recursive_authorization_search_permitted": False,
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
        k for k, expected in expected_consumer.items() if consumer.get(k) != expected
    )
    if consumer_drift:
        _raise(
            "P5_P6_V2_AUTHORIZATION_CONSUMER_DRIFT",
            "V2 authorization consumer contract drifted",
            details=consumer_drift,
        )


def _validate_runtime_consumer_source(repo_root: Path) -> None:
    source = (repo_root / P5_P6_IMPLEMENTATION_TEMPLATE_PATH).read_text(encoding="utf-8")
    required = (
        'AUTHORIZATION_SCOPE = "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"',
        'AUTHORIZATION_CONTROL_NOTEBOOK_NAME = "ag-p5-p6-auth-control-v1"',
        'AUTHORIZATION_CONTROL_OUTPUT_DIRECTORY = "ag_p5_p6_auth_control_v1"',
        'AUTHORIZATION_TRANSPORT_CONTRACT = "GOVERNED_ROOT_EXACT_FLAT_V1"',
        "authorization = require_execution_authorization()",
    )
    missing = tuple(fragment for fragment in required if fragment not in source)
    if missing:
        _raise(
            "P5_P6_V2_AUTHORIZATION_RUNTIME_CONSUMER_DRIFT",
            "runtime authorization consumer source drifted",
            P5_P6_IMPLEMENTATION_TEMPLATE_PATH,
            missing,
        )


def _build_review() -> IssuerArchitectureReview:
    return IssuerArchitectureReview(
        review_id="auragateway-exact-runtime-p5-p6-execution-authorization-v2-review",
        status="APPROVED_FOR_MERGE_NOT_ISSUANCE",
        base_main_commit=ISSUER_BASE_MAIN_COMMIT,
        authorization_design_record_sha256=AUTHORIZATION_DESIGN_RECORD_SHA256,
        p5_p6_implementation_merge_commit=P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        lifecycle_operations=(
            "validate-static-issuer",
            "validate-external-confirmation",
            "preflight-current-transport-round-trip",
            "issue-single-use-authority",
            "validate-live-authority",
            "terminalize-authority",
        ),
        terminal_dispositions=tuple(TerminalDisposition),
        execution_outcomes=tuple(ExecutionOutcome),
        controls=(
            "exact merged V2 implementation and transport identities",
            "fresh platform observation and exact operator confirmation",
            "synchronized clean main and exact issuer merge binding",
            "current authorization producer/consumer round trip before live write",
            "governed-root exact-flat transport contract",
            "6 request / 3 worker-start / 3 model-load ceiling",
            "zero hidden retries, replacement workers, network requests, and spend",
            "one non-overwriting authorization and one terminal receipt",
            "terminal authority permanently non-reusable",
            "pilot and final measured A/B/C authority remain false",
        ),
        non_claims=(
            "Static issuer implementation does not issue live authority.",
            "Static issuer implementation does not execute Kaggle or model code.",
            "Issuer merge does not requalify P5 or P6 behavior.",
            "Issuer merge does not authorize pilot or final measured A/B/C execution.",
        ),
    )


def _build_record(repo_root: Path, review_bytes: bytes) -> IssuerImplementationRecord:
    design_identity = _validate_authorization_design(repo_root)
    _bound_artifacts(repo_root)
    _validate_v2_semantics(repo_root)
    _validate_runtime_consumer_source(repo_root)
    return IssuerImplementationRecord(
        record_id=("auragateway-exact-runtime-p5-p6-execution-authorization-v2-implementation"),
        status="IMPLEMENTED_NOT_ISSUED",
        base_main_commit=ISSUER_BASE_MAIN_COMMIT,
        authorization_design_record=design_identity,
        p5_p6_implementation_merge_commit=P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        bound_artifacts=_bound_artifacts(repo_root),
        implementation_artifacts=_implementation_artifacts(repo_root),
        review=ArtifactIdentity(
            role="issuer_architecture_review",
            path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
            size_bytes=len(review_bytes),
        ),
        authorization_path=AUTHORIZATION_PATH.as_posix(),
        terminal_receipt_path=TERMINAL_RECEIPT_PATH.as_posix(),
        transfer_filename=AUTHORIZATION_TRANSFER_FILENAME,
        transport_contract="GOVERNED_ROOT_EXACT_FLAT_V1",
        control_producer_notebook=CONTROL_NOTEBOOK_NAME,
        control_output_directory=CONTROL_OUTPUT_DIRECTORY_NAME,
        execution_limits=ExecutionLimits(),
        freshness={
            "maximum_platform_observation_age_minutes": 15,
            "maximum_operator_confirmation_age_minutes": 15,
            "maximum_authorization_window_minutes": 240,
            "default_authorization_window_minutes": 180,
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
            "P5_P6_V2_AUTHORIZATION_LIFECYCLE_ALREADY_STARTED",
            "live or terminal V2 authorization artifact already exists",
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
            "P5_P6_V2_AUTHORIZATION_NON_OVERWRITE_VIOLATION",
            "authorization lifecycle artifact already exists",
            path,
        )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _require_no_lifecycle_artifact(root)
    review_bytes = _artifact_json_bytes(_build_review())
    record_bytes = _artifact_json_bytes(_build_record(root, review_bytes))
    _write_atomic(root / REVIEW_PATH, review_bytes)
    _write_atomic(root / RECORD_PATH, record_bytes)
    return {
        "status": "IMPLEMENTED_NOT_ISSUED",
        "review_sha256": _sha256_bytes(review_bytes),
        "record_sha256": _sha256_bytes(record_bytes),
        "authorization_issuer_implemented": True,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE_AFTER_STATIC_IMPLEMENTATION,
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _require_no_lifecycle_artifact(root)
    expected_review = _artifact_json_bytes(_build_review())
    expected_record = _artifact_json_bytes(_build_record(root, expected_review))
    for path, expected in ((REVIEW_PATH, expected_review), (RECORD_PATH, expected_record)):
        target = root / path
        if not target.is_file() or target.is_symlink():
            _raise(
                "P5_P6_V2_AUTHORIZATION_GENERATED_ARTIFACT_MISSING",
                "issuer generated artifact is missing or unsafe",
                path,
            )
        if target.read_bytes() != expected:
            _raise(
                "P5_P6_V2_AUTHORIZATION_GENERATED_ARTIFACT_DRIFT",
                "issuer generated artifact differs from deterministic bytes",
                path,
            )
    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_EXECUTION_AUTHORIZATION_ISSUER_VALID",
        "review_sha256": _sha256_bytes(expected_review),
        "record_sha256": _sha256_bytes(expected_record),
        "v2_implementation_merge_commit": P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        "transport_round_trip_required_at_issue": True,
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
        "P5_P6_V2_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect current branch",
        "branch",
        "--show-current",
    )
    if branch != "main":
        _raise("P5_P6_V2_AUTHORIZATION_NOT_ON_MAIN", "issuance requires main")
    head = _require_git_success(
        repo_root,
        "P5_P6_V2_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect HEAD",
        "rev-parse",
        "HEAD",
    )
    origin_main = _require_git_success(
        repo_root,
        "P5_P6_V2_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect origin/main",
        "rev-parse",
        "origin/main",
    )
    if head != issuer_merge_commit:
        _raise(
            "P5_P6_V2_AUTHORIZATION_ISSUER_COMMIT_MISMATCH",
            "confirmed issuer merge commit does not equal HEAD",
        )
    if head != origin_main:
        _raise(
            "P5_P6_V2_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "HEAD does not equal origin/main",
        )
    status = _require_git_success(
        repo_root,
        "P5_P6_V2_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect repository status",
        "status",
        "--porcelain=v1",
        "-uall",
    )
    if status:
        _raise(
            "P5_P6_V2_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
            "repository must be clean before authorization issuance",
        )
    returncode, _, _ = _git(
        repo_root,
        "merge-base",
        "--is-ancestor",
        P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        head,
    )
    if returncode != 0:
        _raise(
            "P5_P6_V2_AUTHORIZATION_IMPLEMENTATION_NOT_ANCESTOR",
            "merged V2 implementation is not an ancestor of issuer main",
        )
    return head


def _run_v2_validation(repo_root: Path) -> dict[str, object]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "auragateway.local_abc.p5_p6_exact_runtime_requalification_v2",
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
        _raise(
            "P5_P6_V2_AUTHORIZATION_PREEXECUTION_VALIDATION_FAILED",
            "merged V2 implementation validation failed before authorization",
            details=() if not detail else (detail[-2000:],),
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        _raise(
            "P5_P6_V2_AUTHORIZATION_PREEXECUTION_VALIDATION_FAILED",
            "V2 implementation validator returned invalid JSON",
            details=(str(error),),
        )
    if not isinstance(payload, dict):
        _raise(
            "P5_P6_V2_AUTHORIZATION_PREEXECUTION_VALIDATION_FAILED",
            "V2 implementation validator did not return an object",
        )
    return cast(dict[str, object], payload)


def _require_v2_preexecution_contract(repo_root: Path) -> None:
    payload = _run_v2_validation(repo_root)
    required: dict[str, object] = {
        "status": "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_IMPLEMENTATION_VALID",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "fresh_authorization_issued": False,
    }
    drift = tuple(k for k, expected in required.items() if payload.get(k) != expected)
    if drift:
        _raise(
            "P5_P6_V2_AUTHORIZATION_PREEXECUTION_CONTRACT_DRIFT",
            "V2 pre-execution implementation contract drifted",
            details=drift,
        )
    notebook = payload.get("notebook")
    if not isinstance(notebook, dict):
        _raise(
            "P5_P6_V2_AUTHORIZATION_PREEXECUTION_CONTRACT_DRIFT",
            "V2 notebook validation evidence is missing",
        )
    semantic = notebook.get("semantic_boundary")
    transport = notebook.get("authorization_transport")
    if not isinstance(semantic, dict) or not isinstance(transport, dict):
        _raise(
            "P5_P6_V2_AUTHORIZATION_PREEXECUTION_CONTRACT_DRIFT",
            "V2 semantic or transport validation evidence is missing",
        )
    semantic_required: dict[str, object] = {
        "public_evidence_used_as_semantic_input": False,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "authorization_precedes_runtime_installation": True,
    }
    semantic_drift = tuple(
        k for k, expected in semantic_required.items() if semantic.get(k) != expected
    )
    if semantic_drift:
        _raise(
            "P5_P6_V2_AUTHORIZATION_SEMANTIC_BOUNDARY_REVALIDATION_FAILED",
            "V2 semantic boundary drifted before authorization",
            details=semantic_drift,
        )
    transport_required: dict[str, object] = {
        "governed_root_resolved_before_filename": True,
        "global_filename_uniqueness_required": False,
        "unscoped_recursive_authorization_search_permitted": False,
        "authorization_before_runtime_installation": True,
    }
    transport_drift = tuple(
        k for k, expected in transport_required.items() if transport.get(k) != expected
    )
    if transport_drift:
        _raise(
            "P5_P6_V2_AUTHORIZATION_TRANSPORT_REVALIDATION_FAILED",
            "V2 authorization transport audit drifted before authorization",
            details=transport_drift,
        )


def _load_confirmation(path: Path) -> IssuanceConfirmation:
    if not path.is_file() or path.is_symlink():
        _raise(
            "P5_P6_V2_AUTHORIZATION_CONFIRMATION_MISSING",
            "issuance confirmation JSON is missing or unsafe",
            path,
        )
    payload = path.read_bytes()
    try:
        parsed = json.loads(payload)
        confirmation = IssuanceConfirmation.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        _raise(
            "P5_P6_V2_AUTHORIZATION_CONFIRMATION_INVALID",
            "issuance confirmation JSON is invalid",
            path,
            (str(error),),
        )
    if payload != _transport_json_bytes(confirmation):
        _raise(
            "P5_P6_V2_AUTHORIZATION_CONFIRMATION_NONCANONICAL",
            "issuance confirmation JSON is not canonical compact JSON",
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
            "P5_P6_V2_AUTHORIZATION_CONFIRMATION_PHRASE_INVALID",
            "exact operator confirmation phrase is required",
        )
    if confirmation.confirmed_at > observed_now + timedelta(minutes=1):
        _raise(
            "P5_P6_V2_AUTHORIZATION_CONFIRMATION_IN_FUTURE",
            "operator confirmation timestamp is in the future",
        )
    if confirmation.platform.observed_at > observed_now + timedelta(minutes=1):
        _raise(
            "P5_P6_V2_AUTHORIZATION_PLATFORM_OBSERVATION_IN_FUTURE",
            "platform observation timestamp is in the future",
        )
    if observed_now - confirmation.confirmed_at > timedelta(minutes=15):
        _raise(
            "P5_P6_V2_AUTHORIZATION_CONFIRMATION_STALE",
            "operator confirmation is older than 15 minutes",
        )
    if observed_now - confirmation.platform.observed_at > timedelta(minutes=15):
        _raise(
            "P5_P6_V2_AUTHORIZATION_PLATFORM_OBSERVATION_STALE",
            "platform observation is older than 15 minutes",
        )


def _build_authorization(
    confirmation: IssuanceConfirmation,
    issuer_merge_commit: str,
    issued_at: datetime,
) -> ExecutionAuthorization:
    observed = _normalize_time(issued_at, "issuance time")
    return ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle="ISSUED",
        scope=AUTHORIZATION_SCOPE,
        authorization_filename=AUTHORIZATION_TRANSFER_FILENAME,
        issued_at=observed,
        expires_at=observed + timedelta(minutes=confirmation.authorization_window_minutes),
        authorization_window_minutes=confirmation.authorization_window_minutes,
        issuer_merge_commit=issuer_merge_commit,
        authorization_design_record_sha256=AUTHORIZATION_DESIGN_RECORD_SHA256,
        implementation_merge_commit=P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        implementation_record_sha256=P5_P6_IMPLEMENTATION_RECORD_SHA256,
        implementation_review_sha256=P5_P6_IMPLEMENTATION_REVIEW_SHA256,
        design_record_sha256=TRANSPORT_DESIGN_RECORD_SHA256,
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
        runtime_execution_authorized=True,
        single_use=True,
        every_terminal_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        authorization_reusable=False,
        expected_evidence_zip=EXPECTED_EVIDENCE_ZIP,
        next_gate=NEXT_GATE_AFTER_ISSUE,
    )


def _require_transport_round_trip(payload: bytes, now: datetime) -> dict[str, object]:
    try:
        validate_authorization_bytes(payload, require_live=True, now=now)
        with tempfile.TemporaryDirectory(prefix="ag-p5-p6-v2-auth-parity-") as temporary:
            input_root = Path(temporary) / "kaggle" / "input"
            output_root = input_root / CONTROL_NOTEBOOK_NAME / CONTROL_OUTPUT_DIRECTORY_NAME
            materialize_control_package(output_root, payload)
            verified = validate_control_package(
                input_root,
                require_live_authorization=True,
                now=now,
            )
    except (AuthorizationTransportError, OSError, ValueError) as error:
        _raise(
            "P5_P6_V2_AUTHORIZATION_TRANSPORT_ROUND_TRIP_FAILED",
            "candidate authorization failed current producer/consumer transport parity",
            details=(type(error).__name__, str(error)[:1000]),
        )
    return {
        "transport_contract": "GOVERNED_ROOT_EXACT_FLAT_V1",
        "producer_notebook_name": verified.producer_notebook_name,
        "producer_output_directory": verified.producer_output_directory,
        "authorization_sha256": verified.authorization_sha256,
        "exact_flat_file_count": verified.exact_flat_file_count,
    }


def issue_authorization(
    repo_root: Path,
    *,
    confirmation: IssuanceConfirmation,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repo_root.resolve()
    validate_implementation(root)
    _require_v2_preexecution_contract(root)
    _require_no_lifecycle_artifact(root)
    observed_now = _normalize_time(now or datetime.now(UTC), "issuance time")
    _require_confirmation_fresh(confirmation, observed_now)
    issuer_head = _require_issue_repo_state(
        root,
        confirmation.confirmed_issuer_merge_commit,
    )
    authorization = _build_authorization(confirmation, issuer_head, observed_now)
    payload = _transport_json_bytes(authorization)
    parity = _require_transport_round_trip(payload, observed_now)
    _write_non_overwriting(root / AUTHORIZATION_PATH, payload)
    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_EXECUTION_AUTHORIZATION_ISSUED",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "transfer_filename": AUTHORIZATION_TRANSFER_FILENAME,
        "authorization_sha256": _sha256_bytes(payload),
        "issuer_merge_commit": issuer_head,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "transport_round_trip": parity,
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
            "P5_P6_V2_AUTHORIZATION_MISSING",
            "live V2 authorization file is missing or unsafe",
            AUTHORIZATION_PATH,
        )
    payload = target.read_bytes()
    try:
        parsed = json.loads(payload)
        authorization = ExecutionAuthorization.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        _raise(
            "P5_P6_V2_AUTHORIZATION_INVALID",
            "live V2 authorization is invalid",
            AUTHORIZATION_PATH,
            (str(error),),
        )
    if payload != _transport_json_bytes(authorization):
        _raise(
            "P5_P6_V2_AUTHORIZATION_NONCANONICAL",
            "live V2 authorization bytes are not canonical compact JSON",
            AUTHORIZATION_PATH,
        )
    return authorization, payload


def validate_live_authorization(
    repo_root: Path,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repo_root.resolve()
    authorization, payload = _read_authorization(root)
    if (root / TERMINAL_RECEIPT_PATH).exists():
        _raise(
            "P5_P6_V2_AUTHORIZATION_ALREADY_TERMINAL",
            "authorization already has a terminal receipt",
            TERMINAL_RECEIPT_PATH,
        )
    observed = _normalize_time(now or datetime.now(UTC), "validation time")
    if observed < authorization.issued_at or observed >= authorization.expires_at:
        _raise(
            "P5_P6_V2_AUTHORIZATION_OUTSIDE_VALID_WINDOW",
            "live authorization is outside its valid time window",
        )
    validate_authorization_bytes(payload, require_live=True, now=observed)
    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_EXECUTION_AUTHORIZATION_LIVE_VALID",
        "authorization_sha256": _sha256_bytes(payload),
        "issuer_merge_commit": authorization.issuer_merge_commit,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "runtime_execution_authorized": True,
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
    root = repo_root.resolve()
    authorization, payload = _read_authorization(root)
    if (root / TERMINAL_RECEIPT_PATH).exists():
        _raise(
            "P5_P6_V2_AUTHORIZATION_ALREADY_TERMINAL",
            "authorization already has a terminal receipt",
            TERMINAL_RECEIPT_PATH,
        )
    observed = _normalize_time(now or datetime.now(UTC), "terminal time")
    unused = {
        TerminalDisposition.EXPIRED_UNUSED,
        TerminalDisposition.CANCELLED_UNUSED,
        TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
    }
    if disposition == TerminalDisposition.EXPIRED_UNUSED and observed < authorization.expires_at:
        _raise(
            "P5_P6_V2_AUTHORIZATION_NOT_YET_EXPIRED",
            "EXPIRED_UNUSED requires elapsed authorization window",
        )
    if (
        disposition
        in {
            TerminalDisposition.CANCELLED_UNUSED,
            TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
        }
        and observed >= authorization.expires_at
    ):
        _raise(
            "P5_P6_V2_AUTHORIZATION_UNUSED_DISPOSITION_AFTER_EXPIRY",
            "use EXPIRED_UNUSED after authorization expiry",
        )
    attempted = disposition not in unused
    receipt = AuthorizationTerminalReceipt(
        receipt_id=("auragateway-exact-runtime-p5-p6-requalification-v2-authorization-terminal-v1"),
        authorization_id=authorization.authorization_id,
        authorization_sha256=_sha256_bytes(payload),
        issuer_merge_commit=authorization.issuer_merge_commit,
        disposition=disposition,
        execution_attempted=attempted,
        execution_outcome=execution_outcome,
        terminalized_at=observed,
        saved_version_id=saved_version_id,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
    )
    receipt_bytes = _artifact_json_bytes(receipt)
    _write_non_overwriting(root / TERMINAL_RECEIPT_PATH, receipt_bytes)
    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_EXECUTION_AUTHORIZATION_TERMINAL",
        "authorization_sha256": _sha256_bytes(payload),
        "terminal_receipt_sha256": _sha256_bytes(receipt_bytes),
        "disposition": disposition.value,
        "execution_attempted": attempted,
        "execution_outcome": (None if execution_outcome is None else execution_outcome.value),
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }


def validate_confirmation_file(path: Path) -> dict[str, object]:
    confirmation = _load_confirmation(path)
    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_EXECUTION_AUTHORIZATION_CONFIRMATION_VALID",
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
    print(_artifact_json_bytes(envelope).decode("utf-8"), file=sys.stderr, end="")


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
        if args.command == "generate":
            result: object = generate(root)
        elif args.command == "validate-implementation":
            result = validate_implementation(root)
        elif args.command == "validate-confirmation":
            if args.confirmation_json is None:
                _raise(
                    "P5_P6_V2_AUTHORIZATION_ARGUMENT_MISSING",
                    "--confirmation-json is required",
                )
            result = validate_confirmation_file(Path(args.confirmation_json))
        elif args.command == "issue":
            if args.confirmation_json is None:
                _raise(
                    "P5_P6_V2_AUTHORIZATION_ARGUMENT_MISSING",
                    "--confirmation-json is required",
                )
            result = issue_authorization(
                root,
                confirmation=_load_confirmation(Path(args.confirmation_json)),
            )
        elif args.command == "validate-live":
            result = validate_live_authorization(root)
        else:
            if args.disposition is None:
                _raise(
                    "P5_P6_V2_AUTHORIZATION_ARGUMENT_MISSING",
                    "--disposition is required",
                )
            outcome = None if args.outcome is None else ExecutionOutcome(args.outcome)
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
                "P5_P6_V2_AUTHORIZATION_VALIDATION_ERROR",
                "authorization contract validation failed",
                details=(str(error),),
            )
        )
        return 2
    print(_artifact_json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
