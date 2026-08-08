from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p5_p6_successor_unauthorized_execution_reconciliation_v2 as recon,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _copy_repo_file(source_root: Path, target_root: Path, relative: Path) -> None:
    source = source_root / relative
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


@pytest.fixture
def candidate_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    paths = (
        recon.AUTHORIZATION_RECORD_PATH,
        recon.AUTHORIZATION_REVIEW_PATH,
        recon.RUNTIME_RECORD_PATH,
        recon.RUNTIME_REVIEW_PATH,
        recon.RUNTIME_REQUEST_PATH,
        recon.AUTHORIZATION_SOURCE_PATH,
        recon.RUNTIME_SOURCE_PATH,
        recon.SOURCE_PATH,
        recon.TEST_PATH,
        recon.ADR_PATH,
        recon.REPORT_PATH,
        recon.RUNBOOK_PATH,
    )
    for path in paths:
        _copy_repo_file(source_root, tmp_path, path)
    monkeypatch.setattr(recon, "_require_source_main_ancestor", lambda repo_root: None)
    return tmp_path


def test_governance_disposition_never_promotes_technical_pass() -> None:
    disposition = recon._governance()

    assert disposition.authorization_lineage_status == "UNESTABLISHED_AT_EXECUTION"
    assert disposition.governed_acceptance_status == "INVALID_UNGOVERNED_EXECUTION"
    assert disposition.current_line_p5_pass_accepted is False
    assert disposition.current_line_p6_pass_accepted is False
    assert disposition.measured_abc_eligible is False
    assert disposition.measured_abc_execution_authorized is False
    assert disposition.retroactive_authorization_permitted is False


def test_technical_evidence_binds_exact_saved_version_and_runtime() -> None:
    evidence = recon._technical_evidence()

    assert evidence.saved_version_id == 340962890
    assert evidence.executed_runtime_script_sha256 == recon.RUNTIME_SCRIPT_SHA256
    assert evidence.evidence_zip_sha256 == recon.EVIDENCE_ZIP_SHA256
    assert evidence.technical_status == "PASSED"
    assert evidence.completed_probes == ("P3", "P4", "P5", "P6")
    assert evidence.model_requests == 5
    assert evidence.benchmark_trajectory_requests == 0


def test_technical_evidence_preserves_p5_cache_reset_observations() -> None:
    evidence = recon._technical_evidence()

    assert evidence.p5_cold_cached_prefix_tokens == 0
    assert evidence.p5_warm_cached_prefix_tokens == 736
    assert evidence.p5_post_restart_cached_prefix_tokens == 0
    assert evidence.p5_cold_new_prefill_tokens == 747
    assert evidence.p5_warm_new_prefill_tokens == 11
    assert evidence.p5_post_restart_new_prefill_tokens == 747
    assert evidence.p5_full_process_restart_proven is True


def test_technical_evidence_preserves_p6_route_isolation_observations() -> None:
    evidence = recon._technical_evidence()

    assert evidence.p6_worker_1_prompt_delta == 747
    assert evidence.p6_worker_1_non_target_prompt_delta == 0
    assert evidence.p6_worker_2_prompt_delta == 747
    assert evidence.p6_worker_2_non_target_prompt_delta == 0
    assert evidence.p6_model_semantics_used_as_route_proof is False


def test_generate_is_deterministic(candidate_repo: Path) -> None:
    first = recon.generate(candidate_repo)
    review_first = (candidate_repo / recon.REVIEW_PATH).read_bytes()
    record_first = (candidate_repo / recon.RECORD_PATH).read_bytes()

    second = recon.generate(candidate_repo)
    review_second = (candidate_repo / recon.REVIEW_PATH).read_bytes()
    record_second = (candidate_repo / recon.RECORD_PATH).read_bytes()

    assert first == second
    assert review_first == review_second
    assert record_first == record_second


def test_validate_implementation_preserves_governance_boundary(
    candidate_repo: Path,
) -> None:
    recon.generate(candidate_repo)

    result = recon.validate_implementation(candidate_repo)

    assert result["technical_status"] == "PASSED"
    assert result["governed_acceptance_status"] == "INVALID_UNGOVERNED_EXECUTION"
    assert result["authorization_lineage_status"] == "UNESTABLISHED_AT_EXECUTION"
    assert result["current_line_p5_pass_accepted"] is False
    assert result["current_line_p6_pass_accepted"] is False
    assert result["measured_abc_eligible"] is False
    assert result["runtime_execution_authorized"] is False


