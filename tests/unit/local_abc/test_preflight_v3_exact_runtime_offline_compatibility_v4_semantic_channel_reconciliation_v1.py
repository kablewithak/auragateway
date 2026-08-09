from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    preflight_v3_exact_runtime_offline_compatibility_v4_semantic_channel_reconciliation_v1,
)

reconciliation = (
    preflight_v3_exact_runtime_offline_compatibility_v4_semantic_channel_reconciliation_v1
)


def _copy(source_root: Path, target_root: Path, relative: Path) -> None:
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_root / relative, target)


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    paths = (
        reconciliation.V4_NOTEBOOK_PATH,
        reconciliation.V4_SOURCE_PATH,
        reconciliation.V4_TEST_PATH,
        reconciliation.HISTORICAL_STARTUP_EVIDENCE_PATH,
        reconciliation.ADR_PATH,
        reconciliation.REPORT_PATH,
        reconciliation.RUNBOOK_PATH,
    )
    for relative in paths:
        _copy(source_root, tmp_path, relative)
    return tmp_path


def test_current_v4_semantic_channel_defect_is_machine_detected(
    candidate_repo: Path,
) -> None:
    source = reconciliation._notebook_source(candidate_repo / reconciliation.V4_NOTEBOOK_PATH)

    audit = reconciliation._semantic_excerpt_audit(source)

    assert audit["stdout_excerpt_semantic_use_sites"] == 19
    assert audit["stdout_excerpt_semantic_role_count"] == 18
    assert audit["stderr_excerpt_semantic_use_sites"] == 0
    assert audit["lossy_tail_truncation_before_semantic_parse"] is True
    assert audit["working_path_redaction_before_semantic_parse"] is True


def test_deterministic_path_bearing_false_negative_set_is_exact(
    candidate_repo: Path,
) -> None:
    record = reconciliation.build_record(candidate_repo)

    assert record.deterministic_false_negative_roles == (
        "controlled_python_startup",
        "target_native_inventory",
        "native_linker_static_provenance",
        "vllm_native_extension",
        "native_runtime_provenance",
    )
    assert record.runtime_incompatibility_established is False


def test_historical_controlled_startup_semantics_are_recovered(
    candidate_repo: Path,
) -> None:
    reconciliation._validate_historical_startup(candidate_repo)


def test_current_v4_tests_do_not_cover_semantic_evidence_invariance(
    candidate_repo: Path,
) -> None:
    reconciliation._validate_v4_test_gap(candidate_repo)


def test_successor_gate_forbids_semantic_use_of_evidence_channels() -> None:
    gate = reconciliation._successor_gate()

    assert gate.semantic_decisions_reading_stdout_excerpt == 0
    assert gate.semantic_decisions_reading_stderr_excerpt == 0
    assert gate.lossy_transformations_before_semantic_decision == 0
    assert gate.truncation_before_semantic_decision == 0
    assert gate.path_decisions_use_raw_canonical_paths is True
    assert gate.evidence_policy_is_terminal is True
    assert gate.statically_predictable_successor_failures == 0


def test_successor_gate_requires_metamorphic_and_negative_cases() -> None:
    gate = reconciliation._successor_gate()

    assert gate.sanitizer_metamorphic_invariance == "PASS"
    assert gate.excerpt_length_metamorphic_invariance == "PASS"
    assert gate.symlink_escape_negative_case == "PASS"
    assert gate.ambient_python_native_negative_case == "PASS"
    assert gate.cuda_stub_negative_case == "PASS"
    assert gate.real_driver_positive_case == "PASS"
    assert gate.unknown_native_origin_fails_closed == "PASS"


def test_record_is_non_authorizing(candidate_repo: Path) -> None:
    record = reconciliation.build_record(candidate_repo)

    assert record.exact_runtime_offline_verified is False
    assert record.p5_p6_exact_runtime_requalified is False
    assert record.runtime_execution_authorized is False
    assert record.pilot_execution_authorized is False
    assert record.final_measured_abc_execution_authorized is False
    assert record.next_kaggle_execution_authorized is False


def test_generate_is_deterministic(candidate_repo: Path) -> None:
    first = reconciliation.generate(candidate_repo)
    first_bytes = (candidate_repo / reconciliation.RECORD_PATH).read_bytes()

    second = reconciliation.generate(candidate_repo)
    second_bytes = (candidate_repo / reconciliation.RECORD_PATH).read_bytes()

    assert first == second
    assert first_bytes == second_bytes


def test_generated_record_is_canonical_and_valid(candidate_repo: Path) -> None:
    reconciliation.generate(candidate_repo)

    result = reconciliation.validate_generated(candidate_repo)

    assert result["status"] == "V4_SEMANTIC_CHANNEL_RECONCILIATION_VALID"
    assert result["classification"] == "DIAGNOSTIC_HARNESS_DEFECT"
    assert result["failure_code"] == "EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT"
    assert result["deterministic_false_negative_role_count"] == 5
    assert result["next_kaggle_execution_authorized"] is False


def test_generated_record_drift_fails_closed(candidate_repo: Path) -> None:
    reconciliation.generate(candidate_repo)
    path = candidate_repo / reconciliation.RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["runtime_incompatibility_established"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(reconciliation.ReconciliationError):
        reconciliation.validate_generated(candidate_repo)


def test_v4_notebook_identity_drift_fails_closed(candidate_repo: Path) -> None:
    path = candidate_repo / reconciliation.V4_NOTEBOOK_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(reconciliation.ReconciliationError):
        reconciliation.build_record(candidate_repo)


def test_validate_implementation_is_reconciled_not_remediated(
    candidate_repo: Path,
) -> None:
    reconciliation.generate(candidate_repo)

    result = reconciliation.validate_implementation(candidate_repo)

    assert result["implementation_status"] == "RECONCILED_NOT_REMEDIATED"
    assert result["historical_v4_preserved"] is True
    assert result["saved_version_341211001_preserved"] is True
    assert result["runtime_execution_authorized"] is False
