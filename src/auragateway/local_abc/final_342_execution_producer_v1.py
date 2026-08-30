"""Transaction-bound evidence producer for the final 342-trajectory execution.

This module performs no model, GPU, Kaggle, or authorization work on import. It composes
accepted runtime mechanics while adding final-run retry, trace binding, typed measurement,
monotonic evidence persistence, teardown, cleanup, and public bundle production.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol, Self, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

PRODUCER_ID = "auragateway-final-342-execution-producer-v1"
SOURCE_MAIN_COMMIT = "0c0cb3c7cef5125c3a66e2bf64b9f8ce62cf48de"

EXPECTED_TRAJECTORY_COUNT = 342
EXPECTED_TURN_COUNT = 1368
EXPECTED_MAXIMUM_REQUEST_ATTEMPTS = 2736

CONNECT_TIMEOUT_SECONDS = 10
FIRST_OUTPUT_TIMEOUT_SECONDS = 45
TOTAL_REQUEST_TIMEOUT_SECONDS = 120
RETRY_BACKOFF_SECONDS = 2
MAX_RESPONSE_BYTES = 2 * 1024 * 1024

FINAL_CORE_PATH = Path("src/auragateway/local_abc/final_342_non_authorizing_runtime_core_v1.py")
P5_P6_RUNTIME_PATH = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)
V2_RUNTIME_PATH = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_transaction_bound_runtime_v1.py"
)
V2_REQUEST_ADAPTER_PATH = Path(
    "src/auragateway/local_abc/"
    "measured_abc_variance_pilot_v2_accepted_runtime_request_adapter_v1.py"
)
CLOSURE_RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_execution_producer_closure_v1.json"
)
ARCHITECTURE_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_runtime_requalification_architecture_v1.json"
)
PREFLIGHT_FINGERPRINTS_PATH = Path("data/evals/benchmark/preflight-v3/condition_fingerprints.json")

BOUND_PREDECESSOR_PATHS = (
    FINAL_CORE_PATH,
    P5_P6_RUNTIME_PATH,
    V2_RUNTIME_PATH,
    V2_REQUEST_ADAPTER_PATH,
    CLOSURE_RECORD_PATH,
    ARCHITECTURE_PATH,
    PREFLIGHT_FINGERPRINTS_PATH,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ProducerError(RuntimeError):
    """Fail-closed metadata-safe producer failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: Path | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProducerPhase(StrEnum):
    TRANSACTION_ADMISSION = "transaction_admission"
    REQUEST_ATTEMPT_RESERVATION = "request_attempt_reservation"
    TRANSPORT_OUTCOME = "transport_outcome"
    TELEMETRY_AND_OUTPUT_ADMISSION = "telemetry_and_output_admission"
    STATE_MUTATION_DECISION = "state_mutation_decision"
    TRAJECTORY_TERMINAL_STATE = "trajectory_terminal_state"
    WORKER_TEARDOWN = "worker_teardown"
    SCRATCH_CLEANUP = "scratch_cleanup"
    EVIDENCE_PACKAGING = "evidence_packaging"
    AUTHORIZATION_TERMINALIZATION = "authorization_terminalization"


