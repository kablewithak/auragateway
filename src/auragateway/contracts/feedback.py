"""Typed feedback-evidence contracts for Gate 7."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EVENT_ID_PATTERN = re.compile(r"^efc-event-[a-z0-9-]{3,80}$")
_SUBGOAL_ID_PATTERN = re.compile(r"^subgoal-[a-z0-9-]{2,80}$")
_TRAJECTORY_ID_PATTERN = re.compile(r"^efc-trajectory-[a-z0-9-]{3,80}$")
_CASE_ID_PATTERN = re.compile(r"^efc-[a-z0-9-]{3,80}$")
_REASON_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,80}$")


class FeedbackEvidenceSource(StrEnum):
    """Supported provenance categories for feedback evidence."""

    RETRIEVAL = "retrieval"
    SCHEMA_VALIDATOR = "schema_validator"
    CITATION_VALIDATOR = "citation_validator"
    DETERMINISTIC_RULE = "deterministic_rule"
    PROVIDER_ERROR = "provider_error"
    USER_CLARIFICATION = "user_clarification"


class FeedbackValidityStatus(StrEnum):
    """Whether an evidence event is trustworthy enough to use."""

    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class FeedbackNoveltyStatus(StrEnum):
    """Whether an event adds new evidence to the trajectory."""

    NEW = "new"
    REDUNDANT = "redundant"
    UNKNOWN = "unknown"


class FeedbackInformativenessStatus(StrEnum):
    """Whether an event is relevant to its declared subgoal."""

    INFORMATIVE = "informative"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


class TaskSufficiencyStatus(StrEnum):
    """Whether retained evidence is enough to finish the task safely."""

    INSUFFICIENT = "insufficient"
    SUFFICIENT = "sufficient"
    UNKNOWN = "unknown"


class EFCFailureCode(StrEnum):
    """Stable failure labels for practical EFC trace review."""

    INVALID_FEEDBACK = "INVALID_FEEDBACK"
    UNKNOWN_VALIDITY = "UNKNOWN_VALIDITY"
    UNINFORMATIVE_FEEDBACK = "UNINFORMATIVE_FEEDBACK"
    UNKNOWN_INFORMATIVENESS = "UNKNOWN_INFORMATIVENESS"
    REDUNDANT_FEEDBACK = "REDUNDANT_FEEDBACK"
    UNKNOWN_NOVELTY = "UNKNOWN_NOVELTY"
    NOVELTY_STATUS_INCONSISTENT = "NOVELTY_STATUS_INCONSISTENT"
    UNRETAINED_VALID_FEEDBACK = "UNRETAINED_VALID_FEEDBACK"
    UNKNOWN_RETENTION = "UNKNOWN_RETENTION"
    MISSING_REQUIRED_SUBGOAL_EVIDENCE = "MISSING_REQUIRED_SUBGOAL_EVIDENCE"
    TASK_INSUFFICIENT = "TASK_INSUFFICIENT"


class FeedbackEvidenceEvent(BaseModel):
    """One metadata-only feedback event inside an agent trajectory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    trace_id: UUID
    turn_index: int = Field(ge=1)
    event_id: str
    subgoal_id: str
    evidence_source: FeedbackEvidenceSource
    evidence_fingerprint: str
    validity_status: FeedbackValidityStatus
    validity_evidence_sha256: str | None = None
    informativeness_status: FeedbackInformativenessStatus
    novelty_status: FeedbackNoveltyStatus
    retained_in_state: bool | None
    retention_location: str | None = Field(default=None, min_length=3, max_length=160)
    next_action_changed: bool | None
    next_action_fingerprint_before: str | None = None
    next_action_fingerprint_after: str | None = None
    task_sufficiency_status: TaskSufficiencyStatus
    evidence_reason_code: str

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        if _EVENT_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("event_id must use efc-event-<slug> form")
        return value

    @field_validator("subgoal_id")
    @classmethod
    def validate_subgoal_id(cls, value: str) -> str:
        if _SUBGOAL_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("subgoal_id must use subgoal-<slug> form")
        return value

    @field_validator(
        "evidence_fingerprint",
        "validity_evidence_sha256",
        "next_action_fingerprint_before",
        "next_action_fingerprint_after",
    )
    @classmethod
    def validate_optional_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("feedback evidence digests must be lowercase SHA-256")
        return value

    @field_validator("evidence_reason_code")
    @classmethod
    def validate_reason_code(cls, value: str) -> str:
        if _REASON_CODE_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence_reason_code must be lowercase snake_case")
        return value

    @model_validator(mode="after")
    def validate_evidence_shape(self) -> FeedbackEvidenceEvent:
        known_validity = self.validity_status is not FeedbackValidityStatus.UNKNOWN
        if known_validity != (self.validity_evidence_sha256 is not None):
            raise ValueError("known validity requires one validity-evidence digest")

        if self.retained_in_state is True and self.retention_location is None:
            raise ValueError("retained feedback requires a retention location")
        if self.retained_in_state is not True and self.retention_location is not None:
            raise ValueError("unretained or unknown feedback cannot claim a retention location")

        before = self.next_action_fingerprint_before
        after = self.next_action_fingerprint_after
        if self.next_action_changed is None:
            if before is not None or after is not None:
                raise ValueError("unknown action change cannot carry action fingerprints")
        else:
            if before is None or after is None:
                raise ValueError("known action change requires before and after fingerprints")
            if self.next_action_changed != (before != after):
                raise ValueError("next_action_changed must match the action fingerprints")

        if (
            self.task_sufficiency_status is TaskSufficiencyStatus.SUFFICIENT
            and self.validity_status is not FeedbackValidityStatus.VALID
        ):
            raise ValueError("only valid evidence may claim task sufficiency")
        return self


