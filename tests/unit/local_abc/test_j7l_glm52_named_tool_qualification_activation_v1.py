from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest

from auragateway.contracts.j7l_glm52_named_tool_qualification_v1 import (
    J7LGLM52NamedToolQualificationPlanV1,
)
from auragateway.local_abc import (
    j7l_glm52_named_tool_qualification_activation_v1 as subject,
)
from auragateway.local_abc import (
    j7l_glm52_named_tool_qualification_v1 as design,
)
from auragateway.local_abc.j7l_glm52_named_tool_qualification_activation_v1 import (
    ActivationError,
    HttpResult,
)

AUTH = Path(
    "data/evals/quality/j7l-glm52-named-tool-qualification-authorization-v1/authorization.json"
)
PLAN = Path("data/evals/quality/j7l-glm52-named-tool-qualification-v1/qualification_plan.json")
EXPECTED_AUTH_SHA256 = "d5a606355cfb1f67104865c19d2657892aaef62c690f1bbad6d180f5463618a7"


def _copy_governance(root: Path) -> None:
    for relative in (AUTH, PLAN):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative, target)


def _plan(root: Path) -> J7LGLM52NamedToolQualificationPlanV1:
    return J7LGLM52NamedToolQualificationPlanV1.model_validate(
        json.loads((root / PLAN).read_text(encoding="utf-8"))
    )


def _expected_arguments() -> dict[str, object]:
    return {
        "criterion_scores": {
            "task_correctness": 3,
            "evidence_grounding": 3,
            "source_use": 3,
            "terminal_decision": 3,
            "completeness": 3,
            "clarity": 3,
            "safety": 3,
        },
        "failure_labels": [],
        "evidence_references": ["synthetic-evidence-001"],
        "rationale": (
            "The synthetic evidence directly supports the response and the requested "
            "terminal decision."
        ),
        "verdict": "pass",
        "uncertainty_statement": None,
    }


def _request_body() -> dict[str, object]:
    return {
        "model": "glm-5.2",
        "messages": [
            {"role": "system", "content": "synthetic qualification only"},
            {"role": "user", "content": "synthetic qualification only"},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "submit_reference_judgment",
                    "parameters": {"type": "object"},
                },
            }
        ],
        "tool_choice": {
            "type": "function",
            "function": {"name": "submit_reference_judgment"},
        },
        "stream": False,
        "max_completion_tokens": 768,
        "chat_template_kwargs": {"thinking": False},
    }


def _chat_payload() -> dict[str, object]:
    return {
        "id": "synthetic-provider-response",
        "model": "glm-5.2",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "reasoning_content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "submit_reference_judgment",
                                "arguments": json.dumps(
                                    _expected_arguments(),
                                    separators=(",", ":"),
                                ),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {
            "prompt_tokens": 7300,
            "completion_tokens": 180,
            "total_tokens": 7480,
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
    }


class FakeClient:
    def __init__(self, *, reasoning_tokens: int = 0) -> None:
        self.calls: list[tuple[str, str]] = []
        self.reasoning_tokens = reasoning_tokens

    def get(self, url: str, api_key: str, timeout_seconds: int) -> HttpResult:
        assert api_key == "synthetic-secret"
        assert timeout_seconds == 60
        self.calls.append(("GET", url))
        body = json.dumps(
            {
                "object": "list",
                "data": [
                    {
                        "id": "glm-5.2",
                        "object": "model",
                        "created": 0,
                        "owned_by": "system",
                    }
                ],
            },
            separators=(",", ":"),
        ).encode("utf-8")
        return HttpResult(200, {"x-request-id": "catalog-id"}, body)

    def post_json(
        self,
        url: str,
        api_key: str,
        payload: Mapping[str, object],
        timeout_seconds: int,
    ) -> HttpResult:
        assert api_key == "synthetic-secret"
        assert timeout_seconds == 60
        assert payload == _request_body()
        self.calls.append(("POST", url))
        body_payload = _chat_payload()
        usage = cast(dict[str, Any], body_payload["usage"])
        details = cast(dict[str, Any], usage["completion_tokens_details"])
        details["reasoning_tokens"] = self.reasoning_tokens
        body = json.dumps(body_payload, separators=(",", ":")).encode("utf-8")
        return HttpResult(200, {"x-request-id": "chat-id"}, body)


def _patch_design(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
) -> None:
    plan = _plan(root)
    monkeypatch.setattr(design, "load_plan", lambda _: plan)
    monkeypatch.setattr(design, "load_assets", lambda _: (plan, object(), object(), object()))
    monkeypatch.setattr(design, "build_chat_request_body", lambda _: _request_body())
    monkeypatch.setattr(
        design,
        "dry_run",
        lambda _: {"status": "J7L_GLM52_NAMED_TOOL_QUALIFICATION_DESIGN_PASS"},
    )


def _no_live_git_check(_: Path) -> None:
    return None


def test_validate_is_non_live_and_does_not_read_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "must-not-be-read")

    result = subject.validate_activation(tmp_path)

    assert result["status"] == "J7L_GLM52_NAMED_TOOL_AUTHORIZATION_V1_PASS"
    assert result["authorization_sha256"] == EXPECTED_AUTH_SHA256
    assert result["provider_call_performed"] is False
    assert result["credential_accessed"] is False
    assert result["network_access_performed"] is False


