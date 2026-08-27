# ADR: Measured A/B/C Repetition and Statistical Freeze V1

- **Date:** 2026-08-27
- **Status:** Proposed for G10 merge
- **Scope:** Local full measured A/B/C final-run design
- **Execution authority:** None

## Context

Kaggle saved Version `345461230` passed the governed variance-pilot successor V2
transaction and was accepted at repository gate G9. The accepted boundary permits
a repetition freeze but does not itself freeze repetitions, statistical analysis,
the final execution manifest, or any new measured execution authority.

The Benchmark Constitution 1.0.0 already freezes:

- 18 functional episodes, 3 conditions, 3 repetitions, 162 trajectories;
- 6 runtime-microbenchmark episodes, 3 conditions, 10 repetitions, 180 trajectories;
- the exact functional and runtime counterbalance schedules;
- paired percentile bootstrap reporting with 10,000 samples, 95% confidence,
  comparison-pair-at-episode-level resampling, and seed `20260712`;
- quality non-inferiority rules;
- cold/warm classification and cache-namespace isolation;
- retry, exclusion, rerun, denominator, adjudication, and claim-language rules.

The existing final planned-run ledger already materializes 342 trajectories and
1,368 turns with SHA-256:

`c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c`

The V2 pilot added stronger local-vLLM cache telemetry than the older final-run
line. G10 therefore must freeze the final analysis endpoint before the final
execution manifest is requalified.

## Decision

### Repetitions

Freeze the existing constitution and planned ledger without regenerating them:

- functional: 18 episodes × 3 conditions × 3 repetitions = 162 trajectories;
- runtime: 6 episodes × 3 conditions × 10 repetitions = 180 trajectories;
- total: 342 trajectories, 1,368 turns.

The exact existing planned-run ledger is authority for run identities and
counterbalanced ordering.

### Primary runtime endpoint

Freeze `warm-eligible-newly-computed-prefill-tokens-v1` as the primary runtime
endpoint.

For each runtime trajectory:

1. retain turn 1 as cold evidence;
2. include turns 2–4 in the primary endpoint only when they satisfy the frozen
   warm-eligibility contract;
3. sum `newly_computed_prefill_tokens` over the eligible warm turns;
4. compare paired trajectories using intervention-minus-baseline orientation:
   `B-A`, `C-B`, and `C-A`;
5. lower is better.

This endpoint is chosen because it directly measures avoidable prefill work,
which is closer to the cache-affinity mechanism than latency alone. Latency,
cached-prefix evidence, cost, and cold-view measurements remain secondary
reporting families subject to their telemetry-sufficiency gates.

The current final 342-trajectory runner predates this V2 telemetry field.
Therefore G10 explicitly requires final-runner and execution-manifest
requalification before the final execution manifest may freeze.

### Statistical contract

Use the already-frozen `paired-bootstrap-v1` configuration:

- percentile bootstrap;
- comparison pair at episode level as the resampling unit;
- 10,000 bootstrap samples;
- 95% confidence interval;
- random seed `20260712`;
- median paired difference as the primary point estimator.

For the lower-is-better primary runtime endpoint, a positive runtime-improvement
claim after final repository acceptance requires both:

- a negative point estimate; and
- a 95% bootstrap interval whose upper bound is below zero.

This is a benchmark-specific uncertainty rule, not an academic significance
claim and not a universal-generalization claim.

### Quality non-inferiority

No runtime improvement may be accepted unless `quality-non-inferiority-v1`
passes:

- task-success regression no greater than 5 percentage points;
- citation support does not regress;
- structured-output validity at least 95%;
- unsupported-answer rate does not increase;
- retrieval configuration is unchanged;
- no new unsafe route/retry/escalation/refusal pattern appears;
- comparison eligibility is valid.

The frozen blinded-review protocol remains unchanged: deterministic checks and
primary rubric review cover 100% of eligible outputs; 25% receive independent
double review using seed `20260712`, stratified by condition and terminal
decision, with reviewers blinded to condition, route, latency, cache, and cost.

### Cold/warm and reset policy

- no synthetic pre-warm model requests;
- first turn of each trajectory is cold;
- primary runtime analysis uses only warm-eligible turns;
- every condition/comparison pair/replication keeps a distinct cache namespace;
- cross-condition namespace reuse is prohibited;
- namespace identity is the logical reset/isolation boundary;
- provider failure, session reset, benchmark transition, TTL failure, route
  mismatch, prefix mismatch, or namespace mismatch blocks warm eligibility;
- ambiguous cache state remains unavailable/ambiguous;
- cold and warm results are reported separately.

## Alternatives considered

### Make latency the primary endpoint

Rejected for G10. Latency remains important but is noisier and further
downstream than newly-computed prefill work. The accepted pilot showed why a
mechanism-proximal endpoint is valuable.

### Recompute a new 342-run schedule

Rejected. The existing ledger already matches the frozen constitution and is
hash-bound in the current measured-execution authorization design. Regenerating
run identities would add needless invalidation risk.

### Treat G10 as final execution authorization

Rejected. G10 is a deterministic repository freeze only. The final runner and
execution manifest must first be requalified against this freeze, and any later
authorization must remain fresh, explicit, single-use, and separately issued.

## Consequences

After G10 merge:

- `repetition_freeze_established=true`;
- `statistical_freeze_established=true`;
- the primary runtime endpoint is frozen;
- the quality and warm/reset analysis contracts are frozen;
- `execution_manifest_frozen=false`;
- final-runner requalification remains required;
- `final_measured_abc_execution_authorized=false`;
- `new_execution_authorized=false`;
- `effect_claims_permitted=false`.

The next gate is:

`REQUALIFY_FINAL_342_TRAJECTORY_EXECUTION_MANIFEST_AGAINST_G10_FREEZE_V1`
