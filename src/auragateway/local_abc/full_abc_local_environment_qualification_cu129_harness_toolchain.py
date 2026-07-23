"""Prepare the deterministic current CUDA 12.9 harness rematerialization toolchain."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import subprocess
import tempfile
import textwrap
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Final, Never, cast

from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_harness_toolchain_contracts,
)

toolchain_contracts = full_abc_local_environment_qualification_cu129_harness_toolchain_contracts

REVIEW_MINIMUM_ANCESTOR: Final = "defe184d338b525e2f48104ef76e5d0d9a1329a8"
PACKAGE_ID: Final = "auragateway-cu129-current-harness-toolchain-v1"
SOURCE_BINDING_POLICY: Final = "POST_MERGE_CLEAN_MAIN_HEAD"
PYPROJECT_HISTORICAL_SHA256: Final = (
    "5387ea09341bde18d73518e28a236f65865918dd406fcb13824c0c8156a57103"
)
RUFF_CONFIG_SHA256: Final = "d891d61c5ce44d78f9a5313a46fd36406f54674ad742926bd44ebd11344538cd"
HISTORICAL_MATERIALIZER_NOTEBOOK_SHA256: Final = (
    "91f9ccc30883341af4cfd24d11c780ee136b9f7ccf9316b77b9d72ba559312c2"
)
RUFF_CONFIG_PATH: Final = "ruff.toml"
HISTORICAL_MATERIALIZER_NOTEBOOK_PATH: Final = (
    "evidence_vault/local_abc/harness-materializer-input-v3/ag-harness-materializer-input-v3.ipynb"
)
MATERIALIZATION_RECEIPT_NAME: Final = "ag_harness_materialization_receipt_cu129_v1.json"
MATERIALIZER_NOTEBOOK_NAME: Final = "ag-harness-materializer-cu129-v1"
MATERIALIZER_NOTEBOOK_FILENAME: Final = "ag_harness_materializer_cu129_v1.ipynb"
INSPECTION_NOTEBOOK_NAME: Final = "ag-harness-input-inspection-cu129-v1"
INSPECTION_NOTEBOOK_FILENAME: Final = "ag_harness_input_inspection_cu129_v1.ipynb"
INSPECTION_EVIDENCE_ZIP_NAME: Final = "ag-harness-input-inspection-cu129-v1.zip"
TOOLCHAIN_RECEIPT_NAME: Final = "toolchain_receipt.json"
SOURCE_RECEIPT_NAME: Final = "source_packaging_receipt.json"
SOURCE_INVENTORY_NAME: Final = "source_inventory.json"
SHA256_MANIFEST_NAME: Final = "sha256_manifest.json"

RUNTIME_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_wheelhouse_v1"
RUNTIME_PACKAGE_COUNT: Final = 176
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
MODEL_SNAPSHOT_SHA256: Final = "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa"
MODEL_SNAPSHOT_DIRECTORY_TOKEN: Final = (
    "auragateway-qwen2.5-0.5b-instruct-7ae557604adf67be50417f59c2c2f167def9a775"
)

HISTORICAL_HARNESS_DIRECTORY_SHA256: Final = (
    "4a371c80aef605c4f1ab5617c21ce43bd0939ad449ffcbcadab656878d785a2e"
)
HISTORICAL_HARNESS_OUTPUT_DIRECTORY: Final = "auragateway_qualification_harness_be1bfad_v1"
HISTORICAL_RUNTIME_ADAPTER_SHA256: Final = (
    "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"
)
CURRENT_RUNTIME_ADAPTER_SHA256: Final = (
    "aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"
)
CURRENT_CU129_RUNTIME_SHA256: Final = (
    "9230a4f06238b87c3b537f383aceda0de44c41c8c6b21c1d6b35666440a5445c"
)
CURRENT_EXECUTION_MODULE_SHA256: Final = (
    "7dcafa6c09982d2f01d3d3fed1f5fb4f564419e3ae70fa3cd1e7bdd10163aca4"
)
CURRENT_LAUNCHER_SOURCE_SHA256: Final = (
    "0c9b10bef8cb58c8139d4c0de5f299d75f1bc0a70b733742d1876fe4c3e30cdb"
)
CURRENT_LAUNCHER_NOTEBOOK_SHA256: Final = (
    "514d0a354e73319d7c6c42df501ed81386125c03ffee04cba7e2c269cabfe032"
)
CURRENT_EXECUTION_CONTRACTS_SHA256: Final = (
    "644e4013a753010bb1204e4bcc73e4e133a071ccc70213bca27dd24b74f8c0a0"
)
CURRENT_EXECUTION_REQUEST_SHA256: Final = (
    "7b0080429246f6def3c1ac28b8a677a2ed7e29ccf318690d9309ed98ff179ba0"
)
CURRENT_WORKER_PLAN_SHA256: Final = (
    "45bd37e50e663e514a3bac7b3ca22a678015dc5d5472f84bab3381123244262c"
)
CURRENT_REVIEWED_NOTEBOOK_SHA256: Final = (
    "89a0496e571d4e6f23dd1b4f6bc740c51e60699eda5c5df0a0894f0d49601db4"
)

EXECUTION_MODULE_PATH: Final = (
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution.py"
)
LAUNCHER_SOURCE_PATH: Final = (
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
)
LAUNCHER_NOTEBOOK_PATH: Final = (
    "notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb"
)
RUNTIME_ADAPTER_PATH: Final = (
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
EXECUTION_CONTRACTS_PATH: Final = (
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py"
)
CU129_RUNTIME_PATH: Final = (
    "src/auragateway/local_abc/full_abc_local_environment_qualification_cu129_runtime.py"
)
EXECUTION_REQUEST_PATH: Final = (
    "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
)
WORKER_PLAN_PATH: Final = (
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
OFFLINE_MANIFEST_PATH: Final = (
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
REVIEWED_NOTEBOOK_PATH: Final = "notebooks/auragateway_full_abc_environment_qualification_v1.ipynb"
REVIEW_RECORD_PATH: Final = (
    "benchmarks/local_abc/auragateway_cu129_current_harness_rematerialization_review_v1.json"
)
TOOLCHAIN_RECORD_PATH: Final = (
    "benchmarks/local_abc/auragateway_cu129_current_harness_toolchain_v1.json"
)

REQUIRED_PATHS: Final = (
    "pyproject.toml",
    "ruff.toml",
    "README.md",
    "src/auragateway/local_abc/contracts.py",
    "src/auragateway/local_abc/errors.py",
    EXECUTION_MODULE_PATH,
    EXECUTION_CONTRACTS_PATH,
    (
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_authorization_issuance.py"
    ),
    LAUNCHER_SOURCE_PATH,
    RUNTIME_ADAPTER_PATH,
    CU129_RUNTIME_PATH,
    (
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_cu129_harness_rematerialization_review.py"
    ),
    OFFLINE_MANIFEST_PATH,
    (
        "data/evals/benchmark/environment-qualification-v1/"
        "offline_dataset_materialization_record.json"
    ),
    EXECUTION_REQUEST_PATH,
    WORKER_PLAN_PATH,
    REVIEWED_NOTEBOOK_PATH,
    LAUNCHER_NOTEBOOK_PATH,
    REVIEW_RECORD_PATH,
    "benchmarks/local_abc/auragateway_cu129_current_harness_toolchain_v1.json",
    (
        "docs/reports/"
        "AuraGateway_CU129_Harness_Toolchain_Shared_Authority_Propagation_Reasoning_Certificate.md"
    ),
    (
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_cu129_harness_toolchain.py"
    ),
    (
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_cu129_harness_toolchain_contracts.py"
    ),
)

EXPECTED_FILE_SHA256: Final = {
    EXECUTION_MODULE_PATH: CURRENT_EXECUTION_MODULE_SHA256,
    LAUNCHER_SOURCE_PATH: CURRENT_LAUNCHER_SOURCE_SHA256,
    LAUNCHER_NOTEBOOK_PATH: CURRENT_LAUNCHER_NOTEBOOK_SHA256,
    RUNTIME_ADAPTER_PATH: CURRENT_RUNTIME_ADAPTER_SHA256,
    CU129_RUNTIME_PATH: CURRENT_CU129_RUNTIME_SHA256,
    EXECUTION_CONTRACTS_PATH: CURRENT_EXECUTION_CONTRACTS_SHA256,
    EXECUTION_REQUEST_PATH: CURRENT_EXECUTION_REQUEST_SHA256,
    WORKER_PLAN_PATH: CURRENT_WORKER_PLAN_SHA256,
    REVIEWED_NOTEBOOK_PATH: CURRENT_REVIEWED_NOTEBOOK_SHA256,
}

MAXIMUM_FILES: Final = 5_000
MAXIMUM_TOTAL_BYTES: Final = 100 * 1024 * 1024
ARCHIVE_SUFFIXES: Final = (
    ".zip",
    ".tar",
    ".tgz",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".whl",
)
ZIP_TIMESTAMP: Final = (1980, 1, 1, 0, 0, 0)


class HarnessToolchainError(RuntimeError):
    """Metadata-safe failure while packaging or generating the toolchain."""

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
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_ARGUMENT_INVALID",
            "harness toolchain arguments are invalid",
            details=(message,),
        )


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_FILE_UNREADABLE",
            "a toolchain file could not be read",
            path.as_posix(),
        ) from exc
    return digest.hexdigest()


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
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_WRITE_FAILED",
            "a toolchain output could not be written atomically",
            path.as_posix(),
        ) from exc


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
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
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_WRITE_FAILED",
            "a toolchain output could not be written atomically",
            path.as_posix(),
        ) from exc


def _run_git(
    repo_root: Path,
    arguments: Sequence[str],
    *,
    error_code: str,
) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_GIT_UNAVAILABLE",
            "Git could not be executed",
            repo_root.as_posix(),
        ) from exc
    if result.returncode != 0:
        details = tuple(
            line for line in result.stderr.decode("utf-8", errors="replace").splitlines() if line
        )
        raise HarnessToolchainError(
            error_code,
            "a required Git operation failed",
            repo_root.as_posix(),
            details=details[:10],
        )
    return result.stdout


def _git_text(
    repo_root: Path,
    arguments: Sequence[str],
    *,
    error_code: str,
) -> str:
    return _run_git(repo_root, arguments, error_code=error_code).decode("utf-8").strip()


def _validate_prepare_repository(repo_root: Path) -> str:
    """Return the exact clean post-merge main commit authorized for packaging."""

    if not (repo_root / ".git").exists():
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_GIT_CHECKOUT_REQUIRED",
            "a full Git checkout is required",
            repo_root.as_posix(),
        )
    branch = _git_text(
        repo_root,
        ("branch", "--show-current"),
        error_code="HARNESS_TOOLCHAIN_BRANCH_READ_FAILED",
    )
    if branch != "main":
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_MAIN_REQUIRED",
            "toolchain preparation requires branch main",
            details=(f"observed_branch={branch}",),
        )
    status = _git_text(
        repo_root,
        ("status", "--porcelain"),
        error_code="HARNESS_TOOLCHAIN_STATUS_READ_FAILED",
    )
    if status:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_CLEAN_TREE_REQUIRED",
            "toolchain preparation requires a clean working tree",
        )
    head = _git_text(
        repo_root,
        ("rev-parse", "HEAD^{commit}"),
        error_code="HARNESS_TOOLCHAIN_HEAD_READ_FAILED",
    )
    origin_main = _git_text(
        repo_root,
        ("rev-parse", "origin/main^{commit}"),
        error_code="HARNESS_TOOLCHAIN_ORIGIN_MAIN_READ_FAILED",
    )
    if head != origin_main:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_MAIN_NOT_SYNCED",
            "toolchain preparation requires HEAD to equal origin/main",
            details=(f"head={head}", f"origin_main={origin_main}"),
        )
    _run_git(
        repo_root,
        ("merge-base", "--is-ancestor", REVIEW_MINIMUM_ANCESTOR, head),
        error_code="HARNESS_TOOLCHAIN_REVIEW_ANCESTOR_MISSING",
    )
    if head == REVIEW_MINIMUM_ANCESTOR:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_POST_MERGE_SOURCE_REQUIRED",
            "the final harness source must advance beyond the review merge commit",
            details=(f"review_minimum_ancestor={REVIEW_MINIMUM_ANCESTOR}",),
        )
    return head


def default_build_spec(source_commit: str) -> toolchain_contracts.HarnessBuildSpec:
    """Return the deterministic package contract for one exact merged source commit."""

    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_SOURCE_COMMIT_INVALID",
            "the package source must be one lowercase 40-character Git commit id",
            details=(f"observed={source_commit}",),
        )
    source_token = source_commit[:7]
    return toolchain_contracts.HarnessBuildSpec(
        package_id=PACKAGE_ID,
        source_commit=source_commit,
        archive_name=f"ag-harness-{source_token}-v1.zip",
        input_dataset_name=f"ag-harness-{source_token}-v1-input",
        output_directory=f"auragateway_qualification_harness_{source_token}_v1",
        materialization_receipt_name=MATERIALIZATION_RECEIPT_NAME,
        required_paths=REQUIRED_PATHS,
        expected_file_sha256=dict(EXPECTED_FILE_SHA256),
        maximum_files=MAXIMUM_FILES,
        maximum_total_bytes=MAXIMUM_TOTAL_BYTES,
    )


def _parse_git_tree(raw: bytes) -> tuple[tuple[str, str, str], ...]:
    entries: list[tuple[str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            header, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id = header.decode("ascii").split(" ")
            path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_GIT_TREE_INVALID",
                "the source Git tree contains an unsupported entry",
            ) from exc
        if object_type != "blob":
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_NON_BLOB_REJECTED",
                "the source Git tree contains a non-blob entry",
                path,
                details=(f"mode={mode}", f"type={object_type}"),
            )
        if mode not in {"100644", "100755"}:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_NON_REGULAR_ENTRY_REJECTED",
                "the source Git tree contains a symlink or non-regular entry",
                path,
                details=(f"mode={mode}",),
            )
        normalized = PurePosixPath(path)
        if (
            normalized.is_absolute()
            or ".." in normalized.parts
            or "\\" in path
            or normalized.as_posix() != path
        ):
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_UNSAFE_PATH_REJECTED",
                "the source Git tree contains an unsafe path",
                path,
            )
        if path.lower().endswith(ARCHIVE_SUFFIXES):
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_NESTED_ARCHIVE_REJECTED",
                "the source Git tree contains a nested archive",
                path,
            )
        entries.append((mode, object_id, path))
    if not entries:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_SOURCE_EMPTY",
            "the source Git tree is empty",
        )
    ordered = tuple(sorted(entries, key=lambda item: item[2]))
    if len({path for _, _, path in ordered}) != len(ordered):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_DUPLICATE_PATH_REJECTED",
            "the source Git tree contains duplicate normalized paths",
        )
    return ordered


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _read_git_blobs(
    repo_root: Path,
    tree: Sequence[tuple[str, str, str]],
) -> dict[str, bytes]:
    object_ids = tuple(dict.fromkeys(object_id for _, object_id, _ in tree))
    request = b"".join(object_id.encode("ascii") + b"\n" for object_id in object_ids)
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "--batch"],
            input=request,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_GIT_UNAVAILABLE",
            "Git could not be executed",
            repo_root.as_posix(),
        ) from exc
    if result.returncode != 0:
        details = tuple(
            line for line in result.stderr.decode("utf-8", errors="replace").splitlines() if line
        )
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_BLOB_READ_FAILED",
            "exact Git blob bytes could not be read",
            repo_root.as_posix(),
            details=details[:10],
        )

    cursor = 0
    by_object_id: dict[str, bytes] = {}
    for expected_object_id in object_ids:
        newline = result.stdout.find(b"\n", cursor)
        if newline < 0:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_CAT_FILE_PROTOCOL_INVALID",
                "Git cat-file returned an incomplete object header",
            )
        try:
            header = result.stdout[cursor:newline].decode("ascii")
            observed_object_id, object_type, raw_size = header.split(" ")
            size = int(raw_size)
        except (UnicodeDecodeError, ValueError) as exc:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_CAT_FILE_PROTOCOL_INVALID",
                "Git cat-file returned an invalid object header",
            ) from exc
        if observed_object_id != expected_object_id or object_type != "blob" or size < 0:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_BLOB_AUTHORITY_DRIFT",
                "Git cat-file returned an unexpected object authority",
                details=(
                    f"expected_object_id={expected_object_id}",
                    f"observed_object_id={observed_object_id}",
                    f"observed_type={object_type}",
                ),
            )
        payload_start = newline + 1
        payload_end = payload_start + size
        separator_end = payload_end + 1
        if separator_end > len(result.stdout) or result.stdout[payload_end:separator_end] != b"\n":
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_CAT_FILE_PROTOCOL_INVALID",
                "Git cat-file returned an incomplete object payload",
                details=(f"object_id={expected_object_id}",),
            )
        payload = result.stdout[payload_start:payload_end]
        if _git_blob_sha1(payload) != expected_object_id:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_GIT_OBJECT_PAYLOAD_MISMATCH",
                "Git object payload did not match its blob authority",
                details=(f"object_id={expected_object_id}",),
            )
        by_object_id[expected_object_id] = payload
        cursor = separator_end
    if cursor != len(result.stdout):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_CAT_FILE_PROTOCOL_INVALID",
            "Git cat-file returned unexpected trailing bytes",
        )
    return {path: by_object_id[object_id] for _, object_id, path in tree}


def _inventory_identity(entries: Sequence[toolchain_contracts.HarnessSourceInventoryEntry]) -> str:
    payload = [
        {
            "path": entry.path,
            "sha256": entry.sha256,
            "size_bytes": entry.size_bytes,
        }
        for entry in entries
    ]
    return _sha256_bytes(_canonical_json(payload).encode("utf-8"))


def _validate_current_boundary(
    entries: Sequence[toolchain_contracts.HarnessSourceInventoryEntry],
    blobs: dict[str, bytes],
    spec: toolchain_contracts.HarnessBuildSpec,
) -> None:
    by_path = {entry.path: entry for entry in entries}
    missing = tuple(path for path in spec.required_paths if path not in by_path)
    if missing:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REQUIRED_PATH_MISSING",
            "the reviewed source commit is missing required harness files",
            details=missing,
        )
    for path, expected_sha256 in spec.expected_file_sha256.items():
        observed = by_path[path].sha256
        if observed != expected_sha256:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_REQUIRED_IDENTITY_DRIFT",
                "a reviewed source identity drifted",
                path,
                details=(f"expected={expected_sha256}", f"observed={observed}"),
            )

    adapter = blobs[RUNTIME_ADAPTER_PATH].decode("utf-8")
    contracts = blobs[EXECUTION_CONTRACTS_PATH].decode("utf-8")
    manifest = cast(dict[str, object], json.loads(blobs[OFFLINE_MANIFEST_PATH]))
    review = cast(dict[str, object], json.loads(blobs[REVIEW_RECORD_PATH]))

    if (
        'entries["vllm_runtime"]' not in adapter
        or 'entries["vllm_wheel"]' in adapter
        or "full_abc_local_environment_qualification_cu129_runtime" not in adapter
    ):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_CURRENT_ADAPTER_CONTRACT_MISSING",
            "the source runtime adapter does not expose the reviewed CUDA 12.9 boundary",
            RUNTIME_ADAPTER_PATH,
        )
    if "vllm_runtime" not in contracts or "python_wheelhouse_directory" not in contracts:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_CURRENT_CONTRACTS_MISSING",
            "the source execution contracts do not expose the current runtime role and format",
            EXECUTION_CONTRACTS_PATH,
        )
    if by_path[RUNTIME_ADAPTER_PATH].sha256 == HISTORICAL_RUNTIME_ADAPTER_SHA256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_HISTORICAL_ADAPTER_REJECTED",
            "the historical runtime adapter cannot be packaged as current",
            RUNTIME_ADAPTER_PATH,
        )

    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_MANIFEST_INVALID",
            "the source offline dataset manifest entry set is invalid",
            OFFLINE_MANIFEST_PATH,
        )
    role_entries: dict[str, dict[str, object]] = {}
    for item in raw_entries:
        if not isinstance(item, dict) or not isinstance(item.get("role"), str):
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_MANIFEST_INVALID",
                "the source offline dataset manifest contains an invalid entry",
                OFFLINE_MANIFEST_PATH,
            )
        role = cast(str, item["role"])
        if role in role_entries:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_MANIFEST_DUPLICATE_ROLE",
                "the source offline dataset manifest contains a duplicate role",
                OFFLINE_MANIFEST_PATH,
                details=(f"role={role}",),
            )
        role_entries[role] = cast(dict[str, object], item)
    runtime = role_entries.get("vllm_runtime")
    if runtime is None:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_RUNTIME_ENTRY_MISSING",
            "the source offline dataset manifest lacks the current runtime entry",
            OFFLINE_MANIFEST_PATH,
        )
    expected_runtime = {
        "artifact_format": "python_wheelhouse_directory",
        "package_count": RUNTIME_PACKAGE_COUNT,
        "resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
        "runtime_output_directory": RUNTIME_OUTPUT_DIRECTORY,
    }
    drift = tuple(
        f"{key}:expected={value}:observed={runtime.get(key)}"
        for key, value in expected_runtime.items()
        if runtime.get(key) != value
    )
    if drift:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_RUNTIME_ENTRY_DRIFT",
            "the source offline dataset manifest runtime entry drifted",
            OFFLINE_MANIFEST_PATH,
            details=drift,
        )
    if review.get("decision") != (
        "APPROVED_FOR_CURRENT_CU129_HARNESS_REMATERIALIZATION_IMPLEMENTATION"
    ):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REVIEW_DECISION_MISSING",
            "the source commit lacks the approved rematerialization review",
            REVIEW_RECORD_PATH,
        )
    safety = review.get("safety")
    if not isinstance(safety, dict) or safety.get("authorization_issued") is not False:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REVIEW_SAFETY_DRIFT",
            "the rematerialization review no longer keeps authorization blocked",
            REVIEW_RECORD_PATH,
        )


def _collect_source(
    repo_root: Path,
    spec: toolchain_contracts.HarnessBuildSpec,
) -> tuple[tuple[toolchain_contracts.HarnessSourceInventoryEntry, ...], dict[str, bytes]]:
    tree = _parse_git_tree(
        _run_git(
            repo_root,
            ("ls-tree", "-rz", "--full-tree", spec.source_commit),
            error_code="HARNESS_TOOLCHAIN_TREE_READ_FAILED",
        )
    )
    if len(tree) > spec.maximum_files:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_FILE_BUDGET_EXCEEDED",
            "the source Git tree exceeds the file-count budget",
            details=(f"observed={len(tree)}", f"maximum={spec.maximum_files}"),
        )

    payloads = _read_git_blobs(repo_root, tree)
    inventory: list[toolchain_contracts.HarnessSourceInventoryEntry] = []
    total_bytes = 0
    for mode, object_id, path in tree:
        payload = payloads[path]
        total_bytes += len(payload)
        if total_bytes > spec.maximum_total_bytes:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_BYTE_BUDGET_EXCEEDED",
                "the source Git tree exceeds the byte budget",
                details=(
                    f"observed_at_least={total_bytes}",
                    f"maximum={spec.maximum_total_bytes}",
                ),
            )
        inventory.append(
            toolchain_contracts.HarnessSourceInventoryEntry(
                path=path,
                git_blob_sha=object_id,
                sha256=_sha256_bytes(payload),
                size_bytes=len(payload),
                executable=mode == "100755",
            )
        )
    return tuple(inventory), payloads


def _build_archive_bytes(
    inventory: Sequence[toolchain_contracts.HarnessSourceInventoryEntry],
    path_payloads: dict[str, bytes],
) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
        temporary_path = Path(handle.name)
    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for entry in inventory:
                payload = path_payloads.get(entry.path)
                if payload is None:
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_BLOB_CACHE_MISSING",
                        "a source blob was not available for archive construction",
                        entry.path,
                    )
                info = zipfile.ZipInfo(entry.path, date_time=ZIP_TIMESTAMP)
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = 0o100755 if entry.executable else 0o100644
                info.external_attr = mode << 16
                archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        return temporary_path.read_bytes()
    finally:
        temporary_path.unlink(missing_ok=True)


def build_source_package(
    repo_root: Path,
    output_root: Path,
    spec: toolchain_contracts.HarnessBuildSpec,
    *,
    validate_current_boundary: bool,
) -> toolchain_contracts.HarnessSourcePackageReceipt:
    """Build one deterministic source archive from exact immutable Git blob bytes."""

    output_root.mkdir(parents=True, exist_ok=True)
    inventory, path_payloads = _collect_source(repo_root, spec)
    if validate_current_boundary:
        _validate_current_boundary(inventory, path_payloads, spec)

    archive_bytes = _build_archive_bytes(inventory, path_payloads)
    archive_bytes_second = _build_archive_bytes(inventory, path_payloads)
    if archive_bytes != archive_bytes_second:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_ARCHIVE_NONDETERMINISTIC",
            "two source archive builds from the same Git objects differed",
        )

    inventory_payload = [entry.model_dump(mode="json") for entry in inventory]
    inventory_json = _canonical_json(inventory_payload)
    directory_sha256 = _inventory_identity(inventory)
    total_bytes = sum(entry.size_bytes for entry in inventory)
    receipt = toolchain_contracts.HarnessSourcePackageReceipt(
        status="CURRENT_CU129_HARNESS_SOURCE_PACKAGED",
        package_id=spec.package_id,
        source_commit=spec.source_commit,
        archive_name=spec.archive_name,
        archive_sha256=_sha256_bytes(archive_bytes),
        inventory_sha256=_sha256_bytes(inventory_json.encode("utf-8")),
        output_directory=spec.output_directory,
        input_dataset_name=spec.input_dataset_name,
        materialization_receipt_name=spec.materialization_receipt_name,
        directory_sha256=directory_sha256,
        file_count=len(inventory),
        total_bytes=total_bytes,
        required_paths=spec.required_paths,
        expected_file_sha256=dict(spec.expected_file_sha256),
        safety=toolchain_contracts.HarnessToolchainSafety(),
    )
    receipt_json = receipt.canonical_json()
    sha_manifest = {
        spec.archive_name: receipt.archive_sha256,
        SOURCE_INVENTORY_NAME: receipt.inventory_sha256,
        SOURCE_RECEIPT_NAME: _sha256_bytes(receipt_json.encode("utf-8")),
    }

    _write_bytes_atomic(output_root / spec.archive_name, archive_bytes)
    _write_text_atomic(output_root / SOURCE_INVENTORY_NAME, inventory_json)
    _write_text_atomic(output_root / SOURCE_RECEIPT_NAME, receipt_json)
    _write_text_atomic(output_root / SHA256_MANIFEST_NAME, _canonical_json(sha_manifest))
    return receipt


def _notebook_payload(markdown: str, source: str) -> dict[str, object]:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": markdown.splitlines(keepends=True),
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _materializer_source(receipt: toolchain_contracts.HarnessSourcePackageReceipt) -> str:
    expected_receipt = receipt.model_dump(mode="json")
    receipt_json = receipt.canonical_json()
    expected_sha_manifest = {
        receipt.archive_name: receipt.archive_sha256,
        SOURCE_INVENTORY_NAME: receipt.inventory_sha256,
        SOURCE_RECEIPT_NAME: _sha256_bytes(receipt_json.encode("utf-8")),
    }
    expected_control_sha256 = {
        receipt.archive_name: receipt.archive_sha256,
        SOURCE_INVENTORY_NAME: receipt.inventory_sha256,
        SOURCE_RECEIPT_NAME: expected_sha_manifest[SOURCE_RECEIPT_NAME],
        SHA256_MANIFEST_NAME: _sha256_bytes(_canonical_json(expected_sha_manifest).encode("utf-8")),
    }
    return textwrap.dedent(
        f"""\
        from __future__ import annotations

        import hashlib
        import json
        import shutil
        import stat
        import zipfile
        from pathlib import Path, PurePosixPath

        NOTEBOOK_NAME = {MATERIALIZER_NOTEBOOK_NAME!r}
        DATASET_NAME = {receipt.input_dataset_name!r}
        DATASET_OWNER = "kabomolefe"
        INPUT_ROOT = Path("/kaggle/input").resolve()
        WORK_ROOT = Path("/kaggle/working").resolve()
        EXPECTED_ARCHIVE_NAME = {receipt.archive_name!r}
        EXPECTED_SOURCE_COMMIT = {receipt.source_commit!r}
        EXPECTED_DIRECTORY_SHA256 = {receipt.directory_sha256!r}
        EXPECTED_FILE_COUNT = {receipt.file_count}
        EXPECTED_TOTAL_BYTES = {receipt.total_bytes}
        EXPECTED_OUTPUT_DIRECTORY = {receipt.output_directory!r}
        EXPECTED_MATERIALIZATION_RECEIPT_NAME = {receipt.materialization_receipt_name!r}
        EXPECTED_DATASET_FILES = {tuple(expected_control_sha256)!r}
        EXPECTED_CONTROL_SHA256 = {expected_control_sha256!r}
        EXPECTED_SOURCE_RECEIPT = {expected_receipt!r}
        EXPECTED_SHA256_MANIFEST = {expected_sha_manifest!r}
        PRODUCER_OUTPUT_DIRECTORY = "ag_harness_materializer_cu129_v1_output"
        FINAL_BUNDLE_ROOT = WORK_ROOT / PRODUCER_OUTPUT_DIRECTORY
        STAGING_BUNDLE_ROOT = WORK_ROOT / ".ag_harness_materializer_cu129_v1_staging"
        STAGING_HARNESS_ROOT = STAGING_BUNDLE_ROOT / EXPECTED_OUTPUT_DIRECTORY
        STAGING_RECEIPT_PATH = (
            STAGING_BUNDLE_ROOT / EXPECTED_MATERIALIZATION_RECEIPT_NAME
        )
        MAXIMUM_FILES = {MAXIMUM_FILES}
        MAXIMUM_TOTAL_BYTES = {MAXIMUM_TOTAL_BYTES}
        ARCHIVE_SUFFIXES = {ARCHIVE_SUFFIXES!r}
        ZIP_TIMESTAMP = {ZIP_TIMESTAMP!r}


        def canonical_json(payload: object) -> str:
            return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


        def file_sha256(path: Path) -> str:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()


        def normalized_relative_path(value: str) -> PurePosixPath:
            path = PurePosixPath(value)
            if (
                path.is_absolute()
                or not path.parts
                or ".." in path.parts
                or "\\\\" in value
                or value.startswith("./")
                or path.as_posix() != value
            ):
                raise RuntimeError("source dataset contains an unsafe relative path")
            return path


        def resolve_dataset_root() -> Path:
            candidates = (
                INPUT_ROOT / DATASET_NAME,
                INPUT_ROOT / "datasets" / DATASET_OWNER / DATASET_NAME,
            )
            observed = tuple(
                candidate.resolve()
                for candidate in candidates
                if candidate.is_dir() and not candidate.is_symlink()
            )
            if len(observed) != 1:
                raise RuntimeError(
                    "expected exactly one attached harness source dataset "
                    f"but observed {{len(observed)}}"
                )
            dataset_root = observed[0]
            if INPUT_ROOT not in dataset_root.parents:
                raise RuntimeError("harness source dataset escaped /kaggle/input")
            return dataset_root


        def validate_dataset_controls(dataset_root: Path) -> tuple[Path, list[dict[str, object]]]:
            observed_names: list[str] = []
            for path in dataset_root.iterdir():
                if path.is_symlink():
                    raise RuntimeError("source dataset contains a symbolic link")
                metadata = path.stat()
                if not stat.S_ISREG(metadata.st_mode):
                    raise RuntimeError("source dataset contains a non-regular top-level member")
                observed_names.append(path.name)
            if tuple(sorted(observed_names)) != tuple(sorted(EXPECTED_DATASET_FILES)):
                raise RuntimeError("source dataset top-level file set drifted")
            for name, expected_sha256 in EXPECTED_CONTROL_SHA256.items():
                path = dataset_root / name
                if file_sha256(path) != expected_sha256:
                    raise RuntimeError(f"source dataset control identity drifted: {{name}}")

            source_receipt = json.loads(
                (dataset_root / "source_packaging_receipt.json").read_text(encoding="utf-8")
            )
            if source_receipt != EXPECTED_SOURCE_RECEIPT:
                raise RuntimeError("source packaging receipt contract drifted")
            sha_manifest = json.loads(
                (dataset_root / "sha256_manifest.json").read_text(encoding="utf-8")
            )
            if sha_manifest != EXPECTED_SHA256_MANIFEST:
                raise RuntimeError("source SHA-256 manifest contract drifted")
            raw_inventory = json.loads(
                (dataset_root / "source_inventory.json").read_text(encoding="utf-8")
            )
            if not isinstance(raw_inventory, list) or len(raw_inventory) != EXPECTED_FILE_COUNT:
                raise RuntimeError("source inventory shape or file count drifted")
            observed_inventory_paths = {{
                entry.get("path") for entry in raw_inventory if isinstance(entry, dict)
            }}
            if len(observed_inventory_paths) != len(raw_inventory):
                raise RuntimeError("source inventory contains duplicate paths")
            for entry in raw_inventory:
                if not isinstance(entry, dict):
                    raise RuntimeError("source inventory contains an invalid entry")
                normalized_relative_path(str(entry.get("path")))
                if not isinstance(entry.get("size_bytes"), int) or entry["size_bytes"] < 0:
                    raise RuntimeError("source inventory contains an invalid size")
                if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
                    raise RuntimeError("source inventory contains an invalid SHA-256")
                if (
                    not isinstance(entry.get("git_blob_sha"), str)
                    or len(entry["git_blob_sha"]) != 40
                ):
                    raise RuntimeError("source inventory contains an invalid Git blob id")
                if not isinstance(entry.get("executable"), bool):
                    raise RuntimeError("source inventory contains an invalid executable flag")
            return dataset_root / EXPECTED_ARCHIVE_NAME, raw_inventory


        def directory_identity(entries: list[dict[str, object]]) -> str:
            identity_entries = [
                {{
                    "path": entry["path"],
                    "sha256": entry["sha256"],
                    "size_bytes": entry["size_bytes"],
                }}
                for entry in entries
            ]
            return hashlib.sha256(canonical_json(identity_entries).encode("utf-8")).hexdigest()


        def validate_archive(
            archive_path: Path,
            inventory: list[dict[str, object]],
        ) -> tuple[zipfile.ZipInfo, ...]:
            expected_by_path = {{str(entry["path"]): entry for entry in inventory}}
            with zipfile.ZipFile(archive_path) as archive:
                members = tuple(archive.infolist())
                names = tuple(member.filename for member in members)
                if len(names) != len(set(names)):
                    raise RuntimeError("source archive contains duplicate members")
                if names != tuple(sorted(expected_by_path)):
                    raise RuntimeError("source archive member order or path set drifted")
                for member in members:
                    member_path = normalized_relative_path(member.filename)
                    if member.flag_bits & 0x1:
                        raise RuntimeError("source archive contains an encrypted member")
                    if member.is_dir():
                        raise RuntimeError("source archive contains an unexpected directory member")
                    unix_mode = member.external_attr >> 16
                    if stat.S_IFMT(unix_mode) != stat.S_IFREG:
                        raise RuntimeError("source archive contains a non-regular member")
                    expected = expected_by_path[member_path.as_posix()]
                    expected_mode = 0o100755 if expected["executable"] else 0o100644
                    if unix_mode != expected_mode:
                        raise RuntimeError("source archive member mode drifted")
                    if member.date_time != ZIP_TIMESTAMP:
                        raise RuntimeError("source archive member timestamp drifted")
                    if member.compress_type != zipfile.ZIP_DEFLATED:
                        raise RuntimeError("source archive compression method drifted")
                    if member.filename.lower().endswith(ARCHIVE_SUFFIXES):
                        raise RuntimeError("source archive contains a nested archive")
                    if member.file_size != expected["size_bytes"]:
                        raise RuntimeError("source archive member size drifted")
                    payload = archive.read(member)
                    if hashlib.sha256(payload).hexdigest() != expected["sha256"]:
                        raise RuntimeError("source archive member identity drifted")
                return members


        def extract_archive(
            archive_path: Path,
            inventory: list[dict[str, object]],
        ) -> None:
            expected_by_path = {{str(entry["path"]): entry for entry in inventory}}
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    relative_path = normalized_relative_path(member.filename)
                    destination = STAGING_HARNESS_ROOT.joinpath(*relative_path.parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member, "r") as source, destination.open("xb") as target:
                        shutil.copyfileobj(source, target, length=1024 * 1024)
                    expected = expected_by_path[relative_path.as_posix()]
                    destination.chmod(0o755 if expected["executable"] else 0o644)


        def inspect_materialized_tree() -> tuple[list[dict[str, object]], int]:
            entries: list[dict[str, object]] = []
            total_bytes = 0
            for path in sorted(STAGING_HARNESS_ROOT.rglob("*"), key=lambda item: item.as_posix()):
                if path.is_symlink():
                    raise RuntimeError("materialized harness contains a symbolic link")
                metadata = path.stat()
                if path.is_dir():
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    raise RuntimeError("materialized harness contains a non-regular member")
                relative_path = path.relative_to(STAGING_HARNESS_ROOT).as_posix()
                if relative_path.lower().endswith(ARCHIVE_SUFFIXES):
                    raise RuntimeError("materialized harness contains a nested archive")
                total_bytes += metadata.st_size
                if total_bytes > MAXIMUM_TOTAL_BYTES:
                    raise RuntimeError("materialized harness exceeds the byte budget")
                entries.append(
                    {{
                        "path": relative_path,
                        "sha256": file_sha256(path),
                        "size_bytes": metadata.st_size,
                    }}
                )
                if len(entries) > MAXIMUM_FILES:
                    raise RuntimeError("materialized harness exceeds the file-count budget")
            return entries, total_bytes


        def materialize() -> dict[str, object]:
            if FINAL_BUNDLE_ROOT.exists() or STAGING_BUNDLE_ROOT.exists():
                raise RuntimeError("materializer output or staging state already exists")
            dataset_root = resolve_dataset_root()
            archive_path, inventory = validate_dataset_controls(dataset_root)
            validate_archive(archive_path, inventory)
            STAGING_HARNESS_ROOT.mkdir(parents=True)
            completed = False
            try:
                extract_archive(archive_path, inventory)
                observed_entries, observed_total_bytes = inspect_materialized_tree()
                expected_entries = [
                    {{
                        "path": entry["path"],
                        "sha256": entry["sha256"],
                        "size_bytes": entry["size_bytes"],
                    }}
                    for entry in inventory
                ]
                if observed_entries != expected_entries:
                    raise RuntimeError("materialized harness inventory drifted")
                if len(observed_entries) != EXPECTED_FILE_COUNT:
                    raise RuntimeError("materialized harness file count drifted")
                if observed_total_bytes != EXPECTED_TOTAL_BYTES:
                    raise RuntimeError("materialized harness total bytes drifted")
                observed_directory_sha256 = directory_identity(observed_entries)
                if observed_directory_sha256 != EXPECTED_DIRECTORY_SHA256:
                    raise RuntimeError("materialized harness directory identity drifted")
                receipt = {{
                    "schema_version": "1.0.0",
                    "status": "CURRENT_CU129_HARNESS_MATERIALIZED",
                    "producer_notebook_name": NOTEBOOK_NAME,
                    "producer_output_directory": PRODUCER_OUTPUT_DIRECTORY,
                    "source_commit": EXPECTED_SOURCE_COMMIT,
                    "input_dataset_name": DATASET_NAME,
                    "input_mode": "exact_archive_with_control_files",
                    "archive_filename": EXPECTED_ARCHIVE_NAME,
                    "archive_sha256": EXPECTED_CONTROL_SHA256[EXPECTED_ARCHIVE_NAME],
                    "source_inventory_sha256": EXPECTED_CONTROL_SHA256["source_inventory.json"],
                    "source_receipt_sha256": EXPECTED_CONTROL_SHA256[
                        "source_packaging_receipt.json"
                    ],
                    "source_sha256_manifest_sha256": EXPECTED_CONTROL_SHA256[
                        "sha256_manifest.json"
                    ],
                    "output_directory": EXPECTED_OUTPUT_DIRECTORY,
                    "directory_sha256": observed_directory_sha256,
                    "file_count": len(observed_entries),
                    "total_bytes": observed_total_bytes,
                    "nested_archives_present": False,
                    "symlinks_present": False,
                    "network_access_performed": False,
                    "package_installation_performed": False,
                    "gpu_execution_performed": False,
                    "model_loaded": False,
                    "worker_started": False,
                    "model_requests_performed": 0,
                    "benchmark_trajectory_requests_performed": 0,
                    "authorization_issued": False,
                }}
                STAGING_RECEIPT_PATH.write_text(canonical_json(receipt), encoding="utf-8")
                STAGING_BUNDLE_ROOT.replace(FINAL_BUNDLE_ROOT)
                completed = True
                return receipt
            finally:
                if not completed and STAGING_BUNDLE_ROOT.exists():
                    shutil.rmtree(STAGING_BUNDLE_ROOT)


        if len(NOTEBOOK_NAME) > 50:
            raise RuntimeError("Kaggle notebook name exceeds 50 characters")
        result = materialize()
        print("status=CURRENT_CU129_HARNESS_MATERIALIZED")
        print(f"producer_output_directory={{PRODUCER_OUTPUT_DIRECTORY}}")
        print(f"output_directory={{EXPECTED_OUTPUT_DIRECTORY}}")
        print(f"file_count={{result['file_count']}}")
        print(f"total_bytes={{result['total_bytes']}}")
        print(f"directory_sha256={{result['directory_sha256']}}")
        print("gpu_execution_performed=false")
        print("package_installation_performed=false")
        print("model_requests_performed=0")
        print("authorization_issued=false")
        print("save_this_notebook_output=true")
        """
    )


def _inspection_source(receipt: toolchain_contracts.HarnessSourcePackageReceipt) -> str:
    return textwrap.dedent(
        f"""\
        from __future__ import annotations

        import hashlib
        import json
        import stat
        import zipfile
        from pathlib import Path, PurePosixPath

        NOTEBOOK_NAME = {INSPECTION_NOTEBOOK_NAME!r}
        INPUT_ROOT = Path("/kaggle/input").resolve()
        WORK_ROOT = Path("/kaggle/working").resolve()
        EXPECTED_SOURCE_COMMIT = {receipt.source_commit!r}
        EXPECTED_OUTPUT_DIRECTORY = {receipt.output_directory!r}
        EXPECTED_DIRECTORY_SHA256 = {receipt.directory_sha256!r}
        EXPECTED_FILE_COUNT = {receipt.file_count}
        EXPECTED_TOTAL_BYTES = {receipt.total_bytes}
        EXPECTED_MATERIALIZATION_RECEIPT_NAME = {receipt.materialization_receipt_name!r}
        EXPECTED_FILE_SHA256 = {receipt.expected_file_sha256!r}
        HISTORICAL_HARNESS_DIRECTORY_SHA256 = {HISTORICAL_HARNESS_DIRECTORY_SHA256!r}
        HISTORICAL_HARNESS_OUTPUT_DIRECTORY = {HISTORICAL_HARNESS_OUTPUT_DIRECTORY!r}
        HISTORICAL_RUNTIME_ADAPTER_SHA256 = {HISTORICAL_RUNTIME_ADAPTER_SHA256!r}
        CURRENT_RUNTIME_ADAPTER_SHA256 = {CURRENT_RUNTIME_ADAPTER_SHA256!r}
        RUNTIME_OUTPUT_DIRECTORY = {RUNTIME_OUTPUT_DIRECTORY!r}
        RUNTIME_PACKAGE_COUNT = {RUNTIME_PACKAGE_COUNT}
        RUNTIME_RESOLUTION_LOCK_SHA256 = {RUNTIME_RESOLUTION_LOCK_SHA256!r}
        RUNTIME_MANIFEST_SHA256 = {RUNTIME_MANIFEST_SHA256!r}
        RUNTIME_SHA256_MANIFEST_SHA256 = {RUNTIME_SHA256_MANIFEST_SHA256!r}
        RUNTIME_MATERIALIZATION_RECEIPT_SHA256 = {RUNTIME_MATERIALIZATION_RECEIPT_SHA256!r}
        MODEL_SNAPSHOT_SHA256 = {MODEL_SNAPSHOT_SHA256!r}
        MODEL_SNAPSHOT_DIRECTORY_TOKEN = {MODEL_SNAPSHOT_DIRECTORY_TOKEN!r}
        OFFLINE_MANIFEST_RELATIVE_PATH = {OFFLINE_MANIFEST_PATH!r}
        RUNTIME_ADAPTER_RELATIVE_PATH = {RUNTIME_ADAPTER_PATH!r}
        EXECUTION_CONTRACTS_RELATIVE_PATH = {EXECUTION_CONTRACTS_PATH!r}
        CU129_RUNTIME_RELATIVE_PATH = {CU129_RUNTIME_PATH!r}
        EVIDENCE_DIRECTORY = WORK_ROOT / "ag_harness_input_inspection_cu129_v1"
        EVIDENCE_ZIP_PATH = WORK_ROOT / {INSPECTION_EVIDENCE_ZIP_NAME!r}
        MAXIMUM_FILES = {MAXIMUM_FILES}
        MAXIMUM_TOTAL_BYTES = {MAXIMUM_TOTAL_BYTES}
        ARCHIVE_SUFFIXES = {ARCHIVE_SUFFIXES!r}


        def canonical_json(payload: object) -> str:
            return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


        def file_sha256(path: Path) -> str:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()


        def normalized_relative_path(value: str) -> PurePosixPath:
            path = PurePosixPath(value)
            if (
                path.is_absolute()
                or not path.parts
                or ".." in path.parts
                or "\\\\" in value
                or value.startswith("./")
                or path.as_posix() != value
            ):
                raise RuntimeError("consumed manifest contains an unsafe relative path")
            return path


        def write_record(name: str, payload: object) -> Path:
            path = EVIDENCE_DIRECTORY / name
            path.write_text(canonical_json(payload), encoding="utf-8")
            return path


        def finalize_evidence(records: tuple[Path, ...]) -> None:
            evidence_manifest = {{path.name: file_sha256(path) for path in records}}
            manifest_path = write_record("99_evidence_sha256.json", evidence_manifest)
            with zipfile.ZipFile(
                EVIDENCE_ZIP_PATH,
                "x",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as archive:
                for path in (*records, manifest_path):
                    info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, path.read_bytes(), compresslevel=9)


        def resolve_materializer_pair() -> tuple[Path, Path, Path]:
            pairs: list[tuple[Path, Path, Path]] = []
            for harness_root in INPUT_ROOT.rglob(EXPECTED_OUTPUT_DIRECTORY):
                if not harness_root.is_dir() or harness_root.is_symlink():
                    continue
                producer_root = harness_root.parent
                receipt_path = producer_root / EXPECTED_MATERIALIZATION_RECEIPT_NAME
                if receipt_path.is_file() and not receipt_path.is_symlink():
                    pairs.append(
                        (
                            producer_root.resolve(),
                            harness_root.resolve(),
                            receipt_path.resolve(),
                        )
                    )
            unique_pairs = tuple(dict.fromkeys(pairs))
            if len(unique_pairs) != 1:
                raise RuntimeError(
                    "expected exactly one materialized harness and sibling receipt producer pair"
                )
            producer_root, harness_root, receipt_path = unique_pairs[0]
            if INPUT_ROOT not in producer_root.parents:
                raise RuntimeError("materializer producer root escaped /kaggle/input")
            return producer_root, harness_root, receipt_path


        def resolve_exact_directory(name: str) -> Path:
            candidates = tuple(
                path.resolve()
                for path in INPUT_ROOT.rglob(name)
                if path.is_dir() and not path.is_symlink()
            )
            unique = tuple(dict.fromkeys(candidates))
            if len(unique) != 1:
                raise RuntimeError(f"expected exactly one attached directory named {{name}}")
            return unique[0]


        def inspect_harness(root: Path) -> tuple[list[dict[str, object]], int]:
            entries: list[dict[str, object]] = []
            total_bytes = 0
            for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
                if path.is_symlink():
                    raise RuntimeError("materialized harness contains a symbolic link")
                metadata = path.stat()
                if path.is_dir():
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    raise RuntimeError("materialized harness contains a non-regular member")
                relative_path = path.relative_to(root).as_posix()
                if relative_path.lower().endswith(ARCHIVE_SUFFIXES):
                    raise RuntimeError("materialized harness contains a nested archive")
                total_bytes += metadata.st_size
                if total_bytes > MAXIMUM_TOTAL_BYTES:
                    raise RuntimeError("materialized harness exceeds the byte budget")
                entries.append(
                    {{
                        "path": relative_path,
                        "sha256": file_sha256(path),
                        "size_bytes": metadata.st_size,
                    }}
                )
                if len(entries) > MAXIMUM_FILES:
                    raise RuntimeError("materialized harness exceeds the file-count budget")
            return entries, total_bytes


        def directory_identity(entries: list[dict[str, object]]) -> str:
            return hashlib.sha256(canonical_json(entries).encode("utf-8")).hexdigest()


        def manifest_entries_by_role(raw_entries: object) -> dict[str, dict[str, object]]:
            if not isinstance(raw_entries, list):
                raise RuntimeError("offline dataset manifest entry set is invalid")
            by_role: dict[str, dict[str, object]] = {{}}
            for entry in raw_entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("role"), str):
                    raise RuntimeError("offline dataset manifest contains an invalid entry")
                role = str(entry["role"])
                if role in by_role:
                    raise RuntimeError("offline dataset manifest contains a duplicate role")
                by_role[role] = entry
            if set(by_role) != {{"harness_source", "model_artifacts", "vllm_runtime"}}:
                raise RuntimeError("offline dataset manifest role set drifted")
            return by_role


        def validate_runtime_topology(runtime_root: Path) -> dict[str, object]:
            expected_topology = {{
                "requirements.in",
                "resolution_lock.json",
                "materialization.lock.txt",
                "requirements.lock.txt",
                "install_runtime.py",
                "runtime_manifest.json",
                "sha256_manifest.json",
                "materialization_receipt.json",
                "wheels",
            }}
            observed_topology = {{path.name for path in runtime_root.iterdir()}}
            if observed_topology != expected_topology:
                raise RuntimeError("attached CUDA 12.9 runtime top-level topology drifted")
            for path in runtime_root.iterdir():
                if path.is_symlink():
                    raise RuntimeError("attached CUDA 12.9 runtime contains a symbolic link")

            control_identities = {{
                "resolution_lock.json": RUNTIME_RESOLUTION_LOCK_SHA256,
                "runtime_manifest.json": RUNTIME_MANIFEST_SHA256,
                "sha256_manifest.json": RUNTIME_SHA256_MANIFEST_SHA256,
                "materialization_receipt.json": RUNTIME_MATERIALIZATION_RECEIPT_SHA256,
            }}
            for name, expected_sha256 in control_identities.items():
                path = runtime_root / name
                if not path.is_file() or file_sha256(path) != expected_sha256:
                    raise RuntimeError("attached CUDA 12.9 runtime control identity drifted")

            sha_manifest = json.loads(
                (runtime_root / "sha256_manifest.json").read_text(encoding="utf-8")
            )
            raw_entries = sha_manifest.get("entries")
            if not isinstance(raw_entries, list) or len(raw_entries) != 182:
                raise RuntimeError("runtime SHA-256 manifest entry count drifted")
            by_path: dict[str, dict[str, object]] = {{}}
            for entry in raw_entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                    raise RuntimeError("runtime SHA-256 manifest contains an invalid entry")
                relative_path = normalized_relative_path(str(entry["path"])).as_posix()
                if relative_path in by_path:
                    raise RuntimeError("runtime SHA-256 manifest contains duplicate paths")
                if not isinstance(entry.get("size_bytes"), int) or entry["size_bytes"] < 0:
                    raise RuntimeError("runtime SHA-256 manifest contains an invalid size")
                if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
                    raise RuntimeError("runtime SHA-256 manifest contains an invalid digest")
                by_path[relative_path] = entry

            wheel_entries = {{
                path: entry for path, entry in by_path.items() if path.startswith("wheels/")
            }}
            control_entries = {{
                path: entry for path, entry in by_path.items() if not path.startswith("wheels/")
            }}
            if len(wheel_entries) != RUNTIME_PACKAGE_COUNT:
                raise RuntimeError("runtime wheel manifest package count drifted")
            expected_control_entries = {{
                "requirements.in",
                "resolution_lock.json",
                "materialization.lock.txt",
                "requirements.lock.txt",
                "install_runtime.py",
                "runtime_manifest.json",
            }}
            if set(control_entries) != expected_control_entries:
                raise RuntimeError("runtime control manifest path set drifted")
            for relative_path, entry in control_entries.items():
                path = runtime_root / relative_path
                if not path.is_file() or path.is_symlink():
                    raise RuntimeError("runtime control file is missing or non-regular")
                if path.stat().st_size != entry["size_bytes"]:
                    raise RuntimeError("runtime control file size drifted")
                if file_sha256(path) != entry["sha256"]:
                    raise RuntimeError("runtime control file identity drifted")

            wheels_root = runtime_root / "wheels"
            if not wheels_root.is_dir() or wheels_root.is_symlink():
                raise RuntimeError("runtime wheels directory is missing or symbolic")
            actual_wheels = tuple(sorted(wheels_root.iterdir(), key=lambda item: item.name))
            if len(actual_wheels) != RUNTIME_PACKAGE_COUNT:
                raise RuntimeError("runtime wheel directory package count drifted")
            if any(
                path.is_symlink() or not path.is_file() or path.suffix != ".whl"
                for path in actual_wheels
            ):
                raise RuntimeError("runtime wheel directory contains an invalid member")
            actual_names = {{f"wheels/{{path.name}}" for path in actual_wheels}}
            if actual_names != set(wheel_entries):
                raise RuntimeError("runtime wheel filenames drifted from the consumed manifest")
            for path in actual_wheels:
                entry = wheel_entries[f"wheels/{{path.name}}"]
                if path.stat().st_size != entry["size_bytes"]:
                    raise RuntimeError("runtime wheel size drifted from the consumed manifest")

            runtime_manifest = json.loads(
                (runtime_root / "runtime_manifest.json").read_text(encoding="utf-8")
            )
            if (
                runtime_manifest.get("package_count") != RUNTIME_PACKAGE_COUNT
                or runtime_manifest.get("resolution_lock_sha256")
                != RUNTIME_RESOLUTION_LOCK_SHA256
            ):
                raise RuntimeError("runtime manifest authority drifted")
            materialization_receipt = json.loads(
                (runtime_root / "materialization_receipt.json").read_text(encoding="utf-8")
            )
            if (
                materialization_receipt.get("materialization_status") != "PASSED"
                or materialization_receipt.get("package_count") != RUNTIME_PACKAGE_COUNT
                or materialization_receipt.get("resolution_lock_sha256")
                != RUNTIME_RESOLUTION_LOCK_SHA256
                or materialization_receipt.get("model_requests_performed") != 0
            ):
                raise RuntimeError("runtime materialization receipt authority drifted")
            return {{
                "runtime_root_name": runtime_root.name,
                "package_count": len(actual_wheels),
                "manifest_entry_count": len(raw_entries),
                "wheel_bytes_verified_by_manifest_size": sum(
                    int(entry["size_bytes"]) for entry in wheel_entries.values()
                ),
                "wheel_payloads_rehashed": False,
            }}


        def run_inspection() -> tuple[dict[str, object], ...]:
            producer_root, harness_root, receipt_path = resolve_materializer_pair()
            runtime_root = resolve_exact_directory(RUNTIME_OUTPUT_DIRECTORY)
            model_root = resolve_exact_directory(MODEL_SNAPSHOT_DIRECTORY_TOKEN)

            inventory, total_bytes = inspect_harness(harness_root)
            observed_directory_sha256 = directory_identity(inventory)
            if len(inventory) != EXPECTED_FILE_COUNT:
                raise RuntimeError("materialized harness file count drifted")
            if total_bytes != EXPECTED_TOTAL_BYTES:
                raise RuntimeError("materialized harness total bytes drifted")
            if observed_directory_sha256 != EXPECTED_DIRECTORY_SHA256:
                raise RuntimeError("materialized harness directory identity drifted")
            key_identity_drift = tuple(
                relative_path
                for relative_path, expected_sha256 in EXPECTED_FILE_SHA256.items()
                if not (harness_root / relative_path).is_file()
                or file_sha256(harness_root / relative_path) != expected_sha256
            )
            if key_identity_drift:
                raise RuntimeError("materialized harness key source identities drifted")

            materialization_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            expected_receipt_values = {{
                "status": "CURRENT_CU129_HARNESS_MATERIALIZED",
                "producer_notebook_name": {MATERIALIZER_NOTEBOOK_NAME!r},
                "source_commit": EXPECTED_SOURCE_COMMIT,
                "output_directory": EXPECTED_OUTPUT_DIRECTORY,
                "directory_sha256": EXPECTED_DIRECTORY_SHA256,
                "file_count": EXPECTED_FILE_COUNT,
                "total_bytes": EXPECTED_TOTAL_BYTES,
                "authorization_issued": False,
                "model_requests_performed": 0,
            }}
            if any(
                materialization_receipt.get(key) != value
                for key, value in expected_receipt_values.items()
            ):
                raise RuntimeError("materialization receipt contract drifted")

            manifest = json.loads(
                (harness_root / OFFLINE_MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
            )
            by_role = manifest_entries_by_role(manifest.get("entries"))
            historical_harness = by_role["harness_source"]
            historical_mount = str(historical_harness.get("mounted_path"))
            if (
                historical_harness.get("artifact_format") != "source_tree_directory"
                or historical_harness.get("sha256") != HISTORICAL_HARNESS_DIRECTORY_SHA256
                or not historical_mount.endswith(f"/{{HISTORICAL_HARNESS_OUTPUT_DIRECTORY}}")
            ):
                raise RuntimeError(
                    "active manifest was prematurely migrated from historical harness"
                )

            runtime_entry = by_role["vllm_runtime"]
            expected_runtime = {{
                "artifact_format": "python_wheelhouse_directory",
                "package_count": RUNTIME_PACKAGE_COUNT,
                "resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
                "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
                "sha256_manifest_sha256": RUNTIME_SHA256_MANIFEST_SHA256,
                "materialization_receipt_sha256": RUNTIME_MATERIALIZATION_RECEIPT_SHA256,
                "runtime_output_directory": RUNTIME_OUTPUT_DIRECTORY,
            }}
            if any(runtime_entry.get(key) != value for key, value in expected_runtime.items()):
                raise RuntimeError("offline dataset manifest runtime authority drifted")
            model_entry = by_role["model_artifacts"]
            if model_entry.get("sha256") != MODEL_SNAPSHOT_SHA256:
                raise RuntimeError("offline dataset manifest model authority drifted")

            runtime_topology = validate_runtime_topology(runtime_root)
            compiled_paths = (
                RUNTIME_ADAPTER_RELATIVE_PATH,
                EXECUTION_CONTRACTS_RELATIVE_PATH,
                CU129_RUNTIME_RELATIVE_PATH,
            )
            for relative_path in compiled_paths:
                source = (harness_root / relative_path).read_text(encoding="utf-8")
                compile(source, relative_path, "exec")
            observed_adapter_sha256 = file_sha256(
                harness_root / RUNTIME_ADAPTER_RELATIVE_PATH
            )
            if observed_adapter_sha256 != CURRENT_RUNTIME_ADAPTER_SHA256:
                raise RuntimeError("current runtime adapter identity drifted")
            if observed_adapter_sha256 == HISTORICAL_RUNTIME_ADAPTER_SHA256:
                raise RuntimeError("historical runtime adapter resolved as current")

            harness_record = {{
                "status": "CURRENT_CU129_HARNESS_INPUT_VALIDATED",
                "producer_root_name": producer_root.name,
                "source_commit": EXPECTED_SOURCE_COMMIT,
                "directory_sha256": observed_directory_sha256,
                "file_count": len(inventory),
                "total_bytes": total_bytes,
                "current_runtime_adapter_sha256": observed_adapter_sha256,
                "expected_current_runtime_adapter_sha256": CURRENT_RUNTIME_ADAPTER_SHA256,
                "historical_runtime_adapter_sha256": HISTORICAL_RUNTIME_ADAPTER_SHA256,
                "historical_adapter_resolved": False,
            }}
            runtime_record = {{
                "status": "CURRENT_CU129_RUNTIME_AND_MODEL_INPUTS_VALIDATED",
                **runtime_topology,
                "runtime_resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
                "model_snapshot_root_name": model_root.name,
                "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
                "model_weights_loaded": False,
            }}
            source_boundary_record = {{
                "status": "CURRENT_CU129_SOURCE_BOUNDARY_VALIDATED",
                "compiled_source_files": compiled_paths,
                "active_harness_binding_status": (
                    "HISTORICAL_PENDING_EVIDENCE_INTEGRATION"
                ),
                "historical_harness_directory_sha256": (
                    HISTORICAL_HARNESS_DIRECTORY_SHA256
                ),
                "historical_harness_output_directory": (
                    HISTORICAL_HARNESS_OUTPUT_DIRECTORY
                ),
                "authorization_issued": False,
                "package_installation_performed": False,
                "gpu_execution_performed": False,
                "model_loaded": False,
                "worker_started": False,
                "model_requests_performed": 0,
            }}
            summary = {{
                "schema_version": "1.0.0",
                "inspection_status": "CURRENT_CU129_HARNESS_INPUT_INSPECTION_PASSED",
                "operational_input_closure": "PASSED",
                "source_commit": EXPECTED_SOURCE_COMMIT,
                "harness_directory_sha256": observed_directory_sha256,
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
            }}
            return harness_record, runtime_record, source_boundary_record, summary


        if len(NOTEBOOK_NAME) > 50:
            raise RuntimeError("Kaggle notebook name exceeds 50 characters")
        if EVIDENCE_DIRECTORY.exists() or EVIDENCE_ZIP_PATH.exists():
            raise RuntimeError("inspection evidence output already exists")
        EVIDENCE_DIRECTORY.mkdir(parents=False)
        expected_failures = (
            RuntimeError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
            SyntaxError,
        )
        try:
            payloads = run_inspection()
        except expected_failures as exc:
            failure = {{
                "schema_version": "1.0.0",
                "inspection_status": "FAILED",
                "failure_class": "METADATA_INPUT_INSPECTION_FAILED",
                "error_type": type(exc).__name__,
                "safe_message": str(exc)[:500],
                "source_commit": EXPECTED_SOURCE_COMMIT,
                "network_access_performed": False,
                "gpu_execution_performed": False,
                "package_installation_performed": False,
                "model_loaded": False,
                "tokenizer_loaded": False,
                "worker_started": False,
                "model_requests_performed": 0,
                "authorization_issued": False,
            }}
            failure_path = write_record("90_failure.json", failure)
            finalize_evidence((failure_path,))
            print("inspection_status=FAILED")
            print("failure_class=METADATA_INPUT_INSPECTION_FAILED")
            print(f"error_type={{type(exc).__name__}}")
            print("gpu_execution_performed=false")
            print("package_installation_performed=false")
            print("model_requests_performed=0")
            print("authorization_issued=false")
            print(f"evidence_zip={{EVIDENCE_ZIP_PATH}}")
            raise
        else:
            names = (
                "00_harness_input.json",
                "10_runtime_and_model_inputs.json",
                "20_source_boundary.json",
                "90_summary.json",
            )
            records = tuple(write_record(name, payload) for name, payload in zip(names, payloads))
            finalize_evidence(records)
            summary = payloads[-1]
            print("inspection_status=CURRENT_CU129_HARNESS_INPUT_INSPECTION_PASSED")
            print("operational_input_closure=PASSED")
            print(f"source_commit={{EXPECTED_SOURCE_COMMIT}}")
            print(f"harness_directory_sha256={{summary['harness_directory_sha256']}}")
            print(f"runtime_package_count={{RUNTIME_PACKAGE_COUNT}}")
            print("gpu_execution_performed=false")
            print("package_installation_performed=false")
            print("model_requests_performed=0")
            print("authorization_issued=false")
            print(f"evidence_zip={{EVIDENCE_ZIP_PATH}}")
            print("save_this_notebook_output=true")
        """
    )


def _validate_generated_notebook(
    payload: dict[str, object],
    *,
    notebook_name: str,
    filename: str,
) -> toolchain_contracts.GeneratedNotebookReceipt:
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_NOTEBOOK_SHAPE_INVALID",
            "a generated notebook must contain one markdown and one code cell",
            filename,
        )
    markdown, code = cells
    if not isinstance(markdown, dict) or not isinstance(code, dict):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_NOTEBOOK_CELL_INVALID",
            "a generated notebook contains an invalid cell",
            filename,
        )
    if markdown.get("cell_type") != "markdown" or code.get("cell_type") != "code":
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_NOTEBOOK_CELL_ORDER_INVALID",
            "a generated notebook cell order is invalid",
            filename,
        )
    if code.get("execution_count") is not None or code.get("outputs") != []:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_NOTEBOOK_EXECUTION_STATE_PRESENT",
            "a generated notebook contains execution state",
            filename,
        )
    source_value = code.get("source")
    if not isinstance(source_value, list) or not all(
        isinstance(item, str) for item in source_value
    ):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_NOTEBOOK_SOURCE_INVALID",
            "a generated notebook code source is invalid",
            filename,
        )
    source = "".join(cast(list[str], source_value))
    compile(source, filename, "exec")
    prohibited = (
        "requests.",
        "urllib.request",
        "pip install",
        "torch.cuda",
        "AutoModel",
        "AutoTokenizer",
        "execute_from_environment()",
        "except Exception",
    )
    observed = tuple(token for token in prohibited if token in source)
    if observed:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_NOTEBOOK_PROHIBITED_ACTIVITY",
            "a generated notebook contains prohibited operational activity",
            filename,
            details=observed,
        )
    encoded = (_canonical_json(payload) + "\n").encode("utf-8")
    return toolchain_contracts.GeneratedNotebookReceipt(
        notebook_name=notebook_name,
        filename=filename,
        sha256=_sha256_bytes(encoded),
        cell_count=2,
    )


def generate_notebooks(
    receipt: toolchain_contracts.HarnessSourcePackageReceipt,
    output_root: Path,
) -> tuple[
    toolchain_contracts.GeneratedNotebookReceipt,
    toolchain_contracts.GeneratedNotebookReceipt,
]:
    """Generate exact unexecuted materializer and metadata-inspection notebooks."""

    materializer_payload = _notebook_payload(
        "# AuraGateway current CUDA 12.9 harness materializer\n\n"
        "Attach exactly one reviewed source input. Use Accelerator None, Internet Off, "
        "no secrets, and Save Version -> Save & Run All.\n",
        _materializer_source(receipt),
    )
    inspection_payload = _notebook_payload(
        "# AuraGateway current CUDA 12.9 harness input inspection\n\n"
        "Attach the successful materializer output, the exact 176-package CUDA 12.9 "
        "wheelhouse output, and the unchanged model snapshot. Use Accelerator None, "
        "Internet Off, no secrets, and Save Version -> Save & Run All.\n",
        _inspection_source(receipt),
    )
    materializer_receipt = _validate_generated_notebook(
        materializer_payload,
        notebook_name=MATERIALIZER_NOTEBOOK_NAME,
        filename=MATERIALIZER_NOTEBOOK_FILENAME,
    )
    inspection_receipt = _validate_generated_notebook(
        inspection_payload,
        notebook_name=INSPECTION_NOTEBOOK_NAME,
        filename=INSPECTION_NOTEBOOK_FILENAME,
    )
    _write_text_atomic(
        output_root / MATERIALIZER_NOTEBOOK_FILENAME,
        _canonical_json(materializer_payload) + "\n",
    )
    _write_text_atomic(
        output_root / INSPECTION_NOTEBOOK_FILENAME,
        _canonical_json(inspection_payload) + "\n",
    )
    return materializer_receipt, inspection_receipt


def load_source_receipt(path: Path) -> toolchain_contracts.HarnessSourcePackageReceipt:
    """Load and validate one source package receipt."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_RECEIPT_MISSING",
            "the source package receipt is missing",
            path.as_posix(),
        ) from exc
    except json.JSONDecodeError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_RECEIPT_JSON_INVALID",
            "the source package receipt is invalid JSON",
            path.as_posix(),
        ) from exc
    try:
        return toolchain_contracts.HarnessSourcePackageReceipt.model_validate(payload)
    except ValidationError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_RECEIPT_CONTRACT_INVALID",
            "the source package receipt violates its typed contract",
            path.as_posix(),
            details=tuple(str(error) for error in exc.errors())[:10],
        ) from exc


