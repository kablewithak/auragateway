"""Single-use authorization lifecycle for variance-pilot execution V1."""

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
from typing import Final, Literal, Never, Self, TypeVar

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.measured_abc_variance_pilot_v1 import (
    MAXIMUM_REQUEST_ATTEMPTS,
    PILOT_MANIFEST_PATH,
    PILOT_SCHEDULE_PATH,
    PilotManifest,
    PilotSchedule,
)

AUTHORIZATION_ID: Final = "auragateway-measured-abc-variance-pilot-execution-authorization-v1"
AUTHORIZATION_SCOPE: Final = "MEASURED_ABC_VARIANCE_PILOT_V1"
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_execution_authorization_v1.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_execution_authorization_consumption_v1.json"
)
ABANDONMENT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_execution_authorization_abandonment_v1.json"
)
RUNTIME_LAUNCHER_READINESS_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_runtime_launcher_readiness_v1.json"
)

MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"

MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES: Final = 15
MAXIMUM_CONFIRMATION_AGE_MINUTES: Final = 15
_ModelT = TypeVar("_ModelT", bound=LocalABCContract)


class PilotAuthorizationError(RuntimeError):
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
    OTHER = "OTHER"


class RuntimeBinding(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    platform: Literal["Kaggle"] = "Kaggle"
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


class PilotBudget(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    maximum_kaggle_sessions: Literal[1] = 1
    pilot_trajectory_count: Literal[54] = 54
    pilot_turn_count: Literal[216] = 216
    maximum_request_attempts: Literal[432] = MAXIMUM_REQUEST_ATTEMPTS
    maximum_retries_after_initial_attempt: Literal[1] = 1
    maximum_hidden_retries: Literal[0] = 0
    maximum_saved_versions: Literal[1] = 1
    maximum_external_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0
    replacement_cases_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False


class CommittedArtifact(LocalABCContract):
    repository_path: str
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class RuntimeLauncherReadiness(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    readiness_id: Literal[
        "auragateway-measured-abc-variance-pilot-runtime-launcher-readiness-v1"
    ] = "auragateway-measured-abc-variance-pilot-runtime-launcher-readiness-v1"
    status: Literal["READY_FOR_VARIANCE_PILOT_AUTHORIZATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    pilot_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    launcher_source: CommittedArtifact
    launcher_notebook: CommittedArtifact
    runtime_request: CommittedArtifact
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["observe_platform_and_issue_variance_pilot_authorization_v1"]


class PlatformCapabilityObservation(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    observed_at: datetime
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"]
    accelerator: Literal["GPU_T4_X2"]
    allocated_gpu_count: Literal[2]
    internet_enabled: Literal[False]
    wheelhouse_input_count: Literal[1]
    model_snapshot_input_count: Literal[1]

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class IssuanceConfirmation(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    confirmed_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_window_minutes: int = Field(
        ge=1,
        le=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
    )
    pilot_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_launcher_readiness_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    single_use_acknowledged: Literal[True]
    terminal_consumption_required_acknowledged: Literal[True]
    final_measured_authorization_is_separate_acknowledged: Literal[True]
    runtime: RuntimeBinding
    budget: PilotBudget
    platform_observation: PlatformCapabilityObservation

    @field_validator("confirmed_at")
    @classmethod
    def validate_confirmed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("confirmed_at must be timezone-aware")
        return value


class PilotExecutionAuthorization(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal[
        "auragateway-measured-abc-variance-pilot-execution-authorization-v1"
    ] = AUTHORIZATION_ID
    scope: Literal["MEASURED_ABC_VARIANCE_PILOT_V1"] = AUTHORIZATION_SCOPE
    lifecycle: Literal[AuthorizationLifecycle.ISSUED] = AuthorizationLifecycle.ISSUED
    issued_at: datetime
    expires_at: datetime
    issued_from_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_launcher_readiness_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime: RuntimeBinding
    budget: PilotBudget
    single_use: Literal[True] = True
    authorization_reusable: Literal[True] = True
    pilot_execution_authorized: Literal[True] = True
    final_measured_abc_execution_authorized: Literal[False] = False
    terminal_consumption_required: Literal[True] = True
    next_gate: Literal["execute_variance_pilot_once"] = "execute_variance_pilot_once"

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        return self


class AuthorizationConsumption(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal[
        "auragateway-measured-abc-variance-pilot-execution-authorization-v1"
    ] = AUTHORIZATION_ID
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.CONSUMED] = AuthorizationLifecycle.CONSUMED
    outcome: ExecutionOutcome
    consumed_at: datetime
    saved_version_id: int | None = Field(default=None, gt=0)
    evidence_bundle_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    terminal_log_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    authorization_reusable: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal["preserve_and_accept_or_classify_variance_pilot_v1"] = (
        "preserve_and_accept_or_classify_variance_pilot_v1"
    )

    @model_validator(mode="after")
    def validate_pass_evidence(self) -> Self:
        if self.outcome is ExecutionOutcome.PASSED:
            if self.saved_version_id is None:
                raise ValueError("PASSED consumption requires saved_version_id")
            if self.evidence_bundle_sha256 is None or self.terminal_log_sha256 is None:
                raise ValueError("PASSED consumption requires evidence and log hashes")
        return self


class AuthorizationAbandonment(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal[
        "auragateway-measured-abc-variance-pilot-execution-authorization-v1"
    ] = AUTHORIZATION_ID
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.ABANDONED] = AuthorizationLifecycle.ABANDONED
    reason: AbandonmentReason
    abandoned_at: datetime
    authorization_reusable: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal["reconcile_then_issue_fresh_variance_pilot_authorization_v1"] = (
        "reconcile_then_issue_fresh_variance_pilot_authorization_v1"
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


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _error(
    code: str,
    message: str,
    path: Path | None = None,
    details: tuple[str, ...] = (),
) -> Never:
    raise PilotAuthorizationError(
        code,
        message,
        path.as_posix() if path is not None else None,
        details,
    )


def _load_model(model: type[_ModelT], path: Path) -> _ModelT:
    try:
        return model.model_validate_json(path.read_bytes())
    except FileNotFoundError:
        _error(
            "VARIANCE_PILOT_AUTH_ARTIFACT_MISSING",
            "Authorization artifact is missing",
            path,
        )
    except ValidationError as exc:
        _error(
            "VARIANCE_PILOT_AUTH_SCHEMA_INVALID",
            "Authorization artifact failed typed validation",
            path,
            tuple(item["msg"] for item in exc.errors(include_url=False, include_input=False)),
        )


def _run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if completed.returncode != 0:
        _error(
            "VARIANCE_PILOT_AUTH_GIT_FAILED",
            "Required Git operation failed",
            details=(" ".join(args), completed.stderr.strip()),
        )
    return completed.stdout


def _load_runtime_launcher_readiness(
    repo_root: Path,
) -> tuple[RuntimeLauncherReadiness, str]:
    probe = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "cat-file",
            "-e",
            f"HEAD:{RUNTIME_LAUNCHER_READINESS_PATH.as_posix()}",
        ],
        check=False,
        capture_output=True,
        timeout=20,
    )
    if probe.returncode != 0:
        _error(
            "VARIANCE_PILOT_AUTH_RUNTIME_LAUNCHER_NOT_READY",
            "Committed variance-pilot runtime-launcher readiness is missing",
            RUNTIME_LAUNCHER_READINESS_PATH,
        )

    readiness = _load_model(
        RuntimeLauncherReadiness,
        repo_root / RUNTIME_LAUNCHER_READINESS_PATH,
    )
    ancestry = subprocess.run(
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
    if ancestry.returncode != 0:
        _error(
            "VARIANCE_PILOT_AUTH_RUNTIME_LAUNCHER_ANCESTRY_INVALID",
            "Runtime-launcher readiness source main is not an ancestor of HEAD",
            RUNTIME_LAUNCHER_READINESS_PATH,
        )

    for artifact in (
        readiness.launcher_source,
        readiness.launcher_notebook,
        readiness.runtime_request,
    ):
        observed = _run_git(
            repo_root,
            "rev-parse",
            f"HEAD:{artifact.repository_path}",
        ).strip()
        if observed != artifact.git_blob_sha:
            _error(
                "VARIANCE_PILOT_AUTH_RUNTIME_LAUNCHER_RECEIPT_DRIFT",
                "Runtime-launcher readiness artifact identity drifted",
                Path(artifact.repository_path),
                (f"expected={artifact.git_blob_sha}", f"observed={observed}"),
            )

    return readiness, _sha256_file(repo_root / RUNTIME_LAUNCHER_READINESS_PATH)


def _require_clean_main(repo_root: Path) -> str:
    branch = _run_git(repo_root, "branch", "--show-current").strip()
    if branch != "main":
        _error(
            "VARIANCE_PILOT_AUTH_BRANCH_INVALID",
            "Pilot issuance requires branch main",
        )
    head = _run_git(repo_root, "rev-parse", "HEAD").strip()
    origin = _run_git(repo_root, "rev-parse", "origin/main").strip()
    if head != origin:
        _error(
            "VARIANCE_PILOT_AUTH_MAIN_NOT_SYNCHRONIZED",
            "Pilot issuance requires main to match origin/main",
        )
    status = _run_git(
        repo_root,
        "status",
        "--short",
        "--untracked-files=all",
    ).splitlines()
    if status:
        _error(
            "VARIANCE_PILOT_AUTH_WORKTREE_NOT_CLEAN",
            "Pilot issuance requires a clean working tree",
            details=tuple(status),
        )
    return head


def _require_active_worktree(repo_root: Path, issued_from_main_commit: str) -> None:
    branch = _run_git(repo_root, "branch", "--show-current").strip()
    head = _run_git(repo_root, "rev-parse", "HEAD").strip()
    origin = _run_git(repo_root, "rev-parse", "origin/main").strip()
    if branch != "main" or head != origin or head != issued_from_main_commit:
        _error(
            "VARIANCE_PILOT_AUTH_REPOSITORY_DRIFT",
            "Repository identity drifted after pilot authorization issuance",
        )
    status = _run_git(
        repo_root,
        "status",
        "--short",
        "--untracked-files=all",
    ).splitlines()
    expected = [f"?? {AUTHORIZATION_PATH.as_posix()}"]
    if status != expected:
        _error(
            "VARIANCE_PILOT_AUTH_WORKTREE_DRIFT",
            "Active pilot authorization requires exactly one untracked authorization artifact",
            details=tuple(status),
        )


def _write_new(path: Path, model: LocalABCContract) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _error(
            "VARIANCE_PILOT_AUTH_NON_OVERWRITE",
            "Pilot authorization lifecycle artifact already exists",
            path,
        )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical(model.model_dump(mode="json")))
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _fresh(confirmation: IssuanceConfirmation, now: datetime) -> None:
    observation_age = now - confirmation.platform_observation.observed_at
    confirmation_age = now - confirmation.confirmed_at
    if observation_age < timedelta(0) or observation_age > timedelta(
        minutes=MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES
    ):
        _error(
            "VARIANCE_PILOT_AUTH_PLATFORM_OBSERVATION_STALE",
            "Pilot platform observation is stale or future-dated",
        )
    if confirmation_age < timedelta(0) or confirmation_age > timedelta(
        minutes=MAXIMUM_CONFIRMATION_AGE_MINUTES
    ):
        _error(
            "VARIANCE_PILOT_AUTH_CONFIRMATION_STALE",
            "Pilot operator confirmation is stale or future-dated",
        )


def issue_authorization(
    repo_root: Path,
    confirmation: IssuanceConfirmation,
    confirmation_sha256: str,
    now: datetime | None = None,
) -> dict[str, object]:
    head = _require_clean_main(repo_root)
    manifest = _load_model(PilotManifest, repo_root / PILOT_MANIFEST_PATH)
    schedule = _load_model(PilotSchedule, repo_root / PILOT_SCHEDULE_PATH)
    manifest_sha = _sha256_file(repo_root / PILOT_MANIFEST_PATH)
    schedule_sha = _sha256_file(repo_root / PILOT_SCHEDULE_PATH)
    launcher_readiness, launcher_readiness_sha = _load_runtime_launcher_readiness(repo_root)
    current = datetime.now(UTC) if now is None else now
    _fresh(confirmation, current)

    if confirmation.confirmed_issuer_merge_commit != head:
        _error(
            "VARIANCE_PILOT_AUTH_ISSUER_IDENTITY_MISMATCH",
            "Pilot confirmation does not bind synchronized main",
        )
    if confirmation.pilot_manifest_sha256 != manifest_sha:
        _error(
            "VARIANCE_PILOT_AUTH_MANIFEST_IDENTITY_MISMATCH",
            "Pilot confirmation does not bind pilot manifest",
        )
    if confirmation.pilot_schedule_sha256 != schedule_sha:
        _error(
            "VARIANCE_PILOT_AUTH_SCHEDULE_IDENTITY_MISMATCH",
            "Pilot confirmation does not bind pilot schedule",
        )
    if confirmation.runtime_launcher_readiness_sha256 != launcher_readiness_sha:
        _error(
            "VARIANCE_PILOT_AUTH_RUNTIME_LAUNCHER_IDENTITY_MISMATCH",
            "Pilot confirmation does not bind runtime-launcher readiness",
        )
    if launcher_readiness.pilot_manifest_sha256 != manifest_sha:
        _error(
            "VARIANCE_PILOT_AUTH_RUNTIME_LAUNCHER_MANIFEST_MISMATCH",
            "Runtime-launcher readiness does not bind pilot manifest",
        )
    if launcher_readiness.pilot_schedule_sha256 != schedule_sha:
        _error(
            "VARIANCE_PILOT_AUTH_RUNTIME_LAUNCHER_SCHEDULE_MISMATCH",
            "Runtime-launcher readiness does not bind pilot schedule",
        )
    expected_schedule_sha = hashlib.sha256(
        _canonical(schedule.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()
    if manifest.pilot_schedule_sha256 != expected_schedule_sha:
        _error(
            "VARIANCE_PILOT_AUTH_MANIFEST_SCHEDULE_MISMATCH",
            "Pilot manifest does not bind pilot schedule",
        )
    if confirmation.runtime != RuntimeBinding():
        _error(
            "VARIANCE_PILOT_AUTH_RUNTIME_MISMATCH",
            "Pilot confirmation runtime differs from frozen runtime",
        )
    if confirmation.budget != PilotBudget():
        _error(
            "VARIANCE_PILOT_AUTH_BUDGET_MISMATCH",
            "Pilot confirmation budget differs from frozen pilot budget",
        )
    if any(
        (repo_root / path).exists()
        for path in (AUTHORIZATION_PATH, CONSUMPTION_PATH, ABANDONMENT_PATH)
    ):
        _error(
            "VARIANCE_PILOT_AUTH_LIFECYCLE_EXISTS",
            "Pilot authorization lifecycle already exists",
        )

    authorization = PilotExecutionAuthorization(
        issued_at=current,
        expires_at=current + timedelta(minutes=confirmation.authorization_window_minutes),
        issued_from_main_commit=head,
        confirmation_sha256=confirmation_sha256,
        runtime_launcher_readiness_sha256=launcher_readiness_sha,
        pilot_manifest_sha256=manifest_sha,
        pilot_schedule_sha256=schedule_sha,
        runtime=RuntimeBinding(),
        budget=PilotBudget(),
    )
    _write_new(repo_root / AUTHORIZATION_PATH, authorization)
    return {
        "status": "MEASURED_ABC_VARIANCE_PILOT_AUTHORIZATION_V1_ISSUED",
        "authorization_sha256": _sha256_file(repo_root / AUTHORIZATION_PATH),
        "pilot_execution_authorized": True,
        "final_measured_abc_execution_authorized": False,
        "single_use": True,
        "next_gate": "verify_then_execute_variance_pilot_once",
    }


def _load_authorization(repo_root: Path) -> PilotExecutionAuthorization:
    return _load_model(PilotExecutionAuthorization, repo_root / AUTHORIZATION_PATH)


def verify_authorization(
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    authorization = _load_authorization(repo_root)
    _require_active_worktree(repo_root, authorization.issued_from_main_commit)
    current = datetime.now(UTC) if now is None else now
    if current > authorization.expires_at:
        _error(
            "VARIANCE_PILOT_AUTH_EXPIRED",
            "Pilot execution authorization expired",
            AUTHORIZATION_PATH,
        )
    if (repo_root / CONSUMPTION_PATH).exists() or (repo_root / ABANDONMENT_PATH).exists():
        _error(
            "VARIANCE_PILOT_AUTH_TERMINAL",
            "Pilot authorization is already terminal",
        )
    if _sha256_file(repo_root / PILOT_MANIFEST_PATH) != authorization.pilot_manifest_sha256:
        _error("VARIANCE_PILOT_AUTH_MANIFEST_DRIFT", "Pilot manifest drifted")
    if _sha256_file(repo_root / PILOT_SCHEDULE_PATH) != authorization.pilot_schedule_sha256:
        _error("VARIANCE_PILOT_AUTH_SCHEDULE_DRIFT", "Pilot schedule drifted")
    return {
        "status": "MEASURED_ABC_VARIANCE_PILOT_AUTHORIZATION_V1_VERIFIED",
        "authorization_reusable": True,
        "pilot_execution_authorized": True,
        "final_measured_abc_execution_authorized": False,
        "next_gate": "execute_variance_pilot_once",
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
            "VARIANCE_PILOT_AUTH_TERMINAL",
            "Pilot authorization is already terminal",
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
        "status": "MEASURED_ABC_VARIANCE_PILOT_AUTHORIZATION_V1_CONSUMED",
        "outcome": outcome.value,
        "authorization_reusable": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": "preserve_and_accept_or_classify_variance_pilot_v1",
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
            "VARIANCE_PILOT_AUTH_TERMINAL",
            "Pilot authorization is already terminal",
        )
    current = datetime.now(UTC) if now is None else now
    abandonment = AuthorizationAbandonment(
        authorization_sha256=_sha256_file(repo_root / AUTHORIZATION_PATH),
        reason=reason,
        abandoned_at=current,
    )
    _write_new(repo_root / ABANDONMENT_PATH, abandonment)
    return {
        "status": "MEASURED_ABC_VARIANCE_PILOT_AUTHORIZATION_V1_ABANDONED",
        "authorization_reusable": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": "reconcile_then_issue_fresh_variance_pilot_authorization_v1",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="measured-abc-variance-pilot-execution-authorization-v1")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, required=True)
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
        if args.command == "verify":
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
                repo_root,
                AbandonmentReason(args.reason),
            )
        print(_canonical(result), end="")
        return 0
    except PilotAuthorizationError as exc:
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
