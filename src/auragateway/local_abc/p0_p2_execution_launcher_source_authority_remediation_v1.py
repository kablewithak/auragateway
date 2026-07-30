"""Validate the failed P0-P2 launcher source-authority evidence."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import sys
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, model_validator

import auragateway.local_abc.p0_p2_source_acceptance_v1 as source_acceptance
from auragateway.local_abc.contracts import LocalABCContract

REMEDIATION_BASE_MAIN_COMMIT: Final = "d3c111a94ae517763d51fc724702bd9a3c11dd52"
FAILED_LAUNCHER_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-execution-launcher-v2"
FAILED_LAUNCHER_SAVED_VERSION_ID: Final = 339098285
FAILED_LAUNCHER_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-cu129-p0-p2-execution-launcher-v2/log?scriptVersionId=339098285"
)

STALE_BUNDLE_MANIFEST_SHA256: Final = (
    "246937c7fe66460953d88ea05fce2a9244ea4f104793b54ab6a40b122cba4ede"
)
ACCEPTED_BUNDLE_MANIFEST_SHA256: Final = source_acceptance.BUNDLE_MANIFEST_SHA256

EVIDENCE_ROOT: Final = Path(
    "evidence_vault/local_abc/cu129-p0-p2-launcher-source-authority-remediation-v1"
)
FAILED_LOG_PATH: Final = EVIDENCE_ROOT / (
    "ag-cu129-p0-p2-execution-launcher-v2-failed-339098285.log"
)
FAILED_ZIP_PATH: Final = EVIDENCE_ROOT / (
    "ag-cu129-p0-p2-execution-launcher-v2-failed-339098285.zip"
)
REMEDIATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p0_p2_execution_launcher_"
    "source_authority_remediation_v1.json"
)
BOUND_EVIDENCE_PATHS: Final = (FAILED_LOG_PATH, FAILED_ZIP_PATH)

FAILED_LOG_SHA256: Final = "c2302bd80c13d86673931ba7c039e9974f3bf0bf46143766f0a1d274a4764d25"
FAILED_ZIP_SHA256: Final = "7fa90e98c0904d046dce1d5625397185e0bf87a809e5f202d074e5ccde15ae6d"
FAILED_REPORT_MEMBER: Final = "p0_p2_execution_launcher_report_v2.json"
FAILED_REPORT_SHA256: Final = "838cbbed27004a8ca45722787a72170b818e06fdaa4cfe6cc97e5c9efef3b8d1"
FAILURE_CLASSIFICATION: Final = "STALE_TEMPLATE_BUNDLE_MANIFEST_AUTHORITY"
FAILURE_STAGE: Final = "source_output_discovery"
FAILURE_SAFE_MESSAGE: Final = "expected exactly one identity-shaped P0-P2 source output, observed 0"


class P0P2LauncherSourceAuthorityRemediationError(RuntimeError):
    """Fail-closed source-authority remediation error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class EvidenceIdentity(LocalABCContract):
    """Repository-bound failed-run evidence identity."""

    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class RemediationSafety(LocalABCContract):
    """Observed execution boundary for the failed launcher run."""

    diagnostic_execution_attempts: Literal[0] = 0
    runtime_install_attempts: Literal[0] = 0
    kernel_compile_and_execution_attempts: Literal[0] = 0
    model_loads: Literal[0] = 0
    worker_starts: Literal[0] = 0
    model_requests: Literal[0] = 0
    benchmark_trajectory_requests: Literal[0] = 0
    network_requests: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_present: Literal[False] = False
    external_spend: Literal[0] = 0


