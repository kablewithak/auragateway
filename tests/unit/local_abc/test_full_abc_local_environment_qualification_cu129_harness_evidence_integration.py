"""Regression tests for current CUDA 12.9 harness evidence integration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_harness_evidence_integration as integration,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_contracts as auth_contracts,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_contracts as execution_contracts,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_kaggle_launcher as launcher,
)

ROOT = Path(__file__).resolve().parents[3]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def test_repository_package_integrates_current_harness_evidence() -> None:
    summary = integration.validate_repository_package(ROOT)

    assert summary["status"] == "CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED"
    assert summary["operational_input_closure"] == "PASSED"
    assert summary["source_commit"] == integration.SOURCE_COMMIT
    assert summary["harness_directory_sha256"] == (integration.CURRENT_HARNESS_DIRECTORY_SHA256)
    assert summary["harness_file_count"] == 1299
    assert summary["harness_total_bytes"] == 11_632_357
    assert summary["runtime_package_count"] == 176
    assert summary["manifest_sha256"] == integration.CURRENT_MANIFEST_SHA256
    assert summary["materialization_record_sha256"] == (
        integration.CURRENT_MATERIALIZATION_RECORD_SHA256
    )
    assert summary["launcher_notebook_sha256"] == integration.CURRENT_LAUNCHER_NOTEBOOK_SHA256
    assert summary["inspection_evidence_zip_sha256"] == (integration.INSPECTION_EVIDENCE_ZIP_SHA256)
    assert summary["materializer_saved_version_id"] == 337034643
    assert summary["inspection_saved_version_id"] == 337035826
    assert summary["authorization_source_binding_policy"] == (
        "CONTROL_PACKAGE_AUTHORIZATION_PARITY"
    )
    assert summary["authorization_issued"] is False
    assert summary["gpu_execution_performed"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["measured_execution_authorized"] is False
    assert summary["next_gate"] == "fresh_cu129_authorization_issuance_implementation"


def test_evidence_identity_binds_exact_saved_versions_and_artifacts() -> None:
    identity = integration.EvidenceIdentity.model_validate(
        _load_json(ROOT / integration.EVIDENCE_IDENTITY_PATH)
    )

    assert identity.source_commit == integration.SOURCE_COMMIT
    assert identity.materializer_saved_version_id == 337034643
    assert identity.inspection_saved_version_id == 337035826
    assert identity.inspection_saved_version_url == integration.INSPECTION_SAVED_VERSION_URL
    assert identity.materializer_recovery_notebook_sha256 == (
        integration.MATERIALIZER_RECOVERY_NOTEBOOK_SHA256
    )
    assert identity.materialization_receipt_sha256 == (integration.MATERIALIZATION_RECEIPT_SHA256)
    assert identity.inspection_evidence_zip_sha256 == (integration.INSPECTION_EVIDENCE_ZIP_SHA256)
    assert tuple(item.name for item in identity.inspection_evidence_members) == (
        integration.EXPECTED_ZIP_MEMBERS
    )


def test_materialization_receipt_records_kaggle_recovery_without_runtime_activity() -> None:
    receipt = integration.MaterializationReceipt.model_validate(
        _load_json(ROOT / integration.MATERIALIZATION_RECEIPT_PATH)
    )

    assert receipt.source_commit == integration.SOURCE_COMMIT
    assert receipt.input_mode == "kaggle_expanded_source_recovered_to_exact_archive"
    assert receipt.kaggle_auto_expanded_source_detected is True
    assert receipt.exact_archive_reconstructed is True
    assert receipt.directory_sha256 == integration.CURRENT_HARNESS_DIRECTORY_SHA256
    assert receipt.file_count == 1299
    assert receipt.total_bytes == 11_632_357
    assert receipt.gpu_execution_performed is False
    assert receipt.package_installation_performed is False
    assert receipt.model_loaded is False
    assert receipt.worker_started is False
    assert receipt.model_requests_performed == 0
    assert receipt.authorization_issued is False


def test_active_manifest_and_materialization_record_bind_current_harness() -> None:
    manifest = execution_contracts.QualificationDatasetManifest.model_validate(
        _load_json(ROOT / integration.MANIFEST_PATH)
    )
    materialization = auth_contracts.MaterializedOfflineDatasetRecord.model_validate(
        _load_json(ROOT / integration.MATERIALIZATION_RECORD_PATH)
    )

    harness_manifest = manifest.entries[0]
    harness_record = materialization.entries[0]

    assert harness_manifest.mounted_path == integration.CURRENT_HARNESS_MOUNTED_PATH
    assert harness_manifest.sha256 == integration.CURRENT_HARNESS_DIRECTORY_SHA256
    assert harness_record.kaggle_dataset_slug == integration.CURRENT_HARNESS_KAGGLE_SLUG
    assert harness_record.kaggle_dataset_version == 1
    assert harness_record.mounted_path == integration.CURRENT_HARNESS_MOUNTED_PATH
    assert harness_record.sha256 == integration.CURRENT_HARNESS_DIRECTORY_SHA256
    assert materialization.harness_source_commit == integration.SOURCE_COMMIT
    assert materialization.runtime_manifest_sha256 == manifest.fingerprint()


def test_launcher_binds_current_harness_and_dynamic_authorization_source() -> None:
    assert launcher.SOURCE_MAIN_MERGE_COMMIT == integration.SOURCE_COMMIT
    assert launcher.HARNESS_SOURCE_PATH == integration.CURRENT_HARNESS_MOUNTED_PATH
    assert launcher.AUTHORIZATION_SOURCE_BINDING_POLICY == ("CONTROL_PACKAGE_AUTHORIZATION_PARITY")

    notebook = launcher.build_launcher_notebook(ROOT)
    metadata = cast(dict[str, object], notebook["metadata"])
    auragateway = cast(dict[str, object], metadata["auragateway"])

    assert auragateway["source_main_merge_commit"] == integration.SOURCE_COMMIT
    assert auragateway["authorization_source_binding_policy"] == (
        "CONTROL_PACKAGE_AUTHORIZATION_PARITY"
    )


def test_readiness_review_keeps_fresh_authorization_unissued() -> None:
    review = integration.FreshAuthorizationReadinessReview.model_validate(
        _load_json(ROOT / integration.READINESS_REVIEW_PATH)
    )

    assert review.decision == ("APPROVED_FOR_FRESH_CU129_AUTHORIZATION_ISSUANCE_IMPLEMENTATION")
    assert review.operational_input_closure == "PASSED"
    assert review.current_manifest_sha256 == integration.CURRENT_MANIFEST_SHA256
    assert review.current_materialization_record_sha256 == (
        integration.CURRENT_MATERIALIZATION_RECORD_SHA256
    )
    assert review.current_runtime_adapter_sha256 == integration.CURRENT_RUNTIME_ADAPTER_SHA256
    assert review.current_launcher_source_sha256 == integration.CURRENT_LAUNCHER_SOURCE_SHA256
    assert review.current_launcher_notebook_sha256 == integration.CURRENT_LAUNCHER_NOTEBOOK_SHA256
    assert review.inspection_evidence_zip_sha256 == integration.INSPECTION_EVIDENCE_ZIP_SHA256
    assert review.authorization_source_binding_policy == (
        integration.AUTHORIZATION_SOURCE_BINDING_POLICY
    )
    assert review.final_authorization_present is False
    assert review.historical_authorization_issuance_implementation_usable is False
    assert review.safety.authorization_issued is False
    assert review.safety.gpu_execution_performed is False
    assert review.safety.model_requests_performed == 0
    assert review.next_gate == "fresh_cu129_authorization_issuance_implementation"
    assert not (ROOT / integration.FINAL_AUTHORIZATION_PATH).exists()


def test_readiness_review_rejects_incomplete_implementation_scope() -> None:
    payload = _load_json(ROOT / integration.READINESS_REVIEW_PATH)
    payload["required_implementation"] = ["issue authorization"] * 7

    with pytest.raises(
        ValidationError,
        match="fresh authorization implementation scope drifted",
    ):
        integration.FreshAuthorizationReadinessReview.model_validate(payload)


def test_validator_rejects_tampered_inspection_evidence_zip(tmp_path: Path) -> None:
    identity = integration.EvidenceIdentity.model_validate(
        _load_json(ROOT / integration.EVIDENCE_IDENTITY_PATH)
    )
    tampered = tmp_path / "evidence.zip"
    shutil.copy2(ROOT / integration.INSPECTION_ZIP_PATH, tampered)
    with tampered.open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(
        integration.HarnessEvidenceIntegrationError,
        match="inspection evidence ZIP identity drifted",
    ):
        integration._validate_evidence_zip(tampered, identity)


def test_validator_rejects_premature_final_authorization(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    shutil.copytree(ROOT, repository, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    target = repository / integration.FINAL_AUTHORIZATION_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(
        integration.HarnessEvidenceIntegrationError,
        match="final authorization exists before fresh issuance implementation",
    ):
        integration.validate_repository_package(repository)


def test_validator_rejects_active_materialization_record_drift(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    shutil.copytree(ROOT, repository, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    path = repository / integration.MATERIALIZATION_RECORD_PATH
    payload = _load_json(path)
    payload["harness_source_commit"] = "0" * 40
    path.write_text(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(
        integration.HarnessEvidenceIntegrationError,
        match="active manifest or materialization record does not bind the current harness",
    ):
        integration.validate_repository_package(repository)
