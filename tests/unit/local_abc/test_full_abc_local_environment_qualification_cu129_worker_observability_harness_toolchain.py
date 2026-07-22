"""Tests for the post-merge worker-observability harness source toolchain."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_worker_observability_harness_toolchain,
)

toolchain = full_abc_local_environment_qualification_cu129_worker_observability_harness_toolchain


def _git(repo: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
    )


def _source_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    for relative in toolchain.REQUIRED_SOURCE_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture={relative}\n", encoding="utf-8")
    extra = repo / "src/auragateway/local_abc/additional_module.py"
    extra.write_text("VALUE = 1\n", encoding="utf-8")
    historical = repo / "evidence_vault/local_abc/attempt/evidence.zip"
    historical.parent.mkdir(parents=True)
    historical.write_bytes(b"historical archive excluded from harness source")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    return repo


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def test_build_post_merge_package_is_deterministic_and_execution_free(
    tmp_path: Path,
) -> None:
    repo = _source_repo(tmp_path)
    commit = "a" * 40
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_summary = toolchain.build_post_merge_package(
        repo_root=repo,
        output_root=first,
        enforce_git_state=False,
        source_commit=commit,
    )
    second_summary = toolchain.build_post_merge_package(
        repo_root=repo,
        output_root=second,
        enforce_git_state=False,
        source_commit=commit,
    )

    assert first_summary["status"] == ("WORKER_OBSERVABILITY_HARNESS_SOURCE_PACKAGE_VALID")
    assert first_summary["archive_sha256"] == second_summary["archive_sha256"]
    assert first_summary["source_directory_sha256"] == (second_summary["source_directory_sha256"])
    assert first_summary["authorization_issued"] is False
    assert first_summary["kaggle_execution_performed"] is False
    assert first_summary["model_requests_performed"] == 0
    assert first_summary["active_manifest_promoted"] is False


def test_source_inventory_excludes_evidence_archives(tmp_path: Path) -> None:
    repo = _source_repo(tmp_path)
    output = tmp_path / "output"

    toolchain.build_post_merge_package(
        repo_root=repo,
        output_root=output,
        enforce_git_state=False,
        source_commit="b" * 40,
    )

    inventory = _load(output / "source_inventory.json")
    entries = cast(list[dict[str, object]], inventory["files"])
    paths = {str(entry["path"]) for entry in entries}

    assert not any(path.startswith("evidence_vault/") for path in paths)
    assert not any(path.lower().endswith(toolchain.ARCHIVE_SUFFIXES) for path in paths)
    assert set(toolchain.REQUIRED_SOURCE_PATHS).issubset(paths)


def test_materializer_notebook_is_cpu_only_and_has_no_execution_state(
    tmp_path: Path,
) -> None:
    repo = _source_repo(tmp_path)
    output = tmp_path / "output"

    toolchain.build_post_merge_package(
        repo_root=repo,
        output_root=output,
        enforce_git_state=False,
        source_commit="c" * 40,
    )

    notebook = _load(output / "ag_worker_obs_harness_materializer_v1.ipynb")
    metadata = cast(dict[str, Any], notebook["metadata"])
    kaggle = cast(dict[str, Any], metadata["kaggle"])
    cells = cast(list[dict[str, Any]], notebook["cells"])
    source = "".join(cast(list[str], cells[1]["source"]))

    assert kaggle["accelerator"] == "none"
    assert kaggle["isInternetEnabled"] is False
    assert kaggle["dataSources"] == []
    assert cells[1]["execution_count"] is None
    assert cells[1]["outputs"] == []
    assert "model_requests_performed=0" in source
    assert "gpu_execution_performed=false" in source
    assert "validated_member_path" in source
    assert "encrypted member" in source
    assert "nested archive" in source


def test_receipt_requires_source_bound_names() -> None:
    payload: dict[str, object] = {
        "status": "WORKER_OBSERVABILITY_HARNESS_SOURCE_PACKAGED",
        "source_commit": "d" * 40,
        "source_short_commit": "d" * 7,
        "review_merge_commit": toolchain.REVIEW_MERGE_COMMIT,
        "archive_filename": "ag-worker-obs-harness-stale-v1.zip",
        "archive_sha256": "a" * 64,
        "source_inventory_filename": "source_inventory.json",
        "source_inventory_sha256": "b" * 64,
        "source_directory_sha256": "c" * 64,
        "source_file_count": 1,
        "source_total_bytes": 1,
        "materializer_notebook_filename": ("ag_worker_obs_harness_materializer_v1.ipynb"),
        "materializer_notebook_name": toolchain.NOTEBOOK_NAME,
        "input_dataset_name": "ag-worker-obs-harness-stale-v1-input",
        "output_directory": "auragateway_qualification_harness_stale",
    }

    try:
        toolchain.HarnessSourceReceipt.model_validate(payload)
    except ValueError:
        return
    raise AssertionError("source-unbound package names were accepted")
