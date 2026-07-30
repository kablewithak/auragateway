"""Tests for P0-P2 platform diagnostic execution acceptance V1."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p0_p2_platform_diagnostic_execution_acceptance_v1 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"

    for relative in (
        subject.LOG_PATH,
        subject.EVIDENCE_ZIP_PATH,
    ):
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    return repo_root


def test_generate_validate_round_trip(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.status == ("P0_P2_PLATFORM_DIAGNOSTIC_EXECUTION_ACCEPTANCE_V1_VALID")


def test_saved_version_and_archive_are_bound(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.saved_version.saved_version_id == 339140121
    assert record.saved_version.saved_version_url.endswith("scriptVersionId=339140121")
    assert record.saved_version.evidence_archive.sha256 == subject.EVIDENCE_ZIP_SHA256


def test_all_three_platform_gates_are_accepted(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.platform.decision == "P0_REAL_DRIVER_PREFLIGHT_PASSED"
    assert record.link.decision == ("EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED")
    assert record.triton.decision == "CURRENT_STACK_TRITON_PRIMITIVE_PASSED"


def test_governed_cu129_runtime_is_exact(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.triton.torch_version == "2.10.0+cu129"
    assert record.triton.torch_cuda_build == "12.9"
    assert record.triton.triton_version == "3.6.0"
    assert record.triton.result_exact is True
    assert record.triton.target_runtime_origins_exact is True


def test_action_boundary_linker_realization_is_accepted(
    tmp_path: Path,
) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.link.required_link_flags == subject.REQUIRED_LINK_FLAGS
    assert record.triton.command_local_library_path == subject.REAL_DRIVER_DIRECTORY
    assert record.triton.stub_not_selected is True
    assert record.triton.global_environment_mutation_absent is True


def test_safety_and_next_gate_are_exact(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.safety.model_loads == 0
    assert record.safety.worker_starts == 0
    assert record.safety.model_requests == 0
    assert record.safety.network_requests == 0
    assert record.full_triton_qualification_attempt_consumed is True
    assert record.unchanged_diagnostic_replay_authorized is False
    assert record.explicit_attention_backend_v1_implementation_authorized is True
    assert record.next_gate == ("design_and_implement_explicit_triton_attention_backend_v1")


def test_tampered_log_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.LOG_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.DiagnosticAcceptanceError,
        match="identity drifted",
    ):
        subject.build_acceptance_record(repo_root)


def test_tampered_archive_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.EVIDENCE_ZIP_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.DiagnosticAcceptanceError,
        match="identity drifted",
    ):
        subject.build_acceptance_record(repo_root)


def test_transient_authorization_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.AUTHORIZATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(
        subject.DiagnosticAcceptanceError,
        match="authorization must remain absent",
    ):
        subject.build_acceptance_record(repo_root)
