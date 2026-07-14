"""Explicit-key OpenRouter HTTP transport with zero automatic retries."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from auragateway.contracts.provider import ProviderErrorCode
from auragateway.providers.base import LiveProviderError

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_MAX_RESPONSE_BYTES = 2_000_000
_TRANSIENT_STATUSES = frozenset({429, 502, 524, 529})


@dataclass(frozen=True, slots=True)
class OpenRouterHttpResponse:
    """Bounded HTTP response returned by the injectable backend."""

    status_code: int
    headers: Mapping[str, str]
    body: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not 100 <= self.status_code <= 599:
            raise ValueError("HTTP status code must be in the inclusive range 100..599")
        if len(self.body) > _MAX_RESPONSE_BYTES:
            raise ValueError("OpenRouter response exceeds the bounded byte limit")


class OpenRouterHttpBackend(Protocol):
    """Minimal backend seam used by the live transport and deterministic tests."""

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenRouterHttpResponse:
        """Perform one HTTP request without automatic retry."""


class UrllibOpenRouterBackend:
    """Standard-library backend with no hidden retry loop."""

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenRouterHttpResponse:
        request = urllib.request.Request(
            url=url,
            data=body,
            headers=dict(headers),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read(_MAX_RESPONSE_BYTES + 1)
                if len(payload) > _MAX_RESPONSE_BYTES:
                    raise LiveProviderError(
                        ProviderErrorCode.INVALID_RESPONSE,
                        "OpenRouter returned a response larger than the approved limit.",
                        retryable=False,
                    )
                return OpenRouterHttpResponse(
                    status_code=int(response.status),
                    headers={key: value for key, value in response.headers.items()},
                    body=payload,
                )
        except urllib.error.HTTPError as exc:
            payload = exc.read(_MAX_RESPONSE_BYTES + 1)
            if len(payload) > _MAX_RESPONSE_BYTES:
                payload = b""
            return OpenRouterHttpResponse(
                status_code=exc.code,
                headers={key: value for key, value in exc.headers.items()},
                body=payload,
            )
        except TimeoutError as exc:
            raise LiveProviderError(
                ProviderErrorCode.TIMEOUT,
                "OpenRouter transport timed out before a response was retained.",
                retryable=True,
            ) from exc
        except urllib.error.URLError as exc:
            raise LiveProviderError(
                ProviderErrorCode.CONNECTION_FAILED,
                "OpenRouter transport could not establish a connection.",
                retryable=False,
            ) from exc


@dataclass(frozen=True, slots=True, repr=False)
class OpenRouterHttpTransport:
    """OpenRouter transport requiring an explicitly supplied credential."""

    api_key: str = field(repr=False)
    backend: OpenRouterHttpBackend = field(default_factory=UrllibOpenRouterBackend, repr=False)
    base_url: str = _OPENROUTER_BASE_URL

    def __post_init__(self) -> None:
        if not self.api_key.strip() or len(self.api_key) > 512:
            raise ValueError("OpenRouter API key must contain 1 to 512 characters")
        if self.base_url != _OPENROUTER_BASE_URL:
            raise ValueError("OpenRouter transport base URL must remain exact")

    def create_chat(
        self,
        *,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        """Create one non-streaming chat completion."""

        return self._request_json(
            method="POST",
            path="/chat/completions",
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

    def get_generation(
        self,
        *,
        generation_id: str,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        """Fetch metadata for one exact generation without polling."""

        if not generation_id.strip() or len(generation_id) > 256:
            raise ValueError("OpenRouter generation IDs must contain 1 to 256 characters")
        query = urllib.parse.urlencode({"id": generation_id})
        return self._request_json(
            method="GET",
            path=f"/generation?{query}",
            payload=None,
            timeout_seconds=timeout_seconds,
        )

    def get_key_status(self, *, timeout_seconds: float) -> Mapping[str, object]:
        """Fetch current key metadata for activation preflight."""

        return self._request_json(
            method="GET",
            path="/key",
            payload=None,
            timeout_seconds=timeout_seconds,
        )

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        payload: Mapping[str, object] | None,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        if not 0 < timeout_seconds <= 120:
            raise ValueError("OpenRouter HTTP timeout must be greater than zero and at most 120")
        body = (
            None
            if payload is None
            else json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        )
        response = self.backend.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AuraGateway/0.1",
            },
            body=body,
            timeout_seconds=timeout_seconds,
        )
        if response.status_code != 200:
            raise _status_error(response.status_code)
        try:
            decoded = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouter returned a response that was not valid UTF-8 JSON.",
                retryable=False,
            ) from exc
        if not isinstance(decoded, Mapping):
            raise LiveProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "OpenRouter returned a JSON value that was not an object.",
                retryable=False,
            )
        return decoded


def _status_error(status_code: int) -> LiveProviderError:
    if status_code == 401:
        code = ProviderErrorCode.AUTHENTICATION_FAILED
    elif status_code in {402, 403}:
        code = ProviderErrorCode.PERMISSION_DENIED
    elif status_code == 404:
        code = ProviderErrorCode.MODEL_NOT_AVAILABLE
    elif status_code == 429:
        code = ProviderErrorCode.RATE_LIMITED
    elif status_code in {502, 524, 529}:
        code = ProviderErrorCode.UNAVAILABLE
    elif status_code == 408:
        code = ProviderErrorCode.TIMEOUT
    else:
        code = ProviderErrorCode.REQUEST_REJECTED
    return LiveProviderError(
        code,
        "OpenRouter returned a non-success HTTP status.",
        retryable=status_code in _TRANSIENT_STATUSES,
    )


__all__ = [
    "OpenRouterHttpBackend",
    "OpenRouterHttpResponse",
    "OpenRouterHttpTransport",
    "UrllibOpenRouterBackend",
]
