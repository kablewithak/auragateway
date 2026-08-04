from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p3_p6_runtime_diagnostic_failure_acceptance_v4 as acceptance,
)


@pytest.fixture()
def candidate_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    static_paths = (
        acceptance.POLICY_PATH,
        acceptance.SOURCE_PATH,
        acceptance.TEST_PATH,
        acceptance.ADR_PATH,
        acceptance.REPORT_PATH,
        acceptance.RUNBOOK_PATH,
        acceptance.REVIEW_PATH,
        acceptance.RECORD_PATH,
    )
    for relative in static_paths:
        source = source_root / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    policy = acceptance._load_policy(source_root)
    for receipt in policy.evidence_receipts:
        relative = Path(receipt.path)
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, destination)

    monkeypatch.setenv("AURAGATEWAY_SYNTHETIC_FIXTURE", "1")
    return tmp_path


def _load_json(root: Path, relative: Path) -> dict[str, object]:
    payload = json.loads((root / relative).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_policy_identity_and_boundary(candidate_root: Path) -> None:
    policy = acceptance._load_policy(candidate_root)

    assert policy.saved_version_id == 340120168
    assert len(policy.evidence_receipts) == 25
    assert len(policy.intake_member_targets) == 25
    assert len(policy.runtime_member_targets) == 13
    assert len(policy.repository_authorities) == 6
    assert policy.first_divergence == ("P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH")


def test_exact_evidence_accepts(candidate_root: Path) -> None:
    result = acceptance.validate_evidence(candidate_root)

    assert result["status"] == ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V4_EVIDENCE_VALID")
    assert result["completed_probes"] == ["P3", "P4", "P5"]
    assert result["failed_probe"] == "P6"
    assert result["global_model_request_count"] == 4
    assert result["worker_1_completion_post_count"] == 2
    assert result["worker_2_completion_post_count"] == 0
    assert result["p6_terminal_stub_model_requests_performed"] is False


def test_generate_is_deterministic(candidate_root: Path) -> None:
    first = acceptance.generate(candidate_root)
    first_review = (candidate_root / acceptance.REVIEW_PATH).read_bytes()
    first_record = (candidate_root / acceptance.RECORD_PATH).read_bytes()

    second = acceptance.generate(candidate_root)
    second_review = (candidate_root / acceptance.REVIEW_PATH).read_bytes()
    second_record = (candidate_root / acceptance.RECORD_PATH).read_bytes()

    assert first["review_sha256"] == second["review_sha256"]
    assert first["record_sha256"] == second["record_sha256"]
    assert first_review == second_review
    assert first_record == second_record


def test_validate_package_accepts(candidate_root: Path) -> None:
    acceptance.generate(candidate_root)

    result = acceptance.validate_package(candidate_root)

    assert result["status"] == ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V4_VALID")
    assert result["lifecycle_outcome"] == "FAILED"
    assert result["authorization_lifecycle_closed"] is True
    assert result["authorization_reusable"] is False
    assert result["unchanged_replay_authorized"] is False
    assert result["runtime_execution_authorized"] is False
    assert result["next_gate"] == ("design_and_merge_p3_p6_runtime_diagnostic_v5")


def test_log_tamper_fails_closed(candidate_root: Path) -> None:
    policy = acceptance._load_policy(candidate_root)
    log_receipt = next(
        receipt
        for receipt in policy.evidence_receipts
        if receipt.path.endswith("ag-cu129-p3-p6-runtime-diagnostic-v4-340120168.log")
    )
    log_path = candidate_root / log_receipt.path
    log_path.write_bytes(log_path.read_bytes() + b"\nTAMPERED\n")

    with pytest.raises(acceptance.FailureAcceptanceError) as raised:
        acceptance.validate_evidence(candidate_root)

    assert raised.value.error_code == ("P3_P6_V4_FAILURE_ACCEPTANCE_EVIDENCE_HASH_MISMATCH")
    assert raised.value.path == log_receipt.path


def test_policy_tamper_fails_closed(candidate_root: Path) -> None:
    policy_path = candidate_root / acceptance.POLICY_PATH
    policy_path.write_bytes(policy_path.read_bytes() + b"\n")

    with pytest.raises(acceptance.FailureAcceptanceError) as raised:
        acceptance.validate_evidence(candidate_root)

    assert raised.value.error_code == ("P3_P6_V4_FAILURE_ACCEPTANCE_POLICY_DRIFT")


def test_review_preserves_precise_non_claims(candidate_root: Path) -> None:
    policy = acceptance._load_policy(candidate_root)
    review = acceptance.build_review(policy)

    assert review["formal_p3_acceptance_established"] is True
    assert review["p4_deterministic_inference_established"] is True
    assert review["p5_prefix_cache_reuse_established"] is True
    assert review["p5_full_process_reset_established"] is True
    assert review["p6_worker_1_route_request_attempted"] is True
    assert review["p6_worker_1_route_response_contract_passed"] is False
    assert review["p6_worker_2_route_request_executed"] is False
    assert review["p6_full_route_and_metric_isolation_established"] is False
    assert review["runtime_execution_authorized"] is False


def test_record_binds_evidence_without_authorizing_replay(
    candidate_root: Path,
) -> None:
    acceptance.generate(candidate_root)
    record = _load_json(candidate_root, acceptance.RECORD_PATH)

    assert record["saved_version_id"] == 340120168
    assert record["evidence_disposition"] == "ACCEPTED_DIAGNOSTIC_FAILURE"
    assert record["authorization_lifecycle_closed"] is True
    assert record["authorization_reusable"] is False
    assert record["unchanged_replay_authorized"] is False
    assert record["runtime_execution_authorized"] is False
    assert record["measured_abc_execution_established"] is False
    assert record["evidence_quality_defect_count"] == 3

    evidence = record["evidence"]
    authorities = record["repository_authorities"]
    assert isinstance(evidence, list)
    assert isinstance(authorities, list)
    assert len(evidence) == 25
    assert len(authorities) == 6


def test_intake_and_runtime_archives_are_byte_bound(
    candidate_root: Path,
) -> None:
    policy = acceptance._load_policy(candidate_root)

    acceptance._validate_intake_archive(candidate_root, policy)
    manifest = acceptance._validate_runtime_archive(
        candidate_root,
        policy,
    )

    assert len(manifest.members) == 12
    assert manifest.scratch_directories_included is False
    assert manifest.worker_log_directory_included is False


def test_cli_validate_package(candidate_root: Path) -> None:
    acceptance.generate(candidate_root)
    environment = {
        **os.environ,
        "AURAGATEWAY_SYNTHETIC_FIXTURE": "1",
        "PYTHONPATH": str(candidate_root / "src"),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            ("auragateway.local_abc.p3_p6_runtime_diagnostic_failure_acceptance_v4"),
            "validate-package",
            "--repo-root",
            str(candidate_root),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V4_VALID")


def test_operational_paths_are_separate_from_preserved_evidence(
    candidate_root: Path,
) -> None:
    policy = acceptance._load_policy(candidate_root)

    assert not (candidate_root / policy.operational_authorization_path).exists()
    assert not (candidate_root / policy.operational_consumption_path).exists()
    assert any(
        receipt.path.endswith("execution_authorization_v4-340120168.json")
        for receipt in policy.evidence_receipts
    )
    assert any(
        receipt.path.endswith("execution_authorization_consumption_v4-340120168.json")
        for receipt in policy.evidence_receipts
    )
