"""Typed contracts for the J7L human-first development V2 lineage."""

from __future__ import annotations

from collections import Counter
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v1 import J7LCaseFamily
from auragateway.contracts.quality_semantic_projection_v1 import HumanSemanticProjectionV1

EXPECTED_CASE_COUNT: Literal[48] = 48
EXPECTED_FAMILY_CASE_COUNT: Literal[12] = 12
EXPECTED_MINIMUM_PASS_COUNT: Literal[16] = 16
EXPECTED_MINIMUM_FAIL_COUNT: Literal[16] = 16
EXPECTED_MINIMUM_POSITIVE_SUPPORT_PER_LABEL: Literal[2] = 2
EXPECTED_MINIMUM_NEAR_MISS_SUPPORT_PER_LABEL: Literal[2] = 2
EXPECTED_MINIMUM_DISTINCT_SCORES_PER_CRITERION: Literal[3] = 3
EXPECTED_MINIMUM_LOW_SCORES_PER_CRITERION: Literal[4] = 4
EXPECTED_MINIMUM_HIGH_SCORES_PER_CRITERION: Literal[4] = 4
EXPECTED_MINIMUM_TERMINAL_MATERIAL_CASES: Literal[8] = 8

EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256: Literal[
    "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"
] = "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"

EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256: Literal[
    "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"
] = "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"

EXPECTED_HISTORICAL_AUTHORING_CASE_SET_SHA256: Literal[
    "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
] = "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"

EXPECTED_HUMAN_PROJECTION_SHA256: Literal[
    "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
] = "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"

EXPECTED_SEMANTIC_REGISTRY_SHA256: Literal[
    "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
] = "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"

SIMILARITY_ALGORITHM_ID: Literal[
    "nfkc-casefold-whitespace-canonical-json__max-sequence-token-jaccard-v1"
] = "nfkc-casefold-whitespace-canonical-json__max-sequence-token-jaccard-v1"

