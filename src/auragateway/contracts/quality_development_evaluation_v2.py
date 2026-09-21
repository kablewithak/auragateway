"""Typed contracts for the J7L model-derived reference successor."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v1 import (
    THRESHOLD_GRID,
    J7LAdvancementPolicyV1,
    J7LEvaluatorCondition,
)

EXPECTED_CASE_COUNT = 48
EXPECTED_JEV_REQUEST_COUNT = 96
EXPECTED_JEV_MODEL_PIN = "jev-1.13.0"

EXPECTED_AUTHORING_CASE_SET_SHA256: Literal[
    "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
] = "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
EXPECTED_REVIEWER_SAFE_STATE_INVENTORY_SHA256: Literal[
    "fa29e5ab26908874524a331d44189e3db1bf142a7b441cea8271946a0a9e0ab3"
] = "fa29e5ab26908874524a331d44189e3db1bf142a7b441cea8271946a0a9e0ab3"
EXPECTED_PROTECTED_SCHEDULE_SHA256: Literal[
    "0a526cc4ad983e0e0fe040c13703c6d09e86ebcdb9aaa839e2e14f9c6a201cf3"
] = "0a526cc4ad983e0e0fe040c13703c6d09e86ebcdb9aaa839e2e14f9c6a201cf3"
EXPECTED_PROTECTED_PRIMARY_EXPORT_SHA256: Literal[
    "226eb0ceb89e6f173b2a500e1ce009b09abeb373d4086bd08cbe3c94277441fd"
] = "226eb0ceb89e6f173b2a500e1ce009b09abeb373d4086bd08cbe3c94277441fd"
EXPECTED_PROTECTED_SECONDARY_EXPORT_SHA256: Literal[
    "96f636c2dc1e47746e2360d18d3f28fb80cc5832792c0214154fa7e10f188aa1"
] = "96f636c2dc1e47746e2360d18d3f28fb80cc5832792c0214154fa7e10f188aa1"
EXPECTED_REGISTRY_SHA256: Literal[
    "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
] = "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
EXPECTED_HUMAN_PROJECTION_SHA256: Literal[
    "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
] = "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
EXPECTED_MODEL_PROJECTION_SHA256: Literal[
    "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
] = "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
EXPECTED_CONSTITUTION_SHA256: Literal[
    "aef0d6a3edbaa63c1e5b46c278b019aeed613d8b8f941f98ee45eaee0a2d6ad2"
] = "aef0d6a3edbaa63c1e5b46c278b019aeed613d8b8f941f98ee45eaee0a2d6ad2"

CASE_ID_PATTERN = re.compile(r"^j7l-dev-[0-9]{3}$")


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReferenceAuthorityClass(StrEnum):
    MODEL_DERIVED_REFERENCE = "MODEL_DERIVED_REFERENCE"


class ReferenceAttemptStatus(StrEnum):
    ABSTAINED = "ABSTAINED"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    UNRESOLVED_EVIDENCE = "UNRESOLVED_EVIDENCE"


class ReferenceApiProtocol(StrEnum):
    OPENAI_COMPATIBLE_CHAT_COMPLETIONS = "OPENAI_COMPATIBLE_CHAT_COMPLETIONS"
    ANTHROPIC_MESSAGES = "ANTHROPIC_MESSAGES"
    OTHER_TYPED_HTTP = "OTHER_TYPED_HTTP"


class ReferenceStructuredOutputMode(StrEnum):
    FORCED_NAMED_TOOL = "FORCED_NAMED_TOOL"


class J7LReferenceSubjectV1(FrozenModel):
    subject_id: Literal["auragateway-j7l-reference-subject-v1"] = (
        "auragateway-j7l-reference-subject-v1"
    )
    case_count: Literal[48] = 48
    authoring_case_set_sha256: Literal[
        "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
    ] = EXPECTED_AUTHORING_CASE_SET_SHA256
    reviewer_safe_state_inventory_sha256: Literal[
        "fa29e5ab26908874524a331d44189e3db1bf142a7b441cea8271946a0a9e0ab3"
    ] = EXPECTED_REVIEWER_SAFE_STATE_INVENTORY_SHA256
    protected_schedule_sha256: Literal[
        "0a526cc4ad983e0e0fe040c13703c6d09e86ebcdb9aaa839e2e14f9c6a201cf3"
    ] = EXPECTED_PROTECTED_SCHEDULE_SHA256
    protected_primary_export_sha256: Literal[
        "226eb0ceb89e6f173b2a500e1ce009b09abeb373d4086bd08cbe3c94277441fd"
    ] = EXPECTED_PROTECTED_PRIMARY_EXPORT_SHA256
    protected_secondary_export_sha256: Literal[
        "96f636c2dc1e47746e2360d18d3f28fb80cc5832792c0214154fa7e10f188aa1"
    ] = EXPECTED_PROTECTED_SECONDARY_EXPORT_SHA256
    semantic_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = EXPECTED_REGISTRY_SHA256
    human_projection_sha256: Literal[
        "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    ] = EXPECTED_HUMAN_PROJECTION_SHA256
    model_projection_sha256: Literal[
        "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
    ] = EXPECTED_MODEL_PROJECTION_SHA256


class J7LReferenceExecutionPolicyV1(FrozenModel):
    planned_primary_reference_request_count: Literal[48] = 48
    serial_execution: Literal[True] = True
    max_in_flight_requests: Literal[1] = 1
    automatic_retry_permitted: Literal[False] = False
    existing_valid_response_skips_replay: Literal[True] = True
    uncertain_outcome_requires_reconciliation: Literal[True] = True
    replacement_case_after_reference_reveal_permitted: Literal[False] = False
    complete_valid_reference_set_required_before_jev: Literal[True] = True
    hidden_chain_of_thought_requested: Literal[False] = False
    complete_visible_evidence_required: Literal[True] = True
    silent_truncation_permitted: Literal[False] = False
    silent_summary_substitution_permitted: Literal[False] = False
    external_spend_ceiling: Literal[0] = 0
    network_access_requires_separate_authority: Literal[True] = True


class J7LReferenceAuthorityPolicyV1(FrozenModel):
    authority_class: Literal["MODEL_DERIVED_REFERENCE"] = (
        ReferenceAuthorityClass.MODEL_DERIVED_REFERENCE.value
    )
    primary_reference_count: Literal[48] = 48
    protected_audit_stratum_count: Literal[24] = 24
    protected_secondary_schedule_required: Literal[True] = True
    additional_ordinary_and_clear_failure_spot_checks_required: Literal[True] = True
    audit_schedule_must_freeze_before_reference_execution: Literal[True] = True
    audit_may_rewrite_reference: Literal[False] = False
    hybrid_adjudication_permitted: Literal[False] = False
    material_audit_disagreement_invalidates_reference_set: Literal[True] = True
    material_disagreement_verdict_mismatch: Literal[True] = True
    material_disagreement_score_delta: Literal[2] = 2
    material_disagreement_failure_label_set_mismatch: Literal[True] = True
    reference_coverage_gates_preserved_without_relaxation: Literal[True] = True
    jev_may_see_reference: Literal[False] = False
    model_reference_limit_must_be_disclosed: Literal[True] = True


class ReferenceDecodingSettingsV1(FrozenModel):
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    seed: int | None = None
    structured_output_mode: Literal["FORCED_NAMED_TOOL"] = (
        ReferenceStructuredOutputMode.FORCED_NAMED_TOOL.value
    )
    reasoning_mode: str | None = Field(default=None, min_length=1, max_length=120)
    provider_specific_settings: dict[str, JsonValue] = Field(default_factory=dict)


class J7LReferenceStructuredOutputContractV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    mode: Literal["FORCED_NAMED_TOOL"] = ReferenceStructuredOutputMode.FORCED_NAMED_TOOL.value
    tool_name: Literal["submit_reference_judgment"] = "submit_reference_judgment"
    tool_contract_id: str = Field(min_length=20, max_length=160)
    tool_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tool_choice_required: Literal[True] = True
    response_format_present: Literal[False] = False
    additional_model_tools_permitted: Literal[False] = False
    tool_arguments_validation_contract: Literal["J7LReferenceToolArgumentsV1"] = (
        "J7LReferenceToolArgumentsV1"
    )
    hidden_reasoning_persisted: Literal[False] = False


class J7LReferenceJudgeBindingV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    binding_id: str = Field(min_length=20, max_length=160)
    authority_class: Literal["MODEL_DERIVED_REFERENCE"] = (
        ReferenceAuthorityClass.MODEL_DERIVED_REFERENCE.value
    )
    provider_id: str = Field(min_length=1, max_length=120)
    api_protocol: ReferenceApiProtocol
    endpoint_contract_id: str = Field(min_length=1, max_length=160)
    endpoint_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_id: str = Field(min_length=1, max_length=200)
    model_version_or_revision: str = Field(min_length=1, max_length=200)
    prompt_template_id: str = Field(min_length=1, max_length=160)
    prompt_template_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_projection_sha256: Literal[
        "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
    ] = EXPECTED_MODEL_PROJECTION_SHA256
    decoding_settings: ReferenceDecodingSettingsV1
    structured_output: J7LReferenceStructuredOutputContractV1
    max_context_tokens: int = Field(ge=1)
    max_input_tokens_per_request: int = Field(ge=1)
    max_output_tokens_per_request: int = Field(ge=1)
    max_total_reference_input_tokens: int = Field(ge=1)
    max_total_reference_output_tokens: int = Field(ge=1)
    provider_access_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    zero_spend_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    network_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    independent_from_jev: Literal[True] = True
    binding_frozen_before_reference_execution: Literal[True] = True

    @model_validator(mode="after")
    def validate_budgets(self) -> Self:
        if self.max_input_tokens_per_request + self.max_output_tokens_per_request > (
            self.max_context_tokens
        ):
            raise ValueError("reference request token budget exceeds the bound context window")
        if self.max_total_reference_input_tokens < self.max_input_tokens_per_request:
            raise ValueError("total reference input budget is smaller than one request budget")
        if self.max_total_reference_output_tokens < self.max_output_tokens_per_request:
            raise ValueError("total reference output budget is smaller than one request budget")
        return self


def _validate_reference_content(
    *,
    criterion_scores: dict[RubricCriterion, int],
    failure_labels: tuple[EpisodeFailureLabel, ...],
    evidence_references: tuple[str, ...],
    verdict: ReviewVerdict,
) -> None:
    if set(criterion_scores) != set(RubricCriterion):
        raise ValueError("reference judgment must score every rubric criterion")
    if any(score < 1 or score > 4 for score in criterion_scores.values()):
        raise ValueError("reference criterion scores must be in [1,4]")
    if len(failure_labels) != len(set(failure_labels)):
        raise ValueError("reference failure labels must be unique")
    if len(evidence_references) != len(set(evidence_references)):
        raise ValueError("reference evidence references must be unique")

    values = tuple(criterion_scores[criterion] for criterion in RubricCriterion)
    passed = sum(values) >= 21 and min(values) >= 2 and not failure_labels
    implied = ReviewVerdict.PASS if passed else ReviewVerdict.FAIL
    if verdict is not implied:
        raise ValueError("reference verdict does not match the frozen derivation rule")


class J7LReferenceToolArgumentsV1(FrozenModel):
    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=20, max_length=3000)
    verdict: ReviewVerdict
    uncertainty_statement: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_arguments(self) -> Self:
        _validate_reference_content(
            criterion_scores=self.criterion_scores,
            failure_labels=self.failure_labels,
            evidence_references=self.evidence_references,
            verdict=self.verdict,
        )
        return self


class J7LReferenceAuditScheduleV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    schedule_id: str = Field(min_length=20, max_length=160)
    audit_actor_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolution_owner_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_secondary_case_ids: tuple[str, ...] = Field(min_length=24, max_length=24)
    additional_spot_check_case_ids: tuple[str, ...] = Field(min_length=2, max_length=24)
    schedule_frozen_before_reference_execution: Literal[True] = True
    audit_may_rewrite_reference: Literal[False] = False

    @field_validator("protected_secondary_case_ids", "additional_spot_check_case_ids")
    @classmethod
    def validate_case_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(CASE_ID_PATTERN.fullmatch(value) is None for value in values):
            raise ValueError("reference audit schedule contains an invalid case ID")
        if len(values) != len(set(values)):
            raise ValueError("reference audit schedule case IDs must be unique")
        return values

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        if set(self.protected_secondary_case_ids) & set(self.additional_spot_check_case_ids):
            raise ValueError("protected and additional audit samples must be disjoint")
        return self


class J7LReferenceJudgmentV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["VALID_JUDGMENT"] = "VALID_JUDGMENT"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    request_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    judge_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...] = ()
    evidence_references: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=20, max_length=3000)
    verdict: ReviewVerdict
    uncertainty_statement: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_judgment(self) -> Self:
        _validate_reference_content(
            criterion_scores=self.criterion_scores,
            failure_labels=self.failure_labels,
            evidence_references=self.evidence_references,
            verdict=self.verdict,
        )
        return self


class J7LReferenceAttemptFailureV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    attempt_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    judge_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: ReferenceAttemptStatus
    safe_reason: str = Field(min_length=1, max_length=1000)


class J7LReferenceSetV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    reference_set_id: Literal["auragateway-j7l-model-reference-set-v1"] = (
        "auragateway-j7l-model-reference-set-v1"
    )
    authority_class: Literal["MODEL_DERIVED_REFERENCE"] = (
        ReferenceAuthorityClass.MODEL_DERIVED_REFERENCE.value
    )
    cases: tuple[J7LReferenceJudgmentV1, ...] = Field(min_length=48, max_length=48)
    audit_complete: Literal[True] = True
    material_audit_disagreement_count: Literal[0] = 0
    coverage_pass: Literal[True] = True
    frozen_before_jev_reveal: Literal[True] = True
    jev_requests_performed_before_reference_freeze: Literal[0] = 0

    @model_validator(mode="after")
    def validate_reference_set(self) -> Self:
        case_ids = tuple(case.case_id for case in self.cases)
        expected = tuple(f"j7l-dev-{index:03d}" for index in range(1, 49))
        if case_ids != expected:
            raise ValueError("reference set must contain j7l-dev-001..048 in frozen order")
        return self


class J7LReferenceCoverageReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_MODEL_REFERENCE_COVERAGE_PASS"] = "J7L_MODEL_REFERENCE_COVERAGE_PASS"
    case_count: Literal[48] = 48
    pass_count: int = Field(ge=16, le=48)
    fail_count: int = Field(ge=16, le=48)
    minimum_positive_support_observed: int = Field(ge=2)
    minimum_near_miss_negative_support_observed: int = Field(ge=2)
    minimum_distinct_scores_observed: int = Field(ge=3)
    minimum_low_score_count_observed: int = Field(ge=4)
    minimum_high_score_count_observed: int = Field(ge=4)
    terminal_material_evidence_case_count: int = Field(ge=8, le=12)
    authority_class: Literal["MODEL_DERIVED_REFERENCE"] = (
        ReferenceAuthorityClass.MODEL_DERIVED_REFERENCE.value
    )
    next_gate: Literal["FREEZE_J7L_PAIRED_JEV_REQUEST_INVENTORY_V2"] = (
        "FREEZE_J7L_PAIRED_JEV_REQUEST_INVENTORY_V2"
    )


class J7LJevExperimentPolicyV2(FrozenModel):
    case_count: Literal[48] = 48
    planned_provider_request_count: Literal[96] = 96
    model_pin: Literal["jev-1.13.0"] = "jev-1.13.0"
    baseline_condition: Literal["BASELINE_V1_SEMANTICS"] = (
        J7LEvaluatorCondition.BASELINE_V1_SEMANTICS.value
    )
    intervention_condition: Literal["INTERVENTION_V2_SEMANTICS"] = (
        J7LEvaluatorCondition.INTERVENTION_V2_SEMANTICS.value
    )
    threshold_grid: tuple[float, ...] = THRESHOLD_GRID
    serial_execution: Literal[True] = True
    max_in_flight_requests: Literal[1] = 1
    automatic_retry_permitted: Literal[False] = False
    balanced_order_by_case_index: Literal[True] = True
    reference_visible_to_jev: Literal[False] = False
    replacement_case_after_model_reveal_permitted: Literal[False] = False
    selected_threshold_is_development_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        if self.planned_provider_request_count != self.case_count * 2:
            raise ValueError("Jev request count must remain two requests per frozen case")
        if self.threshold_grid != THRESHOLD_GRID:
            raise ValueError("Jev threshold grid drifted")
        return self


class J7LReferenceSuccessorPrerequisiteReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["J7L_REFERENCE_SUCCESSOR_PREREQUISITES_PASS"] = (
        "J7L_REFERENCE_SUCCESSOR_PREREQUISITES_PASS"
    )
    constitution_sha256: Literal[
        "aef0d6a3edbaa63c1e5b46c278b019aeed613d8b8f941f98ee45eaee0a2d6ad2"
    ] = EXPECTED_CONSTITUTION_SHA256
    authoring_case_set_sha256: Literal[
        "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
    ] = EXPECTED_AUTHORING_CASE_SET_SHA256
    reviewer_safe_state_inventory_sha256: Literal[
        "fa29e5ab26908874524a331d44189e3db1bf142a7b441cea8271946a0a9e0ab3"
    ] = EXPECTED_REVIEWER_SAFE_STATE_INVENTORY_SHA256
    protected_schedule_sha256: Literal[
        "0a526cc4ad983e0e0fe040c13703c6d09e86ebcdb9aaa839e2e14f9c6a201cf3"
    ] = EXPECTED_PROTECTED_SCHEDULE_SHA256
    human_projection_sha256: Literal[
        "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    ] = EXPECTED_HUMAN_PROJECTION_SHA256
    model_projection_sha256: Literal[
        "b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e"
    ] = EXPECTED_MODEL_PROJECTION_SHA256
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    network_access_performed: Literal[False] = False
    next_gate: Literal["FREEZE_J7L_REFERENCE_JUDGE_BINDING_V1"] = (
        "FREEZE_J7L_REFERENCE_JUDGE_BINDING_V1"
    )


class J7LDevelopmentConstitutionV2(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    constitution_id: Literal["auragateway-j7l-model-derived-reference-successor-v1"] = (
        "auragateway-j7l-model-derived-reference-successor-v1"
    )
    subject: J7LReferenceSubjectV1 = Field(default_factory=J7LReferenceSubjectV1)
    reference_authority: J7LReferenceAuthorityPolicyV1 = Field(
        default_factory=J7LReferenceAuthorityPolicyV1
    )
    reference_execution: J7LReferenceExecutionPolicyV1 = Field(
        default_factory=J7LReferenceExecutionPolicyV1
    )
    jev_experiment: J7LJevExperimentPolicyV2 = Field(default_factory=J7LJevExperimentPolicyV2)
    advancement_policy: J7LAdvancementPolicyV1 = Field(default_factory=J7LAdvancementPolicyV1)
    metric_gate_uses_unrounded_values: Literal[True] = True
    report_rounding_decimal_places: Literal[6] = 6
    report_rounding_mode: Literal["ROUND_HALF_UP"] = "ROUND_HALF_UP"
    provider_binding_required_before_execution: Literal[True] = True
    provider_binding_present_in_constitution: Literal[False] = False
    final_abc_cache_effect_claim_permitted: Literal[False] = False
    next_gate: Literal["FREEZE_J7L_REFERENCE_JUDGE_BINDING_V1"] = (
        "FREEZE_J7L_REFERENCE_JUDGE_BINDING_V1"
    )
