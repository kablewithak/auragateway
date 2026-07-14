from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel

import auragateway.benchmark.openrouter_hy3_capability_probe_closeout_runner as runner
from auragateway.contracts.openrouter_hy3_capability_probe_execution import (
    OpenRouterProbeJournalRecord,
    OpenRouterProbeRawResponseRecord,
    OpenRouterProbeTerminalReceipt,
)


def _write_json(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, models: Sequence[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(model.model_dump_json() + "\n" for model in models),
        encoding="utf-8",
    )


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path
    local = repo / ".local/benchmark/openrouter-hy3-capability-probe-v1"
    raw = OpenRouterProbeRawResponseRecord(
        authorization_id="openrouter-hy3-capability-probe-auth-v1",
        execution_id="openrouter-hy3-capability-probe-v1",
        attempt_id="openrouter-hy3-capability-probe-v1-cold-attempt-1",
        logical_call_role="cold_probe",
        attempt_number=1,
        response_sequence=1,
        response_kind="completion",
        received_at=datetime(2026, 7, 14, tzinfo=UTC),
        http_status=401,
        content_type="application/json",
        body_sha256="a" * 64,
        body_bytes=64,
        body_representation="json",
        json_payload={"error": {"code": 401, "message": "Missing Authentication header"}},
    )
    journal = [
        OpenRouterProbeJournalRecord(
            authorization_id="openrouter-hy3-capability-probe-auth-v1",
            execution_id="openrouter-hy3-capability-probe-v1",
            event_index=1,
            event_type="execution_started",
            recorded_at=datetime(2026, 7, 14, tzinfo=UTC),
            total_attempt_count=0,
            provider_success_count=0,
            retained_success_count=0,
            replacement_count=0,
        ),
        OpenRouterProbeJournalRecord(
            authorization_id="openrouter-hy3-capability-probe-auth-v1",
            execution_id="openrouter-hy3-capability-probe-v1",
            event_index=2,
            event_type="attempt_started",
            recorded_at=datetime(2026, 7, 14, tzinfo=UTC),
            attempt_id="openrouter-hy3-capability-probe-v1-cold-attempt-1",
            logical_call_role="cold_probe",
            attempt_number=1,
            total_attempt_count=1,
            provider_success_count=0,
            retained_success_count=0,
            replacement_count=0,
        ),
        OpenRouterProbeJournalRecord(
            authorization_id="openrouter-hy3-capability-probe-auth-v1",
            execution_id="openrouter-hy3-capability-probe-v1",
            event_index=3,
            event_type="attempt_terminal_failure",
            recorded_at=datetime(2026, 7, 14, tzinfo=UTC),
            attempt_id="openrouter-hy3-capability-probe-v1-cold-attempt-1",
            logical_call_role="cold_probe",
            attempt_number=1,
            total_attempt_count=1,
            provider_success_count=0,
            retained_success_count=0,
            replacement_count=0,
            safe_error_code="PROVIDER_AUTHENTICATION_FAILED",
            retry_permitted=False,
        ),
        OpenRouterProbeJournalRecord(
            authorization_id="openrouter-hy3-capability-probe-auth-v1",
            execution_id="openrouter-hy3-capability-probe-v1",
            event_index=4,
            event_type="execution_closed",
            recorded_at=datetime(2026, 7, 14, tzinfo=UTC),
            total_attempt_count=1,
            provider_success_count=0,
            retained_success_count=0,
            replacement_count=0,
            terminal_outcome="closed_terminal_provider_failure",
        ),
    ]
    _write_jsonl(local / "raw_responses.jsonl", [raw])
    _write_jsonl(local / "journal.jsonl", journal)
    (local / "parsed_responses.jsonl").write_bytes(b"")
    receipt = OpenRouterProbeTerminalReceipt(
        authorization_id="openrouter-hy3-capability-probe-auth-v1",
        execution_id="openrouter-hy3-capability-probe-v1",
        terminal_outcome="closed_terminal_provider_failure",
        source_commit="b" * 40,
        execution_started_at=datetime(2026, 7, 14, tzinfo=UTC),
        closed_at=datetime(2026, 7, 14, tzinfo=UTC),
        attempt_count=1,
        provider_success_count=0,
        retained_success_count=0,
        replacement_count=0,
        numeric_measurement_channel_observed=False,
        controlled_positive_cache_use_observed=False,
        cold_positive_cache_read_contamination=False,
        route_identity_valid=False,
        prompt_bundle_sha256="c" * 64,
        preflight_receipt_sha256="d" * 64,
        journal_sha256_before_close="e" * 64,
        journal_bytes_before_close=0,
        raw_responses_sha256=runner._sha256_file(local / "raw_responses.jsonl"),
        parsed_responses_sha256=runner._sha256_file(local / "parsed_responses.jsonl"),
        next_gate="sanitized_capability_closeout",
    )
    _write_json(local / "terminal_receipt.json", receipt)

    source_root = Path.cwd()
    for relative in (
        "src/auragateway/contracts/openrouter_hy3_capability_probe_closeout.py",
        "src/auragateway/benchmark/openrouter_hy3_capability_probe_closeout_runner.py",
        "data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_policy.json",
        "docs/adr/openrouter-hy3-capability-probe-closeout.md",
        "docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Closeout.md",
    ):
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((source_root / relative).read_bytes())
    return repo


def test_generate_closeout_publishes_only_sanitized_metadata(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    summary = runner.generate_closeout(
        repo,
        clock=lambda: datetime(2026, 7, 14, 12, tzinfo=UTC),
    )
    assert summary.next_gate == "validate_and_commit_sanitized_closeout"
    result_path = (
        repo
        / "data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_result.json"
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["http_status"] == 401
    assert result["provider_error_message"] == "Missing Authentication header"
    assert result["public_raw_payload_included"] is False
    assert "json_payload" not in result
    assert runner.validate_public(repo).next_gate == "terminal_review_and_continuity_update"


def test_validate_local_rejects_unexpected_parsed_observation(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    parsed = repo / ".local/benchmark/openrouter-hy3-capability-probe-v1/parsed_responses.jsonl"
    parsed.write_text("{}\n", encoding="utf-8")
    with pytest.raises(runner.OpenRouterProbeCloseoutError):
        runner.validate_local(repo)