def _load_json_file(path: Path, *, error_code: str, safe_message: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise HarnessToolchainError(
            error_code,
            safe_message,
            path.as_posix(),
        ) from exc
    except json.JSONDecodeError as exc:
        raise HarnessToolchainError(
            error_code,
            safe_message,
            path.as_posix(),
        ) from exc


def _load_inventory(path: Path) -> tuple[toolchain_contracts.HarnessSourceInventoryEntry, ...]:
    raw_inventory = _load_json_file(
        path,
        error_code="HARNESS_TOOLCHAIN_INVENTORY_INVALID",
        safe_message="the source inventory is missing or invalid",
    )
    if not isinstance(raw_inventory, list):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_INVENTORY_ROOT_INVALID",
            "the source inventory must contain one JSON array",
            path.as_posix(),
        )
    try:
        inventory = tuple(
            toolchain_contracts.HarnessSourceInventoryEntry.model_validate(item)
            for item in raw_inventory
        )
    except ValidationError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_INVENTORY_CONTRACT_INVALID",
            "the source inventory violates its typed contract",
            path.as_posix(),
            details=tuple(str(error) for error in exc.errors())[:10],
        ) from exc
    paths = tuple(entry.path for entry in inventory)
    if paths != tuple(sorted(paths)):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_INVENTORY_ORDER_DRIFT",
            "the source inventory path order is not canonical",
            path.as_posix(),
        )
    if len(paths) != len(set(paths)):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_INVENTORY_DUPLICATE_PATH",
            "the source inventory contains duplicate paths",
            path.as_posix(),
        )
    return inventory


