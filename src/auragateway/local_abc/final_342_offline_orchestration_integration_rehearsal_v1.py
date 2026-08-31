"""Offline end-to-end orchestration rehearsal for the final 342 experiment.

This module composes the accepted final-run planning, producer, protected-review,
measured-quality, and analysis boundaries using deterministic synthetic evidence only.
It performs no model, GPU, Kaggle, manifest-freeze, authorization-issuance, or live
execution work and produces no scientific effect evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    CriterionScore,
    QualityReviewRecord,
    ReviewRole,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.quality import (
    DeterministicQualityResult,
    QualityCheckName,
    QualityCheckResult,
    QualityCheckStatus,
)
from auragateway.contracts.retrieval_eval import TerminalDecision
from auragateway.local_abc import final_342_analysis_engine_v1 as analysis
from auragateway.local_abc import final_342_execution_producer_v1 as producer
from auragateway.local_abc import final_342_measured_quality_reducers_v1 as quality
from auragateway.local_abc import final_342_measured_review_design_v1 as review_design
from auragateway.local_abc import final_342_measured_review_successor_v1 as review_successor
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_offline_orchestration_integration_rehearsal_v1.json"
)
RUBRIC_PATH = Path("data/evals/quality/blinded-v1/rubric.json")

EXPECTED_BASE_MAIN = "0cbb6cea399537345efdbddbb874fecfa6dc5a85"
REHEARSAL_ID: Literal["auragateway-final-342-offline-orchestration-integration-rehearsal-v1"] = (
    "auragateway-final-342-offline-orchestration-integration-rehearsal-v1"
)
NEXT_GATE: Literal["REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1"] = (
    "REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1"
)

EXPECTED_TRAJECTORY_COUNT = 342
EXPECTED_FUNCTIONAL_RUN_COUNT = 162
EXPECTED_RUNTIME_RUN_COUNT = 180
EXPECTED_SECONDARY_REVIEW_COUNT = 41
EXPECTED_RUNTIME_MEASUREMENT_COUNT = 720
EXPECTED_RUNTIME_PAIR_COUNT = 60
EXPECTED_PROTECTED_CAPTURE_COUNT = 4
EXPECTED_PROTECTED_ASSIGNMENT_COUNT = 2

EXPECTED_SOURCE_BLOBS: dict[str, str] = {
    "src/auragateway/local_abc/final_342_non_authorizing_runtime_core_v1.py": (
        "7edeb7cb3f6c2213868d23863c33a9a94669468c"
    ),
    "src/auragateway/local_abc/final_342_execution_producer_v1.py": (
        "9bedae7c7815e80d7c03ccc37b1e5261310056cf"
    ),
    "src/auragateway/local_abc/final_342_measured_review_design_v1.py": (
        "673091128975b2fc33ba175649c8e82b2670a522"
    ),
    "src/auragateway/local_abc/final_342_measured_review_successor_v1.py": (
        "aee9891d5fa5a23621d4e2c7fb20b575e6f43aaf"
    ),
    "benchmarks/local_abc/auragateway_final_342_measured_review_successor_v1.json": (
        "684d645daccb2357e886267154424e2533c6401c"
    ),
    "src/auragateway/local_abc/final_342_measured_quality_reducers_v1.py": (
        "e84f47010f16f0340d38de71a22e1cc7c03b6252"
    ),
    "benchmarks/local_abc/auragateway_final_342_measured_quality_reducers_v1.json": (
        "dd2a9be5dca8eccbf1c70c9d6645866736dff57e"
    ),
    "src/auragateway/local_abc/final_342_analysis_engine_v1.py": (
        "6385c01486885e3e21b90fb18765602eba3b083e"
    ),
    "benchmarks/local_abc/auragateway_final_342_analysis_engine_v1.json": (
        "11b213762ae673cb9c1e13af53df0bb15303d06a"
    ),
    "data/evals/benchmark/preflight-v3/planned_run_ledger.json": (
        "553b23e24629bdca81d9fb9fdcbd90cc2081caf0"
    ),
    RUBRIC_PATH.as_posix(): "13fc4dbd77dfd2667dd601c481821f7ac5ce0bd5",
}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


SYNTHETIC_TRANSACTION_ID = _sha("final-342-offline-integration-rehearsal-transaction-v1")
SYNTHETIC_FINAL_MANIFEST_SHA256 = _sha("final-342-offline-integration-rehearsal-manifest-v1")
SYNTHETIC_RETRIEVAL_FINGERPRINT = _sha("final-342-offline-rehearsal-retrieval-config-v1")
SYNTHETIC_EPISODE_MANIFEST_SHA256 = _sha("final-342-offline-rehearsal-episode-manifest-v1")
SYNTHETIC_RUNTIME_MODEL_FINGERPRINT = _sha("final-342-offline-rehearsal-runtime-model-v1")


class OfflineRehearsalError(RuntimeError):
    """Fail-closed, metadata-safe offline-rehearsal failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise OfflineRehearsalError("FINAL_342_OFFLINE_REHEARSAL_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceBinding(FrozenModel):
    role: str = Field(min_length=3)
    path: str = Field(min_length=3)
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class CompositionBoundary(FrozenModel):
    planned_trajectory_count: Literal[342]
    functional_run_count: Literal[162]
    runtime_run_count: Literal[180]
    secondary_review_target_count: Literal[41]
    producer_initial_state_required: Literal[True]
    protected_review_capture_round_trip_required: Literal[True]
    measured_quality_reducer_required: Literal[True]
    final_analysis_engine_required: Literal[True]
    exact_population_analysis_required: Literal[True]
    synthetic_evidence_only: Literal[True]


class ClaimBoundary(FrozenModel):
    synthetic_result_is_scientific_evidence: Literal[False]
    synthetic_supported_decision_permits_effect_claim: Literal[False]
    measured_feedback_required_for_north_star_claims: Literal[False]
    feedback_specific_claims_without_measured_feedback_permitted: Literal[False]
    measured_execution_claims_permitted: Literal[False]


class SafetyState(FrozenModel):
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    network_transport_performed: Literal[False]
    execution_manifest_frozen: Literal[False]
    manifest_freeze_permitted: Literal[False]
    live_authorization_issued: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class OfflineRehearsalRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    rehearsal_id: Literal["auragateway-final-342-offline-orchestration-integration-rehearsal-v1"]
    status: Literal["PROPOSED_FOR_FINAL_342_OFFLINE_REHEARSAL_ACCEPTANCE"]
    base_main_commit: Literal["0cbb6cea399537345efdbddbb874fecfa6dc5a85"]
    decision: Literal["FINAL_342_OFFLINE_ORCHESTRATION_AND_INTEGRATION_REHEARSAL_V1"]
    source_bindings: tuple[SourceBinding, ...]
    composition_boundary: CompositionBoundary
    claim_boundary: ClaimBoundary
    safety_state: SafetyState
    next_gate: Literal["REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1"]

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        observed = {item.path: item.git_blob_sha for item in self.source_bindings}
        if observed != EXPECTED_SOURCE_BLOBS:
            raise ValueError("offline-rehearsal source binding set drifted")
        return self


class ProtectedReviewRoundTrip(FrozenModel):
    scheduled_secondary_run_id: str
    capture_count: int = Field(ge=0)
    loaded_capture_count: int = Field(ge=0)
    reviewer_assignment_count: int = Field(ge=0)
    public_receipt_item_count: int = Field(ge=0)
    reviewer_payload_safe: Literal[True]

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if (
            self.capture_count != EXPECTED_PROTECTED_CAPTURE_COUNT
            or self.loaded_capture_count != EXPECTED_PROTECTED_CAPTURE_COUNT
            or self.reviewer_assignment_count != EXPECTED_PROTECTED_ASSIGNMENT_COUNT
            or self.public_receipt_item_count != 1
        ):
            raise ValueError("protected-review rehearsal counts drifted")
        return self


class OfflineRehearsalSummary(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    rehearsal_id: Literal[
        "auragateway-final-342-offline-orchestration-integration-rehearsal-v1"
    ] = REHEARSAL_ID
    status: Literal["FINAL_342_OFFLINE_ORCHESTRATION_INTEGRATION_REHEARSAL_PASS"]
    planned_trajectory_count: int = Field(ge=0)
    functional_run_count: int = Field(ge=0)
    runtime_run_count: int = Field(ge=0)
    producer_plan_binding_count: int = Field(ge=0)
    producer_trace_binding_count: int = Field(ge=0)
    secondary_review_schedule_count: int = Field(ge=0)
    protected_review_round_trip: ProtectedReviewRoundTrip
    measured_quality_result_count: int = Field(ge=0)
    runtime_measurement_count: int = Field(ge=0)
    runtime_contrast_count: int = Field(ge=0)
    eligible_pairs_per_contrast: tuple[Literal[60], Literal[60], Literal[60]]
    synthetic_analysis_evidence_complete: Literal[True]
    synthetic_quality_gate_passed: Literal[True]
    synthetic_mechanics_claim_decisions: tuple[
        Literal["SUPPORTED"], Literal["SUPPORTED"], Literal["SUPPORTED"]
    ]
    synthetic_results_are_scientific_evidence: Literal[False]
    synthetic_effect_claims_authoritative: Literal[False]
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    network_transport_performed: Literal[False]
    execution_manifest_frozen: Literal[False]
    manifest_freeze_permitted: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]
    next_gate: Literal["REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1"]

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        observed = (
            self.planned_trajectory_count,
            self.functional_run_count,
            self.runtime_run_count,
            self.producer_plan_binding_count,
            self.producer_trace_binding_count,
            self.secondary_review_schedule_count,
            self.measured_quality_result_count,
            self.runtime_measurement_count,
            self.runtime_contrast_count,
        )
        expected = (342, 162, 180, 342, 342, 41, 162, 720, 3)
        if observed != expected:
            raise ValueError("offline-rehearsal summary population counts drifted")
        return self


@dataclass
class _SyntheticTransportResult:
    response_object: dict[str, object] | None
    response_json_object_valid: bool


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_JSON_READ_FAILED",
            f"unable to read required JSON object: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_JSON_SHAPE_INVALID",
            f"required JSON value must be one string-keyed object: {path.as_posix()}",
        )
    return cast(dict[str, object], value)


