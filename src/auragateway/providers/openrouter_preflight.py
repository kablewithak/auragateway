"""Explicit-key OpenRouter model-catalog and key-status preflight client."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from auragateway.contracts.provider import ProviderErrorCode
from auragateway.providers.base import LiveProviderError
from auragateway.providers.openrouter_http import (
    OpenRouterHttpBackend,
    OpenRouterHttpTransport,
    UrllibOpenRouterBackend,
)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_MAX_RESPONSE_BYTES = 2_000_000


@dataclass(frozen=True, slots=True, repr=False)
class OpenRouterActivationPreflightClient:
    """Two-request non-inference preflight client with explicit credential injection."""

    api_key: str = field(repr=False)
    backend: OpenRouterHttpBackend = field(default_factory=UrllibOpenRouterBackend, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.strip() or len(self.api_key) > 512:
            raise ValueError("OpenRouter API key must contain 1 to 512 characters")

    def get_key_status(self, *, timeout_seconds: float) -> Mapping[str, object]:
        """Return authenticated key metadata through the reviewed HTTP transport."""

        transport = OpenRouterHttpTransport(api_key=self.api_key, backend=self.backend)
        return transport.get_key_status(timeout_seconds=timeout_seconds)

    def get_models(self, *, timeout_seconds: float) -> Mapping[str, object]:
        """Return the current model catalog without issuing an inference request."""

        if not 0 < timeout_seconds <= 120:
            raise ValueError(
                "OpenRouter preflight timeout must be greater than zero and at most 120"
            )
        response = self.backend.request(
            method="GET",
            url=f"{_OPENROUTER_BASE_URL}/models",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "User-Agent": "AuraGateway/0.1",
            },
            body=None,
            timeout_seconds=timeout_seconds,
        )
        if response.status_code != 200:
            raise LiveProviderError(
                ProviderErrorCode.MODEL_NOT_AVAILABLE,
                "OpenRouter model catalog preflight did not return success.",
                retryable=False,
            )
        if len(response.body) > _MAX_RESPONSE_BYTES:
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouter model catalog exceeded the approved response limit.",
                retryable=False,
            )
        try:
            decoded = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouter model catalog was not valid UTF-8 JSON.",
                retryable=False,
            ) from exc
        if not isinstance(decoded, Mapping):
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouter model catalog was not a JSON object.",
                retryable=False,
            )
        return decoded


__all__ = ["OpenRouterActivationPreflightClient"]
