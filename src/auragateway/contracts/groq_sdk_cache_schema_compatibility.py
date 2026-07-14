"""Typed contracts for the non-live Groq SDK cache-schema compatibility review."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.cache_telemetry_capture import BillingCacheObservationState

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class GroqSdkCompatibilityStatus(StrEnum):
    """Terminal state for the bounded non-live review."""

    CLOSED_PROVIDER_OMISSION_SUPPORTED = "closed_provider_omission_supported"


class GroqSdkCompatibilityClassification(StrEnum):
    """Candidate cause classes evaluated by the review."""

    PROVIDER_OMISSION_SUPPORTED = "provider_omission_supported"
    SDK_SCHEMA_INCOMPATIBILITY_SUPPORTED = "sdk_schema_incompatibility_supported"
    ADAPTER_EXTRACTION_DEFECT_SUPPORTED = "adapter_extraction_defect_supported"


class GroqSdkCompatibilityEvidenceKind(StrEnum):
    """Evidence source classes allowed by the review."""

    IMMUTABLE_CALIBRATION = "immutable_calibration"
    REPOSITORY_SOURCE = "repository_source"
    INSTALLED_SDK_RUNTIME = "installed_sdk_runtime"
    OFFICIAL_PROVIDER_DOCUMENTATION = "official_provider_documentation"
    OFFICIAL_PACKAGE_REGISTRY = "official_package_registry"


class GroqSdkProbeCaseId(StrEnum):
    """Real SDK-object cases required for presence and value semantics."""

    DETAILS_ABSENT = "details_absent"
    DETAILS_EXPLICIT_NULL = "details_explicit_null"
    CACHED_TOKENS_ZERO = "cached_tokens_zero"
    CACHED_TOKENS_POSITIVE = "cached_tokens_positive"


class GroqSdkSourceBinding(BaseModel):
    """One local source frozen by exact working-tree byte identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=240)
    sha256: str
    evidence_kind: GroqSdkCompatibilityEvidenceKind

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("source bindings require repository-relative paths")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("source bindings require lowercase SHA-256")
        return value


class GroqSdkExternalSource(BaseModel):
    """One official external source represented by bounded assertions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    evidence_kind: GroqSdkCompatibilityEvidenceKind
    url: str = Field(min_length=8, max_length=500)
    retrieved_on: Literal["2026-07-14"] = "2026-07-14"
    assertions: tuple[str, ...] = Field(min_length=1, max_length=6)

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("external source IDs require stable lowercase slugs")
        return value

    @model_validator(mode="after")
    def validate_external_kind(self) -> GroqSdkExternalSource:
        allowed = {
            GroqSdkCompatibilityEvidenceKind.OFFICIAL_PROVIDER_DOCUMENTATION,
            GroqSdkCompatibilityEvidenceKind.OFFICIAL_PACKAGE_REGISTRY,
        }
        if self.evidence_kind not in allowed:
            raise ValueError("external sources require an official external evidence kind")
        return self


class GroqSdkCandidateAssessment(BaseModel):
    """One candidate cause with an evidence-backed support decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    classification: GroqSdkCompatibilityClassification
    supported: bool
    evidence: tuple[str, ...] = Field(min_length=1, max_length=8)


