"""Validate and execute one authorized Groq raw-wire telemetry reauthorization."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable, Mapping
from importlib import metadata
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar, cast

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from auragateway.contracts.groq_cache_telemetry_reauthorization import (
    GroqCacheTelemetryReauthorizationOutcome,
)
from auragateway.contracts.groq_cache_telemetry_reauthorization_execution import (
    ReauthorizationActivationManifest,
    ReauthorizationActivationReport,
    ReauthorizationAttemptRecord,
    ReauthorizationAttemptStatus,
    ReauthorizationBillingObservationState,
    ReauthorizationExecutionAuthorization,
    ReauthorizationExecutionErrorEnvelope,
    ReauthorizationExecutionManifest,
    ReauthorizationExecutionReport,
    ReauthorizationExecutionRuntimePolicy,
    ReauthorizationExecutionStatus,
    ReauthorizationExecutionSummary,
    ReauthorizationRunRecordSet,
)

_DEFAULT_EXECUTION_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-v1")
_ADR_PATH = Path("docs/adr/groq-cache-telemetry-reauthorization-activation.md")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_Groq_Cache_Telemetry_Reauthorization_Activation.md")
_MODEL_T = TypeVar("_MODEL_T", bound=BaseModel)
_ALLOWED_PROVIDER_EXCEPTION_CLASSES = frozenset(
    {
        "APIConnectionError",
        "APIStatusError",
        "APITimeoutError",
        "AuthenticationError",
        "BadRequestError",
        "ConflictError",
        "InternalServerError",
        "NotFoundError",
        "PermissionDeniedError",
        "RateLimitError",
        "UnprocessableEntityError",
    }
)


class _FrozenPromptMessage(BaseModel):
    """One exact message from the reviewed protected request bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user"]
    content: str


