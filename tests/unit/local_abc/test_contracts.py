from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from auragateway.local_abc.contracts import (
    CacheObservation,
    CacheObservationState,
    ConditionDefinition,
    ConditionId,
    EnvironmentManifest,
    ExperimentManifest,
    FailureRecord,
    ModelIdentity,
    PrefixIdentity,
    PrefixPolicy,
    RouteSchedule,
    RunEligibility,
    RunTerminalClassification,
    TelemetryObservation,
    TokenizerIdentity,
    TrajectoryRecord,
    TrajectoryTerminalState,
    WorkerId,
    WorkerIdentity,
)
from auragateway.local_abc.errors import LocalABCFailureCode

NOW = datetime(2026, 7, 14, 20, 0, tzinfo=UTC)
TRACE_ID = UUID("11111111-1111-4111-8111-111111111111")
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def _model(*, digest: str = SHA_A) -> ModelIdentity:
    return ModelIdentity(
        repository="Qwen/Qwen2.5-0.5B-Instruct",
        revision="1111111",
        config_sha256=digest,
    )


def _tokenizer(*, digest: str = SHA_B) -> TokenizerIdentity:
    return TokenizerIdentity(
        repository="Qwen/Qwen2.5-0.5B-Instruct",
        revision="2222222",
        config_sha256=digest,
    )


def _worker(worker_id: WorkerId, *, model: ModelIdentity | None = None) -> WorkerIdentity:
    topology = {
        WorkerId.WORKER_1: (0, 8001),
        WorkerId.WORKER_2: (1, 8002),
    }
    gpu_index, port = topology[worker_id]
    return WorkerIdentity(
        worker_id=worker_id,
        gpu_index=gpu_index,
        port=port,
        runtime_version="0.10.2",
        model=model or _model(),
        tokenizer=_tokenizer(),
    )


def _environment() -> EnvironmentManifest:
    return EnvironmentManifest(
        manifest_id="local-abc-environment-v1",
        captured_at=NOW,
        python_version="3.11.9",
        cuda_version="12.4",
        gpu_type="NVIDIA-Tesla-T4",
        workers=(
            _worker(WorkerId.WORKER_1),
            _worker(WorkerId.WORKER_2),
        ),
    )


def _prefix(token_hash: str = SHA_C) -> PrefixIdentity:
    return PrefixIdentity(
        serializer_version="1.0.0",
        token_hash=token_hash,
        token_count=4096,
        tokenizer_fingerprint=_tokenizer().fingerprint(),
    )


def _condition(
    condition_id: ConditionId, *, prefix: PrefixIdentity | None = None
) -> ConditionDefinition:
    policies = {
        ConditionId.A: PrefixPolicy.CACHE_HOSTILE,
        ConditionId.B: PrefixPolicy.DETERMINISTIC_EXACT,
        ConditionId.C: PrefixPolicy.DETERMINISTIC_EXACT,
    }
    routes = {
        ConditionId.A: (WorkerId.WORKER_1, WorkerId.WORKER_2),
        ConditionId.B: (WorkerId.WORKER_1, WorkerId.WORKER_2),
        ConditionId.C: (WorkerId.WORKER_1, WorkerId.WORKER_1),
    }
    return ConditionDefinition(
        condition_id=condition_id,
        prefix_policy=policies[condition_id],
        route_schedule=RouteSchedule(workers=routes[condition_id]),
        prefix_identity=prefix or _prefix(),
    )


def _manifest() -> ExperimentManifest:
    shared_prefix = _prefix()
    return ExperimentManifest(
        manifest_id="local-abc-experiment-v1",
        created_at=NOW,
        environment=_environment(),
        conditions=(
            _condition(ConditionId.A, prefix=_prefix(SHA_A)),
            _condition(ConditionId.B, prefix=shared_prefix),
            _condition(ConditionId.C, prefix=shared_prefix),
        ),
        case_ids=("case-001", "case-002"),
        output_token_budget=32,
        decoding_config_sha256=SHA_B,
        quality_rubric_version="1.0.0",
    )


def _cache_zero() -> CacheObservation:
    return CacheObservation(
        state=CacheObservationState.ZERO,
        raw_metric_name="vllm:prefix_cache_hits",
        observed_cached_prefix_tokens=0,
    )


