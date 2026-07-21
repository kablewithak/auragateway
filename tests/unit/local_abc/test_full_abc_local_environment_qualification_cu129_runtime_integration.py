"""Regression tests for atomic CUDA 12.9 qualification runtime integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_runtime_integration as integration,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError("fixture root must be one JSON object")
    return cast(dict[str, Any], payload)


def test_repository_package_is_integrated_and_authorization_blocked() -> None:
    result = integration.validate_repository_package(Path.cwd())

    assert result["integration_status"] == ("INTEGRATED_REPOSITORY_ONLY_AUTHORIZATION_BLOCKED")
    assert result["runtime_output_directory"] == ("auragateway_vllm_cu129_wheelhouse_v1")
    assert result["runtime_package_count"] == 176
    assert result["authorization_issued"] is False
    assert result["runtime_execution_performed"] is False
    assert result["model_requests_performed"] == 0


def test_integration_decision_rejects_authorization_claim() -> None:
    payload = _load_json(Path.cwd() / integration.INTEGRATION_PATH)
    safety = cast(dict[str, Any], payload["safety"])
    safety["authorization_issued"] = True

    with pytest.raises(ValidationError, match="safety boundary drifted"):
        integration.RuntimeIntegrationDecision.model_validate(payload)


def test_integration_decision_rejects_runtime_identity_drift() -> None:
    payload = _load_json(Path.cwd() / integration.INTEGRATION_PATH)
    runtime = cast(dict[str, Any], payload["runtime_authority"])
    runtime["package_count"] = 175

    with pytest.raises(ValidationError, match="runtime authority drifted"):
        integration.RuntimeIntegrationDecision.model_validate(payload)


def test_integration_decision_rejects_model_requests() -> None:
    payload = _load_json(Path.cwd() / integration.INTEGRATION_PATH)
    safety = cast(dict[str, Any], payload["safety"])
    safety["model_requests_performed"] = 1

    with pytest.raises(ValidationError, match="performed model requests"):
        integration.RuntimeIntegrationDecision.model_validate(payload)
