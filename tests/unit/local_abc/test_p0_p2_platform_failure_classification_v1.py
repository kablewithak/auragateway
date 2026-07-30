"""Tests for the P0-P2 platform failure classification record."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import auragateway.local_abc.p0_p2_platform_failure_classification_v1 as subject


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    for relative in subject.BOUND_EVIDENCE_PATHS:
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


def test_classification_distinguishes_link_search_from_driver_absence(
    tmp_path: Path,
) -> None:
    record = subject.build_classification_record(_fixture_repo(tmp_path))
    assert record.p0.real_driver_link_path == subject.REAL_DRIVER_LINK_PATH
    assert record.p0.torch_cuda_available is True
    assert record.p1.failure_stage == "cuda_driver_link"
    assert record.p1.explicit_driver_link_directory_present is False
    assert record.driver_absent_claimed is False
    assert record.platform_incompatible_claimed is False


def test_triton_was_not_executed(tmp_path: Path) -> None:
    record = subject.build_classification_record(_fixture_repo(tmp_path))
    assert record.p2.status == "NOT_RUN_DUE_TO_PRIOR_FAILURE"
    assert record.p2.attempts == 0
    assert record.safety.kernel_compile_and_execution_attempts == 0
    assert record.triton_incompatible_claimed is False


def test_probe_v2_recommendation_is_not_execution_authority(
    tmp_path: Path,
) -> None:
    record = subject.build_classification_record(_fixture_repo(tmp_path))
    recommendation = record.recommended_probe_v2
    assert recommendation.status == "DESIGN_RECOMMENDATION_NOT_EXECUTED"
    assert recommendation.prohibit_cuda_toolkit_stub is True
    assert recommendation.global_environment_mutation_permitted is False
    assert recommendation.gpu_replay_authorized is False


def test_tampered_platform_evidence_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    target = repo_root / subject.PLATFORM_EVIDENCE_PATH
    target.write_bytes(target.read_bytes() + b"tampered")
    with pytest.raises(
        subject.P0P2PlatformFailureClassificationError,
        match="identity drifted",
    ):
        subject.build_classification_record(repo_root)
