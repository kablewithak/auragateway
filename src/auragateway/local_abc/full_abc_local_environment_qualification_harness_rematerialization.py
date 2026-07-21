"""Bind the refreshed Kaggle harness output after authorization-schema parity proof."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/()+ -]{3,320}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"
HISTORICAL_AUTHORITY_COMMIT: Final = "84ab2634f548cc60d8aaeef31cdf4fd1e227ad73"
SUPERSEDED_HARNESS_SOURCE_COMMIT: Final = "4dfd799590195d842f2382bb882fba9b8c4e2422"
REPLACEMENT_HARNESS_SHA256: Final = (
    "4a371c80aef605c4f1ab5617c21ce43bd0939ad449ffcbcadab656878d785a2e"
)
RUNTIME_MANIFEST_SHA256: Final = "9ffd335fad6ac660782be7881625a1fb99a39f5d4a1446f31504154634c91eb7"
MATERIALIZATION_RECORD_SHA256: Final = (
    "8a0f41def6b3e4e8a34713e4cd9c3023d03619d51a62a2e7ec34da0bcc2f52c0"
)
PARITY_EVIDENCE_ZIP_SHA256: Final = (
    "b986f3b82785f86dea2c8fb368dd8ae4def7ee3d7b00f44637f77f3d28b1971b"
)
FAILED_QUALIFICATION_EVIDENCE_SHA256: Final = (
    "8b15e3dbe43f6131471ae988549927a3eafdc46619ebe4384fde9b5267d61352"
)
FAILED_AUTHORIZATION_SHA256: Final = (
    "1d672dc50a463a7e870799a53a0ad8dda64e89977963c518448ab9dd093d57b4"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_environment_qualification_"
    "harness_rematerialization_v1.json"
)
RUNTIME_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
MATERIALIZATION_RECORD_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json"
)
PARITY_EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/environment-qualification-harness-parity-v1"
)
PARITY_INSPECTION_REPORT_PATH: Final = PARITY_EVIDENCE_DIRECTORY / "inspection_report.json"
PARITY_AUTHORIZATION_SCHEMA_REPORT_PATH: Final = (
    PARITY_EVIDENCE_DIRECTORY / "authorization_schema_report.json"
)
PARITY_CANDIDATE_INVENTORY_PATH: Final = PARITY_EVIDENCE_DIRECTORY / "candidate_inventory.json"
PARITY_EVIDENCE_SHA256_PATH: Final = PARITY_EVIDENCE_DIRECTORY / "evidence_sha256.json"
NEXT_GATE: Final = "operator_confirmed_full_abc_environment_qualification_authorization_issuance"

SUPERSEDED_HARNESS_SLUG: Final = "kabomolefe/auragateway-qualification-harness-4dfd799-v1"
SUPERSEDED_HARNESS_PATH: Final = (
    "/kaggle/input/datasets/kabomolefe/auragateway-qualification-harness-4dfd799-v1"
)
SUPERSEDED_HARNESS_SHA256: Final = (
    "2ba96af01e093708b413bece444d5e440a076b4d60ac1ed9932d78c13ab3915a"
)
REPLACEMENT_PRODUCER_SLUG: Final = "kabomolefe/ag-harness-materializer-input-v3"
REPLACEMENT_OUTPUT_DIRECTORY: Final = "auragateway_qualification_harness_be1bfad_v1"
REPLACEMENT_HARNESS_PATH: Final = (
    "/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-input-v3/"
    "auragateway_qualification_harness_be1bfad_v1"
)
REPLACEMENT_FILE_COUNT: Final = 953
REPLACEMENT_TOTAL_BYTES: Final = 8_879_194

_MODEL_ENTRY: Final = (
    "model_artifacts",
    "hugging_face_snapshot_directory",
    "kabomolefe/auragateway-qwen2-5-0-5b-offline-v1",
    1,
    "/kaggle/input/datasets/kabomolefe/"
    "auragateway-qwen2-5-0-5b-offline-v1/"
    "auragateway-qwen2.5-0.5b-instruct-"
    "7ae557604adf67be50417f59c2c2f167def9a775/"
    "hf_home/hub/models--Qwen--Qwen2.5-0.5B-Instruct/"
    "snapshots/7ae557604adf67be50417f59c2c2f167def9a775",
    "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa",
)
_VLLM_ENTRY: Final = (
    "vllm_wheel",
    "python_wheel",
    "kabomolefe/auragateway-vllm-wheel-recovery-v1",
    1,
    "/kaggle/input/notebooks/kabomolefe/"
    "auragateway-vllm-wheel-recovery-v1/"
    "auragateway_vllm_wheels_v1/"
    "vllm-0.25.1+cu129-cp38-abi3-manylinux_2_28_x86_64.whl",
    "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431",
)


class HarnessRematerializationError(RuntimeError):
    """Metadata-safe validation failure for the rematerialization package."""

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


class HarnessRematerializationErrorEnvelope(LocalABCContract):
    """Machine-readable failure without prompts, payloads, or credentials."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class SupersededHarnessBinding(LocalABCContract):
    """Old harness identity retained only as failed lineage."""

    source_commit: Literal["4dfd799590195d842f2382bb882fba9b8c4e2422"]
    kaggle_resource_slug: Literal["kabomolefe/auragateway-qualification-harness-4dfd799-v1"]
    kaggle_resource_version: Literal[1] = 1
    mounted_path: Literal[
        "/kaggle/input/datasets/kabomolefe/auragateway-qualification-harness-4dfd799-v1"
    ]
    directory_sha256: Literal["2ba96af01e093708b413bece444d5e440a076b4d60ac1ed9932d78c13ab3915a"]
    qualification_failure_evidence_sha256: Literal[
        "8b15e3dbe43f6131471ae988549927a3eafdc46619ebe4384fde9b5267d61352"
    ]
    failed_authorization_sha256: Literal[
        "1d672dc50a463a7e870799a53a0ad8dda64e89977963c518448ab9dd093d57b4"
    ]
    failure_code: Literal["HARNESS_AUTHORIZATION_SCHEMA_MISMATCH"]
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    runtime_evidence_generated: Literal[False] = False
    superseded_for_future_qualification: Literal[True] = True


