from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from auragateway.contracts.telemetry import (
    ClaimDecision,
    ClaimKind,
    TelemetryFixtureSet,
)
from auragateway.telemetry.normalize import normalize_telemetry
from auragateway.telemetry.sufficiency import assess_telemetry_sufficiency


def _fixtures_payload() -> dict[str, object]:
    raw: object = json.loads(
        Path("data/provider_fixtures/telemetry/fixtures.json").read_text(encoding="utf-8")
    )
    return cast(dict[str, object], raw)


def test_json_key_order_does_not_change_typed_telemetry_meaning() -> None:
    payload = _fixtures_payload()
    original = TelemetryFixtureSet.model_validate(payload)
    reordered = TelemetryFixtureSet.model_validate(dict(reversed(tuple(payload.items()))))
    original_normalized = normalize_telemetry(original.cases[0].telemetry)
    reordered_normalized = normalize_telemetry(reordered.cases[0].telemetry)
    assert original_normalized == reordered_normalized


def test_more_local_timing_evidence_still_cannot_authorize_provider_cache_claim() -> None:
    fixtures = TelemetryFixtureSet.model_validate(_fixtures_payload())
    case = next(item for item in fixtures.cases if item.case_id == "local-timing-only")
    baseline = normalize_telemetry(case.telemetry)
    changed_payload = case.telemetry.model_copy(update={"prompt_eval_duration_ms": 1})
    changed = normalize_telemetry(changed_payload)
    for telemetry in (baseline, changed):
        decision = assess_telemetry_sufficiency(telemetry).decision_for(ClaimKind.CACHE_EFFICIENCY)
        assert decision.decision is ClaimDecision.BLOCKED
