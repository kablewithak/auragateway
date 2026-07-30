"""Tests for the P0-P2 launcher source-authority remediation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p0_p2_execution_launcher_source_authority_remediation_v1 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    for relative in subject.BOUND_EVIDENCE_PATHS:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def test_generate_and_validate_round_trip(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)
    assert validated == generated


def test_failure_is_pre_probe_and_has_no_platform_conclusion(
    tmp_path: Path,
) -> None:
    record = subject.build_remediation_record(_fixture_repo(tmp_path))
    assert record.first_divergence == "source_output_discovery"
    assert record.safety.diagnostic_execution_attempts == 0
    assert record.safety.runtime_install_attempts == 0
    assert record.safety.kernel_compile_and_execution_attempts == 0
    assert record.platform_conclusion == "NONE"
    assert record.unchanged_rerun_authorized is False


def test_remediation_binds_accepted_not_stale_authority(
    tmp_path: Path,
) -> None:
    record = subject.build_remediation_record(_fixture_repo(tmp_path))
    assert record.accepted_bundle_manifest_sha256 == subject.ACCEPTED_BUNDLE_MANIFEST_SHA256
    assert record.stale_bundle_manifest_sha256 == subject.STALE_BUNDLE_MANIFEST_SHA256
    assert record.accepted_bundle_manifest_sha256 != record.stale_bundle_manifest_sha256


def test_tampered_failure_log_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    (repo_root / subject.FAILED_LOG_PATH).write_bytes(b"tampered")
    with pytest.raises(
        subject.P0P2LauncherSourceAuthorityRemediationError,
        match="identity",
    ):
        subject.build_remediation_record(repo_root)
