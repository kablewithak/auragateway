"""Validate, preflight, execute once, and verify the diagnostic experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.benchmark.diagnostic_authorization_review_runner import (
    DiagnosticAuthorizationReviewError,
    validate_authorization_review,
)
from auragateway.benchmark.diagnostic_fixture_runner import (
    DiagnosticFixtureError,
    verify_diagnostic_fixtures,
)
from auragateway.contracts.diagnostic_authorization_review import (
    DiagnosticDryRunAttempt,
    DiagnosticDryRunReport,
)
from auragateway.contracts.diagnostic_execution import (
    DiagnosticExecutionAttemptRecord,
    DiagnosticExecutionAttemptStatus,
    DiagnosticExecutionAuthorization,
    DiagnosticExecutionManifest,
    DiagnosticExecutionRecordSet,
    DiagnosticExecutionReport,
    DiagnosticExecutionRuntimePolicy,
    DiagnosticExecutionSummary,
    DiagnosticSequenceRecord,
    DiagnosticSequenceStatus,
)
from auragateway.contracts.diagnostic_fixtures import (
    DiagnosticFixtureManifest,
    ProtectedDiagnosticPromptBundle,
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
)
from auragateway.providers.groq import (
    GROQ_ADAPTER_VERSION,
    GROQ_MODEL_ALIAS,
    GROQ_MODEL_ID,
    GroqProviderAdapter,
)

_ASSET_ROOT = Path("data/evals/benchmark/diagnostic-execution-v1")
_AUTHORIZATION_PATH = _ASSET_ROOT / "authorization.json"
_RUNTIME_POLICY_PATH = _ASSET_ROOT / "runtime_policy.json"
_REVIEW_ROOT = Path("data/evals/benchmark/diagnostic-authorization-review-v1")
_DRY_RUN_PATH = _REVIEW_ROOT / "dry_run_report.json"
_REVIEW_MANIFEST_PATH = _REVIEW_ROOT / "manifest.json"
_FIXTURE_MANIFEST_PATH = Path("data/evals/benchmark/diagnostic-fixtures-v1/fixture_manifest.json")
_PROTECTED_PROMPT_BUNDLE_PATH = Path(".local/benchmark/diagnostic-fixtures-v1/prompt_cohorts.json")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class DiagnosticExecutionError(Exception):
    """Expected metadata-safe diagnostic execution failure."""

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


class DiagnosticExecutionErrorEnvelope(BaseModel):
    """Metadata-safe CLI error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _model_json_bytes(model: BaseModel) -> bytes:
    return _canonical_json_bytes(model.model_dump(mode="json"))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_REQUIRED_ASSET_MISSING",
            "A required diagnostic execution asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_REQUIRED_ASSET_MISSING",
            "A required diagnostic execution asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_INVALID_JSON",
            "A diagnostic execution asset is not valid JSON.",
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
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_ASSET_VALIDATION_FAILED",
            "A diagnostic execution asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_model_json_bytes(model))


