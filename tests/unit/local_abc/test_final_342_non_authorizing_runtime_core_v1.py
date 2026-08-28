from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

ROOT = Path(__file__).resolve().parents[3]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _residency(
    worker_id: core.WorkerId = core.WorkerId.WORKER_1,
    generation: int = 1,
) -> core.CacheResidencyIdentity:
    return core.CacheResidencyIdentity(
        worker_id=worker_id,
        worker_generation=generation,
        runtime_model_fingerprint=_sha("runtime-model"),
    )


def _warm_evidence(
    *,
    turn_index: int,
    worker_id: core.WorkerId = core.WorkerId.WORKER_1,
    generation: int = 1,
    prefix: str | None = None,
    epoch: int = 0,
    started_ns: int,
    completed_ns: int | None,
    completed: bool,
) -> core.WarmTurnEvidence:
    return core.WarmTurnEvidence(
        turn_index=turn_index,
        session_id_hash=_sha("session"),
        cache_namespace_sha256=_sha("namespace"),
        static_prefix_fingerprint=_sha("prefix") if prefix is None else prefix,
        residency_identity=_residency(worker_id, generation),
        affinity_epoch=epoch,
        request_started_monotonic_ns=started_ns,
        request_completed_monotonic_ns=completed_ns,
        request_completed=completed,
    )


def test_frozen_ledger_realizes_exact_final_run_shape() -> None:
    ledger = core.load_runtime_plan(ROOT)

    assert len(ledger.runs) == 342
    assert ledger.total_turn_count == 1368
    assert ledger.maximum_request_attempt_count == 2736
    assert ledger.functional_trajectory_count == 162
    assert ledger.runtime_trajectory_count == 180

    first = ledger.runs[0]
    turns = core.realize_run(first)
    assert [turn.worker_id for turn in turns] == [
        core.WorkerId.WORKER_1,
        core.WorkerId.WORKER_2,
        core.WorkerId.WORKER_1,
        core.WorkerId.WORKER_2,
    ]
    assert len({turn.session_id_hash for turn in turns}) == 1


def test_affinity_route_realizes_worker_one_for_all_turns() -> None:
    ledger = core.load_runtime_plan(ROOT)
    affinity = next(
        run for run in ledger.runs if run.route_schedule_id is core.RouteScheduleId.AFFINITY
    )

    assert [turn.worker_id for turn in core.realize_run(affinity)] == [
        core.WorkerId.WORKER_1,
        core.WorkerId.WORKER_1,
        core.WorkerId.WORKER_1,
        core.WorkerId.WORKER_1,
    ]


def test_session_and_protected_review_ids_are_deterministic_and_distinct() -> None:
    run_id = "run-functional-ep-func-001-r01-condition-a"

    assert core.session_id_hash(run_id) == core.session_id_hash(run_id)
    assert core.protected_review_id(run_id) == core.protected_review_id(run_id)
    assert core.session_id_hash(run_id) != core.protected_review_id(run_id)


def test_first_turn_is_cold() -> None:
    current = _warm_evidence(
        turn_index=1,
        started_ns=100,
        completed_ns=None,
        completed=False,
    )

    decision = core.classify_warm_eligibility(current, ())

    assert decision.classification is core.WarmClassification.COLD
    assert decision.decision_code is core.WarmDecisionCode.FIRST_TURN_COLD


def test_turn_two_is_warm_when_exact_prior_cache_domain_matches() -> None:
    prior = _warm_evidence(
        turn_index=1,
        started_ns=100,
        completed_ns=200,
        completed=True,
    )
    current = _warm_evidence(
        turn_index=2,
        started_ns=300,
        completed_ns=None,
        completed=False,
    )

    decision = core.classify_warm_eligibility(current, (prior,))

    assert decision.classification is core.WarmClassification.WARM_ELIGIBLE
    assert decision.matched_prior_turn_index == 1


def test_turn_local_turn_two_is_cold_when_worker_cache_domain_differs() -> None:
    prior = _warm_evidence(
        turn_index=1,
        worker_id=core.WorkerId.WORKER_1,
        started_ns=100,
        completed_ns=200,
        completed=True,
    )
    current = _warm_evidence(
        turn_index=2,
        worker_id=core.WorkerId.WORKER_2,
        started_ns=300,
        completed_ns=None,
        completed=False,
    )

    decision = core.classify_warm_eligibility(current, (prior,))

    assert decision.classification is core.WarmClassification.COLD
    assert decision.decision_code is core.WarmDecisionCode.NO_ELIGIBLE_PRIOR_REQUEST


