from __future__ import annotations

import urllib.request

import pytest

from auragateway.providers.openrouter_http import UrllibOpenRouterBackend


class _RequestCaptured(Exception):
    pass


def test_urllib_backend_propagates_bearer_authorization_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def capture(request: urllib.request.Request, timeout: float) -> object:
        del timeout
        captured.update({key.lower(): value for key, value in request.header_items()})
        raise _RequestCaptured

    monkeypatch.setattr(urllib.request, "urlopen", capture)
    backend = UrllibOpenRouterBackend()

    with pytest.raises(_RequestCaptured):
        backend.request(
            method="POST",
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer fixture-only-not-a-real-key",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AuraGateway/0.1",
            },
            body=b"{}",
            timeout_seconds=1,
        )

    assert captured["authorization"] == "Bearer fixture-only-not-a-real-key"
