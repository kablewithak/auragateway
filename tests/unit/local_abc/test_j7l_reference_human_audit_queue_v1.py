from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v1 import (
    J7LCaseFamily,
    J7LDevelopmentCaseSetV1,
    J7LDevelopmentCaseV1,
)
from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceAuditScheduleV1,
)
from auragateway.local_abc import j7l_reference_human_audit_queue_v1 as subject
from auragateway.local_abc import quality_development_case_freeze_v1 as case_freeze
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
                        "prompt": f"fresh J7L audit case {index}",
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


def _bundle() -> case_freeze.J7LCaseFreezeBundle:
    human, _, parity = semantic_projection.build_projection_bundle(_repo_root())
    return case_freeze.build_bundle(
        _case_set(),
        human_projection=human,
        human_projection_sha256=parity.human_projection_sha256,
        semantic_registry_sha256=parity.source_registry_sha256,
    )


def _audit_schedule() -> J7LReferenceAuditScheduleV1:
    return J7LReferenceAuditScheduleV1(
        schedule_id="j7l-reference-audit-schedule-v3",
        audit_actor_id_sha256=subject.OPERATOR_SHA256,
        resolution_owner_id_sha256=subject.OPERATOR_SHA256,
        protected_secondary_case_ids=tuple(f"j7l-dev-{index:03d}" for index in range(25, 49)),
        additional_spot_check_case_ids=(
            "j7l-dev-001",
            "j7l-dev-002",
            "j7l-dev-013",
            "j7l-dev-014",
        ),
        schedule_frozen_before_reference_execution=True,
        audit_may_rewrite_reference=False,
    )


def _patch_inputs(
    monkeypatch: pytest.MonkeyPatch,
    bundle: case_freeze.J7LCaseFreezeBundle,
    audit: J7LReferenceAuditScheduleV1,
) -> None:
    def fake_load_inputs(
        _root: Path,
    ) -> tuple[
        J7LReferenceAuditScheduleV1,
        case_freeze.J7LReviewScheduleV1,
        case_freeze.J7LReviewerExportV1,
        case_freeze.J7LReviewerExportV1,
    ]:
        return (
            audit,
            bundle.schedule,
            bundle.primary_export,
            bundle.secondary_export,
        )

    def fake_validate_inputs(_root: Path) -> dict[str, object]:
        return {
            "status": "J7L_REFERENCE_HUMAN_AUDIT_INPUTS_VALID",
            "audit_case_count": 28,
        }

    monkeypatch.setattr(subject, "_load_inputs", fake_load_inputs)
    monkeypatch.setattr(subject, "validate_inputs", fake_validate_inputs)


def _submission(
    case_id: str,
    *,
    failure_labels: tuple[EpisodeFailureLabel, ...] = (),
) -> subject.Submission:
    return subject.Submission(
        case_id=case_id,
        criterion_scores=tuple(
            subject.CriterionSubmission(
                criterion=criterion,
                score=3,
                evidence_note=f"Visible evidence supports {criterion.value}.",
            )
            for criterion in RubricCriterion
        ),
        failure_labels=failure_labels,
        evidence_references=("visible-evidence-1",),
        rationale=(
            "The reviewer-safe visible evidence supports the selected criterion "
            "scores and resulting verdict."
        ),
    )


def test_frozen_audit_inventory_is_exact_precommitted_28_cases() -> None:
    bundle = _bundle()
    case_ids = subject._case_ids(_audit_schedule(), bundle.schedule)

    assert case_ids == tuple(
        [f"j7l-dev-{index:03d}" for index in range(25, 49)]
        + ["j7l-dev-001", "j7l-dev-002", "j7l-dev-013", "j7l-dev-014"]
    )
    assert len(case_ids) == 28
    assert len(set(case_ids)) == 28


def test_work_items_use_reviewer_safe_exports_without_model_reference_or_jev() -> None:
    bundle = _bundle()
    audit = _audit_schedule()

    protected = subject._work_item(
        "j7l-dev-025",
        0,
        audit,
        bundle.schedule,
        bundle.primary_export,
        bundle.secondary_export,
    )
    additional = subject._work_item(
        "j7l-dev-001",
        24,
        audit,
        bundle.schedule,
        bundle.primary_export,
        bundle.secondary_export,
    )

    assert protected.audit_stratum == "protected_secondary"
    assert protected.source_review_stream == "secondary"
    assert additional.audit_stratum == "additional_spot_check"
    assert additional.source_review_stream == "primary"

    for work_item in (protected, additional):
        payload = work_item.model_dump(mode="json")
        assert payload["model_reference_included"] is False
        assert payload["jev_output_included"] is False
        assert payload["authoring_targets_included"] is False
        case_freeze.assert_reviewer_export_safe(work_item.reviewer_safe_state)


