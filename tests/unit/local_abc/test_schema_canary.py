from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.measured_quality import (
    MeasuredQualityCheck,
)
from auragateway.local_abc.schema_canary import (
    SchemaCanaryAnswerConstraint,
    SchemaCanaryAuthorizationPackage,
    SchemaCanaryCaseId,
    SchemaCanaryCaseProfile,
    SchemaCanaryLifecycleStatus,
    build_schema_canary_checkpoint,
    build_schema_canary_request_body,
    build_schema_canary_response_format,
    load_schema_canary_authorization_package,
)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = ROOT / "benchmarks/local_abc/schema_probe_v1_evidence_audit.json"
AUTHORIZATION_PATH = (
    ROOT / "benchmarks/local_abc/schema_constrained_quality_canary_authorization_v1.json"
)
EXPECTED_AUDIT_FINGERPRINT = "8e2c2e432957a7a618397165e2613739572870181caf7363243f16a941be9f6f"
EXPECTED_AUTHORIZATION_FINGERPRINT = (
    "6af80f33302e2b6eebf2e4d61efd6b198d9c7706a8a6bfe686b849faad6e5b14"
)


def load_package() -> SchemaCanaryAuthorizationPackage:
    return load_schema_canary_authorization_package(
        audit_path=AUDIT_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )


def profile_for(case_id: SchemaCanaryCaseId) -> SchemaCanaryCaseProfile:
    package = load_package()
    return next(
        profile for profile in package.authorization.case_profiles if profile.case_id is case_id
    )


def test_package_loads_and_cross_binds() -> None:
    package = load_package()

    assert package.audit.fingerprint() == EXPECTED_AUDIT_FINGERPRINT
    assert package.authorization.fingerprint() == EXPECTED_AUTHORIZATION_FINGERPRINT
    assert package.authorization.successful_probe_audit_sha256 == EXPECTED_AUDIT_FINGERPRINT


def test_probe_audit_freezes_successful_result() -> None:
    audit = load_package().audit

    assert audit.reported_status == "SCHEMA_CONSTRAINED_OUTPUT_PROBE_PASSED"
    assert audit.completed_request_count == 1
    assert audit.failure_count == 0
    assert audit.output_shape.value == "json_object"
    assert audit.schema_validation_passed is True
    assert audit.telemetry_valid is True
    assert audit.checkpoint_status == "passed"
    assert audit.cleanup_status == "CLEAN"


def test_probe_output_hashes_match_exact_expected_payload() -> None:
    audit = load_package().audit

    assert audit.output_text_sha256 == audit.validated_output_sha256
    assert audit.validated_output_sha256 == audit.expected_payload_sha256


def test_probe_audit_does_not_claim_cache_measurement() -> None:
    audit = load_package().audit

    assert audit.cache_reuse_evaluated is False
    assert audit.cached_prefix_tokens_observed_not_evaluated == 0
    assert audit.schema_canary_authorization_permitted is True
    assert audit.full_measured_rerun_authorized is False


def test_authorization_scope_is_three_trajectories_six_requests() -> None:
    authorization = load_package().authorization

    assert authorization.execution_authorized is True
    assert authorization.trajectory_count == 3
    assert authorization.request_count == 6
    assert authorization.intended_route[0].value == "worker_1"
    assert authorization.intended_route[1].value == "worker_1"
    assert authorization.full_worker_restart_before_each_trajectory is True


def test_authorization_requires_all_quality_and_cache_gates() -> None:
    authorization = load_package().authorization

    assert authorization.required_quality_checks == tuple(MeasuredQualityCheck)
    assert authorization.required_quality_pass_rate == "1.0"
    assert authorization.require_turn_one_cold is True
    assert authorization.require_positive_turn_two_cached_tokens is True
    assert authorization.cache_reuse_evaluation_permitted is True
    assert authorization.max_trajectory_failures == 0


def test_full_measured_execution_remains_blocked() -> None:
    authorization = load_package().authorization

    assert authorization.schema_canary_execution_authorized is True
    assert authorization.full_measured_rerun_authorized is False
    assert authorization.hidden_retries_permitted is False
    assert authorization.replacement_trajectories_permitted is False


def test_case_order_and_profiles_are_frozen() -> None:
    authorization = load_package().authorization

    assert authorization.selected_case_ids == (
        SchemaCanaryCaseId.INCIDENT_SEVERITY,
        SchemaCanaryCaseId.PAYMENT_RECONCILIATION,
        SchemaCanaryCaseId.DATA_SHARING_POLICY,
    )
    assert (
        tuple(profile.case_id for profile in authorization.case_profiles)
        == authorization.selected_case_ids
    )


def test_incident_schema_constrains_domain_not_expected_answer() -> None:
    profile = profile_for(SchemaCanaryCaseId.INCIDENT_SEVERITY)

    response_format = build_schema_canary_response_format(
        profile=profile,
        turn_index=1,
    )
    answer = response_format["json_schema"]["schema"]["properties"]["answer"]

    assert answer["enum"] == ["sev1", "sev2", "sev3", "sev4"]
    assert len(answer["enum"]) > 1
    assert response_format["json_schema"]["name"] == ("incident-severity-turn-1-output")


