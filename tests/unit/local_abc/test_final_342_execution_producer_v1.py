from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from auragateway.local_abc import final_342_execution_producer_v1 as producer
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

ROOT = Path(__file__).resolve().parents[3]
FINAL_MANIFEST_SHA256 = hashlib.sha256(b"final-execution-manifest").hexdigest()
TRANSACTION_ID = hashlib.sha256(b"transaction").hexdigest()


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _initial_state() -> producer.ProducerState:
    return producer.initial_state(
        ROOT,
        transaction_id=TRANSACTION_ID,
        final_execution_manifest_sha256=FINAL_MANIFEST_SHA256,
    )


def _with_startups(state: producer.ProducerState) -> producer.ProducerState:
    fingerprint = producer.runtime_model_fingerprint()
    payload = state.model_dump(mode="python")
    payload["worker_startups"] = (
        producer.WorkerStartupRecord(
            worker_id=core.WorkerId.WORKER_1,
            gpu_index=0,
            port=8001,
            runtime_model_fingerprint=fingerprint,
            argv_sha256=_sha("worker-1-argv"),
        ),
        producer.WorkerStartupRecord(
            worker_id=core.WorkerId.WORKER_2,
            gpu_index=1,
            port=8002,
            runtime_model_fingerprint=fingerprint,
            argv_sha256=_sha("worker-2-argv"),
        ),
    )
    return producer.ProducerState.model_validate(payload)


def _first_plan(state: producer.ProducerState) -> producer.PlanBinding:
    return state.plan_bindings[0]


def _route_identity(
    state: producer.ProducerState,
    *,
    turn_index: int = 1,
) -> core.CacheResidencyIdentity:
    plan = _first_plan(state)
    worker_id = core.realize_route(plan.route_schedule_id)[turn_index - 1]
    return core.CacheResidencyIdentity(
        worker_id=worker_id,
        worker_generation=1,
        runtime_model_fingerprint=producer.runtime_model_fingerprint(),
    )


def _reserve_first(
    state: producer.ProducerState,
    *,
    fingerprint: str | None = None,
) -> producer.ProducerState:
    plan = _first_plan(state)
    return producer.reserve_attempt(
        state,
        run_id=plan.run_id,
        trace_id=plan.trace_id,
        turn_index=1,
        logical_request_fingerprint=fingerprint or _sha("logical-request"),
        route_identity=_route_identity(state),
    )


class _FakeWorker:
    def __init__(
        self,
        worker_id: str,
        gpu_index: int,
        port: int,
        model_home: Path,
        snapshot: Path,
        generation: int,
    ) -> None:
        self.worker_id = worker_id
        self.gpu_index = gpu_index
        self.port = port
        self.model_home = model_home
        self.snapshot = snapshot
        self.generation = generation

    def start(self, counters: dict[str, int]) -> None:
        counters["worker_starts"] = counters.get("worker_starts", 0) + 1
        counters["model_loads"] = counters.get("model_loads", 0) + 1

    def wait_ready(self) -> None:
        return None

    def validate_model(self) -> None:
        return None

    def wait_backend_marker(self) -> None:
        return None

    def report(self) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "generation": self.generation,
            "gpu_index": self.gpu_index,
            "port": self.port,
            "backend_log_marker_observed": True,
            "argv_sha256": _sha(f"{self.worker_id}-argv"),
        }

    def stop_and_report(self, reason: str) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "generation": self.generation,
            "reason": reason,
            "status": "PASSED",
            "process_tree_absent": True,
            "gpu_processes_absent": True,
            "port_closed": True,
            "memory_returned": True,
        }


def _fake_worker_factory(
    worker_id: str,
    gpu_index: int,
    port: int,
    model_home: Path,
    snapshot: Path,
    generation: int,
) -> _FakeWorker:
    return _FakeWorker(
        worker_id,
        gpu_index,
        port,
        model_home,
        snapshot,
        generation,
    )


class _RecordingTransport(producer.FinalLoopbackVllmTransport):
    def __init__(self, store: producer.MonotonicEvidenceStore) -> None:
        self.store = store
        self.saw_reserved_state = False

    def send(
        self,
        *,
        global_attempt_sequence: int,
        payload: dict[str, object],
    ) -> producer.TransportExecutionResult:
        del payload
        persisted = producer.ProducerState.model_validate_json(
            self.store.state_path.read_text(encoding="utf-8")
        )
        self.saw_reserved_state = (
            len(persisted.attempt_reservations) == 1
            and not persisted.transport_outcomes
        )
        return producer.TransportExecutionResult(
            record=producer.TransportOutcomeRecord(
                global_attempt_sequence=global_attempt_sequence,
                outcome=core.AttemptOutcome.NO_RESPONSE,
                retryable=True,
                http_completed=False,
                error_code="TEST_NO_RESPONSE",
                safe_message="No response was observed.",
            ),
            response_object=None,
            response_json_object_valid=False,
        )


