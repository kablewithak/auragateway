"""Validate terminal Groq raw-wire cache telemetry closeout evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.groq_cache_telemetry_reauthorization import (
    GroqCacheTelemetryReauthorizationOutcome,
)
from auragateway.contracts.groq_cache_telemetry_reauthorization_closeout import (
    GroqCacheTelemetryReauthorizationCloseout,
    GroqCacheTelemetryReauthorizationCloseoutManifest,
    GroqCacheTelemetryReauthorizationCloseoutSummary,
)
from auragateway.contracts.groq_cache_telemetry_reauthorization_execution import (
    ReauthorizationAttemptStatus,
    ReauthorizationBillingObservationState,
    ReauthorizationExecutionManifest,
    ReauthorizationExecutionReport,
    ReauthorizationExecutionStatus,
    ReauthorizationRunRecordSet,
)

_DEFAULT_CLOSEOUT_ROOT = Path(
    "data/evals/benchmark/groq-cache-telemetry-reauthorization-closeout-v1"
)
_DEFAULT_EXECUTION_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-v1")
_EXPECTED_REQUEST_SHA256 = "23cac23a165812ae8e9908e9d0609fb533359a30ed4386d76bcfb82e6a9d17c9"
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class ReauthorizationCloseoutError(Exception):
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


class ReauthorizationCloseoutErrorEnvelope(BaseModel):
    """Metadata-safe CLI error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_ASSET_MISSING",
            "A required reauthorization closeout asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_ASSET_MISSING",
            "A required reauthorization closeout asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_INVALID_JSON",
            "A reauthorization closeout asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(
                include_url=False,
                include_input=False,
            )
        )
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_VALIDATION_FAILED",
            "A reauthorization closeout asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _binding_map(
    closeout: GroqCacheTelemetryReauthorizationCloseout,
) -> dict[str, str]:
    return {item.path: item.sha256 for item in closeout.execution_bindings}


def _validate_bound_assets(
    repo_root: Path,
    closeout: GroqCacheTelemetryReauthorizationCloseout,
) -> None:
    for binding in closeout.execution_bindings:
        observed = _sha256_file(repo_root / binding.path)
        if observed != binding.sha256:
            raise ReauthorizationCloseoutError(
                "GROQ_REAUTHORIZATION_CLOSEOUT_BINDING_MISMATCH",
                "A bound execution asset no longer matches.",
                path=binding.path,
                details=(
                    f"expected={binding.sha256}",
                    f"observed={observed}",
                ),
            )


def _validate_execution_report(report: ReauthorizationExecutionReport) -> None:
    if report.status is not ReauthorizationExecutionStatus.COMPLETED:
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_STATUS_MISMATCH",
            "Execution status does not match the terminal closeout.",
        )
    if report.outcome is not GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_ABSENT:
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_OUTCOME_MISMATCH",
            "Execution outcome does not match the terminal closeout.",
        )
    if (
        report.provider_call_count != 2
        or report.successful_call_count != 2
        or report.provider_error_count != 0
        or report.observation_invalid_count != 0
        or report.skipped_attempt_count != 0
        or report.raw_numeric_sample_count != 0
        or report.parsed_numeric_sample_count != 0
        or report.raw_absent_sample_count != 2
        or report.estimated_cost_microusd != 400
    ):
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_EXECUTION_MISMATCH",
            "Execution counts do not match the terminal closeout.",
        )
    if (
        not report.live_provider_called
        or not report.execution_completed
        or not report.authorization_consumed
        or report.rerun_permitted
        or report.resume_permitted
        or not report.exact_provider_wire_omission_claim_permitted
        or report.sdk_live_parse_defect_claim_permitted
        or report.provider_cache_usage_claim_permitted_for_execution
        or report.provider_cache_savings_claim_permitted
        or report.benchmark_execution_permitted
        or report.benchmark_claims_permitted
        or report.comparison_eligible
    ):
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_CLAIM_STATE_MISMATCH",
            "Execution claim state does not match the terminal closeout.",
        )


