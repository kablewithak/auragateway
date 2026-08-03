"""Tests for P3-P6 runtime evidence-contract hardening V4 assets."""

from __future__ import annotations

import io
import json
import shutil
import types
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v4 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    required = (
        subject.FAILURE_ACCEPTANCE_RECORD_PATH,
        subject.FAILURE_ACCEPTANCE_REVIEW_PATH,
        subject.V3_IMPLEMENTATION_RECORD_PATH,
        subject.V3_TEMPLATE_PATH,
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
    module = types.ModuleType("auragateway_p3_p6_runtime_diagnostic_v4_runtime")
    exec(
        compile(source, subject.TEMPLATE_PATH.as_posix(), "exec"),
        module.__dict__,
    )
    return module


def test_generate_validate_round_trip(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.record.status == "IMPLEMENTED_NOT_EXECUTED"
    assert generated.record.source_main_commit == subject.SOURCE_MAIN_COMMIT
    assert generated.record.notebook.runtime_script_sha256
    assert generated.record.notebook.wrapper_code_sha256


def test_v3_failure_acceptance_is_exact_authority(tmp_path: Path) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request

    assert tuple(item.authority_id for item in request.accepted_authorities) == (
        "v3_failure_acceptance_record",
        "v3_failure_acceptance_review",
        "v3_implementation_record",
    )
    failure = request.known_v3_failure
    assert failure.saved_version_id == 339943910
    assert failure.lifecycle_outcome == "FAILED"
    assert failure.evidence_disposition == "QUARANTINED_INVALID_DIAGNOSTIC"
    assert failure.triton_attn_startup_selection_established is True
    assert failure.formal_p3_acceptance_established is False
    assert failure.unchanged_replay_authorized is False


def test_exact_plain_backend_marker_is_accepted(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))

    evidence = runtime.backend_marker_evidence_from_texts(
        "",
        "Using AttentionBackendEnum.TRITON_ATTN backend.\n",
    )

    assert evidence is not None
    assert evidence["stream"] == "stderr"
    assert evidence["line_number"] == 1
    assert evidence["line_local_match"] is True
    assert len(str(evidence["normalized_line_sha256"])) == 64


def test_info_prefixed_backend_marker_is_accepted(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))

    evidence = runtime.backend_marker_evidence_from_texts(
        "",
        ("INFO 08-03 18:33:10 selector.py:77 Using AttentionBackendEnum.TRITON_ATTN backend.\n"),
    )

    assert evidence is not None
    assert evidence["stream"] == "stderr"


def test_cli_argument_echo_is_rejected(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))

    evidence = runtime.backend_marker_evidence_from_texts(
        (
            "python -m vllm.entrypoints.openai.api_server "
            "--attention-backend TRITON_ATTN "
            "Using AttentionBackendEnum.TRITON_ATTN backend.\n"
        ),
        "",
    )

    assert evidence is None


def test_source_literal_marker_is_rejected(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))

    evidence = runtime.backend_marker_evidence_from_texts(
        ('EXPECTED_BACKEND_LOG_MARKER = "Using AttentionBackendEnum.TRITON_ATTN backend."\n'),
        "",
    )

    assert evidence is None


def test_wrong_backend_marker_is_rejected(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))

    evidence = runtime.backend_marker_evidence_from_texts(
        "",
        "INFO Using AttentionBackendEnum.FLASH_ATTN backend.\n",
    )

    assert evidence is None


def test_marker_split_across_streams_is_rejected(tmp_path: Path) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))

    evidence = runtime.backend_marker_evidence_from_texts(
        "Using AttentionBackendEnum.",
        "TRITON_ATTN backend.",
    )

    assert evidence is None


