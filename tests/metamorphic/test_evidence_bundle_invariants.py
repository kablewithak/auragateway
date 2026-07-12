from __future__ import annotations

from pathlib import Path

from auragateway.contracts.evidence_bundle import (
    EvidenceBundleCandidate,
    EvidenceBundleFixtureCase,
    EvidenceBundleFixtureSet,
)
from auragateway.evidence.bundle import (
    artifact_hash_manifest_sha256,
    evaluate_evidence_bundle,
    finalized_bundle_content_sha256,
)

_FIXTURE_PATH = Path("data/evals/evidence/gate8-v1/fixtures.json")
_ZERO = "0" * 64


def _fixtures() -> EvidenceBundleFixtureSet:
    return EvidenceBundleFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _case(case_id: str) -> EvidenceBundleFixtureCase:
    return next(case for case in _fixtures().cases if case.case_id == case_id)


def _refinalize(candidate: EvidenceBundleCandidate) -> EvidenceBundleCandidate:
    with_manifest = candidate.model_copy(
        update={
            "artifact_hash_manifest_sha256": artifact_hash_manifest_sha256(candidate.artifacts),
            "finalized_content_sha256": _ZERO,
        }
    )
    return with_manifest.model_copy(
        update={"finalized_content_sha256": finalized_bundle_content_sha256(with_manifest)}
    )


def test_run_record_order_does_not_change_accountability_or_eligibility() -> None:
    original = _case("bundle-complete-eligible").candidate
    reordered = _refinalize(original.model_copy(update={"runs": tuple(reversed(original.runs))}))

    original_result = evaluate_evidence_bundle(original)
    reordered_result = evaluate_evidence_bundle(reordered)

    assert reordered_result.bundle_valid is True
    assert (
        reordered_result.run_accountability_complete == original_result.run_accountability_complete
    )
    assert reordered_result.comparison == original_result.comparison


def test_artifact_order_does_not_change_hash_manifest_or_validity() -> None:
    original = _case("bundle-complete-eligible").candidate
    reordered_artifacts = tuple(reversed(original.artifacts))
    reordered = _refinalize(original.model_copy(update={"artifacts": reordered_artifacts}))

    assert artifact_hash_manifest_sha256(reordered.artifacts) == artifact_hash_manifest_sha256(
        original.artifacts
    )
    assert evaluate_evidence_bundle(reordered).bundle_valid is True


def test_omitting_an_excluded_run_is_worse_than_retaining_it() -> None:
    retained = evaluate_evidence_bundle(_case("bundle-explicit-exclusion-retained").candidate)
    omitted = evaluate_evidence_bundle(_case("bundle-missing-scheduled-run").candidate)

    assert retained.bundle_valid is True
    assert omitted.bundle_valid is False
    assert omitted.run_accountability_complete is False


def test_report_prose_cannot_override_ineligible_comparison() -> None:
    result = evaluate_evidence_bundle(_case("bundle-retrieval-mismatch-ineligible").candidate)

    assert result.comparison.comparative_claims_permitted is False
    assert result.comparison.eligible_metric_families == ()
