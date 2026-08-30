from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import final_342_measured_review_design_v1 as design

ROOT = Path(__file__).resolve().parents[3]


def _payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((ROOT / design.RECORD_PATH).read_text(encoding="utf-8")),
    )


def _section(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict):
        raise AssertionError(f"Expected object section: {key}")
    return cast(dict[str, object], value)


def test_current_measured_review_design_validates() -> None:
    result = design.validate(ROOT)

    assert result["status"] == "FINAL_342_MEASURED_REVIEW_DESIGN_V1_VALID"
    assert result["functional_review_population"] == 162
    assert result["primary_assignment_slots"] == 162
    assert result["secondary_review_target_count"] == 41
    assert result["secondary_review_stratum_count"] == 12
    assert result["sampling_uses_expected_terminal_decision"] is True
    assert result["replacement_review_case_permitted"] is False
    assert result["protected_capture_failure_is_model_quality_failure"] is False
    assert result["quality_non_inferiority_permitted_with_capture_gap"] is False
    assert result["manifest_freeze_permitted"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
    assert result["next_gate"] == "DEFINE_FINAL_342_ANALYSIS_CONTRACTS_V1"


def test_secondary_review_target_uses_conservative_ceiling() -> None:
    assert design.secondary_review_target_count() == 41


def test_secondary_review_allocation_is_deterministic_and_proportional() -> None:
    expected = {
        ("A", "answer"): 7,
        ("A", "clarify"): 2,
        ("A", "escalate"): 2,
        ("A", "refuse"): 2,
        ("B", "answer"): 8,
        ("B", "clarify"): 2,
        ("B", "escalate"): 2,
        ("B", "refuse"): 2,
        ("C", "answer"): 8,
        ("C", "clarify"): 2,
        ("C", "escalate"): 2,
        ("C", "refuse"): 2,
    }
    assert design.secondary_review_stratum_allocation() == expected
    assert sum(expected.values()) == 41


def test_review_item_identity_is_run_specific_and_opaque() -> None:
    left = design.review_item_id("run-functional-ep-func-001-r01-condition-a")
    right = design.review_item_id("run-functional-ep-func-001-r01-condition-b")

    assert left != right
    assert len(left) == 64
    assert "condition-a" not in left
    assert "condition-b" not in right


def test_primary_and_secondary_assignment_ids_are_distinct() -> None:
    item = design.review_item_id("run-functional-ep-func-001-r01-condition-a")
    primary = design.role_assignment_id(item, "primary")
    secondary = design.role_assignment_id(item, "secondary")

    assert primary != secondary
    assert primary.startswith("review-")
    assert secondary.startswith("review-")
    assert len(primary) == len("review-") + 24
    assert len(secondary) == len("review-") + 24


def test_design_rejects_observed_decision_sampling() -> None:
    payload = _payload()
    _section(payload, "sampling_policy")["observed_terminal_decision_used_for_sampling"] = True

    with pytest.raises(ValidationError):
        design.ReviewDesignRecord.model_validate(payload)


def test_design_rejects_post_result_replacement() -> None:
    payload = _payload()
    _section(payload, "review_population")["replacement_review_case_permitted"] = True

    with pytest.raises(ValidationError):
        design.ReviewDesignRecord.model_validate(payload)


def test_design_rejects_condition_in_reviewer_payload() -> None:
    payload = _payload()
    _section(payload, "reviewer_payload")["condition_id_visible"] = True

    with pytest.raises(ValidationError):
        design.ReviewDesignRecord.model_validate(payload)


def test_design_rejects_rendered_prompt_in_reviewer_payload() -> None:
    payload = _payload()
    _section(payload, "reviewer_payload")["internal_rendered_prompt_permitted"] = True

    with pytest.raises(ValidationError):
        design.ReviewDesignRecord.model_validate(payload)


def test_design_rejects_capture_gap_as_quality_valid() -> None:
    payload = _payload()
    _section(payload, "capture_policy")["quality_non_inferiority_permitted_with_capture_gap"] = True

    with pytest.raises(ValidationError):
        design.ReviewDesignRecord.model_validate(payload)


def test_design_rejects_manifest_freeze_or_execution_authority() -> None:
    payload = _payload()
    _section(payload, "safety_state")["manifest_freeze_permitted"] = True

    with pytest.raises(ValidationError):
        design.ReviewDesignRecord.model_validate(payload)
