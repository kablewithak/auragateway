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
from auragateway.local_abc.cu129_worker_observability_harness_integration import (
    CURRENT_MODEL_SNAPSHOT_SHA256,
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


def test_repository_package_recognizes_integrated_worker_observability_harness() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("full Git checkout is required for historical authority validation")
    result = implementation.validate_repository_package(ROOT)

    assert result["status"] == (
        "WORKER_STARTUP_OBSERVABILITY_HARDENED_HARNESS_INTEGRATED_AUTHORIZATION_REBOUND"
    )
    assert result["historical_harness_source_commit"] == (
        "426f57dd11dddc2fb8e5a703721c2189abc7a0ff"
    )
    assert result["current_harness_source_commit"] == ("4f3302df871d47fec81e25e9af9609c0e2c7812d")
    assert result["maximum_stream_capture_bytes"] == 32 * 1024
    assert result["maximum_diagnostic_bytes"] == 256 * 1024
    assert result["maximum_readiness_polls"] == 90
    assert result["fresh_issuer_implemented"] is True
    assert result["fresh_issuer_usable"] is True
    assert result["post_integration_rebind_complete"] is True
    assert result["active_harness_reusable_for_retry"] is True
    assert result["fresh_authorization_base_commit"] == ("0805b6f08028709a347ce9e420b3415c3a84ba05")
    assert result["superseded_authorization_base_commit"] == (
        "fba5d25ec831f0ec28a1bcd3d63e9c6d8c4b985b"
    )
    assert result["historical_issuer_usable"] is False
    assert result["active_manifest_promoted"] is True
    assert result["active_model_snapshot_sha256"] == (CURRENT_MODEL_SNAPSHOT_SHA256)
    assert result["operational_input_closure"] == "PASSED"
    assert result["authorization_issued"] is False
    assert result["kaggle_execution_performed"] is False
    assert result["model_requests_performed"] == 0
    assert result["next_gate"] == ("explicit_operator_confirmation_then_issue_fresh_authorization")


def test_historical_toolchain_source_controls_do_not_require_current_hardening_markers(
    tmp_path: Path,
) -> None:
    sources = {
        implementation.DIAGNOSTICS_PATH: "\n".join(
            (
                "MAXIMUM_STREAM_CAPTURE_BYTES: Final = 32 * 1024",
                "MAXIMUM_DIAGNOSTIC_BYTES: Final = 256 * 1024",
                "hidden_retries_performed: Literal[0]",
                "write_diagnostic_atomic",
                "raw_environment_included: Literal[False]",
            )
        ),
        implementation.RUNTIME_ADAPTER_PATH: "\n".join(
            (
                "spawn_captured",
                "_CapturedWorkerProcess",
                "readiness_history",
                "failed bounded readiness polling",
                "write_diagnostic_atomic",
            )
        ),
        implementation.LAUNCHER_SOURCE_PATH: "\n".join(
            (
                "worker_startup_diagnostic.json",
                "worker_startup_diagnostic_included",
                "load_worker_startup_diagnostic",
                "MAXIMUM_DIAGNOSTIC_BYTES",
            )
        ),
        implementation.HARNESS_TOOLCHAIN_PATH: "\n".join(
            (
                "REVIEW_MERGE_COMMIT",
                "_require_clean_synchronized_main",
                'accelerator": "none',
                "active_manifest_promoted",
                "FINAL_AUTHORIZATION_PATH",
            )
        ),
    }

    for relative_path, source in sources.items():
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source, encoding="utf-8")

    historical_toolchain_source = sources[implementation.HARNESS_TOOLCHAIN_PATH]
    assert "VLLM_CLI_HARDENING_RECORD_PATH" not in historical_toolchain_source
    assert "PREDECESSOR_HARNESS_RETAINED_NOT_RETRY_USABLE" not in (historical_toolchain_source)

    implementation._require_source_controls(tmp_path)


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