class TrajectoryTerminalState(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class SourceBinding(FrozenModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanBinding(FrozenModel):
    planned_order_index: int = Field(ge=0, lt=EXPECTED_TRAJECTORY_COUNT)
    run_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    comparison_pair_id: str = Field(min_length=1)
    workload: core.WorkloadId
    condition_id: core.ConditionId
    route_schedule_id: core.RouteScheduleId
    cache_namespace_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RuntimeCompositionBinding(FrozenModel):
    worker_lifecycle_source: Literal[
        "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
    ] = "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
    worker_class_symbol: Literal["Worker"] = "Worker"

    request_materialization_source: Literal[
        "src/auragateway/local_abc/"
        "measured_abc_variance_pilot_v2_accepted_runtime_request_adapter_v1.py"
    ] = (
        "src/auragateway/local_abc/"
        "measured_abc_variance_pilot_v2_accepted_runtime_request_adapter_v1.py"
    )
    request_payload_symbol: Literal["build_request_payload"] = "build_request_payload"
    tokenizer_sidecar_symbol: Literal["AcceptedTokenizerSidecar"] = "AcceptedTokenizerSidecar"
    one_shot_v2_adapter_permitted: Literal[False] = False

    evidence_mechanics_source: Literal[
        "src/auragateway/local_abc/measured_abc_variance_pilot_v2_transaction_bound_runtime_v1.py"
    ] = "src/auragateway/local_abc/measured_abc_variance_pilot_v2_transaction_bound_runtime_v1.py"
    atomic_evidence_pattern_reused: Literal[True] = True
    checkpoint_reconciliation_pattern_reused: Literal[True] = True
    bundle_manifest_pattern_reused: Literal[True] = True

    execution_backend: Literal["local_vllm"] = "local_vllm"
    served_model_alias: Literal["local-qwen2.5-0.5b-instruct"] = "local-qwen2.5-0.5b-instruct"
    exact_model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    exact_model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    vllm_distribution_version: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    transport_endpoint: Literal["/v1/chat/completions"] = "/v1/chat/completions"

    legacy_provider_model_alias_field_retained: Literal[True] = True
    legacy_provider_model_alias_implies_provider_authority: Literal[False] = False
    monetary_cost_comparison_in_scope: Literal[False] = False
    external_spend_ceiling: Literal[0] = 0


class ProducerEvent(FrozenModel):
    sequence: int = Field(ge=1)
    phase: ProducerPhase
    run_id: str | None = None
    trace_id: str | None = None
    turn_index: int | None = Field(default=None, ge=1, le=4)
    attempt_index: int | None = Field(default=None, ge=1, le=2)


class WorkerStartupRecord(FrozenModel):
    worker_id: core.WorkerId
    worker_generation: Literal[1] = 1
    gpu_index: Literal[0, 1]
    port: Literal[8001, 8002]
    runtime_model_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    backend_log_marker_observed: Literal[True] = True
    argv_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_topology(self) -> Self:
        expected = {
            core.WorkerId.WORKER_1: (0, 8001),
            core.WorkerId.WORKER_2: (1, 8002),
        }
        if (self.gpu_index, self.port) != expected[self.worker_id]:
            raise ValueError("worker startup record violates frozen topology")
        return self


class AttemptReservation(FrozenModel):
    global_attempt_sequence: int = Field(ge=1, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)
    run_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    turn_index: int = Field(ge=1, le=4)
    attempt_index: int = Field(ge=1, le=2)
    logical_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    route_identity: core.CacheResidencyIdentity
    retry_backoff_seconds: int = Field(ge=0, le=RETRY_BACKOFF_SECONDS)
    persisted_before_transport: Literal[True] = True

    @model_validator(mode="after")
    def validate_retry_shape(self) -> Self:
        expected = 0 if self.attempt_index == 1 else RETRY_BACKOFF_SECONDS
        if self.retry_backoff_seconds != expected:
            raise ValueError("attempt reservation retry backoff is inconsistent")
        return self


class TransportOutcomeRecord(FrozenModel):
    global_attempt_sequence: int = Field(ge=1, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)
    outcome: core.AttemptOutcome
    retryable: bool
    http_completed: bool
    http_status: int | None = Field(default=None, ge=100, le=599)
    response_sha256: str | None = None
    error_code: str | None = Field(default=None, min_length=3, max_length=120)
    safe_message: str | None = Field(default=None, min_length=1, max_length=240)
    raw_request_retained: Literal[False] = False
    raw_response_retained: Literal[False] = False

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> Self:
        if (
            self.response_sha256 is not None
            and _SHA256_PATTERN.fullmatch(self.response_sha256) is None
        ):
            raise ValueError("response digest must be lowercase SHA-256")

        if self.http_completed:
            if self.http_status is None or self.response_sha256 is None:
                raise ValueError("completed HTTP requires status and response digest")
        elif self.http_status is not None:
            raise ValueError("incomplete HTTP cannot claim status")

        if self.outcome is core.AttemptOutcome.SUCCEEDED:
            if not self.http_completed or self.http_status != 200:
                raise ValueError("successful transport requires completed HTTP 200")
            if self.retryable:
                raise ValueError("successful transport cannot be retryable")
            if self.error_code is not None or self.safe_message is not None:
                raise ValueError("successful transport cannot carry failure detail")

        if self.outcome is core.AttemptOutcome.NO_RESPONSE and (
            self.http_completed or self.response_sha256 is not None
        ):
            raise ValueError("no-response cannot claim completed response evidence")

        if self.outcome is core.AttemptOutcome.AMBIGUOUS and self.retryable:
            raise ValueError("ambiguous transport cannot be retryable")

        if self.outcome is not core.AttemptOutcome.SUCCEEDED and (
            self.error_code is None or self.safe_message is None
        ):
            raise ValueError("failed transport requires metadata-safe failure evidence")

        return self


class TurnMeasurementRecord(FrozenModel):
    global_attempt_sequence: int = Field(ge=1, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)
    run_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    turn_index: int = Field(ge=1, le=4)

    trace_identity: core.RuntimeTraceIdentity
    route_identity: core.CacheResidencyIdentity
    warm_evidence: core.WarmTurnEvidence
    warm_decision: core.WarmEligibilityDecision

    prompt_token_count: int = Field(ge=0)
    server_usage_prompt_tokens: int = Field(ge=0)
    cached_prefix_tokens: int | None = Field(default=None, ge=0)
    newly_computed_prefill_tokens: int | None = Field(default=None, ge=0)
    prefill_duration_ms: float | None = Field(default=None, ge=0)
    time_to_first_token_ms: float | None = Field(default=None, ge=0)
    end_to_end_latency_ms: float | None = Field(default=None, ge=0)

    finish_reason: str | None = None
    output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    raw_provider_payload_retained: Literal[False] = False

    @model_validator(mode="after")
    def validate_measurement(self) -> Self:
        if self.prompt_token_count != self.server_usage_prompt_tokens:
            raise ValueError("pre-send and server prompt-token counts differ")
        if self.trace_identity.run_id != self.run_id:
            raise ValueError("measurement run identity differs from trace binding")
        if self.trace_identity.trace_id != self.trace_id:
            raise ValueError("measurement trace identity differs from trace binding")
        if self.warm_evidence.turn_index != self.turn_index:
            raise ValueError("warm evidence turn index differs from measurement")
        if self.warm_evidence.residency_identity != self.route_identity:
            raise ValueError("warm evidence route differs from measurement route")
        return self


class AdmissionRecord(FrozenModel):
    global_attempt_sequence: int = Field(ge=1, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)
    evidence: core.TurnAdmissionEvidence


class StateMutationRecord(FrozenModel):
    global_attempt_sequence: int = Field(ge=1, le=EXPECTED_MAXIMUM_REQUEST_ATTEMPTS)
    decision: core.TurnCommitDecision


class TrajectoryTerminalRecord(FrozenModel):
    run_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    terminal_state: TrajectoryTerminalState
    scheduled_turn_count: Literal[4] = 4
    attempted_request_count: int = Field(ge=0, le=8)
    committed_turn_count: int = Field(ge=0, le=4)
    failure_code: str | None = Field(default=None, min_length=3, max_length=120)

    @model_validator(mode="after")
    def validate_terminal_shape(self) -> Self:
        if self.terminal_state is TrajectoryTerminalState.COMPLETED:
            if self.committed_turn_count != 4:
                raise ValueError("completed trajectory must commit four turns")
            if self.failure_code is not None:
                raise ValueError("completed trajectory cannot carry failure")
        if self.terminal_state is TrajectoryTerminalState.FAILED and self.failure_code is None:
            raise ValueError("failed trajectory requires failure code")
        return self


class WorkerTeardownRecord(FrozenModel):
    worker_id: core.WorkerId
    worker_generation: int = Field(ge=1)
    status: Literal["PASSED", "NOT_STARTED", "FAILED"]
    process_tree_absent: bool | None = None
    gpu_processes_absent: bool | None = None
    port_closed: bool | None = None
    memory_returned: bool | None = None
    safe_failure_code: str | None = Field(default=None, min_length=3, max_length=120)

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        if self.status == "PASSED":
            checks = (
                self.process_tree_absent,
                self.gpu_processes_absent,
                self.port_closed,
                self.memory_returned,
            )
            if checks != (True, True, True, True):
                raise ValueError("passed teardown requires all terminal checks")
            if self.safe_failure_code is not None:
                raise ValueError("passed teardown cannot carry failure")
        if self.status == "FAILED" and self.safe_failure_code is None:
            raise ValueError("failed teardown requires failure code")
        return self


class ScratchCleanupRecord(FrozenModel):
    status: Literal["PASSED", "FAILED"]
    scratch_absent: bool
    safe_failure_code: str | None = Field(default=None, min_length=3, max_length=120)

    @model_validator(mode="after")
    def validate_cleanup(self) -> Self:
        if self.status == "PASSED":
            if not self.scratch_absent:
                raise ValueError("passed cleanup requires absent scratch")
            if self.safe_failure_code is not None:
                raise ValueError("passed cleanup cannot carry failure")
        if self.status == "FAILED" and self.safe_failure_code is None:
            raise ValueError("failed cleanup requires failure code")
        return self


class EvidenceBundleReceipt(FrozenModel):
    bundle_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    member_count: int = Field(ge=1)
    raw_prompts_included: Literal[False] = False
    raw_outputs_included: Literal[False] = False
    raw_provider_payloads_included: Literal[False] = False
    credentials_included: Literal[False] = False


class ProducerState(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    producer_id: Literal["auragateway-final-342-execution-producer-v1"] = (
        "auragateway-final-342-execution-producer-v1"
    )
    source_main_commit: Literal["0c0cb3c7cef5125c3a66e2bf64b9f8ce62cf48de"] = (
        "0c0cb3c7cef5125c3a66e2bf64b9f8ce62cf48de"
    )

    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_execution_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    source_bindings: tuple[SourceBinding, ...]
    runtime_composition: RuntimeCompositionBinding
    plan_bindings: tuple[PlanBinding, ...]
    trace_bindings: tuple[core.RuntimeTraceIdentity, ...]

    worker_startups: tuple[WorkerStartupRecord, ...] = ()
    request_counters: core.RequestCounters
    failure_state: core.FailureState

    events: tuple[ProducerEvent, ...] = ()
    attempt_reservations: tuple[AttemptReservation, ...] = ()
    transport_outcomes: tuple[TransportOutcomeRecord, ...] = ()
    measurements: tuple[TurnMeasurementRecord, ...] = ()
    admissions: tuple[AdmissionRecord, ...] = ()
    state_mutations: tuple[StateMutationRecord, ...] = ()
    trajectory_terminals: tuple[TrajectoryTerminalRecord, ...] = ()
    worker_teardowns: tuple[WorkerTeardownRecord, ...] = ()
    scratch_cleanup: ScratchCleanupRecord | None = None
    evidence_bundle: EvidenceBundleReceipt | None = None

    complete_offline_producer_rehearsal_established: Literal[False] = False
    manifest_freeze_permitted: Literal[False] = False
    execution_manifest_frozen: Literal[False] = False
    final_measured_abc_execution_authorized_by_producer: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    monetary_cost_comparison_in_scope: Literal[False] = False
    external_spend: Literal[0] = 0
    raw_prompts_in_public_evidence: Literal[False] = False
    raw_outputs_in_public_evidence: Literal[False] = False
    raw_provider_payloads_in_public_evidence: Literal[False] = False

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.final_execution_manifest_sha256 == core.EXPECTED_PLANNING_MANIFEST_SHA256:
            raise ValueError("final producer cannot use planning manifest identity")

        if len(self.plan_bindings) != EXPECTED_TRAJECTORY_COUNT:
            raise ValueError("producer requires exactly 342 plan bindings")
        expected_indexes = tuple(range(EXPECTED_TRAJECTORY_COUNT))
        observed_indexes = tuple(item.planned_order_index for item in self.plan_bindings)
        if observed_indexes != expected_indexes:
            raise ValueError("producer plan order drifted")

        if len(self.trace_bindings) != EXPECTED_TRAJECTORY_COUNT:
            raise ValueError("producer requires one trace binding per run")
        plan_pairs = {(item.run_id, item.trace_id) for item in self.plan_bindings}
        trace_pairs = {(item.run_id, item.trace_id) for item in self.trace_bindings}
        if trace_pairs != plan_pairs:
            raise ValueError("trace bindings do not cover exact frozen plan")
        if any(
            item.final_execution_manifest_sha256 != self.final_execution_manifest_sha256
            for item in self.trace_bindings
        ):
            raise ValueError("runtime trace final-manifest binding drifted")

        worker_ids = tuple(item.worker_id for item in self.worker_startups)
        if len(worker_ids) != len(set(worker_ids)):
            raise ValueError("worker startup evidence may occur only once per worker")

        event_sequences = tuple(event.sequence for event in self.events)
        if event_sequences != tuple(range(1, len(self.events) + 1)):
            raise ValueError("producer event sequence must remain contiguous")

        attempt_sequences = tuple(
            item.global_attempt_sequence for item in self.attempt_reservations
        )
        if attempt_sequences != tuple(range(1, len(self.attempt_reservations) + 1)):
            raise ValueError("attempt reservations must remain contiguous")

        outcome_sequences = {item.global_attempt_sequence for item in self.transport_outcomes}
        if len(outcome_sequences) != len(self.transport_outcomes):
            raise ValueError("transport outcome may persist only once")
        if not outcome_sequences.issubset(set(attempt_sequences)):
            raise ValueError("transport outcome references unknown attempt")

        successful_sequences = {
            item.global_attempt_sequence
            for item in self.transport_outcomes
            if item.outcome is core.AttemptOutcome.SUCCEEDED
        }
        measurement_sequences = {item.global_attempt_sequence for item in self.measurements}
        if len(measurement_sequences) != len(self.measurements):
            raise ValueError("measurement may persist only once")
        if not measurement_sequences.issubset(successful_sequences):
            raise ValueError("measurement requires successful transport")

        admission_sequences = {item.global_attempt_sequence for item in self.admissions}
        if len(admission_sequences) != len(self.admissions):
            raise ValueError("admission may persist only once")
        if not admission_sequences.issubset(measurement_sequences):
            raise ValueError("admission requires retained measurement")

        mutation_sequences = {item.global_attempt_sequence for item in self.state_mutations}
        if len(mutation_sequences) != len(self.state_mutations):
            raise ValueError("state mutation decision may persist only once")
        if not mutation_sequences.issubset(admission_sequences):
            raise ValueError("state mutation requires retained admission")

        terminal_run_ids = tuple(item.run_id for item in self.trajectory_terminals)
        if len(terminal_run_ids) != len(set(terminal_run_ids)):
            raise ValueError("trajectory terminal state may persist only once per run")

        expected_counters = core.RequestCounters(
            scheduled_request_count=len(self.attempt_reservations),
            attempted_request_count=len(self.attempt_reservations),
            http_completed_request_count=sum(
                int(item.http_completed) for item in self.transport_outcomes
            ),
            admitted_request_count=sum(
                int(item.evidence.schema_admitted) for item in self.admissions
            ),
            committed_request_count=sum(
                int(item.decision.history_mutation_permitted) for item in self.state_mutations
            ),
        )
        if self.request_counters != expected_counters:
            raise ValueError("request counters diverged from retained evidence")
        return self


@dataclass(frozen=True)
class TransportExecutionResult:
    record: TransportOutcomeRecord
    response_object: dict[str, object] | None
    response_json_object_valid: bool


class RuntimeWorker(Protocol):
    worker_id: str
    generation: int

    def start(self, counters: dict[str, int]) -> None: ...
    def wait_ready(self) -> None: ...
    def validate_model(self) -> None: ...
    def wait_backend_marker(self) -> None: ...
    def report(self) -> dict[str, object]: ...
    def stop_and_report(self, reason: str) -> dict[str, object]: ...


WorkerFactory = Callable[[str, int, int, Path, Path, int], RuntimeWorker]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def runtime_model_fingerprint() -> str:
    material = {
        "execution_backend": "local_vllm",
        "model_repository": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "served_model_alias": "local-qwen2.5-0.5b-instruct",
        "vllm_distribution_version": "0.25.1+cu129",
        "attention_backend": "TRITON_ATTN",
    }
    return sha256_text(canonical_json(material))


def _read_bytes(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file():
        raise ProducerError(
            "FINAL_342_PRODUCER_SOURCE_MISSING",
            "required predecessor is missing",
            relative,
        )
    if path.is_symlink():
        raise ProducerError(
            "FINAL_342_PRODUCER_SOURCE_UNSAFE",
            "required predecessor cannot be symlinked",
            relative,
        )
    return path.read_bytes()


def _read_object(root: Path, relative: Path) -> dict[str, object]:
    try:
        value = json.loads(_read_bytes(root, relative).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProducerError(
            "FINAL_342_PRODUCER_SOURCE_JSON_INVALID",
            "required predecessor JSON is invalid",
            relative,
        ) from error
    if not isinstance(value, dict):
        raise ProducerError(
            "FINAL_342_PRODUCER_SOURCE_SHAPE_INVALID",
            "required predecessor must contain one object",
            relative,
        )
    return cast(dict[str, object], value)


def _git_source_bytes(root: Path, relative: Path) -> bytes:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "show",
                f"{SOURCE_MAIN_COMMIT}:{relative.as_posix()}",
            ],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProducerError(
            "FINAL_342_PRODUCER_GIT_SOURCE_UNREADABLE",
            "unable to read accepted predecessor from Git",
            relative,
        ) from error
    if completed.returncode != 0:
        raise ProducerError(
            "FINAL_342_PRODUCER_GIT_SOURCE_MISSING",
            "accepted predecessor is absent from source main",
            relative,
        )
    return completed.stdout


def _require_source_unchanged(root: Path, relative: Path) -> bytes:
    accepted = _git_source_bytes(root, relative)
    current = _read_bytes(root, relative)
    if current != accepted:
        raise ProducerError(
            "FINAL_342_PRODUCER_ACCEPTED_SOURCE_DRIFT",
            "accepted predecessor bytes drifted",
            relative,
        )
    return accepted


def _require_source_main_ancestor(root: Path) -> None:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                SOURCE_MAIN_COMMIT,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProducerError(
            "FINAL_342_PRODUCER_GIT_STATE_UNREADABLE",
            "unable to inspect source-main ancestry",
        ) from error
    if completed.returncode != 0:
        raise ProducerError(
            "FINAL_342_PRODUCER_SOURCE_MAIN_MISSING",
            "accepted G11.3B main is not an ancestor",
        )


def validate_predecessors(repo_root: Path) -> tuple[SourceBinding, ...]:
    root = repo_root.resolve()
    _require_source_main_ancestor(root)

    bindings = tuple(
        SourceBinding(
            path=path.as_posix(),
            sha256=sha256_bytes(_require_source_unchanged(root, path)),
        )
        for path in BOUND_PREDECESSOR_PATHS
    )

    closure = _read_object(root, CLOSURE_RECORD_PATH)
    safety = closure.get("safety_state")
    if closure.get("next_gate") != "IMPLEMENT_FINAL_342_EXECUTION_PRODUCER_V1":
        raise ProducerError(
            "FINAL_342_PRODUCER_CLOSURE_GATE_DRIFT",
            "accepted G11.3B next gate drifted",
            CLOSURE_RECORD_PATH,
        )
    if not isinstance(safety, dict):
        raise ProducerError(
            "FINAL_342_PRODUCER_CLOSURE_STATE_INVALID",
            "accepted G11.3B safety state is invalid",
            CLOSURE_RECORD_PATH,
        )
    if safety.get("manifest_freeze_permitted") is not False:
        raise ProducerError(
            "FINAL_342_PRODUCER_CLOSURE_AUTHORITY_DRIFT",
            "producer implementation must remain pre-freeze",
            CLOSURE_RECORD_PATH,
        )
    if safety.get("final_measured_abc_execution_authorized") is not False:
        raise ProducerError(
            "FINAL_342_PRODUCER_CLOSURE_AUTHORITY_DRIFT",
            "producer cannot inherit live authority",
            CLOSURE_RECORD_PATH,
        )

    architecture = _read_object(root, ARCHITECTURE_PATH)
    north_star = architecture.get("north_star")
    retry = architecture.get("retry_and_accountability")
    if not isinstance(north_star, dict) or not isinstance(retry, dict):
        raise ProducerError(
            "FINAL_342_PRODUCER_ARCHITECTURE_INVALID",
            "accepted final runtime architecture is invalid",
            ARCHITECTURE_PATH,
        )

    expected_retry = {
        "maximum_request_attempt_count": EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
        "maximum_retries_after_initial_attempt": 1,
        "retry_backoff_seconds": RETRY_BACKOFF_SECONDS,
        "connection_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "first_output_timeout_seconds": FIRST_OUTPUT_TIMEOUT_SECONDS,
        "total_request_timeout_seconds": TOTAL_REQUEST_TIMEOUT_SECONDS,
        "retry_jitter_permitted": False,
        "retry_requires_no_response_or_definite_failure": True,
        "blind_retry_after_ambiguous_response_permitted": False,
    }
    if any(retry.get(key) != value for key, value in expected_retry.items()):
        raise ProducerError(
            "FINAL_342_PRODUCER_RETRY_CONTRACT_DRIFT",
            "accepted final retry contract drifted",
            ARCHITECTURE_PATH,
        )
    if north_star.get("planned_trajectories") != EXPECTED_TRAJECTORY_COUNT:
        raise ProducerError(
            "FINAL_342_PRODUCER_TRAJECTORY_COUNT_DRIFT",
            "accepted trajectory count drifted",
            ARCHITECTURE_PATH,
        )
    if north_star.get("planned_turns") != EXPECTED_TURN_COUNT:
        raise ProducerError(
            "FINAL_342_PRODUCER_TURN_COUNT_DRIFT",
            "accepted turn count drifted",
            ARCHITECTURE_PATH,
        )

    fingerprints = _read_object(root, PREFLIGHT_FINGERPRINTS_PATH)
    if fingerprints.get("pricing_fields_present") is not False:
        raise ProducerError(
            "FINAL_342_PRODUCER_PRICING_SCOPE_DRIFT",
            "preflight-v3 unexpectedly contains pricing",
            PREFLIGHT_FINGERPRINTS_PATH,
        )
    if fingerprints.get("provider_fields_present") is not False:
        raise ProducerError(
            "FINAL_342_PRODUCER_PROVIDER_SCOPE_DRIFT",
            "preflight-v3 unexpectedly contains provider fields",
            PREFLIGHT_FINGERPRINTS_PATH,
        )

    request_adapter = _read_bytes(root, V2_REQUEST_ADAPTER_PATH).decode("utf-8")
    if "with no retry path" not in request_adapter:
        raise ProducerError(
            "FINAL_342_PRODUCER_V2_ADAPTER_BOUNDARY_DRIFT",
            "accepted V2 no-retry boundary drifted",
            V2_REQUEST_ADAPTER_PATH,
        )
    if "def build_request_payload(" not in request_adapter:
        raise ProducerError(
            "FINAL_342_PRODUCER_REQUEST_BUILDER_MISSING",
            "accepted request builder is missing",
            V2_REQUEST_ADAPTER_PATH,
        )
    if "class AcceptedTokenizerSidecar" not in request_adapter:
        raise ProducerError(
            "FINAL_342_PRODUCER_TOKENIZER_SIDECAR_MISSING",
            "accepted tokenizer sidecar is missing",
            V2_REQUEST_ADAPTER_PATH,
        )

    runtime_text = _read_bytes(root, P5_P6_RUNTIME_PATH).decode("utf-8")
    worker_markers = (
        "class Worker:",
        "def start(",
        "def wait_ready(",
        "def validate_model(",
        "def wait_backend_marker(",
        "def stop_and_report(",
    )
    if any(marker not in runtime_text for marker in worker_markers):
        raise ProducerError(
            "FINAL_342_PRODUCER_WORKER_MECHANICS_DRIFT",
            "accepted worker lifecycle drifted",
            P5_P6_RUNTIME_PATH,
        )

    v2_runtime = _read_bytes(root, V2_RUNTIME_PATH).decode("utf-8")
    evidence_markers = (
        "def _atomic_write_json(",
        "def _checkpoint_payload(",
        "def _write_checkpoint(",
        "def reconcile_requests(",
        "def _bundle(",
    )
    if any(marker not in v2_runtime for marker in evidence_markers):
        raise ProducerError(
            "FINAL_342_PRODUCER_EVIDENCE_MECHANICS_DRIFT",
            "accepted evidence mechanics drifted",
            V2_RUNTIME_PATH,
        )
    return bindings


def initial_state(
    repo_root: Path,
    *,
    transaction_id: str,
    final_execution_manifest_sha256: str,
) -> ProducerState:
    if _SHA256_PATTERN.fullmatch(transaction_id) is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_TRANSACTION_ID_INVALID",
            "transaction identity must be SHA-256",
        )
    if _SHA256_PATTERN.fullmatch(final_execution_manifest_sha256) is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_MANIFEST_ID_INVALID",
            "final manifest identity must be SHA-256",
        )

    ledger = core.load_runtime_plan(repo_root)
    plan_bindings = tuple(
        PlanBinding(
            planned_order_index=run.planned_order_index,
            run_id=run.run_id,
            trace_id=run.trace_id,
            comparison_pair_id=run.comparison_pair_id,
            workload=run.workload,
            condition_id=run.condition_id,
            route_schedule_id=run.route_schedule_id,
            cache_namespace_sha256=sha256_text(run.cache_namespace_id),
        )
        for run in ledger.runs
    )
    trace_bindings = tuple(
        core.RuntimeTraceIdentity(
            run_id=run.run_id,
            trace_id=run.trace_id,
            final_execution_manifest_sha256=final_execution_manifest_sha256,
        )
        for run in ledger.runs
    )
    return ProducerState(
        transaction_id=transaction_id,
        final_execution_manifest_sha256=final_execution_manifest_sha256,
        source_bindings=validate_predecessors(repo_root),
        runtime_composition=RuntimeCompositionBinding(),
        plan_bindings=plan_bindings,
        trace_bindings=trace_bindings,
        request_counters=core.RequestCounters(
            scheduled_request_count=0,
            attempted_request_count=0,
            http_completed_request_count=0,
            admitted_request_count=0,
            committed_request_count=0,
        ),
        failure_state=core.FailureState(),
        events=(ProducerEvent(sequence=1, phase=ProducerPhase.TRANSACTION_ADMISSION),),
    )


def _state_payload(state: ProducerState, **updates: object) -> dict[str, object]:
    payload = cast(dict[str, object], state.model_dump(mode="python"))
    payload.update(updates)
    return payload


def _next_event(
    state: ProducerState,
    *,
    phase: ProducerPhase,
    run_id: str | None = None,
    trace_id: str | None = None,
    turn_index: int | None = None,
    attempt_index: int | None = None,
) -> ProducerEvent:
    return ProducerEvent(
        sequence=len(state.events) + 1,
        phase=phase,
        run_id=run_id,
        trace_id=trace_id,
        turn_index=turn_index,
        attempt_index=attempt_index,
    )


def _plan_for(state: ProducerState, run_id: str, trace_id: str) -> PlanBinding:
    match = next(
        (
            item
            for item in state.plan_bindings
            if item.run_id == run_id and item.trace_id == trace_id
        ),
        None,
    )
    if match is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_UNKNOWN_RUN",
            "request is outside frozen 342-run plan",
        )
    return match


def _trace_for(
    state: ProducerState,
    run_id: str,
    trace_id: str,
) -> core.RuntimeTraceIdentity:
    match = next(
        (
            item
            for item in state.trace_bindings
            if item.run_id == run_id and item.trace_id == trace_id
        ),
        None,
    )
    if match is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_TRACE_UNBOUND",
            "runtime trace lacks final-manifest binding",
        )
    return match


