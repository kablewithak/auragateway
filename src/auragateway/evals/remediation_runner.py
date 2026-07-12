"""Build and verify retrieval metadata remediation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.chunking import CorpusChunk
from auragateway.contracts.dense_retrieval import DenseRetrievalConfiguration
from auragateway.contracts.retrieval import RetrievalConfiguration
from auragateway.contracts.retrieval_eval import (
    DevelopmentRetrievalSet,
    RejectedRetrievalSet,
    RetrievalCaseMetrics,
    RetrievalDevelopmentScorecard,
)
from auragateway.contracts.retrieval_metadata import SourceRetrievalMetadataRegistry
from auragateway.contracts.retrieval_remediation import (
    RemediationAlgorithm,
    RemediationScorecardReference,
    RetrievalRemediationManifest,
    RetrievalRemediationReport,
    RetrievalRemediationSummary,
)
from auragateway.evals.retrieval import aggregate_metrics, evaluate_cases
from auragateway.retrieval.bm25 import BM25Index
from auragateway.retrieval.dense import DenseIndex

_METADATA_PATH: Final = Path("data/retrieval/remediation-v1/source_metadata.json")
_DEVELOPMENT_V1_PATH: Final = Path("data/evals/retrieval/development-v1/accepted_cases.json")
_DEVELOPMENT_V2_PATH: Final = Path("data/evals/retrieval/development-v2/accepted_cases.json")
_REJECTED_V2_PATH: Final = Path("data/evals/retrieval/development-v2/rejected_cases.json")
_HELD_OUT_V1_PATH: Final = Path("data/evals/retrieval/held-out-v1/accepted_cases.json")
_OUTPUT_ROOT: Final = Path("data/evals/retrieval/remediation-v1")
_REPORT_PATH: Final = _OUTPUT_ROOT / "report.json"

_BM25_CONFIG: Final = RetrievalConfiguration(
    config_id="bm25-fixed-window-remediated-v2",
    chunking_config_id="fixed-window-v1",
)
_DENSE_CONFIG: Final = DenseRetrievalConfiguration(
    config_id="dense-hashed-tfidf-section-aware-remediated-v2",
    chunking_config_id="section-aware-v1",
)

_BASELINE_SCORECARDS: Final = (
    Path("data/evals/retrieval/development-v1/bm25-fixed-window-v1/scorecard.json"),
    Path("data/evals/retrieval/development-v1/dense-hashed-tfidf-section-aware-v1/scorecard.json"),
)


class RemediationError(Exception):
    """Expected remediation failure with safe evidence."""

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


class RemediationErrorEnvelope(BaseModel):
    """Safe CLI error output."""

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


def _model_hash(model: BaseModel) -> str:
    return _sha256_bytes(_canonical_json_bytes(model.model_dump(mode="json")))


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, code: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RemediationError(
            code, "Required remediation input was not found.", str(path)
        ) from exc
    except json.JSONDecodeError as exc:
        raise RemediationError(
            "REMEDIATION_INVALID_JSON",
            "Remediation input is not valid JSON.",
            str(path),
        ) from exc


def _load_model(path: Path, model_type: type[BaseModel], code: str) -> BaseModel:
    try:
        return model_type.model_validate(_load_json(path, code))
    except ValidationError as exc:
        raise RemediationError(
            "REMEDIATION_VALIDATION_FAILED",
            "Remediation input failed typed validation.",
            str(path),
            _validation_messages(exc),
        ) from exc


def _load_chunks(path: Path) -> tuple[CorpusChunk, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise RemediationError(
            "REMEDIATION_CHUNKS_NOT_FOUND",
            "Required chunking output was not found.",
            str(path),
        ) from exc
    chunks: list[CorpusChunk] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            chunks.append(CorpusChunk.model_validate_json(line))
        except ValidationError as exc:
            raise RemediationError(
                "REMEDIATION_CHUNK_VALIDATION_FAILED",
                "Persisted chunk failed typed validation.",
                str(path),
                (f"line {line_number}", *_validation_messages(exc)),
            ) from exc
    if not chunks:
        raise RemediationError(
            "REMEDIATION_CHUNKS_EMPTY",
            "Required chunking output contains no chunks.",
            str(path),
        )
    return tuple(chunks)


def _case_results_bytes(results: tuple[RetrievalCaseMetrics, ...]) -> bytes:
    return ("\n".join(result.model_dump_json() for result in results) + "\n").encode("utf-8")


def _load_registry(repo_root: Path) -> SourceRetrievalMetadataRegistry:
    registry = _load_model(
        repo_root / _METADATA_PATH,
        SourceRetrievalMetadataRegistry,
        "REMEDIATION_METADATA_NOT_FOUND",
    )
    assert isinstance(registry, SourceRetrievalMetadataRegistry)
    manifest_file = repo_root / registry.corpus_manifest_path
    try:
        manifest_hash = _sha256_bytes(manifest_file.read_bytes())
    except FileNotFoundError as exc:
        raise RemediationError(
            "REMEDIATION_CORPUS_MANIFEST_NOT_FOUND",
            "Frozen corpus manifest was not found.",
            str(manifest_file),
        ) from exc
    if manifest_hash != registry.corpus_manifest_sha256:
        raise RemediationError(
            "REMEDIATION_CORPUS_MANIFEST_MISMATCH",
            "Source metadata registry does not match the frozen corpus manifest.",
            str(manifest_file),
        )
    return registry


def _candidate_specs() -> tuple[
    tuple[
        RemediationAlgorithm,
        RetrievalConfiguration | DenseRetrievalConfiguration,
        Path,
    ],
    ...,
]:
    return (
        (
            RemediationAlgorithm.BM25,
            _BM25_CONFIG,
            Path("data/chunking/fixed-window-v1/chunks.jsonl"),
        ),
        (
            RemediationAlgorithm.DENSE_HASHED_TFIDF,
            _DENSE_CONFIG,
            Path("data/chunking/section-aware-v1/chunks.jsonl"),
        ),
    )


def _build_candidate(
    repo_root: Path,
    algorithm: RemediationAlgorithm,
    config: RetrievalConfiguration | DenseRetrievalConfiguration,
    chunks_path: Path,
    development_set: DevelopmentRetrievalSet,
    rejected_set: RejectedRetrievalSet,
    registry: SourceRetrievalMetadataRegistry,
) -> tuple[RetrievalRemediationManifest, RetrievalDevelopmentScorecard, bytes]:
    chunks_file = repo_root / chunks_path
    chunks = _load_chunks(chunks_file)
    metadata = registry.by_source_id()
    chunk_source_ids = {chunk.source_id for chunk in chunks}
    metadata_source_ids = set(metadata)
    if chunk_source_ids != metadata_source_ids:
        missing = sorted(chunk_source_ids - metadata_source_ids)
        extra = sorted(metadata_source_ids - chunk_source_ids)
        raise RemediationError(
            "REMEDIATION_METADATA_COVERAGE_MISMATCH",
            "Source metadata must exactly cover the frozen chunk source set.",
            details=(f"missing={missing}", f"extra={extra}"),
        )

    index: BM25Index | DenseIndex
    if isinstance(config, RetrievalConfiguration):
        index = BM25Index(chunks, config, metadata)
    else:
        index = DenseIndex(chunks, config, metadata)
    results = evaluate_cases(chunks, index, development_set.cases)
    results_bytes = _case_results_bytes(results)
    aggregate = aggregate_metrics(results)

    candidate_root = _OUTPUT_ROOT / config.config_id
    manifest_path = candidate_root / "manifest.json"
    results_path = candidate_root / "case_results.jsonl"
    manifest = RetrievalRemediationManifest(
        manifest_id=f"nimbus-relay-{config.config_id}-manifest",
        algorithm=algorithm,
        retriever_config_id=config.config_id,
        retriever_config_sha256=index.configuration_sha256,
        chunking_config_id=config.chunking_config_id,
        bm25_config=config if isinstance(config, RetrievalConfiguration) else None,
        dense_config=config if isinstance(config, DenseRetrievalConfiguration) else None,
        chunks_path=chunks_path.as_posix(),
        chunks_sha256=_sha256_bytes(chunks_file.read_bytes()),
        source_metadata_path=_METADATA_PATH.as_posix(),
        source_metadata_sha256=_sha256_bytes((repo_root / _METADATA_PATH).read_bytes()),
        development_set_path=_DEVELOPMENT_V2_PATH.as_posix(),
        development_set_sha256=_sha256_bytes((repo_root / _DEVELOPMENT_V2_PATH).read_bytes()),
        rejected_set_path=_REJECTED_V2_PATH.as_posix(),
        rejected_set_sha256=_sha256_bytes((repo_root / _REJECTED_V2_PATH).read_bytes()),
        source_document_count=len(chunk_source_ids),
        chunk_count=len(chunks),
    )
    manifest_bytes = _model_json_bytes(manifest)
    scorecard = RetrievalDevelopmentScorecard(
        scorecard_id=f"nimbus-relay-{config.config_id}-development-v2",
        status="development_remediated_candidate",
        retrieval_set_path=_DEVELOPMENT_V2_PATH.as_posix(),
        retrieval_set_sha256=_sha256_bytes((repo_root / _DEVELOPMENT_V2_PATH).read_bytes()),
        rejected_set_path=_REJECTED_V2_PATH.as_posix(),
        rejected_set_sha256=_sha256_bytes((repo_root / _REJECTED_V2_PATH).read_bytes()),
        retrieval_manifest_path=manifest_path.as_posix(),
        retrieval_manifest_sha256=_sha256_bytes(manifest_bytes),
        case_results_path=results_path.as_posix(),
        case_results_sha256=_sha256_bytes(results_bytes),
        retriever_config_id=config.config_id,
        retriever_config_sha256=index.configuration_sha256,
        chunking_config_id=config.chunking_config_id,
        aggregate=aggregate,
    )
    return manifest, scorecard, results_bytes


def _load_case_failures(path: Path) -> set[str]:
    failures: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise RemediationError(
            "REMEDIATION_CASE_RESULTS_NOT_FOUND",
            "Baseline case results were not found.",
            str(path),
        ) from exc
    for line in lines:
        if not line.strip():
            continue
        result = RetrievalCaseMetrics.model_validate_json(line)
        if not result.citation_support_ready:
            failures.add(result.case_id)
    return failures


def _scorecard_reference(
    repo_root: Path,
    stage: str,
    path: Path,
) -> RemediationScorecardReference:
    scorecard = _load_model(
        path=repo_root / path,
        model_type=RetrievalDevelopmentScorecard,
        code="REMEDIATION_SCORECARD_NOT_FOUND",
    )
    assert isinstance(scorecard, RetrievalDevelopmentScorecard)
    return RemediationScorecardReference(
        stage=stage,
        retriever_config_id=scorecard.retriever_config_id,
        scorecard_path=path.as_posix(),
        scorecard_sha256=_sha256_bytes((repo_root / path).read_bytes()),
        aggregate=scorecard.aggregate,
    )


def _build_all(
    repo_root: Path,
) -> tuple[tuple[RetrievalRemediationManifest, RetrievalDevelopmentScorecard, bytes], ...]:
    registry = _load_registry(repo_root)
    development_set = _load_model(
        repo_root / _DEVELOPMENT_V2_PATH,
        DevelopmentRetrievalSet,
        "REMEDIATION_DEVELOPMENT_SET_NOT_FOUND",
    )
    rejected_set = _load_model(
        repo_root / _REJECTED_V2_PATH,
        RejectedRetrievalSet,
        "REMEDIATION_REJECTED_SET_NOT_FOUND",
    )
    assert isinstance(development_set, DevelopmentRetrievalSet)
    assert isinstance(rejected_set, RejectedRetrievalSet)
    return tuple(
        _build_candidate(
            repo_root,
            algorithm,
            config,
            chunks_path,
            development_set,
            rejected_set,
            registry,
        )
        for algorithm, config, chunks_path in _candidate_specs()
    )


def _build_report(
    repo_root: Path,
    built: tuple[tuple[RetrievalRemediationManifest, RetrievalDevelopmentScorecard, bytes], ...],
) -> RetrievalRemediationReport:
    before_refs = tuple(
        _scorecard_reference(repo_root, "before", path) for path in _BASELINE_SCORECARDS
    )
    after_refs: list[RemediationScorecardReference] = []
    after_failures: set[str] = set()
    for _manifest, scorecard, results_bytes in built:
        candidate_root = _OUTPUT_ROOT / scorecard.retriever_config_id
        scorecard_path = candidate_root / "scorecard.json"
        after_refs.append(
            RemediationScorecardReference(
                stage="after",
                retriever_config_id=scorecard.retriever_config_id,
                scorecard_path=scorecard_path.as_posix(),
                scorecard_sha256=_sha256_bytes(_model_json_bytes(scorecard)),
                aggregate=scorecard.aggregate,
            )
        )
        for line in results_bytes.decode("utf-8").splitlines():
            result = RetrievalCaseMetrics.model_validate_json(line)
            if not result.citation_support_ready:
                after_failures.add(result.case_id)

    before_failures = set()
    before_result_paths = (
        Path("data/evals/retrieval/development-v1/bm25-fixed-window-v1/case_results.jsonl"),
        Path(
            "data/evals/retrieval/development-v1/"
            "dense-hashed-tfidf-section-aware-v1/case_results.jsonl"
        ),
    )
    for path in before_result_paths:
        before_failures.update(_load_case_failures(repo_root / path))
    resolved = tuple(sorted(before_failures - after_failures))
    remediated_case_ids = (
        "dev-ret-009",
        "dev-ret-012",
        "dev-ret-013",
        "dev-ret-014",
        "dev-ret-015",
        "dev-ret-023",
        "dev-ret-024",
    )
    return RetrievalRemediationReport(
        metadata_registry_path=_METADATA_PATH.as_posix(),
        metadata_registry_sha256=_sha256_bytes((repo_root / _METADATA_PATH).read_bytes()),
        development_v1_path=_DEVELOPMENT_V1_PATH.as_posix(),
        development_v1_sha256=_sha256_bytes((repo_root / _DEVELOPMENT_V1_PATH).read_bytes()),
        development_v2_path=_DEVELOPMENT_V2_PATH.as_posix(),
        development_v2_sha256=_sha256_bytes((repo_root / _DEVELOPMENT_V2_PATH).read_bytes()),
        held_out_v1_path=_HELD_OUT_V1_PATH.as_posix(),
        held_out_v1_sha256=_sha256_bytes((repo_root / _HELD_OUT_V1_PATH).read_bytes()),
        before_scorecards=before_refs,
        after_scorecards=tuple(after_refs),
        remediated_case_ids=remediated_case_ids,
        resolved_development_case_ids=resolved,
        remaining_development_failure_ids=tuple(sorted(after_failures)),
    )


def _summary(report: RetrievalRemediationReport) -> RetrievalRemediationSummary:
    return RetrievalRemediationSummary(
        report_id=report.report_id,
        remediated_candidate_count=len(report.after_scorecards),
        development_case_count=24,
        remediated_case_count=len(report.remediated_case_ids),
        resolved_case_count=len(report.resolved_development_case_ids),
        remaining_failure_count=len(report.remaining_development_failure_ids),
        gate_1_status=report.gate_1_status,
        held_out_v2_required=report.held_out_v2_required,
        retrieval_freeze_permitted=report.retrieval_freeze_permitted,
        validation_status="valid",
    )


def write_all(repo_root: Path) -> RetrievalRemediationSummary:
    """Build and persist remediated candidate evidence and comparison report."""

    built = _build_all(repo_root)
    for manifest, scorecard, results_bytes in built:
        candidate_root = repo_root / _OUTPUT_ROOT / scorecard.retriever_config_id
        candidate_root.mkdir(parents=True, exist_ok=True)
        (candidate_root / "manifest.json").write_bytes(_model_json_bytes(manifest))
        (candidate_root / "case_results.jsonl").write_bytes(results_bytes)
        (candidate_root / "scorecard.json").write_bytes(_model_json_bytes(scorecard))
    report = _build_report(repo_root, built)
    report_path = repo_root / _REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(_model_json_bytes(report))
    return _summary(report)


def verify_all(repo_root: Path) -> RetrievalRemediationSummary:
    """Rebuild remediation evidence and compare every persisted byte."""

    built = _build_all(repo_root)
    for manifest, scorecard, results_bytes in built:
        candidate_root = repo_root / _OUTPUT_ROOT / scorecard.retriever_config_id
        expected = {
            candidate_root / "manifest.json": _model_json_bytes(manifest),
            candidate_root / "case_results.jsonl": results_bytes,
            candidate_root / "scorecard.json": _model_json_bytes(scorecard),
        }
        for path, payload in expected.items():
            try:
                actual = path.read_bytes()
            except FileNotFoundError as exc:
                raise RemediationError(
                    "REMEDIATION_ARTIFACT_NOT_FOUND",
                    "Persisted remediation artifact was not found.",
                    str(path),
                ) from exc
            if actual != payload:
                raise RemediationError(
                    "REMEDIATION_ARTIFACT_MISMATCH",
                    "Persisted remediation artifact does not match deterministic output.",
                    str(path),
                )
    report = _build_report(repo_root, built)
    report_path = repo_root / _REPORT_PATH
    try:
        actual_report = report_path.read_bytes()
    except FileNotFoundError as exc:
        raise RemediationError(
            "REMEDIATION_REPORT_NOT_FOUND",
            "Persisted remediation report was not found.",
            str(report_path),
        ) from exc
    if actual_report != _model_json_bytes(report):
        raise RemediationError(
            "REMEDIATION_REPORT_MISMATCH",
            "Persisted remediation report does not match deterministic output.",
            str(report_path),
        )
    return _summary(report)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = _parse_args(argv)
    try:
        summary = (
            write_all(args.repo_root) if args.command == "build" else verify_all(args.repo_root)
        )
    except RemediationError as exc:
        envelope = RemediationErrorEnvelope(
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
