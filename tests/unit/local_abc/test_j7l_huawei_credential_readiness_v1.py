from __future__ import annotations

import json

import pytest

from auragateway.local_abc.j7l_huawei_credential_readiness_v1 import (
    CATALOG_ENDPOINT_URL,
    CredentialReadinessError,
    HttpResult,
    ReadinessStatus,
    probe_credential_readiness,
    public_result_json,
)


class FakeCatalogClient:
    def __init__(
        self,
        result: HttpResult | None = None,
        *,
        transport_failure: bool = False,
    ) -> None:
        self.result = result
        self.transport_failure = transport_failure
        self.calls: list[tuple[str, str]] = []

    def get_catalog(
        self,
        *,
        url: str,
        api_key: str,
    ) -> HttpResult:
        self.calls.append((url, api_key))

        if self.transport_failure:
            raise CredentialReadinessError("synthetic transport failure")

        if self.result is None:
            raise AssertionError("fake result is required")

        return self.result


def _catalog_body(*model_ids: str) -> bytes:
    return json.dumps(
        {
            "object": "list",
            "data": [{"id": model_id} for model_id in model_ids],
        },
        separators=(",", ":"),
    ).encode("utf-8")


@pytest.mark.parametrize(
    ("status_code", "expected_status"),
    [
        (401, ReadinessStatus.AUTHENTICATION_FAILED),
        (403, ReadinessStatus.ENTITLEMENT_DENIED),
        (429, ReadinessStatus.RATE_LIMITED),
        (500, ReadinessStatus.PROVIDER_UNAVAILABLE),
    ],
)
def test_non_success_statuses_are_distinct(
    status_code: int,
    expected_status: ReadinessStatus,
) -> None:
    client = FakeCatalogClient(HttpResult(status_code=status_code, body=b"secret-error-body"))

    result = probe_credential_readiness(
        api_key="synthetic-secret",
        client=client,
    )

    assert result.status is expected_status
    assert result.catalog_model_present is False
    assert result.provider_http_requests_attempted == 1
    assert result.model_inference_requests_attempted == 0
    assert result.automatic_retries_performed == 0
    assert result.raw_provider_error_body_persisted is False
    assert client.calls == [(CATALOG_ENDPOINT_URL, "synthetic-secret")]


def test_http_200_with_exact_model_is_ready() -> None:
    client = FakeCatalogClient(
        HttpResult(
            status_code=200,
            body=_catalog_body("glm-5.1", "glm-5.2", "deepseek-v4-flash"),
        )
    )

    result = probe_credential_readiness(
        api_key="synthetic-secret",
        client=client,
    )

    assert result.status is ReadinessStatus.READY
    assert result.catalog_model_present is True
    assert result.model_inference_requests_attempted == 0
    assert result.j7l_reference_requests_performed == 0
    assert result.jev_requests_performed == 0
    assert result.binding_freeze_performed is False
    assert client.calls == [(CATALOG_ENDPOINT_URL, "synthetic-secret")]


def test_transport_failure_is_distinct_and_not_retried() -> None:
    client = FakeCatalogClient(transport_failure=True)

    result = probe_credential_readiness(
        api_key="synthetic-secret",
        client=client,
    )

    assert result.status is ReadinessStatus.TRANSPORT_FAILED
    assert result.automatic_retries_performed == 0
    assert result.model_inference_requests_attempted == 0
    assert client.calls == [(CATALOG_ENDPOINT_URL, "synthetic-secret")]


def test_malformed_success_catalog_is_invalid() -> None:
    client = FakeCatalogClient(
        HttpResult(
            status_code=200,
            body=b"{not-json",
        )
    )

    result = probe_credential_readiness(
        api_key="synthetic-secret",
        client=client,
    )

    assert result.status is ReadinessStatus.CATALOG_INVALID
    assert result.catalog_model_present is False
    assert len(client.calls) == 1


def test_success_catalog_without_exact_model_is_not_ready() -> None:
    client = FakeCatalogClient(
        HttpResult(
            status_code=200,
            body=_catalog_body("glm-5.1", "deepseek-v4-flash"),
        )
    )

    result = probe_credential_readiness(
        api_key="synthetic-secret",
        client=client,
    )

    assert result.status is ReadinessStatus.MODEL_NOT_PRESENT
    assert result.catalog_model_present is False
    assert len(client.calls) == 1


def test_public_result_cannot_persist_secret_or_raw_error_body() -> None:
    client = FakeCatalogClient(
        HttpResult(
            status_code=401,
            body=b"provider-secret-error-body",
        )
    )

    result = probe_credential_readiness(
        api_key="synthetic-secret",
        client=client,
    )
    encoded = public_result_json(result)

    assert "synthetic-secret" not in encoded
    assert "provider-secret-error-body" not in encoded
    assert '"credential_value_persisted":false' in encoded
    assert '"authorization_header_persisted":false' in encoded
    assert '"raw_provider_error_body_persisted":false' in encoded
