from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    final_342_runtime_requalification_architecture_v1 as architecture,
)

ROOT = Path(__file__).resolve().parents[3]


def _payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((ROOT / architecture.RECORD_PATH).read_text(encoding="utf-8")),
    )


def _section(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict):
        raise AssertionError(f"Expected object section: {key}")
    return cast(dict[str, object], value)


def test_current_architecture_validates() -> None:
    result = architecture.validate(ROOT)

    assert result["status"] == ("FINAL_342_RUNTIME_REQUALIFICATION_ARCHITECTURE_V1_VALID")
    assert result["planned_trajectories"] == 342
    assert result["planned_turns"] == 1368
    assert result["maximum_request_attempts"] == 2736
    assert result["planning_manifest_identity_preserved"] is True
    assert result["runtime_prefix_confirmation_required"] is True
    assert result["ttl_assumption_seconds"] == 300
    assert result["protected_measured_review_export_required"] is True
    assert result["execution_manifest_frozen"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["new_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
    assert result["next_gate"] == "IMPLEMENT_FINAL_342_NON_AUTHORIZING_RUNTIME_CORE_V1"


def test_architecture_rejects_ledger_regeneration() -> None:
    payload = _payload()
    _section(payload, "frozen_subject")["ledger_regeneration_permitted"] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_architecture_rejects_planning_manifest_promotion() -> None:
    payload = _payload()
    _section(payload, "execution_identity_bridge")[
        "planning_manifest_hash_is_final_execution_manifest_hash"
    ] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_architecture_rejects_condition_derived_routes() -> None:
    payload = _payload()
    _section(payload, "route_realization")["derive_route_from_condition_permitted"] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_architecture_rejects_cached_token_requirement_for_warm_state() -> None:
    payload = _payload()
    _section(payload, "warm_eligibility")[
        "observed_cached_tokens_required_for_warm_eligibility"
    ] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_architecture_rejects_v2_pretreatment_in_final_execution() -> None:
    payload = _payload()
    _section(payload, "retry_and_accountability")[
        "v2_pretreatment_requests_carried_into_final_execution"
    ] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_architecture_rejects_public_raw_outputs() -> None:
    payload = _payload()
    _section(payload, "evidence_channels")["public_raw_outputs_permitted"] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_architecture_rejects_reusable_successor_authority() -> None:
    payload = _payload()
    _section(payload, "authorization_boundary")[
        "old_authorization_reusable_true_semantics_permitted_in_successor"
    ] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_architecture_rejects_execution_authority_claim() -> None:
    payload = _payload()
    _section(payload, "safety_state")["new_execution_authorized"] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)