def _validate_run_records(records: ReauthorizationRunRecordSet) -> None:
    expected_roles = ("cold_wire_probe", "warm_wire_probe")
    expected_offsets_seconds = (0, 10)
    expected_offsets_ms = (0, 10000)

    for index, record in enumerate(records.records):
        if record.attempt_index != index:
            raise ReauthorizationCloseoutError(
                "GROQ_REAUTHORIZATION_CLOSEOUT_ATTEMPT_INDEX_MISMATCH",
                "Execution attempt indexes no longer match.",
            )
        if (
            record.request_role != expected_roles[index]
            or record.planned_offset_seconds != expected_offsets_seconds[index]
            or record.observed_offset_ms != expected_offsets_ms[index]
        ):
            raise ReauthorizationCloseoutError(
                "GROQ_REAUTHORIZATION_CLOSEOUT_SCHEDULE_MISMATCH",
                "Execution schedule no longer matches the closed trajectory.",
            )
        if (
            record.provider_request_sha256 != _EXPECTED_REQUEST_SHA256
            or record.status is not ReauthorizationAttemptStatus.SUCCEEDED
            or not record.provider_call_made
            or record.provider_error_code is not None
            or record.http_status_code != 200
            or record.raw_body_sha256 is None
            or record.raw_body_byte_count is None
            or record.parsed_response_sha256 is None
            or record.parsed_response_byte_count is None
            or record.installed_sdk_version != "1.5.0"
            or record.estimated_cost_microusd != 200
        ):
            raise ReauthorizationCloseoutError(
                "GROQ_REAUTHORIZATION_CLOSEOUT_ATTEMPT_MISMATCH",
                "A successful execution attempt no longer matches.",
            )
        if (
            record.raw_billing_observation_state
            is not ReauthorizationBillingObservationState.FIELD_ABSENT
            or record.raw_billing_field_present is not False
            or record.raw_billing_cached_tokens is not None
            or record.parsed_billing_observation_state
            is not ReauthorizationBillingObservationState.FIELD_ABSENT
            or record.parsed_billing_field_present is not False
            or record.parsed_billing_cached_tokens is not None
            or record.raw_parsed_numeric_values_match is not None
        ):
            raise ReauthorizationCloseoutError(
                "GROQ_REAUTHORIZATION_CLOSEOUT_TELEMETRY_MISMATCH",
                "Raw and parsed cache telemetry no longer match the closeout.",
            )


def _validate_execution_manifest(
    closeout: GroqCacheTelemetryReauthorizationCloseout,
    manifest: ReauthorizationExecutionManifest,
) -> None:
    bindings = _binding_map(closeout)
    expected = {
        "authorization_sha256": bindings[
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/authorization.json"
        ],
        "runtime_policy_sha256": bindings[
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/runtime_policy.json"
        ],
        "activation_manifest_sha256": bindings[
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/activation_manifest.json"
        ],
        "journal_sha256": bindings[
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/journal.jsonl"
        ],
        "run_records_sha256": bindings[
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/run_records.json"
        ],
        "report_sha256": bindings[
            "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/report.json"
        ],
        "protected_raw_responses_sha256": (closeout.protected_evidence.raw_responses_sha256),
        "protected_parsed_responses_sha256": (closeout.protected_evidence.parsed_responses_sha256),
    }
    for field, expected_value in expected.items():
        if getattr(manifest, field) != expected_value:
            raise ReauthorizationCloseoutError(
                "GROQ_REAUTHORIZATION_CLOSEOUT_MANIFEST_MISMATCH",
                "Execution manifest does not reconcile with the closeout.",
                details=(f"field={field}",),
            )
    if not manifest.live_provider_called or not manifest.execution_completed:
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_MANIFEST_MISMATCH",
            "Execution manifest does not record completed live execution.",
        )


