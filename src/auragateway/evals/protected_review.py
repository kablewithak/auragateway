"""Protected review coverage, agreement, and held-out aggregation controls."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from auragateway.contracts.blinded_quality import (
    AdjudicationRecord,
    BlindedQualityRubric,
    CriterionScore,
    QualityReviewRecord,
    ReviewAssignment,
    ReviewAssignmentManifest,
    ReviewRole,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeEvaluationSplit
from auragateway.contracts.protected_review import (
    EpisodeReviewOutcome,
    FinalReviewSource,
    Gate6ProtectedReviewExecutionReport,
    HeldOutQualityAggregate,
    ProtectedReviewSubmissionSet,
    ReviewerAgreementMetrics,
)
from auragateway.evals.blinded_quality import (
    BlindedQualityError,
    detect_material_disagreement,
    validate_adjudication,
    validate_review_record,
)


class ProtectedReviewExecutionError(Exception):
    """Expected protected review execution failure with a stable error code."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


def _raise_from_blinded(error: BlindedQualityError) -> None:
    raise ProtectedReviewExecutionError(error.error_code, error.safe_message) from error


def _assignment_map(
    manifest: ReviewAssignmentManifest,
) -> dict[str, ReviewAssignment]:
    return {assignment.review_id: assignment for assignment in manifest.assignments}


def _review_map(
    submissions: ProtectedReviewSubmissionSet,
) -> dict[str, QualityReviewRecord]:
    return {review.review_id: review for review in submissions.reviews}


def _score_map(scores: tuple[CriterionScore, ...]) -> dict[RubricCriterion, int]:
    return {score.criterion: score.score for score in scores}


def _total_score(scores: tuple[CriterionScore, ...]) -> int:
    return sum(score.score for score in scores)


def _require_exact_review_coverage(
    assignments: dict[str, ReviewAssignment],
    reviews: dict[str, QualityReviewRecord],
) -> None:
    missing = tuple(sorted(set(assignments) - set(reviews)))
    if missing:
        raise ProtectedReviewExecutionError(
            "REVIEW_COVERAGE_INCOMPLETE",
            "Every frozen review assignment requires exactly one protected submission.",
        )
    unassigned = tuple(sorted(set(reviews) - set(assignments)))
    if unassigned:
        raise ProtectedReviewExecutionError(
            "UNASSIGNED_REVIEW_SUBMISSION",
            "Protected review submissions must match frozen assignment IDs.",
        )


def _validate_reviews(
    assignments: dict[str, ReviewAssignment],
    reviews: dict[str, QualityReviewRecord],
    rubric: BlindedQualityRubric,
) -> None:
    for review_id in sorted(reviews):
        try:
            validate_review_record(reviews[review_id], assignments[review_id], rubric)
        except BlindedQualityError as exc:
            _raise_from_blinded(exc)


def _adjudication_map(
    submissions: ProtectedReviewSubmissionSet,
) -> dict[str, AdjudicationRecord]:
    return {record.episode_id: record for record in submissions.adjudications}


def _assignment_by_episode(
    manifest: ReviewAssignmentManifest,
) -> dict[str, dict[ReviewRole, ReviewAssignment]]:
    grouped: dict[str, dict[ReviewRole, ReviewAssignment]] = {}
    for assignment in manifest.assignments:
        grouped.setdefault(assignment.episode_id, {})[assignment.role] = assignment
    return grouped


