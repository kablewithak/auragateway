# ADR: Separate Single-Use P3-P6 Execution Authorization V3

## Status

Approved for repository implementation. No authorization is issued by
this ADR.

## Context

P3-P6 Runtime Diagnostic V3 is merged at
`52272c82a5964377e7091575c297342f4902b640`. It introduces a bounded
process-tree import-closure probe before model copying, model-load
accounting and worker-start accounting.

Runtime execution remains a separately governed action. The V3
implementation record is `IMPLEMENTED_NOT_EXECUTED`, contains no
authorization issuer and explicitly requires a post-merge authorization
tranche.

## Decision

Implement a transient, non-overwriting, single-use V3 authorization
issuer.

The authorization must bind:

- the V3 implementation merge and feature commits;
- the exact V3 record, request, review, template, source and notebook;
- the exact model snapshot and governed CUDA 12.9 wheelhouse;
- one Kaggle T4 x2 session with Internet disabled;
- one runtime installation attempt;
- one process-tree import-closure probe;
- at most three model loads, three worker starts and five requests;
- no benchmark trajectories, external network calls, hidden retries,
  credentials, customer data or external spend.

PASSED, FAILED and INTERRUPTED terminal outcomes all consume the
authorization. Authorization and consumption artifacts remain untracked
until a later evidence-acceptance tranche preserves them.

## Consequences

Runtime execution cannot begin from repository implementation alone.
Explicit operator confirmation is required after the issuer is merged.
The notebook does not parse the transient authority; the operator gate is
bound to exact artifact and input identities.

No runtime success, remediation success or production readiness is
claimed.
