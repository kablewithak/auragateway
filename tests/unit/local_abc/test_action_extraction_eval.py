from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_eval import (
    RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY,
    ActionExtractionCaseScore,
    ActionExtractionEvaluationPlan,
    ActionExtractionEvaluationReport,
    BaselineMetricState,
    EvaluationGateDecision,
    ExtractionCandidateRejectionCode,
    ExtractionEvaluationFailureCode,
    ReconcileBalanceExtractionManifest,
    build_action_extraction_evaluation_report,
    build_action_extraction_prompt_identity,
    build_reconcile_balance_extraction_response_format,
    evaluate_reconcile_balance_extraction,
    load_action_extraction_evaluation_package,
    load_action_extraction_evaluation_plan,
    load_reconcile_balance_extraction_manifest,
    render_reconcile_balance_extraction_prompt,
)
from auragateway.local_abc.arithmetic_action import (
    ActionRealizationFailureCode,
    ReconcileBalanceAction,
    reconcile_balance_action_schema_sha256,
)

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_extraction_eval_cases_v1.json"
PLAN_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_extraction_eval_plan_v1.json"
EXPECTED_MANIFEST_FINGERPRINT = "babfd460048784991041957fc50e29853d6caa29ba195207bd8f2ad1088bbbf5"
EXPECTED_PLAN_FINGERPRINT = "53a9dc8f3418b4df86151ad9763d44ddd16179ed5d4ca7ac505c3b2f7e401b62"
EXPECTED_PROMPT_POLICY_FINGERPRINT = (
    "5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"
)


def load_manifest() -> ReconcileBalanceExtractionManifest:
    return load_reconcile_balance_extraction_manifest(MANIFEST_PATH)


def load_plan() -> ActionExtractionEvaluationPlan:
    return load_action_extraction_evaluation_plan(PLAN_PATH)


def perfect_score(case_index: int = 0) -> ActionExtractionCaseScore:
    case = load_manifest().accepted_cases[case_index]
    return evaluate_reconcile_balance_extraction(
        case=case,
        output_text=case.expected_action.canonical_json(),
        finish_reason="stop",
        completion_tokens=40,
    )


def perfect_scores() -> tuple[ActionExtractionCaseScore, ...]:
    return tuple(
        evaluate_reconcile_balance_extraction(
            case=case,
            output_text=case.expected_action.canonical_json(),
            finish_reason="stop",
            completion_tokens=40,
        )
        for case in load_manifest().accepted_cases
    )


def test_evaluation_package_cross_binds_manifest_and_plan() -> None:
    package = load_action_extraction_evaluation_package(
        manifest_path=MANIFEST_PATH,
        plan_path=PLAN_PATH,
    )

    assert package.manifest.fingerprint() == EXPECTED_MANIFEST_FINGERPRINT
    assert package.plan.fingerprint() == EXPECTED_PLAN_FINGERPRINT
    assert package.plan.manifest_sha256 == package.manifest.fingerprint()


def test_manifest_and_plan_load_with_exact_fingerprints() -> None:
    manifest = load_manifest()
    plan = load_plan()

    assert manifest.fingerprint() == EXPECTED_MANIFEST_FINGERPRINT
    assert plan.fingerprint() == EXPECTED_PLAN_FINGERPRINT
    assert (
        RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY.fingerprint()
        == EXPECTED_PROMPT_POLICY_FINGERPRINT
    )
    assert plan.manifest_sha256 == manifest.fingerprint()
    assert plan.prompt_policy_sha256 == EXPECTED_PROMPT_POLICY_FINGERPRINT


def test_manifest_binds_merged_action_implementation() -> None:
    manifest = load_manifest()

    assert manifest.implementation_commit == ("0e4f761de11c85ccf40d234e93a5b2d974590612")
    assert manifest.action_schema_sha256 == reconcile_balance_action_schema_sha256()
    assert manifest.failed_canary_audit_sha256 == (
        "772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62"
    )


def test_case_constitution_has_hard_cases_and_rejected_candidates() -> None:
    manifest = load_manifest()
    accepted_ids = {case.eval_case_id for case in manifest.accepted_cases}
    rejected_ids = {case.candidate_id for case in manifest.rejected_candidates}

    assert len(manifest.accepted_cases) == 12
    assert len(manifest.rejected_candidates) == 6
    assert "same-answer-different-operands" in accepted_ids
    assert "turn-two-history-distractors" in accepted_ids
    assert "conflicting-opening-balances" in rejected_ids
    assert accepted_ids.isdisjoint(rejected_ids)


