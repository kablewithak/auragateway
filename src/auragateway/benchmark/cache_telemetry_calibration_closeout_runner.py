"""Validate immutable Groq cache telemetry calibration closeout evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.cache_telemetry_calibration_closeout import (
    CacheTelemetryCalibrationCloseout,
    CacheTelemetryCalibrationCloseoutManifest,
    CacheTelemetryCalibrationCloseoutSummary,
)
from auragateway.contracts.cache_telemetry_calibration_execution import (
    CalibrationExecutionManifest,
    CalibrationExecutionReport,
    CalibrationRunRecordSet,
)
from auragateway.contracts.cache_telemetry_capture import (
    BillingCacheObservationState,
)

_DEFAULT_CLOSEOUT_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-closeout-v1")
_DEFAULT_EXECUTION_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-v1")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class CalibrationCloseoutError(Exception):
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


class CalibrationCloseoutErrorEnvelope(BaseModel):
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
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_ASSET_MISSING",
            "A required calibration closeout asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_ASSET_MISSING",
            "A required calibration closeout asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_INVALID_JSON",
            "A calibration closeout asset is not valid JSON.",
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
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_VALIDATION_FAILED",
            "A calibration closeout asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _validate_bound_assets(
    repo_root: Path,
    closeout: CacheTelemetryCalibrationCloseout,
) -> None:
    for binding in closeout.execution_bindings:
        observed = _sha256_file(repo_root / binding.path)
        if observed != binding.sha256:
            raise CalibrationCloseoutError(
                "CACHE_CALIBRATION_CLOSEOUT_BINDING_MISMATCH",
                "A bound execution asset no longer matches.",
                path=binding.path,
                details=(
                    f"expected={binding.sha256}",
                    f"observed={observed}",
                ),
            )


def _validate_execution(
    repo_root: Path,
    execution_root: Path,
) -> tuple[
    CalibrationExecutionReport,
    CalibrationRunRecordSet,
    CalibrationExecutionManifest,
]:
    report = _load_model(
        repo_root / execution_root / "report.json",
        CalibrationExecutionReport,
    )
    records = _load_model(
        repo_root / execution_root / "run_records.json",
        CalibrationRunRecordSet,
    )
    manifest = _load_model(
        repo_root / execution_root / "manifest.json",
        CalibrationExecutionManifest,
    )

    if report.outcome.value != "billing_cache_field_unavailable":
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_OUTCOME_MISMATCH",
            "Execution outcome does not match the frozen closeout.",
        )
    if (
        report.provider_call_count != 3
        or report.successful_call_count != 3
        or report.provider_error_count != 0
        or report.telemetry_invalid_count != 0
        or report.skipped_attempt_count != 0
    ):
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_EXECUTION_MISMATCH",
            "Execution counts do not match the frozen closeout.",
        )

    expected_offsets = (0, 10000, 20000)
    expected_durations = (98, 130, 113)
    for index, record in enumerate(records.records):
        if record.observed_offset_ms != expected_offsets[index]:
            raise CalibrationCloseoutError(
                "CACHE_CALIBRATION_CLOSEOUT_OFFSET_MISMATCH",
                "Observed calibration offsets no longer match.",
            )
        if record.total_duration_ms != expected_durations[index]:
            raise CalibrationCloseoutError(
                "CACHE_CALIBRATION_CLOSEOUT_DURATION_MISMATCH",
                "Observed calibration durations no longer match.",
            )
        if record.input_tokens != 1401 or record.output_tokens != 27:
            raise CalibrationCloseoutError(
                "CACHE_CALIBRATION_CLOSEOUT_TOKEN_MISMATCH",
                "Observed calibration tokens no longer match.",
            )
        if record.installed_sdk_version != "1.5.0":
            raise CalibrationCloseoutError(
                "CACHE_CALIBRATION_CLOSEOUT_SDK_MISMATCH",
                "Observed Groq SDK version no longer matches.",
            )
        if (
            record.usage_present is not True
            or record.prompt_tokens_details_present is not False
            or record.billing_cached_tokens_field_present is not False
            or record.billing_observation_state is not BillingCacheObservationState.FIELD_ABSENT
            or record.billing_cached_input_tokens is not None
        ):
            raise CalibrationCloseoutError(
                "CACHE_CALIBRATION_CLOSEOUT_BILLING_SIGNAL_MISMATCH",
                "Observed billing cache signal no longer matches.",
            )
        if (
            record.x_groq_present is not True
            or record.x_groq_usage_present is not False
            or record.dram_cached_tokens_field_present is not False
            or record.sram_cached_tokens_field_present is not False
            or record.dram_cached_tokens is not None
            or record.sram_cached_tokens is not None
        ):
            raise CalibrationCloseoutError(
                "CACHE_CALIBRATION_CLOSEOUT_HARDWARE_SIGNAL_MISMATCH",
                "Observed hardware cache signal no longer matches.",
            )

    if not manifest.live_provider_called or not manifest.execution_completed:
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_MANIFEST_MISMATCH",
            "Execution manifest does not record completed live execution.",
        )
    return report, records, manifest


def validate_calibration_closeout(
    repo_root: Path,
    *,
    closeout_root: Path = _DEFAULT_CLOSEOUT_ROOT,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
) -> CacheTelemetryCalibrationCloseoutSummary:
    """Validate closeout and immutable execution evidence."""

    root = repo_root / closeout_root
    closeout = _load_model(
        root / "closeout.json",
        CacheTelemetryCalibrationCloseout,
    )
    manifest = _load_model(
        root / "manifest.json",
        CacheTelemetryCalibrationCloseoutManifest,
    )

    _validate_bound_assets(repo_root, closeout)
    _, _, execution_manifest = _validate_execution(
        repo_root,
        execution_root,
    )

    closeout_path = root / "closeout.json"
    report_path = repo_root / manifest.report_path
    if _sha256_file(closeout_path) != manifest.closeout_sha256:
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_HASH_MISMATCH",
            "The closeout JSON no longer matches its manifest.",
            path=str(closeout_path),
        )
    if _sha256_file(report_path) != manifest.report_sha256:
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_HASH_MISMATCH",
            "The closeout report no longer matches its manifest.",
            path=str(report_path),
        )
    execution_manifest_path = repo_root / manifest.execution_manifest_path
    if _sha256_file(execution_manifest_path) != manifest.execution_manifest_sha256:
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_HASH_MISMATCH",
            "The execution manifest no longer matches the closeout.",
            path=str(execution_manifest_path),
        )
    if execution_manifest.report_sha256 != next(
        item.sha256 for item in closeout.execution_bindings if item.path.endswith("/report.json")
    ):
        raise CalibrationCloseoutError(
            "CACHE_CALIBRATION_CLOSEOUT_REPORT_BINDING_MISMATCH",
            "Execution and closeout report identities do not reconcile.",
        )

    return CacheTelemetryCalibrationCloseoutSummary(
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
        result = validate_calibration_closeout(
            args.repo_root.resolve(),
            closeout_root=args.closeout_root,
            execution_root=args.execution_root,
        )
    except CalibrationCloseoutError as exc:
        envelope = CalibrationCloseoutErrorEnvelope(
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
