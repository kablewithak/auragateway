"""Validate, run, resume, and verify bounded live development benchmark batches."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.benchmark.execution import (
    LiveExecutionError,
    execute_live_development,
    load_journal,
    validate_live_upstream,
)
from auragateway.benchmark.live_output_adapter import (
    ContractAlignedPacedAdapter,
    LiveBatchRuntimePolicy,
)
from auragateway.benchmark.smoke import model_json_bytes, sha256_bytes, sha256_file
from auragateway.contracts.benchmark_execution import (
    LiveDevelopmentAuthorization,
    LiveDevelopmentManifest,
    LiveDevelopmentReport,
    LiveDevelopmentSummary,
    LiveJournalAttemptEvent,
    LiveJournalTerminalEvent,
    LiveRunRecordSet,
)
from auragateway.providers.base import LiveProviderAdapter
from auragateway.providers.groq import GroqProviderAdapter

_ASSET_ROOT = Path("data/evals/benchmark/live-development-v1")
_AUTHORIZATION_PATH = _ASSET_ROOT / "authorization.json"
_JOURNAL_PATH = _ASSET_ROOT / "journal.jsonl"
_RUN_RECORDS_PATH = _ASSET_ROOT / "run_records.json"
_REPORT_PATH = _ASSET_ROOT / "report.json"
_MANIFEST_PATH = _ASSET_ROOT / "manifest.json"
_PROTECTED_OUTPUT_PATH = Path(".local/benchmark/live-development-v1/protected_outputs.jsonl")
_V2_AUTHORIZATION_ID = "live-development-batch-02-auth-v1"
_BATCH_ASSET_ROOTS = {
    "live-development-batch-01-auth-v1": _ASSET_ROOT,
    _V2_AUTHORIZATION_ID: Path("data/evals/benchmark/live-development-v2"),
}
_ModelT = TypeVar("_ModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class _BatchPaths:
    asset_root: Path
    authorization_path: Path
    journal_path: Path
    run_records_path: Path
    report_path: Path
    manifest_path: Path
    protected_output_path: Path
    raw_provider_output_path: Path
    runtime_policy_path: Path


class LiveExecutionErrorEnvelope(BaseModel):
    """Metadata-safe CLI failure envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _paths_for_authorization(authorization_id: str) -> _BatchPaths:
    asset_root = _BATCH_ASSET_ROOTS.get(authorization_id)
    if asset_root is None:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_AUTHORIZATION_UNKNOWN",
            "The supplied live-development authorization ID is not registered.",
            details=(authorization_id,),
        )
    local_root = Path(".local/benchmark") / asset_root.name
    return _BatchPaths(
        asset_root=asset_root,
        authorization_path=asset_root / "authorization.json",
        journal_path=asset_root / "journal.jsonl",
        run_records_path=asset_root / "run_records.json",
        report_path=asset_root / "report.json",
        manifest_path=asset_root / "manifest.json",
        protected_output_path=local_root / "protected_outputs.jsonl",
        raw_provider_output_path=local_root / "provider_raw_outputs.jsonl",
        runtime_policy_path=asset_root / "runtime_policy.json",
    )


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_REQUIRED_ASSET_MISSING",
            "A required live-development asset was not found.",
            str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_INVALID_JSON",
            "A live-development asset is not valid JSON.",
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
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_ASSET_VALIDATION_FAILED",
            "A live-development asset failed typed validation.",
            str(path),
            details,
        ) from exc


def _load_authorization(
    repo_root: Path,
    authorization_id: str,
    paths: _BatchPaths | None = None,
) -> LiveDevelopmentAuthorization:
    resolved_paths = paths or _paths_for_authorization(authorization_id)
    authorization = _load_model(
        repo_root / resolved_paths.authorization_path,
        LiveDevelopmentAuthorization,
    )
    if authorization.authorization_id != authorization_id:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_AUTHORIZATION_ID_MISMATCH",
            "The supplied authorization ID does not match the frozen live authorization.",
        )
    return authorization


def _write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(model_json_bytes(model))


def _manifest(
    repo_root: Path,
    authorization: LiveDevelopmentAuthorization,
    records: LiveRunRecordSet,
    report: LiveDevelopmentReport,
    paths: _BatchPaths,
) -> LiveDevelopmentManifest:
    return LiveDevelopmentManifest(
        authorization_path=paths.authorization_path.as_posix(),
        authorization_sha256=sha256_file(repo_root / paths.authorization_path),
        journal_path=paths.journal_path.as_posix(),
        journal_sha256=sha256_file(repo_root / paths.journal_path),
        run_records_path=paths.run_records_path.as_posix(),
        run_records_sha256=sha256_bytes(model_json_bytes(records)),
        report_path=paths.report_path.as_posix(),
        report_sha256=sha256_bytes(model_json_bytes(report)),
        execution_manifest_sha256=authorization.execution_manifest_sha256,
        planned_run_ledger_sha256=authorization.planned_run_ledger_sha256,
        functional_episode_set_sha256=authorization.functional_episode_set_sha256,
        live_provider_called=records.live_provider_called,
    )


