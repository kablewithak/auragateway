"""Typed execution-manifest freeze contracts for AuraGateway Phase 7."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class FreezeCheckStatus(StrEnum):
    """One execution-freeze check result."""

    PASSED = "passed"
    FAILED = "failed"


class FreezeFailureCode(StrEnum):
    """Stable execution-freeze failure taxonomy."""

    GATE9_PREFLIGHT_INVALID = "GATE9_PREFLIGHT_INVALID"
    PRICING_SCHEDULE_INVALID = "PRICING_SCHEDULE_INVALID"
    NEGATIVE_CONTROLS_INVALID = "NEGATIVE_CONTROLS_INVALID"
    FAULT_FIXTURES_INVALID = "FAULT_FIXTURES_INVALID"
    PRIVACY_VERIFICATION_FAILED = "PRIVACY_VERIFICATION_FAILED"
    CROSS_CONDITION_ISOLATION_FAILED = "CROSS_CONDITION_ISOLATION_FAILED"
    PROVIDER_PROBE_MISSING = "PROVIDER_PROBE_MISSING"
    PROVIDER_PROBE_FAILED = "PROVIDER_PROBE_FAILED"
    COST_BUDGET_INSUFFICIENT = "COST_BUDGET_INSUFFICIENT"
    IMPLEMENTATION_GIT_SHA_INVALID = "IMPLEMENTATION_GIT_SHA_INVALID"
    EXECUTION_MANIFEST_HASH_MISMATCH = "EXECUTION_MANIFEST_HASH_MISMATCH"
    FREEZE_ARTIFACT_MISMATCH = "FREEZE_ARTIFACT_MISMATCH"


class PricingSchedule(BaseModel):
    """Versioned provider pricing and conservative token ceilings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    pricing_schedule_id: str
    provider_name: Literal["groq"]
    provider_model_alias: Literal["groq-gpt-oss-20b"]
    exact_model_identifier: Literal["openai/gpt-oss-20b"]
    source_url: str
    source_date: date
    currency: Literal["USD"]
    uncached_input_usd_per_million_tokens: Decimal = Field(gt=0)
    cached_input_usd_per_million_tokens: Decimal = Field(gt=0)
    output_usd_per_million_tokens: Decimal = Field(gt=0)
    maximum_input_tokens_per_attempt: int = Field(gt=0, le=16_000)
    maximum_output_tokens_per_attempt: int = Field(gt=0, le=2_048)
    estimate_policy: Literal["uncached-input-worst-case-v1"]
    estimate_status: Literal["versioned_estimate_not_invoice"]

    @model_validator(mode="after")
    def validate_cache_discount(self) -> PricingSchedule:
        if self.cached_input_usd_per_million_tokens >= (self.uncached_input_usd_per_million_tokens):
            raise ValueError("cached input price must be lower than uncached input price")
        return self


class NegativeControlEntry(BaseModel):
    """One predeclared freeze or execution negative control."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    control_id: str
    control_family: str
    injected_condition: str
    expected_failure_code: str
    required_before_execution: bool = True


class NegativeControlManifest(BaseModel):
    """Frozen negative-control inventory required by the execution manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str
    controls: tuple[NegativeControlEntry, ...] = Field(min_length=8)
    all_controls_predeclared: Literal[True] = True
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_controls(self) -> NegativeControlManifest:
        control_ids = [item.control_id for item in self.controls]
        if len(control_ids) != len(set(control_ids)):
            raise ValueError("negative-control IDs must be unique")
        if not all(item.required_before_execution for item in self.controls):
            raise ValueError("all freeze negative controls must be required before execution")
        return self


class FaultInjectionFixture(BaseModel):
    """One deterministic fault injected into the runtime harness."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_id: str
    fault_type: str
    injection_boundary: str
    expected_terminal_state: str
    expected_failure_code: str
    retry_permitted: bool
    evidence_retained: Literal[True] = True


class FaultInjectionFixtureSet(BaseModel):
    """Frozen bounded fault-injection fixture set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    fixtures: tuple[FaultInjectionFixture, ...] = Field(min_length=8)
    raw_provider_payloads_required: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_fixtures(self) -> FaultInjectionFixtureSet:
        fixture_ids = [item.fixture_id for item in self.fixtures]
        if len(fixture_ids) != len(set(fixture_ids)):
            raise ValueError("fault-injection fixture IDs must be unique")
        return self


