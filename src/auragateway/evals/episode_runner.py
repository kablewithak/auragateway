"""Build and verify frozen Nimbus Relay diagnostic episode assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Final, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.corpus import CorpusInventory
from auragateway.contracts.episodes import (
    BlindedReviewProtocol,
    EpisodeAssetManifest,
    EpisodeAssetSummary,
    EpisodeEvaluationSplit,
    EpisodeFreezeRecord,
    FunctionalEpisodeSet,
    RejectedEpisodeSet,
    RuntimeEpisodeSelection,
)
from auragateway.contracts.retrieval_gate_v2 import RetrievalFreezeManifestV1

_ASSET_ROOT: Final = Path("data/evals/episodes")
_FUNCTIONAL_PATH: Final = _ASSET_ROOT / "functional-v1/accepted_episodes.json"
_REJECTED_PATH: Final = _ASSET_ROOT / "functional-v1/rejected_proposals.json"
_RUNTIME_PATH: Final = _ASSET_ROOT / "runtime-v1/selection.json"
_REVIEW_PATH: Final = _ASSET_ROOT / "blinded_review_protocol.json"
_MANIFEST_PATH: Final = _ASSET_ROOT / "manifest.json"
_FREEZE_PATH: Final = _ASSET_ROOT / "freeze_record.json"
_RETRIEVAL_FREEZE_PATH: Final = Path("data/retrieval/frozen-v1/manifest.json")
_CORPUS_INVENTORY_PATH: Final = Path("data/corpus/source_inventory.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class EpisodeAssetError(Exception):
    """Expected asset failure with safe machine-readable details."""

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


class EpisodeAssetErrorEnvelope(BaseModel):
    """Safe CLI error output without raw episode messages."""

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
        location = ".".join(str(part) for part in item["loc"]) or "asset"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, error_code: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise EpisodeAssetError(
            error_code=error_code,
            safe_message="Required diagnostic episode asset was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EpisodeAssetError(
            error_code="EPISODE_ASSET_INVALID_JSON",
            safe_message="Diagnostic episode asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT], error_code: str) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path, error_code))
    except ValidationError as exc:
        raise EpisodeAssetError(
            error_code="EPISODE_ASSET_VALIDATION_FAILED",
            safe_message="Diagnostic episode asset failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _verify_source_references(
    episodes: FunctionalEpisodeSet,
    inventory: CorpusInventory,
) -> None:
    source_ids = {source.source_id for source in inventory.sources}
    unknown: set[str] = set()
    for episode in episodes.episodes:
        unknown.update(set(episode.source_scope.required_source_ids) - source_ids)
        unknown.update(set(episode.source_scope.forbidden_source_ids) - source_ids)
        unknown.update(set(episode.source_scope.optional_source_ids) - source_ids)
    if unknown:
        raise EpisodeAssetError(
            error_code="EPISODE_UNKNOWN_SOURCE_REFERENCE",
            safe_message="An accepted episode references an unknown frozen corpus source.",
            details=tuple(sorted(unknown)),
        )


def _verify_split_separation(episodes: FunctionalEpisodeSet) -> None:
    development_messages = {
        turn.user_message.strip().casefold()
        for episode in episodes.episodes
        if episode.evaluation_split is EpisodeEvaluationSplit.DEVELOPMENT
        for turn in episode.turns
    }
    held_out_messages = {
        turn.user_message.strip().casefold()
        for episode in episodes.episodes
        if episode.evaluation_split is EpisodeEvaluationSplit.HELD_OUT
        for turn in episode.turns
    }
    overlap = sorted(development_messages & held_out_messages)
    if overlap:
        raise EpisodeAssetError(
            error_code="EPISODE_SPLIT_LEAKAGE",
            safe_message="Development and held-out episodes contain reused user messages.",
            details=(f"overlap_count={len(overlap)}",),
        )


def _verify_rejected_proposals(
    episodes: FunctionalEpisodeSet,
    rejected: RejectedEpisodeSet,
) -> None:
    episode_ids = {episode.episode_id for episode in episodes.episodes}
    unknown = sorted(
        {
            overlap_id
            for proposal in rejected.proposals
            for overlap_id in proposal.overlaps_episode_ids
            if overlap_id not in episode_ids
        }
    )
    if unknown:
        raise EpisodeAssetError(
            error_code="EPISODE_REJECT_REFERENCE_UNKNOWN",
            safe_message="A rejected proposal references an unknown accepted episode.",
            details=tuple(unknown),
        )


def _verify_runtime_selection(
    episodes: FunctionalEpisodeSet,
    runtime: RuntimeEpisodeSelection,
) -> None:
    by_id = {episode.episode_id: episode for episode in episodes.episodes}
    for entry in runtime.entries:
        try:
            episode = by_id[entry.episode_id]
        except KeyError as exc:
            raise EpisodeAssetError(
                error_code="RUNTIME_EPISODE_REFERENCE_UNKNOWN",
                safe_message="Runtime selection references an unknown functional episode.",
                details=(entry.episode_id,),
            ) from exc
        if not episode.runtime_eligible:
            raise EpisodeAssetError(
                error_code="RUNTIME_EPISODE_NOT_ELIGIBLE",
                safe_message="Runtime selection includes an episode not marked runtime eligible.",
                details=(entry.episode_id,),
            )
        if episode.expected_terminal_decision.decision is not entry.expected_terminal_decision:
            raise EpisodeAssetError(
                error_code="RUNTIME_EPISODE_DECISION_MISMATCH",
                safe_message=(
                    "Runtime selection terminal decision does not match the source episode."
                ),
                details=(entry.episode_id,),
            )


def _build_manifest(
    repo_root: Path,
    episodes: FunctionalEpisodeSet,
    retrieval_freeze: RetrievalFreezeManifestV1,
) -> EpisodeAssetManifest:
    decision_counts = Counter(
        episode.expected_terminal_decision.decision.value for episode in episodes.episodes
    )
    family_counts = Counter(episode.case_family.value for episode in episodes.episodes)
    return EpisodeAssetManifest(
        retrieval_freeze_path=_RETRIEVAL_FREEZE_PATH.as_posix(),
        retrieval_freeze_sha256=_sha256_bytes((repo_root / _RETRIEVAL_FREEZE_PATH).read_bytes()),
        retrieval_configuration_fingerprint=retrieval_freeze.configuration_fingerprint,
        functional_set_path=_FUNCTIONAL_PATH.as_posix(),
        functional_set_sha256=_sha256_bytes((repo_root / _FUNCTIONAL_PATH).read_bytes()),
        rejected_set_path=_REJECTED_PATH.as_posix(),
        rejected_set_sha256=_sha256_bytes((repo_root / _REJECTED_PATH).read_bytes()),
        runtime_selection_path=_RUNTIME_PATH.as_posix(),
        runtime_selection_sha256=_sha256_bytes((repo_root / _RUNTIME_PATH).read_bytes()),
        review_protocol_path=_REVIEW_PATH.as_posix(),
        review_protocol_sha256=_sha256_bytes((repo_root / _REVIEW_PATH).read_bytes()),
        functional_episode_count=episodes.episode_count,
        development_episode_count=episodes.development_episode_count,
        held_out_episode_count=episodes.held_out_episode_count,
        runtime_episode_count=6,
        terminal_decision_counts=dict(sorted(decision_counts.items())),
        case_family_counts=dict(sorted(family_counts.items())),
    )


def _build_freeze(manifest_bytes: bytes) -> EpisodeFreezeRecord:
    return EpisodeFreezeRecord(
        manifest_path=_MANIFEST_PATH.as_posix(),
        manifest_sha256=_sha256_bytes(manifest_bytes),
    )


def build_assets(
    repo_root: Path,
) -> tuple[EpisodeAssetManifest, EpisodeFreezeRecord, EpisodeAssetSummary]:
    """Validate source assets and build deterministic Gate 2 freeze evidence."""

    functional = _load_model(
        repo_root / _FUNCTIONAL_PATH,
        FunctionalEpisodeSet,
        "FUNCTIONAL_EPISODE_SET_NOT_FOUND",
    )
    rejected = _load_model(
        repo_root / _REJECTED_PATH,
        RejectedEpisodeSet,
        "REJECTED_EPISODE_SET_NOT_FOUND",
    )
    runtime = _load_model(
        repo_root / _RUNTIME_PATH,
        RuntimeEpisodeSelection,
        "RUNTIME_EPISODE_SELECTION_NOT_FOUND",
    )
    _load_model(
        repo_root / _REVIEW_PATH,
        BlindedReviewProtocol,
        "BLINDED_REVIEW_PROTOCOL_NOT_FOUND",
    )
    inventory = _load_model(
        repo_root / _CORPUS_INVENTORY_PATH,
        CorpusInventory,
        "CORPUS_INVENTORY_NOT_FOUND",
    )
    retrieval_freeze = _load_model(
        repo_root / _RETRIEVAL_FREEZE_PATH,
        RetrievalFreezeManifestV1,
        "RETRIEVAL_FREEZE_NOT_FOUND",
    )
    if not retrieval_freeze.gate_1_passed:
        raise EpisodeAssetError(
            error_code="RETRIEVAL_FREEZE_NOT_AUTHORIZED",
            safe_message="Diagnostic episode freeze requires a passed Gate 1 retrieval freeze.",
        )
    if retrieval_freeze.measured_execution_permitted:
        raise EpisodeAssetError(
            error_code="RETRIEVAL_FREEZE_SCOPE_INVALID",
            safe_message="Retrieval freeze must not independently permit measured execution.",
        )

    _verify_source_references(functional, inventory)
    _verify_split_separation(functional)
    _verify_rejected_proposals(functional, rejected)
    _verify_runtime_selection(functional, runtime)

    manifest = _build_manifest(repo_root, functional, retrieval_freeze)
    manifest_bytes = _model_json_bytes(manifest)
    freeze = _build_freeze(manifest_bytes)
    summary = EpisodeAssetSummary(
        manifest_id=manifest.manifest_id,
        functional_episode_count=functional.episode_count,
        development_episode_count=functional.development_episode_count,
        held_out_episode_count=functional.held_out_episode_count,
        runtime_episode_count=runtime.episode_count,
        rejected_proposal_count=len(rejected.proposals),
        gate_2_passed=freeze.gate_2_passed,
        measured_execution_permitted=freeze.measured_execution_permitted,
        validation_status="valid",
    )
    return manifest, freeze, summary


def write_assets(repo_root: Path) -> EpisodeAssetSummary:
    """Persist deterministic manifest and Gate 2 freeze record."""

    manifest, freeze, summary = build_assets(repo_root)
    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _MANIFEST_PATH).write_bytes(_model_json_bytes(manifest))
    (repo_root / _FREEZE_PATH).write_bytes(_model_json_bytes(freeze))
    return summary


def verify_assets(repo_root: Path) -> EpisodeAssetSummary:
    """Rebuild and compare persisted diagnostic episode freeze evidence."""

    expected_manifest, expected_freeze, summary = build_assets(repo_root)
    persisted_manifest = _load_model(
        repo_root / _MANIFEST_PATH,
        EpisodeAssetManifest,
        "EPISODE_MANIFEST_NOT_FOUND",
    )
    persisted_freeze = _load_model(
        repo_root / _FREEZE_PATH,
        EpisodeFreezeRecord,
        "EPISODE_FREEZE_RECORD_NOT_FOUND",
    )
    if persisted_manifest != expected_manifest:
        raise EpisodeAssetError(
            error_code="EPISODE_MANIFEST_MISMATCH",
            safe_message="Persisted episode manifest does not match deterministic output.",
            path=str(repo_root / _MANIFEST_PATH),
        )
    if persisted_freeze != expected_freeze:
        raise EpisodeAssetError(
            error_code="EPISODE_FREEZE_RECORD_MISMATCH",
            safe_message="Persisted episode freeze record does not match deterministic output.",
            path=str(repo_root / _FREEZE_PATH),
        )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for diagnostic episode assets."""

    args = _parse_args(argv)
    repo_root: Path = args.repo_root
    try:
        summary = write_assets(repo_root) if args.command == "build" else verify_assets(repo_root)
    except EpisodeAssetError as exc:
        envelope = EpisodeAssetErrorEnvelope(
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
