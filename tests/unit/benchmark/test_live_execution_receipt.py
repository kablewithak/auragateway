from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.execution import LiveExecutionError
from auragateway.benchmark.execution_runner import (
    _missing_receipt_public_artifacts,
    _parse_args,
    _paths_for_authorization,
    _receipt_acceptance_failures,
    receipt_assets,
)
from auragateway.contracts.benchmark_execution import (
    LiveDevelopmentAuthorization,
    LiveDevelopmentReport,
    LiveRunRecordSet,
)


@dataclass(frozen=True)
class _AuthorizationView:
    authorization_id: str = "live-development-batch-03-auth-v1"
    batch_id: str = "auragateway-live-development-batch-03"
    maximum_run_count: int = 3


@dataclass(frozen=True)
class _RecordsView:
    total_attempt_count: int = 12
    total_estimated_cost_microusd: int = 700
    live_provider_called: bool = True


@dataclass(frozen=True)
class _ReportView:
    authorization_id: str = "live-development-batch-03-auth-v1"
    batch_id: str = "auragateway-live-development-batch-03"
    selected_run_count: int = 3
    terminal_record_count: int = 3
    attempt_record_count: int = 12
    provider_call_count: int = 12
    completed_run_count: int = 3
    completed_validation_failure_count: int = 0
    provider_error_count: int = 0
    safety_abort_count: int = 0
    budget_exhausted_count: int = 0
    structured_output_failure_count: int = 0
    citation_scope_failure_count: int = 0
    total_estimated_cost_microusd: int = 700
    attempt_budget_respected: bool = True
    cost_budget_respected: bool = True
    protected_outputs_retained_locally: bool = True
    live_provider_called: bool = True
    batch_completed: bool = True
    held_out_executed: bool = False
    full_benchmark_executed: bool = False
    benchmark_claims_permitted: bool = False
    measured_execution_permitted: bool = False
    comparison_eligible: bool = False


def _accepted_models() -> tuple[
    LiveDevelopmentAuthorization,
    LiveRunRecordSet,
    LiveDevelopmentReport,
]:
    authorization = cast(LiveDevelopmentAuthorization, _AuthorizationView())
    records = cast(LiveRunRecordSet, _RecordsView())
    report = cast(LiveDevelopmentReport, _ReportView())
    return authorization, records, report


def test_receipt_command_is_registered() -> None:
    args = _parse_args(
        [
            "receipt",
            "--authorization-id",
            "live-development-batch-03-auth-v1",
        ]
    )

    assert args.command == "receipt"


def test_missing_receipt_artifacts_are_reported_before_verification(
    tmp_path: Path,
) -> None:
    paths = _paths_for_authorization("live-development-batch-03-auth-v1")

    missing = _missing_receipt_public_artifacts(tmp_path, paths)

    assert missing == (
        "data/evals/benchmark/live-development-v3/authorization.json",
        "data/evals/benchmark/live-development-v3/journal.jsonl",
        "data/evals/benchmark/live-development-v3/run_records.json",
        "data/evals/benchmark/live-development-v3/report.json",
        "data/evals/benchmark/live-development-v3/manifest.json",
    )
    with pytest.raises(LiveExecutionError) as exc_info:
        receipt_assets(tmp_path, "live-development-batch-03-auth-v1")
    assert exc_info.value.error_code == "LIVE_DEVELOPMENT_RECEIPT_ARTIFACTS_MISSING"
    assert exc_info.value.details == missing


@pytest.mark.parametrize(
    ("authorization_id", "asset_version"),
    (
        ("live-development-batch-04-auth-v1", "v4"),
        ("live-development-batch-05-auth-v1", "v5"),
    ),
)
def test_diagnostic_batch_receipt_uses_isolated_public_artifact_root(
    tmp_path: Path,
    authorization_id: str,
    asset_version: str,
) -> None:
    paths = _paths_for_authorization(authorization_id)

    missing = _missing_receipt_public_artifacts(tmp_path, paths)

    assert missing == (
        f"data/evals/benchmark/live-development-{asset_version}/authorization.json",
        f"data/evals/benchmark/live-development-{asset_version}/journal.jsonl",
        f"data/evals/benchmark/live-development-{asset_version}/run_records.json",
        f"data/evals/benchmark/live-development-{asset_version}/report.json",
        f"data/evals/benchmark/live-development-{asset_version}/manifest.json",
    )


def test_missing_receipt_artifacts_clear_only_when_all_five_exist(
    tmp_path: Path,
) -> None:
    paths = _paths_for_authorization("live-development-batch-03-auth-v1")
    public_paths = (
        paths.authorization_path,
        paths.journal_path,
        paths.run_records_path,
        paths.report_path,
        paths.manifest_path,
    )
    for relative_path in public_paths:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    assert _missing_receipt_public_artifacts(tmp_path, paths) == ()


def test_acceptance_gate_passes_only_for_complete_clean_evidence() -> None:
    authorization, records, report = _accepted_models()

    assert _receipt_acceptance_failures(authorization, records, report) == ()

    failed_report = cast(
        LiveDevelopmentReport,
        replace(
            cast(_ReportView, report),
            completed_run_count=2,
            provider_error_count=1,
            structured_output_failure_count=1,
        ),
    )
    failures = _receipt_acceptance_failures(authorization, records, failed_report)

    assert failures == (
        "completed_run_count",
        "provider_error_count",
        "structured_output_failure_count",
    )


def test_acceptance_gate_reconciles_report_to_run_records() -> None:
    authorization, records, report = _accepted_models()
    mismatched_records = cast(
        LiveRunRecordSet,
        replace(
            cast(_RecordsView, records),
            total_attempt_count=11,
            total_estimated_cost_microusd=699,
            live_provider_called=False,
        ),
    )

    failures = _receipt_acceptance_failures(authorization, mismatched_records, report)

    assert failures == (
        "attempt_record_count",
        "provider_call_count",
        "total_estimated_cost_microusd",
        "records_live_provider_called",
    )