def test_multiple_authoritative_marker_lines_are_rejected(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    marker = "Using AttentionBackendEnum.TRITON_ATTN backend.\n"

    with pytest.raises(RuntimeError, match="ambiguous"):
        runtime.backend_marker_evidence_from_texts(marker, marker)


def test_capture_finalize_joins_thread_and_seals_snapshot(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    capture = runtime.BoundedCapture(tmp_path / "capture.log")
    capture.start(io.BytesIO(b"captured-evidence"))

    capture.finalize()
    snapshot = capture.snapshot()

    assert snapshot["capture_finalized"] is True
    assert snapshot["capture_thread_alive"] is False
    assert snapshot["observed_bytes"] == len(b"captured-evidence")
    assert capture.text() == "captured-evidence"


def test_failure_diagnostics_follow_terminal_teardown(
    tmp_path: Path,
) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")
    main_source = source[source.index("def main() -> int:") :]

    stop_index = main_source.index('stop_and_report("TERMINAL_FINALIZATION")')
    diagnostics_index = main_source.index("failure_diagnostics()")
    failure_write_index = main_source.index(
        'write_json(OUTPUT_ROOT / "failure_report_v4.json", failure)'
    )

    assert stop_index < diagnostics_index < failure_write_index


def test_runtime_script_hash_is_bound_into_notebook(
    tmp_path: Path,
) -> None:
    generated = subject.build_generated(_fixture_repo(tmp_path))
    payload = json.loads(generated.notebook_bytes)
    code = "".join(
        line for cell in payload["cells"] if cell["cell_type"] == "code" for line in cell["source"]
    )

    assert generated.runtime_script_sha256 in code
    assert "runtime script identity mismatch" in code
    assert "EXECUTED_RUNTIME_SCRIPT_SHA256" in code
    assert generated.record.notebook.runtime_script_sha256 == (generated.runtime_script_sha256)
    assert generated.record.notebook.wrapper_code_sha256 == (generated.wrapper_code_sha256)


def test_runtime_source_identity_report_is_mandatory(
    tmp_path: Path,
) -> None:
    review = subject.build_generated(_fixture_repo(tmp_path)).review

    assert review.output_contract[0] == ("runtime_source_identity_report_v4.json")
    assert "worker_teardown_report_v4.json" in review.output_contract
    assert "ag-cu129-p3-p6-runtime-evidence-v4.zip" in (review.output_contract)


def test_worker_identity_fields_are_explicit(tmp_path: Path) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    for token in (
        '"worker_instance_id"',
        '"generation"',
        '"pid"',
        '"parent_pid"',
        '"process_start_ticks"',
        '"started_at"',
        '"gpu_identity"',
        '"uuid"',
        '"pci_bus_id"',
    ):
        assert token in source


def test_teardown_contract_fields_are_explicit(tmp_path: Path) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    for token in (
        '"process_tree_absent_after"',
        '"gpu_processes_absent_after"',
        '"port_closed_after"',
        '"capture_threads_finalized"',
        '"memory_returned_within_tolerance"',
        "GPU_MEMORY_RETURN_TOLERANCE_MIB",
    ):
        assert token in source


def test_evidence_contract_rejects_combined_substring_matching(
    tmp_path: Path,
) -> None:
    contract = subject.build_generated(_fixture_repo(tmp_path)).request.evidence_contract

    assert contract.exact_line_local_backend_marker_required is True
    assert contract.combined_stream_substring_matching_permitted is False
    assert contract.cli_echo_as_backend_evidence_permitted is False
    assert contract.capture_threads_finalized_before_failure_serialization is True
    assert contract.executed_runtime_script_hash_required is True


def test_no_runtime_authority_is_issued(tmp_path: Path) -> None:
    generated = subject.build_generated(_fixture_repo(tmp_path))

    assert generated.request.runtime_execution_authorized is False
    assert generated.request.authorization_issuer_included is False
    assert generated.record.safety.kaggle_execution_performed is False
    assert generated.record.safety.gpu_execution_performed is False


def test_accepted_authority_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.FAILURE_ACCEPTANCE_RECORD_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6V4ImplementationError,
        match="identity drifted",
    ):
        subject.build_generated(repo_root)


def test_v3_template_authority_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.V3_TEMPLATE_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6V4ImplementationError,
        match="authority drifted",
    ):
        subject.build_generated(repo_root)


def test_generated_artifact_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    path = repo_root / subject.NOTEBOOK_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6V4ImplementationError,
        match="differs from fresh rebuild",
    ):
        subject.validate(repo_root)


def test_template_and_wrapper_compile_with_bounded_lines(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    generated = subject.build_generated(repo_root)
    runtime = subject._template_bytes(repo_root).decode("utf-8")
    payload = json.loads(generated.notebook_bytes)
    wrapper = "".join(
        line for cell in payload["cells"] if cell["cell_type"] == "code" for line in cell["source"]
    )

    compile(runtime, subject.TEMPLATE_PATH.as_posix(), "exec")
    compile(wrapper, subject.NOTEBOOK_PATH.as_posix(), "exec")
    assert max(len(line) for line in runtime.splitlines()) <= 100
    assert max(len(line) for line in wrapper.splitlines()) <= 100


def test_names_fit_kaggle_limit() -> None:
    assert len(subject.NOTEBOOK_NAME) <= 50
    assert len(subject.FAILED_NOTEBOOK_NAME) <= 50


def test_candidate_boundary_is_exact() -> None:
    assert len(subject.CANDIDATE_PATHS) == 10
    assert len(set(subject.CANDIDATE_PATHS)) == 10
