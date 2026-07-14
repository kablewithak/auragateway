from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.benchmark import (
    groq_cache_telemetry_reauthorization_execution_runner as runner,
)
from auragateway.benchmark.groq_cache_telemetry_reauthorization_execution_runner import (
    ReauthorizationExecutionError,
    execute_reauthorization,
    validate_reauthorization_execution,
    verify_reauthorization_execution,
)

_EXECUTION_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-v1")
_ADR_PATH = Path("docs/adr/groq-cache-telemetry-reauthorization-activation.md")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_Groq_Cache_Telemetry_Reauthorization_Activation.md")


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _copy_activation_assets(repo_root: Path) -> None:
    authorization = _json_object(_EXECUTION_ROOT / "authorization.json")
    bindings = authorization["bindings"]
    assert isinstance(bindings, list)

    relative_paths = [
        _EXECUTION_ROOT / "authorization.json",
        _EXECUTION_ROOT / "runtime_policy.json",
        _EXECUTION_ROOT / "activation_report.json",
        _EXECUTION_ROOT / "activation_manifest.json",
        _ADR_PATH,
        _REPORT_PATH,
    ]
    for binding in bindings:
        assert isinstance(binding, dict)
        if binding["protected_local"] is True:
            continue
        path = binding["path"]
        assert isinstance(path, str)
        relative_paths.append(Path(path))

    for relative_path in relative_paths:
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class _FakeDetails:
    def __init__(self, value: int | None, *, present: bool) -> None:
        self.cached_tokens = value
        self.model_fields_set: set[str] = {"cached_tokens"} if present else set()


class _FakeUsage:
    def __init__(
        self,
        value: int | None,
        *,
        details_present: bool,
        cached_present: bool,
    ) -> None:
        self.prompt_tokens_details = (
            _FakeDetails(value, present=cached_present) if details_present else None
        )
        self.model_fields_set: set[str] = {"prompt_tokens_details"} if details_present else set()


class _FakeParsed:
    def __init__(
        self,
        payload: dict[str, object],
        *,
        usage_present: bool,
        details_present: bool,
        cached_present: bool,
        cached_value: int | None,
    ) -> None:
        self._payload = payload
        self.usage = (
            _FakeUsage(
                cached_value,
                details_present=details_present,
                cached_present=cached_present,
            )
            if usage_present
            else None
        )
        self.model_fields_set: set[str] = {"usage"} if usage_present else set()

    def model_dump(
        self,
        *,
        mode: str = "python",
        exclude_none: bool = False,
        exclude_unset: bool = False,
    ) -> dict[str, object]:
        del mode, exclude_none, exclude_unset
        return self._payload


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.content = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.status_code = 200


class _FakeRawResponse:
    def __init__(
        self,
        payload: dict[str, object],
        parsed: _FakeParsed,
    ) -> None:
        self.http_response: runner._HttpResponse = _FakeHttpResponse(payload)
        self._parsed = parsed
        self.closed = False

    def parse(self) -> runner._ParsedCompletion:
        return self._parsed

    def close(self) -> None:
        self.closed = True


class _FakeClient:
    def __init__(self, responses: list[_FakeRawResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []
        self.closed = False

    def create(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_completion_tokens: int,
        temperature: float,
        stream: bool,
        store: bool,
        reasoning_effort: str,
    ) -> _FakeRawResponse:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "max_completion_tokens": max_completion_tokens,
                "temperature": temperature,
                "stream": stream,
                "store": store,
                "reasoning_effort": reasoning_effort,
            }
        )
        return self.responses[len(self.calls) - 1]

    def close(self) -> None:
        self.closed = True


def _absent_response() -> _FakeRawResponse:
    payload: dict[str, object] = {
        "id": "response",
        "model": "openai/gpt-oss-20b",
        "choices": [{"message": {"role": "assistant", "content": "protected"}}],
        "usage": {
            "prompt_tokens": 1401,
            "completion_tokens": 27,
        },
    }
    parsed = _FakeParsed(
        payload,
        usage_present=True,
        details_present=False,
        cached_present=False,
        cached_value=None,
    )
    return _FakeRawResponse(payload, parsed)


