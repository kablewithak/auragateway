"""Govern P4 execution on a Kaggle T4-x2 allocation with one GPU-0 worker."""

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
    p4_output_contract_diagnostic_execution_authorization_v1 as legacy,
)
from auragateway.local_abc.contracts import LocalABCContract

PREVIOUS_ISSUER_FEATURE_COMMIT: Final = "a1fb841d480237159399b80d156c8485b210401b"
PREVIOUS_ISSUER_MERGE_COMMIT: Final = "2131160bf88e47a481555fcf2550cba438689b0c"
LEGACY_AUTHORIZATION_SHA256: Final = (
    "d43756e5c9bf794ac87f6c56449f63660b76ffde5c655462f394e9e48740e5ad"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_output_contract_diagnostic_execution_authorization_v2.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_output_contract_diagnostic_execution_authorization_v2.py"
)
ADR_PATH: Final = Path("docs/adr/2026-08-06-local-abc-p4-t4-x2-execution-authorization-v2.md")
REPORT_PATH: Final = Path("docs/reports/AuraGateway_P4_T4_X2_Execution_Authorization_V2.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_p4_t4_x2_execution_authorization_v2.md")
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_authorization_v2_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_authorization_v2_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_execution_authorization_v2.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_authorization_consumption_v2.json"
)
LEGACY_ABANDONMENT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_authorization_abandonment_v1.json"
)

AUTHORIZATION_ID: Final = "auragateway-p4-output-contract-diagnostic-execution-authorization-v2"
AUTHORIZATION_SCOPE: Final = "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1"
SELECTED_BACKEND: Final = "TRITON_ATTN"
PLATFORM_ACCELERATOR: Final = "GPU_T4_X2"
WORKER_CUDA_VISIBLE_DEVICES: Final = "0"
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
IMPLEMENTATION_NEXT_GATE: Final = (
    "observe_kaggle_t4_x2_then_explicit_operator_confirmation_and_issue_p4_authorization_v2"
)
ISSUED_NEXT_GATE: Final = (
    "execute_governed_p4_output_contract_diagnostic_v1_on_t4_x2_with_gpu0_only"
)
CONSUMED_NEXT_GATE: Final = "preserve_and_classify_p4_output_contract_diagnostic_v1"


class AuthorizationLifecycle(StrEnum):
    """Lifecycle states for one V2 authorization."""

    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"


class ExecutionOutcome(StrEnum):
    """Terminal outcomes after one governed execution attempt."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class AuthorizationError(RuntimeError):
    """Metadata-safe V2 authorization boundary failure."""

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


class ErrorEnvelope(LocalABCContract):
    """Machine-readable error without sensitive payloads."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ARGUMENT_INVALID",
            "P4 authorization V2 arguments are invalid",
            details=(message,),
        )


class ArtifactReceipt(LocalABCContract):
    """Repository artifact identity."""

    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlatformAllocationControls(LocalABCContract):
    """Separate platform allocation from active worker topology."""

    platform_accelerator: Literal["GPU_T4_X2"] = "GPU_T4_X2"
    allocated_gpu_count: Literal[2] = 2
    worker_cuda_visible_devices: Literal["0"] = "0"
    worker_visible_gpu_count: Literal[1] = 1
    worker_gpu_index: Literal[0] = 0
    unused_allocated_gpu_indices: tuple[Literal[1], ...] = (1,)
    one_model_load_required: Literal[True] = True
    one_worker_start_required: Literal[True] = True
    gpu1_model_worker_permitted: Literal[False] = False
    internet_enabled: Literal[False] = False
    platform_capability_confirmation_required: Literal[True] = True
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"] = "KAGGLE_NOTEBOOK_SETTINGS_UI"


class RuntimeGpuIsolationAuthority(LocalABCContract):
    """Executable markers proving the worker is isolated to GPU 0."""

    cuda_visible_devices_explicit: Literal[True] = True
    cuda_visible_devices_value: Literal["0"] = "0"
    worker_startup_report_gpu_index_zero: Literal[True] = True
    one_model_load_counter: Literal[True] = True
    one_worker_start_counter: Literal[True] = True


class ImplementationAuthority(LocalABCContract):
    """Existing P4 implementation plus V2 allocation authority."""

    original_implementation_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    evidence_contract_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    evidence_contract_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    terminal_closure_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    terminal_closure_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    previous_issuer_feature_commit: Literal["a1fb841d480237159399b80d156c8485b210401b"]
    previous_issuer_merge_commit: Literal["2131160bf88e47a481555fcf2550cba438689b0c"]
    implementation_record: ArtifactReceipt
    notebook: ArtifactReceipt
    request: ArtifactReceipt
    architecture_review: ArtifactReceipt
    implementation_source: ArtifactReceipt
    template: ArtifactReceipt
    implementation_tests: ArtifactReceipt
    implementation_adr: ArtifactReceipt
    implementation_report: ArtifactReceipt
    implementation_runbook: ArtifactReceipt
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wheelhouse: legacy.WheelhouseAuthority
    expected_runtime_outputs: tuple[str, ...]
    terminal_evidence: legacy.TerminalEvidenceAuthority
    execution_budget: legacy.ExecutionBudget
    runtime_gpu_isolation: RuntimeGpuIsolationAuthority


