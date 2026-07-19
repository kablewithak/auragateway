"""Issue and verify one bounded environment-qualification authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_contracts,
    full_abc_local_environment_qualification_execution_authorization_issuance_review,
    full_abc_local_environment_qualification_harness_rematerialization,
)
from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_environment_qualification_execution_contracts import (
    AUTHORIZATION_ISSUANCE_REVIEW_GIT_BLOB_SHA,
    AUTHORIZATION_PATH,
    EXECUTION_REQUEST_PATH,
    RUNTIME_EVIDENCE_PATHS,
    AuthorizationDecision,
    QualificationDatasetManifest,
    QualificationExecutionAuthorization,
    QualificationExecutionRequest,
    QualificationRuntimeFactoryBinding,
)

authorization_contracts = full_abc_local_environment_qualification_execution_authorization_contracts
issuance_review = full_abc_local_environment_qualification_execution_authorization_issuance_review
rematerialization = full_abc_local_environment_qualification_harness_rematerialization
MATERIALIZATION_RECORD_PATH = authorization_contracts.MATERIALIZATION_RECORD_PATH
MATERIALIZED_DATASET_MANIFEST_PATH = authorization_contracts.MATERIALIZED_DATASET_MANIFEST_PATH
RUNTIME_ADAPTER_PATH = authorization_contracts.RUNTIME_ADAPTER_PATH
REVIEW_PATH = issuance_review.REVIEW_PATH

SOURCE_MAIN_MERGE_COMMIT: Final = "be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"
REVIEW_SOURCE_MAIN_MERGE_COMMIT: Final = "211a10757999b1b110cb1d9df172938cf6ed7969"
AUTHORIZATION_ID: Final = (
    "auragateway-full-abc-local-environment-qualification-execution-authorization-v1"
)
AUTHORIZATION_ISSUANCE_REVIEW_SHA256: Final = (
    "73e9a4f0642cce40ce6bc6ef875ee13ab81900f0bc7e768e0c4a9a6b6f0ec859"
)
MATERIALIZATION_RECORD_SHA256: Final = (
    "8a0f41def6b3e4e8a34713e4cd9c3023d03619d51a62a2e7ec34da0bcc2f52c0"
)
RUNTIME_MANIFEST_SHA256: Final = "9ffd335fad6ac660782be7881625a1fb99a39f5d4a1446f31504154634c91eb7"
HARNESS_REMATERIALIZATION_RECORD_SHA256: Final = (
    "18a2055d26e83dd3d7ac1f67c680a7e1f6ff29841af5883a3e400444de51f218"
)
RUNTIME_ADAPTER_SHA256: Final = "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"
EXECUTION_REQUEST_SHA256: Final = "dcef7e7243f4de16955bccdfc36dbd0194b51a602d1fc67f5c6fa375ca529e28"
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
NEXT_GATE: Final = "full_abc_local_full_run_environment_qualification_execution"


class AuthorizationIssuanceError(RuntimeError):
    """Metadata-safe failure while issuing operational authority."""

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


class AuthorizationIssuanceErrorEnvelope(LocalABCContract):
    """Machine-readable issuance failure without sensitive values."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class AuthorizationIssuanceConfirmation(LocalABCContract):
    """Explicit local operator confirmation for one short authorization window."""

    confirmation_id: Literal[
        "auragateway-full-abc-local-environment-qualification-"
        "authorization-issuance-confirmation-v1"
    ]
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(
        ge=1,
        le=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
    )

    @field_validator("confirmed_at")
    @classmethod
    def validate_confirmed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("operator confirmation time must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def validate_confirmation(self) -> Self:
        if self.operator_confirmed is not True:
            raise ValueError("explicit operator confirmation is required")
        return self


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_ARGUMENT_INVALID",
            "authorization issuance arguments are invalid",
            details=(message,),
        )


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_FILE_UNREADABLE",
            "an authorization-bound file could not be read",
            path.as_posix(),
        ) from exc


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_INPUT_UNREADABLE",
            "an authorization issuance input could not be read",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_INPUT_INVALID",
            "an authorization issuance input must be a JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _run_git(
    repo_root: Path,
    arguments: list[str],
    *,
    error_code: str,
    safe_message: str,
) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationIssuanceError(error_code, safe_message) from exc
    if result.returncode != 0:
        raise AuthorizationIssuanceError(error_code, safe_message)
    return result.stdout.strip()


