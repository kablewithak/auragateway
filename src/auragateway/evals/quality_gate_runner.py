"""Build and verify frozen Gate 6 quality non-inferiority dry-run evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.quality_gate import (
    Gate6QualityNonInferiorityManifest,
    Gate6QualityNonInferiorityReport,
    Gate6QualityNonInferioritySummary,
    QualityGateFixtureSet,
    QualityGateStatus,
)
from auragateway.evals.quality_gate import evaluate_quality_gate_fixture

_ASSET_ROOT: Final = Path("data/evals/quality/noninferiority-v1")
_FIXTURE_PATH: Final = _ASSET_ROOT / "fixtures.json"
_REPORT_PATH: Final = _ASSET_ROOT / "report.json"
_MANIFEST_PATH: Final = _ASSET_ROOT / "manifest.json"
_DETERMINISTIC_MANIFEST_PATH: Final = Path("data/evals/quality/deterministic-v1/manifest.json")
_PROTECTED_REVIEW_MANIFEST_PATH: Final = Path("data/evals/quality/execution-v1/manifest.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class DeterministicQualityUpstreamManifest(BaseModel):
    """Minimum upstream controls required by the quality comparison dry run."""

    model_config = ConfigDict(extra="allow", frozen=True)

    deterministic_scorers_passed: Literal[True]
    measured_execution_permitted: Literal[False]
    retrieval_configuration_fingerprint: str


class ProtectedReviewUpstreamManifest(BaseModel):
    """Minimum protected-review controls required by the quality gate."""

    model_config = ConfigDict(extra="allow", frozen=True)

    execution_controls_passed: Literal[True]
    synthetic_fixture_execution: Literal[True]
    human_review_completed: Literal[False]
    measured_execution_permitted: Literal[False]


class QualityGateAssetError(Exception):
    """Expected asset failure with safe machine-readable details."""

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


class QualityGateAssetErrorEnvelope(BaseModel):
    """Safe CLI failure without raw benchmark content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _model_json_bytes(model: BaseModel) -> bytes:
    return (model.model_dump_json(indent=2) + "\n").encode("utf-8")


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "asset"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, error_code: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise QualityGateAssetError(
            error_code=error_code,
            safe_message="Required quality-gate asset was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QualityGateAssetError(
            error_code="QUALITY_GATE_ASSET_INVALID_JSON",
            safe_message="Quality-gate asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT], error_code: str) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path, error_code))
    except ValidationError as exc:
        raise QualityGateAssetError(
            error_code="QUALITY_GATE_ASSET_VALIDATION_FAILED",
            safe_message="Quality-gate asset failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _require_hash_bound_asset(repo_root: Path, path: Path, error_code: str) -> str:
    try:
        return _sha256_bytes((repo_root / path).read_bytes())
    except FileNotFoundError as exc:
        raise QualityGateAssetError(
            error_code=error_code,
            safe_message="A required upstream quality asset was not found.",
            path=str(repo_root / path),
        ) from exc


def build_assets(
    repo_root: Path,
) -> tuple[
    Gate6QualityNonInferiorityReport,
    Gate6QualityNonInferiorityManifest,
    Gate6QualityNonInferioritySummary,
]:
    """Build deterministic synthetic dry-run comparison evidence."""

    fixtures = _load_model(
        repo_root / _FIXTURE_PATH,
        QualityGateFixtureSet,
        "QUALITY_GATE_FIXTURES_NOT_FOUND",
    )
    deterministic_manifest = _load_model(
        repo_root / _DETERMINISTIC_MANIFEST_PATH,
        DeterministicQualityUpstreamManifest,
        "DETERMINISTIC_QUALITY_MANIFEST_NOT_FOUND",
    )
    _load_model(
        repo_root / _PROTECTED_REVIEW_MANIFEST_PATH,
        ProtectedReviewUpstreamManifest,
        "PROTECTED_REVIEW_MANIFEST_NOT_FOUND",
    )

    results = tuple(evaluate_quality_gate_fixture(case) for case in fixtures.cases)
    report = Gate6QualityNonInferiorityReport(
        fixture_set_id=fixtures.fixture_set_id,
        results=results,
        fixture_count=len(results),
        negative_control_count=sum(item.negative_control for item in results),
        passed_fixture_count=sum(
            item.result.status is QualityGateStatus.PASSED for item in results
        ),
        failed_fixture_count=sum(
            item.result.status is QualityGateStatus.FAILED for item in results
        ),
        ineligible_fixture_count=sum(
            item.result.status is QualityGateStatus.INELIGIBLE for item in results
        ),
        insufficient_sample_fixture_count=sum(
            item.result.status is QualityGateStatus.INSUFFICIENT_SAMPLE for item in results
        ),
        all_expectations_matched=all(item.expectation_matched for item in results),
        quality_gate_dry_run_passed=all(item.expectation_matched for item in results),
    )
    report_bytes = _model_json_bytes(report)
    manifest = Gate6QualityNonInferiorityManifest(
        fixture_path=_FIXTURE_PATH.as_posix(),
        fixture_sha256=_require_hash_bound_asset(
            repo_root,
            _FIXTURE_PATH,
            "QUALITY_GATE_FIXTURES_NOT_FOUND",
        ),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=_sha256_bytes(report_bytes),
        deterministic_quality_manifest_path=_DETERMINISTIC_MANIFEST_PATH.as_posix(),
        deterministic_quality_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _DETERMINISTIC_MANIFEST_PATH,
            "DETERMINISTIC_QUALITY_MANIFEST_NOT_FOUND",
        ),
        protected_review_manifest_path=_PROTECTED_REVIEW_MANIFEST_PATH.as_posix(),
        protected_review_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _PROTECTED_REVIEW_MANIFEST_PATH,
            "PROTECTED_REVIEW_MANIFEST_NOT_FOUND",
        ),
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        quality_gate_dry_run_passed=report.quality_gate_dry_run_passed,
    )
    fixture_sha256 = _require_hash_bound_asset(
        repo_root,
        _FIXTURE_PATH,
        "QUALITY_GATE_FIXTURES_NOT_FOUND",
    )
    summary = Gate6QualityNonInferioritySummary(
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        passed_fixture_count=report.passed_fixture_count,
        failed_fixture_count=report.failed_fixture_count,
        ineligible_fixture_count=report.ineligible_fixture_count,
        insufficient_sample_fixture_count=report.insufficient_sample_fixture_count,
        quality_gate_dry_run_passed=report.quality_gate_dry_run_passed,
        synthetic_dry_run=True,
        measured_execution_permitted=False,
        fixture_sha256=fixture_sha256,
        report_sha256=manifest.report_sha256,
    )
    if deterministic_manifest.retrieval_configuration_fingerprint != (
        fixtures.cases[0].comparison.conditions[0].retrieval_configuration_fingerprint
    ):
        raise QualityGateAssetError(
            error_code="FIXTURE_RETRIEVAL_FINGERPRINT_MISMATCH",
            safe_message=("Quality-gate fixtures do not use the frozen retrieval configuration."),
        )
    return report, manifest, summary


