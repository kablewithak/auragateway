"""Validate immutable Batch 06 diagnostic closeout evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from auragateway.contracts.diagnostic_closeout import (
    DiagnosticCacheTelemetryAssessment,
    DiagnosticClaimDecision,
    DiagnosticClaimDecisionRecord,
    DiagnosticClaimKind,
    DiagnosticClaimReason,
    DiagnosticCloseout,
    DiagnosticCloseoutBinding,
    DiagnosticCloseoutManifest,
    DiagnosticCloseoutStatus,
    DiagnosticCloseoutValidationSummary,
    DiagnosticDurationAssessment,
    DiagnosticEvidenceCode,
    DiagnosticExecutionOutcome,
    DiagnosticHypothesisConclusion,
    DiagnosticHypothesisId,
    DiagnosticHypothesisVerdict,
    DiagnosticImplementationResolution,
    DiagnosticTokenCalibration,
)
from auragateway.contracts.diagnostic_execution import (
    DiagnosticExecutionAttemptRecord,
    DiagnosticExecutionManifest,
    DiagnosticExecutionRecordSet,
    DiagnosticExecutionReport,
)

_EXECUTION_ROOT = Path("data/evals/benchmark/diagnostic-execution-v1")
_CLOSEOUT_ROOT = Path("data/evals/benchmark/diagnostic-closeout-v1")
_CLOSEOUT_PATH = _CLOSEOUT_ROOT / "closeout.json"
_CLOSEOUT_MANIFEST_PATH = _CLOSEOUT_ROOT / "manifest.json"
_CLOSEOUT_REPORT_PATH = Path("docs/benchmark/AuraGateway_Batch_06_Diagnostic_Closeout.md")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class DiagnosticCloseoutError(Exception):
    """Expected metadata-safe closeout validation failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        *,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_REQUIRED_ASSET_MISSING",
            "A required diagnostic closeout asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_REQUIRED_ASSET_MISSING",
            "A required diagnostic closeout asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_INVALID_JSON",
            "A diagnostic closeout asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_VALIDATION_FAILED",
            "A diagnostic closeout asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _execution_paths() -> tuple[Path, ...]:
    return (
        _EXECUTION_ROOT / "authorization.json",
        _EXECUTION_ROOT / "runtime_policy.json",
        _EXECUTION_ROOT / "journal.jsonl",
        _EXECUTION_ROOT / "run_records.json",
        _EXECUTION_ROOT / "report.json",
        _EXECUTION_ROOT / "manifest.json",
    )


def _execution_bindings(repo_root: Path) -> tuple[DiagnosticCloseoutBinding, ...]:
    return tuple(
        DiagnosticCloseoutBinding(
            path=path.as_posix(),
            sha256=_sha256_file(repo_root / path),
        )
        for path in _execution_paths()
    )


def _duration_assessment(
    records: DiagnosticExecutionRecordSet,
) -> DiagnosticDurationAssessment:
    durations = [
        item.total_duration_ms for item in records.attempts if item.total_duration_ms is not None
    ]
    if len(durations) != 24:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_DURATION_COVERAGE_INCOMPLETE",
            "All 24 diagnostic attempts require duration telemetry for closeout.",
        )

    by_request: dict[str, list[int]] = defaultdict(list)
    for attempt in records.attempts:
        if attempt.total_duration_ms is None:
            continue
        by_request[attempt.provider_request_sha256].append(attempt.total_duration_ms)
    repeated_pairs = [values for values in by_request.values() if len(values) == 2]
    invalid_repeats = [values for values in by_request.values() if len(values) > 2]
    if len(repeated_pairs) != 6 or invalid_repeats:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_REPEATED_REQUEST_SHAPE_INVALID",
            "The diagnostic execution must contain six exact repeated-request pairs.",
        )

    pair_deltas = [values[1] - values[0] for values in repeated_pairs]
    return DiagnosticDurationAssessment(
        duration_total_ms=sum(durations),
        mean_duration_milli_ms=round(statistics.mean(durations) * 1000),
        median_duration_milli_ms=round(statistics.median(durations) * 1000),
        minimum_duration_ms=min(durations),
        maximum_duration_ms=max(durations),
        second_occurrence_faster_pair_count=sum(delta < 0 for delta in pair_deltas),
        mean_second_minus_first_duration_milli_ms=round(statistics.mean(pair_deltas) * 1000),
        median_second_minus_first_duration_milli_ms=round(statistics.median(pair_deltas) * 1000),
    )


