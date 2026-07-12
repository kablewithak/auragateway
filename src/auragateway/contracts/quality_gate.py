"""Typed Gate 6 quality non-inferiority comparison contracts."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMPARISON_ID_PATTERN = re.compile(r"^quality-compare-[a-z0-9-]{3,80}$")
_CASE_ID_PATTERN = re.compile(r"^quality-gate-[a-z0-9-]{3,80}$")


class QualityCondition(StrEnum):
    """Frozen benchmark conditions used by the A/B/C quality gate."""

    A = "condition_a"
    B = "condition_b"
    C = "condition_c"


class QualityGateStatus(StrEnum):
    """Final state of one quality non-inferiority comparison."""

    PASSED = "passed"
    FAILED = "failed"
    INELIGIBLE = "ineligible"
    INSUFFICIENT_SAMPLE = "insufficient_sample"


class QualityGateCheckStatus(StrEnum):
    """Outcome of one bounded gate check."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class QualityGateCheckName(StrEnum):
    """Machine-readable quality-gate checks."""

    RETRIEVAL_CONFIGURATION_MATCH = "retrieval_configuration_match"
    EPISODE_MANIFEST_MATCH = "episode_manifest_match"
    SAMPLE_COUNT_SUFFICIENT = "sample_count_sufficient"
    RATE_DENOMINATORS_SUFFICIENT = "rate_denominators_sufficient"
    STRUCTURED_OUTPUT_VALIDITY = "structured_output_validity"
    CITATION_SUPPORT_NON_REGRESSION = "citation_support_non_regression"
    UNSUPPORTED_ANSWER_NON_REGRESSION = "unsupported_answer_non_regression"
    TASK_SUCCESS_NON_INFERIORITY = "task_success_non_inferiority"


class QualityGateFailureCode(StrEnum):
    """Stable reasons that block or fail the quality gate."""

    RETRIEVAL_CONFIGURATION_MISMATCH = "RETRIEVAL_CONFIGURATION_MISMATCH"
    EPISODE_MANIFEST_MISMATCH = "EPISODE_MANIFEST_MISMATCH"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    INSUFFICIENT_RATE_DENOMINATOR = "INSUFFICIENT_RATE_DENOMINATOR"
    STRUCTURED_OUTPUT_VALIDITY_BELOW_THRESHOLD = "STRUCTURED_OUTPUT_VALIDITY_BELOW_THRESHOLD"
    CITATION_SUPPORT_REGRESSION = "CITATION_SUPPORT_REGRESSION"
    UNSUPPORTED_ANSWER_RATE_INCREASE = "UNSUPPORTED_ANSWER_RATE_INCREASE"
    TASK_SUCCESS_INFERIOR = "TASK_SUCCESS_INFERIOR"


