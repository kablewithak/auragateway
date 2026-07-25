"""Validate current CUDA 12.9 harness evidence integration."""

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

SOURCE_COMMIT: Final = "56f33739babb80d843fef1ad8f7f1223f3d10d14"
SOURCE_TOKEN: Final = "56f3373"
CURRENT_HARNESS_DIRECTORY_SHA256: Final = (
    "778333c57b02d74be2c18962d7e75b560d269fc9b6c6b611d043304c855e3477"
)
CURRENT_HARNESS_FILE_COUNT: Final = 1_084
CURRENT_HARNESS_TOTAL_BYTES: Final = 10_970_203
CURRENT_HARNESS_OUTPUT_DIRECTORY: Final = "auragateway_qualification_harness_56f3373_v1"
CURRENT_HARNESS_MOUNTED_PATH: Final = (
    "/kaggle/input/notebooks/kabomolefe/"
    "ag-harness-materializer-cu129-v1/"
    "ag_harness_materializer_cu129_v1_output/"
    "auragateway_qualification_harness_56f3373_v1"
)
CURRENT_HARNESS_KAGGLE_SLUG: Final = "kabomolefe/ag-harness-materializer-cu129-v1"
MATERIALIZER_SAVED_VERSION_ID: Final = 337848035
INSPECTION_SAVED_VERSION_ID: Final = 337858124
MATERIALIZER_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-harness-materializer-cu129-v1?scriptVersionId=337848035"
)
INSPECTION_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-harness-input-inspection-cu129-v1/output?scriptVersionId=337858124"
)
MATERIALIZER_RECOVERY_NOTEBOOK_SHA256: Final = (
    "d371262fc120cb30f17c8f7a761055835f7f66178cf777ccfc51950a223571ff"
)
MATERIALIZATION_RECEIPT_SHA256: Final = (
    "a4fe6685458cecc622ac1a13a28cf3349d3d98ff0fbc2e284511da76fb066364"
)
MATERIALIZER_LOG_SHA256: Final = "d1c34c5a7a0f442047dc830214302b5d2f1e72028abc014c33ad30a27b5bc55a"
INSPECTION_LOG_SHA256: Final = "eb3ef42a834536b1a3c318c0b08a8933940eca5b4ed75d15695b861d1142c85c"
INSPECTION_EVIDENCE_ZIP_SHA256: Final = (
    "c0832dde010835401dc11ff654b864c3db62e9c895c18265ea881d154eeaae1e"
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
    "b363c657b9053897a01c3784487e2b3fdc7a42391acb98d380b4e43eba21f3ec"
)
MATERIALIZED_HARNESS_LAUNCHER_NOTEBOOK_SHA256: Final = (
    "9bec10b5f80e53f6a09533e6acf680449e6260329e3e9fbc1f4fdc247d0ad64f"
)
CURRENT_MANIFEST_SHA256: Final = "f8bcd218f7863a8c2ac7dd04ad0c5ee054484035abb8ae44d1d2117e1e84513a"
CURRENT_MATERIALIZATION_RECORD_SHA256: Final = (
    "c19675317ea5b4086ba0cd548cc0f4f9c6cd791c7dc9f046fedc02e5168eb0b8"
)
CURRENT_LAUNCHER_SOURCE_SHA256: Final = (
    "03e37eb4d44b67a9104a249040ef37e63cbbd5a58ef5cc952d46ea41516388e8"
)
CURRENT_LAUNCHER_NOTEBOOK_SHA256: Final = (
    "f27e1ae8683ffb6b93bbc5b91513330c94ec40ec67873f836fb4adaa7e6b87ef"
)
AUTHORIZATION_SOURCE_BINDING_POLICY: Final = "CONTROL_PACKAGE_AUTHORIZATION_PARITY"
HISTORICAL_HARNESS_DIRECTORY_SHA256: Final = (
    "c66f2589bdf55ab34f82bffc1eaaa4b4c7e73cb8195867333ccd99a58438f3e4"
)
HISTORICAL_HARNESS_OUTPUT_DIRECTORY: Final = (
    "auragateway_qualification_harness_dceda98_worker_obs_v1"
)
HISTORICAL_RUNTIME_ADAPTER_SHA256: Final = (
    "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"
)

