from __future__ import annotations

import json
from pathlib import Path

from auragateway.contracts.blinded_quality import RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_semantic_registry_v2 import (
    QualitySemanticRegistryV2,
)
from auragateway.local_abc import quality_semantic_registry_v2_population as subject


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_registry_population_is_complete_and_typed() -> None:
    registry = subject.build_registry()

    assert registry.registry_id == "auragateway-quality-semantic-registry-v2"
    assert set(item.criterion for item in registry.criteria) == set(RubricCriterion)
    assert set(item.label for item in registry.failure_labels) == set(EpisodeFailureLabel)
    assert len(registry.criteria) == 7
    assert len(registry.failure_labels) == 22


def test_all_semantic_sources_exist() -> None:
    repo_root = _repo_root()
    registry = subject.build_registry()

    subject.validate_registry(repo_root, registry)

    for criterion_definition in registry.criteria:
        for source in criterion_definition.semantic_sources:
            path = repo_root / source.repository_path
            assert path.is_file()
            assert not path.is_symlink()

    for failure_definition in registry.failure_labels:
        for source in failure_definition.semantic_sources:
            path = repo_root / source.repository_path
            assert path.is_file()
            assert not path.is_symlink()


def test_population_contains_no_placeholder_semantics() -> None:
    registry = subject.build_registry()

    serialized = registry.model_dump_json().casefold()

    for forbidden in (
        "todo",
        "tbd",
        "placeholder",
        "fill this",
        "unknown semantic",
    ):
        assert forbidden not in serialized


def test_ambiguous_labels_include_normative_v2_authority() -> None:
    registry = subject.build_registry()

    labels_requiring_normative_authority = {
        EpisodeFailureLabel.UNNECESSARY_CLARIFICATION,
        EpisodeFailureLabel.DUPLICATE_RETRIEVAL_EVIDENCE,
        EpisodeFailureLabel.UNRETAINED_FEEDBACK,
        EpisodeFailureLabel.CONTRADICTORY_STATE,
        EpisodeFailureLabel.NOISY_CONTEXT_DILUTION,
        EpisodeFailureLabel.CAPABILITY_MISMATCH,
        EpisodeFailureLabel.PROVIDER_FAILURE_UNHANDLED,
        EpisodeFailureLabel.PRIVACY_VIOLATION,
    }

    definitions = {definition.label: definition for definition in registry.failure_labels}

    for label in labels_requiring_normative_authority:
        assert any(
            source.source_kind == "normative" for source in definitions[label].semantic_sources
        )


def test_evidence_grounding_blocks_vacuous_maximum_interpretation() -> None:
    registry = subject.build_registry()

    definition = next(
        item for item in registry.criteria if item.criterion is RubricCriterion.EVIDENCE_GROUNDING
    )

    assert "does not receive a favourable grounding score" in (
        definition.non_substantive_response_rule
    )
    assert "decision-bearing act" in definition.score_4_anchor


def test_privacy_definition_requires_a_privacy_boundary() -> None:
    registry = subject.build_registry()

    definition = next(
        item
        for item in registry.failure_labels
        if item.label is EpisodeFailureLabel.PRIVACY_VIOLATION
    )

    assert "privacy boundary" in definition.operational_definition
    assert any(
        "non-sensitive fact is fabricated" in rule for rule in definition.does_not_apply_when
    )


def test_invalid_terminal_decision_is_not_generic_terminal_failure() -> None:
    registry = subject.build_registry()

    definition = next(
        item
        for item in registry.failure_labels
        if item.label is EpisodeFailureLabel.INVALID_TERMINAL_DECISION
    )

    assert "requires an answer" in definition.operational_definition
    assert EpisodeFailureLabel.ESCALATION_BYPASSED in definition.related_labels
    assert EpisodeFailureLabel.REFUSAL_BYPASSED in definition.related_labels


def test_materialized_registry_is_canonical() -> None:
    repo_root = _repo_root()
    expected = subject.build_registry()
    path = repo_root / subject.REGISTRY_PATH

    assert path.is_file()
    assert not path.is_symlink()
    assert path.read_bytes() == expected.canonical_bytes() + b"\n"

    observed = QualitySemanticRegistryV2.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    )

    assert observed == expected
    assert observed.sha256() == expected.sha256()


def test_examples_are_not_reused_as_positive_and_near_miss() -> None:
    registry = subject.build_registry()

    for definition in registry.failure_labels:
        assert definition.positive_example != definition.near_miss_example
