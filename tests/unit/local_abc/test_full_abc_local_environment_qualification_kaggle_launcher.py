from __future__ import annotations

import ast
import hashlib
import json
import os
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
    assert auragateway["maximum_evidence_zip_bytes"] == (2 * 1024 * 1024)
    assert auragateway["benchmark_trajectory_requests_permitted"] == 0
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

    assert "maximum_workers" in source
    assert "maximum_kaggle_sessions" in source
    assert "benchmark_trajectory_requests_permitted" in source
    assert "MINIMUM_LAUNCH_WINDOW_MINUTES = 120" in source

    assert "RUNTIME_EVIDENCE_PATHS" in source
    assert "evidence_bundle_sha256.json" in source
    assert "launcher_summary.json" in source
    assert "launcher_failure.json" in source
    assert "MAXIMUM_EVIDENCE_ZIP_BYTES = 2097152" in source
    assert "archive.write(path, arcname=archive_name)" in source
    assert "archive.write(" not in source.replace(
        "archive.write(path, arcname=archive_name)",
        "",
    )


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
                "role": "vllm_wheel",
                "mounted_path": launcher.VLLM_WHEEL_PATH,
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
        "vllm_wheel_path": launcher.VLLM_WHEEL_PATH,
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

    import zipfile

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


def test_committed_launcher_matches_generator() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    notebook_path = repo_root / launcher.LAUNCHER_NOTEBOOK_PATH

    summary = launcher.verify_launcher_notebook(
        repo_root=repo_root,
        notebook_path=notebook_path,
    )

    assert summary.notebook_name == launcher.LAUNCHER_NOTEBOOK_NAME
    assert summary.notebook_sha256 == launcher._file_sha256(notebook_path)
