"""Typed contracts for held-out retrieval validation and Gate 1 freeze evidence."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.contracts.retrieval_selection import (
    MetadataPolicy,
    RetrievalSelectionVariant,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _validate_sha256(value: str, field_name: str) -> str:
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must contain 64 lowercase hexadecimal characters")
    return value


class GateOneDecisionStatus(StrEnum):
    """Held-out comparison outcome."""

    CONFIRMED = "development_recommendation_confirmed"
    REVERSED = "development_recommendation_reversed"
    BLOCKED = "gate_1_blocked"


class RetrievalFreezeStatus(StrEnum):
    """Lifecycle state for the selected retrieval contract."""

    FROZEN = "frozen"


class HeldOutFreezeRecord(BaseModel):
    """Evidence that held-out authoring was frozen before candidate scoring."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    record_id: str = "nimbus-relay-held-out-freeze-v1"
    status: str = "frozen_before_candidate_evaluation"
    freeze_date: date
    held_out_set_path: str
    held_out_set_sha256: str
    rejected_set_path: str
    rejected_set_sha256: str
    development_set_path: str
    development_set_sha256: str
    authoring_complete: bool = True
    candidate_results_present_at_freeze: bool = False

    @model_validator(mode="after")
    def validate_record(self) -> HeldOutFreezeRecord:
        for name, value in (
            ("held_out_set_sha256", self.held_out_set_sha256),
            ("rejected_set_sha256", self.rejected_set_sha256),
            ("development_set_sha256", self.development_set_sha256),
        ):
            _validate_sha256(value, name)
        if not self.authoring_complete:
            raise ValueError("held-out authoring must be complete before freeze")
        if self.candidate_results_present_at_freeze:
            raise ValueError("candidate results must not exist when held-out authoring is frozen")
        return self


class HeldOutFinalist(BaseModel):
    """One development finalist admitted to held-out validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    retriever_config_id: str
    retriever_config_sha256: str
    chunking_config_id: str
    retrieval_manifest_path: str
    retrieval_manifest_sha256: str
    development_rank: int = Field(ge=1)
    development_final_score: float = Field(ge=0.0, le=100.0)
    top_k: int = Field(default=5, ge=1, le=20)
    metadata_policy: MetadataPolicy = MetadataPolicy.AUTHORED

    @model_validator(mode="after")
    def validate_finalist(self) -> HeldOutFinalist:
        _validate_sha256(self.retriever_config_sha256, "retriever_config_sha256")
        _validate_sha256(self.retrieval_manifest_sha256, "retrieval_manifest_sha256")
        if self.metadata_policy is not MetadataPolicy.AUTHORED:
            raise ValueError("held-out finalists must use the authored metadata policy")
        return self


class HeldOutValidationPolicy(BaseModel):
    """Frozen held-out comparison policy derived from development selection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    policy_id: str = "retrieval-held-out-validation-v1"
    status: str = "frozen_before_candidate_evaluation"
    selection_policy_path: str
    selection_policy_sha256: str
    development_report_path: str
    development_report_sha256: str
    held_out_freeze_record_path: str
    held_out_freeze_record_sha256: str
    finalists: tuple[HeldOutFinalist, ...] = Field(min_length=2, max_length=2)
    decision_rule: str = "highest-score-among-hard-gate-passers-v1"
    tie_break_policy: tuple[str, ...] = (
        "final_score_desc",
        "mean_recall_at_k_desc",
        "citation_support_readiness_rate_desc",
        "unsupported_source_retrieval_rate_asc",
        "development_rank_asc",
        "retriever_config_id_asc",
    )
    development_recommendation_is_not_auto_confirmed: bool = True
    minimum_held_out_case_count: int = 12
    retrieval_freeze_requires_gate_pass: bool = True
    measured_execution_permitted: bool = False

    @model_validator(mode="after")
    def validate_policy(self) -> HeldOutValidationPolicy:
        for name, value in (
            ("selection_policy_sha256", self.selection_policy_sha256),
            ("development_report_sha256", self.development_report_sha256),
            ("held_out_freeze_record_sha256", self.held_out_freeze_record_sha256),
        ):
            _validate_sha256(value, name)
        config_ids = [item.retriever_config_id for item in self.finalists]
        ranks = [item.development_rank for item in self.finalists]
        duplicate_config_ids = sorted(
            value for value, count in Counter(config_ids).items() if count > 1
        )
        if duplicate_config_ids:
            raise ValueError("duplicate finalist config IDs: " + ", ".join(duplicate_config_ids))
        duplicate_ranks = sorted(value for value, count in Counter(ranks).items() if count > 1)
        if duplicate_ranks:
            raise ValueError(
                "duplicate development ranks: " + ", ".join(str(item) for item in duplicate_ranks)
            )
        if sorted(ranks) != [1, 2]:
            raise ValueError("held-out finalists must be development ranks one and two")
        if len({item.top_k for item in self.finalists}) != 1:
            raise ValueError("held-out finalists must use the same top_k")
        if not self.development_recommendation_is_not_auto_confirmed:
            raise ValueError("development recommendation must not be auto-confirmed")
        if not self.retrieval_freeze_requires_gate_pass:
            raise ValueError("retrieval freeze must require a held-out hard-gate pass")
        if self.measured_execution_permitted:
            raise ValueError("Gate 1 policy cannot permit measured runtime execution")
        return self