FORBIDDEN_REVIEWER_SAFE_KEYS = frozenset(
    {
        "case_id",
        "case_index",
        "family",
        "case_family",
        "authoring_notes",
        "intended_criterion_scores",
        "intended_failure_labels",
        "near_miss_label_targets",
        "intended_verdict",
        "expected_verdict",
        "expected_failure_labels",
        "human_truth",
        "model_reference",
        "jev_output",
        "baseline_output",
        "intervention_output",
        "provider",
        "model",
    }
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def derived_verdict(
    criterion_scores: dict[RubricCriterion, int],
    failure_labels: tuple[EpisodeFailureLabel, ...],
) -> ReviewVerdict:
    values = tuple(criterion_scores[criterion] for criterion in RubricCriterion)
    passed = sum(values) >= 21 and min(values) >= 2 and not failure_labels
    return ReviewVerdict.PASS if passed else ReviewVerdict.FAIL


def _walk_keys(value: JsonValue) -> tuple[str, ...]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
    if isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return tuple(keys)


class J7LHumanFirstDevelopmentPolicyV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    policy_id: Literal["auragateway-j7l-human-first-development-v2"] = (
        "auragateway-j7l-human-first-development-v2"
    )

    case_count: Literal[48] = EXPECTED_CASE_COUNT
    family_case_count: Literal[12] = EXPECTED_FAMILY_CASE_COUNT
    single_human_development_reference: Literal[True] = True
    independent_qualification_claim_permitted: Literal[False] = False

    minimum_pass_count: Literal[16] = EXPECTED_MINIMUM_PASS_COUNT
    minimum_fail_count: Literal[16] = EXPECTED_MINIMUM_FAIL_COUNT
    minimum_positive_support_per_failure_label: Literal[2] = (
        EXPECTED_MINIMUM_POSITIVE_SUPPORT_PER_LABEL
    )
    minimum_near_miss_negative_support_per_failure_label: Literal[2] = (
        EXPECTED_MINIMUM_NEAR_MISS_SUPPORT_PER_LABEL
    )
    minimum_distinct_scores_per_criterion: Literal[3] = (
        EXPECTED_MINIMUM_DISTINCT_SCORES_PER_CRITERION
    )
    minimum_low_scores_per_criterion: Literal[4] = EXPECTED_MINIMUM_LOW_SCORES_PER_CRITERION
    minimum_high_scores_per_criterion: Literal[4] = EXPECTED_MINIMUM_HIGH_SCORES_PER_CRITERION
    minimum_terminal_material_evidence_cases: Literal[8] = EXPECTED_MINIMUM_TERMINAL_MATERIAL_CASES

    historical_v3_failure_preserved: Literal[True] = True
    contaminated_v1_lineage_non_advancing: Literal[True] = True
    distinct_human_remediation_v2_dormant: Literal[True] = True

    fresh_case_namespace_required: Literal[True] = True
    historical_similarity_profile_required_before_new_population_read: Literal[True] = True
    novelty_threshold_required_before_new_population_read: Literal[True] = True
    exact_historical_case_reuse_permitted: Literal[False] = False
    fuzzy_historical_case_reuse_permitted: Literal[False] = False

    authoring_context_must_be_separate_from_human_review_context: Literal[True] = True
    hidden_authoring_targets_must_remain_unread_by_human_reviewer: Literal[True] = True
    human_reference_must_freeze_before_model_reveal: Literal[True] = True

    provider_requests_authorized: Literal[False] = False
    jev_requests_authorized: Literal[False] = False
    model_reference_execution_authorized: Literal[False] = False

    j7m_qualification_claim_permitted: Literal[False] = False
    final_abc_quality_claim_permitted: Literal[False] = False
    production_readiness_claim_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        if self.case_count != self.family_case_count * len(J7LCaseFamily):
            raise ValueError("J7L V2 family counts do not reconcile to case_count")
        return self


class J7LHumanFirstDevelopmentCaseV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    case_id: str = Field(pattern=r"^j7l-v2-dev-[0-9]{3}$")
    case_index: int = Field(ge=0, le=47)
    family: J7LCaseFamily

    reviewer_safe_state: dict[str, JsonValue]

    intended_criterion_scores: dict[RubricCriterion, int]
    intended_failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    near_miss_label_targets: tuple[EpisodeFailureLabel, ...] = ()
    intended_verdict: ReviewVerdict
    terminal_action_evidence_material: bool = False
    authoring_notes: str = Field(min_length=20, max_length=4000)

    @model_validator(mode="after")
    def validate_case(self) -> Self:
        expected_case_id = f"j7l-v2-dev-{self.case_index + 1:03d}"
        if self.case_id != expected_case_id:
            raise ValueError("J7L V2 case_id must match case_index")

        if not self.reviewer_safe_state:
            raise ValueError("J7L V2 reviewer-safe state must not be empty")

        visible_keys = set(_walk_keys(self.reviewer_safe_state))
        leaked = sorted(visible_keys & FORBIDDEN_REVIEWER_SAFE_KEYS)
        if leaked:
            raise ValueError(
                "J7L V2 reviewer-safe state contains forbidden keys: " + ",".join(leaked)
            )

        if set(self.intended_criterion_scores) != set(RubricCriterion):
            raise ValueError("J7L V2 intended scores must cover every rubric criterion")
        if any(score < 1 or score > 4 for score in self.intended_criterion_scores.values()):
            raise ValueError("J7L V2 intended criterion scores must remain in [1,4]")

        if len(self.intended_failure_labels) != len(set(self.intended_failure_labels)):
            raise ValueError("J7L V2 intended failure labels must be unique")
        if len(self.near_miss_label_targets) != len(set(self.near_miss_label_targets)):
            raise ValueError("J7L V2 near-miss label targets must be unique")

        overlap = set(self.intended_failure_labels) & set(self.near_miss_label_targets)
        if overlap:
            raise ValueError("J7L V2 positive and near-miss label targets must be disjoint")

        expected_verdict = derived_verdict(
            self.intended_criterion_scores,
            self.intended_failure_labels,
        )
        if self.intended_verdict is not expected_verdict:
            raise ValueError("J7L V2 intended verdict differs from frozen derivation rule")

        if self.family is J7LCaseFamily.ORDINARY_CLEAN:
            if self.intended_verdict is not ReviewVerdict.PASS:
                raise ValueError("ordinary-clean authoring cases must target PASS")
            if self.intended_failure_labels:
                raise ValueError("ordinary-clean authoring cases must not target failure labels")

        if self.family is J7LCaseFamily.CLEAR_FAILURE:
            if self.intended_verdict is not ReviewVerdict.FAIL:
                raise ValueError("clear-failure authoring cases must target FAIL")
            if not self.intended_failure_labels:
                raise ValueError("clear-failure authoring cases require a positive failure label")

        if self.family is J7LCaseFamily.ONTOLOGY_NEAR_MISS:
            if self.intended_verdict is not ReviewVerdict.PASS:
                raise ValueError("ontology-near-miss authoring cases must target PASS")
            if self.intended_failure_labels:
                raise ValueError("ontology-near-miss cases must not target positive failure labels")
            if not self.near_miss_label_targets:
                raise ValueError("ontology-near-miss cases require near-miss label targets")

        return self


class J7LHumanFirstDevelopmentCaseSetV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    set_id: Literal["auragateway-j7l-human-first-development-cases-v2"] = (
        "auragateway-j7l-human-first-development-cases-v2"
    )
    status: Literal["SEALED_PRE_HUMAN"] = "SEALED_PRE_HUMAN"
    authoring_handoff_id: Literal["auragateway-j7l-human-first-v2-authoring-handoff-v1"] = (
        "auragateway-j7l-human-first-v2-authoring-handoff-v1"
    )
    authoring_context: Literal["SEPARATE_SEALED_CONTEXT"] = "SEPARATE_SEALED_CONTEXT"
    authoring_assistant_used: Literal[True] = True
    historical_case_content_consulted: Literal[False] = False
    human_reviewer_inspected_hidden_authoring_payload: Literal[False] = False

    cases: tuple[J7LHumanFirstDevelopmentCaseV2, ...] = Field(min_length=48, max_length=48)

    benchmark_model_reveal_performed: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    human_reference_frozen: Literal[False] = False

    @model_validator(mode="after")
    def validate_case_set(self) -> Self:
        case_ids = tuple(case.case_id for case in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("J7L V2 case IDs must be unique")

        indices = tuple(case.case_index for case in self.cases)
        if indices != tuple(range(EXPECTED_CASE_COUNT)):
            raise ValueError("J7L V2 case indices must be exactly 0..47 in frozen order")

        counts = Counter(case.family for case in self.cases)
        expected = {family: EXPECTED_FAMILY_CASE_COUNT for family in J7LCaseFamily}
        if counts != expected:
            raise ValueError("J7L V2 case-family inventory must be exactly 12 per family")

        return self


class J7LHistoricalDispositionV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_HUMAN_FIRST_V2_HISTORICAL_BOUNDARY_LOCKED"] = (
        "J7L_HUMAN_FIRST_V2_HISTORICAL_BOUNDARY_LOCKED"
    )
    failed_v3_audit_result_sha256: Literal[
        "613e279f23cb14c5b2d5a87db16d4a2c666ec0a02fd2b434afd0249b118b6242"
    ] = EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256
    failed_v3_human_freeze_sha256: Literal[
        "57673df0874d344986fbb12480e07f80aee3801354286679e9f2529020fa448e"
    ] = EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256
    contaminated_v1_submitted_assessment_count: Literal[8] = 8
    contaminated_v1_total_recorded_human_count: Literal[36] = 36
    contaminated_v1_pending_count: Literal[12] = 12
    contaminated_v1_next_case_id: Literal["j7l-dev-011"] = "j7l-dev-011"
    contaminated_v1_lineage_non_advancing: Literal[True] = True
    distinct_human_remediation_v2_status: Literal["DORMANT_UNINITIALIZED"] = "DORMANT_UNINITIALIZED"
    distinct_human_remediation_v2_local_root_absent: Literal[True] = True
    historical_evidence_mutated: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    next_gate: Literal["PROFILE_HISTORICAL_CASE_SIMILARITY"] = "PROFILE_HISTORICAL_CASE_SIMILARITY"


class J7LHistoricalSimilarityProfileV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_HISTORICAL_SIMILARITY_PROFILE_FROZEN"] = (
        "J7L_V2_HISTORICAL_SIMILARITY_PROFILE_FROZEN"
    )
    algorithm_id: Literal[
        "nfkc-casefold-whitespace-canonical-json__max-sequence-token-jaccard-v1"
    ] = SIMILARITY_ALGORITHM_ID
    historical_authoring_case_set_sha256: Literal[
        "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
    ] = EXPECTED_HISTORICAL_AUTHORING_CASE_SET_SHA256
    historical_case_count: Literal[48] = EXPECTED_CASE_COUNT
    pair_count: Literal[1128] = 1128
    minimum_similarity: float = Field(ge=0.0, le=1.0)
    p50_similarity: float = Field(ge=0.0, le=1.0)
    p90_similarity: float = Field(ge=0.0, le=1.0)
    p95_similarity: float = Field(ge=0.0, le=1.0)
    p99_similarity: float = Field(ge=0.0, le=1.0)
    maximum_similarity: float = Field(ge=0.0, le=1.0)
    new_population_read: Literal[False] = False
    profile_frozen_before_new_population_read: Literal[True] = True
    next_gate: Literal["FREEZE_NOVELTY_THRESHOLD"] = "FREEZE_NOVELTY_THRESHOLD"

    @model_validator(mode="after")
    def validate_ordering(self) -> Self:
        ordered = (
            self.minimum_similarity,
            self.p50_similarity,
            self.p90_similarity,
            self.p95_similarity,
            self.p99_similarity,
            self.maximum_similarity,
        )
        if tuple(sorted(ordered)) != ordered:
            raise ValueError("historical similarity profile quantiles are not monotonic")
        return self