def _startup_for(state: ProducerState, worker_id: core.WorkerId) -> WorkerStartupRecord:
    match = next(
        (item for item in state.worker_startups if item.worker_id is worker_id),
        None,
    )
    if match is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_WORKER_NOT_STARTED",
            "route references worker without startup evidence",
        )
    return match


def _reservation_history(
    state: ProducerState,
    *,
    run_id: str,
    turn_index: int,
) -> tuple[AttemptReservation, ...]:
    return tuple(
        item
        for item in state.attempt_reservations
        if item.run_id == run_id and item.turn_index == turn_index
    )


def _retry_history(
    state: ProducerState,
    reservations: tuple[AttemptReservation, ...],
) -> tuple[core.RetryAttemptEvidence, ...]:
    by_sequence = {item.global_attempt_sequence: item for item in state.transport_outcomes}
    result: list[core.RetryAttemptEvidence] = []
    for reservation in reservations:
        outcome = by_sequence.get(reservation.global_attempt_sequence)
        if outcome is None:
            break
        result.append(
            core.RetryAttemptEvidence(
                attempt_index=reservation.attempt_index,
                logical_request_fingerprint=reservation.logical_request_fingerprint,
                route_identity=reservation.route_identity,
                outcome=outcome.outcome,
                retryable=outcome.retryable,
            )
        )
    return tuple(result)


