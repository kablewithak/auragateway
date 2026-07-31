"""Tests for P3-P6 runtime diagnostic failure acceptance V1."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import p3_p6_runtime_diagnostic_failure_acceptance_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def _fixture_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    for relative in (
        subject.AUTHORIZATION_EVIDENCE_PATH,
        subject.CONSUMPTION_EVIDENCE_PATH,
        subject.SUMMARY_EVIDENCE_PATH,
        subject.FAILURE_EVIDENCE_PATH,
        subject.REFERENCE_EVIDENCE_PATH,
        subject.LIMITATIONS_EVIDENCE_PATH,
    ):
        source = ROOT / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def test_generate_validate_round_trip() -> None:
    record = subject.validate(ROOT)

    assert record.status == ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_VALID")
    assert record.saved_version_id == 339375227
    assert record.authorization_lifecycle_closed is True
    assert record.root_cause_resolved is False


def test_review_classifies_exact_install_boundary() -> None:
    review = subject.build_review(ROOT)

    assert review.failure_code == "P3_P6_RUNTIME_INSTALL_FAILED"
    assert review.failure_boundary == "OFFLINE_TARGET_RUNTIME_INSTALLATION"
    assert review.root_cause_classification == "UNRESOLVED_PIP_SUBPROCESS_FAILURE"
    assert review.completed_probes == ()
    assert review.counters.runtime_install_attempts == 1
    assert review.counters.model_loads == 0
    assert review.counters.worker_starts == 0
    assert review.counters.model_requests == 0


def test_authorization_lifecycle_is_closed_and_not_reusable() -> None:
    review = subject.build_review(ROOT)

    assert review.authorization_lifecycle_closed is True
    assert review.authorization_reusable is False
    assert review.unchanged_replay_authorized is False
    assert review.runtime_execution_authorized is False


def test_failure_acceptance_does_not_overclaim_root_cause() -> None:
    review = subject.build_review(ROOT)

    assert review.evidence_sufficiency == (
        "SUFFICIENT_FOR_BOUNDARY_CLASSIFICATION_INSUFFICIENT_FOR_ROOT_CAUSE"
    )
    assert any("stdout" in item for item in review.limitations)
    assert any("stderr" in item for item in review.limitations)
    assert any("No dependency root cause" in item for item in review.non_claims)


def test_consumption_binds_exact_authorization_bytes() -> None:
    authorization = (ROOT / subject.AUTHORIZATION_EVIDENCE_PATH).read_bytes()
    consumption = subject.ConsumptionEvidence.model_validate_json(
        (ROOT / subject.CONSUMPTION_EVIDENCE_PATH).read_bytes()
    )

    assert hashlib.sha256(authorization).hexdigest() == (consumption.authorization_sha256)
    assert consumption.saved_version_id == 339375227
    assert consumption.outcome == "FAILED"


def test_summary_evidence_tamper_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.SUMMARY_EVIDENCE_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.FailureAcceptanceError,
        match="identity drifted",
    ):
        subject.build_review(repo_root)


def test_all_evidence_receipts_match_repository_bytes() -> None:
    review = subject.build_review(ROOT)

    observed = {
        item.repository_path: hashlib.sha256((ROOT / item.repository_path).read_bytes()).hexdigest()
        for item in review.evidence
    }
    expected = {item.repository_path: item.sha256 for item in review.evidence}

    assert observed == expected


def test_next_gate_requires_diagnostic_v2_before_new_execution() -> None:
    record = subject.validate(ROOT)

    assert record.next_gate == ("design_and_merge_p3_p6_runtime_install_diagnostics_v2")
    assert record.runtime_execution_authorized is False
    assert record.unchanged_replay_authorized is False
