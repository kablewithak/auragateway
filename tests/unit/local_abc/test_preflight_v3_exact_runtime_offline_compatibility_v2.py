from __future__ import annotations

import json
from pathlib import Path

from auragateway.local_abc import (
    preflight_v3_exact_runtime_offline_compatibility_v2 as runtime,
)

ROOT = Path(__file__).resolve().parents[3]


def test_v1_false_negative_acceptance_validates() -> None:
    runtime.validate_v1_acceptance(ROOT)


def test_v2_notebook_contract_validates() -> None:
    runtime.validate_v2_notebook(ROOT)


def test_v2_preserves_distribution_and_module_version_separation() -> None:
    _, code = runtime._notebook_code(ROOT)

    assert 'EXPECTED_VLLM_MODULE_VERSION = "0.25.1"' in code
    assert '"vllm": "0.25.1+cu129"' in code
    assert 'payload.get("vllm") != EXPECTED_VLLM_MODULE_VERSION' in code
    assert code.count('payload.get("vllm") != EXPECTED_RUNTIME["vllm"]') == 1
    assert "vLLM module version drifted" not in code


def test_v2_still_reaches_native_extension_after_module_gate() -> None:
    _, code = runtime._notebook_code(ROOT)

    assert '"vllm_module"' in code
    assert '"vllm_native_extension"' in code
    assert "importlib.import_module('vllm._C')" in code
    assert 'native_dependencies = ("vllm_module",)' in code


def test_v2_remains_offline_and_non_authorizing() -> None:
    payload = json.loads((ROOT / runtime.V2_NOTEBOOK_PATH).read_text(encoding="utf-8"))
    metadata = payload["metadata"]["auragateway"]
    _, code = runtime._notebook_code(ROOT)

    assert metadata["internet_required"] is False
    assert metadata["accelerator"] == "T4 x2"
    assert metadata["dependency_resolution_permitted"] is False
    assert metadata["model_loads_permitted"] == 0
    assert metadata["worker_startups_permitted"] == 0
    assert metadata["model_requests_permitted"] == 0
    assert metadata["benchmark_trajectories_permitted"] == 0
    assert metadata["runtime_execution_authorized"] is False
    assert metadata["pilot_execution_authorized"] is False
    assert metadata["final_measured_abc_execution_authorized"] is False

    assert "--no-index" in code
    assert "--no-deps" in code
    assert "--require-hashes" in code
    assert "vllm.LLM(" not in code
    assert "AsyncLLMEngine" not in code
    assert "https://" not in code


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


def test_generated_v2_implementation_validates() -> None:
    runtime.generate(ROOT)
    summary = runtime.validate_implementation(ROOT)

    assert summary["status"] == ("PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V2_VALID")
    assert summary["v1_false_negative_accepted"] is True
    assert summary["v1_script_version_id"] == 341091805
    assert summary["vllm_distribution_version"] == "0.25.1+cu129"
    assert summary["vllm_module_semantic_version"] == "0.25.1"
    assert summary["exact_runtime_offline_verified"] is False
    assert summary["p5_p6_exact_runtime_requalified"] is False
    assert summary["runtime_execution_authorized"] is False
    assert summary["pilot_execution_authorized"] is False
    assert summary["final_measured_abc_execution_authorized"] is False
