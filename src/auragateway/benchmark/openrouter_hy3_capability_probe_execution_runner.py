"""Execute the authorized OpenRouter Hy3 capability probe exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, TypeVar, cast

from pydantic import BaseModel, ValidationError

from auragateway.benchmark.openrouter_hy3_capability_probe_activation_runner import (
    OpenRouterProbeActivationError,
    validate_openrouter_probe_activation,
    verify_openrouter_probe_local,
)
from auragateway.contracts.openrouter import (
    OpenRouterCacheObservationState,
    OpenRouterInvocationRequest,
)
from auragateway.contracts.openrouter_hy3_capability_probe_activation import (
    OpenRouterProbeActivationAuthorization,
    OpenRouterProbeActivationRuntimePolicy,
    OpenRouterProbePreflightReceipt,
    OpenRouterProbeProtectedPromptBundle,
)
from auragateway.contracts.openrouter_hy3_capability_probe_execution import (
    OpenRouterProbeAttemptContext,
    OpenRouterProbeExecutionErrorEnvelope,
    OpenRouterProbeExecutionManifest,
    OpenRouterProbeExecutionPolicy,
    OpenRouterProbeExecutionReport,
    OpenRouterProbeExecutionSummary,
    OpenRouterProbeJournalEventType,
    OpenRouterProbeJournalRecord,
    OpenRouterProbeLogicalCallRole,
    OpenRouterProbeParsedObservationRecord,
    OpenRouterProbeRawResponseKind,
    OpenRouterProbeRawResponseRecord,
    OpenRouterProbeTerminalOutcome,
    OpenRouterProbeTerminalReceipt,
)
from auragateway.providers.base import (
    LiveProviderError,
    ProtectedProviderPrompt,
)
from auragateway.providers.openrouter import (
    OpenRouterLiveInvocation,
    OpenRouterProviderAdapter,
    OpenRouterProviderCall,
)
from auragateway.providers.openrouter_recording import (
    OpenRouterRawResponseWriter,
    RecordingOpenRouterTransport,
)

_ACTIVATION_ROOT = Path("data/evals/benchmark/openrouter-hy3-capability-probe-v1")
_EXECUTION_ROOT = Path("data/evals/benchmark/openrouter-hy3-capability-probe-execution-v1")
_EXECUTION_CONTRACT_PATH = Path(
    "src/auragateway/contracts/openrouter_hy3_capability_probe_execution.py"
)
_RECORDING_TRANSPORT_PATH = Path("src/auragateway/providers/openrouter_recording.py")
_EXECUTION_RUNNER_PATH = Path(
    "src/auragateway/benchmark/openrouter_hy3_capability_probe_execution_runner.py"
)
_ADR_PATH = Path("docs/adr/openrouter-hy3-capability-probe-execution.md")
_BENCHMARK_REPORT_PATH = Path(
    "docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Execution.md"
)
_TERMINAL_RECEIPT_PATH = Path(
    ".local/benchmark/openrouter-hy3-capability-probe-v1/terminal_receipt.json"
)
_MODEL_T = TypeVar("_MODEL_T", bound=BaseModel)


class OpenRouterProbeExecutionError(Exception):
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


class _AttemptTransport(Protocol):
    """Adapter transport plus execution-only attempt evidence."""

    @property
    def last_status_code(self) -> int | None: ...

    @property
    def last_response_kind(self) -> OpenRouterProbeRawResponseKind | None: ...

    @property
    def successful_completion_received(self) -> bool: ...

    @property
    def request_count(self) -> int: ...

    def create_chat(
        self,
        *,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]: ...

    def get_generation(
        self,
        *,
        generation_id: str,
        timeout_seconds: float,
    ) -> Mapping[str, object]: ...


class _TransportFactory(Protocol):
    def __call__(
        self,
        *,
        api_key: str,
        context: OpenRouterProbeAttemptContext,
        writer: OpenRouterRawResponseWriter,
        clock: Callable[[], datetime],
    ) -> _AttemptTransport:
        """Create one fresh zero-retry transport for one inference attempt."""


class _GitInspector(Protocol):
    def inspect(self, repo_root: Path) -> tuple[str, str, bool]:
        """Return branch, full commit SHA, and clean-worktree state."""


class SubprocessGitInspector:
    """Inspect the exact local Git state required for irreversible execution."""

    def inspect(self, repo_root: Path) -> tuple[str, str, bool]:
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_GIT_INSPECTION_FAILED",
                "The repository state could not be inspected safely.",
                details=(type(exc).__name__,),
            ) from exc
        return branch, commit, not status.strip()


@dataclass(frozen=True, slots=True)
class _RuntimePaths:
    bundle: Path
    preflight: Path
    journal: Path
    raw: Path
    parsed: Path
    terminal: Path


@dataclass(frozen=True, slots=True)
class _LoadedExecution:
    authorization: OpenRouterProbeActivationAuthorization
    activation_policy: OpenRouterProbeActivationRuntimePolicy
    execution_policy: OpenRouterProbeExecutionPolicy
    bundle: OpenRouterProbeProtectedPromptBundle
    preflight: OpenRouterProbePreflightReceipt
    paths: _RuntimePaths


@dataclass(slots=True)
class _ExecutionState:
    source_commit: str
    started_at: datetime
    event_index: int = 0
    attempt_count: int = 0
    provider_success_count: int = 0
    retained_success_count: int = 0
    replacement_count: int = 0
    network_request_count: int = 0
    numeric_measurement_channel_observed: bool = False
    controlled_positive_cache_use_observed: bool = False
    cold_positive_cache_read_contamination: bool = False
    route_identity_valid: bool = True
    observations: list[OpenRouterProbeParsedObservationRecord] = field(default_factory=list)


class _ProtectedExecutionStore(OpenRouterRawResponseWriter):
    """Fsync-backed protected JSON and JSONL persistence."""

    def __init__(self, paths: _RuntimePaths) -> None:
        self._paths = paths

    def _append_model(self, path: Path, model: BaseModel) -> None:
        payload = (model.model_dump_json() + "\n").encode("utf-8")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("ab") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_EXECUTION_APPEND_FAILED",
                "A protected execution record could not be appended safely.",
                path=str(path),
                details=(type(exc).__name__,),
            ) from exc

    def write_raw_response(self, record: OpenRouterProbeRawResponseRecord) -> None:
        self._append_model(self._paths.raw, record)

    def append_journal(self, record: OpenRouterProbeJournalRecord) -> None:
        self._append_model(self._paths.journal, record)

    def append_parsed(self, record: OpenRouterProbeParsedObservationRecord) -> None:
        self._append_model(self._paths.parsed, record)

    def write_terminal(self, receipt: OpenRouterProbeTerminalReceipt) -> None:
        payload = (receipt.model_dump_json(indent=2) + "\n").encode("utf-8")
        path = self._paths.terminal
        temporary = path.with_suffix(".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                raise OpenRouterProbeExecutionError(
                    "OPENROUTER_HY3_AUTHORIZATION_ALREADY_CONSUMED",
                    "A protected terminal receipt already consumes this authorization.",
                    path=str(path),
                )
            with temporary.open("wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        except OpenRouterProbeExecutionError:
            raise
        except OSError as exc:
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_TERMINAL_RECEIPT_WRITE_FAILED",
                "The protected terminal receipt could not be written safely.",
                path=str(path),
                details=(type(exc).__name__,),
            ) from exc
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_FILE_READ_FAILED",
            "A required execution file could not be read.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_JSON_INVALID",
            "A required execution JSON asset could not be loaded.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


def _load_model(path: Path, model_type: type[_MODEL_T]) -> _MODEL_T:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_CONTRACT_INVALID",
            "An execution asset violates its typed contract.",
            path=str(path),
            details=details,
        ) from exc


def _read_jsonl(path: Path, model_type: type[_MODEL_T]) -> tuple[_MODEL_T, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_FILE_READ_FAILED",
            "A protected execution file could not be read.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc
    records: list[_MODEL_T] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            records.append(model_type.model_validate_json(line))
        except ValidationError as exc:
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_PROTECTED_RECORD_INVALID",
                "A protected JSONL record violates its typed contract.",
                path=str(path),
                details=(f"line={line_number}",),
            ) from exc
    return tuple(records)


def _runtime_paths(
    repo_root: Path,
    authorization: OpenRouterProbeActivationAuthorization,
) -> _RuntimePaths:
    paths = authorization.evidence_paths
    return _RuntimePaths(
        bundle=repo_root / paths.protected_prompt_bundle_path,
        preflight=repo_root / paths.protected_preflight_receipt_path,
        journal=repo_root / paths.protected_journal_path,
        raw=repo_root / paths.protected_raw_responses_path,
        parsed=repo_root / paths.protected_parsed_responses_path,
        terminal=repo_root / _TERMINAL_RECEIPT_PATH,
    )


def _validate_execution_manifest(repo_root: Path) -> OpenRouterProbeExecutionPolicy:
    policy = _load_model(
        repo_root / _EXECUTION_ROOT / "execution_policy.json",
        OpenRouterProbeExecutionPolicy,
    )
    report = _load_model(
        repo_root / _EXECUTION_ROOT / "execution_report.json",
        OpenRouterProbeExecutionReport,
    )
    manifest = _load_model(
        repo_root / _EXECUTION_ROOT / "execution_manifest.json",
        OpenRouterProbeExecutionManifest,
    )
    if report.policy_id != policy.policy_id or manifest.policy_id != policy.policy_id:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_POLICY_ID_MISMATCH",
            "The execution design assets do not share one policy identity.",
        )
    expected = {
        "execution_policy_sha256": _EXECUTION_ROOT / "execution_policy.json",
        "execution_report_sha256": _EXECUTION_ROOT / "execution_report.json",
        "contract_sha256": _EXECUTION_CONTRACT_PATH,
        "recording_transport_sha256": _RECORDING_TRANSPORT_PATH,
        "execution_runner_sha256": _EXECUTION_RUNNER_PATH,
        "adr_sha256": _ADR_PATH,
        "benchmark_report_sha256": _BENCHMARK_REPORT_PATH,
    }
    mismatches = tuple(
        f"{field}: expected={getattr(manifest, field)} observed={_sha256_file(repo_root / path)}"
        for field, path in expected.items()
        if getattr(manifest, field) != _sha256_file(repo_root / path)
    )
    if mismatches:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_MANIFEST_MISMATCH",
            "The execution manifest no longer matches committed assets.",
            details=mismatches,
        )
    return policy


def _load_execution(repo_root: Path) -> _LoadedExecution:
    execution_policy = _validate_execution_manifest(repo_root)
    try:
        validate_openrouter_probe_activation(repo_root)
    except OpenRouterProbeActivationError as exc:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_ACTIVATION_VALIDATION_FAILED",
            "The historical activation boundary failed validation.",
            path=exc.path,
            details=(exc.error_code, *exc.details),
        ) from exc
    authorization = _load_model(
        repo_root / _ACTIVATION_ROOT / "authorization.json",
        OpenRouterProbeActivationAuthorization,
    )
    activation_policy = _load_model(
        repo_root / _ACTIVATION_ROOT / "runtime_policy.json",
        OpenRouterProbeActivationRuntimePolicy,
    )
    if execution_policy.authorization_id != authorization.authorization_id:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_AUTHORIZATION_MISMATCH",
            "The execution policy does not match the active authorization.",
        )
    if (
        activation_policy.maximum_total_inference_attempts
        != execution_policy.maximum_total_inference_attempts
        or activation_policy.transient_http_statuses != execution_policy.transient_http_statuses
    ):
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_RUNTIME_POLICY_MISMATCH",
            "The execution refinement changes the frozen attempt constitution.",
        )
    paths = _runtime_paths(repo_root, authorization)
    bundle = _load_model(paths.bundle, OpenRouterProbeProtectedPromptBundle)
    preflight = _load_model(paths.preflight, OpenRouterProbePreflightReceipt)
    if _sha256_file(paths.bundle) != authorization.protected_prompt_bundle_sha256:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_PROMPT_BUNDLE_MISMATCH",
            "The protected prompt bundle no longer matches the authorization.",
        )
    if preflight.prompt_bundle_sha256 != authorization.protected_prompt_bundle_sha256:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_PREFLIGHT_MISMATCH",
            "The preflight receipt does not match the authorized prompt bundle.",
        )
    if tuple(item.expected_output for item in bundle.calls) != execution_policy.expected_outputs:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_OUTPUT_POLICY_MISMATCH",
            "The protected prompt bundle does not match the exact output policy.",
        )
    return _LoadedExecution(
        authorization=authorization,
        activation_policy=activation_policy,
        execution_policy=execution_policy,
        bundle=bundle,
        preflight=preflight,
        paths=paths,
    )


def _default_transport_factory(
    *,
    api_key: str,
    context: OpenRouterProbeAttemptContext,
    writer: OpenRouterRawResponseWriter,
    clock: Callable[[], datetime],
) -> _AttemptTransport:
    return RecordingOpenRouterTransport(
        api_key=api_key,
        context=context,
        writer=writer,
        clock=clock,
    )


def _journal(
    store: _ProtectedExecutionStore,
    state: _ExecutionState,
    *,
    event_type: OpenRouterProbeJournalEventType,
    recorded_at: datetime,
    attempt: OpenRouterProbeAttemptContext | None = None,
    safe_error_code: str | None = None,
    retry_permitted: bool | None = None,
    terminal_outcome: OpenRouterProbeTerminalOutcome | None = None,
) -> None:
    state.event_index += 1
    store.append_journal(
        OpenRouterProbeJournalRecord(
            authorization_id="openrouter-hy3-capability-probe-auth-v1",
            execution_id="openrouter-hy3-capability-probe-v1",
            event_index=state.event_index,
            event_type=event_type,
            recorded_at=recorded_at,
            attempt_id=None if attempt is None else attempt.attempt_id,
            logical_call_role=None if attempt is None else attempt.logical_call_role,
            attempt_number=None if attempt is None else attempt.attempt_number,
            total_attempt_count=state.attempt_count,
            provider_success_count=state.provider_success_count,
            retained_success_count=state.retained_success_count,
            replacement_count=state.replacement_count,
            safe_error_code=safe_error_code,
            retry_permitted=retry_permitted,
            terminal_outcome=terminal_outcome,
        )
    )


def _attempt_id(role: OpenRouterProbeLogicalCallRole, attempt_number: int) -> str:
    role_fragment = "cold" if role is OpenRouterProbeLogicalCallRole.COLD_PROBE else "warm"
    return f"openrouter-hy3-capability-probe-v1-{role_fragment}-attempt-{attempt_number}"


def _numeric_measurement_observed(
    record: OpenRouterProbeParsedObservationRecord,
) -> bool:
    numeric_states = {
        OpenRouterCacheObservationState.OBSERVED_ZERO,
        OpenRouterCacheObservationState.OBSERVED_POSITIVE,
    }
    return (
        record.observation.read.state in numeric_states
        or record.observation.write.state in numeric_states
        or record.observation.route.native_tokens_cached is not None
    )


def _controlled_positive_cache_use(
    role: OpenRouterProbeLogicalCallRole,
    record: OpenRouterProbeParsedObservationRecord,
) -> bool:
    if role is OpenRouterProbeLogicalCallRole.COLD_PROBE:
        return record.observation.write.state is OpenRouterCacheObservationState.OBSERVED_POSITIVE
    return record.observation.read.state is OpenRouterCacheObservationState.OBSERVED_POSITIVE


def _route_identity_valid(
    observations: Sequence[OpenRouterProbeParsedObservationRecord],
) -> bool:
    if len(observations) != 2:
        return False
    routes = [record.observation.route for record in observations]
    return (
        len({route.requested_model for route in routes}) == 1
        and len({route.resolved_model for route in routes}) == 1
        and len({route.upstream_provider for route in routes}) == 1
        and len({route.session_id_sha256 for route in routes}) == 1
    )


def _safe_error_code(exc: LiveProviderError) -> str:
    value = getattr(exc.error_code, "value", None)
    return value if isinstance(value, str) else str(exc.error_code)


def _provider_error_outcome(exc: LiveProviderError) -> OpenRouterProbeTerminalOutcome:
    message = str(exc).lower()
    if (
        "generation identities do not reconcile" in message
        or "does not preserve the requested session" in message
    ):
        return OpenRouterProbeTerminalOutcome.CLOSED_ROUTE_UNIDENTIFIABLE
    if _safe_error_code(exc) in {"invalid_response", "ambiguous_response"}:
        return OpenRouterProbeTerminalOutcome.CLOSED_OBSERVATION_INVALID
    return OpenRouterProbeTerminalOutcome.CLOSED_TERMINAL_PROVIDER_FAILURE


def _build_parsed_record(
    *,
    loaded: _LoadedExecution,
    attempt: OpenRouterProbeAttemptContext,
    provider_call: OpenRouterProviderCall,
    expected_output: Literal["COLD-PROBE-ACK", "WARM-PROBE-ACK"],
    retained_at: datetime,
) -> OpenRouterProbeParsedObservationRecord:
    call = provider_call
    output_text = call.protected_output.text
    exact_output_valid = output_text.strip() == expected_output
    role = attempt.logical_call_role
    provisional = OpenRouterProbeParsedObservationRecord(
        authorization_id=loaded.authorization.authorization_id,
        execution_id=loaded.authorization.execution_id,
        attempt_id=attempt.attempt_id,
        logical_call_role=role,
        attempt_number=attempt.attempt_number,
        retained_at=retained_at,
        result=call.result,
        telemetry=call.telemetry,
        observation=call.observation,
        expected_output=expected_output,
        exact_trimmed_output_valid=exact_output_valid,
        numeric_measurement_channel_observed=False,
        cold_positive_cache_read_contamination=(
            role is OpenRouterProbeLogicalCallRole.COLD_PROBE
            and call.observation.read.state is OpenRouterCacheObservationState.OBSERVED_POSITIVE
        ),
        controlled_positive_cache_use_observed=False,
    )
    return provisional.model_copy(
        update={
            "numeric_measurement_channel_observed": _numeric_measurement_observed(provisional),
            "controlled_positive_cache_use_observed": _controlled_positive_cache_use(
                role,
                provisional,
            ),
        }
    )


def _run_logical_call(
    *,
    loaded: _LoadedExecution,
    call_index: int,
    state: _ExecutionState,
    store: _ProtectedExecutionStore,
    api_key: str,
    transport_factory: _TransportFactory,
    clock: Callable[[], datetime],
) -> OpenRouterProbeTerminalOutcome | None:
    protected_call = loaded.bundle.calls[call_index]
    role = OpenRouterProbeLogicalCallRole(protected_call.request_role)
    for attempt_number in (1, 2):
        if state.attempt_count >= loaded.execution_policy.maximum_total_inference_attempts:
            return OpenRouterProbeTerminalOutcome.CLOSED_TRANSIENT_BUDGET_EXHAUSTED
        attempt = OpenRouterProbeAttemptContext(
            authorization_id=loaded.authorization.authorization_id,
            execution_id=loaded.authorization.execution_id,
            attempt_id=_attempt_id(role, attempt_number),
            logical_call_role=role,
            logical_call_index=call_index,
            attempt_number=attempt_number,
        )
        state.attempt_count += 1
        _journal(
            store,
            state,
            event_type=OpenRouterProbeJournalEventType.ATTEMPT_STARTED,
            recorded_at=clock(),
            attempt=attempt,
        )
        transport = transport_factory(
            api_key=api_key,
            context=attempt,
            writer=store,
            clock=clock,
        )
        invocation = OpenRouterLiveInvocation(
            request=OpenRouterInvocationRequest(
                request_id=protected_call.request_id,
                fixture_id=protected_call.fixture_id,
                static_prefix_fingerprint=loaded.bundle.stable_prefix_sha256,
                input_token_count=max(
                    1,
                    (
                        len(loaded.bundle.stable_prefix.encode("utf-8"))
                        + len(protected_call.user_suffix.encode("utf-8"))
                        + 3
                    )
                    // 4,
                ),
                output_token_budget=loaded.bundle.output_token_budget,
            ),
            prompt=ProtectedProviderPrompt(
                system_prompt=loaded.bundle.stable_prefix,
                user_prompt=protected_call.user_suffix,
            ),
            session_id=loaded.bundle.session_id,
            timeout_seconds=loaded.authorization.timeout_seconds,
        )
        try:
            provider_call = OpenRouterProviderAdapter(transport).invoke(invocation)
        except LiveProviderError as exc:
            state.network_request_count += transport.request_count
            if transport.successful_completion_received:
                state.provider_success_count += 1
            status = transport.last_status_code
            transient = (
                status in loaded.execution_policy.transient_http_statuses
                and not transport.successful_completion_received
            )
            retry_permitted = (
                transient
                and attempt_number == 1
                and state.attempt_count < loaded.execution_policy.maximum_total_inference_attempts
            )
            if retry_permitted:
                state.replacement_count += 1
                _journal(
                    store,
                    state,
                    event_type=OpenRouterProbeJournalEventType.ATTEMPT_TRANSIENT_FAILURE,
                    recorded_at=clock(),
                    attempt=attempt,
                    safe_error_code=_safe_error_code(exc),
                    retry_permitted=True,
                )
                continue
            outcome = (
                OpenRouterProbeTerminalOutcome.CLOSED_TRANSIENT_BUDGET_EXHAUSTED
                if transient
                else _provider_error_outcome(exc)
            )
            _journal(
                store,
                state,
                event_type=OpenRouterProbeJournalEventType.ATTEMPT_TERMINAL_FAILURE,
                recorded_at=clock(),
                attempt=attempt,
                safe_error_code=_safe_error_code(exc),
                retry_permitted=False,
            )
            return outcome
        state.network_request_count += transport.request_count
        state.provider_success_count += 1
        parsed = _build_parsed_record(
            loaded=loaded,
            attempt=attempt,
            provider_call=provider_call,
            expected_output=cast(
                Literal["COLD-PROBE-ACK", "WARM-PROBE-ACK"],
                protected_call.expected_output,
            ),
            retained_at=clock(),
        )
        store.append_parsed(parsed)
        if not parsed.exact_trimmed_output_valid:
            _journal(
                store,
                state,
                event_type=OpenRouterProbeJournalEventType.ATTEMPT_TERMINAL_FAILURE,
                recorded_at=clock(),
                attempt=attempt,
                safe_error_code="OPENROUTER_HY3_OUTPUT_CONTRACT_FAILURE",
                retry_permitted=False,
            )
            return OpenRouterProbeTerminalOutcome.CLOSED_OBSERVATION_INVALID
        state.retained_success_count += 1
        state.numeric_measurement_channel_observed = (
            state.numeric_measurement_channel_observed
            or parsed.numeric_measurement_channel_observed
        )
        state.controlled_positive_cache_use_observed = (
            state.controlled_positive_cache_use_observed
            or parsed.controlled_positive_cache_use_observed
        )
        state.cold_positive_cache_read_contamination = (
            state.cold_positive_cache_read_contamination
            or parsed.cold_positive_cache_read_contamination
        )
        state.observations.append(parsed)
        _journal(
            store,
            state,
            event_type=OpenRouterProbeJournalEventType.OBSERVATION_RETAINED,
            recorded_at=clock(),
            attempt=attempt,
        )
        return None
    return OpenRouterProbeTerminalOutcome.CLOSED_TRANSIENT_BUDGET_EXHAUSTED


def _terminal_outcome(state: _ExecutionState) -> OpenRouterProbeTerminalOutcome:
    state.route_identity_valid = _route_identity_valid(state.observations)
    if not state.route_identity_valid:
        return OpenRouterProbeTerminalOutcome.CLOSED_ROUTE_UNIDENTIFIABLE
    if not state.numeric_measurement_channel_observed:
        return OpenRouterProbeTerminalOutcome.CLOSED_TELEMETRY_UNAVAILABLE
    if not state.controlled_positive_cache_use_observed:
        return OpenRouterProbeTerminalOutcome.CLOSED_NO_CACHE_USE
    return OpenRouterProbeTerminalOutcome.PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW


def _write_terminal_receipt(
    *,
    loaded: _LoadedExecution,
    state: _ExecutionState,
    store: _ProtectedExecutionStore,
    outcome: OpenRouterProbeTerminalOutcome,
    closed_at: datetime,
) -> OpenRouterProbeTerminalReceipt:
    state.route_identity_valid = _route_identity_valid(state.observations)
    next_gate: Literal[
        "sanitized_capability_closeout",
        "pilot_authorization_review",
    ] = (
        "pilot_authorization_review"
        if outcome is OpenRouterProbeTerminalOutcome.PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW
        else "sanitized_capability_closeout"
    )
    receipt = OpenRouterProbeTerminalReceipt(
        authorization_id=loaded.authorization.authorization_id,
        execution_id=loaded.authorization.execution_id,
        terminal_outcome=outcome,
        source_commit=state.source_commit,
        execution_started_at=state.started_at,
        closed_at=closed_at,
        attempt_count=state.attempt_count,
        provider_success_count=state.provider_success_count,
        retained_success_count=state.retained_success_count,
        replacement_count=state.replacement_count,
        numeric_measurement_channel_observed=(state.numeric_measurement_channel_observed),
        controlled_positive_cache_use_observed=(state.controlled_positive_cache_use_observed),
        cold_positive_cache_read_contamination=(state.cold_positive_cache_read_contamination),
        route_identity_valid=state.route_identity_valid,
        prompt_bundle_sha256=_sha256_file(loaded.paths.bundle),
        preflight_receipt_sha256=_sha256_file(loaded.paths.preflight),
        journal_sha256_before_close=_sha256_file(loaded.paths.journal),
        journal_bytes_before_close=loaded.paths.journal.stat().st_size,
        raw_responses_sha256=_sha256_file(loaded.paths.raw),
        parsed_responses_sha256=_sha256_file(loaded.paths.parsed),
        next_gate=next_gate,
    )
    store.write_terminal(receipt)
    _journal(
        store,
        state,
        event_type=OpenRouterProbeJournalEventType.EXECUTION_CLOSED,
        recorded_at=closed_at,
        terminal_outcome=outcome,
    )
    return receipt


def _summary_from_receipt(
    *,
    command: Literal["validate", "execute", "verify-local", "close-interrupted"],
    receipt: OpenRouterProbeTerminalReceipt,
    credential_accessed: bool,
    network_request_count: int,
) -> OpenRouterProbeExecutionSummary:
    return OpenRouterProbeExecutionSummary(
        command=command,
        authorization_id=receipt.authorization_id,
        execution_id=receipt.execution_id,
        execution_ready=False,
        terminal_receipt_present=True,
        authorization_consumed=True,
        terminal_outcome=receipt.terminal_outcome,
        attempt_count=receipt.attempt_count,
        provider_success_count=receipt.provider_success_count,
        retained_success_count=receipt.retained_success_count,
        replacement_count=receipt.replacement_count,
        credential_accessed=credential_accessed,
        network_request_count=network_request_count,
        next_gate=receipt.next_gate,
    )


def _state_from_existing_records(
    *,
    source_commit: str,
    journal: Sequence[OpenRouterProbeJournalRecord],
    parsed: Sequence[OpenRouterProbeParsedObservationRecord],
) -> _ExecutionState:
    if not journal:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_NO_INTERRUPTED_EXECUTION",
            "No incomplete execution journal exists to close.",
        )
    started = next(
        (
            record.recorded_at
            for record in journal
            if record.event_type is OpenRouterProbeJournalEventType.EXECUTION_STARTED
        ),
        journal[0].recorded_at,
    )
    last = journal[-1]
    state = _ExecutionState(
        source_commit=source_commit,
        started_at=started,
        event_index=max(record.event_index for record in journal),
        attempt_count=last.total_attempt_count,
        provider_success_count=last.provider_success_count,
        retained_success_count=last.retained_success_count,
        replacement_count=last.replacement_count,
        observations=list(parsed),
    )
    state.numeric_measurement_channel_observed = any(
        record.numeric_measurement_channel_observed for record in parsed
    )
    state.controlled_positive_cache_use_observed = any(
        record.controlled_positive_cache_use_observed for record in parsed
    )
    state.cold_positive_cache_read_contamination = any(
        record.cold_positive_cache_read_contamination for record in parsed
    )
    state.route_identity_valid = _route_identity_valid(parsed) if len(parsed) == 2 else False
    return state


def _close_interrupted(
    *,
    loaded: _LoadedExecution,
    source_commit: str,
    clock: Callable[[], datetime],
    command: Literal["execute", "close-interrupted"],
) -> OpenRouterProbeExecutionSummary:
    journal = _read_jsonl(loaded.paths.journal, OpenRouterProbeJournalRecord)
    parsed = _read_jsonl(
        loaded.paths.parsed,
        OpenRouterProbeParsedObservationRecord,
    )
    state = _state_from_existing_records(
        source_commit=source_commit,
        journal=journal,
        parsed=parsed,
    )
    store = _ProtectedExecutionStore(loaded.paths)
    receipt = _write_terminal_receipt(
        loaded=loaded,
        state=state,
        store=store,
        outcome=OpenRouterProbeTerminalOutcome.CLOSED_INTERRUPTED_EXECUTION,
        closed_at=clock(),
    )
    return _summary_from_receipt(
        command=command,
        receipt=receipt,
        credential_accessed=False,
        network_request_count=0,
    )


def validate_openrouter_probe_execution(
    repo_root: Path,
) -> OpenRouterProbeExecutionSummary:
    """Validate additive execution assets without credential or provider access."""

    loaded = _load_execution(repo_root)
    if loaded.paths.terminal.exists():
        receipt = _load_model(loaded.paths.terminal, OpenRouterProbeTerminalReceipt)
        return _summary_from_receipt(
            command="validate",
            receipt=receipt,
            credential_accessed=False,
            network_request_count=0,
        )
    journal_nonempty = loaded.paths.journal.stat().st_size > 0
    return OpenRouterProbeExecutionSummary(
        command="validate",
        authorization_id=loaded.authorization.authorization_id,
        execution_id=loaded.authorization.execution_id,
        execution_ready=not journal_nonempty,
        terminal_receipt_present=False,
        authorization_consumed=False,
        attempt_count=0,
        provider_success_count=0,
        retained_success_count=0,
        replacement_count=0,
        credential_accessed=False,
        network_request_count=0,
        next_gate=(
            "close_interrupted_execution"
            if journal_nonempty
            else "merge_execution_runner_then_execute_once"
        ),
    )


def execute_openrouter_probe(
    repo_root: Path,
    *,
    confirmation_phrase: str,
    environ: Mapping[str, str] | None = None,
    transport_factory: _TransportFactory = _default_transport_factory,
    git_inspector: _GitInspector | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> OpenRouterProbeExecutionSummary:
    """Execute the exact cold/warm probe once or terminalize an interruption."""

    loaded = _load_execution(repo_root)
    inspector = SubprocessGitInspector() if git_inspector is None else git_inspector
    branch, source_commit, clean = inspector.inspect(repo_root)
    if loaded.paths.terminal.exists():
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_AUTHORIZATION_ALREADY_CONSUMED",
            "A protected terminal receipt already consumes this authorization.",
            path=str(loaded.paths.terminal),
        )
    if loaded.paths.journal.stat().st_size > 0:
        return _close_interrupted(
            loaded=loaded,
            source_commit=source_commit,
            clock=clock,
            command="execute",
        )
    try:
        verify_summary = verify_openrouter_probe_local(repo_root)
    except OpenRouterProbeActivationError as exc:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_LOCAL_BOUNDARY_INVALID",
            "The protected activation boundary failed execution validation.",
            path=exc.path,
            details=(exc.error_code, *exc.details),
        ) from exc
    if not verify_summary.live_preflight_passed:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_PREFLIGHT_REQUIRED",
            "A successful protected preflight receipt is required before execution.",
        )
    if branch != "main" or not clean:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_GIT_STATE_INVALID",
            "Live execution requires a clean main branch.",
            details=(f"branch={branch}", f"clean={str(clean).lower()}"),
        )
    if confirmation_phrase != loaded.execution_policy.confirmation_phrase:
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_CONFIRMATION_INVALID",
            "The exact one-time execution confirmation phrase is required.",
        )
    environment = os.environ if environ is None else environ
    api_key = environment.get(loaded.authorization.api_key_environment_name, "")
    if not api_key.strip():
        raise OpenRouterProbeExecutionError(
            "OPENROUTER_HY3_EXECUTION_CREDENTIAL_MISSING",
            "The OpenRouter API key environment variable is missing or empty.",
        )
    started_at = clock()
    state = _ExecutionState(source_commit=source_commit, started_at=started_at)
    store = _ProtectedExecutionStore(loaded.paths)
    _journal(
        store,
        state,
        event_type=OpenRouterProbeJournalEventType.EXECUTION_STARTED,
        recorded_at=started_at,
    )
    outcome: OpenRouterProbeTerminalOutcome | None = None
    for call_index in (0, 1):
        outcome = _run_logical_call(
            loaded=loaded,
            call_index=call_index,
            state=state,
            store=store,
            api_key=api_key,
            transport_factory=transport_factory,
            clock=clock,
        )
        if outcome is not None:
            break
    if outcome is None:
        outcome = _terminal_outcome(state)
    receipt = _write_terminal_receipt(
        loaded=loaded,
        state=state,
        store=store,
        outcome=outcome,
        closed_at=clock(),
    )
    return _summary_from_receipt(
        command="execute",
        receipt=receipt,
        credential_accessed=True,
        network_request_count=state.network_request_count,
    )


def verify_openrouter_probe_execution_local(
    repo_root: Path,
) -> OpenRouterProbeExecutionSummary:
    """Verify the execution boundary or consumed terminal receipt without network access."""

    loaded = _load_execution(repo_root)
    if loaded.paths.terminal.exists():
        receipt = _load_model(loaded.paths.terminal, OpenRouterProbeTerminalReceipt)
        if receipt.prompt_bundle_sha256 != _sha256_file(loaded.paths.bundle):
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_TERMINAL_PROMPT_HASH_MISMATCH",
                "The terminal receipt no longer matches the protected prompt bundle.",
            )
        if receipt.preflight_receipt_sha256 != _sha256_file(loaded.paths.preflight):
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_TERMINAL_PREFLIGHT_HASH_MISMATCH",
                "The terminal receipt no longer matches the preflight receipt.",
            )
        try:
            journal_prefix = loaded.paths.journal.read_bytes()[: receipt.journal_bytes_before_close]
        except OSError as exc:
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_TERMINAL_JOURNAL_READ_FAILED",
                "The protected journal could not be verified.",
                path=str(loaded.paths.journal),
                details=(type(exc).__name__,),
            ) from exc
        if _sha256_bytes(journal_prefix) != receipt.journal_sha256_before_close:
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_TERMINAL_JOURNAL_HASH_MISMATCH",
                "The terminal receipt no longer matches the protected journal prefix.",
            )
        if receipt.raw_responses_sha256 != _sha256_file(loaded.paths.raw):
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_TERMINAL_RAW_HASH_MISMATCH",
                "The terminal receipt no longer matches protected raw responses.",
            )
        if receipt.parsed_responses_sha256 != _sha256_file(loaded.paths.parsed):
            raise OpenRouterProbeExecutionError(
                "OPENROUTER_HY3_TERMINAL_PARSED_HASH_MISMATCH",
                "The terminal receipt no longer matches protected parsed responses.",
            )
        return _summary_from_receipt(
            command="verify-local",
            receipt=receipt,
            credential_accessed=False,
            network_request_count=0,
        )
    journal_nonempty = loaded.paths.journal.stat().st_size > 0
    return OpenRouterProbeExecutionSummary(
        command="verify-local",
        authorization_id=loaded.authorization.authorization_id,
        execution_id=loaded.authorization.execution_id,
        execution_ready=not journal_nonempty,
        terminal_receipt_present=False,
        authorization_consumed=False,
        attempt_count=0,
        provider_success_count=0,
        retained_success_count=0,
        replacement_count=0,
        credential_accessed=False,
        network_request_count=0,
        next_gate=(
            "close_interrupted_execution"
            if journal_nonempty
            else "capability_probe_execution_confirmation"
        ),
    )


def close_interrupted_openrouter_probe(
    repo_root: Path,
    *,
    git_inspector: _GitInspector | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> OpenRouterProbeExecutionSummary:
    """Consume an incomplete authorization locally without provider access."""

    loaded = _load_execution(repo_root)
    inspector = SubprocessGitInspector() if git_inspector is None else git_inspector
    _, source_commit, _ = inspector.inspect(repo_root)
    if loaded.paths.terminal.exists():
        receipt = _load_model(loaded.paths.terminal, OpenRouterProbeTerminalReceipt)
        return _summary_from_receipt(
            command="close-interrupted",
            receipt=receipt,
            credential_accessed=False,
            network_request_count=0,
        )
    return _close_interrupted(
        loaded=loaded,
        source_commit=source_commit,
        clock=clock,
        command="close-interrupted",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute the OpenRouter Hy3 capability probe exactly once."
    )
    parser.add_argument(
        "command",
        choices=("validate", "execute", "verify-local", "close-interrupted"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--confirm", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            summary = validate_openrouter_probe_execution(args.repo_root)
        elif args.command == "execute":
            summary = execute_openrouter_probe(
                args.repo_root,
                confirmation_phrase=args.confirm,
            )
        elif args.command == "verify-local":
            summary = verify_openrouter_probe_execution_local(args.repo_root)
        else:
            summary = close_interrupted_openrouter_probe(args.repo_root)
    except OpenRouterProbeExecutionError as exc:
        print(
            OpenRouterProbeExecutionErrorEnvelope(
                error_code=exc.error_code,
                safe_message=exc.safe_message,
                path=exc.path,
                details=exc.details,
            ).model_dump_json(indent=2),
            file=sys.stderr,
        )
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