def write_assets(repo_root: Path) -> Gate6QualityNonInferioritySummary:
    """Write deterministic report and manifest artifacts."""

    report, manifest, summary = build_assets(repo_root)
    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _REPORT_PATH).write_bytes(_model_json_bytes(report))
    (repo_root / _MANIFEST_PATH).write_bytes(_model_json_bytes(manifest))
    return summary


def verify_assets(repo_root: Path) -> Gate6QualityNonInferioritySummary:
    """Rebuild and compare persisted quality-gate dry-run evidence."""

    expected_report, expected_manifest, summary = build_assets(repo_root)
    persisted_report = _load_model(
        repo_root / _REPORT_PATH,
        Gate6QualityNonInferiorityReport,
        "QUALITY_GATE_REPORT_NOT_FOUND",
    )
    persisted_manifest = _load_model(
        repo_root / _MANIFEST_PATH,
        Gate6QualityNonInferiorityManifest,
        "QUALITY_GATE_MANIFEST_NOT_FOUND",
    )
    if persisted_report != expected_report:
        raise QualityGateAssetError(
            error_code="QUALITY_GATE_REPORT_MISMATCH",
            safe_message="Persisted quality-gate report does not match deterministic output.",
            path=str(repo_root / _REPORT_PATH),
        )
    if persisted_manifest != expected_manifest:
        raise QualityGateAssetError(
            error_code="QUALITY_GATE_MANIFEST_MISMATCH",
            safe_message="Persisted quality-gate manifest does not match deterministic output.",
            path=str(repo_root / _MANIFEST_PATH),
        )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for quality non-inferiority dry-run evidence."""

    args = _parse_args(argv)
    try:
        summary = (
            write_assets(args.repo_root)
            if args.command == "build"
            else verify_assets(args.repo_root)
        )
    except QualityGateAssetError as exc:
        envelope = QualityGateAssetErrorEnvelope(
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