class GroqSdkProbeExpectation(BaseModel):
    """Expected real-SDK and adapter semantics for one synthetic response shape."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: GroqSdkProbeCaseId
    sdk_usage_field_present: Literal[True] = True
    sdk_prompt_tokens_details_field_present: bool
    sdk_cached_tokens_field_present: bool
    sdk_cached_tokens_value: int | None = Field(default=None, ge=0)
    adapter_prompt_tokens_details_present: bool
    adapter_billing_cached_tokens_field_present: bool
    adapter_billing_cached_input_tokens: int | None = Field(default=None, ge=0)
    adapter_billing_observation_state: BillingCacheObservationState
    sdk_model_dump_preserves_expected_shape: Literal[True] = True
    adapter_capture_matches_sdk_presence: Literal[True] = True

    @model_validator(mode="after")
    def validate_case_semantics(self) -> GroqSdkProbeExpectation:
        if self.sdk_cached_tokens_value is not None and not self.sdk_cached_tokens_field_present:
            raise ValueError("SDK cached-token values require field presence")
        if (
            self.adapter_billing_cached_input_tokens is not None
            and not self.adapter_billing_cached_tokens_field_present
        ):
            raise ValueError("adapter cache values require field presence")
        if self.adapter_billing_observation_state is BillingCacheObservationState.FIELD_ABSENT:
            if self.adapter_billing_cached_tokens_field_present:
                raise ValueError("field-absent state cannot report field presence")
        elif self.adapter_billing_observation_state is BillingCacheObservationState.FIELD_NULL:
            if (
                not self.adapter_billing_cached_tokens_field_present
                or self.adapter_billing_cached_input_tokens is not None
            ):
                raise ValueError("field-null state requires a present null field")
        elif self.adapter_billing_observation_state is BillingCacheObservationState.OBSERVED_ZERO:
            if self.adapter_billing_cached_input_tokens != 0:
                raise ValueError("observed-zero state requires a numeric zero")
        elif (
            self.adapter_billing_observation_state is BillingCacheObservationState.OBSERVED_POSITIVE
        ):
            if not isinstance(self.adapter_billing_cached_input_tokens, int):
                raise ValueError("observed-positive state requires an integer")
            if self.adapter_billing_cached_input_tokens <= 0:
                raise ValueError("observed-positive state requires a positive value")
        return self


class GroqSdkCacheSchemaCompatibilityReview(BaseModel):
    """Frozen conclusion from SDK schema, adapter parity, and calibration evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["groq-sdk-cache-schema-compatibility-v1"]
    status: Literal[GroqSdkCompatibilityStatus.CLOSED_PROVIDER_OMISSION_SUPPORTED] = (
        GroqSdkCompatibilityStatus.CLOSED_PROVIDER_OMISSION_SUPPORTED
    )
    source_commit: Literal["75b03a8"] = "75b03a8"
    provider: Literal["groq"] = "groq"
    model_alias: Literal["groq-gpt-oss-20b"] = "groq-gpt-oss-20b"
    exact_model_identifier: Literal["openai/gpt-oss-20b"] = "openai/gpt-oss-20b"
    adapter_version: Literal["groq-chat-completions-v1"] = "groq-chat-completions-v1"
    installed_sdk_version: Literal["1.5.0"] = "1.5.0"
    declared_sdk_requirement: Literal["groq>=1.5,<2"] = "groq>=1.5,<2"
    billing_cache_field_path: Literal["usage.prompt_tokens_details.cached_tokens"] = (
        "usage.prompt_tokens_details.cached_tokens"
    )
    hardware_cache_field_paths: tuple[
        Literal["x_groq.usage.dram_cached_tokens"],
        Literal["x_groq.usage.sram_cached_tokens"],
    ]
    calibration_status: Literal["closed_billing_field_unavailable"] = (
        "closed_billing_field_unavailable"
    )
    calibration_successful_call_count: Literal[3] = 3
    calibration_billing_numeric_sample_count: Literal[0] = 0
    source_bindings: tuple[GroqSdkSourceBinding, ...] = Field(min_length=5, max_length=5)
    external_sources: tuple[GroqSdkExternalSource, ...] = Field(min_length=2, max_length=2)
    probe_expectations: tuple[GroqSdkProbeExpectation, ...] = Field(
        min_length=4,
        max_length=4,
    )
    candidate_assessments: tuple[GroqSdkCandidateAssessment, ...] = Field(
        min_length=3,
        max_length=3,
    )
    primary_classification: Literal[
        GroqSdkCompatibilityClassification.PROVIDER_OMISSION_SUPPORTED
    ] = GroqSdkCompatibilityClassification.PROVIDER_OMISSION_SUPPORTED
    exact_provider_omission_cause_resolved: Literal[False] = False
    nested_cached_tokens_null_rejected_by_sdk: Literal[True] = True
    sdk_upgrade_required: Literal[False] = False
    adapter_change_required: Literal[False] = False
    credential_access_permitted: Literal[False] = False
    provider_call_authorized: Literal[False] = False
    calibration_rerun_authorized: Literal[False] = False
    benchmark_execution_authorized: Literal[False] = False
    new_live_authorization_review_permitted: Literal[True] = True
    next_gate: Literal["groq_cache_telemetry_reauthorization_review"] = (
        "groq_cache_telemetry_reauthorization_review"
    )

    @model_validator(mode="after")
    def validate_complete_review(self) -> GroqSdkCacheSchemaCompatibilityReview:
        expected_paths = {
            "pyproject.toml",
            "src/auragateway/providers/groq.py",
            "src/auragateway/contracts/cache_telemetry_capture.py",
            "data/evals/benchmark/cache-telemetry-calibration-v1/report.json",
            "data/evals/benchmark/cache-telemetry-calibration-closeout-v1/closeout.json",
        }
        observed_paths = [item.path for item in self.source_bindings]
        if set(observed_paths) != expected_paths or len(observed_paths) != len(set(observed_paths)):
            raise ValueError("review requires the five exact source bindings")

        expected_cases = set(GroqSdkProbeCaseId)
        observed_cases = [item.case_id for item in self.probe_expectations]
        if set(observed_cases) != expected_cases or len(observed_cases) != len(set(observed_cases)):
            raise ValueError("review requires all four real SDK probe cases")

        expected_classifications = set(GroqSdkCompatibilityClassification)
        observed_assessments = [item.classification for item in self.candidate_assessments]
        if set(observed_assessments) != expected_classifications or len(
            observed_assessments
        ) != len(set(observed_assessments)):
            raise ValueError("review requires all three candidate cause assessments")

        supported = [item.classification for item in self.candidate_assessments if item.supported]
        if supported != [GroqSdkCompatibilityClassification.PROVIDER_OMISSION_SUPPORTED]:
            raise ValueError("only provider omission may be supported by this evidence")
        return self

    def expectation_for(self, case_id: GroqSdkProbeCaseId) -> GroqSdkProbeExpectation:
        """Return the frozen expectation for one required probe case."""

        return next(item for item in self.probe_expectations if item.case_id is case_id)


