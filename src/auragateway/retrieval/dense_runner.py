"""Build and verify deterministic local dense retrieval candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.chunking.runner import (
    FIXED_WINDOW_CONFIG,
    SECTION_AWARE_CONFIG,
    ChunkingError,
)
from auragateway.chunking.runner import (
    verify_candidate as verify_chunking_candidate,
)
from auragateway.contracts.chunking import (
    ChunkingConfiguration,
    ChunkingManifest,
    CorpusChunk,
)
from auragateway.contracts.dense_retrieval import (
    DenseIndexManifest,
    DenseRetrievalConfiguration,
    DenseRunSummary,
)
from auragateway.contracts.retrieval import RetrievalSmokeQuerySet
from auragateway.retrieval.dense import DenseIndex, to_dense_evidence_result

_DEFAULT_SMOKE_QUERIES: Final = Path("data/retrieval/bm25-v1/smoke_queries.json")
_DEFAULT_OUTPUT_ROOT: Final = Path("data/retrieval/hashed-tfidf-dense-v1")
_DEFAULT_CHUNKING_ROOT: Final = Path("data/chunking")

FIXED_WINDOW_DENSE_CONFIG: Final = DenseRetrievalConfiguration(
    config_id="dense-hashed-tfidf-fixed-window-v1",
    chunking_config_id=FIXED_WINDOW_CONFIG.config_id,
)

SECTION_AWARE_DENSE_CONFIG: Final = DenseRetrievalConfiguration(
    config_id="dense-hashed-tfidf-section-aware-v1",
    chunking_config_id=SECTION_AWARE_CONFIG.config_id,
)


class DenseRetrievalError(Exception):
    """Expected dense retrieval failure with a safe machine-readable envelope."""

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


class DenseRetrievalErrorEnvelope(BaseModel):
    """Safe CLI failure output without document, query, or vector content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _model_json_bytes(model: BaseModel) -> bytes:
    return (model.model_dump_json(indent=2) + "\n").encode("utf-8")


def _config_sha256(config: DenseRetrievalConfiguration) -> str:
    return _sha256_bytes(_canonical_json_bytes(config.model_dump(mode="json")))


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, not_found_code: str) -> object:
    try:
        payload = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DenseRetrievalError(
            error_code=not_found_code,
            safe_message="Required dense retrieval input was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_INPUT_INVALID_JSON",
            safe_message="Dense retrieval input is not valid JSON.",
            path=str(path),
        ) from exc


def _load_smoke_queries(path: Path) -> RetrievalSmokeQuerySet:
    try:
        return RetrievalSmokeQuerySet.model_validate(
            _load_json(path, "DENSE_RETRIEVAL_SMOKE_QUERIES_NOT_FOUND")
        )
    except ValidationError as exc:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_SMOKE_QUERIES_VALIDATION_FAILED",
            safe_message="Smoke-query input failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _load_chunking_manifest(path: Path) -> ChunkingManifest:
    try:
        return ChunkingManifest.model_validate(
            _load_json(path, "DENSE_RETRIEVAL_CHUNKING_MANIFEST_NOT_FOUND")
        )
    except ValidationError as exc:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_CHUNKING_MANIFEST_VALIDATION_FAILED",
            safe_message="Chunking manifest failed typed validation at the dense boundary.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _load_chunks(path: Path) -> tuple[CorpusChunk, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_CHUNKS_NOT_FOUND",
            safe_message="Chunking output was not found.",
            path=str(path),
        ) from exc

    chunks: list[CorpusChunk] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            chunks.append(CorpusChunk.model_validate_json(line))
        except ValidationError as exc:
            raise DenseRetrievalError(
                error_code="DENSE_RETRIEVAL_CHUNK_VALIDATION_FAILED",
                safe_message="A persisted chunk failed typed validation.",
                path=str(path),
                details=(f"line {line_number}", *_validation_messages(exc)),
            ) from exc
    if not chunks:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_CHUNKS_EMPTY",
            safe_message="Chunking output contains no chunks.",
            path=str(path),
        )
    return tuple(chunks)


