"""Typed contracts for J7L evaluator development evaluation v1."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel

EXPECTED_CASE_COUNT = 48
EXPECTED_PRIMARY_REVIEW_COUNT = 48
EXPECTED_SECONDARY_REVIEW_COUNT = 24
EXPECTED_FAMILY_CASE_COUNT = 12
EXPECTED_MODEL_PIN = "jev-1.13.0"

EXPECTED_REGISTRY_SHA256 = "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
EXPECTED_REGISTRY_ARTIFACT_SHA256 = (
    "0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c"
)
EXPECTED_HUMAN_PROJECTION_SHA256 = (
    "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
)
EXPECTED_MODEL_PROJECTION_SHA256 = (
    "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
)
EXPECTED_CONSTITUTION_SHA256 = "b2bcb0152cfed2b32e4516129db09bbe1853d28c7b776305d7d0e10d7a2c2dd5"

THRESHOLD_GRID: tuple[float, ...] = tuple(index / 100 for index in range(5, 100, 5))

FORBIDDEN_VISIBLE_KEYS = frozenset(
    {
        "case_family",
        "positive_label_targets",
        "near_miss_label_targets",
        "authoring_notes",
        "human_truth",
        "expected_verdict",
        "expected_failure_labels",
        "baseline_output",
        "intervention_output",
        "experiment_condition",
        "condition",
        "condition_id",
        "provider",
        "model",
        "reviewer_id_sha256",
        "adjudicator_id_sha256",
        "human_adjudication",
        "authoritative_adjudication",
        "final_adjudication",
    }
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class J7LCaseFamily(StrEnum):
    ORDINARY_CLEAN = "ordinary_clean"
    CLEAR_FAILURE = "clear_failure"
    TERMINAL_NON_SUBSTANTIVE = "terminal_non_substantive"
    ONTOLOGY_NEAR_MISS = "ontology_near_miss"


class J7LEvaluatorCondition(StrEnum):
    BASELINE_V1_SEMANTICS = "BASELINE_V1_SEMANTICS"
    INTERVENTION_V2_SEMANTICS = "INTERVENTION_V2_SEMANTICS"


class J7LHumanAuthority(StrEnum):
    PRIMARY = "primary"
    ADJUDICATION = "adjudication"


def _walk_keys(value: JsonValue) -> tuple[str, ...]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return tuple(keys)


class J7LDevelopmentPolicyV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["auragateway-j7l-development-evaluation-v1"] = (
        "auragateway-j7l-development-evaluation-v1"
    )

    case_count: Literal[48] = 48
    family_case_count: Literal[12] = 12
    primary_review_count: Literal[48] = 48
    secondary_review_count: Literal[24] = 24

    minimum_pass_count: Literal[16] = 16
    minimum_fail_count: Literal[16] = 16
    minimum_positive_support_per_failure_label: Literal[2] = 2
    minimum_near_miss_negative_support_per_failure_label: Literal[2] = 2

    minimum_distinct_scores_per_criterion: Literal[3] = 3
    minimum_low_scores_per_criterion: Literal[4] = 4
    minimum_high_scores_per_criterion: Literal[4] = 4
    minimum_terminal_material_evidence_cases: Literal[8] = 8

    planned_provider_request_count: Literal[96] = 96
    max_in_flight_requests: Literal[1] = 1
    automatic_retry_permitted: Literal[False] = False
    replacement_after_model_reveal_permitted: Literal[False] = False
    existing_valid_response_skips_replay: Literal[True] = True
    paired_case_bytes_required: Literal[True] = True
    paired_model_pin_required: Literal[True] = True
    paired_question_inventory_required: Literal[True] = True
    only_semantic_instruction_content_may_differ: Literal[True] = True

    model_pin: Literal["jev-1.13.0"] = "jev-1.13.0"
    threshold_grid: tuple[float, ...] = THRESHOLD_GRID

    development_threshold_selection_only: Literal[True] = True
    independent_qualification_claim_permitted: Literal[False] = False
    deployment_claim_permitted: Literal[False] = False
    final_342_effect_claim_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        if self.case_count != self.family_case_count * len(J7LCaseFamily):
            raise ValueError("J7L family counts do not reconcile to case_count")
        if self.planned_provider_request_count != self.case_count * len(J7LEvaluatorCondition):
            raise ValueError("J7L request count does not reconcile to paired conditions")
        if self.threshold_grid != THRESHOLD_GRID:
            raise ValueError("J7L threshold grid drifted")
        return self


class J7LAdvancementPolicyV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"

    minimum_overall_criterion_exact_accuracy: float = 0.80
    minimum_overall_criterion_within_one_accuracy: float = 0.97
    maximum_catastrophic_criterion_disagreement_rate: float = 0.03
    minimum_selected_threshold_derived_verdict_accuracy: float = 0.90
    minimum_selected_threshold_failure_micro_f1: float = 0.85
    minimum_selected_threshold_exact_label_set_accuracy: float = 0.75
    maximum_pooled_failure_probability_ece: float = 0.10

    maximum_overall_exact_accuracy_regression: float = 0.02
    maximum_per_criterion_exact_accuracy_regression: float = 0.05
    catastrophic_disagreement_increase_permitted: Literal[False] = False
    maximum_failure_brier_regression: float = 0.02
    maximum_near_miss_false_positive_rate_regression: float = 0.05

    minimum_terminal_slice_evidence_grounding_exact_accuracy: float = 0.85
    maximum_terminal_slice_evidence_grounding_one_four_disagreements: Literal[0] = 0
    maximum_near_miss_false_positive_rate: float = 0.15

    development_only: Literal[True] = True
    production_threshold: Literal[False] = False

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        expected = {
            "minimum_overall_criterion_exact_accuracy": 0.80,
            "minimum_overall_criterion_within_one_accuracy": 0.97,
            "maximum_catastrophic_criterion_disagreement_rate": 0.03,
            "minimum_selected_threshold_derived_verdict_accuracy": 0.90,
            "minimum_selected_threshold_failure_micro_f1": 0.85,
            "minimum_selected_threshold_exact_label_set_accuracy": 0.75,
            "maximum_pooled_failure_probability_ece": 0.10,
            "maximum_overall_exact_accuracy_regression": 0.02,
            "maximum_per_criterion_exact_accuracy_regression": 0.05,
            "maximum_failure_brier_regression": 0.02,
            "maximum_near_miss_false_positive_rate_regression": 0.05,
            "minimum_terminal_slice_evidence_grounding_exact_accuracy": 0.85,
            "maximum_near_miss_false_positive_rate": 0.15,
        }
        drift = tuple(
            name
            for name, expected_value in expected.items()
            if getattr(self, name) != expected_value
        )
        if drift:
            raise ValueError("J7L advancement policy thresholds drifted: " + ",".join(drift))
        return self


class J7LDevelopmentConstitutionV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    constitution_id: Literal["auragateway-j7l-development-constitution-v1"] = (
        "auragateway-j7l-development-constitution-v1"
    )

    semantic_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    semantic_registry_artifact_sha256: Literal[
        "0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c"
    ] = "0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c"
    human_projection_sha256: Literal[
        "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    ] = "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    model_projection_sha256: Literal[
        "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
    ] = "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
    constitution_markdown_sha256: Literal[
        "b2bcb0152cfed2b32e4516129db09bbe1853d28c7b776305d7d0e10d7a2c2dd5"
    ] = "b2bcb0152cfed2b32e4516129db09bbe1853d28c7b776305d7d0e10d7a2c2dd5"

    development_policy: J7LDevelopmentPolicyV1 = Field(default_factory=J7LDevelopmentPolicyV1)
    advancement_policy: J7LAdvancementPolicyV1 = Field(default_factory=J7LAdvancementPolicyV1)

    baseline_condition: Literal["BASELINE_V1_SEMANTICS"] = (
        J7LEvaluatorCondition.BASELINE_V1_SEMANTICS.value
    )
    intervention_condition: Literal["INTERVENTION_V2_SEMANTICS"] = (
        J7LEvaluatorCondition.INTERVENTION_V2_SEMANTICS.value
    )

    human_authority_must_freeze_before_model_reveal: Literal[True] = True
    final_342_permitted_as_j7l_case_source: Literal[False] = False
    semantic_registry_mutation_permitted: Literal[False] = False
    private_evaluator_semantics_permitted: Literal[False] = False
    next_gate_on_pass: Literal["J7M_HELD_OUT_QUALIFICATION_V1"] = "J7M_HELD_OUT_QUALIFICATION_V1"


class J7LDevelopmentCaseV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    case_index: int = Field(ge=0, le=47)
    family: J7LCaseFamily

    reviewer_safe_state: dict[str, JsonValue]
    positive_label_targets: tuple[EpisodeFailureLabel, ...] = ()
    near_miss_label_targets: tuple[EpisodeFailureLabel, ...] = ()
    terminal_action_evidence_material: bool = False

    @model_validator(mode="after")
    def validate_case(self) -> Self:
        expected_case_id = f"j7l-dev-{self.case_index + 1:03d}"
        if self.case_id != expected_case_id:
            raise ValueError("J7L case_id must match case_index")

        if not self.reviewer_safe_state:
            raise ValueError("J7L reviewer-safe state must not be empty")

        visible_keys = set(_walk_keys(self.reviewer_safe_state))
        leaked = sorted(visible_keys & FORBIDDEN_VISIBLE_KEYS)
        if leaked:
            raise ValueError("J7L reviewer-safe state contains forbidden keys: " + ",".join(leaked))

        if len(self.positive_label_targets) != len(set(self.positive_label_targets)):
            raise ValueError("J7L positive-label targets must be unique")

        if len(self.near_miss_label_targets) != len(set(self.near_miss_label_targets)):
            raise ValueError("J7L near-miss-label targets must be unique")

        overlap = set(self.positive_label_targets) & set(self.near_miss_label_targets)
        if overlap:
            raise ValueError("J7L positive and near-miss label targets must be disjoint")

        if self.family is J7LCaseFamily.ONTOLOGY_NEAR_MISS and not self.near_miss_label_targets:
            raise ValueError("ontology near-miss cases require near-miss label targets")

        return self


class J7LDevelopmentCaseSetV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    set_id: Literal["auragateway-j7l-development-cases-v1"] = "auragateway-j7l-development-cases-v1"
    status: Literal["FROZEN_PRE_MODEL"] = "FROZEN_PRE_MODEL"

    cases: tuple[J7LDevelopmentCaseV1, ...] = Field(min_length=48, max_length=48)

    final_342_case_reuse_permitted: Literal[False] = False
    model_reveal_performed: Literal[False] = False
    provider_requests_performed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_case_set(self) -> Self:
        case_ids = tuple(case.case_id for case in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("J7L case IDs must be unique")

        indices = tuple(case.case_index for case in self.cases)
        if indices != tuple(range(EXPECTED_CASE_COUNT)):
            raise ValueError("J7L case indices must be exactly 0..47 in frozen order")

        counts = Counter(case.family for case in self.cases)
        expected = {family: EXPECTED_FAMILY_CASE_COUNT for family in J7LCaseFamily}
        if counts != expected:
            raise ValueError("J7L case-family inventory must be exactly 12 per family")

        terminal_material = sum(
            case.family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE
            and case.terminal_action_evidence_material
            for case in self.cases
        )
        if terminal_material < 8:
            raise ValueError(
                "J7L terminal/non-substantive family needs at least 8 material-evidence cases"
            )

        return self


class J7LAuthoritativeHumanTruthV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    authority: J7LHumanAuthority

    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    verdict: ReviewVerdict

    primary_review_complete: Literal[True] = True
    secondary_review_required: bool
    secondary_review_complete: bool
    material_disagreement: bool
    adjudication_complete: bool

    @model_validator(mode="after")
    def validate_truth(self) -> Self:
        if set(self.criterion_scores) != set(RubricCriterion):
            raise ValueError("J7L human truth must score every criterion")

        if any(score < 1 or score > 4 for score in self.criterion_scores.values()):
            raise ValueError("J7L human truth criterion scores must be in [1,4]")

        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("J7L human truth failure labels must be unique")

        if self.secondary_review_required != self.secondary_review_complete:
            raise ValueError("required J7L secondary review must be complete before truth freeze")

        if self.material_disagreement and not self.secondary_review_required:
            raise ValueError("J7L material disagreement requires a secondary review")

        if self.material_disagreement:
            if not self.adjudication_complete:
                raise ValueError("J7L material disagreement requires completed adjudication")
            if self.authority is not J7LHumanAuthority.ADJUDICATION:
                raise ValueError("J7L material disagreement must resolve to adjudication authority")
        else:
            if self.adjudication_complete:
                raise ValueError("J7L adjudication is not permitted without material disagreement")
            if self.authority is not J7LHumanAuthority.PRIMARY:
                raise ValueError("J7L non-disagreement truth must retain primary authority")

        return self


class J7LAuthoritativeHumanTruthSetV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    truth_set_id: Literal["auragateway-j7l-human-truth-v1"] = "auragateway-j7l-human-truth-v1"

    cases: tuple[J7LAuthoritativeHumanTruthV1, ...] = Field(
        min_length=48,
        max_length=48,
    )

    human_authority_frozen_before_model_reveal: Literal[True] = True
    model_reveal_performed: Literal[False] = False
    provider_requests_performed_before_freeze: Literal[0] = 0

    @model_validator(mode="after")
    def validate_truth_set(self) -> Self:
        case_ids = tuple(case.case_id for case in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("J7L human truth case IDs must be unique")
        return self


class J7LPrerequisiteReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_DEVELOPMENT_PREREQUISITES_PASS"] = "J7L_DEVELOPMENT_PREREQUISITES_PASS"

    constitution_markdown_sha256: Literal[
        "b2bcb0152cfed2b32e4516129db09bbe1853d28c7b776305d7d0e10d7a2c2dd5"
    ] = "b2bcb0152cfed2b32e4516129db09bbe1853d28c7b776305d7d0e10d7a2c2dd5"
    semantic_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    human_projection_sha256: Literal[
        "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    ] = "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    model_projection_sha256: Literal[
        "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
    ] = "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
    j7k_parity_receipt_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    jev_request_performed: Literal[False] = False
    network_access_performed: Literal[False] = False
    deployment_threshold_selected: Literal[False] = False
    human_truth_frozen: Literal[False] = False
    next_gate: Literal["AUTHOR_J7L_48_CASE_DEVELOPMENT_SET"] = "AUTHOR_J7L_48_CASE_DEVELOPMENT_SET"


class J7LCoverageReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_HUMAN_TRUTH_COVERAGE_PASS"] = "J7L_HUMAN_TRUTH_COVERAGE_PASS"

    case_count: Literal[48] = 48
    pass_count: int = Field(ge=16, le=48)
    fail_count: int = Field(ge=16, le=48)
    secondary_review_count: Literal[24] = 24

    minimum_positive_support_observed: int = Field(ge=2)
    minimum_near_miss_negative_support_observed: int = Field(ge=2)
    minimum_distinct_scores_observed: int = Field(ge=3)
    minimum_low_score_count_observed: int = Field(ge=4)
    minimum_high_score_count_observed: int = Field(ge=4)
    terminal_material_evidence_case_count: int = Field(ge=8, le=12)

    human_authority_frozen_before_model_reveal: Literal[True] = True
    provider_requests_performed_before_freeze: Literal[0] = 0
    next_gate: Literal["FREEZE_J7L_PAIRED_MODEL_REQUEST_INVENTORY"] = (
        "FREEZE_J7L_PAIRED_MODEL_REQUEST_INVENTORY"
    )