class PrivacyCheck(BaseModel):
    """One bounded public-evidence privacy check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check_id: str
    passed: bool
    evidence: str


class PrivacyVerificationReport(BaseModel):
    """Metadata-only privacy verification for the execution boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str
    public_root: Literal["evidence_vault"]
    protected_root: Literal[".local"]
    checks: tuple[PrivacyCheck, ...] = Field(min_length=8)
    raw_prompts_public: Literal[False] = False
    raw_user_messages_public: Literal[False] = False
    raw_retrieved_documents_public: Literal[False] = False
    raw_model_outputs_public: Literal[False] = False
    raw_provider_payloads_public: Literal[False] = False
    credentials_public: Literal[False] = False
    protected_review_exports_public: Literal[False] = False
    privacy_verification_passed: bool
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_report(self) -> PrivacyVerificationReport:
        check_ids = [item.check_id for item in self.checks]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("privacy check IDs must be unique")
        expected = all(item.passed for item in self.checks)
        if self.privacy_verification_passed != expected:
            raise ValueError("privacy_verification_passed must match all check outcomes")
        return self


class ProviderReadinessRecord(BaseModel):
    """Sanitized result of the bounded live provider probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    record_id: str
    provider_name: Literal["groq"]
    provider_model_alias: Literal["groq-gpt-oss-20b"]
    provider_adapter_version: Literal["groq-chat-completions-v1"]
    probe_mode: Literal["groq_live"]
    credentials_configured: Literal[True]
    probe_performed: Literal[True]
    probe_passed: Literal[True]
    call_count: int = Field(ge=1, le=2)
    protected_report_path: str
    protected_report_sha256: str
    raw_payload_persisted: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
    observed_at: datetime

    @field_validator("protected_report_path")
    @classmethod
    def validate_protected_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("protected report path must be repository-relative")
        if not value.startswith(".local/provider-calibration/"):
            raise ValueError("provider probe report must remain under .local/provider-calibration")
        return value

    @field_validator("protected_report_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("provider report digest must be lowercase SHA-256")
        return value


class CrossConditionIsolationReport(BaseModel):
    """Deterministic cache-namespace and comparison-pair isolation evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str
    total_trajectory_count: int
    unique_run_id_count: int
    unique_trace_id_count: int
    unique_cache_namespace_count: int
    comparison_pair_count: int
    complete_abc_pair_count: int
    duplicate_run_id_count: int
    duplicate_trace_id_count: int
    duplicate_cache_namespace_count: int
    cross_condition_namespace_reuse_count: int
    isolation_passed: bool
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_counts(self) -> CrossConditionIsolationReport:
        expected = (
            all(
                value == 0
                for value in (
                    self.duplicate_run_id_count,
                    self.duplicate_trace_id_count,
                    self.duplicate_cache_namespace_count,
                    self.cross_condition_namespace_reuse_count,
                )
            )
            and self.complete_abc_pair_count == self.comparison_pair_count
        )
        if self.isolation_passed != expected:
            raise ValueError("isolation_passed must match isolation counts")
        return self


class CostBudgetDecision(BaseModel):
    """Exact conservative cost estimate and operator-approved ceiling."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    decision_id: str
    pricing_schedule_id: str
    maximum_request_attempt_count: int = Field(gt=0)
    maximum_input_tokens_per_attempt: int = Field(gt=0)
    maximum_output_tokens_per_attempt: int = Field(gt=0)
    estimated_upper_bound_minor_units: int = Field(gt=0)
    approved_cost_budget_minor_units: int = Field(gt=0)
    currency: Literal["USD"]
    estimate_uses_uncached_input_price: Literal[True] = True
    budget_sufficient: bool
    estimate_status: Literal["versioned_estimate_not_invoice"]

    @model_validator(mode="after")
    def validate_budget(self) -> CostBudgetDecision:
        expected = self.approved_cost_budget_minor_units >= self.estimated_upper_bound_minor_units
        if self.budget_sufficient != expected:
            raise ValueError("budget_sufficient must match approved and estimated values")
        return self


class FreezeCheckResult(BaseModel):
    """One machine-readable execution-freeze check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check_name: str
    status: FreezeCheckStatus
    failure_code: FreezeFailureCode | None = None
    details: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> FreezeCheckResult:
        if self.status is FreezeCheckStatus.FAILED and self.failure_code is None:
            raise ValueError("failed freeze checks require a failure code")
        if self.status is FreezeCheckStatus.PASSED and self.failure_code is not None:
            raise ValueError("passed freeze checks cannot carry a failure code")
        return self


