"""Validate and smoke-test Groq and Ollama provider calibration boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from auragateway.contracts.provider import (
    ProtectedPromptSummary,
    ProviderInvocationRequest,
    ProviderName,
)
from auragateway.contracts.telemetry import (
    CachedInputDetailTelemetry,
    ClaimDecision,
    ClaimKind,
    LocalPromptEvaluationTelemetry,
    NormalizedTelemetry,
    ProviderTelemetryPayload,
    TelemetryReasonCode,
    TelemetrySufficiencyReport,
)
from auragateway.providers.base import (
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderPrompt,
    ProviderCall,
)
from auragateway.providers.groq import (
    GROQ_ADAPTER_VERSION,
    GROQ_MODEL_ALIAS,
    GROQ_MODEL_ID,
    GroqProviderAdapter,
)
from auragateway.providers.ollama import (
    OLLAMA_ADAPTER_VERSION,
    OLLAMA_DEFAULT_ENDPOINT,
    OLLAMA_MODEL_ALIAS,
    OLLAMA_MODEL_ID,
    OllamaProviderAdapter,
)
from auragateway.telemetry.normalize import normalize_telemetry
from auragateway.telemetry.sufficiency import assess_telemetry_sufficiency

_DEFAULT_CONFIG = Path("data/provider_fixtures/live-calibration/config.json")
_DEFAULT_MANIFEST = Path("data/provider_fixtures/live-calibration/manifest.json")
_DEFAULT_GROQ_SNAPSHOTS = Path("data/provider_fixtures/live-calibration/groq_snapshots.json")
_DEFAULT_OLLAMA_SNAPSHOTS = Path("data/provider_fixtures/live-calibration/ollama_snapshots.json")
_DEFAULT_PREFIX = Path("data/provider_fixtures/live-calibration/stable_prefix.txt")


class ProviderCalibrationError(Exception):
    """Expected calibration failure with bounded, content-free diagnostics."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class ProviderCalibrationErrorEnvelope(BaseModel):
    """Safe CLI error output that excludes prompts and raw provider payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class ProviderCalibrationConfig(BaseModel):
    """Bounded deterministic and live provider-calibration configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    config_id: str
    documentation_date: str
    static_prefix_path: str
    static_prefix_fingerprint: str
    groq_model_id: str
    groq_model_alias: str
    groq_input_token_estimate: int = Field(gt=0, le=3_000)
    groq_output_token_budget: int = Field(gt=0, le=64)
    groq_call_count: int = Field(gt=0, le=2)
    groq_timeout_seconds: float = Field(gt=0, le=120)
    ollama_model_id: str
    ollama_model_alias: str
    ollama_endpoint: str
    ollama_input_token_estimate: int = Field(gt=0, le=3_000)
    ollama_output_token_budget: int = Field(gt=0, le=64)
    ollama_call_count: int = Field(gt=0, le=2)
    ollama_timeout_seconds: float = Field(gt=0, le=300)
    free_plan_only: bool
    raw_payload_persistence_permitted: bool = False
    measured_execution_permitted: bool = False

    @field_validator("static_prefix_path")
    @classmethod
    def validate_prefix_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("static_prefix_path must be repository-relative")
        if not value.startswith("data/provider_fixtures/live-calibration/"):
            raise ValueError("static_prefix_path must remain in the calibration fixture directory")
        return value

    @model_validator(mode="after")
    def validate_frozen_choices(self) -> ProviderCalibrationConfig:
        if self.groq_model_id != GROQ_MODEL_ID or self.groq_model_alias != GROQ_MODEL_ALIAS:
            raise ValueError("Groq calibration identity must match the selected model boundary")
        if self.ollama_model_id != OLLAMA_MODEL_ID or self.ollama_model_alias != OLLAMA_MODEL_ALIAS:
            raise ValueError("Ollama calibration identity must match the installed local model")
        if self.ollama_endpoint != OLLAMA_DEFAULT_ENDPOINT:
            raise ValueError("Ollama calibration must use the local generate endpoint")
        if not self.free_plan_only:
            raise ValueError("Groq calibration must remain free-plan only")
        if self.raw_payload_persistence_permitted or self.measured_execution_permitted:
            raise ValueError("calibration cannot authorize raw persistence or benchmark execution")
        return self