class FeedbackTrajectory(BaseModel):
    """Ordered metadata-only feedback events for one fixed task trajectory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    trajectory_id: str
    trace_id: UUID
    events: tuple[FeedbackEvidenceEvent, ...] = Field(min_length=1)
    required_subgoal_ids: tuple[str, ...] = Field(min_length=1)
    completed_subgoal_ids: tuple[str, ...]
    task_completed: bool
    expected_terminal_decision_reached: bool

    @field_validator("trajectory_id")
    @classmethod
    def validate_trajectory_id(cls, value: str) -> str:
        if _TRAJECTORY_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trajectory_id must use efc-trajectory-<slug> form")
        return value

    @field_validator("required_subgoal_ids", "completed_subgoal_ids")
    @classmethod
    def validate_subgoal_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("trajectory subgoal IDs must be unique")
        for subgoal_id in value:
            if _SUBGOAL_ID_PATTERN.fullmatch(subgoal_id) is None:
                raise ValueError("trajectory subgoal IDs must use subgoal-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_trajectory(self) -> FeedbackTrajectory:
        event_ids = [event.event_id for event in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("feedback event IDs must be unique per trajectory")
        if any(event.trace_id != self.trace_id for event in self.events):
            raise ValueError("every feedback event must match the trajectory trace ID")
        turn_indexes = [event.turn_index for event in self.events]
        if turn_indexes != sorted(turn_indexes):
            raise ValueError("feedback events must be ordered by turn_index")
        required = set(self.required_subgoal_ids)
        if any(event.subgoal_id not in required for event in self.events):
            raise ValueError("feedback events must reference declared required subgoals")
        if not set(self.completed_subgoal_ids).issubset(required):
            raise ValueError("completed subgoals must be a subset of required subgoals")
        return self


class FeedbackEventAssessment(BaseModel):
    """Machine-readable assessment for one feedback event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    valid: bool
    informative: bool
    non_redundant: bool
    retained: bool
    next_action_changed: bool
    failure_codes: tuple[EFCFailureCode, ...]


