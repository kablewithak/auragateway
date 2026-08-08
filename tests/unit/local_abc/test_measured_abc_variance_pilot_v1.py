from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import measured_abc_variance_pilot_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def test_selector_produces_six_non_runtime_development_cases() -> None:
    cases = subject.select_pilot_cases(ROOT)
    assert len(cases) == 6
    runtime_ids = subject._runtime_ids(ROOT)
    assert all(item.evaluation_split == "development" for item in cases)
    assert all(item.episode_id not in runtime_ids for item in cases)
    assert tuple(item.episode_id for item in cases) == tuple(
        sorted(item.episode_id for item in cases)
    )


def test_schedule_is_exact_and_counterbalanced() -> None:
    schedule = subject.build_schedule(ROOT)
    assert schedule.case_count == 6
    assert schedule.trajectory_count == 54
    assert schedule.turn_count == 216
    assert schedule.maximum_request_attempt_count == 432
    assert tuple(item.schedule_index for item in schedule.trajectories) == tuple(range(54))


def test_each_case_has_three_runs_per_condition() -> None:
    schedule = subject.build_schedule(ROOT)
    for case in schedule.cases:
        rows = [row for row in schedule.trajectories if row.episode_id == case.episode_id]
        assert len(rows) == 9
        assert sum(row.condition_id.value == "A" for row in rows) == 3
        assert sum(row.condition_id.value == "B" for row in rows) == 3
        assert sum(row.condition_id.value == "C" for row in rows) == 3


def test_schedule_uses_unique_namespaces() -> None:
    schedule = subject.build_schedule(ROOT)
    namespaces = [item.cache_namespace_id for item in schedule.trajectories]
    assert len(namespaces) == len(set(namespaces))


def test_manifest_does_not_authorize_execution() -> None:
    schedule = subject.build_schedule(ROOT)
    manifest = subject.build_manifest(schedule)
    assert manifest.variance_pilot_execution_authorized is False
    assert manifest.final_measured_abc_execution_authorized is False


def test_implementation_validation_does_not_authorize_execution() -> None:
    result = subject.validate_implementation(ROOT)
    assert result["implementation_status"] == "IMPLEMENTED_NOT_AUTHORIZED"
    assert result["pilot_execution_authorized"] is False
    assert result["final_measured_abc_execution_authorized"] is False