def test_rejected_candidates_preserve_explicit_reasons() -> None:
    manifest = load_manifest()
    codes = {candidate.rejection_code for candidate in manifest.rejected_candidates}

    assert ExtractionCandidateRejectionCode.AMBIGUOUS_GROUND_TRUTH in codes
    assert ExtractionCandidateRejectionCode.REFUSAL_CONTRACT_REQUIRED in codes
    assert ExtractionCandidateRejectionCode.UNSUPPORTED_CAPABILITY in codes
    assert ExtractionCandidateRejectionCode.OUT_OF_SCOPE_DOMAIN in codes
    assert all(len(candidate.reject_reason) >= 24 for candidate in manifest.rejected_candidates)


def test_response_schema_requests_action_not_final_answer() -> None:
    response_format = build_reconcile_balance_extraction_response_format()
    properties = response_format["json_schema"]["schema"]["properties"]

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "reconcile-balance-action-v1"
    assert "opening_balance" in properties
    assert "credits" in properties
    assert "debits" in properties
    assert "answer" not in properties


def test_prompt_policy_prohibits_direct_arithmetic_and_retention() -> None:
    policy = RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY

    assert policy.direct_answer_permitted is False
    assert policy.arithmetic_execution_by_model_permitted is False
    assert policy.extra_text_permitted is False
    assert policy.raw_prompt_retained_in_evidence is False
    assert policy.raw_output_retained_in_evidence is False
    assert policy.hidden_retries_permitted is False
    assert policy.repair_attempts_permitted is False


def test_prompt_identity_retains_hashes_not_prompt_text() -> None:
    case = load_manifest().accepted_cases[0]
    rendered = render_reconcile_balance_extraction_prompt(case)
    identity = build_action_extraction_prompt_identity(case)
    serialized = identity.canonical_json()

    assert identity.case_prompt_sha256 == case.prompt_sha256
    assert identity.raw_prompt_retained is False
    assert case.user_prompt not in serialized
    assert rendered not in serialized
    assert "Do not calculate or emit the final reconciliation answer" in rendered


def test_perfect_action_passes_every_separate_metric() -> None:
    score = perfect_score()

    assert score.action_json_valid is True
    assert score.action_schema_valid is True
    assert score.exact_case_id_match is True
    assert score.exact_turn_index_match is True
    assert score.exact_operand_match is True
    assert score.execution_success is True
    assert score.final_answer_match is True
    assert score.first_attempt_task_success is True
    assert score.action_failure_code is None
    assert score.evaluation_failure_codes == ()


def test_malformed_json_is_contract_failure_without_semantic_claims() -> None:
    case = load_manifest().accepted_cases[0]
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text='{"capability":"arithmetic.reconcile_balance.v1"',
        finish_reason="stop",
        completion_tokens=20,
    )

    assert score.action_json_valid is False
    assert score.action_schema_valid is False
    assert score.exact_operand_match is False
    assert score.execution_success is False
    assert score.action_failure_code is ActionRealizationFailureCode.ACTION_JSON_INVALID
    assert score.evaluation_failure_codes == (
        ExtractionEvaluationFailureCode.OUTPUT_CONTRACT_FAILED,
    )


def test_json_non_object_is_schema_failure() -> None:
    case = load_manifest().accepted_cases[0]
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text="[]",
        finish_reason="stop",
        completion_tokens=3,
    )

    assert score.action_json_valid is True
    assert score.action_schema_valid is False
    assert score.action_failure_code is ActionRealizationFailureCode.ACTION_SCHEMA_INVALID
    assert score.first_attempt_task_success is False


def test_wrong_turn_is_separate_identity_failure() -> None:
    case = load_manifest().accepted_cases[0]
    wrong_turn = case.expected_action.model_copy(update={"turn_index": 2})
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text=wrong_turn.canonical_json(),
        finish_reason="stop",
        completion_tokens=40,
    )

    assert score.action_schema_valid is True
    assert score.exact_case_id_match is True
    assert score.exact_turn_index_match is False
    assert score.exact_operand_match is True
    assert score.execution_success is True
    assert ExtractionEvaluationFailureCode.TURN_INDEX_MISMATCH in (score.evaluation_failure_codes)
    assert score.first_attempt_task_success is False


