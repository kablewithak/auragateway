"""Regression tests for versioned action-extraction remediation v2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_failure_governance import (
    ActionExtractionFailureCode,
)
from auragateway.local_abc.action_extraction_remediation import (
    RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY,
    RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY,
    ActionExtractionRemediationControl,
    ActionExtractionRemediationManifest,
    build_reconcile_balance_extraction_response_format_v2,
    build_remediated_extraction_prompt_identity,
    load_action_extraction_remediation_manifest,
    load_action_extraction_remediation_package,
    load_action_extraction_remediation_plan,
    normalize_reconcile_balance_source_text,
    reconcile_balance_response_schema_v2_sha256,
    render_reconcile_balance_extraction_prompt_v2,
)

ROOT = Path(__file__).resolve().parents[3]
PARENT_MANIFEST_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_extraction_eval_cases_v1.json"
PARENT_PLAN_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_extraction_eval_plan_v1.json"
REMEDIATION_MANIFEST_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_remediation_cases_v2.json"
)
REMEDIATION_PLAN_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_remediation_plan_v2.json"
)

EXPECTED_MANIFEST_FINGERPRINT = "82037903ab9d944a88e6d1460a001a648308163ed7dae735cbf01359737ae4aa"
EXPECTED_PLAN_FINGERPRINT = "ebeb86b583eeff4f8b2c3ea973f67d6aaba1368a4386eb53737179ed3fd64a36"
EXPECTED_NORMALIZATION_POLICY_FINGERPRINT = (
    "7caa66d8bba36260fb97f822fdeea4f4badc16b1add1b5ed9eb5896be6257ef8"
)
EXPECTED_PROMPT_POLICY_FINGERPRINT = (
    "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
)
EXPECTED_RESPONSE_SCHEMA_SHA256 = "bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d"


def load_manifest() -> ActionExtractionRemediationManifest:
    return load_action_extraction_remediation_manifest(REMEDIATION_MANIFEST_PATH)


def test_remediation_package_binds_parent_and_v2_artifacts() -> None:
    package = load_action_extraction_remediation_package(
        parent_manifest_path=PARENT_MANIFEST_PATH,
        parent_plan_path=PARENT_PLAN_PATH,
        remediation_manifest_path=REMEDIATION_MANIFEST_PATH,
        remediation_plan_path=REMEDIATION_PLAN_PATH,
    )

    assert package.remediation_manifest.fingerprint() == EXPECTED_MANIFEST_FINGERPRINT
    assert package.remediation_plan.fingerprint() == EXPECTED_PLAN_FINGERPRINT
    assert package.remediation_plan.remediation_manifest_sha256 == (
        package.remediation_manifest.fingerprint()
    )


def test_policy_and_response_schema_fingerprints_are_frozen() -> None:
    assert (
        RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint()
        == EXPECTED_NORMALIZATION_POLICY_FINGERPRINT
    )
    assert (
        RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY.fingerprint()
        == EXPECTED_PROMPT_POLICY_FINGERPRINT
    )
    assert reconcile_balance_response_schema_v2_sha256() == EXPECTED_RESPONSE_SCHEMA_SHA256


def test_currency_and_grouping_normalization_preserves_every_integer_digit() -> None:
    result = normalize_reconcile_balance_source_text(
        "opening R1,200, credits R300, and debits R50."
    )

    assert result.normalized_text == "opening 1200, credits 300, and debits 50."
    assert result.currency_integer_normalization_count == 3
    assert result.grouped_integer_normalization_count == 0
    assert result.changed is True
    assert result.semantic_field_assignment_performed is False


def test_plain_multi_group_integer_is_normalized_without_currency_conversion() -> None:
    result = normalize_reconcile_balance_source_text("opening balance is 1,000,000,000,000 units")

    assert result.normalized_text == "opening balance is 1000000000000 units"
    assert result.currency_integer_normalization_count == 0
    assert result.grouped_integer_normalization_count == 1
    assert RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.currency_conversion_permitted is False


def test_decimal_amount_is_not_silently_coerced() -> None:
    source = "opening balance is R1,200.50"
    result = normalize_reconcile_balance_source_text(source)

    assert result.normalized_text == source
    assert result.changed is False
    assert result.currency_integer_normalization_count == 0
    assert result.grouped_integer_normalization_count == 0
    assert RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.decimal_normalization_permitted is False


def test_normalization_is_idempotent() -> None:
    first = normalize_reconcile_balance_source_text("opening R 12,500, credits R 875, debits R 375")
    second = normalize_reconcile_balance_source_text(first.normalized_text)

    assert first.normalized_text == "opening 12500, credits 875, debits 375"
    assert second.normalized_text == first.normalized_text
    assert second.changed is False


def test_normalization_does_not_reorder_or_assign_semantic_fields() -> None:
    source = "credits = 275\ndebits = 925\nopening_balance = 6000"
    result = normalize_reconcile_balance_source_text(source)

    assert result.normalized_text == source
    assert result.semantic_field_assignment_performed is False
    assert result.currency_integer_normalization_count == 0
    assert result.grouped_integer_normalization_count == 0


def test_v2_response_schema_describes_roles_without_changing_action_fields() -> None:
    response_format = build_reconcile_balance_extraction_response_format_v2()
    schema = response_format["json_schema"]["schema"]
    properties = schema["properties"]

    assert response_format["json_schema"]["name"] == "reconcile-balance-action-v2"
    assert set(properties) == {
        "schema_version",
        "capability",
        "case_id",
        "turn_index",
        "opening_balance",
        "credits",
        "debits",
    }
    assert "Current-turn opening balance only" in properties["opening_balance"]["description"]
    assert "Never bind a debit value here" in properties["credits"]["description"]
    assert "Never bind a credit value here" in properties["debits"]["description"]
    assert "answer" not in properties


def test_prompt_policy_rejects_position_binding_retries_and_model_arithmetic() -> None:
    policy = RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY

    assert policy.bind_values_by_semantic_label is True
    assert policy.position_based_field_binding_permitted is False
    assert policy.credits_debits_role_swapping_permitted is False
    assert policy.grouped_integer_digit_loss_permitted is False
    assert policy.hidden_retries_permitted is False
    assert policy.repair_attempts_permitted is False
    assert policy.arithmetic_execution_by_model_permitted is False


def test_failed_formatted_case_renders_normalized_source_and_v2_rules() -> None:
    manifest = load_manifest()
    case = next(
        case
        for case in manifest.historical_cases
        if case.eval_case_id == "formatted-currency-values"
    )
    rendered = render_reconcile_balance_extraction_prompt_v2(case)

    assert "opening balance 1200, credits 300, and debits 50" in rendered
    assert "R1,200" not in rendered
    assert "Preserve every digit when reading grouped integers" in rendered
    assert "never by position or line order" in rendered


def test_failed_key_value_case_keeps_labels_and_adds_role_binding_rules() -> None:
    manifest = load_manifest()
    case = next(
        case for case in manifest.historical_cases if case.eval_case_id == "key-value-layout"
    )
    rendered = render_reconcile_balance_extraction_prompt_v2(case)

    assert "opening_balance = 5000" in rendered
    assert "credits = 250" in rendered
    assert "debits = 1250" in rendered
    assert "Never swap credits and debits" in rendered


def test_prompt_identity_retains_hashes_not_prompt_text() -> None:
    case = load_manifest().historical_cases[0]
    identity = build_remediated_extraction_prompt_identity(case)
    serialized = identity.canonical_json()

    assert identity.source_prompt_sha256 == case.prompt_sha256
    assert identity.raw_prompt_retained is False
    assert case.user_prompt not in serialized
    assert "SYNTHETIC CASE" not in serialized


def test_all_twelve_historical_cases_are_preserved_exactly_and_in_order() -> None:
    package = load_action_extraction_remediation_package(
        parent_manifest_path=PARENT_MANIFEST_PATH,
        parent_plan_path=PARENT_PLAN_PATH,
        remediation_manifest_path=REMEDIATION_MANIFEST_PATH,
        remediation_plan_path=REMEDIATION_PLAN_PATH,
    )

    assert tuple(
        case.canonical_json() for case in package.remediation_manifest.historical_cases
    ) == tuple(case.canonical_json() for case in package.parent_manifest.accepted_cases)


def test_added_cases_cover_both_observed_failure_families_without_duplicates() -> None:
    manifest = load_manifest()
    added_ids = {case.eval_case_id for case in manifest.added_diagnostic_cases}
    added_tags = {tag for case in manifest.added_diagnostic_cases for tag in case.diagnostic_tags}

    assert added_ids == {
        "formatted-currency-multi-group",
        "formatted-currency-spaced-symbol",
        "key-value-credits-first-layout",
        "key-value-mixed-delimiters",
    }
    assert "formatted-integer-normalization" in added_tags
    assert "key-value-role-binding" in added_tags
    assert manifest.required_failure_family_coverage == (
        ActionExtractionFailureCode.FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED,
        ActionExtractionFailureCode.KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL,
    )


def test_remediation_plan_is_local_only_and_requires_the_complete_suite() -> None:
    plan = load_action_extraction_remediation_plan(REMEDIATION_PLAN_PATH)

    assert plan.controls == (
        ActionExtractionRemediationControl.DETERMINISTIC_INTEGER_LEXICAL_NORMALIZATION,
        ActionExtractionRemediationControl.SEMANTIC_ROLE_BOUND_INSTRUCTION,
        ActionExtractionRemediationControl.ROLE_DESCRIBED_RESPONSE_SCHEMA,
    )
    assert plan.total_case_count == 16
    assert plan.complete_suite_required is True
    assert plan.failed_case_only_execution_permitted is False
    assert plan.execution_authorized is False
    assert plan.gpu_execution_authorized is False
    assert plan.new_authorization_issued is False
    assert plan.full_measured_rerun_authorized is False
    assert plan.cache_measurement_in_scope is False
    assert plan.cache_claims_permitted is False
    assert plan.next_gate == "bounded_action_extraction_v2_authorization_review"


def test_remediation_does_not_add_semantic_parser_fallback_or_model_upgrade() -> None:
    plan = load_action_extraction_remediation_plan(REMEDIATION_PLAN_PATH)

    assert plan.deterministic_semantic_parser_fallback_permitted is False
    assert plan.direct_model_arithmetic_fallback_permitted is False
    assert plan.model_upgrade_permitted is False
    assert plan.hidden_retry_count == 0
    assert plan.repair_attempt_count == 0
    assert plan.replacement_request_count == 0


def test_manifest_tampering_fails_closed() -> None:
    payload = json.loads(REMEDIATION_MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["parent_evidence_audit_sha256"] = "0" * 64

    with pytest.raises(ValidationError, match="parent_evidence_audit_sha256"):
        ActionExtractionRemediationManifest.model_validate(payload)


def test_historical_case_mutation_breaks_package_binding(tmp_path: Path) -> None:
    payload = json.loads(REMEDIATION_MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["historical_cases"][0]["accept_reason"] = (
        "A deliberately mutated but still schema-valid reason used to prove drift detection."
    )
    mutated_manifest = ActionExtractionRemediationManifest.model_validate(payload)
    mutated_path = tmp_path / "mutated-remediation-manifest.json"
    mutated_path.write_text(mutated_manifest.canonical_json(), encoding="utf-8")

    with pytest.raises(ValidationError, match="historical cases must be preserved"):
        load_action_extraction_remediation_package(
            parent_manifest_path=PARENT_MANIFEST_PATH,
            parent_plan_path=PARENT_PLAN_PATH,
            remediation_manifest_path=mutated_path,
            remediation_plan_path=REMEDIATION_PLAN_PATH,
        )
