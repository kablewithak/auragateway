# ADR: Final-342 Analysis Engine V1

Date: 2026-08-31

## Status

Proposed for acceptance.

## Context

The final-342 execution producer, protected-review successor, and measured-quality reducers now
provide the typed execution, review, task-success, citation, unsupported-answer, and unsafe-behavior
facts required for post-run analysis. G10 already froze the final experiment denominator, primary
runtime endpoint, contrasts, paired-bootstrap configuration, and quality non-inferiority thresholds.
No new statistical design is required.

The remaining material boundary is a deterministic engine that reconciles the exact 342-run plan
against final execution evidence, aggregates the 162 functional quality outcomes, derives the
180-run runtime endpoint, applies the frozen paired analysis, and emits bounded North-Star claim
decisions.

The historical G11.6/G11.7 sequence also marked a measured-feedback successor as required before
manifest freeze. Reinspection against the controlling completion extension shows that measured
feedback is required only for feedback-specific claims. It is not an input to the North-Star
runtime effects or the frozen quality non-inferiority decision. Retaining it as a pre-run blocker
would add a phase without changing the validity or interpretation of the final A/B/C experiment.

## Decision

Implement `FINAL_342_ANALYSIS_ENGINE_V1` as a new Local ABC successor without modifying the
execution producer, G11.9 measured-quality reducer, or historical Gate 7 feedback machinery.

### Scientific denominator and identity

The planned-run ledger remains the scientific denominator:

- 342 scheduled trajectories total;
- 162 functional trajectories, 54 per A/B/C condition;
- 180 runtime-microbenchmark trajectories, 60 per A/B/C condition;
- 54 functional comparison pairs and 60 runtime comparison pairs.

The engine requires exact reconciliation among:

1. the frozen planned runs;
2. producer `PlanBinding` records;
3. producer `RuntimeTraceIdentity` records;
4. the declared final execution manifest SHA-256;
5. trajectory terminal records.

The trace-binding seam is required so failed trajectories with no turn measurement are still proven
to belong to the same final execution manifest. A measurement-only manifest check is insufficient.
Unknown, duplicate, missing, or identity-drifting evidence is surfaced as bounded machine-readable
analysis error state. Failed trajectories are not silently deleted or replaced.

### Functional quality aggregation

The engine consumes exactly the G11.9 `MeasuredQualityRunResult` boundary for functional runs.

An explicit failed execution remains task non-success because G11.9 already resolves it as
`task_success=false`. An evidence-incomplete functional result does not become an inferred failure;
it blocks the quality decision.

Per condition the engine derives:

- task-success rate over all 54 scheduled functional trajectories;
- structured-output-validity rate over all 54 scheduled functional trajectories;
- citation-support rate over citation-evaluable candidates;
- unsupported-answer rate over answer-evaluable candidates;
- unsafe-behavior rate over safety-evaluable runs.

Quality passes only when all frozen requirements hold:

- retrieval configuration is unchanged across A/B/C;
- the episode-manifest identity is unchanged across A/B/C;
- structured-output validity is at least 0.95 for every condition;
- B and C do not regress from A in citation support;
- B and C do not increase unsupported-answer rate from A;
- B and C remain within the five-percentage-point task-success non-inferiority margin from A;
- B and C do not increase unsafe-behavior rate from A.

Unavailable denominators or incomplete functional evidence block the quality decision rather than
being guessed.

### Primary runtime endpoint

The frozen primary endpoint remains
`warm-eligible-newly-computed-prefill-tokens-v1`.

For each completed runtime trajectory the engine inspects candidate turns 2, 3, and 4. A turn
contributes `newly_computed_prefill_tokens` only when its typed warm decision is
`warm_eligible`. The trajectory endpoint is the sum of those contributing turns.

A legitimate non-warm candidate turn is excluded and counted; it is not an analysis error. Missing
candidate measurement evidence, or missing primary telemetry on a warm-eligible turn, makes the
trajectory endpoint evidence-incomplete. Route realization that differs from the frozen route
schedule makes the route-dependent endpoint ineligible.

