"""Build and verify held-out v2 validation and the Gate 1 retrieval freeze."""

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

from auragateway.contracts.corpus import CorpusInventory
from auragateway.contracts.retrieval_eval import (
    DevelopmentRetrievalSet,
    HeldOutRejectedRetrievalSet,
    HeldOutRetrievalSet,
    RetrievalHeldOutScorecard,
)
from auragateway.contracts.retrieval_gate import GateOneDecisionStatus
from auragateway.contracts.retrieval_gate_v2 import (
    GateOneV2Summary,
    HeldOutV2CandidateEvidence,
    HeldOutV2Decision,
    HeldOutV2Finalist,
    HeldOutV2FreezeRecord,
    HeldOutV2ScorecardReference,
    HeldOutV2ValidationPolicy,
    HeldOutV2ValidationReport,
    RetrievalFreezeManifestV1,
)
from auragateway.contracts.retrieval_selection import (
    MetadataPolicy,
    RetrievalSelectionPolicy,
    RetrievalSelectionVariant,
)
from auragateway.evals.remediation_runner import (
    RemediatedEvaluationContext,
    RemediationError,
    load_remediated_context,
)
from auragateway.evals.retrieval import aggregate_metrics
from auragateway.evals.selection import build_selection_variant, evaluate_variant_cases

_HELD_OUT_ROOT: Final = Path("data/evals/retrieval/held-out-v2")
_HELD_OUT_SET_PATH: Final = _HELD_OUT_ROOT / "accepted_cases.json"
_REJECTED_SET_PATH: Final = _HELD_OUT_ROOT / "rejected_cases.json"
_FREEZE_RECORD_PATH: Final = _HELD_OUT_ROOT / "freeze_record.json"
_POLICY_PATH: Final = _HELD_OUT_ROOT / "policy.json"
_DECISION_PATH: Final = _HELD_OUT_ROOT / "decision.json"
_RETRIEVAL_FREEZE_PATH: Final = Path("data/retrieval/frozen-v1/manifest.json")
_CORPUS_INVENTORY_PATH: Final = Path("data/corpus/source_inventory.json")
_CORPUS_MANIFEST_PATH: Final = Path("data/corpus/source_manifest.json")
_CHUNKING_ROOT: Final = Path("data/chunking")


class HeldOutV2Error(Exception):
    """Expected held-out v2 failure with safe details."""

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


