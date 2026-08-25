from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_authority_binding_v1 as subject,
)
from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_wrapper_rehearsal_v1 as rehearsal,
)

ROOT = Path(__file__).resolve().parents[3]


def test_static_binding_is_non_authorizing() -> None:
    review = subject.build_review(ROOT)
    assert review.status == "IMPLEMENTED_NOT_ISSUED"
    assert review.bound_upstream_main_commit == subject.BASE_MAIN_COMMIT
    assert review.candidate_introduced_execution_authority is False
    assert review.live_authorization_issued is False
    assert review.pilot_execution_authorized is False
    assert review.final_measured_abc_execution_authorized is False


def test_v2_budget_is_exact_and_bounded() -> None:
    budget = subject.ExecutionBudget()
    assert budget.maximum_schema_canary_requests == 2
    assert budget.maximum_warmup_requests == 2
    assert budget.maximum_neutral_qualification_requests == 20
    assert budget.maximum_pretreatment_requests == 24
    assert budget.maximum_pilot_trajectory_count == 54
    assert budget.maximum_pilot_turn_count == 216
    assert budget.maximum_pilot_request_attempts == 216
    assert budget.maximum_total_model_requests == 240
    assert budget.maximum_output_tokens_per_request == 256
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_cases == 0


def test_binding_uses_exact_rehearsed_wrapper_identity() -> None:
    review = subject.build_review(ROOT)
    assert (
        review.structural_rehearsal.rendered_wrapper_sha256
        == subject.EXPECTED_RENDERED_WRAPPER_SHA256
    )
    assert review.structural_rehearsal.loaded_runtime_module_count == 6
    assert review.structural_rehearsal.material_validated is True
    assert review.structural_rehearsal.model_requests_performed == 0
    assert review.structural_rehearsal.gpu_execution_performed is False
    assert review.structural_rehearsal.kaggle_execution_performed is False


def test_bound_upstream_boundary_is_exact_and_unique() -> None:
    assert len(subject.BOUND_UPSTREAM_PATHS) == subject.EXPECTED_BOUND_ARTIFACT_COUNT
    assert len(set(subject.BOUND_UPSTREAM_PATHS)) == subject.EXPECTED_BOUND_ARTIFACT_COUNT
    assert rehearsal.TRANSACTION_RUNTIME_PATH in subject.BOUND_UPSTREAM_PATHS
    assert rehearsal.WRAPPER_TEMPLATE_PATH in subject.BOUND_UPSTREAM_PATHS
    assert rehearsal.TOKENIZER_OBSERVATION_PATH in subject.BOUND_UPSTREAM_PATHS


def test_no_live_issuance_surface_is_exposed() -> None:
    assert not hasattr(subject, "issue_live")
    parser = subject._parser()
    for command in ("generate", "validate"):
        parsed = parser.parse_args([command, "--repo-root", str(ROOT)])
        assert parsed.command == command


def test_generated_outputs_validate() -> None:
    result = subject.validate_implementation(ROOT)
    assert result["status"] == ("VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_VALID")
    assert result["bound_upstream_main_commit"] == subject.BASE_MAIN_COMMIT
    assert result["rendered_wrapper_sha256"] == subject.EXPECTED_RENDERED_WRAPPER_SHA256
    assert result["bound_artifact_count"] == subject.EXPECTED_BOUND_ARTIFACT_COUNT
    assert result["candidate_introduced_execution_authority"] is False
    assert result["live_authorization_issued"] is False
    assert result["pilot_execution_authorized"] is False
    assert result["new_execution_authorized"] is False
