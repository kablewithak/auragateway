from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.contracts.provider import ProviderErrorCode
from auragateway.contracts.telemetry import TelemetryFixtureSet
from auragateway.providers.fake import FakeProviderAdapter, FakeProviderError


def _fixtures() -> TelemetryFixtureSet:
    payload = json.loads(
        Path("data/provider_fixtures/telemetry/fixtures.json").read_text(encoding="utf-8")
    )
    return TelemetryFixtureSet.model_validate(payload)


def test_fake_provider_returns_deterministic_digest_and_typed_telemetry() -> None:
    fixtures = _fixtures()
    case = fixtures.cases[0]
    adapter = FakeProviderAdapter(fixtures)
    first = adapter.invoke(case.request)
    second = adapter.invoke(case.request)
    assert first == second
    assert first.result.output_sha256 is not None
    assert first.telemetry.fixture_id == case.case_id


def test_fake_provider_rejects_request_drift() -> None:
    fixtures = _fixtures()
    case = fixtures.cases[0]
    adapter = FakeProviderAdapter(fixtures)
    drifted = case.request.model_copy(update={"output_token_budget": 512})
    with pytest.raises(FakeProviderError) as caught:
        adapter.invoke(drifted)
    assert caught.value.error_code is ProviderErrorCode.REQUEST_MISMATCH
    assert caught.value.retryable is False


def test_fake_provider_rejects_unknown_fixture() -> None:
    fixtures = _fixtures()
    adapter = FakeProviderAdapter(fixtures)
    unknown = fixtures.cases[0].request.model_copy(update={"fixture_id": "unknown-fixture"})
    with pytest.raises(FakeProviderError) as caught:
        adapter.invoke(unknown)
    assert caught.value.error_code is ProviderErrorCode.FIXTURE_NOT_FOUND
