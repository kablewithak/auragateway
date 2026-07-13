"""Typed contracts for privacy-safe Groq cache telemetry capture."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.provider import ProviderName
from auragateway.contracts.telemetry import CachedInputDetailTelemetry

_VERSION_PATTERN = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class BillingCacheObservationState(StrEnum):
    """Observed state of the provider billing-cache field."""

    FIELD_ABSENT = "field_absent"
    FIELD_NULL = "field_null"
    OBSERVED_ZERO = "observed_zero"
    OBSERVED_POSITIVE = "observed_positive"


class CacheMeasurementClaimKind(StrEnum):
    """Claims controlled by the capture sufficiency gate."""

    PROVIDER_CACHE_USAGE = "provider_cache_usage"
    PROVIDER_CACHE_SAVINGS = "provider_cache_savings"


class CacheMeasurementDecision(StrEnum):
    """Machine-readable cache claim decision."""

    PERMITTED = "permitted"
    BLOCKED = "blocked"


class CacheMeasurementReasonCode(StrEnum):
    """Bounded reason taxonomy for cache capture decisions."""

    CLAIM_PERMITTED = "CLAIM_PERMITTED"
    BILLING_CACHE_FIELD_ABSENT = "BILLING_CACHE_FIELD_ABSENT"
    BILLING_CACHE_FIELD_NULL = "BILLING_CACHE_FIELD_NULL"
    INPUT_DENOMINATOR_UNAVAILABLE = "INPUT_DENOMINATOR_UNAVAILABLE"
    CACHE_TOKENS_EXCEED_INPUT = "CACHE_TOKENS_EXCEED_INPUT"
    PROVIDER_IDENTITY_MISMATCH = "PROVIDER_IDENTITY_MISMATCH"
    PRICING_EVIDENCE_UNAVAILABLE = "PRICING_EVIDENCE_UNAVAILABLE"


class CalibrationDraftStatus(StrEnum):
    """Lifecycle state of the prepared three-call calibration."""

    DRAFT_INACTIVE = "draft_inactive"


class CalibrationRequestRole(StrEnum):
    """Predeclared role of one calibration request."""

    COLD = "cold"
    WARM_REPEAT_ONE = "warm_repeat_one"
    WARM_REPEAT_TWO = "warm_repeat_two"


class CacheTelemetryHardeningStatus(StrEnum):
    """Lifecycle state of the non-live hardening acceptance record."""

    IMPLEMENTATION_READY = "implementation_ready"


class GroqCacheTelemetryCapture(BaseModel):
    """Content-free successful-response cache telemetry shape."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    fixture_id: str
    provider: Literal[ProviderName.GROQ] = ProviderName.GROQ
    model_alias: str
    adapter_version: Literal["groq-chat-completions-v1"] = "groq-chat-completions-v1"
    capture_version: Literal["groq-cache-telemetry-capture-v1"] = "groq-cache-telemetry-capture-v1"
    installed_sdk_version: str = Field(min_length=1, max_length=64)
    usage_present: bool
    prompt_tokens_details_present: bool
    billing_cached_tokens_field_present: bool
    billing_cached_input_tokens: int | None = Field(default=None, ge=0)
    x_groq_present: bool
    x_groq_usage_present: bool
    dram_cached_tokens_field_present: bool
    dram_cached_tokens: int | None = Field(default=None, ge=0)
    sram_cached_tokens_field_present: bool
    sram_cached_tokens: int | None = Field(default=None, ge=0)

    @field_validator("fixture_id")
    @classmethod
    def validate_fixture_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("fixture IDs require stable lowercase characters")
        return value

    @field_validator("installed_sdk_version")
    @classmethod
    def validate_sdk_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("installed SDK version contains unsafe characters")
        return value

    @model_validator(mode="after")
    def validate_presence_relationships(self) -> GroqCacheTelemetryCapture:
        if self.prompt_tokens_details_present and not self.usage_present:
            raise ValueError("prompt token details require usage presence")
        if self.billing_cached_tokens_field_present and not self.prompt_tokens_details_present:
            raise ValueError("billing cache field requires prompt token details")
        if (
            self.billing_cached_input_tokens is not None
            and not self.billing_cached_tokens_field_present
        ):
            raise ValueError("billing cache value requires field presence")
        if self.x_groq_usage_present and not self.x_groq_present:
            raise ValueError("x_groq usage requires x_groq presence")
        if (
            self.dram_cached_tokens_field_present or self.sram_cached_tokens_field_present
        ) and not self.x_groq_usage_present:
            raise ValueError("hardware cache fields require x_groq usage")
        if self.dram_cached_tokens is not None and not self.dram_cached_tokens_field_present:
            raise ValueError("DRAM cache value requires field presence")
        if self.sram_cached_tokens is not None and not self.sram_cached_tokens_field_present:
            raise ValueError("SRAM cache value requires field presence")
        return self

    @property
    def billing_observation_state(self) -> BillingCacheObservationState:
        """Return absence, null, measured zero, or measured positive."""

        if not self.billing_cached_tokens_field_present:
            return BillingCacheObservationState.FIELD_ABSENT
        if self.billing_cached_input_tokens is None:
            return BillingCacheObservationState.FIELD_NULL
        if self.billing_cached_input_tokens == 0:
            return BillingCacheObservationState.OBSERVED_ZERO
        return BillingCacheObservationState.OBSERVED_POSITIVE


