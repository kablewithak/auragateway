from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from auragateway.benchmark.diagnostic_closeout_runner import (
    DiagnosticCloseoutError,
    _verify_public_execution_evidence,
    build_expected_closeout,
)
from auragateway.contracts.diagnostic_closeout import (
    DiagnosticClaimDecision,
    DiagnosticClaimKind,
    DiagnosticHypothesisId,
    DiagnosticHypothesisVerdict,
)
from auragateway.contracts.diagnostic_execution import (
    DiagnosticExecutionAttemptRecord,
    DiagnosticExecutionAttemptStatus,
    DiagnosticExecutionManifest,
    DiagnosticExecutionRecordSet,
    DiagnosticExecutionReport,
    DiagnosticSequenceRecord,
    DiagnosticSequenceStatus,
)

_INPUT_TOKENS = (
    1584,
    1669,
    1753,
    1584,
    1669,
    1753,
    1588,
    1676,
    1755,
    1588,
    1676,
    1755,
    1591,
    1674,
    1755,
    1598,
    1683,
    1768,
    1590,
    1675,
    1757,
    1587,
    1671,
    1752,
)
_DURATION_MS = (
    177,
    215,
    170,
    167,
    172,
    173,
    225,
    373,
    148,
    172,
    183,
    145,
    135,
    195,
    306,
    172,
    164,
    145,
    193,
    167,
    169,
    190,
    224,
    215,
)
_SEQUENCE_IDS = (
    "order-alpha-b-first",
    "order-alpha-c-second",
    "order-beta-c-first",
    "order-beta-b-second",
    "spacing-gamma-b-zero",
    "spacing-delta-b-thirty",
    "spacing-epsilon-c-zero",
    "spacing-zeta-c-thirty",
)
_CONDITIONS = (
    "condition_b",
    "condition_c",
    "condition_c",
    "condition_b",
    "condition_b",
    "condition_b",
    "condition_c",
    "condition_c",
)


def _hash(value: int) -> str:
    return f"{value:064x}"


def _request_hash(attempt_index: int) -> str:
    if 3 <= attempt_index <= 5:
        return _hash(100 + attempt_index - 3)
    if 9 <= attempt_index <= 11:
        return _hash(200 + attempt_index - 9)
    if attempt_index <= 2:
        return _hash(100 + attempt_index)
    if 6 <= attempt_index <= 8:
        return _hash(200 + attempt_index - 6)
    return _hash(300 + attempt_index)


def _records() -> DiagnosticExecutionRecordSet:
    estimates_by_turn = (1732, 1809, 1884)
    attempts: list[DiagnosticExecutionAttemptRecord] = []
    for attempt_index in range(24):
        sequence_index = attempt_index // 3
        turn_index = (attempt_index % 3) + 1
        attempts.append(
            DiagnosticExecutionAttemptRecord(
                attempt_index=attempt_index,
                sequence_id=_SEQUENCE_IDS[sequence_index],
                sequence_schedule_index=sequence_index,
                stage=("order_reversal" if sequence_index < 4 else "spacing_matrix"),
                cohort_id=f"cohort-{sequence_index:02d}",
                condition_label=_CONDITIONS[sequence_index],
                turn_index=turn_index,
                planned_offset_seconds=min(sequence_index * 300, 2220),
                observed_offset_ms=attempt_index * 1000,
                system_prompt_sha256=_hash(500 + sequence_index),
                user_prompt_sha256=_hash(600 + attempt_index),
                provider_request_sha256=_request_hash(attempt_index),
                prompt_byte_count=(7365, 7737, 8109)[turn_index - 1],
                input_token_estimate=estimates_by_turn[turn_index - 1],
                status=DiagnosticExecutionAttemptStatus.SUCCEEDED,
                provider_call_made=True,
                output_sha256=_hash(700 + attempt_index),
                output_byte_count=100,
                input_tokens=_INPUT_TOKENS[attempt_index],
                cached_input_tokens=None,
                output_tokens=50,
                total_duration_ms=_DURATION_MS[attempt_index],
                estimated_cost_microusd=208,
            )
        )

    sequences = tuple(
        DiagnosticSequenceRecord(
            sequence_id=sequence_id,
            status=DiagnosticSequenceStatus.COMPLETED,
            provider_call_count=3,
            successful_call_count=3,
            provider_error_count=0,
            skipped_attempt_count=0,
        )
        for sequence_id in _SEQUENCE_IDS
    )
    return DiagnosticExecutionRecordSet(
        authorization_id="batch-06-diagnostic-execution-auth-v1",
        attempts=tuple(attempts),
        sequences=sequences,
        provider_call_count=24,
        successful_call_count=24,
        provider_error_count=0,
        skipped_sequence_attempt_count=0,
        skipped_experiment_attempt_count=0,
        estimated_cost_microusd=4992,
        live_provider_called=True,
    )