EVIDENCE_ROOT: Final = Path(
    "evidence_vault/local_abc/cu129-current-harness-56f3373-input-inspection-v1"
)
EVIDENCE_IDENTITY_PATH: Final = EVIDENCE_ROOT / "evidence_identity.json"
MATERIALIZATION_RECEIPT_PATH: Final = (
    EVIDENCE_ROOT / "ag_harness_materialization_receipt_cu129_v1.json"
)
MATERIALIZER_LOG_PATH: Final = EVIDENCE_ROOT / "ag-harness-materializer-cu129-v1.log"
INSPECTION_LOG_PATH: Final = EVIDENCE_ROOT / "ag-harness-input-inspection-cu129-v1.log"
INSPECTION_ZIP_PATH: Final = EVIDENCE_ROOT / "ag-harness-input-inspection-cu129-v1.zip"
RECOVERY_NOTEBOOK_PATH: Final = EVIDENCE_ROOT / "ag_harness_materializer_cu129_v1.ipynb"
MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
MATERIALIZATION_RECORD_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json"
)
INTEGRATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_56f3373_harness_evidence_integration_v1.json"
)
READINESS_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_56f3373_fresh_authorization_readiness_review_v1.json"
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
    "docs/runbooks/local_abc_cu129_56f3373_harness_evidence_integration_v1.md"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-07-25-local-abc-cu129-56f3373-harness-evidence-integration.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_56F3373_Harness_Operational_Input_Closure_Report.md"
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
    record_id: Literal["auragateway-cu129-current-harness-56f3373-input-inspection-evidence-v1"]
    source_commit: Literal["56f33739babb80d843fef1ad8f7f1223f3d10d14"]
    materializer_notebook_name: Literal["ag-harness-materializer-cu129-v1"]
    materializer_saved_version_id: Literal[337848035]
    materializer_saved_version_url: Literal[
        "https://www.kaggle.com/code/kabomolefe/"
        "ag-harness-materializer-cu129-v1?scriptVersionId=337848035"
    ]
    materializer_recovery_notebook_sha256: str
    inspection_notebook_name: Literal["ag-harness-input-inspection-cu129-v1"]
    inspection_saved_version_id: Literal[337858124]
    inspection_saved_version_url: Literal[
        "https://www.kaggle.com/code/kabomolefe/"
        "ag-harness-input-inspection-cu129-v1/output?scriptVersionId=337858124"
    ]
    materialization_receipt_sha256: str
    materializer_log_sha256: str
    inspection_log_sha256: str
    inspection_evidence_zip_sha256: str
    inspection_evidence_members: tuple[EvidenceZipMember, ...]
    harness_directory_sha256: str
    harness_file_count: Literal[1084]
    harness_total_bytes: Literal[10970203]
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
    status: Literal["CURRENT_CU129_HARNESS_MATERIALIZED"]
    producer_notebook_name: Literal["ag-harness-materializer-cu129-v1"]
    producer_output_directory: Literal["ag_harness_materializer_cu129_v1_output"]
    source_commit: Literal["56f33739babb80d843fef1ad8f7f1223f3d10d14"]
    input_dataset_name: Literal["ag-harness-56f3373-v1-input"]
    input_mode: Literal[
        "exact_archive_with_control_files",
        "kaggle_expanded_source_recovered_to_exact_archive",
    ]
    archive_filename: Literal["ag-harness-56f3373-v1.zip"]
    archive_sha256: str
    source_inventory_sha256: str
    source_receipt_sha256: str
    source_sha256_manifest_sha256: str
    output_directory: Literal["auragateway_qualification_harness_56f3373_v1"]
    directory_sha256: str
    file_count: Literal[1084]
    total_bytes: Literal[10970203]
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
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-56f3373-harness-evidence-integration-v1"]
    decision: Literal["APPROVED_FOR_CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATION"]
    source_commit: Literal["56f33739babb80d843fef1ad8f7f1223f3d10d14"]
    harness_directory_sha256: str
    harness_file_count: Literal[1084]
    harness_total_bytes: Literal[10970203]
    materializer_saved_version_id: Literal[337848035]
    inspection_saved_version_id: Literal[337858124]
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
    review_id: Literal["auragateway-cu129-56f3373-fresh-authorization-readiness-review-v1"]
    decision: Literal["APPROVED_FOR_FRESH_CU129_AUTHORIZATION_ISSUANCE_IMPLEMENTATION"]
    source_commit: Literal["56f33739babb80d843fef1ad8f7f1223f3d10d14"]
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
        "status": "CURRENT_CU129_HARNESS_INPUT_VALIDATED",
        "producer_root_name": "ag_harness_materializer_cu129_v1_output",
        "source_commit": SOURCE_COMMIT,
        "directory_sha256": CURRENT_HARNESS_DIRECTORY_SHA256,
        "file_count": CURRENT_HARNESS_FILE_COUNT,
        "total_bytes": CURRENT_HARNESS_TOTAL_BYTES,
        "current_runtime_adapter_sha256": CURRENT_RUNTIME_ADAPTER_SHA256,
        "expected_current_runtime_adapter_sha256": (CURRENT_RUNTIME_ADAPTER_SHA256),
        "historical_runtime_adapter_sha256": (HISTORICAL_RUNTIME_ADAPTER_SHA256),
        "historical_adapter_resolved": False,
    }
    if any(harness.get(key) != value for key, value in expected_harness.items()):
        raise HarnessEvidenceIntegrationError(
            "CURRENT_CU129_HARNESS_RECORD_DRIFT",
            "the validated current harness evidence drifted",
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
            "CURRENT_CU129_RUNTIME_RECORD_DRIFT",
            "the validated runtime and model evidence drifted",
        )

    expected_boundary = {
        "status": "CURRENT_CU129_SOURCE_BOUNDARY_VALIDATED",
        "active_harness_binding_status": (
            "ACTIVE_PREDECESSOR_PENDING_CURRENT_EVIDENCE_INTEGRATION"
        ),
        "active_predecessor_harness_directory_sha256": (HISTORICAL_HARNESS_DIRECTORY_SHA256),
        "active_predecessor_harness_output_directory": (HISTORICAL_HARNESS_OUTPUT_DIRECTORY),
        "authorization_issued": False,
        "package_installation_performed": False,
        "gpu_execution_performed": False,
        "model_loaded": False,
        "worker_started": False,
        "model_requests_performed": 0,
    }
    if any(source_boundary.get(key) != value for key, value in expected_boundary.items()):
        raise HarnessEvidenceIntegrationError(
            "CURRENT_CU129_SOURCE_BOUNDARY_DRIFT",
            "the validated source-boundary evidence drifted",
        )

    expected_summary = {
        "inspection_status": ("CURRENT_CU129_HARNESS_INPUT_INSPECTION_PASSED"),
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
        "next_gate": ("integrate_current_cu129_harness_materialization_evidence"),
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise HarnessEvidenceIntegrationError(
            "CURRENT_CU129_INSPECTION_SUMMARY_DRIFT",
            "the successful current inspection summary drifted",
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
            "CURRENT_CU129_CROSS_EVIDENCE_DRIFT",
            "materializer and inspection evidence identities disagree",
        )


def _validate_logs(root: Path) -> None:
    paths_and_fragments = {
        MATERIALIZER_LOG_PATH: (
            "status=CURRENT_CU129_HARNESS_MATERIALIZED",
            "input_mode=kaggle_expanded_source_recovered_to_exact_archive",
            f"file_count={CURRENT_HARNESS_FILE_COUNT}",
            f"total_bytes={CURRENT_HARNESS_TOTAL_BYTES}",
            f"directory_sha256={CURRENT_HARNESS_DIRECTORY_SHA256}",
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
                "CURRENT_CU129_LOG_IDENTITY_DRIFT",
                "a preserved successful Kaggle log identity drifted",
                relative_path.as_posix(),
            )
        text = path.read_text(encoding="utf-8")
        if any(fragment not in text for fragment in fragments):
            raise HarnessEvidenceIntegrationError(
                "CURRENT_CU129_LOG_CONTENT_DRIFT",
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
            "CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED",
            SOURCE_COMMIT,
            CURRENT_HARNESS_DIRECTORY_SHA256,
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
    }
    for relative_path, fragments in required.items():
        text = (root / relative_path).read_text(encoding="utf-8")
        if any(fragment not in text for fragment in fragments):
            raise HarnessEvidenceIntegrationError(
                "CURRENT_CU129_DOCUMENTATION_DRIFT",
                "current harness evidence-integration documentation drifted",
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
