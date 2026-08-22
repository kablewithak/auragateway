"""Govern one successor P5/P6 execution authorization without issuing by default."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

SUCCESSOR_MERGE_COMMIT: Final = "2b1841aee4397ae0c72bad6b2c9e7069835d8399"
AUTHORIZATION_SCOPE: Final = "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
AUTHORIZATION_ID: Final = (
    "auragateway-p5-p6-mechanism-admission-successor-v1-execution-authorization"
)
AUTHORIZATION_FILENAME: Final = "execution_authorization_v1.json"
CONFIRMATION_PHRASE: Final = (
    "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
    "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1_EXECUTION"
)
MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES: Final = 15
MAXIMUM_OPERATOR_CONFIRMATION_AGE_MINUTES: Final = 15
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
DEFAULT_AUTHORIZATION_WINDOW_MINUTES: Final = 180

IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_v1_implementation_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_v1_implementation_record.json"
)
DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1.json"
)
DESIGN_RECORD_SHA256: Final = "6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c"
MECHANISM_CONTRACT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_contract_v2.json"
)
MECHANISM_CONTRACT_SHA256: Final = (
    "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
)
IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_v1.py"
)
IMPLEMENTATION_SOURCE_SHA256: Final = (
    "90e74350782ec833865136c9efc3074d714a94148e7da5fd959483935a3488f3"
)
IMPLEMENTATION_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_mechanism_admission_successor_v1.py.tmpl"
)
IMPLEMENTATION_TEMPLATE_SHA256: Final = (
    "e317ec9c06e256f21a80c3008a09a20036e5b4a8d978797013dacadd48d0b745"
)
IMPLEMENTATION_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_mechanism_admission_successor_v1.py"
)
IMPLEMENTATION_TEST_SHA256: Final = (
    "a4f40a3d057f44a69880c7354c7cbb40defad04c911a6305c94dd854e5c6feb1"
)
IMPLEMENTATION_ADDENDUM_PATH: Final = Path(
    "docs/adr/2026-08-22-local-abc-p5-p6-mechanism-admission-successor-"
    "runtime-outcome-contract-addendum-v1.md"
)
IMPLEMENTATION_ADDENDUM_SHA256: Final = (
    "395f9c7e9955594d7c962659dd882e0851dcc6f9833715bb53e5d37bb7439239"
)
IMPLEMENTATION_REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P5_P6_Mechanism_Admission_Successor_Implementation_V1.md"
)
IMPLEMENTATION_REPORT_SHA256: Final = (
    "da39a3eb813a310899a5b94df4e242143fdcdbe6da69939f5172daaf07f8aed6"
)
IMPLEMENTATION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p5_p6_mechanism_admission_successor_implementation_v1.md"
)
IMPLEMENTATION_RUNBOOK_SHA256: Final = (
    "4be593b0d8268a5d957cb3e2645e712cbfcc25888003dd3f704f4777579daa60"
)
IMPLEMENTATION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p5_p6_mechanism_admission_successor_v1.ipynb"
)
IMPLEMENTATION_NOTEBOOK_SHA256: Final = (
    "1c7e214bd7f31747d43cf574c22b4ae1eee816ddff6faa7f267885f0c8f7de74"
)
RUNTIME_SCRIPT_SHA256: Final = "a63d395ec3caa2f7a13723679b0bf081ba11d4246cf2b8e87ea644d3bcecd958"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_execution_authorization_v1.py"
)
TRANSPORT_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_authorization_transport_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_mechanism_admission_successor_execution_authorization_v1.py"
)
TRANSPORT_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_mechanism_admission_successor_authorization_transport_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-22-local-abc-p5-p6-mechanism-admission-successor-"
    "execution-authorization-issuer-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/"
    "AuraGateway_P5_P6_Mechanism_Admission_Successor_Execution_Authorization_Issuer_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/"
    "local_abc_p5_p6_mechanism_admission_successor_execution_authorization_issuer_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_execution_authorization_"
    "issuer_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_execution_authorization_"
    "issuer_v1_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_v1_execution_authorization_live.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_v1_authorization_terminal.json"
)

STATIC_PATHS: Final = (
    SOURCE_PATH,
    TRANSPORT_PATH,
    TEST_PATH,
    TRANSPORT_TEST_PATH,
    ADR_PATH,
    REPORT_PATH,
    RUNBOOK_PATH,
)
GENERATED_PATHS: Final = (REVIEW_PATH, RECORD_PATH)
CANDIDATE_PATHS: Final = tuple(sorted((*STATIC_PATHS, *GENERATED_PATHS)))
NEXT_GATE: Final = (
    "OBSERVE_FRESH_KAGGLE_T4_X2_AND_ISSUE_ONE_"
    "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1_EXECUTION_AUTHORIZATION"
)

BOUND_ARTIFACTS: Final = (
    ("implementation_review", IMPLEMENTATION_REVIEW_PATH, IMPLEMENTATION_REVIEW_SHA256),
    ("successor_design", DESIGN_RECORD_PATH, DESIGN_RECORD_SHA256),
    ("mechanism_admission_contract", MECHANISM_CONTRACT_PATH, MECHANISM_CONTRACT_SHA256),
    ("implementation_source", IMPLEMENTATION_SOURCE_PATH, IMPLEMENTATION_SOURCE_SHA256),
    ("implementation_template", IMPLEMENTATION_TEMPLATE_PATH, IMPLEMENTATION_TEMPLATE_SHA256),
    ("implementation_tests", IMPLEMENTATION_TEST_PATH, IMPLEMENTATION_TEST_SHA256),
    ("implementation_addendum", IMPLEMENTATION_ADDENDUM_PATH, IMPLEMENTATION_ADDENDUM_SHA256),
    ("implementation_report", IMPLEMENTATION_REPORT_PATH, IMPLEMENTATION_REPORT_SHA256),
    ("implementation_runbook", IMPLEMENTATION_RUNBOOK_PATH, IMPLEMENTATION_RUNBOOK_SHA256),
    ("implementation_notebook", IMPLEMENTATION_NOTEBOOK_PATH, IMPLEMENTATION_NOTEBOOK_SHA256),
)


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
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_ARGUMENT_INVALID",
            "successor authorization arguments are invalid",
            details=(message,),
        )


class FrozenModel(BaseModel):
    """Strict immutable persisted-contract base."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))


