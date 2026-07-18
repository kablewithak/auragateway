"""Deterministic identities for mounted offline qualification artifacts."""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
from typing import Final

_MAX_DIRECTORY_FILES: Final = 5_000
_MAX_DIRECTORY_BYTES: Final = 2 * 1024 * 1024 * 1024


class ArtifactIdentityError(ValueError):
    """Fail-closed mounted-artifact identity error."""


def file_sha256(path: Path) -> str:
    """Hash one regular file."""

    if not path.is_file() or path.is_symlink():
        raise ArtifactIdentityError("artifact must be one regular file")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_sha256(
    root: Path,
    *,
    maximum_files: int = _MAX_DIRECTORY_FILES,
    maximum_bytes: int = _MAX_DIRECTORY_BYTES,
) -> str:
    """Hash a directory as a canonical sorted file manifest."""

    if not root.is_dir() or root.is_symlink():
        raise ArtifactIdentityError("artifact must be one real directory")

    entries: list[dict[str, object]] = []
    total_bytes = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ArtifactIdentityError("artifact directory contains a symbolic link")
        metadata = path.stat()
        if path.is_dir():
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ArtifactIdentityError("artifact directory contains a non-regular member")
        total_bytes += metadata.st_size
        if total_bytes > maximum_bytes:
            raise ArtifactIdentityError("artifact directory exceeds the byte budget")
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": file_sha256(path),
                "size_bytes": metadata.st_size,
            }
        )
        if len(entries) > maximum_files:
            raise ArtifactIdentityError("artifact directory exceeds the file-count budget")

    if not entries:
        raise ArtifactIdentityError("artifact directory is empty")
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