def _git_blob_sha(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_SOURCE_MISSING",
            f"required predecessor is missing or symlinked: {relative}",
        )
    completed = subprocess.run(
        ["git", "hash-object", "--", relative],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_GIT_HASH_FAILED",
            f"unable to hash required predecessor: {relative}",
        )
    return completed.stdout.strip()


def _require_base_main_ancestor(root: Path) -> None:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_BASE_MAIN, "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_BASE_MAIN_INVALID",
            "accepted analysis-engine merge must be an ancestor of current HEAD",
        )


def _validate_source_bindings(root: Path, record: OfflineRehearsalRecord) -> None:
    observed = {item.path: item.git_blob_sha for item in record.source_bindings}
    if observed != EXPECTED_SOURCE_BLOBS:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_SOURCE_SET_DRIFT",
            "offline-rehearsal source binding set drifted",
        )
    for relative, expected in EXPECTED_SOURCE_BLOBS.items():
        if _git_blob_sha(root, relative) != expected:
            raise OfflineRehearsalError(
                "FINAL_342_OFFLINE_REHEARSAL_SOURCE_IDENTITY_DRIFT",
                f"offline-rehearsal predecessor identity drifted: {relative}",
            )


def _load_record(root: Path) -> OfflineRehearsalRecord:
    try:
        return OfflineRehearsalRecord.model_validate(_read_json_object(root / RECORD_PATH))
    except ValidationError as error:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_RECORD_INVALID",
            "offline-rehearsal decision record failed validation",
        ) from error


