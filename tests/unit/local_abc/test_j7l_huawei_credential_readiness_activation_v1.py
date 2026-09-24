from __future__ import annotations

import hashlib
import io
import json
import shutil
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import j7l_huawei_credential_readiness_activation_v1 as subject
from auragateway.local_abc import j7l_huawei_credential_readiness_v1 as readiness

_PLAN = subject.READINESS_PLAN_PATH
_CLASSIFIER_SOURCE = Path("src/auragateway/local_abc/j7l_huawei_credential_readiness_v1.py")
_CLASSIFIER_TEST = Path("tests/unit/local_abc/test_j7l_huawei_credential_readiness_v1.py")
_ACTIVATION_SOURCE = subject.ACTIVATION_SOURCE_PATH
_ACTIVATION_TEST = subject.ACTIVATION_TEST_PATH


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_assets(root: Path) -> None:
    for relative in (
        _PLAN,
        _CLASSIFIER_SOURCE,
        _CLASSIFIER_TEST,
        _ACTIVATION_SOURCE,
        _ACTIVATION_TEST,
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative, target)


def _write_authorization(root: Path) -> None:
    payload = {
        "schema_version": "1.0.0",
        "authorization_id": "j7l-huawei-credential-readiness-authorization-v1",
        "status": "active",
        "readiness_plan_path": _PLAN.as_posix(),
        "readiness_plan_sha256": _sha256_file(root / _PLAN),
        "activation_source_path": _ACTIVATION_SOURCE.as_posix(),
        "activation_source_sha256": _sha256_file(root / _ACTIVATION_SOURCE),
        "confirmation_phrase": "EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE",
        "provider": "huawei_modelarts_maas",
        "exact_model_identifier": "glm-5.2",
        "credential_env_name": "HUAWEI_MAAS_API_KEY",
        "provider_call_authorized": True,
        "credential_access_authorized": True,
        "network_access_authorized": True,
        "execution_command_available": True,
        "maximum_provider_http_requests": 1,
        "maximum_catalog_requests": 1,
        "maximum_model_inference_requests": 0,
        "zero_spend_confirmation_required": True,
        "external_spend_ceiling_zar": 0,
        "automatic_retry_permitted": False,
        "resume_permitted": False,
        "rerun_permitted": False,
        "j7l_reference_request_permitted": False,
        "jev_request_permitted": False,
        "binding_freeze_permitted": False,
        "authorization_consumed_on_first_network_attempt": True,
        "clean_main_required": True,
    }
    path = root / subject.AUTHORIZATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _catalog_body(*model_ids: str) -> bytes:
    return json.dumps(
        {"object": "list", "data": [{"id": model_id} for model_id in model_ids]},
        separators=(",", ":"),
    ).encode("utf-8")


class FakeCatalogClient:
    def __init__(
        self,
        result: readiness.HttpResult | None = None,
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
    ) -> readiness.HttpResult:
        self.calls.append((url, api_key))
        if self.transport_failure:
            raise readiness.CredentialReadinessError("synthetic transport failure")
        if self.result is None:
            raise AssertionError("fake result is required")
        return self.result


class ConsumptionAwareClient(FakeCatalogClient):
    def __init__(self, root: Path, result: readiness.HttpResult) -> None:
        super().__init__(result)
        self.root = root

    def get_catalog(
        self,
        *,
        url: str,
        api_key: str,
    ) -> readiness.HttpResult:
        assert (self.root / subject.CONSUMPTION_PATH).is_file()
        return super().get_catalog(url=url, api_key=api_key)


def _no_live_git_check(_: Path) -> None:
    return None


class _Response:
    def __init__(self, body: bytes) -> None:
        self.status = 200
        self._body = body

    def read(self, amount: int = -1) -> bytes:
        del amount
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        del exc_type, exc_value, traceback


