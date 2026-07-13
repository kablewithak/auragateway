"""Provider-facing output normalization and bounded live-call pacing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from auragateway.contracts.episodes import (
    AnswerDecisionOutput,
    ClarifyDecisionOutput,
    EscalateDecisionOutput,
    EscalationReasonCode,
    TerminalDecisionOutput,
    TerminalReasonCode,
)
from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationStatus,
)
from auragateway.providers.base import (
    LiveProviderAdapter,
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderOutput,
    ProviderCall,
)

_FIELD_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_TERMINAL_OUTPUT_ADAPTER: TypeAdapter[TerminalDecisionOutput] = TypeAdapter(TerminalDecisionOutput)
_BATCH_02_POLICY_ID = "live-development-batch-02-runtime-policy-v1"
_BATCH_02_AUTHORIZATION_ID = "live-development-batch-02-auth-v1"
_BATCH_03_POLICY_ID = "live-development-batch-03-runtime-policy-v1"
_BATCH_03_AUTHORIZATION_ID = "live-development-batch-03-auth-v1"
_BATCH_04_POLICY_ID = "live-development-batch-04-runtime-policy-v1"
_BATCH_04_AUTHORIZATION_ID = "live-development-batch-04-auth-v1"
_BATCH_05_POLICY_ID = "live-development-batch-05-runtime-policy-v1"
_BATCH_05_AUTHORIZATION_ID = "live-development-batch-05-auth-v1"
_BATCH_06_POLICY_ID = "live-development-batch-06-runtime-policy-v1"
_BATCH_06_AUTHORIZATION_ID = "live-development-batch-06-auth-v1"
_POLICY_AUTHORIZATION_PAIRS = {
    _BATCH_02_POLICY_ID: _BATCH_02_AUTHORIZATION_ID,
    _BATCH_03_POLICY_ID: _BATCH_03_AUTHORIZATION_ID,
    _BATCH_04_POLICY_ID: _BATCH_04_AUTHORIZATION_ID,
    _BATCH_05_POLICY_ID: _BATCH_05_AUTHORIZATION_ID,
    _BATCH_06_POLICY_ID: _BATCH_06_AUTHORIZATION_ID,
}


class CompilerConfidenceBand(StrEnum):
    """Confidence labels exposed by the frozen provider-facing compiler schema."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OutputNormalizationPath(StrEnum):
    """How one protected provider output reached the canonical terminal contract."""

    CANONICAL_DIRECT = "canonical_direct"
    COMPILER_SCHEMA_V1 = "compiler_schema_v1"
    REJECTED = "rejected"


class CompilerTerminalDecision(BaseModel):
    """Exact terminal-decision shape declared by the frozen compiler specification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal["answer", "clarify", "escalate", "refuse"]
    answer: str | None = None
    citations: tuple[str, ...]
    missing_information: tuple[str, ...]
    escalation_reason: str | None = None
    confidence_band: CompilerConfidenceBand

    @model_validator(mode="after")
    def validate_decision_shape(self) -> CompilerTerminalDecision:
        answer = (self.answer or "").strip()
        escalation_reason = (self.escalation_reason or "").strip()
        if self.decision == "answer" and not answer:
            raise ValueError("answer decisions require non-empty answer text")
        if self.decision == "clarify" and not self.missing_information:
            raise ValueError("clarify decisions require missing_information")
        if self.decision == "escalate" and (not escalation_reason or not self.citations):
            raise ValueError(
                "escalate decisions require escalation_reason and supporting citations"
            )
        if self.decision == "refuse":
            raise ValueError(
                "compiler-schema refuse outputs lack the canonical refusal reason "
                "and safe alternative"
            )
        return self


class NormalizedProtectedOutput(BaseModel):
    """Canonicalized output plus protected reconciliation metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    normalization_path: OutputNormalizationPath
    canonical_text: str = Field(min_length=2)
    raw_output_sha256: str
    canonical_output_sha256: str