class ProviderCalibrationManifest(BaseModel):
    """Immutable identities for deterministic provider-calibration assets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str
    config_id: str
    config_path: str
    config_sha256: str
    groq_snapshots_path: str
    groq_snapshots_sha256: str
    ollama_snapshots_path: str
    ollama_snapshots_sha256: str
    static_prefix_path: str
    static_prefix_sha256: str
    groq_adapter_version: str
    ollama_adapter_version: str
    measured_execution_permitted: bool = False

    @field_validator(
        "config_sha256",
        "groq_snapshots_sha256",
        "ollama_snapshots_sha256",
        "static_prefix_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("calibration manifest hashes must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_versions(self) -> ProviderCalibrationManifest:
        if self.groq_adapter_version != GROQ_ADAPTER_VERSION:
            raise ValueError("Groq adapter version does not match the manifest")
        if self.ollama_adapter_version != OLLAMA_ADAPTER_VERSION:
            raise ValueError("Ollama adapter version does not match the manifest")
        if self.measured_execution_permitted:
            raise ValueError("calibration manifests cannot permit benchmark execution")
        return self


class GroqSnapshot(BaseModel):
    """Typed deterministic Groq response fields used by adapter extraction tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_id: str
    output_text: str = Field(min_length=1)
    prompt_tokens: int = Field(gt=0)
    cached_tokens: int = Field(ge=0)
    completion_tokens: int = Field(gt=0)
    total_time_seconds: float = Field(gt=0)


class GroqSnapshotSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    model_id: str
    snapshots: tuple[GroqSnapshot, ...] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_set(self) -> GroqSnapshotSet:
        if self.model_id != GROQ_MODEL_ID:
            raise ValueError("Groq snapshots must use the configured model")
        if len({item.fixture_id for item in self.snapshots}) != len(self.snapshots):
            raise ValueError("Groq snapshot fixture IDs must be unique")
        return self


class OllamaSnapshot(BaseModel):
    """Typed deterministic Ollama fields used by local timing extraction tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_id: str
    output_text: str = Field(min_length=1)
    total_duration_ns: int = Field(gt=0)
    prompt_eval_count: int = Field(gt=0)
    prompt_eval_duration_ns: int = Field(gt=0)
    eval_count: int = Field(gt=0)


class OllamaSnapshotSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    model_id: str
    snapshots: tuple[OllamaSnapshot, ...] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_set(self) -> OllamaSnapshotSet:
        if self.model_id != OLLAMA_MODEL_ID:
            raise ValueError("Ollama snapshots must use the configured model")
        if len({item.fixture_id for item in self.snapshots}) != len(self.snapshots):
            raise ValueError("Ollama snapshot fixture IDs must be unique")
        return self


class CalibrationCallEvidence(BaseModel):
    """Sanitized evidence for one deterministic or live provider call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    fixture_id: str
    provider: ProviderName
    model_alias: str
    prompt_summary: ProtectedPromptSummary
    output_sha256: str
    telemetry: ProviderTelemetryPayload
    normalized_telemetry: NormalizedTelemetry
    sufficiency: TelemetrySufficiencyReport


class ProviderCalibrationReport(BaseModel):
    """Sanitized calibration report; never contains prompt or raw response content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    mode: Literal["deterministic", "groq_live", "ollama_live"]
    status: Literal["passed", "failed"]
    config_id: str
    calls: tuple[CalibrationCallEvidence, ...] = Field(min_length=2)
    provider_cached_tokens_observed: bool
    local_prompt_timing_observed: bool
    raw_payload_persisted: bool = False
    measured_execution_permitted: bool = False

    @model_validator(mode="after")
    def validate_safety(self) -> ProviderCalibrationReport:
        if self.raw_payload_persisted or self.measured_execution_permitted:
            raise ValueError("calibration reports cannot persist raw payloads or permit execution")
        return self


class ProviderCalibrationSummary(BaseModel):
    """Compact CLI result for one calibration action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str
    calibration_passed: bool
    call_count: int
    provider_cached_tokens_observed: bool
    local_prompt_timing_observed: bool
    report_path: str | None = None
    measured_execution_permitted: bool = False


