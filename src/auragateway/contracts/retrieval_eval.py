"""Typed contracts for development and held-out retrieval evaluation."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.retrieval import RetrievalFilter

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_DEVELOPMENT_CASE_ID_PATTERN = re.compile(r"^dev-ret-[0-9]{3}$")
_HELD_OUT_CASE_ID_PATTERN = re.compile(r"^ho-ret-[0-9]{3}$")
_SOURCE_ID_PATTERN = re.compile(r"^NR-[A-Z][A-Z0-9-]*-[0-9]{3}$")


class EvaluationSplit(StrEnum):
    """Protected evaluation split identity."""

    DEVELOPMENT = "development"
    HELD_OUT = "held_out"


class TerminalDecision(StrEnum):
    """Expected terminal task decision enabled by retrieved evidence."""

    ANSWER = "answer"
    CLARIFY = "clarify"
    ESCALATE = "escalate"
    REFUSE = "refuse"


class RetrievalCaseFamily(StrEnum):
    """Diagnostic retrieval-case families used in the development set."""

    VERSION_CONFLICT = "version_conflict"
    SIMILAR_ERROR_CODES = "similar_error_codes"
    MISSING_REQUIRED_PARAMETERS = "missing_required_parameters"
    INCOMPLETE_DOCUMENTATION = "incomplete_documentation"
    NEAR_DUPLICATE_DISPLACEMENT = "near_duplicate_displacement"
    MULTI_SOURCE_GROUNDING = "multi_source_grounding"
    METADATA_FILTERING = "metadata_filtering"
    UNSUPPORTED_BEHAVIOR = "unsupported_behavior"
    EXACT_PROCEDURE = "exact_procedure"
    SDK_VARIANT = "sdk_variant"


class RejectedCaseReasonCode(StrEnum):
    """Why a proposed diagnostic case was rejected."""

    TRIVIAL = "trivial"
    AMBIGUOUS = "ambiguous"
    DUPLICATE = "duplicate"
    UNGROUNDED = "ungrounded"
    NON_DIAGNOSTIC = "non_diagnostic"
    PRIVACY_UNSAFE = "privacy_unsafe"


class SourceRelevanceJudgment(BaseModel):
    """Grounded source-level relevance label for one retrieval case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    grade: int = Field(ge=1, le=3)
    rationale: str = Field(min_length=10, max_length=500)

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        if _SOURCE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("source_id must match NR-<AREA>-<NNN>")
        return value