def _append_json_line(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(_canonical_json_bytes(payload))
        handle.write(b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def _binding_map(
    authorization: DiagnosticExecutionAuthorization,
) -> dict[str, str]:
    return {item.path: item.sha256 for item in authorization.bindings}


def _evidence_paths(
    repo_root: Path,
    authorization: DiagnosticExecutionAuthorization,
) -> tuple[Path, Path, Path, Path, Path, Path]:
    policy = authorization.evidence_paths
    return (
        repo_root / policy.journal_path,
        repo_root / policy.run_records_path,
        repo_root / policy.report_path,
        repo_root / policy.manifest_path,
        repo_root / policy.protected_raw_outputs_path,
        repo_root / policy.protected_failure_diagnostics_path,
    )


def _assert_provider_profile(
    authorization: DiagnosticExecutionAuthorization,
) -> None:
    observed = (
        authorization.provider_model_alias,
        authorization.exact_model_identifier,
        authorization.adapter_version,
    )
    expected = (
        GROQ_MODEL_ALIAS,
        GROQ_MODEL_ID,
        GROQ_ADAPTER_VERSION,
    )
    if observed != expected:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_PROVIDER_PROFILE_MISMATCH",
            "The active authorization does not match the installed Groq adapter.",
        )


def _assert_bindings(
    repo_root: Path,
    authorization: DiagnosticExecutionAuthorization,
) -> None:
    for binding in authorization.bindings:
        path = repo_root / binding.path
        observed = _sha256_file(path)
        if observed != binding.sha256:
            raise DiagnosticExecutionError(
                "DIAGNOSTIC_EXECUTION_BINDING_MISMATCH",
                "A frozen active-authorization dependency no longer matches.",
                path=str(path),
                details=(
                    f"expected={binding.sha256}",
                    f"observed={observed}",
                ),
            )


def _load_authorized_assets(
    repo_root: Path,
) -> tuple[
    DiagnosticExecutionAuthorization,
    DiagnosticExecutionRuntimePolicy,
    DiagnosticDryRunReport,
    DiagnosticFixtureManifest,
    ProtectedDiagnosticPromptBundle,
]:
    validate_authorization_review(repo_root)
    fixture_summary = verify_diagnostic_fixtures(repo_root)
    if fixture_summary.provider_calls_permitted:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_FIXTURE_STATE_INVALID",
            "Fixture verification unexpectedly permits provider calls.",
        )

    authorization = _load_model(
        repo_root / _AUTHORIZATION_PATH,
        DiagnosticExecutionAuthorization,
    )
    runtime_policy = _load_model(
        repo_root / _RUNTIME_POLICY_PATH,
        DiagnosticExecutionRuntimePolicy,
    )
    dry_run = _load_model(
        repo_root / _DRY_RUN_PATH,
        DiagnosticDryRunReport,
    )
    fixture_manifest = _load_model(
        repo_root / _FIXTURE_MANIFEST_PATH,
        DiagnosticFixtureManifest,
    )
    protected_bundle = _load_model(
        repo_root / _PROTECTED_PROMPT_BUNDLE_PATH,
        ProtectedDiagnosticPromptBundle,
    )

    if runtime_policy.authorization_id != authorization.authorization_id:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_POLICY_AUTHORIZATION_MISMATCH",
            "The runtime policy is bound to a different authorization.",
        )
    if dry_run.review_id != authorization.review_id:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_REVIEW_ID_MISMATCH",
            "The active authorization targets a different review package.",
        )
    if fixture_manifest.fixture_id != authorization.fixture_id:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_FIXTURE_ID_MISMATCH",
            "The active authorization targets a different fixture set.",
        )
    if protected_bundle.fixture_id != authorization.fixture_id:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_PROTECTED_FIXTURE_ID_MISMATCH",
            "The protected prompt bundle targets a different fixture set.",
        )

    _assert_provider_profile(authorization)
    _assert_bindings(repo_root, authorization)

    bindings = _binding_map(authorization)
    expected_direct = {
        _REVIEW_MANIFEST_PATH.as_posix(): _sha256_file(repo_root / _REVIEW_MANIFEST_PATH),
        _DRY_RUN_PATH.as_posix(): _sha256_file(repo_root / _DRY_RUN_PATH),
        _FIXTURE_MANIFEST_PATH.as_posix(): _sha256_file(repo_root / _FIXTURE_MANIFEST_PATH),
        _PROTECTED_PROMPT_BUNDLE_PATH.as_posix(): _sha256_file(
            repo_root / _PROTECTED_PROMPT_BUNDLE_PATH
        ),
    }
    if any(bindings[path] != digest for path, digest in expected_direct.items()):
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_DIRECT_BINDING_MISMATCH",
            "An active authorization binding differs from the validated bytes.",
        )

    observed_offsets = tuple(item.planned_offset_seconds for item in dry_run.attempts)
    if observed_offsets != runtime_policy.schedule_offsets_seconds:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_SCHEDULE_MISMATCH",
            "The runtime policy schedule differs from the reviewed dry run.",
        )
    return (
        authorization,
        runtime_policy,
        dry_run,
        fixture_manifest,
        protected_bundle,
    )


