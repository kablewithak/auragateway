"""Focused tests for G11.14 final-342 single-use live issuer qualification."""

from __future__ import annotations

import json
from pathlib import Path

from auragateway.local_abc import final_342_single_use_live_issuer_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def _record() -> subject.QualificationRecord:
    return subject.QualificationRecord.model_validate_json(
        (ROOT / subject.QUALIFICATION_RECORD_PATH).read_bytes()
    )


def test_qualification_is_non_issuing_and_non_executing() -> None:
    record = _record()

    assert record.status == "QUALIFIED_NOT_ISSUED"
    assert record.qualification_boundary.qualification_may_issue_live_authority is False
    assert record.qualification_boundary.governed_execution_permitted_during_qualification is False
    assert record.safety_state.model_requests_performed == 0
    assert record.safety_state.gpu_execution_performed is False
    assert record.safety_state.network_transport_performed is False
    assert record.safety_state.live_authorization_issued is False
    assert record.safety_state.final_measured_abc_execution_authorized is False


def test_qualification_closes_exact_transaction_bound_execution_seam() -> None:
    record = _record()

    boundary = record.qualification_boundary
    assert boundary.exact_static_authority_required is True
    assert boundary.exact_frozen_manifest_required is True
    assert boundary.exact_final_producer_required is True
    assert boundary.exact_frozen_context_contract_required is True
    assert boundary.canonical_hmac_prefix_contract_required is True
    assert boundary.protected_review_capture_required is True
    assert boundary.transaction_bound_execution_artifact_required is True
    assert boundary.repository_pythonpath_required_at_execution is False
    assert record.planned_trajectory_count == 342
    assert record.planned_turn_count == 1368
    assert record.maximum_request_attempt_count == 2736


def test_single_use_governance_does_not_claim_runtime_anti_replay() -> None:
    boundary = _record().qualification_boundary

    assert boundary.single_use_is_governance_invariant is True
    assert boundary.authorization_reusable is False
    assert boundary.runtime_anti_replay_established is False
    assert boundary.fresh_platform_readiness_required_after_qualification is True
    assert boundary.fresh_human_authority_required_after_qualification is True


def test_qualification_record_reconstructs_deterministically() -> None:
    result = subject.validate_qualification(ROOT)

    assert result["status"] == ("FINAL_342_SINGLE_USE_LIVE_ISSUER_V1_QUALIFIED_NOT_ISSUED")
    assert result["canonical_hmac_prefix_contract_bound"] is True
    assert result["protected_review_capture_bound"] is True
    assert result["repository_pythonpath_required_at_execution"] is False
    assert result["live_authorization_issued"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["next_gate"] == "FRESH_PLATFORM_READINESS_AND_HUMAN_AUTHORITY"


def test_live_authorization_contract_is_single_use() -> None:
    fields = subject.LiveAuthorization.model_fields

    assert "single_use" in fields
    assert "authorization_reusable" in fields
    assert "runtime_anti_replay_established" in fields
    assert "prefix_hmac_key_sha256" in fields
    assert "transaction_material_sha256" in fields


def test_notebook_container_preserves_exact_wrapper_bytes(tmp_path: Path) -> None:
    wrapper = b"print('final-342')\n"
    notebook_path = tmp_path / f"{subject.NOTEBOOK_NAME}.ipynb"

    notebook_bytes = subject._write_notebook(notebook_path, wrapper)
    payload = json.loads(notebook_bytes)

    assert notebook_path.read_bytes() == notebook_bytes
    assert payload["nbformat"] == 4
    assert payload["nbformat_minor"] == 5
    assert len(payload["cells"]) == 1
    assert payload["cells"][0]["cell_type"] == "code"
    assert "".join(payload["cells"][0]["source"]).encode("utf-8") == wrapper
    assert (
        payload["metadata"]["auragateway"]["notebook_container_is_semantic_payload_identity"]
        is False
    )
    assert (
        payload["metadata"]["auragateway"]["semantic_execution_identity"] == "python_wrapper_bytes"
    )