class _SnapshotGroqResponse:
    def __init__(self, snapshot: GroqSnapshot) -> None:
        self._snapshot = snapshot

    def model_dump(self) -> dict[str, object]:
        return {
            "model": GROQ_MODEL_ID,
            "choices": [{"message": {"content": self._snapshot.output_text}}],
            "usage": {
                "prompt_tokens": self._snapshot.prompt_tokens,
                "completion_tokens": self._snapshot.completion_tokens,
                "total_time": self._snapshot.total_time_seconds,
                "prompt_tokens_details": {"cached_tokens": self._snapshot.cached_tokens},
            },
        }


class _SequentialGroqClient:
    def __init__(self, snapshots: tuple[GroqSnapshot, ...]) -> None:
        self._snapshots = snapshots
        self._index = 0

    def create(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        model: str,
        max_completion_tokens: int,
        temperature: float,
        stream: bool,
        store: bool,
        reasoning_effort: str,
    ) -> _SnapshotGroqResponse:
        del (
            messages,
            max_completion_tokens,
            temperature,
            stream,
            store,
            reasoning_effort,
        )
        if model != GROQ_MODEL_ID or self._index >= len(self._snapshots):
            raise RuntimeError("deterministic Groq snapshot request mismatch")
        snapshot = self._snapshots[self._index]
        self._index += 1
        return _SnapshotGroqResponse(snapshot)


