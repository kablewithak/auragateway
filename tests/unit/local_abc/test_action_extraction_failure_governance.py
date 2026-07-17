from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_failure_governance import (
    ActionExtractionArchiveVerificationError,
    ActionExtractionArchiveVerificationFailureCode,
    ActionExtractionAuthorizationConsumedError,
    ActionExtractionAuthorizationReuseFailureCode,
    ActionExtractionCanaryAuthorizationConsumption,
    ActionExtractionCanaryEvidenceAudit,
    ActionExtractionCanaryGovernancePackage,
    ActionExtractionFailureCode,
    ActionExtractionRuntimeWarningCode,
    load_action_extraction_canary_governance_package,
    reject_action_extraction_canary_authorization_reuse,
    verify_action_extraction_canary_evidence_archive,
)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_canary_evidence_audit_v1.json"
)
CONSUMPTION_PATH = (
    ROOT / "benchmarks/local_abc/"
    "reconcile_balance_extraction_canary_authorization_consumption_v1.json"
)
CERTIFICATE_JSON_PATH = (
    ROOT / "benchmarks/local_abc/"
    "reconcile_balance_extraction_canary_semi_formal_reasoning_certificate_v1.json"
)
CERTIFICATE_MARKDOWN_PATH = (
    ROOT / "docs/benchmarks/"
    "local_abc_reconcile_balance_action_extraction_canary_"
    "semi_formal_reasoning_certificate_v1.md"
)
AUDIT_MARKDOWN_PATH = (
    ROOT / "docs/benchmarks/"
    "local_abc_reconcile_balance_action_extraction_canary_evidence_audit_v1.md"
)
EXPECTED_AUDIT_FINGERPRINT = "8e0294686db03adab55e3341914417bb0dfd630e97adc6fe36a9d671d36744bd"
AUTHORIZATION_FINGERPRINT = "9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9"
EXPECTED_MEMBER_NAMES = (
    "RECONCILE_BALANCE_EXTRACTION_CANARY_SUMMARY.txt",
    "model_snapshot_manifest_v1.json",
    "reconcile_balance_extraction_canary_checkpoint_v1.json",
    "reconcile_balance_extraction_canary_evaluation_v1.json",
    "reconcile_balance_extraction_canary_ledger_v1.jsonl",
    "reconcile_balance_extraction_canary_report_v1.json",
    "reconcile_balance_extraction_canary_schedule_v1.json",
    "worker_1.log",
)


def load_package() -> ActionExtractionCanaryGovernancePackage:
    return load_action_extraction_canary_governance_package(
        audit_path=AUDIT_PATH,
        consumption_path=CONSUMPTION_PATH,
        certificate_json_path=CERTIFICATE_JSON_PATH,
        certificate_markdown_path=CERTIFICATE_MARKDOWN_PATH,
    )


def test_governance_package_loads_and_cross_binds() -> None:
    package = load_package()

    assert package.audit.fingerprint() == EXPECTED_AUDIT_FINGERPRINT
    assert package.consumption.evidence_audit_sha256 == EXPECTED_AUDIT_FINGERPRINT
    assert package.consumption.authorization_sha256 == AUTHORIZATION_FINGERPRINT
    assert package.consumption.certificate_json_sha256 == package.audit.certificate_json_sha256


def test_archive_binding_preserves_exact_member_order_and_hashes() -> None:
    audit = load_package().audit

    assert audit.evidence_archive_sha256 == (
        "412db1700b6505502ca9afc83981738c9f50f043bad6de37e015ab7f3a9944c8"
    )
    assert audit.evidence_archive_size_bytes == 18837
    assert audit.evidence_member_count == 8
    assert tuple(member.filename for member in audit.evidence_members) == (EXPECTED_MEMBER_NAMES)
    assert audit.evidence_members[0].sha256 == (
        "9330ba95ef0be33060209d6e6f53d93abba6cdc0e5d5922352866f78924ab6d3"
    )
    assert audit.evidence_members[-1].sha256 == (
        "cc1673a44c0d180ba98209c76c6f7d14ad2d0b90f65f3ae83a2162fee569452b"
    )


