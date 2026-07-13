"""Validate and execute one authorized Groq cache telemetry calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal, TypeVar, cast

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.cache_telemetry_calibration_execution import (
    CalibrationAttemptRecord,
    CalibrationAttemptStatus,
    CalibrationExecutionAuthorization,
    CalibrationExecutionManifest,
    CalibrationExecutionReport,
    CalibrationExecutionRuntimePolicy,
    CalibrationExecutionStatus,
    CalibrationExecutionSummary,
    CalibrationRunRecordSet,
)
from auragateway.contracts.cache_telemetry_calibration_review import (
    CalibrationOutcome,
)
from auragateway.contracts.cache_telemetry_capture import (
    BillingCacheObservationState,
    GroqCacheTelemetryCapture,
)
from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderName,
)
from auragateway.contracts.telemetry import CachedInputDetailTelemetry
from auragateway.providers.base import (
    LiveProviderAdapter,
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderPrompt,
    ProviderCall,
)
from auragateway.providers.groq import GroqProviderAdapter

_DEFAULT_EXECUTION_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-v1")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class CalibrationExecutionError(Exception):
    """Expected metadata-safe execution failure."""

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


class CalibrationExecutionErrorEnvelope(BaseModel):
    """Metadata-safe CLI error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_ASSET_MISSING",
            "A required calibration execution asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_ASSET_MISSING",
            "A required calibration execution asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_INVALID_JSON",
            "A calibration execution asset is not valid JSON.",
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
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_VALIDATION_FAILED",
            "A calibration execution asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _validate_bindings(
    repo_root: Path,
    authorization: CalibrationExecutionAuthorization,
) -> None:
    for binding in authorization.bindings:
        observed = _sha256_file(repo_root / binding.path)
        if observed != binding.sha256:
            raise CalibrationExecutionError(
                "CACHE_CALIBRATION_EXECUTION_BINDING_MISMATCH",
                "A reviewed calibration asset no longer matches.",
                path=binding.path,
                details=(
                    f"expected={binding.sha256}",
                    f"observed={observed}",
                ),
            )


def _load_authorization(
    repo_root: Path,
    execution_root: Path,
) -> tuple[
    CalibrationExecutionAuthorization,
    CalibrationExecutionRuntimePolicy,
]:
    root = repo_root / execution_root
    authorization = _load_model(
        root / "authorization.json",
        CalibrationExecutionAuthorization,
    )
    runtime_policy = _load_model(
        root / "runtime_policy.json",
        CalibrationExecutionRuntimePolicy,
    )
    if runtime_policy.authorization_id != authorization.authorization_id:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_AUTHORIZATION_MISMATCH",
            "Authorization and runtime policy identify different executions.",
        )
    _validate_bindings(repo_root, authorization)
    return authorization, runtime_policy


def _evidence_paths(
    repo_root: Path,
    authorization: CalibrationExecutionAuthorization,
) -> tuple[Path, ...]:
    paths = authorization.evidence_paths
    return (
        repo_root / paths.journal_path,
        repo_root / paths.run_records_path,
        repo_root / paths.report_path,
        repo_root / paths.manifest_path,
        repo_root / paths.protected_outputs_path,
    )


def _assert_fresh_execution_boundary(
    repo_root: Path,
    authorization: CalibrationExecutionAuthorization,
) -> None:
    existing = tuple(
        str(path) for path in _evidence_paths(repo_root, authorization) if path.exists()
    )
    if existing:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_ALREADY_EXISTS",
            "Calibration evidence already exists; rerun and resume are forbidden.",
            details=existing,
        )


def _credential_available() -> bool:
    value = os.environ.get("GROQ_API_KEY")
    return value is not None and bool(value.strip())


def _load_protected_prompt(
    repo_root: Path,
    authorization: CalibrationExecutionAuthorization,
) -> tuple[str, str, str]:
    path = repo_root / authorization.evidence_paths.protected_prompt_bundle_path
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_PROMPT_SHAPE_INVALID",
            "The protected calibration prompt bundle must be a JSON object.",
            path=str(path),
        )
    system_prompt = payload.get("system_prompt")
    user_prompt = payload.get("user_prompt")
    provider_request = payload.get("provider_request")
    if (
        not isinstance(system_prompt, str)
        or not isinstance(user_prompt, str)
        or not isinstance(provider_request, Mapping)
    ):
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_PROMPT_SHAPE_INVALID",
            "The protected calibration prompt bundle is incomplete.",
            path=str(path),
        )
    request_hash = _sha256_bytes(_canonical_json_bytes(provider_request))
    expected_hash = next(
        binding.sha256 for binding in authorization.bindings if binding.protected_local
    )
    if _sha256_file(path) != expected_hash:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_PROMPT_HASH_MISMATCH",
            "The protected calibration prompt bundle no longer matches.",
            path=str(path),
        )
    return system_prompt, user_prompt, request_hash