def test_initial_state_binds_all_342_traces_to_final_manifest() -> None:
    state = _initial_state()

    assert len(state.plan_bindings) == 342
    assert len(state.trace_bindings) == 342
    assert {
        item.final_execution_manifest_sha256 for item in state.trace_bindings
    } == {FINAL_MANIFEST_SHA256}
    assert state.manifest_freeze_permitted is False
    assert state.final_measured_abc_execution_authorized_by_producer is False


def test_worker_startup_composition_persists_each_worker_before_success(
    tmp_path: Path,
) -> None:
    state = _initial_state()
    store = producer.MonotonicEvidenceStore(tmp_path / "evidence")
    counters = {"worker_starts": 0, "model_loads": 0}

    updated, workers = producer.start_workers(
        state,
        store,
        worker_factory=_fake_worker_factory,
        action_counters=counters,
        model_home=tmp_path / "model-home",
        snapshot=tmp_path / "snapshot",
    )

    assert tuple(item.worker_id for item in updated.worker_startups) == (
        core.WorkerId.WORKER_1,
        core.WorkerId.WORKER_2,
    )
    assert set(workers) == set(core.WorkerId)
    assert counters == {"worker_starts": 2, "model_loads": 2}

    persisted = producer.ProducerState.model_validate_json(
        store.state_path.read_text(encoding="utf-8")
    )
    assert persisted.worker_startups == updated.worker_startups


def test_transport_reservation_is_persisted_before_transport(
    tmp_path: Path,
) -> None:
    state = _with_startups(_initial_state())
    store = producer.MonotonicEvidenceStore(tmp_path / "evidence")
    plan = _first_plan(state)
    transport = _RecordingTransport(store)

    updated, result = producer.execute_transport_attempt(
        state,
        store,
        run_id=plan.run_id,
        trace_id=plan.trace_id,
        turn_index=1,
        logical_request_fingerprint=_sha("logical-request"),
        route_identity=_route_identity(state),
        payload={"model": "local-qwen2.5-0.5b-instruct"},
        transport=transport,
    )

    assert transport.saw_reserved_state is True
    assert len(updated.attempt_reservations) == 1
    assert len(updated.transport_outcomes) == 1
    assert result.record.outcome is core.AttemptOutcome.NO_RESPONSE


def test_retry_is_authorized_only_after_persisted_retryable_no_response() -> None:
    state = _with_startups(_initial_state())
    fingerprint = _sha("logical-request")
    state = _reserve_first(state, fingerprint=fingerprint)
    state = producer.record_transport_outcome(
        state,
        producer.TransportOutcomeRecord(
            global_attempt_sequence=1,
            outcome=core.AttemptOutcome.NO_RESPONSE,
            retryable=True,
            http_completed=False,
            error_code="NO_RESPONSE",
            safe_message="No response was observed.",
        ),
    )
    plan = _first_plan(state)

    retried = producer.reserve_attempt(
        state,
        run_id=plan.run_id,
        trace_id=plan.trace_id,
        turn_index=1,
        logical_request_fingerprint=fingerprint,
        route_identity=_route_identity(state),
    )

    assert retried.attempt_reservations[-1].attempt_index == 2
    assert retried.attempt_reservations[-1].retry_backoff_seconds == 2


def test_ambiguous_transport_blocks_retry() -> None:
    state = _with_startups(_initial_state())
    fingerprint = _sha("logical-request")
    state = _reserve_first(state, fingerprint=fingerprint)
    state = producer.record_transport_outcome(
        state,
        producer.TransportOutcomeRecord(
            global_attempt_sequence=1,
            outcome=core.AttemptOutcome.AMBIGUOUS,
            retryable=False,
            http_completed=False,
            error_code="AMBIGUOUS",
            safe_message="Transmission outcome is ambiguous.",
        ),
    )
    plan = _first_plan(state)

    with pytest.raises(
        producer.ProducerError,
        match="bounded retry blocked",
    ) as captured:
        producer.reserve_attempt(
            state,
            run_id=plan.run_id,
            trace_id=plan.trace_id,
            turn_index=1,
            logical_request_fingerprint=fingerprint,
            route_identity=_route_identity(state),
        )

    assert captured.value.error_code == "FINAL_342_PRODUCER_RETRY_NOT_AUTHORIZED"


def test_retry_rejects_logical_request_fingerprint_change() -> None:
    state = _with_startups(_initial_state())
    state = _reserve_first(state, fingerprint=_sha("logical-request"))
    state = producer.record_transport_outcome(
        state,
        producer.TransportOutcomeRecord(
            global_attempt_sequence=1,
            outcome=core.AttemptOutcome.NO_RESPONSE,
            retryable=True,
            http_completed=False,
            error_code="NO_RESPONSE",
            safe_message="No response was observed.",
        ),
    )
    plan = _first_plan(state)

    with pytest.raises(producer.ProducerError) as captured:
        producer.reserve_attempt(
            state,
            run_id=plan.run_id,
            trace_id=plan.trace_id,
            turn_index=1,
            logical_request_fingerprint=_sha("changed-request"),
            route_identity=_route_identity(state),
        )

    assert captured.value.error_code == "FINAL_342_PRODUCER_RETRY_NOT_AUTHORIZED"


