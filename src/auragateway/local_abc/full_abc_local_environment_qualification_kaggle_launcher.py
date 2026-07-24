"""Generate and verify governed Kaggle qualification notebooks."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Final, Literal, Never, cast

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from auragateway.local_abc import (
    full_abc_local_environment_qualification_worker_startup_diagnostics as startup_diagnostics,
)

SOURCE_MAIN_MERGE_COMMIT: Final = "dceda98989386de7a4d57616f9f8a8023f866f10"
AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT: Final = "211a10757999b1b110cb1d9df172938cf6ed7969"
AUTHORIZATION_SOURCE_BINDING_POLICY: Final = "CONTROL_PACKAGE_AUTHORIZATION_PARITY"

REVIEWED_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_v1.ipynb"
)
LAUNCHER_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
DATASET_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)

PREFLIGHT_ARTIFACT_NAME: Final = "ag-input-preflight-v1.zip"
PREFLIGHT_ARTIFACT_SHA256: Final = (
    "55c65f0edfd6fbd0b3dfb17070e5f40e849db17b494a43d8a5fcaa2b3ce841c3"
)
HARNESS_PARITY_EVIDENCE_NAME: Final = "ag-harness-parity-evidence-v1.zip"
HARNESS_PARITY_EVIDENCE_SHA256: Final = (
    "b986f3b82785f86dea2c8fb368dd8ae4def7ee3d7b00f44637f77f3d28b1971b"
)
CONTROL_DISCOVERY_FAILURE_CODE: Final = "CONTROL_OUTPUT_NAMESPACE_COLLISION"
CONTROL_DISCOVERY_FAILURE_EVIDENCE_SHA256: Final = (
    "55910873d6282ce8b98efd2726d2630bfed4f1c706eb4ec6484adb8a66885926"
)
CONTROL_DISCOVERY_REMEDIATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_environment_qualification_"
    "control_output_discovery_remediation_v1.json"
)

CONTROL_NOTEBOOK_NAME: Final = "ag-qualification-control-materializer-v1"
LAUNCHER_NOTEBOOK_NAME: Final = "ag-full-abc-env-qualification-v1"
EVIDENCE_ZIP_NAME: Final = "ag-qualification-evidence-v1.zip"

CONTROL_OUTPUT_DIRECTORY_NAME: Final = "ag_qualification_control_v1"
CONTROL_MANIFEST_NAME: Final = "control_package_manifest.json"
CONTROL_RECEIPT_NAME: Final = "materialization_receipt.json"
AUTHORIZATION_FILENAME: Final = AUTHORIZATION_PATH.name
DATASET_MANIFEST_FILENAME: Final = DATASET_MANIFEST_PATH.name

HARNESS_SOURCE_PATH: Final = (
    "/kaggle/input/notebooks/kabomolefe/"
    "ag-worker-obs-harness-materializer-v1/"
    "ag_worker_obs_harness_materializer_v1_output/"
    "auragateway_qualification_harness_dceda98_worker_obs_v1"
)
MODEL_SNAPSHOT_PATH: Final = (
    "/kaggle/input/datasets/kabomolefe/"
    "auragateway-qwen2-5-0-5b-offline-v1/"
    "auragateway-qwen2.5-0.5b-instruct-"
    "7ae557604adf67be50417f59c2c2f167def9a775/"
    "hf_home/hub/models--Qwen--Qwen2.5-0.5B-Instruct/"
    "snapshots/7ae557604adf67be50417f59c2c2f167def9a775"
)
RUNTIME_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_wheelhouse_v1"
RUNTIME_RESOLUTION_LOCK_SHA256: Final = (
    "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
)
RUNTIME_MANIFEST_SHA256: Final = "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
RUNTIME_SHA256_MANIFEST_SHA256: Final = (
    "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
)
RUNTIME_MATERIALIZATION_RECEIPT_SHA256: Final = (
    "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
)
RUNTIME_PACKAGE_COUNT: Final = 176

MAXIMUM_KAGGLE_NAME_CHARACTERS: Final = 50
MAXIMUM_EVIDENCE_ZIP_BYTES: Final = 2 * 1024 * 1024
MINIMUM_CONTROL_WINDOW_MINUTES: Final = 180
MINIMUM_LAUNCH_WINDOW_MINUTES: Final = 120

RUNTIME_EVIDENCE_PATHS: Final = (
    "data/evals/benchmark/environment-qualification-v1/cache_metric_capability_report.json",
    "data/evals/benchmark/environment-qualification-v1/gpu_topology_report.json",
    "data/evals/benchmark/environment-qualification-v1/kaggle_runtime_dependency_lock.json",
    "data/evals/benchmark/environment-qualification-v1/manifest.json",
    "data/evals/benchmark/environment-qualification-v1/model_identity_report.json",
    "data/evals/benchmark/environment-qualification-v1/qualification_report.json",
    "data/evals/benchmark/environment-qualification-v1/reset_capability_report.json",
    "data/evals/benchmark/environment-qualification-v1/worker_health_report.json",
)
WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH: Final = (
    startup_diagnostics.WORKER_STARTUP_DIAGNOSTIC_PATH.as_posix()
)
MAXIMUM_WORKER_STARTUP_DIAGNOSTIC_BYTES: Final = startup_diagnostics.MAXIMUM_DIAGNOSTIC_BYTES


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class KaggleLauncherError(RuntimeError):
    """Metadata-safe failure while building or verifying launcher notebooks."""

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


class KaggleLauncherErrorEnvelope(_StrictModel):
    """Machine-readable launcher failure without sensitive payloads."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class KaggleControlPackageManifest(_StrictModel):
    """Immutable lineage for one short-lived notebook control output."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    control_package_id: Literal["auragateway-qualification-control-v1"]
    source_main_merge_commit: Literal["dceda98989386de7a4d57616f9f8a8023f866f10"]
    authorization_source_main_merge_commit: str
    authorization_file: Literal[
        "auragateway_full_abc_local_full_run_environment_qualification_"
        "execution_authorization_v1.json"
    ]
    authorization_file_sha256: str
    authorization_contract_sha256: str
    dataset_manifest_file: Literal["offline_dataset_manifest.json"]
    dataset_manifest_file_sha256: str
    dataset_manifest_contract_sha256: str
    issued_at: str
    expires_at: str
    harness_source_path: Literal[
        "/kaggle/input/notebooks/kabomolefe/"
        "ag-worker-obs-harness-materializer-v1/"
        "ag_worker_obs_harness_materializer_v1_output/"
        "auragateway_qualification_harness_dceda98_worker_obs_v1"
    ]
    model_snapshot_path: Literal[
        "/kaggle/input/datasets/kabomolefe/"
        "auragateway-qwen2-5-0-5b-offline-v1/"
        "auragateway-qwen2.5-0.5b-instruct-"
        "7ae557604adf67be50417f59c2c2f167def9a775/"
        "hf_home/hub/models--Qwen--Qwen2.5-0.5B-Instruct/"
        "snapshots/7ae557604adf67be50417f59c2c2f167def9a775"
    ]
    runtime_output_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    runtime_resolution_lock_sha256: str
    runtime_manifest_sha256: str
    runtime_sha256_manifest_sha256: str
    runtime_materialization_receipt_sha256: str
    runtime_package_count: Literal[176]
    network_access_permitted: Literal[False] = False
    credentials_present: Literal[False] = False
    customer_data_present: Literal[False] = False
    hosted_provider_inputs_present: Literal[False] = False
    external_spend: Literal[0] = 0

    @field_validator(
        "authorization_file_sha256",
        "authorization_contract_sha256",
        "dataset_manifest_file_sha256",
        "dataset_manifest_contract_sha256",
        "runtime_resolution_lock_sha256",
        "runtime_manifest_sha256",
        "runtime_sha256_manifest_sha256",
        "runtime_materialization_receipt_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("control package digests must be lowercase SHA-256")
        return value

    @field_validator("authorization_source_main_merge_commit")
    @classmethod
    def validate_authorization_source_commit(cls, value: str) -> str:
        if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("authorization source commit must be one lowercase Git object id")
        return value

    @model_validator(mode="after")
    def validate_timestamps(self) -> KaggleControlPackageManifest:
        issued_at = datetime.fromisoformat(self.issued_at.replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        if issued_at.tzinfo is None or expires_at.tzinfo is None:
            raise ValueError("control package timestamps must be timezone-aware")
        if expires_at <= issued_at:
            raise ValueError("control package expiry must follow issuance")
        expected_runtime = {
            "runtime_resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
            "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
            "runtime_sha256_manifest_sha256": RUNTIME_SHA256_MANIFEST_SHA256,
            "runtime_materialization_receipt_sha256": (RUNTIME_MATERIALIZATION_RECEIPT_SHA256),
        }
        if any(getattr(self, key) != value for key, value in expected_runtime.items()):
            raise ValueError("control package CUDA 12.9 runtime identity drifted")
        return self


class KaggleNotebookVerification(_StrictModel):
    """Deterministic verification result for one generated notebook."""

    notebook_path: str
    notebook_name: str
    notebook_sha256: str
    reviewed_core_sha256: str
    cell_count: int
    output_cells_present: Literal[False] = False
    execution_counts_present: Literal[False] = False
    evidence_zip_name: str | None = None
    maximum_evidence_zip_bytes: int | None = None


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_ARGUMENT_INVALID",
            "Kaggle launcher arguments are invalid",
            details=(message,),
        )


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_FILE_UNREADABLE",
            "a launcher-bound file could not be read",
            path.as_posix(),
        ) from exc


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_FILE_MISSING",
            "a required launcher file is missing",
            path.as_posix(),
        ) from exc
    except json.JSONDecodeError as exc:
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_JSON_INVALID",
            "a required launcher file is not valid JSON",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_JSON_ROOT_INVALID",
            "a required launcher file must contain one JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _write_text_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_WRITE_FAILED",
            "a generated notebook could not be written atomically",
            path.as_posix(),
        ) from exc


def _notebook_source(cell: dict[str, object]) -> str:
    source = cell.get("source")
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(cast(list[str], source))
    raise KaggleLauncherError(
        "KAGGLE_NOTEBOOK_CELL_INVALID",
        "a notebook cell contains an invalid source field",
    )


def _load_reviewed_core(repo_root: Path) -> tuple[str, str]:
    notebook_path = repo_root / REVIEWED_NOTEBOOK_PATH
    notebook = _load_json_object(notebook_path)
    cells = notebook.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        raise KaggleLauncherError(
            "REVIEWED_NOTEBOOK_SHAPE_DRIFT",
            "the reviewed qualification notebook cell set drifted",
            REVIEWED_NOTEBOOK_PATH.as_posix(),
        )
    markdown_cell, code_cell = cells
    if not isinstance(markdown_cell, dict) or not isinstance(code_cell, dict):
        raise KaggleLauncherError(
            "REVIEWED_NOTEBOOK_CELL_INVALID",
            "the reviewed qualification notebook contains an invalid cell",
            REVIEWED_NOTEBOOK_PATH.as_posix(),
        )
    if markdown_cell.get("cell_type") != "markdown" or code_cell.get("cell_type") != "code":
        raise KaggleLauncherError(
            "REVIEWED_NOTEBOOK_CELL_ORDER_DRIFT",
            "the reviewed qualification notebook cell order drifted",
            REVIEWED_NOTEBOOK_PATH.as_posix(),
        )
    if code_cell.get("execution_count") is not None or code_cell.get("outputs") not in ([], None):
        raise KaggleLauncherError(
            "REVIEWED_NOTEBOOK_NOT_CLEAN",
            "the reviewed qualification notebook contains execution state",
            REVIEWED_NOTEBOOK_PATH.as_posix(),
        )
    source = _notebook_source(code_cell)
    if "summary = execution_module.execute_from_environment()" not in source:
        raise KaggleLauncherError(
            "REVIEWED_NOTEBOOK_ENTRYPOINT_DRIFT",
            "the reviewed qualification notebook entrypoint drifted",
            REVIEWED_NOTEBOOK_PATH.as_posix(),
        )
    return source, _sha256_bytes(source.encode("utf-8"))


def _string_literal_block(
    value: str,
    *,
    indent: int = 4,
    chunk_size: int = 76,
) -> str:
    """Render one deterministic implicitly concatenated string literal block."""

    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    prefix = " " * indent
    chunks = (value[index : index + chunk_size] for index in range(0, len(value), chunk_size))
    return "\n".join(f"{prefix}{json.dumps(chunk, ensure_ascii=True)}" for chunk in chunks)


def _launcher_runtime_source(reviewed_core: str, reviewed_core_sha256: str) -> str:
    encoded_core = base64.b64encode(reviewed_core.encode("utf-8")).decode("ascii")
    template = r"""from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import stat