def start_workers(
    state: ProducerState,
    store: MonotonicEvidenceStore,
    *,
    worker_factory: WorkerFactory,
    action_counters: dict[str, int],
    model_home: Path,
    snapshot: Path,
) -> tuple[ProducerState, dict[core.WorkerId, RuntimeWorker]]:
    if state.worker_startups:
        raise ProducerError(
            "FINAL_342_PRODUCER_WORKERS_ALREADY_STARTED",
            "worker startup evidence already exists",
        )

    current = state
    workers: dict[core.WorkerId, RuntimeWorker] = {}
    specs = (
        (core.WorkerId.WORKER_1, 0, 8001),
        (core.WorkerId.WORKER_2, 1, 8002),
    )

    for worker_id, gpu_index, port in specs:
        worker = worker_factory(
            worker_id.value,
            gpu_index,
            port,
            model_home,
            snapshot,
            1,
        )
        worker.start(action_counters)
        worker.wait_ready()
        worker.validate_model()
        worker.wait_backend_marker()
        report = worker.report()

        if report.get("worker_id") != worker_id.value:
            raise ProducerError(
                "FINAL_342_PRODUCER_WORKER_REPORT_INVALID",
                "worker report identity drifted",
            )
        if report.get("generation") != 1:
            raise ProducerError(
                "FINAL_342_PRODUCER_WORKER_REPORT_INVALID",
                "worker generation drifted",
            )
        if report.get("gpu_index") != gpu_index or report.get("port") != port:
            raise ProducerError(
                "FINAL_342_PRODUCER_WORKER_REPORT_INVALID",
                "worker topology drifted",
            )
        if report.get("backend_log_marker_observed") is not True:
            raise ProducerError(
                "FINAL_342_PRODUCER_BACKEND_NOT_REALIZED",
                "required backend marker was not observed",
            )

        argv_sha = report.get("argv_sha256")
        if not isinstance(argv_sha, str) or _SHA256_PATTERN.fullmatch(argv_sha) is None:
            raise ProducerError(
                "FINAL_342_PRODUCER_WORKER_REPORT_INVALID",
                "worker argv identity is invalid",
            )

        startup = WorkerStartupRecord(
            worker_id=worker_id,
            gpu_index=gpu_index,
            port=port,
            runtime_model_fingerprint=runtime_model_fingerprint(),
            argv_sha256=argv_sha,
        )
        current = ProducerState.model_validate(
            _state_payload(
                current,
                worker_startups=(*current.worker_startups, startup),
            )
        )
        store.persist(current)
        workers[worker_id] = worker

    return current, workers


