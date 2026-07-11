# AuraGateway Gate 0 Freeze Review

## Decision

```text
Proof gate: Gate 0 — Benchmark Constitution
Decision: PASS
Constitution version: 1.0.0
Constitution status: Frozen
Constitution SHA-256: c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1
Measured execution permitted: No
Next phase: Phase 1 — Corpus, Retrieval, and Eval Asset Construction
```

## Review scope

This review determines whether AuraGateway has frozen the experiment rules required before implementation work proceeds.

It does not claim that provider, corpus, retrieval, evaluation, or runtime assets already exist.

## Important interpretation resolved

The PRD combines:

- rules that must be frozen at Gate 0; and
- assets that cannot exist until later phases.

Treating every future asset hash as a Gate 0 requirement would make the delivery plan impossible because Phase 1 through Phase 6 create those assets.

The accepted resolution is a two-layer freeze:

### Frozen now

The Benchmark Constitution fixes:

- benchmark question;
- A/B/C condition meaning;
- causal contrasts;
- controlled-constant categories;
- run identities;
- functional and runtime counterbalancing;
- cold and warm classification;
- timeout and retry rules;
- exclusion and rerun rules;
- denominator treatment;
- quality non-inferiority thresholds;
- blinded-review protocol;
- statistical reporting;
- privacy rules;
- evidence immutability;
- comparison eligibility;
- invalidation triggers;
- claims and non-claims.

### Frozen later

The execution manifest will pin exact assets after their proof gates:

- corpus;
- retrieval;
- prompt and context pack;
- schemas and tools;
- provider and model;
- telemetry and TTL;
- route policy;
- evaluation manifests and rubric;
- fault fixtures;
- pricing;
- implementation and dependency hashes.

This later manifest may not change the constitution's rules.

## Gate 0 acceptance review

### Primary causal contrasts are explicit

**PASS**

- A versus B isolates deterministic context construction.
- B versus C isolates cache-affinity routing.
- A versus C is total system effect only.

### Controlled constants are enumerated

**PASS**

The constitution declares every controlled category, and the execution-manifest requirements define where exact later values must be pinned.

### Paired and counterbalanced run order is defined

**PASS**

- Functional schedule: 3 fixed rotations.
- Runtime schedule: 10 fixed permutations.
- Operators may not reorder after partial results.

### Cold and warm classification is defined

**PASS**

The constitution distinguishes cold, warm-eligible, and ambiguous state.

Warm eligibility is explicitly not treated as proof of a cache hit.

### Retry, exclusion, and rerun rules are predeclared

**PASS**

Exact timeout, retry, backoff, allowed exclusions, and rerun triggers are frozen.

### Failed-run denominator treatment is explicit

**PASS**

The primary quality denominator includes all comparison-eligible scheduled trajectories.

Runtime reporting includes completed-run and failure-accounted views.

### Statistical reporting is defined before results

**PASS**

The constitution fixes:

- paired episode-level resampling;
- percentile bootstrap;
- 10,000 samples;
- 95 percent interval;
- seed `20260712`;
- median, quartiles, range, and P90 where useful.

### Constitution version and hash are frozen

**PASS**

```text
Version: 1.0.0
SHA-256: c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1
```

### Privacy and evidence controls exist

**PASS**

ADR-0009, ADR-0010, the privacy boundary, and the evidence-bundle specification govern implementation.

### Scope remains controlled

**PASS**

No production gateway, dashboard, cloud deployment, customer data, billing, authentication, managed vector database, or multi-agent scope has entered the critical path.

## Evidence boundary

The current evidence supports:

- benchmark-constitution validated;
- Phase 0 Gate 0 passed;
- implementation may proceed to Phase 1.

It does not support:

- retrieval readiness;
- prefix determinism;
- provider telemetry integrity;
- route-policy correctness;
- task-quality non-inferiority;
- benchmark performance;
- cost or latency savings;
- production readiness.

## Gate decision

Gate 0 is closed.

Measured benchmark execution remains blocked until:

- Gates 1 through 8 pass;
- the execution manifest is complete;
- the execution manifest is frozen and hashed;
- configuration validation succeeds.

## Next safest slice

Begin Phase 1 with the **synthetic Nimbus Relay corpus constitution and source manifest**.

That slice should define:

- document inventory and minimum counts;
- metadata schema;
- stale, conflicting, incomplete, and near-duplicate document quotas;
- version-sensitive procedure requirements;
- corpus acceptance rules;
- source-manifest and hash rules;
- privacy validation;
- corpus generation boundaries.

It should not yet implement retrieval.