def _build_agreement_metrics(
    double_review_pairs: tuple[tuple[QualityReviewRecord, QualityReviewRecord], ...],
    material_disagreement_count: int,
    adjudication_count: int,
) -> ReviewerAgreementMetrics:
    verdict_agreements = sum(
        primary.verdict is secondary.verdict for primary, secondary in double_review_pairs
    )
    exact_criterion_agreements = 0
    for primary, secondary in double_review_pairs:
        primary_scores = _score_map(primary.criterion_scores)
        secondary_scores = _score_map(secondary.criterion_scores)
        exact_criterion_agreements += sum(
            primary_scores[criterion] == secondary_scores[criterion]
            for criterion in RubricCriterion
        )
    comparison_count = len(double_review_pairs) * len(RubricCriterion)
    return ReviewerAgreementMetrics(
        double_review_count=len(double_review_pairs),
        verdict_agreement_count=verdict_agreements,
        verdict_agreement_rate=verdict_agreements / len(double_review_pairs),
        criterion_comparison_count=comparison_count,
        exact_criterion_agreement_count=exact_criterion_agreements,
        exact_criterion_agreement_rate=exact_criterion_agreements / comparison_count,
        material_disagreement_count=material_disagreement_count,
        adjudication_count=adjudication_count,
    )


def _build_held_out_aggregate(
    outcomes: tuple[EpisodeReviewOutcome, ...],
) -> HeldOutQualityAggregate:
    held_out = tuple(
        outcome
        for outcome in outcomes
        if outcome.evaluation_split is EpisodeEvaluationSplit.HELD_OUT
    )
    if not held_out:
        raise ProtectedReviewExecutionError(
            "HELD_OUT_OUTCOMES_MISSING",
            "Protected review execution requires held-out episode outcomes.",
        )
    pass_count = sum(outcome.quality_passed for outcome in held_out)
    failure_counts = Counter(
        label.value for outcome in held_out for label in outcome.final_failure_labels
    )
    return HeldOutQualityAggregate(
        held_out_episode_count=len(held_out),
        pass_count=pass_count,
        fail_count=len(held_out) - pass_count,
        pass_rate=pass_count / len(held_out),
        mean_total_score=sum(outcome.final_total_score for outcome in held_out) / len(held_out),
        adjudicated_episode_count=sum(outcome.adjudication_applied for outcome in held_out),
        failure_label_counts=dict(sorted(failure_counts.items())),
    )


