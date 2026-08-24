from __future__ import annotations

import hashlib
from pathlib import Path

from auragateway.local_abc import (
    measured_abc_variance_pilot_current_line_reconciliation_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def test_current_acceptance_v2_is_authoritative() -> None:
    review = subject.build_review(ROOT)
    assert review.current_p5_p6_acceptance.path.endswith(
        "auragateway_p5_p6_successor_execution_acceptance_v2.json"
    )
    assert review.historical_p5_p6_acceptance_binding_stale is True
    assert review.current_runtime.vllm_distribution == "0.25.1+cu129"
    assert review.current_runtime.torch == "2.11.0+cu129"


def test_old_pilot_authorization_is_superseded() -> None:
    review = subject.build_review(ROOT)
    assert (
        review.historical_pilot_authorization_status
        == "IMPLEMENTED_BUT_SUPERSEDED_BEFORE_LIVE_ISSUANCE"
    )
    assert review.transaction_bound_authorization_required is True
    assert review.authorization_specific_kaggle_inputs_permitted is False
    assert review.manual_confirmation_json_permitted is False
    assert review.preissuance_platform_observation_required is False
    assert review.post_artifact_platform_observation_required is True


def test_pilot_schedule_is_preserved_exactly() -> None:
    review = subject.build_review(ROOT)
    record = subject.build_record(ROOT, review)
    assert review.pilot_case_count == 6
    assert review.pilot_trajectory_count == 54
    assert review.pilot_turn_count == 216
    assert review.maximum_request_attempt_count == 432
    assert review.hidden_retries_permitted is False
    assert review.replacement_cases_permitted is False
    assert record.pilot_schedule_preserved is True
    assert record.pilot_manifest_binds_schedule is True


def test_timing_telemetry_is_not_promoted_without_evidence() -> None:
    review = subject.build_review(ROOT)
    record = subject.build_record(ROOT, review)
    assert review.current_timing_telemetry_qualification_established is False
    assert review.timing_telemetry_must_fail_closed_before_pilot_requests is True
    assert record.timing_telemetry_preflight_required is True


def test_reconciliation_does_not_authorize_execution() -> None:
    review = subject.build_review(ROOT)
    record = subject.build_record(ROOT, review)
    assert review.runtime_launcher_readiness_committed is False
    assert review.variance_pilot_execution_authorized is False
    assert review.final_measured_abc_execution_authorized is False
    assert record.runtime_launcher_readiness_committed is False
    assert record.variance_pilot_execution_authorized is False
    assert record.final_measured_abc_execution_authorized is False
    assert record.new_execution_authorized is False


def test_review_record_binding_is_deterministic() -> None:
    review = subject.build_review(ROOT)
    record = subject.build_record(ROOT, review)
    expected = hashlib.sha256(
        subject._canonical(review.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()
    assert record.review_sha256 == expected


def test_generated_outputs_validate() -> None:
    result = subject.validate_implementation(ROOT)
    assert result["status"] == "VARIANCE_PILOT_CURRENT_LINE_RECONCILIATION_V1_VALID"
    assert result["candidate_introduced_execution_authority"] is False
