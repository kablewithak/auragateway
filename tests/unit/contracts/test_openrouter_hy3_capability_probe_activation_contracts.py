from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.openrouter_hy3_capability_probe_activation import (
    OpenRouterProbeActivationAuthorization,
    OpenRouterProbeActivationManifest,
    OpenRouterProbeActivationReport,
    OpenRouterProbeActivationRuntimePolicy,
    OpenRouterProbeProtectedPromptBundle,
)

_ROOT = Path("data/evals/benchmark/openrouter-hy3-capability-probe-v1")


def _json_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_committed_activation_assets_validate() -> None:
    authorization = OpenRouterProbeActivationAuthorization.model_validate(
        _json_object(_ROOT / "authorization.json")
    )
    policy = OpenRouterProbeActivationRuntimePolicy.model_validate(
        _json_object(_ROOT / "runtime_policy.json")
    )
    report = OpenRouterProbeActivationReport.model_validate(
        _json_object(_ROOT / "activation_report.json")
    )
    manifest = OpenRouterProbeActivationManifest.model_validate(
        _json_object(_ROOT / "activation_manifest.json")
    )
    assert authorization.status.value == "active"
    assert authorization.capability_probe_execution_authorized is True
    assert authorization.authorization_consumed is False
    assert policy.maximum_total_inference_attempts == 4
    assert report.provider_call_performed is False
    assert manifest.active_authorization_created is True


def test_authorization_rejects_duplicate_bindings() -> None:
    payload = _json_object(_ROOT / "authorization.json")
    bindings = payload["bindings"]
    assert isinstance(bindings, list)
    bindings[-1] = bindings[0]
    with pytest.raises(ValidationError, match="unique"):
        OpenRouterProbeActivationAuthorization.model_validate(payload)


def test_runtime_policy_rejects_changed_transient_statuses() -> None:
    payload = _json_object(_ROOT / "runtime_policy.json")
    payload["transient_http_statuses"] = [429, 500, 524, 529]
    with pytest.raises(ValidationError, match="transient"):
        OpenRouterProbeActivationRuntimePolicy.model_validate(payload)


def test_protected_bundle_rejects_reordered_calls() -> None:
    payload = {
        "bundle_id": "openrouter-hy3-capability-probe-prompt-bundle-v1",
        "authorization_id": "openrouter-hy3-capability-probe-auth-v1",
        "recipe_id": "openrouter-hy3-capability-probe-prompt-v1",
        "session_id": "stable-session",
        "stable_prefix": "x" * 1000,
        "stable_prefix_sha256": "0" * 64,
        "stable_prefix_bytes": 1000,
        "calls": [
            {
                "logical_call_index": 1,
                "request_role": "warm_probe",
                "request_id": "warm-request",
                "fixture_id": "warm-fixture",
                "user_suffix": "Return exactly warm",
                "expected_output": "WARM",
            },
            {
                "logical_call_index": 0,
                "request_role": "cold_probe",
                "request_id": "cold-request",
                "fixture_id": "cold-fixture",
                "user_suffix": "Return exactly cold",
                "expected_output": "COLD",
            },
        ],
    }
    with pytest.raises(ValidationError, match="indexes"):
        OpenRouterProbeProtectedPromptBundle.model_validate(payload)
