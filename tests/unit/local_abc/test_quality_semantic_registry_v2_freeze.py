from __future__ import annotations

import json
from pathlib import Path

from auragateway.local_abc import quality_semantic_registry_v2_freeze as subject


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_freeze_binds_exact_registry_hashes() -> None:
    freeze = subject.build_freeze(_repo_root())

    assert freeze.registry_sha256 == subject.EXPECTED_REGISTRY_SHA256
    assert freeze.registry_artifact_file_sha256 == subject.EXPECTED_REGISTRY_ARTIFACT_SHA256


def test_freeze_preserves_shared_semantic_authority() -> None:
    freeze = subject.build_freeze(_repo_root())
    policy = freeze.projection_policy

    assert policy.human_projection_uses_registry is True
    assert policy.model_projection_uses_registry is True

    assert policy.human_projection_requires_all_criteria is True
    assert policy.model_projection_requires_all_criteria is True

    assert policy.human_projection_requires_all_failure_labels is True
    assert policy.model_projection_requires_all_failure_labels is True

    assert policy.private_human_semantic_augmentation_permitted is False
    assert policy.private_model_semantic_augmentation_permitted is False

    assert policy.semantic_elision_permitted is False
    assert policy.independent_private_ontology_permitted is False

    assert policy.rendering_may_differ is True
    assert policy.semantic_content_may_differ is False


def test_freeze_does_not_promote_historical_final_342() -> None:
    freeze = subject.build_freeze(_repo_root())
    policy = freeze.historical_authority_policy

    assert policy.final_342_human_authority_mutated is False
    assert policy.blinded_v1_rubric_mutated is False

    assert policy.final_342_remains_development_diagnostic is True
    assert policy.final_342_permitted_as_v2_qualification is False

    assert policy.fresh_v2_qualification_required is True

    assert policy.deployment_threshold_selected is False
    assert policy.deployment_threshold_validated is False

    assert policy.jev_request_performed_by_freeze is False
    assert policy.network_access_performed_by_freeze is False


def test_materialized_freeze_is_canonical() -> None:
    repo_root = _repo_root()
    expected = subject.build_freeze(repo_root)
    path = repo_root / subject.FREEZE_PATH

    assert path.is_file()
    assert not path.is_symlink()

    expected_bytes = subject.canonical_json_bytes(expected.model_dump(mode="json")) + b"\n"

    assert path.read_bytes() == expected_bytes

    observed = subject.QualitySemanticRegistryFreezeV1.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    )

    assert observed == expected


def test_freeze_receipt_reports_no_execution_authority() -> None:
    receipt = subject.verify_freeze(_repo_root())

    assert receipt["registry_frozen"] is True
    assert receipt["jev_request_performed"] is False
    assert receipt["network_access_performed"] is False
    assert receipt["deployment_threshold_selected"] is False
    assert receipt["final_342_mutated"] is False
    assert receipt["rubric_v1_mutated"] is False

    assert receipt["next_gate"] == "J7K_SHARED_SEMANTIC_PROJECTION_V1"
