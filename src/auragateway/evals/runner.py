"""Build and verify development retrieval scorecards."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.chunking import CorpusChunk
from auragateway.contracts.corpus import CorpusInventory
from auragateway.contracts.retrieval import RetrievalIndexManifest
from auragateway.contracts.retrieval_eval import (
    DevelopmentRetrievalSet,
    RejectedRetrievalSet,
    RetrievalDevelopmentScorecard,
    RetrievalEvaluationSummary,
)
from auragateway.evals.retrieval import aggregate_metrics, evaluate_cases
from auragateway.retrieval.bm25 import BM25Index
from auragateway.retrieval.runner import (
    FIXED_WINDOW_BM25_CONFIG,
    SECTION_AWARE_BM25_CONFIG,
    RetrievalError,
    verify_candidate,
)

_DEVELOPMENT_ROOT: Final = Path("data/evals/retrieval/development-v1")
_DEVELOPMENT_SET_PATH: Final = _DEVELOPMENT_ROOT / "accepted_cases.json"
_REJECTED_SET_PATH: Final = _DEVELOPMENT_ROOT / "rejected_cases.json"
_CORPUS_INVENTORY_PATH: Final = Path("data/corpus/source_inventory.json")
_RETRIEVAL_ROOT: Final = Path("data/retrieval/bm25-v1")


class RetrievalEvaluationError(Exception):
    """Expected evaluation failure with safe machine-readable details."""

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


class RetrievalEvaluationErrorEnvelope(BaseModel):
    """Safe CLI failure output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _model_json_bytes(model: BaseModel) -> bytes:
    return (model.model_dump_json(indent=2) + "\n").encode("utf-8")


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
        raise RetrievalEvaluationError(
            error_code=not_found_code,
            safe_message="Required retrieval evaluation input was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_INVALID_JSON",
            safe_message="Retrieval evaluation input is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[BaseModel], not_found_code: str) -> BaseModel:
    try:
        return model_type.model_validate(_load_json(path, not_found_code))
    except ValidationError as exc:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_VALIDATION_FAILED",
            safe_message="Retrieval evaluation input failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _load_chunks(path: Path) -> tuple[CorpusChunk, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_CHUNKS_NOT_FOUND",
            safe_message="Chunking output required by retrieval evaluation was not found.",
            path=str(path),
        ) from exc

    chunks: list[CorpusChunk] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            chunks.append(CorpusChunk.model_validate_json(line))
        except ValidationError as exc:
            raise RetrievalEvaluationError(
                error_code="RETRIEVAL_EVAL_CHUNK_VALIDATION_FAILED",
                safe_message="A persisted chunk failed typed validation.",
                path=str(path),
                details=(f"line {line_number}", *_validation_messages(exc)),
            ) from exc
    if not chunks:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_CHUNKS_EMPTY",
            safe_message="Chunking output contains no chunks.",
            path=str(path),
        )
    return tuple(chunks)


def _validate_source_references(
    development_set: DevelopmentRetrievalSet,
    rejected_set: RejectedRetrievalSet,
    inventory: CorpusInventory,
) -> None:
    available_sources = {source.source_id for source in inventory.sources}
    referenced_sources = {
        source_id
        for case in development_set.cases
        for source_id in (
            *(judgment.source_id for judgment in case.relevance_judgments),
            *case.required_sources,
            *case.forbidden_sources,
            *case.near_duplicate_sources,
        )
    }
    unknown_sources = sorted(referenced_sources - available_sources)
    if unknown_sources:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_UNKNOWN_SOURCE",
            safe_message="Retrieval evaluation cases reference unknown corpus sources.",
            details=tuple(unknown_sources),
        )

    accepted_ids = {case.case_id for case in development_set.cases}
    unknown_duplicates = sorted(
        case.duplicate_of_case_id
        for case in rejected_set.cases
        if case.duplicate_of_case_id is not None and case.duplicate_of_case_id not in accepted_ids
    )
    if unknown_duplicates:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_UNKNOWN_DUPLICATE_TARGET",
            safe_message="Rejected duplicate cases reference unknown accepted cases.",
            details=tuple(unknown_duplicates),
        )


