from __future__ import annotations

import json
from pathlib import Path

import pytest

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceAuditScheduleV1,
    J7LReferenceJudgmentV1,
)
from auragateway.local_abc import j7l_reference_human_audit_comparison_v1 as subject
from auragateway.local_abc import j7l_reference_human_audit_queue_v1 as audit_queue


def _scores(value: int) -> dict[RubricCriterion, int]:
    return {criterion: value for criterion in RubricCriterion}


def _audit_schedule() -> J7LReferenceAuditScheduleV1:
    return J7LReferenceAuditScheduleV1(
        schedule_id="j7l-reference-audit-schedule-v3",
        audit_actor_id_sha256=subject.EXPECTED_OPERATOR_SHA256,
        resolution_owner_id_sha256=subject.EXPECTED_OPERATOR_SHA256,
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


def _human(
    case_id: str,
    *,
    score: int = 3,
    labels: tuple[EpisodeFailureLabel, ...] = (),
) -> audit_queue.Assessment:
    scores = _scores(score)
    verdict = (
        ReviewVerdict.PASS
        if sum(scores.values()) >= 21 and min(scores.values()) >= 2 and not labels
        else ReviewVerdict.FAIL
    )
    return audit_queue.Assessment(
        case_id=case_id,
        work_item_sha256="1" * 64,
        reviewer_safe_state_sha256="2" * 64,
        criterion_scores=scores,
        failure_labels=labels,
        evidence_references=("visible-evidence-1",),
        rationale=(
            "The visible reviewer-safe evidence supports this protected human "
            "assessment and its frozen criterion scores."
        ),
        verdict=verdict,
    )


def _reference(
    case_id: str,
    *,
    score: int = 3,
    labels: tuple[EpisodeFailureLabel, ...] = (),
) -> J7LReferenceJudgmentV1:
    scores = _scores(score)
    verdict = (
        ReviewVerdict.PASS
        if sum(scores.values()) >= 21 and min(scores.values()) >= 2 and not labels
        else ReviewVerdict.FAIL
    )
    return J7LReferenceJudgmentV1(
        case_id=case_id,
        request_id_sha256="3" * 64,
        judge_binding_sha256=subject.EXPECTED_BINDING_SHA256,
        criterion_scores=scores,
        failure_labels=labels,
        evidence_references=("visible-evidence-1",),
        rationale=(
            "The visible evidence supports the model-derived reference judgment "
            "and its declared scores."
        ),
        verdict=verdict,
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _populate_human(root: Path) -> None:
    for case_id in subject._audit_case_ids(_audit_schedule()):
        _write_json(
            root / subject.HUMAN_ASSESSMENT_ROOT / f"{case_id}.json",
            _human(case_id).model_dump(mode="json"),
        )


def _populate_references(root: Path) -> None:
    for index in range(1, 49):
        case_id = f"j7l-dev-{index:03d}"
        _write_json(
            root / subject.REFERENCE_JUDGMENT_ROOT / f"{case_id}.json",
            _reference(case_id).model_dump(mode="json"),
        )


def _patch_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "_load_schedule", lambda _root: _audit_schedule())


def test_compare_case_agreement_is_not_material() -> None:
    comparison = subject.compare_case(
        human=_human("j7l-dev-025"),
        human_sha256="4" * 64,
        reference=_reference("j7l-dev-025"),
        reference_sha256="5" * 64,
    )

    assert comparison.material_disagreement is False
    assert comparison.disagreement_reasons == ()


def test_compare_case_score_delta_two_is_material() -> None:
    comparison = subject.compare_case(
        human=_human("j7l-dev-025", score=1),
        human_sha256="4" * 64,
        reference=_reference("j7l-dev-025", score=3),
        reference_sha256="5" * 64,
    )

    assert comparison.material_disagreement is True
    assert "CRITERION_SCORE_DELTA" in comparison.disagreement_reasons


def test_compare_case_failure_label_set_mismatch_is_material() -> None:
    comparison = subject.compare_case(
        human=_human(
            "j7l-dev-025",
            score=1,
            labels=(EpisodeFailureLabel.REDUNDANT_FEEDBACK,),
        ),
        human_sha256="4" * 64,
        reference=_reference(
            "j7l-dev-025",
            score=1,
            labels=(EpisodeFailureLabel.DUPLICATE_RETRIEVAL_EVIDENCE,),
        ),
        reference_sha256="5" * 64,
    )

    assert comparison.material_disagreement is True
    assert comparison.failure_label_set_mismatch is True
    assert "FAILURE_LABEL_SET_MISMATCH" in comparison.disagreement_reasons


def test_freeze_succeeds_before_model_reference_population_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_schedule(monkeypatch)
    _populate_human(tmp_path)

    freeze = subject.freeze_human_audit(tmp_path)

    assert freeze.status == "J7L_REFERENCE_HUMAN_AUDIT_FROZEN"
    assert len(freeze.assessments) == 28
    assert freeze.model_reference_content_read_before_freeze is False
    assert not (tmp_path / subject.REFERENCE_JUDGMENT_ROOT).exists()


def test_evaluate_requires_frozen_human_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_schedule(monkeypatch)
    _populate_human(tmp_path)
    _populate_references(tmp_path)

    with pytest.raises(
        subject.ReferenceAuditComparisonError,
        match="must be frozen",
    ):
        subject.evaluate(tmp_path)


def test_evaluate_zero_material_disagreements_advances_to_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_schedule(monkeypatch)
    _populate_human(tmp_path)
    _populate_references(tmp_path)
    subject.freeze_human_audit(tmp_path)

    result = subject.evaluate(tmp_path)

    assert result.status == "J7L_REFERENCE_HUMAN_AUDIT_PASS"
    assert result.audit_case_count == 28
    assert result.agreement_count == 28
    assert result.material_disagreement_count == 0
    assert result.reference_set_valid_for_advancement is True
    assert result.coverage_evaluated is False
    assert result.next_gate == "EVALUATE_J7L_REFERENCE_COVERAGE_V1"
    assert result.jev_requests_performed == 0


def test_evaluate_material_disagreement_invalidates_reference_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_schedule(monkeypatch)
    _populate_human(tmp_path)
    _populate_references(tmp_path)
    subject.freeze_human_audit(tmp_path)

    case_id = "j7l-dev-025"
    changed = _reference(
        case_id,
        score=1,
        labels=(EpisodeFailureLabel.REDUNDANT_FEEDBACK,),
    )
    _write_json(
        tmp_path / subject.REFERENCE_JUDGMENT_ROOT / f"{case_id}.json",
        changed.model_dump(mode="json"),
    )

    result = subject.evaluate(tmp_path)

    assert result.status == "J7L_REFERENCE_HUMAN_AUDIT_FAIL"
    assert result.material_disagreement_count == 1
    assert result.material_disagreement_case_ids == (case_id,)
    assert result.reference_set_valid_for_advancement is False
    assert result.next_gate == "STOP_REFERENCE_QUALITY_FAILURE"
    assert result.jev_requests_performed == 0