ProviderSuccessTelemetryShape: TypeAlias = GroqCacheTelemetryCapture


class CacheMeasurementDecisionRecord(BaseModel):
    """One cache claim decision with bounded evidence diagnostics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: CacheMeasurementClaimKind
    decision: CacheMeasurementDecision
    reason_code: CacheMeasurementReasonCode
    required_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_decision(self) -> CacheMeasurementDecisionRecord:
        if self.decision is CacheMeasurementDecision.PERMITTED and (
            self.reason_code is not CacheMeasurementReasonCode.CLAIM_PERMITTED
            or self.missing_fields
            or self.invalid_fields
        ):
            raise ValueError("permitted cache claims require complete valid evidence")
        if (
            self.decision is CacheMeasurementDecision.BLOCKED
            and self.reason_code is CacheMeasurementReasonCode.CLAIM_PERMITTED
        ):
            raise ValueError("blocked cache claims require a blocking reason")
        return self


class GroqCacheTelemetrySufficiencyReport(BaseModel):
    """Independent provider-cache usage and savings decisions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_id: str
    billing_observation_state: BillingCacheObservationState
    valid_input_denominator: bool
    hardware_cache_signal_present: bool
    decisions: tuple[CacheMeasurementDecisionRecord, ...] = Field(
        min_length=2,
        max_length=2,
    )

    @model_validator(mode="after")
    def validate_complete_decisions(self) -> GroqCacheTelemetrySufficiencyReport:
        kinds = [item.claim_kind for item in self.decisions]
        if set(kinds) != set(CacheMeasurementClaimKind):
            raise ValueError("cache sufficiency requires both claim decisions")
        if len(kinds) != len(set(kinds)):
            raise ValueError("cache sufficiency decisions must be unique")
        return self

    def decision_for(
        self,
        claim_kind: CacheMeasurementClaimKind,
    ) -> CacheMeasurementDecisionRecord:
        """Return one required cache claim decision."""

        return next(item for item in self.decisions if item.claim_kind is claim_kind)


class CacheTelemetryCalibrationStep(BaseModel):
    """One predeclared request in the inactive calibration draft."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence_index: int = Field(ge=0, le=2)
    request_role: CalibrationRequestRole
    exact_provider_request_required: Literal[True] = True


class CacheTelemetryCalibrationDraft(BaseModel):
    """Inactive three-call cold-warm-repeat calibration plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    calibration_id: Literal["groq-cache-telemetry-calibration-v1"]
    status: Literal[CalibrationDraftStatus.DRAFT_INACTIVE] = CalibrationDraftStatus.DRAFT_INACTIVE
    provider: Literal[ProviderName.GROQ] = ProviderName.GROQ
    model_alias: Literal["groq-gpt-oss-20b"] = "groq-gpt-oss-20b"
    exact_model_identifier: Literal["openai/gpt-oss-20b"] = "openai/gpt-oss-20b"
    steps: tuple[CacheTelemetryCalibrationStep, ...] = Field(
        min_length=3,
        max_length=3,
    )
    maximum_provider_calls: Literal[3] = 3
    retry_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    provider_call_authorized: Literal[False] = False
    calibration_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    next_gate: Literal["cache_telemetry_calibration_authorization_review"] = (
        "cache_telemetry_calibration_authorization_review"
    )

    @model_validator(mode="after")
    def validate_sequence(self) -> CacheTelemetryCalibrationDraft:
        if [item.sequence_index for item in self.steps] != [0, 1, 2]:
            raise ValueError("calibration sequence indexes must be contiguous")
        if [item.request_role for item in self.steps] != list(CalibrationRequestRole):
            raise ValueError("calibration requires cold, warm one, and warm two")
        return self


class CacheTelemetrySourceBinding(BaseModel):
    """One immutable local source bound by Git blob identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    git_blob_sha1: str

    @field_validator("git_blob_sha1")
    @classmethod
    def validate_git_blob_sha1(cls, value: str) -> str:
        if re.fullmatch(r"[0-9a-f]{40}", value) is None:
            raise ValueError("source bindings require lowercase Git blob SHA-1")
        return value


class CacheTelemetryHardeningAction(BaseModel):
    """One completed non-live hardening action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str
    completed: Literal[True] = True
    provider_call_required: Literal[False] = False

    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("action IDs require stable lowercase characters")
        return value