def test_prepare_materializes_exact_28_items_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle()
    audit = _audit_schedule()
    _patch_inputs(monkeypatch, bundle, audit)

    first = subject.prepare(tmp_path)
    second = subject.prepare(tmp_path)

    assert first["status"] == "J7L_REFERENCE_HUMAN_AUDIT_PACKET_READY"
    assert first["audit_case_count"] == 28
    assert first["created_work_item_count"] == 28
    assert first["created_submission_template_count"] == 28

    assert second["created_work_item_count"] == 0
    assert second["created_submission_template_count"] == 0

    work_items = tuple((tmp_path / subject.WORK_ROOT).glob("j7l-dev-*.json"))
    submissions = tuple((tmp_path / subject.SUBMISSION_ROOT).glob("j7l-dev-*.json"))

    assert len(work_items) == 28
    assert len(submissions) == 28
    assert not (tmp_path / ".local/auragateway/j7l-reference-execution-v3/judgments").exists()


def test_submit_seals_human_assessment_before_reference_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle()
    audit = _audit_schedule()
    _patch_inputs(monkeypatch, bundle, audit)
    subject.prepare(tmp_path)

    submission = _submission("j7l-dev-025")
    submission_path = tmp_path / subject.SUBMISSION_ROOT / "j7l-dev-025.json"
    submission_path.write_text(
        json.dumps(
            submission.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    receipt = subject.submit(tmp_path, submission_path)

    assert receipt["status"] == "J7L_REFERENCE_HUMAN_AUDIT_ASSESSMENT_PERSISTED"
    assert receipt["case_id"] == "j7l-dev-025"
    assert receipt["completed_assessment_count"] == 1
    assert receipt["pending_assessment_count"] == 27
    assert receipt["material_disagreement_evaluated"] is False
    assert receipt["model_reference_content_read"] is False
    assert receipt["jev_requests_performed"] == 0

    assessment_path = tmp_path / subject.ASSESSMENT_ROOT / "j7l-dev-025.json"
    assessment = subject.Assessment.model_validate(
        json.loads(assessment_path.read_text(encoding="utf-8"))
    )

    assert assessment.verdict.value == "pass"
    assert assessment.model_reference_included_in_work_item is False
    assert assessment.jev_output_included_in_work_item is False


def test_submit_derives_fail_when_human_marks_failure_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle()
    audit = _audit_schedule()
    _patch_inputs(monkeypatch, bundle, audit)
    subject.prepare(tmp_path)

    submission = _submission(
        "j7l-dev-026",
        failure_labels=(EpisodeFailureLabel.UNSUPPORTED_CLAIM,),
    )
    submission_path = tmp_path / subject.SUBMISSION_ROOT / "j7l-dev-026.json"
    submission_path.write_text(
        json.dumps(
            submission.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    subject.submit(tmp_path, submission_path)

    assessment_path = tmp_path / subject.ASSESSMENT_ROOT / "j7l-dev-026.json"
    assessment = subject.Assessment.model_validate(
        json.loads(assessment_path.read_text(encoding="utf-8"))
    )

    assert assessment.verdict.value == "fail"
    assert assessment.failure_labels == (EpisodeFailureLabel.UNSUPPORTED_CLAIM,)


def test_submit_rejects_case_outside_frozen_audit_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle()
    audit = _audit_schedule()
    _patch_inputs(monkeypatch, bundle, audit)
    subject.prepare(tmp_path)

    submission = _submission("j7l-dev-003")
    submission_path = tmp_path / subject.SUBMISSION_ROOT / "unauthorized.json"
    submission_path.write_text(
        json.dumps(
            submission.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        subject.HumanAuditQueueError,
        match="outside the frozen audit inventory",
    ):
        subject.submit(tmp_path, submission_path)


def test_assessment_rejects_non_derived_verdict() -> None:
    scores = {criterion: 3 for criterion in RubricCriterion}

    with pytest.raises(ValidationError, match="frozen derivation rule"):
        subject.Assessment(
            case_id="j7l-dev-025",
            work_item_sha256="1" * 64,
            reviewer_safe_state_sha256="2" * 64,
            criterion_scores=scores,
            failure_labels=(),
            evidence_references=("visible-evidence-1",),
            rationale=(
                "The reviewer-safe visible evidence supports the selected criterion "
                "scores and resulting verdict."
            ),
            verdict="fail",
        )
