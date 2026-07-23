"""Regression tests for the CUDA 12.9 qualification authority graph."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_authority_graph as graph,
)

ROOT = Path(__file__).resolve().parents[3]


def test_repository_authority_graph_integrates_worker_observability_harness() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("full Git checkout is required for historical authority validation")
    summary = graph.validate_repository_authority_graph(ROOT)

    assert summary["status"] == "CURRENT_CU129_FRESH_AUTHORIZATION_ISSUER_IMPLEMENTED"
    assert summary["current_runtime_role"] == "vllm_runtime"
    assert summary["current_runtime_format"] == "python_wheelhouse_directory"
    assert summary["runtime_package_count"] == 176
    assert summary["canonical_json_authorities_verified"] == 11
    assert summary["current_harness_evidence_integrated"] is True
    assert summary["operational_input_closure"] == "PASSED"
    assert summary["authorization_source_binding_policy"] == (
        "CONTROL_PACKAGE_AUTHORIZATION_PARITY"
    )
    assert summary["worker_observability_review_base_commit"] == (
        "997efb4aacf998567a3d92e7202a0054bf473ca4"
    )
    assert summary["fresh_authorization_base_commit_status"] == ("POST_INTEGRATION_MERGE_BOUND")
    assert summary["fresh_authorization_base_commit"] == (
        "fba5d25ec831f0ec28a1bcd3d63e9c6d8c4b985b"
    )
    assert summary["current_harness_source_commit"] == ("dceda98989386de7a4d57616f9f8a8023f866f10")
    assert summary["historical_preintegration_review_revision_bound"] is True
    assert summary["historical_pr109_issuance_review_revision_bound"] is True
    assert summary["historical_rematerialization_revision_bound"] is True
    assert summary["fresh_cu129_authorization_readiness_review_complete"] is True
    assert summary["fresh_cu129_authorization_issuer_implemented"] is True
    assert summary["worker_startup_observability_implemented"] is True
    assert summary["historical_issuer_usable"] is False
    assert summary["active_manifest_promoted"] is True
    assert summary["authorization_issued"] is False
    assert summary["runtime_execution_performed"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["next_gate"] == ("explicit_operator_confirmation_then_issue_fresh_authorization")


def test_canonical_json_guard_rejects_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text('{"value":1}\n', encoding="utf-8")

    with pytest.raises(graph.AuthorityGraphError, match="canonical single-line"):
        graph._require_canonical_json(path)


def test_retired_runtime_marker_guard_rejects_live_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = Path("runtime.json")
    (tmp_path / relative).write_text(
        json.dumps({"role": "vllm_wheel"}, separators=(",", ":")),
        encoding="utf-8",
    )
    monkeypatch.setattr(graph, "LIVE_RUNTIME_PATHS", (relative,))

    with pytest.raises(graph.AuthorityGraphError, match="retired single-wheel"):
        graph._require_live_runtime_has_no_retired_markers(tmp_path)


def test_source_marker_guard_rejects_missing_current_issuer_binding(
    tmp_path: Path,
) -> None:
    path = tmp_path / "issuer.py"
    path.write_text("CURRENT = True\n", encoding="utf-8")

    with pytest.raises(graph.AuthorityGraphError, match="missing required controls"):
        graph._require_source_markers(path, ("CURRENT_AUTHORIZATION_BASE_COMMIT",))
