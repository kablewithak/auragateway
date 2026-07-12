"""Build and verify the non-live AuraGateway development controlled smoke."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.benchmark.smoke import (
    ControlledSmokeError,
    build_controlled_smoke,
    model_json_bytes,
    sha256_bytes,
    validate_upstream,
)
from auragateway.contracts.benchmark_smoke import (
    ControlledSmokeAuthorization,
    ControlledSmokeReport,
    ControlledSmokeSummary,
    Gate11SmokeManifest,
    ScriptedSmokeFixtureSet,
    SmokeRunRecordSet,
)

_ASSET_ROOT = Path("data/evals/benchmark/smoke-v1")
_AUTHORIZATION_PATH = _ASSET_ROOT / "authorization.json"
_FIXTURE_PATH = _ASSET_ROOT / "scripted_attempts.json"
_RUN_RECORDS_PATH = _ASSET_ROOT / "run_records.json"
_REPORT_PATH = _ASSET_ROOT / "smoke_report.json"
_MANIFEST_PATH = _ASSET_ROOT / "manifest.json"
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class ControlledSmokeErrorEnvelope(BaseModel):
    """Metadata-safe CLI failure envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_REQUIRED_ASSET_MISSING",
            "A required controlled-smoke asset was not found.",
            str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_INVALID_JSON",
            "A controlled-smoke asset is not valid JSON.",
            str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_ASSET_VALIDATION_FAILED",
            "A controlled-smoke asset failed typed validation.",
            str(path),
            details,
        ) from exc


def _load_inputs(
    repo_root: Path,
    authorization_id: str,
) -> tuple[ControlledSmokeAuthorization, ScriptedSmokeFixtureSet]:
    authorization = _load_model(
        repo_root / _AUTHORIZATION_PATH,
        ControlledSmokeAuthorization,
    )
    if authorization.authorization_id != authorization_id:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_AUTHORIZATION_ID_MISMATCH",
            "The supplied authorization ID does not match the frozen smoke authorization.",
        )
    fixtures = _load_model(repo_root / _FIXTURE_PATH, ScriptedSmokeFixtureSet)
    return authorization, fixtures


def _manifest(
    repo_root: Path,
    authorization: ControlledSmokeAuthorization,
    records: SmokeRunRecordSet,
    report: ControlledSmokeReport,
) -> Gate11SmokeManifest:
    authorization_bytes = (repo_root / _AUTHORIZATION_PATH).read_bytes()
    fixture_bytes = (repo_root / _FIXTURE_PATH).read_bytes()
    records_bytes = model_json_bytes(records)
    report_bytes = model_json_bytes(report)
    return Gate11SmokeManifest(
        authorization_path=_AUTHORIZATION_PATH.as_posix(),
        authorization_sha256=sha256_bytes(authorization_bytes),
        fixture_path=_FIXTURE_PATH.as_posix(),
        fixture_sha256=sha256_bytes(fixture_bytes),
        run_records_path=_RUN_RECORDS_PATH.as_posix(),
        run_records_sha256=sha256_bytes(records_bytes),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=sha256_bytes(report_bytes),
        gate10_manifest_sha256=authorization.gate10_manifest_sha256,
        execution_manifest_sha256=authorization.execution_manifest_sha256,
        planned_run_ledger_sha256=authorization.planned_run_ledger_sha256,
        functional_episode_set_sha256=authorization.functional_episode_set_sha256,
        smoke_passed=report.smoke_passed,
    )


def _summary(
    command: str,
    authorization: ControlledSmokeAuthorization,
    records: SmokeRunRecordSet,
    report: ControlledSmokeReport,
    reused: int,
) -> ControlledSmokeSummary:
    return ControlledSmokeSummary.model_validate(
        {
            "command": command,
            "authorization_id": authorization.authorization_id,
            "smoke_passed": report.smoke_passed,
            "terminal_record_count": len(records.terminal_records),
            "attempt_record_count": len(records.attempt_records),
            "reused_terminal_record_count": reused,
            "live_provider_called": False,
            "held_out_executed": False,
            "full_benchmark_executed": False,
            "benchmark_claims_permitted": False,
            "measured_execution_permitted": False,
        }
    )


