"""Tests for P3-P6 runtime diagnostic V1 implementation assets."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v1 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    for relative in (
        subject.OPTION_C_PATH,
        subject.Q6_ACCEPTANCE_PATH,
        subject.TEMPLATE_PATH,
    ):
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def test_generate_validate_round_trip(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.record.status == "IMPLEMENTED_NOT_EXECUTED"


def test_probe_sequence_and_cumulative_budgets_are_exact(
    tmp_path: Path,
) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request

    assert tuple(item.probe_id for item in request.probes) == (
        "P3",
        "P4",
        "P5",
        "P6",
    )
    assert tuple(item.maximum_model_requests for item in request.probes) == (
        0,
        1,
        3,
        5,
    )
    assert tuple(item.maximum_worker_starts for item in request.probes) == (
        1,
        1,
        2,
        3,
    )
    assert request.execution_budget.maximum_model_requests == 5
    assert request.execution_budget.maximum_worker_starts == 3
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")
    assert "ACTION_BUDGET_LIMITS" in source
    assert 'consume_actions(counters, "model_requests")' in source
    assert 'consume_actions(counters, "worker_starts", "model_loads")' in source


def test_review_rejects_legacy_monolithic_capture_flow(
    tmp_path: Path,
) -> None:
    review = subject.build_generated(_fixture_repo(tmp_path)).review

    assert review.first_divergence_from_legacy_adapter == (
        "LEGACY_ADAPTER_STARTS_TWO_WORKERS_BEFORE_P3"
    )
    assert review.legacy_adapter_reuse_decision == (
        "REUSE_HELPERS_AND_CONTRACTS_NOT_MONOLITHIC_CAPTURE_FLOW"
    )


def test_notebook_is_deterministic_clean_and_single_code_cell(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)

    first = subject.build_generated(repo_root)
    second = subject.build_generated(repo_root)
    payload = json.loads(first.notebook_bytes.decode("utf-8"))

    assert first.notebook_bytes == second.notebook_bytes
    assert first.record.notebook.sha256 == second.record.notebook.sha256
    code_cells = [item for item in payload["cells"] if item["cell_type"] == "code"]
    assert len(code_cells) == 1
    assert code_cells[0]["execution_count"] is None
    assert code_cells[0]["outputs"] == []


def test_template_uses_explicit_triton_cli_selection(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    source = (repo_root / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert '"--attention-backend",' in source
    assert "EXPECTED_BACKEND," in source
    assert 'EXPECTED_BACKEND = "TRITON_ATTN"' in source
    assert "automatic backend" not in source.lower()
    assert "wait_backend_marker" in source


def test_p3_is_one_worker_before_p6_starts_worker_two(
    tmp_path: Path,
) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    p3_write = source.index("p3_worker_startup_report_v1.json")
    worker_2_start = source.index("worker_2.start(counters)")

    assert p3_write < worker_2_start


def test_p4_requires_exact_structured_json_without_raw_payload_logging(
    tmp_path: Path,
) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert "validate_structured_response" in source
    assert '"structured_output_valid": True' in source
    assert "observed != expected" in source
    assert "raw_prompt_logged" in source
    assert "raw_output_logged" in source


def test_p5_uses_token_level_cache_metric_and_full_restart(
    tmp_path: Path,
) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert "vllm:prompt_tokens_cached_total" in source
    assert "vllm:prefix_cache_hits_total" not in source
    assert "old_pid == new_pid" in source
    assert "namespace_only_reset_used" in source
    assert "worker_1.stop()" in source
    assert source.count("worker_1.wait_backend_marker()") >= 2


def test_p6_requires_process_gpu_port_route_and_metric_isolation(
    tmp_path: Path,
) -> None:
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    required = (
        "validate_gpu_process_isolation",
        "worker_process_trees_disjoint",
        "worker_1_bound_to_gpu_0",
        "worker_2_bound_to_gpu_1",
        "worker_1_route_isolated",
        "worker_2_route_isolated",
        "ports_distinct",
    )
    assert all(marker in source for marker in required)


def test_partial_evidence_and_stop_on_first_failure_are_required(
    tmp_path: Path,
) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert request.stop_on_first_failure is True
    assert request.partial_evidence_required is True
    assert "failure_report_v1.json" in source
    assert "completed_probes" in source
    assert '"status": "NOT_APPLICABLE"' in source
    assert '"error_code": error_code' in source


def test_runtime_failure_taxonomy_is_machine_readable(
    tmp_path: Path,
) -> None:
    generated = subject.build_generated(_fixture_repo(tmp_path))
    source = (_fixture_repo(tmp_path) / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    for code in generated.review.required_failure_codes:
        assert code in source
    assert '"error_code": error_code' in source
    assert '"failure_code": None if failure is None' in source


def test_no_runtime_authority_is_issued(tmp_path: Path) -> None:
    generated = subject.build_generated(_fixture_repo(tmp_path))

    assert generated.request.runtime_execution_authorized is False
    assert generated.request.authorization_issuer_included is False
    assert generated.record.safety.kaggle_execution_performed is False
    assert generated.record.safety.gpu_execution_performed is False
    assert generated.record.safety.worker_started is False


def test_input_boundary_is_model_and_wheelhouse_only(
    tmp_path: Path,
) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request

    assert tuple(item.role for item in request.inputs) == (
        "model_snapshot",
        "vllm_runtime",
    )
    assert all(item.network_fallback_permitted is False for item in request.inputs)


def test_q6_authority_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.Q6_ACCEPTANCE_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6ImplementationError,
        match="identity drifted",
    ):
        subject.build_generated(repo_root)


def test_generated_artifact_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    path = repo_root / subject.NOTEBOOK_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.P3P6ImplementationError,
        match="differs from fresh rebuild",
    ):
        subject.validate(repo_root)


def test_template_compiles_and_python_lines_are_bounded(
    tmp_path: Path,
) -> None:
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