class ExecutionManifestFreezeReport(BaseModel):
    """Final non-executing Gate 10 freeze decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str
    execution_manifest_id: str
    execution_manifest_sha256: str
    implementation_git_sha: str
    checks: tuple[FreezeCheckResult, ...] = Field(min_length=10)
    failure_codes: tuple[FreezeFailureCode, ...]
    execution_manifest_frozen: bool
    provider_probe_passed: bool
    cost_budget_sufficient: bool
    privacy_verification_passed: bool
    cross_condition_isolation_passed: bool
    gate_10_passed: bool
    measured_execution_permitted: Literal[False] = False

    @field_validator("execution_manifest_sha256")
    @classmethod
    def validate_manifest_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution manifest digest must be lowercase SHA-256")
        return value

    @field_validator("implementation_git_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("implementation Git SHA must be lowercase 40-character hex")
        return value

    @model_validator(mode="after")
    def validate_decision(self) -> ExecutionManifestFreezeReport:
        expected_failures = tuple(
            dict.fromkeys(
                item.failure_code for item in self.checks if item.failure_code is not None
            )
        )
        if self.failure_codes != expected_failures:
            raise ValueError("failure_codes must match failed checks in check order")
        expected_pass = not self.failure_codes and all(
            (
                self.execution_manifest_frozen,
                self.provider_probe_passed,
                self.cost_budget_sufficient,
                self.privacy_verification_passed,
                self.cross_condition_isolation_passed,
            )
        )
        if self.gate_10_passed != expected_pass:
            raise ValueError("gate_10_passed must match all freeze controls")
        return self


class Gate10ExecutionFreezeManifest(BaseModel):
    """Hash-bound inventory for execution-manifest freeze evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-10-execution-freeze-manifest-v1"
    gate9_manifest_path: str
    gate9_manifest_sha256: str
    pricing_schedule_path: str
    pricing_schedule_sha256: str
    negative_control_manifest_path: str
    negative_control_manifest_sha256: str
    fault_injection_fixture_path: str
    fault_injection_fixture_sha256: str
    privacy_verification_report_path: str
    privacy_verification_report_sha256: str
    provider_readiness_path: str
    provider_readiness_sha256: str
    cross_condition_isolation_path: str
    cross_condition_isolation_sha256: str
    cost_budget_decision_path: str
    cost_budget_decision_sha256: str
    execution_manifest_path: str
    execution_manifest_file_sha256: str
    execution_manifest_canonical_sha256: str
    freeze_report_path: str
    freeze_report_sha256: str
    implementation_git_sha: str
    gate_10_passed: Literal[True]
    execution_enabled: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @field_validator(
        "gate9_manifest_sha256",
        "pricing_schedule_sha256",
        "negative_control_manifest_sha256",
        "fault_injection_fixture_sha256",
        "privacy_verification_report_sha256",
        "provider_readiness_sha256",
        "cross_condition_isolation_sha256",
        "cost_budget_decision_sha256",
        "execution_manifest_file_sha256",
        "execution_manifest_canonical_sha256",
        "freeze_report_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("Gate 10 artifact digests must be lowercase SHA-256")
        return value

    @field_validator("implementation_git_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("implementation Git SHA must be lowercase 40-character hex")
        return value


class ExecutionFreezeSummary(BaseModel):
    """Safe CLI summary for validate, probe, freeze, and verify."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: str
    provider_probe_passed: bool
    execution_manifest_frozen: bool
    gate_10_passed: bool
    approved_cost_budget_minor_units: int | None = None
    estimated_upper_bound_minor_units: int | None = None
    currency: str | None = None
    execution_manifest_sha256: str | None = None
    implementation_git_sha: str | None = None
    measured_execution_permitted: Literal[False] = False
