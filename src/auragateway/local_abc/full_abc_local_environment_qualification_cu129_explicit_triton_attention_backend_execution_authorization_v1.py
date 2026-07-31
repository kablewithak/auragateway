"""Generate, issue, verify, and consume one Q6 attention-backend authorization."""

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
    full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_v1,
)
from auragateway.local_abc.contracts import LocalABCContract

implementation = full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_v1

SOURCE_MAIN_MERGE_COMMIT: Final = "6ede70538c52165d92a1df68e2c8bbc97a123c49"
IMPLEMENTATION_FEATURE_COMMIT: Final = "dc9484492169965e0ed17d77bf1894d1ae9e7cb8"
IMPLEMENTATION_RECORD_SHA256: Final = (
    "b602356f7a03a794d74167d477c525cddbb353abd5ca13609a071792263393cb"
)
IMPLEMENTATION_NOTEBOOK_SHA256: Final = (
    "cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208"
)
IMPLEMENTATION_REQUEST_SHA256: Final = (
    "ead0138391f221bc01eaba8b43a07e876217a72bb11a9f9d79ddaf6f868f5910"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "76e1f3ac8346b540633f62dedff94bc2f8d1b208341c8a7fd8f4bed4e668e404"
)
IMPLEMENTATION_TEMPLATE_SHA256: Final = (
    "97f07d647348ccbd1633359ff24b9ceb03cc2c697cbce3586d49c6c562f3577e"
)

IMPLEMENTATION_RECORD_PATH: Final = implementation.RECORD_PATH
IMPLEMENTATION_NOTEBOOK_PATH: Final = implementation.NOTEBOOK_PATH
IMPLEMENTATION_REQUEST_PATH: Final = implementation.REQUEST_PATH
IMPLEMENTATION_REVIEW_PATH: Final = implementation.REVIEW_PATH
IMPLEMENTATION_TEMPLATE_PATH: Final = implementation.TEMPLATE_PATH

ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_"
    "explicit_triton_attention_backend_execution_authorization_v1.py"
)
ISSUER_TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_full_abc_local_environment_qualification_cu129_"
    "explicit_triton_attention_backend_execution_authorization_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-07-31-local-abc-explicit-triton-attention-backend-execution-authorization-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Explicit_Triton_Attention_Backend_Execution_Authorization_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_explicit_triton_attention_backend_execution_authorization_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_triton_attention_backend_"
    "execution_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_triton_attention_backend_"
    "execution_authorization_v1_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_triton_attention_backend_"
    "execution_authorization_v1.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_triton_attention_backend_"
    "execution_authorization_consumption_v1.json"
)

AUTHORIZATION_ID: Final = (
    "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-v1"
)
AUTHORIZATION_SCOPE: Final = "MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_V1"
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
IMPLEMENTATION_NEXT_GATE: Final = (
    "explicit_operator_confirmation_then_issue_explicit_triton_attention_backend_"
    "execution_authorization_v1"
)
ISSUED_NEXT_GATE: Final = "execute_governed_explicit_triton_attention_backend_v1"
CONSUMED_NEXT_GATE: Final = "preserve_and_accept_explicit_triton_attention_backend_evidence_v1"


class AuthorizationLifecycle(StrEnum):
    """Lifecycle states for one transient single-use authority."""

    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"