class GroqSdkCacheSchemaCompatibilityManifest(BaseModel):
    """Hash manifest for the review, ADR, and human-readable report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["groq-sdk-cache-schema-compatibility-manifest-v1"]
    review_id: Literal["groq-sdk-cache-schema-compatibility-v1"]
    review_path: Literal["data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1/review.json"]
    review_sha256: str
    adr_path: Literal["docs/adr/groq-sdk-cache-schema-compatibility.md"]
    adr_sha256: str
    report_path: Literal["docs/benchmark/AuraGateway_Groq_SDK_Cache_Schema_Compatibility_Review.md"]
    report_sha256: str

    @field_validator("review_sha256", "adr_sha256", "report_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest hashes require lowercase SHA-256")
        return value


class GroqSdkCacheSchemaCompatibilitySummary(BaseModel):
    """Metadata-safe CLI output from non-live compatibility validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    review_id: str
    status: GroqSdkCompatibilityStatus
    installed_sdk_version: str
    primary_classification: GroqSdkCompatibilityClassification
    exact_provider_omission_cause_resolved: bool
    probe_case_count: int = Field(ge=0)
    synthetic_adapter_probe_count: int = Field(ge=0)
    sdk_upgrade_required: bool
    adapter_change_required: bool
    credential_accessed: Literal[False] = False
    provider_call_count: Literal[0] = 0
    provider_call_authorized: bool
    calibration_rerun_authorized: bool
    benchmark_execution_authorized: bool
    next_gate: str
