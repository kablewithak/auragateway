from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import final_342_analysis_contracts_v1 as analysis

ROOT = Path(__file__).resolve().parents[3]


def _payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((ROOT / analysis.RECORD_PATH).read_text(encoding="utf-8")),
    )


def _section(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict):
        raise AssertionError(f"Expected object section: {key}")
    return cast(dict[str, object], value)


def test_current_analysis_contracts_validate() -> None:
    result = analysis.validate(ROOT)

    assert result["status"] == "FINAL_342_ANALYSIS_CONTRACTS_V1_VALID"
    assert result["scientific_scheduled_trajectory_count"] == 342
    assert result["scientific_scheduled_logical_turn_count"] == 1368
    assert result["maximum_physical_attempt_count"] == 2736
    assert result["functional_quality_population"] == 162
    assert result["secondary_review_target_count"] == 41
    assert result["runtime_population"] == 180
    assert result["runtime_comparison_pair_count"] == 60
    assert result["request_counter_is_scientific_denominator"] is False
    assert result["measured_task_success_reducer_required"] is True
    assert result["measured_feedback_successor_required"] is True
    assert result["manifest_freeze_permitted"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
    assert result["next_gate"] == "AUDIT_FINAL_342_PRODUCER_REVIEW_ANALYSIS_SEAMS_V1"


def test_analysis_rejects_operational_counter_as_scientific_denominator() -> None:
    payload = _payload()
    _section(payload, "denominator_authority")[
        "request_reconciliation_scheduled_request_count_is_scientific_denominator"
    ] = True

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)


def test_analysis_rejects_capture_gap_quality_promotion() -> None:
    payload = _payload()
    _section(payload, "quality_analysis")["capture_gap_permits_quality_noninferiority"] = True

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)


def test_analysis_rejects_post_result_secondary_replacement() -> None:
    payload = _payload()
    _section(payload, "quality_analysis")["selected_nonreviewable_case_replacement_permitted"] = (
        True
    )

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)


def test_analysis_requires_measured_task_success_reducer() -> None:
    payload = _payload()
    _section(payload, "quality_analysis")[
        "measured_task_success_reducer_required_before_manifest_freeze"
    ] = False

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)


def test_analysis_rejects_synthetic_quality_gate_as_measured_boundary() -> None:
    payload = _payload()
    _section(payload, "quality_analysis")[
        "historical_synthetic_quality_gate_direct_measured_reuse_permitted"
    ] = True

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)


def test_analysis_preserves_primary_runtime_endpoint() -> None:
    payload = _payload()
    _section(payload, "runtime_analysis")["primary_endpoint_id"] = "latency-v1"

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)


def test_analysis_preserves_frozen_claim_precedence() -> None:
    payload = _payload()
    _section(payload, "statistical_and_claim_analysis")["decision_precedence"] = [
        "metric_calculation",
        "quality_noninferiority_decision",
    ]

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)


def test_analysis_requires_measured_feedback_successor() -> None:
    payload = _payload()
    _section(payload, "feedback_analysis")[
        "measured_feedback_successor_required_before_manifest_freeze"
    ] = False

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)


def test_analysis_does_not_authorize_producer_mutation_or_execution() -> None:
    payload = _payload()
    _section(payload, "implementation_boundary")[
        "producer_modification_authorized_by_this_decision"
    ] = True

    with pytest.raises(ValidationError):
        analysis.AnalysisContractsRecord.model_validate(payload)
