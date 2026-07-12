"""Build and verify frozen Gate 7 feedback-evidence fixtures and report."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.feedback import (
    FeedbackFixtureResult,
    FeedbackFixtureSet,
    Gate7EFCEvidenceManifest,
    Gate7EFCEvidenceReport,
    Gate7EFCEvidenceSummary,
)
from auragateway.evals.feedback import evaluate_feedback_trajectory

_ASSET_ROOT: Final = Path("data/evals/feedback/efc-v1")
_FIXTURE_PATH: Final = _ASSET_ROOT / "fixtures.json"
_REPORT_PATH: Final = _ASSET_ROOT / "report.json"
_MANIFEST_PATH: Final = _ASSET_ROOT / "manifest.json"
_EPISODE_MANIFEST_PATH: Final = Path("data/evals/episodes/manifest.json")
_QUALITY_GATE_MANIFEST_PATH: Final = Path("data/evals/quality/noninferiority-v1/manifest.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class EFCEvidenceAssetError(Exception):
    """Expected EFC asset failure with a safe machine-readable envelope."""

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


class EFCEvidenceAssetErrorEnvelope(BaseModel):
    """Safe CLI failure without raw task or feedback content."""

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
        raise EFCEvidenceAssetError(
            error_code=error_code,
            safe_message="Required EFC evidence asset was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EFCEvidenceAssetError(
            error_code="EFC_EVIDENCE_ASSET_INVALID_JSON",
            safe_message="EFC evidence asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT], error_code: str) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path, error_code))
    except ValidationError as exc:
        raise EFCEvidenceAssetError(
            error_code="EFC_EVIDENCE_ASSET_VALIDATION_FAILED",
            safe_message="EFC evidence asset failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _require_hash_bound_asset(repo_root: Path, path: Path, error_code: str) -> str:
    try:
        return _sha256_bytes((repo_root / path).read_bytes())
    except FileNotFoundError as exc:
        raise EFCEvidenceAssetError(
            error_code=error_code,
            safe_message="A required upstream evidence asset was not found.",
            path=str(repo_root / path),
        ) from exc


def build_assets(
    repo_root: Path,
) -> tuple[Gate7EFCEvidenceReport, Gate7EFCEvidenceManifest, Gate7EFCEvidenceSummary]:
    """Build metadata-only EFC fixture evidence."""

    fixtures = _load_model(
        repo_root / _FIXTURE_PATH,
        FeedbackFixtureSet,
        "EFC_EVIDENCE_FIXTURES_NOT_FOUND",
    )
    results: list[FeedbackFixtureResult] = []
    for case in fixtures.cases:
        case_summary = evaluate_feedback_trajectory(case.trajectory)
        expectation_matched = (
            case_summary.efc_evidence_passed == case.expected_pass
            and case_summary.failure_codes == case.expected_failure_codes
        )
        results.append(
            FeedbackFixtureResult(
                case_id=case.case_id,
                summary=case_summary,
                expectation_matched=expectation_matched,
                negative_control=case.negative_control,
            )
        )

    result_tuple = tuple(results)
    report = Gate7EFCEvidenceReport(
        fixture_set_id=fixtures.fixture_set_id,
        results=result_tuple,
        fixture_count=len(result_tuple),
        negative_control_count=sum(result.negative_control for result in result_tuple),
        task_sufficiency_pass_count=sum(
            result.summary.task_sufficiency_passed for result in result_tuple
        ),
        all_expectations_matched=all(result.expectation_matched for result in result_tuple),
        efc_evidence_controls_passed=all(result.expectation_matched for result in result_tuple),
    )
    report_bytes = _model_json_bytes(report)
    manifest = Gate7EFCEvidenceManifest(
        fixture_path=_FIXTURE_PATH.as_posix(),
        fixture_sha256=_require_hash_bound_asset(
            repo_root,
            _FIXTURE_PATH,
            "EFC_EVIDENCE_FIXTURES_NOT_FOUND",
        ),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=_sha256_bytes(report_bytes),
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
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        efc_evidence_controls_passed=report.efc_evidence_controls_passed,
    )
    cli_summary = Gate7EFCEvidenceSummary(
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        task_sufficiency_pass_count=report.task_sufficiency_pass_count,
        efc_evidence_controls_passed=report.efc_evidence_controls_passed,
        synthetic_fixture_execution=report.synthetic_fixture_execution,
        measured_execution_permitted=report.measured_execution_permitted,
        universal_efc_score_reported=report.universal_efc_score_reported,
        fixture_sha256=manifest.fixture_sha256,
        report_sha256=manifest.report_sha256,
    )
    return report, manifest, cli_summary


def write_assets(repo_root: Path) -> Gate7EFCEvidenceSummary:
    """Write deterministic EFC report and manifest."""

    report, manifest, summary = build_assets(repo_root)
    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _REPORT_PATH).write_bytes(_model_json_bytes(report))
    (repo_root / _MANIFEST_PATH).write_bytes(_model_json_bytes(manifest))
    return summary


def verify_assets(repo_root: Path) -> Gate7EFCEvidenceSummary:
    """Rebuild and compare persisted EFC evidence."""

    expected_report, expected_manifest, summary = build_assets(repo_root)
    persisted_report = _load_model(
        repo_root / _REPORT_PATH,
        Gate7EFCEvidenceReport,
        "EFC_EVIDENCE_REPORT_NOT_FOUND",
    )
    persisted_manifest = _load_model(
        repo_root / _MANIFEST_PATH,
        Gate7EFCEvidenceManifest,
        "EFC_EVIDENCE_MANIFEST_NOT_FOUND",
    )
    if persisted_report != expected_report:
        raise EFCEvidenceAssetError(
            error_code="EFC_EVIDENCE_REPORT_MISMATCH",
            safe_message="Persisted EFC report does not match deterministic output.",
            path=str(repo_root / _REPORT_PATH),
        )
    if persisted_manifest != expected_manifest:
        raise EFCEvidenceAssetError(
            error_code="EFC_EVIDENCE_MANIFEST_MISMATCH",
            safe_message="Persisted EFC manifest does not match deterministic output.",
            path=str(repo_root / _MANIFEST_PATH),
        )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for deterministic EFC evidence."""

    args = _parse_args(argv)
    try:
        summary = (
            write_assets(args.repo_root)
            if args.command == "build"
            else verify_assets(args.repo_root)
        )
    except EFCEvidenceAssetError as exc:
        envelope = EFCEvidenceAssetErrorEnvelope(
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
