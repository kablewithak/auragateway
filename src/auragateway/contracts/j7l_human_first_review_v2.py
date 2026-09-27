"""Typed contracts for the J7L human-first development V2 review queue."""

from __future__ import annotations

from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_semantic_projection_v1 import HumanSemanticProjectionV1

EXPECTED_CASE_COUNT: Literal[48] = 48
EXPECTED_NOVELTY_THRESHOLD: Final[float] = 0.8


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def derived_verdict(
    criterion_scores: dict[RubricCriterion, int],
    failure_labels: tuple[EpisodeFailureLabel, ...],
) -> ReviewVerdict:
    values = tuple(criterion_scores[criterion] for criterion in RubricCriterion)
    passed = sum(values) >= 21 and min(values) >= 2 and not failure_labels
    return ReviewVerdict.PASS if passed else ReviewVerdict.FAIL


class J7LHumanFirstReviewPolicyV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    policy_id: Literal["auragateway-j7l-human-first-review-v2"] = (
        "auragateway-j7l-human-first-review-v2"
    )
    case_count: Literal[48] = EXPECTED_CASE_COUNT
    single_human_development_reference: Literal[True] = True
    sequential_submission_required: Literal[True] = True
    append_only_assessments_required: Literal[True] = True
    opaque_assignment_identity_required: Literal[True] = True
    case_id_hidden_from_human_work_item: Literal[True] = True
    family_hidden_from_human_work_item: Literal[True] = True
    hidden_authoring_targets_hidden_until_review_complete: Literal[True] = True
    human_judgment_before_ai_proposal_required: Literal[True] = True
    model_reference_execution_authorized: Literal[False] = False
    provider_requests_authorized: Literal[False] = False
    jev_requests_authorized: Literal[False] = False
    j7m_execution_authorized: Literal[False] = False
    final_abc_execution_authorized: Literal[False] = False
    development_only: Literal[True] = True
    independent_qualification_claim_permitted: Literal[False] = False
    production_readiness_claim_permitted: Literal[False] = False


class J7LHumanReviewerIdentityV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_HUMAN_REVIEWER_INITIALIZED"] = "J7L_V2_HUMAN_REVIEWER_INITIALIZED"
    reviewer_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hidden_authoring_payload_unread_attested: Literal[True] = True
    human_judgments_before_ai_proposals_attested: Literal[True] = True
    raw_reviewer_identity_persisted: Literal[False] = False
    model_reveal_performed: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0


class J7LHumanReviewWorkItemV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    policy_id: Literal["auragateway-j7l-human-first-review-v2"] = (
        "auragateway-j7l-human-first-review-v2"
    )
    queue_index: int = Field(ge=0, le=47)
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state: dict[str, JsonValue]
    semantic_projection: HumanSemanticProjectionV1
    reviewer_instruction: str = Field(min_length=100, max_length=2200)
    model_reference_included: Literal[False] = False
    jev_output_included: Literal[False] = False
    hidden_authoring_targets_included: Literal[False] = False
    case_family_included: Literal[False] = False
    historical_judgments_included: Literal[False] = False


class CriterionDraftV2(FrozenModel):
    criterion: RubricCriterion
    score: int | None = Field(default=None, ge=1, le=4)


class CriterionSubmissionV2(FrozenModel):
    criterion: RubricCriterion
    score: int = Field(ge=1, le=4)


class J7LHumanReviewSubmissionTemplateV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    criterion_scores: tuple[CriterionDraftV2, ...] = Field(min_length=7, max_length=7)
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = ()
    rationale: str | None = Field(default=None, min_length=20, max_length=8000)


class J7LHumanReviewSubmissionV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    criterion_scores: tuple[CriterionSubmissionV2, ...] = Field(
        min_length=7,
        max_length=7,
    )
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=20, max_length=8000)

    @model_validator(mode="after")
    def validate_submission(self) -> Self:
        criteria = tuple(item.criterion for item in self.criterion_scores)
        if len(criteria) != len(set(criteria)) or set(criteria) != set(RubricCriterion):
            raise ValueError("submission must score every rubric criterion exactly once")
        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("submission failure labels must be unique")
        if len(self.evidence_references) != len(set(self.evidence_references)):
            raise ValueError("submission evidence references must be unique")
        return self


