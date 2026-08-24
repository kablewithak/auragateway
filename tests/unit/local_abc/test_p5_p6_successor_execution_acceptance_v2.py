from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p5_p6_successor_execution_acceptance_v2 as acceptance,
)

ROOT = Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_policy_is_hash_locked_and_current_runtime_bound() -> None:
    policy_path = ROOT / acceptance.POLICY_PATH
    assert sha256_file(policy_path) == acceptance.POLICY_SHA256
    policy = acceptance.AcceptancePolicy.model_validate_json(
        policy_path.read_text(encoding="utf-8")
    )
    assert policy.saved_version_id == 344464549
    assert policy.transaction_id == acceptance.TRANSACTION_ID
    assert policy.lifecycle_outcome == "PASSED"
    assert policy.current_line_p5_pass_accepted is True
    assert policy.current_line_p6_pass_accepted is True
    assert policy.p5_requalified is True
    assert policy.p6_requalified is True
    assert policy.c4_mechanism_qualified is True
    assert policy.c4_semantic_qualified is False
    assert policy.c4_semantic_state == "INVALID_JSON"
    assert policy.variance_pilot_p5_p6_prerequisite_satisfied is True
    assert policy.variance_pilot_authority_reconciliation_required is True
    assert policy.variance_pilot_execution_authorized is False
    assert policy.final_measured_abc_execution_authorized is False


def test_preserved_lifecycle_and_runtime_evidence_are_exact() -> None:
    hashes = acceptance._load_policy(ROOT).expected_hashes
    authorization = ROOT / acceptance.EVIDENCE_DIR / "lifecycle" / acceptance.AUTHORIZATION_NAME
    terminal = ROOT / acceptance.EVIDENCE_DIR / "lifecycle" / acceptance.TERMINAL_AUTHORIZATION_NAME
    preservation = ROOT / acceptance.EVIDENCE_DIR / acceptance.PRESERVATION_MANIFEST_NAME
    evidence_zip = ROOT / acceptance.EVIDENCE_DIR / "kaggle" / acceptance.EVIDENCE_ZIP_NAME
    terminal_log = ROOT / acceptance.EVIDENCE_DIR / "kaggle" / acceptance.TERMINAL_LOG_NAME
    assert sha256_file(authorization) == hashes.authorization_live_file
    assert sha256_file(terminal) == hashes.authorization_terminal
    assert sha256_file(preservation) == hashes.preservation_manifest
    assert sha256_file(evidence_zip) == hashes.evidence_zip
    assert sha256_file(terminal_log) == hashes.terminal_log


def test_preservation_manifest_with_utf8_bom_is_read_without_byte_mutation() -> None:
    path = ROOT / acceptance.EVIDENCE_DIR / acceptance.PRESERVATION_MANIFEST_NAME
    before = path.read_bytes()
    payload = acceptance._read_json(path)
    assert isinstance(payload, dict)
    assert payload["status"] == "IMMUTABLE_EVIDENCE_INTAKE_COMPLETE"
    assert path.read_bytes() == before


def test_lifecycle_is_consumed_pass_and_preacceptance() -> None:
    policy = acceptance._load_policy(ROOT)
    acceptance._validate_lifecycle(ROOT, policy)
    terminal_path = (
        ROOT / acceptance.EVIDENCE_DIR / "lifecycle" / acceptance.TERMINAL_AUTHORIZATION_NAME
    )
    terminal = acceptance.TerminalEvidence.model_validate(acceptance._read_json(terminal_path))
    assert terminal.p5_requalified is False
    assert terminal.p6_requalified is False
    assert terminal.repository_acceptance_established is False


def test_preservation_manifest_binds_all_preserved_evidence() -> None:
    policy = acceptance._load_policy(ROOT)
    acceptance._validate_preservation_manifest(ROOT, policy)


def test_runtime_evidence_semantics_pass() -> None:
    policy = acceptance._load_policy(ROOT)
    acceptance._validate_runtime_evidence(ROOT, policy)


def test_review_and_record_are_deterministic() -> None:
    review_a = acceptance.build_review(ROOT)
    review_b = acceptance.build_review(ROOT)
    assert review_a == review_b
    record_a = acceptance.build_record(ROOT, review_a)
    record_b = acceptance.build_record(ROOT, review_b)
    assert record_a == record_b
    assert (
        record_a.review_sha256
        == hashlib.sha256(
            acceptance._canonical(review_a.model_dump(mode="json")).encode("utf-8")
        ).hexdigest()
    )


def test_validate_implementation_accepts_frozen_candidate() -> None:
    result = acceptance.validate_implementation(ROOT)
    assert result["status"] == "P5_P6_SUCCESSOR_EXECUTION_ACCEPTANCE_V2_VALID"
    assert result["p5_requalified"] is True
    assert result["p6_requalified"] is True
    assert result["c4_mechanism_qualified"] is True
    assert result["c4_semantic_qualified"] is False
    assert result["c4_semantic_state"] == "INVALID_JSON"
    assert result["variance_pilot_p5_p6_prerequisite_satisfied"] is True
    assert result["variance_pilot_execution_authorized"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["runtime_execution_authorized"] is False


def test_archive_normalizer_rejects_parent_escape() -> None:
    with pytest.raises(acceptance.AcceptanceError):
        acceptance._normalize_zip_name("../escape.json")


def test_record_preserves_variance_pilot_and_final_execution_boundary() -> None:
    payload = json.loads((ROOT / acceptance.RECORD_PATH).read_text(encoding="utf-8"))
    assert payload["p5_requalified"] is True
    assert payload["p6_requalified"] is True
    assert payload["c4_mechanism_qualified"] is True
    assert payload["c4_semantic_qualified"] is False
    assert payload["variance_pilot_authority_reconciliation_required"] is True
    assert payload["variance_pilot_runtime_launcher_readiness_committed"] is False
    assert payload["variance_pilot_execution_authorized"] is False
    assert payload["final_measured_abc_execution_authorized"] is False
    assert payload["runtime_execution_authorized"] is False
    assert payload["authorization_reusable"] is False
    assert payload["new_execution_authorized"] is False
