"""Regression tests for the immutable v2 action-extraction evidence audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_requalification_evidence_audit import (
    ActionExtractionArchiveVerificationError,
    ActionExtractionArchiveVerificationFailureCode,
    ActionExtractionAuthorizationConsumedError,
    ActionExtractionAuthorizationReuseFailureCode,
    ActionExtractionGovernancePackage,
    ActionExtractionRequalificationEvidenceAudit,
    assert_action_extraction_v2_authorization_not_reusable,
    load_action_extraction_requalification_governance_package,
    sha256_file,
    verify_action_extraction_requalification_evidence_archive,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_ROOT = REPOSITORY_ROOT / "benchmarks" / "local_abc"
DOCS_ROOT = REPOSITORY_ROOT / "docs"
AUDIT_PATH = BENCHMARK_ROOT / "reconcile_balance_extraction_requalification_evidence_audit_v2.json"
CERTIFICATE_JSON_PATH = (
    BENCHMARK_ROOT / "reconcile_balance_extraction_requalification_"
    "semi_formal_reasoning_certificate_v2.json"
)
CONSUMPTION_PATH = (
    BENCHMARK_ROOT / "reconcile_balance_extraction_requalification_"
    "authorization_consumption_v2.json"
)
CERTIFICATE_MARKDOWN_PATH = (
    DOCS_ROOT / "benchmarks" / "local_abc_reconcile_balance_action_extraction_requalification_"
    "semi_formal_reasoning_certificate_v2.md"
)
AUDIT_MARKDOWN_PATH = (
    DOCS_ROOT / "benchmarks" / "local_abc_reconcile_balance_action_extraction_requalification_"
    "evidence_audit_v2.md"
)
RECOVERY_RUNBOOK_PATH = DOCS_ROOT / "runbooks" / "local_abc_kaggle_recovery_topology_v1.md"
EXPECTED_AUDIT_SHA256 = "a6a1031d85997d8b13b521866d580ce468579cfbb8d731180820fdcc5dd0be79"
EXPECTED_CERTIFICATE_SHA256 = "5f3477801f19e14743a621d48bd2a68ac5ced967ef15f9c00ca67a94421cc71e"
EXPECTED_CONSUMPTION_SHA256 = "51b36a3ac4e6122c2cf9fa9e5132d26e57af101a19714cb4cd60c4c71afdff4f"


def _load_package() -> ActionExtractionGovernancePackage:
    return load_action_extraction_requalification_governance_package(
        audit_path=AUDIT_PATH,
        certificate_json_path=CERTIFICATE_JSON_PATH,
        certificate_markdown_path=CERTIFICATE_MARKDOWN_PATH,
        consumption_path=CONSUMPTION_PATH,
    )


def test_governance_package_loads_with_exact_fingerprints() -> None:
    package = _load_package()

    assert package.audit.fingerprint() == EXPECTED_AUDIT_SHA256
    assert package.certificate.fingerprint() == EXPECTED_CERTIFICATE_SHA256
    assert package.consumption.fingerprint() == EXPECTED_CONSUMPTION_SHA256


def test_audit_certifies_the_complete_quality_gate() -> None:
    audit = _load_package().audit

    assert audit.quality_gate_passed is True
    assert audit.metrics.completed_requests == 16
    assert audit.metrics.exact_operand_matches == 16
    assert audit.metrics.exact_final_answer_matches == 16
    assert audit.metrics.semantic_failures == 0
    assert audit.metrics.infrastructure_failures == 0


def test_audit_preserves_complete_case_order() -> None:
    audit = _load_package().audit

    assert len(audit.case_ids) == 16
    assert audit.case_ids[0] == "historical-turn-one"
    assert audit.case_ids[6] == "formatted-currency-values"
    assert audit.case_ids[7] == "key-value-layout"
    assert audit.case_ids[-1] == "key-value-mixed-delimiters"
    assert len(set(audit.case_ids)) == 16


def test_audit_records_both_non_invalidating_findings() -> None:
    audit = _load_package().audit

    assert [finding.code.value for finding in audit.findings] == [
        "STALE_SCORE_PROMPT_IDENTITY_METADATA",
        "OVERSTATED_CLEANUP_STATUS",
    ]
    assert [finding.observed_count for finding in audit.findings] == [16, 2]
    assert all(finding.invalidates_quality_gate is False for finding in audit.findings)
    assert all(finding.requires_rerun is False for finding in audit.findings)


def test_audit_distinguishes_declared_and_audited_cleanup() -> None:
    metrics = _load_package().audit.metrics

    assert metrics.declared_cleanup_status == "CLEAN"
    assert metrics.audited_cleanup_status == "CLEAN_WITH_RUNTIME_WARNINGS"
    assert metrics.worker_return_code == 0
    assert metrics.worker_port_closed is True


def test_runtime_warnings_are_complete_and_ordered() -> None:
    warnings = _load_package().audit.runtime_warnings

    assert [warning.code.value for warning in warnings] == [
        "SITECUSTOMIZE_WRAP_MISSING",
        "BFLOAT16_CAST_TO_FLOAT16",
        "EAGER_MODE_COMPILE_DISABLED",
        "CUDA_BINDINGS_DEPRECATION",
        "TRITON_JIT_DURING_INFERENCE",
        "FORCED_PROCESS_TERMINATION",
        "LEAKED_SEMAPHORE",
    ]
    assert [warning.observed_count for warning in warnings] == [3, 1, 2, 1, 2, 1, 1]
    assert all(warning.infrastructure_failure is False for warning in warnings)


def test_artifact_bindings_preserve_v2_and_legacy_prompt_identities() -> None:
    artifacts = _load_package().audit.artifacts

    assert artifacts.schedule_prompt_policy_sha256 == (
        "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
    )
    assert artifacts.legacy_score_prompt_policy_sha256 == (
        "5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"
    )
    assert artifacts.schedule_prompt_policy_sha256 != artifacts.legacy_score_prompt_policy_sha256


def test_evidence_archive_members_are_frozen() -> None:
    audit = _load_package().audit

    assert audit.evidence_archive_sha256 == (
        "b7da2b703232154742665b47254e662a2e6ff4b6e198827e7d29f67dc9c16c93"
    )
    assert audit.evidence_archive_size_bytes == 22767
    assert audit.evidence_member_count == 8
    assert len(audit.evidence_members) == 8
    assert audit.evidence_members[-1].filename == "worker_1_v2.log"


def test_privacy_and_spend_boundaries_remain_closed() -> None:
    privacy = _load_package().audit.privacy

    assert privacy.raw_prompt_retained is False
    assert privacy.raw_output_retained is False
    assert privacy.raw_action_retained is False
    assert privacy.token_ids_retained is False
    assert privacy.customer_data_used is False
    assert str(privacy.external_spend) == "0"
    assert privacy.credentials_retained is False


def test_consumed_authorization_cannot_be_reused() -> None:
    consumption = _load_package().consumption

    with pytest.raises(ActionExtractionAuthorizationConsumedError) as exc_info:
        assert_action_extraction_v2_authorization_not_reusable(consumption)

    assert (
        exc_info.value.code is ActionExtractionAuthorizationReuseFailureCode.AUTHORIZATION_CONSUMED
    )


def test_consumption_binds_audit_and_certificate() -> None:
    package = _load_package()

    assert package.consumption.evidence_audit_sha256 == package.audit.fingerprint()
    assert package.consumption.certificate_json_sha256 == package.certificate.fingerprint()
    assert package.consumption.reusable is False
    assert package.consumption.notebook_rerun_permitted is False
    assert package.consumption.failed_case_only_execution_permitted is False


def test_certificate_preserves_non_claims_and_next_gate() -> None:
    package = _load_package()

    assert package.certificate.quality_result == ("16_OF_16_EXACT_OPERANDS_AND_FINAL_ANSWERS")
    assert package.certificate.rerun_permitted is False
    assert package.certificate.full_abc_authorized is False
    assert package.certificate.next_gate == ("action_extraction_v2_traceability_cleanup_hardening")
    assert package.audit.full_measured_rerun_authorized is False


def test_certificate_markdown_preserves_full_reasoning_constitution() -> None:
    text = CERTIFICATE_MARKDOWN_PATH.read_text(encoding="utf-8")

    required_sections = (
        "## 4. Definitions",
        "## 5. Premises",
        "## 6. Evidence Trace",
        "## 7. Alternative-Hypothesis Checks",
        "## 8. Formal Derivation",
        "## 9. Formal Conclusion",
        "## 11. Non-Claims",
    )
    for section in required_sections:
        assert section in text

    assert "H1=REFUTED" in text
    assert "H5=REFUTED_AND_PROHIBITED" in text
    assert "quality_gate_passed=true" in text
    assert "audited_cleanup_status=CLEAN_WITH_RUNTIME_WARNINGS" in text
    assert "RERUN_STATUS=PROHIBITED" in text


def test_json_artifacts_are_canonical_single_line_files() -> None:
    for path in (AUDIT_PATH, CERTIFICATE_JSON_PATH, CONSUMPTION_PATH):
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        assert text == canonical


def test_raw_file_hashes_match_model_fingerprints() -> None:
    package = _load_package()

    assert sha256_file(AUDIT_PATH) == package.audit.fingerprint()
    assert sha256_file(CERTIFICATE_JSON_PATH) == package.certificate.fingerprint()
    assert sha256_file(CONSUMPTION_PATH) == package.consumption.fingerprint()


def test_mutated_case_order_fails_closed() -> None:
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    payload["case_ids"][0], payload["case_ids"][1] = (
        payload["case_ids"][1],
        payload["case_ids"][0],
    )

    with pytest.raises(ValidationError, match="complete 16-case order"):
        ActionExtractionRequalificationEvidenceAudit.model_validate(payload)


def test_mutated_archive_digest_fails_closed() -> None:
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    payload["evidence_archive_sha256"] = "0" * 64

    with pytest.raises(ValidationError, match="archive digest drifted"):
        ActionExtractionRequalificationEvidenceAudit.model_validate(payload)


def test_missing_protected_archive_has_stable_failure_code(tmp_path: Path) -> None:
    missing = tmp_path / "missing-evidence.zip"

    with pytest.raises(ActionExtractionArchiveVerificationError) as exc_info:
        verify_action_extraction_requalification_evidence_archive(missing)

    assert exc_info.value.code is ActionExtractionArchiveVerificationFailureCode.ARCHIVE_NOT_FOUND


def test_unqualified_archive_digest_has_stable_failure_code(tmp_path: Path) -> None:
    archive = tmp_path / "evidence.zip"
    archive.write_bytes(b"not-the-governed-archive")

    with pytest.raises(ActionExtractionArchiveVerificationError) as exc_info:
        verify_action_extraction_requalification_evidence_archive(archive)

    assert exc_info.value.code is (
        ActionExtractionArchiveVerificationFailureCode.ARCHIVE_SHA256_MISMATCH
    )


def test_certificate_markdown_mutation_breaks_package_loading(tmp_path: Path) -> None:
    mutated = tmp_path / CERTIFICATE_MARKDOWN_PATH.name
    mutated.write_text(
        CERTIFICATE_MARKDOWN_PATH.read_text(encoding="utf-8") + "\nmutation\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="certificate Markdown SHA-256 mismatch"):
        load_action_extraction_requalification_governance_package(
            audit_path=AUDIT_PATH,
            certificate_json_path=CERTIFICATE_JSON_PATH,
            certificate_markdown_path=mutated,
            consumption_path=CONSUMPTION_PATH,
        )


def test_audit_document_records_canonical_evaluation_digest() -> None:
    text = AUDIT_MARKDOWN_PATH.read_text(encoding="utf-8")

    assert "aac8cb14732b7e3019c0fccc2b8516df997682f973df4262683d70812b0c32fd" in text
    assert "CLEAN_WITH_RUNTIME_WARNINGS" in text
    assert "No rerun" not in text
    assert "No notebook restart" in text


def test_recovery_runbook_freezes_the_two_recovery_outputs() -> None:
    text = RECOVERY_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "AuraGateway Package Recovery v2" in text
    assert "auragateway-vllm-wheel-recovery-v1" in text
    assert "auragateway-local-abc-action-extraction-requalification-notebook-v2.zip" in text
    assert "vllm-0.25.1+cu129-cp38-abi3-manylinux_2_28_x86_64.whl" in text
    assert "Import the exact frozen `.ipynb` again" in text
    assert "Do not rerun failed cells" in text