def _require_non_authorizing_predecessors(root: Path) -> None:
    producer_summary = producer.validate(root)
    review_summary = review_successor.validate(root, require_protected_schedule=False)
    quality_summary = quality.validate(root)
    analysis_summary = analysis.validate(root)

    predecessor_safety_values = (
        producer_summary.get("manifest_freeze_permitted"),
        producer_summary.get("final_measured_abc_execution_authorized"),
        producer_summary.get("effect_claims_permitted"),
        review_summary.get("manifest_freeze_permitted"),
        review_summary.get("final_measured_abc_execution_authorized"),
        review_summary.get("effect_claims_permitted"),
        quality_summary.get("manifest_freeze_permitted"),
        quality_summary.get("final_measured_abc_execution_authorized"),
        quality_summary.get("effect_claims_permitted"),
        analysis_summary.get("manifest_freeze_permitted"),
        analysis_summary.get("final_measured_abc_execution_authorized"),
        analysis_summary.get("effect_claims_permitted"),
    )
    if any(value is not False for value in predecessor_safety_values):
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_PREDECESSOR_AUTHORITY_DRIFT",
            "an accepted predecessor unexpectedly permits freeze, execution, or effect claims",
        )


def validate_subject(repo_root: Path) -> dict[str, object]:
    """Validate the exact merged integration subject without running synthetic evidence."""

    root = repo_root.resolve()
    _require_base_main_ancestor(root)
    record = _load_record(root)
    _validate_source_bindings(root, record)
    _require_non_authorizing_predecessors(root)

    ledger = core.load_runtime_plan(root)
    functional_count = sum(item.workload is core.WorkloadId.FUNCTIONAL for item in ledger.runs)
    runtime_count = sum(
        item.workload is core.WorkloadId.RUNTIME_MICROBENCHMARK for item in ledger.runs
    )
    schedule = review_successor.derive_protected_schedule(root)
    if (
        len(ledger.runs) != EXPECTED_TRAJECTORY_COUNT
        or functional_count != EXPECTED_FUNCTIONAL_RUN_COUNT
        or runtime_count != EXPECTED_RUNTIME_RUN_COUNT
        or len(schedule.entries) != EXPECTED_SECONDARY_REVIEW_COUNT
    ):
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_POPULATION_DRIFT",
            "frozen plan or protected-review population drifted",
        )

    return {
        "status": "FINAL_342_OFFLINE_REHEARSAL_SUBJECT_VALID",
        "rehearsal_id": record.rehearsal_id,
        "planned_trajectory_count": len(ledger.runs),
        "functional_run_count": functional_count,
        "runtime_run_count": runtime_count,
        "secondary_review_schedule_count": len(schedule.entries),
        "synthetic_evidence_only": True,
        "manifest_freeze_permitted": False,
        "final_measured_abc_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": record.next_gate,
    }


