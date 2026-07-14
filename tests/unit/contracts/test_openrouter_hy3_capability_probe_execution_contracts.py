from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.openrouter_hy3_capability_probe_execution import (
    OpenRouterProbeExecutionPolicy,
    OpenRouterProbeRawResponseKind,
    OpenRouterProbeRawResponseRecord,
    OpenRouterProbeTerminalOutcome,
    OpenRouterProbeTerminalReceipt,
)


def test_execution_policy_asset_validates() -> None:
    path = Path(
        "data/evals/benchmark/openrouter-hy3-capability-probe-execution-v1/execution_policy.json"
    )
    policy = OpenRouterProbeExecutionPolicy.model_validate_json(path.read_text(encoding="utf-8"))

    assert policy.cold_positive_read_alone_permits_promotion is False
    assert policy.controlled_positive_cache_use_requires == (
        "cold_cache_write_positive",
        "warm_cache_read_positive",
    )
    assert policy.incomplete_journal_closes_without_network is True


def test_raw_response_requires_one_explicit_body_representation() -> None:
    record = OpenRouterProbeRawResponseRecord(
        authorization_id="openrouter-hy3-capability-probe-auth-v1",
        execution_id="openrouter-hy3-capability-probe-v1",
        attempt_id="openrouter-hy3-capability-probe-v1-cold-attempt-1",
        logical_call_role="cold_probe",
        attempt_number=1,
        response_sequence=1,
        response_kind=OpenRouterProbeRawResponseKind.COMPLETION,
        received_at=datetime(2026, 7, 14, tzinfo=UTC),
        http_status=200,
        body_sha256="a" * 64,
        body_bytes=4,
        body_representation="json",
        json_payload=None,
    )
    assert record.json_payload is None

    invalid = record.model_copy(update={"body_utf8": "null"})
    with pytest.raises(ValidationError, match="alternate body"):
        OpenRouterProbeRawResponseRecord.model_validate(invalid.model_dump())


def _receipt(**updates: object) -> OpenRouterProbeTerminalReceipt:
    payload: dict[str, object] = {
        "authorization_id": "openrouter-hy3-capability-probe-auth-v1",
        "execution_id": "openrouter-hy3-capability-probe-v1",
        "terminal_outcome": "promoted_to_pilot_authorization_review",
        "source_commit": "a" * 40,
        "execution_started_at": datetime(2026, 7, 14, 10, tzinfo=UTC),
        "closed_at": datetime(2026, 7, 14, 10, 1, tzinfo=UTC),
        "attempt_count": 2,
        "provider_success_count": 2,
        "retained_success_count": 2,
        "replacement_count": 0,
        "numeric_measurement_channel_observed": True,
        "controlled_positive_cache_use_observed": True,
        "cold_positive_cache_read_contamination": False,
        "route_identity_valid": True,
        "prompt_bundle_sha256": "b" * 64,
        "preflight_receipt_sha256": "c" * 64,
        "journal_sha256_before_close": "d" * 64,
        "journal_bytes_before_close": 100,
        "raw_responses_sha256": "e" * 64,
        "parsed_responses_sha256": "f" * 64,
        "next_gate": "pilot_authorization_review",
    }
    payload.update(updates)
    return OpenRouterProbeTerminalReceipt.model_validate(payload)


def test_promotion_requires_controlled_positive_cache_use() -> None:
    with pytest.raises(ValidationError, match="controlled positive"):
        _receipt(controlled_positive_cache_use_observed=False)


def test_interrupted_closeout_requires_execution_start() -> None:
    with pytest.raises(ValidationError, match="execution start"):
        _receipt(
            terminal_outcome=OpenRouterProbeTerminalOutcome.CLOSED_INTERRUPTED_EXECUTION,
            execution_started_at=None,
            retained_success_count=0,
            provider_success_count=0,
            numeric_measurement_channel_observed=False,
            controlled_positive_cache_use_observed=False,
            route_identity_valid=False,
            next_gate="sanitized_capability_closeout",
        )
