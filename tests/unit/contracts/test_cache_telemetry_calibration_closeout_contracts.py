from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.cache_telemetry_calibration_closeout import (
    CacheTelemetryCalibrationCloseout,
    CacheTelemetryCalibrationCloseoutManifest,
    CalibrationCloseoutClaimDecision,
    CalibrationCloseoutClaimKind,
    CalibrationCloseoutNextGate,
    CalibrationCloseoutStatus,
)

_CLOSEOUT_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-closeout-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_closeout_loads_with_expected_terminal_state() -> None:
    closeout = CacheTelemetryCalibrationCloseout.model_validate(
        _json_object(_CLOSEOUT_ROOT / "closeout.json")
    )

    assert closeout.status is CalibrationCloseoutStatus.CLOSED_BILLING_FIELD_UNAVAILABLE
    assert closeout.execution_outcome.provider_call_count == 3
    assert closeout.execution_outcome.successful_call_count == 3
    assert closeout.telemetry_assessment.billing_cached_tokens_field_present_count == 0
    assert closeout.telemetry_assessment.unknown_interpreted_as_zero is False
    assert closeout.authorization_consumed is True
    assert closeout.rerun_permitted is False


def test_closeout_contains_all_eight_claim_decisions() -> None:
    closeout = CacheTelemetryCalibrationCloseout.model_validate(
        _json_object(_CLOSEOUT_ROOT / "closeout.json")
    )
    decisions = {item.claim_kind: item.decision for item in closeout.claims}

    assert set(decisions) == set(CalibrationCloseoutClaimKind)
    assert (
        decisions[CalibrationCloseoutClaimKind.EXECUTION_COMPLETED]
        is CalibrationCloseoutClaimDecision.PERMITTED
    )
    assert (
        decisions[CalibrationCloseoutClaimKind.BILLING_FIELD_UNAVAILABLE]
        is CalibrationCloseoutClaimDecision.PERMITTED
    )
    assert (
        decisions[CalibrationCloseoutClaimKind.PROVIDER_CACHE_USAGE]
        is CalibrationCloseoutClaimDecision.BLOCKED
    )


def test_closeout_rejects_missing_execution_binding() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    bindings = deepcopy(payload["execution_bindings"])
    assert isinstance(bindings, list)
    bindings.pop()
    payload["execution_bindings"] = bindings

    with pytest.raises(ValidationError):
        CacheTelemetryCalibrationCloseout.model_validate(payload)


def test_closeout_rejects_duplicate_claim() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    claims = deepcopy(payload["claims"])
    assert isinstance(claims, list)
    claims[-1] = deepcopy(claims[0])
    payload["claims"] = claims

    with pytest.raises(
        ValidationError,
        match="all eight claim decisions",
    ):
        CacheTelemetryCalibrationCloseout.model_validate(payload)


def test_closeout_rejects_cache_claim_promotion() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    claims = payload["claims"]
    assert isinstance(claims, list)
    for claim in claims:
        assert isinstance(claim, dict)
        if claim["claim_kind"] == "provider_cache_usage":
            claim["decision"] = "permitted"
            break

    with pytest.raises(
        ValidationError,
        match="permitted claims require permitted evidence",
    ):
        CacheTelemetryCalibrationCloseout.model_validate(payload)


def test_closeout_preserves_unavailable_not_zero() -> None:
    closeout = CacheTelemetryCalibrationCloseout.model_validate(
        _json_object(_CLOSEOUT_ROOT / "closeout.json")
    )

    assert closeout.telemetry_assessment.billing_cache_numeric_sample_count == 0
    assert closeout.telemetry_assessment.billing_cache_evidence_available is False
    assert closeout.telemetry_assessment.unknown_interpreted_as_zero is False


def test_closeout_manifest_loads_and_locks_source() -> None:
    manifest = CacheTelemetryCalibrationCloseoutManifest.model_validate(
        _json_object(_CLOSEOUT_ROOT / "manifest.json")
    )

    assert manifest.source_evidence_locked is True
    assert manifest.authorization_consumed is True
    assert manifest.rerun_permitted is False
    assert (
        manifest.next_gate is CalibrationCloseoutNextGate.GROQ_SDK_CACHE_SCHEMA_COMPATIBILITY_REVIEW
    )
