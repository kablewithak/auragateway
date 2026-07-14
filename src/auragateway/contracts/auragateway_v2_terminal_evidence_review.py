"""Typed terminal evidence review for AuraGateway v2 core scope."""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class TerminalEvidenceReviewStatus(StrEnum):
    """Terminal state of the core runtime evidence review."""

    CLOSED_CORE_RUNTIME_WITH_NEGATIVE_PROVIDER_TELEMETRY = (
        "closed_core_runtime_with_negative_provider_telemetry"
    )


class TerminalEvidenceGate4Status(StrEnum):
    """Final Gate 4 disposition for measured benchmark eligibility."""

    CLOSED_REQUIRED_PROVIDER_CACHE_EVIDENCE_UNAVAILABLE = (
        "closed_required_provider_cache_evidence_unavailable"
    )


class TerminalEvidenceClaimKind(StrEnum):
    """Claims explicitly permitted or blocked by the terminal review."""

    CORE_RUNTIME_AND_HARNESS_IMPLEMENTED = "core_runtime_and_harness_implemented"
    DETERMINISTIC_PREFIX_CONSTRUCTION = "deterministic_prefix_construction"
    CACHE_AFFINITY_POLICY_IMPLEMENTED = "cache_affinity_policy_implemented"
    TELEMETRY_UNKNOWN_PRESERVED = "telemetry_unknown_preserved"
    TERMINAL_EVIDENCE_INTEGRITY = "terminal_evidence_integrity"
    OBSERVED_PROVIDER_WIRE_OMISSION = "observed_provider_wire_omission"
    UNIVERSAL_PROVIDER_WIRE_OMISSION = "universal_provider_wire_omission"
    PROVIDER_CACHE_USAGE = "provider_cache_usage"
    PROVIDER_CACHE_MISS = "provider_cache_miss"
    CACHED_TOKENS_EQUAL_ZERO = "cached_tokens_equal_zero"
    PROVIDER_CACHE_SAVINGS = "provider_cache_savings"
    MEASURED_A_B_C_COMPARISON = "measured_a_b_c_comparison"
    UNIVERSAL_COST_OR_LATENCY_SAVINGS = "universal_cost_or_latency_savings"
    PRODUCTION_READINESS = "production_readiness"


class TerminalEvidenceClaimDecision(StrEnum):
    """Machine-readable claim decision."""

    PERMITTED = "permitted"
    BLOCKED = "blocked"


class TerminalEvidenceClaimReason(StrEnum):
    """Bounded reason taxonomy for terminal claim decisions."""

    CORE_RUNTIME_LOCALLY_VALIDATED = "CORE_RUNTIME_LOCALLY_VALIDATED"
    PREFIX_EVIDENCE_VALIDATED = "PREFIX_EVIDENCE_VALIDATED"
    ROUTE_POLICY_FIXED_EVIDENCE_VALIDATED = "ROUTE_POLICY_FIXED_EVIDENCE_VALIDATED"
    UNKNOWN_REMAINS_UNKNOWN = "UNKNOWN_REMAINS_UNKNOWN"
    TERMINAL_LINEAGE_HASH_BOUND = "TERMINAL_LINEAGE_HASH_BOUND"
    FIELD_ABSENT_ON_TWO_RAW_RESPONSES = "FIELD_ABSENT_ON_TWO_RAW_RESPONSES"
    OBSERVATION_SCOPE_LIMITED_TO_TWO_CALLS = "OBSERVATION_SCOPE_LIMITED_TO_TWO_CALLS"
    BILLING_CACHE_EVIDENCE_UNAVAILABLE = "BILLING_CACHE_EVIDENCE_UNAVAILABLE"
    FIELD_ABSENCE_IS_NOT_CACHE_MISS = "FIELD_ABSENCE_IS_NOT_CACHE_MISS"
    MISSING_FIELD_IS_NOT_ZERO = "MISSING_FIELD_IS_NOT_ZERO"
    NUMERIC_CACHE_EVIDENCE_UNAVAILABLE = "NUMERIC_CACHE_EVIDENCE_UNAVAILABLE"
    GATE_4_DID_NOT_PASS = "GATE_4_DID_NOT_PASS"
    LOCAL_RESULT_NOT_UNIVERSAL = "LOCAL_RESULT_NOT_UNIVERSAL"
    DEPLOYMENT_AND_OPERATIONS_NOT_PROVEN = "DEPLOYMENT_AND_OPERATIONS_NOT_PROVEN"


class TerminalEvidenceNextPhase(StrEnum):
    """Next project phase after core evidence closure."""

    HUGGING_FACE_PUBLICATION_LAYER_DESIGN = "hugging_face_publication_layer_design"