class J7LNoveltyPolicyV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_NOVELTY_POLICY_FROZEN"] = "J7L_V2_NOVELTY_POLICY_FROZEN"
    algorithm_id: Literal[
        "nfkc-casefold-whitespace-canonical-json__max-sequence-token-jaccard-v1"
    ] = SIMILARITY_ALGORITHM_ID
    historical_similarity_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    maximum_pair_similarity_allowed: float = Field(gt=0.0, lt=1.0)
    exact_canonical_duplicate_permitted: Literal[False] = False
    exact_normalized_duplicate_permitted: Literal[False] = False
    threshold_selected_before_new_population_read: Literal[True] = True
    new_population_read_at_policy_freeze: Literal[False] = False
    next_gate: Literal["IMPORT_SEALED_AUTHORING_POPULATION"] = "IMPORT_SEALED_AUTHORING_POPULATION"


class J7LAuthoringCoverageReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_AUTHORING_COVERAGE_VALID"] = "J7L_V2_AUTHORING_COVERAGE_VALID"
    case_count: Literal[48] = EXPECTED_CASE_COUNT
    family_counts: dict[J7LCaseFamily, int]
    intended_pass_count: int = Field(ge=16, le=48)
    intended_fail_count: int = Field(ge=16, le=48)
    minimum_positive_support_observed: int = Field(ge=2)
    minimum_near_miss_support_observed: int = Field(ge=2)
    minimum_distinct_scores_observed: int = Field(ge=3, le=4)
    minimum_low_scores_observed: int = Field(ge=4)
    minimum_high_scores_observed: int = Field(ge=4)
    terminal_material_evidence_case_count: int = Field(ge=8, le=12)
    authoring_targets_are_not_human_truth: Literal[True] = True

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.intended_pass_count + self.intended_fail_count != self.case_count:
            raise ValueError("J7L V2 intended verdict counts do not reconcile")
        expected = {family: EXPECTED_FAMILY_CASE_COUNT for family in J7LCaseFamily}
        if self.family_counts != expected:
            raise ValueError("J7L V2 authoring coverage family counts drifted")
        return self