class HarnessParityEvidenceBinding(LocalABCContract):
    """Exact metadata-only Kaggle evidence proving schema parity."""

    evidence_zip_sha256: Literal["b986f3b82785f86dea2c8fb368dd8ae4def7ee3d7b00f44637f77f3d28b1971b"]
    evidence_directory: Literal[
        "evidence_vault/local_abc/environment-qualification-harness-parity-v1"
    ]
    inspection_report_path: Literal[
        "evidence_vault/local_abc/environment-qualification-harness-parity-v1/"
        "inspection_report.json"
    ]
    authorization_schema_report_path: Literal[
        "evidence_vault/local_abc/environment-qualification-harness-parity-v1/"
        "authorization_schema_report.json"
    ]
    candidate_inventory_path: Literal[
        "evidence_vault/local_abc/environment-qualification-harness-parity-v1/"
        "candidate_inventory.json"
    ]
    evidence_sha256_path: Literal[
        "evidence_vault/local_abc/environment-qualification-harness-parity-v1/evidence_sha256.json"
    ]
    notebook_name: Literal["ag-harness-parity-inspection-v4"]
    producer_notebook_slug: Literal["kabomolefe/ag-harness-materializer-input-v3"]
    producer_notebook_version: Literal[1] = 1
    inspection_report_sha256: Literal[
        "3137d6192bbbee5c0d35fa7cee41fb1e836c8c258bec86fcf2a5d246997a3484"
    ]
    authorization_schema_report_sha256: Literal[
        "1620cedd514c5ae97985626e5bc13e0232562cea491d95a0e9ca5c1abeb512df"
    ]
    candidate_inventory_sha256: Literal[
        "caac843fc293744f790048e98334cd223f3201562311382b1b592eba21b8b6dd"
    ]
    inspection_status: Literal["HARNESS_AUTHORIZATION_PARITY_PASSED"]
    authorization_status: Literal["AUTHORIZATION_SCHEMA_PARITY_PASSED"]
    runner_loader_accepted_authorization: Literal[True] = True
    gpu_execution_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    network_access_performed: Literal[False] = False
    external_spend: Literal[0] = 0