class CacheTelemetryHardeningAcceptance(BaseModel):
    """Machine-readable acceptance record for the hardening slice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    hardening_id: Literal["groq-cache-telemetry-hardening-v1"]
    status: Literal[CacheTelemetryHardeningStatus.IMPLEMENTATION_READY] = (
        CacheTelemetryHardeningStatus.IMPLEMENTATION_READY
    )
    source_review_id: Literal["cache-telemetry-sufficiency-review-v1"]
    source_commit: Literal["e508655e33acbf544b040f2b6fdea1e2a4fe7a25"]
    source_bindings: tuple[CacheTelemetrySourceBinding, ...] = Field(
        min_length=2,
        max_length=2,
    )
    actions: tuple[CacheTelemetryHardeningAction, ...] = Field(
        min_length=6,
        max_length=6,
    )
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    calibration_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    next_gate: Literal["cache_telemetry_calibration_authorization_review"] = (
        "cache_telemetry_calibration_authorization_review"
    )

    @model_validator(mode="after")
    def validate_action_set(self) -> CacheTelemetryHardeningAcceptance:
        expected = {
            "capture-installed-groq-sdk-version",
            "capture-success-response-presence-bits",
            "separate-billing-and-hardware-cache-semantics",
            "retain-safe-success-telemetry-shape",
            "add-cache-telemetry-sufficiency-gate",
            "prepare-three-call-calibration-review",
        }
        observed = [item.action_id for item in self.actions]
        if set(observed) != expected or len(observed) != len(set(observed)):
            raise ValueError("hardening acceptance requires the six reviewed actions")
        expected_paths = {
            "data/evals/benchmark/cache-telemetry-review-v1/review.json",
            "data/evals/benchmark/cache-telemetry-review-v1/manifest.json",
        }
        observed_paths = [item.path for item in self.source_bindings]
        if set(observed_paths) != expected_paths or len(observed_paths) != len(set(observed_paths)):
            raise ValueError("hardening acceptance requires both review bindings")
        return self


class CacheTelemetryHardeningSummary(BaseModel):
    """Metadata-safe hardening validation summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    hardening_id: str
    status: CacheTelemetryHardeningStatus
    completed_action_count: Literal[6] = 6
    synthetic_case_count: int = Field(ge=1)
    synthetic_cases_passed: bool
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    calibration_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    next_gate: Literal["cache_telemetry_calibration_authorization_review"] = (
        "cache_telemetry_calibration_authorization_review"
    )


class CacheTelemetrySyntheticCase(BaseModel):
    """One deterministic cache capture sufficiency case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    capture: GroqCacheTelemetryCapture
    telemetry: CachedInputDetailTelemetry
    pricing_evidence_available: bool = False
    expected_usage_decision: CacheMeasurementDecision
    expected_usage_reason: CacheMeasurementReasonCode
    expected_savings_decision: CacheMeasurementDecision
    expected_savings_reason: CacheMeasurementReasonCode

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("case IDs require stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> CacheTelemetrySyntheticCase:
        if self.case_id != self.capture.fixture_id or self.case_id != self.telemetry.fixture_id:
            raise ValueError("case, capture, and telemetry fixture IDs must match")
        return self


class CacheTelemetrySyntheticCaseSet(BaseModel):
    """Frozen deterministic cache capture cases."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    fixture_set_id: Literal["groq-cache-telemetry-capture-cases-v1"]
    cases: tuple[CacheTelemetrySyntheticCase, ...] = Field(min_length=6)

    @model_validator(mode="after")
    def validate_unique_cases(self) -> CacheTelemetrySyntheticCaseSet:
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("synthetic cache capture case IDs must be unique")
        return self


class CacheTelemetryHardeningManifest(BaseModel):
    """Integrity manifest for non-live hardening evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    hardening_id: Literal["groq-cache-telemetry-hardening-v1"]
    acceptance_path: Literal["data/evals/benchmark/cache-telemetry-hardening-v1/acceptance.json"]
    acceptance_sha256: str
    calibration_draft_path: Literal[
        "data/evals/benchmark/cache-telemetry-hardening-v1/calibration_draft.json"
    ]
    calibration_draft_sha256: str
    synthetic_cases_path: Literal[
        "data/evals/benchmark/cache-telemetry-hardening-v1/synthetic_cases.json"
    ]
    synthetic_cases_sha256: str
    report_path: Literal["docs/benchmark/AuraGateway_Groq_Cache_Telemetry_Capture_Hardening.md"]
    report_sha256: str
    provider_call_performed: Literal[False] = False
    calibration_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    next_gate: Literal["cache_telemetry_calibration_authorization_review"] = (
        "cache_telemetry_calibration_authorization_review"
    )

    @field_validator(
        "acceptance_sha256",
        "calibration_draft_sha256",
        "synthetic_cases_sha256",
        "report_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("hardening manifest requires lowercase SHA-256")
        return value
