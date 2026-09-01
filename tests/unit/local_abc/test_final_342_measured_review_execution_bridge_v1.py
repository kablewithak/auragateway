from __future__ import annotations

from pathlib import Path

import pytest

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    QualityReviewRecord,
    ReviewRole,
    RubricCriterion,
)
from auragateway.local_abc import (
    final_342_measured_review_design_v1 as review_design,
)
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as subject,
)
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)
from auragateway.local_abc import (
    final_342_non_authorizing_runtime_core_v1 as core,
)

ROOT = Path(__file__).resolve().parents[3]


def _turns() -> tuple[review_successor.ReviewerTurn, ...]:
    return tuple(
        review_successor.ReviewerTurn(
            turn_index=index,
            user_message=f"visible user message {index}",
            assistant_output={
                "answer": f"visible assistant output {index}",
            },
        )
        for index in range(1, 5)
    )


def _protected_export() -> review_successor.ProtectedExport:
    ledger = core.load_runtime_plan(ROOT)
    schedule = review_successor.derive_protected_schedule(ROOT)
    secondary_by_run = {item.run_id: item for item in schedule.entries}

    assignments: list[review_successor.ReviewerPayload] = []

    for run in ledger.runs:
        if run.workload is not core.WorkloadId.FUNCTIONAL:
            continue

        review_item_id = core.protected_review_id(run.run_id)

        assignments.append(
            review_successor.ReviewerPayload(
                assignment_id=review_design.role_assignment_id(
                    review_item_id,
                    "primary",
                ),
                review_item_id=review_item_id,
                episode_id=run.episode_id,
                turns=_turns(),
            )
        )

        secondary = secondary_by_run.get(run.run_id)
        if secondary is not None:
            assignments.append(
                review_successor.ReviewerPayload(
                    assignment_id=secondary.secondary_assignment_id,
                    review_item_id=review_item_id,
                    episode_id=run.episode_id,
                    turns=_turns(),
                )
            )

    return review_successor.ProtectedExport(
        review_item_count=162,
        assignment_count=203,
        assignments=tuple(assignments),
    )


def test_assignment_projection_recovers_exact_frozen_review_population() -> None:
    export = _protected_export()
    schedule = review_successor.derive_protected_schedule(ROOT)

    assignments = subject.project_expected_assignments(
        export,
        schedule,
    )

    primary = tuple(item for item in assignments if item.role == "primary")
    secondary = tuple(item for item in assignments if item.role == "secondary")

    assert len(assignments) == 203
    assert len(primary) == 162
    assert len(secondary) == 41
    assert len({item.review_item_id for item in assignments}) == 162
    assert len({item.assignment_id for item in assignments}) == 203


def test_assignment_projection_rejects_unknown_assignment_identity() -> None:
    export = _protected_export()
    schedule = review_successor.derive_protected_schedule(ROOT)

    first = export.assignments[0]
    mutated_first = first.model_copy(update={"assignment_id": ("review-000000000000000000000000")})

    mutated = export.model_copy(
        update={
            "assignments": (
                mutated_first,
                *export.assignments[1:],
            )
        }
    )

    with pytest.raises(
        subject.ReviewBridgeError,
        match=("protected reviewer export contains an assignment that does not match"),
    ):
        subject.project_expected_assignments(
            mutated,
            schedule,
        )


def test_assignment_projection_contains_no_execution_condition_metadata() -> None:
    export = _protected_export()
    schedule = review_successor.derive_protected_schedule(ROOT)

    assignments = subject.project_expected_assignments(
        export,
        schedule,
    )

    fields = set(assignments[0].model_dump(mode="json"))

    assert fields == {
        "assignment_id",
        "review_item_id",
        "episode_id",
        "role",
    }

    forbidden = {
        "run_id",
        "condition_id",
        "route",
        "worker_id",
        "cache_telemetry",
        "latency",
        "cost",
        "planned_order_index",
    }

    assert fields.isdisjoint(forbidden)


def _rubric() -> BlindedQualityRubric:
    return BlindedQualityRubric.model_validate_json(
        (ROOT / subject.RUBRIC_PATH).read_text(encoding="utf-8")
    )


def _submission(
    assignment: subject.ExpectedReviewAssignment,
    *,
    reviewer_key: str = "reviewer-alpha",
    score: int = 3,
) -> subject.ReviewSubmissionDraft:
    return subject.ReviewSubmissionDraft(
        assignment_id=assignment.assignment_id,
        reviewer_key=reviewer_key,
        criterion_scores=tuple(
            subject.CriterionSubmission(
                criterion=criterion,
                score=score,
                evidence_note=(f"visible evidence note for {criterion.value}"),
            )
            for criterion in RubricCriterion
        ),
        rationale="visible reviewer rationale",
    )


