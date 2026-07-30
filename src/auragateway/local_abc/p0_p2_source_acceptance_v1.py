"""Validate accepted P0-P2 source materialization and inspection evidence."""

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

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_BASE_COMMIT: Final = "24914d79ef4b4d33285f111c8920d16c36244614"
ACCEPTANCE_BASE_MAIN_COMMIT: Final = "0257678b9b6c0afc89927dd24b45cebfe1ab311f"

MATERIALIZER_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-source-materializer-v2"
MATERIALIZER_SAVED_VERSION_ID: Final = 339075357
MATERIALIZER_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-cu129-p0-p2-source-materializer-v2?scriptVersionId=339075357"
)
INSPECTION_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-source-inspection-v2"
INSPECTION_SAVED_VERSION_ID: Final = 339077364
INSPECTION_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-cu129-p0-p2-source-inspection-v2/log?scriptVersionId=339077364"
)

SOURCE_BUNDLE_SHA256: Final = "49cba1ecdf8e754792fefc05a668e81a75371dd5bef35ac7807ba7e0f2259a53"
BUNDLE_MANIFEST_SHA256: Final = "463b58b32d34f39d8c189e69cb9614cd7ca2ad2124f73e239c29b96a97f1728f"
SOURCE_INVENTORY_SHA256: Final = "855b1e77900cd5e022255d12189fce4207bf93f74671fed9ec0d74caaf29d505"
SHA256_MANIFEST_SHA256: Final = "503be20c477257200436a4e80db468e9b67323d3e638c2b229c13f83e9f49b1e"
MATERIALIZATION_RECEIPT_SHA256: Final = (
    "f03199b9b5c97f70173ad167841f064f8e18ddb95265f17711113025f18919ae"
)
INSPECTION_REPORT_SHA256: Final = "26909d06defd68f7386e404d255f6840d0f01db404995b95e389647679042339"

MATERIALIZER_LOG_SHA256: Final = "36d805036fadf9c366e7927bcae8c574b3a6e5aa83f20cd8bf9cc027daf3f288"
MATERIALIZER_RESULTS_ZIP_SHA256: Final = (
    "eb4319319d2a13536aabdad2c644c15728277e1d3265c51ac87e37e6ffd2be97"
)
INSPECTION_LOG_SHA256: Final = "1fbfe999bebb3808b5c4cadb832736d0efd599e062288363c401a6772c6a21d7"
INSPECTION_EVIDENCE_ZIP_SHA256: Final = (
    "cc04c6e287c50d3c2ba6187523174167c7e14219f1d3c96d8c7bec56eefcb21f"
)

EVIDENCE_ROOT: Final = Path("evidence_vault/local_abc/cu129-p0-p2-source-acceptance-v1")
MATERIALIZER_LOG_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p0-p2-source-materializer-v2.log")
MATERIALIZER_RESULTS_ZIP_PATH: Final = EVIDENCE_ROOT / (
    "ag-cu129-p0-p2-source-materializer-v2-results.zip"
)
INSPECTION_LOG_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p0-p2-source-inspection-v2.log")
INSPECTION_EVIDENCE_ZIP_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p0-p2-source-inspection-v2.zip")
ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_source_acceptance_v1.json"
)

BOUND_EVIDENCE_PATHS: Final = (
    MATERIALIZER_LOG_PATH,
    MATERIALIZER_RESULTS_ZIP_PATH,
    INSPECTION_LOG_PATH,
    INSPECTION_EVIDENCE_ZIP_PATH,
)

MATERIALIZER_ROOT: Final = "ag_cu129_p0_p2_source_materializer_v2_output"
MATERIALIZER_RECEIPT_MEMBER: Final = f"{MATERIALIZER_ROOT}/materialization_receipt.json"
MATERIALIZER_INVENTORY_MEMBER: Final = f"{MATERIALIZER_ROOT}/source_inventory.json"
MATERIALIZER_MANIFEST_MEMBER: Final = f"{MATERIALIZER_ROOT}/sha256_manifest.json"
INSPECTION_REPORT_MEMBER: Final = "p0_p2_source_input_inspection_report.json"

