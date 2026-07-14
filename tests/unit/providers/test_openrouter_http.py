from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from auragateway.contracts.provider import ProviderErrorCode
from auragateway.providers.base import LiveProviderError
from auragateway.providers.openrouter_http import (
    OpenRouterHttpResponse,
    OpenRouterHttpTransport,
)


class _Backend:
    def __init__(self, response: OpenRouterHttpResponse) -> None:
        self.response = response
        self.request_values: tuple[str, str, Mapping[str, str], bytes | None, float] | None = None

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenRouterHttpResponse:
        self.request_values = (method, url, headers, body, timeout_seconds)
        return self.response


def _response(payload: object, status: int = 200) -> OpenRouterHttpResponse:
    return OpenRouterHttpResponse(
        status_code=status,
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload).encode("utf-8"),
    )


def test_transport_uses_explicit_key_without_exposing_it_in_repr() -> None:
    backend = _Backend(_response({"ok": True}))
    transport = OpenRouterHttpTransport(api_key="secret-fixture-key", backend=backend)
    assert "secret-fixture-key" not in repr(transport)

    transport.create_chat(payload={"model": "tencent/hy3:free"}, timeout_seconds=30)
    assert backend.request_values is not None
    method, url, headers, body, timeout = backend.request_values
    assert method == "POST"
    assert url == "https://openrouter.ai/api/v1/chat/completions"
    assert headers["Authorization"] == "Bearer secret-fixture-key"
    assert body == b'{"model":"tencent/hy3:free"}'
    assert timeout == 30


def test_transport_encodes_generation_id_and_key_status_path() -> None:
    generation_backend = _Backend(_response({"data": {"id": "gen-a/b"}}))
    OpenRouterHttpTransport(api_key="fixture", backend=generation_backend).get_generation(
        generation_id="gen-a/b",
        timeout_seconds=30,
    )
    assert generation_backend.request_values is not None
    assert generation_backend.request_values[1].endswith("/generation?id=gen-a%2Fb")

    key_backend = _Backend(_response({"data": {"is_free_tier": True}}))
    OpenRouterHttpTransport(api_key="fixture", backend=key_backend).get_key_status(
        timeout_seconds=30
    )
    assert key_backend.request_values is not None
    assert key_backend.request_values[1].endswith("/key")


@pytest.mark.parametrize("status", [429, 502, 524, 529])
def test_transport_marks_only_frozen_transient_statuses_retryable(status: int) -> None:
    backend = _Backend(_response({"error": {}}, status))
    with pytest.raises(LiveProviderError) as caught:
        OpenRouterHttpTransport(api_key="fixture", backend=backend).create_chat(
            payload={"model": "tencent/hy3:free"},
            timeout_seconds=30,
        )
    assert caught.value.retryable is True


@pytest.mark.parametrize(
    ("status", "error_code"),
    [
        (401, ProviderErrorCode.AUTHENTICATION_FAILED),
        (402, ProviderErrorCode.PERMISSION_DENIED),
        (500, ProviderErrorCode.REQUEST_REJECTED),
    ],
)
def test_transport_marks_terminal_statuses_nonretryable(
    status: int,
    error_code: ProviderErrorCode,
) -> None:
    backend = _Backend(_response({"error": {}}, status))
    with pytest.raises(LiveProviderError) as caught:
        OpenRouterHttpTransport(api_key="fixture", backend=backend).create_chat(
            payload={"model": "tencent/hy3:free"},
            timeout_seconds=30,
        )
    assert caught.value.error_code is error_code
    assert caught.value.retryable is False


def test_transport_rejects_invalid_json_without_retry() -> None:
    backend = _Backend(OpenRouterHttpResponse(status_code=200, headers={}, body=b"{"))
    with pytest.raises(LiveProviderError) as caught:
        OpenRouterHttpTransport(api_key="fixture", backend=backend).create_chat(
            payload={"model": "tencent/hy3:free"},
            timeout_seconds=30,
        )
    assert caught.value.error_code is ProviderErrorCode.INVALID_RESPONSE
    assert caught.value.retryable is False


def test_transport_rejects_alternate_base_url() -> None:
    with pytest.raises(ValueError, match="base URL"):
        OpenRouterHttpTransport(
            api_key="fixture",
            backend=_Backend(_response({"ok": True})),
            base_url="https://example.invalid",
        )