def _append_jsonl(path: Path, payload: object) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            if isinstance(payload, BaseModel):
                handle.write(payload.model_dump_json() + "\n")
            else:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_EVIDENCE_WRITE_FAILED",
            "Calibration evidence could not be retained safely.",
            path=str(path),
        ) from exc


def _write_json(path: Path, payload: BaseModel) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            payload.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_EVIDENCE_WRITE_FAILED",
            "Calibration evidence could not be retained safely.",
            path=str(path),
        ) from exc


def _sleep_until(
    start_time: float,
    offset_seconds: int,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> None:
    remaining = start_time + offset_seconds - monotonic()
    if remaining > 0:
        sleep(remaining)


def _success_record(
    *,
    attempt_index: int,
    request_role: str,
    planned_offset_seconds: int,
    observed_offset_ms: int,
    request_hash: str,
    system_hash: str,
    user_hash: str,
    provider_call: ProviderCall,
) -> CalibrationAttemptRecord:
    telemetry = provider_call.telemetry
    output = provider_call.protected_output
    shape = provider_call.success_telemetry_shape
    if (
        output is None
        or not isinstance(shape, GroqCacheTelemetryCapture)
        or not isinstance(telemetry, CachedInputDetailTelemetry)
    ):
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_TELEMETRY_MISSING",
            "A successful provider call did not return required telemetry.",
        )
    return CalibrationAttemptRecord(
        attempt_index=attempt_index,
        request_role=cast(
            Literal[
                "cold",
                "warm_repeat_one",
                "warm_repeat_two",
            ],
            request_role,
        ),
        planned_offset_seconds=planned_offset_seconds,
        observed_offset_ms=observed_offset_ms,
        provider_request_sha256=request_hash,
        system_prompt_sha256=system_hash,
        user_prompt_sha256=user_hash,
        status=CalibrationAttemptStatus.SUCCEEDED,
        provider_call_made=True,
        output_sha256=output.sha256,
        output_byte_count=output.byte_count,
        input_tokens=telemetry.input_tokens,
        cached_input_tokens=telemetry.cached_input_tokens,
        output_tokens=telemetry.output_tokens,
        total_duration_ms=telemetry.total_duration_ms,
        installed_sdk_version=shape.installed_sdk_version,
        usage_present=shape.usage_present,
        prompt_tokens_details_present=(shape.prompt_tokens_details_present),
        billing_cached_tokens_field_present=(shape.billing_cached_tokens_field_present),
        billing_observation_state=shape.billing_observation_state,
        billing_cached_input_tokens=shape.billing_cached_input_tokens,
        x_groq_present=shape.x_groq_present,
        x_groq_usage_present=shape.x_groq_usage_present,
        dram_cached_tokens_field_present=(shape.dram_cached_tokens_field_present),
        dram_cached_tokens=shape.dram_cached_tokens,
        sram_cached_tokens_field_present=(shape.sram_cached_tokens_field_present),
        sram_cached_tokens=shape.sram_cached_tokens,
        estimated_cost_microusd=200,
    )


def _failed_record(
    *,
    attempt_index: int,
    request_role: str,
    planned_offset_seconds: int,
    observed_offset_ms: int,
    request_hash: str,
    system_hash: str,
    user_hash: str,
    error_code: ProviderErrorCode | None,
    telemetry_invalid: bool,
) -> CalibrationAttemptRecord:
    return CalibrationAttemptRecord(
        attempt_index=attempt_index,
        request_role=cast(
            Literal[
                "cold",
                "warm_repeat_one",
                "warm_repeat_two",
            ],
            request_role,
        ),
        planned_offset_seconds=planned_offset_seconds,
        observed_offset_ms=observed_offset_ms,
        provider_request_sha256=request_hash,
        system_prompt_sha256=system_hash,
        user_prompt_sha256=user_hash,
        status=(
            CalibrationAttemptStatus.TELEMETRY_INVALID
            if telemetry_invalid
            else CalibrationAttemptStatus.PROVIDER_ERROR
        ),
        provider_call_made=True,
        provider_error_code=error_code,
        estimated_cost_microusd=200,
    )