class ArtifactIdentity(FrozenModel):
    role: str
    path: str
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
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return normalize_time(value, "platform observed_at")


class IssuanceConfirmation(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    confirmation_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-v1-execution-authorization-confirmation"
    ]
    operator_confirmed: Literal[True]
    exact_confirmation_phrase: Literal[
        "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
        "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1_EXECUTION"
    ]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(
        ge=1,
        le=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
    )
    confirmed_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmed_scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"]
    confirmed_successor_merge_commit: Literal["2b1841aee4397ae0c72bad6b2c9e7069835d8399"]
    confirmed_implementation_review_sha256: Literal[
        "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
    ]
    confirmed_design_record_sha256: Literal[
        "6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c"
    ]
    confirmed_mechanism_contract_sha256: Literal[
        "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
    ]
    confirmed_implementation_addendum_sha256: Literal[
        "395f9c7e9955594d7c962659dd882e0851dcc6f9833715bb53e5d37bb7439239"
    ]
    confirmed_runtime_script_sha256: Literal[
        "a63d395ec3caa2f7a13723679b0bf081ba11d4246cf2b8e87ea644d3bcecd958"
    ]
    execution_limits: ExecutionLimits
    platform: PlatformObservation

    @field_validator("confirmed_at")
    @classmethod
    def normalize_confirmed_at(cls, value: datetime) -> datetime:
        return normalize_time(value, "confirmed_at")

    @model_validator(mode="after")
    def platform_must_precede_confirmation(self) -> Self:
        if self.platform.observed_at > self.confirmed_at:
            raise ValueError("platform observation cannot follow operator confirmation")
        return self


