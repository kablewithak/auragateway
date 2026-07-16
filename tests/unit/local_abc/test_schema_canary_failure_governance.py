from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.schema_canary_failure_governance import (
    SchemaCanaryAuthorizationConsumedError,
    SchemaCanaryAuthorizationReuseFailureCode,
    SchemaCanaryRequestObservationState,
    SchemaCanaryRerunV2AuthorizationConsumption,
    SchemaCanaryRerunV23EvidenceAudit,
    SchemaCanaryRerunV23FailureCode,
    SchemaCanaryRerunV23GovernancePackage,
    load_schema_canary_rerun_v23_governance_package,
    reject_schema_canary_rerun_v2_authorization_reuse,
)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = ROOT / "benchmarks/local_abc/schema_canary_rerun_v2_3_evidence_audit.json"
CONSUMPTION_PATH = (
    ROOT / "benchmarks/local_abc/" / "schema_canary_rerun_v2_authorization_consumption.json"
)
CERTIFICATE_JSON_PATH = (
    ROOT
    / "benchmarks/local_abc/"
    / "schema_canary_rerun_v2_3_semi_formal_reasoning_certificate_v1.json"
)
CERTIFICATE_MARKDOWN_PATH = (
    ROOT
    / "docs/benchmarks/"
    / "local_abc_schema_canary_rerun_v2_3_semi_formal_reasoning_certificate_v1.md"
)
EXPECTED_AUDIT_FINGERPRINT = "772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62"
EXPECTED_CONSUMPTION_FINGERPRINT = (
    "b4260e73b6123bb2f730fbce518493b498a3f322689d6d118852ce6c456bc6c6"
)
AUTHORIZATION_FINGERPRINT = "7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66"


def load_package() -> SchemaCanaryRerunV23GovernancePackage:
    return load_schema_canary_rerun_v23_governance_package(
        audit_path=AUDIT_PATH,
        consumption_path=CONSUMPTION_PATH,
        certificate_json_path=CERTIFICATE_JSON_PATH,
        certificate_markdown_path=CERTIFICATE_MARKDOWN_PATH,
    )


def test_governance_package_loads_and_cross_binds() -> None:
    package = load_package()

    assert package.audit.fingerprint() == EXPECTED_AUDIT_FINGERPRINT
    assert package.consumption.fingerprint() == EXPECTED_CONSUMPTION_FINGERPRINT
    assert package.consumption.evidence_audit_sha256 == package.audit.fingerprint()
    assert package.consumption.authorization_sha256 == package.audit.authorization_sha256


def test_observed_request_order_and_outcomes_are_exact() -> None:
    audit = load_package().audit
    identities = tuple(
        (request.case_id, request.turn_index, request.state) for request in audit.observed_requests
    )

    assert identities == (
        ("incident-severity", 1, SchemaCanaryRequestObservationState.PASSED),
        ("incident-severity", 2, SchemaCanaryRequestObservationState.PASSED),
        (
            "payment-reconciliation",
            1,
            SchemaCanaryRequestObservationState.FAILED,
        ),
    )


def test_incident_turn_two_preserves_positive_cache_evidence() -> None:
    request = load_package().audit.observed_requests[1]

    assert request.planned_prompt_tokens == 290
    assert request.api_prompt_tokens == 290
    assert request.metric_prompt_tokens == 290
    assert request.cached_prefix_tokens == 192
    assert request.newly_computed_prefill_tokens == 98
    assert request.eligible_shared_prefix_tokens == 205
    assert request.cached_prefix_tokens <= request.eligible_shared_prefix_tokens


def test_payment_failure_is_semantic_only_at_observed_boundary() -> None:
    request = load_package().audit.observed_requests[2]

    assert request.status_code == 200
    assert request.schema_validation_passed is True
    assert request.telemetry_valid is True
    assert request.cache_gate_passed is True
    assert request.quality_passed is False
    assert request.failure_codes == (SchemaCanaryRerunV23FailureCode.OUTPUT_ANSWER_MISMATCH,)


def test_remaining_requests_are_explicitly_not_observed() -> None:
    audit = load_package().audit
    states = tuple(
        (request.case_id, request.turn_index, request.state)
        for request in audit.unobserved_requests
    )

    assert states == (
        (
            "payment-reconciliation",
            2,
            SchemaCanaryRequestObservationState.NOT_OBSERVED,
        ),
        (
            "data-sharing-policy",
            1,
            SchemaCanaryRequestObservationState.NOT_OBSERVED,
        ),
        (
            "data-sharing-policy",
            2,
            SchemaCanaryRequestObservationState.NOT_OBSERVED,
        ),
    )


