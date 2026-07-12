"""Typed contracts for frozen multi-turn diagnostic benchmark episodes."""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.retrieval_eval import TerminalDecision

_EPISODE_ID_PATTERN = re.compile(r"^ep-func-[0-9]{3}$")
_PROPOSAL_ID_PATTERN = re.compile(r"^ep-reject-[0-9]{3}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class EpisodeAssetStatus(StrEnum):
    """Lifecycle state for diagnostic episode assets."""

    FROZEN = "frozen"


class EpisodeEvaluationSplit(StrEnum):
    """Functional benchmark split for an accepted episode."""

    DEVELOPMENT = "development"
    HELD_OUT = "held_out"


class EpisodeDifficulty(StrEnum):
    """Diagnostic difficulty classification."""

    MEDIUM = "medium"
    HIGH = "high"


class EpisodeCaseFamily(StrEnum):
    """Failure hypotheses represented in the functional benchmark."""

    VERSION_CONFLICTING_SOURCES = "version_conflicting_sources"
    SIMILAR_ERROR_CODES = "similar_error_codes"
    MISSING_REQUIRED_PARAMETERS = "missing_required_parameters"
    INCOMPLETE_DOCUMENTATION = "incomplete_documentation"
    REPEATED_USER_INFORMATION = "repeated_user_information"
    CONTRADICTORY_USER_CORRECTION = "contradictory_user_correction"
    DUPLICATE_RETRIEVAL_EVIDENCE = "duplicate_retrieval_evidence"
    NOISY_CONTEXT_DILUTION = "noisy_context_dilution"
    UNSUPPORTED_REQUESTED_BEHAVIOUR = "unsupported_requested_behaviour"
    MODEL_CAPABILITY_EDGE_CASES = "model_capability_edge_cases"
    MULTI_TURN_EVIDENCE_CORRECTION = "multi_turn_evidence_correction"
    PROVIDER_FAILURE_MID_SESSION = "provider_failure_mid_session"
    MULTI_SOURCE_GROUNDING = "multi_source_grounding"
    SDK_VARIANT = "sdk_variant"
    EXACT_PROCEDURE = "exact_procedure"


REQUIRED_DIAGNOSTIC_FAMILIES: frozenset[EpisodeCaseFamily] = frozenset(
    {
        EpisodeCaseFamily.VERSION_CONFLICTING_SOURCES,
        EpisodeCaseFamily.SIMILAR_ERROR_CODES,
        EpisodeCaseFamily.MISSING_REQUIRED_PARAMETERS,
        EpisodeCaseFamily.INCOMPLETE_DOCUMENTATION,
        EpisodeCaseFamily.REPEATED_USER_INFORMATION,
        EpisodeCaseFamily.CONTRADICTORY_USER_CORRECTION,
        EpisodeCaseFamily.DUPLICATE_RETRIEVAL_EVIDENCE,
        EpisodeCaseFamily.NOISY_CONTEXT_DILUTION,
        EpisodeCaseFamily.UNSUPPORTED_REQUESTED_BEHAVIOUR,
        EpisodeCaseFamily.MODEL_CAPABILITY_EDGE_CASES,
        EpisodeCaseFamily.MULTI_TURN_EVIDENCE_CORRECTION,
        EpisodeCaseFamily.PROVIDER_FAILURE_MID_SESSION,
    }
)


class EpisodeFailureLabel(StrEnum):
    """Machine-readable diagnostic failures used by later scorers."""

    STALE_SOURCE_SELECTED = "STALE_SOURCE_SELECTED"
    FORBIDDEN_SOURCE_USED = "FORBIDDEN_SOURCE_USED"
    MISSING_REQUIRED_SOURCE = "MISSING_REQUIRED_SOURCE"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    INVALID_TERMINAL_DECISION = "INVALID_TERMINAL_DECISION"
    MISSING_CLARIFICATION = "MISSING_CLARIFICATION"
    UNNECESSARY_CLARIFICATION = "UNNECESSARY_CLARIFICATION"
    ESCALATION_BYPASSED = "ESCALATION_BYPASSED"
    REFUSAL_BYPASSED = "REFUSAL_BYPASSED"
    DUPLICATE_RETRIEVAL_EVIDENCE = "DUPLICATE_RETRIEVAL_EVIDENCE"
    REDUNDANT_FEEDBACK = "REDUNDANT_FEEDBACK"
    UNRETAINED_FEEDBACK = "UNRETAINED_FEEDBACK"
    CONTRADICTORY_STATE = "CONTRADICTORY_STATE"
    NOISY_CONTEXT_DILUTION = "NOISY_CONTEXT_DILUTION"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    PROVIDER_FAILURE_UNHANDLED = "PROVIDER_FAILURE_UNHANDLED"
    BLIND_RETRY = "BLIND_RETRY"
    INVALID_CITATION_ID = "INVALID_CITATION_ID"
    CITATION_UNSUPPORTED = "CITATION_UNSUPPORTED"
    STRUCTURED_OUTPUT_INVALID = "STRUCTURED_OUTPUT_INVALID"
    PRIVACY_VIOLATION = "PRIVACY_VIOLATION"
    TASK_INSUFFICIENT = "TASK_INSUFFICIENT"


class TerminalReasonCode(StrEnum):
    """Reason codes allowed at the terminal decision boundary."""

    EVIDENCE_SUFFICIENT = "evidence_sufficient"
    MISSING_REQUIRED_PARAMETER = "missing_required_parameter"
    AMBIGUOUS_USER_STATE = "ambiguous_user_state"
    INCOMPLETE_DOCUMENTATION = "incomplete_documentation"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    SECRET_HANDLING_PROHIBITED = "secret_handling_prohibited"
    UNSAFE_UNGROUNDED_REQUEST = "unsafe_ungrounded_request"


class EscalationReasonCode(StrEnum):
    """Typed reasons that permit escalation."""

    DOCUMENTATION_GAP = "documentation_gap"
    PROVIDER_FAILURE = "provider_failure"
    UNRESOLVED_TECHNICAL_RISK = "unresolved_technical_risk"


class RefusalReasonCode(StrEnum):
    """Typed reasons that permit refusal."""

    UNSUPPORTED_PRODUCT_BEHAVIOUR = "unsupported_product_behaviour"
    SECRET_EXTRACTION_OR_RECOVERY = "secret_extraction_or_recovery"
    UNSUPPORTED_TECHNICAL_CLAIM = "unsupported_technical_claim"


class RejectedEpisodeReasonCode(StrEnum):
    """Reasons a proposed diagnostic episode is rejected."""

    TRIVIAL = "trivial"
    AMBIGUOUS = "ambiguous"
    DUPLICATE = "duplicate"
    UNGROUNDED = "ungrounded"
    NON_DIAGNOSTIC = "non_diagnostic"
    PRIVACY_RISK = "privacy_risk"


class EpisodeSourceScope(BaseModel):
    """Corpus evidence allowed for one episode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    required_source_ids: tuple[str, ...] = Field(min_length=1)
    forbidden_source_ids: tuple[str, ...] = ()
    optional_source_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_scope(self) -> EpisodeSourceScope:
        groups = {
            "required": set(self.required_source_ids),
            "forbidden": set(self.forbidden_source_ids),
            "optional": set(self.optional_source_ids),
        }
        for name, values in groups.items():
            if len(values) != len(getattr(self, f"{name}_source_ids")):
                raise ValueError(f"{name} source IDs must be unique")
        if groups["required"] & groups["forbidden"]:
            raise ValueError("required and forbidden source IDs must not overlap")
        if groups["required"] & groups["optional"]:
            raise ValueError("required and optional source IDs must not overlap")
        if groups["forbidden"] & groups["optional"]:
            raise ValueError("forbidden and optional source IDs must not overlap")
        return self


class EpisodeTurn(BaseModel):
    """One synthetic user turn and expected trajectory behaviour."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_index: int = Field(ge=1, le=4)
    user_message: str = Field(min_length=10, max_length=2000)
    expected_information_gain: tuple[str, ...] = Field(min_length=1)
    expected_decision: TerminalDecision
    required_state_updates: tuple[str, ...] = ()
    forbidden_assumptions: tuple[str, ...] = ()

    @field_validator(
        "expected_information_gain",
        "required_state_updates",
        "forbidden_assumptions",
    )
    @classmethod
    def normalize_text_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("turn text items must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("turn text items must be unique")
        return normalized


class AnswerExpectation(BaseModel):
    """Required terminal evidence for an answer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[TerminalDecision.ANSWER]
    reason_code: Literal[TerminalReasonCode.EVIDENCE_SUFFICIENT]
    required_claims: tuple[str, ...] = Field(min_length=1)
    forbidden_claims: tuple[str, ...] = ()
    required_citation_source_ids: tuple[str, ...] = Field(min_length=1)


class ClarifyExpectation(BaseModel):
    """Required terminal evidence for a clarification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[TerminalDecision.CLARIFY]
    reason_code: Literal[
        TerminalReasonCode.MISSING_REQUIRED_PARAMETER,
        TerminalReasonCode.AMBIGUOUS_USER_STATE,
    ]
    required_question_fields: tuple[str, ...] = Field(min_length=1)
    forbidden_assumptions: tuple[str, ...] = Field(min_length=1)
    must_not_answer: Literal[True] = True


class EscalateExpectation(BaseModel):
    """Required terminal evidence for an escalation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[TerminalDecision.ESCALATE]
    reason_code: Literal[
        TerminalReasonCode.INCOMPLETE_DOCUMENTATION,
        TerminalReasonCode.PROVIDER_UNAVAILABLE,
    ]
    escalation_reason_code: EscalationReasonCode
    required_evidence_source_ids: tuple[str, ...] = Field(min_length=1)
    must_not_fabricate_procedure: Literal[True] = True


class RefuseExpectation(BaseModel):
    """Required terminal evidence for a refusal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[TerminalDecision.REFUSE]
    reason_code: Literal[
        TerminalReasonCode.UNSUPPORTED_CAPABILITY,
        TerminalReasonCode.SECRET_HANDLING_PROHIBITED,
        TerminalReasonCode.UNSAFE_UNGROUNDED_REQUEST,
    ]
    refusal_reason_code: RefusalReasonCode
    safe_alternative: str = Field(min_length=10, max_length=500)
    must_not_substitute_advice: Literal[True] = True


ExpectedTerminalDecision: TypeAlias = Annotated[
    AnswerExpectation | ClarifyExpectation | EscalateExpectation | RefuseExpectation,
    Field(discriminator="decision"),
]


class AnswerDecisionOutput(BaseModel):
    """Validated runtime output for a terminal answer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[TerminalDecision.ANSWER]
    reason_code: Literal[TerminalReasonCode.EVIDENCE_SUFFICIENT]
    response: str = Field(min_length=1)
    citation_ids: tuple[str, ...] = Field(min_length=1)
    unresolved_items: tuple[str, ...] = ()


class ClarifyDecisionOutput(BaseModel):
    """Validated runtime output for a terminal clarification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[TerminalDecision.CLARIFY]
    reason_code: Literal[
        TerminalReasonCode.MISSING_REQUIRED_PARAMETER,
        TerminalReasonCode.AMBIGUOUS_USER_STATE,
    ]
    question: str = Field(min_length=5)
    missing_fields: tuple[str, ...] = Field(min_length=1)
    citation_ids: tuple[str, ...] = ()


class EscalateDecisionOutput(BaseModel):
    """Validated runtime output for a terminal escalation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[TerminalDecision.ESCALATE]
    reason_code: Literal[
        TerminalReasonCode.INCOMPLETE_DOCUMENTATION,
        TerminalReasonCode.PROVIDER_UNAVAILABLE,
    ]
    escalation_reason_code: EscalationReasonCode
    explanation: str = Field(min_length=10)
    evidence_source_ids: tuple[str, ...] = Field(min_length=1)


class RefuseDecisionOutput(BaseModel):
    """Validated runtime output for a terminal refusal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal[TerminalDecision.REFUSE]
    reason_code: Literal[
        TerminalReasonCode.UNSUPPORTED_CAPABILITY,
        TerminalReasonCode.SECRET_HANDLING_PROHIBITED,
        TerminalReasonCode.UNSAFE_UNGROUNDED_REQUEST,
    ]
    refusal_reason_code: RefusalReasonCode
    explanation: str = Field(min_length=10)
    safe_alternative: str = Field(min_length=10)


TerminalDecisionOutput: TypeAlias = Annotated[
    AnswerDecisionOutput | ClarifyDecisionOutput | EscalateDecisionOutput | RefuseDecisionOutput,
    Field(discriminator="decision"),
]


class BenchmarkEpisode(BaseModel):
    """One accepted four-turn diagnostic episode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: str
    title: str = Field(min_length=8, max_length=160)
    task_type: str = "api_troubleshooting_support"
    case_family: EpisodeCaseFamily
    failure_hypothesis: str = Field(min_length=20, max_length=600)
    difficulty: EpisodeDifficulty
    evaluation_split: EpisodeEvaluationSplit
    turns: tuple[EpisodeTurn, ...] = Field(min_length=4, max_length=4)
    source_scope: EpisodeSourceScope
    expected_terminal_decision: ExpectedTerminalDecision
    required_information_gain: tuple[str, ...] = Field(min_length=1)
    acceptable_variants: tuple[str, ...] = Field(min_length=1)
    failure_labels: tuple[EpisodeFailureLabel, ...] = Field(min_length=1)
    accept_reason: str = Field(min_length=20, max_length=500)
    difficulty_reason: str = Field(min_length=20, max_length=500)
    runtime_eligible: bool = False

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value

    @model_validator(mode="after")
    def validate_episode(self) -> BenchmarkEpisode:
        indexes = tuple(turn.turn_index for turn in self.turns)
        if indexes != (1, 2, 3, 4):
            raise ValueError("episodes must contain exactly four ordered turns")
        if self.turns[-1].expected_decision is not self.expected_terminal_decision.decision:
            raise ValueError("final turn decision must match expected terminal decision")
        if isinstance(self.expected_terminal_decision, AnswerExpectation):
            required = set(self.source_scope.required_source_ids)
            citations = set(self.expected_terminal_decision.required_citation_source_ids)
            if not citations.issubset(required):
                raise ValueError("answer citation requirements must be required episode sources")
        if isinstance(self.expected_terminal_decision, EscalateExpectation):
            required = set(self.source_scope.required_source_ids)
            evidence = set(self.expected_terminal_decision.required_evidence_source_ids)
            if not evidence.issubset(required):
                raise ValueError("escalation evidence must be required episode sources")
        return self


class FunctionalEpisodeSet(BaseModel):
    """Frozen 18-episode functional benchmark asset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    set_id: str = "nimbus-relay-functional-episodes-v1"
    status: EpisodeAssetStatus = EpisodeAssetStatus.FROZEN
    episode_count: int = 18
    development_episode_count: int = 12
    held_out_episode_count: int = 6
    turns_per_episode: int = 4
    episodes: tuple[BenchmarkEpisode, ...] = Field(min_length=18, max_length=18)

    @model_validator(mode="after")
    def validate_set(self) -> FunctionalEpisodeSet:
        if len(self.episodes) != self.episode_count:
            raise ValueError("episode_count must match accepted episodes")
        episode_ids = [episode.episode_id for episode in self.episodes]
        duplicates = sorted(value for value, count in Counter(episode_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate episode IDs: {', '.join(duplicates)}")
        development_count = sum(
            episode.evaluation_split is EpisodeEvaluationSplit.DEVELOPMENT
            for episode in self.episodes
        )
        held_out_count = sum(
            episode.evaluation_split is EpisodeEvaluationSplit.HELD_OUT for episode in self.episodes
        )
        if development_count != self.development_episode_count:
            raise ValueError("development episode count does not match")
        if held_out_count != self.held_out_episode_count:
            raise ValueError("held-out episode count does not match")
        families = {episode.case_family for episode in self.episodes}
        missing_families = sorted(
            family.value for family in REQUIRED_DIAGNOSTIC_FAMILIES - families
        )
        if missing_families:
            raise ValueError(f"missing required diagnostic families: {', '.join(missing_families)}")
        decision_counts = Counter(
            episode.expected_terminal_decision.decision for episode in self.episodes
        )
        for decision in TerminalDecision:
            if decision_counts[decision] < 2:
                raise ValueError(
                    f"terminal decision {decision.value} requires at least two episodes"
                )
        normalized_messages: list[str] = []
        for episode in self.episodes:
            normalized_messages.extend(
                turn.user_message.strip().casefold() for turn in episode.turns
            )
        duplicate_messages = sorted(
            value for value, count in Counter(normalized_messages).items() if count > 1
        )
        if duplicate_messages:
            raise ValueError("accepted episodes must not repeat exact user messages")
        return self


class RejectedEpisodeProposal(BaseModel):
    """One rejected diagnostic episode proposal with retained rationale."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str
    title: str = Field(min_length=8, max_length=160)
    reason_code: RejectedEpisodeReasonCode
    reject_reason: str = Field(min_length=20, max_length=500)
    overlaps_episode_ids: tuple[str, ...] = ()

    @field_validator("proposal_id")
    @classmethod
    def validate_proposal_id(cls, value: str) -> str:
        if _PROPOSAL_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("proposal_id must match ep-reject-<NNN>")
        return value


class RejectedEpisodeSet(BaseModel):
    """Rejected proposals retained for autodata-style evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    set_id: str = "nimbus-relay-rejected-episode-proposals-v1"
    status: EpisodeAssetStatus = EpisodeAssetStatus.FROZEN
    proposals: tuple[RejectedEpisodeProposal, ...] = Field(min_length=6)

    @model_validator(mode="after")
    def validate_set(self) -> RejectedEpisodeSet:
        proposal_ids = [proposal.proposal_id for proposal in self.proposals]
        if len(proposal_ids) != len(set(proposal_ids)):
            raise ValueError("rejected proposal IDs must be unique")
        return self


class RuntimeEpisodeEntry(BaseModel):
    """One functional episode selected for runtime microbenchmark use."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: str
    selection_reason: str = Field(min_length=20, max_length=500)
    expected_terminal_decision: TerminalDecision


class RuntimeEpisodeSelection(BaseModel):
    """Frozen six-episode runtime microbenchmark subset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    set_id: str = "nimbus-relay-runtime-episodes-v1"
    status: EpisodeAssetStatus = EpisodeAssetStatus.FROZEN
    source_functional_set_id: str = "nimbus-relay-functional-episodes-v1"
    episode_count: int = 6
    entries: tuple[RuntimeEpisodeEntry, ...] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def validate_selection(self) -> RuntimeEpisodeSelection:
        episode_ids = [entry.episode_id for entry in self.entries]
        if len(episode_ids) != len(set(episode_ids)):
            raise ValueError("runtime episode IDs must be unique")
        if len(self.entries) != self.episode_count:
            raise ValueError("runtime episode count does not match entries")
        decisions = {entry.expected_terminal_decision for entry in self.entries}
        if decisions != set(TerminalDecision):
            raise ValueError("runtime subset must represent all terminal decisions")
        return self


class BlindedReviewProtocol(BaseModel):
    """Prepared blinded-review and adjudication policy for functional episodes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    protocol_id: str = "blinded-adjudication-v1"
    status: str = "prepared"
    primary_review_fraction: float = Field(default=1.0, ge=0.0, le=1.0)
    double_review_fraction: float = Field(default=0.25, ge=0.0, le=1.0)
    double_review_episode_count: int = Field(default=5, ge=1)
    sampling_seed: int = 20260712
    reviewer_hidden_fields: tuple[str, ...] = Field(min_length=1)
    reviewer_visible_fields: tuple[str, ...] = Field(min_length=1)
    adjudication_required_for_material_disagreement: bool = True
    adjudicator_must_be_independent: bool = True
    protected_review_export_required: bool = True
    public_trace_contains_raw_content: bool = False

    @model_validator(mode="after")
    def validate_protocol(self) -> BlindedReviewProtocol:
        required_hidden = {
            "condition_id",
            "provider",
            "model",
            "route",
            "cost",
            "latency",
            "cache_telemetry",
            "run_order",
        }
        if not required_hidden.issubset(set(self.reviewer_hidden_fields)):
            raise ValueError("review protocol does not hide every required experimental field")
        if self.primary_review_fraction != 1.0:
            raise ValueError("all functional trajectories require primary review")
        if self.double_review_fraction != 0.25:
            raise ValueError("double-review fraction must remain 25 percent")
        if self.public_trace_contains_raw_content:
            raise ValueError("public traces must not contain raw review content")
        return self


class EpisodeAssetManifest(BaseModel):
    """Hash-bound inventory for Gate 2 diagnostic episode assets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "nimbus-relay-diagnostic-episode-manifest-v1"
    status: EpisodeAssetStatus = EpisodeAssetStatus.FROZEN
    retrieval_freeze_path: str
    retrieval_freeze_sha256: str
    retrieval_configuration_fingerprint: str
    functional_set_path: str
    functional_set_sha256: str
    rejected_set_path: str
    rejected_set_sha256: str
    runtime_selection_path: str
    runtime_selection_sha256: str
    review_protocol_path: str
    review_protocol_sha256: str
    functional_episode_count: int
    development_episode_count: int
    held_out_episode_count: int
    runtime_episode_count: int
    terminal_decision_counts: dict[str, int]
    case_family_counts: dict[str, int]

    @model_validator(mode="after")
    def validate_manifest(self) -> EpisodeAssetManifest:
        for name, value in (
            ("retrieval_freeze_sha256", self.retrieval_freeze_sha256),
            ("retrieval_configuration_fingerprint", self.retrieval_configuration_fingerprint),
            ("functional_set_sha256", self.functional_set_sha256),
            ("rejected_set_sha256", self.rejected_set_sha256),
            ("runtime_selection_sha256", self.runtime_selection_sha256),
            ("review_protocol_sha256", self.review_protocol_sha256),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must be lowercase SHA-256")
        if self.functional_episode_count != (
            self.development_episode_count + self.held_out_episode_count
        ):
            raise ValueError("functional split counts must reconcile")
        if sum(self.terminal_decision_counts.values()) != self.functional_episode_count:
            raise ValueError("terminal-decision counts must reconcile")
        if sum(self.case_family_counts.values()) != self.functional_episode_count:
            raise ValueError("case-family counts must reconcile")
        return self


class EpisodeFreezeRecord(BaseModel):
    """Gate 2 freeze decision for diagnostic episode assets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    freeze_id: str = "nimbus-relay-diagnostic-episode-freeze-v1"
    status: EpisodeAssetStatus = EpisodeAssetStatus.FROZEN
    manifest_path: str
    manifest_sha256: str
    gate_2_passed: bool = True
    functional_set_frozen: bool = True
    runtime_set_frozen: bool = True
    development_held_out_separation_enforced: bool = True
    blinded_review_protocol_prepared: bool = True
    measured_execution_permitted: bool = False
    required_next_gate: str = "prefix_determinism"

    @model_validator(mode="after")
    def validate_freeze(self) -> EpisodeFreezeRecord:
        if _SHA256_PATTERN.fullmatch(self.manifest_sha256) is None:
            raise ValueError("manifest_sha256 must be lowercase SHA-256")
        if not all(
            (
                self.gate_2_passed,
                self.functional_set_frozen,
                self.runtime_set_frozen,
                self.development_held_out_separation_enforced,
                self.blinded_review_protocol_prepared,
            )
        ):
            raise ValueError("Gate 2 freeze requires every readiness control")
        if self.measured_execution_permitted:
            raise ValueError("Gate 2 does not permit measured execution")
        return self


class EpisodeAssetSummary(BaseModel):
    """Safe CLI summary for diagnostic episode build or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str
    functional_episode_count: int
    development_episode_count: int
    held_out_episode_count: int
    runtime_episode_count: int
    rejected_proposal_count: int
    gate_2_passed: bool
    measured_execution_permitted: bool
    validation_status: str
