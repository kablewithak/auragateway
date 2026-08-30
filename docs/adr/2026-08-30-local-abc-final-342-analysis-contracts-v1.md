# ADR: Final 342 Post-Run Analysis Contracts V1

**Date:** 2026-08-30
**Status:** Proposed for final-342 analysis-contract acceptance
**Base main:** `9888f05a8c1c3b36fa9728b2bd2790f5704f4109`
**Execution authority:** None

## Context

The final experiment already has a frozen 342-trajectory plan, a merged execution producer,
and a merged measured protected-review design. The remaining pre-freeze analysis problem is
not statistical formula selection. G10 already freezes the runtime endpoint, quality
thresholds, bootstrap configuration, warm/reset policy, and claim order.

The unresolved problem is evidence meaning. The final producer has durable attempt,
measurement, admission, commit, failure, and terminal ledgers, but its
`scheduled_request_count` is operational: it is derived from attempt reservations. It is
therefore not the scientific denominator for the frozen 1,368 logical turns.

The scientific denominator must remain the frozen planned-run ledger. Analysis must also
consume measured quality, protected review, feedback, eligibility, and failure evidence
without reconstructing meaning from logs after the governed execution.

## Decision

Adopt:

`FINAL_342_POST_RUN_ANALYSIS_CONTRACTS_V1`

The analysis boundary is divided into accountability, comparison eligibility, quality,
runtime, feedback, statistics, and claim generation. Each family has one authoritative
evidence source and an explicit fail-closed relationship to later claims.

## Scientific denominator authority

The frozen planned-run ledger remains authority for scheduled scientific work:

- 342 scheduled trajectories;
- 162 functional trajectories;
- 180 runtime-microbenchmark trajectories;
- 1,368 scheduled logical turns; and
- at most 2,736 physical request attempts.

The producer's `request_reconciliation_v1.json.scheduled_request_count` is not promoted to
the logical-turn denominator. In the merged producer it advances with attempt reservations,
so it is an operational attempt-accountability counter.

Physical attempts come from `attempt_action_ledger_v1.json.reservations`. HTTP completion,
admission, commit, and terminal state come from their respective durable ledgers.

Every report retains both completed-run and failure-accounted views. Missing terminal
evidence is evidence incompleteness, not permission to shrink the planned denominator.

## Execution accountability

Every planned run ID must reconcile against final evidence. Unknown run IDs are prohibited.

The final analysis must preserve the distinction between:

1. scheduled trajectories and logical turns from the frozen plan;
2. physical attempts from reservations;
3. transport completions from transport outcomes;
4. admitted outputs from admission evidence;
5. committed turns from state-mutation decisions; and
6. completed or failed trajectories from the terminal ledger.

Hidden retries and replacement cases remain prohibited. Metric-specific exclusions use only
predeclared exclusion rules, remain visible in the evidence bundle, and remain present in
failure-accounted reporting. Poor quality, latency, or an unfavorable result is never an
exclusion reason.

## Comparison eligibility

Eligibility is evaluated before metrics.

Compared runs require compatible final execution-manifest identity and configuration
fingerprints. Route-dependent metrics require route realization. Telemetry-dependent
families require sufficient typed telemetry. The primary runtime endpoint may consume only
turns that pass the frozen warm-eligibility contract.

Partially eligible metric families are permitted only where explicitly supported by the
frozen constitution. Human-authored report prose cannot override an ineligible machine
decision.

The comparison result must retain compared run IDs, mismatched fields, invalidated metrics,
invalidated claims, and required reruns.

## Measured quality analysis

The functional quality population remains 162 planned trajectories. The 180
runtime-microbenchmark trajectories do not replace the functional human-review benchmark.

Every produced candidate requires deterministic quality scoring. A scheduled trajectory
that fails before producing a candidate remains a task non-success under the frozen
denominator policy.

A candidate that exists but loses required protected-review evidence is
`EVIDENCE_INCOMPLETE`. It is not silently dropped and it does not become a model-quality
failure. The gap blocks establishment of quality non-inferiority and therefore blocks a
runtime-improvement claim.

Every reviewable candidate requires a primary rubric review. The exact 41-case secondary
schedule is predeclared before manifest freeze. Selected non-reviewable cases are not
replaced. Material primary/secondary disagreement requires independent adjudication.

The frozen quality thresholds remain:

