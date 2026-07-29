from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_p0_p2_platform_diagnostic as diagnostic,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )


def _request_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "request_id": "auragateway-cu129-p0-p2-platform-diagnostic-request-v1",
        "source_main_merge_commit": diagnostic.SOURCE_MAIN_MERGE_COMMIT,
        "option_c_decision_record_path": diagnostic.DECISION_RECORD_PATH.as_posix(),
        "mode": "KAGGLE_DIAGNOSTIC",
        "notebook_name": diagnostic.NOTEBOOK_NAME,
        "failed_notebook_name": diagnostic.FAILED_NOTEBOOK_NAME,
        "runtime_output_directory": diagnostic.RUNTIME_OUTPUT_DIRECTORY,
        "evidence_zip_name": diagnostic.EVIDENCE_ZIP_NAME,
        "maximum_sessions": 1,
        "stop_on_first_failure": True,
        "network_access_permitted": False,
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "model_load_permitted": False,
        "worker_start_permitted": False,
        "model_requests_permitted": 0,
        "benchmark_trajectory_requests_permitted": 0,
        "hidden_retries_permitted": False,
        "filesystem_mutation_scope": "KAGGLE_WORKING_DIRECTORY_ONLY",
        "system_library_copy_permitted": False,
        "libcuda_symlink_permitted": False,
        "external_spend": 0,
        "probes": [
            {
                "probe_id": "P0",
                "name": "KAGGLE_IMAGE_AND_RUNTIME_IDENTITY",
                "pass_decision": "PLATFORM_IDENTITY_CAPTURED",
                "fail_decision": "DIAGNOSTIC_INVALID",
            },
            {
                "probe_id": "P1",
                "name": "CUDA_DRIVER_LINKER_VISIBILITY",
                "pass_decision": "CUDA_DRIVER_LINKER_CONTRACT_PASSED",
                "fail_decision": "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
            },
            {
                "probe_id": "P2",
                "name": "MINIMAL_TRITON_KERNEL",
                "pass_decision": "CURRENT_STACK_TRITON_PRIMITIVE_PASSED",
                "fail_decision": "CURRENT_STACK_TRITON_INCOMPATIBLE",
            },
        ],
        "required_outputs": list(diagnostic.REQUIRED_OUTPUTS),
        "next_gate_on_pass": "implement_explicit_triton_attention_backend",
        "next_gate_on_failure": "preserve_evidence_and_classify_platform_failure",
    }


def _implementation_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_id": ("auragateway-cu129-p0-p2-platform-diagnostic-implementation-v1"),
        "source_main_merge_commit": diagnostic.SOURCE_MAIN_MERGE_COMMIT,
        "request_path": diagnostic.REQUEST_PATH.as_posix(),
        "notebook_path": diagnostic.NOTEBOOK_PATH.as_posix(),
        "notebook_name": diagnostic.NOTEBOOK_NAME,
        "notebook_sha256": diagnostic.notebook_sha256(),
        "notebook_cell_count": 2,
        "output_cells_present": False,
        "execution_counts_present": False,
        "runtime_output_directory": diagnostic.RUNTIME_OUTPUT_DIRECTORY,
        "evidence_zip_name": diagnostic.EVIDENCE_ZIP_NAME,
        "required_outputs": list(diagnostic.REQUIRED_OUTPUTS),
        "safety": {
            "authorization_issued": False,
            "kaggle_execution_performed": False,
            "gpu_execution_performed": False,
            "model_loaded": False,
            "worker_started": False,
            "model_requests_performed": 0,
            "benchmark_trajectory_requests_performed": 0,
            "runtime_worker_source_changed": False,
            "credentials_used": False,
            "customer_data_used": False,
            "external_spend": 0,
        },
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "next_gate": "review_and_materialize_p0_p2_platform_diagnostic",
        "non_claims": [f"non-claim-{index}" for index in range(12)],
    }


