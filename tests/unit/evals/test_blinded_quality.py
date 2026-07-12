"""Unit tests for deterministic blinded review controls."""

from __future__ import annotations

from pathlib import Path

from auragateway.contracts.blinded_quality import (
    BlindedQualityFixtureSet,
    BlindedQualityRubric,
    ReviewRole,
)
from auragateway.contracts.episodes import BlindedReviewProtocol
from auragateway.evals.blinded_quality import (
    build_assignment_manifest,
    build_blinded_review_export,
    evaluate_fixture_case,
)

ROOT = Path(__file__).parents[3]
BLINDED_ROOT = ROOT / "data/evals/quality/blinded-v1"
PROTOCOL_PATH = ROOT / "data/evals/episodes/blinded_review_protocol.json"


def _protocol() -> BlindedReviewProtocol:
    return BlindedReviewProtocol.model_validate_json(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _rubric() -> BlindedQualityRubric:
    return BlindedQualityRubric.model_validate_json(
        (BLINDED_ROOT / "rubric.json").read_text(encoding="utf-8")
    )


def _fixtures() -> BlindedQualityFixtureSet:
    return BlindedQualityFixtureSet.model_validate_json(
        (BLINDED_ROOT / "fixtures.json").read_text(encoding="utf-8")
    )


def test_assignments_cover_every_episode_and_five_double_reviews() -> None:
    manifest = build_assignment_manifest(
        (f"ep-func-{index:03d}" for index in range(1, 19)),
        _protocol(),
    )
    assert manifest.primary_assignment_count == 18
    assert manifest.secondary_assignment_count == 5
    assert len(manifest.assignments) == 23


def test_double_review_sample_is_frozen() -> None:
    manifest = build_assignment_manifest(
        (f"ep-func-{index:03d}" for index in range(1, 19)),
        _protocol(),
    )
    assert manifest.double_review_episode_ids == (
        "ep-func-002",
        "ep-func-003",
        "ep-func-004",
        "ep-func-012",
        "ep-func-015",
    )


def test_primary_assignments_use_opaque_review_ids() -> None:
    manifest = build_assignment_manifest(
        (f"ep-func-{index:03d}" for index in range(1, 19)),
        _protocol(),
    )
    primary = [item for item in manifest.assignments if item.role is ReviewRole.PRIMARY]
    assert all(item.review_id.startswith("review-") for item in primary)
    assert all(item.episode_id not in item.review_id for item in primary)


def test_blinded_export_excludes_experimental_fields() -> None:
    case = _fixtures().cases[0]
    export = build_blinded_review_export(case.source, case.assignments[0])
    fields = set(export.model_dump())
    assert fields.isdisjoint(
        {
            "condition_id",
            "provider",
            "model",
            "route",
            "cost",
            "latency",
            "cache_telemetry",
            "run_order",
        }
    )


def test_every_fixed_workflow_expectation_matches() -> None:
    rubric = _rubric()
    results = tuple(evaluate_fixture_case(case, rubric) for case in _fixtures().cases)
    assert all(result.expectation_matched for result in results)


def test_negative_controls_return_stable_error_codes() -> None:
    rubric = _rubric()
    results = tuple(
        evaluate_fixture_case(case, rubric) for case in _fixtures().cases if case.negative_control
    )
    assert {result.observed_error_code for result in results} == {
        "REVIEW_EXPORT_EPISODE_MISMATCH",
        "REVIEW_ASSIGNMENT_MISMATCH",
        "REVIEWER_INDEPENDENCE_VIOLATION",
        "ADJUDICATOR_INDEPENDENCE_VIOLATION",
        "ADJUDICATION_NOT_REQUIRED",
    }


def test_material_disagreement_controls_are_detected() -> None:
    rubric = _rubric()
    results = tuple(evaluate_fixture_case(case, rubric) for case in _fixtures().cases)
    assert sum(result.material_disagreement is True for result in results) == 4
