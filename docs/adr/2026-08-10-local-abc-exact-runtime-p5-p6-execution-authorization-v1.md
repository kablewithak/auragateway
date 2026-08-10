# ADR: Exact-Runtime P5/P6 Execution Authorization Issuer V1

**Date:** 2026-08-10
**Status:** Accepted for repository implementation

## Context

The exact-runtime P5/P6 qualification harness is merged but intentionally not
executed. Its authorization design is also merged. A separate issuer is required
so implementation presence cannot imply execution authority.

## Decision

Implement a single-use, short-lived authorization issuer that remains inert
through its repository tranche. Static generation and validation may create only
an architecture review and implementation record.

Live issuance is permitted only after the issuer is merged and the following are
revalidated immediately before issuance:

- synchronized clean `main`;
- exact issuer merge commit;
- merged authorization-design identity;
- merged P5/P6 implementation identity;
- current P5/P6 static implementation validation;
- semantic/evidence boundary invariants;
- fresh T4 x2 / Internet-off platform observation;
- fresh exact operator confirmation.

## Lifecycle

One authorization starts at `ISSUED` and becomes permanently non-reusable after
exactly one terminal receipt. Supported terminal dispositions are:

- `CONSUMED`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`
- `OUTCOME_UNKNOWN`

The receipt path is non-overwriting. `OUTCOME_UNKNOWN` is reserved for an
execution attempt whose final result cannot be established reliably.

## Budget

The issuer cannot expand the frozen execution ceiling: one Kaggle session, one
saved version, six model requests, three worker starts, three model loads, zero
hidden retries, zero replacement workers, zero external network requests, zero
benchmark trajectories, and zero external spend.

## Consequences

Merging this issuer does not issue authority. A later operator-controlled
transaction must create a fresh canonical confirmation and issue one live
authorization. Pilot and final measured A/B/C authority remain separate gates.
