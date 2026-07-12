"""Typed Gate 5 route-history, retry, and regulation evidence contracts."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.provider import ProviderErrorCode, ProviderName
from auragateway.contracts.route import SessionRouteTransitionResult
from auragateway.contracts.route_policy import (
    RoutePolicyDecision,
    RoutePolicyDecisionStatus,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class RegulationDecisionStatus(StrEnum):
    """Authorization state emitted by route and retry regulation."""

    AUTHORIZED = "authorized"
    BLOCKED = "blocked"


class RouteRegulationCode(StrEnum):
    """Bounded outcome codes for route-history regulation."""

    AUTHORIZED_POLICY_DECISION = "AUTHORIZED_POLICY_DECISION"
    BLOCKED_POLICY_DECISION = "BLOCKED_POLICY_DECISION"
    BLOCKED_ROUTE_THRASH = "BLOCKED_ROUTE_THRASH"


class RetryDecisionCode(StrEnum):
    """Bounded outcome codes for retry authorization."""

    AUTHORIZED_BOUNDED_RETRY = "AUTHORIZED_BOUNDED_RETRY"
    BLOCKED_NO_DEFINITE_FAILURE = "BLOCKED_NO_DEFINITE_FAILURE"
    BLOCKED_AMBIGUOUS_DUPLICATE_RISK = "BLOCKED_AMBIGUOUS_DUPLICATE_RISK"
    BLOCKED_NON_RETRYABLE_FAILURE = "BLOCKED_NON_RETRYABLE_FAILURE"
    BLOCKED_RETRY_BUDGET_EXHAUSTED = "BLOCKED_RETRY_BUDGET_EXHAUSTED"
    BLOCKED_RETRY_REQUEST_MISMATCH = "BLOCKED_RETRY_REQUEST_MISMATCH"
    BLOCKED_ROUTE_CHANGE_REQUIRES_POLICY = "BLOCKED_ROUTE_CHANGE_REQUIRES_POLICY"
    BLOCKED_INVALID_RETRY = "BLOCKED_INVALID_RETRY"


class RegulationCaseCategory(StrEnum):
    """Fixture category retained in deterministic Gate 5 evidence."""

    ROUTE = "route"
    RETRY = "retry"


class AttemptOutcome(StrEnum):
    """Terminal certainty for one provider attempt in a retry chain."""

    SUCCEEDED = "succeeded"
    DEFINITE_FAILURE = "definite_failure"
    AMBIGUOUS = "ambiguous"


class RouteDecisionHistoryEntry(BaseModel):
    """One applied, authorized route decision and its resulting state transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence_index: int = Field(ge=1)
    policy_decision: RoutePolicyDecision
    transition_result: SessionRouteTransitionResult
    applied_at: datetime

    @field_validator("applied_at")
    @classmethod
    def validate_applied_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("applied_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_applied_decision(self) -> RouteDecisionHistoryEntry:
        decision = self.policy_decision
        transition = decision.authorized_transition
        if decision.status is not RoutePolicyDecisionStatus.AUTHORIZED or transition is None:
            raise ValueError("route history requires an authorized policy decision")
        if self.applied_at < decision.evaluated_at:
            raise ValueError("route history cannot be applied before policy evaluation")
        if self.transition_result.previous_state != transition.previous_state:
            raise ValueError("history transition previous_state must match the authorization")
        if self.transition_result.reason is not transition.reason:
            raise ValueError("history transition reason must match the authorization")
        current = self.transition_result.current_state
        target = (
            transition.target_provider,
            transition.target_model,
            transition.target_cache_affinity_status,
            transition.cache_evidence_at,
        )
        actual = (
            current.active_provider,
            current.active_model,
            current.cache_affinity_status,
            current.last_cache_evidence_at,
        )
        if actual != target:
            raise ValueError("history transition result must match the authorized target")
        return self


class RouteDecisionHistory(BaseModel):
    """Ordered, metadata-only route history for one session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    session_id_hash: str
    entries: tuple[RouteDecisionHistoryEntry, ...] = Field(default=(), max_length=100)

    @field_validator("session_id_hash")
    @classmethod
    def validate_session_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("session_id_hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_ordered_history(self) -> RouteDecisionHistory:
        for expected_index, entry in enumerate(self.entries, start=1):
            if entry.sequence_index != expected_index:
                raise ValueError("route history sequence indexes must be contiguous")
            current = entry.transition_result.current_state
            if current.session_id_hash != self.session_id_hash:
                raise ValueError("route history entries must belong to one session")
            if expected_index > 1:
                previous_entry = self.entries[expected_index - 2]
                previous_state = entry.transition_result.previous_state
                previous_current_state = previous_entry.transition_result.current_state
                if previous_state != previous_current_state:
                    raise ValueError("route history state chain must be contiguous")
                if entry.applied_at < previous_entry.applied_at:
                    raise ValueError("route history timestamps must be non-decreasing")
        return self

    @property
    def applied_route_change_count(self) -> int:
        """Return applied provider/model binding changes in this history."""

        return sum(entry.transition_result.route_changed for entry in self.entries)


class RoutePolicyRegulationRequest(BaseModel):
    """Regulation inputs applied after one route-policy decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    policy_decision: RoutePolicyDecision
    history: RouteDecisionHistory
    max_route_changes_per_session: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def validate_history_boundary(self) -> RoutePolicyRegulationRequest:
        transition = self.policy_decision.authorized_transition
        if transition is None:
            return self
        previous_state = transition.previous_state
        if previous_state.session_id_hash != self.history.session_id_hash:
            raise ValueError("regulation history must match the proposed transition session")
        if self.history.entries:
            last_state = self.history.entries[-1].transition_result.current_state
            if last_state != previous_state:
                raise ValueError("regulation history must end at the proposed previous state")
        elif previous_state.route_change_count != 0:
            raise ValueError("empty regulation history cannot omit prior route changes")
        if self.history.applied_route_change_count != previous_state.route_change_count:
            raise ValueError("route history count must match the session route-change count")
        return self


class RoutePolicyRegulationDecision(BaseModel):
    """Final authorization after route-history regulation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: RegulationDecisionStatus
    decision_code: RouteRegulationCode
    route_change_count_before: int = Field(ge=0)
    regulated_policy_decision: RoutePolicyDecision | None

    @model_validator(mode="after")
    def validate_decision_shape(self) -> RoutePolicyRegulationDecision:
        if self.status is RegulationDecisionStatus.AUTHORIZED:
            if (
                self.decision_code is not RouteRegulationCode.AUTHORIZED_POLICY_DECISION
                or self.regulated_policy_decision is None
            ):
                raise ValueError("authorized route regulation requires a policy decision")
        elif self.regulated_policy_decision is not None:
            raise ValueError("blocked route regulation must not expose an executable decision")
        return self


class RetryAttemptRecord(BaseModel):
    """One metadata-only provider attempt retained for retry regulation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_index: int = Field(ge=1)
    logical_request_fingerprint: str
    provider: ProviderName
    model_alias: str
    outcome: AttemptOutcome
    error_code: ProviderErrorCode | None = None
    retryable: bool = False
    recovery_action_fingerprint: str | None = None
    new_evidence_fingerprint: str | None = None

    @field_validator(
        "logical_request_fingerprint",
        "recovery_action_fingerprint",
        "new_evidence_fingerprint",
    )
    @classmethod
    def validate_fingerprint(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("retry fingerprints must be lowercase SHA-256")
        return value

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: ProviderName) -> ProviderName:
        if value is ProviderName.UNAVAILABLE:
            raise ValueError("retry attempts require an executable provider")
        return value

    @field_validator("model_alias")
    @classmethod
    def validate_model_alias(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("model_alias must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_attempt_outcome(self) -> RetryAttemptRecord:
        if self.attempt_index == 1 and self.recovery_action_fingerprint is not None:
            raise ValueError("first provider attempt must not contain a recovery action")
        if self.attempt_index > 1 and self.recovery_action_fingerprint is None:
            raise ValueError("retry attempts require a recovery action fingerprint")
        if self.outcome is AttemptOutcome.SUCCEEDED:
            if self.error_code is not None or self.retryable:
                raise ValueError("successful attempts must not contain failure metadata")
        elif self.error_code is None:
            raise ValueError("failed attempts require a provider error code")
        if self.outcome is AttemptOutcome.AMBIGUOUS:
            if self.error_code is not ProviderErrorCode.AMBIGUOUS_RESPONSE:
                raise ValueError("ambiguous attempts require the ambiguous response error code")
            if self.retryable:
                raise ValueError("ambiguous attempts cannot be marked retryable")
        if (
            self.outcome is AttemptOutcome.DEFINITE_FAILURE
            and self.error_code is ProviderErrorCode.AMBIGUOUS_RESPONSE
        ):
            raise ValueError("definite failures cannot use the ambiguous response error code")
        return self


class ProposedRetryAttempt(BaseModel):
    """Metadata-only next retry proposed after a definite provider failure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_index: int = Field(ge=2)
    logical_request_fingerprint: str
    provider: ProviderName
    model_alias: str
    recovery_action_fingerprint: str
    new_evidence_fingerprint: str | None = None

    @field_validator(
        "logical_request_fingerprint",
        "recovery_action_fingerprint",
        "new_evidence_fingerprint",
    )
    @classmethod
    def validate_fingerprint(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("retry fingerprints must be lowercase SHA-256")
        return value

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: ProviderName) -> ProviderName:
        if value is ProviderName.UNAVAILABLE:
            raise ValueError("proposed retries require an executable provider")
        return value

    @field_validator("model_alias")
    @classmethod
    def validate_model_alias(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("model_alias must use stable lowercase characters")
        return value


class RetryAuthorizationRequest(BaseModel):
    """Retry-chain inputs for bounded, duplicate-safe authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    policy_id: str
    policy_version: str
    max_retries: int = Field(default=1, ge=0, le=3)
    attempts: tuple[RetryAttemptRecord, ...] = Field(min_length=1, max_length=4)
    proposed_attempt: ProposedRetryAttempt

    @field_validator("policy_id", "policy_version")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("retry policy identifiers must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_retry_chain(self) -> RetryAuthorizationRequest:
        first = self.attempts[0]
        for expected_index, attempt in enumerate(self.attempts, start=1):
            if attempt.attempt_index != expected_index:
                raise ValueError("retry attempt indexes must be contiguous")
            if attempt.logical_request_fingerprint != first.logical_request_fingerprint:
                raise ValueError("retry history must retain one logical request fingerprint")
            if (attempt.provider, attempt.model_alias) != (first.provider, first.model_alias):
                raise ValueError("retry history must remain on one provider/model route")
        if self.proposed_attempt.attempt_index != len(self.attempts) + 1:
            raise ValueError("proposed retry attempt index must follow the retained history")
        return self


class RetryAuthorizationDecision(BaseModel):
    """Machine-readable authorization or block for one proposed retry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: RegulationDecisionStatus
    decision_code: RetryDecisionCode
    retries_used: int = Field(ge=0)
    authorized_retry: ProposedRetryAttempt | None

    @model_validator(mode="after")
    def validate_decision_shape(self) -> RetryAuthorizationDecision:
        if self.status is RegulationDecisionStatus.AUTHORIZED:
            if (
                self.decision_code is not RetryDecisionCode.AUTHORIZED_BOUNDED_RETRY
                or self.authorized_retry is None
            ):
                raise ValueError("authorized retry decisions require a proposed retry")
        elif self.authorized_retry is not None:
            raise ValueError("blocked retry decisions must not expose an executable retry")
        return self


class RouteRegulationFixtureCase(BaseModel):
    """One deterministic route-regulation case and expected result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    request: RoutePolicyRegulationRequest
    expected_status: RegulationDecisionStatus
    expected_code: RouteRegulationCode
    negative_control: bool = False


class RetryRegulationFixtureCase(BaseModel):
    """One deterministic retry-regulation case and expected result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    request: RetryAuthorizationRequest
    expected_status: RegulationDecisionStatus
    expected_code: RetryDecisionCode
    negative_control: bool = False


class Gate5RegulationFixtureSet(BaseModel):
    """Deterministic route and retry regulation fixtures for Gate 5 closeout."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    route_cases: tuple[RouteRegulationFixtureCase, ...] = Field(min_length=1)
    retry_cases: tuple[RetryRegulationFixtureCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_cases(self) -> Gate5RegulationFixtureSet:
        route_case_ids = [case.case_id for case in self.route_cases]
        retry_case_ids = [case.case_id for case in self.retry_cases]
        case_ids = [*route_case_ids, *retry_case_ids]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Gate 5 regulation case IDs must be unique")
        return self


class Gate5RegulationCaseResult(BaseModel):
    """One deterministic Gate 5 regulation fixture result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    category: RegulationCaseCategory
    actual_status: RegulationDecisionStatus
    actual_code: RouteRegulationCode | RetryDecisionCode
    expectation_matched: bool
    negative_control: bool


class Gate5RegulationReport(BaseModel):
    """Reproducible Gate 5 route and retry regulation report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    status: Literal["passed", "failed"]
    fixture_set_id: str
    results: tuple[Gate5RegulationCaseResult, ...]
    fixture_count: int = Field(ge=1)
    negative_control_count: int = Field(ge=1)
    all_expectations_matched: bool
    route_thrash_detected: bool
    ambiguous_duplicate_risk_blocked: bool
    retry_budget_enforced: bool
    invalid_retry_detected: bool
    gate_5_regulation_passed: bool
    measured_execution_permitted: bool = False


class Gate5RegulationManifest(BaseModel):
    """Frozen hashes and summary for Gate 5 regulation evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_path: str
    fixture_sha256: str
    report_path: str
    report_sha256: str
    fixture_count: int = Field(ge=1)
    negative_control_count: int = Field(ge=1)
    gate_5_regulation_passed: bool

    @field_validator("fixture_sha256", "report_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("Gate 5 manifest hashes must be lowercase SHA-256")
        return value


class Gate5RegulationSummary(BaseModel):
    """Safe CLI summary for Gate 5 build and verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_count: int
    negative_control_count: int
    gate_5_regulation_passed: bool
    measured_execution_permitted: bool = False
    fixture_sha256: str
    report_sha256: str
