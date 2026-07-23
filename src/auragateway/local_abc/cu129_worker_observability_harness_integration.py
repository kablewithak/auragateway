"""Validate worker-observability CUDA 12.9 harness evidence integration."""

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

SOURCE_COMMIT: Final = "dceda98989386de7a4d57616f9f8a8023f866f10"
SOURCE_TOKEN: Final = "dceda98"
CURRENT_HARNESS_DIRECTORY_SHA256: Final = (
    "c66f2589bdf55ab34f82bffc1eaaa4b4c7e73cb8195867333ccd99a58438f3e4"
)
CURRENT_HARNESS_FILE_COUNT: Final = 1_076
CURRENT_HARNESS_TOTAL_BYTES: Final = 10_850_278
CURRENT_HARNESS_OUTPUT_DIRECTORY: Final = "auragateway_qualification_harness_dceda98_worker_obs_v1"
CURRENT_HARNESS_MOUNTED_PATH: Final = (
    "/kaggle/input/notebooks/kabomolefe/"
    "ag-worker-obs-harness-materializer-v1/"
    "ag_worker_obs_harness_materializer_v1_output/"
    "auragateway_qualification_harness_dceda98_worker_obs_v1"
)
CURRENT_HARNESS_KAGGLE_SLUG: Final = "kabomolefe/ag-worker-obs-harness-materializer-v1"
MATERIALIZER_SAVED_VERSION_ID: Final = 337284215
INSPECTION_SAVED_VERSION_ID: Final = 337286728
MATERIALIZER_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-worker-obs-harness-materializer-v1/notebook?scriptVersionId=337284215"
)
INSPECTION_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-worker-obs-input-inspection-v1/notebook?scriptVersionId=337286728"
)
MATERIALIZER_RECOVERY_NOTEBOOK_SHA256: Final = (
    "c9fc3b5435dae4ecba79fb9f8a3b6c113b9a0bcf4dafd31884b095b232f372d1"
)
MATERIALIZATION_RECEIPT_SHA256: Final = (
    "5f2818130abcf338239f49f38683fbdb00c2a290816115925e74e508ea9d0f02"
)
MATERIALIZER_LOG_SHA256: Final = "eda73ed32456a1018898e3b3dcda26f785b2ba97b0b96a7426ccd34df1d81ba8"
INSPECTION_LOG_SHA256: Final = "4cde9268c456aa669151f5a7223c963c587f034928b025d8d447bbec562236e9"
INSPECTION_EVIDENCE_ZIP_SHA256: Final = (
    "e1bf87f44c3ccbf3eda65938cb61b833c95edfb7c200e5f40095eab9e3f936fb"
)
RUNTIME_PACKAGE_COUNT: Final = 176
RUNTIME_RESOLUTION_LOCK_SHA256: Final = (
    "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
)
MODEL_SNAPSHOT_SHA256: Final = "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa"
CURRENT_RUNTIME_ADAPTER_SHA256: Final = (
    "f83452b6fbfd583f4236c2edbaf0e4bd3a6ece331494fdff891bf50d022ba617"
)
CURRENT_WORKER_DIAGNOSTICS_SHA256: Final = (
    "58d39a67c9d82d1b2f5938328dfa9362ee922ced2e089f8b5d529c0139cc2b91"
)
MATERIALIZED_HARNESS_LAUNCHER_SOURCE_SHA256: Final = (
    "454d5e6fe7f7ff5711710d140f0bece3ee84f3a863a7c33316f784af13724bd0"
)
MATERIALIZED_HARNESS_LAUNCHER_NOTEBOOK_SHA256: Final = (
    "8477a8f389fe21a925d87c6c4e5b7a71e9de1b1c09910d5d293eadbf6b73db26"
)
CURRENT_MANIFEST_SHA256: Final = "6c998716849d20e68ded4cce3a113a791a0d863bc97d2c5027991ad6a5615d8f"
CURRENT_MATERIALIZATION_RECORD_SHA256: Final = (
    "a3f5cfee599b4a0258e3ac48a40f1ee27c2e9b85dd624df6fdb53079e6a6b223"
)
CURRENT_LAUNCHER_SOURCE_SHA256: Final = (
    "47a91da2c70f2fa5db93398a3d41cc807b292df84bcac4688479e38f0b0896dc"
)
CURRENT_LAUNCHER_NOTEBOOK_SHA256: Final = (
    "804cc1a0f9da7e1492f179bec7b65e3c7e511a529e38b2c0183a3debbf69670e"
)
AUTHORIZATION_SOURCE_BINDING_POLICY: Final = "CONTROL_PACKAGE_AUTHORIZATION_PARITY"
HISTORICAL_HARNESS_DIRECTORY_SHA256: Final = (
    "c3ea4ae6d047a8b3f3d5afc517e26c4f13fb4a82e48e3cf28cdfabdc343230e6"
)
HISTORICAL_HARNESS_OUTPUT_DIRECTORY: Final = "auragateway_qualification_harness_426f57d_v1"
HISTORICAL_RUNTIME_ADAPTER_SHA256: Final = (
    "aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"
)

