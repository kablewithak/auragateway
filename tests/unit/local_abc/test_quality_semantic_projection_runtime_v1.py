from __future__ import annotations

from pathlib import Path

from auragateway.contracts.quality_semantic_projection_v1 import (
    EXPECTED_REGISTRY_SHA256,
)
from auragateway.local_abc import quality_semantic_projection_v1 as subject


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_frozen_registry_identity_is_exact() -> None:
    registry = subject.load_frozen_registry(_repo_root())

    assert registry.sha256() == EXPECTED_REGISTRY_SHA256
    assert len(registry.criteria) == 7
    assert len(registry.failure_labels) == 22


def test_human_and_model_projection_inventories_are_complete() -> None:
    registry = subject.load_frozen_registry(_repo_root())

    human = subject.build_human_projection(registry)
    model = subject.build_model_projection(registry)

    assert len(human.criteria) == 7
    assert len(human.failure_labels) == 22

    assert len(model.criterion_questions) == 7
    assert len(model.failure_questions) == 22

    assert {item.criterion for item in human.criteria} == {
        item.criterion for item in model.criterion_questions
    }
    assert {item.label for item in human.failure_labels} == {
        item.label for item in model.failure_questions
    }


def test_model_rendering_fits_existing_jev_instruction_boundary() -> None:
    registry = subject.load_frozen_registry(_repo_root())
    model = subject.build_model_projection(registry)

    criterion_instruction_lengths = tuple(
        len(item.instructions) for item in model.criterion_questions
    )
    failure_instruction_lengths = tuple(
        len(item.instructions) for item in model.failure_questions
    )
    instruction_lengths = criterion_instruction_lengths + failure_instruction_lengths

    assert instruction_lengths
    assert max(instruction_lengths) <= 2000


def test_both_renderings_reconstruct_exact_frozen_registry() -> None:
    registry = subject.load_frozen_registry(_repo_root())
    human = subject.build_human_projection(registry)
    model = subject.build_model_projection(registry)

    reconstructed_human = subject.reconstruct_registry_from_human_projection(human)
    reconstructed_model = subject.reconstruct_registry_from_model_projection(model)

    assert reconstructed_human.canonical_bytes() == registry.canonical_bytes()
    assert reconstructed_model.canonical_bytes() == registry.canonical_bytes()
    assert reconstructed_human.sha256() == EXPECTED_REGISTRY_SHA256
    assert reconstructed_model.sha256() == EXPECTED_REGISTRY_SHA256


def test_parity_receipt_proves_semantic_parity_without_execution() -> None:
    registry = subject.load_frozen_registry(_repo_root())
    human = subject.build_human_projection(registry)
    model = subject.build_model_projection(registry)

    receipt = subject.build_parity_receipt(registry, human, model)

    assert receipt.status == "J7K_SHARED_SEMANTIC_PROJECTION_V1_PASS"
    assert receipt.criterion_inventory_parity is True
    assert receipt.failure_label_inventory_parity is True
    assert receipt.canonical_semantic_parity is True
    assert receipt.canonical_source_identity_parity is True

    assert receipt.private_human_semantic_augmentation_permitted is False
    assert receipt.private_model_semantic_augmentation_permitted is False
    assert receipt.semantic_elision_permitted is False

    assert receipt.network_access_performed is False
    assert receipt.jev_request_performed is False
    assert receipt.deployment_threshold_selected is False
    assert receipt.deployment_threshold_validated is False

    assert receipt.final_342_mutated is False
    assert receipt.rubric_v1_mutated is False


def test_generated_projection_artifacts_are_deterministic_and_verifiable(
    tmp_path: Path,
) -> None:
    first = subject.write_projection_artifacts(
        _repo_root(),
        output_root=tmp_path,
    )
    second = subject.write_projection_artifacts(
        _repo_root(),
        output_root=tmp_path,
    )
    verified = subject.verify_materialized_projections(
        _repo_root(),
        output_root=tmp_path,
    )

    assert first == second
    assert verified == first

    assert (tmp_path / subject.HUMAN_PROJECTION_PATH).is_file()
    assert (tmp_path / subject.MODEL_PROJECTION_PATH).is_file()
    assert (tmp_path / subject.PARITY_RECEIPT_PATH).is_file()