def test_terminal_metrics_keep_schema_and_semantic_quality_separate() -> None:
    metrics = load_package().audit.metrics

    assert metrics.authorized_requests == 12
    assert metrics.completed_requests == 12
    assert metrics.valid_action_json == 12
    assert metrics.valid_action_schema == 12
    assert metrics.exact_identity_matches == 12
    assert metrics.deterministic_execution_successes == 12
    assert metrics.exact_operand_matches == 10
    assert metrics.exact_final_answer_matches == 10
    assert metrics.semantic_failures == 2
    assert metrics.infrastructure_failures == 0
    assert metrics.gate_decision == "failed"
    assert metrics.cleanup_status == "CLEAN"


def test_hash_resolved_failure_proofs_are_exact() -> None:
    formatted, key_value = load_package().audit.failures

    assert formatted.eval_case_id == "formatted-currency-values"
    assert formatted.failure_code is (
        ActionExtractionFailureCode.FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED
    )
    assert (
        formatted.expected_action.opening_balance,
        formatted.expected_action.credits,
        formatted.expected_action.debits,
    ) == (1200, 300, 50)
    assert (
        formatted.observed_action.opening_balance,
        formatted.observed_action.credits,
        formatted.observed_action.debits,
    ) == (200, 300, 50)
    assert formatted.expected_answer == 1450
    assert formatted.observed_result.answer == 450
    assert formatted.observed_action.fingerprint() == formatted.retained_action_sha256
    assert formatted.observed_result.fingerprint() == formatted.retained_result_sha256

    assert key_value.eval_case_id == "key-value-layout"
    assert key_value.failure_code is (
        ActionExtractionFailureCode.KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL
    )
    assert (
        key_value.expected_action.opening_balance,
        key_value.expected_action.credits,
        key_value.expected_action.debits,
    ) == (5000, 250, 1250)
    assert (
        key_value.observed_action.opening_balance,
        key_value.observed_action.credits,
        key_value.observed_action.debits,
    ) == (5000, 1250, 250)
    assert key_value.expected_answer == 4000
    assert key_value.observed_result.answer == 6000
    assert key_value.observed_action.fingerprint() == key_value.retained_action_sha256
    assert key_value.observed_result.fingerprint() == key_value.retained_result_sha256


def test_runtime_warnings_remain_non_fatal_follow_up_debt() -> None:
    warnings = load_package().audit.runtime_warnings

    assert tuple(warning.code for warning in warnings) == tuple(ActionExtractionRuntimeWarningCode)
    assert all(warning.infrastructure_failure is False for warning in warnings)
    assert all(warning.blocks_evidence_audit is False for warning in warnings)
    assert all(warning.requires_follow_up is True for warning in warnings)


def test_authorization_is_consumed_and_execution_claims_stay_blocked() -> None:
    package = load_package()
    audit = package.audit
    consumption = package.consumption

    assert audit.authorization_consumed is True
    assert audit.same_authorization_rerun_permitted is False
    assert audit.retry_only_failed_cases_permitted is False
    assert audit.gpu_execution_authorized is False
    assert audit.cache_measurement_in_scope is False
    assert audit.cache_claims_permitted is False
    assert audit.full_measured_rerun_authorized is False

    assert consumption.reusable is False
    assert consumption.execution_authorized is False
    assert consumption.retry_only_failed_cases_permitted is False
    assert consumption.corrected_notebook_generation_permitted is False
    assert consumption.gpu_execution_authorized is False
    assert consumption.cache_claims_permitted is False
    assert consumption.full_measured_rerun_authorized is False


def test_reuse_guard_raises_typed_consumed_error() -> None:
    consumption = load_package().consumption

    with pytest.raises(ActionExtractionAuthorizationConsumedError) as exc_info:
        reject_action_extraction_canary_authorization_reuse(
            authorization_fingerprint=AUTHORIZATION_FINGERPRINT,
            consumption=consumption,
        )

    assert exc_info.value.code is (
        ActionExtractionAuthorizationReuseFailureCode.AUTHORIZATION_CONSUMED
    )


def test_reuse_guard_rejects_unrelated_consumption_record() -> None:
    consumption = load_package().consumption

    with pytest.raises(ValueError, match="does not govern"):
        reject_action_extraction_canary_authorization_reuse(
            authorization_fingerprint="0" * 64,
            consumption=consumption,
        )


