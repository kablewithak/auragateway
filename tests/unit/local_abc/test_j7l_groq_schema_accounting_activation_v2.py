from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path

import pytest

from auragateway.local_abc import j7l_groq_schema_accounting_activation_v2 as runner
from auragateway.local_abc.j7l_groq_schema_accounting_activation_v2 import (
    ActivationError,
    execute_probe,
    validate_activation,
)

_AUTH = Path("data/evals/quality/j7l-groq-schema-accounting-activation-v2/authorization.json")
_PLAN = Path("data/evals/quality/j7l-groq-schema-accounting-review-v1/probe_plan_v2.json")
_PROMPT = Path(
    "data/evals/quality/j7l-groq-schema-accounting-review-v1/synthetic_prompt_recipe.json"
)
_SCHEMA = Path(
    "data/evals/quality/j7l-groq-schema-accounting-review-v1/strict_response_schema.json"
)


def _copy_assets(root: Path) -> None:
    for relative in (_AUTH, _PLAN, _PROMPT, _SCHEMA):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative, target)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class _Http:
    def __init__(self, payload: dict[str, object]) -> None:
        self.content = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.status_code = 200
        self.headers: Mapping[str, str] = {"x-ratelimit-remaining-tokens": "999"}


class _Parsed:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(
        self,
        *,
        mode: str = "python",
        exclude_none: bool = False,
        exclude_unset: bool = False,
    ) -> dict[str, object]:
        del mode, exclude_none, exclude_unset
        return self._payload


class _Raw:
    def __init__(self, payload: dict[str, object]) -> None:
        self.http_response: runner.HttpResponse = _Http(payload)
        self._parsed = _Parsed(payload)
        self.closed = False

    def parse(self) -> runner.ParsedCompletion:
        return self._parsed

    def close(self) -> None:
        self.closed = True


class _Client:
    def __init__(self, prompt_tokens: tuple[int, int]) -> None:
        self.prompt_tokens = prompt_tokens
        self.calls: list[dict[str, object]] = []
        self.closed = False

    def create(self, request: dict[str, object]) -> runner.RawResponse:
        index = len(self.calls)
        self.calls.append(request)
        prompt_tokens = self.prompt_tokens[index]
        return _Raw(
            {
                "id": f"response-{index}",
                "choices": [{"message": {"role": "assistant", "content": "{}"}}],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": 20,
                    "total_tokens": prompt_tokens + 20,
                },
            }
        )

    def close(self) -> None:
        self.closed = True


def _no_live_git_check(_: Path) -> None:
    return None


def test_validate_is_non_live(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setattr(runner, "_assert_sdk", lambda plan: "1.5.0")
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    result = validate_activation(tmp_path)

    assert result["status"] == "J7L_GROQ_SCHEMA_ACCOUNTING_ACTIVATION_V2_PASS"
    assert result["provider_call_performed"] is False
    assert result["credential_accessed"] is False
    assert result["raw_evidence_exists"] is False
    assert result["parsed_evidence_exists"] is False
    assert result["result_exists"] is False


def test_execute_changes_only_response_format_and_waits_ten_seconds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setattr(runner, "_assert_sdk", lambda plan: "1.5.0")
    clock = _Clock()
    client = _Client((30, 47))

    result = execute_probe(
        tmp_path,
        confirmation="EXECUTE_J7L_GROQ_SCHEMA_ACCOUNTING_PROBE_ONCE",
        free_tier_confirmed=True,
        client=client,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        live_boundary=_no_live_git_check,
    )

    assert result["provider_call_count"] == 2
    assert result["control_prompt_tokens"] == 30
    assert result["strict_prompt_tokens"] == 47
    assert result["prompt_token_delta"] == 17
    assert result["outcome"] == "strict_schema_prompt_tokens_higher"
    assert clock.now == 10.0
    assert client.closed is True
    assert len(client.calls) == 2

    control = client.calls[0]
    strict = client.calls[1]
    assert "response_format" not in control
    assert set(strict) == set(control) | {"response_format"}
    for key, value in control.items():
        assert strict[key] == value

    response_format = strict["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"

    raw_path = (
        tmp_path / ".local/auragateway/j7l-groq-schema-accounting-probe-v2/raw_responses.jsonl"
    )
    parsed_path = (
        tmp_path / ".local/auragateway/j7l-groq-schema-accounting-probe-v2/parsed_responses.jsonl"
    )
    result_path = tmp_path / runner.RESULT_PATH

    assert len(raw_path.read_text(encoding="utf-8").splitlines()) == 2
    assert len(parsed_path.read_text(encoding="utf-8").splitlines()) == 2
    assert result_path.is_file()


def test_execution_requires_free_tier_confirmation_before_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setattr(runner, "_assert_sdk", lambda plan: "1.5.0")
    client = _Client((30, 30))

    with pytest.raises(ActivationError, match="Free-tier status"):
        execute_probe(
            tmp_path,
            confirmation="EXECUTE_J7L_GROQ_SCHEMA_ACCOUNTING_PROBE_ONCE",
            free_tier_confirmed=False,
            client=client,
            live_boundary=_no_live_git_check,
        )

    assert client.calls == []


def test_second_execution_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setattr(runner, "_assert_sdk", lambda plan: "1.5.0")
    clock = _Clock()
    first = _Client((30, 30))

    execute_probe(
        tmp_path,
        confirmation="EXECUTE_J7L_GROQ_SCHEMA_ACCOUNTING_PROBE_ONCE",
        free_tier_confirmed=True,
        client=first,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        live_boundary=_no_live_git_check,
    )

    second = _Client((30, 30))
    with pytest.raises(ActivationError, match="rerun and resume are forbidden"):
        execute_probe(
            tmp_path,
            confirmation="EXECUTE_J7L_GROQ_SCHEMA_ACCOUNTING_PROBE_ONCE",
            free_tier_confirmed=True,
            client=second,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            live_boundary=_no_live_git_check,
        )

    assert second.calls == []
