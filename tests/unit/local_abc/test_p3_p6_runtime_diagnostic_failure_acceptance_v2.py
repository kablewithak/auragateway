from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

MODULE_RELATIVE = Path(
    "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v2.py"
)


def _load_subject(repo_root: Path) -> ModuleType:
    path = repo_root / MODULE_RELATIVE
    spec = importlib.util.spec_from_file_location("failure_acceptance_v2_subject", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _repo_from_candidate(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    destination = tmp_path / "repo"
    candidate_paths = (
        Path(
            "benchmarks/local_abc/"
            "auragateway_cu129_p3_p6_runtime_diagnostic_"
            "failure_acceptance_v2.json"
        ),
        Path(
            "benchmarks/local_abc/"
            "auragateway_cu129_p3_p6_runtime_diagnostic_"
            "failure_acceptance_v2_review.json"
        ),
        Path(
            "docs/adr/2026-08-01-local-abc-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v2.md"
        ),
        Path("docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_Failure_Acceptance_V2.md"),
        Path("docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v2.md"),
        Path("src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v2.py"),
        Path("tests/unit/local_abc/test_p3_p6_runtime_diagnostic_failure_acceptance_v2.py"),
    )
    for relative in candidate_paths:
        source = source_root / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    evidence_source = source_root / (
        "evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v2"
    )
    evidence_target = destination / (
        "evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v2"
    )
    shutil.copytree(evidence_source, evidence_target)
    return destination


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )


def test_validate_current_candidate(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    summary = subject.validate(repo)
    assert summary["root_cause_status"] == "CONFIRMED"
    assert summary["runtime_install_status"] == "PASSED"
    assert summary["failed_probe"] == "P3"


def test_generate_is_deterministic(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    first = subject.generate(repo)
    first_review = (repo / subject.REVIEW_PATH).read_bytes()
    first_record = (repo / subject.RECORD_PATH).read_bytes()
    second = subject.generate(repo)
    assert first == second
    assert (repo / subject.REVIEW_PATH).read_bytes() == first_review
    assert (repo / subject.RECORD_PATH).read_bytes() == first_record


def test_summary_counter_drift_fails(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["p3_p6_runtime_diagnostic_summary_v2.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["counters"]["model_requests"] = 1
    _write_json(path, payload)
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_install_status_drift_fails(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["runtime_install_report_v2.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "FAILED"
    _write_json(path, payload)
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_p4_must_remain_not_run(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["p4_deterministic_request_report_v2.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "FAILED"
    _write_json(path, payload)
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_worker_stdout_signature_is_required(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.WORKER_STDOUT_PATH
    path.write_text("truncated", encoding="utf-8")
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_worker_stderr_signature_is_required(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.WORKER_STDERR_PATH
    path.write_text("truncated", encoding="utf-8")
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_kaggle_terminal_signature_is_required(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.KAGGLE_LOG_PATH
    path.write_text("truncated", encoding="utf-8")
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_zip_member_set_is_exact(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.EVIDENCE_ZIP_PATH
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("unexpected.txt", "x")
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_queryable_member_must_match_zip(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["failure_report_v2.json"]
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_authorization_identity_is_exact(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.AUTHORIZATION_EVIDENCE_PATH
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_consumption_outcome_is_failed(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.CONSUMPTION_EVIDENCE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["outcome"] = "PASSED"
    _write_json(path, payload)
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_remediation_cannot_be_claimed_proven(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.ROOT_CAUSE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["remediation_proven"] = True
    _write_json(path, payload)
    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_first_divergence_is_exact(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    payload = json.loads((repo / subject.REVIEW_PATH).read_text(encoding="utf-8"))
    assert payload["first_divergence"] == (
        "TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"
    )


def test_no_runtime_authorization_is_created(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    subject.validate(repo)
    transient = repo / (
        "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_"
        "execution_authorization_v3.json"
    )
    assert not transient.exists()


def test_evidence_path_count_is_nineteen(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    assert len(subject._evidence_paths()) == 19


def test_record_rejects_replay(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    payload = json.loads((repo / subject.RECORD_PATH).read_text(encoding="utf-8"))
    assert payload["authorization_reusable"] is False
    assert payload["unchanged_replay_authorized"] is False


def test_review_preserves_nonclaims(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    payload = json.loads((repo / subject.REVIEW_PATH).read_text(encoding="utf-8"))
    assert len(payload["non_claims"]) >= 8
    assert "P3 worker readiness has not been established." in payload["non_claims"]
