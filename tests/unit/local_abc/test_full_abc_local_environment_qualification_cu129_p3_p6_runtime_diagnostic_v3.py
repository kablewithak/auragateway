"""Tests for P3-P6 runtime process-tree import closure V3 assets."""

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
    full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v3 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    required = (
        subject.FAILURE_ACCEPTANCE_RECORD_PATH,
        subject.FAILURE_ACCEPTANCE_REVIEW_PATH,
        subject.V2_IMPLEMENTATION_RECORD_PATH,
        subject.V2_TEMPLATE_PATH,
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
    module = types.ModuleType("auragateway_p3_p6_runtime_diagnostic_v3_runtime")
    exec(
        compile(source, subject.TEMPLATE_PATH.as_posix(), "exec"),
        module.__dict__,
    )
    return module


def _closure_payload(target_site: Path) -> dict[str, object]:
    modules = {}
    for name, relative in (
        ("vllm", "vllm/__init__.py"),
        ("torch", "torch/__init__.py"),
        ("triton", "triton/__init__.py"),
        ("transformers", "transformers/__init__.py"),
        (
            "vllm.model_executor.models.registry",
            "vllm/model_executor/models/registry.py",
        ),
    ):
        modules[name] = {
            "origin": str((target_site / relative).resolve()),
        }
    return {
        "parent_python_executable": "/usr/bin/python3",
        "parent_pythonpath": str(target_site),
        "child_returncode": 0,
        "child": {
            "python_executable": "/usr/bin/python3",
            "pythonpath": str(target_site),
            "modules": modules,
        },
    }


def test_generate_validate_round_trip(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.record.status == "IMPLEMENTED_NOT_EXECUTED"
    assert generated.record.source_main_commit == subject.SOURCE_MAIN_COMMIT


def test_v2_failure_acceptance_is_exact_authority(tmp_path: Path) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request

    assert tuple(item.authority_id for item in request.accepted_authorities) == (
        "v2_failure_acceptance_record",
        "v2_failure_acceptance_review",
        "v2_implementation_record",
    )
    failure = request.known_v2_failure
    assert failure.saved_version_id == 339387641
    assert failure.runtime_install_status == "PASSED"
    assert failure.failed_probe == "P3"
    assert failure.root_cause_status == "CONFIRMED_FROM_WORKER_LOG_TRACE"
    assert failure.unchanged_replay_authorized is False


def test_pythonpath_is_replaced_with_exact_target_site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    library = target_site / "nvidia" / "cublas" / "lib"
    library.mkdir(parents=True)
    runtime.TARGET_SITE = target_site
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "poison"))
    monkeypatch.setattr(
        runtime,
        "target_library_directories",
        lambda: (library,),
    )

    environment = runtime.process_tree_environment(
        0,
        tmp_path / "model-home",
    )

    assert environment["PYTHONPATH"] == str(target_site)
    assert str(tmp_path / "poison") not in environment["PYTHONPATH"]
    assert environment["PYTHONNOUSERSITE"] == "1"


def test_import_closure_gate_precedes_model_copy_and_worker_start(
    tmp_path: Path,
) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    closure = source.index("validate_process_tree_import_closure(counters)")
    model_copy = source.index("model_home, snapshot = prepare_model_home(source_snapshot)")
    worker_start = source.index("worker_1.start(counters)")

    assert closure < model_copy < worker_start


def test_import_closure_failure_code_and_budget_are_explicit(
    tmp_path: Path,
) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert '"P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED"' in source
    assert '"runtime_import_closure_probes": 1' in source
    assert '"runtime_import_closure_probes": 0' in source
    assert 'consume_actions(counters, "runtime_import_closure_probes")' in source


def test_nested_probe_uses_inherited_environment(
    tmp_path: Path,
) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    parent_marker = source.index("child_executable = sys.argv[2]")
    start = source.index("completed = subprocess.run(", parent_marker)
    nested = source[start : start + 500]

    assert "env=" not in nested
    assert 'EXPECTED_CHILD_PYTHON = Path("/usr/bin/python3")' in source


