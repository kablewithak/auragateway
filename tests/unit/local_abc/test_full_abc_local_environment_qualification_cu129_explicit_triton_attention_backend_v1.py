"""Tests for explicit Triton attention-backend V1 implementation assets."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_v1 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    source = source_root / subject.TEMPLATE_PATH
    target = repo_root / subject.TEMPLATE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return repo_root


def _driver_authority() -> subject.AcceptedDriverAuthority:
    return subject.AcceptedDriverAuthority(
        status="EXPLICIT_DRIVER_LINK_PROBE_EXECUTION_ACCEPTANCE_V1_VALID",
        saved_version_id=339127349,
        terminal_decision="EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED",
        evidence_zip_sha256=("8be080c46a077d88dcd0d51325fe2a751936a599d3b350ba7def3bdf5eb7b33c"),
        unchanged_replay_authorized=False,
    )


def _platform_authority() -> subject.AcceptedPlatformAuthority:
    return subject.AcceptedPlatformAuthority(
        status="P0_P2_PLATFORM_DIAGNOSTIC_EXECUTION_ACCEPTANCE_V1_VALID",
        saved_version_id=339140121,
        terminal_decision="P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED",
        evidence_zip_sha256=("e115d2f8c6c000a7666e0482e4d3d9f69bb74599fbf4f657304d456930de3240"),
        gpu_count=2,
        gpu_name="Tesla T4",
        compute_capability=(7, 5),
        torch_version="2.10.0+cu129",
        triton_version="3.6.0",
        wheel_entry_count=176,
        manifest_entry_count=182,
        verified_entry_count=182,
        implementation_authorized=True,
        unchanged_replay_authorized=False,
        next_gate="design_and_implement_explicit_triton_attention_backend_v1",
    )


def _patch_authorities(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "_load_driver_authority",
        lambda repo_root: _driver_authority(),
    )
    monkeypatch.setattr(
        subject,
        "_load_platform_authority",
        lambda repo_root: _platform_authority(),
    )


def test_generate_validate_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authorities(monkeypatch)
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.status == "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_VALID"
    assert generated.implementation_status == "IMPLEMENTED_NOT_EXECUTED"


def test_notebook_is_deterministic_and_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authorities(monkeypatch)
    repo_root = _fixture_repo(tmp_path)

    first = subject.build_generated(repo_root)
    second = subject.build_generated(repo_root)

    assert first.notebook_bytes == second.notebook_bytes
    notebook = json.loads(first.notebook_bytes)
    assert len(notebook["cells"]) == 2
    assert notebook["cells"][1]["outputs"] == []
    assert notebook["cells"][1]["execution_count"] is None


def test_template_binds_exact_vllm_registry_and_class(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    program = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert subject.EXPECTED_BACKEND_PATH in program
    assert 'selected_backend = registry.AttentionBackendEnum["TRITON_ATTN"]' in program
    assert "selected_backend.is_overridden()" in program
    assert "selected_backend.get_path()" in program
    assert "selected_backend.get_class()" in program
    assert 'backend_class.get_name() != "TRITON_ATTN"' in program


def test_template_validates_t4_configuration(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    program = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert "DeviceCapability(major=7, minor=5)" in program
    assert "head_size=64" in program
    assert "dtype=torch.float16" in program
    assert 'kv_cache_dtype="auto"' in program
    assert "block_size=16" in program
    assert "AttentionType.DECODER" in program
    assert "validate_configuration(" in program


def test_template_attributes_one_model_free_primitive(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    program = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert subject.EXPECTED_PRIMITIVE_MODULE in program
    assert subject.EXPECTED_PRIMITIVE_NAME in program
    assert "backend_primitive is not source_primitive" in program
    assert "backend_primitive(" in program
    assert "torch.nn.functional.scaled_dot_product_attention" in program
    assert "ATTENTION_BACKEND_PRIMITIVE_PASSED" in program


def test_template_keeps_linker_realization_child_local(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    program = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert 'runtime_environment["LIBRARY_PATH"]' in program
    assert 'runtime_environment["LDFLAGS"]' in program
    assert 'runtime_environment["LD_LIBRARY_PATH"]' in program
    assert 'os.environ["LIBRARY_PATH"] =' not in program
    assert 'os.environ["LD_LIBRARY_PATH"] =' not in program


def test_template_has_no_model_worker_or_server_path(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    program = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    for prohibited in (
        "AutoModel",
        "AutoTokenizer",
        "api_server",
        "requests.get(",
        "urllib.request",
    ):
        assert prohibited not in program
    assert '"model_loads": 0' in program
    assert '"worker_starts": 0' in program
    assert '"model_requests": 0' in program


def test_request_has_exact_zero_activity_budgets() -> None:
    request = subject._request()

    assert request.maximum_sessions == 1
    assert request.maximum_runtime_install_attempts == 1
    assert request.maximum_backend_discovery_attempts == 1
    assert request.maximum_backend_import_attempts == 1
    assert request.maximum_attention_primitive_attempts == 1
    assert request.model_loads_permitted == 0
    assert request.worker_starts_permitted == 0
    assert request.model_requests_permitted == 0
    assert request.benchmark_trajectory_requests_permitted == 0
    assert request.network_requests_permitted == 0
    assert request.hidden_retries_permitted is False
    assert request.silent_backend_fallback_permitted is False


def test_failure_taxonomy_is_unique_and_boundary_specific() -> None:
    failures = subject._failure_contracts()
    codes = {failure.error_code for failure in failures}
    boundaries = {failure.first_boundary for failure in failures}

    assert len(codes) == len(failures)
    assert "ATTENTION_BACKEND_OVERRIDE_DETECTED" in codes
    assert "ATTENTION_BACKEND_FALLBACK_DETECTED" in codes
    assert "ATTENTION_BACKEND_RESULT_MISMATCH" in codes
    assert "backend_registry_override" in boundaries
    assert "pytorch_sdpa_comparison" in boundaries


def test_record_binds_consumed_authorities_without_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authorities(monkeypatch)
    repo_root = _fixture_repo(tmp_path)

    record = subject.build_generated(repo_root).record

    assert record.accepted_driver.saved_version_id == 339127349
    assert record.accepted_platform.saved_version_id == 339140121
    assert record.accepted_driver.unchanged_replay_authorized is False
    assert record.accepted_platform.unchanged_replay_authorized is False
    assert record.unchanged_upstream_replay_authorized is False


def test_record_issues_no_runtime_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authorities(monkeypatch)
    repo_root = _fixture_repo(tmp_path)

    record = subject.build_generated(repo_root).record

    assert record.runtime_execution_authorized is False
    assert record.safety.runtime_execution_authorization_issued is False
    assert record.safety.kaggle_execution_performed is False
    assert record.safety.gpu_execution_performed is False
    assert record.safety.runtime_installations_performed == 0
    assert record.safety.backend_imports_performed == 0
    assert record.safety.attention_primitive_attempts == 0
    assert record.next_gate == (
        "design_and_merge_explicit_triton_attention_backend_execution_authorization_v1"
    )


def test_template_is_compilable_and_line_bounded(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.TEMPLATE_PATH
    program = path.read_text(encoding="utf-8")

    compile(program, path.as_posix(), "exec")
    assert max(len(line) for line in program.splitlines()) <= 100


def test_generated_drift_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authorities(monkeypatch)
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    path = repo_root / subject.NOTEBOOK_PATH
    path.write_bytes(path.read_bytes() + b"drift")

    with pytest.raises(
        subject.ExplicitTritonAttentionBackendV1Error,
        match="differs from fresh rebuild",
    ):
        subject.validate(repo_root)


def test_live_runtime_authorization_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authorities(monkeypatch)
    repo_root = _fixture_repo(tmp_path)
    authorization = repo_root / subject.AUTHORIZATION_PATH
    authorization.parent.mkdir(parents=True, exist_ok=True)
    authorization.write_text("{}", encoding="utf-8")

    with pytest.raises(
        subject.ExplicitTritonAttentionBackendV1Error,
        match="authorization must remain absent",
    ):
        subject.build_generated(repo_root)


def test_names_and_output_contract_are_bounded() -> None:
    assert len(subject.NOTEBOOK_NAME) <= 50
    assert len(subject.FAILED_NOTEBOOK_NAME) <= 50
    assert len(subject.REQUIRED_OUTPUTS) == 8
    assert len(set(subject.REQUIRED_OUTPUTS)) == 8
