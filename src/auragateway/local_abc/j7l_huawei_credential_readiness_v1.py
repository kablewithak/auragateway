"""Deterministic Huawei credential-readiness boundary for J7L qualification."""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import StrEnum
from typing import Final, Literal, Protocol, Self, cast

from pydantic import BaseModel, ConfigDict, model_validator

CATALOG_ENDPOINT_URL: Final[Literal["https://api-ap-southeast-1.modelarts-maas.com/v2/models"]] = (
    "https://api-ap-southeast-1.modelarts-maas.com/v2/models"
)

EXACT_MODEL_IDENTIFIER: Final[Literal["glm-5.2"]] = "glm-5.2"

MAXIMUM_CATALOG_REQUESTS: Final[Literal[1]] = 1
MAXIMUM_MODEL_INFERENCE_REQUESTS: Final[Literal[0]] = 0


class ReadinessStatus(StrEnum):
    READY = "READY"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    ENTITLEMENT_DENIED = "ENTITLEMENT_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    TRANSPORT_FAILED = "TRANSPORT_FAILED"
    CATALOG_INVALID = "CATALOG_INVALID"
    MODEL_NOT_PRESENT = "MODEL_NOT_PRESENT"


class CredentialReadinessError(RuntimeError):
    """Expected transport failure at the bounded catalog boundary."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HttpResult(FrozenModel):
    status_code: int
    body: bytes


class CredentialReadinessResultV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    provider: Literal["huawei_modelarts_maas"] = "huawei_modelarts_maas"
    exact_model_identifier: Literal["glm-5.2"] = EXACT_MODEL_IDENTIFIER
    catalog_endpoint_url: Literal["https://api-ap-southeast-1.modelarts-maas.com/v2/models"] = (
        CATALOG_ENDPOINT_URL
    )
    status: ReadinessStatus
    provider_http_requests_attempted: Literal[1] = MAXIMUM_CATALOG_REQUESTS
    catalog_requests_attempted: Literal[1] = MAXIMUM_CATALOG_REQUESTS
    model_inference_requests_attempted: Literal[0] = MAXIMUM_MODEL_INFERENCE_REQUESTS
    automatic_retries_performed: Literal[0] = 0
    j7l_reference_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    binding_freeze_performed: Literal[False] = False
    credential_value_persisted: Literal[False] = False
    authorization_header_persisted: Literal[False] = False
    raw_provider_error_body_persisted: Literal[False] = False
    catalog_model_present: bool

    @model_validator(mode="after")
    def validate_status_consistency(self) -> Self:
        if self.status is ReadinessStatus.READY and not self.catalog_model_present:
            raise ValueError("READY requires exact model presence")

        if self.status is not ReadinessStatus.READY and self.catalog_model_present:
            raise ValueError("non-READY status cannot claim exact model presence")

        return self


class CatalogClient(Protocol):
    def get_catalog(
        self,
        *,
        url: str,
        api_key: str,
    ) -> HttpResult:
        """Perform exactly one catalog GET or raise CredentialReadinessError."""


def _result(
    status: ReadinessStatus,
    *,
    catalog_model_present: bool = False,
) -> CredentialReadinessResultV1:
    return CredentialReadinessResultV1(
        status=status,
        catalog_model_present=catalog_model_present,
    )


def _classify_non_success(status_code: int) -> ReadinessStatus:
    if status_code == 401:
        return ReadinessStatus.AUTHENTICATION_FAILED

    if status_code == 403:
        return ReadinessStatus.ENTITLEMENT_DENIED

    if status_code == 429:
        return ReadinessStatus.RATE_LIMITED

    if 500 <= status_code <= 599:
        return ReadinessStatus.PROVIDER_UNAVAILABLE

    return ReadinessStatus.CATALOG_INVALID


def _catalog_contains_exact_model(body: bytes) -> bool:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("catalog is not valid UTF-8 JSON") from None

    if not isinstance(payload, Mapping):
        raise ValueError("catalog root is not an object")

    data = payload.get("data")

    if not isinstance(data, list):
        raise ValueError("catalog data field is not a list")

    matches = [
        item
        for item in data
        if isinstance(item, Mapping) and item.get("id") == EXACT_MODEL_IDENTIFIER
    ]

    return len(matches) == 1


def evaluate_catalog_result(
    result: HttpResult,
) -> CredentialReadinessResultV1:
    """Classify one catalog response without retaining credential or raw error content."""

    if result.status_code != 200:
        return _result(_classify_non_success(result.status_code))

    try:
        exact_model_present = _catalog_contains_exact_model(result.body)
    except ValueError:
        return _result(ReadinessStatus.CATALOG_INVALID)

    if not exact_model_present:
        return _result(ReadinessStatus.MODEL_NOT_PRESENT)

    return _result(
        ReadinessStatus.READY,
        catalog_model_present=True,
    )


def probe_credential_readiness(
    *,
    api_key: str,
    client: CatalogClient,
) -> CredentialReadinessResultV1:
    """Execute exactly one injected catalog request with no retry or inference seam."""

    if not api_key.strip():
        return _result(ReadinessStatus.AUTHENTICATION_FAILED)

    try:
        result = client.get_catalog(
            url=CATALOG_ENDPOINT_URL,
            api_key=api_key,
        )
    except CredentialReadinessError:
        return _result(ReadinessStatus.TRANSPORT_FAILED)

    return evaluate_catalog_result(result)


def public_result_json(
    result: CredentialReadinessResultV1,
) -> str:
    """Serialize only the bounded metadata-safe readiness result."""

    payload = cast(
        dict[str, object],
        result.model_dump(mode="json"),
    )

    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