def reserve_attempt(
    state: ProducerState,
    *,
    run_id: str,
    trace_id: str,
    turn_index: int,
    logical_request_fingerprint: str,
    route_identity: core.CacheResidencyIdentity,
) -> ProducerState:
    if turn_index not in {1, 2, 3, 4}:
        raise ProducerError(
            "FINAL_342_PRODUCER_TURN_INVALID",
            "turn index is outside frozen four-turn shape",
        )
    if len(state.attempt_reservations) >= EXPECTED_MAXIMUM_REQUEST_ATTEMPTS:
        raise ProducerError(
            "FINAL_342_PRODUCER_ATTEMPT_BUDGET_EXHAUSTED",
            "final request-attempt ceiling is exhausted",
        )

    plan = _plan_for(state, run_id, trace_id)
    _trace_for(state, run_id, trace_id)
    expected_worker = core.realize_route(plan.route_schedule_id)[turn_index - 1]
    if route_identity.worker_id is not expected_worker:
        raise ProducerError(
            "FINAL_342_PRODUCER_ROUTE_DRIFT",
            "request route differs from frozen schedule",
        )

    startup = _startup_for(state, expected_worker)
    if route_identity.worker_generation != startup.worker_generation:
        raise ProducerError(
            "FINAL_342_PRODUCER_WORKER_GENERATION_DRIFT",
            "worker generation drifted",
        )
    if route_identity.runtime_model_fingerprint != startup.runtime_model_fingerprint:
        raise ProducerError(
            "FINAL_342_PRODUCER_RUNTIME_MODEL_DRIFT",
            "runtime-model fingerprint drifted",
        )

    prior = _reservation_history(state, run_id=run_id, turn_index=turn_index)
    attempt_index = len(prior) + 1
    if attempt_index > 2:
        raise ProducerError(
            "FINAL_342_PRODUCER_TURN_RETRY_BUDGET_EXHAUSTED",
            "logical turn already consumed bounded retry",
        )

    backoff = 0
    if attempt_index == 2:
        history = _retry_history(state, prior)
        if len(history) != 1:
            raise ProducerError(
                "FINAL_342_PRODUCER_RETRY_HISTORY_INCOMPLETE",
                "retry requires persisted first-attempt outcome",
            )
        decision = core.authorize_retry(
            history,
            proposed_logical_request_fingerprint=logical_request_fingerprint,
            proposed_route_identity=route_identity,
        )
        if not decision.authorized:
            raise ProducerError(
                "FINAL_342_PRODUCER_RETRY_NOT_AUTHORIZED",
                f"bounded retry blocked: {decision.decision_code.value}",
            )
        if decision.retry_backoff_seconds != RETRY_BACKOFF_SECONDS:
            raise ProducerError(
                "FINAL_342_PRODUCER_RETRY_BACKOFF_DRIFT",
                "authorized retry backoff drifted",
            )
        backoff = RETRY_BACKOFF_SECONDS

    reservation = AttemptReservation(
        global_attempt_sequence=len(state.attempt_reservations) + 1,
        run_id=run_id,
        trace_id=trace_id,
        turn_index=turn_index,
        attempt_index=attempt_index,
        logical_request_fingerprint=logical_request_fingerprint,
        route_identity=route_identity,
        retry_backoff_seconds=backoff,
    )
    reservations = (*state.attempt_reservations, reservation)
    counters = core.RequestCounters(
        scheduled_request_count=len(reservations),
        attempted_request_count=len(reservations),
        http_completed_request_count=state.request_counters.http_completed_request_count,
        admitted_request_count=state.request_counters.admitted_request_count,
        committed_request_count=state.request_counters.committed_request_count,
    )
    return ProducerState.model_validate(
        _state_payload(
            state,
            attempt_reservations=reservations,
            request_counters=counters,
            events=(
                *state.events,
                _next_event(
                    state,
                    phase=ProducerPhase.REQUEST_ATTEMPT_RESERVATION,
                    run_id=run_id,
                    trace_id=trace_id,
                    turn_index=turn_index,
                    attempt_index=attempt_index,
                ),
            ),
        )
    )


def record_transport_outcome(
    state: ProducerState,
    outcome: TransportOutcomeRecord,
) -> ProducerState:
    reservation = next(
        (
            item
            for item in state.attempt_reservations
            if item.global_attempt_sequence == outcome.global_attempt_sequence
        ),
        None,
    )
    if reservation is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_TRANSPORT_WITHOUT_RESERVATION",
            "transport requires persisted reservation",
        )
    if any(
        item.global_attempt_sequence == outcome.global_attempt_sequence
        for item in state.transport_outcomes
    ):
        raise ProducerError(
            "FINAL_342_PRODUCER_TRANSPORT_DUPLICATE",
            "transport outcome is already persisted",
        )

    outcomes = (*state.transport_outcomes, outcome)
    counters = core.RequestCounters(
        scheduled_request_count=state.request_counters.scheduled_request_count,
        attempted_request_count=state.request_counters.attempted_request_count,
        http_completed_request_count=sum(int(item.http_completed) for item in outcomes),
        admitted_request_count=state.request_counters.admitted_request_count,
        committed_request_count=state.request_counters.committed_request_count,
    )
    return ProducerState.model_validate(
        _state_payload(
            state,
            transport_outcomes=outcomes,
            request_counters=counters,
            events=(
                *state.events,
                _next_event(
                    state,
                    phase=ProducerPhase.TRANSPORT_OUTCOME,
                    run_id=reservation.run_id,
                    trace_id=reservation.trace_id,
                    turn_index=reservation.turn_index,
                    attempt_index=reservation.attempt_index,
                ),
            ),
        )
    )


def record_measurement(
    state: ProducerState,
    *,
    global_attempt_sequence: int,
    warm_evidence: core.WarmTurnEvidence,
    prompt_token_count: int,
    server_usage_prompt_tokens: int,
    cached_prefix_tokens: int | None,
    newly_computed_prefill_tokens: int | None,
    prefill_duration_ms: float | None,
    time_to_first_token_ms: float | None,
    end_to_end_latency_ms: float | None,
    finish_reason: str | None,
    output_sha256: str,
) -> ProducerState:
    reservation = next(
        (
            item
            for item in state.attempt_reservations
            if item.global_attempt_sequence == global_attempt_sequence
        ),
        None,
    )
    if reservation is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_MEASUREMENT_WITHOUT_RESERVATION",
            "measurement requires persisted reservation",
        )

    transport = next(
        (
            item
            for item in state.transport_outcomes
            if item.global_attempt_sequence == global_attempt_sequence
        ),
        None,
    )
    if transport is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_MEASUREMENT_WITHOUT_TRANSPORT",
            "measurement requires transport evidence",
        )
    if transport.outcome is not core.AttemptOutcome.SUCCEEDED:
        raise ProducerError(
            "FINAL_342_PRODUCER_MEASUREMENT_WITHOUT_SUCCESS",
            "measurement requires successful transport",
        )
    if any(item.global_attempt_sequence == global_attempt_sequence for item in state.measurements):
        raise ProducerError(
            "FINAL_342_PRODUCER_MEASUREMENT_DUPLICATE",
            "measurement is already persisted",
        )

    plan = _plan_for(state, reservation.run_id, reservation.trace_id)
    trace = _trace_for(state, reservation.run_id, reservation.trace_id)
    if warm_evidence.session_id_hash != core.session_id_hash(reservation.run_id):
        raise ProducerError(
            "FINAL_342_PRODUCER_SESSION_DRIFT",
            "warm evidence session identity drifted",
        )
    if warm_evidence.cache_namespace_sha256 != plan.cache_namespace_sha256:
        raise ProducerError(
            "FINAL_342_PRODUCER_NAMESPACE_DRIFT",
            "warm evidence namespace drifted",
        )
    if warm_evidence.residency_identity != reservation.route_identity:
        raise ProducerError(
            "FINAL_342_PRODUCER_RESIDENCY_DRIFT",
            "warm evidence residency identity drifted",
        )

    prior_warm = tuple(
        item.warm_evidence for item in state.measurements if item.run_id == reservation.run_id
    )
    warm_decision = core.classify_warm_eligibility(warm_evidence, prior_warm)

    measurement = TurnMeasurementRecord(
        global_attempt_sequence=global_attempt_sequence,
        run_id=reservation.run_id,
        trace_id=reservation.trace_id,
        turn_index=reservation.turn_index,
        trace_identity=trace,
        route_identity=reservation.route_identity,
        warm_evidence=warm_evidence,
        warm_decision=warm_decision,
        prompt_token_count=prompt_token_count,
        server_usage_prompt_tokens=server_usage_prompt_tokens,
        cached_prefix_tokens=cached_prefix_tokens,
        newly_computed_prefill_tokens=newly_computed_prefill_tokens,
        prefill_duration_ms=prefill_duration_ms,
        time_to_first_token_ms=time_to_first_token_ms,
        end_to_end_latency_ms=end_to_end_latency_ms,
        finish_reason=finish_reason,
        output_sha256=output_sha256,
    )
    return ProducerState.model_validate(
        _state_payload(
            state,
            measurements=(*state.measurements, measurement),
            events=(
                *state.events,
                _next_event(
                    state,
                    phase=ProducerPhase.TELEMETRY_AND_OUTPUT_ADMISSION,
                    run_id=reservation.run_id,
                    trace_id=reservation.trace_id,
                    turn_index=reservation.turn_index,
                    attempt_index=reservation.attempt_index,
                ),
            ),
        )
    )


def record_admission(
    state: ProducerState,
    admission: AdmissionRecord,
) -> ProducerState:
    measurement = next(
        (
            item
            for item in state.measurements
            if item.global_attempt_sequence == admission.global_attempt_sequence
        ),
        None,
    )
    if measurement is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_ADMISSION_WITHOUT_MEASUREMENT",
            "admission requires retained measurement",
        )
    if admission.evidence.finish_reason != measurement.finish_reason:
        raise ProducerError(
            "FINAL_342_PRODUCER_FINISH_REASON_DRIFT",
            "admission finish reason differs from measurement",
        )
    if any(
        item.global_attempt_sequence == admission.global_attempt_sequence
        for item in state.admissions
    ):
        raise ProducerError(
            "FINAL_342_PRODUCER_ADMISSION_DUPLICATE",
            "admission is already persisted",
        )

    admissions = (*state.admissions, admission)
    counters = core.RequestCounters(
        scheduled_request_count=state.request_counters.scheduled_request_count,
        attempted_request_count=state.request_counters.attempted_request_count,
        http_completed_request_count=state.request_counters.http_completed_request_count,
        admitted_request_count=sum(int(item.evidence.schema_admitted) for item in admissions),
        committed_request_count=state.request_counters.committed_request_count,
    )
    return ProducerState.model_validate(
        _state_payload(
            state,
            admissions=admissions,
            request_counters=counters,
        )
    )


