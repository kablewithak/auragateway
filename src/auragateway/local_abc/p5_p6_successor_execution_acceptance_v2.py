# Accept governed current-runtime P5/P6 mechanism requalification evidence.

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
from pathlib import Path, PurePosixPath
from typing import Literal, Never, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p5_p6_successor_execution_acceptance_v2_policy.json"
)
POLICY_SHA256 = "66067c0ce5f48be48db7c177c30f7daebcc8aa25fdda0cbc3836ad28e6323634"
REVIEW_PATH = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v2_review.json"
)
RECORD_PATH = Path("benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v2.json")
EVIDENCE_DIR = Path("evidence_vault/local_abc/p5-p6-mech-admission-344464549-lifecycle-r2-v1")
EVIDENCE_ZIP_NAME = "ag-p5-p6-mechanism-successor-lifecycle-r2-evidence.zip"
TERMINAL_LOG_NAME = "ag-p5-p6-mechanism-tx-lifecycle-r2.log"
EXECUTED_NOTEBOOK_NAME = "ag-p5-p6-mechanism-tx-lifecycle-r2.ipynb"
DUPLICATE_TERMINAL_EXPORT_NAME = "download-2026-08-24T002503.437.txt"
AUTHORIZATION_NAME = "authorization_live.json"
ARTIFACT_MANIFEST_NAME = "artifact_live_manifest.json"
PLATFORM_OBSERVATION_NAME = "platform_observation_live.json"
TERMINAL_AUTHORIZATION_NAME = "authorization_terminal.json"
PRESERVATION_MANIFEST_NAME = "preservation_manifest.json"
SAVED_VERSION_ID = 344464549
TRANSACTION_ID = "0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"