class QualityNonInferiorityThresholds(BaseModel):
    """Frozen Gate 6 thresholds for measured quality comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_sample_count: int = Field(default=30, ge=1)
    minimum_rate_denominator: int = Field(default=1, ge=1)
    structured_output_validity_minimum: float = Field(default=0.95, ge=0.0, le=1.0)
    citation_support_regression_tolerance: float = Field(default=0.0, ge=0.0, le=1.0)
    unsupported_answer_rate_increase_tolerance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )
    task_success_noninferiority_margin: float = Field(default=0.05, ge=0.0, le=1.0)
    baseline_condition: Literal[QualityCondition.A] = QualityCondition.A


class ConditionQualityMetrics(BaseModel):
    """Aggregate metadata-only quality measurements for one condition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_id: QualityCondition
    sample_count: int = Field(ge=0)
    answer_count: int = Field(ge=0)
    structured_output_valid_count: int = Field(ge=0)
    citation_evaluable_count: int = Field(ge=0)
    citation_supported_count: int = Field(ge=0)
    unsupported_answer_count: int = Field(ge=0)
    task_success_count: int = Field(ge=0)
    retrieval_configuration_fingerprint: str
    episode_manifest_sha256: str
    evidence_bundle_sha256: str

    @field_validator(
        "retrieval_configuration_fingerprint",
        "episode_manifest_sha256",
        "evidence_bundle_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("quality metric digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> ConditionQualityMetrics:
        if self.answer_count > self.sample_count:
            raise ValueError("answer_count cannot exceed sample_count")
        if self.structured_output_valid_count > self.sample_count:
            raise ValueError("structured_output_valid_count cannot exceed sample_count")
        if self.citation_evaluable_count > self.sample_count:
            raise ValueError("citation_evaluable_count cannot exceed sample_count")
        if self.citation_supported_count > self.citation_evaluable_count:
            raise ValueError("citation_supported_count cannot exceed citation_evaluable_count")
        if self.unsupported_answer_count > self.answer_count:
            raise ValueError("unsupported_answer_count cannot exceed answer_count")
        if self.task_success_count > self.sample_count:
            raise ValueError("task_success_count cannot exceed sample_count")
        return self


class QualityComparisonInput(BaseModel):
    """One fixed A/B/C quality comparison request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    comparison_id: str
    thresholds: QualityNonInferiorityThresholds = QualityNonInferiorityThresholds()
    conditions: tuple[ConditionQualityMetrics, ...] = Field(min_length=3, max_length=3)
    synthetic_dry_run: Literal[True] = True
    measured_execution_permitted: Literal[False] = False

    @field_validator("comparison_id")
    @classmethod
    def validate_comparison_id(cls, value: str) -> str:
        if _COMPARISON_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("comparison_id must use quality-compare-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_conditions(self) -> QualityComparisonInput:
        condition_ids = [item.condition_id for item in self.conditions]
        if len(condition_ids) != len(set(condition_ids)):
            raise ValueError("quality comparison conditions must be unique")
        if set(condition_ids) != set(QualityCondition):
            raise ValueError("quality comparison requires conditions A, B, and C exactly once")
        return self


class QualityRateSnapshot(BaseModel):
    """Derived bounded rates for one condition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_id: QualityCondition
    sample_count: int
    structured_output_validity_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    citation_support_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    unsupported_answer_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    task_success_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class QualityGateCheckResult(BaseModel):
    """One deterministic comparison check with bounded evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check_name: QualityGateCheckName
    status: QualityGateCheckStatus
    condition_id: QualityCondition | None = None
    failure_code: QualityGateFailureCode | None = None
    observed_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    reference_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    details: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> QualityGateCheckResult:
        if self.status is QualityGateCheckStatus.FAILED and self.failure_code is None:
            raise ValueError("failed quality-gate checks require a failure code")
        if self.status is not QualityGateCheckStatus.FAILED and self.failure_code is not None:
            raise ValueError("non-failed quality-gate checks cannot carry a failure code")
        return self


class QualityNonInferiorityResult(BaseModel):
    """Metadata-only result for one Gate 6 A/B/C comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    comparison_id: str
    status: QualityGateStatus
    eligible_for_quality_comparison: bool
    rates: tuple[QualityRateSnapshot, ...] = Field(min_length=3, max_length=3)
    checks: tuple[QualityGateCheckResult, ...] = Field(min_length=1)
    failure_codes: tuple[QualityGateFailureCode, ...]
    quality_gate_passed: bool
    synthetic_dry_run: Literal[True] = True
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_result(self) -> QualityNonInferiorityResult:
        condition_ids = tuple(item.condition_id for item in self.rates)
        if condition_ids != tuple(QualityCondition):
            raise ValueError("quality result rates must be ordered A, B, C")
        expected_failures = tuple(
            dict.fromkeys(
                check.failure_code for check in self.checks if check.failure_code is not None
            )
        )
        if self.failure_codes != expected_failures:
            raise ValueError("failure_codes must match failed checks in check order")
        if self.quality_gate_passed != (self.status is QualityGateStatus.PASSED):
            raise ValueError("quality_gate_passed must match final status")
        expected_eligible = self.status in {QualityGateStatus.PASSED, QualityGateStatus.FAILED}
        if self.eligible_for_quality_comparison != expected_eligible:
            raise ValueError("comparison eligibility must match final status")
        return self


class QualityGateFixtureCase(BaseModel):
    """One fixed synthetic quality-gate case and expected outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    comparison: QualityComparisonInput
    expected_status: QualityGateStatus
    expected_failure_codes: tuple[QualityGateFailureCode, ...]
    negative_control: bool

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _CASE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("case_id must use quality-gate-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_case(self) -> QualityGateFixtureCase:
        if self.expected_status is QualityGateStatus.PASSED and self.expected_failure_codes:
            raise ValueError("passing quality-gate fixtures must not expect failure codes")
        if self.negative_control != (self.expected_status is not QualityGateStatus.PASSED):
            raise ValueError("negative_control must identify non-passing fixtures")
        return self


class QualityGateFixtureSet(BaseModel):
    """Frozen synthetic dry-run fixtures for Gate 6 comparison behavior."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str = "auragateway-gate-6-quality-noninferiority-v1"
    cases: tuple[QualityGateFixtureCase, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_fixture_set(self) -> QualityGateFixtureSet:
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("quality-gate fixture case IDs must be unique")
        if not any(not item.negative_control for item in self.cases):
            raise ValueError("quality-gate fixtures require passing controls")
        if not any(item.negative_control for item in self.cases):
            raise ValueError("quality-gate fixtures require negative controls")
        return self


class QualityGateFixtureResult(BaseModel):
    """One executed fixture and expectation comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    result: QualityNonInferiorityResult
    expectation_matched: bool
    negative_control: bool


class Gate6QualityNonInferiorityReport(BaseModel):
    """Reproducible dry-run report for the final pre-execution Gate 6 boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    results: tuple[QualityGateFixtureResult, ...]
    fixture_count: int
    negative_control_count: int
    passed_fixture_count: int
    failed_fixture_count: int
    ineligible_fixture_count: int
    insufficient_sample_fixture_count: int
    all_expectations_matched: bool
    quality_gate_dry_run_passed: bool
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_report(self) -> Gate6QualityNonInferiorityReport:
        if self.fixture_count != len(self.results):
            raise ValueError("fixture_count must match quality-gate results")
        if self.negative_control_count != sum(item.negative_control for item in self.results):
            raise ValueError("negative-control count must reconcile")
        counts = {
            QualityGateStatus.PASSED: self.passed_fixture_count,
            QualityGateStatus.FAILED: self.failed_fixture_count,
            QualityGateStatus.INELIGIBLE: self.ineligible_fixture_count,
            QualityGateStatus.INSUFFICIENT_SAMPLE: self.insufficient_sample_fixture_count,
        }
        for status, expected_count in counts.items():
            observed = sum(item.result.status is status for item in self.results)
            if observed != expected_count:
                raise ValueError(f"{status.value} fixture count must reconcile")
        expected_match = all(item.expectation_matched for item in self.results)
        if self.all_expectations_matched != expected_match:
            raise ValueError("all_expectations_matched must reconcile")
        if self.quality_gate_dry_run_passed != expected_match:
            raise ValueError("dry-run gate status must match fixture expectations")
        return self


class Gate6QualityNonInferiorityManifest(BaseModel):
    """Hash-bound inventory for Gate 6 quality comparison dry-run evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-6-quality-noninferiority-manifest-v1"
    fixture_path: str
    fixture_sha256: str
    report_path: str
    report_sha256: str
    deterministic_quality_manifest_path: str
    deterministic_quality_manifest_sha256: str
    protected_review_manifest_path: str
    protected_review_manifest_sha256: str
    fixture_count: int
    negative_control_count: int
    quality_gate_dry_run_passed: bool
    synthetic_dry_run: Literal[True] = True
    measured_execution_permitted: Literal[False] = False

    @field_validator(
        "fixture_sha256",
        "report_sha256",
        "deterministic_quality_manifest_sha256",
        "protected_review_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("quality-gate manifest digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> Gate6QualityNonInferiorityManifest:
        if not self.quality_gate_dry_run_passed:
            raise ValueError("frozen quality-gate manifest requires passing fixtures")
        return self


class Gate6QualityNonInferioritySummary(BaseModel):
    """Safe CLI summary for quality-gate build or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_count: int
    negative_control_count: int
    passed_fixture_count: int
    failed_fixture_count: int
    ineligible_fixture_count: int
    insufficient_sample_fixture_count: int
    quality_gate_dry_run_passed: bool
    synthetic_dry_run: bool
    measured_execution_permitted: bool
    fixture_sha256: str
    report_sha256: str