def _assert_fresh_evidence_boundary(
    repo_root: Path,
    authorization: DiagnosticExecutionAuthorization,
) -> None:
    evidence_paths = _evidence_paths(repo_root, authorization)
    existing = tuple(
        str(path)
        for path in evidence_paths
        if path.exists() and (not path.is_file() or path.stat().st_size > 0)
    )
    if existing:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_EVIDENCE_ALREADY_EXISTS",
            "One-time diagnostic execution requires a completely fresh evidence boundary.",
            details=existing,
        )


def _probe_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    probe = path.with_name(f".{path.name}.preflight")
    if probe.exists():
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_STALE_PREFLIGHT_PROBE",
            "A stale diagnostic execution preflight probe requires investigation.",
            path=str(probe),
        )
    try:
        with probe.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write('{"probe":"diagnostic-execution-sink"}\n')
            handle.flush()
            os.fsync(handle.fileno())
        probe.unlink()
    except OSError as exc:
        with suppress(OSError):
            probe.unlink(missing_ok=True)
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_SINK_UNAVAILABLE",
            "A diagnostic execution evidence sink is not safely writable.",
            path=str(path),
        ) from exc


def _assert_sinks_writable(
    repo_root: Path,
    authorization: DiagnosticExecutionAuthorization,
) -> None:
    for path in _evidence_paths(repo_root, authorization):
        _probe_parent(path)


def _summary(
    command: str,
    authorization: DiagnosticExecutionAuthorization,
    records: DiagnosticExecutionRecordSet | None = None,
    *,
    credential_checked: bool,
) -> DiagnosticExecutionSummary:
    return DiagnosticExecutionSummary.model_validate(
        {
            "command": command,
            "authorization_id": authorization.authorization_id,
            "authorization_status": authorization.status,
            "provider_call_count": (records.provider_call_count if records is not None else 0),
            "execution_completed": records is not None,
            "live_provider_called": (
                records.live_provider_called if records is not None else False
            ),
            "credential_checked": credential_checked,
            "provider_calls_permitted": command == "run",
        }
    )


def validate_activation(repo_root: Path) -> DiagnosticExecutionSummary:
    """Validate active authorization without credential access or provider calls."""

    authorization, _, _, _, _ = _load_authorized_assets(repo_root)
    _assert_fresh_evidence_boundary(repo_root, authorization)
    return _summary(
        "validate",
        authorization,
        credential_checked=False,
    )


def live_preflight(repo_root: Path) -> DiagnosticExecutionSummary:
    """Check credential presence and writable sinks without creating provider traffic."""

    authorization, _, _, _, _ = _load_authorized_assets(repo_root)
    _assert_fresh_evidence_boundary(repo_root, authorization)
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key is None or not api_key.strip():
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_GROQ_API_KEY_MISSING",
            "GROQ_API_KEY must be loaded deliberately before live execution.",
        )
    _assert_sinks_writable(repo_root, authorization)
    return _summary(
        "live-preflight",
        authorization,
        credential_checked=True,
    )


def _logical_request_hash(
    authorization: DiagnosticExecutionAuthorization,
    system_prompt: str,
    user_prompt: str,
) -> str:
    payload = {
        "max_completion_tokens": authorization.maximum_completion_tokens,
        "messages": [
            {"content": system_prompt, "role": "system"},
            {"content": user_prompt, "role": "user"},
        ],
        "model": authorization.provider_model_alias,
        "reasoning_effort": "low",
        "store": False,
        "stream": False,
        "temperature": 0.0,
    }
    return _sha256_bytes(_canonical_json_bytes(payload))


def _cohort_prompts(
    bundle: ProtectedDiagnosticPromptBundle,
    attempt: DiagnosticDryRunAttempt,
) -> tuple[str, str]:
    cohort = next(
        (item for item in bundle.cohorts if item.cohort_id == attempt.cohort_id),
        None,
    )
    if cohort is None:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_COHORT_MISSING",
            "A reviewed prompt cohort is missing from protected storage.",
            details=(attempt.cohort_id,),
        )
    return (
        cohort.system_prompt,
        cohort.user_prompts_by_turn[attempt.turn_index - 1],
    )


