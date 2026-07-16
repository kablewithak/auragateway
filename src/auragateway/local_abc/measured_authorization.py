"""Typed freeze and authorization contracts for measured Local A/B/C execution."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import ConditionId, LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$")


class AuthorizationGateStatus(StrEnum):
    """Fail-closed status for one predecessor evidence gate."""

    PASSED = "passed"
    FAILED = "failed"


class AuthorizationDecision(StrEnum):
    """Explicit decision controlling measured execution."""

    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not_authorized"


class EvidenceLifecycleState(StrEnum):
    """Qualified predecessor lifecycle states accepted by this package."""

    ENVIRONMENT_QUALIFIED = "ENVIRONMENT_QUALIFIED"
    CACHE_OBSERVABILITY_QUALIFIED = "CACHE_OBSERVABILITY_QUALIFIED"
    PRESSURE_DIAGNOSTICS_COMPLETED = "PRESSURE_DIAGNOSTICS_COMPLETED"
    ROUTE_WORKER_FAULT_DIAGNOSTICS_COMPLETED = "ROUTE_WORKER_FAULT_DIAGNOSTICS_COMPLETED"


class StablePrefixContract(LocalABCContract):
    """Exact reusable prefix material frozen before measured execution."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    template_id: str
    template_version: str
    segments: tuple[str, ...] = Field(min_length=1)
    tool_contracts: tuple[str, ...] = Field(min_length=1)
    output_schema: str = Field(min_length=1)
    context_pack: str = Field(min_length=1)

    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("template_id must use stable lowercase characters")
        return value

    @field_validator("template_version")
    @classmethod
    def validate_template_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("template_version must use a stable version identifier")
        return value

    @field_validator("segments", "tool_contracts")
    @classmethod
    def validate_ordered_entries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("stable prefix entries must not be blank")
        if len(value) != len(set(value)):
            raise ValueError("stable prefix entries must not contain duplicates")
        return value

    @field_validator("output_schema", "context_pack")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("stable prefix text must not be blank")
        return value


class MeasuredTurn(LocalABCContract):
    """One synthetic volatile turn in a frozen measured case."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    turn_index: Literal[1, 2]
    user_message: str = Field(min_length=1, max_length=800)
    retrieved_evidence: tuple[str, ...] = ()
    retained_feedback: tuple[str, ...] = ()

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("user_message must not be blank")
        return value

    @field_validator("retrieved_evidence", "retained_feedback")
    @classmethod
    def validate_entries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("turn evidence and feedback entries must not be blank")
        if len(value) != len(set(value)):
            raise ValueError("turn evidence and feedback entries must be unique")
        return value


class ExpectedTurnOutput(LocalABCContract):
    """Deterministic expected output for one measured turn."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    turn_index: Literal[1, 2]
    answer: str = Field(min_length=1, max_length=120)
    confidence: Literal["high"] = "high"

    def expected_payload(self, *, case_id: str) -> dict[str, str | int]:
        """Return the exact JSON payload expected from the model."""

        return {
            "answer": self.answer,
            "case_id": case_id,
            "confidence": self.confidence,
            "turn_index": self.turn_index,
        }


