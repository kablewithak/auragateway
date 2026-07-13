"""Validate, run, resume, verify, and receipt bounded live development batches."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

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
_V3_AUTHORIZATION_ID = "live-development-batch-03-auth-v1"
_V4_AUTHORIZATION_ID = "live-development-batch-04-auth-v1"
_V5_AUTHORIZATION_ID = "live-development-batch-05-auth-v1"
_PACED_AUTHORIZATION_IDS = frozenset(
    {
        _V2_AUTHORIZATION_ID,
        _V3_AUTHORIZATION_ID,
        _V4_AUTHORIZATION_ID,
        _V5_AUTHORIZATION_ID,
    }
)
_DIAGNOSTIC_AUTHORIZATION_IDS = frozenset({_V4_AUTHORIZATION_ID, _V5_AUTHORIZATION_ID})
_BATCH_ASSET_ROOTS = {
    "live-development-batch-01-auth-v1": _ASSET_ROOT,
    _V2_AUTHORIZATION_ID: Path("data/evals/benchmark/live-development-v2"),
    _V3_AUTHORIZATION_ID: Path("data/evals/benchmark/live-development-v3"),
    _V4_AUTHORIZATION_ID: Path("data/evals/benchmark/live-development-v4"),
    _V5_AUTHORIZATION_ID: Path("data/evals/benchmark/live-development-v5"),
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
    provider_failure_diagnostic_path: Path
    runtime_policy_path: Path


class LiveExecutionErrorEnvelope(BaseModel):
    """Metadata-safe CLI failure envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class LiveReceiptArtifact(BaseModel):
    """One public artifact retained in an accepted live-run receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LiveDevelopmentReceipt(BaseModel):
    """Machine-readable proof that a live batch exists, verifies, and passes acceptance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    command: Literal["receipt"] = "receipt"
    authorization_id: str
    execution_completed: Literal[True] = True
    verification_passed: Literal[True] = True
    acceptance_passed: Literal[True] = True
    required_public_artifact_count: Literal[5] = 5
    public_artifacts: tuple[LiveReceiptArtifact, ...] = Field(min_length=5, max_length=5)
    protected_artifact_paths: tuple[str, ...] = Field(min_length=2, max_length=2)
    terminal_record_count: int = Field(ge=0)
    attempt_record_count: int = Field(ge=0)
    completed_run_count: int = Field(ge=0)
    completed_validation_failure_count: int = Field(ge=0)
    provider_error_count: int = Field(ge=0)
    safety_abort_count: int = Field(ge=0)
    budget_exhausted_count: int = Field(ge=0)
    structured_output_failure_count: int = Field(ge=0)
    citation_scope_failure_count: int = Field(ge=0)
    attempt_budget_respected: Literal[True] = True
    cost_budget_respected: Literal[True] = True
    protected_outputs_retained_locally: Literal[True] = True
    live_provider_called: Literal[True] = True
    batch_completed: Literal[True] = True
    held_out_executed: Literal[False] = False
    full_benchmark_executed: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False


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
        provider_failure_diagnostic_path=(local_root / "provider_failure_diagnostics.jsonl"),
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
            "terminal_record_count": len(records.terminal_records) if records is not None else 0,
            "attempt_record_count": len(records.attempt_records) if records is not None else 0,
            "reused_terminal_record_count": reused,
            "live_provider_called": records.live_provider_called if records is not None else False,
            "held_out_executed": False,
            "full_benchmark_executed": False,
            "benchmark_claims_permitted": False,
            "measured_execution_permitted": False,
            "comparison_eligible": False,
            "batch_completed": report.batch_completed if report is not None else False,
        }
    )


def _load_runtime_policy(
    repo_root: Path,
    authorization_id: str,
    paths: _BatchPaths,
) -> LiveBatchRuntimePolicy:
    policy = _load_model(
        repo_root / paths.runtime_policy_path,
        LiveBatchRuntimePolicy,
    )
    if policy.authorization_id != authorization_id:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_RUNTIME_POLICY_AUTHORIZATION_MISMATCH",
            "Runtime policy is bound to a different live authorization.",
            str(repo_root / paths.runtime_policy_path),
        )
    return policy