def test_turn_three_can_match_turn_one_without_immediate_prior_match() -> None:
    turn_one = _warm_evidence(
        turn_index=1,
        worker_id=core.WorkerId.WORKER_1,
        started_ns=100,
        completed_ns=200,
        completed=True,
    )
    turn_two = _warm_evidence(
        turn_index=2,
        worker_id=core.WorkerId.WORKER_2,
        started_ns=300,
        completed_ns=400,
        completed=True,
    )
    turn_three = _warm_evidence(
        turn_index=3,
        worker_id=core.WorkerId.WORKER_1,
        started_ns=500,
        completed_ns=None,
        completed=False,
    )

    decision = core.classify_warm_eligibility(
        turn_three,
        (turn_one, turn_two),
    )

    assert decision.classification is core.WarmClassification.WARM_ELIGIBLE
    assert decision.matched_prior_turn_index == 1


def test_worker_generation_drift_prevents_warm_match() -> None:
    prior = _warm_evidence(
        turn_index=1,
        generation=1,
        started_ns=100,
        completed_ns=200,
        completed=True,
    )
    current = _warm_evidence(
        turn_index=2,
        generation=2,
        started_ns=300,
        completed_ns=None,
        completed=False,
    )

    decision = core.classify_warm_eligibility(current, (prior,))

    assert decision.classification is core.WarmClassification.COLD


def test_missing_prefix_evidence_is_ambiguous() -> None:
    current = core.WarmTurnEvidence(
        turn_index=2,
        session_id_hash=_sha("session"),
        cache_namespace_sha256=_sha("namespace"),
        static_prefix_fingerprint=None,
        residency_identity=_residency(),
        affinity_epoch=0,
        request_started_monotonic_ns=300,
        request_completed=False,
    )

    decision = core.classify_warm_eligibility(current, ())

    assert decision.classification is core.WarmClassification.UNAVAILABLE_OR_AMBIGUOUS


def test_retry_is_authorized_only_after_retryable_definite_failure() -> None:
    route = _residency()
    fingerprint = _sha("logical-request")
    first = core.RetryAttemptEvidence(
        attempt_index=1,
        logical_request_fingerprint=fingerprint,
        route_identity=route,
        outcome=core.AttemptOutcome.DEFINITE_FAILURE,
        retryable=True,
    )

    decision = core.authorize_retry(
        (first,),
        proposed_logical_request_fingerprint=fingerprint,
        proposed_route_identity=route,
    )

    assert decision.authorized is True
    assert decision.authorized_attempt_index == 2
    assert decision.retry_backoff_seconds == 2


def test_ambiguous_attempt_blocks_retry() -> None:
    route = _residency()
    fingerprint = _sha("logical-request")
    first = core.RetryAttemptEvidence(
        attempt_index=1,
        logical_request_fingerprint=fingerprint,
        route_identity=route,
        outcome=core.AttemptOutcome.AMBIGUOUS,
        retryable=False,
    )

    decision = core.authorize_retry(
        (first,),
        proposed_logical_request_fingerprint=fingerprint,
        proposed_route_identity=route,
    )

    assert decision.authorized is False
    assert decision.decision_code is core.RetryDecisionCode.BLOCKED_AMBIGUOUS_DUPLICATE_RISK


def test_second_failure_exhausts_retry_budget() -> None:
    route = _residency()
    fingerprint = _sha("logical-request")
    attempts = (
        core.RetryAttemptEvidence(
            attempt_index=1,
            logical_request_fingerprint=fingerprint,
            route_identity=route,
            outcome=core.AttemptOutcome.NO_RESPONSE,
            retryable=True,
        ),
        core.RetryAttemptEvidence(
            attempt_index=2,
            logical_request_fingerprint=fingerprint,
            route_identity=route,
            outcome=core.AttemptOutcome.DEFINITE_FAILURE,
            retryable=True,
        ),
    )

    decision = core.authorize_retry(
        attempts,
        proposed_logical_request_fingerprint=fingerprint,
        proposed_route_identity=route,
    )

    assert decision.authorized is False
    assert decision.decision_code is core.RetryDecisionCode.BLOCKED_RETRY_BUDGET_EXHAUSTED