def build_assets(
    repo_root: Path,
    authorization_id: str,
    existing: SmokeRunRecordSet | None = None,
) -> tuple[
    ControlledSmokeAuthorization,
    SmokeRunRecordSet,
    ControlledSmokeReport,
    Gate11SmokeManifest,
    int,
]:
    """Validate upstream bytes and build deterministic non-live smoke evidence."""

    authorization, fixtures = _load_inputs(repo_root, authorization_id)
    plan, episodes = validate_upstream(repo_root, authorization)
    records, report, reused = build_controlled_smoke(
        authorization,
        fixtures,
        plan,
        episodes,
        existing,
    )
    manifest = _manifest(repo_root, authorization, records, report)
    return authorization, records, report, manifest, reused


def validate_assets(repo_root: Path, authorization_id: str) -> ControlledSmokeSummary:
    """Validate the controlled-smoke boundary without writing evidence."""

    authorization, records, report, _, reused = build_assets(repo_root, authorization_id)
    if not report.smoke_passed:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_VALIDATION_FAILED",
            "Controlled-smoke safety expectations did not pass.",
        )
    return _summary("validate", authorization, records, report, reused)


def write_assets(repo_root: Path, authorization_id: str) -> ControlledSmokeSummary:
    """Write deterministic development-only controlled-smoke evidence."""

    authorization, records, report, manifest, reused = build_assets(
        repo_root,
        authorization_id,
    )
    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _RUN_RECORDS_PATH).write_bytes(model_json_bytes(records))
    (repo_root / _REPORT_PATH).write_bytes(model_json_bytes(report))
    (repo_root / _MANIFEST_PATH).write_bytes(model_json_bytes(manifest))
    return _summary("run", authorization, records, report, reused)


def resume_assets(repo_root: Path, authorization_id: str) -> ControlledSmokeSummary:
    """Resume only unterminated runs and preserve all prior terminal evidence."""

    existing = _load_model(repo_root / _RUN_RECORDS_PATH, SmokeRunRecordSet)
    authorization, records, report, manifest, reused = build_assets(
        repo_root,
        authorization_id,
        existing,
    )
    (repo_root / _RUN_RECORDS_PATH).write_bytes(model_json_bytes(records))
    (repo_root / _REPORT_PATH).write_bytes(model_json_bytes(report))
    (repo_root / _MANIFEST_PATH).write_bytes(model_json_bytes(manifest))
    return _summary("resume", authorization, records, report, reused)


def verify_assets(repo_root: Path, authorization_id: str) -> ControlledSmokeSummary:
    """Rebuild and compare every persisted Gate 11 controlled-smoke artifact."""

    authorization, expected_records, expected_report, expected_manifest, reused = build_assets(
        repo_root,
        authorization_id,
    )
    persisted_records = _load_model(repo_root / _RUN_RECORDS_PATH, SmokeRunRecordSet)
    persisted_report = _load_model(repo_root / _REPORT_PATH, ControlledSmokeReport)
    persisted_manifest = _load_model(repo_root / _MANIFEST_PATH, Gate11SmokeManifest)
    comparisons = (
        (persisted_records, expected_records, _RUN_RECORDS_PATH),
        (persisted_report, expected_report, _REPORT_PATH),
        (persisted_manifest, expected_manifest, _MANIFEST_PATH),
    )
    for observed, expected, path in comparisons:
        if observed != expected:
            raise ControlledSmokeError(
                "CONTROLLED_SMOKE_EVIDENCE_MISMATCH",
                "Persisted controlled-smoke evidence is not reproducible.",
                str(repo_root / path),
            )
    if not expected_report.smoke_passed:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_NOT_PASSED",
            "Controlled-smoke evidence does not pass its frozen expectations.",
        )
    return _summary("verify", authorization, expected_records, expected_report, reused)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "run", "resume", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--authorization-id", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run a scripted smoke action; no command calls a live provider."""

    args = _parse_args(argv)
    try:
        if args.command == "validate":
            summary = validate_assets(args.repo_root, args.authorization_id)
        elif args.command == "run":
            summary = write_assets(args.repo_root, args.authorization_id)
        elif args.command == "resume":
            summary = resume_assets(args.repo_root, args.authorization_id)
        else:
            summary = verify_assets(args.repo_root, args.authorization_id)
    except ControlledSmokeError as exc:
        envelope = ControlledSmokeErrorEnvelope(
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
