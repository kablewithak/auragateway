from __future__ import annotations

import hashlib

import pytest

from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderName,
)
from auragateway.providers.base import LiveProviderInvocation, ProtectedProviderPrompt

_PREFIX_FINGERPRINT = "6b7c72729eca9480ef7a0cf734b957dd6c10fa9ff88adc33e322af54d50f4d63"


def _request(
    input_token_count: int = 2000,
    provider: ProviderName = ProviderName.GROQ,
) -> ProviderInvocationRequest:
    model_alias = "ollama-llama3.2-3b" if provider is ProviderName.OLLAMA else "groq-gpt-oss-20b"
    return ProviderInvocationRequest(
        request_id=f"{provider.value}-calibration-request-1",
        fixture_id=f"{provider.value}-live-turn-1",
        provider=provider,
        model_alias=model_alias,
        static_prefix_fingerprint=_PREFIX_FINGERPRINT,
        input_token_count=input_token_count,
        output_token_budget=32,
    )


def test_protected_prompt_repr_and_summary_exclude_raw_content() -> None:
    prompt = ProtectedProviderPrompt(
        system_prompt="synthetic-system-secret",
        user_prompt="synthetic-user-secret",
    )
    representation = repr(prompt)
    assert "synthetic-system-secret" not in representation
    assert "synthetic-user-secret" not in representation
    summary = prompt.summary()
    assert summary.system_sha256 == hashlib.sha256(b"synthetic-system-secret").hexdigest()
    assert summary.user_sha256 == hashlib.sha256(b"synthetic-user-secret").hexdigest()
    assert "synthetic" not in summary.model_dump_json()


def test_live_invocation_requires_positive_token_estimate() -> None:
    prompt = ProtectedProviderPrompt(system_prompt="system", user_prompt="user")
    with pytest.raises(ValueError, match="positive preflight token estimate"):
        LiveProviderInvocation(request=_request(0), prompt=prompt)


def test_live_invocation_rejects_unbounded_hosted_timeout() -> None:
    prompt = ProtectedProviderPrompt(system_prompt="system", user_prompt="user")
    with pytest.raises(ValueError, match="at most 120 seconds for groq"):
        LiveProviderInvocation(request=_request(), prompt=prompt, timeout_seconds=121)


def test_live_invocation_allows_bounded_cpu_local_timeout() -> None:
    prompt = ProtectedProviderPrompt(system_prompt="system", user_prompt="user")
    invocation = LiveProviderInvocation(
        request=_request(provider=ProviderName.OLLAMA),
        prompt=prompt,
        timeout_seconds=300,
    )
    assert invocation.timeout_seconds == 300


def test_live_invocation_rejects_unbounded_cpu_local_timeout() -> None:
    prompt = ProtectedProviderPrompt(system_prompt="system", user_prompt="user")
    with pytest.raises(ValueError, match="at most 300 seconds for ollama"):
        LiveProviderInvocation(
            request=_request(provider=ProviderName.OLLAMA),
            prompt=prompt,
            timeout_seconds=301,
        )


def test_provider_taxonomy_contains_groq_and_safe_live_failures() -> None:
    assert ProviderName.GROQ.value == "groq"
    assert ProviderErrorCode.RATE_LIMITED.value == "PROVIDER_RATE_LIMITED"
    assert ProviderErrorCode.AUTHENTICATION_FAILED.value == "PROVIDER_AUTHENTICATION_FAILED"
