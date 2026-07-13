from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.contracts.provider import ProviderErrorCode
from auragateway.contracts.provider_diagnostics import (
    ProviderFailureDiagnostic,
    ProviderFailureFamily,
)


def _diagnostic(**overrides: object) -> ProviderFailureDiagnostic:
    payload: dict[str, object] = {
        "model_alias": "groq-gpt-oss-20b",
        "request_id_sha256": "a" * 64,
        "family": ProviderFailureFamily.REQUEST_REJECTED,
        "exception_class_allowlisted": "BadRequestError",
        "http_status_code": 400,
        "provider_error_type_allowlisted": "invalid_request_error",
        "provider_error_code_allowlisted": "context_length_exceeded",
        "provider_error_param_allowlisted": "messages",
        "provider_request_id_sha256": "b" * 64,
        "retryable": False,
        "mapped_provider_error_code": ProviderErrorCode.INVALID_RESPONSE,
    }
    payload.update(overrides)
    return ProviderFailureDiagnostic.model_validate(payload)


def test_provider_failure_diagnostic_accepts_only_bounded_metadata() -> None:
    diagnostic = _diagnostic()

    assert diagnostic.family is ProviderFailureFamily.REQUEST_REJECTED
    assert diagnostic.http_status_code == 400
    assert diagnostic.provider_error_param_allowlisted == "messages"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("exception_class_allowlisted", "Bad Request Error"),
        ("provider_error_type_allowlisted", "invalid request"),
        ("provider_error_code_allowlisted", "secret=value"),
        ("provider_error_param_allowlisted", "messages[0]"),
    ],
)
def test_provider_failure_diagnostic_rejects_unbounded_tokens(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError):
        _diagnostic(**{field: value})


def test_provider_failure_diagnostic_rejects_raw_extra_fields() -> None:
    with pytest.raises(ValidationError):
        _diagnostic(raw_error_body={"message": "do not retain"})
