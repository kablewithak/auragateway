from __future__ import annotations

import json
from pathlib import Path

from auragateway.contracts.telemetry import (
    ClaimDecision,
    ClaimKind,
    TelemetryFixtureSet,
    TelemetryReasonCode,
    TelemetrySufficiencyReport,
)
from auragateway.telemetry.normalize import normalize_telemetry
from auragateway.telemetry.sufficiency import assess_telemetry_sufficiency


def _fixtures() -> TelemetryFixtureSet:
    payload = json.loads(
        Path("data/provider_fixtures/telemetry/fixtures.json").read_text(encoding="utf-8")
    )
    return TelemetryFixtureSet.model_validate(payload)


def _report(case_id: str) -> TelemetrySufficiencyReport:
    fixtures = _fixtures()
    case = next(item for item in fixtures.cases if item.case_id == case_id)
    schedules = {item.schedule_id: item for item in fixtures.pricing_schedules}
    pricing = schedules.get(case.pricing_schedule_id) if case.pricing_schedule_id else None
    return assess_telemetry_sufficiency(normalize_telemetry(case.telemetry), pricing)


def test_valid_cached_detail_permits_all_three_claims() -> None:
    report = _report("cached-detail-valid")
    assert all(item.decision is ClaimDecision.PERMITTED for item in report.decisions)


def test_missing_cache_field_blocks_cache_and_cost_without_fabricating_zero() -> None:
    report = _report("missing-cache-field")
    cache = report.decision_for(ClaimKind.CACHE_EFFICIENCY)
    cost = report.decision_for(ClaimKind.ESTIMATED_COST)
    assert cache.reason_code is TelemetryReasonCode.CACHE_EVIDENCE_UNAVAILABLE
    assert cost.reason_code is TelemetryReasonCode.TOKEN_EVIDENCE_UNAVAILABLE


def test_invalid_denominator_produces_semantics_mismatch() -> None:
    report = _report("invalid-cache-denominator")
    cache = report.decision_for(ClaimKind.CACHE_EFFICIENCY)
    cost = report.decision_for(ClaimKind.ESTIMATED_COST)
    assert cache.reason_code is TelemetryReasonCode.CACHE_SEMANTICS_MISMATCH
    assert cost.reason_code is TelemetryReasonCode.CACHE_SEMANTICS_MISMATCH


def test_local_timing_permits_latency_but_blocks_provider_cache_claim() -> None:
    report = _report("local-timing-only")
    assert report.decision_for(ClaimKind.LATENCY).decision is ClaimDecision.PERMITTED
    assert (
        report.decision_for(ClaimKind.CACHE_EFFICIENCY).reason_code
        is TelemetryReasonCode.CACHE_EVIDENCE_UNAVAILABLE
    )


def test_missing_pricing_blocks_only_estimated_cost() -> None:
    report = _report("missing-pricing-schedule")
    assert report.decision_for(ClaimKind.CACHE_EFFICIENCY).decision is ClaimDecision.PERMITTED
    assert report.decision_for(ClaimKind.LATENCY).decision is ClaimDecision.PERMITTED
    assert (
        report.decision_for(ClaimKind.ESTIMATED_COST).reason_code
        is TelemetryReasonCode.PRICING_EVIDENCE_UNAVAILABLE
    )
