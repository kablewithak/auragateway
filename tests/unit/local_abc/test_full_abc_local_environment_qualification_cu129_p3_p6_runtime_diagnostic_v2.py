"""Tests for P3-P6 runtime diagnostic V2 implementation assets."""

from __future__ import annotations

import json
import os
import shutil
import sys
import types
import zipfile
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v2 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    required = (
        subject.FAILURE_ACCEPTANCE_RECORD_PATH,
        subject.FAILURE_ACCEPTANCE_REVIEW_PATH,
        subject.V1_IMPLEMENTATION_RECORD_PATH,
        subject.V1_TEMPLATE_PATH,
        *subject.STATIC_PATHS,
    )
    for relative in required:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def _runtime_module(repo_root: Path) -> Any:
    source = subject._template_bytes(repo_root).decode("utf-8")
    module = types.ModuleType("auragateway_p3_p6_runtime_diagnostic_v2_runtime")
    exec(compile(source, subject.TEMPLATE_PATH.as_posix(), "exec"), module.__dict__)
    return module


def test_generate_validate_round_trip(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.record.status == "IMPLEMENTED_NOT_EXECUTED"
    assert generated.record.source_main_commit == subject.SOURCE_MAIN_COMMIT


def test_v1_failure_acceptance_is_exact_authority(tmp_path: Path) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request

    assert tuple(item.authority_id for item in request.accepted_authorities) == (
        "v1_failure_acceptance_record",
        "v1_failure_acceptance_review",
        "v1_implementation_record",
    )
    assert request.known_v1_failure.saved_version_id == 339375227
    assert request.known_v1_failure.root_cause_status == "UNRESOLVED"
    assert request.known_v1_failure.runtime_root_cause_confirmed is False
    assert request.known_v1_failure.unchanged_replay_authorized is False


def test_find_links_defect_is_remediated_without_root_cause_overclaim(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    generated = subject.build_generated(repo_root)
    source = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert generated.request.known_v1_failure.observed_implementation_defect == (
        "V1_FIND_LINKS_TARGETS_WHEELHOUSE_ROOT_NOT_WHEELS_DIRECTORY"
    )
    find_links = source.index('"--find-links",')
    assert "str(wheels)," in source[find_links : find_links + 120]
    assert 'wheels = wheelhouse / "wheels"' in source
    assert "str(wheelhouse)," not in source[find_links : find_links + 120]


def test_install_precedes_writable_model_copy(tmp_path: Path) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    install_call = source.index("install_runtime(wheelhouse, counters)")
    model_copy = source.index("model_home, snapshot = prepare_model_home(source_snapshot)")

    assert install_call < model_copy
    assert 'model_home = SCRATCH_ROOT / "model_home"' in source


def test_install_report_contract_is_complete(tmp_path: Path) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")
    required = (
        '"returncode": returncode',
        '"timed_out": timed_out',
        '"stdout_tail": stdout_tail',
        '"stderr_tail": stderr_tail',
        '"working_disk_before": before_disk',
        '"working_disk_after": disk_snapshot(WORK_ROOT)',
        '"target_runtime_after": directory_snapshot(TARGET_ROOT)',
        '"hidden_retry_count": 0',
        '"root_cause_review_required": process["status"] != "PASSED"',
    )

    assert all(marker in source for marker in required)
    assert "MAX_INSTALL_EXCERPT_CHARACTERS = 16000" in source
    assert "MAX_EVIDENCE_ZIP_BYTES = 2 * 1024**2" in source


def test_bounded_process_retains_nonzero_exit_evidence(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    report = runtime.run_bounded_process(
        "nonzero",
        [
            sys.executable,
            "-c",
            "import sys; print('bounded-out'); print('bounded-err', file=sys.stderr); sys.exit(7)",
        ],
        timeout_seconds=5.0,
        environment=dict(os.environ),
        capture_root=tmp_path / "capture",
    )

    assert report["status"] == "FAILED"
    assert report["process_outcome"] == "NONZERO_EXIT"
    assert report["returncode"] == 7
    assert report["timed_out"] is False
    assert "bounded-out" in report["stdout_tail"]
    assert "bounded-err" in report["stderr_tail"]


def test_bounded_process_retains_timeout_state(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    report = runtime.run_bounded_process(
        "timeout",
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout_seconds=0.05,
        environment=dict(os.environ),
        capture_root=tmp_path / "capture",
    )

    assert report["status"] == "FAILED"
    assert report["process_outcome"] == "TIMEOUT"
    assert report["timed_out"] is True
    assert report["returncode"] is not None


def test_bounded_process_retains_launch_failure(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    report = runtime.run_bounded_process(
        "launch",
        [str(tmp_path / "missing-executable")],
        timeout_seconds=1.0,
        environment=dict(os.environ),
        capture_root=tmp_path / "capture",
    )

    assert report["status"] == "FAILED"
    assert report["process_outcome"] == "LAUNCH_ERROR"
    assert report["returncode"] is None
    assert report["launch_error_type"]


def test_failure_signals_are_diagnostic_not_root_cause(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))

    signals = runtime.install_failure_signals(
        "",
        "ERROR: Could not find a version that satisfies the requirement vllm",
    )

    assert signals == ("DISTRIBUTION_UNAVAILABLE_SIGNAL",)
    generated = subject.build_generated(_fixture_repo(tmp_path))
    assert generated.request.known_v1_failure.runtime_root_cause_confirmed is False


def test_every_probe_gets_terminal_report_after_install_failure(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    output_root = tmp_path / "evidence"
    output_root.mkdir()
    runtime.OUTPUT_ROOT = output_root

    runtime.write_probe_terminal_reports(
        [],
        None,
        "P3_P6_RUNTIME_INSTALL_NONZERO_EXIT",
    )

    for probe_id, name in (
        ("P3", "p3_worker_startup_report_v2.json"),
        ("P4", "p4_deterministic_request_report_v2.json"),
        ("P5", "p5_prefix_cache_reset_report_v2.json"),
        ("P6", "p6_dual_worker_isolation_report_v2.json"),
    ):
        payload = json.loads((output_root / name).read_text(encoding="utf-8"))
        assert payload["probe_id"] == probe_id
        assert payload["status"] == "NOT_RUN"
        assert payload["blocked_by"] == "P3_P6_RUNTIME_INSTALL_NONZERO_EXIT"


def test_evidence_bundle_excludes_scratch_and_worker_logs(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    output_root = tmp_path / "evidence"
    output_root.mkdir()
    scratch_root = tmp_path / "scratch"
    scratch_root.mkdir()
    (scratch_root / "large.bin").write_bytes(b"x" * 1024)
    log_root = output_root / "worker_logs"
    log_root.mkdir()
    (log_root / "worker.stderr.log").write_text("not bundled", encoding="utf-8")
    evidence_zip = tmp_path / "evidence.zip"
    runtime.OUTPUT_ROOT = output_root
    runtime.SCRATCH_ROOT = scratch_root
    runtime.EVIDENCE_ZIP = evidence_zip

    for name in runtime.OUTPUT_NAMES:
        if name == "bundle_manifest_v2.json":
            continue
        path = output_root / name
        if path.suffix == ".md":
            path.write_text("evidence", encoding="utf-8")
        else:
            path.write_text("{}", encoding="utf-8")

    result = runtime.bundle_outputs()

    assert result["evidence_zip_size_bytes"] <= 2 * 1024**2
    with zipfile.ZipFile(evidence_zip) as archive:
        names = set(archive.namelist())
    assert "worker.stderr.log" not in names
    assert "large.bin" not in names
    assert set(runtime.OUTPUT_NAMES) == names


def test_output_contract_includes_install_cleanup_and_terminal_reports(
    tmp_path: Path,
) -> None:
    review = subject.build_generated(_fixture_repo(tmp_path)).review

    assert review.output_contract == (
        "runtime_install_report_v2.json",
        "p3_worker_startup_report_v2.json",
        "p4_deterministic_request_report_v2.json",
        "p5_prefix_cache_reset_report_v2.json",
        "p6_dual_worker_isolation_report_v2.json",
        "scratch_cleanup_report_v2.json",
        "p3_p6_runtime_diagnostic_summary_v2.json",
        "failure_report_v2.json",
        "bundle_manifest_v2.json",
        "human_report_v2.md",
        "ag-cu129-p3-p6-runtime-evidence-v2.zip",
    )


def test_no_runtime_authority_is_issued(tmp_path: Path) -> None:
    generated = subject.build_generated(_fixture_repo(tmp_path))

    assert generated.request.runtime_execution_authorized is False
    assert generated.request.authorization_issuer_included is False
    assert generated.record.safety.kaggle_execution_performed is False
    assert generated.record.safety.runtime_installation_performed is False
    assert generated.record.safety.model_requests_performed == 0


def test_accepted_authority_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.FAILURE_ACCEPTANCE_RECORD_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6V2ImplementationError,
        match="identity drifted",
    ):
        subject.build_generated(repo_root)


def test_generated_artifact_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    path = repo_root / subject.NOTEBOOK_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6V2ImplementationError,
        match="differs from fresh rebuild",
    ):
        subject.validate(repo_root)


def test_template_compiles_and_python_lines_are_bounded(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    generated = subject.build_generated(repo_root)
    payload = json.loads(generated.notebook_bytes.decode("utf-8"))
    code = "".join(
        item for cell in payload["cells"] if cell["cell_type"] == "code" for item in cell["source"]
    )

    compile(code, subject.NOTEBOOK_PATH.as_posix(), "exec")
    assert max(len(line) for line in code.splitlines()) <= 100


def test_template_import_block_is_ruff_ordered(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    source = subject._template_bytes(repo_root).decode("utf-8")
    expected = (
        "import time\n"
        "import urllib.error\n"
        "import urllib.parse\n"
        "import urllib.request\n"
        "import zipfile\n"
        "from datetime import UTC, datetime\n"
        "from pathlib import Path\n"
        "from typing import Final\n"
    )

    assert expected in source


def test_names_fit_kaggle_limit() -> None:
    assert len(subject.NOTEBOOK_NAME) <= 50
    assert len(subject.FAILED_NOTEBOOK_NAME) <= 50


def test_candidate_boundary_is_exact() -> None:
    assert len(subject.CANDIDATE_PATHS) == 10
    assert len(set(subject.CANDIDATE_PATHS)) == 10