def _validate_archive_against_inventory(
    archive_path: Path,
    inventory: Sequence[toolchain_contracts.HarnessSourceInventoryEntry],
) -> None:
    by_path = {entry.path: entry for entry in inventory}
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = tuple(archive.infolist())
            names = tuple(member.filename for member in members)
            if len(names) != len(set(names)):
                raise HarnessToolchainError(
                    "HARNESS_TOOLCHAIN_ARCHIVE_DUPLICATE_MEMBER",
                    "the source archive contains duplicate members",
                    archive_path.as_posix(),
                )
            if names != tuple(sorted(by_path)):
                raise HarnessToolchainError(
                    "HARNESS_TOOLCHAIN_ARCHIVE_MEMBER_SET_DRIFT",
                    "the source archive member order or path set drifted",
                    archive_path.as_posix(),
                )
            for member in members:
                path = PurePosixPath(member.filename)
                if (
                    path.is_absolute()
                    or not path.parts
                    or ".." in path.parts
                    or "\\" in member.filename
                    or path.as_posix() != member.filename
                ):
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_ARCHIVE_UNSAFE_MEMBER",
                        "the source archive contains an unsafe member path",
                        member.filename,
                    )
                if member.flag_bits & 0x1:
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_ARCHIVE_ENCRYPTED_MEMBER_REJECTED",
                        "the source archive contains an encrypted member",
                        member.filename,
                    )
                if member.is_dir():
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_ARCHIVE_DIRECTORY_MEMBER_REJECTED",
                        "the source archive contains an unexpected directory member",
                        member.filename,
                    )
                if member.filename.lower().endswith(ARCHIVE_SUFFIXES):
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_NESTED_ARCHIVE_REJECTED",
                        "the source archive contains a nested archive",
                        member.filename,
                    )
                entry = by_path[member.filename]
                unix_mode = member.external_attr >> 16
                expected_mode = 0o100755 if entry.executable else 0o100644
                if stat.S_IFMT(unix_mode) != stat.S_IFREG or unix_mode != expected_mode:
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_ARCHIVE_MEMBER_MODE_DRIFT",
                        "a source archive member mode drifted",
                        member.filename,
                    )
                if member.date_time != ZIP_TIMESTAMP:
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_ARCHIVE_TIMESTAMP_DRIFT",
                        "a source archive member timestamp drifted",
                        member.filename,
                    )
                if member.compress_type != zipfile.ZIP_DEFLATED:
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_ARCHIVE_COMPRESSION_DRIFT",
                        "a source archive member compression method drifted",
                        member.filename,
                    )
                payload = archive.read(member)
                if len(payload) != entry.size_bytes or _sha256_bytes(payload) != entry.sha256:
                    raise HarnessToolchainError(
                        "HARNESS_TOOLCHAIN_ARCHIVE_MEMBER_IDENTITY_DRIFT",
                        "a source archive member identity drifted",
                        member.filename,
                    )
    except zipfile.BadZipFile as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_ARCHIVE_INVALID",
            "the source archive is not a valid ZIP file",
            archive_path.as_posix(),
        ) from exc