class ArchitectureReview(LocalABCContract):
    """Decision record for the T4-x2 allocation correction."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    review_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v2-review"
    ]
    status: Literal["APPROVED_FOR_AUTHORIZATION_V2_IMPLEMENTATION"]
    decision: Literal["T4_X2_ALLOCATION_WITH_SINGLE_GPU0_WORKER_AND_LEGACY_ABANDONMENT"]
    implementation: ImplementationAuthority
    platform: PlatformAllocationControls
    operator_confirmation_required: Literal[True]
    legacy_authorization_abandonment_required: Literal[True]
    platform_capability_observation_required_before_issuance: Literal[True]
    authorization_issued_in_review: Literal[False]
    runtime_execution_performed: Literal[False]
    next_gate: Literal[
        "observe_kaggle_t4_x2_then_explicit_operator_confirmation_and_issue_p4_authorization_v2"
    ]
    non_claims: tuple[str, ...] = Field(min_length=10)


class ImplementationRecord(LocalABCContract):
    """Deterministic record for the V2 issuer implementation."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v2-record"
    ]
    status: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V2_VALID"]
    implementation: ImplementationAuthority
    review: ArtifactReceipt
    source: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    legacy_abandonment_path: str
    authorization_path: str
    consumption_path: str
    authorization_issuer_implemented: Literal[True]
    authorization_issued: Literal[False]
    runtime_execution_performed: Literal[False]
    platform: PlatformAllocationControls
    next_gate: Literal[
        "observe_kaggle_t4_x2_then_explicit_operator_confirmation_and_issue_p4_authorization_v2"
    ]