class FeedbackTrajectorySummary(BaseModel):
    """Metadata-only EFC summary without a composite universal score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    trajectory_id: str
    trace_id: UUID
    event_count: int = Field(ge=1)
    valid_event_count: int = Field(ge=0)
    redundant_event_count: int = Field(ge=0)
    retained_valid_event_count: int = Field(ge=0)
    unretained_valid_event_count: int = Field(ge=0)
    feedback_linked_action_change_count: int = Field(ge=0)
    valid_feedback_event_rate: float = Field(ge=0.0, le=1.0)
    redundant_feedback_event_rate: float = Field(ge=0.0, le=1.0)
    retained_feedback_event_rate: float = Field(ge=0.0, le=1.0)
    unretained_valid_feedback_event_rate: float = Field(ge=0.0, le=1.0)
    feedback_linked_action_change_rate: float = Field(ge=0.0, le=1.0)
    task_sufficiency_passed: bool
    event_assessments: tuple[FeedbackEventAssessment, ...]
    failure_codes: tuple[EFCFailureCode, ...]
    efc_evidence_passed: bool
    universal_efc_score: Literal[None] = None

    @model_validator(mode="after")
    def validate_summary(self) -> FeedbackTrajectorySummary:
        if self.event_count != len(self.event_assessments):
            raise ValueError("event_count must match event assessments")
        if self.valid_event_count > self.event_count:
            raise ValueError("valid event count cannot exceed event count")
        if self.redundant_event_count > self.event_count:
            raise ValueError("redundant event count cannot exceed event count")
        if (
            self.retained_valid_event_count + self.unretained_valid_event_count
            != self.valid_event_count
        ):
            raise ValueError("retained and unretained valid-event counts must reconcile")
        expected_valid_rate = self.valid_event_count / self.event_count
        expected_redundant_rate = self.redundant_event_count / self.event_count
        if abs(self.valid_feedback_event_rate - expected_valid_rate) > 1e-12:
            raise ValueError("valid feedback-event rate must reconcile")
        if abs(self.redundant_feedback_event_rate - expected_redundant_rate) > 1e-12:
            raise ValueError("redundant feedback-event rate must reconcile")
        valid_denominator = self.valid_event_count or 1
        if (
            abs(
                self.retained_feedback_event_rate
                - self.retained_valid_event_count / valid_denominator
            )
            > 1e-12
        ):
            raise ValueError("retained feedback-event rate must reconcile")
        if (
            abs(
                self.unretained_valid_feedback_event_rate
                - self.unretained_valid_event_count / valid_denominator
            )
            > 1e-12
        ):
            raise ValueError("unretained feedback-event rate must reconcile")
        actionable = sum(
            assessment.valid and assessment.informative and assessment.retained
            for assessment in self.event_assessments
        )
        action_denominator = actionable or 1
        if (
            abs(
                self.feedback_linked_action_change_rate
                - self.feedback_linked_action_change_count / action_denominator
            )
            > 1e-12
        ):
            raise ValueError("feedback-linked action-change rate must reconcile")
        expected_failure_codes = tuple(
            dict.fromkeys(
                code for assessment in self.event_assessments for code in assessment.failure_codes
            )
        )
        if self.task_sufficiency_passed:
            if EFCFailureCode.TASK_INSUFFICIENT in self.failure_codes:
                raise ValueError("task-sufficient summaries cannot retain TASK_INSUFFICIENT")
        elif EFCFailureCode.TASK_INSUFFICIENT not in self.failure_codes:
            raise ValueError("task-insufficient summaries require TASK_INSUFFICIENT")
        if tuple(
            code
            for code in self.failure_codes
            if code is not EFCFailureCode.TASK_INSUFFICIENT
            and code is not EFCFailureCode.MISSING_REQUIRED_SUBGOAL_EVIDENCE
        ) != tuple(
            code
            for code in expected_failure_codes
            if code is not EFCFailureCode.TASK_INSUFFICIENT
            and code is not EFCFailureCode.MISSING_REQUIRED_SUBGOAL_EVIDENCE
        ):
            raise ValueError("summary failure codes must preserve event failure order")
        expected_pass = not self.failure_codes and self.task_sufficiency_passed
        if self.efc_evidence_passed != expected_pass:
            raise ValueError("efc_evidence_passed must match failures and task sufficiency")
        return self


class FeedbackFixtureCase(BaseModel):
    """One fixed synthetic EFC trajectory and expected outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    trajectory: FeedbackTrajectory
    expected_pass: bool
    expected_failure_codes: tuple[EFCFailureCode, ...]
    negative_control: bool

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _CASE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("case_id must use efc-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_case(self) -> FeedbackFixtureCase:
        if self.expected_pass and self.expected_failure_codes:
            raise ValueError("passing EFC fixtures must not expect failure codes")
        if self.negative_control == self.expected_pass:
            raise ValueError("negative_control must be the inverse of expected_pass")
        return self


class FeedbackFixtureSet(BaseModel):
    """Frozen Gate 7 EFC fixture set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str = "auragateway-gate-7-efc-evidence-v1"
    cases: tuple[FeedbackFixtureCase, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_fixture_set(self) -> FeedbackFixtureSet:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("EFC fixture case IDs must be unique")
        if not any(case.expected_pass for case in self.cases):
            raise ValueError("EFC fixtures require at least one passing control")
        if not any(case.negative_control for case in self.cases):
            raise ValueError("EFC fixtures require negative controls")
        return self


class FeedbackFixtureResult(BaseModel):
    """One executed EFC fixture and expectation comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    summary: FeedbackTrajectorySummary
    expectation_matched: bool
    negative_control: bool


class Gate7EFCEvidenceReport(BaseModel):
    """Reproducible report for fixed feedback-evidence trajectories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    results: tuple[FeedbackFixtureResult, ...]
    fixture_count: int
    negative_control_count: int
    task_sufficiency_pass_count: int
    all_expectations_matched: bool
    efc_evidence_controls_passed: bool
    synthetic_fixture_execution: Literal[True] = True
    measured_execution_permitted: Literal[False] = False
    universal_efc_score_reported: Literal[False] = False

    @model_validator(mode="after")
    def validate_report(self) -> Gate7EFCEvidenceReport:
        if self.fixture_count != len(self.results):
            raise ValueError("fixture_count must match EFC results")
        if self.negative_control_count != sum(result.negative_control for result in self.results):
            raise ValueError("negative control count must reconcile")
        if self.task_sufficiency_pass_count != sum(
            result.summary.task_sufficiency_passed for result in self.results
        ):
            raise ValueError("task-sufficiency pass count must reconcile")
        expected_match = all(result.expectation_matched for result in self.results)
        if self.all_expectations_matched != expected_match:
            raise ValueError("all_expectations_matched must reconcile")
        if self.efc_evidence_controls_passed != expected_match:
            raise ValueError("EFC control status must match fixture expectations")
        return self


class Gate7EFCEvidenceManifest(BaseModel):
    """Hash-bound inventory for synthetic EFC evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-7-efc-evidence-manifest-v1"
    fixture_path: str
    fixture_sha256: str
    report_path: str
    report_sha256: str
    episode_manifest_path: str
    episode_manifest_sha256: str
    quality_gate_manifest_path: str
    quality_gate_manifest_sha256: str
    fixture_count: int
    negative_control_count: int
    efc_evidence_controls_passed: bool
    synthetic_fixture_execution: Literal[True] = True
    measured_execution_permitted: Literal[False] = False
    universal_efc_score_reported: Literal[False] = False

    @field_validator(
        "fixture_sha256",
        "report_sha256",
        "episode_manifest_sha256",
        "quality_gate_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("EFC manifest digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> Gate7EFCEvidenceManifest:
        if not self.efc_evidence_controls_passed:
            raise ValueError("frozen EFC manifest requires passing controls")
        return self


class Gate7EFCEvidenceSummary(BaseModel):
    """Safe CLI summary for EFC evidence build or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_count: int
    negative_control_count: int
    task_sufficiency_pass_count: int
    efc_evidence_controls_passed: bool
    synthetic_fixture_execution: bool
    measured_execution_permitted: bool
    universal_efc_score_reported: bool
    fixture_sha256: str
    report_sha256: str