class TerminalEvidenceBinding(BaseModel):
    """One immutable public source-evidence dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=280)
    sha256: str
    purpose: str = Field(min_length=3, max_length=200)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("terminal evidence paths must be repository-relative")
        if not value.startswith("data/evals/benchmark/"):
            raise ValueError("terminal evidence must remain under benchmark evidence")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal evidence bindings require lowercase SHA-256")
        return value


class TerminalEvidenceClaimRecord(BaseModel):
    """One explicit claim boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_kind: TerminalEvidenceClaimKind
    decision: TerminalEvidenceClaimDecision
    reason: TerminalEvidenceClaimReason


class TerminalEvidenceGate4Resolution(BaseModel):
    """Final distinction between contract integrity and live evidence sufficiency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    telemetry_contract_integrity_passed: Literal[True] = True
    live_provider_numeric_evidence_required: Literal[True] = True
    live_provider_numeric_evidence_available: Literal[False] = False
    status: Literal[
        TerminalEvidenceGate4Status.CLOSED_REQUIRED_PROVIDER_CACHE_EVIDENCE_UNAVAILABLE
    ] = TerminalEvidenceGate4Status.CLOSED_REQUIRED_PROVIDER_CACHE_EVIDENCE_UNAVAILABLE
    gate_4_passed_for_measured_benchmark: Literal[False] = False
    negative_result_accepted: Literal[True] = True
    benchmark_execution_permitted: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False


class TerminalEvidenceAchievedState(BaseModel):
    """Final core-scope implementation and evidence state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    core_runtime_and_harness_implemented: Literal[True] = True
    local_validation_complete: Literal[True] = True
    synthetic_corpus_validation_complete: Literal[True] = True
    fixed_eval_validation_complete: Literal[True] = True
    controlled_provider_execution_complete: Literal[True] = True
    terminal_evidence_review_complete: Literal[True] = True
    measured_a_b_c_comparison_completed: Literal[False] = False
    provider_cache_usage_measured: Literal[False] = False
    provider_cache_savings_measured: Literal[False] = False
    deployed: Literal[False] = False
    customer_data_tested: Literal[False] = False
    production_ready: Literal[False] = False


class TerminalEvidencePublicationBoundary(BaseModel):
    """Seam between closed core runtime scope and future public presentation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hugging_face_publication_part_of_core_runtime: Literal[False] = False
    publication_layer_started: Literal[False] = False
    static_precomputed_artifacts_only: Literal[True] = True
    live_inference_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    protected_provider_payloads_permitted: Literal[False] = False
    next_phase: Literal[TerminalEvidenceNextPhase.HUGGING_FACE_PUBLICATION_LAYER_DESIGN] = (
        TerminalEvidenceNextPhase.HUGGING_FACE_PUBLICATION_LAYER_DESIGN
    )


class AuraGatewayV2TerminalEvidenceReview(BaseModel):
    """Immutable project-level conclusion for the v2 core runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-v2-terminal-evidence-review-v1"]
    status: Literal[
        TerminalEvidenceReviewStatus.CLOSED_CORE_RUNTIME_WITH_NEGATIVE_PROVIDER_TELEMETRY
    ] = TerminalEvidenceReviewStatus.CLOSED_CORE_RUNTIME_WITH_NEGATIVE_PROVIDER_TELEMETRY
    source_commit: str
    prd_version: Literal["2.2.0"] = "2.2.0"
    source_bindings: tuple[TerminalEvidenceBinding, ...] = Field(
        min_length=18,
        max_length=18,
    )
    gate_4_resolution: TerminalEvidenceGate4Resolution
    achieved_state: TerminalEvidenceAchievedState
    claims: tuple[TerminalEvidenceClaimRecord, ...] = Field(
        min_length=14,
        max_length=14,
    )
    publication_boundary: TerminalEvidencePublicationBoundary
    core_scope_closed: Literal[True] = True
    identical_provider_rerun_permitted: Literal[False] = False
    additional_provider_execution_permitted: Literal[False] = False
    execution_evidence_mutation_permitted: Literal[False] = False
    next_phase: Literal[TerminalEvidenceNextPhase.HUGGING_FACE_PUBLICATION_LAYER_DESIGN] = (
        TerminalEvidenceNextPhase.HUGGING_FACE_PUBLICATION_LAYER_DESIGN
    )

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal review requires a full lowercase commit SHA")
        return value

    @model_validator(mode="after")
    def validate_review(self) -> AuraGatewayV2TerminalEvidenceReview:
        observed_paths = [item.path for item in self.source_bindings]
        if len(set(observed_paths)) != 18:
            raise ValueError("terminal review requires 18 unique source bindings")

        expected_claims = set(TerminalEvidenceClaimKind)
        observed_claims = [item.claim_kind for item in self.claims]
        if set(observed_claims) != expected_claims or len(observed_claims) != len(
            set(observed_claims)
        ):
            raise ValueError("terminal review requires all 14 claim decisions")

        permitted = {
            TerminalEvidenceClaimKind.CORE_RUNTIME_AND_HARNESS_IMPLEMENTED,
            TerminalEvidenceClaimKind.DETERMINISTIC_PREFIX_CONSTRUCTION,
            TerminalEvidenceClaimKind.CACHE_AFFINITY_POLICY_IMPLEMENTED,
            TerminalEvidenceClaimKind.TELEMETRY_UNKNOWN_PRESERVED,
            TerminalEvidenceClaimKind.TERMINAL_EVIDENCE_INTEGRITY,
            TerminalEvidenceClaimKind.OBSERVED_PROVIDER_WIRE_OMISSION,
        }
        for claim in self.claims:
            expected_decision = (
                TerminalEvidenceClaimDecision.PERMITTED
                if claim.claim_kind in permitted
                else TerminalEvidenceClaimDecision.BLOCKED
            )
            if claim.decision is not expected_decision:
                raise ValueError("terminal claim decision does not match evidence boundary")

        if self.next_phase is not self.publication_boundary.next_phase:
            raise ValueError("terminal review and publication boundary must select one next phase")
        return self


