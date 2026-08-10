# ADR: Exact-Runtime P5/P6 Requalification V2 Execution Authorization Issuer

Date: 2026-08-10
Status: Accepted for repository implementation

## Context

V2 repaired the V1 authorization discovery false negative by restoring a governed
producer-root contract. The next authority must bind the merged V2 identities and
must prove current producer/consumer transport parity before a live authorization
is written.

## Decision

Implement a V2-specific single-use issuer. Reuse the proven V1 lifecycle,
terminal dispositions, budgets, and freshness limits as design precedent only.
Bind the merged V2 implementation at `f81fa4209efbd4ea7fbffc130705c6b1189c61d5` and the transport remediation
record `679c11a020e7381417f9f2fe0087f72ee10e9a454703609a1ab48c70da57d3bb`.

Before the live authorization file is written, the candidate canonical compact
JSON bytes must round-trip through the current
`p5_p6_exact_runtime_authorization_transport_v1` materializer and validator.
The transport filename remains `execution_authorization_v1.json` because it is a
frozen transport contract; authorization semantic scope is V2.

## Rejected alternatives

- Reuse the consumed V1 authorization: rejected; terminal authority is non-reusable.
- Direct authorization dataset transport: rejected; it caused the observed failure.
- Global recursive authorization filename search: rejected; PR #114 established
  namespace-collision risk.
- Issue during this PR: rejected; issuer merge identity is a live issuance input.

## Consequences

The issuer PR is inert. After merge, a fresh operator confirmation and fresh Kaggle
settings observation are required. Issuance remains one-shot and non-overwriting.
