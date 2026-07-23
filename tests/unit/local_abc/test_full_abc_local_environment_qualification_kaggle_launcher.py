from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
import zipfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_kaggle_launcher as launcher,
)


def _copy_reviewed_notebook(repo_root: Path) -> None:
    source = Path(__file__).resolve().parents[3] / launcher.REVIEWED_NOTEBOOK_PATH
    destination = repo_root / launcher.REVIEWED_NOTEBOOK_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def _code_source(notebook: dict[str, object]) -> str:
    cells = cast(list[dict[str, object]], notebook["cells"])
    source = cells[1]["source"]
    assert isinstance(source, list)
    return "".join(cast(list[str], source))


def _launcher_runtime_namespace(
    tmp_path: Path,
) -> dict[str, object]:
    repo_root = tmp_path / "repo"
    _copy_reviewed_notebook(repo_root)
    source = _code_source(launcher.build_launcher_notebook(repo_root))

    input_root = tmp_path / "kaggle" / "input"
    work_root = tmp_path / "kaggle" / "working"
    input_root.mkdir(parents=True)
    work_root.mkdir(parents=True)

    source = source.replace(
        'Path("/kaggle/input").resolve()',
        f"Path({str(input_root)!r}).resolve()",
        1,
    )
    source = source.replace(
        'Path("/kaggle/working").resolve()',
        f"Path({str(work_root)!r}).resolve()",
        1,
    )

    preamble, separator, _ = source.partition('\ntry:\n    stage = "fresh_session_guard"')
    assert separator

    namespace: dict[str, object] = {}
    exec(
        compile(preamble, "launcher_runtime_preamble.py", "exec"),
        namespace,
    )
    return namespace


def _write_control_output(root: Path) -> None:
    root.mkdir(parents=True)
    for filename in (
        launcher.AUTHORIZATION_FILENAME,
        launcher.DATASET_MANIFEST_FILENAME,
        launcher.CONTROL_MANIFEST_NAME,
        launcher.CONTROL_RECEIPT_NAME,
    ):
        (root / filename).write_text("{}", encoding="utf-8")


@contextmanager
def _short_windows_safe_temp_root() -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="ag-") as directory:
        yield Path(directory)


def test_build_launcher_notebook_is_deterministic(
    tmp_path: Path,
) -> None:
    _copy_reviewed_notebook(tmp_path)

    first = launcher.build_launcher_notebook(tmp_path)
    second = launcher.build_launcher_notebook(tmp_path)

    assert first == second

    metadata = cast(dict[str, object], first["metadata"])
    auragateway = cast(dict[str, object], metadata["auragateway"])

    assert auragateway["notebook_name"] == ("ag-full-abc-env-qualification-v1")
    assert auragateway["control_notebook_name"] == ("ag-qualification-control-materializer-v1")
    assert auragateway["evidence_zip_name"] == ("ag-qualification-evidence-v1.zip")
    assert auragateway["control_output_directory_name"] == ("ag_qualification_control_v1")
    assert auragateway["control_output_discovery_scope"] == ("governed_control_output_root")
    assert auragateway["control_discovery_failure_code"] == ("CONTROL_OUTPUT_NAMESPACE_COLLISION")
    assert auragateway["control_discovery_failure_evidence_sha256"] == (
        "55910873d6282ce8b98efd2726d2630bfed4f1c706eb4ec6484adb8a66885926"
    )
    assert auragateway["maximum_evidence_zip_bytes"] == (2 * 1024 * 1024)
    assert auragateway["maximum_worker_startup_diagnostic_bytes"] == (
        launcher.MAXIMUM_WORKER_STARTUP_DIAGNOSTIC_BYTES
    )
    assert auragateway["worker_startup_diagnostic_relative_path"] == (
        launcher.WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH
    )
    assert auragateway["benchmark_trajectory_requests_permitted"] == 0
    assert auragateway["authorization_source_binding_policy"] == (
        "CONTROL_PACKAGE_AUTHORIZATION_PARITY"
    )
    notebook_name = auragateway["notebook_name"]
    control_notebook_name = auragateway["control_notebook_name"]

    assert isinstance(notebook_name, str)
    assert isinstance(control_notebook_name, str)
    assert len(notebook_name) <= 50
    assert len(control_notebook_name) <= 50