def record_state_mutation_decision(
    state: ProducerState,
    *,
    global_attempt_sequence: int,
) -> ProducerState:
    admission = next(
        (
            item
            for item in state.admissions
            if item.global_attempt_sequence == global_attempt_sequence
        ),
        None,
    )
    if admission is None:
        raise ProducerError(
            "FINAL_342_PRODUCER_MUTATION_WITHOUT_ADMISSION",
            "state mutation requires persisted admission",
        )
    if any(
        item.global_attempt_sequence == global_attempt_sequence for item in state.state_mutations
    ):
        raise ProducerError(
            "FINAL_342_PRODUCER_MUTATION_DUPLICATE",
            "state mutation decision is already persisted",
        )

    decision = core.evaluate_turn_commit(admission.evidence)
    mutation = StateMutationRecord(
        global_attempt_sequence=global_attempt_sequence,
        decision=decision,
    )
    mutations = (*state.state_mutations, mutation)
    reservation = state.attempt_reservations[global_attempt_sequence - 1]
    counters = core.RequestCounters(
        scheduled_request_count=state.request_counters.scheduled_request_count,
        attempted_request_count=state.request_counters.attempted_request_count,
        http_completed_request_count=state.request_counters.http_completed_request_count,
        admitted_request_count=state.request_counters.admitted_request_count,
        committed_request_count=sum(
            int(item.decision.history_mutation_permitted) for item in mutations
        ),
    )
    return ProducerState.model_validate(
        _state_payload(
            state,
            state_mutations=mutations,
            request_counters=counters,
            events=(
                *state.events,
                _next_event(
                    state,
                    phase=ProducerPhase.STATE_MUTATION_DECISION,
                    run_id=reservation.run_id,
                    trace_id=reservation.trace_id,
                    turn_index=reservation.turn_index,
                    attempt_index=reservation.attempt_index,
                ),
            ),
        )
    )


def record_trajectory_terminal(
    state: ProducerState,
    terminal: TrajectoryTerminalRecord,
) -> ProducerState:
    _plan_for(state, terminal.run_id, terminal.trace_id)
    if any(item.run_id == terminal.run_id for item in state.trajectory_terminals):
        raise ProducerError(
            "FINAL_342_PRODUCER_TRAJECTORY_TERMINAL_DUPLICATE",
            "trajectory terminal state is already persisted",
        )
    return ProducerState.model_validate(
        _state_payload(
            state,
            trajectory_terminals=(*state.trajectory_terminals, terminal),
            events=(
                *state.events,
                _next_event(
                    state,
                    phase=ProducerPhase.TRAJECTORY_TERMINAL_STATE,
                    run_id=terminal.run_id,
                    trace_id=terminal.trace_id,
                ),
            ),
        )
    )


def record_failure(
    state: ProducerState,
    failure: core.FailureRecord,
) -> ProducerState:
    next_failure_state = core.record_failure(state.failure_state, failure)
    phase_map = {
        core.FailurePhase.TRANSPORT: ProducerPhase.TRANSPORT_OUTCOME,
        core.FailurePhase.ADMISSION: ProducerPhase.TELEMETRY_AND_OUTPUT_ADMISSION,
        core.FailurePhase.STATE: ProducerPhase.STATE_MUTATION_DECISION,
        core.FailurePhase.TELEMETRY: ProducerPhase.TELEMETRY_AND_OUTPUT_ADMISSION,
        core.FailurePhase.TEARDOWN: ProducerPhase.WORKER_TEARDOWN,
        core.FailurePhase.CLEANUP: ProducerPhase.SCRATCH_CLEANUP,
        core.FailurePhase.EVIDENCE_PACKAGING: ProducerPhase.EVIDENCE_PACKAGING,
        core.FailurePhase.AUTHORIZATION_TERMINALIZATION: (
            ProducerPhase.AUTHORIZATION_TERMINALIZATION
        ),
    }
    return ProducerState.model_validate(
        _state_payload(
            state,
            failure_state=next_failure_state,
            events=(
                *state.events,
                _next_event(state, phase=phase_map[failure.phase]),
            ),
        )
    )