def _telemetry(worker_id: WorkerId, observation_id: str) -> TelemetryObservation:
    return TelemetryObservation(
        observation_id=observation_id,
        worker_id=worker_id,
        collected_at=NOW,
        metric_mapping_version="1.0.0",
        cache=_cache_zero(),
        eligible_shared_prefix_tokens=4096,
        newly_computed_prefill_tokens=4096,
        prefill_duration_ms=25.0,
        time_to_first_token_ms=30.0,
        end_to_end_latency_ms=45.0,
    )


def test_manifest_accepts_frozen_abc_constitution() -> None:
    manifest = _manifest()
    assert manifest.condition_for(ConditionId.B).route_schedule.workers == (
        WorkerId.WORKER_1,
        WorkerId.WORKER_2,
    )
    assert (
        manifest.condition_for(ConditionId.B).prefix_identity
        == manifest.condition_for(ConditionId.C).prefix_identity
    )


def test_environment_rejects_model_identity_drift() -> None:
    with pytest.raises(ValidationError, match="MODEL_IDENTITY_MISMATCH"):
        EnvironmentManifest(
            manifest_id="local-abc-environment-v1",
            captured_at=NOW,
            python_version="3.11.9",
            cuda_version="12.4",
            gpu_type="NVIDIA-Tesla-T4",
            workers=(
                _worker(WorkerId.WORKER_1),
                _worker(WorkerId.WORKER_2, model=_model(digest=SHA_C)),
            ),
        )


def test_environment_rejects_duplicate_worker_identity() -> None:
    with pytest.raises(ValidationError, match="worker_1 and worker_2"):
        EnvironmentManifest(
            manifest_id="local-abc-environment-v1",
            captured_at=NOW,
            python_version="3.11.9",
            cuda_version="12.4",
            gpu_type="NVIDIA-Tesla-T4",
            workers=(
                _worker(WorkerId.WORKER_1),
                _worker(WorkerId.WORKER_1),
            ),
        )


def test_environment_rejects_nonzero_external_spend() -> None:
    payload = _environment().model_dump()
    payload["external_spend"] = Decimal("0.01")
    with pytest.raises(ValidationError, match="external_spend must remain zero"):
        EnvironmentManifest.model_validate(payload)


def test_environment_rejects_customer_data() -> None:
    payload = _environment().model_dump()
    payload["customer_data_used"] = True
    with pytest.raises(ValidationError, match="Input should be False"):
        EnvironmentManifest.model_validate(payload)


def test_worker_rejects_unfrozen_port_mapping() -> None:
    payload = _worker(WorkerId.WORKER_1).model_dump()
    payload["port"] = 9001
    with pytest.raises(ValidationError, match="frozen GPU and port topology"):
        WorkerIdentity.model_validate(payload)


def test_condition_rejects_wrong_route_schedule() -> None:
    with pytest.raises(ValidationError, match="route schedule violates"):
        ConditionDefinition(
            condition_id=ConditionId.C,
            prefix_policy=PrefixPolicy.DETERMINISTIC_EXACT,
            route_schedule=RouteSchedule(workers=(WorkerId.WORKER_1, WorkerId.WORKER_2)),
            prefix_identity=_prefix(),
        )


def test_manifest_rejects_b_c_prefix_mismatch() -> None:
    with pytest.raises(ValidationError, match="PREFIX_HASH_MISMATCH"):
        ExperimentManifest(
            manifest_id="local-abc-experiment-v1",
            created_at=NOW,
            environment=_environment(),
            conditions=(
                _condition(ConditionId.A, prefix=_prefix(SHA_A)),
                _condition(ConditionId.B, prefix=_prefix(SHA_B)),
                _condition(ConditionId.C, prefix=_prefix(SHA_C)),
            ),
            case_ids=("case-001",),
            output_token_budget=32,
            decoding_config_sha256=SHA_B,
            quality_rubric_version="1.0.0",
        )


def test_condition_b_rejects_route_mismatch_with_condition_a() -> None:
    with pytest.raises(ValidationError, match="route schedule violates"):
        ConditionDefinition(
            condition_id=ConditionId.B,
            prefix_policy=PrefixPolicy.DETERMINISTIC_EXACT,
            route_schedule=RouteSchedule(workers=(WorkerId.WORKER_1, WorkerId.WORKER_1)),
            prefix_identity=_prefix(),
        )


