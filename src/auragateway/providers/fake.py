"""Deterministic provider adapter backed by frozen Gate 4 fixtures."""

from __future__ import annotations

import hashlib

from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationRequest,
    ProviderInvocationResult,
    ProviderInvocationStatus,
)
from auragateway.contracts.telemetry import TelemetryFixtureCase, TelemetryFixtureSet
from auragateway.providers.base import ProviderCall


class FakeProviderError(Exception):
    """Expected deterministic provider-fixture failure with safe details."""

    def __init__(self, error_code: ProviderErrorCode, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.retryable = False


class FakeProviderAdapter:
    """Replay typed fixtures without network access or raw response persistence."""

    def __init__(self, fixture_set: TelemetryFixtureSet) -> None:
        self._fixtures = {case.case_id: case for case in fixture_set.cases}

    def invoke(self, request: ProviderInvocationRequest) -> ProviderCall:
        """Return a deterministic output digest and the fixture telemetry payload."""

        case = self._fixtures.get(request.fixture_id)
        if case is None:
            raise FakeProviderError(
                ProviderErrorCode.FIXTURE_NOT_FOUND,
                "Requested deterministic provider fixture was not found.",
            )
        self._validate_request(request, case)
        output_digest = hashlib.sha256(
            request.model_dump_json(exclude_none=False).encode("utf-8")
        ).hexdigest()
        result = ProviderInvocationResult(
            request_id=request.request_id,
            provider=request.provider,
            model_alias=request.model_alias,
            status=ProviderInvocationStatus.SUCCEEDED,
            output_sha256=output_digest,
        )
        return ProviderCall(result=result, telemetry=case.telemetry)

    @staticmethod
    def _validate_request(request: ProviderInvocationRequest, case: TelemetryFixtureCase) -> None:
        if request != case.request:
            raise FakeProviderError(
                ProviderErrorCode.REQUEST_MISMATCH,
                "Provider request did not match the frozen deterministic fixture.",
            )
