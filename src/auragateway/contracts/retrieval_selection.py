"""Typed contracts for development-only retrieval candidate selection."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.retrieval_eval import (
    RetrievalAggregateMetrics,
    RetrievalCaseFamily,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class MetadataPolicy(StrEnum):
    """Metadata-filter policies compared during development selection."""

    AUTHORED = "authored-case-filters-v1"
    API_AREA_ONLY = "api-area-only-negative-control-v1"
    NONE = "no-metadata-negative-control-v1"


class SelectionRecommendationStatus(StrEnum):
    """Development recommendation outcome."""

    DEVELOPMENT_RECOMMENDED = "development_recommended"
    NO_ELIGIBLE_CANDIDATE = "no_eligible_candidate"


class CaseFamilyWeights(BaseModel):
    """Failure weights for diagnostic case families."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version_conflict: float = Field(default=3.0, gt=0.0)
    similar_error_codes: float = Field(default=2.0, gt=0.0)
    missing_required_parameters: float = Field(default=3.0, gt=0.0)
    incomplete_documentation: float = Field(default=3.0, gt=0.0)
    near_duplicate_displacement: float = Field(default=2.0, gt=0.0)
    multi_source_grounding: float = Field(default=3.0, gt=0.0)
    metadata_filtering: float = Field(default=3.0, gt=0.0)
    unsupported_behavior: float = Field(default=3.0, gt=0.0)
    exact_procedure: float = Field(default=2.0, gt=0.0)
    sdk_variant: float = Field(default=2.0, gt=0.0)

    def for_family(self, family: RetrievalCaseFamily) -> float:
        """Return the declared weight for one diagnostic family."""

        return float(getattr(self, family.value))


class SelectionBenefitWeights(BaseModel):
    """Weights for positive development metrics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mean_recall_at_k: float = Field(default=0.20, ge=0.0, le=1.0)
    all_required_sources_in_top_k_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    citation_support_readiness_rate: float = Field(default=0.20, ge=0.0, le=1.0)
    mean_reciprocal_rank: float = Field(default=0.10, ge=0.0, le=1.0)
    mean_ndcg_at_k: float = Field(default=0.10, ge=0.0, le=1.0)
    mean_precision_at_k: float = Field(default=0.05, ge=0.0, le=1.0)
    weighted_case_pass_rate: float = Field(default=0.20, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_weight_sum(self) -> SelectionBenefitWeights:
        total = sum(float(value) for value in self.model_dump().values())
        if abs(total - 1.0) > 1e-12:
            raise ValueError("selection benefit weights must sum to one")
        return self


class SelectionPenaltyWeights(BaseModel):
    """Penalty multipliers for unsafe or noisy retrieval behaviour."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unsupported_source_retrieval_rate: float = Field(default=0.20, ge=0.0, le=1.0)
    stale_source_retrieval_rate: float = Field(default=0.25, ge=0.0, le=1.0)
    metadata_filter_violation_rate: float = Field(default=0.30, ge=0.0, le=1.0)
    near_duplicate_displacement_rate: float = Field(default=0.20, ge=0.0, le=1.0)


