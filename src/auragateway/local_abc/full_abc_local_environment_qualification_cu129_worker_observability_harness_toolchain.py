"""Build the post-merge source package for worker-observability rematerialization."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

REVIEW_MERGE_COMMIT: Final = "997efb4aacf998567a3d92e7202a0054bf473ca4"
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
NOTEBOOK_NAME: Final = "ag-worker-obs-harness-materializer-v1"
MATERIALIZER_OUTPUT_ROOT: Final = "ag_worker_obs_harness_materializer_v1_output"
MAXIMUM_SOURCE_FILES: Final = 5_000
MAXIMUM_SOURCE_BYTES: Final = 100 * 1024 * 1024
ZIP_TIMESTAMP: Final = (1980, 1, 1, 0, 0, 0)
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
REQUIRED_SOURCE_PATHS: Final = (
    "pyproject.toml",
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py",
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py",
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_worker_startup_diagnostics.py",
    "notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb",
)


class HarnessToolchainError(RuntimeError):
    """Metadata-safe post-merge harness toolchain failure."""

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
            "WORKER_OBSERVABILITY_HARNESS_ARGUMENT_INVALID",
            "worker-observability harness arguments are invalid",
            details=(message,),
        )


class SourceInventoryEntry(LocalABCContract):
    """One regular source file in the deterministic harness tree."""

    path: str
    sha256: str
    size_bytes: int = Field(ge=0, le=MAXIMUM_SOURCE_BYTES)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("source inventory paths must be safe relative POSIX paths")
        if value.lower().endswith(ARCHIVE_SUFFIXES):
            raise ValueError("source inventory cannot contain nested archives")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("source inventory digest must be lowercase SHA-256")
        return value


class HarnessSourceReceipt(LocalABCContract):
    """Exact post-merge source package identity and safety boundary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["WORKER_OBSERVABILITY_HARNESS_SOURCE_PACKAGED"]
    source_commit: str
    source_short_commit: str
    review_merge_commit: Literal["997efb4aacf998567a3d92e7202a0054bf473ca4"]
    archive_filename: str
    archive_sha256: str
    source_inventory_filename: Literal["source_inventory.json"]
    source_inventory_sha256: str
    source_directory_sha256: str
    source_file_count: int = Field(ge=1, le=MAXIMUM_SOURCE_FILES)
    source_total_bytes: int = Field(ge=1, le=MAXIMUM_SOURCE_BYTES)
    materializer_notebook_filename: Literal["ag_worker_obs_harness_materializer_v1.ipynb"]
    materializer_notebook_name: Literal["ag-worker-obs-harness-materializer-v1"]
    input_dataset_name: str
    output_directory: str
    nested_archives_present: Literal[False] = False
    symlinks_present: Literal[False] = False
    network_access_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    benchmark_trajectory_requests_performed: Literal[0] = 0
    authorization_issued: Literal[False] = False
    active_manifest_promoted: Literal[False] = False

    @field_validator(
        "source_commit",
        "review_merge_commit",
    )
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("source commits must be lowercase Git object ids")
        return value

    @field_validator(
        "archive_sha256",
        "source_inventory_sha256",
        "source_directory_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("source package digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_names(self) -> Self:
        if self.source_short_commit != self.source_commit[:7]:
            raise ValueError("short source commit does not match source commit")
        if self.source_short_commit not in self.archive_filename:
            raise ValueError("archive filename does not bind short source commit")
        if self.source_short_commit not in self.input_dataset_name:
            raise ValueError("dataset name does not bind short source commit")
        if self.source_short_commit not in self.output_directory:
            raise ValueError("output directory does not bind short source commit")
        return self


class PackageFileEntry(LocalABCContract):
    """One regular top-level producer output, including the source archive."""

    path: str
    sha256: str
    size_bytes: int = Field(ge=0, le=MAXIMUM_SOURCE_BYTES)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.name != value:
            raise ValueError("package paths must be safe top-level POSIX names")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("package member digest must be lowercase SHA-256")
        return value


class HarnessSourcePackageManifest(LocalABCContract):
    """Flat local producer output topology."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    package_id: Literal["auragateway-worker-observability-harness-source-v1"]
    source_commit: str
    files: tuple[PackageFileEntry, ...]
    authorization_included: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    model_requests_performed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_file_set(self) -> Self:
        names = tuple(entry.path for entry in self.files)
        required = {
            "source_inventory.json",
            "source_receipt.json",
            "ag_worker_obs_harness_materializer_v1.ipynb",
        }
        if not required.issubset(names):
            raise ValueError("source package manifest is incomplete")
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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_git(repo_root: Path, arguments: list[str], *, timeout: float = 10.0) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_GIT_FAILED",
            "a required Git authority could not be resolved",
            details=(" ".join(arguments),),
        )
    return result.stdout


def _require_clean_synchronized_main(repo_root: Path) -> str:
    branch = _run_git(repo_root, ["branch", "--show-current"]).decode().strip()
    if branch != "main":
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_MAIN_REQUIRED",
            "post-merge harness packaging requires main",
        )
    head = _run_git(repo_root, ["rev-parse", "HEAD"]).decode().strip()
    origin_main = _run_git(repo_root, ["rev-parse", "origin/main"]).decode().strip()
    if head != origin_main:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_ORIGIN_DRIFT",
            "local main must equal origin/main",
        )
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            REVIEW_MERGE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        timeout=5,
    )
    if ancestry.returncode != 0:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_REVIEW_MERGE_MISSING",
            "worker-observability review merge must be an ancestor of HEAD",
        )
    status = _run_git(
        repo_root,
        ["status", "--porcelain", "--untracked-files=all"],
    )
    if status:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_TREE_NOT_CLEAN",
            "post-merge harness packaging requires a clean working tree",
        )
    if (repo_root / FINAL_AUTHORIZATION_PATH).exists():
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_AUTHORIZATION_PRESENT",
            "authorization must remain absent during harness packaging",
            FINAL_AUTHORIZATION_PATH.as_posix(),
        )
    return head


def _tracked_source_paths(repo_root: Path) -> tuple[Path, ...]:
    raw = _run_git(repo_root, ["ls-files", "-z"], timeout=30.0)
    paths: list[Path] = []
    for value in raw.decode("utf-8").split("\0"):
        if not value:
            continue
        relative = Path(value)
        posix = relative.as_posix()
        if posix.startswith("evidence_vault/"):
            continue
        if relative == FINAL_AUTHORIZATION_PATH:
            continue
        if posix.lower().endswith(ARCHIVE_SUFFIXES):
            continue
        path = repo_root / relative
        if path.is_symlink():
            raise HarnessToolchainError(
                "WORKER_OBSERVABILITY_HARNESS_SYMLINK_REJECTED",
                "source package contains a symbolic link",
                posix,
            )
        if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
            raise HarnessToolchainError(
                "WORKER_OBSERVABILITY_HARNESS_MEMBER_REJECTED",
                "source package contains a non-regular tracked member",
                posix,
            )
        paths.append(relative)
    observed = {path.as_posix() for path in paths}
    missing = tuple(path for path in REQUIRED_SOURCE_PATHS if path not in observed)
    if missing:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_REQUIRED_PATH_MISSING",
            "post-merge source package is missing required paths",
            details=missing,
        )
    if not paths or len(paths) > MAXIMUM_SOURCE_FILES:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_FILE_BUDGET_EXCEEDED",
            "post-merge source package exceeds its file-count boundary",
        )
    return tuple(sorted(paths, key=lambda item: item.as_posix()))


def _source_inventory(
    repo_root: Path,
    paths: tuple[Path, ...],
) -> tuple[tuple[SourceInventoryEntry, ...], int]:
    entries: list[SourceInventoryEntry] = []
    total_bytes = 0
    for relative in paths:
        path = repo_root / relative
        size = path.stat().st_size
        total_bytes += size
        if total_bytes > MAXIMUM_SOURCE_BYTES:
            raise HarnessToolchainError(
                "WORKER_OBSERVABILITY_HARNESS_BYTE_BUDGET_EXCEEDED",
                "post-merge source package exceeds its byte boundary",
            )
        entries.append(
            SourceInventoryEntry(
                path=relative.as_posix(),
                sha256=_file_sha256(path),
                size_bytes=size,
            )
        )
    return tuple(entries), total_bytes


def _inventory_json(entries: tuple[SourceInventoryEntry, ...]) -> str:
    return _canonical_json(
        {
            "schema_version": "1.0.0",
            "files": [entry.model_dump(mode="json") for entry in entries],
        }
    )


def _directory_sha256(entries: tuple[SourceInventoryEntry, ...]) -> str:
    return _sha256_bytes(_inventory_json(entries).encode("utf-8"))


def _write_archive(
    repo_root: Path,
    paths: tuple[Path, ...],
    archive_path: Path,
) -> None:
    with zipfile.ZipFile(
        archive_path,
        mode="x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative in paths:
            info = zipfile.ZipInfo(relative.as_posix(), date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (repo_root / relative).read_bytes())


def _string_literal_block(value: str, *, indent: int = 4) -> str:
    chunks = (value[index : index + 76] for index in range(0, len(value), 76))
    prefix = " " * indent
    return "\n".join(f"{prefix}{json.dumps(chunk)}" for chunk in chunks)


def _materializer_source(receipt: HarnessSourceReceipt) -> str:
    template = r"""from __future__ import annotations

import hashlib
import json
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

NOTEBOOK_NAME = "__NOTEBOOK_NAME__"
INPUT_ROOT = Path("/kaggle/input").resolve()
WORK_ROOT = Path("/kaggle/working").resolve()
DATASET_NAME = "__DATASET_NAME__"
ARCHIVE_FILENAME = "__ARCHIVE_FILENAME__"
EXPECTED_ARCHIVE_SHA256 = "__ARCHIVE_SHA256__"
EXPECTED_INVENTORY_SHA256 = "__INVENTORY_SHA256__"
EXPECTED_DIRECTORY_SHA256 = "__DIRECTORY_SHA256__"
EXPECTED_FILE_COUNT = __FILE_COUNT__
EXPECTED_TOTAL_BYTES = __TOTAL_BYTES__
OUTPUT_PARENT = WORK_ROOT / "__MATERIALIZER_OUTPUT_ROOT__"
OUTPUT_ROOT = OUTPUT_PARENT / "__OUTPUT_DIRECTORY__"
STAGING_ROOT = WORK_ROOT / ".ag_worker_obs_harness_staging"
RECEIPT_PATH = OUTPUT_PARENT / "materialization_receipt.json"
MAXIMUM_FILES = __MAXIMUM_FILES__
MAXIMUM_TOTAL_BYTES = __MAXIMUM_BYTES__
ARCHIVE_SUFFIXES = (".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".7z", ".whl")


def canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validated_member_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise RuntimeError("source archive contains an unsafe path")
    if path.as_posix().lower().endswith(ARCHIVE_SUFFIXES):
        raise RuntimeError("source archive contains a nested archive")
    return path


def inspect_tree(root: Path) -> tuple[list[dict[str, object]], int]:
    entries = []
    total_bytes = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise RuntimeError("source tree contains a symbolic link")
        if path.is_dir():
            continue
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("source tree contains a non-regular member")
        relative = path.relative_to(root).as_posix()
        validated_member_path(relative)
        total_bytes += metadata.st_size
        if total_bytes > MAXIMUM_TOTAL_BYTES:
            raise RuntimeError("source tree exceeds its byte boundary")
        entries.append(
            {
                "path": relative,
                "sha256": file_sha256(path),
                "size_bytes": metadata.st_size,
            }
        )
        if len(entries) > MAXIMUM_FILES:
            raise RuntimeError("source tree exceeds its file-count boundary")
    return entries, total_bytes


def validate_tree(root: Path) -> tuple[list[dict[str, object]], int]:
    entries, total_bytes = inspect_tree(root)
    inventory = canonical_json({"schema_version": "1.0.0", "files": entries})
    if hashlib.sha256(inventory.encode("utf-8")).hexdigest() != EXPECTED_DIRECTORY_SHA256:
        raise RuntimeError("source directory identity drifted")
    if len(entries) != EXPECTED_FILE_COUNT or total_bytes != EXPECTED_TOTAL_BYTES:
        raise RuntimeError("source tree size boundary drifted")
    return entries, total_bytes


def resolve_dataset_root() -> Path:
    candidates = tuple(
        path.resolve()
        for path in INPUT_ROOT.rglob(DATASET_NAME)
        if path.is_dir() and not path.is_symlink()
    )
    if len(candidates) != 1:
        raise RuntimeError("expected exactly one worker-observability source dataset")
    if INPUT_ROOT not in candidates[0].parents:
        raise RuntimeError("source dataset escaped /kaggle/input")
    return candidates[0]


def extract_archive(archive_path: Path) -> None:
    if file_sha256(archive_path) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("source archive identity drifted")
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        file_count = 0
        total_bytes = 0
        for member in members:
            member_path = validated_member_path(member.filename)
            if member.flag_bits & 0x1:
                raise RuntimeError("source archive contains an encrypted member")
            mode = member.external_attr >> 16
            if member.is_dir():
                continue
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise RuntimeError("source archive contains a non-regular member")
            file_count += 1
            total_bytes += member.file_size
            if file_count > MAXIMUM_FILES or total_bytes > MAXIMUM_TOTAL_BYTES:
                raise RuntimeError("source archive exceeds a bounded limit")
            destination = STAGING_ROOT.joinpath(*member_path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)


def copy_expanded_tree(dataset_root: Path) -> None:
    validate_tree(dataset_root)
    for source in sorted(dataset_root.rglob("*"), key=lambda item: item.as_posix()):
        if source.is_dir():
            continue
        relative = source.relative_to(dataset_root)
        destination = STAGING_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as source_handle, destination.open("xb") as target:
            shutil.copyfileobj(source_handle, target, length=1024 * 1024)


if len(NOTEBOOK_NAME) > 50:
    raise RuntimeError("Kaggle notebook name exceeds 50 characters")
if OUTPUT_PARENT.exists() or STAGING_ROOT.exists():
    raise RuntimeError("worker-observability materializer output already exists")

dataset_root = resolve_dataset_root()
archive_path = dataset_root / ARCHIVE_FILENAME
archive_present = archive_path.is_file() and not archive_path.is_symlink()
direct_tree_present = (dataset_root / "pyproject.toml").is_file()
if archive_present == direct_tree_present:
    raise RuntimeError("worker-observability source input shape is ambiguous")

STAGING_ROOT.mkdir()
try:
    if archive_present:
        extract_archive(archive_path)
        input_mode = "exact_archive"
    else:
        copy_expanded_tree(dataset_root)
        input_mode = "expanded_dataset_tree"
    entries, total_bytes = validate_tree(STAGING_ROOT)
    OUTPUT_PARENT.mkdir()
    STAGING_ROOT.replace(OUTPUT_ROOT)
except Exception:
    shutil.rmtree(STAGING_ROOT, ignore_errors=True)
    raise

receipt = {
    "schema_version": "1.0.0",
    "status": "WORKER_OBSERVABILITY_HARNESS_MATERIALIZED",
    "producer_notebook_name": NOTEBOOK_NAME,
    "source_commit": "__SOURCE_COMMIT__",
    "input_dataset_name": DATASET_NAME,
    "input_mode": input_mode,
    "archive_filename": ARCHIVE_FILENAME,
    "archive_sha256": EXPECTED_ARCHIVE_SHA256,
    "source_inventory_sha256": EXPECTED_INVENTORY_SHA256,
    "output_directory": "__OUTPUT_DIRECTORY__",
    "directory_sha256": EXPECTED_DIRECTORY_SHA256,
    "file_count": len(entries),
    "total_bytes": total_bytes,
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
}
RECEIPT_PATH.write_text(canonical_json(receipt), encoding="utf-8")
print("status=WORKER_OBSERVABILITY_HARNESS_MATERIALIZED")
print(f"input_mode={input_mode}")
print(f"output_directory={OUTPUT_ROOT}")
print(f"file_count={len(entries)}")
print(f"total_bytes={total_bytes}")
print(f"directory_sha256={EXPECTED_DIRECTORY_SHA256}")
print("nested_archives_present=false")
print("gpu_execution_performed=false")
print("model_requests_performed=0")
print("save_this_notebook_output=true")
"""
    replacements = {
        "__NOTEBOOK_NAME__": NOTEBOOK_NAME,
        "__DATASET_NAME__": receipt.input_dataset_name,
        "__ARCHIVE_FILENAME__": receipt.archive_filename,
        "__ARCHIVE_SHA256__": receipt.archive_sha256,
        "__INVENTORY_SHA256__": receipt.source_inventory_sha256,
        "__DIRECTORY_SHA256__": receipt.source_directory_sha256,
        "__FILE_COUNT__": str(receipt.source_file_count),
        "__TOTAL_BYTES__": str(receipt.source_total_bytes),
        "__MATERIALIZER_OUTPUT_ROOT__": MATERIALIZER_OUTPUT_ROOT,
        "__OUTPUT_DIRECTORY__": receipt.output_directory,
        "__SOURCE_COMMIT__": receipt.source_commit,
        "__MAXIMUM_FILES__": str(MAXIMUM_SOURCE_FILES),
        "__MAXIMUM_BYTES__": str(MAXIMUM_SOURCE_BYTES),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    unresolved = tuple(marker for marker in replacements if marker in template)
    if unresolved:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_MATERIALIZER_TEMPLATE_INCOMPLETE",
            "materializer template contains unresolved markers",
            details=unresolved,
        )
    return template


def _materializer_notebook(receipt: HarnessSourceReceipt) -> dict[str, object]:
    source = _materializer_source(receipt)
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "worker-observability-materializer-introduction",
                "metadata": {},
                "source": [
                    "# AuraGateway worker-observability harness materializer v1\n",
                    "\n",
                    "CPU-only, Internet Off, no secrets, Save Version -> Save & Run All.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "worker-observability-materializer",
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "auragateway": {
                "archive_sha256": receipt.archive_sha256,
                "directory_sha256": receipt.source_directory_sha256,
                "file_count": receipt.source_file_count,
                "input_dataset_name": receipt.input_dataset_name,
                "notebook_name": NOTEBOOK_NAME,
                "output_directory": receipt.output_directory,
                "source_commit": receipt.source_commit,
                "runtime_execution_performed": False,
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
                "version": "3.12",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write_text_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
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
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        if path.exists():
            raise HarnessToolchainError(
                "WORKER_OBSERVABILITY_HARNESS_OUTPUT_EXISTS",
                "post-merge harness output already exists",
                path.as_posix(),
            )
        temporary.replace(path)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def build_post_merge_package(
    *,
    repo_root: Path,
    output_root: Path,
    enforce_git_state: bool = True,
    source_commit: str | None = None,
) -> dict[str, object]:
    """Build one deterministic post-merge package without operational execution."""

    root = repo_root.resolve()
    commit = (
        _require_clean_synchronized_main(root) if enforce_git_state else cast(str, source_commit)
    )
    if len(commit) != 40:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_SOURCE_COMMIT_INVALID",
            "post-merge source commit is invalid",
        )
    short = commit[:7]
    paths = _tracked_source_paths(root)
    entries, total_bytes = _source_inventory(root, paths)
    inventory_json = _inventory_json(entries)
    inventory_sha256 = _sha256_bytes(inventory_json.encode("utf-8"))
    directory_sha256 = _directory_sha256(entries)

    package_root = output_root.resolve()
    if package_root.exists():
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_OUTPUT_EXISTS",
            "post-merge harness package output already exists",
            package_root.as_posix(),
        )
    package_root.mkdir(parents=True)
    archive_filename = f"ag-worker-obs-harness-{short}-v1.zip"
    archive_path = package_root / archive_filename
    _write_archive(root, paths, archive_path)
    archive_sha256 = _file_sha256(archive_path)

    receipt = HarnessSourceReceipt(
        status="WORKER_OBSERVABILITY_HARNESS_SOURCE_PACKAGED",
        source_commit=commit,
        source_short_commit=short,
        review_merge_commit=REVIEW_MERGE_COMMIT,
        archive_filename=archive_filename,
        archive_sha256=archive_sha256,
        source_inventory_filename="source_inventory.json",
        source_inventory_sha256=inventory_sha256,
        source_directory_sha256=directory_sha256,
        source_file_count=len(entries),
        source_total_bytes=total_bytes,
        materializer_notebook_filename=("ag_worker_obs_harness_materializer_v1.ipynb"),
        materializer_notebook_name=NOTEBOOK_NAME,
        input_dataset_name=f"ag-worker-obs-harness-{short}-v1-input",
        output_directory=(f"auragateway_qualification_harness_{short}_worker_obs_v1"),
    )
    _write_text_atomic(
        package_root / "source_inventory.json",
        inventory_json,
    )
    _write_text_atomic(
        package_root / "source_receipt.json",
        receipt.canonical_json(),
    )
    notebook_payload = (
        json.dumps(
            _materializer_notebook(receipt),
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    )
    _write_text_atomic(
        package_root / "ag_worker_obs_harness_materializer_v1.ipynb",
        notebook_payload,
    )

    package_entries = tuple(
        PackageFileEntry(
            path=path.name,
            sha256=_file_sha256(path),
            size_bytes=path.stat().st_size,
        )
        for path in sorted(package_root.iterdir(), key=lambda item: item.name)
        if path.is_file()
    )
    manifest = HarnessSourcePackageManifest(
        package_id="auragateway-worker-observability-harness-source-v1",
        source_commit=commit,
        files=package_entries,
    )
    _write_text_atomic(
        package_root / "package_manifest.json",
        manifest.canonical_json(),
    )
    return validate_built_package(package_root)


def validate_built_package(package_root: Path) -> dict[str, object]:
    """Validate one local producer output without running Kaggle or a model."""

    root = package_root.resolve()
    manifest = HarnessSourcePackageManifest.model_validate_json(
        (root / "package_manifest.json").read_text(encoding="utf-8")
    )
    observed = {
        path.name
        for path in root.iterdir()
        if path.is_file() and path.name != "package_manifest.json"
    }
    expected = {entry.path for entry in manifest.files}
    if observed != expected:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_PACKAGE_TOPOLOGY_DRIFT",
            "post-merge harness package topology drifted",
        )
    for entry in manifest.files:
        path = root / entry.path
        if path.stat().st_size != entry.size_bytes or _file_sha256(path) != entry.sha256:
            raise HarnessToolchainError(
                "WORKER_OBSERVABILITY_HARNESS_PACKAGE_IDENTITY_DRIFT",
                "post-merge harness package member identity drifted",
                entry.path,
            )
    receipt = HarnessSourceReceipt.model_validate_json(
        (root / "source_receipt.json").read_text(encoding="utf-8")
    )
    if _file_sha256(root / receipt.archive_filename) != receipt.archive_sha256:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_HARNESS_ARCHIVE_DRIFT",
            "post-merge harness archive identity drifted",
        )
    notebook = json.loads(
        (root / receipt.materializer_notebook_filename).read_text(encoding="utf-8")
    )
    cells = notebook.get("cells") if isinstance(notebook, dict) else None
    if not isinstance(cells, list) or len(cells) != 2:
        raise HarnessToolchainError(
            "WORKER_OBSERVABILITY_MATERIALIZER_NOTEBOOK_DRIFT",
            "post-merge materializer notebook topology drifted",
        )
    return {
        "status": "WORKER_OBSERVABILITY_HARNESS_SOURCE_PACKAGE_VALID",
        "source_commit": receipt.source_commit,
        "archive_filename": receipt.archive_filename,
        "archive_sha256": receipt.archive_sha256,
        "source_directory_sha256": receipt.source_directory_sha256,
        "source_file_count": receipt.source_file_count,
        "source_total_bytes": receipt.source_total_bytes,
        "materializer_notebook_name": receipt.materializer_notebook_name,
        "authorization_issued": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "active_manifest_promoted": False,
        "next_gate": "cpu_only_harness_materialization_then_metadata_inspection",
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-worker-observability-harness-toolchain")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--repo-root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--package-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _build_parser().parse_args(argv)
        if arguments.command == "build":
            result = build_post_merge_package(
                repo_root=cast(Path, arguments.repo_root),
                output_root=cast(Path, arguments.output),
            )
        else:
            result = validate_built_package(cast(Path, arguments.package_root))
        for key, value in result.items():
            rendered = str(value).lower() if isinstance(value, bool) else value
            print(f"{key}={rendered}")
        return 0
    except HarnessToolchainError as error:
        envelope = {
            "error_code": error.error_code,
            "safe_message": error.safe_message,
            "path": error.path,
            "details": error.details,
        }
        print(_canonical_json(envelope), file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