def _require_clean_main(repo_root: Path) -> None:
    branch = _run_git(
        repo_root,
        ["branch", "--show-current"],
        error_code="AUTHORIZATION_ISSUANCE_BRANCH_UNREADABLE",
        safe_message="the current Git branch could not be resolved",
    )
    if branch != "main":
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REQUIRES_MAIN",
            "authorization may be issued only from the synchronized main branch",
            details=(branch,),
        )
    status = _run_git(
        repo_root,
        ["status", "--porcelain"],
        error_code="AUTHORIZATION_ISSUANCE_STATUS_UNREADABLE",
        safe_message="the current Git working-tree state could not be resolved",
    )
    if status:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REQUIRES_CLEAN_TREE",
            "authorization may be issued only from a clean working tree",
        )


def _require_source_authority(repo_root: Path) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                SOURCE_MAIN_MERGE_COMMIT,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_ANCESTRY_UNREADABLE",
            "the PR 112 source ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_SOURCE_MISSING",
            "PR 112 must be an ancestor before authorization issuance",
            details=(SOURCE_MAIN_MERGE_COMMIT,),
        )
    observed_blob = _run_git(
        repo_root,
        [
            "rev-parse",
            f"{REVIEW_SOURCE_MAIN_MERGE_COMMIT}:{REVIEW_PATH.as_posix()}",
        ],
        error_code="AUTHORIZATION_ISSUANCE_REVIEW_BLOB_UNREADABLE",
        safe_message="the merged authorization-issuance review could not be resolved",
    )
    if observed_blob != AUTHORIZATION_ISSUANCE_REVIEW_GIT_BLOB_SHA:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REVIEW_BLOB_DRIFT",
            "the merged authorization-issuance review identity drifted",
            REVIEW_PATH.as_posix(),
            details=(observed_blob,),
        )


def _load_operational_inputs(
    repo_root: Path,
) -> tuple[
    QualificationExecutionRequest,
    QualificationDatasetManifest,
]:
    try:
        request = QualificationExecutionRequest.model_validate(
            _load_json_object(repo_root / EXECUTION_REQUEST_PATH)
        )
        manifest = QualificationDatasetManifest.model_validate(
            _load_json_object(repo_root / MATERIALIZED_DATASET_MANIFEST_PATH)
        )
    except ValidationError as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_INPUT_INVALID",
            "execution request or runtime manifest failed typed validation",
        ) from exc
    return request, manifest


def _validate_no_runtime_activity(repo_root: Path) -> None:
    present = tuple(
        path.as_posix() for path in RUNTIME_EVIDENCE_PATHS if (repo_root / path).exists()
    )
    if present:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_RUNTIME_EVIDENCE_PRESENT",
            "runtime evidence exists before the bounded authorization is issued",
            details=present,
        )


def _validate_rematerialization_package(
    repo_root: Path,
) -> dict[str, object]:
    try:
        summary = rematerialization.validate_repository_package(repo_root)
        record = rematerialization.load_record(repo_root / rematerialization.RECORD_PATH)
    except rematerialization.HarnessRematerializationError as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REMATERIALIZATION_INVALID",
            "the parity-approved harness rematerialization did not validate",
            exc.path,
            details=exc.details,
        ) from exc
    if record.fingerprint() != HARNESS_REMATERIALIZATION_RECORD_SHA256:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REMATERIALIZATION_DRIFT",
            "the harness rematerialization content identity drifted",
            rematerialization.RECORD_PATH.as_posix(),
        )
    return summary


