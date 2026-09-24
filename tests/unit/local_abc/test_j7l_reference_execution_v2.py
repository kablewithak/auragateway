from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.local_abc import j7l_reference_execution_v2 as subject


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _response(*, reasoning_tokens: int = 0, reasoning_content: str | None = None) -> bytes:
    rationale = (
        "The visible evidence supports the candidate response and the declared terminal outcome."
    )
    return json.dumps(
        {
            "model": "glm-5.2",
            "choices": [
                {
                    "message": {
                        "content": None,
                        "reasoning_content": reasoning_content,
                        "tool_calls": [
                            {
                                "id": "call-reference",
                                "type": "function",
                                "function": {
                                    "name": "submit_reference_judgment",
                                    "arguments": json.dumps(
                                        {
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
                                            "evidence_references": ["visible-evidence-1"],
                                            "rationale": rationale,
                                            "verdict": "pass",
                                            "uncertainty_statement": None,
                                        }
                                    ),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 12000,
                "completion_tokens": 220,
                "total_tokens": 12220,
                "completion_tokens_details": {"reasoning_tokens": reasoning_tokens},
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _audit_cases() -> tuple[dict[str, object], ...]:
    families = (
        ("ordinary_clean", 12),
        ("clear_failure", 12),
        ("terminal_non_substantive", 12),
        ("ontology_near_miss", 12),
    )
    cases: list[dict[str, object]] = []
    index = 1
    for family, count in families:
        for _ in range(count):
            cases.append({"case_id": f"j7l-dev-{index:03d}", "family": family})
            index += 1
    return tuple(cases)


def test_binding_v2_is_frozen_without_execution_authority() -> None:
    binding, plan = subject._load_bound_assets(_repo_root())
    provider_identity = subject._mapping(
        binding["provider_identity"],
        role="provider identity",
    )
    request_policy = subject._mapping(plan["request_policy"], role="request policy")

    assert binding["binding_frozen"] is True
    assert binding["reference_execution_authorized"] is False
    assert provider_identity["provider_revision_state"] == "NOT_EXPOSED_BY_PROVIDER"
    assert provider_identity["provider_revision_not_fabricated"] is True
    assert request_policy["planned_reference_request_count"] == 48
    assert request_policy["hard_reference_phase_total_token_ceiling"] == 960000


def test_audit_schedule_is_deterministic_and_complete() -> None:
    first = subject._audit_schedule_bytes(_audit_cases())
    second = subject._audit_schedule_bytes(_audit_cases())

    assert first == second
    payload = json.loads(first)
    assert len(payload["protected_secondary_case_ids"]) == 24
    assert len(payload["additional_spot_check_case_ids"]) == 4
    assert payload["additional_spot_check_case_ids"] == [
        "j7l-dev-001",
        "j7l-dev-002",
        "j7l-dev-013",
        "j7l-dev-014",
    ]


def test_response_validation_accepts_exact_named_tool_contract() -> None:
    judgment, usage, returned_model = subject._validate_response(
        _response(),
        case_id="j7l-dev-001",
        request_id_sha256="a" * 64,
        judge_binding_sha256=subject.EXPECTED_BINDING_SHA256,
    )

    assert judgment.case_id == "j7l-dev-001"
    assert judgment.verdict.value == "pass"
    assert usage["total_tokens"] == 12220
    assert usage["reasoning_tokens"] == 0
    assert returned_model == "glm-5.2"


def test_response_validation_rejects_reasoning_tokens() -> None:
    with pytest.raises(subject.ReferenceExecutionError, match="non-zero reasoning tokens"):
        subject._validate_response(
            _response(reasoning_tokens=1),
            case_id="j7l-dev-001",
            request_id_sha256="a" * 64,
            judge_binding_sha256=subject.EXPECTED_BINDING_SHA256,
        )


def test_response_validation_rejects_reasoning_content() -> None:
    with pytest.raises(subject.ReferenceExecutionError, match="non-empty reasoning_content"):
        subject._validate_response(
            _response(reasoning_content="hidden reasoning"),
            case_id="j7l-dev-001",
            request_id_sha256="a" * 64,
            judge_binding_sha256=subject.EXPECTED_BINDING_SHA256,
        )


def test_ambiguous_prior_attempt_is_not_retried(tmp_path: Path) -> None:
    attempt = tmp_path / subject.ATTEMPTS_DIR / "j7l-dev-001.json"
    attempt.parent.mkdir(parents=True)
    attempt.write_text('{"status":"REFERENCE_REQUEST_ATTEMPT_STARTED"}\n', encoding="utf-8")

    with pytest.raises(subject.ReferenceExecutionError, match="do not retry"):
        subject._completed_judgment(tmp_path, "j7l-dev-001")
