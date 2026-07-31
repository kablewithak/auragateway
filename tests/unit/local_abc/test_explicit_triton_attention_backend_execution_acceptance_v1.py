"""Tests for explicit Triton attention-backend execution acceptance V1."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    explicit_triton_attention_backend_execution_acceptance_v1 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    for relative in (
        subject.LOG_PATH,
        subject.EVIDENCE_ZIP_PATH,
        subject.AUTHORIZATION_EVIDENCE_PATH,
        subject.CONSUMPTION_EVIDENCE_PATH,
        subject.INSPECTION_MANIFEST_PATH,
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
    assert generated.status == ("EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_ACCEPTANCE_V1_VALID")


def test_saved_version_and_evidence_are_bound(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.saved_version.saved_version_id == 339181603
    assert record.saved_version.saved_version_url.endswith("scriptVersionId=339181603")
    assert record.saved_version.evidence_archive.sha256 == (subject.EVIDENCE_ZIP_SHA256)


def test_authorization_lifecycle_is_closed(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))
    lifecycle = record.authorization_lifecycle

    assert lifecycle.single_use is True
    assert lifecycle.outcome == "PASSED"
    assert lifecycle.authorization_reusable is False
    assert lifecycle.execution_evidence_within_authorization_window is True
    assert record.authorization_lifecycle_closed is True
    assert record.unchanged_replay_authorized is False


def test_explicit_backend_identity_is_accepted(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.backend.registry_enum == "AttentionBackendEnum.TRITON_ATTN"
    assert record.backend.backend_name == "TRITON_ATTN"
    assert record.backend.registry_overridden is False
    assert record.backend.all_origins_inside_target is True
    assert record.backend.vllm_version == "0.19.1"


def test_capability_and_primitive_are_exact(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.capability.attention_type == "decoder"
    assert record.capability.compute_capability == (7, 5)
    assert record.primitive.backend_owns_exact_primitive is True
    assert record.primitive.result_close is True
    assert record.primitive.maximum_absolute_error == 0.00048828125
    assert record.primitive.atol == 0.03
    assert record.primitive.rtol == 0.03
    assert record.primitive.causal is False


def test_primitive_numeric_contract_rejects_drift(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))
    payload = record.primitive.model_dump(mode="python")
    payload["atol"] = 0.04

    with pytest.raises(ValueError, match="primitive numerical contract drifted"):
        subject.PrimitiveContract.model_validate(payload)


def test_safety_and_next_gate_are_exact(tmp_path: Path) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.safety.runtime_install_attempts == 1
    assert record.safety.attention_primitive_attempts == 1
    assert record.safety.model_loads == 0
    assert record.safety.worker_starts == 0
    assert record.safety.model_requests == 0
    assert record.safety.benchmark_trajectory_requests == 0
    assert record.p3_p6_runtime_diagnostic_implementation_authorized is True
    assert record.next_gate == "design_and_implement_p3_p6_runtime_diagnostic_v1"


@pytest.mark.parametrize(
    ("relative", "expected_message"),
    (
        (subject.LOG_PATH, "identity drifted"),
        (subject.EVIDENCE_ZIP_PATH, "identity drifted"),
        (subject.AUTHORIZATION_EVIDENCE_PATH, "identity drifted"),
        (subject.CONSUMPTION_EVIDENCE_PATH, "identity drifted"),
        (subject.INSPECTION_MANIFEST_PATH, "identity drifted"),
    ),
)
def test_tampered_evidence_is_rejected(
    tmp_path: Path,
    relative: Path,
    expected_message: str,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / relative
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.AttentionBackendAcceptanceError,
        match=expected_message,
    ):
        subject.build_acceptance_record(repo_root)


@pytest.mark.parametrize(
    "transient",
    (
        subject.OPERATIONAL_AUTHORIZATION_PATH,
        subject.OPERATIONAL_CONSUMPTION_PATH,
    ),
)
def test_operational_transient_artifacts_are_rejected(
    tmp_path: Path,
    transient: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / transient
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(
        subject.AttentionBackendAcceptanceError,
        match="operational transient authorization artifacts must be absent",
    ):
        subject.build_acceptance_record(repo_root)
