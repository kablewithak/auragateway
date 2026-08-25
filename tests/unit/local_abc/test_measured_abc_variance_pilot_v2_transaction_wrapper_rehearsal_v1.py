from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_wrapper_rehearsal_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def test_transaction_material_preserves_frozen_v2_budget_and_authority() -> None:
    material = subject.build_transaction_material(ROOT)

    schedule = material["pilot_schedule"]
    neutral_plan = material["neutral_worker_qualification_plan"]
    generation = material["generation_contract"]

    assert isinstance(schedule, dict)
    assert isinstance(neutral_plan, dict)
    assert isinstance(generation, dict)
    assert len(schedule["trajectories"]) == 54
    assert schedule["pilot_turn_count"] == 216
    assert len(neutral_plan["requests"]) == 24
    assert generation["max_tokens"] == 256
    assert material["pilot_execution_authorized"] is False
    assert material["final_measured_abc_execution_authorized"] is False


def test_rendered_rehearsal_wrapper_is_inert_and_fully_resolved() -> None:
    rendered = subject.render_rehearsal_wrapper(ROOT).decode("utf-8")

    assert "__R2_RUNTIME_B64__" not in rendered
    assert "__TRANSACTION_RUNTIME_B64__" not in rendered
    assert "__MATERIAL_B64__" not in rendered
    assert "_LIVE_EXECUTION_ENABLED = False" in rendered
    assert "maximum_total_model_requests != 240" in rendered
    assert "raise SystemExit(3)" in rendered


def test_structural_rehearsal_executes_exact_embedded_module_graph() -> None:
    result = subject.rehearse(ROOT)

    assert result["status"] == "V2_TRANSACTION_WRAPPER_STRUCTURAL_REHEARSAL_PASS"
    assert result["loaded_runtime_module_count"] == 6
    assert result["material_validated"] is True
    assert result["dataclass_module_identity_validated"] is True
    assert result["package_import_graph_validated"] is True
    assert result["request_budget_validated"] is True
    assert result["system_exit_zero_handled"] is True
    assert result["nonzero_system_exit_propagated"] is True
    assert result["bootstrap_failure_cleanup_validated"] is True
    assert result["live_execution_enabled"] is False
    assert result["model_requests_performed"] == 0
    assert result["gpu_execution_performed"] is False
    assert result["kaggle_execution_performed"] is False
    assert result["new_execution_authorized"] is False


def test_validation_surface_remains_non_authorizing() -> None:
    result = subject.validate_implementation(ROOT)

    assert result["status"] == ("VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_WRAPPER_REHEARSAL_VALID")
    assert result["loaded_runtime_module_count"] == 6
    assert result["material_validated"] is True
    assert result["model_requests_performed"] == 0
    assert result["gpu_execution_performed"] is False
    assert result["kaggle_execution_performed"] is False
    assert result["live_authorization_issued"] is False
    assert result["pilot_execution_authorized"] is False
    assert result["new_execution_authorized"] is False
    assert result["next_gate"] == (
        "IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_V1"
    )
