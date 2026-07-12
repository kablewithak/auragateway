"""Build and verify frozen Gate 6 blinded-review preparation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.blinded_quality import (
    BlindedQualityFixtureSet,
    BlindedQualityRubric,
    Gate6BlindedQualityManifest,
    Gate6BlindedQualityReport,
    Gate6BlindedQualitySummary,
    ReviewAssignmentManifest,
)
from auragateway.contracts.episodes import BlindedReviewProtocol, FunctionalEpisodeSet
from auragateway.evals.blinded_quality import build_assignment_manifest, evaluate_fixture_case

_ASSET_ROOT: Final = Path("data/evals/quality/blinded-v1")
_RUBRIC_PATH: Final = _ASSET_ROOT / "rubric.json"
_ASSIGNMENT_PATH: Final = _ASSET_ROOT / "assignment_manifest.json"
_FIXTURE_PATH: Final = _ASSET_ROOT / "fixtures.json"
_REPORT_PATH: Final = _ASSET_ROOT / "report.json"
_MANIFEST_PATH: Final = _ASSET_ROOT / "manifest.json"
_EPISODE_SET_PATH: Final = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
_PROTOCOL_PATH: Final = Path("data/evals/episodes/blinded_review_protocol.json")
_EPISODE_MANIFEST_PATH: Final = Path("data/evals/episodes/manifest.json")
_DETERMINISTIC_MANIFEST_PATH: Final = Path("data/evals/quality/deterministic-v1/manifest.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class BlindedQualityAssetError(Exception):
    """Expected asset failure with a safe machine-readable envelope."""

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


class BlindedQualityAssetErrorEnvelope(BaseModel):
    """Safe CLI failure without raw protected review content."""

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
        raise BlindedQualityAssetError(
            error_code=error_code,
            safe_message="Required blinded quality asset was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BlindedQualityAssetError(
            error_code="BLINDED_QUALITY_ASSET_INVALID_JSON",
            safe_message="Blinded quality asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT], error_code: str) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path, error_code))
    except ValidationError as exc:
        raise BlindedQualityAssetError(
            error_code="BLINDED_QUALITY_ASSET_VALIDATION_FAILED",
            safe_message="Blinded quality asset failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _require_hash_bound_asset(repo_root: Path, path: Path, error_code: str) -> str:
    try:
        return _sha256_bytes((repo_root / path).read_bytes())
    except FileNotFoundError as exc:
        raise BlindedQualityAssetError(
            error_code=error_code,
            safe_message="A required upstream evidence asset was not found.",
            path=str(repo_root / path),
        ) from exc


def build_assets(
    repo_root: Path,
) -> tuple[
    ReviewAssignmentManifest,
    Gate6BlindedQualityReport,
    Gate6BlindedQualityManifest,
    Gate6BlindedQualitySummary,
]:
    """Build deterministic blinded-review preparation and fixture evidence."""

    rubric = _load_model(
        repo_root / _RUBRIC_PATH,
        BlindedQualityRubric,
        "BLINDED_QUALITY_RUBRIC_NOT_FOUND",
    )
    fixtures = _load_model(
        repo_root / _FIXTURE_PATH,
        BlindedQualityFixtureSet,
        "BLINDED_QUALITY_FIXTURES_NOT_FOUND",
    )
    episodes = _load_model(
        repo_root / _EPISODE_SET_PATH,
        FunctionalEpisodeSet,
        "FUNCTIONAL_EPISODE_SET_NOT_FOUND",
    )
    protocol = _load_model(
        repo_root / _PROTOCOL_PATH,
        BlindedReviewProtocol,
        "BLINDED_REVIEW_PROTOCOL_NOT_FOUND",
    )

    if protocol.public_trace_contains_raw_content:
        raise BlindedQualityAssetError(
            error_code="PUBLIC_RAW_REVIEW_CONTENT_PROHIBITED",
            safe_message="Public traces must not contain raw review content.",
        )
    if not protocol.protected_review_export_required:
        raise BlindedQualityAssetError(
            error_code="PROTECTED_REVIEW_EXPORT_REQUIRED",
            safe_message="Blinded review requires protected exports.",
        )
    if not protocol.adjudicator_must_be_independent:
        raise BlindedQualityAssetError(
            error_code="INDEPENDENT_ADJUDICATOR_REQUIRED",
            safe_message="Material disagreements require an independent adjudicator.",
        )

    assignments = build_assignment_manifest(
        (episode.episode_id for episode in episodes.episodes),
        protocol,
    )
    results = tuple(evaluate_fixture_case(case, rubric) for case in fixtures.cases)
    report = Gate6BlindedQualityReport(
        fixture_set_id=fixtures.fixture_set_id,
        assignment_manifest_id=assignments.manifest_id,
        results=results,
        fixture_count=len(results),
        negative_control_count=sum(item.negative_control for item in results),
        material_disagreement_fixture_count=sum(
            item.material_disagreement is True for item in results
        ),
        all_expectations_matched=all(item.expectation_matched for item in results),
        blinded_workflow_passed=all(item.expectation_matched for item in results),
    )

    assignment_bytes = _model_json_bytes(assignments)
    report_bytes = _model_json_bytes(report)
    manifest = Gate6BlindedQualityManifest(
        rubric_path=_RUBRIC_PATH.as_posix(),
        rubric_sha256=_require_hash_bound_asset(
            repo_root,
            _RUBRIC_PATH,
            "BLINDED_QUALITY_RUBRIC_NOT_FOUND",
        ),
        assignment_path=_ASSIGNMENT_PATH.as_posix(),
        assignment_sha256=_sha256_bytes(assignment_bytes),
        fixture_path=_FIXTURE_PATH.as_posix(),
        fixture_sha256=_require_hash_bound_asset(
            repo_root,
            _FIXTURE_PATH,
            "BLINDED_QUALITY_FIXTURES_NOT_FOUND",
        ),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=_sha256_bytes(report_bytes),
        protocol_path=_PROTOCOL_PATH.as_posix(),
        protocol_sha256=_require_hash_bound_asset(
            repo_root,
            _PROTOCOL_PATH,
            "BLINDED_REVIEW_PROTOCOL_NOT_FOUND",
        ),
        episode_manifest_path=_EPISODE_MANIFEST_PATH.as_posix(),
        episode_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _EPISODE_MANIFEST_PATH,
            "EPISODE_MANIFEST_NOT_FOUND",
        ),
        deterministic_quality_manifest_path=_DETERMINISTIC_MANIFEST_PATH.as_posix(),
        deterministic_quality_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _DETERMINISTIC_MANIFEST_PATH,
            "DETERMINISTIC_QUALITY_MANIFEST_NOT_FOUND",
        ),
        primary_assignment_count=assignments.primary_assignment_count,
        secondary_assignment_count=assignments.secondary_assignment_count,
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        blinded_workflow_passed=report.blinded_workflow_passed,
    )
    summary = Gate6BlindedQualitySummary(
        rubric_id=rubric.rubric_id,
        primary_assignment_count=assignments.primary_assignment_count,
        secondary_assignment_count=assignments.secondary_assignment_count,
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        material_disagreement_fixture_count=report.material_disagreement_fixture_count,
        blinded_workflow_passed=report.blinded_workflow_passed,
        measured_execution_permitted=report.measured_execution_permitted,
    )
    return assignments, report, manifest, summary


def write_assets(repo_root: Path) -> Gate6BlindedQualitySummary:
    """Write deterministic assignments, report, and manifest."""

    assignments, report, manifest, summary = build_assets(repo_root)
    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _ASSIGNMENT_PATH).write_bytes(_model_json_bytes(assignments))
    (repo_root / _REPORT_PATH).write_bytes(_model_json_bytes(report))
    (repo_root / _MANIFEST_PATH).write_bytes(_model_json_bytes(manifest))
    return summary


def verify_assets(repo_root: Path) -> Gate6BlindedQualitySummary:
    """Rebuild and compare persisted blinded quality evidence."""

    expected_assignments, expected_report, expected_manifest, summary = build_assets(repo_root)
    persisted_assignments = _load_model(
        repo_root / _ASSIGNMENT_PATH,
        ReviewAssignmentManifest,
        "BLINDED_QUALITY_ASSIGNMENTS_NOT_FOUND",
    )
    persisted_report = _load_model(
        repo_root / _REPORT_PATH,
        Gate6BlindedQualityReport,
        "BLINDED_QUALITY_REPORT_NOT_FOUND",
    )
    persisted_manifest = _load_model(
        repo_root / _MANIFEST_PATH,
        Gate6BlindedQualityManifest,
        "BLINDED_QUALITY_MANIFEST_NOT_FOUND",
    )
    if persisted_assignments != expected_assignments:
        raise BlindedQualityAssetError(
            error_code="BLINDED_QUALITY_ASSIGNMENT_MISMATCH",
            safe_message="Persisted review assignments do not match deterministic output.",
            path=str(repo_root / _ASSIGNMENT_PATH),
        )
    if persisted_report != expected_report:
        raise BlindedQualityAssetError(
            error_code="BLINDED_QUALITY_REPORT_MISMATCH",
            safe_message="Persisted blinded quality report does not match deterministic output.",
            path=str(repo_root / _REPORT_PATH),
        )
    if persisted_manifest != expected_manifest:
        raise BlindedQualityAssetError(
            error_code="BLINDED_QUALITY_MANIFEST_MISMATCH",
            safe_message="Persisted blinded quality manifest does not match deterministic output.",
            path=str(repo_root / _MANIFEST_PATH),
        )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for deterministic blinded quality evidence."""

    args = _parse_args(argv)
    try:
        summary = (
            write_assets(args.repo_root)
            if args.command == "build"
            else verify_assets(args.repo_root)
        )
    except BlindedQualityAssetError as exc:
        envelope = BlindedQualityAssetErrorEnvelope(
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