def _report() -> DiagnosticExecutionReport:
    return DiagnosticExecutionReport(
        authorization_id="batch-06-diagnostic-execution-auth-v1",
        provider_call_count=24,
        completed_sequence_count=8,
        request_rejected_sequence_count=0,
        experiment_stopped_sequence_count=0,
        not_started_sequence_count=0,
        successful_call_count=24,
        provider_error_count=0,
        skipped_attempt_count=0,
        estimated_cost_microusd=4992,
        protected_outputs_retained_locally=True,
        live_provider_called=True,
    )


def _write_execution_placeholders(repo_root: Path) -> None:
    paths = (
        "authorization.json",
        "runtime_policy.json",
        "journal.jsonl",
        "run_records.json",
        "report.json",
        "manifest.json",
    )
    execution_root = repo_root / "data/evals/benchmark/diagnostic-execution-v1"
    execution_root.mkdir(parents=True)
    for index, name in enumerate(paths):
        (execution_root / name).write_text(
            f"synthetic-{index}\n",
            encoding="utf-8",
        )


def test_builder_reproduces_frozen_metrics(tmp_path: Path) -> None:
    _write_execution_placeholders(tmp_path)

    closeout = build_expected_closeout(tmp_path, _records(), _report())

    assert closeout.execution_outcome.provider_call_count == 24
    assert closeout.token_calibration.estimated_input_tokens_total == 43400
    assert closeout.token_calibration.observed_input_tokens_total == 40151
    assert closeout.token_calibration.estimate_minus_observed_tokens == 3249
    assert closeout.token_calibration.estimate_over_observed_parts_per_million == 80920
    assert closeout.duration_assessment.duration_total_ms == 4595
    assert closeout.duration_assessment.mean_duration_milli_ms == 191458
    assert closeout.duration_assessment.median_duration_milli_ms == 172500


def test_builder_preserves_cache_unknown(tmp_path: Path) -> None:
    _write_execution_placeholders(tmp_path)

    closeout = build_expected_closeout(tmp_path, _records(), _report())

    assert closeout.cache_telemetry.cached_input_token_sample_count == 0
    assert closeout.cache_telemetry.total_cached_input_tokens is None
    assert closeout.cache_telemetry.unknown_interpreted_as_zero is False


def test_builder_records_all_hypothesis_verdicts(tmp_path: Path) -> None:
    _write_execution_placeholders(tmp_path)

    closeout = build_expected_closeout(tmp_path, _records(), _report())
    verdicts = {item.hypothesis_id: item.verdict for item in closeout.hypotheses}

    assert verdicts[DiagnosticHypothesisId.DETERMINISTIC_REQUEST_DEFECT] is (
        DiagnosticHypothesisVerdict.STRONGLY_CONTRADICTED
    )
    assert (
        verdicts[DiagnosticHypothesisId.TRANSIENT_OR_HIDDEN_PROVIDER_BACKEND_EVENT]
        is DiagnosticHypothesisVerdict.BEST_SUPPORTED_INFERENCE
    )


