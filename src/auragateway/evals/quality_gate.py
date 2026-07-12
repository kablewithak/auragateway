"""Deterministic Gate 6 quality non-inferiority comparison logic."""

from __future__ import annotations

from auragateway.contracts.quality_gate import (
    ConditionQualityMetrics,
    QualityComparisonInput,
    QualityCondition,
    QualityGateCheckName,
    QualityGateCheckResult,
    QualityGateCheckStatus,
    QualityGateFailureCode,
    QualityGateFixtureCase,
    QualityGateFixtureResult,
    QualityGateStatus,
    QualityNonInferiorityResult,
    QualityRateSnapshot,
)


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _rates(metrics: ConditionQualityMetrics) -> QualityRateSnapshot:
    return QualityRateSnapshot(
        condition_id=metrics.condition_id,
        sample_count=metrics.sample_count,
        structured_output_validity_rate=_safe_rate(
            metrics.structured_output_valid_count,
            metrics.sample_count,
        ),
        citation_support_rate=_safe_rate(
            metrics.citation_supported_count,
            metrics.citation_evaluable_count,
        ),
        unsupported_answer_rate=_safe_rate(
            metrics.unsupported_answer_count,
            metrics.answer_count,
        ),
        task_success_rate=_safe_rate(
            metrics.task_success_count,
            metrics.sample_count,
        ),
    )


def _check(
    check_name: QualityGateCheckName,
    passed: bool,
    *,
    condition_id: QualityCondition | None = None,
    failure_code: QualityGateFailureCode | None = None,
    observed_rate: float | None = None,
    reference_rate: float | None = None,
    threshold: float | None = None,
    details: tuple[str, ...] = (),
) -> QualityGateCheckResult:
    return QualityGateCheckResult(
        check_name=check_name,
        status=QualityGateCheckStatus.PASSED if passed else QualityGateCheckStatus.FAILED,
        condition_id=condition_id,
        failure_code=None if passed else failure_code,
        observed_rate=observed_rate,
        reference_rate=reference_rate,
        threshold=threshold,
        details=details,
    )


def _not_applicable(
    check_name: QualityGateCheckName,
    condition_id: QualityCondition | None = None,
) -> QualityGateCheckResult:
    return QualityGateCheckResult(
        check_name=check_name,
        status=QualityGateCheckStatus.NOT_APPLICABLE,
        condition_id=condition_id,
    )


def _failure_codes(
    checks: tuple[QualityGateCheckResult, ...],
) -> tuple[QualityGateFailureCode, ...]:
    return tuple(
        dict.fromkeys(check.failure_code for check in checks if check.failure_code is not None)
    )


def _result(
    comparison: QualityComparisonInput,
    rates: tuple[QualityRateSnapshot, ...],
    checks: tuple[QualityGateCheckResult, ...],
    status: QualityGateStatus,
) -> QualityNonInferiorityResult:
    return QualityNonInferiorityResult(
        comparison_id=comparison.comparison_id,
        status=status,
        eligible_for_quality_comparison=status
        in {
            QualityGateStatus.PASSED,
            QualityGateStatus.FAILED,
        },
        rates=rates,
        checks=checks,
        failure_codes=_failure_codes(checks),
        quality_gate_passed=status is QualityGateStatus.PASSED,
    )


