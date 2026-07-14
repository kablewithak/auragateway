"""Typed experiment contracts for the controlled local A/B/C extension."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.local_abc.errors import LocalABCFailureCode

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{2,199}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$")


class LocalABCContract(BaseModel):
    """Immutable, strict contract with deterministic serialization support."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        """Return stable JSON suitable for hashing and evidence manifests."""

        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    def fingerprint(self) -> str:
        """Return the lowercase SHA-256 digest of canonical JSON."""

        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class WorkerId(StrEnum):
    """Fixed worker identities for the two-worker causal experiment."""

    WORKER_1 = "worker_1"
    WORKER_2 = "worker_2"


class ConditionId(StrEnum):
    """The three controlled experimental conditions."""

    A = "A"
    B = "B"
    C = "C"


class PrefixPolicy(StrEnum):
    """Prompt-prefix construction policy used by a condition."""

    CACHE_HOSTILE = "cache_hostile"
    DETERMINISTIC_EXACT = "deterministic_exact"


class CacheObservationState(StrEnum):
    """Explicit cache-observation semantics; missing never becomes zero."""

    NOT_EXPOSED = "not_exposed"
    NOT_OBSERVED = "not_observed"
    ZERO = "zero"
    POSITIVE = "positive"
    INVALID = "invalid"


class TrajectoryTerminalState(StrEnum):
    """Execution-level terminal state for one attempted trajectory."""

    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class RunTerminalClassification(StrEnum):
    """Ledger classification separating task completion from comparison eligibility."""

    COMPLETED_ELIGIBLE = "completed_eligible"
    COMPLETED_INELIGIBLE = "completed_ineligible"
    FAILED_RETAINED = "failed_retained"
    INTERRUPTED_RETAINED = "interrupted_retained"
    TASK_COMPLETED_BUT_COMPARISON_INELIGIBLE = "task_completed_but_comparison_ineligible"


class ModelIdentity(LocalABCContract):
    """Immutable model identity captured from the qualified runtime."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    repository: str
    revision: str = Field(min_length=7, max_length=200)
    config_sha256: str

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        if _REPOSITORY_PATTERN.fullmatch(value) is None:
            raise ValueError("model repository contains unsupported characters")
        return value

    @field_validator("config_sha256")
    @classmethod
    def validate_config_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("model config digest must be lowercase SHA-256")
        return value


class TokenizerIdentity(LocalABCContract):
    """Immutable tokenizer identity captured from the qualified runtime."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    repository: str
    revision: str = Field(min_length=7, max_length=200)
    config_sha256: str

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        if _REPOSITORY_PATTERN.fullmatch(value) is None:
            raise ValueError("tokenizer repository contains unsupported characters")
        return value

    @field_validator("config_sha256")
    @classmethod
    def validate_config_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("tokenizer config digest must be lowercase SHA-256")
        return value


class WorkerIdentity(LocalABCContract):
    """Observed identity and fixed topology for one local vLLM worker."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    worker_id: WorkerId
    gpu_index: int = Field(ge=0, le=1)
    port: int = Field(ge=1024, le=65535)
    runtime_name: Literal["vllm"] = "vllm"
    runtime_version: str
    model: ModelIdentity
    tokenizer: TokenizerIdentity

    @field_validator("runtime_version")
    @classmethod
    def validate_runtime_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime_version must be a stable version identifier")
        return value

    @model_validator(mode="after")
    def validate_fixed_topology(self) -> Self:
        expected = {
            WorkerId.WORKER_1: (0, 8001),
            WorkerId.WORKER_2: (1, 8002),
        }
        expected_gpu, expected_port = expected[self.worker_id]
        if self.gpu_index != expected_gpu or self.port != expected_port:
            raise ValueError("worker identity must match the frozen GPU and port topology")
        return self


