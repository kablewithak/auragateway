"""Typed protected review-execution contracts for Gate 6."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.blinded_quality import (
    AdjudicationRecord,
    QualityReviewRecord,
    ReviewVerdict,
)
from auragateway.contracts.episodes import EpisodeEvaluationSplit, EpisodeFailureLabel

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EPISODE_ID_PATTERN = re.compile(r"^ep-func-[0-9]{3}$")


class FinalReviewSource(StrEnum):
    """Source of the final quality outcome for an episode."""

    PRIMARY = "primary"
    ADJUDICATION = "adjudication"


class ProtectedReviewSubmissionSet(BaseModel):
    """Protected synthetic review submissions bound to frozen assignments."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    execution_id: str = "auragateway-gate-6-protected-review-execution-v1"
    assignment_manifest_id: str
    rubric_id: str
    reviews: tuple[QualityReviewRecord, ...] = Field(min_length=1)
    adjudications: tuple[AdjudicationRecord, ...] = ()
    synthetic_fixture_execution: Literal[True] = True
    human_review_completed: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_submission_set(self) -> ProtectedReviewSubmissionSet:
        review_ids = [review.review_id for review in self.reviews]
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("protected review submissions must have unique review IDs")
        adjudicated_episodes = [record.episode_id for record in self.adjudications]
        if len(adjudicated_episodes) != len(set(adjudicated_episodes)):
            raise ValueError("protected review submissions allow one adjudication per episode")
        return self


class EpisodeReviewOutcome(BaseModel):
    """Metadata-only final review outcome for one functional episode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: str
    evaluation_split: EpisodeEvaluationSplit
    primary_review_id: str
    secondary_review_id: str | None = None
    material_disagreement: bool
    adjudication_applied: bool
    final_source: FinalReviewSource
    final_verdict: ReviewVerdict
    final_total_score: int = Field(ge=7, le=28)
    final_failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    quality_passed: bool

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value

    @model_validator(mode="after")
    def validate_outcome(self) -> EpisodeReviewOutcome:
        if self.quality_passed != (self.final_verdict is ReviewVerdict.PASS):
            raise ValueError("quality_passed must match the final verdict")
        if self.adjudication_applied != (self.final_source is FinalReviewSource.ADJUDICATION):
            raise ValueError("final source must identify whether adjudication was applied")
        if self.adjudication_applied and not self.material_disagreement:
            raise ValueError("adjudication requires material disagreement")
        if self.material_disagreement and not self.adjudication_applied:
            raise ValueError("material disagreement requires adjudication")
        if self.secondary_review_id is None and self.material_disagreement:
            raise ValueError("material disagreement requires a secondary review")
        return self


class ReviewerAgreementMetrics(BaseModel):
    """Metadata-only agreement measurements for the frozen double-review sample."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    double_review_count: int = Field(ge=1)
    verdict_agreement_count: int = Field(ge=0)
    verdict_agreement_rate: float = Field(ge=0.0, le=1.0)
    criterion_comparison_count: int = Field(ge=1)
    exact_criterion_agreement_count: int = Field(ge=0)
    exact_criterion_agreement_rate: float = Field(ge=0.0, le=1.0)
    material_disagreement_count: int = Field(ge=0)
    adjudication_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_metrics(self) -> ReviewerAgreementMetrics:
        if self.verdict_agreement_count > self.double_review_count:
            raise ValueError("verdict agreement count cannot exceed double-review count")
        if self.exact_criterion_agreement_count > self.criterion_comparison_count:
            raise ValueError("exact criterion agreement count cannot exceed comparisons")
        expected_verdict_rate = self.verdict_agreement_count / self.double_review_count
        if abs(self.verdict_agreement_rate - expected_verdict_rate) > 1e-12:
            raise ValueError("verdict agreement rate must reconcile")
        expected_criterion_rate = (
            self.exact_criterion_agreement_count / self.criterion_comparison_count
        )
        if abs(self.exact_criterion_agreement_rate - expected_criterion_rate) > 1e-12:
            raise ValueError("criterion agreement rate must reconcile")
        if self.adjudication_count != self.material_disagreement_count:
            raise ValueError("every material disagreement requires exactly one adjudication")
        return self


