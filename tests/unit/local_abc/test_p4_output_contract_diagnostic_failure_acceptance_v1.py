from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest

from auragateway.local_abc import p4_output_contract_diagnostic_failure_acceptance_v1 as subject

EXPECTED_POLICY_SHA = "a9016731aa16db755b1af871fda8410b811e843b4b7b2cd163c87bd3fb195b43"


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    destination = tmp_path / "repo"
    destination.mkdir()

    policy = subject._load_policy(ROOT)

    paths = {
        subject.POLICY_PATH,
        subject.SOURCE_PATH,
        subject.TEST_PATH,
        subject.ADR_PATH,
        subject.REPORT_PATH,
        subject.RUNBOOK_PATH,
        subject.REVIEW_PATH,
        subject.RECORD_PATH,
    }

    paths.update(Path(receipt.path) for receipt in policy.evidence_receipts)
    paths.update(Path(receipt.path) for receipt in policy.repository_authorities)

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

    return destination


def test_policy_identity_is_pinned() -> None:
    assert subject.POLICY_SHA256 == EXPECTED_POLICY_SHA


def test_validate_evidence_accepts_governed_failure(repo_root: Path) -> None:
    result = subject.validate_evidence(repo_root)

    assert result["status"] == "P4_OUTPUT_CONTRACT_DIAGNOSTIC_FAILURE_EVIDENCE_V1_VALID"
    assert result["saved_version_id"] == 340622392
    assert result["first_divergence"] == "RUNTIME_IMPORT_CLOSURE_FAILED"
    assert result["root_cause_status"] == "UNRESOLVED"
    assert result["model_loads"] == 0
    assert result["worker_starts"] == 0
    assert result["model_requests"] == 0
    assert result["authorization_reusable"] is False
    assert result["unchanged_replay_authorized"] is False


def test_generate_and_validate_package_round_trip(repo_root: Path) -> None:
    generated = subject.generate(repo_root)
    validated = subject.validate_package(repo_root)

    assert generated["status"] == ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_GENERATED")
    assert validated["status"] == ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_VALID")
    assert validated["evidence_disposition"] == "ACCEPTED_DIAGNOSTIC_FAILURE"
    assert validated["root_cause_status"] == "UNRESOLVED"
    assert validated["runtime_execution_authorized"] is False
    assert validated["measured_abc_authorized"] is False


def test_review_selects_import_closure_diagnostic(repo_root: Path) -> None:
    subject.generate(repo_root)
    review = json.loads((repo_root / subject.REVIEW_PATH).read_text(encoding="utf-8"))

    assert review["next_gate"] == "design_and_merge_p4_runtime_import_closure_diagnostic_v1"
    assert review["root_cause_status"] == "UNRESOLVED"
    assert review["runtime_execution_authorized"] is False
    assert "OTHER_IMPORT_TIME_EXCEPTION" in review["unresolved_hypotheses"]


