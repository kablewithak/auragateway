from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_harness_toolchain_contracts,
)

toolchain_contracts = full_abc_local_environment_qualification_cu129_harness_toolchain_contracts


def test_inventory_entry_requires_normalized_relative_posix_path() -> None:
    with pytest.raises(ValidationError):
        toolchain_contracts.HarnessSourceInventoryEntry(
            path="../escape.py",
            git_blob_sha="0" * 40,
            sha256="0" * 64,
            size_bytes=1,
        )


def test_build_spec_requires_expected_identity_paths_to_be_required() -> None:
    with pytest.raises(ValidationError):
        toolchain_contracts.HarnessBuildSpec(
            package_id="test-package",
            source_commit="1" * 40,
            archive_name="test.zip",
            input_dataset_name="test-input",
            output_directory="test-output",
            materialization_receipt_name="receipt.json",
            required_paths=("README.md",),
            expected_file_sha256={"src/example.py": "2" * 64},
            maximum_files=10,
            maximum_total_bytes=10_000,
        )


def test_safety_contract_rejects_operational_activity() -> None:
    with pytest.raises(ValidationError):
        toolchain_contracts.HarnessToolchainSafety(model_requests_performed=1)


def test_prepared_receipt_rejects_incomplete_output_set() -> None:
    source = toolchain_contracts.HarnessSourcePackageReceipt(
        status="CURRENT_CU129_HARNESS_SOURCE_PACKAGED",
        package_id="test-package",
        source_commit="1" * 40,
        archive_name="test.zip",
        archive_sha256="2" * 64,
        inventory_sha256="3" * 64,
        output_directory="test-output",
        input_dataset_name="test-input",
        materialization_receipt_name="receipt.json",
        directory_sha256="4" * 64,
        file_count=1,
        total_bytes=1,
        required_paths=("README.md",),
        expected_file_sha256={},
    )
    materializer = toolchain_contracts.GeneratedNotebookReceipt(
        notebook_name="test-materializer",
        filename="materializer.ipynb",
        sha256="5" * 64,
        cell_count=2,
    )
    inspection = toolchain_contracts.GeneratedNotebookReceipt(
        notebook_name="test-inspection",
        filename="inspection.ipynb",
        sha256="6" * 64,
        cell_count=2,
    )

    with pytest.raises(ValidationError):
        toolchain_contracts.PreparedHarnessToolchainReceipt(
            status="CURRENT_CU129_HARNESS_TOOLCHAIN_PREPARED",
            source_package=source,
            source_receipt_sha256="7" * 64,
            source_sha256_manifest_sha256="8" * 64,
            materializer_notebook=materializer,
            inspection_notebook=inspection,
            output_filenames=("test.zip",),
            next_gate="publish_materialize_and_metadata_inspect_current_cu129_harness",
        )


def test_decision_record_rejects_incomplete_capability_set() -> None:
    payload = {
        "record_id": "auragateway-cu129-current-harness-toolchain-v1",
        "review_minimum_ancestor": "defe184d338b525e2f48104ef76e5d0d9a1329a8",
        "decision": "APPROVED_FOR_COMPLETE_CURRENT_CU129_HARNESS_TOOLCHAIN",
        "capabilities": ("deterministic_git_object_source_packaging",),
        "next_gate": "merge_then_prepare_current_cu129_harness_toolchain",
        "non_claims": (
            "current harness archive not yet generated",
            "Kaggle materialization not yet performed",
            "metadata-only input inspection not yet performed",
            "authorization not issued",
            "environment qualification not performed",
            "measured A/B/C execution not authorized",
            "production readiness not claimed",
        ),
    }

    with pytest.raises(ValidationError):
        toolchain_contracts.HarnessToolchainDecisionRecord.model_validate(payload)
