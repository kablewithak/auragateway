"""Deterministic blinded-review preparation and adjudication controls."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from pydantic import BaseModel

from auragateway.contracts.blinded_quality import (
    AdjudicationRecord,
    BlindedQualityFixtureCase,
    BlindedQualityFixtureResult,
    BlindedQualityRubric,
    BlindedReviewExport,
    CriterionScore,
    DisagreementReason,
    MaterialDisagreement,
    QualityReviewRecord,
    ReviewAssignment,
    ReviewAssignmentManifest,
    ReviewRole,
    ReviewSourceEnvelope,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import BlindedReviewProtocol

_HIDDEN_EXPERIMENT_FIELDS = frozenset(
    {
        "condition_id",
        "provider",
        "model",
        "route",
        "cost",
        "latency",
        "cache_telemetry",
        "run_order",
    }
)


class BlindedQualityError(Exception):
    """Expected workflow failure with a stable machine-readable code."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _model_sha256(model: BaseModel) -> str:
    payload = model.model_dump_json(exclude_none=True)
    normalized = json.dumps(json.loads(payload), sort_keys=True, separators=(",", ":"))
    return _sha256_text(normalized)


def _assignment_identity(protocol_id: str, episode_id: str, role: ReviewRole) -> str:
    return f"{protocol_id}:{episode_id}:{role.value}"


def _make_assignment(
    protocol_id: str,
    episode_id: str,
    role: ReviewRole,
) -> ReviewAssignment:
    identity = _assignment_identity(protocol_id, episode_id, role)
    digest = _sha256_text(identity)
    return ReviewAssignment(
        review_id=f"review-{digest[:24]}",
        episode_id=episode_id,
        role=role,
        assignment_key_sha256=digest,
    )


def build_assignment_manifest(
    episode_ids: Iterable[str],
    protocol: BlindedReviewProtocol,
) -> ReviewAssignmentManifest:
    """Build deterministic primary and 25 percent double-review assignments."""

    normalized_ids = tuple(sorted(episode_ids))
    if len(normalized_ids) != len(set(normalized_ids)):
        raise BlindedQualityError(
            "DUPLICATE_EPISODE_ID",
            "Review assignments require unique episode IDs.",
        )
    if not normalized_ids:
        raise BlindedQualityError(
            "EMPTY_EPISODE_SET",
            "Review assignments require at least one episode.",
        )
    if protocol.primary_review_fraction != 1.0:
        raise BlindedQualityError(
            "PRIMARY_REVIEW_FRACTION_INVALID",
            "All functional episodes require primary review.",
        )
    if protocol.double_review_fraction != 0.25:
        raise BlindedQualityError(
            "DOUBLE_REVIEW_FRACTION_INVALID",
            "Double-review fraction must remain 25 percent.",
        )
    if protocol.double_review_episode_count > len(normalized_ids):
        raise BlindedQualityError(
            "DOUBLE_REVIEW_SAMPLE_TOO_LARGE",
            "Double-review sample exceeds the available episode count.",
        )

    ranked_ids = sorted(
        normalized_ids,
        key=lambda episode_id: (
            _sha256_text(f"{protocol.sampling_seed}:{episode_id}"),
            episode_id,
        ),
    )
    double_review_ids = tuple(sorted(ranked_ids[: protocol.double_review_episode_count]))
    primary = tuple(
        _make_assignment(protocol.protocol_id, episode_id, ReviewRole.PRIMARY)
        for episode_id in normalized_ids
    )
    secondary = tuple(
        _make_assignment(protocol.protocol_id, episode_id, ReviewRole.SECONDARY)
        for episode_id in double_review_ids
    )
    return ReviewAssignmentManifest(
        protocol_id=protocol.protocol_id,
        sampling_seed=protocol.sampling_seed,
        episode_count=len(normalized_ids),
        primary_assignment_count=len(primary),
        secondary_assignment_count=len(secondary),
        double_review_episode_ids=double_review_ids,
        assignments=primary + secondary,
    )