def _provider_invocation(
    authorization: DiagnosticExecutionAuthorization,
    attempt: DiagnosticDryRunAttempt,
    bundle: ProtectedDiagnosticPromptBundle,
) -> LiveProviderInvocation:
    system_prompt, user_prompt = _cohort_prompts(bundle, attempt)
    system_sha256 = _sha256_bytes(system_prompt.encode("utf-8"))
    user_sha256 = _sha256_bytes(user_prompt.encode("utf-8"))
    logical_request_sha256 = _logical_request_hash(
        authorization,
        system_prompt,
        user_prompt,
    )
    observed = (
        system_sha256,
        user_sha256,
        logical_request_sha256,
        len(system_prompt.encode("utf-8")) + len(user_prompt.encode("utf-8")),
    )
    expected = (
        attempt.system_prompt_sha256,
        attempt.user_prompt_sha256,
        attempt.provider_request_sha256,
        attempt.prompt_byte_count,
    )
    if observed != expected:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_REQUEST_SHAPE_MISMATCH",
            "A protected prompt no longer reproduces the reviewed provider request.",
            details=(attempt.sequence_id, str(attempt.turn_index)),
        )

    request_id = f"diag-{attempt.attempt_index:02d}-{attempt.sequence_id}-t{attempt.turn_index}"
    request = ProviderInvocationRequest(
        request_id=request_id,
        fixture_id=authorization.fixture_id,
        provider=ProviderName.GROQ,
        model_alias=authorization.provider_model_alias,
        static_prefix_fingerprint=attempt.system_prompt_sha256,
        input_token_count=attempt.input_token_estimate,
        output_token_budget=authorization.maximum_completion_tokens,
    )
    return LiveProviderInvocation(
        request=request,
        prompt=ProtectedProviderPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ),
        timeout_seconds=float(authorization.timeout_seconds),
    )


def _success_record(
    attempt: DiagnosticDryRunAttempt,
    observed_offset_ms: int,
    call: object,
    *,
    estimated_cost_microusd: int,
) -> DiagnosticExecutionAttemptRecord:
    from auragateway.providers.base import ProviderCall

    if not isinstance(call, ProviderCall):
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_PROVIDER_CALL_TYPE_INVALID",
            "The provider adapter returned an unsupported call envelope.",
        )
    if call.protected_output is None:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_PROTECTED_OUTPUT_MISSING",
            "A successful provider call did not retain protected output.",
        )
    telemetry = call.telemetry
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    total_duration_ms: int | None = None
    if isinstance(telemetry, CachedInputDetailTelemetry):
        input_tokens = telemetry.input_tokens
        cached_input_tokens = telemetry.cached_input_tokens
        output_tokens = telemetry.output_tokens
        total_duration_ms = telemetry.total_duration_ms

    return DiagnosticExecutionAttemptRecord(
        attempt_index=attempt.attempt_index,
        sequence_id=attempt.sequence_id,
        sequence_schedule_index=attempt.sequence_schedule_index,
        stage=attempt.stage,
        cohort_id=attempt.cohort_id,
        condition_label=attempt.condition_label,
        turn_index=attempt.turn_index,
        planned_offset_seconds=attempt.planned_offset_seconds,
        observed_offset_ms=observed_offset_ms,
        system_prompt_sha256=attempt.system_prompt_sha256,
        user_prompt_sha256=attempt.user_prompt_sha256,
        provider_request_sha256=attempt.provider_request_sha256,
        prompt_byte_count=attempt.prompt_byte_count,
        input_token_estimate=attempt.input_token_estimate,
        status=DiagnosticExecutionAttemptStatus.SUCCEEDED,
        provider_call_made=True,
        output_sha256=call.protected_output.sha256,
        output_byte_count=call.protected_output.byte_count,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        total_duration_ms=total_duration_ms,
        estimated_cost_microusd=estimated_cost_microusd,
    )