class EnvironmentManifest(LocalABCContract):
    """Qualified two-worker environment with zero-spend and privacy invariants."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: str
    captured_at: datetime
    python_version: str
    cuda_version: str
    gpu_type: str = Field(min_length=2, max_length=120)
    workers: tuple[WorkerIdentity, WorkerIdentity]
    external_spend: Decimal = Decimal("0")
    customer_data_used: Literal[False] = False
    paid_fallback_permitted: Literal[False] = False

    @field_validator("manifest_id")
    @classmethod
    def validate_manifest_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("manifest_id must use stable lowercase characters")
        return value

    @field_validator("captured_at")
    @classmethod
    def validate_captured_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        return value

    @field_validator("python_version", "cuda_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("environment versions must use stable version identifiers")
        return value

    @field_validator("external_spend")
    @classmethod
    def validate_zero_spend(cls, value: Decimal) -> Decimal:
        if value != Decimal("0"):
            raise ValueError("external_spend must remain zero")
        return value

    @model_validator(mode="after")
    def validate_worker_parity(self) -> Self:
        workers_by_id = {worker.worker_id: worker for worker in self.workers}
        if set(workers_by_id) != set(WorkerId):
            raise ValueError("environment requires exactly worker_1 and worker_2")
        if len({worker.gpu_index for worker in self.workers}) != 2:
            raise ValueError("workers must use independent GPUs")
        if len({worker.port for worker in self.workers}) != 2:
            raise ValueError("workers must use distinct ports")

        first, second = self.workers
        if first.model != second.model:
            raise ValueError(LocalABCFailureCode.MODEL_IDENTITY_MISMATCH)
        if first.tokenizer != second.tokenizer:
            raise ValueError(LocalABCFailureCode.TOKENIZER_IDENTITY_MISMATCH)
        if first.runtime_version != second.runtime_version:
            raise ValueError("workers must use the same vLLM version")
        return self


class RouteSchedule(LocalABCContract):
    """Deterministic two-turn destination schedule."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    workers: tuple[WorkerId, WorkerId]


class PrefixIdentity(LocalABCContract):
    """Metadata-only identity for a canonical tokenized prefix."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    serializer_version: str
    token_hash: str
    token_count: int = Field(gt=0)
    tokenizer_fingerprint: str

    @field_validator("serializer_version")
    @classmethod
    def validate_serializer_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("serializer_version must be a stable version identifier")
        return value

    @field_validator("token_hash", "tokenizer_fingerprint")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("prefix identities require lowercase SHA-256 digests")
        return value


class ConditionDefinition(LocalABCContract):
    """One frozen condition in the A/B/C causal constitution."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    condition_id: ConditionId
    prefix_policy: PrefixPolicy
    route_schedule: RouteSchedule
    prefix_identity: PrefixIdentity

    @model_validator(mode="after")
    def validate_condition_shape(self) -> Self:
        expected = {
            ConditionId.A: (
                PrefixPolicy.CACHE_HOSTILE,
                (WorkerId.WORKER_1, WorkerId.WORKER_2),
            ),
            ConditionId.B: (
                PrefixPolicy.DETERMINISTIC_EXACT,
                (WorkerId.WORKER_1, WorkerId.WORKER_2),
            ),
            ConditionId.C: (
                PrefixPolicy.DETERMINISTIC_EXACT,
                (WorkerId.WORKER_1, WorkerId.WORKER_1),
            ),
        }
        expected_policy, expected_workers = expected[self.condition_id]
        if self.prefix_policy is not expected_policy:
            raise ValueError("condition prefix policy violates the frozen A/B/C constitution")
        if self.route_schedule.workers != expected_workers:
            raise ValueError("condition route schedule violates the frozen A/B/C constitution")
        return self


