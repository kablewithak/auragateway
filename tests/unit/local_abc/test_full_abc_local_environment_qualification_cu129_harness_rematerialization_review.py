"""Regression tests for the current CUDA 12.9 harness-rematerialization review."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_harness_rematerialization_review as review,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError("fixture root must be one JSON object")
    return cast(dict[str, Any], payload)


def _widen_string(value: str) -> str:
    """Erase Literal precision for intentional cross-version identity comparisons."""

    return value


def test_repository_review_proves_current_harness_rematerialization_required() -> None:
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
        pytest.skip("review base commit is unavailable")

    result = review.validate_repository_package(root)

    assert result["decision"] == (
        "APPROVED_FOR_CURRENT_CU129_HARNESS_REMATERIALIZATION_IMPLEMENTATION"
    )
    assert result["failure_class"] == ("FROZEN_HARNESS_CANNOT_REALIZE_CURRENT_CU129_RUNTIME")
    assert result["historical_harness_source_commit"] == (
        "be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"
    )
    assert result["current_runtime_role"] == "vllm_runtime"
    assert result["current_runtime_package_count"] == 176
    assert result["current_harness_rematerialization_required"] is True
    assert result["authorization_issued"] is False
    assert result["kaggle_execution_performed"] is False
    assert result["model_requests_performed"] == 0
    assert result["next_gate"] == "implement_current_cu129_harness_rematerializer"


def test_manifest_role_lookup_is_order_independent() -> None:
    payload = _load_json(Path.cwd() / review.MANIFEST_PATH)
    entries = payload["entries"]
    assert isinstance(entries, list)

    by_role = review._manifest_entries_by_role(list(reversed(entries)))

    assert set(by_role) == {"harness_source", "model_artifacts", "vllm_runtime"}
    assert by_role["harness_source"]["mounted_path"] == (review.HISTORICAL_HARNESS_MOUNTED_PATH)
    assert by_role["vllm_runtime"]["package_count"] == 176


def test_historical_harness_mount_uses_exact_materializer_output_name() -> None:
    assert review.HISTORICAL_HARNESS_OUTPUT_DIRECTORY == (
        "auragateway_qualification_harness_be1bfad_v1"
    )
    assert review.HISTORICAL_HARNESS_MOUNTED_PATH.endswith(
        "/auragateway_qualification_harness_be1bfad_v1"
    )
    assert review.HISTORICAL_HARNESS_SOURCE_COMMIT.startswith("be1bfadd")


def test_review_rejects_decision_drift() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    payload["decision"] = "AUTHORIZED"

    with pytest.raises(ValidationError):
        review.CurrentHarnessRematerializationReview.model_validate(payload)


def test_review_requires_complete_implementation_scope() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    payload["required_implementation"] = ["build a notebook"] * 10

    with pytest.raises(
        ValidationError,
        match="required rematerialization implementation scope drifted",
    ):
        review.CurrentHarnessRematerializationReview.model_validate(payload)


def test_review_requires_negative_regressions() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    payload["required_negative_regressions"] = ["happy path"] * 10

    with pytest.raises(
        ValidationError,
        match="required rematerialization regressions drifted",
    ):
        review.CurrentHarnessRematerializationReview.model_validate(payload)


def test_review_rejects_model_request_activity() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    safety = cast(dict[str, Any], payload["safety"])
    safety["model_requests_performed"] = 1

    with pytest.raises(ValidationError):
        review.CurrentHarnessRematerializationReview.model_validate(payload)


def test_historical_materializer_identity_is_exact() -> None:
    payload = _load_json(Path.cwd() / review.HISTORICAL_IDENTITY_PATH)
    identity = review.HistoricalMaterializerIdentity.model_validate(payload)

    assert identity.notebook_raw_sha256 == review.HISTORICAL_NOTEBOOK_SHA256
    assert identity.source_commit == review.HISTORICAL_HARNESS_SOURCE_COMMIT
    assert identity.directory_sha256 == review.HISTORICAL_DIRECTORY_SHA256
    assert identity.file_count == 953
    assert identity.total_bytes == 8_879_194
    assert identity.model_requests_performed == 0


def test_current_and_historical_runtime_boundaries_are_not_equal() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    parsed = review.CurrentHarnessRematerializationReview.model_validate(payload)
    boundary = parsed.observed_current_boundary

    assert _widen_string(boundary.current_runtime_adapter_sha256) != _widen_string(
        boundary.historical_runtime_adapter_sha256
    )
    assert _widen_string(boundary.current_execution_contracts_sha256) != _widen_string(
        boundary.historical_execution_contracts_sha256
    )
    assert _widen_string(boundary.current_execution_request_sha256) != _widen_string(
        boundary.historical_execution_request_sha256
    )
    assert _widen_string(boundary.current_worker_plan_sha256) != _widen_string(
        boundary.historical_worker_plan_sha256
    )


def test_review_keeps_authorization_and_runtime_execution_blocked() -> None:
    payload = _load_json(Path.cwd() / review.REVIEW_PATH)
    parsed = review.CurrentHarnessRematerializationReview.model_validate(payload)

    assert parsed.safety.authorization_issued is False
    assert parsed.safety.kaggle_execution_performed is False
    assert parsed.safety.package_installation_performed is False
    assert parsed.safety.model_loaded is False
    assert parsed.safety.worker_started is False
    assert parsed.safety.model_requests_performed == 0
    assert parsed.safety.measured_execution_authorized is False