def _provider_error_record(
    attempt: DiagnosticDryRunAttempt,
    observed_offset_ms: int,
    error: LiveProviderError,
    *,
    estimated_cost_microusd: int,
) -> DiagnosticExecutionAttemptRecord:
    return DiagnosticExecutionAttemptRecord(
        attempt_index=attempt.attempt_index,
        sequence_id=attempt.sequence_id,
        sequence_schedule_index=attempt.sequence_schedule_index,
        stage=attempt.stage,
        cohort_id=attempt.cohort_id,
        condition_label=attempt.condition_label,
        turn_index=attempt.turn_index,
        planned_offset_seconds=attempt.planned_offset_seconds,
        observed_offset_ms=observed_offset_ms,
        system_prompt_sha256=attempt.system_prompt_sha256,
        user_prompt_sha256=attempt.user_prompt_sha256,
        provider_request_sha256=attempt.provider_request_sha256,
        prompt_byte_count=attempt.prompt_byte_count,
        input_token_estimate=attempt.input_token_estimate,
        status=DiagnosticExecutionAttemptStatus.PROVIDER_ERROR,
        provider_call_made=True,
        provider_error_code=error.error_code,
        estimated_cost_microusd=estimated_cost_microusd,
    )


def _skipped_record(
    attempt: DiagnosticDryRunAttempt,
    status: DiagnosticExecutionAttemptStatus,
) -> DiagnosticExecutionAttemptRecord:
    return DiagnosticExecutionAttemptRecord(
        attempt_index=attempt.attempt_index,
        sequence_id=attempt.sequence_id,
        sequence_schedule_index=attempt.sequence_schedule_index,
        stage=attempt.stage,
        cohort_id=attempt.cohort_id,
        condition_label=attempt.condition_label,
        turn_index=attempt.turn_index,
        planned_offset_seconds=attempt.planned_offset_seconds,
        system_prompt_sha256=attempt.system_prompt_sha256,
        user_prompt_sha256=attempt.user_prompt_sha256,
        provider_request_sha256=attempt.provider_request_sha256,
        prompt_byte_count=attempt.prompt_byte_count,
        input_token_estimate=attempt.input_token_estimate,
        status=status,
        provider_call_made=False,
        estimated_cost_microusd=0,
    )


def _append_protected_output(
    path: Path,
    attempt: DiagnosticDryRunAttempt,
    invocation: LiveProviderInvocation,
    call: object,
) -> None:
    from auragateway.providers.base import ProviderCall

    if not isinstance(call, ProviderCall) or call.protected_output is None:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_PROTECTED_OUTPUT_MISSING",
            "A successful provider call did not retain protected output.",
        )
    _append_json_line(
        path,
        {
            "attempt_index": attempt.attempt_index,
            "request_id": invocation.request.request_id,
            "output_sha256": call.protected_output.sha256,
            "output_byte_count": call.protected_output.byte_count,
            "output_text": call.protected_output.text,
        },
    )


def _sequence_record(
    sequence_id: str,
    attempts: tuple[DiagnosticExecutionAttemptRecord, ...],
) -> DiagnosticSequenceRecord:
    successes = sum(item.status is DiagnosticExecutionAttemptStatus.SUCCEEDED for item in attempts)
    errors = [
        item for item in attempts if item.status is DiagnosticExecutionAttemptStatus.PROVIDER_ERROR
    ]
    skipped = sum(
        item.status
        in {
            DiagnosticExecutionAttemptStatus.SKIPPED_SEQUENCE,
            DiagnosticExecutionAttemptStatus.SKIPPED_EXPERIMENT,
        }
        for item in attempts
    )
    provider_calls = successes + len(errors)
    terminal_error = errors[0].provider_error_code if errors else None

    if successes == 3:
        status = DiagnosticSequenceStatus.COMPLETED
    elif terminal_error is ProviderErrorCode.REQUEST_REJECTED:
        status = DiagnosticSequenceStatus.REQUEST_REJECTED
    elif provider_calls > 0:
        status = DiagnosticSequenceStatus.EXPERIMENT_STOPPED
    else:
        status = DiagnosticSequenceStatus.NOT_STARTED

    return DiagnosticSequenceRecord(
        sequence_id=sequence_id,
        status=status,
        provider_call_count=provider_calls,
        successful_call_count=successes,
        provider_error_count=len(errors),
        skipped_attempt_count=skipped,
        terminal_error_code=terminal_error,
    )