def _skipped_record(
    *,
    attempt_index: int,
    request_role: str,
    planned_offset_seconds: int,
    request_hash: str,
    system_hash: str,
    user_hash: str,
) -> CalibrationAttemptRecord:
    return CalibrationAttemptRecord(
        attempt_index=attempt_index,
        request_role=cast(
            Literal[
                "cold",
                "warm_repeat_one",
                "warm_repeat_two",
            ],
            request_role,
        ),
        planned_offset_seconds=planned_offset_seconds,
        provider_request_sha256=request_hash,
        system_prompt_sha256=system_hash,
        user_prompt_sha256=user_hash,
        status=CalibrationAttemptStatus.SKIPPED,
        provider_call_made=False,
        estimated_cost_microusd=0,
    )


def _classify_outcome(
    records: tuple[CalibrationAttemptRecord, ...],
) -> CalibrationOutcome:
    if any(record.status is not CalibrationAttemptStatus.SUCCEEDED for record in records):
        return CalibrationOutcome.CALIBRATION_EXECUTION_FAILED
    if any(
        record.billing_observation_state
        in {
            BillingCacheObservationState.FIELD_ABSENT,
            BillingCacheObservationState.FIELD_NULL,
        }
        for record in records
    ):
        return CalibrationOutcome.BILLING_CACHE_FIELD_UNAVAILABLE
    warm_records = records[1:]
    if any((record.billing_cached_input_tokens or 0) > 0 for record in warm_records):
        return CalibrationOutcome.TELEMETRY_OBSERVED_WITH_CACHE_HIT
    return CalibrationOutcome.TELEMETRY_OBSERVED_WITHOUT_CACHE_HIT


def _report(
    records: tuple[CalibrationAttemptRecord, ...],
) -> CalibrationExecutionReport:
    outcome = _classify_outcome(records)
    success_count = sum(item.status is CalibrationAttemptStatus.SUCCEEDED for item in records)
    provider_error_count = sum(
        item.status is CalibrationAttemptStatus.PROVIDER_ERROR for item in records
    )
    telemetry_invalid_count = sum(
        item.status is CalibrationAttemptStatus.TELEMETRY_INVALID for item in records
    )
    skipped_count = sum(item.status is CalibrationAttemptStatus.SKIPPED for item in records)
    numeric_count = sum(
        item.billing_observation_state
        in {
            BillingCacheObservationState.OBSERVED_ZERO,
            BillingCacheObservationState.OBSERVED_POSITIVE,
        }
        for item in records
    )
    warm_positive_count = sum((item.billing_cached_input_tokens or 0) > 0 for item in records[1:])
    provider_call_count = success_count + provider_error_count + telemetry_invalid_count
    return CalibrationExecutionReport(
        authorization_id="groq-cache-telemetry-calibration-auth-v1",
        calibration_id="groq-cache-telemetry-calibration-v1",
        status=(
            CalibrationExecutionStatus.COMPLETED
            if outcome is not CalibrationOutcome.CALIBRATION_EXECUTION_FAILED
            else CalibrationExecutionStatus.FAILED
        ),
        outcome=outcome,
        provider_call_count=provider_call_count,
        successful_call_count=success_count,
        provider_error_count=provider_error_count,
        telemetry_invalid_count=telemetry_invalid_count,
        skipped_attempt_count=skipped_count,
        billing_cache_numeric_sample_count=numeric_count,
        warm_positive_cache_sample_count=warm_positive_count,
        estimated_cost_microusd=provider_call_count * 200,
        live_provider_called=provider_call_count > 0,
        provider_cache_usage_claim_permitted_for_calibration=(
            outcome
            in {
                CalibrationOutcome.TELEMETRY_OBSERVED_WITH_CACHE_HIT,
                CalibrationOutcome.TELEMETRY_OBSERVED_WITHOUT_CACHE_HIT,
            }
        ),
    )


def validate_calibration_execution(
    repo_root: Path,
    *,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
) -> CalibrationExecutionSummary:
    """Validate active authorization without credential access."""

    authorization, _ = _load_authorization(repo_root, execution_root)
    _load_protected_prompt(repo_root, authorization)
    return CalibrationExecutionSummary(
        command="validate",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        provider_call_count=0,
        execution_completed=False,
        live_provider_called=False,
        credential_checked=False,
        provider_calls_permitted=False,
    )


def live_preflight_calibration_execution(
    repo_root: Path,
    *,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
) -> CalibrationExecutionSummary:
    """Check credential and one-time boundary without a provider call."""

    authorization, _ = _load_authorization(repo_root, execution_root)
    _load_protected_prompt(repo_root, authorization)
    _assert_fresh_execution_boundary(repo_root, authorization)
    if not _credential_available():
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_GROQ_API_KEY_MISSING",
            "GROQ_API_KEY is not available in the current process.",
        )
    return CalibrationExecutionSummary(
        command="live-preflight",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        provider_call_count=0,
        execution_completed=False,
        live_provider_called=False,
        credential_checked=True,
        provider_calls_permitted=True,
    )


