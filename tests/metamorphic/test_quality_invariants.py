from __future__ import annotations

import json
from pathlib import Path

from auragateway.contracts.corpus import CorpusInventory
from auragateway.contracts.episodes import FunctionalEpisodeSet
from auragateway.contracts.quality import (
    DeterministicQualityResult,
    QualityCandidateTrace,
    QualityFixtureSet,
)
from auragateway.evals.quality import score_deterministic_quality

_REPO_ROOT = Path(__file__).parents[2]
_FIXTURES = QualityFixtureSet.model_validate_json(
    (_REPO_ROOT / "data/evals/quality/deterministic-v1/fixtures.json").read_text(encoding="utf-8")
)
_EPISODES = FunctionalEpisodeSet.model_validate_json(
    (_REPO_ROOT / "data/evals/episodes/functional-v1/accepted_episodes.json").read_text(
        encoding="utf-8"
    )
)
_INVENTORY = CorpusInventory.model_validate_json(
    (_REPO_ROOT / "data/corpus/source_inventory.json").read_text(encoding="utf-8")
)
_FINGERPRINT = "220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490"


def _score(candidate: QualityCandidateTrace) -> DeterministicQualityResult:
    case = next(item for item in _FIXTURES.cases if item.candidate.trace_id == candidate.trace_id)
    episode = next(item for item in _EPISODES.episodes if item.episode_id == candidate.episode_id)
    return score_deterministic_quality(
        episode=episode,
        inventory=_INVENTORY,
        candidate=candidate,
        claim_support=case.claim_support,
        expected_retrieval_configuration_fingerprint=_FINGERPRINT,
    )


def test_retrieved_source_order_does_not_change_quality_result() -> None:
    case = next(item for item in _FIXTURES.cases if item.case_id == "quality-answer-grounded-pass")
    original = _score(case.candidate)
    payload = case.candidate.model_dump(mode="json")
    payload["retrieved_source_ids"] = list(reversed(payload["retrieved_source_ids"]))
    reordered = _score(QualityCandidateTrace.model_validate(payload))

    assert original.failure_labels == reordered.failure_labels
    assert original.deterministic_quality_passed is reordered.deterministic_quality_passed


def test_raw_response_wording_does_not_create_fake_semantic_score() -> None:
    case = next(item for item in _FIXTURES.cases if item.case_id == "quality-answer-grounded-pass")
    payload = case.candidate.model_dump(mode="json")
    candidate_output = dict(payload["candidate_output"])
    candidate_output["response"] = (
        "Different synthetic wording for the same declared evidence trace."
    )
    payload["candidate_output"] = candidate_output
    payload["output_sha256"] = "e" * 64
    changed = QualityCandidateTrace.model_validate(payload)

    result = _score(changed)
    assert result.deterministic_quality_passed is True
    assert "Different synthetic wording" not in json.dumps(result.model_dump(mode="json"))
