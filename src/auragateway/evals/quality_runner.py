"""Build and verify deterministic Gate 6 quality-scoring evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.corpus import CorpusInventory
from auragateway.contracts.episodes import EpisodeAssetManifest, FunctionalEpisodeSet
from auragateway.contracts.quality import (
    Gate6DeterministicQualityManifest,
    Gate6DeterministicQualityReport,
    Gate6DeterministicQualitySummary,
    QualityFixtureResult,
    QualityFixtureSet,
)
from auragateway.evals.quality import score_deterministic_quality

_FIXTURE_PATH = Path("data/evals/quality/deterministic-v1/fixtures.json")
_REPORT_PATH = Path("data/evals/quality/deterministic-v1/report.json")
_MANIFEST_PATH = Path("data/evals/quality/deterministic-v1/manifest.json")
_EPISODE_PATH = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
_EPISODE_MANIFEST_PATH = Path("data/evals/episodes/manifest.json")
_CORPUS_INVENTORY_PATH = Path("data/corpus/source_inventory.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class QualityEvidenceError(Exception):
    """Expected quality-evidence failure with safe diagnostics."""

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


class QualityEvidenceErrorEnvelope(BaseModel):
    """Safe CLI failure envelope without raw candidate output content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


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
        raise QualityEvidenceError(
            not_found_code,
            "Required deterministic quality artifact was not found.",
            str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QualityEvidenceError(
            "QUALITY_ARTIFACT_INVALID_JSON",
            "Deterministic quality artifact is not valid JSON.",
            str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT], code: str) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path, f"{code}_NOT_FOUND"))
    except ValidationError as exc:
        raise QualityEvidenceError(
            f"{code}_VALIDATION_FAILED",
            "Deterministic quality artifact failed typed validation.",
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


def _build_report(
    fixtures: QualityFixtureSet,
    episodes: FunctionalEpisodeSet,
    inventory: CorpusInventory,
    episode_manifest: EpisodeAssetManifest,
) -> Gate6DeterministicQualityReport:
    episodes_by_id = {episode.episode_id: episode for episode in episodes.episodes}
    results: list[QualityFixtureResult] = []

    for case in fixtures.cases:
        try:
            episode = episodes_by_id[case.candidate.episode_id]
        except KeyError as exc:
            raise QualityEvidenceError(
                "QUALITY_EPISODE_REFERENCE_UNKNOWN",
                "Quality fixture references an unknown frozen diagnostic episode.",
                details=(case.case_id, case.candidate.episode_id),
            ) from exc

        scorecard = score_deterministic_quality(
            episode=episode,
            inventory=inventory,
            candidate=case.candidate,
            claim_support=case.claim_support,
            expected_retrieval_configuration_fingerprint=(
                episode_manifest.retrieval_configuration_fingerprint
            ),
        )
        expectation_matched = (
            scorecard.deterministic_quality_passed is case.expected_pass
            and scorecard.failure_labels == case.expected_failure_labels
        )
        results.append(
            QualityFixtureResult(
                case_id=case.case_id,
                scorecard=scorecard,
                expectation_matched=expectation_matched,
                negative_control=case.negative_control,
            )
        )

    all_expectations_matched = all(result.expectation_matched for result in results)
    return Gate6DeterministicQualityReport(
        fixture_set_id=fixtures.fixture_set_id,
        results=tuple(results),
        fixture_count=len(results),
        negative_control_count=sum(result.negative_control for result in results),
        all_expectations_matched=all_expectations_matched,
        deterministic_scorers_passed=all_expectations_matched,
    )


def _summary(
    fixture_path: Path,
    report_path: Path,
    report: Gate6DeterministicQualityReport,
) -> Gate6DeterministicQualitySummary:
    return Gate6DeterministicQualitySummary(
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        deterministic_scorers_passed=report.deterministic_scorers_passed,
        measured_execution_permitted=report.measured_execution_permitted,
        fixture_sha256=_sha256_path(fixture_path),
        report_sha256=_sha256_path(report_path),
    )


def build_quality_evidence(repo_root: Path) -> Gate6DeterministicQualitySummary:
    """Build deterministic quality report and hash-bound manifest."""

    fixture_path = repo_root / _FIXTURE_PATH
    report_path = repo_root / _REPORT_PATH
    manifest_path = repo_root / _MANIFEST_PATH
    episode_manifest_path = repo_root / _EPISODE_MANIFEST_PATH

    fixtures = _load_model(fixture_path, QualityFixtureSet, "QUALITY_FIXTURE_SET")
    episodes = _load_model(
        repo_root / _EPISODE_PATH,
        FunctionalEpisodeSet,
        "FUNCTIONAL_EPISODE_SET",
    )
    inventory = _load_model(
        repo_root / _CORPUS_INVENTORY_PATH,
        CorpusInventory,
        "CORPUS_INVENTORY",
    )
    episode_manifest = _load_model(
        episode_manifest_path,
        EpisodeAssetManifest,
        "EPISODE_MANIFEST",
    )

    report = _build_report(fixtures, episodes, inventory, episode_manifest)
    if not report.deterministic_scorers_passed:
        failed_cases = tuple(
            result.case_id for result in report.results if not result.expectation_matched
        )
        raise QualityEvidenceError(
            "GATE_6_DETERMINISTIC_QUALITY_FAILED",
            "Deterministic quality fixtures did not match expected outcomes.",
            details=failed_cases,
        )

    _write_model(report_path, report)
    manifest = Gate6DeterministicQualityManifest(
        fixture_path=_FIXTURE_PATH.as_posix(),
        fixture_sha256=_sha256_path(fixture_path),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=_sha256_path(report_path),
        episode_manifest_path=_EPISODE_MANIFEST_PATH.as_posix(),
        episode_manifest_sha256=_sha256_path(episode_manifest_path),
        retrieval_configuration_fingerprint=(episode_manifest.retrieval_configuration_fingerprint),
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        deterministic_scorers_passed=report.deterministic_scorers_passed,
    )
    _write_model(manifest_path, manifest)
    return _summary(fixture_path, report_path, report)


def verify_quality_evidence(repo_root: Path) -> Gate6DeterministicQualitySummary:
    """Verify frozen hashes and deterministic report reproduction."""

    fixture_path = repo_root / _FIXTURE_PATH
    report_path = repo_root / _REPORT_PATH
    manifest_path = repo_root / _MANIFEST_PATH
    episode_manifest_path = repo_root / _EPISODE_MANIFEST_PATH

    manifest = _load_model(
        manifest_path,
        Gate6DeterministicQualityManifest,
        "QUALITY_MANIFEST",
    )
    if _sha256_path(fixture_path) != manifest.fixture_sha256:
        raise QualityEvidenceError(
            "QUALITY_FIXTURE_HASH_MISMATCH",
            "Quality fixture hash does not match the frozen manifest.",
            str(fixture_path),
        )
    if _sha256_path(report_path) != manifest.report_sha256:
        raise QualityEvidenceError(
            "QUALITY_REPORT_HASH_MISMATCH",
            "Quality report hash does not match the frozen manifest.",
            str(report_path),
        )
    if _sha256_path(episode_manifest_path) != manifest.episode_manifest_sha256:
        raise QualityEvidenceError(
            "QUALITY_EPISODE_MANIFEST_HASH_MISMATCH",
            "Episode manifest hash does not match the quality manifest.",
            str(episode_manifest_path),
        )

    fixtures = _load_model(fixture_path, QualityFixtureSet, "QUALITY_FIXTURE_SET")
    episodes = _load_model(
        repo_root / _EPISODE_PATH,
        FunctionalEpisodeSet,
        "FUNCTIONAL_EPISODE_SET",
    )
    inventory = _load_model(
        repo_root / _CORPUS_INVENTORY_PATH,
        CorpusInventory,
        "CORPUS_INVENTORY",
    )
    episode_manifest = _load_model(
        episode_manifest_path,
        EpisodeAssetManifest,
        "EPISODE_MANIFEST",
    )
    frozen_report = _load_model(
        report_path,
        Gate6DeterministicQualityReport,
        "QUALITY_REPORT",
    )
    rebuilt_report = _build_report(fixtures, episodes, inventory, episode_manifest)
    if rebuilt_report != frozen_report:
        raise QualityEvidenceError(
            "QUALITY_REPORT_REPRODUCTION_MISMATCH",
            "Rebuilt quality report does not match the frozen report.",
            str(report_path),
        )
    if (
        manifest.fixture_count != frozen_report.fixture_count
        or manifest.negative_control_count != frozen_report.negative_control_count
        or manifest.deterministic_scorers_passed != frozen_report.deterministic_scorers_passed
    ):
        raise QualityEvidenceError(
            "QUALITY_MANIFEST_REPORT_MISMATCH",
            "Quality manifest does not match the frozen report summary.",
            str(manifest_path),
        )
    return _summary(fixture_path, report_path, frozen_report)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run deterministic quality build or verification with safe JSON output."""

    args = _parse_args(argv)
    try:
        if args.command == "build":
            summary = build_quality_evidence(args.repo_root)
        else:
            summary = verify_quality_evidence(args.repo_root)
    except QualityEvidenceError as exc:
        envelope = QualityEvidenceErrorEnvelope(
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