class HeldOutScorecardReference(BaseModel):
    """Hash reference to one held-out finalist scorecard and case result set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    retriever_config_id: str
    scorecard_path: str
    scorecard_sha256: str
    case_results_path: str
    case_results_sha256: str

    @model_validator(mode="after")
    def validate_reference(self) -> HeldOutScorecardReference:
        _validate_sha256(self.scorecard_sha256, "scorecard_sha256")
        _validate_sha256(self.case_results_sha256, "case_results_sha256")
        return self


class HeldOutCandidateEvidence(BaseModel):
    """One held-out finalist result under the frozen comparison policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    development_rank: int = Field(ge=1)
    scorecard: HeldOutScorecardReference
    variant: RetrievalSelectionVariant

    @model_validator(mode="after")
    def validate_evidence(self) -> HeldOutCandidateEvidence:
        if self.scorecard.retriever_config_id != self.variant.retriever_config_id:
            raise ValueError("scorecard and variant must reference the same retriever")
        if self.variant.metadata_policy is not MetadataPolicy.AUTHORED:
            raise ValueError("held-out evidence must use the authored metadata policy")
        return self


class HeldOutRetrievalDecision(BaseModel):
    """Machine-enforced held-out decision for Gate 1."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: GateOneDecisionStatus
    development_recommended_retriever_config_id: str
    selected_retriever_config_id: str | None = None
    selected_chunking_config_id: str | None = None
    selected_top_k: int | None = None
    selected_metadata_policy: MetadataPolicy | None = None
    selected_final_score: float | None = None
    development_recommendation_confirmed: bool = False
    rationale: tuple[str, ...] = Field(min_length=1)
    gate_1_passed: bool
    retrieval_freeze_permitted: bool
    measured_execution_permitted: bool = False
    required_next_gate: str

    @model_validator(mode="after")
    def validate_decision(self) -> HeldOutRetrievalDecision:
        selected_fields = (
            self.selected_retriever_config_id,
            self.selected_chunking_config_id,
            self.selected_top_k,
            self.selected_metadata_policy,
            self.selected_final_score,
        )
        if self.status is GateOneDecisionStatus.BLOCKED:
            if any(value is not None for value in selected_fields):
                raise ValueError("blocked decision must not include selected candidate fields")
            if self.gate_1_passed or self.retrieval_freeze_permitted:
                raise ValueError("blocked decision cannot pass Gate 1 or permit retrieval freeze")
        else:
            if any(value is None for value in selected_fields):
                raise ValueError("passed held-out decision requires complete selected fields")
            if not self.gate_1_passed or not self.retrieval_freeze_permitted:
                raise ValueError("selected held-out decision must pass Gate 1 and permit freeze")
            should_confirm = (
                self.selected_retriever_config_id
                == self.development_recommended_retriever_config_id
            )
            if self.development_recommendation_confirmed != should_confirm:
                raise ValueError("development confirmation flag must match the selected retriever")
            if self.status is GateOneDecisionStatus.CONFIRMED and not should_confirm:
                raise ValueError("confirmed status requires the development recommendation")
            if self.status is GateOneDecisionStatus.REVERSED and should_confirm:
                raise ValueError("reversed status requires a different selected retriever")
        if self.measured_execution_permitted:
            raise ValueError("Gate 1 cannot permit measured runtime execution")
        return self


class HeldOutValidationReport(BaseModel):
    """Hash-bound held-out comparison and Gate 1 decision report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str = "nimbus-relay-held-out-retrieval-decision-v1"
    status: str = "gate_1_decision"
    held_out_policy_path: str
    held_out_policy_sha256: str
    held_out_set_path: str
    held_out_set_sha256: str
    rejected_set_path: str
    rejected_set_sha256: str
    freeze_record_path: str
    freeze_record_sha256: str
    development_selection_report_path: str
    development_selection_report_sha256: str
    candidate_evidence: tuple[HeldOutCandidateEvidence, ...] = Field(min_length=2, max_length=2)
    decision: HeldOutRetrievalDecision

    @model_validator(mode="after")
    def validate_report(self) -> HeldOutValidationReport:
        for name, value in (
            ("held_out_policy_sha256", self.held_out_policy_sha256),
            ("held_out_set_sha256", self.held_out_set_sha256),
            ("rejected_set_sha256", self.rejected_set_sha256),
            ("freeze_record_sha256", self.freeze_record_sha256),
            ("development_selection_report_sha256", self.development_selection_report_sha256),
        ):
            _validate_sha256(value, name)
        config_ids = [item.variant.retriever_config_id for item in self.candidate_evidence]
        if len(config_ids) != len(set(config_ids)):
            raise ValueError("held-out candidate evidence must reference unique retrievers")
        return self


