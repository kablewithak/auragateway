from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_345461230_classification_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def test_policy_identity_is_frozen() -> None:
    path = ROOT / subject.POLICY_PATH
    assert subject._sha256_file(path) == subject.POLICY_SHA256
    policy = subject._load_policy(ROOT)
    assert policy.saved_version_id == 345461230
    assert policy.transaction_id == (
        "4341cafac81245d433a680db0bc9c62ecabdbf1d279c0ddc0a19741eb44c7d8b"
    )
    assert len(policy.expected_hashes) == 7
    assert len(policy.expected_zip_members) == 32


def test_governed_execution_pass_is_repository_classified() -> None:
    classification = subject.build_classification(ROOT)
    finding = classification.execution
    assert finding.governed_execution_disposition == "ACCEPTED_GOVERNED_EXECUTION_PASS"
    assert finding.scheduled_request_count == 240
    assert finding.attempted_request_count == 240
    assert finding.http_completed_request_count == 240
    assert finding.admitted_request_count == 240
    assert finding.committed_request_count == 240
    assert finding.hidden_retry_count == 0
    assert finding.replacement_case_count == 0
    assert finding.output_admission_failure_count == 0
    assert finding.primary_runtime_failure is False
    assert finding.worker_teardown_passed is True
    assert finding.scratch_cleanup_passed is True


def test_v2_task_output_contract_passes_without_hidden_retries() -> None:
    classification = subject.build_classification(ROOT)
    task = classification.task_output
    assert task.scheduled_trajectory_count == 54
    assert task.observed_trajectory_count == 54
    assert task.failed_trajectory_count == 0
    assert task.scheduled_turn_count == 216
    assert task.completed_turn_count == 216
    assert task.finish_reason_stop_count == 216
    assert task.admitted_turn_count == 216
    assert task.committed_turn_count == 216
    assert task.task_output_contract == "PASSED"


def test_neutral_worker_control_and_counterbalancing_are_qualified() -> None:
    classification = subject.build_classification(ROOT)
    finding = classification.worker_nuisance
    assert finding.decision == "PASS"
    assert finding.observed_sample_count == 20
    assert finding.worker_1_sample_count == 10
    assert finding.worker_2_sample_count == 10
    assert finding.worker_median_ttft_ratio <= 1.25
    assert finding.worker_median_prefill_ratio <= 1.25
    assert finding.global_orientation_1_pair_count == 9
    assert finding.global_orientation_2_pair_count == 9
    assert finding.each_replication_orientation_1_pair_count == 3
    assert finding.each_replication_orientation_2_pair_count == 3
    assert finding.each_case_observed_under_both_orientations is True
    assert finding.worker_nuisance_control == "QUALIFIED"
    assert finding.estimator_and_nuisance_controls_interpretable is True


def test_affinity_pilot_signal_is_preserved_without_effect_claim() -> None:
    classification = subject.build_classification(ROOT)
    finding = classification.affinity_pilot
    assert finding.matched_pair_count == 18
    assert finding.output_hash_comparison_count == 72
    assert finding.output_hash_match_count == 72
    assert finding.newly_computed_prefill_favorable_pair_count == 18
    assert finding.prefill_duration_favorable_pair_count == 18
    assert finding.ttft_favorable_pair_count == 18
    assert finding.end_to_end_favorable_pair_count == 18
    assert finding.mean_newly_computed_prefill_delta_c_minus_b < 0
    assert finding.mean_prefill_duration_ms_delta_c_minus_b < 0
    assert finding.mean_ttft_ms_delta_c_minus_b < 0
    assert finding.mean_end_to_end_latency_ms_delta_c_minus_b < 0
    assert finding.pilot_directional_signal_observed is True
    assert finding.final_affinity_effect_established is False
    assert classification.effect_claims_permitted is False
    assert classification.affinity_effect_established is False


def test_papermill_metadata_anomaly_does_not_override_runtime_evidence() -> None:
    classification = subject.build_classification(ROOT)
    finding = classification.notebook
    assert finding.papermill_exception_metadata_observed is True
    assert finding.runtime_execution_outcome == "PASSED"
    assert finding.papermill_metadata_promoted_to_runtime_failure is False


def test_g9_acceptance_opens_only_g10_design_boundary() -> None:
    classification = subject.build_classification(ROOT)
    boundary = subject.build_acceptance_boundary(classification)
    assert classification.pilot_acceptance_decision == "ACCEPT"
    assert classification.pilot_repository_acceptance_established is True
    assert classification.repetition_freeze_permitted is True
    assert classification.repetition_freeze_established is False
    assert boundary.governed_execution_evidence_accepted is True
    assert boundary.task_output_contract_satisfied is True
    assert boundary.worker_nuisance_control_qualified is True
    assert boundary.estimator_and_nuisance_controls_interpretable is True
    assert boundary.pilot_repository_acceptance_established is True
    assert boundary.repetition_freeze_permitted is True
    assert boundary.repetition_freeze_established is False
    assert boundary.final_measured_abc_execution_authorized is False
    assert boundary.new_execution_authorized is False
    assert boundary.effect_claims_permitted is False


def test_pilot_acceptance_does_not_promote_final_claims() -> None:
    classification = subject.build_classification(ROOT)
    assert classification.final_measured_abc_execution_authorized is False
    assert classification.new_execution_authorized is False
    assert classification.effect_claims_permitted is False
    assert classification.prefix_effect_established is False
    assert classification.affinity_effect_established is False
    assert classification.combined_effect_established is False
    assert classification.quality_noninferiority_established is False
    assert classification.production_readiness_established is False


def test_member_identity_drift_fails_closed(tmp_path: Path) -> None:
    policy = subject._load_policy(ROOT)
    source = ROOT / policy.vault_path / ("raw_kaggle/ag-variance-pilot-v2-tx-v1-evidence.zip")
    target = tmp_path / "mutated.zip"
    with zipfile.ZipFile(source) as observed, zipfile.ZipFile(target, "w") as mutated:
        for info in observed.infolist():
            payload = observed.read(info)
            if info.filename == "runtime_summary_v1.json":
                payload += b" "
            mutated.writestr(info.filename, payload)
    with pytest.raises(subject.ClassificationError) as captured:
        subject._read_evidence_zip(target, policy)
    assert captured.value.error_code == "V2_PILOT_CLASSIFICATION_ZIP_MEMBER_DRIFT"


def test_generated_outputs_validate() -> None:
    result = subject.validate(ROOT)
    assert result["status"] == "VARIANCE_PILOT_V2_345461230_CLASSIFICATION_V1_VALID"
    assert result["governed_execution_evidence_accepted"] is True
    assert result["pilot_repository_acceptance_established"] is True
    assert result["repetition_freeze_permitted"] is True
    assert result["repetition_freeze_established"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["new_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
