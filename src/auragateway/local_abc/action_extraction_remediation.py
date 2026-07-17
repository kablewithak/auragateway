"""Versioned local remediation for reconcile-balance action extraction."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.action_extraction_eval import (
    ActionExtractionEvaluationPlan,
    EvaluationThresholds,
    ReconcileBalanceExtractionCase,
    ReconcileBalanceExtractionManifest,
    load_action_extraction_evaluation_plan,
    load_reconcile_balance_extraction_manifest,
)
from auragateway.local_abc.action_extraction_failure_governance import (
    ActionExtractionCanaryClassification,
    ActionExtractionFailureCode,
)
from auragateway.local_abc.arithmetic_action import (
    ReconcileBalanceAction,
    reconcile_balance_action_schema_sha256,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_CURRENCY_INTEGER_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?P<currency>R|\$|€|£)\s*"
    r"(?P<number>\d{1,3}(?:,\d{3})+|\d+)(?!\d|,\d{3}|\.\d)"
)
_GROUPED_INTEGER_PATTERN = re.compile(r"(?<![\d,])(?P<number>\d{1,3}(?:,\d{3})+)(?!\d|,\d{3}|\.\d)")

_PARENT_CASE_MANIFEST_SHA256: Final = (
    "babfd460048784991041957fc50e29853d6caa29ba195207bd8f2ad1088bbbf5"
)
_PARENT_EVALUATION_PLAN_SHA256: Final = (
    "53a9dc8f3418b4df86151ad9763d44ddd16179ed5d4ca7ac505c3b2f7e401b62"
)
_PARENT_PROMPT_POLICY_SHA256: Final = (
    "5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"
)
_PARENT_ACTION_SCHEMA_SHA256: Final = (
    "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
)
_PARENT_EVIDENCE_AUDIT_SHA256: Final = (
    "8e0294686db03adab55e3341914417bb0dfd630e97adc6fe36a9d671d36744bd"
)
_PARENT_EVIDENCE_ARCHIVE_SHA256: Final = (
    "412db1700b6505502ca9afc83981738c9f50f043bad6de37e015ab7f3a9944c8"
)
_EXPECTED_HISTORICAL_CASE_COUNT: Final = 12
_EXPECTED_ADDED_CASE_COUNT: Final = 4
_EXPECTED_TOTAL_CASE_COUNT: Final = 16

_STABLE_INSTRUCTION_V2 = """You are an action extraction component.
Return exactly one JSON object matching the supplied schema.
Extract capability, case identity, turn identity, opening_balance, credits, and debits.
Do not calculate or emit the final reconciliation answer.
Do not add explanations, Markdown, or unrequested fields.
Use only the current synthetic case facts; ignore metadata and historical distractors.
Treat currency symbols and integer grouping separators as formatting only.
Preserve every digit when reading grouped integers; never drop a leading group.
Bind values by their explicit semantic labels, never by position or line order.
opening_balance must come only from the current opening-balance field or phrase.
credits must come only from the current credits field or phrase.
debits must come only from the current debits field or phrase.
Never swap credits and debits, even when their values or line order are asymmetric.
"""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ActionExtractionRemediationControl(StrEnum):
    """Explicit controls introduced by the v2 remediation candidate."""

    DETERMINISTIC_INTEGER_LEXICAL_NORMALIZATION = "deterministic_integer_lexical_normalization"
    SEMANTIC_ROLE_BOUND_INSTRUCTION = "semantic_role_bound_instruction"
    ROLE_DESCRIBED_RESPONSE_SCHEMA = "role_described_response_schema"


class IntegerSourceNormalizationPolicy(LocalABCContract):
    """Deterministic lexical normalization without semantic field extraction."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["reconcile-balance-integer-source-normalization-v1"] = (
        "reconcile-balance-integer-source-normalization-v1"
    )
    accepted_currency_markers: tuple[str, ...] = ("R", "$", "€", "£")
    currency_integer_pattern_sha256: str
    grouped_integer_pattern_sha256: str
    remove_currency_marker_before_integer: Literal[True] = True
    remove_integer_grouping_commas: Literal[True] = True
    decimal_normalization_permitted: Literal[False] = False
    currency_conversion_permitted: Literal[False] = False
    semantic_field_assignment_permitted: Literal[False] = False
    raw_source_retention_in_evidence_permitted: Literal[False] = False

    @field_validator("accepted_currency_markers")
    @classmethod
    def validate_currency_markers(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = ("R", "$", "€", "£")
        if value != expected:
            raise ValueError("currency markers must remain in the frozen canonical order")
        return value

    @field_validator("currency_integer_pattern_sha256", "grouped_integer_pattern_sha256")
    @classmethod
    def validate_pattern_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("normalization pattern digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_pattern_bindings(self) -> Self:
        if self.currency_integer_pattern_sha256 != _sha256_text(_CURRENCY_INTEGER_PATTERN.pattern):
            raise ValueError("currency-integer regex binding drifted")
        if self.grouped_integer_pattern_sha256 != _sha256_text(_GROUPED_INTEGER_PATTERN.pattern):
            raise ValueError("grouped-integer regex binding drifted")
        return self


RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY = IntegerSourceNormalizationPolicy(
    currency_integer_pattern_sha256=_sha256_text(_CURRENCY_INTEGER_PATTERN.pattern),
    grouped_integer_pattern_sha256=_sha256_text(_GROUPED_INTEGER_PATTERN.pattern),
)


class NormalizedExtractionInput(LocalABCContract):
    """Transient normalized source plus evidence-safe transformation metadata."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_sha256: str
    source_text: str = Field(min_length=1, exclude=True, repr=False)
    normalized_text: str = Field(min_length=1, exclude=True, repr=False)
    source_text_sha256: str
    normalized_text_sha256: str
    source_character_count: int = Field(ge=1)
    normalized_character_count: int = Field(ge=1)
    currency_integer_normalization_count: int = Field(ge=0)
    grouped_integer_normalization_count: int = Field(ge=0)
    changed: bool
    raw_source_retained_in_evidence: Literal[False] = False
    semantic_field_assignment_performed: Literal[False] = False

    @field_validator("policy_sha256", "source_text_sha256", "normalized_text_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("normalization digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_normalization(self) -> Self:
        if self.policy_sha256 != RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint():
            raise ValueError("normalization result must bind the frozen policy")
        if self.source_text_sha256 != _sha256_text(self.source_text):
            raise ValueError("source text digest drifted")
        if self.normalized_text_sha256 != _sha256_text(self.normalized_text):
            raise ValueError("normalized text digest drifted")
        if self.source_character_count != len(self.source_text):
            raise ValueError("source character count drifted")
        if self.normalized_character_count != len(self.normalized_text):
            raise ValueError("normalized character count drifted")
        if self.changed != (self.source_text != self.normalized_text):
            raise ValueError("changed flag must match the actual transformation")
        if not self.changed and any(
            (
                self.currency_integer_normalization_count,
                self.grouped_integer_normalization_count,
            )
        ):
            raise ValueError("unchanged input cannot report normalization events")
        return self


class ActionExtractionRemediationPromptPolicy(LocalABCContract):
    """Frozen prompt, normalization, response-schema, and retention policy."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    policy_id: Literal["reconcile-balance-action-extraction-prompt-v2"] = (
        "reconcile-balance-action-extraction-prompt-v2"
    )
    stable_instruction_sha256: str
    stable_instruction_character_count: int = Field(ge=1)
    source_normalization_policy_sha256: str
    response_schema_sha256: str
    action_schema_sha256: str
    bind_values_by_semantic_label: Literal[True] = True
    position_based_field_binding_permitted: Literal[False] = False
    credits_debits_role_swapping_permitted: Literal[False] = False
    grouped_integer_digit_loss_permitted: Literal[False] = False
    direct_answer_permitted: Literal[False] = False
    arithmetic_execution_by_model_permitted: Literal[False] = False
    extra_text_permitted: Literal[False] = False
    raw_prompt_retained_in_evidence: Literal[False] = False
    raw_output_retained_in_evidence: Literal[False] = False
    hidden_retries_permitted: Literal[False] = False
    repair_attempts_permitted: Literal[False] = False
    synthetic_data_only: Literal[True] = True

    @field_validator(
        "stable_instruction_sha256",
        "source_normalization_policy_sha256",
        "response_schema_sha256",
        "action_schema_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("remediation policy digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        if self.stable_instruction_sha256 != _sha256_text(_STABLE_INSTRUCTION_V2):
            raise ValueError("prompt policy must bind the frozen v2 instruction")
        if self.stable_instruction_character_count != len(_STABLE_INSTRUCTION_V2):
            raise ValueError("prompt policy instruction character count drifted")
        if (
            self.source_normalization_policy_sha256
            != RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint()
        ):
            raise ValueError("prompt policy must bind the integer normalization policy")
        if self.response_schema_sha256 != reconcile_balance_response_schema_v2_sha256():
            raise ValueError("prompt policy must bind the role-described response schema")
        if self.action_schema_sha256 != reconcile_balance_action_schema_sha256():
            raise ValueError("prompt policy must preserve the deterministic action contract")
        return self


class RemediatedExtractionPromptIdentity(LocalABCContract):
    """Hash-only identity for source normalization and v2 prompt rendering."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    prompt_policy_sha256: str
    normalization_policy_sha256: str
    response_schema_sha256: str
    source_prompt_sha256: str
    source_prompt_character_count: int = Field(ge=1)
    normalized_prompt_sha256: str
    normalized_prompt_character_count: int = Field(ge=1)
    rendered_prompt_sha256: str
    rendered_prompt_character_count: int = Field(ge=1)
    currency_integer_normalization_count: int = Field(ge=0)
    grouped_integer_normalization_count: int = Field(ge=0)
    raw_prompt_retained: Literal[False] = False

    @field_validator(
        "prompt_policy_sha256",
        "normalization_policy_sha256",
        "response_schema_sha256",
        "source_prompt_sha256",
        "normalized_prompt_sha256",
        "rendered_prompt_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("prompt identity digests must be lowercase SHA-256")
        return value


class ActionExtractionRemediationManifest(LocalABCContract):
    """Versioned full-suite case constitution for remediation requalification."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    manifest_id: Literal["reconcile-balance-extraction-remediation-cases-v2"] = (
        "reconcile-balance-extraction-remediation-cases-v2"
    )
    parent_case_manifest_sha256: str
    parent_evaluation_plan_sha256: str
    parent_evidence_audit_sha256: str
    parent_evidence_archive_sha256: str
    action_schema_sha256: str
    normalization_policy_sha256: str
    prompt_policy_sha256: str
    response_schema_sha256: str
    historical_cases: tuple[ReconcileBalanceExtractionCase, ...] = Field(min_length=12)
    added_diagnostic_cases: tuple[ReconcileBalanceExtractionCase, ...] = Field(min_length=4)
    historical_case_count: Literal[12] = 12
    added_diagnostic_case_count: Literal[4] = 4
    total_case_count: Literal[16] = 16
    required_failure_family_coverage: tuple[
        Literal[ActionExtractionFailureCode.FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED],
        Literal[ActionExtractionFailureCode.KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL],
    ] = (
        ActionExtractionFailureCode.FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED,
        ActionExtractionFailureCode.KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL,
    )
    synthetic_data_only: Literal[True] = True
    raw_prompt_retention_in_evidence_permitted: Literal[False] = False
    raw_output_retention_in_evidence_permitted: Literal[False] = False
    execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False

    @field_validator(
        "parent_case_manifest_sha256",
        "parent_evaluation_plan_sha256",
        "parent_evidence_audit_sha256",
        "parent_evidence_archive_sha256",
        "action_schema_sha256",
        "normalization_policy_sha256",
        "prompt_policy_sha256",
        "response_schema_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("remediation manifest digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        expected_bindings = {
            "parent_case_manifest_sha256": _PARENT_CASE_MANIFEST_SHA256,
            "parent_evaluation_plan_sha256": _PARENT_EVALUATION_PLAN_SHA256,
            "parent_evidence_audit_sha256": _PARENT_EVIDENCE_AUDIT_SHA256,
            "parent_evidence_archive_sha256": _PARENT_EVIDENCE_ARCHIVE_SHA256,
            "action_schema_sha256": reconcile_balance_action_schema_sha256(),
            "normalization_policy_sha256": (
                RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint()
            ),
            "prompt_policy_sha256": RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY.fingerprint(),
            "response_schema_sha256": reconcile_balance_response_schema_v2_sha256(),
        }
        for field_name, expected in expected_bindings.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"remediation manifest binding {field_name} drifted")

        historical_ids = tuple(case.eval_case_id for case in self.historical_cases)
        added_ids = tuple(case.eval_case_id for case in self.added_diagnostic_cases)
        all_ids = historical_ids + added_ids
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("remediation case IDs must be unique")
        if len(self.historical_cases) != self.historical_case_count:
            raise ValueError("historical case count drifted")
        if len(self.added_diagnostic_cases) != self.added_diagnostic_case_count:
            raise ValueError("added diagnostic case count drifted")
        if len(all_ids) != self.total_case_count:
            raise ValueError("total remediation case count drifted")

        added_tags = {tag for case in self.added_diagnostic_cases for tag in case.diagnostic_tags}
        if "formatted-integer-normalization" not in added_tags:
            raise ValueError("added diagnostics must cover formatted integer normalization")
        if "key-value-role-binding" not in added_tags:
            raise ValueError("added diagnostics must cover key-value role binding")
        return self


class ActionExtractionRemediationPlan(LocalABCContract):
    """Local-only intervention definition; it never authorizes execution."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    plan_id: Literal["reconcile-balance-extraction-remediation-plan-v2"] = (
        "reconcile-balance-extraction-remediation-plan-v2"
    )
    created_at: datetime
    baseline_classification: Literal[
        ActionExtractionCanaryClassification.FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS
    ] = ActionExtractionCanaryClassification.FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS
    baseline_evidence_audit_sha256: str
    baseline_evidence_archive_sha256: str
    baseline_case_manifest_sha256: str
    baseline_evaluation_plan_sha256: str
    baseline_prompt_policy_sha256: str
    baseline_action_schema_sha256: str
    baseline_case_count: Literal[12] = 12
    baseline_exact_operand_matches: Literal[10] = 10
    baseline_exact_final_answer_matches: Literal[10] = 10
    baseline_semantic_failure_count: Literal[2] = 2
    remediation_manifest_sha256: str
    normalization_policy_sha256: str
    prompt_policy_sha256: str
    response_schema_sha256: str
    action_schema_sha256: str
    controls: tuple[
        Literal[ActionExtractionRemediationControl.DETERMINISTIC_INTEGER_LEXICAL_NORMALIZATION],
        Literal[ActionExtractionRemediationControl.SEMANTIC_ROLE_BOUND_INSTRUCTION],
        Literal[ActionExtractionRemediationControl.ROLE_DESCRIBED_RESPONSE_SCHEMA],
    ] = (
        ActionExtractionRemediationControl.DETERMINISTIC_INTEGER_LEXICAL_NORMALIZATION,
        ActionExtractionRemediationControl.SEMANTIC_ROLE_BOUND_INSTRUCTION,
        ActionExtractionRemediationControl.ROLE_DESCRIBED_RESPONSE_SCHEMA,
    )
    required_failure_families: tuple[
        Literal[ActionExtractionFailureCode.FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED],
        Literal[ActionExtractionFailureCode.KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL],
    ] = (
        ActionExtractionFailureCode.FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED,
        ActionExtractionFailureCode.KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL,
    )
    historical_case_count: Literal[12] = 12
    added_diagnostic_case_count: Literal[4] = 4
    total_case_count: Literal[16] = 16
    thresholds: EvaluationThresholds = EvaluationThresholds()
    complete_suite_required: Literal[True] = True
    failed_case_only_execution_permitted: Literal[False] = False
    hidden_retry_count: Literal[0] = 0
    repair_attempt_count: Literal[0] = 0
    replacement_request_count: Literal[0] = 0
    deterministic_semantic_parser_fallback_permitted: Literal[False] = False
    direct_model_arithmetic_fallback_permitted: Literal[False] = False
    model_upgrade_permitted: Literal[False] = False
    prompt_change_is_versioned: Literal[True] = True
    source_normalization_is_versioned: Literal[True] = True
    response_schema_change_is_versioned: Literal[True] = True
    cache_measurement_in_scope: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    new_authorization_issued: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    external_spend: Literal[0] = 0
    customer_data_used: Literal[False] = False
    next_gate: Literal["bounded_action_extraction_v2_authorization_review"] = (
        "bounded_action_extraction_v2_authorization_review"
    )

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value

    @field_validator(
        "baseline_evidence_audit_sha256",
        "baseline_evidence_archive_sha256",
        "baseline_case_manifest_sha256",
        "baseline_evaluation_plan_sha256",
        "baseline_prompt_policy_sha256",
        "baseline_action_schema_sha256",
        "remediation_manifest_sha256",
        "normalization_policy_sha256",
        "prompt_policy_sha256",
        "response_schema_sha256",
        "action_schema_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("remediation plan digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        expected_bindings = {
            "baseline_evidence_audit_sha256": _PARENT_EVIDENCE_AUDIT_SHA256,
            "baseline_evidence_archive_sha256": _PARENT_EVIDENCE_ARCHIVE_SHA256,
            "baseline_case_manifest_sha256": _PARENT_CASE_MANIFEST_SHA256,
            "baseline_evaluation_plan_sha256": _PARENT_EVALUATION_PLAN_SHA256,
            "baseline_prompt_policy_sha256": _PARENT_PROMPT_POLICY_SHA256,
            "baseline_action_schema_sha256": _PARENT_ACTION_SCHEMA_SHA256,
            "normalization_policy_sha256": (
                RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint()
            ),
            "prompt_policy_sha256": RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY.fingerprint(),
            "response_schema_sha256": reconcile_balance_response_schema_v2_sha256(),
            "action_schema_sha256": reconcile_balance_action_schema_sha256(),
        }
        for field_name, expected in expected_bindings.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"remediation plan binding {field_name} drifted")
        if self.total_case_count != self.historical_case_count + self.added_diagnostic_case_count:
            raise ValueError("remediation plan case counts do not reconcile")
        return self


class ActionExtractionRemediationPackage(LocalABCContract):
    """Cross-file binding for baseline and remediation assets."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    parent_manifest: ReconcileBalanceExtractionManifest
    parent_plan: ActionExtractionEvaluationPlan
    remediation_manifest: ActionExtractionRemediationManifest
    remediation_plan: ActionExtractionRemediationPlan

    @model_validator(mode="after")
    def validate_package(self) -> Self:
        if self.parent_manifest.fingerprint() != _PARENT_CASE_MANIFEST_SHA256:
            raise ValueError("parent case manifest fingerprint drifted")
        if self.parent_plan.fingerprint() != _PARENT_EVALUATION_PLAN_SHA256:
            raise ValueError("parent evaluation plan fingerprint drifted")
        if self.parent_plan.manifest_sha256 != self.parent_manifest.fingerprint():
            raise ValueError("parent evaluation plan no longer binds its case manifest")
        if (
            self.remediation_manifest.parent_case_manifest_sha256
            != self.parent_manifest.fingerprint()
        ):
            raise ValueError("remediation manifest must bind the exact parent manifest")
        if tuple(
            case.canonical_json() for case in self.remediation_manifest.historical_cases
        ) != tuple(case.canonical_json() for case in self.parent_manifest.accepted_cases):
            raise ValueError("all historical cases must be preserved exactly and in order")
        if self.remediation_plan.remediation_manifest_sha256 != (
            self.remediation_manifest.fingerprint()
        ):
            raise ValueError("remediation plan must bind the exact remediation manifest")
        return self


def _canonical_json_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return _sha256_text(payload)


def _normalize_currency_integer(match: re.Match[str]) -> str:
    return match.group("number").replace(",", "")


def _normalize_grouped_integer(match: re.Match[str]) -> str:
    return match.group("number").replace(",", "")


def normalize_reconcile_balance_source_text(source_text: str) -> NormalizedExtractionInput:
    """Normalize integer formatting only; never infer or assign semantic fields."""

    if not source_text.strip():
        raise ValueError("source text must not be empty")
    currency_normalized, currency_count = _CURRENCY_INTEGER_PATTERN.subn(
        _normalize_currency_integer,
        source_text,
    )
    normalized, grouped_count = _GROUPED_INTEGER_PATTERN.subn(
        _normalize_grouped_integer,
        currency_normalized,
    )
    return NormalizedExtractionInput(
        policy_sha256=RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint(),
        source_text=source_text,
        normalized_text=normalized,
        source_text_sha256=_sha256_text(source_text),
        normalized_text_sha256=_sha256_text(normalized),
        source_character_count=len(source_text),
        normalized_character_count=len(normalized),
        currency_integer_normalization_count=currency_count,
        grouped_integer_normalization_count=grouped_count,
        changed=source_text != normalized,
    )


def build_reconcile_balance_extraction_response_format_v2() -> dict[str, Any]:
    """Return a role-described schema while preserving the v1 action contract."""

    schema = copy.deepcopy(ReconcileBalanceAction.model_json_schema())
    schema["description"] = (
        "Extract the current-turn reconciliation action. Bind each integer by its semantic "
        "field label; line order and numeric magnitude must not change field identity."
    )
    properties = cast(dict[str, dict[str, Any]], schema["properties"])
    properties["opening_balance"]["description"] = (
        "Current-turn opening balance only. Do not use credits, debits, metadata, or prior-turn "
        "values. Currency symbols and grouping commas are formatting, not digits to discard."
    )
    properties["credits"]["description"] = (
        "Current-turn credits only. Never bind a debit value here, regardless of line order or "
        "numeric magnitude."
    )
    properties["debits"]["description"] = (
        "Current-turn debits only. Never bind a credit value here, regardless of line order or "
        "numeric magnitude."
    )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "reconcile-balance-action-v2",
            "schema": schema,
        },
    }