EVIDENCE_ROOT: Final = Path(
    "evidence_vault/local_abc/cu129-worker-observability-harness-input-inspection-v1"
)
EVIDENCE_IDENTITY_PATH: Final = EVIDENCE_ROOT / "evidence_identity.json"
MATERIALIZATION_RECEIPT_PATH: Final = EVIDENCE_ROOT / "materialization_receipt.json"
MATERIALIZER_LOG_PATH: Final = EVIDENCE_ROOT / "ag-worker-obs-harness-materializer-v1.log"
INSPECTION_LOG_PATH: Final = EVIDENCE_ROOT / "ag-worker-obs-input-inspection-v1.log"
INSPECTION_ZIP_PATH: Final = EVIDENCE_ROOT / "ag-worker-obs-input-inspection-v1.zip"
RECOVERY_NOTEBOOK_PATH: Final = (
    EVIDENCE_ROOT / "ag_worker_obs_harness_materializer_v1_recovery.ipynb"
)
MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
MATERIALIZATION_RECORD_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json"
)
INTEGRATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_worker_observability_harness_evidence_integration_v1.json"
)
READINESS_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_worker_observability_fresh_authorization_readiness_review_v1.json"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
RUNTIME_ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
WORKER_DIAGNOSTICS_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_worker_startup_diagnostics.py"
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
AUTHORIZATION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_authorization_issuance_v1.md"
)
INTEGRATION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_worker_observability_harness_evidence_integration_v1.md"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-07-23-local-abc-cu129-worker-observability-harness-evidence-integration.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/"
    "AuraGateway_CU129_Worker_Observability_Harness_Operational_Input_Closure_Report.md"
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
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ARGUMENT_INVALID",
            "worker-observability evidence-integration arguments are invalid",
            details=(message,),
        )


class IntegrationSafety(LocalABCContract):
    authorization_issued: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    measured_execution_authorized: Literal[False] = False


class EvidenceZipMember(LocalABCContract):
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
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-cu129-worker-observability-harness-input-inspection-evidence-v1"
    ]
    source_commit: Literal["dceda98989386de7a4d57616f9f8a8023f866f10"]
    materializer_notebook_name: Literal["ag-worker-obs-harness-materializer-v1"]
    materializer_saved_version_id: Literal[337284215]
    materializer_saved_version_url: Literal[
        "https://www.kaggle.com/code/kabomolefe/"
        "ag-worker-obs-harness-materializer-v1/notebook?scriptVersionId=337284215"
    ]
    materializer_recovery_notebook_sha256: str
    inspection_notebook_name: Literal["ag-worker-obs-input-inspection-v1"]
    inspection_saved_version_id: Literal[337286728]
    inspection_saved_version_url: Literal[
        "https://www.kaggle.com/code/kabomolefe/"
        "ag-worker-obs-input-inspection-v1/notebook?scriptVersionId=337286728"
    ]
    materialization_receipt_sha256: str
    materializer_log_sha256: str
    inspection_log_sha256: str
    inspection_evidence_zip_sha256: str
    inspection_evidence_members: tuple[EvidenceZipMember, ...]
    harness_directory_sha256: str
    harness_file_count: Literal[1076]
    harness_total_bytes: Literal[10850278]
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
        if tuple(item.name for item in self.inspection_evidence_members) != (EXPECTED_ZIP_MEMBERS):
            raise ValueError("inspection evidence member order or set drifted")
        return self


