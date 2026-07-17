"""Regression tests for the deterministic action-extraction Kaggle package v2."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_execution_package import (
    ActionExtractionExecutionPackageBundleV2,
    ActionExtractionKaggleExecutionPackageV2,
    build_action_extraction_kaggle_package_v2,
    canonical_execution_package_file_sha256,
    inspect_action_extraction_kaggle_package_v2,
    load_action_extraction_execution_package_bundle_v2,
    load_action_extraction_execution_package_v2,
)

ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_ROOT = ROOT / "benchmarks" / "local_abc"
MANIFEST_PATH = (
    BENCHMARK_ROOT / "reconcile_balance_extraction_requalification_execution_package_v2.json"
)
EXPECTED_PACKAGE_SHA256 = "deb7d803819ec489218f78ecc4466ae1402eef30a63ba7b93d293ea872677451"
EXPECTED_MANIFEST_SHA256 = "47e47014e225d3372619568f43f1b139c650b58bfd4773d20089fbc88b07ec0b"
EXPECTED_PR89_MERGE = "1cbb01e72fc624b71be1faef9da199a1556d2f0c"
EXPECTED_MEMBER_PATHS = (
    "benchmarks/local_abc/reconcile_balance_extraction_requalification_notebook_binding_v2.json",
    "notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb",
)


def manifest_payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))


def build_package(tmp_path: Path) -> Path:
    path = tmp_path / "auragateway-local-abc-action-extraction-requalification-notebook-v2.zip"
    build_action_extraction_kaggle_package_v2(repository_root=ROOT, destination=path)
    return path


def load_bundle(tmp_path: Path) -> ActionExtractionExecutionPackageBundleV2:
    package_path = build_package(tmp_path)
    return load_action_extraction_execution_package_bundle_v2(
        repository_root=ROOT,
        execution_package_path=MANIFEST_PATH,
        generated_package_path=package_path,
    )


def test_execution_package_manifest_loads() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert manifest.source_merge_commit == EXPECTED_PR89_MERGE
    assert manifest.package_sha256 == EXPECTED_PACKAGE_SHA256


def test_execution_package_manifest_is_canonical_single_line_json() -> None:
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert text.count("\n") == 1
    assert canonical_execution_package_file_sha256(MANIFEST_PATH) == (EXPECTED_MANIFEST_SHA256)


def test_source_bindings_use_exact_pr89_blobs() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert tuple(binding.git_blob_sha for binding in manifest.source_bindings) == (
        "97a5756d3a95defccdff90811ff1318f863456b7",
        "237c344330d63b803f94265dbdc24c20ae379dcd",
        "9e88e7ac87b0452839b25c540f4e50f3282e72a1",
    )


def test_deterministic_builder_reproduces_package_identity(tmp_path: Path) -> None:
    first = build_package(tmp_path)
    first_bytes = first.read_bytes()
    second = tmp_path / "second.zip"
    build_action_extraction_kaggle_package_v2(repository_root=ROOT, destination=second)
    assert first_bytes == second.read_bytes()
    assert inspect_action_extraction_kaggle_package_v2(first).package_sha256 == (
        EXPECTED_PACKAGE_SHA256
    )


def test_package_has_exact_two_member_constitution(tmp_path: Path) -> None:
    facts = inspect_action_extraction_kaggle_package_v2(build_package(tmp_path))
    assert facts.member_paths == EXPECTED_MEMBER_PATHS
    assert facts.member_size_bytes == (4097, 72258)


def test_package_members_use_fixed_stored_metadata(tmp_path: Path) -> None:
    package_path = build_package(tmp_path)
    with zipfile.ZipFile(package_path) as archive:
        assert archive.testzip() is None
        for info in archive.infolist():
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.create_system == 3
            assert info.external_attr >> 16 == 0o100644


def test_package_member_bytes_match_repository_sources(tmp_path: Path) -> None:
    package_path = build_package(tmp_path)
    with zipfile.ZipFile(package_path) as archive:
        for member_path in EXPECTED_MEMBER_PATHS:
            assert archive.read(member_path) == (ROOT / member_path).read_bytes()


def test_cross_file_bundle_preserves_qualification_lineage(tmp_path: Path) -> None:
    bundle = load_bundle(tmp_path)
    assert bundle.qualification_package.binding.notebook_qualified_for_bounded_execution is True
    assert bundle.execution_package.notebook_binding_sha256 == (
        bundle.qualification_package.binding.fingerprint()
    )
    assert bundle.qualification_package.binding.authorization_consumed is False


def test_execution_scope_is_exactly_one_complete_sixteen_case_run() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert manifest.execution_attempt_limit == 1
    assert manifest.request_count == 16
    assert manifest.request_attempts_per_case == 1
    assert manifest.complete_suite_required is True
    assert manifest.failed_case_only_execution_permitted is False


def test_retry_repair_and_replacement_paths_remain_blocked() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert manifest.hidden_retry_count == 0
    assert manifest.repair_attempt_count == 0
    assert manifest.replacement_request_count == 0
    assert manifest.restart_and_rerun_permitted is False
    assert manifest.failed_cell_only_rerun_permitted is False


def test_kaggle_runtime_operator_boundary_is_explicit() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert manifest.kaggle_accelerator == "GPU T4 x2"
    assert manifest.kaggle_internet_required is True
    assert manifest.kaggle_secrets_required is False
    assert manifest.package_attachment_required is True
    assert manifest.operator_merge_verification_required is True


def test_privacy_zero_spend_and_scope_blocks_remain_frozen() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert manifest.raw_prompt_retention_permitted is False
    assert manifest.raw_output_retention_permitted is False
    assert manifest.raw_action_retention_permitted is False
    assert manifest.token_id_retention_permitted is False
    assert manifest.external_spend == 0
    assert manifest.customer_data_used is False
    assert manifest.cache_measurement_in_scope is False
    assert manifest.full_measured_rerun_authorized is False


def test_packaging_does_not_consume_authorization_or_execute_model() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert manifest.authorization_consumed is False
    assert manifest.provider_call_performed is False
    assert manifest.model_request_performed is False
    assert manifest.gpu_execution_performed is False
    assert manifest.credential_accessed is False


def test_evidence_archive_is_mandatory_after_execution() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert manifest.evidence_archive_download_required is True
    assert manifest.expected_evidence_archive_filename == (
        "auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip"
    )


def test_mutated_notebook_member_fails_package_contract(tmp_path: Path) -> None:
    package_path = build_package(tmp_path)
    mutated = tmp_path / "mutated.zip"
    with zipfile.ZipFile(package_path) as source, zipfile.ZipFile(mutated, "w") as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.endswith(".ipynb"):
                data += b"\n"
            target.writestr(info, data)
    facts = inspect_action_extraction_kaggle_package_v2(mutated)
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    bundle = load_bundle(tmp_path)
    with pytest.raises(ValidationError, match="generated package SHA"):
        ActionExtractionExecutionPackageBundleV2(
            qualification_package=bundle.qualification_package,
            execution_package=manifest,
            facts=facts,
        )


def test_extra_member_fails_closed(tmp_path: Path) -> None:
    package_path = build_package(tmp_path)
    with zipfile.ZipFile(package_path, "a", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("unexpected.txt", b"unexpected")
    with pytest.raises(ValueError, match="member paths or order"):
        inspect_action_extraction_kaggle_package_v2(package_path)


def test_manifest_mutation_fails_closed() -> None:
    payload = manifest_payload()
    payload["package_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="archive digest drifted"):
        ActionExtractionKaggleExecutionPackageV2.model_validate(payload)


def test_next_gate_is_immutable_execution_evidence_audit() -> None:
    manifest = load_action_extraction_execution_package_v2(MANIFEST_PATH)
    assert manifest.status == "ready_for_single_kaggle_execution"
    assert manifest.execution_permitted_after_package_pr_merge is True
    assert manifest.next_gate == "immutable_action_extraction_v2_execution_evidence_audit"
