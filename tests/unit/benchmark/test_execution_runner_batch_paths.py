from pathlib import Path

import pytest

from auragateway.benchmark.execution import LiveExecutionError
from auragateway.benchmark.execution_runner import (
    _adapter_for_authorization,
    _paths_for_authorization,
    _validate_provider_failure_diagnostic_sink,
)
from auragateway.benchmark.live_output_adapter import (
    ContractAlignedPacedAdapter,
    LiveBatchRuntimePolicy,
)
from auragateway.providers.groq import GroqProviderAdapter

_DIAGNOSTIC_AUTHORIZATION_IDS = (
    "live-development-batch-04-auth-v1",
    "live-development-batch-05-auth-v1",
)


def test_live_batches_use_separate_evidence_roots() -> None:
    batch_01 = _paths_for_authorization("live-development-batch-01-auth-v1")
    batch_02 = _paths_for_authorization("live-development-batch-02-auth-v1")
    batch_03 = _paths_for_authorization("live-development-batch-03-auth-v1")
    batch_04 = _paths_for_authorization("live-development-batch-04-auth-v1")
    batch_05 = _paths_for_authorization("live-development-batch-05-auth-v1")

    assert batch_01.asset_root == Path("data/evals/benchmark/live-development-v1")
    assert batch_02.asset_root == Path("data/evals/benchmark/live-development-v2")
    assert batch_03.asset_root == Path("data/evals/benchmark/live-development-v3")
    assert batch_04.asset_root == Path("data/evals/benchmark/live-development-v4")
    assert batch_05.asset_root == Path("data/evals/benchmark/live-development-v5")
    assert (
        len(
            {
                batch_01.journal_path,
                batch_02.journal_path,
                batch_03.journal_path,
                batch_04.journal_path,
                batch_05.journal_path,
            }
        )
        == 5
    )
    assert (
        len(
            {
                batch_01.protected_output_path,
                batch_02.protected_output_path,
                batch_03.protected_output_path,
                batch_04.protected_output_path,
                batch_05.protected_output_path,
            }
        )
        == 5
    )
    assert batch_03.raw_provider_output_path == Path(
        ".local/benchmark/live-development-v3/provider_raw_outputs.jsonl"
    )
    assert batch_04.provider_failure_diagnostic_path == Path(
        ".local/benchmark/live-development-v4/provider_failure_diagnostics.jsonl"
    )
    assert batch_05.provider_failure_diagnostic_path == Path(
        ".local/benchmark/live-development-v5/provider_failure_diagnostics.jsonl"
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
        (
            "live-development-batch-04-auth-v1",
            "live-development-batch-04-runtime-policy-v1",
        ),
        (
            "live-development-batch-05-auth-v1",
            "live-development-batch-05-runtime-policy-v1",
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


def test_diagnostic_batches_wire_failure_diagnostics_inside_paced_adapter() -> None:
    batch_03_id = "live-development-batch-03-auth-v1"
    batch_03_paths = _paths_for_authorization(batch_03_id)
    batch_03_adapter = _adapter_for_authorization(Path("."), batch_03_id, batch_03_paths)

    assert isinstance(batch_03_adapter, ContractAlignedPacedAdapter)
    assert isinstance(batch_03_adapter._inner, GroqProviderAdapter)
    assert batch_03_adapter._inner._failure_diagnostic_path is None

    for authorization_id in _DIAGNOSTIC_AUTHORIZATION_IDS:
        paths = _paths_for_authorization(authorization_id)
        adapter = _adapter_for_authorization(Path("."), authorization_id, paths)

        assert isinstance(adapter, ContractAlignedPacedAdapter)
        assert isinstance(adapter._inner, GroqProviderAdapter)
        assert adapter._inner._failure_diagnostic_path == paths.provider_failure_diagnostic_path


@pytest.mark.parametrize("authorization_id", _DIAGNOSTIC_AUTHORIZATION_IDS)
def test_diagnostic_preflight_leaves_no_probe(
    tmp_path: Path,
    authorization_id: str,
) -> None:
    paths = _paths_for_authorization(authorization_id)

    _validate_provider_failure_diagnostic_sink(tmp_path, paths, require_absent=True)

    diagnostic_path = tmp_path / paths.provider_failure_diagnostic_path
    probe_path = diagnostic_path.with_name(f".{diagnostic_path.name}.preflight")
    assert diagnostic_path.parent.is_dir()
    assert not diagnostic_path.exists()
    assert not probe_path.exists()


@pytest.mark.parametrize("authorization_id", _DIAGNOSTIC_AUTHORIZATION_IDS)
def test_fresh_preflight_rejects_existing_diagnostics(
    tmp_path: Path,
    authorization_id: str,
) -> None:
    paths = _paths_for_authorization(authorization_id)
    diagnostic_path = tmp_path / paths.provider_failure_diagnostic_path
    diagnostic_path.parent.mkdir(parents=True)
    diagnostic_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(LiveExecutionError) as exc_info:
        _validate_provider_failure_diagnostic_sink(tmp_path, paths, require_absent=True)

    assert exc_info.value.error_code == "LIVE_DEVELOPMENT_PROVIDER_DIAGNOSTIC_ALREADY_EXISTS"
    assert diagnostic_path.read_text(encoding="utf-8") == "{}\n"


@pytest.mark.parametrize("authorization_id", _DIAGNOSTIC_AUTHORIZATION_IDS)
def test_resume_preflight_preserves_existing_diagnostics(
    tmp_path: Path,
    authorization_id: str,
) -> None:
    paths = _paths_for_authorization(authorization_id)
    diagnostic_path = tmp_path / paths.provider_failure_diagnostic_path
    diagnostic_path.parent.mkdir(parents=True)
    diagnostic_path.write_text("{}\n", encoding="utf-8")

    _validate_provider_failure_diagnostic_sink(tmp_path, paths, require_absent=False)

    assert diagnostic_path.read_text(encoding="utf-8") == "{}\n"


def test_runtime_policy_rejects_cross_batch_binding() -> None:
    with pytest.raises(ValueError, match="matching authorization"):
        LiveBatchRuntimePolicy(
            policy_id="live-development-batch-05-runtime-policy-v1",
            authorization_id="live-development-batch-04-auth-v1",
            minimum_call_interval_seconds=20.0,
            rate_limit_cooldown_seconds=65.0,
            maximum_cumulative_sleep_seconds=900.0,
        )