def build_blinded_review_export(
    source: ReviewSourceEnvelope,
    assignment: ReviewAssignment,
) -> BlindedReviewExport:
    """Strip every experimental field before reviewer export."""

    if source.episode_id != assignment.episode_id:
        raise BlindedQualityError(
            "REVIEW_EXPORT_EPISODE_MISMATCH",
            "Review source and assignment refer to different episodes.",
        )
    export = BlindedReviewExport(
        review_id=assignment.review_id,
        episode_id=source.episode_id,
        synthetic_conversation=source.synthetic_conversation,
        terminal_decision_output=source.terminal_decision_output,
        citation_source_ids=source.citation_source_ids,
        deterministic_validation_results=source.deterministic_validation_results,
    )
    leaked = _HIDDEN_EXPERIMENT_FIELDS & set(export.model_dump())
    if leaked:
        raise BlindedQualityError(
            "HIDDEN_EXPERIMENT_FIELD_LEAKED",
            "Blinded review export retained a prohibited experimental field.",
        )
    return export


def _score_map(scores: tuple[CriterionScore, ...]) -> dict[RubricCriterion, int]:
    return {item.criterion: item.score for item in scores}


def expected_verdict(
    scores: tuple[CriterionScore, ...],
    failure_label_count: int,
    rubric: BlindedQualityRubric,
) -> ReviewVerdict:
    """Calculate the deterministic verdict implied by the frozen rubric."""

    values = [item.score for item in scores]
    passed = (
        sum(values) >= rubric.passing_total_score
        and min(values) >= rubric.minimum_criterion_score
        and failure_label_count == 0
    )
    return ReviewVerdict.PASS if passed else ReviewVerdict.FAIL


def validate_review_record(
    review: QualityReviewRecord,
    assignment: ReviewAssignment,
    rubric: BlindedQualityRubric,
) -> None:
    """Validate one review against its frozen assignment and rubric."""

    if (
        review.review_id != assignment.review_id
        or review.episode_id != assignment.episode_id
        or review.role is not assignment.role
    ):
        raise BlindedQualityError(
            "REVIEW_ASSIGNMENT_MISMATCH",
            "Review record does not match its frozen assignment.",
        )
    implied_verdict = expected_verdict(
        review.criterion_scores,
        len(review.failure_labels),
        rubric,
    )
    if review.verdict is not implied_verdict:
        raise BlindedQualityError(
            "REVIEW_VERDICT_INCONSISTENT",
            "Review verdict does not match rubric scores and failure labels.",
        )


def detect_material_disagreement(
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
    rubric: BlindedQualityRubric,
) -> MaterialDisagreement | None:
    """Detect deterministic disagreements requiring independent adjudication."""

    if primary.episode_id != secondary.episode_id:
        raise BlindedQualityError(
            "REVIEW_EPISODE_MISMATCH",
            "Primary and secondary reviews refer to different episodes.",
        )
    if primary.role is not ReviewRole.PRIMARY or secondary.role is not ReviewRole.SECONDARY:
        raise BlindedQualityError(
            "REVIEW_ROLE_MISMATCH",
            "Material disagreement requires primary and secondary review roles.",
        )
    if primary.reviewer_id_sha256 == secondary.reviewer_id_sha256:
        raise BlindedQualityError(
            "REVIEWER_INDEPENDENCE_VIOLATION",
            "Primary and secondary reviews must use independent reviewers.",
        )

    primary_scores = _score_map(primary.criterion_scores)
    secondary_scores = _score_map(secondary.criterion_scores)
    deltas = {
        criterion: abs(primary_scores[criterion] - secondary_scores[criterion])
        for criterion in RubricCriterion
    }
    reasons: list[DisagreementReason] = []
    if primary.verdict is not secondary.verdict:
        reasons.append(DisagreementReason.VERDICT_MISMATCH)
    if any(delta >= rubric.material_score_delta for delta in deltas.values()):
        reasons.append(DisagreementReason.MATERIAL_SCORE_DELTA)
    if set(primary.failure_labels) != set(secondary.failure_labels):
        reasons.append(DisagreementReason.FAILURE_LABEL_MISMATCH)
    if not reasons:
        return None
    return MaterialDisagreement(
        episode_id=primary.episode_id,
        primary_review_id=primary.review_id,
        secondary_review_id=secondary.review_id,
        reasons=tuple(reasons),
        criterion_score_deltas=deltas,
    )


