from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from auragateway.providers.base import LiveProviderError
from auragateway.providers.openrouter_http import OpenRouterHttpResponse
from auragateway.providers.openrouter_preflight import OpenRouterActivationPreflightClient


class _Backend:
    def __init__(self, responses: list[OpenRouterHttpResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, Mapping[str, str], bytes | None, float]] = []

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenRouterHttpResponse:
        self.calls.append((method, url, headers, body, timeout_seconds))
        return self.responses.pop(0)


def _response(payload: object, status: int = 200) -> OpenRouterHttpResponse:
    return OpenRouterHttpResponse(
        status_code=status,
        headers={},
        body=json.dumps(payload).encode("utf-8"),
    )


def test_preflight_client_uses_explicit_key_for_two_non_inference_requests() -> None:
    backend = _Backend(
        [
            _response({"data": {"label": "probe", "usage": 0}}),
            _response({"data": [{"id": "tencent/hy3:free"}]}),
        ]
    )
    client = OpenRouterActivationPreflightClient(api_key="secret", backend=backend)
    client.get_key_status(timeout_seconds=30)
    client.get_models(timeout_seconds=30)
    assert len(backend.calls) == 2
    assert backend.calls[0][1].endswith("/key")
    assert backend.calls[1][1].endswith("/models")
    assert all(call[2]["Authorization"] == "Bearer secret" for call in backend.calls)
    assert all("chat/completions" not in call[1] for call in backend.calls)


def test_model_catalog_rejects_non_success() -> None:
    backend = _Backend([_response({"error": "unavailable"}, status=503)])
    client = OpenRouterActivationPreflightClient(api_key="secret", backend=backend)
    with pytest.raises(LiveProviderError, match="catalog"):
        client.get_models(timeout_seconds=30)


def test_model_catalog_rejects_non_object_json() -> None:
    backend = _Backend([_response([{"id": "tencent/hy3:free"}])])
    client = OpenRouterActivationPreflightClient(api_key="secret", backend=backend)
    with pytest.raises(LiveProviderError, match="JSON object"):
        client.get_models(timeout_seconds=30)


def test_preflight_client_rejects_empty_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenRouterActivationPreflightClient(api_key="")
