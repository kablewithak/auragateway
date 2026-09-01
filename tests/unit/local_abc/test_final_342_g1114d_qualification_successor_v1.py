from __future__ import annotations

from pathlib import Path

from auragateway.local_abc import (
    final_342_g1114d_qualification_successor_v1 as successor,
)
from auragateway.local_abc import final_342_single_use_live_issuer_v1 as issuer

ROOT = Path(__file__).resolve().parents[3]


def test_g1114d_successor_changes_only_repair_bound_fields() -> None:
    predecessor, expected = successor.build_successor(ROOT)

    assert (
        successor._changed_fields(
            predecessor,
            expected,
        )
        == successor.ALLOWED_CHANGED_FIELDS
    )

    assert expected.source == predecessor.source
    assert expected.transaction_material_sha256 == predecessor.transaction_material_sha256
    assert expected.bootstrap_state_sha256 == predecessor.bootstrap_state_sha256
    assert expected.canonical_static_payload_sha256 == predecessor.canonical_static_payload_sha256
    assert expected.protected_review_schedule_sha256 == predecessor.protected_review_schedule_sha256

    assert expected.live_execution_template.sha256 != predecessor.live_execution_template.sha256
    assert expected.test.sha256 != predecessor.test.sha256


def test_g1114d_successor_remains_non_authorizing() -> None:
    _, expected = successor.build_successor(ROOT)

    assert expected.safety_state.effect_claims_permitted is False
    assert expected.safety_state.final_measured_abc_execution_authorized is False
    assert expected.safety_state.new_execution_authorized is False
    assert expected.safety_state.live_authorization_issued is False


def test_generated_qualification_matches_g1114d_successor() -> None:
    path = ROOT / issuer.QUALIFICATION_RECORD_PATH

    observed = issuer.QualificationRecord.model_validate_json(path.read_bytes())
    _, expected = successor.build_successor(ROOT)

    assert observed == expected
    assert path.read_bytes() == issuer.canonical_bytes(expected)

    assert observed.live_execution_template.sha256 != successor.PREDECESSOR_TEMPLATE_SHA256
    assert observed.test.sha256 != successor.PREDECESSOR_TEST_SHA256

    assert observed.safety_state.effect_claims_permitted is False
    assert observed.safety_state.final_measured_abc_execution_authorized is False
    assert observed.safety_state.new_execution_authorized is False
