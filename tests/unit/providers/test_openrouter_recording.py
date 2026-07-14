from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

from auragateway.contracts.openrouter_hy3_capability_probe_execution import (
    OpenRouterProbeAttemptContext,
    OpenRouterProbeRawResponseKind,
    OpenRouterProbeRawResponseRecord,
)
from auragateway.providers.base import LiveProviderError
from auragateway.providers.openrouter_http import (
    OpenRouterHttpResponse,
)
from auragateway.providers.openrouter_recording import (
    RecordingOpenRouterTransport,
)


class _Writer:
    def __init__(self) -> None:
        self.records: list[OpenRouterProbeRawResponseRecord] = []

    def write_raw_response(self, record: OpenRouterProbeRawResponseRecord) -> None:
        self.records.append(record)


class _Backend:
    def __init__(self, responses: list[OpenRouterHttpResponse]) -> None:
        self.responses = responses

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenRouterHttpResponse:
        del method, url, headers, body, timeout_seconds
        return self.responses.pop(0)


def _response(payload: object, status: int = 200) -> OpenRouterHttpResponse:
    return OpenRouterHttpResponse(
        status_code=status,
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload).encode("utf-8"),
    )


def _context() -> OpenRouterProbeAttemptContext:
    return OpenRouterProbeAttemptContext(
        authorization_id="openrouter-hy3-capability-probe-auth-v1",
        execution_id="openrouter-hy3-capability-probe-v1",
        attempt_id="openrouter-hy3-capability-probe-v1-cold-attempt-1",
        logical_call_role="cold_probe",
        logical_call_index=0,
        attempt_number=1,
    )


def test_recording_transport_persists_completion_and_generation_separately() -> None:
    writer = _Writer()
    transport = RecordingOpenRouterTransport(
        api_key="secret-fixture-key",
        context=_context(),
        writer=writer,
        backend=_Backend(
            [
                _response({"id": "gen-1"}),
                _response({"data": {"id": "gen-1"}}),
            ]
        ),
        clock=lambda: datetime(2026, 7, 14, tzinfo=UTC),
    )

    transport.create_chat(payload={"model": "tencent/hy3:free"}, timeout_seconds=30)
    transport.get_generation(generation_id="gen-1", timeout_seconds=30)

    assert [record.response_kind for record in writer.records] == [
        OpenRouterProbeRawResponseKind.COMPLETION,
        OpenRouterProbeRawResponseKind.GENERATION_METADATA,
    ]
    assert [record.response_sequence for record in writer.records] == [1, 2]
    assert transport.request_count == 2
    assert transport.successful_completion_received is True
    assert "secret-fixture-key" not in repr(transport)


def test_recording_transport_retains_non_success_response_before_error_mapping() -> None:
    writer = _Writer()
    transport = RecordingOpenRouterTransport(
        api_key="fixture",
        context=_context(),
        writer=writer,
        backend=_Backend([_response({"error": {"message": "busy"}}, status=429)]),
        clock=lambda: datetime(2026, 7, 14, tzinfo=UTC),
    )

    with pytest.raises(LiveProviderError):
        transport.create_chat(
            payload={"model": "tencent/hy3:free"},
            timeout_seconds=30,
        )

    assert len(writer.records) == 1
    assert writer.records[0].http_status == 429
    assert writer.records[0].response_kind is OpenRouterProbeRawResponseKind.COMPLETION
    assert transport.successful_completion_received is False