def _load_rubric(root: Path) -> BlindedQualityRubric:
    try:
        return BlindedQualityRubric.model_validate(_read_json_object(root / RUBRIC_PATH))
    except ValidationError as error:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_RUBRIC_INVALID",
            "frozen blinded-quality rubric failed validation",
        ) from error


def _completed_terminal(plan: producer.PlanBinding) -> producer.TrajectoryTerminalRecord:
    return producer.TrajectoryTerminalRecord(
        run_id=plan.run_id,
        trace_id=plan.trace_id,
        terminal_state=producer.TrajectoryTerminalState.COMPLETED,
        attempted_request_count=4,
        committed_turn_count=4,
    )


def _route_identity(
    plan: producer.PlanBinding,
    turn_index: int,
) -> core.CacheResidencyIdentity:
    return core.CacheResidencyIdentity(
        worker_id=core.realize_route(plan.route_schedule_id)[turn_index - 1],
        worker_generation=1,
        runtime_model_fingerprint=SYNTHETIC_RUNTIME_MODEL_FINGERPRINT,
    )


def _functional_execution_evidence(
    plan: producer.PlanBinding,
) -> tuple[
    tuple[producer.AttemptReservation, ...],
    tuple[producer.TransportOutcomeRecord, ...],
]:
    reservations: list[producer.AttemptReservation] = []
    outcomes: list[producer.TransportOutcomeRecord] = []
    for turn_index in range(1, 5):
        sequence = turn_index
        reservations.append(
            producer.AttemptReservation(
                global_attempt_sequence=sequence,
                run_id=plan.run_id,
                trace_id=plan.trace_id,
                turn_index=turn_index,
                attempt_index=1,
                logical_request_fingerprint=_sha(
                    f"offline-rehearsal|request|{plan.run_id}|{turn_index}"
                ),
                route_identity=_route_identity(plan, turn_index),
                retry_backoff_seconds=0,
            )
        )
        outcomes.append(
            producer.TransportOutcomeRecord(
                global_attempt_sequence=sequence,
                outcome=core.AttemptOutcome.SUCCEEDED,
                retryable=False,
                http_completed=True,
                http_status=200,
                response_sha256=_sha(f"offline-rehearsal|response|{plan.run_id}|{turn_index}"),
            )
        )
    return tuple(reservations), tuple(outcomes)


