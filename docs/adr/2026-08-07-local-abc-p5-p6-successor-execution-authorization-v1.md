# ADR: P5/P6 Successor Execution Authorization V1

**Date:** 2026-08-07
**Status:** Implemented candidate; runtime authority remains absent until explicit issuance

## Context

P5/P6 Successor Runtime Qualification V1 is merged on main at
`6e424acb27e568bb7ce5000ea0732e175bf6b35a` and remains
`IMPLEMENTED_NOT_EXECUTED`.

The merged successor binds one bounded runtime transaction:

- one Kaggle session;
- one saved version;
- one offline runtime install attempt;
- one process-tree import-closure probe;
- at most three model loads;
- at most three worker starts;
- at most five model requests;
- at most 32 output tokens per request;
- zero hidden retries;
- zero replacement workers;
- zero benchmark-trajectory requests;
- zero external network requests;
- zero external spend.

The merged implementation does not itself issue runtime authority.

## Decision

Implement a separate, transient, single-use authorization lifecycle for the
exact merged successor bytes.

The authorization issuer MUST bind:

- merged successor implementation commit;
- implementation record, request, review, source, template, tests, notebook,
  ADR, report, and runbook identities;
- notebook, runtime-script, wrapper-code, model-snapshot, backend, and logical
  request identities;
- the five-request and three-worker-start ceilings;
- fresh Kaggle T4 x2 capability observation;
- Internet disabled;
- one wheelhouse attachment and one model-snapshot attachment;
- worker 1 on GPU 0 / port 8001;
- worker 2 on GPU 1 / port 8002;
- P5 token-telemetry and full-process-reset evidence;
- P6 typed transport plus target/non-target metric isolation;
- fail-closed ambiguous metric-series handling;
- structured teardown and request reconciliation.

Issuance requires an explicit canonical operator confirmation whose platform
observation is no more than 15 minutes old.

The live authorization and all terminal lifecycle receipts remain untracked.

## Lifecycle

```text
STATIC ISSUER MERGED
    |
    v
FRESH KAGGLE CAPABILITY OBSERVATION
    |
    v
EXPLICIT OPERATOR CONFIRMATION
    |
    v
SINGLE-USE AUTHORIZATION ISSUED
    |
    +--> ABANDONED BEFORE EXECUTION
    |
    `--> ONE GOVERNED ATTEMPT
             |
             v
       CONSUMED ON TERMINAL OUTCOME
```

Terminal execution outcomes include:

- PASSED;
- FAILED;
- INTERRUPTED;
- TIMED_OUT;
- KAGGLE_PLATFORM_TERMINATED;
- OUTCOME_UNKNOWN.

Every terminal execution outcome is non-reusable.

An unused issued authorization may be abandoned, but abandonment is also
non-reusable.

## Alternatives considered

### Reuse the historical P3-P6 V5 authorization issuer

Rejected. The V5 issuer binds predecessor implementation identities rather
than the composed current-line successor.

### Treat the merged implementation as implicit authority

Rejected. Implementation and execution authority are separate control planes.

### Issue authorization in the implementation PR

Rejected. This would collapse repository implementation and live runtime
authority into one transition and defeat the single-use lifecycle.

## Consequences

The issuer adds one explicit operator confirmation and one transient lifecycle
artifact before execution. This is intentional friction: it binds the exact
runtime bytes and current platform state immediately before the high-risk
runtime transition.

The authorization implementation still makes no P5, P6, measured A/B/C,
deployment, or production-readiness claim.