class MaterializationReceipt(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["WORKER_OBSERVABILITY_HARNESS_MATERIALIZED"]
    producer_notebook_name: Literal["ag-worker-obs-harness-materializer-v1"]
    source_commit: Literal["dceda98989386de7a4d57616f9f8a8023f866f10"]
    input_dataset_name: Literal["ag-worker-obs-harness-dceda98-v1-input"]
    input_mode: Literal["kaggle_expanded_archive_recovery"]
    archive_filename: Literal["ag-worker-obs-harness-dceda98-v1.zip"]
    archive_sha256: str
    archive_reconstructed: Literal[True]
    source_inventory_sha256: str
    source_package_manifest_sha256: str
    source_receipt_sha256: str
    original_materializer_notebook_sha256: str
    output_directory: Literal["auragateway_qualification_harness_dceda98_worker_obs_v1"]
    directory_sha256: str
    file_count: Literal[1076]
    total_bytes: Literal[10850278]
    nested_archives_present: Literal[False]
    symlinks_present: Literal[False]
    network_access_performed: Literal[False]
    package_installation_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    model_loaded: Literal[False]
    worker_started: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    authorization_issued: Literal[False]
    active_manifest_promoted: Literal[False]

    @field_validator(
        "archive_sha256",
        "source_inventory_sha256",
        "source_package_manifest_sha256",
        "source_receipt_sha256",
        "original_materializer_notebook_sha256",
        "directory_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("materialization receipt digests must be lowercase SHA-256")
        return value


class IntegrationDecisionRecord(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-worker-observability-harness-evidence-integration-v1"]
    decision: Literal["APPROVED_FOR_WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATION"]
    source_commit: Literal["dceda98989386de7a4d57616f9f8a8023f866f10"]
    harness_directory_sha256: str
    harness_file_count: Literal[1076]
    harness_total_bytes: Literal[10850278]
    materializer_saved_version_id: Literal[337284215]
    inspection_saved_version_id: Literal[337286728]
    inspection_evidence_zip_sha256: str
    materialization_receipt_sha256: str
    manifest_sha256: str
    materialization_record_sha256: str
    runtime_adapter_sha256: str
    worker_startup_diagnostics_sha256: str
    materialized_harness_launcher_source_sha256: str
    materialized_harness_launcher_notebook_sha256: str
    launcher_source_sha256: str
    launcher_notebook_sha256: str
    authorization_source_binding_policy: Literal["CONTROL_PACKAGE_AUTHORIZATION_PARITY"]
    active_harness_binding_status: Literal["WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED"]
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
        "worker_startup_diagnostics_sha256",
        "materialized_harness_launcher_source_sha256",
        "materialized_harness_launcher_notebook_sha256",
        "launcher_source_sha256",
        "launcher_notebook_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("integration identities must be lowercase SHA-256")
        return value


class FreshAuthorizationReadinessReview(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-cu129-worker-observability-fresh-authorization-readiness-review-v1"
    ]
    decision: Literal[
        "APPROVED_FOR_FRESH_WORKER_OBSERVABILITY_CU129_AUTHORIZATION_ISSUANCE_IMPLEMENTATION"
    ]
    source_commit: Literal["dceda98989386de7a4d57616f9f8a8023f866f10"]
    operational_input_closure: Literal["PASSED"]
    current_harness_directory_sha256: str
    current_manifest_sha256: str
    current_materialization_record_sha256: str
    current_runtime_adapter_sha256: str
    current_worker_startup_diagnostics_sha256: str
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
        "current_worker_startup_diagnostics_sha256",
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
            "runtime adapter and worker-startup diagnostics",
            "generated launcher source and notebook",
            "eight-request hard limits",
            "zero benchmark trajectory requests",
            "do not overwrite",
            "dynamic launcher-control authorization-source parity",
        )
        if len(self.required_implementation) != len(required_fragments) or any(
            fragment not in item
            for fragment, item in zip(
                required_fragments,
                self.required_implementation,
                strict=True,
            )
        ):
            raise ValueError("fresh authorization implementation scope drifted")
        if len(self.non_claims) < 7:
            raise ValueError("fresh authorization non-claims are incomplete")
        return self


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_FILE_UNREADABLE",
            "an integration-bound file could not be read",
            path.as_posix(),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_JSON_INVALID",
            "an integration-bound JSON file is missing or invalid",
            path.as_posix(),
        ) from exc


def _load_canonical_contract(
    path: Path,
    model: type[LocalABCContract],
) -> LocalABCContract:
    payload = _load_json(path)
    try:
        parsed = model.model_validate(payload)
    except ValidationError as exc:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_CONTRACT_INVALID",
            "an integration-bound JSON contract failed validation",
            path.as_posix(),
            details=tuple(str(item) for item in exc.errors())[:10],
        ) from exc
    if path.read_text(encoding="utf-8") != parsed.canonical_json():
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_JSON_NOT_CANONICAL",
            "an integration-bound JSON contract is not canonical",
            path.as_posix(),
        )
    return parsed