import sys
import traceback
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

NOTEBOOK_NAME = "__LAUNCHER_NOTEBOOK_NAME__"
INPUT_ROOT = Path("/kaggle/input").resolve()
WORK_ROOT = Path("/kaggle/working").resolve()
MATERIALIZED_HARNESS_ROOT = WORK_ROOT / "auragateway_qualification_harness"
EVIDENCE_ZIP_PATH = WORK_ROOT / "__EVIDENCE_ZIP_NAME__"

CONTROL_NOTEBOOK_TOKEN = "__CONTROL_NOTEBOOK_NAME__"
CONTROL_OUTPUT_DIRECTORY_NAME = "__CONTROL_OUTPUT_DIRECTORY_NAME__"
CONTROL_MANIFEST_NAME = "__CONTROL_MANIFEST_NAME__"
CONTROL_RECEIPT_NAME = "__CONTROL_RECEIPT_NAME__"
AUTHORIZATION_FILENAME = (
__AUTHORIZATION_FILENAME_LITERAL__
)
DATASET_MANIFEST_FILENAME = "__DATASET_MANIFEST_FILENAME__"

EXPECTED_SOURCE_MAIN_MERGE_COMMIT = "__SOURCE_MAIN_MERGE_COMMIT__"
EXPECTED_REVIEWED_CORE_SHA256 = "__REVIEWED_CORE_SHA256__"
REVIEWED_CORE_B64 = (
__REVIEWED_CORE_B64_LITERAL__
)

EXPECTED_HARNESS_SOURCE = Path(
__HARNESS_SOURCE_PATH_LITERAL__
)
EXPECTED_MODEL_SNAPSHOT = Path(
__MODEL_SNAPSHOT_PATH_LITERAL__
)
EXPECTED_RUNTIME_OUTPUT_DIRECTORY = "__RUNTIME_OUTPUT_DIRECTORY__"
EXPECTED_RUNTIME_RESOLUTION_LOCK_SHA256 = (
    "__RUNTIME_RESOLUTION_LOCK_SHA256__"
)
EXPECTED_RUNTIME_MANIFEST_SHA256 = (
    "__RUNTIME_MANIFEST_SHA256__"
)
EXPECTED_RUNTIME_SHA256_MANIFEST_SHA256 = (
    "__RUNTIME_SHA256_MANIFEST_SHA256__"
)
EXPECTED_RUNTIME_MATERIALIZATION_RECEIPT_SHA256 = (
    "__RUNTIME_MATERIALIZATION_RECEIPT_SHA256__"
)
EXPECTED_RUNTIME_PACKAGE_COUNT = __RUNTIME_PACKAGE_COUNT__

MINIMUM_LAUNCH_WINDOW_MINUTES = __MINIMUM_LAUNCH_WINDOW_MINUTES__
MAXIMUM_EVIDENCE_ZIP_BYTES = __MAXIMUM_EVIDENCE_ZIP_BYTES__
WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH = (
    "__WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH__"
)
MAXIMUM_WORKER_STARTUP_DIAGNOSTIC_BYTES = (
    __MAXIMUM_WORKER_STARTUP_DIAGNOSTIC_BYTES__
)

RUNTIME_EVIDENCE_PATHS = (
__RUNTIME_EVIDENCE_TUPLE__
)

stage = "launcher_initialization"
harness_identity_observation: dict[str, object] | None = None


@dataclass(frozen=True)
class DirectoryIdentity:
    sha256: str
    file_count: int
    total_bytes: int


class HarnessIdentityMismatch(RuntimeError):
    error_code = "HARNESS_SOURCE_IDENTITY_MISMATCH"

    def __init__(
        self,
        *,
        expected_sha256: str,
        observed_identity: DirectoryIdentity,
        manifest_path_relative_to_input: str,
        resolved_path_relative_to_input: str,
    ) -> None:
        super().__init__("harness_source identity does not match the manifest")
        self.expected_sha256 = expected_sha256
        self.observed_sha256 = observed_identity.sha256
        self.observed_file_count = observed_identity.file_count
        self.observed_total_bytes = observed_identity.total_bytes
        self.manifest_path_relative_to_input = manifest_path_relative_to_input
        self.resolved_path_relative_to_input = resolved_path_relative_to_input


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def input_relative_path(path: Path) -> str:
    resolved = path.resolve()
    if resolved == INPUT_ROOT:
        return "."
    if INPUT_ROOT not in resolved.parents:
        raise RuntimeError("harness source escaped /kaggle/input")
    return resolved.relative_to(INPUT_ROOT).as_posix()