class LiveBatchRuntimePolicy(BaseModel):
    """Bounded runtime policy for corrective live-development batches."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: Literal[
        "live-development-batch-02-runtime-policy-v1",
        "live-development-batch-03-runtime-policy-v1",
        "live-development-batch-04-runtime-policy-v1",
        "live-development-batch-05-runtime-policy-v1",
        "live-development-batch-06-runtime-policy-v1",
    ] = "live-development-batch-02-runtime-policy-v1"
    authorization_id: Literal[
        "live-development-batch-02-auth-v1",
        "live-development-batch-03-auth-v1",
        "live-development-batch-04-auth-v1",
        "live-development-batch-05-auth-v1",
        "live-development-batch-06-auth-v1",
    ] = "live-development-batch-02-auth-v1"
    output_normalization_profile: Literal["compiler-to-terminal-v1"] = "compiler-to-terminal-v1"
    minimum_call_interval_seconds: float = Field(ge=0, le=120)
    rate_limit_cooldown_seconds: float = Field(ge=0, le=300)
    maximum_cumulative_sleep_seconds: float = Field(gt=0, le=1800)

    @model_validator(mode="after")
    def validate_policy_authorization_pair(self) -> LiveBatchRuntimePolicy:
        expected_authorization = _POLICY_AUTHORIZATION_PAIRS[self.policy_id]
        if self.authorization_id != expected_authorization:
            raise ValueError("runtime policy must be bound to its matching authorization")
        return self


class _ProtectedRawOutputRecord(BaseModel):
    """Ignored local record retaining the unmodified provider output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    request_id_sha256: str
    raw_output_sha256: str
    canonical_output_sha256: str | None = None
    normalization_path: OutputNormalizationPath
    raw_output: str = Field(min_length=1)


