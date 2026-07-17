"""Local-only hardening for action-extraction traceability and cleanup semantics."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.action_extraction_eval import (
    ActionExtractionCaseScore,
    ActionExtractionPromptIdentity,
    ReconcileBalanceExtractionCase,
    evaluate_reconcile_balance_extraction,
)
from auragateway.local_abc.action_extraction_remediation import (
    RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY,
    build_remediated_extraction_prompt_identity,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_MERGE_COMMIT: Final = "fe25c0869f62624247cc12bb97c5185586845f22"
_SOURCE_AUDIT_SHA256: Final = "a6a1031d85997d8b13b521866d580ce468579cfbb8d731180820fdcc5dd0be79"
_SOURCE_CERTIFICATE_MARKDOWN_SHA256: Final = (
    "8c60ed9d47bc20e3e2f90edfc72a96b993a4bcb15912b70f8c1de5cedd3bc775"
)
_SOURCE_AUTHORIZATION_CONSUMPTION_SHA256: Final = (
    "51b36a3ac4e6122c2cf9fa9e5132d26e57af101a19714cb4cd60c4c71afdff4f"
)
_LEGACY_SCORE_PROMPT_POLICY_SHA256: Final = (
    "5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"
)


class ActionExtractionCleanupStatus(StrEnum):
    """Terminal cleanup state derived from observed worker evidence."""

    CLEAN = "CLEAN"
    CLEAN_WITH_RUNTIME_WARNINGS = "CLEAN_WITH_RUNTIME_WARNINGS"
    FAILED = "FAILED"


class ActionExtractionCleanupWarningCode(StrEnum):
    """Cleanup warnings that prevent a perfectly clean classification."""

    FORCED_PROCESS_TERMINATION = "FORCED_PROCESS_TERMINATION"
    LEAKED_SEMAPHORE = "LEAKED_SEMAPHORE"
    LEAKED_SHARED_MEMORY = "LEAKED_SHARED_MEMORY"
    SURVIVING_CHILD_PROCESS = "SURVIVING_CHILD_PROCESS"


class ActionExtractionWorkerCleanupObservation(LocalABCContract):
    """Privacy-safe cleanup facts captured after one local worker lifecycle."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    worker_id: Literal["worker_1"] = "worker_1"
    return_code: int | None
    port_closed: bool
    application_shutdown_completed: bool
    signal_path: tuple[Literal["SIGINT", "SIGTERM", "SIGKILL"], ...] = ()
    forced_process_termination_count: int = Field(default=0, ge=0)
    leaked_semaphore_count: int = Field(default=0, ge=0)
    leaked_shared_memory_count: int = Field(default=0, ge=0)
    surviving_child_process_count: int = Field(default=0, ge=0)
    raw_worker_log_retained_in_classification: Literal[False] = False

    @field_validator("signal_path")
    @classmethod
    def validate_signal_path(
        cls,
        value: tuple[Literal["SIGINT", "SIGTERM", "SIGKILL"], ...],
    ) -> tuple[Literal["SIGINT", "SIGTERM", "SIGKILL"], ...]:
        allowed_order = ("SIGINT", "SIGTERM", "SIGKILL")
        if len(value) != len(set(value)):
            raise ValueError("cleanup signal path must not contain duplicates")
        positions = tuple(allowed_order.index(item) for item in value)
        if positions != tuple(sorted(positions)):
            raise ValueError("cleanup signal path must preserve escalation order")
        return value