class ExecutionAuthorization(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-v1-execution-authorization"
    ]
    authorization_filename: Literal["execution_authorization_v1.json"]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"]
    successor_merge_commit: Literal["2b1841aee4397ae0c72bad6b2c9e7069835d8399"]
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issued_at: datetime
    expires_at: datetime
    runtime_script_sha256: Literal[
        "a63d395ec3caa2f7a13723679b0bf081ba11d4246cf2b8e87ea644d3bcecd958"
    ]
    implementation_review_sha256: Literal[
        "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
    ]
    design_record_sha256: Literal[
        "6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c"
    ]
    mechanism_admission_contract_sha256: Literal[
        "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
    ]
    implementation_addendum_sha256: Literal[
        "395f9c7e9955594d7c962659dd882e0851dcc6f9833715bb53e5d37bb7439239"
    ]
    runtime_execution_authorized: Literal[True]
    single_use: Literal[True]
    every_terminal_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    maximum_model_requests: Literal[6]
    maximum_worker_starts: Literal[3]
    maximum_model_loads: Literal[3]
    hidden_retries_permitted: Literal[0]
    authorization_reusable: Literal[False]

    @field_validator("issued_at", "expires_at")
    @classmethod
    def normalize_authorization_time(cls, value: datetime) -> datetime:
        return normalize_time(value, "authorization timestamp")

    @model_validator(mode="after")
    def expiry_must_follow_issue(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        return self


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


class AuthorizationTerminalReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    receipt_id: Literal["auragateway-p5-p6-mechanism-admission-successor-v1-authorization-terminal"]
    authorization_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-v1-execution-authorization"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    disposition: TerminalDisposition
    execution_attempted: bool
    execution_outcome: ExecutionOutcome | None
    saved_version_id: int | None = Field(default=None, ge=1)
    evidence_zip_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    terminalized_at: datetime
    authorization_reusable: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False

    @field_validator("terminalized_at")
    @classmethod
    def normalize_terminalized_at(cls, value: datetime) -> datetime:
        return normalize_time(value, "terminalized_at")

    @model_validator(mode="after")
    def validate_terminal_semantics(self) -> Self:
        attempted = self.disposition in {
            TerminalDisposition.CONSUMED,
            TerminalDisposition.OUTCOME_UNKNOWN,
        }
        if attempted != self.execution_attempted:
            raise ValueError("terminal disposition and execution-attempt flag disagree")
        if not self.execution_attempted and self.execution_outcome is not None:
            raise ValueError("unused authorization cannot have an execution outcome")
        if self.disposition is TerminalDisposition.CONSUMED and self.execution_outcome is None:
            raise ValueError("consumed authorization requires a known execution outcome")
        if (
            self.disposition is TerminalDisposition.OUTCOME_UNKNOWN
            and self.execution_outcome is not None
        ):
            raise ValueError("OUTCOME_UNKNOWN cannot carry a known execution outcome")
        if self.execution_outcome is ExecutionOutcome.PASSED and (
            self.saved_version_id is None or self.evidence_zip_sha256 is None
        ):
            raise ValueError("passed execution requires saved version and evidence identity")
        return self


class IssuerReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-execution-authorization-issuer-v1-review"
    ]
    status: Literal["APPROVED_FOR_MERGE_NOT_ISSUANCE"]
    successor_merge_commit: Literal["2b1841aee4397ae0c72bad6b2c9e7069835d8399"]
    authorization_scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"]
    candidate_artifacts: tuple[ArtifactIdentity, ...]
    maximum_model_requests: Literal[6]
    maximum_worker_starts: Literal[3]
    maximum_model_loads: Literal[3]
    hidden_retries_permitted: Literal[0]
    human_confirmation_required: Literal[True]
    fresh_platform_observation_required: Literal[True]
    single_use_required: Literal[True]
    transport_contract: Literal["GOVERNED_ROOT_EXACT_FLAT_V1"]
    exact_flat_file_count: Literal[3]
    live_authorization_issued: Literal[False]
    runtime_execution_authorized: Literal[False]
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    next_gate: str


class IssuerRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-execution-authorization-issuer-v1-record"
    ]
    status: Literal["IMPLEMENTED_NOT_ISSUED"]
    successor_merge_commit: Literal["2b1841aee4397ae0c72bad6b2c9e7069835d8399"]
    review: ArtifactIdentity
    authorization_scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"]
    authorization_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-v1-execution-authorization"
    ]
    runtime_script_sha256: Literal[
        "a63d395ec3caa2f7a13723679b0bf081ba11d4246cf2b8e87ea644d3bcecd958"
    ]
    transport_contract: Literal["GOVERNED_ROOT_EXACT_FLAT_V1"]
    exact_flat_file_count: Literal[3]
    live_authorization_issued: Literal[False]
    runtime_execution_authorized: Literal[False]
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    next_gate: str