def _positive_response(value: int) -> _FakeRawResponse:
    payload: dict[str, object] = {
        "id": "response",
        "model": "openai/gpt-oss-20b",
        "choices": [{"message": {"role": "assistant", "content": "protected"}}],
        "usage": {
            "prompt_tokens": 1401,
            "completion_tokens": 27,
            "prompt_tokens_details": {"cached_tokens": value},
        },
    }
    parsed = _FakeParsed(
        payload,
        usage_present=True,
        details_present=True,
        cached_present=True,
        cached_value=value,
    )
    return _FakeRawResponse(payload, parsed)


def _wire_positive_parsed_absent_response(value: int) -> _FakeRawResponse:
    payload: dict[str, object] = {
        "id": "response",
        "model": "openai/gpt-oss-20b",
        "choices": [{"message": {"role": "assistant", "content": "protected"}}],
        "usage": {
            "prompt_tokens": 1401,
            "completion_tokens": 27,
            "prompt_tokens_details": {"cached_tokens": value},
        },
    }
    parsed = _FakeParsed(
        payload,
        usage_present=True,
        details_present=False,
        cached_present=False,
        cached_value=None,
    )
    return _FakeRawResponse(payload, parsed)


def _patch_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = runner._FrozenProviderRequest.model_validate(
        {
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
            "model": "openai/gpt-oss-20b",
            "max_completion_tokens": 32,
            "temperature": 0.0,
            "stream": False,
            "store": False,
            "reasoning_effort": "low",
        }
    )
    monkeypatch.setattr(
        runner,
        "_load_protected_prompt",
        lambda repo_root, authorization: (request, "a" * 64),
    )
    monkeypatch.setattr(runner, "_installed_sdk_version", lambda: "1.5.0")


def test_validate_accepts_active_non_live_authorization(tmp_path: Path) -> None:
    _copy_activation_assets(tmp_path)

    summary = validate_reauthorization_execution(tmp_path)

    assert summary.command == "validate"
    assert summary.authorization_status.value == "active"
    assert summary.planned_attempt_count == 2
    assert summary.provider_call_count == 0
    assert summary.execution_completed is False
    assert summary.live_provider_called is False
    assert summary.credential_checked is False
    assert summary.provider_calls_permitted is True


def test_validate_does_not_read_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = validate_reauthorization_execution(tmp_path)

    assert summary.credential_checked is False
    assert summary.live_provider_called is False


def test_validate_rejects_activation_hash_drift(tmp_path: Path) -> None:
    _copy_activation_assets(tmp_path)
    report_path = tmp_path / _EXECUTION_ROOT / "activation_report.json"
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        ReauthorizationExecutionError,
        match="activation manifest",
    ):
        validate_reauthorization_execution(tmp_path)


