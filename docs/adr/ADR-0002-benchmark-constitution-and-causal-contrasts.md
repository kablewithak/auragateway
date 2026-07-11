# ADR-0002: Benchmark Constitution and Causal Contrasts

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 0
- **Supersedes:** None

## Context

AuraGateway compares three runtime conditions. Without a predeclared constitution, implementation choices, run order, exclusions, provider behaviour, or quality review could create misleading improvements.

The benchmark must distinguish three questions:

1. Does deterministic context construction improve runtime behaviour?
2. Does cache-affinity routing improve trajectory-level behaviour after deterministic construction already exists?
3. What is the total difference between the realistic weak baseline and the complete runtime policy?

These questions cannot be collapsed into one claim.

## Decision

AuraGateway will use a versioned benchmark constitution that is frozen before measured benchmark execution.

The constitution is a first-class controlled artifact. It defines:

- condition implementations;
- causal contrasts;
- controlled constants;
- run identities;
- counterbalancing;
- cache namespace isolation;
- cold and warm classification;
- retry and ambiguous-response policy;
- exclusions and reruns;
- denominator treatment;
- quality thresholds;
- adjudication rules;
- statistical reporting;
- claim permissions;
- invalidation triggers.

Measured results produced under different constitution versions are not directly comparable unless a later approved compatibility decision proves otherwise.

## Conditions

### Condition A — Cache-Hostile Baseline

A realistic weak implementation:

- stable and dynamic content may be mixed;
- context lacks enforced static/volatile separation;
- canonical serialization is not required;
- route selection is turn-local;
- session cache value is not preserved.

Condition A must remain functional and plausible. It must not be sabotaged.

### Condition B — Prefix-Deterministic Runtime

Condition B introduces:

- versioned static anchors;
- canonical ordering and serialization;
- typed volatile append;
- retrieval only in volatile context;
- prefix fingerprint validation;
- mutation and volatile-leak detection.

For the A-versus-B contrast, route behaviour remains fixed.

### Condition C — Cache-Aware Agent Runtime

Condition C includes Condition B plus:

- typed session route state;
- plausible warm-cache affinity;
- bounded TTL-based route reconsideration;
- explicit capability, safety, quality, provider-failure, and benchmark-control reasons;
- route-thrash detection.

## Causal interpretations

### A versus B

Interpretation:

> Effect of deterministic context-construction policy under fixed route behaviour.

No route-policy change is permitted in this contrast.

### B versus C

Interpretation:

> Effect of cache-affinity route policy after deterministic context construction is already present.

No context-construction change is permitted in this contrast.

### A versus C

Interpretation:

> Total system difference between the weak baseline and the complete runtime policy.

This comparison must not be described as identifying a single causal mechanism.

## Comparison eligibility

Every compared run must share the controlled configuration fingerprint required by the constitution.

A comparison is ineligible when any controlled field differs, including:

- corpus manifest;
- retrieval configuration;
- prompt template;
- static context pack;
- tool contract;
- output schema;
- evaluation manifests;
- quality rubric;
- adjudication protocol;
- provider/model capability tier;
- runtime condition implementation version;
- benchmark runner;
- route-policy version;
- run-order policy;
- statistical configuration;
- pricing schedule when cost is reported.

The comparison gate must identify mismatches, affected claims, and required reruns.

## Run accountability

Every run resolves to one of:

- completed;
- completed with validation failure;
- provider error;
- budget exhausted;
- excluded by predeclared rule;
- invalidated by configuration mismatch;
- aborted by safety control.

Failed, retried, excluded, and invalidated runs remain in the evidence bundle.

## Review blindness

Rubric-based quality review must use opaque review identifiers. Reviewers must not know the runtime condition.

At least 25 percent of rubric-reviewed outputs must be double-reviewed, with disagreement reasons retained and material disagreements adjudicated.

## Quality-before-savings rule

A cost, token, cache, or latency improvement is not accepted when the fixed quality non-inferiority gate fails.

At minimum:

- task success may not regress by more than 5 percentage points;
- citation support may not regress;
- structured-output validity must remain at or above 95 percent;
- unsupported-answer rate may not increase;
- retrieval configuration must remain unchanged;
- no new unsafe route, retry, escalation, or refusal pattern may appear.

## Consequences

### Positive

- Results remain interpretable and reproducible.
- A/B, B/C, and A/C claims remain distinct.
- Failed runs and configuration mismatches cannot be hidden.
- Quality review is less vulnerable to condition bias.
- Reporting can machine-block unsupported conclusions.

### Negative

- Any controlled-constant change may require a full rerun.
- Benchmark execution becomes slower and more administratively strict.
- Some provider changes may invalidate evidence even when application code is unchanged.

## Implementation requirement

No measured A/B/C benchmark run may begin until the benchmark constitution is explicitly marked frozen with a version and content hash.
