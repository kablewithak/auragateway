"""Deterministic immutable-bundle and comparison-eligibility evaluation."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable

from pydantic import BaseModel

from auragateway.contracts.evidence_bundle import (
    CONFIGURATION_FIELD_NAMES,
    ArtifactHashEntry,
    BenchmarkCondition,
    BundleFailureCode,
    ComparisonEligibilityDecision,
    ComparisonEligibilityStatus,
    EvidenceBundleCandidate,
    EvidenceBundleEvaluationResult,
    EvidenceBundleFixtureCase,
    EvidenceBundleFixtureResult,
    EvidenceBundleType,
    MetricEligibilityResult,
    MetricFamily,
    RunStatusCount,
    RunTerminalStatus,
)

_REQUIRED_COMMON_ARTIFACTS = frozenset(
    {
        "benchmark_manifest.json",
        "configuration_fingerprint.json",
        "environment_manifest.json",
        "run_results.jsonl",
        "failures.jsonl",
        "exclusions.jsonl",
        "reruns.jsonl",
        "comparison_eligibility.json",
        "sanitized_trace_samples.jsonl",
        "artifact_hashes.json",
        "bundle_manifest.json",
    }
)
_REQUIRED_BENCHMARK_ARTIFACTS = _REQUIRED_COMMON_ARTIFACTS | {
    "comparison.csv",
    "benchmark_report.md",
}
_FORBIDDEN_PUBLIC_TOKENS = frozenset(
    {
        ".env",
        "credential",
        "credentials",
        "protected-review",
        "protected_review",
        "provider-payload",
        "provider_payload",
        "raw-prompt",
        "raw-prompts",
        "raw_prompt",
        "raw_prompts",
        "secret",
        "secrets",
    }
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_payload(model: BaseModel, *, exclude: set[str] | None = None) -> bytes:
    payload = model.model_dump(mode="json", exclude=exclude or set(), exclude_none=True)
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return normalized.encode("utf-8")


def configuration_fingerprint_sha256(candidate: BaseModel) -> str:
    """Calculate the canonical digest for one configuration snapshot."""

    return _sha256_bytes(_canonical_payload(candidate, exclude={"fingerprint_sha256"}))


def artifact_hash_manifest_sha256(artifacts: Iterable[ArtifactHashEntry]) -> str:
    """Hash the non-recursive artifact inventory in deterministic path order."""

    non_recursive = tuple(
        sorted(
            (
                item
                for item in artifacts
                if item.relative_path not in {"artifact_hashes.json", "bundle_manifest.json"}
            ),
            key=lambda item: item.relative_path,
        )
    )
    payload = [item.model_dump(mode="json", exclude_none=True) for item in non_recursive]
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(normalized.encode("utf-8"))


def finalized_bundle_content_sha256(candidate: EvidenceBundleCandidate) -> str:
    """Calculate the append-only finalized bundle content digest."""

    return _sha256_bytes(_canonical_payload(candidate, exclude={"finalized_content_sha256"}))


def _required_artifacts(bundle_type: EvidenceBundleType) -> frozenset[str]:
    if bundle_type is EvidenceBundleType.BENCHMARK:
        return frozenset(_REQUIRED_BENCHMARK_ARTIFACTS)
    return frozenset(_REQUIRED_COMMON_ARTIFACTS)


def _contains_forbidden_artifact(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    parts = set(normalized.split("/"))
    return any(token in normalized or token in parts for token in _FORBIDDEN_PUBLIC_TOKENS)


def _evaluate_comparison(candidate: EvidenceBundleCandidate) -> ComparisonEligibilityDecision:
    snapshots = candidate.configuration_snapshots
    snapshot_payloads = tuple(
        item.model_dump(
            mode="json",
            exclude={"condition_id", "fingerprint_sha256"},
            exclude_none=True,
        )
        for item in snapshots
    )
    mismatched_fields = tuple(
        sorted(
            field
            for field in CONFIGURATION_FIELD_NAMES
            if len({payload[field] for payload in snapshot_payloads}) > 1
        )
    )

    metric_results: list[MetricEligibilityResult] = []
    for rule in candidate.comparison_contract.rules:
        invalidating = tuple(
            field for field in mismatched_fields if field not in rule.allowed_mismatch_fields
        )
        metric_results.append(
            MetricEligibilityResult(
                metric_family=rule.metric_family,
                eligible=not invalidating,
                mismatched_fields=invalidating,
            )
        )

    results = tuple(metric_results)
    eligible = tuple(item.metric_family for item in results if item.eligible)
    invalidated = tuple(item.metric_family for item in results if not item.eligible)
    if len(eligible) == len(MetricFamily):
        status = ComparisonEligibilityStatus.ELIGIBLE
    elif eligible:
        status = ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE
    else:
        status = ComparisonEligibilityStatus.INELIGIBLE
    return ComparisonEligibilityDecision(
        contract_version=candidate.comparison_contract.contract_version,
        status=status,
        metric_results=results,
        eligible_metric_families=eligible,
        invalidated_metric_families=invalidated,
        mismatched_fields=mismatched_fields,
        comparative_claims_permitted=bool(eligible),
    )


def evaluate_evidence_bundle(candidate: EvidenceBundleCandidate) -> EvidenceBundleEvaluationResult:
    """Evaluate run accountability, immutability, public safety, and eligibility."""

    failures: list[BundleFailureCode] = []

    snapshot_digests_valid = all(
        snapshot.fingerprint_sha256 == configuration_fingerprint_sha256(snapshot)
        for snapshot in candidate.configuration_snapshots
    )
    if not snapshot_digests_valid:
        failures.append(BundleFailureCode.FINGERPRINT_DIGEST_MISMATCH)

    planned = {item.run_id: item for item in candidate.run_plan.scheduled_runs}
    observed = {item.run_id: item for item in candidate.runs}
    run_accountability_complete = set(planned) == set(observed)
    if not run_accountability_complete:
        failures.append(BundleFailureCode.RUN_ACCOUNTABILITY_INCOMPLETE)

    run_records_match = all(
        run_id in observed
        and observed[run_id].condition_id is slot.condition_id
        and observed[run_id].episode_id == slot.episode_id
        for run_id, slot in planned.items()
    )
    if not run_records_match:
        failures.append(BundleFailureCode.RUN_RECORD_MISMATCH)
        run_accountability_complete = False

    artifact_paths = {item.relative_path for item in candidate.artifacts}
    artifact_inventory_complete = _required_artifacts(candidate.bundle_type) <= artifact_paths
    if not artifact_inventory_complete:
        failures.append(BundleFailureCode.REQUIRED_ARTIFACT_MISSING)

    private_artifacts_absent = not any(
        _contains_forbidden_artifact(item.relative_path) for item in candidate.artifacts
    )
    if not private_artifacts_absent:
        failures.append(BundleFailureCode.FORBIDDEN_PUBLIC_ARTIFACT)

    artifact_manifest_valid = (
        candidate.artifact_hash_manifest_sha256
        == artifact_hash_manifest_sha256(candidate.artifacts)
    )
    if not artifact_manifest_valid:
        failures.append(BundleFailureCode.ARTIFACT_HASH_MANIFEST_MISMATCH)

    finalized_digest_valid = candidate.finalized_content_sha256 == finalized_bundle_content_sha256(
        candidate
    )
    if not finalized_digest_valid:
        failures.append(BundleFailureCode.BUNDLE_CONTENT_DIGEST_MISMATCH)

    supersession_valid = True
    if candidate.supersession is not None:
        supersession_valid = (
            candidate.supersession.supersedes_bundle_id != candidate.evidence_bundle_id
            and set(candidate.supersession.affected_artifacts) <= artifact_paths
        )
    if not supersession_valid:
        failures.append(BundleFailureCode.INVALID_SUPERSESSION)

    counts = Counter(item.terminal_status for item in candidate.runs)
    terminal_counts = tuple(
        RunStatusCount(terminal_status=status, count=counts.get(status, 0))
        for status in RunTerminalStatus
    )
    comparison = _evaluate_comparison(candidate)
    structural_controls = (
        run_accountability_complete,
        snapshot_digests_valid,
        artifact_inventory_complete,
        private_artifacts_absent,
        artifact_manifest_valid,
        finalized_digest_valid,
        supersession_valid,
    )
    return EvidenceBundleEvaluationResult(
        evidence_bundle_id=candidate.evidence_bundle_id,
        bundle_valid=all(structural_controls),
        run_accountability_complete=run_accountability_complete,
        fingerprint_digests_valid=snapshot_digests_valid,
        artifact_inventory_complete=artifact_inventory_complete,
        private_artifacts_absent=private_artifacts_absent,
        artifact_hash_manifest_valid=artifact_manifest_valid,
        finalized_content_digest_valid=finalized_digest_valid,
        supersession_valid=supersession_valid,
        terminal_status_counts=terminal_counts,
        comparison=comparison,
        failure_codes=tuple(dict.fromkeys(failures)),
    )


def evaluate_fixture_case(case: EvidenceBundleFixtureCase) -> EvidenceBundleFixtureResult:
    """Evaluate one fixed bundle case without retaining raw benchmark content."""

    evaluation = evaluate_evidence_bundle(case.candidate)
    expectation_matched = all(
        (
            evaluation.bundle_valid == case.expected_bundle_valid,
            evaluation.comparison.status is case.expected_eligibility_status,
            evaluation.failure_codes == case.expected_failure_codes,
            evaluation.comparison.invalidated_metric_families
            == case.expected_invalidated_metric_families,
        )
    )
    return EvidenceBundleFixtureResult(
        case_id=case.case_id,
        evaluation=evaluation,
        expectation_matched=expectation_matched,
        negative_control=case.negative_control,
    )


def condition_order() -> tuple[BenchmarkCondition, ...]:
    """Expose deterministic condition ordering for tests and fixture builders."""

    return tuple(BenchmarkCondition)