class P0P2LauncherSourceAuthorityRemediationRecord(LocalABCContract):
    """Validated launcher failure and accepted correction authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-execution-launcher-source-authority-remediation-v1"]
    status: Literal["P0_P2_EXECUTION_LAUNCHER_SOURCE_AUTHORITY_REMEDIATION_V1_VALID"]
    remediation_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    failed_launcher_notebook_name: str
    failed_launcher_saved_version_id: int = Field(gt=0)
    failed_launcher_saved_version_url: str
    failure_classification: Literal["STALE_TEMPLATE_BUNDLE_MANIFEST_AUTHORITY"]
    first_divergence: Literal["source_output_discovery"]
    stale_bundle_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_bundle_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    failure_log: EvidenceIdentity
    failure_archive: EvidenceIdentity
    failure_report_member: str
    failure_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    failure_status: Literal["P0_P2_EXECUTION_LAUNCHER_FAILED_V2"]
    failure_safe_message: str
    safety: RemediationSafety
    unchanged_rerun_authorized: Literal[False] = False
    platform_conclusion: Literal["NONE"] = "NONE"
    next_gate: Literal["regenerate_and_validate_p0_p2_execution_launcher_v2"]

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        if self.remediation_base_main_commit != REMEDIATION_BASE_MAIN_COMMIT:
            raise ValueError("remediation base-main commit drifted")
        if self.failed_launcher_notebook_name != FAILED_LAUNCHER_NOTEBOOK_NAME:
            raise ValueError("failed launcher notebook name drifted")
        if self.failed_launcher_saved_version_id != FAILED_LAUNCHER_SAVED_VERSION_ID:
            raise ValueError("failed launcher saved-version ID drifted")
        if self.failed_launcher_saved_version_url != FAILED_LAUNCHER_SAVED_VERSION_URL:
            raise ValueError("failed launcher saved-version URL drifted")
        if self.stale_bundle_manifest_sha256 != STALE_BUNDLE_MANIFEST_SHA256:
            raise ValueError("stale bundle-manifest identity drifted")
        if self.accepted_bundle_manifest_sha256 != ACCEPTED_BUNDLE_MANIFEST_SHA256:
            raise ValueError("accepted bundle-manifest identity drifted")
        if self.stale_bundle_manifest_sha256 == self.accepted_bundle_manifest_sha256:
            raise ValueError("stale and accepted bundle-manifest identities are equal")
        return self


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_TEMPORARY_PATH_PRESENT",
            "temporary remediation output path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _read_bound_file(
    repo_root: Path,
    relative_path: Path,
    expected_sha256: str,
) -> bytes:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_EVIDENCE_UNSAFE",
            "required failed-launcher evidence is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_EVIDENCE_DRIFT",
            "failed-launcher evidence identity drifted",
            relative_path.as_posix(),
        )
    return payload


def _load_canonical_json_object(payload: bytes, *, label: str) -> dict[str, object]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_JSON_INVALID",
            "failed-launcher report is invalid JSON",
            label,
        ) from error
    if not isinstance(raw, dict):
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_JSON_ROOT_INVALID",
            "failed-launcher report root must be one object",
            label,
        )
    normalized = {str(key): value for key, value in raw.items()}
    if _canonical_json(normalized).encode("utf-8") != payload:
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_JSON_NONCANONICAL",
            "failed-launcher report is not canonical JSON",
            label,
        )
    return normalized


def _read_failure_report(archive_payload: bytes) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_payload)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if names != [FAILED_REPORT_MEMBER]:
                raise P0P2LauncherSourceAuthorityRemediationError(
                    "P0_P2_LAUNCHER_SOURCE_AUTHORITY_ZIP_MEMBER_SET_DRIFT",
                    "failed-launcher archive member set drifted",
                    FAILED_ZIP_PATH.as_posix(),
                )
            info = infos[0]
            path = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if path.is_absolute() or ".." in path.parts or info.is_dir() or stat.S_ISLNK(mode):
                raise P0P2LauncherSourceAuthorityRemediationError(
                    "P0_P2_LAUNCHER_SOURCE_AUTHORITY_ZIP_MEMBER_UNSAFE",
                    "failed-launcher archive contains an unsafe member",
                    info.filename,
                )
            return archive.read(info.filename)
    except zipfile.BadZipFile as error:
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_ZIP_INVALID",
            "failed-launcher evidence archive is invalid",
            FAILED_ZIP_PATH.as_posix(),
        ) from error


def _require_value(
    payload: Mapping[str, object],
    key: str,
    expected: object,
) -> None:
    if payload.get(key) != expected:
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_SEMANTIC_DRIFT",
            f"failed-launcher evidence binding drifted: {key}",
            FAILED_REPORT_MEMBER,
        )


def build_remediation_record(
    repo_root: Path,
) -> P0P2LauncherSourceAuthorityRemediationRecord:
    """Build the remediation record from immutable failed-run evidence."""

    log_payload = _read_bound_file(
        repo_root,
        FAILED_LOG_PATH,
        FAILED_LOG_SHA256,
    )
    archive_payload = _read_bound_file(
        repo_root,
        FAILED_ZIP_PATH,
        FAILED_ZIP_SHA256,
    )
    report_payload = _read_failure_report(archive_payload)
    if _sha256_bytes(report_payload) != FAILED_REPORT_SHA256:
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_REPORT_IDENTITY_DRIFT",
            "failed-launcher report identity drifted",
            FAILED_REPORT_MEMBER,
        )
    report = _load_canonical_json_object(
        report_payload,
        label=FAILED_REPORT_MEMBER,
    )

    expected = {
        "schema_version": "2.0.0",
        "status": "P0_P2_EXECUTION_LAUNCHER_FAILED_V2",
        "notebook_name": FAILED_LAUNCHER_NOTEBOOK_NAME,
        "stage": FAILURE_STAGE,
        "safe_message": FAILURE_SAFE_MESSAGE,
        "diagnostic_execution_attempts": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "credentials_used": False,
        "customer_data_present": False,
        "external_spend": 0,
        "next_gate": "preserve_failure_evidence_and_review_launcher_v2",
    }
    for key, value in expected.items():
        _require_value(report, key, value)

    log_text = log_payload.decode("utf-8", errors="strict")
    required_log_fragments = (
        "source_output_discovery",
        FAILURE_SAFE_MESSAGE,
        "discover_source_output",
    )
    if any(fragment not in log_text for fragment in required_log_fragments):
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_LOG_SEMANTIC_DRIFT",
            "failed-launcher log does not preserve the first divergence",
            FAILED_LOG_PATH.as_posix(),
        )

    return P0P2LauncherSourceAuthorityRemediationRecord(
        record_id=("auragateway-cu129-p0-p2-execution-launcher-source-authority-remediation-v1"),
        status=("P0_P2_EXECUTION_LAUNCHER_SOURCE_AUTHORITY_REMEDIATION_V1_VALID"),
        remediation_base_main_commit=REMEDIATION_BASE_MAIN_COMMIT,
        failed_launcher_notebook_name=FAILED_LAUNCHER_NOTEBOOK_NAME,
        failed_launcher_saved_version_id=FAILED_LAUNCHER_SAVED_VERSION_ID,
        failed_launcher_saved_version_url=FAILED_LAUNCHER_SAVED_VERSION_URL,
        failure_classification=FAILURE_CLASSIFICATION,
        first_divergence=FAILURE_STAGE,
        stale_bundle_manifest_sha256=STALE_BUNDLE_MANIFEST_SHA256,
        accepted_bundle_manifest_sha256=ACCEPTED_BUNDLE_MANIFEST_SHA256,
        failure_log=EvidenceIdentity(
            repository_path=FAILED_LOG_PATH.as_posix(),
            sha256=FAILED_LOG_SHA256,
            size_bytes=len(log_payload),
        ),
        failure_archive=EvidenceIdentity(
            repository_path=FAILED_ZIP_PATH.as_posix(),
            sha256=FAILED_ZIP_SHA256,
            size_bytes=len(archive_payload),
        ),
        failure_report_member=FAILED_REPORT_MEMBER,
        failure_report_sha256=FAILED_REPORT_SHA256,
        failure_status="P0_P2_EXECUTION_LAUNCHER_FAILED_V2",
        failure_safe_message=FAILURE_SAFE_MESSAGE,
        safety=RemediationSafety(),
        unchanged_rerun_authorized=False,
        platform_conclusion="NONE",
        next_gate="regenerate_and_validate_p0_p2_execution_launcher_v2",
    )


def _record_bytes(
    record: P0P2LauncherSourceAuthorityRemediationRecord,
) -> bytes:
    return _canonical_json(record.model_dump(mode="json")).encode("utf-8")


def generate(
    repo_root: Path,
) -> P0P2LauncherSourceAuthorityRemediationRecord:
    """Generate the canonical remediation record."""

    record = build_remediation_record(repo_root)
    _write_bytes_atomic(
        repo_root / REMEDIATION_RECORD_PATH,
        _record_bytes(record),
    )
    print("P0_P2_LAUNCHER_SOURCE_AUTHORITY_REMEDIATION_RECORD_GENERATED")
    print(record.canonical_json())
    return record


def validate(
    repo_root: Path,
) -> P0P2LauncherSourceAuthorityRemediationRecord:
    """Validate the canonical remediation record and evidence."""

    expected = build_remediation_record(repo_root)
    path = repo_root / REMEDIATION_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_RECORD_MISSING",
            "source-authority remediation record is missing or unsafe",
            REMEDIATION_RECORD_PATH.as_posix(),
        )
    observed = path.read_bytes()
    if observed != _record_bytes(expected):
        raise P0P2LauncherSourceAuthorityRemediationError(
            "P0_P2_LAUNCHER_SOURCE_AUTHORITY_RECORD_DRIFT",
            "source-authority remediation record differs from generated state",
            REMEDIATION_RECORD_PATH.as_posix(),
        )
    return expected


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or validate P0-P2 launcher source-authority remediation."
    )
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> Never:
    arguments = _parser().parse_args(argv)
    repo_root = arguments.repo_root.resolve()
    try:
        if arguments.command == "generate":
            generate(repo_root)
        else:
            record = validate(repo_root)
            print(record.canonical_json())
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        P0P2LauncherSourceAuthorityRemediationError,
    ) as error:
        if isinstance(
            error,
            P0P2LauncherSourceAuthorityRemediationError,
        ):
            payload = error.envelope()
        else:
            payload = {
                "error_code": ("P0_P2_LAUNCHER_SOURCE_AUTHORITY_UNEXPECTED_VALIDATION_ERROR"),
                "safe_message": str(error),
                "path": None,
            }
        print(_canonical_json(cast(object, payload)), file=sys.stderr)
        raise SystemExit(2) from error
    raise SystemExit(0)


if __name__ == "__main__":
    main()