def verify_source_package(toolchain_root: Path) -> dict[str, object]:
    """Verify the exact four-file source dataset contract and archive contents."""

    archive_path_candidates = tuple(toolchain_root.glob("*.zip"))
    receipt_path = toolchain_root / SOURCE_RECEIPT_NAME
    receipt = load_source_receipt(receipt_path)
    archive_path = toolchain_root / receipt.archive_name
    inventory_path = toolchain_root / receipt.inventory_name
    sha_manifest_path = toolchain_root / receipt.sha256_manifest_name
    if archive_path_candidates != (archive_path,):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_SOURCE_ARCHIVE_SET_DRIFT",
            "the prepared source dataset must contain exactly one expected ZIP archive",
            toolchain_root.as_posix(),
        )
    if _file_sha256(archive_path) != receipt.archive_sha256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_ARCHIVE_IDENTITY_DRIFT",
            "the source archive identity drifted",
            archive_path.as_posix(),
        )

    inventory = _load_inventory(inventory_path)
    inventory_json = _canonical_json([entry.model_dump(mode="json") for entry in inventory])
    if _sha256_bytes(inventory_json.encode("utf-8")) != receipt.inventory_sha256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_INVENTORY_IDENTITY_DRIFT",
            "the source inventory identity drifted",
            inventory_path.as_posix(),
        )
    if len(inventory) != receipt.file_count:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_INVENTORY_COUNT_DRIFT",
            "the source inventory file count drifted",
            inventory_path.as_posix(),
        )
    if sum(entry.size_bytes for entry in inventory) != receipt.total_bytes:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_INVENTORY_BYTES_DRIFT",
            "the source inventory total bytes drifted",
            inventory_path.as_posix(),
        )
    if _inventory_identity(inventory) != receipt.directory_sha256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_DIRECTORY_IDENTITY_DRIFT",
            "the source directory identity drifted",
            inventory_path.as_posix(),
        )
    by_path = {entry.path: entry for entry in inventory}
    missing = tuple(path for path in receipt.required_paths if path not in by_path)
    if missing:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REQUIRED_PATH_MISSING",
            "the source inventory is missing required paths",
            details=missing,
        )
    expected_identity_drift = tuple(
        path
        for path, expected_sha256 in receipt.expected_file_sha256.items()
        if by_path[path].sha256 != expected_sha256
    )
    if expected_identity_drift:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REQUIRED_IDENTITY_DRIFT",
            "a required source identity drifted in the source inventory",
            details=expected_identity_drift,
        )

    receipt_json = receipt.canonical_json()
    expected_sha_manifest = {
        receipt.archive_name: receipt.archive_sha256,
        receipt.inventory_name: receipt.inventory_sha256,
        receipt.source_receipt_name: _sha256_bytes(receipt_json.encode("utf-8")),
    }
    observed_sha_manifest = _load_json_file(
        sha_manifest_path,
        error_code="HARNESS_TOOLCHAIN_SHA256_MANIFEST_INVALID",
        safe_message="the source SHA-256 manifest is missing or invalid",
    )
    if observed_sha_manifest != expected_sha_manifest:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_SHA256_MANIFEST_DRIFT",
            "the source SHA-256 manifest contract drifted",
            sha_manifest_path.as_posix(),
        )
    _validate_archive_against_inventory(archive_path, inventory)
    return {
        "status": "CURRENT_CU129_HARNESS_SOURCE_PACKAGE_VERIFIED",
        "source_commit": receipt.source_commit,
        "archive_sha256": receipt.archive_sha256,
        "directory_sha256": receipt.directory_sha256,
        "file_count": receipt.file_count,
        "total_bytes": receipt.total_bytes,
        "source_dataset_file_count": 4,
        "authorization_issued": False,
        "model_requests_performed": 0,
    }


