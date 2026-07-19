"""Validate the bounded control-output discovery remediation package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final, Literal, cast

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_environment_qualification_"
    "control_output_discovery_remediation_v1.json"
)
EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/environment-qualification-control-output-discovery-failure-v1"
)
LAUNCHER_FAILURE_PATH: Final = EVIDENCE_DIRECTORY / "launcher_failure.json"
LAUNCHER_FAILURE_TRACE_PATH: Final = EVIDENCE_DIRECTORY / "launcher_failure_trace.txt"
EVIDENCE_SHA256_PATH: Final = EVIDENCE_DIRECTORY / "evidence_sha256.json"
LAUNCHER_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb"
)

EXPECTED_EVIDENCE_ZIP_SHA256: Final = (
    "55910873d6282ce8b98efd2726d2630bfed4f1c706eb4ec6484adb8a66885926"
)
EXPECTED_LAUNCHER_FAILURE_SHA256: Final = (
    "7983ce6c26fda353a1abdbf8f279911f111e7964dfd335eac29551cc6b0185ba"
)
EXPECTED_TRACE_SHA256: Final = "c0216790e19642ea907555ad94505c7bb1fae29a6992000474375edf93b37c69"
EXPECTED_EVIDENCE_SHA256_FILE_SHA256: Final = (
    "15cced4ecf960e603959cc8c8afcf43c4c7a3a2ef1e5ce7f7702b83fab8f41e9"
)
EXPECTED_LAUNCHER_SHA256: Final = "33e85b6982d9a07328854e922d1a4a0dadc15a92bebf6805e9c2dfa21c18624e"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceBinding(_StrictModel):
    evidence_directory: Literal[
        "evidence_vault/local_abc/environment-qualification-control-output-discovery-failure-v1"
    ]
    source_evidence_zip_name: Literal["ag-qualification-evidence-v1.zip"]
    source_evidence_zip_sha256: str
    launcher_failure_path: Literal[
        "evidence_vault/local_abc/"
        "environment-qualification-control-output-discovery-failure-v1/"
        "launcher_failure.json"
    ]
    launcher_failure_sha256: str
    launcher_failure_trace_path: Literal[
        "evidence_vault/local_abc/"
        "environment-qualification-control-output-discovery-failure-v1/"
        "launcher_failure_trace.txt"
    ]
    launcher_failure_trace_sha256: str
    evidence_sha256_path: Literal[
        "evidence_vault/local_abc/"
        "environment-qualification-control-output-discovery-failure-v1/"
        "evidence_sha256.json"
    ]
    evidence_sha256_file_sha256: str

    @field_validator(
        "source_evidence_zip_sha256",
        "launcher_failure_sha256",
        "launcher_failure_trace_sha256",
        "evidence_sha256_file_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("evidence digests must be lowercase SHA-256")
        return value


class FailureClassification(_StrictModel):
    status: Literal["FAILED"]
    failure_class: Literal["INPUT_DISCOVERY_FAILURE"]
    failure_code: Literal["CONTROL_OUTPUT_NAMESPACE_COLLISION"]
    stage: Literal["control_output_discovery"]
    exception_type: Literal["RuntimeError"]
    safe_message: Literal[
        "control output must expose exactly one authorization, manifest, "
        "control manifest, and receipt"
    ]
    captured_at: Literal["2026-07-19T19:46:08+00:00"]
    first_divergence: Literal[
        "global filename uniqueness was enforced before the governed "
        "control-output root was resolved"
    ]
    duplicate_filename: Literal["offline_dataset_manifest.json"]


class RemediationContract(_StrictModel):
    discovery_scope: Literal["governed_control_output_root"]
    control_notebook_token: Literal["ag-qualification-control-materializer-v1"]
    control_output_directory_name: Literal["ag_qualification_control_v1"]
    exact_flat_file_set: tuple[str, ...]
    global_filename_uniqueness_required: Literal[False] = False
    unrelated_input_filename_collisions_ignored: Literal[True] = True
    multiple_governed_roots_rejected: Literal[True] = True
    wrapper_directories_accepted: Literal[False] = False
    nested_archives_accepted: Literal[False] = False
    symbolic_links_accepted: Literal[False] = False
    launcher_notebook_sha256: str
    reviewed_core_sha256: Literal[
        "b5f9b3ab7534f3a17b6b82c214edbac8bdcce650b4572721abdb054c35d0c613"
    ]

    @field_validator("launcher_notebook_sha256")
    @classmethod
    def validate_launcher_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("launcher digest must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_exact_file_set(self) -> RemediationContract:
        expected = (
            "auragateway_full_abc_local_full_run_environment_qualification_"
            "execution_authorization_v1.json",
            "control_package_manifest.json",
            "materialization_receipt.json",
            "offline_dataset_manifest.json",
        )
        if self.exact_flat_file_set != expected:
            raise ValueError("control output file contract drifted")
        return self


class SafetyEnvelope(_StrictModel):
    authorization_committed: Literal[False] = False
    benchmark_trajectory_requests_performed: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0
    hosted_provider_calls_performed: Literal[False] = False
    kaggle_gpu_session_started: Literal[True] = True
    model_requests_performed: Literal[0] = 0
    model_runtime_started: Literal[False] = False
    network_access_performed: Literal[False] = False
    runtime_evidence_generated: Literal[False] = False
    worker_started: Literal[False] = False


class ControlOutputDiscoveryRemediationRecord(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-full-abc-local-environment-qualification-"
        "control-output-discovery-remediation-v1"
    ]
    decision: Literal["APPROVED_FOR_BOUNDED_LAUNCHER_REMEDIATION"]
    evidence: EvidenceBinding
    failure: FailureClassification
    remediation: RemediationContract
    safety: SafetyEnvelope
    authorization_identity_exposed_by_failure_bundle: Literal[False] = False
    harness_rebuild_required: Literal[False] = False
    model_identity_changed: Literal[False] = False
    vllm_wheel_identity_changed: Literal[False] = False
    next_gate: Literal["merge_control_root_scoped_launcher_then_issue_fresh_authorization"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_bindings(self) -> ControlOutputDiscoveryRemediationRecord:
        if self.evidence.source_evidence_zip_sha256 != EXPECTED_EVIDENCE_ZIP_SHA256:
            raise ValueError("source evidence ZIP identity drifted")
        if self.evidence.launcher_failure_sha256 != EXPECTED_LAUNCHER_FAILURE_SHA256:
            raise ValueError("launcher failure identity drifted")
        if self.evidence.launcher_failure_trace_sha256 != EXPECTED_TRACE_SHA256:
            raise ValueError("launcher failure trace identity drifted")
        if self.evidence.evidence_sha256_file_sha256 != EXPECTED_EVIDENCE_SHA256_FILE_SHA256:
            raise ValueError("evidence checksum file identity drifted")
        if self.remediation.launcher_notebook_sha256 != EXPECTED_LAUNCHER_SHA256:
            raise ValueError("remediated launcher identity drifted")
        return self


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path.as_posix()}")
    return cast(dict[str, object], payload)


def load_record(path: Path) -> ControlOutputDiscoveryRemediationRecord:
    try:
        return ControlOutputDiscoveryRemediationRecord.model_validate(_load_json_object(path))
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise RuntimeError("control-output discovery remediation record is invalid") from exc


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record_path = root / RECORD_PATH
    record = load_record(record_path)

    expected_file_hashes = {
        record.evidence.launcher_failure_path: (record.evidence.launcher_failure_sha256),
        record.evidence.launcher_failure_trace_path: (
            record.evidence.launcher_failure_trace_sha256
        ),
        record.evidence.evidence_sha256_path: (record.evidence.evidence_sha256_file_sha256),
        LAUNCHER_PATH.as_posix(): record.remediation.launcher_notebook_sha256,
    }
    drift = tuple(
        sorted(
            path
            for path, expected_sha256 in expected_file_hashes.items()
            if not (root / path).is_file() or _file_sha256(root / path) != expected_sha256
        )
    )
    if drift:
        raise RuntimeError(
            "control-output discovery remediation package drifted: " + ", ".join(drift)
        )

    failure = _load_json_object(root / LAUNCHER_FAILURE_PATH)
    expected_failure = {
        "status": record.failure.status,
        "stage": record.failure.stage,
        "exception_type": record.failure.exception_type,
        "safe_message": record.failure.safe_message,
        "captured_at": record.failure.captured_at,
        "provider_calls_performed": False,
        "external_spend": 0,
        "credentials_used": False,
        "customer_data_used": False,
        "runtime_evidence_found": [],
    }
    failure_drift = tuple(
        sorted(
            key
            for key, expected_value in expected_failure.items()
            if failure.get(key) != expected_value
        )
    )
    if failure_drift:
        raise RuntimeError("captured launcher failure fields drifted: " + ", ".join(failure_drift))

    evidence_checksums = _load_json_object(root / EVIDENCE_SHA256_PATH)
    if evidence_checksums.get("source_evidence_zip_sha256") != (EXPECTED_EVIDENCE_ZIP_SHA256):
        raise RuntimeError("evidence ZIP checksum binding drifted")
    files = evidence_checksums.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("evidence checksum file map is invalid")
    expected_checksums = {
        LAUNCHER_FAILURE_PATH.name: EXPECTED_LAUNCHER_FAILURE_SHA256,
        LAUNCHER_FAILURE_TRACE_PATH.name: EXPECTED_TRACE_SHA256,
    }
    if files != expected_checksums:
        raise RuntimeError("evidence member checksum bindings drifted")

    from auragateway.local_abc import (
        full_abc_local_environment_qualification_kaggle_launcher as launcher,
    )

    launcher_summary = launcher.verify_launcher_notebook(
        repo_root=root,
        notebook_path=root / LAUNCHER_PATH,
    )
    if launcher_summary.notebook_sha256 != EXPECTED_LAUNCHER_SHA256:
        raise RuntimeError("launcher verifier reported an unexpected identity")

    launcher_notebook = _load_json_object(root / LAUNCHER_PATH)
    metadata = launcher_notebook.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("launcher metadata is invalid")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise RuntimeError("AuraGateway launcher metadata is invalid")
    expected_metadata = {
        "control_discovery_failure_code": record.failure.failure_code,
        "control_discovery_failure_evidence_sha256": (record.evidence.source_evidence_zip_sha256),
        "control_output_directory_name": (record.remediation.control_output_directory_name),
        "control_output_discovery_scope": record.remediation.discovery_scope,
    }
    metadata_drift = tuple(
        sorted(
            key
            for key, expected_value in expected_metadata.items()
            if auragateway.get(key) != expected_value
        )
    )
    if metadata_drift:
        raise RuntimeError("launcher remediation metadata drifted: " + ", ".join(metadata_drift))

    return {
        "status": "CONTROL_OUTPUT_DISCOVERY_REMEDIATION_PACKAGE_VALID",
        "record_sha256": _file_sha256(record_path),
        "failure_class": record.failure.failure_class,
        "failure_code": record.failure.failure_code,
        "failure_stage": record.failure.stage,
        "evidence_zip_sha256": record.evidence.source_evidence_zip_sha256,
        "evidence_files_verified": 3,
        "launcher_sha256": launcher_summary.notebook_sha256,
        "discovery_scope": record.remediation.discovery_scope,
        "authorization_issued": False,
        "kaggle_gpu_session_started": record.safety.kaggle_gpu_session_started,
        "model_runtime_started": record.safety.model_runtime_started,
        "model_requests_performed": 0,
        "next_gate": record.next_gate,
    }
