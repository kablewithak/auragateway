"""Typed contracts for the J7L human-review remediation V2 lineage."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.j7l_audited_adjudicated_development_reference_v1 import (
    derived_verdict,
)
from auragateway.contracts.quality_semantic_projection_v1 import (
    HumanSemanticProjectionV1,
)

EXPECTED_CASE_COUNT: Literal[48] = 48
EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT: Literal[28] = 28
EXPECTED_FRESH_REMEDIATION_ASSESSMENT_COUNT: Literal[20] = 20
EXPECTED_V1_CONTAMINATED_SUBMISSION_COUNT: Literal[8] = 8
EXPECTED_KNOWN_EXPOSED_UNSUBMITTED_COUNT: Literal[1] = 1

EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256: Literal[
    "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"
] = "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"

EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256: Literal[
    "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"
] = "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"

EXPECTED_V1_ASSESSMENT_ACTOR_SHA256: Literal[
    "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"
] = "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"

EXPECTED_REMEDIATION_CASE_IDS: tuple[str, ...] = (
    *(f"j7l-dev-{index:03d}" for index in range(3, 13)),
    *(f"j7l-dev-{index:03d}" for index in range(15, 25)),
)

EXPECTED_V1_CONTAMINATED_CASE_IDS: tuple[str, ...] = tuple(
    f"j7l-dev-{index:03d}" for index in range(3, 11)
)

EXPECTED_KNOWN_EXPOSED_UNSUBMITTED_CASE_IDS: tuple[str, ...] = ("j7l-dev-011",)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class J7LHumanReviewRemediationPolicyV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    policy_id: Literal["auragateway-j7l-human-review-remediation-v2"] = (
        "auragateway-j7l-human-review-remediation-v2"
    )
    predecessor_v1_policy_id: Literal[
        "auragateway-j7l-audited-adjudicated-development-reference-v1"
    ] = "auragateway-j7l-audited-adjudicated-development-reference-v1"

    case_count: Literal[48] = EXPECTED_CASE_COUNT
    preserved_original_human_assessment_count: Literal[28] = (
        EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
    )
    fresh_remediation_assessment_count: Literal[20] = EXPECTED_FRESH_REMEDIATION_ASSESSMENT_COUNT
    required_full_human_assessment_count: Literal[48] = EXPECTED_CASE_COUNT

    predecessor_v1_lineage_non_advancing: Literal[True] = True
    predecessor_v1_assessment_mutation_permitted: Literal[False] = False
    predecessor_v1_assessment_reuse_permitted: Literal[False] = False
    predecessor_v1_submitted_contaminated_count: Literal[8] = (
        EXPECTED_V1_CONTAMINATED_SUBMISSION_COUNT
    )
    known_exposed_unsubmitted_count: Literal[1] = EXPECTED_KNOWN_EXPOSED_UNSUBMITTED_COUNT

    fresh_reviewer_required: Literal[True] = True
    fresh_reviewer_must_differ_from_v1_actor: Literal[True] = True
    fresh_reviewer_no_prior_judgment_exposure_required: Literal[True] = True
    fresh_assessment_required_for_all_20_cases: Literal[True] = True

    failed_v3_lineage_remains_failed: Literal[True] = True
    model_reference_replay_permitted: Literal[False] = False
    original_28_human_rescoring_permitted: Literal[False] = False

    model_reference_content_permitted_in_human_work_items: Literal[False] = False
    v1_assessment_content_permitted_in_human_work_items: Literal[False] = False
    authoring_targets_permitted_in_human_work_items: Literal[False] = False
    jev_output_permitted_in_human_work_items: Literal[False] = False

    provider_requests_authorized: Literal[False] = False
    jev_requests_authorized: Literal[False] = False

    development_only: Literal[True] = True
    j7m_qualification_claim_permitted: Literal[False] = False
    final_abc_quality_claim_permitted: Literal[False] = False
    production_readiness_claim_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        if (
            self.preserved_original_human_assessment_count + self.fresh_remediation_assessment_count
            != self.required_full_human_assessment_count
        ):
            raise ValueError("remediation human-assessment counts do not reconcile")
        if self.required_full_human_assessment_count != self.case_count:
            raise ValueError("remediation authority must cover the exact 48-case population")
        return self


class AssessmentDigestV2(FrozenModel):
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class J7LV1ContaminationFreezeV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V1_CONTAMINATION_FROZEN"] = "J7L_V1_CONTAMINATION_FROZEN"
    predecessor_policy_id: Literal[
        "auragateway-j7l-audited-adjudicated-development-reference-v1"
    ] = "auragateway-j7l-audited-adjudicated-development-reference-v1"
    predecessor_queue_root: Literal[
        ".local/auragateway/j7l-audited-adjudicated-development-reference-v1"
    ] = ".local/auragateway/j7l-audited-adjudicated-development-reference-v1"
    predecessor_lineage_non_advancing: Literal[True] = True
    predecessor_assessment_mutation_permitted: Literal[False] = False
    contaminated_submission_count: Literal[8] = EXPECTED_V1_CONTAMINATED_SUBMISSION_COUNT
    contaminated_assessments: tuple[AssessmentDigestV2, ...] = Field(
        min_length=8,
        max_length=8,
    )
    known_exposed_unsubmitted_case_ids: tuple[str, ...] = (
        EXPECTED_KNOWN_EXPOSED_UNSUBMITTED_CASE_IDS
    )
    model_reference_content_read_for_freeze: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        ids = tuple(item.case_id for item in self.contaminated_assessments)
        if ids != EXPECTED_V1_CONTAMINATED_CASE_IDS:
            raise ValueError(
                "V1 contaminated assessment inventory differs from the frozen incident"
            )
        if self.known_exposed_unsubmitted_case_ids != (EXPECTED_KNOWN_EXPOSED_UNSUBMITTED_CASE_IDS):
            raise ValueError("known unsubmitted exposure inventory drifted")
        return self


class J7LRemediationReviewerIdentityV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_REMEDIATION_REVIEWER_IDENTITY_FROZEN"] = (
        "J7L_REMEDIATION_REVIEWER_IDENTITY_FROZEN"
    )
    reviewer_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    distinct_from_v1_assessment_actor_attested: Literal[True] = True
    no_prior_ai_or_v1_judgment_exposure_attested: Literal[True] = True
    raw_reviewer_identity_persisted: Literal[False] = False

    @model_validator(mode="after")
    def validate_reviewer(self) -> Self:
        if self.reviewer_id_sha256 == EXPECTED_V1_ASSESSMENT_ACTOR_SHA256:
            raise ValueError("remediation reviewer must differ from the V1 assessment actor")
        return self


class CriterionDraftV2(FrozenModel):
    criterion: RubricCriterion
    score: int | None = Field(default=None, ge=1, le=4)
    evidence_note: str | None = Field(default=None, min_length=1, max_length=4000)


class CriterionSubmissionV2(FrozenModel):
    criterion: RubricCriterion
    score: int = Field(ge=1, le=4)
    evidence_note: str = Field(min_length=1, max_length=4000)


class J7LRemediationSubmissionTemplateV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    criterion_scores: tuple[CriterionDraftV2, ...] = Field(min_length=7, max_length=7)
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = ()
    rationale: str | None = Field(default=None, min_length=20, max_length=8000)


class J7LRemediationSubmissionV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
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


class J7LRemediationHumanWorkItemV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    policy_id: Literal["auragateway-j7l-human-review-remediation-v2"] = (
        "auragateway-j7l-human-review-remediation-v2"
    )
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    queue_index: int = Field(ge=0, le=19)
    source_review_stream: Literal["primary"] = "primary"
    source_assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state: dict[str, object]
    semantic_projection: HumanSemanticProjectionV1
    reviewer_instruction: str = Field(min_length=100, max_length=1600)
    assessment_actor_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    predecessor_model_reference_included: Literal[False] = False
    predecessor_v1_assessment_content_included: Literal[False] = False
    predecessor_comparison_included: Literal[False] = False
    jev_output_included: Literal[False] = False
    authoring_targets_included: Literal[False] = False
    family_metadata_included: Literal[False] = False


class J7LRemediationHumanAssessmentV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_REMEDIATION_HUMAN_ASSESSMENT_COMPLETE"] = (
        "J7L_REMEDIATION_HUMAN_ASSESSMENT_COMPLETE"
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
    predecessor_v1_assessment_content_included_in_work_item: Literal[False] = False
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
        if self.verdict is not derived_verdict(
            self.criterion_scores,
            self.failure_labels,
        ):
            raise ValueError("assessment verdict differs from the frozen derivation rule")
        return self


class J7LRemediationInitializeReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_REMEDIATION_V2_INITIALIZED"] = "J7L_REMEDIATION_V2_INITIALIZED"
    contaminated_v1_submission_count: Literal[8] = EXPECTED_V1_CONTAMINATED_SUBMISSION_COUNT
    fresh_assessment_required_count: Literal[20] = EXPECTED_FRESH_REMEDIATION_ASSESSMENT_COUNT
    reviewer_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_v1_lineage_non_advancing: Literal[True] = True
    model_reference_content_read_for_human_review: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    next_gate: Literal["PREPARE_20_FRESH_BLINDED_HUMAN_ASSESSMENTS"] = (
        "PREPARE_20_FRESH_BLINDED_HUMAN_ASSESSMENTS"
    )


class J7LRemediationPreflightReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_REMEDIATION_INPUTS_VALID"] = "J7L_REMEDIATION_INPUTS_VALID"
    failed_v3_audit_result_sha256: Literal[
        "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"
    ] = EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256
    failed_v3_human_freeze_sha256: Literal[
        "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"
    ] = EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256
    preserved_original_human_assessment_count: Literal[28] = (
        EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
    )
    fresh_remediation_assessment_count: Literal[20] = EXPECTED_FRESH_REMEDIATION_ASSESSMENT_COUNT
    total_case_count: Literal[48] = EXPECTED_CASE_COUNT
    v1_contamination_frozen: Literal[True] = True
    distinct_reviewer_identity_frozen: Literal[True] = True
    model_reference_content_read_for_human_review: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0


class J7LRemediationPrepareReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_REMEDIATION_HUMAN_PACKET_READY"] = "J7L_REMEDIATION_HUMAN_PACKET_READY"
    fresh_remediation_assessment_count: Literal[20] = EXPECTED_FRESH_REMEDIATION_ASSESSMENT_COUNT
    created_work_item_count: int = Field(ge=0, le=20)
    created_submission_template_count: int = Field(ge=0, le=20)
    work_item_root: str
    submission_root: str
    model_reference_content_read_for_human_review: Literal[False] = False
    v1_assessment_content_included_in_work_items: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0


class J7LRemediationQueueStatusV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal[
        "REMEDIATION_HUMAN_REVIEW_PENDING",
        "REMEDIATION_HUMAN_REVIEW_COMPLETE",
    ]
    preserved_original_human_assessment_count: Literal[28] = (
        EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
    )
    remediation_completed_assessment_count: int = Field(ge=0, le=20)
    total_clean_human_assessment_count: int = Field(ge=28, le=48)
    pending_remediation_assessment_count: int = Field(ge=0, le=20)
    next_case_id: str | None = Field(default=None, pattern=r"^j7l-dev-[0-9]{3}$")
    next_work_item_path: str | None = None
    next_submission_path: str | None = None
    v1_lineage_non_advancing: Literal[True] = True
    model_reference_content_read_for_human_review: Literal[False] = False
    material_disagreement_evaluated_for_full_48: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if (
            self.preserved_original_human_assessment_count
            + self.remediation_completed_assessment_count
            != self.total_clean_human_assessment_count
        ):
            raise ValueError("remediation completed-count accounting drifted")
        if (
            self.remediation_completed_assessment_count + self.pending_remediation_assessment_count
            != EXPECTED_FRESH_REMEDIATION_ASSESSMENT_COUNT
        ):
            raise ValueError("remediation pending-count accounting drifted")
        complete = self.pending_remediation_assessment_count == 0
        expected_status = (
            "REMEDIATION_HUMAN_REVIEW_COMPLETE" if complete else "REMEDIATION_HUMAN_REVIEW_PENDING"
        )
        if self.status != expected_status:
            raise ValueError("remediation queue status does not match pending count")
        if complete != (self.next_case_id is None):
            raise ValueError("remediation queue next-case state drifted")
        return self


class J7LRemediationSubmissionReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_REMEDIATION_HUMAN_ASSESSMENT_PERSISTED"] = (
        "J7L_REMEDIATION_HUMAN_ASSESSMENT_PERSISTED"
    )
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created: bool
    total_clean_human_assessment_count: int = Field(ge=29, le=48)
    pending_remediation_assessment_count: int = Field(ge=0, le=19)
    next_case_id: str | None = Field(default=None, pattern=r"^j7l-dev-[0-9]{3}$")
    model_reference_content_read_for_human_review: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0


class J7LFullHumanInventoryFreezeV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_REMEDIATION_FULL_HUMAN_INVENTORY_FROZEN"] = (
        "J7L_REMEDIATION_FULL_HUMAN_INVENTORY_FROZEN"
    )
    predecessor_human_freeze_sha256: Literal[
        "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"
    ] = EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256
    preserved_original_human_assessment_count: Literal[28] = (
        EXPECTED_PRESERVED_HUMAN_ASSESSMENT_COUNT
    )
    remediation_human_assessment_count: Literal[20] = EXPECTED_FRESH_REMEDIATION_ASSESSMENT_COUNT
    full_human_assessment_count: Literal[48] = EXPECTED_CASE_COUNT
    remediation_reviewer_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    remediation_assessments: tuple[AssessmentDigestV2, ...] = Field(
        min_length=20,
        max_length=20,
    )
    frozen_before_full_48_model_comparison: Literal[True] = True
    model_reference_content_read_before_freeze: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    next_gate: Literal["IMPLEMENT_FULL_48_HUMAN_VS_V3_COMPARISON"] = (
        "IMPLEMENT_FULL_48_HUMAN_VS_V3_COMPARISON"
    )

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        ids = tuple(item.case_id for item in self.remediation_assessments)
        if ids != EXPECTED_REMEDIATION_CASE_IDS:
            raise ValueError("remediation freeze must contain the exact ordered 20-case inventory")
        return self
