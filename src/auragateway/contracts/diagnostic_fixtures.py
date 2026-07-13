"""Typed contracts for privacy-safe diagnostic prompt fixture materialization."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")
_VOCABULARY_PATTERN = re.compile(r"^[a-z]{3,8}$")


class DiagnosticFixtureRecipe(BaseModel):
    """Public deterministic recipe that contains no complete provider prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    recipe_id: Literal["batch-06-diagnostic-prompt-recipe-v1"]
    materializer_version: Literal["diagnostic-prompt-materializer-v1"]
    design_id: Literal["batch-06-request-rejection-diagnostic-design-v1"]
    cohort_ids: tuple[
        Literal["cohort-alpha"],
        Literal["cohort-beta"],
        Literal["cohort-gamma"],
        Literal["cohort-delta"],
        Literal["cohort-epsilon"],
        Literal["cohort-zeta"],
    ]
    system_prompt_byte_count: Literal[6000] = 6000
    user_prompt_byte_counts_by_turn: tuple[Literal[1365], Literal[1737], Literal[2109]]
    total_prompt_byte_counts_by_turn: tuple[Literal[7365], Literal[7737], Literal[8109]]
    input_token_estimates_by_turn: tuple[Literal[1732], Literal[1809], Literal[1884]]
    input_token_estimate_profile: Literal["batch-06-observed-exact-byte-profile-v1"]
    provider_model_alias: Literal["groq-gpt-oss-20b"] = "groq-gpt-oss-20b"
    maximum_completion_tokens: Literal[256] = 256
    temperature_milli: Literal[0] = 0
    streaming: Literal[False] = False
    store_enabled: Literal[False] = False
    reasoning_effort: Literal["low"] = "low"
    filler_vocabulary: tuple[str, ...] = Field(min_length=24, max_length=64)
    synthetic_content_only: Literal[True] = True
    pii_or_secret_content_permitted: Literal[False] = False
    raw_prompt_commit_permitted: Literal[False] = False

    @field_validator("filler_vocabulary")
    @classmethod
    def validate_vocabulary(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("fixture filler vocabulary must be unique")
        if any(_VOCABULARY_PATTERN.fullmatch(item) is None for item in value):
            raise ValueError("fixture filler vocabulary must use lowercase synthetic words")
        return value

    @model_validator(mode="after")
    def validate_prompt_byte_arithmetic(self) -> DiagnosticFixtureRecipe:
        observed_totals = tuple(
            self.system_prompt_byte_count + item for item in self.user_prompt_byte_counts_by_turn
        )
        if observed_totals != self.total_prompt_byte_counts_by_turn:
            raise ValueError("fixture total bytes must equal system plus user bytes")
        if len(self.cohort_ids) != len(set(self.cohort_ids)):
            raise ValueError("fixture recipe cohort IDs must be unique")
        return self


class DiagnosticCohortFixtureRecord(BaseModel):
    """Public content-free identity for one materialized prompt cohort."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cohort_id: str
    system_prompt_sha256: str
    system_prompt_byte_count: Literal[6000]
    user_prompt_sha256_by_turn: tuple[str, str, str]
    user_prompt_byte_counts_by_turn: tuple[Literal[1365], Literal[1737], Literal[2109]]
    total_prompt_byte_counts_by_turn: tuple[Literal[7365], Literal[7737], Literal[8109]]
    input_token_estimates_by_turn: tuple[Literal[1732], Literal[1809], Literal[1884]]
    condition_b_request_sha256_by_turn: tuple[str, str, str]
    condition_c_request_sha256_by_turn: tuple[str, str, str]
    provider_visible_b_c_equivalence_verified: Literal[True] = True
    synthetic_content_only: Literal[True] = True
    pii_or_secret_content_present: Literal[False] = False

    @field_validator("cohort_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("fixture cohort ID must use a stable lowercase slug")
        return value

    @field_validator("system_prompt_sha256")
    @classmethod
    def validate_system_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("fixture identities must be lowercase SHA-256")
        return value

    @field_validator(
        "user_prompt_sha256_by_turn",
        "condition_b_request_sha256_by_turn",
        "condition_c_request_sha256_by_turn",
    )
    @classmethod
    def validate_turn_hashes(
        cls,
        value: tuple[str, str, str],
    ) -> tuple[str, str, str]:
        if any(_SHA256_PATTERN.fullmatch(item) is None for item in value):
            raise ValueError("fixture identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_equivalence(self) -> DiagnosticCohortFixtureRecord:
        if self.condition_b_request_sha256_by_turn != self.condition_c_request_sha256_by_turn:
            raise ValueError("condition B and condition C provider request hashes must match")
        observed_totals = tuple(
            self.system_prompt_byte_count + item for item in self.user_prompt_byte_counts_by_turn
        )
        if observed_totals != self.total_prompt_byte_counts_by_turn:
            raise ValueError("fixture total bytes must equal system plus user bytes")
        if len(set(self.user_prompt_sha256_by_turn)) != 3:
            raise ValueError("fixture user prompt hashes must be unique by turn")
        if len(set(self.condition_b_request_sha256_by_turn)) != 3:
            raise ValueError("fixture request hashes must be unique by turn")
        return self


class DiagnosticFixtureManifest(BaseModel):
    """Committed public manifest for materialized privacy-safe prompt fixtures."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    fixture_id: Literal["batch-06-diagnostic-prompt-fixtures-v1"]
    status: Literal["fixture_ready"] = "fixture_ready"
    design_id: Literal["batch-06-request-rejection-diagnostic-design-v1"]
    design_plan_path: Literal["data/evals/benchmark/diagnostic-design-v1/experiment_plan.json"]
    design_plan_sha256: str
    design_manifest_path: Literal["data/evals/benchmark/diagnostic-design-v1/manifest.json"]
    design_manifest_sha256: str
    recipe_path: Literal["data/evals/benchmark/diagnostic-fixtures-v1/fixture_recipe.json"]
    recipe_sha256: str
    materializer_version: Literal["diagnostic-prompt-materializer-v1"]
    protected_prompt_bundle_path: Literal[
        ".local/benchmark/diagnostic-fixtures-v1/prompt_cohorts.json"
    ]
    protected_prompt_bundle_sha256: str
    cohorts: tuple[DiagnosticCohortFixtureRecord, ...] = Field(
        min_length=6,
        max_length=6,
    )
    unique_stable_prefixes_verified: Literal[True] = True
    exact_byte_counts_verified: Literal[True] = True
    bounded_token_estimates_verified: Literal[True] = True
    provider_visible_b_c_equivalence_verified: Literal[True] = True
    synthetic_content_only: Literal[True] = True
    pii_or_secret_content_present: Literal[False] = False
    raw_prompt_committed: Literal[False] = False
    provider_calls_permitted: Literal[False] = False
    execution_authorization_created: Literal[False] = False
    next_gate: Literal["execution_authorization_review"] = "execution_authorization_review"

    @field_validator(
        "design_plan_sha256",
        "design_manifest_sha256",
        "recipe_sha256",
        "protected_prompt_bundle_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("fixture manifest identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_cohort_set(self) -> DiagnosticFixtureManifest:
        expected_ids = {
            "cohort-alpha",
            "cohort-beta",
            "cohort-gamma",
            "cohort-delta",
            "cohort-epsilon",
            "cohort-zeta",
        }
        observed_ids = [item.cohort_id for item in self.cohorts]
        if set(observed_ids) != expected_ids or len(observed_ids) != len(set(observed_ids)):
            raise ValueError("fixture manifest requires the six designed cohorts exactly")
        prefix_hashes = [item.system_prompt_sha256 for item in self.cohorts]
        if len(prefix_hashes) != len(set(prefix_hashes)):
            raise ValueError("fixture stable-prefix hashes must be unique")
        request_hashes = [
            digest
            for cohort in self.cohorts
            for digest in cohort.condition_b_request_sha256_by_turn
        ]
        if len(request_hashes) != len(set(request_hashes)):
            raise ValueError("fixture provider request hashes must be globally unique")
        return self


class ProtectedDiagnosticPromptCohort(BaseModel):
    """Raw synthetic prompt fixture retained only below ignored local storage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cohort_id: str
    system_prompt: str = Field(min_length=1)
    user_prompts_by_turn: tuple[str, str, str]

    @field_validator("cohort_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("protected cohort ID must use a stable lowercase slug")
        return value

    @field_validator("user_prompts_by_turn")
    @classmethod
    def validate_user_prompts(
        cls,
        value: tuple[str, str, str],
    ) -> tuple[str, str, str]:
        if any(not item for item in value):
            raise ValueError("protected user prompts must not be blank")
        return value


class ProtectedDiagnosticPromptBundle(BaseModel):
    """Raw synthetic prompt bundle that must never be committed beneath data/."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    fixture_id: Literal["batch-06-diagnostic-prompt-fixtures-v1"]
    design_id: Literal["batch-06-request-rejection-diagnostic-design-v1"]
    materializer_version: Literal["diagnostic-prompt-materializer-v1"]
    cohorts: tuple[ProtectedDiagnosticPromptCohort, ...] = Field(
        min_length=6,
        max_length=6,
    )

    @model_validator(mode="after")
    def validate_cohorts(self) -> ProtectedDiagnosticPromptBundle:
        cohort_ids = [item.cohort_id for item in self.cohorts]
        if len(cohort_ids) != len(set(cohort_ids)):
            raise ValueError("protected prompt bundle cohort IDs must be unique")
        return self


class DiagnosticFixtureValidationSummary(BaseModel):
    """Metadata-only result from materialization or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["materialize", "verify"]
    fixture_id: str
    status: Literal["fixture_ready"] = "fixture_ready"
    cohort_count: Literal[6] = 6
    turn_count_per_cohort: Literal[3] = 3
    protected_prompt_bundle_sha256: str
    unique_stable_prefixes_verified: Literal[True] = True
    exact_byte_counts_verified: Literal[True] = True
    bounded_token_estimates_verified: Literal[True] = True
    provider_visible_b_c_equivalence_verified: Literal[True] = True
    provider_calls_permitted: Literal[False] = False
    authorization_created: Literal[False] = False
    execution_permitted: Literal[False] = False
    next_gate: Literal["execution_authorization_review"] = "execution_authorization_review"

    @field_validator("protected_prompt_bundle_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("fixture summary bundle identity must be lowercase SHA-256")
        return value
