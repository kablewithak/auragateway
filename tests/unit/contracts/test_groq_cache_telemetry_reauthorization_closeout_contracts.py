from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.groq_cache_telemetry_reauthorization_closeout import (
    GroqCacheTelemetryReauthorizationCloseout,
    GroqCacheTelemetryReauthorizationCloseoutManifest,
    ReauthorizationCloseoutClaimDecision,
    ReauthorizationCloseoutClaimKind,
    ReauthorizationCloseoutNextGate,
    ReauthorizationCloseoutStatus,
)

_CLOSEOUT_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-closeout-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_closeout_loads_with_terminal_wire_omission_state() -> None:
    closeout = GroqCacheTelemetryReauthorizationCloseout.model_validate(
        _json_object(_CLOSEOUT_ROOT / "closeout.json")
    )

    assert closeout.status is ReauthorizationCloseoutStatus.CLOSED_PROVIDER_WIRE_FIELD_UNAVAILABLE
    assert closeout.execution_outcome.provider_call_count == 2
    assert closeout.execution_outcome.successful_call_count == 2
    assert closeout.telemetry_assessment.raw_billing_field_absent_count == 2
    assert closeout.telemetry_assessment.raw_billing_numeric_sample_count == 0
    assert closeout.authorization_consumed is True
    assert closeout.provider_calls_permitted is False


def test_closeout_contains_all_ten_claim_decisions() -> None:
    closeout = GroqCacheTelemetryReauthorizationCloseout.model_validate(
        _json_object(_CLOSEOUT_ROOT / "closeout.json")
    )
    decisions = {item.claim_kind: item.decision for item in closeout.claims}

    assert set(decisions) == set(ReauthorizationCloseoutClaimKind)
    assert (
        decisions[ReauthorizationCloseoutClaimKind.EXECUTION_COMPLETED]
        is ReauthorizationCloseoutClaimDecision.PERMITTED
    )
    assert (
        decisions[ReauthorizationCloseoutClaimKind.EXACT_PROVIDER_WIRE_OMISSION_FOR_OBSERVED_CALLS]
        is ReauthorizationCloseoutClaimDecision.PERMITTED
    )
    assert (
        decisions[ReauthorizationCloseoutClaimKind.PROVIDER_CACHE_USAGE]
        is ReauthorizationCloseoutClaimDecision.BLOCKED
    )
    assert (
        decisions[ReauthorizationCloseoutClaimKind.ACCEPTED_A_B_C_COMPARISON]
        is ReauthorizationCloseoutClaimDecision.BLOCKED
    )


def test_closeout_rejects_missing_execution_binding() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    bindings = deepcopy(payload["execution_bindings"])
    assert isinstance(bindings, list)
    bindings.pop()
    payload["execution_bindings"] = bindings

    with pytest.raises(ValidationError):
        GroqCacheTelemetryReauthorizationCloseout.model_validate(payload)


def test_closeout_rejects_duplicate_claim() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    claims = deepcopy(payload["claims"])
    assert isinstance(claims, list)
    claims[-1] = deepcopy(claims[0])
    payload["claims"] = claims

    with pytest.raises(ValidationError, match="all ten claim decisions"):
        GroqCacheTelemetryReauthorizationCloseout.model_validate(payload)


def test_closeout_rejects_universal_omission_promotion() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    claims = payload["claims"]
    assert isinstance(claims, list)
    for claim in claims:
        assert isinstance(claim, dict)
        if claim["claim_kind"] == "universal_provider_wire_omission":
            claim["decision"] = "permitted"
            break

    with pytest.raises(
        ValidationError,
        match="permitted claims require permitted evidence",
    ):
        GroqCacheTelemetryReauthorizationCloseout.model_validate(payload)


def test_closeout_preserves_unknown_not_zero() -> None:
    closeout = GroqCacheTelemetryReauthorizationCloseout.model_validate(
        _json_object(_CLOSEOUT_ROOT / "closeout.json")
    )

    assert closeout.telemetry_assessment.provider_cache_usage_evidence_available is False
    assert closeout.telemetry_assessment.unknown_interpreted_as_zero is False
    decisions = {item.claim_kind: item.decision for item in closeout.claims}
    assert (
        decisions[ReauthorizationCloseoutClaimKind.CACHED_TOKENS_EQUAL_ZERO]
        is ReauthorizationCloseoutClaimDecision.BLOCKED
    )


def test_closeout_preserves_hash_only_protected_lineage() -> None:
    closeout = GroqCacheTelemetryReauthorizationCloseout.model_validate(
        _json_object(_CLOSEOUT_ROOT / "closeout.json")
    )

    assert closeout.protected_evidence.protected_content_committed is False
    assert closeout.protected_evidence.protected_content_read_by_closeout is False
    assert closeout.protected_evidence.hash_lineage_preserved is True


def test_closeout_closes_gate_4_without_passing_it() -> None:
    closeout = GroqCacheTelemetryReauthorizationCloseout.model_validate(
        _json_object(_CLOSEOUT_ROOT / "closeout.json")
    )

    assert closeout.gate_4_resolution.gate_4_passed is False
    assert closeout.gate_4_resolution.negative_result_accepted is True
    assert closeout.benchmark_execution_permitted is False
    assert closeout.comparison_eligible is False
    assert (
        closeout.next_gate
        is ReauthorizationCloseoutNextGate.AURAGATEWAY_V2_TERMINAL_EVIDENCE_REVIEW
    )


def test_closeout_manifest_locks_source_and_execution() -> None:
    manifest = GroqCacheTelemetryReauthorizationCloseoutManifest.model_validate(
        _json_object(_CLOSEOUT_ROOT / "manifest.json")
    )

    assert manifest.source_evidence_locked is True
    assert manifest.protected_evidence_read is False
    assert manifest.authorization_consumed is True
    assert manifest.provider_calls_permitted is False
    assert manifest.rerun_permitted is False
