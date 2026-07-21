"""Regression tests for the historical CUDA 12.9 runtime-integration review."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_runtime_integration_review as review,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError("fixture root must be one JSON object")
    return cast(dict[str, Any], payload)


def test_repository_review_preserves_history_and_binds_current_supersession() -> None:
    root = Path.cwd()
    if not (root / ".git").exists():
        pytest.skip("full Git checkout is required for historical authority validation")
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
        pytest.skip("runtime integration review base commit is unavailable")

    result = review.validate_repository_package(root)

    assert result["review_decision"] == (
        "APPROVED_FOR_BOUNDED_CU129_QUALIFICATION_RUNTIME_INTEGRATION"
    )
    assert result["review_disposition"] == "HISTORICAL_PREINTEGRATION_AUTHORITY"
    assert result["historical_runtime_input"] == "single_vllm_0_25_1_cu129_wheel"
    assert result["current_runtime_input"] == "exact_176_package_cu129_wheelhouse"
    assert result["current_integration_status"] == (
        "INTEGRATED_REPOSITORY_ONLY_AUTHORIZATION_BLOCKED"
    )
    assert result["authorization_issued"] is False
    assert result["runtime_execution_performed"] is False
    assert result["model_requests_performed"] == 0


def test_review_rejects_runtime_execution_claim() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    safety = cast(dict[str, Any], payload["safety"])
    safety["kaggle_execution_performed"] = True

    with pytest.raises(ValidationError, match="safety boundary drifted"):
        review.RuntimeIntegrationReview.model_validate(payload)


def test_review_rejects_model_request_claim() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    safety = cast(dict[str, Any], payload["safety"])
    safety["model_requests_performed"] = 1

    with pytest.raises(ValidationError, match="performed model requests"):
        review.RuntimeIntegrationReview.model_validate(payload)


def test_review_requires_atomic_cross_boundary_change_set() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    payload["required_atomic_change_set"] = ["adapter only"]

    with pytest.raises(ValidationError):
        review.RuntimeIntegrationReview.model_validate(payload)


def test_review_requires_negative_regressions() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    payload["regression_requirements"] = ["happy path"]

    with pytest.raises(ValidationError):
        review.RuntimeIntegrationReview.model_validate(payload)
