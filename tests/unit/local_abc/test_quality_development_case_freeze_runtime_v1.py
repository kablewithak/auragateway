from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v1 import (
    J7LCaseFamily,
    J7LDevelopmentCaseSetV1,
    J7LDevelopmentCaseV1,
)
from auragateway.local_abc import quality_development_case_freeze_v1 as subject
from auragateway.local_abc import quality_semantic_projection_v1 as semantic_projection


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _case_set() -> J7LDevelopmentCaseSetV1:
    families = tuple(J7LCaseFamily)
    cases: list[J7LDevelopmentCaseV1] = []

    for index in range(48):
        family = families[index // 12]
        cases.append(
            J7LDevelopmentCaseV1(
                case_id=f"j7l-dev-{index + 1:03d}",
                case_index=index,
                family=family,
                reviewer_safe_state={
                    "visible_case": {
                        "prompt": f"fresh J7L case {index}",
                        "candidate": "candidate output",
                    }
                },
                positive_label_targets=(
                    (EpisodeFailureLabel.UNSUPPORTED_CLAIM,) if index % 2 else ()
                ),
                near_miss_label_targets=(
                    (EpisodeFailureLabel.CITATION_UNSUPPORTED,)
                    if family is J7LCaseFamily.ONTOLOGY_NEAR_MISS
                    else ()
                ),
                terminal_action_evidence_material=(
                    family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE
                ),
            )
        )

    return J7LDevelopmentCaseSetV1(cases=tuple(cases))


def _bundle() -> subject.J7LCaseFreezeBundle:
    human, _, parity = semantic_projection.build_projection_bundle(_repo_root())
    return subject.build_bundle(
        _case_set(),
        human_projection=human,
        human_projection_sha256=parity.human_projection_sha256,
        semantic_registry_sha256=parity.source_registry_sha256,
    )


def test_bundle_freezes_exact_primary_and_secondary_counts() -> None:
    bundle = _bundle()

    assert len(bundle.schedule.entries) == 48
    assert bundle.primary_export.item_count == 48
    assert bundle.secondary_export.item_count == 24
    assert bundle.public_receipt.primary_assignment_count == 48
    assert bundle.public_receipt.secondary_assignment_count == 24

    secondary_entries = tuple(
        item for item in bundle.schedule.entries if item.secondary_assignment_id is not None
    )
    assert len(secondary_entries) == 24
    assert {item.family for item in secondary_entries} == {
        J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE,
        J7LCaseFamily.ONTOLOGY_NEAR_MISS,
    }


def test_reviewer_exports_do_not_contain_authoring_metadata() -> None:
    bundle = _bundle()

    for export in (bundle.primary_export, bundle.secondary_export):
        payload = export.model_dump(mode="json")
        keys = set(subject._walk_keys(payload))
        assert not keys.intersection(subject.AUTHORING_ONLY_KEYS)

        serialized = json.dumps(payload, sort_keys=True)
        assert "positive_label_targets" not in serialized
        assert "near_miss_label_targets" not in serialized
        assert '"family"' not in serialized
        assert '"case_id"' not in serialized


def test_reviewer_export_embeds_exact_human_semantic_projection() -> None:
    bundle = _bundle()
    human, _, parity = semantic_projection.build_projection_bundle(_repo_root())

    assert bundle.primary_export.semantic_projection == human
    assert bundle.secondary_export.semantic_projection == human
    assert bundle.public_receipt.human_projection_sha256 == parity.human_projection_sha256
    assert bundle.public_receipt.semantic_registry_sha256 == parity.source_registry_sha256


def test_schedule_and_export_identities_are_deterministic() -> None:
    first = _bundle()
    second = _bundle()

    assert subject.artifact_bytes(first.schedule) == subject.artifact_bytes(second.schedule)
    assert subject.artifact_bytes(first.primary_export) == subject.artifact_bytes(
        second.primary_export
    )
    assert subject.artifact_bytes(first.secondary_export) == subject.artifact_bytes(
        second.secondary_export
    )
    assert first.public_receipt == second.public_receipt


def test_public_receipt_is_metadata_only() -> None:
    bundle = _bundle()
    payload = bundle.public_receipt.model_dump(mode="json")

    assert payload["authoring_targets_publicly_persisted"] is False
    assert payload["reviewer_export_contains_authoring_metadata"] is False
    assert payload["model_reveal_performed"] is False
    assert payload["provider_requests_performed"] == 0
    assert payload["jev_requests_performed"] == 0
    assert payload["human_truth_frozen"] is False
    assert payload["threshold_selected"] is False

    keys = set(subject._walk_keys(payload))
    assert "positive_label_targets" not in keys
    assert "near_miss_label_targets" not in keys
    assert "reviewer_safe_state" not in keys


def test_load_case_set_rejects_identity_drift(tmp_path: Path) -> None:
    case_set = _case_set()
    path = tmp_path / "case-set.json"
    path.write_text(
        json.dumps(case_set.model_dump(mode="json"), sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        subject.J7LCaseFreezeError,
        match="SHA-256 drifted",
    ):
        subject._load_case_set(
            path,
            expected_sha256="0" * 64,
        )