class LegacyAuthorizationAbandonment(LocalABCContract):
    """Non-overwriting terminal receipt for the unused V1 authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    abandonment_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-abandonment-v1"
    ]
    status: Literal["ABANDONED_BEFORE_EXECUTION"]
    legacy_authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v1"
    ]
    legacy_authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    legacy_issued_from_main_commit: Literal["2131160bf88e47a481555fcf2550cba438689b0c"]
    legacy_required_accelerator: Literal["T4_X1"]
    observed_platform_accelerator: Literal["GPU_T4_X2"]
    reason: Literal["KAGGLE_PLATFORM_ACCELERATOR_UNAVAILABLE"]
    abandoned_at: datetime
    no_saved_version_created: Literal[True]
    runtime_execution_performed: Literal[False]
    runtime_install_attempts: Literal[0]
    model_loads: Literal[0]
    worker_starts: Literal[0]
    model_requests: Literal[0]
    authorization_reusable: Literal[False]
    operator_attested: Literal[True]
    next_gate: Literal["issue_p4_output_contract_diagnostic_execution_authorization_v2"]

    @field_validator("abandoned_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("abandoned_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


class PlatformCapabilityConfirmation(LocalABCContract):
    """Operator-observed Kaggle capability immediately before issuance."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    observed_at: datetime
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"]
    observed_platform_accelerator: Literal["GPU_T4_X2"]
    observed_allocated_gpu_count: Literal[2]
    observed_internet_enabled: Literal[False]
    observed_wheelhouse_attachment_count: Literal[1]
    observed_model_snapshot_attachment_count: Literal[1]
    confirmed_worker_cuda_visible_devices: Literal["0"]
    confirmed_worker_visible_gpu_count: Literal[1]
    confirmed_worker_gpu_index: Literal[0]

    @field_validator("observed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


class IssuanceConfirmation(LocalABCContract):
    """Explicit operator confirmation binding platform and implementation."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=240)
    confirmed_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmed_scope: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1"]
    confirmed_backend: Literal["TRITON_ATTN"]
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
    confirmed_model_request_budget: Literal[18]
    confirmed_runtime_output_count: Literal[16]
    platform: PlatformCapabilityConfirmation

    @field_validator("confirmed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("confirmed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def require_fresh_platform_observation(self) -> Self:
        if self.platform.observed_at > self.confirmed_at:
            raise ValueError("platform observation cannot follow confirmation")
        maximum_age = timedelta(minutes=15)
        if self.confirmed_at - self.platform.observed_at > maximum_age:
            raise ValueError("platform observation is older than 15 minutes")
        return self


class ExecutionAuthorization(LocalABCContract):
    """Transient single-use V2 runtime authority."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v2"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal[AuthorizationLifecycle.ISSUED]
    scope: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1"]
    issued_from_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issued_at: datetime
    expires_at: datetime
    implementation: ImplementationAuthority
    platform: PlatformAllocationControls
    capability_observation: PlatformCapabilityConfirmation
    operator_confirmation_recorded: Literal[True]
    single_use: Literal[True]
    passed_failed_or_interrupted_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]

    @field_validator("issued_at", "expires_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def validate_window_and_platform(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        maximum = timedelta(minutes=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES)
        if self.expires_at - self.issued_at > maximum:
            raise ValueError("authorization window exceeds reviewed budget")
        if self.platform != PlatformAllocationControls():
            raise ValueError("platform allocation controls drifted")
        return self


class AuthorizationConsumption(LocalABCContract):
    """Non-overwriting receipt after one V2 execution attempt."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    consumption_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-consumption-v2"
    ]
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v2"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.CONSUMED]
    consumed_at: datetime
    outcome: ExecutionOutcome
    saved_version_id: int = Field(gt=0)
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


def _artifact(repo_root: Path, relative_path: Path) -> ArtifactReceipt:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ARTIFACT_UNSAFE",
            "a required authorization V2 artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    return ArtifactReceipt(
        repository_path=relative_path.as_posix(),
        sha256=_sha256_bytes(_canonical_lf(path.read_bytes())),
    )


def _copy_receipt(receipt: legacy.ArtifactReceipt) -> ArtifactReceipt:
    return ArtifactReceipt(
        repository_path=receipt.repository_path,
        sha256=receipt.sha256,
    )


def _runtime_gpu_isolation(repo_root: Path) -> RuntimeGpuIsolationAuthority:
    template = (repo_root / legacy.IMPLEMENTATION_TEMPLATE_PATH).read_text(encoding="utf-8")
    markers = (
        'environment["CUDA_VISIBLE_DEVICES"] = "0"',
        '"gpu_index": 0,',
        'COUNTERS["model_loads"] += 1',
        'COUNTERS["worker_starts"] += 1',
    )
    missing = tuple(marker for marker in markers if marker not in template)
    if missing:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_GPU_ISOLATION_DRIFT",
            "the merged runtime GPU-isolation contract drifted",
            legacy.IMPLEMENTATION_TEMPLATE_PATH.as_posix(),
            missing,
        )
    return RuntimeGpuIsolationAuthority()


def _implementation(repo_root: Path) -> ImplementationAuthority:
    authority = legacy._implementation_authority(repo_root)
    return ImplementationAuthority(
        original_implementation_merge_commit=(authority.original_implementation_merge_commit),
        evidence_contract_feature_commit=(authority.evidence_contract_feature_commit),
        evidence_contract_merge_commit=(authority.evidence_contract_merge_commit),
        terminal_closure_feature_commit=(authority.terminal_closure_feature_commit),
        terminal_closure_merge_commit=(authority.terminal_closure_merge_commit),
        previous_issuer_feature_commit=PREVIOUS_ISSUER_FEATURE_COMMIT,
        previous_issuer_merge_commit=PREVIOUS_ISSUER_MERGE_COMMIT,
        implementation_record=_copy_receipt(authority.implementation_record),
        notebook=_copy_receipt(authority.notebook),
        request=_copy_receipt(authority.request),
        architecture_review=_copy_receipt(authority.architecture_review),
        implementation_source=_copy_receipt(authority.implementation_source),
        template=_copy_receipt(authority.template),
        implementation_tests=_copy_receipt(authority.implementation_tests),
        implementation_adr=_copy_receipt(authority.adr),
        implementation_report=_copy_receipt(authority.report),
        implementation_runbook=_copy_receipt(authority.runbook),
        runtime_script_sha256=authority.runtime_script_sha256,
        wrapper_code_sha256=authority.wrapper_code_sha256,
        model_snapshot_sha256=authority.model_snapshot_sha256,
        wheelhouse=authority.wheelhouse,
        expected_runtime_outputs=authority.expected_runtime_outputs,
        terminal_evidence=authority.terminal_evidence,
        execution_budget=authority.execution_budget,
        runtime_gpu_isolation=_runtime_gpu_isolation(repo_root),
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "The V1 authorization was not executed.",
        "No Kaggle saved version was created under V1.",
        "No runtime installation was attempted under V1.",
        "No model was loaded under V1.",
        "No worker was started under V1.",
        "No model request was made under V1.",
        "T4 x2 allocation does not authorize two-GPU execution.",
        "Only GPU 0 is exposed to the governed worker.",
        "GPU 1 is not authorized for a model worker.",
        "P4 structured-output reliability is not established.",
        "No A-F case is selected.",
        "Measured A/B/C is not authorized.",
        "Deployment readiness is not established.",
        "Production readiness is not established.",
    )


def _build_review(repo_root: Path) -> ArchitectureReview:
    return ArchitectureReview(
        review_id=("auragateway-p4-output-contract-diagnostic-execution-authorization-v2-review"),
        status="APPROVED_FOR_AUTHORIZATION_V2_IMPLEMENTATION",
        decision=("T4_X2_ALLOCATION_WITH_SINGLE_GPU0_WORKER_AND_LEGACY_ABANDONMENT"),
        implementation=_implementation(repo_root),
        platform=PlatformAllocationControls(),
        operator_confirmation_required=True,
        legacy_authorization_abandonment_required=True,
        platform_capability_observation_required_before_issuance=True,
        authorization_issued_in_review=False,
        runtime_execution_performed=False,
        next_gate=IMPLEMENTATION_NEXT_GATE,
        non_claims=_non_claims(),
    )


def _build_record(
    repo_root: Path,
    review_bytes: bytes,
) -> ImplementationRecord:
    return ImplementationRecord(
        record_id=("auragateway-p4-output-contract-diagnostic-execution-authorization-v2-record"),
        status=("P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V2_VALID"),
        implementation=_implementation(repo_root),
        review=ArtifactReceipt(
            repository_path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
        ),
        source=_artifact(repo_root, SOURCE_PATH),
        tests=_artifact(repo_root, TEST_PATH),
        adr=_artifact(repo_root, ADR_PATH),
        report=_artifact(repo_root, REPORT_PATH),
        runbook=_artifact(repo_root, RUNBOOK_PATH),
        legacy_abandonment_path=LEGACY_ABANDONMENT_PATH.as_posix(),
        authorization_path=AUTHORIZATION_PATH.as_posix(),
        consumption_path=CONSUMPTION_PATH.as_posix(),
        authorization_issuer_implemented=True,
        authorization_issued=False,
        runtime_execution_performed=False,
        platform=PlatformAllocationControls(),
        next_gate=IMPLEMENTATION_NEXT_GATE,
    )


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
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
            temporary = Path(handle.name)
        os.replace(temporary, path)
    except OSError as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ATOMIC_WRITE_FAILED",
            "an authorization V2 artifact could not be written atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_non_overwriting(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ALREADY_EXISTS",
            "a transient authorization V2 artifact already exists",
            path.as_posix(),
        )
    temporary: Path | None = None
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
            temporary = Path(handle.name)
        os.link(temporary, path)
    except FileExistsError as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ALREADY_EXISTS",
            "a transient authorization V2 artifact appeared during creation",
            path.as_posix(),
        ) from error
    except OSError as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ATOMIC_CREATE_FAILED",
            "a transient authorization V2 artifact could not be created",
            path.as_posix(),
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _static_transient_paths() -> tuple[Path, ...]:
    return (
        LEGACY_ABANDONMENT_PATH,
        AUTHORIZATION_PATH,
        CONSUMPTION_PATH,
        legacy.AUTHORIZATION_PATH,
        legacy.CONSUMPTION_PATH,
    )


def generate(repo_root: Path) -> ImplementationRecord:
    """Generate deterministic V2 review and implementation record."""

    root = repo_root.resolve()
    existing = tuple(
        path.as_posix() for path in _static_transient_paths() if (root / path).exists()
    )
    if existing:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_TRANSIENT_PRESENT",
            "transient lifecycle artifacts must be absent during generation",
            details=existing,
        )
    review = _build_review(root)
    review_bytes = review.canonical_json().encode("utf-8")
    _atomic_write(root / REVIEW_PATH, review_bytes)
    record = _build_record(root, review_bytes)
    _atomic_write(
        root / RECORD_PATH,
        record.canonical_json().encode("utf-8"),
    )
    return record


def _validate_static(repo_root: Path) -> ImplementationRecord:
    review = _build_review(repo_root)
    review_bytes = review.canonical_json().encode("utf-8")
    record = _build_record(repo_root, review_bytes)
    expected = (
        (REVIEW_PATH, review_bytes),
        (
            RECORD_PATH,
            record.canonical_json().encode("utf-8"),
        ),
    )
    for relative_path, payload in expected:
        path = repo_root / relative_path
        if not path.is_file() or path.is_symlink():
            raise AuthorizationError(
                "P4_AUTHORIZATION_V2_STATIC_ARTIFACT_UNSAFE",
                "a static authorization V2 artifact is missing or unsafe",
                relative_path.as_posix(),
            )
        if path.read_bytes() != payload:
            raise AuthorizationError(
                "P4_AUTHORIZATION_V2_STATIC_ARTIFACT_DRIFT",
                "a static authorization V2 artifact differs from generation",
                relative_path.as_posix(),
            )
    return record


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate the static V2 issuer without creating live authority."""

    record = _validate_static(repo_root.resolve())
    return {
        "status": record.status,
        "previous_issuer_feature_commit": PREVIOUS_ISSUER_FEATURE_COMMIT,
        "previous_issuer_merge_commit": PREVIOUS_ISSUER_MERGE_COMMIT,
        "platform_accelerator": record.platform.platform_accelerator,
        "allocated_gpu_count": record.platform.allocated_gpu_count,
        "worker_cuda_visible_devices": (record.platform.worker_cuda_visible_devices),
        "worker_visible_gpu_count": (record.platform.worker_visible_gpu_count),
        "worker_gpu_index": record.platform.worker_gpu_index,
        "gpu1_model_worker_permitted": (record.platform.gpu1_model_worker_permitted),
        "authorization_issuer_implemented": True,
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "next_gate": record.next_gate,
    }


def _run_git(repo_root: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_GIT_FAILED",
            "a required Git inspection could not be completed",
            details=tuple(arguments),
        ) from error
    if result.returncode != 0:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_GIT_FAILED",
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
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ANCESTRY_UNREADABLE",
            "source authority ancestry could not be inspected",
            details=(commit,),
        ) from error
    if result.returncode != 0:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_SOURCE_AUTHORITY_MISSING",
            "a required source authority is not an ancestor of HEAD",
            details=(commit,),
        )


