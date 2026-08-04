from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import (
    p3_p6_runtime_diagnostic_failure_acceptance_v5 as acceptance,
)

ROOT = Path(__file__).resolve().parents[3]


def _policy() -> acceptance.FailureAcceptancePolicy:
    return acceptance._load_policy(ROOT)


def _fixture_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    destination = tmp_path / "repo"
    destination.mkdir()

    policy = _policy()

    paths = {
        acceptance.POLICY_PATH,
        acceptance.SOURCE_PATH,
        acceptance.TEST_PATH,
        acceptance.ADR_PATH,
        acceptance.REPORT_PATH,
        acceptance.RUNBOOK_PATH,
        acceptance.REVIEW_PATH,
        acceptance.RECORD_PATH,
    }

    paths.update(Path(item.path) for item in policy.evidence_receipts)

    for relative in sorted(paths):
        source = ROOT / relative

        if not source.is_file():
            continue

        target = destination / relative
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        shutil.copy2(source, target)

    monkeypatch.setenv(
        "AURAGATEWAY_SYNTHETIC_FIXTURE",
        "1",
    )
    return destination


def _load_evidence(
    root: Path,
    suffix: str,
) -> dict[str, object]:
    policy = acceptance._load_policy(root)
    path = acceptance._evidence_path(
        policy,
        suffix,
    )
    payload = acceptance._read_json(
        root / path,
    )

    if not isinstance(payload, dict):
        raise AssertionError("evidence root must be an object")

    return cast(
        dict[str, object],
        payload,
    )


def test_policy_identity_is_pinned() -> None:
    assert acceptance._file_sha256(ROOT / acceptance.POLICY_PATH) == acceptance.POLICY_SHA256


def test_validate_evidence_accepts_governed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)

    result = acceptance.validate_evidence(root)

    assert result["status"] == "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V5_EVIDENCE_VALID"
    assert result["completed_probes"] == ["P3"]
    assert result["failed_probe"] == "P4"
    assert result["global_model_request_count"] == 1


def test_generate_and_validate_package_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    (root / acceptance.REVIEW_PATH).unlink(missing_ok=True)
    (root / acceptance.RECORD_PATH).unlink(missing_ok=True)

    generated = acceptance.generate(root)
    validated = acceptance.validate_package(root)

    assert generated["runtime_execution_authorized"] is False
    assert validated["evidence_disposition"] == "ACCEPTED_DIAGNOSTIC_FAILURE"
    assert validated["unchanged_replay_authorized"] is False


def test_probe_sequence_is_p3_then_p4_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    result = acceptance.validate_evidence(root)

    assert result["completed_probes"] == ["P3"]
    assert result["failed_probe"] == "P4"
    assert result["p5_status"] == "NOT_RUN"
    assert result["p6_status"] == "NOT_RUN"


def test_authorization_is_consumed_and_not_reusable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    result = acceptance.validate_evidence(root)

    assert result["authorization_lifecycle"] == "CONSUMED"
    assert result["authorization_reusable"] is False


def test_layer_1_inspection_performed_no_model_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    receipt = _load_evidence(
        root,
        "layer_1_inspection_validation_receipt_v1-340232886.json",
    )

    assert receipt["status"] == "PASSED"
    assert receipt["model_loads"] == 0
    assert receipt["worker_starts"] == 0
    assert receipt["model_requests"] == 0
    assert receipt["network_requests"] == 0


def test_root_cause_classification_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    root_cause = _load_evidence(
        root,
        "root_cause_analysis_v5-340227787.json",
    )

    assert root_cause["primary_classification"] == "P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS"
    assert (
        root_cause["specific_classification"]
        == "V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION"
    )
    assert root_cause["confidence"] == "HIGH_CAUSAL_CLASSIFICATION_NOT_COUNTERFACTUAL_PROOF"


def test_model_and_wheelhouse_corruption_are_rejected_causes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(
        tmp_path,
        monkeypatch,
    )
    root_cause = _load_evidence(
        root,
        "root_cause_analysis_v5-340227787.json",
    )

    rejected_value = root_cause["rejected_root_causes"]

    assert isinstance(
        rejected_value,
        list,
    )
    assert all(isinstance(item, str) for item in rejected_value)

    rejected = set(
        cast(
            list[str],
            rejected_value,
        )
    )

    assert "MODEL_SNAPSHOT_CORRUPTION" in rejected
    assert "WHEELHOUSE_CORRUPTION" in rejected
    assert "TOP_K_FILTERING_UNDER_TEMPERATURE_ZERO" in rejected


def test_review_does_not_authorize_execution() -> None:
    policy = acceptance._load_policy(ROOT)
    review = acceptance.build_review(policy)

    assert review["runtime_execution_authorized"] is False
    assert review["measured_abc_execution_established"] is False
    assert review["unchanged_replay_authorized"] is False


