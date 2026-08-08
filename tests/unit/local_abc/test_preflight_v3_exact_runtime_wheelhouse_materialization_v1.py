from __future__ import annotations

import json
from pathlib import Path

from auragateway.local_abc import (
    preflight_v3_exact_runtime_wheelhouse_materialization_v1 as runtime,
)

ROOT = Path(__file__).resolve().parents[3]


def test_frozen_resolution_authority_validates() -> None:
    runtime.validate_authority(ROOT)


def test_materializer_notebook_contract_validates() -> None:
    runtime.validate_notebook(ROOT)


def test_embedded_lock_is_byte_identical_to_repository_lock() -> None:
    _, code = runtime._notebook_code(ROOT)
    embedded = runtime._extract_embedded_lock(code)

    assert embedded == (ROOT / runtime.LOCK_PATH).read_bytes()
    assert runtime._sha256_bytes(embedded) == runtime.EXPECTED_LOCK_SHA256


def test_notebook_is_unexecuted_and_non_authorizing() -> None:
    payload = json.loads((ROOT / runtime.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    metadata = payload["metadata"]["auragateway"]
    code_cell = payload["cells"][1]

    assert metadata["accelerator"] == "none"
    assert metadata["internet_required"] is True
    assert metadata["inputs_permitted"] is False
    assert metadata["credentials_permitted"] is False
    assert metadata["dependency_resolution_permitted"] is False
    assert metadata["package_installation_permitted"] is False
    assert metadata["model_loads_permitted"] == 0
    assert metadata["model_requests_permitted"] == 0
    assert metadata["benchmark_trajectories_permitted"] == 0
    assert code_cell["execution_count"] is None
    assert code_cell["outputs"] == []


def test_notebook_does_not_resolve_or_install_dependencies() -> None:
    _, code = runtime._notebook_code(ROOT)

    assert "pip install" not in code
    assert "pip download" not in code
    assert "--dry-run" not in code
    assert '"dependency_resolution_performed": False' in code
    assert '"package_installation_performed": False' in code


def test_transport_redirect_is_narrow_and_separate_from_authority_hosts() -> None:
    _, code = runtime._notebook_code(ROOT)

    assert "MAX_REDIRECTS_PER_ARTIFACT = 1" in code
    assert '"github.com",' in code
    assert '"release-assets.githubusercontent.com",' in code
    assert "authority_host_count_unchanged" in code
    assert "REDIRECT_POLICY_VIOLATION" in code


def test_materializer_has_full_hash_and_set_gates() -> None:
    _, code = runtime._notebook_code(ROOT)

    assert "DOWNLOAD_SHA256_MISMATCH" in code
    assert "WHEEL_SET_DRIFT" in code
    assert "sha256_manifest.json" in code
    assert "materialization_receipt.json" in code
    assert "materialization_evidence.zip" in code


def test_generate_is_deterministic() -> None:
    first = runtime.generate(ROOT)
    first_review = (ROOT / runtime.REVIEW_PATH).read_bytes()
    first_record = (ROOT / runtime.RECORD_PATH).read_bytes()

    second = runtime.generate(ROOT)
    second_review = (ROOT / runtime.REVIEW_PATH).read_bytes()
    second_record = (ROOT / runtime.RECORD_PATH).read_bytes()

    assert first == second
    assert first_review == second_review
    assert first_record == second_record


def test_generated_implementation_validates() -> None:
    runtime.generate(ROOT)
    summary = runtime.validate_implementation(ROOT)

    assert summary["status"] == ("PREFLIGHT_V3_EXACT_RUNTIME_WHEELHOUSE_MATERIALIZER_V1_VALID")
    assert summary["package_count"] == 196
    assert summary["authority_host_count"] == 5
    assert summary["exact_runtime_resolution_lock_frozen"] is True
    assert summary["exact_runtime_materialized"] is False
    assert summary["exact_runtime_offline_verified"] is False
    assert summary["runtime_execution_authorized"] is False
    assert summary["pilot_execution_authorized"] is False
    assert summary["final_measured_abc_execution_authorized"] is False