def _require_transient_untracked(repo_root: Path) -> None:
    tracked = _run_git(
        repo_root,
        [
            "ls-files",
            "--",
            *(path.as_posix() for path in _static_transient_paths()),
        ],
    )
    if tracked:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_TRANSIENT_TRACKED",
            "authorization lifecycle artifacts must remain untracked",
            details=tuple(tracked.splitlines()),
        )


def _require_main(
    repo_root: Path,
    allowed_transient_paths: tuple[Path, ...],
) -> str:
    branch = _run_git(repo_root, ["branch", "--show-current"])
    if branch != "main":
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_MAIN_REQUIRED",
            "authorization V2 lifecycle operations require main",
            details=(branch,),
        )
    head = _run_git(repo_root, ["rev-parse", "HEAD"])
    origin_main = _run_git(repo_root, ["rev-parse", "origin/main"])
    if head != origin_main:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_MAIN_NOT_SYNCHRONIZED",
            "local main and origin/main are not synchronized",
        )
    _require_transient_untracked(repo_root)
    status = tuple(
        line
        for line in _run_git(
            repo_root,
            ["status", "--porcelain=v1", "--untracked-files=all"],
        ).splitlines()
        if line
    )
    allowed = {f"?? {relative_path.as_posix()}" for relative_path in allowed_transient_paths}
    unexpected = tuple(sorted(line for line in status if line not in allowed))
    if unexpected:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_REPOSITORY_NOT_CLEAN",
            "repository changes exist outside allowed lifecycle artifacts",
            details=unexpected,
        )
    return head