def _load_assets(
    repo_root: Path,
) -> tuple[DevelopmentRetrievalSet, RejectedRetrievalSet, CorpusInventory]:
    development_set = _load_model(
        repo_root / _DEVELOPMENT_SET_PATH,
        DevelopmentRetrievalSet,
        "RETRIEVAL_EVAL_DEVELOPMENT_SET_NOT_FOUND",
    )
    rejected_set = _load_model(
        repo_root / _REJECTED_SET_PATH,
        RejectedRetrievalSet,
        "RETRIEVAL_EVAL_REJECTED_SET_NOT_FOUND",
    )
    inventory = _load_model(
        repo_root / _CORPUS_INVENTORY_PATH,
        CorpusInventory,
        "RETRIEVAL_EVAL_CORPUS_INVENTORY_NOT_FOUND",
    )
    assert isinstance(development_set, DevelopmentRetrievalSet)
    assert isinstance(rejected_set, RejectedRetrievalSet)
    assert isinstance(inventory, CorpusInventory)
    _validate_source_references(development_set, rejected_set, inventory)
    return development_set, rejected_set, inventory


def _case_results_jsonl(results: tuple[BaseModel, ...]) -> bytes:
    return ("\n".join(result.model_dump_json() for result in results) + "\n").encode("utf-8")


def _candidate_paths(config_id: str) -> tuple[Path, Path, Path]:
    candidate_root = _DEVELOPMENT_ROOT / config_id
    return (
        candidate_root,
        candidate_root / "case_results.jsonl",
        candidate_root / "scorecard.json",
    )


def build_scorecard(repo_root: Path, config_id: str) -> tuple[RetrievalDevelopmentScorecard, bytes]:
    """Build one development scorecard in memory."""

    configs = {
        FIXED_WINDOW_BM25_CONFIG.config_id: FIXED_WINDOW_BM25_CONFIG,
        SECTION_AWARE_BM25_CONFIG.config_id: SECTION_AWARE_BM25_CONFIG,
    }
    try:
        config = configs[config_id]
    except KeyError as exc:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_CONFIG_UNSUPPORTED",
            safe_message="Unsupported retrieval candidate configuration.",
            details=(config_id,),
        ) from exc

    try:
        verify_candidate(repo_root, config)
    except RetrievalError as exc:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_CANDIDATE_INVALID",
            safe_message="Retrieval candidate verification failed before evaluation.",
            path=exc.path,
            details=(exc.error_code, *exc.details),
        ) from exc

    development_set, _, _ = _load_assets(repo_root)
    retrieval_manifest_path = _RETRIEVAL_ROOT / config.chunking_config_id / "manifest.json"
    retrieval_manifest_file = repo_root / retrieval_manifest_path
    retrieval_manifest = _load_model(
        retrieval_manifest_file,
        RetrievalIndexManifest,
        "RETRIEVAL_EVAL_RETRIEVAL_MANIFEST_NOT_FOUND",
    )
    assert isinstance(retrieval_manifest, RetrievalIndexManifest)
    chunks = _load_chunks(repo_root / retrieval_manifest.chunks_path)
    index = BM25Index(chunks, config)
    results = evaluate_cases(chunks, index, development_set.cases)
    results_bytes = _case_results_jsonl(results)
    aggregate = aggregate_metrics(results)
    _, results_path, _ = _candidate_paths(config_id)
    scorecard = RetrievalDevelopmentScorecard(
        scorecard_id=f"nimbus-relay-{config_id}-development-v1",
        retrieval_set_path=_DEVELOPMENT_SET_PATH.as_posix(),
        retrieval_set_sha256=_sha256_bytes((repo_root / _DEVELOPMENT_SET_PATH).read_bytes()),
        rejected_set_path=_REJECTED_SET_PATH.as_posix(),
        rejected_set_sha256=_sha256_bytes((repo_root / _REJECTED_SET_PATH).read_bytes()),
        retrieval_manifest_path=retrieval_manifest_path.as_posix(),
        retrieval_manifest_sha256=_sha256_bytes(retrieval_manifest_file.read_bytes()),
        case_results_path=results_path.as_posix(),
        case_results_sha256=_sha256_bytes(results_bytes),
        retriever_config_id=config.config_id,
        retriever_config_sha256=index.configuration_sha256,
        chunking_config_id=config.chunking_config_id,
        aggregate=aggregate,
    )
    return scorecard, results_bytes