def test_certificate_files_match_frozen_hashes_and_verdict() -> None:
    audit = load_package().audit
    certificate = json.loads(CERTIFICATE_JSON_PATH.read_text(encoding="utf-8"))

    assert hashlib.sha256(CERTIFICATE_JSON_PATH.read_bytes()).hexdigest() == (
        audit.certificate_json_sha256
    )
    assert hashlib.sha256(CERTIFICATE_MARKDOWN_PATH.read_bytes()).hexdigest() == (
        audit.certificate_markdown_sha256
    )
    assert audit.source_certificate_markdown_sha256 == (
        "2bba7783be895dcedb3b4fa89dee94ed3750310f0383feb5cb790240987ee6eb"
    )
    assert audit.certificate_markdown_sha256 == (
        "ceaf5c7cbc9f700bae961239dab6e457cd556e57d0f4413ee3d7031da07f68e9"
    )
    assert certificate["certificate_id"] == audit.certificate_id
    assert certificate["status"] == audit.certificate_status
    assert certificate["formal_conclusion"]["verdict"] == audit.certificate_status


def test_privacy_and_spend_boundary_is_exact() -> None:
    privacy = load_package().audit.privacy

    assert privacy.raw_prompt_retained is False
    assert privacy.raw_output_retained is False
    assert privacy.raw_action_retained is False
    assert privacy.token_ids_retained is False
    assert privacy.credentials_retained is False
    assert privacy.customer_data_used is False
    assert str(privacy.external_spend) == "0"


def test_audit_rejects_member_reordering() -> None:
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    payload["evidence_members"] = list(reversed(payload["evidence_members"]))

    with pytest.raises(ValidationError, match="exact evidence member order"):
        ActionExtractionCanaryEvidenceAudit.model_validate(payload)


def test_audit_rejects_semantic_failure_reclassification() -> None:
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    payload["failures"][0]["failure_code"] = "KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL"

    with pytest.raises(ValidationError, match="exact failure family"):
        ActionExtractionCanaryEvidenceAudit.model_validate(payload)


def test_consumption_contract_rejects_authorization_reuse() -> None:
    payload = json.loads(CONSUMPTION_PATH.read_text(encoding="utf-8"))
    payload["reusable"] = True

    with pytest.raises(ValidationError):
        ActionExtractionCanaryAuthorizationConsumption.model_validate(payload)


def test_governance_package_rejects_audit_binding_drift() -> None:
    package = load_package()
    payload = package.consumption.model_dump(mode="json")
    payload["evidence_audit_sha256"] = "0" * 64
    drifted = ActionExtractionCanaryAuthorizationConsumption.model_validate(payload)

    with pytest.raises(ValidationError, match="must bind the audit fingerprint"):
        ActionExtractionCanaryGovernancePackage(
            audit=package.audit,
            consumption=drifted,
        )


def test_archive_verifier_rejects_missing_protected_archive(tmp_path: Path) -> None:
    audit = load_package().audit

    with pytest.raises(ActionExtractionArchiveVerificationError) as exc_info:
        verify_action_extraction_canary_evidence_archive(
            archive_path=tmp_path / "missing.zip",
            audit=audit,
        )

    assert exc_info.value.code is (ActionExtractionArchiveVerificationFailureCode.ARCHIVE_NOT_FOUND)


def test_archive_verifier_rejects_wrong_archive_digest(tmp_path: Path) -> None:
    audit = load_package().audit
    archive_path = tmp_path / audit.evidence_archive_filename
    with zipfile.ZipFile(archive_path, mode="w") as archive:
        for member_name in EXPECTED_MEMBER_NAMES:
            archive.writestr(member_name, b"wrong protected evidence")

    with pytest.raises(ActionExtractionArchiveVerificationError) as exc_info:
        verify_action_extraction_canary_evidence_archive(
            archive_path=archive_path,
            audit=audit,
        )

    assert exc_info.value.code is (
        ActionExtractionArchiveVerificationFailureCode.ARCHIVE_SHA256_MISMATCH
    )


def test_machine_readable_governance_json_is_canonical_where_required() -> None:
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


def test_audit_markdown_keeps_required_non_claims() -> None:
    text = AUDIT_MARKDOWN_PATH.read_text(encoding="utf-8")

    assert "schema validity guarantees semantic correctness" in text
    assert "cache savings were measured" in text
    assert "full A/B/C benchmark is authorized" in text
    assert "AuraGateway is production-ready" in text
