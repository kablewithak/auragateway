from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from auragateway.contracts.quality_development_evaluation_v2 import (
    EXPECTED_AUTHORING_CASE_SET_SHA256,
    EXPECTED_CONSTITUTION_SHA256,
    EXPECTED_HUMAN_PROJECTION_SHA256,
    EXPECTED_MODEL_PROJECTION_SHA256,
    EXPECTED_PROTECTED_SCHEDULE_SHA256,
    EXPECTED_REVIEWER_SAFE_STATE_INVENTORY_SHA256,
)
from auragateway.local_abc import quality_development_case_freeze_v1 as case_freeze
from auragateway.local_abc import quality_development_evaluation_v2 as subject
from auragateway.local_abc import quality_semantic_projection_v1 as semantic_projection


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_successor_prerequisites_bind_existing_subject_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        case_freeze,
        "verify_artifacts",
        lambda _root: SimpleNamespace(
            authoring_case_set_sha256=EXPECTED_AUTHORING_CASE_SET_SHA256,
            reviewer_safe_state_inventory_sha256=(EXPECTED_REVIEWER_SAFE_STATE_INVENTORY_SHA256),
            protected_schedule_sha256=EXPECTED_PROTECTED_SCHEDULE_SHA256,
        ),
    )
    monkeypatch.setattr(
        semantic_projection,
        "verify_materialized_projections",
        lambda _root: SimpleNamespace(
            human_projection_sha256=EXPECTED_HUMAN_PROJECTION_SHA256,
            model_projection_sha256=EXPECTED_MODEL_PROJECTION_SHA256,
            canonical_semantic_parity=True,
        ),
    )

    receipt = subject.verify_prerequisites(_repo_root())

    assert receipt.status == "J7L_REFERENCE_SUCCESSOR_PREREQUISITES_PASS"
    assert receipt.constitution_sha256 == EXPECTED_CONSTITUTION_SHA256
    assert receipt.provider_requests_performed == 0
    assert receipt.jev_requests_performed == 0
    assert receipt.network_access_performed is False
    assert receipt.next_gate == "FREEZE_J7L_REFERENCE_JUDGE_BINDING_V1"
