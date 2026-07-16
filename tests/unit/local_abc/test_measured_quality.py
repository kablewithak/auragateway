from __future__ import annotations

import json

import pytest

from auragateway.local_abc.contracts import (
    ConditionId,
    RunTerminalClassification,
)
from auragateway.local_abc.errors import LocalABCFailureCode
from auragateway.local_abc.measured_quality import (
    MeasuredOutputShape,
    MeasuredQualityDecision,
    build_quality_gated_run_eligibility,
    build_trajectory_quality_failure_envelope,
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
    assert decision.failure_codes == ()
    assert decision.score.output_shape is MeasuredOutputShape.JSON_OBJECT


def test_empty_output_reports_only_json_invalid() -> None:
    decision = decision_for("", completion_tokens=1)

    assert decision.passed is False
    assert decision.score.output_shape is MeasuredOutputShape.EMPTY
    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_JSON_INVALID,)


def test_malformed_json_reports_only_json_invalid() -> None:
    decision = decision_for('{"answer":"sev3"')

    assert decision.score.output_shape is MeasuredOutputShape.MALFORMED_JSON
    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_JSON_INVALID,)


def test_markdown_fence_is_classified_without_semantic_claims() -> None:
    output = "```json\n" + json.dumps(EXPECTED) + "\n```"

    decision = decision_for(output)

    assert decision.score.output_shape is MeasuredOutputShape.MARKDOWN_FENCE
    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_JSON_INVALID,)


def test_leading_prose_is_classified_without_semantic_claims() -> None:
    output = "Here is the result: " + json.dumps(EXPECTED)

    decision = decision_for(output)

    assert decision.score.output_shape is MeasuredOutputShape.LEADING_TEXT
    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_JSON_INVALID,)


def test_other_non_json_text_is_classified() -> None:
    decision = decision_for("The answer is sev3.")

    assert decision.score.output_shape is MeasuredOutputShape.OTHER_NON_JSON
    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_JSON_INVALID,)


def test_trailing_text_reports_extra_text_only() -> None:
    output = json.dumps(EXPECTED) + " trailing"

    decision = decision_for(output)

    assert decision.score.output_shape is MeasuredOutputShape.TRAILING_TEXT
    assert decision.score.json_parse_success is True
    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_EXTRA_TEXT,)


def test_multiple_json_values_are_structurally_distinct() -> None:
    output = json.dumps(EXPECTED) + " " + json.dumps(EXPECTED)

    decision = decision_for(output)

    assert decision.score.output_shape is MeasuredOutputShape.MULTIPLE_JSON_VALUES
    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_EXTRA_TEXT,)


def test_json_non_object_reports_key_set_mismatch_only() -> None:
    decision = decision_for('["sev3"]')

    assert decision.score.output_shape is MeasuredOutputShape.JSON_NON_OBJECT
    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_KEY_SET_MISMATCH,)


def test_wrong_key_set_does_not_invent_semantic_mismatches() -> None:
    payload = dict(EXPECTED)
    payload["extra"] = "not-permitted"

    decision = decision_for(json.dumps(payload))

    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_KEY_SET_MISMATCH,)


def test_semantic_mismatch_requires_exact_key_set() -> None:
    payload = dict(EXPECTED)
    payload["answer"] = "sev1"

    decision = decision_for(json.dumps(payload))

    assert decision.failure_codes == (LocalABCFailureCode.OUTPUT_ANSWER_MISMATCH,)


def test_length_finish_reason_adds_truncation_code() -> None:
    decision = decision_for(
        '{"answer":"sev3"',
        finish_reason="length",
        completion_tokens=128,
    )

    assert decision.failure_codes == (
        LocalABCFailureCode.OUTPUT_JSON_INVALID,
        LocalABCFailureCode.OUTPUT_TRUNCATED,
    )


def test_score_retains_metadata_but_not_raw_output() -> None:
    output = json.dumps(EXPECTED, separators=(",", ":"))

    decision = decision_for(output)
    dumped = decision.model_dump(mode="json")

    assert dumped["score"]["output_character_count"] == len(output)
    assert "output_text" not in dumped["score"]
    assert output not in decision.canonical_json()


def test_failed_turn_propagates_to_trajectory_envelope() -> None:
    decision = decision_for("The answer is sev3.")

    envelope = build_trajectory_quality_failure_envelope(
        trajectory_id="canary-c-incident-severity",
        condition_id=ConditionId.C,
        failed_turn_index=1,
        turn_decision=decision,
    )

    assert envelope.failed_turn_index == 1
    assert envelope.failure_codes == (LocalABCFailureCode.OUTPUT_JSON_INVALID,)
    assert envelope.terminal_classification is RunTerminalClassification.FAILED_RETAINED
    assert envelope.comparison_eligible is False


def test_passing_turn_cannot_create_failure_envelope() -> None:
    decision = decision_for(json.dumps(EXPECTED))

    with pytest.raises(ValueError, match="passing output"):
        build_trajectory_quality_failure_envelope(
            trajectory_id="canary-c-incident-severity",
            condition_id=ConditionId.C,
            failed_turn_index=1,
            turn_decision=decision,
        )


def test_two_passing_turns_are_comparison_eligible() -> None:
    first = decision_for(json.dumps(EXPECTED))
    second_expected = dict(EXPECTED)
    second_expected["turn_index"] = 2
    second = decide_measured_output_quality(
        score_measured_output(
            output_text=json.dumps(second_expected),
            expected_payload=second_expected,
            finish_reason="stop",
            completion_tokens=24,
        )
    )

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


def test_failed_turn_makes_trajectory_failed_and_ineligible() -> None:
    passing = decision_for(json.dumps(EXPECTED))
    failing = decision_for("not-json")

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
    assert eligibility.failure_codes == (LocalABCFailureCode.OUTPUT_JSON_INVALID,)