class _FrozenProviderRequest(BaseModel):
    """Exact provider request whose canonical hash was reviewed before activation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    messages: tuple[_FrozenPromptMessage, _FrozenPromptMessage]
    model: Literal["openai/gpt-oss-20b"]
    max_completion_tokens: Literal[32]
    temperature: float
    stream: Literal[False]
    store: Literal[False]
    reasoning_effort: Literal["low"]

    @model_validator(mode="after")
    def validate_message_order(self) -> _FrozenProviderRequest:
        if tuple(message.role for message in self.messages) != ("system", "user"):
            raise ValueError("reviewed request messages must remain system then user")
        if self.temperature != 0.0:
            raise ValueError("reviewed request temperature must remain zero")
        return self


class _HttpResponse(Protocol):
    content: bytes
    status_code: int


class _ParsedCompletion(Protocol):
    model_fields_set: set[str]

    def model_dump(
        self,
        *,
        mode: str = "python",
        exclude_none: bool = False,
        exclude_unset: bool = False,
    ) -> dict[str, object]:
        """Return the parsed SDK object as a temporary mapping."""


class _RawApiResponse(Protocol):
    http_response: _HttpResponse

    def parse(self) -> _ParsedCompletion:
        """Parse the exact raw response into the SDK response model."""

    def close(self) -> None:
        """Release the underlying response."""


class RawCompletionClient(Protocol):
    def create(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_completion_tokens: int,
        temperature: float,
        stream: bool,
        store: bool,
        reasoning_effort: str,
    ) -> _RawApiResponse:
        """Create one raw-response chat completion."""

    def close(self) -> None:
        """Close the provider client."""


class _RawCreateResource(Protocol):
    def create(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_completion_tokens: int,
        temperature: float,
        stream: bool,
        store: bool,
        reasoning_effort: str,
    ) -> _RawApiResponse:
        """Create one raw-response chat completion."""


class ReauthorizationExecutionError(Exception):
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


class _SdkRawCompletionClient:
    """Narrow wrapper around the reviewed Groq raw-response surface."""

    def __init__(self, *, api_key: str, timeout_seconds: float) -> None:
        from groq import Groq

        self._client = Groq(
            api_key=api_key,
            max_retries=0,
            timeout=timeout_seconds,
        )

    def create(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_completion_tokens: int,
        temperature: float,
        stream: bool,
        store: bool,
        reasoning_effort: str,
    ) -> _RawApiResponse:
        resource = cast(
            _RawCreateResource,
            cast(Any, self._client.chat.completions.with_raw_response),
        )
        return resource.create(
            messages=messages,
            model=model,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            stream=stream,
            store=store,
            reasoning_effort=reasoning_effort,
        )

    def close(self) -> None:
        self._client.close()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_FILE_READ_FAILED",
            "A required reauthorization execution file could not be read.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_JSON_INVALID",
            "A required reauthorization JSON asset could not be loaded.",
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
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_CONTRACT_INVALID",
            "A reauthorization execution asset violates its typed contract.",
            path=str(path),
            details=details,
        ) from exc


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _write_json(path: Path, payload: BaseModel) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload.model_dump_json(indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_EVIDENCE_WRITE_FAILED",
            "Reauthorization evidence could not be retained safely.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


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
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_EVIDENCE_WRITE_FAILED",
            "Reauthorization evidence could not be retained safely.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


def _validate_activation_manifest(
    repo_root: Path,
    execution_root: Path,
    manifest: ReauthorizationActivationManifest,
) -> None:
    expected = {
        "authorization_sha256": execution_root / "authorization.json",
        "runtime_policy_sha256": execution_root / "runtime_policy.json",
        "activation_report_sha256": execution_root / "activation_report.json",
        "adr_sha256": _ADR_PATH,
        "report_sha256": _REPORT_PATH,
    }
    mismatches = tuple(
        f"{field}: expected={getattr(manifest, field)} observed={_sha256_file(repo_root / path)}"
        for field, path in expected.items()
        if getattr(manifest, field) != _sha256_file(repo_root / path)
    )
    if mismatches:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_ACTIVATION_HASH_MISMATCH",
            "The active authorization no longer matches its activation manifest.",
            details=mismatches,
        )


def _validate_public_bindings(
    repo_root: Path,
    authorization: ReauthorizationExecutionAuthorization,
) -> None:
    for binding in authorization.bindings:
        if binding.protected_local:
            continue
        observed = _sha256_file(repo_root / binding.path)
        if observed != binding.sha256:
            raise ReauthorizationExecutionError(
                "GROQ_REAUTHORIZATION_EXECUTION_BINDING_MISMATCH",
                "A reviewed reauthorization asset no longer matches.",
                path=binding.path,
                details=(f"expected={binding.sha256}", f"observed={observed}"),
            )


def _load_activation(
    repo_root: Path,
    execution_root: Path,
) -> tuple[
    ReauthorizationExecutionAuthorization,
    ReauthorizationExecutionRuntimePolicy,
]:
    root = repo_root / execution_root
    authorization = _load_model(
        root / "authorization.json",
        ReauthorizationExecutionAuthorization,
    )
    policy = _load_model(
        root / "runtime_policy.json",
        ReauthorizationExecutionRuntimePolicy,
    )
    activation_report = _load_model(
        root / "activation_report.json",
        ReauthorizationActivationReport,
    )
    activation_manifest = _load_model(
        root / "activation_manifest.json",
        ReauthorizationActivationManifest,
    )
    if policy.authorization_id != authorization.authorization_id:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_AUTHORIZATION_MISMATCH",
            "Authorization and runtime policy identify different executions.",
        )
    if activation_report.authorization_id != authorization.authorization_id:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_ACTIVATION_REPORT_MISMATCH",
            "Activation report and authorization identify different executions.",
        )
    if activation_manifest.authorization_id != authorization.authorization_id:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_ACTIVATION_MANIFEST_MISMATCH",
            "Activation manifest and authorization identify different executions.",
        )
    _validate_activation_manifest(repo_root, execution_root, activation_manifest)
    _validate_public_bindings(repo_root, authorization)
    return authorization, policy


def _protected_binding(
    authorization: ReauthorizationExecutionAuthorization,
) -> tuple[str, str]:
    item = next(binding for binding in authorization.bindings if binding.protected_local)
    return item.path, item.sha256


def _load_protected_prompt(
    repo_root: Path,
    authorization: ReauthorizationExecutionAuthorization,
) -> tuple[_FrozenProviderRequest, str]:
    binding_path, binding_hash = _protected_binding(authorization)
    path = repo_root / binding_path
    if _sha256_file(path) != binding_hash:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_PROMPT_HASH_MISMATCH",
            "The protected prompt bundle no longer matches authorization.",
            path=binding_path,
        )
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_PROMPT_SHAPE_INVALID",
            "The protected prompt bundle must be a JSON object.",
            path=binding_path,
        )
    system_prompt = payload.get("system_prompt")
    user_prompt = payload.get("user_prompt")
    provider_request_payload = payload.get("provider_request")
    if (
        not isinstance(system_prompt, str)
        or not isinstance(user_prompt, str)
        or not isinstance(provider_request_payload, Mapping)
    ):
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_PROMPT_SHAPE_INVALID",
            "The protected prompt bundle is incomplete.",
            path=binding_path,
        )
    try:
        provider_request = _FrozenProviderRequest.model_validate(provider_request_payload)
    except ValidationError as exc:
        details = tuple(
            ".".join(str(part) for part in item["loc"])
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_REQUEST_SHAPE_INVALID",
            "The protected provider request no longer matches the reviewed shape.",
            path=binding_path,
            details=details,
        ) from exc
    canonical_request = provider_request.model_dump(mode="json")
    if _canonical_json_bytes(canonical_request) != _canonical_json_bytes(provider_request_payload):
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_REQUEST_CANONICALIZATION_MISMATCH",
            "The typed provider request does not preserve the reviewed request bytes.",
            path=binding_path,
        )
    if (
        provider_request.messages[0].content != system_prompt
        or provider_request.messages[1].content != user_prompt
    ):
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_MESSAGE_BINDING_MISMATCH",
            "The protected prompts and reviewed provider request diverged.",
            path=binding_path,
        )
    system_hash = _sha256_bytes(system_prompt.encode("utf-8"))
    user_hash = _sha256_bytes(user_prompt.encode("utf-8"))
    request_hash = _sha256_bytes(_canonical_json_bytes(canonical_request))
    recipe_path = next(
        item.path for item in authorization.bindings if item.path.endswith("prompt_recipe.json")
    )
    recipe = _load_json(repo_root / recipe_path)
    if not isinstance(recipe, Mapping):
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_PROMPT_RECIPE_INVALID",
            "The frozen prompt recipe must be a JSON object.",
            path=recipe_path,
        )
    expected = {
        "system_prompt_sha256": system_hash,
        "user_prompt_sha256": user_hash,
        "provider_request_sha256": request_hash,
    }
    mismatches = tuple(
        f"{field}: expected={recipe.get(field)} observed={observed}"
        for field, observed in expected.items()
        if recipe.get(field) != observed
    )
    if mismatches:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_REQUEST_IDENTITY_MISMATCH",
            "The protected prompt no longer reproduces the reviewed request identity.",
            details=mismatches,
        )
    return provider_request, request_hash


def _terminal_evidence_paths(
    repo_root: Path,
    authorization: ReauthorizationExecutionAuthorization,
) -> tuple[Path, ...]:
    paths = authorization.evidence_paths
    return (
        repo_root / paths.journal_path,
        repo_root / paths.run_records_path,
        repo_root / paths.report_path,
        repo_root / paths.manifest_path,
        repo_root / paths.protected_raw_responses_path,
        repo_root / paths.protected_parsed_responses_path,
    )


def _assert_fresh_execution_boundary(
    repo_root: Path,
    authorization: ReauthorizationExecutionAuthorization,
) -> None:
    existing = tuple(
        str(path) for path in _terminal_evidence_paths(repo_root, authorization) if path.exists()
    )
    if existing:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_ALREADY_EXISTS",
            "Reauthorization evidence already exists; rerun and resume are forbidden.",
            details=existing,
        )


def _credential_available() -> bool:
    value = os.environ.get("GROQ_API_KEY")
    return value is not None and bool(value.strip())


def _installed_sdk_version() -> str:
    try:
        return metadata.version("groq")
    except metadata.PackageNotFoundError as exc:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_SDK_UNAVAILABLE",
            "The Groq SDK is not installed in the active environment.",
        ) from exc


def _build_client(
    authorization: ReauthorizationExecutionAuthorization,
) -> RawCompletionClient:
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key is None or not api_key.strip():
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_GROQ_API_KEY_MISSING",
            "GROQ_API_KEY is not available in the current process.",
        )
    return _SdkRawCompletionClient(
        api_key=api_key,
        timeout_seconds=authorization.timeout_seconds,
    )


def _model_fields_set(value: object) -> set[str]:
    fields: object = getattr(value, "model_fields_set", set())
    if isinstance(fields, set) and all(isinstance(item, str) for item in fields):
        return fields
    return set()


def _state_from_value(
    *,
    field_present: bool,
    value: object,
) -> tuple[ReauthorizationBillingObservationState, int | None]:
    if not field_present:
        return ReauthorizationBillingObservationState.FIELD_ABSENT, None
    if value is None:
        return ReauthorizationBillingObservationState.FIELD_NULL, None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_CACHE_VALUE_INVALID",
            "The billing cache field was present with an invalid value.",
        )
    if value == 0:
        return ReauthorizationBillingObservationState.OBSERVED_ZERO, 0
    return ReauthorizationBillingObservationState.OBSERVED_POSITIVE, value


def _raw_billing_observation(
    payload: Mapping[str, object],
) -> tuple[ReauthorizationBillingObservationState, bool, int | None]:
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        return ReauthorizationBillingObservationState.FIELD_ABSENT, False, None
    if "prompt_tokens_details" not in usage:
        return ReauthorizationBillingObservationState.FIELD_ABSENT, False, None
    details = usage.get("prompt_tokens_details")
    if details is None:
        return ReauthorizationBillingObservationState.FIELD_NULL, True, None
    if not isinstance(details, Mapping):
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_RAW_SHAPE_INVALID",
            "The raw prompt-token details field was not an object or null.",
        )
    present = "cached_tokens" in details
    state, numeric = _state_from_value(
        field_present=present,
        value=details.get("cached_tokens"),
    )
    return state, present, numeric


def _parsed_billing_observation(
    parsed: object,
) -> tuple[ReauthorizationBillingObservationState, bool, int | None]:
    if "usage" not in _model_fields_set(parsed):
        return ReauthorizationBillingObservationState.FIELD_ABSENT, False, None
    usage = getattr(parsed, "usage", None)
    if usage is None:
        return ReauthorizationBillingObservationState.FIELD_NULL, True, None
    if "prompt_tokens_details" not in _model_fields_set(usage):
        return ReauthorizationBillingObservationState.FIELD_ABSENT, False, None
    details = getattr(usage, "prompt_tokens_details", None)
    if details is None:
        return ReauthorizationBillingObservationState.FIELD_NULL, True, None
    present = "cached_tokens" in _model_fields_set(details)
    state, numeric = _state_from_value(
        field_present=present,
        value=getattr(details, "cached_tokens", None),
    )
    return state, present, numeric


def _sleep_until(
    start_time: float,
    offset_seconds: int,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> None:
    remaining = start_time + offset_seconds - monotonic()
    if remaining > 0:
        sleep(remaining)


def _provider_error_code(exc: Exception) -> str:
    name = type(exc).__name__
    if name == "APITimeoutError":
        return "PROVIDER_TIMEOUT"
    if name == "RateLimitError":
        return "PROVIDER_RATE_LIMITED"
    if name == "AuthenticationError":
        return "PROVIDER_AUTHENTICATION_FAILED"
    if name == "PermissionDeniedError":
        return "PROVIDER_PERMISSION_DENIED"
    if name == "NotFoundError":
        return "PROVIDER_MODEL_NOT_AVAILABLE"
    if name == "APIConnectionError":
        return "PROVIDER_CONNECTION_FAILED"
    if name in {"BadRequestError", "ConflictError", "UnprocessableEntityError"}:
        return "PROVIDER_REQUEST_REJECTED"
    return "PROVIDER_UNAVAILABLE"


def _skipped_record(
    *,
    attempt_index: int,
    request_role: str,
    planned_offset_seconds: int,
    request_hash: str,
) -> ReauthorizationAttemptRecord:
    return ReauthorizationAttemptRecord(
        attempt_index=attempt_index,
        request_role=cast(Literal["cold_wire_probe", "warm_wire_probe"], request_role),
        planned_offset_seconds=planned_offset_seconds,
        provider_request_sha256=request_hash,
        status=ReauthorizationAttemptStatus.SKIPPED,
        provider_call_made=False,
        estimated_cost_microusd=0,
    )


def _failed_record(
    *,
    attempt_index: int,
    request_role: str,
    planned_offset_seconds: int,
    observed_offset_ms: int,
    request_hash: str,
    status: ReauthorizationAttemptStatus,
    provider_error_code: str,
    http_status_code: int | None = None,
    raw_body: bytes | None = None,
) -> ReauthorizationAttemptRecord:
    return ReauthorizationAttemptRecord(
        attempt_index=attempt_index,
        request_role=cast(Literal["cold_wire_probe", "warm_wire_probe"], request_role),
        planned_offset_seconds=planned_offset_seconds,
        observed_offset_ms=observed_offset_ms,
        provider_request_sha256=request_hash,
        status=status,
        provider_call_made=True,
        provider_error_code=provider_error_code,
        http_status_code=http_status_code,
        raw_body_sha256=(_sha256_bytes(raw_body) if raw_body is not None else None),
        raw_body_byte_count=(len(raw_body) if raw_body is not None else None),
        estimated_cost_microusd=200,
    )


def _success_record(
    *,
    attempt_index: int,
    request_role: str,
    planned_offset_seconds: int,
    observed_offset_ms: int,
    request_hash: str,
    http_status_code: int,
    raw_body: bytes,
    parsed_bytes: bytes,
    raw_observation: tuple[ReauthorizationBillingObservationState, bool, int | None],
    parsed_observation: tuple[ReauthorizationBillingObservationState, bool, int | None],
    sdk_version: str,
) -> ReauthorizationAttemptRecord:
    raw_state, raw_present, raw_numeric = raw_observation
    parsed_state, parsed_present, parsed_numeric = parsed_observation
    values_match: bool | None = None
    if raw_numeric is not None:
        values_match = raw_numeric == parsed_numeric
    return ReauthorizationAttemptRecord(
        attempt_index=attempt_index,
        request_role=cast(Literal["cold_wire_probe", "warm_wire_probe"], request_role),
        planned_offset_seconds=planned_offset_seconds,
        observed_offset_ms=observed_offset_ms,
        provider_request_sha256=request_hash,
        status=ReauthorizationAttemptStatus.SUCCEEDED,
        provider_call_made=True,
        http_status_code=http_status_code,
        raw_body_sha256=_sha256_bytes(raw_body),
        raw_body_byte_count=len(raw_body),
        parsed_response_sha256=_sha256_bytes(parsed_bytes),
        parsed_response_byte_count=len(parsed_bytes),
        installed_sdk_version=sdk_version,
        raw_billing_observation_state=raw_state,
        raw_billing_field_present=raw_present,
        raw_billing_cached_tokens=raw_numeric,
        parsed_billing_observation_state=parsed_state,
        parsed_billing_field_present=parsed_present,
        parsed_billing_cached_tokens=parsed_numeric,
        raw_parsed_numeric_values_match=values_match,
        estimated_cost_microusd=200,
    )


def _report(
    records: tuple[ReauthorizationAttemptRecord, ReauthorizationAttemptRecord],
) -> ReauthorizationExecutionReport:
    successes = tuple(
        item for item in records if item.status is ReauthorizationAttemptStatus.SUCCEEDED
    )
    provider_errors = sum(
        item.status is ReauthorizationAttemptStatus.PROVIDER_ERROR for item in records
    )
    invalid = sum(
        item.status is ReauthorizationAttemptStatus.OBSERVATION_INVALID for item in records
    )
    skipped = sum(item.status is ReauthorizationAttemptStatus.SKIPPED for item in records)
    raw_numeric = sum(item.raw_billing_cached_tokens is not None for item in successes)
    parsed_numeric = sum(item.parsed_billing_cached_tokens is not None for item in successes)
    raw_absent = sum(
        item.raw_billing_observation_state is ReauthorizationBillingObservationState.FIELD_ABSENT
        for item in successes
    )

    if provider_errors or invalid or len(successes) != 2:
        outcome = GroqCacheTelemetryReauthorizationOutcome.EXECUTION_FAILED
        status = ReauthorizationExecutionStatus.FAILED
    elif any(
        item.raw_billing_cached_tokens is not None and item.parsed_billing_cached_tokens is None
        for item in successes
    ):
        outcome = GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_PRESENT_BUT_PARSED_ABSENT
        status = ReauthorizationExecutionStatus.COMPLETED
    elif raw_numeric > 0 and all(
        item.raw_billing_cached_tokens == item.parsed_billing_cached_tokens
        for item in successes
        if item.raw_billing_cached_tokens is not None
    ):
        outcome = GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_PRESENT_AND_PARSED
        status = ReauthorizationExecutionStatus.COMPLETED
    elif raw_absent == 2:
        outcome = GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_ABSENT
        status = ReauthorizationExecutionStatus.COMPLETED
    else:
        outcome = GroqCacheTelemetryReauthorizationOutcome.EXECUTION_FAILED
        status = ReauthorizationExecutionStatus.FAILED

    provider_calls = sum(item.provider_call_made for item in records)
    return ReauthorizationExecutionReport(
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        execution_id="groq-cache-telemetry-reauthorization-v1",
        status=status,
        outcome=outcome,
        provider_call_count=provider_calls,
        successful_call_count=len(successes),
        provider_error_count=provider_errors,
        observation_invalid_count=invalid,
        skipped_attempt_count=skipped,
        raw_numeric_sample_count=raw_numeric,
        parsed_numeric_sample_count=parsed_numeric,
        raw_absent_sample_count=raw_absent,
        estimated_cost_microusd=provider_calls * 200,
        live_provider_called=provider_calls > 0,
        exact_provider_wire_omission_claim_permitted=(
            outcome is GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_ABSENT
        ),
        sdk_live_parse_defect_claim_permitted=(
            outcome is GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_PRESENT_BUT_PARSED_ABSENT
        ),
        provider_cache_usage_claim_permitted_for_execution=(
            outcome is GroqCacheTelemetryReauthorizationOutcome.WIRE_FIELD_PRESENT_AND_PARSED
        ),
    )


def validate_reauthorization_execution(
    repo_root: Path,
    *,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
) -> ReauthorizationExecutionSummary:
    """Validate activation without reading credentials or calling Groq."""

    authorization, _ = _load_activation(repo_root, execution_root)
    _assert_fresh_execution_boundary(repo_root, authorization)
    return ReauthorizationExecutionSummary(
        command="validate",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        provider_call_count=0,
        execution_completed=False,
        live_provider_called=False,
        credential_checked=False,
        provider_calls_permitted=True,
    )


def live_preflight_reauthorization_execution(
    repo_root: Path,
    *,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
) -> ReauthorizationExecutionSummary:
    """Check credential, protected prompt, and one-time boundary without a provider call."""

    authorization, _ = _load_activation(repo_root, execution_root)
    _assert_fresh_execution_boundary(repo_root, authorization)
    _load_protected_prompt(repo_root, authorization)
    if not _credential_available():
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_GROQ_API_KEY_MISSING",
            "GROQ_API_KEY is not available in the current process.",
        )
    return ReauthorizationExecutionSummary(
        command="live-preflight",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        provider_call_count=0,
        execution_completed=False,
        live_provider_called=False,
        credential_checked=True,
        provider_calls_permitted=True,
    )


def execute_reauthorization(
    repo_root: Path,
    *,
    authorization_id: str,
    confirmation: str,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
    client: RawCompletionClient | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> ReauthorizationExecutionSummary:
    """Execute the active two-call raw-wire authorization exactly once."""

    authorization, policy = _load_activation(repo_root, execution_root)
    if authorization_id != authorization.authorization_id:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_AUTHORIZATION_ID_MISMATCH",
            "The requested authorization ID does not match.",
        )
    if confirmation != authorization.confirmation_phrase:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_CONFIRMATION_MISMATCH",
            "The exact one-time confirmation phrase was not supplied.",
        )
    _assert_fresh_execution_boundary(repo_root, authorization)
    provider_request, request_hash = _load_protected_prompt(
        repo_root,
        authorization,
    )
    if client is None and not _credential_available():
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_GROQ_API_KEY_MISSING",
            "GROQ_API_KEY is not available in the current process.",
        )

    active_client = client or _build_client(authorization)
    sdk_version = _installed_sdk_version()
    records: list[ReauthorizationAttemptRecord] = []
    stopped = False
    start = monotonic()
    paths = authorization.evidence_paths
    journal_path = repo_root / paths.journal_path
    protected_raw_path = repo_root / paths.protected_raw_responses_path
    protected_parsed_path = repo_root / paths.protected_parsed_responses_path
    for path in (journal_path, protected_raw_path, protected_parsed_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)

    try:
        for index, (role, offset) in enumerate(
            zip(policy.request_roles, policy.schedule_offsets_seconds, strict=True)
        ):
            if stopped:
                record = _skipped_record(
                    attempt_index=index,
                    request_role=role,
                    planned_offset_seconds=offset,
                    request_hash=request_hash,
                )
                records.append(record)
                _append_jsonl(journal_path, record)
                continue

            _sleep_until(start, offset, monotonic, sleep)
            observed_offset_ms = round((monotonic() - start) * 1000)
            raw_response: _RawApiResponse | None = None
            raw_body: bytes | None = None
            try:
                raw_response = active_client.create(
                    messages=[
                        message.model_dump(mode="json") for message in provider_request.messages
                    ],
                    model=provider_request.model,
                    max_completion_tokens=provider_request.max_completion_tokens,
                    temperature=provider_request.temperature,
                    stream=provider_request.stream,
                    store=provider_request.store,
                    reasoning_effort=provider_request.reasoning_effort,
                )
                raw_body = bytes(raw_response.http_response.content)
                _append_jsonl(
                    protected_raw_path,
                    {
                        "attempt_index": index,
                        "request_role": role,
                        "raw_body_base64": base64.b64encode(raw_body).decode("ascii"),
                    },
                )
                raw_payload = json.loads(raw_body)
                if not isinstance(raw_payload, Mapping):
                    raise ReauthorizationExecutionError(
                        "GROQ_REAUTHORIZATION_EXECUTION_RAW_SHAPE_INVALID",
                        "The raw provider response was not a JSON object.",
                    )
                parsed = raw_response.parse()
                parsed_payload = parsed.model_dump(
                    mode="json",
                    exclude_none=False,
                    exclude_unset=False,
                )
                parsed_bytes = _canonical_json_bytes(parsed_payload)
                _append_jsonl(
                    protected_parsed_path,
                    {
                        "attempt_index": index,
                        "request_role": role,
                        "parsed_response": parsed_payload,
                    },
                )
                raw_observation = _raw_billing_observation(cast(Mapping[str, object], raw_payload))
                parsed_observation = _parsed_billing_observation(parsed)
                record = _success_record(
                    attempt_index=index,
                    request_role=role,
                    planned_offset_seconds=offset,
                    observed_offset_ms=observed_offset_ms,
                    request_hash=request_hash,
                    http_status_code=raw_response.http_response.status_code,
                    raw_body=raw_body,
                    parsed_bytes=parsed_bytes,
                    raw_observation=raw_observation,
                    parsed_observation=parsed_observation,
                    sdk_version=sdk_version,
                )
            except ReauthorizationExecutionError as exc:
                _append_jsonl(
                    protected_parsed_path,
                    {
                        "attempt_index": index,
                        "request_role": role,
                        "observation_error_code": exc.error_code,
                    },
                )
                record = _failed_record(
                    attempt_index=index,
                    request_role=role,
                    planned_offset_seconds=offset,
                    observed_offset_ms=observed_offset_ms,
                    request_hash=request_hash,
                    status=ReauthorizationAttemptStatus.OBSERVATION_INVALID,
                    provider_error_code=exc.error_code,
                    http_status_code=(
                        raw_response.http_response.status_code if raw_response is not None else None
                    ),
                    raw_body=raw_body,
                )
                stopped = True
            except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
                _append_jsonl(
                    protected_parsed_path,
                    {
                        "attempt_index": index,
                        "request_role": role,
                        "observation_error_code": type(exc).__name__,
                    },
                )
                record = _failed_record(
                    attempt_index=index,
                    request_role=role,
                    planned_offset_seconds=offset,
                    observed_offset_ms=observed_offset_ms,
                    request_hash=request_hash,
                    status=ReauthorizationAttemptStatus.OBSERVATION_INVALID,
                    provider_error_code="GROQ_REAUTHORIZATION_OBSERVATION_INVALID",
                    http_status_code=(
                        raw_response.http_response.status_code if raw_response is not None else None
                    ),
                    raw_body=raw_body,
                )
                stopped = True
            except Exception as exc:
                exception_name = type(exc).__name__
                provider_error_code = (
                    _provider_error_code(exc)
                    if exception_name in _ALLOWED_PROVIDER_EXCEPTION_CLASSES
                    else "GROQ_REAUTHORIZATION_UNSUPPORTED_PROVIDER_EXCEPTION"
                )
                record = _failed_record(
                    attempt_index=index,
                    request_role=role,
                    planned_offset_seconds=offset,
                    observed_offset_ms=observed_offset_ms,
                    request_hash=request_hash,
                    status=ReauthorizationAttemptStatus.PROVIDER_ERROR,
                    provider_error_code=provider_error_code,
                )
                stopped = True
            finally:
                if raw_response is not None:
                    raw_response.close()

            records.append(record)
            _append_jsonl(journal_path, record)
    finally:
        active_client.close()

    record_set = ReauthorizationRunRecordSet(
        authorization_id=authorization.authorization_id,
        execution_id=authorization.execution_id,
        records=cast(
            tuple[ReauthorizationAttemptRecord, ReauthorizationAttemptRecord],
            tuple(records),
        ),
    )
    report = _report(record_set.records)
    run_records_path = repo_root / paths.run_records_path
    report_path = repo_root / paths.report_path
    _write_json(run_records_path, record_set)
    _write_json(report_path, report)

    manifest = ReauthorizationExecutionManifest(
        authorization_id=authorization.authorization_id,
        authorization_sha256=_sha256_file(repo_root / paths.authorization_path),
        runtime_policy_sha256=_sha256_file(repo_root / paths.runtime_policy_path),
        activation_manifest_sha256=_sha256_file(repo_root / paths.activation_manifest_path),
        journal_sha256=_sha256_file(journal_path),
        run_records_sha256=_sha256_file(run_records_path),
        report_sha256=_sha256_file(report_path),
        protected_raw_responses_sha256=_sha256_file(protected_raw_path),
        protected_parsed_responses_sha256=_sha256_file(protected_parsed_path),
        live_provider_called=report.live_provider_called,
    )
    _write_json(repo_root / paths.manifest_path, manifest)
    return ReauthorizationExecutionSummary(
        command="run",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        provider_call_count=report.provider_call_count,
        execution_completed=True,
        live_provider_called=report.live_provider_called,
        credential_checked=client is None,
        provider_calls_permitted=True,
    )


def verify_reauthorization_execution(
    repo_root: Path,
    *,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
) -> ReauthorizationExecutionSummary:
    """Verify terminal public and protected evidence after execution."""

    authorization, _ = _load_activation(repo_root, execution_root)
    paths = authorization.evidence_paths
    record_set = _load_model(
        repo_root / paths.run_records_path,
        ReauthorizationRunRecordSet,
    )
    report = _load_model(
        repo_root / paths.report_path,
        ReauthorizationExecutionReport,
    )
    manifest = _load_model(
        repo_root / paths.manifest_path,
        ReauthorizationExecutionManifest,
    )
    journal_path = repo_root / paths.journal_path
    try:
        lines = [
            line for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
    except OSError as exc:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_JOURNAL_READ_FAILED",
            "The public journal could not be read.",
            path=str(journal_path),
        ) from exc
    if len(lines) != 2:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_JOURNAL_COUNT_MISMATCH",
            "The public journal must contain exactly two records.",
            path=str(journal_path),
        )
    journal_records = tuple(
        ReauthorizationAttemptRecord.model_validate_json(line) for line in lines
    )
    if journal_records != record_set.records:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_JOURNAL_MISMATCH",
            "Journal and run records do not reconcile.",
        )

    checks = {
        "authorization_sha256": _sha256_file(repo_root / paths.authorization_path),
        "runtime_policy_sha256": _sha256_file(repo_root / paths.runtime_policy_path),
        "activation_manifest_sha256": _sha256_file(repo_root / paths.activation_manifest_path),
        "journal_sha256": _sha256_file(journal_path),
        "run_records_sha256": _sha256_file(repo_root / paths.run_records_path),
        "report_sha256": _sha256_file(repo_root / paths.report_path),
        "protected_raw_responses_sha256": _sha256_file(
            repo_root / paths.protected_raw_responses_path
        ),
        "protected_parsed_responses_sha256": _sha256_file(
            repo_root / paths.protected_parsed_responses_path
        ),
    }
    mismatches = tuple(
        f"{field}: expected={getattr(manifest, field)} observed={observed}"
        for field, observed in checks.items()
        if getattr(manifest, field) != observed
    )
    if mismatches:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_HASH_MISMATCH",
            "Reauthorization execution evidence no longer matches.",
            details=mismatches,
        )
    if _report(record_set.records) != report:
        raise ReauthorizationExecutionError(
            "GROQ_REAUTHORIZATION_EXECUTION_REPORT_MISMATCH",
            "The reauthorization report did not reproduce.",
        )
    return ReauthorizationExecutionSummary(
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
    parser.add_argument("--execution-root", type=Path, default=_DEFAULT_EXECUTION_ROOT)
    parser.add_argument("--authorization-id")
    parser.add_argument("--confirm")
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "validate":
            result = validate_reauthorization_execution(
                repo_root,
                execution_root=args.execution_root,
            )
        elif args.command == "live-preflight":
            result = live_preflight_reauthorization_execution(
                repo_root,
                execution_root=args.execution_root,
            )
        elif args.command == "run":
            result = execute_reauthorization(
                repo_root,
                authorization_id=args.authorization_id or "",
                confirmation=args.confirm or "",
                execution_root=args.execution_root,
            )
        else:
            result = verify_reauthorization_execution(
                repo_root,
                execution_root=args.execution_root,
            )
    except ReauthorizationExecutionError as exc:
        envelope = ReauthorizationExecutionErrorEnvelope(
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
