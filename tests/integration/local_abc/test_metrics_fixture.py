from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.request import urlopen

import pytest

from auragateway.local_abc.contracts import WorkerIdentity
from auragateway.local_abc.telemetry import (
    TelemetryAdaptationRequest,
    TelemetryMappingProfile,
    VersionedTelemetryAdapter,
)
from auragateway.local_abc.worker_client import (
    WorkerInvocationResponse,
    WorkerMetricsSnapshot,
)

FIXTURE_PATH = (
    Path(__file__).parents[2]
    / "fixtures"
    / "local_abc"
    / "metrics"
    / "synthetic_vllm_metrics_fixture_v1.json"
)


class _FixtureHandler(BaseHTTPRequestHandler):
    fixture_bytes: bytes = b""

    def do_GET(self) -> None:
        if self.path != "/metrics-fixture":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.fixture_bytes)))
        self.end_headers()
        self.wfile.write(self.fixture_bytes)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@contextmanager
def fixture_server(fixture_bytes: bytes) -> Iterator[str]:
    handler = type(
        "BoundFixtureHandler",
        (_FixtureHandler,),
        {"fixture_bytes": fixture_bytes},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = cast(tuple[str, int], server.server_address)
        yield f"http://{host}:{port}/metrics-fixture"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def canonical_payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def metrics_snapshot(payload: dict[str, Any]) -> WorkerMetricsSnapshot:
    snapshot_payload = dict(payload)
    snapshot_payload["raw_payload_sha256"] = canonical_payload_sha256(payload)
    return WorkerMetricsSnapshot.model_validate(snapshot_payload)


def test_local_http_metrics_fixture_normalizes_through_versioned_adapter() -> None:
    fixture_bytes = FIXTURE_PATH.read_bytes()

    with (
        fixture_server(fixture_bytes) as fixture_url,
        urlopen(fixture_url, timeout=2.0) as response,
    ):
        remote_bytes = response.read()

    assert remote_bytes == fixture_bytes
    fixture = json.loads(remote_bytes)
    profile = TelemetryMappingProfile.model_validate(fixture["mapping_profile"])
    before = metrics_snapshot(fixture["before_metrics"])
    after = metrics_snapshot(fixture["after_metrics"])
    identity = WorkerIdentity.model_validate(fixture["worker_identity"])
    invocation = WorkerInvocationResponse.model_validate(fixture["invocation_response"])
    request = TelemetryAdaptationRequest(
        observation_id=fixture["adaptation"]["observation_id"],
        worker_identity=identity,
        before_snapshot=before,
        after_snapshot=after,
        invocation_response=invocation,
        eligible_shared_prefix_tokens=fixture["adaptation"]["eligible_shared_prefix_tokens"],
    )

    record = VersionedTelemetryAdapter(profile).adapt(request)
    observation = record.observation
    expected = fixture["expected"]

    assert observation.cache.state.value == expected["cache_state"]
    assert observation.cache.observed_cached_prefix_tokens == expected["cached_prefix_tokens"]
    assert observation.newly_computed_prefill_tokens == expected["newly_computed_prefill_tokens"]
    assert observation.prefill_duration_ms == pytest.approx(expected["prefill_duration_ms"])
    assert observation.time_to_first_token_ms == pytest.approx(expected["time_to_first_token_ms"])
    assert observation.end_to_end_latency_ms == expected["end_to_end_latency_ms"]
    assert record.before_snapshot_sha256 == canonical_payload_sha256(fixture["before_metrics"])
    assert record.after_snapshot_sha256 == canonical_payload_sha256(fixture["after_metrics"])
