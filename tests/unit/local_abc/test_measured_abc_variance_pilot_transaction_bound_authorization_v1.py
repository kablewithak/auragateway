from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from auragateway.local_abc import (
    measured_abc_variance_pilot_transaction_bound_authorization_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def test_static_review_is_non_authorizing() -> None:
    review = subject.build_review(ROOT)
    assert review.status == "IMPLEMENTED_NOT_ISSUED"
    assert review.live_authorization_issued is False
    assert review.pilot_execution_authorized is False
    assert review.final_measured_abc_execution_authorized is False
    assert review.authorization_specific_kaggle_inputs == 0
    assert review.manual_confirmation_json_files == 0


def test_budget_separates_timing_preflight_from_pilot_attempts() -> None:
    budget = subject.ExecutionBudget()
    assert budget.maximum_timing_preflight_requests == 2
    assert budget.maximum_cache_salt_preflight_requests == 3
    assert budget.maximum_preflight_requests == 5
    assert budget.maximum_pilot_request_attempts == 432
    assert budget.maximum_total_model_requests == 437
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_external_spend == 0


def test_cache_isolation_contract_is_explicit() -> None:
    isolation = subject.CacheIsolationContract()
    assert isolation.mechanism == "VLLM_CACHE_SALT"
    assert isolation.per_trajectory_cache_salt_required is True
    assert isolation.same_trajectory_cache_reuse_permitted is True
    assert isolation.cross_trajectory_cache_reuse_permitted is False
    assert isolation.cache_salt_security_secret_claimed is False


def test_live_authorization_never_enables_final_measured_abc() -> None:
    now = datetime.now(UTC)
    authorization = subject.LiveAuthorization(
        authorization_id="variance-pilot-tx-test",
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        issuer_merge_commit="a" * 40,
        issuer_source_sha256="b" * 64,
        pilot_runtime_payload_sha256="c" * 64,
        pilot_material_sha256="d" * 64,
        runtime_launcher_readiness_sha256="e" * 64,
        current_p5_p6_acceptance_sha256="f" * 64,
    )
    assert authorization.pilot_execution_authorized is True
    assert authorization.final_measured_abc_execution_authorized is False
    assert authorization.single_use is True
    assert authorization.authorization_reusable is False
    assert authorization.unchanged_replay_authorized is False


def test_generated_outputs_validate() -> None:
    result = subject.validate_implementation(ROOT)
    assert result["status"] == ("VARIANCE_PILOT_TRANSACTION_BOUND_AUTHORIZATION_V1_VALID")
    assert result["candidate_introduced_execution_authority"] is False