def _build_authorization(
    *,
    repo_root: Path,
    confirmation: AuthorizationIssuanceConfirmation,
) -> QualificationExecutionAuthorization:
    _require_source_authority(repo_root)
    _validate_no_runtime_activity(repo_root)
    rematerialization_summary = _validate_rematerialization_package(repo_root)
    review = issuance_review.load_review(repo_root / REVIEW_PATH)
    request, manifest = _load_operational_inputs(repo_root)
    if review.fingerprint() != AUTHORIZATION_ISSUANCE_REVIEW_SHA256:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REVIEW_CONTENT_DRIFT",
            "the authorization-issuance review content identity drifted",
            REVIEW_PATH.as_posix(),
        )
    if request.fingerprint() != EXECUTION_REQUEST_SHA256:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REQUEST_DRIFT",
            "the execution request identity drifted",
            EXECUTION_REQUEST_PATH.as_posix(),
        )
    if manifest.fingerprint() != RUNTIME_MANIFEST_SHA256:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_MANIFEST_DRIFT",
            "the runtime manifest identity drifted",
            MATERIALIZED_DATASET_MANIFEST_PATH.as_posix(),
        )
    materialization_path = repo_root / MATERIALIZATION_RECORD_PATH
    if not materialization_path.is_file():
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_MATERIALIZATION_MISSING",
            "the materialization record is missing",
            MATERIALIZATION_RECORD_PATH.as_posix(),
        )
    if rematerialization_summary["materialization_record_sha256"] != (
        MATERIALIZATION_RECORD_SHA256
    ):
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_MATERIALIZATION_DRIFT",
            "the parity-approved rematerialization record no longer binds "
            "the exact materialization record",
        )
    if review.runtime_factory.artifact_sha256 != RUNTIME_ADAPTER_SHA256:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_ADAPTER_DRIFT",
            "the review no longer binds the exact runtime adapter",
        )

    issued_at = confirmation.confirmed_at
    expires_at = issued_at + timedelta(minutes=confirmation.authorization_window_minutes)
    return QualificationExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision=AuthorizationDecision.AUTHORIZED,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        request_sha256=request.fingerprint(),
        review_git_blob_sha=AUTHORIZATION_ISSUANCE_REVIEW_GIT_BLOB_SHA,
        authorization_issuance_review_sha256=review.fingerprint(),
        materialization_record_sha256=MATERIALIZATION_RECORD_SHA256,
        dataset_manifest_sha256=manifest.fingerprint(),
        runtime_factory=QualificationRuntimeFactoryBinding(
            factory_path=review.runtime_factory.factory_path,
            artifact_path=review.runtime_factory.artifact_path,
            artifact_sha256=review.runtime_factory.artifact_sha256,
        ),
        issued_at=issued_at,
        expires_at=expires_at,
        maximum_workers=review.budget.maximum_workers,
        maximum_kaggle_sessions=review.budget.maximum_kaggle_sessions,
        maximum_model_requests=review.budget.maximum_model_requests,
        maximum_output_tokens_per_request=(review.budget.maximum_output_tokens_per_request),
        benchmark_trajectory_requests_permitted=(
            review.budget.benchmark_trajectory_requests_permitted
        ),
        customer_data_permitted=review.privacy.customer_data_permitted,
        credentials_permitted=review.privacy.credentials_permitted,
        network_access_permitted=review.privacy.network_access_permitted,
        external_spend=review.budget.external_spend,
        operator_confirmation_recorded=True,
        measured_execution_authorized=False,
    )


def _write_authorization(
    path: Path,
    authorization: QualificationExecutionAuthorization,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ALREADY_EXISTS",
            "the final authorization already exists and will not be overwritten",
            path.as_posix(),
        )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(authorization.canonical_json())
            handle.flush()
            temporary_path = Path(handle.name)
        if path.exists():
            raise AuthorizationIssuanceError(
                "AUTHORIZATION_ALREADY_EXISTS",
                "the final authorization appeared during issuance",
                path.as_posix(),
            )
        temporary_path.replace(path)
    except AuthorizationIssuanceError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_COMMIT_FAILED",
            "the final authorization could not be committed atomically",
            path.as_posix(),
        ) from exc


