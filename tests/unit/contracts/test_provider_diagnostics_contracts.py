from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.contracts.provider import ProviderErrorCode
from auragateway.contracts.provider_diagnostics import (
    AssistantContentState,
    ProviderFailureDiagnostic,
    ProviderFailureFamily,
    ProviderFinishReason,
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


def _missing_content_diagnostic(**overrides: object) -> ProviderFailureDiagnostic:
    payload: dict[str, object] = {
        "model_alias": "groq-gpt-oss-20b",
        "request_id_sha256": "a" * 64,
        "family": ProviderFailureFamily.ASSISTANT_CONTENT_MISSING,
        "retryable": False,
        "mapped_provider_error_code": ProviderErrorCode.AMBIGUOUS_RESPONSE,
        "response_id_sha256": "c" * 64,
        "response_choice_count": 1,
        "response_finish_reason_allowlisted": ProviderFinishReason.STOP,
        "assistant_content_state": AssistantContentState.NULL,
        "response_usage_present": True,
        "response_completion_tokens": 20,
        "reasoning_present": True,
        "reasoning_byte_count": 32,
        "tool_call_count": 0,
        "refusal_present": False,
        "refusal_byte_count": 0,
    }
    payload.update(overrides)
    return ProviderFailureDiagnostic.model_validate(payload)


def _schema_invalid_diagnostic(**overrides: object) -> ProviderFailureDiagnostic:
    payload: dict[str, object] = {
        "model_alias": "groq-gpt-oss-20b",
        "request_id_sha256": "a" * 64,
        "family": ProviderFailureFamily.RESPONSE_SCHEMA_INVALID,
        "exception_class_allowlisted": "ValidationError",
        "retryable": False,
        "mapped_provider_error_code": ProviderErrorCode.INVALID_RESPONSE,
        "response_validation_error_count": 1,
        "response_validation_locations_allowlisted": ("choices.*.message.tool_calls",),
        "response_validation_types_allowlisted": ("tuple_type",),
    }
    payload.update(overrides)
    return ProviderFailureDiagnostic.model_validate(payload)


def test_provider_failure_diagnostic_accepts_only_bounded_metadata() -> None:
    diagnostic = _diagnostic()

    assert diagnostic.family is ProviderFailureFamily.REQUEST_REJECTED
    assert diagnostic.http_status_code == 400
    assert diagnostic.provider_error_param_allowlisted == "messages"
    assert diagnostic.schema_version == "1.2.0"


def test_missing_content_diagnostic_requires_complete_response_shape() -> None:
    diagnostic = _missing_content_diagnostic()

    assert diagnostic.assistant_content_state is AssistantContentState.NULL
    assert diagnostic.response_finish_reason_allowlisted is ProviderFinishReason.STOP
    assert diagnostic.reasoning_present is True
    assert diagnostic.reasoning_byte_count == 32


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


@pytest.mark.parametrize(
    "unsafe_field",
    [
        "raw_error_body",
        "raw_exception_message",
        "reasoning_text",
        "refusal_text",
        "tool_call_arguments",
        "raw_response",
    ],
)
def test_provider_failure_diagnostic_rejects_raw_extra_fields(
    unsafe_field: str,
) -> None:
    with pytest.raises(ValidationError):
        _diagnostic(**{unsafe_field: "do not retain"})


def test_non_response_failure_rejects_response_shape_metadata() -> None:
    with pytest.raises(ValidationError, match="reserved for assistant-content-missing"):
        _diagnostic(response_choice_count=1)


def test_missing_content_failure_rejects_incomplete_response_shape() -> None:
    with pytest.raises(ValidationError, match="complete response-shape metadata"):
        _missing_content_diagnostic(reasoning_byte_count=None)


def test_completion_tokens_require_usage_metadata() -> None:
    with pytest.raises(ValidationError, match="completion tokens require"):
        _missing_content_diagnostic(response_usage_present=False)


def test_present_reasoning_requires_positive_byte_count() -> None:
    with pytest.raises(ValidationError, match="positive byte count"):
        _missing_content_diagnostic(reasoning_present=True, reasoning_byte_count=0)


def test_present_refusal_requires_positive_byte_count() -> None:
    with pytest.raises(ValidationError, match="positive byte count"):
        _missing_content_diagnostic(refusal_present=True, refusal_byte_count=0)


def test_schema_invalid_diagnostic_accepts_bounded_validation_metadata() -> None:
    diagnostic = _schema_invalid_diagnostic()

    assert diagnostic.response_validation_error_count == 1
    assert diagnostic.response_validation_locations_allowlisted == ("choices.*.message.tool_calls",)
    assert diagnostic.response_validation_types_allowlisted == ("tuple_type",)


def test_non_schema_failure_rejects_response_validation_metadata() -> None:
    with pytest.raises(ValidationError, match="reserved for response-schema-invalid"):
        _diagnostic(
            response_validation_error_count=1,
            response_validation_locations_allowlisted=("choices",),
            response_validation_types_allowlisted=("too_short",),
        )


def test_validation_error_count_requires_locations_and_types() -> None:
    with pytest.raises(ValidationError, match="require an allowlisted location tuple"):
        _schema_invalid_diagnostic(response_validation_locations_allowlisted=None)

    with pytest.raises(ValidationError, match="require an allowlisted type tuple"):
        _schema_invalid_diagnostic(response_validation_types_allowlisted=None)


def test_validation_locations_reject_unbounded_provider_paths() -> None:
    with pytest.raises(ValidationError, match="bounded safe paths"):
        _schema_invalid_diagnostic(
            response_validation_locations_allowlisted=("choices.0.message.tool_calls[secret]",)
        )


def test_validation_metadata_rejects_duplicates() -> None:
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        _schema_invalid_diagnostic(
            response_validation_types_allowlisted=("tuple_type", "tuple_type")
        )
