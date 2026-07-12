"""Build and verify deterministic Gate 5 route and retry regulation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.route_regulation import (
    Gate5RegulationCaseResult,
    Gate5RegulationFixtureSet,
    Gate5RegulationManifest,
    Gate5RegulationReport,
    Gate5RegulationSummary,
    RegulationCaseCategory,
    RetryDecisionCode,
    RouteRegulationCode,
)
from auragateway.routing.regulation import authorize_retry, regulate_route_policy

_DEFAULT_FIXTURES = Path("data/provider_fixtures/routing/regulation_cases.json")
_DEFAULT_REPORT = Path("data/provider_fixtures/routing/regulation_report.json")
_DEFAULT_MANIFEST = Path("data/provider_fixtures/routing/regulation_manifest.json")


class RouteRegulationEvidenceError(Exception):
    """Expected Gate 5 evidence failure with bounded diagnostics."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class RouteRegulationErrorEnvelope(BaseModel):
    """Metadata-only CLI error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


ModelT = TypeVar("ModelT", bound=BaseModel)


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, not_found_code: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RouteRegulationEvidenceError(
            not_found_code,
            "Required Gate 5 regulation artifact was not found.",
            str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RouteRegulationEvidenceError(
            "ROUTE_REGULATION_ARTIFACT_INVALID_JSON",
            "Gate 5 regulation artifact is not valid JSON.",
            str(path),
        ) from exc


def _load_model(path: Path, model_type: type[ModelT], code: str) -> ModelT:
    try:
        return model_type.model_validate(_load_json(path, f"{code}_NOT_FOUND"))
    except ValidationError as exc:
        raise RouteRegulationEvidenceError(
            f"{code}_VALIDATION_FAILED",
            "Gate 5 regulation artifact failed typed validation.",
            str(path),
            _validation_messages(exc),
        ) from exc


def _write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        model.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_report(fixtures: Gate5RegulationFixtureSet) -> Gate5RegulationReport:
    results: list[Gate5RegulationCaseResult] = []
    for route_case in fixtures.route_cases:
        route_decision = regulate_route_policy(route_case.request)
        results.append(
            Gate5RegulationCaseResult(
                case_id=route_case.case_id,
                category=RegulationCaseCategory.ROUTE,
                actual_status=route_decision.status,
                actual_code=route_decision.decision_code,
                expectation_matched=(
                    route_decision.status is route_case.expected_status
                    and route_decision.decision_code is route_case.expected_code
                ),
                negative_control=route_case.negative_control,
            )
        )
    for retry_case in fixtures.retry_cases:
        retry_decision = authorize_retry(retry_case.request)
        results.append(
            Gate5RegulationCaseResult(
                case_id=retry_case.case_id,
                category=RegulationCaseCategory.RETRY,
                actual_status=retry_decision.status,
                actual_code=retry_decision.decision_code,
                expectation_matched=(
                    retry_decision.status is retry_case.expected_status
                    and retry_decision.decision_code is retry_case.expected_code
                ),
                negative_control=retry_case.negative_control,
            )
        )

    result_by_id = {result.case_id: result for result in results}
    all_expectations_matched = all(result.expectation_matched for result in results)
    route_thrash_detected = (
        result_by_id["second-route-change-blocked"].actual_code
        is RouteRegulationCode.BLOCKED_ROUTE_THRASH
    )
    ambiguous_duplicate_risk_blocked = (
        result_by_id["ambiguous-response-retry-blocked"].actual_code
        is RetryDecisionCode.BLOCKED_AMBIGUOUS_DUPLICATE_RISK
    )
    retry_budget_enforced = (
        result_by_id["retry-budget-exhausted"].actual_code
        is RetryDecisionCode.BLOCKED_RETRY_BUDGET_EXHAUSTED
    )
    invalid_retry_detected = (
        result_by_id["repeated-recovery-action-blocked"].actual_code
        is RetryDecisionCode.BLOCKED_INVALID_RETRY
    )
    gate_passed = all(
        (
            all_expectations_matched,
            route_thrash_detected,
            ambiguous_duplicate_risk_blocked,
            retry_budget_enforced,
            invalid_retry_detected,
        )
    )
    return Gate5RegulationReport(
        status="passed" if gate_passed else "failed",
        fixture_set_id=fixtures.fixture_set_id,
        results=tuple(results),
        fixture_count=len(results),
        negative_control_count=sum(result.negative_control for result in results),
        all_expectations_matched=all_expectations_matched,
        route_thrash_detected=route_thrash_detected,
        ambiguous_duplicate_risk_blocked=ambiguous_duplicate_risk_blocked,
        retry_budget_enforced=retry_budget_enforced,
        invalid_retry_detected=invalid_retry_detected,
        gate_5_regulation_passed=gate_passed,
    )


def _summary(
    fixtures_path: Path,
    report_path: Path,
    report: Gate5RegulationReport,
) -> Gate5RegulationSummary:
    return Gate5RegulationSummary(
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        gate_5_regulation_passed=report.gate_5_regulation_passed,
        fixture_sha256=_sha256_path(fixtures_path),
        report_sha256=_sha256_path(report_path),
    )


def build_route_regulation(repo_root: Path) -> Gate5RegulationSummary:
    """Build the deterministic Gate 5 report and frozen manifest."""

    fixtures_path = repo_root / _DEFAULT_FIXTURES
    report_path = repo_root / _DEFAULT_REPORT
    manifest_path = repo_root / _DEFAULT_MANIFEST
    fixtures = _load_model(
        fixtures_path,
        Gate5RegulationFixtureSet,
        "ROUTE_REGULATION_FIXTURE_SET",
    )
    report = _build_report(fixtures)
    if not report.gate_5_regulation_passed:
        raise RouteRegulationEvidenceError(
            "GATE_5_ROUTE_REGULATION_FAILED",
            "Deterministic route and retry fixtures did not satisfy Gate 5.",
        )
    _write_model(report_path, report)
    manifest = Gate5RegulationManifest(
        fixture_path=_DEFAULT_FIXTURES.as_posix(),
        fixture_sha256=_sha256_path(fixtures_path),
        report_path=_DEFAULT_REPORT.as_posix(),
        report_sha256=_sha256_path(report_path),
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        gate_5_regulation_passed=report.gate_5_regulation_passed,
    )
    _write_model(manifest_path, manifest)
    return _summary(fixtures_path, report_path, report)


def verify_route_regulation(repo_root: Path) -> Gate5RegulationSummary:
    """Verify frozen Gate 5 hashes and deterministic report reproduction."""

    fixtures_path = repo_root / _DEFAULT_FIXTURES
    report_path = repo_root / _DEFAULT_REPORT
    manifest_path = repo_root / _DEFAULT_MANIFEST
    manifest = _load_model(
        manifest_path,
        Gate5RegulationManifest,
        "ROUTE_REGULATION_MANIFEST",
    )
    if _sha256_path(fixtures_path) != manifest.fixture_sha256:
        raise RouteRegulationEvidenceError(
            "ROUTE_REGULATION_FIXTURE_HASH_MISMATCH",
            "Gate 5 fixture hash does not match the frozen manifest.",
            str(fixtures_path),
        )
    if _sha256_path(report_path) != manifest.report_sha256:
        raise RouteRegulationEvidenceError(
            "ROUTE_REGULATION_REPORT_HASH_MISMATCH",
            "Gate 5 report hash does not match the frozen manifest.",
            str(report_path),
        )
    fixtures = _load_model(
        fixtures_path,
        Gate5RegulationFixtureSet,
        "ROUTE_REGULATION_FIXTURE_SET",
    )
    frozen_report = _load_model(
        report_path,
        Gate5RegulationReport,
        "ROUTE_REGULATION_REPORT",
    )
    rebuilt_report = _build_report(fixtures)
    if rebuilt_report != frozen_report:
        raise RouteRegulationEvidenceError(
            "ROUTE_REGULATION_REPORT_REPRODUCTION_MISMATCH",
            "Rebuilt Gate 5 report does not match the frozen report.",
            str(report_path),
        )
    if (
        manifest.fixture_count != frozen_report.fixture_count
        or manifest.negative_control_count != frozen_report.negative_control_count
        or manifest.gate_5_regulation_passed != frozen_report.gate_5_regulation_passed
    ):
        raise RouteRegulationEvidenceError(
            "ROUTE_REGULATION_MANIFEST_REPORT_MISMATCH",
            "Gate 5 manifest does not match the frozen report summary.",
            str(manifest_path),
        )
    return _summary(fixtures_path, report_path, frozen_report)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the Gate 5 evidence builder or verifier with safe JSON output."""

    args = _parse_args(argv)
    try:
        if args.command == "build":
            summary = build_route_regulation(args.repo_root)
        else:
            summary = verify_route_regulation(args.repo_root)
    except RouteRegulationEvidenceError as exc:
        envelope = RouteRegulationErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