def _capture_object(
    run_id: str,
    episode_id: str,
    turn_index: int,
) -> review_successor.ProtectedTurnCapture:
    output: dict[str, object] = {
        "decision": "answer",
        "rehearsal_only": True,
        "turn_index": turn_index,
    }
    return review_successor.ProtectedTurnCapture(
        run_id=run_id,
        review_item_id=core.protected_review_id(run_id),
        episode_id=episode_id,
        turn_index=turn_index,
        user_message=f"offline-rehearsal-user-turn-{turn_index}",
        assistant_output=output,
        response_sha256=review_successor.sha256_bytes(
            review_successor.canonical_json_bytes(output)
        ),
    )


def _captures_for_run(
    run_id: str,
    episode_id: str,
) -> tuple[review_successor.ProtectedTurnCapture, ...]:
    return tuple(_capture_object(run_id, episode_id, turn_index) for turn_index in range(1, 5))


def _deterministic_quality_result(
    run_id: str,
    episode_id: str,
) -> DeterministicQualityResult:
    checks = tuple(
        QualityCheckResult(
            check_name=check_name,
            status=QualityCheckStatus.PASSED,
        )
        for check_name in QualityCheckName
    )
    return DeterministicQualityResult(
        trace_id=f"quality-trace-offline-rehearsal-{_sha(run_id)[:16]}",
        episode_id=episode_id,
        output_sha256=_sha(f"offline-rehearsal|candidate|{run_id}"),
        retrieval_configuration_fingerprint=SYNTHETIC_RETRIEVAL_FINGERPRINT,
        structured_output_valid=True,
        terminal_decision=TerminalDecision.ANSWER,
        checks=checks,
        failure_labels=(),
        deterministic_quality_passed=True,
    )


def _criterion_scores(run_id: str, role: ReviewRole) -> tuple[CriterionScore, ...]:
    return tuple(
        CriterionScore(
            criterion=criterion,
            score=3,
            evidence_note_sha256=_sha(
                f"offline-rehearsal|review-note|{run_id}|{role.value}|{criterion.value}"
            ),
        )
        for criterion in RubricCriterion
    )


def _review(
    run_id: str,
    episode_id: str,
    role: ReviewRole,
) -> QualityReviewRecord:
    if role is ReviewRole.PRIMARY:
        role_name: Literal["primary", "secondary"] = "primary"
    elif role is ReviewRole.SECONDARY:
        role_name = "secondary"
    else:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_REVIEW_ROLE_INVALID",
            "offline rehearsal only synthesizes primary and secondary review roles",
        )
    review_item_id = core.protected_review_id(run_id)
    return QualityReviewRecord(
        review_id=review_design.role_assignment_id(review_item_id, role_name),
        episode_id=episode_id,
        reviewer_id_sha256=_sha(f"offline-rehearsal|reviewer|{role_name}"),
        role=role,
        criterion_scores=_criterion_scores(run_id, role),
        failure_labels=(),
        verdict=ReviewVerdict.PASS,
        rationale_sha256=_sha(f"offline-rehearsal|rationale|{run_id}|{role_name}"),
    )


def _reduce_functional_quality(
    planned: core.PlannedRun,
    plan: producer.PlanBinding,
    schedule: review_successor.ProtectedSchedule,
    scheduled_secondary_run_ids: frozenset[str],
    rubric: BlindedQualityRubric,
) -> quality.MeasuredQualityRunResult:
    attempts, outcomes = _functional_execution_evidence(plan)
    secondary = (
        _review(plan.run_id, planned.episode_id, ReviewRole.SECONDARY)
        if plan.run_id in scheduled_secondary_run_ids
        else None
    )
    value = quality.MeasuredQualityRunInput(
        run_id=plan.run_id,
        episode_id=planned.episode_id,
        plan=plan,
        terminal=_completed_terminal(plan),
        attempt_reservations=attempts,
        transport_outcomes=outcomes,
        protected_captures=_captures_for_run(plan.run_id, planned.episode_id),
        deterministic_quality=_deterministic_quality_result(plan.run_id, planned.episode_id),
        primary_review=_review(plan.run_id, planned.episode_id, ReviewRole.PRIMARY),
        secondary_review=secondary,
        adjudication=None,
        rubric=rubric,
        review_schedule=schedule,
    )
    return quality.reduce_measured_quality_run(value)


