"""Build and verify deterministic chunking candidates over the frozen corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.chunking import (
    ChunkingConfiguration,
    ChunkingManifest,
    ChunkingRunSummary,
    ChunkingStrategy,
    CorpusChunk,
    SourceChunkCount,
)
from auragateway.contracts.corpus import CorpusInventory, CorpusSource, DocumentFormat
from auragateway.contracts.corpus_freeze import CorpusSourceManifest
from auragateway.corpus.freeze import CorpusFreezeError, verify_frozen_corpus

_DEFAULT_INVENTORY: Final = Path("data/corpus/source_inventory.json")
_DEFAULT_CORPUS_MANIFEST: Final = Path("data/corpus/source_manifest.json")
_DEFAULT_OUTPUT_ROOT: Final = Path("data/chunking")
_TOKEN_PATTERN: Final = re.compile(r"\S+")
_HEADING_PATTERN: Final = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

FIXED_WINDOW_CONFIG: Final = ChunkingConfiguration(
    config_id="fixed-window-v1",
    strategy=ChunkingStrategy.FIXED_WINDOW,
    target_tokens=96,
    overlap_tokens=16,
    minimum_fallback_tokens=24,
    preserve_parent_headings=False,
)

SECTION_AWARE_CONFIG: Final = ChunkingConfiguration(
    config_id="section-aware-v1",
    strategy=ChunkingStrategy.SECTION_AWARE,
    target_tokens=96,
    overlap_tokens=16,
    minimum_fallback_tokens=24,
    preserve_parent_headings=True,
)


class ChunkingError(Exception):
    """Expected chunking failure with a safe error envelope."""

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


class ChunkingErrorEnvelope(BaseModel):
    """Safe machine-readable CLI failure output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LoadedDocument:
    """Validated source metadata and retrieval-visible body text."""

    source: CorpusSource
    body: str


@dataclass(frozen=True, slots=True)
class TextSection:
    """One section-aware unit before bounded fallback splitting."""

    parent_headings: tuple[str, ...]
    content: str


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _model_json_bytes(model: BaseModel) -> bytes:
    return (model.model_dump_json(indent=2) + "\n").encode("utf-8")


def _load_json(path: Path, error_code: str) -> object:
    try:
        payload = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ChunkingError(
            error_code=error_code,
            safe_message="Required chunking input was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ChunkingError(
            error_code="CHUNKING_INPUT_INVALID_JSON",
            safe_message="Chunking input is not valid JSON.",
            path=str(path),
        ) from exc