def _record_set(
    authorization: DiagnosticExecutionAuthorization,
    attempts: list[DiagnosticExecutionAttemptRecord],
    sequences: list[DiagnosticSequenceRecord],
) -> DiagnosticExecutionRecordSet:
    provider_calls = sum(item.provider_call_made for item in attempts)
    successes = sum(item.status is DiagnosticExecutionAttemptStatus.SUCCEEDED for item in attempts)
    errors = sum(
        item.status is DiagnosticExecutionAttemptStatus.PROVIDER_ERROR for item in attempts
    )
    sequence_skips = sum(
        item.status is DiagnosticExecutionAttemptStatus.SKIPPED_SEQUENCE for item in attempts
    )
    experiment_skips = sum(
        item.status is DiagnosticExecutionAttemptStatus.SKIPPED_EXPERIMENT for item in attempts
    )
    return DiagnosticExecutionRecordSet(
        authorization_id=authorization.authorization_id,
        attempts=tuple(attempts),
        sequences=tuple(sequences),
        provider_call_count=provider_calls,
        successful_call_count=successes,
        provider_error_count=errors,
        skipped_sequence_attempt_count=sequence_skips,
        skipped_experiment_attempt_count=experiment_skips,
        estimated_cost_microusd=sum(item.estimated_cost_microusd for item in attempts),
        live_provider_called=provider_calls > 0,
    )


def _report(
    records: DiagnosticExecutionRecordSet,
    protected_output_path: Path,
) -> DiagnosticExecutionReport:
    statuses = [item.status for item in records.sequences]
    skipped = records.skipped_sequence_attempt_count + records.skipped_experiment_attempt_count
    protected_outputs_retained = (
        records.successful_call_count == 0 or protected_output_path.is_file()
    )
    return DiagnosticExecutionReport(
        authorization_id=records.authorization_id,
        provider_call_count=records.provider_call_count,
        completed_sequence_count=statuses.count(DiagnosticSequenceStatus.COMPLETED),
        request_rejected_sequence_count=statuses.count(DiagnosticSequenceStatus.REQUEST_REJECTED),
        experiment_stopped_sequence_count=statuses.count(
            DiagnosticSequenceStatus.EXPERIMENT_STOPPED
        ),
        not_started_sequence_count=statuses.count(DiagnosticSequenceStatus.NOT_STARTED),
        successful_call_count=records.successful_call_count,
        provider_error_count=records.provider_error_count,
        skipped_attempt_count=skipped,
        estimated_cost_microusd=records.estimated_cost_microusd,
        protected_outputs_retained_locally=protected_outputs_retained,
        live_provider_called=records.live_provider_called,
    )


def _manifest(
    repo_root: Path,
    authorization: DiagnosticExecutionAuthorization,
    records: DiagnosticExecutionRecordSet,
    report: DiagnosticExecutionReport,
) -> DiagnosticExecutionManifest:
    paths = authorization.evidence_paths
    return DiagnosticExecutionManifest(
        authorization_id=authorization.authorization_id,
        authorization_sha256=_sha256_file(repo_root / paths.authorization_path),
        runtime_policy_sha256=_sha256_file(repo_root / paths.runtime_policy_path),
        review_manifest_sha256=_sha256_file(repo_root / _REVIEW_MANIFEST_PATH),
        dry_run_report_sha256=_sha256_file(repo_root / _DRY_RUN_PATH),
        journal_sha256=_sha256_file(repo_root / paths.journal_path),
        run_records_sha256=_sha256_bytes(_model_json_bytes(records)),
        report_sha256=_sha256_bytes(_model_json_bytes(report)),
        protected_raw_outputs_path=paths.protected_raw_outputs_path,
        protected_failure_diagnostics_path=(paths.protected_failure_diagnostics_path),
        live_provider_called=records.live_provider_called,
    )


