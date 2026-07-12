"""Provider adapter protocol and metadata-safe call container."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from auragateway.contracts.provider import (
    ProviderInvocationRequest,
    ProviderInvocationResult,
)
from auragateway.contracts.telemetry import ProviderTelemetryPayload


@dataclass(frozen=True, slots=True)
class ProviderCall:
    """Typed invocation result after raw provider payloads have been discarded."""

    result: ProviderInvocationResult
    telemetry: ProviderTelemetryPayload


class ProviderAdapter(Protocol):
    """Provider boundary; only implementations may inspect raw SDK payloads."""

    def invoke(self, request: ProviderInvocationRequest) -> ProviderCall:
        """Execute one bounded provider request and return typed metadata only."""
