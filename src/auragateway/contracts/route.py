"""Typed session-route state and Gate 5 transition contracts."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.provider import ProviderName

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class CacheAffinityStatus(StrEnum):
    """Bounded cache-affinity state used by route-policy decisions."""

    COLD = "cold"
    PLAUSIBLY_WARM = "plausibly_warm"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class RouteReason(StrEnum):
    """Allowed reasons for initializing, preserving, changing, or resetting a route."""

    SESSION_START = "session_start"
    WARM_CACHE_AFFINITY = "warm_cache_affinity"
    TTL_EXPIRED = "ttl_expired"
    PROVIDER_FAILURE = "provider_failure"
    CAPABILITY_REQUIREMENT = "capability_requirement"
    SAFETY_REQUIREMENT = "safety_requirement"
    QUALITY_GUARDRAIL = "quality_guardrail"
    SESSION_RESET = "session_reset"
    BENCHMARK_CONTROL = "benchmark_control"


class RouteTransitionKind(StrEnum):
    """Structural outcome of one deterministic route-state transition."""

    INITIALIZED = "initialized"
    PRESERVED = "preserved"
    CHANGED = "changed"
    RESET = "reset"


class SessionRouteInitialization(BaseModel):
    """Metadata-only request used to create a new cold session route."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    session_id_hash: str
    active_provider: ProviderName
    active_model: str

    @field_validator("session_id_hash")
    @classmethod
    def validate_session_id_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("session_id_hash must be lowercase SHA-256")
        return value

    @field_validator("active_model")
    @classmethod
    def validate_model_alias(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("active_model must use stable lowercase characters")
        return value

    @field_validator("active_provider")
    @classmethod
    def validate_provider(cls, value: ProviderName) -> ProviderName:
        if value is ProviderName.UNAVAILABLE:
            raise ValueError("active_provider must identify an executable route")
        return value


class SessionRouteState(BaseModel):
    """Privacy-safe state for one provider/model route across a session trajectory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    session_id_hash: str
    active_provider: ProviderName | None
    active_model: str | None
    last_cache_evidence_at: datetime | None = None
    cache_affinity_status: CacheAffinityStatus
    route_change_count: int = Field(ge=0)
    last_route_reason: RouteReason

    @field_validator("session_id_hash")
    @classmethod
    def validate_session_id_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("session_id_hash must be lowercase SHA-256")
        return value

    @field_validator("active_model")
    @classmethod
    def validate_model_alias(cls, value: str | None) -> str | None:
        if value is not None and _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("active_model must use stable lowercase characters")
        return value

    @field_validator("last_cache_evidence_at")
    @classmethod
    def validate_timezone_aware_evidence_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("last_cache_evidence_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_route_state(self) -> SessionRouteState:
        has_provider = self.active_provider is not None
        has_model = self.active_model is not None
        if has_provider != has_model:
            raise ValueError("active_provider and active_model must be present or absent together")
        if self.active_provider is ProviderName.UNAVAILABLE:
            raise ValueError("active_provider must identify an executable route")

        if self.cache_affinity_status is CacheAffinityStatus.COLD:
            if self.last_cache_evidence_at is not None:
                raise ValueError("cold route state must not fabricate cache evidence")
        elif self.cache_affinity_status in {
            CacheAffinityStatus.PLAUSIBLY_WARM,
            CacheAffinityStatus.EXPIRED,
        } and (not has_provider or self.last_cache_evidence_at is None):
            raise ValueError(
                "warm or expired route state requires an active route and evidence timestamp"
            )

        if self.last_route_reason is RouteReason.SESSION_START:
            if self.route_change_count != 0:
                raise ValueError("session_start requires route_change_count equal to zero")
            if self.cache_affinity_status is not CacheAffinityStatus.COLD:
                raise ValueError("session_start requires a cold cache-affinity state")
        elif self.last_route_reason is RouteReason.WARM_CACHE_AFFINITY:
            if self.cache_affinity_status is not CacheAffinityStatus.PLAUSIBLY_WARM:
                raise ValueError("warm_cache_affinity requires plausibly_warm state")
        elif self.last_route_reason is RouteReason.TTL_EXPIRED:
            if self.cache_affinity_status is not CacheAffinityStatus.EXPIRED:
                raise ValueError("ttl_expired requires expired state")
        elif self.last_route_reason is RouteReason.SESSION_RESET:
            if has_provider or self.last_cache_evidence_at is not None:
                raise ValueError("session_reset requires an unbound route without cache evidence")
            if self.cache_affinity_status is not CacheAffinityStatus.COLD:
                raise ValueError("session_reset requires a cold cache-affinity state")
        return self


class SessionRouteTransitionRequest(BaseModel):
    """Explicit target state supplied to the deterministic state transition function."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    previous_state: SessionRouteState
    target_provider: ProviderName | None
    target_model: str | None
    target_cache_affinity_status: CacheAffinityStatus
    reason: RouteReason
    cache_evidence_at: datetime | None = None

    @field_validator("target_model")
    @classmethod
    def validate_model_alias(cls, value: str | None) -> str | None:
        if value is not None and _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("target_model must use stable lowercase characters")
        return value

    @field_validator("cache_evidence_at")
    @classmethod
    def validate_timezone_aware_evidence_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("cache_evidence_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_transition_request(self) -> SessionRouteTransitionRequest:
        has_provider = self.target_provider is not None
        has_model = self.target_model is not None
        if has_provider != has_model:
            raise ValueError("target_provider and target_model must be present or absent together")
        if self.target_provider is ProviderName.UNAVAILABLE:
            raise ValueError("target_provider must identify an executable route")
        if self.reason is RouteReason.SESSION_START:
            raise ValueError("session_start is reserved for route initialization")

        previous_binding = (self.previous_state.active_provider, self.previous_state.active_model)
        target_binding = (self.target_provider, self.target_model)
        if self.reason is RouteReason.WARM_CACHE_AFFINITY:
            if target_binding != previous_binding:
                raise ValueError("warm_cache_affinity cannot change the active route")
            if self.target_cache_affinity_status is not CacheAffinityStatus.PLAUSIBLY_WARM:
                raise ValueError("warm_cache_affinity requires plausibly_warm target state")
            if self.cache_evidence_at is None:
                raise ValueError("warm_cache_affinity requires cache evidence time")
        elif self.reason is RouteReason.TTL_EXPIRED:
            if self.target_cache_affinity_status is not CacheAffinityStatus.EXPIRED:
                raise ValueError("ttl_expired requires expired target state")
            if self.cache_evidence_at is None:
                raise ValueError("ttl_expired requires the last cache evidence time")
        elif self.reason is RouteReason.SESSION_RESET:
            if has_provider or self.cache_evidence_at is not None:
                raise ValueError("session_reset must clear route binding and cache evidence")
            if self.target_cache_affinity_status is not CacheAffinityStatus.COLD:
                raise ValueError("session_reset requires cold target state")

        if self.target_cache_affinity_status is CacheAffinityStatus.COLD:
            if self.cache_evidence_at is not None:
                raise ValueError("cold target state must not contain cache evidence")
        elif self.target_cache_affinity_status in {
            CacheAffinityStatus.PLAUSIBLY_WARM,
            CacheAffinityStatus.EXPIRED,
        } and (not has_provider or self.cache_evidence_at is None):
            raise ValueError(
                "warm or expired target state requires an active route and evidence timestamp"
            )
        return self


class SessionRouteTransitionResult(BaseModel):
    """Auditable result of initialization or one explicit state transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    previous_state: SessionRouteState | None
    current_state: SessionRouteState
    transition_kind: RouteTransitionKind
    route_changed: bool
    reason: RouteReason

    @model_validator(mode="after")
    def validate_transition_result(self) -> SessionRouteTransitionResult:
        if self.current_state.last_route_reason is not self.reason:
            raise ValueError("result reason must match current state last_route_reason")
        if self.previous_state is None:
            if self.transition_kind is not RouteTransitionKind.INITIALIZED:
                raise ValueError("missing previous_state requires initialized transition")
            if self.route_changed:
                raise ValueError("route initialization is not counted as a route change")
            if self.reason is not RouteReason.SESSION_START:
                raise ValueError("route initialization requires session_start reason")
            return self

        if self.transition_kind is RouteTransitionKind.INITIALIZED:
            raise ValueError("initialized transition must not contain previous_state")
        if self.previous_state.session_id_hash != self.current_state.session_id_hash:
            raise ValueError("route transition cannot change session_id_hash")

        previous_binding = (
            self.previous_state.active_provider,
            self.previous_state.active_model,
        )
        current_binding = (
            self.current_state.active_provider,
            self.current_state.active_model,
        )
        binding_changed = previous_binding != current_binding
        if self.route_changed != binding_changed:
            raise ValueError("route_changed must match the provider/model binding change")

        expected_count = self.previous_state.route_change_count + int(binding_changed)
        if self.current_state.route_change_count != expected_count:
            raise ValueError("route_change_count must increment exactly once per binding change")

        if self.reason is RouteReason.SESSION_RESET:
            expected_kind = RouteTransitionKind.RESET
        elif binding_changed:
            expected_kind = RouteTransitionKind.CHANGED
        else:
            expected_kind = RouteTransitionKind.PRESERVED
        if self.transition_kind is not expected_kind:
            raise ValueError("transition_kind does not match the structural route outcome")
        return self