def _summary(
    command: str,
    authorization: LiveDevelopmentAuthorization,
    records: LiveRunRecordSet | None,
    report: LiveDevelopmentReport | None,
    reused: int,
) -> LiveDevelopmentSummary:
    return LiveDevelopmentSummary.model_validate(
        {
            "command": command,
            "authorization_id": authorization.authorization_id,
            "terminal_record_count": (len(records.terminal_records) if records is not None else 0),
            "attempt_record_count": (len(records.attempt_records) if records is not None else 0),
            "reused_terminal_record_count": reused,
            "live_provider_called": (
                records.live_provider_called if records is not None else False
            ),
            "held_out_executed": False,
            "full_benchmark_executed": False,
            "benchmark_claims_permitted": False,
            "measured_execution_permitted": False,
            "comparison_eligible": False,
            "batch_completed": report.batch_completed if report is not None else False,
        }
    )


def _adapter_for_authorization(
    repo_root: Path,
    authorization_id: str,
    paths: _BatchPaths,
) -> LiveProviderAdapter:
    adapter: LiveProviderAdapter = GroqProviderAdapter()
    if authorization_id != _V2_AUTHORIZATION_ID:
        return adapter
    policy = _load_model(
        repo_root / paths.runtime_policy_path,
        LiveBatchRuntimePolicy,
    )
    return ContractAlignedPacedAdapter(
        adapter,
        policy,
        repo_root / paths.raw_provider_output_path,
    )


def validate_assets(repo_root: Path, authorization_id: str) -> LiveDevelopmentSummary:
    """Validate authorization and frozen run scope without reading live credentials."""

    paths = _paths_for_authorization(authorization_id)
    authorization = _load_authorization(repo_root, authorization_id, paths)
    validate_live_upstream(repo_root, authorization)
    return _summary("validate", authorization, None, None, 0)


def _execute(
    repo_root: Path,
    authorization_id: str,
    *,
    resume: bool,
) -> LiveDevelopmentSummary:
    paths = _paths_for_authorization(authorization_id)
    authorization = _load_authorization(repo_root, authorization_id, paths)
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key is None or not api_key.strip():
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_GROQ_API_KEY_MISSING",
            "GROQ_API_KEY must be loaded deliberately before live execution.",
        )
    records, report, reused = execute_live_development(
        repo_root=repo_root,
        authorization=authorization,
        adapter=_adapter_for_authorization(repo_root, authorization_id, paths),
        journal_path=repo_root / paths.journal_path,
        protected_output_path=repo_root / paths.protected_output_path,
        resume=resume,
    )
    _write_model(repo_root / paths.run_records_path, records)
    _write_model(repo_root / paths.report_path, report)
    manifest = _manifest(repo_root, authorization, records, report, paths)
    _write_model(repo_root / paths.manifest_path, manifest)
    return _summary("resume" if resume else "run", authorization, records, report, reused)


def write_assets(repo_root: Path, authorization_id: str) -> LiveDevelopmentSummary:
    """Run a fresh bounded live development batch."""

    paths = _paths_for_authorization(authorization_id)
    journal_path = repo_root / paths.journal_path
    if journal_path.exists() and journal_path.stat().st_size:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_JOURNAL_ALREADY_EXISTS",
            "Existing live evidence must be continued with the resume command.",
            str(journal_path),
        )
    return _execute(repo_root, authorization_id, resume=False)


def resume_assets(repo_root: Path, authorization_id: str) -> LiveDevelopmentSummary:
    """Preserve terminal records and fail closed on unterminated provider state."""

    return _execute(repo_root, authorization_id, resume=True)


def verify_assets(repo_root: Path, authorization_id: str) -> LiveDevelopmentSummary:
    """Verify persisted public evidence without calling a provider."""

    paths = _paths_for_authorization(authorization_id)
    authorization = _load_authorization(repo_root, authorization_id, paths)
    validate_live_upstream(repo_root, authorization)
    records = _load_model(repo_root / paths.run_records_path, LiveRunRecordSet)
    report = _load_model(repo_root / paths.report_path, LiveDevelopmentReport)
    manifest = _load_model(repo_root / paths.manifest_path, LiveDevelopmentManifest)
    events = load_journal(repo_root / paths.journal_path)
    terminal_count = sum(isinstance(item, LiveJournalTerminalEvent) for item in events)
    attempt_count = sum(isinstance(item, LiveJournalAttemptEvent) for item in events)
    if terminal_count != len(records.terminal_records) or attempt_count != len(
        records.attempt_records
    ):
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_JOURNAL_RECONCILIATION_FAILED",
            "Persisted journal and reconciled run records do not agree.",
        )
    expected_manifest = _manifest(repo_root, authorization, records, report, paths)
    if manifest != expected_manifest:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_MANIFEST_MISMATCH",
            "Persisted live-development manifest does not reproduce.",
            str(repo_root / paths.manifest_path),
        )
    if report.authorization_id != authorization.authorization_id:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_REPORT_AUTHORIZATION_MISMATCH",
            "Persisted report is bound to a different authorization.",
        )
    if len(records.terminal_records) != authorization.maximum_run_count:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_RUN_ACCOUNTABILITY_INCOMPLETE",
            "Every authorized run must retain one terminal record.",
        )
    return _summary("verify", authorization, records, report, 0)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "run", "resume", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--authorization-id", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run one bounded live-development action with metadata-safe CLI output."""

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
    except LiveExecutionError as exc:
        envelope = LiveExecutionErrorEnvelope(
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
