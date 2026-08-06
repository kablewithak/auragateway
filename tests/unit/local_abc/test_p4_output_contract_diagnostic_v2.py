from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType

import pytest

from auragateway.local_abc import p4_output_contract_diagnostic_v2 as subject


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def rendered_runtime() -> str:
    request = subject.load_request(repo_root())
    return subject.render_runtime(repo_root(), request).decode("utf-8")


def runtime_module(tmp_path: Path) -> ModuleType:
    source = rendered_runtime()
    path = tmp_path / "runtime_v2.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("runtime_v2", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_request_preserves_v1_matrix_and_order() -> None:
    request = subject.load_request(repo_root())
    assert [item.case_id for item in request.cases] == list("ABCDEF")
    assert request.request_order == [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "F",
        "E",
        "D",
        "C",
        "B",
        "A",
        "C",
        "D",
        "E",
        "F",
        "A",
        "B",
    ]
    assert request.runtime_execution_authorized is False
    assert request.measured_abc_execution_authorized is False


def test_template_renders_and_parses() -> None:
    source = rendered_runtime()
    ast.parse(source)
    assert "__SOURCE_MAIN_COMMIT__" not in source
    assert "ag-p4-output-contract-evidence-v2.zip" in source


def test_native_environment_precedes_ambient_and_filters_stubs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = runtime_module(tmp_path)
    target = tmp_path / "target"
    for relative in runtime.TARGET_LIBRARY_RELATIVE_DIRECTORIES:
        (target / relative).mkdir(parents=True, exist_ok=True)
    driver = tmp_path / "driver"
    driver.mkdir()
    monkeypatch.setattr(runtime, "TARGET_SITE", target)
    monkeypatch.setattr(runtime, "REAL_DRIVER_DIRECTORY", driver)
    monkeypatch.setenv(
        "LD_LIBRARY_PATH",
        os.pathsep.join(("/usr/local/cuda/lib64/stubs", "/ambient/cuda")),
    )
    environment = runtime.build_runtime_environment(gpu_index=0)
    paths = environment["LD_LIBRARY_PATH"].split(os.pathsep)
    assert paths[0] == str(target / "nvidia/nvjitlink/lib")
    assert "/usr/local/cuda/lib64/stubs" not in paths
    assert "/ambient/cuda" in paths
    assert paths[-1] == str(driver)
    assert environment["LIBRARY_PATH"] == str(driver)
    assert environment["CUDA_VISIBLE_DEVICES"] == "0"


def test_import_and_worker_use_same_environment_helper() -> None:
    tree = ast.parse(rendered_runtime())
    calls: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names = [
                child.func.id
                for child in ast.walk(node)
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
            ]
            calls[node.name] = names
    assert "build_runtime_environment" in calls["import_closure"]
    assert "build_runtime_environment" in calls["start_worker"]


def test_worker_flags_disable_request_logs_and_pin_backend() -> None:
    source = rendered_runtime()
    assert '"--attention-backend"' in source
    assert '"--no-enable-log-requests"' in source
    assert 'EXPECTED_BACKEND = "TRITON_ATTN"' in source


def test_wait_ready_checks_process_exit() -> None:
    source = rendered_runtime()
    tree = ast.parse(source)
    wait_ready = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "wait_ready"
    )
    attributes = [child.attr for child in ast.walk(wait_ready) if isinstance(child, ast.Attribute)]
    assert "poll" in attributes
    assert "P4_V2_WORKER_EXITED_BEFORE_READINESS" in source


def test_capture_is_bounded(tmp_path: Path) -> None:
    runtime = runtime_module(tmp_path)

    class Stream:
        def __init__(self) -> None:
            self.rows = iter(["x" * 70000 + "\n", "y" * 70000 + "\n"])

        def readline(self) -> str:
            return next(self.rows, "")

        def close(self) -> None:
            return None

    capture = runtime.Capture()
    capture.consume(Stream())
    receipt = capture.receipt()
    assert receipt["observed_bytes"] > runtime.MAX_STREAM_BYTES
    assert receipt["retained_bytes"] <= runtime.MAX_STREAM_BYTES
    assert receipt["truncated"] is True


def test_native_origin_policy_requires_target_pair() -> None:
    source = rendered_runtime()
    assert 'TARGET_REQUIRED_NATIVE_TOKENS = ("libcusparse", "libnvJitLink")' in source
    assert "P4_V2_NATIVE_ORIGIN_CLOSURE_FAILED" in source
    assert "PROHIBITED_CUDA_STUB" in source


def test_inspection_evidence_identity() -> None:
    path = repo_root() / subject.INSPECTION_ZIP_PATH
    assert hashlib.sha256(path.read_bytes()).hexdigest() == subject.INSPECTION_EVIDENCE_SHA256


def test_generation_is_deterministic() -> None:
    root = repo_root()
    subject.generate(root)
    first_notebook = (root / subject.NOTEBOOK_PATH).read_bytes()
    first_record = (root / subject.RECORD_PATH).read_bytes()
    subject.generate(root)
    assert (root / subject.NOTEBOOK_PATH).read_bytes() == first_notebook
    assert (root / subject.RECORD_PATH).read_bytes() == first_record
    subject.validate_package(root)


def test_notebook_is_unexecuted_single_cell() -> None:
    subject.generate(repo_root())
    notebook = json.loads((repo_root() / subject.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    assert len(notebook["cells"]) == 1
    cell = notebook["cells"][0]
    assert cell["cell_type"] == "code"
    assert cell["execution_count"] is None
    assert cell["outputs"] == []


def test_notebook_wrapper_respects_repository_line_length() -> None:
    subject.generate(repo_root())
    notebook = json.loads((repo_root() / subject.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    wrapper = "".join(notebook["cells"][0]["source"])
    lines = wrapper.splitlines()

    assert lines
    assert max(len(line) for line in lines) <= 100
    assert "RUNTIME_SOURCE_B64 = (" in wrapper


def test_v1_files_are_not_candidate_paths() -> None:
    candidate_names = {
        subject.TEMPLATE_PATH.name,
        subject.NOTEBOOK_PATH.name,
        subject.RECORD_PATH.name,
        subject.REQUEST_PATH.name,
    }
    assert all("v2" in name for name in candidate_names)
    assert all("v1" not in name for name in candidate_names)