class J7LNoveltyReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    status: Literal["J7L_V2_NOVELTY_VALID"] = "J7L_V2_NOVELTY_VALID"
    case_count: Literal[48] = EXPECTED_CASE_COUNT
    historical_case_count: Literal[48] = EXPECTED_CASE_COUNT
    maximum_new_to_historical_similarity: float = Field(ge=0.0, lt=1.0)
    maximum_within_new_similarity: float = Field(ge=0.0, lt=1.0)
    exact_canonical_duplicate_count: Literal[0] = 0
    exact_normalized_duplicate_count: Literal[0] = 0
    threshold_respected: Literal[True] = True


class J7LReviewScheduleEntryV2(FrozenModel):
    case_id: str = Field(pattern=r"^j7l-v2-dev-[0-9]{3}$")
    case_index: int = Field(ge=0, le=47)
    family: J7LCaseFamily
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    primary_assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")


class J7LReviewScheduleV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    schedule_id: Literal["auragateway-j7l-v2-human-review-schedule-v1"] = (
        "auragateway-j7l-v2-human-review-schedule-v1"
    )
    primary_assignment_count: Literal[48] = EXPECTED_CASE_COUNT
    entries: tuple[J7LReviewScheduleEntryV2, ...] = Field(min_length=48, max_length=48)

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        if tuple(item.case_index for item in self.entries) != tuple(range(48)):
            raise ValueError("J7L V2 review schedule must preserve frozen case order")
        review_ids = tuple(item.review_item_id for item in self.entries)
        assignment_ids = tuple(item.primary_assignment_id for item in self.entries)
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("J7L V2 review item IDs must be unique")
        if len(assignment_ids) != len(set(assignment_ids)):
            raise ValueError("J7L V2 primary assignment IDs must be unique")
        return self