class HeldOutV2ErrorEnvelope(BaseModel):
    """Safe CLI error output without query or source content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateBuild:
    """In-memory held-out v2 evidence for one remediated finalist."""

    finalist: HeldOutV2Finalist
    context: RemediatedEvaluationContext
    variant: RetrievalSelectionVariant
    scorecard: RetrievalHeldOutScorecard
    scorecard_bytes: bytes
    results_bytes: bytes
    scorecard_path: Path
    results_path: Path


@dataclass(frozen=True, slots=True)
class HeldOutV2Build:
    """Complete in-memory Gate 1 v2 output set."""

    report: HeldOutV2ValidationReport
    report_bytes: bytes
    candidates: tuple[CandidateBuild, ...]
    freeze_manifest: RetrievalFreezeManifestV1 | None
    freeze_manifest_bytes: bytes | None


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise HeldOutV2Error(
            "HELD_OUT_V2_REQUIRED_FILE_NOT_FOUND",
            "A required held-out v2 artifact was not found.",
            str(path),
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
        raise HeldOutV2Error(
            not_found_code,
            "Required held-out v2 input was not found.",
            str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HeldOutV2Error(
            "HELD_OUT_V2_INVALID_JSON",
            "Held-out v2 input is not valid JSON.",
            str(path),
        ) from exc


def _load_model(path: Path, model_type: type[BaseModel], not_found_code: str) -> BaseModel:
    try:
        return model_type.model_validate(_load_json(path, not_found_code))
    except ValidationError as exc:
        raise HeldOutV2Error(
            "HELD_OUT_V2_VALIDATION_FAILED",
            "Held-out v2 input failed typed validation.",
            str(path),
            _validation_messages(exc),
        ) from exc


def _candidate_paths(config_id: str) -> tuple[Path, Path]:
    root = _HELD_OUT_ROOT / config_id
    return root / "case_results.jsonl", root / "scorecard.json"


def _validate_hash_bindings(repo_root: Path, record: HeldOutV2FreezeRecord) -> None:
    bindings = (
        (record.held_out_set_path, record.held_out_set_sha256, "HELD_OUT_V2_SET_HASH_MISMATCH"),
        (
            record.rejected_set_path,
            record.rejected_set_sha256,
            "HELD_OUT_V2_REJECTED_HASH_MISMATCH",
        ),
        (
            record.development_set_path,
            record.development_set_sha256,
            "HELD_OUT_V2_DEVELOPMENT_HASH_MISMATCH",
        ),
        (
            record.held_out_v1_set_path,
            record.held_out_v1_set_sha256,
            "HELD_OUT_V1_SET_CHANGED",
        ),
        (
            record.held_out_v1_decision_path,
            record.held_out_v1_decision_sha256,
            "HELD_OUT_V1_DECISION_CHANGED",
        ),
        (
            record.remediation_report_path,
            record.remediation_report_sha256,
            "HELD_OUT_V2_REMEDIATION_REPORT_CHANGED",
        ),
        (
            record.source_metadata_path,
            record.source_metadata_sha256,
            "HELD_OUT_V2_SOURCE_METADATA_CHANGED",
        ),
    )
    for relative, expected, error_code in bindings:
        path = repo_root / relative
        if _sha256_file(path) != expected:
            raise HeldOutV2Error(
                error_code,
                "A frozen input changed after held-out v2 authoring was frozen.",
                str(path),
            )


def _validate_queries(
    repo_root: Path,
    held_out_set: HeldOutRetrievalSet,
    freeze_record: HeldOutV2FreezeRecord,
) -> None:
    development = _load_model(
        repo_root / freeze_record.development_set_path,
        DevelopmentRetrievalSet,
        "HELD_OUT_V2_DEVELOPMENT_SET_NOT_FOUND",
    )
    held_out_v1 = _load_model(
        repo_root / freeze_record.held_out_v1_set_path,
        HeldOutRetrievalSet,
        "HELD_OUT_V1_SET_NOT_FOUND",
    )
    assert isinstance(development, DevelopmentRetrievalSet)
    assert isinstance(held_out_v1, HeldOutRetrievalSet)
    prior_queries = {
        case.query_text.casefold() for case in (*development.cases, *held_out_v1.cases)
    }
    duplicates = tuple(
        case.case_id for case in held_out_set.cases if case.query_text.casefold() in prior_queries
    )
    if duplicates:
        raise HeldOutV2Error(
            "HELD_OUT_V2_QUERY_LEAKAGE",
            "Held-out v2 duplicates a development-v2 or held-out-v1 query.",
            details=duplicates,
        )


def _validate_sources_and_rejections(
    repo_root: Path,
    held_out_set: HeldOutRetrievalSet,
    rejected_set: HeldOutRejectedRetrievalSet,
) -> None:
    inventory = _load_model(
        repo_root / _CORPUS_INVENTORY_PATH,
        CorpusInventory,
        "HELD_OUT_V2_CORPUS_INVENTORY_NOT_FOUND",
    )
    assert isinstance(inventory, CorpusInventory)
    available = {source.source_id for source in inventory.sources}
    referenced = {
        source_id
        for case in held_out_set.cases
        for source_id in (
            *(judgment.source_id for judgment in case.relevance_judgments),
            *case.required_sources,
            *case.forbidden_sources,
            *case.near_duplicate_sources,
        )
    }
    unknown = tuple(sorted(referenced - available))
    if unknown:
        raise HeldOutV2Error(
            "HELD_OUT_V2_UNKNOWN_SOURCE",
            "Held-out v2 cases reference unknown corpus sources.",
            details=unknown,
        )
    accepted_ids = {case.case_id for case in held_out_set.cases}
    unknown_duplicates = tuple(
        sorted(
            case.duplicate_of_case_id
            for case in rejected_set.cases
            if case.duplicate_of_case_id is not None
            and case.duplicate_of_case_id not in accepted_ids
        )
    )
    if unknown_duplicates:
        raise HeldOutV2Error(
            "HELD_OUT_V2_UNKNOWN_DUPLICATE_TARGET",
            "Rejected held-out v2 proposals reference unknown accepted cases.",
            details=unknown_duplicates,
        )


def _development_variants(
    repo_root: Path,
    policy: HeldOutV2ValidationPolicy,
    selection_policy: RetrievalSelectionPolicy,
    development_set: DevelopmentRetrievalSet,
) -> dict[str, RetrievalSelectionVariant]:
    variants: dict[str, RetrievalSelectionVariant] = {}
    for finalist in policy.finalists:
        try:
            context = load_remediated_context(repo_root, finalist.retriever_config_id)
        except RemediationError as exc:
            raise HeldOutV2Error(
                "HELD_OUT_V2_FINALIST_INVALID",
                "A remediated finalist failed upstream verification.",
                exc.path,
                (exc.error_code, *exc.details),
            ) from exc
        variant = build_selection_variant(
            index=context.index,
            cases=development_set.cases,
            retriever_config_id=context.config_id,
            retriever_config_sha256=context.config_sha256,
            chunking_config_id=context.chunking_config_id,
            top_k=finalist.top_k,
            metadata_policy=MetadataPolicy.AUTHORED,
            policy=selection_policy,
        )
        variants[finalist.retriever_config_id] = variant
    return variants


def _validate_policy_and_finalists(
    repo_root: Path,
    policy: HeldOutV2ValidationPolicy,
    freeze_record: HeldOutV2FreezeRecord,
    selection_policy: RetrievalSelectionPolicy,
    development_set: DevelopmentRetrievalSet,
) -> None:
    bindings = (
        (policy.selection_policy_path, policy.selection_policy_sha256),
        (policy.remediation_report_path, policy.remediation_report_sha256),
        (policy.source_metadata_path, policy.source_metadata_sha256),
        (policy.held_out_freeze_record_path, policy.held_out_freeze_record_sha256),
    )
    for relative, expected in bindings:
        if _sha256_file(repo_root / relative) != expected:
            raise HeldOutV2Error(
                "HELD_OUT_V2_POLICY_BINDING_MISMATCH",
                "Held-out v2 policy binding changed after freeze.",
                str(repo_root / relative),
            )
    if policy.held_out_freeze_record_path != _FREEZE_RECORD_PATH.as_posix():
        raise HeldOutV2Error(
            "HELD_OUT_V2_FREEZE_REFERENCE_MISMATCH",
            "Held-out v2 policy references the wrong freeze record.",
        )
    if policy.remediation_report_path != freeze_record.remediation_report_path:
        raise HeldOutV2Error(
            "HELD_OUT_V2_REMEDIATION_REFERENCE_MISMATCH",
            "Held-out v2 policy and freeze record reference different remediation reports.",
        )
    variants = _development_variants(repo_root, policy, selection_policy, development_set)
    ranked = tuple(
        sorted(
            variants.values(),
            key=lambda item: (
                not item.hard_gate_passed,
                -item.final_score,
                item.retriever_config_id,
            ),
        )
    )
    expected_rank = {variant.retriever_config_id: rank for rank, variant in enumerate(ranked, 1)}
    for finalist in policy.finalists:
        variant = variants[finalist.retriever_config_id]
        manifest_path = repo_root / finalist.remediation_manifest_path
        if _sha256_file(manifest_path) != finalist.remediation_manifest_sha256:
            raise HeldOutV2Error(
                "HELD_OUT_V2_FINALIST_MANIFEST_MISMATCH",
                "A remediated finalist manifest changed after policy freeze.",
                str(manifest_path),
            )
        if variant.retriever_config_sha256 != finalist.retriever_config_sha256:
            raise HeldOutV2Error(
                "HELD_OUT_V2_FINALIST_CONFIG_MISMATCH",
                "Finalist configuration fingerprint does not match deterministic development v2.",
                details=(finalist.retriever_config_id,),
            )
        if expected_rank[finalist.retriever_config_id] != finalist.development_rank:
            raise HeldOutV2Error(
                "HELD_OUT_V2_FINALIST_RANK_MISMATCH",
                "Finalist rank does not match deterministic development-v2 ranking.",
                details=(finalist.retriever_config_id,),
            )
        if variant.final_score != finalist.development_final_score:
            raise HeldOutV2Error(
                "HELD_OUT_V2_FINALIST_SCORE_MISMATCH",
                "Finalist score does not match deterministic development-v2 evidence.",
                details=(finalist.retriever_config_id,),
            )


def _load_inputs(
    repo_root: Path,
) -> tuple[
    HeldOutRetrievalSet,
    HeldOutRejectedRetrievalSet,
    HeldOutV2FreezeRecord,
    HeldOutV2ValidationPolicy,
    RetrievalSelectionPolicy,
]:
    held_out_set = _load_model(
        repo_root / _HELD_OUT_SET_PATH,
        HeldOutRetrievalSet,
        "HELD_OUT_V2_SET_NOT_FOUND",
    )
    rejected_set = _load_model(
        repo_root / _REJECTED_SET_PATH,
        HeldOutRejectedRetrievalSet,
        "HELD_OUT_V2_REJECTED_SET_NOT_FOUND",
    )
    freeze_record = _load_model(
        repo_root / _FREEZE_RECORD_PATH,
        HeldOutV2FreezeRecord,
        "HELD_OUT_V2_FREEZE_RECORD_NOT_FOUND",
    )
    policy = _load_model(
        repo_root / _POLICY_PATH,
        HeldOutV2ValidationPolicy,
        "HELD_OUT_V2_POLICY_NOT_FOUND",
    )
    assert isinstance(held_out_set, HeldOutRetrievalSet)
    assert isinstance(rejected_set, HeldOutRejectedRetrievalSet)
    assert isinstance(freeze_record, HeldOutV2FreezeRecord)
    assert isinstance(policy, HeldOutV2ValidationPolicy)
    selection_policy = _load_model(
        repo_root / policy.selection_policy_path,
        RetrievalSelectionPolicy,
        "HELD_OUT_V2_SELECTION_POLICY_NOT_FOUND",
    )
    development_set = _load_model(
        repo_root / freeze_record.development_set_path,
        DevelopmentRetrievalSet,
        "HELD_OUT_V2_DEVELOPMENT_SET_NOT_FOUND",
    )
    assert isinstance(selection_policy, RetrievalSelectionPolicy)
    assert isinstance(development_set, DevelopmentRetrievalSet)
    _validate_hash_bindings(repo_root, freeze_record)
    _validate_queries(repo_root, held_out_set, freeze_record)
    _validate_sources_and_rejections(repo_root, held_out_set, rejected_set)
    _validate_policy_and_finalists(
        repo_root,
        policy,
        freeze_record,
        selection_policy,
        development_set,
    )
    if len(held_out_set.cases) < policy.minimum_held_out_case_count:
        raise HeldOutV2Error(
            "HELD_OUT_V2_CASE_COUNT_INSUFFICIENT",
            "Held-out v2 does not meet the frozen minimum case count.",
        )
    return held_out_set, rejected_set, freeze_record, policy, selection_policy


def _build_candidate(
    repo_root: Path,
    held_out_set: HeldOutRetrievalSet,
    freeze_record: HeldOutV2FreezeRecord,
    finalist: HeldOutV2Finalist,
    selection_policy: RetrievalSelectionPolicy,
) -> CandidateBuild:
    try:
        context = load_remediated_context(repo_root, finalist.retriever_config_id)
    except RemediationError as exc:
        raise HeldOutV2Error(
            "HELD_OUT_V2_FINALIST_INVALID",
            "A remediated finalist failed upstream verification.",
            exc.path,
            (exc.error_code, *exc.details),
        ) from exc
    results = evaluate_variant_cases(
        context.index,
        held_out_set.cases,
        finalist.top_k,
        MetadataPolicy.AUTHORED,
    )
    results_bytes = _models_jsonl(tuple(results))
    results_path, scorecard_path = _candidate_paths(finalist.retriever_config_id)
    scorecard = RetrievalHeldOutScorecard(
        scorecard_id=f"nimbus-relay-{finalist.retriever_config_id}-held-out-v2",
        status="held_out_remediated_candidate",
        retrieval_set_path=_HELD_OUT_SET_PATH.as_posix(),
        retrieval_set_sha256=_sha256_file(repo_root / _HELD_OUT_SET_PATH),
        rejected_set_path=_REJECTED_SET_PATH.as_posix(),
        rejected_set_sha256=_sha256_file(repo_root / _REJECTED_SET_PATH),
        freeze_record_path=_FREEZE_RECORD_PATH.as_posix(),
        freeze_record_sha256=_sha256_file(repo_root / _FREEZE_RECORD_PATH),
        retrieval_manifest_path=context.manifest_path.as_posix(),
        retrieval_manifest_sha256=_sha256_file(context.manifest_file),
        case_results_path=results_path.as_posix(),
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
        top_k=finalist.top_k,
        metadata_policy=MetadataPolicy.AUTHORED,
        policy=selection_policy,
    )
    if scorecard.retrieval_set_sha256 != freeze_record.held_out_set_sha256:
        raise HeldOutV2Error(
            "HELD_OUT_V2_SCORECARD_SET_MISMATCH",
            "Held-out v2 scorecard does not bind to the frozen case set.",
        )
    return CandidateBuild(
        finalist=finalist,
        context=context,
        variant=variant,
        scorecard=scorecard,
        scorecard_bytes=_model_json_bytes(scorecard),
        results_bytes=results_bytes,
        scorecard_path=scorecard_path,
        results_path=results_path,
    )


def _rank_passing(candidates: tuple[CandidateBuild, ...]) -> tuple[CandidateBuild, ...]:
    return tuple(
        sorted(
            (item for item in candidates if item.variant.hard_gate_passed),
            key=lambda item: (
                -item.variant.final_score,
                -item.variant.aggregate.mean_recall_at_k,
                -item.variant.aggregate.citation_support_readiness_rate,
                item.variant.aggregate.unsupported_source_retrieval_rate,
                item.finalist.development_rank,
                item.variant.retriever_config_id,
            ),
        )
    )


def _build_decision(candidates: tuple[CandidateBuild, ...]) -> HeldOutV2Decision:
    passing = _rank_passing(candidates)
    development_recommended = next(
        item.finalist.retriever_config_id
        for item in candidates
        if item.finalist.development_rank == 1
    )
    if not passing:
        return HeldOutV2Decision(
            status=GateOneDecisionStatus.BLOCKED,
            development_recommended_retriever_config_id=development_recommended,
            rationale=(
                "No remediated finalist passed every unchanged held-out v2 hard gate.",
                "Gate 1 remains blocked and retrieval remains unfrozen.",
            ),
            gate_1_passed=False,
            retrieval_freeze_permitted=False,
            required_next_gate="held_out_retrieval_v2_remediation",
        )
    selected = passing[0]
    confirmed = selected.variant.retriever_config_id == development_recommended
    status = GateOneDecisionStatus.CONFIRMED if confirmed else GateOneDecisionStatus.REVERSED
    margin = (
        selected.variant.final_score - passing[1].variant.final_score
        if len(passing) > 1
        else selected.variant.final_score
    )
    return HeldOutV2Decision(
        status=status,
        development_recommended_retriever_config_id=development_recommended,
        selected_retriever_config_id=selected.variant.retriever_config_id,
        selected_chunking_config_id=selected.variant.chunking_config_id,
        selected_top_k=selected.variant.top_k,
        selected_metadata_policy=selected.variant.metadata_policy,
        selected_final_score=selected.variant.final_score,
        development_recommendation_confirmed=confirmed,
        rationale=(
            "Selected the highest-scoring held-out v2 finalist that passed every hard gate.",
            (
                "Held-out v2 reversed the development-v2 ranking."
                if not confirmed
                else "Held-out v2 confirmed the development-v2 ranking."
            ),
            f"Held-out final-score margin over the next passing finalist: {margin:.12f}.",
            "Gate 1 freezes retrieval only; measured runtime execution remains prohibited.",
        ),
        gate_1_passed=True,
        retrieval_freeze_permitted=True,
        required_next_gate="gate_2_diagnostic_eval_asset_readiness",
    )


def _candidate_reference(candidate: CandidateBuild) -> HeldOutV2CandidateEvidence:
    return HeldOutV2CandidateEvidence(
        development_rank=candidate.finalist.development_rank,
        scorecard=HeldOutV2ScorecardReference(
            retriever_config_id=candidate.variant.retriever_config_id,
            scorecard_path=candidate.scorecard_path.as_posix(),
            scorecard_sha256=_sha256_bytes(candidate.scorecard_bytes),
            case_results_path=candidate.results_path.as_posix(),
            case_results_sha256=_sha256_bytes(candidate.results_bytes),
        ),
        variant=candidate.variant,
    )


def _fingerprint_payload(
    report_sha256: str,
    selected: CandidateBuild,
    policy: HeldOutV2ValidationPolicy,
    report: HeldOutV2ValidationReport,
    repo_root: Path,
) -> dict[str, object]:
    chunking_manifest = _CHUNKING_ROOT / selected.variant.chunking_config_id / "manifest.json"
    return {
        "schema_version": "1.0.0",
        "gate_1_report_sha256": report_sha256,
        "selected_retriever_config_id": selected.variant.retriever_config_id,
        "selected_retriever_config_sha256": selected.variant.retriever_config_sha256,
        "selected_chunking_config_id": selected.variant.chunking_config_id,
        "selected_top_k": selected.variant.top_k,
        "selected_metadata_policy": selected.variant.metadata_policy.value,
        "corpus_manifest_sha256": _sha256_file(repo_root / _CORPUS_MANIFEST_PATH),
        "chunking_manifest_sha256": _sha256_file(repo_root / chunking_manifest),
        "retrieval_manifest_sha256": _sha256_file(selected.context.manifest_file),
        "source_metadata_sha256": report.source_metadata_sha256,
        "remediation_report_sha256": report.remediation_report_sha256,
        "held_out_set_sha256": report.held_out_set_sha256,
        "selection_policy_sha256": policy.selection_policy_sha256,
    }


def build_gate_one_v2(repo_root: Path) -> HeldOutV2Build:
    """Build held-out v2 finalist evidence, Gate 1 decision, and retrieval freeze."""

    held_out_set, _, freeze_record, policy, selection_policy = _load_inputs(repo_root)
    candidates = tuple(
        _build_candidate(
            repo_root,
            held_out_set,
            freeze_record,
            finalist,
            selection_policy,
        )
        for finalist in sorted(policy.finalists, key=lambda item: item.development_rank)
    )
    decision = _build_decision(candidates)
    report = HeldOutV2ValidationReport(
        held_out_policy_path=_POLICY_PATH.as_posix(),
        held_out_policy_sha256=_sha256_file(repo_root / _POLICY_PATH),
        held_out_set_path=_HELD_OUT_SET_PATH.as_posix(),
        held_out_set_sha256=_sha256_file(repo_root / _HELD_OUT_SET_PATH),
        rejected_set_path=_REJECTED_SET_PATH.as_posix(),
        rejected_set_sha256=_sha256_file(repo_root / _REJECTED_SET_PATH),
        freeze_record_path=_FREEZE_RECORD_PATH.as_posix(),
        freeze_record_sha256=_sha256_file(repo_root / _FREEZE_RECORD_PATH),
        selection_policy_path=policy.selection_policy_path,
        selection_policy_sha256=policy.selection_policy_sha256,
        remediation_report_path=policy.remediation_report_path,
        remediation_report_sha256=policy.remediation_report_sha256,
        source_metadata_path=policy.source_metadata_path,
        source_metadata_sha256=policy.source_metadata_sha256,
        held_out_v1_decision_path=freeze_record.held_out_v1_decision_path,
        held_out_v1_decision_sha256=freeze_record.held_out_v1_decision_sha256,
        candidate_evidence=tuple(_candidate_reference(item) for item in candidates),
        decision=decision,
    )
    report_bytes = _model_json_bytes(report)
    if not decision.gate_1_passed:
        return HeldOutV2Build(report, report_bytes, candidates, None, None)
    selected_id = decision.selected_retriever_config_id
    assert selected_id is not None
    selected = next(item for item in candidates if item.variant.retriever_config_id == selected_id)
    chunking_manifest = _CHUNKING_ROOT / selected.variant.chunking_config_id / "manifest.json"
    report_sha256 = _sha256_bytes(report_bytes)
    fingerprint = _sha256_bytes(
        _canonical_json_bytes(
            _fingerprint_payload(report_sha256, selected, policy, report, repo_root)
        )
    )
    freeze_manifest = RetrievalFreezeManifestV1(
        freeze_date=date(2026, 7, 12),
        gate_1_decision_path=_DECISION_PATH.as_posix(),
        gate_1_decision_sha256=report_sha256,
        selected_retriever_config_id=selected.variant.retriever_config_id,
        selected_retriever_config_sha256=selected.variant.retriever_config_sha256,
        selected_chunking_config_id=selected.variant.chunking_config_id,
        selected_top_k=selected.variant.top_k,
        selected_metadata_policy=selected.variant.metadata_policy,
        corpus_manifest_path=_CORPUS_MANIFEST_PATH.as_posix(),
        corpus_manifest_sha256=_sha256_file(repo_root / _CORPUS_MANIFEST_PATH),
        chunking_manifest_path=chunking_manifest.as_posix(),
        chunking_manifest_sha256=_sha256_file(repo_root / chunking_manifest),
        retrieval_manifest_path=selected.context.manifest_path.as_posix(),
        retrieval_manifest_sha256=_sha256_file(selected.context.manifest_file),
        source_metadata_path=policy.source_metadata_path,
        source_metadata_sha256=policy.source_metadata_sha256,
        remediation_report_path=policy.remediation_report_path,
        remediation_report_sha256=policy.remediation_report_sha256,
        held_out_set_path=_HELD_OUT_SET_PATH.as_posix(),
        held_out_set_sha256=report.held_out_set_sha256,
        held_out_scorecard_path=selected.scorecard_path.as_posix(),
        held_out_scorecard_sha256=_sha256_bytes(selected.scorecard_bytes),
        selection_policy_path=policy.selection_policy_path,
        selection_policy_sha256=policy.selection_policy_sha256,
        configuration_fingerprint=fingerprint,
    )
    return HeldOutV2Build(
        report,
        report_bytes,
        candidates,
        freeze_manifest,
        _model_json_bytes(freeze_manifest),
    )


def _summary(build: HeldOutV2Build) -> GateOneV2Summary:
    decision = build.report.decision
    return GateOneV2Summary(
        report_id=build.report.report_id,
        held_out_case_count=12,
        finalist_count=len(build.candidates),
        passing_finalist_count=sum(item.variant.hard_gate_passed for item in build.candidates),
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


def write_gate_one_v2(repo_root: Path) -> GateOneV2Summary:
    """Persist deterministic held-out v2 evidence and retrieval freeze."""

    build = build_gate_one_v2(repo_root)
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


def _require_exact_bytes(path: Path, expected: bytes, code: str, message: str) -> None:
    try:
        actual = path.read_bytes()
    except FileNotFoundError as exc:
        raise HeldOutV2Error(code, message, str(path)) from exc
    if actual != expected:
        raise HeldOutV2Error(code, message, str(path))


def verify_gate_one_v2(repo_root: Path) -> GateOneV2Summary:
    """Rebuild held-out v2 evidence and compare every persisted byte."""

    build = build_gate_one_v2(repo_root)
    for candidate in build.candidates:
        _require_exact_bytes(
            repo_root / candidate.results_path,
            candidate.results_bytes,
            "HELD_OUT_V2_CASE_RESULTS_MISMATCH",
            "Persisted held-out v2 case results do not match deterministic output.",
        )
        _require_exact_bytes(
            repo_root / candidate.scorecard_path,
            candidate.scorecard_bytes,
            "HELD_OUT_V2_SCORECARD_MISMATCH",
            "Persisted held-out v2 scorecard does not match deterministic output.",
        )
    _require_exact_bytes(
        repo_root / _DECISION_PATH,
        build.report_bytes,
        "HELD_OUT_V2_DECISION_MISMATCH",
        "Persisted held-out v2 decision does not match deterministic output.",
    )
    freeze_path = repo_root / _RETRIEVAL_FREEZE_PATH
    if build.freeze_manifest_bytes is None:
        if freeze_path.exists():
            raise HeldOutV2Error(
                "HELD_OUT_V2_UNAUTHORIZED_FREEZE",
                "Retrieval freeze exists despite a blocked held-out v2 decision.",
                str(freeze_path),
            )
    else:
        _require_exact_bytes(
            freeze_path,
            build.freeze_manifest_bytes,
            "HELD_OUT_V2_RETRIEVAL_FREEZE_MISMATCH",
            "Persisted retrieval freeze does not match deterministic held-out v2 output.",
        )
    return _summary(build)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for held-out v2 Gate 1 evidence."""

    args = _parse_args(argv)
    try:
        summary = (
            write_gate_one_v2(args.repo_root)
            if args.command == "build"
            else verify_gate_one_v2(args.repo_root)
        )
    except HeldOutV2Error as exc:
        envelope = HeldOutV2ErrorEnvelope(
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
