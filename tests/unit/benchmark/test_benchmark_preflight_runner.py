from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.benchmark.preflight_runner import (
    BenchmarkPreflightAssetError,
    build_assets,
    main,
    validate_config,
    verify_assets,
)

ROOT = Path(__file__).resolve().parents[3]


def test_validate_config_returns_non_executing_plan_summary() -> None:
    summary = validate_config(ROOT)

    assert summary.planning_ready is True
    assert summary.total_trajectory_count == 342
    assert summary.measured_execution_ready is False
    assert summary.execution_enabled is False


def test_verify_reproduces_all_persisted_assets() -> None:
    summary = verify_assets(ROOT)

    assert summary.total_turn_count == 1368
    assert summary.maximum_request_attempt_count == 2736


def test_build_assets_binds_gate_7_and_gate_8_manifests() -> None:
    *_, manifest, _summary = build_assets(ROOT)

    assert manifest.gate8_manifest_sha256 == (
        "259f1a3646311e705d68eca10ee7ea7fa4b9d89700227b15dedb8fd118808405"
    )
    assert manifest.gate7_manifest_sha256 == (
        "7e856227772b38d4b66cd41936e0ad695747544f733942d4165c80dd1f71573e"
    )


def test_verify_detects_mutated_plan(tmp_path: Path) -> None:
    copied = tmp_path / "repo"
    copied.mkdir()
    for path in ROOT.rglob("*"):
        relative_parts = path.relative_to(ROOT).parts
        if path.is_file() and not any(part.startswith(".") for part in relative_parts):
            target = copied / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())

    plan_path = copied / "data/evals/benchmark/preflight-v1/planned_run_ledger.json"
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["runs"][0]["cache_namespace_id"] = "ns-mutated-test-namespace"
    plan_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BenchmarkPreflightAssetError) as error:
        verify_assets(copied)

    assert error.value.error_code == "BENCHMARK_PREFLIGHT_MANIFEST_MISMATCH" or (
        error.value.error_code == "BENCHMARK_PLAN_MISMATCH"
    )


def test_cli_rejects_provider_run_command() -> None:
    with pytest.raises(SystemExit) as error:
        main(["run", "--repo-root", str(ROOT)])

    assert error.value.code == 2