def test_wrong_operands_can_match_answer_but_still_fail_extraction() -> None:
    case = load_manifest().accepted_cases[0]
    compensating_action = ReconcileBalanceAction(
        case_id="payment-reconciliation",
        turn_index=1,
        opening_balance=1100,
        credits=400,
        debits=50,
    )
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text=compensating_action.canonical_json(),
        finish_reason="stop",
        completion_tokens=40,
    )

    assert score.exact_operand_match is False
    assert score.execution_success is True
    assert score.final_answer_match is True
    assert ExtractionEvaluationFailureCode.OPERAND_MISMATCH in (score.evaluation_failure_codes)
    assert score.first_attempt_task_success is False


def test_wrong_operands_and_wrong_answer_are_scored_separately() -> None:
    case = load_manifest().accepted_cases[0]
    wrong_action = case.expected_action.model_copy(update={"credits": 301})
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text=wrong_action.canonical_json(),
        finish_reason="stop",
        completion_tokens=40,
    )

    assert score.exact_operand_match is False
    assert score.execution_success is True
    assert score.final_answer_match is False
    assert score.evaluation_failure_codes == (
        ExtractionEvaluationFailureCode.FINAL_ANSWER_MISMATCH,
        ExtractionEvaluationFailureCode.OPERAND_MISMATCH,
    )


def test_valid_action_with_unsigned_result_failure_is_retained() -> None:
    case = load_manifest().accepted_cases[0]
    failing_action = ReconcileBalanceAction(
        case_id="payment-reconciliation",
        turn_index=1,
        opening_balance=0,
        credits=0,
        debits=1,
    )
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text=failing_action.canonical_json(),
        finish_reason="stop",
        completion_tokens=40,
    )

    assert score.action_schema_valid is True
    assert score.execution_success is False
    assert score.result_sha256 is None
    assert score.action_failure_code is (ActionRealizationFailureCode.ACTION_RESULT_OUT_OF_RANGE)
    assert ExtractionEvaluationFailureCode.DETERMINISTIC_EXECUTION_FAILED in (
        score.evaluation_failure_codes
    )


def test_unexpected_finish_reason_fails_first_attempt_gate() -> None:
    case = load_manifest().accepted_cases[0]
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text=case.expected_action.canonical_json(),
        finish_reason="length",
        completion_tokens=128,
    )

    assert score.final_answer_match is True
    assert score.first_attempt_task_success is False
    assert score.evaluation_failure_codes == (
        ExtractionEvaluationFailureCode.FINISH_REASON_UNEXPECTED,
    )


def test_score_retains_hashes_not_model_output() -> None:
    case = load_manifest().accepted_cases[0]
    output = case.expected_action.canonical_json()
    score = evaluate_reconcile_balance_extraction(
        case=case,
        output_text=output,
        finish_reason="stop",
        completion_tokens=40,
    )

    serialized = score.canonical_json()
    assert output not in serialized
    assert score.output_text_sha256 in serialized
    assert score.raw_output_retained is False
    assert score.hidden_retry_count == 0
    assert score.repair_attempt_count == 0
    assert score.replacement_request_count == 0


def test_perfect_fixed_report_passes_all_or_nothing_gate() -> None:
    manifest = load_manifest()
    plan = load_plan()
    report = build_action_extraction_evaluation_report(
        report_id="reconcile-balance-extraction-local-perfect-v1",
        created_at=datetime(2026, 7, 16, 20, 0, tzinfo=UTC),
        plan=plan,
        manifest=manifest,
        scores=perfect_scores(),
    )

    assert report.gate_decision is EvaluationGateDecision.PASSED
    assert report.failed_case_ids == ()
    assert report.action_json_valid.rate == 1
    assert report.action_schema_valid.rate == 1
    assert report.identity_accuracy.rate == 1
    assert report.operand_accuracy.rate == 1
    assert report.execution_success.rate == 1
    assert report.final_answer_accuracy.rate == 1
    assert report.first_attempt_task_success.rate == 1
    assert report.failure_code_counts == {}


