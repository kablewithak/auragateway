"""Focused tests for final-342 execution-manifest post-commit custody."""

from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    final_342_execution_manifest_post_commit_custody_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def _receipt() -> subject.Final342ManifestCustodyReceipt:
    return subject.Final342ManifestCustodyReceipt.model_validate_json(
        (ROOT / subject.RECEIPT_PATH).read_bytes()
    )


def test_receipt_binds_exact_manifest_identities() -> None:
    receipt = _receipt()

    assert receipt.manifest_identity.manifest_semantic_sha256 == (
        subject.EXPECTED_MANIFEST_SEMANTIC_SHA256
    )
    assert receipt.manifest_identity.manifest_file_sha256 == (subject.EXPECTED_MANIFEST_FILE_SHA256)
    assert receipt.manifest_identity.manifest_git_blob_sha == (
        subject.EXPECTED_MANIFEST_GIT_BLOB_SHA
    )


def test_receipt_binds_acyclic_source_and_first_containing_commits() -> None:
    receipt = _receipt()

    assert receipt.commit_custody.source_subject_commit == (
        "fcf403a1c31e26a2cdf3f682a8878db01338a13d"
    )
    assert receipt.commit_custody.first_containing_commit == (
        "078c1da32fe7c1ee8ff5a8661e5f38e588782abc"
    )
    assert receipt.commit_custody.source_subject_manifest_absent is True
    assert receipt.commit_custody.first_containing_parent_is_source_subject is True
    assert receipt.commit_custody.first_containing_commit_contains_exact_manifest_bytes is True


def test_receipt_promotes_repository_freeze_but_not_execution_authority() -> None:
    receipt = _receipt()

    assert receipt.freeze_promotion.manifest_subject_bytes_frozen is True
    assert receipt.freeze_promotion.post_commit_custody_complete is True
    assert receipt.freeze_promotion.repository_execution_manifest_frozen is True
    assert receipt.freeze_promotion.repository_freeze_gate_promoted is True
    assert receipt.freeze_promotion.execution_manifest_itself_is_execution_authority is False
    assert receipt.safety_state.final_measured_abc_execution_authorized is False
    assert receipt.safety_state.new_execution_authorized is False
    assert receipt.safety_state.live_authorization_issued is False


def test_receipt_requires_history_preserving_merge_strategy() -> None:
    receipt = _receipt()

    assert receipt.commit_custody.merge_commit_preserving_feature_commits_required is True
    assert receipt.commit_custody.squash_merge_permitted is False
    assert receipt.commit_custody.rebase_merge_permitted is False


def test_repository_validator_reconstructs_same_receipt() -> None:
    summary = subject.validate(ROOT)

    assert summary["post_commit_custody_complete"] is True
    assert summary["repository_execution_manifest_frozen"] is True
    assert summary["repository_freeze_gate_promoted"] is True
    assert summary["final_measured_abc_execution_authorized"] is False
    assert summary["next_gate"] == "BIND_FINAL_342_STATIC_EXECUTION_AUTHORITY_V1"
