"""Typed contracts for J7K shared quality-semantic projection parity."""

from __future__ import annotations

from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.blinded_quality import RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel

EXPECTED_REGISTRY_ID: Final = "auragateway-quality-semantic-registry-v2"
EXPECTED_REGISTRY_SCHEMA_VERSION: Final = "2.0.0"
EXPECTED_REGISTRY_PATH: Final = "data/evals/quality/semantic-registry-v2/registry.json"
EXPECTED_REGISTRY_SHA256: Final = (
    "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
)
EXPECTED_REGISTRY_ARTIFACT_SHA256: Final = (
    "0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HumanCriterionSemanticProjectionV1(FrozenModel):
    criterion: RubricCriterion
    guidance: str = Field(min_length=20, max_length=2200)


class HumanFailureLabelSemanticProjectionV1(FrozenModel):
    label: EpisodeFailureLabel
    guidance: str = Field(min_length=20, max_length=2200)


class HumanSemanticProjectionV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    projection_id: Literal["auragateway-quality-human-semantic-projection-v1"] = (
        "auragateway-quality-human-semantic-projection-v1"
    )
    consumer: Literal["human"] = "human"
    source_registry_id: Literal["auragateway-quality-semantic-registry-v2"] = (
        "auragateway-quality-semantic-registry-v2"
    )
    source_registry_schema_version: Literal["2.0.0"] = "2.0.0"
    source_registry_path: Literal[
        "data/evals/quality/semantic-registry-v2/registry.json"
    ] = "data/evals/quality/semantic-registry-v2/registry.json"
    source_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = EXPECTED_REGISTRY_SHA256
    source_registry_artifact_sha256: Literal[
        "0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c"
    ] = EXPECTED_REGISTRY_ARTIFACT_SHA256
    criteria: tuple[HumanCriterionSemanticProjectionV1, ...] = Field(
        min_length=7,
        max_length=7,
    )
    failure_labels: tuple[HumanFailureLabelSemanticProjectionV1, ...] = Field(
        min_length=22,
        max_length=22,
    )
    private_semantic_augmentation_permitted: Literal[False] = False
    semantic_elision_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        criteria = tuple(item.criterion for item in self.criteria)
        if len(criteria) != len(set(criteria)) or set(criteria) != set(RubricCriterion):
            raise ValueError("human projection must contain every rubric criterion exactly once")

        labels = tuple(item.label for item in self.failure_labels)
        if len(labels) != len(set(labels)) or set(labels) != set(EpisodeFailureLabel):
            raise ValueError("human projection must contain every failure label exactly once")

        return self


class ModelCriterionSemanticQuestionV1(FrozenModel):
    type: Literal["choice"] = "choice"
    question_name: str = Field(pattern=r"^criterion__[a-z0-9_]+$")
    criterion: RubricCriterion
    instructions: str = Field(min_length=20, max_length=2000)
    criteria: dict[str, str]

    @model_validator(mode="after")
    def validate_question(self) -> Self:
        expected_name = f"criterion__{self.criterion.value}"
        if self.question_name != expected_name:
            raise ValueError("criterion question name does not match criterion")

        if set(self.criteria) != {"1", "2", "3", "4"}:
            raise ValueError("criterion question score inventory must be exactly 1,2,3,4")

        if any(not value.strip() for value in self.criteria.values()):
            raise ValueError("criterion question anchors must not be blank")

        return self


class ModelFailureLabelSemanticQuestionV1(FrozenModel):
    type: Literal["noul"] = "noul"
    question_name: str = Field(pattern=r"^failure__[A-Z0-9_]+$")
    label: EpisodeFailureLabel
    instructions: str = Field(min_length=20, max_length=2000)

    @model_validator(mode="after")
    def validate_question(self) -> Self:
        if self.question_name != f"failure__{self.label.value}":
            raise ValueError("failure-label question name does not match label")
        return self


class ModelSemanticProjectionV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    projection_id: Literal["auragateway-quality-model-semantic-projection-v1"] = (
        "auragateway-quality-model-semantic-projection-v1"
    )
    consumer: Literal["model"] = "model"
    source_registry_id: Literal["auragateway-quality-semantic-registry-v2"] = (
        "auragateway-quality-semantic-registry-v2"
    )
    source_registry_schema_version: Literal["2.0.0"] = "2.0.0"
    source_registry_path: Literal[
        "data/evals/quality/semantic-registry-v2/registry.json"
    ] = "data/evals/quality/semantic-registry-v2/registry.json"
    source_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = EXPECTED_REGISTRY_SHA256
    source_registry_artifact_sha256: Literal[
        "0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c"
    ] = EXPECTED_REGISTRY_ARTIFACT_SHA256
    criterion_questions: tuple[ModelCriterionSemanticQuestionV1, ...] = Field(
        min_length=7,
        max_length=7,
    )
    failure_questions: tuple[ModelFailureLabelSemanticQuestionV1, ...] = Field(
        min_length=22,
        max_length=22,
    )
    private_semantic_augmentation_permitted: Literal[False] = False
    semantic_elision_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        criteria = tuple(item.criterion for item in self.criterion_questions)
        if len(criteria) != len(set(criteria)) or set(criteria) != set(RubricCriterion):
            raise ValueError("model projection must contain every rubric criterion exactly once")

        labels = tuple(item.label for item in self.failure_questions)
        if len(labels) != len(set(labels)) or set(labels) != set(EpisodeFailureLabel):
            raise ValueError("model projection must contain every failure label exactly once")

        criterion_question_names = tuple(
            item.question_name for item in self.criterion_questions
        )
        failure_question_names = tuple(
            item.question_name for item in self.failure_questions
        )
        question_names = criterion_question_names + failure_question_names
        if len(question_names) != len(set(question_names)):
            raise ValueError("model projection question names must be unique")

        return self


class SemanticProjectionParityReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    receipt_id: Literal["auragateway-quality-semantic-projection-parity-v1"] = (
        "auragateway-quality-semantic-projection-parity-v1"
    )
    status: Literal["J7K_SHARED_SEMANTIC_PROJECTION_V1_PASS"] = (
        "J7K_SHARED_SEMANTIC_PROJECTION_V1_PASS"
    )
    source_registry_id: Literal["auragateway-quality-semantic-registry-v2"] = (
        "auragateway-quality-semantic-registry-v2"
    )
    source_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = EXPECTED_REGISTRY_SHA256
    source_registry_artifact_sha256: Literal[
        "0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c"
    ] = EXPECTED_REGISTRY_ARTIFACT_SHA256
    human_projection_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_projection_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    human_reconstructed_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = EXPECTED_REGISTRY_SHA256
    model_reconstructed_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = EXPECTED_REGISTRY_SHA256
    criterion_count: Literal[7] = 7
    failure_label_count: Literal[22] = 22
    semantic_source_count: Literal[50] = 50
    criterion_inventory_parity: Literal[True] = True
    failure_label_inventory_parity: Literal[True] = True
    canonical_semantic_parity: Literal[True] = True
    canonical_source_identity_parity: Literal[True] = True
    private_human_semantic_augmentation_permitted: Literal[False] = False
    private_model_semantic_augmentation_permitted: Literal[False] = False
    semantic_elision_permitted: Literal[False] = False
    network_access_performed: Literal[False] = False
    jev_request_performed: Literal[False] = False
    deployment_threshold_selected: Literal[False] = False
    deployment_threshold_validated: Literal[False] = False
    final_342_mutated: Literal[False] = False
    rubric_v1_mutated: Literal[False] = False
    next_gate: Literal["J7L_DEVELOPMENT_EVALUATION"] = "J7L_DEVELOPMENT_EVALUATION"

    @field_validator("human_projection_sha256", "model_projection_sha256")
    @classmethod
    def validate_projection_sha(cls, value: str) -> str:
        return value.lower()
