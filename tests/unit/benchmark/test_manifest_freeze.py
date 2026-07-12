from __future__ import annotations

import json
from pathlib import Path

from auragateway.benchmark.manifest_freeze import (
    _report_is_public_safe,
    build_isolation_report,
    estimate_cost_budget,
)
from auragateway.contracts.benchmark_preflight import PlannedRunLedger
from auragateway.contracts.execution_freeze import PricingSchedule

_REPO_ROOT = Path(__file__).parents[3]
_FREEZE_ROOT = _REPO_ROOT / "data/evals/benchmark/freeze-v1"
_GATE9_PLAN = _REPO_ROOT / "data/evals/benchmark/preflight-v1/planned_run_ledger.json"


def _pricing() -> PricingSchedule:
    return PricingSchedule.model_validate_json(
        (_FREEZE_ROOT / "pricing_schedule.json").read_text(encoding="utf-8")
    )


def _ledger() -> PlannedRunLedger:
    return PlannedRunLedger.model_validate_json(_GATE9_PLAN.read_text(encoding="utf-8"))


def test_conservative_cost_estimate_is_exact() -> None:
    decision = estimate_cost_budget(
        pricing=_pricing(),
        maximum_request_attempt_count=2736,
        approved_cost_budget_minor_units=500,
    )

    assert decision.estimated_upper_bound_minor_units == 83
    assert decision.approved_cost_budget_minor_units == 500
    assert decision.budget_sufficient is True


def test_insufficient_budget_is_explicit() -> None:
    decision = estimate_cost_budget(
        pricing=_pricing(),
        maximum_request_attempt_count=2736,
        approved_cost_budget_minor_units=82,
    )

    assert decision.estimated_upper_bound_minor_units == 83
    assert decision.budget_sufficient is False


def test_gate9_ledger_passes_cross_condition_isolation() -> None:
    report = build_isolation_report(_ledger())

    assert report.total_trajectory_count == 342
    assert report.comparison_pair_count == 114
    assert report.complete_abc_pair_count == 114
    assert report.unique_cache_namespace_count == 342
    assert report.isolation_passed is True


def test_duplicate_namespace_is_detected() -> None:
    ledger = _ledger()
    first = ledger.runs[0]
    second = ledger.runs[1].model_copy(update={"cache_namespace_id": first.cache_namespace_id})
    mutated = ledger.model_copy(update={"runs": (first, second, *ledger.runs[2:])})

    report = build_isolation_report(mutated)

    assert report.duplicate_cache_namespace_count == 1
    assert report.cross_condition_namespace_reuse_count == 1
    assert report.isolation_passed is False


def test_provider_report_safety_scan_blocks_raw_fields() -> None:
    safe = {"mode": "groq_live", "prompt_summary": {"content_sha256": "a" * 64}}
    unsafe = {"mode": "groq_live", "output_text": "raw output"}

    assert _report_is_public_safe(safe) is True
    assert _report_is_public_safe(unsafe) is False


def test_pricing_json_contains_no_float_values() -> None:
    payload = json.loads((_FREEZE_ROOT / "pricing_schedule.json").read_text())

    assert isinstance(payload["uncached_input_usd_per_million_tokens"], str)
    assert isinstance(payload["cached_input_usd_per_million_tokens"], str)
    assert isinstance(payload["output_usd_per_million_tokens"], str)