def _smoke_results_jsonl(index: DenseIndex, query_set: RetrievalSmokeQuerySet) -> bytes:
    evidence = tuple(to_dense_evidence_result(index.search(query)) for query in query_set.queries)
    lines = [result.model_dump_json() for result in evidence]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _chunking_config_for_dense(
    config: DenseRetrievalConfiguration,
) -> ChunkingConfiguration:
    mapping = {
        FIXED_WINDOW_CONFIG.config_id: FIXED_WINDOW_CONFIG,
        SECTION_AWARE_CONFIG.config_id: SECTION_AWARE_CONFIG,
    }
    try:
        return mapping[config.chunking_config_id]
    except KeyError as exc:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_CHUNKING_CONFIG_UNSUPPORTED",
            safe_message="Dense configuration references an unsupported chunking candidate.",
            details=(config.chunking_config_id,),
        ) from exc


def build_candidate(
    repo_root: Path,
    config: DenseRetrievalConfiguration,
    smoke_queries_path: Path = _DEFAULT_SMOKE_QUERIES,
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
) -> tuple[DenseIndexManifest, bytes]:
    """Build one dense candidate and development smoke evidence in memory."""

    chunking_config = _chunking_config_for_dense(config)
    try:
        verify_chunking_candidate(repo_root, chunking_config)
    except ChunkingError as exc:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_CHUNKING_CANDIDATE_INVALID",
            safe_message="Chunking candidate verification failed before dense indexing.",
            path=exc.path,
            details=(exc.error_code, *exc.details),
        ) from exc

    chunking_root = _DEFAULT_CHUNKING_ROOT / config.chunking_config_id
    chunking_manifest_path = chunking_root / "manifest.json"
    chunking_manifest_file = repo_root / chunking_manifest_path
    chunking_manifest = _load_chunking_manifest(chunking_manifest_file)
    chunks_path = Path(chunking_manifest.chunks_path)
    chunks_file = repo_root / chunks_path
    chunks = _load_chunks(chunks_file)
    query_file = repo_root / smoke_queries_path
    query_set = _load_smoke_queries(query_file)

    index = DenseIndex(chunks, config)
    smoke_results = _smoke_results_jsonl(index, query_set)
    candidate_root = output_root / config.chunking_config_id
    smoke_results_path = candidate_root / "smoke_results.jsonl"
    manifest = DenseIndexManifest(
        corpus_id=chunking_manifest.corpus_id,
        corpus_version=chunking_manifest.corpus_version,
        config=config,
        config_sha256=_config_sha256(config),
        chunking_manifest_path=chunking_manifest_path.as_posix(),
        chunking_manifest_sha256=_sha256_bytes(chunking_manifest_file.read_bytes()),
        chunks_path=chunks_path.as_posix(),
        chunks_sha256=_sha256_bytes(chunks_file.read_bytes()),
        smoke_queries_path=smoke_queries_path.as_posix(),
        smoke_queries_sha256=_sha256_bytes(query_file.read_bytes()),
        smoke_results_path=smoke_results_path.as_posix(),
        smoke_results_sha256=_sha256_bytes(smoke_results),
        source_document_count=index.source_document_count,
        chunk_count=index.chunk_count,
        vocabulary_size=index.vocabulary_size,
        vector_dimension=config.vector_dimension,
        average_nonzero_dimensions=round(
            index.average_nonzero_dimensions,
            config.score_precision,
        ),
        smoke_query_count=len(query_set.queries),
    )
    return manifest, smoke_results


