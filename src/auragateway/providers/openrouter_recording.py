"""Write-through OpenRouter HTTP recording without changing the hash-bound adapter."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, cast

from pydantic import JsonValue

from auragateway.contracts.openrouter_hy3_capability_probe_execution import (
    OpenRouterProbeAttemptContext,
    OpenRouterProbeRawResponseKind,
    OpenRouterProbeRawResponseRecord,
)
from auragateway.providers.openrouter_http import (
    OpenRouterHttpBackend,
    OpenRouterHttpResponse,
    OpenRouterHttpTransport,
    UrllibOpenRouterBackend,
)


class OpenRouterRawResponseWriter(Protocol):
    """Protected sink used by the recording backend."""

    def write_raw_response(self, record: OpenRouterProbeRawResponseRecord) -> None:
        """Persist and fsync one raw response before returning it to the transport."""


def _response_kind(url: str) -> OpenRouterProbeRawResponseKind:
    if url.endswith("/chat/completions"):
        return OpenRouterProbeRawResponseKind.COMPLETION
    if "/generation?" in url:
        return OpenRouterProbeRawResponseKind.GENERATION_METADATA
    raise ValueError("recording backend received an unsupported OpenRouter response path")


def _content_type(headers: Mapping[str, str]) -> str | None:
    for key, value in headers.items():
        if key.lower() == "content-type":
            return value[:200]
    return None


def _body_fields(body: bytes) -> dict[str, object]:
    try:
        decoded_text = body.decode("utf-8")
    except UnicodeDecodeError:
        return {
            "body_representation": "base64",
            "body_base64": base64.b64encode(body).decode("ascii"),
        }
    try:
        decoded_json = cast(JsonValue, json.loads(decoded_text))
    except json.JSONDecodeError:
        return {
            "body_representation": "utf8",
            "body_utf8": decoded_text,
        }
    return {
        "body_representation": "json",
        "json_payload": decoded_json,
    }


@dataclass(slots=True, repr=False)
class RecordingOpenRouterHttpBackend:
    """Record every returned HTTP response before status or JSON interpretation."""

    context: OpenRouterProbeAttemptContext
    writer: OpenRouterRawResponseWriter = field(repr=False)
    clock: Callable[[], datetime] = field(repr=False)
    backend: OpenRouterHttpBackend = field(default_factory=UrllibOpenRouterBackend, repr=False)
    request_count: int = field(default=0, init=False)
    response_count: int = field(default=0, init=False)
    last_status_code: int | None = field(default=None, init=False)
    last_response_kind: OpenRouterProbeRawResponseKind | None = field(default=None, init=False)
    successful_completion_received: bool = field(default=False, init=False)

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenRouterHttpResponse:
        self.request_count += 1
        response = self.backend.request(
            method=method,
            url=url,
            headers=headers,
            body=body,
            timeout_seconds=timeout_seconds,
        )
        kind = _response_kind(url)
        self.response_count += 1
        if self.response_count > 2:
            raise RuntimeError("one OpenRouter attempt cannot retain more than two responses")
        record = OpenRouterProbeRawResponseRecord(
            authorization_id=self.context.authorization_id,
            execution_id=self.context.execution_id,
            attempt_id=self.context.attempt_id,
            logical_call_role=self.context.logical_call_role,
            attempt_number=self.context.attempt_number,
            response_sequence=self.response_count,
            response_kind=kind,
            received_at=self.clock(),
            http_status=response.status_code,
            content_type=_content_type(response.headers),
            body_sha256=hashlib.sha256(response.body).hexdigest(),
            body_bytes=len(response.body),
            **_body_fields(response.body),
        )
        self.writer.write_raw_response(record)
        self.last_status_code = response.status_code
        self.last_response_kind = kind
        if kind is OpenRouterProbeRawResponseKind.COMPLETION and response.status_code == 200:
            self.successful_completion_received = True
        return response


@dataclass(slots=True, repr=False)
class RecordingOpenRouterTransport:
    """Adapter-compatible transport backed by write-through response recording."""

    api_key: str = field(repr=False)
    context: OpenRouterProbeAttemptContext
    writer: OpenRouterRawResponseWriter = field(repr=False)
    clock: Callable[[], datetime] = field(repr=False)
    backend: OpenRouterHttpBackend = field(default_factory=UrllibOpenRouterBackend, repr=False)
    _recording_backend: RecordingOpenRouterHttpBackend = field(init=False, repr=False)
    _transport: OpenRouterHttpTransport = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._recording_backend = RecordingOpenRouterHttpBackend(
            context=self.context,
            writer=self.writer,
            backend=self.backend,
            clock=self.clock,
        )
        self._transport = OpenRouterHttpTransport(
            api_key=self.api_key,
            backend=self._recording_backend,
        )

    @property
    def last_status_code(self) -> int | None:
        return self._recording_backend.last_status_code

    @property
    def last_response_kind(self) -> OpenRouterProbeRawResponseKind | None:
        return self._recording_backend.last_response_kind

    @property
    def successful_completion_received(self) -> bool:
        return self._recording_backend.successful_completion_received

    @property
    def request_count(self) -> int:
        return self._recording_backend.request_count

    @property
    def response_count(self) -> int:
        return self._recording_backend.response_count

    def create_chat(
        self,
        *,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        return self._transport.create_chat(
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

    def get_generation(
        self,
        *,
        generation_id: str,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        return self._transport.get_generation(
            generation_id=generation_id,
            timeout_seconds=timeout_seconds,
        )


__all__ = [
    "OpenRouterRawResponseWriter",
    "RecordingOpenRouterHttpBackend",
    "RecordingOpenRouterTransport",
]