def normalize_time(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC).replace(microsecond=0)


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(repo_root: Path, role: str, path: Path) -> ArtifactIdentity:
    full = repo_root / path
    if not full.is_file() or full.is_symlink():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_ARTIFACT_MISSING",
            "required authorization artifact is missing or unsafe",
            path.as_posix(),
        )
    return ArtifactIdentity(
        role=role,
        path=path.as_posix(),
        sha256=file_sha256(full),
        size_bytes=full.stat().st_size,
    )


def _validate_bound_implementation(repo_root: Path) -> tuple[ArtifactIdentity, ...]:
    observed: list[ArtifactIdentity] = []
    for role, path, expected_sha in BOUND_ARTIFACTS:
        identity = _artifact(repo_root, role, path)
        if identity.sha256 != expected_sha:
            raise AuthorizationIssuerError(
                "P5_P6_SUCCESSOR_AUTHORIZATION_BOUND_IDENTITY_DRIFT",
                "bound successor artifact identity drifted",
                path.as_posix(),
            )
        observed.append(identity)

    record_path = repo_root / IMPLEMENTATION_RECORD_PATH
    if not record_path.is_file() or record_path.is_symlink():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_IMPLEMENTATION_RECORD_MISSING",
            "successor implementation record is missing or unsafe",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_IMPLEMENTATION_RECORD_INVALID",
            "successor implementation record is invalid JSON",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        ) from error
    if not isinstance(record, dict):
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_IMPLEMENTATION_RECORD_INVALID",
            "successor implementation record root must be an object",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    expected = {
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "authorization_scope": AUTHORIZATION_SCOPE,
        "p5_requalified": False,
        "p6_requalified": False,
        "c4_semantic_qualified": False,
        "next_gate": (
            "DESIGN_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1_EXECUTION_AUTHORIZATION_ISSUER"
        ),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise AuthorizationIssuerError(
                "P5_P6_SUCCESSOR_AUTHORIZATION_IMPLEMENTATION_RECORD_DRIFT",
                f"successor implementation record semantic drift: {key}",
                IMPLEMENTATION_RECORD_PATH.as_posix(),
            )
    notebook = record.get("notebook")
    if not isinstance(notebook, dict):
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_IMPLEMENTATION_RECORD_DRIFT",
            "successor implementation notebook identity is missing",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    if notebook.get("runtime_script_sha256") != RUNTIME_SCRIPT_SHA256:
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_RUNTIME_IDENTITY_DRIFT",
            "successor runtime-script identity drifted",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    return tuple(observed)


def _git(repo_root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_GIT_FAILURE",
            "required git inspection failed",
            details=(process.stderr.strip(),),
        )
    return process.stdout.strip()


def _require_issue_repo_state(repo_root: Path, confirmed_commit: str) -> str:
    branch = _git(repo_root, "branch", "--show-current")
    if branch != "main":
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_NOT_MAIN",
            "live authorization may only be issued from main",
        )
    head = _git(repo_root, "rev-parse", "HEAD")
    origin_main = _git(repo_root, "rev-parse", "origin/main")
    if head != origin_main:
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "local main is not synchronized to origin/main",
        )
    if head != confirmed_commit:
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_CONFIRMATION_COMMIT_DRIFT",
            "operator confirmation does not bind current merged issuer main",
        )
    if _git(repo_root, "diff", "--name-only"):
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRACKED_WORKTREE_DIRTY",
            "tracked worktree must be clean before live authorization issuance",
        )
    if _git(repo_root, "diff", "--cached", "--name-only"):
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_INDEX_DIRTY",
            "index must be empty before live authorization issuance",
        )
    return head