class ExecutionOutcome(StrEnum):
    """Terminal outcome recorded after the single governed attempt."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class AttentionBackendAuthorizationError(RuntimeError):
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
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_ARGUMENT_INVALID",
            "attention-backend authorization arguments are invalid",
            details=(message,),
        )


class ArtifactReceipt(LocalABCContract):
    """Deterministic repository artifact identity."""

    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ImplementationAuthority(LocalABCContract):
    """Exact merged Q6 implementation and generated-artifact binding."""

    source_main_merge_commit: Literal["6ede70538c52165d92a1df68e2c8bbc97a123c49"]
    implementation_feature_commit: Literal["dc9484492169965e0ed17d77bf1894d1ae9e7cb8"]
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    implementation_record: ArtifactReceipt
    notebook: ArtifactReceipt
    request: ArtifactReceipt
    architecture_review: ArtifactReceipt
    template: ArtifactReceipt
    runtime_execution_authorized_before_issuance: Literal[False]
    unchanged_upstream_replay_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_exact_bindings(self) -> Self:
        expected = {
            self.implementation_record.repository_path: IMPLEMENTATION_RECORD_SHA256,
            self.notebook.repository_path: IMPLEMENTATION_NOTEBOOK_SHA256,
            self.request.repository_path: IMPLEMENTATION_REQUEST_SHA256,
            self.architecture_review.repository_path: IMPLEMENTATION_REVIEW_SHA256,
            self.template.repository_path: IMPLEMENTATION_TEMPLATE_SHA256,
        }
        observed = {
            IMPLEMENTATION_RECORD_PATH.as_posix(): self.implementation_record.sha256,
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(): self.notebook.sha256,
            IMPLEMENTATION_REQUEST_PATH.as_posix(): self.request.sha256,
            IMPLEMENTATION_REVIEW_PATH.as_posix(): self.architecture_review.sha256,
            IMPLEMENTATION_TEMPLATE_PATH.as_posix(): self.template.sha256,
        }
        if observed != expected:
            raise ValueError("merged implementation artifact bindings drifted")
        return self


class AuthorizationBudget(LocalABCContract):
    """Hard action ceiling for one model-free Q6 execution."""

    maximum_authorization_window_minutes: Literal[240] = 240
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_platform_preflight_attempts: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_backend_discovery_attempts: Literal[1] = 1
    maximum_backend_import_attempts: Literal[1] = 1
    maximum_backend_capability_validation_attempts: Literal[1] = 1
    maximum_attention_primitive_attempts: Literal[1] = 1
    maximum_model_loads: Literal[0] = 0
    maximum_worker_starts: Literal[0] = 0
    maximum_model_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class AuthorizationControls(LocalABCContract):
    """Fail-closed privacy, fallback, and environment controls."""

    internet_enabled: Literal[False] = False
    network_access_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    global_environment_mutation_permitted: Literal[False] = False
    cuda_toolkit_stub_permitted: Literal[False] = False
    silent_backend_fallback_permitted: Literal[False] = False
    hidden_retries_permitted: Literal[False] = False
    filesystem_mutation_scope: Literal["KAGGLE_WORKING_DIRECTORY_ONLY"] = (
        "KAGGLE_WORKING_DIRECTORY_ONLY"
    )
    measured_execution_authorized: Literal[False] = False


class AuthorizationArchitectureReview(LocalABCContract):
    """Deterministic decision to implement but not issue runtime authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-v1-review"
    ]
    status: Literal["APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION"]
    decision: Literal["SEPARATE_TRANSIENT_SINGLE_USE_Q6_AUTHORIZATION"]
    implementation: ImplementationAuthority
    budget: AuthorizationBudget
    controls: AuthorizationControls
    operator_confirmation_required: Literal[True]
    authorization_must_remain_untracked: Literal[True]
    successful_or_failed_attempt_consumes_authorization: Literal[True]
    runtime_loader_enforcement_mode: Literal["OPERATOR_GATE_BOUND_TO_EXACT_NOTEBOOK"]
    authorization_issued_in_review: Literal[False]
    runtime_execution_performed: Literal[False]
    next_gate: Literal[
        "explicit_operator_confirmation_then_issue_explicit_triton_attention_backend_"
        "execution_authorization_v1"
    ]
    non_claims: tuple[str, ...] = Field(min_length=8)