class FinalLoopbackVllmTransport:
    """Direct loopback transport with conservative duplicate-risk handling."""

    def __init__(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "http":
            raise ProducerError(
                "FINAL_342_PRODUCER_TRANSPORT_URL_INVALID",
                "final transport must use loopback HTTP",
            )
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ProducerError(
                "FINAL_342_PRODUCER_TRANSPORT_URL_INVALID",
                "final transport host must be loopback",
            )
        if parsed.port is None:
            raise ProducerError(
                "FINAL_342_PRODUCER_TRANSPORT_URL_INVALID",
                "final transport requires explicit port",
            )
        if parsed.path != "/v1/chat/completions":
            raise ProducerError(
                "FINAL_342_PRODUCER_TRANSPORT_URL_INVALID",
                "final transport endpoint drifted",
            )
        if parsed.username is not None or parsed.password is not None:
            raise ProducerError(
                "FINAL_342_PRODUCER_TRANSPORT_URL_INVALID",
                "transport URL cannot contain credentials",
            )
        if parsed.query or parsed.fragment:
            raise ProducerError(
                "FINAL_342_PRODUCER_TRANSPORT_URL_INVALID",
                "transport URL cannot contain query or fragment",
            )

        self.host = parsed.hostname
        self.port = parsed.port
        self.path = parsed.path

    def send(
        self,
        *,
        global_attempt_sequence: int,
        payload: dict[str, object],
    ) -> TransportExecutionResult:
        body = canonical_json(payload).encode("utf-8")
        connection = http.client.HTTPConnection(
            self.host,
            self.port,
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
        started = time.monotonic()

        try:
            try:
                connection.connect()
            except OSError:
                return self._failure(
                    global_attempt_sequence,
                    outcome=core.AttemptOutcome.NO_RESPONSE,
                    retryable=True,
                    error_code="LOOPBACK_CONNECT_FAILED",
                    safe_message="loopback connection failed before request transmission",
                )

            try:
                connection.request(
                    "POST",
                    self.path,
                    body=body,
                    headers={"Content-Type": "application/json"},
                )
            except OSError:
                return self._failure(
                    global_attempt_sequence,
                    outcome=core.AttemptOutcome.AMBIGUOUS,
                    retryable=False,
                    error_code="LOOPBACK_SEND_AMBIGUOUS",
                    safe_message="request transmission outcome is ambiguous",
                )

            remaining = TOTAL_REQUEST_TIMEOUT_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                return self._failure(
                    global_attempt_sequence,
                    outcome=core.AttemptOutcome.AMBIGUOUS,
                    retryable=False,
                    error_code="TOTAL_TIMEOUT_AFTER_SEND",
                    safe_message="total timeout expired after transmission",
                )
            if connection.sock is not None:
                connection.sock.settimeout(min(FIRST_OUTPUT_TIMEOUT_SECONDS, remaining))

            try:
                response = connection.getresponse()
            except OSError:
                return self._failure(
                    global_attempt_sequence,
                    outcome=core.AttemptOutcome.AMBIGUOUS,
                    retryable=False,
                    error_code="FIRST_OUTPUT_TIMEOUT_OR_FAILURE",
                    safe_message="response did not begin after transmission",
                )

            remaining = TOTAL_REQUEST_TIMEOUT_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                return self._failure(
                    global_attempt_sequence,
                    outcome=core.AttemptOutcome.AMBIGUOUS,
                    retryable=False,
                    error_code="TOTAL_TIMEOUT_AFTER_RESPONSE_START",
                    safe_message="response began after total timeout expired",
                )
            if connection.sock is not None:
                connection.sock.settimeout(remaining)

            try:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            except OSError:
                return self._failure(
                    global_attempt_sequence,
                    outcome=core.AttemptOutcome.AMBIGUOUS,
                    retryable=False,
                    error_code="RESPONSE_BODY_INCOMPLETE",
                    safe_message="response body did not complete within total timeout",
                )

            if len(raw) > MAX_RESPONSE_BYTES:
                return self._completed_failure(
                    global_attempt_sequence,
                    status=response.status,
                    raw=raw,
                    error_code="RESPONSE_BODY_TOO_LARGE",
                    safe_message="response exceeded bounded size",
                )
            if response.status != 200:
                return self._completed_failure(
                    global_attempt_sequence,
                    status=response.status,
                    raw=raw,
                    error_code=f"HTTP_{response.status}",
                    safe_message="loopback runtime returned definite non-success status",
                )

            digest = sha256_bytes(raw)
            response_object: dict[str, object] | None = None
            valid_object = False
            try:
                decoded = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                decoded = None
            if isinstance(decoded, dict) and all(isinstance(key, str) for key in decoded):
                response_object = cast(dict[str, object], decoded)
                valid_object = True

            return TransportExecutionResult(
                record=TransportOutcomeRecord(
                    global_attempt_sequence=global_attempt_sequence,
                    outcome=core.AttemptOutcome.SUCCEEDED,
                    retryable=False,
                    http_completed=True,
                    http_status=200,
                    response_sha256=digest,
                ),
                response_object=response_object,
                response_json_object_valid=valid_object,
            )
        finally:
            connection.close()

    @staticmethod
    def _failure(
        sequence: int,
        *,
        outcome: core.AttemptOutcome,
        retryable: bool,
        error_code: str,
        safe_message: str,
    ) -> TransportExecutionResult:
        return TransportExecutionResult(
            record=TransportOutcomeRecord(
                global_attempt_sequence=sequence,
                outcome=outcome,
                retryable=retryable,
                http_completed=False,
                error_code=error_code,
                safe_message=safe_message,
            ),
            response_object=None,
            response_json_object_valid=False,
        )

    @staticmethod
    def _completed_failure(
        sequence: int,
        *,
        status: int,
        raw: bytes,
        error_code: str,
        safe_message: str,
    ) -> TransportExecutionResult:
        return TransportExecutionResult(
            record=TransportOutcomeRecord(
                global_attempt_sequence=sequence,
                outcome=core.AttemptOutcome.DEFINITE_FAILURE,
                retryable=False,
                http_completed=True,
                http_status=status,
                response_sha256=sha256_bytes(raw),
                error_code=error_code,
                safe_message=safe_message,
            ),
            response_object=None,
            response_json_object_valid=False,
        )


def execute_transport_attempt(
    state: ProducerState,
    store: MonotonicEvidenceStore,
    *,
    run_id: str,
    trace_id: str,
    turn_index: int,
    logical_request_fingerprint: str,
    route_identity: core.CacheResidencyIdentity,
    payload: dict[str, object],
    transport: FinalLoopbackVllmTransport,
) -> tuple[ProducerState, TransportExecutionResult]:
    reserved = reserve_attempt(
        state,
        run_id=run_id,
        trace_id=trace_id,
        turn_index=turn_index,
        logical_request_fingerprint=logical_request_fingerprint,
        route_identity=route_identity,
    )
    store.persist(reserved)
    reservation = reserved.attempt_reservations[-1]

    if reservation.retry_backoff_seconds:
        time.sleep(reservation.retry_backoff_seconds)

    result = transport.send(
        global_attempt_sequence=reservation.global_attempt_sequence,
        payload=payload,
    )
    persisted = record_transport_outcome(reserved, result.record)
    store.persist(persisted)
    return persisted, result


def record_worker_teardown(
    state: ProducerState,
    store: MonotonicEvidenceStore,
    record: WorkerTeardownRecord,
) -> ProducerState:
    if any(item.worker_id is record.worker_id for item in state.worker_teardowns):
        raise ProducerError(
            "FINAL_342_PRODUCER_TEARDOWN_DUPLICATE",
            "worker teardown is already persisted",
        )
    updated = ProducerState.model_validate(
        _state_payload(
            state,
            worker_teardowns=(*state.worker_teardowns, record),
            events=(
                *state.events,
                _next_event(state, phase=ProducerPhase.WORKER_TEARDOWN),
            ),
        )
    )
    store.persist(updated)
    return updated


def teardown_workers(
    state: ProducerState,
    store: MonotonicEvidenceStore,
    workers: dict[core.WorkerId, RuntimeWorker],
    *,
    reason: str,
) -> ProducerState:
    current = state
    for worker_id in (core.WorkerId.WORKER_2, core.WorkerId.WORKER_1):
        worker = workers.get(worker_id)
        if worker is None:
            continue

        report = worker.stop_and_report(reason)
        status_value = report.get("status")
        status: Literal["PASSED", "NOT_STARTED", "FAILED"] = "FAILED"
        if status_value == "PASSED":
            status = "PASSED"
        if status_value == "NOT_STARTED":
            status = "NOT_STARTED"

        generation_value = report.get("generation")
        generation = generation_value if isinstance(generation_value, int) else 1
        failure_code = None if status != "FAILED" else "WORKER_TEARDOWN_FAILED"

        record = WorkerTeardownRecord(
            worker_id=worker_id,
            worker_generation=generation,
            status=status,
            process_tree_absent=cast(bool | None, report.get("process_tree_absent")),
            gpu_processes_absent=cast(bool | None, report.get("gpu_processes_absent")),
            port_closed=cast(bool | None, report.get("port_closed")),
            memory_returned=cast(bool | None, report.get("memory_returned")),
            safe_failure_code=failure_code,
        )
        current = record_worker_teardown(current, store, record)
    return current


def record_scratch_cleanup(
    state: ProducerState,
    store: MonotonicEvidenceStore,
    record: ScratchCleanupRecord,
) -> ProducerState:
    if state.scratch_cleanup is not None:
        raise ProducerError(
            "FINAL_342_PRODUCER_CLEANUP_DUPLICATE",
            "scratch cleanup is already persisted",
        )
    updated = ProducerState.model_validate(
        _state_payload(
            state,
            scratch_cleanup=record,
            events=(
                *state.events,
                _next_event(state, phase=ProducerPhase.SCRATCH_CLEANUP),
            ),
        )
    )
    store.persist(updated)
    return updated


def cleanup_scratch(
    state: ProducerState,
    store: MonotonicEvidenceStore,
    scratch_root: Path,
) -> ProducerState:
    root = scratch_root.resolve()
    cleanup_failed = False
    try:
        if root.exists():
            if root.is_symlink():
                raise ProducerError(
                    "FINAL_342_PRODUCER_SCRATCH_UNSAFE",
                    "scratch root cannot be symlinked",
                )
            shutil.rmtree(root)
    except (OSError, ProducerError):
        cleanup_failed = True

    if cleanup_failed:
        return record_scratch_cleanup(
            state,
            store,
            ScratchCleanupRecord(
                status="FAILED",
                scratch_absent=not root.exists(),
                safe_failure_code="SCRATCH_CLEANUP_FAILED",
            ),
        )
    return record_scratch_cleanup(
        state,
        store,
        ScratchCleanupRecord(
            status="PASSED",
            scratch_absent=not root.exists(),
        ),
    )


def request_reconciliation(state: ProducerState) -> dict[str, object]:
    counts = state.request_counters
    return {
        "schema_version": "1.0.0",
        "scheduled_request_count": counts.scheduled_request_count,
        "attempted_request_count": counts.attempted_request_count,
        "http_completed_request_count": counts.http_completed_request_count,
        "admitted_request_count": counts.admitted_request_count,
        "committed_request_count": counts.committed_request_count,
        "attempted_minus_http_completed": (
            counts.attempted_request_count - counts.http_completed_request_count
        ),
        "http_completed_minus_admitted": (
            counts.http_completed_request_count - counts.admitted_request_count
        ),
        "admitted_minus_committed": (
            counts.admitted_request_count - counts.committed_request_count
        ),
        "maximum_request_attempt_count": EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
        "hidden_retry_permitted": False,
        "replacement_case_permitted": False,
        "every_attempt_retained": True,
    }


class MonotonicEvidenceStore:
    """Persist append-only truth by atomic whole-state replacement."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.state_path = self.root / "producer_state_v1.json"

    def persist(self, state: ProducerState) -> SourceBinding:
        self._require_safe_root()
        previous = self._load_previous()
        if previous is not None:
            self._require_monotonic_successor(previous, state)

        payload = canonical_json(state.model_dump(mode="json")).encode("utf-8")
        temporary = self.state_path.with_name(f"{self.state_path.name}.{os.getpid()}.tmp")
        if temporary.exists():
            raise ProducerError(
                "FINAL_342_PRODUCER_TEMPORARY_PATH_EXISTS",
                "temporary producer state already exists",
            )

        self.root.mkdir(parents=True, exist_ok=True)
        try:
            temporary.write_bytes(payload)
            temporary.replace(self.state_path)
        finally:
            if temporary.exists():
                temporary.unlink()

        return SourceBinding(
            path=self.state_path.name,
            sha256=sha256_bytes(payload),
        )

    def _require_safe_root(self) -> None:
        if self.root.exists() and self.root.is_symlink():
            raise ProducerError(
                "FINAL_342_PRODUCER_EVIDENCE_ROOT_UNSAFE",
                "evidence root cannot be symlinked",
            )
        if self.state_path.exists() and self.state_path.is_symlink():
            raise ProducerError(
                "FINAL_342_PRODUCER_EVIDENCE_STATE_UNSAFE",
                "producer state cannot be symlinked",
            )

    def _load_previous(self) -> ProducerState | None:
        if not self.state_path.is_file():
            return None
        try:
            return ProducerState.model_validate_json(self.state_path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise ProducerError(
                "FINAL_342_PRODUCER_EXISTING_STATE_INVALID",
                "existing producer state is invalid",
            ) from error

    @staticmethod
    def _require_prefix(
        previous: tuple[BaseModel, ...],
        current: tuple[BaseModel, ...],
        label: str,
    ) -> None:
        if len(current) < len(previous):
            raise ProducerError(
                "FINAL_342_PRODUCER_MONOTONICITY_VIOLATION",
                f"{label} cannot shrink",
            )
        previous_payload = tuple(item.model_dump(mode="json") for item in previous)
        current_prefix = tuple(item.model_dump(mode="json") for item in current[: len(previous)])
        if previous_payload != current_prefix:
            raise ProducerError(
                "FINAL_342_PRODUCER_MONOTONICITY_VIOLATION",
                f"{label} cannot rewrite persisted truth",
            )

    @classmethod
    def _require_monotonic_successor(
        cls,
        previous: ProducerState,
        current: ProducerState,
    ) -> None:
        immutable_fields = (
            "transaction_id",
            "final_execution_manifest_sha256",
            "source_bindings",
            "runtime_composition",
            "plan_bindings",
            "trace_bindings",
        )
        if any(getattr(previous, name) != getattr(current, name) for name in immutable_fields):
            raise ProducerError(
                "FINAL_342_PRODUCER_IMMUTABLE_STATE_DRIFT",
                "immutable execution identity changed",
            )

        cls._require_prefix(previous.events, current.events, "events")
        cls._require_prefix(
            previous.worker_startups,
            current.worker_startups,
            "worker startups",
        )
        cls._require_prefix(
            previous.attempt_reservations,
            current.attempt_reservations,
            "attempt reservations",
        )
        cls._require_prefix(
            previous.transport_outcomes,
            current.transport_outcomes,
            "transport outcomes",
        )
        cls._require_prefix(previous.measurements, current.measurements, "measurements")
        cls._require_prefix(previous.admissions, current.admissions, "admissions")
        cls._require_prefix(
            previous.state_mutations,
            current.state_mutations,
            "state mutations",
        )
        cls._require_prefix(
            previous.trajectory_terminals,
            current.trajectory_terminals,
            "trajectory terminals",
        )
        cls._require_prefix(
            previous.worker_teardowns,
            current.worker_teardowns,
            "worker teardowns",
        )

        before = previous.request_counters
        after = current.request_counters
        pairs = (
            (before.scheduled_request_count, after.scheduled_request_count),
            (before.attempted_request_count, after.attempted_request_count),
            (before.http_completed_request_count, after.http_completed_request_count),
            (before.admitted_request_count, after.admitted_request_count),
            (before.committed_request_count, after.committed_request_count),
        )
        if any(current_value < previous_value for previous_value, current_value in pairs):
            raise ProducerError(
                "FINAL_342_PRODUCER_COUNTER_REGRESSION",
                "request counters cannot decrease",
            )

        if (
            previous.failure_state.primary_failure is not None
            and current.failure_state.primary_failure != previous.failure_state.primary_failure
        ):
            raise ProducerError(
                "FINAL_342_PRODUCER_PRIMARY_FAILURE_REWRITE",
                "first causal failure cannot be replaced",
            )
        cls._require_prefix(
            previous.failure_state.secondary_failures,
            current.failure_state.secondary_failures,
            "secondary failures",
        )

        if (
            previous.scratch_cleanup is not None
            and current.scratch_cleanup != previous.scratch_cleanup
        ):
            raise ProducerError(
                "FINAL_342_PRODUCER_CLEANUP_REWRITE",
                "cleanup result cannot be replaced",
            )
        if (
            previous.evidence_bundle is not None
            and current.evidence_bundle != previous.evidence_bundle
        ):
            raise ProducerError(
                "FINAL_342_PRODUCER_BUNDLE_REWRITE",
                "bundle receipt cannot be replaced",
            )


def _atomic_write_json(path: Path, value: object) -> None:
    payload = canonical_json(value).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise ProducerError(
            "FINAL_342_PRODUCER_TEMPORARY_PATH_EXISTS",
            "temporary evidence path already exists",
        )
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_evidence_bundle(
    state: ProducerState,
    *,
    output_root: Path,
    archive_path: Path,
) -> EvidenceBundleReceipt:
    root = output_root.resolve()
    archive = archive_path.resolve()

    if root.exists() and root.is_symlink():
        raise ProducerError(
            "FINAL_342_PRODUCER_BUNDLE_ROOT_UNSAFE",
            "public evidence root cannot be symlinked",
        )
    if archive.exists():
        raise ProducerError(
            "FINAL_342_PRODUCER_BUNDLE_ARCHIVE_EXISTS",
            "evidence archive path must be fresh",
        )
    if archive.is_symlink():
        raise ProducerError(
            "FINAL_342_PRODUCER_BUNDLE_ARCHIVE_UNSAFE",
            "evidence archive cannot be symlinked",
        )

    root.mkdir(parents=True, exist_ok=True)

    projections: dict[str, object] = {
        "runtime_trace_bindings_v1.json": {
            "schema_version": "1.0.0",
            "final_execution_manifest_sha256": state.final_execution_manifest_sha256,
            "trace_count": len(state.trace_bindings),
            "traces": [item.model_dump(mode="json") for item in state.trace_bindings],
        },
        "attempt_action_ledger_v1.json": {
            "schema_version": "1.0.0",
            "reservations": [item.model_dump(mode="json") for item in state.attempt_reservations],
            "transport_outcomes": [
                item.model_dump(mode="json") for item in state.transport_outcomes
            ],
            "admissions": [item.model_dump(mode="json") for item in state.admissions],
            "state_mutations": [item.model_dump(mode="json") for item in state.state_mutations],
        },
        "turn_measurements_v1.json": {
            "schema_version": "1.0.0",
            "measurement_count": len(state.measurements),
            "measurements": [item.model_dump(mode="json") for item in state.measurements],
        },
        "request_reconciliation_v1.json": request_reconciliation(state),
        "failure_report_v1.json": state.failure_state.model_dump(mode="json"),
        "worker_startup_report_v1.json": {
            "schema_version": "1.0.0",
            "workers": [item.model_dump(mode="json") for item in state.worker_startups],
        },
        "worker_teardown_report_v1.json": {
            "schema_version": "1.0.0",
            "workers": [item.model_dump(mode="json") for item in state.worker_teardowns],
        },
        "scratch_cleanup_report_v1.json": (
            {"schema_version": "1.0.0", "status": "NOT_RECORDED"}
            if state.scratch_cleanup is None
            else state.scratch_cleanup.model_dump(mode="json")
        ),
        "trajectory_terminal_ledger_v1.json": {
            "schema_version": "1.0.0",
            "scheduled_trajectory_count": EXPECTED_TRAJECTORY_COUNT,
            "observed_terminal_count": len(state.trajectory_terminals),
            "trajectories": [item.model_dump(mode="json") for item in state.trajectory_terminals],
        },
    }

    paths: list[Path] = []
    for name, payload in projections.items():
        path = root / name
        _atomic_write_json(path, payload)
        paths.append(path)

    members = [
        {
            "path": path.name,
            "sha256": sha256_bytes(path.read_bytes()),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(paths, key=lambda item: item.name)
    ]
    manifest = {
        "schema_version": "1.0.0",
        "producer_id": PRODUCER_ID,
        "transaction_id": state.transaction_id,
        "final_execution_manifest_sha256": state.final_execution_manifest_sha256,
        "member_count": len(members),
        "members": members,
        "raw_prompts_included": False,
        "raw_outputs_included": False,
        "raw_provider_payloads_included": False,
        "credentials_included": False,
    }
    manifest_path = root / "bundle_manifest_v1.json"
    _atomic_write_json(manifest_path, manifest)

    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in [*paths, manifest_path]:
            handle.write(path, arcname=path.name)

    return EvidenceBundleReceipt(
        bundle_manifest_sha256=sha256_bytes(manifest_path.read_bytes()),
        evidence_archive_sha256=sha256_bytes(archive.read_bytes()),
        member_count=len(members),
    )


def record_evidence_bundle(
    state: ProducerState,
    store: MonotonicEvidenceStore,
    receipt: EvidenceBundleReceipt,
) -> ProducerState:
    if state.evidence_bundle is not None:
        raise ProducerError(
            "FINAL_342_PRODUCER_BUNDLE_DUPLICATE",
            "evidence bundle is already persisted",
        )
    updated = ProducerState.model_validate(
        _state_payload(
            state,
            evidence_bundle=receipt,
            events=(
                *state.events,
                _next_event(state, phase=ProducerPhase.EVIDENCE_PACKAGING),
            ),
        )
    )
    store.persist(updated)
    return updated


def validate(repo_root: Path) -> dict[str, object]:
    bindings = validate_predecessors(repo_root)
    return {
        "status": "FINAL_342_EXECUTION_PRODUCER_V1_IMPLEMENTATION_VALID",
        "producer_id": PRODUCER_ID,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "bound_predecessor_count": len(bindings),
        "planned_trajectory_count": EXPECTED_TRAJECTORY_COUNT,
        "planned_turn_count": EXPECTED_TURN_COUNT,
        "maximum_request_attempt_count": EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
        "retry_backoff_seconds": RETRY_BACKOFF_SECONDS,
        "connection_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "first_output_timeout_seconds": FIRST_OUTPUT_TIMEOUT_SECONDS,
        "total_request_timeout_seconds": TOTAL_REQUEST_TIMEOUT_SECONDS,
        "per_trace_final_manifest_binding_implemented": True,
        "worker_startup_composition_implemented": True,
        "request_transport_composition_implemented": True,
        "typed_turn_measurement_persistence_implemented": True,
        "attempt_reconciliation_persistence_implemented": True,
        "primary_secondary_failure_persistence_implemented": True,
        "teardown_cleanup_evidence_implemented": True,
        "measured_evidence_bundle_writer_implemented": True,
        "local_runtime_provider_field_mapping_implemented": True,
        "monetary_cost_comparison_in_scope": False,
        "external_spend_ceiling": 0,
        "one_shot_v2_adapter_permitted": False,
        "complete_offline_producer_rehearsal_established": False,
        "manifest_freeze_permitted": False,
        "execution_manifest_frozen": False,
        "final_measured_abc_execution_authorized": False,
        "effect_claims_permitted": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": "AUTHOR_FINAL_342_EXECUTION_PRODUCER_V1_TESTS",
    }


__all__ = [
    "AdmissionRecord",
    "AttemptReservation",
    "EvidenceBundleReceipt",
    "FinalLoopbackVllmTransport",
    "MonotonicEvidenceStore",
    "PlanBinding",
    "ProducerError",
    "ProducerEvent",
    "ProducerPhase",
    "ProducerState",
    "RuntimeCompositionBinding",
    "ScratchCleanupRecord",
    "SourceBinding",
    "StateMutationRecord",
    "TrajectoryTerminalRecord",
    "TrajectoryTerminalState",
    "TransportExecutionResult",
    "TransportOutcomeRecord",
    "TurnMeasurementRecord",
    "WorkerStartupRecord",
    "WorkerTeardownRecord",
    "cleanup_scratch",
    "execute_transport_attempt",
    "initial_state",
    "record_admission",
    "record_evidence_bundle",
    "record_failure",
    "record_measurement",
    "record_scratch_cleanup",
    "record_state_mutation_decision",
    "record_trajectory_terminal",
    "record_transport_outcome",
    "record_worker_teardown",
    "request_reconciliation",
    "reserve_attempt",
    "runtime_model_fingerprint",
    "sha256_bytes",
    "sha256_text",
    "start_workers",
    "teardown_workers",
    "validate",
    "validate_predecessors",
    "write_evidence_bundle",
]
