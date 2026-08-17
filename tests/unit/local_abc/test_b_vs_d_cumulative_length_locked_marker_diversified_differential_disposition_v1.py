from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    b_vs_d_cumulative_length_locked_marker_diversified_differential_disposition_v1,
)

disposition = b_vs_d_cumulative_length_locked_marker_diversified_differential_disposition_v1

REPO_ROOT = Path(__file__).resolve().parents[3]

REQUIRED_INPUTS = (
    disposition.CUSTODY_MANIFEST_PATH,
    disposition.AUTHORIZATION_PATH,
    disposition.EXECUTION_MANIFEST_PATH,
    disposition.PLATFORM_RECEIPT_PATH,
    disposition.TERMINAL_RECEIPT_PATH,
    disposition.EVIDENCE_ZIP_PATH,
    disposition.OUTER_RESULTS_ZIP_PATH,
    disposition.TERMINAL_LOG_PATH,
    disposition.NOTEBOOK_PATH,
    disposition.RUNTIME_PATH,
    disposition.IMPLEMENTATION_RECORD_PATH,
    disposition.IMPLEMENTATION_REVIEW_PATH,
    disposition.AUTHORIZATION_DESIGN_RECORD_PATH,
    disposition.ISSUER_SOURCE_PATH,
    disposition.GENERATOR_CONTRACT_PATH,
)


def _copy_inputs(destination: Path) -> Path:
    for relative in REQUIRED_INPUTS:
        source = REPO_ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return destination


def test_repository_disposition_validates() -> None:
    record, review = disposition.validate(REPO_ROOT)

    assert record.decision_state == disposition.DECISION_STATE
    assert record.condition_b_exact_object_count == 0
    assert record.condition_d_exact_object_count == 3
    assert record.wrapper_reporting_defect_observed is True
    assert record.new_execution_authorized is False
    assert review.marker_diversification_result_accepted is True


def test_generated_record_and_review_are_deterministic(tmp_path: Path) -> None:
    root = _copy_inputs(tmp_path)

    first_record, first_review = disposition.generate(root)
    second_record, second_review = disposition.generate(root)

    assert first_record == second_record
    assert first_review == second_review
    assert disposition.validate(root)


def test_evidence_zip_byte_drift_fails_closed(tmp_path: Path) -> None:
    root = _copy_inputs(tmp_path)
    evidence_path = root / disposition.EVIDENCE_ZIP_PATH
    evidence_path.write_bytes(evidence_path.read_bytes() + b"x")

    with pytest.raises(
        disposition.DispositionError,
        match="byte identity drifted",
    ):
        disposition.build_record(root)


def test_custody_manifest_rejects_reusable_authorization() -> None:
    payload = json.loads(
        (REPO_ROOT / disposition.CUSTODY_MANIFEST_PATH).read_text(encoding="utf-8")
    )
    payload["authorization_reusable"] = True

    with pytest.raises(ValidationError):
        disposition.CustodyManifest.model_validate(payload)


def test_custody_manifest_has_exact_eight_members() -> None:
    manifest = disposition.validate_custody(REPO_ROOT)

    assert manifest.member_count == 8
    assert len(manifest.members) == 8
    assert {item.role for item in manifest.members} == {
        "execution_authorization",
        "execution_artifact_manifest",
        "platform_observation_receipt",
        "authorization_terminal_receipt",
        "governed_evidence_zip",
        "outer_kaggle_results_zip",
        "terminal_log",
        "saved_notebook",
    }


def test_outer_results_preserve_control_plane_false_positive() -> None:
    disposition.validate_outer_results(REPO_ROOT)
    disposition.validate_notebook_reporting_defect(REPO_ROOT)


def test_lifecycle_is_terminal_and_non_reusable() -> None:
    disposition.validate_lifecycle(REPO_ROOT)
    terminal = json.loads(
        (REPO_ROOT / disposition.TERMINAL_RECEIPT_PATH).read_text(encoding="utf-8")
    )

    assert terminal["disposition"] == "CONSUMED"
    assert terminal["execution_outcome"] == "PASSED"
    assert terminal["authorization_reusable"] is False
    assert terminal["runtime_execution_authorized"] is False


def test_disposition_authority_boundary_is_exact() -> None:
    record = disposition.build_record(REPO_ROOT)

    assert len(record.authorities) == 15
    assert record.authorization_reusable is False
    assert record.unchanged_replay_authorized is False


def test_wrapper_defect_does_not_promote_scientific_claims() -> None:
    record = disposition.build_record(REPO_ROOT)

    assert record.scientific_result_invalidated_by_wrapper_reporting_defect is False
    assert record.exact_repetition_sole_or_root_cause_established is False
    assert record.exact_ngram_and_periodicity_effects_individually_isolated is False
    assert record.exact_repetition_threshold_established is False
    assert record.prefix_cache_defect_established is False
    assert record.p5_requalified is False
    assert record.p6_requalified is False
    assert record.measured_abc_execution_performed is False


def test_next_gate_requires_wrapper_repair_before_new_execution() -> None:
    record = disposition.build_record(REPO_ROOT)

    assert record.next_gate == (
        "REPAIR_TRANSACTION_BOUND_WRAPPER_ZERO_EXIT_REPORTING_BEFORE_NEW_EXECUTION_V1"
    )
    assert record.new_execution_authorized is False