def _warm_decision(
    planned: core.PlannedRun,
    turn_index: int,
) -> core.WarmEligibilityDecision:
    if turn_index == 1:
        return core.WarmEligibilityDecision(
            classification=core.WarmClassification.COLD,
            decision_code=core.WarmDecisionCode.FIRST_TURN_COLD,
        )
    if planned.condition_id is not core.ConditionId.C and turn_index == 2:
        return core.WarmEligibilityDecision(
            classification=core.WarmClassification.COLD,
            decision_code=core.WarmDecisionCode.NO_ELIGIBLE_PRIOR_REQUEST,
        )
    matched_prior = turn_index - 1 if planned.condition_id is core.ConditionId.C else turn_index - 2
    return core.WarmEligibilityDecision(
        classification=core.WarmClassification.WARM_ELIGIBLE,
        decision_code=core.WarmDecisionCode.PRIOR_ELIGIBLE_REQUEST_MATCHED,
        matched_prior_turn_index=matched_prior,
    )


def _primary_prefill_value(condition: core.ConditionId) -> int:
    return {
        core.ConditionId.A: 100,
        core.ConditionId.B: 80,
        core.ConditionId.C: 40,
    }[condition]


def _runtime_measurements(
    planned_runs: tuple[core.PlannedRun, ...],
    final_manifest_sha256: str,
) -> tuple[producer.TurnMeasurementRecord, ...]:
    measurements: list[producer.TurnMeasurementRecord] = []
    sequence = 1
    for planned in planned_runs:
        if planned.workload is not core.WorkloadId.RUNTIME_MICROBENCHMARK:
            continue
        route = core.realize_route(planned.route_schedule_id)
        namespace_sha = producer.sha256_text(planned.cache_namespace_id)
        for turn_index in range(1, 5):
            route_identity = core.CacheResidencyIdentity(
                worker_id=route[turn_index - 1],
                worker_generation=1,
                runtime_model_fingerprint=SYNTHETIC_RUNTIME_MODEL_FINGERPRINT,
            )
            warm_decision = _warm_decision(planned, turn_index)
            warm_evidence = core.WarmTurnEvidence(
                turn_index=turn_index,
                session_id_hash=_sha(f"offline-rehearsal|session|{planned.run_id}"),
                cache_namespace_sha256=namespace_sha,
                static_prefix_fingerprint=_sha(f"offline-rehearsal|prefix|{planned.run_id}"),
                residency_identity=route_identity,
                affinity_epoch=0,
                request_started_monotonic_ns=sequence * 10,
                request_completed_monotonic_ns=sequence * 10 + 1,
                request_completed=True,
            )
            warm_eligible = warm_decision.classification is core.WarmClassification.WARM_ELIGIBLE
            measurements.append(
                producer.TurnMeasurementRecord(
                    global_attempt_sequence=sequence,
                    run_id=planned.run_id,
                    trace_id=planned.trace_id,
                    turn_index=turn_index,
                    trace_identity=core.RuntimeTraceIdentity(
                        run_id=planned.run_id,
                        trace_id=planned.trace_id,
                        final_execution_manifest_sha256=final_manifest_sha256,
                    ),
                    route_identity=route_identity,
                    warm_evidence=warm_evidence,
                    warm_decision=warm_decision,
                    prompt_token_count=1000,
                    server_usage_prompt_tokens=1000,
                    cached_prefix_tokens=900 if warm_eligible else 0,
                    newly_computed_prefill_tokens=_primary_prefill_value(planned.condition_id),
                    prefill_duration_ms=10.0,
                    time_to_first_token_ms=20.0,
                    end_to_end_latency_ms=30.0,
                    finish_reason="stop",
                    output_sha256=_sha(
                        f"offline-rehearsal|runtime-output|{planned.run_id}|{turn_index}"
                    ),
                )
            )
            sequence += 1
    return tuple(measurements)


def _condition_identities() -> tuple[analysis.ConditionIdentity, ...]:
    return tuple(
        analysis.ConditionIdentity(
            condition_id=condition,
            retrieval_configuration_fingerprint=SYNTHETIC_RETRIEVAL_FINGERPRINT,
            episode_manifest_sha256=SYNTHETIC_EPISODE_MANIFEST_SHA256,
        )
        for condition in core.ConditionId
    )