class J7LHumanAssessmentV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    authority: Literal["SINGLE_HUMAN_DEVELOPMENT_REFERENCE"] = "SINGLE_HUMAN_DEVELOPMENT_REFERENCE"
    case_id: str = Field(pattern=r"^j7l-v2-dev-[0-9]{3}$")
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    reviewer_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_item_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=20, max_length=8000)
    verdict: ReviewVerdict
    human_judgment_before_ai_proposal_attested: Literal[True] = True
    hidden_authoring_payload_unread_during_judgment_attested: Literal[True] = True
    model_reference_read_for_judgment: Literal[False] = False
    jev_output_read_for_judgment: Literal[False] = False

    @model_validator(mode="after")
    def validate_assessment(self) -> Self:
        if set(self.criterion_scores) != set(RubricCriterion):
            raise ValueError("assessment must score every rubric criterion")
        if any(score < 1 or score > 4 for score in self.criterion_scores.values()):
            raise ValueError("assessment criterion scores must remain in [1,4]")
        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("assessment failure labels must be unique")
        if self.verdict is not derived_verdict(self.criterion_scores, self.failure_labels):
            raise ValueError("assessment verdict differs from deterministic derivation")
        return self


class J7LHumanReviewPreflightReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_HUMAN_REVIEW_INPUTS_VALID"] = "J7L_V2_HUMAN_REVIEW_INPUTS_VALID"
    case_count: Literal[48] = EXPECTED_CASE_COUNT
    novelty_threshold: float = Field(
        default=EXPECTED_NOVELTY_THRESHOLD,
        ge=EXPECTED_NOVELTY_THRESHOLD,
        le=EXPECTED_NOVELTY_THRESHOLD,
    )
    reviewer_safe_export_valid: Literal[True] = True
    authoring_payload_content_read: Literal[False] = False
    model_reveal_performed: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    next_gate: Literal["INITIALIZE_SINGLE_HUMAN_REVIEWER"] = "INITIALIZE_SINGLE_HUMAN_REVIEWER"


class J7LHumanReviewPrepareReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_HUMAN_REVIEW_PREPARED"] = "J7L_V2_HUMAN_REVIEW_PREPARED"
    work_item_count: Literal[48] = EXPECTED_CASE_COUNT
    submission_template_count: Literal[48] = EXPECTED_CASE_COUNT
    created_work_item_count: int = Field(ge=0, le=48)
    created_submission_template_count: int = Field(ge=0, le=48)
    work_item_root: str
    submission_root: str
    next_gate: Literal["COMPLETE_SEQUENTIAL_HUMAN_REVIEW"] = "COMPLETE_SEQUENTIAL_HUMAN_REVIEW"


class J7LHumanReviewQueueStatusV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_HUMAN_REVIEW_PENDING", "J7L_V2_HUMAN_REVIEW_COMPLETE"]
    completed_assessment_count: int = Field(ge=0, le=48)
    pending_assessment_count: int = Field(ge=0, le=48)
    next_assignment_id: str | None = Field(default=None, pattern=r"^review-[0-9a-f]{24}$")
    next_work_item_path: str | None = None
    next_submission_path: str | None = None
    case_id_exposed_in_status: Literal[False] = False
    family_exposed_in_status: Literal[False] = False
    model_reveal_performed: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.completed_assessment_count + self.pending_assessment_count != 48:
            raise ValueError("human-review queue counts do not reconcile")
        if self.pending_assessment_count == 0 and self.next_assignment_id is not None:
            raise ValueError("complete queue must not expose a next assignment")
        if self.pending_assessment_count > 0 and self.next_assignment_id is None:
            raise ValueError("pending queue must expose the next assignment")
        return self


class J7LHumanReviewSubmissionReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_HUMAN_ASSESSMENT_ACCEPTED"] = "J7L_V2_HUMAN_ASSESSMENT_ACCEPTED"
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created: bool
    completed_assessment_count: int = Field(ge=1, le=48)
    pending_assessment_count: int = Field(ge=0, le=47)
    next_assignment_id: str | None = Field(default=None, pattern=r"^review-[0-9a-f]{24}$")