def _load_generated_notebook(path: Path) -> dict[str, object]:
    payload = _load_json_file(
        path,
        error_code="HARNESS_TOOLCHAIN_NOTEBOOK_JSON_INVALID",
        safe_message="a generated notebook is missing or invalid JSON",
    )
    if not isinstance(payload, dict):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_NOTEBOOK_ROOT_INVALID",
            "a generated notebook root must be one JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def verify_prepared_toolchain(toolchain_root: Path) -> dict[str, object]:
    """Independently verify all seven prepared toolchain outputs."""

    toolchain_root = toolchain_root.resolve()
    if not toolchain_root.is_dir() or toolchain_root.is_symlink():
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_OUTPUT_DIRECTORY_INVALID",
            "the prepared toolchain directory is missing or symbolic",
            toolchain_root.as_posix(),
        )
    receipt_path = toolchain_root / TOOLCHAIN_RECEIPT_NAME
    payload = _load_json_file(
        receipt_path,
        error_code="HARNESS_TOOLCHAIN_PREPARED_RECEIPT_INVALID",
        safe_message="the prepared toolchain receipt is missing or invalid",
    )
    try:
        prepared = toolchain_contracts.PreparedHarnessToolchainReceipt.model_validate(payload)
    except ValidationError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_PREPARED_RECEIPT_CONTRACT_INVALID",
            "the prepared toolchain receipt violates its typed contract",
            receipt_path.as_posix(),
            details=tuple(str(error) for error in exc.errors())[:10],
        ) from exc

    observed_paths: list[str] = []
    for path in toolchain_root.iterdir():
        if path.is_symlink() or not path.is_file():
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_OUTPUT_MEMBER_INVALID",
                "the prepared toolchain contains a symbolic or non-regular member",
                path.as_posix(),
            )
        observed_paths.append(path.name)
    if set(observed_paths) != set(prepared.output_filenames) or len(observed_paths) != 7:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_OUTPUT_SET_DRIFT",
            "the prepared toolchain output filename set drifted",
            toolchain_root.as_posix(),
        )

    source_summary = verify_source_package(toolchain_root)
    source_receipt_path = toolchain_root / SOURCE_RECEIPT_NAME
    sha_manifest_path = toolchain_root / SHA256_MANIFEST_NAME
    if _file_sha256(source_receipt_path) != prepared.source_receipt_sha256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_SOURCE_RECEIPT_IDENTITY_DRIFT",
            "the source receipt identity drifted from the prepared receipt",
            source_receipt_path.as_posix(),
        )
    if _file_sha256(sha_manifest_path) != prepared.source_sha256_manifest_sha256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_SOURCE_SHA_MANIFEST_IDENTITY_DRIFT",
            "the source SHA-256 manifest identity drifted from the prepared receipt",
            sha_manifest_path.as_posix(),
        )
    if prepared.source_package != load_source_receipt(source_receipt_path):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_SOURCE_RECEIPT_PARITY_DRIFT",
            "the prepared receipt and source receipt disagree",
            source_receipt_path.as_posix(),
        )

    materializer_payload = _load_generated_notebook(
        toolchain_root / prepared.materializer_notebook.filename
    )
    inspection_payload = _load_generated_notebook(
        toolchain_root / prepared.inspection_notebook.filename
    )
    observed_materializer = _validate_generated_notebook(
        materializer_payload,
        notebook_name=prepared.materializer_notebook.notebook_name,
        filename=prepared.materializer_notebook.filename,
    )
    observed_inspection = _validate_generated_notebook(
        inspection_payload,
        notebook_name=prepared.inspection_notebook.notebook_name,
        filename=prepared.inspection_notebook.filename,
    )
    if observed_materializer != prepared.materializer_notebook:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_MATERIALIZER_IDENTITY_DRIFT",
            "the materializer notebook identity drifted",
            prepared.materializer_notebook.filename,
        )
    if observed_inspection != prepared.inspection_notebook:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_INSPECTION_IDENTITY_DRIFT",
            "the inspection notebook identity drifted",
            prepared.inspection_notebook.filename,
        )
    return {
        "status": "CURRENT_CU129_HARNESS_TOOLCHAIN_VERIFIED",
        "source_commit": prepared.source_package.source_commit,
        "archive_sha256": source_summary["archive_sha256"],
        "directory_sha256": source_summary["directory_sha256"],
        "output_file_count": len(observed_paths),
        "materializer_notebook_sha256": prepared.materializer_notebook.sha256,
        "inspection_notebook_sha256": prepared.inspection_notebook.sha256,
        "authorization_issued": False,
        "model_requests_performed": 0,
    }