def issue_authorization(
    *,
    repo_root: Path,
    confirmation: AuthorizationIssuanceConfirmation,
) -> dict[str, object]:
    """Issue one non-overwriting authorization after explicit confirmation."""

    repo_root = repo_root.resolve()
    _require_clean_main(repo_root)
    target = repo_root / AUTHORIZATION_PATH
    if target.exists():
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ALREADY_EXISTS",
            "the final authorization already exists and will not be overwritten",
            AUTHORIZATION_PATH.as_posix(),
        )
    authorization = _build_authorization(
        repo_root=repo_root,
        confirmation=confirmation,
    )
    _write_authorization(target, authorization)
    return {
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": authorization.fingerprint(),
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "source_main_merge_commit": authorization.source_main_merge_commit,
        "review_git_blob_sha": authorization.review_git_blob_sha,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "maximum_authorization_window_minutes": (confirmation.authorization_window_minutes),
        "maximum_workers": authorization.maximum_workers,
        "maximum_kaggle_sessions": authorization.maximum_kaggle_sessions,
        "maximum_model_requests": authorization.maximum_model_requests,
        "maximum_output_tokens_per_request": (authorization.maximum_output_tokens_per_request),
        "benchmark_trajectory_requests_permitted": (
            authorization.benchmark_trajectory_requests_permitted
        ),
        "network_access_permitted": authorization.network_access_permitted,
        "customer_data_permitted": authorization.customer_data_permitted,
        "credentials_permitted": authorization.credentials_permitted,
        "external_spend": authorization.external_spend,
        "operator_confirmation_recorded": (authorization.operator_confirmation_recorded),
        "kaggle_session_started": False,
        "worker_started": False,
        "model_request_count": 0,
        "measured_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _load_authorization(path: Path) -> QualificationExecutionAuthorization:
    try:
        return QualificationExecutionAuthorization.model_validate(_load_json_object(path))
    except ValidationError as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_INVALID",
            "the final authorization failed typed validation",
            path.as_posix(),
        ) from exc


