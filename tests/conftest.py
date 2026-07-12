from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from auragateway.benchmark.smoke import execution_manifest_canonical_sha256
from auragateway.contracts.benchmark_smoke import (
    ControlledSmokeAuthorization,
    EpisodeSetProjection,
    ScriptedSmokeFixtureSet,
    SmokePlanLedgerProjection,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_runs() -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    for index, suffix in enumerate(("a", "b", "c")):
        runs.append(
            {
                "schedule_index": index,
                "run_id": f"run-functional-ep-func-001-r01-condition-{suffix}",
                "comparison_pair_id": "pair-functional-ep-func-001-r01",
                "workload": "functional",
                "episode_id": "ep-func-001",
                "replication_id": "replication-01",
                "condition_id": f"condition_{suffix}",
                "condition_order_index": index,
                "cache_namespace_id": (f"ns-functional-ep-func-001-r01-condition-{suffix}"),
                "turn_count": 4,
                "maximum_request_attempt_count": 8,
            }
        )
    return runs


@pytest.fixture
def controlled_smoke_inputs() -> tuple[
    ControlledSmokeAuthorization,
    ScriptedSmokeFixtureSet,
    SmokePlanLedgerProjection,
    EpisodeSetProjection,
]:
    authorization = ControlledSmokeAuthorization.model_validate_json(
        (PACKAGE_ROOT / "data/evals/benchmark/smoke-v1/authorization.json").read_text()
    )
    fixtures = ScriptedSmokeFixtureSet.model_validate_json(
        (PACKAGE_ROOT / "data/evals/benchmark/smoke-v1/scripted_attempts.json").read_text()
    )
    plan = SmokePlanLedgerProjection.model_validate(
        {"plan_id": "benchmark-plan-auragateway-abc-v1", "runs": selected_runs()}
    )
    episodes = EpisodeSetProjection.model_validate(
        {"episodes": [{"episode_id": "ep-func-001", "evaluation_split": "development"}]}
    )
    return authorization, fixtures, plan, episodes


@pytest.fixture
def temp_smoke_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    smoke_root = repo / "data/evals/benchmark/smoke-v1"
    smoke_root.mkdir(parents=True)
    fixture_payload = json.loads(
        (PACKAGE_ROOT / "data/evals/benchmark/smoke-v1/scripted_attempts.json").read_text()
    )
    _write_json(smoke_root / "scripted_attempts.json", fixture_payload)

    plan_path = repo / "data/evals/benchmark/preflight-v1/planned_run_ledger.json"
    _write_json(plan_path, {"plan_id": "plan-v1", "runs": selected_runs()})
    gate9_path = repo / "data/evals/benchmark/preflight-v1/manifest.json"
    gate9_payload = {
        "plan_path": "data/evals/benchmark/preflight-v1/planned_run_ledger.json",
        "plan_sha256": _sha(plan_path),
        "planning_ready": True,
        "measured_execution_ready": False,
        "execution_enabled": False,
        "measured_execution_permitted": False,
    }
    _write_json(gate9_path, gate9_payload)

    episode_path = repo / "data/evals/episodes/functional-v1/accepted_episodes.json"
    _write_json(
        episode_path,
        {"episodes": [{"episode_id": "ep-func-001", "evaluation_split": "development"}]},
    )

    execution_path = repo / "data/evals/benchmark/freeze-v1/execution_manifest.json"
    execution: dict[str, Any] = {
        "identity": {
            "execution_manifest_status": "frozen",
            "execution_manifest_sha256": None,
            "execution_enabled": False,
        },
        "assets": {"provider_model_alias": "fixture"},
    }
    canonical = execution_manifest_canonical_sha256(execution)
    identity = execution["identity"]
    assert isinstance(identity, dict)
    identity["execution_manifest_sha256"] = canonical
    _write_json(execution_path, execution)

    gate10_path = repo / "data/evals/benchmark/freeze-v1/manifest.json"
    gate10 = {
        "gate9_manifest_path": "data/evals/benchmark/preflight-v1/manifest.json",
        "gate9_manifest_sha256": _sha(gate9_path),
        "execution_manifest_path": ("data/evals/benchmark/freeze-v1/execution_manifest.json"),
        "execution_manifest_file_sha256": _sha(execution_path),
        "execution_manifest_canonical_sha256": canonical,
        "gate_10_passed": True,
        "execution_enabled": False,
        "measured_execution_permitted": False,
    }
    _write_json(gate10_path, gate10)

    authorization_id = "development-controlled-smoke-auth-v1"
    authorization = {
        "smoke_id": "auragateway-development-controlled-smoke-v1",
        "authorization_id": authorization_id,
        "execution_manifest_sha256": canonical,
        "gate10_manifest_sha256": _sha(gate10_path),
        "gate9_manifest_sha256": _sha(gate9_path),
        "planned_run_ledger_sha256": _sha(plan_path),
        "functional_episode_set_sha256": _sha(episode_path),
        "allowed_episode_ids": ["ep-func-001"],
        "allowed_run_ids": [str(item["run_id"]) for item in selected_runs()],
        "allowed_conditions": ["condition_a", "condition_b", "condition_c"],
        "maximum_total_attempt_count": 11,
        "maximum_total_cost_microusd": 5000,
    }
    _write_json(smoke_root / "authorization.json", authorization)
    return repo, authorization_id