def test_not_exposed_cache_evidence_cannot_be_encoded_as_zero() -> None:
    with pytest.raises(ValidationError, match="cannot contain a metric or value"):
        CacheObservation(
            state=CacheObservationState.NOT_EXPOSED,
            observed_cached_prefix_tokens=0,
            reason_code=LocalABCFailureCode.TELEMETRY_NOT_EXPOSED,
        )


def test_not_observed_cache_evidence_cannot_be_encoded_as_zero() -> None:
    with pytest.raises(ValidationError, match="no numeric value"):
        CacheObservation(
            state=CacheObservationState.NOT_OBSERVED,
            raw_metric_name="vllm:prefix_cache_hits",
            observed_cached_prefix_tokens=0,
            reason_code=LocalABCFailureCode.TELEMETRY_NOT_OBSERVED,
        )


def test_zero_cache_evidence_requires_observed_zero() -> None:
    with pytest.raises(ValidationError, match="observed metric value of zero"):
        CacheObservation(
            state=CacheObservationState.ZERO,
            raw_metric_name="vllm:prefix_cache_hits",
        )


def test_positive_cache_evidence_requires_positive_value() -> None:
    with pytest.raises(ValidationError, match="observed positive value"):
        CacheObservation(
            state=CacheObservationState.POSITIVE,
            raw_metric_name="vllm:prefix_cache_hits",
            observed_cached_prefix_tokens=0,
        )


def test_invalid_cache_evidence_cannot_retain_numeric_value() -> None:
    with pytest.raises(ValidationError, match="cannot retain a normalized numeric value"):
        CacheObservation(
            state=CacheObservationState.INVALID,
            raw_metric_name="vllm:prefix_cache_hits",
            observed_cached_prefix_tokens=1,
            reason_code=LocalABCFailureCode.TELEMETRY_AMBIGUOUS,
        )


def test_telemetry_rejects_cached_tokens_above_eligible_prefix() -> None:
    with pytest.raises(ValidationError, match="cannot exceed eligible shared prefix"):
        TelemetryObservation(
            observation_id="observation-001",
            worker_id=WorkerId.WORKER_1,
            collected_at=NOW,
            metric_mapping_version="1.0.0",
            cache=CacheObservation(
                state=CacheObservationState.POSITIVE,
                raw_metric_name="vllm:prefix_cache_hits",
                observed_cached_prefix_tokens=4097,
            ),
            eligible_shared_prefix_tokens=4096,
        )


def test_completed_trajectory_requires_two_turns_and_observations() -> None:
    with pytest.raises(ValidationError, match="require two realized turns"):
        TrajectoryRecord(
            trajectory_id="trajectory-001",
            trace_id=TRACE_ID,
            case_id="case-001",
            replication_id="replication-001",
            condition_id=ConditionId.C,
            intended_route=RouteSchedule(workers=(WorkerId.WORKER_1, WorkerId.WORKER_1)),
            realized_route=(WorkerId.WORKER_1,),
            terminal_state=TrajectoryTerminalState.COMPLETED,
            task_completed=True,
            telemetry=(_telemetry(WorkerId.WORKER_1, "observation-001"),),
        )


def test_route_mismatch_requires_explicit_fallback() -> None:
    with pytest.raises(ValidationError, match="fallback_used must exactly match"):
        TrajectoryRecord(
            trajectory_id="trajectory-001",
            trace_id=TRACE_ID,
            case_id="case-001",
            replication_id="replication-001",
            condition_id=ConditionId.C,
            intended_route=RouteSchedule(workers=(WorkerId.WORKER_1, WorkerId.WORKER_1)),
            realized_route=(WorkerId.WORKER_1, WorkerId.WORKER_2),
            terminal_state=TrajectoryTerminalState.COMPLETED,
            task_completed=True,
            telemetry=(
                _telemetry(WorkerId.WORKER_1, "observation-001"),
                _telemetry(WorkerId.WORKER_2, "observation-002"),
            ),
        )


