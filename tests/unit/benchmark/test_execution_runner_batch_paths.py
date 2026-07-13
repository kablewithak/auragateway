from pathlib import Path

import pytest

from auragateway.benchmark.execution import LiveExecutionError
from auragateway.benchmark.execution_runner import _paths_for_authorization
from auragateway.benchmark.live_output_adapter import LiveBatchRuntimePolicy


def test_batch_01_and_batch_02_use_separate_evidence_roots() -> None:
    batch_01 = _paths_for_authorization("live-development-batch-01-auth-v1")
    batch_02 = _paths_for_authorization("live-development-batch-02-auth-v1")

    assert batch_01.asset_root == Path("data/evals/benchmark/live-development-v1")
    assert batch_02.asset_root == Path("data/evals/benchmark/live-development-v2")
    assert batch_01.journal_path != batch_02.journal_path
    assert batch_01.protected_output_path != batch_02.protected_output_path
    assert batch_02.raw_provider_output_path == Path(
        ".local/benchmark/live-development-v2/provider_raw_outputs.jsonl"
    )


def test_unknown_authorization_fails_closed() -> None:
    with pytest.raises(LiveExecutionError) as exc_info:
        _paths_for_authorization("live-development-batch-99-auth-v1")

    assert exc_info.value.error_code == "LIVE_DEVELOPMENT_AUTHORIZATION_UNKNOWN"


def test_batch_02_runtime_policy_is_bound_to_its_authorization() -> None:
    paths = _paths_for_authorization("live-development-batch-02-auth-v1")
    policy = LiveBatchRuntimePolicy.model_validate_json(
        paths.runtime_policy_path.read_text(encoding="utf-8")
    )

    assert policy.authorization_id == "live-development-batch-02-auth-v1"
    assert policy.output_normalization_profile == "compiler-to-terminal-v1"
