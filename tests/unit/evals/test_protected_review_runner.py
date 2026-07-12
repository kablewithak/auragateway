from pathlib import Path

from auragateway.evals.protected_review_runner import verify_assets


def test_frozen_protected_review_assets_reproduce() -> None:
    summary = verify_assets(Path("."))

    assert summary.assignment_count == 23
    assert summary.review_count == 23
    assert summary.adjudication_count == 2
    assert summary.held_out_episode_count == 6
    assert summary.held_out_pass_count == 5
    assert summary.execution_controls_passed is True
    assert summary.human_review_completed is False
    assert summary.measured_execution_permitted is False