def _validate_provider_failure_diagnostic_sink(
    repo_root: Path,
    paths: _BatchPaths,
    *,
    require_absent: bool,
) -> None:
    """Prove the protected diagnostic parent is writable without retaining probe data."""

    diagnostic_path = repo_root / paths.provider_failure_diagnostic_path
    if diagnostic_path.exists():
        if not diagnostic_path.is_file():
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_PROVIDER_DIAGNOSTIC_PATH_INVALID",
                "The provider failure diagnostic path must be a regular file when present.",
                str(diagnostic_path),
            )
        if require_absent:
            raise LiveExecutionError(
                "LIVE_DEVELOPMENT_PROVIDER_DIAGNOSTIC_ALREADY_EXISTS",
                "Fresh live execution requires an empty provider failure diagnostic boundary.",
                str(diagnostic_path),
            )

    probe_path = diagnostic_path.with_name(f".{diagnostic_path.name}.preflight")
    if probe_path.exists():
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PROVIDER_DIAGNOSTIC_PROBE_EXISTS",
            "A stale provider diagnostic preflight probe must be investigated before execution.",
            str(probe_path),
        )

    try:
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        with probe_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write('{"schema_version":"1.0.0","probe":"provider-failure-diagnostic-sink"}\n')
            handle.flush()
            os.fsync(handle.fileno())
        probe_path.unlink()
    except OSError as exc:
        with suppress(OSError):
            probe_path.unlink(missing_ok=True)
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_PROVIDER_DIAGNOSTIC_SINK_UNAVAILABLE",
            "The protected provider failure diagnostic sink is not safely writable.",
            str(diagnostic_path),
        ) from exc


def _adapter_for_authorization(
    repo_root: Path,
    authorization_id: str,
    paths: _BatchPaths,
) -> LiveProviderAdapter:
    diagnostic_path = (
        repo_root / paths.provider_failure_diagnostic_path
        if authorization_id in _DIAGNOSTIC_AUTHORIZATION_IDS
        else None
    )
    adapter: LiveProviderAdapter = GroqProviderAdapter(failure_diagnostic_path=diagnostic_path)
    if authorization_id not in _PACED_AUTHORIZATION_IDS:
        return adapter
    policy = _load_runtime_policy(repo_root, authorization_id, paths)
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
    if authorization_id in _PACED_AUTHORIZATION_IDS:
        _load_runtime_policy(repo_root, authorization_id, paths)
    if authorization_id in _DIAGNOSTIC_AUTHORIZATION_IDS:
        _validate_provider_failure_diagnostic_sink(repo_root, paths, require_absent=True)
    return _summary("validate", authorization, None, None, 0)


def _execute(
    repo_root: Path,
    authorization_id: str,
    *,
    resume: bool,
) -> LiveDevelopmentSummary:
    paths = _paths_for_authorization(authorization_id)
    authorization = _load_authorization(repo_root, authorization_id, paths)
    if authorization_id in _DIAGNOSTIC_AUTHORIZATION_IDS:
        _validate_provider_failure_diagnostic_sink(repo_root, paths, require_absent=not resume)
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


def _receipt_public_paths(paths: _BatchPaths) -> tuple[Path, ...]:
    return (
        paths.authorization_path,
        paths.journal_path,
        paths.run_records_path,
        paths.report_path,
        paths.manifest_path,
    )


def _missing_receipt_public_artifacts(repo_root: Path, paths: _BatchPaths) -> tuple[str, ...]:
    return tuple(
        relative_path.as_posix()
        for relative_path in _receipt_public_paths(paths)
        if not (repo_root / relative_path).is_file()
    )


