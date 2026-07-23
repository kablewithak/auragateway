"""Historical CUDA 12.9 harness-integration evidence preservation tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest

from auragateway.local_abc import (
    cu129_worker_observability_harness_integration as current,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_harness_evidence_integration as historical,
)

ROOT = Path(__file__).resolve().parents[3]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def test_historical_harness_authority_remains_distinct_from_current() -> None:
    assert historical.SOURCE_COMMIT == "426f57dd11dddc2fb8e5a703721c2189abc7a0ff"
    assert historical.CURRENT_HARNESS_DIRECTORY_SHA256 == (
        "c3ea4ae6d047a8b3f3d5afc517e26c4f13fb4a82e48e3cf28cdfabdc343230e6"
    )
    assert historical.CURRENT_HARNESS_OUTPUT_DIRECTORY == (
        "auragateway_qualification_harness_426f57d_v1"
    )

    historical_source_commit: str = historical.SOURCE_COMMIT
    current_source_commit: str = current.SOURCE_COMMIT
    historical_directory_sha256: str = historical.CURRENT_HARNESS_DIRECTORY_SHA256
    current_directory_sha256: str = current.CURRENT_HARNESS_DIRECTORY_SHA256
    historical_output_directory: str = historical.CURRENT_HARNESS_OUTPUT_DIRECTORY
    current_output_directory: str = current.CURRENT_HARNESS_OUTPUT_DIRECTORY

    assert historical_source_commit != current_source_commit
    assert historical_directory_sha256 != current_directory_sha256
    assert historical_output_directory != current_output_directory


def test_historical_evidence_identity_remains_valid_and_immutable() -> None:
    identity = historical.EvidenceIdentity.model_validate(
        _load_json(ROOT / historical.EVIDENCE_IDENTITY_PATH)
    )

    assert identity.source_commit == historical.SOURCE_COMMIT
    assert identity.materializer_saved_version_id == 337034643
    assert identity.inspection_saved_version_id == 337035826
    assert identity.inspection_saved_version_url == historical.INSPECTION_SAVED_VERSION_URL
    assert identity.materializer_recovery_notebook_sha256 == (
        historical.MATERIALIZER_RECOVERY_NOTEBOOK_SHA256
    )
    assert identity.materialization_receipt_sha256 == (historical.MATERIALIZATION_RECEIPT_SHA256)
    assert identity.inspection_evidence_zip_sha256 == (historical.INSPECTION_EVIDENCE_ZIP_SHA256)
    assert tuple(item.name for item in identity.inspection_evidence_members) == (
        historical.EXPECTED_ZIP_MEMBERS
    )


def test_historical_materialization_receipt_retains_original_non_execution_claims() -> None:
    receipt = historical.MaterializationReceipt.model_validate(
        _load_json(ROOT / historical.MATERIALIZATION_RECEIPT_PATH)
    )

    assert receipt.source_commit == historical.SOURCE_COMMIT
    assert receipt.input_mode == "kaggle_expanded_source_recovered_to_exact_archive"
    assert receipt.kaggle_auto_expanded_source_detected is True
    assert receipt.exact_archive_reconstructed is True
    assert receipt.directory_sha256 == historical.CURRENT_HARNESS_DIRECTORY_SHA256
    assert receipt.file_count == 1299
    assert receipt.total_bytes == 11_632_357
    assert receipt.gpu_execution_performed is False
    assert receipt.package_installation_performed is False
    assert receipt.model_loaded is False
    assert receipt.worker_started is False
    assert receipt.model_requests_performed == 0
    assert receipt.authorization_issued is False


def test_historical_inspection_zip_and_logs_still_validate() -> None:
    identity = historical.EvidenceIdentity.model_validate(
        _load_json(ROOT / historical.EVIDENCE_IDENTITY_PATH)
    )
    receipt = historical.MaterializationReceipt.model_validate(
        _load_json(ROOT / historical.MATERIALIZATION_RECEIPT_PATH)
    )

    records = historical._validate_evidence_zip(
        ROOT / historical.INSPECTION_ZIP_PATH,
        identity,
    )
    historical._validate_cross_evidence(receipt, records)
    historical._validate_logs(ROOT)


def test_historical_external_artifact_hashes_remain_frozen() -> None:
    expected = {
        historical.RECOVERY_NOTEBOOK_PATH: (historical.MATERIALIZER_RECOVERY_NOTEBOOK_SHA256),
        historical.MATERIALIZATION_RECEIPT_PATH: (historical.MATERIALIZATION_RECEIPT_SHA256),
        historical.MATERIALIZER_LOG_PATH: historical.MATERIALIZER_LOG_SHA256,
        historical.INSPECTION_LOG_PATH: historical.INSPECTION_LOG_SHA256,
        historical.INSPECTION_ZIP_PATH: historical.INSPECTION_EVIDENCE_ZIP_SHA256,
    }

    for relative_path, expected_sha256 in expected.items():
        assert historical._file_sha256(ROOT / relative_path) == expected_sha256


def test_historical_validator_rejects_tampered_inspection_evidence_zip(
    tmp_path: Path,
) -> None:
    identity = historical.EvidenceIdentity.model_validate(
        _load_json(ROOT / historical.EVIDENCE_IDENTITY_PATH)
    )
    tampered = tmp_path / "evidence.zip"
    shutil.copy2(ROOT / historical.INSPECTION_ZIP_PATH, tampered)
    with tampered.open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(
        historical.HarnessEvidenceIntegrationError,
        match="inspection evidence ZIP identity drifted",
    ):
        historical._validate_evidence_zip(tampered, identity)