def _validate_evidence_zip(
    path: Path,
    identity: EvidenceIdentity,
) -> dict[str, object]:
    if _file_sha256(path) != INSPECTION_EVIDENCE_ZIP_SHA256:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ZIP_IDENTITY_DRIFT",
            "the inspection evidence ZIP identity drifted",
            path.as_posix(),
        )
    try:
        with zipfile.ZipFile(path) as archive:
            members = tuple(archive.infolist())
            names = tuple(item.filename for item in members)
            if names != EXPECTED_ZIP_MEMBERS or len(names) != len(set(names)):
                raise HarnessEvidenceIntegrationError(
                    "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ZIP_MEMBER_SET_DRIFT",
                    "the inspection evidence ZIP member set or order drifted",
                    path.as_posix(),
                )
            payloads: dict[str, bytes] = {}
            for member in members:
                member_path = PurePosixPath(member.filename)
                unix_mode = member.external_attr >> 16
                if (
                    member_path.is_absolute()
                    or len(member_path.parts) != 1
                    or member.is_dir()
                    or member.flag_bits & 0x1
                    or member.date_time != ZIP_TIMESTAMP
                    or member.compress_type != zipfile.ZIP_DEFLATED
                    or stat.S_IFMT(unix_mode) != stat.S_IFREG
                    or unix_mode != 0o100644
                ):
                    raise HarnessEvidenceIntegrationError(
                        "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ZIP_METADATA_DRIFT",
                        "an inspection evidence ZIP member metadata field drifted",
                        member.filename,
                    )
                payloads[member.filename] = archive.read(member)
    except zipfile.BadZipFile as exc:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ZIP_INVALID",
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
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ZIP_MEMBER_IDENTITY_DRIFT",
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
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ZIP_JSON_INVALID",
            "an inspection evidence ZIP member is invalid JSON",
            path.as_posix(),
        ) from exc
    for name, payload in records.items():
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        if payloads[name].decode("utf-8") != canonical:
            raise HarnessEvidenceIntegrationError(
                "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ZIP_JSON_NOT_CANONICAL",
                "an inspection evidence ZIP JSON member is not canonical",
                name,
            )
    expected_manifest = {
        name: _sha256_bytes(payloads[name])
        for name in EXPECTED_ZIP_MEMBERS
        if name != "99_evidence_sha256.json"
    }
    if records["99_evidence_sha256.json"] != expected_manifest:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_ZIP_HASH_MANIFEST_DRIFT",
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
        "status": "WORKER_OBSERVABILITY_HARNESS_INPUT_VALIDATED",
        "producer_root_name": "ag_worker_obs_harness_materializer_v1_output",
        "source_commit": SOURCE_COMMIT,
        "directory_sha256": CURRENT_HARNESS_DIRECTORY_SHA256,
        "file_count": CURRENT_HARNESS_FILE_COUNT,
        "total_bytes": CURRENT_HARNESS_TOTAL_BYTES,
        "materialization_receipt_sha256": MATERIALIZATION_RECEIPT_SHA256,
        "current_runtime_adapter_sha256": CURRENT_RUNTIME_ADAPTER_SHA256,
        "expected_current_runtime_adapter_sha256": CURRENT_RUNTIME_ADAPTER_SHA256,
        "historical_runtime_adapter_sha256": HISTORICAL_RUNTIME_ADAPTER_SHA256,
        "historical_adapter_resolved": False,
        "worker_startup_diagnostics_sha256": CURRENT_WORKER_DIAGNOSTICS_SHA256,
        "launcher_source_sha256": MATERIALIZED_HARNESS_LAUNCHER_SOURCE_SHA256,
        "launcher_notebook_sha256": MATERIALIZED_HARNESS_LAUNCHER_NOTEBOOK_SHA256,
        "transient_authorization_present": False,
    }
    if any(harness.get(key) != value for key, value in expected_harness.items()):
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_HARNESS_RECORD_DRIFT",
            "the validated worker-observability harness evidence drifted",
        )
    expected_runtime = {
        "status": "WORKER_OBSERVABILITY_RUNTIME_AND_MODEL_INPUTS_VALIDATED",
        "package_count": RUNTIME_PACKAGE_COUNT,
        "manifest_entry_count": 182,
        "runtime_resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
        "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
        "model_weights_loaded": False,
        "wheel_payloads_rehashed": False,
    }
    if any(runtime.get(key) != value for key, value in expected_runtime.items()):
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_RUNTIME_RECORD_DRIFT",
            "the validated runtime and model evidence drifted",
        )
    expected_boundary = {
        "status": "WORKER_OBSERVABILITY_SOURCE_BOUNDARY_VALIDATED",
        "active_harness_binding_status": "HISTORICAL_PENDING_EVIDENCE_INTEGRATION",
        "historical_harness_directory_sha256": HISTORICAL_HARNESS_DIRECTORY_SHA256,
        "historical_harness_output_directory": HISTORICAL_HARNESS_OUTPUT_DIRECTORY,
        "new_harness_directory_sha256": CURRENT_HARNESS_DIRECTORY_SHA256,
        "active_manifest_promoted": False,
        "authorization_issued": False,
        "network_access_performed": False,
        "package_installation_performed": False,
        "gpu_execution_performed": False,
        "model_loaded": False,
        "tokenizer_loaded": False,
        "worker_started": False,
        "model_requests_performed": 0,
    }
    if any(source_boundary.get(key) != value for key, value in expected_boundary.items()):
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_SOURCE_BOUNDARY_DRIFT",
            "the validated source-boundary evidence drifted",
        )
    expected_summary = {
        "inspection_status": "WORKER_OBSERVABILITY_HARNESS_INPUT_INSPECTION_PASSED",
        "operational_input_closure": "PASSED",
        "source_commit": SOURCE_COMMIT,
        "harness_directory_sha256": CURRENT_HARNESS_DIRECTORY_SHA256,
        "materialization_receipt_sha256": MATERIALIZATION_RECEIPT_SHA256,
        "runtime_resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
        "runtime_package_count": RUNTIME_PACKAGE_COUNT,
        "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
        "active_manifest_promoted": False,
        "network_access_performed": False,
        "gpu_execution_performed": False,
        "package_installation_performed": False,
        "model_loaded": False,
        "tokenizer_loaded": False,
        "worker_started": False,
        "model_requests_performed": 0,
        "authorization_issued": False,
        "next_gate": "integrate_worker_observability_harness_materialization_evidence",
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_INSPECTION_SUMMARY_DRIFT",
            "the successful worker-observability inspection summary drifted",
        )
    parity = (
        receipt.source_commit == summary["source_commit"],
        receipt.directory_sha256 == summary["harness_directory_sha256"],
        receipt.directory_sha256 == harness["directory_sha256"],
        receipt.file_count == harness["file_count"],
        receipt.total_bytes == harness["total_bytes"],
    )
    if not all(parity):
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_CROSS_EVIDENCE_DRIFT",
            "materializer and inspection evidence identities disagree",
        )


