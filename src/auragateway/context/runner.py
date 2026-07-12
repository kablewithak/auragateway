"""Verify the static-anchor registry and volatile-append context boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.context import (
    ContextBoundaryManifest,
    ContextBoundarySummary,
    StaticAnchorRegistry,
    VolatileItemKind,
)

_DEFAULT_REGISTRY = Path("data/context/static_anchor_registry.json")
_DEFAULT_MANIFEST = Path("data/context/boundary_manifest.json")


class ContextBoundaryError(Exception):
    """Expected context-boundary failure with safe details."""

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


class ContextBoundaryErrorEnvelope(BaseModel):
    """Safe CLI error output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, not_found_code: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContextBoundaryError(
            not_found_code,
            "Required context-boundary artifact was not found.",
            str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContextBoundaryError(
            "CONTEXT_BOUNDARY_INVALID_JSON",
            "Context-boundary artifact is not valid JSON.",
            str(path),
        ) from exc


def verify_context_boundary(repo_root: Path) -> ContextBoundarySummary:
    """Validate typed registry, referenced hashes, and boundary manifest."""

    registry_path = repo_root / _DEFAULT_REGISTRY
    manifest_path = repo_root / _DEFAULT_MANIFEST
    try:
        registry = StaticAnchorRegistry.model_validate(
            _load_json(registry_path, "STATIC_ANCHOR_REGISTRY_NOT_FOUND")
        )
    except ValidationError as exc:
        raise ContextBoundaryError(
            "STATIC_ANCHOR_REGISTRY_VALIDATION_FAILED",
            "Static-anchor registry failed typed validation.",
            str(registry_path),
            _validation_messages(exc),
        ) from exc
    try:
        manifest = ContextBoundaryManifest.model_validate(
            _load_json(manifest_path, "CONTEXT_BOUNDARY_MANIFEST_NOT_FOUND")
        )
    except ValidationError as exc:
        raise ContextBoundaryError(
            "CONTEXT_BOUNDARY_MANIFEST_VALIDATION_FAILED",
            "Context-boundary manifest failed typed validation.",
            str(manifest_path),
            _validation_messages(exc),
        ) from exc

    if manifest.static_registry_path != _DEFAULT_REGISTRY.as_posix():
        raise ContextBoundaryError(
            "STATIC_ANCHOR_REGISTRY_PATH_MISMATCH",
            "Context-boundary manifest references an unexpected registry path.",
            str(manifest_path),
        )
    if manifest.static_registry_sha256 != _sha256(registry_path):
        raise ContextBoundaryError(
            "STATIC_ANCHOR_REGISTRY_HASH_MISMATCH",
            "Static-anchor registry bytes do not match the boundary manifest.",
            str(registry_path),
        )
    if manifest.static_anchor_count != len(registry.anchors):
        raise ContextBoundaryError(
            "STATIC_ANCHOR_COUNT_MISMATCH",
            "Static-anchor count does not match the boundary manifest.",
            str(manifest_path),
        )

    for anchor in registry.anchors:
        artifact = repo_root / anchor.artifact_path
        try:
            actual_hash = _sha256(artifact)
        except FileNotFoundError as exc:
            raise ContextBoundaryError(
                "STATIC_ANCHOR_ARTIFACT_NOT_FOUND",
                "A required static-anchor artifact was not found.",
                str(artifact),
                (anchor.anchor_id,),
            ) from exc
        if actual_hash != anchor.artifact_sha256:
            raise ContextBoundaryError(
                "STATIC_ANCHOR_ARTIFACT_HASH_MISMATCH",
                "A static-anchor artifact does not match its registered hash.",
                str(artifact),
                (anchor.anchor_id,),
            )

    return ContextBoundarySummary(
        registry_id=registry.registry_id,
        static_anchor_count=len(registry.anchors),
        volatile_item_kind_count=len(VolatileItemKind),
        gate_3_passed=manifest.gate_3_passed,
        measured_execution_permitted=manifest.measured_execution_permitted,
        validation_status="valid",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = _parse_args(argv)
    try:
        summary = verify_context_boundary(args.repo_root)
    except ContextBoundaryError as exc:
        envelope = ContextBoundaryErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 2
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