def test_launcher_binds_reviewed_core_and_cold_session_guards(
    tmp_path: Path,
) -> None:
    _copy_reviewed_notebook(tmp_path)

    notebook = launcher.build_launcher_notebook(tmp_path)
    source = _code_source(notebook)

    ast.parse(source)

    assert max(len(line) for line in source.splitlines()) <= 100
    assert "\nimport shutil\n" not in source

    reviewed = json.loads((tmp_path / launcher.REVIEWED_NOTEBOOK_PATH).read_text(encoding="utf-8"))
    reviewed_cells = cast(list[dict[str, Any]], reviewed["cells"])
    reviewed_source_raw = reviewed_cells[1]["source"]
    reviewed_source = (
        reviewed_source_raw
        if isinstance(reviewed_source_raw, str)
        else "".join(cast(list[str], reviewed_source_raw))
    )
    reviewed_sha256 = hashlib.sha256(reviewed_source.encode("utf-8")).hexdigest()

    metadata = cast(dict[str, object], notebook["metadata"])
    auragateway = cast(dict[str, object], metadata["auragateway"])

    assert auragateway["reviewed_core_sha256"] == reviewed_sha256
    assert "EXPECTED_REVIEWED_CORE_SHA256" in source
    assert "base64.b64decode" in source
    assert "compile(" in source
    assert "exec(" in source

    assert "stale_runtime_keys" in source
    assert 'name == "vllm"' in source
    assert 'name == "transformers"' in source
    assert "pre-existing CUDA context" in source
    assert "vLLM worker ports are already open" in source
    assert "writable harness destination already exists" in source

    assert "resolve_control_output" in source
    assert "INPUT_ROOT.rglob(CONTROL_OUTPUT_DIRECTORY_NAME)" in source
    assert "exact_candidates" not in source
    assert "maximum_workers" in source
    assert "maximum_kaggle_sessions" in source
    assert "benchmark_trajectory_requests_permitted" in source
    assert "MINIMUM_LAUNCH_WINDOW_MINUTES = 120" in source
    assert "authorization_source_main_merge_commit = authorization.get(" in source
    assert "EXPECTED_AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT" not in source

    assert "RUNTIME_EVIDENCE_PATHS" in source
    assert "evidence_bundle_sha256.json" in source
    assert "launcher_summary.json" in source
    assert "launcher_failure.json" in source
    assert "worker_startup_diagnostic.json" in source
    assert "load_worker_startup_diagnostic" in source
    assert "worker_startup_diagnostic_included" in source
    assert "MAXIMUM_EVIDENCE_ZIP_BYTES = 2097152" in source
    assert "archive.write(path, arcname=archive_name)" in source
    assert "archive.write(" not in source.replace(
        "archive.write(path, arcname=archive_name)",
        "",
    )


def test_control_output_discovery_scopes_duplicate_manifest_to_governed_root() -> None:
    with _short_windows_safe_temp_root() as tmp_path:
        namespace = _launcher_runtime_namespace(tmp_path)
        input_root = cast(Path, namespace["INPUT_ROOT"])
        control_root = (
            input_root
            / "notebooks"
            / "kabomolefe"
            / launcher.CONTROL_NOTEBOOK_NAME
            / launcher.CONTROL_OUTPUT_DIRECTORY_NAME
        )
        _write_control_output(control_root)

        duplicate_manifest = input_root / "unrelated-harness-input" / launcher.DATASET_MANIFEST_PATH
        duplicate_manifest.parent.mkdir(parents=True)
        duplicate_manifest.write_text("{}", encoding="utf-8")

        resolver = cast(
            Callable[[], tuple[Path, Path, Path, Path]],
            namespace["resolve_control_output"],
        )
        observed = resolver()

        assert all(path.parent == control_root for path in observed)
        assert observed[1] == control_root / launcher.DATASET_MANIFEST_FILENAME
        assert duplicate_manifest.is_file()


def test_control_output_discovery_rejects_multiple_governed_roots() -> None:
    with _short_windows_safe_temp_root() as tmp_path:
        namespace = _launcher_runtime_namespace(tmp_path)
        input_root = cast(Path, namespace["INPUT_ROOT"])

        for owner in ("kabomolefe", "duplicate-owner"):
            _write_control_output(
                input_root
                / "notebooks"
                / owner
                / launcher.CONTROL_NOTEBOOK_NAME
                / launcher.CONTROL_OUTPUT_DIRECTORY_NAME
            )

        resolver = cast(
            Callable[[], tuple[Path, Path, Path, Path]],
            namespace["resolve_control_output"],
        )

        with pytest.raises(
            RuntimeError,
            match=r"governed control-output root; observed=2",
        ):
            resolver()


