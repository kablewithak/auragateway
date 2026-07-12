"""Typed blinded-review and adjudication contracts for Gate 6."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from auragateway.contracts.episodes import EpisodeFailureLabel

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EPISODE_ID_PATTERN = re.compile(r"^ep-func-[0-9]{3}$")
_REVIEW_ID_PATTERN = re.compile(r"^review-[0-9a-f]{24}$")
_CASE_ID_PATTERN = re.compile(r"^blind-[a-z0-9-]{3,80}$")


class ReviewRole(StrEnum):
    """Supported roles in the blinded review workflow."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    ADJUDICATOR = "adjudicator"


class ReviewVerdict(StrEnum):
    """Bounded reviewer verdict."""

    PASS = "pass"
    FAIL = "fail"


class RubricCriterion(StrEnum):
    """Frozen residual-quality criteria used after deterministic checks."""

    TASK_CORRECTNESS = "task_correctness"
    EVIDENCE_GROUNDING = "evidence_grounding"
    SOURCE_USE = "source_use"
    TERMINAL_DECISION = "terminal_decision"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    SAFETY = "safety"


class DisagreementReason(StrEnum):
    """Machine-readable reasons requiring independent adjudication."""

    VERDICT_MISMATCH = "verdict_mismatch"
    MATERIAL_SCORE_DELTA = "material_score_delta"
    FAILURE_LABEL_MISMATCH = "failure_label_mismatch"


class RubricCriterionDefinition(BaseModel):
    """One frozen rubric criterion and its score anchors."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion: RubricCriterion
    description: str = Field(min_length=20, max_length=500)
    score_1_anchor: str = Field(min_length=10, max_length=300)
    score_2_anchor: str = Field(min_length=10, max_length=300)
    score_3_anchor: str = Field(min_length=10, max_length=300)
    score_4_anchor: str = Field(min_length=10, max_length=300)


class BlindedQualityRubric(BaseModel):
    """Versioned rubric for condition-blind residual-quality review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    rubric_id: str = "auragateway-quality-rubric-v1"
    criteria: tuple[RubricCriterionDefinition, ...] = Field(min_length=7, max_length=7)
    passing_total_score: int = Field(default=21, ge=7, le=28)
    minimum_criterion_score: int = Field(default=2, ge=1, le=4)
    material_score_delta: int = Field(default=2, ge=1, le=3)
    reviewer_must_use_visible_evidence_only: bool = True
    hidden_reasoning_prohibited: bool = True

    @model_validator(mode="after")
    def validate_rubric(self) -> BlindedQualityRubric:
        criteria = [item.criterion for item in self.criteria]
        if len(criteria) != len(set(criteria)):
            raise ValueError("rubric criteria must be unique")
        if set(criteria) != set(RubricCriterion):
            raise ValueError("rubric must define every required criterion exactly once")
        if not self.reviewer_must_use_visible_evidence_only:
            raise ValueError("reviewers must use only visible blinded evidence")
        if not self.hidden_reasoning_prohibited:
            raise ValueError("review artifacts must not require hidden reasoning")
        return self


