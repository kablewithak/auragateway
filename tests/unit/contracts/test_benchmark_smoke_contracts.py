from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.contracts.benchmark_smoke import (
    ControlledSmokeAuthorization,
    ScriptedAttemptFixture,
    SmokeAttemptOutcome,
)


def _authorization() -> dict[str, object]:
    return {
        "smoke_id": "smoke-v1",
        "authorization_id": "auth-v1",
        "execution_manifest_sha256": "a" * 64,
        "gate10_manifest_sha256": "b" * 64,
        "gate9_manifest_sha256": "c" * 64,
        "planned_run_ledger_sha256": "d" * 64,
        "functional_episode_set_sha256": "e" * 64,
        "allowed_episode_ids": ["ep-func-001"],
        "allowed_run_ids": [
            "run-functional-ep-func-001-r01-condition-a",
            "run-functional-ep-func-001-r01-condition-b",
            "run-functional-ep-func-001-r01-condition-c",
        ],
        "allowed_conditions": ["condition_a", "condition_b", "condition_c"],
        "maximum_total_attempt_count": 11,
        "maximum_total_cost_microusd": 5000,
    }


def test_authorization_requires_all_three_conditions() -> None:
    payload = _authorization()
    payload["allowed_conditions"] = ["condition_a", "condition_b", "condition_b"]
    with pytest.raises(ValidationError, match="conditions A, B, and C"):
        ControlledSmokeAuthorization.model_validate(payload)


def test_authorization_rejects_duplicate_run_ids() -> None:
    payload = _authorization()
    payload["allowed_run_ids"] = [payload["allowed_run_ids"][0]] * 3  # type: ignore[index]
    with pytest.raises(ValidationError, match="run IDs must be unique"):
        ControlledSmokeAuthorization.model_validate(payload)


def test_ambiguous_attempt_cannot_authorize_retry() -> None:
    payload = {
        "turn_index": 1,
        "attempt_index": 1,
        "outcome": "ambiguous_response",
        "response_certainty": "ambiguous",
        "retryable": True,
        "logical_request_sha256": "a" * 64,
        "provider_request_id_sha256": "b" * 64,
        "provider_error_code": "AMBIGUOUS_PROVIDER_RESPONSE",
        "input_tokens": 1,
        "output_tokens": 0,
        "latency_ms": 1,
        "estimated_cost_microusd": 1,
    }
    with pytest.raises(ValidationError, match="must block retry"):
        ScriptedAttemptFixture.model_validate(payload)


def test_completed_attempt_requires_output_evidence() -> None:
    payload = {
        "turn_index": 1,
        "attempt_index": 1,
        "outcome": SmokeAttemptOutcome.COMPLETED,
        "response_certainty": "success",
        "retryable": False,
        "logical_request_sha256": "a" * 64,
        "provider_request_id_sha256": "b" * 64,
        "input_tokens": 1,
        "output_tokens": 0,
        "latency_ms": 1,
        "estimated_cost_microusd": 1,
    }
    with pytest.raises(ValidationError, match="output evidence"):
        ScriptedAttemptFixture.model_validate(payload)


def test_authorization_is_immutable() -> None:
    authorization = ControlledSmokeAuthorization.model_validate(_authorization())
    with pytest.raises(ValidationError):
        authorization.maximum_total_attempt_count = 12  # type: ignore[misc]


def test_retry_must_preserve_logical_request_fingerprint() -> None:
    payload = {
        "run_id": "run-functional-ep-func-001-r01-condition-a",
        "expected_terminal_status": "provider_error",
        "attempts": [
            {
                "turn_index": 1,
                "attempt_index": 1,
                "outcome": "definite_retryable_failure",
                "response_certainty": "definite_failure",
                "retryable": True,
                "logical_request_sha256": "a" * 64,
                "provider_request_id_sha256": "b" * 64,
                "provider_error_code": "PROVIDER_UNAVAILABLE",
                "input_tokens": 1,
                "output_tokens": 0,
                "latency_ms": 1,
                "estimated_cost_microusd": 1,
            },
            {
                "turn_index": 1,
                "attempt_index": 2,
                "outcome": "completed",
                "response_certainty": "success",
                "retryable": False,
                "logical_request_sha256": "c" * 64,
                "provider_request_id_sha256": "d" * 64,
                "output_sha256": "e" * 64,
                "input_tokens": 1,
                "output_tokens": 1,
                "latency_ms": 1,
                "estimated_cost_microusd": 1,
            },
        ],
    }
    from auragateway.contracts.benchmark_smoke import ScriptedRunScenario

    with pytest.raises(ValidationError, match="logical-request fingerprint"):
        ScriptedRunScenario.model_validate(payload)
