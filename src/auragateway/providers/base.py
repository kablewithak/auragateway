"""Provider adapter protocols, protected prompts, and metadata-safe call containers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Protocol

from auragateway.contracts.provider import (
    ProtectedPromptSummary,
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderInvocationResult,
    ProviderName,
)
from auragateway.contracts.telemetry import ProviderTelemetryPayload

_MAX_PROTECTED_PROMPT_BYTES = 200_000


@dataclass(frozen=True, slots=True, repr=False)
class ProtectedProviderPrompt:
    """In-memory prompt content that cannot enter normal repr or typed traces."""

    system_prompt: str = field(repr=False)
    user_prompt: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.system_prompt.strip() or not self.user_prompt.strip():
            raise ValueError("protected provider prompts require non-empty system and user text")
        if self.total_bytes > _MAX_PROTECTED_PROMPT_BYTES:
            raise ValueError("protected provider prompt exceeds the bounded byte limit")

    @property
    def total_bytes(self) -> int:
        """Return the total UTF-8 byte count without exposing content."""

        return len(self.system_prompt.encode("utf-8")) + len(self.user_prompt.encode("utf-8"))

    def summary(self) -> ProtectedPromptSummary:
        """Return the only prompt representation permitted in reports and traces."""

        return ProtectedPromptSummary(
            system_sha256=hashlib.sha256(self.system_prompt.encode("utf-8")).hexdigest(),
            user_sha256=hashlib.sha256(self.user_prompt.encode("utf-8")).hexdigest(),
            total_bytes=self.total_bytes,
        )


@dataclass(frozen=True, slots=True)
class LiveProviderInvocation:
    """One bounded live invocation with metadata and protected in-memory content."""

    request: ProviderInvocationRequest
    prompt: ProtectedProviderPrompt = field(repr=False)
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        maximum_timeout = 300 if self.request.provider is ProviderName.OLLAMA else 120
        if not 0 < self.timeout_seconds <= maximum_timeout:
            raise ValueError(
                "live provider timeout must be greater than zero and at most "
                f"{maximum_timeout} seconds for {self.request.provider.value}"
            )
        if self.request.input_token_count <= 0:
            raise ValueError("live provider requests require a positive preflight token estimate")


@dataclass(frozen=True, slots=True)
class ProviderCall:
    """Typed invocation result after raw provider payloads have been discarded."""

    result: ProviderInvocationResult
    telemetry: ProviderTelemetryPayload


class ProviderAdapter(Protocol):
    """Deterministic provider boundary used by frozen fixtures."""

    def invoke(self, request: ProviderInvocationRequest) -> ProviderCall:
        """Execute one deterministic request and return typed metadata only."""


class LiveProviderAdapter(Protocol):
    """Live provider boundary; only implementations may inspect raw payloads."""

    def invoke(self, invocation: LiveProviderInvocation) -> ProviderCall:
        """Execute one bounded live request and return typed metadata only."""


class LiveProviderError(Exception):
    """Expected provider failure with bounded, content-free diagnostics."""

    def __init__(
        self,
        error_code: ProviderErrorCode,
        safe_message: str,
        *,
        retryable: bool,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.retryable = retryable
