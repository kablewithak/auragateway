# AuraGateway Gate 6 Protected Review Execution

## Purpose

This slice validates the protected execution layer after blinded assignment preparation. It proves that every frozen review slot is covered, every material disagreement is independently adjudicated, and metadata-only agreement and held-out aggregates reproduce from fixed synthetic submissions.

## Runtime boundary

1. Load the frozen review assignments and rubric.
2. Load protected synthetic review submissions.
3. Require one review per assignment and reject extra submissions.
4. Validate assignment identity, role, rubric scores, and verdict consistency.
5. Detect material disagreement for every double-reviewed episode.
6. Require one independent adjudication for each material disagreement.
7. Select the primary outcome when no material disagreement exists.
8. Select the adjudicated outcome when material disagreement exists.
9. Produce metadata-only agreement and held-out quality aggregates.

## Frozen execution evidence

- 23 review assignments
- 23 protected review submissions
- 18 primary reviews
- 5 secondary reviews
- 2 material disagreements
- 2 independent adjudications
- 6 held-out episode outcomes
- no raw conversation, candidate output, reviewer note, or rationale in the report

The fixed held-out aggregate intentionally contains both passing and failing synthetic outcomes so pass/fail aggregation is exercised. It is not a provider-condition result.

## Failure controls

The implementation rejects:

- missing primary or secondary submissions;
- unassigned review IDs;
- review-to-assignment mismatches;
- inconsistent rubric verdicts;
- reviewer independence violations;
- missing adjudications;
- unnecessary adjudications;
- adjudicator independence violations;
- unknown episode split references;
- persisted report or manifest drift.

## Privacy and evidence boundary

Protected submissions retain only review IDs, episode IDs, reviewer identity digests, criterion scores, failure labels, verdicts, and rationale/evidence-note digests. Public reports retain only counts, rates, final metadata-only outcomes, and hashes.

## Claim boundary

This slice is synthetic-data validated. It proves deterministic protected review coverage, disagreement handling, adjudication completeness, reviewer-agreement calculations, and held-out aggregation. It does not prove completed human review or task-quality non-inferiority across A/B/C conditions.
