from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import measured_abc_variance_pilot_v2 as subject
from auragateway.local_abc.contracts import ConditionId, WorkerId

ROOT = Path(__file__).resolve().parents[3]


def _pair_rows(
    schedule: subject.PilotScheduleV2,
    pair_index: int,
) -> list[subject.PilotTrajectoryV2]:
    return sorted(
        [
            item
            for item in schedule.trajectories
            if item.comparison_pair_index == pair_index
        ],
        key=lambda item: item.condition_order_index,
    )


def _passing_neutral_samples(
    plan: subject.NeutralWorkerQualificationPlan,
) -> tuple[subject.NeutralWorkerSample, ...]:
    samples: list[subject.NeutralWorkerSample] = []
    for request in plan.requests:
        if not request.measured_for_worker_symmetry:
            continue
        assert request.measurement_pair_index is not None
        assert request.pair_order_index is not None
        base = 100.0 if request.worker_id is WorkerId.WORKER_1 else 105.0
        samples.append(
            subject.NeutralWorkerSample(
                measurement_pair_index=request.measurement_pair_index,
                pair_order_index=request.pair_order_index,
                worker_id=request.worker_id,
                admitted=True,
                telemetry_valid=True,
                time_to_first_token_ms=base,
                prefill_duration_ms=base,
            )
        )
    return tuple(samples)


def test_schedule_reuses_exact_accepted_v1_case_set() -> None:
    schedule = subject.build_schedule(ROOT)
    assert schedule.case_count == 6
    assert schedule.comparison_pair_count == 18
    assert schedule.trajectory_count == 54
    assert schedule.pilot_turn_count == 216
    assert schedule.hidden_retries_permitted is False
    assert schedule.replacement_cases_permitted is False
    assert schedule.pilot_execution_authorized is False
    assert schedule.final_measured_abc_execution_authorized is False
    assert tuple(item.episode_id for item in schedule.cases) == tuple(
        sorted(item.episode_id for item in schedule.cases)
    )


def test_schedule_uses_exact_replication_condition_orders() -> None:
    schedule = subject.build_schedule(ROOT)
    expected = {
        1: (ConditionId.A, ConditionId.B, ConditionId.C),
        2: (ConditionId.B, ConditionId.C, ConditionId.A),
        3: (ConditionId.C, ConditionId.A, ConditionId.B),
    }
    for pair_index in range(18):
        rows = _pair_rows(schedule, pair_index)
        assert len(rows) == 3
        assert tuple(item.condition_id for item in rows) == expected[
            rows[0].replication_index
        ]


def test_schedule_rotates_cases_and_balances_worker_orientation() -> None:
    schedule = subject.build_schedule(ROOT)
    case_ids = tuple(item.episode_id for item in schedule.cases)
    expected_case_orders = {
        1: case_ids,
        2: case_ids[2:] + case_ids[:2],
        3: case_ids[4:] + case_ids[:4],
    }
    expected_orientation_pattern = (
        subject.WorkerOrientation.ORIENTATION_1,
        subject.WorkerOrientation.ORIENTATION_2,
        subject.WorkerOrientation.ORIENTATION_2,
        subject.WorkerOrientation.ORIENTATION_1,
        subject.WorkerOrientation.ORIENTATION_1,
        subject.WorkerOrientation.ORIENTATION_2,
    )
    pair_representatives = [
        _pair_rows(schedule, pair_index)[0] for pair_index in range(18)
    ]
    for replication_index in (1, 2, 3):
        rows = [
            item
            for item in pair_representatives
            if item.replication_index == replication_index
        ]
        rows = sorted(rows, key=lambda item: item.case_order_position)
        assert tuple(item.episode_id for item in rows) == expected_case_orders[
            replication_index
        ]
        assert tuple(item.worker_orientation for item in rows) == (
            expected_orientation_pattern
        )
        assert sum(
            item.worker_orientation is subject.WorkerOrientation.ORIENTATION_1
            for item in rows
        ) == 3
        assert sum(
            item.worker_orientation is subject.WorkerOrientation.ORIENTATION_2
            for item in rows
        ) == 3

    assert sum(
        item.worker_orientation is subject.WorkerOrientation.ORIENTATION_1
        for item in pair_representatives
    ) == 9
    assert sum(
        item.worker_orientation is subject.WorkerOrientation.ORIENTATION_2
        for item in pair_representatives
    ) == 9


