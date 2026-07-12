from __future__ import annotations

from pathlib import Path

from auragateway.contracts.quality_gate import (
    ConditionQualityMetrics,
    QualityComparisonInput,
    QualityGateFixtureSet,
)
from auragateway.evals.quality_gate import evaluate_quality_noninferiority

_FIXTURE_PATH = Path("data/evals/quality/noninferiority-v1/fixtures.json")


def _comparison() -> QualityComparisonInput:
    fixtures = QualityGateFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return fixtures.cases[0].comparison


def test_condition_input_order_does_not_change_result() -> None:
    original = _comparison()
    reordered = original.model_copy(update={"conditions": tuple(reversed(original.conditions))})

    assert evaluate_quality_noninferiority(reordered) == evaluate_quality_noninferiority(original)


def test_proportional_count_scaling_does_not_change_rates_or_status() -> None:
    original = _comparison()
    scaled_conditions = tuple(
        ConditionQualityMetrics(
            condition_id=item.condition_id,
            sample_count=item.sample_count * 2,
            answer_count=item.answer_count * 2,
            structured_output_valid_count=item.structured_output_valid_count * 2,
            citation_evaluable_count=item.citation_evaluable_count * 2,
            citation_supported_count=item.citation_supported_count * 2,
            unsupported_answer_count=item.unsupported_answer_count * 2,
            task_success_count=item.task_success_count * 2,
            retrieval_configuration_fingerprint=item.retrieval_configuration_fingerprint,
            episode_manifest_sha256=item.episode_manifest_sha256,
            evidence_bundle_sha256=item.evidence_bundle_sha256,
        )
        for item in original.conditions
    )
    scaled = original.model_copy(update={"conditions": scaled_conditions})

    original_result = evaluate_quality_noninferiority(original)
    scaled_result = evaluate_quality_noninferiority(scaled)

    assert scaled_result.status is original_result.status
    assert scaled_result.failure_codes == original_result.failure_codes
    assert [item.model_dump(exclude={"sample_count"}) for item in scaled_result.rates] == [
        item.model_dump(exclude={"sample_count"}) for item in original_result.rates
    ]
