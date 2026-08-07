"""Accept and classify the governed P4 output-contract diagnostic V2 execution pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p4_output_contract_diagnostic_execution_acceptance_v1_policy.json"
)
POLICY_SHA256: Final = "7f16eb72d2215073049bf3c4bbe794d436cbe7ae97cf04bb36e148d00beb7e73"
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_output_contract_diagnostic_execution_acceptance_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_output_contract_diagnostic_execution_acceptance_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-07-local-abc-p4-output-contract-diagnostic-v2-execution-acceptance-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_Output_Contract_Diagnostic_V2_Execution_Acceptance_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p4_output_contract_diagnostic_v2_execution_acceptance_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_acceptance_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_execution_acceptance_v1.json"
)

SAVED_VERSION_ID: Final = 340775383
EVIDENCE_DIR: Final = Path("evidence_vault/local_abc/p4-output-contract-diagnostic-pass-v2")
REQUEST_ORDER: Final = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "F",
    "E",
    "D",
    "C",
    "B",
    "A",
    "C",
    "D",
    "E",
    "F",
    "A",
    "B",
)
ELIGIBLE_CASE_IDS: Final = ("A", "C", "E", "F")
INELIGIBLE_CASE_IDS: Final = ("B", "D")


class AcceptanceError(RuntimeError):
    """Fail-closed execution-acceptance error."""

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

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
            "details": list(self.details),
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AcceptanceError(
            "P4_EXECUTION_ACCEPTANCE_ARGUMENT_INVALID",
            "P4 execution-acceptance arguments are invalid",
            details=(message,),
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExternalModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class ArtifactReceipt(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class ExpectedHashes(StrictModel):
    intake_archive: str = Field(pattern=r"^[0-9a-f]{64}$")
    outer_results_zip: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption: str = Field(pattern=r"^[0-9a-f]{64}$")
    intake_manifest: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_snapshot: str = Field(pattern=r"^[0-9a-f]{64}$")


class AcceptancePolicy(StrictModel):
    schema_version: Literal["1.0.0"]
    policy_id: Literal["auragateway-p4-output-contract-diagnostic-execution-acceptance-v1-policy"]
    current_main_authority: str = Field(pattern=r"^[0-9a-f]{40}$")
    p4_v2_implementation_merge_commit: Literal["d61a146a2503a5e6bfd3fadbf1dad65dcad402ac"]
    issuer_merge_commit: Literal["426992050f7112818a83a4db094346d155718933"]
    saved_version_id: Literal[340775383]
    lifecycle_outcome: Literal["PASSED"]
    evidence_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    selected_case_id: Literal["A"]
    eligible_case_ids: tuple[str, ...]
    ineligible_case_ids: tuple[str, ...]
    first_divergence: None
    reported_failure_code: None
    model_requests: Literal[18]
    measured_abc_execution: Literal[False]
    next_gate: Literal["design_and_merge_measured_abc_execution_authorization_v1"]
    expected_hashes: ExpectedHashes
    evidence_receipt_count: int = Field(gt=0)
    evidence_receipts: tuple[ArtifactReceipt, ...]
    repository_authority_count: int = Field(gt=0)
    repository_authorities: tuple[ArtifactReceipt, ...]
    runtime_member_targets: dict[str, str]
    intake_member_targets: dict[str, str]
    expected_runtime_member_count: Literal[17]
    expected_intake_mapped_member_count: Literal[21]
    expected_intake_archive_member_count: Literal[22]
    expected_outer_results_member_count: Literal[17]
    expected_terminal_log_tokens: tuple[str, ...]
    operational_transient_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_fixed_contract(self) -> Self:
        if self.eligible_case_ids != ELIGIBLE_CASE_IDS:
            raise ValueError("eligible case IDs drifted")
        if self.ineligible_case_ids != INELIGIBLE_CASE_IDS:
            raise ValueError("ineligible case IDs drifted")
        if len(self.evidence_receipts) != self.evidence_receipt_count:
            raise ValueError("evidence receipt count drifted")
        if len(self.repository_authorities) != self.repository_authority_count:
            raise ValueError("repository authority count drifted")
        if len(self.runtime_member_targets) != self.expected_runtime_member_count:
            raise ValueError("runtime member target count drifted")
        if len(self.intake_member_targets) != self.expected_intake_mapped_member_count:
            raise ValueError("intake member target count drifted")
        if len(self.expected_terminal_log_tokens) != 6:
            raise ValueError("terminal log token count drifted")
        if len(self.operational_transient_paths) != 2:
            raise ValueError("transient lifecycle path count drifted")
        return self


class ActionCounters(StrictModel):
    benchmark_trajectory_requests: Literal[0]
    external_spend: Literal[0]
    hidden_retries: Literal[0]
    kaggle_sessions: Literal[1]
    model_loads: Literal[1]
    model_requests: Literal[18]
    network_requests: Literal[0]
    runtime_import_closure_probes: Literal[1]
    runtime_install_attempts: Literal[1]
    worker_starts: Literal[1]


class DiagnosticSummary(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    counters: ActionCounters
    first_divergence: None
    inspection_evidence_sha256: Literal[
        "ea54b6ec59bd3a73be20fec04aa56ca9f3f4af58f8499ec2962a66f152180849"
    ]
    inspection_saved_version: Literal[340657269]
    reported_failure_code: None
    request_count: Literal[18]
    selected_case_id: Literal["A"]


class SelectionReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["SELECTED"]
    eligible_case_ids: tuple[str, ...]
    selected_case_id: Literal["A"]
    selection_rule: str

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        if self.eligible_case_ids != ELIGIBLE_CASE_IDS:
            raise ValueError("eligible case IDs drifted")
        expected = (
            "3/3 exact-object responses, one response hash, and zero request errors; "
            "prefer the least constraining configuration."
        )
        if self.selection_rule != expected:
            raise ValueError("selection rule drifted")
        return self


class CaseMetric(StrictModel):
    case_id: str
    attempt_count: Literal[3]
    completed_count: Literal[3]
    exact_object_count: int
    exact_object_rate: float
    valid_json_count: int
    valid_json_rate: float
    request_error_count: Literal[0]
    response_hash_cardinality: Literal[1]
    completion_token_distribution: dict[str, int]
    failure_category_distribution: dict[str, int]
    finish_reason_distribution: dict[str, int]


class CaseMetrics(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["COMPLETE"]
    cases: tuple[CaseMetric, ...]


class RequestResult(ExternalModel):
    sequence_index: int
    case_id: str
    status: Literal["COMPLETED"]
    http_status: Literal[200]
    exact_object: bool
    valid_json: bool
    failure_category: str | None
    markdown_fence_detected: bool
    raw_output_retained: Literal[False]
    raw_prompt_retained: Literal[False]
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RequestResults(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["COMPLETE"]
    scheduled_request_count: Literal[18]
    observed_request_count: Literal[18]
    results: tuple[RequestResult, ...]


class RuntimeSourceIdentity(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    notebook_name: Literal["ag-p4-output-contract-diagnostic-v2"]
    executed_runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ModelSnapshotReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    governed_model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    file_count: Literal[10]
    total_bytes: int = Field(gt=0)


class WheelhouseReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    exact_manifest_closure_verified: Literal[True]
    manifest_entry_count: Literal[182]
    wheel_count: Literal[176]


class RuntimeInstallReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    return_code: Literal[0]
    installer_contract: Literal["HASH_LOCKED_OFFLINE_TARGET_INSTALL"]
    network_access_requested: Literal[False]
    raw_install_output_retained: Literal[False]
    duration_ms: int = Field(gt=0)


class RuntimeImportClosureReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    decision: Literal["NATIVE_HARDENED_IMPORT_CLOSURE_PASSED"]
    return_code: Literal[0]
    network_access_requested: Literal[False]
    raw_import_output_retained: Literal[False]
    timed_out: Literal[False]
    model_loads_consumed: Literal[0]
    worker_starts_consumed: Literal[0]
    versions: dict[str, str]


class RequiredTargetOrigin(StrictModel):
    observed: Literal[True]
    all_from_target: Literal[True]


class NativeOriginReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    prohibited_origin_count: Literal[0]
    required_target_origins: dict[str, RequiredTargetOrigin]
    observations: tuple[dict[str, object], ...]


class WorkerStartupReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    backend_marker: str
    gpu_index: Literal[0]
    request_logging_disabled: Literal[True]
    raw_worker_logs_retained: Literal[False]
    environment: dict[str, object]


class WorkerTeardownReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    capture_threads_finalized: Literal[True]
    port_closed: Literal[True]
    process_absent: Literal[True]
    surviving_descendant_pids: tuple[int, ...]
    error_types: tuple[str, ...]


class ScratchCleanupReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    scratch_absent: Literal[True]
    error_type: None


class FailureReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["NOT_APPLICABLE"]
    error_code: None


class ManifestMember(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class BundleManifest(ExternalModel):
    schema_version: Literal["1.0.0"]
    member_count: Literal[15]
    members: tuple[ManifestMember, ...]
    raw_output_included: Literal[False]


class AuthorizationEvidence(ExternalModel):
    schema_version: Literal["3.0.0"]
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v3"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2"]
    issued_from_main_commit: Literal["426992050f7112818a83a4db094346d155718933"]
    issued_at: datetime
    expires_at: datetime
    runtime_execution_authorized: Literal[True]
    single_use: Literal[True]
    every_terminal_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]


class ConsumptionEvidence(ExternalModel):
    schema_version: Literal["3.0.0"]
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v3"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["PASSED"]
    saved_version_id: Literal[340775383]
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False]


class IntakeMember(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class IntakeManifest(StrictModel):
    schema_version: Literal["1.0.0"]
    intake_id: Literal["auragateway-p4-output-contract-diagnostic-v2-pass-340775383"]
    saved_version_id: Literal[340775383]
    execution_outcome: Literal["PASSED"]
    selected_case_id: Literal["A"]
    model_requests: Literal[18]
    measured_abc_execution: Literal[False]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outer_results_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    governed_evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    members: tuple[IntakeMember, ...]


class LimitationsEvidence(StrictModel):
    schema_version: Literal["1.0.0"]
    saved_version_id: Literal[340775383]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]


def _canonical(payload: object) -> str:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _require(
    condition: bool,
    error_code: str,
    safe_message: str,
    path: Path | None = None,
    details: tuple[str, ...] = (),
) -> None:
    if condition:
        return
    raise AcceptanceError(
        error_code,
        safe_message,
        path.as_posix() if path is not None else None,
        details,
    )


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceError(
            "P4_EXECUTION_ACCEPTANCE_JSON_INVALID",
            "required JSON could not be loaded",
            path.as_posix(),
        ) from error


def _load_model(model: type[BaseModel], path: Path) -> BaseModel:
    try:
        return model.model_validate(_read_json(path))
    except ValidationError as error:
        raise AcceptanceError(
            "P4_EXECUTION_ACCEPTANCE_SCHEMA_INVALID",
            "evidence schema validation failed",
            path.as_posix(),
        ) from error


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        _canonical(payload),
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def _load_policy(root: Path) -> AcceptancePolicy:
    path = root / POLICY_PATH
    _require(
        path.is_file(),
        "P4_EXECUTION_ACCEPTANCE_POLICY_MISSING",
        "execution-acceptance policy is missing",
        POLICY_PATH,
    )
    _require(
        _file_sha256(path) == POLICY_SHA256,
        "P4_EXECUTION_ACCEPTANCE_POLICY_IDENTITY_DRIFT",
        "execution-acceptance policy identity drifted",
        POLICY_PATH,
    )
    try:
        return AcceptancePolicy.model_validate(_read_json(path))
    except ValidationError as error:
        raise AcceptanceError(
            "P4_EXECUTION_ACCEPTANCE_POLICY_INVALID",
            "execution-acceptance policy validation failed",
            POLICY_PATH.as_posix(),
        ) from error


def _artifact_receipt(root: Path, relative: Path) -> ArtifactReceipt:
    path = root / relative
    _require(
        path.is_file() and not path.is_symlink(),
        "P4_EXECUTION_ACCEPTANCE_ARTIFACT_MISSING",
        "required acceptance artifact is missing or unsafe",
        relative,
    )
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_file_sha256(path),
        size_bytes=path.stat().st_size,
    )


def _git_blob(root: Path, relative: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"HEAD:{relative}"],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AcceptanceError(
            "P4_EXECUTION_ACCEPTANCE_GIT_FAILED",
            "repository authority could not be read",
            relative,
        ) from error
    _require(
        result.returncode == 0,
        "P4_EXECUTION_ACCEPTANCE_GIT_FAILED",
        "repository authority could not be read",
        Path(relative),
    )
    return result.stdout


def _validate_repository_authorities(
    root: Path,
    policy: AcceptancePolicy,
) -> None:
    for receipt in policy.repository_authorities:
        payload = _git_blob(root, receipt.path)
        _require(
            _sha256_bytes(payload) == receipt.sha256 and len(payload) == receipt.size_bytes,
            "P4_EXECUTION_ACCEPTANCE_REPOSITORY_AUTHORITY_DRIFT",
            "repository authority identity drifted",
            Path(receipt.path),
        )
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                policy.current_main_authority,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AcceptanceError(
            "P4_EXECUTION_ACCEPTANCE_ANCESTRY_UNREADABLE",
            "main authority ancestry could not be inspected",
        ) from error
    _require(
        result.returncode == 0,
        "P4_EXECUTION_ACCEPTANCE_MAIN_AUTHORITY_MISSING",
        "accepted execution main authority is not an ancestor of HEAD",
    )


def _validate_evidence_receipts(
    root: Path,
    policy: AcceptancePolicy,
) -> None:
    seen: set[str] = set()
    for receipt in policy.evidence_receipts:
        _require(
            receipt.path not in seen,
            "P4_EXECUTION_ACCEPTANCE_DUPLICATE_RECEIPT",
            "duplicate evidence receipt path",
        )
        seen.add(receipt.path)
        observed = _artifact_receipt(root, Path(receipt.path))
        _require(
            observed == receipt,
            "P4_EXECUTION_ACCEPTANCE_EVIDENCE_RECEIPT_DRIFT",
            "evidence receipt drifted",
            Path(receipt.path),
        )


def _normalize_zip_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    _require(
        not path.is_absolute(),
        "P4_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member is absolute",
    )
    _require(
        ".." not in path.parts,
        "P4_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member escapes archive root",
    )
    _require(
        re.match(r"^[A-Za-z]:", normalized) is None,
        "P4_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member has a drive prefix",
    )
    return path.as_posix()


def _safe_zip_members(path: Path) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            members: dict[str, bytes] = {}
            for info in archive.infolist():
                if info.is_dir():
                    continue
                mode = (info.external_attr >> 16) & 0o170000
                _require(
                    mode != stat.S_IFLNK,
                    "P4_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE",
                    "archive member is a symbolic link",
                    path,
                )
                normalized = _normalize_zip_name(info.filename)
                _require(
                    normalized not in members,
                    "P4_EXECUTION_ACCEPTANCE_ARCHIVE_DUPLICATE",
                    "archive contains a duplicate normalized member",
                    path,
                )
                members[normalized] = archive.read(info)
            return members
    except (OSError, zipfile.BadZipFile) as error:
        raise AcceptanceError(
            "P4_EXECUTION_ACCEPTANCE_ARCHIVE_INVALID",
            "evidence archive is invalid",
            path.as_posix(),
        ) from error


def _evidence_path(policy: AcceptancePolicy, filename: str) -> Path:
    matches = [
        Path(receipt.path)
        for receipt in policy.evidence_receipts
        if Path(receipt.path).name == filename
    ]
    _require(
        len(matches) == 1,
        "P4_EXECUTION_ACCEPTANCE_EVIDENCE_PATH_AMBIGUOUS",
        "evidence path is missing or ambiguous",
        details=(filename,),
    )
    return matches[0]


def _runtime_target(policy: AcceptancePolicy, source_name: str) -> Path:
    target = policy.runtime_member_targets.get(source_name)
    _require(
        isinstance(target, str),
        "P4_EXECUTION_ACCEPTANCE_RUNTIME_TARGET_MISSING",
        "runtime evidence target is missing",
        details=(source_name,),
    )
    return Path(cast(str, target))


def _validate_intake_archive(
    root: Path,
    policy: AcceptancePolicy,
) -> dict[str, bytes]:
    intake_name = "AuraGateway_P4_Output_Contract_Diagnostic_V2_Pass_Intake_340775383.zip"
    intake_path = root / _evidence_path(policy, intake_name)
    members = _safe_zip_members(intake_path)
    _require(
        len(members) == policy.expected_intake_archive_member_count,
        "P4_EXECUTION_ACCEPTANCE_INTAKE_BOUNDARY_DRIFT",
        "intake archive member count drifted",
        intake_path,
    )
    expected = set(policy.intake_member_targets)
    expected.add("kaggle_results_340775383.zip")
    _require(
        set(members) == expected,
        "P4_EXECUTION_ACCEPTANCE_INTAKE_BOUNDARY_DRIFT",
        "intake archive member boundary drifted",
        intake_path,
    )
    for source_name, target in policy.intake_member_targets.items():
        _require(
            members[source_name] == (root / target).read_bytes(),
            "P4_EXECUTION_ACCEPTANCE_INTAKE_BYTE_DRIFT",
            "intake archive member bytes differ from preserved evidence",
            Path(target),
        )
    outer_results = members["kaggle_results_340775383.zip"]
    _require(
        _sha256_bytes(outer_results) == policy.expected_hashes.outer_results_zip,
        "P4_EXECUTION_ACCEPTANCE_OUTER_RESULTS_DRIFT",
        "outer Kaggle results ZIP identity drifted",
        intake_path,
    )
    _validate_outer_results(root, policy, outer_results)
    return members


def _validate_outer_results(
    root: Path,
    policy: AcceptancePolicy,
    payload: bytes,
) -> None:
    temporary = root / ".p4-execution-acceptance-outer-results.tmp.zip"
    try:
        temporary.write_bytes(payload)
        members = _safe_zip_members(temporary)
    finally:
        temporary.unlink(missing_ok=True)
    _require(
        len(members) == policy.expected_outer_results_member_count,
        "P4_EXECUTION_ACCEPTANCE_OUTER_RESULTS_BOUNDARY_DRIFT",
        "outer Kaggle results member count drifted",
    )
    prefix = "p4_output_contract_diagnostic_v2/"
    expected = {prefix + name for name in policy.runtime_member_targets}
    _require(
        set(members) == expected,
        "P4_EXECUTION_ACCEPTANCE_OUTER_RESULTS_BOUNDARY_DRIFT",
        "outer Kaggle results member boundary drifted",
    )
    for source_name, target in policy.runtime_member_targets.items():
        _require(
            members[prefix + source_name] == (root / target).read_bytes(),
            "P4_EXECUTION_ACCEPTANCE_OUTER_RESULTS_BYTE_DRIFT",
            "outer results member bytes differ from preserved evidence",
            Path(target),
        )


def _validate_runtime_evidence_zip(
    root: Path,
    policy: AcceptancePolicy,
) -> None:
    evidence_zip = root / _runtime_target(
        policy,
        "ag-p4-output-contract-evidence-v2.zip",
    )
    members = _safe_zip_members(evidence_zip)
    expected = {
        name
        for name in policy.runtime_member_targets
        if name != "ag-p4-output-contract-evidence-v2.zip"
    }
    _require(
        set(members) == expected,
        "P4_EXECUTION_ACCEPTANCE_RUNTIME_ZIP_BOUNDARY_DRIFT",
        "governed evidence ZIP member boundary drifted",
        evidence_zip,
    )
    for name in expected:
        target = _runtime_target(policy, name)
        _require(
            members[name] == (root / target).read_bytes(),
            "P4_EXECUTION_ACCEPTANCE_RUNTIME_ZIP_BYTE_DRIFT",
            "governed evidence ZIP member bytes drifted",
            target,
        )


def _validate_runtime_manifest(
    root: Path,
    policy: AcceptancePolicy,
) -> None:
    path = root / _runtime_target(policy, "bundle_manifest_v2.json")
    manifest = cast(BundleManifest, _load_model(BundleManifest, path))
    expected_names = {
        name
        for name in policy.runtime_member_targets
        if name
        not in {
            "bundle_manifest_v2.json",
            "ag-p4-output-contract-evidence-v2.zip",
        }
    }
    observed_names = {member.path for member in manifest.members}
    _require(
        observed_names == expected_names,
        "P4_EXECUTION_ACCEPTANCE_MANIFEST_BOUNDARY_DRIFT",
        "runtime bundle manifest boundary drifted",
        path,
    )
    by_name = {member.path: member for member in manifest.members}
    for name in expected_names:
        target = _runtime_target(policy, name)
        receipt = _artifact_receipt(root, target)
        member = by_name[name]
        _require(
            member.sha256 == receipt.sha256 and member.size_bytes == receipt.size_bytes,
            "P4_EXECUTION_ACCEPTANCE_MANIFEST_RECEIPT_DRIFT",
            "runtime bundle manifest receipt drifted",
            target,
        )


def _validate_intake_manifest(
    root: Path,
    policy: AcceptancePolicy,
    intake_members: dict[str, bytes],
) -> None:
    path = root / _evidence_path(
        policy,
        "intake_manifest_v1-340775383.json",
    )
    manifest = cast(IntakeManifest, _load_model(IntakeManifest, path))
    expected_hashes = policy.expected_hashes
    _require(
        manifest.authorization_sha256 == expected_hashes.authorization,
        "P4_EXECUTION_ACCEPTANCE_INTAKE_MANIFEST_DRIFT",
        "intake authorization identity drifted",
        path,
    )
    _require(
        manifest.terminal_log_sha256 == expected_hashes.terminal_log,
        "P4_EXECUTION_ACCEPTANCE_INTAKE_MANIFEST_DRIFT",
        "intake terminal-log identity drifted",
        path,
    )
    _require(
        manifest.outer_results_zip_sha256 == expected_hashes.outer_results_zip,
        "P4_EXECUTION_ACCEPTANCE_INTAKE_MANIFEST_DRIFT",
        "intake outer-results identity drifted",
        path,
    )
    _require(
        manifest.governed_evidence_zip_sha256 == expected_hashes.evidence_zip,
        "P4_EXECUTION_ACCEPTANCE_INTAKE_MANIFEST_DRIFT",
        "intake governed evidence identity drifted",
        path,
    )
    _require(
        len(manifest.members) == 21,
        "P4_EXECUTION_ACCEPTANCE_INTAKE_MANIFEST_COUNT_DRIFT",
        "intake manifest receipt count drifted",
        path,
    )
    for member in manifest.members:
        observed = intake_members.get(member.path)
        _require(
            observed is not None,
            "P4_EXECUTION_ACCEPTANCE_INTAKE_MANIFEST_MEMBER_MISSING",
            "intake manifest member is missing",
            path,
            (member.path,),
        )
        payload = cast(bytes, observed)
        _require(
            _sha256_bytes(payload) == member.sha256 and len(payload) == member.size_bytes,
            "P4_EXECUTION_ACCEPTANCE_INTAKE_MANIFEST_RECEIPT_DRIFT",
            "intake manifest member receipt drifted",
            path,
            (member.path,),
        )


def _validate_lifecycle(root: Path, policy: AcceptancePolicy) -> None:
    authorization_path = root / _evidence_path(
        policy,
        "execution_authorization_v3-340775383.json",
    )
    consumption_path = root / _evidence_path(
        policy,
        "execution_authorization_consumption_v3-340775383.json",
    )
    authorization = cast(
        AuthorizationEvidence,
        _load_model(AuthorizationEvidence, authorization_path),
    )
    consumption = cast(
        ConsumptionEvidence,
        _load_model(ConsumptionEvidence, consumption_path),
    )
    _require(
        _file_sha256(authorization_path) == policy.expected_hashes.authorization,
        "P4_EXECUTION_ACCEPTANCE_AUTHORIZATION_DRIFT",
        "authorization evidence identity drifted",
        authorization_path,
    )
    _require(
        _file_sha256(consumption_path) == policy.expected_hashes.consumption,
        "P4_EXECUTION_ACCEPTANCE_CONSUMPTION_DRIFT",
        "consumption evidence identity drifted",
        consumption_path,
    )
    _require(
        consumption.authorization_sha256 == policy.expected_hashes.authorization,
        "P4_EXECUTION_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption receipt does not bind the accepted authorization",
        consumption_path,
    )
    _require(
        consumption.evidence_zip_sha256 == policy.expected_hashes.evidence_zip,
        "P4_EXECUTION_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption receipt does not bind the governed evidence ZIP",
        consumption_path,
    )
    _require(
        consumption.terminal_log_sha256 == policy.expected_hashes.terminal_log,
        "P4_EXECUTION_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption receipt does not bind the terminal log",
        consumption_path,
    )
    consumed_at = consumption_path_time(consumption_path)
    _require(
        authorization.issued_at < consumed_at <= authorization.expires_at,
        "P4_EXECUTION_ACCEPTANCE_LIFECYCLE_TIME_DRIFT",
        "consumption timestamp is outside the issued authorization window",
        consumption_path,
    )


def consumption_path_time(path: Path) -> datetime:
    payload = cast(dict[str, object], _read_json(path))
    value = payload.get("consumed_at")
    _require(
        isinstance(value, str),
        "P4_EXECUTION_ACCEPTANCE_LIFECYCLE_TIME_INVALID",
        "consumption timestamp is invalid",
        path,
    )
    return datetime.fromisoformat(cast(str, value).replace("Z", "+00:00"))


def _validate_case_metrics(root: Path, policy: AcceptancePolicy) -> None:
    path = root / _runtime_target(policy, "case_metrics_v2.json")
    metrics = cast(CaseMetrics, _load_model(CaseMetrics, path))
    _require(
        tuple(metric.case_id for metric in metrics.cases) == ("A", "B", "C", "D", "E", "F"),
        "P4_EXECUTION_ACCEPTANCE_CASE_ORDER_DRIFT",
        "case metrics order drifted",
        path,
    )
    by_case = {metric.case_id: metric for metric in metrics.cases}
    for case_id in ELIGIBLE_CASE_IDS:
        metric = by_case[case_id]
        _require(
            metric.exact_object_count == 3
            and metric.exact_object_rate == 1.0
            and metric.valid_json_count == 3
            and metric.valid_json_rate == 1.0
            and metric.failure_category_distribution == {"None": 3},
            "P4_EXECUTION_ACCEPTANCE_ELIGIBLE_CASE_DRIFT",
            "eligible case metrics drifted",
            path,
            (case_id,),
        )
    for case_id in INELIGIBLE_CASE_IDS:
        metric = by_case[case_id]
        _require(
            metric.exact_object_count == 0
            and metric.exact_object_rate == 0.0
            and metric.valid_json_count == 0
            and metric.valid_json_rate == 0.0
            and metric.failure_category_distribution
            == {"REQUEST_COMPLETED_OUTPUT_INVALID_JSON": 3},
            "P4_EXECUTION_ACCEPTANCE_INELIGIBLE_CASE_DRIFT",
            "ineligible case metrics drifted",
            path,
            (case_id,),
        )


def _validate_request_results(root: Path, policy: AcceptancePolicy) -> None:
    path = root / _runtime_target(policy, "request_results_v2.json")
    results = cast(RequestResults, _load_model(RequestResults, path))
    _require(
        len(results.results) == 18,
        "P4_EXECUTION_ACCEPTANCE_REQUEST_COUNT_DRIFT",
        "request result count drifted",
        path,
    )
    observed_order = tuple(result.case_id for result in results.results)
    _require(
        observed_order == REQUEST_ORDER,
        "P4_EXECUTION_ACCEPTANCE_REQUEST_ORDER_DRIFT",
        "request result order drifted",
        path,
    )
    for index, result in enumerate(results.results, start=1):
        _require(
            result.sequence_index == index,
            "P4_EXECUTION_ACCEPTANCE_REQUEST_SEQUENCE_DRIFT",
            "request sequence index drifted",
            path,
        )
        if result.case_id in ELIGIBLE_CASE_IDS:
            _require(
                result.exact_object
                and result.valid_json
                and result.failure_category is None
                and not result.markdown_fence_detected,
                "P4_EXECUTION_ACCEPTANCE_ELIGIBLE_REQUEST_DRIFT",
                "eligible-case request result drifted",
                path,
                (result.case_id, str(index)),
            )
        else:
            _require(
                not result.exact_object
                and not result.valid_json
                and result.failure_category == "REQUEST_COMPLETED_OUTPUT_INVALID_JSON"
                and result.markdown_fence_detected,
                "P4_EXECUTION_ACCEPTANCE_INELIGIBLE_REQUEST_DRIFT",
                "ineligible-case request result drifted",
                path,
                (result.case_id, str(index)),
            )


def _validate_runtime_semantics(root: Path, policy: AcceptancePolicy) -> None:
    summary_path = root / _runtime_target(
        policy,
        "p4_output_contract_diagnostic_summary_v2.json",
    )
    summary = cast(
        DiagnosticSummary,
        _load_model(DiagnosticSummary, summary_path),
    )
    selection = cast(
        SelectionReport,
        _load_model(
            SelectionReport,
            root / _runtime_target(policy, "selection_report_v2.json"),
        ),
    )
    _require(
        selection.selected_case_id == summary.selected_case_id,
        "P4_EXECUTION_ACCEPTANCE_SELECTION_DRIFT",
        "summary and selection report disagree",
    )
    _validate_case_metrics(root, policy)
    _validate_request_results(root, policy)

    source = cast(
        RuntimeSourceIdentity,
        _load_model(
            RuntimeSourceIdentity,
            root
            / _runtime_target(
                policy,
                "runtime_source_identity_report_v2.json",
            ),
        ),
    )
    _require(
        source.executed_runtime_script_sha256 == policy.expected_hashes.runtime_script,
        "P4_EXECUTION_ACCEPTANCE_RUNTIME_SCRIPT_DRIFT",
        "executed runtime script identity drifted",
    )

    model = cast(
        ModelSnapshotReport,
        _load_model(
            ModelSnapshotReport,
            root / _runtime_target(policy, "model_snapshot_report_v2.json"),
        ),
    )
    _require(
        model.governed_model_snapshot_sha256 == policy.expected_hashes.model_snapshot,
        "P4_EXECUTION_ACCEPTANCE_MODEL_SNAPSHOT_DRIFT",
        "model snapshot identity drifted",
    )

    cast(
        WheelhouseReport,
        _load_model(
            WheelhouseReport,
            root / _runtime_target(policy, "wheelhouse_report_v2.json"),
        ),
    )
    cast(
        RuntimeInstallReport,
        _load_model(
            RuntimeInstallReport,
            root / _runtime_target(policy, "runtime_install_report_v2.json"),
        ),
    )
    import_report = cast(
        RuntimeImportClosureReport,
        _load_model(
            RuntimeImportClosureReport,
            root
            / _runtime_target(
                policy,
                "runtime_import_closure_report_v2.json",
            ),
        ),
    )
    expected_versions = {
        "cuda": "12.9",
        "tokenizers": "0.22.2",
        "torch": "2.10.0+cu129",
        "transformers": "5.5.3",
        "triton": "3.6.0",
        "vllm": "0.19.1",
    }
    _require(
        import_report.versions == expected_versions,
        "P4_EXECUTION_ACCEPTANCE_IMPORT_VERSION_DRIFT",
        "import-closure package versions drifted",
    )

    origin = cast(
        NativeOriginReport,
        _load_model(
            NativeOriginReport,
            root
            / _runtime_target(
                policy,
                "runtime_native_origin_report_v2.json",
            ),
        ),
    )
    _require(
        set(origin.required_target_origins) == {"libcusparse", "libnvJitLink"},
        "P4_EXECUTION_ACCEPTANCE_NATIVE_ORIGIN_DRIFT",
        "required target-native origin set drifted",
    )

    startup = cast(
        WorkerStartupReport,
        _load_model(
            WorkerStartupReport,
            root / _runtime_target(policy, "worker_startup_report_v2.json"),
        ),
    )
    _require(
        "TRITON_ATTN" in startup.backend_marker,
        "P4_EXECUTION_ACCEPTANCE_BACKEND_DRIFT",
        "worker did not realize the reviewed TRITON_ATTN backend",
    )
    _require(
        startup.environment.get("prohibited_stub_path_present") is False,
        "P4_EXECUTION_ACCEPTANCE_NATIVE_ENVIRONMENT_DRIFT",
        "prohibited CUDA stub path was present",
    )
    _require(
        startup.environment.get("pythonpath_exact_target_site") is True,
        "P4_EXECUTION_ACCEPTANCE_NATIVE_ENVIRONMENT_DRIFT",
        "worker PYTHONPATH did not realize exact target site",
    )

    teardown = cast(
        WorkerTeardownReport,
        _load_model(
            WorkerTeardownReport,
            root / _runtime_target(policy, "worker_teardown_report_v2.json"),
        ),
    )
    _require(
        not teardown.surviving_descendant_pids and not teardown.error_types,
        "P4_EXECUTION_ACCEPTANCE_TEARDOWN_DRIFT",
        "worker teardown left residual evidence",
    )
    cast(
        ScratchCleanupReport,
        _load_model(
            ScratchCleanupReport,
            root / _runtime_target(policy, "scratch_cleanup_report_v2.json"),
        ),
    )
    cast(
        FailureReport,
        _load_model(
            FailureReport,
            root / _runtime_target(policy, "failure_report_v2.json"),
        ),
    )


def _validate_logs_and_limits(root: Path, policy: AcceptancePolicy) -> None:
    log_path = root / _evidence_path(
        policy,
        "ag-p4-output-contract-diagnostic-v2-340775383.log",
    )
    text = log_path.read_text(encoding="utf-8")
    for token in policy.expected_terminal_log_tokens:
        _require(
            token in text,
            "P4_EXECUTION_ACCEPTANCE_TERMINAL_TOKEN_MISSING",
            "required terminal certificate token is missing",
            log_path,
            (token,),
        )
    limitations_path = root / _evidence_path(
        policy,
        "evidence_limitations_v1-340775383.json",
    )
    limitations = cast(
        LimitationsEvidence,
        _load_model(LimitationsEvidence, limitations_path),
    )
    _require(
        len(limitations.limitations) >= 7,
        "P4_EXECUTION_ACCEPTANCE_LIMITATIONS_INCOMPLETE",
        "evidence limitations are incomplete",
        limitations_path,
    )
    _require(
        len(limitations.non_claims) >= 8,
        "P4_EXECUTION_ACCEPTANCE_NON_CLAIMS_INCOMPLETE",
        "evidence non-claims are incomplete",
        limitations_path,
    )


def _validate_transient_paths_absent(
    root: Path,
    policy: AcceptancePolicy,
) -> None:
    present = [path for path in policy.operational_transient_paths if (root / path).exists()]
    _require(
        not present,
        "P4_EXECUTION_ACCEPTANCE_TRANSIENT_PATH_PRESENT",
        "live authorization lifecycle artifacts must be absent",
        details=tuple(present),
    )


def validate_evidence(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    _validate_repository_authorities(root, policy)
    _validate_evidence_receipts(root, policy)
    intake_members = _validate_intake_archive(root, policy)
    _validate_intake_manifest(root, policy, intake_members)
    _validate_runtime_evidence_zip(root, policy)
    _validate_runtime_manifest(root, policy)
    _validate_lifecycle(root, policy)
    _validate_runtime_semantics(root, policy)
    _validate_logs_and_limits(root, policy)
    _validate_transient_paths_absent(root, policy)
    return {
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_EVIDENCE_VALID",
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": policy.lifecycle_outcome,
        "evidence_disposition": policy.evidence_disposition,
        "selected_case_id": policy.selected_case_id,
        "eligible_case_ids": list(policy.eligible_case_ids),
        "ineligible_case_ids": list(policy.ineligible_case_ids),
        "first_divergence": None,
        "model_requests": 18,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_established": False,
        "measured_abc_execution_authorized": False,
        "next_gate": policy.next_gate,
    }


def _non_claims() -> list[str]:
    return [
        "This acceptance covers one governed saved version only.",
        "General model reliability is not established.",
        "Cross-run stability is not established.",
        "Production readiness is not established.",
        "Deployment readiness is not established.",
        "Measured A/B/C execution was not performed.",
        "Measured A/B/C execution is not authorized by this acceptance.",
        "All CUDA libraries are not claimed to originate from the target runtime.",
        "The ambient Kaggle Python environment is not claimed conflict free.",
        "Cases B and D do not satisfy the exact-object criterion in this run.",
        "JSON-schema compatibility is not generalized beyond cases E and F.",
    ]


def build_review(policy: AcceptancePolicy) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "review_id": ("auragateway-p4-output-contract-diagnostic-execution-acceptance-v1-review"),
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_CLASSIFIED",
        "decision": ("ACCEPT_GOVERNED_PASS_AND_SELECT_CASE_A_FOR_NEXT_MEASURED_ABC_DESIGN"),
        "current_main_authority": policy.current_main_authority,
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "PASSED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "evidence_disposition": policy.evidence_disposition,
        "first_divergence": None,
        "reported_failure_code": None,
        "runtime_source_identity_status": "PASSED",
        "model_snapshot_status": "PASSED",
        "wheelhouse_status": "PASSED",
        "runtime_install_status": "PASSED",
        "runtime_import_closure_status": "PASSED",
        "runtime_native_origin_status": "PASSED",
        "worker_startup_status": "PASSED",
        "request_matrix_status": "COMPLETE",
        "worker_teardown_status": "PASSED",
        "scratch_cleanup_status": "PASSED",
        "model_loads": 1,
        "worker_starts": 1,
        "model_requests": 18,
        "selected_case_id": "A",
        "selected_case": {
            "prompt_variant": "V4",
            "repetition_penalty": 1.1,
            "output_mode": "UNCONSTRAINED",
        },
        "eligible_case_ids": list(ELIGIBLE_CASE_IDS),
        "ineligible_case_ids": list(INELIGIBLE_CASE_IDS),
        "ineligible_case_failure_category": ("REQUEST_COMPLETED_OUTPUT_INVALID_JSON"),
        "p4_output_contract_diagnostic_established": True,
        "json_schema_mode_compatibility_observed": True,
        "measured_abc_execution_established": False,
        "measured_abc_execution_authorized": False,
        "runtime_execution_authorized": False,
        "next_gate": policy.next_gate,
        "non_claims": _non_claims(),
    }


def build_record(
    root: Path,
    policy: AcceptancePolicy,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_id": ("auragateway-p4-output-contract-diagnostic-execution-acceptance-v1"),
        "status": ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_ACCEPTANCE_V1_VALID"),
        "current_main_authority": policy.current_main_authority,
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "PASSED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "evidence_disposition": policy.evidence_disposition,
        "first_divergence": None,
        "reported_failure_code": None,
        "selected_case_id": "A",
        "eligible_case_ids": list(ELIGIBLE_CASE_IDS),
        "ineligible_case_ids": list(INELIGIBLE_CASE_IDS),
        "model_loads": 1,
        "worker_starts": 1,
        "model_requests": 18,
        "p4_output_contract_diagnostic_established": True,
        "json_schema_mode_compatibility_observed": True,
        "measured_abc_execution_established": False,
        "measured_abc_execution_authorized": False,
        "runtime_execution_authorized": False,
        "policy": _artifact_receipt(root, POLICY_PATH).model_dump(mode="json"),
        "source": _artifact_receipt(root, SOURCE_PATH).model_dump(mode="json"),
        "tests": _artifact_receipt(root, TEST_PATH).model_dump(mode="json"),
        "adr": _artifact_receipt(root, ADR_PATH).model_dump(mode="json"),
        "report": _artifact_receipt(root, REPORT_PATH).model_dump(mode="json"),
        "runbook": _artifact_receipt(root, RUNBOOK_PATH).model_dump(mode="json"),
        "review": _artifact_receipt(root, REVIEW_PATH).model_dump(mode="json"),
        "repository_authorities": [
            receipt.model_dump(mode="json") for receipt in policy.repository_authorities
        ],
        "evidence": [receipt.model_dump(mode="json") for receipt in policy.evidence_receipts],
        "next_gate": policy.next_gate,
        "non_claims": _non_claims(),
    }


def generate(root: Path) -> dict[str, object]:
    resolved = root.resolve()
    policy = _load_policy(resolved)
    evidence = validate_evidence(resolved)
    _write_json(resolved / REVIEW_PATH, build_review(policy))
    _write_json(resolved / RECORD_PATH, build_record(resolved, policy))
    return {
        "status": ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_ACCEPTANCE_V1_GENERATED"),
        "saved_version_id": policy.saved_version_id,
        "review_sha256": _file_sha256(resolved / REVIEW_PATH),
        "record_sha256": _file_sha256(resolved / RECORD_PATH),
        "evidence_status": evidence["status"],
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
    }


def validate_package(root: Path) -> dict[str, object]:
    resolved = root.resolve()
    policy = _load_policy(resolved)
    evidence = validate_evidence(resolved)
    expected_review = _canonical(build_review(policy))
    review_path = resolved / REVIEW_PATH
    _require(
        review_path.is_file() and review_path.read_text(encoding="utf-8") == expected_review,
        "P4_EXECUTION_ACCEPTANCE_REVIEW_DRIFT",
        "stored execution-acceptance review drifted",
        REVIEW_PATH,
    )
    expected_record = _canonical(build_record(resolved, policy))
    record_path = resolved / RECORD_PATH
    _require(
        record_path.is_file() and record_path.read_text(encoding="utf-8") == expected_record,
        "P4_EXECUTION_ACCEPTANCE_RECORD_DRIFT",
        "stored execution-acceptance record drifted",
        RECORD_PATH,
    )
    return {
        "status": ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_ACCEPTANCE_V1_VALID"),
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "PASSED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "evidence_disposition": policy.evidence_disposition,
        "selected_case_id": "A",
        "eligible_case_ids": list(ELIGIBLE_CASE_IDS),
        "ineligible_case_ids": list(INELIGIBLE_CASE_IDS),
        "p4_output_contract_diagnostic_established": True,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": policy.next_gate,
        "record_sha256": _file_sha256(record_path),
        "review_sha256": _file_sha256(review_path),
        "evidence_status": evidence["status"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="p4-output-contract-diagnostic-execution-acceptance-v1")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate-evidence", "generate", "validate-package"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        root = cast(Path, arguments.repo_root)
        command = cast(str, arguments.command)
        if command == "validate-evidence":
            result = validate_evidence(root)
        elif command == "generate":
            result = generate(root)
        else:
            result = validate_package(root)
        print(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
        return 0
    except AcceptanceError as error:
        print(
            json.dumps(
                error.envelope(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