def _receipt_acceptance_failures(
    authorization: LiveDevelopmentAuthorization,
    records: LiveRunRecordSet,
    report: LiveDevelopmentReport,
) -> tuple[str, ...]:
    checks = (
        ("authorization_id", report.authorization_id == authorization.authorization_id),
        ("batch_id", report.batch_id == authorization.batch_id),
        (
            "selected_run_count",
            report.selected_run_count == authorization.maximum_run_count,
        ),
        (
            "terminal_record_count",
            report.terminal_record_count == authorization.maximum_run_count,
        ),
        (
            "completed_run_count",
            report.completed_run_count == authorization.maximum_run_count,
        ),
        (
            "completed_validation_failure_count",
            report.completed_validation_failure_count == 0,
        ),
        ("provider_error_count", report.provider_error_count == 0),
        ("safety_abort_count", report.safety_abort_count == 0),
        ("budget_exhausted_count", report.budget_exhausted_count == 0),
        (
            "structured_output_failure_count",
            report.structured_output_failure_count == 0,
        ),
        ("citation_scope_failure_count", report.citation_scope_failure_count == 0),
        ("attempt_budget_respected", report.attempt_budget_respected),
        ("cost_budget_respected", report.cost_budget_respected),
        (
            "protected_outputs_retained_locally",
            report.protected_outputs_retained_locally,
        ),
        ("live_provider_called", report.live_provider_called),
        ("batch_completed", report.batch_completed),
        ("held_out_executed", not report.held_out_executed),
        ("full_benchmark_executed", not report.full_benchmark_executed),
        ("benchmark_claims_permitted", not report.benchmark_claims_permitted),
        ("measured_execution_permitted", not report.measured_execution_permitted),
        ("comparison_eligible", not report.comparison_eligible),
        (
            "attempt_record_count",
            report.attempt_record_count == records.total_attempt_count,
        ),
        (
            "provider_call_count",
            report.provider_call_count == records.total_attempt_count,
        ),
        (
            "total_estimated_cost_microusd",
            report.total_estimated_cost_microusd == records.total_estimated_cost_microusd,
        ),
        ("records_live_provider_called", records.live_provider_called),
    )
    return tuple(name for name, passed in checks if not passed)


def receipt_assets(repo_root: Path, authorization_id: str) -> LiveDevelopmentReceipt:
    """Fail unless public evidence verifies and the live acceptance contract passes."""

    paths = _paths_for_authorization(authorization_id)
    missing_public = _missing_receipt_public_artifacts(repo_root, paths)
    if missing_public:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_RECEIPT_ARTIFACTS_MISSING",
            "A live-run receipt requires every public evidence artifact.",
            details=missing_public,
        )

    verify_assets(repo_root, authorization_id)
    authorization = _load_authorization(repo_root, authorization_id, paths)
    records = _load_model(repo_root / paths.run_records_path, LiveRunRecordSet)
    report = _load_model(repo_root / paths.report_path, LiveDevelopmentReport)
    acceptance_failures = _receipt_acceptance_failures(authorization, records, report)
    if acceptance_failures:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_RECEIPT_ACCEPTANCE_FAILED",
            "The live batch exists but does not satisfy the acceptance contract.",
            details=acceptance_failures,
        )

    protected_paths = (paths.protected_output_path, paths.raw_provider_output_path)
    missing_protected = tuple(
        relative_path.as_posix()
        for relative_path in protected_paths
        if not (repo_root / relative_path).is_file()
    )
    if missing_protected:
        raise LiveExecutionError(
            "LIVE_DEVELOPMENT_RECEIPT_PROTECTED_EVIDENCE_MISSING",
            "The public batch passed, but required protected local evidence is absent.",
            details=missing_protected,
        )

    public_artifacts = tuple(
        LiveReceiptArtifact(
            path=relative_path.as_posix(),
            sha256=sha256_file(repo_root / relative_path),
        )
        for relative_path in _receipt_public_paths(paths)
    )
    return LiveDevelopmentReceipt(
        authorization_id=authorization.authorization_id,
        public_artifacts=public_artifacts,
        protected_artifact_paths=tuple(item.as_posix() for item in protected_paths),
        terminal_record_count=report.terminal_record_count,
        attempt_record_count=report.attempt_record_count,
        completed_run_count=report.completed_run_count,
        completed_validation_failure_count=report.completed_validation_failure_count,
        provider_error_count=report.provider_error_count,
        safety_abort_count=report.safety_abort_count,
        budget_exhausted_count=report.budget_exhausted_count,
        structured_output_failure_count=report.structured_output_failure_count,
        citation_scope_failure_count=report.citation_scope_failure_count,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "run", "resume", "verify", "receipt"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--authorization-id", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run one bounded live-development action with metadata-safe CLI output."""

    args = _parse_args(argv)
    result: BaseModel
    try:
        if args.command == "validate":
            result = validate_assets(args.repo_root, args.authorization_id)
        elif args.command == "run":
            result = write_assets(args.repo_root, args.authorization_id)
        elif args.command == "resume":
            result = resume_assets(args.repo_root, args.authorization_id)
        elif args.command == "verify":
            result = verify_assets(args.repo_root, args.authorization_id)
        else:
            result = receipt_assets(args.repo_root, args.authorization_id)
    except LiveExecutionError as exc:
        envelope = LiveExecutionErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
