from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    final_342_transaction_wrapper_rehearsal_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def _copy_subject_files(destination: Path) -> None:
    paths = (
        subject.WRAPPER_TEMPLATE_PATH,
        subject.RUNTIME_CORE_PATH,
        subject.PLANNED_RUN_LEDGER_PATH,
        subject.ARCHITECTURE_PATH,
    )
    for relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def test_subject_preserves_exact_final_plan_and_non_authority() -> None:
    result = subject.validate_subject(ROOT)

    assert result["planned_trajectories"] == 342
    assert result["planned_turns"] == 1368
    assert result["maximum_request_attempts"] == 2736
    assert result["planned_run_ledger_sha256"] == subject.EXPECTED_LEDGER_SHA256
    assert result["execution_manifest_frozen"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["new_execution_authorized"] is False


def test_rendered_wrapper_is_inert_and_fully_resolved() -> None:
    rendered = subject.render_rehearsal_wrapper(ROOT).decode("utf-8")

    assert "__RUNTIME_CORE_B64__" not in rendered
    assert "__PLANNED_RUN_LEDGER_B64__" not in rendered
    assert "_LIVE_EXECUTION_ENABLED = False" in rendered
    assert "_EXECUTION_MANIFEST_FROZEN = False" in rendered
    assert '_REHEARSAL_TRANSACTION_ID = "0" * 64' in rendered
    assert "AURAGATEWAY_TRANSACTION_ID" in rendered
    assert "EXECUTED_RUNTIME_SCRIPT_SHA256" in rendered


def test_structural_rehearsal_executes_exact_embedded_graph() -> None:
    result = subject.rehearse(ROOT)

    assert result["status"] == ("FINAL_342_TRANSACTION_WRAPPER_STRUCTURAL_REHEARSAL_PASS")
    assert result["loaded_runtime_module_count"] == 1
    assert result["created_module_graph_entry_count"] == 3
    assert result["runtime_core_validated"] is True
    assert result["planned_trajectories"] == 342
    assert result["realized_turns"] == 1368
    assert result["maximum_request_attempts"] == 2736
    assert result["runtime_payload_identity_bound"] is True
    assert result["transaction_identity_seeded"] is True
    assert result["dataclass_module_identity_validated"] is True
    assert result["package_import_graph_validated"] is True
    assert result["pythonpath_cleared"] is True
    assert result["auragateway_environment_cleared"] is True
    assert result["system_exit_zero_handled"] is True
    assert result["nonzero_system_exit_propagated"] is True
    assert result["bootstrap_failure_cleanup_validated"] is True
    assert result["live_execution_enabled"] is False
    assert result["execution_manifest_frozen"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["model_requests_performed"] == 0
    assert result["gpu_execution_performed"] is False
    assert result["kaggle_execution_performed"] is False
    assert result["new_execution_authorized"] is False


def test_validation_surface_remains_non_authorizing() -> None:
    result = subject.validate_implementation(ROOT)

    assert result["status"] == ("FINAL_342_TRANSACTION_WRAPPER_REHEARSAL_V1_VALID")
    assert result["planned_trajectories"] == 342
    assert result["realized_turns"] == 1368
    assert result["maximum_request_attempts"] == 2736
    assert result["runtime_payload_identity_bound"] is True
    assert result["real_module_graph_structural_rehearsal"] is True
    assert result["repository_pythonpath_dependency_permitted"] is False
    assert result["authorization_producer_notebooks_permitted"] is False
    assert result["authorization_specific_kaggle_inputs_permitted"] is False
    assert result["manual_confirmation_json_permitted"] is False
    assert result["whole_notebook_sha256_is_semantic_execution_identity"] is False
    assert result["model_requests_performed"] == 0
    assert result["gpu_execution_performed"] is False
    assert result["kaggle_execution_performed"] is False
    assert result["live_authorization_issued"] is False
    assert result["execution_manifest_frozen"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["new_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
    assert result["next_gate"] == ("REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1")


def test_tampered_planned_ledger_is_rejected(tmp_path: Path) -> None:
    _copy_subject_files(tmp_path)
    ledger_path = tmp_path / subject.PLANNED_RUN_LEDGER_PATH
    ledger_path.write_bytes(ledger_path.read_bytes() + b"\n")

    with pytest.raises(subject.WrapperRehearsalError) as error:
        subject.render_rehearsal_wrapper(tmp_path)

    assert error.value.error_code == "FINAL_342_WRAPPER_LEDGER_IDENTITY_DRIFT"
