"""Metamorphic invariants for Gate 6 blinded review preparation."""

from __future__ import annotations

from pathlib import Path

from auragateway.contracts.blinded_quality import (
    BlindedQualityFixtureSet,
    ReviewAssignment,
    ReviewSourceEnvelope,
)
from auragateway.contracts.episodes import BlindedReviewProtocol
from auragateway.evals.blinded_quality import (
    build_assignment_manifest,
    build_blinded_review_export,
)

ROOT = Path(__file__).parents[2]
BLINDED_ROOT = ROOT / "data/evals/quality/blinded-v1"


def _protocol() -> BlindedReviewProtocol:
    path = ROOT / "data/evals/episodes/blinded_review_protocol.json"
    return BlindedReviewProtocol.model_validate_json(path.read_text(encoding="utf-8"))


def _first_case() -> tuple[ReviewSourceEnvelope, ReviewAssignment]:
    fixtures = BlindedQualityFixtureSet.model_validate_json(
        (BLINDED_ROOT / "fixtures.json").read_text(encoding="utf-8")
    )
    case = fixtures.cases[0]
    return case.source, case.assignments[0]


def test_episode_input_order_does_not_change_assignment_manifest() -> None:
    episode_ids = tuple(f"ep-func-{index:03d}" for index in range(1, 19))
    forward = build_assignment_manifest(episode_ids, _protocol())
    reverse = build_assignment_manifest(reversed(episode_ids), _protocol())
    assert forward == reverse


def test_hidden_experimental_changes_do_not_change_blinded_export() -> None:
    source, assignment = _first_case()
    baseline = build_blinded_review_export(source, assignment)
    mutated = source.model_copy(
        update={
            "condition_id": "condition-c",
            "provider": "other-provider",
            "model": "other-model",
            "route": "other-route",
            "cost": 999.0,
            "latency": 99999,
            "cache_telemetry": {"status": "cold"},
            "run_order": 99,
        }
    )
    assert build_blinded_review_export(mutated, assignment) == baseline