def verify_authorization(
    *,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify exact authority bindings and the live authorization window."""

    repo_root = repo_root.resolve()
    _require_source_authority(repo_root)
    _validate_no_runtime_activity(repo_root)
    _validate_rematerialization_package(repo_root)
    authorization_path = repo_root / AUTHORIZATION_PATH
    authorization = _load_authorization(authorization_path)
    try:
        authorization_text = authorization_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_UNREADABLE",
            "the final authorization could not be read",
            AUTHORIZATION_PATH.as_posix(),
        ) from exc
    if authorization_text != authorization.canonical_json():
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_NOT_CANONICAL",
            "the final authorization is not canonical JSON",
            AUTHORIZATION_PATH.as_posix(),
        )
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    window = authorization.expires_at - authorization.issued_at
    if window > timedelta(minutes=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES):
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_WINDOW_EXCEEDS_REVIEW",
            "the final authorization exceeds the reviewed time budget",
            AUTHORIZATION_PATH.as_posix(),
        )
    if not authorization.issued_at <= observed_now < authorization.expires_at:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_EXPIRED",
            "the final authorization is outside its validity window",
            AUTHORIZATION_PATH.as_posix(),
        )
    review = issuance_review.load_review(repo_root / REVIEW_PATH)
    request, manifest = _load_operational_inputs(repo_root)
    materialization_path = repo_root / MATERIALIZATION_RECORD_PATH
    adapter_path = repo_root / RUNTIME_ADAPTER_PATH
    checks = (
        authorization.authorization_id == AUTHORIZATION_ID,
        authorization.source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT,
        authorization.request_sha256 == request.fingerprint(),
        authorization.review_git_blob_sha == AUTHORIZATION_ISSUANCE_REVIEW_GIT_BLOB_SHA,
        authorization.authorization_issuance_review_sha256 == AUTHORIZATION_ISSUANCE_REVIEW_SHA256,
        review.fingerprint() == AUTHORIZATION_ISSUANCE_REVIEW_SHA256,
        authorization.materialization_record_sha256 == MATERIALIZATION_RECORD_SHA256,
        _file_sha256(materialization_path) == MATERIALIZATION_RECORD_SHA256,
        authorization.dataset_manifest_sha256 == manifest.fingerprint(),
        authorization.runtime_factory.factory_path == review.runtime_factory.factory_path,
        authorization.runtime_factory.artifact_path == review.runtime_factory.artifact_path,
        authorization.runtime_factory.artifact_sha256 == review.runtime_factory.artifact_sha256,
        _file_sha256(adapter_path) == RUNTIME_ADAPTER_SHA256,
        authorization.maximum_workers == review.budget.maximum_workers,
        authorization.maximum_kaggle_sessions == review.budget.maximum_kaggle_sessions,
        authorization.maximum_model_requests == review.budget.maximum_model_requests,
        authorization.maximum_output_tokens_per_request
        == review.budget.maximum_output_tokens_per_request,
        authorization.benchmark_trajectory_requests_permitted == 0,
        authorization.network_access_permitted is False,
        authorization.customer_data_permitted is False,
        authorization.credentials_permitted is False,
        authorization.external_spend == 0,
        authorization.operator_confirmation_recorded is True,
        authorization.measured_execution_authorized is False,
    )
    if not all(checks):
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_BINDING_DRIFT",
            "the final authorization no longer binds the reviewed inputs",
            AUTHORIZATION_PATH.as_posix(),
        )
    if not adapter_path.is_file():
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_RUNTIME_ADAPTER_MISSING",
            "the authorized runtime adapter is missing",
            RUNTIME_ADAPTER_PATH.as_posix(),
        )
    return {
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": authorization.fingerprint(),
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_valid": True,
        "source_main_merge_commit": authorization.source_main_merge_commit,
        "review_git_blob_sha": authorization.review_git_blob_sha,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "maximum_workers": authorization.maximum_workers,
        "maximum_kaggle_sessions": authorization.maximum_kaggle_sessions,
        "maximum_model_requests": authorization.maximum_model_requests,
        "maximum_output_tokens_per_request": (authorization.maximum_output_tokens_per_request),
        "benchmark_trajectory_requests_permitted": 0,
        "network_access_permitted": False,
        "customer_data_permitted": False,
        "credentials_permitted": False,
        "external_spend": 0,
        "kaggle_session_started": False,
        "runtime_evidence_generated": False,
        "measured_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-environment-qualification-authorization-issuance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    issue_parser = subparsers.add_parser("issue")
    issue_parser.add_argument("--repo-root", type=Path, required=True)
    issue_parser.add_argument(
        "--operator-confirm",
        action="store_true",
        help="confirm immediate issuance of one bounded authorization",
    )
    issue_parser.add_argument(
        "--window-minutes",
        type=int,
        default=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
    )
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def _error_envelope(error: AuthorizationIssuanceError) -> str:
    return AuthorizationIssuanceErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).canonical_json()


def main(argv: list[str] | None = None) -> int:
    """Issue or verify one bounded authorization without runtime execution."""

    try:
        arguments = _build_parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "issue":
            if arguments.operator_confirm is not True:
                raise AuthorizationIssuanceError(
                    "OPERATOR_CONFIRMATION_REQUIRED",
                    "explicit --operator-confirm is required for issuance",
                )
            confirmation = AuthorizationIssuanceConfirmation(
                confirmation_id=(
                    "auragateway-full-abc-local-environment-qualification-"
                    "authorization-issuance-confirmation-v1"
                ),
                operator_confirmed=True,
                confirmed_at=datetime.now(UTC).replace(microsecond=0),
                authorization_window_minutes=cast(int, arguments.window_minutes),
            )
            summary = issue_authorization(
                repo_root=repo_root,
                confirmation=confirmation,
            )
        else:
            summary = verify_authorization(repo_root=repo_root)
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
        return 0
    except AuthorizationIssuanceError as error:
        print(_error_envelope(error), file=sys.stderr)
        return 2
    except (OSError, ValidationError, ValueError) as error:
        envelope = AuthorizationIssuanceErrorEnvelope(
            error_code="UNEXPECTED_AUTHORIZATION_ISSUANCE_FAILURE",
            safe_message="authorization issuance failed at a typed boundary",
            details=(type(error).__name__,),
        )
        print(envelope.canonical_json(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