def test_fallback_trajectory_requires_route_failure_code() -> None:
    with pytest.raises(ValidationError, match="ROUTE_REALIZATION_MISMATCH"):
        TrajectoryRecord(
            trajectory_id="trajectory-001",
            trace_id=TRACE_ID,
            case_id="case-001",
            replication_id="replication-001",
            condition_id=ConditionId.C,
            intended_route=RouteSchedule(workers=(WorkerId.WORKER_1, WorkerId.WORKER_1)),
            realized_route=(WorkerId.WORKER_1, WorkerId.WORKER_2),
            terminal_state=TrajectoryTerminalState.COMPLETED,
            task_completed=True,
            fallback_used=True,
            telemetry=(
                _telemetry(WorkerId.WORKER_1, "observation-001"),
                _telemetry(WorkerId.WORKER_2, "observation-002"),
            ),
        )


def test_incomplete_trajectory_cannot_be_marked_comparison_eligible() -> None:
    with pytest.raises(ValidationError, match="completed_eligible must exactly match"):
        RunEligibility(
            trajectory_id="trajectory-001",
            condition_id=ConditionId.C,
            terminal_classification=RunTerminalClassification.INTERRUPTED_RETAINED,
            task_completed=False,
            comparison_eligible=True,
            affinity_comparison_eligible=True,
            telemetry_sufficient=False,
            route_realized=False,
            fallback_used=False,
            failure_codes=(LocalABCFailureCode.SESSION_INTERRUPTED,),
        )


def test_fallback_cannot_be_affinity_eligible() -> None:
    with pytest.raises(ValidationError, match="fallback blocks"):
        RunEligibility(
            trajectory_id="trajectory-001",
            condition_id=ConditionId.C,
            terminal_classification=(
                RunTerminalClassification.TASK_COMPLETED_BUT_COMPARISON_INELIGIBLE
            ),
            task_completed=True,
            comparison_eligible=False,
            affinity_comparison_eligible=True,
            telemetry_sufficient=True,
            route_realized=False,
            fallback_used=True,
            failure_codes=(LocalABCFailureCode.ROUTE_REALIZATION_MISMATCH,),
        )


def test_eligible_run_rejects_failure_codes() -> None:
    with pytest.raises(ValidationError, match="cannot contain fallback or failures"):
        RunEligibility(
            trajectory_id="trajectory-001",
            condition_id=ConditionId.B,
            terminal_classification=RunTerminalClassification.COMPLETED_ELIGIBLE,
            task_completed=True,
            comparison_eligible=True,
            affinity_comparison_eligible=True,
            telemetry_sufficient=True,
            route_realized=True,
            fallback_used=False,
            failure_codes=(LocalABCFailureCode.RUN_INELIGIBLE,),
        )


def test_ineligible_run_requires_reason_code() -> None:
    with pytest.raises(ValidationError, match="at least one failure code"):
        RunEligibility(
            trajectory_id="trajectory-001",
            condition_id=ConditionId.B,
            terminal_classification=RunTerminalClassification.COMPLETED_INELIGIBLE,
            task_completed=True,
            comparison_eligible=False,
            affinity_comparison_eligible=False,
            telemetry_sufficient=False,
            route_realized=True,
            fallback_used=False,
        )


def test_failure_record_cannot_remove_attempt_from_ledger() -> None:
    with pytest.raises(ValidationError, match="Input should be True"):
        FailureRecord(
            failure_id="failure-001",
            trajectory_id="trajectory-001",
            occurred_at=NOW,
            code=LocalABCFailureCode.SESSION_INTERRUPTED,
            attempt_retained=False,
            safe_detail="Kaggle session ended before turn two completed.",
        )


def test_contracts_forbid_extra_fields() -> None:
    payload = _prefix().model_dump()
    payload["raw_prefix"] = "must-not-enter-contract"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PrefixIdentity.model_validate(payload)


def test_canonical_json_and_fingerprint_are_deterministic() -> None:
    left = ModelIdentity.model_validate(
        {
            "repository": "Qwen/Qwen2.5-0.5B-Instruct",
            "revision": "1111111",
            "config_sha256": SHA_A,
        }
    )
    right = ModelIdentity.model_validate(
        {
            "config_sha256": SHA_A,
            "revision": "1111111",
            "repository": "Qwen/Qwen2.5-0.5B-Instruct",
        }
    )
    assert left.canonical_json() == right.canonical_json()
    assert left.fingerprint() == right.fingerprint()
    assert len(left.fingerprint()) == 64
