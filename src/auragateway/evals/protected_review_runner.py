"""Build and verify frozen Gate 6 protected review-execution evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    Gate6BlindedQualityManifest,
    ReviewAssignmentManifest,
)
from auragateway.contracts.episodes import FunctionalEpisodeSet
from auragateway.contracts.protected_review import (
    Gate6ProtectedReviewExecutionManifest,
    Gate6ProtectedReviewExecutionReport,
    Gate6ProtectedReviewExecutionSummary,
    ProtectedReviewSubmissionSet,
)
from auragateway.evals.protected_review import (
    ProtectedReviewExecutionError,
    evaluate_protected_review_execution,
)

_ASSET_ROOT: Final = Path("data/evals/quality/execution-v1")
_SUBMISSION_PATH: Final = _ASSET_ROOT / "submissions.json"
_REPORT_PATH: Final = _ASSET_ROOT / "report.json"
_MANIFEST_PATH: Final = _ASSET_ROOT / "manifest.json"
_ASSIGNMENT_PATH: Final = Path("data/evals/quality/blinded-v1/assignment_manifest.json")
_RUBRIC_PATH: Final = Path("data/evals/quality/blinded-v1/rubric.json")
_BLINDED_MANIFEST_PATH: Final = Path("data/evals/quality/blinded-v1/manifest.json")
_EPISODE_SET_PATH: Final = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
_EPISODE_MANIFEST_PATH: Final = Path("data/evals/episodes/manifest.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class ProtectedReviewAssetError(Exception):
    """Expected protected-review asset failure with safe details."""

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


class ProtectedReviewAssetErrorEnvelope(BaseModel):
    """Safe CLI failure without protected review content."""

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
        raise ProtectedReviewAssetError(
            error_code=error_code,
            safe_message="Required protected review asset was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtectedReviewAssetError(
            error_code="PROTECTED_REVIEW_ASSET_INVALID_JSON",
            safe_message="Protected review asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT], error_code: str) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path, error_code))
    except ValidationError as exc:
        raise ProtectedReviewAssetError(
            error_code="PROTECTED_REVIEW_ASSET_VALIDATION_FAILED",
            safe_message="Protected review asset failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _require_hash_bound_asset(repo_root: Path, path: Path, error_code: str) -> str:
    try:
        return _sha256_bytes((repo_root / path).read_bytes())
    except FileNotFoundError as exc:
        raise ProtectedReviewAssetError(
            error_code=error_code,
            safe_message="A required upstream review evidence asset was not found.",
            path=str(repo_root / path),
        ) from exc


def build_assets(
    repo_root: Path,
) -> tuple[
    Gate6ProtectedReviewExecutionReport,
    Gate6ProtectedReviewExecutionManifest,
    Gate6ProtectedReviewExecutionSummary,
]:
    """Build metadata-only protected review execution evidence."""

    submissions = _load_model(
        repo_root / _SUBMISSION_PATH,
        ProtectedReviewSubmissionSet,
        "PROTECTED_REVIEW_SUBMISSIONS_NOT_FOUND",
    )
    assignments = _load_model(
        repo_root / _ASSIGNMENT_PATH,
        ReviewAssignmentManifest,
        "BLINDED_REVIEW_ASSIGNMENTS_NOT_FOUND",
    )
    rubric = _load_model(
        repo_root / _RUBRIC_PATH,
        BlindedQualityRubric,
        "BLINDED_QUALITY_RUBRIC_NOT_FOUND",
    )
    episodes = _load_model(
        repo_root / _EPISODE_SET_PATH,
        FunctionalEpisodeSet,
        "FUNCTIONAL_EPISODE_SET_NOT_FOUND",
    )
    blinded_manifest = _load_model(
        repo_root / _BLINDED_MANIFEST_PATH,
        Gate6BlindedQualityManifest,
        "BLINDED_QUALITY_MANIFEST_NOT_FOUND",
    )
    if not blinded_manifest.blinded_workflow_passed:
        raise ProtectedReviewAssetError(
            error_code="BLINDED_WORKFLOW_NOT_PASSED",
            safe_message="Protected execution requires a passed blinded-workflow manifest.",
        )
    if blinded_manifest.measured_execution_permitted:
        raise ProtectedReviewAssetError(
            error_code="BLINDED_MANIFEST_SCOPE_INVALID",
            safe_message="Blinded preparation must not permit measured execution.",
        )

    episode_splits = {episode.episode_id: episode.evaluation_split for episode in episodes.episodes}
    try:
        report = evaluate_protected_review_execution(
            assignments,
            rubric,
            episode_splits,
            submissions,
        )
    except ProtectedReviewExecutionError as exc:
        raise ProtectedReviewAssetError(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
        ) from exc

    report_bytes = _model_json_bytes(report)
    manifest = Gate6ProtectedReviewExecutionManifest(
        submission_path=_SUBMISSION_PATH.as_posix(),
        submission_sha256=_require_hash_bound_asset(
            repo_root,
            _SUBMISSION_PATH,
            "PROTECTED_REVIEW_SUBMISSIONS_NOT_FOUND",
        ),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=_sha256_bytes(report_bytes),
        assignment_path=_ASSIGNMENT_PATH.as_posix(),
        assignment_sha256=_require_hash_bound_asset(
            repo_root,
            _ASSIGNMENT_PATH,
            "BLINDED_REVIEW_ASSIGNMENTS_NOT_FOUND",
        ),
        rubric_path=_RUBRIC_PATH.as_posix(),
        rubric_sha256=_require_hash_bound_asset(
            repo_root,
            _RUBRIC_PATH,
            "BLINDED_QUALITY_RUBRIC_NOT_FOUND",
        ),
        episode_manifest_path=_EPISODE_MANIFEST_PATH.as_posix(),
        episode_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _EPISODE_MANIFEST_PATH,
            "EPISODE_MANIFEST_NOT_FOUND",
        ),
        blinded_quality_manifest_path=_BLINDED_MANIFEST_PATH.as_posix(),
        blinded_quality_manifest_sha256=_require_hash_bound_asset(
            repo_root,
            _BLINDED_MANIFEST_PATH,
            "BLINDED_QUALITY_MANIFEST_NOT_FOUND",
        ),
        assignment_count=report.assignment_count,
        review_count=report.review_count,
        adjudication_count=report.adjudication_count,
        held_out_episode_count=report.held_out.held_out_episode_count,
        execution_controls_passed=report.execution_controls_passed,
    )
    summary = Gate6ProtectedReviewExecutionSummary(
        execution_id=report.execution_id,
        assignment_count=report.assignment_count,
        review_count=report.review_count,
        adjudication_count=report.adjudication_count,
        double_review_count=report.agreement.double_review_count,
        verdict_agreement_rate=report.agreement.verdict_agreement_rate,
        exact_criterion_agreement_rate=report.agreement.exact_criterion_agreement_rate,
        held_out_episode_count=report.held_out.held_out_episode_count,
        held_out_pass_count=report.held_out.pass_count,
        held_out_pass_rate=report.held_out.pass_rate,
        execution_controls_passed=report.execution_controls_passed,
        synthetic_fixture_execution=report.synthetic_fixture_execution,
        human_review_completed=report.human_review_completed,
        measured_execution_permitted=report.measured_execution_permitted,
    )
    return report, manifest, summary


def write_assets(repo_root: Path) -> Gate6ProtectedReviewExecutionSummary:
    """Write deterministic protected review report and manifest."""

    report, manifest, summary = build_assets(repo_root)
    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _REPORT_PATH).write_bytes(_model_json_bytes(report))
    (repo_root / _MANIFEST_PATH).write_bytes(_model_json_bytes(manifest))
    return summary


def verify_assets(repo_root: Path) -> Gate6ProtectedReviewExecutionSummary:
    """Rebuild and compare persisted protected review execution evidence."""

    expected_report, expected_manifest, summary = build_assets(repo_root)
    persisted_report = _load_model(
        repo_root / _REPORT_PATH,
        Gate6ProtectedReviewExecutionReport,
        "PROTECTED_REVIEW_REPORT_NOT_FOUND",
    )
    persisted_manifest = _load_model(
        repo_root / _MANIFEST_PATH,
        Gate6ProtectedReviewExecutionManifest,
        "PROTECTED_REVIEW_MANIFEST_NOT_FOUND",
    )
    if persisted_report != expected_report:
        raise ProtectedReviewAssetError(
            error_code="PROTECTED_REVIEW_REPORT_MISMATCH",
            safe_message="Persisted protected review report does not match deterministic output.",
            path=str(repo_root / _REPORT_PATH),
        )
    if persisted_manifest != expected_manifest:
        raise ProtectedReviewAssetError(
            error_code="PROTECTED_REVIEW_MANIFEST_MISMATCH",
            safe_message="Persisted protected review manifest does not match deterministic output.",
            path=str(repo_root / _MANIFEST_PATH),
        )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for protected review execution evidence."""

    args = _parse_args(argv)
    try:
        summary = (
            write_assets(args.repo_root)
            if args.command == "build"
            else verify_assets(args.repo_root)
        )
    except ProtectedReviewAssetError as exc:
        envelope = ProtectedReviewAssetErrorEnvelope(
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
