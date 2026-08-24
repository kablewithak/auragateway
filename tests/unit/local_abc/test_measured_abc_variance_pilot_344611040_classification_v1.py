from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    measured_abc_variance_pilot_344611040_classification_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def test_governed_execution_pass_is_distinct_from_pilot_acceptance() -> None:
    classification = subject.build_classification(ROOT)
    assert classification.governed_execution_disposition == ("ACCEPTED_GOVERNED_EXECUTION_PASS")
    assert classification.runtime_fatal_failure is False
    assert classification.pilot_repository_acceptance_established is False
    assert classification.final_measured_abc_execution_authorized is False
    assert classification.new_execution_authorized is False


def test_cache_salt_mechanism_evidence_is_preserved() -> None:
    classification = subject.build_classification(ROOT)
    cache = classification.cache_salt
    assert cache.status == "QUALIFIED"
    assert cache.same_salt_cold_cached_prefix_tokens == 0
    assert cache.same_salt_warm_cached_prefix_tokens == 944
    assert cache.different_salt_cached_prefix_tokens == 0
    assert cache.cross_salt_reuse_observed is False


def test_task_output_contract_failure_is_not_hidden_by_runtime_pass() -> None:
    classification = subject.build_classification(ROOT)
    task = classification.task_output
    assert task.failed_trajectory_count == 54
    assert task.request_completed_turn_count == 216
    assert task.finish_reason_length_count == 132
    assert task.finish_reason_stop_count == 84
    assert task.json_valid_turn_count == 6
    assert task.json_invalid_turn_count == 210
    assert task.task_output_contract == "FAILED"


def test_worker_projection_is_explicitly_classified_as_confounded() -> None:
    classification = subject.build_classification(ROOT)
    finding = classification.worker_projection
    assert finding.worker_1_projection_count == 18
    assert finding.worker_2_projection_count == 36
    assert finding.worker_1_conditions == ("C",)
    assert finding.worker_2_conditions == ("A", "B")
    assert finding.causal_worker_effect_interpretable is False
    assert classification.repetition_freeze_decision == ("BLOCK_REPETITION_FREEZE_AND_REDESIGN")


def test_redesign_boundary_cannot_authorize_execution() -> None:
    policy = subject._load_policy(ROOT)
    classification = subject.build_classification(ROOT)
    boundary = subject.build_redesign_boundary(classification, policy)
    assert boundary.accepted_execution_evidence is True
    assert boundary.accepted_cache_salt_mechanism_evidence is True
    assert boundary.task_output_contract_satisfied is False
    assert boundary.worker_symmetry_established is False
    assert boundary.repetition_freeze_permitted is False
    assert boundary.final_measured_abc_execution_authorized is False
    assert boundary.new_execution_authorized is False
    assert len(boundary.redesign_requirements) == 5


def test_generated_outputs_validate() -> None:
    result = subject.validate(ROOT)
    assert result["status"] == ("VARIANCE_PILOT_344611040_CLASSIFICATION_V1_VALID")
    assert result["governed_execution_evidence_accepted"] is True
    assert result["repetition_freeze_permitted"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["new_execution_authorized"] is False