class AcceptanceError(RuntimeError):
    # Fail-closed governed execution-acceptance error.

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
            "P5_P6_EXECUTION_ACCEPTANCE_ARGUMENT_INVALID",
            "P5/P6 execution-acceptance arguments are invalid",
            details=(message,),
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExternalModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class ArtifactReceipt(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ExpectedHashes(StrictModel):
    authorization_live_file: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_canonical: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_live_manifest: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_observation: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_terminal: str = Field(pattern=r"^[0-9a-f]{64}$")
    preservation_manifest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log: str = Field(pattern=r"^[0-9a-f]{64}$")
    duplicate_terminal_export: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_snapshot: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExpectedSemantics(StrictModel):
    completed_capabilities: tuple[str, ...]
    model_requests: Literal[6]
    model_loads: Literal[3]
    worker_starts: Literal[3]
    runtime_install_attempts: Literal[1]
    runtime_import_closure_probes: Literal[1]
    hidden_retries: Literal[0]
    benchmark_trajectory_requests: Literal[0]
    network_requests: Literal[0]
    external_spend: Literal[0]
    measured_abc_execution_performed: Literal[False]
    pilot_execution_performed: Literal[False]
    c4_semantic_qualified: Literal[False]
    c4_semantic_state: Literal["INVALID_JSON"]
    p5_base_cold_cache_hit: Literal[0]
    p5_base_cold_local_compute: Literal[896]
    p5_base_warm_cache_hit: Literal[880]
    p5_base_warm_local_compute: Literal[16]
    p5_negative_prefix_cache_hit: Literal[16]
    p5_negative_prefix_local_compute: Literal[856]
    p5_post_reset_cache_hit: Literal[0]
    p5_post_reset_local_compute: Literal[896]
    p5_cross_worker_cache_hit: Literal[0]
    p5_cross_worker_local_compute: Literal[896]
    p6_cross_worker_cache_hit: Literal[0]
    p6_cross_worker_local_compute: Literal[896]
    p6_worker1_retention_cache_hit: Literal[880]
    p6_worker1_retention_local_compute: Literal[16]

    @model_validator(mode="after")
    def validate_capability_order(self) -> ExpectedSemantics:
        if self.completed_capabilities != ("C1", "C2", "C3", "C4", "P5", "P6"):
            raise ValueError("completed capability order drifted")
        return self


class AcceptancePolicy(StrictModel):
    schema_version: Literal["2.0.0"]
    policy_id: Literal["auragateway-p5-p6-successor-execution-acceptance-v2-policy"]
    current_main_authority: Literal["73e05613e1bf8a3e3529325730d79843a0b8fb4d"]
    issuer_merge_commit: Literal["73e05613e1bf8a3e3529325730d79843a0b8fb4d"]
    saved_version_id: Literal[344464549]
    transaction_id: Literal["0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"]
    lifecycle_outcome: Literal["PASSED"]
    evidence_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    expected_hashes: ExpectedHashes
    expected_semantics: ExpectedSemantics
    expected_zip_member_count: Literal[19]
    expected_bundle_manifest_member_count: Literal[18]
    evidence_receipt_count: Literal[9]
    evidence_receipts: tuple[ArtifactReceipt, ...]
    current_line_p5_pass_accepted: Literal[True]
    current_line_p6_pass_accepted: Literal[True]
    p5_requalified: Literal[True]
    p6_requalified: Literal[True]
    c4_mechanism_qualified: Literal[True]
    c4_semantic_qualified: Literal[False]
    c4_semantic_state: Literal["INVALID_JSON"]
    variance_pilot_p5_p6_prerequisite_satisfied: Literal[True]
    variance_pilot_authority_reconciliation_required: Literal[True]
    variance_pilot_runtime_launcher_readiness_committed: Literal[False]
    variance_pilot_execution_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_gate: Literal[
        "RECONCILE_VARIANCE_PILOT_CURRENT_P5_P6_ACCEPTANCE_AND_BUILD_RUNTIME_LAUNCHER_READINESS_V1"
    ]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_counts(self) -> AcceptancePolicy:
        if len(self.evidence_receipts) != self.evidence_receipt_count:
            raise ValueError("evidence receipt count drifted")
        return self


class AuthorizationBudget(ExternalModel):
    maximum_benchmark_trajectory_requests: Literal[0]
    maximum_external_network_requests: Literal[0]
    maximum_external_spend: Literal[0]
    maximum_hidden_retries: Literal[0]
    maximum_kaggle_sessions: Literal[1]
    maximum_model_loads: Literal[3]
    maximum_model_requests: Literal[6]
    maximum_replacement_workers: Literal[0]
    maximum_runtime_import_closure_probes: Literal[1]
    maximum_runtime_install_attempts: Literal[1]
    maximum_save_and_run_all_actions: Literal[1]
    maximum_worker_starts: Literal[3]
    maximum_worker_teardowns: Literal[3]


class AuthorizationMechanism(ExternalModel):
    invalid_json_blocks_mechanism: Literal[False]
    p5_acceptance_relaxed: Literal[False]
    p5_uses_semantic_state: Literal[False]
    p6_acceptance_relaxed: Literal[False]
    p6_uses_semantic_state: Literal[False]
    raw_output_logging_permitted: Literal[False]
    semantic_mismatch_blocks_mechanism: Literal[False]


class AuthorizationPayload(ExternalModel):
    schema_version: Literal["1.0.0"]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"]
    issuer_merge_commit: Literal["73e05613e1bf8a3e3529325730d79843a0b8fb4d"]
    runtime_payload_sha256: Literal[
        "7f820f1b1195dd2877d4cd197fdc10b79c4e86490e98597aab8bae09cd4a3afc"
    ]
    runtime_execution_authorized: Literal[True]
    mechanism_admission_execution_authorized: Literal[True]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    repository_acceptance_established: Literal[False]
    authorization_reusable: Literal[False]
    single_use: Literal[True]
    unchanged_replay_authorized: Literal[False]
    budget: AuthorizationBudget
    mechanism: AuthorizationMechanism


class AuthorizationEvidence(StrictModel):
    schema_version: Literal["1.0.0"]
    transaction_id: Literal["0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"]
    authorization: AuthorizationPayload


class ArtifactLiveManifest(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["TRANSACTION_BOUND_EXECUTABLE_GENERATED"]
    transaction_id: Literal["0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    issuer_merge_commit: Literal["73e05613e1bf8a3e3529325730d79843a0b8fb4d"]
    runtime_payload_sha256: Literal[
        "7f820f1b1195dd2877d4cd197fdc10b79c4e86490e98597aab8bae09cd4a3afc"
    ]
    runtime_execution_authorized: Literal[True]
    single_use_governance: Literal[True]
    platform_observation_required_before_save_and_run_all: Literal[True]


class PlatformObservation(ExternalModel):
    schema_version: Literal["1.0.0"]
    transaction_id: Literal["0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accelerator: Literal["T4_X2"]
    allocated_gpu_count: Literal[2]
    internet_enabled: Literal[False]
    persisted_before_save_and_run_all: Literal[True]
    receipt_runtime_input: Literal[False]


class TerminalEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    transaction_id: Literal["0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"]
    saved_version_id: Literal[344464549]
    disposition: Literal["CONSUMED"]
    execution_attempted: Literal[True]
    execution_outcome: Literal["PASSED"]
    authorization_reusable: Literal[False]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_observation_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_requalified: Literal[False]
    p6_requalified: Literal[False]
    repository_acceptance_established: Literal[False]


class ObservedExecution(StrictModel):
    runtime_install_attempts: Literal[1]
    runtime_import_closure_probes: Literal[1]
    model_loads: Literal[3]
    worker_starts: Literal[3]
    model_requests: Literal[6]
    hidden_retries: Literal[0]
    network_requests: Literal[0]
    p5_executed: Literal[True]
    p5_decision: Literal["PASS"]
    p6_executed: Literal[True]
    p6_decision: Literal["PASS"]


class PreservationLifecycle(StrictModel):
    authorization_live_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_live_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_observation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_terminal_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreservationRawKaggle(StrictModel):
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duplicate_terminal_export_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    executed_notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreservationCustody(StrictModel):
    lifecycle_file_count: Literal[4]
    raw_kaggle_file_count: Literal[4]
    immutable_source_files_modified: Literal[False]
    vault_copy_identity_verified: Literal[True]


class PreservationManifest(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["IMMUTABLE_EVIDENCE_INTAKE_COMPLETE"]
    saved_version_id: Literal[344464549]
    transaction_id: Literal["0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"]
    issuer_merge_commit: Literal["73e05613e1bf8a3e3529325730d79843a0b8fb4d"]
    runtime_payload_sha256: Literal[
        "7f820f1b1195dd2877d4cd197fdc10b79c4e86490e98597aab8bae09cd4a3afc"
    ]
    execution_disposition: Literal["CONSUMED"]
    execution_outcome: Literal["PASSED"]
    authorization_reusable: Literal[False]
    new_execution_authorized: Literal[False]
    observed_execution: ObservedExecution
    lifecycle: PreservationLifecycle
    raw_kaggle: PreservationRawKaggle
    custody: PreservationCustody


class AcceptanceReview(StrictModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    review_id: Literal["auragateway-p5-p6-successor-execution-acceptance-v2-review"]
    saved_version_id: Literal[344464549]
    transaction_id: Literal["0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"]
    technical_status: Literal["PASSED"]
    lifecycle_status: Literal["CONSUMED"]
    lifecycle_outcome: Literal["PASSED"]
    evidence_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    current_line_p5_pass_accepted: Literal[True]
    current_line_p6_pass_accepted: Literal[True]
    p5_requalified: Literal[True]
    p6_requalified: Literal[True]
    c4_mechanism_qualified: Literal[True]
    c4_semantic_qualified: Literal[False]
    c4_semantic_state: Literal["INVALID_JSON"]
    variance_pilot_p5_p6_prerequisite_satisfied: Literal[True]
    variance_pilot_authority_reconciliation_required: Literal[True]
    variance_pilot_runtime_launcher_readiness_committed: Literal[False]
    variance_pilot_execution_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    new_execution_authorized: Literal[False]
    authorization_live_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_live_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_observation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_terminal_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preservation_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    next_gate: Literal[
        "RECONCILE_VARIANCE_PILOT_CURRENT_P5_P6_ACCEPTANCE_AND_BUILD_RUNTIME_LAUNCHER_READINESS_V1"
    ]
    non_claims: tuple[str, ...]


class AcceptanceRecord(StrictModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal["auragateway-p5-p6-successor-execution-acceptance-v2"]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_version_id: Literal[344464549]
    transaction_id: Literal["0ab0101b14901f484c2c9d3342302563ea5d334f827e8b25dfa515faa3820843"]
    technical_status: Literal["PASSED"]
    governed_acceptance_status: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    current_line_p5_pass_accepted: Literal[True]
    current_line_p6_pass_accepted: Literal[True]
    p5_requalified: Literal[True]
    p6_requalified: Literal[True]
    c4_mechanism_qualified: Literal[True]
    c4_semantic_qualified: Literal[False]
    c4_semantic_state: Literal["INVALID_JSON"]
    variance_pilot_p5_p6_prerequisite_satisfied: Literal[True]
    variance_pilot_authority_reconciliation_required: Literal[True]
    variance_pilot_runtime_launcher_readiness_committed: Literal[False]
    variance_pilot_execution_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    new_execution_authorized: Literal[False]
    evidence_receipts: tuple[ArtifactReceipt, ...]
    current_main_authority: Literal["73e05613e1bf8a3e3529325730d79843a0b8fb4d"]
    issuer_merge_commit: Literal["73e05613e1bf8a3e3529325730d79843a0b8fb4d"]
    next_gate: Literal[
        "RECONCILE_VARIANCE_PILOT_CURRENT_P5_P6_ACCEPTANCE_AND_BUILD_RUNTIME_LAUNCHER_READINESS_V1"
    ]


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
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceError(
            "P5_P6_EXECUTION_ACCEPTANCE_JSON_INVALID",
            "required JSON could not be loaded",
            path.as_posix(),
        ) from error


def _load_model(model: type[BaseModel], path: Path) -> BaseModel:
    try:
        return model.model_validate(_read_json(path))
    except ValidationError as error:
        raise AcceptanceError(
            "P5_P6_EXECUTION_ACCEPTANCE_SCHEMA_INVALID",
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
        "P5_P6_EXECUTION_ACCEPTANCE_POLICY_MISSING",
        "execution-acceptance policy is missing",
        POLICY_PATH,
    )
    _require(
        _file_sha256(path) == POLICY_SHA256,
        "P5_P6_EXECUTION_ACCEPTANCE_POLICY_IDENTITY_DRIFT",
        "execution-acceptance policy identity drifted",
        POLICY_PATH,
    )
    return cast(AcceptancePolicy, _load_model(AcceptancePolicy, path))


def _artifact_receipt(root: Path, relative: Path) -> ArtifactReceipt:
    path = root / relative
    _require(
        path.is_file() and not path.is_symlink(),
        "P5_P6_EXECUTION_ACCEPTANCE_ARTIFACT_MISSING",
        "required artifact is missing or unsafe",
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
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AcceptanceError(
            "P5_P6_EXECUTION_ACCEPTANCE_GIT_FAILED",
            "repository authority could not be read",
            relative,
        ) from error
    _require(
        result.returncode == 0,
        "P5_P6_EXECUTION_ACCEPTANCE_GIT_FAILED",
        "repository authority could not be read",
        Path(relative),
    )
    return result.stdout


def _validate_repository_authority(root: Path, policy: AcceptancePolicy) -> None:
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
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AcceptanceError(
            "P5_P6_EXECUTION_ACCEPTANCE_ANCESTRY_UNREADABLE",
            "main authority ancestry could not be inspected",
        ) from error
    _require(
        result.returncode == 0,
        "P5_P6_EXECUTION_ACCEPTANCE_MAIN_AUTHORITY_MISSING",
        "accepted execution main authority is not an ancestor of HEAD",
    )


def _validate_evidence_receipts(root: Path, policy: AcceptancePolicy) -> None:
    for expected in policy.evidence_receipts:
        observed = _artifact_receipt(root, Path(expected.path))
        _require(
            observed == expected,
            "P5_P6_EXECUTION_ACCEPTANCE_EVIDENCE_RECEIPT_DRIFT",
            "evidence receipt drifted",
            Path(expected.path),
        )


def _normalize_zip_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    _require(
        not path.is_absolute(),
        "P5_P6_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member is absolute",
    )
    _require(
        ".." not in path.parts,
        "P5_P6_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member escapes archive root",
    )
    _require(
        re.match(r"^[A-Za-z]:", normalized) is None,
        "P5_P6_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member has drive prefix",
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
                    "P5_P6_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE",
                    "archive member is a symbolic link",
                    path,
                )
                normalized = _normalize_zip_name(info.filename)
                _require(
                    normalized not in members,
                    "P5_P6_EXECUTION_ACCEPTANCE_ARCHIVE_DUPLICATE",
                    "archive contains duplicate normalized member",
                    path,
                )
                members[normalized] = archive.read(info)
            return members
    except (OSError, zipfile.BadZipFile) as error:
        raise AcceptanceError(
            "P5_P6_EXECUTION_ACCEPTANCE_ARCHIVE_INVALID",
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
        "P5_P6_EXECUTION_ACCEPTANCE_EVIDENCE_PATH_AMBIGUOUS",
        "evidence path is missing or ambiguous",
        details=(filename,),
    )
    return matches[0]


def _canonical_sha256(payload: object) -> str:
    return _sha256_bytes(
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def _validate_lifecycle(root: Path, policy: AcceptancePolicy) -> None:
    authorization_path = root / _evidence_path(policy, AUTHORIZATION_NAME)
    manifest_path = root / _evidence_path(policy, ARTIFACT_MANIFEST_NAME)
    observation_path = root / _evidence_path(policy, PLATFORM_OBSERVATION_NAME)
    terminal_path = root / _evidence_path(policy, TERMINAL_AUTHORIZATION_NAME)

    authorization = cast(
        AuthorizationEvidence,
        _load_model(AuthorizationEvidence, authorization_path),
    )
    manifest = cast(
        ArtifactLiveManifest,
        _load_model(ArtifactLiveManifest, manifest_path),
    )
    observation = cast(
        PlatformObservation,
        _load_model(PlatformObservation, observation_path),
    )
    terminal = cast(
        TerminalEvidence,
        _load_model(TerminalEvidence, terminal_path),
    )

    hashes = policy.expected_hashes
    canonical_authorization = _canonical_sha256(authorization.model_dump(mode="json"))
    inner_authorization = _canonical_sha256(authorization.authorization.model_dump(mode="json"))

    _require(
        _file_sha256(authorization_path) == hashes.authorization_live_file,
        "P5_P6_EXECUTION_ACCEPTANCE_AUTHORIZATION_FILE_DRIFT",
        "authorization live file identity drifted",
        authorization_path,
    )
    _require(
        canonical_authorization == hashes.authorization_canonical,
        "P5_P6_EXECUTION_ACCEPTANCE_AUTHORIZATION_CANONICAL_DRIFT",
        "canonical authorization wrapper identity drifted",
        authorization_path,
    )
    _require(
        inner_authorization == policy.transaction_id
        and authorization.transaction_id == policy.transaction_id,
        "P5_P6_EXECUTION_ACCEPTANCE_TRANSACTION_BINDING_DRIFT",
        "authorization transaction identity drifted",
        authorization_path,
    )
    _require(
        _file_sha256(manifest_path) == hashes.artifact_live_manifest
        and _file_sha256(observation_path) == hashes.platform_observation
        and _file_sha256(terminal_path) == hashes.authorization_terminal,
        "P5_P6_EXECUTION_ACCEPTANCE_LIFECYCLE_FILE_DRIFT",
        "preserved lifecycle file identity drifted",
    )
    _require(
        manifest.authorization_sha256 == hashes.authorization_canonical
        and observation.authorization_sha256 == hashes.authorization_canonical
        and terminal.authorization_sha256 == hashes.authorization_canonical,
        "P5_P6_EXECUTION_ACCEPTANCE_AUTHORIZATION_BINDING_DRIFT",
        "lifecycle artifact authorization binding drifted",
    )
    _require(
        observation.manifest_sha256 == hashes.artifact_live_manifest
        and terminal.manifest_sha256 == hashes.artifact_live_manifest
        and terminal.platform_observation_receipt_sha256 == hashes.platform_observation,
        "P5_P6_EXECUTION_ACCEPTANCE_LIFECYCLE_BINDING_DRIFT",
        "terminal lifecycle binding drifted",
    )
    _require(
        terminal.evidence_zip_sha256 == hashes.evidence_zip
        and terminal.terminal_log_sha256 == hashes.terminal_log,
        "P5_P6_EXECUTION_ACCEPTANCE_TERMINAL_EVIDENCE_BINDING_DRIFT",
        "terminal evidence binding drifted",
        terminal_path,
    )


def _validate_preservation_manifest(root: Path, policy: AcceptancePolicy) -> None:
    path = root / _evidence_path(policy, PRESERVATION_MANIFEST_NAME)
    manifest = cast(
        PreservationManifest,
        _load_model(PreservationManifest, path),
    )
    hashes = policy.expected_hashes

    _require(
        _file_sha256(path) == hashes.preservation_manifest,
        "P5_P6_EXECUTION_ACCEPTANCE_PRESERVATION_MANIFEST_DRIFT",
        "preservation manifest identity drifted",
        path,
    )
    _require(
        manifest.lifecycle.authorization_live_sha256 == hashes.authorization_live_file
        and manifest.lifecycle.artifact_live_manifest_sha256 == hashes.artifact_live_manifest
        and manifest.lifecycle.platform_observation_sha256 == hashes.platform_observation
        and manifest.lifecycle.authorization_terminal_sha256 == hashes.authorization_terminal,
        "P5_P6_EXECUTION_ACCEPTANCE_PRESERVATION_LIFECYCLE_DRIFT",
        "preservation lifecycle binding drifted",
        path,
    )
    _require(
        manifest.raw_kaggle.evidence_zip_sha256 == hashes.evidence_zip
        and manifest.raw_kaggle.terminal_log_sha256 == hashes.terminal_log
        and manifest.raw_kaggle.duplicate_terminal_export_sha256 == hashes.duplicate_terminal_export
        and manifest.raw_kaggle.executed_notebook_sha256 == hashes.notebook,
        "P5_P6_EXECUTION_ACCEPTANCE_PRESERVATION_RAW_DRIFT",
        "preserved raw Kaggle identity drifted",
        path,
    )


def _member_json(members: dict[str, bytes], name: str) -> dict[str, object]:
    try:
        payload = json.loads(members[name])
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AcceptanceError(
            "P5_P6_EXECUTION_ACCEPTANCE_MEMBER_JSON_INVALID",
            "runtime evidence member JSON is invalid",
            name,
        ) from error
    _require(
        isinstance(payload, dict),
        "P5_P6_EXECUTION_ACCEPTANCE_MEMBER_JSON_INVALID",
        "runtime evidence member root is not an object",
        Path(name),
    )
    return cast(dict[str, object], payload)


def _mapping(value: object, label: str) -> dict[str, object]:
    _require(
        isinstance(value, dict),
        "P5_P6_EXECUTION_ACCEPTANCE_SEMANTIC_DRIFT",
        "runtime evidence structure drifted",
        details=(label,),
    )
    return cast(dict[str, object], value)


def _number(value: object, expected: float, label: str) -> None:
    _require(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and float(value) == expected,
        "P5_P6_EXECUTION_ACCEPTANCE_SEMANTIC_DRIFT",
        "runtime evidence metric drifted",
        details=(label, str(value), str(expected)),
    )


def _bundle_manifest_receipts(
    members: dict[str, bytes],
    expected_member_count: int,
) -> dict[str, ArtifactReceipt]:
    manifest = _member_json(members, "bundle_manifest_v1.json")
    raw_receipts = manifest.get("members")
    _require(
        isinstance(raw_receipts, list) and len(raw_receipts) == expected_member_count,
        "P5_P6_EXECUTION_ACCEPTANCE_BUNDLE_MANIFEST_DRIFT",
        "runtime bundle manifest member count drifted",
    )
    receipts: dict[str, ArtifactReceipt] = {}
    for item in cast(list[object], raw_receipts):
        _require(
            isinstance(item, dict),
            "P5_P6_EXECUTION_ACCEPTANCE_BUNDLE_MANIFEST_DRIFT",
            "runtime bundle manifest receipt structure drifted",
        )
        try:
            receipt = ArtifactReceipt.model_validate(item)
        except ValidationError as error:
            raise AcceptanceError(
                "P5_P6_EXECUTION_ACCEPTANCE_BUNDLE_MANIFEST_DRIFT",
                "runtime bundle manifest receipt schema drifted",
            ) from error
        normalized = _normalize_zip_name(receipt.path)
        _require(
            normalized == receipt.path and normalized not in receipts,
            "P5_P6_EXECUTION_ACCEPTANCE_BUNDLE_MANIFEST_DRIFT",
            "runtime bundle manifest path drifted",
            details=(receipt.path,),
        )
        receipts[normalized] = receipt
    return receipts


def _metric_delta(
    observation: dict[str, object],
    label: str,
) -> dict[str, object]:
    return _mapping(observation.get("metric_delta"), f"{label}.metric_delta")


def _validate_metric_observation(
    observation: dict[str, object],
    *,
    label: str,
    expected_role: str,
    expected_cache_hit: float,
    expected_local_compute: float,
) -> None:
    delta = _metric_delta(observation, label)
    _require(
        observation.get("request_role") == expected_role,
        "P5_P6_EXECUTION_ACCEPTANCE_REQUEST_IDENTITY_DRIFT",
        "runtime request role drifted",
        details=(label, str(observation.get("request_role")), expected_role),
    )
    _number(delta.get("local_cache_hit"), expected_cache_hit, f"{label}.local_cache_hit")
    _number(delta.get("local_compute"), expected_local_compute, f"{label}.local_compute")
    _number(
        delta.get("newly_computed_prefill_tokens"),
        expected_local_compute,
        f"{label}.newly_computed_prefill_tokens",
    )
    _number(delta.get("external_kv_transfer"), 0.0, f"{label}.external_kv_transfer")
    prompt_tokens = observation.get("prompt_tokens")
    _number(
        prompt_tokens,
        expected_cache_hit + expected_local_compute,
        f"{label}.prompt_tokens",
    )
    token_identity = _mapping(observation.get("token_identity"), f"{label}.token_identity")
    _number(
        token_identity.get("token_count"),
        expected_cache_hit + expected_local_compute,
        f"{label}.token_identity.token_count",
    )
    _require(
        token_identity.get("request_role") == expected_role,
        "P5_P6_EXECUTION_ACCEPTANCE_REQUEST_IDENTITY_DRIFT",
        "runtime token identity role drifted",
        details=(label,),
    )


def _validate_route(
    observation: dict[str, object],
    *,
    label: str,
    expected_role: str,
    expected_worker: str,
) -> None:
    route = _mapping(observation.get("route_observation"), f"{label}.route_observation")
    _require(
        route.get("request_role") == expected_role
        and route.get("intended_worker") == expected_worker
        and route.get("realized_worker") == expected_worker
        and route.get("fallback_reason") is None
        and route.get("route_reason") == "DIRECT_LOOPBACK_ENDPOINT",
        "P5_P6_EXECUTION_ACCEPTANCE_P6_ROUTE_DRIFT",
        "P6 route realization drifted",
        details=(label,),
    )


def _validate_runtime_evidence(root: Path, policy: AcceptancePolicy) -> None:
    zip_path = root / _evidence_path(policy, EVIDENCE_ZIP_NAME)
    log_path = root / _evidence_path(policy, TERMINAL_LOG_NAME)
    duplicate_log_path = root / _evidence_path(policy, DUPLICATE_TERMINAL_EXPORT_NAME)
    notebook_path = root / _evidence_path(policy, EXECUTED_NOTEBOOK_NAME)
    hashes = policy.expected_hashes
    semantics = policy.expected_semantics

    _require(
        _file_sha256(zip_path) == hashes.evidence_zip,
        "P5_P6_EXECUTION_ACCEPTANCE_EVIDENCE_ZIP_DRIFT",
        "evidence ZIP identity drifted",
        zip_path,
    )
    _require(
        _file_sha256(log_path) == hashes.terminal_log
        and _file_sha256(duplicate_log_path) == hashes.duplicate_terminal_export
        and log_path.read_bytes() == duplicate_log_path.read_bytes(),
        "P5_P6_EXECUTION_ACCEPTANCE_TERMINAL_LOG_DRIFT",
        "terminal log custody identity drifted",
        log_path,
    )
    _require(
        _file_sha256(notebook_path) == hashes.notebook,
        "P5_P6_EXECUTION_ACCEPTANCE_NOTEBOOK_DRIFT",
        "executed notebook identity drifted",
        notebook_path,
    )

    members = _safe_zip_members(zip_path)
    expected_names = {
        "runtime_source_identity_report_v1.json",
        "runtime_install_report_v1.json",
        "runtime_environment_report_v1.json",
        "runtime_import_closure_report_v1.json",
        "c1_model_construction_report_v1.json",
        "c2_worker_startup_report_v1.json",
        "c3_single_request_report_v1.json",
        "c4_output_contract_report_v1.json",
        "p5_cache_behavior_report_v1.json",
        "p5_post_restart_native_origin_report_v1.json",
        "p6_stage_checkpoint_report_v1.json",
        "p6_native_origin_report_v1.json",
        "p6_worker_state_isolation_report_v1.json",
        "worker_teardown_report_v1.json",
        "scratch_cleanup_report_v1.json",
        "p5_p6_exact_runtime_requalification_summary_v1.json",
        "failure_report_v1.json",
        "bundle_manifest_v1.json",
        "human_report_v1.md",
    }
    _require(
        len(members) == policy.expected_zip_member_count and set(members) == expected_names,
        "P5_P6_EXECUTION_ACCEPTANCE_RUNTIME_ZIP_BOUNDARY_DRIFT",
        "runtime evidence ZIP member boundary drifted",
        zip_path,
    )

    manifest_receipts = _bundle_manifest_receipts(
        members,
        policy.expected_bundle_manifest_member_count,
    )
    _require(
        set(manifest_receipts) == expected_names - {"bundle_manifest_v1.json"},
        "P5_P6_EXECUTION_ACCEPTANCE_BUNDLE_MANIFEST_DRIFT",
        "runtime bundle manifest member boundary drifted",
        zip_path,
    )
    for name, receipt in manifest_receipts.items():
        payload = members[name]
        _require(
            _sha256_bytes(payload) == receipt.sha256 and len(payload) == receipt.size_bytes,
            "P5_P6_EXECUTION_ACCEPTANCE_BUNDLE_MEMBER_DRIFT",
            "runtime bundle member identity drifted",
            Path(name),
        )

    source_identity = _member_json(members, "runtime_source_identity_report_v1.json")
    _require(
        source_identity.get("status") == "PASSED"
        and source_identity.get("decision") == "EXECUTED_RUNTIME_SCRIPT_IDENTITY_VERIFIED"
        and source_identity.get("wrapper_hash_verification_passed") is True
        and source_identity.get("executed_runtime_script_sha256") == hashes.runtime_script,
        "P5_P6_EXECUTION_ACCEPTANCE_RUNTIME_SOURCE_DRIFT",
        "runtime source identity drifted",
    )

    install = _member_json(members, "runtime_install_report_v1.json")
    _require(
        install.get("status") == "PASSED"
        and install.get("process_outcome") == "PASSED"
        and install.get("returncode") == 0
        and install.get("hidden_retry_count") == 0
        and install.get("network_access_requested") is False
        and install.get("post_install_snapshot_status") == "PASSED",
        "P5_P6_EXECUTION_ACCEPTANCE_RUNTIME_INSTALL_DRIFT",
        "runtime install evidence drifted",
    )

    environment = _member_json(members, "runtime_environment_report_v1.json")
    _require(
        environment.get("status") == "PASSED"
        and environment.get("attention_backend") == "TRITON_ATTN"
        and environment.get("pythonpath_exact_target_site") is True
        and environment.get("prohibited_stub_path_present") is False
        and environment.get("target_libraries_precede_inherited") is True,
        "P5_P6_EXECUTION_ACCEPTANCE_RUNTIME_ENVIRONMENT_DRIFT",
        "runtime environment evidence drifted",
    )

    import_closure = _member_json(members, "runtime_import_closure_report_v1.json")
    _require(
        import_closure.get("status") == "PASSED"
        and import_closure.get("process_outcome") == "PASSED"
        and import_closure.get("decision") == "PROCESS_TREE_IMPORT_CLOSURE_PASSED"
        and import_closure.get("returncode") == 0
        and import_closure.get("hidden_retry_count") == 0
        and import_closure.get("network_access_requested") is False
        and import_closure.get("all_critical_origins_within_target_site") is True,
        "P5_P6_EXECUTION_ACCEPTANCE_IMPORT_CLOSURE_DRIFT",
        "runtime import-closure evidence drifted",
    )

    c1 = _member_json(members, "c1_model_construction_report_v1.json")
    c1_observations = _mapping(c1.get("observations"), "c1.observations")
    _require(
        c1.get("state") == "PASS"
        and c1.get("failure_class") is None
        and c1_observations.get("model_snapshot_sha256") == hashes.model_snapshot,
        "P5_P6_EXECUTION_ACCEPTANCE_C1_DRIFT",
        "C1 model construction evidence drifted",
    )

    c2 = _member_json(members, "c2_worker_startup_report_v1.json")
    c3 = _member_json(members, "c3_single_request_report_v1.json")
    _require(
        c2.get("state") == "PASS"
        and c2.get("failure_class") is None
        and c3.get("state") == "PASS"
        and c3.get("failure_class") is None,
        "P5_P6_EXECUTION_ACCEPTANCE_C2_C3_DRIFT",
        "C2/C3 mechanism evidence drifted",
    )

    c4 = _member_json(members, "c4_output_contract_report_v1.json")
    c4_observations = _mapping(c4.get("observations"), "c4.observations")
    c4_semantic = _mapping(c4_observations.get("semantic_observation"), "c4.semantic")
    c4_route = _mapping(c4_observations.get("route_observation"), "c4.route")
    _require(
        c4.get("state") == "FAIL"
        and c4.get("failure_class") == "OUTPUT_CONTRACT_FAILURE"
        and c4_semantic.get("state") == semantics.c4_semantic_state
        and c4_semantic.get("valid_json") is False
        and c4_semantic.get("exact_match") is False
        and c4_route.get("intended_worker") == "worker_1"
        and c4_route.get("realized_worker") == "worker_1"
        and c4_route.get("fallback_reason") is None,
        "P5_P6_EXECUTION_ACCEPTANCE_C4_BOUNDARY_DRIFT",
        "C4 semantic/mechanism boundary drifted",
    )

    summary = _member_json(members, "p5_p6_exact_runtime_requalification_summary_v1.json")
    _require(
        summary.get("status") == "PASSED"
        and summary.get("terminal_state") == "PASSED_PENDING_REPOSITORY_ACCEPTANCE"
        and tuple(cast(list[str], summary.get("completed_capabilities")))
        == semantics.completed_capabilities
        and summary.get("failed_capability") is None
        and summary.get("failure_class") is None
        and summary.get("executed_runtime_script_sha256") == hashes.runtime_script
        and summary.get("c4_semantic_qualified") is semantics.c4_semantic_qualified
        and summary.get("c4_semantic_state") == semantics.c4_semantic_state
        and summary.get("p5_decision") == "PASS"
        and summary.get("p6_decision") == "PASS"
        and summary.get("measured_abc_execution_performed")
        is semantics.measured_abc_execution_performed
        and summary.get("pilot_execution_performed") is semantics.pilot_execution_performed
        and summary.get("public_evidence_used_as_semantic_input") is False
        and summary.get("network_access_permitted") is False
        and summary.get("runtime_install_process_outcome") == "PASSED"
        and summary.get("runtime_import_closure_process_outcome") == "PASSED"
        and summary.get("worker_teardown_status") == "PASSED"
        and summary.get("scratch_cleanup_status") == "PASSED",
        "P5_P6_EXECUTION_ACCEPTANCE_SUMMARY_DRIFT",
        "runtime requalification summary drifted",
    )
    counters = _mapping(summary.get("counters"), "summary.counters")
    expected_counters = {
        "benchmark_trajectory_requests": semantics.benchmark_trajectory_requests,
        "external_spend": semantics.external_spend,
        "hidden_retries": semantics.hidden_retries,
        "kaggle_sessions": 1,
        "model_loads": semantics.model_loads,
        "model_requests": semantics.model_requests,
        "network_requests": semantics.network_requests,
        "runtime_import_closure_probes": semantics.runtime_import_closure_probes,
        "runtime_install_attempts": semantics.runtime_install_attempts,
        "worker_starts": semantics.worker_starts,
    }
    _require(
        counters == expected_counters,
        "P5_P6_EXECUTION_ACCEPTANCE_COUNTER_DRIFT",
        "runtime qualification counters drifted",
    )

    p5 = _member_json(members, "p5_cache_behavior_report_v1.json")
    p5_observations = _mapping(p5.get("observations"), "p5.observations")
    _require(
        p5.get("state") == "PASS" and p5.get("failure_class") is None,
        "P5_P6_EXECUTION_ACCEPTANCE_P5_DRIFT",
        "P5 cache-behavior decision drifted",
    )
    p5_cases = (
        (
            "BASE_COLD",
            semantics.p5_base_cold_cache_hit,
            semantics.p5_base_cold_local_compute,
        ),
        (
            "BASE_WARM",
            semantics.p5_base_warm_cache_hit,
            semantics.p5_base_warm_local_compute,
        ),
        (
            "NEGATIVE_PREFIX",
            semantics.p5_negative_prefix_cache_hit,
            semantics.p5_negative_prefix_local_compute,
        ),
        (
            "POST_RESET_COLD",
            semantics.p5_post_reset_cache_hit,
            semantics.p5_post_reset_local_compute,
        ),
        (
            "CROSS_WORKER_COLD",
            semantics.p5_cross_worker_cache_hit,
            semantics.p5_cross_worker_local_compute,
        ),
    )
    base_token_sha256: str | None = None
    for role, expected_hit, expected_compute in p5_cases:
        observation = _mapping(p5_observations.get(role), f"p5.{role}")
        _validate_metric_observation(
            observation,
            label=f"p5.{role}",
            expected_role=role,
            expected_cache_hit=float(expected_hit),
            expected_local_compute=float(expected_compute),
        )
        token_identity = _mapping(
            observation.get("token_identity"),
            f"p5.{role}.token_identity",
        )
        token_sha256 = token_identity.get("token_sha256")
        _require(
            isinstance(token_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", token_sha256) is not None,
            "P5_P6_EXECUTION_ACCEPTANCE_P5_TOKEN_IDENTITY_DRIFT",
            "P5 token identity digest drifted",
            details=(role,),
        )
        if role == "NEGATIVE_PREFIX":
            _require(
                base_token_sha256 is not None and token_sha256 != base_token_sha256,
                "P5_P6_EXECUTION_ACCEPTANCE_P5_NEGATIVE_PREFIX_DRIFT",
                "P5 negative-prefix token identity did not diverge",
            )
        if role != "NEGATIVE_PREFIX":
            if base_token_sha256 is None:
                base_token_sha256 = cast(str, token_sha256)
            _require(
                token_sha256 == base_token_sha256,
                "P5_P6_EXECUTION_ACCEPTANCE_P5_TOKEN_IDENTITY_DRIFT",
                "P5 base token identity drifted across governed requests",
                details=(role,),
            )

    p5_post_restart_origin = _member_json(
        members,
        "p5_post_restart_native_origin_report_v1.json",
    )
    _require(
        p5_post_restart_origin.get("status") == "PASSED"
        and p5_post_restart_origin.get("rejected_origin_count") == 0,
        "P5_P6_EXECUTION_ACCEPTANCE_P5_NATIVE_ORIGIN_DRIFT",
        "P5 post-restart native-origin evidence drifted",
    )

    p6_checkpoint = _member_json(members, "p6_stage_checkpoint_report_v1.json")
    _require(
        p6_checkpoint.get("status") == "PASS"
        and p6_checkpoint.get("current_stage") == "P6_COMPLETED"
        and p6_checkpoint.get("starting_model_requests") == 4
        and p6_checkpoint.get("global_model_requests") == semantics.model_requests
        and p6_checkpoint.get("raw_output_logged") is False
        and p6_checkpoint.get("raw_prompt_logged") is False,
        "P5_P6_EXECUTION_ACCEPTANCE_P6_CHECKPOINT_DRIFT",
        "P6 stage checkpoint drifted",
    )

    p6_origin = _member_json(members, "p6_native_origin_report_v1.json")
    _require(
        p6_origin.get("status") == "PASSED"
        and p6_origin.get("decision") == "RUNTIME_NATIVE_ORIGIN_CLOSURE_PASSED"
        and p6_origin.get("rejected_origin_count") == 0,
        "P5_P6_EXECUTION_ACCEPTANCE_P6_NATIVE_ORIGIN_DRIFT",
        "P6 native-origin closure drifted",
    )

    p6 = _member_json(members, "p6_worker_state_isolation_report_v1.json")
    p6_observations = _mapping(p6.get("observations"), "p6.observations")
    _require(
        p6.get("state") == "PASS"
        and p6.get("failure_class") is None
        and p6_observations.get("request_counters_reconciled") is True,
        "P5_P6_EXECUTION_ACCEPTANCE_P6_DRIFT",
        "P6 worker-state isolation decision drifted",
    )
    cross_worker = _mapping(
        p6_observations.get("CROSS_WORKER_COLD"),
        "p6.CROSS_WORKER_COLD",
    )
    retention = _mapping(
        p6_observations.get("WORKER1_RETENTION"),
        "p6.WORKER1_RETENTION",
    )
    _validate_metric_observation(
        cross_worker,
        label="p6.CROSS_WORKER_COLD",
        expected_role="CROSS_WORKER_COLD",
        expected_cache_hit=float(semantics.p6_cross_worker_cache_hit),
        expected_local_compute=float(semantics.p6_cross_worker_local_compute),
    )
    _validate_metric_observation(
        retention,
        label="p6.WORKER1_RETENTION",
        expected_role="WORKER1_RETENTION",
        expected_cache_hit=float(semantics.p6_worker1_retention_cache_hit),
        expected_local_compute=float(semantics.p6_worker1_retention_local_compute),
    )
    _validate_route(
        cross_worker,
        label="p6.CROSS_WORKER_COLD",
        expected_role="CROSS_WORKER_COLD",
        expected_worker="worker_2",
    )
    _validate_route(
        retention,
        label="p6.WORKER1_RETENTION",
        expected_role="WORKER1_RETENTION",
        expected_worker="worker_1",
    )

    process_isolation = _mapping(
        p6_observations.get("process_isolation"),
        "p6.process_isolation",
    )
    gpu_isolation = _mapping(p6_observations.get("gpu_isolation"), "p6.gpu_isolation")
    worker_1 = _mapping(p6_observations.get("worker_1"), "p6.worker_1")
    worker_2 = _mapping(p6_observations.get("worker_2"), "p6.worker_2")
    native_closure = _mapping(
        p6_observations.get("native_origin_closure"),
        "p6.native_origin_closure",
    )
    _require(
        process_isolation.get("worker_process_trees_disjoint") is True
        and process_isolation.get("worker_1_root_pid") != process_isolation.get("worker_2_root_pid")
        and gpu_isolation.get("worker_1_bound_to_gpu_0") is True
        and gpu_isolation.get("worker_2_bound_to_gpu_1") is True
        and worker_1.get("explicit_attention_backend") == "TRITON_ATTN"
        and worker_2.get("explicit_attention_backend") == "TRITON_ATTN"
        and worker_1.get("backend_log_marker_observed") is True
        and worker_2.get("backend_log_marker_observed") is True
        and native_closure.get("status") == "PASSED"
        and native_closure.get("rejected_origin_count") == 0,
        "P5_P6_EXECUTION_ACCEPTANCE_P6_ISOLATION_DRIFT",
        "P6 process/GPU/backend isolation evidence drifted",
    )

    teardown = _member_json(members, "worker_teardown_report_v1.json")
    _require(
        teardown.get("status") == "PASSED"
        and teardown.get("all_capture_threads_finalized") is True
        and teardown.get("all_gpu_processes_absent") is True
        and teardown.get("all_ports_closed") is True,
        "P5_P6_EXECUTION_ACCEPTANCE_TEARDOWN_DRIFT",
        "worker teardown evidence drifted",
    )
    cleanup = _member_json(members, "scratch_cleanup_report_v1.json")
    _require(
        cleanup.get("status") == "PASSED" and cleanup.get("scratch_exists_after") is False,
        "P5_P6_EXECUTION_ACCEPTANCE_CLEANUP_DRIFT",
        "scratch cleanup evidence drifted",
    )
    failure = _member_json(members, "failure_report_v1.json")
    _require(
        failure.get("status") == "NOT_APPLICABLE"
        and failure.get("failed_capability") is None
        and failure.get("failure_class") is None
        and failure.get("teardown_status") == "PASSED",
        "P5_P6_EXECUTION_ACCEPTANCE_FAILURE_REPORT_DRIFT",
        "terminal failure report drifted",
    )

    log_text = log_path.read_text(encoding="utf-8")
    required_tokens = (
        '"completed_capabilities":["C1","C2","C3","C4","P5","P6"]',
        '"c4_semantic_qualified":false',
        '"c4_semantic_state":"INVALID_JSON"',
        '"model_loads":3',
        '"model_requests":6',
        '"worker_starts":3',
        '"benchmark_trajectory_requests":0',
        '"hidden_retries":0',
        '"network_requests":0',
        '"measured_abc_execution_performed":false',
        '"pilot_execution_performed":false',
        '"p5_decision":"PASS"',
        '"p6_decision":"PASS"',
        f'"evidence_zip_sha256":"{hashes.evidence_zip}"',
        f'"executed_runtime_script_sha256":"{hashes.runtime_script}"',
        '"status":"PASSED"',
        '"terminal_state":"PASSED_PENDING_REPOSITORY_ACCEPTANCE"',
        "AURAGATEWAY_BOUND_RUNTIME_EXIT=0",
    )
    _require(
        all(token in log_text for token in required_tokens),
        "P5_P6_EXECUTION_ACCEPTANCE_TERMINAL_SEMANTIC_DRIFT",
        "terminal-log semantic marker drifted",
        log_path,
    )


def _validate_all(root: Path) -> AcceptancePolicy:
    policy = _load_policy(root)
    _validate_repository_authority(root, policy)
    _validate_evidence_receipts(root, policy)
    _validate_lifecycle(root, policy)
    _validate_preservation_manifest(root, policy)
    _validate_runtime_evidence(root, policy)
    return policy


def build_review(root: Path) -> AcceptanceReview:
    policy = _validate_all(root)
    hashes = policy.expected_hashes
    return AcceptanceReview(
        review_id="auragateway-p5-p6-successor-execution-acceptance-v2-review",
        saved_version_id=SAVED_VERSION_ID,
        transaction_id=TRANSACTION_ID,
        technical_status="PASSED",
        lifecycle_status="CONSUMED",
        lifecycle_outcome="PASSED",
        evidence_disposition="ACCEPTED_GOVERNED_EXECUTION_PASS",
        current_line_p5_pass_accepted=True,
        current_line_p6_pass_accepted=True,
        p5_requalified=True,
        p6_requalified=True,
        c4_mechanism_qualified=True,
        c4_semantic_qualified=False,
        c4_semantic_state="INVALID_JSON",
        variance_pilot_p5_p6_prerequisite_satisfied=True,
        variance_pilot_authority_reconciliation_required=True,
        variance_pilot_runtime_launcher_readiness_committed=False,
        variance_pilot_execution_authorized=False,
        runtime_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        authorization_reusable=False,
        new_execution_authorized=False,
        authorization_live_file_sha256=hashes.authorization_live_file,
        authorization_canonical_sha256=hashes.authorization_canonical,
        artifact_live_manifest_sha256=hashes.artifact_live_manifest,
        platform_observation_sha256=hashes.platform_observation,
        authorization_terminal_sha256=hashes.authorization_terminal,
        preservation_manifest_sha256=hashes.preservation_manifest,
        evidence_zip_sha256=hashes.evidence_zip,
        terminal_log_sha256=hashes.terminal_log,
        next_gate=policy.next_gate,
        non_claims=policy.non_claims,
    )


def build_record(root: Path, review: AcceptanceReview) -> AcceptanceRecord:
    policy = _load_policy(root)
    review_bytes = _canonical(review.model_dump(mode="json")).encode("utf-8")
    return AcceptanceRecord(
        record_id="auragateway-p5-p6-successor-execution-acceptance-v2",
        review_sha256=_sha256_bytes(review_bytes),
        saved_version_id=SAVED_VERSION_ID,
        transaction_id=TRANSACTION_ID,
        technical_status="PASSED",
        governed_acceptance_status="ACCEPTED_GOVERNED_EXECUTION_PASS",
        current_line_p5_pass_accepted=True,
        current_line_p6_pass_accepted=True,
        p5_requalified=True,
        p6_requalified=True,
        c4_mechanism_qualified=True,
        c4_semantic_qualified=False,
        c4_semantic_state="INVALID_JSON",
        variance_pilot_p5_p6_prerequisite_satisfied=True,
        variance_pilot_authority_reconciliation_required=True,
        variance_pilot_runtime_launcher_readiness_committed=False,
        variance_pilot_execution_authorized=False,
        runtime_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        authorization_reusable=False,
        new_execution_authorized=False,
        evidence_receipts=policy.evidence_receipts,
        current_main_authority=policy.current_main_authority,
        issuer_merge_commit=policy.issuer_merge_commit,
        next_gate=policy.next_gate,
    )


def _result(status: str, policy: AcceptancePolicy) -> dict[str, object]:
    return {
        "status": status,
        "saved_version_id": SAVED_VERSION_ID,
        "transaction_id": TRANSACTION_ID,
        "technical_status": "PASSED",
        "governed_acceptance_status": "ACCEPTED_GOVERNED_EXECUTION_PASS",
        "current_line_p5_pass_accepted": True,
        "current_line_p6_pass_accepted": True,
        "p5_requalified": True,
        "p6_requalified": True,
        "c4_mechanism_qualified": True,
        "c4_semantic_qualified": False,
        "c4_semantic_state": "INVALID_JSON",
        "variance_pilot_p5_p6_prerequisite_satisfied": True,
        "variance_pilot_authority_reconciliation_required": True,
        "variance_pilot_runtime_launcher_readiness_committed": False,
        "variance_pilot_execution_authorized": False,
        "runtime_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "authorization_reusable": False,
        "new_execution_authorized": False,
        "next_gate": policy.next_gate,
    }


def generate(root: Path) -> dict[str, object]:
    review = build_review(root)
    record = build_record(root, review)
    _write_json(
        REVIEW_PATH if root == Path(".") else root / REVIEW_PATH,
        review.model_dump(mode="json"),
    )
    _write_json(
        RECORD_PATH if root == Path(".") else root / RECORD_PATH,
        record.model_dump(mode="json"),
    )
    return _result(
        "P5_P6_SUCCESSOR_EXECUTION_ACCEPTANCE_V2_GENERATED",
        _load_policy(root),
    )


def validate_implementation(root: Path) -> dict[str, object]:
    review = build_review(root)
    record = build_record(root, review)
    review_path = root / REVIEW_PATH
    record_path = root / RECORD_PATH
    _require(
        review_path.is_file() and record_path.is_file(),
        "P5_P6_EXECUTION_ACCEPTANCE_OUTPUT_MISSING",
        "generated acceptance outputs are missing",
    )
    observed_review = cast(
        AcceptanceReview,
        _load_model(AcceptanceReview, review_path),
    )
    observed_record = cast(
        AcceptanceRecord,
        _load_model(AcceptanceRecord, record_path),
    )
    _require(
        observed_review == review,
        "P5_P6_EXECUTION_ACCEPTANCE_REVIEW_DRIFT",
        "acceptance review is not deterministic",
        REVIEW_PATH,
    )
    _require(
        observed_record == record,
        "P5_P6_EXECUTION_ACCEPTANCE_RECORD_DRIFT",
        "acceptance record is not deterministic",
        RECORD_PATH,
    )
    return _result(
        "P5_P6_SUCCESSOR_EXECUTION_ACCEPTANCE_V2_VALID",
        _load_policy(root),
    )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="p5-p6-successor-execution-acceptance-v2")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate-implementation"):
        child = sub.add_parser(command)
        child.add_argument("--repo-root", type=Path, required=True)
    return parser


def main() -> int:
    try:
        args = _parser().parse_args()
        root = args.repo_root.resolve()
        result = generate(root) if args.command == "generate" else validate_implementation(root)
        print(_canonical(result), end="")
        return 0
    except AcceptanceError as error:
        print(_canonical(error.envelope()), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