class RetrievalEvaluationCase(BaseModel):
    """One accepted, grounded, diagnostic retrieval case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    case_family: RetrievalCaseFamily
    failure_hypothesis: str = Field(min_length=20, max_length=500)
    query_text: str = Field(min_length=5, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: RetrievalFilter = RetrievalFilter()
    relevance_judgments: tuple[SourceRelevanceJudgment, ...] = Field(min_length=1)
    required_sources: tuple[str, ...] = Field(min_length=1)
    forbidden_sources: tuple[str, ...] = ()
    near_duplicate_sources: tuple[str, ...] = ()
    expected_terminal_decision: TerminalDecision
    required_information_gain: tuple[str, ...] = Field(min_length=1)
    acceptable_variants: tuple[str, ...] = Field(min_length=1)
    failure_labels: tuple[str, ...] = Field(min_length=1)
    accept_reason: str = Field(min_length=20, max_length=500)
    difficulty_reason: str = Field(min_length=20, max_length=500)
    evaluation_split: EvaluationSplit = EvaluationSplit.DEVELOPMENT

    @field_validator(
        "required_sources",
        "forbidden_sources",
        "near_duplicate_sources",
        "required_information_gain",
        "acceptable_variants",
        "failure_labels",
    )
    @classmethod
    def require_unique_non_blank_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("tuple values must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("tuple values must be unique")
        return normalized

    @field_validator("query_text")
    @classmethod
    def normalize_query_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query_text must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_case(self) -> RetrievalEvaluationCase:
        relevance_ids = [item.source_id for item in self.relevance_judgments]
        duplicates = sorted(
            source_id for source_id, count in Counter(relevance_ids).items() if count > 1
        )
        if duplicates:
            raise ValueError(f"duplicate relevance source IDs: {', '.join(duplicates)}")

        relevance_by_source = {item.source_id: item.grade for item in self.relevance_judgments}
        unknown_required = sorted(set(self.required_sources) - set(relevance_by_source))
        if unknown_required:
            raise ValueError(
                "required sources must have relevance judgments: " + ", ".join(unknown_required)
            )
        low_grade_required = sorted(
            source_id for source_id in self.required_sources if relevance_by_source[source_id] < 2
        )
        if low_grade_required:
            raise ValueError(
                "required sources must have relevance grade two or three: "
                + ", ".join(low_grade_required)
            )
        if set(self.forbidden_sources) & set(relevance_by_source):
            raise ValueError("forbidden sources cannot also be relevant")
        if set(self.required_sources) & set(self.forbidden_sources):
            raise ValueError("required and forbidden sources must not overlap")
        if set(self.required_sources) & set(self.near_duplicate_sources):
            raise ValueError("required and near-duplicate displacement sources must not overlap")
        pattern = (
            _DEVELOPMENT_CASE_ID_PATTERN
            if self.evaluation_split is EvaluationSplit.DEVELOPMENT
            else _HELD_OUT_CASE_ID_PATTERN
        )
        expected = (
            "dev-ret-<NNN>"
            if self.evaluation_split is EvaluationSplit.DEVELOPMENT
            else "ho-ret-<NNN>"
        )
        if pattern.fullmatch(self.case_id) is None:
            raise ValueError(f"case_id must match {expected} for the selected evaluation split")
        return self


class DevelopmentRetrievalSet(BaseModel):
    """Versioned accepted development retrieval set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    retrieval_set_id: str = Field(min_length=3, max_length=100)
    retrieval_set_version: str = Field(min_length=1, max_length=32)
    status: str = "accepted_development"
    evaluation_split: EvaluationSplit = EvaluationSplit.DEVELOPMENT
    cases: tuple[RetrievalEvaluationCase, ...] = Field(min_length=24, max_length=24)

    @model_validator(mode="after")
    def validate_set(self) -> DevelopmentRetrievalSet:
        case_ids = [case.case_id for case in self.cases]
        queries = [case.query_text.casefold() for case in self.cases]
        for label, values in (("case IDs", case_ids), ("query texts", queries)):
            duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
            if duplicates:
                raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")

        if self.evaluation_split is not EvaluationSplit.DEVELOPMENT:
            raise ValueError("development retrieval set must use the development split")
        if any(case.evaluation_split is not EvaluationSplit.DEVELOPMENT for case in self.cases):
            raise ValueError("development retrieval set contains a non-development case")

        required_families = {
            RetrievalCaseFamily.VERSION_CONFLICT,
            RetrievalCaseFamily.SIMILAR_ERROR_CODES,
            RetrievalCaseFamily.MISSING_REQUIRED_PARAMETERS,
            RetrievalCaseFamily.INCOMPLETE_DOCUMENTATION,
            RetrievalCaseFamily.NEAR_DUPLICATE_DISPLACEMENT,
            RetrievalCaseFamily.MULTI_SOURCE_GROUNDING,
            RetrievalCaseFamily.UNSUPPORTED_BEHAVIOR,
        }
        present_families = {case.case_family for case in self.cases}
        missing_families = sorted(family.value for family in required_families - present_families)
        if missing_families:
            raise ValueError(
                "development set is missing required case families: " + ", ".join(missing_families)
            )
        return self


