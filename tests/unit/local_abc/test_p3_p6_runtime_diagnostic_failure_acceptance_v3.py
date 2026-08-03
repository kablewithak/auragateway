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
    "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v3.py"
)


def _load_subject(repo_root: Path) -> ModuleType:
    path = repo_root / MODULE_RELATIVE
    spec = importlib.util.spec_from_file_location(
        "failure_acceptance_v3_subject",
        path,
    )
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
            "failure_acceptance_v3.json"
        ),
        Path(
            "benchmarks/local_abc/"
            "auragateway_cu129_p3_p6_runtime_diagnostic_"
            "failure_acceptance_v3_review.json"
        ),
        Path(
            "docs/adr/2026-08-03-local-abc-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v3.md"
        ),
        Path("docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_Failure_Acceptance_V3.md"),
        Path("docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v3.md"),
        Path("notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v3.ipynb"),
        Path("src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v3.py.tmpl"),
        MODULE_RELATIVE,
        Path("tests/unit/local_abc/test_p3_p6_runtime_diagnostic_failure_acceptance_v3.py"),
    )
    for relative in candidate_paths:
        source = source_root / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    evidence_source = source_root / (
        "evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v3"
    )
    evidence_target = destination / (
        "evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v3"
    )
    shutil.copytree(evidence_source, evidence_target)
    return destination


def _write_json(
    path: Path,
    payload: dict[str, object],
) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_validate_current_candidate(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)

    result = subject.validate(repo)

    assert result["lifecycle_outcome"] == "FAILED"
    assert result["evidence_disposition"] == ("QUARANTINED_INVALID_DIAGNOSTIC")
    assert result["worker_readiness_established"] is True
    assert result["formal_p3_acceptance_established"] is False


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


def test_summary_request_counter_drift_fails(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["p3_p6_runtime_diagnostic_summary_v3.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["counters"]["model_requests"] = 1
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_import_closure_status_drift_fails(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["runtime_import_closure_report_v3.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "FAILED"
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_p4_must_remain_not_run(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["p4_deterministic_request_report_v3.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "FAILED"
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_backend_marker_is_required(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["failure_report_v3.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    diagnostics = payload["worker_1_diagnostics"]
    diagnostics["stdout_tail"] = diagnostics["stdout_tail"].replace(
        subject.EXPECTED_BACKEND_MARKER, ""
    )
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_cli_echo_alone_is_not_backend_proof(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["failure_report_v3.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    diagnostics = payload["worker_1_diagnostics"]
    assert "'attention_backend': 'TRITON_ATTN'" in diagnostics["stdout_tail"]
    diagnostics["stdout_tail"] = diagnostics["stdout_tail"].replace(
        subject.EXPECTED_BACKEND_MARKER, ""
    )
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_reviewed_predicate_is_exact(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_TEMPLATE_PATH
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            subject.EXPECTED_PREDICATE,
            'return "triton_attn" in text',
        ),
        encoding="utf-8",
    )

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_runtime_health_signature_is_required(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["failure_report_v3.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    diagnostics = payload["worker_1_diagnostics"]
    diagnostics["stdout_tail"] = diagnostics["stdout_tail"].replace(
        'GET /health HTTP/1.1" 200 OK', ""
    )
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_stream_truncation_is_rejected(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["failure_report_v3.json"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["worker_1_diagnostics"]["stdout"]["retained_bytes"] -= 1
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_runtime_zip_member_set_is_exact(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.EVIDENCE_ZIP_PATH

    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("unexpected.txt", "x")

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_queryable_member_matches_runtime_zip(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.RUNTIME_MEMBER_PATHS["failure_report_v3.json"]
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_intake_archive_identity_is_exact(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.INTAKE_ARCHIVE_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_authorization_identity_is_exact(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.AUTHORIZATION_EVIDENCE_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_consumption_must_remain_failed(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.CONSUMPTION_EVIDENCE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["outcome"] = "PASSED"
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_formal_p3_cannot_be_claimed(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    path = repo / subject.ROOT_CAUSE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["formal_p3_acceptance_established"] = True
    _write_json(path, payload)

    with pytest.raises(subject.FailureAcceptanceError):
        subject.validate(repo)


def test_executed_notebook_identity_remains_unverified(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    payload = json.loads((repo / subject.REVIEW_PATH).read_text(encoding="utf-8"))

    assert payload["executed_notebook_source_identity_verified"] is False


def test_first_divergence_is_exact(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    payload = json.loads((repo / subject.REVIEW_PATH).read_text(encoding="utf-8"))

    assert payload["first_divergence"] == (
        "BACKEND_MARKER_PREDICATE_INCOMPATIBLE_WITH_PINNED_VLLM_0_19_1_RUNTIME_MARKER"
    )


def test_evidence_path_count_is_twenty_two(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)

    assert len(subject._evidence_paths()) == 22


def test_record_rejects_replay(tmp_path: Path) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    payload = json.loads((repo / subject.RECORD_PATH).read_text(encoding="utf-8"))

    assert payload["authorization_reusable"] is False
    assert payload["unchanged_replay_authorized"] is False
    assert payload["runtime_execution_authorized"] is False


def test_next_gate_is_v4_evidence_hardening(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    payload = json.loads((repo / subject.REVIEW_PATH).read_text(encoding="utf-8"))

    assert payload["next_gate"] == ("design_and_merge_p3_p6_runtime_evidence_contract_hardening_v4")


def test_vllm_authority_is_startup_scoped(
    tmp_path: Path,
) -> None:
    repo = _repo_from_candidate(tmp_path)
    subject = _load_subject(repo)
    payload = json.loads((repo / subject.VLLM_AUTHORITY_PATH).read_text(encoding="utf-8"))

    assert payload["scope"] == "STARTUP_BACKEND_SELECTION_ONLY"
    assert payload["request_level_kernel_execution_proven"] is False