def test_control_output_discovery_rejects_non_flat_file_set() -> None:
    with _short_windows_safe_temp_root() as tmp_path:
        namespace = _launcher_runtime_namespace(tmp_path)
        input_root = cast(Path, namespace["INPUT_ROOT"])
        control_root = (
            input_root
            / "notebooks"
            / "kabomolefe"
            / launcher.CONTROL_NOTEBOOK_NAME
            / launcher.CONTROL_OUTPUT_DIRECTORY_NAME
        )
        _write_control_output(control_root)
        (control_root / "unexpected.json").write_text("{}", encoding="utf-8")

        resolver = cast(
            Callable[[], tuple[Path, Path, Path, Path]],
            namespace["resolve_control_output"],
        )

        with pytest.raises(RuntimeError, match="control output file set drifted"):
            resolver()


def test_launcher_notebook_verification_rejects_drift(
    tmp_path: Path,
) -> None:
    _copy_reviewed_notebook(tmp_path)

    notebook_path = tmp_path / "launcher.ipynb"
    summary = launcher.write_launcher_notebook(
        repo_root=tmp_path,
        output_path=notebook_path,
    )

    assert summary.notebook_name == launcher.LAUNCHER_NOTEBOOK_NAME
    assert summary.cell_count == 2
    assert summary.output_cells_present is False
    assert summary.execution_counts_present is False

    observed = json.loads(notebook_path.read_text(encoding="utf-8"))
    observed["metadata"]["auragateway"]["minimum_launch_window_minutes"] = 1
    notebook_path.write_text(
        json.dumps(observed, ensure_ascii=True),
        encoding="utf-8",
    )

    with pytest.raises(
        launcher.KaggleLauncherError,
        match="launcher notebook drifted",
    ):
        launcher.verify_launcher_notebook(
            repo_root=tmp_path,
            notebook_path=notebook_path,
        )


def test_launcher_separates_harness_and_authorization_source_authorities() -> None:
    assert launcher.SOURCE_MAIN_MERGE_COMMIT == ("dceda98989386de7a4d57616f9f8a8023f866f10")
    assert launcher.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT == (
        "211a10757999b1b110cb1d9df172938cf6ed7969"
    )
    assert launcher.AUTHORIZATION_SOURCE_BINDING_POLICY == ("CONTROL_PACKAGE_AUTHORIZATION_PARITY")
    assert launcher.HARNESS_SOURCE_PATH.endswith(
        "/ag_worker_obs_harness_materializer_v1_output/"
        "auragateway_qualification_harness_dceda98_worker_obs_v1"
    )


