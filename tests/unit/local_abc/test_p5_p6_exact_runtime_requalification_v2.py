"""Tests for Exact-Runtime P5/P6 Requalification V2 transport remediation."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import (
    p5_p6_exact_runtime_authorization_transport_v1 as transport,
)
from auragateway.local_abc import (
    p5_p6_exact_runtime_requalification_v2 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    required = (
        subject.DESIGN_RECORD_PATH,
        subject.PREDECESSOR_SOURCE_PATH,
        subject.PREDECESSOR_TEMPLATE_PATH,
        subject.PREDECESSOR_TEST_PATH,
        subject.PREDECESSOR_NOTEBOOK_PATH,
        subject.PREDECESSOR_REVIEW_PATH,
        subject.PREDECESSOR_RECORD_PATH,
        subject.FAILURE_ACCEPTANCE_PATH,
        subject.FAILURE_REVIEW_PATH,
        subject.FAILURE_SFR_PATH,
        subject.HISTORICAL_CONTROL_DISCOVERY_RECORD_PATH,
        subject.HISTORICAL_LAUNCHER_PATH,
        *subject.STATIC_PATHS,
    )
    for relative in required:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def _runtime(repo_root: Path) -> dict[str, Any]:
    return subject.runtime_namespace(repo_root)


def _authorization_bytes(
    runtime: dict[str, Any],
    now: datetime | None = None,
) -> bytes:
    current = datetime.now(UTC) if now is None else now
    payload = {
        "schema_version": "1.0.0",
        "authorization_id": runtime["AUTHORIZATION_ID"],
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "scope": runtime["AUTHORIZATION_SCOPE"],
        "implementation_review_sha256": runtime["IMPLEMENTATION_REVIEW_SHA256"],
        "design_record_sha256": runtime["DESIGN_RECORD_SHA256"],
        "v5_acceptance_sha256": runtime["V5_ACCEPTANCE_SHA256"],
        "runtime_script_sha256": runtime["EXECUTED_RUNTIME_SCRIPT_SHA256"],
        "issued_at": (current - timedelta(minutes=1)).isoformat(timespec="seconds"),
        "expires_at": (current + timedelta(minutes=30)).isoformat(timespec="seconds"),
        "runtime_execution_authorized": True,
        "single_use": True,
        "every_terminal_attempt_consumes_authorization": True,
        "unchanged_replay_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "hidden_retries_permitted": 0,
    }
    canonical_json = runtime["canonical_json"]
    canonical_payload = canonical_json(payload)
    assert isinstance(canonical_payload, str)
    return canonical_payload.encode("utf-8")


def _control_root(input_root: Path) -> Path:
    return (
        input_root
        / "notebooks"
        / "kabomolefe"
        / transport.CONTROL_NOTEBOOK_NAME
        / transport.CONTROL_OUTPUT_DIRECTORY_NAME
    )


def test_candidate_boundary_is_exact() -> None:
    assert len(subject.STATIC_PATHS) == 8
    assert len(subject.GENERATED_PATHS) == 3
    assert len(subject.CANDIDATE_PATHS) == 12
    assert subject.DESIGN_RECORD_PATH in subject.CANDIDATE_PATHS


def test_failure_lineage_and_design_are_frozen(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    predecessor = subject.validate_predecessor_lineage(repo_root)
    design = subject.validate_design_authority(repo_root)

    assert predecessor["status"] == "EXACT_RUNTIME_P5_P6_V1_AND_FAILURE_LINEAGE_VALID"
    assert predecessor["failed_saved_version_id"] == 341454766
    assert predecessor["inspection_saved_version_id"] == 341466979
    assert design["status"] == "EXACT_RUNTIME_P5_P6_TRANSPORT_REMEDIATION_DESIGN_VALID"
    assert design["runtime_execution_authorized"] is False


def test_behavioral_core_is_preserved_from_v1(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    audit = subject.audit_behavioral_core_preservation(repo_root)

    assert audit["status"] == "EXACT_RUNTIME_P5_P6_V2_BEHAVIORAL_CORE_PRESERVED"
    assert audit["behavioral_semantics_changed"] is False
    unchanged_function_count = audit["unchanged_top_level_function_count"]
    assert isinstance(unchanged_function_count, int)
    assert unchanged_function_count > 20


def test_generation_round_trip_is_deterministic(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    first = subject.generate(repo_root)
    first_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}
    second = subject.generate(repo_root)
    second_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}

    assert first == second
    assert first_bytes == second_bytes
    assert first["status"] == "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_GENERATED"
    assert first["runtime_execution_authorized"] is False


def test_notebook_is_single_cell_unexecuted_and_transport_bound(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)

    validation = subject.validate_notebook(repo_root)
    notebook = json.loads((repo_root / subject.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    cells = notebook["cells"]

    assert len(cells) == 1
    assert cells[0]["execution_count"] is None
    assert cells[0]["outputs"] == []
    assert validation["runtime_execution_authorized"] is False
    transport_audit = validation["authorization_transport"]
    assert isinstance(transport_audit, dict)
    assert transport_audit["governed_root_resolved_before_filename"] is True
    assert transport_audit["global_filename_uniqueness_required"] is False
    assert transport_audit["unscoped_recursive_authorization_search_permitted"] is False


def test_runtime_accepts_exact_governed_control_package(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    runtime = _runtime(repo_root)
    input_root = tmp_path / "input"
    input_root.mkdir()
    runtime["INPUT_ROOT"] = input_root

    authorization_bytes = _authorization_bytes(runtime)
    root = _control_root(input_root)
    transport.materialize_control_package(root, authorization_bytes)

    result = runtime["require_execution_authorization"]()

    assert result["runtime_execution_authorized"] is True
    assert result["single_use"] is True
    assert result["scope"] == "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"
    assert result["transport_contract"] == "GOVERNED_ROOT_EXACT_FLAT_V1"
    assert result["producer_notebook_name"] == "ag-p5-p6-auth-control-v1"


def test_runtime_ignores_unrelated_authorization_filename_collision(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    runtime = _runtime(repo_root)
    input_root = tmp_path / "input"
    runtime["INPUT_ROOT"] = input_root
    authorization_bytes = _authorization_bytes(runtime)

    transport.materialize_control_package(
        _control_root(input_root),
        authorization_bytes,
    )
    unrelated = input_root / "datasets" / "kabomolefe" / "unrelated-expanded-input" / "nested"
    unrelated.mkdir(parents=True)
    (unrelated / transport.AUTHORIZATION_FILENAME).write_bytes(authorization_bytes)

    result = runtime["require_execution_authorization"]()

    assert result["runtime_execution_authorized"] is True


def test_runtime_rejects_old_direct_dataset_transport(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    runtime = _runtime(repo_root)
    input_root = tmp_path / "input"
    runtime["INPUT_ROOT"] = input_root
    old_root = input_root / "datasets" / "kabomolefe" / "ag-p5-p6-execution-authorization-v1"
    old_root.mkdir(parents=True)
    (old_root / transport.AUTHORIZATION_FILENAME).write_bytes(_authorization_bytes(runtime))

    old_shallow_candidates = tuple(input_root.glob(f"*/{transport.AUTHORIZATION_FILENAME}"))
    assert old_shallow_candidates == ()

    with pytest.raises(
        runtime["DiagnosticFailure"],
        match="exactly one governed P5/P6 authorization control root",
    ):
        runtime["require_execution_authorization"]()


def test_runtime_rejects_extra_control_member(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    runtime = _runtime(repo_root)
    input_root = tmp_path / "input"
    runtime["INPUT_ROOT"] = input_root

    root = _control_root(input_root)
    transport.materialize_control_package(
        root,
        _authorization_bytes(runtime),
    )
    (root / "unexpected.json").write_text("{}", encoding="utf-8")

    with pytest.raises(
        runtime["DiagnosticFailure"],
        match="authorization control root file set drifted",
    ):
        runtime["require_execution_authorization"]()


def test_runtime_authorization_precedes_installation(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    review = subject._review(repo_root)
    runtime_source = subject._render_runtime_template(
        repo_root,
        subject._sha256_bytes(review.canonical_bytes()),
    )

    audit = subject.audit_authorization_transport_runtime(runtime_source)
    semantic = subject.audit_runtime_semantic_boundary(runtime_source)

    assert audit["authorization_before_runtime_installation"] is True
    assert semantic["authorization_precedes_runtime_installation"] is True
    assert semantic["public_evidence_used_as_semantic_input"] is False
    assert semantic["semantic_channel_violation_count"] == 0