class RetrievalFreezeManifest(BaseModel):
    """Frozen retrieval contract selected by a passed Gate 1 decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    freeze_id: str = "nimbus-relay-retrieval-freeze-v1"
    status: RetrievalFreezeStatus = RetrievalFreezeStatus.FROZEN
    freeze_date: date
    gate_1_decision_path: str
    gate_1_decision_sha256: str
    selected_retriever_config_id: str
    selected_retriever_config_sha256: str
    selected_chunking_config_id: str
    selected_top_k: int = Field(ge=1, le=20)
    selected_metadata_policy: MetadataPolicy
    corpus_manifest_path: str
    corpus_manifest_sha256: str
    chunking_manifest_path: str
    chunking_manifest_sha256: str
    retrieval_manifest_path: str
    retrieval_manifest_sha256: str
    held_out_set_path: str
    held_out_set_sha256: str
    held_out_scorecard_path: str
    held_out_scorecard_sha256: str
    development_selection_policy_path: str
    development_selection_policy_sha256: str
    development_selection_report_path: str
    development_selection_report_sha256: str
    configuration_fingerprint: str
    gate_1_passed: bool = True
    measured_execution_permitted: bool = False
    required_next_gate: str = "gate_2_diagnostic_eval_asset_readiness"

    @model_validator(mode="after")
    def validate_manifest(self) -> RetrievalFreezeManifest:
        for name, value in (
            ("gate_1_decision_sha256", self.gate_1_decision_sha256),
            ("selected_retriever_config_sha256", self.selected_retriever_config_sha256),
            ("corpus_manifest_sha256", self.corpus_manifest_sha256),
            ("chunking_manifest_sha256", self.chunking_manifest_sha256),
            ("retrieval_manifest_sha256", self.retrieval_manifest_sha256),
            ("held_out_set_sha256", self.held_out_set_sha256),
            ("held_out_scorecard_sha256", self.held_out_scorecard_sha256),
            ("development_selection_policy_sha256", self.development_selection_policy_sha256),
            ("development_selection_report_sha256", self.development_selection_report_sha256),
            ("configuration_fingerprint", self.configuration_fingerprint),
        ):
            _validate_sha256(value, name)
        if self.selected_metadata_policy is not MetadataPolicy.AUTHORED:
            raise ValueError("frozen retrieval must use the authored metadata policy")
        if not self.gate_1_passed:
            raise ValueError("retrieval freeze requires Gate 1 pass")
        if self.measured_execution_permitted:
            raise ValueError("retrieval freeze alone cannot permit measured runtime execution")
        return self


class GateOneSummary(BaseModel):
    """Safe CLI build or verification summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    report_id: str
    held_out_case_count: int
    finalist_count: int
    passing_finalist_count: int
    decision_status: GateOneDecisionStatus
    selected_retriever_config_id: str | None
    selected_top_k: int | None
    selected_final_score: float | None
    gate_1_passed: bool
    retrieval_freeze_permitted: bool
    retrieval_configuration_fingerprint: str | None
    measured_execution_permitted: bool
    validation_status: str
