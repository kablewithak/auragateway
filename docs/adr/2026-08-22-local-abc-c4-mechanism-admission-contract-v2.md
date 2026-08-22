# ADR: C4 Mechanism-Admission Contract V2

**Date:** 2026-08-22  
**Status:** Proposed for repository integration  
**Scope:** static qualification boundary only  
**Execution authorization:** absent  

## Context

Canonical C4 is validly dispositioned as `NOT_QUALIFIED`: 0/3 exact objects,
3/3 valid JSON responses, 3/3 HTTP 200 responses, 3/3 terminal `stop`, 899
prompt tokens, 880 reusable-prefix tokens, zero hidden retries, and clean
teardown.

The exact-runtime P5/P6 design predates that result. P5's frozen pass criteria
are cache-metric, token-identity, starting-state, negative-control, and reset
criteria. P6 explicitly sets:

```text
model_semantics_as_route_proof_permitted=false
```

The current runtime path nevertheless couples exact semantic equality into a
shared request helper before all P5/P6 evidence can be completed.

## Decision

Split C4 into two independently recorded observations:

```text
C4-S = semantic canary
C4-M = mechanism admission
```

`C4-S` remains `NOT_QUALIFIED`.

`C4-M` may be `QUALIFIED`, `NOT_QUALIFIED`, or `AMBIGUOUS`.

Mechanism admission answers only whether the composed exact-runtime request is
sufficiently realized, attributable, bounded, and observable for later P5/P6
mechanism evidence to be interpretable.

The mechanism classifier consumes no exact-object or valid-JSON field.

## Provenance rule

The contract is derived from pre-existing P5/P6 proof obligations. It is not
allowed to weaken a semantic criterion and then relabel C4 semantic
qualification.

The following remain separate downstream measurements:

```text
positive cache reuse
worker-local target/non-target metric movement
cross-worker state isolation
```

Mechanism admission must not pre-prove P5 or P6.

## Current corpus

Retain the current corpus for mechanism qualification.

Current geometry:

```text
full prompt = 899 tokens
reusable prefix = 880 tokens
physical/hash block size = 16 tokens
complete reusable blocks = 55
```

No static evidence requires a corpus redesign.

## Static assessment

The first V2 assessment consumes only current repository authorities:

```text
canonical C4 NOT_QUALIFIED disposition record
canonical C4 disposition review
exact-runtime P5/P6 requalification design
```

All are exact-SHA bound.

No model, GPU, Kaggle, network, or authorization action occurs.

## Decision states

`QUALIFIED` means the request boundary is interpretable enough to proceed to a
separately governed P5/P6 mechanism experiment.

`NOT_QUALIFIED` means a trustworthy blocking mechanism failure is observed.

`AMBIGUOUS` means required mechanism evidence is absent or unresolved without a
trustworthy blocking failure already being established.

## Non-claims

A `QUALIFIED` C4-M result does not establish:

- semantic C4 qualification;
- P5 cache reuse;
- P6 route/state isolation;
- variance-pilot acceptance;
- final A/B/C effects;
- quality non-inferiority;
- production readiness.

## Consequences

Positive:

- preserves the immutable C4 semantic failure;
- restores the original mechanism/semantic separation;
- removes semantic output equality from P6 route proof;
- permits reuse of existing governed evidence before another expensive run;
- keeps P5/P6 as the actual mechanism proof boundaries.

Negative:

- a successor P5/P6 runtime still needs implementation work if C4-M qualifies;
- final benchmark cache namespace realization remains a separate downstream
  launcher requirement.

## Next gate

If static C4-M is `QUALIFIED`:

```text
DESIGN_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1
```

Otherwise:

```text
RECONCILE_C4_MECHANISM_ADMISSION_EVIDENCE_V1
```

Neither state creates live execution authority.
