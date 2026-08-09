from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import final_offline_verifier_v5_evidence_acceptance_v1 as subject


def _policy_payload() -> dict[str, object]:
    payload = json.loads(Path(subject.POLICY_PATH).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


def test_policy_hash_is_bound() -> None:
    payload = Path(subject.POLICY_PATH).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == subject.POLICY_SHA256


def test_policy_requires_25_roles() -> None:
    policy = subject.AcceptancePolicy.model_validate(_policy_payload())
    assert len(policy.required_roles) == 25
    assert len(set(policy.required_roles)) == 25


def test_policy_promotes_only_capability_claim() -> None:
    policy = subject.AcceptancePolicy.model_validate(_policy_payload())
    assert policy.accepted_claims.exact_runtime_offline_verified is True
    assert policy.accepted_claims.qualification_scope == "CAPABILITY_ONLY"
    assert policy.next_gate == "design_exact_runtime_p5_p6_requalification_v1"


def test_review_keeps_downstream_authority_false() -> None:
    review = subject.AcceptanceReview(
        review_id=("auragateway-final-offline-verifier-v5-evidence-acceptance-v1-review"),
        saved_version_id=341257985,
        technical_status="PASSED",
        execution_outcome="PASSED",
        evidence_status="VALIDATED",
        governed_acceptance_status=("ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"),
        qualification_scope="CAPABILITY_ONLY",
        exact_runtime_offline_verified=True,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        evidence_receipts=(),
        next_gate="design_exact_runtime_p5_p6_requalification_v1",
        non_claims=("no downstream execution authority",),
    )
    assert review.exact_runtime_offline_verified is True
    assert review.p5_p6_exact_runtime_requalified is False
    assert review.runtime_execution_authorized is False
    assert review.pilot_execution_authorized is False
    assert review.final_measured_abc_execution_authorized is False


def test_safe_zip_rejects_parent_escape(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.json", b"{}")
    with pytest.raises(subject.AcceptanceError) as captured:
        subject._safe_zip_members(archive_path)
    assert captured.value.error_code == ("FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARCHIVE_UNSAFE")


def test_safe_zip_rejects_duplicate_normalized_member(tmp_path: Path) -> None:
    archive_path = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("a\\b.json", b"{}")
        archive.writestr("a/b.json", b"{}")
    with pytest.raises(subject.AcceptanceError) as captured:
        subject._safe_zip_members(archive_path)
    assert captured.value.error_code == ("FINAL_OFFLINE_VERIFIER_V5_ACCEPTANCE_ARCHIVE_DUPLICATE")


def test_consumption_schema_rejects_failed_outcome() -> None:
    payload = {
        "schema_version": "1.0.0",
        "authorization_id": "x",
        "authorization_sha256": "a" * 64,
        "lifecycle": "CONSUMED",
        "outcome": "FAILED",
        "consumed_at": "2026-08-09T15:10:00Z",
        "saved_version_id": 341257985,
        "evidence_zip_sha256": "b" * 64,
        "authorization_reusable": False,
        "offline_verifier_v5_execution_authorized": False,
        "model_execution_authorized": False,
        "p5_p6_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": ("preserve_and_accept_or_classify_final_offline_verifier_v5_evidence"),
    }
    with pytest.raises(ValidationError):
        subject.ConsumptionEvidence.model_validate(payload)