def validate_adjudication(
    adjudication: AdjudicationRecord,
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
    disagreement: MaterialDisagreement | None,
    rubric: BlindedQualityRubric,
) -> None:
    """Require independent adjudication only for material disagreement."""

    if disagreement is None:
        raise BlindedQualityError(
            "ADJUDICATION_NOT_REQUIRED",
            "Adjudication is prohibited when reviews do not materially disagree.",
        )
    if adjudication.episode_id != disagreement.episode_id:
        raise BlindedQualityError(
            "ADJUDICATION_EPISODE_MISMATCH",
            "Adjudication and disagreement refer to different episodes.",
        )
    if (
        adjudication.primary_review_id != primary.review_id
        or adjudication.secondary_review_id != secondary.review_id
    ):
        raise BlindedQualityError(
            "ADJUDICATION_REVIEW_REFERENCE_MISMATCH",
            "Adjudication does not reference the disputed reviews.",
        )
    reviewer_ids = {primary.reviewer_id_sha256, secondary.reviewer_id_sha256}
    if adjudication.adjudicator_id_sha256 in reviewer_ids:
        raise BlindedQualityError(
            "ADJUDICATOR_INDEPENDENCE_VIOLATION",
            "Adjudicator must be independent from both reviewers.",
        )
    implied_verdict = expected_verdict(
        adjudication.final_criterion_scores,
        len(adjudication.final_failure_labels),
        rubric,
    )
    if adjudication.final_verdict is not implied_verdict:
        raise BlindedQualityError(
            "ADJUDICATION_VERDICT_INCONSISTENT",
            "Adjudication verdict does not match final scores and failure labels.",
        )


def _find_assignment(
    assignments: tuple[ReviewAssignment, ...],
    review_id: str,
) -> ReviewAssignment:
    matches = [item for item in assignments if item.review_id == review_id]
    if len(matches) != 1:
        raise BlindedQualityError(
            "REVIEW_ASSIGNMENT_NOT_FOUND",
            "Fixture review does not have exactly one matching assignment.",
        )
    return matches[0]


def evaluate_fixture_case(
    case: BlindedQualityFixtureCase,
    rubric: BlindedQualityRubric,
) -> BlindedQualityFixtureResult:
    """Execute one fixed workflow case without retaining raw review content."""

    observed_error_code: str | None = None
    material: bool | None = None
    export_sha256: str | None = None
    try:
        primary_assignment = _find_assignment(case.assignments, case.primary_review.review_id)
        export = build_blinded_review_export(case.source, primary_assignment)
        export_sha256 = _model_sha256(export)
        validate_review_record(case.primary_review, primary_assignment, rubric)

        disagreement: MaterialDisagreement | None = None
        if case.secondary_review is not None:
            secondary_assignment = _find_assignment(
                case.assignments,
                case.secondary_review.review_id,
            )
            validate_review_record(case.secondary_review, secondary_assignment, rubric)
            disagreement = detect_material_disagreement(
                case.primary_review,
                case.secondary_review,
                rubric,
            )
            material = disagreement is not None
            if material != case.expected_material_disagreement:
                raise BlindedQualityError(
                    "FIXTURE_MATERIAL_EXPECTATION_MISMATCH",
                    "Observed disagreement did not match fixture expectation.",
                )
            if case.adjudication is not None:
                validate_adjudication(
                    case.adjudication,
                    case.primary_review,
                    case.secondary_review,
                    disagreement,
                    rubric,
                )
            elif disagreement is not None:
                raise BlindedQualityError(
                    "MATERIAL_DISAGREEMENT_UNADJUDICATED",
                    "Material disagreement requires an adjudication record.",
                )
        elif case.adjudication is not None:
            raise BlindedQualityError(
                "ADJUDICATION_WITHOUT_SECONDARY_REVIEW",
                "Adjudication requires primary and secondary reviews.",
            )
    except BlindedQualityError as exc:
        observed_error_code = exc.error_code

    expectation_matched = observed_error_code == case.expected_error_code
    return BlindedQualityFixtureResult(
        case_id=case.case_id,
        expectation_matched=expectation_matched,
        observed_error_code=observed_error_code,
        material_disagreement=material,
        export_sha256=export_sha256,
        negative_control=case.negative_control,
    )