def _require_transient_paths_untracked(repo_root: Path) -> None:
    for path in (AUTHORIZATION_PATH, TERMINAL_RECEIPT_PATH):
        process = subprocess.run(
            ["git", "ls-files", "--error-unmatch", path.as_posix()],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode == 0:
            raise AuthorizationIssuerError(
                "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSIENT_PATH_TRACKED",
                "transient authorization custody path must remain untracked",
                path.as_posix(),
            )


def _require_confirmation_fresh(
    confirmation: IssuanceConfirmation,
    now: datetime,
) -> None:
    current = normalize_time(now, "issuance time")
    if confirmation.confirmed_at > current + timedelta(minutes=1):
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_CONFIRMATION_IN_FUTURE",
            "operator confirmation timestamp is in the future",
        )
    if current - confirmation.confirmed_at > timedelta(
        minutes=MAXIMUM_OPERATOR_CONFIRMATION_AGE_MINUTES
    ):
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_CONFIRMATION_STALE",
            "operator confirmation is older than 15 minutes",
        )
    if confirmation.confirmed_at - confirmation.platform.observed_at > timedelta(
        minutes=MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES
    ):
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_PLATFORM_OBSERVATION_STALE",
            "platform observation is older than 15 minutes at confirmation",
        )


def _build_authorization(
    confirmation: IssuanceConfirmation,
    issuer_merge_commit: str,
    now: datetime,
) -> ExecutionAuthorization:
    issued_at = normalize_time(now, "issuance time")
    return ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        authorization_filename=AUTHORIZATION_FILENAME,
        decision="AUTHORIZED",
        lifecycle="ISSUED",
        scope=AUTHORIZATION_SCOPE,
        successor_merge_commit=SUCCESSOR_MERGE_COMMIT,
        issuer_merge_commit=issuer_merge_commit,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(minutes=confirmation.authorization_window_minutes),
        runtime_script_sha256=RUNTIME_SCRIPT_SHA256,
        implementation_review_sha256=IMPLEMENTATION_REVIEW_SHA256,
        design_record_sha256=DESIGN_RECORD_SHA256,
        mechanism_admission_contract_sha256=MECHANISM_CONTRACT_SHA256,
        implementation_addendum_sha256=IMPLEMENTATION_ADDENDUM_SHA256,
        runtime_execution_authorized=True,
        single_use=True,
        every_terminal_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        maximum_model_requests=6,
        maximum_worker_starts=3,
        maximum_model_loads=3,
        hidden_retries_permitted=0,
        authorization_reusable=False,
    )


def _write_non_overwriting(path: Path, payload: bytes) -> None:
    if path.exists():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_LIFECYCLE_ALREADY_STARTED",
            "authorization custody path already exists",
            path.as_posix(),
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def issue_authorization(
    repo_root: Path,
    *,
    confirmation: IssuanceConfirmation,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repo_root.resolve()
    observed_now = normalize_time(now or datetime.now(UTC), "issuance time")
    _require_confirmation_fresh(confirmation, observed_now)
    _validate_bound_implementation(root)
    _require_transient_paths_untracked(root)
    issuer_head = _require_issue_repo_state(root, confirmation.confirmed_issuer_merge_commit)
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_ALREADY_TERMINAL",
            "terminal authorization receipt already exists",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )
    authorization = _build_authorization(confirmation, issuer_head, observed_now)
    payload = authorization.canonical_bytes()
    _write_non_overwriting(root / AUTHORIZATION_PATH, payload)
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_AUTHORIZATION_ISSUED",
        "authorization_sha256": sha256_bytes(payload),
        "live_authorization_issued": True,
        "runtime_execution_authorized": True,
        "single_use": True,
        "next_gate": "MATERIALIZE_AND_EXECUTE_ONE_GOVERNED_SUCCESSOR_RUN",
    }


def _load_authorization(path: Path) -> ExecutionAuthorization:
    if not path.is_file() or path.is_symlink():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_MISSING",
            "live successor authorization is missing or unsafe",
            path.as_posix(),
        )
    raw = path.read_bytes()
    try:
        parsed = ExecutionAuthorization.model_validate_json(raw)
    except ValidationError as error:
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_INVALID",
            "live successor authorization is invalid",
            path.as_posix(),
        ) from error
    if raw != parsed.canonical_bytes():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_NON_CANONICAL",
            "live successor authorization is not canonical JSON",
            path.as_posix(),
        )
    return parsed


