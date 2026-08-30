from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import final_342_measured_review_design_v1 as review_design
from auragateway.local_abc import final_342_producer_review_analysis_seam_audit_v1 as audit

ROOT = Path(__file__).resolve().parents[3]


def _record_payload() -> dict[str, object]:
    value = json.loads((ROOT / audit.RECORD_PATH).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise AssertionError("seam-audit record must be a string-keyed object")
    return cast(dict[str, object], value)


def _object_section(
    payload: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value):
        raise AssertionError(f"record section must be a string-keyed object: {key}")
    return dict(cast(dict[str, object], value))


def test_current_seam_audit_validates() -> None:
    result = audit.validate(ROOT)
    assert result["status"] == "FINAL_342_PRODUCER_REVIEW_ANALYSIS_SEAM_AUDIT_V1_VALID"
    assert result["producer_modification_required"] is False
    assert result["existing_transient_response_hook"] is True
    assert result["secondary_schedule_count"] == 41
    assert result["next_gate"] == "AUTHOR_FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1"


def test_secondary_schedule_is_exact_and_unique() -> None:
    rows = audit.derive_secondary_schedule(ROOT)
    assert len(rows) == 41
    run_ids = [str(row["run_id"]) for row in rows]
    assert len(run_ids) == len(set(run_ids))


def test_secondary_schedule_preserves_frozen_allocation() -> None:
    rows = audit.derive_secondary_schedule(ROOT)
    observed: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (
            str(row["condition_id"]),
            str(row["expected_terminal_decision"]),
        )
        observed[key] = observed.get(key, 0) + 1
    assert observed == review_design.secondary_review_stratum_allocation()


def test_record_rejects_producer_modification_requirement() -> None:
    payload = _record_payload()
    producer = _object_section(payload, "producer_seam")
    producer["producer_modification_required"] = True
    payload["producer_seam"] = producer
    with pytest.raises(ValidationError):
        audit.SeamAuditRecord.model_validate(payload)


def test_record_rejects_materialized_schedule_claim() -> None:
    payload = _record_payload()
    review = _object_section(payload, "review_seams")
    schedule = _object_section(review, "exact_secondary_schedule")
    schedule["materialized"] = True
    review["exact_secondary_schedule"] = schedule
    payload["review_seams"] = review
    with pytest.raises(ValidationError):
        audit.SeamAuditRecord.model_validate(payload)


def test_record_rejects_direct_synthetic_feedback_reuse() -> None:
    payload = _record_payload()
    feedback = _object_section(payload, "feedback_seam")
    feedback["historical_synthetic_direct_reuse_permitted"] = True
    payload["feedback_seam"] = feedback
    with pytest.raises(ValidationError):
        audit.SeamAuditRecord.model_validate(payload)


def test_record_rejects_premature_analysis_engine_authority() -> None:
    payload = _record_payload()
    engine = _object_section(payload, "analysis_engine_seam")
    engine["implementation_authorized_by_current_accepted_design"] = True
    payload["analysis_engine_seam"] = engine
    with pytest.raises(ValidationError):
        audit.SeamAuditRecord.model_validate(payload)


def test_record_rejects_next_gate_drift() -> None:
    payload = _record_payload()
    payload["next_gate"] = "MODIFY_FINAL_342_EXECUTION_PRODUCER_V1"
    with pytest.raises(ValidationError):
        audit.SeamAuditRecord.model_validate(payload)
