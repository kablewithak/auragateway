from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping
from pathlib import Path

import pytest

from auragateway.local_abc import j7l_glm52_named_tool_qualification_activation_v1 as v1_activation
from auragateway.local_abc import j7l_glm52_named_tool_qualification_v1 as v1_design
from auragateway.local_abc import j7l_glm52_named_tool_requalification_v2 as subject

PLAN = subject.REQUALIFICATION_PLAN_PATH
SOURCE_PLAN = Path(
    "data/evals/quality/j7l-glm52-named-tool-qualification-v1/qualification_plan.json"
)
READINESS = Path("data/evals/quality/j7l-huawei-credential-readiness-v1/readiness_result.json")
ACTIVATION = subject.ACTIVATION_SOURCE_PATH
OLD_CONSUMPTION = Path(
    ".local/auragateway/j7l-glm52-named-tool-qualification-v1/authorization_consumed.json"
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_governance(root: Path) -> None:
    for relative in (PLAN, SOURCE_PLAN, READINESS, ACTIVATION):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative, target)


def _write_authorization(root: Path) -> None:
    payload = {
        "schema_version": "1.0.0",
        "authorization_id": "j7l-glm52-named-tool-requalification-authorization-v2",
        "status": "active",
        "requalification_plan_path": PLAN.as_posix(),
        "requalification_plan_sha256": _sha256_file(root / PLAN),
        "source_qualification_plan_path": SOURCE_PLAN.as_posix(),
        "source_qualification_plan_sha256": _sha256_file(root / SOURCE_PLAN),
        "readiness_result_path": READINESS.as_posix(),
        "readiness_result_sha256": _sha256_file(root / READINESS),
        "activation_source_path": ACTIVATION.as_posix(),
        "activation_source_sha256": _sha256_file(root / ACTIVATION),
        "confirmation_phrase": "EXECUTE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE",
        "provider": "huawei_modelarts_maas",
        "exact_model_identifier": "glm-5.2",
        "credential_env_name": "HUAWEI_MAAS_API_KEY",
        "provider_call_authorized": True,
        "credential_access_authorized": True,
        "network_access_authorized": True,
        "execution_command_available": True,
        "maximum_provider_http_requests": 2,
        "maximum_catalog_requests": 1,
        "maximum_model_inference_requests": 1,
        "qualification_token_allowance": 20000,
        "zero_spend_confirmation_required": True,
        "external_spend_ceiling_zar": 0,
        "paid_fallback_permitted": False,
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


def _arguments() -> dict[str, object]:
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
        "rationale": "The synthetic evidence supports the requested terminal decision.",
        "verdict": "pass",
        "uncertainty_statement": None,
    }


class FakeClient:
    def __init__(self, *, reasoning_tokens: int = 0) -> None:
        self.calls: list[tuple[str, str]] = []
        self.reasoning_tokens = reasoning_tokens

    def get(
        self,
        url: str,
        api_key: str,
        timeout_seconds: int,
    ) -> v1_activation.HttpResult:
        assert api_key == "synthetic-secret"
        assert timeout_seconds == 60
        self.calls.append(("GET", url))
        body = json.dumps(
            {"object": "list", "data": [{"id": "glm-5.2", "object": "model"}]},
            separators=(",", ":"),
        ).encode()
        return v1_activation.HttpResult(200, {"x-request-id": "catalog-id"}, body)

    def post_json(
        self,
        url: str,
        api_key: str,
        payload: Mapping[str, object],
        timeout_seconds: int,
    ) -> v1_activation.HttpResult:
        assert payload == _request_body()
        assert api_key == "synthetic-secret"
        assert timeout_seconds == 60
        self.calls.append(("POST", url))
        body = json.dumps(
            {
                "model": "glm-5.2",
                "choices": [
                    {
                        "message": {
                            "reasoning_content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "submit_reference_judgment",
                                        "arguments": json.dumps(_arguments()),
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
                    "completion_tokens_details": {"reasoning_tokens": self.reasoning_tokens},
                },
            },
            separators=(",", ":"),
        ).encode()
        return v1_activation.HttpResult(200, {"x-request-id": "chat-id"}, body)


def _patch_design(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    source_plan = v1_design.load_plan(root)
    monkeypatch.setattr(
        v1_design,
        "load_assets",
        lambda _: (source_plan, object(), object(), object()),
    )
    monkeypatch.setattr(v1_design, "build_chat_request_body", lambda _: _request_body())
    monkeypatch.setattr(
        v1_design,
        "dry_run",
        lambda _: {"status": "J7L_GLM52_NAMED_TOOL_QUALIFICATION_DESIGN_PASS"},
    )


def _no_git(_: Path) -> None:
    return None


def test_validate_is_non_live_without_fresh_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    result = subject.validate_activation(tmp_path)
    assert result["authorization_present"] is False
    assert result["readiness_status"] == "READY"
    assert result["provider_call_performed"] is False
    assert result["credential_accessed"] is False
    assert result["network_access_performed"] is False


def test_readiness_hash_drift_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    (tmp_path / READINESS).write_text("{}\n", encoding="utf-8")
    with pytest.raises(subject.ActivationError, match="artifact identity drifted"):
        subject.validate_activation(tmp_path)


def test_old_v1_consumption_does_not_block_fresh_v2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _write_authorization(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    old = tmp_path / OLD_CONSUMPTION
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text('{"status":"AUTHORIZATION_CONSUMED"}\n', encoding="utf-8")
    result = subject.execute_requalification(
        tmp_path,
        confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE",
        zero_spend_confirmed=True,
        client=FakeClient(),
        live_boundary=_no_git,
    )
    assert result["status"] == "J7L_GLM52_NAMED_TOOL_REQUALIFICATION_V2_PASS"
    assert old.is_file()


def test_execution_is_exactly_catalog_then_named_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _write_authorization(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    client = FakeClient()
    result = subject.execute_requalification(
        tmp_path,
        confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE",
        zero_spend_confirmed=True,
        client=client,
        live_boundary=_no_git,
    )
    assert [call[0] for call in client.calls] == ["GET", "POST"]
    assert result["provider_http_request_count"] == 2
    assert result["model_inference_request_count"] == 1
    assert result["reasoning_tokens"] == 0
    assert result["j7l_reference_request_performed"] is False
    assert result["jev_request_performed"] is False


def test_nonzero_reasoning_tokens_fail_closed_after_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _write_authorization(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    with pytest.raises(v1_activation.ActivationError, match="non-zero reasoning tokens"):
        subject.execute_requalification(
            tmp_path,
            confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE",
            zero_spend_confirmed=True,
            client=FakeClient(reasoning_tokens=1),
            live_boundary=_no_git,
        )
    plan = subject.RequalificationPlanV2.model_validate(
        json.loads((tmp_path / PLAN).read_text(encoding="utf-8"))
    )
    assert (tmp_path / plan.evidence_paths.consumption_path).is_file()


def test_second_execution_is_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_governance(tmp_path)
    _write_authorization(tmp_path)
    _patch_design(monkeypatch, tmp_path)
    monkeypatch.setenv("HUAWEI_MAAS_API_KEY", "synthetic-secret")
    subject.execute_requalification(
        tmp_path,
        confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE",
        zero_spend_confirmed=True,
        client=FakeClient(),
        live_boundary=_no_git,
    )
    with pytest.raises(subject.ActivationError, match="consumed or v2 evidence exists"):
        subject.execute_requalification(
            tmp_path,
            confirmation="EXECUTE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE",
            zero_spend_confirmed=True,
            client=FakeClient(),
            live_boundary=_no_git,
        )