def reconcile_balance_response_schema_v2_sha256() -> str:
    """Hash the role-described response format used by the remediation candidate."""

    return _canonical_json_sha256(build_reconcile_balance_extraction_response_format_v2())


RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY = ActionExtractionRemediationPromptPolicy(
    stable_instruction_sha256=_sha256_text(_STABLE_INSTRUCTION_V2),
    stable_instruction_character_count=len(_STABLE_INSTRUCTION_V2),
    source_normalization_policy_sha256=(
        RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint()
    ),
    response_schema_sha256=reconcile_balance_response_schema_v2_sha256(),
    action_schema_sha256=reconcile_balance_action_schema_sha256(),
)


def render_reconcile_balance_extraction_prompt_v2(
    case: ReconcileBalanceExtractionCase,
) -> str:
    """Render the v2 prompt after deterministic lexical normalization."""

    normalized = normalize_reconcile_balance_source_text(case.user_prompt)
    return f"{_STABLE_INSTRUCTION_V2}\nSYNTHETIC CASE:\n{normalized.normalized_text}\n"


def build_remediated_extraction_prompt_identity(
    case: ReconcileBalanceExtractionCase,
) -> RemediatedExtractionPromptIdentity:
    """Build a hash-only identity for normalization and rendered prompt lineage."""

    normalized = normalize_reconcile_balance_source_text(case.user_prompt)
    rendered = render_reconcile_balance_extraction_prompt_v2(case)
    return RemediatedExtractionPromptIdentity(
        prompt_policy_sha256=RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY.fingerprint(),
        normalization_policy_sha256=(RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint()),
        response_schema_sha256=reconcile_balance_response_schema_v2_sha256(),
        source_prompt_sha256=case.prompt_sha256,
        source_prompt_character_count=len(case.user_prompt),
        normalized_prompt_sha256=normalized.normalized_text_sha256,
        normalized_prompt_character_count=normalized.normalized_character_count,
        rendered_prompt_sha256=_sha256_text(rendered),
        rendered_prompt_character_count=len(rendered),
        currency_integer_normalization_count=normalized.currency_integer_normalization_count,
        grouped_integer_normalization_count=normalized.grouped_integer_normalization_count,
    )


