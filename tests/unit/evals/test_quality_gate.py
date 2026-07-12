from __future__ import annotations

from pathlib import Path

from auragateway.contracts.quality_gate import (
    QualityCondition,
    QualityGateFailureCode,
    QualityGateFixtureSet,
    QualityGateStatus,
)
from auragateway.evals.quality_gate import (
    evaluate_quality_gate_fixture,
    evaluate_quality_noninferiority,
)

_FIXTURE_PATH = Path("data/evals/quality/noninferiority-v1/fixtures.json")


def _fixtures() -> QualityGateFixtureSet:
    return QualityGateFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _case(case_id: str):  # type: ignore[no-untyped-def]
    return next(case for case in _fixtures().cases if case.case_id == case_id)


def test_all_fixed_quality_gate_expectations_match() -> None:
    results = tuple(evaluate_quality_gate_fixture(case) for case in _fixtures().cases)

    assert all(result.expectation_matched for result in results)


def test_exact_quality_boundaries_pass() -> None:
    result = evaluate_quality_noninferiority(_case("quality-gate-boundary-pass").comparison)

    assert result.status is QualityGateStatus.PASSED
    condition_c = next(rate for rate in result.rates if rate.condition_id is QualityCondition.C)
    assert condition_c.structured_output_validity_rate == 0.95
    assert condition_c.task_success_rate == 0.85


def test_configuration_drift_is_ineligible_not_failed() -> None:
    result = evaluate_quality_noninferiority(_case("quality-gate-retrieval-ineligible").comparison)

    assert result.status is QualityGateStatus.INELIGIBLE
    assert not result.eligible_for_quality_comparison
    assert result.failure_codes == (QualityGateFailureCode.RETRIEVAL_CONFIGURATION_MISMATCH,)


def test_insufficient_sample_is_not_interpreted_as_quality_failure() -> None:
    result = evaluate_quality_noninferiority(_case("quality-gate-sample-insufficient").comparison)

    assert result.status is QualityGateStatus.INSUFFICIENT_SAMPLE
    assert not result.eligible_for_quality_comparison
    assert result.failure_codes == (QualityGateFailureCode.INSUFFICIENT_SAMPLE,)


def test_multiple_regressions_retain_stable_failure_order() -> None:
    result = evaluate_quality_noninferiority(_case("quality-gate-multiple-regressions").comparison)

    assert result.failure_codes == (
        QualityGateFailureCode.STRUCTURED_OUTPUT_VALIDITY_BELOW_THRESHOLD,
        QualityGateFailureCode.CITATION_SUPPORT_REGRESSION,
        QualityGateFailureCode.UNSUPPORTED_ANSWER_RATE_INCREASE,
        QualityGateFailureCode.TASK_SUCCESS_INFERIOR,
    )
