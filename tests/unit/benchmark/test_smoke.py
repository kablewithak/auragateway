from __future__ import annotations

from auragateway.benchmark.smoke import (
    build_controlled_smoke,
    execute_controlled_smoke,
)
from auragateway.contracts.benchmark_smoke import (
    ControlledSmokeAuthorization,
    EpisodeSetProjection,
    ScriptedSmokeFixtureSet,
    SmokePlanLedgerProjection,
)
from auragateway.contracts.evidence_bundle import RunTerminalStatus

SmokeInputs = tuple[
    ControlledSmokeAuthorization,
    ScriptedSmokeFixtureSet,
    SmokePlanLedgerProjection,
    EpisodeSetProjection,
]


def test_controlled_smoke_exercises_success_retry_and_ambiguity(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    records, report, reused = build_controlled_smoke(authorization, fixtures, plan, episodes)
    assert reused == 0
    assert [item.terminal_status for item in records.terminal_records] == [
        RunTerminalStatus.COMPLETED,
        RunTerminalStatus.COMPLETED,
        RunTerminalStatus.ABORTED_SAFETY_CONTROL,
    ]
    assert records.total_attempt_count == 11
    assert report.retry_authorized_count == 1
    assert report.ambiguous_retry_blocked_count == 1
    assert report.smoke_passed is True


def test_resume_preserves_all_terminal_records(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    first, _, _ = build_controlled_smoke(authorization, fixtures, plan, episodes)
    resumed, reused = execute_controlled_smoke(authorization, fixtures, plan, episodes, first)
    assert reused == 3
    assert resumed == first


def test_partial_resume_preserves_existing_record_identity(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    complete, _, _ = build_controlled_smoke(authorization, fixtures, plan, episodes)
    partial = complete.model_copy(
        update={
            "terminal_records": complete.terminal_records[:1],
            "attempt_records": complete.attempt_records[:4],
            "total_attempt_count": 4,
            "total_estimated_cost_microusd": sum(
                item.estimated_cost_microusd for item in complete.attempt_records[:4]
            ),
        }
    )
    resumed, reused = execute_controlled_smoke(authorization, fixtures, plan, episodes, partial)
    assert reused == 1
    assert resumed.terminal_records[0] == partial.terminal_records[0]
    assert len(resumed.terminal_records) == 3


def test_attempt_budget_kill_switch_blocks_later_run(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    constrained = ControlledSmokeAuthorization.model_validate(
        {
            **authorization.model_dump(mode="json"),
            "maximum_total_attempt_count": 10,
        }
    )
    records, report, _ = build_controlled_smoke(constrained, fixtures, plan, episodes)
    assert records.terminal_records[-1].terminal_status is RunTerminalStatus.BUDGET_EXHAUSTED
    assert report.attempt_budget_respected is True
    assert report.smoke_passed is False


def test_cost_budget_kill_switch_blocks_before_overspend(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    constrained = ControlledSmokeAuthorization.model_validate(
        {
            **authorization.model_dump(mode="json"),
            "maximum_total_cost_microusd": 1000,
        }
    )
    records, report, _ = build_controlled_smoke(constrained, fixtures, plan, episodes)
    assert records.total_estimated_cost_microusd <= 1000
    assert any(
        item.terminal_status is RunTerminalStatus.BUDGET_EXHAUSTED
        for item in records.terminal_records
    )
    assert report.smoke_passed is False


def test_held_out_episode_is_blocked(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, _ = controlled_smoke_inputs
    held_out = EpisodeSetProjection.model_validate(
        {"episodes": [{"episode_id": "ep-func-001", "evaluation_split": "held_out"}]}
    )
    import pytest

    from auragateway.benchmark.smoke import ControlledSmokeError

    with pytest.raises(ControlledSmokeError, match="development episodes only"):
        build_controlled_smoke(authorization, fixtures, plan, held_out)


def test_duplicate_cache_namespace_is_blocked(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    runs = list(plan.runs)
    runs[1] = runs[1].model_copy(update={"cache_namespace_id": runs[0].cache_namespace_id})
    invalid_plan = SmokePlanLedgerProjection(plan_id=plan.plan_id, runs=tuple(runs))
    import pytest

    from auragateway.benchmark.smoke import ControlledSmokeError

    with pytest.raises(ControlledSmokeError, match="distinct condition cache namespaces"):
        build_controlled_smoke(authorization, fixtures, invalid_plan, episodes)


def test_fixture_scope_must_match_authorized_runs(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    _, fixtures, _, _ = controlled_smoke_inputs
    payload = fixtures.model_dump(mode="json")
    payload["scenarios"] = [
        fixtures.scenarios[0].model_dump(mode="json"),
        fixtures.scenarios[1].model_dump(mode="json"),
        fixtures.scenarios[1].model_dump(mode="json"),
    ]
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="scenario run IDs must be unique"):
        ScriptedSmokeFixtureSet.model_validate(payload)
