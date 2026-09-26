# ADR: J7L Audited/Adjudicated Development Reference V1

**Date:** 2026-09-26
**Status:** Proposed for implementation
**Scope:** J7L development/reference recovery after failed V3 human audit

## Context

J7L Reference Execution V3 completed 48/48 GLM-5.2 judgments under the frozen
`MODEL_DERIVED_REFERENCE` protocol.

The precommitted 28-case blinded human audit then failed its advancement rule:

- material disagreements: 16/28;
- verdict mismatches: 0;
- material criterion-score-delta cases: 11;
- failure-label-set mismatches: 15;
- `reference_set_valid_for_advancement=false`;
- `coverage_evaluated=false`;
- Jev requests: 0;
- next gate: `STOP_REFERENCE_QUALITY_FAILURE`.

The V3 rule was valid and must remain terminal. This ADR does not convert V3
into a pass, rewrite human assessments, rewrite GLM judgments, relax the V3
acceptance rule, or use Jev as a tie-breaker.

Historical Final-342 evidence also showed that exact structured semantic
agreement can be substantially less stable than top-level verdict agreement.
That historical path resolved material human-review disagreement through
independent adjudication. The later semantic-registry/J7K work repaired shared
semantic definitions but did not establish that two independent judges will
produce identical criterion scores and exact label sets.

The current failed audit also sampled only 28 of the 48 frozen J7L cases.
Adjudicating only the 16 known disagreements would leave the 20 unaudited cases
without equivalent human evidence.

## Decision

Introduce a new development-only authority:

`AUDITED_ADJUDICATED_DEVELOPMENT_REFERENCE`

This is a successor authority. It is not a repaired
`MODEL_DERIVED_REFERENCE`.

### Human evidence

The exact frozen 48-case J7L development population is retained.

- Preserve the existing 28 blinded human assessments byte-for-byte.
- Do not rescore or replace those 28 cases.
- Complete blinded human assessment for the remaining 20 cases.
- The remaining human work items are derived only from the already-frozen
  reviewer-safe primary export and the shared J7K human semantic projection.
- GLM judgments, V3 comparison results, Jev outputs, authoring targets, and
  family metadata are excluded from those work items.

The resulting 48 human assessments are development evidence. Because the
remaining 20 are completed after V3 model execution already exists, this
successor must not be represented as a fresh pre-model independent
qualification set.

### Full-48 comparison

Only after all 48 human assessments are complete and frozen may the successor
compare them with the preserved V3 GLM judgments.

The material-disagreement rule remains exactly:

- verdict mismatch; or
- absolute criterion-score delta >= 2; or
- failure-label-set mismatch.

No post-result relaxation is permitted.

### Resolution

For a case with no material disagreement:

`HUMAN_ASSESSMENT` is authoritative for the development reference.

For a case with material disagreement:

`INDEPENDENT_ADJUDICATION` is required.

The adjudication boundary must:

- present the same reviewer-safe evidence;
- present the two structured judgments anonymously as A/B;
- hide whether A or B came from the human assessor or GLM;
- use the same semantic registry/projection;
- require an adjudicator identity distinct from the human assessor;
- prohibit Jev output;
- prohibit authoring targets;
- prohibit mechanical score averaging;
- persist append-only adjudication evidence.

The GLM judgment is therefore an audit/second-opinion signal in this successor.
It is never directly promoted to final authority.

## Claim boundary

This authority may support:

- J7L development evaluation;
- failure analysis;
- threshold development;
- evaluator calibration;
- selection of a candidate procedure for later qualification.

It may not support:

- J7M held-out qualification;
- production evaluator qualification;
- autonomous adjudication claims;
- final A/B/C quality claims;
- production-readiness claims.

J7M remains the future fresh held-out qualification boundary. Any tuning or
procedure selection informed by this exposed J7L population must be frozen
before J7M and evaluated on fresh evidence.

## Alternatives considered

### Retry or reprompt GLM until V3 agrees

Rejected. This would optimize against revealed audit outcomes and erase a valid
negative result.

### Rescore the existing 28 human assessments

Rejected. They are frozen predecessor evidence.

### Adjudicate only the 16 known disagreements

Rejected. The V3 audit observed only 28/48 cases. The remaining 20 cases would
retain unaudited model-derived authority.

### Accept the 12/28 agreements and infer the rest

Rejected. Agreement on a sampled subset does not establish the unaudited tail.

### Treat the 48 human assessments as fresh held-out truth

Rejected. Twenty assessments occur after model-reference execution exists,
even though the model outputs remain blinded from the assessor.

### Complete human evidence for all 48 and use prospective adjudication

Accepted. This preserves V3 as failed evidence, closes the unaudited tail,
reuses the project's established adjudication pattern, and keeps independent
qualification deferred to fresh J7M evidence.

## Implementation gates

### S1 â€” inactive successor contract and remaining-human queue

Implement:

- typed successor policy;
- exact V3 failed-result and human-freeze identity bindings;
- deterministic derivation of the 20 remaining cases;
- blinded work-item materialization;
- append-only successor assessment persistence;
- status/accounting for 28 preserved + 20 remaining.

No provider request. No Jev request. No model-reference content may be read by
the human-review work-item path.

### S2 â€” complete remaining 20 blinded human assessments

After S1 is merged and synchronized:

- prepare the 20 work items;
- complete them one at a time;
- persist append-only assessments;
- freeze the full 48-case human inventory before any full-48 model comparison.

### S3 â€” full-48 comparison

Implement and execute the exact V3 material-disagreement rule over all 48
cases. Preserve per-case comparisons and aggregate counts.

### S4 â€” independent adjudication

Materialize anonymous A/B adjudication only for cases identified by S3.
Complete every required adjudication before producing final development truth.

### S5 â€” development-reference coverage

Construct the 48-case authoritative development reference from:

- human assessment when no material disagreement exists;
- independent adjudication when material disagreement exists.

Run the existing required coverage checks without relaxation.

Only a valid covered development reference may advance to J7L Jev execution.

## Non-claims

This ADR does not establish that GLM-5.2 is a qualified reference judge, that
the human assessor is universally correct, that adjudication will resolve every
case cleanly, that Jev is qualified, or that AuraGateway is production ready.
