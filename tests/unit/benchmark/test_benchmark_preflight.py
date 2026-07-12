from __future__ import annotations

from pathlib import Path

from auragateway.benchmark.preflight import build_run_ledger, evaluate_preflight
from auragateway.contracts.benchmark_preflight import (
    BenchmarkBudgetEnvelope,
    BenchmarkPreflightInput,
    BenchmarkWorkload,
    PreflightFailureCode,
)
from auragateway.contracts.evidence_bundle import BenchmarkCondition

ROOT = Path(__file__).resolve().parents[3]
INPUT_PATH = ROOT / "data/evals/benchmark/preflight-v1/input.json"


def load_input() -> BenchmarkPreflightInput:
    return BenchmarkPreflightInput.model_validate_json(INPUT_PATH.read_text(encoding="utf-8"))


def test_plan_expands_frozen_functional_and_runtime_matrices() -> None:
    input_asset = load_input()
    ledger = build_run_ledger(input_asset.plan_request)

    assert ledger.functional_trajectory_count == 162
    assert ledger.runtime_trajectory_count == 180
    assert ledger.total_trajectory_count == 342
    assert ledger.total_turn_count == 1368
    assert ledger.maximum_request_attempt_count == 2736
    assert ledger.execution_enabled is False


def test_functional_counterbalance_order_is_frozen() -> None:
    ledger = build_run_ledger(load_input().plan_request)
    first_episode = tuple(
        run
        for run in ledger.runs
        if run.workload is BenchmarkWorkload.FUNCTIONAL and run.episode_id == "ep-func-001"
    )

    assert tuple(run.condition_id for run in first_episode[:9]) == (
        BenchmarkCondition.A,
        BenchmarkCondition.B,
        BenchmarkCondition.C,
        BenchmarkCondition.B,
        BenchmarkCondition.C,
        BenchmarkCondition.A,
        BenchmarkCondition.C,
        BenchmarkCondition.A,
        BenchmarkCondition.B,
    )


def test_every_run_has_a_unique_cache_namespace() -> None:
    ledger = build_run_ledger(load_input().plan_request)
    namespaces = [run.cache_namespace_id for run in ledger.runs]

    assert len(namespaces) == len(set(namespaces)) == 342


def test_preflight_is_planning_ready_but_measured_execution_blocked() -> None:
    input_asset = load_input()
    ledger = build_run_ledger(input_asset.plan_request)
    report = evaluate_preflight(
        manifest=input_asset.execution_manifest,
        provider=input_asset.provider_readiness,
        budget=input_asset.budget,
        vault=input_asset.evidence_vault,
        ledger=ledger,
    )

    assert report.planning_ready is True
    assert report.measured_execution_ready is False
    assert report.execution_enabled is False
    assert report.measured_execution_permitted is False
    assert report.failure_codes == (
        PreflightFailureCode.EXECUTION_MANIFEST_ASSETS_UNRESOLVED,
        PreflightFailureCode.EXECUTION_MANIFEST_NOT_FROZEN,
        PreflightFailureCode.PROVIDER_CONFIGURATION_NOT_READY,
        PreflightFailureCode.PROVIDER_LIVE_PROBE_NOT_PASSED,
        PreflightFailureCode.COST_BUDGET_NOT_DECLARED,
    )


def test_insufficient_request_budget_blocks_planning() -> None:
    input_asset = load_input()
    ledger = build_run_ledger(input_asset.plan_request)
    report = evaluate_preflight(
        manifest=input_asset.execution_manifest,
        provider=input_asset.provider_readiness,
        budget=BenchmarkBudgetEnvelope(
            maximum_trajectory_count=341,
            maximum_turn_count=1368,
            maximum_request_attempt_count=2736,
            currency="USD",
        ),
        vault=input_asset.evidence_vault,
        ledger=ledger,
    )

    assert report.planning_ready is False
    assert PreflightFailureCode.REQUEST_BUDGET_INSUFFICIENT in report.failure_codes


def test_runtime_subset_starts_after_all_functional_runs() -> None:
    ledger = build_run_ledger(load_input().plan_request)

    assert ledger.runs[161].workload is BenchmarkWorkload.FUNCTIONAL
    assert ledger.runs[162].workload is BenchmarkWorkload.RUNTIME
    assert ledger.runs[162].schedule_index == 162