class PromotionThresholds(BaseModel):
    """Hard development gates required before recommendation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_mean_recall_at_k: float = Field(default=0.98, ge=0.0, le=1.0)
    minimum_correct_source_in_top_k_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    minimum_all_required_sources_in_top_k_rate: float = Field(default=0.95, ge=0.0, le=1.0)
    minimum_citation_support_readiness_rate: float = Field(default=0.90, ge=0.0, le=1.0)
    minimum_mean_reciprocal_rank: float = Field(default=0.95, ge=0.0, le=1.0)
    minimum_weighted_case_pass_rate: float = Field(default=0.90, ge=0.0, le=1.0)
    maximum_unsupported_source_retrieval_rate: float = Field(default=0.11, ge=0.0, le=1.0)
    maximum_stale_source_retrieval_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    maximum_metadata_filter_violation_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    maximum_near_duplicate_displacement_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class RetrievalSelectionPolicy(BaseModel):
    """Frozen development selection policy before variant scoring."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    policy_id: str = "retrieval-development-selection-v1"
    status: str = "development_only"
    top_k_values: tuple[int, ...] = (3, 5, 7)
    metadata_policies: tuple[MetadataPolicy, ...] = (
        MetadataPolicy.AUTHORED,
        MetadataPolicy.API_AREA_ONLY,
        MetadataPolicy.NONE,
    )
    eligible_metadata_policy: MetadataPolicy = MetadataPolicy.AUTHORED
    minimum_top_k: int = 3
    top_k_penalty_per_extra_hit: float = Field(default=0.01, ge=0.0, le=0.1)
    benefit_weights: SelectionBenefitWeights = SelectionBenefitWeights()
    penalty_weights: SelectionPenaltyWeights = SelectionPenaltyWeights()
    thresholds: PromotionThresholds = PromotionThresholds()
    case_family_weights: CaseFamilyWeights = CaseFamilyWeights()
    held_out_validation_required: bool = True
    measured_execution_permitted: bool = False

    @field_validator("top_k_values")
    @classmethod
    def validate_top_k_values(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if not value or any(item < 1 or item > 20 for item in value):
            raise ValueError("top_k_values must contain integers from one to twenty")
        if tuple(sorted(set(value))) != value:
            raise ValueError("top_k_values must be unique and sorted")
        return value

    @field_validator("metadata_policies")
    @classmethod
    def validate_metadata_policies(
        cls, value: tuple[MetadataPolicy, ...]
    ) -> tuple[MetadataPolicy, ...]:
        if len(value) != len(set(value)):
            raise ValueError("metadata_policies must be unique")
        required = {MetadataPolicy.AUTHORED, MetadataPolicy.API_AREA_ONLY, MetadataPolicy.NONE}
        if set(value) != required:
            raise ValueError("selection policy must include authored and both negative controls")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> RetrievalSelectionPolicy:
        if self.minimum_top_k != min(self.top_k_values):
            raise ValueError("minimum_top_k must equal the smallest swept top_k value")
        if self.eligible_metadata_policy not in self.metadata_policies:
            raise ValueError("eligible_metadata_policy must be included in metadata_policies")
        if not self.held_out_validation_required:
            raise ValueError("held-out validation must remain required")
        if self.measured_execution_permitted:
            raise ValueError("development selection cannot permit measured execution")
        return self


class PromotionGateResult(BaseModel):
    """One machine-readable hard-gate decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_id: str
    passed: bool
    observed: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    comparator: str


class RetrievalSelectionVariant(BaseModel):
    """One candidate, top-k, and metadata-policy development result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    variant_id: str
    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    top_k: int = Field(ge=1, le=20)
    metadata_policy: MetadataPolicy
    eligible_for_recommendation: bool
    aggregate: RetrievalAggregateMetrics
    weighted_case_pass_rate: float = Field(ge=0.0, le=1.0)
    weighted_case_failure_rate: float = Field(ge=0.0, le=1.0)
    failed_case_ids: tuple[str, ...]
    gate_results: tuple[PromotionGateResult, ...]
    hard_gate_passed: bool
    benefit_score: float = Field(ge=0.0, le=1.0)
    penalty_score: float = Field(ge=0.0)
    top_k_penalty: float = Field(ge=0.0)
    final_score: float = Field(ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_variant(self) -> RetrievalSelectionVariant:
        if _SHA256_PATTERN.fullmatch(self.retriever_config_sha256) is None:
            raise ValueError("retriever_config_sha256 must be lowercase SHA-256")
        if abs(self.weighted_case_pass_rate + self.weighted_case_failure_rate - 1.0) > 1e-9:
            raise ValueError("weighted case pass and failure rates must sum to one")
        if self.hard_gate_passed != all(result.passed for result in self.gate_results):
            raise ValueError("hard_gate_passed must match all gate results")
        if self.eligible_for_recommendation and self.metadata_policy is not MetadataPolicy.AUTHORED:
            raise ValueError(
                "only authored metadata-policy variants may be recommendation eligible"
            )
        return self


class SelectionScorecardReference(BaseModel):
    """Hash reference to one upstream development scorecard."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    retriever_config_id: str
    scorecard_path: str
    scorecard_sha256: str

    @field_validator("scorecard_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("scorecard_sha256 must be lowercase SHA-256")
        return value


class SelectionRankingEntry(BaseModel):
    """Ranked authored-policy variant."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rank: int = Field(ge=1)
    variant_id: str
    retriever_config_id: str
    chunking_config_id: str
    top_k: int
    hard_gate_passed: bool
    final_score: float


class RetrievalSelectionRecommendation(BaseModel):
    """Development-only recommendation with explicit next gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: SelectionRecommendationStatus
    variant_id: str | None = None
    retriever_config_id: str | None = None
    chunking_config_id: str | None = None
    top_k: int | None = None
    metadata_policy: MetadataPolicy | None = None
    final_score: float | None = None
    rationale: tuple[str, ...] = Field(min_length=1)
    blocked_from_freeze: bool = True
    required_next_gate: str = "held_out_retrieval_validation"

    @model_validator(mode="after")
    def validate_recommendation(self) -> RetrievalSelectionRecommendation:
        candidate_fields = (
            self.variant_id,
            self.retriever_config_id,
            self.chunking_config_id,
            self.top_k,
            self.metadata_policy,
            self.final_score,
        )
        if self.status is SelectionRecommendationStatus.DEVELOPMENT_RECOMMENDED:
            if any(value is None for value in candidate_fields):
                raise ValueError("development recommendation requires complete candidate fields")
        elif any(value is not None for value in candidate_fields):
            raise ValueError("no-eligible-candidate status must not include candidate fields")
        if not self.blocked_from_freeze:
            raise ValueError("development recommendation must remain blocked from freeze")
        return self


class RetrievalSelectionReport(BaseModel):
    """Hash-bound development cross-retriever selection report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str = "nimbus-relay-retrieval-development-selection-v1"
    status: str = "development_recommendation_only"
    selection_policy_path: str
    selection_policy_sha256: str
    retrieval_set_path: str
    retrieval_set_sha256: str
    source_scorecards: tuple[SelectionScorecardReference, ...] = Field(min_length=4, max_length=4)
    variants_path: str
    variants_sha256: str
    variant_count: int = Field(ge=1)
    eligible_variant_count: int = Field(ge=1)
    negative_control_variant_count: int = Field(ge=1)
    rankings: tuple[SelectionRankingEntry, ...] = Field(min_length=1)
    recommendation: RetrievalSelectionRecommendation
    held_out_validation_required: bool = True
    retrieval_freeze_permitted: bool = False

    @model_validator(mode="after")
    def validate_report(self) -> RetrievalSelectionReport:
        for name, value in (
            ("selection_policy_sha256", self.selection_policy_sha256),
            ("retrieval_set_sha256", self.retrieval_set_sha256),
            ("variants_sha256", self.variants_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must be lowercase SHA-256")
        scorecard_ids = [item.retriever_config_id for item in self.source_scorecards]
        duplicates = sorted(value for value, count in Counter(scorecard_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate scorecard references: {', '.join(duplicates)}")
        expected_ranks = tuple(range(1, len(self.rankings) + 1))
        if tuple(item.rank for item in self.rankings) != expected_ranks:
            raise ValueError("ranking entries must be contiguous and start at one")
        if self.variant_count != self.eligible_variant_count + self.negative_control_variant_count:
            raise ValueError("variant counts must reconcile")
        if not self.held_out_validation_required or self.retrieval_freeze_permitted:
            raise ValueError("development report cannot permit retrieval freeze")
        return self


class RetrievalSelectionSummary(BaseModel):
    """Safe CLI build or verification output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str
    variant_count: int
    eligible_variant_count: int
    passing_variant_count: int
    recommendation_status: SelectionRecommendationStatus
    recommended_retriever_config_id: str | None
    recommended_top_k: int | None
    recommended_final_score: float | None
    held_out_validation_required: bool
    retrieval_freeze_permitted: bool
    validation_status: str
