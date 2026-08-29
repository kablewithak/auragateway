from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import final_342_requirements_precedence_reconciliation_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def test_reconciliation_covers_every_legacy_required_field_once() -> None:
    record = subject.build_record(ROOT)

    fields = [field for group in record.requirement_groups for field in group.members]

    assert len(fields) == 69
    assert len(fields) == len(set(fields))
    assert set(fields) == {
        field
        for members in subject.REQUIRED_FIELD_FAMILIES.values()
        for field in members
    }


def test_reconciliation_covers_all_thirteen_freeze_steps_once() -> None:
    record = subject.build_record(ROOT)

    steps = [step for group in record.freeze_procedure_groups for step in group.steps]

    assert sorted(steps) == list(range(1, 14))
    assert len(steps) == len(set(steps))


def test_readiness_probe_is_explicitly_superseded_not_silently_ignored() -> None:
    record = subject.build_record(ROOT)
    group = next(
        item
        for item in record.freeze_procedure_groups
        if item.group_id == "procedure.readiness_sequence"
    )

    assert group.steps == (7,)
    assert group.disposition is subject.Disposition.SUPERSEDED_BY_ACCEPTED_SEQUENCE
    assert group.blocking_before_manifest_freeze is False
    assert "after issuance" in group.rationale


def test_git_commit_requirement_uses_acyclic_post_commit_custody() -> None:
    record = subject.build_record(ROOT)
    custody = record.commit_binding

    assert custody.historical_same_commit_self_reference_rejected is True
    assert custody.first_containing_commit_stored_inside_same_manifest is False
    assert custody.post_commit_custody_receipt_required is True
    assert custody.receipt_binds_manifest_sha256 is True
    assert custody.receipt_binds_manifest_file_sha256 is True
    assert custody.receipt_binds_source_subject_commit is True
    assert custody.receipt_binds_first_containing_commit is True
    assert custody.g11_freeze_gate_promoted_before_receipt is False


def test_producer_closure_and_cost_scope_block_manifest_freeze() -> None:
    record = subject.build_record(ROOT)
    blockers = {
        group.group_id
        for group in record.requirement_groups
        if group.blocking_before_manifest_freeze
    }

    assert blockers == {
        "identity.producer",
        "provider_telemetry.local_runtime_mapping",
        "provider_telemetry.pricing_scope",
        "route_policy.local_runtime_mapping",
    }
    assert len(record.producer_obligations) == 10
    assert record.safety_state.manifest_freeze_permitted is False
    assert record.safety_state.execution_manifest_frozen is False
    assert record.next_gate == "G11_3B_FINAL_EXECUTION_PRODUCER_CLOSURE_V1"


def test_reconciliation_remains_non_authorizing() -> None:
    state = subject.build_record(ROOT).safety_state

    assert state.final_measured_abc_execution_authorized is False
    assert state.new_execution_authorized is False
    assert state.effect_claims_permitted is False
    assert state.model_requests_performed == 0
    assert state.gpu_execution_performed is False
    assert state.kaggle_execution_performed is False


def test_preflight_v3_planning_state_uses_nested_identity_contract() -> None:
    preflight = subject._read_object(ROOT, subject.PREFLIGHT_DRAFT_PATH)
    identity = preflight.get("identity")

    assert isinstance(identity, dict)
    assert identity["execution_manifest_frozen"] is False
    assert identity["execution_enabled"] is False
    assert identity["execution_manifest_status"] == "planning_draft"
    assert preflight["measured_execution_authorized"] is False
    assert preflight["gpu_execution_authorized"] is False
    assert preflight["provider_execution_authorized"] is False
    assert preflight["claim_generation_permitted"] is False

    subject._validate_source_contracts(ROOT)


def test_repository_record_regenerates_exactly() -> None:
    result = subject.validate_repository(ROOT)

    assert result["status"] == "FINAL_342_REQUIREMENTS_PRECEDENCE_RECONCILIATION_V1_VALID"
    assert result["required_field_count"] == 69
    assert result["freeze_procedure_step_count"] == 13
    assert result["producer_obligation_count"] == 10
    assert result["requirements_inventory_complete"] is True
    assert result["requirements_precedence_established"] is True
    assert result["manifest_freeze_permitted"] is False
    assert result["execution_manifest_frozen"] is False
    assert result["next_gate"] == "G11_3B_FINAL_EXECUTION_PRODUCER_CLOSURE_V1"
