"""Regression tests for the deterministic T4 attention-backend review."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_attention_backend_remediation_review as review,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_repository_review_package_validates() -> None:
    summary = review.validate_repository_package(REPO_ROOT)

    assert summary["status"] == ("T4_ATTENTION_BACKEND_REMEDIATION_REVIEW_VALID")
    assert summary["decision"] == review.DECISION
    assert summary["root_cause"] == ("FLASHINFER_JIT_CUDA_DRIVER_LINK_LIBRARY_UNAVAILABLE")
    assert summary["selected_backend"] == "TRITON_ATTN"
    assert summary["evidence_count"] == 6
    assert summary["runtime_source_changed"] is False
    assert summary["authorization_issued"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["rerun_permitted"] is False
    assert summary["next_gate"] == review.NEXT_GATE


def test_review_record_preserves_bounded_scope() -> None:
    record = review.AttentionBackendRemediationReviewRecord.model_validate_json(
        (REPO_ROOT / review.RECORD_PATH).read_text(encoding="utf-8")
    )

    assert record.failure.runtime_installation_reached is True
    assert record.failure.model_weights_loaded is True
    assert record.failure.workers_started == 2
    assert record.failure.workers_ready == 0
    assert record.failure.model_requests_performed == 0
    assert record.implementation_boundary.selected_backend == "TRITON_ATTN"
    assert record.implementation_boundary.automatic_backend_selection_permitted is False
    assert record.implementation_boundary.flashinfer_fallback_permitted is False
    assert record.implementation_boundary.runtime_wheelhouse_change_expected is False
    assert record.authority_transition.current_harness_reusable_for_retry is False
    assert record.circuit_breaker.unchanged_rerun_permitted is False
    assert record.safety.runtime_source_changed is False
    assert record.safety.authorization_issued is False
    assert record.next_gate == review.NEXT_GATE


def test_review_record_is_canonical_json() -> None:
    path = REPO_ROOT / review.RECORD_PATH
    observed = path.read_text(encoding="utf-8")
    payload = json.loads(observed)

    assert observed == json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def test_review_rejects_live_authorization(tmp_path: Path) -> None:
    authorization = (
        tmp_path / "benchmarks/local_abc/"
        "auragateway_full_abc_local_full_run_environment_qualification_"
        "execution_authorization_v1.json"
    )
    authorization.parent.mkdir(parents=True)
    authorization.write_text("{}", encoding="utf-8")

    with pytest.raises(
        review.AttentionBackendRemediationReviewError,
        match="live transient authorization",
    ):
        review._require_authorization_absent(tmp_path)


def test_worker_observations_remain_exact() -> None:
    record = review.AttentionBackendRemediationReviewRecord.model_validate_json(
        (REPO_ROOT / review.RECORD_PATH).read_text(encoding="utf-8")
    )

    assert tuple(
        (
            worker.worker_id,
            worker.gpu_index,
            worker.port,
            worker.process_returncode,
            worker.ready,
        )
        for worker in record.workers
    ) == (
        ("worker_1", 0, 8001, 1, False),
        ("worker_2", 1, 8002, 1, False),
    )
