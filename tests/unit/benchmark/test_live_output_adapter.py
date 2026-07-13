from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from auragateway.benchmark.live_output_adapter import (
    ContractAlignedPacedAdapter,
    LiveBatchRuntimePolicy,
    OutputNormalizationPath,
    normalize_provider_output,
)
from auragateway.contracts.episodes import TerminalDecisionOutput
from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderInvocationResult,
    ProviderInvocationStatus,
    ProviderName,
)
from auragateway.contracts.telemetry import CachedInputDetailTelemetry
from auragateway.providers.base import (
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderOutput,
    ProtectedProviderPrompt,
    ProviderCall,
)

_TERMINAL_ADAPTER: TypeAdapter[TerminalDecisionOutput] = TypeAdapter(TerminalDecisionOutput)

_BATCH_01_OUTPUTS = (
    (
        '{"decision":"answer","answer":"A newly issued key is valid for 24 hours.",'
        '"citations":["NR-AUTH-001"],"missing_information":[],'
        '"confidence_band":"high"}'
    ),
    (
        '{"decision":"clarify","answer":"","citations":[],"missing_information":'
        '["Which API version are you currently using?",'
        '"Do you have a reference to the guide that states seven days?"],'
        '"escalation_reason":"","confidence_band":"medium"}'
    ),
    (
        '{"decision":"clarify","answer":"","citations":[],"missing_information":'
        '["token_type"],"escalation_reason":"","confidence_band":"high"}'
    ),
)


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class _SuccessfulAdapter:
    def __init__(self, raw_output: str) -> None:
        self.raw_output = raw_output
        self.invocations: list[LiveProviderInvocation] = []

    def invoke(self, invocation: LiveProviderInvocation) -> ProviderCall:
        self.invocations.append(invocation)
        protected = ProtectedProviderOutput(self.raw_output)
        return ProviderCall(
            result=ProviderInvocationResult(
                request_id=invocation.request.request_id,
                provider=ProviderName.GROQ,
                model_alias=invocation.request.model_alias,
                status=ProviderInvocationStatus.SUCCEEDED,
                output_sha256=protected.sha256,
            ),
            telemetry=CachedInputDetailTelemetry(
                fixture_id=invocation.request.fixture_id,
                provider=ProviderName.GROQ,
                model_alias=invocation.request.model_alias,
                input_tokens=100,
                output_tokens=20,
            ),
            protected_output=protected,
        )


class _RateLimitedAdapter:
    def invoke(self, invocation: LiveProviderInvocation) -> ProviderCall:
        raise LiveProviderError(
            ProviderErrorCode.RATE_LIMITED,
            "rate limited",
            retryable=True,
        )


def _policy() -> LiveBatchRuntimePolicy:
    return LiveBatchRuntimePolicy(
        minimum_call_interval_seconds=20.0,
        rate_limit_cooldown_seconds=65.0,
        maximum_cumulative_sleep_seconds=900.0,
    )


def _invocation(request_id: str) -> LiveProviderInvocation:
    return LiveProviderInvocation(
        request=ProviderInvocationRequest(
            request_id=request_id,
            fixture_id=f"fixture-{request_id}",
            provider=ProviderName.GROQ,
            model_alias="groq-gpt-oss-20b",
            static_prefix_fingerprint="a" * 64,
            input_token_count=100,
            output_token_budget=64,
        ),
        prompt=ProtectedProviderPrompt(
            system_prompt="synthetic system prompt",
            user_prompt="synthetic user prompt",
        ),
        timeout_seconds=30.0,
    )


@pytest.mark.parametrize("raw_output", _BATCH_01_OUTPUTS)
def test_batch_01_observed_outputs_normalize_to_canonical_contract(
    raw_output: str,
) -> None:
    normalized = normalize_provider_output(raw_output)

    assert normalized.normalization_path is OutputNormalizationPath.COMPILER_SCHEMA_V1
    canonical = _TERMINAL_ADAPTER.validate_json(normalized.canonical_text)
    assert canonical.decision.value in {"answer", "clarify"}


def test_canonical_output_passes_without_legacy_mapping() -> None:
    raw_output = (
        '{"decision":"answer","reason_code":"evidence_sufficient",'
        '"response":"Use current guidance.","citation_ids":["NR-AUTH-001"],'
        '"unresolved_items":[]}'
    )

    normalized = normalize_provider_output(raw_output)

    assert normalized.normalization_path is OutputNormalizationPath.CANONICAL_DIRECT
    _TERMINAL_ADAPTER.validate_json(normalized.canonical_text)


def test_adapter_retains_raw_output_and_returns_canonical_output(tmp_path: Path) -> None:
    raw_output = _BATCH_01_OUTPUTS[0]
    raw_path = tmp_path / "provider_raw_outputs.jsonl"
    clock = _FakeClock()
    inner = _SuccessfulAdapter(raw_output)
    adapter = ContractAlignedPacedAdapter(
        inner,
        _policy(),
        raw_path,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    first = adapter.invoke(_invocation("request-one"))
    second = adapter.invoke(_invocation("request-two"))

    assert first.protected_output is not None
    assert second.protected_output is not None
    _TERMINAL_ADAPTER.validate_json(first.protected_output.text)
    assert clock.sleeps == [20.0]
    records = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    assert [item["raw_output"] for item in records] == [raw_output, raw_output]
    assert all(item["normalization_path"] == "compiler_schema_v1" for item in records)


def test_rate_limit_enforces_cooldown_before_next_call(tmp_path: Path) -> None:
    clock = _FakeClock()
    adapter = ContractAlignedPacedAdapter(
        _RateLimitedAdapter(),
        _policy(),
        tmp_path / "provider_raw_outputs.jsonl",
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    with pytest.raises(LiveProviderError):
        adapter.invoke(_invocation("request-one"))
    with pytest.raises(LiveProviderError):
        adapter.invoke(_invocation("request-two"))

    assert clock.sleeps == [65.0]
    assert adapter.cumulative_sleep_seconds == 65.0


def test_legacy_refusal_fails_closed() -> None:
    raw_output = (
        '{"decision":"refuse","answer":"I cannot do that.","citations":[],'
        '"missing_information":[],"confidence_band":"high"}'
    )

    with pytest.raises(ValueError, match="matches neither"):
        normalize_provider_output(raw_output)


def test_adapter_retains_rejected_raw_output_before_failing(tmp_path: Path) -> None:
    raw_output = (
        '{"decision":"refuse","answer":"I cannot do that.","citations":[],'
        '"missing_information":[],"confidence_band":"high"}'
    )
    raw_path = tmp_path / "provider_raw_outputs.jsonl"
    adapter = ContractAlignedPacedAdapter(
        _SuccessfulAdapter(raw_output),
        _policy(),
        raw_path,
    )

    with pytest.raises(LiveProviderError) as exc_info:
        adapter.invoke(_invocation("request-rejected"))

    assert exc_info.value.error_code is ProviderErrorCode.INVALID_RESPONSE
    record = json.loads(raw_path.read_text(encoding="utf-8"))
    assert record["normalization_path"] == "rejected"
    assert record["canonical_output_sha256"] is None
    assert record["raw_output"] == raw_output