- structured-output validity at least 95 percent;
- task-success regression no greater than five percentage points;
- no citation-support regression;
- no unsupported-answer-rate increase;
- unchanged retrieval configuration; and
- no new unsafe route, retry, escalation, or refusal pattern.

The historical quality non-inferiority implementation is a synthetic dry-run boundary. Its
threshold logic is reusable, but its synthetic contract is not the final measured input
schema.

Current accepted assets do not define one exact measured reducer that converts deterministic
quality plus completed human review into the final `task_success_count`. This design does
not guess that mapping. A measured task-success reducer must be defined, tested, and bound
before execution-manifest freeze.

The same rule applies to the frozen unsafe-behavior non-regression check: the measured
reducer must be explicit rather than inferred from prose after the run.

## Runtime analysis

The primary runtime population contains 180 trajectories and 60 comparison pairs. Every
pair contains conditions A, B, and C for one episode and replication.

The primary endpoint remains:

`warm-eligible-newly-computed-prefill-tokens-v1`

Turn 1 is retained as cold evidence. Turns 2 through 4 contribute only when they satisfy the
frozen warm-eligibility contract. The endpoint sums
`newly_computed_prefill_tokens` over those eligible warm turns.

The frozen contrast orientations remain:

- `B-A` for context-construction policy;
- `C-B` for route policy; and
- `C-A` for the total system.

Lower is better. Cold and warm views remain separate. Warm-ineligible turns and missing
telemetry remain visible in coverage and failure-accounted reporting rather than
disappearing from evidence.

Monetary cost comparison remains out of scope for the final local-runtime claim family.

## Statistical and claim contract

Use `paired-bootstrap-v1` exactly:

- percentile bootstrap;
- comparison pair at episode level as the resampling unit;
- 10,000 bootstrap samples;
- 95 percent confidence interval;
- seed `20260712`; and
- median paired difference as the primary point estimator.

For the lower-is-better primary endpoint, a positive runtime-improvement claim requires both
a negative point estimate and a confidence interval whose upper bound is below zero.

The benchmark does not claim academic statistical significance or universal
generalization.

Comparative reporting preserves the frozen precedence:

1. bundle schema and hash verification;
2. run-accountability verification;
3. execution-manifest and configuration-fingerprint eligibility;
4. telemetry-sufficiency decision;
5. quality non-inferiority decision;
6. metric calculation; and
7. claim generation.

Failure at an earlier gate blocks dependent claims. Faster runtime with a failed quality
gate is classified as a quality regression, not an improvement.

## Feedback analysis

Feedback evidence remains a separate trace-level evidence family covering validity, novelty,
retention, later action change, and task sufficiency.

The project does not calculate a universal EFC score.

The current feedback contracts are synthetic and explicitly prohibit measured execution.
A measured feedback successor is therefore required before final manifest freeze if
feedback claims are to be produced from the governed execution.

## Reuse and implementation boundary

This decision deliberately does not authorize a producer rewrite.

The next gate must audit the exact producer-to-review-to-analysis seam. That audit maps every
required analysis field to one authoritative producer, protected-review, deterministic
quality, feedback, or frozen-plan source.

The seam audit must distinguish true missing hooks from already-sufficient evidence. Only a
proven missing hook may justify a bounded producer repair.

Known pre-freeze implementation obligations now include:

- materializing the exact 41-case review schedule;
- implementing the measured protected-review exporter;
- implementing the measured task-success reducer;
- implementing the unsafe-behavior regression reducer;
- implementing the measured feedback successor where required; and
- implementing the typed post-run analysis engine after the seam is closed.

## Consequences

This tranche prevents three important analysis errors:

- treating physical retry attempts as the scientific logical-turn denominator;
- reconstructing quality or review completeness from public logs after raw evidence is gone;
- producing a runtime-improvement claim before eligibility and quality gates pass.

It also preserves the existing producer until a seam audit proves a real deficiency.

## Non-claims

This design does not:

- implement the final analysis engine;
- implement the measured review exporter;
- define the exact 41-run schedule bytes;
- modify the execution producer;
- run a complete offline integration rehearsal;
- freeze the final execution manifest;
- authorize model, GPU, or Kaggle execution; or
- permit any final quality, runtime, feedback, or effect claim.

## Next gate

`AUDIT_FINAL_342_PRODUCER_REVIEW_ANALYSIS_SEAMS_V1`