def _load_canonical(
    path: Path,
    model: type[LocalABCContract],
) -> LocalABCContract:
    try:
        observed = path.read_text(encoding="utf-8")
        contract = model.model_validate_json(observed)
    except (OSError, ValidationError) as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_PAYLOAD_INVALID",
            "an authorization V2 payload failed validation",
            path.as_posix(),
        ) from error
    if observed != contract.canonical_json():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_PAYLOAD_NOT_CANONICAL",
            "an authorization V2 payload is not canonical JSON",
            path.as_posix(),
        )
    return contract


def abandon_legacy_authorization(
    *,
    repo_root: Path,
    archived_authorization_path: Path,
    operator_confirmed: bool,
    no_saved_version_created: bool,
    runtime_execution_performed: bool,
    abandoned_at: datetime | None = None,
) -> dict[str, object]:
    """Terminalize the exact unused V1 authority without inventing a run."""

    root = repo_root.resolve()
    _require_main(root, ())
    _require_ancestor(root, PREVIOUS_ISSUER_MERGE_COMMIT)
    _validate_static(root)

    if operator_confirmed is not True:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_OPERATOR_CONFIRMATION_REQUIRED",
            "explicit operator confirmation is required",
        )
    if no_saved_version_created is not True:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_SAVED_VERSION_STATE_INVALID",
            "legacy abandonment requires no saved version",
        )
    if runtime_execution_performed is not False:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_RUNTIME_STATE_INVALID",
            "legacy abandonment requires no runtime execution",
        )
    if (root / legacy.AUTHORIZATION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_LEGACY_AUTHORIZATION_STILL_PRESENT",
            "legacy authorization must be archived outside the repository",
            legacy.AUTHORIZATION_PATH.as_posix(),
        )
    if (root / legacy.CONSUMPTION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_LEGACY_CONSUMPTION_PRESENT",
            "legacy abandonment is invalid after consumption",
            legacy.CONSUMPTION_PATH.as_posix(),
        )

    archived_path = archived_authorization_path.resolve()
    if archived_path == root or root in archived_path.parents:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ARCHIVE_LOCATION_INVALID",
            "legacy authorization archive must be outside the repository",
            str(archived_path),
        )

    loaded = _load_canonical(
        archived_path,
        legacy.P4ExecutionAuthorization,
    )
    authorization = cast(legacy.P4ExecutionAuthorization, loaded)
    authorization_bytes = authorization.canonical_json().encode("utf-8")
    observed_sha256 = _sha256_bytes(authorization_bytes)

    if observed_sha256 != LEGACY_AUTHORIZATION_SHA256:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_LEGACY_IDENTITY_DRIFT",
            "archived legacy authorization identity drifted",
            str(archived_path),
            (observed_sha256,),
        )
    if authorization.controls.accelerator != "T4_X1":
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_LEGACY_ACCELERATOR_DRIFT",
            "legacy authorization accelerator is not T4_X1",
        )
    if authorization.issued_from_main_commit != PREVIOUS_ISSUER_MERGE_COMMIT:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_LEGACY_ISSUER_DRIFT",
            "legacy authorization issuer merge drifted",
        )

    receipt = LegacyAuthorizationAbandonment(
        abandonment_id=(
            "auragateway-p4-output-contract-diagnostic-execution-authorization-abandonment-v1"
        ),
        status="ABANDONED_BEFORE_EXECUTION",
        legacy_authorization_id=authorization.authorization_id,
        legacy_authorization_sha256=observed_sha256,
        legacy_issued_from_main_commit=PREVIOUS_ISSUER_MERGE_COMMIT,
        legacy_required_accelerator="T4_X1",
        observed_platform_accelerator=PLATFORM_ACCELERATOR,
        reason="KAGGLE_PLATFORM_ACCELERATOR_UNAVAILABLE",
        abandoned_at=abandoned_at or datetime.now(UTC),
        no_saved_version_created=True,
        runtime_execution_performed=False,
        runtime_install_attempts=0,
        model_loads=0,
        worker_starts=0,
        model_requests=0,
        authorization_reusable=False,
        operator_attested=True,
        next_gate=("issue_p4_output_contract_diagnostic_execution_authorization_v2"),
    )
    payload = receipt.canonical_json().encode("utf-8")
    _write_non_overwriting(root / LEGACY_ABANDONMENT_PATH, payload)
    return {
        "status": receipt.status,
        "legacy_authorization_sha256": receipt.legacy_authorization_sha256,
        "abandonment_path": LEGACY_ABANDONMENT_PATH.as_posix(),
        "abandonment_sha256": _sha256_bytes(payload),
        "authorization_reusable": False,
        "runtime_execution_performed": False,
        "next_gate": receipt.next_gate,
    }