def load_action_extraction_remediation_manifest(
    path: Path,
) -> ActionExtractionRemediationManifest:
    """Load the immutable v2 remediation case constitution."""

    return ActionExtractionRemediationManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_action_extraction_remediation_plan(
    path: Path,
) -> ActionExtractionRemediationPlan:
    """Load the local-only remediation plan without granting execution authority."""

    return ActionExtractionRemediationPlan.model_validate_json(path.read_text(encoding="utf-8"))


def load_action_extraction_remediation_package(
    *,
    parent_manifest_path: Path,
    parent_plan_path: Path,
    remediation_manifest_path: Path,
    remediation_plan_path: Path,
) -> ActionExtractionRemediationPackage:
    """Load and cross-validate baseline and remediation artifacts."""

    parent_manifest = load_reconcile_balance_extraction_manifest(parent_manifest_path)
    parent_plan = load_action_extraction_evaluation_plan(parent_plan_path)
    remediation_manifest = load_action_extraction_remediation_manifest(remediation_manifest_path)
    remediation_plan = load_action_extraction_remediation_plan(remediation_plan_path)
    return ActionExtractionRemediationPackage(
        parent_manifest=parent_manifest,
        parent_plan=parent_plan,
        remediation_manifest=remediation_manifest,
        remediation_plan=remediation_plan,
    )