def directory_identity(root: Path) -> DirectoryIdentity:
    entries: list[dict[str, object]] = []
    total_bytes = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise RuntimeError("harness source contains a symbolic link")
        metadata = path.stat()
        if path.is_dir():
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("harness source contains a non-regular member")
        total_bytes += metadata.st_size
        if total_bytes > 100 * 1024 * 1024:
            raise RuntimeError("harness source exceeds the bootstrap byte budget")
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": file_sha256(path),
                "size_bytes": metadata.st_size,
            }
        )
        if len(entries) > 5_000:
            raise RuntimeError("harness source exceeds the bootstrap file budget")
    if not entries:
        raise RuntimeError("harness source is empty")
    return DirectoryIdentity(
        sha256=sha256_bytes(
            canonical_json(
                {"schema_version": "1.0.0", "files": entries}
            ).encode("utf-8")
        ),
        file_count=len(entries),
        total_bytes=total_bytes,
    )


def parse_timestamp(raw_value: object) -> datetime:
    if not isinstance(raw_value, str):
        raise RuntimeError("authorization timestamp is invalid")
    value = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise RuntimeError("authorization timestamp must be timezone-aware")
    return value.astimezone(UTC)


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def resolve_control_output() -> tuple[Path, Path, Path, Path]:
    candidate_roots = tuple(
        sorted(
            (
                path.resolve()
                for path in INPUT_ROOT.rglob(CONTROL_OUTPUT_DIRECTORY_NAME)
                if path.is_dir()
                and not path.is_symlink()
                and CONTROL_NOTEBOOK_TOKEN in path.resolve().as_posix()
            ),
            key=lambda item: item.as_posix(),
        )
    )
    relative_candidates = tuple(
        path.relative_to(INPUT_ROOT).as_posix()
        for path in candidate_roots
        if INPUT_ROOT in path.parents
    )
    if len(candidate_roots) != 1:
        raise RuntimeError(
            "expected exactly one governed control-output root; "
            f"observed={len(candidate_roots)}; "
            f"candidates={relative_candidates}"
        )

    control_root = candidate_roots[0]
    if INPUT_ROOT not in control_root.parents:
        raise RuntimeError("control output escaped /kaggle/input")

    expected_control_names = {
        AUTHORIZATION_FILENAME,
        DATASET_MANIFEST_FILENAME,
        CONTROL_MANIFEST_NAME,
        CONTROL_RECEIPT_NAME,
    }
    control_members = tuple(
        sorted(
            control_root.iterdir(),
            key=lambda item: item.name,
        )
    )
    observed_control_names = {path.name for path in control_members}
    if observed_control_names != expected_control_names:
        raise RuntimeError(
            "control output file set drifted; "
            f"expected={tuple(sorted(expected_control_names))}; "
            f"observed={tuple(sorted(observed_control_names))}"
        )

    for path in control_members:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("control output contains an unsafe member type")
        if path.suffix.lower() in {".zip", ".tar", ".tgz", ".7z"}:
            raise RuntimeError("control output cannot contain nested archives")
        validate_regular_file(path, maximum_bytes=1024 * 1024)

    return (
        control_root / AUTHORIZATION_FILENAME,
        control_root / DATASET_MANIFEST_FILENAME,
        control_root / CONTROL_MANIFEST_NAME,
        control_root / CONTROL_RECEIPT_NAME,
    )


def validate_regular_file(path: Path, *, maximum_bytes: int) -> None:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"expected one regular file: {path.name}")
    if path.stat().st_size > maximum_bytes:
        raise RuntimeError(f"bounded file exceeds its size limit: {path.name}")