class HeldOutRetrievalSet(BaseModel):
    """Frozen accepted held-out retrieval set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    retrieval_set_id: str = Field(min_length=3, max_length=100)
    retrieval_set_version: str = Field(min_length=1, max_length=32)
    status: str = "frozen_held_out"
    evaluation_split: EvaluationSplit = EvaluationSplit.HELD_OUT
    development_set_path: str
    development_set_sha256: str
    authoring_complete_before_evaluation: bool = True
    cases: tuple[RetrievalEvaluationCase, ...] = Field(min_length=12, max_length=12)

    @model_validator(mode="after")
    def validate_set(self) -> HeldOutRetrievalSet:
        if self.evaluation_split is not EvaluationSplit.HELD_OUT:
            raise ValueError("held-out retrieval set must use the held-out split")
        if any(case.evaluation_split is not EvaluationSplit.HELD_OUT for case in self.cases):
            raise ValueError("held-out retrieval set contains a non-held-out case")
        if _SHA256_PATTERN.fullmatch(self.development_set_sha256) is None:
            raise ValueError("development_set_sha256 must contain lowercase SHA-256")
        if not self.authoring_complete_before_evaluation:
            raise ValueError("held-out authoring must complete before candidate evaluation")

        case_ids = [case.case_id for case in self.cases]
        queries = [case.query_text.casefold() for case in self.cases]
        for label, values in (("case IDs", case_ids), ("query texts", queries)):
            duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
            if duplicates:
                raise ValueError(f"duplicate held-out {label}: {', '.join(duplicates)}")

        required_families = {
            RetrievalCaseFamily.VERSION_CONFLICT,
            RetrievalCaseFamily.INCOMPLETE_DOCUMENTATION,
            RetrievalCaseFamily.NEAR_DUPLICATE_DISPLACEMENT,
            RetrievalCaseFamily.MULTI_SOURCE_GROUNDING,
            RetrievalCaseFamily.EXACT_PROCEDURE,
            RetrievalCaseFamily.SDK_VARIANT,
        }
        present_families = {case.case_family for case in self.cases}
        missing_families = sorted(family.value for family in required_families - present_families)
        if missing_families:
            raise ValueError(
                "held-out set is missing required case families: " + ", ".join(missing_families)
            )
        return self


class RejectedRetrievalCase(BaseModel):
    """One rejected proposed case with a retained diagnostic reason."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_case_id: str = Field(min_length=3, max_length=80)
    case_family: RetrievalCaseFamily | None = None
    candidate_query_text: str = Field(min_length=1, max_length=2000)
    reason_code: RejectedCaseReasonCode
    reject_reason: str = Field(min_length=20, max_length=500)
    duplicate_of_case_id: str | None = None
    evaluation_split: EvaluationSplit = EvaluationSplit.DEVELOPMENT

    @model_validator(mode="after")
    def validate_rejection(self) -> RejectedRetrievalCase:
        if (
            self.reason_code is RejectedCaseReasonCode.DUPLICATE
            and self.duplicate_of_case_id is None
        ):
            raise ValueError("duplicate rejections require duplicate_of_case_id")
        if self.reason_code is not RejectedCaseReasonCode.DUPLICATE and self.duplicate_of_case_id:
            raise ValueError("duplicate_of_case_id is allowed only for duplicate rejections")
        return self


