from __future__ import annotations

import json
from pathlib import Path

from auragateway.local_abc import (
    preflight_v3_exact_runtime_wheelhouse_materialization_acceptance_v1 as runtime,
)

ROOT = Path(__file__).resolve().parents[3]


def test_materialization_acceptance_validates() -> None:
    summary = runtime.validate_repository_package(ROOT)

    assert summary["status"] == ("PREFLIGHT_V3_EXACT_RUNTIME_MATERIALIZATION_V1_ACCEPTED")
    assert summary["kaggle_script_version_id"] == 341083505
    assert summary["package_count"] == 196
    assert summary["authority_host_count"] == 5
    assert summary["total_wheel_bytes"] == 6164913809
    assert summary["wheelhouse_materialized"] is True
    assert summary["exact_runtime_materialized"] is True
    assert summary["exact_runtime_offline_verified"] is False
    assert summary["p5_p6_exact_runtime_requalified"] is False
    assert summary["runtime_execution_authorized"] is False
    assert summary["pilot_execution_authorized"] is False
    assert summary["final_measured_abc_execution_authorized"] is False


def test_acceptance_binds_executed_notebook_source() -> None:
    payload = json.loads((ROOT / runtime.ACCEPTANCE_PATH).read_text(encoding="utf-8"))

    assert payload["repository_notebook_sha256"] == (runtime.EXPECTED_REPOSITORY_NOTEBOOK_SHA256)
    assert payload["executed_notebook_sha256"] == (runtime.EXPECTED_EXECUTED_NOTEBOOK_SHA256)
    assert payload["executed_markdown_source_matches_repository"] is True
    assert payload["executed_code_source_matches_repository"] is True
    assert payload["markdown_cell_source_sha256"] == (runtime.EXPECTED_MARKDOWN_SOURCE_SHA256)
    assert payload["code_cell_source_sha256"] == runtime.EXPECTED_CODE_SOURCE_SHA256


def test_queryable_evidence_is_hash_bound() -> None:
    payload = json.loads((ROOT / runtime.ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    members = payload["queryable_evidence_members"]

    assert set(members) == set(runtime.EXPECTED_MEMBER_HASHES)
    for name, expected_sha in runtime.EXPECTED_MEMBER_HASHES.items():
        path = ROOT / runtime.EVIDENCE_DIR / name
        assert runtime._sha256(path) == expected_sha
        assert path.stat().st_size == runtime.EXPECTED_MEMBER_SIZES[name]


def test_acceptance_promotes_only_materialization_state() -> None:
    payload = json.loads((ROOT / runtime.ACCEPTANCE_PATH).read_text(encoding="utf-8"))

    assert payload["wheelhouse_materialized"] is True
    assert payload["exact_runtime_resolution_lock_frozen"] is True
    assert payload["exact_runtime_materialized"] is True
    assert payload["exact_runtime_offline_verified"] is False
    assert payload["p5_p6_exact_runtime_requalified"] is False
    assert payload["variance_pilot_accepted"] is False
    assert payload["repetition_count_frozen"] is False
    assert payload["execution_manifest_frozen"] is False
    assert payload["runtime_execution_authorized"] is False
    assert payload["pilot_execution_authorized"] is False
    assert payload["final_measured_abc_execution_authorized"] is False