class ReviewAssignment(BaseModel):
    """One deterministic blinded review slot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str
    episode_id: str
    role: ReviewRole
    assignment_key_sha256: str

    @field_validator("review_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        if _REVIEW_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("review_id must use review-<24 lowercase hex> form")
        return value

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value

    @field_validator("assignment_key_sha256")
    @classmethod
    def validate_assignment_key(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("assignment_key_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_role(self) -> ReviewAssignment:
        if self.role is ReviewRole.ADJUDICATOR:
            raise ValueError("adjudicators are not pre-assigned review slots")
        return self


class ReviewAssignmentManifest(BaseModel):
    """Deterministic primary and double-review assignment inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-6-review-assignments-v1"
    protocol_id: str
    sampling_seed: int
    episode_count: int
    primary_assignment_count: int
    secondary_assignment_count: int
    double_review_episode_ids: tuple[str, ...]
    assignments: tuple[ReviewAssignment, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> ReviewAssignmentManifest:
        if self.episode_count <= 0:
            raise ValueError("episode_count must be positive")
        if self.primary_assignment_count != self.episode_count:
            raise ValueError("every episode requires exactly one primary assignment")
        if self.secondary_assignment_count != len(self.double_review_episode_ids):
            raise ValueError("secondary count must match double-review episode IDs")
        if tuple(sorted(self.double_review_episode_ids)) != self.double_review_episode_ids:
            raise ValueError("double-review episode IDs must be sorted")
        if len(self.double_review_episode_ids) != len(set(self.double_review_episode_ids)):
            raise ValueError("double-review episode IDs must be unique")

        review_ids = [item.review_id for item in self.assignments]
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("review assignment IDs must be unique")

        primary_ids = [
            item.episode_id for item in self.assignments if item.role is ReviewRole.PRIMARY
        ]
        secondary_ids = [
            item.episode_id for item in self.assignments if item.role is ReviewRole.SECONDARY
        ]
        if len(primary_ids) != self.primary_assignment_count:
            raise ValueError("primary assignment count does not reconcile")
        if len(primary_ids) != len(set(primary_ids)):
            raise ValueError("episodes must not have duplicate primary assignments")
        if tuple(sorted(secondary_ids)) != self.double_review_episode_ids:
            raise ValueError("secondary assignments must match the frozen sample")
        return self


class ReviewSourceEnvelope(BaseModel):
    """Protected source material before experimental fields are stripped."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: str
    synthetic_conversation: tuple[str, ...] = Field(min_length=1)
    terminal_decision_output: dict[str, JsonValue]
    citation_source_ids: tuple[str, ...] = ()
    deterministic_validation_results: dict[str, JsonValue]
    condition_id: str
    provider: str
    model: str
    route: str
    cost: float = Field(ge=0.0)
    latency: int = Field(ge=0)
    cache_telemetry: dict[str, JsonValue]
    run_order: int = Field(ge=1)

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value


class BlindedReviewExport(BaseModel):
    """Condition-blind reviewer payload containing only approved visible fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    review_id: str
    episode_id: str
    synthetic_conversation: tuple[str, ...] = Field(min_length=1)
    terminal_decision_output: dict[str, JsonValue]
    citation_source_ids: tuple[str, ...] = ()
    deterministic_validation_results: dict[str, JsonValue]

    @field_validator("review_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        if _REVIEW_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("review_id must use review-<24 lowercase hex> form")
        return value


class CriterionScore(BaseModel):
    """One reviewer score with a protected rationale digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion: RubricCriterion
    score: int = Field(ge=1, le=4)
    evidence_note_sha256: str

    @field_validator("evidence_note_sha256")
    @classmethod
    def validate_note_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence_note_sha256 must be lowercase SHA-256")
        return value


class QualityReviewRecord(BaseModel):
    """Protected primary or secondary review result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    review_id: str
    episode_id: str
    reviewer_id_sha256: str
    role: ReviewRole
    criterion_scores: tuple[CriterionScore, ...] = Field(min_length=7, max_length=7)
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    verdict: ReviewVerdict
    rationale_sha256: str

    @field_validator("review_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        if _REVIEW_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("review_id must use review-<24 lowercase hex> form")
        return value

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value

    @field_validator("reviewer_id_sha256", "rationale_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("review digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_record(self) -> QualityReviewRecord:
        if self.role is ReviewRole.ADJUDICATOR:
            raise ValueError("adjudicator outcomes use AdjudicationRecord")
        criteria = [item.criterion for item in self.criterion_scores]
        if len(criteria) != len(set(criteria)):
            raise ValueError("criterion scores must be unique")
        if set(criteria) != set(RubricCriterion):
            raise ValueError("review must score every rubric criterion")
        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("failure labels must be unique")
        return self


class MaterialDisagreement(BaseModel):
    """Deterministic material disagreement between independent reviews."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: str
    primary_review_id: str
    secondary_review_id: str
    reasons: tuple[DisagreementReason, ...] = Field(min_length=1)
    criterion_score_deltas: dict[RubricCriterion, int]

    @model_validator(mode="after")
    def validate_disagreement(self) -> MaterialDisagreement:
        if len(self.reasons) != len(set(self.reasons)):
            raise ValueError("disagreement reasons must be unique")
        if any(delta < 0 or delta > 3 for delta in self.criterion_score_deltas.values()):
            raise ValueError("criterion score deltas must be between zero and three")
        return self


class AdjudicationRecord(BaseModel):
    """Independent final decision for a material disagreement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    episode_id: str
    primary_review_id: str
    secondary_review_id: str
    adjudicator_id_sha256: str
    final_criterion_scores: tuple[CriterionScore, ...] = Field(min_length=7, max_length=7)
    final_failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    final_verdict: ReviewVerdict
    rationale_sha256: str

    @field_validator("adjudicator_id_sha256", "rationale_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("adjudication digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_record(self) -> AdjudicationRecord:
        criteria = [item.criterion for item in self.final_criterion_scores]
        if len(criteria) != len(set(criteria)):
            raise ValueError("adjudication criterion scores must be unique")
        if set(criteria) != set(RubricCriterion):
            raise ValueError("adjudication must score every rubric criterion")
        if len(self.final_failure_labels) != len(set(self.final_failure_labels)):
            raise ValueError("adjudication failure labels must be unique")
        return self


class BlindedQualityFixtureCase(BaseModel):
    """One fixed workflow case and expected protected outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    source: ReviewSourceEnvelope
    assignments: tuple[ReviewAssignment, ...] = Field(min_length=1, max_length=2)
    primary_review: QualityReviewRecord
    secondary_review: QualityReviewRecord | None = None
    adjudication: AdjudicationRecord | None = None
    expected_material_disagreement: bool | None = None
    expected_error_code: str | None = None
    negative_control: bool = False

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _CASE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("case_id must use blind-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_case(self) -> BlindedQualityFixtureCase:
        review_ids = [item.review_id for item in self.assignments]
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("fixture assignments must have unique review IDs")
        if self.secondary_review is None and self.expected_material_disagreement is not None:
            raise ValueError("material-disagreement expectation requires a secondary review")
        if self.negative_control != (self.expected_error_code is not None):
            raise ValueError("negative_control must match expected_error_code presence")
        return self


class BlindedQualityFixtureSet(BaseModel):
    """Fixed Gate 6 blinded-review workflow fixtures."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str = "auragateway-gate-6-blinded-quality-v1"
    cases: tuple[BlindedQualityFixtureCase, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_fixture_set(self) -> BlindedQualityFixtureSet:
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("blinded quality fixture case IDs must be unique")
        if not any(item.negative_control for item in self.cases):
            raise ValueError("blinded quality fixtures require negative controls")
        if not any(not item.negative_control for item in self.cases):
            raise ValueError("blinded quality fixtures require passing controls")
        return self


class BlindedQualityFixtureResult(BaseModel):
    """Metadata-only result for one blinded workflow fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    expectation_matched: bool
    observed_error_code: str | None = None
    material_disagreement: bool | None = None
    export_sha256: str | None = None
    negative_control: bool

    @field_validator("export_sha256")
    @classmethod
    def validate_export_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("export_sha256 must be lowercase SHA-256")
        return value


class Gate6BlindedQualityReport(BaseModel):
    """Reproducible report for review preparation and adjudication controls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    assignment_manifest_id: str
    results: tuple[BlindedQualityFixtureResult, ...]
    fixture_count: int
    negative_control_count: int
    material_disagreement_fixture_count: int
    all_expectations_matched: bool
    blinded_workflow_passed: bool
    measured_execution_permitted: bool = False

    @model_validator(mode="after")
    def validate_report(self) -> Gate6BlindedQualityReport:
        if self.fixture_count != len(self.results):
            raise ValueError("fixture_count must match blinded quality results")
        if self.negative_control_count != sum(item.negative_control for item in self.results):
            raise ValueError("negative control count must reconcile")
        material_count = sum(item.material_disagreement is True for item in self.results)
        if self.material_disagreement_fixture_count != material_count:
            raise ValueError("material disagreement fixture count must reconcile")
        expected_match = all(item.expectation_matched for item in self.results)
        if self.all_expectations_matched != expected_match:
            raise ValueError("all_expectations_matched must reconcile")
        if self.blinded_workflow_passed != expected_match:
            raise ValueError("blinded_workflow_passed must match fixture expectations")
        if self.measured_execution_permitted:
            raise ValueError("blinded workflow fixtures do not permit measured execution")
        return self


class Gate6BlindedQualityManifest(BaseModel):
    """Hash-bound inventory for blinded review preparation evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-6-blinded-quality-manifest-v1"
    rubric_path: str
    rubric_sha256: str
    assignment_path: str
    assignment_sha256: str
    fixture_path: str
    fixture_sha256: str
    report_path: str
    report_sha256: str
    protocol_path: str
    protocol_sha256: str
    episode_manifest_path: str
    episode_manifest_sha256: str
    deterministic_quality_manifest_path: str
    deterministic_quality_manifest_sha256: str
    primary_assignment_count: int
    secondary_assignment_count: int
    fixture_count: int
    negative_control_count: int
    blinded_workflow_passed: bool
    measured_execution_permitted: bool = False

    @model_validator(mode="after")
    def validate_manifest(self) -> Gate6BlindedQualityManifest:
        digest_fields = (
            self.rubric_sha256,
            self.assignment_sha256,
            self.fixture_sha256,
            self.report_sha256,
            self.protocol_sha256,
            self.episode_manifest_sha256,
            self.deterministic_quality_manifest_sha256,
        )
        if any(_SHA256_PATTERN.fullmatch(value) is None for value in digest_fields):
            raise ValueError("manifest digests must be lowercase SHA-256")
        if not self.blinded_workflow_passed:
            raise ValueError("frozen blinded quality manifest requires passing fixtures")
        if self.measured_execution_permitted:
            raise ValueError("blinded preparation does not permit measured execution")
        return self


class Gate6BlindedQualitySummary(BaseModel):
    """Safe CLI summary for blinded quality build or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    rubric_id: str
    primary_assignment_count: int
    secondary_assignment_count: int
    fixture_count: int
    negative_control_count: int
    material_disagreement_fixture_count: int
    blinded_workflow_passed: bool
    measured_execution_permitted: bool