def test_review_selects_output_contract_diagnostic() -> None:
    policy = acceptance._load_policy(ROOT)
    review = acceptance.build_review(policy)

    assert review["next_gate"] == "design_and_merge_p4_output_contract_diagnostic_v1"

    non_claims_value = review["non_claims"]

    assert isinstance(
        non_claims_value,
        list,
    )
    assert all(isinstance(item, str) for item in non_claims_value)

    non_claims = cast(
        list[str],
        non_claims_value,
    )

    assert "JSON-schema compatibility with the pinned runtime is not established." in non_claims


def test_record_contains_all_evidence_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(
        tmp_path,
        monkeypatch,
    )
    policy = acceptance._load_policy(root)

    acceptance._write_json(
        root / acceptance.REVIEW_PATH,
        acceptance.build_review(policy),
    )

    record = acceptance.build_record(
        root,
        policy,
        [],
    )

    evidence_value = record["evidence"]

    assert isinstance(
        evidence_value,
        list,
    )
    assert len(evidence_value) == policy.evidence_receipt_count
    assert record["completed_probes"] == ["P3"]
    assert record["failed_probe"] == "P4"


def test_windows_zip_member_is_normalized() -> None:
    assert (
        acceptance._normalize_zip_name(r"metadata\saved_version_and_disposition.txt")
        == "metadata/saved_version_and_disposition.txt"
    )


@pytest.mark.parametrize(
    "member",
    (
        "../escape.json",
        "/absolute.json",
        "C:/drive.json",
        "safe/../../escape.json",
        "",
    ),
)
def test_unsafe_zip_member_is_rejected(member: str) -> None:
    with pytest.raises(acceptance.FailureAcceptanceError):
        acceptance._normalize_zip_name(member)


def test_duplicate_normalized_zip_members_are_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(r"metadata\receipt.json", b"first")
        archive.writestr("metadata/receipt.json", b"second")

    with (
        zipfile.ZipFile(archive_path) as archive,
        pytest.raises(acceptance.FailureAcceptanceError),
    ):
        acceptance._safe_zip_members(
            archive,
            Path("duplicate.zip"),
        )


def test_tampered_runtime_summary_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    policy = acceptance._load_policy(root)
    path = Path(policy.runtime_member_targets["p3_p6_runtime_diagnostic_summary_v5.json"])
    payload = json.loads((root / path).read_text(encoding="utf-8"))
    payload["failed_probe"] = "P5"
    (root / path).write_text(
        json.dumps(payload, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(acceptance.FailureAcceptanceError) as captured:
        acceptance.validate_evidence(root)

    assert captured.value.error_code == "P3_P6_V5_FAILURE_ACCEPTANCE_EVIDENCE_HASH_MISMATCH"


def test_tampered_terminal_log_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    policy = acceptance._load_policy(root)
    path = acceptance._evidence_path(
        policy,
        "ag-cu129-p3-p6-runtime-diagnostic-v5-340227787.log",
    )
    with (root / path).open("a", encoding="utf-8") as handle:
        handle.write("tampered\n")

    with pytest.raises(acceptance.FailureAcceptanceError) as captured:
        acceptance.validate_evidence(root)

    assert captured.value.error_code == "P3_P6_V5_FAILURE_ACCEPTANCE_EVIDENCE_HASH_MISMATCH"


def test_p4_failure_report_preserves_safe_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    failure = _load_evidence(
        root,
        "failure_report_v5-340227787.json",
    )

    assert failure["failed_probe"] == "P4"
    assert failure["error_code"] == "P3_P6_REQUEST_FAILED"
    assert failure["safe_message"] == "model response is not valid JSON"
    assert failure["teardown_status"] == "PASSED"


def test_p6_checkpoint_proves_not_started(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    checkpoint = _load_evidence(
        root,
        "p6_stage_checkpoint_report_v5-340227787.json",
    )

    assert checkpoint["status"] == "NOT_RUN"
    assert checkpoint["current_stage"] == "P6_NOT_STARTED"
    assert checkpoint["events"] == []
    assert checkpoint["worker_request_counters"] == {
        "worker_1": {"attempted": 0, "completed": 0},
        "worker_2": {"attempted": 0, "completed": 0},
    }


def test_raw_prompt_and_output_remain_excluded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    p4 = _load_evidence(
        root,
        "p4_deterministic_request_report_v5-340227787.json",
    )

    assert p4["raw_prompt_logged"] is False
    assert p4["raw_output_logged"] is False


def test_layer_2_is_not_presented_as_counterfactual_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(
        tmp_path,
        monkeypatch,
    )
    root_cause = _load_evidence(
        root,
        "root_cause_analysis_v5-340227787.json",
    )

    confidence_value = root_cause["confidence"]

    assert isinstance(
        confidence_value,
        str,
    )
    assert "NOT_COUNTERFACTUAL_PROOF" in confidence_value
    assert root_cause["unchanged_replay_authorized"] is False


def test_operational_transient_paths_are_not_candidate_evidence() -> None:
    policy = acceptance._load_policy(ROOT)
    evidence_paths = {item.path for item in policy.evidence_receipts}

    assert policy.operational_authorization_path not in evidence_paths
    assert policy.operational_consumption_path not in evidence_paths
