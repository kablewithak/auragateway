"""Build and verify held-out retrieval validation and the Gate 1 freeze decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.retrieval_eval import (
    HeldOutRejectedRetrievalSet,
    HeldOutRetrievalSet,
    RetrievalHeldOutScorecard,
)
from auragateway.contracts.retrieval_gate import (
    GateOneDecisionStatus,
    GateOneSummary,
    HeldOutCandidateEvidence,
    HeldOutFreezeRecord,
    HeldOutRetrievalDecision,
    HeldOutScorecardReference,
    HeldOutValidationPolicy,
    HeldOutValidationReport,
    RetrievalFreezeManifest,
)
from auragateway.contracts.retrieval_selection import (
    MetadataPolicy,
    RetrievalSelectionPolicy,
    RetrievalSelectionReport,
    RetrievalSelectionVariant,
)
from auragateway.evals.retrieval import aggregate_metrics
from auragateway.evals.runner import (
    EvaluationIndexContext,
    RetrievalEvaluationError,
    load_development_assets,
    load_index_context,
)
from auragateway.evals.selection import build_selection_variant, evaluate_variant_cases

_HELD_OUT_ROOT: Final = Path("data/evals/retrieval/held-out-v1")
_HELD_OUT_SET_PATH: Final = _HELD_OUT_ROOT / "accepted_cases.json"
_REJECTED_SET_PATH: Final = _HELD_OUT_ROOT / "rejected_cases.json"
_FREEZE_RECORD_PATH: Final = _HELD_OUT_ROOT / "freeze_record.json"
_POLICY_PATH: Final = _HELD_OUT_ROOT / "policy.json"
_DECISION_PATH: Final = _HELD_OUT_ROOT / "decision.json"
_RETRIEVAL_FREEZE_PATH: Final = Path("data/retrieval/frozen-v1/manifest.json")
_CORPUS_MANIFEST_PATH: Final = Path("data/corpus/source_manifest.json")


class HeldOutValidationError(Exception):
    """Expected held-out validation failure with safe details."""

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


class HeldOutValidationErrorEnvelope(BaseModel):
    """Safe CLI failure output without held-out query content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateBuild:
    """In-memory held-out evidence for one finalist."""

    finalist_rank: int
    context: EvaluationIndexContext
    variant: RetrievalSelectionVariant
    scorecard: RetrievalHeldOutScorecard
    scorecard_bytes: bytes
    results_bytes: bytes
    scorecard_path: Path
    results_path: Path


@dataclass(frozen=True, slots=True)
class HeldOutBuild:
    """Complete in-memory Gate 1 output set."""

    report: HeldOutValidationReport
    report_bytes: bytes
    candidates: tuple[CandidateBuild, ...]
    freeze_manifest: RetrievalFreezeManifest | None
    freeze_manifest_bytes: bytes | None


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise HeldOutValidationError(
            error_code="HELD_OUT_REQUIRED_FILE_NOT_FOUND",
            safe_message="A required held-out validation artifact was not found.",
            path=str(path),
        ) from exc


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


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