def test_control_materializer_source_is_flat_and_archive_free() -> None:
    authorization = {
        "decision": "AUTHORIZED",
        "source_main_merge_commit": (launcher.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT),
        "dataset_manifest_sha256": "a" * 64,
        "issued_at": "2026-07-19T12:00:00+00:00",
        "expires_at": "2026-07-19T16:00:00+00:00",
        "maximum_workers": 2,
        "maximum_kaggle_sessions": 1,
        "maximum_model_requests": 8,
        "maximum_output_tokens_per_request": 32,
        "benchmark_trajectory_requests_permitted": 0,
        "network_access_permitted": False,
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "external_spend": 0,
        "measured_execution_authorized": False,
    }
    manifest = {
        "entries": [
            {
                "role": "harness_source",
                "mounted_path": launcher.HARNESS_SOURCE_PATH,
            },
            {
                "role": "model_artifacts",
                "mounted_path": launcher.MODEL_SNAPSHOT_PATH,
            },
            {
                "role": "vllm_runtime",
                "artifact_format": "python_wheelhouse_directory",
                "mounted_path": None,
                "sha256": launcher.RUNTIME_SHA256_MANIFEST_SHA256,
                "runtime_output_directory": launcher.RUNTIME_OUTPUT_DIRECTORY,
                "resolution_lock_sha256": launcher.RUNTIME_RESOLUTION_LOCK_SHA256,
                "runtime_manifest_sha256": launcher.RUNTIME_MANIFEST_SHA256,
                "sha256_manifest_sha256": launcher.RUNTIME_SHA256_MANIFEST_SHA256,
                "materialization_receipt_sha256": (launcher.RUNTIME_MATERIALIZATION_RECEIPT_SHA256),
                "package_count": launcher.RUNTIME_PACKAGE_COUNT,
            },
        ]
    }

    source = launcher._control_materializer_source(
        authorization_bytes=json.dumps(
            authorization,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
        manifest_bytes=json.dumps(
            manifest,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
        authorization_contract_sha256="b" * 64,
        manifest_contract_sha256="a" * 64,
    )

    ast.parse(source)

    assert max(len(line) for line in source.splitlines()) <= 100
    assert "\nimport shutil\n" not in source
    assert "ag_qualification_control_v1" in source
    assert "file_count" in source
    assert '"file_count": 4' in source
    assert "nested_archives_present" in source
    assert "zipfile" not in source
    assert "shutil.copy" not in source
    assert "model_content_copied" in source
    assert "authorization_source_main_merge_commit = authorization.get(" in source
    assert "AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT =" not in source


def test_control_manifest_accepts_dynamic_authorization_source_commit() -> None:
    payload: dict[str, object] = {
        "control_package_id": "auragateway-qualification-control-v1",
        "source_main_merge_commit": launcher.SOURCE_MAIN_MERGE_COMMIT,
        "authorization_source_main_merge_commit": "f" * 40,
        "authorization_file": launcher.AUTHORIZATION_FILENAME,
        "authorization_file_sha256": "a" * 64,
        "authorization_contract_sha256": "b" * 64,
        "dataset_manifest_file": launcher.DATASET_MANIFEST_FILENAME,
        "dataset_manifest_file_sha256": "c" * 64,
        "dataset_manifest_contract_sha256": "d" * 64,
        "issued_at": "2026-07-22T12:00:00+00:00",
        "expires_at": "2026-07-22T16:00:00+00:00",
        "harness_source_path": launcher.HARNESS_SOURCE_PATH,
        "model_snapshot_path": launcher.MODEL_SNAPSHOT_PATH,
        "runtime_output_directory": launcher.RUNTIME_OUTPUT_DIRECTORY,
        "runtime_resolution_lock_sha256": launcher.RUNTIME_RESOLUTION_LOCK_SHA256,
        "runtime_manifest_sha256": launcher.RUNTIME_MANIFEST_SHA256,
        "runtime_sha256_manifest_sha256": launcher.RUNTIME_SHA256_MANIFEST_SHA256,
        "runtime_materialization_receipt_sha256": (launcher.RUNTIME_MATERIALIZATION_RECEIPT_SHA256),
        "runtime_package_count": launcher.RUNTIME_PACKAGE_COUNT,
    }

    parsed = launcher.KaggleControlPackageManifest.model_validate(payload)

    assert parsed.authorization_source_main_merge_commit == "f" * 40


def test_control_manifest_rejects_digest_drift() -> None:
    payload: dict[str, object] = {
        "control_package_id": "auragateway-qualification-control-v1",
        "source_main_merge_commit": launcher.SOURCE_MAIN_MERGE_COMMIT,
        "authorization_source_main_merge_commit": (launcher.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT),
        "authorization_file": launcher.AUTHORIZATION_FILENAME,
        "authorization_file_sha256": "x" * 64,
        "authorization_contract_sha256": "a" * 64,
        "dataset_manifest_file": launcher.DATASET_MANIFEST_FILENAME,
        "dataset_manifest_file_sha256": "b" * 64,
        "dataset_manifest_contract_sha256": "c" * 64,
        "issued_at": "2026-07-19T12:00:00+00:00",
        "expires_at": "2026-07-19T16:00:00+00:00",
        "harness_source_path": launcher.HARNESS_SOURCE_PATH,
        "model_snapshot_path": launcher.MODEL_SNAPSHOT_PATH,
        "runtime_output_directory": launcher.RUNTIME_OUTPUT_DIRECTORY,
        "runtime_resolution_lock_sha256": launcher.RUNTIME_RESOLUTION_LOCK_SHA256,
        "runtime_manifest_sha256": launcher.RUNTIME_MANIFEST_SHA256,
        "runtime_sha256_manifest_sha256": launcher.RUNTIME_SHA256_MANIFEST_SHA256,
        "runtime_materialization_receipt_sha256": (launcher.RUNTIME_MATERIALIZATION_RECEIPT_SHA256),
        "runtime_package_count": launcher.RUNTIME_PACKAGE_COUNT,
    }

    with pytest.raises(
        ValueError,
        match="lowercase SHA-256",
    ):
        launcher.KaggleControlPackageManifest.model_validate(payload)


def test_launcher_failure_path_writes_one_small_zip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    _copy_reviewed_notebook(repo_root)
    notebook = launcher.build_launcher_notebook(repo_root)
    source = _code_source(notebook)

    input_root = tmp_path / "kaggle" / "input"
    work_root = tmp_path / "kaggle" / "working"
    input_root.mkdir(parents=True)
    work_root.mkdir(parents=True)

    source = source.replace(
        'Path("/kaggle/input").resolve()',
        f"Path({str(input_root)!r}).resolve()",
        1,
    )
    source = source.replace(
        'Path("/kaggle/working").resolve()',
        f"Path({str(work_root)!r}).resolve()",
        1,
    )

    for key in tuple(os.environ):
        if key.startswith(("AURAGATEWAY_", "VLLM_")):
            monkeypatch.delenv(key, raising=False)

    with pytest.raises(
        RuntimeError,
        match="static input",
    ):
        exec(
            compile(source, "launcher_failure_test.py", "exec"),
            {},
        )

    evidence_zip = work_root / launcher.EVIDENCE_ZIP_NAME
    assert evidence_zip.is_file()
    assert evidence_zip.stat().st_size < launcher.MAXIMUM_EVIDENCE_ZIP_BYTES

    with zipfile.ZipFile(evidence_zip) as archive:
        assert set(archive.namelist()) == {
            "launcher_failure.json",
            "launcher_failure_trace.txt",
        }
        failure = json.loads(archive.read("launcher_failure.json").decode("utf-8"))

    assert failure["status"] == "FAILED"
    assert failure["benchmark_trajectory_requests_permitted"] == 0
    assert failure["customer_data_used"] is False
    assert failure["credentials_used"] is False
    assert failure["provider_calls_performed"] is False
    assert failure["worker_startup_diagnostic_included"] is False


def test_launcher_failure_bundle_embeds_worker_startup_diagnostic(
    tmp_path: Path,
) -> None:
    namespace = _launcher_runtime_namespace(tmp_path)
    work_root = cast(Path, namespace["WORK_ROOT"])
    harness_root = cast(Path, namespace["MATERIALIZED_HARNESS_ROOT"])
    relative = cast(str, namespace["WORKER_STARTUP_DIAGNOSTIC_RELATIVE_PATH"])
    diagnostic_path = harness_root / relative
    diagnostic_path.parent.mkdir(parents=True)

    def stream() -> dict[str, object]:
        return {
            "available": True,
            "observed_bytes": 0,
            "captured_bytes": 0,
            "truncated": False,
            "sha256": hashlib.sha256(b"").hexdigest(),
            "text": "",
        }

    workers = []
    for worker_id, gpu_index, port, digest in (
        ("worker_1", 0, 8001, "a" * 64),
        ("worker_2", 1, 8002, "b" * 64),
    ):
        workers.append(
            {
                "worker_id": worker_id,
                "gpu_index": gpu_index,
                "host": "127.0.0.1",
                "port": port,
                "command_sha256": digest,
                "ready": False,
                "process_returncode": 1,
                "poll_count": 1,
                "final_error_type": "WorkerProcessExited",
                "final_safe_error": "worker process exited",
                "readiness_history": [
                    {
                        "poll_index": 1,
                        "process_returncode": 1,
                        "http_status": None,
                        "error_type": "WorkerProcessExited",
                        "safe_error": "worker process exited",
                    }
                ],
                "stdout": stream(),
                "stderr": stream(),
                "hidden_retry_count": 0,
                "replacement_count": 0,
            }
        )
    diagnostic = {
        "schema_version": "1.0.0",
        "diagnostic_id": ("auragateway-environment-qualification-worker-startup-diagnostic-v1"),
        "status": "FAILED",
        "phase": "initial_startup",
        "captured_at": "2026-07-22T13:30:00+00:00",
        "failed_worker_id": "worker_1",
        "workers": workers,
        "raw_environment_included": False,
        "authorization_payload_included": False,
        "model_content_included": False,
        "hidden_retries_performed": 0,
        "workers_replaced": 0,
        "model_requests_performed": 0,
        "benchmark_trajectory_requests_performed": 0,
    }
    diagnostic_bytes = json.dumps(
        diagnostic,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    diagnostic_path.write_bytes(diagnostic_bytes)

    writer = cast(Callable[[BaseException], None], namespace["write_failure_bundle"])
    writer(RuntimeError("worker failed"))

    evidence_zip = work_root / launcher.EVIDENCE_ZIP_NAME
    with zipfile.ZipFile(evidence_zip) as archive:
        assert set(archive.namelist()) == {
            "launcher_failure.json",
            "launcher_failure_trace.txt",
            "worker_startup_diagnostic.json",
        }
        assert archive.read("worker_startup_diagnostic.json") == diagnostic_bytes
        failure = json.loads(archive.read("launcher_failure.json"))

    assert failure["worker_startup_diagnostic_included"] is True


def test_committed_launcher_matches_generator() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    notebook_path = repo_root / launcher.LAUNCHER_NOTEBOOK_PATH

    summary = launcher.verify_launcher_notebook(
        repo_root=repo_root,
        notebook_path=notebook_path,
    )

    assert summary.notebook_name == launcher.LAUNCHER_NOTEBOOK_NAME
    assert summary.notebook_sha256 == launcher._file_sha256(notebook_path)