def test_one_operand_failure_fails_report_without_hiding_execution() -> None:
    manifest = load_manifest()
    plan = load_plan()
    scores = list(perfect_scores())
    case = manifest.accepted_cases[0]
    wrong_action = case.expected_action.model_copy(update={"credits": 301})
    scores[0] = evaluate_reconcile_balance_extraction(
        case=case,
        output_text=wrong_action.canonical_json(),
        finish_reason="stop",
        completion_tokens=40,
    )
    report = build_action_extraction_evaluation_report(
        report_id="reconcile-balance-extraction-local-failed-v1",
        created_at=datetime(2026, 7, 16, 20, 5, tzinfo=UTC),
        plan=plan,
        manifest=manifest,
        scores=tuple(scores),
    )

    assert report.gate_decision is EvaluationGateDecision.FAILED
    assert report.failed_case_ids == ("historical-turn-one",)
    assert report.execution_success.rate == 1
    assert report.operand_accuracy.rate < 1
    assert report.final_answer_accuracy.rate < 1
    assert report.failure_code_counts["OPERAND_MISMATCH"] == 1
    assert report.failure_code_counts["FINAL_ANSWER_MISMATCH"] == 1


def test_report_contract_rejects_metric_drift() -> None:
    manifest = load_manifest()
    plan = load_plan()
    report = build_action_extraction_evaluation_report(
        report_id="reconcile-balance-extraction-metric-binding-v1",
        created_at=datetime(2026, 7, 16, 20, 8, tzinfo=UTC),
        plan=plan,
        manifest=manifest,
        scores=perfect_scores(),
    )
    payload = report.model_dump(mode="json")
    payload["operand_accuracy"]["passed_count"] = 11
    payload["operand_accuracy"]["rate"] = "0.9166666666666666666666666667"

    with pytest.raises(ValidationError, match="report metric operand_accuracy drifted"):
        ActionExtractionEvaluationReport.model_validate(payload)


def test_report_rejects_missing_or_reordered_cases() -> None:
    manifest = load_manifest()
    plan = load_plan()
    scores = perfect_scores()

    with pytest.raises(ValueError, match="exact fixed case order"):
        build_action_extraction_evaluation_report(
            report_id="reconcile-balance-extraction-order-drift-v1",
            created_at=datetime(2026, 7, 16, 20, 10, tzinfo=UTC),
            plan=plan,
            manifest=manifest,
            scores=tuple(reversed(scores)),
        )


def test_baseline_comparison_is_bounded_to_observed_metrics() -> None:
    baseline = load_plan().baseline

    assert baseline.final_answer_match is False
    assert baseline.first_attempt_task_success is False
    assert baseline.failure_code == "OUTPUT_ANSWER_MISMATCH"
    assert baseline.action_json_valid_state is BaselineMetricState.NOT_MEASURED
    assert baseline.action_schema_valid_state is BaselineMetricState.NOT_MEASURED
    assert baseline.identity_accuracy_state is BaselineMetricState.NOT_MEASURED
    assert baseline.operand_accuracy_state is BaselineMetricState.NOT_MEASURED
    assert baseline.deterministic_execution_state is BaselineMetricState.NOT_MEASURED


def test_plan_keeps_execution_and_gpu_blocked() -> None:
    plan = load_plan()

    assert plan.execution_authorized is False
    assert plan.gpu_execution_authorized is False
    assert plan.full_measured_rerun_authorized is False
    assert plan.hidden_retry_count == 0
    assert plan.repair_attempt_count == 0
    assert plan.replacement_request_count == 0
    assert plan.direct_model_arithmetic_fallback_permitted is False
    assert plan.next_gate == "new_bounded_action_extraction_authorization"


def test_plan_thresholds_are_all_one() -> None:
    thresholds = load_plan().thresholds

    assert thresholds.action_json_valid_rate == 1
    assert thresholds.action_schema_valid_rate == 1
    assert thresholds.identity_accuracy == 1
    assert thresholds.operand_accuracy == 1
    assert thresholds.execution_success_rate == 1
    assert thresholds.final_answer_accuracy == 1
    assert thresholds.first_attempt_task_success_rate == 1


def test_manifest_rejects_action_schema_drift() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["action_schema_sha256"] = "0" * 64

    with pytest.raises(ValidationError, match="action schema binding drifted"):
        ReconcileBalanceExtractionManifest.model_validate(payload)


def test_machine_readable_eval_assets_are_canonical_single_line_json() -> None:
    for path in (MANIFEST_PATH, PLAN_PATH):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1
        assert json.dumps(
            json.loads(text),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ) == text.rstrip("\n")