def _validate_logs(root: Path) -> None:
    paths_and_fragments = {
        MATERIALIZER_LOG_PATH: (
            "status=WORKER_OBSERVABILITY_HARNESS_MATERIALIZED",
            f"source_commit={SOURCE_COMMIT}",
            f"file_count={CURRENT_HARNESS_FILE_COUNT}",
            f"total_bytes={CURRENT_HARNESS_TOTAL_BYTES}",
            f"directory_sha256={CURRENT_HARNESS_DIRECTORY_SHA256}",
            "archive_reconstructed=true",
            "authorization_issued=false",
        ),
        INSPECTION_LOG_PATH: (
            "inspection_status=WORKER_OBSERVABILITY_HARNESS_INPUT_INSPECTION_PASSED",
            "operational_input_closure=PASSED",
            f"source_commit={SOURCE_COMMIT}",
            f"harness_directory_sha256={CURRENT_HARNESS_DIRECTORY_SHA256}",
            f"materialization_receipt_sha256={MATERIALIZATION_RECEIPT_SHA256}",
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
                "WORKER_OBSERVABILITY_LOG_IDENTITY_DRIFT",
                "a preserved successful Kaggle log identity drifted",
                relative_path.as_posix(),
            )
        text = path.read_text(encoding="utf-8")
        if any(fragment not in text for fragment in fragments):
            raise HarnessEvidenceIntegrationError(
                "WORKER_OBSERVABILITY_LOG_CONTENT_DRIFT",
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
            "WORKER_OBSERVABILITY_ACTIVE_CONTRACT_INVALID",
            "the active manifest or materialization record failed typed validation",
            details=tuple(str(item) for item in exc.errors())[:10],
        ) from exc
    if (root / MANIFEST_PATH).read_text(encoding="utf-8") != manifest.canonical_json():
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_MANIFEST_NOT_CANONICAL",
            "the active dataset manifest is not canonical JSON",
            MANIFEST_PATH.as_posix(),
        )
    if (root / MATERIALIZATION_RECORD_PATH).read_text(
        encoding="utf-8"
    ) != materialization.canonical_json():
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_MATERIALIZATION_NOT_CANONICAL",
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
            "WORKER_OBSERVABILITY_ACTIVE_HARNESS_DRIFT",
            "the active manifest or materialization record does not bind the integrated harness",
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
            "WORKER_OBSERVABILITY_RUNTIME_AUTHORITY_DRIFT",
            "the active CUDA 12.9 runtime authority drifted",
        )
    return manifest.fingerprint(), materialization.fingerprint()


