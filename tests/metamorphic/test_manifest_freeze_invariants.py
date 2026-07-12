from __future__ import annotations

from pathlib import Path

from auragateway.benchmark.manifest_freeze import (
    build_isolation_report,
    estimate_cost_budget,
)
from auragateway.contracts.benchmark_preflight import PlannedRunLedger
from auragateway.contracts.execution_freeze import PricingSchedule

_REPO_ROOT = Path(__file__).parents[2]
_FREEZE_ROOT = _REPO_ROOT / "data/evals/benchmark/freeze-v1"
_GATE9_PLAN = _REPO_ROOT / "data/evals/benchmark/preflight-v1/planned_run_ledger.json"


def _pricing() -> PricingSchedule:
    return PricingSchedule.model_validate_json(
        (_FREEZE_ROOT / "pricing_schedule.json").read_text(encoding="utf-8")
    )


def _ledger() -> PlannedRunLedger:
    return PlannedRunLedger.model_validate_json(_GATE9_PLAN.read_text(encoding="utf-8"))


def test_run_order_projection_does_not_change_isolation_counts() -> None:
    ledger = _ledger()
    original = build_isolation_report(ledger)
    reversed_ledger = ledger.model_copy(update={"runs": tuple(reversed(ledger.runs))})
    reversed_report = build_isolation_report(reversed_ledger)

    assert reversed_report.model_dump(exclude={"report_id"}) == original.model_dump(
        exclude={"report_id"}
    )


def test_higher_approved_budget_does_not_change_estimate() -> None:
    low = estimate_cost_budget(
        pricing=_pricing(),
        maximum_request_attempt_count=2736,
        approved_cost_budget_minor_units=100,
    )
    high = estimate_cost_budget(
        pricing=_pricing(),
        maximum_request_attempt_count=2736,
        approved_cost_budget_minor_units=500,
    )

    assert low.estimated_upper_bound_minor_units == high.estimated_upper_bound_minor_units
    assert low.budget_sufficient is True
    assert high.budget_sufficient is True


def test_cached_price_does_not_reduce_pre_execution_upper_bound() -> None:
    pricing = _pricing()
    cheaper_cache = pricing.model_copy(
        update={
            "cached_input_usd_per_million_tokens": (pricing.cached_input_usd_per_million_tokens / 2)
        }
    )

    original = estimate_cost_budget(
        pricing=pricing,
        maximum_request_attempt_count=2736,
        approved_cost_budget_minor_units=500,
    )
    mutated = estimate_cost_budget(
        pricing=cheaper_cache,
        maximum_request_attempt_count=2736,
        approved_cost_budget_minor_units=500,
    )

    assert mutated.estimated_upper_bound_minor_units == original.estimated_upper_bound_minor_units


def test_derived_trace_id_count_matches_run_count() -> None:
    report = build_isolation_report(_ledger())

    assert report.unique_trace_id_count == report.total_trajectory_count
    assert report.duplicate_trace_id_count == 0
