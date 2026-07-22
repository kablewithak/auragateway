"""Issue and verify one bounded current CUDA 12.9 qualification authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Literal, Never, Self, TypeVar, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc import (
    full_abc_local_environment_qualification_authorization_source_authority_parity,
    full_abc_local_environment_qualification_cu129_harness_evidence_integration,
    full_abc_local_environment_qualification_execution_authorization,
    full_abc_local_environment_qualification_execution_authorization_contracts,
    full_abc_local_environment_qualification_kaggle_launcher,
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

source_authority_parity = (
    full_abc_local_environment_qualification_authorization_source_authority_parity
)
harness_integration = full_abc_local_environment_qualification_cu129_harness_evidence_integration
authorization_package = full_abc_local_environment_qualification_execution_authorization
authorization_contracts = full_abc_local_environment_qualification_execution_authorization_contracts
launcher = full_abc_local_environment_qualification_kaggle_launcher

MATERIALIZATION_RECORD_PATH = authorization_contracts.MATERIALIZATION_RECORD_PATH
MATERIALIZED_DATASET_MANIFEST_PATH = authorization_contracts.MATERIALIZED_DATASET_MANIFEST_PATH
AUTHORIZATION_REQUEST_PATH = authorization_contracts.AUTHORIZATION_REQUEST_PATH
RUNTIME_ADAPTER_PATH = authorization_contracts.RUNTIME_ADAPTER_PATH
READINESS_REVIEW_PATH = harness_integration.READINESS_REVIEW_PATH
REVIEW_PATH = READINESS_REVIEW_PATH
LAUNCHER_SOURCE_PATH = harness_integration.LAUNCHER_SOURCE_PATH
LAUNCHER_NOTEBOOK_PATH = harness_integration.LAUNCHER_NOTEBOOK_PATH

# Frozen payload compatibility authorities. These literals must remain accepted by the
# rematerialized runtime loader and historical authority-parity evidence.
SOURCE_MAIN_MERGE_COMMIT: Final = source_authority_parity.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT
HARNESS_SOURCE_COMMIT: Final = source_authority_parity.HARNESS_SOURCE_COMMIT
REVIEW_SOURCE_MAIN_MERGE_COMMIT: Final = SOURCE_MAIN_MERGE_COMMIT

# Current repository and operational-input authorities reviewed at PR #135.
CURRENT_AUTHORIZATION_BASE_COMMIT: Final = "3ea2cf60db7057f94cdbda9060587e5e6881ef28"
CURRENT_HARNESS_SOURCE_COMMIT: Final = harness_integration.SOURCE_COMMIT
AUTHORIZATION_ID: Final = (
    "auragateway-full-abc-local-environment-qualification-execution-authorization-v1"
)
READINESS_REVIEW_SHA256: Final = "2a0463c48e1a8ffdd4c93f7ed20cc4c60bd7925602a09a59a7b9d9dc3545f00b"
AUTHORIZATION_ISSUANCE_REVIEW_SHA256: Final = READINESS_REVIEW_SHA256
MATERIALIZATION_RECORD_SHA256: Final = (
    "284b488dece09e6b17dcf72e4dea69bbdadd440356ce353622b100c38a02100a"
)
RUNTIME_MANIFEST_SHA256: Final = "f7289cee9414d03d88ceb4775198e15ff9446fd99771a58c187de0d4264ef94a"
RUNTIME_ADAPTER_SHA256: Final = "aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"
EXECUTION_REQUEST_SHA256: Final = "7b0080429246f6def3c1ac28b8a677a2ed7e29ccf318690d9309ed98ff179ba0"
AUTHORIZATION_REQUEST_SHA256: Final = (
    "57efaf2209bf3bc7127d9d0a9baa04d5463f97e689ef348ede1d298acaa20f25"
)
LAUNCHER_SOURCE_SHA256: Final = "7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16"
LAUNCHER_NOTEBOOK_SHA256: Final = "7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9"
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
IMPLEMENTATION_NEXT_GATE: Final = "explicit_operator_confirmation_then_issue_fresh_authorization"
NEXT_GATE: Final = "full_abc_local_full_run_environment_qualification_control_materialization"

_ContractT = TypeVar("_ContractT", bound=LocalABCContract)


class AuthorizationIssuanceError(RuntimeError):
    """Metadata-safe failure while validating or issuing operational authority."""

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


@dataclass(frozen=True, slots=True)
class CurrentAuthorizationInputs:
    """Typed current inputs required to construct one frozen-compatible payload."""

    readiness: harness_integration.FreshAuthorizationReadinessReview
    authorization_request: authorization_contracts.QualificationAuthorizationRequest
    execution_request: QualificationExecutionRequest
    runtime_manifest: QualificationDatasetManifest
    materialization_record: authorization_contracts.MaterializedOfflineDatasetRecord


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


def _load_canonical_contract(
    path: Path,
    model: type[_ContractT],
) -> _ContractT:
    try:
        observed = path.read_text(encoding="utf-8")
        contract = model.model_validate_json(observed)
    except (OSError, ValidationError) as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_INPUT_INVALID",
            "an authorization issuance input failed typed validation",
            path.as_posix(),
        ) from exc
    if observed != contract.canonical_json():
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_INPUT_NOT_CANONICAL",
            "an authorization issuance input is not canonical JSON",
            path.as_posix(),
        )
    return contract


def _require_file_identity(path: Path, expected_sha256: str) -> None:
    observed = _file_sha256(path)
    if observed != expected_sha256:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_CURRENT_IDENTITY_DRIFT",
            "a current authorization input identity drifted",
            path.as_posix(),
            details=(observed,),
        )


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


def _require_synchronized_main(
    repo_root: Path,
    *,
    allow_authorization_artifact: bool,
) -> str:
    branch = _run_git(
        repo_root,
        ["branch", "--show-current"],
        error_code="AUTHORIZATION_ISSUANCE_BRANCH_UNREADABLE",
        safe_message="the current Git branch could not be resolved",
    )
    if branch != "main":
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REQUIRES_MAIN",
            "authorization may be issued or verified only from main",
            details=(branch,),
        )

    head = _run_git(
        repo_root,
        ["rev-parse", "HEAD"],
        error_code="AUTHORIZATION_ISSUANCE_HEAD_UNREADABLE",
        safe_message="the current Git HEAD could not be resolved",
    )
    origin_main = _run_git(
        repo_root,
        ["rev-parse", "origin/main"],
        error_code="AUTHORIZATION_ISSUANCE_ORIGIN_MAIN_UNREADABLE",
        safe_message="origin/main could not be resolved",
    )
    if head != origin_main:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_MAIN_NOT_SYNCHRONIZED",
            "local main must equal origin/main before authorization work",
            details=(head, origin_main),
        )

    status = _run_git(
        repo_root,
        ["status", "--porcelain", "--untracked-files=all"],
        error_code="AUTHORIZATION_ISSUANCE_STATUS_UNREADABLE",
        safe_message="the current Git working-tree state could not be resolved",
    )
    changes = tuple(line for line in status.splitlines() if line)
    permitted = (f"?? {AUTHORIZATION_PATH.as_posix()}",)
    if allow_authorization_artifact and changes == permitted:
        return head
    if changes:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_REQUIRES_CLEAN_TREE",
            "authorization work requires a clean tree except for the transient authority",
            details=changes,
        )
    return head


def _require_clean_main(repo_root: Path) -> str:
    return _require_synchronized_main(
        repo_root,
        allow_authorization_artifact=False,
    )


def _require_verification_main(repo_root: Path) -> str:
    return _require_synchronized_main(
        repo_root,
        allow_authorization_artifact=True,
    )


def _require_ancestor(
    repo_root: Path,
    commit: str,
    *,
    error_code: str,
    safe_message: str,
) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationIssuanceError(error_code, safe_message) from exc
    if result.returncode != 0:
        raise AuthorizationIssuanceError(
            error_code,
            safe_message,
            details=(commit,),
        )


def _require_authorization_untracked(repo_root: Path) -> None:
    tracked = _run_git(
        repo_root,
        ["ls-files", "--cached", "--", AUTHORIZATION_PATH.as_posix()],
        error_code="AUTHORIZATION_ISSUANCE_TRACKING_STATE_UNREADABLE",
        safe_message="the authorization tracking state could not be resolved",
    )
    if tracked:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_MUST_REMAIN_UNTRACKED",
            "the transient authorization must never be committed",
            AUTHORIZATION_PATH.as_posix(),
        )


def _require_source_authority(repo_root: Path) -> None:
    _require_ancestor(
        repo_root,
        CURRENT_AUTHORIZATION_BASE_COMMIT,
        error_code="CURRENT_AUTHORIZATION_BASE_COMMIT_MISSING",
        safe_message="the PR 135 integration merge must be an ancestor of HEAD",
    )
    _require_ancestor(
        repo_root,
        CURRENT_HARNESS_SOURCE_COMMIT,
        error_code="CURRENT_HARNESS_SOURCE_COMMIT_MISSING",
        safe_message="the current harness source commit must be an ancestor of HEAD",
    )
    try:
        summary = source_authority_parity.validate_repository_package(repo_root)
    except RuntimeError as exc:
        raise AuthorizationIssuanceError(
            "FROZEN_AUTHORIZATION_SOURCE_PARITY_INVALID",
            "the frozen authorization-source parity package did not validate",
        ) from exc
    if summary.get("authorization_source_main_merge_commit") != SOURCE_MAIN_MERGE_COMMIT:
        raise AuthorizationIssuanceError(
            "FROZEN_AUTHORIZATION_SOURCE_PARITY_DRIFT",
            "the frozen authorization-source authority drifted",
        )


def _validate_no_runtime_activity(repo_root: Path) -> None:
    present = tuple(
        path.as_posix() for path in RUNTIME_EVIDENCE_PATHS if (repo_root / path).exists()
    )
    if present:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_RUNTIME_EVIDENCE_PRESENT",
            "runtime evidence exists before the bounded authorization is used",
            details=present,
        )


def _validate_current_input_package(repo_root: Path) -> CurrentAuthorizationInputs:
    readiness_path = repo_root / READINESS_REVIEW_PATH
    authorization_request_path = repo_root / AUTHORIZATION_REQUEST_PATH
    execution_request_path = repo_root / EXECUTION_REQUEST_PATH
    runtime_manifest_path = repo_root / MATERIALIZED_DATASET_MANIFEST_PATH
    materialization_path = repo_root / MATERIALIZATION_RECORD_PATH
    adapter_path = repo_root / RUNTIME_ADAPTER_PATH
    launcher_source_path = repo_root / LAUNCHER_SOURCE_PATH
    launcher_notebook_path = repo_root / LAUNCHER_NOTEBOOK_PATH

    readiness = _load_canonical_contract(
        readiness_path,
        harness_integration.FreshAuthorizationReadinessReview,
    )
    authorization_request = _load_canonical_contract(
        authorization_request_path,
        authorization_contracts.QualificationAuthorizationRequest,
    )
    execution_request = _load_canonical_contract(
        execution_request_path,
        QualificationExecutionRequest,
    )
    runtime_manifest = _load_canonical_contract(
        runtime_manifest_path,
        QualificationDatasetManifest,
    )
    portable_manifest = _load_canonical_contract(
        runtime_manifest_path,
        authorization_contracts.PortableQualificationDatasetManifest,
    )
    materialization_record = _load_canonical_contract(
        materialization_path,
        authorization_contracts.MaterializedOfflineDatasetRecord,
    )

    expected_files = (
        (readiness_path, READINESS_REVIEW_SHA256),
        (authorization_request_path, AUTHORIZATION_REQUEST_SHA256),
        (execution_request_path, EXECUTION_REQUEST_SHA256),
        (runtime_manifest_path, RUNTIME_MANIFEST_SHA256),
        (materialization_path, MATERIALIZATION_RECORD_SHA256),
        (adapter_path, RUNTIME_ADAPTER_SHA256),
        (launcher_source_path, LAUNCHER_SOURCE_SHA256),
        (launcher_notebook_path, LAUNCHER_NOTEBOOK_SHA256),
    )
    for path, expected_sha256 in expected_files:
        _require_file_identity(path, expected_sha256)

    projected_manifest = authorization_package.build_portable_runtime_manifest(
        materialization_record
    )
    if projected_manifest.canonical_json() != portable_manifest.canonical_json():
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_MANIFEST_PROJECTION_DRIFT",
            "the materialization record no longer projects to the runtime manifest",
            runtime_manifest_path.as_posix(),
        )

    checks = (
        readiness.fingerprint() == READINESS_REVIEW_SHA256,
        readiness.current_manifest_sha256 == RUNTIME_MANIFEST_SHA256,
        readiness.current_materialization_record_sha256 == MATERIALIZATION_RECORD_SHA256,
        readiness.current_runtime_adapter_sha256 == RUNTIME_ADAPTER_SHA256,
        readiness.current_launcher_source_sha256 == LAUNCHER_SOURCE_SHA256,
        readiness.current_launcher_notebook_sha256 == LAUNCHER_NOTEBOOK_SHA256,
        readiness.final_authorization_present is False,
        readiness.authorization_source_binding_policy
        == launcher.AUTHORIZATION_SOURCE_BINDING_POLICY,
        authorization_request.fingerprint() == AUTHORIZATION_REQUEST_SHA256,
        authorization_request.execution_request_sha256 == EXECUTION_REQUEST_SHA256,
        authorization_request.maximum_authorization_window_minutes
        == MAXIMUM_AUTHORIZATION_WINDOW_MINUTES,
        execution_request.fingerprint() == EXECUTION_REQUEST_SHA256,
        runtime_manifest.fingerprint() == RUNTIME_MANIFEST_SHA256,
        materialization_record.fingerprint() == MATERIALIZATION_RECORD_SHA256,
        materialization_record.runtime_manifest_sha256 == RUNTIME_MANIFEST_SHA256,
        materialization_record.harness_source_commit == CURRENT_HARNESS_SOURCE_COMMIT,
        launcher.SOURCE_MAIN_MERGE_COMMIT == CURRENT_HARNESS_SOURCE_COMMIT,
        launcher.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT == SOURCE_MAIN_MERGE_COMMIT,
        launcher.AUTHORIZATION_SOURCE_BINDING_POLICY == "CONTROL_PACKAGE_AUTHORIZATION_PARITY",
    )
    if not all(checks):
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_CURRENT_BINDING_DRIFT",
            "the fresh readiness decision no longer binds the current inputs",
        )

    try:
        launcher_summary = launcher.verify_launcher_notebook(
            repo_root=repo_root,
            notebook_path=launcher_notebook_path,
        )
    except launcher.KaggleLauncherError as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_LAUNCHER_INVALID",
            "the current launcher failed deterministic verification",
            LAUNCHER_NOTEBOOK_PATH.as_posix(),
            details=exc.details,
        ) from exc
    if launcher_summary.notebook_sha256 != LAUNCHER_NOTEBOOK_SHA256:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ISSUANCE_LAUNCHER_IDENTITY_DRIFT",
            "the current launcher notebook identity drifted",
            LAUNCHER_NOTEBOOK_PATH.as_posix(),
        )

    return CurrentAuthorizationInputs(
        readiness=readiness,
        authorization_request=authorization_request,
        execution_request=execution_request,
        runtime_manifest=runtime_manifest,
        materialization_record=materialization_record,
    )


def _load_operational_inputs(
    repo_root: Path,
) -> tuple[QualificationExecutionRequest, QualificationDatasetManifest]:
    inputs = _validate_current_input_package(repo_root)
    return inputs.execution_request, inputs.runtime_manifest


def _prepare_issuance_inputs(repo_root: Path) -> CurrentAuthorizationInputs:
    _require_source_authority(repo_root)
    _validate_no_runtime_activity(repo_root)
    try:
        evidence_summary = harness_integration.validate_repository_package(repo_root)
    except harness_integration.HarnessEvidenceIntegrationError as exc:
        raise AuthorizationIssuanceError(
            "CURRENT_HARNESS_EVIDENCE_INTEGRATION_INVALID",
            "the current harness evidence integration did not validate",
            exc.path,
            details=exc.details,
        ) from exc
    if evidence_summary.get("operational_input_closure") != "PASSED":
        raise AuthorizationIssuanceError(
            "CURRENT_OPERATIONAL_INPUT_CLOSURE_MISSING",
            "operational input closure must pass before authorization issuance",
        )
    if evidence_summary.get("authorization_issued") is not False:
        raise AuthorizationIssuanceError(
            "CURRENT_HARNESS_EVIDENCE_CROSSED_AUTHORIZATION_BOUNDARY",
            "the current harness evidence package crossed the authorization boundary",
        )
    if (repo_root / AUTHORIZATION_PATH).exists():
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ALREADY_EXISTS",
            "the final authorization already exists and will not be overwritten",
            AUTHORIZATION_PATH.as_posix(),
        )
    return _validate_current_input_package(repo_root)


def validate_implementation_package(repo_root: Path) -> dict[str, object]:
    """Validate the merged issuer boundary without creating live authority."""

    root = repo_root.resolve()
    inputs = _prepare_issuance_inputs(root)
    return {
        "status": "FRESH_CU129_AUTHORIZATION_ISSUER_READY",
        "current_authorization_base_commit": CURRENT_AUTHORIZATION_BASE_COMMIT,
        "current_harness_source_commit": CURRENT_HARNESS_SOURCE_COMMIT,
        "frozen_authorization_source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
        "readiness_review_sha256": inputs.readiness.fingerprint(),
        "execution_request_sha256": inputs.execution_request.fingerprint(),
        "runtime_manifest_sha256": inputs.runtime_manifest.fingerprint(),
        "materialization_record_sha256": inputs.materialization_record.fingerprint(),
        "runtime_adapter_sha256": RUNTIME_ADAPTER_SHA256,
        "launcher_source_sha256": LAUNCHER_SOURCE_SHA256,
        "launcher_notebook_sha256": LAUNCHER_NOTEBOOK_SHA256,
        "maximum_workers": inputs.authorization_request.maximum_workers,
        "maximum_kaggle_sessions": inputs.authorization_request.maximum_kaggle_sessions,
        "maximum_model_requests": inputs.authorization_request.maximum_model_requests,
        "maximum_output_tokens_per_request": (
            inputs.authorization_request.maximum_output_tokens_per_request
        ),
        "benchmark_trajectory_requests_permitted": 0,
        "authorization_issued": False,
        "kaggle_session_started": False,
        "worker_started": False,
        "model_requests_performed": 0,
        "measured_execution_authorized": False,
        "external_spend": 0,
        "next_gate": IMPLEMENTATION_NEXT_GATE,
    }


def _build_authorization(
    *,
    repo_root: Path,
    confirmation: AuthorizationIssuanceConfirmation,
) -> QualificationExecutionAuthorization:
    inputs = _prepare_issuance_inputs(repo_root)
    request = inputs.execution_request
    manifest = inputs.runtime_manifest
    authorization_request = inputs.authorization_request

    issued_at = confirmation.confirmed_at
    expires_at = issued_at + timedelta(minutes=confirmation.authorization_window_minutes)
    authorization = QualificationExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision=AuthorizationDecision.AUTHORIZED,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        request_sha256=request.fingerprint(),
        review_git_blob_sha=AUTHORIZATION_ISSUANCE_REVIEW_GIT_BLOB_SHA,
        authorization_issuance_review_sha256=inputs.readiness.fingerprint(),
        materialization_record_sha256=inputs.materialization_record.fingerprint(),
        dataset_manifest_sha256=manifest.fingerprint(),
        runtime_factory=QualificationRuntimeFactoryBinding(
            factory_path=authorization_request.runtime_adapter.factory_path,
            artifact_path=authorization_request.runtime_adapter.artifact_path,
            artifact_sha256=RUNTIME_ADAPTER_SHA256,
        ),
        issued_at=issued_at,
        expires_at=expires_at,
        maximum_workers=authorization_request.maximum_workers,
        maximum_kaggle_sessions=authorization_request.maximum_kaggle_sessions,
        maximum_model_requests=authorization_request.maximum_model_requests,
        maximum_output_tokens_per_request=(authorization_request.maximum_output_tokens_per_request),
        benchmark_trajectory_requests_permitted=(
            authorization_request.benchmark_trajectory_requests_permitted
        ),
        customer_data_permitted=authorization_request.customer_data_permitted,
        credentials_permitted=authorization_request.credentials_permitted,
        network_access_permitted=authorization_request.network_access_permitted,
        external_spend=authorization_request.external_spend,
        operator_confirmation_recorded=True,
        measured_execution_authorized=False,
    )
    _validate_frozen_loader_parity(authorization)
    return authorization


def _validate_frozen_loader_parity(
    authorization: QualificationExecutionAuthorization,
) -> None:
    try:
        source_authority_parity.validate_authorization_payload(
            authorization.model_dump(mode="json")
        )
    except source_authority_parity.FrozenLoaderParityError as exc:
        raise AuthorizationIssuanceError(
            "CURRENT_ISSUANCE_FROZEN_LOADER_PARITY_FAILED",
            "current authorization is incompatible with the frozen runtime loader",
            AUTHORIZATION_PATH.as_posix(),
            details=exc.details,
        ) from exc


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
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.link(temporary_path, path)
    except FileExistsError as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ALREADY_EXISTS",
            "the final authorization appeared during issuance",
            path.as_posix(),
        ) from exc
    except OSError as exc:
        raise AuthorizationIssuanceError(
            "AUTHORIZATION_ATOMIC_WRITE_FAILED",
            "the final authorization could not be created atomically",
            path.as_posix(),
        ) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def issue_authorization(
    *,
    repo_root: Path,
    confirmation: AuthorizationIssuanceConfirmation,
) -> dict[str, object]:
    """Issue one non-overwriting authorization after explicit confirmation."""

    root = repo_root.resolve()
    issuer_head = _require_clean_main(root)
    _require_authorization_untracked(root)
    authorization = _build_authorization(
        repo_root=root,
        confirmation=confirmation,
    )
    target = root / AUTHORIZATION_PATH
    _write_authorization(target, authorization)
    return {
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": authorization.fingerprint(),
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "issuer_head_commit": issuer_head,
        "current_authorization_base_commit": CURRENT_AUTHORIZATION_BASE_COMMIT,
        "current_harness_source_commit": CURRENT_HARNESS_SOURCE_COMMIT,
        "frozen_authorization_source_main_merge_commit": (authorization.source_main_merge_commit),
        "readiness_review_sha256": authorization.authorization_issuance_review_sha256,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "maximum_authorization_window_minutes": confirmation.authorization_window_minutes,
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
        "operator_confirmation_recorded": authorization.operator_confirmation_recorded,
        "kaggle_session_started": False,
        "worker_started": False,
        "model_request_count": 0,
        "measured_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _load_authorization(path: Path) -> QualificationExecutionAuthorization:
    return _load_canonical_contract(path, QualificationExecutionAuthorization)


def verify_authorization(
    *,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify current input bindings and one live frozen-compatible window."""

    root = repo_root.resolve()
    issuer_head = _require_verification_main(root)
    _require_authorization_untracked(root)
    _require_source_authority(root)
    _validate_no_runtime_activity(root)
    inputs = _validate_current_input_package(root)
    authorization_path = root / AUTHORIZATION_PATH
    authorization = _load_authorization(authorization_path)

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
    _validate_frozen_loader_parity(authorization)

    checks = (
        authorization.authorization_id == AUTHORIZATION_ID,
        authorization.source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT,
        authorization.request_sha256 == inputs.execution_request.fingerprint(),
        authorization.review_git_blob_sha == AUTHORIZATION_ISSUANCE_REVIEW_GIT_BLOB_SHA,
        authorization.authorization_issuance_review_sha256 == inputs.readiness.fingerprint(),
        authorization.materialization_record_sha256 == inputs.materialization_record.fingerprint(),
        authorization.dataset_manifest_sha256 == inputs.runtime_manifest.fingerprint(),
        authorization.runtime_factory.factory_path
        == inputs.authorization_request.runtime_adapter.factory_path,
        authorization.runtime_factory.artifact_path
        == inputs.authorization_request.runtime_adapter.artifact_path,
        authorization.runtime_factory.artifact_sha256 == RUNTIME_ADAPTER_SHA256,
        authorization.maximum_workers == inputs.authorization_request.maximum_workers,
        authorization.maximum_kaggle_sessions
        == inputs.authorization_request.maximum_kaggle_sessions,
        authorization.maximum_model_requests == inputs.authorization_request.maximum_model_requests,
        authorization.maximum_output_tokens_per_request
        == inputs.authorization_request.maximum_output_tokens_per_request,
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
            "the final authorization no longer binds the reviewed current inputs",
            AUTHORIZATION_PATH.as_posix(),
        )

    return {
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": authorization.fingerprint(),
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_valid": True,
        "issuer_head_commit": issuer_head,
        "current_authorization_base_commit": CURRENT_AUTHORIZATION_BASE_COMMIT,
        "current_harness_source_commit": CURRENT_HARNESS_SOURCE_COMMIT,
        "frozen_authorization_source_main_merge_commit": (authorization.source_main_merge_commit),
        "readiness_review_sha256": authorization.authorization_issuance_review_sha256,
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

    validate_parser = subparsers.add_parser("validate-implementation")
    validate_parser.add_argument("--repo-root", type=Path, required=True)

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
    """Validate, issue, or verify one bounded authorization without execution."""

    try:
        arguments = _build_parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "validate-implementation":
            summary = validate_implementation_package(repo_root)
        elif arguments.command == "issue":
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
