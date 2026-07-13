from pathlib import Path

import pytest

from auragateway.benchmark.execution import LiveExecutionError
from auragateway.benchmark.execution_runner import _paths_for_authorization
from auragateway.benchmark.live_output_adapter import LiveBatchRuntimePolicy


def test_live_batches_use_separate_evidence_roots() -> None:
    batch_01 = _paths_for_authorization("live-development-batch-01-auth-v1")
    batch_02 = _paths_for_authorization("live-development-batch-02-auth-v1")
    batch_03 = _paths_for_authorization("live-development-batch-03-auth-v1")

    assert batch_01.asset_root == Path("data/evals/benchmark/live-development-v1")
    assert batch_02.asset_root == Path("data/evals/benchmark/live-development-v2")
    assert batch_03.asset_root == Path("data/evals/benchmark/live-development-v3")
    assert len({batch_01.journal_path, batch_02.journal_path, batch_03.journal_path}) == 3
    assert (
        len(
            {
                batch_01.protected_output_path,
                batch_02.protected_output_path,
                batch_03.protected_output_path,
            }
        )
        == 3
    )
    assert batch_03.raw_provider_output_path == Path(
        ".local/benchmark/live-development-v3/provider_raw_outputs.jsonl"
    )


def test_unknown_authorization_fails_closed() -> None:
    with pytest.raises(LiveExecutionError) as exc_info:
        _paths_for_authorization("live-development-batch-99-auth-v1")

    assert exc_info.value.error_code == "LIVE_DEVELOPMENT_AUTHORIZATION_UNKNOWN"


@pytest.mark.parametrize(
    ("authorization_id", "policy_id"),
    (
        (
            "live-development-batch-02-auth-v1",
            "live-development-batch-02-runtime-policy-v1",
        ),
        (
            "live-development-batch-03-auth-v1",
            "live-development-batch-03-runtime-policy-v1",
        ),
    ),
)
def test_corrective_runtime_policy_is_bound_to_its_authorization(
    authorization_id: str,
    policy_id: str,
) -> None:
    paths = _paths_for_authorization(authorization_id)
    policy = LiveBatchRuntimePolicy.model_validate_json(
        paths.runtime_policy_path.read_text(encoding="utf-8")
    )

    assert policy.authorization_id == authorization_id
    assert policy.policy_id == policy_id
    assert policy.output_normalization_profile == "compiler-to-terminal-v1"


def test_runtime_policy_rejects_cross_batch_binding() -> None:
    with pytest.raises(ValueError, match="matching authorization"):
        LiveBatchRuntimePolicy(
            policy_id="live-development-batch-03-runtime-policy-v1",
            authorization_id="live-development-batch-02-auth-v1",
            minimum_call_interval_seconds=20.0,
            rate_limit_cooldown_seconds=65.0,
            maximum_cumulative_sleep_seconds=900.0,
        )
