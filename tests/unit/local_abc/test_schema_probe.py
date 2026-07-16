from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.measured_quality import (
    MeasuredOutputShape,
    MeasuredQualityCheck,
)
from auragateway.local_abc.schema_probe import (
    IncidentSeverityProbeOutput,
    SchemaProbeAuthorizationPackage,
    SchemaProbeLifecycleStatus,
    build_schema_probe_request_body,
    build_schema_probe_response_format,
    build_terminal_schema_probe_checkpoint,
    load_schema_probe_authorization_package,
)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = ROOT / "benchmarks/local_abc/measured_quality_canary_v1_evidence_audit.json"
AUTHORIZATION_PATH = (
    ROOT / "benchmarks/local_abc/schema_constrained_output_probe_authorization_v1.json"
)
EXPECTED_AUDIT_FINGERPRINT = "6b403f4fe75ed530dbf733b62443504197ecfe3457df51abb5eccf620cb2bcd2"
EXPECTED_AUTHORIZATION_FINGERPRINT = (
    "d8066307c9bb327dbe5bd7d61e7b8c33ff352bd7e4ee50bc3d1fdd6f26dc7f6e"
)


def load_package() -> SchemaProbeAuthorizationPackage:
    return load_schema_probe_authorization_package(
        audit_path=AUDIT_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )


def test_package_loads_and_cross_binds() -> None:
    package = load_package()

    assert package.audit.fingerprint() == EXPECTED_AUDIT_FINGERPRINT
    assert package.authorization.fingerprint() == EXPECTED_AUTHORIZATION_FINGERPRINT
    assert package.authorization.failed_canary_audit_sha256 == EXPECTED_AUDIT_FINGERPRINT


def test_failed_canary_audit_preserves_exact_evidence() -> None:
    audit = load_package().audit

    assert audit.completed_request_count == 1
    assert audit.request_status_code == 200
    assert audit.prompt_token_count == 282
    assert audit.completion_token_count == 110
    assert audit.output_character_count == 551
    assert audit.finish_reason == "stop"
    assert audit.cleanup_status == "CLEAN"


def test_failed_canary_audit_freezes_secondary_defects() -> None:
    audit = load_package().audit

    assert audit.trajectory_failure_codes_propagated is False
    assert audit.checkpoint_terminal_status_correct is False
    assert audit.checkpoint_status == "RUNNING"
    assert audit.execution_status == "CANARY_EXECUTION_ABORTED"


def test_probe_authorizes_one_request_only() -> None:
    authorization = load_package().authorization

    assert authorization.execution_authorized is True
    assert authorization.request_count == 1
    assert authorization.max_request_failures == 0
    assert authorization.cache_reuse_evaluation_permitted is False
    assert authorization.six_request_canary_rerun_authorized is False
    assert authorization.full_measured_rerun_authorized is False


def test_probe_requires_every_quality_check() -> None:
    authorization = load_package().authorization

    assert authorization.required_quality_checks == tuple(MeasuredQualityCheck)
    assert authorization.expected_output_shape is MeasuredOutputShape.JSON_OBJECT
    assert authorization.expected_answer == "sev3"


def test_response_format_is_exact_json_schema() -> None:
    response_format = build_schema_probe_response_format()

    assert response_format["type"] == "json_schema"
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "answer",
        "case_id",
        "confidence",
        "turn_index",
    ]
    assert schema["properties"]["answer"]["enum"] == [
        "sev1",
        "sev2",
        "sev3",
        "sev4",
    ]


def test_request_body_uses_chat_completions_contract() -> None:
    authorization = load_package().authorization

    body = build_schema_probe_request_body(
        model="auragateway-qwen2.5-0.5b-instruct",
        user_content="synthetic incident severity probe",
        authorization=authorization,
    )

    assert body["messages"] == [
        {
            "role": "user",
            "content": "synthetic incident severity probe",
        }
    ]
    assert body["response_format"]["type"] == "json_schema"
    assert body["max_tokens"] == 128
    assert body["temperature"] == 0.0
    assert body["stream"] is False


def test_probe_output_schema_rejects_extra_keys() -> None:
    with pytest.raises(ValidationError):
        IncidentSeverityProbeOutput.model_validate(
            {
                "answer": "sev3",
                "case_id": "incident-severity",
                "confidence": "high",
                "turn_index": 1,
                "extra": "forbidden",
            }
        )


def test_terminal_pass_checkpoint_is_not_running() -> None:
    checkpoint = build_terminal_schema_probe_checkpoint(passed=True)

    assert checkpoint.status is SchemaProbeLifecycleStatus.PASSED
    assert checkpoint.completed_request_count == 1
    assert checkpoint.failure_count == 0


def test_terminal_failure_checkpoint_is_not_running() -> None:
    checkpoint = build_terminal_schema_probe_checkpoint(
        passed=False,
        abort_reason="OUTPUT_JSON_INVALID",
    )

    assert checkpoint.status is SchemaProbeLifecycleStatus.FAILED
    assert checkpoint.completed_request_count == 1
    assert checkpoint.failure_count == 1
    assert checkpoint.abort_reason == "OUTPUT_JSON_INVALID"


def test_failed_checkpoint_requires_abort_reason() -> None:
    with pytest.raises(ValueError, match="abort reason"):
        build_terminal_schema_probe_checkpoint(passed=False)


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