class _SuccessOpener:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls: list[tuple[urllib.request.Request, int]] = []

    def open(self, request: urllib.request.Request, timeout: int) -> _Response:
        self.calls.append((request, timeout))
        return _Response(self.body)


class _ErrorBody(io.BytesIO):
    def read(self, size: int | None = -1, /) -> bytes:
        del size
        raise AssertionError("HTTP error body must not be read")


class _HttpErrorOpener:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.calls = 0

    def open(self, request: urllib.request.Request, timeout: int) -> _Response:
        del request, timeout
        self.calls += 1
        raise urllib.error.HTTPError(
            url=readiness.CATALOG_ENDPOINT_URL,
            code=self.status_code,
            msg="synthetic error",
            hdrs=Message(),
            fp=_ErrorBody(b"provider-secret-error-body"),
        )


def test_validate_is_non_live_without_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "must-not-be-read")

    result = subject.validate_activation(tmp_path)

    assert result["status"] == "J7L_HUAWEI_CREDENTIAL_READINESS_ACTIVATION_V1_PASS"
    assert result["authorization_present"] is False
    assert result["provider_call_performed"] is False
    assert result["credential_accessed"] is False
    assert result["network_access_performed"] is False


def test_urllib_adapter_performs_one_authenticated_catalog_get(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _SuccessOpener(_catalog_body("glm-5.2"))

    def build_opener(*handlers: object) -> _SuccessOpener:
        assert any(isinstance(handler, subject._NoRedirect) for handler in handlers)
        return opener

    monkeypatch.setattr(urllib.request, "build_opener", build_opener)
    client = subject.UrllibHuaweiCatalogClient()

    result = client.get_catalog(
        url=readiness.CATALOG_ENDPOINT_URL,
        api_key="synthetic-secret",
    )

    assert result.status_code == 200
    assert len(opener.calls) == 1
    request, timeout = opener.calls[0]
    assert request.full_url == readiness.CATALOG_ENDPOINT_URL
    assert request.method == "GET"
    assert request.get_header("Authorization") == "Bearer synthetic-secret"
    assert timeout == 60


def test_urllib_adapter_maps_http_error_without_reading_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _HttpErrorOpener(401)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_: opener)
    client = subject.UrllibHuaweiCatalogClient()

    result = client.get_catalog(
        url=readiness.CATALOG_ENDPOINT_URL,
        api_key="synthetic-secret",
    )

    assert result.status_code == 401
    assert result.body == b""
    assert opener.calls == 1


