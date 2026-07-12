"""Build and verify development-only cross-retriever selection evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.retrieval_eval import RetrievalDevelopmentScorecard
from auragateway.contracts.retrieval_selection import (
    RetrievalSelectionPolicy,
    RetrievalSelectionRecommendation,
    RetrievalSelectionReport,
    RetrievalSelectionSummary,
    RetrievalSelectionVariant,
    SelectionRankingEntry,
    SelectionRecommendationStatus,
    SelectionScorecardReference,
)
from auragateway.evals.runner import (
    RetrievalEvaluationError,
    load_development_assets,
    load_index_context,
    verify_all_scorecards,
)
from auragateway.evals.selection import build_selection_variant, rank_eligible_variants
from auragateway.retrieval.dense_runner import (
    FIXED_WINDOW_DENSE_CONFIG,
    SECTION_AWARE_DENSE_CONFIG,
)
from auragateway.retrieval.runner import (
    FIXED_WINDOW_BM25_CONFIG,
    SECTION_AWARE_BM25_CONFIG,
)

_SELECTION_ROOT: Final = Path("data/evals/retrieval/selection-v1")
_POLICY_PATH: Final = _SELECTION_ROOT / "policy.json"
_VARIANTS_PATH: Final = _SELECTION_ROOT / "variants.jsonl"
_REPORT_PATH: Final = _SELECTION_ROOT / "report.json"
_DEVELOPMENT_SET_PATH: Final = Path("data/evals/retrieval/development-v1/accepted_cases.json")
_DEVELOPMENT_SCORECARD_ROOT: Final = Path("data/evals/retrieval/development-v1")

_DEFAULT_POLICY: Final = RetrievalSelectionPolicy()


class RetrievalSelectionError(Exception):
    """Expected selection failure with safe machine-readable details."""

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


class RetrievalSelectionErrorEnvelope(BaseModel):
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


def _models_jsonl(models: tuple[BaseModel, ...]) -> bytes:
    return ("\n".join(model.model_dump_json() for model in models) + "\n").encode("utf-8")


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_model(path: Path, model_type: type[BaseModel], not_found_code: str) -> BaseModel:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RetrievalSelectionError(
            error_code=not_found_code,
            safe_message="Required retrieval selection artifact was not found.",
            path=str(path),
        ) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RetrievalSelectionError(
            error_code="RETRIEVAL_SELECTION_INVALID_JSON",
            safe_message="Retrieval selection artifact is not valid JSON.",
            path=str(path),
        ) from exc
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise RetrievalSelectionError(
            error_code="RETRIEVAL_SELECTION_VALIDATION_FAILED",
            safe_message="Retrieval selection artifact failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _candidate_config_ids() -> tuple[str, ...]:
    return (
        FIXED_WINDOW_BM25_CONFIG.config_id,
        SECTION_AWARE_BM25_CONFIG.config_id,
        FIXED_WINDOW_DENSE_CONFIG.config_id,
        SECTION_AWARE_DENSE_CONFIG.config_id,
    )


def _scorecard_path(config_id: str) -> Path:
    return _DEVELOPMENT_SCORECARD_ROOT / config_id / "scorecard.json"


def _scorecard_references(repo_root: Path) -> tuple[SelectionScorecardReference, ...]:
    references: list[SelectionScorecardReference] = []
    for config_id in _candidate_config_ids():
        path = _scorecard_path(config_id)
        file_path = repo_root / path
        scorecard = _load_model(
            file_path,
            RetrievalDevelopmentScorecard,
            "RETRIEVAL_SELECTION_SCORECARD_NOT_FOUND",
        )
        assert isinstance(scorecard, RetrievalDevelopmentScorecard)
        if scorecard.retriever_config_id != config_id:
            raise RetrievalSelectionError(
                error_code="RETRIEVAL_SELECTION_SCORECARD_CONFIG_MISMATCH",
                safe_message="Upstream scorecard configuration identity does not match its path.",
                path=str(file_path),
                details=(config_id, scorecard.retriever_config_id),
            )
        references.append(
            SelectionScorecardReference(
                retriever_config_id=config_id,
                scorecard_path=path.as_posix(),
                scorecard_sha256=_sha256_bytes(file_path.read_bytes()),
            )
        )
    return tuple(references)


def build_selection_evidence(
    repo_root: Path,
) -> tuple[
    RetrievalSelectionPolicy, tuple[RetrievalSelectionVariant, ...], RetrievalSelectionReport
]:
    """Build policy, all variants, and development-only recommendation in memory."""

    try:
        verify_all_scorecards(repo_root)
        development_set, _, _ = load_development_assets(repo_root)
    except RetrievalEvaluationError as exc:
        raise RetrievalSelectionError(
            error_code="RETRIEVAL_SELECTION_UPSTREAM_EVIDENCE_INVALID",
            safe_message="Upstream retrieval evidence failed verification before selection.",
            path=exc.path,
            details=(exc.error_code, *exc.details),
        ) from exc

    policy = _DEFAULT_POLICY
    variants: list[RetrievalSelectionVariant] = []
    for config_id in _candidate_config_ids():
        try:
            context = load_index_context(repo_root, config_id)
        except RetrievalEvaluationError as exc:
            raise RetrievalSelectionError(
                error_code="RETRIEVAL_SELECTION_CANDIDATE_INVALID",
                safe_message="Retrieval candidate failed verification before selection.",
                path=exc.path,
                details=(config_id, exc.error_code, *exc.details),
            ) from exc
        for metadata_policy in policy.metadata_policies:
            for top_k in policy.top_k_values:
                variants.append(
                    build_selection_variant(
                        index=context.index,
                        cases=development_set.cases,
                        retriever_config_id=context.config_id,
                        retriever_config_sha256=context.config_sha256,
                        chunking_config_id=context.chunking_config_id,
                        top_k=top_k,
                        metadata_policy=metadata_policy,
                        policy=policy,
                    )
                )

    variants_tuple = tuple(variants)
    variants_bytes = _models_jsonl(variants_tuple)
    policy_bytes = _model_json_bytes(policy)
    ranked = rank_eligible_variants(variants_tuple)
    rankings = tuple(
        SelectionRankingEntry(
            rank=rank,
            variant_id=variant.variant_id,
            retriever_config_id=variant.retriever_config_id,
            chunking_config_id=variant.chunking_config_id,
            top_k=variant.top_k,
            hard_gate_passed=variant.hard_gate_passed,
            final_score=variant.final_score,
        )
        for rank, variant in enumerate(ranked, start=1)
    )
    passing = tuple(variant for variant in ranked if variant.hard_gate_passed)
    if passing:
        winner = passing[0]
        runner_up = passing[1] if len(passing) > 1 else None
        rationale = [
            (
                "Highest failure-weighted final score among authored-policy variants "
                "that pass every hard gate."
            ),
            (
                "Top-k includes an explicit context-expansion penalty, so additional "
                "hits must earn their cost."
            ),
            (
                "Recommendation is development-only and cannot freeze retrieval "
                "before held-out validation."
            ),
        ]
        if runner_up is not None:
            delta = round(winner.final_score - runner_up.final_score, 12)
            rationale.append(
                f"Development final-score margin over the next passing variant is {delta}."
            )
        recommendation = RetrievalSelectionRecommendation(
            status=SelectionRecommendationStatus.DEVELOPMENT_RECOMMENDED,
            variant_id=winner.variant_id,
            retriever_config_id=winner.retriever_config_id,
            chunking_config_id=winner.chunking_config_id,
            top_k=winner.top_k,
            metadata_policy=winner.metadata_policy,
            final_score=winner.final_score,
            rationale=tuple(rationale),
        )
    else:
        recommendation = RetrievalSelectionRecommendation(
            status=SelectionRecommendationStatus.NO_ELIGIBLE_CANDIDATE,
            rationale=(
                "No authored-policy variant passed every predeclared development promotion gate.",
                (
                    "Retrieval changes and a complete development rerun are required "
                    "before held-out evaluation."
                ),
            ),
        )

    source_scorecards = _scorecard_references(repo_root)
    report = RetrievalSelectionReport(
        selection_policy_path=_POLICY_PATH.as_posix(),
        selection_policy_sha256=_sha256_bytes(policy_bytes),
        retrieval_set_path=_DEVELOPMENT_SET_PATH.as_posix(),
        retrieval_set_sha256=_sha256_bytes((repo_root / _DEVELOPMENT_SET_PATH).read_bytes()),
        source_scorecards=source_scorecards,
        variants_path=_VARIANTS_PATH.as_posix(),
        variants_sha256=_sha256_bytes(variants_bytes),
        variant_count=len(variants_tuple),
        eligible_variant_count=sum(
            variant.eligible_for_recommendation for variant in variants_tuple
        ),
        negative_control_variant_count=sum(
            not variant.eligible_for_recommendation for variant in variants_tuple
        ),
        rankings=rankings,
        recommendation=recommendation,
    )
    return policy, variants_tuple, report


def _summary(
    variants: tuple[RetrievalSelectionVariant, ...],
    report: RetrievalSelectionReport,
) -> RetrievalSelectionSummary:
    recommendation = report.recommendation
    return RetrievalSelectionSummary(
        report_id=report.report_id,
        variant_count=report.variant_count,
        eligible_variant_count=report.eligible_variant_count,
        passing_variant_count=sum(
            variant.eligible_for_recommendation and variant.hard_gate_passed for variant in variants
        ),
        recommendation_status=recommendation.status,
        recommended_retriever_config_id=recommendation.retriever_config_id,
        recommended_top_k=recommendation.top_k,
        recommended_final_score=recommendation.final_score,
        held_out_validation_required=report.held_out_validation_required,
        retrieval_freeze_permitted=report.retrieval_freeze_permitted,
        validation_status="valid",
    )


def write_selection_evidence(repo_root: Path) -> RetrievalSelectionSummary:
    """Persist deterministic selection policy, variants, and report."""

    policy, variants, report = build_selection_evidence(repo_root)
    output_root = repo_root / _SELECTION_ROOT
    output_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _POLICY_PATH).write_bytes(_model_json_bytes(policy))
    (repo_root / _VARIANTS_PATH).write_bytes(_models_jsonl(variants))
    (repo_root / _REPORT_PATH).write_bytes(_model_json_bytes(report))
    return _summary(variants, report)


def verify_selection_evidence(repo_root: Path) -> RetrievalSelectionSummary:
    """Rebuild selection evidence and compare exact persisted bytes."""

    expected_policy, expected_variants, expected_report = build_selection_evidence(repo_root)
    expected_files = (
        (_POLICY_PATH, _model_json_bytes(expected_policy)),
        (_VARIANTS_PATH, _models_jsonl(expected_variants)),
        (_REPORT_PATH, _model_json_bytes(expected_report)),
    )
    for path, expected in expected_files:
        file_path = repo_root / path
        try:
            observed = file_path.read_bytes()
        except FileNotFoundError as exc:
            raise RetrievalSelectionError(
                error_code="RETRIEVAL_SELECTION_ARTIFACT_NOT_FOUND",
                safe_message="Persisted retrieval selection artifact was not found.",
                path=str(file_path),
            ) from exc
        if observed != expected:
            raise RetrievalSelectionError(
                error_code="RETRIEVAL_SELECTION_ARTIFACT_MISMATCH",
                safe_message="Persisted retrieval selection artifact is not deterministic.",
                path=str(file_path),
            )
    return _summary(expected_variants, expected_report)


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
            write_selection_evidence(args.repo_root)
            if args.command == "build"
            else verify_selection_evidence(args.repo_root)
        )
    except RetrievalSelectionError as exc:
        envelope = RetrievalSelectionErrorEnvelope(
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