class CacheObservation(LocalABCContract):
    """Normalized cache evidence with explicit missing, zero, and invalid states."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    state: CacheObservationState
    raw_metric_name: str | None = Field(default=None, min_length=1, max_length=200)
    observed_cached_prefix_tokens: int | None = Field(default=None, ge=0)
    reason_code: LocalABCFailureCode | None = None

    @model_validator(mode="after")
    def validate_cache_semantics(self) -> Self:
        value = self.observed_cached_prefix_tokens
        if self.state is CacheObservationState.NOT_EXPOSED:
            if self.raw_metric_name is not None or value is not None:
                raise ValueError("not_exposed cache evidence cannot contain a metric or value")
            if self.reason_code is not LocalABCFailureCode.TELEMETRY_NOT_EXPOSED:
                raise ValueError("not_exposed cache evidence requires TELEMETRY_NOT_EXPOSED")
            return self

        if self.state is CacheObservationState.NOT_OBSERVED:
            if self.raw_metric_name is None or value is not None:
                raise ValueError("not_observed requires a metric name and no numeric value")
            if self.reason_code is not LocalABCFailureCode.TELEMETRY_NOT_OBSERVED:
                raise ValueError("not_observed cache evidence requires TELEMETRY_NOT_OBSERVED")
            return self

        if self.state is CacheObservationState.ZERO:
            if self.raw_metric_name is None or value != 0 or self.reason_code is not None:
                raise ValueError("zero cache evidence requires an observed metric value of zero")
            return self

        if self.state is CacheObservationState.POSITIVE:
            if self.raw_metric_name is None or value is None or value <= 0:
                raise ValueError("positive cache evidence requires an observed positive value")
            if self.reason_code is not None:
                raise ValueError("positive cache evidence cannot contain a failure reason")
            return self

        if value is not None:
            raise ValueError("invalid cache evidence cannot retain a normalized numeric value")
        if self.reason_code not in {
            LocalABCFailureCode.TELEMETRY_AMBIGUOUS,
            LocalABCFailureCode.TELEMETRY_INVALID,
        }:
            raise ValueError("invalid cache evidence requires an ambiguity or invalidity reason")
        return self


class TelemetryObservation(LocalABCContract):
    """One worker-scoped normalized telemetry observation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    observation_id: str
    worker_id: WorkerId
    collected_at: datetime
    metric_mapping_version: str
    cache: CacheObservation
    eligible_shared_prefix_tokens: int = Field(ge=0)
    newly_computed_prefill_tokens: int | None = Field(default=None, ge=0)
    prefill_duration_ms: float | None = Field(default=None, ge=0)
    time_to_first_token_ms: float | None = Field(default=None, ge=0)
    end_to_end_latency_ms: float | None = Field(default=None, ge=0)

    @field_validator("observation_id")
    @classmethod
    def validate_observation_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("observation_id must use stable lowercase characters")
        return value

    @field_validator("collected_at")
    @classmethod
    def validate_collected_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("collected_at must be timezone-aware")
        return value

    @field_validator("metric_mapping_version")
    @classmethod
    def validate_metric_mapping_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("metric mapping version must be stable")
        return value

    @model_validator(mode="after")
    def validate_cache_bounds(self) -> Self:
        cached = self.cache.observed_cached_prefix_tokens
        if cached is not None and cached > self.eligible_shared_prefix_tokens:
            raise ValueError("cached prefix tokens cannot exceed eligible shared prefix tokens")
        return self


class TrajectoryRecord(LocalABCContract):
    """Immutable metadata-only record for one attempted two-turn trajectory."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    trajectory_id: str
    trace_id: UUID
    case_id: str
    replication_id: str
    condition_id: ConditionId
    intended_route: RouteSchedule
    realized_route: tuple[WorkerId, ...] = Field(min_length=1, max_length=2)
    terminal_state: TrajectoryTerminalState
    task_completed: bool
    fallback_used: bool = False
    telemetry: tuple[TelemetryObservation, ...] = Field(max_length=2)
    failure_codes: tuple[LocalABCFailureCode, ...] = ()

    @field_validator("trajectory_id", "case_id", "replication_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trajectory identifiers must use stable lowercase characters")
        return value

    @field_validator("failure_codes")
    @classmethod
    def validate_failure_codes(
        cls, value: tuple[LocalABCFailureCode, ...]
    ) -> tuple[LocalABCFailureCode, ...]:
        if len(value) != len(set(value)):
            raise ValueError("trajectory failure codes must be unique")
        return value

    @model_validator(mode="after")
    def validate_trajectory(self) -> Self:
        if self.terminal_state is TrajectoryTerminalState.COMPLETED:
            if not self.task_completed:
                raise ValueError("completed trajectories must complete the task")
            if len(self.realized_route) != 2 or len(self.telemetry) != 2:
                raise ValueError(
                    "completed trajectories require two realized turns and observations"
                )
        elif self.task_completed:
            raise ValueError("failed or interrupted trajectories cannot claim task completion")

        intended_prefix = self.intended_route.workers[: len(self.realized_route)]
        route_mismatch = self.realized_route != intended_prefix
        if route_mismatch != self.fallback_used:
            raise ValueError("fallback_used must exactly match route realization divergence")
        if self.fallback_used and (
            LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH not in self.failure_codes
        ):
            raise ValueError("fallback trajectories require ROUTE_REALIZATION_MISMATCH")

        observed_workers = tuple(observation.worker_id for observation in self.telemetry)
        if observed_workers != self.realized_route[: len(observed_workers)]:
            raise ValueError("telemetry worker identities must match the realized route")
        observation_ids = [observation.observation_id for observation in self.telemetry]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("telemetry observation IDs must be unique per trajectory")
        return self


class RunEligibility(LocalABCContract):
    """Fail-closed eligibility decision for one retained trajectory."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    trajectory_id: str
    condition_id: ConditionId
    terminal_classification: RunTerminalClassification
    task_completed: bool
    comparison_eligible: bool
    affinity_comparison_eligible: bool
    telemetry_sufficient: bool
    route_realized: bool
    fallback_used: bool
    failure_codes: tuple[LocalABCFailureCode, ...] = ()

    @field_validator("trajectory_id")
    @classmethod
    def validate_trajectory_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trajectory_id must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_eligibility(self) -> Self:
        eligible = self.terminal_classification is RunTerminalClassification.COMPLETED_ELIGIBLE
        if eligible != self.comparison_eligible:
            raise ValueError("completed_eligible must exactly match comparison_eligible")

        if self.comparison_eligible:
            if not self.task_completed or not self.telemetry_sufficient or not self.route_realized:
                raise ValueError("eligible comparisons require complete task, telemetry, and route")
            if self.fallback_used or self.failure_codes:
                raise ValueError("eligible comparisons cannot contain fallback or failures")

        if self.fallback_used and (
            self.comparison_eligible or self.affinity_comparison_eligible or self.route_realized
        ):
            raise ValueError("fallback blocks route and affinity comparison eligibility")
        if self.affinity_comparison_eligible and not self.comparison_eligible:
            raise ValueError("affinity eligibility requires overall comparison eligibility")

        if (
            self.terminal_classification
            in {
                RunTerminalClassification.FAILED_RETAINED,
                RunTerminalClassification.INTERRUPTED_RETAINED,
            }
            and self.task_completed
        ):
            raise ValueError("failed or interrupted classifications cannot complete the task")

        task_ineligible = {
            RunTerminalClassification.COMPLETED_INELIGIBLE,
            RunTerminalClassification.TASK_COMPLETED_BUT_COMPARISON_INELIGIBLE,
        }
        if self.terminal_classification in task_ineligible and not self.task_completed:
            raise ValueError("completed-ineligible classifications require task completion")

        if not self.comparison_eligible and not self.failure_codes:
            raise ValueError("ineligible trajectories require at least one failure code")
        return self