def _validate_launcher(root: Path) -> dict[str, object]:
    from auragateway.local_abc import (
        full_abc_local_environment_qualification_kaggle_launcher as launcher,
    )

    if launcher.SOURCE_MAIN_MERGE_COMMIT != SOURCE_COMMIT:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_LAUNCHER_SOURCE_DRIFT",
            "the launcher source authority does not bind the integrated harness",
            LAUNCHER_SOURCE_PATH.as_posix(),
        )
    if launcher.HARNESS_SOURCE_PATH != CURRENT_HARNESS_MOUNTED_PATH:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_LAUNCHER_MOUNT_DRIFT",
            "the launcher harness mounted path drifted",
            LAUNCHER_SOURCE_PATH.as_posix(),
        )
    if launcher.AUTHORIZATION_SOURCE_BINDING_POLICY != (AUTHORIZATION_SOURCE_BINDING_POLICY):
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_AUTHORIZATION_POLICY_DRIFT",
            "the launcher authorization-source parity policy drifted",
            LAUNCHER_SOURCE_PATH.as_posix(),
        )
    verification = launcher.verify_launcher_notebook(
        repo_root=root,
        notebook_path=root / LAUNCHER_NOTEBOOK_PATH,
    )
    if _file_sha256(root / LAUNCHER_SOURCE_PATH) != CURRENT_LAUNCHER_SOURCE_SHA256:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_LAUNCHER_SOURCE_IDENTITY_DRIFT",
            "the active launcher source identity drifted",
            LAUNCHER_SOURCE_PATH.as_posix(),
        )
    if verification.notebook_sha256 != CURRENT_LAUNCHER_NOTEBOOK_SHA256:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_LAUNCHER_NOTEBOOK_IDENTITY_DRIFT",
            "the active generated launcher notebook identity drifted",
            LAUNCHER_NOTEBOOK_PATH.as_posix(),
        )
    return verification.model_dump(mode="json")


