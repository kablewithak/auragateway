"""Single-use authorization lifecycle for current-line measured A/B/C execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, TypeVar, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "abb4fe30ebddb83bb9596bd2a4bcb6d114089d39"
POLICY_PATH: Final = Path(
    "data/evals/benchmark/preflight-v3/measured_abc_execution_authorization_v1_policy.json"
)
POLICY_SHA256: Final = "158f4cfeb03570c334752e8f6e8733ee8007e4a26b8986c006e9f792d2015730"
SOURCE_PATH: Final = Path("src/auragateway/local_abc/measured_abc_execution_authorization_v1.py")
TEST_PATH: Final = Path("tests/unit/local_abc/test_measured_abc_execution_authorization_v1.py")
ADR_PATH: Final = Path(
    "docs/adr/2026-08-08-local-abc-measured-abc-execution-authorization-v1-implementation.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Measured_ABC_Execution_Authorization_V1_Implementation.md"
)
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_measured_abc_execution_authorization_v1.md")
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_execution_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_execution_authorization_v1_record.json"
)
READINESS_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_execution_readiness_v1.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_execution_authorization_v1.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_execution_authorization_consumption_v1.json"
)
ABANDONMENT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_execution_authorization_abandonment_v1.json"
)

AUTHORIZATION_ID: Final = "auragateway-measured-abc-execution-authorization-v1"
AUTHORIZATION_SCOPE: Final = "MEASURED_LOCAL_ABC_V3_342_TRAJECTORY_EXECUTION"
CONFIRMATION_ID: Final = "auragateway-measured-abc-execution-authorization-confirmation-v1"
READINESS_ID: Final = "auragateway-measured-abc-execution-readiness-v1"
MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
DESIGN_GIT_BLOB_SHA: Final = "740bec826703524e409243475ae713c18173a780"
P5_P6_ACCEPTANCE_GIT_BLOB_SHA: Final = "2cac406ed4e8f2d5c50795d104d2db425abfcbac"
PREFLIGHT_MANIFEST_GIT_BLOB_SHA: Final = "9d25301b23a77c5bfc0ed14383e9cfe16ca9e842"
PLANNED_LEDGER_SHA256: Final = "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
CONDITION_FINGERPRINTS_SHA256: Final = (
    "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
)

MAX_AUTHORIZATION_WINDOW_MINUTES: Final = 240
MAX_PLATFORM_OBSERVATION_AGE_MINUTES: Final = 15
MAX_CONFIRMATION_AGE_MINUTES: Final = 15
_ModelT = TypeVar("_ModelT", bound=LocalABCContract)


class AuthorizationLifecycle(StrEnum):
    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"
    ABANDONED = "ABANDONED"


class ExecutionOutcome(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"
    TIMED_OUT = "TIMED_OUT"
    KAGGLE_PLATFORM_TERMINATED = "KAGGLE_PLATFORM_TERMINATED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class AbandonmentReason(StrEnum):
    OPERATOR_CANCELLED = "OPERATOR_CANCELLED"
    AUTHORIZATION_EXPIRED_UNUSED = "AUTHORIZATION_EXPIRED_UNUSED"
    PLATFORM_CAPABILITY_CHANGED = "PLATFORM_CAPABILITY_CHANGED"
    INPUT_IDENTITY_CHANGED = "INPUT_IDENTITY_CHANGED"
    READINESS_INVALIDATED = "READINESS_INVALIDATED"
    OTHER = "OTHER"


class MeasuredABCAuthorizationError(RuntimeError):
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
    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise MeasuredABCAuthorizationError(
            "MEASURED_ABC_AUTHORIZATION_ARGUMENT_INVALID",
            "Measured A/B/C authorization arguments are invalid",
            details=(message,),
        )


class ArtifactReceipt(LocalABCContract):
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class RuntimeBinding(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    accelerator: Literal["GPU_T4_X2"] = "GPU_T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    execution_backend: Literal["local_vllm"] = "local_vllm"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = MODEL_REPOSITORY
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = MODEL_REVISION
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = MODEL_SNAPSHOT_SHA256
    worker_1_gpu_index: Literal[0] = 0
    worker_1_port: Literal[8001] = 8001
    worker_2_gpu_index: Literal[1] = 1
    worker_2_port: Literal[8002] = 8002


class ExecutionBudget(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    maximum_kaggle_sessions: Literal[1] = 1
    planned_trajectories: Literal[342] = 342
    planned_turns: Literal[1368] = 1368
    maximum_model_request_attempts: Literal[2736] = 2736
    maximum_retries_after_initial_attempt: Literal[1] = 1
    maximum_hidden_retries: Literal[0] = 0
    maximum_saved_versions: Literal[1] = 1
    maximum_external_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0
    replacement_cases_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False


class MeasuredABCExecutionReadiness(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    readiness_id: Literal["auragateway-measured-abc-execution-readiness-v1"] = READINESS_ID
    status: Literal["READY_FOR_MEASURED_ABC_AUTHORIZATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    current_line_p5_pass_accepted: Literal[True]
    current_line_p6_pass_accepted: Literal[True]
    variance_pilot_accepted: Literal[True]
    repetition_count_frozen: Literal[True]
    execution_manifest_frozen: Literal[True]
    execution_manifest_execution_enabled: Literal[False]
    planned_trajectories: Literal[342]
    planned_turns: Literal[1368]
    maximum_model_request_attempts: Literal[2736]
    maximum_hidden_retries: Literal[0]
    planned_run_ledger_sha256: Literal[
        "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
    ]
    condition_fingerprints_sha256: Literal[
        "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
    ]
    execution_manifest: ArtifactReceipt
    variance_pilot_acceptance: ArtifactReceipt
    repetition_count_freeze: ArtifactReceipt
    governed_p5_p6_acceptance: ArtifactReceipt
    runtime: RuntimeBinding
    measured_abc_execution_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    next_gate: Literal["observe_platform_and_issue_measured_abc_execution_authorization_v1"]

    @model_validator(mode="after")
    def validate_receipts(self) -> Self:
        receipts = (
            self.execution_manifest,
            self.variance_pilot_acceptance,
            self.repetition_count_freeze,
            self.governed_p5_p6_acceptance,
        )
        paths = tuple(item.repository_path for item in receipts)
        if len(paths) != len(set(paths)):
            raise ValueError("readiness artifact receipts must have unique repository paths")
        return self


class PlatformCapabilityObservation(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    observed_at: datetime
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"]
    accelerator: Literal["GPU_T4_X2"]
    allocated_gpu_count: Literal[2]
    internet_enabled: Literal[False]
    wheelhouse_input_count: Literal[1]
    model_snapshot_input_count: Literal[1]
    worker_1_cuda_visible_devices: Literal["0"]
    worker_1_gpu_index: Literal[0]
    worker_1_port: Literal[8001]
    worker_2_cuda_visible_devices: Literal["1"]
    worker_2_gpu_index: Literal[1]
    worker_2_port: Literal[8002]

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class IssuanceConfirmation(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    confirmation_id: Literal["auragateway-measured-abc-execution-authorization-confirmation-v1"] = (
        CONFIRMATION_ID
    )
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    confirmed_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    scope: Literal["MEASURED_LOCAL_ABC_V3_342_TRAJECTORY_EXECUTION"]
    authorization_window_minutes: int = Field(ge=1, le=MAX_AUTHORIZATION_WINDOW_MINUTES)
    single_use_acknowledged: Literal[True]
    terminal_consumption_required_acknowledged: Literal[True]
    no_historical_authority_reuse_acknowledged: Literal[True]
    readiness_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmed_runtime: RuntimeBinding
    confirmed_budget: ExecutionBudget
    platform_observation: PlatformCapabilityObservation

    @field_validator("confirmed_at")
    @classmethod
    def validate_confirmed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("confirmed_at must be timezone-aware")
        return value


class MeasuredABCExecutionAuthorization(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["auragateway-measured-abc-execution-authorization-v1"] = (
        AUTHORIZATION_ID
    )
    scope: Literal["MEASURED_LOCAL_ABC_V3_342_TRAJECTORY_EXECUTION"] = AUTHORIZATION_SCOPE
    lifecycle: Literal[AuthorizationLifecycle.ISSUED] = AuthorizationLifecycle.ISSUED
    issued_at: datetime
    expires_at: datetime
    issued_from_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    design_git_blob_sha: Literal["740bec826703524e409243475ae713c18173a780"] = DESIGN_GIT_BLOB_SHA
    governed_p5_p6_acceptance_git_blob_sha: Literal["2cac406ed4e8f2d5c50795d104d2db425abfcbac"] = (
        P5_P6_ACCEPTANCE_GIT_BLOB_SHA
    )
    confirmation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    readiness_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    planned_run_ledger_sha256: Literal[
        "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
    ] = PLANNED_LEDGER_SHA256
    condition_fingerprints_sha256: Literal[
        "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
    ] = CONDITION_FINGERPRINTS_SHA256
    platform_observation: PlatformCapabilityObservation
    runtime: RuntimeBinding
    budget: ExecutionBudget
    single_use: Literal[True] = True
    authorization_reusable: Literal[True] = True
    runtime_execution_authorized: Literal[True] = True
    measured_abc_execution_authorized: Literal[True] = True
    terminal_consumption_required: Literal[True] = True
    historical_authorization_reuse_permitted: Literal[False] = False
    next_gate: Literal["execute_governed_measured_abc_once"] = "execute_governed_measured_abc_once"

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        return self


class AuthorizationConsumption(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["auragateway-measured-abc-execution-authorization-v1"] = (
        AUTHORIZATION_ID
    )
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.CONSUMED] = AuthorizationLifecycle.CONSUMED
    outcome: ExecutionOutcome
    consumed_at: datetime
    saved_version_id: int | None = Field(default=None, gt=0)
    evidence_bundle_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal["preserve_and_accept_or_classify_measured_abc_execution_v1"] = (
        "preserve_and_accept_or_classify_measured_abc_execution_v1"
    )

    @model_validator(mode="after")
    def validate_pass_evidence(self) -> Self:
        if self.outcome is ExecutionOutcome.PASSED:
            if self.saved_version_id is None:
                raise ValueError("PASSED consumption requires saved_version_id")
            if self.evidence_bundle_sha256 is None or self.terminal_log_sha256 is None:
                raise ValueError("PASSED consumption requires evidence and terminal log hashes")
        return self


class AuthorizationAbandonment(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["auragateway-measured-abc-execution-authorization-v1"] = (
        AUTHORIZATION_ID
    )
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.ABANDONED] = AuthorizationLifecycle.ABANDONED
    reason: AbandonmentReason
    abandoned_at: datetime
    authorization_reusable: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal["reconcile_then_issue_fresh_measured_abc_execution_authorization_v1"] = (
        "reconcile_then_issue_fresh_measured_abc_execution_authorization_v1"
    )


class ImplementationReview(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-measured-abc-execution-authorization-v1-review"] = (
        "auragateway-measured-abc-execution-authorization-v1-review"
    )
    implementation_base_main_commit: Literal["abb4fe30ebddb83bb9596bd2a4bcb6d114089d39"] = (
        IMPLEMENTATION_BASE_MAIN_COMMIT
    )
    design_git_blob_sha: Literal["740bec826703524e409243475ae713c18173a780"] = DESIGN_GIT_BLOB_SHA
    governed_p5_p6_acceptance_git_blob_sha: Literal["2cac406ed4e8f2d5c50795d104d2db425abfcbac"] = (
        P5_P6_ACCEPTANCE_GIT_BLOB_SHA
    )
    planned_run_ledger_sha256: Literal[
        "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
    ] = PLANNED_LEDGER_SHA256
    condition_fingerprints_sha256: Literal[
        "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
    ] = CONDITION_FINGERPRINTS_SHA256
    lifecycle_commands: tuple[str, ...]
    readiness_contract_path: str
    readiness_generated_by_issuer: Literal[False] = False
    authorization_issued: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    implementation_status: Literal["IMPLEMENTED_NOT_ISSUED"] = "IMPLEMENTED_NOT_ISSUED"
    next_gate: Literal["merge_then_resolve_readiness_and_issue_once"] = (
        "merge_then_resolve_readiness_and_issue_once"
    )


class ImplementationRecord(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-measured-abc-execution-authorization-v1-record"] = (
        "auragateway-measured-abc-execution-authorization-v1-record"
    )
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: ArtifactReceipt
    tests: ArtifactReceipt
    policy: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    implementation_status: Literal["IMPLEMENTED_NOT_ISSUED"] = "IMPLEMENTED_NOT_ISSUED"
    readiness_contract_implemented: Literal[True] = True
    authorization_issued: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    next_gate: Literal["merge_then_resolve_readiness_and_issue_once"] = (
        "merge_then_resolve_readiness_and_issue_once"
    )


def _canonical(payload: object) -> str:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _error(
    code: str,
    message: str,
    path: Path | None = None,
    details: tuple[str, ...] = (),
) -> Never:
    raise MeasuredABCAuthorizationError(
        code,
        message,
        path.as_posix() if path is not None else None,
        details,
    )


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _error(
            "MEASURED_ABC_AUTHORIZATION_ARTIFACT_MISSING",
            "Required authorization artifact is missing",
            path,
        )
    except json.JSONDecodeError:
        _error(
            "MEASURED_ABC_AUTHORIZATION_JSON_INVALID",
            "Required authorization artifact is not valid JSON",
            path,
        )


def _load_model(model: type[_ModelT], path: Path) -> _ModelT:
    try:
        return model.model_validate(_read_json(path))
    except ValidationError as exc:
        _error(
            "MEASURED_ABC_AUTHORIZATION_SCHEMA_INVALID",
            "Authorization artifact failed typed validation",
            path,
            tuple(item["msg"] for item in exc.errors(include_url=False, include_input=False)),
        )


def _write_new(path: Path, model: LocalABCContract) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        _error(
            "MEASURED_ABC_AUTHORIZATION_NON_OVERWRITE",
            "Authorization lifecycle artifact already exists",
            path,
        )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical(model.model_dump(mode="json")))
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _write_replace(path: Path, model: LocalABCContract) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        _canonical(model.model_dump(mode="json")),
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def _run_git(repo_root: Path, *args: str, binary: bool = False) -> str | bytes:
    if binary:
        completed_bytes = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if completed_bytes.returncode != 0:
            _error(
                "MEASURED_ABC_AUTHORIZATION_GIT_FAILED",
                "Required Git operation failed",
                details=(
                    " ".join(args),
                    completed_bytes.stderr.decode(errors="replace").strip(),
                ),
            )
        return completed_bytes.stdout

    completed_text = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if completed_text.returncode != 0:
        _error(
            "MEASURED_ABC_AUTHORIZATION_GIT_FAILED",
            "Required Git operation failed",
            details=(" ".join(args), completed_text.stderr.strip()),
        )
    return completed_text.stdout


def _git_blob_sha(repo_root: Path, relative: Path) -> str:
    return cast(
        str,
        _run_git(repo_root, "rev-parse", f"HEAD:{relative.as_posix()}"),
    ).strip()


def _git_blob_bytes(repo_root: Path, relative: Path) -> bytes:
    return cast(
        bytes,
        _run_git(repo_root, "show", f"HEAD:{relative.as_posix()}", binary=True),
    )


def _git_sha256(repo_root: Path, relative: Path) -> str:
    return _sha256_bytes(_git_blob_bytes(repo_root, relative))


def _git_receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    payload = _git_blob_bytes(repo_root, relative)
    return ArtifactReceipt(
        repository_path=relative.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _load_policy(repo_root: Path) -> dict[str, object]:
    path = repo_root / POLICY_PATH
    if not path.is_file() or _sha256_file(path) != POLICY_SHA256:
        _error(
            "MEASURED_ABC_AUTHORIZATION_POLICY_DRIFT",
            "Measured A/B/C authorization policy identity drifted",
            POLICY_PATH,
        )
    payload = _read_json(path)
    if not isinstance(payload, dict):
        _error(
            "MEASURED_ABC_AUTHORIZATION_POLICY_INVALID",
            "Measured A/B/C authorization policy root is invalid",
            POLICY_PATH,
        )
    return cast(dict[str, object], payload)


def _validate_current_authority(repo_root: Path) -> None:
    _load_policy(repo_root)
    expected_blobs = {
        Path(
            "benchmarks/local_abc/auragateway_measured_abc_execution_authorization_v1_design.json"
        ): DESIGN_GIT_BLOB_SHA,
        Path(
            "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"
        ): P5_P6_ACCEPTANCE_GIT_BLOB_SHA,
        Path("data/evals/benchmark/preflight-v3/manifest.json"): PREFLIGHT_MANIFEST_GIT_BLOB_SHA,
        Path(
            "benchmarks/local_abc/measured_execution_authorization_v1.json"
        ): "9a712372cee83c4af4a026081ec01ddbc809effa",
        Path(
            "data/evals/benchmark/freeze-v1/execution_manifest.json"
        ): "791299bb0df45441f25ed8c1e030d84ca1a31ec3",
        Path(
            "src/auragateway/local_abc/measured_authorization.py"
        ): "58438a4e2b125df1e908f18eff79d27124f40b34",
    }
    for path, expected_blob in expected_blobs.items():
        observed = _git_blob_sha(repo_root, path)
        if observed != expected_blob:
            _error(
                "MEASURED_ABC_AUTHORIZATION_AUTHORITY_DRIFT",
                "Repository authority identity drifted",
                path,
                (f"expected={expected_blob}", f"observed={observed}"),
            )

    ledger = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
    fingerprints = Path("data/evals/benchmark/preflight-v3/condition_fingerprints.json")
    if _git_sha256(repo_root, ledger) != PLANNED_LEDGER_SHA256:
        _error(
            "MEASURED_ABC_AUTHORIZATION_LEDGER_DRIFT",
            "Planned run ledger identity drifted",
            ledger,
        )
    if _git_sha256(repo_root, fingerprints) != CONDITION_FINGERPRINTS_SHA256:
        _error(
            "MEASURED_ABC_AUTHORIZATION_FINGERPRINT_DRIFT",
            "Condition fingerprint identity drifted",
            fingerprints,
        )

    acceptance_path = Path(
        "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"
    )
    acceptance_payload = json.loads(_git_blob_bytes(repo_root, acceptance_path))
    required_acceptance = {
        "current_line_p5_pass_accepted": True,
        "current_line_p6_pass_accepted": True,
        "governed_acceptance_status": "ACCEPTED_GOVERNED_EXECUTION_PASS",
        "measured_abc_eligible": True,
        "measured_abc_execution_authorized": False,
        "runtime_execution_authorized": False,
        "saved_version_id": 340976295,
    }
    if not isinstance(acceptance_payload, dict):
        _error(
            "MEASURED_ABC_AUTHORIZATION_ACCEPTANCE_INVALID",
            "Governed P5/P6 acceptance root is invalid",
            acceptance_path,
        )
    for key, expected_acceptance_value in required_acceptance.items():
        if acceptance_payload.get(key) != expected_acceptance_value:
            _error(
                "MEASURED_ABC_AUTHORIZATION_ACCEPTANCE_INVALID",
                "Governed P5/P6 acceptance semantics drifted",
                acceptance_path,
                (key,),
            )

    preflight_path = Path("data/evals/benchmark/preflight-v3/manifest.json")
    preflight_payload = json.loads(_git_blob_bytes(repo_root, preflight_path))
    required_preflight = {
        "planning_lineage_complete": True,
        "execution_enabled": False,
        "execution_manifest_frozen": False,
        "measured_execution_authorized": False,
    }
    if not isinstance(preflight_payload, dict):
        _error(
            "MEASURED_ABC_AUTHORIZATION_PREFLIGHT_INVALID",
            "Preflight v3 manifest root is invalid",
            preflight_path,
        )
    for key, expected_preflight_value in required_preflight.items():
        if preflight_payload.get(key) != expected_preflight_value:
            _error(
                "MEASURED_ABC_AUTHORIZATION_PREFLIGHT_INVALID",
                "Preflight v3 planning authority semantics drifted",
                preflight_path,
                (key,),
            )


def _validate_receipt(repo_root: Path, receipt: ArtifactReceipt) -> None:
    observed = _git_receipt(repo_root, Path(receipt.repository_path))
    if observed != receipt:
        _error(
            "MEASURED_ABC_AUTHORIZATION_READINESS_RECEIPT_DRIFT",
            "Readiness receipt does not match committed repository bytes",
            Path(receipt.repository_path),
        )


def _load_readiness(repo_root: Path) -> tuple[MeasuredABCExecutionReadiness, str]:
    payload = _git_blob_bytes(repo_root, READINESS_PATH)
    try:
        readiness = MeasuredABCExecutionReadiness.model_validate_json(payload)
    except ValidationError as exc:
        _error(
            "MEASURED_ABC_AUTHORIZATION_READINESS_INVALID",
            "Measured A/B/C readiness record failed typed validation",
            READINESS_PATH,
            tuple(item["msg"] for item in exc.errors(include_url=False, include_input=False)),
        )

    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            readiness.source_main_commit,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        timeout=20,
    )
    if result.returncode != 0:
        _error(
            "MEASURED_ABC_AUTHORIZATION_READINESS_ANCESTRY_INVALID",
            "Readiness source main is not an ancestor of current HEAD",
            READINESS_PATH,
        )

    for receipt in (
        readiness.execution_manifest,
        readiness.variance_pilot_acceptance,
        readiness.repetition_count_freeze,
        readiness.governed_p5_p6_acceptance,
    ):
        _validate_receipt(repo_root, receipt)

    acceptance_receipt = _git_receipt(
        repo_root,
        Path("benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"),
    )
    if readiness.governed_p5_p6_acceptance != acceptance_receipt:
        _error(
            "MEASURED_ABC_AUTHORIZATION_READINESS_ACCEPTANCE_DRIFT",
            "Readiness does not bind the current governed P5/P6 acceptance",
            READINESS_PATH,
        )

    return readiness, _sha256_bytes(payload)


def _readiness_state(repo_root: Path) -> tuple[bool, str | None]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "cat-file",
            "-e",
            f"HEAD:{READINESS_PATH.as_posix()}",
        ],
        check=False,
        capture_output=True,
        timeout=20,
    )
    if result.returncode != 0:
        return False, "readiness_record_not_committed"
    _load_readiness(repo_root)
    return True, None


def _artifact_receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file():
        _error(
            "MEASURED_ABC_AUTHORIZATION_IMPLEMENTATION_ARTIFACT_MISSING",
            "Implementation artifact is missing",
            relative,
        )
    return ArtifactReceipt(
        repository_path=relative.as_posix(),
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def build_review(repo_root: Path) -> ImplementationReview:
    _validate_current_authority(repo_root)
    return ImplementationReview(
        lifecycle_commands=(
            "generate",
            "validate-implementation",
            "issue",
            "verify",
            "consume",
            "abandon",
        ),
        readiness_contract_path=READINESS_PATH.as_posix(),
    )


def build_record(repo_root: Path, review: ImplementationReview) -> ImplementationRecord:
    review_bytes = _canonical(review.model_dump(mode="json")).encode("utf-8")
    return ImplementationRecord(
        review_sha256=_sha256_bytes(review_bytes),
        source=_artifact_receipt(repo_root, SOURCE_PATH),
        tests=_artifact_receipt(repo_root, TEST_PATH),
        policy=_artifact_receipt(repo_root, POLICY_PATH),
        adr=_artifact_receipt(repo_root, ADR_PATH),
        report=_artifact_receipt(repo_root, REPORT_PATH),
        runbook=_artifact_receipt(repo_root, RUNBOOK_PATH),
    )


def generate(repo_root: Path) -> dict[str, object]:
    review = build_review(repo_root)
    record = build_record(repo_root, review)
    _write_replace(repo_root / REVIEW_PATH, review)
    _write_replace(repo_root / RECORD_PATH, record)
    return {
        "status": "MEASURED_ABC_EXECUTION_AUTHORIZATION_V1_GENERATED",
        "implementation_status": "IMPLEMENTED_NOT_ISSUED",
        "authorization_issued": False,
        "measured_abc_execution_authorized": False,
        "runtime_execution_authorized": False,
        "next_gate": "merge_then_resolve_readiness_and_issue_once",
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    review = build_review(repo_root)
    record = build_record(repo_root, review)
    observed_review = _load_model(ImplementationReview, repo_root / REVIEW_PATH)
    observed_record = _load_model(ImplementationRecord, repo_root / RECORD_PATH)
    if observed_review != review:
        _error(
            "MEASURED_ABC_AUTHORIZATION_REVIEW_DRIFT",
            "Implementation review is not deterministic",
            REVIEW_PATH,
        )
    if observed_record != record:
        _error(
            "MEASURED_ABC_AUTHORIZATION_RECORD_DRIFT",
            "Implementation record is not deterministic",
            RECORD_PATH,
        )
    issuance_ready, blocker = _readiness_state(repo_root)
    return {
        "status": "MEASURED_ABC_EXECUTION_AUTHORIZATION_V1_VALID",
        "implementation_status": "IMPLEMENTED_NOT_ISSUED",
        "issuance_ready": issuance_ready,
        "issuance_blocker": blocker,
        "authorization_issued": False,
        "measured_abc_execution_authorized": False,
        "runtime_execution_authorized": False,
        "next_gate": (
            "observe_platform_and_issue_measured_abc_execution_authorization_v1"
            if issuance_ready
            else "resolve_measured_abc_execution_readiness_v1"
        ),
    }


def _require_clean_main(repo_root: Path) -> str:
    branch = cast(str, _run_git(repo_root, "branch", "--show-current")).strip()
    if branch != "main":
        _error(
            "MEASURED_ABC_AUTHORIZATION_BRANCH_INVALID",
            "Issuance requires branch main",
            details=(branch,),
        )
    head = cast(str, _run_git(repo_root, "rev-parse", "HEAD")).strip()
    origin = cast(str, _run_git(repo_root, "rev-parse", "origin/main")).strip()
    if head != origin:
        _error(
            "MEASURED_ABC_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "Issuance requires main to match origin/main",
            details=(head, origin),
        )
    status = cast(
        str,
        _run_git(repo_root, "status", "--short", "--untracked-files=all"),
    ).splitlines()
    if status:
        _error(
            "MEASURED_ABC_AUTHORIZATION_WORKTREE_NOT_CLEAN",
            "Issuance requires a clean working tree",
            details=tuple(status),
        )
    return head


def _require_active_worktree(repo_root: Path, issued_from_main_commit: str) -> None:
    branch = cast(str, _run_git(repo_root, "branch", "--show-current")).strip()
    head = cast(str, _run_git(repo_root, "rev-parse", "HEAD")).strip()
    origin = cast(str, _run_git(repo_root, "rev-parse", "origin/main")).strip()
    if branch != "main" or head != origin or head != issued_from_main_commit:
        _error(
            "MEASURED_ABC_AUTHORIZATION_REPOSITORY_DRIFT",
            "Repository identity drifted after authorization issuance",
            details=(branch, head, origin),
        )
    status = cast(
        str,
        _run_git(repo_root, "status", "--short", "--untracked-files=all"),
    ).splitlines()
    expected = [f"?? {AUTHORIZATION_PATH.as_posix()}"]
    if status != expected:
        _error(
            "MEASURED_ABC_AUTHORIZATION_WORKTREE_DRIFT",
            "Active authorization requires exactly one untracked authorization artifact",
            details=tuple(status),
        )


def _validate_freshness(
    confirmation: IssuanceConfirmation,
    now: datetime,
) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        _error(
            "MEASURED_ABC_AUTHORIZATION_CLOCK_INVALID",
            "Authorization clock must be timezone-aware",
        )
    observation_age = now - confirmation.platform_observation.observed_at
    confirmation_age = now - confirmation.confirmed_at
    if observation_age < timedelta(0) or observation_age > timedelta(
        minutes=MAX_PLATFORM_OBSERVATION_AGE_MINUTES
    ):
        _error(
            "MEASURED_ABC_AUTHORIZATION_PLATFORM_OBSERVATION_STALE",
            "Platform capability observation is stale or future-dated",
        )
    if confirmation_age < timedelta(0) or confirmation_age > timedelta(
        minutes=MAX_CONFIRMATION_AGE_MINUTES
    ):
        _error(
            "MEASURED_ABC_AUTHORIZATION_CONFIRMATION_STALE",
            "Operator confirmation is stale or future-dated",
        )


def issue_authorization(
    repo_root: Path,
    confirmation: IssuanceConfirmation,
    confirmation_sha256: str,
    now: datetime | None = None,
) -> dict[str, object]:
    validate_implementation(repo_root)
    head = _require_clean_main(repo_root)
    readiness, readiness_sha = _load_readiness(repo_root)
    current = datetime.now(UTC) if now is None else now
    _validate_freshness(confirmation, current)

    if confirmation.confirmed_issuer_merge_commit != head:
        _error(
            "MEASURED_ABC_AUTHORIZATION_ISSUER_IDENTITY_MISMATCH",
            "Confirmation does not bind the synchronized issuer merge commit",
        )
    if confirmation.readiness_sha256 != readiness_sha:
        _error(
            "MEASURED_ABC_AUTHORIZATION_READINESS_IDENTITY_MISMATCH",
            "Confirmation does not bind the current readiness record",
        )
    if confirmation.execution_manifest_sha256 != readiness.execution_manifest.sha256:
        _error(
            "MEASURED_ABC_AUTHORIZATION_MANIFEST_IDENTITY_MISMATCH",
            "Confirmation does not bind the current execution manifest",
        )
    if confirmation.confirmed_runtime != readiness.runtime:
        _error(
            "MEASURED_ABC_AUTHORIZATION_RUNTIME_CONFIRMATION_MISMATCH",
            "Confirmation runtime differs from readiness runtime",
        )
    if confirmation.confirmed_budget != ExecutionBudget():
        _error(
            "MEASURED_ABC_AUTHORIZATION_BUDGET_CONFIRMATION_MISMATCH",
            "Confirmation budget differs from the frozen execution budget",
        )
    if any(
        (repo_root / path).exists()
        for path in (AUTHORIZATION_PATH, CONSUMPTION_PATH, ABANDONMENT_PATH)
    ):
        _error(
            "MEASURED_ABC_AUTHORIZATION_LIFECYCLE_ALREADY_EXISTS",
            "An authorization lifecycle artifact already exists",
        )

    authorization = MeasuredABCExecutionAuthorization(
        issued_at=current,
        expires_at=current + timedelta(minutes=confirmation.authorization_window_minutes),
        issued_from_main_commit=head,
        confirmation_sha256=confirmation_sha256,
        readiness_sha256=readiness_sha,
        execution_manifest_sha256=readiness.execution_manifest.sha256,
        platform_observation=confirmation.platform_observation,
        runtime=readiness.runtime,
        budget=ExecutionBudget(),
    )
    _write_new(repo_root / AUTHORIZATION_PATH, authorization)
    return {
        "status": "MEASURED_ABC_EXECUTION_AUTHORIZATION_V1_ISSUED",
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": _sha256_file(repo_root / AUTHORIZATION_PATH),
        "issued_from_main_commit": head,
        "expires_at": authorization.expires_at.isoformat(),
        "runtime_execution_authorized": True,
        "measured_abc_execution_authorized": True,
        "single_use": True,
        "next_gate": "verify_then_execute_governed_measured_abc_once",
    }


def _load_authorization(repo_root: Path) -> MeasuredABCExecutionAuthorization:
    return _load_model(MeasuredABCExecutionAuthorization, repo_root / AUTHORIZATION_PATH)


def verify_authorization(
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    authorization = _load_authorization(repo_root)
    _require_active_worktree(repo_root, authorization.issued_from_main_commit)
    current = datetime.now(UTC) if now is None else now
    if current > authorization.expires_at:
        _error(
            "MEASURED_ABC_AUTHORIZATION_EXPIRED",
            "Measured A/B/C authorization expired",
            AUTHORIZATION_PATH,
        )
    if (repo_root / CONSUMPTION_PATH).exists() or (repo_root / ABANDONMENT_PATH).exists():
        _error(
            "MEASURED_ABC_AUTHORIZATION_TERMINAL",
            "Measured A/B/C authorization is already terminal",
        )
    readiness, readiness_sha = _load_readiness(repo_root)
    if readiness_sha != authorization.readiness_sha256:
        _error(
            "MEASURED_ABC_AUTHORIZATION_READINESS_DRIFT",
            "Readiness identity drifted after issuance",
            READINESS_PATH,
        )
    if readiness.execution_manifest.sha256 != authorization.execution_manifest_sha256:
        _error(
            "MEASURED_ABC_AUTHORIZATION_MANIFEST_DRIFT",
            "Execution manifest identity drifted after issuance",
            READINESS_PATH,
        )
    return {
        "status": "MEASURED_ABC_EXECUTION_AUTHORIZATION_V1_VERIFIED",
        "authorization_sha256": _sha256_file(repo_root / AUTHORIZATION_PATH),
        "runtime_execution_authorized": True,
        "measured_abc_execution_authorized": True,
        "authorization_reusable": True,
        "next_gate": "execute_governed_measured_abc_once",
    }


def consume_authorization(
    repo_root: Path,
    outcome: ExecutionOutcome,
    saved_version_id: int | None,
    evidence_bundle_sha256: str | None,
    terminal_log_sha256: str | None,
    now: datetime | None = None,
) -> dict[str, object]:
    authorization = _load_authorization(repo_root)
    _require_active_worktree(repo_root, authorization.issued_from_main_commit)
    if (repo_root / CONSUMPTION_PATH).exists() or (repo_root / ABANDONMENT_PATH).exists():
        _error(
            "MEASURED_ABC_AUTHORIZATION_TERMINAL",
            "Measured A/B/C authorization is already terminal",
        )
    current = datetime.now(UTC) if now is None else now
    consumption = AuthorizationConsumption(
        authorization_sha256=_sha256_file(repo_root / AUTHORIZATION_PATH),
        outcome=outcome,
        consumed_at=current,
        saved_version_id=saved_version_id,
        evidence_bundle_sha256=evidence_bundle_sha256,
        terminal_log_sha256=terminal_log_sha256,
    )
    _write_new(repo_root / CONSUMPTION_PATH, consumption)
    return {
        "status": "MEASURED_ABC_EXECUTION_AUTHORIZATION_V1_CONSUMED",
        "outcome": outcome.value,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": "preserve_and_accept_or_classify_measured_abc_execution_v1",
    }


def abandon_authorization(
    repo_root: Path,
    reason: AbandonmentReason,
    now: datetime | None = None,
) -> dict[str, object]:
    authorization = _load_authorization(repo_root)
    _require_active_worktree(repo_root, authorization.issued_from_main_commit)
    if (repo_root / CONSUMPTION_PATH).exists() or (repo_root / ABANDONMENT_PATH).exists():
        _error(
            "MEASURED_ABC_AUTHORIZATION_TERMINAL",
            "Measured A/B/C authorization is already terminal",
        )
    current = datetime.now(UTC) if now is None else now
    abandonment = AuthorizationAbandonment(
        authorization_sha256=_sha256_file(repo_root / AUTHORIZATION_PATH),
        reason=reason,
        abandoned_at=current,
    )
    _write_new(repo_root / ABANDONMENT_PATH, abandonment)
    return {
        "status": "MEASURED_ABC_EXECUTION_AUTHORIZATION_V1_ABANDONED",
        "reason": reason.value,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": "reconcile_then_issue_fresh_measured_abc_execution_authorization_v1",
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="measured-abc-execution-authorization-v1")
    sub = parser.add_subparsers(dest="command", required=True)

    for command in ("generate", "validate-implementation", "verify"):
        child = sub.add_parser(command)
        child.add_argument("--repo-root", type=Path, required=True)

    issue = sub.add_parser("issue")
    issue.add_argument("--repo-root", type=Path, required=True)
    issue.add_argument("--confirmation-json", type=Path, required=True)

    consume = sub.add_parser("consume")
    consume.add_argument("--repo-root", type=Path, required=True)
    consume.add_argument(
        "--outcome",
        choices=tuple(item.value for item in ExecutionOutcome),
        required=True,
    )
    consume.add_argument("--saved-version-id", type=int)
    consume.add_argument("--evidence-bundle-sha256")
    consume.add_argument("--terminal-log-sha256")

    abandon = sub.add_parser("abandon")
    abandon.add_argument("--repo-root", type=Path, required=True)
    abandon.add_argument(
        "--reason",
        choices=tuple(item.value for item in AbandonmentReason),
        required=True,
    )
    return parser


def main() -> int:
    try:
        args = _parser().parse_args()
        repo_root = args.repo_root.resolve()
        if args.command == "generate":
            result = generate(repo_root)
        elif args.command == "validate-implementation":
            result = validate_implementation(repo_root)
        elif args.command == "verify":
            result = verify_authorization(repo_root)
        elif args.command == "issue":
            confirmation = _load_model(IssuanceConfirmation, args.confirmation_json)
            result = issue_authorization(
                repo_root,
                confirmation,
                _sha256_file(args.confirmation_json),
            )
        elif args.command == "consume":
            result = consume_authorization(
                repo_root=repo_root,
                outcome=ExecutionOutcome(args.outcome),
                saved_version_id=args.saved_version_id,
                evidence_bundle_sha256=args.evidence_bundle_sha256,
                terminal_log_sha256=args.terminal_log_sha256,
            )
        else:
            result = abandon_authorization(
                repo_root=repo_root,
                reason=AbandonmentReason(args.reason),
            )
        print(_canonical(result), end="")
        return 0
    except MeasuredABCAuthorizationError as exc:
        envelope = ErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(_canonical(envelope.model_dump(mode="json")), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
