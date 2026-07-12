from __future__ import annotations

from auragateway.benchmark.smoke import build_controlled_smoke
from auragateway.contracts.benchmark_smoke import (
    ControlledSmokeAuthorization,
    EpisodeSetProjection,
    ScriptedSmokeFixtureSet,
    SmokePlanLedgerProjection,
)

SmokeInputs = tuple[
    ControlledSmokeAuthorization,
    ScriptedSmokeFixtureSet,
    SmokePlanLedgerProjection,
    EpisodeSetProjection,
]


def test_scenario_input_order_does_not_change_evidence(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    reversed_fixtures = ScriptedSmokeFixtureSet(
        fixture_set_id=fixtures.fixture_set_id,
        scenarios=tuple(reversed(fixtures.scenarios)),
    )
    original_records, original_report, _ = build_controlled_smoke(
        authorization, fixtures, plan, episodes
    )
    reversed_records, reversed_report, _ = build_controlled_smoke(
        authorization, reversed_fixtures, plan, episodes
    )
    assert reversed_records == original_records
    assert reversed_report == original_report


def test_resume_is_idempotent(controlled_smoke_inputs: SmokeInputs) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    records, report, _ = build_controlled_smoke(authorization, fixtures, plan, episodes)
    resumed, resumed_report, reused = build_controlled_smoke(
        authorization, fixtures, plan, episodes, records
    )
    assert reused == 3
    assert resumed == records
    assert resumed_report == report


def test_lower_cost_budget_cannot_improve_smoke_result(
    controlled_smoke_inputs: SmokeInputs,
) -> None:
    authorization, fixtures, plan, episodes = controlled_smoke_inputs
    _, baseline_report, _ = build_controlled_smoke(authorization, fixtures, plan, episodes)
    reduced = authorization.model_copy(update={"maximum_total_cost_microusd": 500})
    _, reduced_report, _ = build_controlled_smoke(reduced, fixtures, plan, episodes)
    assert baseline_report.smoke_passed is True
    assert reduced_report.smoke_passed is False