def test_execution_consumes_authorization_and_performs_exact_two_http_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    client = FakeClient()

    result = subject.execute_qualification(
        tmp_path,
        confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_ONCE",
        zero_spend_confirmed=True,
        client=client,
        live_boundary=_no_live_git_check,
    )

    assert client.calls == [
        ("GET", "https://api-ap-southeast-1.modelarts-maas.com/v2/models"),
        (
            "POST",
            "https://api-ap-southeast-1.modelarts-maas.com/openai/v1/chat/completions",
        ),
    ]
    assert result["status"] == "J7L_GLM52_NAMED_TOOL_QUALIFICATION_PASS"
    assert result["provider_http_request_count"] == 2
    assert result["catalog_request_count"] == 1
    assert result["model_inference_request_count"] == 1
    assert result["total_tokens"] == 7480
    assert result["reasoning_tokens"] == 0
    assert result["provider_version_or_revision_exposed"] is False
    assert result["zero_spend_independently_proven"] is False
    assert result["j7l_reference_request_performed"] is False
    assert result["jev_request_performed"] is False
    assert result["binding_freeze_performed"] is False

    plan = _plan(tmp_path)
    assert (tmp_path / subject.CONSUMPTION_PATH).is_file()
    assert (tmp_path / subject.CATALOG_RAW_PATH).is_file()
    assert (tmp_path / subject.CHAT_RAW_PATH).is_file()
    assert (tmp_path / plan.protected_raw_response_path).is_file()
    assert (tmp_path / plan.protected_parsed_response_path).is_file()
    assert (tmp_path / plan.public_result_path).is_file()


def test_execution_requires_confirmation_before_credential_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.delenv("HUAWEI_MAAS_API_KEY", raising=False)
    client = FakeClient()

    with pytest.raises(ActivationError, match="confirmation phrase"):
        subject.execute_qualification(
            tmp_path,
            confirmation="WRONG",
            zero_spend_confirmed=True,
            client=client,
            live_boundary=_no_live_git_check,
        )

    assert client.calls == []
    assert not (tmp_path / subject.CONSUMPTION_PATH).exists()


def test_execution_requires_zero_spend_confirmation_before_credential_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.delenv("HUAWEI_MAAS_API_KEY", raising=False)
    client = FakeClient()

    with pytest.raises(ActivationError, match="R0 external-spend"):
        subject.execute_qualification(
            tmp_path,
            confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_ONCE",
            zero_spend_confirmed=False,
            client=client,
            live_boundary=_no_live_git_check,
        )

    assert client.calls == []
    assert not (tmp_path / subject.CONSUMPTION_PATH).exists()


def test_nonzero_reasoning_tokens_fail_closed_and_consume_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    client = FakeClient(reasoning_tokens=1)

    with pytest.raises(ActivationError, match="non-zero reasoning tokens"):
        subject.execute_qualification(
            tmp_path,
            confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_ONCE",
            zero_spend_confirmed=True,
            client=client,
            live_boundary=_no_live_git_check,
        )

    assert len(client.calls) == 2
    assert (tmp_path / subject.CONSUMPTION_PATH).is_file()
    assert (tmp_path / subject.CATALOG_RAW_PATH).is_file()
    assert (tmp_path / subject.CHAT_RAW_PATH).is_file()


def test_second_execution_is_blocked_after_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    first = FakeClient()

    subject.execute_qualification(
        tmp_path,
        confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_ONCE",
        zero_spend_confirmed=True,
        client=first,
        live_boundary=_no_live_git_check,
    )

    second = FakeClient()
    with pytest.raises(ActivationError, match="consumed or execution evidence exists"):
        subject.execute_qualification(
            tmp_path,
            confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_ONCE",
            zero_spend_confirmed=True,
            client=second,
            live_boundary=_no_live_git_check,
        )

    assert second.calls == []