class FailureRecord(LocalABCContract):
    """Safe retained failure entry for the monotonic attempt ledger."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    failure_id: str
    trajectory_id: str
    occurred_at: datetime
    code: LocalABCFailureCode
    retryable: bool = False
    attempt_retained: Literal[True] = True
    safe_detail: str = Field(min_length=1, max_length=300)

    @field_validator("failure_id", "trajectory_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("failure identifiers must use stable lowercase characters")
        return value

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


class ExperimentManifest(LocalABCContract):
    """Frozen local A/B/C constitution and environment binding."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: str
    created_at: datetime
    environment: EnvironmentManifest
    conditions: tuple[ConditionDefinition, ConditionDefinition, ConditionDefinition]
    case_ids: tuple[str, ...] = Field(min_length=1)
    output_token_budget: int = Field(gt=0)
    decoding_config_sha256: str
    quality_rubric_version: str
    measured_execution_authorized: bool = False

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

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("experiment case IDs must be unique")
        if any(_ID_PATTERN.fullmatch(case_id) is None for case_id in value):
            raise ValueError("experiment case IDs must use stable lowercase characters")
        return value

    @field_validator("decoding_config_sha256")
    @classmethod
    def validate_decoding_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("decoding configuration digest must be lowercase SHA-256")
        return value

    @field_validator("quality_rubric_version")
    @classmethod
    def validate_quality_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("quality rubric version must be stable")
        return value

    @model_validator(mode="after")
    def validate_causal_constitution(self) -> Self:
        conditions = {condition.condition_id: condition for condition in self.conditions}
        if set(conditions) != set(ConditionId):
            raise ValueError("manifest requires exactly one definition for A, B, and C")

        condition_a = conditions[ConditionId.A]
        condition_b = conditions[ConditionId.B]
        condition_c = conditions[ConditionId.C]
        if condition_a.route_schedule != condition_b.route_schedule:
            raise ValueError("A and B must use identical route schedules")
        if condition_b.prefix_identity != condition_c.prefix_identity:
            raise ValueError(LocalABCFailureCode.PREFIX_HASH_MISMATCH)
        return self

    def condition_for(self, condition_id: ConditionId) -> ConditionDefinition:
        """Return one required condition definition."""

        return next(item for item in self.conditions if item.condition_id is condition_id)
