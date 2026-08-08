# Accept the governed P5/P6 successor runtime qualification pass.

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
from typing import Literal, Never, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p5_p6_successor_execution_acceptance_v1_policy.json"
)
POLICY_SHA256 = "73be5cd771db95d9d018ea5530fb5c85bbd735c2a2c47a7f10f509982848ff4c"
REVIEW_PATH = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1_review.json"
)
RECORD_PATH = Path("benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json")
EVIDENCE_DIR = Path("evidence_vault/local_abc/p5-p6-successor-runtime-qualification-pass-v1")
EVIDENCE_ZIP_NAME = "ag-p5-p6-successor-runtime-evidence-v1-340976295.zip"
TERMINAL_LOG_NAME = "ag-p5-p6-successor-runtime-qual-v1-340976295.log"
AUTHORIZATION_NAME = "execution_authorization_v1-340976295.json"
CONSUMPTION_NAME = "execution_authorization_consumption_v1-340976295.json"
INTAKE_MANIFEST_NAME = "intake_manifest_v1-340976295.json"
SAVED_VERSION_ID = 340976295


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
    authorization: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_snapshot: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExpectedSizes(StrictModel):
    authorization: int = Field(gt=0)
    consumption: int = Field(gt=0)
    evidence_zip: int = Field(gt=0)
    terminal_log: int = Field(gt=0)


class ExpectedSemantics(StrictModel):
    completed_probes: tuple[str, ...]
    model_requests: Literal[5]
    model_loads: Literal[3]
    worker_starts: Literal[3]
    hidden_retries: Literal[0]
    benchmark_trajectory_requests: Literal[0]
    network_requests: Literal[0]
    external_spend: Literal[0]
    measured_abc_execution_performed: Literal[False]
    p5_cold_cached_prefix_tokens: Literal[0]
    p5_warm_cached_prefix_tokens: Literal[736]
    p5_post_restart_cached_prefix_tokens: Literal[0]
    p5_cold_new_prefill_tokens: Literal[747]
    p5_warm_new_prefill_tokens: Literal[11]
    p5_post_restart_new_prefill_tokens: Literal[747]
    p6_worker_1_prompt_delta: Literal[747]
    p6_worker_1_non_target_prompt_delta: Literal[0]
    p6_worker_2_prompt_delta: Literal[747]
    p6_worker_2_non_target_prompt_delta: Literal[0]

    @model_validator(mode="after")
    def validate_probe_order(self) -> ExpectedSemantics:
        if self.completed_probes != ("P3", "P4", "P5", "P6"):
            raise ValueError("completed probe order drifted")
        return self


class AcceptancePolicy(StrictModel):
    schema_version: Literal["1.0.0"]
    policy_id: Literal["auragateway-p5-p6-successor-execution-acceptance-v1-policy"]
    current_main_authority: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_merge_commit: Literal["6e424acb27e568bb7ce5000ea0732e175bf6b35a"]
    authorization_issued_from_main_commit: Literal["0be8dda7cf63c6709bf5b246656b13fdf769f45e"]
    saved_version_id: Literal[340976295]
    lifecycle_outcome: Literal["PASSED"]
    evidence_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    expected_hashes: ExpectedHashes
    expected_sizes: ExpectedSizes
    expected_semantics: ExpectedSemantics
    expected_evidence_member_count: Literal[18]
    evidence_receipt_count: int = Field(gt=0)
    evidence_receipts: tuple[ArtifactReceipt, ...]
    repository_authority_count: int = Field(gt=0)
    repository_authorities: tuple[ArtifactReceipt, ...]
    operational_transient_paths: tuple[str, ...]
    current_line_p5_pass_accepted: Literal[True]
    current_line_p6_pass_accepted: Literal[True]
    measured_abc_eligible: Literal[True]
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["design_and_merge_measured_abc_execution_authorization_v1"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_counts(self) -> AcceptancePolicy:
        if len(self.evidence_receipts) != self.evidence_receipt_count:
            raise ValueError("evidence receipt count drifted")
        if len(self.repository_authorities) != self.repository_authority_count:
            raise ValueError("repository authority count drifted")
        if len(self.operational_transient_paths) != 2:
            raise ValueError("operational transient path count drifted")
        return self


class AuthorizationEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal["auragateway-p5-p6-successor-execution-authorization-v1"]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1"]
    issued_from_main_commit: Literal["0be8dda7cf63c6709bf5b246656b13fdf769f45e"]
    issued_at: datetime
    expires_at: datetime
    runtime_execution_authorized: Literal[True]
    single_use: Literal[True]
    measured_abc_execution_authorized: Literal[False]


class ConsumptionEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal["auragateway-p5-p6-successor-execution-authorization-v1"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["PASSED"]
    consumed_at: datetime
    saved_version_id: Literal[340976295]
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False]
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]


