"""Validate current CUDA 12.9 harness evidence integration and authorization readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_contracts as auth_contracts,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_contracts as execution_contracts,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

SOURCE_COMMIT: Final = "426f57dd11dddc2fb8e5a703721c2189abc7a0ff"
SOURCE_TOKEN: Final = "426f57d"
CURRENT_HARNESS_DIRECTORY_SHA256: Final = (
    "c3ea4ae6d047a8b3f3d5afc517e26c4f13fb4a82e48e3cf28cdfabdc343230e6"
)
CURRENT_HARNESS_FILE_COUNT: Final = 1_299
CURRENT_HARNESS_TOTAL_BYTES: Final = 11_632_357
CURRENT_HARNESS_OUTPUT_DIRECTORY: Final = "auragateway_qualification_harness_426f57d_v1"
CURRENT_HARNESS_MOUNTED_PATH: Final = (
    "/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-cu129-v1/"
    "ag_harness_materializer_cu129_v1_output/"
    "auragateway_qualification_harness_426f57d_v1"
)
CURRENT_HARNESS_KAGGLE_SLUG: Final = "kabomolefe/ag-harness-materializer-cu129-v1"
MATERIALIZER_SAVED_VERSION_ID: Final = 337034643
INSPECTION_SAVED_VERSION_ID: Final = 337035826
INSPECTION_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-harness-input-inspection-cu129-v1/notebook?scriptVersionId=337035826"
)
MATERIALIZER_RECOVERY_NOTEBOOK_SHA256: Final = (
    "27813e0d055080d58053f8ed038e0bb8c4e38f32aefcbde5993eab69515c6e74"
)
MATERIALIZATION_RECEIPT_SHA256: Final = (
    "07d81dbea5b5ed24d0786c0ee16782129e163834254c095262944baaf5c59db2"
)
MATERIALIZER_LOG_SHA256: Final = "c8bf05db62a12b2efb91492bec065b425d2c4c9b5264f54d2d9a0767e17946a4"
INSPECTION_LOG_SHA256: Final = "ed84a1273ef291517dc312c910042788f19f1a8adbd0caf92b0a90589da9cd44"
INSPECTION_EVIDENCE_ZIP_SHA256: Final = (
    "2d2f6afdd53787f6b3977e799dff441f9023a3c265ddf65d35855c5b62ad90d8"
)
RUNTIME_PACKAGE_COUNT: Final = 176
RUNTIME_RESOLUTION_LOCK_SHA256: Final = (
    "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
)
MODEL_SNAPSHOT_SHA256: Final = "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa"
CURRENT_RUNTIME_ADAPTER_SHA256: Final = (
    "aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"
)
CURRENT_MANIFEST_SHA256: Final = "f7289cee9414d03d88ceb4775198e15ff9446fd99771a58c187de0d4264ef94a"
CURRENT_MATERIALIZATION_RECORD_SHA256: Final = (
    "284b488dece09e6b17dcf72e4dea69bbdadd440356ce353622b100c38a02100a"
)
CURRENT_LAUNCHER_SOURCE_SHA256: Final = (
    "7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16"
)
CURRENT_LAUNCHER_NOTEBOOK_SHA256: Final = (
    "7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9"
)
AUTHORIZATION_SOURCE_BINDING_POLICY: Final = "CONTROL_PACKAGE_AUTHORIZATION_PARITY"
HISTORICAL_RUNTIME_ADAPTER_SHA256: Final = (
    "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"
)
EVIDENCE_ROOT: Final = Path("evidence_vault/local_abc/cu129-current-harness-input-inspection-v1")
EVIDENCE_IDENTITY_PATH: Final = EVIDENCE_ROOT / "evidence_identity.json"
MATERIALIZATION_RECEIPT_PATH: Final = (
    EVIDENCE_ROOT / "ag_harness_materialization_receipt_cu129_v1.json"
)
MATERIALIZER_LOG_PATH: Final = EVIDENCE_ROOT / "ag-harness-materializer-cu129-v1.log"
INSPECTION_LOG_PATH: Final = EVIDENCE_ROOT / "ag-harness-input-inspection-cu129-v1.log"
INSPECTION_ZIP_PATH: Final = EVIDENCE_ROOT / "ag-harness-input-inspection-cu129-v1.zip"
RECOVERY_NOTEBOOK_PATH: Final = EVIDENCE_ROOT / "ag_harness_materializer_cu129_v1_recovery.ipynb"
MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
MATERIALIZATION_RECORD_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json"
)
INTEGRATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_current_harness_evidence_integration_v1.json"
)
READINESS_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_fresh_authorization_readiness_review_v1.json"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
LAUNCHER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
)
LAUNCHER_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb"
)
LAUNCHER_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_kaggle_launcher_v1.md"
)
INTEGRATION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_current_harness_evidence_integration_v1.md"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-07-22-local-abc-cu129-current-harness-evidence-integration.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Current_Harness_Operational_Input_Closure_Report.md"
)
EXPECTED_ZIP_MEMBERS: Final = (
    "00_harness_input.json",
    "10_runtime_and_model_inputs.json",
    "20_source_boundary.json",
    "90_summary.json",
    "99_evidence_sha256.json",
)
ZIP_TIMESTAMP: Final = (1980, 1, 1, 0, 0, 0)


class HarnessEvidenceIntegrationError(RuntimeError):
    """Metadata-safe evidence-integration failure."""

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


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_ARGUMENT_INVALID",
            "evidence-integration arguments are invalid",
            details=(message,),
        )


class IntegrationSafety(LocalABCContract):
    """Fail-closed state retained by evidence integration and readiness review."""

    authorization_issued: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    measured_execution_authorized: Literal[False] = False


class EvidenceZipMember(LocalABCContract):
    """One exact member of the bounded metadata-only inspection bundle."""

    name: str
    sha256: str
    size_bytes: int = Field(ge=1, le=512 * 1024)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or len(path.parts) != 1 or path.as_posix() != value:
            raise ValueError("evidence member names must be flat POSIX filenames")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence member SHA-256 must be lowercase")
        return value


class EvidenceIdentity(LocalABCContract):
    """Frozen identities for one successful materializer and inspection pair."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-current-harness-input-inspection-evidence-v1"]
    source_commit: Literal["426f57dd11dddc2fb8e5a703721c2189abc7a0ff"]
    materializer_notebook_name: Literal["ag-harness-materializer-cu129-v1"]
    materializer_saved_version_id: Literal[337034643]
    materializer_recovery_notebook_sha256: str
    inspection_notebook_name: Literal["ag-harness-input-inspection-cu129-v1"]
    inspection_saved_version_id: Literal[337035826]
    inspection_saved_version_url: Literal[
        "https://www.kaggle.com/code/kabomolefe/"
        "ag-harness-input-inspection-cu129-v1/notebook?scriptVersionId=337035826"
    ]
    materialization_receipt_sha256: str
    materializer_log_sha256: str
    inspection_log_sha256: str
    inspection_evidence_zip_sha256: str
    inspection_evidence_members: tuple[EvidenceZipMember, ...]
    harness_directory_sha256: str
    harness_file_count: Literal[1299]
    harness_total_bytes: Literal[11632357]
    runtime_package_count: Literal[176]
    operational_input_closure: Literal["PASSED"]
    authorization_issued: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    model_requests_performed: Literal[0] = 0

    @field_validator(
        "materializer_recovery_notebook_sha256",
        "materialization_receipt_sha256",
        "materializer_log_sha256",
        "inspection_log_sha256",
        "inspection_evidence_zip_sha256",
        "harness_directory_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_member_set(self) -> Self:
        names = tuple(item.name for item in self.inspection_evidence_members)
        if names != EXPECTED_ZIP_MEMBERS:
            raise ValueError("inspection evidence member order or set drifted")
        return self


class MaterializationReceipt(LocalABCContract):
    """Consumed materializer receipt for the exact current source tree."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["CURRENT_CU129_HARNESS_MATERIALIZED"]
    producer_notebook_name: Literal["ag-harness-materializer-cu129-v1"]
    producer_output_directory: Literal["ag_harness_materializer_cu129_v1_output"]
    source_commit: Literal["426f57dd11dddc2fb8e5a703721c2189abc7a0ff"]
    input_dataset_name: Literal["ag-harness-426f57d-v1-input"]
    input_mode: Literal["kaggle_expanded_source_recovered_to_exact_archive"]
    archive_filename: Literal["ag-harness-426f57d-v1.zip"]
    archive_sha256: str
    source_inventory_sha256: str
    source_receipt_sha256: str
    source_sha256_manifest_sha256: str
    output_directory: Literal["auragateway_qualification_harness_426f57d_v1"]
    directory_sha256: str
    file_count: Literal[1299]
    total_bytes: Literal[11632357]
    nested_archives_present: Literal[False]
    symlinks_present: Literal[False]
    network_access_performed: Literal[False]
    package_installation_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    model_loaded: Literal[False]
    tokenizer_loaded: Literal[False]
    worker_started: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    authorization_issued: Literal[False]
    kaggle_auto_expanded_source_detected: Literal[True]
    exact_archive_reconstructed: Literal[True]

    @field_validator(
        "archive_sha256",
        "source_inventory_sha256",
        "source_receipt_sha256",
        "source_sha256_manifest_sha256",
        "directory_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("materialization receipt digests must be lowercase SHA-256")
        return value


class IntegrationDecisionRecord(LocalABCContract):
    """Repository decision consuming the immutable external evidence."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-current-harness-evidence-integration-v1"]
    decision: Literal["APPROVED_FOR_CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATION"]
    source_commit: Literal["426f57dd11dddc2fb8e5a703721c2189abc7a0ff"]
    harness_directory_sha256: str
    harness_file_count: Literal[1299]
    harness_total_bytes: Literal[11632357]
    materializer_saved_version_id: Literal[337034643]
    inspection_saved_version_id: Literal[337035826]
    inspection_evidence_zip_sha256: str
    materialization_receipt_sha256: str
    manifest_sha256: str
    materialization_record_sha256: str
    runtime_adapter_sha256: str
    launcher_source_sha256: str
    launcher_notebook_sha256: str
    authorization_source_binding_policy: Literal["CONTROL_PACKAGE_AUTHORIZATION_PARITY"]
    active_harness_binding_status: Literal["CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED"]
    operational_input_closure: Literal["PASSED"]
    safety: IntegrationSafety
    next_gate: Literal["fresh_cu129_authorization_issuance_implementation"]

    @field_validator(
        "harness_directory_sha256",
        "inspection_evidence_zip_sha256",
        "materialization_receipt_sha256",
        "manifest_sha256",
        "materialization_record_sha256",
        "runtime_adapter_sha256",
        "launcher_source_sha256",
        "launcher_notebook_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("integration identities must be lowercase SHA-256")
        return value


class FreshAuthorizationReadinessReview(LocalABCContract):
    """Fresh implementation review after current operational inputs close."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-fresh-authorization-readiness-review-v1"]
    decision: Literal["APPROVED_FOR_FRESH_CU129_AUTHORIZATION_ISSUANCE_IMPLEMENTATION"]
    source_commit: Literal["426f57dd11dddc2fb8e5a703721c2189abc7a0ff"]
    operational_input_closure: Literal["PASSED"]
    current_harness_directory_sha256: str
    current_manifest_sha256: str
    current_materialization_record_sha256: str
    current_runtime_adapter_sha256: str
    current_launcher_source_sha256: str
    current_launcher_notebook_sha256: str
    inspection_evidence_zip_sha256: str
    authorization_source_binding_policy: Literal["CONTROL_PACKAGE_AUTHORIZATION_PARITY"]
    final_authorization_present: Literal[False]
    runtime_package_count: Literal[176]
    historical_authorization_issuance_implementation_usable: Literal[False]
    required_implementation: tuple[str, ...]
    non_claims: tuple[str, ...]
    safety: IntegrationSafety
    next_gate: Literal["fresh_cu129_authorization_issuance_implementation"]

    @field_validator(
        "current_harness_directory_sha256",
        "current_manifest_sha256",
        "current_materialization_record_sha256",
        "current_runtime_adapter_sha256",
        "current_launcher_source_sha256",
        "current_launcher_notebook_sha256",
        "inspection_evidence_zip_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("readiness identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        required_fragments = (
            "post-integration merge commit",
            "current manifest",
            "current runtime adapter",
            "eight-request hard limits",
            "zero benchmark trajectory requests",
            "do not overwrite",
            "dynamic launcher-control authorization-source parity",
        )
        if len(self.required_implementation) != len(required_fragments) or any(
            fragment not in item
            for fragment, item in zip(required_fragments, self.required_implementation, strict=True)
        ):
            raise ValueError("fresh authorization implementation scope drifted")
        if len(self.non_claims) < 6:
            raise ValueError("fresh authorization non-claims are incomplete")
        return self


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_FILE_UNREADABLE",
            "an integration-bound file could not be read",
            path.as_posix(),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_JSON_INVALID",
            "an integration-bound JSON file is missing or invalid",
            path.as_posix(),
        ) from exc


def _load_canonical_contract(path: Path, model: type[LocalABCContract]) -> LocalABCContract:
    payload = _load_json(path)
    try:
        parsed = model.model_validate(payload)
    except ValidationError as exc:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_CONTRACT_INVALID",
            "an integration-bound JSON contract failed validation",
            path.as_posix(),
            details=tuple(str(item) for item in exc.errors())[:10],
        ) from exc
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_FILE_UNREADABLE",
            "an integration-bound file could not be read",
            path.as_posix(),
        ) from exc
    if raw != parsed.canonical_json():
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_JSON_NOT_CANONICAL",
            "an integration-bound JSON contract is not canonical",
            path.as_posix(),
        )
    return parsed


def _validate_evidence_zip(path: Path, identity: EvidenceIdentity) -> dict[str, object]:
    if _file_sha256(path) != INSPECTION_EVIDENCE_ZIP_SHA256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_ZIP_IDENTITY_DRIFT",
            "the inspection evidence ZIP identity drifted",
            path.as_posix(),
        )
    try:
        with zipfile.ZipFile(path) as archive:
            members = tuple(archive.infolist())
            names = tuple(item.filename for item in members)
            if names != EXPECTED_ZIP_MEMBERS or len(names) != len(set(names)):
                raise HarnessEvidenceIntegrationError(
                    "HARNESS_EVIDENCE_INTEGRATION_ZIP_MEMBER_SET_DRIFT",
                    "the inspection evidence ZIP member set or order drifted",
                    path.as_posix(),
                )
            payloads: dict[str, bytes] = {}
            for member in members:
                member_path = PurePosixPath(member.filename)
                if member_path.is_absolute() or len(member_path.parts) != 1:
                    raise HarnessEvidenceIntegrationError(
                        "HARNESS_EVIDENCE_INTEGRATION_ZIP_UNSAFE_MEMBER",
                        "the inspection evidence ZIP contains an unsafe member",
                        member.filename,
                    )
                unix_mode = member.external_attr >> 16
                if (
                    member.is_dir()
                    or member.flag_bits & 0x1
                    or member.date_time != ZIP_TIMESTAMP
                    or member.compress_type != zipfile.ZIP_DEFLATED
                    or stat.S_IFMT(unix_mode) != stat.S_IFREG
                    or unix_mode != 0o100644
                ):
                    raise HarnessEvidenceIntegrationError(
                        "HARNESS_EVIDENCE_INTEGRATION_ZIP_METADATA_DRIFT",
                        "an inspection evidence ZIP member metadata field drifted",
                        member.filename,
                    )
                payloads[member.filename] = archive.read(member)
    except zipfile.BadZipFile as exc:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_ZIP_INVALID",
            "the inspection evidence ZIP is invalid",
            path.as_posix(),
        ) from exc

    observed_members = tuple(
        EvidenceZipMember(
            name=name,
            sha256=_sha256_bytes(payloads[name]),
            size_bytes=len(payloads[name]),
        )
        for name in EXPECTED_ZIP_MEMBERS
    )
    if observed_members != identity.inspection_evidence_members:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_ZIP_MEMBER_IDENTITY_DRIFT",
            "an inspection evidence ZIP member identity drifted",
            path.as_posix(),
        )

    try:
        records: dict[str, object] = {
            name: cast(dict[str, object], json.loads(payloads[name]))
            for name in EXPECTED_ZIP_MEMBERS
        }
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_ZIP_JSON_INVALID",
            "an inspection evidence ZIP member is invalid JSON",
            path.as_posix(),
        ) from exc
    for name, payload in records.items():
        if payloads[name].decode("utf-8") != json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ):
            raise HarnessEvidenceIntegrationError(
                "HARNESS_EVIDENCE_INTEGRATION_ZIP_JSON_NOT_CANONICAL",
                "an inspection evidence ZIP JSON member is not canonical",
                name,
            )

    evidence_manifest = records["99_evidence_sha256.json"]
    expected_evidence_manifest = {
        name: _sha256_bytes(payloads[name])
        for name in EXPECTED_ZIP_MEMBERS
        if name != "99_evidence_sha256.json"
    }
    if evidence_manifest != expected_evidence_manifest:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_ZIP_HASH_MANIFEST_DRIFT",
            "the inspection evidence ZIP checksum manifest drifted",
            path.as_posix(),
        )
    return records


def _validate_cross_evidence(
    receipt: MaterializationReceipt,
    records: dict[str, object],
) -> None:
    harness = cast(dict[str, object], records["00_harness_input.json"])
    runtime = cast(dict[str, object], records["10_runtime_and_model_inputs.json"])
    source_boundary = cast(dict[str, object], records["20_source_boundary.json"])
    summary = cast(dict[str, object], records["90_summary.json"])

    expected_harness = {
        "status": "CURRENT_CU129_HARNESS_INPUT_VALIDATED",
        "source_commit": SOURCE_COMMIT,
        "directory_sha256": CURRENT_HARNESS_DIRECTORY_SHA256,
        "file_count": CURRENT_HARNESS_FILE_COUNT,
        "total_bytes": CURRENT_HARNESS_TOTAL_BYTES,
        "current_runtime_adapter_sha256": CURRENT_RUNTIME_ADAPTER_SHA256,
        "expected_current_runtime_adapter_sha256": CURRENT_RUNTIME_ADAPTER_SHA256,
        "historical_runtime_adapter_sha256": HISTORICAL_RUNTIME_ADAPTER_SHA256,
        "historical_adapter_resolved": False,
    }
    if any(harness.get(key) != value for key, value in expected_harness.items()):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_HARNESS_RECORD_DRIFT",
            "the validated harness evidence record drifted",
        )
    expected_runtime = {
        "status": "CURRENT_CU129_RUNTIME_AND_MODEL_INPUTS_VALIDATED",
        "package_count": RUNTIME_PACKAGE_COUNT,
        "manifest_entry_count": 182,
        "runtime_resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
        "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
        "model_weights_loaded": False,
        "wheel_payloads_rehashed": False,
    }
    if any(runtime.get(key) != value for key, value in expected_runtime.items()):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_RUNTIME_RECORD_DRIFT",
            "the validated runtime and model evidence record drifted",
        )
    expected_source_boundary = {
        "status": "CURRENT_CU129_SOURCE_BOUNDARY_VALIDATED",
        "active_harness_binding_status": "HISTORICAL_PENDING_EVIDENCE_INTEGRATION",
        "authorization_issued": False,
        "package_installation_performed": False,
        "gpu_execution_performed": False,
        "model_loaded": False,
        "worker_started": False,
        "model_requests_performed": 0,
    }
    if any(source_boundary.get(key) != value for key, value in expected_source_boundary.items()):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_SOURCE_BOUNDARY_DRIFT",
            "the validated source-boundary evidence record drifted",
        )
    expected_summary = {
        "inspection_status": "CURRENT_CU129_HARNESS_INPUT_INSPECTION_PASSED",
        "operational_input_closure": "PASSED",
        "source_commit": SOURCE_COMMIT,
        "harness_directory_sha256": CURRENT_HARNESS_DIRECTORY_SHA256,
        "runtime_resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
        "runtime_package_count": RUNTIME_PACKAGE_COUNT,
        "network_access_performed": False,
        "gpu_execution_performed": False,
        "package_installation_performed": False,
        "model_loaded": False,
        "tokenizer_loaded": False,
        "worker_started": False,
        "model_requests_performed": 0,
        "authorization_issued": False,
        "next_gate": "integrate_current_cu129_harness_materialization_evidence",
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_SUMMARY_DRIFT",
            "the successful inspection summary drifted",
        )
    receipt_parity = (
        receipt.source_commit == summary["source_commit"],
        receipt.directory_sha256 == summary["harness_directory_sha256"],
        receipt.directory_sha256 == harness["directory_sha256"],
        receipt.file_count == harness["file_count"],
        receipt.total_bytes == harness["total_bytes"],
    )
    if not all(receipt_parity):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_CROSS_EVIDENCE_DRIFT",
            "materializer and inspection evidence identities disagree",
        )


def _validate_logs(root: Path) -> None:
    paths_and_fragments = {
        MATERIALIZER_LOG_PATH: (
            "status=CURRENT_CU129_HARNESS_MATERIALIZED",
            f"source_commit={SOURCE_COMMIT}",
            f"file_count={CURRENT_HARNESS_FILE_COUNT}",
            f"total_bytes={CURRENT_HARNESS_TOTAL_BYTES}",
            f"directory_sha256={CURRENT_HARNESS_DIRECTORY_SHA256}",
            "exact_archive_reconstructed=true",
            "authorization_issued=false",
        ),
        INSPECTION_LOG_PATH: (
            "inspection_status=CURRENT_CU129_HARNESS_INPUT_INSPECTION_PASSED",
            "operational_input_closure=PASSED",
            f"source_commit={SOURCE_COMMIT}",
            f"harness_directory_sha256={CURRENT_HARNESS_DIRECTORY_SHA256}",
            "runtime_package_count=176",
            "authorization_issued=false",
        ),
    }
    expected_hashes = {
        MATERIALIZER_LOG_PATH: MATERIALIZER_LOG_SHA256,
        INSPECTION_LOG_PATH: INSPECTION_LOG_SHA256,
    }
    for relative_path, fragments in paths_and_fragments.items():
        path = root / relative_path
        if _file_sha256(path) != expected_hashes[relative_path]:
            raise HarnessEvidenceIntegrationError(
                "HARNESS_EVIDENCE_INTEGRATION_LOG_IDENTITY_DRIFT",
                "a preserved successful Kaggle log identity drifted",
                relative_path.as_posix(),
            )
        text = path.read_text(encoding="utf-8")
        if any(fragment not in text for fragment in fragments):
            raise HarnessEvidenceIntegrationError(
                "HARNESS_EVIDENCE_INTEGRATION_LOG_CONTENT_DRIFT",
                "a preserved successful Kaggle log lost required signals",
                relative_path.as_posix(),
            )


def _validate_active_repository(root: Path) -> tuple[str, str]:
    try:
        manifest = execution_contracts.QualificationDatasetManifest.model_validate(
            _load_json(root / MANIFEST_PATH)
        )
        materialization = auth_contracts.MaterializedOfflineDatasetRecord.model_validate(
            _load_json(root / MATERIALIZATION_RECORD_PATH)
        )
    except ValidationError as exc:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_ACTIVE_CONTRACT_INVALID",
            "the active manifest or materialization record failed typed validation",
            details=tuple(str(item) for item in exc.errors())[:10],
        ) from exc
    if (root / MANIFEST_PATH).read_text(encoding="utf-8") != manifest.canonical_json():
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_MANIFEST_NOT_CANONICAL",
            "the active dataset manifest is not canonical JSON",
            MANIFEST_PATH.as_posix(),
        )
    if (root / MATERIALIZATION_RECORD_PATH).read_text(
        encoding="utf-8"
    ) != materialization.canonical_json():
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_RECORD_NOT_CANONICAL",
            "the active materialization record is not canonical JSON",
            MATERIALIZATION_RECORD_PATH.as_posix(),
        )
    harness_manifest = manifest.entries[0]
    harness_record = materialization.entries[0]
    expected_harness = (
        harness_manifest.mounted_path == CURRENT_HARNESS_MOUNTED_PATH,
        harness_manifest.sha256 == CURRENT_HARNESS_DIRECTORY_SHA256,
        harness_record.kaggle_dataset_slug == CURRENT_HARNESS_KAGGLE_SLUG,
        harness_record.kaggle_dataset_version == 1,
        harness_record.mounted_path == CURRENT_HARNESS_MOUNTED_PATH,
        harness_record.sha256 == CURRENT_HARNESS_DIRECTORY_SHA256,
        materialization.harness_source_commit == SOURCE_COMMIT,
        materialization.runtime_manifest_sha256 == manifest.fingerprint(),
    )
    if not all(expected_harness):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_ACTIVE_HARNESS_DRIFT",
            "the active manifest or materialization record does not bind the current harness",
        )
    runtime_manifest = manifest.entries[2]
    runtime_record = materialization.entries[2]
    runtime_parity = (
        runtime_manifest.package_count == RUNTIME_PACKAGE_COUNT,
        runtime_record.package_count == RUNTIME_PACKAGE_COUNT,
        runtime_manifest.resolution_lock_sha256 == RUNTIME_RESOLUTION_LOCK_SHA256,
        runtime_record.resolution_lock_sha256 == RUNTIME_RESOLUTION_LOCK_SHA256,
    )
    if not all(runtime_parity):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_RUNTIME_AUTHORITY_DRIFT",
            "the active CUDA 12.9 runtime authority drifted",
        )
    return manifest.fingerprint(), materialization.fingerprint()


def _validate_launcher(root: Path) -> dict[str, object]:
    from auragateway.local_abc import (
        full_abc_local_environment_qualification_kaggle_launcher as launcher,
    )

    if launcher.SOURCE_MAIN_MERGE_COMMIT != SOURCE_COMMIT:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_LAUNCHER_SOURCE_DRIFT",
            "the launcher source authority does not bind the current harness",
            LAUNCHER_SOURCE_PATH.as_posix(),
        )
    if launcher.HARNESS_SOURCE_PATH != CURRENT_HARNESS_MOUNTED_PATH:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_LAUNCHER_MOUNT_DRIFT",
            "the launcher harness mounted path drifted",
            LAUNCHER_SOURCE_PATH.as_posix(),
        )
    if launcher.AUTHORIZATION_SOURCE_BINDING_POLICY != AUTHORIZATION_SOURCE_BINDING_POLICY:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_AUTHORIZATION_POLICY_DRIFT",
            "the launcher authorization-source parity policy drifted",
            LAUNCHER_SOURCE_PATH.as_posix(),
        )
    verification = launcher.verify_launcher_notebook(
        repo_root=root,
        notebook_path=root / LAUNCHER_NOTEBOOK_PATH,
    )
    if _file_sha256(root / LAUNCHER_SOURCE_PATH) != CURRENT_LAUNCHER_SOURCE_SHA256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_LAUNCHER_SOURCE_IDENTITY_DRIFT",
            "the launcher source identity drifted",
            LAUNCHER_SOURCE_PATH.as_posix(),
        )
    if verification.notebook_sha256 != CURRENT_LAUNCHER_NOTEBOOK_SHA256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_LAUNCHER_NOTEBOOK_IDENTITY_DRIFT",
            "the generated launcher notebook identity drifted",
            LAUNCHER_NOTEBOOK_PATH.as_posix(),
        )
    return verification.model_dump(mode="json")


def _validate_documentation(root: Path) -> None:
    required = {
        ADR_PATH: (
            "CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED",
            "CONTROL_PACKAGE_AUTHORIZATION_PARITY",
        ),
        REPORT_PATH: (
            "operational_input_closure=PASSED",
            INSPECTION_EVIDENCE_ZIP_SHA256,
        ),
        INTEGRATION_RUNBOOK_PATH: (
            "337034643",
            "337035826",
            "authorization_issued=false",
        ),
        LAUNCHER_RUNBOOK_PATH: (
            CURRENT_HARNESS_MOUNTED_PATH,
            "fresh_cu129_authorization_issuance_implementation",
        ),
    }
    for relative_path, fragments in required.items():
        text = (root / relative_path).read_text(encoding="utf-8")
        if any(fragment not in text for fragment in fragments):
            raise HarnessEvidenceIntegrationError(
                "HARNESS_EVIDENCE_INTEGRATION_DOCUMENTATION_DRIFT",
                "evidence-integration documentation drifted",
                relative_path.as_posix(),
            )


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    """Validate immutable evidence, active bindings, and the blocked next gate."""

    root = Path(repo_root).resolve()
    identity = cast(
        EvidenceIdentity,
        _load_canonical_contract(root / EVIDENCE_IDENTITY_PATH, EvidenceIdentity),
    )
    receipt = cast(
        MaterializationReceipt,
        _load_canonical_contract(root / MATERIALIZATION_RECEIPT_PATH, MaterializationReceipt),
    )
    integration = cast(
        IntegrationDecisionRecord,
        _load_canonical_contract(root / INTEGRATION_RECORD_PATH, IntegrationDecisionRecord),
    )
    readiness = cast(
        FreshAuthorizationReadinessReview,
        _load_canonical_contract(root / READINESS_REVIEW_PATH, FreshAuthorizationReadinessReview),
    )

    expected_identities = {
        RECOVERY_NOTEBOOK_PATH: MATERIALIZER_RECOVERY_NOTEBOOK_SHA256,
        MATERIALIZATION_RECEIPT_PATH: MATERIALIZATION_RECEIPT_SHA256,
        MATERIALIZER_LOG_PATH: MATERIALIZER_LOG_SHA256,
        INSPECTION_LOG_PATH: INSPECTION_LOG_SHA256,
        INSPECTION_ZIP_PATH: INSPECTION_EVIDENCE_ZIP_SHA256,
    }
    drift = tuple(
        path.as_posix()
        for path, expected_sha256 in expected_identities.items()
        if _file_sha256(root / path) != expected_sha256
    )
    if drift:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_EXTERNAL_IDENTITY_DRIFT",
            "one or more consumed external evidence identities drifted",
            details=drift,
        )
    if (
        identity.materializer_recovery_notebook_sha256 != MATERIALIZER_RECOVERY_NOTEBOOK_SHA256
        or identity.materialization_receipt_sha256 != MATERIALIZATION_RECEIPT_SHA256
        or identity.inspection_evidence_zip_sha256 != INSPECTION_EVIDENCE_ZIP_SHA256
    ):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_IDENTITY_REGISTRY_DRIFT",
            "the evidence identity registry drifted from consumed artifacts",
        )

    records = _validate_evidence_zip(root / INSPECTION_ZIP_PATH, identity)
    _validate_cross_evidence(receipt, records)
    _validate_logs(root)
    manifest_sha256, materialization_sha256 = _validate_active_repository(root)
    if manifest_sha256 != CURRENT_MANIFEST_SHA256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_MANIFEST_IDENTITY_DRIFT",
            "the active manifest identity drifted from the integrated authority",
            MANIFEST_PATH.as_posix(),
        )
    if materialization_sha256 != CURRENT_MATERIALIZATION_RECORD_SHA256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_MATERIALIZATION_IDENTITY_DRIFT",
            "the active materialization-record identity drifted",
            MATERIALIZATION_RECORD_PATH.as_posix(),
        )
    if _file_sha256(root / auth_contracts.RUNTIME_ADAPTER_PATH) != CURRENT_RUNTIME_ADAPTER_SHA256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_RUNTIME_ADAPTER_IDENTITY_DRIFT",
            "the current runtime adapter identity drifted",
            auth_contracts.RUNTIME_ADAPTER_PATH.as_posix(),
        )
    if integration.manifest_sha256 != manifest_sha256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_DECISION_MANIFEST_DRIFT",
            "the integration decision no longer binds the active manifest",
        )
    if integration.materialization_record_sha256 != materialization_sha256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_DECISION_MATERIALIZATION_DRIFT",
            "the integration decision no longer binds the active materialization record",
        )
    if readiness.current_manifest_sha256 != manifest_sha256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_READINESS_MANIFEST_DRIFT",
            "the readiness review no longer binds the active manifest",
        )
    if readiness.current_materialization_record_sha256 != materialization_sha256:
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_READINESS_MATERIALIZATION_DRIFT",
            "the readiness review no longer binds the active materialization record",
        )
    if (
        integration.harness_directory_sha256 != receipt.directory_sha256
        or readiness.current_harness_directory_sha256 != receipt.directory_sha256
    ):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_DECISION_HARNESS_DRIFT",
            "integration decisions no longer bind the consumed harness",
        )
    launcher_summary = _validate_launcher(root)
    expected_decision_identities = (
        integration.runtime_adapter_sha256 == CURRENT_RUNTIME_ADAPTER_SHA256,
        integration.launcher_source_sha256 == CURRENT_LAUNCHER_SOURCE_SHA256,
        integration.launcher_notebook_sha256 == CURRENT_LAUNCHER_NOTEBOOK_SHA256,
        integration.authorization_source_binding_policy == AUTHORIZATION_SOURCE_BINDING_POLICY,
        readiness.current_runtime_adapter_sha256 == CURRENT_RUNTIME_ADAPTER_SHA256,
        readiness.current_launcher_source_sha256 == CURRENT_LAUNCHER_SOURCE_SHA256,
        readiness.current_launcher_notebook_sha256 == CURRENT_LAUNCHER_NOTEBOOK_SHA256,
        readiness.inspection_evidence_zip_sha256 == INSPECTION_EVIDENCE_ZIP_SHA256,
        readiness.authorization_source_binding_policy == AUTHORIZATION_SOURCE_BINDING_POLICY,
        readiness.final_authorization_present is False,
    )
    if not all(expected_decision_identities):
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_DECISION_IDENTITY_DRIFT",
            "integration or readiness identities drifted from active authorities",
        )
    _validate_documentation(root)
    if (root / FINAL_AUTHORIZATION_PATH).exists():
        raise HarnessEvidenceIntegrationError(
            "HARNESS_EVIDENCE_INTEGRATION_PREMATURE_AUTHORIZATION",
            "the final authorization exists before fresh issuance implementation",
            FINAL_AUTHORIZATION_PATH.as_posix(),
        )

    return {
        "status": "CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED",
        "decision": integration.decision,
        "operational_input_closure": "PASSED",
        "source_commit": SOURCE_COMMIT,
        "harness_directory_sha256": CURRENT_HARNESS_DIRECTORY_SHA256,
        "harness_file_count": CURRENT_HARNESS_FILE_COUNT,
        "harness_total_bytes": CURRENT_HARNESS_TOTAL_BYTES,
        "runtime_package_count": RUNTIME_PACKAGE_COUNT,
        "manifest_sha256": manifest_sha256,
        "materialization_record_sha256": materialization_sha256,
        "inspection_evidence_zip_sha256": INSPECTION_EVIDENCE_ZIP_SHA256,
        "materializer_saved_version_id": MATERIALIZER_SAVED_VERSION_ID,
        "inspection_saved_version_id": INSPECTION_SAVED_VERSION_ID,
        "launcher_notebook_sha256": launcher_summary["notebook_sha256"],
        "authorization_source_binding_policy": AUTHORIZATION_SOURCE_BINDING_POLICY,
        "authorization_issued": False,
        "gpu_execution_performed": False,
        "model_requests_performed": 0,
        "measured_execution_authorized": False,
        "next_gate": readiness.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    """Validate the integrated evidence boundary and print safe machine output."""

    try:
        arguments = _build_parser().parse_args(argv)
        result = validate_repository_package(arguments.repo_root)
        for key, value in result.items():
            rendered = str(value).lower() if isinstance(value, bool) else value
            print(f"{key}={rendered}")
        return 0
    except HarnessEvidenceIntegrationError as exc:
        envelope = {
            "error_code": exc.error_code,
            "safe_message": exc.safe_message,
            "path": exc.path,
            "details": exc.details,
        }
        print(json.dumps(envelope, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
