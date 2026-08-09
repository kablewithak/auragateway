from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import preflight_v3_exact_runtime_offline_compatibility_v3 as runtime


def _copy(source_root: Path, target_root: Path, relative: Path) -> None:
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_root / relative, target)


@pytest.fixture
def candidate_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    paths = (
        *runtime.EXPECTED_AUTHORITIES.keys(),
        runtime.NOTEBOOK_PATH,
        runtime.SOURCE_PATH,
        runtime.TEST_PATH,
        runtime.ADR_PATH,
        runtime.REPORT_PATH,
        runtime.RUNBOOK_PATH,
    )
    for path in paths:
        _copy(source_root, tmp_path, path)
    monkeypatch.setattr(runtime, "_require_base_main_ancestor", lambda repo_root: None)
    return tmp_path


def test_capability_contract_is_reconciled_and_non_authorizing() -> None:
    contract = runtime._capability_contract()

    assert contract.current_boundary == "P0_FINAL_RUNTIME_OFFLINE_VERIFIER_IMPLEMENTATION"
    assert contract.required_cuda_native_module == "vllm._C_stable_libtorch"
    assert contract.static_linker_provenance_required is True
    assert contract.dynamic_loader_provenance_required is True
    assert contract.successful_native_import_alone_sufficient is False
    assert contract.cuda_stub_and_compat_paths_permitted is False
    assert contract.unapproved_ambient_python_native_libraries_permitted is False
    assert contract.model_loads_permitted == 0
    assert contract.worker_startups_permitted == 0
    assert contract.model_requests_permitted == 0
    assert contract.benchmark_trajectories_permitted == 0


def test_notebook_contract_validates(candidate_repo: Path) -> None:
    runtime.validate_notebook(candidate_repo)


def test_notebook_uses_controlled_startup_and_loader_provenance(candidate_repo: Path) -> None:
    _, code = runtime._notebook(candidate_repo)

    assert 'environment.pop("PYTHONPATH", None)' in code
    assert 'environment.pop("PYTHONHOME", None)' in code
    assert 'environment.pop("LD_PRELOAD", None)' in code
    assert 'sys.modules["sitecustomize"] = sentinel("sitecustomize")' in code
    assert 'sys.modules["usercustomize"] = sentinel("usercustomize")' in code
    assert "site.main()" in code
    assert '["ldd", str(native_path)]' in code
    assert 'Path("/proc/self/maps")' in code
    assert 'REAL_DRIVER_DIRECTORY = Path("/usr/local/nvidia/lib64")' in code
    assert '"/usr/local/cuda/lib64/stubs"' in code
    assert '"/usr/local/cuda/compat"' in code


def test_notebook_uses_correct_vllm_cuda_extension(candidate_repo: Path) -> None:
    _, code = runtime._notebook(candidate_repo)

    assert 'REQUIRED_NATIVE_MODULE = "vllm._C_stable_libtorch"' in code
    assert 'importlib.import_module("vllm._C_stable_libtorch")' in code
    assert "importlib.import_module('vllm._C')" not in code
    assert 'importlib.import_module("vllm._C")' not in code
    assert "CudaPlatform.import_kernels()" in code


def test_notebook_preserves_exact_offline_install(candidate_repo: Path) -> None:
    _, code = runtime._notebook(candidate_repo)

    assert "EXPECTED_PACKAGE_COUNT = 196" in code
    assert '"--no-index"' in code
    assert '"--no-deps"' in code
    assert '"--require-hashes"' in code
    assert "EXPECTED_TOTAL_WHEEL_BYTES = 6164913809" in code


def test_notebook_prohibits_model_worker_and_request_execution(candidate_repo: Path) -> None:
    payload, code = runtime._notebook(candidate_repo)
    metadata_root = cast(dict[str, object], payload["metadata"])
    metadata = cast(dict[str, object], metadata_root["auragateway"])

    assert (
        metadata["notebook_name"]
        == "auragateway-preflight-v3-exact-runtime-offline-compatibility-v3"
    )
    assert metadata["requested_kaggle_title"] == "ag-preflight-v3-final-offline-verifier-v3"
    assert metadata["execution_authorization_issued"] is False
    assert metadata["runtime_execution_authorized"] is False
    assert metadata["next_expensive_execution_permitted"] is False
    assert metadata["model_loads_permitted"] == 0
    assert metadata["worker_startups_permitted"] == 0
    assert metadata["model_requests_permitted"] == 0
    assert metadata["benchmark_trajectories_permitted"] == 0
    assert "vllm.LLM(" not in code
    assert "AsyncLLMEngine" not in code
    assert "EngineArgs(" not in code
    assert "requests.post(" not in code


def test_all_reconciled_capability_roles_are_present(candidate_repo: Path) -> None:
    _, code = runtime._notebook(candidate_repo)

    for role in runtime.REQUIRED_CAPABILITY_ROLES:
        assert f'"{role}"' in code


def test_generate_is_deterministic(candidate_repo: Path) -> None:
    first = runtime.generate(candidate_repo)
    first_review = (candidate_repo / runtime.REVIEW_PATH).read_bytes()
    first_record = (candidate_repo / runtime.RECORD_PATH).read_bytes()

    second = runtime.generate(candidate_repo)
    second_review = (candidate_repo / runtime.REVIEW_PATH).read_bytes()
    second_record = (candidate_repo / runtime.RECORD_PATH).read_bytes()

    assert first == second
    assert first_review == second_review
    assert first_record == second_record


def test_validate_implementation_preserves_execution_boundary(candidate_repo: Path) -> None:
    runtime.generate(candidate_repo)

    result = runtime.validate_implementation(candidate_repo)

    assert result["implementation_status"] == "IMPLEMENTED_NOT_EXECUTED"
    assert result["required_cuda_native_module"] == "vllm._C_stable_libtorch"
    assert result["exact_runtime_offline_verified"] is False
    assert result["p5_p6_exact_runtime_requalified"] is False
    assert result["runtime_execution_authorized"] is False
    assert result["pilot_execution_authorized"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["next_expensive_execution_permitted"] is False
    assert result["next_gate"] == runtime.NEXT_GATE


def test_reconciliation_authority_drift_fails_closed(candidate_repo: Path) -> None:
    target = candidate_repo / runtime.RECONCILIATION_RECORD_PATH
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(runtime.VerifierImplementationError) as captured:
        runtime._require_authorities(candidate_repo)

    assert captured.value.error_code == "PREFLIGHT_V3_FINAL_VERIFIER_AUTHORITY_DRIFT"


def test_generated_record_drift_fails_closed(candidate_repo: Path) -> None:
    runtime.generate(candidate_repo)
    target = candidate_repo / runtime.RECORD_PATH
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(runtime.VerifierImplementationError) as captured:
        runtime.validate_generated(candidate_repo)

    assert captured.value.error_code == "PREFLIGHT_V3_FINAL_VERIFIER_GENERATED_RECORD_DRIFT"
