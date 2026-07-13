"""Validate the non-live Batch 06 request-rejection diagnostic design."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.diagnostic_experiment import (
    DiagnosticDesignManifest,
    DiagnosticDesignValidationSummary,
    DiagnosticExperimentPlan,
)

_DEFAULT_DESIGN_ROOT = Path("data/evals/benchmark/diagnostic-design-v1")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class DiagnosticDesignError(Exception):
    """Expected metadata-safe diagnostic design validation failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        *,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class _SourceBatchManifestProjection(BaseModel):
    """Fields required to bind the design to Batch 06 public evidence."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    journal_sha256: str
    run_records_sha256: str
    report_sha256: str
    live_provider_called: bool
    held_out_executed: bool
    full_benchmark_executed: bool
    benchmark_claims_permitted: bool
    measured_execution_permitted: bool
    comparison_eligible: bool


class _SourceBatchReportProjection(BaseModel):
    """Batch 06 outcome facts needed by the design validator."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    batch_id: str
    authorization_id: str
    terminal_record_count: int
    attempt_record_count: int
    completed_run_count: int
    provider_error_count: int
    development_only: bool
    live_provider_called: bool
    held_out_executed: bool
    full_benchmark_executed: bool
    benchmark_claims_permitted: bool
    measured_execution_permitted: bool
    comparison_eligible: bool
    batch_completed: bool


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_REQUIRED_ASSET_MISSING",
            "A required diagnostic design asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_INVALID_JSON",
            "A diagnostic design asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_VALIDATION_FAILED",
            "A diagnostic design asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def validate_diagnostic_design(
    repo_root: Path,
    design_root: Path = _DEFAULT_DESIGN_ROOT,
) -> DiagnosticDesignValidationSummary:
    """Validate design integrity without creating authorization or provider calls."""

    resolved_root = repo_root / design_root
    plan_path = resolved_root / "experiment_plan.json"
    manifest_path = resolved_root / "manifest.json"
    authorization_path = resolved_root / "authorization.json"

    if authorization_path.exists():
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_AUTHORIZATION_FORBIDDEN",
            "The design-only artifact must not contain an execution authorization.",
            path=str(authorization_path),
        )

    plan = _load_model(plan_path, DiagnosticExperimentPlan)
    manifest = _load_model(manifest_path, DiagnosticDesignManifest)

    if plan.design_id != manifest.design_id:
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_ID_MISMATCH",
            "The plan and manifest identify different diagnostic designs.",
        )

    observed_plan_sha256 = _sha256_file(plan_path)
    if observed_plan_sha256 != manifest.plan_sha256:
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_PLAN_HASH_MISMATCH",
            "The diagnostic experiment plan no longer matches its manifest.",
            path=str(plan_path),
        )

    expected_plan_path = (repo_root / manifest.plan_path).resolve()
    if expected_plan_path != plan_path.resolve():
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_PLAN_PATH_MISMATCH",
            "The manifest plan path does not resolve to the validated plan.",
            path=str(plan_path),
        )

    source_manifest_path = repo_root / manifest.source_batch_manifest_path
    source_manifest = _load_model(
        source_manifest_path,
        _SourceBatchManifestProjection,
    )

    expected_hashes = (
        manifest.source_journal_sha256,
        manifest.source_run_records_sha256,
        manifest.source_report_sha256,
    )
    observed_hashes = (
        source_manifest.journal_sha256,
        source_manifest.run_records_sha256,
        source_manifest.report_sha256,
    )
    if observed_hashes != expected_hashes:
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_SOURCE_EVIDENCE_MISMATCH",
            "The Batch 06 public evidence identities differ from the frozen design anchor.",
            path=str(source_manifest_path),
        )

    unsafe_source_flags = (
        source_manifest.held_out_executed,
        source_manifest.full_benchmark_executed,
        source_manifest.benchmark_claims_permitted,
        source_manifest.measured_execution_permitted,
        source_manifest.comparison_eligible,
    )
    if not source_manifest.live_provider_called or any(unsafe_source_flags):
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_SOURCE_MANIFEST_STATE_INVALID",
            "The source manifest does not represent the bounded Batch 06 development evidence.",
            path=str(source_manifest_path),
        )

    source_report_path = source_manifest_path.with_name("report.json")
    source_report = _load_model(source_report_path, _SourceBatchReportProjection)

    expected_report_identity = (
        plan.source_anchor.source_batch_id,
        plan.source_anchor.source_authorization_id,
    )
    observed_report_identity = (
        source_report.batch_id,
        source_report.authorization_id,
    )
    if observed_report_identity != expected_report_identity:
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_SOURCE_REPORT_IDENTITY_MISMATCH",
            "The source report identity differs from the frozen Batch 06 anchor.",
            path=str(source_report_path),
        )

    expected_counts = (3, 11, 2, 1)
    observed_counts = (
        source_report.terminal_record_count,
        source_report.attempt_record_count,
        source_report.completed_run_count,
        source_report.provider_error_count,
    )
    if observed_counts != expected_counts:
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_SOURCE_REPORT_COUNTS_MISMATCH",
            "The source report no longer contains the recorded Batch 06 outcome.",
            path=str(source_report_path),
        )

    unsafe_report_flags = (
        source_report.held_out_executed,
        source_report.full_benchmark_executed,
        source_report.benchmark_claims_permitted,
        source_report.measured_execution_permitted,
        source_report.comparison_eligible,
    )
    if (
        not source_report.development_only
        or not source_report.live_provider_called
        or not source_report.batch_completed
        or any(unsafe_report_flags)
    ):
        raise DiagnosticDesignError(
            "DIAGNOSTIC_DESIGN_SOURCE_REPORT_STATE_INVALID",
            "The source report does not preserve the bounded failed-verification state.",
            path=str(source_report_path),
        )

    return DiagnosticDesignValidationSummary(
        design_id=plan.design_id,
        status=plan.status,
        hypothesis_count=len(plan.hypotheses),
        cohort_count=len(plan.cohorts),
        sequence_count=len(plan.sequences),
        maximum_provider_calls=plan.maximum_provider_calls,
        plan_sha256=observed_plan_sha256,
    )


def _error_envelope(exc: DiagnosticDesignError) -> str:
    return json.dumps(
        {
            "error_code": exc.error_code,
            "safe_message": exc.safe_message,
            "path": exc.path,
            "details": exc.details,
        },
        indent=2,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the non-live Batch 06 request-rejection design."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root containing the design and Batch 06 public evidence.",
    )
    parser.add_argument(
        "--design-root",
        type=Path,
        default=_DEFAULT_DESIGN_ROOT,
        help="Repository-relative diagnostic design directory.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        summary = validate_diagnostic_design(
            args.repo_root.resolve(),
            args.design_root,
        )
    except DiagnosticDesignError as exc:
        print(_error_envelope(exc), file=sys.stderr)
        return 1

    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