def test_authorization_is_consumed_and_execution_stays_blocked() -> None:
    consumption = load_package().consumption

    assert consumption.execution_started is True
    assert consumption.observed_request_count == 3
    assert consumption.reusable is False
    assert consumption.execution_authorized is False
    assert consumption.corrected_notebook_generation_permitted is False
    assert consumption.gpu_execution_authorized is False
    assert consumption.full_measured_rerun_authorized is False


def test_reuse_guard_raises_typed_consumed_error() -> None:
    consumption = load_package().consumption

    with pytest.raises(SchemaCanaryAuthorizationConsumedError) as exc_info:
        reject_schema_canary_rerun_v2_authorization_reuse(
            authorization_fingerprint=AUTHORIZATION_FINGERPRINT,
            consumption=consumption,
        )

    assert exc_info.value.code is SchemaCanaryAuthorizationReuseFailureCode.AUTHORIZATION_CONSUMED


def test_reuse_guard_rejects_unrelated_consumption_record() -> None:
    consumption = load_package().consumption

    with pytest.raises(
        ValueError,
        match="consumption record does not govern",
    ):
        reject_schema_canary_rerun_v2_authorization_reuse(
            authorization_fingerprint="0" * 64,
            consumption=consumption,
        )


def test_certificate_files_match_frozen_hashes() -> None:
    audit = load_package().audit

    assert (
        hashlib.sha256(CERTIFICATE_JSON_PATH.read_bytes()).hexdigest()
        == audit.certificate_json_sha256
    )
    assert (
        hashlib.sha256(CERTIFICATE_MARKDOWN_PATH.read_bytes()).hexdigest()
        == audit.certificate_markdown_sha256
    )


def test_certificate_binds_evidence_and_formal_verdict() -> None:
    audit = load_package().audit
    certificate = json.loads(CERTIFICATE_JSON_PATH.read_text(encoding="utf-8"))

    assert certificate["certificate_id"] == audit.certificate_id
    assert certificate["status"] == audit.certificate_status
    assert certificate["evidence_bindings"]["archive_sha256"] == audit.evidence_archive_sha256
    assert certificate["formal_conclusion"]["verdict"] == ("CERTIFIED_FAILED_DIAGNOSTIC")
    assert certificate["adr_decision_boundary"]["certificate_does_not_choose_option"] is True


def test_audit_rejects_unobserved_request_reordering() -> None:
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    payload["unobserved_requests"] = list(reversed(payload["unobserved_requests"]))

    with pytest.raises(
        ValidationError,
        match="exact unobserved request order",
    ):
        SchemaCanaryRerunV23EvidenceAudit.model_validate(payload)


def test_audit_rejects_payment_failure_reclassification() -> None:
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    payload["observed_requests"][2]["state"] = "passed"
    payload["observed_requests"][2]["quality_passed"] = True
    payload["observed_requests"][2]["failure_codes"] = []

    with pytest.raises(
        ValidationError,
        match="payment turn one must remain failed",
    ):
        SchemaCanaryRerunV23EvidenceAudit.model_validate(payload)


def test_consumption_contract_rejects_authorization_reuse() -> None:
    payload = json.loads(CONSUMPTION_PATH.read_text(encoding="utf-8"))
    payload["reusable"] = True

    with pytest.raises(ValidationError):
        SchemaCanaryRerunV2AuthorizationConsumption.model_validate(payload)


def test_governance_package_rejects_audit_binding_drift() -> None:
    package = load_package()
    payload = package.consumption.model_dump(mode="json")
    payload["evidence_audit_sha256"] = "0" * 64
    drifted = SchemaCanaryRerunV2AuthorizationConsumption.model_validate(payload)

    with pytest.raises(
        ValidationError,
        match="must bind the evidence audit",
    ):
        SchemaCanaryRerunV23GovernancePackage(
            audit=package.audit,
            consumption=drifted,
        )


def test_machine_readable_governance_json_is_canonical() -> None:
    for path in (AUDIT_PATH, CONSUMPTION_PATH):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1
        assert json.dumps(
            json.loads(text),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ) == text.rstrip("\n")
