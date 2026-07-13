from pathlib import Path

from auragateway.benchmark.execution import validate_live_upstream
from auragateway.benchmark.execution_runner import (
    _adapter_for_authorization,
    _load_authorization,
    _missing_receipt_public_artifacts,
    _paths_for_authorization,
)
from auragateway.benchmark.live_output_adapter import (
    ContractAlignedPacedAdapter,
    LiveBatchRuntimePolicy,
)
from auragateway.providers.groq import GroqProviderAdapter

_AUTHORIZATION_ID = "live-development-batch-06-auth-v1"
_EXPECTED_RUN_IDS = (
    "run-functional-ep-func-001-r03-condition-c",
    "run-functional-ep-func-001-r03-condition-a",
    "run-functional-ep-func-001-r03-condition-b",
)


def test_batch_06_selects_the_frozen_c_first_replication() -> None:
    paths = _paths_for_authorization(_AUTHORIZATION_ID)
    authorization = _load_authorization(Path("."), _AUTHORIZATION_ID, paths)

    selected, _, _, _, _ = validate_live_upstream(Path("."), authorization)

    assert authorization.allowed_run_ids == _EXPECTED_RUN_IDS
    assert tuple(item.run_id for item in selected) == _EXPECTED_RUN_IDS
    assert tuple(item.condition_id.value for item in selected) == (
        "condition_c",
        "condition_a",
        "condition_b",
    )
    assert {item.replication_id for item in selected} == {"replication-03"}
    assert tuple(item.schedule_index for item in selected) == (6, 7, 8)


def test_batch_06_runtime_policy_is_bound_and_unchanged() -> None:
    paths = _paths_for_authorization(_AUTHORIZATION_ID)
    policy = LiveBatchRuntimePolicy.model_validate_json(
        paths.runtime_policy_path.read_text(encoding="utf-8")
    )

    assert policy.policy_id == "live-development-batch-06-runtime-policy-v1"
    assert policy.authorization_id == _AUTHORIZATION_ID
    assert policy.output_normalization_profile == "compiler-to-terminal-v1"
    assert policy.minimum_call_interval_seconds == 20.0
    assert policy.rate_limit_cooldown_seconds == 65.0
    assert policy.maximum_cumulative_sleep_seconds == 900.0


def test_batch_06_uses_isolated_public_and_protected_roots(tmp_path: Path) -> None:
    paths = _paths_for_authorization(_AUTHORIZATION_ID)

    assert paths.asset_root == Path("data/evals/benchmark/live-development-v6")
    assert paths.protected_output_path == Path(
        ".local/benchmark/live-development-v6/protected_outputs.jsonl"
    )
    assert paths.raw_provider_output_path == Path(
        ".local/benchmark/live-development-v6/provider_raw_outputs.jsonl"
    )
    assert paths.provider_failure_diagnostic_path == Path(
        ".local/benchmark/live-development-v6/provider_failure_diagnostics.jsonl"
    )
    assert _missing_receipt_public_artifacts(tmp_path, paths) == (
        "data/evals/benchmark/live-development-v6/authorization.json",
        "data/evals/benchmark/live-development-v6/journal.jsonl",
        "data/evals/benchmark/live-development-v6/run_records.json",
        "data/evals/benchmark/live-development-v6/report.json",
        "data/evals/benchmark/live-development-v6/manifest.json",
    )


def test_batch_06_wires_diagnostics_inside_the_paced_adapter() -> None:
    paths = _paths_for_authorization(_AUTHORIZATION_ID)
    adapter = _adapter_for_authorization(Path("."), _AUTHORIZATION_ID, paths)

    assert isinstance(adapter, ContractAlignedPacedAdapter)
    assert isinstance(adapter._inner, GroqProviderAdapter)
    assert adapter._inner._failure_diagnostic_path == paths.provider_failure_diagnostic_path