def _summary(scorecard: RetrievalDevelopmentScorecard) -> RetrievalEvaluationSummary:
    aggregate = scorecard.aggregate
    return RetrievalEvaluationSummary(
        scorecard_id=scorecard.scorecard_id,
        retriever_config_id=scorecard.retriever_config_id,
        chunking_config_id=scorecard.chunking_config_id,
        case_count=aggregate.case_count,
        mean_recall_at_k=aggregate.mean_recall_at_k,
        mean_precision_at_k=aggregate.mean_precision_at_k,
        mean_reciprocal_rank=aggregate.mean_reciprocal_rank,
        mean_ndcg_at_k=aggregate.mean_ndcg_at_k,
        correct_source_in_top_k_rate=aggregate.correct_source_in_top_k_rate,
        citation_support_readiness_rate=aggregate.citation_support_readiness_rate,
        stale_source_retrieval_rate=aggregate.stale_source_retrieval_rate,
        near_duplicate_displacement_rate=aggregate.near_duplicate_displacement_rate,
        validation_status="valid",
    )


def write_scorecard(repo_root: Path, config_id: str) -> RetrievalEvaluationSummary:
    """Build and persist one development scorecard."""

    scorecard, results_bytes = build_scorecard(repo_root, config_id)
    candidate_root, results_path, scorecard_path = _candidate_paths(config_id)
    (repo_root / candidate_root).mkdir(parents=True, exist_ok=True)
    (repo_root / results_path).write_bytes(results_bytes)
    (repo_root / scorecard_path).write_bytes(_model_json_bytes(scorecard))
    return _summary(scorecard)


def verify_scorecard(repo_root: Path, config_id: str) -> RetrievalEvaluationSummary:
    """Rebuild one scorecard and compare persisted deterministic evidence."""

    expected_scorecard, expected_results = build_scorecard(repo_root, config_id)
    _, results_path, scorecard_path = _candidate_paths(config_id)
    persisted_scorecard = _load_model(
        repo_root / scorecard_path,
        RetrievalDevelopmentScorecard,
        "RETRIEVAL_EVAL_SCORECARD_NOT_FOUND",
    )
    assert isinstance(persisted_scorecard, RetrievalDevelopmentScorecard)
    try:
        persisted_results = (repo_root / results_path).read_bytes()
    except FileNotFoundError as exc:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_CASE_RESULTS_NOT_FOUND",
            safe_message="Persisted retrieval case results were not found.",
            path=str(repo_root / results_path),
        ) from exc

    if persisted_scorecard != expected_scorecard:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_SCORECARD_MISMATCH",
            safe_message="Persisted retrieval scorecard does not match deterministic output.",
            path=str(repo_root / scorecard_path),
        )
    if persisted_results != expected_results:
        raise RetrievalEvaluationError(
            error_code="RETRIEVAL_EVAL_CASE_RESULTS_MISMATCH",
            safe_message="Persisted retrieval case results do not match deterministic output.",
            path=str(repo_root / results_path),
        )
    return _summary(expected_scorecard)


def build_all_scorecards(repo_root: Path) -> tuple[RetrievalEvaluationSummary, ...]:
    """Persist development scorecards for both BM25 chunking candidates."""

    return tuple(
        write_scorecard(repo_root, config.config_id)
        for config in (FIXED_WINDOW_BM25_CONFIG, SECTION_AWARE_BM25_CONFIG)
    )


def verify_all_scorecards(repo_root: Path) -> tuple[RetrievalEvaluationSummary, ...]:
    """Verify both persisted BM25 development scorecards."""

    return tuple(
        verify_scorecard(repo_root, config.config_id)
        for config in (FIXED_WINDOW_BM25_CONFIG, SECTION_AWARE_BM25_CONFIG)
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for deterministic development retrieval evaluation."""

    args = _parse_args(argv)
    try:
        summaries = (
            build_all_scorecards(args.repo_root)
            if args.command == "build"
            else verify_all_scorecards(args.repo_root)
        )
    except RetrievalEvaluationError as exc:
        envelope = RetrievalEvaluationErrorEnvelope(
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
