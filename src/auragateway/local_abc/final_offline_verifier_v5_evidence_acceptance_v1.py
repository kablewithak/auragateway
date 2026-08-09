"""Accept the governed Final Offline Verifier V5 capability pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
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
    "final_offline_verifier_v5_evidence_acceptance_v1_policy.json"
)
POLICY_SHA256 = "9a255b4b2528865420e7826e86e086dd1d1ceb89c4c76a65ab67f48ca418f815"
EVIDENCE_DIR = Path("evidence_vault/local_abc/preflight-v5-exact-runtime-offline-pass-v1")
REVIEW_PATH = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_evidence_acceptance_v1_review.json"
)
RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_evidence_acceptance_v1_record.json"
)
SAVED_VERSION_ID = 341257985
ACCEPTANCE_BASE_MAIN = "23f74af3da1d61ef6a3f9f375617847d7aecef47"
VERIFIER_IMPLEMENTATION_MERGE = "a0a21c648e881c7eb733967b42ee6f08cbcbb48a"
ISSUER_MERGE = "23f74af3da1d61ef6a3f9f375617847d7aecef47"

PRESERVED_NOTEBOOK = "ag-preflight-v3-final-offline-verifier-v5-341257985.ipynb"
PRESERVED_LOG = "ag-preflight-v3-final-offline-verifier-v5-341257985.log"
PRESERVED_ZIP = (
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_evidence_v5-341257985.zip"
)
PRESERVED_AUTHORIZATION = "execution_authorization_v1-341257985.json"
PRESERVED_CONSUMPTION = "execution_authorization_consumption_v1-341257985.json"
INTAKE_MANIFEST = "intake_manifest_v1-341257985.json"


class AcceptanceError(RuntimeError):
    """Fail-closed V5 evidence-acceptance error."""

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
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARGUMENT_INVALID",
            "V5 evidence-acceptance arguments are invalid",
            details=(message,),
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExternalModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class ArtifactIdentity(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ExternalArtifact(StrictModel):
    filename: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class EvidenceMember(StrictModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class LifecyclePolicy(StrictModel):
    authorization_path: str
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption_path: str
    consumption_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    abandonment_path: str


class SemanticBoundaryPolicy(StrictModel):
    semantic_decisions_reading_stdout_excerpt: Literal[0]
    semantic_decisions_reading_stderr_excerpt: Literal[0]
    lossy_transformations_before_semantic_decision: Literal[0]
    truncation_before_semantic_decision: Literal[0]
    raw_streams_persisted: Literal[False]
    evidence_projection_terminal: Literal[True]


class AcceptedClaims(StrictModel):
    exact_runtime_offline_verified: Literal[True]
    qualification_scope: Literal["CAPABILITY_ONLY"]


class AcceptancePolicy(StrictModel):
    schema_version: Literal["1.0.0"]
    policy_id: Literal["auragateway-final-offline-verifier-v5-evidence-acceptance-v1-policy"]
    acceptance_base_main_commit: Literal["23f74af3da1d61ef6a3f9f375617847d7aecef47"]
    verifier_implementation_merge_commit: Literal["a0a21c648e881c7eb733967b42ee6f08cbcbb48a"]
    authorization_issuer_merge_commit: Literal["23f74af3da1d61ef6a3f9f375617847d7aecef47"]
    saved_version_id: Literal[341257985]
    saved_version_url: str
    execution_outcome: Literal["PASSED"]
    offline_compatibility_status: Literal["PASSED_PENDING_REPOSITORY_ACCEPTANCE"]
    governed_acceptance_status: Literal["ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"]
    external_artifacts: dict[str, ExternalArtifact]
    lifecycle_artifacts: LifecyclePolicy
    evidence_members: dict[str, EvidenceMember]
    required_roles: tuple[str, ...]
    required_native_module: Literal["vllm._C_stable_libtorch"]
    expected_materializer_script_version_id: Literal[341083505]
    expected_locked_package_count: Literal[196]
    expected_manifest_entry_count: Literal[200]
    expected_total_wheel_bytes: Literal[6164913809]
    expected_semantic_boundary: SemanticBoundaryPolicy
    accepted_claims: AcceptedClaims
    non_claims: tuple[str, ...]
    next_gate: Literal["design_exact_runtime_p5_p6_requalification_v1"]

    @model_validator(mode="after")
    def validate_shapes(self) -> AcceptancePolicy:
        if set(self.external_artifacts) != {
            "executed_notebook",
            "terminal_log",
            "evidence_zip",
        }:
            raise ValueError("external artifact boundary drifted")
        if set(self.evidence_members) != {
            "input_validation.json",
            "probe_records.json",
            "verification_summary.json",
            "evidence_manifest.json",
        }:
            raise ValueError("evidence member boundary drifted")
        if len(self.required_roles) != 25:
            raise ValueError("required role count drifted")
        return self


class AuthorizationEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    authorization_id: str
    lifecycle: Literal["ISSUED"]
    issued_at: datetime
    expires_at: datetime
    issuer_merge_commit: Literal["23f74af3da1d61ef6a3f9f375617847d7aecef47"]
    implementation_merge_commit: Literal["a0a21c648e881c7eb733967b42ee6f08cbcbb48a"]
    operator_attested_platform: Literal["T4_X2"]
    operator_attested_gpu_count: Literal[2]
    operator_attested_internet_enabled: Literal[False]
    offline_verifier_v5_execution_authorized: Literal[True]
    model_execution_authorized: Literal[False]
    p5_p6_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]


class ConsumptionEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    authorization_id: str
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["PASSED"]
    consumed_at: datetime
    saved_version_id: Literal[341257985]
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False]
    offline_verifier_v5_execution_authorized: Literal[False]
    model_execution_authorized: Literal[False]
    p5_p6_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["preserve_and_accept_or_classify_final_offline_verifier_v5_evidence"]


class IntakeManifest(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    intake_id: Literal["auragateway-final-offline-verifier-v5-pass-341257985"]
    saved_version_id: Literal[341257985]
    execution_outcome: Literal["PASSED"]
    governed_acceptance_status: Literal["ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"]
    artifacts: tuple[ArtifactIdentity, ...]
    exact_runtime_offline_verified: Literal[True]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["design_exact_runtime_p5_p6_requalification_v1"]


class AcceptanceReview(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-final-offline-verifier-v5-evidence-acceptance-v1-review"]
    saved_version_id: Literal[341257985]
    technical_status: Literal["PASSED"]
    execution_outcome: Literal["PASSED"]
    evidence_status: Literal["VALIDATED"]
    governed_acceptance_status: Literal["ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"]
    qualification_scope: Literal["CAPABILITY_ONLY"]
    exact_runtime_offline_verified: Literal[True]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    evidence_receipts: tuple[ArtifactIdentity, ...]
    next_gate: Literal["design_exact_runtime_p5_p6_requalification_v1"]
    non_claims: tuple[str, ...]


class AcceptanceRecord(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-final-offline-verifier-v5-evidence-acceptance-v1"]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_version_id: Literal[341257985]
    technical_status: Literal["PASSED"]
    governed_acceptance_status: Literal["ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"]
    qualification_scope: Literal["CAPABILITY_ONLY"]
    acceptance_base_main_commit: Literal["23f74af3da1d61ef6a3f9f375617847d7aecef47"]
    verifier_implementation_merge_commit: Literal["a0a21c648e881c7eb733967b42ee6f08cbcbb48a"]
    authorization_issuer_merge_commit: Literal["23f74af3da1d61ef6a3f9f375617847d7aecef47"]
    exact_runtime_offline_verified: Literal[True]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    evidence_receipts: tuple[ArtifactIdentity, ...]
    next_gate: Literal["design_exact_runtime_p5_p6_requalification_v1"]


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
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_JSON_INVALID",
            "required JSON could not be loaded",
            path.as_posix(),
        ) from error


def _load_model(model: type[BaseModel], path: Path) -> BaseModel:
    try:
        return model.model_validate(_read_json(path))
    except ValidationError as error:
        raise AcceptanceError(
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_SCHEMA_INVALID",
            "evidence schema validation failed",
            path.as_posix(),
            details=(str(error),),
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


def _identity(root: Path, relative: Path) -> ArtifactIdentity:
    path = root / relative
    _require(
        path.is_file() and not path.is_symlink(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARTIFACT_MISSING",
        "required artifact is missing or unsafe",
        relative,
    )
    return ArtifactIdentity(
        path=relative.as_posix(),
        sha256=_file_sha256(path),
        size_bytes=path.stat().st_size,
    )


def _load_policy(root: Path) -> AcceptancePolicy:
    path = root / POLICY_PATH
    _require(
        path.is_file() and not path.is_symlink(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_POLICY_MISSING",
        "V5 evidence-acceptance policy is missing",
        POLICY_PATH,
    )
    _require(
        _file_sha256(path) == POLICY_SHA256,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_POLICY_IDENTITY_DRIFT",
        "V5 evidence-acceptance policy identity drifted",
        POLICY_PATH,
    )
    return cast(AcceptancePolicy, _load_model(AcceptancePolicy, path))


def _git(root: Path, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _require_repo_ancestry(root: Path) -> None:
    for commit in (
        ACCEPTANCE_BASE_MAIN,
        VERIFIER_IMPLEMENTATION_MERGE,
        ISSUER_MERGE,
    ):
        code, _, _ = _git(root, "merge-base", "--is-ancestor", commit, "HEAD")
        _require(
            code == 0,
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ANCESTRY_DRIFT",
            "required accepted authority is not an ancestor of HEAD",
            details=(commit,),
        )


def _normalize_zip_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    _require(
        not path.is_absolute(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member is absolute",
    )
    _require(
        ".." not in path.parts,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member escapes archive root",
    )
    _require(
        re.match(r"^[A-Za-z]:", normalized) is None,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARCHIVE_UNSAFE",
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
                    "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARCHIVE_UNSAFE",
                    "archive member is a symbolic link",
                    path,
                )
                normalized = _normalize_zip_name(info.filename)
                _require(
                    normalized not in members,
                    "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARCHIVE_DUPLICATE",
                    "archive contains duplicate normalized member",
                    path,
                )
                members[normalized] = archive.read(info)
            return members
    except (OSError, zipfile.BadZipFile) as error:
        raise AcceptanceError(
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARCHIVE_INVALID",
            "V5 evidence ZIP is invalid",
            path.as_posix(),
        ) from error


def _validate_external_file(
    path: Path,
    expected: ExternalArtifact,
    label: str,
) -> None:
    _require(
        path.is_file() and not path.is_symlink(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_EXTERNAL_MISSING",
        "external evidence artifact is missing or unsafe",
        path,
        details=(label,),
    )
    _require(
        path.name == expected.filename
        and path.stat().st_size == expected.size_bytes
        and _file_sha256(path) == expected.sha256,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_EXTERNAL_IDENTITY_DRIFT",
        "external evidence artifact identity drifted",
        path,
        details=(label,),
    )


def _validate_lifecycle(
    root: Path,
    policy: AcceptancePolicy,
) -> tuple[bytes, bytes]:
    lifecycle = policy.lifecycle_artifacts
    authorization_path = root / lifecycle.authorization_path
    consumption_path = root / lifecycle.consumption_path
    abandonment_path = root / lifecycle.abandonment_path
    _require(
        not abandonment_path.exists(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ABANDONMENT_CONFLICT",
        "abandonment artifact conflicts with PASSED consumption",
        abandonment_path,
    )
    _require(
        authorization_path.is_file() and consumption_path.is_file(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_LIFECYCLE_MISSING",
        "authorization lifecycle evidence is incomplete",
    )
    authorization_bytes = authorization_path.read_bytes()
    consumption_bytes = consumption_path.read_bytes()
    _require(
        _sha256_bytes(authorization_bytes) == lifecycle.authorization_sha256,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_AUTHORIZATION_DRIFT",
        "authorization identity drifted",
        authorization_path,
    )
    _require(
        _sha256_bytes(consumption_bytes) == lifecycle.consumption_sha256,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_CONSUMPTION_DRIFT",
        "consumption identity drifted",
        consumption_path,
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
        authorization.authorization_id == consumption.authorization_id,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_LIFECYCLE_BINDING_DRIFT",
        "authorization ID binding drifted",
    )
    _require(
        consumption.authorization_sha256 == lifecycle.authorization_sha256,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_LIFECYCLE_BINDING_DRIFT",
        "consumption does not bind accepted authorization",
    )
    zip_sha = policy.external_artifacts["evidence_zip"].sha256
    _require(
        consumption.evidence_zip_sha256 == zip_sha,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_LIFECYCLE_BINDING_DRIFT",
        "consumption does not bind accepted V5 evidence ZIP",
    )
    _require(
        authorization.issued_at < consumption.consumed_at <= authorization.expires_at,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_LIFECYCLE_TIME_DRIFT",
        "consumption timestamp is outside authorization window",
    )
    return authorization_bytes, consumption_bytes


def _validate_member_identities(
    members: dict[str, bytes],
    policy: AcceptancePolicy,
) -> None:
    _require(
        set(members) == set(policy.evidence_members),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MEMBER_BOUNDARY_DRIFT",
        "V5 evidence ZIP member boundary drifted",
    )
    for name, expected in policy.evidence_members.items():
        payload = members[name]
        _require(
            len(payload) == expected.size_bytes and _sha256_bytes(payload) == expected.sha256,
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MEMBER_IDENTITY_DRIFT",
            "V5 evidence member identity drifted",
            Path(name),
        )


def _member_object(members: dict[str, bytes], name: str) -> dict[str, object]:
    try:
        payload = json.loads(members[name])
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AcceptanceError(
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MEMBER_JSON_INVALID",
            "V5 evidence member JSON is invalid",
            name,
        ) from error
    _require(
        isinstance(payload, dict),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MEMBER_JSON_INVALID",
        "V5 evidence member root is not an object",
        Path(name),
    )
    return cast(dict[str, object], payload)


def _validate_evidence_manifest(
    members: dict[str, bytes],
    policy: AcceptancePolicy,
) -> None:
    manifest = _member_object(members, "evidence_manifest.json")
    _require(
        manifest.get("schema_version") == "1.0.0" and manifest.get("entry_count") == 3,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MANIFEST_DRIFT",
        "V5 evidence manifest header drifted",
    )
    entries = manifest.get("entries")
    _require(
        isinstance(entries, list) and len(entries) == 3,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MANIFEST_DRIFT",
        "V5 evidence manifest entries drifted",
    )
    expected_names = {
        "input_validation.json",
        "probe_records.json",
        "verification_summary.json",
    }
    observed: set[str] = set()
    for raw in cast(list[object], entries):
        _require(
            isinstance(raw, dict),
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MANIFEST_DRIFT",
            "V5 evidence manifest entry is invalid",
        )
        entry = cast(dict[str, object], raw)
        name_value = entry.get("path")
        _require(
            isinstance(name_value, str) and name_value in expected_names,
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MANIFEST_DRIFT",
            "V5 evidence manifest path drifted",
        )
        name = cast(str, name_value)
        expected = policy.evidence_members[name]
        _require(
            entry.get("sha256") == expected.sha256
            and entry.get("size_bytes") == expected.size_bytes,
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MANIFEST_DRIFT",
            "V5 evidence manifest receipt drifted",
            Path(name),
        )
        observed.add(name)
    _require(
        observed == expected_names,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_MANIFEST_DRIFT",
        "V5 evidence manifest coverage drifted",
    )


def _validate_summary(
    members: dict[str, bytes],
    policy: AcceptancePolicy,
) -> None:
    summary = _member_object(members, "verification_summary.json")
    required_statuses = summary.get("required_role_statuses")
    _require(
        isinstance(required_statuses, dict),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_SUMMARY_DRIFT",
        "required role status map is invalid",
    )
    role_map = cast(dict[str, object], required_statuses)
    _require(
        set(role_map) == set(policy.required_roles)
        and all(role_map.get(role) == "PASSED" for role in policy.required_roles),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_REQUIRED_ROLE_DRIFT",
        "one or more V5 required roles did not pass",
    )
    _require(
        summary.get("offline_compatibility_status") == "PASSED_PENDING_REPOSITORY_ACCEPTANCE"
        and summary.get("failed_required_roles") == []
        and summary.get("required_native_module") == policy.required_native_module
        and summary.get("expected_materializer_script_version_id")
        == policy.expected_materializer_script_version_id
        and summary.get("locked_package_count") == policy.expected_locked_package_count
        and summary.get("validated_manifest_entry_count") == policy.expected_manifest_entry_count
        and summary.get("total_wheel_bytes") == policy.expected_total_wheel_bytes,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_SUMMARY_DRIFT",
        "V5 verification summary identity/shape drifted",
    )
    safety = {
        "package_installation_performed": True,
        "dependency_resolution_performed": False,
        "internet_required": False,
        "model_loads_performed": 0,
        "worker_startups_performed": 0,
        "model_requests_performed": 0,
        "benchmark_trajectories_performed": 0,
        "credentials_used": False,
        "customer_data_used": False,
        "external_spend": 0,
        "qualification_claimed": False,
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, expected in safety.items():
        _require(
            summary.get(key) == expected,
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_SAFETY_DRIFT",
            "V5 safety/non-claim contract drifted",
            details=(key,),
        )
    semantic = policy.expected_semantic_boundary
    for key, expected in semantic.model_dump().items():
        _require(
            summary.get(key) == expected,
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_SEMANTIC_BOUNDARY_DRIFT",
            "V5 semantic-boundary invariant drifted",
            details=(key,),
        )


def _validate_probe_records(
    members: dict[str, bytes],
    policy: AcceptancePolicy,
) -> None:
    records = _member_object(members, "probe_records.json")
    _require(
        set(records) == set(policy.required_roles),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_PROBE_BOUNDARY_DRIFT",
        "V5 probe-record role boundary drifted",
    )
    for role in policy.required_roles:
        raw = records.get(role)
        _require(
            isinstance(raw, dict),
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_PROBE_RECORD_DRIFT",
            "V5 probe record is invalid",
            details=(role,),
        )
        record = cast(dict[str, object], raw)
        _require(
            record.get("command_role") == role
            and record.get("status") == "PASSED"
            and record.get("failure_code") is None
            and record.get("timed_out") is False,
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_PROBE_RECORD_DRIFT",
            "V5 probe record did not preserve a clean pass",
            details=(role,),
        )


def _validate_input_evidence(
    members: dict[str, bytes],
    policy: AcceptancePolicy,
) -> None:
    payload = _member_object(members, "input_validation.json")
    _require(
        payload.get("schema_version") == "1.0.0"
        and payload.get("expected_package_count") == policy.expected_locked_package_count
        and payload.get("expected_manifest_entry_count") == policy.expected_manifest_entry_count
        and payload.get("expected_total_wheel_bytes") == policy.expected_total_wheel_bytes,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_INPUT_EVIDENCE_DRIFT",
        "V5 input-validation evidence drifted",
    )
    validation = payload.get("input_validation")
    _require(
        isinstance(validation, dict)
        and cast(dict[str, object], validation).get("status") == "PASSED",
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_INPUT_EVIDENCE_DRIFT",
        "V5 input validation did not pass",
    )


def _validate_log(path: Path, policy: AcceptancePolicy) -> None:
    text = path.read_text(encoding="utf-8")
    required_tokens = (
        '"offline_compatibility_status":"PASSED_PENDING_REPOSITORY_ACCEPTANCE"',
        '"failed_required_roles":[]',
        f'"evidence_zip_sha256":"{policy.external_artifacts["evidence_zip"].sha256}"',
        '"semantic_decisions_reading_stdout_excerpt":0',
        '"semantic_decisions_reading_stderr_excerpt":0',
        '"lossy_transformations_before_semantic_decision":0',
        '"truncation_before_semantic_decision":0',
    )
    _require(
        all(token in text for token in required_tokens),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_LOG_SEMANTIC_DRIFT",
        "terminal-log semantic markers drifted",
        path,
    )


def _validate_executed_notebook(
    path: Path,
    policy: AcceptancePolicy,
) -> None:
    payload = _read_json(path)
    _require(
        isinstance(payload, dict),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_NOTEBOOK_INVALID",
        "executed notebook root is invalid",
        path,
    )
    notebook = cast(dict[str, object], payload)
    metadata = notebook.get("metadata")
    _require(
        isinstance(metadata, dict),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_NOTEBOOK_INVALID",
        "executed notebook metadata is invalid",
        path,
    )
    aura = cast(dict[str, object], metadata).get("auragateway")
    _require(
        isinstance(aura, dict),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_NOTEBOOK_INVALID",
        "executed notebook AuraGateway metadata is missing",
        path,
    )
    aura_map = cast(dict[str, object], aura)
    _require(
        aura_map.get("requested_kaggle_title") == "ag-preflight-v3-final-offline-verifier-v5"
        and aura_map.get("accelerator") == "T4 x2"
        and aura_map.get("internet_required") is False
        and aura_map.get("required_native_module") == policy.required_native_module,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_NOTEBOOK_METADATA_DRIFT",
        "executed notebook governed metadata drifted",
        path,
    )
    serialized = json.dumps(notebook, ensure_ascii=True, separators=(",", ":"))
    _require(
        policy.external_artifacts["evidence_zip"].sha256 in serialized
        and "PASSED_PENDING_REPOSITORY_ACCEPTANCE" in serialized,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_NOTEBOOK_OUTPUT_DRIFT",
        "executed notebook does not preserve terminal V5 output identity",
        path,
    )


def _validate_external_evidence(
    notebook_path: Path,
    log_path: Path,
    zip_path: Path,
    policy: AcceptancePolicy,
) -> dict[str, bytes]:
    _validate_external_file(
        notebook_path,
        policy.external_artifacts["executed_notebook"],
        "executed_notebook",
    )
    _validate_external_file(
        log_path,
        policy.external_artifacts["terminal_log"],
        "terminal_log",
    )
    _validate_external_file(
        zip_path,
        policy.external_artifacts["evidence_zip"],
        "evidence_zip",
    )
    members = _safe_zip_members(zip_path)
    _validate_member_identities(members, policy)
    _validate_evidence_manifest(members, policy)
    _validate_input_evidence(members, policy)
    _validate_summary(members, policy)
    _validate_probe_records(members, policy)
    _validate_log(log_path, policy)
    _validate_executed_notebook(notebook_path, policy)
    return members


def _artifact_list(root: Path) -> tuple[ArtifactIdentity, ...]:
    names = (
        PRESERVED_NOTEBOOK,
        PRESERVED_LOG,
        PRESERVED_ZIP,
        PRESERVED_AUTHORIZATION,
        PRESERVED_CONSUMPTION,
        "input_validation.json",
        "probe_records.json",
        "verification_summary.json",
        "evidence_manifest.json",
    )
    return tuple(_identity(root, EVIDENCE_DIR / name) for name in names)


def _validate_preserved(root: Path, policy: AcceptancePolicy) -> IntakeManifest:
    intake_path = root / EVIDENCE_DIR / INTAKE_MANIFEST
    intake = cast(IntakeManifest, _load_model(IntakeManifest, intake_path))
    observed = _artifact_list(root)
    _require(
        intake.artifacts == observed,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_INTAKE_DRIFT",
        "preserved V5 intake manifest drifted",
        intake_path,
    )
    lifecycle = policy.lifecycle_artifacts
    _require(
        not (root / lifecycle.authorization_path).exists()
        and not (root / lifecycle.consumption_path).exists()
        and not (root / lifecycle.abandonment_path).exists(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_TRANSIENT_NOT_RETIRED",
        "operational lifecycle transient remains after preservation",
    )
    zip_path = root / EVIDENCE_DIR / PRESERVED_ZIP
    members = _safe_zip_members(zip_path)
    _validate_member_identities(members, policy)
    _validate_evidence_manifest(members, policy)
    _validate_input_evidence(members, policy)
    _validate_summary(members, policy)
    _validate_probe_records(members, policy)
    for name, payload in members.items():
        _require(
            (root / EVIDENCE_DIR / name).read_bytes() == payload,
            "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_PRESERVED_MEMBER_DRIFT",
            "preserved evidence member differs from ZIP member",
            EVIDENCE_DIR / name,
        )
    _validate_log(root / EVIDENCE_DIR / PRESERVED_LOG, policy)
    _validate_executed_notebook(
        root / EVIDENCE_DIR / PRESERVED_NOTEBOOK,
        policy,
    )
    return intake


def preserve(
    root: Path,
    *,
    notebook_path: Path,
    log_path: Path,
    zip_path: Path,
) -> dict[str, object]:
    policy = _load_policy(root)
    _require_repo_ancestry(root)
    target = root / EVIDENCE_DIR
    staging = target.with_name(target.name + ".tmp")
    _require(
        not target.exists() and not staging.exists(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_TARGET_EXISTS",
        "V5 evidence preservation target already exists",
        EVIDENCE_DIR,
    )
    authorization_bytes, consumption_bytes = _validate_lifecycle(root, policy)
    members = _validate_external_evidence(
        notebook_path,
        log_path,
        zip_path,
        policy,
    )
    try:
        staging.mkdir(parents=True)
        shutil.copyfile(notebook_path, staging / PRESERVED_NOTEBOOK)
        shutil.copyfile(log_path, staging / PRESERVED_LOG)
        shutil.copyfile(zip_path, staging / PRESERVED_ZIP)
        (staging / PRESERVED_AUTHORIZATION).write_bytes(authorization_bytes)
        (staging / PRESERVED_CONSUMPTION).write_bytes(consumption_bytes)
        for name, payload in members.items():
            (staging / name).write_bytes(payload)
        artifact_names = (
            PRESERVED_NOTEBOOK,
            PRESERVED_LOG,
            PRESERVED_ZIP,
            PRESERVED_AUTHORIZATION,
            PRESERVED_CONSUMPTION,
            "input_validation.json",
            "probe_records.json",
            "verification_summary.json",
            "evidence_manifest.json",
        )
        artifacts = tuple(
            ArtifactIdentity(
                path=(EVIDENCE_DIR / name).as_posix(),
                sha256=_file_sha256(staging / name),
                size_bytes=(staging / name).stat().st_size,
            )
            for name in artifact_names
        )
        intake = IntakeManifest(
            intake_id="auragateway-final-offline-verifier-v5-pass-341257985",
            saved_version_id=SAVED_VERSION_ID,
            execution_outcome="PASSED",
            governed_acceptance_status=("ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"),
            artifacts=artifacts,
            exact_runtime_offline_verified=True,
            p5_p6_exact_runtime_requalified=False,
            runtime_execution_authorized=False,
            pilot_execution_authorized=False,
            final_measured_abc_execution_authorized=False,
            next_gate="design_exact_runtime_p5_p6_requalification_v1",
        )
        _write_json(staging / INTAKE_MANIFEST, intake.model_dump(mode="json"))
        os.replace(staging, target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    lifecycle = policy.lifecycle_artifacts
    (root / lifecycle.authorization_path).unlink()
    (root / lifecycle.consumption_path).unlink()
    _validate_preserved(root, policy)
    return {
        "status": "FINAL_OFFLINE_VERIFIER_V5_EVIDENCE_PRESERVED",
        "saved_version_id": SAVED_VERSION_ID,
        "evidence_zip_sha256": policy.external_artifacts["evidence_zip"].sha256,
        "authorization_sha256": lifecycle.authorization_sha256,
        "consumption_sha256": lifecycle.consumption_sha256,
        "transient_lifecycle_retired": True,
        "exact_runtime_offline_verified": True,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": "generate_and_validate_v5_evidence_acceptance_v1",
    }


def build_review(root: Path) -> AcceptanceReview:
    policy = _load_policy(root)
    _require_repo_ancestry(root)
    intake = _validate_preserved(root, policy)
    return AcceptanceReview(
        review_id=("auragateway-final-offline-verifier-v5-evidence-acceptance-v1-review"),
        saved_version_id=SAVED_VERSION_ID,
        technical_status="PASSED",
        execution_outcome="PASSED",
        evidence_status="VALIDATED",
        governed_acceptance_status=("ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"),
        qualification_scope="CAPABILITY_ONLY",
        exact_runtime_offline_verified=True,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        evidence_receipts=intake.artifacts,
        next_gate=policy.next_gate,
        non_claims=policy.non_claims,
    )


def build_record(root: Path, review: AcceptanceReview) -> AcceptanceRecord:
    policy = _load_policy(root)
    review_bytes = _canonical(review.model_dump(mode="json")).encode("utf-8")
    return AcceptanceRecord(
        record_id="auragateway-final-offline-verifier-v5-evidence-acceptance-v1",
        review_sha256=_sha256_bytes(review_bytes),
        saved_version_id=SAVED_VERSION_ID,
        technical_status="PASSED",
        governed_acceptance_status=("ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"),
        qualification_scope="CAPABILITY_ONLY",
        acceptance_base_main_commit=ACCEPTANCE_BASE_MAIN,
        verifier_implementation_merge_commit=VERIFIER_IMPLEMENTATION_MERGE,
        authorization_issuer_merge_commit=ISSUER_MERGE,
        exact_runtime_offline_verified=True,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        evidence_receipts=review.evidence_receipts,
        next_gate=policy.next_gate,
    )


def generate(root: Path) -> dict[str, object]:
    review = build_review(root)
    record = build_record(root, review)
    _write_json(root / REVIEW_PATH, review.model_dump(mode="json"))
    _write_json(root / RECORD_PATH, record.model_dump(mode="json"))
    return {
        "status": "FINAL_OFFLINE_VERIFIER_V5_EVIDENCE_ACCEPTANCE_V1_GENERATED",
        "saved_version_id": SAVED_VERSION_ID,
        "governed_acceptance_status": ("ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"),
        "qualification_scope": "CAPABILITY_ONLY",
        "exact_runtime_offline_verified": True,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": "design_exact_runtime_p5_p6_requalification_v1",
    }


def validate_implementation(root: Path) -> dict[str, object]:
    review = build_review(root)
    record = build_record(root, review)
    review_path = root / REVIEW_PATH
    record_path = root / RECORD_PATH
    _require(
        review_path.is_file() and record_path.is_file(),
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_OUTPUT_MISSING",
        "generated V5 acceptance outputs are missing",
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
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_REVIEW_DRIFT",
        "V5 acceptance review is not deterministic",
        REVIEW_PATH,
    )
    _require(
        observed_record == record,
        "FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_RECORD_DRIFT",
        "V5 acceptance record is not deterministic",
        RECORD_PATH,
    )
    return {
        "status": "FINAL_OFFLINE_VERIFIER_V5_EVIDENCE_ACCEPTANCE_V1_VALID",
        "saved_version_id": SAVED_VERSION_ID,
        "technical_status": "PASSED",
        "governed_acceptance_status": ("ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"),
        "qualification_scope": "CAPABILITY_ONLY",
        "exact_runtime_offline_verified": True,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": "design_exact_runtime_p5_p6_requalification_v1",
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="final-offline-verifier-v5-evidence-acceptance-v1")
    sub = parser.add_subparsers(dest="command", required=True)
    preserve_parser = sub.add_parser("preserve")
    preserve_parser.add_argument("--repo-root", type=Path, required=True)
    preserve_parser.add_argument("--executed-notebook", type=Path, required=True)
    preserve_parser.add_argument("--terminal-log", type=Path, required=True)
    preserve_parser.add_argument("--evidence-zip", type=Path, required=True)
    for command in ("generate", "validate-implementation"):
        child = sub.add_parser(command)
        child.add_argument("--repo-root", type=Path, required=True)
    return parser


def main() -> int:
    try:
        args = _parser().parse_args()
        root = args.repo_root.resolve()
        if args.command == "preserve":
            result = preserve(
                root,
                notebook_path=args.executed_notebook.resolve(),
                log_path=args.terminal_log.resolve(),
                zip_path=args.evidence_zip.resolve(),
            )
        elif args.command == "generate":
            result = generate(root)
        else:
            result = validate_implementation(root)
        print(_canonical(result), end="")
        return 0
    except AcceptanceError as error:
        print(_canonical(error.envelope()), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
