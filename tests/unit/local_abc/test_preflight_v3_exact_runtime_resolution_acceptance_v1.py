from __future__ import annotations

import json
from pathlib import Path

from auragateway.local_abc import (
    preflight_v3_exact_runtime_resolution_acceptance_v1 as runtime,
)

ROOT = Path(__file__).resolve().parents[3]


def test_exact_runtime_resolution_lock_package_validates() -> None:
    summary = runtime.validate_repository_package(ROOT)

    assert summary["status"] == "PREFLIGHT_V3_EXACT_RUNTIME_RESOLUTION_LOCK_V1_VALID"
    assert summary["package_count"] == 196
    assert summary["host_count"] == 5
    assert summary["exact_runtime_resolution_lock_frozen"] is True
    assert summary["exact_runtime_materialized"] is False
    assert summary["exact_runtime_offline_verified"] is False
    assert summary["runtime_execution_authorized"] is False
    assert summary["pilot_execution_authorized"] is False
    assert summary["final_measured_abc_execution_authorized"] is False


def test_acceptance_binds_executed_source_to_repository_source() -> None:
    acceptance = json.loads((ROOT / runtime.ACCEPTANCE_PATH).read_text(encoding="utf-8"))

    assert acceptance["kaggle_script_version_id"] == 341073810
    assert acceptance["repository_notebook_sha256"] == (runtime.EXPECTED_REPOSITORY_NOTEBOOK_SHA256)
    assert acceptance["executed_notebook_sha256"] == (runtime.EXPECTED_EXECUTED_NOTEBOOK_SHA256)
    assert acceptance["executed_markdown_source_matches_repository"] is True
    assert acceptance["executed_code_source_matches_repository"] is True
    assert acceptance["code_cell_source_sha256"] == runtime.EXPECTED_CODE_SOURCE_SHA256


def test_exact_lock_binds_planned_runtime() -> None:
    lock = json.loads((ROOT / runtime.LOCK_PATH).read_text(encoding="utf-8"))
    runtime_identity = lock["runtime"]

    assert runtime_identity["vllm_distribution_version"] == "0.25.1+cu129"
    assert (
        runtime_identity["vllm_wheel_sha256"]
        == "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
    )
    assert runtime_identity["torch_version"] == "2.11.0+cu129"
    assert lock["package_count"] == 196
    assert lock["host_count"] == 5


def test_exact_lock_has_unique_wheel_only_records() -> None:
    lock = json.loads((ROOT / runtime.LOCK_PATH).read_text(encoding="utf-8"))
    records = lock["records"]

    assert len(records) == 196
    assert len({record["normalized_name"] for record in records}) == 196
    assert all(record["artifact_filename"].endswith(".whl") for record in records)
    assert all(record["sanitized_url"].startswith("https://") for record in records)
    assert all("?" not in record["sanitized_url"] for record in records)
    assert all("#" not in record["sanitized_url"] for record in records)


def test_acceptance_remains_non_authorizing() -> None:
    acceptance = json.loads((ROOT / runtime.ACCEPTANCE_PATH).read_text(encoding="utf-8"))

    assert acceptance["exact_runtime_resolution_lock_frozen"] is True
    assert acceptance["exact_runtime_materialized"] is False
    assert acceptance["exact_runtime_offline_verified"] is False
    assert acceptance["runtime_execution_authorized"] is False
    assert acceptance["pilot_execution_authorized"] is False
    assert acceptance["final_measured_abc_execution_authorized"] is False
