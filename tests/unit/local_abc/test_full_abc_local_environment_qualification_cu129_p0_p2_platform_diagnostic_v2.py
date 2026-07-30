"""Tests for the governed CUDA 12.9 P0-P2 platform diagnostic V2."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_p0_p2_platform_diagnostic_v2 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    source = source_root / subject.TEMPLATE_PATH
    target = repo_root / subject.TEMPLATE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return repo_root


def _authority() -> subject.AcceptedProbeAuthority:
    return subject.AcceptedProbeAuthority(
        status=("EXPLICIT_DRIVER_LINK_PROBE_EXECUTION_ACCEPTANCE_V1_VALID"),
        saved_version_id=339127349,
        evidence_zip_sha256=subject.ACCEPTED_EVIDENCE_ZIP_SHA256,
        notebook_sha256=subject.ACCEPTED_NOTEBOOK_SHA256,
        link_decision=("EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"),
        required_link_flags=subject.REQUIRED_LINK_FLAGS,
        selected_link_library=subject.REAL_DRIVER_RESOLVED_PATH,
        runtime_library_path=subject.RUNTIME_DRIVER_PATH,
        cu_init_zero=True,
        stub_rejected=True,
        global_environment_mutation_required=False,
        p0_p2_v2_authorized=True,
        unchanged_replay_authorized=False,
        next_gate=("design_and_implement_p0_p2_platform_diagnostic_v2"),
    )


def _patch_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "_load_acceptance_authority",
        lambda repo_root: _authority(),
    )


def test_generate_validate_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authority(monkeypatch)
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.status == "P0_P2_PLATFORM_DIAGNOSTIC_V2_VALID"


def test_notebook_is_deterministic_and_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authority(monkeypatch)
    repo_root = _fixture_repo(tmp_path)

    first = subject.build_generated(repo_root)
    second = subject.build_generated(repo_root)

    assert first.notebook_bytes == second.notebook_bytes
    notebook = json.loads(first.notebook_bytes)
    assert len(notebook["cells"]) == 2
    assert notebook["cells"][1]["outputs"] == []
    assert notebook["cells"][1]["execution_count"] is None


def test_p1_template_uses_accepted_explicit_contract(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    program = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    for flag in subject.REQUIRED_LINK_FLAGS:
        assert flag in program

    assert "readelf" in program
    assert "libcuda.so.1" in program
    assert "cu_init_zero" in program
    assert "/usr/local/cuda/lib64/stubs" in program


def test_p2_is_gated_after_p0_and_p1(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    program = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    main_start = program.index("def main()")
    main_program = program[main_start:]
    p0_call = main_program.index("p0_platform_identity()")
    p1_call = main_program.index("p1_explicit_driver_link()")
    p2_call = main_program.index("p2_minimal_triton()")

    assert p0_call < p1_call < p2_call
    assert "if not p0_passed" in main_program
    assert "if not p1_passed" in main_program


def test_internal_linker_realization_is_child_local(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    program = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert 'runtime_environment["LIBRARY_PATH"]' in program
    assert 'runtime_environment["LDFLAGS"]' in program
    assert 'os.environ["LIBRARY_PATH"] =' not in program
    assert 'os.environ["LD_LIBRARY_PATH"] =' not in program


def test_request_has_exact_execution_budget() -> None:
    request = subject._request()

    assert request.attached_inputs_required == 1
    assert request.maximum_runtime_install_attempts == 1
    assert request.maximum_kernel_compile_and_execution_attempts == 1
    assert request.model_loads_permitted == 0
    assert request.worker_starts_permitted == 0
    assert request.model_requests_permitted == 0
    assert request.network_requests_permitted == 0
    assert request.hidden_retries_permitted is False


def test_review_preserves_v1_and_rejects_stubs() -> None:
    review = subject._review()

    assert "preserve_platform_diagnostic_v1" in review.architecture_requirements
    assert "cuda_toolkit_stub_linking" in review.rejected_alternatives
    assert "global_library_path_mutation" in review.rejected_alternatives


def test_record_authorizes_only_post_merge_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authority(monkeypatch)
    repo_root = _fixture_repo(tmp_path)

    record = subject.build_generated(repo_root).record

    assert record.implementation_status == "IMPLEMENTED_NOT_EXECUTED"
    assert record.execution_authorized_after_merge is True
    assert record.unchanged_kaggle_replay_authorized is False
    assert record.safety.kaggle_execution_performed is False
    assert record.next_gate == ("execute_governed_p0_p2_platform_diagnostic_v2")


def test_generated_drift_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_authority(monkeypatch)
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    path = repo_root / subject.NOTEBOOK_PATH
    path.write_bytes(path.read_bytes() + b"drift")

    with pytest.raises(
        subject.P0P2PlatformDiagnosticV2Error,
        match="differs from fresh rebuild",
    ):
        subject.validate(repo_root)


def test_names_and_output_contract_are_bounded() -> None:
    assert len(subject.NOTEBOOK_NAME) <= 50
    assert len(subject.FAILED_NOTEBOOK_NAME) <= 50
    assert len(subject.REQUIRED_OUTPUTS) == 6
    assert len(set(subject.REQUIRED_OUTPUTS)) == 6