Turn 1 remains a cold descriptive view. Missing cold-turn telemetry is reported through coverage but
does not invalidate an otherwise complete primary warm endpoint.

Observed execution failure is retained as `EXECUTION_FAILED`, not converted into missing evidence.
It prevents that scheduled pair from entering the paired runtime estimate.

### Pairing and statistics

The frozen contrasts are retained exactly:

- B-A: context-construction-policy effect;
- C-B: route-policy / affinity effect;
- C-A: total-system combined effect.

Differences are right condition minus left condition. Lower is better.

For each contrast the engine uses the frozen 60 runtime comparison pairs. A causal effect claim
requires all 60 scheduled pairs to provide complete eligible endpoints. Partial completed-run views
may still be calculated for evidence inspection, but no effect claim is emitted because the frozen
contracts do not define an acceptance rule for partial pair coverage.

The statistical method remains:

- median paired difference;
- 10,000 percentile-bootstrap resamples;
- resampling unit: comparison pair at episode level;
- seed: 20260712;
- 95% interval.

G10 did not freeze a percentile interpolation convention, so this implementation fixes the missing
deterministic software detail before final results exist: empirical quantiles use linear
interpolation at position `p * (n - 1)` in the sorted bootstrap estimates.

A runtime improvement direction is established only when both frozen rules hold:

1. the median paired difference is below zero; and
2. the 95% interval upper bound is below zero.

No additional practical-effect magnitude threshold is invented.

### Claim precedence

Quality non-inferiority precedes all runtime improvement claims.

For each North-Star contrast the engine emits one bounded state:

- `SUPPORTED`: quality passed, all 60 runtime pairs are eligible, and the frozen direction/interval
  rule is satisfied;
- `NOT_ESTABLISHED`: quality passed and runtime evidence is complete, but the frozen direction or
  interval rule is not satisfied;
- `BLOCKED`: quality is failed/incomplete or the runtime contrast is incomplete.

`NOT_ESTABLISHED` is not a claim of no effect. `BLOCKED` is not a claim that the experiment itself
failed.

### Feedback reconciliation

This ADR supersedes only the historical pre-run blocking interpretation of measured feedback.

- measured feedback is **not** required for the North-Star A/B/C runtime or quality claims;
- measured feedback **is** required before making any feedback-specific claim;
- feedback-specific claims without measured feedback remain prohibited;
- historical Gate 7 artifacts are not modified or reinterpreted as measured evidence.

This removes one non-decision-relevant pre-run phase without weakening any North-Star acceptance
criterion.

### Authorization boundary

This engine is deterministic analysis software. Its implementation does not freeze the final
execution manifest, authorize model/GPU/Kaggle execution, consume an execution authorization, or
permit effect claims from the current development state.

## Consequences

The analysis-engine input seam is now complete using existing producer, runtime, G11.9, G10, and
planned-ledger contracts. No producer modification, measured-quality modification, new statistical
design, or measured-feedback successor is required before the North-Star experiment.

The next material boundary is one offline end-to-end orchestration and integration rehearsal. That
rehearsal should prove composition of the frozen plan, execution producer, protected review,
measured quality, and this analysis engine before manifest freeze.

## Rejected alternatives

Creating a standalone measured-feedback successor before the analysis engine was rejected because
its absence cannot change North-Star experiment eligibility, quality non-inferiority, or any B-A,
C-B, or C-A claim. It remains necessary only if a feedback-specific claim is later added.

Checking final-manifest identity only on observed measurements was rejected because failed runs can
lack measurements while still belonging to the scientific denominator.

Treating every non-warm candidate turn as missing telemetry was rejected because the frozen endpoint
explicitly includes only warm-eligible candidate turns.

Letting missing cold-turn telemetry invalidate the primary endpoint was rejected because G10 keeps
cold results as a separately reported descriptive view.

Allowing partial runtime pair coverage to support an effect claim was rejected because no frozen
missing-pair acceptance rule exists. Partial views remain evidence, not claim authority.

Adding a practical-effect threshold was rejected because G10 froze no such threshold.

## Next gate

`AUTHOR_FINAL_342_OFFLINE_ORCHESTRATION_AND_INTEGRATION_REHEARSAL_V1`