def _summary(manifest: DenseIndexManifest) -> DenseRunSummary:
    return DenseRunSummary(
        corpus_id=manifest.corpus_id,
        corpus_version=manifest.corpus_version,
        retriever_config_id=manifest.config.config_id,
        retriever_config_sha256=manifest.config_sha256,
        chunking_config_id=manifest.config.chunking_config_id,
        source_document_count=manifest.source_document_count,
        chunk_count=manifest.chunk_count,
        vocabulary_size=manifest.vocabulary_size,
        vector_dimension=manifest.vector_dimension,
        average_nonzero_dimensions=manifest.average_nonzero_dimensions,
        smoke_query_count=manifest.smoke_query_count,
        smoke_results_sha256=manifest.smoke_results_sha256,
        validation_status="valid",
    )


def write_candidate(
    repo_root: Path,
    config: DenseRetrievalConfiguration,
) -> DenseRunSummary:
    """Build and persist one dense candidate manifest and smoke result set."""

    manifest, smoke_results = build_candidate(repo_root, config)
    candidate_root = repo_root / _DEFAULT_OUTPUT_ROOT / config.chunking_config_id
    candidate_root.mkdir(parents=True, exist_ok=True)
    (candidate_root / "smoke_results.jsonl").write_bytes(smoke_results)
    (candidate_root / "manifest.json").write_bytes(_model_json_bytes(manifest))
    return _summary(manifest)


def verify_candidate(
    repo_root: Path,
    config: DenseRetrievalConfiguration,
) -> DenseRunSummary:
    """Rebuild one dense candidate and compare persisted deterministic evidence."""

    expected_manifest, expected_results = build_candidate(repo_root, config)
    candidate_root = repo_root / _DEFAULT_OUTPUT_ROOT / config.chunking_config_id
    manifest_path = candidate_root / "manifest.json"
    results_path = candidate_root / "smoke_results.jsonl"
    try:
        persisted_manifest = DenseIndexManifest.model_validate(
            _load_json(manifest_path, "DENSE_RETRIEVAL_MANIFEST_NOT_FOUND")
        )
    except ValidationError as exc:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_MANIFEST_VALIDATION_FAILED",
            safe_message="Persisted dense retrieval manifest failed typed validation.",
            path=str(manifest_path),
            details=_validation_messages(exc),
        ) from exc
    try:
        persisted_results = results_path.read_bytes()
    except FileNotFoundError as exc:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_SMOKE_RESULTS_NOT_FOUND",
            safe_message="Persisted dense smoke results were not found.",
            path=str(results_path),
        ) from exc

    if persisted_manifest != expected_manifest:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_MANIFEST_MISMATCH",
            safe_message="Persisted dense manifest does not match deterministic output.",
            path=str(manifest_path),
        )
    if persisted_results != expected_results:
        raise DenseRetrievalError(
            error_code="DENSE_RETRIEVAL_SMOKE_RESULTS_MISMATCH",
            safe_message="Persisted dense smoke results do not match deterministic output.",
            path=str(results_path),
        )
    return _summary(expected_manifest)


def build_all_candidates(repo_root: Path) -> tuple[DenseRunSummary, ...]:
    """Persist dense candidates over both Phase 1 chunking strategies."""

    return tuple(
        write_candidate(repo_root, config)
        for config in (FIXED_WINDOW_DENSE_CONFIG, SECTION_AWARE_DENSE_CONFIG)
    )


def verify_all_candidates(repo_root: Path) -> tuple[DenseRunSummary, ...]:
    """Verify dense candidates over both Phase 1 chunking strategies."""

    return tuple(
        verify_candidate(repo_root, config)
        for config in (FIXED_WINDOW_DENSE_CONFIG, SECTION_AWARE_DENSE_CONFIG)
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for deterministic dense retrieval candidates."""

    args = _parse_args(argv)
    try:
        summaries = (
            build_all_candidates(args.repo_root)
            if args.command == "build"
            else verify_all_candidates(args.repo_root)
        )
    except DenseRetrievalError as exc:
        envelope = DenseRetrievalErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 2
    print(json.dumps([summary.model_dump(mode="json") for summary in summaries], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