def evaluate_quality_noninferiority(
    comparison: QualityComparisonInput,
) -> QualityNonInferiorityResult:
    """Evaluate A/B/C quality eligibility and non-inferiority deterministically."""

    metrics_by_condition = {item.condition_id: item for item in comparison.conditions}
    metrics = tuple(metrics_by_condition[condition] for condition in QualityCondition)
    rates = tuple(_rates(item) for item in metrics)
    rates_by_condition = {item.condition_id: item for item in rates}
    thresholds = comparison.thresholds
    checks: list[QualityGateCheckResult] = []

    retrieval_fingerprints = {
        item.retrieval_configuration_fingerprint for item in comparison.conditions
    }
    retrieval_match = len(retrieval_fingerprints) == 1
    checks.append(
        _check(
            QualityGateCheckName.RETRIEVAL_CONFIGURATION_MATCH,
            retrieval_match,
            failure_code=QualityGateFailureCode.RETRIEVAL_CONFIGURATION_MISMATCH,
            details=(f"distinct_fingerprint_count={len(retrieval_fingerprints)}",),
        )
    )

    episode_manifests = {item.episode_manifest_sha256 for item in comparison.conditions}
    episode_match = len(episode_manifests) == 1
    checks.append(
        _check(
            QualityGateCheckName.EPISODE_MANIFEST_MATCH,
            episode_match,
            failure_code=QualityGateFailureCode.EPISODE_MANIFEST_MISMATCH,
            details=(f"distinct_manifest_count={len(episode_manifests)}",),
        )
    )

    if not retrieval_match or not episode_match:
        for condition in QualityCondition:
            checks.extend(
                (
                    _not_applicable(QualityGateCheckName.SAMPLE_COUNT_SUFFICIENT, condition),
                    _not_applicable(
                        QualityGateCheckName.RATE_DENOMINATORS_SUFFICIENT,
                        condition,
                    ),
                    _not_applicable(
                        QualityGateCheckName.STRUCTURED_OUTPUT_VALIDITY,
                        condition,
                    ),
                )
            )
        for condition in (QualityCondition.B, QualityCondition.C):
            checks.extend(
                (
                    _not_applicable(
                        QualityGateCheckName.CITATION_SUPPORT_NON_REGRESSION,
                        condition,
                    ),
                    _not_applicable(
                        QualityGateCheckName.UNSUPPORTED_ANSWER_NON_REGRESSION,
                        condition,
                    ),
                    _not_applicable(
                        QualityGateCheckName.TASK_SUCCESS_NON_INFERIORITY,
                        condition,
                    ),
                )
            )
        return _result(
            comparison,
            rates,
            tuple(checks),
            QualityGateStatus.INELIGIBLE,
        )

    sample_sufficient = True
    denominators_sufficient = True
    for item in metrics:
        enough_samples = item.sample_count >= thresholds.minimum_sample_count
        sample_sufficient = sample_sufficient and enough_samples
        checks.append(
            _check(
                QualityGateCheckName.SAMPLE_COUNT_SUFFICIENT,
                enough_samples,
                condition_id=item.condition_id,
                failure_code=QualityGateFailureCode.INSUFFICIENT_SAMPLE,
                details=(
                    f"sample_count={item.sample_count}",
                    f"minimum_sample_count={thresholds.minimum_sample_count}",
                ),
            )
        )

        enough_denominators = (
            item.answer_count >= thresholds.minimum_rate_denominator
            and item.citation_evaluable_count >= thresholds.minimum_rate_denominator
        )
        denominators_sufficient = denominators_sufficient and enough_denominators
        checks.append(
            _check(
                QualityGateCheckName.RATE_DENOMINATORS_SUFFICIENT,
                enough_denominators,
                condition_id=item.condition_id,
                failure_code=QualityGateFailureCode.INSUFFICIENT_RATE_DENOMINATOR,
                details=(
                    f"answer_count={item.answer_count}",
                    f"citation_evaluable_count={item.citation_evaluable_count}",
                    f"minimum_rate_denominator={thresholds.minimum_rate_denominator}",
                ),
            )
        )

    if not sample_sufficient or not denominators_sufficient:
        for condition in QualityCondition:
            checks.append(
                _not_applicable(
                    QualityGateCheckName.STRUCTURED_OUTPUT_VALIDITY,
                    condition,
                )
            )
        for condition in (QualityCondition.B, QualityCondition.C):
            checks.extend(
                (
                    _not_applicable(
                        QualityGateCheckName.CITATION_SUPPORT_NON_REGRESSION,
                        condition,
                    ),
                    _not_applicable(
                        QualityGateCheckName.UNSUPPORTED_ANSWER_NON_REGRESSION,
                        condition,
                    ),
                    _not_applicable(
                        QualityGateCheckName.TASK_SUCCESS_NON_INFERIORITY,
                        condition,
                    ),
                )
            )
        return _result(
            comparison,
            rates,
            tuple(checks),
            QualityGateStatus.INSUFFICIENT_SAMPLE,
        )

    for condition in QualityCondition:
        rate = rates_by_condition[condition].structured_output_validity_rate
        assert rate is not None
        checks.append(
            _check(
                QualityGateCheckName.STRUCTURED_OUTPUT_VALIDITY,
                rate >= thresholds.structured_output_validity_minimum,
                condition_id=condition,
                failure_code=(QualityGateFailureCode.STRUCTURED_OUTPUT_VALIDITY_BELOW_THRESHOLD),
                observed_rate=rate,
                threshold=thresholds.structured_output_validity_minimum,
            )
        )

    baseline = rates_by_condition[QualityCondition.A]
    assert baseline.citation_support_rate is not None
    assert baseline.unsupported_answer_rate is not None
    assert baseline.task_success_rate is not None

    for condition in (QualityCondition.B, QualityCondition.C):
        candidate = rates_by_condition[condition]
        assert candidate.citation_support_rate is not None
        assert candidate.unsupported_answer_rate is not None
        assert candidate.task_success_rate is not None

        minimum_citation_rate = (
            baseline.citation_support_rate - thresholds.citation_support_regression_tolerance
        )
        checks.append(
            _check(
                QualityGateCheckName.CITATION_SUPPORT_NON_REGRESSION,
                candidate.citation_support_rate >= minimum_citation_rate,
                condition_id=condition,
                failure_code=QualityGateFailureCode.CITATION_SUPPORT_REGRESSION,
                observed_rate=candidate.citation_support_rate,
                reference_rate=baseline.citation_support_rate,
                threshold=minimum_citation_rate,
            )
        )

        maximum_unsupported_rate = (
            baseline.unsupported_answer_rate + thresholds.unsupported_answer_rate_increase_tolerance
        )
        checks.append(
            _check(
                QualityGateCheckName.UNSUPPORTED_ANSWER_NON_REGRESSION,
                candidate.unsupported_answer_rate <= maximum_unsupported_rate,
                condition_id=condition,
                failure_code=QualityGateFailureCode.UNSUPPORTED_ANSWER_RATE_INCREASE,
                observed_rate=candidate.unsupported_answer_rate,
                reference_rate=baseline.unsupported_answer_rate,
                threshold=maximum_unsupported_rate,
            )
        )

        minimum_task_success = (
            baseline.task_success_rate - thresholds.task_success_noninferiority_margin
        )
        checks.append(
            _check(
                QualityGateCheckName.TASK_SUCCESS_NON_INFERIORITY,
                candidate.task_success_rate >= minimum_task_success,
                condition_id=condition,
                failure_code=QualityGateFailureCode.TASK_SUCCESS_INFERIOR,
                observed_rate=candidate.task_success_rate,
                reference_rate=baseline.task_success_rate,
                threshold=minimum_task_success,
            )
        )

    final_status = (
        QualityGateStatus.FAILED
        if any(check.status is QualityGateCheckStatus.FAILED for check in checks)
        else QualityGateStatus.PASSED
    )
    return _result(comparison, rates, tuple(checks), final_status)


def evaluate_quality_gate_fixture(
    case: QualityGateFixtureCase,
) -> QualityGateFixtureResult:
    """Execute one fixed synthetic quality-gate case."""

    result = evaluate_quality_noninferiority(case.comparison)
    expectation_matched = (
        result.status is case.expected_status
        and result.failure_codes == case.expected_failure_codes
    )
    return QualityGateFixtureResult(
        case_id=case.case_id,
        result=result,
        expectation_matched=expectation_matched,
        negative_control=case.negative_control,
    )
