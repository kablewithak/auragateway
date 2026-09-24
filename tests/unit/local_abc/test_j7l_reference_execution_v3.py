from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import j7l_reference_execution_v3 as subject


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _response(*, total_tokens: int = 12220) -> bytes:
    prompt_tokens = total_tokens - 220
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
                        "reasoning_content": None,
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
                "prompt_tokens": prompt_tokens,
                "completion_tokens": 220,
                "total_tokens": total_tokens,
                "completion_tokens_details": {"reasoning_tokens": 0},
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
            cases.append(
                {
                    "case_id": f"j7l-dev-{index:03d}",
                    "family": family,
                    "reviewer_safe_state": {},
                }
            )
            index += 1
    return tuple(cases)


def _tool_contract() -> Mapping[str, object]:
    return {
        "wire": {
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "submit_reference_judgment"},
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {"name": "submit_reference_judgment"},
            },
        }
    }


def _plan() -> Mapping[str, object]:
    _binding, plan = subject._load_bound_assets(_repo_root())
    return plan


def _authorization(
    *,
    reference_audit_schedule_sha256: str,
) -> subject.AuthorizationV3:
    return subject.AuthorizationV3(
        schema_version="1.0.0",
        authorization_id="j7l-reference-execution-authorization-v3",
        status="active",
        binding_path="data/evals/quality/j7l-reference-judge-binding-v2/binding.json",
        binding_sha256=subject.EXPECTED_BINDING_SHA256,
        execution_plan_path=(
            "data/evals/quality/j7l-reference-execution-protocol-v3/reference_execution_plan.json"
        ),
        execution_plan_sha256=subject.EXPECTED_PLAN_SHA256,
        reference_audit_schedule_sha256=reference_audit_schedule_sha256,
        audit_actor_id_sha256=subject.OPERATOR_ID_SHA256,
        resolution_owner_id_sha256=subject.OPERATOR_ID_SHA256,
        confirmation_phrase="EXECUTE_J7L_REFERENCE_SET_V3",
        provider="huawei_modelarts_maas",
        exact_model_identifier="glm-5.2",
        credential_env_name="HUAWEI_MAAS_API_KEY",
        provider_call_authorized=True,
        credential_access_authorized=True,
        network_access_authorized=True,
        reference_execution_authorized=True,
        maximum_model_inference_requests=48,
        max_in_flight_requests=1,
        automatic_retry_permitted=False,
        completed_case_replay_permitted=False,
        ambiguous_attempt_retry_permitted=False,
        resume_after_completed_cases_permitted=True,
        cumulative_phase_total_token_ceiling=subject.PHASE_TOTAL_TOKEN_CEILING,
        external_spend_ceiling_zar=0,
        paid_fallback_permitted=False,
        jev_request_permitted=False,
        zero_spend_confirmation_required=True,
        clean_main_required=True,
    )


def _persist_completed_case(
    repo_root: Path,
    *,
    case: Mapping[str, object],
    model_projection: object,
    tool_contract: Mapping[str, object],
    total_tokens: int,
) -> None:
    case_id = cast(str, case["case_id"])
    reviewer_safe_state = cast(Mapping[str, object], case["reviewer_safe_state"])
    request = subject._build_request(
        model_projection=model_projection,
        reviewer_safe_state=reviewer_safe_state,
        tool_contract=tool_contract,
    )
    request_sha256 = subject.sha256_bytes(subject.canonical_json(request).encode("utf-8"))
    body = _response(total_tokens=total_tokens)
    judgment, _usage, _returned_model = subject._validate_response(
        body,
        case_id=case_id,
        request_id_sha256=request_sha256,
        judge_binding_sha256=subject.EXPECTED_BINDING_SHA256,
    )

    subject._write_once(
        repo_root / subject.ATTEMPTS_DIR / f"{case_id}.json",
        {
            "schema_version": "1.0.0",
            "status": "REFERENCE_REQUEST_ATTEMPT_STARTED",
            "case_id": case_id,
            "request_id_sha256": request_sha256,
            "judge_binding_sha256": subject.EXPECTED_BINDING_SHA256,
            "started_at_utc": "2026-09-25T00:00:00+00:00",
            "retry_permitted": False,
        },
    )
    subject._write_once(
        repo_root / subject.RAW_RESPONSES_DIR / f"{case_id}.json",
        {
            "schema_version": "1.0.0",
            "case_id": case_id,
            "request_id_sha256": request_sha256,
            "http_status_code": 200,
            "raw_body_sha256": subject.sha256_bytes(body),
            "raw_body_base64": base64.b64encode(body).decode("ascii"),
            "safe_response_headers": {},
        },
    )
    subject._write_once(
        repo_root / subject.JUDGMENTS_DIR / f"{case_id}.json",
        judgment.model_dump(mode="json"),
    )


def test_v3_plan_is_inactive_and_bound_to_complete_audit_authority() -> None:
    _binding, plan = subject._load_bound_assets(_repo_root())
    audit = subject._mapping(plan["audit_authority"], role="audit authority")
    policy = subject._mapping(plan["request_policy"], role="request policy")

    assert plan["plan_id"] == "j7l-reference-execution-v3"
    assert plan["reference_execution_authorized"] is False
    assert plan["provider_call_authorized"] is False
    assert plan["network_access_authorized"] is False
    assert plan["jev_request_permitted"] is False
    assert audit["audit_actor_id_sha256"] == subject.OPERATOR_ID_SHA256
    assert audit["resolution_owner_id_sha256"] == subject.OPERATOR_ID_SHA256
    assert audit["audit_schedule_contract"] == "J7LReferenceAuditScheduleV1"
    assert policy["completed_usage_reconstructed_on_resume"] is True
    assert policy["cumulative_phase_total_token_ceiling_enforced_across_resumes"] is True