def test_each_case_observes_both_orientations_and_all_order_bands() -> None:
    schedule = subject.build_schedule(ROOT)
    pair_representatives = [
        _pair_rows(schedule, pair_index)[0] for pair_index in range(18)
    ]
    for case in schedule.cases:
        rows = [
            item for item in pair_representatives if item.episode_id == case.episode_id
        ]
        assert len(rows) == 3
        assert {item.worker_orientation for item in rows} == set(
            subject.WorkerOrientation
        )
        assert {(item.case_order_position - 1) // 2 for item in rows} == {0, 1, 2}


@pytest.mark.parametrize(
    ("orientation", "condition_id", "expected"),
    [
        (
            subject.WorkerOrientation.ORIENTATION_1,
            ConditionId.A,
            (
                WorkerId.WORKER_1,
                WorkerId.WORKER_2,
                WorkerId.WORKER_1,
                WorkerId.WORKER_2,
            ),
        ),
        (
            subject.WorkerOrientation.ORIENTATION_1,
            ConditionId.B,
            (
                WorkerId.WORKER_1,
                WorkerId.WORKER_2,
                WorkerId.WORKER_1,
                WorkerId.WORKER_2,
            ),
        ),
        (
            subject.WorkerOrientation.ORIENTATION_1,
            ConditionId.C,
            (
                WorkerId.WORKER_1,
                WorkerId.WORKER_1,
                WorkerId.WORKER_1,
                WorkerId.WORKER_1,
            ),
        ),
        (
            subject.WorkerOrientation.ORIENTATION_2,
            ConditionId.A,
            (
                WorkerId.WORKER_2,
                WorkerId.WORKER_1,
                WorkerId.WORKER_2,
                WorkerId.WORKER_1,
            ),
        ),
        (
            subject.WorkerOrientation.ORIENTATION_2,
            ConditionId.B,
            (
                WorkerId.WORKER_2,
                WorkerId.WORKER_1,
                WorkerId.WORKER_2,
                WorkerId.WORKER_1,
            ),
        ),
        (
            subject.WorkerOrientation.ORIENTATION_2,
            ConditionId.C,
            (
                WorkerId.WORKER_2,
                WorkerId.WORKER_2,
                WorkerId.WORKER_2,
                WorkerId.WORKER_2,
            ),
        ),
    ],
)
def test_routes_match_frozen_worker_orientation(
    orientation: subject.WorkerOrientation,
    condition_id: ConditionId,
    expected: tuple[WorkerId, WorkerId, WorkerId, WorkerId],
) -> None:
    assert subject.route_for(condition_id, orientation) == expected


def test_v1_style_condition_c_always_worker_1_is_rejected() -> None:
    schedule = subject.build_schedule(ROOT)
    payload = schedule.model_dump(mode="json")
    trajectories = payload["trajectories"]
    assert isinstance(trajectories, list)
    changed = False
    for row in trajectories:
        assert isinstance(row, dict)
        if (
            row["condition_id"] == "C"
            and row["worker_orientation"] == "orientation_2"
        ):
            row["realized_route"] = ["worker_1"] * 4
            changed = True
            break
    assert changed
    with pytest.raises(ValidationError, match="realized route"):
        subject.PilotScheduleV2.model_validate(payload)


def test_pre_treatment_plan_is_exact_and_separate_from_pilot_namespaces() -> None:
    plan = subject.build_neutral_worker_plan()
    schedule = subject.build_schedule(ROOT)

    assert plan.pre_treatment_request_count == 24
    assert plan.schema_canary_request_count == 2
    assert plan.warmup_request_count == 2
    assert plan.measured_request_count == 20
    assert plan.hidden_retries_permitted is False
    assert plan.pilot_execution_authorized is False

    canary = [
        item
        for item in plan.requests
        if item.phase is subject.PreTreatmentPhase.SCHEMA_CANARY
    ]
    warmup = [
        item
        for item in plan.requests
        if item.phase is subject.PreTreatmentPhase.WARMUP
    ]
    measured = [item for item in plan.requests if item.measured_for_worker_symmetry]

    assert [item.worker_id for item in canary] == [
        WorkerId.WORKER_1,
        WorkerId.WORKER_2,
    ]
    assert [item.worker_id for item in warmup] == [
        WorkerId.WORKER_2,
        WorkerId.WORKER_1,
    ]
    assert len(measured) == 20
    assert sum(
        item.pair_order_index == 0 and item.worker_id is WorkerId.WORKER_1
        for item in measured
    ) == 5
    assert sum(
        item.pair_order_index == 0 and item.worker_id is WorkerId.WORKER_2
        for item in measured
    ) == 5

    pre_namespaces = {item.cache_namespace_id for item in plan.requests}
    pilot_namespaces = {item.cache_namespace_id for item in schedule.trajectories}
    assert pre_namespaces.isdisjoint(pilot_namespaces)


def test_neutral_worker_qualification_passes_symmetric_support() -> None:
    plan = subject.build_neutral_worker_plan()
    assessment = subject.assess_neutral_worker_qualification(
        plan,
        _passing_neutral_samples(plan),
    )
    assert assessment.decision == "PASS"
    assert assessment.observed_sample_count == 20
    assert assessment.worker_1_sample_count == 10
    assert assessment.worker_2_sample_count == 10
    assert assessment.worker_median_ttft_ratio == pytest.approx(1.05)
    assert assessment.worker_median_prefill_ratio == pytest.approx(1.05)
    assert assessment.blocking_reasons == ()


def test_neutral_worker_qualification_blocks_gross_asymmetry() -> None:
    plan = subject.build_neutral_worker_plan()
    samples = list(_passing_neutral_samples(plan))
    samples = [
        item.model_copy(
            update={
                "time_to_first_token_ms": (
                    150.0 if item.worker_id is WorkerId.WORKER_2 else 100.0
                ),
                "prefill_duration_ms": (
                    150.0 if item.worker_id is WorkerId.WORKER_2 else 100.0
                ),
            }
        )
        for item in samples
    ]
    assessment = subject.assess_neutral_worker_qualification(plan, tuple(samples))
    assert assessment.decision == "FAIL"
    assert "NEUTRAL_TTFT_ASYMMETRY_EXCEEDED" in assessment.blocking_reasons
    assert "NEUTRAL_PREFILL_ASYMMETRY_EXCEEDED" in assessment.blocking_reasons


def test_neutral_worker_qualification_blocks_missing_support() -> None:
    plan = subject.build_neutral_worker_plan()
    samples = _passing_neutral_samples(plan)[:-1]
    assessment = subject.assess_neutral_worker_qualification(plan, samples)
    assert assessment.decision == "FAIL"
    assert "NEUTRAL_SAMPLE_SET_INCOMPLETE" in assessment.blocking_reasons


def test_neutral_worker_qualification_rejects_duplicate_identity() -> None:
    plan = subject.build_neutral_worker_plan()
    samples = _passing_neutral_samples(plan)
    with pytest.raises(subject.VariancePilotV2ContractError) as observed:
        subject.assess_neutral_worker_qualification(
            plan,
            (*samples[:-1], samples[0]),
        )
    assert observed.value.error_code == "V2_NEUTRAL_SAMPLE_DUPLICATE"