def _load_abandonment(repo_root: Path) -> LegacyAuthorizationAbandonment:
    loaded = _load_canonical(
        repo_root / LEGACY_ABANDONMENT_PATH,
        LegacyAuthorizationAbandonment,
    )
    abandonment = cast(LegacyAuthorizationAbandonment, loaded)
    if abandonment.legacy_authorization_sha256 != LEGACY_AUTHORIZATION_SHA256:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ABANDONMENT_IDENTITY_DRIFT",
            "legacy abandonment receipt binds the wrong authorization",
        )
    return abandonment


def _build_authorization(
    *,
    repo_root: Path,
    issuer_head: str,
    confirmation: IssuanceConfirmation,
) -> ExecutionAuthorization:
    _validate_static(repo_root)
    _load_abandonment(repo_root)

    if confirmation.confirmed_issuer_merge_commit != issuer_head:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ISSUER_CONFIRMATION_DRIFT",
            "operator confirmation does not bind current merged main",
        )
    issued_at = confirmation.confirmed_at
    return ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=AuthorizationLifecycle.ISSUED,
        scope=AUTHORIZATION_SCOPE,
        issued_from_main_commit=issuer_head,
        issued_at=issued_at,
        expires_at=(issued_at + timedelta(minutes=confirmation.authorization_window_minutes)),
        implementation=_implementation(repo_root),
        platform=PlatformAllocationControls(),
        capability_observation=confirmation.platform,
        operator_confirmation_recorded=True,
        single_use=True,
        passed_failed_or_interrupted_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        measured_abc_execution_authorized=False,
    )


def issue_authorization(
    *,
    repo_root: Path,
    confirmation: IssuanceConfirmation,
) -> dict[str, object]:
    """Issue one non-overwriting V2 authority after live capability review."""

    root = repo_root.resolve()
    issuer_head = _require_main(
        root,
        (LEGACY_ABANDONMENT_PATH,),
    )
    _require_ancestor(root, PREVIOUS_ISSUER_MERGE_COMMIT)
    if (root / legacy.AUTHORIZATION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_LEGACY_AUTHORIZATION_PRESENT",
            "legacy authorization must remain archived outside repository",
        )
    if (root / CONSUMPTION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ALREADY_CONSUMED",
            "authorization V2 was already consumed",
        )
    authorization = _build_authorization(
        repo_root=root,
        issuer_head=issuer_head,
        confirmation=confirmation,
    )
    payload = authorization.canonical_json().encode("utf-8")
    _write_non_overwriting(root / AUTHORIZATION_PATH, payload)
    return {
        "status": ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V2_ISSUED"),
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": _sha256_bytes(payload),
        "issued_from_main_commit": authorization.issued_from_main_commit,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "platform_accelerator": (authorization.platform.platform_accelerator),
        "allocated_gpu_count": authorization.platform.allocated_gpu_count,
        "worker_cuda_visible_devices": (authorization.platform.worker_cuda_visible_devices),
        "worker_visible_gpu_count": (authorization.platform.worker_visible_gpu_count),
        "worker_gpu_index": authorization.platform.worker_gpu_index,
        "maximum_model_requests": 18,
        "maximum_worker_starts": 1,
        "maximum_model_loads": 1,
        "authorization_reusable": False,
        "next_gate": ISSUED_NEXT_GATE,
    }


def _validate_live_authorization(
    repo_root: Path,
    authorization: ExecutionAuthorization,
    issuer_head: str,
) -> None:
    if authorization.issued_from_main_commit != issuer_head:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ISSUER_DRIFT",
            "authorization V2 was not issued from current merged main",
        )
    if authorization.implementation != _implementation(repo_root):
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_IMPLEMENTATION_DRIFT",
            "authorization V2 implementation binding drifted",
        )
    if authorization.platform != PlatformAllocationControls():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_PLATFORM_DRIFT",
            "authorization V2 platform binding drifted",
        )