class _SequentialOllamaTransport:
    def __init__(self, snapshots: tuple[OllamaSnapshot, ...]) -> None:
        self._snapshots = snapshots
        self._index = 0

    def generate(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        del payload, timeout_seconds
        if endpoint != OLLAMA_DEFAULT_ENDPOINT or self._index >= len(self._snapshots):
            raise RuntimeError("deterministic Ollama snapshot request mismatch")
        snapshot = self._snapshots[self._index]
        self._index += 1
        return {
            "model": OLLAMA_MODEL_ID,
            "response": snapshot.output_text,
            "done": True,
            "done_reason": "stop",
            "total_duration": snapshot.total_duration_ns,
            "prompt_eval_count": snapshot.prompt_eval_count,
            "prompt_eval_duration": snapshot.prompt_eval_duration_ns,
            "eval_count": snapshot.eval_count,
        }


ModelT = TypeVar("ModelT", bound=BaseModel)


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_model(path: Path, model_type: type[ModelT], code: str) -> ModelT:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProviderCalibrationError(
            f"{code}_NOT_FOUND",
            "Required provider-calibration artifact was not found.",
            str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProviderCalibrationError(
            f"{code}_INVALID_JSON",
            "Provider-calibration artifact is not valid JSON.",
            str(path),
        ) from exc
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise ProviderCalibrationError(
            f"{code}_VALIDATION_FAILED",
            "Provider-calibration artifact failed typed validation.",
            str(path),
            _validation_messages(exc),
        ) from exc


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_manifest(repo_root: Path) -> ProviderCalibrationManifest:
    manifest = _load_model(
        repo_root / _DEFAULT_MANIFEST,
        ProviderCalibrationManifest,
        "CALIBRATION_MANIFEST",
    )
    checks = (
        (manifest.config_path, manifest.config_sha256),
        (manifest.groq_snapshots_path, manifest.groq_snapshots_sha256),
        (manifest.ollama_snapshots_path, manifest.ollama_snapshots_sha256),
        (manifest.static_prefix_path, manifest.static_prefix_sha256),
    )
    for relative_path, expected_hash in checks:
        path = repo_root / relative_path
        if not path.exists() or _sha256_path(path) != expected_hash:
            raise ProviderCalibrationError(
                "CALIBRATION_ASSET_HASH_MISMATCH",
                "Provider-calibration asset does not match the immutable manifest.",
                str(path),
            )
    return manifest


def _load_prefix(path: Path) -> str:
    try:
        prefix = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProviderCalibrationError(
            "CALIBRATION_PREFIX_NOT_FOUND",
            "The synthetic calibration prefix was not found.",
            str(path),
        ) from exc
    if len(prefix.encode("utf-8")) < 6_000:
        raise ProviderCalibrationError(
            "CALIBRATION_PREFIX_TOO_SHORT",
            "The synthetic prefix is too short for meaningful cache calibration.",
            str(path),
        )
    return prefix


def _invocation(
    config: ProviderCalibrationConfig,
    provider: ProviderName,
    fixture_id: str,
    turn_index: int,
    prefix: str,
) -> LiveProviderInvocation:
    if provider is ProviderName.GROQ:
        model_alias = config.groq_model_alias
        input_tokens = config.groq_input_token_estimate
        output_budget = config.groq_output_token_budget
        timeout_seconds = config.groq_timeout_seconds
    else:
        model_alias = config.ollama_model_alias
        input_tokens = config.ollama_input_token_estimate
        output_budget = config.ollama_output_token_budget
        timeout_seconds = config.ollama_timeout_seconds
    user_prompt = (
        "Synthetic calibration turn "
        f"{turn_index}: return exactly the token READY-{turn_index} and no other text."
    )
    request = ProviderInvocationRequest(
        request_id=f"{provider.value}-calibration-request-{turn_index}",
        fixture_id=fixture_id,
        provider=provider,
        model_alias=model_alias,
        static_prefix_fingerprint=config.static_prefix_fingerprint,
        input_token_count=input_tokens,
        output_token_budget=output_budget,
    )
    return LiveProviderInvocation(
        request=request,
        prompt=ProtectedProviderPrompt(system_prompt=prefix, user_prompt=user_prompt),
        timeout_seconds=timeout_seconds,
    )


def _call_evidence(
    call: ProviderCall, invocation: LiveProviderInvocation
) -> CalibrationCallEvidence:
    output_sha256 = call.result.output_sha256
    if output_sha256 is None:
        raise ProviderCalibrationError(
            "CALIBRATION_OUTPUT_DIGEST_MISSING",
            "Provider calibration call did not produce an output digest.",
        )
    normalized = normalize_telemetry(call.telemetry)
    sufficiency = assess_telemetry_sufficiency(normalized)
    return CalibrationCallEvidence(
        request_id=call.result.request_id,
        fixture_id=call.telemetry.fixture_id,
        provider=call.result.provider,
        model_alias=call.result.model_alias,
        prompt_summary=invocation.prompt.summary(),
        output_sha256=output_sha256,
        telemetry=call.telemetry,
        normalized_telemetry=normalized,
        sufficiency=sufficiency,
    )


def _report(
    mode: Literal["deterministic", "groq_live", "ollama_live"],
    config: ProviderCalibrationConfig,
    calls: tuple[CalibrationCallEvidence, ...],
) -> ProviderCalibrationReport:
    provider_cached_tokens_observed = any(
        isinstance(item.telemetry, CachedInputDetailTelemetry)
        and item.telemetry.cached_input_tokens is not None
        and item.telemetry.cached_input_tokens > 0
        for item in calls
    )
    local_prompt_timing_observed = any(
        isinstance(item.telemetry, LocalPromptEvaluationTelemetry)
        and item.telemetry.prompt_eval_duration_ms is not None
        and item.telemetry.prompt_eval_duration_ms > 0
        for item in calls
    )
    groq_calls = tuple(item for item in calls if item.provider is ProviderName.GROQ)
    ollama_calls = tuple(item for item in calls if item.provider is ProviderName.OLLAMA)
    groq_claims_valid = bool(groq_calls) and all(
        item.sufficiency.decision_for(ClaimKind.CACHE_EFFICIENCY).decision
        is ClaimDecision.PERMITTED
        for item in groq_calls
    )
    groq_live_evidence_valid = bool(groq_calls) and all(
        isinstance(item.telemetry, CachedInputDetailTelemetry)
        and item.telemetry.input_tokens is not None
        and item.telemetry.output_tokens is not None
        and item.telemetry.total_duration_ms is not None
        and (
            (cache_decision := item.sufficiency.decision_for(ClaimKind.CACHE_EFFICIENCY)).decision
            is ClaimDecision.PERMITTED
            or (
                cache_decision.decision is ClaimDecision.BLOCKED
                and cache_decision.reason_code is TelemetryReasonCode.CACHE_EVIDENCE_UNAVAILABLE
                and cache_decision.missing_fields == ("provider_cached_input_tokens",)
                and not cache_decision.invalid_fields
            )
        )
        for item in groq_calls
    )
    ollama_claims_blocked = bool(ollama_calls) and all(
        item.sufficiency.decision_for(ClaimKind.CACHE_EFFICIENCY).decision is ClaimDecision.BLOCKED
        for item in ollama_calls
    )
    if mode == "deterministic":
        passed = groq_claims_valid and ollama_claims_blocked
    elif mode == "groq_live":
        passed = groq_live_evidence_valid
    else:
        passed = ollama_claims_blocked and local_prompt_timing_observed
    status = "passed" if passed else "failed"
    return ProviderCalibrationReport(
        mode=mode,
        status=status,
        config_id=config.config_id,
        calls=calls,
        provider_cached_tokens_observed=provider_cached_tokens_observed,
        local_prompt_timing_observed=local_prompt_timing_observed,
    )


def _summary(
    report: ProviderCalibrationReport, report_path: Path | None
) -> ProviderCalibrationSummary:
    return ProviderCalibrationSummary(
        mode=report.mode,
        calibration_passed=report.status == "passed",
        call_count=len(report.calls),
        provider_cached_tokens_observed=report.provider_cached_tokens_observed,
        local_prompt_timing_observed=report.local_prompt_timing_observed,
        report_path=str(report_path) if report_path is not None else None,
    )


def _write_live_report(repo_root: Path, report: ProviderCalibrationReport) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = repo_root / ".local/provider-calibration" / timestamp
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / f"{report.mode}-report.json"
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def validate_calibration(repo_root: Path) -> ProviderCalibrationSummary:
    """Replay deterministic snapshots through both live adapter boundaries."""

    manifest = _verify_manifest(repo_root)
    config = _load_model(
        repo_root / _DEFAULT_CONFIG, ProviderCalibrationConfig, "CALIBRATION_CONFIG"
    )
    if manifest.config_id != config.config_id:
        raise ProviderCalibrationError(
            "CALIBRATION_MANIFEST_CONFIG_MISMATCH",
            "Calibration manifest and configuration identities do not match.",
        )
    prefix = _load_prefix(repo_root / config.static_prefix_path)
    groq_snapshots = _load_model(
        repo_root / _DEFAULT_GROQ_SNAPSHOTS,
        GroqSnapshotSet,
        "GROQ_SNAPSHOTS",
    )
    ollama_snapshots = _load_model(
        repo_root / _DEFAULT_OLLAMA_SNAPSHOTS,
        OllamaSnapshotSet,
        "OLLAMA_SNAPSHOTS",
    )
    groq_adapter = GroqProviderAdapter(_SequentialGroqClient(groq_snapshots.snapshots))
    ollama_adapter = OllamaProviderAdapter(_SequentialOllamaTransport(ollama_snapshots.snapshots))
    calls: list[CalibrationCallEvidence] = []
    for index, groq_snapshot in enumerate(groq_snapshots.snapshots, start=1):
        invocation = _invocation(config, ProviderName.GROQ, groq_snapshot.fixture_id, index, prefix)
        calls.append(_call_evidence(groq_adapter.invoke(invocation), invocation))
    for index, ollama_snapshot in enumerate(ollama_snapshots.snapshots, start=1):
        invocation = _invocation(
            config, ProviderName.OLLAMA, ollama_snapshot.fixture_id, index, prefix
        )
        calls.append(_call_evidence(ollama_adapter.invoke(invocation), invocation))
    report = _report("deterministic", config, tuple(calls))
    if report.status != "passed" or not report.provider_cached_tokens_observed:
        raise ProviderCalibrationError(
            "DETERMINISTIC_PROVIDER_CALIBRATION_FAILED",
            "Deterministic provider calibration did not satisfy the typed evidence controls.",
        )
    return _summary(report, None)


def run_groq_smoke(repo_root: Path) -> ProviderCalibrationSummary:
    """Run two free-plan-only Groq calls using one exact synthetic prefix."""

    manifest = _verify_manifest(repo_root)
    config = _load_model(
        repo_root / _DEFAULT_CONFIG, ProviderCalibrationConfig, "CALIBRATION_CONFIG"
    )
    if manifest.config_id != config.config_id:
        raise ProviderCalibrationError(
            "CALIBRATION_MANIFEST_CONFIG_MISMATCH",
            "Calibration manifest and configuration identities do not match.",
        )
    prefix = _load_prefix(repo_root / config.static_prefix_path)
    adapter = GroqProviderAdapter()
    calls: list[CalibrationCallEvidence] = []
    for index in range(1, config.groq_call_count + 1):
        invocation = _invocation(
            config,
            ProviderName.GROQ,
            f"groq-live-turn-{index}",
            index,
            prefix,
        )
        try:
            calls.append(_call_evidence(adapter.invoke(invocation), invocation))
        except LiveProviderError as exc:
            raise ProviderCalibrationError(
                exc.error_code.value,
                exc.safe_message,
                details=(f"retryable={str(exc.retryable).lower()}",),
            ) from exc
    report = _report("groq_live", config, tuple(calls))
    if report.status != "passed":
        raise ProviderCalibrationError(
            "GROQ_LIVE_CALIBRATION_FAILED",
            "Groq live calibration did not produce sufficient typed provider evidence.",
        )
    report_path = _write_live_report(repo_root, report)
    return _summary(report, report_path)


def run_ollama_smoke(repo_root: Path) -> ProviderCalibrationSummary:
    """Run two local Ollama calls and retain prompt-evaluation timing only."""

    manifest = _verify_manifest(repo_root)
    config = _load_model(
        repo_root / _DEFAULT_CONFIG, ProviderCalibrationConfig, "CALIBRATION_CONFIG"
    )
    if manifest.config_id != config.config_id:
        raise ProviderCalibrationError(
            "CALIBRATION_MANIFEST_CONFIG_MISMATCH",
            "Calibration manifest and configuration identities do not match.",
        )
    prefix = _load_prefix(repo_root / config.static_prefix_path)
    adapter = OllamaProviderAdapter(endpoint=config.ollama_endpoint)
    calls: list[CalibrationCallEvidence] = []
    for index in range(1, config.ollama_call_count + 1):
        invocation = _invocation(
            config,
            ProviderName.OLLAMA,
            f"ollama-live-turn-{index}",
            index,
            prefix,
        )
        try:
            calls.append(_call_evidence(adapter.invoke(invocation), invocation))
        except LiveProviderError as exc:
            raise ProviderCalibrationError(
                exc.error_code.value,
                exc.safe_message,
                details=(f"retryable={str(exc.retryable).lower()}",),
            ) from exc
    report = _report("ollama_live", config, tuple(calls))
    if report.status != "passed" or not report.local_prompt_timing_observed:
        raise ProviderCalibrationError(
            "OLLAMA_LIVE_CALIBRATION_FAILED",
            "Ollama live calibration did not produce local prompt-evaluation timing.",
        )
    report_path = _write_live_report(repo_root, report)
    return _summary(report, report_path)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "groq-smoke", "ollama-smoke"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run deterministic validation or one bounded live smoke calibration."""

    args = _parse_args(argv)
    try:
        if args.command == "validate":
            summary = validate_calibration(args.repo_root)
        elif args.command == "groq-smoke":
            summary = run_groq_smoke(args.repo_root)
        else:
            summary = run_ollama_smoke(args.repo_root)
    except ProviderCalibrationError as exc:
        envelope = ProviderCalibrationErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