def load_worker_startup_diagnostic() -> bytes | None:
    path = (
        MATERIALIZED_HARNESS_ROOT
        / WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH
    )
    if not path.exists():
        return None
    validate_regular_file(
        path,
        maximum_bytes=MAXIMUM_WORKER_STARTUP_DIAGNOSTIC_BYTES,
    )
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "worker-startup diagnostic is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise RuntimeError("worker-startup diagnostic root is invalid")
    expected = {
        "schema_version": "1.0.0",
        "diagnostic_id": (
            "auragateway-environment-qualification-"
            "worker-startup-diagnostic-v1"
        ),
        "status": "FAILED",
        "raw_environment_included": False,
        "authorization_payload_included": False,
        "model_content_included": False,
        "hidden_retries_performed": 0,
        "workers_replaced": 0,
        "model_requests_performed": 0,
        "benchmark_trajectory_requests_performed": 0,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise RuntimeError("worker-startup diagnostic safety drifted")
    workers = payload.get("workers")
    if not isinstance(workers, list) or len(workers) != 2:
        raise RuntimeError("worker-startup diagnostic worker set drifted")
    identities = tuple(
        worker.get("worker_id")
        for worker in workers
        if isinstance(worker, dict)
    )
    if identities != ("worker_1", "worker_2"):
        raise RuntimeError("worker-startup diagnostic identity drifted")
    prohibited_keys = {
        "environment",
        "env",
        "authorization_payload",
        "model_content",
        "command_argv",
    }

    def reject_prohibited_keys(value: object) -> None:
        if isinstance(value, dict):
            if prohibited_keys.intersection(value):
                raise RuntimeError(
                    "worker-startup diagnostic contains prohibited fields"
                )
            for item in value.values():
                reject_prohibited_keys(item)
        elif isinstance(value, list):
            for item in value:
                reject_prohibited_keys(item)

    reject_prohibited_keys(payload)
    if raw != canonical_json(payload).encode("utf-8"):
        raise RuntimeError("worker-startup diagnostic is not canonical JSON")
    return raw


def identity_mismatch_evidence(
    error: BaseException,
) -> dict[str, object] | None:
    if getattr(error, "error_code", None) == "HARNESS_SOURCE_IDENTITY_MISMATCH":
        expected_sha256 = getattr(error, "expected_sha256", None)
        observed_sha256 = getattr(error, "observed_sha256", None)
        observed_file_count = getattr(error, "observed_file_count", None)
        observed_total_bytes = getattr(error, "observed_total_bytes", None)
        manifest_path = getattr(error, "manifest_path_relative_to_input", None)
        resolved_path = getattr(error, "resolved_path_relative_to_input", None)
        comparison_stage = "launcher_preflight"
        reviewed_core_reported_mismatch = False
    elif (
        str(error) == "harness_source identity does not match the manifest"
        and harness_identity_observation is not None
    ):
        expected_sha256 = harness_identity_observation.get("expected_sha256")
        observed_sha256 = harness_identity_observation.get("observed_sha256")
        observed_file_count = harness_identity_observation.get("observed_file_count")
        observed_total_bytes = harness_identity_observation.get("observed_total_bytes")
        manifest_path = harness_identity_observation.get(
            "manifest_path_relative_to_input"
        )
        resolved_path = harness_identity_observation.get(
            "resolved_path_relative_to_input"
        )
        comparison_stage = "reviewed_core_execution"
        reviewed_core_reported_mismatch = True
    else:
        return None

    digests = (expected_sha256, observed_sha256)
    digests_valid = all(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
        for value in digests
    )
    counts_valid = (
        isinstance(observed_file_count, int)
        and not isinstance(observed_file_count, bool)
        and observed_file_count >= 0
        and isinstance(observed_total_bytes, int)
        and not isinstance(observed_total_bytes, bool)
        and observed_total_bytes >= 0
    )
    paths_valid = all(
        isinstance(value, str)
        and value not in ("", ".")
        and not value.startswith("/")
        and ".." not in Path(value).parts
        for value in (manifest_path, resolved_path)
    )
    if not (digests_valid and counts_valid and paths_valid):
        return {
            "error_code": "HARNESS_SOURCE_IDENTITY_MISMATCH",
            "evidence_valid": False,
            "comparison_stage": comparison_stage,
            "reviewed_core_reported_mismatch": reviewed_core_reported_mismatch,
        }

    return {
        "error_code": "HARNESS_SOURCE_IDENTITY_MISMATCH",
        "evidence_valid": True,
        "comparison_stage": comparison_stage,
        "expected_sha256": expected_sha256,
        "observed_sha256": observed_sha256,
        "observed_file_count": observed_file_count,
        "observed_total_bytes": observed_total_bytes,
        "manifest_path_relative_to_input": manifest_path,
        "resolved_path_relative_to_input": resolved_path,
        "hash_parity_at_launcher_preflight": expected_sha256 == observed_sha256,
        "reviewed_core_reported_mismatch": reviewed_core_reported_mismatch,
    }


def write_failure_bundle(error: BaseException) -> None:
    evidence_found: list[str] = []
    if MATERIALIZED_HARNESS_ROOT.is_dir():
        for relative_path in RUNTIME_EVIDENCE_PATHS:
            path = MATERIALIZED_HARNESS_ROOT / relative_path
            if path.is_file() and not path.is_symlink():
                evidence_found.append(relative_path)

    diagnostic_bytes = load_worker_startup_diagnostic()
    identity_mismatch = identity_mismatch_evidence(error)
    failure = {
        "schema_version": "1.0.0",
        "status": "FAILED",
        "stage": stage,
        "captured_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "exception_type": type(error).__name__,
        "safe_message": str(error)[:1000],
        "runtime_evidence_found": sorted(evidence_found),
        "worker_startup_diagnostic_included": (
            diagnostic_bytes is not None
        ),
        "ports_open": [
            port
            for port in (8001, 8002)
            if port_open(port)
        ],
        "benchmark_trajectory_requests_permitted": 0,
        "customer_data_used": False,
        "credentials_used": False,
        "provider_calls_performed": False,
        "external_spend": 0,
        "identity_mismatch": identity_mismatch,
    }
    trace = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )[-65536:]

    if EVIDENCE_ZIP_PATH.exists():
        EVIDENCE_ZIP_PATH.unlink()

    with zipfile.ZipFile(
        EVIDENCE_ZIP_PATH,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.writestr(
            "launcher_failure.json",
            canonical_json(failure),
        )
        archive.writestr(
            "launcher_failure_trace.txt",
            trace,
        )
        if diagnostic_bytes is not None:
            archive.writestr(
                "worker_startup_diagnostic.json",
                diagnostic_bytes,
            )

    if EVIDENCE_ZIP_PATH.stat().st_size > MAXIMUM_EVIDENCE_ZIP_BYTES:
        EVIDENCE_ZIP_PATH.unlink(missing_ok=True)
        raise RuntimeError("failure evidence ZIP exceeded the size budget")

    print(f"artifact={EVIDENCE_ZIP_PATH}")
    print(f"size_bytes={EVIDENCE_ZIP_PATH.stat().st_size}")
    print(f"sha256={file_sha256(EVIDENCE_ZIP_PATH)}")
    print("qualification_status=FAILED")
    print(
        "worker_startup_diagnostic_included="
        + str(diagnostic_bytes is not None).lower()
    )
    print(
        "identity_mismatch_included="
        + str(identity_mismatch is not None).lower()
    )
    print("upload_only_this_file=true")


try:
    stage = "fresh_session_guard"

    if not INPUT_ROOT.is_dir() or not WORK_ROOT.is_dir():
        raise RuntimeError("required Kaggle filesystem roots are unavailable")

    if len(NOTEBOOK_NAME) > 50:
        raise RuntimeError("Kaggle notebook name exceeds 50 characters")

    loaded_runtime_modules = sorted(
        name
        for name in sys.modules
        if name == "vllm"
        or name.startswith("vllm.")
        or name == "transformers"
        or name.startswith("transformers.")
    )
    if loaded_runtime_modules:
        raise RuntimeError(
            "qualification requires a fresh kernel without loaded runtime modules: "
            + ", ".join(loaded_runtime_modules)
        )

    if "torch" in sys.modules:
        torch_module = sys.modules["torch"]
        cuda_module = getattr(torch_module, "cuda", None)
        is_initialized = getattr(cuda_module, "is_initialized", None)
        if callable(is_initialized) and bool(is_initialized()):
            raise RuntimeError("qualification found a pre-existing CUDA context")

    stale_runtime_keys = sorted(
        key
        for key in os.environ
        if key.startswith("AURAGATEWAY_") or key.startswith("VLLM_")
    )
    if stale_runtime_keys:
        raise RuntimeError(
            "qualification found stale AuraGateway/vLLM environment variables: "
            + ", ".join(stale_runtime_keys)
        )

    if MATERIALIZED_HARNESS_ROOT.exists():
        raise RuntimeError("writable harness destination already exists")

    if EVIDENCE_ZIP_PATH.exists():
        raise RuntimeError("qualification evidence ZIP already exists")

    open_ports = [port for port in (8001, 8002) if port_open(port)]
    if open_ports:
        raise RuntimeError(f"vLLM worker ports are already open: {open_ports}")

    for expected_path in (
        EXPECTED_HARNESS_SOURCE,
        EXPECTED_MODEL_SNAPSHOT,
    ):
        resolved = expected_path.resolve()
        if INPUT_ROOT not in resolved.parents:
            raise RuntimeError("a static input escaped /kaggle/input")
        if not resolved.exists() or resolved.is_symlink():
            raise RuntimeError(f"expected static input is unavailable: {resolved}")

    stage = "control_output_discovery"

    (
        authorization_path,
        dataset_manifest_path,
        control_manifest_path,
        receipt_path,
    ) = resolve_control_output()

    control_manifest = json.loads(
        control_manifest_path.read_text(encoding="utf-8")
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    authorization = json.loads(
        authorization_path.read_text(encoding="utf-8")
    )
    dataset_manifest = json.loads(
        dataset_manifest_path.read_text(encoding="utf-8")
    )
    if not all(
        isinstance(payload, dict)
        for payload in (
            control_manifest,
            receipt,
            authorization,
            dataset_manifest,
        )
    ):
        raise RuntimeError("control output JSON roots must be objects")

    if control_manifest.get("source_main_merge_commit") != (
        EXPECTED_SOURCE_MAIN_MERGE_COMMIT
    ):
        raise RuntimeError("control output source main binding drifted")
    authorization_source_main_merge_commit = authorization.get(
        "source_main_merge_commit"
    )
    if (
        not isinstance(authorization_source_main_merge_commit, str)
        or len(authorization_source_main_merge_commit) != 40
        or any(
            character not in "0123456789abcdef"
            for character in authorization_source_main_merge_commit
        )
    ):
        raise RuntimeError("authorization source main binding is invalid")
    if control_manifest.get("authorization_source_main_merge_commit") != (
        authorization_source_main_merge_commit
    ):
        raise RuntimeError("authorization source main binding drifted")

    if control_manifest.get("authorization_file_sha256") != file_sha256(
        authorization_path
    ):
        raise RuntimeError("authorization file identity drifted")
    if control_manifest.get("dataset_manifest_file_sha256") != file_sha256(
        dataset_manifest_path
    ):
        raise RuntimeError("dataset manifest file identity drifted")

    if receipt.get("control_manifest_sha256") != file_sha256(
        control_manifest_path
    ):
        raise RuntimeError("control materialization receipt drifted")

    if authorization.get("decision") != "AUTHORIZED":
        raise RuntimeError("authorization decision is not AUTHORIZED")

    if any(
        (
            authorization.get("maximum_workers") != 2,
            authorization.get("maximum_kaggle_sessions") != 1,
            authorization.get("maximum_model_requests") != 8,
            authorization.get("maximum_output_tokens_per_request") != 32,
            authorization.get("benchmark_trajectory_requests_permitted") != 0,
            authorization.get("network_access_permitted") is not False,
            authorization.get("credentials_permitted") is not False,
            authorization.get("customer_data_permitted") is not False,
            authorization.get("external_spend") != 0,
            authorization.get("measured_execution_authorized") is not False,
        )
    ):
        raise RuntimeError("authorization safety envelope drifted")

    expires_at = parse_timestamp(authorization.get("expires_at"))
    remaining_minutes = int(
        (expires_at - datetime.now(UTC)).total_seconds() // 60
    )
    if remaining_minutes < MINIMUM_LAUNCH_WINDOW_MINUTES:
        raise RuntimeError(
            "authorization has insufficient time remaining for a cold launch"
        )

    entries = dataset_manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != 3:
        raise RuntimeError("dataset manifest entry set drifted")
    entries_by_role = {
        str(entry.get("role")): entry
        for entry in entries
        if isinstance(entry, dict)
    }
    expected_mounts = {
        "harness_source": EXPECTED_HARNESS_SOURCE.as_posix(),
        "model_artifacts": EXPECTED_MODEL_SNAPSHOT.as_posix(),
    }
    observed_mounts = {
        role: str(entries_by_role.get(role, {}).get("mounted_path"))
        for role in expected_mounts
    }
    if observed_mounts != expected_mounts:
        raise RuntimeError("dataset manifest static mount bindings drifted")

    harness_entry = entries_by_role.get("harness_source")
    if not isinstance(harness_entry, dict):
        raise RuntimeError("dataset manifest harness_source entry is missing")
    expected_harness_sha256 = harness_entry.get("sha256")
    if not isinstance(expected_harness_sha256, str):
        raise RuntimeError("dataset manifest harness_source identity is invalid")
    observed_harness_identity = directory_identity(EXPECTED_HARNESS_SOURCE)
    harness_identity_observation = {
        "expected_sha256": expected_harness_sha256,
        "observed_sha256": observed_harness_identity.sha256,
        "observed_file_count": observed_harness_identity.file_count,
        "observed_total_bytes": observed_harness_identity.total_bytes,
        "manifest_path_relative_to_input": input_relative_path(
            Path(harness_entry.get("mounted_path"))
        ),
        "resolved_path_relative_to_input": input_relative_path(
            EXPECTED_HARNESS_SOURCE
        ),
    }
    if observed_harness_identity.sha256 != expected_harness_sha256:
        raise HarnessIdentityMismatch(
            expected_sha256=expected_harness_sha256,
            observed_identity=observed_harness_identity,
            manifest_path_relative_to_input=input_relative_path(
                Path(harness_entry.get("mounted_path"))
            ),
            resolved_path_relative_to_input=input_relative_path(
                EXPECTED_HARNESS_SOURCE
            ),
        )

    runtime_entry = entries_by_role.get("vllm_runtime")
    if not isinstance(runtime_entry, dict):
        raise RuntimeError("dataset manifest CUDA 12.9 runtime entry is missing")
    expected_runtime = {
        "artifact_format": "python_wheelhouse_directory",
        "mounted_path": None,
        "sha256": EXPECTED_RUNTIME_SHA256_MANIFEST_SHA256,
        "runtime_output_directory": EXPECTED_RUNTIME_OUTPUT_DIRECTORY,
        "resolution_lock_sha256": EXPECTED_RUNTIME_RESOLUTION_LOCK_SHA256,
        "runtime_manifest_sha256": EXPECTED_RUNTIME_MANIFEST_SHA256,
        "sha256_manifest_sha256": EXPECTED_RUNTIME_SHA256_MANIFEST_SHA256,
        "materialization_receipt_sha256": (
            EXPECTED_RUNTIME_MATERIALIZATION_RECEIPT_SHA256
        ),
        "package_count": EXPECTED_RUNTIME_PACKAGE_COUNT,
    }
    if any(runtime_entry.get(key) != value for key, value in expected_runtime.items()):
        raise RuntimeError("dataset manifest CUDA 12.9 runtime authority drifted")

    stage = "reviewed_core_execution"

    reviewed_core = base64.b64decode(
        REVIEWED_CORE_B64.encode("ascii"),
        validate=True,
    )
    if sha256_bytes(reviewed_core) != EXPECTED_REVIEWED_CORE_SHA256:
        raise RuntimeError("reviewed qualification core identity drifted")

    os.environ["AURAGATEWAY_QUALIFICATION_AUTHORIZATION"] = str(
        authorization_path
    )
    os.environ["AURAGATEWAY_QUALIFICATION_DATASET_MANIFEST"] = str(
        dataset_manifest_path
    )

    execution_namespace: dict[str, object] = {}
    exec(
        compile(
            reviewed_core.decode("utf-8"),
            "auragateway_reviewed_qualification_core_v1.py",
            "exec",
        ),
        execution_namespace,
    )

    summary = execution_namespace.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("qualification execution did not return a summary")

    expected_summary = {
        "model_request_count": 6,
        "runtime_evidence_generated": True,
        "runtime_evidence_count": 8,
        "environment_qualified": True,
        "measured_execution_authorized": False,
        "external_spend": 0,
        "next_gate": (
            "full_abc_local_full_run_environment_qualification_evidence_review"
        ),
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise RuntimeError(
                f"qualification summary drifted: {key}"
            )

    stage = "success_evidence_packaging"

    repo_root_raw = os.environ.get("AURAGATEWAY_REPO_ROOT")
    if repo_root_raw is None:
        raise RuntimeError("reviewed core did not bind AURAGATEWAY_REPO_ROOT")
    repo_root = Path(repo_root_raw).resolve()
    if repo_root != MATERIALIZED_HARNESS_ROOT.resolve():
        raise RuntimeError("reviewed core repository root drifted")

    evidence_files: list[tuple[str, Path]] = []
    evidence_checksums: dict[str, dict[str, object]] = {}
    for relative_path in RUNTIME_EVIDENCE_PATHS:
        path = repo_root / relative_path
        validate_regular_file(path, maximum_bytes=512 * 1024)
        evidence_files.append((Path(relative_path).name, path))
        evidence_checksums[Path(relative_path).name] = {
            "sha256": file_sha256(path),
            "size_bytes": path.stat().st_size,
        }

    launcher_summary = {
        "schema_version": "1.0.0",
        "status": "QUALIFIED",
        "notebook_name": NOTEBOOK_NAME,
        "captured_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reviewed_core_sha256": EXPECTED_REVIEWED_CORE_SHA256,
        "source_main_merge_commit": EXPECTED_SOURCE_MAIN_MERGE_COMMIT,
        "authorization_source_main_merge_commit": (
            authorization_source_main_merge_commit
        ),
        "authorization_file_sha256": file_sha256(authorization_path),
        "dataset_manifest_file_sha256": file_sha256(dataset_manifest_path),
        "remaining_minutes_at_launch": remaining_minutes,
        "summary": summary,
        "benchmark_trajectory_requests_permitted": 0,
        "customer_data_used": False,
        "credentials_used": False,
        "provider_calls_performed": False,
        "external_spend": 0,
    }

    if EVIDENCE_ZIP_PATH.exists():
        raise RuntimeError("qualification evidence ZIP appeared unexpectedly")

    with zipfile.ZipFile(
        EVIDENCE_ZIP_PATH,
        mode="x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for archive_name, path in sorted(evidence_files):
            archive.write(path, arcname=archive_name)
        archive.writestr(
            "evidence_bundle_sha256.json",
            canonical_json(evidence_checksums),
        )
        archive.writestr(
            "launcher_summary.json",
            canonical_json(launcher_summary),
        )

    zip_size = EVIDENCE_ZIP_PATH.stat().st_size
    if zip_size > MAXIMUM_EVIDENCE_ZIP_BYTES:
        EVIDENCE_ZIP_PATH.unlink(missing_ok=True)
        raise RuntimeError("qualification evidence ZIP exceeded the size budget")

    print(f"artifact={EVIDENCE_ZIP_PATH}")
    print(f"size_bytes={zip_size}")
    print(f"sha256={file_sha256(EVIDENCE_ZIP_PATH)}")
    print("qualification_status=QUALIFIED")
    print("runtime_evidence_count=8")
    print("model_request_count=6")
    print("benchmark_trajectory_requests_permitted=0")
    print("upload_only_this_file=true")

except BaseException as error:
    write_failure_bundle(error)
    raise
"""
    replacements = {
        "__LAUNCHER_NOTEBOOK_NAME__": LAUNCHER_NOTEBOOK_NAME,
        "__EVIDENCE_ZIP_NAME__": EVIDENCE_ZIP_NAME,
        "__CONTROL_NOTEBOOK_NAME__": CONTROL_NOTEBOOK_NAME,
        "__CONTROL_OUTPUT_DIRECTORY_NAME__": CONTROL_OUTPUT_DIRECTORY_NAME,
        "__CONTROL_MANIFEST_NAME__": CONTROL_MANIFEST_NAME,
        "__CONTROL_RECEIPT_NAME__": CONTROL_RECEIPT_NAME,
        "__AUTHORIZATION_FILENAME_LITERAL__": _string_literal_block(AUTHORIZATION_FILENAME),
        "__DATASET_MANIFEST_FILENAME__": DATASET_MANIFEST_FILENAME,
        "__SOURCE_MAIN_MERGE_COMMIT__": SOURCE_MAIN_MERGE_COMMIT,
        "__REVIEWED_CORE_SHA256__": reviewed_core_sha256,
        "__REVIEWED_CORE_B64_LITERAL__": _string_literal_block(encoded_core),
        "__HARNESS_SOURCE_PATH_LITERAL__": _string_literal_block(HARNESS_SOURCE_PATH),
        "__MODEL_SNAPSHOT_PATH_LITERAL__": _string_literal_block(MODEL_SNAPSHOT_PATH),
        "__RUNTIME_OUTPUT_DIRECTORY__": RUNTIME_OUTPUT_DIRECTORY,
        "__RUNTIME_RESOLUTION_LOCK_SHA256__": RUNTIME_RESOLUTION_LOCK_SHA256,
        "__RUNTIME_MANIFEST_SHA256__": RUNTIME_MANIFEST_SHA256,
        "__RUNTIME_SHA256_MANIFEST_SHA256__": RUNTIME_SHA256_MANIFEST_SHA256,
        "__RUNTIME_MATERIALIZATION_RECEIPT_SHA256__": (RUNTIME_MATERIALIZATION_RECEIPT_SHA256),
        "__RUNTIME_PACKAGE_COUNT__": str(RUNTIME_PACKAGE_COUNT),
        "__MINIMUM_LAUNCH_WINDOW_MINUTES__": str(MINIMUM_LAUNCH_WINDOW_MINUTES),
        "__MAXIMUM_EVIDENCE_ZIP_BYTES__": str(MAXIMUM_EVIDENCE_ZIP_BYTES),
        "__WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH__": (WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH),
        "__MAXIMUM_WORKER_STARTUP_DIAGNOSTIC_BYTES__": str(MAXIMUM_WORKER_STARTUP_DIAGNOSTIC_BYTES),
        "__RUNTIME_EVIDENCE_TUPLE__": "\n".join(
            f'    "{path}",' for path in RUNTIME_EVIDENCE_PATHS
        ),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    unresolved = tuple(marker for marker in replacements if marker in template)
    if unresolved:
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_TEMPLATE_INCOMPLETE",
            "the launcher runtime template contains unresolved markers",
            details=unresolved,
        )
    return template


def build_launcher_notebook(repo_root: Path) -> dict[str, object]:
    """Build the deterministic cold-session Kaggle launcher notebook."""

    for name in (CONTROL_NOTEBOOK_NAME, LAUNCHER_NOTEBOOK_NAME):
        if len(name) > MAXIMUM_KAGGLE_NAME_CHARACTERS:
            raise KaggleLauncherError(
                "KAGGLE_NAME_TOO_LONG",
                "a governed Kaggle notebook name exceeds 50 characters",
                details=(name,),
            )
    reviewed_core, reviewed_core_sha256 = _load_reviewed_core(repo_root.resolve())
    runtime_source = _launcher_runtime_source(
        reviewed_core,
        reviewed_core_sha256,
    )
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "launcher-introduction",
                "metadata": {},
                "source": [
                    "# AuraGateway governed full A/B/C environment qualification\n",
                    "\n",
                    "Cold-session launcher for one authorized six-probe qualification. "
                    "No benchmark trajectory is permitted. Use T4 x2, Internet Off, "
                    "no secrets, and Save Version -> Save & Run All.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "governed-launcher",
                "metadata": {},
                "outputs": [],
                "source": runtime_source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "auragateway": {
                "authorization_source_binding_policy": (AUTHORIZATION_SOURCE_BINDING_POLICY),
                "benchmark_trajectory_requests_permitted": 0,
                "control_discovery_failure_code": CONTROL_DISCOVERY_FAILURE_CODE,
                "control_discovery_failure_evidence_sha256": (
                    CONTROL_DISCOVERY_FAILURE_EVIDENCE_SHA256
                ),
                "control_discovery_remediation_record_path": (
                    CONTROL_DISCOVERY_REMEDIATION_RECORD_PATH.as_posix()
                ),
                "control_notebook_name": CONTROL_NOTEBOOK_NAME,
                "control_output_directory_name": CONTROL_OUTPUT_DIRECTORY_NAME,
                "control_output_discovery_scope": "governed_control_output_root",
                "evidence_zip_name": EVIDENCE_ZIP_NAME,
                "maximum_evidence_zip_bytes": MAXIMUM_EVIDENCE_ZIP_BYTES,
                "maximum_worker_startup_diagnostic_bytes": (
                    MAXIMUM_WORKER_STARTUP_DIAGNOSTIC_BYTES
                ),
                "worker_startup_diagnostic_relative_path": (
                    WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH
                ),
                "minimum_launch_window_minutes": (MINIMUM_LAUNCH_WINDOW_MINUTES),
                "notebook_name": LAUNCHER_NOTEBOOK_NAME,
                "preflight_artifact_sha256": PREFLIGHT_ARTIFACT_SHA256,
                "harness_parity_evidence_name": HARNESS_PARITY_EVIDENCE_NAME,
                "harness_parity_evidence_sha256": HARNESS_PARITY_EVIDENCE_SHA256,
                "reviewed_core_sha256": reviewed_core_sha256,
                "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
            },
            "kaggle": {
                "accelerator": "nvidiaTeslaT4",
                "dataSources": [],
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_launcher_notebook(
    *,
    repo_root: Path,
    output_path: Path,
) -> KaggleNotebookVerification:
    """Write and verify one deterministic launcher notebook."""

    notebook = build_launcher_notebook(repo_root)
    payload = (
        json.dumps(
            notebook,
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    )
    _write_text_atomic(output_path, payload)
    return verify_launcher_notebook(
        repo_root=repo_root,
        notebook_path=output_path,
    )


def verify_launcher_notebook(
    *,
    repo_root: Path,
    notebook_path: Path,
) -> KaggleNotebookVerification:
    """Reject any drift from the deterministic launcher notebook."""

    expected = build_launcher_notebook(repo_root)
    observed = _load_json_object(notebook_path)
    if _canonical_json(observed) != _canonical_json(expected):
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_NOTEBOOK_DRIFT",
            "the generated Kaggle launcher notebook drifted",
            notebook_path.as_posix(),
        )
    cells = cast(list[dict[str, object]], observed["cells"])
    code_cells = tuple(cell for cell in cells if cell.get("cell_type") == "code")
    output_cells_present = any(cell.get("outputs") not in ([], None) for cell in code_cells)
    execution_counts_present = any(cell.get("execution_count") is not None for cell in code_cells)
    if output_cells_present or execution_counts_present:
        raise KaggleLauncherError(
            "KAGGLE_LAUNCHER_EXECUTION_STATE_PRESENT",
            "the generated Kaggle launcher contains execution state",
            notebook_path.as_posix(),
        )
    metadata = cast(dict[str, object], observed["metadata"])
    auragateway = cast(dict[str, object], metadata["auragateway"])
    return KaggleNotebookVerification(
        notebook_path=notebook_path.as_posix(),
        notebook_name=LAUNCHER_NOTEBOOK_NAME,
        notebook_sha256=_file_sha256(notebook_path),
        reviewed_core_sha256=cast(str, auragateway["reviewed_core_sha256"]),
        cell_count=len(cells),
        output_cells_present=False,
        execution_counts_present=False,
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        maximum_evidence_zip_bytes=MAXIMUM_EVIDENCE_ZIP_BYTES,
    )


def _control_materializer_source(
    *,
    authorization_bytes: bytes,
    manifest_bytes: bytes,
    authorization_contract_sha256: str,
    manifest_contract_sha256: str,
) -> str:
    authorization_b64 = base64.b64encode(authorization_bytes).decode("ascii")
    manifest_b64 = base64.b64encode(manifest_bytes).decode("ascii")
    authorization_file_sha256 = _sha256_bytes(authorization_bytes)
    manifest_file_sha256 = _sha256_bytes(manifest_bytes)

    template = r"""from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

NOTEBOOK_NAME = "__CONTROL_NOTEBOOK_NAME__"
WORK_ROOT = Path("/kaggle/working").resolve()
OUTPUT_ROOT = WORK_ROOT / "__CONTROL_OUTPUT_DIRECTORY_NAME__"

AUTHORIZATION_FILENAME = (
__AUTHORIZATION_FILENAME_LITERAL__
)
DATASET_MANIFEST_FILENAME = "__DATASET_MANIFEST_FILENAME__"
CONTROL_OUTPUT_DIRECTORY_NAME = "__CONTROL_OUTPUT_DIRECTORY_NAME__"
CONTROL_MANIFEST_NAME = "__CONTROL_MANIFEST_NAME__"
CONTROL_RECEIPT_NAME = "__CONTROL_RECEIPT_NAME__"

AUTHORIZATION_B64 = (
__AUTHORIZATION_B64_LITERAL__
)
DATASET_MANIFEST_B64 = (
__DATASET_MANIFEST_B64_LITERAL__
)
EXPECTED_AUTHORIZATION_FILE_SHA256 = (
__AUTHORIZATION_FILE_SHA256_LITERAL__
)
EXPECTED_DATASET_MANIFEST_FILE_SHA256 = (
__MANIFEST_FILE_SHA256_LITERAL__
)
AUTHORIZATION_CONTRACT_SHA256 = (
__AUTHORIZATION_CONTRACT_SHA256_LITERAL__
)
DATASET_MANIFEST_CONTRACT_SHA256 = (
__MANIFEST_CONTRACT_SHA256_LITERAL__
)

SOURCE_MAIN_MERGE_COMMIT = "__SOURCE_MAIN_MERGE_COMMIT__"
MINIMUM_CONTROL_WINDOW_MINUTES = __MINIMUM_CONTROL_WINDOW_MINUTES__

HARNESS_SOURCE_PATH = (
__HARNESS_SOURCE_PATH_LITERAL__
)
MODEL_SNAPSHOT_PATH = (
__MODEL_SNAPSHOT_PATH_LITERAL__
)
RUNTIME_OUTPUT_DIRECTORY = "__RUNTIME_OUTPUT_DIRECTORY__"
RUNTIME_RESOLUTION_LOCK_SHA256 = "__RUNTIME_RESOLUTION_LOCK_SHA256__"
RUNTIME_MANIFEST_SHA256 = "__RUNTIME_MANIFEST_SHA256__"
RUNTIME_SHA256_MANIFEST_SHA256 = "__RUNTIME_SHA256_MANIFEST_SHA256__"
RUNTIME_MATERIALIZATION_RECEIPT_SHA256 = (
    "__RUNTIME_MATERIALIZATION_RECEIPT_SHA256__"
)
RUNTIME_PACKAGE_COUNT = __RUNTIME_PACKAGE_COUNT__


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def parse_timestamp(raw_value: object) -> datetime:
    if not isinstance(raw_value, str):
        raise RuntimeError("authorization timestamp is invalid")
    value = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise RuntimeError("authorization timestamp must be timezone-aware")
    return value.astimezone(UTC)


if len(NOTEBOOK_NAME) > 50:
    raise RuntimeError("Kaggle notebook name exceeds 50 characters")

loaded_runtime_modules = sorted(
    name
    for name in sys.modules
    if name == "vllm"
    or name.startswith("vllm.")
    or name == "transformers"
    or name.startswith("transformers.")
)
if loaded_runtime_modules:
    raise RuntimeError(
        "control materialization requires a fresh kernel without runtime modules"
    )

stale_runtime_keys = sorted(
    key
    for key in os.environ
    if key.startswith("AURAGATEWAY_") or key.startswith("VLLM_")
)
if stale_runtime_keys:
    raise RuntimeError(
        "control materialization found stale runtime environment variables"
    )

if OUTPUT_ROOT.exists():
    raise RuntimeError("control output directory already exists")

authorization_bytes = base64.b64decode(
    AUTHORIZATION_B64.encode("ascii"),
    validate=True,
)
manifest_bytes = base64.b64decode(
    DATASET_MANIFEST_B64.encode("ascii"),
    validate=True,
)

if sha256_bytes(authorization_bytes) != EXPECTED_AUTHORIZATION_FILE_SHA256:
    raise RuntimeError("embedded authorization file identity drifted")
if sha256_bytes(manifest_bytes) != EXPECTED_DATASET_MANIFEST_FILE_SHA256:
    raise RuntimeError("embedded dataset manifest file identity drifted")

authorization = json.loads(authorization_bytes.decode("utf-8"))
dataset_manifest = json.loads(manifest_bytes.decode("utf-8"))
if not isinstance(authorization, dict) or not isinstance(dataset_manifest, dict):
    raise RuntimeError("embedded control JSON roots must be objects")

if authorization.get("decision") != "AUTHORIZED":
    raise RuntimeError("embedded authorization is not AUTHORIZED")
authorization_source_main_merge_commit = authorization.get(
    "source_main_merge_commit"
)
if (
    not isinstance(authorization_source_main_merge_commit, str)
    or len(authorization_source_main_merge_commit) != 40
    or any(
        character not in "0123456789abcdef"
        for character in authorization_source_main_merge_commit
    )
):
    raise RuntimeError("embedded authorization merge binding is invalid")
if authorization.get("dataset_manifest_sha256") != DATASET_MANIFEST_CONTRACT_SHA256:
    raise RuntimeError("embedded authorization does not bind the dataset manifest")

if any(
    (
        authorization.get("maximum_workers") != 2,
        authorization.get("maximum_kaggle_sessions") != 1,
        authorization.get("maximum_model_requests") != 8,
        authorization.get("maximum_output_tokens_per_request") != 32,
        authorization.get("benchmark_trajectory_requests_permitted") != 0,
        authorization.get("network_access_permitted") is not False,
        authorization.get("credentials_permitted") is not False,
        authorization.get("customer_data_permitted") is not False,
        authorization.get("external_spend") != 0,
        authorization.get("measured_execution_authorized") is not False,
    )
):
    raise RuntimeError("embedded authorization safety envelope drifted")

expires_at = parse_timestamp(authorization.get("expires_at"))
remaining_minutes = int(
    (expires_at - datetime.now(UTC)).total_seconds() // 60
)
if remaining_minutes < MINIMUM_CONTROL_WINDOW_MINUTES:
    raise RuntimeError(
        "authorization has insufficient time remaining for materialization"
    )

entries = dataset_manifest.get("entries")
if not isinstance(entries, list) or len(entries) != 3:
    raise RuntimeError("embedded dataset manifest entry set drifted")
entries_by_role = {
    str(entry.get("role")): entry
    for entry in entries
    if isinstance(entry, dict)
}
expected_mounts = {
    "harness_source": HARNESS_SOURCE_PATH,
    "model_artifacts": MODEL_SNAPSHOT_PATH,
}
observed_mounts = {
    role: str(entries_by_role.get(role, {}).get("mounted_path"))
    for role in expected_mounts
}
if observed_mounts != expected_mounts:
    raise RuntimeError("embedded dataset manifest static mount bindings drifted")
runtime_entry = entries_by_role.get("vllm_runtime")
if not isinstance(runtime_entry, dict):
    raise RuntimeError("embedded CUDA 12.9 runtime entry is missing")
expected_runtime = {
    "artifact_format": "python_wheelhouse_directory",
    "mounted_path": None,
    "sha256": RUNTIME_SHA256_MANIFEST_SHA256,
    "runtime_output_directory": RUNTIME_OUTPUT_DIRECTORY,
    "resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
    "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
    "sha256_manifest_sha256": RUNTIME_SHA256_MANIFEST_SHA256,
    "materialization_receipt_sha256": RUNTIME_MATERIALIZATION_RECEIPT_SHA256,
    "package_count": RUNTIME_PACKAGE_COUNT,
}
if any(runtime_entry.get(key) != value for key, value in expected_runtime.items()):
    raise RuntimeError("embedded CUDA 12.9 runtime authority drifted")

OUTPUT_ROOT.mkdir(parents=True)
authorization_path = OUTPUT_ROOT / AUTHORIZATION_FILENAME
manifest_path = OUTPUT_ROOT / DATASET_MANIFEST_FILENAME
control_manifest_path = OUTPUT_ROOT / CONTROL_MANIFEST_NAME
receipt_path = OUTPUT_ROOT / CONTROL_RECEIPT_NAME

authorization_path.write_bytes(authorization_bytes)
manifest_path.write_bytes(manifest_bytes)

control_manifest = {
    "schema_version": "1.0.0",
    "control_package_id": "auragateway-qualification-control-v1",
    "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
    "authorization_source_main_merge_commit": (
        authorization_source_main_merge_commit
    ),
    "authorization_file": AUTHORIZATION_FILENAME,
    "authorization_file_sha256": file_sha256(authorization_path),
    "authorization_contract_sha256": AUTHORIZATION_CONTRACT_SHA256,
    "dataset_manifest_file": DATASET_MANIFEST_FILENAME,
    "dataset_manifest_file_sha256": file_sha256(manifest_path),
    "dataset_manifest_contract_sha256": DATASET_MANIFEST_CONTRACT_SHA256,
    "issued_at": authorization["issued_at"],
    "expires_at": authorization["expires_at"],
    "harness_source_path": HARNESS_SOURCE_PATH,
    "model_snapshot_path": MODEL_SNAPSHOT_PATH,
    "runtime_output_directory": RUNTIME_OUTPUT_DIRECTORY,
    "runtime_resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
    "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
    "runtime_sha256_manifest_sha256": RUNTIME_SHA256_MANIFEST_SHA256,
    "runtime_materialization_receipt_sha256": (
        RUNTIME_MATERIALIZATION_RECEIPT_SHA256
    ),
    "runtime_package_count": RUNTIME_PACKAGE_COUNT,
    "network_access_permitted": False,
    "credentials_present": False,
    "customer_data_present": False,
    "hosted_provider_inputs_present": False,
    "external_spend": 0,
}
control_manifest_path.write_text(
    canonical_json(control_manifest),
    encoding="utf-8",
)

receipt = {
    "schema_version": "1.0.0",
    "status": "MATERIALIZED",
    "notebook_name": NOTEBOOK_NAME,
    "output_directory": OUTPUT_ROOT.name,
    "control_manifest_sha256": file_sha256(control_manifest_path),
    "file_count": 4,
    "nested_archives_present": False,
    "vllm_imported": False,
    "runtime_execution_performed": False,
    "model_content_copied": False,
}
receipt_path.write_text(
    canonical_json(receipt),
    encoding="utf-8",
)

expected_names = {
    AUTHORIZATION_FILENAME,
    DATASET_MANIFEST_FILENAME,
    CONTROL_MANIFEST_NAME,
    CONTROL_RECEIPT_NAME,
}
observed_names = {
    path.name
    for path in OUTPUT_ROOT.iterdir()
    if path.is_file()
}
if observed_names != expected_names:
    raise RuntimeError("materialized control output file set drifted")

print(f"output_directory={OUTPUT_ROOT}")
print(f"file_count={len(observed_names)}")
print(f"remaining_minutes={remaining_minutes}")
print(f"control_manifest_sha256={file_sha256(control_manifest_path)}")
print("nested_archives_present=false")
print("runtime_execution_performed=false")
print("save_this_notebook_output=true")
"""
    replacements = {
        "__CONTROL_NOTEBOOK_NAME__": CONTROL_NOTEBOOK_NAME,
        "__CONTROL_OUTPUT_DIRECTORY_NAME__": CONTROL_OUTPUT_DIRECTORY_NAME,
        "__AUTHORIZATION_FILENAME_LITERAL__": _string_literal_block(AUTHORIZATION_FILENAME),
        "__DATASET_MANIFEST_FILENAME__": DATASET_MANIFEST_FILENAME,
        "__CONTROL_MANIFEST_NAME__": CONTROL_MANIFEST_NAME,
        "__CONTROL_RECEIPT_NAME__": CONTROL_RECEIPT_NAME,
        "__AUTHORIZATION_B64_LITERAL__": _string_literal_block(authorization_b64),
        "__DATASET_MANIFEST_B64_LITERAL__": _string_literal_block(manifest_b64),
        "__AUTHORIZATION_FILE_SHA256_LITERAL__": _string_literal_block(authorization_file_sha256),
        "__MANIFEST_FILE_SHA256_LITERAL__": _string_literal_block(manifest_file_sha256),
        "__AUTHORIZATION_CONTRACT_SHA256_LITERAL__": _string_literal_block(
            authorization_contract_sha256
        ),
        "__MANIFEST_CONTRACT_SHA256_LITERAL__": _string_literal_block(manifest_contract_sha256),
        "__SOURCE_MAIN_MERGE_COMMIT__": SOURCE_MAIN_MERGE_COMMIT,
        "__MINIMUM_CONTROL_WINDOW_MINUTES__": str(MINIMUM_CONTROL_WINDOW_MINUTES),
        "__HARNESS_SOURCE_PATH_LITERAL__": _string_literal_block(HARNESS_SOURCE_PATH),
        "__MODEL_SNAPSHOT_PATH_LITERAL__": _string_literal_block(MODEL_SNAPSHOT_PATH),
        "__RUNTIME_OUTPUT_DIRECTORY__": RUNTIME_OUTPUT_DIRECTORY,
        "__RUNTIME_RESOLUTION_LOCK_SHA256__": RUNTIME_RESOLUTION_LOCK_SHA256,
        "__RUNTIME_MANIFEST_SHA256__": RUNTIME_MANIFEST_SHA256,
        "__RUNTIME_SHA256_MANIFEST_SHA256__": RUNTIME_SHA256_MANIFEST_SHA256,
        "__RUNTIME_MATERIALIZATION_RECEIPT_SHA256__": (RUNTIME_MATERIALIZATION_RECEIPT_SHA256),
        "__RUNTIME_PACKAGE_COUNT__": str(RUNTIME_PACKAGE_COUNT),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    return template


def build_control_materializer_notebook(
    *,
    repo_root: Path,
) -> dict[str, object]:
    """Build one authorization-specific, flat-output control notebook."""

    repo_root = repo_root.resolve()
    try:
        import importlib

        issuance = importlib.import_module(
            "auragateway.local_abc."
            "full_abc_local_environment_qualification_execution_"
            "authorization_issuance"
        )
        execution_contracts = importlib.import_module(
            "auragateway.local_abc.full_abc_local_environment_qualification_execution_contracts"
        )
        QualificationDatasetManifest = execution_contracts.QualificationDatasetManifest
        QualificationExecutionAuthorization = (
            execution_contracts.QualificationExecutionAuthorization
        )
    except ImportError as exc:
        raise KaggleLauncherError(
            "CONTROL_MATERIALIZER_IMPORT_FAILED",
            "authorization contracts could not be imported",
        ) from exc

    verification = issuance.verify_authorization(repo_root=repo_root)
    authorization_path = repo_root / AUTHORIZATION_PATH
    manifest_path = repo_root / DATASET_MANIFEST_PATH
    authorization = QualificationExecutionAuthorization.model_validate(
        _load_json_object(authorization_path)
    )
    manifest = QualificationDatasetManifest.model_validate(_load_json_object(manifest_path))

    if verification.get("authorization_sha256") != authorization.fingerprint():
        raise KaggleLauncherError(
            "CONTROL_AUTHORIZATION_VERIFICATION_DRIFT",
            "authorization verification output drifted",
        )

    runtime_source = _control_materializer_source(
        authorization_bytes=authorization_path.read_bytes(),
        manifest_bytes=manifest_path.read_bytes(),
        authorization_contract_sha256=authorization.fingerprint(),
        manifest_contract_sha256=manifest.fingerprint(),
    )
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "control-introduction",
                "metadata": {},
                "source": [
                    "# AuraGateway qualification control materializer v1\n",
                    "\n",
                    "Materializes one short-lived authorization and its exact dataset "
                    "manifest into a flat notebook output. Accelerator None, Internet "
                    "Off, no secrets, Save Version -> Save & Run All.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "control-materializer",
                "metadata": {},
                "outputs": [],
                "source": runtime_source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "auragateway": {
                "authorization_sha256": authorization.fingerprint(),
                "control_output_directory": CONTROL_OUTPUT_DIRECTORY_NAME,
                "dataset_manifest_sha256": manifest.fingerprint(),
                "minimum_control_window_minutes": (MINIMUM_CONTROL_WINDOW_MINUTES),
                "notebook_name": CONTROL_NOTEBOOK_NAME,
                "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
            },
            "kaggle": {
                "accelerator": "none",
                "dataSources": [],
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_control_materializer_notebook(
    *,
    repo_root: Path,
    output_path: Path,
) -> KaggleNotebookVerification:
    """Write one authorization-specific control notebook."""

    notebook = build_control_materializer_notebook(repo_root=repo_root)
    payload = (
        json.dumps(
            notebook,
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    )
    _write_text_atomic(output_path, payload)
    metadata = cast(dict[str, object], notebook["metadata"])
    auragateway = cast(dict[str, object], metadata["auragateway"])
    return KaggleNotebookVerification(
        notebook_path=output_path.as_posix(),
        notebook_name=CONTROL_NOTEBOOK_NAME,
        notebook_sha256=_file_sha256(output_path),
        reviewed_core_sha256=cast(str, auragateway["authorization_sha256"]),
        cell_count=2,
        output_cells_present=False,
        execution_counts_present=False,
    )


def generate_committed_launcher(repo_root: Path) -> KaggleNotebookVerification:
    """Generate the repository-owned launcher at its canonical path."""

    return write_launcher_notebook(
        repo_root=repo_root,
        output_path=repo_root / LAUNCHER_NOTEBOOK_PATH,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-qualification-kaggle-launcher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_launcher = subparsers.add_parser("generate-launcher")
    generate_launcher.add_argument("--repo-root", type=Path, required=True)
    generate_launcher.add_argument("--output", type=Path)

    verify_launcher = subparsers.add_parser("verify-launcher")
    verify_launcher.add_argument("--repo-root", type=Path, required=True)
    verify_launcher.add_argument("--notebook", type=Path)

    generate_control = subparsers.add_parser("generate-control-materializer")
    generate_control.add_argument("--repo-root", type=Path, required=True)
    generate_control.add_argument("--output", type=Path, required=True)

    return parser


def _error_envelope(error: KaggleLauncherError) -> str:
    return KaggleLauncherErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).model_dump_json()


def main(argv: list[str] | None = None) -> int:
    """Generate or verify governed Kaggle notebooks."""

    try:
        arguments = _build_parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()

        if arguments.command == "generate-launcher":
            output = cast(Path | None, arguments.output)
            summary = write_launcher_notebook(
                repo_root=repo_root,
                output_path=(
                    output.resolve() if output is not None else repo_root / LAUNCHER_NOTEBOOK_PATH
                ),
            )
        elif arguments.command == "verify-launcher":
            notebook = cast(Path | None, arguments.notebook)
            summary = verify_launcher_notebook(
                repo_root=repo_root,
                notebook_path=(
                    notebook.resolve()
                    if notebook is not None
                    else repo_root / LAUNCHER_NOTEBOOK_PATH
                ),
            )
        else:
            summary = write_control_materializer_notebook(
                repo_root=repo_root,
                output_path=cast(Path, arguments.output).resolve(),
            )

        print(summary.model_dump_json())
        return 0
    except KaggleLauncherError as error:
        print(_error_envelope(error), file=__import__("sys").stderr)
        return 2
    except (OSError, ValidationError, ValueError) as error:
        envelope = KaggleLauncherErrorEnvelope(
            error_code="UNEXPECTED_KAGGLE_LAUNCHER_FAILURE",
            safe_message="Kaggle launcher failed at a typed boundary",
            details=(type(error).__name__,),
        )
        print(envelope.model_dump_json(), file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
