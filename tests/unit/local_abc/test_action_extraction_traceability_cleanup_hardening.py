"""Regression tests for local action-extraction traceability and cleanup hardening."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_eval import (
    ActionExtractionCaseScore,
    ReconcileBalanceExtractionCase,
    evaluate_reconcile_balance_extraction,
)
from auragateway.local_abc.action_extraction_remediation import (
    RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY,
    load_action_extraction_remediation_manifest,
)
from auragateway.local_abc.action_extraction_traceability_cleanup_hardening import (
    ActionExtractionCleanupStatus,
    ActionExtractionCleanupWarningCode,
    ActionExtractionWorkerCleanupDecision,
    ActionExtractionWorkerCleanupObservation,
    build_v2_score_prompt_identity,
    classify_action_extraction_worker_cleanup,
    evaluate_reconcile_balance_extraction_v2,
    harden_legacy_v2_score_prompt_identity,
    load_action_extraction_traceability_cleanup_hardening_plan,
)

ROOT = Path(__file__).resolve().parents[3]
REMEDIATION_MANIFEST_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_remediation_cases_v2.json"
)
HARDENING_PLAN_PATH = (
    ROOT / "benchmarks/local_abc/"
    "reconcile_balance_extraction_traceability_cleanup_hardening_v1.json"
)
LEGACY_PROMPT_POLICY_SHA256 = "5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"
V2_PROMPT_POLICY_SHA256 = "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"


def _case(
    case_id: str = "formatted-currency-values",
) -> ReconcileBalanceExtractionCase:
    manifest = load_action_extraction_remediation_manifest(REMEDIATION_MANIFEST_PATH)
    cases = (*manifest.historical_cases, *manifest.added_diagnostic_cases)
    return next(case for case in cases if case.eval_case_id == case_id)


def _output_text(case_id: str = "formatted-currency-values") -> str:
    return _case(case_id).expected_action.model_dump_json()


def _legacy_score(
    case_id: str = "formatted-currency-values",
) -> ActionExtractionCaseScore:
    case = _case(case_id)
    return evaluate_reconcile_balance_extraction(
        case=case,
        output_text=case.expected_action.model_dump_json(),
        finish_reason="stop",
        completion_tokens=32,
    )


def test_legacy_default_scoring_behavior_remains_compatible() -> None:
    score = _legacy_score()

    assert score.first_attempt_task_success is True
    assert score.prompt_identity.policy_sha256 == LEGACY_PROMPT_POLICY_SHA256


def test_v2_score_identity_binds_the_executed_remediation_prompt() -> None:
    case = _case()
    identity = build_v2_score_prompt_identity(case)

    assert identity.policy_sha256 == V2_PROMPT_POLICY_SHA256
    assert identity.policy_sha256 == RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY.fingerprint()
    assert identity.case_prompt_sha256 == case.prompt_sha256
    assert identity.rendered_prompt_sha256 != _legacy_score().prompt_identity.rendered_prompt_sha256
    assert identity.raw_prompt_retained is False


def test_v2_evaluator_propagates_the_active_prompt_identity() -> None:
    case = _case()
    score = evaluate_reconcile_balance_extraction_v2(
        case=case,
        output_text=case.expected_action.model_dump_json(),
        finish_reason="stop",
        completion_tokens=32,
    )

    assert score.first_attempt_task_success is True
    assert score.prompt_identity == build_v2_score_prompt_identity(case)
    assert score.prompt_identity.policy_sha256 == V2_PROMPT_POLICY_SHA256


def test_explicit_identity_seam_is_honored_by_the_base_evaluator() -> None:
    case = _case("key-value-layout")
    identity = build_v2_score_prompt_identity(case)
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text=case.expected_action.model_dump_json(),
        finish_reason="stop",
        completion_tokens=24,
        prompt_identity=identity,
    )

    assert score.prompt_identity == identity
    assert score.first_attempt_task_success is True


def test_explicit_identity_seam_rejects_a_different_case_identity() -> None:
    case = _case("formatted-currency-values")
    wrong_identity = build_v2_score_prompt_identity(_case("key-value-layout"))

    with pytest.raises(ValueError, match="evaluated case prompt"):
        evaluate_reconcile_balance_extraction(
            case=case,
            output_text=case.expected_action.model_dump_json(),
            finish_reason="stop",
            completion_tokens=32,
            prompt_identity=wrong_identity,
        )


def test_legacy_score_migration_changes_only_prompt_identity() -> None:
    case = _case()
    legacy = _legacy_score()
    result = harden_legacy_v2_score_prompt_identity(case=case, score=legacy)

    before = legacy.model_dump(mode="python", exclude={"prompt_identity"})
    after = result.score.model_dump(mode="python", exclude={"prompt_identity"})

    assert before == after
    assert result.score.prompt_identity.policy_sha256 == V2_PROMPT_POLICY_SHA256
    assert result.correction.changed_fields == ("prompt_identity",)
    assert result.correction.metric_fields_preserved is True
    assert result.correction.model_request_performed is False
    assert result.correction.authorization_reused is False


def test_legacy_score_migration_preserves_failed_metrics() -> None:
    case = _case()
    legacy = evaluate_reconcile_balance_extraction(
        case=case,
        output_text="{}",
        finish_reason="stop",
        completion_tokens=2,
    )
    result = harden_legacy_v2_score_prompt_identity(case=case, score=legacy)

    assert legacy.first_attempt_task_success is False
    assert result.score.first_attempt_task_success is False
    assert result.score.evaluation_failure_codes == legacy.evaluation_failure_codes
    assert result.score.action_failure_code == legacy.action_failure_code


def test_migration_rejects_wrong_case_binding() -> None:
    with pytest.raises(ValueError, match="case identity"):
        harden_legacy_v2_score_prompt_identity(
            case=_case("key-value-layout"),
            score=_legacy_score("formatted-currency-values"),
        )


def test_migration_rejects_an_already_hardened_score() -> None:
    case = _case()
    score = evaluate_reconcile_balance_extraction_v2(
        case=case,
        output_text=_output_text(),
        finish_reason="stop",
        completion_tokens=32,
    )

    with pytest.raises(ValueError, match="audited legacy score identity"):
        harden_legacy_v2_score_prompt_identity(case=case, score=score)


def test_clean_shutdown_requires_every_cleanliness_invariant() -> None:
    decision = classify_action_extraction_worker_cleanup(
        ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGINT",),
        )
    )

    assert decision.status is ActionExtractionCleanupStatus.CLEAN
    assert decision.warning_codes == ()
    assert decision.cleanup_perfect is True
    assert decision.terminally_safe is True
    assert decision.infrastructure_failure is False


def test_forced_internal_termination_is_warning_qualified() -> None:
    decision = classify_action_extraction_worker_cleanup(
        ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGINT",),
            forced_process_termination_count=1,
        )
    )

    assert decision.status is ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS
    assert decision.warning_codes == (
        ActionExtractionCleanupWarningCode.FORCED_PROCESS_TERMINATION,
    )
    assert decision.cleanup_perfect is False
    assert decision.terminally_safe is True


def test_sigterm_escalation_is_warning_qualified_even_with_zero_return_code() -> None:
    decision = classify_action_extraction_worker_cleanup(
        ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGINT", "SIGTERM"),
        )
    )

    assert decision.status is ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS
    assert ActionExtractionCleanupWarningCode.FORCED_PROCESS_TERMINATION in (decision.warning_codes)


def test_leaked_semaphore_is_warning_qualified() -> None:
    decision = classify_action_extraction_worker_cleanup(
        ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGINT",),
            leaked_semaphore_count=1,
        )
    )

    assert decision.status is ActionExtractionCleanupStatus.CLEAN_WITH_RUNTIME_WARNINGS
    assert decision.warning_codes == (ActionExtractionCleanupWarningCode.LEAKED_SEMAPHORE,)


def test_open_port_is_a_cleanup_failure() -> None:
    decision = classify_action_extraction_worker_cleanup(
        ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=False,
            application_shutdown_completed=True,
            signal_path=("SIGINT",),
        )
    )

    assert decision.status is ActionExtractionCleanupStatus.FAILED
    assert decision.infrastructure_failure is True
    assert decision.terminally_safe is False


def test_nonzero_return_code_is_a_cleanup_failure() -> None:
    decision = classify_action_extraction_worker_cleanup(
        ActionExtractionWorkerCleanupObservation(
            return_code=-9,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGINT", "SIGTERM", "SIGKILL"),
        )
    )

    assert decision.status is ActionExtractionCleanupStatus.FAILED
    assert decision.infrastructure_failure is True


def test_missing_application_shutdown_is_a_cleanup_failure() -> None:
    decision = classify_action_extraction_worker_cleanup(
        ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=False,
            signal_path=("SIGINT",),
        )
    )

    assert decision.status is ActionExtractionCleanupStatus.FAILED


def test_surviving_child_process_is_a_cleanup_failure_and_warning() -> None:
    decision = classify_action_extraction_worker_cleanup(
        ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGINT",),
            surviving_child_process_count=1,
        )
    )

    assert decision.status is ActionExtractionCleanupStatus.FAILED
    assert ActionExtractionCleanupWarningCode.SURVIVING_CHILD_PROCESS in (decision.warning_codes)


def test_cleanup_signal_order_is_fail_closed() -> None:
    with pytest.raises(ValidationError, match="escalation order"):
        ActionExtractionWorkerCleanupObservation(
            return_code=0,
            port_closed=True,
            application_shutdown_completed=True,
            signal_path=("SIGTERM", "SIGINT"),
        )


def test_cleanup_decision_cannot_overstate_observation() -> None:
    observation = ActionExtractionWorkerCleanupObservation(
        return_code=0,
        port_closed=True,
        application_shutdown_completed=True,
        leaked_semaphore_count=1,
    )

    with pytest.raises(ValidationError, match="status does not follow"):
        ActionExtractionWorkerCleanupDecision(
            observation=observation,
            status=ActionExtractionCleanupStatus.CLEAN,
            warning_codes=(),
            cleanup_perfect=True,
            terminally_safe=True,
            infrastructure_failure=False,
        )


def test_hardening_plan_binds_final_audit_lineage_and_blocks_execution() -> None:
    plan = load_action_extraction_traceability_cleanup_hardening_plan(HARDENING_PLAN_PATH)

    assert plan.source_merge_commit == "fe25c0869f62624247cc12bb97c5185586845f22"
    assert plan.source_evidence_audit_sha256 == (
        "a6a1031d85997d8b13b521866d580ce468579cfbb8d731180820fdcc5dd0be79"
    )
    assert plan.consumed_authorization_reused is False
    assert plan.model_request_performed is False
    assert plan.gpu_execution_performed is False
    assert plan.new_authorization_issued is False
    assert plan.full_measured_rerun_authorized is False
    assert plan.next_gate == "full_abc_harness_integration_design"


def test_hardening_plan_json_is_canonical_single_line() -> None:
    text = HARDENING_PLAN_PATH.read_text(encoding="utf-8")
    payload = json.loads(text)
    expected = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )

    assert text == expected