class MeasuredCase(LocalABCContract):
    """One two-turn synthetic diagnostic case with exact expectations."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str
    diagnostic_axis: str = Field(min_length=3, max_length=120)
    turns: tuple[MeasuredTurn, MeasuredTurn]
    expected_outputs: tuple[ExpectedTurnOutput, ExpectedTurnOutput]

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("case_id must use stable lowercase characters")
        return value

    @field_validator("diagnostic_axis")
    @classmethod
    def validate_diagnostic_axis(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("diagnostic_axis must not be blank")
        return value

    @model_validator(mode="after")
    def validate_ordered_turns(self) -> Self:
        if tuple(turn.turn_index for turn in self.turns) != (1, 2):
            raise ValueError("measured cases require ordered turns 1 and 2")
        if tuple(item.turn_index for item in self.expected_outputs) != (1, 2):
            raise ValueError("expected outputs require ordered turns 1 and 2")
        if self.turns[0].user_message == self.turns[1].user_message:
            raise ValueError("measured turns must contain distinct volatile inputs")
        return self


class QualityRubric(LocalABCContract):
    """Deterministic quality scoring without an LLM judge."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    rubric_version: str
    required_keys: tuple[str, ...]
    exact_key_set_required: Literal[True] = True
    exact_answer_match_required: Literal[True] = True
    exact_case_id_required: Literal[True] = True
    exact_turn_index_required: Literal[True] = True
    confidence_value: Literal["high"] = "high"
    extra_text_permitted: Literal[False] = False

    @field_validator("rubric_version")
    @classmethod
    def validate_rubric_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("rubric_version must use a stable version identifier")
        return value

    @field_validator("required_keys")
    @classmethod
    def validate_required_keys(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = ("answer", "case_id", "confidence", "turn_index")
        if value != expected:
            raise ValueError("quality rubric must freeze the exact output key order")
        return value


class MeasuredCaseManifest(LocalABCContract):
    """Frozen synthetic case set and deterministic scoring boundary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: str
    created_at: datetime
    stable_prefix: StablePrefixContract
    quality_rubric: QualityRubric
    cases: tuple[MeasuredCase, ...] = Field(min_length=6)
    customer_data_used: Literal[False] = False
    private_client_artifacts_used: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False

    @field_validator("manifest_id")
    @classmethod
    def validate_manifest_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest_id must use stable lowercase characters")
        return value

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_case_set(self) -> Self:
        case_ids = tuple(case.case_id for case in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("measured case IDs must be unique")
        axes = tuple(case.diagnostic_axis for case in self.cases)
        if len(axes) != len(set(axes)):
            raise ValueError("diagnostic axes must be unique across the case set")
        return self


class EvidenceBinding(LocalABCContract):
    """Hash-bound predecessor evidence required for authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    evidence_id: str
    lifecycle_state: EvidenceLifecycleState
    report_sha256: str
    archive_sha256: str
    gate_status: AuthorizationGateStatus

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence_id must use stable lowercase characters")
        return value

    @field_validator("report_sha256", "archive_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence digests must be lowercase SHA-256")
        return value


class RuntimeBinding(LocalABCContract):
    """Exact runtime and worker topology authorized for the measured run."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    kaggle_username: Literal["kabomolefe"] = "kabomolefe"
    gpu_type: Literal["Tesla T4"] = "Tesla T4"
    gpu_count: Literal[2] = 2
    cuda_version: Literal["12.9"] = "12.9"
    vllm_version: Literal["0.25.1"] = "0.25.1"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_manifest_sha256: str
    worker_1_gpu_index: Literal[0] = 0
    worker_1_port: Literal[8001] = 8001
    worker_2_gpu_index: Literal[1] = 1
    worker_2_port: Literal[8002] = 8002

    @field_validator("model_manifest_sha256")
    @classmethod
    def validate_model_manifest_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("model manifest digest must be lowercase SHA-256")
        return value


class DecodingPolicy(LocalABCContract):
    """Deterministic decoding configuration for all measured trajectories."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    temperature: Decimal = Decimal("0")
    top_p: Decimal = Decimal("1")
    seed: Literal[7] = 7
    max_output_tokens: Literal[64] = 64
    n: Literal[1] = 1
    stream: Literal[False] = False

    @model_validator(mode="after")
    def validate_determinism(self) -> Self:
        if self.temperature != Decimal("0"):
            raise ValueError("measured decoding requires temperature=0")
        if self.top_p != Decimal("1"):
            raise ValueError("measured decoding requires top_p=1")
        return self


class ConditionOrderPlan(LocalABCContract):
    """Three-replication Latin-square condition order."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    replications: tuple[
        tuple[ConditionId, ConditionId, ConditionId],
        tuple[ConditionId, ConditionId, ConditionId],
        tuple[ConditionId, ConditionId, ConditionId],
    ]
    full_worker_restart_before_each_trajectory: Literal[True] = True

    @model_validator(mode="after")
    def validate_latin_square(self) -> Self:
        expected = (
            (ConditionId.A, ConditionId.B, ConditionId.C),
            (ConditionId.B, ConditionId.C, ConditionId.A),
            (ConditionId.C, ConditionId.A, ConditionId.B),
        )
        if self.replications != expected:
            raise ValueError("condition order must match the frozen Latin square")
        return self


class AbortPolicy(LocalABCContract):
    """Fail-closed abort conditions for the measured notebook."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    max_total_trajectory_failures: Literal[3] = 3
    max_consecutive_trajectory_failures: Literal[2] = 2
    max_route_realization_mismatches: Literal[0] = 0
    max_invalid_telemetry_records: Literal[0] = 0
    stop_on_model_identity_mismatch: Literal[True] = True
    stop_on_tokenizer_identity_mismatch: Literal[True] = True
    stop_on_privacy_scan_failure: Literal[True] = True
    stop_on_nonzero_external_spend: Literal[True] = True
    stop_on_unclosed_worker_port: Literal[True] = True


class AnalysisPlan(LocalABCContract):
    """Frozen estimands, pairing rules, and minimum evidence requirements."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    primary_contrast: Literal["C_minus_B_turn2_cache_affinity"] = "C_minus_B_turn2_cache_affinity"
    negative_control_contrast: Literal["B_minus_A_turn2_no_affinity"] = (
        "B_minus_A_turn2_no_affinity"
    )
    pairing_key: Literal["case_id+replication_id"] = "case_id+replication_id"
    aggregation: Literal["paired_median_and_pairwise_win_rate"] = (
        "paired_median_and_pairwise_win_rate"
    )
    primary_metrics: tuple[str, ...]
    quality_metrics: tuple[str, ...]
    minimum_eligible_pairs_per_contrast: Literal[21] = 21
    llm_judge_permitted: Literal[False] = False

    @field_validator("primary_metrics")
    @classmethod
    def validate_primary_metrics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = (
            "turn2_cached_prefix_tokens",
            "turn2_newly_computed_prefill_tokens",
            "turn2_prefill_duration_ms",
            "turn2_time_to_first_token_ms",
            "turn2_end_to_end_latency_ms",
        )
        if value != expected:
            raise ValueError("primary metrics must match the frozen measured plan")
        return value

    @field_validator("quality_metrics")
    @classmethod
    def validate_quality_metrics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = (
            "json_parse_success",
            "exact_key_set_match",
            "exact_answer_match",
            "exact_case_id_match",
            "exact_turn_index_match",
            "no_extra_text",
        )
        if value != expected:
            raise ValueError("quality metrics must match the frozen rubric")
        return value


class MeasuredExecutionAuthorization(LocalABCContract):
    """Explicit authorization bound to evidence, cases, runtime, and analysis."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str
    issued_at: datetime
    decision: AuthorizationDecision
    measured_execution_authorized: bool
    case_manifest_sha256: str
    case_count: int = Field(gt=0)
    replication_count: Literal[3] = 3
    condition_count: Literal[3] = 3
    planned_trajectory_count: int = Field(gt=0)
    planned_request_count: int = Field(gt=0)
    runtime: RuntimeBinding
    evidence: tuple[EvidenceBinding, EvidenceBinding, EvidenceBinding, EvidenceBinding]
    decoding: DecodingPolicy
    condition_order: ConditionOrderPlan
    abort_policy: AbortPolicy
    analysis_plan: AnalysisPlan
    external_spend: Decimal = Decimal("0")
    customer_data_used: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False

    @field_validator("authorization_id")
    @classmethod
    def validate_authorization_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization_id must use stable lowercase characters")
        return value

    @field_validator("issued_at")
    @classmethod
    def validate_issued_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value

    @field_validator("case_manifest_sha256")
    @classmethod
    def validate_case_manifest_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("case manifest digest must be lowercase SHA-256")
        return value

    @field_validator("external_spend")
    @classmethod
    def validate_zero_spend(cls, value: Decimal) -> Decimal:
        if value != Decimal("0"):
            raise ValueError("external_spend must remain zero")
        return value

    @model_validator(mode="after")
    def validate_authorization(self) -> Self:
        required_states = {
            EvidenceLifecycleState.ENVIRONMENT_QUALIFIED,
            EvidenceLifecycleState.CACHE_OBSERVABILITY_QUALIFIED,
            EvidenceLifecycleState.PRESSURE_DIAGNOSTICS_COMPLETED,
            EvidenceLifecycleState.ROUTE_WORKER_FAULT_DIAGNOSTICS_COMPLETED,
        }
        observed_states = {item.lifecycle_state for item in self.evidence}
        if observed_states != required_states:
            raise ValueError("authorization requires all four qualified predecessor states")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("authorization evidence IDs must be unique")

        all_gates_passed = all(
            item.gate_status is AuthorizationGateStatus.PASSED for item in self.evidence
        )
        decision_authorized = self.decision is AuthorizationDecision.AUTHORIZED
        if self.measured_execution_authorized != decision_authorized:
            raise ValueError("authorization decision must match measured_execution_authorized")
        if decision_authorized and not all_gates_passed:
            raise ValueError("measured execution cannot be authorized with a failed gate")

        expected_trajectories = self.case_count * self.replication_count * self.condition_count
        if self.planned_trajectory_count != expected_trajectories:
            raise ValueError("planned trajectory count does not match the frozen design")
        if self.planned_request_count != expected_trajectories * 2:
            raise ValueError("planned request count must equal two turns per trajectory")
        return self


class MeasuredAuthorizationPackage(LocalABCContract):
    """Cross-file validation boundary for the manifest and authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    case_manifest: MeasuredCaseManifest
    authorization: MeasuredExecutionAuthorization

    @model_validator(mode="after")
    def validate_package_binding(self) -> Self:
        if self.case_manifest.fingerprint() != self.authorization.case_manifest_sha256:
            raise ValueError("authorization case manifest digest does not match manifest bytes")
        if len(self.case_manifest.cases) != self.authorization.case_count:
            raise ValueError("authorization case count does not match the case manifest")
        return self


def load_measured_authorization_package(
    *,
    case_manifest_path: Path,
    authorization_path: Path,
) -> MeasuredAuthorizationPackage:
    """Load and cross-validate the two frozen JSON authorization artifacts."""

    case_payload = json.loads(case_manifest_path.read_text(encoding="utf-8"))
    authorization_payload = json.loads(authorization_path.read_text(encoding="utf-8"))
    return MeasuredAuthorizationPackage(
        case_manifest=MeasuredCaseManifest.model_validate(case_payload),
        authorization=MeasuredExecutionAuthorization.model_validate(authorization_payload),
    )