class AuraGatewayV2TerminalEvidenceReviewManifest(BaseModel):
    """Integrity manifest for review and governing-document updates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-v2-terminal-evidence-review-v1"]
    source_commit: str
    review_path: Literal[
        "data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1/review.json"
    ]
    review_sha256: str
    report_path: Literal["docs/benchmark/AuraGateway_v2_Terminal_Evidence_Review.md"]
    report_sha256: str
    adr_path: Literal["docs/adr/auragateway-v2-terminal-evidence-review.md"]
    adr_sha256: str
    prd_path: Literal["docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md"]
    prd_sha256: str
    session_brief_path: Literal["docs/session/AuraGateway_SESSION_BRIEF.md"]
    session_brief_sha256: str
    readme_path: Literal["README.md"]
    readme_sha256: str
    publication_prd_path: Literal["docs/product/AuraGateway_Hugging_Face_Publication_Layer_PRD.md"]
    publication_prd_sha256: str
    source_evidence_locked: Literal[True] = True
    protected_evidence_read: Literal[False] = False
    core_scope_closed: Literal[True] = True
    next_phase: Literal[TerminalEvidenceNextPhase.HUGGING_FACE_PUBLICATION_LAYER_DESIGN] = (
        TerminalEvidenceNextPhase.HUGGING_FACE_PUBLICATION_LAYER_DESIGN
    )

    @field_validator("source_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal manifest requires a full lowercase commit SHA")
        return value

    @field_validator(
        "review_sha256",
        "report_sha256",
        "adr_sha256",
        "prd_sha256",
        "session_brief_sha256",
        "readme_sha256",
        "publication_prd_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal review manifest requires lowercase SHA-256")
        return value


class TerminalEvidenceSupersededDocumentPath(StrEnum):
    """Mutable governing documents delegated to the later continuity review."""

    CORE_PRD = "docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md"
    SESSION_BRIEF = "docs/session/AuraGateway_SESSION_BRIEF.md"
    README = "README.md"


class TerminalEvidenceSupersedingHashField(StrEnum):
    """Hash fields exposed by the superseding Hy3 terminal-review manifest."""

    CORE_PRD_SHA256 = "core_prd_sha256"
    SESSION_BRIEF_SHA256 = "session_brief_sha256"
    README_SHA256 = "readme_sha256"


class TerminalEvidenceSupersededAsset(BaseModel):
    """One historical governing-document binding delegated to a later manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: TerminalEvidenceSupersededDocumentPath
    historical_sha256: str
    superseding_hash_field: TerminalEvidenceSupersedingHashField
    superseding_sha256: str
    reason: Literal["governing_document_superseded_by_terminal_continuity"] = (
        "governing_document_superseded_by_terminal_continuity"
    )

    @field_validator("historical_sha256", "superseding_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("superseded document bindings require lowercase SHA-256")
        return value


class OpenRouterHy3TerminalEvidenceReviewManifest(BaseModel):
    """Typed subset-complete manifest for the later Hy3 terminal continuity review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["openrouter-hy3-terminal-evidence-review-v1"]
    source_main_checkpoint: str
    source_closeout_result_sha256: str
    source_closeout_manifest_sha256: str
    source_closeout_policy_sha256: str
    review_sha256: str
    readme_sha256: str
    core_prd_sha256: str
    hy3_mini_prd_sha256: str
    session_brief_sha256: str
    terminal_review_sha256: str
    provider_matrix_sha256: str
    adr_sha256: str
    handover_sha256: str
    terminal_outcome: Literal["closed_terminal_provider_failure"]
    comparison_eligible: Literal[False] = False
    pilot_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    runtime_rerun_permitted: Literal[False] = False
    raw_provider_payload_published: Literal[False] = False
    protected_prompt_published: Literal[False] = False
    credential_published: Literal[False] = False
    generated_at: date

    @field_validator("source_main_checkpoint")
    @classmethod
    def validate_source_main_checkpoint(cls, value: str) -> str:
        if re.fullmatch(r"[0-9a-f]{7,40}", value) is None:
            raise ValueError("Hy3 terminal manifest requires a lowercase Git checkpoint")
        return value

    @field_validator(
        "source_closeout_result_sha256",
        "source_closeout_manifest_sha256",
        "source_closeout_policy_sha256",
        "review_sha256",
        "readme_sha256",
        "core_prd_sha256",
        "hy3_mini_prd_sha256",
        "session_brief_sha256",
        "terminal_review_sha256",
        "provider_matrix_sha256",
        "adr_sha256",
        "handover_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("Hy3 terminal manifest requires lowercase SHA-256")
        return value


class AuraGatewayV2TerminalEvidenceReviewSupersession(BaseModel):
    """Additive overlay delegating mutable governing documents to a later review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    supersession_id: Literal["auragateway-v2-terminal-evidence-review-supersession-v1"]
    source_review_id: Literal["auragateway-v2-terminal-evidence-review-v1"]
    source_manifest_path: Literal[
        "data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1/manifest.json"
    ]
    source_manifest_sha256: str
    superseding_review_id: Literal["openrouter-hy3-terminal-evidence-review-v1"]
    superseding_manifest_path: Literal[
        "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/manifest.json"
    ]
    superseding_manifest_sha256: str
    superseding_source_main_checkpoint: Literal["00d0712"]
    superseding_merge_checkpoint: Literal["768800b"]
    effective_prd_version: Literal["2.3.0"]
    assets: tuple[TerminalEvidenceSupersededAsset, ...] = Field(
        min_length=3,
        max_length=3,
    )
    historical_manifest_immutable: Literal[True] = True
    source_evidence_locked: Literal[True] = True
    protected_evidence_read: Literal[False] = False
    provider_execution_permitted: Literal[False] = False
    next_phase: Literal["hugging_face_static_publication_package"] = (
        "hugging_face_static_publication_package"
    )

    @field_validator("source_manifest_sha256", "superseding_manifest_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("terminal supersession requires lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_assets(self) -> AuraGatewayV2TerminalEvidenceReviewSupersession:
        expected = {
            TerminalEvidenceSupersededDocumentPath.CORE_PRD: (
                TerminalEvidenceSupersedingHashField.CORE_PRD_SHA256
            ),
            TerminalEvidenceSupersededDocumentPath.SESSION_BRIEF: (
                TerminalEvidenceSupersedingHashField.SESSION_BRIEF_SHA256
            ),
            TerminalEvidenceSupersededDocumentPath.README: (
                TerminalEvidenceSupersedingHashField.README_SHA256
            ),
        }
        observed = {item.path: item.superseding_hash_field for item in self.assets}
        if observed != expected:
            raise ValueError("terminal supersession requires the exact three document mappings")
        return self


class AuraGatewayV2TerminalEvidenceReviewSummary(BaseModel):
    """Metadata-safe CLI result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    review_id: Literal["auragateway-v2-terminal-evidence-review-v1"]
    status: TerminalEvidenceReviewStatus
    prd_version: Literal["2.2.0"] = "2.2.0"
    source_binding_count: Literal[18] = 18
    core_scope_closed: Literal[True] = True
    gate_4_passed_for_measured_benchmark: Literal[False] = False
    measured_a_b_c_comparison_completed: Literal[False] = False
    provider_cache_usage_measured: Literal[False] = False
    benchmark_claims_permitted: Literal[False] = False
    comparison_eligible: Literal[False] = False
    additional_provider_execution_permitted: Literal[False] = False
    next_phase: TerminalEvidenceNextPhase