def verify_authorization(
    *,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify V2 immediately before the one governed Kaggle execution."""

    root = repo_root.resolve()
    issuer_head = _require_main(
        root,
        (LEGACY_ABANDONMENT_PATH, AUTHORIZATION_PATH),
    )
    _require_ancestor(root, PREVIOUS_ISSUER_MERGE_COMMIT)
    _validate_static(root)
    _load_abandonment(root)
    if (root / CONSUMPTION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ALREADY_CONSUMED",
            "authorization V2 has a consumption receipt",
        )
    loaded = _load_canonical(
        root / AUTHORIZATION_PATH,
        ExecutionAuthorization,
    )
    authorization = cast(ExecutionAuthorization, loaded)
    _validate_live_authorization(root, authorization, issuer_head)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if not authorization.issued_at <= observed_now < authorization.expires_at:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_EXPIRED",
            "authorization V2 is outside its validity window",
        )
    return {
        "status": ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V2_VALID"),
        "authorization_sha256": authorization.fingerprint(),
        "issuer_head_commit": issuer_head,
        "platform_accelerator": (authorization.platform.platform_accelerator),
        "allocated_gpu_count": authorization.platform.allocated_gpu_count,
        "worker_cuda_visible_devices": (authorization.platform.worker_cuda_visible_devices),
        "worker_visible_gpu_count": (authorization.platform.worker_visible_gpu_count),
        "worker_gpu_index": authorization.platform.worker_gpu_index,
        "consumed": False,
        "next_gate": ISSUED_NEXT_GATE,
    }


def consume_authorization(
    *,
    repo_root: Path,
    outcome: ExecutionOutcome,
    saved_version_id: int,
    consumed_at: datetime | None = None,
) -> dict[str, object]:
    """Consume V2 after PASSED, FAILED, or INTERRUPTED."""

    root = repo_root.resolve()
    issuer_head = _require_main(
        root,
        (
            LEGACY_ABANDONMENT_PATH,
            AUTHORIZATION_PATH,
        ),
    )
    _require_ancestor(root, PREVIOUS_ISSUER_MERGE_COMMIT)
    _validate_static(root)
    _load_abandonment(root)
    if (root / CONSUMPTION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V2_ALREADY_CONSUMED",
            "authorization V2 consumption already exists",
        )
    loaded = _load_canonical(
        root / AUTHORIZATION_PATH,
        ExecutionAuthorization,
    )
    authorization = cast(ExecutionAuthorization, loaded)
    _validate_live_authorization(root, authorization, issuer_head)
    authorization_payload = authorization.canonical_json().encode("utf-8")
    receipt = AuthorizationConsumption(
        consumption_id=(
            "auragateway-p4-output-contract-diagnostic-execution-authorization-consumption-v2"
        ),
        authorization_id=AUTHORIZATION_ID,
        authorization_sha256=_sha256_bytes(authorization_payload),
        lifecycle=AuthorizationLifecycle.CONSUMED,
        consumed_at=consumed_at or datetime.now(UTC),
        outcome=outcome,
        saved_version_id=saved_version_id,
        authorization_reusable=False,
        next_gate=CONSUMED_NEXT_GATE,
    )
    payload = receipt.canonical_json().encode("utf-8")
    _write_non_overwriting(root / CONSUMPTION_PATH, payload)
    return {
        "status": ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V2_CONSUMED"),
        "authorization_sha256": receipt.authorization_sha256,
        "consumption_path": CONSUMPTION_PATH.as_posix(),
        "consumption_sha256": _sha256_bytes(payload),
        "outcome": receipt.outcome.value,
        "saved_version_id": receipt.saved_version_id,
        "authorization_reusable": False,
        "next_gate": receipt.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-p4-t4-x2-authorization-v2")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("generate", "validate-implementation", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)

    abandon = subparsers.add_parser("abandon-v1")
    abandon.add_argument("--repo-root", type=Path, required=True)
    abandon.add_argument(
        "--archived-authorization-path",
        type=Path,
        required=True,
    )
    abandon.add_argument("--operator-confirm", action="store_true")
    abandon.add_argument(
        "--confirm-no-saved-version",
        action="store_true",
    )
    abandon.add_argument(
        "--confirm-no-runtime-execution",
        action="store_true",
    )

    issue = subparsers.add_parser("issue")
    issue.add_argument("--repo-root", type=Path, required=True)
    issue.add_argument("--operator-confirm", action="store_true")
    issue.add_argument("--window-minutes", type=int, default=240)
    issue.add_argument("--confirm-issuer-merge-commit", required=True)
    issue.add_argument("--confirm-scope", required=True)
    issue.add_argument("--confirm-backend", required=True)
    issue.add_argument("--confirm-notebook-sha256", required=True)
    issue.add_argument("--confirm-runtime-script-sha256", required=True)
    issue.add_argument("--confirm-wrapper-code-sha256", required=True)
    issue.add_argument("--confirm-request-sha256", required=True)
    issue.add_argument(
        "--confirm-implementation-record-sha256",
        required=True,
    )
    issue.add_argument("--confirm-model-snapshot-sha256", required=True)
    issue.add_argument(
        "--confirm-model-request-budget",
        type=int,
        required=True,
    )
    issue.add_argument(
        "--confirm-runtime-output-count",
        type=int,
        required=True,
    )
    issue.add_argument("--observed-platform-accelerator", required=True)
    issue.add_argument(
        "--observed-allocated-gpu-count",
        type=int,
        required=True,
    )
    issue.add_argument(
        "--confirm-internet-disabled",
        action="store_true",
    )
    issue.add_argument(
        "--observed-wheelhouse-attachment-count",
        type=int,
        required=True,
    )
    issue.add_argument(
        "--observed-model-snapshot-attachment-count",
        type=int,
        required=True,
    )
    issue.add_argument(
        "--confirm-worker-cuda-visible-devices",
        required=True,
    )
    issue.add_argument(
        "--confirm-worker-visible-gpu-count",
        type=int,
        required=True,
    )
    issue.add_argument(
        "--confirm-worker-gpu-index",
        type=int,
        required=True,
    )

    consume = subparsers.add_parser("consume")
    consume.add_argument("--repo-root", type=Path, required=True)
    consume.add_argument("--operator-confirm", action="store_true")
    consume.add_argument(
        "--outcome",
        choices=tuple(item.value for item in ExecutionOutcome),
        required=True,
    )
    consume.add_argument(
        "--saved-version-id",
        type=int,
        required=True,
    )
    return parser


def _error_json(error: AuthorizationError) -> str:
    return ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).canonical_json()


def main(argv: list[str] | None = None) -> int:
    """Run one repository-only V2 authorization lifecycle command."""

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
            summary = validate_implementation(repo_root)
        elif arguments.command == "abandon-v1":
            summary = abandon_legacy_authorization(
                repo_root=repo_root,
                archived_authorization_path=cast(
                    Path,
                    arguments.archived_authorization_path,
                ),
                operator_confirmed=cast(
                    bool,
                    arguments.operator_confirm,
                ),
                no_saved_version_created=cast(
                    bool,
                    arguments.confirm_no_saved_version,
                ),
                runtime_execution_performed=not cast(
                    bool,
                    arguments.confirm_no_runtime_execution,
                ),
            )
        elif arguments.command == "issue":
            if arguments.operator_confirm is not True:
                raise AuthorizationError(
                    "P4_AUTHORIZATION_V2_OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required",
                )
            if arguments.confirm_internet_disabled is not True:
                raise AuthorizationError(
                    "P4_AUTHORIZATION_V2_INTERNET_CONFIRMATION_REQUIRED",
                    "explicit Internet-disabled confirmation is required",
                )
            observed_at = datetime.now(UTC)
            platform = PlatformCapabilityConfirmation(
                observed_at=observed_at,
                capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
                observed_platform_accelerator=cast(
                    str,
                    arguments.observed_platform_accelerator,
                ),
                observed_allocated_gpu_count=cast(
                    int,
                    arguments.observed_allocated_gpu_count,
                ),
                observed_internet_enabled=False,
                observed_wheelhouse_attachment_count=cast(
                    int,
                    arguments.observed_wheelhouse_attachment_count,
                ),
                observed_model_snapshot_attachment_count=cast(
                    int,
                    arguments.observed_model_snapshot_attachment_count,
                ),
                confirmed_worker_cuda_visible_devices=cast(
                    str,
                    arguments.confirm_worker_cuda_visible_devices,
                ),
                confirmed_worker_visible_gpu_count=cast(
                    int,
                    arguments.confirm_worker_visible_gpu_count,
                ),
                confirmed_worker_gpu_index=cast(
                    int,
                    arguments.confirm_worker_gpu_index,
                ),
            )
            confirmation = IssuanceConfirmation(
                operator_confirmed=True,
                confirmed_at=datetime.now(UTC),
                authorization_window_minutes=cast(
                    int,
                    arguments.window_minutes,
                ),
                confirmed_issuer_merge_commit=cast(
                    str,
                    arguments.confirm_issuer_merge_commit,
                ),
                confirmed_scope=cast(str, arguments.confirm_scope),
                confirmed_backend=cast(str, arguments.confirm_backend),
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
                confirmed_model_request_budget=cast(
                    int,
                    arguments.confirm_model_request_budget,
                ),
                confirmed_runtime_output_count=cast(
                    int,
                    arguments.confirm_runtime_output_count,
                ),
                platform=platform,
            )
            summary = issue_authorization(
                repo_root=repo_root,
                confirmation=confirmation,
            )
        elif arguments.command == "verify":
            summary = verify_authorization(repo_root=repo_root)
        elif arguments.command == "consume":
            if arguments.operator_confirm is not True:
                raise AuthorizationError(
                    "P4_AUTHORIZATION_V2_OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required",
                )
            summary = consume_authorization(
                repo_root=repo_root,
                outcome=ExecutionOutcome(cast(str, arguments.outcome)),
                saved_version_id=cast(
                    int,
                    arguments.saved_version_id,
                ),
            )
        else:
            raise AuthorizationError(
                "P4_AUTHORIZATION_V2_COMMAND_UNSUPPORTED",
                "authorization V2 command is unsupported",
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
    except (
        AuthorizationError,
        ValidationError,
        ValueError,
        OSError,
    ) as error:
        if isinstance(error, AuthorizationError):
            output = _error_json(error)
        else:
            output = ErrorEnvelope(
                error_code="P4_AUTHORIZATION_V2_UNEXPECTED",
                safe_message=type(error).__name__,
            ).canonical_json()
        print(output, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