def test_missing_audit_actor_blocks_schedule_construction() -> None:
    plan = dict(_plan())
    audit = dict(subject._mapping(plan["audit_authority"], role="audit authority"))
    audit.pop("audit_actor_id_sha256")
    plan["audit_authority"] = audit

    with pytest.raises(subject.ReferenceExecutionError, match="audit_actor_id_sha256"):
        subject._audit_schedule(_audit_cases(), plan)


def test_missing_resolution_owner_blocks_schedule_construction() -> None:
    plan = dict(_plan())
    audit = dict(subject._mapping(plan["audit_authority"], role="audit authority"))
    audit.pop("resolution_owner_id_sha256")
    plan["audit_authority"] = audit

    with pytest.raises(subject.ReferenceExecutionError, match="resolution_owner_id_sha256"):
        subject._audit_schedule(_audit_cases(), plan)


def test_complete_audit_schedule_validates_through_typed_contract() -> None:
    schedule = subject._audit_schedule(_audit_cases(), _plan())

    assert schedule.audit_actor_id_sha256 == subject.OPERATOR_ID_SHA256
    assert schedule.resolution_owner_id_sha256 == subject.OPERATOR_ID_SHA256
    assert len(schedule.protected_secondary_case_ids) == 24
    assert schedule.additional_spot_check_case_ids == (
        "j7l-dev-001",
        "j7l-dev-002",
        "j7l-dev-013",
        "j7l-dev-014",
    )
    assert schedule.schedule_frozen_before_reference_execution is True
    assert schedule.audit_may_rewrite_reference is False


def test_incomplete_prior_case_evidence_blocks_retry(tmp_path: Path) -> None:
    case = _audit_cases()[0]
    case_id = cast(str, case["case_id"])
    request = subject._build_request(
        model_projection={"projection": "test"},
        reviewer_safe_state=cast(Mapping[str, object], case["reviewer_safe_state"]),
        tool_contract=_tool_contract(),
    )
    request_sha256 = subject.sha256_bytes(subject.canonical_json(request).encode("utf-8"))

    subject._write_once(
        tmp_path / subject.ATTEMPTS_DIR / f"{case_id}.json",
        {
            "schema_version": "1.0.0",
            "status": "REFERENCE_REQUEST_ATTEMPT_STARTED",
            "case_id": case_id,
            "request_id_sha256": request_sha256,
            "judge_binding_sha256": subject.EXPECTED_BINDING_SHA256,
            "started_at_utc": "2026-09-25T00:00:00+00:00",
            "retry_permitted": False,
        },
    )

    with pytest.raises(subject.ReferenceExecutionError, match="do not retry"):
        subject._completed_case_evidence(
            tmp_path,
            case_id=case_id,
            expected_request_sha256=request_sha256,
        )


def test_resume_reconstructs_cumulative_usage_without_provider_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, plan = subject._load_bound_assets(_repo_root())
    cases = _audit_cases()
    model_projection: object = {"projection": "test"}
    tool_contract = _tool_contract()
    per_case_total_tokens = 12220

    audit_schedule_sha256 = subject.sha256_bytes(subject._audit_schedule_bytes(cases, plan))
    auth = _authorization(reference_audit_schedule_sha256=audit_schedule_sha256)
    authorization_sha256 = "e" * 64

    for case in cases:
        _persist_completed_case(
            tmp_path,
            case=case,
            model_projection=model_projection,
            tool_contract=tool_contract,
            total_tokens=per_case_total_tokens,
        )

    subject._write_once(
        tmp_path / subject.CONSUMPTION_PATH,
        {
            "schema_version": "1.0.0",
            "status": "REFERENCE_EXECUTION_AUTHORIZATION_CONSUMED",
            "authorization_id": auth.authorization_id,
            "authorization_sha256": authorization_sha256,
            "binding_sha256": subject.EXPECTED_BINDING_SHA256,
            "execution_plan_sha256": subject.EXPECTED_PLAN_SHA256,
        },
    )

    def fake_load_bound_assets(
        _repo_root_value: Path,
    ) -> tuple[Mapping[str, object], Mapping[str, object]]:
        return binding, plan

    def fake_authorization(_repo_root_value: Path) -> tuple[subject.AuthorizationV3, str]:
        return auth, authorization_sha256

    def fake_live_git_boundary(_repo_root_value: Path) -> None:
        return None

    def fake_load_reference_inputs(
        _repo_root_value: Path,
        _plan_value: Mapping[str, object],
    ) -> tuple[tuple[dict[str, object], ...], object, Mapping[str, object]]:
        return cases, model_projection, tool_contract

    monkeypatch.setattr(subject, "_load_bound_assets", fake_load_bound_assets)
    monkeypatch.setattr(subject, "_authorization", fake_authorization)
    monkeypatch.setattr(subject, "_assert_live_git_boundary", fake_live_git_boundary)
    monkeypatch.setattr(subject, "_load_reference_inputs", fake_load_reference_inputs)

    result = subject.execute(
        tmp_path,
        confirmation="EXECUTE_J7L_REFERENCE_SET_V3",
        zero_spend_confirmed=True,
    )

    expected_total = len(cases) * per_case_total_tokens

    assert result["provider_requests_in_this_invocation"] == 0
    assert result["completed_cases_reused_on_resume"] == 48
    assert result["observed_total_tokens_in_this_invocation"] == 0
    assert result["cumulative_observed_total_tokens"] == expected_total
    assert result["completed_usage_reconstructed_on_resume"] is True
    assert result["credential_accessed_in_this_invocation"] is False
    assert result["network_access_performed_in_this_invocation"] is False
    assert result["jev_requests_performed"] == 0