def _canonical_json(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _question_from_missing_information(items: tuple[str, ...]) -> str:
    first = items[0].strip()
    if first.endswith("?"):
        return first
    return f"Please provide the missing information for {first}."


def _clarify_reason(items: tuple[str, ...]) -> TerminalReasonCode:
    if all(_FIELD_NAME_PATTERN.fullmatch(item.strip()) is not None for item in items):
        return TerminalReasonCode.MISSING_REQUIRED_PARAMETER
    return TerminalReasonCode.AMBIGUOUS_USER_STATE


def _normalize_compiler_output(
    output: CompilerTerminalDecision,
) -> TerminalDecisionOutput:
    if output.decision == "answer":
        return AnswerDecisionOutput(
            decision="answer",
            reason_code=TerminalReasonCode.EVIDENCE_SUFFICIENT,
            response=(output.answer or "").strip(),
            citation_ids=output.citations,
            unresolved_items=output.missing_information,
        )
    if output.decision == "clarify":
        return ClarifyDecisionOutput(
            decision="clarify",
            reason_code=_clarify_reason(output.missing_information),
            question=_question_from_missing_information(output.missing_information),
            missing_fields=output.missing_information,
            citation_ids=output.citations,
        )
    if output.decision == "escalate":
        return EscalateDecisionOutput(
            decision="escalate",
            reason_code=TerminalReasonCode.INCOMPLETE_DOCUMENTATION,
            escalation_reason_code=EscalationReasonCode.DOCUMENTATION_GAP,
            explanation=(output.escalation_reason or "").strip(),
            evidence_source_ids=output.citations,
        )
    raise ValueError("compiler-schema refusal cannot be normalized safely")


def normalize_provider_output(raw_output: str) -> NormalizedProtectedOutput:
    """Normalize canonical or compiler-schema JSON without inspecting semantic correctness."""

    raw_sha256 = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError("provider output is not one JSON object") from exc

    try:
        canonical = _TERMINAL_OUTPUT_ADAPTER.validate_python(payload)
        normalization_path = OutputNormalizationPath.CANONICAL_DIRECT
    except ValidationError:
        try:
            compiler_output = CompilerTerminalDecision.model_validate(payload)
            canonical = _normalize_compiler_output(compiler_output)
            normalization_path = OutputNormalizationPath.COMPILER_SCHEMA_V1
        except (ValidationError, ValueError) as exc:
            raise ValueError(
                "provider output matches neither the canonical nor compiler terminal contract"
            ) from exc

    canonical_text = _canonical_json(canonical)
    canonical_sha256 = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
    return NormalizedProtectedOutput(
        normalization_path=normalization_path,
        canonical_text=canonical_text,
        raw_output_sha256=raw_sha256,
        canonical_output_sha256=canonical_sha256,
    )


class ContractAlignedPacedAdapter:
    """Translate provider output at the boundary and regulate live call cadence."""

    def __init__(
        self,
        inner: LiveProviderAdapter,
        policy: LiveBatchRuntimePolicy,
        raw_output_path: Path,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._inner = inner
        self._policy = policy
        self._raw_output_path = raw_output_path
        self._monotonic = monotonic
        self._sleep = sleep
        self._last_call_started_at: float | None = None
        self._rate_limit_not_before = 0.0
        self._cumulative_sleep_seconds = 0.0

    @property
    def cumulative_sleep_seconds(self) -> float:
        """Return local pacing time for deterministic unit assertions only."""

        return self._cumulative_sleep_seconds

    def _wait_for_slot(self) -> None:
        now = self._monotonic()
        interval_not_before = (
            0.0
            if self._last_call_started_at is None
            else self._last_call_started_at + self._policy.minimum_call_interval_seconds
        )
        not_before = max(interval_not_before, self._rate_limit_not_before)
        wait_seconds = max(0.0, not_before - now)
        if (
            self._cumulative_sleep_seconds + wait_seconds
            > self._policy.maximum_cumulative_sleep_seconds
        ):
            raise LiveProviderError(
                ProviderErrorCode.RATE_LIMITED,
                "Configured provider pacing budget was exhausted.",
                retryable=False,
            )
        if wait_seconds:
            self._sleep(wait_seconds)
            self._cumulative_sleep_seconds += wait_seconds
        self._last_call_started_at = self._monotonic()

    def _record_rate_limit(self) -> None:
        self._rate_limit_not_before = max(
            self._rate_limit_not_before,
            self._monotonic() + self._policy.rate_limit_cooldown_seconds,
        )

    def _append_raw_output(
        self,
        invocation: LiveProviderInvocation,
        raw_output: str,
        *,
        raw_output_sha256: str,
        normalization_path: OutputNormalizationPath,
        canonical_output_sha256: str | None,
    ) -> None:
        record = _ProtectedRawOutputRecord(
            request_id_sha256=hashlib.sha256(
                invocation.request.request_id.encode("utf-8")
            ).hexdigest(),
            raw_output_sha256=raw_output_sha256,
            canonical_output_sha256=canonical_output_sha256,
            normalization_path=normalization_path,
            raw_output=raw_output,
        )
        self._raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        with self._raw_output_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(record.model_dump_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def invoke(self, invocation: LiveProviderInvocation) -> ProviderCall:
        """Execute one paced call and return canonical protected output."""

        self._wait_for_slot()
        try:
            provider_call = self._inner.invoke(invocation)
        except LiveProviderError as exc:
            if exc.error_code is ProviderErrorCode.RATE_LIMITED:
                self._record_rate_limit()
            raise

        if (
            provider_call.result.status is ProviderInvocationStatus.FAILED
            and provider_call.result.error_code is ProviderErrorCode.RATE_LIMITED
        ):
            self._record_rate_limit()
            return provider_call

        protected_output = provider_call.protected_output
        if protected_output is None:
            return provider_call

        try:
            normalized = normalize_provider_output(protected_output.text)
        except ValueError as exc:
            raw_sha256 = hashlib.sha256(protected_output.text.encode("utf-8")).hexdigest()
            try:
                self._append_raw_output(
                    invocation,
                    protected_output.text,
                    raw_output_sha256=raw_sha256,
                    normalization_path=OutputNormalizationPath.REJECTED,
                    canonical_output_sha256=None,
                )
            except OSError as retention_exc:
                raise LiveProviderError(
                    ProviderErrorCode.AMBIGUOUS_RESPONSE,
                    "Provider output could not be retained safely.",
                    retryable=False,
                ) from retention_exc
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "Provider output matched no supported terminal contract.",
                retryable=False,
            ) from exc

        try:
            self._append_raw_output(
                invocation,
                protected_output.text,
                raw_output_sha256=normalized.raw_output_sha256,
                normalization_path=normalized.normalization_path,
                canonical_output_sha256=normalized.canonical_output_sha256,
            )
        except OSError as exc:
            raise LiveProviderError(
                ProviderErrorCode.AMBIGUOUS_RESPONSE,
                "Provider output could not be retained safely.",
                retryable=False,
            ) from exc

        canonical_output = ProtectedProviderOutput(normalized.canonical_text)
        canonical_result = provider_call.result.model_copy(
            update={"output_sha256": canonical_output.sha256}
        )
        return ProviderCall(
            result=canonical_result,
            telemetry=provider_call.telemetry,
            protected_output=canonical_output,
        )