def test_closure_payload_accepts_exact_target_origins(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    runtime.TARGET_SITE = target_site

    validated = runtime.validate_import_closure_payload(_closure_payload(target_site))

    assert validated["all_critical_origins_within_target_site"] is True


def test_closure_payload_rejects_one_external_origin(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    runtime.TARGET_SITE = target_site
    payload = _closure_payload(target_site)
    child = payload["child"]
    assert isinstance(child, dict)
    modules = child["modules"]
    assert isinstance(modules, dict)
    item = modules["vllm"]
    assert isinstance(item, dict)
    item["origin"] = str(tmp_path / "base" / "vllm.py")

    with pytest.raises(
        runtime.DiagnosticFailure,
        match="outside target site",
    ):
        runtime.validate_import_closure_payload(payload)


def test_probe_failure_consumes_no_model_or_worker_action(
    tmp_path: Path,
) -> None:
    contract = subject.build_generated(_fixture_repo(tmp_path)).request.process_tree_import_closure

    assert contract.model_loads_on_probe_failure == 0
    assert contract.worker_starts_on_probe_failure == 0


def test_output_contract_includes_import_closure_report(
    tmp_path: Path,
) -> None:
    review = subject.build_generated(_fixture_repo(tmp_path)).review

    assert review.output_contract[0:2] == (
        "runtime_install_report_v3.json",
        "runtime_import_closure_report_v3.json",
    )
    assert "ag-cu129-p3-p6-runtime-evidence-v3.zip" in review.output_contract


def test_bounded_process_retains_nonzero_exit_evidence(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    report = runtime.run_bounded_process(
        "nonzero",
        [
            sys.executable,
            "-c",
            (
                "import sys; print('bounded-out'); "
                "print('bounded-err', file=sys.stderr); sys.exit(7)"
            ),
        ],
        timeout_seconds=5.0,
        environment=dict(os.environ),
        capture_root=tmp_path / "capture",
    )

    assert report["status"] == "FAILED"
    assert report["process_outcome"] == "NONZERO_EXIT"
    assert report["returncode"] == 7
    assert "bounded-out" in report["stdout_tail"]
    assert "bounded-err" in report["stderr_tail"]


def test_worker_failure_diagnostics_are_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    library = target_site / "nvidia" / "cublas" / "lib"
    library.mkdir(parents=True)
    runtime.TARGET_SITE = target_site
    monkeypatch.setattr(
        runtime,
        "target_library_directories",
        lambda: (library,),
    )
    worker = runtime.Worker(
        "worker_1",
        0,
        8001,
        tmp_path / "model-home",
        tmp_path / "snapshot",
    )
    worker.stdout.buffer.extend(b"stdout-tail")
    worker.stdout.observed = len(b"stdout-tail")
    worker.stderr.buffer.extend(b"stderr-tail")
    worker.stderr.observed = len(b"stderr-tail")

    diagnostics = worker.failure_diagnostics()

    assert diagnostics["stdout_tail"] == "stdout-tail"
    assert diagnostics["stderr_tail"] == "stderr-tail"
    assert diagnostics["pythonpath_exact_target_site"] is True


def test_evidence_bundle_excludes_raw_worker_logs(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    output_root = tmp_path / "evidence"
    output_root.mkdir()
    scratch_root = tmp_path / "scratch"
    scratch_root.mkdir()
    log_root = output_root / "worker_logs"
    log_root.mkdir()
    (log_root / "worker.stderr.log").write_text(
        "not bundled",
        encoding="utf-8",
    )
    evidence_zip = tmp_path / "evidence.zip"
    runtime.OUTPUT_ROOT = output_root
    runtime.SCRATCH_ROOT = scratch_root
    runtime.EVIDENCE_ZIP = evidence_zip

    for name in runtime.OUTPUT_NAMES:
        if name == "bundle_manifest_v3.json":
            continue
        path = output_root / name
        if path.suffix == ".md":
            path.write_text("evidence", encoding="utf-8")
        else:
            path.write_text("{}", encoding="utf-8")

    runtime.bundle_outputs()

    with zipfile.ZipFile(evidence_zip) as archive:
        names = set(archive.namelist())
    assert "worker.stderr.log" not in names
    assert set(runtime.OUTPUT_NAMES) == names


def test_no_runtime_authority_is_issued(tmp_path: Path) -> None:
    generated = subject.build_generated(_fixture_repo(tmp_path))

    assert generated.request.runtime_execution_authorized is False
    assert generated.request.authorization_issuer_included is False
    assert generated.record.safety.kaggle_execution_performed is False
    assert generated.record.safety.import_closure_probe_performed is False


def test_accepted_authority_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.FAILURE_ACCEPTANCE_RECORD_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6V3ImplementationError,
        match="identity drifted",
    ):
        subject.build_generated(repo_root)


def test_generated_artifact_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    path = repo_root / subject.NOTEBOOK_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6V3ImplementationError,
        match="differs from fresh rebuild",
    ):
        subject.validate(repo_root)


def test_template_compiles_and_lines_are_bounded(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    generated = subject.build_generated(repo_root)
    payload = json.loads(generated.notebook_bytes.decode("utf-8"))
    code = "".join(
        item for cell in payload["cells"] if cell["cell_type"] == "code" for item in cell["source"]
    )

    compile(code, subject.NOTEBOOK_PATH.as_posix(), "exec")
    assert max(len(line) for line in code.splitlines()) <= 100


def test_names_fit_kaggle_limit() -> None:
    assert len(subject.NOTEBOOK_NAME) <= 50
    assert len(subject.FAILED_NOTEBOOK_NAME) <= 50


def test_candidate_boundary_is_exact() -> None:
    assert len(subject.CANDIDATE_PATHS) == 10
    assert len(set(subject.CANDIDATE_PATHS)) == 10
