from __future__ import annotations

from pathlib import Path

from auragateway.contracts.evidence_bundle import (
    BundleFailureCode,
    ComparisonEligibilityStatus,
    EvidenceBundleFixtureCase,
    EvidenceBundleFixtureSet,
    MetricFamily,
    RunTerminalStatus,
)
from auragateway.evidence.bundle import evaluate_evidence_bundle, evaluate_fixture_case

_FIXTURE_PATH = Path("data/evals/evidence/gate8-v1/fixtures.json")


def _fixtures() -> EvidenceBundleFixtureSet:
    return EvidenceBundleFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _case(case_id: str) -> EvidenceBundleFixtureCase:
    return next(case for case in _fixtures().cases if case.case_id == case_id)


def test_all_fixed_bundle_expectations_match() -> None:
    results = tuple(evaluate_fixture_case(case) for case in _fixtures().cases)

    assert all(result.expectation_matched for result in results)


def test_pricing_mismatch_only_invalidates_cost() -> None:
    result = evaluate_evidence_bundle(_case("bundle-partial-pricing-mismatch").candidate)

    assert result.bundle_valid is True
    assert result.comparison.status is ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE
    assert result.comparison.invalidated_metric_families == (MetricFamily.COST,)


def test_retrieval_mismatch_invalidates_every_metric_family() -> None:
    result = evaluate_evidence_bundle(_case("bundle-retrieval-mismatch-ineligible").candidate)

    assert result.bundle_valid is True
    assert result.comparison.status is ComparisonEligibilityStatus.INELIGIBLE
    assert result.comparison.invalidated_metric_families == tuple(MetricFamily)
    assert result.comparison.comparative_claims_permitted is False


def test_missing_scheduled_run_is_not_hidden() -> None:
    result = evaluate_evidence_bundle(_case("bundle-missing-scheduled-run").candidate)

    assert result.bundle_valid is False
    assert result.failure_codes == (
        BundleFailureCode.RUN_ACCOUNTABILITY_INCOMPLETE,
        BundleFailureCode.RUN_RECORD_MISMATCH,
    )


def test_explicit_exclusion_remains_accounted_for() -> None:
    result = evaluate_evidence_bundle(_case("bundle-explicit-exclusion-retained").candidate)
    status_counts = {item.terminal_status: item.count for item in result.terminal_status_counts}

    assert result.bundle_valid is True
    assert status_counts[RunTerminalStatus.EXCLUDED_PREDECLARED] == 1
    assert result.run_accountability_complete is True


def test_mutated_finalized_bundle_is_rejected() -> None:
    result = evaluate_evidence_bundle(_case("bundle-finalized-content-mutated").candidate)

    assert result.finalized_content_digest_valid is False
    assert result.failure_codes == (BundleFailureCode.BUNDLE_CONTENT_DIGEST_MISMATCH,)


def test_forbidden_private_artifact_is_rejected() -> None:
    result = evaluate_evidence_bundle(_case("bundle-forbidden-private-artifact").candidate)

    assert result.private_artifacts_absent is False
    assert result.failure_codes == (BundleFailureCode.FORBIDDEN_PUBLIC_ARTIFACT,)