def _token_calibration(
    records: DiagnosticExecutionRecordSet,
) -> DiagnosticTokenCalibration:
    estimates = [item.input_token_estimate for item in records.attempts]
    observed = [item.input_tokens for item in records.attempts if item.input_tokens is not None]
    if len(estimates) != 24 or len(observed) != 24:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_TOKEN_COVERAGE_INCOMPLETE",
            "All 24 diagnostic attempts require estimate and observed token counts.",
        )

    estimated_total = sum(estimates)
    observed_total = sum(observed)
    difference = estimated_total - observed_total
    if observed_total <= 0 or difference <= 0:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_TOKEN_CALIBRATION_INVALID",
            "The frozen estimator must remain a positive conservative overestimate.",
        )
    return DiagnosticTokenCalibration(
        estimated_input_tokens_total=estimated_total,
        observed_input_tokens_total=observed_total,
        estimate_minus_observed_tokens=difference,
        estimate_over_observed_parts_per_million=round(difference * 1_000_000 / observed_total),
    )


def _cache_assessment(
    records: DiagnosticExecutionRecordSet,
) -> DiagnosticCacheTelemetryAssessment:
    samples = [
        item.cached_input_tokens
        for item in records.attempts
        if item.cached_input_tokens is not None
    ]
    if samples:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_CACHE_EVIDENCE_UNEXPECTED",
            "The frozen closeout expects cached-input telemetry to remain unavailable.",
        )
    return DiagnosticCacheTelemetryAssessment()


def _hypotheses() -> tuple[DiagnosticHypothesisConclusion, ...]:
    return (
        DiagnosticHypothesisConclusion(
            hypothesis_id=DiagnosticHypothesisId.DETERMINISTIC_REQUEST_DEFECT,
            verdict=DiagnosticHypothesisVerdict.STRONGLY_CONTRADICTED,
            evidence_codes=(
                DiagnosticEvidenceCode.ALL_24_CALLS_SUCCEEDED,
                DiagnosticEvidenceCode.ZERO_REQUEST_REJECTIONS,
            ),
        ),
        DiagnosticHypothesisConclusion(
            hypothesis_id=DiagnosticHypothesisId.FIRST_SEQUENCE_STATE_EFFECT,
            verdict=DiagnosticHypothesisVerdict.NOT_OBSERVED,
            evidence_codes=(
                DiagnosticEvidenceCode.ORDER_REVERSALS_SUCCEEDED,
                DiagnosticEvidenceCode.ALL_8_SEQUENCES_COMPLETED,
            ),
        ),
        DiagnosticHypothesisConclusion(
            hypothesis_id=DiagnosticHypothesisId.SPACING_SENSITIVE_PROVIDER_STATE,
            verdict=(DiagnosticHypothesisVerdict.NOT_OBSERVED_FOR_REQUEST_ACCEPTANCE),
            evidence_codes=(
                DiagnosticEvidenceCode.ZERO_AND_THIRTY_SECOND_CELLS_SUCCEEDED,
                DiagnosticEvidenceCode.ZERO_REQUEST_REJECTIONS,
            ),
        ),
        DiagnosticHypothesisConclusion(
            hypothesis_id=(DiagnosticHypothesisId.HIDDEN_CONDITION_SPECIFIC_HARNESS_DIFFERENCE),
            verdict=(DiagnosticHypothesisVerdict.STRONGLY_CONTRADICTED_AT_PROVIDER_BOUNDARY),
            evidence_codes=(
                DiagnosticEvidenceCode.MATCHED_B_C_REQUEST_IDENTITIES_SUCCEEDED,
                DiagnosticEvidenceCode.ALL_24_CALLS_SUCCEEDED,
            ),
        ),
        DiagnosticHypothesisConclusion(
            hypothesis_id=(DiagnosticHypothesisId.TRANSIENT_OR_HIDDEN_PROVIDER_BACKEND_EVENT),
            verdict=DiagnosticHypothesisVerdict.BEST_SUPPORTED_INFERENCE,
            evidence_codes=(
                DiagnosticEvidenceCode.ALL_24_CALLS_SUCCEEDED,
                DiagnosticEvidenceCode.ZERO_REQUEST_REJECTIONS,
                DiagnosticEvidenceCode.ORDER_REVERSALS_SUCCEEDED,
                DiagnosticEvidenceCode.ZERO_AND_THIRTY_SECOND_CELLS_SUCCEEDED,
            ),
        ),
    )


