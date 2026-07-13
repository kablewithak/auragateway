from __future__ import annotations

from pathlib import Path

from auragateway.benchmark.execution import append_journal_event, load_journal
from auragateway.contracts.benchmark_execution import (
    LiveAttemptRecord,
    LiveExecutionFailureCode,
    LiveJournalAttemptEvent,
    LiveJournalTerminalEvent,
    LiveResponseCertainty,
    LiveTerminalRecord,
)
from auragateway.contracts.evidence_bundle import BenchmarkCondition, RunTerminalStatus
from auragateway.contracts.provider import ProviderInvocationStatus, ProviderName

_HASH = "a" * 64
_RUN_ID = "run-functional-ep-func-001-r01-condition-a"


def _failed_attempt() -> LiveAttemptRecord:
    return LiveAttemptRecord(
        attempt_id="attempt-" + "1" * 24,
        trace_id="trace-" + "2" * 24,
        run_id=_RUN_ID,
        condition_id=BenchmarkCondition.A,
        turn_index=1,
        attempt_index=1,
        provider=ProviderName.GROQ,
        model_alias="groq-gpt-oss-20b",
        route_reason="benchmark_control",
        provider_status=ProviderInvocationStatus.FAILED,
        response_certainty=LiveResponseCertainty.AMBIGUOUS,
        retry_authorized=False,
        logical_request_sha256=_HASH,
        provider_request_id_sha256=_HASH,
        static_prefix_fingerprint=_HASH,
        prefix_hmac_key_id="test-key-v1",
        system_prompt_sha256=_HASH,
        user_prompt_sha256=_HASH,
        prompt_byte_count=100,
        provider_error_code="TIMEOUT",
        estimated_cost_microusd=0,
    )


def test_journal_round_trip_preserves_attempt_then_terminal(tmp_path: Path) -> None:
    journal = tmp_path / "journal.jsonl"
    attempt = _failed_attempt()
    terminal = LiveTerminalRecord(
        terminal_record_id="terminal-" + "3" * 24,
        trace_id=attempt.trace_id,
        run_id=_RUN_ID,
        comparison_pair_id="pair-functional-ep-func-001-r01",
        episode_id="ep-func-001",
        condition_id=BenchmarkCondition.A,
        cache_namespace_id="ns-functional-ep-func-001-r01-condition-a",
        terminal_status=RunTerminalStatus.ABORTED_SAFETY_CONTROL,
        completed_turn_count=0,
        attempt_count=1,
        attempt_ids=(attempt.attempt_id,),
        structured_output_failure_count=0,
        citation_scope_failure_count=0,
        failure_code=LiveExecutionFailureCode.AMBIGUOUS_PROVIDER_RESPONSE,
    )

    append_journal_event(
        journal,
        LiveJournalAttemptEvent(sequence_index=0, attempt=attempt),
    )
    append_journal_event(
        journal,
        LiveJournalTerminalEvent(sequence_index=1, terminal=terminal),
    )

    events = load_journal(journal)

    assert len(events) == 2
    assert isinstance(events[0], LiveJournalAttemptEvent)
    assert isinstance(events[1], LiveJournalTerminalEvent)
    assert events[1].terminal.attempt_ids == (attempt.attempt_id,)