EXPECTED_MATERIALIZER_MEMBERS: Final = (
    f"{MATERIALIZER_ROOT}/auragateway_cu129_p0_p2_platform_diagnostic_implementation_v1.json",
    f"{MATERIALIZER_ROOT}/auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb",
    MATERIALIZER_RECEIPT_MEMBER,
    f"{MATERIALIZER_ROOT}/option_c_p0_p2_platform_diagnostic_request.json",
    MATERIALIZER_MANIFEST_MEMBER,
    MATERIALIZER_INVENTORY_MEMBER,
)
EXPECTED_INSPECTION_MEMBERS: Final = (
    INSPECTION_REPORT_MEMBER,
    "materialization_receipt.json",
    "sha256_manifest.json",
    "source_inventory.json",
)


class P0P2SourceAcceptanceError(RuntimeError):
    """Fail-closed P0-P2 source-acceptance error."""

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


class AcceptanceSafety(LocalABCContract):
    """Static non-execution state for source acceptance."""

    authorization_issued: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    diagnostic_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    network_requests: Literal[0] = 0
    model_requests: Literal[0] = 0
    benchmark_trajectory_requests: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_present: Literal[False] = False
    external_spend: Literal[0] = 0


class EvidenceFile(LocalABCContract):
    """Repository-bound external evidence file."""

    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class EvidenceZipMember(LocalABCContract):
    """Identity of one regular evidence ZIP member."""

    name: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class AcceptedSavedVersion(LocalABCContract):
    """Accepted immutable Kaggle saved-version locator."""

    notebook_name: str
    saved_version_id: int = Field(gt=0)
    saved_version_url: str
    log: EvidenceFile
    archive: EvidenceFile