def test_validate_implementation_rejects_record_drift(candidate_repo: Path) -> None:
    recon.generate(candidate_repo)
    record_path = candidate_repo / recon.RECORD_PATH
    record_path.write_text(
        record_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(recon.ReconciliationError) as captured:
        recon.validate_implementation(candidate_repo)

    assert captured.value.error_code == "P5_P6_RECONCILIATION_STATIC_ARTIFACT_NOT_CANONICAL"


def test_bound_repo_authority_drift_fails_closed(candidate_repo: Path) -> None:
    path = candidate_repo / recon.RUNTIME_REQUEST_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(recon.ReconciliationError) as captured:
        recon._require_expected_repo_authorities(candidate_repo)

    assert captured.value.error_code == "P5_P6_RECONCILIATION_SOURCE_AUTHORITY_DRIFT"


def _summary_payload() -> bytes:
    return json.dumps(
        {
            "status": "PASSED",
            "terminal_decision": "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1_PASSED",
            "executed_runtime_script_sha256": recon.RUNTIME_SCRIPT_SHA256,
            "failed_probe": None,
            "failure_code": None,
            "measured_abc_execution_performed": False,
            "network_access_permitted": False,
            "worker_teardown_status": "PASSED",
            "scratch_cleanup_status": "PASSED",
            "scratch_exists_after_cleanup": False,
            "completed_probes": ["P3", "P4", "P5", "P6"],
            "counters": {
                "benchmark_trajectory_requests": 0,
                "external_spend": 0,
                "hidden_retries": 0,
                "kaggle_sessions": 1,
                "model_loads": 3,
                "model_requests": 5,
                "network_requests": 0,
                "runtime_import_closure_probes": 1,
                "runtime_install_attempts": 1,
                "worker_starts": 3,
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _p5_payload(*, warm_cached: float = 736.0) -> bytes:
    def request(cached: float, prefill: float) -> dict[str, object]:
        return {
            "metric_delta": {
                "cached_prefix_tokens": cached,
                "newly_computed_prefill_tokens": prefill,
            }
        }

    return json.dumps(
        {
            "status": "PASSED",
            "full_process_restart_reset_proven": True,
            "namespace_only_reset_used": False,
            "cold_request": request(0.0, 747.0),
            "warm_request": request(warm_cached, 11.0),
            "post_reset_request": request(0.0, 747.0),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _p6_payload() -> bytes:
    def request(port: int, target_prompt: float) -> dict[str, object]:
        return {
            "port": port,
            "route_acknowledged": True,
            "route_acknowledgement_source": "HARNESS_TRANSPORT_AND_METRICS",
            "target_metric_delta": {"prompt_tokens": target_prompt},
            "non_target_metric_delta": {"prompt_tokens": 0.0},
        }

    return json.dumps(
        {
            "status": "PASSED",
            "model_semantics_used_as_route_proof": False,
            "route_and_metric_isolation": {
                "request_counters_reconciled": True,
                "worker_1_request": request(8001, 747.0),
                "worker_2_request": request(8002, 747.0),
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _teardown_payload() -> bytes:
    return json.dumps(
        {
            "status": "PASSED",
            "all_ports_closed": True,
            "all_gpu_processes_absent": True,
            "all_capture_threads_finalized": True,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _external_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    warm_cached: float = 736.0,
) -> tuple[Path, Path]:
    members = {
        "p5_p6_successor_runtime_qualification_summary_v1.json": _summary_payload(),
        "p5_prefix_cache_reset_report_v1.json": _p5_payload(warm_cached=warm_cached),
        "p6_dual_worker_isolation_report_v1.json": _p6_payload(),
        "worker_teardown_report_v1.json": _teardown_payload(),
    }
    evidence_zip = tmp_path / "evidence.zip"
    with zipfile.ZipFile(evidence_zip, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)

    terminal = (
        '{"executed_runtime_script_sha256":"'
        + recon.RUNTIME_SCRIPT_SHA256
        + '","measured_abc_execution_performed":false,'
        + '"model_requests":5,"status":"PASSED",'
        + '"terminal_decision":"P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1_PASSED"}'
    ).encode()
    terminal_log = tmp_path / "run.log"
    terminal_log.write_bytes(terminal)

    expected_members = tuple(
        (name, _sha256(payload), len(payload)) for name, payload in members.items()
    )
    monkeypatch.setattr(recon, "EXPECTED_EVIDENCE_MEMBERS", expected_members)
    monkeypatch.setattr(recon, "EVIDENCE_ZIP_SHA256", _sha256(evidence_zip.read_bytes()))
    monkeypatch.setattr(recon, "EVIDENCE_ZIP_SIZE_BYTES", evidence_zip.stat().st_size)
    monkeypatch.setattr(recon, "TERMINAL_LOG_SHA256", _sha256(terminal))
    monkeypatch.setattr(recon, "TERMINAL_LOG_SIZE_BYTES", len(terminal))
    return evidence_zip, terminal_log


def test_verify_evidence_accepts_exact_technical_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_zip, terminal_log = _external_fixture(tmp_path, monkeypatch)

    result = recon.verify_evidence(evidence_zip, terminal_log)

    assert result["technical_status"] == "PASSED"
    assert result["governed_acceptance_status"] == "INVALID_UNGOVERNED_EXECUTION"
    assert result["measured_abc_eligible"] is False


def test_verify_evidence_rejects_external_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_zip, terminal_log = _external_fixture(tmp_path, monkeypatch)
    evidence_zip.write_bytes(evidence_zip.read_bytes() + b"x")

    with pytest.raises(recon.ReconciliationError) as captured:
        recon.verify_evidence(evidence_zip, terminal_log)

    assert captured.value.error_code == "P5_P6_RECONCILIATION_EXTERNAL_EVIDENCE_IDENTITY_MISMATCH"


def test_verify_evidence_rejects_semantic_metric_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_zip, terminal_log = _external_fixture(
        tmp_path,
        monkeypatch,
        warm_cached=735.0,
    )

    with pytest.raises(recon.ReconciliationError) as captured:
        recon.verify_evidence(evidence_zip, terminal_log)

    assert captured.value.error_code == "P5_P6_RECONCILIATION_EVIDENCE_SEMANTICS_MISMATCH"


def test_safe_member_name_rejects_parent_traversal() -> None:
    with pytest.raises(recon.ReconciliationError) as captured:
        recon._safe_member_name("../evidence.json")

    assert captured.value.error_code == "P5_P6_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE"


def test_cli_validate_result_never_authorizes_runtime(
    candidate_repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recon.generate(candidate_repo)

    exit_code = recon.main(
        [
            "validate-implementation",
            "--repo-root",
            str(candidate_repo),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["runtime_execution_authorized"] is False
    assert payload["measured_abc_execution_authorized"] is False
