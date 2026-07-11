"""Build and verify immutable evidence for the authored Nimbus Relay corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from auragateway.contracts.corpus import CorpusInventory, CorpusSource
from auragateway.contracts.corpus_freeze import (
    CorpusArtifactRecord,
    CorpusDocumentHeader,
    CorpusFreezeRecord,
    CorpusFreezeStatus,
    CorpusFreezeSummary,
    CorpusSourceManifest,
)

_DEFAULT_INVENTORY: Final = Path("data/corpus/source_inventory.json")
_DEFAULT_MANIFEST: Final = Path("data/corpus/source_manifest.json")
_DEFAULT_FREEZE_RECORD: Final = Path("data/corpus/corpus_freeze_record.json")
_DOCUMENTS_ROOT: Final = Path("data/corpus/documents")
_ALLOWED_SUFFIXES: Final = {".md", ".json"}
_FORBIDDEN_CONTENT_PATTERNS: Final = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "openai_style_secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}


@dataclass(frozen=True, slots=True)
class CorpusFreezeError(Exception):
    """Expected corpus freeze failure with a safe machine-readable code."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.safe_message


class CorpusFreezeErrorEnvelope(BaseModel):
    """Safe CLI failure output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class CorpusJsonDocument(BaseModel):
    """Typed outer boundary for a JSON corpus document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: CorpusDocumentHeader
    content: JsonValue


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(path: Path, error_code: str) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise CorpusFreezeError(
            error_code=error_code,
            safe_message="Required corpus artifact was not found.",
            path=str(path),
        ) from exc


def _read_json(path: Path, error_code: str) -> object:
    payload = _read_bytes(path, error_code)
    try:
        return json.loads(payload.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_ARTIFACT_NOT_UTF8",
            safe_message="Corpus artifact is not valid UTF-8.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_ARTIFACT_INVALID_JSON",
            safe_message="Corpus artifact is not valid JSON.",
            path=str(path),
        ) from exc


def _load_inventory(path: Path) -> CorpusInventory:
    try:
        inventory = CorpusInventory.model_validate(_read_json(path, "CORPUS_INVENTORY_NOT_FOUND"))
    except ValidationError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_INVENTORY_VALIDATION_FAILED",
            safe_message="Corpus inventory failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc
    if inventory.status != CorpusFreezeStatus.FROZEN.value:
        raise CorpusFreezeError(
            error_code="CORPUS_INVENTORY_NOT_FROZEN",
            safe_message=(
                "Corpus inventory must be marked frozen before corpus freeze evidence is built."
            ),
            path=str(path),
        )
    return inventory


def _load_manifest(path: Path) -> CorpusSourceManifest:
    try:
        return CorpusSourceManifest.model_validate(
            _read_json(path, "CORPUS_SOURCE_MANIFEST_NOT_FOUND")
        )
    except ValidationError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_SOURCE_MANIFEST_VALIDATION_FAILED",
            safe_message="Corpus source manifest failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _load_freeze_record(path: Path) -> CorpusFreezeRecord:
    try:
        return CorpusFreezeRecord.model_validate(_read_json(path, "CORPUS_FREEZE_RECORD_NOT_FOUND"))
    except ValidationError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_FREEZE_RECORD_VALIDATION_FAILED",
            safe_message="Corpus freeze record failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _front_matter_value(raw_value: str) -> object:
    value = raw_value.strip()
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    return value