class HeldOutQualityAggregate(BaseModel):
    """Metadata-only held-out quality aggregation for the synthetic review set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    held_out_episode_count: int = Field(ge=1)
    pass_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    mean_total_score: float = Field(ge=7.0, le=28.0)
    adjudicated_episode_count: int = Field(ge=0)
    failure_label_counts: dict[str, int]

    @model_validator(mode="after")
    def validate_aggregate(self) -> HeldOutQualityAggregate:
        if self.pass_count + self.fail_count != self.held_out_episode_count:
            raise ValueError("held-out pass and fail counts must reconcile")
        expected_rate = self.pass_count / self.held_out_episode_count
        if abs(self.pass_rate - expected_rate) > 1e-12:
            raise ValueError("held-out pass rate must reconcile")
        if self.adjudicated_episode_count > self.held_out_episode_count:
            raise ValueError("held-out adjudication count cannot exceed episode count")
        if any(count <= 0 for count in self.failure_label_counts.values()):
            raise ValueError("held-out failure-label counts must be positive")
        return self


class Gate6ProtectedReviewExecutionReport(BaseModel):
    """Reproducible metadata-only report for protected review execution controls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    execution_id: str
    assignment_manifest_id: str
    rubric_id: str
    assignment_count: int
    review_count: int
    primary_review_count: int
    secondary_review_count: int
    adjudication_count: int
    assignment_coverage_complete: bool
    secondary_coverage_complete: bool
    adjudication_coverage_complete: bool
    reviewer_independence_verified: bool
    outcomes: tuple[EpisodeReviewOutcome, ...]
    agreement: ReviewerAgreementMetrics
    held_out: HeldOutQualityAggregate
    execution_controls_passed: bool
    synthetic_fixture_execution: Literal[True] = True
    human_review_completed: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_report(self) -> Gate6ProtectedReviewExecutionReport:
        if self.assignment_count != self.review_count:
            raise ValueError("complete review execution requires one review per assignment")
        if self.review_count != self.primary_review_count + self.secondary_review_count:
            raise ValueError("review role counts must reconcile")
        if self.adjudication_count != self.agreement.adjudication_count:
            raise ValueError("adjudication count must match agreement metrics")
        if len(self.outcomes) != self.primary_review_count:
            raise ValueError("one final outcome is required per primary review")
        episode_ids = [outcome.episode_id for outcome in self.outcomes]
        if len(episode_ids) != len(set(episode_ids)):
            raise ValueError("episode outcomes must be unique")
        expected_pass = all(
            (
                self.assignment_coverage_complete,
                self.secondary_coverage_complete,
                self.adjudication_coverage_complete,
                self.reviewer_independence_verified,
            )
        )
        if self.execution_controls_passed != expected_pass:
            raise ValueError("execution control status must match coverage controls")
        return self


class Gate6ProtectedReviewExecutionManifest(BaseModel):
    """Hash-bound inventory for protected review execution evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-6-protected-review-execution-manifest-v1"
    submission_path: str
    submission_sha256: str
    report_path: str
    report_sha256: str
    assignment_path: str
    assignment_sha256: str
    rubric_path: str
    rubric_sha256: str
    episode_manifest_path: str
    episode_manifest_sha256: str
    blinded_quality_manifest_path: str
    blinded_quality_manifest_sha256: str
    assignment_count: int
    review_count: int
    adjudication_count: int
    held_out_episode_count: int
    execution_controls_passed: bool
    synthetic_fixture_execution: Literal[True] = True
    human_review_completed: Literal[False] = False
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_manifest(self) -> Gate6ProtectedReviewExecutionManifest:
        digests = (
            self.submission_sha256,
            self.report_sha256,
            self.assignment_sha256,
            self.rubric_sha256,
            self.episode_manifest_sha256,
            self.blinded_quality_manifest_sha256,
        )
        if any(_SHA256_PATTERN.fullmatch(value) is None for value in digests):
            raise ValueError("manifest digests must be lowercase SHA-256")
        if self.assignment_count != self.review_count:
            raise ValueError("manifest review coverage must be complete")
        if not self.execution_controls_passed:
            raise ValueError("frozen execution manifest requires passing controls")
        return self


class Gate6ProtectedReviewExecutionSummary(BaseModel):
    """Safe CLI summary for protected review execution build or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    execution_id: str
    assignment_count: int
    review_count: int
    adjudication_count: int
    double_review_count: int
    verdict_agreement_rate: float
    exact_criterion_agreement_rate: float
    held_out_episode_count: int
    held_out_pass_count: int
    held_out_pass_rate: float
    execution_controls_passed: bool
    synthetic_fixture_execution: bool
    human_review_completed: bool
    measured_execution_permitted: bool