def _validate_documentation(root: Path) -> None:
    required = {
        ADR_PATH: (
            "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED",
            "CONTROL_PACKAGE_AUTHORIZATION_PARITY",
        ),
        REPORT_PATH: (
            "operational_input_closure=PASSED",
            INSPECTION_EVIDENCE_ZIP_SHA256,
        ),
        INTEGRATION_RUNBOOK_PATH: (
            str(MATERIALIZER_SAVED_VERSION_ID),
            str(INSPECTION_SAVED_VERSION_ID),
            "authorization_issued=false",
        ),
        LAUNCHER_RUNBOOK_PATH: (
            CURRENT_HARNESS_MOUNTED_PATH,
            "fresh_cu129_authorization_issuance_implementation",
        ),
        AUTHORIZATION_RUNBOOK_PATH: (
            "WORKER OBSERVABILITY HARNESS EVIDENCE INTEGRATED",
            "historical issuer",
            "authorization_issued=false",
        ),
    }
    for relative_path, fragments in required.items():
        text = (root / relative_path).read_text(encoding="utf-8")
        if any(fragment not in text for fragment in fragments):
            raise HarnessEvidenceIntegrationError(
                "WORKER_OBSERVABILITY_DOCUMENTATION_DRIFT",
                "worker-observability evidence-integration documentation drifted",
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
        _load_canonical_contract(
            root / MATERIALIZATION_RECEIPT_PATH,
            MaterializationReceipt,
        ),
    )
    integration = cast(
        IntegrationDecisionRecord,
        _load_canonical_contract(
            root / INTEGRATION_RECORD_PATH,
            IntegrationDecisionRecord,
        ),
    )
    readiness = cast(
        FreshAuthorizationReadinessReview,
        _load_canonical_contract(
            root / READINESS_REVIEW_PATH,
            FreshAuthorizationReadinessReview,
        ),
    )

    expected_identities = {
        RECOVERY_NOTEBOOK_PATH: MATERIALIZER_RECOVERY_NOTEBOOK_SHA256,
        MATERIALIZATION_RECEIPT_PATH: MATERIALIZATION_RECEIPT_SHA256,
        MATERIALIZER_LOG_PATH: MATERIALIZER_LOG_SHA256,
        INSPECTION_LOG_PATH: INSPECTION_LOG_SHA256,
        INSPECTION_ZIP_PATH: INSPECTION_EVIDENCE_ZIP_SHA256,
        RUNTIME_ADAPTER_PATH: CURRENT_RUNTIME_ADAPTER_SHA256,
        WORKER_DIAGNOSTICS_PATH: CURRENT_WORKER_DIAGNOSTICS_SHA256,
    }
    drift = tuple(
        path.as_posix()
        for path, expected_sha256 in expected_identities.items()
        if _file_sha256(root / path) != expected_sha256
    )
    if drift:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_EXTERNAL_IDENTITY_DRIFT",
            "one or more evidence-bound identities drifted",
            details=drift,
        )
    identity_parity = (
        identity.materializer_recovery_notebook_sha256 == MATERIALIZER_RECOVERY_NOTEBOOK_SHA256,
        identity.materialization_receipt_sha256 == MATERIALIZATION_RECEIPT_SHA256,
        identity.inspection_evidence_zip_sha256 == INSPECTION_EVIDENCE_ZIP_SHA256,
        identity.materializer_saved_version_url == MATERIALIZER_SAVED_VERSION_URL,
        identity.inspection_saved_version_url == INSPECTION_SAVED_VERSION_URL,
    )
    if not all(identity_parity):
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_IDENTITY_REGISTRY_DRIFT",
            "the evidence identity registry drifted from consumed artifacts",
        )

    records = _validate_evidence_zip(root / INSPECTION_ZIP_PATH, identity)
    _validate_cross_evidence(receipt, records)
    _validate_logs(root)
    manifest_sha256, materialization_sha256 = _validate_active_repository(root)
    if manifest_sha256 != CURRENT_MANIFEST_SHA256:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_MANIFEST_IDENTITY_DRIFT",
            "the active manifest identity drifted from the integrated authority",
            MANIFEST_PATH.as_posix(),
        )
    if materialization_sha256 != CURRENT_MATERIALIZATION_RECORD_SHA256:
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_MATERIALIZATION_IDENTITY_DRIFT",
            "the active materialization-record identity drifted",
            MATERIALIZATION_RECORD_PATH.as_posix(),
        )
    launcher_summary = _validate_launcher(root)

    decision_parity = (
        integration.harness_directory_sha256 == receipt.directory_sha256,
        integration.manifest_sha256 == manifest_sha256,
        integration.materialization_record_sha256 == materialization_sha256,
        integration.runtime_adapter_sha256 == CURRENT_RUNTIME_ADAPTER_SHA256,
        integration.worker_startup_diagnostics_sha256 == CURRENT_WORKER_DIAGNOSTICS_SHA256,
        integration.materialized_harness_launcher_source_sha256
        == MATERIALIZED_HARNESS_LAUNCHER_SOURCE_SHA256,
        integration.materialized_harness_launcher_notebook_sha256
        == MATERIALIZED_HARNESS_LAUNCHER_NOTEBOOK_SHA256,
        integration.launcher_source_sha256 == CURRENT_LAUNCHER_SOURCE_SHA256,
        integration.launcher_notebook_sha256 == CURRENT_LAUNCHER_NOTEBOOK_SHA256,
        readiness.current_harness_directory_sha256 == receipt.directory_sha256,
        readiness.current_manifest_sha256 == manifest_sha256,
        readiness.current_materialization_record_sha256 == materialization_sha256,
        readiness.current_runtime_adapter_sha256 == CURRENT_RUNTIME_ADAPTER_SHA256,
        readiness.current_worker_startup_diagnostics_sha256 == CURRENT_WORKER_DIAGNOSTICS_SHA256,
        readiness.current_launcher_source_sha256 == CURRENT_LAUNCHER_SOURCE_SHA256,
        readiness.current_launcher_notebook_sha256 == CURRENT_LAUNCHER_NOTEBOOK_SHA256,
        readiness.inspection_evidence_zip_sha256 == INSPECTION_EVIDENCE_ZIP_SHA256,
        readiness.final_authorization_present is False,
    )
    if not all(decision_parity):
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_DECISION_IDENTITY_DRIFT",
            "integration or readiness identities drifted from active authorities",
        )
    _validate_documentation(root)
    if (root / FINAL_AUTHORIZATION_PATH).exists():
        raise HarnessEvidenceIntegrationError(
            "WORKER_OBSERVABILITY_PREMATURE_AUTHORIZATION",
            "the final authorization exists before fresh issuance implementation",
            FINAL_AUTHORIZATION_PATH.as_posix(),
        )

    return {
        "status": "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED",
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
        "runtime_adapter_sha256": CURRENT_RUNTIME_ADAPTER_SHA256,
        "worker_startup_diagnostics_sha256": CURRENT_WORKER_DIAGNOSTICS_SHA256,
        "launcher_notebook_sha256": launcher_summary["notebook_sha256"],
        "authorization_source_binding_policy": AUTHORIZATION_SOURCE_BINDING_POLICY,
        "authorization_issued": False,
        "gpu_execution_performed": False,
        "model_requests_performed": 0,
        "measured_execution_authorized": False,
        "active_manifest_promoted": True,
        "historical_issuer_usable": False,
        "next_gate": readiness.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
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
        print(
            json.dumps(
                envelope,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
