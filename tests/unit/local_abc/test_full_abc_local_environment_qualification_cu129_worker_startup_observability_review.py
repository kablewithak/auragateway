"""Tests for the CUDA 12.9 worker-startup observability review."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_worker_startup_observability_review as review,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError("fixture root must be one JSON object")
    return cast(dict[str, Any], payload)


def test_repository_review_validates_immutable_failure_and_next_gate() -> None:
    root = Path.cwd()
    if not (root / ".git").exists():
        pytest.skip("full Git checkout is required for ancestry validation")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "merge-base",
            "--is-ancestor",
            review.BASE_COMMIT,
            "HEAD",
        ],
        check=False,
    )
    if ancestry.returncode != 0:
        pytest.skip("Attempt 5 base commit is unavailable")

    result = review.validate_repository_package(root)

    assert result["decision"] == ("APPROVED_FOR_WORKER_STARTUP_OBSERVABILITY_IMPLEMENTATION")
    assert result["reported_status"] == "FAILED"
    assert result["first_divergence"] == "worker_startup_readiness"
    assert result["root_cause_status"] == "UNRESOLVED"
    assert result["unchanged_rerun_permitted"] is False
    assert result["authorization_reuse_permitted"] is False
    assert result["model_requests_performed"] == 0


def test_review_rejects_root_cause_invention() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    assessment = cast(dict[str, Any], payload["evidence_backed_assessment"])
    assessment["root_cause_status"] = "VLLM_CRASHED"

    with pytest.raises(ValidationError):
        review.WorkerStartupObservabilityReview.model_validate(payload)


def test_review_rejects_unchanged_rerun_authorization() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    assessment = cast(dict[str, Any], payload["evidence_backed_assessment"])
    assessment["unchanged_rerun_justified"] = True

    with pytest.raises(ValidationError):
        review.WorkerStartupObservabilityReview.model_validate(payload)


def test_review_requires_complete_implementation_scope() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    payload["required_implementation"] = ["capture output"] * 12

    with pytest.raises(
        ValidationError,
        match="required observability implementation scope drifted",
    ):
        review.WorkerStartupObservabilityReview.model_validate(payload)


def test_review_requires_complete_negative_regressions() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    payload["required_negative_regressions"] = ["happy path"] * 12

    with pytest.raises(
        ValidationError,
        match="required observability regressions drifted",
    ):
        review.WorkerStartupObservabilityReview.model_validate(payload)


def test_safety_rejects_authorization_reuse() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    safety = cast(dict[str, Any], payload["safety"])
    safety["authorization_reuse_permitted"] = True

    with pytest.raises(ValidationError):
        review.WorkerStartupObservabilityReview.model_validate(payload)


def test_attempt_5_failure_record_is_preserved() -> None:
    failure = _load_json(Path.cwd() / review.EVIDENCE_DIRECTORY / "launcher_failure.json")

    assert failure["status"] == "FAILED"
    assert failure["stage"] == "reviewed_core_execution"
    assert failure["safe_message"] == "worker failed bounded readiness polling"
    assert failure["runtime_evidence_found"] == []
    assert failure["ports_open"] == []


def test_attempt_5_trace_binds_worker_readiness_divergence() -> None:
    trace = (Path.cwd() / review.EVIDENCE_DIRECTORY / "launcher_failure_trace.txt").read_text(
        encoding="utf-8"
    )

    assert "adapter.capture" in trace
    assert "self._wait_for_workers(plans)" in trace
    assert "worker failed bounded readiness polling" in trace


def test_authority_impact_requires_new_harness_lineage() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    parsed = review.WorkerStartupObservabilityReview.model_validate(copy.deepcopy(payload))

    assert parsed.authority_impact.runtime_adapter_change_required is True
    assert parsed.authority_impact.launcher_change_required is True
    assert parsed.authority_impact.new_post_merge_harness_source_required is True
    assert parsed.authority_impact.historical_attempt_5_remains_immutable is True
