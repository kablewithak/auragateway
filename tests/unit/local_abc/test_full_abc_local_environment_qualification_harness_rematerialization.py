from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_harness_rematerialization as remat,
)

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_RECORD_SHA256 = "18a2055d26e83dd3d7ac1f67c680a7e1f6ff29841af5883a3e400444de51f218"


def test_repository_record_has_expected_identity() -> None:
    record = remat.load_record(ROOT / remat.RECORD_PATH)

    assert record.fingerprint() == EXPECTED_RECORD_SHA256
    assert record.source_main_merge_commit == remat.SOURCE_MAIN_MERGE_COMMIT
    assert record.next_gate == remat.NEXT_GATE


def test_default_builder_reproduces_repository_record() -> None:
    assert remat.build_default_record() == remat.load_record(ROOT / remat.RECORD_PATH)


def test_superseded_harness_is_retained_only_as_failed_lineage() -> None:
    binding = remat.load_record(ROOT / remat.RECORD_PATH).superseded_harness

    assert binding.source_commit == remat.SUPERSEDED_HARNESS_SOURCE_COMMIT
    assert binding.failure_code == "HARNESS_AUTHORIZATION_SCHEMA_MISMATCH"
    assert binding.worker_started is False
    assert binding.model_requests_performed == 0
    assert binding.runtime_evidence_generated is False
    assert binding.superseded_for_future_qualification is True


def test_replacement_harness_binds_saved_notebook_output() -> None:
    binding = remat.load_record(ROOT / remat.RECORD_PATH).replacement_harness

    assert binding.kaggle_resource_slug == ("kabomolefe/ag-harness-materializer-input-v3")
    assert binding.kaggle_resource_version == 1
    assert binding.mounted_path == remat.REPLACEMENT_HARNESS_PATH
    assert binding.directory_sha256 == remat.REPLACEMENT_HARNESS_SHA256
    assert binding.file_count == 953
    assert binding.total_bytes == 8_879_194
    assert binding.input_mode == "expanded_dataset_tree"


def test_parity_evidence_binds_successful_metadata_only_run() -> None:
    evidence = remat.load_record(ROOT / remat.RECORD_PATH).parity_evidence

    assert evidence.evidence_zip_sha256 == remat.PARITY_EVIDENCE_ZIP_SHA256
    assert evidence.notebook_name == "ag-harness-parity-inspection-v4"
    assert evidence.runner_loader_accepted_authorization is True
    assert evidence.gpu_execution_performed is False
    assert evidence.model_requests_performed == 0
    assert evidence.network_access_performed is False


def test_parity_evidence_bundle_is_committed_and_hash_bound() -> None:
    record = remat.load_record(ROOT / remat.RECORD_PATH)
    evidence = record.parity_evidence

    assert evidence.evidence_directory == remat.PARITY_EVIDENCE_DIRECTORY.as_posix()
    assert (ROOT / remat.PARITY_INSPECTION_REPORT_PATH).is_file()
    assert (ROOT / remat.PARITY_AUTHORIZATION_SCHEMA_REPORT_PATH).is_file()
    assert (ROOT / remat.PARITY_CANDIDATE_INVENTORY_PATH).is_file()
    assert (ROOT / remat.PARITY_EVIDENCE_SHA256_PATH).is_file()


def test_model_and_vllm_inputs_remain_unchanged() -> None:
    inputs = remat.load_record(ROOT / remat.RECORD_PATH).unchanged_runtime_inputs

    assert tuple(item.role for item in inputs) == (
        "model_artifacts",
        "vllm_wheel",
    )
    assert inputs[0].sha256 == ("b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa")
    assert inputs[1].sha256 == ("9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431")


def test_repository_package_validates_exact_updated_authorities() -> None:
    summary = remat.validate_repository_package(ROOT)

    assert summary == {
        "record_sha256": EXPECTED_RECORD_SHA256,
        "source_main_merge_commit": remat.SOURCE_MAIN_MERGE_COMMIT,
        "superseded_harness_source_commit": (remat.SUPERSEDED_HARNESS_SOURCE_COMMIT),
        "replacement_harness_sha256": remat.REPLACEMENT_HARNESS_SHA256,
        "replacement_file_count": 953,
        "replacement_total_bytes": 8_879_194,
        "parity_status": "HARNESS_AUTHORIZATION_PARITY_PASSED",
        "runner_loader_accepted_authorization": True,
        "parity_evidence_files_verified": 4,
        "runtime_manifest_sha256": remat.RUNTIME_MANIFEST_SHA256,
        "materialization_record_sha256": (remat.MATERIALIZATION_RECORD_SHA256),
        "authorization_issued": False,
        "gpu_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": remat.NEXT_GATE,
    }


def test_runtime_manifest_uses_refreshed_notebook_output() -> None:
    manifest = json.loads((ROOT / remat.RUNTIME_MANIFEST_PATH).read_text())
    harness = manifest["entries"][0]

    assert harness == {
        "artifact_format": "source_tree_directory",
        "mounted_path": remat.REPLACEMENT_HARNESS_PATH,
        "role": "harness_source",
        "sha256": remat.REPLACEMENT_HARNESS_SHA256,
    }


def test_materialization_record_binds_runtime_manifest() -> None:
    payload = json.loads((ROOT / remat.MATERIALIZATION_RECORD_PATH).read_text())
    harness = payload["entries"][0]

    assert payload["harness_source_commit"] == remat.SOURCE_MAIN_MERGE_COMMIT
    assert payload["runtime_manifest_sha256"] == remat.RUNTIME_MANIFEST_SHA256
    assert harness["kaggle_dataset_slug"] == remat.REPLACEMENT_PRODUCER_SLUG
    assert harness["mounted_path"] == remat.REPLACEMENT_HARNESS_PATH
    assert harness["sha256"] == remat.REPLACEMENT_HARNESS_SHA256


def test_record_rejects_enabling_operational_activity() -> None:
    payload = remat.load_record(ROOT / remat.RECORD_PATH).model_dump(mode="json")
    payload["safety"]["authorization_issued"] = True

    with pytest.raises(ValidationError):
        remat.HarnessRematerializationRecord.model_validate(payload)


def test_record_rejects_replacement_identity_drift() -> None:
    payload = remat.load_record(ROOT / remat.RECORD_PATH).model_dump(mode="json")
    payload["replacement_harness"]["directory_sha256"] = "0" * 64

    with pytest.raises(ValidationError):
        remat.HarnessRematerializationRecord.model_validate(payload)


def test_json_authorities_are_canonical_single_line() -> None:
    for relative_path in (
        remat.RECORD_PATH,
        remat.RUNTIME_MANIFEST_PATH,
        remat.MATERIALIZATION_RECORD_PATH,
    ):
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        expected = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        assert text == expected