def build_synthetic_analysis_input(repo_root: Path) -> analysis.Final342AnalysisInput:
    """Build exact-population synthetic evidence for integration mechanics only."""

    root = repo_root.resolve()
    validate_subject(root)
    ledger = core.load_runtime_plan(root)
    initial = producer.initial_state(
        root,
        transaction_id=SYNTHETIC_TRANSACTION_ID,
        final_execution_manifest_sha256=SYNTHETIC_FINAL_MANIFEST_SHA256,
    )
    planned_by_id = {item.run_id: item for item in ledger.runs}
    plans_by_id = {item.run_id: item for item in initial.plan_bindings}
    if set(planned_by_id) != set(plans_by_id):
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_PRODUCER_PLAN_COVERAGE_DRIFT",
            "producer initial state does not cover the exact frozen plan",
        )

    schedule = review_successor.derive_protected_schedule(root)
    scheduled_secondary_run_ids = frozenset(item.run_id for item in schedule.entries)
    rubric = _load_rubric(root)
    measured_quality_results = tuple(
        _reduce_functional_quality(
            planned,
            plans_by_id[planned.run_id],
            schedule,
            scheduled_secondary_run_ids,
            rubric,
        )
        for planned in ledger.runs
        if planned.workload is core.WorkloadId.FUNCTIONAL
    )
    if len(measured_quality_results) != EXPECTED_FUNCTIONAL_RUN_COUNT:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_QUALITY_POPULATION_INCOMPLETE",
            "offline rehearsal did not reduce all 162 functional trajectories",
        )
    if any(
        item.evidence_state is not quality.EvidenceState.COMPLETE or item.task_success is not True
        for item in measured_quality_results
    ):
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_QUALITY_REDUCTION_FAILED",
            "synthetic complete/pass quality evidence did not reduce to complete task success",
        )

    terminals = tuple(_completed_terminal(plans_by_id[item.run_id]) for item in ledger.runs)
    measurements = _runtime_measurements(
        ledger.runs,
        SYNTHETIC_FINAL_MANIFEST_SHA256,
    )
    if len(measurements) != EXPECTED_RUNTIME_MEASUREMENT_COUNT:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_RUNTIME_MEASUREMENT_COUNT_DRIFT",
            "offline rehearsal did not produce exactly 720 synthetic runtime measurements",
        )

    return analysis.Final342AnalysisInput(
        final_execution_manifest_sha256=SYNTHETIC_FINAL_MANIFEST_SHA256,
        bundle_verification=analysis.BundleVerification(
            receipt=producer.EvidenceBundleReceipt(
                bundle_manifest_sha256=_sha("offline-rehearsal|bundle-manifest"),
                evidence_archive_sha256=_sha("offline-rehearsal|evidence-archive"),
                member_count=8,
            ),
            schema_and_hash_verified=True,
        ),
        condition_identities=_condition_identities(),
        planned_runs=ledger.runs,
        plan_bindings=initial.plan_bindings,
        trace_bindings=initial.trace_bindings,
        trajectory_terminals=terminals,
        measurements=measurements,
        measured_quality_results=measured_quality_results,
    )


def _exercise_protected_review_round_trip(repo_root: Path) -> ProtectedReviewRoundTrip:
    root = repo_root.resolve()
    schedule = review_successor.derive_protected_schedule(root)
    if not schedule.entries:
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_SECONDARY_SCHEDULE_EMPTY",
            "protected secondary-review schedule is unexpectedly empty",
        )
    selected = schedule.entries[0]
    with tempfile.TemporaryDirectory(
        prefix="auragateway-final-342-offline-review-rehearsal-"
    ) as directory:
        protected_root = Path(directory)
        captures = tuple(
            review_successor.capture_transport_response(
                store_root=protected_root,
                transport_result=_SyntheticTransportResult(
                    response_object={
                        "decision": "answer",
                        "rehearsal_only": True,
                        "turn_index": turn_index,
                    },
                    response_json_object_valid=True,
                ),
                run_id=selected.run_id,
                episode_id=selected.episode_id,
                turn_index=turn_index,
                user_message=f"offline-rehearsal-user-turn-{turn_index}",
            )
            for turn_index in range(1, 5)
        )
        loaded = review_successor.load_captures(
            protected_root,
            core.protected_review_id(selected.run_id),
        )
        payloads = review_successor.build_reviewer_payloads(
            captures=loaded,
            schedule=schedule,
            deterministic_validation_summary={"rehearsal_only": True},
        )
        for payload in payloads:
            review_successor.assert_reviewer_safe(payload.model_dump(mode="python"))
        receipt = review_successor.write_protected_export(
            protected_root=protected_root,
            assignments=payloads,
        )

    if (
        len(captures) != EXPECTED_PROTECTED_CAPTURE_COUNT
        or len(loaded) != EXPECTED_PROTECTED_CAPTURE_COUNT
        or len(payloads) != EXPECTED_PROTECTED_ASSIGNMENT_COUNT
        or receipt.item_count != 1
    ):
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_PROTECTED_REVIEW_ROUND_TRIP_FAILED",
            "protected review capture/export round trip did not preserve expected shape",
        )
    return ProtectedReviewRoundTrip(
        scheduled_secondary_run_id=selected.run_id,
        capture_count=EXPECTED_PROTECTED_CAPTURE_COUNT,
        loaded_capture_count=EXPECTED_PROTECTED_CAPTURE_COUNT,
        reviewer_assignment_count=EXPECTED_PROTECTED_ASSIGNMENT_COUNT,
        public_receipt_item_count=1,
        reviewer_payload_safe=True,
    )