def _validate_output_placement(repo_root: Path, output_root: Path) -> None:
    try:
        output_root.relative_to(repo_root)
    except ValueError:
        return
    raise HarnessToolchainError(
        "HARNESS_TOOLCHAIN_OUTPUT_INSIDE_REPOSITORY_REJECTED",
        "toolchain output must be outside the source repository",
        output_root.as_posix(),
    )


def prepare_current_toolchain(
    repo_root: Path,
    output_root: Path,
) -> toolchain_contracts.PreparedHarnessToolchainReceipt:
    """Prepare all seven outputs in one atomic sibling-directory transaction."""

    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    source_commit = _validate_prepare_repository(repo_root)
    _validate_output_placement(repo_root, output_root)
    if output_root.exists():
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_OUTPUT_ALREADY_EXISTS",
            "toolchain output directory must not already exist",
            output_root.as_posix(),
        )
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.staging-",
            dir=output_root.parent,
        )
    )
    completed = False
    try:
        source_receipt = build_source_package(
            repo_root,
            staging_root,
            default_build_spec(source_commit),
            validate_current_boundary=True,
        )
        verify_source_package(staging_root)
        materializer, inspection = generate_notebooks(source_receipt, staging_root)
        output_filenames = (
            source_receipt.archive_name,
            SOURCE_INVENTORY_NAME,
            SOURCE_RECEIPT_NAME,
            SHA256_MANIFEST_NAME,
            materializer.filename,
            inspection.filename,
            TOOLCHAIN_RECEIPT_NAME,
        )
        prepared = toolchain_contracts.PreparedHarnessToolchainReceipt(
            status="CURRENT_CU129_HARNESS_TOOLCHAIN_PREPARED",
            source_package=source_receipt,
            source_receipt_sha256=_file_sha256(staging_root / SOURCE_RECEIPT_NAME),
            source_sha256_manifest_sha256=_file_sha256(staging_root / SHA256_MANIFEST_NAME),
            materializer_notebook=materializer,
            inspection_notebook=inspection,
            output_filenames=output_filenames,
            next_gate="publish_materialize_and_metadata_inspect_current_cu129_harness",
            safety=toolchain_contracts.HarnessToolchainSafety(),
        )
        _write_text_atomic(staging_root / TOOLCHAIN_RECEIPT_NAME, prepared.canonical_json())
        verify_prepared_toolchain(staging_root)
        staging_root.replace(output_root)
        completed = True
        return prepared
    finally:
        if not completed and staging_root.exists():
            shutil.rmtree(staging_root)


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate the committed toolchain, current runtime, and blocked safety boundary."""

    repo_root = repo_root.resolve()
    review_path = repo_root / REVIEW_RECORD_PATH
    review_payload = _load_json_file(
        review_path,
        error_code="HARNESS_TOOLCHAIN_REVIEW_RECORD_INVALID",
        safe_message="the rematerialization review record is missing or invalid",
    )
    if not isinstance(review_payload, dict):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REVIEW_RECORD_INVALID",
            "the rematerialization review record must contain one JSON object",
            review_path.as_posix(),
        )
    review = cast(dict[str, object], review_payload)
    if review.get("repository_base_commit") != "16decd4e0d91c4baa18129b0d7afc69bb2630aa1":
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REVIEW_BASE_DRIFT",
            "the rematerialization review base authority drifted",
            review_path.as_posix(),
        )
    if review.get("decision") != (
        "APPROVED_FOR_CURRENT_CU129_HARNESS_REMATERIALIZATION_IMPLEMENTATION"
    ):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REVIEW_DECISION_DRIFT",
            "the rematerialization implementation is not approved",
            review_path.as_posix(),
        )
    review_safety = review.get("safety")
    if not isinstance(review_safety, dict) or any(
        (
            review_safety.get("authorization_issued") is not False,
            review_safety.get("kaggle_execution_performed") is not False,
            review_safety.get("model_requests_performed") != 0,
        )
    ):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REVIEW_SAFETY_DRIFT",
            "the rematerialization review safety boundary drifted",
            review_path.as_posix(),
        )

    record_path = repo_root / TOOLCHAIN_RECORD_PATH
    record_payload = _load_json_file(
        record_path,
        error_code="HARNESS_TOOLCHAIN_DECISION_RECORD_INVALID",
        safe_message="the toolchain decision record is missing or invalid",
    )
    try:
        record = toolchain_contracts.HarnessToolchainDecisionRecord.model_validate(record_payload)
    except ValidationError as exc:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_DECISION_RECORD_INVALID",
            "the toolchain decision record violates its typed contract",
            record_path.as_posix(),
            details=tuple(str(error) for error in exc.errors())[:10],
        ) from exc

    mutable_after_materialization = {
        LAUNCHER_SOURCE_PATH,
        LAUNCHER_NOTEBOOK_PATH,
        RUNTIME_ADAPTER_PATH,
    }
    for relative_path, expected_sha256 in EXPECTED_FILE_SHA256.items():
        if relative_path in mutable_after_materialization:
            continue
        path = repo_root / relative_path
        if not path.is_file() or _file_sha256(path) != expected_sha256:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_CURRENT_SOURCE_IDENTITY_DRIFT",
                "a current CUDA 12.9 source identity drifted",
                relative_path,
            )

    manifest_path = repo_root / OFFLINE_MANIFEST_PATH
    manifest_payload = _load_json_file(
        manifest_path,
        error_code="HARNESS_TOOLCHAIN_MANIFEST_INVALID",
        safe_message="the active offline dataset manifest is missing or invalid",
    )
    if not isinstance(manifest_payload, dict):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_MANIFEST_INVALID",
            "the active offline dataset manifest must contain one JSON object",
            manifest_path.as_posix(),
        )
    raw_entries = manifest_payload.get("entries")
    if not isinstance(raw_entries, list):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_MANIFEST_INVALID",
            "the active offline dataset manifest entry set is invalid",
            manifest_path.as_posix(),
        )
    by_role: dict[str, dict[str, object]] = {}
    for entry in raw_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("role"), str):
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_MANIFEST_INVALID",
                "the active offline dataset manifest contains an invalid entry",
                manifest_path.as_posix(),
            )
        role = cast(str, entry["role"])
        if role in by_role:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_MANIFEST_DUPLICATE_ROLE",
                "the active offline dataset manifest contains a duplicate role",
                manifest_path.as_posix(),
                details=(f"role={role}",),
            )
        by_role[role] = cast(dict[str, object], entry)
    if set(by_role) != {"harness_source", "model_artifacts", "vllm_runtime"}:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_MANIFEST_ROLE_SET_DRIFT",
            "the active offline dataset manifest role set drifted",
            manifest_path.as_posix(),
        )
    harness_entry = by_role["harness_source"]
    mounted_path = str(harness_entry.get("mounted_path"))
    from auragateway.local_abc import (
        cu129_worker_observability_harness_integration as integration,
    )

    if (
        harness_entry.get("artifact_format") != "source_tree_directory"
        or harness_entry.get("sha256") != integration.CURRENT_HARNESS_DIRECTORY_SHA256
        or mounted_path != integration.CURRENT_HARNESS_MOUNTED_PATH
    ):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_ACTIVE_HARNESS_INTEGRATION_DRIFT",
            "the active manifest does not bind the consumed current harness evidence",
            manifest_path.as_posix(),
        )
    runtime_entry = by_role["vllm_runtime"]
    expected_runtime = {
        "artifact_format": "python_wheelhouse_directory",
        "package_count": RUNTIME_PACKAGE_COUNT,
        "resolution_lock_sha256": RUNTIME_RESOLUTION_LOCK_SHA256,
        "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
        "sha256_manifest_sha256": RUNTIME_SHA256_MANIFEST_SHA256,
        "materialization_receipt_sha256": RUNTIME_MATERIALIZATION_RECEIPT_SHA256,
        "runtime_output_directory": RUNTIME_OUTPUT_DIRECTORY,
    }
    if any(runtime_entry.get(key) != value for key, value in expected_runtime.items()):
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_RUNTIME_ENTRY_DRIFT",
            "the active CUDA 12.9 runtime authority drifted",
            manifest_path.as_posix(),
        )

    if record.review_minimum_ancestor != REVIEW_MINIMUM_ANCESTOR:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_REVIEW_AUTHORITY_DRIFT",
            "the toolchain review authority drifted",
        )
    pyproject_path = repo_root / "pyproject.toml"
    if _file_sha256(pyproject_path) != PYPROJECT_HISTORICAL_SHA256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_PYPROJECT_HISTORICAL_IDENTITY_DRIFT",
            "pyproject.toml no longer preserves the historical shared authority",
            pyproject_path.as_posix(),
        )
    ruff_config_path = repo_root / RUFF_CONFIG_PATH
    if _file_sha256(ruff_config_path) != RUFF_CONFIG_SHA256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_RUFF_POLICY_IDENTITY_DRIFT",
            "the dedicated Ruff policy overlay drifted",
            ruff_config_path.as_posix(),
        )
    historical_notebook_path = repo_root / HISTORICAL_MATERIALIZER_NOTEBOOK_PATH
    if _file_sha256(historical_notebook_path) != HISTORICAL_MATERIALIZER_NOTEBOOK_SHA256:
        raise HarnessToolchainError(
            "HARNESS_TOOLCHAIN_HISTORICAL_NOTEBOOK_IDENTITY_DRIFT",
            "the historical materializer notebook identity drifted",
            historical_notebook_path.as_posix(),
        )
    integration_summary = integration.validate_repository_package(repo_root)
    review_spec = default_build_spec(REVIEW_MINIMUM_ANCESTOR)
    return {
        "status": "CURRENT_CU129_HARNESS_TOOLCHAIN_IMPLEMENTED",
        "decision": record.decision,
        "review_minimum_ancestor": REVIEW_MINIMUM_ANCESTOR,
        "source_binding_policy": SOURCE_BINDING_POLICY,
        "archive_name_template": "ag-harness-<head7>-v1.zip",
        "input_dataset_name_template": "ag-harness-<head7>-v1-input",
        "output_directory_template": "auragateway_qualification_harness_<head7>_v1",
        "review_archive_example": review_spec.archive_name,
        "materializer_notebook_name": MATERIALIZER_NOTEBOOK_NAME,
        "inspection_notebook_name": INSPECTION_NOTEBOOK_NAME,
        "runtime_role": "vllm_runtime",
        "runtime_artifact_format": "python_wheelhouse_directory",
        "runtime_package_count": RUNTIME_PACKAGE_COUNT,
        "active_harness_binding_status": ("WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED"),
        "operational_input_closure": integration_summary["operational_input_closure"],
        "authorization_issued": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": integration_summary["next_gate"],
    }


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--repo-root", type=Path, default=Path("."))
    prepare.add_argument("--output-dir", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--toolchain-dir", type=Path, required=True)

    validate = subparsers.add_parser("validate-repository")
    validate.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one explicit toolchain command and emit machine-readable safe output."""

    parser = _build_parser()
    try:
        arguments = parser.parse_args(argv)
        command = cast(str, arguments.command)
        if command == "prepare":
            result: object = prepare_current_toolchain(
                arguments.repo_root,
                arguments.output_dir,
            )
            prepared = cast(toolchain_contracts.PreparedHarnessToolchainReceipt, result)
            print(prepared.canonical_json())
        elif command == "verify":
            result = verify_prepared_toolchain(arguments.toolchain_dir)
            for key, value in result.items():
                rendered = str(value).lower() if isinstance(value, bool) else value
                print(f"{key}={rendered}")
        elif command == "validate-repository":
            result = validate_repository_package(arguments.repo_root.resolve())
            for key, value in result.items():
                rendered = str(value).lower() if isinstance(value, bool) else value
                print(f"{key}={rendered}")
        else:
            raise HarnessToolchainError(
                "HARNESS_TOOLCHAIN_COMMAND_INVALID",
                "an unsupported toolchain command was requested",
            )
        return 0
    except HarnessToolchainError as exc:
        envelope = {
            "error_code": exc.error_code,
            "safe_message": exc.safe_message,
            "path": exc.path,
            "details": exc.details,
        }
        print(_canonical_json(envelope))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
