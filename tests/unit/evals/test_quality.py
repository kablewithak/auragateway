from __future__ import annotations

from pathlib import Path

import pytest

from auragateway.contracts.corpus import CorpusInventory
from auragateway.contracts.episodes import FunctionalEpisodeSet
from auragateway.contracts.quality import (
    QualityCheckName,
    QualityCheckStatus,
    QualityFixtureCase,
    QualityFixtureSet,
)
from auragateway.evals.quality import score_deterministic_quality

_REPO_ROOT = Path(__file__).parents[3]
_FIXTURE_PATH = _REPO_ROOT / "data/evals/quality/deterministic-v1/fixtures.json"
_EPISODE_PATH = _REPO_ROOT / "data/evals/episodes/functional-v1/accepted_episodes.json"
_INVENTORY_PATH = _REPO_ROOT / "data/corpus/source_inventory.json"
_EXPECTED_FINGERPRINT = "220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490"


def _fixtures() -> QualityFixtureSet:
    return QualityFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _episodes() -> FunctionalEpisodeSet:
    return FunctionalEpisodeSet.model_validate_json(_EPISODE_PATH.read_text(encoding="utf-8"))


def _inventory() -> CorpusInventory:
    return CorpusInventory.model_validate_json(_INVENTORY_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _fixtures().cases, ids=lambda case: case.case_id)
def test_deterministic_quality_fixtures(case: QualityFixtureCase) -> None:
    typed_case = case
    episode = next(
        item for item in _episodes().episodes if item.episode_id == typed_case.candidate.episode_id
    )
    result = score_deterministic_quality(
        episode=episode,
        inventory=_inventory(),
        candidate=typed_case.candidate,
        claim_support=typed_case.claim_support,
        expected_retrieval_configuration_fingerprint=_EXPECTED_FINGERPRINT,
    )
    assert result.deterministic_quality_passed is typed_case.expected_pass
    assert result.failure_labels == typed_case.expected_failure_labels


def test_scorecard_does_not_retain_raw_candidate_output() -> None:
    case = next(
        item for item in _fixtures().cases if item.case_id == "quality-answer-grounded-pass"
    )
    episode = next(
        item for item in _episodes().episodes if item.episode_id == case.candidate.episode_id
    )
    result = score_deterministic_quality(
        episode=episode,
        inventory=_inventory(),
        candidate=case.candidate,
        claim_support=case.claim_support,
        expected_retrieval_configuration_fingerprint=_EXPECTED_FINGERPRINT,
    )
    serialized = result.model_dump_json()
    assert "candidate_output" not in serialized
    assert "Synthetic fixture output" not in serialized


def test_invalid_schema_marks_residual_checks_not_applicable() -> None:
    case = next(
        item for item in _fixtures().cases if item.case_id == "quality-structured-output-invalid"
    )
    episode = next(
        item for item in _episodes().episodes if item.episode_id == case.candidate.episode_id
    )
    result = score_deterministic_quality(
        episode=episode,
        inventory=_inventory(),
        candidate=case.candidate,
        claim_support=case.claim_support,
        expected_retrieval_configuration_fingerprint=_EXPECTED_FINGERPRINT,
    )
    by_name = {check.check_name: check for check in result.checks}
    assert by_name[QualityCheckName.STRUCTURED_OUTPUT_VALID].status is QualityCheckStatus.FAILED
    assert (
        by_name[QualityCheckName.TERMINAL_DECISION_CORRECT].status
        is QualityCheckStatus.NOT_APPLICABLE
    )