def _projected_assignments() -> tuple[
    subject.ExpectedReviewAssignment,
    ...,
]:
    return subject.project_expected_assignments(
        _protected_export(),
        review_successor.derive_protected_schedule(ROOT),
    )


def test_review_record_hashes_raw_submission_and_derives_verdict() -> None:
    assignment = next(item for item in _projected_assignments() if item.role == "primary")

    submission = _submission(assignment)

    review = subject.build_review_record(
        assignment,
        submission,
        _rubric(),
    )

    assert review.role is ReviewRole.PRIMARY
    assert review.verdict.value == "pass"
    assert review.reviewer_id_sha256 == subject._sha256_text(submission.reviewer_key)

    serialized = review.model_dump_json()

    assert submission.reviewer_key not in serialized
    assert submission.rationale not in serialized

    for criterion_submission in submission.criterion_scores:
        assert criterion_submission.evidence_note not in serialized


def test_secondary_review_requires_independent_reviewer() -> None:
    assignments = _projected_assignments()

    secondary = next(item for item in assignments if item.role == "secondary")

    primary = next(
        item
        for item in assignments
        if (item.review_item_id == secondary.review_item_id and item.role == "primary")
    )

    primary_review = subject.build_review_record(
        primary,
        _submission(
            primary,
            reviewer_key="same-reviewer",
        ),
        _rubric(),
    )

    with pytest.raises(
        subject.ReviewBridgeError,
        match="independent reviewers",
    ):
        subject.build_review_record(
            secondary,
            _submission(
                secondary,
                reviewer_key="same-reviewer",
            ),
            _rubric(),
            primary_review=primary_review,
        )


def test_secondary_review_accepts_independent_reviewer() -> None:
    assignments = _projected_assignments()

    secondary = next(item for item in assignments if item.role == "secondary")

    primary = next(
        item
        for item in assignments
        if (item.review_item_id == secondary.review_item_id and item.role == "primary")
    )

    primary_review = subject.build_review_record(
        primary,
        _submission(
            primary,
            reviewer_key="reviewer-primary",
        ),
        _rubric(),
    )

    secondary_review = subject.build_review_record(
        secondary,
        _submission(
            secondary,
            reviewer_key="reviewer-secondary",
        ),
        _rubric(),
        primary_review=primary_review,
    )

    assert secondary_review.role is ReviewRole.SECONDARY
    assert secondary_review.reviewer_id_sha256 != primary_review.reviewer_id_sha256


def test_review_persistence_is_idempotent_and_conflict_safe(
    tmp_path: Path,
) -> None:
    assignment = next(item for item in _projected_assignments() if item.role == "primary")

    review = subject.build_review_record(
        assignment,
        _submission(assignment),
        _rubric(),
    )

    first_path, first_digest, first_created = subject.persist_review_record(
        review,
        tmp_path,
    )

    second_path, second_digest, second_created = subject.persist_review_record(
        review,
        tmp_path,
    )

    assert first_created is True
    assert second_created is False
    assert first_path == second_path
    assert first_digest == second_digest

    conflicting = review.model_copy(
        update={
            "rationale_sha256": "0" * 64,
        }
    )

    with pytest.raises(
        subject.ReviewBridgeError,
        match="differs from submitted review",
    ):
        subject.persist_review_record(
            conflicting,
            tmp_path,
        )


def test_submission_requires_all_seven_unique_rubric_criteria() -> None:
    assignment = next(item for item in _projected_assignments() if item.role == "primary")

    repeated = tuple(
        subject.CriterionSubmission(
            criterion=RubricCriterion.CLARITY,
            score=3,
            evidence_note=f"note {index}",
        )
        for index in range(7)
    )

    with pytest.raises(ValueError):
        subject.ReviewSubmissionDraft(
            assignment_id=assignment.assignment_id,
            reviewer_key="reviewer-alpha",
            criterion_scores=repeated,
            rationale="review rationale",
        )


def _scheduled_review_pair(
    *,
    material_disagreement: bool,
) -> tuple[
    subject.ExpectedReviewAssignment,
    subject.ExpectedReviewAssignment,
    QualityReviewRecord,
    QualityReviewRecord,
]:
    assignments = _projected_assignments()

    secondary_assignment = next(item for item in assignments if item.role == "secondary")

    primary_assignment = next(
        item
        for item in assignments
        if (item.review_item_id == secondary_assignment.review_item_id and item.role == "primary")
    )

    primary_review = subject.build_review_record(
        primary_assignment,
        _submission(
            primary_assignment,
            reviewer_key="reviewer-primary",
            score=3,
        ),
        _rubric(),
    )

    secondary_score = 1 if material_disagreement else 3

    secondary_review = subject.build_review_record(
        secondary_assignment,
        _submission(
            secondary_assignment,
            reviewer_key="reviewer-secondary",
            score=secondary_score,
        ),
        _rubric(),
        primary_review=primary_review,
    )

    return (
        primary_assignment,
        secondary_assignment,
        primary_review,
        secondary_review,
    )


