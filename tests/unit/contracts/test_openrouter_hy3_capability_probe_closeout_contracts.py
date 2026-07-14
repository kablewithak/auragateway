from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from auragateway.contracts.openrouter_hy3_capability_probe_closeout import (
    OpenRouterProbePosthocAuthDiagnostic,
    OpenRouterProbeSanitizedCloseout,
)


def _result() -> OpenRouterProbeSanitizedCloseout:
    return OpenRouterProbeSanitizedCloseout(
        closeout_id="openrouter-hy3-capability-probe-closeout-v1",
        authorization_id="openrouter-hy3-capability-probe-auth-v1",
        execution_id="openrouter-hy3-capability-probe-v1",
        source_commit="a" * 40,
        terminal_outcome="closed_terminal_provider_failure",
        failure_stage="pre_inference_authentication",
        failure_class="provider_authentication_failed",
        attempt_count=1,
        provider_success_count=0,
        retained_success_count=0,
        replacement_count=0,
        network_request_count=1,
        response_kind="completion",
        http_status=401,
        safe_error_code="PROVIDER_AUTHENTICATION_FAILED",
        provider_error_code="401",
        provider_error_message="Missing Authentication header",
        response_body_sha256="b" * 64,
        response_body_bytes=64,
        terminal_receipt_sha256="c" * 64,
        journal_sha256="d" * 64,
        raw_responses_sha256="e" * 64,
        parsed_responses_sha256="f" * 64,
        prompt_bundle_sha256="1" * 64,
        preflight_receipt_sha256="2" * 64,
        posthoc_auth_diagnostic=OpenRouterProbePosthocAuthDiagnostic(
            authorization_header_present=True,
            authorization_scheme="Bearer",
            proxy_entry_count=0,
            proxy_detected=False,
            diagnostic_recorded_at=datetime(2026, 7, 14, tzinfo=UTC),
        ),
        permitted_claim=(
            "The one-time OpenRouter Hy3 capability probe closed on its first cold-call "
            "attempt after an HTTP 401 authentication failure; no completion, generation "
            "metadata, or cache telemetry was obtained."
        ),
        non_claims=(
            "No Hy3 model inference succeeded.",
            "No cache hit, miss, read, write, discount, saving, or latency result was observed.",
            "The evidence does not establish whether credential validity, credential entry, "
            "header delivery, or another authentication factor caused the 401 response.",
            "No A/B/C pilot or retained benchmark is authorized.",
        ),
        residual_harness_gaps=(
            "Credential continuity was not fingerprinted.",
            "Live header delivery was not proven.",
        ),
        next_gate="terminal_review_and_continuity_update",
        closed_at=datetime(2026, 7, 14, tzinfo=UTC),
        sanitized_at=datetime(2026, 7, 14, tzinfo=UTC),
    )


def test_sanitized_closeout_accepts_terminal_authentication_failure() -> None:
    result = _result()
    assert result.http_status == 401
    assert result.authorization_consumed is True
    assert result.rerun_permitted is False


def test_sanitized_closeout_rejects_credential_material() -> None:
    with pytest.raises(ValidationError):
        OpenRouterProbeSanitizedCloseout.model_validate(
            _result().model_dump() | {"provider_error_message": "Bearer sk-or-v1-secret"}
        )


def test_posthoc_diagnostic_cannot_claim_provider_wire_delivery() -> None:
    diagnostic = _result().posthoc_auth_diagnostic
    assert diagnostic.network_request_performed is False
    assert diagnostic.proves_provider_received_header is False