class ReplacementHarnessBinding(LocalABCContract):
    """Exact saved notebook output replacing the stale source dataset."""

    source_commit: Literal["be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"]
    kaggle_resource_slug: Literal["kabomolefe/ag-harness-materializer-input-v3"]
    kaggle_resource_version: Literal[1] = 1
    output_directory: Literal["auragateway_qualification_harness_be1bfad_v1"]
    mounted_path: Literal[
        "/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-input-v3/"
        "auragateway_qualification_harness_be1bfad_v1"
    ]
    artifact_format: Literal["source_tree_directory"] = "source_tree_directory"
    directory_sha256: Literal["4a371c80aef605c4f1ab5617c21ce43bd0939ad449ffcbcadab656878d785a2e"]
    file_count: Literal[953] = 953
    total_bytes: Literal[8879194] = 8_879_194
    input_mode: Literal["expanded_dataset_tree"]
    nested_archives_present: Literal[False] = False
    symlinks_present: Literal[False] = False


class UnchangedRuntimeInputBinding(LocalABCContract):
    """Model or vLLM input intentionally unchanged by rematerialization."""

    role: Literal["model_artifacts", "vllm_wheel"]
    artifact_format: Literal["hugging_face_snapshot_directory", "python_wheel"]
    kaggle_resource_slug: str
    kaggle_resource_version: Literal[1] = 1
    mounted_path: str
    sha256: str

    @field_validator("kaggle_resource_slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if value.count("/") != 1 or value.startswith("/") or value.endswith("/"):
            raise ValueError("Kaggle resource slug must use owner/resource syntax")
        return value

    @field_validator("mounted_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if not value.startswith("/kaggle/input/") or ".." in Path(value).parts:
            raise ValueError("runtime input must remain below /kaggle/input")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime input identity must be lowercase SHA-256")
        return value


class HistoricalPortableManifestEntry(LocalABCContract):
    """One exact offline input as represented at the rematerialization commit."""

    role: Literal["harness_source", "model_artifacts", "vllm_wheel"]
    artifact_format: Literal[
        "source_tree_directory",
        "hugging_face_snapshot_directory",
        "python_wheel",
    ]
    mounted_path: str
    sha256: str

    @field_validator("mounted_path")
    @classmethod
    def validate_mounted_path(cls, value: str) -> str:
        if not value.startswith("/kaggle/input/") or ".." in Path(value).parts:
            raise ValueError("historical mounted path must remain below /kaggle/input")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_entry_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("historical manifest entry requires lowercase SHA-256")
        return value


class HistoricalPortableManifest(LocalABCContract):
    """Typed historical runtime manifest detached from current live enums."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["auragateway-environment-qualification-offline-dataset-v1"]
    entries: tuple[
        HistoricalPortableManifestEntry,
        HistoricalPortableManifestEntry,
        HistoricalPortableManifestEntry,
    ]
    network_access_permitted: Literal[False] = False
    credentials_present: Literal[False] = False
    customer_data_present: Literal[False] = False
    hosted_provider_inputs_present: Literal[False] = False


class HistoricalMaterializedEntry(LocalABCContract):
    """One exact materialized input at the historical rematerialization boundary."""

    role: Literal["harness_source", "model_artifacts", "vllm_wheel"]
    artifact_format: Literal[
        "source_tree_directory",
        "hugging_face_snapshot_directory",
        "python_wheel",
    ]
    kaggle_dataset_slug: str
    kaggle_dataset_version: Literal[1] = 1
    mounted_path: str
    sha256: str
    network_fallback_permitted: Literal[False] = False

    @field_validator("kaggle_dataset_slug")
    @classmethod
    def validate_dataset_slug(cls, value: str) -> str:
        if value.count("/") != 1 or value.startswith("/") or value.endswith("/"):
            raise ValueError("historical Kaggle slug must use owner/resource syntax")
        return value

    @field_validator("mounted_path")
    @classmethod
    def validate_materialized_path(cls, value: str) -> str:
        if not value.startswith("/kaggle/input/") or ".." in Path(value).parts:
            raise ValueError("historical materialized path must remain below /kaggle/input")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_materialized_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("historical materialized entry requires lowercase SHA-256")
        return value


class HistoricalMaterializationRecord(LocalABCContract):
    """Typed historical materialization record detached from current live enums."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-environment-qualification-offline-materialization-v1"]
    harness_source_commit: Literal["be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"]
    entries: tuple[
        HistoricalMaterializedEntry,
        HistoricalMaterializedEntry,
        HistoricalMaterializedEntry,
    ]
    runtime_manifest_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
    ]
    runtime_manifest_sha256: str
    network_access_permitted: Literal[False] = False
    credentials_present: Literal[False] = False
    customer_data_present: Literal[False] = False
    hosted_provider_inputs_present: Literal[False] = False

    @field_validator("runtime_manifest_sha256")
    @classmethod
    def validate_manifest_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("historical runtime manifest identity must be lowercase SHA-256")
        return value