def _adjudication_submission(
    review_item_id: str,
    *,
    adjudicator_key: str = "reviewer-adjudicator",
    score: int = 3,
) -> subject.AdjudicationSubmissionDraft:
    return subject.AdjudicationSubmissionDraft(
        review_item_id=review_item_id,
        adjudicator_key=adjudicator_key,
        criterion_scores=tuple(
            subject.CriterionSubmission(
                criterion=criterion,
                score=score,
                evidence_note=(f"adjudication evidence for {criterion.value}"),
            )
            for criterion in RubricCriterion
        ),
        rationale="independent adjudication rationale",
    )


def test_adjudication_requires_material_disagreement() -> None:
    (
        primary_assignment,
        secondary_assignment,
        primary_review,
        secondary_review,
    ) = _scheduled_review_pair(material_disagreement=False)

    with pytest.raises(
        subject.ReviewBridgeError,
        match="prohibited without material disagreement",
    ):
        subject.build_adjudication_record(
            primary_assignment,
            secondary_assignment,
            _adjudication_submission(primary_assignment.review_item_id),
            primary_review,
            secondary_review,
            _rubric(),
        )


def test_material_disagreement_accepts_independent_adjudication() -> None:
    (
        primary_assignment,
        secondary_assignment,
        primary_review,
        secondary_review,
    ) = _scheduled_review_pair(material_disagreement=True)

    adjudication = subject.build_adjudication_record(
        primary_assignment,
        secondary_assignment,
        _adjudication_submission(primary_assignment.review_item_id),
        primary_review,
        secondary_review,
        _rubric(),
    )

    assert adjudication.episode_id == primary_review.episode_id
    assert adjudication.primary_review_id == primary_review.review_id
    assert adjudication.secondary_review_id == secondary_review.review_id
    assert adjudication.final_verdict.value == "pass"

    serialized = adjudication.model_dump_json()

    assert "reviewer-adjudicator" not in serialized
    assert "independent adjudication rationale" not in serialized


def test_adjudicator_must_be_independent_from_both_reviewers() -> None:
    (
        primary_assignment,
        secondary_assignment,
        primary_review,
        secondary_review,
    ) = _scheduled_review_pair(material_disagreement=True)

    with pytest.raises(
        subject.ReviewBridgeError,
        match="independent from both reviewers",
    ):
        subject.build_adjudication_record(
            primary_assignment,
            secondary_assignment,
            _adjudication_submission(
                primary_assignment.review_item_id,
                adjudicator_key="reviewer-primary",
            ),
            primary_review,
            secondary_review,
            _rubric(),
        )


def test_adjudication_persistence_is_append_only(
    tmp_path: Path,
) -> None:
    (
        primary_assignment,
        secondary_assignment,
        primary_review,
        secondary_review,
    ) = _scheduled_review_pair(material_disagreement=True)

    adjudication = subject.build_adjudication_record(
        primary_assignment,
        secondary_assignment,
        _adjudication_submission(primary_assignment.review_item_id),
        primary_review,
        secondary_review,
        _rubric(),
    )

    first_path, first_digest, first_created = subject.persist_adjudication_record(
        adjudication,
        primary_assignment.review_item_id,
        tmp_path,
    )

    second_path, second_digest, second_created = subject.persist_adjudication_record(
        adjudication,
        primary_assignment.review_item_id,
        tmp_path,
    )

    assert first_created is True
    assert second_created is False
    assert first_path == second_path
    assert first_digest == second_digest

    conflicting = adjudication.model_copy(
        update={
            "rationale_sha256": "0" * 64,
        }
    )

    with pytest.raises(
        subject.ReviewBridgeError,
        match="differs from submitted review",
    ):
        subject.persist_adjudication_record(
            conflicting,
            primary_assignment.review_item_id,
            tmp_path,
        )