def _load_inventory(path: Path) -> CorpusInventory:
    try:
        return CorpusInventory.model_validate(_load_json(path, "CHUNKING_INVENTORY_NOT_FOUND"))
    except ValidationError as exc:
        raise ChunkingError(
            error_code="CHUNKING_INVENTORY_VALIDATION_FAILED",
            safe_message="Corpus inventory failed typed validation at the chunking boundary.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _load_corpus_manifest(path: Path) -> CorpusSourceManifest:
    try:
        return CorpusSourceManifest.model_validate(
            _load_json(path, "CHUNKING_CORPUS_MANIFEST_NOT_FOUND")
        )
    except ValidationError as exc:
        raise ChunkingError(
            error_code="CHUNKING_CORPUS_MANIFEST_VALIDATION_FAILED",
            safe_message="Corpus source manifest failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def lexical_token_count(text: str) -> int:
    """Count deterministic provider-neutral lexical tokens."""

    return len(_TOKEN_PATTERN.findall(text))


def _window_text(
    text: str,
    target_tokens: int,
    overlap_tokens: int,
    minimum_fallback_tokens: int,
) -> tuple[str, ...]:
    matches = list(_TOKEN_PATTERN.finditer(text))
    if not matches:
        return ()
    if len(matches) <= target_tokens:
        return (text.strip(),)

    step = target_tokens - overlap_tokens
    starts = list(range(0, len(matches), step))
    starts = [start for start in starts if start < len(matches)]
    if len(matches) - starts[-1] < minimum_fallback_tokens and len(starts) > 1:
        starts[-1] = max(starts[-2] + 1, len(matches) - target_tokens)
    starts = list(dict.fromkeys(starts))

    chunks: list[str] = []
    for start in starts:
        end = min(start + target_tokens, len(matches))
        start_character = matches[start].start()
        end_character = matches[end - 1].end()
        chunk = text[start_character:end_character].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(matches):
            break
    return tuple(chunks)


def _strip_markdown_front_matter(text: str, path: Path) -> str:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ChunkingError(
            error_code="CHUNKING_MARKDOWN_METADATA_MISSING",
            safe_message="Markdown source is missing expected front matter.",
            path=str(path),
        )
    try:
        closing_index = lines[1:].index("---") + 1
    except ValueError as exc:
        raise ChunkingError(
            error_code="CHUNKING_MARKDOWN_METADATA_UNCLOSED",
            safe_message="Markdown source has unclosed front matter.",
            path=str(path),
        ) from exc
    return "\n".join(lines[closing_index + 1 :]).strip()


def _markdown_sections(body: str) -> tuple[TextSection, ...]:
    lines = body.splitlines()
    sections: list[TextSection] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []
    current_headings: tuple[str, ...] = ()

    def flush() -> None:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append(TextSection(parent_headings=current_headings, content=content))

    for line in lines:
        match = _HEADING_PATTERN.match(line)
        if match is None:
            current_lines.append(line)
            continue

        flush()
        level = len(match.group(1))
        title = match.group(2).strip()
        del heading_stack[level - 1 :]
        heading_stack.append(title)
        current_headings = tuple(heading_stack)
        current_lines = [line]

    flush()
    return tuple(sections)


def _json_sections(
    payload: object,
    path: Path,
    minimum_section_tokens: int,
) -> tuple[TextSection, ...]:
    if not isinstance(payload, dict) or "content" not in payload:
        raise ChunkingError(
            error_code="CHUNKING_JSON_CONTENT_MISSING",
            safe_message="JSON corpus source is missing its content field.",
            path=str(path),
        )
    content = payload["content"]
    if not isinstance(content, dict):
        return (
            TextSection(
                parent_headings=("content",),
                content=json.dumps(content, sort_keys=True, indent=2, ensure_ascii=False),
            ),
        )

    sections: list[TextSection] = []
    small_fields: dict[str, object] = {}
    for key, value in sorted(content.items(), key=lambda item: str(item[0])):
        section_content = json.dumps(
            {key: value},
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        if lexical_token_count(section_content) < minimum_section_tokens:
            small_fields[str(key)] = value
            continue
        sections.append(
            TextSection(
                parent_headings=(str(key),),
                content=section_content,
            )
        )

    if small_fields:
        sections.append(
            TextSection(
                parent_headings=("document_fields",),
                content=json.dumps(
                    small_fields,
                    sort_keys=True,
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        )
    return tuple(sections)


def _load_document(repo_root: Path, source: CorpusSource) -> LoadedDocument:
    path = repo_root / source.document_path
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ChunkingError(
            error_code="CHUNKING_SOURCE_NOT_FOUND",
            safe_message="Frozen corpus source was not found.",
            path=str(path),
            details=(source.source_id,),
        ) from exc
    if source.document_format is DocumentFormat.MARKDOWN:
        body = _strip_markdown_front_matter(text, path)
    else:
        raw_json = _load_json(path, "CHUNKING_SOURCE_NOT_FOUND")
        if not isinstance(raw_json, dict) or "content" not in raw_json:
            raise ChunkingError(
                error_code="CHUNKING_JSON_CONTENT_MISSING",
                safe_message="JSON corpus source is missing its content field.",
                path=str(path),
            )
        body = json.dumps(
            raw_json["content"],
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
    if not body.strip():
        raise ChunkingError(
            error_code="CHUNKING_SOURCE_BODY_EMPTY",
            safe_message="Corpus source has no retrieval-visible body content.",
            path=str(path),
        )
    return LoadedDocument(source=source, body=body)


def _config_sha256(config: ChunkingConfiguration) -> str:
    return _sha256_bytes(_canonical_json_bytes(config.model_dump(mode="json")))


def _chunk_id(
    source_id: str,
    config_sha256: str,
    chunk_index: int,
    parent_headings: tuple[str, ...],
    content_sha256: str,
) -> str:
    identity = {
        "source_id": source_id,
        "config_sha256": config_sha256,
        "chunk_index": chunk_index,
        "parent_headings": parent_headings,
        "content_sha256": content_sha256,
    }
    return f"chunk-{_sha256_bytes(_canonical_json_bytes(identity))[:24]}"


def _make_chunk(
    document: LoadedDocument,
    config: ChunkingConfiguration,
    config_sha256: str,
    chunk_index: int,
    parent_headings: tuple[str, ...],
    content: str,
) -> CorpusChunk:
    normalized_content = content.strip()
    content_sha256 = _sha256_bytes(normalized_content.encode("utf-8"))
    source = document.source
    return CorpusChunk(
        chunk_id=_chunk_id(
            source.source_id,
            config_sha256,
            chunk_index,
            parent_headings,
            content_sha256,
        ),
        source_id=source.source_id,
        document_path=source.document_path,
        source_version=source.version,
        document_format=source.document_format,
        api_area=source.api_area,
        source_status=source.status,
        is_stale=source.is_stale,
        conflict_group_id=source.conflict_group_id,
        completeness=source.completeness,
        near_duplicate_group_id=source.near_duplicate_group_id,
        version_sensitive_procedure=source.version_sensitive_procedure,
        strategy=config.strategy,
        config_id=config.config_id,
        config_sha256=config_sha256,
        chunk_index=chunk_index,
        parent_headings=parent_headings,
        content=normalized_content,
        token_count=lexical_token_count(normalized_content),
        character_count=len(normalized_content),
        content_sha256=content_sha256,
    )


def chunk_fixed_window(
    document: LoadedDocument,
    config: ChunkingConfiguration = FIXED_WINDOW_CONFIG,
) -> tuple[CorpusChunk, ...]:
    """Chunk one validated source with deterministic lexical windows."""

    if config.strategy is not ChunkingStrategy.FIXED_WINDOW:
        raise ValueError("fixed-window chunker requires a fixed-window configuration")
    config_sha256 = _config_sha256(config)
    windows = _window_text(
        document.body,
        config.target_tokens,
        config.overlap_tokens,
        config.minimum_fallback_tokens,
    )
    return tuple(
        _make_chunk(document, config, config_sha256, index, (), content)
        for index, content in enumerate(windows)
    )


def _sections_for_document(
    repo_root: Path,
    document: LoadedDocument,
    config: ChunkingConfiguration,
) -> tuple[TextSection, ...]:
    path = repo_root / document.source.document_path
    if document.source.document_format is DocumentFormat.MARKDOWN:
        return _markdown_sections(document.body)
    return _json_sections(
        _load_json(path, "CHUNKING_SOURCE_NOT_FOUND"),
        path,
        config.minimum_fallback_tokens,
    )


def chunk_section_aware(
    repo_root: Path,
    document: LoadedDocument,
    config: ChunkingConfiguration = SECTION_AWARE_CONFIG,
) -> tuple[CorpusChunk, ...]:
    """Chunk one source by structural section with bounded fallback windows."""

    if config.strategy is not ChunkingStrategy.SECTION_AWARE:
        raise ValueError("section-aware chunker requires a section-aware configuration")
    config_sha256 = _config_sha256(config)
    chunks: list[CorpusChunk] = []
    for section in _sections_for_document(repo_root, document, config):
        windows = _window_text(
            section.content,
            config.target_tokens,
            config.overlap_tokens,
            config.minimum_fallback_tokens,
        )
        for content in windows:
            chunks.append(
                _make_chunk(
                    document,
                    config,
                    config_sha256,
                    len(chunks),
                    section.parent_headings,
                    content,
                )
            )
    return tuple(chunks)


def _chunks_jsonl(chunks: Iterable[CorpusChunk]) -> bytes:
    lines = [chunk.model_dump_json() for chunk in chunks]
    return (("\n".join(lines) + "\n") if lines else "").encode("utf-8")


def build_candidate(
    repo_root: Path,
    config: ChunkingConfiguration,
    inventory_path: Path = _DEFAULT_INVENTORY,
    corpus_manifest_path: Path = _DEFAULT_CORPUS_MANIFEST,
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
) -> tuple[ChunkingManifest, bytes]:
    """Build one deterministic chunking candidate in memory."""

    try:
        verify_frozen_corpus(repo_root)
    except CorpusFreezeError as exc:
        raise ChunkingError(
            error_code="CHUNKING_FROZEN_CORPUS_INVALID",
            safe_message="Frozen corpus verification failed before chunking.",
            path=exc.path,
            details=(exc.error_code, *exc.details),
        ) from exc

    inventory = _load_inventory(repo_root / inventory_path)
    corpus_manifest = _load_corpus_manifest(repo_root / corpus_manifest_path)
    corpus_manifest_payload = (repo_root / corpus_manifest_path).read_bytes()
    documents = tuple(
        _load_document(repo_root, source)
        for source in sorted(inventory.sources, key=lambda item: item.source_id)
    )

    chunks: list[CorpusChunk] = []
    source_counts: list[SourceChunkCount] = []
    for document in documents:
        source_chunks = (
            chunk_fixed_window(document, config)
            if config.strategy is ChunkingStrategy.FIXED_WINDOW
            else chunk_section_aware(repo_root, document, config)
        )
        if not source_chunks:
            raise ChunkingError(
                error_code="CHUNKING_SOURCE_PRODUCED_NO_CHUNKS",
                safe_message="A frozen source produced no chunking output.",
                path=document.source.document_path,
                details=(document.source.source_id,),
            )
        chunks.extend(source_chunks)
        source_counts.append(
            SourceChunkCount(
                source_id=document.source.source_id,
                chunk_count=len(source_chunks),
            )
        )

    chunk_ids = [chunk.chunk_id for chunk in chunks]
    duplicate_ids = sorted(value for value, count in Counter(chunk_ids).items() if count > 1)
    if duplicate_ids:
        raise ChunkingError(
            error_code="CHUNKING_DUPLICATE_CHUNK_IDS",
            safe_message="Chunk generation produced duplicate chunk identifiers.",
            details=tuple(duplicate_ids),
        )

    config_sha256 = _config_sha256(config)
    chunks_payload = _chunks_jsonl(chunks)
    strategy_root = output_root / config.config_id
    chunks_path = strategy_root / "chunks.jsonl"
    manifest = ChunkingManifest(
        corpus_id=inventory.corpus_id,
        corpus_version=inventory.corpus_version,
        strategy=config.strategy,
        config=config,
        config_sha256=config_sha256,
        corpus_manifest_path=corpus_manifest_path.as_posix(),
        corpus_manifest_sha256=_sha256_bytes(corpus_manifest_payload),
        chunks_path=chunks_path.as_posix(),
        chunks_sha256=_sha256_bytes(chunks_payload),
        source_document_count=len(documents),
        chunk_count=len(chunks),
        total_chunk_tokens=sum(chunk.token_count for chunk in chunks),
        source_chunk_counts=tuple(source_counts),
    )
    if manifest.corpus_id != corpus_manifest.corpus_id:
        raise ChunkingError(
            error_code="CHUNKING_CORPUS_ID_MISMATCH",
            safe_message="Corpus inventory and source manifest identifiers do not match.",
        )
    return manifest, chunks_payload


def _summary(manifest: ChunkingManifest) -> ChunkingRunSummary:
    return ChunkingRunSummary(
        corpus_id=manifest.corpus_id,
        corpus_version=manifest.corpus_version,
        strategy=manifest.strategy,
        config_id=manifest.config.config_id,
        config_sha256=manifest.config_sha256,
        source_document_count=manifest.source_document_count,
        chunk_count=manifest.chunk_count,
        total_chunk_tokens=manifest.total_chunk_tokens,
        chunks_sha256=manifest.chunks_sha256,
        validation_status="valid",
    )


def write_candidate(repo_root: Path, config: ChunkingConfiguration) -> ChunkingRunSummary:
    """Build and persist one candidate manifest and JSONL chunk set."""

    manifest, chunks_payload = build_candidate(repo_root, config)
    strategy_root = repo_root / _DEFAULT_OUTPUT_ROOT / config.config_id
    strategy_root.mkdir(parents=True, exist_ok=True)
    (strategy_root / "chunks.jsonl").write_bytes(chunks_payload)
    (strategy_root / "manifest.json").write_bytes(_model_json_bytes(manifest))
    return _summary(manifest)


def verify_candidate(repo_root: Path, config: ChunkingConfiguration) -> ChunkingRunSummary:
    """Rebuild one candidate and compare it with persisted deterministic evidence."""

    expected_manifest, expected_chunks = build_candidate(repo_root, config)
    strategy_root = repo_root / _DEFAULT_OUTPUT_ROOT / config.config_id
    manifest_path = strategy_root / "manifest.json"
    chunks_path = strategy_root / "chunks.jsonl"
    try:
        persisted_manifest = ChunkingManifest.model_validate(
            _load_json(manifest_path, "CHUNKING_MANIFEST_NOT_FOUND")
        )
    except ValidationError as exc:
        raise ChunkingError(
            error_code="CHUNKING_MANIFEST_VALIDATION_FAILED",
            safe_message="Persisted chunking manifest failed typed validation.",
            path=str(manifest_path),
            details=_validation_messages(exc),
        ) from exc
    try:
        persisted_chunks = chunks_path.read_bytes()
    except FileNotFoundError as exc:
        raise ChunkingError(
            error_code="CHUNKING_OUTPUT_NOT_FOUND",
            safe_message="Persisted chunk output was not found.",
            path=str(chunks_path),
        ) from exc

    if persisted_manifest != expected_manifest:
        raise ChunkingError(
            error_code="CHUNKING_MANIFEST_MISMATCH",
            safe_message="Persisted chunking manifest does not match deterministic output.",
            path=str(manifest_path),
        )
    if persisted_chunks != expected_chunks:
        raise ChunkingError(
            error_code="CHUNKING_OUTPUT_MISMATCH",
            safe_message="Persisted chunks do not match deterministic output.",
            path=str(chunks_path),
        )
    return _summary(expected_manifest)


def build_all_candidates(repo_root: Path) -> tuple[ChunkingRunSummary, ...]:
    """Persist both required Phase 1 chunking candidates."""

    return tuple(
        write_candidate(repo_root, config) for config in (FIXED_WINDOW_CONFIG, SECTION_AWARE_CONFIG)
    )


def verify_all_candidates(repo_root: Path) -> tuple[ChunkingRunSummary, ...]:
    """Verify both required Phase 1 chunking candidates."""

    return tuple(
        verify_candidate(repo_root, config)
        for config in (FIXED_WINDOW_CONFIG, SECTION_AWARE_CONFIG)
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for deterministic candidate build and verification."""

    args = _parse_args(argv)
    try:
        summaries = (
            build_all_candidates(args.repo_root)
            if args.command == "build"
            else verify_all_candidates(args.repo_root)
        )
    except ChunkingError as exc:
        envelope = ChunkingErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 2

    print(
        json.dumps(
            [summary.model_dump(mode="json") for summary in summaries],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
