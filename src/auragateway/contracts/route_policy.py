"""Typed Gate 5 route-policy authorization contracts."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.provider import ProviderErrorCode, ProviderName
from auragateway.contracts.route import RouteReason, SessionRouteTransitionRequest

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class ProviderResponseState(StrEnum):
    """Certainty of the provider response state available to route policy."""

    NONE = "none"
    DEFINITE_FAILURE = "definite_failure"
    AMBIGUOUS = "ambiguous"


class RoutePolicyDecisionStatus(StrEnum):
    """Machine authorization result for one proposed route transition."""

    AUTHORIZED = "authorized"
    BLOCKED = "blocked"


class RoutePolicyDecisionCode(StrEnum):
    """Bounded reason code explaining one route-policy authorization result."""

    AUTHORIZED_WARM_PRESERVATION = "AUTHORIZED_WARM_PRESERVATION"
    AUTHORIZED_TTL_EXPIRY = "AUTHORIZED_TTL_EXPIRY"
    AUTHORIZED_PROVIDER_FAILURE_REROUTE = "AUTHORIZED_PROVIDER_FAILURE_REROUTE"
    AUTHORIZED_CAPABILITY_REROUTE = "AUTHORIZED_CAPABILITY_REROUTE"
    AUTHORIZED_SAFETY_REROUTE = "AUTHORIZED_SAFETY_REROUTE"
    AUTHORIZED_QUALITY_REROUTE = "AUTHORIZED_QUALITY_REROUTE"
    AUTHORIZED_SESSION_RESET = "AUTHORIZED_SESSION_RESET"
    AUTHORIZED_BENCHMARK_CONTROL = "AUTHORIZED_BENCHMARK_CONTROL"
    BLOCKED_AMBIGUOUS_RESPONSE = "BLOCKED_AMBIGUOUS_RESPONSE"
    BLOCKED_TTL_EXPIRED = "BLOCKED_TTL_EXPIRED"
    BLOCKED_TTL_NOT_EXPIRED = "BLOCKED_TTL_NOT_EXPIRED"
    BLOCKED_PROVIDER_FAILURE_UNCONFIRMED = "BLOCKED_PROVIDER_FAILURE_UNCONFIRMED"
    BLOCKED_ACTIVE_CAPABILITY_ELIGIBLE = "BLOCKED_ACTIVE_CAPABILITY_ELIGIBLE"
    BLOCKED_ACTIVE_SAFETY_ELIGIBLE = "BLOCKED_ACTIVE_SAFETY_ELIGIBLE"
    BLOCKED_ACTIVE_QUALITY_ELIGIBLE = "BLOCKED_ACTIVE_QUALITY_ELIGIBLE"
    BLOCKED_TARGET_ROUTE_INELIGIBLE = "BLOCKED_TARGET_ROUTE_INELIGIBLE"
    BLOCKED_REASON_STATE_MISMATCH = "BLOCKED_REASON_STATE_MISMATCH"


_AUTHORIZED_REASON_BY_CODE = {
    RoutePolicyDecisionCode.AUTHORIZED_WARM_PRESERVATION: RouteReason.WARM_CACHE_AFFINITY,
    RoutePolicyDecisionCode.AUTHORIZED_TTL_EXPIRY: RouteReason.TTL_EXPIRED,
    RoutePolicyDecisionCode.AUTHORIZED_PROVIDER_FAILURE_REROUTE: RouteReason.PROVIDER_FAILURE,
    RoutePolicyDecisionCode.AUTHORIZED_CAPABILITY_REROUTE: RouteReason.CAPABILITY_REQUIREMENT,
    RoutePolicyDecisionCode.AUTHORIZED_SAFETY_REROUTE: RouteReason.SAFETY_REQUIREMENT,
    RoutePolicyDecisionCode.AUTHORIZED_QUALITY_REROUTE: RouteReason.QUALITY_GUARDRAIL,
    RoutePolicyDecisionCode.AUTHORIZED_SESSION_RESET: RouteReason.SESSION_RESET,
    RoutePolicyDecisionCode.AUTHORIZED_BENCHMARK_CONTROL: RouteReason.BENCHMARK_CONTROL,
}


class RouteEligibilitySnapshot(BaseModel):
    """Metadata-only capability, safety, and quality eligibility for one route."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ProviderName
    model_alias: str
    capability_eligible: bool
    safety_eligible: bool
    quality_eligible: bool

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: ProviderName) -> ProviderName:
        if value is ProviderName.UNAVAILABLE:
            raise ValueError("route eligibility requires an executable provider")
        return value

    @field_validator("model_alias")
    @classmethod
    def validate_model_alias(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("model_alias must use stable lowercase characters")
        return value

    @property
    def fully_eligible(self) -> bool:
        """Return whether the route satisfies every current hard eligibility gate."""

        return self.capability_eligible and self.safety_eligible and self.quality_eligible


class RoutePolicyEvaluationRequest(BaseModel):
    """Deterministic policy inputs for authorizing one proposed state transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    policy_id: str
    policy_version: str
    warm_ttl_seconds: int = Field(gt=0, le=86_400)
    evaluated_at: datetime
    proposed_transition: SessionRouteTransitionRequest
    active_route_eligibility: RouteEligibilitySnapshot
    target_route_eligibility: RouteEligibilitySnapshot | None
    provider_response_state: ProviderResponseState = ProviderResponseState.NONE
    provider_error_code: ProviderErrorCode | None = None

    @field_validator("policy_id", "policy_version")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("policy identifiers must use stable lowercase characters")
        return value

    @field_validator("evaluated_at")
    @classmethod
    def validate_evaluated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy_inputs(self) -> RoutePolicyEvaluationRequest:
        previous_state = self.proposed_transition.previous_state
        active_binding = (
            self.active_route_eligibility.provider,
            self.active_route_eligibility.model_alias,
        )
        if active_binding != (previous_state.active_provider, previous_state.active_model):
            raise ValueError("active eligibility must match the previous active route")

        target_binding = (
            self.proposed_transition.target_provider,
            self.proposed_transition.target_model,
        )
        if target_binding == (None, None):
            if self.target_route_eligibility is not None:
                raise ValueError("unbound target transition must not contain target eligibility")
        else:
            if self.target_route_eligibility is None:
                raise ValueError("bound target transition requires target eligibility")
            eligibility_binding = (
                self.target_route_eligibility.provider,
                self.target_route_eligibility.model_alias,
            )
            if eligibility_binding != target_binding:
                raise ValueError("target eligibility must match the proposed target route")

        if self.provider_response_state is ProviderResponseState.NONE:
            if self.provider_error_code is not None:
                raise ValueError("provider_error_code requires a provider response failure state")
        elif self.provider_error_code is None:
            raise ValueError("provider failure states require provider_error_code")

        evidence_at = self.proposed_transition.cache_evidence_at
        if evidence_at is not None and evidence_at > self.evaluated_at:
            raise ValueError("cache evidence time cannot be later than policy evaluation time")
        return self


class RoutePolicyDecision(BaseModel):
    """Machine-readable authorization or block for one proposed route transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    policy_id: str
    policy_version: str
    evaluated_at: datetime
    status: RoutePolicyDecisionStatus
    decision_code: RoutePolicyDecisionCode
    proposed_reason: RouteReason
    authorized_transition: SessionRouteTransitionRequest | None

    @field_validator("policy_id", "policy_version")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("policy identifiers must use stable lowercase characters")
        return value

    @field_validator("evaluated_at")
    @classmethod
    def validate_evaluated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_decision_shape(self) -> RoutePolicyDecision:
        authorized_code = self.decision_code.value.startswith("AUTHORIZED_")
        if self.status is RoutePolicyDecisionStatus.AUTHORIZED:
            if not authorized_code or self.authorized_transition is None:
                raise ValueError("authorized policy decisions require an authorized transition")
            if self.authorized_transition.reason is not self.proposed_reason:
                raise ValueError("authorized transition reason must match proposed_reason")
            expected_reason = _AUTHORIZED_REASON_BY_CODE.get(self.decision_code)
            if expected_reason is not self.proposed_reason:
                raise ValueError("authorized decision code must match proposed_reason")
        else:
            if authorized_code or self.authorized_transition is not None:
                raise ValueError("blocked policy decisions must not authorize a transition")
        return self
