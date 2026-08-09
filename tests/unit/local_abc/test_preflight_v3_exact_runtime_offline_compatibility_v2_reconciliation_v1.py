from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from auragateway.local_abc import (
    preflight_v3_exact_runtime_offline_compatibility_v2_reconciliation_v1 as recon,
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
        *recon.EXPECTED_REPO_AUTHORITIES.keys(),
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


def test_v2_disposition_is_diagnostic_not_runtime_failure() -> None:
    disposition = recon._disposition()

    assert disposition.v2_repository_disposition == "ACCEPTED_DIAGNOSTIC_FAILURE"
    assert disposition.classification == "STALE_VERSION_BOUND_NATIVE_EXTENSION_PROBE"
    assert disposition.runtime_incompatibility_established is False
    assert disposition.exact_runtime_offline_verified is False
    assert disposition.v2_replay_authorized is False
    assert disposition.next_expensive_execution_permitted is False


def test_capability_contract_binds_correct_cuda_module_and_gate() -> None:
    contract = recon._capability_contract()

    assert contract.current_boundary == "P0_FINAL_RUNTIME_VERIFIER_RECONCILIATION"
    assert contract.sequencing_authority == "HANDOVER_V17_AND_CURRENT_REPOSITORY_EVIDENCE"
    assert contract.original_prd_role == "HISTORICAL_NORTH_STAR_AND_DESIGN_CONTEXT_ONLY"
    assert contract.stale_v2_native_probe == "vllm._C"
    assert contract.required_cuda_native_module == "vllm._C_stable_libtorch"
    assert contract.controlled_python_startup_required is True
    assert contract.native_loader_provenance_required is True
    assert contract.successful_native_import_alone_sufficient is False
    assert contract.model_loads_permitted == 0
    assert contract.worker_startups_permitted == 0
    assert contract.model_requests_permitted == 0
    assert contract.benchmark_trajectories_permitted == 0


def test_historical_controls_are_reused_without_promoting_old_runtime() -> None:
    controls = recon._historical_controls()

    assert controls.python_startup_policy == "NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"
    assert controls.canonical_loader_policy == "TARGET_NVIDIA_LIBRARIES_PREPENDED"
    assert controls.cuda_stub_policy == "REJECT"
    assert controls.ambient_python_package_native_library_policy == "REJECT"
    assert controls.historical_runtime_promoted_to_current_qualification is False


def test_v2_evidence_preserves_startup_canary_without_causal_assignment() -> None:
    evidence = recon._v2_evidence()

    assert evidence.saved_version_id == 341096416
    assert evidence.vllm_module_status == "PASSED"
    assert evidence.vllm_module_returncode == 0
    assert evidence.native_probe_module == "vllm._C"
    assert evidence.native_probe_status == "FAILED"
    assert evidence.native_probe_returncode == 1
    assert evidence.startup_canary_observed is True
    assert evidence.startup_canary_causal_role == "UNPROVEN"
    assert evidence.runtime_incompatibility_established is False


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


def test_validate_implementation_preserves_authorization_boundary(
    candidate_repo: Path,
) -> None:
    recon.generate(candidate_repo)

    result = recon.validate_implementation(candidate_repo)

    assert result["v2_repository_disposition"] == "ACCEPTED_DIAGNOSTIC_FAILURE"
    assert result["runtime_incompatibility_established"] is False
    assert result["exact_runtime_offline_verified"] is False
    assert result["p5_p6_exact_runtime_requalified"] is False
    assert result["runtime_execution_authorized"] is False
    assert result["pilot_execution_authorized"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["next_expensive_execution_permitted"] is False


def test_validate_implementation_rejects_record_drift(candidate_repo: Path) -> None:
    recon.generate(candidate_repo)
    record_path = candidate_repo / recon.RECORD_PATH
    record_path.write_text(
        record_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(recon.ReconciliationError) as captured:
        recon.validate_implementation(candidate_repo)

    assert captured.value.error_code == "PREFLIGHT_V3_RECONCILIATION_STATIC_ARTIFACT_NOT_CANONICAL"


def test_bound_repository_authority_drift_fails_closed(candidate_repo: Path) -> None:
    path = next(iter(recon.EXPECTED_REPO_AUTHORITIES))
    target = candidate_repo / path
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(recon.ReconciliationError) as captured:
        recon._require_expected_repo_authorities(candidate_repo)

    assert captured.value.error_code == "PREFLIGHT_V3_RECONCILIATION_SOURCE_AUTHORITY_DRIFT"


def _notebook_payload() -> bytes:
    metadata = {
        "accepted_materializer_script_version_id": 341083505,
        "benchmark_trajectories_permitted": 0,
        "dependency_resolution_permitted": False,
        "exact_resolution_lock_sha256": (
            "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
        ),
        "expected_package_count": 196,
        "expected_sha_manifest_entry_count": 200,
        "expected_total_wheel_bytes": 6164913809,
        "final_measured_abc_execution_authorized": False,
        "internet_required": False,
        "materialization_acceptance_sha256": (
            "042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725"
        ),
        "model_loads_permitted": 0,
        "model_requests_permitted": 0,
        "pilot_execution_authorized": False,
        "runtime_execution_authorized": False,
        "v1_false_negative_acceptance_sha256": (
            "86d679eb4cf76debb7afbecdc4573c10d1884fe343b424327b4477e9d5a1b27b"
        ),
        "v1_false_negative_script_version_id": 341091805,
        "vllm_distribution_version": "0.25.1+cu129",
        "vllm_module_semantic_version": "0.25.1",
        "worker_startups_permitted": 0,
    }
    payload = {
        "cells": [
            {"cell_type": "markdown", "source": ["fixture markdown\n"]},
            {"cell_type": "code", "source": ["print('fixture')\n"]},
        ],
        "metadata": {"auragateway": metadata},
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def _summary_payload() -> bytes:
    return json.dumps(
        {
            "offline_compatibility_status": "FAILED_PENDING_REVIEW",
            "failed_required_roles": ["vllm_native_extension"],
            "locked_package_count": 196,
            "validated_manifest_entry_count": 200,
            "total_wheel_bytes": 6164913809,
            "package_installation_performed": True,
            "model_loads_performed": 0,
            "worker_startups_performed": 0,
            "model_requests_performed": 0,
            "benchmark_trajectories_performed": 0,
            "qualification_claimed": False,
            "exact_runtime_offline_verified": False,
            "p5_p6_exact_runtime_requalified": False,
            "runtime_execution_authorized": False,
            "pilot_execution_authorized": False,
            "final_measured_abc_execution_authorized": False,
            "required_role_statuses": recon.EXPECTED_REQUIRED_ROLE_STATUSES,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _probe_records_payload() -> bytes:
    warning = (
        "Error in sitecustomize; set PYTHONVERBOSE for traceback:\n"
        "ModuleNotFoundError: No module named 'wrapt'\n"
    )
    native = warning + "ModuleNotFoundError: No module named 'vllm._C'\n"
    return json.dumps(
        {
            "vllm_module": {
                "status": "PASSED",
                "returncode": 0,
                "stdout_excerpt": '{"vllm":"0.25.1"}\n',
                "stderr_excerpt": warning,
            },
            "vllm_native_extension": {
                "status": "FAILED",
                "returncode": 1,
                "stdout_excerpt": "",
                "stderr_excerpt": native,
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _external_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path]:
    notebook = _notebook_payload()
    notebook_path = tmp_path / "executed.ipynb"
    notebook_path.write_bytes(notebook)

    markdown_source = b"fixture markdown\n"
    code_source = b"print('fixture')\n"
    monkeypatch.setattr(recon, "V2_EXECUTED_NOTEBOOK_SHA256", _sha256(notebook))
    monkeypatch.setattr(recon, "V2_EXECUTED_NOTEBOOK_SIZE_BYTES", len(notebook))
    monkeypatch.setattr(recon, "V2_MARKDOWN_SOURCE_SHA256", _sha256(markdown_source))
    monkeypatch.setattr(recon, "V2_CODE_SOURCE_SHA256", _sha256(code_source))

    members = {
        "input_validation.json": b"{}",
        "probe_records.json": _probe_records_payload(),
        "verification_summary.json": _summary_payload(),
        "evidence_manifest.json": b"{}",
    }
    expected_members = tuple(
        (name, _sha256(payload), len(payload)) for name, payload in members.items()
    )
    monkeypatch.setattr(recon, "EXPECTED_EVIDENCE_MEMBERS", expected_members)

    evidence_zip = tmp_path / "evidence.zip"
    with zipfile.ZipFile(evidence_zip, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    evidence_bytes = evidence_zip.read_bytes()
    monkeypatch.setattr(recon, "V2_EVIDENCE_ZIP_SHA256", _sha256(evidence_bytes))
    monkeypatch.setattr(recon, "V2_EVIDENCE_ZIP_SIZE_BYTES", len(evidence_bytes))

    log = (
        b'{"offline_compatibility_status":"FAILED_PENDING_REVIEW",'
        b'"failed_required_roles":["vllm_native_extension"],'
        b'"exact_runtime_offline_verified":false,'
        b'"runtime_execution_authorized":false,'
        b'"pilot_execution_authorized":false,'
        b'"final_measured_abc_execution_authorized":false}'
    )
    log_path = tmp_path / "execution.log"
    log_path.write_bytes(log)
    monkeypatch.setattr(recon, "V2_EXECUTION_LOG_SHA256", _sha256(log))
    monkeypatch.setattr(recon, "V2_EXECUTION_LOG_SIZE_BYTES", len(log))
    return notebook_path, log_path, evidence_zip


def test_verify_evidence_accepts_exact_diagnostic_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notebook, log, evidence_zip = _external_fixture(tmp_path, monkeypatch)

    result = recon.verify_evidence(notebook, log, evidence_zip)

    assert result["status"] == "V2_EXTERNAL_DIAGNOSTIC_EVIDENCE_VERIFIED"
    assert result["classification"] == "STALE_VERSION_BOUND_NATIVE_EXTENSION_PROBE"
    assert result["runtime_incompatibility_established"] is False
    assert result["next_expensive_execution_permitted"] is False


def test_verify_evidence_rejects_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notebook, log, evidence_zip = _external_fixture(tmp_path, monkeypatch)
    log.write_bytes(log.read_bytes() + b"x")

    with pytest.raises(recon.ReconciliationError) as captured:
        recon.verify_evidence(notebook, log, evidence_zip)

    assert (
        captured.value.error_code
        == "PREFLIGHT_V3_RECONCILIATION_EXTERNAL_EVIDENCE_IDENTITY_MISMATCH"
    )


def test_safe_member_name_rejects_parent_traversal() -> None:
    with pytest.raises(recon.ReconciliationError) as captured:
        recon._safe_member_name("../evidence.json")

    assert captured.value.error_code == "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE"