def test_payment_schema_uses_numeric_pattern_not_expected_value() -> None:
    profile = profile_for(SchemaCanaryCaseId.PAYMENT_RECONCILIATION)

    response_format = build_schema_canary_response_format(
        profile=profile,
        turn_index=2,
    )
    answer = response_format["json_schema"]["schema"]["properties"]["answer"]

    assert profile.answer_constraint is (SchemaCanaryAnswerConstraint.INTEGER_STRING)
    assert answer == {"type": "string", "pattern": "^[0-9]+$"}
    assert "1550" not in json.dumps(response_format)


def test_data_sharing_schema_allows_both_policy_actions() -> None:
    profile = profile_for(SchemaCanaryCaseId.DATA_SHARING_POLICY)

    response_format = build_schema_canary_response_format(
        profile=profile,
        turn_index=2,
    )
    answer = response_format["json_schema"]["schema"]["properties"]["answer"]

    assert answer["enum"] == ["allow", "block"]
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False


def test_each_schema_freezes_case_and_turn_metadata() -> None:
    profile = profile_for(SchemaCanaryCaseId.DATA_SHARING_POLICY)

    response_format = build_schema_canary_response_format(
        profile=profile,
        turn_index=2,
    )
    properties = response_format["json_schema"]["schema"]["properties"]

    assert properties["case_id"]["const"] == "data-sharing-policy"
    assert properties["confidence"]["const"] == "high"
    assert properties["turn_index"]["const"] == 2


def test_request_builder_uses_chat_schema_and_determinism() -> None:
    package = load_package()
    profile = profile_for(SchemaCanaryCaseId.INCIDENT_SEVERITY)

    body = build_schema_canary_request_body(
        model="auragateway-qwen2.5-0.5b-instruct",
        user_content="synthetic incident severity request",
        profile=profile,
        turn_index=1,
        authorization=package.authorization,
    )

    assert body["messages"] == [
        {
            "role": "user",
            "content": "synthetic incident severity request",
        }
    ]
    assert body["response_format"]["type"] == "json_schema"
    assert body["temperature"] == 0.0
    assert body["top_p"] == 1.0
    assert body["seed"] == 7
    assert body["max_tokens"] == 128
    assert body["stream"] is False


def test_running_checkpoint_allows_only_complete_clean_trajectories() -> None:
    checkpoint = build_schema_canary_checkpoint(
        status=SchemaCanaryLifecycleStatus.RUNNING,
        retained_trajectory_count=2,
        completed_request_count=4,
        failure_count=0,
    )

    assert checkpoint.status is SchemaCanaryLifecycleStatus.RUNNING


def test_running_checkpoint_rejects_terminal_counts() -> None:
    with pytest.raises(ValidationError):
        build_schema_canary_checkpoint(
            status=SchemaCanaryLifecycleStatus.RUNNING,
            retained_trajectory_count=3,
            completed_request_count=6,
            failure_count=0,
        )


def test_passed_checkpoint_requires_exact_complete_run() -> None:
    checkpoint = build_schema_canary_checkpoint(
        status=SchemaCanaryLifecycleStatus.PASSED,
        retained_trajectory_count=3,
        completed_request_count=6,
        failure_count=0,
    )

    assert checkpoint.status is SchemaCanaryLifecycleStatus.PASSED


def test_failed_checkpoint_accepts_first_turn_failure() -> None:
    checkpoint = build_schema_canary_checkpoint(
        status=SchemaCanaryLifecycleStatus.FAILED,
        retained_trajectory_count=1,
        completed_request_count=1,
        failure_count=1,
        abort_reason="OUTPUT_JSON_INVALID",
    )

    assert checkpoint.status is SchemaCanaryLifecycleStatus.FAILED


def test_failed_checkpoint_accepts_second_turn_failure_after_one_pass() -> None:
    checkpoint = build_schema_canary_checkpoint(
        status=SchemaCanaryLifecycleStatus.FAILED,
        retained_trajectory_count=2,
        completed_request_count=4,
        failure_count=1,
        abort_reason="TURN_TWO_CACHE_NOT_POSITIVE",
    )

    assert checkpoint.failure_count == 1


def test_failed_checkpoint_requires_abort_reason() -> None:
    with pytest.raises(ValidationError):
        build_schema_canary_checkpoint(
            status=SchemaCanaryLifecycleStatus.FAILED,
            retained_trajectory_count=1,
            completed_request_count=1,
            failure_count=1,
        )


def test_blocked_checkpoint_requires_zero_execution() -> None:
    checkpoint = build_schema_canary_checkpoint(
        status=SchemaCanaryLifecycleStatus.BLOCKED,
        retained_trajectory_count=0,
        completed_request_count=0,
        failure_count=0,
        abort_reason="AUTHORIZATION_DRIFT",
    )

    assert checkpoint.status is SchemaCanaryLifecycleStatus.BLOCKED


def test_json_artifacts_are_canonical_single_line_payloads() -> None:
    for path in (AUDIT_PATH, AUTHORIZATION_PATH):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1
        assert json.dumps(
            json.loads(text),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ) == text.rstrip("\n")
