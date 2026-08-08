from __future__ import annotations

import hashlib
import json
from pathlib import Path

from auragateway.local_abc import (
    preflight_v3_exact_runtime_resolution_reconnaissance_v1 as runtime,
)

ROOT = Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_merged_authority_is_valid() -> None:
    runtime.validate_authority(ROOT)


def test_notebook_contract_is_valid() -> None:
    runtime.validate_notebook(ROOT)


def test_notebook_is_unexecuted_and_cpu_only() -> None:
    payload = json.loads((ROOT / runtime.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    metadata = payload["metadata"]["auragateway"]
    code_cell = payload["cells"][1]

    assert metadata["requested_kaggle_title"] == runtime.REQUESTED_KAGGLE_TITLE
    assert len(runtime.REQUESTED_KAGGLE_TITLE) <= 50
    assert metadata["accelerator"] == "none"
    assert metadata["internet_required"] is True
    assert metadata["package_installation_permitted"] is False
    assert metadata["artifact_download_retention_permitted"] is False
    assert metadata["model_loads_permitted"] == 0
    assert metadata["model_requests_permitted"] == 0
    assert metadata["benchmark_trajectories_permitted"] == 0
    assert metadata["credentials_permitted"] is False
    assert metadata["customer_data_permitted"] is False
    assert metadata["external_spend"] == 0
    assert code_cell["execution_count"] is None
    assert code_cell["outputs"] == []


def test_notebook_binds_exact_preflight_v3_runtime() -> None:
    payload = json.loads((ROOT / runtime.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    source = "".join(payload["cells"][1]["source"])

    assert f'EXPECTED_VLLM_DISTRIBUTION = "{runtime.EXPECTED_VLLM_DISTRIBUTION}"' in source
    assert runtime.EXPECTED_VLLM_WHEEL_SHA256 in source
    assert f'EXPECTED_TORCH_VERSION = "{runtime.EXPECTED_TORCH_VERSION}"' in source
    assert 'VLLM_RELEASE_TAG = "v0.25.1"' in source
    assert '"--dry-run"' in source
    assert '"--ignore-installed"' in source
    assert '"--only-binary=:all:"' in source
    assert '"--report"' in source
    assert '"--no-cache-dir"' in source
    assert '"x86_64" in lowered' in source


def test_notebook_fails_closed_against_mutation_and_inputs() -> None:
    payload = json.loads((ROOT / runtime.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    source = "".join(payload["cells"][1]["source"])

    assert "installed_snapshot" in source
    assert "PACKAGE_ENVIRONMENT_MUTATED" in source
    assert "KAGGLE_INPUTS_PRESENT" in source
    assert "CREDENTIAL_ENV_PRESENT" in source
    assert "OUTPUT_ALREADY_EXISTS" in source
    assert "WHEEL_ARTIFACT_RETENTION_DETECTED" in source
    assert "stable_url_sha256" in source
    assert "query_present" in source
    assert "fragment_present" in source


def test_notebook_has_no_model_or_gpu_execution_surface() -> None:
    payload = json.loads((ROOT / runtime.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    source = "".join(payload["cells"][1]["source"])

    assert "torch.cuda" not in source
    assert "vllm.LLM" not in source
    assert "AsyncLLMEngine" not in source
    assert "/v1/chat/completions" not in source
    assert "model_requests_performed" in source
    assert '"model_requests_performed": 0' in source
    assert '"benchmark_trajectories_performed": 0' in source


def test_old_resolution_lock_remains_non_authoritative() -> None:
    design = json.loads((ROOT / runtime.DESIGN_PATH).read_text(encoding="utf-8"))

    assert design["direct_reuse_permitted"] is False
    assert design["existing_materializer_runtime"]["vllm_distribution_version"] == ("0.19.1")
    assert design["planned_runtime"]["vllm_distribution_version"] == (
        runtime.EXPECTED_VLLM_DISTRIBUTION
    )


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


def test_generated_artifacts_validate() -> None:
    runtime.generate(ROOT)
    summary = runtime.validate_implementation(ROOT)

    assert summary["status"] == ("PREFLIGHT_V3_EXACT_RUNTIME_RESOLUTION_RECONNAISSANCE_V1_VALID")
    assert summary["implementation_status"] == "IMPLEMENTED_NOT_EXECUTED"
    assert summary["exact_runtime_resolution_lock_frozen"] is False
    assert summary["exact_runtime_materialized"] is False
    assert summary["exact_runtime_offline_verified"] is False
    assert summary["runtime_execution_authorized"] is False
    assert summary["pilot_execution_authorized"] is False
    assert summary["final_measured_abc_execution_authorized"] is False
    assert summary["next_gate"] == runtime.NEXT_GATE


def test_notebook_raw_identity_is_bound_by_generated_review() -> None:
    runtime.generate(ROOT)
    review = json.loads((ROOT / runtime.REVIEW_PATH).read_text(encoding="utf-8"))

    assert review["notebook"]["path"] == runtime.NOTEBOOK_PATH.as_posix()
    assert review["notebook"]["sha256"] == _sha256(ROOT / runtime.NOTEBOOK_PATH)


def test_generated_record_preserves_non_authorizing_boundary() -> None:
    runtime.generate(ROOT)
    record = json.loads((ROOT / runtime.RECORD_PATH).read_text(encoding="utf-8"))

    assert record["required_outputs"] == [
        "resolved_artifacts.json",
        "resolver_report.json",
        "host_policy.json",
        "resolution_receipt.json",
        "output_manifest.json",
    ]
    assert record["exact_runtime_resolution_lock_frozen"] is False
    assert record["exact_runtime_materialized"] is False
    assert record["exact_runtime_offline_verified"] is False
    assert record["runtime_execution_authorized"] is False
    assert record["pilot_execution_authorized"] is False
    assert record["final_measured_abc_execution_authorized"] is False
