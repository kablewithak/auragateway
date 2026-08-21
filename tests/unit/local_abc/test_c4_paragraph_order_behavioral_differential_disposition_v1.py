from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    c4_paragraph_order_behavioral_differential_disposition_v1,
)

disposition = c4_paragraph_order_behavioral_differential_disposition_v1

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
    assert record.control_anchor_reproduced is True
    assert record.control_exact_object_count == 0
    assert record.treatment_exact_object_count == 0
    assert record.control_valid_json_count == 3
    assert record.treatment_valid_json_count == 3
    assert record.same_deterministic_failure_phenotype_observed is True
    assert record.new_execution_authorized is False
    assert review.same_failure_phenotype_accepted is True


def test_generated_record_and_review_are_deterministic(tmp_path: Path) -> None:
    root = _copy_inputs(tmp_path)

    first_record, first_review = disposition.generate(root)
    first_record_bytes = (root / disposition.RECORD_PATH).read_bytes()
    first_review_bytes = (root / disposition.REVIEW_PATH).read_bytes()

    second_record, second_review = disposition.generate(root)

    assert first_record == second_record
    assert first_review == second_review
    assert (root / disposition.RECORD_PATH).read_bytes() == first_record_bytes
    assert (root / disposition.REVIEW_PATH).read_bytes() == first_review_bytes
    assert disposition.validate(root)


def test_evidence_zip_byte_drift_fails_closed(tmp_path: Path) -> None:
    root = _copy_inputs(tmp_path)
    evidence_path = root / disposition.EVIDENCE_ZIP_PATH
    evidence_path.write_bytes(evidence_path.read_bytes() + b"x")

    with pytest.raises(
        disposition.DispositionError,
        match="expected",
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


def test_governed_evidence_reconciles_frozen_decision() -> None:
    disposition.validate_evidence_bundle(REPO_ROOT)
    record = disposition.build_record(REPO_ROOT)

    assert record.control_historical_parsed_identity_matched is True
    assert record.treatment_parsed_identity_matches_historical_control is True
    assert record.same_deterministic_failure_phenotype_observed is True
    assert record.static_token_multiset_premise_reexecuted is False


def test_outer_results_and_notebook_have_no_wrapper_false_positive() -> None:
    disposition.validate_outer_results(REPO_ROOT)
    disposition.validate_notebook(REPO_ROOT)

    record = disposition.build_record(REPO_ROOT)
    assert record.wrapper_reporting_defect_observed is False


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
    assert record.new_execution_authorized is False


def test_no_change_result_does_not_promote_c4_or_downstream_claims() -> None:
    record = disposition.build_record(REPO_ROOT)

    assert record.paragraph_order_root_cause_established is False
    assert record.c4_qualification_accepted_by_repository is False
    assert record.paragraph_order_repository_state_advanced is False
    assert record.p5_requalified is False
    assert record.p6_requalified is False
    assert record.final_abc_measured is False
    assert record.production_readiness_established is False


def test_next_gate_is_analysis_before_new_execution() -> None:
    record = disposition.build_record(REPO_ROOT)

    assert record.next_gate == ("ANALYZE_C4_PARAGRAPH_ORDER_NO_CHANGE_BEFORE_NEW_EXECUTION_V1")
    assert record.new_execution_authorized is False