class RejectedRetrievalSet(BaseModel):
    """Rejected proposed cases retained to preserve eval-design evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    rejected_set_id: str = Field(min_length=3, max_length=100)
    status: str = "rejected_development_candidates"
    cases: tuple[RejectedRetrievalCase, ...] = Field(min_length=5)

    @model_validator(mode="after")
    def validate_rejected_set(self) -> RejectedRetrievalSet:
        candidate_ids = [case.candidate_case_id for case in self.cases]
        duplicates = sorted(value for value, count in Counter(candidate_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate rejected candidate IDs: {', '.join(duplicates)}")
        return self


class HeldOutRejectedRetrievalSet(BaseModel):
    """Rejected held-out proposals retained before candidate evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    rejected_set_id: str = Field(min_length=3, max_length=100)
    status: str = "rejected_held_out_candidates"
    evaluation_split: EvaluationSplit = EvaluationSplit.HELD_OUT
    cases: tuple[RejectedRetrievalCase, ...] = Field(min_length=5)

    @model_validator(mode="after")
    def validate_rejected_set(self) -> HeldOutRejectedRetrievalSet:
        if any(case.evaluation_split is not EvaluationSplit.HELD_OUT for case in self.cases):
            raise ValueError("held-out rejected set contains a non-held-out proposal")
        candidate_ids = [case.candidate_case_id for case in self.cases]
        duplicates = sorted(value for value, count in Counter(candidate_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate held-out rejected candidate IDs: {', '.join(duplicates)}")
        return self


class RetrievalCaseMetrics(BaseModel):
    """Deterministic metric result for one development retrieval case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    case_id: str
    case_family: RetrievalCaseFamily
    query_sha256: str
    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    top_k: int
    returned_hit_count: int = Field(ge=0)
    ranked_hit_source_ids: tuple[str, ...]
    ranked_unique_source_ids: tuple[str, ...]
    required_sources_found: tuple[str, ...]
    missing_required_sources: tuple[str, ...]
    forbidden_sources_found: tuple[str, ...]
    relevant_sources_found: tuple[str, ...]
    metadata_filter_violation_chunk_ids: tuple[str, ...]
    recall_at_k: float = Field(ge=0.0, le=1.0)
    precision_at_k: float = Field(ge=0.0, le=1.0)
    reciprocal_rank: float = Field(ge=0.0, le=1.0)
    ndcg_at_k: float = Field(ge=0.0, le=1.0)
    correct_source_in_top_k: bool
    all_required_sources_in_top_k: bool
    citation_support_ready: bool
    unsupported_source_retrieval_rate: float = Field(ge=0.0, le=1.0)
    stale_source_retrieval_rate: float = Field(ge=0.0, le=1.0)
    metadata_filter_violation_rate: float = Field(ge=0.0, le=1.0)
    near_duplicate_displacement: bool

    @model_validator(mode="after")
    def validate_hashes_and_counts(self) -> RetrievalCaseMetrics:
        for name, value in (
            ("query_sha256", self.query_sha256),
            ("retriever_config_sha256", self.retriever_config_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
        if self.returned_hit_count != len(self.ranked_hit_source_ids):
            raise ValueError("returned_hit_count must match ranked_hit_source_ids")
        return self


class RetrievalAggregateMetrics(BaseModel):
    """Aggregate metrics for one retrieval candidate across the development set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_count: int = Field(ge=1)
    mean_recall_at_k: float = Field(ge=0.0, le=1.0)
    mean_precision_at_k: float = Field(ge=0.0, le=1.0)
    mean_reciprocal_rank: float = Field(ge=0.0, le=1.0)
    mean_ndcg_at_k: float = Field(ge=0.0, le=1.0)
    correct_source_in_top_k_rate: float = Field(ge=0.0, le=1.0)
    all_required_sources_in_top_k_rate: float = Field(ge=0.0, le=1.0)
    citation_support_readiness_rate: float = Field(ge=0.0, le=1.0)
    unsupported_source_retrieval_rate: float = Field(ge=0.0, le=1.0)
    stale_source_retrieval_rate: float = Field(ge=0.0, le=1.0)
    metadata_filter_violation_rate: float = Field(ge=0.0, le=1.0)
    near_duplicate_case_count: int = Field(ge=0)
    near_duplicate_displacement_rate: float = Field(ge=0.0, le=1.0)


class RetrievalDevelopmentScorecard(BaseModel):
    """Hash-bound development scorecard for one retrieval candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    scorecard_id: str
    status: str = "development_candidate"
    metric_contract_version: str = "source-level-retrieval-metrics-v1"
    retrieval_set_path: str
    retrieval_set_sha256: str
    rejected_set_path: str
    rejected_set_sha256: str
    retrieval_manifest_path: str
    retrieval_manifest_sha256: str
    case_results_path: str
    case_results_sha256: str
    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    aggregate: RetrievalAggregateMetrics

    @model_validator(mode="after")
    def validate_hashes(self) -> RetrievalDevelopmentScorecard:
        for name, value in (
            ("retrieval_set_sha256", self.retrieval_set_sha256),
            ("rejected_set_sha256", self.rejected_set_sha256),
            ("retrieval_manifest_sha256", self.retrieval_manifest_sha256),
            ("case_results_sha256", self.case_results_sha256),
            ("retriever_config_sha256", self.retriever_config_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
        return self


class RetrievalHeldOutScorecard(BaseModel):
    """Hash-bound held-out scorecard for one finalist."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    scorecard_id: str
    status: str = "held_out_candidate"
    metric_contract_version: str = "source-level-retrieval-metrics-v1"
    retrieval_set_path: str
    retrieval_set_sha256: str
    rejected_set_path: str
    rejected_set_sha256: str
    freeze_record_path: str
    freeze_record_sha256: str
    retrieval_manifest_path: str
    retrieval_manifest_sha256: str
    case_results_path: str
    case_results_sha256: str
    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    aggregate: RetrievalAggregateMetrics

    @model_validator(mode="after")
    def validate_hashes(self) -> RetrievalHeldOutScorecard:
        for name, value in (
            ("retrieval_set_sha256", self.retrieval_set_sha256),
            ("rejected_set_sha256", self.rejected_set_sha256),
            ("freeze_record_sha256", self.freeze_record_sha256),
            ("retrieval_manifest_sha256", self.retrieval_manifest_sha256),
            ("case_results_sha256", self.case_results_sha256),
            ("retriever_config_sha256", self.retriever_config_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
        return self


class RetrievalEvaluationSummary(BaseModel):
    """Safe build or verification summary for one development scorecard."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    scorecard_id: str
    retriever_config_id: str
    chunking_config_id: str
    case_count: int
    mean_recall_at_k: float
    mean_precision_at_k: float
    mean_reciprocal_rank: float
    mean_ndcg_at_k: float
    correct_source_in_top_k_rate: float
    citation_support_readiness_rate: float
    stale_source_retrieval_rate: float
    near_duplicate_displacement_rate: float
    validation_status: str