class J7LHumanReferenceCoverageReportV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal[
        "J7L_V2_HUMAN_REFERENCE_COVERAGE_PASS",
        "J7L_V2_HUMAN_REFERENCE_COVERAGE_FAIL",
    ]
    case_count: Literal[48] = EXPECTED_CASE_COUNT
    pass_count: int = Field(ge=0, le=48)
    fail_count: int = Field(ge=0, le=48)
    minimum_positive_support_observed: int = Field(ge=0)
    minimum_near_miss_negative_support_observed: int = Field(ge=0)
    minimum_distinct_scores_observed: int = Field(ge=1, le=4)
    minimum_low_scores_observed: int = Field(ge=0, le=48)
    minimum_high_scores_observed: int = Field(ge=0, le=48)
    terminal_material_evidence_case_count: int = Field(ge=0, le=12)
    pass_fail_coverage_pass: bool
    positive_label_coverage_pass: bool
    near_miss_negative_coverage_pass: bool
    criterion_diversity_coverage_pass: bool
    criterion_low_coverage_pass: bool
    criterion_high_coverage_pass: bool
    terminal_material_coverage_pass: bool
    hidden_authoring_targets_read_only_after_human_completion: Literal[True] = True
    authoring_targets_treated_as_human_truth: Literal[False] = False
    human_assessments_mutated_for_coverage: Literal[False] = False
    model_reveal_performed: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    next_gate: Literal[
        "FREEZE_SINGLE_HUMAN_DEVELOPMENT_REFERENCE",
        "STOP_VERSIONED_SUCCESSOR_REQUIRED",
    ]

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        checks = (
            self.pass_fail_coverage_pass,
            self.positive_label_coverage_pass,
            self.near_miss_negative_coverage_pass,
            self.criterion_diversity_coverage_pass,
            self.criterion_low_coverage_pass,
            self.criterion_high_coverage_pass,
            self.terminal_material_coverage_pass,
        )
        passed = all(checks)
        expected_status = (
            "J7L_V2_HUMAN_REFERENCE_COVERAGE_PASS"
            if passed
            else "J7L_V2_HUMAN_REFERENCE_COVERAGE_FAIL"
        )
        expected_next = (
            "FREEZE_SINGLE_HUMAN_DEVELOPMENT_REFERENCE"
            if passed
            else "STOP_VERSIONED_SUCCESSOR_REQUIRED"
        )
        if self.status != expected_status:
            raise ValueError("coverage status does not match coverage checks")
        if self.next_gate != expected_next:
            raise ValueError("coverage next gate does not match coverage checks")
        if self.pass_count + self.fail_count != self.case_count:
            raise ValueError("coverage verdict counts do not reconcile")
        return self


class AssessmentDigestV2(FrozenModel):
    case_id: str = Field(pattern=r"^j7l-v2-dev-[0-9]{3}$")
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class J7LHumanReferenceFreezeV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_SINGLE_HUMAN_DEVELOPMENT_REFERENCE_FROZEN"] = (
        "J7L_V2_SINGLE_HUMAN_DEVELOPMENT_REFERENCE_FROZEN"
    )
    authority: Literal["SINGLE_HUMAN_DEVELOPMENT_REFERENCE"] = "SINGLE_HUMAN_DEVELOPMENT_REFERENCE"
    reviewer_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    foundation_case_freeze_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    coverage_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessments: tuple[AssessmentDigestV2, ...] = Field(min_length=48, max_length=48)
    assessment_count: Literal[48] = EXPECTED_CASE_COUNT
    hidden_authoring_targets_read_after_human_completion: Literal[True] = True
    authoring_targets_treated_as_human_truth: Literal[False] = False
    model_reveal_performed_before_freeze: Literal[False] = False
    provider_requests_performed_before_freeze: Literal[0] = 0
    jev_requests_performed_before_freeze: Literal[0] = 0
    independent_qualification_claim_permitted: Literal[False] = False
    next_gate: Literal["DESIGN_J7L_V2_DEVELOPMENT_EVALUATOR_EXECUTION"] = (
        "DESIGN_J7L_V2_DEVELOPMENT_EVALUATOR_EXECUTION"
    )

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        case_ids = tuple(item.case_id for item in self.assessments)
        assignment_ids = tuple(item.assignment_id for item in self.assessments)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("human reference freeze case IDs must be unique")
        if len(assignment_ids) != len(set(assignment_ids)):
            raise ValueError("human reference freeze assignment IDs must be unique")
        return self


class J7LHumanReferencePublicReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    receipt_id: Literal["auragateway-j7l-v2-human-reference-freeze-v1"] = (
        "auragateway-j7l-v2-human-reference-freeze-v1"
    )
    status: Literal["J7L_V2_SINGLE_HUMAN_DEVELOPMENT_REFERENCE_FROZEN"] = (
        "J7L_V2_SINGLE_HUMAN_DEVELOPMENT_REFERENCE_FROZEN"
    )
    authority: Literal["SINGLE_HUMAN_DEVELOPMENT_REFERENCE"] = "SINGLE_HUMAN_DEVELOPMENT_REFERENCE"
    assessment_count: Literal[48] = EXPECTED_CASE_COUNT
    pass_count: int = Field(ge=16, le=32)
    fail_count: int = Field(ge=16, le=32)
    foundation_case_freeze_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    coverage_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_human_reference_freeze_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_assessments_publicly_persisted: Literal[False] = False
    reviewer_rationale_publicly_persisted: Literal[False] = False
    hidden_authoring_targets_publicly_persisted: Literal[False] = False
    independent_qualification_claim_permitted: Literal[False] = False
    model_reveal_performed_before_freeze: Literal[False] = False
    provider_requests_performed_before_freeze: Literal[0] = 0
    jev_requests_performed_before_freeze: Literal[0] = 0
    next_gate: Literal["DESIGN_J7L_V2_DEVELOPMENT_EVALUATOR_EXECUTION"] = (
        "DESIGN_J7L_V2_DEVELOPMENT_EVALUATOR_EXECUTION"
    )

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.pass_count + self.fail_count != self.assessment_count:
            raise ValueError("public human-reference verdict counts do not reconcile")
        return self