def _claims() -> tuple[DiagnosticClaimDecisionRecord, ...]:
    return (
        DiagnosticClaimDecisionRecord(
            claim_kind=DiagnosticClaimKind.REQUEST_REJECTION_NONREPRODUCTION,
            decision=DiagnosticClaimDecision.PERMITTED,
            reason=DiagnosticClaimReason.CONTROLLED_NONREPRODUCTION_OBSERVED,
        ),
        DiagnosticClaimDecisionRecord(
            claim_kind=DiagnosticClaimKind.DETERMINISTIC_REQUEST_DEFECT_CONTRADICTED,
            decision=DiagnosticClaimDecision.PERMITTED,
            reason=DiagnosticClaimReason.DETERMINISTIC_DEFECT_CONTRADICTED,
        ),
        DiagnosticClaimDecisionRecord(
            claim_kind=DiagnosticClaimKind.EXACT_PROVIDER_ROOT_CAUSE,
            decision=DiagnosticClaimDecision.BLOCKED,
            reason=DiagnosticClaimReason.PROVIDER_INTERNAL_STATE_UNOBSERVED,
        ),
        DiagnosticClaimDecisionRecord(
            claim_kind=DiagnosticClaimKind.CACHE_USAGE,
            decision=DiagnosticClaimDecision.BLOCKED,
            reason=DiagnosticClaimReason.CACHE_EVIDENCE_UNAVAILABLE,
        ),
        DiagnosticClaimDecisionRecord(
            claim_kind=DiagnosticClaimKind.CACHE_SAVINGS,
            decision=DiagnosticClaimDecision.BLOCKED,
            reason=DiagnosticClaimReason.CACHE_EVIDENCE_UNAVAILABLE,
        ),
        DiagnosticClaimDecisionRecord(
            claim_kind=DiagnosticClaimKind.LATENCY_IMPROVEMENT,
            decision=DiagnosticClaimDecision.BLOCKED,
            reason=DiagnosticClaimReason.DIAGNOSTIC_NOT_POWERED_FOR_LATENCY,
        ),
        DiagnosticClaimDecisionRecord(
            claim_kind=DiagnosticClaimKind.ACCEPTED_A_B_C_COMPARISON,
            decision=DiagnosticClaimDecision.BLOCKED,
            reason=DiagnosticClaimReason.COMPARISON_INELIGIBLE_DIAGNOSTIC,
        ),
    )


def build_expected_closeout(
    repo_root: Path,
    records: DiagnosticExecutionRecordSet,
    report: DiagnosticExecutionReport,
) -> DiagnosticCloseout:
    """Derive the immutable closeout from public execution evidence."""

    if (
        records.provider_call_count != 24
        or records.successful_call_count != 24
        or records.provider_error_count != 0
    ):
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_EXECUTION_OUTCOME_UNEXPECTED",
            "The frozen closeout requires 24 successful calls and zero provider errors.",
        )
    if (
        report.completed_sequence_count != 8
        or report.request_rejected_sequence_count != 0
        or report.skipped_attempt_count != 0
    ):
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_SEQUENCE_OUTCOME_UNEXPECTED",
            "The frozen closeout requires all eight sequences to complete.",
        )

    return DiagnosticCloseout(
        closeout_id="batch-06-diagnostic-closeout-v1",
        source_batch_id="auragateway-live-development-batch-06",
        authorization_id="batch-06-diagnostic-execution-auth-v1",
        execution_bindings=_execution_bindings(repo_root),
        execution_outcome=DiagnosticExecutionOutcome(),
        token_calibration=_token_calibration(records),
        cache_telemetry=_cache_assessment(records),
        duration_assessment=_duration_assessment(records),
        hypotheses=_hypotheses(),
        claims=_claims(),
        implementation_resolution=DiagnosticImplementationResolution(),
    )


def _assert_equal(observed: BaseModel, expected: BaseModel, error_code: str) -> None:
    if observed.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise DiagnosticCloseoutError(
            error_code,
            "Committed diagnostic closeout evidence does not reproduce.",
        )


def _load_journal(path: Path) -> tuple[DiagnosticExecutionAttemptRecord, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_JOURNAL_MISSING",
            "The public diagnostic journal was not found.",
            path=str(path),
        ) from exc
    try:
        return tuple(
            DiagnosticExecutionAttemptRecord.model_validate_json(line)
            for line in lines
            if line.strip()
        )
    except ValidationError as exc:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_JOURNAL_INVALID",
            "The public diagnostic journal contains an invalid record.",
            path=str(path),
        ) from exc