class ActionExtractionWorkerCleanupDecision(LocalABCContract):
    """Evidence-derived cleanup decision with explicit warning semantics."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    observation: ActionExtractionWorkerCleanupObservation
    status: ActionExtractionCleanupStatus
    warning_codes: tuple[ActionExtractionCleanupWarningCode, ...]
    cleanup_perfect: bool
    terminally_safe: bool
    infrastructure_failure: bool

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        expected = _classify_cleanup_observation(self.observation)
        if self.status is not expected[0]:
            raise ValueError("cleanup status does not follow observed evidence")
        if self.warning_codes != expected[1]:
            raise ValueError("cleanup warnings do not follow observed evidence")
        if self.cleanup_perfect != (self.status is ActionExtractionCleanupStatus.CLEAN):
            raise ValueError("cleanup_perfect must follow cleanup status")
        if self.terminally_safe != (self.status is not ActionExtractionCleanupStatus.FAILED):
            raise ValueError("terminally_safe must follow cleanup status")
        if self.infrastructure_failure != (self.status is ActionExtractionCleanupStatus.FAILED):
            raise ValueError("infrastructure_failure must follow cleanup status")
        return self


class ActionExtractionTraceabilityCorrection(LocalABCContract):
    """Before/after proof that only score prompt identity metadata changed."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    eval_case_id: str
    before_score_sha256: str
    after_score_sha256: str
    before_prompt_policy_sha256: str
    after_prompt_policy_sha256: str
    expected_v2_prompt_policy_sha256: str
    source_prompt_sha256: str
    rendered_prompt_sha256: str
    changed_fields: tuple[Literal["prompt_identity"], ...] = ("prompt_identity",)
    metric_fields_preserved: Literal[True] = True
    model_request_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    authorization_reused: Literal[False] = False

    @field_validator(
        "before_score_sha256",
        "after_score_sha256",
        "before_prompt_policy_sha256",
        "after_prompt_policy_sha256",
        "expected_v2_prompt_policy_sha256",
        "source_prompt_sha256",
        "rendered_prompt_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("traceability correction digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_correction(self) -> Self:
        if self.before_prompt_policy_sha256 != _LEGACY_SCORE_PROMPT_POLICY_SHA256:
            raise ValueError("before identity must preserve the audited legacy policy")
        if self.after_prompt_policy_sha256 != self.expected_v2_prompt_policy_sha256:
            raise ValueError("after identity must bind the active v2 policy")
        if self.after_prompt_policy_sha256 != (
            RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY.fingerprint()
        ):
            raise ValueError("after identity must bind the repository v2 policy")
        if self.before_score_sha256 == self.after_score_sha256:
            raise ValueError("traceability correction must change the score fingerprint")
        return self


class ActionExtractionTraceabilityCorrectionResult(LocalABCContract):
    """Corrected score plus a queryable local-only migration proof."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    score: ActionExtractionCaseScore
    correction: ActionExtractionTraceabilityCorrection

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if self.score.eval_case_id != self.correction.eval_case_id:
            raise ValueError("corrected score and correction report must share case identity")
        if self.score.fingerprint() != self.correction.after_score_sha256:
            raise ValueError("corrected score fingerprint does not match correction report")
        if self.score.prompt_identity.policy_sha256 != self.correction.after_prompt_policy_sha256:
            raise ValueError("corrected score prompt policy does not match correction report")
        return self


class ActionExtractionTraceabilityCleanupHardeningPlan(LocalABCContract):
    """Immutable local-only plan binding the audited findings to their fixes."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    hardening_id: Literal["reconcile-balance-action-extraction-v2-traceability-cleanup-hardening"]
    source_merge_commit: str
    source_evidence_audit_sha256: str
    source_certificate_markdown_sha256: str
    source_authorization_consumption_sha256: str
    audited_findings: tuple[
        Literal["STALE_SCORE_PROMPT_IDENTITY_METADATA"],
        Literal["OVERSTATED_CLEANUP_STATUS"],
    ]
    traceability_intervention: Literal["explicit_executed_prompt_identity_injection"]
    cleanup_intervention: Literal["evidence_derived_three_state_cleanup_classification"]
    legacy_default_behavior_preserved: Literal[True] = True
    consumed_authorization_reused: Literal[False] = False
    model_request_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    new_authorization_issued: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    next_gate: Literal["full_abc_harness_integration_design"] = (
        "full_abc_harness_integration_design"
    )

    @field_validator(
        "source_evidence_audit_sha256",
        "source_certificate_markdown_sha256",
        "source_authorization_consumption_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("hardening plan digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        expected = {
            "source_merge_commit": _SOURCE_MERGE_COMMIT,
            "source_evidence_audit_sha256": _SOURCE_AUDIT_SHA256,
            "source_certificate_markdown_sha256": (_SOURCE_CERTIFICATE_MARKDOWN_SHA256),
            "source_authorization_consumption_sha256": (_SOURCE_AUTHORIZATION_CONSUMPTION_SHA256),
        }
        for field_name, value in expected.items():
            if getattr(self, field_name) != value:
                raise ValueError(f"hardening plan binding {field_name} drifted")
        return self


def build_v2_score_prompt_identity(
    case: ReconcileBalanceExtractionCase,
) -> ActionExtractionPromptIdentity:
    """Adapt the full v2 identity into the score contract without losing execution lineage."""

    identity = build_remediated_extraction_prompt_identity(case)
    return ActionExtractionPromptIdentity(
        policy_sha256=identity.prompt_policy_sha256,
        case_prompt_sha256=identity.source_prompt_sha256,
        case_prompt_character_count=identity.source_prompt_character_count,
        rendered_prompt_sha256=identity.rendered_prompt_sha256,
        rendered_prompt_character_count=identity.rendered_prompt_character_count,
    )


def evaluate_reconcile_balance_extraction_v2(
    *,
    case: ReconcileBalanceExtractionCase,
    output_text: str,
    finish_reason: str | None,
    completion_tokens: int,
) -> ActionExtractionCaseScore:
    """Score one v2 output while binding metadata to the prompt that was executed."""

    return evaluate_reconcile_balance_extraction(
        case=case,
        output_text=output_text,
        finish_reason=finish_reason,
        completion_tokens=completion_tokens,
        prompt_identity=build_v2_score_prompt_identity(case),
    )


def harden_legacy_v2_score_prompt_identity(
    *,
    case: ReconcileBalanceExtractionCase,
    score: ActionExtractionCaseScore,
) -> ActionExtractionTraceabilityCorrectionResult:
    """Correct audited legacy score metadata without changing any measured result field."""

    if score.eval_case_id != case.eval_case_id:
        raise ValueError("score case identity does not match the remediation case")
    if score.expected_action_sha256 != case.expected_action_sha256:
        raise ValueError("score expected-action identity does not match the remediation case")
    if score.prompt_identity.case_prompt_sha256 != case.prompt_sha256:
        raise ValueError("score source-prompt identity does not match the remediation case")
    if score.prompt_identity.policy_sha256 != _LEGACY_SCORE_PROMPT_POLICY_SHA256:
        raise ValueError("only the audited legacy score identity may be migrated")

    corrected_identity = build_v2_score_prompt_identity(case)
    payload = score.model_dump(mode="python")
    payload["prompt_identity"] = corrected_identity
    corrected_score = ActionExtractionCaseScore.model_validate(payload)

    before_metrics = score.model_dump(mode="python", exclude={"prompt_identity"})
    after_metrics = corrected_score.model_dump(mode="python", exclude={"prompt_identity"})
    if before_metrics != after_metrics:
        raise ValueError("score migration changed measured fields")

    correction = ActionExtractionTraceabilityCorrection(
        eval_case_id=case.eval_case_id,
        before_score_sha256=score.fingerprint(),
        after_score_sha256=corrected_score.fingerprint(),
        before_prompt_policy_sha256=score.prompt_identity.policy_sha256,
        after_prompt_policy_sha256=corrected_identity.policy_sha256,
        expected_v2_prompt_policy_sha256=(
            RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY.fingerprint()
        ),
        source_prompt_sha256=corrected_identity.case_prompt_sha256,
        rendered_prompt_sha256=corrected_identity.rendered_prompt_sha256,
    )
    return ActionExtractionTraceabilityCorrectionResult(
        score=corrected_score,
        correction=correction,
    )


def _classify_cleanup_observation(
    observation: ActionExtractionWorkerCleanupObservation,
) -> tuple[
    ActionExtractionCleanupStatus,
    tuple[ActionExtractionCleanupWarningCode, ...],
]:
    warning_codes: list[ActionExtractionCleanupWarningCode] = []
    if observation.forced_process_termination_count > 0 or any(
        signal_name in {"SIGTERM", "SIGKILL"} for signal_name in observation.signal_path
    ):
        warning_codes.append(ActionExtractionCleanupWarningCode.FORCED_PROCESS_TERMINATION)
    if observation.leaked_semaphore_count > 0:
        warning_codes.append(ActionExtractionCleanupWarningCode.LEAKED_SEMAPHORE)
    if observation.leaked_shared_memory_count > 0:
        warning_codes.append(ActionExtractionCleanupWarningCode.LEAKED_SHARED_MEMORY)
    if observation.surviving_child_process_count > 0:
        warning_codes.append(ActionExtractionCleanupWarningCode.SURVIVING_CHILD_PROCESS)

    warnings = tuple(warning_codes)
    hard_failure = (
        observation.return_code != 0
        or not observation.port_closed
        or not observation.application_shutdown_completed
        or observation.surviving_child_process_count > 0
    )
    if hard_failure:
        return ActionExtractionCleanupStatus.FAILED, warnings
    if warnings:
        return ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS, warnings
    return ActionExtractionCleanupStatus.CLEAN, warnings


def classify_action_extraction_worker_cleanup(
    observation: ActionExtractionWorkerCleanupObservation,
) -> ActionExtractionWorkerCleanupDecision:
    """Classify cleanup from facts rather than from port closure alone."""

    status, warnings = _classify_cleanup_observation(observation)
    return ActionExtractionWorkerCleanupDecision(
        observation=observation,
        status=status,
        warning_codes=warnings,
        cleanup_perfect=status is ActionExtractionCleanupStatus.CLEAN,
        terminally_safe=status is not ActionExtractionCleanupStatus.FAILED,
        infrastructure_failure=status is ActionExtractionCleanupStatus.FAILED,
    )


def load_action_extraction_traceability_cleanup_hardening_plan(
    path: Path,
) -> ActionExtractionTraceabilityCleanupHardeningPlan:
    """Load the immutable local-only hardening plan."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("hardening plan must contain one JSON object")
    return ActionExtractionTraceabilityCleanupHardeningPlan.model_validate(
        cast(dict[str, object], payload)
    )