def test_builder_blocks_cache_latency_and_comparison_claims(
    tmp_path: Path,
) -> None:
    _write_execution_placeholders(tmp_path)

    closeout = build_expected_closeout(tmp_path, _records(), _report())
    decisions = {item.claim_kind: item.decision for item in closeout.claims}

    for claim in (
        DiagnosticClaimKind.CACHE_USAGE,
        DiagnosticClaimKind.CACHE_SAVINGS,
        DiagnosticClaimKind.LATENCY_IMPROVEMENT,
        DiagnosticClaimKind.ACCEPTED_A_B_C_COMPARISON,
    ):
        assert decisions[claim] is DiagnosticClaimDecision.BLOCKED


def test_builder_rejects_unexpected_cache_samples(tmp_path: Path) -> None:
    _write_execution_placeholders(tmp_path)
    payload = _records().model_dump(mode="python")
    attempts = payload["attempts"]
    assert isinstance(attempts, tuple)
    attempts[0]["cached_input_tokens"] = 100
    records = DiagnosticExecutionRecordSet.model_validate(payload)

    with pytest.raises(
        DiagnosticCloseoutError,
        match="expects cached-input telemetry to remain unavailable",
    ):
        build_expected_closeout(tmp_path, records, _report())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_public_execution_evidence(
    repo_root: Path,
    records: DiagnosticExecutionRecordSet,
    report: DiagnosticExecutionReport,
) -> DiagnosticExecutionManifest:
    execution_root = repo_root / "data/evals/benchmark/diagnostic-execution-v1"
    review_root = repo_root / "data/evals/benchmark/diagnostic-authorization-review-v1"
    execution_root.mkdir(parents=True)
    review_root.mkdir(parents=True)

    authorization_path = execution_root / "authorization.json"
    runtime_policy_path = execution_root / "runtime_policy.json"
    journal_path = execution_root / "journal.jsonl"
    run_records_path = execution_root / "run_records.json"
    report_path = execution_root / "report.json"
    review_manifest_path = review_root / "manifest.json"
    dry_run_path = review_root / "dry_run_report.json"

    authorization_path.write_text("{}\n", encoding="utf-8")
    runtime_policy_path.write_text("{}\n", encoding="utf-8")
    review_manifest_path.write_text("{}\n", encoding="utf-8")
    dry_run_path.write_text("{}\n", encoding="utf-8")
    journal_path.write_text(
        "".join(f"{item.model_dump_json()}\n" for item in records.attempts),
        encoding="utf-8",
    )
    run_records_path.write_text(records.model_dump_json(), encoding="utf-8")
    report_path.write_text(report.model_dump_json(), encoding="utf-8")

    return DiagnosticExecutionManifest(
        authorization_id="batch-06-diagnostic-execution-auth-v1",
        authorization_sha256=_sha256(authorization_path),
        runtime_policy_sha256=_sha256(runtime_policy_path),
        review_manifest_sha256=_sha256(review_manifest_path),
        dry_run_report_sha256=_sha256(dry_run_path),
        journal_sha256=_sha256(journal_path),
        run_records_sha256=_sha256(run_records_path),
        report_sha256=_sha256(report_path),
        protected_raw_outputs_path=(
            ".local/benchmark/diagnostic-execution-v1/provider_raw_outputs.jsonl"
        ),
        protected_failure_diagnostics_path=(
            ".local/benchmark/diagnostic-execution-v1/provider_failure_diagnostics.jsonl"
        ),
        live_provider_called=True,
    )


def test_public_execution_evidence_reconciles_without_protected_files(
    tmp_path: Path,
) -> None:
    records = _records()
    report = _report()
    manifest = _write_public_execution_evidence(tmp_path, records, report)

    _verify_public_execution_evidence(tmp_path, records, report, manifest)


def test_public_execution_evidence_rejects_journal_drift(
    tmp_path: Path,
) -> None:
    records = _records()
    report = _report()
    manifest = _write_public_execution_evidence(tmp_path, records, report)
    journal_path = tmp_path / "data/evals/benchmark/diagnostic-execution-v1/journal.jsonl"
    journal_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(DiagnosticCloseoutError):
        _verify_public_execution_evidence(tmp_path, records, report, manifest)
