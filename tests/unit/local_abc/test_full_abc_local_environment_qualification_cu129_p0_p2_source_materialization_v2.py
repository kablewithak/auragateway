"""Tests for the P0-P2 source materialization V2 toolchain."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Literal, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_p0_p2_source_materialization_v2 as subject,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _synthetic_notebook() -> bytes:
    payload = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Synthetic\n"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": ["value = 1\n"],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _write_fixture_repo(
    tmp_path: Path,
) -> tuple[Path, tuple[subject.SourceArtifactBinding, ...]]:
    repo_root = tmp_path / "repo"
    source_payloads = (
        (
            "diagnostic_notebook",
            "notebooks/source.ipynb",
            "source.ipynb",
            _synthetic_notebook(),
        ),
        (
            "diagnostic_request",
            "data/request.json",
            "request.json",
            b'{"request":true}',
        ),
        (
            "implementation_record",
            "benchmarks/record.json",
            "record.json",
            b'{"record":true}',
        ),
    )
    bindings: list[subject.SourceArtifactBinding] = []
    for role, repository_path, output_name, payload in source_payloads:
        path = repo_root / repository_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        bindings.append(
            subject.SourceArtifactBinding(
                role=cast(
                    Literal[
                        "diagnostic_notebook",
                        "diagnostic_request",
                        "implementation_record",
                    ],
                    role,
                ),
                repository_path=repository_path,
                output_name=output_name,
                sha256=_sha256(payload),
                size_bytes=len(payload),
            )
        )

    for relative in (
        subject.MATERIALIZER_TEMPLATE_PATH,
        subject.INSPECTION_TEMPLATE_PATH,
    ):
        source = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "auragateway"
            / "local_abc"
            / "templates"
            / relative.name
        )
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    return repo_root, tuple(bindings)


def _code_source(notebook_bytes: bytes) -> str:
    raw = json.loads(notebook_bytes.decode("utf-8"))
    assert isinstance(raw, dict)
    cells = raw["cells"]
    assert isinstance(cells, list)
    code_cell = cells[1]
    assert isinstance(code_cell, dict)
    source = code_cell["source"]
    assert isinstance(source, list)
    return "".join(cast(list[str], source))


def test_kaggle_resource_names_fit_limit() -> None:
    names = (
        subject.MATERIALIZER_NOTEBOOK_NAME,
        subject.INSPECTION_NOTEBOOK_NAME,
        subject.MATERIALIZER_FAILED_NOTEBOOK_NAME,
        subject.INSPECTION_FAILED_NOTEBOOK_NAME,
        subject.OUTPUT_DATASET_NAME,
    )

    assert all(len(name) <= subject.MAXIMUM_KAGGLE_NAME_CHARACTERS for name in names)


def test_source_bundle_is_byte_deterministic(tmp_path: Path) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)

    first = subject.build_source_bundle(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )
    second = subject.build_source_bundle(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )

    assert first == second


def test_source_bundle_has_safe_fixed_members(tmp_path: Path) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)
    bundle_bytes, _, _ = subject.build_source_bundle(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )

    bundle_path = tmp_path / "bundle.zip"
    bundle_path.write_bytes(bundle_bytes)
    with zipfile.ZipFile(bundle_path) as archive:
        members = archive.infolist()

    assert tuple(member.filename for member in members) == (
        "bundle_manifest.json",
        "record.json",
        "request.json",
        "source.ipynb",
    )
    assert all(member.date_time == subject.ZIP_TIMESTAMP for member in members)
    assert all(not member.is_dir() for member in members)


def test_generated_notebooks_compile_and_respect_line_policy(
    tmp_path: Path,
) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)

    toolchain = subject.build_generated_toolchain(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )

    for label, notebook_bytes in (
        ("materializer", toolchain.materializer_notebook_bytes),
        ("inspection", toolchain.inspection_notebook_bytes),
    ):
        source = _code_source(notebook_bytes)
        compile(source, label, "exec")
        assert max(len(line) for line in source.splitlines()) <= 100
        assert "lines.extend([" not in source


def test_generated_notebooks_are_unexecuted(tmp_path: Path) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)
    toolchain = subject.build_generated_toolchain(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )

    for notebook_bytes in (
        toolchain.materializer_notebook_bytes,
        toolchain.inspection_notebook_bytes,
    ):
        raw = json.loads(notebook_bytes.decode("utf-8"))
        assert isinstance(raw, dict)
        cells = raw["cells"]
        assert isinstance(cells, list)
        assert len(cells) == 2
        code_cell = cells[1]
        assert isinstance(code_cell, dict)
        assert code_cell["outputs"] == []
        assert code_cell["execution_count"] is None


def test_embedded_bundle_uses_fixed_width_chunks(tmp_path: Path) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)
    toolchain = subject.build_generated_toolchain(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )
    source = _code_source(toolchain.materializer_notebook_bytes)

    chunk_lines = [
        line for line in source.splitlines() if line.startswith('    "') and line.endswith('"')
    ]

    assert chunk_lines
    assert all(len(line) <= subject.BASE64_CHUNK_WIDTH + 6 for line in chunk_lines)


def test_source_identity_drift_is_rejected(tmp_path: Path) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)
    source_path = repo_root / bindings[0].repository_path
    source_path.write_bytes(b"tampered")

    with pytest.raises(
        subject.P0P2SourceMaterializationV2Error,
        match=r"identity|size",
    ):
        subject.build_source_bundle(
            repo_root,
            bindings,
            source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
        )


def test_unsafe_output_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        subject.SourceArtifactBinding(
            role="diagnostic_request",
            repository_path="data/request.json",
            output_name="../request.json",
            sha256="0" * 64,
            size_bytes=1,
        )


def test_generation_is_byte_deterministic(tmp_path: Path) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)

    first = subject.build_generated_toolchain(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )
    second = subject.build_generated_toolchain(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )

    assert first.materializer_notebook_bytes == second.materializer_notebook_bytes
    assert first.inspection_notebook_bytes == second.inspection_notebook_bytes
    assert first.record == second.record


def test_review_record_rejects_missing_architecture_gate() -> None:
    payload = {
        "record_id": ("auragateway-cu129-p0-p2-source-materialization-review-v2"),
        "decision": "CLEAN_GLOBAL_REBUILD",
        "rejected_architecture": ("NESTED_STRING_FRAGMENT_CODE_GENERATION"),
        "source_main_base_commit": subject.SOURCE_MAIN_BASE_COMMIT,
        "architecture_origin_branch": subject.ARCHITECTURE_ORIGIN_BRANCH,
        "source_artifacts": [
            binding.model_dump(mode="json") for binding in subject.SOURCE_BINDINGS
        ],
        "source_bundle_name": subject.SOURCE_BUNDLE_NAME,
        "materializer_notebook_name": subject.MATERIALIZER_NOTEBOOK_NAME,
        "inspection_notebook_name": subject.INSPECTION_NOTEBOOK_NAME,
        "output_dataset_name": subject.OUTPUT_DATASET_NAME,
        "architecture_requirements": [
            "deterministic_source_bundle",
        ],
        "prohibited_techniques": [
            "manual_generated_notebook_edits",
            "nested_lines_extend_program_construction",
            "whitespace_sensitive_source_surgery",
            "broad_ruff_format",
            "runtime_or_kaggle_execution",
        ],
        "safety": subject.SafetyRecord().model_dump(mode="json"),
        "next_gate": "execute_cpu_only_p0_p2_source_materializer_v2",
    }

    with pytest.raises(ValidationError):
        subject.SourceMaterializationReviewRecord.model_validate(payload)


def test_generate_and_validate_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)
    monkeypatch.setattr(subject, "SOURCE_BINDINGS", bindings)

    review = subject.SourceMaterializationReviewRecord(
        record_id=("auragateway-cu129-p0-p2-source-materialization-review-v2"),
        decision="CLEAN_GLOBAL_REBUILD",
        rejected_architecture="NESTED_STRING_FRAGMENT_CODE_GENERATION",
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
        architecture_origin_branch=subject.ARCHITECTURE_ORIGIN_BRANCH,
        source_artifacts=bindings,
        source_bundle_name=subject.SOURCE_BUNDLE_NAME,
        materializer_notebook_name=subject.MATERIALIZER_NOTEBOOK_NAME,
        inspection_notebook_name=subject.INSPECTION_NOTEBOOK_NAME,
        output_dataset_name=subject.OUTPUT_DATASET_NAME,
        architecture_requirements=(
            "deterministic_source_bundle",
            "fixed_width_base64_chunks",
            "ordinary_multiline_notebook_templates",
            "safe_bundle_member_validation",
            "two_build_byte_determinism",
            "generated_source_compile_and_line_length_gates",
        ),
        prohibited_techniques=(
            "manual_generated_notebook_edits",
            "nested_lines_extend_program_construction",
            "whitespace_sensitive_source_surgery",
            "broad_ruff_format",
            "runtime_or_kaggle_execution",
        ),
        safety=subject.SafetyRecord(),
        next_gate="execute_cpu_only_p0_p2_source_materializer_v2",
    )
    review_path = repo_root / subject.REVIEW_RECORD_PATH
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        review.canonical_json(),
        encoding="utf-8",
    )

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert validated == generated


def test_lineage_contract_uses_base_commit_semantics(tmp_path: Path) -> None:
    repo_root, bindings = _write_fixture_repo(tmp_path)
    toolchain = subject.build_generated_toolchain(
        repo_root,
        bindings,
        source_main_base_commit=subject.SOURCE_MAIN_BASE_COMMIT,
    )
    manifest = json.loads(toolchain.bundle_manifest_bytes.decode("utf-8"))
    assert isinstance(manifest, dict)
    assert manifest["source_main_base_commit"] == subject.SOURCE_MAIN_BASE_COMMIT
    assert manifest["option_c_decision_merge_commit"] == subject.OPTION_C_DECISION_MERGE_COMMIT
    assert "source_repository_commit" not in manifest
    assert "diagnostic_source_main_merge_commit" not in manifest

    materializer_source = _code_source(toolchain.materializer_notebook_bytes)
    inspection_source = _code_source(toolchain.inspection_notebook_bytes)
    for source in (materializer_source, inspection_source):
        assert "EXPECTED_SOURCE_MAIN_BASE_COMMIT" in source
        assert '"source_main_base_commit"' in source
        assert "EXPECTED_SOURCE_REPOSITORY_COMMIT" not in source
        assert '"source_repository_commit"' not in source


def test_lineage_remediation_record_has_no_legacy_authority_fields() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    payload = json.loads(
        (repo_root / subject.LINEAGE_REMEDIATION_RECORD_PATH).read_text(encoding="utf-8")
    )
    assert isinstance(payload, dict)
    assert payload["source_main_base_commit"] == subject.SOURCE_MAIN_BASE_COMMIT
    assert payload["architecture_origin_branch"] == subject.ARCHITECTURE_ORIGIN_BRANCH
    assert payload["legacy_fields_rejected"] == [
        "branch_name",
        "diagnostic_source_main_merge_commit",
        "source_main_merge_commit",
        "source_repository_commit",
    ]