def rehearse(repo_root: Path) -> OfflineRehearsalSummary:
    """Run the deterministic, non-authorizing end-to-end integration rehearsal."""

    root = repo_root.resolve()
    subject = validate_subject(root)
    protected_round_trip = _exercise_protected_review_round_trip(root)
    value = build_synthetic_analysis_input(root)
    result = analysis.analyze_final_342(value)

    eligible_pairs = tuple(item.eligible_pair_count for item in result.runtime_contrasts)
    decisions = tuple(item.decision.value for item in result.claim_decisions)
    if (
        result.evidence_state is not analysis.AnalysisEvidenceState.COMPLETE
        or not result.run_accountability.accountability_complete
        or result.quality_noninferiority.state is not analysis.QualityGateState.PASSED
        or eligible_pairs != (60, 60, 60)
        or decisions != ("SUPPORTED", "SUPPORTED", "SUPPORTED")
    ):
        raise OfflineRehearsalError(
            "FINAL_342_OFFLINE_REHEARSAL_ANALYSIS_COMPOSITION_FAILED",
            "synthetic complete/pass evidence did not traverse the final analysis path",
        )

    return OfflineRehearsalSummary(
        status="FINAL_342_OFFLINE_ORCHESTRATION_INTEGRATION_REHEARSAL_PASS",
        planned_trajectory_count=EXPECTED_TRAJECTORY_COUNT,
        functional_run_count=EXPECTED_FUNCTIONAL_RUN_COUNT,
        runtime_run_count=EXPECTED_RUNTIME_RUN_COUNT,
        producer_plan_binding_count=len(value.plan_bindings),
        producer_trace_binding_count=len(value.trace_bindings),
        secondary_review_schedule_count=cast(int, subject["secondary_review_schedule_count"]),
        protected_review_round_trip=protected_round_trip,
        measured_quality_result_count=len(value.measured_quality_results),
        runtime_measurement_count=len(value.measurements),
        runtime_contrast_count=len(result.runtime_contrasts),
        eligible_pairs_per_contrast=(60, 60, 60),
        synthetic_analysis_evidence_complete=True,
        synthetic_quality_gate_passed=True,
        synthetic_mechanics_claim_decisions=("SUPPORTED", "SUPPORTED", "SUPPORTED"),
        synthetic_results_are_scientific_evidence=False,
        synthetic_effect_claims_authoritative=False,
        model_requests_performed=0,
        gpu_execution_performed=False,
        kaggle_execution_performed=False,
        network_transport_performed=False,
        execution_manifest_frozen=False,
        manifest_freeze_permitted=False,
        final_measured_abc_execution_authorized=False,
        new_execution_authorized=False,
        effect_claims_permitted=False,
        next_gate=NEXT_GATE,
    )


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate the implemented rehearsal by executing its offline composition path."""

    summary = rehearse(repo_root)
    return summary.model_dump(mode="json")


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser(prog="final-342-offline-orchestration-integration-rehearsal-v1")
    parser.add_argument("command", choices=("rehearse", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = (
            rehearse(args.repo_root).model_dump(mode="json")
            if args.command == "rehearse"
            else validate_implementation(args.repo_root)
        )
    except OfflineRehearsalError as error:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "error_code": error.error_code,
                    "safe_message": error.safe_message,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
