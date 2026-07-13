from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.diagnostic_execution import (
    DiagnosticExecutionAuthorization,
    DiagnosticExecutionRuntimePolicy,
)

_ASSET_ROOT = Path("data/evals/benchmark/diagnostic-execution-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_active_authorization_exposes_one_time_execution_only() -> None:
    authorization = DiagnosticExecutionAuthorization.model_validate(
        _json_object(_ASSET_ROOT / "authorization.json")
    )

    assert authorization.status.value == "active"
    assert authorization.maximum_provider_calls == 24
    assert authorization.provider_calls_permitted is True
    assert authorization.execution_command_available is True
    assert authorization.one_time_execution is True
    assert authorization.retry_permitted is False
    assert authorization.resume_permitted is False
    assert authorization.execution_completed is False


def test_runtime_policy_binds_reviewed_schedule_and_budget() -> None:
    policy = DiagnosticExecutionRuntimePolicy.model_validate(
        _json_object(_ASSET_ROOT / "runtime_policy.json")
    )

    assert len(policy.schedule_offsets_seconds) == 24
    assert policy.schedule_offsets_seconds[-1] == 2220
    assert policy.planned_maximum_cost_microusd == 4992
    assert policy.authorization_cost_ceiling_microusd == 5000
    assert policy.request_rejection_action.value == "stop_sequence"
    assert policy.other_provider_error_action.value == "stop_experiment"


def test_authorization_rejects_retry_enablement() -> None:
    payload = _json_object(_ASSET_ROOT / "authorization.json")
    payload["retry_permitted"] = True

    with pytest.raises(ValidationError):
        DiagnosticExecutionAuthorization.model_validate(payload)


def test_authorization_rejects_resume_enablement() -> None:
    payload = _json_object(_ASSET_ROOT / "authorization.json")
    payload["resume_permitted"] = True

    with pytest.raises(ValidationError):
        DiagnosticExecutionAuthorization.model_validate(payload)


def test_authorization_requires_exact_binding_set() -> None:
    payload = _json_object(_ASSET_ROOT / "authorization.json")
    bindings = deepcopy(payload["bindings"])
    assert isinstance(bindings, list)
    bindings.pop()
    payload["bindings"] = bindings

    with pytest.raises(ValidationError):
        DiagnosticExecutionAuthorization.model_validate(payload)


def test_authorization_requires_exact_confirmation_phrase() -> None:
    payload = _json_object(_ASSET_ROOT / "authorization.json")
    payload["confirmation_phrase"] = "execute"

    with pytest.raises(ValidationError):
        DiagnosticExecutionAuthorization.model_validate(payload)


def test_runtime_policy_rejects_schedule_drift() -> None:
    payload = _json_object(_ASSET_ROOT / "runtime_policy.json")
    offsets = deepcopy(payload["schedule_offsets_seconds"])
    assert isinstance(offsets, list)
    offsets[-1] = 2219
    payload["schedule_offsets_seconds"] = offsets

    with pytest.raises(ValidationError):
        DiagnosticExecutionRuntimePolicy.model_validate(payload)


def test_runtime_policy_rejects_cost_ceiling_breach() -> None:
    payload = _json_object(_ASSET_ROOT / "runtime_policy.json")
    payload["planned_cost_microusd_per_provider_call"] = 209
    payload["planned_maximum_cost_microusd"] = 5016

    with pytest.raises(ValidationError):
        DiagnosticExecutionRuntimePolicy.model_validate(payload)


def test_public_activation_assets_contain_no_raw_prompt_or_secret_fields() -> None:
    text = "\n".join(
        (
            (_ASSET_ROOT / "authorization.json").read_text(encoding="utf-8"),
            (_ASSET_ROOT / "runtime_policy.json").read_text(encoding="utf-8"),
        )
    )

    for forbidden in (
        '"system_prompt":',
        '"user_prompts_by_turn":',
        '"messages":',
        '"raw_output":',
        '"provider_error_message":',
        '"api_key":',
    ):
        assert forbidden not in text