class HarnessRematerializationSafety(LocalABCContract):
    """No operational runtime activity is permitted in this binding slice."""

    repository_record_generated: Literal[True] = True
    authorization_issued: Literal[False] = False
    kaggle_gpu_session_started: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    worker_started: Literal[False] = False
    model_loaded: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    benchmark_trajectory_requests_performed: Literal[0] = 0
    network_access_performed: Literal[False] = False
    credentials_used: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0
    measured_execution_authorized: Literal[False] = False
    environment_qualified: Literal[False] = False


class HarnessRematerializationRecord(LocalABCContract):
    """Authoritative bridge from failed harness lineage to the refreshed output."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-full-abc-local-environment-qualification-harness-rematerialization-v1"
    ]
    source_main_merge_commit: Literal["be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"]
    decision: Literal["APPROVED_FOR_AUTHORIZATION_REISSUANCE"]
    superseded_harness: SupersededHarnessBinding
    parity_evidence: HarnessParityEvidenceBinding
    replacement_harness: ReplacementHarnessBinding
    unchanged_runtime_inputs: tuple[
        UnchangedRuntimeInputBinding,
        UnchangedRuntimeInputBinding,
    ]
    runtime_manifest_path: str
    runtime_manifest_sha256: str
    materialization_record_path: str
    materialization_record_sha256: str
    safety: HarnessRematerializationSafety
    next_gate: Literal[
        "operator_confirmed_full_abc_environment_qualification_authorization_issuance"
    ]

    @field_validator("source_main_merge_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("source merge commit must be lowercase Git SHA")
        return value

    @field_validator("runtime_manifest_path", "materialization_record_path")
    @classmethod
    def validate_repository_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or Path(value).is_absolute():
            raise ValueError("rematerialization paths must remain repository-relative")
        if ".." in Path(value).parts:
            raise ValueError("rematerialization paths cannot traverse parents")
        return Path(value).as_posix()

    @field_validator("runtime_manifest_sha256", "materialization_record_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("rematerialization identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_exact_bindings(self) -> Self:
        expected_inputs = (_MODEL_ENTRY, _VLLM_ENTRY)
        observed_inputs = tuple(
            (
                item.role,
                item.artifact_format,
                item.kaggle_resource_slug,
                item.kaggle_resource_version,
                item.mounted_path,
                item.sha256,
            )
            for item in self.unchanged_runtime_inputs
        )
        if observed_inputs != expected_inputs:
            raise ValueError("unchanged runtime input bindings drifted")
        if self.runtime_manifest_sha256 != RUNTIME_MANIFEST_SHA256:
            raise ValueError("runtime manifest identity drifted")
        if self.materialization_record_sha256 != MATERIALIZATION_RECORD_SHA256:
            raise ValueError("materialization record identity drifted")
        return self


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_FILE_UNREADABLE",
            "a rematerialization-bound file could not be read",
            path.as_posix(),
        ) from exc


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_JSON_INVALID",
            "a rematerialization artifact is missing or invalid",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_JSON_INVALID",
            "a rematerialization artifact must contain one JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _git_file_bytes_at_revision(
    repo_root: Path,
    relative_path: Path,
    revision: str,
) -> bytes:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "show",
                f"{revision}:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_HISTORICAL_AUTHORITY_UNREADABLE",
            "a historical rematerialization authority could not be read",
            relative_path.as_posix(),
            details=(revision,),
        ) from exc
    return result.stdout


def _load_historical_json_object(
    repo_root: Path,
    relative_path: Path,
) -> dict[str, object]:
    try:
        payload = json.loads(
            _git_file_bytes_at_revision(
                repo_root,
                relative_path,
                HISTORICAL_AUTHORITY_COMMIT,
            ).decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_HISTORICAL_JSON_INVALID",
            "a historical rematerialization authority is not valid JSON",
            relative_path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_HISTORICAL_JSON_INVALID",
            "a historical rematerialization authority must contain one JSON object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], payload)


def load_historical_runtime_manifest(
    repo_root: Path,
) -> HistoricalPortableManifest:
    """Load the exact runtime manifest at the rematerialization commit."""

    try:
        return HistoricalPortableManifest.model_validate(
            _load_historical_json_object(repo_root, RUNTIME_MANIFEST_PATH)
        )
    except ValidationError as exc:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_HISTORICAL_MANIFEST_INVALID",
            "the historical runtime manifest failed typed validation",
            RUNTIME_MANIFEST_PATH.as_posix(),
        ) from exc


def load_historical_materialization_record(
    repo_root: Path,
) -> HistoricalMaterializationRecord:
    """Load the exact materialization record at the rematerialization commit."""

    try:
        return HistoricalMaterializationRecord.model_validate(
            _load_historical_json_object(repo_root, MATERIALIZATION_RECORD_PATH)
        )
    except ValidationError as exc:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_HISTORICAL_RECORD_INVALID",
            "the historical materialization record failed typed validation",
            MATERIALIZATION_RECORD_PATH.as_posix(),
        ) from exc


def build_default_record() -> HarnessRematerializationRecord:
    """Build the canonical repository record without issuing authorization."""

    unchanged_inputs = tuple(
        UnchangedRuntimeInputBinding(
            role=cast(Literal["model_artifacts", "vllm_wheel"], role),
            artifact_format=cast(
                Literal["hugging_face_snapshot_directory", "python_wheel"],
                artifact_format,
            ),
            kaggle_resource_slug=slug,
            kaggle_resource_version=1,
            mounted_path=mounted_path,
            sha256=sha256,
        )
        for role, artifact_format, slug, _version, mounted_path, sha256 in (
            _MODEL_ENTRY,
            _VLLM_ENTRY,
        )
    )
    typed_inputs = cast(
        tuple[UnchangedRuntimeInputBinding, UnchangedRuntimeInputBinding],
        unchanged_inputs,
    )
    return HarnessRematerializationRecord(
        record_id=(
            "auragateway-full-abc-local-environment-qualification-harness-rematerialization-v1"
        ),
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        decision="APPROVED_FOR_AUTHORIZATION_REISSUANCE",
        superseded_harness=SupersededHarnessBinding(
            source_commit=SUPERSEDED_HARNESS_SOURCE_COMMIT,
            kaggle_resource_slug=SUPERSEDED_HARNESS_SLUG,
            mounted_path=SUPERSEDED_HARNESS_PATH,
            directory_sha256=SUPERSEDED_HARNESS_SHA256,
            qualification_failure_evidence_sha256=(FAILED_QUALIFICATION_EVIDENCE_SHA256),
            failed_authorization_sha256=FAILED_AUTHORIZATION_SHA256,
            failure_code="HARNESS_AUTHORIZATION_SCHEMA_MISMATCH",
        ),
        parity_evidence=HarnessParityEvidenceBinding(
            evidence_zip_sha256=PARITY_EVIDENCE_ZIP_SHA256,
            evidence_directory=PARITY_EVIDENCE_DIRECTORY.as_posix(),
            inspection_report_path=PARITY_INSPECTION_REPORT_PATH.as_posix(),
            authorization_schema_report_path=(PARITY_AUTHORIZATION_SCHEMA_REPORT_PATH.as_posix()),
            candidate_inventory_path=PARITY_CANDIDATE_INVENTORY_PATH.as_posix(),
            evidence_sha256_path=PARITY_EVIDENCE_SHA256_PATH.as_posix(),
            notebook_name="ag-harness-parity-inspection-v4",
            producer_notebook_slug=REPLACEMENT_PRODUCER_SLUG,
            inspection_report_sha256=(
                "3137d6192bbbee5c0d35fa7cee41fb1e836c8c258bec86fcf2a5d246997a3484"
            ),
            authorization_schema_report_sha256=(
                "1620cedd514c5ae97985626e5bc13e0232562cea491d95a0e9ca5c1abeb512df"
            ),
            candidate_inventory_sha256=(
                "caac843fc293744f790048e98334cd223f3201562311382b1b592eba21b8b6dd"
            ),
            inspection_status="HARNESS_AUTHORIZATION_PARITY_PASSED",
            authorization_status="AUTHORIZATION_SCHEMA_PARITY_PASSED",
        ),
        replacement_harness=ReplacementHarnessBinding(
            source_commit=SOURCE_MAIN_MERGE_COMMIT,
            kaggle_resource_slug=REPLACEMENT_PRODUCER_SLUG,
            output_directory=REPLACEMENT_OUTPUT_DIRECTORY,
            mounted_path=REPLACEMENT_HARNESS_PATH,
            directory_sha256=REPLACEMENT_HARNESS_SHA256,
            input_mode="expanded_dataset_tree",
        ),
        unchanged_runtime_inputs=typed_inputs,
        runtime_manifest_path=RUNTIME_MANIFEST_PATH.as_posix(),
        runtime_manifest_sha256=RUNTIME_MANIFEST_SHA256,
        materialization_record_path=MATERIALIZATION_RECORD_PATH.as_posix(),
        materialization_record_sha256=MATERIALIZATION_RECORD_SHA256,
        safety=HarnessRematerializationSafety(),
        next_gate=NEXT_GATE,
    )


def load_record(path: Path) -> HarnessRematerializationRecord:
    """Load the canonical rematerialization record with safe failures."""

    try:
        return HarnessRematerializationRecord.model_validate(_load_json_object(path))
    except ValidationError as exc:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_RECORD_INVALID",
            "the harness rematerialization record failed typed validation",
            path.as_posix(),
        ) from exc


def write_default_record(path: Path) -> HarnessRematerializationRecord:
    """Write the canonical record without operational side effects."""

    record = build_default_record()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.canonical_json(), encoding="utf-8", newline="\n")
    return record


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate the record and exact updated offline-input authorities."""

    repo_root = repo_root.resolve()
    record = load_record(repo_root / RECORD_PATH)
    parity_evidence_files = (
        (
            repo_root / PARITY_INSPECTION_REPORT_PATH,
            record.parity_evidence.inspection_report_sha256,
        ),
        (
            repo_root / PARITY_AUTHORIZATION_SCHEMA_REPORT_PATH,
            record.parity_evidence.authorization_schema_report_sha256,
        ),
        (
            repo_root / PARITY_CANDIDATE_INVENTORY_PATH,
            record.parity_evidence.candidate_inventory_sha256,
        ),
    )

    for evidence_path, expected_sha256 in parity_evidence_files:
        if _file_sha256(evidence_path) != expected_sha256:
            raise HarnessRematerializationError(
                "HARNESS_REMATERIALIZATION_PARITY_EVIDENCE_DRIFT",
                "a parity evidence artifact identity drifted",
                evidence_path.relative_to(repo_root).as_posix(),
            )

    evidence_hash_manifest = _load_json_object(repo_root / PARITY_EVIDENCE_SHA256_PATH)
    expected_hash_manifest = {
        path.name: expected_sha256 for path, expected_sha256 in parity_evidence_files
    }
    if evidence_hash_manifest != expected_hash_manifest:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_PARITY_HASH_MANIFEST_DRIFT",
            "the parity evidence hash manifest drifted",
            PARITY_EVIDENCE_SHA256_PATH.as_posix(),
        )

    historical_manifest_bytes = _git_file_bytes_at_revision(
        repo_root,
        RUNTIME_MANIFEST_PATH,
        HISTORICAL_AUTHORITY_COMMIT,
    )
    historical_materialization_bytes = _git_file_bytes_at_revision(
        repo_root,
        MATERIALIZATION_RECORD_PATH,
        HISTORICAL_AUTHORITY_COMMIT,
    )
    if hashlib.sha256(historical_manifest_bytes).hexdigest() != RUNTIME_MANIFEST_SHA256:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_MANIFEST_DRIFT",
            "the historical rematerialized runtime manifest identity drifted",
            RUNTIME_MANIFEST_PATH.as_posix(),
        )
    if (
        hashlib.sha256(historical_materialization_bytes).hexdigest()
        != MATERIALIZATION_RECORD_SHA256
    ):
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_RECORD_DRIFT",
            "the historical rematerialization record identity drifted",
            MATERIALIZATION_RECORD_PATH.as_posix(),
        )

    manifest = load_historical_runtime_manifest(repo_root)
    materialization = load_historical_materialization_record(repo_root)

    expected_manifest_entries = (
        (
            "harness_source",
            "source_tree_directory",
            REPLACEMENT_HARNESS_PATH,
            REPLACEMENT_HARNESS_SHA256,
        ),
        (_MODEL_ENTRY[0], _MODEL_ENTRY[1], _MODEL_ENTRY[4], _MODEL_ENTRY[5]),
        (_VLLM_ENTRY[0], _VLLM_ENTRY[1], _VLLM_ENTRY[4], _VLLM_ENTRY[5]),
    )
    observed_manifest_entries = tuple(
        (item.role, item.artifact_format, item.mounted_path, item.sha256)
        for item in manifest.entries
    )
    if observed_manifest_entries != expected_manifest_entries:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_MANIFEST_BINDING_DRIFT",
            "runtime manifest entries no longer match the parity-approved inputs",
        )

    expected_materialization_entries = (
        (
            "harness_source",
            "source_tree_directory",
            REPLACEMENT_PRODUCER_SLUG,
            1,
            REPLACEMENT_HARNESS_PATH,
            REPLACEMENT_HARNESS_SHA256,
        ),
        _MODEL_ENTRY,
        _VLLM_ENTRY,
    )
    observed_materialization_entries = tuple(
        (
            item.role,
            item.artifact_format,
            item.kaggle_dataset_slug,
            item.kaggle_dataset_version,
            item.mounted_path,
            item.sha256,
        )
        for item in materialization.entries
    )
    if observed_materialization_entries != expected_materialization_entries:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_PROVENANCE_DRIFT",
            "materialization entries no longer match the parity-approved inputs",
        )
    if materialization.harness_source_commit != SOURCE_MAIN_MERGE_COMMIT:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_SOURCE_DRIFT",
            "materialized harness source commit drifted",
        )
    if materialization.runtime_manifest_sha256 != RUNTIME_MANIFEST_SHA256:
        raise HarnessRematerializationError(
            "HARNESS_REMATERIALIZATION_MANIFEST_LINK_DRIFT",
            "materialization record no longer binds the runtime manifest",
        )

    return {
        "record_sha256": record.fingerprint(),
        "source_main_merge_commit": record.source_main_merge_commit,
        "superseded_harness_source_commit": (record.superseded_harness.source_commit),
        "replacement_harness_sha256": (record.replacement_harness.directory_sha256),
        "replacement_file_count": record.replacement_harness.file_count,
        "replacement_total_bytes": record.replacement_harness.total_bytes,
        "parity_status": record.parity_evidence.inspection_status,
        "runner_loader_accepted_authorization": (
            record.parity_evidence.runner_loader_accepted_authorization
        ),
        "parity_evidence_files_verified": len(parity_evidence_files) + 1,
        "runtime_manifest_sha256": manifest.fingerprint(),
        "materialization_record_sha256": hashlib.sha256(
            historical_materialization_bytes
        ).hexdigest(),
        "authorization_issued": False,
        "gpu_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": record.next_gate,
    }