def _parse_markdown_header(path: Path, payload: bytes) -> CorpusDocumentHeader:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_DOCUMENT_NOT_UTF8",
            safe_message="Corpus document is not valid UTF-8.",
            path=str(path),
        ) from exc

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise CorpusFreezeError(
            error_code="CORPUS_MARKDOWN_METADATA_MISSING",
            safe_message="Markdown corpus document is missing front matter.",
            path=str(path),
        )

    try:
        closing_index = lines[1:].index("---") + 1
    except ValueError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_MARKDOWN_METADATA_UNCLOSED",
            safe_message="Markdown corpus document has unclosed front matter.",
            path=str(path),
        ) from exc

    raw_metadata: dict[str, object] = {}
    for line in lines[1:closing_index]:
        key, separator, raw_value = line.partition(":")
        if not separator or not key.strip():
            raise CorpusFreezeError(
                error_code="CORPUS_MARKDOWN_METADATA_INVALID",
                safe_message="Markdown corpus front matter contains an invalid line.",
                path=str(path),
            )
        raw_metadata[key.strip()] = _front_matter_value(raw_value)

    try:
        return CorpusDocumentHeader.model_validate(raw_metadata)
    except ValidationError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_DOCUMENT_HEADER_VALIDATION_FAILED",
            safe_message="Corpus document metadata failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _parse_json_header(path: Path, payload: bytes) -> CorpusDocumentHeader:
    try:
        raw_document = json.loads(payload.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_DOCUMENT_NOT_UTF8",
            safe_message="Corpus document is not valid UTF-8.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_DOCUMENT_INVALID_JSON",
            safe_message="JSON corpus document is malformed.",
            path=str(path),
        ) from exc

    try:
        return CorpusJsonDocument.model_validate(raw_document).metadata
    except ValidationError as exc:
        raise CorpusFreezeError(
            error_code="CORPUS_DOCUMENT_HEADER_VALIDATION_FAILED",
            safe_message="Corpus document metadata failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _expected_header(source: CorpusSource) -> CorpusDocumentHeader:
    return CorpusDocumentHeader(
        source_id=source.source_id,
        version=source.version,
        status=source.status,
        updated_at=source.updated_at,
        document_format=source.document_format,
        api_area=source.api_area,
        is_stale=source.is_stale,
        conflict_group_id=source.conflict_group_id,
        completeness=source.completeness,
        near_duplicate_group_id=source.near_duplicate_group_id,
        version_sensitive_procedure=source.version_sensitive_procedure,
    )


def _validate_document_content(path: Path, source: CorpusSource, payload: bytes) -> None:
    if not payload.strip():
        raise CorpusFreezeError(
            error_code="CORPUS_DOCUMENT_EMPTY",
            safe_message="Corpus document must not be empty.",
            path=str(path),
        )

    header = (
        _parse_markdown_header(path, payload)
        if source.document_format.value == "markdown"
        else _parse_json_header(path, payload)
    )
    if header != _expected_header(source):
        raise CorpusFreezeError(
            error_code="CORPUS_DOCUMENT_METADATA_MISMATCH",
            safe_message="Corpus document metadata does not match the source inventory.",
            path=str(path),
            details=(source.source_id,),
        )

    text = payload.decode("utf-8")
    for label, pattern in _FORBIDDEN_CONTENT_PATTERNS.items():
        if pattern.search(text) is not None:
            raise CorpusFreezeError(
                error_code="CORPUS_FORBIDDEN_SECRET_PATTERN",
                safe_message="Corpus document contains a forbidden secret-like pattern.",
                path=str(path),
                details=(label,),
            )

    uppercase_text = text.upper()
    if source.is_stale and not ("DEPRECATED" in uppercase_text or "SUPERSEDED" in uppercase_text):
        raise CorpusFreezeError(
            error_code="CORPUS_STALE_WARNING_MISSING",
            safe_message="Stale corpus document lacks an explicit lifecycle warning.",
            path=str(path),
        )
    if source.completeness.value == "incomplete" and "KNOWN GAP" not in uppercase_text:
        raise CorpusFreezeError(
            error_code="CORPUS_INCOMPLETE_GAP_MISSING",
            safe_message="Incomplete corpus document lacks an explicit known-gap section.",
            path=str(path),
        )


def _relative_document_paths(repo_root: Path) -> set[str]:
    documents_root = repo_root / _DOCUMENTS_ROOT
    if not documents_root.exists():
        return set()
    return {
        path.relative_to(repo_root).as_posix()
        for path in documents_root.rglob("*")
        if path.is_file() and path.suffix in _ALLOWED_SUFFIXES
    }


def build_source_manifest(repo_root: Path, inventory_path: Path) -> CorpusSourceManifest:
    """Build deterministic source hash evidence from the authored corpus."""

    absolute_inventory = repo_root / inventory_path
    inventory = _load_inventory(absolute_inventory)
    expected_paths = {source.document_path for source in inventory.sources}
    actual_paths = _relative_document_paths(repo_root)
    if expected_paths != actual_paths:
        missing = sorted(expected_paths - actual_paths)
        unexpected = sorted(actual_paths - expected_paths)
        raise CorpusFreezeError(
            error_code="CORPUS_DOCUMENT_SET_MISMATCH",
            safe_message="Authored corpus files do not match the frozen inventory.",
            path=str(repo_root / _DOCUMENTS_ROOT),
            details=tuple(
                [
                    *(f"missing:{item}" for item in missing),
                    *(f"extra:{item}" for item in unexpected),
                ]
            ),
        )

    artifacts: list[CorpusArtifactRecord] = []
    for source in sorted(inventory.sources, key=lambda item: item.document_path):
        path = repo_root / source.document_path
        payload = _read_bytes(path, "CORPUS_DOCUMENT_NOT_FOUND")
        _validate_document_content(path, source, payload)
        artifacts.append(
            CorpusArtifactRecord(
                source_id=source.source_id,
                document_path=source.document_path,
                document_format=source.document_format,
                byte_count=len(payload),
                sha256=_sha256_bytes(payload),
            )
        )

    inventory_payload = _read_bytes(absolute_inventory, "CORPUS_INVENTORY_NOT_FOUND")
    return CorpusSourceManifest(
        schema_version="1.0.0",
        corpus_id=inventory.corpus_id,
        corpus_version=inventory.corpus_version,
        status=CorpusFreezeStatus.FROZEN,
        inventory_path=inventory_path.as_posix(),
        inventory_sha256=_sha256_bytes(inventory_payload),
        artifacts=tuple(artifacts),
    )


def _canonical_json_bytes(model: BaseModel) -> bytes:
    return (model.model_dump_json(indent=2) + "\n").encode("utf-8")


def build_freeze_record(
    manifest: CorpusSourceManifest,
    manifest_path: Path,
    freeze_date: date,
) -> CorpusFreezeRecord:
    """Build the top-level freeze identity for a source manifest."""

    manifest_payload = _canonical_json_bytes(manifest)
    return CorpusFreezeRecord(
        schema_version="1.0.0",
        corpus_id=manifest.corpus_id,
        corpus_version=manifest.corpus_version,
        status=CorpusFreezeStatus.FROZEN,
        freeze_date=freeze_date,
        inventory_path=manifest.inventory_path,
        inventory_sha256=manifest.inventory_sha256,
        manifest_path=manifest_path.as_posix(),
        manifest_sha256=_sha256_bytes(manifest_payload),
        document_count=len(manifest.artifacts),
        total_document_bytes=sum(artifact.byte_count for artifact in manifest.artifacts),
    )


def write_freeze_assets(
    repo_root: Path,
    inventory_path: Path = _DEFAULT_INVENTORY,
    manifest_path: Path = _DEFAULT_MANIFEST,
    freeze_record_path: Path = _DEFAULT_FREEZE_RECORD,
    freeze_date: date = date(2026, 7, 12),
) -> CorpusFreezeSummary:
    """Build and write deterministic manifest and freeze-record files."""

    manifest = build_source_manifest(repo_root, inventory_path)
    absolute_manifest = repo_root / manifest_path
    absolute_manifest.parent.mkdir(parents=True, exist_ok=True)
    absolute_manifest.write_bytes(_canonical_json_bytes(manifest))

    freeze_record = build_freeze_record(manifest, manifest_path, freeze_date)
    absolute_freeze_record = repo_root / freeze_record_path
    absolute_freeze_record.parent.mkdir(parents=True, exist_ok=True)
    absolute_freeze_record.write_bytes(_canonical_json_bytes(freeze_record))

    return verify_frozen_corpus(repo_root, inventory_path, manifest_path, freeze_record_path)


def verify_frozen_corpus(
    repo_root: Path,
    inventory_path: Path = _DEFAULT_INVENTORY,
    manifest_path: Path = _DEFAULT_MANIFEST,
    freeze_record_path: Path = _DEFAULT_FREEZE_RECORD,
) -> CorpusFreezeSummary:
    """Verify documents, embedded metadata, hashes, and freeze evidence."""

    inventory = _load_inventory(repo_root / inventory_path)
    expected_manifest = build_source_manifest(repo_root, inventory_path)
    persisted_manifest = _load_manifest(repo_root / manifest_path)
    if persisted_manifest != expected_manifest:
        raise CorpusFreezeError(
            error_code="CORPUS_SOURCE_MANIFEST_MISMATCH",
            safe_message="Persisted corpus source manifest does not match authored documents.",
            path=str(repo_root / manifest_path),
        )

    persisted_manifest_payload = _read_bytes(
        repo_root / manifest_path, "CORPUS_SOURCE_MANIFEST_NOT_FOUND"
    )
    freeze_record = _load_freeze_record(repo_root / freeze_record_path)
    expected_manifest_hash = _sha256_bytes(persisted_manifest_payload)

    expected_record_values = {
        "corpus_id": persisted_manifest.corpus_id,
        "corpus_version": persisted_manifest.corpus_version,
        "inventory_path": inventory_path.as_posix(),
        "inventory_sha256": persisted_manifest.inventory_sha256,
        "manifest_path": manifest_path.as_posix(),
        "manifest_sha256": expected_manifest_hash,
        "document_count": len(persisted_manifest.artifacts),
        "total_document_bytes": sum(
            artifact.byte_count for artifact in persisted_manifest.artifacts
        ),
    }
    mismatches = tuple(
        field_name
        for field_name, expected_value in expected_record_values.items()
        if getattr(freeze_record, field_name) != expected_value
    )
    if mismatches:
        raise CorpusFreezeError(
            error_code="CORPUS_FREEZE_RECORD_MISMATCH",
            safe_message="Corpus freeze record does not match the persisted source evidence.",
            path=str(repo_root / freeze_record_path),
            details=mismatches,
        )

    summary = inventory.validation_summary()
    return CorpusFreezeSummary(
        schema_version=freeze_record.schema_version,
        corpus_id=inventory.corpus_id,
        corpus_version=inventory.corpus_version,
        status=freeze_record.status,
        document_count=freeze_record.document_count,
        total_document_bytes=freeze_record.total_document_bytes,
        inventory_sha256=freeze_record.inventory_sha256,
        manifest_sha256=freeze_record.manifest_sha256,
        stale_document_count=summary.stale_document_count,
        conflicting_document_count=summary.conflicting_document_count,
        incomplete_document_count=summary.incomplete_document_count,
        near_duplicate_document_count=summary.near_duplicate_document_count,
        version_sensitive_document_count=summary.version_sensitive_document_count,
        validation_status="valid",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, default=Path("."))
        subparser.add_argument("--inventory", type=Path, default=_DEFAULT_INVENTORY)
        subparser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
        subparser.add_argument("--freeze-record", type=Path, default=_DEFAULT_FREEZE_RECORD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for deterministic build and verification."""

    args = _parse_args(argv)
    repo_root: Path = args.repo_root.resolve()
    try:
        if args.command == "build":
            summary = write_freeze_assets(
                repo_root,
                inventory_path=args.inventory,
                manifest_path=args.manifest,
                freeze_record_path=args.freeze_record,
            )
        else:
            summary = verify_frozen_corpus(
                repo_root,
                inventory_path=args.inventory,
                manifest_path=args.manifest,
                freeze_record_path=args.freeze_record,
            )
    except CorpusFreezeError as exc:
        error = CorpusFreezeErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(error.model_dump_json(indent=2), file=sys.stderr)
        return 2

    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