def test_execute_ready_consumes_authorization_and_performs_one_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _write_authorization(tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    client = ConsumptionAwareClient(
        tmp_path,
        readiness.HttpResult(
            status_code=200,
            body=_catalog_body("glm-5.1", "glm-5.2"),
        ),
    )

    result = subject.execute_readiness(
        tmp_path,
        confirmation="EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE",
        zero_spend_confirmed=True,
        client=client,
        live_boundary=_no_live_git_check,
    )

    observed = cast(dict[str, object], result["readiness"])
    assert observed["status"] == "READY"
    assert observed["model_inference_requests_attempted"] == 0
    assert observed["automatic_retries_performed"] == 0
    assert observed["j7l_reference_requests_performed"] == 0
    assert observed["jev_requests_performed"] == 0
    assert observed["binding_freeze_performed"] is False
    assert len(client.calls) == 1
    assert (tmp_path / subject.CONSUMPTION_PATH).is_file()
    assert (tmp_path / subject.RESULT_PATH).is_file()

    encoded = (tmp_path / subject.RESULT_PATH).read_text(encoding="utf-8")
    assert "synthetic-secret" not in encoded
    assert "Authorization" not in encoded


@pytest.mark.parametrize(
    ("status_code", "expected_status"),
    [
        (401, "AUTHENTICATION_FAILED"),
        (403, "ENTITLEMENT_DENIED"),
        (429, "RATE_LIMITED"),
        (503, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_execute_preserves_bounded_http_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_status: str,
) -> None:
    _copy_assets(tmp_path)
    _write_authorization(tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    client = FakeCatalogClient(
        readiness.HttpResult(status_code=status_code, body=b"provider-secret-error-body")
    )

    result = subject.execute_readiness(
        tmp_path,
        confirmation="EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE",
        zero_spend_confirmed=True,
        client=client,
        live_boundary=_no_live_git_check,
    )

    observed = cast(dict[str, object], result["readiness"])
    assert observed["status"] == expected_status
    assert len(client.calls) == 1
    encoded = (tmp_path / subject.RESULT_PATH).read_text(encoding="utf-8")
    assert "provider-secret-error-body" not in encoded
    assert "synthetic-secret" not in encoded


def test_execute_transport_failure_is_terminal_and_not_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _write_authorization(tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    client = FakeCatalogClient(transport_failure=True)

    result = subject.execute_readiness(
        tmp_path,
        confirmation="EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE",
        zero_spend_confirmed=True,
        client=client,
        live_boundary=_no_live_git_check,
    )

    observed = cast(dict[str, object], result["readiness"])
    assert observed["status"] == "TRANSPORT_FAILED"
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    ("body", "expected_status"),
    [
        (b"{not-json", "CATALOG_INVALID"),
        (_catalog_body("glm-5.1"), "MODEL_NOT_PRESENT"),
    ],
)
def test_execute_classifies_success_body_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
    expected_status: str,
) -> None:
    _copy_assets(tmp_path)
    _write_authorization(tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    client = FakeCatalogClient(readiness.HttpResult(status_code=200, body=body))

    result = subject.execute_readiness(
        tmp_path,
        confirmation="EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE",
        zero_spend_confirmed=True,
        client=client,
        live_boundary=_no_live_git_check,
    )

    observed = cast(dict[str, object], result["readiness"])
    assert observed["status"] == expected_status
    assert len(client.calls) == 1


def test_missing_credential_does_not_consume_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _write_authorization(tmp_path)
    monkeypatch.delenv("HUAWEI_MAAS_API_KEY", raising=False)
    client = FakeCatalogClient(readiness.HttpResult(status_code=200, body=_catalog_body("glm-5.2")))

    with pytest.raises(subject.ActivationError, match="API key is unavailable"):
        subject.execute_readiness(
            tmp_path,
            confirmation="EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE",
            zero_spend_confirmed=True,
            client=client,
            live_boundary=_no_live_git_check,
        )

    assert client.calls == []
    assert not (tmp_path / subject.CONSUMPTION_PATH).exists()


def test_wrong_confirmation_precedes_credential_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _write_authorization(tmp_path)

    def forbidden_credential_read(_: str) -> str:
        raise AssertionError("credential must not be read before confirmation")

    monkeypatch.setattr(subject, "_read_api_key", forbidden_credential_read)

    with pytest.raises(subject.ActivationError, match="confirmation phrase"):
        subject.execute_readiness(
            tmp_path,
            confirmation="WRONG",
            zero_spend_confirmed=True,
            client=FakeCatalogClient(),
            live_boundary=_no_live_git_check,
        )


def test_second_execution_is_blocked_after_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    _write_authorization(tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    first = FakeCatalogClient(readiness.HttpResult(status_code=200, body=_catalog_body("glm-5.2")))

    subject.execute_readiness(
        tmp_path,
        confirmation="EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE",
        zero_spend_confirmed=True,
        client=first,
        live_boundary=_no_live_git_check,
    )

    second = FakeCatalogClient(readiness.HttpResult(status_code=200, body=_catalog_body("glm-5.2")))
    with pytest.raises(subject.ActivationError, match="consumed or result evidence exists"):
        subject.execute_readiness(
            tmp_path,
            confirmation="EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE",
            zero_spend_confirmed=True,
            client=second,
            live_boundary=_no_live_git_check,
        )

    assert second.calls == []
