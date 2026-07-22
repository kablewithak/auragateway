"""Tests for the bounded worker-startup observability implementation boundary."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_worker_startup_observability_implementation,
)

implementation = (
    full_abc_local_environment_qualification_cu129_worker_startup_observability_implementation
)

ROOT = Path(__file__).resolve().parents[3]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError("fixture root must be one JSON object")
    return cast(dict[str, Any], payload)


def test_repository_package_requires_rematerialization() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("full Git checkout is required for historical authority validation")
    result = implementation.validate_repository_package(ROOT)

    assert result["status"] == (
        "WORKER_STARTUP_OBSERVABILITY_IMPLEMENTED_REMATERIALIZATION_REQUIRED"
    )
    assert result["historical_active_harness_source_commit"] == (
        "426f57dd11dddc2fb8e5a703721c2189abc7a0ff"
    )
    assert result["maximum_stream_capture_bytes"] == 32 * 1024
    assert result["maximum_diagnostic_bytes"] == 256 * 1024
    assert result["maximum_readiness_polls"] == 90
    assert result["historical_issuer_usable"] is False
    assert result["active_manifest_promoted"] is False
    assert result["authorization_issued"] is False
    assert result["kaggle_execution_performed"] is False
    assert result["model_requests_performed"] == 0
    assert result["next_gate"] == (
        "merge_then_build_post_merge_worker_observability_harness_source_package"
    )


def test_record_rejects_manifest_promotion() -> None:
    payload = _load_json(ROOT / implementation.IMPLEMENTATION_PATH)
    transition = cast(dict[str, Any], payload["authority_transition"])
    transition["active_manifest_promoted"] = True

    with pytest.raises(ValidationError):
        implementation.WorkerStartupObservabilityImplementation.model_validate(payload)


def test_record_rejects_hidden_retry() -> None:
    payload = _load_json(ROOT / implementation.IMPLEMENTATION_PATH)
    controls = cast(dict[str, Any], payload["diagnostic_controls"])
    controls["hidden_retries_performed"] = 1

    with pytest.raises(ValidationError):
        implementation.WorkerStartupObservabilityImplementation.model_validate(payload)


def test_record_requires_exact_artifact_order() -> None:
    payload = _load_json(ROOT / implementation.IMPLEMENTATION_PATH)
    artifacts = cast(list[dict[str, Any]], copy.deepcopy(payload["implemented_artifacts"]))
    artifacts.reverse()
    payload["implemented_artifacts"] = artifacts

    with pytest.raises(ValidationError, match="artifact order"):
        implementation.WorkerStartupObservabilityImplementation.model_validate(payload)


def test_source_control_guard_rejects_missing_diagnostic_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = (
        implementation.DIAGNOSTICS_PATH,
        implementation.RUNTIME_ADAPTER_PATH,
        implementation.LAUNCHER_SOURCE_PATH,
        implementation.HARNESS_TOOLCHAIN_PATH,
    )
    for relative in paths:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("placeholder\n", encoding="utf-8")

    monkeypatch.setattr(implementation, "DIAGNOSTICS_PATH", paths[0])

    with pytest.raises(implementation.ImplementationError, match="controls drifted"):
        implementation._require_source_controls(tmp_path)