def _verify_public_execution_evidence(
    repo_root: Path,
    records: DiagnosticExecutionRecordSet,
    report: DiagnosticExecutionReport,
    execution_manifest: DiagnosticExecutionManifest,
) -> None:
    if (
        records.provider_call_count != 24
        or records.successful_call_count != 24
        or records.provider_error_count != 0
        or not records.live_provider_called
        or not records.execution_completed
    ):
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_EXECUTION_NOT_COMPLETE",
            "The public diagnostic execution is not complete and successful.",
        )
    if (
        report.provider_call_count != 24
        or report.successful_call_count != 24
        or report.provider_error_count != 0
        or not report.live_provider_called
        or not report.execution_completed
    ):
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_REPORT_NOT_COMPLETE",
            "The public diagnostic report is not complete and successful.",
        )

    journal_path = repo_root / _EXECUTION_ROOT / "journal.jsonl"
    journal = _load_journal(journal_path)
    if journal != records.attempts:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_JOURNAL_RECONCILIATION_FAILED",
            "The public journal and public run records differ.",
        )

    expected_hashes = {
        "authorization_sha256": _sha256_file(repo_root / _EXECUTION_ROOT / "authorization.json"),
        "runtime_policy_sha256": _sha256_file(repo_root / _EXECUTION_ROOT / "runtime_policy.json"),
        "review_manifest_sha256": _sha256_file(
            repo_root / "data/evals/benchmark/diagnostic-authorization-review-v1/manifest.json"
        ),
        "dry_run_report_sha256": _sha256_file(
            repo_root
            / "data/evals/benchmark/diagnostic-authorization-review-v1/dry_run_report.json"
        ),
        "journal_sha256": _sha256_file(journal_path),
        "run_records_sha256": _sha256_file(repo_root / _EXECUTION_ROOT / "run_records.json"),
        "report_sha256": _sha256_file(repo_root / _EXECUTION_ROOT / "report.json"),
    }
    observed_hashes = {key: getattr(execution_manifest, key) for key in expected_hashes}
    if observed_hashes != expected_hashes:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_EXECUTION_MANIFEST_RECONCILIATION_FAILED",
            "The execution manifest does not reconcile with public evidence.",
        )


def validate_closeout(repo_root: Path) -> DiagnosticCloseoutValidationSummary:
    """Validate public execution evidence and reproduce the immutable closeout."""

    records = _load_model(
        repo_root / _EXECUTION_ROOT / "run_records.json",
        DiagnosticExecutionRecordSet,
    )
    report = _load_model(
        repo_root / _EXECUTION_ROOT / "report.json",
        DiagnosticExecutionReport,
    )
    execution_manifest = _load_model(
        repo_root / _EXECUTION_ROOT / "manifest.json",
        DiagnosticExecutionManifest,
    )
    _verify_public_execution_evidence(
        repo_root,
        records,
        report,
        execution_manifest,
    )
    closeout = _load_model(repo_root / _CLOSEOUT_PATH, DiagnosticCloseout)
    closeout_manifest = _load_model(
        repo_root / _CLOSEOUT_MANIFEST_PATH,
        DiagnosticCloseoutManifest,
    )

    expected_closeout = build_expected_closeout(repo_root, records, report)
    _assert_equal(
        closeout,
        expected_closeout,
        "DIAGNOSTIC_CLOSEOUT_REPRODUCTION_FAILED",
    )

    if closeout_manifest.closeout_id != closeout.closeout_id:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_MANIFEST_ID_MISMATCH",
            "The closeout manifest identifies a different closeout.",
        )
    if _sha256_file(repo_root / closeout_manifest.closeout_path) != (
        closeout_manifest.closeout_sha256
    ):
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_HASH_MISMATCH",
            "The closeout JSON no longer matches its manifest.",
            path=str(repo_root / closeout_manifest.closeout_path),
        )
    if _sha256_file(repo_root / closeout_manifest.report_path) != (closeout_manifest.report_sha256):
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_REPORT_HASH_MISMATCH",
            "The closeout report no longer matches its manifest.",
            path=str(repo_root / closeout_manifest.report_path),
        )
    if _sha256_file(repo_root / closeout_manifest.execution_manifest_path) != (
        closeout_manifest.execution_manifest_sha256
    ):
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_EXECUTION_MANIFEST_HASH_MISMATCH",
            "The execution manifest no longer matches the closeout manifest.",
            path=str(repo_root / closeout_manifest.execution_manifest_path),
        )
    if execution_manifest.authorization_id != closeout.authorization_id:
        raise DiagnosticCloseoutError(
            "DIAGNOSTIC_CLOSEOUT_AUTHORIZATION_MISMATCH",
            "The execution manifest and closeout use different authorizations.",
        )

    return DiagnosticCloseoutValidationSummary(
        closeout_id=closeout.closeout_id,
        status=DiagnosticCloseoutStatus.CLOSED_NONREPRODUCED,
    )


def _error_envelope(exc: DiagnosticCloseoutError) -> str:
    return json.dumps(
        {
            "error_code": exc.error_code,
            "safe_message": exc.safe_message,
            "path": exc.path,
            "details": exc.details,
        },
        indent=2,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = validate_closeout(args.repo_root.resolve())
    except DiagnosticCloseoutError as exc:
        print(_error_envelope(exc), file=sys.stderr)
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