def test_execute_absent_wire_field_and_verify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    _patch_prompt(monkeypatch)
    clock = _Clock()
    client = _FakeClient([_absent_response(), _absent_response()])

    summary = execute_reauthorization(
        tmp_path,
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        confirmation="EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE",
        client=client,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert summary.command == "run"
    assert summary.provider_call_count == 2
    assert summary.execution_completed is True
    assert client.closed is True
    assert len(client.calls) == 2
    assert client.calls[0] == client.calls[1]

    report = _json_object(tmp_path / _EXECUTION_ROOT / "report.json")
    assert report["outcome"] == "wire_field_absent"
    assert report["exact_provider_wire_omission_claim_permitted"] is True
    assert report["provider_cache_usage_claim_permitted_for_execution"] is False

    verified = verify_reauthorization_execution(tmp_path)
    assert verified.command == "verify"
    assert verified.provider_call_count == 2
    assert verified.provider_calls_permitted is False


def test_execute_positive_wire_and_parsed_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    _patch_prompt(monkeypatch)
    clock = _Clock()
    client = _FakeClient([_positive_response(0), _positive_response(700)])

    execute_reauthorization(
        tmp_path,
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        confirmation="EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE",
        client=client,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    report = _json_object(tmp_path / _EXECUTION_ROOT / "report.json")
    assert report["outcome"] == "wire_field_present_and_parsed"
    assert report["raw_numeric_sample_count"] == 2
    assert report["parsed_numeric_sample_count"] == 2
    assert report["provider_cache_usage_claim_permitted_for_execution"] is True
    assert report["provider_cache_savings_claim_permitted"] is False


def test_execute_classifies_wire_present_but_parsed_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    _patch_prompt(monkeypatch)
    clock = _Clock()
    client = _FakeClient(
        [
            _wire_positive_parsed_absent_response(0),
            _wire_positive_parsed_absent_response(700),
        ]
    )

    execute_reauthorization(
        tmp_path,
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        confirmation="EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE",
        client=client,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    report = _json_object(tmp_path / _EXECUTION_ROOT / "report.json")
    assert report["outcome"] == "wire_field_present_but_parsed_absent"
    assert report["sdk_live_parse_defect_claim_permitted"] is True
    assert report["provider_cache_usage_claim_permitted_for_execution"] is False


def test_execute_rejects_confirmation_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    _patch_prompt(monkeypatch)

    with pytest.raises(
        ReauthorizationExecutionError,
        match="confirmation phrase",
    ):
        execute_reauthorization(
            tmp_path,
            authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
            confirmation="WRONG",
            client=_FakeClient([_absent_response(), _absent_response()]),
        )


def test_second_execution_is_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    _patch_prompt(monkeypatch)
    clock = _Clock()

    execute_reauthorization(
        tmp_path,
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        confirmation="EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE",
        client=_FakeClient([_absent_response(), _absent_response()]),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    with pytest.raises(
        ReauthorizationExecutionError,
        match="rerun and resume are forbidden",
    ):
        execute_reauthorization(
            tmp_path,
            authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
            confirmation="EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE",
            client=_FakeClient([_absent_response(), _absent_response()]),
        )


def test_public_evidence_does_not_contain_protected_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    _patch_prompt(monkeypatch)
    clock = _Clock()

    execute_reauthorization(
        tmp_path,
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        confirmation="EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE",
        client=_FakeClient([_absent_response(), _absent_response()]),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    public_text = "\n".join(
        (tmp_path / _EXECUTION_ROOT / name).read_text(encoding="utf-8")
        for name in ("journal.jsonl", "run_records.json", "report.json", "manifest.json")
    )
    assert '"content":"protected"' not in public_text
    assert '"content": "protected"' not in public_text
    assert "raw_body_base64" not in public_text
    assert '"parsed_response"' not in public_text

    raw_path = (
        tmp_path / ".local/benchmark/groq-cache-telemetry-reauthorization-v1/raw_responses.jsonl"
    )
    assert "raw_body_base64" in raw_path.read_text(encoding="utf-8")


def test_verify_rejects_protected_evidence_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    _patch_prompt(monkeypatch)
    clock = _Clock()

    execute_reauthorization(
        tmp_path,
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        confirmation="EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE",
        client=_FakeClient([_absent_response(), _absent_response()]),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    raw_path = (
        tmp_path / ".local/benchmark/groq-cache-telemetry-reauthorization-v1/raw_responses.jsonl"
    )
    raw_path.write_text(
        raw_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        ReauthorizationExecutionError,
        match="no longer matches",
    ):
        verify_reauthorization_execution(tmp_path)


class _UnexpectedFailureClient:
    def __init__(self) -> None:
        self.closed = False

    def create(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_completion_tokens: int,
        temperature: float,
        stream: bool,
        store: bool,
        reasoning_effort: str,
    ) -> _FakeRawResponse:
        del (
            messages,
            model,
            max_completion_tokens,
            temperature,
            stream,
            store,
            reasoning_effort,
        )
        raise RuntimeError("protected unexpected provider detail")

    def close(self) -> None:
        self.closed = True


def test_unexpected_provider_exception_becomes_safe_terminal_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_activation_assets(tmp_path)
    _patch_prompt(monkeypatch)
    clock = _Clock()
    client = _UnexpectedFailureClient()

    execute_reauthorization(
        tmp_path,
        authorization_id="groq-cache-telemetry-reauthorization-auth-v1",
        confirmation="EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE",
        client=client,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    records = _json_object(tmp_path / _EXECUTION_ROOT / "run_records.json")
    serialized = json.dumps(records, sort_keys=True)
    assert "GROQ_REAUTHORIZATION_UNSUPPORTED_PROVIDER_EXCEPTION" in serialized
    assert "protected unexpected provider detail" not in serialized
    assert client.closed is True


def test_frozen_provider_request_rejects_unreviewed_fields() -> None:
    with pytest.raises(ValidationError):
        runner._FrozenProviderRequest.model_validate(
            {
                "messages": [
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": "user"},
                ],
                "model": "openai/gpt-oss-20b",
                "max_completion_tokens": 32,
                "temperature": 0.0,
                "stream": False,
                "store": False,
                "reasoning_effort": "low",
                "seed": 7,
            }
        )