class J7LVisibleReviewItemV2(FrozenModel):
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state: dict[str, JsonValue]


class J7LReviewerExportV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    export_id: Literal["auragateway-j7l-v2-primary-reviewer-export-v1"] = (
        "auragateway-j7l-v2-primary-reviewer-export-v1"
    )
    review_stream: Literal["primary"] = "primary"
    human_projection_sha256: Literal[
        "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    ] = EXPECTED_HUMAN_PROJECTION_SHA256
    semantic_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = EXPECTED_SEMANTIC_REGISTRY_SHA256
    semantic_projection: HumanSemanticProjectionV1
    reviewer_instruction: str = Field(min_length=100, max_length=1600)
    item_count: Literal[48] = EXPECTED_CASE_COUNT
    items: tuple[J7LVisibleReviewItemV2, ...] = Field(min_length=48, max_length=48)

    @model_validator(mode="after")
    def validate_export(self) -> Self:
        assignment_ids = tuple(item.assignment_id for item in self.items)
        review_ids = tuple(item.review_item_id for item in self.items)
        if len(assignment_ids) != len(set(assignment_ids)):
            raise ValueError("J7L V2 reviewer export assignment IDs must be unique")
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("J7L V2 reviewer export review item IDs must be unique")
        return self


class J7LCaseSetFreezeReceiptV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    receipt_id: Literal["auragateway-j7l-human-first-v2-case-set-freeze-v1"] = (
        "auragateway-j7l-human-first-v2-case-set-freeze-v1"
    )
    status: Literal["J7L_V2_CASE_SET_FROZEN_FOR_HUMAN_REVIEW"] = (
        "J7L_V2_CASE_SET_FROZEN_FOR_HUMAN_REVIEW"
    )
    authoring_case_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    historical_similarity_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    novelty_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_primary_export_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    case_count: Literal[48] = EXPECTED_CASE_COUNT
    family_case_count: Literal[12] = EXPECTED_FAMILY_CASE_COUNT
    authoring_coverage_valid: Literal[True] = True
    novelty_valid: Literal[True] = True

    authoring_targets_publicly_persisted: Literal[False] = False
    reviewer_export_contains_authoring_metadata: Literal[False] = False
    human_reference_frozen: Literal[False] = False
    model_reveal_performed: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    next_gate: Literal["COMPLETE_48_SINGLE_HUMAN_ASSESSMENTS"] = (
        "COMPLETE_48_SINGLE_HUMAN_ASSESSMENTS"
    )
