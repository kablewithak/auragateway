from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.measured_quality import MeasuredQualityCheck
from auragateway.local_abc.measured_remediation import (
    CorrectedRunClassification,
    MeasuredQualityRemediationPackage,
    MeasuredRunDefectCode,
    MeasuredRunV1EvidenceAudit,
    load_measured_quality_remediation_package,
)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = ROOT / "benchmarks/local_abc/measured_run_v1_evidence_audit.json"
CANARY_PATH = ROOT / "benchmarks/local_abc/measured_quality_canary_authorization_v1.json"
EXPECTED_AUDIT_FINGERPRINT = "f4b458f18e1ff304b0000897af4bf33fc79c1e270766bc61b59e5a1901bd780e"
EXPECTED_CANARY_FINGERPRINT = "ae4657143927fff0594c1cc0766ef8927d8bd603dec3a0b939c1d8003956fdf0"


def load_package() -> MeasuredQualityRemediationPackage:
    return load_measured_quality_remediation_package(
        audit_path=AUDIT_PATH,
        canary_authorization_path=CANARY_PATH,
    )


def test_remediation_package_loads_and_cross_binds() -> None:
    package = load_package()

    assert package.audit.fingerprint() == EXPECTED_AUDIT_FINGERPRINT
    assert package.canary.fingerprint() == EXPECTED_CANARY_FINGERPRINT
    assert package.canary.measured_v1_audit_sha256 == EXPECTED_AUDIT_FINGERPRINT


def test_v1_run_is_corrected_to_diagnostic_only() -> None:
    audit = load_package().audit

    assert audit.corrected_classification is CorrectedRunClassification.DIAGNOSTIC_ONLY
    assert audit.telemetry_measurement_scope_accepted is True
    assert audit.quality_preserving_benchmark_qualified is False
    assert audit.full_measured_rerun_authorized is False


def test_v1_quality_counts_capture_the_silent_failure() -> None:
    quality = load_package().audit.quality

    assert quality.turn_count == 144
    assert quality.reported_valid_turn_count == 144
    assert quality.json_parse_pass_count == 0
    assert quality.corrected_quality_eligible_turn_count == 0
    assert quality.empty_output_count == 126
    assert quality.truncated_output_count == 18


def test_v1_telemetry_scope_retains_primary_cache_evidence() -> None:
    telemetry = load_package().audit.telemetry

    assert telemetry.primary_pair_count == 24
    assert telemetry.condition_a_turn2_cached_tokens == 0
    assert telemetry.condition_b_turn2_cached_tokens == 0
    assert telemetry.condition_c_turn2_cached_tokens == 176
    assert telemetry.primary_pairwise_win_rate == "1.0"


def test_all_three_root_defects_are_frozen() -> None:
    assert load_package().audit.defects == tuple(MeasuredRunDefectCode)


def test_canary_authorizes_only_three_trajectories_and_six_requests() -> None:
    canary = load_package().canary

    assert canary.canary_execution_authorized is True
    assert canary.trajectory_count == 3
    assert canary.request_count == 6
    assert canary.full_measured_rerun_authorized is False
    assert canary.max_trajectory_failures == 0


def test_canary_requires_every_quality_check_and_positive_cache() -> None:
    canary = load_package().canary

    assert canary.required_quality_checks == tuple(MeasuredQualityCheck)
    assert canary.required_quality_pass_rate == "1.0"
    assert canary.require_positive_turn2_cached_tokens is True


def test_canary_uses_chat_template_transport_with_larger_output_budget() -> None:
    transport = load_package().canary.transport

    assert transport.transport_id == "qwen-chat-template-single-user-v1"
    assert transport.add_generation_prompt is True
    assert transport.max_output_tokens == 128
    assert transport.raw_prompt_logging_permitted is False


def test_tampered_audit_breaks_cross_file_binding() -> None:
    package = load_package()
    audit_payload = package.audit.model_dump(mode="json")
    audit_payload["quality"]["empty_output_count"] = 125

    with pytest.raises(ValidationError):
        tampered = MeasuredRunV1EvidenceAudit.model_validate(audit_payload)
        MeasuredQualityRemediationPackage(
            audit=tampered,
            canary=package.canary,
        )


def test_json_artifacts_are_canonical_single_line_payloads() -> None:
    for path in (AUDIT_PATH, CANARY_PATH):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1
        assert json.dumps(
            json.loads(text),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ) == text.rstrip("\n")