def _persist_complete_review_population(
    result_root: Path,
    *,
    disagreement_review_item_id: str | None = None,
) -> tuple[
    tuple[subject.ExpectedReviewAssignment, ...],
    dict[tuple[str, str], QualityReviewRecord],
]:
    assignments = _projected_assignments()
    rubric = _rubric()

    reviews: dict[
        tuple[str, str],
        QualityReviewRecord,
    ] = {}

    for assignment in assignments:
        if assignment.role != "primary":
            continue

        review = subject.build_review_record(
            assignment,
            _submission(
                assignment,
                reviewer_key=(f"primary-{assignment.assignment_id}"),
                score=3,
            ),
            rubric,
        )

        subject.persist_review_record(
            review,
            result_root,
        )

        reviews[
            (
                assignment.review_item_id,
                "primary",
            )
        ] = review

    for assignment in assignments:
        if assignment.role != "secondary":
            continue

        primary_review = reviews[
            (
                assignment.review_item_id,
                "primary",
            )
        ]

        score = 1 if (disagreement_review_item_id == assignment.review_item_id) else 3

        review = subject.build_review_record(
            assignment,
            _submission(
                assignment,
                reviewer_key=(f"secondary-{assignment.assignment_id}"),
                score=score,
            ),
            rubric,
            primary_review=primary_review,
        )

        subject.persist_review_record(
            review,
            result_root,
        )

        reviews[
            (
                assignment.review_item_id,
                "secondary",
            )
        ] = review

    return assignments, reviews


def test_empty_review_accountability_reports_full_missing_population(
    tmp_path: Path,
) -> None:
    result = subject.build_review_accountability(
        _projected_assignments(),
        _rubric(),
        tmp_path,
    )

    assert result.status == "INCOMPLETE"
    assert result.valid_primary_review_count == 0
    assert result.missing_primary_review_count == 162
    assert result.valid_secondary_review_count == 0
    assert result.missing_secondary_review_count == 41
    assert result.complete_secondary_pair_count == 0
    assert result.pending_secondary_pair_count == 41
    assert result.currently_required_adjudication_count == 0
    assert result.adjudication_requirement_fully_determined is False
    assert result.overall_review_evidence_complete is False


def test_complete_review_population_without_disagreement_is_complete(
    tmp_path: Path,
) -> None:
    _persist_complete_review_population(tmp_path)

    result = subject.build_review_accountability(
        _projected_assignments(),
        _rubric(),
        tmp_path,
    )

    assert result.status == "COMPLETE"
    assert result.valid_primary_review_count == 162
    assert result.valid_secondary_review_count == 41
    assert result.complete_secondary_pair_count == 41
    assert result.pending_secondary_pair_count == 0
    assert result.reviewer_independence_violation_count == 0
    assert result.detected_material_disagreement_count == 0
    assert result.currently_required_adjudication_count == 0
    assert result.adjudication_requirement_fully_determined is True
    assert result.review_complete is True
    assert result.adjudication_complete is True
    assert result.overall_review_evidence_complete is True


def test_material_disagreement_remains_incomplete_until_adjudicated(
    tmp_path: Path,
) -> None:
    secondary = next(item for item in _projected_assignments() if item.role == "secondary")

    assignments, reviews = _persist_complete_review_population(
        tmp_path,
        disagreement_review_item_id=(secondary.review_item_id),
    )

    before = subject.build_review_accountability(
        assignments,
        _rubric(),
        tmp_path,
    )

    assert before.review_complete is True
    assert before.detected_material_disagreement_count == 1
    assert before.currently_required_adjudication_count == 1
    assert before.missing_required_adjudication_count == 1
    assert before.unresolved_material_disagreement_count == 1
    assert before.adjudication_complete is False
    assert before.overall_review_evidence_complete is False

    primary_assignment = next(
        item
        for item in assignments
        if (item.review_item_id == secondary.review_item_id and item.role == "primary")
    )

    adjudication = subject.build_adjudication_record(
        primary_assignment,
        secondary,
        _adjudication_submission(
            secondary.review_item_id,
            adjudicator_key=("independent-final-adjudicator"),
        ),
        reviews[
            (
                secondary.review_item_id,
                "primary",
            )
        ],
        reviews[
            (
                secondary.review_item_id,
                "secondary",
            )
        ],
        _rubric(),
    )

    subject.persist_adjudication_record(
        adjudication,
        secondary.review_item_id,
        tmp_path,
    )

    after = subject.build_review_accountability(
        assignments,
        _rubric(),
        tmp_path,
    )

    assert after.valid_adjudication_count == 1
    assert after.missing_required_adjudication_count == 0
    assert after.unresolved_material_disagreement_count == 0
    assert after.adjudication_complete is True
    assert after.overall_review_evidence_complete is True


def test_unexpected_review_artifact_blocks_completion(
    tmp_path: Path,
) -> None:
    _persist_complete_review_population(tmp_path)

    unexpected = tmp_path / "reviews" / "unexpected.json"

    unexpected.write_text(
        "{}\n",
        encoding="utf-8",
    )

    result = subject.build_review_accountability(
        _projected_assignments(),
        _rubric(),
        tmp_path,
    )

    assert result.unexpected_review_file_count == 1
    assert result.review_complete is False
    assert result.overall_review_evidence_complete is False