class P0P2SourceAcceptanceRecord(LocalABCContract):
    """Accepted corrected P0-P2 source lineage."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-source-acceptance-v1"]
    status: Literal["P0_P2_SOURCE_ACCEPTANCE_INTEGRATED_V1"]
    source_main_base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    acceptance_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    materializer: AcceptedSavedVersion
    inspection: AcceptedSavedVersion
    materializer_members: tuple[EvidenceZipMember, ...]
    inspection_members: tuple[EvidenceZipMember, ...]
    materialization_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inspection_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bundle_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sha256_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_file_count: Literal[3] = 3
    operational_input_closure: Literal["PASSED"]
    safety: AcceptanceSafety
    next_gate: Literal["generate_and_validate_p0_p2_execution_launcher_v2"]

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        if self.source_main_base_commit != SOURCE_MAIN_BASE_COMMIT:
            raise ValueError("source main base commit drifted")
        if self.acceptance_base_main_commit != ACCEPTANCE_BASE_MAIN_COMMIT:
            raise ValueError("acceptance base main commit drifted")
        if self.materializer.notebook_name != MATERIALIZER_NOTEBOOK_NAME:
            raise ValueError("materializer notebook name drifted")
        if self.materializer.saved_version_id != MATERIALIZER_SAVED_VERSION_ID:
            raise ValueError("materializer saved-version ID drifted")
        if self.materializer.saved_version_url != MATERIALIZER_SAVED_VERSION_URL:
            raise ValueError("materializer saved-version URL drifted")
        if self.inspection.notebook_name != INSPECTION_NOTEBOOK_NAME:
            raise ValueError("inspection notebook name drifted")
        if self.inspection.saved_version_id != INSPECTION_SAVED_VERSION_ID:
            raise ValueError("inspection saved-version ID drifted")
        if self.inspection.saved_version_url != INSPECTION_SAVED_VERSION_URL:
            raise ValueError("inspection saved-version URL drifted")
        if self.materialization_receipt_sha256 != MATERIALIZATION_RECEIPT_SHA256:
            raise ValueError("materialization receipt identity drifted")
        if self.inspection_report_sha256 != INSPECTION_REPORT_SHA256:
            raise ValueError("inspection report identity drifted")
        if self.source_bundle_sha256 != SOURCE_BUNDLE_SHA256:
            raise ValueError("source bundle identity drifted")
        if self.bundle_manifest_sha256 != BUNDLE_MANIFEST_SHA256:
            raise ValueError("bundle manifest identity drifted")
        if self.source_inventory_sha256 != SOURCE_INVENTORY_SHA256:
            raise ValueError("source inventory identity drifted")
        if self.sha256_manifest_sha256 != SHA256_MANIFEST_SHA256:
            raise ValueError("SHA-256 manifest identity drifted")
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
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_TEMPORARY_PATH_PRESENT",
            "temporary acceptance-record path already exists",
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
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_EVIDENCE_FILE_UNSAFE",
            "required source-acceptance evidence is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_EVIDENCE_IDENTITY_DRIFT",
            "source-acceptance evidence identity drifted",
            relative_path.as_posix(),
        )
    return payload


def _load_json_object(payload: bytes, *, member_name: str) -> dict[str, object]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_JSON_INVALID",
            "source-acceptance JSON evidence is invalid",
            member_name,
        ) from error
    if not isinstance(raw, dict):
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_JSON_ROOT_INVALID",
            "source-acceptance JSON root must be one object",
            member_name,
        )
    if _canonical_json(raw).encode("utf-8") != payload:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_JSON_NONCANONICAL",
            "source-acceptance JSON evidence is not canonical",
            member_name,
        )
    return {str(key): value for key, value in raw.items()}


def _load_json_array(payload: bytes, *, member_name: str) -> list[object]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_JSON_INVALID",
            "source-acceptance JSON evidence is invalid",
            member_name,
        ) from error
    if not isinstance(raw, list):
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_JSON_ROOT_INVALID",
            "source-acceptance JSON root must be one array",
            member_name,
        )
    if _canonical_json(raw).encode("utf-8") != payload:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_JSON_NONCANONICAL",
            "source-acceptance JSON evidence is not canonical",
            member_name,
        )
    return cast(list[object], raw)


def _read_zip(
    payload: bytes,
    *,
    archive_name: str,
    expected_names: tuple[str, ...],
) -> tuple[dict[str, bytes], tuple[EvidenceZipMember, ...]]:
    members: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise P0P2SourceAcceptanceError(
                    "P0_P2_SOURCE_ACCEPTANCE_ZIP_DUPLICATE_MEMBER",
                    "source-acceptance evidence ZIP has duplicate members",
                    archive_name,
                )
            if tuple(sorted(names)) != tuple(sorted(expected_names)):
                raise P0P2SourceAcceptanceError(
                    "P0_P2_SOURCE_ACCEPTANCE_ZIP_MEMBER_SET_DRIFT",
                    "source-acceptance evidence ZIP member set drifted",
                    archive_name,
                )
            for info in infos:
                path = PurePosixPath(info.filename)
                mode = info.external_attr >> 16
                if path.is_absolute() or ".." in path.parts or info.is_dir() or stat.S_ISLNK(mode):
                    raise P0P2SourceAcceptanceError(
                        "P0_P2_SOURCE_ACCEPTANCE_ZIP_MEMBER_UNSAFE",
                        "source-acceptance evidence ZIP contains an unsafe member",
                        info.filename,
                    )
                members[info.filename] = archive.read(info.filename)
    except zipfile.BadZipFile as error:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_ZIP_INVALID",
            "source-acceptance evidence ZIP is invalid",
            archive_name,
        ) from error

    identities = tuple(
        EvidenceZipMember(
            name=name,
            sha256=_sha256_bytes(members[name]),
            size_bytes=len(members[name]),
        )
        for name in sorted(members)
    )
    return members, identities


def _last_log_json(payload: bytes, *, path: Path) -> dict[str, object]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_LOG_ENCODING_INVALID",
            "source-acceptance log is not valid UTF-8",
            path.as_posix(),
        ) from error

    candidate: dict[str, object] | None = None
    for line in text.splitlines():
        start = line.find("{")
        if start < 0:
            continue
        try:
            raw = json.loads(line[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            candidate = {str(key): value for key, value in raw.items()}

    if candidate is None:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_LOG_JSON_MISSING",
            "source-acceptance log has no machine-readable JSON record",
            path.as_posix(),
        )
    return candidate


def _require_mapping_value(
    payload: Mapping[str, object],
    key: str,
    expected: object,
    *,
    source: str,
) -> None:
    if payload.get(key) != expected:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_SEMANTIC_DRIFT",
            f"source-acceptance semantic binding drifted: {key}",
            source,
        )


def _validate_common_source_bindings(
    payload: Mapping[str, object],
    *,
    source: str,
) -> None:
    expected = {
        "source_main_base_commit": SOURCE_MAIN_BASE_COMMIT,
        "source_bundle_sha256": SOURCE_BUNDLE_SHA256,
        "source_inventory_sha256": SOURCE_INVENTORY_SHA256,
        "source_file_count": 3,
        "external_spend": 0,
        "model_loads": 0,
        "model_requests": 0,
        "worker_starts": 0,
        "benchmark_trajectory_requests": 0,
    }
    for key, value in expected.items():
        _require_mapping_value(payload, key, value, source=source)


def build_acceptance_record(repo_root: Path) -> P0P2SourceAcceptanceRecord:
    """Build the accepted source-lineage record from repository evidence."""

    materializer_log = _read_bound_file(
        repo_root,
        MATERIALIZER_LOG_PATH,
        MATERIALIZER_LOG_SHA256,
    )
    materializer_zip = _read_bound_file(
        repo_root,
        MATERIALIZER_RESULTS_ZIP_PATH,
        MATERIALIZER_RESULTS_ZIP_SHA256,
    )
    inspection_log = _read_bound_file(
        repo_root,
        INSPECTION_LOG_PATH,
        INSPECTION_LOG_SHA256,
    )
    inspection_zip = _read_bound_file(
        repo_root,
        INSPECTION_EVIDENCE_ZIP_PATH,
        INSPECTION_EVIDENCE_ZIP_SHA256,
    )

    materializer_members, materializer_member_identities = _read_zip(
        materializer_zip,
        archive_name=MATERIALIZER_RESULTS_ZIP_PATH.as_posix(),
        expected_names=EXPECTED_MATERIALIZER_MEMBERS,
    )
    inspection_members, inspection_member_identities = _read_zip(
        inspection_zip,
        archive_name=INSPECTION_EVIDENCE_ZIP_PATH.as_posix(),
        expected_names=EXPECTED_INSPECTION_MEMBERS,
    )

    receipt_bytes = materializer_members[MATERIALIZER_RECEIPT_MEMBER]
    inventory_bytes = materializer_members[MATERIALIZER_INVENTORY_MEMBER]
    manifest_bytes = materializer_members[MATERIALIZER_MANIFEST_MEMBER]
    report_bytes = inspection_members[INSPECTION_REPORT_MEMBER]

    if _sha256_bytes(receipt_bytes) != MATERIALIZATION_RECEIPT_SHA256:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_RECEIPT_IDENTITY_DRIFT",
            "materialization receipt identity drifted",
            MATERIALIZER_RECEIPT_MEMBER,
        )
    if _sha256_bytes(inventory_bytes) != SOURCE_INVENTORY_SHA256:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_INVENTORY_IDENTITY_DRIFT",
            "source inventory identity drifted",
            MATERIALIZER_INVENTORY_MEMBER,
        )
    if _sha256_bytes(manifest_bytes) != SHA256_MANIFEST_SHA256:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_MANIFEST_IDENTITY_DRIFT",
            "SHA-256 manifest identity drifted",
            MATERIALIZER_MANIFEST_MEMBER,
        )
    if _sha256_bytes(report_bytes) != INSPECTION_REPORT_SHA256:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_REPORT_IDENTITY_DRIFT",
            "inspection report identity drifted",
            INSPECTION_REPORT_MEMBER,
        )

    expected_cross_archive = {
        "materialization_receipt.json": receipt_bytes,
        "source_inventory.json": inventory_bytes,
        "sha256_manifest.json": manifest_bytes,
    }
    for name, expected_bytes in expected_cross_archive.items():
        if inspection_members[name] != expected_bytes:
            raise P0P2SourceAcceptanceError(
                "P0_P2_SOURCE_ACCEPTANCE_CROSS_ARCHIVE_DRIFT",
                "inspection evidence does not preserve materializer bytes",
                name,
            )

    receipt = _load_json_object(receipt_bytes, member_name=MATERIALIZER_RECEIPT_MEMBER)
    inventory = _load_json_array(
        inventory_bytes,
        member_name=MATERIALIZER_INVENTORY_MEMBER,
    )
    sha_manifest = _load_json_object(
        manifest_bytes,
        member_name=MATERIALIZER_MANIFEST_MEMBER,
    )
    report = _load_json_object(report_bytes, member_name=INSPECTION_REPORT_MEMBER)
    materializer_log_record = _last_log_json(
        materializer_log,
        path=MATERIALIZER_LOG_PATH,
    )
    inspection_log_record = _last_log_json(
        inspection_log,
        path=INSPECTION_LOG_PATH,
    )

    if len(inventory) != 3:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_INVENTORY_COUNT_DRIFT",
            "source inventory must contain exactly three artifacts",
            MATERIALIZER_INVENTORY_MEMBER,
        )
    if len(sha_manifest) != 4:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_MANIFEST_COUNT_DRIFT",
            "SHA-256 manifest must contain exactly four bindings",
            MATERIALIZER_MANIFEST_MEMBER,
        )

    _validate_common_source_bindings(receipt, source=MATERIALIZER_RECEIPT_MEMBER)
    _require_mapping_value(
        receipt,
        "status",
        "P0_P2_SOURCE_MATERIALIZED_V2",
        source=MATERIALIZER_RECEIPT_MEMBER,
    )
    _require_mapping_value(
        receipt,
        "bundle_manifest_sha256",
        BUNDLE_MANIFEST_SHA256,
        source=MATERIALIZER_RECEIPT_MEMBER,
    )
    _require_mapping_value(
        receipt,
        "sha256_manifest_sha256",
        SHA256_MANIFEST_SHA256,
        source=MATERIALIZER_RECEIPT_MEMBER,
    )
    _require_mapping_value(
        receipt,
        "credentials_present",
        False,
        source=MATERIALIZER_RECEIPT_MEMBER,
    )
    _require_mapping_value(
        receipt,
        "customer_data_present",
        False,
        source=MATERIALIZER_RECEIPT_MEMBER,
    )

    _validate_common_source_bindings(report, source=INSPECTION_REPORT_MEMBER)
    _require_mapping_value(
        report,
        "status",
        "P0_P2_SOURCE_INPUT_INSPECTION_PASSED_V2",
        source=INSPECTION_REPORT_MEMBER,
    )
    _require_mapping_value(
        report,
        "bundle_manifest_sha256",
        BUNDLE_MANIFEST_SHA256,
        source=INSPECTION_REPORT_MEMBER,
    )
    _require_mapping_value(
        report,
        "notebook_outputs_present",
        False,
        source=INSPECTION_REPORT_MEMBER,
    )
    _require_mapping_value(
        report,
        "notebook_execution_counts_present",
        False,
        source=INSPECTION_REPORT_MEMBER,
    )
    _require_mapping_value(
        report,
        "credentials_used",
        False,
        source=INSPECTION_REPORT_MEMBER,
    )
    _require_mapping_value(
        report,
        "customer_data_present",
        False,
        source=INSPECTION_REPORT_MEMBER,
    )

    materializer_log_expected = {
        "status": "P0_P2_SOURCE_MATERIALIZED_V2",
        "next_gate": "execute_metadata_only_p0_p2_source_inspection_v2",
        "output_dataset_name": "ag-cu129-p0-p2-source-v2",
        "output_directory": ("/kaggle/working/ag_cu129_p0_p2_source_materializer_v2_output"),
        "source_bundle_sha256": SOURCE_BUNDLE_SHA256,
        "source_file_count": 3,
    }
    for key, value in materializer_log_expected.items():
        _require_mapping_value(
            materializer_log_record,
            key,
            value,
            source=MATERIALIZER_LOG_PATH.as_posix(),
        )

    _validate_common_source_bindings(
        inspection_log_record,
        source=INSPECTION_LOG_PATH.as_posix(),
    )
    _require_mapping_value(
        inspection_log_record,
        "status",
        "P0_P2_SOURCE_INPUT_INSPECTION_PASSED_V2",
        source=INSPECTION_LOG_PATH.as_posix(),
    )
    _require_mapping_value(
        inspection_log_record,
        "next_gate",
        "integrate_materialized_p0_p2_source_with_execution_launcher_v2",
        source=INSPECTION_LOG_PATH.as_posix(),
    )
    _require_mapping_value(
        inspection_log_record,
        "inspection_evidence_zip_sha256",
        INSPECTION_EVIDENCE_ZIP_SHA256,
        source=INSPECTION_LOG_PATH.as_posix(),
    )

    return P0P2SourceAcceptanceRecord(
        record_id="auragateway-cu129-p0-p2-source-acceptance-v1",
        status="P0_P2_SOURCE_ACCEPTANCE_INTEGRATED_V1",
        source_main_base_commit=SOURCE_MAIN_BASE_COMMIT,
        acceptance_base_main_commit=ACCEPTANCE_BASE_MAIN_COMMIT,
        materializer=AcceptedSavedVersion(
            notebook_name=MATERIALIZER_NOTEBOOK_NAME,
            saved_version_id=MATERIALIZER_SAVED_VERSION_ID,
            saved_version_url=MATERIALIZER_SAVED_VERSION_URL,
            log=EvidenceFile(
                repository_path=MATERIALIZER_LOG_PATH.as_posix(),
                sha256=MATERIALIZER_LOG_SHA256,
                size_bytes=len(materializer_log),
            ),
            archive=EvidenceFile(
                repository_path=MATERIALIZER_RESULTS_ZIP_PATH.as_posix(),
                sha256=MATERIALIZER_RESULTS_ZIP_SHA256,
                size_bytes=len(materializer_zip),
            ),
        ),
        inspection=AcceptedSavedVersion(
            notebook_name=INSPECTION_NOTEBOOK_NAME,
            saved_version_id=INSPECTION_SAVED_VERSION_ID,
            saved_version_url=INSPECTION_SAVED_VERSION_URL,
            log=EvidenceFile(
                repository_path=INSPECTION_LOG_PATH.as_posix(),
                sha256=INSPECTION_LOG_SHA256,
                size_bytes=len(inspection_log),
            ),
            archive=EvidenceFile(
                repository_path=INSPECTION_EVIDENCE_ZIP_PATH.as_posix(),
                sha256=INSPECTION_EVIDENCE_ZIP_SHA256,
                size_bytes=len(inspection_zip),
            ),
        ),
        materializer_members=materializer_member_identities,
        inspection_members=inspection_member_identities,
        materialization_receipt_sha256=MATERIALIZATION_RECEIPT_SHA256,
        inspection_report_sha256=INSPECTION_REPORT_SHA256,
        source_bundle_sha256=SOURCE_BUNDLE_SHA256,
        bundle_manifest_sha256=BUNDLE_MANIFEST_SHA256,
        source_inventory_sha256=SOURCE_INVENTORY_SHA256,
        sha256_manifest_sha256=SHA256_MANIFEST_SHA256,
        operational_input_closure="PASSED",
        safety=AcceptanceSafety(),
        next_gate="generate_and_validate_p0_p2_execution_launcher_v2",
    )


def generate(repo_root: Path) -> P0P2SourceAcceptanceRecord:
    """Generate the canonical acceptance record from bound evidence."""

    record = build_acceptance_record(repo_root)
    payload = record.canonical_json().encode("utf-8")
    _write_bytes_atomic(repo_root / ACCEPTANCE_RECORD_PATH, payload)
    return record


def validate(repo_root: Path) -> P0P2SourceAcceptanceRecord:
    """Validate bound evidence and the byte-identical acceptance record."""

    expected = build_acceptance_record(repo_root)
    path = repo_root / ACCEPTANCE_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_RECORD_MISSING",
            "source-acceptance record is missing or unsafe",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    try:
        observed = P0P2SourceAcceptanceRecord.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_RECORD_INVALID",
            "source-acceptance record violates its contract",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        ) from error
    expected_bytes = expected.canonical_json().encode("utf-8")
    if observed != expected or path.read_bytes() != expected_bytes:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_RECORD_DRIFT",
            "source-acceptance record differs from deterministic rebuild",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    return expected


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise P0P2SourceAcceptanceError(
            "P0_P2_SOURCE_ACCEPTANCE_ARGUMENT_INVALID",
            message,
        )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            record = generate(repo_root)
            status = "P0_P2_SOURCE_ACCEPTANCE_RECORD_GENERATED"
        else:
            record = validate(repo_root)
            status = record.status
        print(
            _canonical_json(
                {
                    "status": status,
                    "materializer_saved_version_id": (record.materializer.saved_version_id),
                    "inspection_saved_version_id": (record.inspection.saved_version_id),
                    "inspection_evidence_zip_sha256": (record.inspection.archive.sha256),
                    "operational_input_closure": record.operational_input_closure,
                    "next_gate": record.next_gate,
                }
            )
        )
        return 0
    except P0P2SourceAcceptanceError as error:
        print(_canonical_json(error.envelope()), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
