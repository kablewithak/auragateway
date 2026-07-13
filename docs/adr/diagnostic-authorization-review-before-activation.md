# ADR: Separate Diagnostic Authorization Review from Live Activation

**Status:** Accepted
**Decision ID:** `diagnostic-authorization-review-before-activation-v1`

## Context

The Batch 06 diagnostic design and prompt fixtures are ready, but a provider call would create new evidence and spend a bounded live-call budget.

Three implementation options were considered:

1. commit an active authorization and executable runner together;
2. keep authorization entirely outside the repository;
3. commit an inactive review package and dry-run projection, then activate separately.

## Decision

Use option 3.

The repository will first contain an inactive authorization review package that binds:

- the experiment design;
- the design manifest;
- the fixture recipe;
- the fixture manifest;
- the protected local prompt-bundle hash;
- provider identity and request parameters;
- sequence order, budgets, evidence destinations, and privacy restrictions.

A deterministic dry-run report must reproduce the full 24-attempt schedule without credentials or provider calls.

No active `authorization.json`, execution command, or Batch 07 asset may exist in this slice.

## Rationale

This preserves a hard review boundary between:

- proving what would execute; and
- permitting it to execute.

It prevents accidental live calls during implementation, CI, test discovery, or repository validation. It also gives the next activation slice immutable inputs instead of mixing review and execution in one change.

## Consequences

Positive:

- activation is explicit and inspectable;
- review can validate exact request identities and timing;
- credentials are not needed for this slice;
- rollback is deletion of the inactive review package only;
- future execution evidence can bind to reviewed hashes.

Trade-off:

- one additional pull request is required before live execution.

## Rejected alternatives

An immediately active authorization was rejected because it weakens the human review boundary.

An external-only authorization was rejected because it would reduce repository evidence, reproducibility, and regression protection.
