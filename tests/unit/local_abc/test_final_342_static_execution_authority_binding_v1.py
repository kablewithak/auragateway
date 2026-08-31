"""Focused tests for final-342 static execution-authority binding."""

from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import final_342_static_execution_authority_binding_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def _binding() -> subject.Final342StaticExecutionAuthorityBinding:
    return subject.Final342StaticExecutionAuthorityBinding.model_validate_json(
        (ROOT / subject.RECORD_PATH).read_bytes()
    )


def test_binding_preserves_exact_frozen_manifest_custody() -> None:
    binding = _binding()

    assert binding.frozen_manifest.manifest_semantic_sha256 == (
        subject.EXPECTED_MANIFEST_SEMANTIC_SHA256
    )
    assert binding.frozen_manifest.manifest_file_sha256 == (subject.EXPECTED_MANIFEST_FILE_SHA256)
    assert binding.frozen_manifest.first_containing_commit == (
        subject.EXPECTED_FIRST_CONTAINING_COMMIT
    )
    assert binding.frozen_manifest.custody_commit == subject.EXPECTED_CUSTODY_COMMIT
    assert binding.frozen_manifest.post_commit_custody_complete is True
    assert binding.frozen_manifest.repository_execution_manifest_frozen is True


def test_binding_freezes_exact_request_budget_without_extra_calls() -> None:
    binding = _binding()

    assert binding.execution_budget.planned_trajectory_count == 342
    assert binding.execution_budget.planned_turn_count == 1368
    assert binding.execution_budget.maximum_request_attempt_count == 2736
    assert binding.execution_budget.maximum_retries_after_initial_attempt == 1
    assert binding.execution_budget.hidden_retries_permitted is False
    assert binding.execution_budget.replacement_cases_permitted is False
    assert binding.execution_budget.extra_authority_canary_requests_permitted is False
    assert binding.execution_budget.extra_worker_qualification_requests_permitted is False


def test_static_binding_is_not_live_execution_authority() -> None:
    binding = _binding()

    assert binding.authority_boundary.static_authority_binding_complete is True
    assert binding.authority_boundary.execution_manifest_freeze_is_live_authority is False
    assert binding.authority_boundary.static_binding_is_live_issuance is False
    assert binding.authority_boundary.issuer_capability_is_live_issuance is False
    assert binding.authority_boundary.live_authorization_issued is False
    assert binding.authority_boundary.final_measured_abc_execution_authorized is False
    assert binding.authority_boundary.new_execution_authorized is False


def test_single_use_and_execution_subject_controls_are_bound() -> None:
    binding = _binding()

    assert binding.execution_subject.authorization_scope == (
        "FINAL_342_TRANSACTION_BOUND_MEASURED_ABC_V1"
    )
    assert binding.execution_subject.final_manifest_identity_required_on_every_trace is True
    assert binding.execution_subject.transaction_bound_execution_artifact_required is True
    assert binding.execution_subject.route_derived_from_planned_run_only is True
    assert binding.execution_subject.loopback_vllm_transport_only is True
    assert binding.execution_subject.single_use_is_governance_invariant is True
    assert (
        binding.execution_subject.multiple_observed_executions_for_one_transaction_invalidate_acceptance
        is True
    )
    assert binding.execution_subject.runtime_anti_replay_established is False


def test_issuer_qualification_remains_non_issuing() -> None:
    binding = _binding()

    boundary = binding.issuer_qualification_boundary
    assert boundary.exact_static_binding_required is True
    assert boundary.exact_frozen_manifest_required is True
    assert boundary.exact_custody_receipt_required is True
    assert boundary.qualification_may_issue_live_authority is False
    assert boundary.fresh_platform_readiness_required_after_qualification is True
    assert boundary.fresh_human_authority_required_after_qualification is True
    assert boundary.governed_execution_permitted_during_qualification is False


def test_repository_validator_reconstructs_exact_binding() -> None:
    summary = subject.validate(ROOT)

    assert summary["static_authority_binding_complete"] is True
    assert summary["repository_execution_manifest_frozen"] is True
    assert summary["live_authorization_issued"] is False
    assert summary["final_measured_abc_execution_authorized"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["next_gate"] == "QUALIFY_FINAL_342_SINGLE_USE_LIVE_ISSUER_V1"