class AuthorizationImplementationRecord(LocalABCContract):
    """Deterministic record that the issuer exists but no authority was issued."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-v1-record"
    ]
    status: Literal["EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1_VALID"]
    source_main_merge_commit: Literal["6ede70538c52165d92a1df68e2c8bbc97a123c49"]
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
    next_gate: Literal[
        "explicit_operator_confirmation_then_issue_explicit_triton_attention_backend_"
        "execution_authorization_v1"
    ]

    @model_validator(mode="after")
    def validate_paths(self) -> Self:
        if self.authorization_path != AUTHORIZATION_PATH.as_posix():
            raise ValueError("transient authorization path drifted")
        if self.consumption_path != CONSUMPTION_PATH.as_posix():
            raise ValueError("authorization consumption path drifted")
        return self


class AuthorizationIssuanceConfirmation(LocalABCContract):
    """Explicit operator confirmation for one exact notebook and scope."""

    confirmation_id: Literal[
        "auragateway-cu129-explicit-triton-attention-backend-"
        "execution-authorization-confirmation-v1"
    ]
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(
        ge=1,
        le=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
    )
    confirmed_scope: Literal["MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_V1"]
    confirmed_notebook_sha256: Literal[
        "cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208"
    ]

    @field_validator("confirmed_at")
    @classmethod
    def normalize_confirmed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("operator confirmation time must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


class AttentionBackendExecutionAuthorization(LocalABCContract):
    """One transient, single-use, model-free Q6 execution authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal[
        "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-v1"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal[AuthorizationLifecycle.ISSUED]
    scope: Literal["MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_V1"]
    source_main_merge_commit: Literal["6ede70538c52165d92a1df68e2c8bbc97a123c49"]
    implementation_feature_commit: Literal["dc9484492169965e0ed17d77bf1894d1ae9e7cb8"]
    implementation_record_sha256: Literal[
        "b602356f7a03a794d74167d477c525cddbb353abd5ca13609a071792263393cb"
    ]
    request_sha256: Literal["ead0138391f221bc01eaba8b43a07e876217a72bb11a9f9d79ddaf6f868f5910"]
    notebook_sha256: Literal["cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208"]
    issued_from_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issued_at: datetime
    expires_at: datetime
    operator_confirmation_recorded: Literal[True]
    single_use: Literal[True]
    successful_or_failed_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    budget: AuthorizationBudget
    controls: AuthorizationControls

    @field_validator("issued_at", "expires_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        if self.expires_at - self.issued_at > timedelta(
            minutes=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES
        ):
            raise ValueError("authorization window exceeds reviewed budget")
        return self


class AttentionBackendAuthorizationConsumption(LocalABCContract):
    """Immutable local receipt consuming the authority after one attempt."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    consumption_id: Literal[
        "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-consumption-v1"
    ]
    authorization_id: Literal[
        "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-v1"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.CONSUMED]
    consumed_at: datetime
    outcome: ExecutionOutcome
    saved_version_id: int = Field(ge=1)
    notebook_sha256: Literal["cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208"]
    authorization_reusable: Literal[False]
    next_gate: Literal["preserve_and_accept_explicit_triton_attention_backend_evidence_v1"]

    @field_validator("consumed_at")
    @classmethod
    def normalize_consumed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumption time must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as error:
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_FILE_UNREADABLE",
            "an authorization-bound file could not be read",
            path.as_posix(),
        ) from error


def _artifact(repo_root: Path, path: Path) -> ArtifactReceipt:
    return ArtifactReceipt(
        repository_path=path.as_posix(),
        sha256=_sha256_file(repo_root / path),
    )


def _implementation_authority(repo_root: Path) -> ImplementationAuthority:
    try:
        record = implementation.validate(repo_root)
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        implementation.ExplicitTritonAttentionBackendV1Error,
    ) as error:
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_IMPLEMENTATION_AUTHORITY_INVALID",
            "the merged explicit Triton attention-backend implementation is invalid",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        ) from error

    checks = (
        record.status == "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_VALID",
        record.implementation_status == "IMPLEMENTED_NOT_EXECUTED",
        record.runtime_execution_authorized is False,
        record.unchanged_upstream_replay_authorized is False,
        record.next_gate
        == "design_and_merge_explicit_triton_attention_backend_execution_authorization_v1",
        record.notebook.sha256 == IMPLEMENTATION_NOTEBOOK_SHA256,
        record.request.sha256 == IMPLEMENTATION_REQUEST_SHA256,
        record.review.sha256 == IMPLEMENTATION_REVIEW_SHA256,
        record.template.sha256 == IMPLEMENTATION_TEMPLATE_SHA256,
    )
    if not all(checks):
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_IMPLEMENTATION_BINDING_DRIFT",
            "the merged attention-backend implementation no longer matches its authority",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    exact_files = (
        (IMPLEMENTATION_RECORD_PATH, IMPLEMENTATION_RECORD_SHA256),
        (IMPLEMENTATION_NOTEBOOK_PATH, IMPLEMENTATION_NOTEBOOK_SHA256),
        (IMPLEMENTATION_REQUEST_PATH, IMPLEMENTATION_REQUEST_SHA256),
        (IMPLEMENTATION_REVIEW_PATH, IMPLEMENTATION_REVIEW_SHA256),
        (IMPLEMENTATION_TEMPLATE_PATH, IMPLEMENTATION_TEMPLATE_SHA256),
    )
    for path, expected in exact_files:
        if _sha256_file(repo_root / path) != expected:
            raise AttentionBackendAuthorizationError(
                "ATTENTION_BACKEND_IMPLEMENTATION_FILE_IDENTITY_DRIFT",
                "an implementation-bound file identity drifted",
                path.as_posix(),
            )

    return ImplementationAuthority(
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        implementation_record=_artifact(repo_root, IMPLEMENTATION_RECORD_PATH),
        notebook=_artifact(repo_root, IMPLEMENTATION_NOTEBOOK_PATH),
        request=_artifact(repo_root, IMPLEMENTATION_REQUEST_PATH),
        architecture_review=_artifact(repo_root, IMPLEMENTATION_REVIEW_PATH),
        template=_artifact(repo_root, IMPLEMENTATION_TEMPLATE_PATH),
        runtime_execution_authorized_before_issuance=False,
        unchanged_upstream_replay_authorized=False,
    )


def _build_review(repo_root: Path) -> AuthorizationArchitectureReview:
    return AuthorizationArchitectureReview(
        review_id=(
            "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-v1-review"
        ),
        status="APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION",
        decision="SEPARATE_TRANSIENT_SINGLE_USE_Q6_AUTHORIZATION",
        implementation=_implementation_authority(repo_root),
        budget=AuthorizationBudget(),
        controls=AuthorizationControls(),
        operator_confirmation_required=True,
        authorization_must_remain_untracked=True,
        successful_or_failed_attempt_consumes_authorization=True,
        runtime_loader_enforcement_mode="OPERATOR_GATE_BOUND_TO_EXACT_NOTEBOOK",
        authorization_issued_in_review=False,
        runtime_execution_performed=False,
        next_gate=IMPLEMENTATION_NEXT_GATE,
        non_claims=(
            "This review does not issue runtime authorization.",
            "The attention-backend notebook has not been executed.",
            "No Kaggle session has been started.",
            "No GPU action has been performed.",
            "No target runtime has been installed.",
            "No vLLM or attention backend has been imported.",
            "No model, worker, request, or benchmark trajectory is authorized.",
            "The notebook does not parse the transient authorization artifact.",
            "Execution remains an operator gate bound to the exact notebook hash.",
            "Deployment and production readiness are not claimed.",
        ),
    )


def _build_record(
    repo_root: Path,
    review_bytes: bytes,
) -> AuthorizationImplementationRecord:
    return AuthorizationImplementationRecord(
        record_id=(
            "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-v1-record"
        ),
        status=("EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1_VALID"),
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
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_ATOMIC_WRITE_FAILED",
            "an authorization artifact could not be written atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _write_non_overwriting(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_ALREADY_EXISTS",
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
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_ALREADY_EXISTS",
            "the transient authorization appeared during issuance",
            path.as_posix(),
        ) from error
    except OSError as error:
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_ATOMIC_CREATE_FAILED",
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
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_TRANSIENT_AUTHORITY_PRESENT",
            "transient authorization artifacts must be absent during generation",
        )
    review = _build_review(root)
    review_bytes = review.canonical_json().encode("utf-8")
    _write_atomic(root / REVIEW_PATH, review_bytes)
    record = _build_record(root, review_bytes)
    _write_atomic(root / RECORD_PATH, record.canonical_json().encode("utf-8"))
    return record


def _validate_static_package(
    repo_root: Path,
) -> AuthorizationImplementationRecord:
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
            raise AttentionBackendAuthorizationError(
                "ATTENTION_BACKEND_AUTHORIZATION_STATIC_ARTIFACT_UNSAFE",
                "a static authorization artifact is missing or unsafe",
                path.as_posix(),
            )
        if target.read_bytes() != payload:
            raise AttentionBackendAuthorizationError(
                "ATTENTION_BACKEND_AUTHORIZATION_STATIC_ARTIFACT_DRIFT",
                "a static authorization artifact differs from fresh generation",
                path.as_posix(),
            )
    return record


def validate_implementation_package(repo_root: Path) -> dict[str, object]:
    """Validate the issuer implementation without creating runtime authority."""

    root = repo_root.resolve()
    if (root / AUTHORIZATION_PATH).exists() or (root / CONSUMPTION_PATH).exists():
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_TRANSIENT_AUTHORITY_PRESENT",
            "transient authorization artifacts must be absent during implementation review",
        )
    record = _validate_static_package(root)
    return {
        "status": record.status,
        "source_main_merge_commit": record.source_main_merge_commit,
        "implementation_feature_commit": record.implementation.implementation_feature_commit,
        "notebook_sha256": record.implementation.notebook.sha256,
        "authorization_issuer_implemented": True,
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "maximum_kaggle_sessions": record.budget.maximum_kaggle_sessions,
        "maximum_attention_primitive_attempts": (
            record.budget.maximum_attention_primitive_attempts
        ),
        "maximum_model_loads": 0,
        "maximum_worker_starts": 0,
        "maximum_model_requests": 0,
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
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_GIT_FAILED",
            "a required Git inspection could not be completed",
            details=tuple(arguments),
        ) from error
    if result.returncode != 0:
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_GIT_FAILED",
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
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_ANCESTRY_UNREADABLE",
            "authorization source ancestry could not be inspected",
            details=(commit,),
        ) from error
    if result.returncode != 0:
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_SOURCE_AUTHORITY_MISSING",
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
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_REQUIRES_MAIN",
            "runtime authorization work is permitted only from main",
            details=(branch,),
        )
    head = _run_git(repo_root, ["rev-parse", "HEAD"])
    origin_main = _run_git(repo_root, ["rev-parse", "origin/main"])
    if head != origin_main:
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "local main must equal origin/main before authorization work",
            details=(head, origin_main),
        )
    status = _run_git(repo_root, ["status", "--porcelain", "--untracked-files=all"])
    changes = tuple(sorted(line for line in status.splitlines() if line))
    allowed = set(_allowed_transient_status(allow_transient))
    if changes and (not allow_transient or not set(changes).issubset(allowed)):
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_REQUIRES_CLEAN_TREE",
            "authorization work requires a clean tree except for transient authority files",
            details=changes,
        )
    return head


def _require_transient_paths_untracked(repo_root: Path) -> None:
    for path in (AUTHORIZATION_PATH, CONSUMPTION_PATH):
        tracked = _run_git(repo_root, ["ls-files", "--cached", "--", path.as_posix()])
        if tracked:
            raise AttentionBackendAuthorizationError(
                "ATTENTION_BACKEND_AUTHORIZATION_MUST_REMAIN_UNTRACKED",
                "transient authorization artifacts must never be committed",
                path.as_posix(),
            )


def _require_source_authority(repo_root: Path) -> None:
    _require_ancestor(repo_root, SOURCE_MAIN_MERGE_COMMIT)
    _require_ancestor(repo_root, IMPLEMENTATION_FEATURE_COMMIT)


def _build_authorization(
    *,
    repo_root: Path,
    issuer_head: str,
    confirmation: AuthorizationIssuanceConfirmation,
) -> AttentionBackendExecutionAuthorization:
    _validate_static_package(repo_root)
    issued_at = confirmation.confirmed_at
    expires_at = issued_at + timedelta(minutes=confirmation.authorization_window_minutes)
    return AttentionBackendExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=AuthorizationLifecycle.ISSUED,
        scope=AUTHORIZATION_SCOPE,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        implementation_record_sha256=IMPLEMENTATION_RECORD_SHA256,
        request_sha256=IMPLEMENTATION_REQUEST_SHA256,
        notebook_sha256=IMPLEMENTATION_NOTEBOOK_SHA256,
        issued_from_main_commit=issuer_head,
        issued_at=issued_at,
        expires_at=expires_at,
        operator_confirmation_recorded=True,
        single_use=True,
        successful_or_failed_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        budget=AuthorizationBudget(),
        controls=AuthorizationControls(),
    )


def issue_authorization(
    *,
    repo_root: Path,
    confirmation: AuthorizationIssuanceConfirmation,
) -> dict[str, object]:
    """Issue one non-overwriting, time-bounded, untracked authority."""

    root = repo_root.resolve()
    if (root / CONSUMPTION_PATH).exists():
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_CONSUMPTION_ALREADY_PRESENT",
            "a prior authorization consumption receipt already exists",
            CONSUMPTION_PATH.as_posix(),
        )
    issuer_head = _require_synchronized_main(root, allow_transient=False)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    authorization = _build_authorization(
        repo_root=root,
        issuer_head=issuer_head,
        confirmation=confirmation,
    )
    payload = authorization.canonical_json().encode("utf-8")
    _write_non_overwriting(root / AUTHORIZATION_PATH, payload)
    return {
        "status": "ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_ISSUED",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": _sha256_bytes(payload),
        "issuer_head_commit": issuer_head,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "single_use": True,
        "successful_or_failed_attempt_consumes_authorization": True,
        "maximum_kaggle_sessions": 1,
        "maximum_attention_primitive_attempts": 1,
        "maximum_model_loads": 0,
        "maximum_worker_starts": 0,
        "maximum_model_requests": 0,
        "maximum_benchmark_trajectory_requests": 0,
        "next_gate": ISSUED_NEXT_GATE,
    }


def _load_canonical(path: Path, model: type[LocalABCContract]) -> LocalABCContract:
    try:
        observed = path.read_text(encoding="utf-8")
        contract = model.model_validate_json(observed)
    except (OSError, ValidationError) as error:
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_PAYLOAD_INVALID",
            "an authorization payload failed strict validation",
            path.as_posix(),
        ) from error
    if observed != contract.canonical_json():
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_PAYLOAD_NOT_CANONICAL",
            "an authorization payload is not canonical JSON",
            path.as_posix(),
        )
    return contract


def _validate_authorization_bindings(
    authorization: AttentionBackendExecutionAuthorization,
) -> None:
    checks = (
        authorization.authorization_id == AUTHORIZATION_ID,
        authorization.scope == AUTHORIZATION_SCOPE,
        authorization.source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT,
        authorization.implementation_feature_commit == IMPLEMENTATION_FEATURE_COMMIT,
        authorization.implementation_record_sha256 == IMPLEMENTATION_RECORD_SHA256,
        authorization.request_sha256 == IMPLEMENTATION_REQUEST_SHA256,
        authorization.notebook_sha256 == IMPLEMENTATION_NOTEBOOK_SHA256,
        authorization.operator_confirmation_recorded is True,
        authorization.single_use is True,
        authorization.successful_or_failed_attempt_consumes_authorization is True,
        authorization.unchanged_replay_authorized is False,
        authorization.budget == AuthorizationBudget(),
        authorization.controls == AuthorizationControls(),
    )
    if not all(checks):
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_BINDING_DRIFT",
            "the transient authorization no longer binds the reviewed Q6 inputs",
            AUTHORIZATION_PATH.as_posix(),
        )


def verify_authorization(
    *,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify one live authority immediately before the governed execution."""

    root = repo_root.resolve()
    issuer_head = _require_synchronized_main(root, allow_transient=True)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    _validate_static_package(root)
    if (root / CONSUMPTION_PATH).exists():
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_ALREADY_CONSUMED",
            "the authorization has a consumption receipt and is not reusable",
            CONSUMPTION_PATH.as_posix(),
        )
    loaded = _load_canonical(root / AUTHORIZATION_PATH, AttentionBackendExecutionAuthorization)
    authorization = cast(AttentionBackendExecutionAuthorization, loaded)
    _validate_authorization_bindings(authorization)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if not authorization.issued_at <= observed_now < authorization.expires_at:
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_EXPIRED",
            "the transient authorization is outside its validity window",
            AUTHORIZATION_PATH.as_posix(),
        )
    return {
        "status": "ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_VALID",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": authorization.fingerprint(),
        "issuer_head_commit": issuer_head,
        "issued_from_main_commit": authorization.issued_from_main_commit,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "notebook_sha256": authorization.notebook_sha256,
        "single_use": True,
        "consumed": False,
        "maximum_kaggle_sessions": 1,
        "maximum_attention_primitive_attempts": 1,
        "maximum_model_loads": 0,
        "maximum_worker_starts": 0,
        "maximum_model_requests": 0,
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
        raise AttentionBackendAuthorizationError(
            "ATTENTION_BACKEND_AUTHORIZATION_ALREADY_CONSUMED",
            "the authorization consumption receipt already exists",
            CONSUMPTION_PATH.as_posix(),
        )
    loaded = _load_canonical(root / AUTHORIZATION_PATH, AttentionBackendExecutionAuthorization)
    authorization = cast(AttentionBackendExecutionAuthorization, loaded)
    _validate_authorization_bindings(authorization)
    authorization_payload = authorization.canonical_json().encode("utf-8")
    receipt = AttentionBackendAuthorizationConsumption(
        consumption_id=(
            "auragateway-cu129-explicit-triton-attention-backend-"
            "execution-authorization-consumption-v1"
        ),
        authorization_id=AUTHORIZATION_ID,
        authorization_sha256=_sha256_bytes(authorization_payload),
        lifecycle=AuthorizationLifecycle.CONSUMED,
        consumed_at=(consumed_at or datetime.now(UTC)).astimezone(UTC),
        outcome=outcome,
        saved_version_id=saved_version_id,
        notebook_sha256=IMPLEMENTATION_NOTEBOOK_SHA256,
        authorization_reusable=False,
        next_gate=CONSUMED_NEXT_GATE,
    )
    payload = receipt.canonical_json().encode("utf-8")
    _write_non_overwriting(root / CONSUMPTION_PATH, payload)
    return {
        "status": "ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_CONSUMED",
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
    parser = _ArgumentParser(prog="auragateway-triton-attention-authorization-v1")
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


def _error_json(error: AttentionBackendAuthorizationError) -> str:
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
                raise AttentionBackendAuthorizationError(
                    "ATTENTION_BACKEND_OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required for issuance",
                )
            confirmation = AuthorizationIssuanceConfirmation(
                confirmation_id=(
                    "auragateway-cu129-explicit-triton-attention-backend-"
                    "execution-authorization-confirmation-v1"
                ),
                operator_confirmed=True,
                confirmed_at=datetime.now(UTC),
                authorization_window_minutes=cast(int, arguments.window_minutes),
                confirmed_scope=cast(str, arguments.confirm_scope),
                confirmed_notebook_sha256=cast(
                    str,
                    arguments.confirm_notebook_sha256,
                ),
            )
            summary = issue_authorization(
                repo_root=repo_root,
                confirmation=confirmation,
            )
        elif arguments.command == "consume":
            if arguments.operator_confirm is not True:
                raise AttentionBackendAuthorizationError(
                    "ATTENTION_BACKEND_OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required for consumption",
                )
            summary = consume_authorization(
                repo_root=repo_root,
                outcome=ExecutionOutcome(cast(str, arguments.outcome)),
                saved_version_id=cast(int, arguments.saved_version_id),
            )
        else:
            summary = verify_authorization(repo_root=repo_root)
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
        return 0
    except AttentionBackendAuthorizationError as error:
        print(_error_json(error), file=sys.stderr)
        return 2
    except (OSError, ValueError, ValidationError) as error:
        envelope = AuthorizationErrorEnvelope(
            error_code="ATTENTION_BACKEND_AUTHORIZATION_UNEXPECTED",
            safe_message=str(error),
        )
        print(envelope.canonical_json(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