def test_record_binds_all_evidence_and_authorities(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    subject.generate(repo_root)
    record = json.loads((repo_root / subject.RECORD_PATH).read_text(encoding="utf-8"))

    assert len(record["evidence"]) == policy.evidence_receipt_count
    assert len(record["repository_authorities"]) == policy.repository_authority_count
    assert record["authorization_lifecycle_closed"] is True
    assert record["authorization_reusable"] is False
    assert record["unchanged_replay_authorized"] is False


def test_runtime_boundary_is_install_pass_then_import_failure(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    install_path = repo_root / policy.runtime_member_targets["runtime_install_report_v1.json"]
    import_path = repo_root / policy.runtime_member_targets["runtime_import_closure_report_v1.json"]
    worker_path = repo_root / policy.runtime_member_targets["worker_startup_report_v1.json"]

    install = json.loads(install_path.read_text(encoding="utf-8"))
    import_report = json.loads(import_path.read_text(encoding="utf-8"))
    worker = json.loads(worker_path.read_text(encoding="utf-8"))

    assert install["status"] == "PASSED"
    assert install["return_code"] == 0
    assert import_report["status"] == "FAILED"
    assert import_report["return_code"] == 1
    assert import_report["raw_import_output_retained"] is False
    assert worker["status"] == "NOT_RUN"


def test_request_matrix_was_not_executed(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    request_path = repo_root / policy.runtime_member_targets["request_results_v1.json"]
    selection_path = repo_root / policy.runtime_member_targets["selection_report_v1.json"]

    request = json.loads(request_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))

    assert request["scheduled_request_count"] == 18
    assert request["observed_request_count"] == 0
    assert request["status"] == "NOT_RUN"
    assert selection["status"] == "INELIGIBLE_PARTIAL_EVIDENCE"
    assert selection["selected_case_id"] is None


def test_authorization_is_consumed_and_not_reusable(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    consumption_path = repo_root / subject._evidence_path(
        policy,
        "execution_authorization_consumption_v2-340622392.json",
    )
    consumption = json.loads(consumption_path.read_text(encoding="utf-8"))

    assert consumption["lifecycle"] == "CONSUMED"
    assert consumption["outcome"] == "FAILED"
    assert consumption["saved_version_id"] == 340622392
    assert consumption["authorization_reusable"] is False


def test_operational_transient_paths_are_rejected(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    transient = repo_root / policy.operational_transient_paths[0]
    transient.parent.mkdir(parents=True, exist_ok=True)
    transient.write_text("{}\n", encoding="utf-8")

    with pytest.raises(subject.FailureAcceptanceError) as exc_info:
        subject.validate_evidence(repo_root)

    assert exc_info.value.error_code == "P4_FAILURE_ACCEPTANCE_TRANSIENT_PATH_PRESENT"


def test_tampered_runtime_summary_is_rejected(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    path = (
        repo_root / policy.runtime_member_targets["p4_output_contract_diagnostic_summary_v1.json"]
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["counters"]["model_requests"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(subject.FailureAcceptanceError) as exc_info:
        subject.validate_evidence(repo_root)

    assert exc_info.value.error_code == "P4_FAILURE_ACCEPTANCE_RECEIPT_DRIFT"


def test_tampered_terminal_log_is_rejected(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    path = repo_root / subject._evidence_path(
        policy,
        "ag-p4-output-contract-diagnostic-v1-340622392.log",
    )
    path.write_text("tampered\n", encoding="utf-8")

    with pytest.raises(subject.FailureAcceptanceError) as exc_info:
        subject.validate_evidence(repo_root)

    assert exc_info.value.error_code == "P4_FAILURE_ACCEPTANCE_RECEIPT_DRIFT"


def test_tampered_authorization_binding_is_rejected(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    path = repo_root / subject._evidence_path(
        policy,
        "execution_authorization_consumption_v2-340622392.json",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["authorization_sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(subject.FailureAcceptanceError) as exc_info:
        subject.validate_evidence(repo_root)

    assert exc_info.value.error_code == "P4_FAILURE_ACCEPTANCE_RECEIPT_DRIFT"


@pytest.mark.parametrize(
    "member",
    ["../escape.json", "/absolute.json", "C:/drive.json"],
)
def test_unsafe_zip_member_is_rejected(repo_root: Path, member: str) -> None:
    archive = repo_root / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(member, "{}")

    with pytest.raises(subject.FailureAcceptanceError) as exc_info:
        subject._safe_zip_members(archive)

    assert exc_info.value.error_code == "P4_FAILURE_ACCEPTANCE_ARCHIVE_UNSAFE"


def test_duplicate_normalized_zip_member_is_rejected(repo_root: Path) -> None:
    archive = repo_root / "duplicate.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("a/b.json", "{}")
        handle.writestr("a\\b.json", "{}")

    with pytest.raises(subject.FailureAcceptanceError) as exc_info:
        subject._safe_zip_members(archive)

    assert exc_info.value.error_code == "P4_FAILURE_ACCEPTANCE_ARCHIVE_DUPLICATE"


def test_review_does_not_claim_root_cause(repo_root: Path) -> None:
    subject.generate(repo_root)
    review = json.loads((repo_root / subject.REVIEW_PATH).read_text(encoding="utf-8"))
    text = json.dumps(review)

    assert review["root_cause_status"] == "UNRESOLVED"
    assert "The exact import exception is unknown." in review["non_claims"]
    assert "CUDA_ABI_FAILURE_CONFIRMED" not in text
    assert "VLLM_IMPORT_FAILURE_CONFIRMED" not in text


def test_raw_prompts_outputs_and_import_output_remain_excluded(repo_root: Path) -> None:
    policy = subject._load_policy(repo_root)
    summary_path = (
        repo_root / policy.runtime_member_targets["p4_output_contract_diagnostic_summary_v1.json"]
    )
    import_path = repo_root / policy.runtime_member_targets["runtime_import_closure_report_v1.json"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    import_report = json.loads(import_path.read_text(encoding="utf-8"))

    assert summary["raw_prompt_retained"] is False
    assert summary["raw_output_retained"] is False
    assert import_report["raw_import_output_retained"] is False