def evaluate_protected_review_execution(
    assignment_manifest: ReviewAssignmentManifest,
    rubric: BlindedQualityRubric,
    episode_splits: Mapping[str, EpisodeEvaluationSplit],
    submissions: ProtectedReviewSubmissionSet,
) -> Gate6ProtectedReviewExecutionReport:
    """Validate complete review coverage and aggregate metadata-only outcomes."""

    if submissions.assignment_manifest_id != assignment_manifest.manifest_id:
        raise ProtectedReviewExecutionError(
            "ASSIGNMENT_MANIFEST_ID_MISMATCH",
            "Protected review submissions target a different assignment manifest.",
        )
    if submissions.rubric_id != rubric.rubric_id:
        raise ProtectedReviewExecutionError(
            "RUBRIC_ID_MISMATCH",
            "Protected review submissions target a different quality rubric.",
        )

    assignments = _assignment_map(assignment_manifest)
    reviews = _review_map(submissions)
    _require_exact_review_coverage(assignments, reviews)
    _validate_reviews(assignments, reviews, rubric)

    assignments_by_episode = _assignment_by_episode(assignment_manifest)
    adjudications = _adjudication_map(submissions)
    outcomes: list[EpisodeReviewOutcome] = []
    double_review_pairs: list[tuple[QualityReviewRecord, QualityReviewRecord]] = []
    used_adjudication_episodes: set[str] = set()
    reviewer_independence_verified = True

    for episode_id in sorted(assignments_by_episode):
        split = episode_splits.get(episode_id)
        if split is None:
            raise ProtectedReviewExecutionError(
                "EPISODE_SPLIT_NOT_FOUND",
                "A frozen review assignment references an episode without a split.",
            )
        episode_assignments = assignments_by_episode[episode_id]
        primary_assignment = episode_assignments.get(ReviewRole.PRIMARY)
        if primary_assignment is None:
            raise ProtectedReviewExecutionError(
                "PRIMARY_REVIEW_ASSIGNMENT_MISSING",
                "Every functional episode requires one primary assignment.",
            )
        primary = reviews[primary_assignment.review_id]
        secondary_assignment = episode_assignments.get(ReviewRole.SECONDARY)
        secondary = reviews[secondary_assignment.review_id] if secondary_assignment else None
        adjudication = adjudications.get(episode_id)
        material = False

        if secondary is not None:
            double_review_pairs.append((primary, secondary))
            try:
                disagreement = detect_material_disagreement(primary, secondary, rubric)
            except BlindedQualityError as exc:
                reviewer_independence_verified = False
                _raise_from_blinded(exc)
            material = disagreement is not None
            if disagreement is not None:
                if adjudication is None:
                    raise ProtectedReviewExecutionError(
                        "MATERIAL_DISAGREEMENT_UNADJUDICATED",
                        "Every material disagreement requires one independent adjudication.",
                    )
                try:
                    validate_adjudication(
                        adjudication,
                        primary,
                        secondary,
                        disagreement,
                        rubric,
                    )
                except BlindedQualityError as exc:
                    reviewer_independence_verified = False
                    _raise_from_blinded(exc)
                used_adjudication_episodes.add(episode_id)
            elif adjudication is not None:
                raise ProtectedReviewExecutionError(
                    "ADJUDICATION_NOT_REQUIRED",
                    "Adjudication is prohibited without material disagreement.",
                )
        elif adjudication is not None:
            raise ProtectedReviewExecutionError(
                "ADJUDICATION_WITHOUT_SECONDARY_REVIEW",
                "Adjudication requires a frozen secondary-review assignment.",
            )

        if adjudication is not None and material:
            final_scores = adjudication.final_criterion_scores
            final_labels = adjudication.final_failure_labels
            final_verdict = adjudication.final_verdict
            final_source = FinalReviewSource.ADJUDICATION
        else:
            final_scores = primary.criterion_scores
            final_labels = primary.failure_labels
            final_verdict = primary.verdict
            final_source = FinalReviewSource.PRIMARY

        outcomes.append(
            EpisodeReviewOutcome(
                episode_id=episode_id,
                evaluation_split=split,
                primary_review_id=primary.review_id,
                secondary_review_id=secondary.review_id if secondary else None,
                material_disagreement=material,
                adjudication_applied=final_source is FinalReviewSource.ADJUDICATION,
                final_source=final_source,
                final_verdict=final_verdict,
                final_total_score=_total_score(final_scores),
                final_failure_labels=final_labels,
                quality_passed=final_verdict.value == "pass",
            )
        )

    unused_adjudications = set(adjudications) - used_adjudication_episodes
    if unused_adjudications:
        raise ProtectedReviewExecutionError(
            "UNUSED_ADJUDICATION_SUBMISSION",
            "Every protected adjudication must resolve one material disagreement.",
        )

    outcome_tuple = tuple(outcomes)
    agreement = _build_agreement_metrics(
        tuple(double_review_pairs),
        material_disagreement_count=len(used_adjudication_episodes),
        adjudication_count=len(submissions.adjudications),
    )
    held_out = _build_held_out_aggregate(outcome_tuple)
    primary_count = sum(review.role is ReviewRole.PRIMARY for review in submissions.reviews)
    secondary_count = sum(review.role is ReviewRole.SECONDARY for review in submissions.reviews)

    return Gate6ProtectedReviewExecutionReport(
        execution_id=submissions.execution_id,
        assignment_manifest_id=assignment_manifest.manifest_id,
        rubric_id=rubric.rubric_id,
        assignment_count=len(assignment_manifest.assignments),
        review_count=len(submissions.reviews),
        primary_review_count=primary_count,
        secondary_review_count=secondary_count,
        adjudication_count=len(submissions.adjudications),
        assignment_coverage_complete=True,
        secondary_coverage_complete=(
            secondary_count == assignment_manifest.secondary_assignment_count
        ),
        adjudication_coverage_complete=(
            len(submissions.adjudications) == len(used_adjudication_episodes)
        ),
        reviewer_independence_verified=reviewer_independence_verified,
        outcomes=outcome_tuple,
        agreement=agreement,
        held_out=held_out,
        execution_controls_passed=True,
    )