def test_admission_and_mutation_cannot_skip_measurement_boundary() -> None:
    state = _with_startups(_initial_state())
    state = _reserve_first(state)
    state = producer.record_transport_outcome(
        state,
        producer.TransportOutcomeRecord(
            global_attempt_sequence=1,
            outcome=core.AttemptOutcome.SUCCEEDED,
            retryable=False,
            http_completed=True,
            http_status=200,
            response_sha256=_sha("response"),
        ),
    )
    admission = producer.AdmissionRecord(
        global_attempt_sequence=1,
        evidence=core.TurnAdmissionEvidence(
            turn_index=1,
            current_prompt_budget_valid=True,
            finish_reason="stop",
            schema_admitted=True,
            has_next_turn=True,
            next_prompt_reachable=True,
        ),
    )

    with pytest.raises(producer.ProducerError) as admission_failure:
        producer.record_admission(state, admission)
    assert (
        admission_failure.value.error_code
        == "FINAL_342_PRODUCER_ADMISSION_WITHOUT_MEASUREMENT"
    )

    with pytest.raises(producer.ProducerError) as mutation_failure:
        producer.record_state_mutation_decision(
            state,
            global_attempt_sequence=1,
        )
    assert (
        mutation_failure.value.error_code
        == "FINAL_342_PRODUCER_MUTATION_WITHOUT_ADMISSION"
    )


def test_first_causal_failure_survives_secondary_failures() -> None:
    state = _initial_state()
    primary = core.FailureRecord(
        phase=core.FailurePhase.ADMISSION,
        error_code="OUTPUT_SCHEMA_INVALID",
        safe_message="Output admission failed.",
    )
    cleanup = core.FailureRecord(
        phase=core.FailurePhase.CLEANUP,
        error_code="SCRATCH_CLEANUP_FAILED",
        safe_message="Scratch cleanup failed.",
    )
    packaging = core.FailureRecord(
        phase=core.FailurePhase.EVIDENCE_PACKAGING,
        error_code="EVIDENCE_ZIP_FAILED",
        safe_message="Evidence packaging failed.",
    )

    state = producer.record_failure(state, primary)
    state = producer.record_failure(state, cleanup)
    state = producer.record_failure(state, packaging)

    assert state.failure_state.primary_failure == primary
    assert state.failure_state.secondary_failures == (cleanup, packaging)


def test_monotonic_store_rejects_identity_rewrite(tmp_path: Path) -> None:
    state = _initial_state()
    store = producer.MonotonicEvidenceStore(tmp_path / "evidence")
    store.persist(state)

    rewritten = state.model_copy(
        update={"transaction_id": _sha("different-transaction")}
    )

    with pytest.raises(producer.ProducerError) as captured:
        store.persist(rewritten)

    assert captured.value.error_code == "FINAL_342_PRODUCER_IMMUTABLE_STATE_DRIFT"


def test_public_bundle_contains_typed_evidence_without_raw_content(
    tmp_path: Path,
) -> None:
    state = _initial_state()
    output_root = tmp_path / "public-evidence"
    archive = tmp_path / "public-evidence.zip"

    receipt = producer.write_evidence_bundle(
        state,
        output_root=output_root,
        archive_path=archive,
    )

    manifest = json.loads(
        (output_root / "bundle_manifest_v1.json").read_text(encoding="utf-8")
    )
    measurements = json.loads(
        (output_root / "turn_measurements_v1.json").read_text(encoding="utf-8")
    )

    assert receipt.raw_prompts_included is False
    assert receipt.raw_outputs_included is False
    assert receipt.raw_provider_payloads_included is False
    assert manifest["raw_prompts_included"] is False
    assert manifest["raw_outputs_included"] is False
    assert manifest["raw_provider_payloads_included"] is False
    assert measurements["measurement_count"] == 0
    assert archive.is_file()


def test_producer_validation_is_non_authorizing() -> None:
    result = producer.validate(ROOT)

    assert result["status"] == "FINAL_342_EXECUTION_PRODUCER_V1_IMPLEMENTATION_VALID"
    assert result["planned_trajectory_count"] == 342
    assert result["planned_turn_count"] == 1368
    assert result["maximum_request_attempt_count"] == 2736
    assert result["complete_offline_producer_rehearsal_established"] is False
    assert result["manifest_freeze_permitted"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["model_requests_performed"] == 0
    assert result["gpu_execution_performed"] is False
    assert result["kaggle_execution_performed"] is False