def _validate_execution(
    repo_root: Path,
    execution_root: Path,
    closeout: GroqCacheTelemetryReauthorizationCloseout,
) -> tuple[
    ReauthorizationExecutionReport,
    ReauthorizationRunRecordSet,
    ReauthorizationExecutionManifest,
]:
    report = _load_model(
        repo_root / execution_root / "report.json",
        ReauthorizationExecutionReport,
    )
    records = _load_model(
        repo_root / execution_root / "run_records.json",
        ReauthorizationRunRecordSet,
    )
    manifest = _load_model(
        repo_root / execution_root / "manifest.json",
        ReauthorizationExecutionManifest,
    )

    _validate_execution_report(report)
    _validate_run_records(records)
    _validate_execution_manifest(closeout, manifest)
    return report, records, manifest


def validate_reauthorization_closeout(
    repo_root: Path,
    *,
    closeout_root: Path = _DEFAULT_CLOSEOUT_ROOT,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
) -> GroqCacheTelemetryReauthorizationCloseoutSummary:
    """Validate terminal closeout and immutable execution evidence."""

    root = repo_root / closeout_root
    closeout = _load_model(
        root / "closeout.json",
        GroqCacheTelemetryReauthorizationCloseout,
    )
    closeout_manifest = _load_model(
        root / "manifest.json",
        GroqCacheTelemetryReauthorizationCloseoutManifest,
    )

    _validate_bound_assets(repo_root, closeout)
    _, _, execution_manifest = _validate_execution(
        repo_root,
        execution_root,
        closeout,
    )

    closeout_path = root / "closeout.json"
    report_path = repo_root / closeout_manifest.report_path
    execution_report_path = repo_root / closeout_manifest.execution_report_path
    execution_manifest_path = repo_root / closeout_manifest.execution_manifest_path

    hash_checks = (
        (
            closeout_path,
            closeout_manifest.closeout_sha256,
            "closeout JSON",
        ),
        (
            report_path,
            closeout_manifest.report_sha256,
            "closeout report",
        ),
        (
            execution_report_path,
            closeout_manifest.execution_report_sha256,
            "execution report",
        ),
        (
            execution_manifest_path,
            closeout_manifest.execution_manifest_sha256,
            "execution manifest",
        ),
    )
    for path, expected_hash, label in hash_checks:
        observed_hash = _sha256_file(path)
        if observed_hash != expected_hash:
            raise ReauthorizationCloseoutError(
                "GROQ_REAUTHORIZATION_CLOSEOUT_HASH_MISMATCH",
                f"The {label} no longer matches its manifest.",
                path=str(path),
                details=(
                    f"expected={expected_hash}",
                    f"observed={observed_hash}",
                ),
            )

    if (
        closeout_manifest.source_commit != closeout.source_commit
        or closeout_manifest.next_gate is not closeout.next_gate
    ):
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_LINEAGE_MISMATCH",
            "Closeout manifest lineage does not match the closeout.",
        )
    if execution_manifest.report_sha256 != closeout_manifest.execution_report_sha256:
        raise ReauthorizationCloseoutError(
            "GROQ_REAUTHORIZATION_CLOSEOUT_REPORT_BINDING_MISMATCH",
            "Execution and closeout report identities do not reconcile.",
        )

    return GroqCacheTelemetryReauthorizationCloseoutSummary(
        closeout_id=closeout.closeout_id,
        status=closeout.status,
        next_gate=closeout.next_gate,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--closeout-root",
        type=Path,
        default=_DEFAULT_CLOSEOUT_ROOT,
    )
    parser.add_argument(
        "--execution-root",
        type=Path,
        default=_DEFAULT_EXECUTION_ROOT,
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = validate_reauthorization_closeout(
            args.repo_root.resolve(),
            closeout_root=args.closeout_root,
            execution_root=args.execution_root,
        )
    except ReauthorizationCloseoutError as exc:
        envelope = ReauthorizationCloseoutErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
