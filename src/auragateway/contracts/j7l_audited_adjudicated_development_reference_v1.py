"""Typed contracts for the J7L audited/adjudicated development-reference successor."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_semantic_projection_v1 import HumanSemanticProjectionV1

EXPECTED_CASE_COUNT: Literal[48] = 48
EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT: Literal[28] = 28
EXPECTED_REMAINING_HUMAN_ASSESSMENT_COUNT: Literal[20] = 20
EXPECTED_FAILED_V3_AUDIT_CASE_COUNT: Literal[28] = 28
EXPECTED_FAILED_V3_MATERIAL_DISAGREEMENT_COUNT: Literal[16] = 16
EXPECTED_MATERIAL_SCORE_DELTA: Literal[2] = 2

EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256: Literal[
    "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"
] = "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"

EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256: Literal[
    "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"
] = "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DevelopmentReferenceAuthorityClass(StrEnum):
    AUDITED_ADJUDICATED_DEVELOPMENT_REFERENCE = "AUDITED_ADJUDICATED_DEVELOPMENT_REFERENCE"


class DevelopmentResolutionSource(StrEnum):
    HUMAN_ASSESSMENT = "HUMAN_ASSESSMENT"
    INDEPENDENT_ADJUDICATION = "INDEPENDENT_ADJUDICATION"


def derived_verdict(
    criterion_scores: dict[RubricCriterion, int],
    failure_labels: tuple[EpisodeFailureLabel, ...],
) -> ReviewVerdict:
    values = tuple(criterion_scores[criterion] for criterion in RubricCriterion)
    passed = sum(values) >= 21 and min(values) >= 2 and not failure_labels
    return ReviewVerdict.PASS if passed else ReviewVerdict.FAIL


class J7LAuditedAdjudicatedDevelopmentReferencePolicyV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["auragateway-j7l-audited-adjudicated-development-reference-v1"] = (
        "auragateway-j7l-audited-adjudicated-development-reference-v1"
    )

    authority_class: Literal["AUDITED_ADJUDICATED_DEVELOPMENT_REFERENCE"] = (
        DevelopmentReferenceAuthorityClass.AUDITED_ADJUDICATED_DEVELOPMENT_REFERENCE.value
    )

    case_count: Literal[48] = EXPECTED_CASE_COUNT
    failed_v3_audit_case_count: Literal[28] = EXPECTED_FAILED_V3_AUDIT_CASE_COUNT
    failed_v3_material_disagreement_count: Literal[16] = (
        EXPECTED_FAILED_V3_MATERIAL_DISAGREEMENT_COUNT
    )
    preserved_human_assessment_count: Literal[28] = EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
    remaining_human_assessment_count: Literal[20] = EXPECTED_REMAINING_HUMAN_ASSESSMENT_COUNT
    required_full_human_assessment_count: Literal[48] = EXPECTED_CASE_COUNT

    failed_v3_lineage_remains_failed: Literal[True] = True
    failed_v3_reference_mutation_permitted: Literal[False] = False
    failed_v3_human_rescoring_permitted: Literal[False] = False
    model_reference_replay_permitted: Literal[False] = False

    remaining_human_review_blinded_from_model_reference: Literal[True] = True
    remaining_human_review_blinded_from_authoring_targets: Literal[True] = True
    remaining_human_review_blinded_from_jev: Literal[True] = True

    material_disagreement_verdict_mismatch: Literal[True] = True
    material_disagreement_score_delta: Literal[2] = EXPECTED_MATERIAL_SCORE_DELTA
    material_disagreement_failure_label_set_mismatch: Literal[True] = True

    no_material_disagreement_resolution_source: Literal["HUMAN_ASSESSMENT"] = (
        DevelopmentResolutionSource.HUMAN_ASSESSMENT.value
    )
    material_disagreement_resolution_source: Literal["INDEPENDENT_ADJUDICATION"] = (
        DevelopmentResolutionSource.INDEPENDENT_ADJUDICATION.value
    )
    independent_adjudicator_required: Literal[True] = True
    human_model_origin_hidden_from_adjudicator: Literal[True] = True
    mechanical_score_averaging_permitted: Literal[False] = False
    model_judgment_direct_authority_permitted: Literal[False] = False

    development_only: Literal[True] = True
    j7m_qualification_claim_permitted: Literal[False] = False
    final_abc_quality_claim_permitted: Literal[False] = False
    production_readiness_claim_permitted: Literal[False] = False

    provider_requests_authorized: Literal[False] = False
    jev_requests_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        if (
            self.preserved_human_assessment_count + self.remaining_human_assessment_count
            != self.required_full_human_assessment_count
        ):
            raise ValueError("successor human-assessment counts do not reconcile")
        if self.required_full_human_assessment_count != self.case_count:
            raise ValueError("successor authority must cover the exact 48-case population")
        return self


class CriterionDraft(FrozenModel):
    criterion: RubricCriterion
    score: int | None = Field(default=None, ge=1, le=4)
    evidence_note: str | None = Field(default=None, min_length=1, max_length=4000)


class CriterionSubmission(FrozenModel):
    criterion: RubricCriterion
    score: int = Field(ge=1, le=4)
    evidence_note: str = Field(min_length=1, max_length=4000)


class J7LSuccessorSubmissionTemplateV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    criterion_scores: tuple[CriterionDraft, ...] = Field(min_length=7, max_length=7)
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = ()
    rationale: str | None = Field(default=None, min_length=20, max_length=8000)


class J7LSuccessorSubmissionV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    criterion_scores: tuple[CriterionSubmission, ...] = Field(min_length=7, max_length=7)
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


class J7LSuccessorHumanWorkItemV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["auragateway-j7l-audited-adjudicated-development-reference-v1"] = (
        "auragateway-j7l-audited-adjudicated-development-reference-v1"
    )
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    queue_index: int = Field(ge=0, le=19)
    source_review_stream: Literal["primary"] = "primary"
    source_assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state: dict[str, object]
    semantic_projection: HumanSemanticProjectionV1
    reviewer_instruction: str = Field(min_length=100, max_length=1200)
    assessment_actor_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    predecessor_model_reference_included: Literal[False] = False
    predecessor_comparison_included: Literal[False] = False
    jev_output_included: Literal[False] = False
    authoring_targets_included: Literal[False] = False
    family_metadata_included: Literal[False] = False


class J7LSuccessorHumanAssessmentV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_SUCCESSOR_HUMAN_ASSESSMENT_COMPLETE"] = (
        "J7L_SUCCESSOR_HUMAN_ASSESSMENT_COMPLETE"
    )
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    assessment_actor_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_item_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=20, max_length=8000)
    verdict: ReviewVerdict

    predecessor_model_reference_included_in_work_item: Literal[False] = False
    predecessor_comparison_included_in_work_item: Literal[False] = False
    jev_output_included_in_work_item: Literal[False] = False
    authoring_targets_included_in_work_item: Literal[False] = False

    @model_validator(mode="after")
    def validate_assessment(self) -> Self:
        if set(self.criterion_scores) != set(RubricCriterion):
            raise ValueError("assessment must score every rubric criterion")
        if any(score < 1 or score > 4 for score in self.criterion_scores.values()):
            raise ValueError("assessment scores must remain in [1,4]")
        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("assessment failure labels must be unique")
        if len(self.evidence_references) != len(set(self.evidence_references)):
            raise ValueError("assessment evidence references must be unique")
        if self.verdict is not derived_verdict(self.criterion_scores, self.failure_labels):
            raise ValueError("assessment verdict differs from the frozen derivation rule")
        return self


class J7LSuccessorPreflightReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_SUCCESSOR_INPUTS_VALID"] = "J7L_SUCCESSOR_INPUTS_VALID"
    failed_v3_audit_result_sha256: Literal[
        "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"
    ] = EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256
    failed_v3_human_freeze_sha256: Literal[
        "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"
    ] = EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256
    failed_v3_material_disagreement_count: Literal[16] = (
        EXPECTED_FAILED_V3_MATERIAL_DISAGREEMENT_COUNT
    )
    preserved_human_assessment_count: Literal[28] = EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
    remaining_human_assessment_count: Literal[20] = EXPECTED_REMAINING_HUMAN_ASSESSMENT_COUNT
    total_case_count: Literal[48] = EXPECTED_CASE_COUNT
    model_reference_content_read_for_human_review: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    next_gate: Literal["PREPARE_REMAINING_20_BLINDED_HUMAN_ASSESSMENTS"] = (
        "PREPARE_REMAINING_20_BLINDED_HUMAN_ASSESSMENTS"
    )


class J7LSuccessorPrepareReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_SUCCESSOR_HUMAN_PACKET_READY"] = "J7L_SUCCESSOR_HUMAN_PACKET_READY"
    remaining_human_assessment_count: Literal[20] = EXPECTED_REMAINING_HUMAN_ASSESSMENT_COUNT
    created_work_item_count: int = Field(ge=0, le=20)
    created_submission_template_count: int = Field(ge=0, le=20)
    work_item_root: str
    submission_root: str
    model_reference_content_read_for_human_review: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0


class J7LSuccessorQueueStatusV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["SUCCESSOR_HUMAN_REVIEW_PENDING", "SUCCESSOR_HUMAN_REVIEW_COMPLETE"]
    preserved_human_assessment_count: Literal[28] = EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
    successor_completed_assessment_count: int = Field(ge=0, le=20)
    total_completed_human_assessment_count: int = Field(ge=28, le=48)
    pending_successor_assessment_count: int = Field(ge=0, le=20)
    next_case_id: str | None = Field(default=None, pattern=r"^j7l-dev-[0-9]{3}$")
    next_work_item_path: str | None = None
    next_submission_path: str | None = None
    model_reference_content_read_for_human_review: Literal[False] = False
    material_disagreement_evaluated_for_full_48: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if (
            self.preserved_human_assessment_count + self.successor_completed_assessment_count
            != self.total_completed_human_assessment_count
        ):
            raise ValueError("successor queue completed-count accounting drifted")
        if (
            self.successor_completed_assessment_count + self.pending_successor_assessment_count
            != EXPECTED_REMAINING_HUMAN_ASSESSMENT_COUNT
        ):
            raise ValueError("successor queue pending-count accounting drifted")
        complete = self.pending_successor_assessment_count == 0
        expected_status = (
            "SUCCESSOR_HUMAN_REVIEW_COMPLETE" if complete else "SUCCESSOR_HUMAN_REVIEW_PENDING"
        )
        if self.status != expected_status:
            raise ValueError("successor queue status does not match pending count")
        if complete != (self.next_case_id is None):
            raise ValueError("successor queue next-case state drifted")
        return self


class J7LSuccessorSubmissionReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_SUCCESSOR_HUMAN_ASSESSMENT_PERSISTED"] = (
        "J7L_SUCCESSOR_HUMAN_ASSESSMENT_PERSISTED"
    )
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created: bool
    total_completed_human_assessment_count: int = Field(ge=29, le=48)
    pending_successor_assessment_count: int = Field(ge=0, le=19)
    next_case_id: str | None = Field(default=None, pattern=r"^j7l-dev-[0-9]{3}$")
    model_reference_content_read_for_human_review: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
