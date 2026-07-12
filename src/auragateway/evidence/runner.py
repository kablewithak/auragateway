"""Build and verify frozen Gate 8 comparison-eligibility evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.evidence_bundle import (
    ComparisonEligibilityStatus,
    EvidenceBundleFixtureSet,
    Gate8EvidenceBundleManifest,
    Gate8EvidenceBundleReport,
    Gate8EvidenceBundleSummary,
)
from auragateway.evidence.bundle import evaluate_fixture_case

_ASSET_ROOT: Final = Path("data/evals/evidence/gate8-v1")
_FIXTURE_PATH: Final = _ASSET_ROOT / "fixtures.json"
_REPORT_PATH: Final = _ASSET_ROOT / "report.json"
_MANIFEST_PATH: Final = _ASSET_ROOT / "manifest.json"
_ADR_PATH: Final = Path(
    "docs/adr/ADR-0010-immutable-evidence-bundles-and-comparison-eligibility.md"
)
_EPISODE_MANIFEST_PATH: Final = Path("data/evals/episodes/manifest.json")
_QUALITY_GATE_MANIFEST_PATH: Final = Path("data/evals/quality/noninferiority-v1/manifest.json")
_EFC_MANIFEST_PATH: Final = Path("data/evals/feedback/efc-v1/manifest.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class EvidenceBundleAssetError(Exception):
    """Expected Gate 8 asset failure with safe details."""

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


class EvidenceBundleAssetErrorEnvelope(BaseModel):
    """Safe CLI failure without benchmark payloads."""

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
        raise EvidenceBundleAssetError(
            error_code=error_code,
            safe_message="Required Gate 8 evidence asset was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EvidenceBundleAssetError(
            error_code="GATE8_ASSET_INVALID_JSON",
            safe_message="Gate 8 evidence asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT], error_code: str) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path, error_code))
    except ValidationError as exc:
        raise EvidenceBundleAssetError(
            error_code="GATE8_ASSET_VALIDATION_FAILED",
            safe_message="Gate 8 evidence asset failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _require_hash_bound_asset(repo_root: Path, path: Path, error_code: str) -> str:
    try:
        return _sha256_bytes((repo_root / path).read_bytes())
    except FileNotFoundError as exc:
        raise EvidenceBundleAssetError(
            error_code=error_code,
            safe_message="A required upstream evidence asset was not found.",
            path=str(repo_root / path),
        ) from exc


def build_assets(
    repo_root: Path,
) -> tuple[Gate8EvidenceBundleReport, Gate8EvidenceBundleManifest, Gate8EvidenceBundleSummary]:
    """Build deterministic Gate 8 fixture, report, and manifest evidence."""

    fixtures = _load_model(
        repo_root / _FIXTURE_PATH,
        EvidenceBundleFixtureSet,
        "GATE8_FIXTURES_NOT_FOUND",
    )
    results = tuple(evaluate_fixture_case(case) for case in fixtures.cases)
    statuses = [item.evaluation.comparison.status for item in results]
    report = Gate8EvidenceBundleReport(
        fixture_set_id=fixtures.fixture_set_id,
        results=results,
        fixture_count=len(results),
        negative_control_count=sum(item.negative_control for item in results),
        valid_bundle_count=sum(item.evaluation.bundle_valid for item in results),
        fully_eligible_count=statuses.count(ComparisonEligibilityStatus.ELIGIBLE),
        partially_eligible_count=statuses.count(ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE),
        ineligible_count=statuses.count(ComparisonEligibilityStatus.INELIGIBLE),
        all_expectations_matched=all(item.expectation_matched for item in results),
        gate_8_controls_passed=all(item.expectation_matched for item in results),
    )
    report_bytes = _model_json_bytes(report)
    manifest = Gate8EvidenceBundleManifest(
        fixture_path=_FIXTURE_PATH.as_posix(),
        fixture_sha256=_require_hash_bound_asset(
            repo_root,
            _FIXTURE_PATH,
            "GATE8_FIXTURES_NOT_FOUND",
        ),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=_sha256_bytes(report_bytes),
        adr_path=_ADR_PATH.as_posix(),
        adr_sha256=_require_hash_bound_asset(
            repo_root,
            _ADR_PATH,
            "ADR_0010_NOT_FOUND",
        ),
        episode_manifest_path=_EPISODE_MANIFEST_PATH.as_posix(),
        episode_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _EPISODE_MANIFEST_PATH,
            "EPISODE_MANIFEST_NOT_FOUND",
        ),
        quality_gate_manifest_path=_QUALITY_GATE_MANIFEST_PATH.as_posix(),
        quality_gate_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _QUALITY_GATE_MANIFEST_PATH,
            "QUALITY_GATE_MANIFEST_NOT_FOUND",
        ),
        efc_manifest_path=_EFC_MANIFEST_PATH.as_posix(),
        efc_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _EFC_MANIFEST_PATH,
            "EFC_MANIFEST_NOT_FOUND",
        ),
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        gate_8_controls_passed=report.gate_8_controls_passed,
    )
    summary = Gate8EvidenceBundleSummary(
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        valid_bundle_count=report.valid_bundle_count,
        fully_eligible_count=report.fully_eligible_count,
        partially_eligible_count=report.partially_eligible_count,
        ineligible_count=report.ineligible_count,
        gate_8_controls_passed=report.gate_8_controls_passed,
        synthetic_fixture_execution=report.synthetic_fixture_execution,
        measured_execution_permitted=report.measured_execution_permitted,
    )
    return report, manifest, summary


def write_assets(repo_root: Path) -> Gate8EvidenceBundleSummary:
    """Write deterministic Gate 8 report and manifest."""

    report, manifest, summary = build_assets(repo_root)
    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _REPORT_PATH).write_bytes(_model_json_bytes(report))
    (repo_root / _MANIFEST_PATH).write_bytes(_model_json_bytes(manifest))
    return summary


def verify_assets(repo_root: Path) -> Gate8EvidenceBundleSummary:
    """Rebuild and compare persisted Gate 8 evidence."""

    expected_report, expected_manifest, summary = build_assets(repo_root)
    persisted_report = _load_model(
        repo_root / _REPORT_PATH,
        Gate8EvidenceBundleReport,
        "GATE8_REPORT_NOT_FOUND",
    )
    persisted_manifest = _load_model(
        repo_root / _MANIFEST_PATH,
        Gate8EvidenceBundleManifest,
        "GATE8_MANIFEST_NOT_FOUND",
    )
    if persisted_report != expected_report:
        raise EvidenceBundleAssetError(
            error_code="GATE8_REPORT_MISMATCH",
            safe_message="Persisted Gate 8 report does not match deterministic output.",
            path=str(repo_root / _REPORT_PATH),
        )
    if persisted_manifest != expected_manifest:
        raise EvidenceBundleAssetError(
            error_code="GATE8_MANIFEST_MISMATCH",
            safe_message="Persisted Gate 8 manifest does not match deterministic output.",
            path=str(repo_root / _MANIFEST_PATH),
        )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for deterministic Gate 8 evidence."""

    args = _parse_args(argv)
    try:
        summary = (
            write_assets(args.repo_root)
            if args.command == "build"
            else verify_assets(args.repo_root)
        )
    except EvidenceBundleAssetError as exc:
        envelope = EvidenceBundleAssetErrorEnvelope(
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