def validate_live_authorization(
    repo_root: Path,
    *,
    now: datetime | None = None,
) -> ExecutionAuthorization:
    root = repo_root.resolve()
    _validate_bound_implementation(root)
    _require_transient_paths_untracked(root)
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_ALREADY_TERMINAL",
            "successor authorization is already terminal",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )
    authorization = _load_authorization(root / AUTHORIZATION_PATH)
    current = normalize_time(now or datetime.now(UTC), "validation time")
    if current < authorization.issued_at or current >= authorization.expires_at:
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_OUTSIDE_VALID_WINDOW",
            "successor authorization is outside its valid time window",
        )
    _require_issue_repo_state(root, authorization.issuer_merge_commit)
    return authorization


def terminalize_authorization(
    repo_root: Path,
    *,
    disposition: TerminalDisposition,
    execution_outcome: ExecutionOutcome | None,
    saved_version_id: int | None = None,
    evidence_zip_sha256: str | None = None,
    terminal_log_sha256: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repo_root.resolve()
    _require_transient_paths_untracked(root)
    authorization_path = root / AUTHORIZATION_PATH
    terminal_path = root / TERMINAL_RECEIPT_PATH
    if terminal_path.exists():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_ALREADY_TERMINAL",
            "terminal successor authorization receipt already exists",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )
    authorization = _load_authorization(authorization_path)
    execution_attempted = disposition in {
        TerminalDisposition.CONSUMED,
        TerminalDisposition.OUTCOME_UNKNOWN,
    }
    receipt = AuthorizationTerminalReceipt(
        receipt_id=("auragateway-p5-p6-mechanism-admission-successor-v1-authorization-terminal"),
        authorization_id=AUTHORIZATION_ID,
        authorization_sha256=file_sha256(authorization_path),
        issuer_merge_commit=authorization.issuer_merge_commit,
        disposition=disposition,
        execution_attempted=execution_attempted,
        execution_outcome=execution_outcome,
        saved_version_id=saved_version_id,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
        terminalized_at=normalize_time(now or datetime.now(UTC), "terminalized_at"),
    )
    payload = receipt.canonical_bytes()
    _write_non_overwriting(terminal_path, payload)
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_AUTHORIZATION_TERMINAL",
        "disposition": receipt.disposition.value,
        "runtime_execution_authorized": False,
        "authorization_reusable": False,
        "terminal_receipt_sha256": sha256_bytes(payload),
    }


def _candidate_artifacts(repo_root: Path) -> tuple[ArtifactIdentity, ...]:
    roles = (
        "issuer_source",
        "transport_source",
        "issuer_tests",
        "transport_tests",
        "issuer_adr",
        "issuer_report",
        "issuer_runbook",
    )
    return tuple(
        _artifact(repo_root, role, path) for role, path in zip(roles, STATIC_PATHS, strict=True)
    )


def build_review(repo_root: Path) -> IssuerReview:
    return IssuerReview(
        review_id=(
            "auragateway-p5-p6-mechanism-admission-successor-"
            "execution-authorization-issuer-v1-review"
        ),
        status="APPROVED_FOR_MERGE_NOT_ISSUANCE",
        successor_merge_commit=SUCCESSOR_MERGE_COMMIT,
        authorization_scope=AUTHORIZATION_SCOPE,
        candidate_artifacts=_candidate_artifacts(repo_root),
        maximum_model_requests=6,
        maximum_worker_starts=3,
        maximum_model_loads=3,
        hidden_retries_permitted=0,
        human_confirmation_required=True,
        fresh_platform_observation_required=True,
        single_use_required=True,
        transport_contract="GOVERNED_ROOT_EXACT_FLAT_V1",
        exact_flat_file_count=3,
        live_authorization_issued=False,
        runtime_execution_authorized=False,
        model_requests_performed=0,
        gpu_execution_performed=False,
        kaggle_execution_performed=False,
        next_gate=NEXT_GATE,
    )