def execute_calibration(
    repo_root: Path,
    *,
    authorization_id: str,
    confirmation: str,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
    adapter: LiveProviderAdapter | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> CalibrationExecutionSummary:
    """Execute the authorized calibration exactly once."""

    authorization, policy = _load_authorization(repo_root, execution_root)
    if authorization_id != authorization.authorization_id:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_AUTHORIZATION_ID_MISMATCH",
            "The requested authorization ID does not match.",
        )
    if confirmation != authorization.confirmation_phrase:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_CONFIRMATION_MISMATCH",
            "The exact one-time execution confirmation was not supplied.",
        )
    _assert_fresh_execution_boundary(repo_root, authorization)
    if not _credential_available() and adapter is None:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_GROQ_API_KEY_MISSING",
            "GROQ_API_KEY is not available in the current process.",
        )

    system_prompt, user_prompt, request_hash = _load_protected_prompt(
        repo_root,
        authorization,
    )
    expected_request_hash = next(
        item.sha256 for item in authorization.bindings if item.path.endswith("prompt_bundle.json")
    )
    if (
        _sha256_file(repo_root / authorization.evidence_paths.protected_prompt_bundle_path)
        != expected_request_hash
    ):
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_PROMPT_HASH_MISMATCH",
            "The protected prompt bundle differs from authorization.",
        )

    system_hash = _sha256_bytes(system_prompt.encode("utf-8"))
    user_hash = _sha256_bytes(user_prompt.encode("utf-8"))
    provider = adapter or GroqProviderAdapter()
    records: list[CalibrationAttemptRecord] = []
    start = monotonic()
    stopped = False

    journal_path = repo_root / authorization.evidence_paths.journal_path
    protected_output_path = repo_root / authorization.evidence_paths.protected_outputs_path

    for index, (role, offset) in enumerate(
        zip(
            policy.request_roles,
            policy.schedule_offsets_seconds,
            strict=True,
        )
    ):
        if stopped:
            record = _skipped_record(
                attempt_index=index,
                request_role=role,
                planned_offset_seconds=offset,
                request_hash=request_hash,
                system_hash=system_hash,
                user_hash=user_hash,
            )
            records.append(record)
            _append_jsonl(journal_path, record)
            continue

        _sleep_until(start, offset, monotonic, sleep)
        observed_offset_ms = round((monotonic() - start) * 1000)
        invocation = LiveProviderInvocation(
            request=ProviderInvocationRequest(
                request_id=f"cache-calibration-attempt-{index}",
                fixture_id="groq-cache-telemetry-calibration-v1",
                provider=ProviderName.GROQ,
                model_alias=authorization.model_alias,
                static_prefix_fingerprint=system_hash,
                input_token_count=2112,
                output_token_budget=authorization.maximum_completion_tokens,
            ),
            prompt=ProtectedProviderPrompt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            ),
            timeout_seconds=authorization.timeout_seconds,
        )
        try:
            call = provider.invoke(invocation)
            if call.protected_output is None:
                raise CalibrationExecutionError(
                    "CACHE_CALIBRATION_EXECUTION_OUTPUT_MISSING",
                    "A successful provider call returned no protected output.",
                )
            _append_jsonl(
                protected_output_path,
                {
                    "attempt_index": index,
                    "request_role": role,
                    "output_text": call.protected_output.text,
                },
            )
            record = _success_record(
                attempt_index=index,
                request_role=role,
                planned_offset_seconds=offset,
                observed_offset_ms=observed_offset_ms,
                request_hash=request_hash,
                system_hash=system_hash,
                user_hash=user_hash,
                provider_call=call,
            )
        except LiveProviderError as exc:
            record = _failed_record(
                attempt_index=index,
                request_role=role,
                planned_offset_seconds=offset,
                observed_offset_ms=observed_offset_ms,
                request_hash=request_hash,
                system_hash=system_hash,
                user_hash=user_hash,
                error_code=exc.error_code,
                telemetry_invalid=False,
            )
            stopped = True
        except CalibrationExecutionError:
            record = _failed_record(
                attempt_index=index,
                request_role=role,
                planned_offset_seconds=offset,
                observed_offset_ms=observed_offset_ms,
                request_hash=request_hash,
                system_hash=system_hash,
                user_hash=user_hash,
                error_code=ProviderErrorCode.INVALID_RESPONSE,
                telemetry_invalid=True,
            )
            stopped = True

        records.append(record)
        _append_jsonl(journal_path, record)

    record_set = CalibrationRunRecordSet(
        authorization_id=authorization.authorization_id,
        calibration_id=authorization.calibration_id,
        records=tuple(records),
    )
    report = _report(record_set.records)
    run_records_path = repo_root / authorization.evidence_paths.run_records_path
    report_path = repo_root / authorization.evidence_paths.report_path
    _write_json(run_records_path, record_set)
    _write_json(report_path, report)

    authorization_path = repo_root / authorization.evidence_paths.authorization_path
    runtime_policy_path = repo_root / authorization.evidence_paths.runtime_policy_path
    manifest = CalibrationExecutionManifest(
        authorization_id=authorization.authorization_id,
        authorization_sha256=_sha256_file(authorization_path),
        runtime_policy_sha256=_sha256_file(runtime_policy_path),
        journal_sha256=_sha256_file(journal_path),
        run_records_sha256=_sha256_file(run_records_path),
        report_sha256=_sha256_file(report_path),
        live_provider_called=report.live_provider_called,
    )
    _write_json(
        repo_root / authorization.evidence_paths.manifest_path,
        manifest,
    )

    return CalibrationExecutionSummary(
        command="run",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        provider_call_count=report.provider_call_count,
        execution_completed=True,
        live_provider_called=report.live_provider_called,
        credential_checked=adapter is None,
        provider_calls_permitted=True,
    )


