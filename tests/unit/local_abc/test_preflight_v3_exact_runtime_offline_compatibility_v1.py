from __future__ import annotations

import json
from pathlib import Path

from auragateway.local_abc import (
    preflight_v3_exact_runtime_offline_compatibility_v1 as runtime,
)

ROOT = Path(__file__).resolve().parents[3]


def test_materialization_authority_validates() -> None:
    runtime.validate_authority(ROOT)


def test_offline_verifier_notebook_contract_validates() -> None:
    runtime.validate_notebook(ROOT)


def test_notebook_is_unexecuted_and_non_authorizing() -> None:
    payload = json.loads((ROOT / runtime.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    metadata = payload["metadata"]["auragateway"]
    code_cell = payload["cells"][1]

    assert metadata["accelerator"] == "T4 x2"
    assert metadata["internet_required"] is False
    assert metadata["secrets_permitted"] is False
    assert metadata["package_installation_permitted"] is True
    assert metadata["dependency_resolution_permitted"] is False
    assert metadata["model_loads_permitted"] == 0
    assert metadata["worker_startups_permitted"] == 0
    assert metadata["model_requests_permitted"] == 0
    assert metadata["benchmark_trajectories_permitted"] == 0
    assert metadata["runtime_execution_authorized"] is False
    assert metadata["pilot_execution_authorized"] is False
    assert metadata["final_measured_abc_execution_authorized"] is False
    assert code_cell["execution_count"] is None
    assert code_cell["outputs"] == []


def test_notebook_uses_offline_hash_locked_target_install() -> None:
    _, code = runtime._notebook_code(ROOT)

    assert "--without-pip" in code
    assert "--python" in code
    assert "--no-index" in code
    assert "--no-cache-dir" in code
    assert "--no-deps" in code
    assert "--require-hashes" in code
    assert "PIP_NO_INDEX" in code


def test_notebook_has_t4_and_runtime_identity_gates() -> None:
    _, code = runtime._notebook_code(ROOT)

    assert "nvidia-smi" in code
    assert "torch.cuda.is_available" in code
    assert "torch.cuda.device_count" in code
    assert "2.11.0+cu129" in code
    assert "0.25.1+cu129" in code
    assert "5.14.1" in code
    assert "3.6.0" in code
    assert "importlib.import_module('vllm._C')" in code


def test_notebook_does_not_load_models_or_use_network() -> None:
    _, code = runtime._notebook_code(ROOT)

    forbidden = (
        "urllib.request",
        "requests.get(",
        "http://",
        "https://",
        "vllm.LLM(",
        "AsyncLLMEngine",
        "/v1/chat/completions",
        "huggingface_hub.snapshot_download",
    )
    assert all(item not in code for item in forbidden)


def test_notebook_preserves_role_taxonomy() -> None:
    _, code = runtime._notebook_code(ROOT)

    for role in runtime.REQUIRED_ROLES:
        assert f'"{role}"' in code

    assert "BLOCKED_BY_UPSTREAM_FAILURE" in code
    assert "FAILED_PENDING_REVIEW" in code
    assert "PASSED_PENDING_REPOSITORY_ACCEPTANCE" in code


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

    assert summary["status"] == ("PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V1_VALID")
    assert summary["package_count"] == 196
    assert summary["sha_manifest_entry_count"] == 200
    assert summary["total_wheel_bytes"] == 6164913809
    assert summary["wheelhouse_materialized"] is True
    assert summary["exact_runtime_materialized"] is True
    assert summary["exact_runtime_offline_verified"] is False
    assert summary["p5_p6_exact_runtime_requalified"] is False
    assert summary["runtime_execution_authorized"] is False
    assert summary["pilot_execution_authorized"] is False
    assert summary["final_measured_abc_execution_authorized"] is False