def _write_repository_fixture(root: Path, *, backend_mutated: bool = False) -> None:
    decision = {
        "decision": "APPROVED_FOR_OPTION_C_TWO_STAGE_RUNTIME_DIAGNOSTIC",
        "next_gate": "implement_p0_p2_platform_diagnostic_assets",
        "platform_diagnostic": {},
        "selected_strategy": {},
    }
    _write_json(root / diagnostic.DECISION_RECORD_PATH, decision)
    _write_json(root / diagnostic.REQUEST_PATH, _request_payload())
    _write_json(root / diagnostic.IMPLEMENTATION_RECORD_PATH, _implementation_payload())
    command = ["python", "-m", "vllm"]
    if backend_mutated:
        command.extend(["--attention-backend", "TRITON_ATTN"])
    _write_json(
        root / diagnostic.WORKER_PLAN_PATH,
        {
            "workers": [
                {"command_argv": command},
                {"command_argv": command},
            ]
        },
    )
    diagnostic.write_notebook(root / diagnostic.NOTEBOOK_PATH)


def test_request_accepts_exact_fixed_contract() -> None:
    request = diagnostic.PlatformDiagnosticRequest.model_validate(_request_payload())

    assert tuple(item.probe_id for item in request.probes) == ("P0", "P1", "P2")
    assert request.required_outputs == diagnostic.REQUIRED_OUTPUTS
    assert request.model_requests_permitted == 0
    assert request.worker_start_permitted is False


def test_request_rejects_session_budget_drift() -> None:
    payload = _request_payload()
    payload["maximum_sessions"] = 2

    with pytest.raises(ValidationError):
        diagnostic.PlatformDiagnosticRequest.model_validate(payload)


def test_notebook_generation_is_deterministic_and_output_free(tmp_path: Path) -> None:
    path = tmp_path / "diagnostic.ipynb"

    diagnostic.write_notebook(path)
    first = path.read_bytes()
    diagnostic.write_notebook(path)
    second = path.read_bytes()
    validation = diagnostic.validate_notebook(path)

    assert first == second == diagnostic.notebook_bytes()
    assert validation["notebook_sha256"] == diagnostic.notebook_sha256()
    assert validation["cell_count"] == 2
    assert validation["output_cells_present"] is False


def test_notebook_program_preserves_execution_boundary() -> None:
    required = (
        "BUILD_DATE",
        "GIT_COMMIT",
        "nvidia-smi",
        "-lcuda",
        "triton.jit",
        "--no-index",
        "--require-hashes",
    )
    prohibited = (
        "Qwen/Qwen",
        "vllm.entrypoints.openai.api_server",
        "/v1/chat/completions",
        "--attention-backend",
        "urllib.request",
    )

    assert all(marker in diagnostic.KAGGLE_PROGRAM for marker in required)
    assert all(marker not in diagnostic.KAGGLE_PROGRAM for marker in prohibited)
    assert len(diagnostic.NOTEBOOK_NAME) <= 50
    assert len(diagnostic.FAILED_NOTEBOOK_NAME) <= 50


def test_notebook_validation_rejects_identity_drift(tmp_path: Path) -> None:
    path = tmp_path / "diagnostic.ipynb"
    diagnostic.write_notebook(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cells"][0]["source"].append("tampered\n")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        diagnostic.P0P2PlatformDiagnosticError,
        match="identity drifted",
    ):
        diagnostic.validate_notebook(path)


def test_repository_package_validates_without_runtime_mutation(tmp_path: Path) -> None:
    _write_repository_fixture(tmp_path)

    summary = diagnostic.validate_repository_package(tmp_path)

    assert summary["status"] == "P0_P2_PLATFORM_DIAGNOSTIC_IMPLEMENTATION_VALID"
    assert summary["probe_count"] == 3
    assert summary["required_output_count"] == 6
    assert summary["runtime_worker_source_changed"] is False
    assert summary["authorization_issued"] is False
    assert summary["kaggle_execution_performed"] is False


def test_repository_package_rejects_mixed_backend_implementation(
    tmp_path: Path,
) -> None:
    _write_repository_fixture(tmp_path, backend_mutated=True)

    with pytest.raises(
        diagnostic.P0P2PlatformDiagnosticError,
        match="runtime backend mutation was mixed",
    ):
        diagnostic.validate_repository_package(tmp_path)


def test_implementation_record_rejects_notebook_hash_drift() -> None:
    payload = _implementation_payload()
    payload["notebook_sha256"] = "f" * 63

    with pytest.raises(ValidationError):
        diagnostic.PlatformDiagnosticImplementationRecord.model_validate(payload)
