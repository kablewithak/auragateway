"""Tests for Exact-Runtime P5/P6 V2 outcome-unknown governance V1."""

from pathlib import Path

import pytest

from auragateway.local_abc import (
    p5_p6_exact_runtime_v2_outcome_unknown_governance_v1 as governance,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_current_repository_governance_validates() -> None:
    result = governance.validate_governance(_repo_root())

    assert result["status"] == ("EXACT_RUNTIME_P5_P6_V2_OUTCOME_UNKNOWN_GOVERNANCE_VALID")
    assert result["saved_version_id"] == 341548056
    assert result["governed_execution_outcome"] == "OUTCOME_UNKNOWN"
    assert result["diagnostic_masking_established"] is True
    assert result["runtime_incompatibility_established"] is False
    assert result["authorization_reusable"] is False


def test_terminal_receipt_preserves_outcome_unknown() -> None:
    root = _repo_root()
    receipt = governance._load_json(root / governance.VAULT_RECEIPT_PATH)

    assert receipt["disposition"] == "OUTCOME_UNKNOWN"
    assert receipt["execution_attempted"] is True
    assert receipt["execution_outcome"] is None
    assert receipt["saved_version_id"] == 341548056
    assert receipt["evidence_zip_sha256"] is None
    assert receipt["authorization_reusable"] is False


def test_partial_results_exclude_governed_terminal_bundle() -> None:
    root = _repo_root()

    governance._validate_partial_results(root / governance.PARTIAL_RESULTS_PATH)


def test_terminal_log_preserves_cleanup_snapshot_failure() -> None:
    root = _repo_root()

    governance._validate_log(root / governance.TERMINAL_LOG_PATH)


def test_terminal_authorization_reuse_is_rejected() -> None:
    with pytest.raises(governance.GovernanceError) as caught:
        governance.reject_authorization_reuse(governance.AUTHORIZATION_SHA256)

    assert caught.value.code == ("P5_P6_V2_OUTCOME_UNKNOWN_AUTHORIZATION_TERMINAL")


def test_wrong_authorization_identity_is_not_treated_as_consumed() -> None:
    with pytest.raises(governance.GovernanceError) as caught:
        governance.reject_authorization_reuse("0" * 64)

    assert caught.value.code == ("P5_P6_V2_OUTCOME_UNKNOWN_AUTHORIZATION_IDENTITY_UNKNOWN")
