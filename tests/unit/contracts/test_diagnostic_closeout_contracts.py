from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.diagnostic_closeout import (
    DiagnosticClaimDecision,
    DiagnosticClaimKind,
    DiagnosticCloseout,
    DiagnosticCloseoutManifest,
    DiagnosticHypothesisId,
)

_CLOSEOUT_ROOT = Path("data/evals/benchmark/diagnostic-closeout-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_closeout_validates_terminal_nonreproduction() -> None:
    closeout = DiagnosticCloseout.model_validate(_json_object(_CLOSEOUT_ROOT / "closeout.json"))

    assert closeout.status.value == "closed_nonreproduced"
    assert closeout.execution_outcome.provider_call_count == 24
    assert closeout.execution_outcome.successful_call_count == 24
    assert closeout.execution_outcome.provider_error_count == 0
    assert closeout.authorization_consumed is True
    assert closeout.rerun_permitted is False
    assert closeout.next_gate.value == "cache_telemetry_sufficiency_review"


def test_closeout_contains_every_predeclared_hypothesis() -> None:
    closeout = DiagnosticCloseout.model_validate(_json_object(_CLOSEOUT_ROOT / "closeout.json"))

    observed = {item.hypothesis_id for item in closeout.hypotheses}
    assert observed == set(DiagnosticHypothesisId)


def test_cache_unknown_is_not_zero() -> None:
    closeout = DiagnosticCloseout.model_validate(_json_object(_CLOSEOUT_ROOT / "closeout.json"))

    assert closeout.cache_telemetry.cached_input_token_sample_count == 0
    assert closeout.cache_telemetry.total_cached_input_tokens is None
    assert closeout.cache_telemetry.cached_share_parts_per_million is None
    assert closeout.cache_telemetry.unknown_interpreted_as_zero is False


def test_cache_and_latency_claims_are_blocked() -> None:
    closeout = DiagnosticCloseout.model_validate(_json_object(_CLOSEOUT_ROOT / "closeout.json"))
    decisions = {item.claim_kind: item.decision for item in closeout.claims}

    assert decisions[DiagnosticClaimKind.CACHE_USAGE] is DiagnosticClaimDecision.BLOCKED
    assert decisions[DiagnosticClaimKind.CACHE_SAVINGS] is DiagnosticClaimDecision.BLOCKED
    assert decisions[DiagnosticClaimKind.LATENCY_IMPROVEMENT] is DiagnosticClaimDecision.BLOCKED
    assert (
        decisions[DiagnosticClaimKind.ACCEPTED_A_B_C_COMPARISON] is DiagnosticClaimDecision.BLOCKED
    )


def test_closeout_rejects_rerun_enablement() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    payload["rerun_permitted"] = True

    with pytest.raises(ValidationError):
        DiagnosticCloseout.model_validate(payload)


def test_closeout_rejects_cache_unknown_as_zero() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    cache = deepcopy(payload["cache_telemetry"])
    assert isinstance(cache, dict)
    cache["total_cached_input_tokens"] = 0
    payload["cache_telemetry"] = cache

    with pytest.raises(ValidationError):
        DiagnosticCloseout.model_validate(payload)


def test_closeout_rejects_missing_hypothesis() -> None:
    payload = _json_object(_CLOSEOUT_ROOT / "closeout.json")
    hypotheses = deepcopy(payload["hypotheses"])
    assert isinstance(hypotheses, list)
    hypotheses.pop()
    payload["hypotheses"] = hypotheses

    with pytest.raises(ValidationError):
        DiagnosticCloseout.model_validate(payload)


def test_closeout_manifest_locks_execution_manifest() -> None:
    manifest = DiagnosticCloseoutManifest.model_validate(
        _json_object(_CLOSEOUT_ROOT / "manifest.json")
    )

    assert manifest.execution_manifest_sha256 == (
        "0715d0e64188a3a55909b1fd8a048a06d1f4a32a3351bdfb3b01c0167ad6e97f"
    )
    assert manifest.source_evidence_locked is True
    assert manifest.authorization_consumed is True
    assert manifest.rerun_permitted is False
