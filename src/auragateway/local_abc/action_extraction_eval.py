"""Fixed evaluation harness for deterministic reconcile-balance action extraction."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal, Self, cast

from pydantic import Field, StrictInt, field_validator, model_validator

from auragateway.local_abc.arithmetic_action import (
    ActionRealizationError,
    ActionRealizationFailureCode,
    DeterministicCapabilityId,
    ReconcileBalanceAction,
    execute_reconcile_balance,
    realize_deterministic_action,
    reconcile_balance_action_schema_sha256,
    validate_reconcile_balance_payload,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_IMPLEMENTATION_COMMIT: Final[Literal["0e4f761de11c85ccf40d234e93a5b2d974590612"]] = (
    "0e4f761de11c85ccf40d234e93a5b2d974590612"
)
_FAILED_CANARY_AUDIT_SHA256: Final[
    Literal["772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62"]
] = "772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62"
_BASELINE_ARCHIVE_SHA256: Final[
    Literal["38dfb3e727b5234e9db510e0c4735150e5721b479908c69fec4d4c8e004059f1"]
] = "38dfb3e727b5234e9db510e0c4735150e5721b479908c69fec4d4c8e004059f1"
_STABLE_INSTRUCTION = """You are an action extraction component.
Return exactly one JSON object matching the supplied schema.
Extract capability, case identity, turn identity, opening_balance, credits, and debits.
Do not calculate or emit the final reconciliation answer.
Do not add explanations, Markdown, or unrequested fields.
Use only the current synthetic case facts; ignore metadata and historical distractors.
"""
_EXPECTED_METRIC_NAMES: Final = (
    "action_json_valid_rate",
    "action_schema_valid_rate",
    "identity_accuracy",
    "operand_accuracy",
    "execution_success_rate",
    "final_answer_accuracy",
    "first_attempt_task_success_rate",
)


class ExtractionCandidateRejectionCode(StrEnum):
    """Why a proposed prompt is excluded from the executable fixed case set."""

    AMBIGUOUS_GROUND_TRUTH = "ambiguous_ground_truth"
    MISSING_REQUIRED_OPERAND = "missing_required_operand"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    OUT_OF_SCOPE_DOMAIN = "out_of_scope_domain"
    DUPLICATE_CASE = "duplicate_case"
    REFUSAL_CONTRACT_REQUIRED = "refusal_contract_required"


class ExtractionEvaluationFailureCode(StrEnum):
    """Machine-readable evaluation failures separate from action runtime errors."""

    OUTPUT_CONTRACT_FAILED = "OUTPUT_CONTRACT_FAILED"
    CASE_ID_MISMATCH = "CASE_ID_MISMATCH"
    TURN_INDEX_MISMATCH = "TURN_INDEX_MISMATCH"
    OPERAND_MISMATCH = "OPERAND_MISMATCH"
    DETERMINISTIC_EXECUTION_FAILED = "DETERMINISTIC_EXECUTION_FAILED"
    FINAL_ANSWER_MISMATCH = "FINAL_ANSWER_MISMATCH"
    FINISH_REASON_UNEXPECTED = "FINISH_REASON_UNEXPECTED"


class EvaluationGateDecision(StrEnum):
    """Terminal regression-gate decision for one completed fixed evaluation."""

    PASSED = "passed"
    FAILED = "failed"


class BaselineMetricState(StrEnum):
    """Whether a metric was observable in the direct-answer v2.3 baseline."""

    MEASURED = "measured"
    NOT_MEASURED = "not_measured"


class ActionExtractionPromptPolicy(LocalABCContract):
    """Frozen prompt and retention policy for action extraction."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["reconcile-balance-action-extraction-prompt-v1"] = (
        "reconcile-balance-action-extraction-prompt-v1"
    )
    capability: Literal[DeterministicCapabilityId.RECONCILE_BALANCE] = (
        DeterministicCapabilityId.RECONCILE_BALANCE
    )
    stable_instruction_sha256: str
    stable_instruction_character_count: int = Field(ge=1)
    response_format_type: Literal["json_schema"] = "json_schema"
    direct_answer_permitted: Literal[False] = False
    arithmetic_execution_by_model_permitted: Literal[False] = False
    extra_text_permitted: Literal[False] = False
    raw_prompt_retained_in_evidence: Literal[False] = False
    raw_output_retained_in_evidence: Literal[False] = False
    hidden_retries_permitted: Literal[False] = False
    repair_attempts_permitted: Literal[False] = False
    synthetic_data_only: Literal[True] = True

    @field_validator("stable_instruction_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("stable instruction digest must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_instruction_binding(self) -> Self:
        expected_sha = hashlib.sha256(_STABLE_INSTRUCTION.encode("utf-8")).hexdigest()
        if self.stable_instruction_sha256 != expected_sha:
            raise ValueError("prompt policy must bind the frozen instruction")
        if self.stable_instruction_character_count != len(_STABLE_INSTRUCTION):
            raise ValueError("prompt policy character count drifted")
        return self


RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY = ActionExtractionPromptPolicy(
    stable_instruction_sha256=hashlib.sha256(_STABLE_INSTRUCTION.encode("utf-8")).hexdigest(),
    stable_instruction_character_count=len(_STABLE_INSTRUCTION),
)


class ActionExtractionPromptIdentity(LocalABCContract):
    """Hash-only prompt identity without retaining rendered prompt text."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_sha256: str
    case_prompt_sha256: str
    case_prompt_character_count: int = Field(ge=1)
    rendered_prompt_sha256: str
    rendered_prompt_character_count: int = Field(ge=1)
    raw_prompt_retained: Literal[False] = False

    @field_validator("policy_sha256", "case_prompt_sha256", "rendered_prompt_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("prompt identity digests must be lowercase SHA-256")
        return value


class ReconcileBalanceExtractionCase(LocalABCContract):
    """One accepted synthetic prompt with deterministic extraction ground truth."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    eval_case_id: str
    user_prompt: str = Field(min_length=20, max_length=1200)
    prompt_sha256: str
    expected_action: ReconcileBalanceAction
    expected_action_sha256: str
    expected_answer: StrictInt = Field(ge=0)
    diagnostic_tags: tuple[str, ...] = Field(min_length=1)
    accept_reason: str = Field(min_length=20, max_length=320)
    synthetic_data: Literal[True] = True

    @field_validator("eval_case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("eval_case_id must use stable lowercase characters")
        return value

    @field_validator("prompt_sha256", "expected_action_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("case digests must be lowercase SHA-256")
        return value

    @field_validator("diagnostic_tags")
    @classmethod
    def validate_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("diagnostic tags must be unique")
        if any(_ID_PATTERN.fullmatch(tag) is None for tag in value):
            raise ValueError("diagnostic tags must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_ground_truth(self) -> Self:
        prompt_sha = hashlib.sha256(self.user_prompt.encode("utf-8")).hexdigest()
        if self.prompt_sha256 != prompt_sha:
            raise ValueError("case prompt digest drifted")
        if self.expected_action_sha256 != self.expected_action.fingerprint():
            raise ValueError("expected action fingerprint drifted")
        result = execute_reconcile_balance(self.expected_action)
        if result.answer != self.expected_answer:
            raise ValueError("expected answer must match deterministic execution")
        return self


class RejectedExtractionCandidate(LocalABCContract):
    """Candidate prompt deliberately excluded from the executable eval set."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    candidate_id: str
    user_prompt: str = Field(min_length=10, max_length=1200)
    rejection_code: ExtractionCandidateRejectionCode
    reject_reason: str = Field(min_length=24, max_length=360)
    synthetic_data: Literal[True] = True

    @field_validator("candidate_id")
    @classmethod
    def validate_candidate_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("candidate_id must use stable lowercase characters")
        return value


class ReconcileBalanceExtractionManifest(LocalABCContract):
    """Fixed accepted cases plus rejected candidate constitution."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["reconcile-balance-extraction-eval-cases-v1"] = (
        "reconcile-balance-extraction-eval-cases-v1"
    )
    implementation_commit: Literal["0e4f761de11c85ccf40d234e93a5b2d974590612"] = (
        _IMPLEMENTATION_COMMIT
    )
    failed_canary_audit_sha256: Literal[
        "772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62"
    ] = _FAILED_CANARY_AUDIT_SHA256
    capability: Literal[DeterministicCapabilityId.RECONCILE_BALANCE] = (
        DeterministicCapabilityId.RECONCILE_BALANCE
    )
    action_schema_sha256: str
    prompt_policy_sha256: str
    accepted_cases: tuple[ReconcileBalanceExtractionCase, ...] = Field(min_length=10)
    rejected_candidates: tuple[RejectedExtractionCandidate, ...] = Field(min_length=4)
    synthetic_data_only: Literal[True] = True
    raw_prompt_retention_in_evidence_permitted: Literal[False] = False
    raw_output_retention_in_evidence_permitted: Literal[False] = False
    execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False

    @field_validator("action_schema_sha256", "prompt_policy_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        accepted_ids = tuple(case.eval_case_id for case in self.accepted_cases)
        rejected_ids = tuple(case.candidate_id for case in self.rejected_candidates)
        if len(accepted_ids) != len(set(accepted_ids)):
            raise ValueError("accepted eval case IDs must be unique")
        if len(rejected_ids) != len(set(rejected_ids)):
            raise ValueError("rejected candidate IDs must be unique")
        if set(accepted_ids) & set(rejected_ids):
            raise ValueError("accepted and rejected IDs must not overlap")
        if self.action_schema_sha256 != reconcile_balance_action_schema_sha256():
            raise ValueError("manifest action schema binding drifted")
        if self.prompt_policy_sha256 != RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY.fingerprint():
            raise ValueError("manifest prompt policy binding drifted")
        return self


class DirectAnswerBaseline(LocalABCContract):
    """Evidence-bounded baseline from the failed v2.3 direct-answer request."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    baseline_id: Literal["schema-canary-v2-3-payment-turn-one-direct-answer"] = (
        "schema-canary-v2-3-payment-turn-one-direct-answer"
    )
    source_run_id: Literal["auragateway-schema-canary-rerun-v2-bf55bf4de546"]
    source_repository_commit: Literal["5d8170b5f33f9bff07a3f6c0db3f90b5399a1bae"]
    source_evidence_archive_sha256: Literal[
        "38dfb3e727b5234e9db510e0c4735150e5721b479908c69fec4d4c8e004059f1"
    ] = _BASELINE_ARCHIVE_SHA256
    source_audit_sha256: Literal[
        "772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62"
    ] = _FAILED_CANARY_AUDIT_SHA256
    case_id: Literal["payment-reconciliation"] = "payment-reconciliation"
    turn_index: Literal[1] = 1
    expected_answer: Literal[1450] = 1450
    final_answer_match: Literal[False] = False
    first_attempt_task_success: Literal[False] = False
    failure_code: Literal["OUTPUT_ANSWER_MISMATCH"] = "OUTPUT_ANSWER_MISMATCH"
    action_json_valid_state: Literal[BaselineMetricState.NOT_MEASURED] = (
        BaselineMetricState.NOT_MEASURED
    )
    action_schema_valid_state: Literal[BaselineMetricState.NOT_MEASURED] = (
        BaselineMetricState.NOT_MEASURED
    )
    identity_accuracy_state: Literal[BaselineMetricState.NOT_MEASURED] = (
        BaselineMetricState.NOT_MEASURED
    )
    operand_accuracy_state: Literal[BaselineMetricState.NOT_MEASURED] = (
        BaselineMetricState.NOT_MEASURED
    )
    deterministic_execution_state: Literal[BaselineMetricState.NOT_MEASURED] = (
        BaselineMetricState.NOT_MEASURED
    )
    raw_output_retained: Literal[False] = False


class EvaluationThresholds(LocalABCContract):
    """All-or-nothing thresholds for the first bounded extraction canary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    action_json_valid_rate: Decimal = Decimal("1")
    action_schema_valid_rate: Decimal = Decimal("1")
    identity_accuracy: Decimal = Decimal("1")
    operand_accuracy: Decimal = Decimal("1")
    execution_success_rate: Decimal = Decimal("1")
    final_answer_accuracy: Decimal = Decimal("1")
    first_attempt_task_success_rate: Decimal = Decimal("1")

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        for metric_name in _EXPECTED_METRIC_NAMES:
            if getattr(self, metric_name) != Decimal("1"):
                raise ValueError("first bounded extraction thresholds must remain 1.0")
        return self


class ActionExtractionEvaluationPlan(LocalABCContract):
    """Frozen evaluation method without execution authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    plan_id: Literal["reconcile-balance-extraction-eval-plan-v1"] = (
        "reconcile-balance-extraction-eval-plan-v1"
    )
    created_at: datetime
    implementation_commit: Literal["0e4f761de11c85ccf40d234e93a5b2d974590612"] = (
        _IMPLEMENTATION_COMMIT
    )
    manifest_sha256: str
    prompt_policy_sha256: str
    baseline: DirectAnswerBaseline
    intervention: Literal["typed_action_extraction_plus_deterministic_execution"] = (
        "typed_action_extraction_plus_deterministic_execution"
    )
    case_count: int = Field(ge=10)
    thresholds: EvaluationThresholds = EvaluationThresholds()
    permitted_finish_reasons: tuple[Literal["stop"], ...] = ("stop",)
    hidden_retry_count: Literal[0] = 0
    repair_attempt_count: Literal[0] = 0
    replacement_request_count: Literal[0] = 0
    direct_model_arithmetic_fallback_permitted: Literal[False] = False
    raw_prompt_retention_permitted: Literal[False] = False
    raw_output_retention_permitted: Literal[False] = False
    execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    next_gate: Literal["new_bounded_action_extraction_authorization"] = (
        "new_bounded_action_extraction_authorization"
    )

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value

    @field_validator("manifest_sha256", "prompt_policy_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("plan digests must be lowercase SHA-256")
        return value


class ActionExtractionEvaluationPackage(LocalABCContract):
    """Cross-file binding for the fixed case manifest and evaluation plan."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest: ReconcileBalanceExtractionManifest
    plan: ActionExtractionEvaluationPlan

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.plan.manifest_sha256 != self.manifest.fingerprint():
            raise ValueError("evaluation plan must bind the exact manifest")
        if (
            self.plan.prompt_policy_sha256
            != RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY.fingerprint()
        ):
            raise ValueError("evaluation plan must bind the prompt policy")
        if self.plan.implementation_commit != self.manifest.implementation_commit:
            raise ValueError("evaluation plan and manifest implementation commits must match")
        if self.plan.case_count != len(self.manifest.accepted_cases):
            raise ValueError("evaluation plan case count must match the manifest")
        return self


class ActionExtractionCaseScore(LocalABCContract):
    """Metadata-only score for one first-attempt model action output."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    eval_case_id: str
    prompt_identity: ActionExtractionPromptIdentity
    expected_action_sha256: str
    output_text_sha256: str
    output_character_count: int = Field(ge=0)
    finish_reason: str | None = Field(default=None, max_length=80)
    completion_tokens: int = Field(ge=0)
    action_json_valid: bool
    action_schema_valid: bool
    exact_case_id_match: bool
    exact_turn_index_match: bool
    exact_operand_match: bool
    execution_success: bool
    final_answer_match: bool
    first_attempt_task_success: bool
    action_sha256: str | None = None
    result_sha256: str | None = None
    action_failure_code: ActionRealizationFailureCode | None = None
    evaluation_failure_codes: tuple[ExtractionEvaluationFailureCode, ...] = ()
    raw_output_retained: Literal[False] = False
    hidden_retry_count: Literal[0] = 0
    repair_attempt_count: Literal[0] = 0
    replacement_request_count: Literal[0] = 0
    direct_model_arithmetic_fallback_used: Literal[False] = False

    @field_validator("eval_case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("eval_case_id must use stable lowercase characters")
        return value

    @field_validator(
        "expected_action_sha256",
        "output_text_sha256",
        "action_sha256",
        "result_sha256",
    )
    @classmethod
    def validate_optional_digest(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("score digests must be lowercase SHA-256")
        return value

    @field_validator("evaluation_failure_codes")
    @classmethod
    def validate_failure_codes(
        cls,
        value: tuple[ExtractionEvaluationFailureCode, ...],
    ) -> tuple[ExtractionEvaluationFailureCode, ...]:
        if len(value) != len(set(value)):
            raise ValueError("evaluation failure codes must be unique")
        expected = tuple(sorted(value, key=lambda code: code.value))
        if value != expected:
            raise ValueError("evaluation failure codes must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_score_consistency(self) -> Self:
        if not self.action_json_valid and self.action_schema_valid:
            raise ValueError("schema-valid action requires valid JSON")
        if not self.action_schema_valid and any(
            (
                self.exact_case_id_match,
                self.exact_turn_index_match,
                self.exact_operand_match,
                self.execution_success,
                self.final_answer_match,
            )
        ):
            raise ValueError("invalid action schema cannot pass dependent checks")
        if self.action_schema_valid != (self.action_sha256 is not None):
            raise ValueError("valid action schema requires an action fingerprint")
        if self.execution_success != (self.result_sha256 is not None):
            raise ValueError("successful execution requires a result fingerprint")
        expected_success = all(
            (
                self.action_json_valid,
                self.action_schema_valid,
                self.exact_case_id_match,
                self.exact_turn_index_match,
                self.exact_operand_match,
                self.execution_success,
                self.final_answer_match,
                self.finish_reason == "stop",
                not self.evaluation_failure_codes,
                self.action_failure_code is None,
            )
        )
        if self.first_attempt_task_success != expected_success:
            raise ValueError("first-attempt success must match all fixed gates")
        if self.first_attempt_task_success and self.evaluation_failure_codes:
            raise ValueError("passing score cannot retain evaluation failures")
        return self


class MetricSummary(LocalABCContract):
    """Exact count and rate for one fixed metric."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    passed_count: int = Field(ge=0)
    total_count: int = Field(ge=1)
    rate: Decimal = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_rate(self) -> Self:
        expected = Decimal(self.passed_count) / Decimal(self.total_count)
        if self.rate != expected:
            raise ValueError("metric rate must equal passed divided by total")
        return self


class ActionExtractionEvaluationReport(LocalABCContract):
    """Before/after report with separate extraction, execution, and answer metrics."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    report_id: str
    created_at: datetime
    plan_sha256: str
    manifest_sha256: str
    baseline: DirectAnswerBaseline
    scores: tuple[ActionExtractionCaseScore, ...]
    action_json_valid: MetricSummary
    action_schema_valid: MetricSummary
    identity_accuracy: MetricSummary
    operand_accuracy: MetricSummary
    execution_success: MetricSummary
    final_answer_accuracy: MetricSummary
    first_attempt_task_success: MetricSummary
    gate_decision: EvaluationGateDecision
    failed_case_ids: tuple[str, ...]
    failure_code_counts: dict[str, int]
    baseline_comparable_metrics: tuple[
        Literal["final_answer_accuracy"],
        Literal["first_attempt_task_success_rate"],
    ] = ("final_answer_accuracy", "first_attempt_task_success_rate")
    extraction_metrics_have_baseline: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False

    @field_validator("report_id")
    @classmethod
    def validate_report_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("report_id must use stable lowercase characters")
        return value

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value

    @field_validator("plan_sha256", "manifest_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("report digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_report(self) -> Self:
        expected_metrics = {
            "action_json_valid": _metric_summary(
                tuple(score.action_json_valid for score in self.scores)
            ),
            "action_schema_valid": _metric_summary(
                tuple(score.action_schema_valid for score in self.scores)
            ),
            "identity_accuracy": _metric_summary(
                tuple(
                    score.exact_case_id_match and score.exact_turn_index_match
                    for score in self.scores
                )
            ),
            "operand_accuracy": _metric_summary(
                tuple(score.exact_operand_match for score in self.scores)
            ),
            "execution_success": _metric_summary(
                tuple(score.execution_success for score in self.scores)
            ),
            "final_answer_accuracy": _metric_summary(
                tuple(score.final_answer_match for score in self.scores)
            ),
            "first_attempt_task_success": _metric_summary(
                tuple(score.first_attempt_task_success for score in self.scores)
            ),
        }
        for field_name, expected in expected_metrics.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"report metric {field_name} drifted from case scores")

        failed_ids = tuple(
            score.eval_case_id for score in self.scores if not score.first_attempt_task_success
        )
        if self.failed_case_ids != failed_ids:
            raise ValueError("failed case IDs must preserve score order")

        expected_counter: Counter[str] = Counter()
        for score in self.scores:
            if score.action_failure_code is not None:
                expected_counter[score.action_failure_code.value] += 1
            expected_counter.update(code.value for code in score.evaluation_failure_codes)
        if self.failure_code_counts != dict(sorted(expected_counter.items())):
            raise ValueError("failure-code counts must match case scores")

        all_metrics_passed = all(
            summary.rate == Decimal("1") for summary in expected_metrics.values()
        )
        expected_decision = (
            EvaluationGateDecision.PASSED
            if all_metrics_passed and not failed_ids
            else EvaluationGateDecision.FAILED
        )
        if self.gate_decision is not expected_decision:
            raise ValueError("gate decision must follow all fixed metrics")
        return self


def build_reconcile_balance_extraction_response_format() -> dict[str, Any]:
    """Return the exact JSON Schema response format for model action extraction."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "reconcile-balance-action-v1",
            "schema": ReconcileBalanceAction.model_json_schema(),
        },
    }


def render_reconcile_balance_extraction_prompt(
    case: ReconcileBalanceExtractionCase,
) -> str:
    """Render the transient synthetic prompt without writing it to evidence."""

    return f"{_STABLE_INSTRUCTION}\nSYNTHETIC CASE:\n{case.user_prompt}\n"


def build_action_extraction_prompt_identity(
    case: ReconcileBalanceExtractionCase,
) -> ActionExtractionPromptIdentity:
    """Build a hash-only identity for the transient rendered prompt."""

    rendered = render_reconcile_balance_extraction_prompt(case)
    return ActionExtractionPromptIdentity(
        policy_sha256=RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY.fingerprint(),
        case_prompt_sha256=case.prompt_sha256,
        case_prompt_character_count=len(case.user_prompt),
        rendered_prompt_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        rendered_prompt_character_count=len(rendered),
    )


def _load_json_mapping(output_text: str) -> tuple[dict[str, object] | None, bool]:
    if not output_text.strip():
        return None, False
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError:
        return None, False
    if not isinstance(parsed, dict):
        return None, True
    return cast(dict[str, object], parsed), True


def _parse_action_for_evaluation(
    output_text: str,
) -> tuple[ReconcileBalanceAction | None, bool, ActionRealizationFailureCode | None]:
    payload, json_valid = _load_json_mapping(output_text)
    if payload is None:
        if not output_text.strip():
            return None, json_valid, ActionRealizationFailureCode.ACTION_OUTPUT_MISSING
        if json_valid:
            return None, True, ActionRealizationFailureCode.ACTION_SCHEMA_INVALID
        return None, False, ActionRealizationFailureCode.ACTION_JSON_INVALID
    try:
        action = validate_reconcile_balance_payload(payload)
    except ActionRealizationError as error:
        return None, True, error.code
    return action, True, None


def _operand_tuple(action: ReconcileBalanceAction) -> tuple[int, int, int]:
    return action.opening_balance, action.credits, action.debits


def evaluate_reconcile_balance_extraction(
    *,
    case: ReconcileBalanceExtractionCase,
    output_text: str,
    finish_reason: str | None,
    completion_tokens: int,
) -> ActionExtractionCaseScore:
    """Score one first-attempt output without retries or raw-output retention."""

    action, json_valid, action_failure = _parse_action_for_evaluation(output_text)
    failure_codes: set[ExtractionEvaluationFailureCode] = set()
    action_schema_valid = action is not None
    exact_case_id_match = False
    exact_turn_index_match = False
    exact_operand_match = False
    execution_success = False
    final_answer_match = False
    action_sha256: str | None = None
    result_sha256: str | None = None

    if action is None:
        failure_codes.add(ExtractionEvaluationFailureCode.OUTPUT_CONTRACT_FAILED)
    else:
        action_sha256 = action.fingerprint()
        exact_case_id_match = action.case_id == case.expected_action.case_id
        exact_turn_index_match = action.turn_index == case.expected_action.turn_index
        exact_operand_match = _operand_tuple(action) == _operand_tuple(case.expected_action)
        if not exact_case_id_match:
            failure_codes.add(ExtractionEvaluationFailureCode.CASE_ID_MISMATCH)
        if not exact_turn_index_match:
            failure_codes.add(ExtractionEvaluationFailureCode.TURN_INDEX_MISMATCH)
        if not exact_operand_match:
            failure_codes.add(ExtractionEvaluationFailureCode.OPERAND_MISMATCH)
        try:
            result = realize_deterministic_action(action)
        except ActionRealizationError as error:
            action_failure = error.code
            failure_codes.add(ExtractionEvaluationFailureCode.DETERMINISTIC_EXECUTION_FAILED)
        else:
            execution_success = True
            result_sha256 = result.fingerprint()
            final_answer_match = result.answer == case.expected_answer
            if not final_answer_match:
                failure_codes.add(ExtractionEvaluationFailureCode.FINAL_ANSWER_MISMATCH)

    if finish_reason != "stop":
        failure_codes.add(ExtractionEvaluationFailureCode.FINISH_REASON_UNEXPECTED)

    ordered_failures = tuple(sorted(failure_codes, key=lambda code: code.value))
    first_attempt_success = (
        json_valid
        and action_schema_valid
        and exact_case_id_match
        and exact_turn_index_match
        and exact_operand_match
        and execution_success
        and final_answer_match
        and finish_reason == "stop"
        and not ordered_failures
        and action_failure is None
    )
    return ActionExtractionCaseScore(
        eval_case_id=case.eval_case_id,
        prompt_identity=build_action_extraction_prompt_identity(case),
        expected_action_sha256=case.expected_action_sha256,
        output_text_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        output_character_count=len(output_text),
        finish_reason=finish_reason,
        completion_tokens=completion_tokens,
        action_json_valid=json_valid,
        action_schema_valid=action_schema_valid,
        exact_case_id_match=exact_case_id_match,
        exact_turn_index_match=exact_turn_index_match,
        exact_operand_match=exact_operand_match,
        execution_success=execution_success,
        final_answer_match=final_answer_match,
        first_attempt_task_success=first_attempt_success,
        action_sha256=action_sha256,
        result_sha256=result_sha256,
        action_failure_code=action_failure,
        evaluation_failure_codes=ordered_failures,
    )


def _metric_summary(values: tuple[bool, ...]) -> MetricSummary:
    return MetricSummary(
        passed_count=sum(values),
        total_count=len(values),
        rate=Decimal(sum(values)) / Decimal(len(values)),
    )


def build_action_extraction_evaluation_report(
    *,
    report_id: str,
    created_at: datetime,
    plan: ActionExtractionEvaluationPlan,
    manifest: ReconcileBalanceExtractionManifest,
    scores: tuple[ActionExtractionCaseScore, ...],
) -> ActionExtractionEvaluationReport:
    """Build the fixed before/after report and all-or-nothing regression gate."""

    if plan.manifest_sha256 != manifest.fingerprint():
        raise ValueError("evaluation plan must bind the exact manifest")
    if plan.prompt_policy_sha256 != RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY.fingerprint():
        raise ValueError("evaluation plan must bind the prompt policy")
    if plan.case_count != len(manifest.accepted_cases):
        raise ValueError("evaluation plan case count must match the manifest")
    expected_ids = tuple(case.eval_case_id for case in manifest.accepted_cases)
    observed_ids = tuple(score.eval_case_id for score in scores)
    if observed_ids != expected_ids:
        raise ValueError("scores must cover the exact fixed case order")

    action_json = _metric_summary(tuple(score.action_json_valid for score in scores))
    action_schema = _metric_summary(tuple(score.action_schema_valid for score in scores))
    identity = _metric_summary(
        tuple(score.exact_case_id_match and score.exact_turn_index_match for score in scores)
    )
    operands = _metric_summary(tuple(score.exact_operand_match for score in scores))
    execution = _metric_summary(tuple(score.execution_success for score in scores))
    final_answer = _metric_summary(tuple(score.final_answer_match for score in scores))
    first_attempt = _metric_summary(tuple(score.first_attempt_task_success for score in scores))

    rate_by_name = {
        "action_json_valid_rate": action_json.rate,
        "action_schema_valid_rate": action_schema.rate,
        "identity_accuracy": identity.rate,
        "operand_accuracy": operands.rate,
        "execution_success_rate": execution.rate,
        "final_answer_accuracy": final_answer.rate,
        "first_attempt_task_success_rate": first_attempt.rate,
    }
    thresholds_passed = all(
        rate_by_name[name] >= getattr(plan.thresholds, name) for name in _EXPECTED_METRIC_NAMES
    )
    failed_case_ids = tuple(
        score.eval_case_id for score in scores if not score.first_attempt_task_success
    )
    failure_counter: Counter[str] = Counter()
    for score in scores:
        if score.action_failure_code is not None:
            failure_counter[score.action_failure_code.value] += 1
        failure_counter.update(code.value for code in score.evaluation_failure_codes)

    return ActionExtractionEvaluationReport(
        report_id=report_id,
        created_at=created_at,
        plan_sha256=plan.fingerprint(),
        manifest_sha256=manifest.fingerprint(),
        baseline=plan.baseline,
        scores=scores,
        action_json_valid=action_json,
        action_schema_valid=action_schema,
        identity_accuracy=identity,
        operand_accuracy=operands,
        execution_success=execution,
        final_answer_accuracy=final_answer,
        first_attempt_task_success=first_attempt,
        gate_decision=(
            EvaluationGateDecision.PASSED
            if thresholds_passed and not failed_case_ids
            else EvaluationGateDecision.FAILED
        ),
        failed_case_ids=failed_case_ids,
        failure_code_counts=dict(sorted(failure_counter.items())),
    )


def load_reconcile_balance_extraction_manifest(
    path: Path,
) -> ReconcileBalanceExtractionManifest:
    """Load and validate the fixed extraction case constitution."""

    return ReconcileBalanceExtractionManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_action_extraction_evaluation_plan(
    path: Path,
) -> ActionExtractionEvaluationPlan:
    """Load and validate the non-executable fixed evaluation plan."""

    return ActionExtractionEvaluationPlan.model_validate_json(path.read_text(encoding="utf-8"))


def load_action_extraction_evaluation_package(
    *,
    manifest_path: Path,
    plan_path: Path,
) -> ActionExtractionEvaluationPackage:
    """Load and cross-validate the fixed manifest and non-executable plan."""

    return ActionExtractionEvaluationPackage(
        manifest=load_reconcile_balance_extraction_manifest(manifest_path),
        plan=load_action_extraction_evaluation_plan(plan_path),
    )