def verify_calibration_execution(
    repo_root: Path,
    *,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
) -> CalibrationExecutionSummary:
    """Verify immutable public evidence after execution."""

    authorization, _ = _load_authorization(repo_root, execution_root)
    paths = authorization.evidence_paths
    record_set = _load_model(
        repo_root / paths.run_records_path,
        CalibrationRunRecordSet,
    )
    report = _load_model(
        repo_root / paths.report_path,
        CalibrationExecutionReport,
    )
    manifest = _load_model(
        repo_root / paths.manifest_path,
        CalibrationExecutionManifest,
    )
    journal_path = repo_root / paths.journal_path
    lines = [line for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 3:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_JOURNAL_COUNT_MISMATCH",
            "The public journal must contain exactly three records.",
            path=str(journal_path),
        )
    journal_records = tuple(CalibrationAttemptRecord.model_validate_json(line) for line in lines)
    if journal_records != record_set.records:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_JOURNAL_MISMATCH",
            "Journal and run records do not reconcile.",
        )

    checks = {
        "authorization_sha256": _sha256_file(repo_root / paths.authorization_path),
        "runtime_policy_sha256": _sha256_file(repo_root / paths.runtime_policy_path),
        "journal_sha256": _sha256_file(journal_path),
        "run_records_sha256": _sha256_file(repo_root / paths.run_records_path),
        "report_sha256": _sha256_file(repo_root / paths.report_path),
    }
    mismatches = tuple(
        f"{field}: expected={getattr(manifest, field)} observed={observed}"
        for field, observed in checks.items()
        if getattr(manifest, field) != observed
    )
    if mismatches:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_HASH_MISMATCH",
            "Calibration execution evidence no longer matches.",
            details=mismatches,
        )
    rebuilt_report = _report(record_set.records)
    if rebuilt_report != report:
        raise CalibrationExecutionError(
            "CACHE_CALIBRATION_EXECUTION_REPORT_MISMATCH",
            "The calibration report did not reproduce.",
        )

    return CalibrationExecutionSummary(
        command="verify",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        provider_call_count=report.provider_call_count,
        execution_completed=True,
        live_provider_called=report.live_provider_called,
        credential_checked=False,
        provider_calls_permitted=False,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("validate", "live-preflight", "run", "verify"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--execution-root",
        type=Path,
        default=_DEFAULT_EXECUTION_ROOT,
    )
    parser.add_argument("--authorization-id")
    parser.add_argument("--confirm")
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "validate":
            result = validate_calibration_execution(
                repo_root,
                execution_root=args.execution_root,
            )
        elif args.command == "live-preflight":
            result = live_preflight_calibration_execution(
                repo_root,
                execution_root=args.execution_root,
            )
        elif args.command == "run":
            result = execute_calibration(
                repo_root,
                authorization_id=args.authorization_id or "",
                confirmation=args.confirm or "",
                execution_root=args.execution_root,
            )
        else:
            result = verify_calibration_execution(
                repo_root,
                execution_root=args.execution_root,
            )
    except CalibrationExecutionError as exc:
        envelope = CalibrationExecutionErrorEnvelope(
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