class IntakeManifest(ExternalModel):
    schema_version: Literal["1.0.0"]
    intake_id: Literal["auragateway-p5-p6-successor-runtime-qualification-pass-340976295"]
    saved_version_id: Literal[340976295]
    execution_outcome: Literal["PASSED"]
    evidence_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_line_p5_pass_accepted: Literal[True]
    current_line_p6_pass_accepted: Literal[True]
    measured_abc_eligible: Literal[True]
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    members: tuple[ArtifactReceipt, ...]


class AcceptanceReview(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-p5-p6-successor-execution-acceptance-v1-review"]
    saved_version_id: Literal[340976295]
    technical_status: Literal["PASSED"]
    lifecycle_status: Literal["CONSUMED"]
    lifecycle_outcome: Literal["PASSED"]
    evidence_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    current_line_p5_pass_accepted: Literal[True]
    current_line_p6_pass_accepted: Literal[True]
    measured_abc_eligible: Literal[True]
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    authorization_sha256: str
    consumption_sha256: str
    evidence_zip_sha256: str
    terminal_log_sha256: str
    next_gate: Literal["design_and_merge_measured_abc_execution_authorization_v1"]
    non_claims: tuple[str, ...]


class AcceptanceRecord(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p5-p6-successor-execution-acceptance-v1"]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_version_id: Literal[340976295]
    technical_status: Literal["PASSED"]
    governed_acceptance_status: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    current_line_p5_pass_accepted: Literal[True]
    current_line_p6_pass_accepted: Literal[True]
    measured_abc_eligible: Literal[True]
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    evidence_receipts: tuple[ArtifactReceipt, ...]
    repository_authorities: tuple[ArtifactReceipt, ...]
    next_gate: Literal["design_and_merge_measured_abc_execution_authorization_v1"]


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
        return json.loads(path.read_text(encoding="utf-8"))
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


def _validate_repository_authorities(root: Path, policy: AcceptancePolicy) -> None:
    for receipt in policy.repository_authorities:
        payload = _git_blob(root, receipt.path)
        _require(
            _sha256_bytes(payload) == receipt.sha256 and len(payload) == receipt.size_bytes,
            "P5_P6_EXECUTION_ACCEPTANCE_REPOSITORY_AUTHORITY_DRIFT",
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


def _validate_lifecycle(root: Path, policy: AcceptancePolicy) -> None:
    authorization_path = root / _evidence_path(policy, AUTHORIZATION_NAME)
    consumption_path = root / _evidence_path(policy, CONSUMPTION_NAME)
    authorization = cast(
        AuthorizationEvidence,
        _load_model(AuthorizationEvidence, authorization_path),
    )
    consumption = cast(
        ConsumptionEvidence,
        _load_model(ConsumptionEvidence, consumption_path),
    )
    hashes = policy.expected_hashes
    sizes = policy.expected_sizes
    _require(
        _file_sha256(authorization_path) == hashes.authorization
        and authorization_path.stat().st_size == sizes.authorization,
        "P5_P6_EXECUTION_ACCEPTANCE_AUTHORIZATION_DRIFT",
        "authorization evidence identity drifted",
        authorization_path,
    )
    _require(
        _file_sha256(consumption_path) == hashes.consumption
        and consumption_path.stat().st_size == sizes.consumption,
        "P5_P6_EXECUTION_ACCEPTANCE_CONSUMPTION_DRIFT",
        "consumption evidence identity drifted",
        consumption_path,
    )
    _require(
        consumption.authorization_sha256 == hashes.authorization,
        "P5_P6_EXECUTION_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption does not bind accepted authorization",
        consumption_path,
    )
    _require(
        consumption.evidence_zip_sha256 == hashes.evidence_zip,
        "P5_P6_EXECUTION_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption does not bind accepted evidence ZIP",
        consumption_path,
    )
    _require(
        consumption.terminal_log_sha256 == hashes.terminal_log,
        "P5_P6_EXECUTION_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption does not bind accepted terminal log",
        consumption_path,
    )
    _require(
        authorization.issued_at < consumption.consumed_at <= authorization.expires_at,
        "P5_P6_EXECUTION_ACCEPTANCE_LIFECYCLE_TIME_DRIFT",
        "consumption timestamp is outside authorization window",
        consumption_path,
    )


def _validate_intake_manifest(root: Path, policy: AcceptancePolicy) -> None:
    path = root / _evidence_path(policy, INTAKE_MANIFEST_NAME)
    manifest = cast(
        IntakeManifest,
        _load_model(IntakeManifest, path),
    )
    hashes = policy.expected_hashes
    _require(
        manifest.authorization_sha256 == hashes.authorization
        and manifest.consumption_sha256 == hashes.consumption
        and manifest.evidence_zip_sha256 == hashes.evidence_zip
        and manifest.terminal_log_sha256 == hashes.terminal_log,
        "P5_P6_EXECUTION_ACCEPTANCE_INTAKE_BINDING_DRIFT",
        "intake manifest lifecycle/evidence binding drifted",
        path,
    )
    for item in manifest.members:
        observed = _artifact_receipt(root, Path(item.path))
        _require(
            observed == item,
            "P5_P6_EXECUTION_ACCEPTANCE_INTAKE_RECEIPT_DRIFT",
            "intake manifest member receipt drifted",
            Path(item.path),
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


def _validate_runtime_evidence(root: Path, policy: AcceptancePolicy) -> None:
    zip_path = root / _evidence_path(policy, EVIDENCE_ZIP_NAME)
    log_path = root / _evidence_path(policy, TERMINAL_LOG_NAME)
    hashes = policy.expected_hashes
    sizes = policy.expected_sizes

    _require(
        _file_sha256(zip_path) == hashes.evidence_zip
        and zip_path.stat().st_size == sizes.evidence_zip,
        "P5_P6_EXECUTION_ACCEPTANCE_EVIDENCE_ZIP_DRIFT",
        "evidence ZIP identity drifted",
        zip_path,
    )
    _require(
        _file_sha256(log_path) == hashes.terminal_log
        and log_path.stat().st_size == sizes.terminal_log,
        "P5_P6_EXECUTION_ACCEPTANCE_TERMINAL_LOG_DRIFT",
        "terminal log identity drifted",
        log_path,
    )

    members = _safe_zip_members(zip_path)
    expected_member_names = {
        Path(item.path).name
        for item in policy.evidence_receipts
        if Path(item.path).parent == EVIDENCE_DIR
        and Path(item.path).name
        in {
            "runtime_source_identity_report_v1.json",
            "runtime_install_report_v1.json",
            "runtime_environment_report_v1.json",
            "runtime_import_closure_report_v1.json",
            "p3_worker_startup_report_v1.json",
            "p3_native_origin_report_v1.json",
            "p4_case_a_canary_report_v1.json",
            "p5_prefix_cache_reset_report_v1.json",
            "p5_post_restart_native_origin_report_v1.json",
            "p6_stage_checkpoint_report_v1.json",
            "p6_native_origin_report_v1.json",
            "p6_dual_worker_isolation_report_v1.json",
            "worker_teardown_report_v1.json",
            "scratch_cleanup_report_v1.json",
            "p5_p6_successor_runtime_qualification_summary_v1.json",
            "failure_report_v1.json",
            "bundle_manifest_v1.json",
            "human_report_v1.md",
        }
    }
    _require(
        len(members) == policy.expected_evidence_member_count
        and set(members) == expected_member_names,
        "P5_P6_EXECUTION_ACCEPTANCE_RUNTIME_ZIP_BOUNDARY_DRIFT",
        "runtime evidence ZIP member boundary drifted",
        zip_path,
    )
    for name, payload in members.items():
        preserved = root / EVIDENCE_DIR / name
        _require(
            preserved.read_bytes() == payload,
            "P5_P6_EXECUTION_ACCEPTANCE_RUNTIME_ZIP_BYTE_DRIFT",
            "preserved runtime member differs from evidence ZIP",
            preserved,
        )

    summary = _member_json(members, "p5_p6_successor_runtime_qualification_summary_v1.json")
    semantics = policy.expected_semantics
    _require(
        summary.get("status") == "PASSED"
        and tuple(cast(list[str], summary.get("completed_probes"))) == semantics.completed_probes
        and summary.get("failed_probe") is None
        and summary.get("failure_code") is None
        and summary.get("executed_runtime_script_sha256") == hashes.runtime_script
        and summary.get("measured_abc_execution_performed") is False
        and summary.get("network_access_permitted") is False
        and summary.get("worker_teardown_status") == "PASSED"
        and summary.get("scratch_cleanup_status") == "PASSED",
        "P5_P6_EXECUTION_ACCEPTANCE_SUMMARY_DRIFT",
        "runtime qualification summary drifted",
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
        "runtime_import_closure_probes": 1,
        "runtime_install_attempts": 1,
        "worker_starts": semantics.worker_starts,
    }
    _require(
        counters == expected_counters,
        "P5_P6_EXECUTION_ACCEPTANCE_COUNTER_DRIFT",
        "runtime qualification counters drifted",
    )

    p5 = _member_json(members, "p5_prefix_cache_reset_report_v1.json")
    _require(
        p5.get("status") == "PASSED"
        and p5.get("full_process_restart_reset_proven") is True
        and p5.get("namespace_only_reset_used") is False,
        "P5_P6_EXECUTION_ACCEPTANCE_P5_DRIFT",
        "P5 reset proof drifted",
    )
    for request_key, cached, prefill in (
        (
            "cold_request",
            semantics.p5_cold_cached_prefix_tokens,
            semantics.p5_cold_new_prefill_tokens,
        ),
        (
            "warm_request",
            semantics.p5_warm_cached_prefix_tokens,
            semantics.p5_warm_new_prefill_tokens,
        ),
        (
            "post_reset_request",
            semantics.p5_post_restart_cached_prefix_tokens,
            semantics.p5_post_restart_new_prefill_tokens,
        ),
    ):
        request = _mapping(p5.get(request_key), f"p5.{request_key}")
        delta = _mapping(
            request.get("metric_delta"),
            f"p5.{request_key}.metric_delta",
        )
        _number(
            delta.get("cached_prefix_tokens"),
            float(cached),
            f"p5.{request_key}.cached_prefix_tokens",
        )
        _number(
            delta.get("newly_computed_prefill_tokens"),
            float(prefill),
            f"p5.{request_key}.newly_computed_prefill_tokens",
        )

    p6 = _member_json(members, "p6_dual_worker_isolation_report_v1.json")
    _require(
        p6.get("status") == "PASSED" and p6.get("model_semantics_used_as_route_proof") is False,
        "P5_P6_EXECUTION_ACCEPTANCE_P6_DRIFT",
        "P6 route-isolation proof drifted",
    )
    isolation = _mapping(
        p6.get("route_and_metric_isolation"),
        "p6.route_and_metric_isolation",
    )
    _require(
        isolation.get("request_counters_reconciled") is True,
        "P5_P6_EXECUTION_ACCEPTANCE_P6_DRIFT",
        "P6 request counters were not reconciled",
    )
    for request_key, target_prompt, non_target_prompt in (
        (
            "worker_1_request",
            semantics.p6_worker_1_prompt_delta,
            semantics.p6_worker_1_non_target_prompt_delta,
        ),
        (
            "worker_2_request",
            semantics.p6_worker_2_prompt_delta,
            semantics.p6_worker_2_non_target_prompt_delta,
        ),
    ):
        request = _mapping(isolation.get(request_key), f"p6.{request_key}")
        _require(
            request.get("route_acknowledged") is True
            and request.get("route_acknowledgement_source") == "HARNESS_TRANSPORT_AND_METRICS",
            "P5_P6_EXECUTION_ACCEPTANCE_P6_ROUTE_DRIFT",
            "P6 route acknowledgement drifted",
            details=(request_key,),
        )
        target = _mapping(
            request.get("target_metric_delta"),
            f"p6.{request_key}.target",
        )
        non_target = _mapping(
            request.get("non_target_metric_delta"),
            f"p6.{request_key}.non_target",
        )
        _number(
            target.get("prompt_tokens"),
            float(target_prompt),
            f"p6.{request_key}.target.prompt_tokens",
        )
        _number(
            non_target.get("prompt_tokens"),
            float(non_target_prompt),
            f"p6.{request_key}.non_target.prompt_tokens",
        )

    log_text = log_path.read_text(encoding="utf-8")
    required_tokens = (
        '"completed_probes":["P3","P4","P5","P6"]',
        '"model_loads":3',
        '"model_requests":5',
        '"worker_starts":3',
        '"benchmark_trajectory_requests":0',
        '"hidden_retries":0',
        '"network_requests":0',
        '"measured_abc_execution_performed":false',
        f'"evidence_zip_sha256":"{hashes.evidence_zip}"',
        f'"executed_runtime_script_sha256":"{hashes.runtime_script}"',
        '"status":"PASSED"',
        '"terminal_decision":"P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1_PASSED"',
    )
    _require(
        all(token in log_text for token in required_tokens),
        "P5_P6_EXECUTION_ACCEPTANCE_TERMINAL_SEMANTIC_DRIFT",
        "terminal-log semantic marker drifted",
        log_path,
    )


def _require_transient_paths_retired(root: Path, policy: AcceptancePolicy) -> None:
    present = [path for path in policy.operational_transient_paths if (root / path).exists()]
    _require(
        not present,
        "P5_P6_EXECUTION_ACCEPTANCE_TRANSIENT_NOT_RETIRED",
        "operational transient lifecycle artifacts remain after preservation",
        details=tuple(present),
    )


def _validate_all(root: Path) -> AcceptancePolicy:
    policy = _load_policy(root)
    _validate_repository_authorities(root, policy)
    _validate_evidence_receipts(root, policy)
    _validate_lifecycle(root, policy)
    _validate_intake_manifest(root, policy)
    _validate_runtime_evidence(root, policy)
    _require_transient_paths_retired(root, policy)
    return policy


def build_review(root: Path) -> AcceptanceReview:
    policy = _validate_all(root)
    hashes = policy.expected_hashes
    return AcceptanceReview(
        review_id="auragateway-p5-p6-successor-execution-acceptance-v1-review",
        saved_version_id=SAVED_VERSION_ID,
        technical_status="PASSED",
        lifecycle_status="CONSUMED",
        lifecycle_outcome="PASSED",
        evidence_disposition="ACCEPTED_GOVERNED_EXECUTION_PASS",
        current_line_p5_pass_accepted=True,
        current_line_p6_pass_accepted=True,
        measured_abc_eligible=True,
        runtime_execution_authorized=False,
        measured_abc_execution_authorized=False,
        authorization_sha256=hashes.authorization,
        consumption_sha256=hashes.consumption,
        evidence_zip_sha256=hashes.evidence_zip,
        terminal_log_sha256=hashes.terminal_log,
        next_gate="design_and_merge_measured_abc_execution_authorization_v1",
        non_claims=policy.non_claims,
    )


def build_record(root: Path, review: AcceptanceReview) -> AcceptanceRecord:
    policy = _load_policy(root)
    review_bytes = _canonical(review.model_dump(mode="json")).encode("utf-8")
    return AcceptanceRecord(
        record_id="auragateway-p5-p6-successor-execution-acceptance-v1",
        review_sha256=_sha256_bytes(review_bytes),
        saved_version_id=SAVED_VERSION_ID,
        technical_status="PASSED",
        governed_acceptance_status="ACCEPTED_GOVERNED_EXECUTION_PASS",
        current_line_p5_pass_accepted=True,
        current_line_p6_pass_accepted=True,
        measured_abc_eligible=True,
        runtime_execution_authorized=False,
        measured_abc_execution_authorized=False,
        evidence_receipts=policy.evidence_receipts,
        repository_authorities=policy.repository_authorities,
        next_gate="design_and_merge_measured_abc_execution_authorization_v1",
    )


def generate(root: Path) -> dict[str, object]:
    review = build_review(root)
    record = build_record(root, review)
    _write_json(
        REVIEW_PATH if root == Path(".") else root / REVIEW_PATH, review.model_dump(mode="json")
    )
    _write_json(
        RECORD_PATH if root == Path(".") else root / RECORD_PATH, record.model_dump(mode="json")
    )
    return {
        "status": "P5_P6_SUCCESSOR_EXECUTION_ACCEPTANCE_V1_GENERATED",
        "saved_version_id": SAVED_VERSION_ID,
        "technical_status": "PASSED",
        "governed_acceptance_status": "ACCEPTED_GOVERNED_EXECUTION_PASS",
        "current_line_p5_pass_accepted": True,
        "current_line_p6_pass_accepted": True,
        "measured_abc_eligible": True,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": "design_and_merge_measured_abc_execution_authorization_v1",
    }


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
    return {
        "status": "P5_P6_SUCCESSOR_EXECUTION_ACCEPTANCE_V1_VALID",
        "saved_version_id": SAVED_VERSION_ID,
        "technical_status": "PASSED",
        "governed_acceptance_status": "ACCEPTED_GOVERNED_EXECUTION_PASS",
        "current_line_p5_pass_accepted": True,
        "current_line_p6_pass_accepted": True,
        "measured_abc_eligible": True,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": "design_and_merge_measured_abc_execution_authorization_v1",
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="p5-p6-successor-execution-acceptance-v1")
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
