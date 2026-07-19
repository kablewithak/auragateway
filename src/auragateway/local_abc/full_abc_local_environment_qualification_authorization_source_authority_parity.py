"""Validate current issuance against the frozen runtime authorization loader."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Self, cast

from pydantic import ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/+-]{3,240}$")
_FACTORY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{2,199}:[A-Za-z_][A-Za-z0-9_]{1,79}$")

AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT: Final = "211a10757999b1b110cb1d9df172938cf6ed7969"
HARNESS_SOURCE_COMMIT: Final = "be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"
FROZEN_EXECUTION_CONTRACTS_SHA256: Final = (
    "69c0412b6bf89ad5eed2bb174f55c1fb621d126767c48147bbc2287a323adcd0"
)
FROZEN_REVIEW_GIT_BLOB_SHA: Final = "61590be7fe1d10e8e9b38405cf634f4a0cae3e31"
EXPECTED_EVIDENCE_ZIP_SHA256: Final = (
    "9e82ea353f434a0a1b06c2de07cb556dd485bd156cb956c7a50b8a98bc929cd2"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_environment_qualification_"
    "authorization_source_authority_parity_v1.json"
)
EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/environment-qualification-authorization-source-authority-failure-v1"
)
LAUNCHER_FAILURE_PATH: Final = EVIDENCE_DIRECTORY / "launcher_failure.json"
LAUNCHER_FAILURE_TRACE_PATH: Final = EVIDENCE_DIRECTORY / "launcher_failure_trace.txt"
EVIDENCE_SHA256_PATH: Final = EVIDENCE_DIRECTORY / "evidence_sha256.json"


class FrozenRuntimeFactoryBindingV1(LocalABCContract):
    """Exact runtime-factory contract accepted by the frozen harness."""

    factory_path: str
    artifact_path: str
    artifact_sha256: str

    @field_validator("factory_path")
    @classmethod
    def validate_factory_path(cls, value: str) -> str:
        if _FACTORY_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime factory path must use module:function syntax")
        return value

    @field_validator("artifact_path")
    @classmethod
    def validate_artifact_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if _PATH_PATTERN.fullmatch(value) is None or path.is_absolute() or ".." in path.parts:
            raise ValueError(
                "runtime factory artifact path must be repository-relative and bounded"
            )
        return value

    @field_validator("artifact_sha256")
    @classmethod
    def validate_artifact_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime adapter digest must be lowercase SHA-256")
        return value


class FrozenHarnessQualificationExecutionAuthorizationV1(LocalABCContract):
    """Exact authorization shape accepted by the rematerialized frozen harness."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str
    decision: Literal["AUTHORIZED"]
    source_main_merge_commit: Literal["211a10757999b1b110cb1d9df172938cf6ed7969"]
    request_sha256: str
    review_git_blob_sha: Literal["61590be7fe1d10e8e9b38405cf634f4a0cae3e31"]
    authorization_issuance_review_sha256: str
    materialization_record_sha256: str
    dataset_manifest_sha256: str
    runtime_factory: FrozenRuntimeFactoryBindingV1
    issued_at: datetime
    expires_at: datetime
    maximum_workers: Literal[2] = 2
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_model_requests: Literal[8] = 8
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    customer_data_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    network_access_permitted: Literal[False] = False
    external_spend: Literal[0] = 0
    operator_confirmation_recorded: Literal[True]
    measured_execution_authorized: Literal[False] = False

    @field_validator("authorization_id")
    @classmethod
    def validate_authorization_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization IDs must use stable lowercase characters")
        return value

    @field_validator(
        "request_sha256",
        "authorization_issuance_review_sha256",
        "materialization_record_sha256",
        "dataset_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization digests must be lowercase SHA-256")
        return value

    @field_validator("issued_at", "expires_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        if self.expires_at - self.issued_at > timedelta(minutes=240):
            raise ValueError("authorization window cannot exceed 240 minutes")
        return self


class FrozenLoaderParityError(RuntimeError):
    """Bounded incompatibility between current issuance and frozen runtime loader."""

    def __init__(
        self,
        safe_message: str,
        *,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message
        self.details = details


def validate_authorization_payload(
    payload: object,
) -> FrozenHarnessQualificationExecutionAuthorizationV1:
    """Validate one current-issuance payload through the frozen loader contract."""

    try:
        return FrozenHarnessQualificationExecutionAuthorizationV1.model_validate(payload)
    except ValidationError as exc:
        details = tuple(
            sorted(
                {
                    ".".join(str(part) for part in error["loc"])
                    for error in exc.errors(include_url=False)
                }
            )
        )
        raise FrozenLoaderParityError(
            "current authorization is incompatible with the frozen runtime loader",
            details=details,
        ) from exc


def frozen_authorization_schema_sha256() -> str:
    """Return a deterministic identity for the preserved compatibility schema."""

    payload = json.dumps(
        FrozenHarnessQualificationExecutionAuthorizationV1.model_json_schema(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected one JSON object: {path.as_posix()}")
    return cast(dict[str, object], payload)


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate evidence and active authority semantics without issuing authority."""

    root = repo_root.resolve()
    record = _load_json_object(root / RECORD_PATH)
    evidence = _load_json_object(root / EVIDENCE_SHA256_PATH)

    if evidence.get("source_evidence_zip_sha256") != EXPECTED_EVIDENCE_ZIP_SHA256:
        raise RuntimeError("source evidence ZIP identity drifted")

    files = evidence.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("evidence checksum map is invalid")

    expected_hashes = {
        LAUNCHER_FAILURE_PATH.name: _file_sha256(root / LAUNCHER_FAILURE_PATH),
        LAUNCHER_FAILURE_TRACE_PATH.name: _file_sha256(root / LAUNCHER_FAILURE_TRACE_PATH),
    }
    if files != expected_hashes:
        raise RuntimeError("preserved failure evidence identity drifted")

    failure = _load_json_object(root / LAUNCHER_FAILURE_PATH)
    expected_failure = {
        "status": "FAILED",
        "stage": "reviewed_core_execution",
        "exception_type": "FullABCLocalEnvironmentQualificationExecutionError",
        "safe_message": "the qualification execution authorization is invalid",
        "provider_calls_performed": False,
        "external_spend": 0,
        "credentials_used": False,
        "customer_data_used": False,
        "runtime_evidence_found": [],
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_failure.items()
            if failure.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("captured failure fields drifted: " + ", ".join(drift))

    authority = record.get("authority_semantics")
    if not isinstance(authority, dict):
        raise RuntimeError("authority semantics are missing")
    if authority.get("authorization_source_main_merge_commit") != (
        AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT
    ):
        raise RuntimeError("authorization source authority drifted")
    if authority.get("harness_source_commit") != HARNESS_SOURCE_COMMIT:
        raise RuntimeError("harness source authority drifted")
    if authority.get("frozen_execution_contracts_sha256") != (FROZEN_EXECUTION_CONTRACTS_SHA256):
        raise RuntimeError("frozen execution-contract identity drifted")

    from auragateway.local_abc import (
        full_abc_local_environment_qualification_execution_authorization_issuance as issuance,
    )
    from auragateway.local_abc import (
        full_abc_local_environment_qualification_kaggle_launcher as launcher,
    )

    if issuance.SOURCE_MAIN_MERGE_COMMIT != AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT:
        raise RuntimeError("issuance authorization authority drifted")
    if issuance.HARNESS_SOURCE_COMMIT != HARNESS_SOURCE_COMMIT:
        raise RuntimeError("issuance harness authority drifted")
    if launcher.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT != (AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT):
        raise RuntimeError("launcher authorization authority drifted")
    if launcher.SOURCE_MAIN_MERGE_COMMIT != HARNESS_SOURCE_COMMIT:
        raise RuntimeError("launcher harness authority drifted")

    launcher_summary = launcher.verify_launcher_notebook(
        repo_root=root,
        notebook_path=root / launcher.LAUNCHER_NOTEBOOK_PATH,
    )

    return {
        "status": "AUTHORIZATION_SOURCE_AUTHORITY_PARITY_PACKAGE_VALID",
        "record_sha256": _file_sha256(root / RECORD_PATH),
        "evidence_zip_sha256": EXPECTED_EVIDENCE_ZIP_SHA256,
        "evidence_files_verified": 3,
        "failure_class": "AUTHORIZATION_INVALID",
        "failure_code": "SOURCE_MAIN_MERGE_COMMIT_LITERAL_DRIFT",
        "failure_stage": "reviewed_core_execution",
        "authorization_source_main_merge_commit": (AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT),
        "harness_source_commit": HARNESS_SOURCE_COMMIT,
        "frozen_execution_contracts_sha256": FROZEN_EXECUTION_CONTRACTS_SHA256,
        "frozen_authorization_schema_sha256": frozen_authorization_schema_sha256(),
        "current_launcher_sha256": launcher_summary.notebook_sha256,
        "authorization_issued": False,
        "model_requests_performed": 0,
        "next_gate": "merge_authority_parity_then_issue_fresh_authorization",
    }
