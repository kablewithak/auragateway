# ADR: P3-P6 Runtime Diagnostic Execution Authorization V5

**Date:** 2026-08-04
**Status:** Accepted for repository implementation

## Context

P3-P6 Runtime Diagnostic V5 is merged on main at
`13861da2f13f2ce55fd5fa935e38c765602cb374`, with implementation feature
commit `a942c1edb46ae98a0db9ac9e7085d7a648372d1c`.

The merged V5 implementation remains `IMPLEMENTED_NOT_EXECUTED`. It binds the
accepted V4 diagnostic failure, preserves the accepted P3-P5 runtime lineage,
repairs the P6 route-realization boundary, adds atomic P6 checkpoint evidence,
and requires a separate transient authorization before execution.

The implementation pull request does not issue runtime authority. A repository
issuer is required so that any later execution is explicit, short-lived,
single-use, bound to exact bytes, and consumed after passed, failed, or
interrupted execution.

## Decision

Implement a separate V5 authorization issuer with these boundaries:

- bind the exact V5 implementation merge and feature commits;
- bind the implementation record, request, review, notebook, template, source,
  runtime script, wrapper code, model snapshot, and offline wheelhouse;
- require synchronized clean `main`;
- require transient authorization and consumption files to remain untracked;
- require explicit operator confirmation for issuance and consumption;
- issue one non-overwriting authorization with a maximum 240-minute window;
- permit one Kaggle session, three model loads, three worker starts, and five
  model requests;
- permit no external network requests, hidden retries, benchmark trajectories,
  customer data, credentials, or external spend;
- bind V5 typed route acknowledgement, request-attempt and transport-completion
  checkpoints, per-worker counters, atomic checkpoint serialization, precise
  P6 failure taxonomy, and native-origin closure;
- consume the authorization after the single passed, failed, or interrupted
  attempt;
- keep measured A/B/C execution unauthorized.

## Consequences

The merged issuer can validate and later issue one exact V5 execution authority
without performing execution during the issuer tranche.

The live authorization remains an untracked operational artifact. Repository
generation and validation fail closed when a transient authorization or
consumption artifact is present.

## Non-claims

This ADR does not issue V5 runtime authorization, execute Kaggle, establish P6
success, qualify measured A/B/C, prove latency or cost improvement, or claim
deployment or production readiness.