@pytest.mark.parametrize(
    ("evidence", "expected"),
    (
        (
            core.TurnAdmissionEvidence(
                turn_index=1,
                current_prompt_budget_valid=False,
                finish_reason="stop",
                schema_admitted=True,
                has_next_turn=True,
                next_prompt_reachable=True,
            ),
            core.CommitDecisionCode.BLOCKED_CURRENT_PROMPT_BUDGET,
        ),
        (
            core.TurnAdmissionEvidence(
                turn_index=1,
                current_prompt_budget_valid=True,
                finish_reason="length",
                schema_admitted=True,
                has_next_turn=True,
                next_prompt_reachable=True,
            ),
            core.CommitDecisionCode.BLOCKED_FINISH_REASON,
        ),
        (
            core.TurnAdmissionEvidence(
                turn_index=1,
                current_prompt_budget_valid=True,
                finish_reason="stop",
                schema_admitted=False,
                has_next_turn=True,
                next_prompt_reachable=True,
            ),
            core.CommitDecisionCode.BLOCKED_SCHEMA_ADMISSION,
        ),
        (
            core.TurnAdmissionEvidence(
                turn_index=1,
                current_prompt_budget_valid=True,
                finish_reason="stop",
                schema_admitted=True,
                has_next_turn=True,
                next_prompt_reachable=False,
            ),
            core.CommitDecisionCode.BLOCKED_NEXT_PROMPT_REACHABILITY,
        ),
    ),
)
def test_failed_admission_gates_never_authorize_history_mutation(
    evidence: core.TurnAdmissionEvidence,
    expected: core.CommitDecisionCode,
) -> None:
    decision = core.evaluate_turn_commit(evidence)

    assert decision.decision_code is expected
    assert decision.history_mutation_permitted is False


def test_terminal_turn_can_commit_without_next_prompt_probe() -> None:
    evidence = core.TurnAdmissionEvidence(
        turn_index=4,
        current_prompt_budget_valid=True,
        finish_reason="stop",
        schema_admitted=True,
        has_next_turn=False,
        next_prompt_reachable=None,
    )

    decision = core.evaluate_turn_commit(evidence)

    assert decision.decision_code is core.CommitDecisionCode.COMMIT_AUTHORIZED
    assert decision.history_mutation_permitted is True


def test_request_counters_reject_non_monotonic_accounting() -> None:
    with pytest.raises(ValidationError):
        core.RequestCounters(
            scheduled_request_count=8,
            attempted_request_count=2,
            http_completed_request_count=1,
            admitted_request_count=2,
            committed_request_count=1,
        )


def test_primary_failure_survives_cleanup_and_packaging_failures() -> None:
    state = core.FailureState()
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

    state = core.record_failure(state, primary)
    state = core.record_failure(state, cleanup)
    state = core.record_failure(state, packaging)

    assert state.primary_failure == primary
    assert state.secondary_failures == (cleanup, packaging)


def test_public_protected_review_receipt_cannot_expose_raw_content() -> None:
    receipt = core.ProtectedReviewPublicReceipt(
        export_sha256=_sha("protected-export"),
        item_count=162,
        retention_and_deletion_rule_bound=True,
    )

    assert receipt.protected_export_root == core.PROTECTED_REVIEW_ROOT
    assert receipt.raw_prompts_in_public_evidence is False
    assert receipt.raw_outputs_in_public_evidence is False
    assert receipt.raw_provider_payloads_in_public_evidence is False


def test_runtime_trace_requires_distinct_final_execution_manifest_identity() -> None:
    with pytest.raises(ValidationError):
        core.RuntimeTraceIdentity(
            run_id="run-functional-ep-func-001-r01-condition-a",
            trace_id="trace",
            final_execution_manifest_sha256=core.EXPECTED_PLANNING_MANIFEST_SHA256,
        )


def test_core_validation_is_non_authorizing() -> None:
    result = core.validate(ROOT)

    assert result["status"] == "FINAL_342_NON_AUTHORIZING_RUNTIME_CORE_V1_VALID"
    assert result["planned_trajectories"] == 342
    assert result["realized_turns"] == 1368
    assert result["maximum_request_attempts"] == 2736
    assert result["model_requests_performed"] == 0
    assert result["gpu_execution_performed"] is False
    assert result["kaggle_execution_performed"] is False
    assert result["execution_manifest_frozen"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["new_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
    assert result["next_gate"] == "REHEARSE_FINAL_342_TRANSACTION_WRAPPER_V1"


def test_current_session_reset_invalidates_warm_eligibility() -> None:
    prior = _warm_evidence(
        turn_index=1,
        started_ns=100,
        completed_ns=200,
        completed=True,
    )
    current = _warm_evidence(
        turn_index=2,
        started_ns=300,
        completed_ns=None,
        completed=False,
    ).model_copy(update={"session_reset": True})

    decision = core.classify_warm_eligibility(current, (prior,))

    assert decision.classification is core.WarmClassification.COLD


def test_current_benchmark_transition_invalidates_warm_eligibility() -> None:
    prior = _warm_evidence(
        turn_index=1,
        started_ns=100,
        completed_ns=200,
        completed=True,
    )
    current = _warm_evidence(
        turn_index=2,
        started_ns=300,
        completed_ns=None,
        completed=False,
    ).model_copy(update={"benchmark_transition": True})

    decision = core.classify_warm_eligibility(current, (prior,))

    assert decision.classification is core.WarmClassification.COLD