def generated_payloads(repo_root: Path) -> dict[Path, bytes]:
    review = build_review(repo_root)
    review_bytes = review.canonical_bytes()
    record = IssuerRecord(
        record_id=(
            "auragateway-p5-p6-mechanism-admission-successor-"
            "execution-authorization-issuer-v1-record"
        ),
        status="IMPLEMENTED_NOT_ISSUED",
        successor_merge_commit=SUCCESSOR_MERGE_COMMIT,
        review=ArtifactIdentity(
            role="issuer_review",
            path=REVIEW_PATH.as_posix(),
            sha256=sha256_bytes(review_bytes),
            size_bytes=len(review_bytes),
        ),
        authorization_scope=AUTHORIZATION_SCOPE,
        authorization_id=AUTHORIZATION_ID,
        runtime_script_sha256=RUNTIME_SCRIPT_SHA256,
        transport_contract="GOVERNED_ROOT_EXACT_FLAT_V1",
        exact_flat_file_count=3,
        live_authorization_issued=False,
        runtime_execution_authorized=False,
        model_requests_performed=0,
        gpu_execution_performed=False,
        kaggle_execution_performed=False,
        next_gate=NEXT_GATE,
    )
    return {REVIEW_PATH: review_bytes, RECORD_PATH: record.canonical_bytes()}


def write_generated(repo_root: Path) -> dict[str, object]:
    outputs = generated_payloads(repo_root)
    for path, payload in outputs.items():
        target = repo_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        if temporary.exists():
            raise AuthorizationIssuerError(
                "P5_P6_SUCCESSOR_AUTHORIZATION_TEMP_PATH_EXISTS",
                "temporary issuer-generation path already exists",
                path.as_posix(),
            )
        temporary.write_bytes(payload)
        temporary.replace(target)
    return {
        "status": "P5_P6_SUCCESSOR_AUTHORIZATION_ISSUER_GENERATED",
        "generated_path_count": len(outputs),
        "candidate_path_count": len(CANDIDATE_PATHS),
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def check_generated(repo_root: Path) -> dict[str, object]:
    _validate_bound_implementation(repo_root)
    outputs = generated_payloads(repo_root)
    for path, expected in outputs.items():
        target = repo_root / path
        if not target.is_file() or target.is_symlink() or target.read_bytes() != expected:
            raise AuthorizationIssuerError(
                "P5_P6_SUCCESSOR_AUTHORIZATION_GENERATED_DRIFT",
                "generated issuer artifact is non-canonical",
                path.as_posix(),
            )
    if (repo_root / AUTHORIZATION_PATH).exists():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_UNEXPECTED_LIVE_AUTHORITY",
            "live authorization exists during issuer implementation validation",
            AUTHORIZATION_PATH.as_posix(),
        )
    return {
        "status": "P5_P6_SUCCESSOR_AUTHORIZATION_ISSUER_VALID",
        "candidate_path_count": len(CANDIDATE_PATHS),
        "generated_path_count": len(outputs),
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _load_confirmation(path: Path) -> IssuanceConfirmation:
    try:
        confirmation = IssuanceConfirmation.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as error:
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_CONFIRMATION_INVALID",
            "operator confirmation file is invalid",
            path.as_posix(),
        ) from error
    if path.read_bytes() != confirmation.canonical_bytes():
        raise AuthorizationIssuerError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_CONFIRMATION_NON_CANONICAL",
            "operator confirmation must use canonical JSON bytes",
            path.as_posix(),
        )
    return confirmation


def _print_error(error: AuthorizationIssuerError) -> None:
    print(
        json.dumps(
            {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path,
                "details": error.details,
            },
            sort_keys=True,
        ),
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--write", action="store_true")
    actions.add_argument("--check", action="store_true")
    actions.add_argument("--issue-confirmation-json", type=Path)
    actions.add_argument("--validate-live", action="store_true")
    arguments = parser.parse_args(argv)
    repo_root = arguments.repo_root.resolve()
    try:
        if arguments.write:
            result = write_generated(repo_root)
        elif arguments.check:
            result = check_generated(repo_root)
        elif arguments.issue_confirmation_json is not None:
            confirmation = _load_confirmation(arguments.issue_confirmation_json)
            result = issue_authorization(repo_root, confirmation=confirmation)
        else:
            authorization = validate_live_authorization(repo_root)
            result = {
                "status": "P5_P6_SUCCESSOR_AUTHORIZATION_LIVE_VALID",
                "authorization_sha256": sha256_bytes(authorization.canonical_bytes()),
                "runtime_execution_authorized": True,
            }
    except AuthorizationIssuerError as error:
        _print_error(error)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
