from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import p5_p6_successor_runtime_qualification_v1_review as subject

ROOT = Path(__file__).resolve().parents[3]


def test_review_selects_exact_p4_case_a_without_reselection() -> None:
    review = subject.build_review()
    assert review.selected_p4_contract.case_id == "A"
    assert review.selected_p4_contract.prompt_variant == "V4"
    assert review.selected_p4_contract.repetition_penalty == 1.1
    assert review.selected_p4_contract.output_mode == "UNCONSTRAINED"
    assert review.selected_p4_contract.exact_object_required is True
    assert review.selected_p4_contract.reselection_permitted is False
    assert review.selected_p4_contract.json_schema_required is False


def test_selected_p4_repetition_penalty_rejects_contract_drift() -> None:
    with pytest.raises(ValidationError):
        subject.SelectedP4Contract(repetition_penalty=1.0)

    with pytest.raises(ValidationError):
        subject.SelectedP4Contract(repetition_penalty=1.2)

    with pytest.raises(ValidationError):
        subject.SelectedP4Contract.model_validate({"repetition_penalty": "1.1"})


def test_review_preserves_v5_execution_budget() -> None:
    budget = subject.build_review().execution_budget
    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_runtime_install_attempts == 1
    assert budget.maximum_runtime_import_closure_probes == 1
    assert budget.maximum_model_loads == 3
    assert budget.maximum_worker_starts == 3
    assert budget.maximum_model_requests == 5
    assert budget.maximum_output_tokens_per_request == 32
    assert budget.benchmark_trajectory_requests_permitted == 0
    assert budget.hidden_retries_permitted == 0
    assert budget.network_requests_permitted == 0
    assert budget.external_spend == 0


def test_review_probe_order_and_request_budget_are_exact() -> None:
    review = subject.build_review()
    assert tuple(probe.probe_id for probe in review.probes) == (
        "P3_CANARY",
        "P4_CANARY",
        "P5",
        "P6",
    )
    assert tuple(probe.maximum_model_requests for probe in review.probes) == (0, 1, 2, 2)
    assert sum(probe.maximum_model_requests for probe in review.probes) == 5


def test_review_requires_full_p5_reset_and_explicit_cache_evidence() -> None:
    review = subject.build_review()
    joined = "\n".join(review.p5_requirements)
    assert "request-attributable token telemetry" in joined
    assert "latency alone" in joined
    assert "full worker-process termination and restart" in joined
    assert "fresh process identity" in joined
    assert "cache baseline" in joined


def test_review_requires_p6_route_metric_and_process_isolation() -> None:
    review = subject.build_review()
    joined = "\n".join(review.p6_requirements)
    assert "GPU 0/port 8001" in joined
    assert "GPU 1/port 8002" in joined
    assert "TRITON_ATTN" in joined
    assert "route proof uses harness routing acknowledgement" in joined
    assert "model-generated route semantics" in joined
    assert "request-attributable metric evidence" in joined
    assert "partial stage checkpoints" in joined


def test_review_does_not_authorize_execution_or_measured_abc() -> None:
    review = subject.build_review()
    assert review.runtime_execution_authorized is False
    assert review.measured_abc_execution_authorized is False
    assert review.execution_manifest_freeze_authorized is False
    assert review.next_gate == "implement_and_merge_p5_p6_successor_runtime_qualification_v1"


def test_review_binds_all_required_predecessor_authorities() -> None:
    review = subject.build_review()
    assert tuple(authority.authority_id for authority in review.authorities) == (
        "option_c_runtime_diagnostic_decision_v1",
        "p3_p6_v4_failure_acceptance_review",
        "p3_p6_v5_implementation_record",
        "p3_p6_v5_failure_acceptance_review",
        "p4_v2_execution_acceptance_record",
        "p4_v2_execution_acceptance_review",
    )


def test_review_canonical_json_is_deterministic_and_round_trips() -> None:
    review = subject.build_review()
    payload_1 = review.canonical_json()
    payload_2 = subject.build_review().canonical_json()
    assert payload_1 == payload_2
    decoded = json.loads(payload_1)
    assert subject.ReviewArtifact.model_validate(decoded) == review


def test_probe_budget_overflow_is_rejected() -> None:
    review = subject.build_review()
    payload = review.model_dump(mode="json")
    payload["probes"][1]["maximum_model_requests"] = 5
    with pytest.raises(ValidationError, match="successor model-request budget drifted"):
        subject.ReviewArtifact.model_validate(payload)


def test_candidate_boundary_is_exact() -> None:
    assert (
        tuple(
            sorted(
                (
                    subject.REVIEW_PATH,
                    subject.SOURCE_PATH,
                    subject.TEST_PATH,
                    subject.ADR_PATH,
                    subject.REPORT_PATH,
                    subject.RUNBOOK_PATH,
                )
            )
        )
        == subject.CANDIDATE_PATHS
    )
    assert len(subject.CANDIDATE_PATHS) == 6


def test_nonclaims_cover_remaining_full_run_gates() -> None:
    joined = "\n".join(subject.build_review().non_claims)
    assert "342-trajectory benchmark is not authorized" in joined
    assert "Pressure and eviction behavior" in joined
    assert "Fault-recovery behavior" in joined
    assert "Variance adequacy and repetition count" in joined
    assert "execution manifest is not frozen" in joined
    assert "production readiness" in joined


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="real repository authorities are unavailable in synthetic fixture",
)
def test_current_repository_authorities_validate() -> None:
    result = subject.validate_authorities(ROOT)
    assert result["status"] == "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_AUTHORITIES_VALID"
    assert result["selected_case_id"] == "A"
    assert result["runtime_execution_authorized"] is False
    assert result["measured_abc_execution_authorized"] is False