def _load_json(path: Path, not_found_code: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HeldOutValidationError(
            error_code=not_found_code,
            safe_message="Required held-out validation input was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HeldOutValidationError(
            error_code="HELD_OUT_INVALID_JSON",
            safe_message="Held-out validation input is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[BaseModel], not_found_code: str) -> BaseModel:
    try:
        return model_type.model_validate(_load_json(path, not_found_code))
    except ValidationError as exc:
        raise HeldOutValidationError(
            error_code="HELD_OUT_VALIDATION_FAILED",
            safe_message="Held-out validation input failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _candidate_paths(config_id: str) -> tuple[Path, Path]:
    root = _HELD_OUT_ROOT / config_id
    return root / "case_results.jsonl", root / "scorecard.json"


def _load_inputs(
    repo_root: Path,
) -> tuple[
    HeldOutRetrievalSet,
    HeldOutRejectedRetrievalSet,
    HeldOutFreezeRecord,
    HeldOutValidationPolicy,
    RetrievalSelectionPolicy,
    RetrievalSelectionReport,
]:
    held_out_set = _load_model(
        repo_root / _HELD_OUT_SET_PATH,
        HeldOutRetrievalSet,
        "HELD_OUT_SET_NOT_FOUND",
    )
    rejected_set = _load_model(
        repo_root / _REJECTED_SET_PATH,
        HeldOutRejectedRetrievalSet,
        "HELD_OUT_REJECTED_SET_NOT_FOUND",
    )
    freeze_record = _load_model(
        repo_root / _FREEZE_RECORD_PATH,
        HeldOutFreezeRecord,
        "HELD_OUT_FREEZE_RECORD_NOT_FOUND",
    )
    policy = _load_model(
        repo_root / _POLICY_PATH,
        HeldOutValidationPolicy,
        "HELD_OUT_POLICY_NOT_FOUND",
    )
    assert isinstance(held_out_set, HeldOutRetrievalSet)
    assert isinstance(rejected_set, HeldOutRejectedRetrievalSet)
    assert isinstance(freeze_record, HeldOutFreezeRecord)
    assert isinstance(policy, HeldOutValidationPolicy)

    selection_policy_path = repo_root / policy.selection_policy_path
    selection_report_path = repo_root / policy.development_report_path
    selection_policy = _load_model(
        selection_policy_path,
        RetrievalSelectionPolicy,
        "HELD_OUT_SELECTION_POLICY_NOT_FOUND",
    )
    selection_report = _load_model(
        selection_report_path,
        RetrievalSelectionReport,
        "HELD_OUT_DEVELOPMENT_REPORT_NOT_FOUND",
    )
    assert isinstance(selection_policy, RetrievalSelectionPolicy)
    assert isinstance(selection_report, RetrievalSelectionReport)

    _validate_frozen_inputs(
        repo_root,
        held_out_set,
        rejected_set,
        freeze_record,
        policy,
        selection_report,
    )
    return (
        held_out_set,
        rejected_set,
        freeze_record,
        policy,
        selection_policy,
        selection_report,
    )


def _validate_frozen_inputs(
    repo_root: Path,
    held_out_set: HeldOutRetrievalSet,
    rejected_set: HeldOutRejectedRetrievalSet,
    freeze_record: HeldOutFreezeRecord,
    policy: HeldOutValidationPolicy,
    selection_report: RetrievalSelectionReport,
) -> None:
    expected_hashes = (
        (
            repo_root / freeze_record.held_out_set_path,
            freeze_record.held_out_set_sha256,
            "HELD_OUT_SET_HASH_MISMATCH",
        ),
        (
            repo_root / freeze_record.rejected_set_path,
            freeze_record.rejected_set_sha256,
            "HELD_OUT_REJECTED_SET_HASH_MISMATCH",
        ),
        (
            repo_root / freeze_record.development_set_path,
            freeze_record.development_set_sha256,
            "HELD_OUT_DEVELOPMENT_SET_HASH_MISMATCH",
        ),
        (
            repo_root / policy.selection_policy_path,
            policy.selection_policy_sha256,
            "HELD_OUT_SELECTION_POLICY_HASH_MISMATCH",
        ),
        (
            repo_root / policy.development_report_path,
            policy.development_report_sha256,
            "HELD_OUT_DEVELOPMENT_REPORT_HASH_MISMATCH",
        ),
        (
            repo_root / policy.held_out_freeze_record_path,
            policy.held_out_freeze_record_sha256,
            "HELD_OUT_FREEZE_RECORD_HASH_MISMATCH",
        ),
    )
    for path, expected, error_code in expected_hashes:
        if _sha256_file(path) != expected:
            raise HeldOutValidationError(
                error_code=error_code,
                safe_message="A frozen held-out validation artifact changed after freeze.",
                path=str(path),
            )

    if held_out_set.development_set_path != freeze_record.development_set_path:
        raise HeldOutValidationError(
            error_code="HELD_OUT_DEVELOPMENT_REFERENCE_MISMATCH",
            safe_message="Held-out and freeze records reference different development sets.",
        )
    if held_out_set.development_set_sha256 != freeze_record.development_set_sha256:
        raise HeldOutValidationError(
            error_code="HELD_OUT_DEVELOPMENT_HASH_MISMATCH",
            safe_message="Held-out and freeze records disagree on the development-set hash.",
        )
    if len(held_out_set.cases) < policy.minimum_held_out_case_count:
        raise HeldOutValidationError(
            error_code="HELD_OUT_CASE_COUNT_INSUFFICIENT",
            safe_message="Held-out set does not meet the frozen minimum case count.",
        )

    development_set, _, inventory = load_development_assets(repo_root)
    development_queries = {case.query_text.casefold() for case in development_set.cases}
    duplicate_queries = sorted(
        case.case_id
        for case in held_out_set.cases
        if case.query_text.casefold() in development_queries
    )
    if duplicate_queries:
        raise HeldOutValidationError(
            error_code="HELD_OUT_DEVELOPMENT_QUERY_LEAKAGE",
            safe_message="Held-out cases duplicate development query text.",
            details=tuple(duplicate_queries),
        )

    available_sources = {source.source_id for source in inventory.sources}
    referenced_sources = {
        source_id
        for case in held_out_set.cases
        for source_id in (
            *(judgment.source_id for judgment in case.relevance_judgments),
            *case.required_sources,
            *case.forbidden_sources,
            *case.near_duplicate_sources,
        )
    }
    unknown_sources = sorted(referenced_sources - available_sources)
    if unknown_sources:
        raise HeldOutValidationError(
            error_code="HELD_OUT_UNKNOWN_SOURCE",
            safe_message="Held-out cases reference unknown corpus sources.",
            details=tuple(unknown_sources),
        )

    held_out_ids = {case.case_id for case in held_out_set.cases}
    invalid_duplicate_targets = sorted(
        case.duplicate_of_case_id
        for case in rejected_set.cases
        if case.duplicate_of_case_id is not None and case.duplicate_of_case_id not in held_out_ids
    )
    if invalid_duplicate_targets:
        raise HeldOutValidationError(
            error_code="HELD_OUT_UNKNOWN_DUPLICATE_TARGET",
            safe_message="Rejected held-out proposals reference unknown accepted cases.",
            details=tuple(invalid_duplicate_targets),
        )

    development_rankings = {
        item.rank: item for item in selection_report.rankings if item.rank in {1, 2}
    }
    if set(development_rankings) != {1, 2}:
        raise HeldOutValidationError(
            error_code="HELD_OUT_FINALIST_RANKS_MISSING",
            safe_message="Development report does not contain both frozen finalist ranks.",
        )
    for finalist in policy.finalists:
        ranking = development_rankings[finalist.development_rank]
        if (
            ranking.retriever_config_id != finalist.retriever_config_id
            or ranking.chunking_config_id != finalist.chunking_config_id
            or ranking.top_k != finalist.top_k
            or ranking.final_score != finalist.development_final_score
        ):
            raise HeldOutValidationError(
                error_code="HELD_OUT_FINALIST_DEVELOPMENT_MISMATCH",
                safe_message="Held-out finalist does not match the frozen development ranking.",
                details=(finalist.retriever_config_id,),
            )
        manifest_path = repo_root / finalist.retrieval_manifest_path
        if _sha256_file(manifest_path) != finalist.retrieval_manifest_sha256:
            raise HeldOutValidationError(
                error_code="HELD_OUT_FINALIST_MANIFEST_MISMATCH",
                safe_message="A finalist retrieval manifest changed after held-out policy freeze.",
                path=str(manifest_path),
            )

    recommendation = selection_report.recommendation
    if (
        recommendation.retriever_config_id is None
        or recommendation.retriever_config_id != development_rankings[1].retriever_config_id
    ):
        raise HeldOutValidationError(
            error_code="HELD_OUT_DEVELOPMENT_RECOMMENDATION_MISMATCH",
            safe_message="Development recommendation does not match the rank-one finalist.",
        )


def _build_candidate(
    repo_root: Path,
    held_out_set: HeldOutRetrievalSet,
    freeze_record: HeldOutFreezeRecord,
    finalist_rank: int,
    config_id: str,
    top_k: int,
    selection_policy: RetrievalSelectionPolicy,
) -> CandidateBuild:
    try:
        context = load_index_context(repo_root, config_id)
    except RetrievalEvaluationError as exc:
        raise HeldOutValidationError(
            error_code="HELD_OUT_FINALIST_INVALID",
            safe_message="A held-out finalist failed upstream verification.",
            path=exc.path,
            details=(exc.error_code, *exc.details),
        ) from exc

    results = evaluate_variant_cases(
        context.index,
        held_out_set.cases,
        top_k,
        MetadataPolicy.AUTHORED,
    )
    results_bytes = _models_jsonl(tuple(results))
    scorecard_results_path, scorecard_path = _candidate_paths(config_id)
    scorecard = RetrievalHeldOutScorecard(
        scorecard_id=f"nimbus-relay-{config_id}-held-out-v1",
        retrieval_set_path=_HELD_OUT_SET_PATH.as_posix(),
        retrieval_set_sha256=_sha256_file(repo_root / _HELD_OUT_SET_PATH),
        rejected_set_path=_REJECTED_SET_PATH.as_posix(),
        rejected_set_sha256=_sha256_file(repo_root / _REJECTED_SET_PATH),
        freeze_record_path=_FREEZE_RECORD_PATH.as_posix(),
        freeze_record_sha256=_sha256_file(repo_root / _FREEZE_RECORD_PATH),
        retrieval_manifest_path=context.manifest_path.as_posix(),
        retrieval_manifest_sha256=_sha256_file(context.manifest_file),
        case_results_path=scorecard_results_path.as_posix(),
        case_results_sha256=_sha256_bytes(results_bytes),
        retriever_config_id=context.config_id,
        retriever_config_sha256=context.config_sha256,
        chunking_config_id=context.chunking_config_id,
        aggregate=aggregate_metrics(results),
    )
    variant = build_selection_variant(
        index=context.index,
        cases=held_out_set.cases,
        retriever_config_id=context.config_id,
        retriever_config_sha256=context.config_sha256,
        chunking_config_id=context.chunking_config_id,
        top_k=top_k,
        metadata_policy=MetadataPolicy.AUTHORED,
        policy=selection_policy,
    )
    scorecard_bytes = _model_json_bytes(scorecard)
    if freeze_record.held_out_set_sha256 != scorecard.retrieval_set_sha256:
        raise HeldOutValidationError(
            error_code="HELD_OUT_SCORECARD_SET_HASH_MISMATCH",
            safe_message="Held-out scorecard does not bind to the frozen case set.",
        )
    return CandidateBuild(
        finalist_rank=finalist_rank,
        context=context,
        variant=variant,
        scorecard=scorecard,
        scorecard_bytes=scorecard_bytes,
        results_bytes=results_bytes,
        scorecard_path=scorecard_path,
        results_path=scorecard_results_path,
    )


def _rank_passing(candidates: tuple[CandidateBuild, ...]) -> tuple[CandidateBuild, ...]:
    passing = tuple(item for item in candidates if item.variant.hard_gate_passed)
    return tuple(
        sorted(
            passing,
            key=lambda item: (
                -item.variant.final_score,
                -item.variant.aggregate.mean_recall_at_k,
                -item.variant.aggregate.citation_support_readiness_rate,
                item.variant.aggregate.unsupported_source_retrieval_rate,
                item.finalist_rank,
                item.variant.retriever_config_id,
            ),
        )
    )


def _build_decision(
    candidates: tuple[CandidateBuild, ...],
    development_recommended_config_id: str,
) -> HeldOutRetrievalDecision:
    passing = _rank_passing(candidates)
    if not passing:
        failed = tuple(item.variant.retriever_config_id for item in candidates)
        return HeldOutRetrievalDecision(
            status=GateOneDecisionStatus.BLOCKED,
            development_recommended_retriever_config_id=development_recommended_config_id,
            rationale=(
                "No finalist passed every frozen held-out hard gate.",
                (
                    "Retrieval remains unfrozen and Gate 1 requires remediation plus "
                    "a new held-out version."
                ),
                "Failed finalists: " + ", ".join(failed),
            ),
            gate_1_passed=False,
            retrieval_freeze_permitted=False,
            required_next_gate="held_out_retrieval_remediation",
        )

    selected = passing[0]
    confirmed = selected.variant.retriever_config_id == development_recommended_config_id
    status = GateOneDecisionStatus.CONFIRMED if confirmed else GateOneDecisionStatus.REVERSED
    margin = (
        selected.variant.final_score - passing[1].variant.final_score
        if len(passing) > 1
        else selected.variant.final_score
    )
    outcome = "confirmed" if confirmed else "reversed"
    return HeldOutRetrievalDecision(
        status=status,
        development_recommended_retriever_config_id=development_recommended_config_id,
        selected_retriever_config_id=selected.variant.retriever_config_id,
        selected_chunking_config_id=selected.variant.chunking_config_id,
        selected_top_k=selected.variant.top_k,
        selected_metadata_policy=selected.variant.metadata_policy,
        selected_final_score=selected.variant.final_score,
        development_recommendation_confirmed=confirmed,
        rationale=(
            "Highest held-out final score among finalists that passed every hard gate.",
            f"The development recommendation was {outcome} by held-out evidence.",
            f"Held-out final-score margin over the next passing finalist: {margin:.12f}.",
            "Gate 1 freezes retrieval only; measured runtime execution remains prohibited.",
        ),
        gate_1_passed=True,
        retrieval_freeze_permitted=True,
        required_next_gate="gate_2_diagnostic_eval_asset_readiness",
    )


def _candidate_reference(candidate: CandidateBuild) -> HeldOutCandidateEvidence:
    return HeldOutCandidateEvidence(
        development_rank=candidate.finalist_rank,
        scorecard=HeldOutScorecardReference(
            retriever_config_id=candidate.variant.retriever_config_id,
            scorecard_path=candidate.scorecard_path.as_posix(),
            scorecard_sha256=_sha256_bytes(candidate.scorecard_bytes),
            case_results_path=candidate.results_path.as_posix(),
            case_results_sha256=_sha256_bytes(candidate.results_bytes),
        ),
        variant=candidate.variant,
    )


def _configuration_fingerprint_payload(
    *,
    decision_report_sha256: str,
    selected: CandidateBuild,
    held_out_set_sha256: str,
    selection_policy_sha256: str,
    selection_report_sha256: str,
    corpus_manifest_sha256: str,
    chunking_manifest_sha256: str,
    retrieval_manifest_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "decision_report_sha256": decision_report_sha256,
        "selected_retriever_config_id": selected.variant.retriever_config_id,
        "selected_retriever_config_sha256": selected.variant.retriever_config_sha256,
        "selected_chunking_config_id": selected.variant.chunking_config_id,
        "selected_top_k": selected.variant.top_k,
        "selected_metadata_policy": selected.variant.metadata_policy.value,
        "held_out_set_sha256": held_out_set_sha256,
        "selection_policy_sha256": selection_policy_sha256,
        "selection_report_sha256": selection_report_sha256,
        "corpus_manifest_sha256": corpus_manifest_sha256,
        "chunking_manifest_sha256": chunking_manifest_sha256,
        "retrieval_manifest_sha256": retrieval_manifest_sha256,
    }


def build_gate_one(repo_root: Path) -> HeldOutBuild:
    """Build all held-out finalist evidence and the Gate 1 decision in memory."""

    (
        held_out_set,
        _,
        freeze_record,
        policy,
        selection_policy,
        selection_report,
    ) = _load_inputs(repo_root)
    candidates = tuple(
        _build_candidate(
            repo_root,
            held_out_set,
            freeze_record,
            finalist.development_rank,
            finalist.retriever_config_id,
            finalist.top_k,
            selection_policy,
        )
        for finalist in sorted(policy.finalists, key=lambda item: item.development_rank)
    )
    development_recommended = selection_report.recommendation.retriever_config_id
    if development_recommended is None:
        raise HeldOutValidationError(
            error_code="HELD_OUT_DEVELOPMENT_RECOMMENDATION_MISSING",
            safe_message="Development selection report does not contain a finalist recommendation.",
        )
    decision = _build_decision(candidates, development_recommended)
    report = HeldOutValidationReport(
        held_out_policy_path=_POLICY_PATH.as_posix(),
        held_out_policy_sha256=_sha256_file(repo_root / _POLICY_PATH),
        held_out_set_path=_HELD_OUT_SET_PATH.as_posix(),
        held_out_set_sha256=_sha256_file(repo_root / _HELD_OUT_SET_PATH),
        rejected_set_path=_REJECTED_SET_PATH.as_posix(),
        rejected_set_sha256=_sha256_file(repo_root / _REJECTED_SET_PATH),
        freeze_record_path=_FREEZE_RECORD_PATH.as_posix(),
        freeze_record_sha256=_sha256_file(repo_root / _FREEZE_RECORD_PATH),
        development_selection_report_path=policy.development_report_path,
        development_selection_report_sha256=policy.development_report_sha256,
        candidate_evidence=tuple(_candidate_reference(candidate) for candidate in candidates),
        decision=decision,
    )
    report_bytes = _model_json_bytes(report)

    if not decision.gate_1_passed:
        return HeldOutBuild(
            report=report,
            report_bytes=report_bytes,
            candidates=candidates,
            freeze_manifest=None,
            freeze_manifest_bytes=None,
        )

    selected_config_id = decision.selected_retriever_config_id
    assert selected_config_id is not None
    selected = next(
        candidate
        for candidate in candidates
        if candidate.variant.retriever_config_id == selected_config_id
    )
    retrieval_manifest_payload = _load_json(
        selected.context.manifest_file,
        "HELD_OUT_SELECTED_RETRIEVAL_MANIFEST_NOT_FOUND",
    )
    if not isinstance(retrieval_manifest_payload, dict):
        raise HeldOutValidationError(
            error_code="HELD_OUT_SELECTED_RETRIEVAL_MANIFEST_INVALID",
            safe_message="Selected retrieval manifest is not a JSON object.",
            path=str(selected.context.manifest_file),
        )
    chunking_manifest_path_value = retrieval_manifest_payload.get("chunking_manifest_path")
    if not isinstance(chunking_manifest_path_value, str):
        raise HeldOutValidationError(
            error_code="HELD_OUT_CHUNKING_MANIFEST_REFERENCE_MISSING",
            safe_message="Selected retrieval manifest lacks a chunking manifest reference.",
            path=str(selected.context.manifest_file),
        )
    chunking_manifest_path = Path(chunking_manifest_path_value)
    corpus_manifest_sha256 = _sha256_file(repo_root / _CORPUS_MANIFEST_PATH)
    chunking_manifest_sha256 = _sha256_file(repo_root / chunking_manifest_path)
    retrieval_manifest_sha256 = _sha256_file(selected.context.manifest_file)
    decision_report_sha256 = _sha256_bytes(report_bytes)
    selection_policy_sha256 = _sha256_file(repo_root / policy.selection_policy_path)
    selection_report_sha256 = _sha256_file(repo_root / policy.development_report_path)
    fingerprint = _sha256_bytes(
        _canonical_json_bytes(
            _configuration_fingerprint_payload(
                decision_report_sha256=decision_report_sha256,
                selected=selected,
                held_out_set_sha256=report.held_out_set_sha256,
                selection_policy_sha256=selection_policy_sha256,
                selection_report_sha256=selection_report_sha256,
                corpus_manifest_sha256=corpus_manifest_sha256,
                chunking_manifest_sha256=chunking_manifest_sha256,
                retrieval_manifest_sha256=retrieval_manifest_sha256,
            )
        )
    )
    freeze_manifest = RetrievalFreezeManifest(
        freeze_date=date(2026, 7, 12),
        gate_1_decision_path=_DECISION_PATH.as_posix(),
        gate_1_decision_sha256=decision_report_sha256,
        selected_retriever_config_id=selected.variant.retriever_config_id,
        selected_retriever_config_sha256=selected.variant.retriever_config_sha256,
        selected_chunking_config_id=selected.variant.chunking_config_id,
        selected_top_k=selected.variant.top_k,
        selected_metadata_policy=selected.variant.metadata_policy,
        corpus_manifest_path=_CORPUS_MANIFEST_PATH.as_posix(),
        corpus_manifest_sha256=corpus_manifest_sha256,
        chunking_manifest_path=chunking_manifest_path.as_posix(),
        chunking_manifest_sha256=chunking_manifest_sha256,
        retrieval_manifest_path=selected.context.manifest_path.as_posix(),
        retrieval_manifest_sha256=retrieval_manifest_sha256,
        held_out_set_path=_HELD_OUT_SET_PATH.as_posix(),
        held_out_set_sha256=report.held_out_set_sha256,
        held_out_scorecard_path=selected.scorecard_path.as_posix(),
        held_out_scorecard_sha256=_sha256_bytes(selected.scorecard_bytes),
        development_selection_policy_path=policy.selection_policy_path,
        development_selection_policy_sha256=selection_policy_sha256,
        development_selection_report_path=policy.development_report_path,
        development_selection_report_sha256=selection_report_sha256,
        configuration_fingerprint=fingerprint,
    )
    return HeldOutBuild(
        report=report,
        report_bytes=report_bytes,
        candidates=candidates,
        freeze_manifest=freeze_manifest,
        freeze_manifest_bytes=_model_json_bytes(freeze_manifest),
    )


def _summary(build: HeldOutBuild) -> GateOneSummary:
    decision = build.report.decision
    return GateOneSummary(
        report_id=build.report.report_id,
        held_out_case_count=12,
        finalist_count=len(build.candidates),
        passing_finalist_count=sum(
            candidate.variant.hard_gate_passed for candidate in build.candidates
        ),
        decision_status=decision.status,
        selected_retriever_config_id=decision.selected_retriever_config_id,
        selected_top_k=decision.selected_top_k,
        selected_final_score=decision.selected_final_score,
        gate_1_passed=decision.gate_1_passed,
        retrieval_freeze_permitted=decision.retrieval_freeze_permitted,
        retrieval_configuration_fingerprint=(
            build.freeze_manifest.configuration_fingerprint
            if build.freeze_manifest is not None
            else None
        ),
        measured_execution_permitted=False,
        validation_status="valid",
    )


def write_gate_one(repo_root: Path) -> GateOneSummary:
    """Build and persist held-out evidence, decision, and optional freeze manifest."""

    build = build_gate_one(repo_root)
    for candidate in build.candidates:
        (repo_root / candidate.results_path).parent.mkdir(parents=True, exist_ok=True)
        (repo_root / candidate.results_path).write_bytes(candidate.results_bytes)
        (repo_root / candidate.scorecard_path).write_bytes(candidate.scorecard_bytes)
    (repo_root / _DECISION_PATH).write_bytes(build.report_bytes)
    freeze_path = repo_root / _RETRIEVAL_FREEZE_PATH
    if build.freeze_manifest_bytes is None:
        freeze_path.unlink(missing_ok=True)
    else:
        freeze_path.parent.mkdir(parents=True, exist_ok=True)
        freeze_path.write_bytes(build.freeze_manifest_bytes)
    return _summary(build)


def _require_exact_bytes(path: Path, expected: bytes, error_code: str, message: str) -> None:
    try:
        observed = path.read_bytes()
    except FileNotFoundError as exc:
        raise HeldOutValidationError(
            error_code=error_code,
            safe_message=message,
            path=str(path),
        ) from exc
    if observed != expected:
        raise HeldOutValidationError(
            error_code=error_code,
            safe_message=message,
            path=str(path),
        )


def verify_gate_one(repo_root: Path) -> GateOneSummary:
    """Rebuild Gate 1 evidence and compare every persisted output byte."""

    build = build_gate_one(repo_root)
    for candidate in build.candidates:
        _require_exact_bytes(
            repo_root / candidate.results_path,
            candidate.results_bytes,
            "HELD_OUT_CASE_RESULTS_MISMATCH",
            "Persisted held-out case results do not match deterministic output.",
        )
        _require_exact_bytes(
            repo_root / candidate.scorecard_path,
            candidate.scorecard_bytes,
            "HELD_OUT_SCORECARD_MISMATCH",
            "Persisted held-out scorecard does not match deterministic output.",
        )
    _require_exact_bytes(
        repo_root / _DECISION_PATH,
        build.report_bytes,
        "HELD_OUT_DECISION_MISMATCH",
        "Persisted held-out decision does not match deterministic output.",
    )
    freeze_path = repo_root / _RETRIEVAL_FREEZE_PATH
    if build.freeze_manifest_bytes is None:
        if freeze_path.exists():
            raise HeldOutValidationError(
                error_code="HELD_OUT_UNAUTHORIZED_FREEZE_PRESENT",
                safe_message=(
                    "A retrieval freeze manifest exists despite a blocked Gate 1 decision."
                ),
                path=str(freeze_path),
            )
    else:
        _require_exact_bytes(
            freeze_path,
            build.freeze_manifest_bytes,
            "HELD_OUT_RETRIEVAL_FREEZE_MISMATCH",
            "Persisted retrieval freeze manifest does not match deterministic output.",
        )
    return _summary(build)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for held-out validation and Gate 1 freeze evidence."""

    args = _parse_args(argv)
    try:
        summary = (
            write_gate_one(args.repo_root)
            if args.command == "build"
            else verify_gate_one(args.repo_root)
        )
    except HeldOutValidationError as exc:
        envelope = HeldOutValidationErrorEnvelope(
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
