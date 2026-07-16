"""Fail-closed deterministic output scoring for measured Local A/B/C runs."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import (
    ConditionId,
    LocalABCContract,
    RunEligibility,
    RunTerminalClassification,
)
from auragateway.local_abc.errors import LocalABCFailureCode

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_KEYS = ("answer", "case_id", "confidence", "turn_index")


class MeasuredQualityCheck(StrEnum):
    """Exact deterministic checks required at the model-output boundary."""

    JSON_PARSE_SUCCESS = "json_parse_success"
    EXACT_KEY_SET_MATCH = "exact_key_set_match"
    EXACT_ANSWER_MATCH = "exact_answer_match"
    EXACT_CASE_ID_MATCH = "exact_case_id_match"
    EXACT_TURN_INDEX_MATCH = "exact_turn_index_match"
    EXACT_CONFIDENCE_MATCH = "exact_confidence_match"
    NO_EXTRA_TEXT = "no_extra_text"


class MeasuredOutputScore(LocalABCContract):
    """Metadata-only deterministic score for one model output."""

    schema_version: str = "1.0.0"
    output_text_sha256: str
    output_character_count: int = Field(ge=0)
    finish_reason: str | None = Field(default=None, max_length=80)
    completion_tokens: int = Field(ge=0)
    json_parse_success: bool
    exact_key_set_match: bool
    exact_answer_match: bool
    exact_case_id_match: bool
    exact_turn_index_match: bool
    exact_confidence_match: bool
    no_extra_text: bool

    @field_validator("output_text_sha256")
    @classmethod
    def validate_output_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("output_text_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_score_consistency(self) -> Self:
        dependent = (
            self.exact_key_set_match,
            self.exact_answer_match,
            self.exact_case_id_match,
            self.exact_turn_index_match,
            self.exact_confidence_match,
            self.no_extra_text,
        )
        if not self.json_parse_success and any(dependent):
            raise ValueError("failed JSON parsing cannot pass dependent quality checks")
        if self.output_character_count == 0 and self.json_parse_success:
            raise ValueError("empty output cannot pass JSON parsing")
        return self

    def check_passed(self, check: MeasuredQualityCheck) -> bool:
        """Return the exact boolean represented by one required check."""

        return bool(getattr(self, check.value))

    def all_required_checks_passed(self) -> bool:
        """Return true only when every deterministic check passes."""

        return all(self.check_passed(check) for check in MeasuredQualityCheck)


class MeasuredQualityDecision(LocalABCContract):
    """Fail-closed eligibility decision for one measured output."""

    schema_version: str = "1.0.0"
    score: MeasuredOutputScore
    passed: bool
    comparison_eligible: bool
    failed_checks: tuple[MeasuredQualityCheck, ...] = ()
    failure_codes: tuple[LocalABCFailureCode, ...] = ()

    @field_validator("failed_checks")
    @classmethod
    def validate_failed_checks(
        cls,
        value: tuple[MeasuredQualityCheck, ...],
    ) -> tuple[MeasuredQualityCheck, ...]:
        if len(value) != len(set(value)):
            raise ValueError("failed quality checks must be unique")
        expected_order = tuple(check for check in MeasuredQualityCheck if check in set(value))
        if value != expected_order:
            raise ValueError("failed quality checks must use canonical order")
        return value

    @field_validator("failure_codes")
    @classmethod
    def validate_failure_codes(
        cls,
        value: tuple[LocalABCFailureCode, ...],
    ) -> tuple[LocalABCFailureCode, ...]:
        if len(value) != len(set(value)):
            raise ValueError("quality failure codes must be unique")
        if value != tuple(sorted(value, key=lambda code: code.value)):
            raise ValueError("quality failure codes must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        expected_passed = self.score.all_required_checks_passed()
        if self.passed != expected_passed:
            raise ValueError("quality decision must match the deterministic score")
        if self.comparison_eligible != self.passed:
            raise ValueError("output comparison eligibility must fail closed")
        expected_failed = tuple(
            check for check in MeasuredQualityCheck if not self.score.check_passed(check)
        )
        if self.failed_checks != expected_failed:
            raise ValueError("failed_checks do not match the deterministic score")
        if self.passed and self.failure_codes:
            raise ValueError("passing output cannot contain failure codes")
        if not self.passed and not self.failure_codes:
            raise ValueError("failed output requires machine-readable failure codes")
        return self


def score_measured_output(
    *,
    output_text: str,
    expected_payload: Mapping[str, Any],
    finish_reason: str | None,
    completion_tokens: int,
) -> MeasuredOutputScore:
    """Score one raw output without retaining its text in the returned contract."""

    if tuple(expected_payload) != _EXPECTED_KEYS:
        raise ValueError("expected payload must use the frozen ordered key set")

    stripped = output_text.strip()
    parsed: Any = None
    parse_success = False
    no_extra_text = False

    if stripped:
        try:
            decoder = json.JSONDecoder()
            parsed, end_index = decoder.raw_decode(stripped)
            parse_success = True
            no_extra_text = end_index == len(stripped)
        except json.JSONDecodeError:
            pass

    parsed_mapping = parsed if isinstance(parsed, dict) else {}
    parsed_keys = tuple(parsed_mapping)
    return MeasuredOutputScore(
        output_text_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        output_character_count=len(output_text),
        finish_reason=finish_reason,
        completion_tokens=completion_tokens,
        json_parse_success=parse_success,
        exact_key_set_match=parsed_keys == _EXPECTED_KEYS,
        exact_answer_match=(
            parse_success and parsed_mapping.get("answer") == expected_payload["answer"]
        ),
        exact_case_id_match=(
            parse_success and parsed_mapping.get("case_id") == expected_payload["case_id"]
        ),
        exact_turn_index_match=(
            parse_success and parsed_mapping.get("turn_index") == expected_payload["turn_index"]
        ),
        exact_confidence_match=(
            parse_success and parsed_mapping.get("confidence") == expected_payload["confidence"]
        ),
        no_extra_text=no_extra_text,
    )


def decide_measured_output_quality(
    score: MeasuredOutputScore,
) -> MeasuredQualityDecision:
    """Translate exact check failures into stable error taxonomy entries."""

    failed_checks = tuple(check for check in MeasuredQualityCheck if not score.check_passed(check))
    failure_codes: set[LocalABCFailureCode] = set()

    mapping = {
        MeasuredQualityCheck.JSON_PARSE_SUCCESS: (LocalABCFailureCode.OUTPUT_JSON_INVALID),
        MeasuredQualityCheck.EXACT_KEY_SET_MATCH: (LocalABCFailureCode.OUTPUT_KEY_SET_MISMATCH),
        MeasuredQualityCheck.EXACT_ANSWER_MATCH: (LocalABCFailureCode.OUTPUT_ANSWER_MISMATCH),
        MeasuredQualityCheck.EXACT_CASE_ID_MATCH: (LocalABCFailureCode.OUTPUT_CASE_ID_MISMATCH),
        MeasuredQualityCheck.EXACT_TURN_INDEX_MATCH: (
            LocalABCFailureCode.OUTPUT_TURN_INDEX_MISMATCH
        ),
        MeasuredQualityCheck.EXACT_CONFIDENCE_MATCH: (
            LocalABCFailureCode.OUTPUT_CONFIDENCE_MISMATCH
        ),
        MeasuredQualityCheck.NO_EXTRA_TEXT: (LocalABCFailureCode.OUTPUT_EXTRA_TEXT),
    }
    failure_codes.update(mapping[check] for check in failed_checks)
    if score.finish_reason == "length":
        failure_codes.add(LocalABCFailureCode.OUTPUT_TRUNCATED)

    passed = not failed_checks
    return MeasuredQualityDecision(
        score=score,
        passed=passed,
        comparison_eligible=passed,
        failed_checks=failed_checks,
        failure_codes=tuple(sorted(failure_codes, key=lambda code: code.value)),
    )


def build_quality_gated_run_eligibility(
    *,
    trajectory_id: str,
    condition_id: ConditionId,
    turn_decisions: Sequence[MeasuredQualityDecision],
    telemetry_sufficient: bool,
    route_realized: bool,
    fallback_used: bool,
) -> RunEligibility:
    """Build trajectory eligibility with output quality as a hard boundary."""

    if len(turn_decisions) != 2:
        raise ValueError("quality-gated eligibility requires exactly two turns")

    quality_passed = all(decision.passed for decision in turn_decisions)
    task_completed = quality_passed
    comparison_eligible = (
        quality_passed and telemetry_sufficient and route_realized and not fallback_used
    )

    failure_codes = {code for decision in turn_decisions for code in decision.failure_codes}
    if not telemetry_sufficient:
        failure_codes.add(LocalABCFailureCode.TELEMETRY_INVALID)
    if not route_realized or fallback_used:
        failure_codes.add(LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH)
    if not comparison_eligible and not failure_codes:
        failure_codes.add(LocalABCFailureCode.RUN_INELIGIBLE)

    if comparison_eligible:
        classification = RunTerminalClassification.COMPLETED_ELIGIBLE
    elif task_completed:
        classification = RunTerminalClassification.TASK_COMPLETED_BUT_COMPARISON_INELIGIBLE
    else:
        classification = RunTerminalClassification.FAILED_RETAINED

    return RunEligibility(
        trajectory_id=trajectory_id,
        condition_id=condition_id,
        terminal_classification=classification,
        task_completed=task_completed,
        comparison_eligible=comparison_eligible,
        affinity_comparison_eligible=comparison_eligible,
        telemetry_sufficient=telemetry_sufficient,
        route_realized=route_realized,
        fallback_used=fallback_used,
        failure_codes=tuple(sorted(failure_codes, key=lambda code: code.value)),
    )