def execute_authorized_diagnostic(
    repo_root: Path,
    *,
    adapter: LiveProviderAdapter,
    confirmation_phrase: str,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> DiagnosticExecutionSummary:
    """Execute once with no retries and full planned-attempt accountability."""

    (
        authorization,
        runtime_policy,
        dry_run,
        _,
        protected_bundle,
    ) = _load_authorized_assets(repo_root)
    if confirmation_phrase != authorization.confirmation_phrase:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_CONFIRMATION_MISMATCH",
            "The exact one-time diagnostic execution confirmation was not supplied.",
        )
    _assert_fresh_evidence_boundary(repo_root, authorization)
    _assert_sinks_writable(repo_root, authorization)

    (
        journal_path,
        run_records_path,
        report_path,
        manifest_path,
        protected_output_path,
        _,
    ) = _evidence_paths(repo_root, authorization)

    grouped: dict[str, list[DiagnosticDryRunAttempt]] = {}
    sequence_order: list[str] = []
    for attempt in dry_run.attempts:
        if attempt.sequence_id not in grouped:
            grouped[attempt.sequence_id] = []
            sequence_order.append(attempt.sequence_id)
        grouped[attempt.sequence_id].append(attempt)

    start = monotonic()
    attempt_records: list[DiagnosticExecutionAttemptRecord] = []
    sequence_records: list[DiagnosticSequenceRecord] = []
    experiment_stopped = False

    for sequence_id in sequence_order:
        planned_sequence = grouped[sequence_id]
        sequence_records_start = len(attempt_records)
        sequence_stopped = False

        for attempt in planned_sequence:
            if experiment_stopped:
                record = _skipped_record(
                    attempt,
                    DiagnosticExecutionAttemptStatus.SKIPPED_EXPERIMENT,
                )
            elif sequence_stopped:
                record = _skipped_record(
                    attempt,
                    DiagnosticExecutionAttemptStatus.SKIPPED_SEQUENCE,
                )
            else:
                elapsed = monotonic() - start
                wait_seconds = max(
                    0.0,
                    float(attempt.planned_offset_seconds) - elapsed,
                )
                if wait_seconds:
                    sleep(wait_seconds)
                observed_offset_ms = int((monotonic() - start) * 1000)
                invocation = _provider_invocation(
                    authorization,
                    attempt,
                    protected_bundle,
                )
                try:
                    call = adapter.invoke(invocation)
                except LiveProviderError as exc:
                    record = _provider_error_record(
                        attempt,
                        observed_offset_ms,
                        exc,
                        estimated_cost_microusd=(
                            runtime_policy.planned_cost_microusd_per_provider_call
                        ),
                    )
                    if exc.error_code is runtime_policy.request_rejection_error_code:
                        sequence_stopped = True
                    else:
                        experiment_stopped = True
                else:
                    _append_protected_output(
                        protected_output_path,
                        attempt,
                        invocation,
                        call,
                    )
                    record = _success_record(
                        attempt,
                        observed_offset_ms,
                        call,
                        estimated_cost_microusd=(
                            runtime_policy.planned_cost_microusd_per_provider_call
                        ),
                    )

            attempt_records.append(record)
            _append_json_line(
                journal_path,
                record.model_dump(mode="json"),
            )

        sequence_slice = tuple(attempt_records[sequence_records_start:])
        sequence_records.append(_sequence_record(sequence_id, sequence_slice))

    records = _record_set(
        authorization,
        attempt_records,
        sequence_records,
    )
    if records.provider_call_count > authorization.maximum_provider_calls:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_ATTEMPT_BUDGET_EXCEEDED",
            "The diagnostic execution exceeded its provider-call ceiling.",
        )
    if records.estimated_cost_microusd > authorization.maximum_total_cost_microusd:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_COST_BUDGET_EXCEEDED",
            "The diagnostic execution exceeded its estimated-cost ceiling.",
        )

    report = _report(records, protected_output_path)
    _write_model(run_records_path, records)
    _write_model(report_path, report)
    manifest = _manifest(
        repo_root,
        authorization,
        records,
        report,
    )
    _write_model(manifest_path, manifest)
    return _summary(
        "run",
        authorization,
        records,
        credential_checked=True,
    )


