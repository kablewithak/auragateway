from __future__ import annotations

import json

from auragateway.local_abc.contracts import (
    ConditionId,
    RunTerminalClassification,
)
from auragateway.local_abc.errors import LocalABCFailureCode
from auragateway.local_abc.measured_quality import (
    MeasuredQualityCheck,
    MeasuredQualityDecision,
    build_quality_gated_run_eligibility,
    decide_measured_output_quality,
    score_measured_output,
)

EXPECTED = {
    "answer": "sev3",
    "case_id": "incident-severity",
    "confidence": "high",
    "turn_index": 1,
}


def decision_for(
    output_text: str,
    *,
    finish_reason: str = "stop",
    completion_tokens: int = 24,
) -> MeasuredQualityDecision:
    score = score_measured_output(
        output_text=output_text,
        expected_payload=EXPECTED,
        finish_reason=finish_reason,
        completion_tokens=completion_tokens,
    )
    return decide_measured_output_quality(score)


def test_exact_json_passes_every_required_check() -> None:
    output = json.dumps(EXPECTED, separators=(",", ":"))

    decision = decision_for(output)

    assert decision.passed is True
    assert decision.comparison_eligible is True
    assert decision.failed_checks == ()
    assert decision.failure_codes == ()
    assert decision.score.all_required_checks_passed() is True


def test_empty_output_fails_closed() -> None:
    decision = decision_for("", completion_tokens=1)

    assert decision.passed is False
    assert MeasuredQualityCheck.JSON_PARSE_SUCCESS in decision.failed_checks
    assert LocalABCFailureCode.OUTPUT_JSON_INVALID in decision.failure_codes
    assert decision.score.output_character_count == 0


def test_malformed_json_fails_closed() -> None:
    decision = decision_for('{"answer":"sev3"')

    assert decision.passed is False
    assert LocalABCFailureCode.OUTPUT_JSON_INVALID in decision.failure_codes


def test_trailing_text_is_rejected() -> None:
    output = json.dumps(EXPECTED) + " trailing"

    decision = decision_for(output)

    assert decision.score.json_parse_success is True
    assert decision.score.no_extra_text is False
    assert LocalABCFailureCode.OUTPUT_EXTRA_TEXT in decision.failure_codes


def test_wrong_key_set_is_rejected() -> None:
    payload = dict(EXPECTED)
    payload["extra"] = "not-permitted"

    decision = decision_for(json.dumps(payload))

    assert decision.score.exact_key_set_match is False
    assert LocalABCFailureCode.OUTPUT_KEY_SET_MISMATCH in decision.failure_codes


def test_wrong_answer_is_rejected() -> None:
    payload = dict(EXPECTED)
    payload["answer"] = "sev1"

    decision = decision_for(json.dumps(payload))

    assert decision.score.exact_answer_match is False
    assert LocalABCFailureCode.OUTPUT_ANSWER_MISMATCH in decision.failure_codes


def test_wrong_case_id_is_rejected() -> None:
    payload = dict(EXPECTED)
    payload["case_id"] = "wrong-case"

    decision = decision_for(json.dumps(payload))

    assert decision.score.exact_case_id_match is False
    assert LocalABCFailureCode.OUTPUT_CASE_ID_MISMATCH in decision.failure_codes


def test_wrong_turn_index_is_rejected() -> None:
    payload = dict(EXPECTED)
    payload["turn_index"] = 2

    decision = decision_for(json.dumps(payload))

    assert decision.score.exact_turn_index_match is False
    assert LocalABCFailureCode.OUTPUT_TURN_INDEX_MISMATCH in decision.failure_codes


def test_wrong_confidence_is_rejected() -> None:
    payload = dict(EXPECTED)
    payload["confidence"] = "low"

    decision = decision_for(json.dumps(payload))

    assert decision.score.exact_confidence_match is False
    assert LocalABCFailureCode.OUTPUT_CONFIDENCE_MISMATCH in decision.failure_codes


def test_length_finish_reason_adds_truncation_code() -> None:
    decision = decision_for(
        '{"answer":"sev3"',
        finish_reason="length",
        completion_tokens=64,
    )

    assert LocalABCFailureCode.OUTPUT_TRUNCATED in decision.failure_codes


def test_score_retains_hash_and_length_but_not_raw_output() -> None:
    output = json.dumps(EXPECTED, separators=(",", ":"))

    decision = decision_for(output)
    dumped = decision.model_dump(mode="json")

    assert dumped["score"]["output_character_count"] == len(output)
    assert "output_text" not in dumped["score"]
    assert output not in decision.canonical_json()


def test_two_passing_turns_are_comparison_eligible() -> None:
    first = decision_for(json.dumps(EXPECTED))
    second_expected = dict(EXPECTED)
    second_expected["turn_index"] = 2
    second_score = score_measured_output(
        output_text=json.dumps(second_expected),
        expected_payload=second_expected,
        finish_reason="stop",
        completion_tokens=24,
    )
    second = decide_measured_output_quality(second_score)

    eligibility = build_quality_gated_run_eligibility(
        trajectory_id="r1-c-incident-severity",
        condition_id=ConditionId.C,
        turn_decisions=(first, second),
        telemetry_sufficient=True,
        route_realized=True,
        fallback_used=False,
    )

    assert eligibility.comparison_eligible is True
    assert eligibility.task_completed is True
    assert eligibility.terminal_classification is RunTerminalClassification.COMPLETED_ELIGIBLE


def test_one_failed_turn_makes_trajectory_failed_and_ineligible() -> None:
    passing = decision_for(json.dumps(EXPECTED))
    failing = decision_for("")

    eligibility = build_quality_gated_run_eligibility(
        trajectory_id="r1-c-incident-severity",
        condition_id=ConditionId.C,
        turn_decisions=(passing, failing),
        telemetry_sufficient=True,
        route_realized=True,
        fallback_used=False,
    )

    assert eligibility.comparison_eligible is False
    assert eligibility.task_completed is False
    assert eligibility.terminal_classification is RunTerminalClassification.FAILED_RETAINED
    assert LocalABCFailureCode.OUTPUT_JSON_INVALID in eligibility.failure_codes


def test_quality_pass_with_bad_telemetry_is_task_complete_but_ineligible() -> None:
    decision = decision_for(json.dumps(EXPECTED))

    eligibility = build_quality_gated_run_eligibility(
        trajectory_id="r1-c-incident-severity",
        condition_id=ConditionId.C,
        turn_decisions=(decision, decision),
        telemetry_sufficient=False,
        route_realized=True,
        fallback_used=False,
    )

    assert eligibility.task_completed is True
    assert eligibility.comparison_eligible is False
    assert (
        eligibility.terminal_classification
        is RunTerminalClassification.TASK_COMPLETED_BUT_COMPARISON_INELIGIBLE
    )
    assert LocalABCFailureCode.TELEMETRY_INVALID in eligibility.failure_codes


def test_route_mismatch_blocks_comparison_eligibility() -> None:
    decision = decision_for(json.dumps(EXPECTED))

    eligibility = build_quality_gated_run_eligibility(
        trajectory_id="r1-c-incident-severity",
        condition_id=ConditionId.C,
        turn_decisions=(decision, decision),
        telemetry_sufficient=True,
        route_realized=False,
        fallback_used=True,
    )

    assert eligibility.comparison_eligible is False
    assert LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH in eligibility.failure_codes
