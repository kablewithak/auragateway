from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_harness_toolchain as toolchain,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_harness_toolchain_contracts,
)

toolchain_contracts = full_abc_local_environment_qualification_cu129_harness_toolchain_contracts

ROOT = Path(__file__).resolve().parents[3]


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _create_repository(root: Path) -> str:
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (root / ".gitattributes").write_text("src/subst.txt export-subst\n", encoding="utf-8")
    (root / "src/example.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "src/subst.txt").write_text("$Format:%H$\n", encoding="utf-8")
    _git(root, "init", "-b", "main")
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=AuraGateway Tests",
        "-c",
        "user.email=tests@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    return _git(root, "rev-parse", "HEAD")


def _fixture_spec(commit: str) -> toolchain_contracts.HarnessBuildSpec:
    return toolchain_contracts.HarnessBuildSpec(
        package_id="test-harness-package",
        source_commit=commit,
        archive_name="test-harness.zip",
        input_dataset_name="test-harness-input",
        output_directory="test-harness-output",
        materialization_receipt_name="test-receipt.json",
        required_paths=("README.md", "pyproject.toml", "src/example.py"),
        expected_file_sha256={},
        maximum_files=20,
        maximum_total_bytes=100_000,
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def _source_receipt(
    *,
    archive_sha256: str = "2" * 64,
) -> toolchain_contracts.HarnessSourcePackageReceipt:
    return toolchain_contracts.HarnessSourcePackageReceipt(
        status="CURRENT_CU129_HARNESS_SOURCE_PACKAGED",
        package_id="test-harness-package",
        source_commit="1" * 40,
        archive_name="test-harness.zip",
        archive_sha256=archive_sha256,
        inventory_sha256="3" * 64,
        output_directory="test-harness-output",
        input_dataset_name="test-harness-input",
        materialization_receipt_name="test-receipt.json",
        directory_sha256="4" * 64,
        file_count=3,
        total_bytes=100,
        required_paths=("README.md", "pyproject.toml", "src/example.py"),
        expected_file_sha256={},
    )


def _copy_repository_validator_fixture(destination: Path) -> None:
    relative_paths: set[Path] = {
        Path("pyproject.toml"),
        Path(toolchain.RUFF_CONFIG_PATH),
        Path(toolchain.HISTORICAL_MATERIALIZER_NOTEBOOK_PATH),
        Path(toolchain.REVIEW_RECORD_PATH),
        Path(toolchain.TOOLCHAIN_RECORD_PATH),
        Path(toolchain.OFFLINE_MANIFEST_PATH),
        Path(
            "data/evals/benchmark/environment-qualification-v1/"
            "offline_dataset_materialization_record.json"
        ),
        Path(
            "benchmarks/local_abc/"
            "auragateway_cu129_worker_observability_harness_evidence_integration_v1.json"
        ),
        Path(
            "benchmarks/local_abc/"
            "auragateway_cu129_worker_observability_fresh_authorization_readiness_review_v1.json"
        ),
        Path(
            "docs/adr/"
            "2026-07-23-local-abc-cu129-worker-observability-harness-evidence-integration.md"
        ),
        Path(
            "docs/reports/"
            "AuraGateway_CU129_Worker_Observability_Harness_Operational_Input_Closure_Report.md"
        ),
        Path(
            "docs/runbooks/local_abc_cu129_worker_observability_harness_evidence_integration_v1.md"
        ),
        Path("docs/runbooks/local_abc_full_run_environment_qualification_kaggle_launcher_v1.md"),
        Path(
            "docs/runbooks/"
            "local_abc_full_run_environment_qualification_authorization_issuance_v1.md"
        ),
        Path("notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb"),
        Path("notebooks/auragateway_full_abc_environment_qualification_v1.ipynb"),
        Path(
            "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
        ),
        Path(
            "src/auragateway/local_abc/"
            "full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
        ),
        Path(
            "src/auragateway/local_abc/"
            "full_abc_local_environment_qualification_worker_startup_diagnostics.py"
        ),
        Path(
            "evidence_vault/local_abc/"
            "cu129-worker-observability-harness-input-inspection-v1/evidence_identity.json"
        ),
        Path(
            "evidence_vault/local_abc/"
            "cu129-worker-observability-harness-input-inspection-v1/materialization_receipt.json"
        ),
        Path(
            "evidence_vault/local_abc/"
            "cu129-worker-observability-harness-input-inspection-v1/"
            "ag-worker-obs-harness-materializer-v1.log"
        ),
        Path(
            "evidence_vault/local_abc/"
            "cu129-worker-observability-harness-input-inspection-v1/"
            "ag-worker-obs-input-inspection-v1.log"
        ),
        Path(
            "evidence_vault/local_abc/"
            "cu129-worker-observability-harness-input-inspection-v1/"
            "ag-worker-obs-input-inspection-v1.zip"
        ),
        Path(
            "evidence_vault/local_abc/"
            "cu129-worker-observability-harness-input-inspection-v1/"
            "ag_worker_obs_harness_materializer_v1_recovery.ipynb"
        ),
        *(Path(path) for path in toolchain.EXPECTED_FILE_SHA256),
    }
    for relative_path in relative_paths:
        source = ROOT / relative_path
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def test_default_spec_derives_names_from_exact_source_commit() -> None:
    source_commit = "1234567" + "8" * 33
    spec = toolchain.default_build_spec(source_commit)

    assert spec.source_commit == source_commit
    assert spec.archive_name == "ag-harness-1234567-v1.zip"
    assert spec.input_dataset_name == "ag-harness-1234567-v1-input"
    assert spec.output_directory == "auragateway_qualification_harness_1234567_v1"
    assert spec.expected_file_sha256[toolchain.RUNTIME_ADAPTER_PATH] == (
        toolchain.CURRENT_RUNTIME_ADAPTER_SHA256
    )
    assert spec.expected_file_sha256[toolchain.CU129_RUNTIME_PATH] == (
        toolchain.CURRENT_CU129_RUNTIME_SHA256
    )
    assert spec.expected_file_sha256[toolchain.LAUNCHER_NOTEBOOK_PATH] == (
        toolchain.CURRENT_LAUNCHER_NOTEBOOK_SHA256
    )


def test_repository_package_exposes_approved_toolchain_boundary() -> None:
    summary = toolchain.validate_repository_package(ROOT)

    assert summary["status"] == "CURRENT_CU129_HARNESS_TOOLCHAIN_IMPLEMENTED"
    assert summary["decision"] == "APPROVED_FOR_COMPLETE_CURRENT_CU129_HARNESS_TOOLCHAIN"
    assert summary["review_minimum_ancestor"] == toolchain.REVIEW_MINIMUM_ANCESTOR
    assert summary["source_binding_policy"] == "POST_MERGE_CLEAN_MAIN_HEAD"
    assert summary["runtime_role"] == "vllm_runtime"
    assert summary["runtime_package_count"] == 176
    assert summary["active_harness_binding_status"] == (
        "WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED"
    )
    assert summary["operational_input_closure"] == "PASSED"
    assert summary["authorization_issued"] is False
    assert summary["model_requests_performed"] == 0


def test_repository_validator_rejects_duplicate_manifest_role(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _copy_repository_validator_fixture(root)
    manifest_path = root / toolchain.OFFLINE_MANIFEST_PATH
    manifest = _load_json(manifest_path)
    entries = cast(list[dict[str, Any]], manifest["entries"])
    entries.append(dict(entries[0]))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(toolchain.HarnessToolchainError) as captured:
        toolchain.validate_repository_package(root)

    assert captured.value.error_code == "HARNESS_TOOLCHAIN_MANIFEST_DUPLICATE_ROLE"


def test_source_archive_uses_exact_git_blob_bytes_and_is_deterministic(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    commit = _create_repository(repo)
    spec = _fixture_spec(commit)
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_receipt = toolchain.build_source_package(
        repo,
        first,
        spec,
        validate_current_boundary=False,
    )
    second_receipt = toolchain.build_source_package(
        repo,
        second,
        spec,
        validate_current_boundary=False,
    )

    assert first_receipt == second_receipt
    assert (first / spec.archive_name).read_bytes() == (second / spec.archive_name).read_bytes()
    with zipfile.ZipFile(first / spec.archive_name) as archive:
        assert archive.read("src/subst.txt") == b"$Format:%H$\n"
    summary = toolchain.verify_source_package(first)
    assert summary["status"] == "CURRENT_CU129_HARNESS_SOURCE_PACKAGE_VERIFIED"
    assert summary["source_dataset_file_count"] == 4
    assert summary["authorization_issued"] is False
    assert summary["model_requests_performed"] == 0


def test_archive_metadata_is_canonical(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    commit = _create_repository(repo)
    spec = _fixture_spec(commit)
    output = tmp_path / "output"

    toolchain.build_source_package(repo, output, spec, validate_current_boundary=False)

    with zipfile.ZipFile(output / spec.archive_name) as archive:
        members = archive.infolist()
        assert [member.filename for member in members] == sorted(
            member.filename for member in members
        )
        assert all(member.date_time == toolchain.ZIP_TIMESTAMP for member in members)
        assert all(member.flag_bits & 0x1 == 0 for member in members)
        assert all(member.compress_type == zipfile.ZIP_DEFLATED for member in members)


def test_git_tree_parser_rejects_symlink_and_nested_archive() -> None:
    with pytest.raises(toolchain.HarnessToolchainError) as symlink:
        toolchain._parse_git_tree(b"120000 blob " + b"0" * 40 + b"\tlink\0")
    assert symlink.value.error_code == "HARNESS_TOOLCHAIN_NON_REGULAR_ENTRY_REJECTED"

    with pytest.raises(toolchain.HarnessToolchainError) as nested:
        toolchain._parse_git_tree(b"100644 blob " + b"0" * 40 + b"\tevidence.zip\0")
    assert nested.value.error_code == "HARNESS_TOOLCHAIN_NESTED_ARCHIVE_REJECTED"


def test_archive_verifier_rejects_duplicate_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "duplicate.zip"
    payload = b"value\n"
    entry = toolchain_contracts.HarnessSourceInventoryEntry(
        path="value.txt",
        git_blob_sha="0" * 40,
        sha256=toolchain._sha256_bytes(payload),
        size_bytes=len(payload),
    )
    with zipfile.ZipFile(archive_path, "w") as archive:
        info = zipfile.ZipInfo("value.txt", date_time=toolchain.ZIP_TIMESTAMP)
        info.create_system = 3
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, payload)
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr(info, payload)

    with pytest.raises(toolchain.HarnessToolchainError) as captured:
        toolchain._validate_archive_against_inventory(archive_path, (entry,))

    assert captured.value.error_code == "HARNESS_TOOLCHAIN_ARCHIVE_DUPLICATE_MEMBER"


def test_generated_notebooks_are_clean_compilable_and_fully_bound(
    tmp_path: Path,
) -> None:
    receipt = _source_receipt()

    materializer, inspection = toolchain.generate_notebooks(receipt, tmp_path)

    assert materializer.notebook_name == toolchain.MATERIALIZER_NOTEBOOK_NAME
    assert inspection.notebook_name == toolchain.INSPECTION_NOTEBOOK_NAME
    assert materializer.outputs_present is False
    assert inspection.execution_counts_present is False

    materializer_payload = _load_json(tmp_path / materializer.filename)
    inspection_payload = _load_json(tmp_path / inspection.filename)
    for payload in (materializer_payload, inspection_payload):
        cells = cast(list[dict[str, Any]], payload["cells"])
        assert cells[1]["execution_count"] is None
        assert cells[1]["outputs"] == []

    materializer_source = "".join(
        cast(list[str], cast(list[dict[str, Any]], materializer_payload["cells"])[1]["source"])
    )
    inspection_source = "".join(
        cast(list[str], cast(list[dict[str, Any]], inspection_payload["cells"])[1]["source"])
    )
    assert "EXPECTED_DATASET_FILES" in materializer_source
    assert "source_packaging_receipt.json" in materializer_source
    assert "sha256_manifest.json" in materializer_source
    assert "except Exception" not in materializer_source
    assert "resolve_materializer_pair" in inspection_source
    assert "runtime wheel directory package count drifted" in inspection_source
    assert "HISTORICAL_PENDING_EVIDENCE_INTEGRATION" in inspection_source
    assert "historical_adapter_resolved" in inspection_source
    assert "METADATA_INPUT_INSPECTION_FAILED" in inspection_source
    assert "wheel_payloads_rehashed" in inspection_source
    assert "execute_from_environment()" not in inspection_source


def test_prepare_is_atomic_and_removes_staging_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    commit = _create_repository(repo)
    spec = _fixture_spec(commit)
    output = tmp_path / "prepared"
    original_builder = toolchain.build_source_package

    monkeypatch.setattr(toolchain, "_validate_prepare_repository", lambda repo_root: commit)
    monkeypatch.setattr(toolchain, "default_build_spec", lambda source_commit: spec)

    def build_fixture(
        repo_root: Path,
        output_root: Path,
        build_spec: toolchain_contracts.HarnessBuildSpec,
        *,
        validate_current_boundary: bool,
    ) -> toolchain_contracts.HarnessSourcePackageReceipt:
        assert validate_current_boundary is True
        return original_builder(
            repo_root,
            output_root,
            build_spec,
            validate_current_boundary=False,
        )

    def fail_generation(
        receipt: toolchain_contracts.HarnessSourcePackageReceipt,
        output_root: Path,
    ) -> tuple[
        toolchain_contracts.GeneratedNotebookReceipt,
        toolchain_contracts.GeneratedNotebookReceipt,
    ]:
        del receipt, output_root
        raise toolchain.HarnessToolchainError("TEST_FAILURE", "injected generation failure")

    monkeypatch.setattr(toolchain, "build_source_package", build_fixture)
    monkeypatch.setattr(toolchain, "generate_notebooks", fail_generation)

    with pytest.raises(toolchain.HarnessToolchainError) as captured:
        toolchain.prepare_current_toolchain(repo, output)

    assert captured.value.error_code == "TEST_FAILURE"
    assert not output.exists()
    assert not tuple(tmp_path.glob(".prepared.staging-*"))


def test_prepare_generates_and_verifies_exact_seven_file_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    commit = _create_repository(repo)
    spec = _fixture_spec(commit)
    output = tmp_path / "prepared"
    original_builder = toolchain.build_source_package

    monkeypatch.setattr(toolchain, "_validate_prepare_repository", lambda repo_root: commit)
    monkeypatch.setattr(toolchain, "default_build_spec", lambda source_commit: spec)

    def build_fixture(
        repo_root: Path,
        output_root: Path,
        build_spec: toolchain_contracts.HarnessBuildSpec,
        *,
        validate_current_boundary: bool,
    ) -> toolchain_contracts.HarnessSourcePackageReceipt:
        assert validate_current_boundary is True
        return original_builder(
            repo_root,
            output_root,
            build_spec,
            validate_current_boundary=False,
        )

    monkeypatch.setattr(toolchain, "build_source_package", build_fixture)

    prepared = toolchain.prepare_current_toolchain(repo, output)
    summary = toolchain.verify_prepared_toolchain(output)

    assert output.is_dir()
    assert len(tuple(output.iterdir())) == 7
    assert set(path.name for path in output.iterdir()) == set(prepared.output_filenames)
    assert summary["status"] == "CURRENT_CU129_HARNESS_TOOLCHAIN_VERIFIED"
    assert summary["output_file_count"] == 7
    assert summary["authorization_issued"] is False


def _configure_origin(root: Path) -> Path:
    origin = root.parent / f"{root.name}-origin.git"
    _git(origin.parent, "init", "--bare", str(origin))
    _git(root, "remote", "add", "origin", str(origin))
    _git(root, "push", "-u", "origin", "main")
    return origin


def test_prepare_repository_returns_synced_post_review_main_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    review_commit = _create_repository(repo)
    (repo / "post_review.txt").write_text("merged toolchain\n", encoding="utf-8")
    _git(repo, "add", "post_review.txt")
    _git(
        repo,
        "-c",
        "user.name=AuraGateway Tests",
        "-c",
        "user.email=tests@example.invalid",
        "commit",
        "-m",
        "post review",
    )
    final_commit = _git(repo, "rev-parse", "HEAD")
    _configure_origin(repo)
    monkeypatch.setattr(toolchain, "REVIEW_MINIMUM_ANCESTOR", review_commit)

    assert toolchain._validate_prepare_repository(repo) == final_commit


def test_prepare_repository_rejects_review_commit_as_final_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    review_commit = _create_repository(repo)
    _configure_origin(repo)
    monkeypatch.setattr(toolchain, "REVIEW_MINIMUM_ANCESTOR", review_commit)

    with pytest.raises(toolchain.HarnessToolchainError) as captured:
        toolchain._validate_prepare_repository(repo)

    assert captured.value.error_code == "HARNESS_TOOLCHAIN_POST_MERGE_SOURCE_REQUIRED"


def test_prepare_repository_rejects_unsynced_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    review_commit = _create_repository(repo)
    _configure_origin(repo)
    (repo / "local_only.txt").write_text("local commit\n", encoding="utf-8")
    _git(repo, "add", "local_only.txt")
    _git(
        repo,
        "-c",
        "user.name=AuraGateway Tests",
        "-c",
        "user.email=tests@example.invalid",
        "commit",
        "-m",
        "local only",
    )
    monkeypatch.setattr(toolchain, "REVIEW_MINIMUM_ANCESTOR", review_commit)

    with pytest.raises(toolchain.HarnessToolchainError) as captured:
        toolchain._validate_prepare_repository(repo)

    assert captured.value.error_code == "HARNESS_TOOLCHAIN_MAIN_NOT_SYNCED"


def test_output_inside_repository_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(toolchain.HarnessToolchainError) as captured:
        toolchain._validate_output_placement(repo.resolve(), (repo / "generated").resolve())

    assert captured.value.error_code == ("HARNESS_TOOLCHAIN_OUTPUT_INSIDE_REPOSITORY_REJECTED")


def test_verify_rejects_source_archive_tampering(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    commit = _create_repository(repo)
    spec = _fixture_spec(commit)
    output = tmp_path / "output"
    toolchain.build_source_package(repo, output, spec, validate_current_boundary=False)
    archive = output / spec.archive_name
    archive.write_bytes(archive.read_bytes() + b"tamper")

    with pytest.raises(toolchain.HarnessToolchainError) as captured:
        toolchain.verify_source_package(output)

    assert captured.value.error_code == "HARNESS_TOOLCHAIN_ARCHIVE_IDENTITY_DRIFT"