def run_live_diagnostic(
    repo_root: Path,
    *,
    confirmation_phrase: str,
) -> DiagnosticExecutionSummary:
    """Instantiate the Groq adapter only after deliberate live preflight."""

    live_preflight(repo_root)
    authorization = _load_model(
        repo_root / _AUTHORIZATION_PATH,
        DiagnosticExecutionAuthorization,
    )
    adapter: LiveProviderAdapter = GroqProviderAdapter(
        failure_diagnostic_path=(
            repo_root / authorization.evidence_paths.protected_failure_diagnostics_path
        )
    )
    return execute_authorized_diagnostic(
        repo_root,
        adapter=adapter,
        confirmation_phrase=confirmation_phrase,
    )


def _load_journal(path: Path) -> tuple[DiagnosticExecutionAttemptRecord, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_JOURNAL_MISSING",
            "The diagnostic execution journal was not found.",
            path=str(path),
        ) from exc
    try:
        return tuple(
            DiagnosticExecutionAttemptRecord.model_validate_json(line)
            for line in lines
            if line.strip()
        )
    except ValidationError as exc:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_JOURNAL_INVALID",
            "The diagnostic execution journal contains an invalid record.",
            path=str(path),
        ) from exc


def verify_execution(repo_root: Path) -> DiagnosticExecutionSummary:
    """Verify persisted evidence without credential access or provider calls."""

    (
        authorization,
        _,
        dry_run,
        _,
        _,
    ) = _load_authorized_assets(repo_root)
    paths = authorization.evidence_paths
    records = _load_model(
        repo_root / paths.run_records_path,
        DiagnosticExecutionRecordSet,
    )
    report = _load_model(
        repo_root / paths.report_path,
        DiagnosticExecutionReport,
    )
    manifest = _load_model(
        repo_root / paths.manifest_path,
        DiagnosticExecutionManifest,
    )
    journal = _load_journal(repo_root / paths.journal_path)

    if journal != records.attempts:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_JOURNAL_RECONCILIATION_FAILED",
            "The public journal and reconciled attempt records differ.",
        )
    if tuple(item.provider_request_sha256 for item in records.attempts) != tuple(
        item.provider_request_sha256 for item in dry_run.attempts
    ):
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_DRY_RUN_RECONCILIATION_FAILED",
            "Executed attempt identities differ from the reviewed dry run.",
        )
    if report.authorization_id != authorization.authorization_id:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_REPORT_AUTHORIZATION_MISMATCH",
            "The report is bound to a different active authorization.",
        )
    if report.provider_call_count != records.provider_call_count:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_REPORT_COUNT_MISMATCH",
            "The report and record set contain different provider-call counts.",
        )
    expected_manifest = _manifest(
        repo_root,
        authorization,
        records,
        report,
    )
    if manifest != expected_manifest:
        raise DiagnosticExecutionError(
            "DIAGNOSTIC_EXECUTION_MANIFEST_MISMATCH",
            "Persisted diagnostic execution evidence does not reproduce.",
            path=str(repo_root / paths.manifest_path),
        )
    return _summary(
        "verify",
        authorization,
        records,
        credential_checked=False,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("validate", "live-preflight", "run", "verify"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--authorization-id",
        default="batch-06-diagnostic-execution-auth-v1",
    )
    parser.add_argument(
        "--confirm",
        default="",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.authorization_id != "batch-06-diagnostic-execution-auth-v1":
        envelope = DiagnosticExecutionErrorEnvelope(
            error_code="DIAGNOSTIC_EXECUTION_AUTHORIZATION_UNKNOWN",
            safe_message="The supplied diagnostic execution authorization is unknown.",
            details=(args.authorization_id,),
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1

    try:
        if args.command == "validate":
            result = validate_activation(args.repo_root.resolve())
        elif args.command == "live-preflight":
            result = live_preflight(args.repo_root.resolve())
        elif args.command == "run":
            result = run_live_diagnostic(
                args.repo_root.resolve(),
                confirmation_phrase=args.confirm,
            )
        else:
            result = verify_execution(args.repo_root.resolve())
    except (
        DiagnosticExecutionError,
        DiagnosticAuthorizationReviewError,
        DiagnosticFixtureError,
    ) as exc:
        envelope = DiagnosticExecutionErrorEnvelope(
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
